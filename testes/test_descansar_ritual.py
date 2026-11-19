"""Contrato do texto do ritual de fim de fita (`descansar fita`, passo 2b) — card #3220.

O passo 2b mandava gravar o episodio de ferramenta no caderno do chapeu (diario de bordo);
o parecer 2026-10-01-caderno mediu 77 de 95 entradas de caderno como diario. Agora o
contorno vai a rotina Triar (debito tecnico, `tarefas dt`) e o caderno nao ganha diario.

O texto e lido do fonte por AST: o verbo importa redis e mede o ar ao rodar, e o que se
fixa aqui e so o que o ritual MANDA fazer.
"""

from __future__ import annotations

import ast
from pathlib import Path

VERBO = Path(__file__).resolve().parents[1] / "bin" / "descansar"


def _ritual() -> str:
    arvore = ast.parse(VERBO.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Call) and getattr(no.func, "id", None) == "print"
                and no.args and isinstance(no.args[0], ast.Constant)
                and isinstance(no.args[0].value, str)
                and "== proximo passo ==" in no.args[0].value):
            return no.args[0].value
    raise AssertionError("o ritual (== proximo passo ==) sumiu de bin/descansar")


def _passo_2b(texto: str) -> str:
    ini = texto.index("2b.")
    return texto[ini:texto.index("\n3. ", ini)]


def test_2b_manda_o_contorno_ao_debito_tecnico():
    p = _passo_2b(_ritual())
    assert "Triar" in p
    assert "tarefas dt admitir" in p
    assert "tarefas dt listar" in p and "#2856 linha" in p, "ja na lista: cita a linha"


def test_2b_nao_manda_mais_gravar_diario_no_caderno():
    texto = _ritual()
    p = _passo_2b(texto)
    assert "2b. diario de bordo" not in texto
    assert "contorno encontrado NA DATA" not in texto, "o formato fixo do diario saiu"
    assert "entra cru, no caderno" not in texto
    assert "nunca por `descansar publicar`" in p.lower().replace("\n   ", " ")


def test_resto_do_ritual_intacto():
    texto = _ritual()
    assert "2a. conhecimento curado" in texto
    assert "triagem da memoria" not in texto, "a triagem da memoria saiu do roteiro (debito 654)"
    assert "3. encerramento" in texto
    assert "descansar encerrar" in texto and "descansar fita --encerra-sessao" in texto


# ---------------------------------------------------------------- #3217 / DTs 885, 889: publicar no banco de eventos
def _passo(texto: str, ini: str, fim: str) -> str:
    i = texto.index(ini)
    return texto[i:texto.index(fim, i)]


def test_2a_aponta_descansar_publicar_com_esquema_json_e_chaves_do_fichario():
    p = _passo(_ritual(), "2a.", "2b.")
    assert "descansar publicar" in p
    for campo in ("enunciado", "destinatario", "tipo-de-mensagem", "etiqueta", "<classe>:<slug>"):
        assert campo in p, f"esquema JSON sem {campo}"
    assert "mesa escrever <chapeu>" not in p, "mesa escrever fechou na story 4355 (DT 885/889)"
    assert "mesa substituir" not in p
    assert "guia\n   registrar" in p or "guia registrar" in p
    # #4377: sessao.caderno_* e bot caderno-poda encerrados; exemplos alinhados a chaves.json
    for obsoleto in ("caderno-poda", "mesa caderno", "mesa legado", "mesa tombar", "a revisar",
                     "chapeu:<cadeira>/<chapeu>", "persona:ia", "chapeu:ia/busca"):
        assert obsoleto not in p, f"texto obsoleto pos-S4377: {obsoleto}"
    for valido in ("chapeu:<chapeu>", "capacidade:busca", "chapeu:busca"):
        assert valido in p, f"exemplo valido do fichario ausente: {valido}"
    assert "seis\n   heuristicas" not in p and "historico e o git" not in p, "a arq:0072 saiu"


def test_2c_marca_a_aresta_por_descansar_publicar_so_do_que_entrou_na_resposta():
    p = _passo(_ritual(), "2c.", "\n3. ")
    assert "descansar publicar" in p and "etiqueta" in p and "<classe>:<slug>" in p
    assert "mesa aresta <chapeu>" not in p, "mesa aresta fechou na story 4355 (DT 889)"
    assert "#2947" in p and "puxado de fora da cadeira" in p


# ---------------------------------------------------------------- debito 654 / DT 896: encerramento no mesmo ato
def _corrido(p: str) -> str:
    return " ".join(p.split())


def test_3_encerra_no_mesmo_ato_sem_pergunta_no_fecho():
    p = _corrido(_passo(_ritual(), "\n3. ", "segundo caminho de morte"))
    assert "descansar fita" in p and "descansar encerrar" in p and "no mesmo ato" in p
    assert "sem perguntar nada no fecho" in p
    assert "limpo?" not in _ritual() and "NAO rode o passo" not in _ritual()


# ---------------------------------------------------------------- debito 423: a mesa so com repasse
def test_1_planta_item_so_com_repasse_e_o_descanso_nao_le_a_caixa():
    p = _corrido(_passo(_ritual(), "1. ", "\n2. "))
    assert "item so quando a fita deixa pendurado" in p and "mesa sem item" in p
    # dono, 17/11/2026: o descanso encerra a fita, nao a interpreta; a caixa saiu inteira
    assert "fila" not in _ritual() and "cartas" not in _ritual().lower()
    assert "escreva a mesa antes de a fita morrer" not in p


def test_a_mesa_do_passo_1_e_item_nao_prosa():
    p = _passo(_ritual(), "1. ", "\n2. ")
    assert "mesa item <chapeu>" in p and "mesa anota" not in p
