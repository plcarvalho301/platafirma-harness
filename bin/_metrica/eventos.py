"""eventos — o cliente da rota de escrita do banco de eventos de plataforma (spec banco-de-eventos-de-plataforma R6, R7 e
R8; spec eixos-do-host R15; card #3922).

MODULO IMPORTAVEL (como `cadencia` e `abertura`): `bin/sinal` o carrega e conduz a passada. Aqui moram quatro coisas:

  - a identidade: o `evento_id` é o uuid v5 do que a ficha declara (a amostra, de (eixo, minuto); a morte, de (boot,
    pid, instante do kernel)), no namespace da ficha, para o produtor e a rota calcularem igual;
  - o evento: o JSON do eixo (o retorno de `infra medir <eixo> --json`) vira o evento da ficha por LISTA FECHADA de
    campos. O que a ficha não nomeia fica no JSON e na frase do ato, e a rota o recusaria (422 ConteudoNoEvento,
    lote inteiro de volta). `executavel` e `conteiner` saem na forma que a rota aceita, sem espaço; chave fora da forma
    da rota vira desvio, e nunca recusa de lote;
  - a fila: o JSONL local de cada família (R8). Todo evento entra nela antes do envio e só sai dela quando a rota o
    aceitou (ou o recusou por nome, e então já está na quarentena). Banco mudo não perde amostra: a passada seguinte
    repõe;
  - o cliente: POST em lote, com o token da sonda, que nunca se imprime. 409 e 422 não se reenviam (o evento já está na
    quarentena); 401, 404, 503, 5xx e rede caída mantêm a fila.

O TOKEN e o segredo nunca entram em exceção, em retorno nem em saída: o módulo não os repete em lugar nenhum.
"""
from __future__ import annotations

import fcntl
import http.client
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent / "lib"))
sys.path.insert(0, str(AQUI.parent / "_infra"))
import eixos
import raizes

UTC = timezone.utc
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://wiki.platafirma.org/evento-de-plataforma")
URL_PADRAO = "http://127.0.0.1:8111"
FAMILIAS = ("eixo_host", "morte_limite")
SEGREDO_DO_TOKEN = ("eventos", "EVENTOS_SONDA_TOKEN")
LOTE_MAXIMO = 1000
LOTES_POR_PASSADA = 5
TENTATIVAS_POR_PASSADA = 25   # envios por passada, contando os que a rota recusou ou mandou partir
FILA_TETO = 50_000
TIMEOUT_PADRAO_S = 10.0
MAIORES = 10
CAUSA_SEM_RESPOSTA = "ato_nao_respondeu"
DESVIO_PADRAO = "fora_de_compose_e_unit"

HTTP_OK = 200
HTTP_CONFLITO = 409
HTTP_CORPO_GRANDE = 413
HTTP_RECUSA = 422

# As formas que a rota aceita (deploy/eventos/servico/logica.py); aqui só para sanear antes de enviar.
RE_CHAVE = re.compile(r"[a-z0-9][a-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.@:-]*")
RE_NOME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@:-]{0,127}")
_FORA_DO_BINARIO = re.compile(r"[^A-Za-z0-9_.+@:-]")
_FORA_DO_NOME = re.compile(r"[^A-Za-z0-9_.@:-]")
_RE_SLUG = re.compile(r"[a-z][a-z0-9_]*")
TAMANHO_DO_NOME = 128

CAMPOS_DO_TOPO = ("causa", "fonte", "valor", "unidade", "teto", "teto_fonte", "limiar", "limiar_por",
                  "pressao_avg10", "pressao_avg60", "pressao_avg300", "cache_bytes")


class RedeFora(Exception):
    """A rota não respondeu (rede, timeout, resposta ilegível): o lote fica na fila e volta na passada seguinte."""


# --- a identidade ---------------------------------------------------------------------------------

def minuto_iso(minuto: datetime) -> str:
    """O `ts` da amostra: o minuto cheio, UTC, segundos zero."""
    return minuto.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:00Z")


def id_da_amostra(eixo: str, minuto: datetime) -> str:
    return str(uuid.uuid5(NAMESPACE, f"eixo_host|{eixo}|{minuto.astimezone(UTC):%Y-%m-%dT%H:%MZ}"))


def id_da_morte(boot_id: str, pid: int, instante: datetime) -> str:
    return str(uuid.uuid5(NAMESPACE, f"morte_limite|{boot_id}|{pid}|{eixos.carimbo(instante)}"))


def nome_da_instancia() -> str:
    return os.environ.get("SINAL_INSTANCIA") or socket.gethostname()


def pasta_de_estado() -> Path:
    return raizes.instancia() / "var" / "eventos"


# --- o evento -------------------------------------------------------------------------------------

