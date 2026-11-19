"""Ponto de entrada da peça suite."""
from __future__ import annotations

import sys

USO = """uso:
  suite medir <componente> [--arvore <caminho>] [--json]
  suite selecionar <componente> [--arvore <caminho>] [--ampliado]
  suite admitir [<arvore>]
  suite consultar <componente|stack|momento|soltos> [<alvo>] [--arvore <caminho>] [--json]
  suite rodar [<alvo>] [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--json]
  suite veredito [<alvo>] [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--json]
  suite portao <repositorio> [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--gravar-fichas] [--json]

Atos da peça suite:
  medir       muta o código exercitado do componente e lista os casos cegos
  selecionar  roda os testes do componente na fita
  admitir     ensaia as fichas de verificação e confere o vínculo na admissão
  consultar   mostra o que cada teste protege, quando roda e o alvo encerrado
  rodar       roda a seleção da esteira em ambiente isolado e grava o veredito
  veredito    lê o veredito gravado para o repositório ou par de árvores
  portao      cobra o veredito verde do par de árvores ao integrar na main e grava as fichas
"""


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        sys.stdout.write(USO)
        return 0
    ato = argv[0]
    resto = argv[1:]
    if ato == "medir":
        from suite.mutacao import main as medir_main

        return medir_main(resto)
    if ato == "selecionar":
        from suite.selecao import main as selecionar_main

        return selecionar_main(resto)
    if ato == "admitir":
        from suite.admissao import main as admitir_main

        return admitir_main(resto)
    if ato == "consultar":
        from suite.consulta import main as consultar_main

        return consultar_main(resto)
    if ato == "rodar":
        from suite.esteira import main_rodar

        return main_rodar(resto)
    if ato == "veredito":
        from suite.esteira import main_veredito

        return main_veredito(resto)
    if ato == "portao":
        from suite.portao import main as portao_main

        return portao_main(resto)
    sys.stderr.write(f"suite: ato desconhecido '{ato}'\n\n{USO}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
