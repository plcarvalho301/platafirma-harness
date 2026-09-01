"""Contrato de persistência de turnos em sessao.giro (Card #2945).

Verifica:
1. Gravação do prompt do dono (Evento 1) com fita_id e seq.
2. Gravação da resposta do modelo (Evento 2) no mesmo (fita_id, seq).
3. Gravação simultânea (prompt + resposta) no caso de fita criada no próprio giro.
4. Auto-cálculo de seq se ausente via COALESCE(MAX(seq), 0) + 1.
5. Inserção preventiva em sessao.fita para respeitar FK ON DELETE CASCADE.
6. Gravação assíncrona não-bloqueante (grava_giro_async).
7. Falha de banco (ou psycopg ausente) não levanta exceção e degrada declarado (log em stderr).
8. Worker do chat dispara grava_giro_async nos dois eventos do turno.
9. Giros silenciosos (rituais/âncoras) não gravam em sessao.giro.
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


def test_grava_giro_evento_prompt():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        r = g.grava_giro(
            fita_id="fita-abc-123",
            seq=1,
            prompt_texto="Qual o status do acervo?",
            cadeira="ti",
        )

        assert r["gravado"] is True
        assert r["fita_id"] == "fita-abc-123"
        assert r["seq"] == 1

        # Verifica queries executadas: fita e giro
        chamadas = mock_cursor.execute.call_args_list
        assert len(chamadas) == 2

        # 1. sessao.fita
        sql_fita, params_fita = chamadas[0][0]
        assert "INSERT INTO sessao.fita" in sql_fita
        assert params_fita[0] == "fita-abc-123"
        assert params_fita[1] == "ti"

        # 2. sessao.giro
        sql_giro, params_giro = chamadas[1][0]
        assert "INSERT INTO sessao.giro" in sql_giro
        assert "ON CONFLICT (fita_id, seq) DO UPDATE" in sql_giro
        assert params_giro[0] == "fita-abc-123"
        assert params_giro[1] == 1
        assert params_giro[3] == "Qual o status do acervo?"
        assert params_giro[4] is None  # resposta ainda ausente


def test_grava_giro_evento_resposta():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        r = g.grava_giro(
            fita_id="fita-abc-123",
            seq=1,
            resposta_texto="O acervo está em dia.",
            cadeira="ti",
        )

        assert r["gravado"] is True
        assert r["fita_id"] == "fita-abc-123"
        assert r["seq"] == 1

        chamadas = mock_cursor.execute.call_args_list
        assert len(chamadas) == 2
        sql_giro, params_giro = chamadas[1][0]
        assert params_giro[3] is None  # prompt
        assert params_giro[4] == "O acervo está em dia."


def test_grava_giro_ambos_prompt_e_resposta():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        r = g.grava_giro(
            fita_id="fita-nova-456",
            seq=1,
            prompt_texto="Pergunta 1",
            resposta_texto="Resposta 1",
            cadeira="ia",
            chapeu="especialista",
        )

        assert r["gravado"] is True
        assert r["fita_id"] == "fita-nova-456"
        assert r["seq"] == 1

        chamadas = mock_cursor.execute.call_args_list
        sql_giro, params_giro = chamadas[1][0]
        assert params_giro[2] == "especialista"
        assert params_giro[3] == "Pergunta 1"
        assert params_giro[4] == "Resposta 1"


def test_grava_giro_calcula_seq_se_ausente():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (4,)
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        r = g.grava_giro(
            fita_id="fita-existente",
            seq=None,
            prompt_texto="Pergunta 4",
        )

        assert r["gravado"] is True
        assert r["seq"] == 4

        chamadas = mock_cursor.execute.call_args_list
        assert any("SELECT COALESCE(MAX(seq), 0) + 1" in str(c[0][0]) for c in chamadas)


def test_grava_giro_validacoes_basicas():
    # Sem fita_id
    r1 = g.grava_giro(fita_id="", seq=1, prompt_texto="oi")
    assert r1["gravado"] is False

    # Sem texto
    r2 = g.grava_giro(fita_id="fita-1", seq=1, prompt_texto=None, resposta_texto=None)
    assert r2["gravado"] is False


def test_grava_giro_falha_banco_nao_derruba_e_degrada(capsys):
    with patch("psycopg.connect", side_effect=Exception("Connection refused 5437")):
        r = g.grava_giro(
            fita_id="fita-falha",
            seq=1,
            prompt_texto="Pergunta",
        )

        assert r["gravado"] is False
        assert "Exception" in r["motivo"]

        # Log emitido em stderr
        err = capsys.readouterr().err
        assert "[sessao.giro] FALHOU persistir giro" in err


def test_grava_giro_async_dispara_em_thread():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("psycopg.connect", return_value=mock_conn):
        t = g.grava_giro_async(
            fita_id="fita-async",
            seq=2,
            prompt_texto="Async prompt",
        )
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert mock_cursor.execute.called


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
