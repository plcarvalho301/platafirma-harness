"""Leitura e consulta de robots.txt conforme RFC 9309 (card #4458).

Suporta agrupamento de User-agent, precedência pelo padrão mais longo (empate vence
Allow), curingas `*` e âncora de fim `$`, diretivas `Crawl-delay` e `Sitemap`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

NOME_ROBO = "platafirma-pesquisa"
TOKENS_CASA = ("platafirma-pesquisa", "platafirma")

_HTTP_CLIENT_MIN = 400
_HTTP_SERVER_MIN = 500
_HTTP_TOO_MANY = 429
_RE_HEX_PCT = re.compile(r"%[0-9a-fA-F]{2}")
_RE_ATRASO = re.compile(r"^\d+(?:\.\d+)?$")


def _normalizar_pct(texto: str) -> str:
    return _RE_HEX_PCT.sub(lambda m: m.group(0).upper(), texto)


def _compilar_padrao(padrao: str) -> re.Pattern[str]:
    norm = _normalizar_pct(padrao)
    ancora_fim = norm.endswith("$")
    miolo = norm[:-1] if ancora_fim else norm
    partes = [re.escape(trecho) for trecho in miolo.split("*")]
    expr = "^" + ".*".join(partes) + (r"\Z" if ancora_fim else "")
    return re.compile(expr)


@dataclass(frozen=True)
class RegraRobots:
    """Uma regra Allow ou Disallow compilada."""

    permitido: bool
    padrao: str
    regex: re.Pattern[str]
    comprimento: int


@dataclass
class _GrupoRobots:
    agentes: list[str] = field(default_factory=list)
    regras: list[RegraRobots] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass(frozen=True)
class PoliticaRobots:
    """Política efetiva de um host para o robô da casa."""

    host: str
    status: int | None
    regras: tuple[RegraRobots, ...]
    crawl_delay: float | None = None
    sitemaps: tuple[str, ...] = ()
    indisponivel: bool = False
    motivo_indisponivel: str | None = None

    def pode_buscar(self, url: str) -> tuple[bool, str | None]:
        """Devolve `(permitido, motivo)`. Quando negado, `motivo` traz a regra ou causa."""
        if self.indisponivel:
            return False, self.motivo_indisponivel or "robots-indisponivel"
        if not self.regras:
            return True, None
        partes = urlsplit(url)
        caminho = partes.path or "/"
        if not caminho.startswith("/"):
            caminho = "/" + caminho
        alvo = _normalizar_pct(f"{caminho}?{partes.query}" if partes.query else caminho)
        vencedora: RegraRobots | None = None
        chave_venc = (-1, -1)
        for regra in self.regras:
            if not regra.regex.search(alvo):
                continue
            chave = (regra.comprimento, 1 if regra.permitido else 0)
            if chave > chave_venc:
                chave_venc = chave
                vencedora = regra
        if vencedora is None or vencedora.permitido:
            return True, None
        return False, f"robots:{vencedora.padrao}"


def _limpar_linha(linha: str) -> tuple[str, str] | None:
    sem_comentario = linha.split("#", 1)[0].strip()
    if ":" not in sem_comentario:
        return None
    chave, _, valor = sem_comentario.partition(":")
    k = chave.strip().lower()
    v = valor.strip()
    return (k, v) if k else None


def _aplicar_diretiva_regra(grupo: _GrupoRobots, chave: str, valor: str) -> None:
    if chave in ("allow", "disallow"):
        if not valor:
            return
        padrao = valor if valor.startswith(("/", "*")) else "/" + valor
        grupo.regras.append(
            RegraRobots(
                permitido=(chave == "allow"),
                padrao=padrao,
                regex=_compilar_padrao(padrao),
                comprimento=len(padrao.encode("utf-8")),
            )
        )
        return
    if chave == "crawl-delay" and _RE_ATRASO.fullmatch(valor):
        atraso = float(valor)
        if grupo.crawl_delay is None or atraso > grupo.crawl_delay:
            grupo.crawl_delay = atraso


def _extrair_grupos_e_sitemaps(texto: str) -> tuple[list[_GrupoRobots], list[str]]:
    limpo = texto.lstrip("\ufeff")
    grupos: list[_GrupoRobots] = []
    sitemaps: list[str] = []
    atual: _GrupoRobots | None = None
    em_cabecalho_ua = False

    for linha in limpo.splitlines():
        par = _limpar_linha(linha)
        if par is None:
            continue
        chave, valor = par
        if chave == "sitemap":
            if valor and valor not in sitemaps:
                sitemaps.append(valor)
            continue
        if chave == "user-agent":
            if not valor:
                continue
            if atual is None or not em_cabecalho_ua:
                atual = _GrupoRobots()
                grupos.append(atual)
                em_cabecalho_ua = True
            atual.agentes.append(valor.lower())
            continue
        if atual is not None:
            em_cabecalho_ua = False
            _aplicar_diretiva_regra(atual, chave, valor)

    return grupos, sitemaps


def _casa_agente(ua_declarado: str, tokens_alvo: tuple[str, ...]) -> bool:
    ua = ua_declarado.strip().lower()
    if not ua or ua == "*":
        return False
    base = ua.split("/", 1)[0].strip()
    return any(tok == base or tok.startswith(base) for tok in tokens_alvo if base)


def _fundir_grupos(escolhidos: list[_GrupoRobots]) -> tuple[tuple[RegraRobots, ...], float | None]:
    regras: list[RegraRobots] = []
    atraso: float | None = None
    for g in escolhidos:
        regras.extend(g.regras)
        if g.crawl_delay is not None and (atraso is None or g.crawl_delay > atraso):
            atraso = g.crawl_delay
    return tuple(regras), atraso


def analisa_robots(
    texto: str,
    *,
    status: int | None = 200,
    host: str = "",
    agente: str = NOME_ROBO,
) -> PoliticaRobots:
    """Constrói `PoliticaRobots` a partir do status HTTP e do corpo de `/robots.txt`."""
    if status is None or status >= _HTTP_SERVER_MIN or status == _HTTP_TOO_MANY:
        motivo = f"robots-status-{status}" if status is not None else "robots-rede"
        return PoliticaRobots(
            host=host,
            status=status,
            regras=(),
            indisponivel=True,
            motivo_indisponivel=motivo,
        )
    if _HTTP_CLIENT_MIN <= status < _HTTP_SERVER_MIN:
        return PoliticaRobots(host=host, status=status, regras=())

    grupos, sitemaps = _extrair_grupos_e_sitemaps(texto or "")
    ag_low = agente.strip().lower()
    tokens = (ag_low, *TOKENS_CASA) if ag_low and ag_low not in TOKENS_CASA else TOKENS_CASA

    especificos = [g for g in grupos if any(_casa_agente(ua, tokens) for ua in g.agentes)]
    curingas = [g for g in grupos if "*" in g.agentes]
    regras, atraso = _fundir_grupos(especificos or curingas)
    return PoliticaRobots(
        host=host,
        status=status,
        regras=regras,
        crawl_delay=atraso,
        sitemaps=tuple(sitemaps),
    )
