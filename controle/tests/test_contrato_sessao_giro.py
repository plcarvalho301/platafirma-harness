"""Contrato de persistência de turnos em sessao.giro (Card #2945).

Verifica:
1. Worker do chat dispara grava_giro_async nos dois eventos do turno.
2. Giros silenciosos (rituais/âncoras) não gravam em sessao.giro.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAT_DIR = REPO_ROOT / "chat"
for d in (CHAT_DIR, REPO_ROOT):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from comum import giro as g


def test_grava_giro_validacoes_basicas():
    # Sem fita_id
    r1 = g.grava_giro(fita_id="", seq=1, prompt_texto="oi")
    assert r1["gravado"] is False

    # Sem texto
    r2 = g.grava_giro(fita_id="fita-1", seq=1, prompt_texto=None, resposta_texto=None)
    assert r2["gravado"] is False


def test_worker_dispara_gravacao_nos_dois_eventos():
    import sqlite3
    from chat.comum import journal
    from chat.worker import worker

    # Cria journal temporario
    con = sqlite3.connect(":memory:", isolation_level=None)
    con.row_factory = sqlite3.Row
    con.executescript(journal.ESQUEMA)
    journal._migra(con)

    # Simula fita existente na sala com 1 giro previo
    con.execute(
        "INSERT INTO fitas (sala, id_fita, atualizado_em, giros) VALUES (?, ?, ?, ?)",
        ("!sala1:x", "fita-existente-1", 100.0, 1),
    )

    # Registra chegada
    job_id = journal.registra_chegada(
        con,
        event_id="$ev1",
        txn_id="t1",
        sala="!sala1:x",
        cadeira="ti",
        remetente="@dono:x",
        corpo="Como vai o sistema?",
    )

    chamadas_grava = []

    def mock_grava_async(**kwargs):
        chamadas_grava.append(kwargs)
        return MagicMock()

    with patch("chat.worker.worker.journal.abre", return_value=con), \
         patch("chat.worker.worker.giro_db.grava_giro_async", side_effect=mock_grava_async), \
         patch.object(worker.Giro, "executa", return_value={"estado": journal.OK, "texto": "Sistema 100%", "id_fita": "fita-existente-1"}):

        # Roda uma volta no atende_sala
        vivas = {"!sala1:x"}
        trava = worker.threading.Lock()
        worker.atende_sala("!sala1:x", vivas, trava)

        # Devem ter ocorrido 2 disparos: prompt e resposta
        assert len(chamadas_grava) == 2

        # 1. Evento prompt
        ev_prompt = chamadas_grava[0]
        assert ev_prompt["fita_id"] == "fita-existente-1"
        assert ev_prompt["seq"] == 2  # giros previo (1) + 1
        assert ev_prompt["prompt_texto"] == "Como vai o sistema?"

        # 2. Evento resposta
        ev_resp = chamadas_grava[1]
        assert ev_resp["fita_id"] == "fita-existente-1"
        assert ev_resp["seq"] == 2
        assert ev_resp["resposta_texto"] == "Sistema 100%"


def test_worker_giro_silencioso_nao_grava_em_sessao_giro():
    import sqlite3
    from chat.comum import journal, rituais
    from chat.worker import worker

    con = sqlite3.connect(":memory:", isolation_level=None)
    con.row_factory = sqlite3.Row
    con.executescript(journal.ESQUEMA)
    journal._migra(con)

    journal.enfileira_silencioso(
        con,
        sala="!sala_ritual:x",
        cadeira="ti",
        id_fita="fita-morta",
        corpo=rituais.ENCERRAMENTO,
        marca=journal.RITUAL,
    )

    chamadas_grava = []

    with patch("chat.worker.worker.journal.abre", return_value=con), \
         patch("chat.worker.worker.giro_db.grava_giro_async", side_effect=lambda **kw: chamadas_grava.append(kw)), \
         patch.object(worker.Giro, "executa", return_value={"estado": journal.OK, "texto": "", "id_fita": "fita-morta"}):

        vivas = {"!sala_ritual:x"}
        trava = worker.threading.Lock()
        worker.atende_sala("!sala_ritual:x", vivas, trava)

        # Giro silencioso nao deve gravar sessao.giro
        assert len(chamadas_grava) == 0
