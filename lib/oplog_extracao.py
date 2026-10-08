"""oplog_extracao — o extrator do bruto da porta para a partição `log` (card #3353; arq:0123 regras 8, 11, 12 e 13).

Lê o dia FECHADO do bruto pelo módulo `oplog` (o único que abre `var/log/ops`), traduz cada linha legível
em UM evento SEM CONTEÚDO e o entrega à API do acervo (spec apis-escrita-acervo §D5, acervo-escrita.yaml
1.5.0, tag `log`). Roda sem modelo, só com a biblioteca padrão (o `linhagem-ops` roda no python3 do sistema).

    D5.1  PUT  /acervo/log/dias/{dia}                   o arquivo do dia e o sha256 dos bytes lidos
    D5.2  POST /acervo/log/dias/{dia}/extracoes         abre a passada (retoma a aberta)
    D5.3  POST /acervo/log/extracoes/{id}/eventos       lotes de 1.000, idempotentes por evento_id
    D5.4  POST /acervo/log/extracoes/{id}/fechar        a passada confere contagem e amostra

O QUE NÃO ATRAVESSA. Argumento, texto de erro, identidade do token (sujeito, sub, username, azp, sid, jti), a
pergunta e o texto do turno ficam no bruto. Um campo do evento só leva valor que casa com um vocabulário ou
uma forma curta (`ato`, `ledger`, `capacidade`...): o que não casa vira nulo e conta em `campos_invalidos`,
porque `ato` de uma linha recusada pode ser texto digitado pelo chamador. O serviço recusa o que sobrar
(422 ConteudoNoEvento); esta é a primeira trava, a dele é a que vale.

UMA LINHA, UM EVENTO. O tipo da partição sai do que a linha é (`tipo_particao`): a chamada de verbo é giro; a
abertura de sessão, o fecho, o escopo, o turno, a consulta do motor, o contorno e a queda no padrão são
tipos próprios; o acesso (http_req, auth_negada, pep_negou) é da extensão `acesso`. Linha que não cabe em
nenhum dos doze tipos NÃO é adivinhada: levanta `SemTraducao` e a passada não começa, com o nome do valor.

ORIGEM DA LINHA ANTIGA. A origem (cadeira, agente, sonda) se deduz da identidade ANTES de a identidade ser
descartada (`oplog.origem_da_linha`). A linha anterior à chave ganha o uuid v5 de (dia, linha).
"""
from __future__ import annotations

import hashlib
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
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import oplog

# --- o que a partição aceita (D1; o serviço confere de novo) ---------------------------------

TIPOS = ("giro", "abertura", "fecho", "auth_negada", "http_req", "pep_negou", "contorno", "fallback",
         "leitura", "escopo", "turno", "consulta_motor")
ORIGENS = ("cadeira", "agente", "sonda")
CLASSES = oplog.CLASSES
CLASSES_FONTE = ("verbo", "tabela")
# `abertura`, `runner` e `gap` são as fontes de 09/10/2026 em diante (spec log-de-negocio §3, Turno); `hook`, `transcript` e
# `declarado` só existem no bruto anterior. O CHECK de acervo.log_giro (088 e 089) tem as seis.
TURNO_FONTES = ("hook", "transcript", "runner", "declarado", "gap", "abertura")
ROTEADOR_VIAS = ("casou", "fallback")
MOTIVOS_NEGACAO = ("sem_token", "nao_jwt", "assinatura", "audience", "emissor", "expirado", "outro")
MOTIVOS_PARADA = ("concluiu", "teto_giros", "orcamento_erro", "interrompida")
FONTES_TOKENS = ("provedor", "estimado")

# O bruto começa em 15/09/2026 (arq:0123, Contexto): o primeiro dia que a linhagem cobre.
INICIO = date(2026, 9, 15)
LOTE = 1000
# O dia do arquivo é o dia local da porta, America/Sao_Paulo, UTC-3 fixo desde 2019 (spec log-de-negocio §3).
FUSO = timezone(timedelta(hours=-3))

# Como o roteador do bruto escreve a `via` e como a partição a quer: o desenho (D1) tem `casou` e `fallback`;
# o roteador grava também `determinístico` (casou por regra) e `comando` (chapéu forçado por argumento, o
# roteador não decidiu: vai nulo, sem contar como inválido).
_VIA_TRADUZIDA = {"fallback": "fallback", "determinístico": "casou", "deterministico": "casou", "casou": "casou"}
_VIA_FORCADA = frozenset({"comando"})

# O nome da exceção do JWT que a porta gravou em `motivo` -> o vocabulário fechado de `auth_negada`.
_MOTIVO_JWT = {"ExpiredSignatureError": "expirado", "InvalidAudienceError": "audience",
               "InvalidIssuerError": "emissor", "InvalidSignatureError": "assinatura",
               "DecodeError": "nao_jwt", "InvalidTokenError": "outro", "MissingRequiredClaimError": "outro",
               "ImmatureSignatureError": "outro", "InvalidAlgorithmError": "assinatura"}

