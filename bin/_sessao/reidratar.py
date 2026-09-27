"""bin/_sessao/reidratar.py — reidrata `sessao:{id}` a partir de `sessao.sessao`
(Postgres, durável) quando a chave efêmera some do msg-mem (card #3145, Onda 1 Frente E).

MECANISMO: a stack motor (msg-mem, Valkey; `platafirma-motor/deploy/msg-mem.conf`,
`appendonly no`, `save ""`) é recriada vazia a cada promoção — `sessao:{id}` some de
todo mundo. O registro durável (`sessao.sessao`, INSERT no ato de cunhar por
`bin/sessao::_registra_duravel` e `bin/monta-sessao::registra_sessao_duravel`) fica.
Este módulo fecha o furo: quando a chave efêmera falta, quem consome relê o durável
e regrava a chave com o TTL que resta, em vez de reportar "não existe" para uma
sessão que só perdeu o cache (incidente de 24/09: `descansar fita` saiu 1 com
"PF_CADEIRA nao definida" logo após a promoção do motor).

REGRA DE VALIDADE (arq:0091 §3, arq:0093 §7): a entidade-sessão é durável — não
expira por si (arq:0091 §3: "a chave é durável: estável enquanto a conversa vive").
Nenhuma das duas ADRs fixa uma janela própria para "ainda resumível"; a única janela
que já existe no sistema é a do CACHE efêmero (`sessao:{id}`, TTL_SESSAO_S = 48h, a
mesma constante documentada em bin/sessao e em ops-server/server.py). Reidratar
recria essa MESMA janela, contada de `aberta_em`: uma linha achada porém já fora
dela não reidrata — o "não existe" fica idêntico ao de uma chave que tivesse
expirado por TTL, nunca sem-fim.

SESSÃO ENCERRADA DE PROPÓSITO NÃO REIDRATA (migração 0092): `sessao.sessao` ganhou a
coluna `encerrada_em` — `bin/sessao::ato_encerrar`/`ato_limpar` gravam `now()` nela,
melhor esforço, além do DEL de sempre no msg-mem (`_marca_encerrada`). Linha com
`encerrada_em` preenchida nunca reidrata, mesmo dentro da janela de TTL. A migração
aplica-se DEPOIS da promoção (mesma janela de risco de qualquer migração aditiva):
enquanto a coluna ainda não existe, a consulta tolera o erro e cai na forma antiga
(sem checar fechamento) — comportamento de antes da 0092, nunca uma exceção.

NUM SÓ LUGAR, DOS DOIS LADOS DO VENV: bin/sessao roda no venv harness (psycopg já é
dependência dele, via `_registra_duravel`) e chama `reidratar()` direto, em processo.
ops-server/server.py roda no venv ops, SEM driver de banco (mesma razão declarada em
bin/_sessao/giro-carga.py: "ops-mcp roda no venv ops da release, sem driver de
banco") — nunca importa psycopg; chama `reidratar_via_verbo()`, que invoca o verbo
`sessao ver <id> --json` (subprocesso, harness venv) em vez de abrir conexão própria.
As DUAS funções aplicam a mesma regra de validade; só a via de acesso ao Postgres
muda. `ledger:{id}` e `giro:{id}` não se reidratam (são rederiváveis).
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

TTL_SESSAO_S = 172800  # 48h — mesma constante de bin/sessao e ops-server/server.py


def reidratar(sid: str, rc_mem, roda, pg_porta: str = "5437",
              ttl_padrao: int = TTL_SESSAO_S) -> dict | None:
    """`sessao:{sid}` ausente do msg-mem: tenta reidratar de `sessao.sessao` (Postgres).

    `rc_mem`: cliente do msg-mem já conectado — usado só para o SET da chave
    reidratada, nunca para o GET (isso é responsabilidade de quem chama; este módulo
    só entra em cena depois que o GET já deu ausente).
    `roda`: callable(argv: list[str], timeout: int) -> (exit, stdout, stderr) — o
    mesmo `_roda` do chamador (reusa PATH/env dele; este módulo nunca abre
    subprocesso de segredo por conta própria).

    Devolve o dict pronto para `sessao:{id}` (mesmo shape de `_le_chave`), já
    regravado no msg-mem com o TTL que resta — ou None (sem linha, encerrada de
    proposito, Postgres inalcançável, ou fora da janela de validade): o "não existe"
    de quem chama fica idêntico ao de hoje.
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
    tem_colunas_novas = True
    try:
        with psycopg.connect(dsn, connect_timeout=3) as con, con.cursor() as cur:
            try:
                cur.execute(
                    "SELECT cadeira, chapeu, superficie, aberta_em, encerrada_em, sujeito "
                    "FROM sessao.sessao WHERE sessao_id = %s", (sid,))
                row = cur.fetchone()
            except Exception:  # noqa: BLE001 — coluna ainda ausente (0092/0094 nao
                # aplicadas apos a promocao): tolera, cai na forma de antes das duas
                con.rollback()
                tem_colunas_novas = False
                cur.execute(
                    "SELECT cadeira, chapeu, superficie, aberta_em "
                    "FROM sessao.sessao WHERE sessao_id = %s", (sid,))
                row = cur.fetchone()
    except Exception:  # noqa: BLE001 — banco inalcançável: "nao existe", como hoje
        return None
    if row is None:
        return None
    sujeito = None
    if tem_colunas_novas:
        cadeira, chapeu, superficie, aberta_em, encerrada_em, sujeito = row
        if encerrada_em is not None:
            return None  # encerrada de proposito (sessao encerrar|limpar) -- nao reidrata
    else:
        cadeira, chapeu, superficie, aberta_em = row
    if aberta_em.tzinfo is None:
        aberta_em = aberta_em.replace(tzinfo=timezone.utc)
    restante = int(ttl_padrao - (datetime.now(timezone.utc) - aberta_em).total_seconds())
    if restante <= 0:
        return None  # fora da janela de validade (arq:0091 §3) — vencida, nao reidrata
    ch = {
        "cadeira": cadeira, "chapeu": chapeu, "superficie": superficie or "desconhecida",
        "ordem_id": "-", "aberto_em": aberta_em.isoformat(), "origem": "reidratada",
    }
    # sujeito (card #3145, migracao 0094): so entra quando o registro duravel o tem --
    # linha gravada antes da 0094, ou coluna ainda nao aplicada, fica sem a chave;
    # nunca um valor fabricado (fallback de cadeira/USER e proibido pela decisao 9).
    if sujeito:
        ch["sujeito"] = sujeito
    try:
        rc_mem.set(f"sessao:{sid}", json.dumps(ch, ensure_ascii=False), ex=restante)
    except Exception:  # noqa: BLE001 — msg-mem mudo no regravar: devolve mesmo assim
        pass
    return ch


def reidratar_via_verbo(sid: str, bin_sessao: str, env: dict, timeout: int = 10) -> dict | None:
    """Mesma reidratação de `reidratar()` acima, pelo verbo `sessao ver --json` — uso
    de quem não fala com o Postgres no próprio processo (ops-server/server.py, venv
    ops sem driver de banco). Não abre conexão nenhuma aqui: só subprocesso + JSON.
    Qualquer desvio (verbo ausente, exit != 0, JSON inválido, timeout) devolve None —
    comportamento de hoje, nunca uma exceção que derrube quem chamou."""
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
    """Segredo por verbo, no processo (spec_acesso §2) — mesmo padrão de bin/sessao,
    nunca variável de ambiente nem arquivo."""
    rc, out, err = roda(["seg", "segredo", "ler", "harness-sessao/SESSAO_PG_PASSWORD"], timeout=10)
    if rc == 0 and out.strip():
        return out.strip(), None
    return None, ("seg segredo ler harness-sessao/SESSAO_PG_PASSWORD: "
                  f"{(err or out).strip()[:120] or f'exit {rc}'}")
