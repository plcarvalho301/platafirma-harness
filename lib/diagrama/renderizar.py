"""Renderização da peça diagrama: a fonte vira SVG pela grade, e o PNG sai do mesmo SVG.

A posição de cada caixa vem da fonte (faixa, coluna e ordem); a grade calcula as coordenadas, roteia as
setas e pinta com os tokens. O PNG é a prévia do SVG, para o crítico e para o dono ver na conversa.
"""
from __future__ import annotations

from functools import lru_cache
import glob
import html
import json
import math
from pathlib import Path
import re
import sys

import jsonschema

from diagrama import grade, medida

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "skills" / "diagrama" / "fonte.schema.json"
PNG_MAX = 1568
PESOS_INTER = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}


def carregar_schema() -> dict:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Esquema de fonte não encontrado em {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validar_fonte(dados: dict) -> list[str]:
    validador = jsonschema.Draft7Validator(carregar_schema())
    erros = []
    for err in validador.iter_errors(dados):
        campo = ".".join(str(p) for p in err.path) or "raiz"
        erros.append(f"campo '{campo}': {err.message}")
    return erros


def _attrs(tag: str) -> dict[str, str]:
    return dict(re.findall(r'([a-zA-Z_:][-a-zA-Z0-9_.:]*)="([^"]*)"', tag))


def _arco_svg(x1: float, y1: float, rx: float, ry: float, rot: float,
              large: int, sweep: int, x2: float, y2: float, passos: int = 20) -> list[tuple[float, float]]:
    if rx <= 0 or ry <= 0 or (x1 == x2 and y1 == y2):
        return [(x2, y2)]
    phi = math.radians(rot)
    c_phi, s_phi = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = c_phi * dx + s_phi * dy
    y1p = -s_phi * dx + c_phi * dy
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = max(0.0, rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p)
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    fator = math.sqrt(num / den) if den > 0 else 0.0
    if bool(large) == bool(sweep):
        fator = -fator
    cxp = fator * (rx * y1p / ry)
    cyp = fator * (-ry * x1p / rx)
    cx = c_phi * cxp - s_phi * cyp + (x1 + x2) / 2.0
    cy = s_phi * cxp + c_phi * cyp + (y1 + y2) / 2.0

    def angulo(ux: float, uy: float, vx: float, vy: float) -> float:
        dot = ux * vx + uy * vy
        n = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, dot / n))) if n > 0 else 0.0
        return -a if (ux * vy - uy * vx) < 0 else a

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    theta1 = angulo(1.0, 0.0, ux, uy)
    dtheta = angulo(ux, uy, vx, vy)
    if not sweep and dtheta > 0:
        dtheta -= 2.0 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2.0 * math.pi
    pts = []
    for i in range(1, passos + 1):
        t = theta1 + dtheta * (i / passos)
        px, py = rx * math.cos(t), ry * math.sin(t)
        pts.append((c_phi * px - s_phi * py + cx, s_phi * px + c_phi * py + cy))
    return pts


def _subcaminhos_de_path(d: str) -> list[list[tuple[float, float]]]:
    tokens = re.findall(r"[MLHVAZmlhvaz]|-?\d+(?:\.\d+)?", d)
    subcaminhos: list[list[tuple[float, float]]] = []
    atual: list[tuple[float, float]] = []
    i, cmd = 0, ""
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in ("Z", "z"):
                if atual and atual[-1] != atual[0]:
                    atual.append(atual[0])
                continue
        if cmd == "M":
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            atual = [(x, y)]
            subcaminhos.append(atual)
            cmd = "L"
        elif cmd == "L":
            atual.append((float(tokens[i]), float(tokens[i + 1])))
            i += 2
        elif cmd == "H":
            atual.append((float(tokens[i]), atual[-1][1]))
            i += 1
        elif cmd == "V":
            atual.append((atual[-1][0], float(tokens[i])))
            i += 1
        elif cmd == "A":
            rx, ry, rot = float(tokens[i]), float(tokens[i + 1]), float(tokens[i + 2])
            large, sweep = int(float(tokens[i + 3])), int(float(tokens[i + 4]))
            x2, y2 = float(tokens[i + 5]), float(tokens[i + 6])
            i += 7
            x1, y1 = atual[-1]
            atual.extend(_arco_svg(x1, y1, rx, ry, rot, large, sweep, x2, y2))
        else:
            i += 1
    return subcaminhos


