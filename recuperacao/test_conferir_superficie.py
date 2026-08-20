"""Testes de aceite do conferir superficie --caso descricao (#2305).

Aceite (executável por terceiro):
1. `conferir superficie --caso descricao` sai 0 quando servido == índice.
2. Reprovando de propósito, os dois lados: linha a mais na tabela sai 1 nomeando a fonte
   que só está no índice; fonte servida e fora da tabela sai 1 nomeando o outro lado.
3. Tabela vazia: exit 0, saída diz "não medido" e o motivo, e o --json traz o campo.
4. `conferir superficie` sem --caso: veredito de hoje inalterado, incluindo o exit code.
5. Linha no tool-manifest/TI.md no MESMO commit — verbo não indexado é verbo inexistente.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CONFERIR_PATH = Path(__file__).resolve().parent.parent / "bin" / "conferir"


def _carregar_conferir():
    loader = importlib.machinery.SourceFileLoader("conferir_cli_test", str(CONFERIR_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


conferir_mod = _carregar_conferir()
conferir_superficie_descricao = conferir_mod.conferir_superficie_descricao

DESC_6_FONTES = """Recupera estado da plataforma consultando fontes declaradas.
Fontes disponíveis:
- board (exata): capacidade trabalho, dono claudinho-TI — HTTP do rastreador + header de identidade
- fila (exata): capacidade mensagem, dono claudinho-TI — XINFO STREAM · XRANGE no motor-msg
- mesa (exata): capacidade memoria, dono claudinho-IA — mapa por chave (arq:0062)
- registro (exata): capacidade decisao, dono claudinha-gestao-estrategica — decisions/INDICE.md, mantido na escrita
- wiki (exata): capacidade conhecimento, dono claudinho-dados — API do MediaWiki
- acervo (semantica): capacidade conhecimento, dono claudinho-dados — API do rag"""


def test_conferir_superficie_caso_descricao_sucesso(capsys):
    """Prova 1: Sai 0 quando servido == índice."""
    rc = conferir_superficie_descricao(descricao_fornecida=DESC_6_FONTES)
    out, _ = capsys.readouterr()
    assert rc == 0
    assert "veredito         : em dia" in out
    assert "só no índice     : 0" in out
    assert "só no servido    : 0" in out


def test_conferir_superficie_caso_descricao_json_sucesso(capsys):
    """Prova 1b: Saída JSON estruturada em dia."""
    rc = conferir_superficie_descricao(descricao_fornecida=DESC_6_FONTES, como_json=True)
    out, _ = capsys.readouterr()
    assert rc == 0
    d = json.loads(out)
    assert d["caso"] == "descricao"
    assert d["veredito"] == "em dia"
    assert d["so_no_indice"] == []
    assert d["so_no_servido"] == []
    assert sorted(d["slugs_indice"]) == ["acervo", "board", "fila", "mesa", "registro", "wiki"]
    assert sorted(d["slugs_servidos"]) == ["acervo", "board", "fila", "mesa", "registro", "wiki"]


def test_reprovando_linha_a_mais_na_tabela_so_no_indice(capsys):
    """Prova 2a: Fonte a mais no índice sai 1 nomeando o que só está no índice."""
    desc_5 = """Recupera estado da plataforma consultando fontes declaradas.
Fontes disponíveis:
- board (exata): capacidade trabalho, dono claudinho-TI — HTTP
- fila (exata): capacidade mensagem, dono claudinho-TI — stream
- mesa (exata): capacidade memoria, dono claudinho-IA — postgres
- registro (exata): capacidade decisao, dono claudinha-gestao-estrategica — git
- acervo (semantica): capacidade conhecimento, dono claudinho-dados — HTTP"""

    rc = conferir_superficie_descricao(descricao_fornecida=desc_5)
    out, _ = capsys.readouterr()
    assert rc == 1
    assert "veredito         : divergente" in out
    assert "SÓ NO ÍNDICE     : 1 (wiki)" in out


def test_reprovando_fonte_a_mais_no_servido_so_no_servido(capsys):
    """Prova 2b: Fonte a mais no servido sai 1 nomeando o que só está no servido."""
    desc_7 = """Recupera estado da plataforma consultando fontes declaradas.
Fontes disponíveis:
- board (exata): capacidade trabalho, dono claudinho-TI — HTTP
- fila (exata): capacidade mensagem, dono claudinho-TI — stream
- mesa (exata): capacidade memoria, dono claudinho-IA — postgres
- registro (exata): capacidade decisao, dono claudinha-gestao-estrategica — git
- wiki (exata): capacidade conhecimento, dono claudinho-dados — HTTP
- acervo (semantica): capacidade conhecimento, dono claudinho-dados — HTTP
- cofre (exata): capacidade seguranca, dono claudinho-seguranca — vault"""

    rc = conferir_superficie_descricao(descricao_fornecida=desc_7)
    out, _ = capsys.readouterr()
    assert rc == 1
    assert "veredito         : divergente" in out
    assert "SÓ NO SERVIDO    : 1 (cofre)" in out


def test_tabela_vazia_sai_nao_medido_exit_0(capsys):
    """Prova 3: Tabela vazia sai exit 0 como NÃO MEDIDO declarado, com campo no json."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as tmp:
        tmp.write("## Outra secao\n\nsem tabela de fontes\n")
        tmp_path = tmp.name

    try:
        rc = conferir_superficie_descricao(caminho_catalogo=tmp_path, descricao_fornecida=DESC_6_FONTES)
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "NAO MEDIDO" in out
        assert "veredito  : nao-medido" in out

        rc_json = conferir_superficie_descricao(caminho_catalogo=tmp_path, descricao_fornecida=DESC_6_FONTES, como_json=True)
        out_json, _ = capsys.readouterr()
        assert rc_json == 0
        d = json.loads(out_json)
        assert d["caso"] == "descricao"
        assert d["veredito"] == "nao-medido"
        assert "motivo" in d
        assert d["slugs_indice"] == []
    finally:
        os.unlink(tmp_path)


def test_conferir_superficie_sem_caso_preserva_comportamento():
    """Prova 4: conferir superficie sem --caso tem veredito e exit code de conectores."""
    p = subprocess.run([sys.executable, str(CONFERIR_PATH), "superficie", "--json"], capture_output=True, text=True)
    assert p.returncode == 0
    d = json.loads(p.stdout)
    assert "veredito" in d
    assert d["veredito"] in ("em dia", "divergente")
    assert "conector_prometido_nao_servido" in d
