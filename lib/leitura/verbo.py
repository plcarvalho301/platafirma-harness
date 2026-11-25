"""Adaptador de leitura de arquivo/conteúdo para verbos do harness (`python -m leitura.verbo`).

Usado por baixo de `release ler`, `repo ler`, `acervo ler casa` e `tarefas`,
delegando integralmente fatiamento por linhas, offset em bytes UTF-8 e modo
inteiro ao núcleo `lib/leitura` (`ler_arquivo`), sem duplicar paginação nos
verbos e sem passar pelo gatilho MCP da porta (incidente #4433).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .leitura import _valida_opcoes, le, le_memoria
from .morada import eh_segredo
from .recusa import Recusa


@dataclass
class _CliPedido:
    caminho: str | None = None
    caminho_logico: str | None = None
    checar_vedado: str | None = None
    usar_stdin: bool = False
    validar_opcoes: bool = False
    linhas: str | None = None
    offset: int | None = None
    max_bytes: int | None = None
    inteiro: bool = True
    numerar: bool = False
    rotulo: str = "ler"


def _recusa_vedada(caminho: Path | str) -> tuple[int, bytes, str, dict[str, Any]]:
    rec = Recusa(
        saida=4,
        codigo="segredo-fora-do-leitor",
        onde="caminho",
        recebido=str(caminho),
        regra="superficie-vedada",
        cura="segredos, política de acesso, projeção de sujeitos e trilha bruta ficam fora do leitor geral",
        proximo="",
    )
    err_s = json.dumps(rec.campos(), ensure_ascii=False) + "\n"
    meta = {"erro": rec.codigo, "exit_code": 4, "recusado": True, "recusa": rec.campos()}
    return 4, b"", err_s, meta


def _parse_int_nao_negativo(
    valor: str, flag: str, rotulo: str, *, minimo: int = 0
) -> int | tuple[int, str]:
    if not valor or not valor.lstrip("-").isdigit():
        return 2, f"{rotulo}: {flag} pede um número inteiro (>= {minimo})\n"
    n = int(valor)
    if n < minimo:
        return 2, f"{rotulo}: {flag} pede um número inteiro (>= {minimo})\n"
    return n


def _formatar_numerado(conteudo: str, linha_inicial: int, *, garantir_nl_final: bool) -> bytes:
    if not conteudo:
        return b""
    saida: list[bytes] = []
    for idx, linha in enumerate(conteudo.splitlines(keepends=True), start=linha_inicial):
        bloco = f"{idx}: {linha}".encode()
        if garantir_nl_final and not bloco.endswith(b"\n"):
            bloco += b"\n"
        saida.append(bloco)
    return b"".join(saida)


def _formatar_erro_leitura(res: dict[str, Any], *, rotulo: str, offset: Any, linhas: Any) -> tuple[int, str]:
    rc = int(res.get("exit_code") or 2)
    msg = str(res.get("erro") or res.get("falta") or res.get("motivo") or "falha na leitura")
    if msg == "offset além do fim":
        total = res.get("bytes_total", 0)
        return 2, f"{rotulo}: --offset {offset} passa do fim ({total} bytes)\n"
    if msg == "faixa além do fim":
        total_l = res.get("linhas_total")
        det = f" ({total_l} linhas)" if total_l is not None else ""
        return 2, f"{rotulo}: --linhas {linhas!r}: faixa além do fim{det}\n"
    return rc, f"{rotulo}: {msg}\n"


def ler_conteudo_verbo(
    *,
    caminho: Path | str | None = None,
    dados: bytes | None = None,
    **opcoes_verbo: Any,
) -> tuple[int, bytes, str, dict[str, Any]]:
    """Executa a leitura pelo núcleo `lib/leitura` e devolve `(exit_code, stdout_bytes, stderr_str, meta)`."""
    rotulo_erro = str(opcoes_verbo.get("rotulo_erro") or "ler")
    linhas = opcoes_verbo.get("linhas")
    offset = opcoes_verbo.get("offset")
    max_bytes = opcoes_verbo.get("max_bytes")
    inteiro = bool(opcoes_verbo.get("inteiro", True)) and max_bytes is None
    numerar = bool(opcoes_verbo.get("numerar", False))
    nome_memoria = str(opcoes_verbo.get("nome_memoria") or "conteudo.txt")

    opcoes_nucleo: dict[str, Any] = {
        "linhas": linhas,
        "offset": offset,
        "max_bytes": max_bytes,
        "inteiro": inteiro,
    }
    caminho_logico = opcoes_verbo.get("caminho_logico")
    if caminho_logico is not None and eh_segredo(caminho_logico):
        return _recusa_vedada(caminho_logico)

    if caminho is not None:
        if eh_segredo(caminho):
            return _recusa_vedada(caminho)
        res = le(Path(caminho), **opcoes_nucleo)
    elif dados is not None:
        res = le_memoria(dados, nome=nome_memoria, **opcoes_nucleo)
    else:
        return 2, b"", f"{rotulo_erro}: informe --arquivo ou --stdin\n", {}

    if "erro" in res or res.get("recusado"):
        rc, err_msg = _formatar_erro_leitura(res, rotulo=rotulo_erro, offset=offset, linhas=linhas)
        return rc, b"", err_msg, res

    conteudo = str(res.get("conteudo") or "")
    if not numerar:
        return 0, conteudo.encode(), "", res

    faixa_res = res.get("linhas")
    ini_l = (
        int(faixa_res[0])
        if isinstance(faixa_res, list) and faixa_res and isinstance(faixa_res[0], int)
        else int(res.get("linha_inicio") or 1)
    )
    corpo_b = _formatar_numerado(conteudo, ini_l, garantir_nl_final=bool(linhas))
    return 0, corpo_b, "", res


def _aplicar_flag_simples(ped: _CliPedido, tok: str) -> bool:
    if tok == "--stdin":
        ped.usar_stdin = True
        return True
    if tok == "--validar-opcoes":
        ped.validar_opcoes = True
        return True
    if tok == "--inteiro":
        ped.inteiro = True
        return True
    if tok in ("--numerar", "-n"):
        ped.numerar = True
        return True
    return False


def _aplicar_flag_numerica(ped: _CliPedido, tok: str, valor: str | None) -> str | None:
    minimo = 0 if tok == "--offset" else 1
    if valor is None:
        return f"{ped.rotulo}: {tok} pede um número de bytes (>= {minimo})\n"
    parsed = _parse_int_nao_negativo(valor, tok, ped.rotulo, minimo=minimo)
    if isinstance(parsed, tuple):
        return parsed[1]
    if tok == "--offset":
        ped.offset = parsed
    else:
        ped.max_bytes = parsed
        ped.inteiro = False
    return None


def _aplicar_flag_valor(ped: _CliPedido, tok: str, valor: str | None) -> str | None:
    if tok == "--arquivo":
        if valor is None:
            return f"{ped.rotulo}: --arquivo exige caminho\n"
        ped.caminho = valor
        return None
    if tok == "--caminho-logico":
        if valor is None:
            return f"{ped.rotulo}: --caminho-logico exige caminho\n"
        ped.caminho_logico = valor
        return None
    if tok == "--checar-vedado":
        if valor is None:
            return f"{ped.rotulo}: --checar-vedado exige caminho\n"
        ped.checar_vedado = valor
        return None
    if tok == "--rotulo":
        if valor is None:
            return "ler: --rotulo exige valor\n"
        ped.rotulo = valor
        return None
    if tok == "--linhas":
        if not valor:
            return f"{ped.rotulo}: --linhas exige uma faixa (ex.: 1-25, 10-, -20)\n"
        ped.linhas = valor
        return None
    if tok in ("--offset", "--max-bytes"):
        return _aplicar_flag_numerica(ped, tok, valor)
    return f"{ped.rotulo}: opção desconhecida: {tok}\n"


def _interpretar_argv(args: list[str]) -> _CliPedido | tuple[int, str]:
    ped = _CliPedido()
    i = 0
    _FLAGS_VALOR = (
        "--arquivo",
        "--caminho-logico",
        "--checar-vedado",
        "--rotulo",
        "--linhas",
        "--offset",
        "--max-bytes",
    )
    while i < len(args):
        tok = args[i]
        if _aplicar_flag_simples(ped, tok):
            i += 1
            continue
        valor = args[i + 1] if (i + 1 < len(args) and tok in _FLAGS_VALOR) else None
        err = _aplicar_flag_valor(ped, tok, valor)
        if err is not None:
            return 2, err
        i += 2
    return ped


def _validar_cli(ped: _CliPedido) -> int:
    res = _valida_opcoes(
        Path(ped.caminho or "memoria.txt"),
        {
            "linhas": ped.linhas,
            "offset": ped.offset,
            "max_bytes": ped.max_bytes,
            "inteiro": bool(ped.inteiro and ped.max_bytes is None),
        },
    )
    if isinstance(res, dict):
        msg = str(res.get("erro") or res.get("falta") or "opções inválidas")
        sys.stderr.write(f"{ped.rotulo}: {msg}\n")
        return int(res.get("exit_code") or 2)
    return 0


def main(argv: list[str] | None = None) -> int:
    parsed = _interpretar_argv(list(sys.argv[1:] if argv is None else argv))
    if isinstance(parsed, tuple):
        sys.stderr.write(parsed[1])
        return parsed[0]
    if parsed.checar_vedado is not None:
        if eh_segredo(parsed.checar_vedado):
            rc, _, err_s, _ = _recusa_vedada(parsed.checar_vedado)
            sys.stderr.write(err_s)
            return rc
        return 0
    if parsed.validar_opcoes:
        return _validar_cli(parsed)
    dados = sys.stdin.buffer.read() if parsed.usar_stdin else None
    rc, corpo_b, err_s, _ = ler_conteudo_verbo(
        caminho=parsed.caminho,
        caminho_logico=parsed.caminho_logico,
        dados=dados,
        linhas=parsed.linhas,
        offset=parsed.offset,
        max_bytes=parsed.max_bytes,
        inteiro=parsed.inteiro,
        numerar=parsed.numerar,
        rotulo_erro=parsed.rotulo,
    )
    if err_s:
        sys.stderr.write(err_s)
    if rc == 0 and corpo_b:
        sys.stdout.buffer.write(corpo_b)
        sys.stdout.buffer.flush()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
