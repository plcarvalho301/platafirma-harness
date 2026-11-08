"""DT 512 — `busca` falhava com «unhashable type: 'list'» quando o JSON do motor trazia campo lista.

`_lava_json_motor` testava `v in {None, False}` em todo campo de `fontes` e de `contexto`, e um campo
lista ou dicionario (ex.: `conceitos`, `breadcrumb` em lista) derrubava a poda inteira, depois de a
busca ter dado certo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
if str(OPS_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(OPS_SERVER_DIR))

import poda  # noqa: E402


def _json(fontes, contexto=None):
    d = {"fontes": fontes}
    if contexto is not None:
        d["contexto"] = contexto
    return json.dumps(d, ensure_ascii=False)


def test_campo_lista_em_fonte_nao_derruba_a_poda():
    fonte = {"obra": "o", "trecho": "t", "conceitos": ["a", "b"], "rerank": None, "codigo_exato": False}
    saida, mudou = poda._lava_json_motor(_json([fonte]))
    assert mudou
    f = json.loads(saida)["fontes"][0]
    assert f["conceitos"] == ["a", "b"]                 # a lista fica
    assert "rerank" not in f and "codigo_exato" not in f  # o que era constante sai, como antes


def test_campo_dicionario_em_fonte_nao_derruba_a_poda():
    fonte = {"obra": "o", "trecho": "t", "meta": {"k": 1}, "rerank": None}
    saida, _ = poda._lava_json_motor(_json([fonte]))
    assert json.loads(saida)["fontes"][0]["meta"] == {"k": 1}


def test_campo_lista_em_contexto_nao_derruba_a_poda():
    ctx = {"obra": "o", "vizinhos": ["x", "y"], "rerank": None}
    saida, mudou = poda._lava_json_motor(_json([{"obra": "o", "trecho": "t"}], [ctx]))
    assert mudou
    c = json.loads(saida)["contexto"][0]
    assert c["vizinhos"] == ["x", "y"] and "rerank" not in c


def test_lista_vazia_nao_e_constante():
    saida, _ = poda._lava_json_motor(_json([{"obra": "o", "trecho": "t", "conceitos": [], "rerank": None}]))
    assert json.loads(saida)["fontes"][0]["conceitos"] == []


@pytest.mark.parametrize("v,esperado", [(None, True), (False, True), (0, True), ("", False), ("x", False),
                                         (1, False), ([], False), ({}, False), (["a"], False)])
def test_eh_constante_json(v, esperado):
    assert poda._eh_constante_json(v) is esperado


def test_lava_inteira_com_campo_lista():
    texto = _json([{"obra": "o", "trecho": "t " * 50, "conceitos": ["a"], "rerank": None}])
    lavado, rel = poda.lava(texto, cosmetica=True)
    assert "conceitos" in lavado
