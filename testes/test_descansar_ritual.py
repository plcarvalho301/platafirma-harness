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
    assert "3. triagem da memoria do Project" in texto
    assert "descansar fita --encerra-sessao" in texto
