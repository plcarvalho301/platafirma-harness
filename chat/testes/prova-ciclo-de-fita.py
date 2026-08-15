#!/usr/bin/env python3
"""Prova do ciclo de vida da fita — card 449, criterios 8-12 e 16-18.

Roda NO HOST, so com stdlib, contra um journal descartavel em /tmp:

    python3 chat/testes/prova-ciclo-de-fita.py

O que ela encena, e por que cada uma existe:
  - rotacao preguicosa: a idade e da SALA e nao se renova a cada mensagem;
  - `/zerar`: comando vira sala nova, nunca giro, e passa pelo dedupe;
  - ritual da fita morta com id EXPLICITO — a corrida que o criterio 18 nomeia,
    encenada de verdade: a fita nova e gravada ANTES de o worker tomar o ritual;
  - ancora de compactacao e o fallback por contagem de giro (criterio 17);
  - aviso de mesa atrasada, uma vez so (secao 2, passo 4 da minuta).

Matrix nao entra: a rotacao chama a recepcao por tres metodos, e aqui eles sao
um duble que anota o que foi pedido. Provar contra homeserver de verdade e o
aceite de ponta a ponta, nao esta prova. Sai 0 se tudo passou.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
CHAT = os.path.dirname(AQUI)
sys.path.insert(0, CHAT)
sys.path.insert(0, os.path.join(CHAT, "recepcao"))

from comum import journal, rituais  # noqa: E402
import rotacao  # noqa: E402

falhas = []
_n = 0


def novo_journal():
    global _n
    _n += 1
    caminho = os.path.join(tempfile.gettempdir(), f"prova-ciclo-{os.getpid()}-{_n}.db")
    for sufixo in ("", "-wal", "-shm"):
        try:
            os.unlink(caminho + sufixo)
        except FileNotFoundError:
            pass
    return caminho, journal.abre(caminho)


class RecepcaoDeMentira:
    """Só os tres metodos que a rotacao usa. Anota o que foi pedido."""

    def __init__(self, con, nova="!nova:x"):
        self.con = con
        self.nova = nova
        self.criou = []
        self.descartou = []
        self.falha_ao_criar = False

    def intent_da(self, cadeira):
        return f"intent:{cadeira}"

    async def cria_sala_direta(self, intent, dono):
        if self.falha_ao_criar:
            return None
        self.criou.append((intent, dono))
        return self.nova

    async def descarta_sala(self, intent, sala, dono):
        self.descartou.append((intent, sala, dono))


def chega(con, sala="!velha:x", cadeira="TI", corpo="oi"):
    global _n
    _n += 1
    return journal.registra_chegada(
        con, event_id=f"$ev{_n}", txn_id="t1", sala=sala,
        cadeira=cadeira, remetente="@pedro:x", corpo=corpo,
    )


def prova(nome):
    def marca(fn):
        try:
            fn()
            print(f"  ok   {nome}")
        except AssertionError as erro:
            falhas.append(nome)
            print(f"  FALHA {nome}: {erro}")
    return marca


# --- idade da sala ---------------------------------------------------------

@prova("sala recem-conhecida nao vence, e a idade nao se renova por mensagem")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!s:x", "TI")
    assert not rotacao.vencida(con, "!s:x"), "sala nova venceu de cara"
    nasceu = journal.nascimento_da_sala(con, "!s:x")
    time.sleep(0.01)
    journal.grava_cadeira(con, "!s:x", "TI")  # segunda mensagem na mesma sala
    assert journal.nascimento_da_sala(con, "!s:x") == nasceu, \
        "a segunda mensagem rejuvenesceu a sala — a rotacao de 24h nunca dispararia"


@prova("sala passada da idade vence; sala desconhecida nao")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!s:x", "TI")
    con.execute("UPDATE salas SET nascida_em = ? WHERE sala = ?",
                (time.time() - rotacao.IDADE_S - 1, "!s:x"))
    assert rotacao.vencida(con, "!s:x"), "sala velha nao venceu"
    assert not rotacao.vencida(con, "!nunca-vista:x"), \
        "sala fora do cache venceu — rodaria antes de aprender a cadeira"


@prova("sala anterior a migracao adota a idade em vez de rodar de cara")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!s:x", "TI")
    con.execute("UPDATE salas SET nascida_em = 0 WHERE sala = ?", ("!s:x",))
    assert not rotacao.vencida(con, "!s:x"), "carimbo ausente virou idade de 1970"
    assert journal.nascimento_da_sala(con, "!s:x") > 0, "nao adotou o carimbo"


@prova("comando so vale como mensagem inteira")
def _():
    assert rotacao.eh_comando("/zerar")
    assert rotacao.eh_comando("  /ZERAR  ")
    assert not rotacao.eh_comando("/zerar a conversa toda"), \
        "prefixo virou comando — apagar conversa por engano nao tem desfazer"
    assert not rotacao.eh_comando("me explica o /zerar")


# --- a rotacao em si -------------------------------------------------------

@prova("gira: sala nova antes de descartar, fita nao migra, velha sai do cache")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!velha:x", "TI")
    job = chega(con)
    journal.reivindica(con, "!velha:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="fita-1")
    assert journal.fita_da_sala(con, "!velha:x") == "fita-1"

    r = RecepcaoDeMentira(con)
    nova = asyncio.run(rotacao.gira(r, "!velha:x", "TI", "@pedro:x", "idade", eco="e agora?"))
    assert nova == "!nova:x", "nao devolveu a sala nova"
    assert r.criou and r.descartou, "criou ou descartou de menos"
    assert journal.cadeira_da_sala(con, "!velha:x") is None, "a velha ficou no cache"
    assert journal.cadeira_da_sala(con, "!nova:x") == "TI", "a nova nao herdou a cadeira"
    assert journal.fita_da_sala(con, "!nova:x") == "", \
        "a sala nova acordou com a fita da anterior dentro"
    avisos = journal.avisos_pendentes(con)
    assert len(avisos) == 1 and "e agora?" in avisos[0]["texto"], \
        "o eco da mensagem que disparou a rotacao nao chegou a sala nova"


@prova("createRoom falho aborta a rotacao sem destruir nada")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!velha:x", "TI")
    r = RecepcaoDeMentira(con)
    r.falha_ao_criar = True
    nova = asyncio.run(rotacao.gira(r, "!velha:x", "TI", "@pedro:x", "idade"))
    assert nova is None, "devolveu sala que nao criou"
    assert r.descartou == [], "descartou a sala velha depois de falhar a nova"
    assert journal.cadeira_da_sala(con, "!velha:x") == "TI", "perdeu o endereco da cadeira"


# --- o ritual e a corrida do criterio 18 -----------------------------------

@prova("ritual toma a fita MORTA mesmo com a fita nova ja gravada")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!velha:x", "TI")
    job = chega(con)
    journal.reivindica(con, "!velha:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="fita-morta")

    r = RecepcaoDeMentira(con)
    asyncio.run(rotacao.gira(r, "!velha:x", "TI", "@pedro:x", "comando"))

    # A fita nova nasce e e gravada ANTES de o worker chegar ao ritual: e essa
    # a ordem que a rotacao real produz, e a que quebraria uma leitura da tabela.
    novo = chega(con, sala="!nova:x")
    journal.reivindica(con, "!nova:x")
    journal.conclui(con, novo, estado=journal.OK, texto="ja sou a nova", id_fita="fita-viva")

    ritual = journal.reivindica(con, "!velha:x")
    assert ritual is not None, "o ritual nao foi enfileirado"
    assert ritual["silencioso"], "o ritual saiu como giro comum — falaria na sala"
    assert ritual["id_fita"] == "fita-morta", \
        f"o ritual pegou a fita {ritual['id_fita']!r} — encerraria a fita viva"
    assert ritual["corpo"] == rituais.ENCERRAMENTO


@prova("giro silencioso nao promove fita nem vai a sala")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!s:x", "TI")
    job = chega(con, sala="!s:x")
    journal.reivindica(con, "!s:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="fita-viva")
    for j in journal.a_expedir(con):
        journal.marca_enviado(con, j["id"])

    journal.enfileira_silencioso(
        con, sala="!s:x", cadeira="TI", id_fita="fita-morta",
        corpo=rituais.ENCERRAMENTO, marca=journal.RITUAL,
    )
    tomado = journal.reivindica(con, "!s:x")
    journal.conclui(con, tomado["id"], estado=journal.OK, texto="", id_fita="fita-morta")
    assert journal.fita_da_sala(con, "!s:x") == "fita-viva", \
        "o ritual ressuscitou a fita morta como corrente da sala"
    assert journal.a_expedir(con) == [], \
        "o giro silencioso entrou na fila da sala — viraria 'terminou sem resposta'"


# --- compactacao e contagem (criterio 17) ----------------------------------

@prova("contador de giro dispara a ancora no marco, e so nele")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!s:x", "TI")
    job = chega(con, sala="!s:x")
    journal.reivindica(con, "!s:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="f1")
    vistos = [journal.conta_giro(con, "!s:x") for _ in range(10)]
    assert vistos == list(range(1, 11)), f"contagem errada: {vistos}"
    journal.zera_giros(con, "!s:x")
    assert journal.conta_giro(con, "!s:x") == 1, "zerar nao zerou"
    assert journal.conta_giro(con, "!sem-fita:x") == 0, \
        "contou giro em sala sem fita registrada"


@prova("a ancora e um giro silencioso a mais na fita corrente")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!s:x", "TI")
    job = chega(con, sala="!s:x")
    journal.reivindica(con, "!s:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="f1")
    for j in journal.a_expedir(con):
        journal.marca_enviado(con, j["id"])
    journal.enfileira_silencioso(
        con, sala="!s:x", cadeira="TI", id_fita=journal.fita_da_sala(con, "!s:x"),
        corpo=rituais.ANCORA, marca=journal.ANCORA,
    )
    tomado = journal.reivindica(con, "!s:x")
    assert tomado["id_fita"] == "f1", "a ancora abriu fita nova em vez de ancorar a viva"
    assert tomado["event_id"].startswith(f"pf!{journal.ANCORA}:"), \
        "a marca nao distingue ancora de ritual — o worker fecharia o slot da fita viva"


# --- degradacao declarada (secao 2, passo 4) --------------------------------

@prova("ritual atrasado vira aviso na sala nova, uma vez so")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!velha:x", "TI")
    job = chega(con)
    journal.reivindica(con, "!velha:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="f1")
    r = RecepcaoDeMentira(con)
    asyncio.run(rotacao.gira(r, "!velha:x", "TI", "@pedro:x", "idade"))
    for a in journal.avisos_pendentes(con):
        journal.marca_aviso_enviado(con, a["id"])

    assert asyncio.run(rotacao.declara_atraso(r)) == 0, \
        "avisou antes do teto — ritual rapido nao e degradacao"
    con.execute("UPDATE rotacoes SET em = ?", (time.time() - rotacao.TETO_RITUAL_S - 1,))
    assert asyncio.run(rotacao.declara_atraso(r)) == 1, "nao avisou depois do teto"
    avisos = journal.avisos_pendentes(con)
    assert len(avisos) == 1 and avisos[0]["sala"] == "!nova:x", \
        "o aviso de mesa atrasada foi para a sala errada"
    assert asyncio.run(rotacao.declara_atraso(r)) == 0, "avisou duas vezes"


@prova("ritual concluido dentro do teto nunca vira aviso")
def _():
    _, con = novo_journal()
    journal.grava_cadeira(con, "!velha:x", "TI")
    job = chega(con)
    journal.reivindica(con, "!velha:x")
    journal.conclui(con, job, estado=journal.OK, texto="oi", id_fita="f1")
    r = RecepcaoDeMentira(con)
    asyncio.run(rotacao.gira(r, "!velha:x", "TI", "@pedro:x", "idade"))
    ritual = journal.reivindica(con, "!velha:x")
    journal.conclui(con, ritual["id"], estado=journal.OK, texto="")
    con.execute("UPDATE rotacoes SET em = ?", (time.time() - rotacao.TETO_RITUAL_S - 1,))
    assert asyncio.run(rotacao.declara_atraso(r)) == 0, \
        "ritual ja fechado gerou aviso de atraso"


# --- migracao --------------------------------------------------------------

@prova("migracao e idempotente sobre banco do esquema anterior")
def _():
    import sqlite3
    caminho = os.path.join(tempfile.gettempdir(), f"prova-migra-{os.getpid()}.db")
    for sufixo in ("", "-wal", "-shm"):
        try:
            os.unlink(caminho + sufixo)
        except FileNotFoundError:
            pass
    antigo = sqlite3.connect(caminho)
    antigo.executescript("""
        CREATE TABLE fitas (sala TEXT PRIMARY KEY, id_fita TEXT NOT NULL, atualizado_em REAL NOT NULL);
        CREATE TABLE salas (sala TEXT PRIMARY KEY, cadeira TEXT NOT NULL, atualizado_em REAL NOT NULL);
        CREATE TABLE jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
            sala TEXT NOT NULL, cadeira TEXT NOT NULL, remetente TEXT NOT NULL, corpo TEXT NOT NULL,
            id_fita TEXT NOT NULL DEFAULT '', estado TEXT NOT NULL, detalhe TEXT NOT NULL DEFAULT '',
            texto TEXT NOT NULL DEFAULT '', reiniciada INTEGER NOT NULL DEFAULT 0,
            criado_em REAL NOT NULL, iniciado_em REAL, batida_em REAL, concluido_em REAL,
            partes_enviadas INTEGER NOT NULL DEFAULT 0, enviado_em REAL);
        INSERT INTO salas VALUES ('!antiga:x', 'TI', 1.0);
    """)
    antigo.commit()
    antigo.close()

    for _ in range(2):  # duas subidas seguidas: ALTER TABLE nao pode repetir
        con = journal.abre(caminho)
        colunas = {l["name"] for l in con.execute("PRAGMA table_info(jobs)")}
        assert "silencioso" in colunas, "jobs nao ganhou silencioso"
        assert journal.cadeira_da_sala(con, "!antiga:x") == "TI", "perdeu dado na migracao"
        con.close()


if __name__ == "__main__":
    print("prova do ciclo de vida da fita — rotacao, ritual, ancora e degradacao")
    if falhas:
        print(f"\n{len(falhas)} falha(s): {', '.join(falhas)}")
        sys.exit(1)
    print("\ntudo passou")