_VAZIO = (None, "", "-")
_P_TOOL = re.compile(r"[A-Za-z0-9_.:-]{1,60}")
_P_ATO = re.compile(r"[A-Za-z0-9_.:+-]{1,60}")
_P_NOME = re.compile(r"[a-z][a-z0-9_]{0,39}")                  # lavado, ledger
_P_ID_CURTO = re.compile(r"[A-Za-z0-9_-]{1,40}")                  # lote_id
_P_SLUG = re.compile(r"[a-z0-9][a-z0-9._-]{0,59}")                # capacidade, ferramenta, chapeu, superficie
_P_CADEIRA = re.compile(r"[A-Za-z0-9_.-]{1,60}")
_P_ORDEM = re.compile(r"[A-Za-z0-9_.:-]{1,80}")
_P_TURNO = re.compile(r"[A-Za-z0-9_.:-]{1,60}")
_P_MAPA = re.compile(r"[A-Za-z0-9_.:-]{1,60}")
_P_ESCOPO = re.compile(r"#[0-9]+|atendimento")
_P_CAUSA = re.compile(r"[a-z][a-z0-9_]*")
_P_CAMINHO = re.compile(r"/[A-Za-z0-9/_.:%~+@-]{0,499}")
_P_ORIGEM_REQ = re.compile(r"[A-Za-z0-9_.:,@ -]{1,100}")
_P_SHA = re.compile(r"[0-9a-f]{7,64}")
_P_INSTANCIA = re.compile(r"[A-Za-z0-9_.-]{1,60}")
_P_PECA = re.compile(r"[a-z0-9_.-]{1,60}")
_P_REGRA = re.compile(r"[a-z][a-z0-9_ -]{0,59}")
_INT32 = 2 ** 31 - 1
_INT64 = 2 ** 63 - 1


class SemTraducao(Exception):
    """A linha não cabe em nenhum dos doze tipos da partição; `evento` é o valor que a identifica."""

    def __init__(self, evento: str, motivo: str = ""):
        super().__init__(f"{evento}{': ' + motivo if motivo else ''}")
        self.evento = evento
        self.motivo = motivo


class Falha(Exception):
    """Erro da API ou do arquivo, já com o exit da tabela (arq:0110 §4): 1 mérito · 2 uso · 3 fora do
    ar · 4 alarme/recusa · 5 indeterminável."""

    def __init__(self, codigo: int, mensagem: str, titulo: str | None = None, corpo: dict | None = None):
        super().__init__(mensagem)
        self.codigo, self.titulo, self.corpo = codigo, titulo, corpo or {}


# --- vocabulários: o valor casa ou vira nulo e conta ------------------------------------------

class Invalidos:
    """Os valores que não couberam na coluna e foram gravados nulos, por campo. Placeholder (`-`, vazio,
    ausente) é nulo de verdade, não inválido: a sonda grava `sessao_id: "-"` 1.400 vezes por dia."""

    def __init__(self):
        self.por_campo: Counter = Counter()

    def __call__(self, campo: str) -> None:
        self.por_campo[campo] += 1

    @property
    def total(self) -> int:
        return sum(self.por_campo.values())


def _forma(valor, padrao: re.Pattern, campo: str, inv: Invalidos):
    if valor in _VAZIO:
        return None
    if isinstance(valor, str) and padrao.fullmatch(valor):
        return valor
    inv(campo)
    return None


def _vocab(valor, vocabulario: tuple, campo: str, inv: Invalidos):
    if valor in _VAZIO:
        return None
    if isinstance(valor, str) and valor in vocabulario:
        return valor
    inv(campo)
    return None


def _inteiro(valor, campo: str, inv: Invalidos, minimo: int = 0, maximo: int = _INT32):
    if valor in _VAZIO:
        return None
    if isinstance(valor, float) and valor == int(valor):
        valor = int(valor)
    if isinstance(valor, int) and not isinstance(valor, bool) and minimo <= valor <= maximo:
        return valor
    inv(campo)
    return None


def _uuid_ou_nulo(valor, campo: str, inv: Invalidos):
    if valor in _VAZIO:
        return None
    if isinstance(valor, str) and not valor.lower().startswith("urn:"):
        try:
            return str(uuid.UUID(valor))
        except ValueError:
            pass
    inv(campo)
    return None


