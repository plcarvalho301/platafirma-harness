"""Geração de dublê ASGI em processo a partir de cópia fixada de contrato OpenAPI 3.1."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from suite.contrato import (
    METODOS_HTTP,
    ContratoCarregado,
    ContratoErro,
    extrair_exemplo_midia,
    ler_copia,
    resolver_ref,
    trazer,
    validar_contra_schema,
)

_STATUS_SUCESSO_MIN = 200
_STATUS_SUCESSO_MAX = 300
_STATUS_ERRO_MIN = 400
_STATUS_SEM_CORPO = 204


@dataclass(frozen=True)
class _RespostaExemplo:
    status: int
    content_type: str
    corpo: Any


@dataclass(frozen=True)
class _OperacaoDuble:
    metodo: str
    padrao: re.Pattern[str]
    caminho_tmpl: str
    sucesso: _RespostaExemplo
    erros: dict[int, _RespostaExemplo]
    req_schema: dict[str, Any] | None


def _compilar_caminho(caminho_tmpl: str) -> re.Pattern[str]:
    partes = re.split(r"(\{[^}]+\})", caminho_tmpl)
    regex = ["^"]
    for parte in partes:
        if parte.startswith("{") and parte.endswith("}"):
            nome = re.escape(parte[1:-1])
            regex.append(f"(?P<{nome}>[^/]+)")
        else:
            regex.append(re.escape(parte))
    regex.append("$")
    return re.compile("".join(regex))


def _extrair_resposta(doc: dict[str, Any], status: int, spec_raw: dict[str, Any]) -> _RespostaExemplo:
    spec = resolver_ref(doc, spec_raw)
    content = spec.get("content") or {}
    if not content:
        return _RespostaExemplo(status=status, content_type="application/json", corpo=None)
    for ctype in ("application/json", "application/problem+json", *content.keys()):
        if ctype in content:
            achou, exemplo = extrair_exemplo_midia(doc, content[ctype])
            return _RespostaExemplo(
                status=status,
                content_type=ctype,
                corpo=exemplo if achou else {},
            )
    return _RespostaExemplo(status=status, content_type="application/json", corpo=None)


def _compilar_operacao(
    doc: dict[str, Any],
    padrao: re.Pattern[str],
    caminho_tmpl: str,
    metodo: str,
    op: dict[str, Any],
) -> _OperacaoDuble:
    responses = op.get("responses") or {}
    sucesso: _RespostaExemplo | None = None
    erros: dict[int, _RespostaExemplo] = {}
    for code_str, resp_spec in responses.items():
        if not str(code_str).isdigit():
            continue
        code = int(code_str)
        resp_ex = _extrair_resposta(doc, code, resp_spec)
        if _STATUS_SUCESSO_MIN <= code < _STATUS_SUCESSO_MAX and sucesso is None:
            sucesso = resp_ex
        elif code >= _STATUS_ERRO_MIN:
            erros[code] = resp_ex
    if sucesso is None:
        sucesso = _RespostaExemplo(status=200, content_type="application/json", corpo={})

    req_schema: dict[str, Any] | None = None
    req_body = op.get("requestBody")
    if isinstance(req_body, dict):
        req_body = resolver_ref(doc, req_body)
        json_media = (req_body.get("content") or {}).get("application/json")
        if isinstance(json_media, dict):
            json_media = resolver_ref(doc, json_media)
            if isinstance(json_media.get("schema"), dict):
                req_schema = json_media["schema"]

    return _OperacaoDuble(
        metodo=metodo.upper(),
        padrao=padrao,
        caminho_tmpl=caminho_tmpl,
        sucesso=sucesso,
        erros=erros,
        req_schema=req_schema,
    )


def _compilar_operacoes(doc: dict[str, Any]) -> list[_OperacaoDuble]:
    operacoes: list[_OperacaoDuble] = []
    paths = doc.get("paths") or {}
    for caminho_tmpl, item in paths.items():
        if not isinstance(item, dict):
            continue
        padrao = _compilar_caminho(caminho_tmpl)
        for metodo in METODOS_HTTP:
            op = item.get(metodo)
            if isinstance(op, dict):
                operacoes.append(_compilar_operacao(doc, padrao, caminho_tmpl, metodo, op))
    return operacoes


async def _ler_corpo(receive: Any) -> bytes:
    partes: list[bytes] = []
    while True:
        msg = await receive()
        if msg["type"] == "http.request":
            partes.append(msg.get("body", b""))
            if not msg.get("more_body", False):
                break
        elif msg["type"] == "http.disconnect":
            break
    return b"".join(partes)


async def _enviar_json(send: Any, resp: _RespostaExemplo) -> None:
    if resp.status == _STATUS_SEM_CORPO or resp.corpo is None:
        corpo_bytes = b""
        headers = [(b"content-length", b"0")]
    else:
        corpo_bytes = json.dumps(resp.corpo, ensure_ascii=False).encode("utf-8")
        headers = [
            (b"content-type", resp.content_type.encode("utf-8")),
            (b"content-length", str(len(corpo_bytes)).encode("ascii")),
        ]
    await send({"type": "http.response.start", "status": resp.status, "headers": headers})
    await send({"type": "http.response.body", "body": corpo_bytes})


async def _escolher_resposta(
    doc: dict[str, Any],
    operacoes: list[_OperacaoDuble],
    scope: dict[str, Any],
    receive: Any,
) -> _RespostaExemplo:
    metodo = scope["method"].upper()
    caminho = scope.get("path", "/")
    headers_req = {
        k.decode("latin-1").lower(): v.decode("latin-1")
        for k, v in scope.get("headers", [])
    }
    casou_caminho = [op for op in operacoes if op.padrao.match(caminho)]
    if not casou_caminho:
        return _RespostaExemplo(
            status=404,
            content_type="application/problem+json",
            corpo={
                "type": "about:blank",
                "title": "RotaNaoEncontrada",
                "detail": f"caminho '{caminho}' não declarado no contrato",
            },
        )

    op = next((o for o in casou_caminho if o.metodo == metodo), None)
    if op is None:
        return _RespostaExemplo(
            status=405,
            content_type="application/problem+json",
            corpo={
                "type": "about:blank",
                "title": "MetodoNaoPermitido",
                "detail": f"método {metodo} não declarado para '{caminho}'",
            },
        )

    if "x-duble-status" in headers_req and headers_req["x-duble-status"].isdigit():
        cod = int(headers_req["x-duble-status"])
        if cod in op.erros:
            return op.erros[cod]

    if op.req_schema is not None:
        bruto = await _ler_corpo(receive)
        try:
            instancia = json.loads(bruto.decode("utf-8")) if bruto else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            instancia = None
        erros = validar_contra_schema(doc, op.req_schema, instancia)
        if erros:
            return op.erros.get(422) or op.erros.get(400) or _RespostaExemplo(
                status=422,
                content_type="application/problem+json",
                corpo={
                    "type": "about:blank",
                    "title": "EntradaInvalida",
                    "detail": "; ".join(erros),
                },
            )

    return op.sucesso


def gerar_duble(caminho_copia: str | Path) -> Any:
    """Gera uma aplicação ASGI em processo a partir da cópia fixada do contrato."""
    carregado: ContratoCarregado = ler_copia(caminho_copia)
    doc = carregado.documento
    operacoes = _compilar_operacoes(doc)

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            return
        resp = await _escolher_resposta(doc, operacoes, scope, receive)
        await _enviar_json(send, resp)

    app.versao = carregado.versao
    app.sha256 = carregado.sha256
    app.operacoes = [(o.metodo, o.caminho_tmpl) for o in operacoes]
    return app


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite.duble")
    sub = p.add_subparsers(dest="ato", required=True)
    p_trazer = sub.add_parser("trazer", help="copia o contrato publicado e fixa versão e hash")
    p_trazer.add_argument("arvore_fornecedor", help="caminho da árvore do repositório fornecedor")
    p_trazer.add_argument("caminho_descricao", help="caminho relativo da descrição OpenAPI na árvore")
    p_trazer.add_argument("versao", help="versão semântica esperada em info.version")
    p_trazer.add_argument("--destino", default=".", help="diretório ou arquivo de destino da cópia")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.ato == "trazer":
        try:
            res = trazer(
                args.arvore_fornecedor,
                args.caminho_descricao,
                args.versao,
                destino=args.destino,
            )
        except ContratoErro as exc:
            sys.stderr.write(f"duble: {exc}\n")
            return 1
        estado = "atualizada" if res.mudou else "inalterada"
        sys.stdout.write(
            f"trazido: {res.destino} (versão {res.versao}, sha256 {res.sha256[:12]}, {estado})\n"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
