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

from _metrica import job_do_evento, somar_tokens, tokens_main


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
        assert "ordem ordem-antiga: 2000 tokens/obra (2 obras · tokenizador qwen2.5)" == linhas[0]
        assert "job job-4120: 1000 tokens/obra (2 obras · tokenizador qwen2.5)" == linhas[1]


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


# --- o que o lote real mostrou (05/11/2026): o giro não traz job_id nem obra_id ---------------------------------

JOB = "abde8f59-fb60-437b-a56a-d788276ac3ed"
OUTRO = "549017e0-5f42-4ec1-944e-666052291474"


def _giro(args, tokens, ordem="o-nova", **extra):
    return {"tool": "acervo", "ato": "catalogar", "args": args, "ordem_id": ordem, "tokens": tokens,
            "metodo_tokens": "tokenizador qwen2.5", **extra}


@pytest.fixture
def giros_reais():
    """O que a porta grava de verdade: os argumentos do ato e o `lote_id` do malote, sem job nem obra."""
    return [
        _giro(f"biblioteca obra --job {JOB}", 5000, lote_id="lote-do-malote"),
        _giro(f"biblioteca obra --job {JOB} --resposta", 300),
        _giro(f"--job={JOB} --espera 240", 400),
        _giro(f"biblioteca obra --job {OUTRO}", 7000),
        _giro("biblioteca obra", 90, lote_id=JOB),  # o lote do malote nunca é job do acervo
    ]


def test_o_job_se_acha_nos_argumentos_do_giro(giros_reais):
    res = somar_tokens(giros_reais, job_id=JOB)
    assert res["total_tokens"] == 5700 and res["eventos"] == 3
    assert somar_tokens(giros_reais, job_id=OUTRO)["total_tokens"] == 7000


def test_o_lote_id_do_malote_nao_vira_job(giros_reais):
    assert somar_tokens(giros_reais, job_id="lote-do-malote")["total_tokens"] == 0
    assert not any(job_do_evento(ev) == "lote-do-malote" for ev in giros_reais)


def test_o_campo_job_id_do_evento_vale_antes_dos_argumentos():
    assert job_do_evento({"job_id": "job-x", "args": f"--job {JOB}"}) == "job-x"
    assert job_do_evento({"args": "sem job aqui"}) == "" and job_do_evento({}) == ""


def test_sem_numero_de_obras_a_linha_diz_o_total_e_nao_finge_media(giros_reais):
    with patch("_metrica.oplog.ler", return_value=giros_reais):
        out = io.StringIO()
        with patch("sys.stdout", out):
            assert tokens_main(["--job", JOB]) == 0
    linha = out.getvalue().strip()
    assert linha == (f"job {JOB}: 5700 tokens no total; número de obras desconhecido "
                     "(passe --obras-job N) (tokenizador qwen2.5)")
    assert "tokens/obra" not in linha


def test_o_numero_de_obras_informado_divide_o_total(giros_reais):
    with patch("_metrica.oplog.ler", return_value=giros_reais):
        out = io.StringIO()
        with patch("sys.stdout", out):
            assert tokens_main(["--ordem", "o-nova", "--job", JOB, "--obras-ordem", "10", "--obras-job", "3"]) == 0
    linhas = out.getvalue().strip().splitlines()
    assert linhas[0] == "ordem o-nova: 1279 tokens/obra (10 obras · tokenizador qwen2.5)"
    assert linhas[1] == f"job {JOB}: 1900 tokens/obra (3 obras · tokenizador qwen2.5)"


def test_json_sem_obras_traz_nulo_e_nao_zero(giros_reais):
    with patch("_metrica.oplog.ler", return_value=giros_reais):
        out = io.StringIO()
        with patch("sys.stdout", out):
            assert tokens_main(["--ordem", "o-nova", "--job", JOB, "--json"]) == 0
    dados = json.loads(out.getvalue())
    assert dados["job"]["tokens_total"] == 5700 and dados["job"]["tokens_por_obra"] is None
    assert dados["job"]["obras"] is None and dados["ordem"]["tokens_por_obra"] is None


# #4128: uso do provedor por chamada; fita inteira dedicada à tarefa.
def _uso(n):
    return {"input_tokens": n, "output_tokens": n * 2,
            "cache_creation_input_tokens": n * 3, "cache_read_input_tokens": n * 4}