def _subcaminhos_da_forma(tipo: str, attrs: dict[str, str]) -> list[list[tuple[float, float]]]:
    if tipo == "path":
        return _subcaminhos_de_path(attrs.get("d", ""))
    if tipo == "line":
        return [[(float(attrs.get("x1", 0)), float(attrs.get("y1", 0))),
                 (float(attrs.get("x2", 0)), float(attrs.get("y2", 0)))]]
    if tipo == "polygon":
        pts = [(float(a), float(b)) for a, b in re.findall(r"(-?[\d.]+)[,\s]+(-?[\d.]+)", attrs.get("points", ""))]
        return [pts + [pts[0]]] if pts else []
    if tipo == "ellipse":
        cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
        rx, ry = float(attrs.get("rx", 0)), float(attrs.get("ry", 0))
        n = 64
        return [[(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
                 for i in range(n + 1)]]
    if tipo == "rect":
        x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
        w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
        r = min(float(attrs.get("rx", 0)), w / 2.0, h / 2.0)
        if r <= 0:
            return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]]
        pts: list[tuple[float, float]] = [(x + r, y)]
        cantos = [
            ((x + w - r, y), (x + w - r, y + r), -math.pi / 2, 0.0),
            ((x + w, y + h - r), (x + w - r, y + h - r), 0.0, math.pi / 2),
            ((x + r, y + h), (x + r, y + h - r), math.pi / 2, math.pi),
            ((x, y + r), (x + r, y + r), math.pi, 1.5 * math.pi),
        ]
        for reta, (cx, cy), a0, a1 in cantos:
            pts.append(reta)
            for k in range(1, 7):
                ang = a0 + (a1 - a0) * (k / 6.0)
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return [pts]
    return []


