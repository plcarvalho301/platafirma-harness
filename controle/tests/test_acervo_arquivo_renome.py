"""`acervo ler biblioteca objeto` virou `acervo ler biblioteca arquivo` (arq:0108 §10; ordem do dono em 18/10/2026,
comentário #3015 da #3761): o arquivo da obra nunca se chama «objeto», também em ato de verbo. O nome velho
recusa com exit 2 e nomeia o novo."""
from __future__ import annotations

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin" / "acervo"


def _roda(*args):
    return subprocess.run([str(BIN), *args], capture_output=True, text=True)


def test_o_nome_velho_recusa_com_exit_2_e_nomeia_o_novo():
    r = _roda("ler", "biblioteca", "objeto", "qualquer-obra")
    assert r.returncode == 2
    assert "acervo ler biblioteca arquivo" in r.stderr and "nunca se chama" in r.stderr
    assert r.stdout == ""


def test_o_uso_e_o_roteamento_dizem_arquivo_e_o_script_tambem():
    texto = BIN.read_text(encoding="utf-8")
    assert "acervo ler      biblioteca arquivo <uuid|prefixo|titulo>" in texto
    assert "ler:biblioteca:arquivo)" in texto
    script = (RAIZ / "bin" / "_acervo" / "objeto").read_text(encoding="utf-8")
    assert "uso: acervo ler biblioteca arquivo" in script
    assert "uso: acervo ler biblioteca objeto" not in script


def test_o_baixar_aponta_o_ato_novo():
    texto = BIN.read_text(encoding="utf-8")
    assert 'acervo ler biblioteca arquivo \\"<titulo>\\"' in texto
    assert 'acervo ler biblioteca objeto \\"<titulo>\\"' not in texto
