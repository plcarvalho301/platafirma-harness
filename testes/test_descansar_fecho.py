"""O fecho da fita no log da porta (card #3345, spec log-de-negocio §3, Fecho).

`descansar fita --encerra-sessao` grava a linha de fecho pelo lib/oplog: por que a fita parou
(`motivo_parada`, vocabulario fechado) e, onde a superficie informa, os tokens. No Code,
`descansar` soma o `usage` do transcript que o Claude Code ja grava; sem transcript achado o
fecho sai sem tokens, e a falta se diz.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
import oplog  # noqa: E402

loader = SourceFileLoader("descansar_fecho_bin", str(REPO_ROOT / "bin" / "descansar"))
spec = importlib.util.spec_from_loader("descansar_fecho_bin", loader)
assert spec and spec.loader
descansar = importlib.util.module_from_spec(spec)
loader.exec_module(descansar)

SID = "2be6bc3b-36fd-43e2-a189-3e01b0ec5e36"


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    """Log e home em tmp: nada do host real."""
    log = tmp_path / "ops"
    monkeypatch.setenv("OPS_LOG_DIR", str(log))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PF_SESSAO", SID)
    monkeypatch.setenv("PF_ORDEM_ID", "o20261008T000000-abc123")
    monkeypatch.setenv("PF_CADEIRA", "ia")
    monkeypatch.setenv("PF_SUJEITO", "b6986be0-c5b6-4693-839f-73c90b79b25a")
    monkeypatch.setenv("PF_SUPERFICIE", "code")
    monkeypatch.setattr(descansar, "LOG_OPS", str(log))
    return tmp_path


def _fecho(tmp_path):
    linhas = [l for f in sorted((tmp_path / "ops").glob("ops-*.jsonl"))
              for l in f.read_text(encoding="utf-8").splitlines()]
    (linha,) = [json.loads(l) for l in linhas]
    return linha


def _transcript(tmp_path, cadeira="ia", usos=()):
    pasta = tmp_path / "home" / ".claude" / "projects" / f"x-fitas-{cadeira}"
    pasta.mkdir(parents=True)
    linhas = [json.dumps({"type": "assistant", "requestId": rid, "message": {"usage": uso}})
              for rid, uso in usos]
    (pasta / "fita.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def test_o_fecho_diz_por_que_a_fita_parou(ambiente):
    gravou, tokens = descansar.grava_fecho("ia", "teto_de_giros")
    assert gravou is True and tokens is None
    linha = _fecho(ambiente)
    assert linha["evento"] == "fecho" and linha["motivo_parada"] == "teto_de_giros"
    assert linha["sessao_id"] == SID and linha["cadeira"] == "ia"
    assert "tokens" not in linha, "sem transcript de Code a falta se diz, nunca se estima"
    assert oplog.validar(linha) == []


def test_no_code_os_tokens_sao_a_soma_do_usage_do_transcript(ambiente):
    _transcript(ambiente, usos=[
        ("r1", {"input_tokens": 10, "output_tokens": 5}),
        ("r1", {"input_tokens": 10, "output_tokens": 50}),     # mesma resposta: vale a ultima
        ("r2", {"input_tokens": 3, "output_tokens": 7, "cache_creation_input_tokens": 100,
                "cache_read_input_tokens": 1000}),
    ])
    gravou, tokens = descansar.grava_fecho("ia", "concluiu")
    assert gravou and tokens == {"entrada": 13, "saida": 57, "cache_criacao": 100, "cache_leitura": 1000}
    linha = _fecho(ambiente)
    assert linha["tokens"] == 13 + 57 + 100 + 1000
    assert linha["fonte_tokens"] == "provedor" and linha["tokens_por_tipo"]["saida"] == 57
    assert oplog.validar(linha) == []


def test_transcript_de_outra_cadeira_nao_conta(ambiente):
    _transcript(ambiente, cadeira="dados", usos=[("r1", {"input_tokens": 9, "output_tokens": 9})])
    assert descansar.tokens_do_transcript("ia") is None


def test_parada_so_aceita_o_vocabulario_fechado():
    assert set(oplog.MOTIVOS_PARADA) == {"concluiu", "teto_de_giros", "orcamento_de_erro", "interrompida"}
    erros = oplog.validar({"ts": "t", "evento_id": "e", "schema_v": 1, "origem": "cadeira",
                           "mapa_v": None, "tool": "descansar", "evento": "fecho",
                           "sessao_id": SID, "cadeira": "ia", "motivo_parada": "cansei"})
    assert any("motivo_parada" in e for e in erros)


def test_o_ritual_manda_dizer_por_que_a_fita_parou():
    texto = (REPO_ROOT / "bin" / "descansar").read_text(encoding="utf-8")
    assert "--parada teto_de_giros|orcamento_de_erro|interrompida" in texto
