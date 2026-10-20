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
    assert "NUNCA o\n   caderno" in p or "nunca o caderno" in p.lower().replace("\n   ", " ")


def test_resto_do_ritual_intacto():
    texto = _ritual()
    assert "2a. conhecimento curado" in texto
    assert "3. triagem da memoria do claude.ai" in texto
    assert "descansar fita --encerra-sessao" in texto


# ---------------------------------------------------------------- #3217: o caderno no banco
def _passo(texto: str, ini: str, fim: str) -> str:
    i = texto.index(ini)
    return texto[i:texto.index(fim, i)]


def test_2a_escreve_por_categoria_no_banco_e_a_poda_e_do_bot():
    p = _passo(_ritual(), "2a.", "2b.")
    for categoria in ("--licao", "--preferencia", "--premissa"):
        assert f"mesa escrever <chapeu> {categoria}" in p
    assert "--caso" in p and "--dito-em" in p and "--vale-ate" in p, "o campo de cada categoria"
    assert "guia\n   registrar" in p or "guia registrar" in p
    # #3884: a cadeira nao resolve nada antes de escrever; a poda e do bot, e a carta dele pede o tombamento
    assert "A poda nao e sua" in p and "a revisar" not in p, "a marca a revisar saiu (arq:0120, 19/10)"
    assert "mesa tombar <id> --destino" in p and "legado" in p, "lembra a carta do bot e o legado"
    assert "seis\n   heuristicas" not in p and "historico e o git" not in p, "a arq:0072 saiu"


def test_2c_marca_a_aresta_so_do_que_entrou_na_resposta():
    p = _passo(_ritual(), "2c.", "\n3. ")
    assert "mesa aresta <chapeu>" in p and "--para <ponta>" in p and "--para-que" in p
    assert "#2947" in p and "puxado de fora da cadeira" in p


# ---------------------------------------------------------------- #3930: a memoria do claude.ai
def test_3_cobre_as_duas_camadas_e_a_passada_automatica():
    p = _passo(_ritual(), "\n3. ", "\n4. ")
    assert "camada do Project" in p and "/projects/<id>/" in p
    assert "camada de conta" in p and "passada automatica" in p
    assert "REPETE-CONDUTA" in p and "SUBSTRATO" in p and "FOSSIL" in p and "TRATO" in p


def test_3_limpa_so_o_project_e_so_com_pedido_do_dono():
    p = _passo(_ritual(), "\n3. ", "\n4. ")
    assert "PORTAO" in p and "MENSAGEM DO DONO neste turno" in p
    assert "nunca se edita daqui" in p, "a conta nao se escreve da sessao do Project"
    assert "configuracao de memoria do Project" in p and "ato dele" in p, "a escolha do caminho e do dono"


def test_a_mesa_do_passo_1_e_item_nao_prosa():
    p = _passo(_ritual(), "1. ", "\n2. ")
    assert "mesa item <chapeu>" in p and "mesa anota" not in p
