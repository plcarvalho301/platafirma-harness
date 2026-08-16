#!/home/claudinho/AI/.venv-harness/bin/python
# capturar-mesa-legada — copia a mesa escrita no Valkey para `sessao.mesa_legado`.
# capacidade: memoria
# dono: claudinho-TI
# componente: harness-sessao
#
# Ato de migração da fase 6 (spec_montagem-de-sessao §10, card #189). Roda quantas vezes
# quiser: é UPSERT por chave de origem, e não apaga nada do Valkey — a mesa velha segue
# servindo quem ainda lê de lá até o cliente `mesa` trocar de substrato.
#
# NÃO CONVERTE em item. `sessao.mesa_item` exige `ato` e `alvo`; o que está escrito hoje é
# prosa por chapéu. Fabricar ato para caber no modelo seria inventar pendência que ninguém
# declarou — a triagem é da cadeira dona, na primeira fita depois do corte.
#
# NÃO DEDUPLICA por alias. `mem:ti:construcao` e `mem:claudinho-ti:construcao` coexistem e
# divergem (medido, 16/08, nas cinco cadeiras com par): o slug canônico entra na coluna
# `cadeira`, a chave crua fica em `chave_origem`, e as duas metades chegam inteiras.

import os
import re
import sys

try:
    import psycopg
except ImportError:
    sys.exit("erro: modulo 'psycopg' nao instalado neste venv (uv pip install psycopg[binary])")

try:
    import redis
except ImportError:
    sys.exit("erro: modulo 'redis' nao instalado neste venv (uv pip install redis)")

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
PERSONAS = os.path.join(RAIZ, "platafirma-harness", "personas")

MEM_HOST = os.environ.get("MEM_REDIS_HOST", "127.0.0.1")
MEM_PORTA = int(os.environ.get("MEM_REDIS_PORT", "6380"))

PG = os.environ.get(
    "SESSAO_PG_DSN",
    "host=127.0.0.1 port=5437 dbname=sessao user=sessao password=" + os.environ.get("SESSAO_PG_PASSWORD", ""),
)


def mapa_de_slug():
    """alias curto -> slug canonico, derivado das personas que existem no clone.

    Sem tabela escrita a mao: o nome canonico ja esta na linha 1 de cada persona, e
    segunda fonte diverge em silencio.
    """
    mapa = {}
    for nome in sorted(os.listdir(PERSONAS)):
        if not (nome.startswith("persona-") and nome.endswith(".md")):
            continue
        curto = nome[len("persona-"):-len(".md")]
        with open(os.path.join(PERSONAS, nome), encoding="utf-8") as fh:
            primeira = fh.readline()
        achado = re.search(r"claudinh[oa]-[A-Za-z0-9-]+", primeira)
        canonico = achado.group(0) if achado else curto
        mapa[curto.lower()] = canonico
        mapa[canonico.lower()] = canonico
    return mapa


def main():
    mapa = mapa_de_slug()
    r = redis.Redis(host=MEM_HOST, port=MEM_PORTA, decode_responses=True)
    linhas = []
    for chave in r.scan_iter(match="mem:*"):
        partes = chave.split(":")
        if len(partes) != 3:
            continue  # `mem:<cadeira>` sem slot e a fita corrente (card 449), nao e mesa
        _, bruta, chapeu = partes
        texto = r.get(chave)
        if texto is None:
            continue
        ttl = r.ttl(chave)
        linhas.append(
            (
                chave,
                mapa.get(bruta.lower(), bruta),
                chapeu,
                texto,
                len(texto.encode("utf-8")),
                ttl if ttl and ttl > 0 else None,
            )
        )

    if not linhas:
        print("nada a capturar: nenhuma chave `mem:<cadeira>:<chapeu>` no msg-mem")
        return 0

    with psycopg.connect(PG) as con, con.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO sessao.mesa_legado
              (chave_origem, cadeira, chapeu, texto, bytes, ttl_restante_s)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (chave_origem) DO UPDATE SET
              cadeira = EXCLUDED.cadeira,
              texto = EXCLUDED.texto,
              bytes = EXCLUDED.bytes,
              ttl_restante_s = EXCLUDED.ttl_restante_s,
              capturado_em = now()
            """,
            linhas,
        )
        con.commit()

    print(f"capturadas {len(linhas)} mesas, {sum(l[4] for l in linhas)} bytes")
    for cadeira in sorted({l[1] for l in linhas}):
        chaves = sorted(l[0] for l in linhas if l[1] == cadeira)
        print(f"  {cadeira}: {', '.join(chaves)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
