"""Checagem estrutural de diagrama: plano contra SVG.

Mede o que o leitor vê, com a figura numa coluna de 760 px: a letra no tamanho de um papel da hierarquia
de tipo da platafirma-ui, a proporção, o cruzamento de setas, o rótulo longe da seta e o texto sobre caixa
alheia. Mede também o que a casa veda: entidade e rótulo do plano fora dos textos da figura, cor fora dos
tokens, efeito, fio grosso, mais de quatro famílias e rótulo de caixa em peso regular. O que pede olho é
do crítico de figura.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from diagrama import medida
from diagrama import tokens as tk

LEITURA = 760.0
DISTANCIA_ROTULO = 24.0
PAPEIS = (("bloco", "text-section"), ("texto", "text-body"), ("metadado", "text-meta"))
TAGS_DE_EFEITO = {"filter", "lineargradient", "radialgradient", "fegaussianblur", "fedropshadow", "feoffset"}
COR_LIVRE = {"none", "transparent", "currentcolor", "inherit"}
PESOS_DE_ROTULO = {"bold", "bolder", "600", "700", "800", "900"}
GRUPO_DE_SETA = re.compile(r"\b(seta|link|edge)\b")
GRUPO_DE_CAIXA = re.compile(r"\b(caixa|entity|node)\b")
_RGB = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", re.I)
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_HERDA = ("font-size", "font-weight", "text-anchor", "fill", "stroke", "stroke-width")


# ----------------------------------------------------------------------------------------------- leitura

def _props(el: ET.Element) -> dict[str, str]:
    """Atributos do elemento, com as propriedades do `style` por cima."""
    p = {k.lower(): v for k, v in el.attrib.items()}
    for trecho in (el.get("style") or "").split(";"):
        if ":" in trecho:
            k, v = trecho.split(":", 1)
            p[k.strip().lower()] = v.strip()
    return p


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1].lower()


def _cor_normal(valor: str) -> str | None:
    v = valor.strip().lower()
    m = _RGB.match(v)
    if m:
        return "#{:02x}{:02x}{:02x}".format(*(min(int(g), 255) for g in m.groups()))
    return tk.normaliza_cor(v)


def _numero(valor: str) -> float | None:
    m = re.match(r"^\s*([-+]?[\d.]+)", valor or "")
    return float(m.group(1)) if m else None


def _caminhar(el: ET.Element, herdado: dict, grupos: tuple, saida: list) -> None:
    """Percorre a árvore com as propriedades herdadas e a pilha de grupos com classe."""
    props = dict(herdado)
    proprias = _props(el)
    for k in _HERDA:
        if k in proprias:
            props[k] = proprias[k]
    classe = (el.get("class") or "") + " " + (el.get("id") or "")
    if _tag(el) == "g" and classe.strip():
        grupos = grupos + ((classe, el),)
    saida.append((el, props, grupos))
    if _tag(el) in ("metadata", "defs", "title", "desc"):
        return
    for filho in el:
        _caminhar(filho, props, grupos, saida)


def _texto_de(el: ET.Element) -> str:
    return " ".join(t.strip() for t in el.itertext() if t.strip())


def _dimensoes(root: ET.Element) -> tuple[float, float]:
    vb = (root.get("viewBox") or "").replace(",", " ").split()
    if len(vb) == 4:
        return float(vb[2]), float(vb[3])
    return _numero(root.get("width", "")) or 0.0, _numero(root.get("height", "")) or 0.0


# ----------------------------------------------------------------------------------------------- geometria

def _bezier(p0, p1, p2, p3, n=8):
    return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0],
             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1])
            for t in (k / n for k in range(1, n + 1))]


def pontos_do_path(d: str) -> list[list[tuple]]:
    """Os traços de um `path`, cada um como lista de pontos; curva vira poligonal."""
    fichas = re.findall(r"[MmLlHhVvCcSsQqTtZzAa]|" + _NUM.pattern, d or "")
    tracos, atual = [], []
    x = y = 0.0
    inicio = (0.0, 0.0)
    cmd = None
    i = 0
    ultimo_ctrl = None

    def nums(k):
        nonlocal i
        vals = [float(v) for v in fichas[i:i + k]]
        i += k
        return vals

    while i < len(fichas):
        f = fichas[i]
        if re.fullmatch(r"[A-Za-z]", f):
            cmd = f
            i += 1
            if cmd in "Zz":
                if atual:
                    atual.append(inicio)
                x, y = inicio
                continue
        if cmd is None:
            break
        rel = cmd.islower()
        c = cmd.upper()
        try:
            if c == "M":
                dx, dy = nums(2)
                x, y = (x + dx, y + dy) if rel else (dx, dy)
                if len(atual) > 1:
                    tracos.append(atual)
                atual = [(x, y)]
                inicio = (x, y)
                cmd = "l" if rel else "L"
            elif c == "L":
                dx, dy = nums(2)
                x, y = (x + dx, y + dy) if rel else (dx, dy)
                atual.append((x, y))
            elif c == "H":
                (v,) = nums(1)
                x = x + v if rel else v
                atual.append((x, y))
            elif c == "V":
                (v,) = nums(1)
                y = y + v if rel else v
                atual.append((x, y))
            elif c == "C":
                v = nums(6)
                if rel:
                    v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y, v[4] + x, v[5] + y]
                atual += _bezier((x, y), (v[0], v[1]), (v[2], v[3]), (v[4], v[5]))
                ultimo_ctrl = (v[2], v[3])
                x, y = v[4], v[5]
            elif c == "S":
                v = nums(4)
                if rel:
                    v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y]
                c1 = (2 * x - ultimo_ctrl[0], 2 * y - ultimo_ctrl[1]) if ultimo_ctrl else (x, y)
                atual += _bezier((x, y), c1, (v[0], v[1]), (v[2], v[3]))
                ultimo_ctrl = (v[0], v[1])
                x, y = v[2], v[3]
            elif c in ("Q", "T"):
                k = 4 if c == "Q" else 2
                v = nums(k)
                if rel:
                    v = [v[j] + (x if j % 2 == 0 else y) for j in range(k)]
                fim = (v[-2], v[-1])
                atual.append(fim)
                x, y = fim
            elif c == "A":
                v = nums(7)
                x, y = (x + v[5], y + v[6]) if rel else (v[5], v[6])
                atual.append((x, y))
            else:
                i += 1
        except (ValueError, IndexError):
            break
    if len(atual) > 1:
        tracos.append(atual)
    return tracos


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _cruzam(a1, a2, b1, b2) -> bool:
    """Os dois segmentos se cruzam por dentro, sem contar ponta encostada em ponta ou em segmento."""
    d1, d2 = _orient(b1, b2, a1), _orient(b1, b2, a2)
    d3, d4 = _orient(a1, a2, b1), _orient(a1, a2, b2)
    eps = 1e-6
    return ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
           ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps))


def _tira_o_comum(segs: list, outros: list) -> list:
    """Os segmentos sem os trechos em que correm junto com os outros. Duas setas do mesmo feixe dividem o
    tronco, e o lugar onde uma entra ou sai dele é ponta que encosta, e não cruzamento."""
    saida = []
    for p, q in segs:
        if abs(p[1] - q[1]) < 1e-6:
            v, f = 0, 1
        elif abs(p[0] - q[0]) < 1e-6:
            v, f = 1, 0
        else:
            saida.append((p, q))
            continue
        lo, hi = sorted((p[v], q[v]))
        cortes = []
        for r, t in outros:
            if abs(r[f] - t[f]) < 1e-6 and abs(r[f] - p[f]) < 1e-6:
                a, b = max(lo, min(r[v], t[v])), min(hi, max(r[v], t[v]))
                if b - a > 1e-6:
                    cortes.append((a, b))
        x = lo
        for a, b in sorted(cortes) + [(hi, hi)]:
            if a - x > 1e-6:
                saida.append(((x, p[f]), (a, p[f])) if v == 0 else ((p[f], x), (p[f], a)))
            x = max(x, b)
    return saida


def _se_cruzam(segs_a: list, segs_b: list) -> bool:
    """A segunda seta anda um centésimo de pixel para um lado e depois para o outro. O cruzamento de verdade
    aparece nos dois, até o que passa por vértice das duas; o feixe que se junta ou se separa, e a ponta que
    só encosta, tocam de um lado só e não contam."""
    for sinal in (1, -1):
        dx, dy = 0.013 * sinal, 0.007 * sinal
        if not any(_cruzam(p1, p2, (q1[0] + dx, q1[1] + dy), (q2[0] + dx, q2[1] + dy))
                   for p1, p2 in segs_a for q1, q2 in segs_b):
            return False
    return True


def _dist_ponto_seg(p, a, b) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _dist_ret_seg(r, a, b) -> float:
    """Distância de um retângulo a um segmento: zero se o segmento entra nele."""
    if r[0] <= a[0] <= r[2] and r[1] <= a[1] <= r[3]:
        return 0.0
    cantos = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    lados = list(zip(cantos, cantos[1:] + cantos[:1]))
    if any(_cruzam(a, b, p, q) for p, q in lados):
        return 0.0
    return min([_dist_ponto_seg(c, a, b) for c in cantos] + [_dist_ponto_seg(a, p, q) for p, q in lados] +
               [_dist_ponto_seg(b, p, q) for p, q in lados])


def _caixa_do_texto(el: ET.Element, props: dict) -> tuple | None:
    """O retângulo que o texto ocupa, estimado pela medida da Inter."""
    tamanho = _numero(props.get("font-size", "16")) or 16.0
    peso = props.get("font-weight", "400")
    peso = {"bold": "700", "normal": "400"}.get(peso, peso)
    ancora = props.get("text-anchor", "start")
    linhas = [t for t in el.iter() if _tag(t) == "tspan"] or [el]
    caixas = []
    for t in linhas:
        txt = (t.text or "").strip() if t is not el else "".join(el.itertext()).strip()
        if not txt:
            continue
        x = _numero(t.get("x") or el.get("x") or "") or 0.0
        y = _numero(t.get("y") or el.get("y") or "") or 0.0
        w = medida.largura(txt, tamanho, peso if peso.isdigit() else 400)
        x0 = x - w / 2 if ancora == "middle" else x - w if ancora == "end" else x
        caixas.append((x0, y - 0.75 * tamanho, x0 + w, y + 0.25 * tamanho))
    if not caixas:
        return None
    return (min(c[0] for c in caixas), min(c[1] for c in caixas), max(c[2] for c in caixas), max(c[3] for c in caixas))


def _contorno(el: ET.Element) -> tuple | None:
    """O retângulo que uma forma ocupa: rect, polygon, ellipse, circle ou path fechado."""
    t = _tag(el)
    n = lambda k: _numero(el.get(k, "")) or 0.0  # noqa: E731
    if t == "rect":
        return (n("x"), n("y"), n("x") + n("width"), n("y") + n("height"))
    if t in ("ellipse", "circle"):
        rx = n("rx") if t == "ellipse" else n("r")
        ry = n("ry") if t == "ellipse" else n("r")
        return (n("cx") - rx, n("cy") - ry, n("cx") + rx, n("cy") + ry)
    if t == "polygon":
        vals = [float(v) for v in _NUM.findall(el.get("points", ""))]
        xs, ys = vals[0::2], vals[1::2]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None
    if t == "path":
        pts = [p for tr in pontos_do_path(el.get("d", "")) for p in tr]
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            return (min(xs), min(ys), max(xs), max(ys))
    return None


def _poligono(el: ET.Element, r: tuple) -> list:
    """O contorno real da forma: o losango e a elipse não ocupam o retângulo que os contém."""
    t = _tag(el)
    if t == "polygon":
        vals = [float(v) for v in _NUM.findall(el.get("points", ""))]
        pts = list(zip(vals[0::2], vals[1::2]))
        if len(pts) >= 3:
            return pts
    if t in ("ellipse", "circle"):
        cx, cy, a, b = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, (r[2] - r[0]) / 2, (r[3] - r[1]) / 2
        return [(cx + a * math.cos(2 * math.pi * k / 24), cy + b * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    return [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]


def _toca_poligono(r: tuple, poli: list, folga: float = 1.0) -> bool:
    """O retângulo do texto, encolhido pela folga, toca o polígono (teste do eixo separador)."""
    r = (r[0] + folga, r[1] + folga, r[2] - folga, r[3] - folga)
    if r[0] >= r[2] or r[1] >= r[3]:
        return False
    ret = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    for forma in (ret, poli):
        for i in range(len(forma)):
            x1, y1 = forma[i]
            x2, y2 = forma[(i + 1) % len(forma)]
            nx, ny = y2 - y1, x1 - x2
            pa = [nx * x + ny * y for x, y in ret]
            pb = [nx * x + ny * y for x, y in poli]
            if max(pa) <= min(pb) + 1e-9 or max(pb) <= min(pa) + 1e-9:
                return False
    return True


def _contem(a, b) -> bool:
    return a[0] <= b[0] + 0.5 and a[1] <= b[1] + 0.5 and a[2] >= b[2] - 0.5 and a[3] >= b[3] - 0.5


# ----------------------------------------------------------------------------------------------- medidas

def _setas(nos: list) -> list[dict]:
    """Cada seta da figura: o nome, os traços e os textos que vêm com ela."""
    setas: dict[int, dict] = {}
    for el, props, grupos in nos:
        grupo = next(((c, g) for c, g in reversed(grupos) if GRUPO_DE_SETA.search(c)), None)
        tag = _tag(el)
        eh_traco = tag in ("path", "line", "polyline")
        if not eh_traco and tag != "text":
            continue
        if grupo is None:
            if not (eh_traco and el.get("marker-end")):
                continue
            chave, g = id(el), el
        else:
            chave, g = id(grupo[1]), grupo[1]
        s = setas.setdefault(chave, {"nome": _nome_da_seta(g, len(setas) + 1), "tracos": [], "textos": []})
        if tag == "text":
            s["textos"].append((el, props))
        elif tag == "path":
            if (props.get("fill", "none").strip().lower() in ("none", "transparent")) or el.get("marker-end"):
                s["tracos"] += pontos_do_path(el.get("d", ""))
        elif tag == "line":
            n = lambda k: _numero(el.get(k, "")) or 0.0  # noqa: E731
            s["tracos"].append([(n("x1"), n("y1")), (n("x2"), n("y2"))])
        else:
            vals = [float(v) for v in _NUM.findall(el.get("points", ""))]
            s["tracos"].append(list(zip(vals[0::2], vals[1::2])))
    return [s for s in setas.values() if s["tracos"]]


def _nome_da_seta(g: ET.Element, n: int) -> str:
    if g.get("data-de") and g.get("data-para"):
        return f"{g.get('data-de')} → {g.get('data-para')}"
    titulo = next((t for t in g if _tag(t) == "title" and (t.text or "").strip()), None)
    if titulo is not None:
        return titulo.text.strip()
    if g.get("data-entity-1") and g.get("data-entity-2"):
        return f"{g.get('data-entity-1')} → {g.get('data-entity-2')}"
    return g.get("id") or f"seta {n}"


def _segmentos(seta: dict) -> list:
    return [(a, b) for tr in seta["tracos"] for a, b in zip(tr, tr[1:]) if a != b]


def _caixas(nos: list, largura: float, altura: float) -> list[tuple]:
    """As caixas da figura: formas dentro de grupo de caixa ou, sem grupo, formas soltas com contorno.
    Moldura que contém outra forma (fundo, zona, raia) não conta como caixa."""
    formas = []
    for el, props, grupos in nos:
        if _tag(el) not in ("rect", "polygon", "ellipse", "circle", "path"):
            continue
        if any(GRUPO_DE_SETA.search(c) for c, _ in grupos):
            continue
        if _tag(el) == "path" and props.get("fill", "none").strip().lower() in ("none", "transparent"):
            continue
        r = _contorno(el)
        if not r or (r[2] - r[0]) < 2 or (r[3] - r[1]) < 2:
            continue
        if r[2] - r[0] >= largura - 1 and r[3] - r[1] >= altura - 1:
            continue
        grupo = next((g for c, g in reversed(grupos) if GRUPO_DE_CAIXA.search(c)), None)
        formas.append((r, id(grupo) if grupo is not None else id(el), _poligono(el, r)))
    return [(r, dono, poli) for r, dono, poli in formas
            if not any(o is not r and _contem(r, o) and r != o for o, _, _ in formas)]


# ----------------------------------------------------------------------------------------------- checagem

def checar_svg(svg_texto: str, plano: dict | None = None, t: dict | None = None) -> list[str]:
    """Os defeitos do SVG, contra o plano quando ele vem."""
    root = ET.fromstring(re.sub(r'\sxmlns="[^"]+"', "", svg_texto, count=1))
    t = t or tk.carregar()
    largura, altura = _dimensoes(root)
    escala = min(1.0, LEITURA / largura) if largura else 1.0
    papeis = {nome: tk.px(tk.resolver(token, t)) for nome, token in PAPEIS}
    fio_max = tk.px(tk.resolver("diagram-border-width", t))
    paleta = tk.paleta(t)
    strokes_de_familia = {tk.familia(t, n)["stroke"]: n for n in range(1, 9)}
    nos: list = []
    _caminhar(root, {}, (), nos)
    textos = [(el, props, grupos) for el, props, grupos in nos if _tag(el) == "text" and _texto_de(el)]
    defeitos: list[str] = []

    if plano:
        conteudo = " ".join(_texto_de(el) for el, _, _ in textos)
        for ent in plano.get("entidades", []):
            nome, eid = ent.get("nome", ""), ent.get("id", "")
            palavras = [w for w in re.findall(r"\w+", nome) if len(w) > 2]
            if not ((nome and nome in conteudo) or (palavras and all(w in conteudo for w in palavras))
                    or (not nome and eid in conteudo)):
                defeitos.append(f"entidade '{nome}' ({eid}) do plano ausente nos textos da figura")
        for rel in plano.get("relacoes", []):
            rotulo = rel.get("rotulo", "").strip()
            palavras = [w for w in re.findall(r"\w+", rotulo) if len(w) > 2]
            if rotulo and not (rotulo in conteudo or (palavras and all(w in conteudo for w in palavras))):
                defeitos.append(f"relação '{rel.get('de')} -> {rel.get('para')}' com rótulo '{rotulo}' "
                                f"ausente nos textos da figura")

    # letra: na coluna de leitura, cada texto tem o tamanho de um papel da hierarquia
    validos = sorted(set(papeis.values()))
    for el, props, _ in textos:
        sz = _numero(props.get("font-size", "16")) or 16.0
        lido = sz * escala
        if not any(abs(lido - v) < 0.05 for v in validos):
            nomes = ", ".join(f"{n} {v:g}" for n, v in papeis.items())
            defeitos.append(f"texto '{_texto_de(el)}' sai com letra de {lido:.1f}px na coluna de {LEITURA:g}px; "
                            f"a letra é a de um papel ({nomes})")

    if largura and altura and largura > 2 * altura:
        defeitos.append(f"figura de {largura:g} por {altura:g}: a largura passa do dobro da altura")

    setas = _setas(nos)
    for i, a in enumerate(setas):
        for b in setas[i + 1:]:
            sa, sb = _segmentos(a), _segmentos(b)
            if _se_cruzam(_tira_o_comum(sa, sb), _tira_o_comum(sb, sa)):
                defeitos.append(f"as setas {a['nome']} e {b['nome']} se cruzam")
    for s in setas:
        segs = _segmentos(s)
        for el, props in s["textos"]:
            r = _caixa_do_texto(el, props)
            if r and segs:
                d = min(_dist_ret_seg(r, p, q) for p, q in segs)
                if d > DISTANCIA_ROTULO:
                    defeitos.append(f"rótulo '{_texto_de(el)}' a {d:.0f}px da seta {s['nome']}; "
                                    f"o teto é {DISTANCIA_ROTULO:g}px")

    caixas = _caixas(nos, largura, altura)
    for el, props, grupos in textos:
        r = _caixa_do_texto(el, props)
        if not r:
            continue
        grupo = next((g for c, g in reversed(grupos) if GRUPO_DE_CAIXA.search(c)), None)
        ax = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        for caixa, dono, poli in caixas:
            if grupo is not None and dono == id(grupo):
                continue
            if grupo is None and caixa[0] <= ax[0] <= caixa[2] and caixa[1] <= ax[1] <= caixa[3]:
                continue
            if _toca_poligono(r, poli):
                defeitos.append(f"texto '{_texto_de(el)}' invade uma caixa que não é a dele")
                break

    # cor fora dos tokens, efeito vedado e fio grosso
    fora_dos_tokens: dict[str, int] = {}
    efeitos: set[str] = set()
    fios: set[float] = set()
    familias_usadas: set[int] = set()
    for el in root.iter():
        tag = _tag(el)
        if tag in TAGS_DE_EFEITO:
            efeitos.add(tag)
        props = _props(el)
        if "filter" in props and props["filter"].strip().lower() != "none":
            efeitos.add("filter")
        for chave in ("fill", "stroke", "stop-color", "color"):
            valor = props.get(chave)
            if valor is None or valor.strip().lower() in COR_LIVRE:
                continue
            if valor.strip().lower().startswith("url("):
                efeitos.add("gradiente")
                continue
            c = _cor_normal(valor)
            if c is None:
                fora_dos_tokens[valor.strip()] = fora_dos_tokens.get(valor.strip(), 0) + 1
            elif c not in paleta:
                fora_dos_tokens[c] = fora_dos_tokens.get(c, 0) + 1
            if chave == "stroke" and c in strokes_de_familia:
                familias_usadas.add(strokes_de_familia[c])
        sw = _numero(props.get("stroke-width", ""))
        if sw is not None and sw > fio_max + 0.01:
            fios.add(sw)
    for cor_crua, n in sorted(fora_dos_tokens.items()):
        defeitos.append(f"cor {cor_crua} fora dos tokens ({n} uso{'s' if n > 1 else ''})")
    for ef in sorted(efeitos):
        defeitos.append(f"efeito vedado no SVG: {ef}")
    for sw in sorted(fios):
        defeitos.append(f"fio de {sw:g}px mais grosso que o contorno de {fio_max:g}px")
    if len(familias_usadas) > 4:
        defeitos.append(f"{len(familias_usadas)} famílias de cor na figura; o teto é 4")

    if plano:
        nomes = {e.get("nome", "").strip() for e in plano.get("entidades", []) if e.get("nome")}
        for el, props, _ in textos:
            txt = _texto_de(el)
            if txt in nomes:
                peso = props.get("font-weight", "").strip().lower()
                if peso not in PESOS_DE_ROTULO:
                    defeitos.append(f"rótulo '{txt}' em peso regular; o rótulo de caixa pede semibold")
    return defeitos


def checar_plano_svg(caminho_plano: str | Path, caminho_svg: str | Path) -> tuple[int, list[str]]:
    """Compara o plano com o SVG. Devolve (0, []) sem defeito e (1, defeitos) com."""
    p_plano, p_svg = Path(caminho_plano), Path(caminho_svg)
    if not p_plano.is_file():
        return 1, [f"arquivo de plano não encontrado: {caminho_plano}"]
    if not p_svg.is_file():
        return 1, [f"arquivo SVG não encontrado: {caminho_svg}"]
    try:
        plano = json.loads(p_plano.read_text(encoding="utf-8"))
    except Exception as e:
        return 1, [f"falha ao ler plano JSON: {e}"]
    try:
        svg_texto = p_svg.read_text(encoding="utf-8")
        ET.fromstring(re.sub(r'\sxmlns="[^"]+"', "", svg_texto, count=1))
    except Exception as e:
        return 1, [f"falha ao ler o SVG: {e}"]
    defeitos = checar_svg(svg_texto, plano)  # sem tokens.css, FileNotFoundError sai 3 no main
    return (1 if defeitos else 0), defeitos


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print("uso: diagrama checar <plano.json> <figura.svg>", file=sys.stderr)
        return 2
    try:
        cod, defeitos = checar_plano_svg(argv[0], argv[1])
    except FileNotFoundError as e:
        print(f"diagrama checar: {e}", file=sys.stderr)
        return 3
    if cod != 0:
        for d in defeitos:
            print(f"defeito: {d}", file=sys.stderr)
        return 1
    print("checagem estrutural: 0 defeitos")
    return 0
