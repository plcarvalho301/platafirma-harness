"""Testes unitários para U10 (ingerir: resumo, saída, exit codes e sha256) (#4120)."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from importlib.machinery import SourceFileLoader
import importlib.util

HARNESS_DIR = Path(__file__).resolve().parents[2]
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

# Mock requests caso o ambiente de teste de controle não o possua
if "requests" not in sys.modules:
    sys.modules["requests"] = MagicMock()

# Import bin/ingerir (arquivo sem extensão .py)
ingerir_path = HARNESS_DIR / "bin" / "ingerir"
loader = SourceFileLoader("ingerir_mod", str(ingerir_path))
spec = importlib.util.spec_from_loader("ingerir_mod", loader)
ingerir_mod = importlib.util.module_from_spec(spec)
loader.exec_module(ingerir_mod)

calcular_sha256_pasta = ingerir_mod.calcular_sha256_pasta
formatar_resumo_veredito_e_excecoes = ingerir_mod.formatar_resumo_veredito_e_excecoes
formatar_tabela_plano = ingerir_mod.formatar_tabela_plano


def test_calcular_sha256_pasta():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        (d / "sub").mkdir()
        (d / "a.txt").write_text("conteudo a", encoding="utf-8")
        (d / "sub" / "b.txt").write_text("conteudo b", encoding="utf-8")

        sha1 = calcular_sha256_pasta(str(d))
        assert len(sha1) == 64

        # Determinístico
        sha2 = calcular_sha256_pasta(str(d))
        assert sha1 == sha2

        # Modificação de arquivo altera o sha256
        (d / "sub" / "b.txt").write_text("conteudo b alterado", encoding="utf-8")
        sha3 = calcular_sha256_pasta(str(d))
        assert sha3 != sha1


def test_formatar_resumo_veredito_e_excecoes_sem_excecoes():
    lote = {
        "id": "lote-123",
        "autor": "devops",
        "motor": "rag",
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 2, "edicao": 0, "ja_ingerido": 0, "bloqueada": 0, "reprovado": 0},
        "itens": [
            {"posicao": 1, "arquivo": "doc1.pdf", "veredito": "criar", "portoes": []},
            {"posicao": 2, "arquivo": "doc2.pdf", "veredito": "criar", "portoes": []},
        ],
    }
    texto = formatar_resumo_veredito_e_excecoes(lote, fase="plano")
    assert "Plano de Ingestão: lote lote-123" in texto
    assert "total=2 | criar=2" in texto
    assert "Exceções e recusas:" not in texto


def test_formatar_resumo_veredito_e_excecoes_com_excecoes_e_recusa():
    lote = {
        "id": "lote-456",
        "autor": "devops",
        "motor": "rag",
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 1, "edicao": 0, "ja_ingerido": 1, "bloqueada": 1, "reprovado": 1},
        "itens": [
            {"posicao": 1, "arquivo": "doc1.pdf", "veredito": "criar", "portoes": []},
            {
                "posicao": 2,
                "arquivo": "vazio.pdf",
                "veredito": "bloqueada",
                "portoes": [{"portao": "origem", "resultado": "bloqueada", "title": "ArquivoVazio", "detail": "0 bytes"}],
            },
            {
                "posicao": 3,
                "arquivo": "antigo.pdf",
                "veredito": "ja_ingerido",
                "portoes": [{"portao": "ja_ingerido", "resultado": "ja_ingerido", "title": "JaIngerido"}],
            },
            {
                "posicao": 4,
                "arquivo": "suspeito.pdf",
                "veredito": "reprovado",
                "portoes": [{"portao": "identidade", "resultado": "reprovado", "title": "SuspeitaEstacionada", "detail": "degrau 4"}],
            },
        ],
    }
    texto = formatar_resumo_veredito_e_excecoes(lote, fase="plano")
    assert "Plano de Ingestão: lote lote-456" in texto
    assert "Exceções e recusas:" in texto
    assert "[bloqueada] vazio.pdf: origem:ArquivoVazio — 0 bytes" in texto
    assert "[ja_ingerido] antigo.pdf: ja_ingerido:JaIngerido" in texto
    assert "[reprovado] suspeito.pdf: identidade:SuspeitaEstacionada — degrau 4" in texto


def test_formatar_tabela_vs_resumo():
    lote = {
        "id": "lote-789",
        "autor": "devops",
        "motor": "rag",
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 1, "edicao": 0, "ja_ingerido": 0, "bloqueada": 0, "reprovado": 0},
        "itens": [
            {"posicao": 1, "arquivo": "doc.pdf", "titulo": "Um Documento", "veredito": "criar", "portoes": []},
        ],
    }
    tabela = formatar_tabela_plano(lote)
    resumo = formatar_resumo_veredito_e_excecoes(lote, fase="plano")

    assert "Formato (ficha)" in tabela
    assert "Formato (ficha)" not in resumo
    assert "Resumo: total=1 | criar=1" in resumo
