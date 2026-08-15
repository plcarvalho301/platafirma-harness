#!/usr/bin/env python3
"""Recepcao da PlataFirma — o Application Service do Matrix, corpo minimo do card 447.

O que ESTE arquivo faz: sobe, aceita a transacao que o homeserver empurra, responde a
sonda de saude e loga. Nada mais. Ela existe para a recepcao estar registrada e de pe, que e
o aceite do card.

O que ele NAO faz, e onde isso entra: sala por cadeira, alias, avatar, typing, anexo e
o despacho para o motor sao o card 448 — e entram como handler aqui dentro, sem mexer
no registration (o par as_token/hs_token ja cobre o namespace inteiro). Rotacao,
/zerar e leave+forget sao o card 449, e falam com a Admin API pela rede interna.

Ack-then-work (posicao de claudinho-TI na minuta 0002): a transacao e confirmada assim
que aceita, e o giro roda fora do caminho dela. Em v0/A nao ha giro — mas a forma ja e
esta, para o 448 nao ter de reescrever o receptor.
"""

import asyncio
import logging
import os

from aiohttp import web
from mautrix.appservice import AppService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("chat-recepcao")


def exigido(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise SystemExit(f"falta a variavel {nome} — ela desce do cofre pelo .env da stack")
    return valor


async def principal() -> None:
    porta = int(os.environ.get("AS_PORTA", "8080"))
    appserv = AppService(
        server=exigido("AS_SERVIDOR"),
        domain=exigido("AS_DOMINIO"),
        as_token=exigido("AS_TOKEN"),
        hs_token=exigido("HS_TOKEN"),
        bot_localpart=os.environ.get("AS_BOT", "_pf"),
        id=os.environ.get("AS_ID", "pf"),
        log=log,
    )

    @appserv.matrix_event_handler
    async def registra(evento) -> None:
        # v0/A nao responde a nada: so prova que a transacao chegou e foi aceita.
        log.info("evento recebido: type=%s sala=%s", getattr(evento, "type", "?"), getattr(evento, "room_id", "?"))

    async def estado(_pedido: web.Request) -> web.Response:
        # Sonda do compose. Deliberadamente burra: se o processo responde, o receptor
        # esta de pe. Saude do homeserver e sonda dele, nao daqui.
        return web.json_response({"estado": "de pe", "as_id": os.environ.get("AS_ID", "pf")})

    appserv.app.router.add_get("/estado", estado)

    await appserv.start("0.0.0.0", porta)
    appserv.ready = True
    log.info("application service de pe na porta %s", porta)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(principal())