def executavel_da_rota(texto: object) -> str | None:
    """O nome-base do binário sem espaço nem argumento, na forma que a rota aceita; None quando não sobra nome."""
    if not isinstance(texto, str):
        return None
    limpo = _FORA_DO_BINARIO.sub("_", texto.strip())[:TAMANHO_DO_NOME]
    return limpo or None


def conteiner_da_rota(texto: object) -> str | None:
    """O nome do contêiner na forma da rota (sem espaço nem barra, começando por letra ou dígito)."""
    if not isinstance(texto, str):
        return None
    limpo = _FORA_DO_NOME.sub("_", texto.strip()).lstrip("_.@:-")[:TAMANHO_DO_NOME]
    return limpo if RE_NOME.fullmatch(limpo) else None


def _numero(valor: object) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def chave_ou_desvio(c: dict) -> dict:
    """A chave `<stack>/<serviço>` na forma da rota, ou o desvio. Chave fora da forma vira desvio, para a rota não
    recusar o lote inteiro por causa de um consumidor."""
    servico = c.get("servico")
    if isinstance(servico, str) and RE_CHAVE.fullmatch(servico):
        return {"servico": servico}
    desvio = c.get("desvio")
    return {"desvio": desvio if not servico and desvio in eixos.DESVIOS else DESVIO_PADRAO}


def _consumidor(c: dict, posicao: int, valor: float) -> dict:
    saida = {"posicao": posicao, "valor": valor, **chave_ou_desvio(c)}
    conteiner = conteiner_da_rota(c.get("conteiner"))
    if conteiner:
        saida["conteiner"] = conteiner
    if isinstance(c.get("pid"), int) and not isinstance(c["pid"], bool) and c["pid"] >= 1:
        saida["pid"] = c["pid"]
    executavel = executavel_da_rota(c.get("executavel"))
    if executavel:
        saida["executavel"] = executavel
    sm = c.get("sm_fracao")
    if _numero(sm) and 0 <= sm <= 1:
        saida["sm_ocupacao"] = float(sm)
    return saida


def _valor_do_consumidor(c: dict) -> float | None:
    valor = c.get("valor") if c.get("valor") is not None else c.get("reservado_bytes")
    return valor if _numero(valor) else None


def consumidores_do_evento(escolhidos: list[dict], fora: list[dict], j: dict) -> tuple[list[dict], dict]:
    """(os dez maiores, na ordem do maior ao menor, e o que ficou de fora). Fora é tudo o que a amostra não lista: o
    que passou do décimo, o que a cadência deixou de fora e o que o ato já contou como omitido."""
    com_valor = [(c, _valor_do_consumidor(c)) for c in escolhidos]
    validos = sorted(((c, v) for c, v in com_valor if v is not None), key=lambda par: -par[1])
    sem_valor = sum(1 for _, v in com_valor if v is None)
    lista = [_consumidor(c, i, v) for i, (c, v) in enumerate(validos[:MAIORES], start=1)]
    cortados = validos[MAIORES:]
    valores_fora = [v for c in fora if (v := _valor_do_consumidor(c)) is not None]
    omitidos = (j.get("consumidores_omitidos") or 0) + len(cortados) + len(fora) + sem_valor
    valor_omitido = (j.get("valor_omitido") or 0) + sum(v for _, v in cortados) + sum(valores_fora)
    extras = {}
    if j.get("consumidores_omitidos") is not None or omitidos:
        extras = {"consumidores_omitidos": omitidos, "valor_omitido": valor_omitido}
    return lista, extras


def diferenciar_reconexoes(j: dict, estado: dict) -> dict[str, int | None]:
    """A reconexão de cada túnel na janela: a diferença da contagem acumulada entre duas leituras do mesmo túnel. Sem
    leitura anterior vale nulo; com a contagem menor que a anterior (o cloudflared reiniciou) vale a contagem atual.
    Nunca um zero inventado. Guarda no estado a contagem desta leitura."""
    guardadas = estado.setdefault("reconexoes", {})
    saida: dict[str, int | None] = {}
    for t in j.get("tuneis") or []:
        atual = t.get("reconexoes_acumuladas")
        if t.get("estado_leitura") != "lida" or not isinstance(atual, int):
            saida[t["tunel"]] = None
            continue
        anterior = guardadas.get(t["tunel"])
        if not isinstance(anterior, int):
            saida[t["tunel"]] = None
        else:
            saida[t["tunel"]] = atual - anterior if atual >= anterior else atual
        guardadas[t["tunel"]] = atual
    return saida


