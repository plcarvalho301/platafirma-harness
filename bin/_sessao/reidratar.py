"""bin/_sessao/reidratar.py — reidrata `sessao:{id}` a partir de `sessao.sessao`
(Postgres, durável) quando a chave efêmera some do msg-mem.

Migrado para gravar `sessao:{id}` como hash no Valkey.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any

TTL_SESSAO_S = 172800  # 48h — mesma constante de bin/sessao e porta/sessao_mem.py


def _serializar_hash(campos: dict[str, Any]) -> dict[str, str]:
    saida: dict[str, str] = {}
    for k, v in campos.items():
        if v is None:
            continue
        if isinstance(v, bool):
            saida[str(k)] = "true" if v else "false"
        elif isinstance(v, (dict, list)):
            saida[str(k)] = json.dumps(v, ensure_ascii=False)
        else:
            saida[str(k)] = str(v)
    return saida


def reidratar(sid: str, rc_mem, roda, pg_porta: str = "5437",
              ttl_padrao: int = TTL_SESSAO_S) -> dict | None:
    """`sessao:{sid}` ausente do msg-mem: tenta reidratar de `sessao.sessao` (Postgres).

    Grava `sessao:{sid}` como hash (`HSET` + `EXPIRE`) com o TTL restante.
    """
    try:
        import psycopg
    except ImportError:
        return None
    senha, _motivo = _senha_pg(roda)
    if not senha:
        return None
    dsn = f"host=127.0.0.1 port={pg_porta} dbname=sessao user=sessao password={senha}"
    row = None
    try:
        with psycopg.connect(dsn, connect_timeout=3) as con, con.cursor() as cur:
            consultas = (
                "SELECT cadeira, chapeu, superficie, aberta_em, encerrada_em, sujeito, ordem_id "
                "FROM sessao.sessao WHERE sessao_id = %s",
                "SELECT cadeira, chapeu, superficie, aberta_em, encerrada_em, sujeito "
                "FROM sessao.sessao WHERE sessao_id = %s",
                "SELECT cadeira, chapeu, superficie, aberta_em "
                "FROM sessao.sessao WHERE sessao_id = %s",
            )
            for i, sql in enumerate(consultas):
                try:
                    cur.execute(sql, (sid,))
                    row = cur.fetchone()
                    break
                except Exception:  # noqa: BLE001
                    if i == len(consultas) - 1:
                        raise
                    con.rollback()
    except Exception:  # noqa: BLE001 — banco inalcançável: "nao existe", como hoje
        return None
    if row is None:
        return None
    sujeito = ordem_id = encerrada_em = None
    if len(row) >= 7:
        cadeira, chapeu, superficie, aberta_em, encerrada_em, sujeito, ordem_id = row[:7]
    elif len(row) >= 6:
        cadeira, chapeu, superficie, aberta_em, encerrada_em, sujeito = row[:6]
    else:
        cadeira, chapeu, superficie, aberta_em = row[:4]
    if encerrada_em is not None:
        return None  # encerrada de proposito (sessao encerrar|limpar) -- nao reidrata
    if aberta_em.tzinfo is None:
        aberta_em = aberta_em.replace(tzinfo=timezone.utc)
    restante = int(ttl_padrao - (datetime.now(timezone.utc) - aberta_em).total_seconds())
    if restante <= 0:
        return None  # fora da janela de validade — vencida, nao reidrata
    ch: dict[str, Any] = {
        "cadeira": cadeira, "chapeu": chapeu, "superficie": superficie or "desconhecida",
        "canonizada": True, "autorizada_por": "reidratada",
        "ordem_id": ordem_id or "-", "aberto_em": aberta_em.isoformat(), "origem": "reidratada",
    }
    if sujeito:
        ch["sujeito"] = sujeito
    chave = f"sessao:{sid}"
    try:
        mapping = _serializar_hash(ch)
        if mapping:
            rc_mem.hset(chave, mapping=mapping)
            rc_mem.expire(chave, restante)
    except Exception:  # noqa: BLE001 — msg-mem mudo no regravar: devolve mesmo assim
        pass
    return ch


def encerrada_em_duravel(sid: str, roda, pg_porta: str = "5437") -> str | None:
    """Devolve o ISO de `encerrada_em` em `sessao.sessao` quando a linha foi encerrada de
    propósito (`sessao encerrar`, `sessao limpar`, `descansar encerrar`), ou
    None se não existe, segue aberta ou o banco/coluna não responde."""
    try:
        import psycopg
    except ImportError:
        return None
    senha, _motivo = _senha_pg(roda)
    if not senha:
        return None
    dsn = f"host=127.0.0.1 port={pg_porta} dbname=sessao user=sessao password={senha}"
    try:
        with psycopg.connect(dsn, connect_timeout=3) as con, con.cursor() as cur:
            cur.execute(
                "SELECT cadeira, chapeu, superficie, aberta_em, encerrada_em "
                "FROM sessao.sessao WHERE sessao_id = %s",
                (sid,))
            row = cur.fetchone()
    except Exception:  # noqa: BLE001
        return None
    if not row or len(row) < 5 or row[4] is None:
        return None
    enc = row[4]
    if hasattr(enc, "tzinfo") and enc.tzinfo is None:
        enc = enc.replace(tzinfo=timezone.utc)
    return enc.isoformat() if hasattr(enc, "isoformat") else str(enc)


def reidratar_via_verbo(sid: str, bin_sessao: str, env: dict, timeout: int = 10) -> dict | None:
    """Mesma reidratação de `reidratar()` acima, pelo verbo `sessao ver --json`."""
    try:
        proc = subprocess.run([bin_sessao, "ver", sid, "--json"], capture_output=True,
                              text=True, timeout=timeout, env=env)
        if proc.returncode != 0:
            return None
        d = json.loads(proc.stdout)
        return d if isinstance(d, dict) else None
    except Exception:  # noqa: BLE001 — reidratar nunca pode travar quem chamou
        return None


def _senha_pg(roda) -> tuple[str | None, str | None]:
    """Segredo por verbo, no processo (spec_acesso §2) — mesmo padrão de bin/sessao."""
    rc, out, err = roda(["seg", "segredo", "ler", "harness-sessao/SESSAO_PG_PASSWORD"], timeout=10)
    if rc == 0 and out.strip():
        return out.strip(), None
    return None, ("seg segredo ler harness-sessao/SESSAO_PG_PASSWORD: "
                  f"{(err or out).strip()[:120] or f'exit {rc}'}")
