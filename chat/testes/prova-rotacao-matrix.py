#!/usr/bin/env python3
"""Prova do lado MATRIX da rotacao — criterios 11 e 12, contra o Synapse real.

Roda DENTRO do container da recepcao, que e quem alcanca o homeserver (rede
`interna`, sem porta publicada) e quem tem os tokens no ambiente:

    docker exec chat-recepcao python /testes/prova-rotacao-matrix.py

O que a prova do ciclo (`prova-ciclo-de-fita.py`) NAO cobre e exatamente isto: la
a recepcao e duble e o journal e descartavel, entao `createRoom`, `kick`, `leave`
e `forget` nunca sao exercitados. Aqui eles sao, e contra o homeserver de
verdade.

Atores de mentira no namespace do AS (`_pf_prova-*`), NUNCA uma cadeira: o
`m.direct` da cadeira e como o provisionamento acha a sala dela, e sujar isso com
sala de teste e defeito que sobrevive a prova. Sai 0 se tudo passou.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, "/opt/chat")

from mautrix.appservice import AppService  # noqa: E402

import recepcao as mod  # noqa: E402

DOMINIO = os.environ["AS_DOMINIO"]
ATOR = f"@_pf_prova-rotacao:{DOMINIO}"
DONO = f"@_pf_prova-dono:{DOMINIO}"
# Fica na sala depois de todo mundo sair: sem ela nao ha de quem ler o estado
# final — quem foi expulso e quem saiu perdem o direito de consultar a sala, e a
# consulta falha por IntentError em vez de mostrar o membership.
TESTEMUNHA = f"@_pf_prova-testemunha:{DOMINIO}"

falhas = []


def checa(nome: str, condicao: bool, detalhe: str = "") -> None:
    if condicao:
        print(f"  ok   {nome}")
    else:
        falhas.append(nome)
        print(f"  FALHA {nome}: {detalhe}")


async def membro(intent, sala: str, quem: str) -> str:
    try:
        estado = await intent.get_state_event(sala, "m.room.member", quem)
    except Exception as erro:
        return f"(sem estado: {type(erro).__name__})"
    return str(getattr(estado, "membership", "") or "")


async def principal() -> None:
    appserv = AppService(
        server=os.environ["AS_SERVIDOR"],
        domain=DOMINIO,
        as_token=os.environ["AS_TOKEN"],
        hs_token=os.environ["HS_TOKEN"],
        bot_localpart=os.environ.get("AS_BOT", "_pf"),
        id=os.environ.get("AS_ID", "pf"),
    )
    await appserv.start("127.0.0.1", 0)
    try:
        ator = appserv.intent.api.intent(ATOR)
        dono = appserv.intent.api.intent(DONO)
        testemunha = appserv.intent.api.intent(TESTEMUNHA)
        await ator.ensure_registered()
        await dono.ensure_registered()
        await testemunha.ensure_registered()

        # A recepcao entra so pelos dois metodos sob prova; o journal nao e
        # tocado aqui, e por isso `con=None` nao machuca.
        r = mod.Recepcao(appserv, None, DOMINIO, os.environ.get("AS_BOT", "_pf"))

        sala = await r.cria_sala_direta(ator, DONO)
        checa("createRoom da sala nova responde com id", bool(sala), f"veio {sala!r}")
        if not sala:
            return

        checa("o dono nasce convidado", await membro(ator, sala, DONO) == "invite",
              await membro(ator, sala, DONO))
        direto = await ator.get_account_data("m.direct")
        checa("m.direct do lado de quem cria aponta para a sala nova",
              sala in (direto.get(DONO) or []), f"m.direct: {direto!r}")

        await ator.invite_user(sala, TESTEMUNHA)
        await testemunha.join_room_by_id(sala)
        await dono.join_room_by_id(sala)
        checa("o dono entra", await membro(ator, sala, DONO) == "join",
              await membro(ator, sala, DONO))

        # A razao de o preset ser `private_chat`: com `trusted_private_chat` o
        # convidado nasce com poder 100 e nao ha como expulsa-lo depois.
        # `serialize()` e nao atributo: evento de estado sem tipo registrado volta
        # como `Obj` generico da mautrix, e `Obj.users` nao e um dict.
        poderes = await ator.get_state_event(sala, "m.room.power_levels")
        bruto = poderes.serialize() if hasattr(poderes, "serialize") else dict(poderes)
        usuarios = dict(bruto.get("users") or {})
        checa("o dono nao nasce com poder igual ao da cadeira",
              usuarios.get(DONO, 0) < usuarios.get(ATOR, 0),
              f"poderes: {usuarios!r}")

        await r.descarta_sala(ator, sala, DONO)
        checa("criterio 12 — o dono e expulso da sala descartada",
              await membro(testemunha, sala, DONO) == "leave",
              await membro(testemunha, sala, DONO))
        checa("criterio 12 — quem descartou tambem saiu",
              await membro(testemunha, sala, ATOR) == "leave",
              await membro(testemunha, sala, ATOR))
        checa("quem foi expulso nao consegue mais ler a sala",
              "IntentError" in await membro(dono, sala, DONO),
              await membro(dono, sala, DONO))

        salas = await ator.get_joined_rooms()
        checa("a sala descartada saiu da lista de quem descartou",
              sala not in salas, f"{len(salas)} sala(s) ainda listadas")

        # Idempotencia: rotacao que roda duas vezes (reentrega do homeserver) nao
        # pode estourar. Cada gesto ja e independente por dentro.
        await r.descarta_sala(ator, sala, DONO)
        checa("descartar de novo nao levanta", True)
    finally:
        await appserv.stop()


if __name__ == "__main__":
    print("prova do lado Matrix da rotacao — createRoom, kick, leave, forget")
    asyncio.run(principal())
    if falhas:
        print(f"\n{len(falhas)} falha(s): {', '.join(falhas)}")
        sys.exit(1)
    print("\ntudo passou")
