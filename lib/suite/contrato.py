"""Leitura de contratos OpenAPI 3.1, cópia fixada por hash e verificação de quem fornece."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import referencing
import referencing.jsonschema
import yaml

METODOS_HTTP = ("get", "post", "put", "patch", "delete", "head", "options")


if not hasattr(httpx.ASGITransport, "__enter__"):
    def _asgi_enter(self: httpx.ASGITransport) -> httpx.ASGITransport:
        return self

    def _asgi_exit(self: httpx.ASGITransport, *args: object) -> None:
        asyncio.run(self.aclose())

    def _asgi_close(self: httpx.ASGITransport) -> None:
        asyncio.run(self.aclose())

    def _asgi_handle_request(self: httpx.ASGITransport, request: httpx.Request) -> httpx.Response:
        async def _rodar() -> httpx.Response:
            resp = await self.handle_async_request(request)
            corpo = await resp.aread()
            return httpx.Response(
                status_code=resp.status_code,
                headers=resp.headers,
                content=corpo,
                request=request,
            )

        return asyncio.run(_rodar())

    httpx.ASGITransport.__enter__ = _asgi_enter  # type: ignore[attr-defined]
    httpx.ASGITransport.__exit__ = _asgi_exit  # type: ignore[attr-defined]
    httpx.ASGITransport.close = _asgi_close  # type: ignore[attr-defined]
    httpx.ASGITransport.handle_request = _asgi_handle_request  # type: ignore[attr-defined]


class ContratoErro(RuntimeError):
    """Erro ao trazer, ler ou validar a integridade de um contrato."""


class VerificacaoContratoErro(AssertionError):
    """Falha na verificação de quem fornece contra o contrato."""


@dataclass(frozen=True)
class ResultadoTrazer:
    """Resultado da cópia idempotente de um contrato publicado."""

    destino: Path
    meta: Path
    versao: str
    sha256: str
    mudou: bool


@dataclass(frozen=True)
class ContratoCarregado:
    """Contrato lido e conferido pelo hash da cópia."""

    caminho: Path
    versao: str
    sha256: str
    documento: dict[str, Any]


def _sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def _meta_de(caminho_copia: Path) -> Path:
    return caminho_copia.with_suffix(caminho_copia.suffix + ".meta.json")


def ler_openapi(caminho: Path) -> dict[str, Any]:
    """Lê uma descrição OpenAPI 3.1 em YAML a partir do caminho dado."""
    try:
        bruto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContratoErro(f"descrição ausente ou ilegível: {caminho} ({exc})") from exc
    try:
        doc = yaml.safe_load(bruto)
    except yaml.YAMLError as exc:
        raise ContratoErro(f"YAML inválido em {caminho}: {exc}") from exc
    if not isinstance(doc, dict) or "paths" not in doc:
        raise ContratoErro(f"descrição OpenAPI inválida (falta 'paths'): {caminho}")
    return doc


def _copia_igual(caminho_dest: Path, caminho_meta: Path, bytes_origem: bytes, versao: str, sha: str) -> bool:
    try:
        meta_atual = json.loads(caminho_meta.read_text(encoding="utf-8"))
        bytes_atuais = caminho_dest.read_bytes()
    except (OSError, json.JSONDecodeError):
        return False
    return (
        meta_atual.get("sha256") == sha
        and meta_atual.get("versao") == versao
        and bytes_atuais == bytes_origem
    )


def trazer(
    arvore_fornecedor: str | Path,
    caminho_descricao: str | Path,
    versao: str,
    destino: str | Path | None = None,
) -> ResultadoTrazer:
    """Copia a descrição publicada na árvore de quem fornece para a pasta de teste.

    Confere que o arquivo existe e declara exatamente `info.version == versao`.
    Grava a cópia e o arquivo `.meta.json` com versão e sha256. Idempotente.
    """
    raiz = Path(arvore_fornecedor)
    rel = Path(caminho_descricao)
    if rel.is_absolute() or ".." in rel.parts:
        raise ContratoErro(f"caminho da descrição deve ser relativo à árvore: {caminho_descricao}")
    origem = raiz / rel
    try:
        bytes_origem = origem.read_bytes()
    except OSError as exc:
        raise ContratoErro(
            f"descrição '{caminho_descricao}' não publicada em '{arvore_fornecedor}' ({exc})"
        ) from exc

    doc = ler_openapi(origem)
    info = doc.get("info") if isinstance(doc.get("info"), dict) else {}
    versao_publicada = str(info.get("version", ""))
    if versao_publicada != versao:
        raise ContratoErro(
            f"versão '{versao}' não publicada em '{caminho_descricao}' "
            f"(publicada: '{versao_publicada or 'ausente'}')"
        )

    sha = _sha256_bytes(bytes_origem)
    dest_base = Path(destino) if destino is not None else Path(".")
    caminho_dest = dest_base / rel.name if dest_base.is_dir() or not dest_base.suffix else dest_base
    caminho_meta = _meta_de(caminho_dest)

    mudou = not _copia_igual(caminho_dest, caminho_meta, bytes_origem, versao, sha)
    if mudou:
        caminho_dest.parent.mkdir(parents=True, exist_ok=True)
        caminho_dest.write_bytes(bytes_origem)
        meta = {
            "versao": versao,
            "sha256": sha,
            "origem": str(rel),
        }
        caminho_meta.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return ResultadoTrazer(
        destino=caminho_dest,
        meta=caminho_meta,
        versao=versao,
        sha256=sha,
        mudou=mudou,
    )


def ler_copia(caminho_copia: str | Path) -> ContratoCarregado:
    """Lê a cópia local da descrição e confere versão e sha256 no arquivo `.meta.json`."""
    caminho = Path(caminho_copia)
    meta_path = _meta_de(caminho)
    try:
        bytes_copia = caminho.read_bytes()
    except OSError as exc:
        raise ContratoErro(f"cópia do contrato ausente ou ilegível: {caminho} ({exc})") from exc
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContratoErro(f"metadados do contrato ausentes ou ilegíveis em {meta_path}: {exc}") from exc

    esperado = meta.get("sha256", "")
    versao = str(meta.get("versao", ""))
    atual = _sha256_bytes(bytes_copia)
    if not esperado or atual != esperado:
        raise ContratoErro(
            f"hash da cópia {caminho} não confere com {meta_path} "
            f"(esperado {esperado[:12]}, atual {atual[:12]})"
        )

    doc = ler_openapi(caminho)
    versao_doc = str((doc.get("info") or {}).get("version", ""))
    if versao_doc != versao:
        raise ContratoErro(
            f"versão em {caminho} ({versao_doc}) diverge dos metadados ({versao})"
        )
    return ContratoCarregado(caminho=caminho, versao=versao, sha256=atual, documento=doc)


def resolver_ref(doc: dict[str, Any], obj: Any) -> Any:
    """Resolve `$ref` local (`#/components/...`) dentro do documento OpenAPI."""
    vistos: set[str] = set()
    atual = obj
    while isinstance(atual, dict) and "$ref" in atual:
        ref = atual["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise ContratoErro(f"$ref não suportado fora do documento: {ref!r}")
        if ref in vistos:
            raise ContratoErro(f"$ref cíclico: {ref}")
        vistos.add(ref)
        alvo: Any = doc
        for parte in ref[2:].split("/"):
            parte = parte.replace("~1", "/").replace("~0", "~")
            if not isinstance(alvo, dict) or parte not in alvo:
                raise ContratoErro(f"$ref não encontrado: {ref}")
            alvo = alvo[parte]
        atual = alvo
    return atual


def _registry_de(doc: dict[str, Any]) -> referencing.Registry:
    recurso = referencing.Resource.from_contents(
        doc, default_specification=referencing.jsonschema.DRAFT202012
    )
    return referencing.Registry().with_resource("", recurso)


def _expandir_refs(
    doc: dict[str, Any], obj: Any, vistos: frozenset[str] = frozenset()
) -> Any:
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            ref = obj["$ref"]
            if ref in vistos:
                raise ContratoErro(f"$ref cíclico: {ref}")
            alvo = resolver_ref(doc, obj)
            return _expandir_refs(doc, alvo, vistos | {ref})
        return {k: _expandir_refs(doc, v, vistos) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expandir_refs(doc, item, vistos) for item in obj]
    return obj


def validar_contra_schema(
    doc: dict[str, Any], schema: dict[str, Any], instancia: Any
) -> list[str]:
    """Valida `instancia` contra `schema` no dialeto JSON Schema 2020-12."""
    schema_resolvido = _expandir_refs(doc, schema)
    validador = jsonschema.Draft202012Validator(
        schema_resolvido,
        registry=_registry_de(doc),
    )
    erros = sorted(validador.iter_errors(instancia), key=lambda e: list(e.path))
    return [f"{'/'.join(str(p) for p in e.path) or '<raiz>'}: {e.message}" for e in erros]


def extrair_exemplo_midia(doc: dict[str, Any], media: dict[str, Any]) -> tuple[bool, Any]:
    """Extrai `(encontrou, valor)` de um objeto MediaType OpenAPI."""
    media = resolver_ref(doc, media)
    if "example" in media:
        return True, media["example"]
    examples = media.get("examples")
    if isinstance(examples, dict) and examples:
        primeiro = resolver_ref(doc, next(iter(examples.values())))
        if isinstance(primeiro, dict) and "value" in primeiro:
            return True, primeiro["value"]
    schema = media.get("schema")
    if isinstance(schema, dict):
        schema = resolver_ref(doc, schema)
        if "example" in schema:
            return True, schema["example"]
    return False, None


def _exemplo_parametro(doc: dict[str, Any], param: dict[str, Any]) -> Any:
    param = resolver_ref(doc, param)
    if "example" in param:
        return param["example"]
    schema = param.get("schema")
    if isinstance(schema, dict):
        schema = resolver_ref(doc, schema)
        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
    return "exemplo"


def _nome_operacao(metodo: str, caminho: str, op: dict[str, Any]) -> str:
    op_id = op.get("operationId")
    base = f"{metodo.upper()} {caminho}"
    return f"{base} ({op_id})" if op_id else base


def _montar_requisicao(
    doc: dict[str, Any],
    caminho_tmpl: str,
    params_comuns: list[Any],
    op: dict[str, Any],
) -> tuple[str, dict[str, Any], dict[str, str], Any]:
    url = caminho_tmpl
    query: dict[str, Any] = {}
    headers: dict[str, str] = {}

    for p_raw in [*params_comuns, *(op.get("parameters") or [])]:
        p = resolver_ref(doc, p_raw)
        local = p.get("in")
        nome_p = p.get("name")
        if not nome_p:
            continue
        val = _exemplo_parametro(doc, p)
        if local == "path":
            url = re.sub(r"\{" + re.escape(nome_p) + r"\}", str(val), url)
        elif local == "query" and p.get("required"):
            query[nome_p] = val
        elif local == "header" and p.get("required"):
            headers[nome_p] = str(val)

    json_body = None
    req_body = op.get("requestBody")
    if isinstance(req_body, dict):
        req_body = resolver_ref(doc, req_body)
        content = req_body.get("content") or {}
        if "application/json" in content:
            achou, val = extrair_exemplo_midia(doc, content["application/json"])
            if achou:
                json_body = val
    return url, query, headers, json_body


def _conferir_resposta(
    doc: dict[str, Any],
    nome_op: str,
    op: dict[str, Any],
    resp: httpx.Response,
) -> None:
    responses = op.get("responses") or {}
    status_sucesso = [str(code) for code in responses if str(code).startswith("2")]
    if str(resp.status_code) not in status_sucesso:
        raise VerificacaoContratoErro(
            f"operação {nome_op} devolveu status {resp.status_code}, "
            f"esperado um de {status_sucesso}"
        )

    resp_spec = resolver_ref(doc, responses[str(resp.status_code)])
    content_resp = resp_spec.get("content") or {}
    if not content_resp:
        return
    ctype = resp.headers.get("content-type", "application/json").split(";")[0].strip()
    media = content_resp.get(ctype) or content_resp.get("application/json")
    if media is None:
        raise VerificacaoContratoErro(
            f"operação {nome_op} devolveu content-type '{ctype}' não declarado"
        )
    media = resolver_ref(doc, media)
    schema = media.get("schema")
    if not isinstance(schema, dict):
        return
    try:
        corpo = resp.json()
    except ValueError as exc:
        raise VerificacaoContratoErro(
            f"operação {nome_op} devolveu JSON inválido: {exc}"
        ) from exc
    erros = validar_contra_schema(doc, schema, corpo)
    if erros:
        raise VerificacaoContratoErro(
            f"operação {nome_op} devolveu resposta fora do contrato: " + "; ".join(erros)
        )


def verificar_fornecedor(
    contrato: ContratoCarregado | str | Path,
    fornecedor: httpx.Client | Any,
) -> list[str]:
    """Chama cada operação declarada no contrato com o exemplo de entrada e confere a resposta.

    `fornecedor` pode ser um `httpx.Client` ou uma aplicação ASGI (envolvida por `ASGITransport`).
    Retorna a lista de operações verificadas; levanta `VerificacaoContratoErro` nomeando a
    operação se o status ou o esquema da resposta não cumprir o contrato.
    """
    carregado = ler_copia(contrato) if not isinstance(contrato, ContratoCarregado) else contrato
    doc = carregado.documento

    if isinstance(fornecedor, httpx.Client):
        return _executar_verificacao(doc, fornecedor)

    with httpx.Client(
        transport=httpx.ASGITransport(app=fornecedor),
        base_url="http://fornecedor",
    ) as cliente:
        return _executar_verificacao(doc, cliente)


def _executar_verificacao(doc: dict[str, Any], cliente: httpx.Client) -> list[str]:
    verificadas: list[str] = []
    paths = doc.get("paths") or {}

    for caminho_tmpl, item in paths.items():
        if not isinstance(item, dict):
            continue
        params_comuns = item.get("parameters") or []
        for metodo in METODOS_HTTP:
            op = item.get(metodo)
            if not isinstance(op, dict):
                continue
            nome_op = _nome_operacao(metodo, caminho_tmpl, op)
            url, query, headers, json_body = _montar_requisicao(
                doc, caminho_tmpl, params_comuns, op
            )
            resp = cliente.request(
                metodo.upper(),
                url,
                params=query or None,
                headers=headers or None,
                json=json_body,
            )
            _conferir_resposta(doc, nome_op, op, resp)
            verificadas.append(nome_op)

    return verificadas
