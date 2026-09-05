#!/usr/bin/env python3
"""diagrama — gera figura de arquitetura a partir de um modelo em texto, pela régua
de figura do DS (platafirma-arquitetura/design/diagramas.md §2-§3).

Uma fonte (o modelo, JSON), duas vistas:
  engenharia — estilo provedor de nuvem: caixa branca, glifo de família no canto, zona com fio
  diretoria  — estilo C4: caixa cheia na cor da família, rótulo de tipo, fronteira do sistema

Cor, tipo e fio vêm de platafirma-ui/src/tokens.css em tempo de geração — nenhum
primitivo mora aqui. Cor é FIXA por categoria técnica (family-1..8); teto de quatro
categorias por figura é conferido e trava a geração.

uso: gerar.py <modelo.json> [--vista engenharia|diretoria|ambas] [--saida DIR] [--png]
                             [--tokens CAMINHO]
"""
import argparse, json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parents[3]          # ~/AI
TOKENS = RAIZ / "platafirma-ui" / "src" / "tokens.css"

# catálogo — design/diagramas.md §3 (família fixa por categoria)
CATEGORIA = {
    "persistencia": 1, "servico": 2, "superficie": 3, "porta": 4,
    "conhecimento": 5, "host": 6, "mensageria": 7, "identidade": 8,
}
ROTULO_C4 = {
    "persistencia": "persistência", "servico": "serviço", "superficie": "superfície",
    "porta": "porta", "conhecimento": "conhecimento", "host": "host",
    "mensageria": "mensageria", "identidade": "identidade",
}
GLIFO_DE_TIPO = {"verbo": "⚙"}   # tipo com glifo próprio dentro da família (§3)

# ---------------------------------------------------------------- tokens
def carregar_tokens(caminho):
    """Lê --platafirma-*: valor; a 1ª ocorrência vence (tema claro). Resolve var() e light-dark()."""
    bruto = {}
    for m in re.finditer(r"--platafirma-([a-z0-9-]+)\s*:\s*([^;]+);", caminho.read_text(encoding="utf-8")):
        bruto.setdefault(m.group(1), m.group(2).strip())
    def resolver(v, prof=0):
        if prof > 12:
            raise ValueError(f"token circular: {v}")
        v = v.strip()
        m = re.match(r"light-dark\((.*)\)$", v)
        if m:
            v = m.group(1).split(",")[0]
        m = re.match(r"var\(--platafirma-([a-z0-9-]+)\)$", v.strip())
        if m:
            return resolver(bruto[m.group(1)], prof + 1)
        return v.strip().strip("'\"")
    class T(dict):
        def __missing__(self, k):
            raise KeyError(f"token ausente em tokens.css: --platafirma-{k}")
    t = T()
    for k in bruto:
        try:
            t[k] = resolver(bruto[k])
        except (KeyError, ValueError):
            pass
    return t

def px(v):
    """px ou rem (1rem = 16px, base do DS)."""
    v = v.strip()
    if v.endswith("rem"):
        return float(v[:-3]) * 16
    return float(v.replace("px", ""))

def tema(t):
    fam = {}
    for n in range(1, 9):
        fam[n] = dict(bg=t[f"family-{n}-bg"], zone=t[f"family-{n}-zone"], bd=t[f"family-{n}-bd"],
                      ink=t[f"family-{n}-fg"], stroke=t[f"family-{n}-stroke"], glifo=t[f"family-{n}-glyph"])
    return dict(
        fonte=t.get("font-family-sans", "'Inter', system-ui, sans-serif"),
        ink=t["diagram-stroke"], body=t["fg-body"], muted=t["fg-muted"],
        surface=t["bg-surface"], border=t["border-default"], border_strong=t["border-strong"],
        label=px(t["diagram-label-size"]), label_w=t["diagram-label-weight"],
        body_sz=px(t["diagram-annotation-size"]), body_w=t["diagram-body-weight"],
        fio=px(t["diagram-border-width"]), raio=px(t["radius-md"]), fam=fam,
    )

# ---------------------------------------------------------------- modelo
def validar(m):
    cats = set()
    for c in m["caixas"]:
        if "cadeira" in c:
            continue
        if c["categoria"] not in CATEGORIA:
            sys.exit(f"categoria desconhecida em {c['id']}: {c['categoria']} (catálogo: {', '.join(CATEGORIA)})")
        cats.add(c["categoria"])
    for z in m.get("zonas", []):
        if z.get("categoria") and z["categoria"] not in CATEGORIA:
            sys.exit(f"categoria desconhecida na zona {z['id']}: {z['categoria']}")
        if z.get("categoria"):
            cats.add(z["categoria"])
    if len(cats) > 4:
        sys.exit(f"figura com {len(cats)} categorias ({', '.join(sorted(cats))}) — teto é quatro (§3). Corta a figura ou junta caixas.")
    return cats

