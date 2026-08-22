"""Cadeira: a unica traducao entre o slug do org, o sufixo do harness e o MXID.

Existe porque a mesma cadeira tem tres formas em uso, e nenhuma e derivavel das
outras por regra fixa:

  slug do org        claudinho-TI, claudinha-gestao-estrategica
  sufixo do harness  TI, gestao-estrategica   (abertura/<X>/persona.md)
  localpart Matrix   _pf_ti, _pf_gestao-estrategica   (minusculo, exigencia do Synapse)

A caixa do sufixo nao segue regra: `TI` e `IA` sao maiusculas, `produto` e
`seguranca` nao. Medido em 15/08: `monta-sessao ti` falha, `monta-sessao TI` passa.
Por isso a caixa NAO se calcula — se le do nome do arquivo de persona, que e a fonte.
Cadeira nova entra sozinha, sem editar este arquivo.

Fonte: platafirma-harness/abertura/<sufixo>/. A raiz sai de PF_RAIZ, ou do
default do host. No container da recepcao, abertura/ entra por bind mount ro.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PREFIXO_BOT = "_pf"
_PREFIXOS_DE_SLUG = ("claudinho-", "claudinha-")
_NAO_SAO_CADEIRA = {"TEMPLATE", "jaiminho", "jaiminho-fabrica", "osint", "fabrica", "EXTERNO"}

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


def _raiz_personas() -> Path:
    raiz = os.environ.get("PF_RAIZ", "/home/claudinho/AI")
    return Path(raiz) / "platafirma-harness" / "abertura"


def cadeiras() -> list[str]:
    """Sufixos canonicos, na caixa em que os arquivos de persona os escrevem.

    Ausencia se declara: diretorio inexistente e erro, nao lista vazia.
    """
    dir_abertura = _raiz_personas()
    if not dir_abertura.is_dir():
        raise FileNotFoundError(
            f"diretorio de abertura nao encontrado: {dir_abertura} "
            "(defina PF_RAIZ, ou monte abertura/ no container)"
        )
    achados = [
        p.name for p in dir_abertura.iterdir()
        if p.is_dir() and p.name not in _NAO_SAO_CADEIRA
    ]
    return sorted(achados)


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
        if (dir_personas / nome / "persona.md").is_file()
    ]
    return sorted(achados)


def atores() -> list[str]:
    """O roster da SUPERFICIE de conversa: cadeiras + participantes.

    E este o conjunto que ganha MXID, sala com o dono e giro — nao o do org. Quem
    decide roteamento, voto ou remit continua chamando `cadeiras()`; quem opera a
    conversa chama esta. Ter duas listas com nomes parecidos e o risco conhecido, e
    o corte esta escrito no nome: cadeira e vinculo, ator e porta.
    """
    return sorted(cadeiras() + participantes())


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
        # Participante nao e claudinho: o proprio nome e o slug, e a linha 1 da
        # persona dele nao carrega prefixo nenhum. Cair no regex abaixo devolveria
        # None, e quem chama trataria isso como "ator sem slug" — que e ausencia,
        # nao a resposta certa.
        return sufixo
    arq = _raiz_personas() / sufixo / "persona.md"
    try:
        primeira = arq.read_text(errors="replace").split("\n", 1)[0]
    except OSError:
        return None
    achado = re.search(r"\b(claudinh[oa]-[A-Za-z0-9-]+)", primeira)
    return achado.group(1) if achado else None


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
