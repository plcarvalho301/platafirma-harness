"""Todo `.py` do ops-server compila — o portao que faltava antes de promover a porta.

A porta e a mao que sobe o resto e a unica que o dono tem no host: `release promover`
reinicia o servico, e um erro de sintaxe em `server.py` derruba justamente quem faria o
`release reverter`. O `_ensaio.py` nao serve de portao aqui: so importa no venv do
ops-server (depende de `mcp`) e manda recado real ao importar. `compile()` nao importa
nada — le o fonte e falha na sintaxe, que e o que se quer saber antes do restart.

Nascido em 18/09, quando uma edicao de `server.py` subiu a main sem verificacao por
maquina: `lint` detecta o repo como stack bash e nao olha o Python.
"""
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parent.parent / "ops-server"
_FONTES = sorted(_OPS.rglob("*.py"))


def test_ha_fonte_para_conferir():
    assert _FONTES, f"nenhum .py sob {_OPS} — o portao estaria verde por vazio"


@pytest.mark.parametrize("fonte", _FONTES, ids=lambda p: str(p.relative_to(_OPS)))
def test_compila(fonte):
    compile(fonte.read_text(encoding="utf-8"), str(fonte), "exec")
