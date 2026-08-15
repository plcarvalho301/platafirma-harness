"""Rotacao de sala — a fita morre por mecanismo, e o dono ve que morreu.

Card 449, criterios 8 a 12 da minuta 0002. Tres coisas, e uma so mecanica:

  - **Preguicosa, nao agendada.** Nao ha timer. A idade e da SALA, e o gatilho e
    a mensagem: sala parada nao roda. Retomada a conversa depois de 24h, a
    anterior nao esta na tela (criterio 10).
  - **Sob demanda.** `/zerar` do celular faz o mesmo, sem shell e sem admin
    console (criterio 11). Nao ha comando para ABRIR fita: morta a anterior, a
    proxima mensagem ja abre uma.
  - **Sem corpo presente.** Sala descartada leva kick do dono, leave e forget da
    cadeira (criterio 12). O que sobra e purgado pelo proprio Synapse, pela
    retencao de sala esquecida.

A cadeira e reencontravel porque a sala nova nasce `is_direct` do MESMO MXID: em
conversa direta o cliente encontra pela pessoa, nao por alias de sala — as salas
nascem sem alias (`provisiona-cadeiras.sh`), e por isso nao ha alias a mover.

O que NAO se faz aqui: chamar verbo. A recepcao nao cruza a fronteira; o ritual
de encerramento vai ao journal como giro silencioso e quem o executa e o worker.
"""

from __future__ import annotations

import logging
import os
import time

from comum import journal, rituais

log = logging.getLogger("chat-recepcao.rotacao")

# 24 h, e a idade e da sala (minuta 0002, secao 2). Configuravel para a prova
# poder encolher a janela sem esperar um dia.
IDADE_S = float(os.environ.get("CHAT_ROTACAO_S", str(24 * 3600)))
# Teto de espera do ritual antes de a degradacao ser declarada na sala nova.
TETO_RITUAL_S = float(os.environ.get("CHAT_TETO_RITUAL_S", "20"))

# `/zerar` e o do criterio 11; os outros dois sao a mesma coisa dita como o dono
# fala. Comando so vale como mensagem INTEIRA — texto que comeca com a palavra
# nao e comando, e apagar conversa por engano nao tem desfazer.
COMANDOS = {"/zerar", "/limpar", "/nova"}

MORTE = (
    "**Fita encerrada — sala nova.** A conversa anterior saiu da tela e a memoria "
    "de trabalho foi guardada na mesa. Falo daqui em diante."
)
MESA_ATRASADA = (
    "**A mesa da fita anterior nao fechou a tempo.** Esta fita abriu com a memoria "
    "como estava; o que a anterior ainda ia anotar pode faltar."
)


def eh_comando(corpo: str) -> bool:
    return corpo.strip().lower() in COMANDOS


def vencida(con, sala: str, agora: float | None = None) -> bool:
    """A sala passou da idade? Sala desconhecida nao vence — quem nao esta no
    cache ainda nem aprendeu a cadeira, e rodar ali perderia o endereco."""
    nascida = journal.nascimento_da_sala(con, sala)
    if nascida is None:
        return False
    if not nascida:
        # Sala anterior a migracao: adota a idade AGORA em vez de rodar de cara.
        # Tratar carimbo ausente como nascimento em 1970 rodaria todas as salas
        # existentes na primeira mensagem depois do deploy.
        journal.adota_nascimento(con, sala, time.time())
        return False
    return (agora or time.time()) - nascida >= IDADE_S


async def gira(recepcao, sala: str, cadeira: str, dono: str, motivo: str,
               eco: str = "") -> str | None:
    """Roda a sala da cadeira. Devolve o id da sala nova, ou None se falhou.

    Ordem, e ela importa: a sala nova nasce ANTES de qualquer descarte. Falhando
    o `createRoom`, nada foi destruido e a conversa segue onde estava — o dono
    perde a rotacao, nao o endereco da cadeira.
    """
    con = recepcao.con
    intent = recepcao.intent_da(cadeira)
    id_fita = journal.fita_da_sala(con, sala)

    nova = await recepcao.cria_sala_direta(intent, dono)
    if not nova:
        log.error("rotacao de %s abortada: nao consegui criar a sala nova", sala)
        return None

    job = None
    if id_fita:
        # O ritual roda na fita que morre, com o id EXPLICITO: quando o worker o
        # tomar, a tabela ja aponta para a fita nova.
        job = journal.enfileira_silencioso(
            con, sala=sala, cadeira=cadeira, id_fita=id_fita,
            corpo=rituais.ENCERRAMENTO, marca=journal.RITUAL,
        )

    journal.registra_rotacao(
        con, velha=sala, nova=nova, cadeira=cadeira, id_fita=id_fita,
        job_ritual=job, motivo=motivo,
    )
    journal.troca_de_sala(con, sala, nova, cadeira)
    # O eco e o que impede o dono de ver a resposta sem a pergunta: a mensagem
    # que disparou a rotacao foi escrita na sala que acabou de sumir da tela.
    # Vai no MESMO aviso, e nao em dois, para a sala nova nao abrir com duas
    # falas de sistema antes da cadeira dizer qualquer coisa.
    texto = MORTE + (f"\n\n> {eco.strip()}" if eco.strip() else "")
    journal.avisa(con, nova, texto)
    log.info("sala %s rodada para %s (cadeira %s, motivo %s)", sala, nova, cadeira, motivo)

    await recepcao.descarta_sala(intent, sala, dono)
    return nova


async def declara_atraso(recepcao) -> int:
    """Emite, uma vez por rotacao, o aviso de mesa que nao fechou a tempo."""
    quantos = 0
    for linha in journal.rituais_atrasados(recepcao.con, TETO_RITUAL_S):
        journal.avisa(recepcao.con, linha["sala_nova"], MESA_ATRASADA)
        journal.marca_rotacao_avisada(recepcao.con, linha["sala_velha"])
        quantos += 1
    return quantos
