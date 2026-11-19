"""DT 771: `acervo extrato` lê campos CSV maiores que o limite padrão de 128 KB."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EXTRATO = RAIZ / "bin" / "_acervo" / "extrato"


def _mod():
    loader = importlib.machinery.SourceFileLoader("acervo_extrato", str(EXTRATO))
    spec = importlib.util.spec_from_loader("acervo_extrato", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_ler_csv_aceita_campo_maior_que_128kb():
    mod = _mod()
    campo_grande = "a" * 200_000
    dados = f'id,corpo\n1,"{campo_grande}"\n'
    linhas = mod.ler_csv(dados)
    assert len(linhas) == 2
    assert linhas[0] == ["id", "corpo"]
    assert linhas[1] == ["1", campo_grande]


def test_limpa_remove_caracteres_de_controle_proibidos():
    mod = _mod()
    assert mod.limpa("ok\x00\x0b\x1f\t\n\r") == "ok\t\n\r"
