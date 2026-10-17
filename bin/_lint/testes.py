"""testes — a linha da lista de portão (arq:0129; padrão testes).

A régua é a lista `checklist-testes` do acervo: ela diz, por critério, o antipadrão, a
severidade e a cura. Aqui mora só o detector de cada critério, escolhido pelo id da lista
(T1, T2...). Critério novo na lista sem detector aqui sai listado como «sem detector», nunca calado.

O que se lê é a lista de portão (`VERDES`) de cada subárvore de teste do repositório, pela mesma
gramática do `teste rodar` (bin/teste, `campos_da_linha`): `<arquivo> | <globs do raio> |
degrau: imagem|rodada | regressivo #<n> | quarentena #<débito> | preparo`. O tipo do teste
(contrato, integração) não tem marca na linha, e por isso nenhum critério depende dele.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable, Iterator, Optional, Tuple

from .lista import resolver_lista
from .resultado import Apontamento

CHAVE_LISTA = "checklist-testes"

DEGRAUS = ("pequeno", "imagem", "rodada")
PASTAS_FORA = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist"}

NOMEADO = re.compile(r"^([a-z][a-z-]*):")


class Linha:
    """Uma linha da lista de portão, lida pela gramática do `teste`."""
    __slots__ = ("lista", "arquivo", "n", "degrau", "regressivo", "quarentena", "preparo", "globs", "erros")

    def __init__(self, arquivo: str, n: int):
        self.lista = ""
        self.arquivo = arquivo
        self.n = n
        self.degrau = ""
        self.regressivo = False
        self.quarentena = ""
        self.preparo = False
        self.globs: list[str] = []
        self.erros: list[str] = []


def ler_linha(texto: str, n: int = 1) -> Optional[Linha]:
    """A linha da lista, ou None se é comentário ou vazia. Espelha `campos_da_linha` do bin/teste."""
    if not texto.strip() or texto.lstrip().startswith("#"):
        return None
    arquivo, barra, resto = texto.partition("|")
    linha = Linha(arquivo.strip(), n)
    if not barra:
        return linha
    for campo in resto.split("|"):
        campo = campo.strip()
        nomeado = NOMEADO.match(campo)
        if not campo:
            continue
        if campo.startswith("degrau:"):
            valor = campo[len("degrau:"):].strip()
            if valor in DEGRAUS:
                linha.degrau = valor
            else:
                linha.erros.append(f"degrau: com valor '{valor}' (pequeno, imagem ou rodada)")
        elif re.fullmatch(r"regressivo(\s.*)?", campo):
            linha.regressivo = True
        elif re.fullmatch(r"quarentena(\s.*)?", campo):
            linha.quarentena = campo
        elif re.fullmatch(r"preparo(\s.*)?", campo):
            linha.preparo = True
        elif nomeado:
            linha.erros.append(f"campo desconhecido '{nomeado.group(1)}:'")
        else:
            linha.globs.extend(campo.split())
    return linha


def listas_de_portao(raiz: Path, alvo: Optional[str] = None) -> Iterator[Path]:
    """Cada arquivo `VERDES` do repositório, ou o que `alvo` aponta (arquivo ou pasta)."""
    base = (raiz / alvo) if alvo else raiz
    if base.is_file():
        yield base
        return
    for dirpath, dirs, nomes in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in PASTAS_FORA)
        if "VERDES" in nomes:
            yield Path(dirpath) / "VERDES"


def _linhas(raiz: Path, alvo: Optional[str]) -> Iterator[Linha]:
    for lista in listas_de_portao(raiz, alvo):
        try:
            texto = lista.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(lista.relative_to(raiz))
        except ValueError:
            rel = str(lista)
        for n, bruta in enumerate(texto.splitlines(), 1):
            linha = ler_linha(bruta, n)
            if linha is not None and linha.arquivo:
                linha.lista = rel
                yield linha


# ------------------------------------------------------------------ detectores
# cada um recebe a linha e devolve o detalhe do que fere, ou None

def t1(linha: Linha) -> Optional[str]:
    """campo que a gramática não lê"""
    return "; ".join(linha.erros) if linha.erros else None


def t2(linha: Linha) -> Optional[str]:
    """regressivo fora do pequeno"""
    if linha.regressivo and linha.degrau in ("imagem", "rodada"):
        return f"regressivo com degrau: {linha.degrau}"
    return None


def t3(linha: Linha) -> Optional[str]:
    """quarentena sem débito"""
    if linha.quarentena and not re.search(r"#\d+", linha.quarentena):
        return "quarentena sem #<débito>"
    return None


DETECTORES: dict[str, Callable[[Linha], Optional[str]]] = {"T1": t1, "T2": t2, "T3": t3}


def verificar_testes(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> Tuple[list[Apontamento], str, Optional[int]]:
    raiz = Path(raiz)
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ValueError(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")

    rev = lista.get("rev", 1)
    itens = [i for i in lista.get("itens", []) if i.get("id")]
    apontamentos: list[Apontamento] = []

    for item in itens:
        if item["id"] not in DETECTORES:
            apontamentos.append(Apontamento(
                CHAVE_LISTA, 1, f"{item['id']} {item.get('o_que_fere', '')} [sem detector no lint testes]".strip(),
                "escrever o detector em bin/_lint/testes.py ou tirar o critério da lista",
                severidade="aviso", id=item["id"]))

    for linha in _linhas(raiz, alvo):
        for item in itens:
            detector = DETECTORES.get(item["id"])
            detalhe = detector(linha) if detector else None
            if detalhe is None:
                continue
            apontamentos.append(Apontamento(
                linha.lista, linha.n,
                f"{item['id']} {item.get('o_que_fere', '')} [{linha.arquivo}: {detalhe}]".strip(),
                item.get("cura", ""),
                severidade=item.get("severidade", "aviso"), id=item["id"]))
    return apontamentos, CHAVE_LISTA, rev
