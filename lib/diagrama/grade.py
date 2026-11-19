"""A grade: quem desenha diz a faixa, a coluna e a ordem de cada caixa; a grade calcula as coordenadas,
roteia as setas em ângulo reto e escreve o SVG com os tokens do design system.

O tamanho de cada texto é o do papel dele na hierarquia de tipo da platafirma-ui: o título da figura no
papel de bloco, o nome de faixa e o título de caixa no de texto, o subtítulo, o rótulo de seta
no de metadado. A grade não escreve número de fonte: lê o token do papel.

A figura tem até 760 px de largura e a altura que o conteúdo pede. Uma unidade do SVG é um pixel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import html
import math

from diagrama import medida
from diagrama import tokens as tk

LARGURA = 760
LADOS = ("cima", "baixo", "esquerda", "direita")
_NORMAL = {"cima": (0, -1), "baixo": (0, 1), "esquerda": (-1, 0), "direita": (1, 0)}

# Custo da rota: o cruzamento é a estética que mais pesa na leitura; dobra pesa menos; comprimento, menos ainda.
CUSTO_CRUZAR = 5000.0
CUSTO_SOBREPOR = 3000.0
CUSTO_DOBRA = 40.0
CUSTO_RENTE = 0.5      # por pixel que a seta corre rente à borda de caixa ou de zona
PERTO = 8.0            # setas alheias mais perto que isso parecem se tocar
PERTO_NA_LINHA = 40.0  # na mesma linha, a seta alheia mais perto que isso parece continuar a outra
DESCONTO_FEIXE = 0.1   # por pixel que a seta corre junto com outra do mesmo feixe
CUSTO_PORTA_DE_NOVO = 120.0  # a porta que já solta (ou recebe) uma seta solta outra: o feixe custa pouco
CUSTO_LADO = {"natural": 0.0, "lateral": 60.0, "oposto": 200.0}
DISTANCIA_ROTULO = 24.0


class ErroDeFonte(ValueError):
    """A fonte não se desenha como está; a mensagem diz que caixa e o que mudar."""


# ----------------------------------------------------------------------------------------------- estilo

@dataclass
class Estilo:
    margem: float
    calha: float
    vao_pilha: float
    vao_faixa: float
    folga: float
    pad_h: float
    pad_v: float
    coluna_max: float
    raio: float
    fio: float
    fio_fino: float
    entrelinha: float
    fonte: str
    bloco: float
    texto: float
    metadado: float
    peso_rotulo: str
    peso_corpo: str
    peso_faixa: str
    tinta: str
    corpo: str
    quieto: str
    titulo_cor: str
    fundo: str
    recuado: str
    separador: str
    familias: dict
    cadeiras: dict

    @classmethod
    def dos_tokens(cls, t: dict[str, str] | None = None) -> "Estilo":
        t = t or tk.carregar()
        r = lambda n: tk.resolver(n, t)  # noqa: E731
        px = lambda n: tk.px(r(n))  # noqa: E731
        familias = {cat: tk.familia(t, n) for cat, n in tk.FAMILIA_DA_CATEGORIA.items()}
        cadeiras = {n[len("cadeira-"):]: tk.normaliza_cor(r(n)) for n in t
                    if n.startswith("cadeira-") and tk.normaliza_cor(r(n))}
        return cls(
            margem=px("space-5"), calha=px("space-6"), vao_pilha=px("space-5"), vao_faixa=px("space-6"),
            folga=px("space-2"), pad_h=px("space-3"), pad_v=px("space-3"), coluna_max=4 * px("space-7"),
            raio=px("radius-md"), fio=px("diagram-border-width"), fio_fino=px("line-hairline"),
            entrelinha=float(r("leading-tight")), fonte=r("family-sans").replace("'", ""),
            bloco=px("text-section"), texto=px("text-body"), metadado=px("text-meta"),
            peso_rotulo=r("diagram-label-weight"), peso_corpo=r("diagram-body-weight"), peso_faixa=r("weight-bold"),
            tinta=tk.cor("diagram-stroke", t), corpo=tk.cor("fg-body", t), quieto=tk.cor("fg-muted", t),
            titulo_cor=tk.cor("fg-default", t), fundo=tk.cor("bg-surface", t), recuado=tk.cor("bg-sunken", t),
            separador=tk.cor("border-default", t), familias=familias, cadeiras=cadeiras,
        )

    def linha(self, tamanho: float) -> float:
        return tamanho * self.entrelinha

    def base(self, topo: float, tamanho: float) -> float:
        """A linha de base do texto cuja linha começa em `topo`."""
        alto = medida.subida(tamanho) + medida.descida(tamanho)
        return topo + (self.linha(tamanho) - alto) / 2 + medida.subida(tamanho)


# ----------------------------------------------------------------------------------------------- modelo

@dataclass
class Caixa:
    id: str
    titulo: str
    subtitulo: str
    tipo: str
    categoria: str | None
    cadeira: str | None
    zona: str | None
    faixa: str
    coluna: int
    colunas: int
    ordem: int
    forma: str = "retangulo"
    tracejada: bool = False  # a caixa é de outra camada: o fio sai tracejado
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    linhas_titulo: list = field(default_factory=list)
    linhas_sub: list = field(default_factory=list)
    centros: list = field(default_factory=list)  # o x do meio de cada coluna que a caixa ocupa

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def porta(self, lado: str) -> tuple[float, float]:
        return {"cima": (self.cx, self.y), "baixo": (self.cx, self.y + self.h),
                "esquerda": (self.x, self.cy), "direita": (self.x + self.w, self.cy)}[lado]

    def portas(self, lado: str) -> list[tuple[float, float]]:
        """O meio do lado. A caixa de canto reto que ocupa várias colunas tem, em cima e embaixo, uma porta
        no meio de cada coluna: a seta da caixa de cima ou de baixo chega reta, sem correr até o meio."""
        if lado in ("cima", "baixo") and len(self.centros) > 1 and self.forma != "losango" and self.forma != "elipse":
            y = self.y if lado == "cima" else self.y + self.h
            return [(x, y) for x in self.centros]
        return [self.porta(lado)]


@dataclass
class Seta:
    indice: int
    de: str
    para: str
    rotulo: str
    sai: str | None
    chega: str | None
    tracejada: bool = False  # a ligação é de outra camada: a linha sai tracejada, e o rótulo é opcional
    pontos: list = field(default_factory=list)
    rotulo_linhas: list = field(default_factory=list)
    rotulo_pos: tuple | None = None  # (x, topo, ancora)


@dataclass
class Zona:
    id: str
    nome: str
    faixa: str
    categoria: str | None
    cadeira: str | None
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    tracejada: bool = False

    centros = ()
    cx = Caixa.cx
    cy = Caixa.cy
    porta = Caixa.porta
    portas = Caixa.portas


@dataclass
class Cabeca:
    """O nome de uma zona ou de uma faixa, escrito no alto dela. Ele vai no primeiro trecho do alto que
    nenhuma seta atravessa, a começar da esquerda, e quebra em até `n` linhas."""
    chave: tuple       # ("zona", id) ou ("faixa", id)
    nome: str
    peso: str
    x0: float          # de onde a onde, em x, o nome pode ir
    x1: float
    topo: float
    n: int
    linhas: list = field(default_factory=list)
    x: float = 0.0

    def retangulo(self, e: "Estilo") -> tuple:
        largura = max(medida.largura(l, e.texto, self.peso) for l in self.linhas)
        return (self.x - 2, self.topo - 2, self.x + largura + 2, self.topo + len(self.linhas) * e.linha(e.texto) + 2)


@dataclass
class Figura:
    largura: float
    altura: float
    titulo: str
    titulo_linhas: list
    faixas: list           # [(id, nome, topo, base_do_conteudo)]
    caixas: dict
    setas: list
    zonas: list
    separadores: list      # [y]
    estilo: Estilo
    calhas_x: list = field(default_factory=list)  # [(x0, x1)] de cada calha, da esquerda para a direita
    cabecas: dict = field(default_factory=dict)   # chave -> Cabeca
    baixo: float = 0.0                            # margem de baixo aberta para o rótulo da seta que passa por ali


# ----------------------------------------------------------------------------------------------- leitura

def _forma(el: dict) -> str:
    tipo = (el.get("tipo") or "").lower()
    if tipo == "decisao":
        return "losango"
    if tipo in ("inicio", "fim"):
        return "elipse"
    if tipo == "passo":
        return "arredondado"
    if tipo in ("banco", "database") or el.get("categoria") == "persistencia":
        return "cilindro"
    return "retangulo"


def ler_fonte(dados: dict) -> tuple[list, dict, list, list]:
    """Confere a fonte e devolve faixas, caixas, setas e zonas. A falta e o choque saem com o nome da caixa."""
    faixas = [(f["id"], f.get("nome", "")) for f in dados.get("faixas") or []]
    ids_faixa = [f for f, _ in faixas]
    if not faixas:
        raise ErroDeFonte("a fonte não declara faixas: cada caixa precisa de uma faixa")
    caixas: dict[str, Caixa] = {}
    for i, el in enumerate(dados.get("elementos") or []):
        nome = el.get("id") or f"elementos[{i}]"
        faltam = [c for c in ("faixa", "coluna", "ordem") if el.get(c) in (None, "")]
        if faltam:
            raise ErroDeFonte(f"a caixa '{nome}' não tem {', '.join(faltam)}")
        if el["faixa"] not in ids_faixa:
            raise ErroDeFonte(f"a caixa '{nome}' está na faixa '{el['faixa']}', que a fonte não declara")
        for campo in ("coluna", "ordem", "colunas"):
            v = el.get(campo, 1)
            if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                raise ErroDeFonte(f"a caixa '{nome}' tem {campo} {v!r}: tem de ser inteiro a partir de 1")
        if nome in caixas:
            raise ErroDeFonte(f"duas caixas com o id '{nome}'")
        caixas[nome] = Caixa(
            id=nome, titulo=str(el.get("titulo", nome)), subtitulo=str(el.get("subtitulo") or ""),
            tipo=str(el.get("tipo") or ""), categoria=el.get("categoria"), cadeira=el.get("cadeira"),
            zona=el.get("zona"), faixa=el["faixa"], coluna=el["coluna"], colunas=el.get("colunas", 1),
            ordem=el["ordem"], forma=_forma(el), tracejada=bool(el.get("tracejada")))
    _conferir_celulas(caixas)
    zonas = _ler_zonas(dados, caixas)
    pontas = set(caixas) | {z.id for z in zonas}
    setas = []
    for i, a in enumerate(dados.get("arestas") or []):
        for ponta in ("de", "para"):
            if a.get(ponta) not in pontas:
                raise ErroDeFonte(f"a seta {i + 1} ({a.get('de')} → {a.get('para')}) aponta a caixa "
                                  f"'{a.get(ponta)}', que a fonte não declara")
        if a["de"] == a["para"]:
            raise ErroDeFonte(f"a seta {i + 1} sai e chega na mesma caixa '{a['de']}'")
        rotulo = str(a.get("rotulo") or "").strip()
        tracejada = bool(a.get("tracejada"))
        if not rotulo and not tracejada:
            raise ErroDeFonte(f"a seta {i + 1} ({a['de']} → {a['para']}) não tem rótulo: só a seta tracejada "
                              f"dispensa o rótulo")
        setas.append(Seta(i, a["de"], a["para"], rotulo, a.get("sai"), a.get("chega"), tracejada))
    return faixas, caixas, setas, zonas


def _ler_zonas(dados: dict, caixas: dict) -> list:
    zonas = []
    for z in dados.get("zonas") or []:
        membros = [c for c in caixas.values() if c.zona == z["id"]]
        if not membros:
            raise ErroDeFonte(f"a zona '{z['id']}' não tem caixa")
        fora = [c.id for c in membros if c.faixa != z.get("faixa")]
        if fora:
            raise ErroDeFonte(f"a zona '{z['id']}' é da faixa '{z.get('faixa')}', e a caixa '{fora[0]}' está em "
                              f"outra: zona não atravessa faixa")
        zonas.append(Zona(z["id"], str(z.get("nome", "")), z["faixa"], z.get("categoria"), z.get("cadeira"),
                          tracejada=bool(z.get("tracejada"))))
    for c in caixas.values():
        if c.zona and c.zona not in {z.id for z in zonas}:
            raise ErroDeFonte(f"a caixa '{c.id}' está na zona '{c.zona}', que a fonte não declara")
    return zonas


def _conferir_celulas(caixas: dict[str, Caixa]) -> None:
    """Duas caixas não pedem a mesma célula: a mesma faixa, colunas que se tocam e a mesma pilha."""
    lista = list(caixas.values())
    for i, a in enumerate(lista):
        for b in lista[i + 1:]:
            if a.faixa != b.faixa:
                continue
            ra = range(a.coluna, a.coluna + a.colunas)
            rb = range(b.coluna, b.coluna + b.colunas)
            if not set(ra) & set(rb):
                continue
            mesma_pilha = a.coluna == b.coluna and a.colunas == b.colunas
            if not mesma_pilha or a.ordem == b.ordem:
                raise ErroDeFonte(f"as caixas '{a.id}' e '{b.id}' pedem a mesma célula da grade "
                                  f"(faixa '{a.faixa}', coluna {a.coluna}, ordem {a.ordem} e {b.ordem})")


# ----------------------------------------------------------------------------------------------- medidas

def _medir_caixa(c: Caixa, largura: float, e: Estilo) -> float:
    """Quebra o texto na largura da caixa e devolve a altura que ela pede."""
    def quebra(texto, tamanho, peso, maximo):
        linhas = medida.quebrar(texto, tamanho, peso, maximo)
        for l in linhas:
            if medida.largura(l, tamanho, peso) > maximo + 0.01:
                raise ErroDeFonte(f"a caixa '{c.id}' não cabe na coluna: «{l}» mede "
                                  f"{medida.largura(l, tamanho, peso):.0f} px e a coluna dá {maximo:.0f}; "
                                  f"dê mais colunas à caixa ou encurte o texto")
        return linhas

    if c.forma in ("losango", "elipse"):
        # o texto cabe no retângulo inscrito; quanto mais largo o texto, mais alta a forma. Tenta quebras
        # em larguras diferentes e fica com a que pede a forma mais baixa.
        a = largura / 2
        melhor = None
        for fator in ((0.85, 0.6, 0.45) if c.forma == "losango" else (0.95, 0.75, 0.55)):
            util = largura * fator - e.pad_h / 2
            try:
                lt = quebra(c.titulo, e.texto, e.peso_rotulo, util)
                ls = quebra(c.subtitulo, e.metadado, e.peso_corpo, util) if c.subtitulo else []
            except ErroDeFonte:
                if melhor is None and fator == (0.85 if c.forma == "losango" else 0.95):
                    raise
                continue
            th = len(lt) * e.linha(e.texto) + len(ls) * e.linha(e.metadado)
            tw = max([medida.largura(l, e.texto, e.peso_rotulo) for l in lt] +
                     [medida.largura(l, e.metadado, e.peso_corpo) for l in ls])
            r = min(0.95, (tw / 2 + e.pad_h / 4) / a)
            b = (th / 2) / (1 - r) if c.forma == "losango" else (th / 2) / math.sqrt(1 - r * r)
            alto = 2 * b + e.pad_v
            if melhor is None or alto < melhor[0]:
                melhor = (alto, lt, ls)
        alto, c.linhas_titulo, c.linhas_sub = melhor
        return alto
    util = largura - 2 * e.pad_h
    c.linhas_titulo = quebra(c.titulo, e.texto, e.peso_rotulo, util)
    c.linhas_sub = quebra(c.subtitulo, e.metadado, e.peso_corpo, util) if c.subtitulo else []
    alto = 2 * e.pad_v + len(c.linhas_titulo) * e.linha(e.texto)
    if c.linhas_sub:
        alto += e.folga / 2 + len(c.linhas_sub) * e.linha(e.metadado)
    if c.forma == "cilindro":
        alto += 2 * _ry(e)
    return alto


def _ry(e: Estilo) -> float:
    return e.folga * 0.75


def _arred(v: float) -> float:
    return round(v * 2) / 2


# ----------------------------------------------------------------------------------------------- layout

@dataclass
class _Ajuste:
    calhas: dict = field(default_factory=dict)      # índice da calha -> largura
    vaos_faixa: dict = field(default_factory=dict)  # índice do vão (entre faixa i e i+1) -> altura
    vaos_pilha: dict = field(default_factory=dict)  # faixa -> vão entre caixas empilhadas
    margens: dict = field(default_factory=dict)     # "esq", "dir" ou "baixo" -> medida a mais na margem
    cabecas: dict = field(default_factory=dict)     # chave da cabeça -> linhas reservadas para o nome


def _layout(dados: dict, e: Estilo, aj: _Ajuste) -> Figura:
    faixas, caixas, setas, zonas = ler_fonte(dados)
    ncol = max(c.coluna + c.colunas - 1 for c in caixas.values())
    # toda medida da grade cai em pixel inteiro, e o centro de caixa também: a rota e a checagem comparam
    # coordenadas, e meio pixel de arredondamento viraria um cruzamento que não existe
    calhas = [2 * math.ceil(aj.calhas.get(i, e.calha) / 2) for i in range(ncol - 1)]
    esq = e.margem + 2 * math.ceil(aj.margens.get("esq", 0) / 2)
    dir_ = e.margem + 2 * math.ceil(aj.margens.get("dir", 0) / 2)
    util = LARGURA - esq - dir_ - sum(calhas)
    col = 2 * math.floor(min(e.coluna_max, util / ncol) / 2)
    largura = esq + dir_ + ncol * col + sum(calhas)
    if col < 3 * e.pad_h:
        raise ErroDeFonte(f"{ncol} colunas não cabem em {LARGURA} px com as calhas que os rótulos pedem; "
                          f"tire colunas ou encurte os rótulos das setas")
    xs = []
    x = esq
    for i in range(ncol):
        xs.append(x)
        x += col + (calhas[i] if i < ncol - 1 else 0)

    def x_de(c: Caixa) -> tuple[float, float]:
        ini = xs[c.coluna - 1]
        fim = xs[c.coluna + c.colunas - 2] + col
        return ini, fim - ini

    for c in caixas.values():
        c.x, c.w = x_de(c)
        c.centros = [xs[i] + col / 2 for i in range(c.coluna - 1, c.coluna + c.colunas - 1)]
        c.h = 2 * math.ceil(_medir_caixa(c, c.w, e) / 2)
    # caixas de canto reto da mesma faixa ficam da mesma altura
    for fid, _ in faixas:
        retas = [c for c in caixas.values() if c.faixa == fid and c.forma in ("retangulo", "arredondado", "cilindro")]
        if retas:
            alto = max(c.h for c in retas)
            for c in retas:
                c.h = alto

    titulo_linhas = medida.quebrar(dados.get("titulo", ""), e.bloco, e.peso_rotulo, largura - 2 * e.margem)
    y = math.ceil(e.margem + len(titulo_linhas) * e.linha(e.bloco) + e.vao_faixa / 2)
    faixas_pos, separadores = [], []
    zonas_por_faixa = {f: [z for z in zonas if z.faixa == f] for f, _ in faixas}
    lh = e.linha(e.texto)
    # o nome da zona quebra na largura dela; a faixa reserva, no alto, as linhas do nome mais alto
    linhas_zona = {}
    for z in zonas:
        membros = [c for c in caixas.values() if c.zona == z.id]
        dentro = max(c.x + c.w for c in membros) - min(c.x for c in membros)
        linhas_zona[z.id] = aj.cabecas.get(("zona", z.id),
                                           len(medida.quebrar(z.nome, e.texto, e.peso_rotulo, dentro)))
    cabeca_da_faixa = {f: max([linhas_zona[z.id] for z in zs] or [0]) for f, zs in zonas_por_faixa.items()}
    cabecas = {}
    for i, (fid, nome) in enumerate(faixas):
        topo = y
        if i > 0 and nome:  # a faixa sem nome é só uma linha da grade: não leva fio que a separe
            separadores.append(y - math.ceil(aj.vaos_faixa.get(i - 1, e.vao_faixa) / 2))
        if nome:
            n = aj.cabecas.get(("faixa", fid), 1)
            cabecas[("faixa", fid)] = Cabeca(("faixa", fid), nome, e.peso_faixa, e.margem, largura - e.margem, topo, n)
            y = math.ceil(y + n * lh + e.folga)
        if zonas_por_faixa[fid]:
            y = math.ceil(y + cabeca_da_faixa[fid] * lh + e.folga + e.pad_h)
        vao = 2 * math.ceil(aj.vaos_pilha.get(fid, e.vao_pilha) / 2)
        pilhas: dict[tuple, list] = {}
        for c in caixas.values():
            if c.faixa == fid:
                pilhas.setdefault((c.coluna, c.colunas), []).append(c)
        alturas = {k: sum(c.h for c in v) + vao * (len(v) - 1) for k, v in pilhas.items()}
        alto = max(alturas.values()) if alturas else e.linha(e.texto)
        for k, pilha in pilhas.items():
            yy = y + (alto - alturas[k]) // 2
            for c in sorted(pilha, key=lambda c: c.ordem):
                c.y = yy
                yy += c.h + vao
        y += alto
        if zonas_por_faixa[fid]:
            y += e.pad_h
        faixas_pos.append((fid, nome, topo, y))
        y += 2 * math.ceil(aj.vaos_faixa.get(i, e.vao_faixa) / 2)
    altura = math.ceil(y - 2 * math.ceil(aj.vaos_faixa.get(len(faixas) - 1, e.vao_faixa) / 2) + e.margem
                       + 2 * math.ceil(aj.margens.get("baixo", 0) / 2))
    for z in zonas:
        membros = [c for c in caixas.values() if c.zona == z.id]
        x0 = min(c.x for c in membros) - e.pad_h
        x1 = max(c.x + c.w for c in membros) + e.pad_h
        y0 = min(c.y for c in membros) - e.pad_h - cabeca_da_faixa[z.faixa] * lh - e.folga
        y1 = max(c.y + c.h for c in membros) + e.pad_h
        x0, y0, x1, y1 = math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)
        z.x, z.y, z.w, z.h = x0, y0, x1 - x0, y1 - y0
        cabecas[("zona", z.id)] = Cabeca(("zona", z.id), z.nome, e.peso_rotulo, z.x + e.pad_h, z.x + z.w - e.pad_h,
                                         z.y + e.folga / 2, cabeca_da_faixa[z.faixa])
    calhas_x = [(xs[i] + col, xs[i + 1]) for i in range(ncol - 1)]
    return Figura(largura, altura, dados.get("titulo", ""), titulo_linhas, faixas_pos, caixas, setas, zonas,
                  separadores, e, calhas_x, cabecas, 2 * math.ceil(aj.margens.get("baixo", 0) / 2))


# ----------------------------------------------------------------------------------------------- rota

def _dentro(px_: float, py_: float, r: tuple) -> bool:
    return r[0] + 1e-6 < px_ < r[2] - 1e-6 and r[1] + 1e-6 < py_ < r[3] - 1e-6


def _corta(a: tuple, b: tuple, r: tuple) -> bool:
    """O segmento de eixo a-b passa pelo interior do retângulo r."""
    (x1, y1), (x2, y2) = a, b
    if abs(y1 - y2) < 1e-6:
        if not (r[1] + 1e-6 < y1 < r[3] - 1e-6):
            return False
        lo, hi = sorted((x1, x2))
        return min(hi, r[2]) - max(lo, r[0]) > 1e-6
    lo, hi = sorted((y1, y2))
    if not (r[0] + 1e-6 < x1 < r[2] - 1e-6):
        return False
    return min(hi, r[3]) - max(lo, r[1]) > 1e-6


def _cruza(a1, a2, b1, b2) -> bool:
    """Dois segmentos de eixo, um horizontal e um vertical, se cruzam por dentro dos dois."""
    ah = abs(a1[1] - a2[1]) < 1e-6
    bh = abs(b1[1] - b2[1]) < 1e-6
    if ah == bh:
        return False
    h1, h2, v1, v2 = (a1, a2, b1, b2) if ah else (b1, b2, a1, a2)
    y, x = h1[1], v1[0]
    return (min(h1[0], h2[0]) + 1e-6 < x < max(h1[0], h2[0]) - 1e-6 and
            min(v1[1], v2[1]) + 1e-6 < y < max(v1[1], v2[1]) - 1e-6)


def _atravessa(q, direcao: str, feitos: list) -> bool:
    """A rota que segue reta pelo nó `q` cruza ali uma seta já posta, que passa por ele de través. O trilho da
    seta posta é trilho da grade, e o cruzamento cai no nó, onde o teste de segmento não o vê."""
    for f1, f2, _, _ in feitos:
        if direcao == "h" and abs(f1[0] - f2[0]) < 1e-6 and abs(f1[0] - q[0]) < 1e-6:
            if min(f1[1], f2[1]) + 1e-6 < q[1] < max(f1[1], f2[1]) - 1e-6:
                return True
        if direcao == "v" and abs(f1[1] - f2[1]) < 1e-6 and abs(f1[1] - q[1]) < 1e-6:
            if min(f1[0], f2[0]) + 1e-6 < q[0] < max(f1[0], f2[0]) - 1e-6:
                return True
    return False


def _paralelas_perto(a1, a2, b1, b2) -> bool:
    """Dois segmentos de eixo paralelos, em linhas diferentes a menos de PERTO, lado a lado."""
    if abs(a1[0] - a2[0]) < 1e-6 and abs(b1[0] - b2[0]) < 1e-6:
        d, lo, hi = abs(a1[0] - b1[0]), max(min(a1[1], a2[1]), min(b1[1], b2[1])), min(max(a1[1], a2[1]), max(b1[1], b2[1]))
    elif abs(a1[1] - a2[1]) < 1e-6 and abs(b1[1] - b2[1]) < 1e-6:
        d, lo, hi = abs(a1[1] - b1[1]), max(min(a1[0], a2[0]), min(b1[0], b2[0])), min(max(a1[0], a2[0]), max(b1[0], b2[0]))
    else:
        return False
    return 1e-6 < d <= 2 * PERTO and hi - lo > 1e-6


def _na_mesma_linha(a1, a2, b1, b2) -> bool:
    if abs(a1[0] - a2[0]) < 1e-6 and abs(b1[0] - b2[0]) < 1e-6:
        return abs(a1[0] - b1[0]) < 1e-6
    if abs(a1[1] - a2[1]) < 1e-6 and abs(b1[1] - b2[1]) < 1e-6:
        return abs(a1[1] - b1[1]) < 1e-6
    return False


def _dist_seg_seg(a1, a2, b1, b2) -> float:
    """Distância entre dois segmentos de eixo."""
    dx = max(0.0, min(b1[0], b2[0]) - max(a1[0], a2[0]), min(a1[0], a2[0]) - max(b1[0], b2[0]))
    dy = max(0.0, min(b1[1], b2[1]) - max(a1[1], a2[1]), min(a1[1], a2[1]) - max(b1[1], b2[1]))
    return math.hypot(dx, dy)


def _encosta(a1, a2, b1, b2) -> bool:
    """Dois segmentos de eixo, um horizontal e um vertical, têm um ponto em comum, nem que seja a ponta."""
    ah = abs(a1[1] - a2[1]) < 1e-6
    bh = abs(b1[1] - b2[1]) < 1e-6
    if ah == bh:
        return False
    h1, h2, v1, v2 = (a1, a2, b1, b2) if ah else (b1, b2, a1, a2)
    y, x = h1[1], v1[0]
    return (min(h1[0], h2[0]) - 1e-6 <= x <= max(h1[0], h2[0]) + 1e-6 and
            min(v1[1], v2[1]) - 1e-6 <= y <= max(v1[1], v2[1]) + 1e-6)


def _sobrepoe(a1, a2, b1, b2) -> float:
    """Comprimento em que dois segmentos de eixo correm juntos, na mesma linha."""
    if abs(a1[1] - a2[1]) < 1e-6 and abs(b1[1] - b2[1]) < 1e-6 and abs(a1[1] - b1[1]) < 1e-6:
        lo = max(min(a1[0], a2[0]), min(b1[0], b2[0]))
        hi = min(max(a1[0], a2[0]), max(b1[0], b2[0]))
        return max(0.0, hi - lo)
    if abs(a1[0] - a2[0]) < 1e-6 and abs(b1[0] - b2[0]) < 1e-6 and abs(a1[0] - b1[0]) < 1e-6:
        lo = max(min(a1[1], a2[1]), min(b1[1], b2[1]))
        hi = min(max(a1[1], a2[1]), max(b1[1], b2[1]))
        return max(0.0, hi - lo)
    return 0.0


def _lado_natural(o: Caixa, d: Caixa) -> dict[str, str]:
    """Para cada lado de `o`, se ele olha para `d` (natural), de través (lateral) ou de costas (oposto)."""
    dx, dy = d.cx - o.cx, d.cy - o.cy
    if o.faixa != d.faixa and abs(dy) > 1:
        frente = "baixo" if dy > 0 else "cima"
    elif abs(dx) >= abs(dy):
        frente = "direita" if dx > 0 else "esquerda"
    else:
        frente = "baixo" if dy > 0 else "cima"
    costas = {"cima": "baixo", "baixo": "cima", "esquerda": "direita", "direita": "esquerda"}[frente]
    return {l: ("natural" if l == frente else "oposto" if l == costas else "lateral") for l in LADOS}


def _rotear(fig: Figura) -> None:
    e = fig.estilo
    cl = e.folga
    caixas = fig.caixas
    obst = {c.id: (c.x - cl, c.y - cl, c.x + c.w + cl, c.y + c.h + cl) for c in caixas.values()}
    textos = [_retangulo_do_titulo(fig)]
    # no alto da zona e da faixa, onde vai o nome, a seta pode atravessar, mas não correr ao longo
    lh = e.linha(e.texto)
    bandas = [(h.x0 - e.pad_h, h.topo - 2, h.x1 + e.pad_h, h.topo + h.n * lh + 2) for h in fig.cabecas.values()]
    if fig.baixo:
        # a margem de baixo se abriu para o rótulo de quem sobe para a caixa: a seta corre pelo fundo, e não rente
        fundo = max(c.y + c.h for c in caixas.values()) + 1
        bandas.append((0, fundo, fig.largura, fig.altura - e.margem / 2 - 1))
    toco = cl + e.folga / 2
    # trilhos candidatos
    xs = {e.margem / 2, fig.largura - e.margem / 2}
    ys = {fig.altura - e.margem / 2}
    for r in obst.values():
        xs.update((r[0], r[2]))
        ys.update((r[1], r[3]))
    colunas = sorted({(c.x, c.x + c.w) for c in caixas.values()})
    bordas = sorted({v for par in colunas for v in par})
    for a, b in zip(bordas, bordas[1:]):
        if b - a > 2 * cl:
            meio = (a + b) / 2
            xs.update((meio, meio - cl, meio + cl))
    linhas_y = sorted({c.y for c in caixas.values()} | {c.y + c.h for c in caixas.values()})
    for a, b in zip(linhas_y, linhas_y[1:]):
        if b - a > 2 * cl:
            meio = (a + b) / 2
            ys.update((meio, meio - cl, meio + cl))
    pontas = {**caixas, **{z.id: z for z in fig.zonas}}
    portas: dict[tuple, tuple] = {}
    for c in pontas.values():
        for lado in LADOS:
            nx, ny = _NORMAL[lado]
            for k, (px_, py_) in enumerate(c.portas(lado)):
                q = (px_ + nx * toco, py_ + ny * toco)
                portas[(c.id, lado, k)] = ((px_, py_), q)
                xs.add(q[0])
                ys.add(q[1])
    # a seta corre dentro da figura: o trilho que cairia na borda dela, como o do toco da porta de uma zona
    # que encosta na margem, fica de fora
    xs_l = sorted(x for x in xs if e.margem / 2 - 1e-6 <= x <= fig.largura - e.margem / 2 + 1e-6)
    ys_l = sorted(y for y in ys if e.margem / 2 - 1e-6 <= y <= fig.altura - e.margem / 2 + 1e-6)
    todos = list(obst.values()) + textos

    def livre(p):
        return not any(_dentro(p[0], p[1], r) for r in todos)

    nos = {}
    for y in ys_l:
        for x in xs_l:
            if livre((x, y)):
                nos[(x, y)] = len(nos)
    viz: dict[tuple, list] = {p: [] for p in nos}
    for y in ys_l:
        fila = [x for x in xs_l if (x, y) in nos]
        for a, b in zip(fila, fila[1:]):
            if any(r[1] <= y <= r[3] and a < r[2] and b > r[0] for r in bandas):
                continue
            if not any(_corta((a, y), (b, y), r) for r in todos):
                viz[(a, y)].append(((b, y), "h"))
                viz[(b, y)].append(((a, y), "h"))
    for x in xs_l:
        fila = [y for y in ys_l if (x, y) in nos]
        for a, b in zip(fila, fila[1:]):
            if not any(_corta((x, a), (x, b), r) for r in todos):
                viz[(x, a)].append(((x, b), "v"))
                viz[(x, b)].append(((x, a), "v"))

    # a seta que corre rente à borda de uma caixa ou de uma zona se confunde com ela: custa mais
    rentes = []
    for c in caixas.values():
        rentes += [("h", c.y, c.x, c.x + c.w, toco + 1), ("h", c.y + c.h, c.x, c.x + c.w, toco + 1),
                   ("v", c.x, c.y, c.y + c.h, toco + 1), ("v", c.x + c.w, c.y, c.y + c.h, toco + 1)]
    for z in fig.zonas:
        rentes += [("h", z.y, z.x, z.x + z.w, 2), ("h", z.y + z.h, z.x, z.x + z.w, 2),
                   ("v", z.x, z.y, z.y + z.h, 2), ("v", z.x + z.w, z.y, z.y + z.h, 2)]
    feitos: list[tuple] = []
    usadas: dict[tuple, dict] = {}  # (ponta, lado, porta) -> {"sai": n, "chega": n}

    def pena_porta(chave: tuple, sentido: str) -> float:
        u = usadas.get(chave, {})
        contra = "chega" if sentido == "sai" else "sai"
        # a porta que recebe não solta seta, e a que solta não recebe: a leitura do sentido se perderia
        return 20 * CUSTO_SOBREPOR * u.get(contra, 0) + CUSTO_PORTA_DE_NOVO * u.get(sentido, 0)
    def reta(s) -> bool:
        """Há porta de saída e de chegada, nos lados que a fonte permite, frente a frente e alinhadas."""
        o, d = pontas[s.de], pontas[s.para]
        frente = {"baixo": "cima", "cima": "baixo", "direita": "esquerda", "esquerda": "direita"}
        for lo in ([s.sai] if s.sai else LADOS):
            ld = frente[lo]
            if s.chega and s.chega != ld:
                continue
            nx, ny = _NORMAL[lo]
            for p in o.portas(lo):
                for q in d.portas(ld):
                    if nx and abs(p[1] - q[1]) < 1e-6 and (q[0] - p[0]) * nx > 0:
                        return True
                    if ny and abs(p[0] - q[0]) < 1e-6 and (q[1] - p[1]) * ny > 0:
                        return True
        return False
    # a seta que vai reta, porta com porta, passa primeiro: é a espinha da figura, e as outras desviam dela
    ordem = sorted(fig.setas, key=lambda s: (not reta(s), abs(pontas[s.de].cx - pontas[s.para].cx) +
                                             abs(pontas[s.de].cy - pontas[s.para].cy)))
    for s in ordem:
        o, d = pontas[s.de], pontas[s.para]
        nat_o, nat_d = _lado_natural(o, d), _lado_natural(d, o)
        lados_o = [s.sai] if s.sai else list(LADOS)
        lados_d = [s.chega] if s.chega else list(LADOS)
        inicio, alvo = {}, {}
        for l in lados_o:
            for k in range(len(o.portas(l))):
                chave = (o.id, l, k)
                p, q = portas[chave]
                if q in nos:
                    pena = CUSTO_LADO[nat_o[l]] + pena_porta(chave, "sai") + _custo_seg(p, q, feitos, s.de, s.para)
                    if q not in inicio or pena < inicio[q][0]:
                        inicio[q] = (pena, "v" if l in ("cima", "baixo") else "h", p, chave)
        for l in lados_d:
            for k in range(len(d.portas(l))):
                chave = (d.id, l, k)
                p, q = portas[chave]
                if q in nos:
                    alvo[q] = (CUSTO_LADO[nat_d[l]] + pena_porta(chave, "chega") + _custo_seg(q, p, feitos, s.de, s.para),
                               "v" if l in ("cima", "baixo") else "h", p, chave)
        caminho = _dijkstra(inicio, alvo, viz, feitos, s.de, s.para, rentes)
        if caminho is None:
            raise ErroDeFonte(f"a seta {s.indice + 1} ({s.de} → {s.para}) não acha caminho entre as caixas; "
                              f"abra uma calha ou mude a caixa de coluna")
        pontos, chave_o, chave_d = caminho
        for chave, sentido in ((chave_o, "sai"), (chave_d, "chega")):
            u = usadas.setdefault(chave, {})
            u[sentido] = u.get(sentido, 0) + 1
        s.pontos = _simplificar(pontos)
        feitos.extend((a, b, s.de, s.para) for a, b in zip(s.pontos, s.pontos[1:]))


def _custo_seg(a, b, feitos, de: str = "", para: str = "", rentes=()) -> float:
    """Comprimento, mais o cruzamento e a sobreposição com as setas já postas, mais o trecho rente a borda.
    Setas que saem da mesma caixa podem correr juntas no começo, e as que chegam na mesma caixa, no fim:
    é o feixe."""
    custo = abs(a[0] - b[0]) + abs(a[1] - b[1])
    h = abs(a[1] - b[1]) < 1e-6
    fixo, lo, hi = (a[1], *sorted((a[0], b[0]))) if h else (a[0], *sorted((a[1], b[1])))
    for eixo, valor, r0, r1, perto in rentes:
        if (eixo == "h") == h and abs(valor - fixo) <= perto:
            custo += CUSTO_RENTE * max(0.0, min(hi, r1) - max(lo, r0))
    for f1, f2, f_de, f_para in feitos:
        feixe = de and (f_de == de or f_para == para)
        junto = _sobrepoe(a, b, f1, f2)
        if _cruza(a, b, f1, f2):
            custo += CUSTO_CRUZAR
        elif junto > 1e-6:
            # o feixe corre junto: o trecho comum se desenha uma vez só, e por isso custa um pouco menos
            custo += -DESCONTO_FEIXE * junto if feixe else CUSTO_SOBREPOR
        elif feixe and _paralelas_perto(a, b, f1, f2):
            # duas setas do mesmo feixe lado a lado, quase juntas: ou correm juntas, ou se afastam
            custo += CUSTO_CRUZAR / 4
        elif not feixe and _encosta(a, b, f1, f2):
            # o trilho cruza a seta já posta num nó da grade: metade na chegada, metade na saída; e duas
            # setas que só se tocam no canto também se leem como cruzadas
            custo += CUSTO_CRUZAR / 2
        elif not feixe and _dist_seg_seg(a, b, f1, f2) <= (PERTO_NA_LINHA if _na_mesma_linha(a, b, f1, f2) else PERTO):
            # a seta alheia a um passo, ou na mesma linha logo adiante: na leitura, as duas parecem uma só
            custo += CUSTO_CRUZAR / 4
    return custo


def _dijkstra(inicio: dict, alvo: dict, viz: dict, feitos: list, de: str, para: str, rentes=()):
    fila, visto, pai = [], {}, {}
    porta_ini = {}
    for q, (custo, dir_, p, chave) in inicio.items():
        estado = (q, dir_)
        heapq.heappush(fila, (custo, q, dir_))
        visto[estado] = custo
        pai[estado] = None
        porta_ini[estado] = (p, chave)
    melhor, fim = math.inf, None
    while fila:
        custo, q, dir_ = heapq.heappop(fila)
        if custo > visto.get((q, dir_), math.inf) or custo >= melhor:
            continue
        if q in alvo:
            extra, dir_alvo, _, _ = alvo[q]
            total = custo + extra + (CUSTO_DOBRA if dir_ != dir_alvo else 0)
            if total < melhor:
                melhor, fim = total, (q, dir_)
        for (v, d) in viz.get(q, []):
            novo = custo + _custo_seg(q, v, feitos, de, para, rentes) + (CUSTO_DOBRA if d != dir_ else 0)
            if d == dir_ and _atravessa(q, d, feitos):
                novo += CUSTO_CRUZAR
            if novo < visto.get((v, d), math.inf):
                visto[(v, d)] = novo
                pai[(v, d)] = (q, dir_)
                heapq.heappush(fila, (novo, v, d))
    if fim is None:
        return None
    seq = []
    estado = fim
    while estado is not None:
        seq.append(estado)
        ant = pai[estado]
        if ant is None:
            break
        estado = ant
    seq.reverse()
    p_ini, chave_o = porta_ini[seq[0]]
    _, _, p_fim, chave_d = alvo[fim[0]]
    pontos = [p_ini] + [q for q, _ in seq] + [p_fim]
    return pontos, chave_o, chave_d


def _simplificar(pontos: list) -> list:
    saida = []
    for p in pontos:
        p = (_arred(p[0]), _arred(p[1]))
        if saida and abs(saida[-1][0] - p[0]) < 1e-6 and abs(saida[-1][1] - p[1]) < 1e-6:
            continue
        saida.append(p)
    i = 1
    while i < len(saida) - 1:
        a, b, c = saida[i - 1], saida[i], saida[i + 1]
        if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6) or (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6):
            saida.pop(i)
        else:
            i += 1
    return saida


def _retangulo_do_titulo(fig: Figura) -> tuple:
    e = fig.estilo
    alto_t = len(fig.titulo_linhas) * e.linha(e.bloco)
    larg_t = max([medida.largura(l, e.bloco, e.peso_rotulo) for l in fig.titulo_linhas] or [0])
    return (e.margem - 2, e.margem - 2, e.margem + larg_t + 2, e.margem + alto_t + 2)


def _colocar_cabecas(fig: Figura) -> list:
    """Põe o nome de cada zona e faixa no primeiro trecho do alto dela que nenhuma seta atravessa, a começar
    da esquerda. Devolve as cabeças que não acharam trecho com as linhas reservadas."""
    e = fig.estilo
    lh = e.linha(e.texto)
    segs = [(a, b) for s in fig.setas for a, b in zip(s.pontos, s.pontos[1:])]
    sem_lugar = []
    for h in fig.cabecas.values():
        y0, y1 = h.topo - 2, h.topo + h.n * lh + 2
        tapado = sorted((min(a[0], b[0]) - e.folga, max(a[0], b[0]) + e.folga) for a, b in segs
                        if min(a[1], b[1]) <= y1 and max(a[1], b[1]) >= y0)
        livres, x = [], h.x0
        for t0, t1 in tapado:
            if t0 > x:
                livres.append((x, min(t0, h.x1)))
            x = max(x, t1)
            if x >= h.x1:
                break
        if x < h.x1:
            livres.append((x, h.x1))
        h.linhas = []
        for lo, hi in livres:
            linhas = medida.quebrar(h.nome, e.texto, h.peso, hi - lo)
            if len(linhas) <= h.n and all(medida.largura(l, e.texto, h.peso) <= hi - lo + 0.01 for l in linhas):
                h.x, h.linhas = lo, linhas
                break
        if not h.linhas:
            sem_lugar.append(h)
    return sem_lugar


# ----------------------------------------------------------------------------------------------- rótulos

@dataclass
class _Falta:
    seta: Seta
    eixo: str        # "x" quando falta largura numa calha, "y" quando falta altura num vão
    onde: float      # a coordenada do segmento
    quanto: float
    trecho: tuple = ()  # o segmento onde o rótulo não coube


def _poligono(c: Caixa, folga: float = 2.0) -> list:
    """O contorno da caixa como polígono convexo, com uma folga em volta."""
    if c.forma == "losango":
        return [(c.cx, c.y - folga), (c.x + c.w + folga, c.cy), (c.cx, c.y + c.h + folga), (c.x - folga, c.cy)]
    if c.forma == "elipse":
        a, b = c.w / 2 + folga, c.h / 2 + folga
        return [(c.cx + a * math.cos(2 * math.pi * k / 24), c.cy + b * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    return [(c.x - folga, c.y - folga), (c.x + c.w + folga, c.y - folga),
            (c.x + c.w + folga, c.y + c.h + folga), (c.x - folga, c.y + c.h + folga)]


def _toca_poligono(r: tuple, poli: list) -> bool:
    """Um retângulo de eixo toca um polígono convexo (teste do eixo separador)."""
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


def _rotular(fig: Figura) -> list[_Falta]:
    e = fig.estilo
    caixas = list(fig.caixas.values())
    formas = [_poligono(c) for c in caixas]
    # o rótulo da seta não vai no alto da zona ou da faixa, onde se leria como parte do nome dela
    lh_t = e.linha(e.texto)
    ocupado = [_retangulo_do_titulo(fig)] + [(h.x0 - 2, h.topo - 2, h.x1 + 2, h.topo + h.n * lh_t + 2)
                                             for h in fig.cabecas.values()]
    segs = [(s, a, b) for s in fig.setas for a, b in zip(s.pontos, s.pontos[1:])]
    for z in fig.zonas:  # o rótulo não atravessa a borda da zona
        cantos = [(z.x, z.y), (z.x + z.w, z.y), (z.x + z.w, z.y + z.h), (z.x, z.y + z.h)]
        segs += [(z, a, b) for a, b in zip(cantos, cantos[1:] + cantos[:1])]
    faltas = []
    lh = e.linha(e.metadado)
    for s in fig.setas:
        s.rotulo_linhas, s.rotulo_pos = [], None
    postos = []  # os rótulos já postos: o próximo guarda uma folga deles, para não se lerem como um só

    def tentar(grupo: list, trechos: list):
        rotulo = grupo[0].rotulo
        for (a, b), dono in trechos:
            horizontal = abs(a[1] - b[1]) < 1e-6
            comp = abs(a[0] - b[0]) + abs(a[1] - b[1])
            larguras = [max(comp - 8, 40), 140, 100, 72, 56] if horizontal else [200, 160, 120, 90, 72, 56]
            for maximo in larguras:
                linhas = medida.quebrar(rotulo, e.metadado, e.peso_corpo, maximo)
                lw = max(medida.largura(l, e.metadado, e.peso_corpo) for l in linhas)
                for cand in _candidatos(a, b, lw, len(linhas) * lh, horizontal, e):
                    x0, y0, x1, y1, ax, topo, ancora = cand
                    r = (x0, y0, x1, y1)
                    if x0 < 2 or x1 > fig.largura - 2 or y0 < 2 or y1 > fig.altura - 2:
                        continue
                    if any(_toca(r, o) for o in ocupado) or any(_toca_poligono(r, pol) for pol in formas):
                        continue
                    if any(_toca((x0 - e.folga, y0 - e.folga, x1 + e.folga, y1 + e.folga), o) for o in postos):
                        continue
                    if any(outra not in grupo and _seg_toca(p, q, r) for outra, p, q in segs):
                        continue
                    # nem a própria seta passa por cima do rótulo, fora do trecho onde ele está
                    if any(outra in grupo and not _sobrepoe(a, b, p, q) and _seg_toca(p, q, r) for outra, p, q in segs):
                        continue
                    if any(isinstance(outra, Seta) and outra not in grupo and _dist_ret_seg(r, p, q) < 2 * e.folga
                           for outra, p, q in segs):
                        continue
                    return dono, linhas, (ax, topo, ancora), r
        return None

    def comprimento(ab):
        return abs(ab[0][0] - ab[1][0]) + abs(ab[0][1] - ab[1][1])

    # a seta tracejada sem rótulo não pede lugar de rótulo, mas segue obstáculo para o rótulo das outras
    fila = _feixes_de_mesmo_rotulo([s for s in fig.setas if s.rotulo])
    while fila:
        grupo = fila.pop(0)
        s = grupo[0]

        # o rótulo vai no trecho só desta seta: no tronco que ela divide com outra, ele não diz de quem é
        def dividido(ab, grupo=grupo):
            return any(isinstance(outra, Seta) and outra not in grupo and _sobrepoe(ab[0], ab[1], p, q) > 1e-6
                       for outra, p, q in segs)
        if len(grupo) > 1:
            # o feixe de setas que dizem a mesma coisa leva o rótulo uma vez, no tronco comum a todas; sem
            # lugar no tronco, cada uma leva o seu
            tronco = sorted((ab for ab in _tronco(s, grupo[1:]) if not dividido(ab)), key=lambda ab: -comprimento(ab))
            posto = tentar(grupo, [(ab, s) for ab in tronco])
            if posto is None:
                fila[0:0] = [[m] for m in grupo]
                continue
        else:
            trechos = sorted(zip(s.pontos, s.pontos[1:]), key=lambda ab: (dividido(ab), -comprimento(ab)))
            posto = tentar(grupo, [(ab, s) for ab in trechos])
        if posto:
            dono, dono.rotulo_linhas, dono.rotulo_pos, caixa = posto
            postos.append(caixa)
            continue
        a, b = trechos[0]
        inteiro = medida.largura(s.rotulo, e.metadado, e.peso_corpo)
        linhas = medida.quebrar(s.rotulo, e.metadado, e.peso_corpo, max(64.0, inteiro / 2 + 8))
        lw = max(medida.largura(l, e.metadado, e.peso_corpo) for l in linhas)
        meio_x, meio_y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        vertical = abs(a[0] - b[0]) < 1e-6
        x_min = min(c.x for c in caixas)
        x_max = max(c.x + c.w for c in caixas)
        if any(x0 - 1 <= meio_x <= x1 + 1 for x0, x1 in fig.calhas_x):
            faltas.append(_Falta(s, "x", meio_x, lw + 2 * e.folga + (e.folga if vertical else 0)))
        elif vertical and (meio_x < x_min or meio_x > x_max):
            faltas.append(_Falta(s, "margem", meio_x, lw + 2 * e.folga))
        else:
            faltas.append(_Falta(s, "y", meio_y, len(linhas) * lh + 2 * e.folga, (a, b)))
    return faltas


def _tronco(s: Seta, outras: list) -> list:
    """Os trechos do caminho de `s` por onde todas as outras também passam."""
    saida = []
    for a, b in zip(s.pontos, s.pontos[1:]):
        h = abs(a[1] - b[1]) < 1e-6
        v, f = (0, 1) if h else (1, 0)
        lo, hi = sorted((a[v], b[v]))
        for t in outras:
            melhor = None
            for p, q in zip(t.pontos, t.pontos[1:]):
                if _sobrepoe(a, b, p, q) > 1e-6:
                    c0, c1 = max(lo, min(p[v], q[v])), min(hi, max(p[v], q[v]))
                    if melhor is None or c1 - c0 > melhor[1] - melhor[0]:
                        melhor = (c0, c1)
            if melhor is None:
                lo = hi
                break
            lo, hi = max(lo, melhor[0]), min(hi, melhor[1])
        if hi - lo > 1e-6:
            saida.append(((lo, a[f]), (hi, a[f])) if h else ((a[f], lo), (a[f], hi)))
    return saida


def _feixes_de_mesmo_rotulo(setas: list) -> list[list]:
    """As setas agrupadas em feixes: as que saem da mesma caixa ou chegam na mesma, correm juntas num trecho e
    dizem a mesma coisa. Seta sem par fica num grupo só dela."""
    def juntas(s, t):
        return any(_sobrepoe(a, b, p, q) > 1e-6 for a, b in zip(s.pontos, s.pontos[1:])
                   for p, q in zip(t.pontos, t.pontos[1:]))
    grupos: list[list] = []
    for s in setas:
        par = next((g for g in grupos if any(t.rotulo == s.rotulo and (t.de == s.de or t.para == s.para)
                                             and juntas(s, t) for t in g)), None)
        if par is None:
            grupos.append([s])
        else:
            par.append(s)
    return grupos


def _candidatos(a, b, lw, lh, horizontal, e: Estilo):
    d = e.folga / 2 + 2
    if horizontal:
        y = a[1]
        x_lo, x_hi = sorted((a[0], b[0]))
        for frac in (0.5, 0.35, 0.65, 0.2, 0.8):
            cx = x_lo + (x_hi - x_lo) * frac
            for topo in (y - d - lh, y + d):
                yield (cx - lw / 2, topo, cx + lw / 2, topo + lh, cx, topo, "middle")
    else:
        x = a[0]
        y_lo, y_hi = sorted((a[1], b[1]))
        for frac in (0.5, 0.35, 0.65, 0.2, 0.8):
            cy = y_lo + (y_hi - y_lo) * frac
            topo = cy - lh / 2
            yield (x + d, topo, x + d + lw, topo + lh, x + d, topo, "start")
            yield (x - d - lw, topo, x - d, topo + lh, x - d, topo, "end")


def _dist_ret_seg(r: tuple, p, q) -> float:
    """Distância de um retângulo de eixo a um segmento de eixo."""
    x0, x1 = sorted((p[0], q[0]))
    y0, y1 = sorted((p[1], q[1]))
    dx = max(0.0, r[0] - x1, x0 - r[2])
    dy = max(0.0, r[1] - y1, y0 - r[3])
    return math.hypot(dx, dy)


def _toca(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _seg_toca(p, q, r) -> bool:
    x0, x1 = sorted((p[0], q[0]))
    y0, y1 = sorted((p[1], q[1]))
    return x0 <= r[2] and r[0] <= x1 and y0 <= r[3] and r[1] <= y1


# ----------------------------------------------------------------------------------------------- montagem

def montar(dados: dict, estilo: Estilo | None = None, tentativas: int = 8) -> Figura:
    """Calcula a figura: posições, rotas e rótulos. Abre calha ou vão quando um rótulo não acha lugar."""
    e = estilo or Estilo.dos_tokens()
    aj = _Ajuste()
    for _ in range(tentativas):
        fig = _layout(dados, e, aj)
        _rotear(fig)
        sem_lugar = _colocar_cabecas(fig)
        faltas = _rotular(fig)
        if not faltas and not sem_lugar:
            return fig
        mudou = _abrir(fig, faltas, aj)
        for h in sem_lugar:
            if h.n < 4:
                aj.cabecas[h.chave] = h.n + 1
                mudou = True
        if not mudou:
            break
    if sem_lugar:
        h = sem_lugar[0]
        raise ErroDeFonte(f"o nome {'da zona' if h.chave[0] == 'zona' else 'da faixa'} '{h.chave[1]}' não acha, no "
                          f"alto dela, trecho que nenhuma seta atravesse; mude a coluna da caixa que recebe a seta "
                          f"por cima ou encurte o nome")
    nomes = ", ".join(f"«{f.seta.rotulo}» ({f.seta.de} → {f.seta.para})" for f in faltas)
    raise ErroDeFonte(f"o rótulo não acha lugar junto da seta: {nomes}; encurte o rótulo ou afaste as caixas")


def _abrir(fig: Figura, faltas: list[_Falta], aj: _Ajuste) -> bool:
    """Abre a calha ou o vão onde o rótulo não coube. Devolve se mudou alguma coisa."""
    e = fig.estilo
    mudou = False
    x_min = min(c.x for c in fig.caixas.values())
    for f in faltas:
        if f.eixo == "margem":
            lado = "esq" if f.onde < x_min else "dir"
            aj.margens[lado] = max(aj.margens.get(lado, 0) + 2 * e.folga, f.quanto)
            mudou = True
            continue
        if f.eixo == "x":
            for i, (x0, x1) in enumerate(fig.calhas_x):
                if x0 - 1 <= f.onde <= x1 + 1:
                    atual = aj.calhas.get(i, e.calha)
                    novo = max(atual + 2 * e.folga, f.quanto)
                    aj.calhas[i] = novo
                    mudou = True
                    break
            continue
        if f.onde > max(c.y + c.h for c in fig.caixas.values()):  # abaixo da última caixa: abre a margem de baixo
            aj.margens["baixo"] = max(aj.margens.get("baixo", 0) + 2 * e.folga, f.quanto)
            mudou = True
            continue
        alvo = None
        y_lo, y_hi = (sorted((f.trecho[0][1], f.trecho[1][1])) if f.trecho else (f.onde, f.onde))
        for i, (_, _, topo, base) in enumerate(fig.faixas[:-1]):
            # o trecho que passa pelo vão entre duas faixas cresce com o vão, mesmo que o meio dele caia na faixa
            if y_lo <= fig.faixas[i + 1][2] and y_hi >= base:
                alvo = (aj.vaos_faixa, i, e.vao_faixa)
                break
        if alvo is None:
            for fid, _, topo, base in fig.faixas:
                if topo <= f.onde <= base:
                    alvo = (aj.vaos_pilha, fid, e.vao_pilha)
                    break
        if alvo is None:
            continue
        mapa, chave, base_v = alvo
        mapa[chave] = max(mapa.get(chave, base_v) + 2 * e.folga, f.quanto)
        mudou = True
    return mudou


# ----------------------------------------------------------------------------------------------- SVG

def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _num(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _cores_da_caixa(c: Caixa, e: Estilo) -> tuple[str, str, str]:
    """(fundo, fio, tinta do título)."""
    if c.categoria == "cadeira" and c.cadeira and c.cadeira in e.cadeiras:
        return e.fundo, e.cadeiras[c.cadeira], e.corpo
    if c.categoria and c.categoria in e.familias:
        f = e.familias[c.categoria]
        return f["bg"], f["stroke"], f["fg"]
    return e.fundo, e.tinta, e.corpo


PONTA = 10.0       # comprimento da ponta da seta
MEIA_PONTA = 4.5   # metade da base da ponta


def _ponta(pontos: list) -> tuple[list, str]:
    """A linha da seta, recuada para dentro da ponta, e o triângulo da ponta. A ponta é forma desenhada, e não
    marcador do SVG, porque nem todo pintor pinta marcador: o da prévia em PNG não pinta."""
    (ax, ay), (bx, by) = pontos[-2], pontos[-1]
    comp = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / comp, (by - ay) / comp
    recuo = min(PONTA - 2, comp - 1)
    linha = list(pontos[:-1]) + [(bx - ux * recuo, by - uy * recuo)]
    cx, cy = bx - ux * PONTA, by - uy * PONTA
    nx, ny = -uy * MEIA_PONTA, ux * MEIA_PONTA
    d = f"M{_num(bx)} {_num(by)}L{_num(cx + nx)} {_num(cy + ny)}L{_num(cx - nx)} {_num(cy - ny)}Z"
    return linha, d


def _texto(x, topo, linhas, tamanho, peso, cor, papel, ancora, e: Estilo) -> str:
    if not linhas:
        return ""
    lh = e.linha(tamanho)
    spans = "".join(f'<tspan x="{_num(x)}" y="{_num(e.base(topo + i * lh, tamanho))}">{_esc(l)}</tspan>'
                    for i, l in enumerate(linhas))
    return (f'<text data-papel="{papel}" font-size="{_num(tamanho)}" font-weight="{peso}" fill="{cor}" '
            f'text-anchor="{ancora}">{spans}</text>')


def _traco(e: Estilo, tracejada: bool) -> str:
    """O tracejado da linha de outra camada: traço de space-2 e vão de space-1, sem token próprio."""
    return f' stroke-dasharray="{_num(e.folga)} {_num(e.folga / 2)}"' if tracejada else ""


def _forma_svg(c: Caixa, fundo: str, fio: str, e: Estilo) -> str:
    x, y, w, h = c.x, c.y, c.w, c.h
    comum = f'fill="{fundo}" stroke="{fio}" stroke-width="{_num(e.fio)}"' + _traco(e, c.tracejada)
    if c.forma == "losango":
        pts = f"{_num(x + w / 2)},{_num(y)} {_num(x + w)},{_num(y + h / 2)} {_num(x + w / 2)},{_num(y + h)} {_num(x)},{_num(y + h / 2)}"
        return f'<polygon points="{pts}" {comum}/>'
    if c.forma == "elipse":
        return f'<ellipse cx="{_num(x + w / 2)}" cy="{_num(y + h / 2)}" rx="{_num(w / 2)}" ry="{_num(h / 2)}" {comum}/>'
    if c.forma == "cilindro":
        ry = _ry(e)
        d = (f"M{_num(x)} {_num(y + ry)}A{_num(w / 2)} {_num(ry)} 0 0 1 {_num(x + w)} {_num(y + ry)}"
             f"V{_num(y + h - ry)}A{_num(w / 2)} {_num(ry)} 0 0 1 {_num(x)} {_num(y + h - ry)}Z"
             f"M{_num(x)} {_num(y + ry)}A{_num(w / 2)} {_num(ry)} 0 0 0 {_num(x + w)} {_num(y + ry)}")
        return f'<path d="{d}" {comum}/>'
    rx = e.raio if c.forma == "arredondado" else 0
    return f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}" rx="{_num(rx)}" {comum}/>'


def svg(fig: Figura) -> str:
    e = fig.estilo
    W, H = fig.largura, fig.altura
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(W)}" height="{_num(H)}" '
         f'viewBox="0 0 {_num(W)} {_num(H)}" font-family="{_esc(e.fonte)}" role="img" '
         f'aria-label="{_esc(fig.titulo)}">',
         f"<title>{_esc(fig.titulo)}</title>",
         f'<rect width="{_num(W)}" height="{_num(H)}" fill="{e.fundo}"/>',
         _texto(e.margem, e.margem, fig.titulo_linhas, e.bloco, e.peso_rotulo, e.titulo_cor, "bloco", "start", e)]
    for y in fig.separadores:
        o.append(f'<line class="separador" x1="{_num(e.margem)}" x2="{_num(W - e.margem)}" y1="{_num(y)}" '
                 f'y2="{_num(y)}" stroke="{e.separador}" stroke-width="{_num(e.fio_fino)}"/>')
    for fid, nome, topo, _ in fig.faixas:
        h = fig.cabecas.get(("faixa", fid))
        if nome and h:
            o.append(f'<g class="faixa" data-id="{_esc(fid)}">'
                     + _texto(h.x, h.topo, h.linhas, e.texto, e.peso_faixa, e.titulo_cor, "texto", "start", e) + "</g>")
    for z in fig.zonas:
        if z.categoria and z.categoria in e.familias:
            fundo, fio, tinta = e.familias[z.categoria]["zone"], e.familias[z.categoria]["bd"], e.familias[z.categoria]["fg"]
        elif z.cadeira and z.cadeira in e.cadeiras:
            fundo, fio, tinta = e.recuado, e.cadeiras[z.cadeira], e.corpo
        else:
            fundo, fio, tinta = e.recuado, e.separador, e.corpo
        o.append(f'<g class="zona" data-id="{_esc(z.id)}"><rect x="{_num(z.x)}" y="{_num(z.y)}" width="{_num(z.w)}" '
                 f'height="{_num(z.h)}" rx="{_num(e.raio)}" fill="{fundo}" stroke="{fio}" '
                 f'stroke-width="{_num(e.fio_fino)}"{_traco(e, z.tracejada)}/>'
                 + _texto(fig.cabecas[("zona", z.id)].x, z.y + e.folga / 2, fig.cabecas[("zona", z.id)].linhas,
                          e.texto, e.peso_rotulo, tinta, "texto", "start", e)
                 + "</g>")
    for s in fig.setas:
        linha, ponta = _ponta(s.pontos)
        d = "M" + "L".join(f"{_num(x)} {_num(y)}" for x, y in linha)
        rot = ""
        if s.rotulo_pos:
            ax, topo, ancora = s.rotulo_pos
            rot = _texto(ax, topo, s.rotulo_linhas, e.metadado, e.peso_corpo, e.corpo, "metadado", ancora, e)
        o.append(f'<g class="seta{" tracejada" if s.tracejada else ""}" data-de="{_esc(s.de)}" data-para="{_esc(s.para)}">'
                 f'<path d="{d}" fill="none" stroke="{e.tinta}" stroke-width="{_num(e.fio)}"{_traco(e, s.tracejada)}/>'
                 f'<path class="ponta" d="{ponta}" fill="{e.tinta}"/>{rot}</g>')
    for c in fig.caixas.values():
        fundo, fio, tinta = _cores_da_caixa(c, e)
        lh_t, lh_s = e.linha(e.texto), e.linha(e.metadado)
        bloco = len(c.linhas_titulo) * lh_t + (e.folga / 2 + len(c.linhas_sub) * lh_s if c.linhas_sub else 0)
        topo = c.y + (c.h - bloco) / 2
        partes = [_forma_svg(c, fundo, fio, e),
                  _texto(c.cx, topo, c.linhas_titulo, e.texto, e.peso_rotulo, tinta, "texto", "middle", e)]
        if c.linhas_sub:
            partes.append(_texto(c.cx, topo + len(c.linhas_titulo) * lh_t + e.folga / 2, c.linhas_sub,
                                 e.metadado, e.peso_corpo, e.quieto, "metadado", "middle", e))
        # nenhuma figura leva ícone ou glifo dentro da caixa: a cor é da categoria, e o tipo vai no rótulo
        o.append(f'<g class="caixa" data-id="{_esc(c.id)}">' + "".join(partes) + "</g>")
    o.append("</svg>")
    return "\n".join(p for p in o if p)


def desenhar(dados: dict, estilo: Estilo | None = None) -> str:
    """A fonte vira o SVG: conferência, grade, rota, rótulo e pintura."""
    return svg(montar(dados, estilo))
