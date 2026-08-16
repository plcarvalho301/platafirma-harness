#!/usr/bin/env python3
"""Journal do chat — a UNICA fronteira entre o receptor e o worker (card 458).

A recepcao e duas pecas partidas POR DIRECAO (topologia de claudinho-TI,
comentario 302 do card): o receptor faz todo o lado Matrix de dentro do
container, o worker faz todo o lado verbo de fora dele, no host. As duas nao se
chamam: escrevem e leem ESTE arquivo, num bind mount rw. Nenhuma porta nova,
nenhuma travessia container->host — que em docker rootless e caminho mudo.

Por que SQLite e nao um arquivo de estado como o do harness-controle: la o
agregador escreve e a tela le, um sentido so. Aqui os dois escrevem no mesmo
registro (o worker grava resposta e batida; o receptor grava chegada e envio),
e o dedupe do criterio 14 exige uma escrita atomica com leitura no meio.
Arquivo solto entregaria corrida; WAL entrega transacao.

Sem dependencia fora da stdlib DE PROPOSITO: este modulo roda dentro do
container (python 3.13 da imagem) e no host (python 3.12 do systemd). Instalar
pacote nos dois lados para o mesmo esquema seria fronteira com duas verdades.

ESTADOS de um giro, e quem move cada seta:

    pendente  --(worker reivindica)-->  em_curso  --(worker conclui)--> ok
        |                                   |                           erro
        |                                   |                           cota
        '------(receptor condena)-----------'-------------------------> timeout

Terminal nao quer dizer entregue: `enviado_em` e do receptor, e so ele escreve.
Toda transicao e compare-and-swap sobre o estado anterior — e o que impede o
worker atrasado de esmagar a condenacao do vigia, e vice-versa.
"""

from __future__ import annotations

import os
import sqlite3
import time

CAMINHO_PADRAO = "/home/claudinho/AI/var/run/chat/journal.db"

PENDENTE = "pendente"
EM_CURSO = "em_curso"
OK = "ok"
ERRO = "erro"
COTA = "cota"
TIMEOUT = "timeout"

VIVOS = (PENDENTE, EM_CURSO)
TERMINAIS = (OK, ERRO, COTA, TIMEOUT)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS recebidos (
    event_id    TEXT PRIMARY KEY,
    txn_id      TEXT,
    sala        TEXT NOT NULL,
    recebido_em REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT NOT NULL UNIQUE,
    sala            TEXT NOT NULL,
    cadeira         TEXT NOT NULL,
    remetente       TEXT NOT NULL,
    corpo           TEXT NOT NULL,
    id_fita         TEXT NOT NULL DEFAULT '',
    estado          TEXT NOT NULL,
    detalhe         TEXT NOT NULL DEFAULT '',
    texto           TEXT NOT NULL DEFAULT '',
    reiniciada      INTEGER NOT NULL DEFAULT 0,
    criado_em       REAL NOT NULL,
    iniciado_em     REAL,
    batida_em       REAL,
    concluido_em    REAL,
    partes_enviadas INTEGER NOT NULL DEFAULT 0,
    enviado_em      REAL
);

CREATE INDEX IF NOT EXISTS jobs_por_estado ON jobs (estado, id);
CREATE INDEX IF NOT EXISTS jobs_por_sala   ON jobs (sala, estado, id);

