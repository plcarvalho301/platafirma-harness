"""Linha de comando do ato escrever e do daemon escritor."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO, TextIO

from .escrita import OpcoesExecucao, executar_ato_escrever
from .pedido import desligar_core_dump, ler_stdin_limitado, ler_token_descritor
from .politica import carregar_politica
from .servidor import ServidorEscritor, montar_config_padrao
from .tipos import ContextoEscrita, ErroEscrita, RecusaEscrita, emitir_recusa

_MIN_ARGS_ATO = 2
_RE_NUMERO_POSITIVO = re.compile(r"^\d+(?:\.\d+)?$")


def _main_servidor(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="escrita servidor")
    parser.add_argument("--socket", type=Path, default=None)
    parser.add_argument("--wt", type=Path, default=None)
    parser.add_argument("--estado", type=Path, default=None)
    parser.add_argument("--release-link", type=Path, default=None)
    parser.add_argument("--pdp-dir", type=Path, default=None)
    ns = parser.parse_args(list(argv))
    cfg = montar_config_padrao(
        socket_path=ns.socket,
        raiz_bancadas=ns.wt,
        estado_dir=ns.estado,
        release_link=ns.release_link,
        pdp_dir=ns.pdp_dir,
    )
    srv = ServidorEscritor(cfg)
    return srv.servir(instalar_sinais=True)


def _prazo_ns_do_ambiente() -> int:
    bruto = (os.environ.get("PF_PRAZO_S") or "").strip()
    if not bruto or not _RE_NUMERO_POSITIVO.match(bruto):
        return 0
    valor = float(bruto)
    return time.monotonic_ns() + int(valor * 1_000_000_000) if valor > 0 else 0


def _ler_stdin_para_ato(
    forma: str, fluxo: BinaryIO | None, teto_bytes: int
) -> bytes | None:
    if forma in ("retirar", "restaurar"):
        return None
    if fluxo is None:
        return b""
    return ler_stdin_limitado(fluxo, teto_bytes)


def executar_cli(
    argv: Sequence[str],
    *,
    stdin: BinaryIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    socket_path: Path | None = None,
) -> int:
    """Executa a CLI das seis formas devolvendo exit_code e emitindo JSON único no erro."""
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    desligar_core_dump()
    if len(argv) < _MIN_ARGS_ATO:
        return emitir_recusa(
            RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="ato-nao-aceito",
                    onde="argv",
                    recebido=" ".join(argv),
                    regra="uso: escrita <verbo> <forma> [<classe>] <chave> [<versao>] [flags]",
                    cura="informe o verbo e uma das seis formas fechadas do ato escrever",
                    proximo="",
                )
            ),
            fluxo=err,
        )
    verbo = argv[0]
    resto = list(argv[1:])
    try:
        politica = carregar_politica()
        token = ler_token_descritor()
        stdin_bytes = _ler_stdin_para_ato(resto[0], stdin, politica.entrada_max_bytes)
        ctx = ContextoEscrita(
            verbo=verbo,
            cadeira=os.environ.get("PF_CADEIRA") or "",
            sujeito=os.environ.get("PF_SUJEITO") or "",
            sessao_id=os.environ.get("PF_SESSAO") or "",
            ordem_id=os.environ.get("PF_ORDEM_ID") or os.environ.get("PF_SESSAO") or "",
            card=os.environ.get("PF_CARD") or "",
            prazo_ns=_prazo_ns_do_ambiente(),
            token=token,
        )
        res = executar_ato_escrever(
            verbo,
            resto,
            stdin_bytes,
            opcoes=OpcoesExecucao(
                contexto=ctx,
                politica=politica,
                socket_path=socket_path,
            ),
        )
    except RecusaEscrita as exc:
        return emitir_recusa(exc, fluxo=err)

    if "--json" in resto:
        out.write(json.dumps(res.como_dict(), ensure_ascii=False) + "\n")
    else:
        out.write(res.primeira_linha() + "\n")
    out.flush()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Despacha o daemon (`servidor`) ou a CLI do ato escrever."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "servidor":
        return _main_servidor(args[1:])
    return executar_cli(args, stdin=sys.stdin.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
