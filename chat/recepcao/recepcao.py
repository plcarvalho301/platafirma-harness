#!/usr/bin/env python3
"""Recepcao da PlataFirma — o lado MATRIX do giro (card 458, fatia B-1).

Esta peca faz tudo o que fala Matrix, e so isso: aceita a transacao, deduplica,
enfileira no journal, liga o typing, baixa anexo para o inbox da fita, formata,
fatia e envia a resposta. Ela NAO chama verbo e nao sabe o que e Claude Code.

Do outro lado da fronteira mora o worker (chat/worker/worker.py), no host, sob
systemd --user: ele chama `chat despachar` e nunca fala Matrix. A partida e por
DIRECAO, e nao por etapa — topologia decidida por claudinho-TI no comentario 302
do card. A razao e medida: em docker rootless o container nao alcanca o host, e
publicar a porta do Synapse no loopback poria a Admin API fora da rede interna,
contra arq:0026. Partindo assim, nenhuma porta nova e nenhuma travessia.

A UNICA fronteira e o journal SQLite em WAL, no bind mount (chat/comum/journal.py).

ACK-THEN-WORK, ao pe da letra: a mautrix 0.21.1 aguarda o handler antes de
responder 200 (medido em `AppServiceServerMixin.handle_transaction`), entao o
que fica dentro do ack e exatamente o que o card manda persistir antes de
qualquer giro — dedupe e job. O giro roda noutro PROCESSO, do outro lado do
arquivo.

NUNCA SILENCIO, em tres aneis (posicao de claudinho-TI):
  1. status estruturado do verbo vira mensagem formatada na sala (expedidor);
  2. watchdog — o de primeira ordem e do worker, sobre o silencio do stream; o
     de segunda ordem e o `vigia` daqui, sobre o silencio do proprio worker;
  3. journal + varredura na subida cobrem a morte desta peca.
Stack trace nao vai a sala em caminho nenhum.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import os
import sys

from aiohttp import web
from mautrix.appservice import AppService
from mautrix.types import EventType, MessageType

sys.path.insert(0, "/opt/chat")

import anexo as anexos  # noqa: E402
import formata  # noqa: E402
from comum import journal  # noqa: E402
from comum.cadeiras import cadeiras, eh_de_cadeira, mxid_da_cadeira, sufixo_canonico  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("chat-recepcao")

# Silencio tolerado antes de o vigia declarar o giro pendurado. E DE PROPOSITO
# maior que o watchdog do worker (240 s de stream mudo): o de la e o de primeira
# ordem e tem de disparar primeiro, senao o receptor condena giro de um worker
# que ia matar sozinho. E ainda cabe no criterio 3, que da 5 min entre a falha e
# a mensagem de erro: 270 s + a volta do laco (15 s) = 4,75 min.
PENDURADO_S = float(os.environ.get("CHAT_PENDURADO_S", "270"))
INTERVALO_VIGIA = float(os.environ.get("CHAT_INTERVALO_VIGIA", "15"))
INTERVALO_EXPEDIDOR = float(os.environ.get("CHAT_INTERVALO_EXPEDIDOR", "2"))
# O typing do Matrix expira sozinho; renovar antes disso e o que impede o
# "digitando" de sumir no meio de um giro longo. Cessar e sempre ato nosso,
# em `finally` — typing pendurado por expiracao e o defeito medido em
# hermes-agent #6016, e virou o criterio 2.
TYPING_MS = int(os.environ.get("CHAT_TYPING_MS", "30000"))
INTERVALO_TYPING = float(os.environ.get("CHAT_INTERVALO_TYPING", "20"))
ANEXO_TIMEOUT = float(os.environ.get("CHAT_ANEXO_TIMEOUT", "30"))

TEXTOS = (MessageType.TEXT, MessageType.NOTICE, MessageType.EMOTE)
MIDIAS = (MessageType.IMAGE, MessageType.FILE)

_txn_atual: contextvars.ContextVar[str] = contextvars.ContextVar("txn", default="")


def exigido(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise SystemExit(f"falta a variavel {nome} — ela desce do cofre pelo .env da stack")
    return valor


class Recepcao:
    def __init__(self, appserv: AppService, con, dominio: str, prefixo: str) -> None:
        self.appserv = appserv
        self.con = con
        self.dominio = dominio
        self.prefixo = prefixo  # localpart do bot, ex. "_pf"
        self.em_voo: set[str] = set()
        self.sem_cadeira = 0

    # --- identidade: de que cadeira e esta sala ---------------------------

    def eh_do_namespace(self, mxid: str) -> bool:
        """Qualquer usuario do AS, INCLUSIVE o bot @_pf.

        Guarda de laco, e de proposito mais larga que `eh_de_cadeira`: aquela
        responde "e uma cadeira?" e exclui o bot, que e o certo para identidade;
        esta responde "e nosso?", e o bot tambem e. Trocar uma pela outra faria
        m.notice do bot — o que a rotacao do card 449 vai emitir — virar giro.
        """
        return mxid.startswith(f"@{self.prefixo}") and mxid.endswith(f":{self.dominio}")

    def aprende_pelo_membro(self, evento) -> None:
        """A sala aprende a cadeira dela pelo evento de entrada do usuario da
        cadeira — que e o ato do card B-3 e o unico que chega aqui de graca.

        Nao ha rota melhor: o bot da recepcao nao esta nas sete salas, e
        `/joined_members` exige estar dentro. Como o homeserver REENTREGA
        transacao nao confirmada, esta peca fora do ar quando o B-3 provisionar
        nao perde o evento — ele volta na subida.
        """
        alvo = getattr(evento, "state_key", "") or ""
        membro = getattr(getattr(evento, "content", None), "membership", None)
        if not alvo or membro is None or str(membro) != "join":
            return
        if not eh_de_cadeira(alvo, self.dominio, self.prefixo):
            return
        cadeira = sufixo_canonico(alvo)
        if cadeira:
            journal.grava_cadeira(self.con, evento.room_id, cadeira)
            log.info("sala %s e da cadeira %s", evento.room_id, cadeira)

    async def cadeira_da_sala(self, sala: str) -> str | None:
        cadeira = journal.cadeira_da_sala(self.con, sala)
        if cadeira:
            return cadeira
        # Ultimo recurso: se o bot estiver na sala, ele enxerga os membros.
        try:
            membros = await self.appserv.intent.get_joined_members(sala)
        except Exception:
            # Falha esperada quando o bot nao esta na sala, que e o caso das
            # sete: o alcance vem do evento de entrada. Logado com a causa
            # mesmo assim — sala muda e sem motivo visivel e o pior estado.
            log.warning("nao consegui listar os membros de %s", sala, exc_info=True)
            self.sem_cadeira += 1
            return None
        for mxid in membros:
            achada = sufixo_canonico(mxid) if eh_de_cadeira(
                mxid, self.dominio, self.prefixo) else None
            if achada:
                journal.grava_cadeira(self.con, sala, achada)
                return achada
        self.sem_cadeira += 1
        return None

    def intent_da(self, cadeira: str):
        """Intent do usuario da cadeira.

        O MXID sai de `mxid_da_cadeira`, nunca de concatenacao: o localpart do
        Matrix e minusculo com separador (`_pf_ti`) e o sufixo do harness nao
        (`TI`). Montar na mao aqui foi o defeito que o comentario 318 pegou —
        cada giro ia para uma cadeira que nao existe.
        """
        mxid = mxid_da_cadeira(cadeira, self.dominio, self.prefixo)
        if mxid is None:
            raise ValueError(f"cadeira sem persona: {cadeira!r}")
        return self.appserv.intent.api.intent(mxid)

    # --- chegada ----------------------------------------------------------

    async def recebe(self, evento) -> None:
        if evento.type == EventType.ROOM_MEMBER:
            self.aprende_pelo_membro(evento)
            return
        if evento.type != EventType.ROOM_MESSAGE:
            return
        # Guarda de laco: mensagem nossa nao vira giro. Sem isto a resposta da
        # cadeira volta como transacao e a sala entra em recursao.
        if self.eh_do_namespace(evento.sender):
            return

        sala, event_id = evento.room_id, evento.event_id
        if event_id in self.em_voo:
            return
        if self.con.execute(
            "SELECT 1 FROM recebidos WHERE event_id = ?", (event_id,)
        ).fetchone():
            return

        cadeira = await self.cadeira_da_sala(sala)
        if cadeira is None:
            log.error("sala %s sem cadeira conhecida — evento %s ignorado", sala, event_id)
            return

        self.em_voo.add(event_id)
        try:
            await self._enfileira(evento, sala, cadeira)
        finally:
            self.em_voo.discard(event_id)

    async def _enfileira(self, evento, sala: str, cadeira: str) -> None:
        conteudo = evento.content
        tipo = getattr(conteudo, "msgtype", None)
        txn = _txn_atual.get()
        intent = self.intent_da(cadeira)

        if tipo in MIDIAS:
            info = getattr(conteudo, "info", None)
            try:
                caminho, tamanho, mime = await asyncio.wait_for(
                    anexos.baixa(
                        intent,
                        mxc=str(getattr(conteudo, "url", "") or ""),
                        nome=str(getattr(conteudo, "body", "") or ""),
                        mime=str(getattr(info, "mimetype", "") or ""),
                        tamanho_declarado=int(getattr(info, "size", 0) or 0),
                        cadeira=cadeira,
                    ),
                    timeout=ANEXO_TIMEOUT,
                )
            except (anexos.Recusado, asyncio.TimeoutError) as recusa:
                motivo = (
                    "o download do anexo passou do tempo."
                    if isinstance(recusa, asyncio.TimeoutError)
                    else str(recusa)
                )
                # Recusa e EXPLICITA, e entra no dedupe: sem isso a reentrega do
                # homeserver repete a recusa na sala (criterio 19).
                if journal.registra_recusa(
                    self.con, event_id=evento.event_id, txn_id=txn, sala=sala
                ):
                    await self.diz(intent, sala, f"**Anexo recusado** — {motivo}")
                return
            corpo = anexos.linha_de_corpo(caminho, tamanho, mime)
        elif tipo in TEXTOS:
            corpo = str(getattr(conteudo, "body", "") or "").strip()
            caminho = ""
            if not corpo:
                return
        else:
            if journal.registra_recusa(
                self.con, event_id=evento.event_id, txn_id=txn, sala=sala
            ):
                await self.diz(
                    intent, sala,
                    f"**Anexo recusado** — nao recebo mensagem do tipo `{tipo}`. "
                    "Em v0 chegam texto, imagem e arquivo.",
                )
            return

        job = journal.registra_chegada(
            self.con,
            event_id=evento.event_id,
            txn_id=txn,
            sala=sala,
            cadeira=cadeira,
            remetente=evento.sender,
            corpo=corpo,
        )
        if job is None:
            # Corrida com a reentrega: o outro lado ganhou. Se este ramo baixou
            # um anexo, o arquivo sobra no inbox — apaga, para nao deixar copia
            # que ninguem citou.
            if tipo in MIDIAS and caminho:
                try:
                    os.unlink(caminho)
                except OSError:
                    pass
            return

        log.info("giro %s enfileirado: sala=%s cadeira=%s", job, sala, cadeira)
        await self.typing(intent, sala, True)

    # --- fala na sala -----------------------------------------------------

    async def typing(self, intent, sala: str, ligado: bool) -> None:
        try:
            await intent.set_typing(sala, timeout=TYPING_MS if ligado else 0)
        except Exception:
            log.warning("nao consegui mexer no typing da sala %s", sala, exc_info=True)

    async def diz(self, intent, sala: str, md: str) -> None:
        """Fala do sistema — erro, recusa, aviso. m.notice, nao m.text: e a
        recepcao falando, nao a cadeira respondendo."""
        conteudo = formata.conteudo(md, msgtype="m.notice")
        try:
            await intent.send_notice(sala, text=conteudo["body"], html=conteudo["formatted_body"])
        except Exception:
            log.error("nao consegui falar na sala %s", sala, exc_info=True)

    # --- expedicao --------------------------------------------------------

    def mensagem_de(self, job) -> tuple[str, str]:
        """(markdown, msgtype) do que vai a sala para cada estado terminal."""
        estado, detalhe = job["estado"], (job["detalhe"] or "").strip()
        if estado == journal.OK:
            texto = (job["texto"] or "").strip()
            if texto:
                return texto, "m.text"
            return ("**A cadeira terminou o giro sem escrever resposta.** "
                    "Nao ha o que mostrar aqui — o produto do giro, se houve, "
                    "foi para a mesa ou para o caderno."), "m.notice"
        if estado == journal.COTA:
            volta = f" Volta em {detalhe}." if detalhe else ""
            return f"**Cota da assinatura estourada.**{volta}", "m.notice"
        if estado == journal.TIMEOUT:
            return ("**O giro travou e foi encerrado.** "
                    + (detalhe or "Ficou sem sinal de vida por tempo demais.")), "m.notice"
        return f"**O giro falhou.** {detalhe or 'Sem detalhe do verbo.'}", "m.notice"

    async def expede(self, job) -> None:
        cadeira, sala = job["cadeira"], job["sala"]
        intent = self.intent_da(cadeira)
        md, msgtype = self.mensagem_de(job)
        partes = formata.eventos(md, msgtype=msgtype)
        try:
            # Retoma de onde parou: receptor derrubado no meio de uma resposta
            # de N partes volta na parte seguinte, nunca na primeira. E a metade
            # "sem resposta duplicada" do criterio 14.
            for i in range(int(job["partes_enviadas"] or 0), len(partes)):
                conteudo = partes[i]
                # Envio serializado: espera o event_id de cada parte antes da
                # proxima. Ordem garantida por nos, sem depender do transporte
                # nem do rate limit (criterio 15; o registration ja vai com
                # rate_limited: false, sem o qual isto flakeia).
                await intent.send_text(
                    sala,
                    text=conteudo["body"],
                    html=conteudo["formatted_body"],
                    msgtype=MessageType.NOTICE if msgtype == "m.notice" else MessageType.TEXT,
                )
                journal.marca_parte_enviada(self.con, job["id"], i + 1)
            journal.marca_enviado(self.con, job["id"])
        finally:
            # O typing cessa em TODO caminho de saida, inclusive no de erro —
            # e o que o criterio 2 cobra, e a razao de estar num finally.
            await self.typing(intent, sala, False)

    # --- lacos ------------------------------------------------------------

    async def laco_expedidor(self) -> None:
        while True:
            try:
                for job in journal.a_expedir(self.con):
                    await self.expede(job)
            except Exception:
                log.error("falha no expedidor", exc_info=True)
            await asyncio.sleep(INTERVALO_EXPEDIDOR)

    async def laco_typing(self) -> None:
        while True:
            try:
                for sala in {j["sala"]: j for j in journal.giros_vivos(self.con)}:
                    cadeira = journal.cadeira_da_sala(self.con, sala)
                    if cadeira:
                        await self.typing(self.intent_da(cadeira), sala, True)
            except Exception:
                log.error("falha no laco de typing", exc_info=True)
            await asyncio.sleep(INTERVALO_TYPING)

    def varre(self, motivo: str) -> int:
        """Converte giro pendurado em erro. Roda na subida e em laco.

        Fresco NAO e condenado, e isto e decisao de claudinho-TI (comentario 310
        do card): derrubada qualquer uma das duas pecas no meio do giro, o dono
        recebe OU a resposta OU um erro, em ate 5 min — nunca as duas. Se o
        worker esta vivo e batendo, o giro sobreviveu e a resposta chega quando
        o receptor volta; converter isso em erro transformaria sucesso em falha
        e ainda renderia mensagem dupla quando a resposta chegasse atras. O que
        a varredura condena e giro SEM BATIDA, que e worker morto de fato.
        """
        quantos = 0
        for job in journal.giros_pendurados(self.con, PENDURADO_S):
            if journal.condena(
                self.con, job["id"], estado=journal.TIMEOUT,
                detalhe=f"Sem sinal de vida do worker por mais de {int(PENDURADO_S)}s.",
            ):
                quantos += 1
                log.warning("giro %s condenado na %s (sala %s)", job["id"], motivo, job["sala"])
        return quantos

    async def laco_vigia(self) -> None:
        while True:
            try:
                self.varre("vigia")
            except Exception:
                log.error("falha no vigia", exc_info=True)
            await asyncio.sleep(INTERVALO_VIGIA)


async def principal() -> None:
    porta = int(os.environ.get("AS_PORTA", "8080"))
    dominio = exigido("AS_DOMINIO")
    prefixo = os.environ.get("AS_BOT", "_pf")

    appserv = AppService(
        server=exigido("AS_SERVIDOR"),
        domain=dominio,
        as_token=exigido("AS_TOKEN"),
        hs_token=exigido("HS_TOKEN"),
        bot_localpart=prefixo,
        id=os.environ.get("AS_ID", "pf"),
        log=log,
    )

    con = journal.abre()
    recepcao = Recepcao(appserv, con, dominio, prefixo)

    # O txn_id nao chega ao handler de evento pela API da lib, e ele e o que
    # amarra o dedupe a transacao do homeserver na trilha. Embrulhar o
    # `handle_transaction` da instancia e mais barato que reimplementar a rota.
    original = appserv.handle_transaction

    async def com_txn(txn_id, **resto):
        _txn_atual.set(txn_id)
        return await original(txn_id, **resto)

    appserv.handle_transaction = com_txn

    @appserv.matrix_event_handler
    async def entrega(evento) -> None:
        try:
            await recepcao.recebe(evento)
        except Exception:
            # Excecao aqui derrubaria o 200 e o homeserver reentregaria para
            # sempre. Registrada e engolida: o dedupe ja e persistente.
            log.error("falha ao receber evento", exc_info=True)

    async def estado(_pedido: web.Request) -> web.Response:
        vivos = journal.giros_vivos(con)
        return web.json_response({
            "estado": "de pe",
            "as_id": os.environ.get("AS_ID", "pf"),
            "giros_vivos": len(vivos),
            "a_expedir": len(journal.a_expedir(con)),
            "salas_sem_cadeira": recepcao.sem_cadeira,
        })

    appserv.app.router.add_get("/estado", estado)

    # Le as personas UMA vez na subida, de proposito: sem o bind mount de
    # personas/ o modulo de cadeiras levanta FileNotFoundError, e e melhor que
    # isso derrube a subida — visivel no healthcheck — do que apareca so no
    # primeiro giro, engolido pelo handler de evento como sala sem cadeira.
    log.info("cadeiras visiveis: %s", ", ".join(cadeiras()))

    condenados = recepcao.varre("varredura de subida")
    log.info("varredura de subida: %s giro(s) orfao(s) convertido(s) em erro", condenados)

    await appserv.start("0.0.0.0", porta)
    appserv.ready = True
    log.info("recepcao de pe na porta %s", porta)

    await asyncio.gather(
        recepcao.laco_expedidor(),
        recepcao.laco_typing(),
        recepcao.laco_vigia(),
    )


if __name__ == "__main__":
    asyncio.run(principal())