CREATE TABLE IF NOT EXISTS fitas (
    sala          TEXT PRIMARY KEY,
    id_fita       TEXT NOT NULL,
    atualizado_em REAL NOT NULL,
    giros         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS salas (
    sala          TEXT PRIMARY KEY,
    cadeira       TEXT NOT NULL,
    atualizado_em REAL NOT NULL,
    nascida_em    REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS avisos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sala       TEXT NOT NULL,
    texto      TEXT NOT NULL,
    criado_em  REAL NOT NULL,
    enviado_em REAL
);

CREATE INDEX IF NOT EXISTS avisos_por_enviar ON avisos (enviado_em, id);

CREATE TABLE IF NOT EXISTS preferencias (
    sala          TEXT NOT NULL,
    chave         TEXT NOT NULL,
    valor         TEXT NOT NULL,
    atualizado_em REAL NOT NULL,
    PRIMARY KEY (sala, chave)
);

CREATE TABLE IF NOT EXISTS rotacoes (
    sala_velha TEXT PRIMARY KEY,
    sala_nova  TEXT NOT NULL,
    cadeira    TEXT NOT NULL,
    id_fita    TEXT NOT NULL DEFAULT '',
    job_ritual INTEGER,
    motivo     TEXT NOT NULL DEFAULT '',
    em         REAL NOT NULL,
    avisado_em REAL
);
"""

# Colunas que chegaram depois do primeiro esquema. `CREATE TABLE IF NOT EXISTS`
# nao mexe em tabela existente: sem isto, banco ja criado sobe sem as colunas do
# card 449 e o erro aparece no primeiro giro, nao na subida.
MIGRACOES = (
    ("fitas", "giros", "INTEGER NOT NULL DEFAULT 0"),
    ("salas", "nascida_em", "REAL NOT NULL DEFAULT 0"),
    ("jobs", "silencioso", "INTEGER NOT NULL DEFAULT 0"),
    ("jobs", "progresso", "TEXT NOT NULL DEFAULT ''"),
    ("jobs", "progresso_evento", "TEXT NOT NULL DEFAULT ''"),
)


def _migra(con: sqlite3.Connection) -> None:
    for tabela, coluna, tipo in MIGRACOES:
        tem = any(
            linha["name"] == coluna
            for linha in con.execute(f"PRAGMA table_info({tabela})")
        )
        if not tem:
            con.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def abre(caminho: str | None = None) -> sqlite3.Connection:
    """Abre (e cria, se faltar) o journal em WAL.

    WAL nao e enfeite: com o journal de rollback padrao o leitor bloqueia o
    escritor, e aqui os dois processos batem no mesmo arquivo o tempo todo — o
    receptor varrendo a cada 2 s, o worker batendo heartbeat por evento do
    stream. `busy_timeout` cobre a janela em que o outro lado esta no meio de
    uma escrita: sem ele, o segundo processo leva SQLITE_BUSY na cara em vez de
    esperar alguns milissegundos.
    """
    caminho = caminho or os.environ.get("CHAT_JOURNAL", CAMINHO_PADRAO)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    # isolation_level=None: transacao explicita, na mao. O modo implicito do
    # sqlite3 abre transacao adiada e so a fecha no commit, o que transforma
    # "BEGIN IMMEDIATE" em erro de aninhamento.
    con = sqlite3.connect(caminho, timeout=30.0, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(ESQUEMA)
    _migra(con)
    return con


def _agora() -> float:
    return time.time()


# --- lado do receptor: chegada -------------------------------------------


def registra_chegada(
    con: sqlite3.Connection,
    *,
    event_id: str,
    txn_id: str,
    sala: str,
    cadeira: str,
    remetente: str,
    corpo: str,
) -> int | None:
    """Persiste o evento e enfileira o giro. Devolve o id do job, ou None se
    o evento ja tinha sido recebido antes.

    ISTO E O DEDUPE DO CRITERIO 14, e e por isso que as duas escritas estao na
    MESMA transacao: o homeserver reentrega transacao nao confirmada, e um
    dedupe gravado depois do enfileiramento deixaria a janela em que a reentrega
    vira segundo giro. Gravado antes, a reentrega colide na PK e nao produz nada.

    Roda no caminho da transacao HTTP, antes do 200 — mas SO porque o receptor liga
    `synchronous_handlers` na mao (recepcao.py). No default da mautrix 0.21.1 o
    handler vai para background task e o 200 sai antes desta escrita; como o
    homeserver nao reentrega o que ja confirmou, morrer nessa janela perderia a
    mensagem em silencio. E o ack-then-work do card: dentro do ack fica so isto
    (uma escrita), e o giro inteiro fica do lado de la da fronteira.
    """
    agora = _agora()
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute(
            "INSERT OR IGNORE INTO recebidos (event_id, txn_id, sala, recebido_em)"
            " VALUES (?, ?, ?, ?)",
            (event_id, txn_id, sala, agora),
        )
        if cur.rowcount == 0:
            con.execute("ROLLBACK")
            return None
        fita = con.execute("SELECT id_fita FROM fitas WHERE sala = ?", (sala,)).fetchone()
        cur = con.execute(
            "INSERT INTO jobs (event_id, sala, cadeira, remetente, corpo, id_fita,"
            " estado, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, sala, cadeira, remetente, corpo, fita["id_fita"] if fita else "",
             PENDENTE, agora),
        )
        job_id = cur.lastrowid
        con.execute("COMMIT")
        return job_id
    except Exception:
        con.execute("ROLLBACK")
        raise


def registra_recusa(con: sqlite3.Connection, *, event_id: str, txn_id: str, sala: str) -> bool:
    """Marca um evento como visto SEM abrir giro (anexo recusado, mensagem de
    quem nao e o dono). Devolve False se ja era conhecido.

    Sem isto, evento recusado nao entra no dedupe e a reentrega do homeserver
    faz a recusa aparecer na sala mais de uma vez.
    """
    cur = con.execute(
        "INSERT OR IGNORE INTO recebidos (event_id, txn_id, sala, recebido_em)"
        " VALUES (?, ?, ?, ?)",
        (event_id, txn_id, sala, _agora()),
    )
    return cur.rowcount > 0


def avisa(con: sqlite3.Connection, sala: str, texto: str) -> int:
    """Uma linha do SISTEMA para a sala, atravessando a fronteira pelo journal.

    O worker nao fala Matrix e a recepcao nao chama verbo — quem tem o que
    dizer (morte de fita, compactacao, mesa que nao fechou a tempo) escreve
    aqui, e o expedidor de avisos da recepcao poe na sala como `m.notice`.
    Fila persistente de proposito: receptor derrubado no meio da rotacao volta e
    entrega o aviso, em vez de a fita morrer calada.
    """
    cur = con.execute(
        "INSERT INTO avisos (sala, texto, criado_em) VALUES (?, ?, ?)",
        (sala, texto, _agora()),
    )
    return cur.lastrowid


def avisos_pendentes(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(con.execute(
        "SELECT * FROM avisos WHERE enviado_em IS NULL ORDER BY id"
    ))


def marca_aviso_enviado(con: sqlite3.Connection, aviso_id: int) -> None:
    con.execute("UPDATE avisos SET enviado_em = ? WHERE id = ?", (_agora(), aviso_id))


def registra_rotacao(
    con: sqlite3.Connection,
    *,
    velha: str,
    nova: str,
    cadeira: str,
    id_fita: str,
    job_ritual: int | None,
    motivo: str,
) -> None:
    """Guarda o par sala velha -> sala nova de uma rotacao.

    Existe para uma pergunta so, que nenhuma outra tabela responde depois do
    `troca_de_sala`: em que sala avisar quando o ritual da fita morta demora
    demais. Sem o par gravado, a recepcao teria de adivinhar a sala nova pela
    cadeira, e cadeira com duas rotacoes no mesmo dia daria o palpite errado.
    """
    con.execute(
        "INSERT INTO rotacoes (sala_velha, sala_nova, cadeira, id_fita, job_ritual,"
        " motivo, em) VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(sala_velha) DO UPDATE SET sala_nova = excluded.sala_nova,"
        " id_fita = excluded.id_fita, job_ritual = excluded.job_ritual,"
        " motivo = excluded.motivo, em = excluded.em, avisado_em = NULL",
        (velha, nova, cadeira, id_fita, job_ritual, motivo, _agora()),
    )


def rituais_atrasados(con: sqlite3.Connection, teto_s: float) -> list[sqlite3.Row]:
    """Rotacoes cujo ritual passou do teto e ainda esta vivo, sem aviso dado.

    E o passo 4 da secao 2 da minuta: estourado o teto, a fita nova ja abriu com
    a mesa como estava, e a degradacao se DECLARA na sala. Silencio aqui seria
    memoria faltando sem ninguem saber.
    """
    corte = _agora() - teto_s
    return list(con.execute(
        "SELECT r.* FROM rotacoes r JOIN jobs j ON j.id = r.job_ritual"
        " WHERE r.avisado_em IS NULL AND r.em < ? AND j.estado IN (?, ?)"
        " ORDER BY r.em", (corte, PENDENTE, EM_CURSO),
    ))


def marca_rotacao_avisada(con: sqlite3.Connection, velha: str) -> None:
    con.execute(
        "UPDATE rotacoes SET avisado_em = ? WHERE sala_velha = ? AND avisado_em IS NULL",
        (_agora(), velha),
    )


RITUAL = "encerramento"
ANCORA = "ancora"


def enfileira_silencioso(
    con: sqlite3.Connection,
    *,
    sala: str,
    cadeira: str,
    id_fita: str,
    corpo: str,
    marca: str,
) -> int | None:
    """Giro cujo produto e escrita em mesa ou caderno, nunca texto para a sala.

    Duas chamadas: o ritual de encerramento da fita que morre (criterio 8) e a
    ancora de compactacao (criterio 17). Sao o mesmo mecanismo — um giro a mais
    na fita, com `--silencioso` no verbo — e por isso nao ha duas rotas.

    `id_fita` vem EXPLICITO e nao da tabela: o ritual roda na fita que ja morreu,
    e no momento em que o worker o toma a tabela ja aponta para a fita nova. Ler
    dali encerraria a fita errada.

    O event_id e sintetico e carrega a marca e o relogio: ele existe so para a
    UNIQUE do job, e colisao com event_id do Matrix e impossivel pelo prefixo.
    """
    agora = _agora()
    event_id = f"pf!{marca}:{sala}:{agora:.6f}"
    try:
        cur = con.execute(
            "INSERT INTO jobs (event_id, sala, cadeira, remetente, corpo, id_fita,"
            " estado, silencioso, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (event_id, sala, cadeira, "@pf:local", corpo, id_fita, PENDENTE, agora),
        )
    except sqlite3.IntegrityError:
        return None
    return cur.lastrowid


# --- lado do worker: execucao --------------------------------------------


def salas_pendentes(con: sqlite3.Connection) -> list[str]:
    return [r["sala"] for r in con.execute(
        "SELECT DISTINCT sala FROM jobs WHERE estado = ? ORDER BY sala", (PENDENTE,)
    )]


def reivindica(con: sqlite3.Connection, sala: str) -> sqlite3.Row | None:
    """Toma o giro mais antigo pendente da sala, se houver, e o poe em curso.

    Um por sala de cada vez: e a fila por sala do card (a cadeira responde na
    ordem em que foi falada). O paralelismo entre salas vem de haver uma linha
    destas por sala, nao de haver varias por sala.

    O UPDATE condicionado ao estado e o que torna a tomada atomica: dois
    reivindicadores na mesma sala, so um ve rowcount 1.
    """
    agora = _agora()
    con.execute("BEGIN IMMEDIATE")
    try:
        ocupada = con.execute(
            "SELECT 1 FROM jobs WHERE sala = ? AND estado = ? LIMIT 1", (sala, EM_CURSO)
        ).fetchone()
        if ocupada:
            con.execute("ROLLBACK")
            return None
        alvo = con.execute(
            "SELECT * FROM jobs WHERE sala = ? AND estado = ? ORDER BY id LIMIT 1",
            (sala, PENDENTE),
        ).fetchone()
        if alvo is None:
            con.execute("ROLLBACK")
            return None
        cur = con.execute(
            "UPDATE jobs SET estado = ?, iniciado_em = ?, batida_em = ?"
            " WHERE id = ? AND estado = ?",
            (EM_CURSO, agora, agora, alvo["id"], PENDENTE),
        )
        if cur.rowcount == 0:
            con.execute("ROLLBACK")
            return None
        # A fita corrente e lida na tomada, nao na chegada: entre uma coisa e
        # outra o giro anterior da MESMA sala pode ter aberto fita nova, e o
        # id gravado na chegada estaria velho.
        job = dict(alvo)
        job["estado"] = EM_CURSO
        if not job.get("silencioso"):
            fita = con.execute(
                "SELECT id_fita FROM fitas WHERE sala = ?", (sala,)
            ).fetchone()
            job["id_fita"] = fita["id_fita"] if fita else ""
        con.execute("COMMIT")
        return job
    except Exception:
        con.execute("ROLLBACK")
        raise


def bate(con: sqlite3.Connection, job_id: int, progresso: str = "") -> bool:
    """Heartbeat do giro. Devolve False se o job ja nao esta em curso — foi
    condenado pelo vigia, e o worker deve parar de trabalhar nele.

    `progresso` viaja junto com a batida DE PROPOSITO: e o mesmo dado (o giro
    esta vivo, e eis o que ele fez ate agora) e uma escrita so. Metadado do
    stream, nunca conteudo — quem monta a frase e o receptor.
    """
    cur = con.execute(
        "UPDATE jobs SET batida_em = ?, progresso = ? WHERE id = ? AND estado = ?",
        (_agora(), progresso, job_id, EM_CURSO),
    )
    return cur.rowcount > 0


def marca_progresso_evento(con: sqlite3.Connection, job_id: int, evento: str) -> None:
    """Guarda o event_id da nota efemera de progresso.

    Vai a banco, e nao a memoria do receptor, por uma razao so: receptor
    reiniciado no meio de um giro perde o mapa e deixa a nota pendurada na sala
    para sempre. Com a coluna, a varredura de subida a redige."""
    con.execute("UPDATE jobs SET progresso_evento = ? WHERE id = ?", (evento, job_id))


def notas_de_progresso_orfas(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Giros ja terminais cuja nota efemera continua na sala."""
    return list(con.execute(
        "SELECT id, sala, cadeira, progresso_evento FROM jobs"
        " WHERE progresso_evento != '' AND estado NOT IN (?, ?)", VIVOS
    ))


def conclui(
    con: sqlite3.Connection,
    job_id: int,
    *,
    estado: str,
    texto: str = "",
    detalhe: str = "",
    id_fita: str = "",
    reiniciada: bool = False,
) -> bool:
    """Fecha o giro com o que o verbo devolveu.

    Condicionado a `em_curso`: se o vigia ja condenou este giro por silencio, a
    condenacao ganha e o resultado atrasado e descartado. O contrario — worker
    atrasado esmagando um erro que o dono JA leu na sala — produziria resposta
    depois do erro, que e a duplicata que o criterio 14 proibe.
    """
    agora = _agora()
    con.execute("BEGIN IMMEDIATE")
    try:
        cur = con.execute(
            "UPDATE jobs SET estado = ?, texto = ?, detalhe = ?, reiniciada = ?,"
            " concluido_em = ?, batida_em = ? WHERE id = ? AND estado = ?",
            (estado, texto, detalhe, 1 if reiniciada else 0, agora, agora, job_id, EM_CURSO),
        )
        venceu = cur.rowcount > 0
        silencioso = con.execute(
            "SELECT silencioso FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()["silencioso"]
        # Ritual e ancora rodam DENTRO de uma fita que ja tem endereco. Deixar o
        # id deles reescrever a tabela faria o ritual da fita morta ressuscita-la
        # como corrente da sala — o esmagamento que o criterio 18 proibe, so que
        # do lado do journal em vez do lado da mesa.
        if venceu and id_fita and not silencioso:
            sala = con.execute("SELECT sala FROM jobs WHERE id = ?", (job_id,)).fetchone()["sala"]
            con.execute(
                "INSERT INTO fitas (sala, id_fita, atualizado_em) VALUES (?, ?, ?)"
                " ON CONFLICT(sala) DO UPDATE SET id_fita = excluded.id_fita,"
                " atualizado_em = excluded.atualizado_em",
                (sala, id_fita, agora),
            )
        con.execute("COMMIT")
        return venceu
    except Exception:
        con.execute("ROLLBACK")
        raise


# --- lado do receptor: vigia e expedicao ----------------------------------


def giros_vivos(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(con.execute(
        "SELECT * FROM jobs WHERE estado IN (?, ?) ORDER BY id", VIVOS
    ))


def giros_pendurados(con: sqlite3.Connection, limite_s: float) -> list[sqlite3.Row]:
    """Giros sem sinal de vida ha mais de `limite_s`.

    Duas formas de pendurar, e as duas contam:

    - em curso sem batida: o worker morreu no meio (ou o host caiu). E o
      watchdog de segunda ordem do card — o de primeira ordem e o do proprio
      worker, sobre o silencio do stream.
    - pendente sem ninguem: o worker nao esta no ar para reivindicar.

    O pendente so conta o relogio quando a sala NAO tem outro giro em curso com
    batida fresca. Sem essa ressalva, o segundo giro de uma conversa rapida
    seria condenado por estar esperando a vez — que e exatamente o
    comportamento correto da fila por sala, nao uma falha.
    """
    corte = _agora() - limite_s
    em_curso = list(con.execute(
        "SELECT * FROM jobs WHERE estado = ?"
        " AND COALESCE(batida_em, iniciado_em, criado_em) < ?",
        (EM_CURSO, corte),
    ))
    pendentes = list(con.execute(
        "SELECT * FROM jobs j WHERE j.estado = ? AND j.criado_em < ?"
        " AND NOT EXISTS (SELECT 1 FROM jobs o WHERE o.sala = j.sala AND o.estado = ?"
        "                 AND COALESCE(o.batida_em, o.iniciado_em, o.criado_em) >= ?)",
        (PENDENTE, corte, EM_CURSO, corte),
    ))
    return sorted(em_curso + pendentes, key=lambda r: r["id"])


def condena(con: sqlite3.Connection, job_id: int, *, estado: str, detalhe: str) -> bool:
    """Converte giro pendurado em erro. CAS sobre os estados vivos: se o worker
    concluiu no ultimo instante, ele ganha e a condenacao nao acontece."""
    agora = _agora()
    cur = con.execute(
        "UPDATE jobs SET estado = ?, detalhe = ?, concluido_em = ?"
        " WHERE id = ? AND estado IN (?, ?)",
        (estado, detalhe, agora, job_id, PENDENTE, EM_CURSO),
    )
    return cur.rowcount > 0


def a_expedir(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Giros terminais que ainda nao chegaram inteiros a sala.

    Silencioso fica de fora: o produto dele e escrita em mesa ou caderno, e o
    contrato do verbo ja devolve `texto` vazio. Sem este filtro o expedidor
    poria na sala o "terminou sem escrever resposta" a cada ritual — que e
    exatamente o ruido que o modo silencioso existe para nao produzir.
    """
    return list(con.execute(
        "SELECT * FROM jobs WHERE estado IN (?, ?, ?, ?) AND enviado_em IS NULL"
        " AND silencioso = 0 ORDER BY id", TERMINAIS,
    ))


def marca_parte_enviada(con: sqlite3.Connection, job_id: int, quantas: int) -> None:
    """Registra quantas partes ja tem event_id no homeserver.

    Gravado apos CADA parte, e nao no fim: receptor derrubado no meio de uma
    resposta de N partes volta e continua da parte seguinte. Sem este contador,
    religar reenviaria a resposta inteira — a duplicata que o criterio 14 nomeia.
    """
    con.execute("UPDATE jobs SET partes_enviadas = ? WHERE id = ?", (quantas, job_id))


def marca_enviado(con: sqlite3.Connection, job_id: int) -> None:
    con.execute("UPDATE jobs SET enviado_em = ? WHERE id = ?", (_agora(), job_id))


# --- cache de sala -> cadeira ---------------------------------------------


def cadeira_da_sala(con: sqlite3.Connection, sala: str) -> str | None:
    linha = con.execute("SELECT cadeira FROM salas WHERE sala = ?", (sala,)).fetchone()
    return linha["cadeira"] if linha else None


def grava_cadeira(con: sqlite3.Connection, sala: str, cadeira: str) -> None:
    """Cache sala -> cadeira, e o carimbo de nascimento da sala.

    `nascida_em` NAO se reescreve no conflito: a idade e da sala, e o gatilho da
    rotacao e a mensagem (minuta 0002). Reescrever aqui faria toda mensagem
    rejuvenescer a sala, e a rotacao de 24h nunca dispararia.
    """
    agora = _agora()
    con.execute(
        "INSERT INTO salas (sala, cadeira, atualizado_em, nascida_em) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(sala) DO UPDATE SET cadeira = excluded.cadeira,"
        " atualizado_em = excluded.atualizado_em",
        (sala, cadeira, agora, agora),
    )


def nascimento_da_sala(con: sqlite3.Connection, sala: str) -> float | None:
    """Epoch em que a sala entrou no journal. None quando ela e desconhecida;
    0 quando veio de banco anterior a migracao — nos dois casos quem chama
    decide, e nenhum deles e "idade zero"."""
    linha = con.execute("SELECT nascida_em FROM salas WHERE sala = ?", (sala,)).fetchone()
    if linha is None:
        return None
    return float(linha["nascida_em"] or 0.0)


def adota_nascimento(con: sqlite3.Connection, sala: str, quando: float) -> None:
    """Carimba a idade de sala que nasceu antes da migracao. So preenche o que
    esta em zero — sala com carimbo nao se reescreve."""
    con.execute(
        "UPDATE salas SET nascida_em = ? WHERE sala = ? AND (nascida_em IS NULL OR nascida_em = 0)",
        (quando, sala),
    )


def fita_da_sala(con: sqlite3.Connection, sala: str) -> str:
    linha = con.execute("SELECT id_fita FROM fitas WHERE sala = ?", (sala,)).fetchone()
    return linha["id_fita"] if linha else ""


def conta_giro(con: sqlite3.Connection, sala: str) -> int:
    """Incrementa e devolve o contador de giros da fita corrente da sala.

    E o fallback determinstico do criterio 17: formato de stream de CLI muda
    rapido, contador nao. Sala sem fita registrada conta zero — nao ha fita a
    ancorar, e inventar linha aqui poria contador em sala que nunca girou.
    """
    cur = con.execute(
        "UPDATE fitas SET giros = giros + 1, atualizado_em = ? WHERE sala = ?",
        (_agora(), sala),
    )
    if cur.rowcount == 0:
        return 0
    linha = con.execute("SELECT giros FROM fitas WHERE sala = ?", (sala,)).fetchone()
    return int(linha["giros"] or 0)


def giros_da_sala(con: sqlite3.Connection, sala: str) -> int:
    """Leitura pura do contador. `conta_giro` incrementa: quem so quer relatar
    tem de vir por aqui, senao relatar o estado adianta a rotacao."""
    linha = con.execute("SELECT giros FROM fitas WHERE sala = ?", (sala,)).fetchone()
    return int(linha["giros"] or 0) if linha else 0


def zera_giros(con: sqlite3.Connection, sala: str) -> None:
    con.execute("UPDATE fitas SET giros = 0 WHERE sala = ?", (sala,))


def preferencias_da_sala(con: sqlite3.Connection, sala: str) -> dict[str, str]:
    """Parametros de giro que a sala pediu (modelo, esforco). Sala sem pedido
    devolve dicionario vazio, e quem chama cai no default do verbo — ausencia
    aqui e "nao pediu", nunca "pediu o default"."""
    linhas = con.execute(
        "SELECT chave, valor FROM preferencias WHERE sala = ?", (sala,)
    ).fetchall()
    return {l["chave"]: l["valor"] for l in linhas}


def grava_preferencia(con: sqlite3.Connection, sala: str, chave: str, valor: str) -> None:
    con.execute(
        "INSERT INTO preferencias (sala, chave, valor, atualizado_em) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(sala, chave) DO UPDATE SET valor = excluded.valor,"
        " atualizado_em = excluded.atualizado_em",
        (sala, chave, valor, _agora()),
    )


def troca_de_sala(con: sqlite3.Connection, velha: str, nova: str, cadeira: str) -> None:
    """A cadeira mudou de endereco: a sala nova herda a cadeira e nasce agora,
    a velha some do cache e leva a fita e as preferencias junto.

    A fita NAO migra: sala nova e fita nova, que e o ponto inteiro da rotacao.
    Migrar o id aqui faria a sala limpa acordar com a conversa anterior dentro.
    """
    agora = _agora()
    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute(
            "INSERT INTO salas (sala, cadeira, atualizado_em, nascida_em) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(sala) DO UPDATE SET cadeira = excluded.cadeira,"
            " atualizado_em = excluded.atualizado_em",
            (nova, cadeira, agora, agora),
        )
        con.execute("DELETE FROM salas WHERE sala = ?", (velha,))
        con.execute("DELETE FROM fitas WHERE sala = ?", (velha,))
        # Preferencia e da SALA, e por isso morre com ela: sala nova volta ao
        # default do verbo. Herdar aqui faria a rotacao — que existe para dar
        # tela limpa — carregar um modelo caro que o dono nao pediu de novo.
        con.execute("DELETE FROM preferencias WHERE sala = ?", (velha,))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
