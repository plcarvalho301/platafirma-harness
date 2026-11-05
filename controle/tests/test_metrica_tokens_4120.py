"""Testes do comando `metrica tokens` e da agregação de tokens (#4120).

U11 da story 4120:
- somar_tokens por ato, ordem e job
- metrica tokens --ordem <id> --job <id> devolve as duas linhas comparativas
- formato json
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[2]
if str(HARNESS_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR / "lib"))
if str(HARNESS_DIR / "bin") not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR / "bin"))

from _metrica import somar_tokens, tokens_main


@pytest.fixture
def eventos_exemplo():
    return [
        {
            "ts": "2026-11-05T10:00:00Z",
            "tool": "acervo",
            "ato": "catalogar",
            "ordem_id": "ordem-antiga",
            "job_id": None,
            "obra_id": "obra-1",
            "tokens": 1500,
            "metodo_tokens": "tokenizador qwen2.5",
        },
        {
            "ts": "2026-11-05T10:05:00Z",
            "tool": "acervo",
            "ato": "catalogar",
            "ordem_id": "ordem-antiga",
            "job_id": None,
            "obra_id": "obra-2",
            "tokens": 2500,
            "metodo_tokens": "tokenizador qwen2.5",
        },
        {
            "ts": "2026-11-05T11:00:00Z",
            "tool": "acervo",
            "ato": "pipeline",
            "ordem_id": "ordem-nova",
            "job_id": "job-4120",
            "obra_id": "obra-1",
            "tokens": 800,
            "metodo_tokens": "tokenizador qwen2.5",
        },
        {
            "ts": "2026-11-05T11:05:00Z",
            "tool": "acervo",
            "ato": "pipeline",
            "ordem_id": "ordem-nova",
            "job_id": "job-4120",
            "obra_id": "obra-2",
            "tokens": 1200,
            "metodo_tokens": "tokenizador qwen2.5",
        },
    ]


def test_somar_tokens_por_ordem(eventos_exemplo):
    res = somar_tokens(eventos_exemplo, ordem_id="ordem-antiga")
    assert res["total_tokens"] == 4000
    assert res["eventos"] == 2
    assert len(res["obras"]) == 2
    assert res["metodo"] == "tokenizador qwen2.5"


def test_somar_tokens_por_job(eventos_exemplo):
    res = somar_tokens(eventos_exemplo, job_id="job-4120")
    assert res["total_tokens"] == 2000
    assert res["eventos"] == 2
    assert len(res["obras"]) == 2


def test_metrica_tokens_duas_linhas(eventos_exemplo):
    with patch("_metrica.oplog.ler", return_value=eventos_exemplo):
        out = io.StringIO()
        with patch("sys.stdout", out):
            ret = tokens_main(["--ordem", "ordem-antiga", "--job", "job-4120"])
        assert ret == 0
        linhas = out.getvalue().strip().splitlines()
        assert len(linhas) == 2
        assert "ordem ordem-antiga: 2000 tokens/obra (tokenizador qwen2.5)" == linhas[0]
        assert "job job-4120: 1000 tokens/obra (tokenizador qwen2.5)" == linhas[1]


def test_metrica_tokens_json(eventos_exemplo):
    with patch("_metrica.oplog.ler", return_value=eventos_exemplo):
        out = io.StringIO()
        with patch("sys.stdout", out):
            ret = tokens_main(["--ordem", "ordem-antiga", "--job", "job-4120", "--json"])
        assert ret == 0
        dados = json.loads(out.getvalue())
        assert "ordem" in dados
        assert "job" in dados
        assert dados["ordem"]["tokens_por_obra"] == 2000
        assert dados["job"]["tokens_por_obra"] == 1000
