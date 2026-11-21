# componente: componente:verbo-metrica
"""Contrato de `metrica abertura --tudo` e `--json` sem `--tudo` (card #3145)."""
from __future__ import annotations

import json

from test_contrato_metrica_abertura import _run, raiz  # noqa: F401


def test_abertura_tudo_json_lista_as_duas_cadeiras_com_pecas(raiz):  # noqa: F811
    proc = _run(["abertura", "--tudo", "--json"], raiz)
    assert proc.returncode == 0, proc.stderr
    dados = json.loads(proc.stdout)
    nomes = {c["total"]["cadeira"] for c in dados["cadeiras"]}
    assert nomes == {"teste", "outra"}
    for c in dados["cadeiras"]:
        assert c["pecas"] is not None
        assert len(c["pecas"]) == c["total"]["pecas"]


def test_abertura_json_sem_tudo_omite_pecas_por_cadeira(raiz):  # noqa: F811
    proc = _run(["abertura", "--json"], raiz)
    assert proc.returncode == 0, proc.stderr
    dados = json.loads(proc.stdout)
    assert len(dados["cadeiras"]) == 2
    assert all(c["pecas"] is None for c in dados["cadeiras"])
