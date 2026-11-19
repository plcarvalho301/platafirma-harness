"""Ponto de entrada da peça diagrama."""
import sys
from diagrama.lint import main as lint_main

USO = """uso:
  diagrama lint <plano>
  diagrama renderizar <fonte>
  diagrama checar <plano> <svg>
  diagrama conferir-plano <plano>
  diagrama conferir-figura <plano> <svg> <png>
  diagrama embutir <svg> <fonte> [<plano>]
  diagrama receita <svg> [--saida <dir>]

Atos da peça diagrama:
  lint              valida o plano contra o esquema e as regras estruturais
  renderizar        gera SVG e PNG a partir da fonte declarativa
  checar            executa checagem estrutural entre plano e SVG
  conferir-plano    executa lint e auditor de plano
  conferir-figura   executa checagem estrutural e crítico de figura
  embutir           guarda o plano e a fonte dentro do SVG da figura entregue
  receita           devolve o plano e a fonte guardados no SVG, para redesenhar
"""

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        print(USO)
        return 0
    ato = argv[0]
    resto = argv[1:]
    if ato == "lint":
        return lint_main(resto)
    elif ato == "renderizar":
        from diagrama.renderizar import main as renderizar_main
        return renderizar_main(resto)
    elif ato == "checar":
        from diagrama.checagem import main as checagem_main
        return checagem_main(resto)
    elif ato == "conferir-plano":
        from diagrama.juizes import main_plano
        return main_plano(resto)
    elif ato == "conferir-figura":
        from diagrama.juizes import main_figura
        return main_figura(resto)
    elif ato == "embutir":
        from diagrama.receita import main_embutir
        return main_embutir(resto)
    elif ato == "receita":
        from diagrama.receita import main_receita
        return main_receita(resto)
    else:
        print(f"diagrama: ato desconhecido '{ato}'\n\n{USO}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
