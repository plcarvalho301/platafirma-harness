"""Estrutura derivável da camada de texto (card #3189, ato temporário `acervo censo obra`).

Bloco I do censo: só texto, determinístico, sem modelo (NBR 6024, 6027, 6029, 6034; Tschichold).
Entrada: a lista de páginas (o texto de cada uma). Saída: um dict com as medidas.
Só biblioteca padrão. Não levanta: o que não se mede fica None.
"""
from __future__ import annotations

import bisect
import re
from collections import Counter

PAGINAS_SUMARIO = 15        # o sumário se procura nas primeiras 15 páginas
LIVRO_MIN = 50              # NBR 6029 §3.32: livro tem mais de 49 páginas
FOLHETO_MIN = 5             # e folheto de 5 a 49
LINHAS_POR_PAGINA_PSEUDO = 60   # TXT e MD sem form feed: páginas de mentira, só para janelar

_ROMANO = re.compile(r"^m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")
# título + folio no fim: com reticências ou 2+ espaços (arábico ou romano); com 1 espaço, só arábico
_FOLIO_LIDER = re.compile(r"^(?P<t>\S.*?\S)(?:\s*[.·…_]{2,}\s*|\s{2,})(?P<f>\d{1,4}|[ivxlcdm]{1,7})$", re.I)
_FOLIO_SIMPLES = re.compile(r"^(?P<t>\S.*[A-Za-zÀ-ÿ)])\s(?P<f>\d{1,4})$")
_SEM_INDICE = re.compile(r"^(figura|tabela|mapa|gr[aá]fico)\s+\d", re.I)
_INDICATIVO = re.compile(r"^([1-9]\d*(?:\.[1-9]\d*){0,4}) \S")
_FOLIO_PURO = re.compile(r"^(\d{1,4}|[ivxlcdm]{1,7})$", re.I)
_INDICE_REMISSIVO = re.compile(r"^.{2,80}?,\s*\d{1,4}(?:[-–]\d{1,4})?(?:\s*,\s*\d{1,4}(?:[-–]\d{1,4})?)*\s*$")
_MARCA_LICENCA = re.compile(r"licen|licens|downloaded|purchased|copyright|©|https?://|www\.|@|lic\.|personal use|uso pessoal", re.I)
_HIFEN = ("-", chr(0x00AD), chr(0x2010))


def _romano_valor(s: str) -> int | None:
    s = s.lower()
    if not s or not _ROMANO.match(s):
        return None
    tab = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = tab[a]
        total += -v if b != " " and tab[b] > v else v
    return total


def _folio_valor(txt: str) -> int | None:
    if txt.isdigit():
        return int(txt)
    return _romano_valor(txt)


def _mais_longa_nao_decrescente(seq: list[int]) -> int:
    caudas: list[int] = []
    for v in seq:
        i = bisect.bisect_right(caudas, v)
        if i == len(caudas):
            caudas.append(v)
        else:
            caudas[i] = v
    return len(caudas)


def _folio_no_fim(linha: str) -> int | None:
    """O folio de uma linha 'título ... folio', ou None. Lista de figuras e tabelas não conta."""
    if len(linha) > 160 or _SEM_INDICE.match(linha):
        return None
    m = _FOLIO_LIDER.match(linha)
    if m:
        return _folio_valor(m.group("f"))
    m = _FOLIO_SIMPLES.match(linha)
    return _folio_valor(m.group("f")) if m else None


def _sumario(linhas_pag: list[list[str]]) -> dict:
    melhor, onde = 0, None
    for i, linhas in enumerate(linhas_pag[:PAGINAS_SUMARIO], 1):
        folios = [v for v in (_folio_no_fim(l) for l in linhas) if v is not None]
        n = _mais_longa_nao_decrescente(folios)
        if n >= 3 and n > melhor:
            melhor, onde = n, i
    return {"entradas": melhor, "pagina": onde}


def _indicativo_valido(prev: tuple | None, c: tuple) -> bool:
    if prev is None:
        return c == (1,)
    if len(c) == len(prev) + 1 and c[:-1] == prev and c[-1] == 1:
        return True                                     # filho depois do pai
    k = len(c)
    return k <= len(prev) and c[:k - 1] == prev[:k - 1] and c[k - 1] == prev[k - 1] + 1   # irmão incrementa


def _indicativos(linhas_pag: list[list[str]]) -> dict:
    aceitos: list[tuple] = []
    prev = None
    for linhas in linhas_pag:
        for l in linhas:
            if len(l) > 100 or l.endswith("."):
                continue
            m = _INDICATIVO.match(l)
            if not m or _folio_no_fim(l) is not None:
                continue                                # linha de sumário não é indicativo
            c = tuple(int(x) for x in m.group(1).split("."))
            if _indicativo_valido(prev, c):
                aceitos.append(c)
                prev = c
    return {"contagem": len(aceitos), "profundidade_max": max((len(c) for c in aceitos), default=0)}


