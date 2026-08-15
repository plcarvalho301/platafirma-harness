#!/usr/bin/env python3
"""Prova de ponta a ponta das DUAS pecas do card 458.

Sobe um homeserver de mentira, o receptor de verdade e o worker de verdade, e
empurra transacao como o Synapse empurraria. O que se mede e o que chegou na
sala — que e onde os criterios de aceite moram.

    docker run --rm -v "$PWD:/chat:ro" --entrypoint python \\
      platafirma/chat-recepcao:local /chat/testes/prova-ponta-a-ponta.py

De mentira e SO o homeserver e o verbo (o duble do card 459). Receptor, worker,
journal, dedupe, typing, fatiamento e download de anexo sao os de producao.

Cobre: 2 (typing cessa no envio), 3 (falha vira mensagem), 4 (HTML), 5 e 15
(fatiamento em ordem), 6 (so a resposta final), 14 (dedupe) e 19 (anexo).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from aiohttp import ClientSession, web

CHAT = "/chat"
PORTA_HS = 18099
PORTA_AS = 18098
DOMINIO = "chat.teste"
AS_TOKEN, HS_TOKEN = "astok-de-teste", "hstok-de-teste"
CADEIRA = "TI"
USUARIO = f"@_pf{CADEIRA}:{DOMINIO}"
DONO = f"@pedro:{DOMINIO}"

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 2048

falhas: list[str] = []
_n = 0


def prova(nome: str, condicao: bool, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok   {nome}")
    else:
        falhas.append(nome)
        print(f"  FALHA {nome}: {detalhe}")


# --- homeserver de mentira -------------------------------------------------


class Homeserver:
    """So o bastante para a mautrix conversar. Guarda tudo o que recebe: e a
    unica testemunha do que o dono veria no celular."""

    def __init__(self) -> None:
        self.enviados: list[dict] = []
        self.typing: list[tuple[str, int]] = []
        self.pedidos: list[str] = []
        self._seq = 0

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/_matrix/client/versions", self.versoes)
        app.router.add_put("/_matrix/client/v3/rooms/{sala}/typing/{quem}", self.digitando)
        app.router.add_put("/_matrix/client/v3/rooms/{sala}/send/{tipo}/{txn}", self.envia)
        app.router.add_get("/_matrix/client/v3/rooms/{sala}/joined_members", self.membros)
        app.router.add_get("/_matrix/client/v3/rooms/{sala}/state/{tipo}{cauda:.*}", self.estado)
        app.router.add_get("/_matrix/client/v1/media/download/{srv}/{id}", self.midia)
        app.router.add_post("/_matrix/client/v3/join/{sala}", self.entra)
        app.router.add_post("/_matrix/client/v3/rooms/{sala}/join", self.entra)
        app.router.add_route("*", "/{cauda:.*}", self.qualquer)
        return app

    async def versoes(self, _p):
        return web.json_response({"versions": ["v1.1", "v1.4", "v1.11"]})

    async def digitando(self, p):
        corpo = await p.json()
        self.typing.append((p.match_info["sala"], int(corpo.get("timeout", 0) or 0)))
        return web.json_response({})

    async def envia(self, p):
        self._seq += 1
        self.enviados.append({
            "sala": p.match_info["sala"],
            "tipo": p.match_info["tipo"],
            "conteudo": await p.json(),
        })
        return web.json_response({"event_id": f"$enviado{self._seq}"})

    async def membros(self, p):
        return web.json_response({"joined": {DONO: {}, USUARIO: {}}})

    async def estado(self, p):
        """Estado da sala. A mautrix le `m.room.power_levels` e `m.room.create`
        ANTES de cada envio (IntentAPI._ensure_has_power_level_for), e o Synapse
        de verdade responde os dois: duble que devolve {} faz o envio explodir
        na desserializacao, e o erro aparece longe de onde nasceu."""
        tipo = p.match_info["tipo"]
        conteudo = {
            "m.room.power_levels": {"users_default": 0, "events_default": 0,
                                    "state_default": 50, "users": {}, "events": {}},
            "m.room.create": {"creator": USUARIO, "room_version": "10"},
            "m.room.member": {"membership": "join"},
        }.get(tipo, {})
        if p.rel_url.query.get("format") == "event":
            return web.json_response({
                "type": tipo, "room_id": p.match_info["sala"], "event_id": "$estado",
                "sender": USUARIO, "origin_server_ts": 0,
                "state_key": p.match_info["cauda"].lstrip("/"), "content": conteudo,
            })
        return web.json_response(conteudo)

    async def midia(self, p):
        tipo = {"png": "image/png", "elf": "application/x-elf"}.get(
            p.match_info["id"], "application/octet-stream")
        return web.Response(body=PNG, content_type=tipo)

    async def entra(self, p):
        """`join` tem de devolver o room_id: a mautrix o le direto do corpo, e
        duble que devolve {} rebenta com KeyError dentro do ensure_joined —
        longe da chamada que o disparou."""
        return web.json_response({"room_id": p.match_info["sala"]})

    async def qualquer(self, p):
        self.pedidos.append(f"{p.method} {p.path}")
        return web.json_response({})

    # --- leitura do que chegou ---

    def na_sala(self, sala: str) -> list[dict]:
        return [e["conteudo"] for e in self.enviados if e["sala"] == sala]

    async def espera(self, sala: str, quantos: int, teto: float = 40.0) -> list[dict]:
        fim = time.monotonic() + teto
        while time.monotonic() < fim:
            if len(self.na_sala(sala)) >= quantos:
                await asyncio.sleep(0.5)  # deixa chegar o que vier depois
                return self.na_sala(sala)
            await asyncio.sleep(0.2)
        return self.na_sala(sala)


# --- eventos ---------------------------------------------------------------


def _id() -> str:
    global _n
    _n += 1
    return f"$ev{_n}"


def entrada(sala: str) -> dict:
    return {"type": "m.room.member", "event_id": _id(), "room_id": sala,
            "sender": USUARIO, "state_key": USUARIO, "origin_server_ts": 0,
            "content": {"membership": "join"}}


def texto(sala: str, corpo: str, *, remetente: str = DONO, event_id: str | None = None) -> dict:
    return {"type": "m.room.message", "event_id": event_id or _id(), "room_id": sala,
            "sender": remetente, "origin_server_ts": 0,
            "content": {"msgtype": "m.text", "body": corpo}}


def midia(sala: str, *, nome: str, mime: str, tamanho: int, media: str = "png") -> dict:
    return {"type": "m.room.message", "event_id": _id(), "room_id": sala,
            "sender": DONO, "origin_server_ts": 0,
            "content": {"msgtype": "m.image", "body": nome,
                        "url": f"mxc://{DOMINIO}/{media}",
                        "info": {"mimetype": mime, "size": tamanho}}}


async def empurra(sessao: ClientSession, txn: str, eventos: list[dict]) -> int:
    async with sessao.put(
        f"http://127.0.0.1:{PORTA_AS}/_matrix/app/v1/transactions/{txn}",
        json={"events": eventos},
        headers={"Authorization": f"Bearer {HS_TOKEN}"},
    ) as r:
        await r.read()
        return r.status


class Pecas:
    """As duas pecas como processos que o teste pode derrubar em separado — e o
    que o criterio 14 cobra depois do comentario 310.

    As duas falam no MESMO stdout do teste: quando um criterio reprova, o log
    delas e a primeira coisa que se quer ler, e escondido em pipe ele some.
    """

    def __init__(self, ambiente: dict) -> None:
        self.ambiente = ambiente
        self.receptor: subprocess.Popen | None = None
        self.worker: subprocess.Popen | None = None

    def sobe_receptor(self) -> None:
        self.receptor = subprocess.Popen(
            [sys.executable, "-u", "/opt/chat/recepcao.py"], env=self.ambiente)

    def sobe_worker(self) -> None:
        self.worker = subprocess.Popen(
            [sys.executable, "-u", f"{CHAT}/worker/worker.py"], env=self.ambiente)

    def derruba(self, proc: subprocess.Popen | None) -> None:
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    def para_tudo(self) -> None:
        self.derruba(self.receptor)
        self.derruba(self.worker)


# --- corrida ---------------------------------------------------------------


async def principal() -> int:
    raiz = tempfile.mkdtemp(prefix="prova-chat-")
    journal_db = os.path.join(raiz, "journal.db")
    fitas = os.path.join(raiz, "fitas")
    os.makedirs(fitas)

    hs = Homeserver()
    runner = web.AppRunner(hs.app())
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PORTA_HS).start()

    ambiente = dict(os.environ)
    ambiente.update({
        "AS_SERVIDOR": f"http://127.0.0.1:{PORTA_HS}",
        "AS_DOMINIO": DOMINIO,
        "AS_TOKEN": AS_TOKEN,
        "HS_TOKEN": HS_TOKEN,
        "AS_BOT": "_pf",
        "AS_ID": "pf",
        "AS_PORTA": str(PORTA_AS),
        "CHAT_JOURNAL": journal_db,
        "CHAT_FITAS_RAIZ": fitas,
        "CHAT_INTERVALO_EXPEDIDOR": "0.5",
        "CHAT_INTERVALO_TYPING": "2",
        "CHAT_INTERVALO_VIGIA": "3",
        "CHAT_ANEXO_TETO": str(4 * 1024),
        "CHAT_VERBO": f"{CHAT}/worker/duble-despachar.py",
        "CHAT_INTERVALO_RONDA": "0.5",
    })

    pecas = Pecas(ambiente)
    pecas.sobe_receptor()
    pecas.sobe_worker()
    try:
        async with ClientSession() as sessao:
            await espera_de_pe(sessao)
            await corpo_da_prova(sessao, hs, fitas, pecas)
    finally:
        pecas.para_tudo()
        await runner.cleanup()
        shutil.rmtree(raiz, ignore_errors=True)

    if falhas:
        print(f"\n{len(falhas)} falha(s): {', '.join(falhas)}")
        return 1
    print("\ntudo passou")
    return 0


async def espera_de_pe(sessao: ClientSession) -> None:
    fim = time.monotonic() + 30
    while time.monotonic() < fim:
        try:
            async with sessao.get(f"http://127.0.0.1:{PORTA_AS}/estado") as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        await asyncio.sleep(0.3)
    raise SystemExit("o receptor nao subiu")


async def corpo_da_prova(sessao: ClientSession, hs: Homeserver, fitas: str,
                         pecas: "Pecas") -> None:
    # --- giro completo, com formatacao ---
    sala = "!um:chat.teste"
    codigo = await empurra(sessao, "t1", [entrada(sala), texto(sala, "quem e voce?")])
    prova("a transacao e confirmada (ack-then-work)", codigo == 200, f"status {codigo}")

    chegou = await hs.espera(sala, 1)
    prova("criterio 1/3 — a mensagem do dono vira resposta na sala", len(chegou) == 1,
          f"{len(chegou)} mensagens")
    if chegou:
        c = chegou[0]
        prova("criterio 4 — a resposta vai com <table> em formatted_body",
              "<table>" in c.get("formatted_body", ""), c.get("formatted_body", "")[:120])
        prova("criterio 4 — code block vira <pre><code>",
              "<pre><code" in c.get("formatted_body", ""))
        prova("a resposta e da cadeira (m.text), nao aviso do sistema",
              c.get("msgtype") == "m.text", str(c.get("msgtype")))
    prova("criterio 6 — so a resposta final entra na sala (um evento, nao um por passo)",
          len(chegou) == 1, f"{len(chegou)} eventos para um giro")

    typing_da_sala = [t for t in hs.typing if t[0] == sala]
    prova("criterio 2 — typing ligou durante a inferencia",
          any(t[1] > 0 for t in typing_da_sala), str(typing_da_sala))
    prova("criterio 2 — typing cessou por ato nosso, nao por expiracao",
          typing_da_sala and typing_da_sala[-1][1] == 0, str(typing_da_sala))

    # --- dedupe: a reentrega do homeserver ---
    sala2 = "!dois:chat.teste"
    evento = texto(sala2, "pergunta unica", event_id="$repetido")
    await empurra(sessao, "t2", [entrada(sala2), evento])
    await hs.espera(sala2, 1)
    # txn NOVO com o MESMO event_id: e o que dribla o dedupe em memoria da lib e
    # deixa so o nosso, que e o persistente.
    await empurra(sessao, "t3", [evento])
    await asyncio.sleep(4)
    prova("criterio 14 — reentrega do mesmo evento nao produz segunda resposta",
          len(hs.na_sala(sala2)) == 1, f"{len(hs.na_sala(sala2))} respostas")

    # --- erro estruturado vira mensagem, nunca silencio ---
    sala3 = "!tres:chat.teste"
    await empurra(sessao, "t4", [entrada(sala3), texto(sala3, "DUBLE:erro")])
    erro = await hs.espera(sala3, 1)
    prova("criterio 3 — giro que falha vira mensagem de erro na sala", len(erro) == 1)
    if erro:
        prova("o erro e aviso do sistema (m.notice), com o detalhe do verbo",
              erro[0].get("msgtype") == "m.notice"
              and "nao conseguiu abrir a fita" in erro[0].get("body", ""),
              erro[0].get("body", "")[:120])
        prova("stack trace nao vai a sala",
              "Traceback" not in erro[0].get("body", ""))

    # --- cota ---
    sala4 = "!quatro:chat.teste"
    await empurra(sessao, "t5", [entrada(sala4), texto(sala4, "DUBLE:cota")])
    cota = await hs.espera(sala4, 1)
    prova("estouro de cota diz o horario de volta",
          cota and "03:40" in cota[0].get("body", ""),
          cota[0].get("body", "")[:120] if cota else "nada chegou")

    # --- resposta longa, fatiada e em ordem ---
    sala5 = "!cinco:chat.teste"
    await empurra(sessao, "t6", [entrada(sala5), texto(sala5, "DUBLE:longo")])
    partes = await hs.espera(sala5, 2, teto=60)
    prova("criterio 5 — resposta longa chega fatiada", len(partes) > 1, f"{len(partes)} partes")
    if len(partes) > 1:
        marcadores = [p["body"].strip().splitlines()[-1] for p in partes]
        prova("criterio 15 — as partes chegam em ordem, numeradas",
              marcadores == [f"({i}/{len(partes)})" for i in range(1, len(partes) + 1)],
              str(marcadores[:4]))
        prova("nenhuma parte estoura o teto de evento",
              all(len(json.dumps(p, ensure_ascii=False).encode()) < 65536 for p in partes))
        prova("nenhuma parte parte um bloco de codigo ao meio",
              all(p["body"].count("```") % 2 == 0 for p in partes))

    # --- anexo aceito ---
    sala6 = "!seis:chat.teste"
    await empurra(sessao, "t7", [entrada(sala6),
                                 midia(sala6, nome="print da tela.png", mime="image/png",
                                       tamanho=len(PNG))])
    await hs.espera(sala6, 1)
    inbox = os.path.join(fitas, CADEIRA, "inbox")
    arquivos = sorted(os.listdir(inbox)) if os.path.isdir(inbox) else []
    prova("criterio 19 — o anexo e gravado no inbox da fita", len(arquivos) == 1, str(arquivos))
    if arquivos:
        gravado = os.path.join(inbox, arquivos[0])
        prova("o arquivo chegou inteiro e com nome saneado",
              os.path.getsize(gravado) == len(PNG) and " " not in arquivos[0], arquivos[0])
    respondeu = hs.na_sala(sala6)
    prova("o anexo vira giro (a cadeira responde), nao recusa",
          respondeu and respondeu[0].get("msgtype") == "m.text",
          respondeu[0].get("body", "")[:80] if respondeu else "nada")

    # --- anexo recusado: MIME fora da lista ---
    sala7 = "!sete:chat.teste"
    await empurra(sessao, "t8", [entrada(sala7),
                                 midia(sala7, nome="binario", mime="application/x-elf",
                                       tamanho=len(PNG), media="elf")])
    recusa = await hs.espera(sala7, 1)
    prova("criterio 19 — MIME fora da lista vira recusa explicita, nao silencio",
          recusa and "Anexo recusado" in recusa[0].get("body", ""),
          recusa[0].get("body", "")[:120] if recusa else "nada chegou")

    # --- anexo recusado: acima do teto ---
    sala8 = "!oito:chat.teste"
    await empurra(sessao, "t9", [entrada(sala8),
                                 midia(sala8, nome="grande.png", mime="image/png",
                                       tamanho=99 * 1024 * 1024)])
    grande = await hs.espera(sala8, 1)
    prova("criterio 19 — arquivo acima do teto vira recusa que diz o limite",
          grande and "teto" in grande[0].get("body", ""),
          grande[0].get("body", "")[:120] if grande else "nada chegou")

    # --- guarda de laco ---
    sala9 = "!nove:chat.teste"
    await empurra(sessao, "t10", [entrada(sala9), texto(sala9, "eco", remetente=USUARIO)])
    await asyncio.sleep(4)
    prova("mensagem da propria cadeira nao vira giro (guarda de laco)",
          hs.na_sala(sala9) == [], str(hs.na_sala(sala9)))

    # --- sala sem evento de entrada: cai no /joined_members ---
    sala10 = "!dez:chat.teste"
    await empurra(sessao, "t11", [texto(sala10, "e sem ter visto a entrada?")])
    tarde = await hs.espera(sala10, 1)
    prova("sala desconhecida descobre a cadeira pelos membros", len(tarde) == 1,
          f"{len(tarde)} respostas")

    # --- criterio 14, na leitura do comentario 310 ---
    # Derrubada QUALQUER uma das duas pecas no meio do giro, o dono recebe OU a
    # resposta OU um erro. Nunca as duas, nunca duplicata, nunca silencio.
    sala11 = "!onze:chat.teste"
    await empurra(sessao, "t12", [entrada(sala11), texto(sala11, "DUBLE:demora")])
    await asyncio.sleep(2.5)  # o giro ja esta em curso no worker
    pecas.derruba(pecas.receptor)
    prova("o receptor foi derrubado com o giro em curso", pecas.receptor.poll() is not None)
    await asyncio.sleep(9)  # o worker termina com o receptor fora do ar
    prova("o worker sobreviveu a queda do receptor", pecas.worker.poll() is None)
    pecas.sobe_receptor()
    await espera_de_pe(sessao)
    voltou = await hs.espera(sala11, 1, teto=40)
    prova("criterio 14 — receptor derrubado com worker vivo: a RESPOSTA chega",
          len(voltou) == 1 and voltou[0].get("msgtype") == "m.text",
          voltou[0].get("body", "")[:80] if voltou else "nada chegou")
    prova("criterio 14 — e nao vira erro: giro que sobreviveu nao e falha",
          voltou and "falhou" not in voltou[0].get("body", ""),
          voltou[0].get("body", "")[:80] if voltou else "nada chegou")
    await asyncio.sleep(6)
    prova("criterio 14 — uma mensagem so, sem duplicata na volta",
          len(hs.na_sala(sala11)) == 1, f"{len(hs.na_sala(sala11))} mensagens")


if __name__ == "__main__":
    print("prova de ponta a ponta — homeserver e verbo de mentira, resto de verdade")
    sys.exit(asyncio.run(principal()))
