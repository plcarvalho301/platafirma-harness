#!/usr/bin/env python3
"""Worker do chat — o lado VERBO do giro (card 458, fatia B-1).

Roda no HOST, sob systemd --user, porque verbo assume o host inteiro: `claude`
em ~/.local/bin, `monta-sessao`, ~/AI/fitas, o PATH do harness. Precedente pago
e medido no mesmo repo: controle/compose.yaml:1-13 conta que por em container o
lado que chama verbo deixou 5 dos 8 blocos indisponiveis.

Ele NUNCA fala Matrix. Le job pendente do journal, chama o verbo, bate heartbeat
e devolve o resultado ao journal. Quem poe qualquer coisa na sala e o receptor.

Contrato do verbo (fixado por claudinho-TI, identico no card 459):
    chamada : chat despachar --cadeira <slug> --fita <id-ou-vazio> [--silencioso]
              corpo da mensagem em stdin
    stdout  : UMA linha JSON
              {"estado":"ok|erro|cota|timeout","texto":"...","id_fita":"...",
               "detalhe":"...","reiniciada":true|false}
    stderr  : uma linha JSON por passo do stream — e o que o watchdog observa
    exit    : 0 sempre que houver JSON valido em stdout

Enquanto o card 459 nao mergeia, `CHAT_VERBO` aponta para o duble ao lado.

FILA POR SALA, PARALELISMO ENTRE SALAS: uma thread por sala com giro pendente,
que consome a fila daquela sala em ordem e morre quando ela esvazia. A ordem
dentro da sala e do `reivindica` (um em curso por sala, por transacao); o
paralelismo vem de haver varias salas, nao de haver varias threads por sala.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comum import journal  # noqa: E402

# Watchdog de SEGUNDA ordem sobre o silencio do stream. O de primeira ordem e do
# proprio verbo: bin/chat tem `SILENCIO_S = 240` e, ao estourar, mata o grupo do
# motor e AINDA IMPRIME o contrato — inclusive o `id_fita`, que na primeira
# mensagem de uma sala e o unico registro da fita recem-aberta.
#
# Por isso 300 e nao 240: iguais, o worker SIGTERMa o verbo antes de ele imprimir,
# e o id da fita nova se perde — a proxima mensagem abriria outra fita e o dono
# perderia o contexto sem nada dizer. A margem e a mesma disciplina que o receptor
# ja aplica sobre o worker (270 contra 240): anel de fora sempre depois do de
# dentro. Medido em 15/08: PF_CHAT_SILENCIO=240 em bin/chat:41.
STREAM_MUDO_S = float(os.environ.get("CHAT_STREAM_MUDO_S", "300"))
# Vigia de ultima instancia, so para o caso de o verbo ignorar o SIGTERM e
# continuar produzindo stream para sempre. Desligado por padrao.
TETO_ABSOLUTO_S = float(os.environ.get("CHAT_TETO_ABSOLUTO_S", "0"))
INTERVALO_RONDA = float(os.environ.get("CHAT_INTERVALO_RONDA", "2"))
VERBO = os.environ.get("CHAT_VERBO", "chat")
GRACA_KILL_S = 10.0

log_trava = threading.Lock()


def log(msg: str) -> None:
    with log_trava:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


class Giro:
    """Uma execucao do verbo, com o watchdog em volta dela."""

    def __init__(self, con, job) -> None:
        self.con = con
        self.job = job
        self.ultimo_sinal = time.monotonic()
        self.saida: list[str] = []
        self.passos = 0
        self.trava = threading.Lock()

    def _le_stdout(self, fluxo) -> None:
        for linha in fluxo:
            self.saida.append(linha)
        fluxo.close()

    def _le_stderr(self, fluxo) -> None:
        """Cada linha do stream e um sinal de vida. E so isso que ela e aqui: o
        conteudo do passo e do verbo, e nao sobe a sala nem ao journal."""
        for _ in fluxo:
            with self.trava:
                self.ultimo_sinal = time.monotonic()
                self.passos += 1
        fluxo.close()

    def executa(self) -> dict:
        cmd = [
            VERBO, "despachar",
            "--cadeira", self.job["cadeira"],
            "--fita", self.job["id_fita"] or "",
        ]
        try:
            # start_new_session: o verbo vira lider do proprio grupo de
            # processos. Sem isso, matar o pendurado deixa `claude` vivo — foi
            # a mesma armadilha que o ops-mcp ja pagou com os.killpg.
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except FileNotFoundError:
            return {"estado": journal.ERRO,
                    "detalhe": f"o verbo `{VERBO}` nao esta no PATH do worker."}
        except OSError as erro:
            return {"estado": journal.ERRO,
                    "detalhe": f"nao consegui invocar o verbo ({type(erro).__name__})."}

        threading.Thread(target=self._le_stdout, args=(proc.stdout,), daemon=True).start()
        threading.Thread(target=self._le_stderr, args=(proc.stderr,), daemon=True).start()

        try:
            proc.stdin.write(self.job["corpo"])
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

        motivo = self._vigia(proc)
        proc.wait()
        time.sleep(0.2)  # deixa as threads de leitura drenarem o que sobrou

        if motivo:
            return {"estado": journal.TIMEOUT, "detalhe": motivo}
        return self._resultado(proc.returncode)

    def _vigia(self, proc) -> str:
        """Fica de olho enquanto o verbo trabalha. Devolve o motivo da morte,
        ou string vazia se ele terminou sozinho."""
        comeco = time.monotonic()
        while proc.poll() is None:
            time.sleep(1.0)
            with self.trava:
                mudo = time.monotonic() - self.ultimo_sinal
            if mudo > STREAM_MUDO_S:
                self._mata(proc)
                return (f"Sem evento no stream do verbo por {int(mudo)}s "
                        f"(teto de {int(STREAM_MUDO_S)}s).")
            if TETO_ABSOLUTO_S and time.monotonic() - comeco > TETO_ABSOLUTO_S:
                self._mata(proc)
                return f"O giro passou do teto absoluto de {int(TETO_ABSOLUTO_S)}s."
            # Batida no journal: e o que o vigia do receptor observa. Se ela
            # falhar, este giro ja foi condenado la — parar de trabalhar nele e
            # o certo, porque o dono ja leu o erro na sala.
            if not journal.bate(self.con, self.job["id"]):
                self._mata(proc)
                return "condenado"
        return ""

    def _mata(self, proc) -> None:
        """Mata o GRUPO, nao o processo: `claude` roda filhos, e SIGTERM so no
        lider deixa neto vivo segurando o pipe."""
        try:
            grupo = os.getpgid(proc.pid)
        except ProcessLookupError:
            return
        for sinal, espera in ((signal.SIGTERM, GRACA_KILL_S), (signal.SIGKILL, 2.0)):
            try:
                os.killpg(grupo, sinal)
            except ProcessLookupError:
                return
            fim = time.monotonic() + espera
            while time.monotonic() < fim:
                if proc.poll() is not None:
                    return
                time.sleep(0.2)

    def _resultado(self, codigo: int | None) -> dict:
        """Ultima linha de stdout que seja JSON com `estado` — o contrato manda
        UMA linha, e ler a ultima valida tolera ruido antes dela sem inventar
        significado nenhum."""
        for linha in reversed(self.saida):
            linha = linha.strip()
            if not linha.startswith("{"):
                continue
            try:
                dado = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if isinstance(dado, dict) and "estado" in dado:
                estado = str(dado.get("estado") or "").lower()
                if estado not in journal.TERMINAIS:
                    return {"estado": journal.ERRO,
                            "detalhe": f"o verbo devolveu estado desconhecido `{estado}`."}
                return {
                    "estado": estado,
                    "texto": str(dado.get("texto") or ""),
                    "detalhe": str(dado.get("detalhe") or ""),
                    "id_fita": str(dado.get("id_fita") or ""),
                    "reiniciada": bool(dado.get("reiniciada")),
                }
        return {"estado": journal.ERRO,
                "detalhe": f"o verbo saiu com codigo {codigo} e sem JSON valido em stdout."}


def atende_sala(sala: str, vivas: set, trava: threading.Lock) -> None:
    con = journal.abre()
    try:
        while True:
            job = journal.reivindica(con, sala)
            if job is None:
                return
            log(f"giro {job['id']} tomado: sala={sala} cadeira={job['cadeira']}")
            comeco = time.monotonic()
            giro = Giro(con, job)
            try:
                fim = giro.executa()
            except Exception as erro:  # nunca deixa o job preso em curso
                fim = {"estado": journal.ERRO,
                       "detalhe": f"o worker falhou no giro ({type(erro).__name__})."}
                log(f"giro {job['id']} estourou no worker: {erro!r}")
            if fim.get("detalhe") == "condenado":
                log(f"giro {job['id']} ja condenado pelo receptor — resultado descartado")
                continue
            venceu = journal.conclui(
                con, job["id"],
                estado=fim["estado"],
                texto=fim.get("texto", ""),
                detalhe=fim.get("detalhe", ""),
                id_fita=fim.get("id_fita", ""),
                reiniciada=fim.get("reiniciada", False),
            )
            log(f"giro {job['id']} fechou como {fim['estado']} em "
                f"{time.monotonic() - comeco:.1f}s ({giro.passos} passos)"
                + ("" if venceu else " — descartado, o vigia chegou antes"))
    finally:
        con.close()
        with trava:
            vivas.discard(sala)


def ronda(uma_volta: bool = False) -> None:
    con = journal.abre()
    vivas: set[str] = set()
    trava = threading.Lock()
    log(f"worker de pe — verbo `{VERBO}`, stream mudo em {int(STREAM_MUDO_S)}s")
    while True:
        try:
            for sala in journal.salas_pendentes(con):
                with trava:
                    if sala in vivas:
                        continue
                    vivas.add(sala)
                threading.Thread(
                    target=atende_sala, args=(sala, vivas, trava), daemon=True
                ).start()
        except Exception as erro:
            log(f"falha na ronda: {erro!r}")
        if uma_volta:
            while True:
                with trava:
                    if not vivas:
                        return
                time.sleep(0.2)
        time.sleep(INTERVALO_RONDA)


if __name__ == "__main__":
    ronda(uma_volta="--uma-volta" in sys.argv)
