"""O gate da §16.5 da spec ler-arquivo: roda o bench, imprime o relatório e falha listando os
critérios reprovados. Sai 0 ou sai 1, sem julgamento; limite mudado sem emenda não vale."""
from __future__ import annotations

import bench_leitura


def test_bench_leitura(capsys):
    r = bench_leitura.rodar()
    with capsys.disabled():                      # o relatório vai ao log do `teste`
        print()
        print(r["texto"])
    reprovados = [k for k in r["criterios"] if not k["passou"]]
    assert not reprovados, "critérios reprovados (spec ler-arquivo §16.5): " + "; ".join(
        f"{k['n']} ({k['descricao']}) — medido: {k['medido']}" for k in reprovados)
