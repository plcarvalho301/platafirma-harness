# componente: componente:verbo-pesquisar
"""O verbo pesquisar fica fora do ar por ordem do dono (27/11/2026).

Todo ato recusa com exit 4 e causa `verbo-suspenso`, antes de carregar o pacote `pesquisa`,
tocar a rede ou criar pasta de trabalho. O teste roda o executável de verdade, com a pasta de
pesquisa apontada para um diretório temporário, e confere que ela não nasce.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
VERBO = RAIZ / "bin" / "pesquisar"
ATOS = ("consultar", "resolver", "ler", "percorrer", "coletar", "historico",
        "manifesto", "exportar", "verificar", "saude", "--help")


@pytest.mark.parametrize("ato", ATOS)
def test_todo_ato_recusa_antes_de_rede_e_disco(ato, tmp_path):
    pasta = tmp_path / "pesquisa"
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "PF_PESQUISA_DIR": str(pasta)}
    r = subprocess.run([sys.executable, str(VERBO), ato, "https://example.org"],
                       capture_output=True, text=True, env=env, timeout=30)
    assert r.returncode == 4, r.stderr
    saida = json.loads(r.stdout)
    assert saida["ok"] is False
    assert saida["causa"] == "verbo-suspenso"
    assert saida["tipo"] == "dado"
    assert "fora do ar" in r.stderr
    assert not pasta.exists()
