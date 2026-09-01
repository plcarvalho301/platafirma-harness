#!/usr/bin/env python3
"""Persistência de turnos em sessao.giro (Card #2945).

Grava os dois eventos de cada turno — prompt do dono e resposta do modelo —
no Postgres da fita (host=127.0.0.1 port=5437 dbname=sessao user=sessao)
de forma assíncrona e degradada (falha de banco não bloqueia nem derruba o turno).

PK de giro é (fita_id, seq).
Schema: sessao.giro (fita_id, seq, chapeu, prompt_texto, resposta_texto, em).
"""

from __future__ import annotations

import os
import sys
import threading

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
HARNESS = os.environ.get("PF_HARNESS", os.path.join(RAIZ, "platafirma-harness"))
SESSAO_ENV = os.path.join(HARNESS, "sessao", ".env")


def dsn() -> str:
    """DSN do Postgres de sessão (5437).

    Senha lida de SESSAO_PG_PASSWORD ou do arquivo sessao/.env (600, fora do git).
    """
    d = os.environ.get("SESSAO_PG_DSN")
    if d:
        return d
    senha = os.environ.get("SESSAO_PG_PASSWORD", "")
    if not senha and os.path.isfile(SESSAO_ENV):
        try:
            with open(SESSAO_ENV, encoding="utf-8") as f:
                for linha in f:
                    if linha.startswith("SESSAO_PG_PASSWORD="):
                        senha = linha.split("=", 1)[1].strip().strip("'\"")
                        break
        except OSError:
            pass
    porta = os.environ.get("SESSAO_PG_PORT", "5437")
    host = os.environ.get("SESSAO_PG_HOST", "127.0.0.1")
    dbname = os.environ.get("SESSAO_PG_DBNAME", "sessao")
    user = os.environ.get("SESSAO_PG_USER", "sessao")
    return f"host={host} port={porta} dbname={dbname} user={user} password={senha}"


def grava_giro(
    fita_id: str,
    seq: int | None = None,
    *,
    prompt_texto: str | None = None,
    resposta_texto: str | None = None,
    cadeira: str = "",
    chapeu: str = "",
    superficie: str = "",
    dsn_override: str | None = None,
) -> dict:
    """Grava ou atualiza a linha em sessao.giro para (fita_id, seq).

    Garante a fita em sessao.fita para respeitar FK.
    Degradado: falha de conexão ou módulo ausente gera log em stderr e segue,
    sem levantar exceção.
    """
    fid = (fita_id or os.environ.get("PF_FITA") or os.environ.get("PF_SESSAO") or "").strip()
    if not fid:
        return {"gravado": False, "motivo": "sem fita_id"}
    if prompt_texto is None and resposta_texto is None:
        return {"gravado": False, "motivo": "sem texto a gravar"}

    try:
        import psycopg
    except ImportError:
        print("[sessao.giro] FALHOU persistir giro: modulo psycopg ausente", file=sys.stderr, flush=True)
        return {"gravado": False, "motivo": "psycopg ausente"}

    con_dsn = dsn_override or dsn()
    try:
        with psycopg.connect(con_dsn, connect_timeout=3) as con:
            with con.cursor() as cur:
                # 1. Garantir sessao.fita para satisfazer a FK de sessao.giro
                sup = (superficie or os.environ.get("PF_SUPERFICIE", "chat")).strip()
                if sup not in ("claude.ai", "chat", "code", "desconhecida"):
                    sup = "chat"
                pers = (cadeira or os.environ.get("PF_CADEIRA", "desconhecida")).strip() or "desconhecida"
                cur.execute(
                    "INSERT INTO sessao.fita (id, persona, superficie) VALUES (%s, %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (fid, pers, sup),
                )

                # 2. Determinar seq se ausente
                n_seq = seq
                if n_seq is None or n_seq <= 0:
                    cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM sessao.giro WHERE fita_id = %s", (fid,))
                    row = cur.fetchone()
                    n_seq = int(row[0]) if row else 1

                chap = chapeu or os.environ.get("PF_CHAPEU") or None

                # 3. Upsert atômico no sessao.giro
                cur.execute(
                    """
                    INSERT INTO sessao.giro (fita_id, seq, chapeu, prompt_texto, resposta_texto, em)
                    VALUES (%s, %s, %s, %s, %s, now())
                    ON CONFLICT (fita_id, seq) DO UPDATE SET
                      prompt_texto = COALESCE(EXCLUDED.prompt_texto, sessao.giro.prompt_texto),
                      resposta_texto = COALESCE(EXCLUDED.resposta_texto, sessao.giro.resposta_texto),
                      chapeu = COALESCE(EXCLUDED.chapeu, sessao.giro.chapeu)
                    """,
                    (fid, n_seq, chap, prompt_texto, resposta_texto),
                )
                con.commit()
                return {"gravado": True, "fita_id": fid, "seq": n_seq}
    except Exception as e:  # noqa: BLE001 — banco mudo não derruba o turno
        print(f"[sessao.giro] FALHOU persistir giro ({fid}, {seq}): {e!r}", file=sys.stderr, flush=True)
        return {"gravado": False, "motivo": f"{type(e).__name__}: {e}"}


def grava_giro_async(
    fita_id: str,
    seq: int | None = None,
    *,
    prompt_texto: str | None = None,
    resposta_texto: str | None = None,
    cadeira: str = "",
    chapeu: str = "",
    superficie: str = "",
    dsn_override: str | None = None,
) -> threading.Thread:
    """Dispara a gravação em background thread daemon (não-bloqueante)."""
    t = threading.Thread(
        target=grava_giro,
        args=(fita_id, seq),
        kwargs={
            "prompt_texto": prompt_texto,
            "resposta_texto": resposta_texto,
            "cadeira": cadeira,
            "chapeu": chapeu,
            "superficie": superficie,
            "dsn_override": dsn_override,
        },
        daemon=True,
    )
    t.start()
    return t