def _norm_repeticao(linha: str) -> str:
    return re.sub(r"\d+", "#", linha.strip().lower())


def _mobilia(linhas_pag: list[list[str]]) -> dict:
    """Proporção de páginas cujo topo ou pé repete uma linha, por paridade (NBR 6029 §5.3)."""
    saida: dict = {}
    marca = 0
    for nome, resto in (("impar", 1), ("par", 0)):
        idx = [i for i in range(len(linhas_pag)) if (i + 1) % 2 == resto and linhas_pag[i]]
        topos = Counter(_norm_repeticao(linhas_pag[i][0]) for i in idx if not _FOLIO_PURO.match(linhas_pag[i][0]))
        pes = Counter(_norm_repeticao(linhas_pag[i][-1]) for i in idx if not _FOLIO_PURO.match(linhas_pag[i][-1]))
        minimo = max(3, int(0.2 * len(idx)))
        topo = next((k for k, v in topos.most_common(1) if v >= minimo), None)
        pe = next((k for k, v in pes.most_common(1) if v >= minimo), None)
        com = 0
        for i in idx:
            t, p = _norm_repeticao(linhas_pag[i][0]), _norm_repeticao(linhas_pag[i][-1])
            if (topo is not None and t == topo) or (pe is not None and p == pe):
                com += 1
        saida[nome] = {"paginas": len(idx), "repetem": com,
                       "proporcao": round(com / len(idx), 4) if idx else None,
                       "topo": topo, "pe": pe}
        marca += sum(1 for k in (topo, pe) if k and _MARCA_LICENCA.search(k))
    saida["marca_licenca_linhas"] = marca      # marca d'água de licença repete e fica à parte
    return saida


def _folio_offset(linhas_pag: list[list[str]]) -> dict:
    """Página física − fólio, e se é constante (≥ 90% das páginas com fólio no mesmo deslocamento)."""
    offs = []
    for i, linhas in enumerate(linhas_pag, 1):
        for cand in (linhas[-1:] + linhas[:1]):
            if _FOLIO_PURO.match(cand):
                v = _folio_valor(cand)
                if v is not None:
                    offs.append(i - v)
                    break
    if not offs:
        return {"paginas_com_folio": 0, "offset_modal": None, "constante": None}
    modal, n = Counter(offs).most_common(1)[0]
    return {"paginas_com_folio": len(offs), "offset_modal": modal, "constante": n >= 0.9 * len(offs)}


def _hifen_eol(linhas_pag: list[list[str]]) -> dict:
    todas = [l for linhas in linhas_pag for l in linhas]
    n = 0
    for a, b in zip(todas, todas[1:]):
        if len(a) >= 2 and a[-1] in _HIFEN and a[-2].isalpha() and b[:1].islower():
            n += 1
    return {"total": n, "por_mil_linhas": round(1000 * n / len(todas), 3) if todas else None}


def _indice_final(linhas_pag: list[list[str]]) -> dict:
    total = len(linhas_pag)
    inicio = total - max(1, total // 10) if total else 0
    janela = [l for linhas in linhas_pag[inicio:] for l in linhas]
    casam = sum(1 for l in janela if _INDICE_REMISSIVO.match(l) and not _FOLIO_PURO.match(l))
    return {"linhas": len(janela), "casam": casam,
            "proporcao": round(casam / len(janela), 4) if janela else None,
            "paginas": total - inicio}


def paginas_de_texto(texto: str) -> tuple[list[str], bool]:
    """Páginas para TXT e MD: as de form feed, se houver; senão janelas de 60 linhas (pseudo=True)."""
    if "\f" in texto:
        return texto.split("\f"), False
    linhas = texto.splitlines()
    n = LINHAS_POR_PAGINA_PSEUDO
    return ["\n".join(linhas[i:i + n]) for i in range(0, len(linhas), n)] or [""], True


def derivar(paginas: list[str] | None, pseudo: bool = False) -> dict | None:
    """As medidas do bloco I. `pseudo`: as páginas são janelas de mentira (mobília e fólio ficam None)."""
    if not paginas:
        return None
    linhas_pag = [[l.strip() for l in p.splitlines() if l.strip()] for p in paginas]
    n = len(paginas)
    return {
        "paginas": n,
        "paginas_pseudo": pseudo,
        "porte": None if pseudo else ("livro" if n >= LIVRO_MIN else "folheto" if n >= FOLHETO_MIN else None),
        "sumario_entradas": _sumario(linhas_pag),
        "indicativos": _indicativos(linhas_pag),
        "mobilia": None if pseudo else _mobilia(linhas_pag),
        "folio_offset": None if pseudo else _folio_offset(linhas_pag),
        "hifen_eol": _hifen_eol(linhas_pag),
        "indice_final": _indice_final(linhas_pag),
    }
