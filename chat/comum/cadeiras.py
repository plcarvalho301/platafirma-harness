"""Cadeira: a unica traducao entre o slug do org, o sufixo do harness e o MXID.

Fonte viva unica: a arvore `abertura/<cadeira>/`, HEAD do working tree (arq:0073 §1,
estado vivo por arq:0074). O slug e o nome do diretorio, MINUSCULO PURO, sem prefixo
`claudinho-`/`claudinha-` e sem alias (arq:0073 §2). Cadeira nova entra sozinha, criando
o diretorio `abertura/<slug>/persona.md`; este arquivo nao se edita.

  slug do org / sufixo   ti, ia, gestao-estrategica   (== nome do diretorio em abertura/)
  localpart Matrix       _pf_ti, _pf_gestao-estrategica   (minusculo, exigencia do Synapse)

INCIDENTE (ordem do dono): o ledger de vinculo (`registro/eventos-org.jsonl`) e
HISTORICO append-only, para consulta — NENHUM codigo vivo o le para resolver
identidade. O expurgo do prefixo `claudinho-` do slug (ordem anterior do dono) ficou
sem conformar: o ledger guardava a forma antiga (`claudinho-IA`), o codigo vivo a lia,
e o slug fossil resolvia como vigente. A fonte viva agora e a arvore, so ela.

Fonte da persona do ator: abertura/<persona>/persona.md, onde a persona
sai de _PERSONA_DO_ATOR (ator != persona: jaiminho monta `fabrica`).
Fonte do alias humano: abertura/aliases.json (mapa slug->nome afetivo, dado vivo).
A raiz sai de PF_RAIZ, ou do default do host; no container da recepcao ela entra
por bind mount ro.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

PREFIXO_BOT = "_pf"
_PREFIXOS_DE_SLUG = ("claudinho-", "claudinha-")
_NAO_SAO_CADEIRA = {"TEMPLATE", "jaiminho", "jaiminho-fabrica", "osint", "EXTERNO"}

# PARTICIPANTE — quem tem porta com o dono sem ocupar cadeira (colaborador externo,
# assessor, fornecedor). Rito e estatuto em platafirma-arquitetura/docs/
# admissao-de-participante.md; quem declara o vinculo e RH, no org canonico.
#
# Esta lista NAO os promove a cadeira, e a diferenca e o card inteiro: cadeira tem
# roteamento entre cadeiras e voto, participante nao. `cadeiras()` segue excluindo
# jaiminho de proposito — quem pergunta "quem sao as cadeiras" continua recebendo a
# resposta certa. O que muda e que a SUPERFICIE de conversa passa a ter um roster
# proprio (`atores()`), maior que o do org: o dono fala com quem tem porta com ele.
_SAO_PARTICIPANTE = {"jaiminho", "jaiminho-fabrica"}

# ATOR INTERNO nao-cadeira — ganha MXID, sala com o dono e giro, mas NAO e cadeira
# do org (nao vota, nao tem head, nao entra em roteamento) e NAO e participante de
# motor externo. O motor dele e o mesmo das cadeiras: Claude Code no cwd, conta
# claudinho. E este terceiro balde que o modelo N-provider da fabrica exige: a
# `fabrica` e uma PERSONA fungivel, encarnada uma vez por conta/provider. Esta e a
# encarnacao `claude`/conta-claudinho; a encarnacao `agy` ja existe como o
# participante `jaiminho-fabrica`. Generalizar provider->client e o card aberto
# junto com esta fatia — aqui ha UMA encarnacao, sem a tabela generica ainda.
#
# Fora de _SAO_PARTICIPANTE de proposito: `eh_participante('fabrica')` e False, e
# por isso o giro cai no ramo MotorClaudeCode do bin/chat, nao no ramo do verbo
# externo. Monta a persona homonima (abertura/fabrica/persona.md), que ja existe.
_ATORES_INTERNOS = {"fabrica"}

# ATOR de superficie -> PERSONA que a sessao dele monta.
#
# O ator jaiminho monta a persona `fabrica` (roteador de linha: devops/blueteam/
# front-end). NAO ha mais "persona jaiminho": o provider e uma fabrica com outro
# provider em outra conta. Ator sem entrada aqui monta a persona homonima (o caso
# das cadeiras, onde ator e persona coincidem).
_PERSONA_DO_ATOR = {
    "jaiminho": "fabrica",
    "jaiminho-fabrica": "fabrica",
}


def _raiz_personas() -> Path:
    raiz = os.environ.get("PF_RAIZ", "/home/claudinho/AI")
    return Path(raiz) / "platafirma-harness" / "abertura"


def _sem_prefixo(slug: str) -> str:
    for pref in _PREFIXOS_DE_SLUG:
        if slug.startswith(pref):
            return slug[len(pref):]
    return slug


def _slugs_da_arvore() -> set[str]:
    """Os slugs vivos: todo diretorio de `abertura/`.

    Fonte viva unica (arq:0073 §1). Substitui a leitura do ledger de vinculo: o slug
    e o nome do diretorio, minusculo puro, e cadeira sem persona.md redigida nao entra
    (mesma regra de ausencia que participantes()/atores_internos() ja aplicavam).
    Diretorio ausente e erro declarado, nunca set vazio silencioso.
    """
    dir_personas = _raiz_personas()
    if not dir_personas.is_dir():
        raise FileNotFoundError(
            f"diretorio de personas nao encontrado: {dir_personas} "
            "(defina PF_RAIZ, ou monte abertura/ no container)"
        )
    # Existência da cadeira é o DIRETÓRIO (arq:0073 §7.5: criada mas não redigida
    # abre com peças indisponíveis, não some do roster). A peça persona é quem fica
    # indisponível quando falta persona.md — não a cadeira.
    return {
        d.name
        for d in dir_personas.iterdir()
        if d.is_dir()
    }


def _dobra(txt: str) -> str:
    """minusculas sem acento: 'Joao' e 'João' sao a mesma pessoa digitada de dois
    jeitos, e a resolucao de nome humano nao pode depender de o dono acertar o til."""
    n = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in n if not unicodedata.combining(c)).lower().strip()


def _aliases() -> dict:
    """{forma_dobrada_do_nome_humano: slug} de abertura/aliases.json.

    Dado vivo na arvore (nao mais o ledger). Casa duas formas por alias: o nome
    inteiro ('oswaldo aranha') e o primeiro token ('oswaldo'). O primeiro token SO
    entra se for unico entre todos os aliases: homonimo de primeiro nome exige o nome
    inteiro, porque casar a cadeira errada e pior que nao casar. Arquivo ausente
    devolve {}: alias e a ULTIMA tentativa de `sufixo_canonico`, e sua falta nao pode
    derrubar a resolucao das formas que nao dependem dela.
    """
    p = _raiz_personas() / "aliases.json"
    if not p.is_file():
        return {}
    try:
        mapa = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    inteiros: dict = {}
    primeiros: dict = {}
    ambiguos: set = set()
    for slug, alias in mapa.items():
        if not slug or not alias:
            continue
        inteiros[_dobra(alias)] = slug
        partes = [t for t in re.split(r"[\s-]+", alias) if t]
        if partes:
            tok = _dobra(partes[0])
            if tok in primeiros and primeiros[tok] != slug:
                ambiguos.add(tok)
            primeiros[tok] = slug
    for tok in ambiguos:
        primeiros.pop(tok, None)
    # inteiro vence primeiro-token quando as duas formas coincidem.
    return {**primeiros, **inteiros}


def cadeiras() -> list[str]:
    """Slugs vivos (minusculo puro), sem participantes nem nao-cadeiras.
    Ausencia se declara: diretorio de personas ausente e erro.
    """
    fora = _NAO_SAO_CADEIRA | _SAO_PARTICIPANTE | _ATORES_INTERNOS
    return sorted(s for s in _slugs_da_arvore() if s not in fora)


def participantes() -> list[str]:
    """Slugs dos participantes que tem persona no harness.

    Mesma fonte das cadeiras (abertura/<cadeira>/persona.md) e mesma regra de ausencia:
    participante declarado em `_SAO_PARTICIPANTE` sem arquivo de persona NAO entra.
    """
    dir_personas = _raiz_personas()
    if not dir_personas.is_dir():
        raise FileNotFoundError(
            f"diretorio de personas nao encontrado: {dir_personas} "
            "(defina PF_RAIZ, ou monte personas/ no container)"
        )
    return sorted(
        nome for nome in _SAO_PARTICIPANTE
        if (dir_personas / _PERSONA_DO_ATOR.get(nome, nome) / "persona.md").is_file()
    )


def atores_internos() -> list[str]:
    """Slugs dos atores internos nao-cadeira que tem persona no harness.
    Mesma regra de ausencia das outras duas listas: declarado sem persona NAO entra.
    """
    dir_personas = _raiz_personas()
    if not dir_personas.is_dir():
        raise FileNotFoundError(
            f"diretorio de personas nao encontrado: {dir_personas} "
            "(defina PF_RAIZ, ou monte personas/ no container)"
        )
    return sorted(
        nome for nome in _ATORES_INTERNOS
        if (dir_personas / nome / "persona.md").is_file()
    )


def atores() -> list[str]:
    """O roster da SUPERFICIE de conversa: cadeiras + participantes + atores internos.

    E este o conjunto que ganha MXID, sala com o dono e giro — nao o do org. Quem
    decide roteamento, voto ou remit continua chamando `cadeiras()`; quem opera a
    conversa chama esta.
    """
    return sorted(cadeiras() + participantes() + atores_internos())


def eh_participante(nome: str) -> bool:
    """O ator resolvido e participante, e nao cadeira? Fonte da rota de motor."""
    canonico = sufixo_canonico(nome)
    return canonico is not None and canonico in _SAO_PARTICIPANTE


def sufixo_canonico(nome: str) -> str | None:
    """Qualquer forma do ator -> o slug vivo (minusculo puro). None se nao existe.

    Aceita as entradas, e por isso quem chama nao prepara nada antes:
      "ti"                          -> "ti"    (slug, ja canonico)
      "TI"                          -> "ti"    (case fossil de digitacao, dobrado)
      "claudinho-ti"                -> "ti"    (prefixo fossil, descartado na entrada)
      "_pf_ti"                      -> "ti"    (localpart do Matrix)
      "@_pf_ti:chat.platafirma.org" -> "ti"    (MXID inteiro)

    O prefixo `claudinho-`/`claudinha-` na ENTRADA e tolerado e descartado (formas
    fosseis ainda em transito nao devem quebrar o roteamento), mas nunca e produzido
    de volta: o slug canonico e sempre a forma pura da arvore.
    """
    if not nome:
        return None
    bruto = nome.strip()

    if bruto.startswith("@"):                      # MXID inteiro -> localpart
        bruto = bruto[1:].split(":", 1)[0]

    if bruto.lower().startswith(PREFIXO_BOT):      # localpart -> sufixo cru
        bruto = bruto[len(PREFIXO_BOT):].lstrip("_-")

    bruto = _sem_prefixo(bruto.lower())            # prefixo fossil de slug, descartado

    if not bruto:
        return None
    for canonico in atores():
        if canonico.lower() == bruto:
            return canonico
    # Ultima forma: nome humano (alias vivo). 'Oswaldo'/'Oswaldo Aranha' -> 'ti'.
    # So chega aqui quem nao casou como slug/localpart/MXID, entao um slug real sempre
    # vence o alias — o fallback nunca sequestra uma forma ja valida.
    return _aliases().get(_dobra(bruto)) or None


def slug_da_cadeira(nome: str) -> str | None:
    """Qualquer forma -> o slug canonico (== sufixo). None se nao ha.

    Depois do expurgo do prefixo (ordem do dono), o slug do org e o proprio sufixo
    minusculo: nao ha mais `claudinho-<cadeira>`. Esta funcao sobrevive como a ponte
    para participante e ator interno, cujo slug e o da PERSONA que montam, nao o nome
    do ator (jaiminho -> fabrica).

    A caixa da fila, `PF_CADEIRA`, o arquivo de persona e o Project sao chaveados por
    este slug; `monta-sessao` e `--cadeira` querem a mesma forma. Uma forma so.
    """
    sufixo = sufixo_canonico(nome)
    if sufixo is None:
        return None
    # Participante e ator interno: o slug e a PERSONA que montam (jaiminho -> fabrica),
    # nao o nome do ator, para nao criar mem:jaiminho:* paralela. Cadeira: slug == sufixo.
    return _PERSONA_DO_ATOR.get(sufixo, sufixo)


def localpart_da_cadeira(nome: str, prefixo: str = PREFIXO_BOT) -> str | None:
    """Qualquer forma da cadeira -> o localpart do Matrix. None se nao existe.

      "ti"                  -> "_pf_ti"
      "gestao-estrategica"  -> "_pf_gestao-estrategica"

    Minusculo porque o Synapse recusa localpart com maiuscula. Como o slug ja e
    minusculo puro, o localpart e o slug prefixado — sem dobra de caixa a fazer.
    """
    canonico = sufixo_canonico(nome)
    if canonico is None:
        return None
    return f"{prefixo}_{canonico.lower()}"


def mxid_da_cadeira(nome: str, dominio: str, prefixo: str = PREFIXO_BOT) -> str | None:
    """Qualquer forma da cadeira -> o MXID completo. None se nao existe."""
    localpart = localpart_da_cadeira(nome, prefixo)
    if localpart is None:
        return None
    return f"@{localpart}:{dominio}"


def eh_de_ator(mxid: str, dominio: str, prefixo: str = PREFIXO_BOT) -> bool:
    """O MXID e de um ator NOSSO — cadeira ou participante? O bot nao conta."""
    if not mxid.startswith(f"@{prefixo}") or not mxid.endswith(f":{dominio}"):
        return False
    return sufixo_canonico(mxid) is not None


def eh_de_cadeira(mxid: str, dominio: str, prefixo: str = PREFIXO_BOT) -> bool:
    """O MXID e de uma CADEIRA nossa? Participante responde False."""
    if not eh_de_ator(mxid, dominio, prefixo):
        return False
    return sufixo_canonico(mxid) in cadeiras()


_LOCALPART_VALIDO = re.compile(r"^[a-z0-9._=\-/+]+$")


def valida_localpart(localpart: str) -> bool:
    """A gramatica de localpart do Matrix, para falhar aqui e nao no Synapse."""
    return bool(_LOCALPART_VALIDO.match(localpart))