# ---------------------------------------------------------------- svg
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")

def caminho(pts):
    return "M " + " L ".join(f"{x} {y}" for x, y in pts)

class Svg:
    def __init__(self, tm, W, H, seta, fundo):
        self.tm, self.W, self.H = tm, W, H
        self.o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
                  f'font-family="{tm["fonte"]}"><defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" '
                  f'markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="{seta}"/>'
                  f'</marker></defs><rect width="{W}" height="{H}" fill="{fundo}"/>']
    def texto(self, x, y, s, size, weight, fill, anchor="start"):
        self.o.append(f'<text x="{x}" y="{y}" font-size="{size:g}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')
    def rect(self, x, y, w, h, fill, stroke, sw, rx=0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx:g}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:g}"{d}/>')
    def arestas(self, arestas, cor, dash=None):
        tm = self.tm
        for a in arestas:
            pts = [tuple(p) for p in a["pontos"]]
            d = f' stroke-dasharray="{dash}"' if dash else ""
            self.o.append(f'<path d="{caminho(pts)}" fill="none" stroke="{cor}" stroke-width="{tm["fio"]:g}"{d} marker-end="url(#seta)"/>')
            r = a.get("rotulo")
            if r:
                (x1, y1), (x2, y2) = pts[0], pts[1]
                if x1 == x2:
                    self.texto(x1 + 10, (y1 + y2) / 2 + 5, r, tm["body_sz"], tm["body_w"], tm["body"])
                else:
                    self.texto((x1 + x2) / 2, y1 - 10, r, tm["body_sz"], tm["body_w"], tm["body"], "middle")
    def fim(self):
        return "\n".join(self.o + ["</svg>"])

def familia(tm, c):
    return tm["fam"][CATEGORIA[c["categoria"]]]

def glifo(tm, c):
    return GLIFO_DE_TIPO.get(c.get("tipo"), familia(tm, c)["glifo"])

def vista_engenharia(m, tm):
    s = Svg(tm, m["largura"], m["altura"], tm["ink"], tm["surface"])
    for z in m.get("zonas", []):
        f = tm["fam"][CATEGORIA[z["categoria"]]]
        s.rect(z["x"], z["y"], z["w"], z["h"], f["zone"], f["bd"], tm["fio"], tm["raio"])
        s.texto(z["x"] + 14, z["y"] + 24, f'{f["glifo"]} {z["nome"]}', tm["label"], tm["label_w"], f["ink"])
    s.arestas(m.get("arestas", []), tm["ink"])
    for c in m["caixas"]:
        f = familia(tm, c); x, y, w, h = c["x"], c["y"], c["w"], c["h"]
        s.rect(x, y, w, h, tm["surface"], tm["border"], tm["fio"], tm["raio"])
        s.rect(x + 12, y + (h - 32) / 2, 32, 32, f["bg"], f["bd"], 1, tm["raio"])
        s.texto(x + 28, y + h / 2 + 6, glifo(tm, c), 15, 400, f["ink"], "middle")
        s.texto(x + 56, y + h / 2 - 3, c["titulo"], tm["label"], tm["label_w"], tm["ink"])
        s.texto(x + 56, y + h / 2 + 17, c.get("subtitulo", ""), tm["body_sz"], tm["body_w"], tm["muted"])
    return s.fim()