def test_uso_modelo_media_p90_e_cache_separados():
    from _metrica.uso_modelo import resumir
    res = resumir({str(n): _uso(n) for n in range(1, 11)})
    assert res["chamadas"] == 10
    assert res["campos"]["entrada"] == {
        "amostras": 10, "ausentes": 0, "total": 55, "media": 5.5, "p90": 9}
    assert res["campos"]["saida"]["media"] == 11
    assert res["campos"]["cache_criacao"]["p90"] == 27
    assert res["campos"]["cache_leitura"]["p90"] == 36
    assert res["campos"]["entrada_total"]["p90"] == 72

def test_uso_modelo_ausencia_nao_vira_zero():
    from _metrica.uso_modelo import resumir
    res = resumir({"1": {"input_tokens": 0, "output_tokens": 2}, "2": {"output_tokens": -1}})
    entrada = res["campos"]["entrada"]
    assert entrada["media"] == 0 and entrada["ausentes"] == 1 and entrada["total"] is None
    assert res["campos"]["entrada_total"]["media"] is None
    assert res["campos"]["cache_leitura"]["p90"] is None
    assert res["campos"]["saida"]["ausentes"] == 1

def test_uso_modelo_le_transcript_real_e_deduplica_requestid(tmp_path):
    import transcript
    arquivo = tmp_path / "antes.jsonl"
    arquivo.write_text("\n".join(json.dumps(d) for d in [
        {"requestId": "r1", "message": {"usage": _uso(1)}},
        {"requestId": "r1", "message": {"usage": _uso(3)}},
        {"requestId": "r2", "message": {"usage": _uso(5)}},
        {"type": "assistant", "message": {"content": "texto privado"}},
    ]) + "\n")
    out = io.StringIO()
    with patch.object(transcript, "da_sessao", return_value=arquivo), patch("sys.stdout", out):
        assert tokens_main(["--fita", JOB, "--tarefa", "status-job", "--json"]) == 0
    res = json.loads(out.getvalue())
    assert res["fitas"]["fita"]["chamadas"] == 2
    assert res["fitas"]["fita"]["campos"]["entrada"]["media"] == 4
    assert "texto privado" not in out.getvalue() and "r1" not in out.getvalue()

def test_uso_modelo_compara_fitas_sem_misturar_populacoes(tmp_path):
    import transcript
    a, b = tmp_path / "antes.jsonl", tmp_path / "depois.jsonl"
    for arquivo, n in [(a, 100), (b, 10)]:
        arquivo.write_text(json.dumps({"requestId": "r1", "message": {"usage": _uso(n)}}) + "\n")
    out = io.StringIO()
    with patch.object(transcript, "da_sessao", side_effect=[a, b]), patch("sys.stdout", out):
        assert tokens_main(["--fita", JOB, "--comparar-fita", OUTRO, "--tarefa", "status-job", "--json"]) == 0
    res = json.loads(out.getvalue())
    assert res["tarefa"] == "status-job"
    assert res["fitas"]["antes"]["campos"]["entrada"]["media"] == 100
    assert res["fitas"]["depois"]["campos"]["entrada"]["media"] == 10

def test_uso_modelo_cadeira_resolve_fita_e_ausente_sai_indeterminavel(tmp_path):
    import transcript
    arquivo = tmp_path / "id-da-fita.jsonl"
    arquivo.write_text(json.dumps({"requestId": "r", "message": {"usage": _uso(4)}}) + "\n")
    out = io.StringIO()
    with patch.object(transcript, "da_cadeira", return_value=arquivo), patch("sys.stdout", out):
        assert tokens_main(["--fita", "dados", "--json"]) == 0
    assert json.loads(out.getvalue())["fitas"]["fita"]["fita"] == "id-da-fita"
    out = io.StringIO()
    with patch.object(transcript, "da_sessao", return_value=None), patch("sys.stdout", out):
        assert tokens_main(["--fita", JOB, "--json"]) == 5
    res = json.loads(out.getvalue())
    assert res["fitas"]["fita"]["estado"] == "ausente"
    assert "campos" not in res["fitas"]["fita"]

def test_uso_modelo_campo_ausente_nao_sai_verde(tmp_path):
    import transcript
    arquivo = tmp_path / "sem-cache.jsonl"
    arquivo.write_text(json.dumps({"requestId": "r", "message": {"usage": {"input_tokens": 10}}}))
    out = io.StringIO()
    with patch.object(transcript, "da_sessao", return_value=arquivo), patch("sys.stdout", out):
        assert tokens_main(["--fita", JOB, "--json"]) == 5
    assert json.loads(out.getvalue())["fitas"]["fita"]["campos"]["saida"]["media"] is None
