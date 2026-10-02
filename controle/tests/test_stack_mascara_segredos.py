"""`infra config <stack>` nao imprime valor de segredo (#2856 linha 76; incidente #3221).

`bin/_release/stack` passa a saida de `compose config` por `mascara_segredos`: o valor de
variavel cujo NOME sugere segredo sai como `***`, em YAML (mapa e lista) e em JSON; o nome e o
resto da linha ficam. A funcao se extrai do proprio script e roda no bash real, sem docker.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

STACK = Path(__file__).resolve().parents[2] / "bin" / "_release" / "stack"

if not shutil.which("bash") or not shutil.which("sed"):
    pytest.skip("precisa de bash e sed reais", allow_module_level=True)


def _mascara(texto: str) -> str:
    achou = re.search(r"^mascara_segredos\(\) \{.*?^\}$", STACK.read_text(encoding="utf-8"), re.DOTALL | re.MULTILINE)
    assert achou, "bin/_release/stack perdeu a funcao mascara_segredos"
    r = subprocess.run(["bash", "-c", achou.group(0) + "\nmascara_segredos"], input=texto,
                       capture_output=True, text=True, timeout=20, check=True)
    return r.stdout


def test_yaml_em_mapa_mascara_so_o_valor_do_segredo():
    saida = _mascara(
        "services:\n"
        "  searxng:\n"
        "    environment:\n"
        "      SEARXNG_SECRET: abc123\n"
        "      POSTGRES_PASSWORD: p4ss\n"
        "      OAUTH2_PROXY_COOKIE_SECRET: c00kie\n"
        "      RAG_API_TOKEN: tok\n"
        "      LOG_LEVEL: debug\n")
    assert "SEARXNG_SECRET: ***\n" in saida and "POSTGRES_PASSWORD: ***\n" in saida
    assert "OAUTH2_PROXY_COOKIE_SECRET: ***\n" in saida and "RAG_API_TOKEN: ***\n" in saida
    assert "LOG_LEVEL: debug\n" in saida
    for valor in ("abc123", "p4ss", "c00kie", "tok"):
        assert valor not in saida


def test_yaml_em_lista_mascara_depois_do_igual():
    saida = _mascara("    environment:\n      - RAG_API_TOKEN=tok\n      - LOG_LEVEL=debug\n")
    assert "- RAG_API_TOKEN=***\n" in saida and "- LOG_LEVEL=debug\n" in saida
    assert "=tok" not in saida


def test_json_mascara_o_valor_e_guarda_a_virgula():
    saida = _mascara('{\n    "SEARXNG_SECRET": "abc123",\n    "LOG_LEVEL": "debug"\n}\n')
    assert '"SEARXNG_SECRET": "***",' in saida and '"LOG_LEVEL": "debug"' in saida
    assert "abc123" not in saida


def test_linha_sem_segredo_e_chave_sem_valor_passam_intactas():
    entrada = "services:\n  rag:\n    secrets:\n      - rag_api_token\n    image: rag:1\n"
    assert _mascara(entrada) == entrada
