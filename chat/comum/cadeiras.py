"""Cadeira: a unica traducao entre o slug do org, o sufixo do harness e o MXID.

Existe porque a mesma cadeira tem tres formas em uso, e nenhuma e derivavel das
outras por regra fixa:

  slug do org        claudinho-TI, claudinha-gestao-estrategica
  sufixo do harness  TI, gestao-estrategica   (abertura/<X>/persona.md)
  localpart Matrix   _pf_ti, _pf_gestao-estrategica   (minusculo, exigencia do Synapse)

A caixa do sufixo nao segue regra: `TI` e `IA` sao maiusculas, `produto` e
`seguranca` nao. Por isso o case NAO se calcula — se le do LEDGER DE VINCULO
(arq:0073), que carrega o slug canonico (`claudinho-TI`). A persona do form novo poe
o alias na linha 1, entao ela nao serve mais de fonte do prefixo. Cadeira nova entra
sozinha, sem editar este arquivo.

Fonte do case e do prefixo: platafirma-harness/registro/eventos-org.jsonl.
Fonte da persona do ator: abertura/<persona>/persona.md, onde a persona
sai de _PERSONA_DO_ATOR (ator != persona: jaiminho monta `fabrica`).
A raiz sai de PF_RAIZ, ou do default do host; no container da recepcao ambos entram
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
# Tres eixos independentes, e este mapa e a unica ponte entre dois deles:
#   conta    o usuario do SO onde o ator roda — o PERIMETRO de segregacao, canonico
#            (conta != persona; regra de conta como segregacao vale em todo lugar serio).
#   provider a entidade por tras da conta, e o nome AFETIVO do ator: claudinho e o
#            Claude, jaiminho e o Antigravity, gepeto sera o ChatGPT. E o que o dono
#            ve na sala e o que o MXID (_pf_<ator>) carrega — identidade permanente.
#   persona  o que monta_sessao carrega — abertura/<persona>/persona.md.
#
# O ator jaiminho monta a persona `fabrica` (roteador de linha: devops/blueteam/
# front-end). NAO ha mais "persona jaiminho": o provider e uma fabrica com outro
# provider em outra conta. Ator sem entrada aqui monta a persona homonima (o caso
# das cadeiras claudinho-*, onde ator e persona coincidem).
_PERSONA_DO_ATOR = {
    "jaiminho": "fabrica",
    "jaiminho-fabrica": "fabrica",
}


def _raiz_personas() -> Path:
    raiz = os.environ.get("PF_RAIZ", "/home/claudinho/AI")
    return Path(raiz) / "platafirma-harness" / "abertura"


def _ledger() -> Path:
    raiz = os.environ.get("PF_RAIZ", "/home/claudinho/AI")
    return Path(raiz) / "platafirma-harness" / "registro" / "eventos-org.jsonl"


def _sem_prefixo(slug: str) -> str:
    for pref in _PREFIXOS_DE_SLUG:
        if slug.startswith(pref):
            return slug[len(pref):]
    return slug


def _cadeiras_do_ledger() -> dict:
    """{sufixo_minusculo: slug_canonico} do ledger de vinculo. Fonte do case e do
    prefixo (arq:0073). Ausencia se declara: ledger ausente e erro, nao dict vazio."""
    p = _ledger()
    if not p.is_file():
        raise FileNotFoundError(
            f"ledger de vinculo nao encontrado: {p} (defina PF_RAIZ, ou monte registro/)")
    mapa: dict = {}
    with p.open(encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                slug = (json.loads(linha).get("cadeira") or "").strip()
            except ValueError:
                continue
            if slug:
                mapa[_sem_prefixo(slug).lower()] = slug
    return mapa


def _dobra(txt: str) -> str:
    """minusculas sem acento: 'Joao' e 'João' sao a mesma pessoa digitada de dois
    jeitos, e a resolucao de nome humano nao pode depender de o dono acertar o til."""
    n = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in n if not unicodedata.combining(c)).lower().strip()


def _alias_do_ledger() -> dict:
    """{forma_dobrada_do_nome_humano: sufixo_canonico} do ledger de vinculo.

    A entrada que faltava a `sufixo_canonico`: o nome AFETIVO do ator
    ('Oswaldo Aranha' -> 'TI'), que ate aqui so o organograma de display (#2438,
    `_mapa_alias_cadeiras`) conhecia. Mesma fonte, mesmo PROVIMENTO.alias — aqui a
    leitura e invertida (nome -> sufixo) porque quem RESOLVE parte do nome.

    Casa duas formas por alias: o nome inteiro ('oswaldo aranha') e o primeiro token
    ('oswaldo'). O primeiro token SO entra se for unico entre todos os aliases:
    homonimo de primeiro nome exige o nome inteiro, porque casar a cadeira errada e
    pior que nao casar. Alias ausente (engenharia) nao entra. Ledger ausente devolve
    {} em vez de erro: alias e a ULTIMA tentativa de `sufixo_canonico`, e sua falta
    nao pode derrubar a resolucao das formas que nao dependem dela.
    """
    p = _ledger()
    if not p.is_file():
        return {}
    inteiros: dict = {}
    primeiros: dict = {}
    ambiguos: set = set()
    with p.open(encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                ev = json.loads(linha)
            except ValueError:
                continue
            if ev.get("tipo") != "PROVIMENTO":
                continue
            slug = (ev.get("cadeira") or "").strip()
            alias = (ev.get("alias") or "").strip()
            if not slug or not alias:
                continue
            suf = _sem_prefixo(slug)
            inteiros[_dobra(alias)] = suf
            partes = [t for t in re.split(r"[\s-]+", alias) if t]
            if partes:
                tok = _dobra(partes[0])
                if tok in primeiros and primeiros[tok] != suf:
                    ambiguos.add(tok)
                primeiros[tok] = suf
    for tok in ambiguos:
        primeiros.pop(tok, None)
    # inteiro vence primeiro-token quando as duas formas coincidem.
    return {**primeiros, **inteiros}


def cadeiras() -> list[str]:
    """Sufixos canonicos, no case do ledger de vinculo (`TI`/`IA` maiusculos), sem
    participantes nem nao-cadeiras. Ausencia se declara: ledger ausente e erro.
    """
    fora = _NAO_SAO_CADEIRA | _SAO_PARTICIPANTE
    sufs = [_sem_prefixo(slug) for slug in _cadeiras_do_ledger().values()]
    return sorted(s for s in sufs if s not in fora)


def participantes() -> list[str]:
    """Sufixos dos participantes que tem persona no harness.

    Mesma fonte das cadeiras (abertura/<cadeira>/persona.md) e mesma regra de ausencia:
    participante declarado em `_SAO_PARTICIPANTE` sem arquivo de persona NAO entra —
    sem persona nao ha identidade a provisionar, e inventar uma aqui daria MXID a
    quem o rito de admissao nao admitiu.
    """
    dir_personas = _raiz_personas()
    if not dir_personas.is_dir():
        raise FileNotFoundError(
            f"diretorio de personas nao encontrado: {dir_personas} "
            "(defina PF_RAIZ, ou monte personas/ no container)"
        )
    achados = [
        nome for nome in _SAO_PARTICIPANTE
        if (dir_personas / _PERSONA_DO_ATOR.get(nome, nome) / "persona.md").is_file()
    ]
    return sorted(achados)


def atores_internos() -> list[str]:
    """Sufixos dos atores internos nao-cadeira que tem persona no harness.

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
    """O roster da SUPERFICIE de conversa: cadeiras + participantes.

    E este o conjunto que ganha MXID, sala com o dono e giro — nao o do org. Quem
    decide roteamento, voto ou remit continua chamando `cadeiras()`; quem opera a
    conversa chama esta. Ter duas listas com nomes parecidos e o risco conhecido, e
    o corte esta escrito no nome: cadeira e vinculo, ator e porta.
    """
    return sorted(cadeiras() + participantes() + atores_internos())