def _tunel(t: dict, reconexoes: dict[str, int | None]) -> dict:
    saida = {"tunel": t["tunel"], "estado_leitura": t["estado_leitura"]}
    if t["estado_leitura"] != "lida":
        causa = t.get("causa")
        saida["causa"] = causa if isinstance(causa, str) and _RE_SLUG.fullmatch(causa) else "leitura_sem_causa"
        return saida
    for campo in ("conexoes_borda", "erros_transporte"):
        if isinstance(t.get(campo), int) and not isinstance(t[campo], bool) and t[campo] >= 0:
            saida[campo] = t[campo]
    if reconexoes.get(t["tunel"]) is not None:
        saida["reconexoes"] = reconexoes[t["tunel"]]
    if t["tunel"] == "ops" and _numero(t.get("latencia_externa_ms")) and t["latencia_externa_ms"] >= 0:
        saida["latencia_externa_ms"] = t["latencia_externa_ms"]
    return saida


def leitura_sem_resposta(eixo: str) -> dict:
    """O JSON de um eixo cujo ato não respondeu (timeout, exit fora de 0 e 5, saída que não é JSON): `nao_consegui_olhar`
    com a causa e a fonte, nunca um zero e nunca um minuto calado."""
    return {"schema_v": eixos.SCHEMA_V, "eixo": eixo, "instrumento": f"infra-medir-{eixo}",
            "estado_leitura": "nao_consegui_olhar", "causa": CAUSA_SEM_RESPOSTA, "fonte": f"infra medir {eixo}",
            "consumidores": []}


def evento_do_eixo(  # noqa: PLR0913 — por nome, nunca por posição: são os campos do envelope da amostra
    j: dict, *, minuto: datetime, janela_s: float, instancia: str, escolhidos: list[dict] | None = None,
    fora: list[dict] | None = None, reconexoes: dict[str, int | None] | None = None,
) -> dict:
    """O evento da família `eixo_host` do JSON do eixo `j`, só com campo da ficha. `escolhidos` são os consumidores que a
    cadência deixou entrar (todos, sem ela) e `fora` os que ela deixou de fora; `reconexoes`, a diferença por túnel."""
    eixo = j["eixo"]
    evento = {"evento_id": id_da_amostra(eixo, minuto), "ts": minuto_iso(minuto), "instancia": instancia,
              "instrumento": j["instrumento"], "schema_v": j["schema_v"], "estado_leitura": j["estado_leitura"],
              "eixo": eixo, "janela": janela_s}
    for campo in CAMPOS_DO_TOPO:
        if j.get(campo) is not None:
            evento[campo] = j[campo]
    lista, extras = consumidores_do_evento(j.get("consumidores") or [] if escolhidos is None else escolhidos,
                                           fora or [], j)
    evento["consumidores"] = lista
    evento.update(extras)
    if eixo == "rede" and j.get("tuneis"):
        evento["tuneis"] = [_tunel(t, reconexoes or {}) for t in j["tuneis"]]
    return evento


# --- a fila ---------------------------------------------------------------------------------------

@contextmanager
def trava(pasta: Path):
    """Uma passada de cada vez: `livre` diz se a trava foi tomada. Quem não a toma não escreve na fila."""
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "passada.lock", "a+", encoding="utf-8") as arquivo:
        try:
            fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
            livre = True
        except OSError:
            livre = False
        try:
            yield livre
        finally:
            if livre:
                fcntl.flock(arquivo, fcntl.LOCK_UN)


