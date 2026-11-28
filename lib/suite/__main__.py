"""Ponto de entrada da peça suite."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

USO = """uso:
  suite medir <componente> [--arvore <caminho>] [--json]
  suite selecionar <componente> [--arvore <caminho>] [--ampliado]
  suite admitir [<arvore>]
  suite consultar <componente|stack|momento|soltos> [<alvo>] [--arvore <caminho>] [--json]
  suite rodar [<alvo>] [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--json]
  suite veredito [<alvo>] [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--json]
  suite portao <repositorio> [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--gravar-fichas] [--json]
  suite laudo <chave>... --arvore <caminho> [--alvo <alvo>] [--prazo <segundos>] --json

Atos da peça suite:
  medir       muta o código exercitado do componente e lista os casos cegos
  selecionar  roda os testes do componente na fita
  admitir     ensaia as fichas de verificação e confere o vínculo na admissão
  consultar   mostra o que cada teste protege, quando roda e o alvo encerrado
  rodar       roda a seleção da esteira em ambiente isolado e grava o veredito
  veredito    lê o veredito gravado para o repositório ou par de árvores
  portao      cobra o veredito verde do par de árvores ao integrar na main e grava as fichas
  laudo       julga duas ou mais fichas de teste no motor da suíte e imprime o laudo em JSON
"""

SAIDA_USO = 2
SAIDA_INDETERMINAVEL = 5
PRAZO_PADRAO_LAUDO_S = 300.0
REGRA_LAUDO = "ato:verificar §Qual é a forma e a regra de unidade da chamada?"


def _veredito_como_dict(v: Any) -> dict[str, Any]:
    return {
        "alvo": v.alvo,
        "quesito": v.quesito,
        "resultado": v.resultado,
        "constatacao": v.constatacao,
        "modo": v.modo,
        "motor": v.motor,
        "versao_servico": v.versao_servico,
        "casos_total": v.casos_total,
        "casos_quarentena": v.casos_quarentena,
        "apontamentos": [a.como_dict() for a in v.apontamentos],
    }


def _carregar_executor_duble_env() -> Any:
    caminho_raw = (os.environ.get("PF_SUITE_DUBLE_JSON") or "").strip()
    if not caminho_raw:
        return None
    from suite.esteira import DubleExecutorIsolado

    cfg = json.loads(Path(caminho_raw).read_text(encoding="utf-8"))
    atraso_s = float(cfg.get("atraso_s") or 0.0)
    casos = {str(k): bool(v) for k, v in dict(cfg.get("casos") or {}).items()}
    duble = DubleExecutorIsolado(casos)
    if atraso_s <= 0:
        return duble

    def _com_atraso(raiz: Path, selecionados: list[str]) -> dict[str, Any]:
        time.sleep(atraso_s)
        return duble(raiz, selecionados)

    return _com_atraso


def main_laudo(argv: Sequence[str]) -> int:
    """Executa `suite laudo <chave>... --arvore <caminho> [--alvo <alvo>] [--prazo <s>] --json`."""
    from suite.executor import OpcoesExecucaoTeste
    from suite.motor import ErroLaudoSuite, julgar_laudo

    parser = argparse.ArgumentParser(prog="suite laudo", add_help=False)
    parser.add_argument("chaves", nargs="+")
    parser.add_argument("--arvore", required=True)
    parser.add_argument("--alvo", default="")
    parser.add_argument("--prazo", type=float, default=PRAZO_PADRAO_LAUDO_S)
    parser.add_argument("--json", action="store_true", dest="como_json")
    try:
        ns = parser.parse_args(list(argv))
    except SystemExit:
        sys.stderr.write(USO)
        return SAIDA_USO

    if not ns.como_json:
        sys.stderr.write("suite laudo: informe --json\n")
        return SAIDA_USO

    opcoes = OpcoesExecucaoTeste(
        alvo=str(ns.alvo or ""),
        executor_isolado=_carregar_executor_duble_env(),
        prazo_s=float(ns.prazo),
        ficha_confirmada=True,
    )
    try:
        laudo = julgar_laudo(ns.chaves, Path(ns.arvore), opcoes=opcoes)
    except ErroLaudoSuite as exc:
        if exc.saida == SAIDA_INDETERMINAVEL and exc.vereditos_parciais:
            parciais = {"vereditos_parciais": [_veredito_como_dict(v) for v in exc.vereditos_parciais]}
            sys.stdout.write(json.dumps(parciais, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        erro_json = {
            "codigo": exc.codigo,
            "onde": "suite-de-testes",
            "recebido": ", ".join(ns.chaves),
            "regra": REGRA_LAUDO,
            "cura": exc.detalhe,
            "proximo": "",
        }
        sys.stderr.write(json.dumps(erro_json, ensure_ascii=False) + "\n")
        sys.stderr.flush()
        return exc.saida

    corpo = {
        "alvo": laudo.alvo,
        "resultado": laudo.resultado,
        "constatacao": laudo.constatacao,
        "motor": laudo.motor,
        "versao_motor": laudo.versao_motor,
        "vereditos": [_veredito_como_dict(v) for v in laudo.vereditos],
    }
    sys.stdout.write(json.dumps(corpo, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0


def _rotas_suite() -> dict[str, Callable[[list[str]], int]]:
    from suite.admissao import main as admitir_main
    from suite.consulta import main as consultar_main
    from suite.esteira import main_rodar, main_veredito
    from suite.mutacao import main as medir_main
    from suite.portao import main as portao_main
    from suite.selecao import main as selecionar_main

    return {
        "medir": medir_main,
        "selecionar": selecionar_main,
        "admitir": admitir_main,
        "consultar": consultar_main,
        "rodar": main_rodar,
        "veredito": main_veredito,
        "portao": portao_main,
        "laudo": main_laudo,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help", "ajuda"):
        sys.stdout.write(USO)
        return 0
    ato, resto = args[0], args[1:]
    rota = _rotas_suite().get(ato)
    if rota is None:
        sys.stderr.write(f"suite: ato desconhecido '{ato}'\n\n{USO}")
        return SAIDA_USO
    return rota(resto)


if __name__ == "__main__":
    raise SystemExit(main())
