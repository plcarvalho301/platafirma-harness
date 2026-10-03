# md_render — Markdown e os formatos de mesa/caderno -> HTML, sem dependencia externa.
# capacidade: expediente
# dono: claudinho-TI
"""Conteudo LIVRE (persona, mesa, caderno), escrito pela cadeira, chega como texto.
`_esc()` cru despejava tudo grudado — a "linguica" da tela. Aqui cada formato vira
estrutura: `md_seguro` para Markdown (heading, lista, tabela, citacao, bloco de
codigo, enfase, link http), `render_mesa` para os itens `#N [chapeu] ato -> alvo` e
`render_cadernos` para o indice e o corpo do caderno.

Seguro por construcao: todo texto passa por `html.escape` ANTES de entrar numa tag;
nenhum HTML do conteudo sobrevive, so as tags que este modulo emite. Link so com
http(s). Ausencia se desenha como ausencia: vazio nunca vira saude.
"""

from __future__ import annotations

import html
import re
from typing import Any


def _esc(s: Any) -> str:
    return html.escape(str(s)) if s is not None else ""


# --- inline -------------------------------------------------------------

_INLINE = (
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)"),
     r'<a href="\2" rel="noopener noreferrer">\1</a>'),
    # referencia de entrada de caderno: [c77]
    (re.compile(r"(?<![\w\[])\[(c\d+)\](?!\()"), r'<span class="ref mono">\1</span>'),
)


def md_inline(texto_escapado: str) -> str:
    """Enfase, link e codigo inline sobre texto JA escapado. O que esta entre
    crases fica como esta: nao recebe enfase nem link."""
    partes = re.split(r"(`[^`]+`)", texto_escapado)
    for i, p in enumerate(partes):
        if i % 2:
            partes[i] = f"<code>{p[1:-1]}</code>"
        else:
            for rx, repl in _INLINE:
                p = rx.sub(repl, p)
            partes[i] = p
    return "".join(partes)


def _inline(texto: str) -> str:
    return md_inline(_esc(texto))


# --- blocos -------------------------------------------------------------

