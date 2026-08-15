"""Cadeira: a unica traducao entre o slug do org, o sufixo do harness e o MXID.

Existe porque a mesma cadeira tem tres formas em uso, e nenhuma e derivavel das
outras por regra fixa:

  slug do org        claudinho-TI, claudinha-gestao-estrategica
  sufixo do harness  TI, gestao-estrategica   (personas/persona-<X>.md, tool-manifest/<X>.md)
  localpart Matrix   _pf_ti, _pf_gestao-estrategica   (minusculo, exigencia do Synapse)

A caixa do sufixo nao segue regra: `TI` e `IA` sao maiusculas, `produto` e
`seguranca` nao. Medido em 15/08: `monta-sessao ti` falha, `monta-sessao TI` passa.
Por isso a caixa NAO se calcula — se le do nome do arquivo de persona, que e a fonte.
Cadeira nova entra sozinha, sem editar este arquivo.

Fonte: platafirma-harness/personas/persona-<sufixo>.md. A raiz sai de PF_RAIZ, ou do
default do host. No container da recepcao, personas/ entra por bind mount ro.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PREFIXO_BOT = "_pf"
_PREFIXOS_DE_SLUG = ("claudinho-", "claudinha-")
_NAO_SAO_CADEIRA = {"TEMPLATE", "jaiminho", "osint", "fabrica", "EXTERNO"}


def _raiz_personas() -> Path:
    raiz = os.environ.get("PF_RAIZ", "/home/claudinho/AI")
    return Path(raiz) / "platafirma-harness" / "personas"


def cadeiras() -> list[str]:
    """Sufixos canonicos, na caixa em que os arquivos de persona os escrevem.

    Ausencia se declara: diretorio inexistente e erro, nao lista vazia.
    """
    dir_personas = _raiz_personas()
    if not dir_personas.is_dir():
        raise FileNotFoundError(
            f"diretorio de personas nao encontrado: {dir_personas} "
            "(defina PF_RAIZ, ou monte personas/ no container)"
        )
    achados = [
        arq.stem[len("persona-"):]
        for arq in dir_personas.glob("persona-*.md")
        if arq.stem[len("persona-"):] and arq.stem[len("persona-"):] not in _NAO_SAO_CADEIRA
    ]
    return sorted(achados)


def sufixo_canonico(nome: str) -> str | None:
    """Qualquer forma da cadeira -> o sufixo na caixa canonica. None se nao existe.

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
    for canonico in cadeiras():
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
    arq = _raiz_personas() / f"persona-{sufixo}.md"
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


def eh_de_cadeira(mxid: str, dominio: str, prefixo: str = PREFIXO_BOT) -> bool:
    """O MXID e de uma cadeira NOSSA neste dominio? O bot da recepcao nao conta."""
    if not mxid.startswith(f"@{prefixo}") or not mxid.endswith(f":{dominio}"):
        return False
    return sufixo_canonico(mxid) is not None


_LOCALPART_VALIDO = re.compile(r"^[a-z0-9._=\-/+]+$")


def valida_localpart(localpart: str) -> bool:
    """A gramatica de localpart do Matrix, para falhar aqui e nao no Synapse."""
    return bool(_LOCALPART_VALIDO.match(localpart))
