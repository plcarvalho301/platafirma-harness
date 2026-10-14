"""Testes da borda das faces (card #3516). O self-check de borda.py é o grosso: nove recusas em 403 sem
chegar à porta, o que passa, o que o navegador não pode pôr e o envelope da porta. Aqui ele roda no portão,
e o cabeçalho real do verbo `motor` (o que a release serve) é lido pelo mesmo parser."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import borda  # noqa: E402

MOTOR = AQUI.parent / "bin" / "motor"
TOKEN = {"authorization": "Bearer a.b.c"}


def test_autoteste_da_borda(capsys):
    borda._autoteste()
    assert "borda OK (#3516)" in capsys.readouterr().out


def test_a_lista_de_atos_da_face_motor_e_a_do_cabecalho_do_verbo_real():
    atos = borda.Face("motor", verbo=str(MOTOR)).atos()
    assert set(atos) == {"buscar", "medir", "listar", "ajuste", "indexar", "trocar", "consultas", "trabalhos"}
    assert atos["ajuste"] == {"leitura", "escrita"}
    assert atos["trocar"] == {"escrita"} and atos["indexar"] == {"escrita"}
    assert atos["consultas"] == {"leitura"} and atos["trabalhos"] == {"leitura"}
    # a linha de exclusao (instrumento de medida da ia) nao tem face
    assert not {"sortear", "parear", "escrever", "julgar", "lintar", "eleger"} & set(atos)


def test_o_cabecalho_novo_do_verbo_vale_sem_reiniciar_a_borda(tmp_path):
    verbo = tmp_path / "motor"
    verbo.write_text("#!/bin/sh\n# atos: a (leitura, x), b (escrita, y)\n# face: a=motor\n", encoding="utf-8")
    face = borda.Face("motor", verbo=str(verbo))
    assert set(face.atos()) == {"a"}
    verbo.write_text("#!/bin/sh\n# atos: a (leitura, x), b (escrita, y)\n# face: a=motor\n# face: b=motor\n",
                     encoding="utf-8")
    assert set(face.atos()) == {"a", "b"}


def test_ato_declarado_na_face_sem_capacidade_fica_de_fora():
    assert borda.ler_cabecalho("# atos: a (leitura, x)\n# face: a=motor\n# face: b=motor\n") == {
        "motor": {"a": frozenset({"leitura"})}}


@pytest.mark.parametrize("env", [{}, {"BORDA_FACES": "nao e json"}, {"BORDA_FACES": '{"motor": {}}'}])
def test_configuracao_ilegivel_sobe_a_borda_sem_face_e_nada_passa(env, capsys):
    app = borda.criar_app(env)
    assert asyncio.run(borda._chamar(app, "GET", "/api/motor/buscar", TOKEN))[0] == 404


def test_a_lista_de_origens_e_a_configuracao_da_instancia():
    env = {"BORDA_FACES": json.dumps({"motor": {"verbo": str(MOTOR), "instancia": "rag"}}),
           "BORDA_ORIGENS": "https://a.exemplo, https://b.exemplo"}
    app = borda.criar_app(env)
    assert app.origens == ("https://a.exemplo", "https://b.exemplo")
    escrita = {"origin": "https://b.exemplo", "x-pf-tela": "1", "content-type": "application/json", **TOKEN}
    # a origem da lista passa pela recusa; a porta nao existe aqui, entao a chamada vira 502, nunca 403
    app._chamar = lambda token, tool, argumentos: (502, {"erro": "a porta está fora do ar"})
    assert asyncio.run(borda._chamar(app, "POST", "/api/motor/trocar", escrita, b"{}"))[0] == 502
    assert asyncio.run(borda._chamar(
        app, "POST", "/api/motor/trocar", {**escrita, "origin": "https://c.exemplo"}, b"{}"))[0] == 403