def eh_participante(nome: str) -> bool:
    """O ator resolvido e participante, e nao cadeira? Fonte da rota de motor.

    O verbo `chat` ramifica por aqui: cadeira gira por `monta-sessao` + Claude Code
    no cwd dela, participante gira pelo verbo proprio dele. Sem esta pergunta a
    escolha de motor seria implicita e unica, que e o estado que o card 464 corrige.
    """
    canonico = sufixo_canonico(nome)
    return canonico is not None and canonico in _SAO_PARTICIPANTE


def sufixo_canonico(nome: str) -> str | None:
    """Qualquer forma do ator -> o sufixo na caixa canonica. None se nao existe.

    Aceita as tres entradas, e por isso quem chama nao prepara nada antes:
      "claudinho-TI"                -> "TI"    (slug do org, com prefixo)
      "ti"                          -> "TI"    (sufixo em qualquer caixa)
      "_pf_ti"                      -> "TI"    (localpart do Matrix)
      "@_pf_ti:chat.platafirma.org" -> "TI"    (MXID inteiro)
    """
    if not nome:
        return None
    bruto = nome.strip()

    if bruto.startswith("@"):                      # MXID inteiro -> localpart
        bruto = bruto[1:].split(":", 1)[0]

    if bruto.lower().startswith(PREFIXO_BOT):      # localpart -> sufixo cru
        bruto = bruto[len(PREFIXO_BOT):].lstrip("_-")

    for prefixo in _PREFIXOS_DE_SLUG:              # slug do org -> sufixo cru
        if bruto.lower().startswith(prefixo):
            bruto = bruto[len(prefixo):]
            break

    if not bruto:
        return None
    alvo = bruto.lower()
    for canonico in atores():
        if canonico.lower() == alvo:
            return canonico
    # Ultima forma: nome humano (alias do ledger). 'Oswaldo'/'Oswaldo Aranha' -> 'TI'.
    # So chega aqui quem nao casou como sufixo/slug/MXID, entao um sufixo real sempre
    # vence o alias — o fallback nunca sequestra uma forma ja valida.
    suf = _alias_do_ledger().get(_dobra(bruto))
    if suf:
        return suf
    return None