def _sem_nul(valor):
    """A linha da amostra vai a jsonb, que recusa NUL em texto: troca por U+FFFD (a prova de que é a mesma
    linha é o sha256 dos BYTES, que não muda)."""
    if isinstance(valor, str):
        return valor.replace("\x00", "�")
    if isinstance(valor, dict):
        return {_sem_nul(k): _sem_nul(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_sem_nul(v) for v in valor]
    return valor


# --- o tipo da linha ----------------------------------------------------------------------

def _e_chamada(reg: dict) -> bool:
    """Linha de chamada de ferramenta: tem `tool` e não é o transporte. É a mesma regra de `oplog._e_giro` e
    de `metrica.e_giro`, para a contagem de giros bater com a que `metrica` dava do bruto."""
    return reg.get("evento") != "http_req" and reg.get("tool") not in _VAZIO


def tipo_particao(reg: dict) -> str:
    """Em qual dos doze tipos de D1 a linha atravessa. Levanta `SemTraducao(evento)` quando em nenhum.

    A ordem importa: primeiro o que a linha DIZ ser (`evento`), depois a abertura, depois a chamada. Uma
    chamada negada pelo PEP tem `tool` e a classe `negada` (arq:0123 regra 5): é giro, e a classe a distingue.
    Sem `tool`, a negação do PEP e a do JWT são acesso.
    """
    evento = reg.get("evento")
    if evento == "http_req":
        return "http_req"
    if evento in ("auth_negada", "jwt_recusado"):
        return "auth_negada"
    if evento in ("escopo", "turno", "fecho", "fallback"):
        return evento
    if evento == "consulta":
        return "consulta_motor"
    if evento == "verbo_contornado":
        return "contorno"
    if evento in _VAZIO and reg.get("tool") in ("monta_sessao", "monta-sessao") \
            and oplog.classificar(reg)["classe"] == "ok":
        return "abertura"
    if _e_chamada(reg):
        return "giro"
    if isinstance(evento, str) and (evento.startswith("pep_negou") or evento == "negado"):
        return "pep_negou"
    raise SemTraducao(str(evento) if evento not in _VAZIO else "(sem evento, sem tool)")


# --- a tradução de uma linha ---------------------------------------------------------------

def _ts(reg: dict, dia: str, inv: Invalidos) -> datetime:
    bruto = reg.get("ts")
    if isinstance(bruto, str):
        try:
            ts = datetime.fromisoformat(bruto[:-1] + "+00:00" if bruto.endswith("Z") else bruto)
            return ts if ts.tzinfo else ts.replace(tzinfo=FUSO)
        except ValueError:
            pass
    inv("ts")
    return datetime.fromisoformat(f"{dia}T00:00:00").replace(tzinfo=FUSO)


def origem_do_evento(reg: dict) -> str:
    """A origem (cadeira, agente, sonda) que o evento leva: a que a porta gravou, ou a deduzida da identidade. É a
    regra do extrator e a que `metrica --fonte bruto` usa, para as duas séries serem a mesma conta."""
    origem = reg.get("origem")
    return origem if origem in ORIGENS else oplog.origem_da_linha(reg)


def classe_do_giro(reg: dict) -> str:
    """A classe do giro: a que a porta gravou, ou a deduzida do `exit_code` pela tabela de saída (arq:0110 §4)."""
    return reg.get("classe") if reg.get("classe") in CLASSES else oplog.classificar(reg)["classe"]


def _topo(reg: dict, tipo: str, dia: str, n: int, inv: Invalidos) -> dict:
    evento_id = _uuid_ou_nulo(reg.get("evento_id"), "evento_id", inv) or oplog.evento_id_da_linha(dia, n)
    origem = origem_do_evento(reg)
    schema_v = _inteiro(reg.get("schema_v"), "schema_v", inv)
    return {
        "evento_id": evento_id, "tipo": tipo, "ts": _ts(reg, dia, inv).isoformat(timespec="milliseconds"),
        "fonte": "bruto", "linha_n": n, "schema_v": schema_v if schema_v is not None else 0,
        "instancia": _forma(reg.get("instancia"), _P_INSTANCIA, "instancia", inv),
        "cadeira": _forma(reg.get("cadeira"), _P_CADEIRA, "cadeira", inv),
        "ordem_id": _forma(reg.get("ordem_id"), _P_ORDEM, "ordem_id", inv),
        "sessao_id": _uuid_ou_nulo(reg.get("sessao_id"), "sessao_id", inv),
        "origem": origem,
        "origem_sessao": _uuid_ou_nulo(reg.get("origem_sessao"), "origem_sessao", inv),
        "mapa_v": _forma(reg.get("mapa_v"), _P_MAPA, "mapa_v", inv),
    }


def _giro(reg: dict, inv: Invalidos) -> dict:
    tool = reg.get("tool")
    if not (isinstance(tool, str) and _P_TOOL.fullmatch(tool)):
        raise SemTraducao("(tool fora da forma)", "a ferramenta não casa com a forma de nome")
    c = oplog.classificar(reg)
    classe = classe_do_giro(reg)
    classe_fonte = reg.get("classe_fonte") if reg.get("classe_fonte") in CLASSES_FONTE else c["classe_fonte"]
    causa = None
    if classe == "execucao":
        causa = _forma(reg.get("causa") or c.get("causa"), _P_CAUSA, "causa", inv)
    lavado = reg.get("lavado")
    if isinstance(lavado, list):
        boas = [x for x in lavado if isinstance(x, str) and _P_NOME.fullmatch(x)]
        if len(boas) != len(lavado):
            inv("lavado")
        lavado = boas[:20]
    else:
        lavado = []
    return {
        "tool": tool,
        "ato": _forma(reg.get("ato"), _P_ATO, "ato", inv),
        "exit_code": _inteiro(reg.get("exit_code"), "exit_code", inv, minimo=-_INT32),
        "classe": classe, "causa": causa, "classe_fonte": classe_fonte,
        "dur_ms": _inteiro(reg.get("dur_ms"), "dur_ms", inv),
        "bytes_produzidos": _inteiro(reg.get("bytes_produzidos"), "bytes_produzidos", inv, maximo=_INT64),
        "bytes_servidos": _inteiro(reg.get("bytes_servidos"), "bytes_servidos", inv, maximo=_INT64),
        "lavado": lavado,
        "ledger": _forma(reg.get("ledger"), _P_NOME, "ledger", inv),
        "lote_id": _forma(reg.get("lote_id"), _P_ID_CURTO, "lote_id", inv),
        "lote_n": _inteiro(reg.get("lote_n"), "lote_n", inv),
        "capacidade": _forma(reg.get("capacidade"), _P_SLUG, "capacidade", inv),
        "ferramenta": _forma(reg.get("ferramenta"), _P_SLUG, "ferramenta", inv),
        "escopo": _forma(reg.get("escopo"), _P_ESCOPO, "escopo", inv),
        "turno_id": _forma(reg.get("turno_id"), _P_TURNO, "turno_id", inv),
        "turno_fonte": _vocab(reg.get("turno_fonte"), TURNO_FONTES, "turno_fonte", inv),
        "aparado": bool(reg.get("aparado")),
    }


def bloco_giro(reg: dict) -> dict:
    """O bloco `giro` que a linha levaria à partição (o mesmo de `para_item`), sem contar campo inválido. Levanta
    `SemTraducao`. `metrica dia --fonte bruto` conta por ele, para o bruto e a partição serem a mesma conta."""
    return _giro(reg, Invalidos())


def _acesso(reg: dict, tipo: str, inv: Invalidos) -> dict:
    caminho = reg.get("path") if isinstance(reg.get("path"), str) else None
    if caminho is not None:
        caminho = caminho.split("?", 1)[0]      # a query pode levar token: o caminho atravessa sem ela
    motivo = None
    if tipo == "auth_negada":
        bruto = reg.get("motivo")
        if reg.get("evento") == "jwt_recusado":
            motivo = _MOTIVO_JWT.get(bruto, "outro") if isinstance(bruto, str) else None
        else:
            motivo = _vocab(bruto, MOTIVOS_NEGACAO, "motivo", inv)
    elif tipo == "pep_negou":
        motivo = _forma(reg.get("regra") or reg.get("motivo"), _P_REGRA, "motivo", inv)
    status = reg.get("status") if reg.get("status") is not None else reg.get("status_http")
    return {
        "caminho": _forma(caminho, _P_CAMINHO, "caminho", inv),
        "origem_requisicao": _forma(reg.get("origem_requisicao"), _P_ORIGEM_REQ, "origem_requisicao", inv),
        "status_http": _inteiro(status, "status_http", inv, minimo=100, maximo=599),
        "motivo": motivo,
    }


def _tokens_pacote(reg: dict, inv: Invalidos):
    """Tokens por peça e o método de contagem, em objeto raso: {peça: tokens, "metodo": nome}. A linha grava
    por peça um dicionário ou uma lista de pares/objetos."""
    pecas = reg.get("tokens_pecas")
    saida: dict = {}
    if isinstance(pecas, dict):
        itens = list(pecas.items())
    elif isinstance(pecas, list):
        itens = []
        for p in pecas:
            if isinstance(p, dict) and "peca" in p:
                itens.append((p["peca"], p.get("tokens")))
            elif isinstance(p, (list, tuple)) and len(p) == 2:
                itens.append((p[0], p[1]))
    else:
        itens = []
    for peca, tokens in itens[:60]:
        if isinstance(peca, str) and _P_PECA.fullmatch(peca) and isinstance(tokens, (int, float)) \
                and not isinstance(tokens, bool):
            saida[peca] = tokens
        else:
            inv("tokens_pacote")
    metodo = reg.get("metodo_tokens")
    if isinstance(metodo, str) and _P_SLUG.fullmatch(metodo.lower().replace(" ", "-")):
        saida["metodo"] = metodo.lower().replace(" ", "-")
    elif metodo not in _VAZIO:
        inv("tokens_pacote")
    return saida or None


def _abertura(reg: dict, inv: Invalidos) -> dict:
    via = reg.get("roteador_via")
    if via in _VAZIO or via in _VIA_FORCADA:
        via_particao = None
    elif via in _VIA_TRADUZIDA:
        via_particao = _VIA_TRADUZIDA[via]
    else:
        inv("roteador_via")
        via_particao = None
    return {
        "superficie": _forma(reg.get("superficie"), _P_SLUG, "superficie", inv),
        "chapeu": _forma(reg.get("chapeu"), _P_SLUG, "chapeu", inv),
        "roteador_via": via_particao,
        "tokens_pacote": _tokens_pacote(reg, inv),
        "prefixo_sha": _forma(reg.get("prefixo_sha"), _P_SHA, "prefixo_sha", inv),
        "montador_sha": _forma(reg.get("montador_sha"), _P_SHA, "montador_sha", inv),
    }


def _fecho(reg: dict, inv: Invalidos) -> dict:
    return {
        "motivo_parada": _vocab(reg.get("motivo_parada"), MOTIVOS_PARADA, "motivo_parada", inv),
        "tokens": _inteiro(reg.get("tokens"), "tokens", inv, maximo=_INT64),
        "fonte_tokens": _vocab(reg.get("fonte_tokens"), FONTES_TOKENS, "fonte_tokens", inv),
    }


_BLOCO = {"giro": "giro", "abertura": "abertura", "fecho": "fecho",
          "auth_negada": "acesso", "http_req": "acesso", "pep_negou": "acesso"}


def para_item(reg: dict, dia: str, n: int, inv: Invalidos) -> dict:
    """O item do lote de D5.3 para uma linha legível: `{evento, <bloco>}`, sem `conteudo` (o conteúdo da
    amostra se junta depois, quando o dia inteiro foi lido). Levanta `SemTraducao`."""
    tipo = tipo_particao(reg)
    item = {"evento": _topo(reg, tipo, dia, n, inv)}
    bloco = _BLOCO.get(tipo)
    if bloco == "giro":
        item["giro"] = _giro(reg, inv)
    elif bloco == "acesso":
        item["acesso"] = _acesso(reg, tipo, inv)
    elif bloco == "abertura":
        item["abertura"] = _abertura(reg, inv)
    elif bloco == "fecho":
        item["fecho"] = _fecho(reg, inv)
    return item


# --- a amostra (arq:0123 regra 8; D1) ----------------------------------------------------------

def amostra_esperada(giros) -> set[str]:
    """Todo giro de classe `execucao` ou `interrompida` e os dez `ok` de menor md5(evento_id::text) por tool
    (todos, se forem dez ou menos), no dia. `giros` = iterável de (evento_id, tool, classe). É a MESMA regra
    do serviço (platafirma-conhecimento, motor_acervo/log_evento.amostra_esperada); o teste das duas pontas
    usa o mesmo vetor, e o fecho da passada confere o conjunto gravado contra a regra do servidor."""
    escolhidos: set[str] = set()
    oks: dict[str, list[str]] = {}
    for evento_id, tool, classe in giros:
        if classe in ("execucao", "interrompida"):
            escolhidos.add(evento_id)
        elif classe == "ok":
            oks.setdefault(tool, []).append(evento_id)
    for ids in oks.values():
        ids.sort(key=lambda e: (hashlib.md5(e.encode("ascii")).hexdigest(), e))  # noqa: S324 — a regra é md5
        escolhidos.update(ids[:10])
    return escolhidos


# --- o dia lido ---------------------------------------------------------------------------------

class Extracao:
    """Um dia do bruto traduzido. `itens` na ordem do arquivo; nada vai à rede aqui."""

    def __init__(self, dia: str, dados: bytes | None):
        self.dia = dia
        self.ausente = dados is None
        self.arquivo = oplog.nome_do_dia(dia)
        self.bytes = len(dados) if dados is not None else None
        self.sha256 = hashlib.sha256(dados).hexdigest() if dados is not None else None
        self.invalidos = Invalidos()
        self.itens: list[dict] = []
        self.por_tipo: Counter = Counter()
        self.schema_v: set[int] = set()
        self.ilegiveis = 0
        self.sem_traducao: Counter = Counter()
        self.por_evento: Counter = Counter()        # o valor de `evento` da linha -> quantas (só contagem)
        self.por_tool_e_tipo: Counter = Counter()   # (tool, tipo da partição) das linhas com `tool`: reconcilia com `metrica`
        self._conteudos: dict[str, dict] = {}
        if dados is not None:
            self._ler(dados)
        giros = [(i["evento"]["evento_id"], i["giro"]["tool"], i["giro"]["classe"])
                 for i in self.itens if i["evento"]["tipo"] == "giro"]
        self.amostra = amostra_esperada(giros)

    def _ler(self, dados: bytes) -> None:
        for n, bruta, reg in oplog.linhas_do_dia(dados):
            if reg is None:
                self.ilegiveis += 1
                continue
            self.por_evento[str(reg.get("evento")) if reg.get("evento") not in _VAZIO else "(sem evento)"] += 1
            try:
                item = para_item(reg, self.dia, n, self.invalidos)
            except SemTraducao as e:
                self.sem_traducao[e.evento] += 1
                continue
            self.itens.append(item)
            self.por_tipo[item["evento"]["tipo"]] += 1
            if _e_chamada(reg):
                self.por_tool_e_tipo[(reg["tool"], item["evento"]["tipo"])] += 1
            self.schema_v.add(item["evento"]["schema_v"])
            if item["evento"]["tipo"] == "giro":
                self._conteudos[item["evento"]["evento_id"]] = {
                    "linha": _sem_nul(reg), "linha_sha256": hashlib.sha256(bruta).hexdigest()}

    @property
    def legiveis(self) -> int:
        return len(self.itens) + sum(self.sem_traducao.values())

    @property
    def lidas(self) -> int:
        return self.legiveis + self.ilegiveis

    def lotes(self, tamanho: int = LOTE):
        """Os itens em lotes, o conteúdo junto do item que é da amostra."""
        lote = []
        for item in self.itens:
            if item["evento"]["evento_id"] in self.amostra:
                item = {**item, "conteudo": self._conteudos[item["evento"]["evento_id"]]}
            lote.append(item)
            if len(lote) == tamanho:
                yield lote
                lote = []
        if lote:
            yield lote

    def fecho(self, autor: str) -> dict:
        return {"autor": autor, "linhas_lidas": self.lidas, "linhas_legiveis": self.legiveis,
                "linhas_ilegiveis": self.ilegiveis, "campos_invalidos": self.invalidos.total,
                "schema_v_achadas": sorted(self.schema_v), "por_tipo": dict(sorted(self.por_tipo.items()))}


def extrair(dia: str, diretorio_=None) -> Extracao:
    return Extracao(dia, oplog.conteudo_do_dia(dia, diretorio_))


def relatorio_seco(ext: Extracao) -> dict:
    """O que o dia traria, SÓ em contagem: nenhum valor de campo, nenhum argumento, nenhuma identidade. É
    leitura mecânica pelo módulo que não devolve conteúdo a quem chamou (arq:0123 regra 15), por isso roda
    sem incidente. Serve para fechar a tabela de tradução com o dado real antes da primeira passada."""
    giros = Counter()
    for i in ext.itens:
        if i["evento"]["tipo"] == "giro":
            giros[(i["giro"]["tool"], i["giro"]["classe"])] += 1
    # A contagem que `metrica` dá do bruto é «toda linha com tool que não é http_req», e a da partição só conta
    # o que é giro. Por tool, a conta fecha assim: legado = giro + abertura + consulta_motor + fecho + ...
    por_tool: dict[str, dict] = {}
    for (tool, tipo), n in sorted(ext.por_tool_e_tipo.items()):
        por_tool.setdefault(tool, {})[tipo] = n
    legado = {t: sum(d.values()) for t, d in por_tool.items()}
    return {
        "dia": ext.dia, "ausente": ext.ausente, "arquivo": ext.arquivo, "bytes": ext.bytes, "sha256": ext.sha256,
        "linhas_lidas": ext.lidas, "linhas_legiveis": ext.legiveis, "linhas_ilegiveis": ext.ilegiveis,
        "por_evento_do_bruto": dict(sorted(ext.por_evento.items(), key=lambda kv: (-kv[1], kv[0]))),
        "por_tipo_da_particao": dict(sorted(ext.por_tipo.items())),
        "sem_traducao": dict(sorted(ext.sem_traducao.items())),
        "campos_invalidos": ext.invalidos.total,
        "campos_invalidos_por_campo": dict(sorted(ext.invalidos.por_campo.items(), key=lambda kv: (-kv[1], kv[0]))),
        "schema_v_achadas": sorted(ext.schema_v),
        "amostra_n": len(ext.amostra),
        "giros_por_tool_e_classe": {f"{t}:{c}": n for (t, c), n in sorted(giros.items())},
        "giros_por_tool": dict(sorted(Counter({t: sum(n for (tt, _), n in giros.items() if tt == t)
                                               for t, _ in giros}).items())),
        "giros_legado_por_tool": legado,
        "por_tool_e_tipo": por_tool,
    }


# --- a API --------------------------------------------------------------------------------------

def _base_url() -> str:
    return (os.environ.get("MOTOR_ACERVO_URL") or os.environ.get("RAG_API_URL")
            or os.environ.get("RAG_API_BASE") or "http://127.0.0.1:8100").rstrip("/")


class Api:
    """O cliente HTTP do acervo (urllib, como `bin/bot`). O exit da tabela (arq:0110 §4): 404/405 que não é do
    negócio e 503 = 3 (contrato fora do ar ou banco fora) · 401/403 = 4 · 409/422/404 de negócio = 1 · outro
    5xx e conexão que cai = 5 · outro 4xx = 2."""

    NEGOCIO_404 = frozenset({"ExtracaoNaoEncontrada"})

    def __init__(self, base: str | None = None, token: str | None = None, timeout: float | None = None):
        self.base = (base or _base_url()).rstrip("/")
        self.token = (os.environ.get("RAG_API_TOKEN", "") if token is None else token).strip()
        self.timeout = timeout if timeout is not None else float(os.environ.get("LINHAGEM_TIMEOUT_S", "180"))

    def chamar(self, metodo: str, caminho: str, corpo: dict | None = None, params: dict | None = None,
               aceita: tuple = (200,)) -> tuple[int, dict | None]:
        url = self.base + caminho + ("?" + urllib.parse.urlencode(params) if params else "")
        cab = {"Accept": "application/json"}
        dados = None
        if corpo is not None:
            dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            cab["Content-Type"] = "application/json"
        if self.token:
            cab["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=dados, method=metodo, headers=cab)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 — loopback
                status, bruto = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, bruto = e.code, e.read()
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise Falha(5, f"{metodo} {caminho}: passou de {self.timeout:g}s sem resposta; não se sabe se valeu") from None
            raise Falha(3, f"{metodo} {caminho}: {self.base} não respondeu ({e.reason})") from None
        except (OSError, ValueError, http.client.HTTPException) as e:     # IncompleteRead etc. não são OSError
            raise Falha(5, f"{metodo} {caminho}: a conexão caiu ({type(e).__name__}); não se sabe se valeu") from None
        obj = None
        if bruto:
            try:
                obj = json.loads(bruto)
            except ValueError:
                obj = None
        titulo = obj.get("title") if isinstance(obj, dict) else None
        detalhe = obj.get("detail") if isinstance(obj, dict) else None
        if status in (404, 405) and titulo not in self.NEGOCIO_404:
            raise Falha(3, f"{metodo} {caminho}: rota ausente em {self.base} (HTTP {status}); "
                           "o contrato acervo-escrita >= 1.5.0 (tag log) não está no ar", titulo, obj)
        if status in aceita:
            return status, obj
        msg = f"{metodo} {caminho}: HTTP {status}" + (f" {titulo}" if titulo else "") + (f": {detalhe}" if detalhe else "")
        codigo = (3 if status == 503 else 5 if status >= 500 else 4 if status in (401, 403)
                  else 1 if status in (404, 409, 422) else 2)
        raise Falha(codigo, msg, titulo, obj if isinstance(obj, dict) else None)


# --- a passada de um dia ----------------------------------------------------------------------------

def versao_do_extrator() -> str:
    """O sha de onde este código roda: a release sob /opt/platafirma, ou `PF_VERSAO_EXTRATOR`, ou `dev`."""
    if os.environ.get("PF_VERSAO_EXTRATOR"):
        return os.environ["PF_VERSAO_EXTRATOR"][:80]
    achado = re.search(r"/([0-9a-f]{40})(?:/|$)", os.path.realpath(__file__))
    return achado.group(1)[:12] if achado else "dev"


def _com_retomada(operacao, tentativas: int = 4, espera=time.sleep):
    """D5.3 e PUT são idempotentes: conexão que cai ou 5xx volta a tentar, com 2, 4, 8 e 16 s."""
    for k in range(tentativas):
        try:
            return operacao()
        except Falha as f:
            if f.codigo not in (3, 5) or k == tentativas - 1:
                raise
            espera(2 ** (k + 1))
    raise AssertionError("inalcançável")  # pragma: no cover


def passada(api: Api, ext: Extracao, autor: str, versao: str, espera=time.sleep) -> dict:
    """D5.1 a D5.4 para um dia lido. Devolve a passada fechada (a resposta de D5.4)."""
    if ext.sem_traducao:
        nomes = ", ".join(f"{e} ({n})" for e, n in sorted(ext.sem_traducao.items()))
        raise Falha(1, f"{ext.dia}: linha sem tradução para os doze tipos da partição — {nomes}; a passada não começou",
                    "SemTraducao")
    dia = {"autor": autor} if ext.ausente else {"autor": autor, "arquivo": ext.arquivo, "bytes": ext.bytes,
                                                "sha256": ext.sha256}
    if ext.ausente:
        dia["ausente"] = True
    _com_retomada(lambda: api.chamar("PUT", f"/acervo/log/dias/{ext.dia}", dia, aceita=(200, 201)), espera=espera)
    abertura = {"autor": autor, "versao_extrator": versao, "sha256_lido": ext.sha256}
    try:
        _, passada_ = api.chamar("POST", f"/acervo/log/dias/{ext.dia}/extracoes", abertura, aceita=(201,))
        extracao_id = passada_["id"]
    except Falha as f:
        if f.titulo != "ExtracaoAberta" or not f.corpo.get("extracao_id"):
            raise
        extracao_id = f.corpo["extracao_id"]       # a passada que ficou aberta: retoma, D5.3 é idempotente
    for lote in ext.lotes():
        _com_retomada(lambda lote=lote: api.chamar(
            "POST", f"/acervo/log/extracoes/{extracao_id}/eventos", {"autor": autor, "itens": lote}), espera=espera)
    try:
        _, fechada = api.chamar("POST", f"/acervo/log/extracoes/{extracao_id}/fechar", ext.fecho(autor))
    except Falha as f:
        if f.codigo == 5:       # a resposta se perdeu: se a passada fechou, vale
            _, atual = api.chamar("GET", f"/acervo/log/extracoes/{extracao_id}")
            if atual and atual.get("estado") == "concluida":
                return atual
        raise
    return fechada


def dias_pendentes(api: Api, hoje: date, inicio: date = INICIO) -> list[str]:
    """Todo dia FECHADO desde `inicio` sem passada concluída, em ordem. Um GET só (até 400 dias)."""
    ate = hoje - timedelta(days=1)
    if ate < inicio:
        return []
    _, corpo = api.chamar("GET", "/acervo/log/dias", params={"desde": inicio.isoformat(), "ate": ate.isoformat()})
    return [linha["dia"] for linha in (corpo or {}).get("itens", []) if linha.get("passada") is None]


def hoje_local() -> date:
    return datetime.now(timezone.utc).astimezone(FUSO).date()


def linha_do_dia(ext: Extracao, fechada: dict) -> str:
    return (f"linhagem-ops {ext.dia}: {fechada.get('estado')} cobertura={fechada.get('cobertura')} "
            f"lidas={fechada.get('linhas_lidas')} legiveis={fechada.get('linhas_legiveis')} "
            f"ilegiveis={fechada.get('linhas_ilegiveis')} novos={fechada.get('eventos_novos')} "
            f"existentes={fechada.get('eventos_existentes')} amostra={fechada.get('amostra_n')} "
            f"invalidos={fechada.get('campos_invalidos')} sha256={(ext.sha256 or '-')[:12]} "
            f"passada={fechada.get('id')}")


USO = """uso: linhagem-ops [--dia AAAA-MM-DD ...] [--seco AAAA-MM-DD ...] [--desde AAAA-MM-DD]
sem argumento: todo dia fechado desde 15/09/2026 sem passada concluída, um por vez, em ordem.
  --dia    roda esse dia (de novo, se já tem passada: é idempotente); pode repetir
  --desde  muda o primeiro dia da busca dos pendentes
  --seco   não toca a API: lê o dia e imprime só CONTAGEM (valores de `evento`, tipos, tradução faltando,
           campos inválidos, giros por tool e classe). Leitura mecânica, sem conteúdo.
exit: 0 ok · 1 passada reprovada · 2 uso · 3 API ou banco fora · 4 alarme de integridade ou token recusado · 5 indeterminável"""


def main(argv: list[str], api: Api | None = None, hoje: date | None = None, saida=print,
         diretorio_=None, espera=time.sleep) -> int:
    dias, secos, desde = [], [], INICIO
    args = list(argv)
    try:
        while args:
            a = args.pop(0)
            if a == "--dia":
                dias.append(date.fromisoformat(args.pop(0)).isoformat())
            elif a == "--seco":
                secos.append(date.fromisoformat(args.pop(0)).isoformat())
            elif a == "--desde":
                desde = date.fromisoformat(args.pop(0))
            elif a in ("-h", "--help", "--ajuda"):
                saida(USO)
                return 0
            else:
                raise ValueError(a)
    except (IndexError, ValueError):
        print(USO, file=sys.stderr)
        return 2
    if secos:
        for dia in secos:
            saida(json.dumps(relatorio_seco(extrair(dia, diretorio_)), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    api = api or Api()
    pior = 0
    autor = os.environ.get("PF_CADEIRA") or "ti"
    versao = versao_do_extrator()
    try:
        alvo = dias or dias_pendentes(api, hoje or hoje_local(), desde)
    except Falha as f:
        print(f"linhagem-ops: {f}", file=sys.stderr)
        return f.codigo
    if not alvo:
        saida("linhagem-ops: nenhum dia pendente")
        return 0
    for dia in alvo:
        if date.fromisoformat(dia) >= (hoje or hoje_local()):
            print(f"linhagem-ops {dia}: dia ainda aberto, não se extrai", file=sys.stderr)
            pior = max(pior, 2)
            continue
        ext = extrair(dia, diretorio_)
        try:
            fechada = passada(api, ext, autor, versao, espera=espera)
        except Falha as f:
            print(f"linhagem-ops {dia}: {f}" + (f" [{f.titulo}]" if f.titulo else ""), file=sys.stderr)
            if f.titulo == "Sha256Divergente":
                print(f"linhagem-ops {dia}: ALARME DE INTEGRIDADE — o dia fica no disco e o incidente vai à "
                      "mesa de seguranca (arq:0123 regra 12)", file=sys.stderr)
            pior = max(pior, f.codigo)
            continue
        saida(linha_do_dia(ext, fechada))
    return pior
