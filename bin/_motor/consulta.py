"""A consulta ao motor montada pelo verbo, não redigida pela cadeira (#3360, #3364; spec motor-do-conhecimento §2b).

A cadeira diz em uma frase o que precisa saber (a *necessidade*). O verbo `motor <inst> buscar`
monta com ela a lista de perguntas que a API funde por RRF:

    1. a necessidade, literal;
    2. a necessidade seguida dos rótulos do chapéu vestido («necessidade. Buscar também: rótulos»), se houver rótulos.

Se o chapéu estiver em fallback ou sem rótulos, a lista tem apenas a necessidade (1 item).
O verbo recusa com causa e jeito certo (`lint`) e nunca reescreve: não chama modelo, não traduz,
não corrige. Quem corrige é a cadeira, na chamada seguinte.

Só funções puras e leitura de arquivo; sem rede, sem banco. `bin/motor` chama; o teste mede.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

MAX_ROTULOS = 8

# --- lint ---------------------------------------------------------------------------------------
MIN_PALAVRAS = 4       # abaixo disto não há proporção a medir: «o que é RRF?» passa
PISO_FUNCIONAIS = 0.15  # proporção mínima de palavras funcionais para ter forma de frase

CAUSA_ASSUNTOS = "assuntos em uma chamada"
CAUSA_FRASE = "sem forma de frase"

# Palavras funcionais (artigos, preposições, pronomes, conjunções, auxiliares comuns). Lista fixa,
# sem dependência: o lint mede forma de frase, não entende a língua. Saco de palavras-chave quase
# não as tem; frase tem uma a cada três ou quatro palavras.
FUNCIONAIS_PT = frozenset("""
a o as os um uma uns umas de do da dos das em no na nos nas num numa por pelo pela pelos pelas
para pra com sem sobre entre até ao aos à às e ou mas que se como qual quais quem quando onde
porque porquê é são foi era ser está estão estar tem têm ter há haver vai vão fazer faz pode
podem preciso deve devem não já mais menos muito também só isso isto esse essa esses essas este
esta estes estas aquele aquela nesse nessa neste nesta seu sua seus suas meu minha nosso nossa
eu ele ela nós você me te lhe então ainda depois antes cada todo toda todos todas outro outra
""".split())

FUNCIONAIS_EN = frozenset("""
the a an of in on at to for from by with without about between into and or but if how what which
who whom when where why is are was were be been being do does did has have had can could should
would will may might must not no it its this that these those there their they he she we you your
i my our as than then so also only more most less very each every all other another
""".split())

# O que só uma das línguas tem. «a», «as», «no», «me» existem nas duas e não decidem a língua.
_SO_PT = FUNCIONAIS_PT - FUNCIONAIS_EN
_SO_EN = FUNCIONAIS_EN - FUNCIONAIS_PT

_PALAVRA = re.compile(r"[\wÀ-ÿ]+(?:['’-][\wÀ-ÿ]+)*", re.UNICODE)
_SEPARADOR_ASSUNTOS = re.compile(r";|\s\|\s")

_NUMERAL = {2: "dois", 3: "três", 4: "quatro", 5: "cinco"}


def palavras(texto: str) -> list[str]:
    return _PALAVRA.findall((texto or "").lower())


def proporcao_funcionais(texto: str) -> float:
    """Fração das palavras do texto que são funcionais em pt ou en. Sem palavra, 0."""
    ps = palavras(texto)
    if not ps:
        return 0.0
    return sum(1 for p in ps if p in FUNCIONAIS_PT or p in FUNCIONAIS_EN) / len(ps)


def _lingua(texto: str) -> str | None:
    """«pt», «en» ou None (empate ou nenhuma palavra que decida): pelas funcionais exclusivas."""
    ps = palavras(texto)
    pt = sum(1 for p in ps if p in _SO_PT)
    en = sum(1 for p in ps if p in _SO_EN)
    if pt == en:
        return None
    return "pt" if pt > en else "en"


lingua = _lingua


def lint(texto: str, *args, **kwargs) -> tuple[str, str] | None:
    """None se a necessidade passa; senão `(causa, jeito_certo)`. Nunca reescreve (#3364, #1918).

    (a) vários assuntos separados por `;` ou ` | `;
    (b) quatro ou mais palavras e proporção de funcionais abaixo do piso.
    """
    partes = [p for p in _SEPARADOR_ASSUNTOS.split(texto or "") if p.strip()]
    if len(partes) > 1:
        n = len(partes)
        return (f"{_NUMERAL.get(n, str(n))} {CAUSA_ASSUNTOS}",
                f"uma necessidade por chamada; mande {n} chamadas no mesmo lote")
    ps = palavras(texto)
    if len(ps) >= MIN_PALAVRAS and proporcao_funcionais(texto) < PISO_FUNCIONAIS:
        return (CAUSA_FRASE,
                "escreva a necessidade em frase: o que você precisa saber para o próximo ato")
    return None


def mensagem_de_recusa(causa: str, jeito: str) -> str:
    return f"consulta recusada: {causa}\n  {jeito}"


# --- montagem -----------------------------------------------------------------------------------

def montar(necessidade: str, rotulos=None, *args) -> list[str]:
    """A lista de perguntas, na ordem do contrato (#3364):
    [necessidade, necessidade + ". Buscar também: " + rótulos do chapéu].
    Se chapéu em fallback ou sem rótulos → lista de 1 item ([necessidade]).
    """
    if args:
        rotulos = args[0]
    nec = (necessidade or "").strip()
    if not nec:
        return []
    vistos: list[str] = []
    for r in (rotulos or ()):
        if isinstance(r, str) and r.strip() and r.strip() not in vistos:
            vistos.append(r.strip())
    rots = tuple(vistos[:MAX_ROTULOS])
    if not rots:
        return [nec]
    return [nec, f"{nec}. Buscar também: {', '.join(rots)}"]


def consulta(necessidade: str, chapeu: str | None = None, rotulos=None, *,
             lint_desligado: bool = False, **kwargs) -> dict:
    """O bloco `consulta` do corpo da busca: o que a API valida e grava no evento (#3364)."""
    nec = (necessidade or "").strip()
    vistos: list[str] = []
    for r in (rotulos or ()):
        if isinstance(r, str) and r.strip() and r.strip() not in vistos:
            vistos.append(r.strip())
    rots = vistos[:MAX_ROTULOS]
    bloco = {
        "necessidade": nec,
        "chapeu": chapeu or None,
        "rotulos": rots,
        "perguntas": montar(nec, rots),
    }
    if lint_desligado:
        bloco["lint"] = "desligado"
    return bloco


# --- chapéu -------------------------------------------------------------------------------------

def _dir_abertura(raiz: str | os.PathLike | None = None) -> Path:
    """Onde mora rotas-chapeu.json: a abertura publicada, como o roteador (`bin/_expediente/rotear`)."""
    if raiz:
        return Path(raiz)
    morada = os.environ.get("PF_ABERTURA_DIR")
    if morada:
        return Path(morada) / "current" / "abertura"
    import raizes  # lib/ já está no sys.path de bin/motor
    return raizes.instancia() / "var" / "abertura-publicada" / "current" / "abertura"


def chapeu_vestido(ambiente=None) -> str | None:
    """PF_CHAPEU, ou None no fallback do roteador (vazio ou «-»)."""
    v = ((ambiente if ambiente is not None else os.environ).get("PF_CHAPEU") or "").strip()
    return None if v in ("", "-") else v


def rotulos_do_chapeu(cadeira: str | None, chapeu: str | None, raiz=None) -> tuple[str, ...]:
    """Os primeiros MAX_ROTULOS rótulos do chapéu da cadeira em rotas-chapeu.json, sem repetir.

    Sem chapéu, sem cadeira, sem arquivo ou chapéu fora da tabela: vazio (a montagem sai sem o
    segundo item e o bloco declara `chapeu: null` ou `rotulos: []`)."""
    if not chapeu or not cadeira or cadeira == "-":
        return ()
    try:
        with open(_dir_abertura(raiz) / "rotas-chapeu.json", encoding="utf-8") as f:
            tabela = json.load(f)
        brutos = tabela.get(cadeira, {}).get(chapeu, [])
    except (OSError, ValueError, AttributeError):
        return ()
    vistos: list[str] = []
    for r in brutos if isinstance(brutos, list) else []:
        if isinstance(r, str) and r.strip() and r.strip() not in vistos:
            vistos.append(r.strip())
    return tuple(vistos[:MAX_ROTULOS])