def slug_da_cadeira(nome: str) -> str | None:
    """Sufixo do harness -> slug do org (`TI` -> `claudinho-TI`). None se nao ha.

    A caixa da fila, `PF_CADEIRA`, o arquivo de persona e o Project sao chaveados
    pelo SLUG; `monta-sessao` e `--cadeira` querem o SUFIXO. As duas formas nao se
    calculam uma da outra — `persona-IA.md` nao diz se e claudinho- ou claudinha-,
    e o prefixo nao segue regra de genero derivavel do sufixo.

    A fonte e a linha 1 da persona, mesma de `bin/descansar` e do `monta-sessao`.
    Nao e o nome do arquivo, e nao e tabela embutida aqui: cadeira nova entra
    sozinha, e uma segunda tabela envelheceria em silencio.

    Medido em 15/08, e a razao de esta funcao existir: o giro do chat exportava
    `PF_CADEIRA=TI`, e `mesa`, `fila` e `tarefas` chaveiam pelo slug — tudo o que
    a fita escrevia ia para `mem:TI:*`, uma memoria paralela que nenhuma outra
    sessao da cadeira enxergava.
    """
    sufixo = sufixo_canonico(nome)
    if sufixo is None:
        return None
    if sufixo in _SAO_PARTICIPANTE:
        # Participante nao e claudinho: o slug e o da PERSONA que ele monta
        # (jaiminho -> fabrica), nao o nome do ator. PF_CADEIRA, o arquivo de
        # persona e o Project sao chaveados pela persona; chavear pelo ator daria
        # a mem:jaiminho:* paralela que esta funcao existe para evitar.
        return _PERSONA_DO_ATOR.get(sufixo, sufixo)
    if sufixo in _ATORES_INTERNOS:
        # Ator interno nao esta no ledger de vinculo (nao e cadeira do org), entao
        # o slug NAO sai de _cadeiras_do_ledger — sairia None e o giro do bin/chat
        # nao teria cwd/PF_CADEIRA. O slug e a propria persona homonima que ele
        # monta (fabrica -> fabrica): mesma chave de mesa/fila/Project das cadeiras,
        # sem prefixo claudinho-, porque fabrica e persona fungivel, nao vinculo.
        return sufixo
    # Fonte do prefixo e o LEDGER, nao a linha 1 da persona (form novo poe alias la).
    return _cadeiras_do_ledger().get(sufixo.lower())


def localpart_da_cadeira(nome: str, prefixo: str = PREFIXO_BOT) -> str | None:
    """Qualquer forma da cadeira -> o localpart do Matrix. None se nao existe.

      "claudinho-TI"        -> "_pf_ti"
      "gestao-estrategica"  -> "_pf_gestao-estrategica"

    Minusculo porque o Synapse recusa localpart com maiuscula, e porque o MXID vai
    assado em todo evento: e identidade permanente, nao rotulo de tela. O nome de
    exibicao e o alias do org, e esse sim se troca depois.
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
    """O MXID e de um ator NOSSO — cadeira ou participante? O bot nao conta.

    E esta, e nao `eh_de_cadeira`, que a recepcao usa para aprender de quem e uma
    sala: a sala do Jaiminho tem de ser aprendida como qualquer outra, senao ela
    fica muda para sempre e o dono nao tem porta com ele.
    """
    if not mxid.startswith(f"@{prefixo}") or not mxid.endswith(f":{dominio}"):
        return False
    return sufixo_canonico(mxid) is not None


def eh_de_cadeira(mxid: str, dominio: str, prefixo: str = PREFIXO_BOT) -> bool:
    """O MXID e de uma CADEIRA nossa? Participante responde False.

    Sentido estrito de proposito: quem pergunta isto esta perguntando sobre vinculo
    no org (roteamento, voto), e nesse plano participante nao e cadeira. Para a
    mecanica da sala a pergunta certa e `eh_de_ator`.
    """
    if not eh_de_ator(mxid, dominio, prefixo):
        return False
    return sufixo_canonico(mxid) in cadeiras()


_LOCALPART_VALIDO = re.compile(r"^[a-z0-9._=\-/+]+$")


def valida_localpart(localpart: str) -> bool:
    """A gramatica de localpart do Matrix, para falhar aqui e nao no Synapse."""
    return bool(_LOCALPART_VALIDO.match(localpart))