_RE_H = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_UL = re.compile(r"^[-*+]\s+(.*)$")
_RE_OL = re.compile(r"^\d+[.)]\s+(.*)$")
_RE_BANNER = re.compile(r"^={3,}\s*(.*?)\s*={3,}$")
_RE_SEP_TABELA = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def _celulas(linha: str) -> list[str]:
    miolo = linha.strip().removeprefix("|")
    if miolo.endswith("|") and not miolo.endswith("\\|"):
        miolo = miolo[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", miolo)]


def _tabela(cab: list[str], linhas: list[list[str]]) -> str:
    n = len(cab)
    th = "".join(f"<th>{_inline(c)}</th>" for c in cab)
    trs = []
    for linha in linhas:
        cel = (linha + [""] * n)[:n]
        trs.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cel) + "</tr>")
    return (f'<div class="tabela-md"><table><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def md_seguro(texto: Any) -> str:
    """Markdown -> HTML. String vazia/None vira vazio, nunca vira saude.

    Cobre o que persona, mesa e caderno usam: '#'..'######' (heading), linha
    '=====' (banner), '---' (separador), '- '/'* '/'1. ' (lista, com linha de
    continuacao indentada), tabela '|', citacao '>', bloco ``` , paragrafo e
    enfase/link/codigo inline. O resto cai como paragrafo de texto escapado —
    nunca some, nunca vira tag alheia. Linha '#25 ...' (numero de item) nao e
    heading: heading pede espaco depois do '#'.
    """
    if not texto:
        return ""
    linhas = str(texto).replace("\r\n", "\n").split("\n")
    out: list[str] = []
    par: list[str] = []
    cit: list[str] = []
    lista: list = []  # [tipo, [itens]]; vazia = fechada

    def fecha_par():
        if par:
            out.append("<p>" + _inline(" ".join(par)) + "</p>")
            par.clear()

    def fecha_cit():
        if cit:
            out.append("<blockquote><p>" + _inline(" ".join(cit)) + "</p></blockquote>")
            cit.clear()

    def fecha_lista():
        if lista:
            tipo, itens = lista
            out.append(f"<{tipo}>" + "".join(f"<li>{_inline(t)}</li>" for t in itens)
                       + f"</{tipo}>")
            lista.clear()

    def fecha():
        fecha_par()
        fecha_cit()
        fecha_lista()

    i = 0
    while i < len(linhas):
        bruta = linhas[i].rstrip()
        crua = bruta.strip()
        i += 1
        if crua.startswith("```"):
            fecha()
            bloco = []
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                bloco.append(linhas[i])
                i += 1
            i += 1
            out.append("<pre><code>" + _esc("\n".join(bloco)) + "</code></pre>")
            continue
        if not crua:
            fecha_par()
            fecha_cit()
            continue  # a lista segue aberta ate vir outra coisa
        if crua in ("---", "***", "___"):
            fecha()
            out.append("<hr>")
            continue
        m = _RE_BANNER.match(crua)
        if m:
            fecha()
            out.append(f'<h3 class="banner">{_inline(m.group(1))}</h3>')
            continue
        m = _RE_H.match(crua)
        if m:
            fecha()
            nivel = len(m.group(1))
            out.append(f"<h{nivel}>{_inline(m.group(2))}</h{nivel}>")
            continue
        if crua.startswith("|") and i < len(linhas) and _RE_SEP_TABELA.match(linhas[i].strip()):
            fecha()
            cab = _celulas(crua)
            i += 1
            corpo: list[list[str]] = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                corpo.append(_celulas(linhas[i]))
                i += 1
            out.append(_tabela(cab, corpo))
            continue
        if crua.startswith(">"):
            fecha_par()
            fecha_lista()
            cit.append(crua.lstrip(">").strip())
            continue
        tipo = "ul"
        m = _RE_UL.match(crua)
        if not m:
            tipo = "ol"
            m = _RE_OL.match(crua)
        if m:
            fecha_par()
            fecha_cit()
            if lista and lista[0] != tipo:
                fecha_lista()
            if not lista:
                lista.extend([tipo, []])
            lista[1].append(m.group(1))
            continue
        if lista and bruta[:1] in (" ", "\t"):
            lista[1][-1] += " " + crua  # continuacao do item
            continue
        fecha_lista()
        fecha_cit()
        par.append(crua)
    fecha()
    return "".join(out)


# --- mesa ---------------------------------------------------------------
# `mesa ver` imprime um item por linha: `#N [chapeu] ato → alvo   (plantado ha X)`,
# ordenado por chapeu. Linha sem esse cabecalho e continuacao do item anterior.

_RE_ITEM = re.compile(r"^#(\d+)\s+\[([^\]]+)\]\s*(.*)$")
_RE_PLANTADO = re.compile(r"\s+\(plantado h[aá] ([^)]*)\)\s*$")


def itens_mesa(conteudo: Any) -> tuple[list[dict], list[str]]:
    """(itens, soltas): os itens da mesa e as linhas que vieram antes de qualquer
    item (cabecalho, `slot X: vazio`). O chapeu sai SO do cabecalho `#N [chapeu]`:
    colchete no meio do texto (`[conf: media]`) nao e chapeu."""
    itens: list[dict] = []
    soltas: list[str] = []
    for linha in str(conteudo or "").replace("\r\n", "\n").split("\n"):
        crua = linha.strip()
        if not crua:
            continue
        m = _RE_ITEM.match(crua)
        if m:
            resto, plantado = m.group(3), ""
            pl = _RE_PLANTADO.search(resto)
            if pl:
                plantado, resto = pl.group(1), resto[:pl.start()]
            ato, sep, alvo = resto.rpartition(" → ")
            if not sep:
                ato, alvo = resto, ""
            itens.append({"num": m.group(1), "chapeu": m.group(2).strip(),
                          "ato": ato.strip(), "alvo": alvo.strip(),
                          "plantado": plantado, "extra": []})
        elif itens:
            itens[-1]["extra"].append(crua)
        else:
            soltas.append(crua)
    return itens, soltas


def contagem_mesa(conteudo: Any) -> dict[str, int]:
    cont: dict[str, int] = {}
    for it in itens_mesa(conteudo)[0]:
        cont[it["chapeu"]] = cont.get(it["chapeu"], 0) + 1
    return cont


def _item_mesa_html(it: dict) -> str:
    cab = [f'<span class="num mono">#{_esc(it["num"])}</span>']
    if it["plantado"]:
        cab.append(f'<span class="idade">plantado há {_esc(it["plantado"])}</span>')
    partes = [f'<div class="mesa-cab">{"".join(cab)}</div>']
    if it["ato"]:
        partes.append(f'<p class="mesa-ato">{_inline(it["ato"])}</p>')
    if it["alvo"]:
        partes.append(f'<p class="mesa-alvo"><span class="rot">alvo</span> {_inline(it["alvo"])}</p>')
    if it["extra"]:
        partes.append('<div class="mesa-extra">' + md_seguro("\n".join(it["extra"])) + "</div>")
    return '<li class="mesa-item">' + "".join(partes) + "</li>"


def _vazio(texto: str) -> str:
    return f'<p class="vazio">{texto}</p>'


def render_mesa(conteudo: Any, chapeu_sel: str | None = None) -> str:
    """A mesa em cartoes, agrupada por chapeu (ou so os do chapeu escolhido).
    Sem item do chapeu, diz que nao ha — ausencia se declara."""
    itens, soltas = itens_mesa(conteudo)
    if chapeu_sel:
        itens = [it for it in itens if it["chapeu"] == chapeu_sel]
        if not itens:
            return _vazio(f"Nenhum item da mesa para o chapéu <code>{_esc(chapeu_sel)}</code>.")
        return '<ol class="mesa-itens">' + "".join(_item_mesa_html(it) for it in itens) + "</ol>"
    if not itens:
        return md_seguro("\n".join(soltas)) or _vazio("Mesa sem conteúdo.")
    grupos: dict[str, list[dict]] = {}
    for it in itens:
        grupos.setdefault(it["chapeu"], []).append(it)
    blocos = [md_seguro("\n".join(soltas))] if soltas else []
    for chapeu, grupo in grupos.items():
        blocos.append(
            '<section class="mesa-grupo">'
            f'<h3>{_esc(chapeu)} <span class="n num">{len(grupo)}</span></h3>'
            '<ol class="mesa-itens">' + "".join(_item_mesa_html(it) for it in grupo) + "</ol>"
            "</section>"
        )
    return "".join(blocos)


# --- cadernos -----------------------------------------------------------
# `mesa caderno` serve um indice (`chapeu  N vigentes · X/1500 tk · ...`, uma linha
# por chapeu, mais a nota `(corpo sob demanda: ...)`) e, na sessao com chapeu, o
# corpo: `===== caderno <cadeira>/<chapeu> · ... =====` seguido de `## categoria` e
# `- [cNN] entrada`.

_RE_LINHA_INDICE = re.compile(r"^(\S+)\s+(.*\d.*)$")
_RE_CAD_TITULO = re.compile(r"^caderno\s+(\S+)\s*(.*)$")
_RE_ATENCAO = re.compile(r"acumulando|legado|revisar|a triar")


def _chips(resto: str) -> str:
    out = []
    for x in (p.strip() for p in resto.split(" · ")):
        if x:
            papel = "caveat" if _RE_ATENCAO.search(x) else "calmo"
            out.append(f'<span class="chip {papel}">{_esc(x)}</span>')
    return "".join(out)


def _indice_html(linhas: list[str], chapeu_sel: str | None) -> tuple[str, str]:
    """(lista de chapeus, notas e linhas soltas)."""
    lis, resto_html = [], []
    for linha in linhas:
        m = None if linha.startswith("(") else _RE_LINHA_INDICE.match(linha)
        if m:
            if chapeu_sel and m.group(1) != chapeu_sel:
                continue
            lis.append(f'<li><span class="cad-chapeu">{_esc(m.group(1))}</span>'
                       f'<span class="cad-metricas">{_chips(m.group(2))}</span></li>')
        else:
            resto_html.append(f'<p class="nota-indice">{_inline(linha)}</p>')
    return ('<ul class="cad-indice">' + "".join(lis) + "</ul>" if lis else ""), "".join(resto_html)


def _secao_html(titulo: str, corpo: list[str]) -> str:
    m = _RE_CAD_TITULO.match(titulo)
    if m:
        cab = (f'<h3 class="cad-titulo">caderno <span class="mono">{_esc(m.group(1))}</span></h3>'
               f'<div class="cad-metricas">{_chips(m.group(2).lstrip("· ").strip())}</div>')
    else:
        cab = f'<h3 class="cad-titulo">{_inline(titulo)}</h3>'
    return '<section class="cad-secao">' + cab + md_seguro("\n".join(corpo)) + "</section>"


def render_cadernos(conteudo: Any, chapeu_sel: str | None = None) -> str:
    """O indice dos cadernos em linhas com chips e, quando a abertura traz o corpo,
    cada caderno com suas categorias. Com chapeu escolhido, so o dele."""
    indice: list[str] = []
    secoes: list[list] = []
    for linha in str(conteudo or "").replace("\r\n", "\n").split("\n"):
        crua = linha.strip()
        if crua.startswith("====="):
            secoes.append([crua.strip("=").strip(), []])
        elif secoes:
            secoes[-1][1].append(linha)
        elif crua:
            indice.append(crua)
    if chapeu_sel:
        def _do_chapeu(titulo: str) -> bool:
            m = _RE_CAD_TITULO.match(titulo)
            return bool(m) and m.group(1).rsplit("/", 1)[-1] == chapeu_sel
        secoes = [s for s in secoes if _do_chapeu(s[0])]
    lista, notas = _indice_html(indice, chapeu_sel)
    if chapeu_sel and not lista and not secoes:
        return _vazio(f"Nenhum caderno indexado para o chapéu <code>{_esc(chapeu_sel)}</code>.")
    return lista + notas + "".join(_secao_html(t, c) for t, c in secoes)