def vista_diretoria(m, tm):
    s = Svg(tm, m["largura"], m["altura"], tm["border_strong"], tm["surface"])
    fr = m.get("fronteira")
    if fr:
        s.rect(fr["x"], fr["y"], fr["w"], fr["h"], "none", tm["border_strong"], tm["fio"], tm["raio"], "8,5")
        s.texto(fr["x"] + 14, fr["y"] + fr["h"] - 12, fr["nome"], tm["label"], tm["label_w"], tm["ink"])
        s.texto(fr["x"] + 14 + 8 * len(fr["nome"]) + 12, fr["y"] + fr["h"] - 12, "[sistema de software]", tm["body_sz"], tm["body_w"], tm["muted"])
    for z in m.get("zonas", []):
        if z.get("fora_da_fronteira"):
            continue
        f = tm["fam"][CATEGORIA[z["categoria"]]]
        s.rect(z["x"], z["y"], z["w"], z["h"], f["zone"], f["bd"], tm["fio"], tm["raio"])
        s.texto(z["x"] + 14, z["y"] + 24, f'{f["glifo"]} {z["nome"]}', tm["label"], tm["label_w"], f["ink"])
    s.arestas(m.get("arestas", []), tm["border_strong"], "6,4")
    for c in m["caixas"]:
        f = familia(tm, c); x, y, w, h = c["x"], c["y"], c["w"], c["h"]
        s.rect(x, y, w, h, f["bg"], f["bd"], tm["fio"], tm["raio"])
        cx = x + w / 2
        tipo = f'[{c.get("tipo") or ROTULO_C4[c["categoria"]]}]'
        if h >= 76 and c.get("subtitulo"):
            s.texto(cx, y + h / 2 - 12, c["titulo"], tm["label"], tm["label_w"], f["ink"], "middle")
            s.texto(cx, y + h / 2 + 7, tipo, tm["body_sz"], tm["body_w"], f["ink"], "middle")
            s.texto(cx, y + h / 2 + 26, c["subtitulo"], tm["body_sz"], tm["body_w"], f["ink"], "middle")
        else:
            s.texto(cx, y + h / 2 - 4, c["titulo"], tm["label"], tm["label_w"], f["ink"], "middle")
            s.texto(cx, y + h / 2 + 16, tipo, tm["body_sz"], tm["body_w"], f["ink"], "middle")
    return s.fim()

VISTAS = {"engenharia": vista_engenharia, "diretoria": vista_diretoria}

# ---------------------------------------------------------------- medição
def medir(m, tm):
    """Rótulo cabe na caixa? Mede com a Inter instalada; sem ela, avisa e segue."""
    try:
        from PIL import ImageFont
    except ImportError:
        print("aviso: PIL ausente, encaixe não medido"); return []
    import glob
    def fonte(w):
        nome = {"600": "SemiBold", "500": "Medium"}.get(str(w), "Regular")
        cand = glob.glob(f"/usr/share/fonts/**/Inter-{nome}.*", recursive=True)
        return ImageFont.truetype(cand[0], 16) if cand else None
    fs, fb = fonte(tm["label_w"]), fonte(tm["body_w"])
    if not (fs and fb):
        print("aviso: Inter não instalada, encaixe não medido"); return []
    def larg(f, s, size):
        return f.getlength(s) * size / 16
    sobras = []
    for c in m["caixas"]:
        t, sub, w = c["titulo"], c.get("subtitulo", ""), c["w"]
        tipo = f'[{c.get("tipo") or ROTULO_C4[c["categoria"]]}]'
        if 56 + larg(fs, t, tm["label"]) + 10 > w: sobras.append(("engenharia", c["id"], t))
        if 56 + larg(fb, sub, tm["body_sz"]) + 10 > w: sobras.append(("engenharia", c["id"], sub))
        for s in (t, tipo, sub):
            if larg(fb if s != t else fs, s, tm["body_sz"] if s != t else tm["label"]) + 24 > w:
                sobras.append(("diretoria", c["id"], s))
    return sobras

def png(svg_path, W, H):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.set_content("<html><body style='margin:0'>" + svg_path.read_text() + "</body></html>")
        pg.screenshot(path=str(svg_path.with_suffix(".png")))
        b.close()

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modelo"); ap.add_argument("--vista", default="ambas", choices=["engenharia", "diretoria", "ambas"])
    ap.add_argument("--saida", default="."); ap.add_argument("--png", action="store_true", help="também PNG a 2x (só para slide)")
    ap.add_argument("--tokens", default=str(TOKENS))
    a = ap.parse_args()
    m = json.loads(pathlib.Path(a.modelo).read_text(encoding="utf-8"))
    validar(m)
    tm = tema(carregar_tokens(pathlib.Path(a.tokens)))
    saida = pathlib.Path(a.saida); saida.mkdir(parents=True, exist_ok=True)
    nome = pathlib.Path(a.modelo).stem
    for v in (["engenharia", "diretoria"] if a.vista == "ambas" else [a.vista]):
        alvo = saida / f"{nome}.{v}.svg"
        alvo.write_text(VISTAS[v](m, tm), encoding="utf-8")
        print("escreveu", alvo)
        if a.png:
            png(alvo, m["largura"], m["altura"]); print("escreveu", alvo.with_suffix(".png"))
    sobras = medir(m, tm)
    if sobras:
        print("SOBRA — rótulo não cabe na caixa:")
        for s in sobras: print("  ", *s)
        sys.exit(1)
    print("encaixe: tudo cabe")

if __name__ == "__main__":
    main()
