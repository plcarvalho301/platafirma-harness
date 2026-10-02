"""lista — resolucao de lista de verificacao via acervo da casa.

O acervo serve documento de casa em markdown (`acervo ler casa <especie> <chave>`):
primeira linha de situacao («<forca> · <vigencia> — <especie> <chave> · <titulo>»),
depois o corpo do documento. A lista se le desse formato, que e o de todo o acervo:
cabecalho de metadado (`Rev:`, `Dono:`...) e os criterios em tabela markdown.

Nada aqui e especifico de uma lista: as colunas se reconhecem pelo nome no cabecalho
da tabela. Classe que precisa de coluna nova acrescenta o nome em COLUNAS.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

ESPECIE = "lista-de-verificacao"

# nome da coluna no cabecalho da tabela (normalizado) -> campo do item
COLUNAS = {
    "#": "id",
    "id": "id",
    "antipadrao": "o_que_fere",
    "o que fere": "o_que_fere",
    "criterio": "o_que_fere",
    "lei da casa": "fonte",
    "deriva de": "fonte",
    "fonte": "fonte",
    "detector": "detector",
    "classe": "severidade",
    "severidade": "severidade",
    "cura": "cura",
}

_ACENTOS = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeiooouc" "AAAAEEIOOOUC")


class ListaNaoEncontrada(Exception):
    def __init__(self, chave: str, msg: str = ""):
        super().__init__(msg or f"lista de verificacao '{chave}' nao encontrada no acervo")
        self.chave = chave


def _norm(s: str) -> str:
    return s.strip().strip("*`").translate(_ACENTOS).lower()


def _celulas(linha: str) -> List[str]:
    corpo = linha.strip()
    if corpo.startswith("|"):
        corpo = corpo[1:]
    if corpo.endswith("|"):
        corpo = corpo[:-1]
    return [c.strip() for c in corpo.split("|")]


def _separador(linha: str) -> bool:
    return bool(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?", linha.strip()))


def parse_lista(texto: str) -> Dict[str, Any]:
    """Le uma lista de verificacao no formato em que o acervo a serve.

    Devolve {titulo, rev, metadados, situacao, itens}. `itens` traz um dict por linha
    de toda tabela cujo cabecalho tenha `detector` ou `severidade`/`classe`, com os
    campos de COLUNAS; celula vazia fica fora. Sem tabela reconhecida, itens = [].
    """
    linhas = texto.splitlines()
    situacao = ""
    if linhas and " — " in linhas[0] and not linhas[0].startswith("#"):
        situacao = linhas[0]
        linhas = linhas[1:]

    titulo = ""
    metadados: Dict[str, str] = {}
    for ln in linhas:
        if not titulo and ln.startswith("# "):
            titulo = ln[2:].strip()
            continue
        m = re.match(r"^([A-ZÀ-Ú][\wÀ-ú ]{0,30}):\s+(.+)$", ln)
        if m and titulo and not ln.startswith("|"):
            metadados.setdefault(_norm(m.group(1)), m.group(2).strip())
        if ln.startswith("## "):
            break

    rev: Optional[int] = None
    if "rev" in metadados:
        m = re.search(r"\d+", metadados["rev"])
        rev = int(m.group()) if m else None

    itens: List[Dict[str, str]] = []
    i = 0
    while i < len(linhas) - 1:
        cab, sep = linhas[i], linhas[i + 1]
        if cab.strip().startswith("|") and _separador(sep):
            campos = [COLUNAS.get(_norm(c)) for c in _celulas(cab)]
            if "detector" in campos or "severidade" in campos:
                j = i + 2
                while j < len(linhas) and linhas[j].strip().startswith("|"):
                    item = {}
                    for campo, valor in zip(campos, _celulas(linhas[j])):
                        if campo and valor:
                            item[campo] = valor
                    if "severidade" in item:
                        item["severidade"] = _norm(item["severidade"])
                    if item:
                        itens.append(item)
                    j += 1
                i = j
                continue
        i += 1

    # corpo inteiro: classe que le dado fora de tabela (contraponto, lista de termos) le daqui
    return {"titulo": titulo, "rev": rev, "metadados": metadados,
            "situacao": situacao, "itens": itens, "corpo": texto}


def _acervo_bin() -> str:
    # PF_LINT_ACERVO: o acervo que o lint consulta. Os testes de contrato apontam um
    # acervo de fixture aqui, para nao depender do que o acervo real serve hoje.
    sob = os.environ.get("PF_LINT_ACERVO")
    if sob:
        return sob
    harness_raiz = Path(__file__).resolve().parent.parent.parent
    local = harness_raiz / "bin" / "acervo"
    return str(local) if local.exists() else "acervo"


def resolver_lista(chave: str, especies: tuple = (ESPECIE,)) -> Optional[Dict[str, Any]]:
    """Obtem a regua `chave` do acervo, ja lida, na primeira de `especies` que a serve.

    Regua que mora no acervo como `padrao` (styleguide-da-wiki) le-se pelo mesmo parse.
    """
    for especie in especies:
        lista = _resolver_na_especie(chave, especie)
        if lista:
            return lista
    return None


def _resolver_na_especie(chave: str, especie: str) -> Optional[Dict[str, Any]]:
    """Obtem a lista de verificacao `chave` do acervo, ja lida.

    Devolve o dict de parse_lista acrescido de `id` (= chave), ou None se a lista nao
    esta servida, esta retirada, ou o acervo nao respondeu (o chamador sai 5).
    """
    if not chave:
        return None
    try:
        proc = subprocess.run(
            [_acervo_bin(), "ler", "casa", especie, chave],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    saida = proc.stdout.strip()
    if proc.returncode != 0 or not saida:
        return None

    # forma antiga (JSON), aceita enquanto houver quem a sirva
    if saida.startswith("{"):
        try:
            dado = json.loads(saida)
            dado.setdefault("id", chave)
            return dado
        except json.JSONDecodeError:
            pass

    lista = parse_lista(saida)
    if "retirada" in lista["situacao"].split(" — ")[0]:
        return None
    lista["id"] = chave
    if lista["rev"] is None:
        lista["rev"] = 1
    return lista