def _cortar_em_tracos(subcaminhos: list[list[tuple[float, float]]], padrao: list[float]) -> str:
    if not padrao or sum(padrao) <= 0:
        return ""
    if len(padrao) % 2 == 1:
        padrao = padrao * 2
    partes: list[str] = []
    for pts in subcaminhos:
        if len(pts) < 2:
            continue
        idx = 0
        resta = padrao[0]
        traco_atual: list[tuple[float, float]] = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            seg = math.hypot(bx - ax, by - ay)
            if seg <= 1e-6:
                continue
            ux, uy = (bx - ax) / seg, (by - ay) / seg
            px, py = ax, ay
            falta = seg
            while falta > 1e-6:
                passo = min(falta, resta)
                nx, ny = px + ux * passo, py + uy * passo
                if idx % 2 == 0:
                    if not traco_atual:
                        traco_atual = [(px, py), (nx, ny)]
                    else:
                        traco_atual.append((nx, ny))
                px, py = nx, ny
                falta -= passo
                resta -= passo
                if resta <= 1e-6:
                    if idx % 2 == 0 and traco_atual:
                        partes.append("M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in traco_atual))
                        traco_atual = []
                    idx = (idx + 1) % len(padrao)
                    resta = padrao[idx]
        if traco_atual:
            partes.append("M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in traco_atual))
    return "".join(partes)


def _expandir_tracejado(m: re.Match) -> str:
    tag = m.group(0)
    tipo = m.group(1)
    attrs = _attrs(tag)
    bruto = attrs.get("stroke-dasharray", "")
    padrao = [float(x) for x in re.split(r"[\s,]+", bruto.strip()) if x]
    d_traco = _cortar_em_tracos(_subcaminhos_da_forma(tipo, attrs), padrao)
    if not d_traco:
        return tag
    stroke = attrs.get("stroke", "#18181B")
    sw = attrs.get("stroke-width", "1.5")
    fill = attrs.get("fill", "none")
    caminho_borda = f'<path d="{d_traco}" fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
    if fill == "none":
        return caminho_borda
    sem_dasharray = re.sub(r'\s*stroke-dasharray="[^"]*"', "", tag)
    sem_borda = re.sub(r'\bstroke="[^"]*"', 'stroke="none"', sem_dasharray)
    return sem_borda + caminho_borda


def para_o_mupdf(svg: str) -> str:
    """O SVG como o pintor da prévia o lê. O MuPDF não herda a família de letra do elemento de fora, então
    cada texto recebe a da raiz; ele só tem o peso regular e o negrito, então o médio vai para o regular
    e o semibold para o negrito; e não interpreta stroke-dasharray, então a borda ou seta tracejada vira
    subcaminhos de traço e vão."""
    familia = re.search(r'<svg\b[^>]*\sfont-family="([^"]*)"', svg)
    if familia:
        svg = re.sub(r"<text(?![^>]*font-family=)", f'<text font-family="{familia.group(1)}"', svg)
    svg = re.sub(r"<(path|rect|polygon|ellipse|line)\b[^>]*\bstroke-dasharray=\"[^\"]+\"[^>]*/>",
                 _expandir_tracejado, svg)
    return re.sub(r'font-weight="(\d+)"',
                  lambda m: 'font-weight="bold"' if int(m.group(1)) >= 600 else 'font-weight="normal"', svg)


@lru_cache(maxsize=8)
def _caminho_inter(peso: int) -> str | None:
    chave = min(PESOS_INTER, key=lambda p: abs(p - peso))
    nome = PESOS_INTER[chave]
    achados = sorted(glob.glob(f"/usr/share/fonts/**/Inter-{nome}.*", recursive=True))
    return achados[0] if achados else None


def _cor_rgb(hex_cor: str) -> tuple[float, float, float]:
    h = hex_cor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (0.094, 0.094, 0.106)
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def _extrair_textos(svg: str) -> list[dict]:
    saida: list[dict] = []
    for m in re.finditer(r"<text\b([^>]*)>(.*?)</text>", svg, flags=re.DOTALL):
        t_attrs = _attrs(m.group(1))
        corpo = m.group(2)
        tamanho = float(t_attrs.get("font-size", "12"))
        peso_str = t_attrs.get("font-weight", "400")
        peso = 700 if peso_str == "bold" else (400 if peso_str == "normal" else int(peso_str))
        cor = _cor_rgb(t_attrs.get("fill", "#18181B"))
        ancora = t_attrs.get("text-anchor", "start")
        spans = list(re.finditer(r"<tspan\b([^>]*)>(.*?)</tspan>", corpo, flags=re.DOTALL))
        if spans:
            for sp in spans:
                s_attrs = _attrs(sp.group(1))
                txt = html.unescape(re.sub(r"<[^>]+>", "", sp.group(2)))
                if not txt:
                    continue
                x = float(s_attrs.get("x", t_attrs.get("x", "0")))
                y = float(s_attrs.get("y", t_attrs.get("y", "0")))
                saida.append({"x": x, "y": y, "texto": txt, "tamanho": tamanho,
                              "peso": peso, "cor": cor, "ancora": ancora})
        else:
            txt = html.unescape(re.sub(r"<[^>]+>", "", corpo))
            if txt:
                x = float(t_attrs.get("x", "0"))
                y = float(t_attrs.get("y", "0"))
                saida.append({"x": x, "y": y, "texto": txt, "tamanho": tamanho,
                              "peso": peso, "cor": cor, "ancora": ancora})
    return saida


def png_do_svg(svg: str, max_dim: int = PNG_MAX) -> bytes:
    """O PNG do SVG, a 2x, sem passar de `max_dim` px no lado maior. Pinta as formas pelo MuPDF e os
    textos com a Inter instalada no host, para a largura no PNG bater com a que o leitor vê no SVG."""
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    textos = _extrair_textos(svg)
    svg_formas = re.sub(r"<text\b[^>]*>.*?</text>", "", para_o_mupdf(svg), flags=re.DOTALL)
    doc_svg = pymupdf.open(stream=svg_formas.encode("utf-8"), filetype="svg")
    pdf = pymupdf.open("pdf", doc_svg.convert_to_pdf())
    pagina = pdf[0]
    fontes: dict[int, object] = {}
    for item in textos:
        peso = item["peso"]
        if peso not in fontes:
            arq = _caminho_inter(peso)
            fontes[peso] = pymupdf.Font(fontfile=arq) if arq else pymupdf.Font("hebo" if peso >= 600 else "helv")
        fonte = fontes[peso]
        txt, tam = item["texto"], item["tamanho"]
        larg = fonte.text_length(txt, fontsize=tam)
        x = item["x"]
        if item["ancora"] == "middle":
            x -= larg / 2.0
        elif item["ancora"] == "end":
            x -= larg
        tw = pymupdf.TextWriter(pagina.rect)
        tw.append((x, item["y"]), txt, font=fonte, fontsize=tam)
        tw.write_text(pagina, color=item["cor"])
    escala = min(2.0, max_dim / max(pagina.rect.width, pagina.rect.height))
    pix = pagina.get_pixmap(matrix=pymupdf.Matrix(escala, escala), alpha=False)
    return pix.tobytes("png")


def renderizar_dados(dados: dict) -> str:
    """A fonte conferida vira o SVG. Falta de posição e choque de célula saem com o nome da caixa."""
    if isinstance(dados, dict) and isinstance(dados.get("elementos"), list):
        grade.ler_fonte(dados)
    erros = validar_fonte(dados)
    if erros:
        raise ValueError(f"Fonte fora do esquema: {'; '.join(erros)}")
    return grade.desenhar(dados)


def renderizar_arquivo(caminho_fonte: str | Path, saida_dir: str | Path | None = None) -> tuple[Path, Path]:
    caminho = Path(caminho_fonte).resolve()
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de fonte não encontrado: {caminho}")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"JSON inválido em {caminho}: {e}")
    svg = renderizar_dados(dados)
    destino = Path(saida_dir).resolve() if saida_dir else caminho.parent
    destino.mkdir(parents=True, exist_ok=True)
    stem = caminho.stem[:-6] if caminho.stem.endswith(".fonte") else caminho.stem
    svg_path, png_path = destino / f"{stem}.svg", destino / f"{stem}.png"
    svg_path.write_text(svg, encoding="utf-8")
    png_path.write_bytes(png_do_svg(svg))
    return svg_path, png_path


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("uso: diagrama renderizar <caminho_fonte> [--saida <dir>]", file=sys.stderr)
        return 2
    saida_dir = argv[2] if len(argv) >= 3 and argv[1] in ("--saida", "-o") else None
    try:
        svg_path, png_path = renderizar_arquivo(argv[0], saida_dir)
        print(str(svg_path))
        print(str(png_path))
        return 0
    except ValueError as e:  # grade.ErroDeFonte é ValueError
        print(f"diagrama renderizar: erro: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"diagrama renderizar: falha: {e}", file=sys.stderr)
        return 3