class Fila:
    """O JSONL local de uma família: um evento por linha, na ordem em que nasceram."""

    def __init__(self, pasta: Path, familia: str) -> None:
        self.caminho = pasta / f"fila-{familia}.jsonl"

    def ler(self) -> list[dict]:
        try:
            linhas = self.caminho.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        eventos = []
        for linha in linhas:
            try:
                evento = json.loads(linha)
            except ValueError:
                continue
            if isinstance(evento, dict):
                eventos.append(evento)
        return eventos

    def gravar(self, eventos: list[dict]) -> None:
        """Reescrita atômica: quem lê nunca vê meia fila."""
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        provisorio = self.caminho.with_name(f".{self.caminho.name}.{os.getpid()}")
        with open(provisorio, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(evento, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                         for evento in eventos)
            f.flush()
            os.fsync(f.fileno())
        os.replace(provisorio, self.caminho)

    def anexar(self, novos: list[dict]) -> int:
        """Põe os eventos novos no fim, antes de qualquer envio, sem repetir o que já está na fila. Acima do teto sai o
        mais antigo; devolve quantos saíram."""
        atuais = self.ler()
        vistos = {e.get("evento_id") for e in atuais}
        todos = atuais + [e for e in novos if e.get("evento_id") not in vistos]
        descartados = max(0, len(todos) - FILA_TETO)
        if novos or descartados:
            self.gravar(todos[descartados:])
        return descartados


# --- o cliente ------------------------------------------------------------------------------------

def ler_token() -> str | None:
    """O token da sonda em segredos/eventos/EVENTOS_SONDA_TOKEN; None quando não se lê. Nunca se imprime."""
    try:
        token = raizes.instancia().joinpath("segredos", *SEGREDO_DO_TOKEN).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token if token and "\n" not in token else None


def _pedir(requisicao: urllib.request.Request, timeout: float) -> tuple[int, dict | None]:
    """(status, corpo JSON ou None). Sem proxy de ambiente: é loopback. Erro HTTP volta como status; erro de rede sobe
    como RedeFora, sem o texto do erro, que poderia carregar o cabeçalho."""
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with abridor.open(requisicao, timeout=timeout) as r:
            status, bruto = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, bruto = e.code, e.read()
    except (urllib.error.URLError, OSError, TimeoutError, http.client.HTTPException):
        raise RedeFora("a rota não respondeu") from None
    try:
        corpo = json.loads(bruto)
    except ValueError:
        corpo = None
    return status, corpo if isinstance(corpo, dict) else None


def gravar_lote(url: str, familia: str, lote: list[dict], token: str, timeout: float) -> tuple[int, dict | None]:
    corpo = json.dumps({"eventos": lote}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    requisicao = urllib.request.Request(
        f"{url}/eventos/{familia}", data=corpo, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return _pedir(requisicao, timeout)


def _motivo_da_resposta(status: int, corpo: dict | None) -> str:
    if corpo and corpo.get("tipo"):
        return f"{status} {corpo['tipo']}: {str(corpo.get('detalhe') or '')[:160]}".rstrip(": ")
    return f"{status}"


def _indices_recusados(corpo: dict | None, tamanho: int) -> dict[int, dict]:
    recusados = (corpo or {}).get("recusados")
    if not isinstance(recusados, list):
        return {}
    return {r["indice"]: r for r in recusados
            if isinstance(r, dict) and isinstance(r.get("indice"), int) and 0 <= r["indice"] < tamanho}


def enviar_fila(  # noqa: PLR0913 — por nome, nunca por posição
    familia: str, fila: Fila, *, url: str, token: str, timeout: float = TIMEOUT_PADRAO_S, prazo: float | None = None,
) -> dict:
    """Envia a fila da família em lotes de até 1.000, no máximo cinco aceitos por passada. 200 tira o lote da fila. Recusa com
    `recusados` tira só os índices nomeados (o evento já está na quarentena) e o resto volta na mesma passada. 413 parte o
    lote ao meio. Qualquer outra resposta, e a rede caída, mantêm a fila e dizem a causa em `erro`."""
    resumo: dict = {"familia": familia, "inseridos": 0, "existentes": 0, "recusados": [], "pendentes": 0, "erro": None}
    tamanho, lotes, tentativas = LOTE_MAXIMO, 0, 0
    while lotes < LOTES_POR_PASSADA and tentativas < TENTATIVAS_POR_PASSADA:
        tentativas += 1
        if prazo is not None and time.monotonic() > prazo:
            resumo["erro"] = "prazo da passada esgotado"
            break
        pendentes = fila.ler()
        if not pendentes:
            break
        lote = pendentes[:tamanho]
        try:
            status, corpo = gravar_lote(url, familia, lote, token, timeout)
        except RedeFora as e:
            resumo["erro"] = str(e)
            break
        if status == HTTP_OK and corpo is not None:
            resumo["inseridos"] += len(corpo.get("inseridos") or [])
            resumo["existentes"] += len(corpo.get("existentes") or [])
            fila.gravar(pendentes[len(lote):])
            lotes += 1
            continue
        recusados = _indices_recusados(corpo, len(lote)) if status in (HTTP_CONFLITO, HTTP_RECUSA) else {}
        if recusados:
            resumo["recusados"] += [{"evento_id": r.get("evento_id"), "motivo": r.get("motivo"), "campo": r.get("campo")}
                                    for r in recusados.values()]
            fila.gravar([e for i, e in enumerate(lote) if i not in recusados] + pendentes[len(lote):])
            continue
        if status == HTTP_CORPO_GRANDE and len(lote) > 1:
            tamanho = max(1, len(lote) // 2)
            continue
        resumo["erro"] = _motivo_da_resposta(status, corpo)
        break
    resumo["pendentes"] = len(fila.ler())
    return resumo


def ler_serie(  # noqa: PLR0913 — por nome, nunca por posição
    eixo: str, *, de: datetime, ate: datetime, granularidade: str, url: str, timeout: float = TIMEOUT_PADRAO_S,
) -> tuple[int, dict | None]:
    """A API de leitura da família `eixo_host` (a leitura é só por ela, R11). Não pede token."""
    consulta = urllib.parse.urlencode({"eixo": eixo, "de": minuto_iso(de), "ate": minuto_iso(ate),
                                       "granularidade": granularidade})
    return _pedir(urllib.request.Request(f"{url}/eventos/eixo_host?{consulta}"), timeout)
