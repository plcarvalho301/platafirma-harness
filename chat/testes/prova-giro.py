#!/usr/bin/env python3
"""Prova do journal e do worker — a fronteira e o lado verbo (card 458).

Roda NO HOST, so com stdlib, contra um journal descartavel em /tmp e o duble do
verbo (o card 459 ainda nao mergeou):

    python3 testes/prova-giro.py

Cobre o criterio 14 pelas duas pontas que o comentario 302 acrescentou: dedupe
que sobrevive a reentrega, e cada peca derrubada em separado sem produzir
resposta duplicada. Sai 0 se tudo passou.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
CHAT = os.path.dirname(AQUI)
sys.path.insert(0, CHAT)

from comum import journal  # noqa: E402

DUBLE = os.path.join(CHAT, "worker", "duble-despachar.py")
WORKER = os.path.join(CHAT, "worker", "worker.py")

falhas = []
_n = 0


def novo_journal():
    global _n
    _n += 1
    caminho = os.path.join(tempfile.gettempdir(), f"prova-chat-{os.getpid()}-{_n}.db")
    for sufixo in ("", "-wal", "-shm"):
        try:
            os.unlink(caminho + sufixo)
        except FileNotFoundError:
            pass
    return caminho, journal.abre(caminho)


def chega(con, sala="!s1:x", cadeira="TI", corpo="oi", event_id=None):
    global _n
    _n += 1
    return journal.registra_chegada(
        con, event_id=event_id or f"$ev{_n}", txn_id="t1", sala=sala,
        cadeira=cadeira, remetente="@pedro:x", corpo=corpo,
    )


def roda_worker(caminho, *, mudo="240", espera=90):
    ambiente = dict(os.environ)
    ambiente.update({
        "CHAT_JOURNAL": caminho,
        "CHAT_VERBO": DUBLE,
        "CHAT_STREAM_MUDO_S": mudo,
        "CHAT_INTERVALO_RONDA": "0.2",
    })
    return subprocess.run(
        [sys.executable, WORKER, "--uma-volta"],
        env=ambiente, capture_output=True, text=True, timeout=espera,
    )


def prova(nome):
    def marca(fn):
        try:
            fn()
            print(f"  ok   {nome}")
        except AssertionError as erro:
            falhas.append(nome)
            print(f"  FALHA {nome}: {erro}")
        except Exception as erro:
            falhas.append(nome)
            print(f"  ERRO  {nome}: {erro!r}")
        return fn
    return marca


@prova("criterio 14 — reentrega do mesmo evento nao abre segundo giro")
def _():
    _, con = novo_journal()
    primeiro = chega(con, event_id="$mesmo")
    segundo = chega(con, event_id="$mesmo")
    assert primeiro is not None, "o primeiro deveria enfileirar"
    assert segundo is None, "a reentrega abriu um segundo giro"
    n = con.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
    assert n == 1, f"{n} jobs para o mesmo event_id"


@prova("recusa tambem entra no dedupe (criterio 19 nao repete na reentrega)")
def _():
    _, con = novo_journal()
    assert journal.registra_recusa(con, event_id="$r", txn_id="t", sala="!s:x") is True
    assert journal.registra_recusa(con, event_id="$r", txn_id="t", sala="!s:x") is False


@prova("fila por sala: um giro em curso por sala, na ordem de chegada")
def _():
    _, con = novo_journal()
    a, b = chega(con, corpo="primeiro"), chega(con, corpo="segundo")
    tomado = journal.reivindica(con, "!s1:x")
    assert tomado["id"] == a, "tomou fora de ordem"
    assert journal.reivindica(con, "!s1:x") is None, "tomou dois da mesma sala"
    journal.conclui(con, a, estado=journal.OK, texto="pronto")
    assert journal.reivindica(con, "!s1:x")["id"] == b, "nao liberou o proximo da fila"


@prova("paralelismo entre salas: sala ocupada nao trava a outra")
def _():
    _, con = novo_journal()
    chega(con, sala="!a:x")
    chega(con, sala="!b:x")
    assert journal.reivindica(con, "!a:x") is not None
    assert journal.reivindica(con, "!b:x") is not None, "a segunda sala ficou presa"


@prova("criterio 14 — worker atrasado nao esmaga a condenacao do vigia")
def _():
    _, con = novo_journal()
    job = chega(con)
    journal.reivindica(con, "!s1:x")
    assert journal.condena(con, job, estado=journal.TIMEOUT, detalhe="pendurado") is True
    venceu = journal.conclui(con, job, estado=journal.OK, texto="resposta atrasada")
    assert venceu is False, "o resultado atrasado sobrescreveu o erro ja lido na sala"
    linha = con.execute("SELECT estado, texto FROM jobs WHERE id = ?", (job,)).fetchone()
    assert linha["estado"] == journal.TIMEOUT and linha["texto"] == ""


@prova("vigia: giro fresco NAO e condenado, pendurado e")
def _():
    _, con = novo_journal()
    fresco = chega(con, sala="!a:x")
    velho = chega(con, sala="!b:x")
    journal.reivindica(con, "!a:x")
    journal.reivindica(con, "!b:x")
    con.execute("UPDATE jobs SET batida_em = batida_em - 600 WHERE id = ?", (velho,))
    pendurados = [j["id"] for j in journal.giros_pendurados(con, 270)]
    assert velho in pendurados, "giro sem batida ha 10 min nao foi pego"
    assert fresco not in pendurados, "condenou giro de worker vivo"


@prova("vigia: pendente atras de sala ocupada nao conta o relogio")
def _():
    _, con = novo_journal()
    chega(con, sala="!a:x")
    espera = chega(con, sala="!a:x")
    journal.reivindica(con, "!a:x")
    con.execute("UPDATE jobs SET criado_em = criado_em - 600 WHERE id = ?", (espera,))
    pendurados = [j["id"] for j in journal.giros_pendurados(con, 270)]
    assert espera not in pendurados, "condenou giro que so estava esperando a vez"


@prova("worker + duble: giro completo devolve ok, texto e id de fita")
def _():
    caminho, con = novo_journal()
    job = chega(con)
    saida = roda_worker(caminho)
    assert saida.returncode == 0, saida.stderr[-400:]
    linha = con.execute("SELECT * FROM jobs WHERE id = ?", (job,)).fetchone()
    assert linha["estado"] == journal.OK, f"{linha['estado']} / {linha['detalhe']}"
    assert "| criterio | o que prova |" in linha["texto"], "a resposta nao chegou inteira"
    fita = con.execute("SELECT id_fita FROM fitas WHERE sala = '!s1:x'").fetchone()
    assert fita["id_fita"] == "fita-de-TI", "o id de fita nao voltou ao journal"
    assert linha["reiniciada"] == 1, "fita nova deveria vir marcada como reiniciada"


@prova("worker + duble: a segunda mensagem reusa a fita devolvida")
def _():
    caminho, con = novo_journal()
    chega(con)
    roda_worker(caminho)
    segundo = chega(con, corpo="e agora?")
    roda_worker(caminho)
    linha = con.execute("SELECT * FROM jobs WHERE id = ?", (segundo,)).fetchone()
    assert linha["estado"] == journal.OK
    assert linha["reiniciada"] == 0, "abriu fita nova quando havia fita"


@prova("estados estruturados: cota, erro e ok-sem-texto chegam como campo")
def _():
    for gatilho, esperado in (("DUBLE:cota", journal.COTA),
                              ("DUBLE:erro", journal.ERRO),
                              ("DUBLE:vazio", journal.OK)):
        caminho, con = novo_journal()
        job = chega(con, corpo=gatilho)
        roda_worker(caminho)
        linha = con.execute("SELECT * FROM jobs WHERE id = ?", (job,)).fetchone()
        assert linha["estado"] == esperado, f"{gatilho} virou {linha['estado']}"
        if esperado == journal.COTA:
            assert "03:40" in linha["detalhe"], "perdeu o horario de volta da cota"


@prova("verbo que nao cumpre o contrato vira erro, nao silencio")
def _():
    caminho, con = novo_journal()
    job = chega(con, corpo="DUBLE:lixo")
    roda_worker(caminho)
    linha = con.execute("SELECT * FROM jobs WHERE id = ?", (job,)).fetchone()
    assert linha["estado"] == journal.ERRO, linha["estado"]
    assert "sem JSON valido" in linha["detalhe"], linha["detalhe"]


@prova("verbo ausente do PATH vira erro nomeado")
def _():
    caminho, con = novo_journal()
    job = chega(con)
    ambiente = dict(os.environ)
    ambiente.update({"CHAT_JOURNAL": caminho, "CHAT_VERBO": "/nao/existe/verbo",
                     "CHAT_INTERVALO_RONDA": "0.2"})
    subprocess.run([sys.executable, WORKER, "--uma-volta"], env=ambiente,
                   capture_output=True, text=True, timeout=60)
    linha = con.execute("SELECT * FROM jobs WHERE id = ?", (job,)).fetchone()
    assert linha["estado"] == journal.ERRO
    assert "PATH" in linha["detalhe"], linha["detalhe"]


@prova("watchdog do worker: stream mudo vira timeout e mata o grupo")
def _():
    caminho, con = novo_journal()
    job = chega(con, corpo="DUBLE:pendura")
    comeco = time.monotonic()
    roda_worker(caminho, mudo="3", espera=60)
    gasto = time.monotonic() - comeco
    linha = con.execute("SELECT * FROM jobs WHERE id = ?", (job,)).fetchone()
    assert linha["estado"] == journal.TIMEOUT, f"{linha['estado']} / {linha['detalhe']}"
    assert "stream do verbo" in linha["detalhe"], linha["detalhe"]
    assert gasto < 30, f"o watchdog demorou {gasto:.0f}s"
    # O padrao inclui o verbo `despachar` de proposito: "duble-despachar.py"
    # sozinho casa com a propria linha de comando de quem chamou este teste.
    sobrou = subprocess.run(["pgrep", "-f", r"duble-despachar\.py despachar"],
                            capture_output=True, text=True).stdout.strip()
    assert not sobrou, f"processo do verbo sobreviveu ao kill: pid {sobrou}"


@prova("criterio 14 — worker derrubado no meio: o vigia condena e o worker desiste")
def _():
    caminho, con = novo_journal()
    job = chega(con, corpo="DUBLE:pendura")
    ambiente = dict(os.environ)
    ambiente.update({"CHAT_JOURNAL": caminho, "CHAT_VERBO": DUBLE,
                     "CHAT_STREAM_MUDO_S": "300", "CHAT_INTERVALO_RONDA": "0.2"})
    proc = subprocess.Popen([sys.executable, WORKER, "--uma-volta"], env=ambiente,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for _espera in range(50):
            time.sleep(0.2)
            if con.execute("SELECT 1 FROM jobs WHERE id = ? AND estado = ?",
                           (job, journal.EM_CURSO)).fetchone():
                break
        else:
            raise AssertionError("o worker nao chegou a tomar o giro")
        # E o que o receptor faz quando o worker para de bater: condena, e a
        # mensagem de erro ja foi para a sala.
        assert journal.condena(con, job, estado=journal.TIMEOUT,
                               detalhe="Sem sinal de vida do worker.") is True
        proc.wait(timeout=40)
    finally:
        if proc.poll() is None:
            proc.kill()
    linha = con.execute("SELECT * FROM jobs WHERE id = ?", (job,)).fetchone()
    assert linha["estado"] == journal.TIMEOUT, linha["estado"]
    assert linha["texto"] == "", "o worker escreveu resposta depois do erro na sala"
    assert "Sem sinal de vida" in linha["detalhe"], linha["detalhe"]


@prova("criterio 14 — receptor derrubado no meio do envio retoma na parte certa")
def _():
    _, con = novo_journal()
    job = chega(con)
    journal.reivindica(con, "!s1:x")
    journal.conclui(con, job, estado=journal.OK, texto="resposta de tres partes")
    # O receptor mandou duas partes e caiu antes da terceira.
    journal.marca_parte_enviada(con, job, 2)
    pendente = journal.a_expedir(con)
    assert [j["id"] for j in pendente] == [job], "o job sumiu da fila de expedicao"
    assert pendente[0]["partes_enviadas"] == 2, "religou sem lembrar o que ja mandou"
    journal.marca_enviado(con, job)
    assert journal.a_expedir(con) == [], "job enviado continuou na fila — reenviaria"


if __name__ == "__main__":
    print("prova do journal e do worker (duble no lugar do verbo do card 459)")
    if falhas:
        print(f"\n{len(falhas)} falha(s): {', '.join(falhas)}")
        sys.exit(1)
    print("\ntudo passou")
