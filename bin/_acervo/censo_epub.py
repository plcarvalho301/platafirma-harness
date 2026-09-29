"""card #3189, ato temporário: lê um EPUB só com a biblioteca padrão.

Zip, mimetype, container, OPF (manifest, spine, metadados), sumário (nav ou NCX),
criptografia e o texto dos XHTML da spine. Não converte nada: lê os bytes.
"""

import codecs
import importlib.metadata
import io
import posixpath
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote

MIMETYPE = b"application/epub+zip"
ALG_FONTE = "http://www.idpf.org/2008/embedding"  # ofuscação de fonte, não DRM
TIPO_OPF = "application/oebps-package+xml"
TIPOS_HTML = ("application/xhtml+xml", "text/html")
LIMITE_MEMBRO = 32 * 1024 * 1024
LIMITE_TEXTO = 4_000_000
LIMITE_LISTA = 2000
XHTML_ENCODING = 30
NL = chr(10)
# Marcas de ordem de byte; a de 32 bits vem antes da de 16 (começam igual).
BOMS = (
    (bytes([0xFF, 0xFE, 0x00, 0x00]), "utf-32-le"),
    (bytes([0x00, 0x00, 0xFE, 0xFF]), "utf-32-be"),
    (bytes([0xEF, 0xBB, 0xBF]), "utf-8"),
    (bytes([0xFF, 0xFE]), "utf-16-le"),
    (bytes([0xFE, 0xFF]), "utf-16-be"),
)
MUDOS = frozenset(("script", "style", "title"))
BLOCOS = frozenset((
    "address article aside blockquote br dd div dl dt figcaption figure footer "
    "h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table tr td th ul"
).split())

_ESPACO = re.compile(r"[ \t\r\n\f]+")
_QUEBRAS = re.compile(r" *\n[ \n]*")
_ESQUEMA = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_DECLARACAO = re.compile(r"""^\s*<\?xml[^>]*?\sencoding\s*=\s*["']([^"']+)["']""", re.I)
_VERSAO = re.compile(r"(?<![\w.])[vV]?(\d+(?:\.\d+)+\w*|\d+$)")


# ---------- utilidades pequenas ----------

def _uma_linha(e):
    return " ".join(f"{type(e).__name__}: {e}".split())[:200]


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _local(tag):
    """Nome da tag sem o espaço de nomes."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _filhos(no, nome):
    return [c for c in no if _local(c.tag) == nome]


def _descendentes(no, nome):
    return [c for c in no.iter() if _local(c.tag) == nome]


def _primeiro(no, nome):
    achados = _descendentes(no, nome)
    return achados[0] if achados else None


def _xml(dados):
    """(raiz, None) ou (None, motivo). Tolera espaço antes da declaração XML."""
    try:
        return ET.fromstring(dados), None
    except Exception as e:
        motivo = _uma_linha(e)
    limpo = dados.lstrip()
    if limpo != dados:
        try:
            return ET.fromstring(limpo), None
        except Exception:
            pass
    return None, motivo


def _chave(nome):
    return unicodedata.normalize("NFC", nome).casefold()


def _candidatos(base, href):
    """Caminhos possíveis no zip para um href relativo ao OPF: decodificado e literal."""
    href = href.strip().split("#", 1)[0].split("?", 1)[0]
    if not href or _ESQUEMA.match(href):
        return []
    saida = []
    for h in (unquote(href), href):
        alvo = h.lstrip("/") if h.startswith("/") else posixpath.join(base, h)
        alvo = posixpath.normpath(alvo)
        if alvo not in saida:
            saida.append(alvo)
    return saida


def _e_html(item):
    tipo = (item["tipo"] or "").strip().lower()
    if tipo:
        return tipo in TIPOS_HTML
    return (item["href"] or "").lower().endswith((".xhtml", ".html", ".htm"))


def _resumo(nomes, rotulo):
    mais = ", ..." if len(nomes) > 5 else ""
    return f"{len(nomes)} {rotulo}: " + ", ".join(nomes[:5]) + mais


def _mais_comum(contagem):
    return contagem.most_common(1)[0][0] if contagem else None


def _versao_lib(nome):
    try:
        return importlib.metadata.version(nome)
    except Exception:
        return "desconhecida"


# ---------- prazo e zip ----------

class _Prazo:
    """Relógio do `ler`: diz se os segundos combinados estouraram."""

    def __init__(self, limite):
        self.limite = limite
        self.inicio = time.monotonic()

    def estourou(self):
        return self.limite is not None and time.monotonic() - self.inicio >= self.limite


class _Pacote:
    """O zip, com busca por nome exato e, na falta, por grafia divergente (com aviso)."""

    def __init__(self, zf):
        self.zf = zf
        self.infos = zf.infolist()
        self.exato = {}
        self.folgado = {}
        for info in self.infos:
            self.exato.setdefault(info.filename, info)
            self.folgado.setdefault(_chave(info.filename), info)
        self.divergentes = {}  # caminho pedido -> nome real no zip

    def achar(self, candidatos):
        for nome in candidatos:
            if nome in self.exato:
                return self.exato[nome]
        for nome in candidatos:
            info = self.folgado.get(_chave(nome))
            if info is not None:
                self.divergentes.setdefault(candidatos[0], info.filename)
                return info
        return None

    def ler(self, info, limite=LIMITE_MEMBRO):
        """(bytes, None) ou (None, motivo)."""
        if info.file_size > limite:
            return None, f"maior que {limite // 1048576} MB, não lido"
        try:
            with self.zf.open(info) as f:
                dados = f.read(limite + 1)
        except Exception as e:  # senha, compressão que o zipfile não lê, CRC
            return None, _uma_linha(e)
        if len(dados) > limite:
            return None, f"maior que {limite // 1048576} MB, não lido"
        return dados, None


# ---------- mimetype, sumário, criptografia ----------

def _mimetype(pac):
    """Bloco mimetype_conforme (EPUB 3.3 §4.3.3): primeiro, sem compressão, exato, sem BOM."""
    m = {"conforme": None, "primeiro_membro": None, "comprimido": None,
         "conteudo_exato": None, "bom": None}
    if pac.infos:
        m["primeiro_membro"] = pac.infos[0].filename
    info = pac.exato.get("mimetype")
    if info is None:
        m["conforme"] = False
        return m
    m["comprimido"] = info.compress_type != zipfile.ZIP_STORED
    conteudo, _ = pac.ler(info, 4096)
    sinais = [m["primeiro_membro"] == "mimetype", not m["comprimido"]]
    if conteudo is None:
        m["conforme"] = None if all(sinais) else False
        return m
    m["conteudo_exato"] = conteudo == MIMETYPE
    m["bom"] = any(conteudo.startswith(marca) for marca, _ in BOMS)
    m["conforme"] = all(sinais + [m["conteudo_exato"], not m["bom"]])
    return m


class _NavParser(HTMLParser):
    """Lê os <nav> de um documento de navegação: tipos, li, aninhamento de ol e ramos hidden."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.navs = []
        self.nav = None
        self.pilha = []  # (tag, hidden) dos ol/ul/li abertos dentro do nav

    def handle_starttag(self, tag, attrs):
        if tag == "nav":
            tipos = set()
            for nome, valor in attrs:
                if nome.endswith(":type"):  # epub:type
                    tipos.update((valor or "").split())
            self.nav = {"tipos": tipos, "li": 0, "prof": 0, "hidden": 0}
            self.navs.append(self.nav)
            self.pilha = []
        elif self.nav is not None and tag in ("ol", "ul", "li"):
            self.abrir(tag, any(nome == "hidden" for nome, _ in attrs))

    def abrir(self, tag, oculto):
        if tag == "li" and self.pilha and self.pilha[-1][0] == "li":
            self.pilha.pop()  # li que ficou sem fechar
        if oculto and not any(h for _, h in self.pilha):
            self.nav["hidden"] += 1  # só o ramo de fora conta
        self.pilha.append((tag, oculto))
        if tag == "li":
            self.nav["li"] += 1
        else:
            fundo = sum(1 for t, _ in self.pilha if t != "li")
            self.nav["prof"] = max(self.nav["prof"], fundo)

    def handle_endtag(self, tag):
        if tag == "nav":
            self.nav = None
        elif self.nav is not None and tag in ("ol", "ul", "li"):
            for i in range(len(self.pilha) - 1, -1, -1):
                if self.pilha[i][0] == tag:
                    del self.pilha[i:]
                    break


def _nav_toc(texto):
    """Sumário de um documento nav: dict do sumario, ou None se não há nav epub:type=toc."""
    p = _NavParser()
    p.feed(texto)
    p.close()

    def contar(tipo):
        nav = next((n for n in p.navs if tipo in n["tipos"]), None)
        return nav["li"] if nav else 0

    toc = next((n for n in p.navs if "toc" in n["tipos"]), None)
    if toc is None:
        return None
    return {"fonte": "nav", "entradas": toc["li"], "profundidade": toc["prof"],
            "ramos_hidden": toc["hidden"], "page_list": contar("page-list"),
            "landmarks": contar("landmarks")}


def _ncx(raiz):
    """Sumário de um NCX: navPoint da navMap e aninhamento; None se não há navMap."""
    mapa = _primeiro(raiz, "navMap")
    if mapa is None:
        return None
    entradas, fundo = 0, 0
    pilha = [(f, 1) for f in _filhos(mapa, "navPoint")]
    while pilha:
        no, nivel = pilha.pop()
        entradas += 1
        fundo = max(fundo, nivel)
        pilha.extend((f, nivel + 1) for f in _filhos(no, "navPoint"))
    paginas = _primeiro(raiz, "pageList")
    n_paginas = len(_descendentes(paginas, "pageTarget")) if paginas is not None else 0
    return {"fonte": "ncx", "entradas": entradas, "profundidade": fundo,
            "ramos_hidden": None, "page_list": n_paginas, "landmarks": None}


def _alvo_drm(algoritmos, pares, rights):
    """Resumo (algoritmos e caminhos) do que não é ofuscação de fonte."""
    partes = []
    for alg in algoritmos:
        if alg == ALG_FONTE:
            continue
        uris = [u for a, u in pares if a == alg and u]
        if uris:
            mais = ", ..." if len(uris) > 2 else ""
            alg += f" em {len(uris)} arquivo(s): " + ", ".join(uris[:2]) + mais
        partes.append(alg)
    if rights:
        partes.append("META-INF/rights.xml")
    alvo = "; ".join(partes)
    return alvo if len(alvo) <= 300 else alvo[:297] + "..."


def _nome_versao(texto):
    """Separa "Sigil 1.9.0" em ("Sigil", "1.9.0"); sem número, só o nome."""
    m = _VERSAO.search(texto)
    if m is None:
        return texto, None
    nome = texto[:m.start()].strip(" \t([/,:;-")
    return (nome or texto), m.group(1)


def _aplicacoes(meta):
    """Programas que dizem ter feito o arquivo (meta generator); a data é o dcterms:modified."""
    metas = _descendentes(meta, "meta")
    data = next(((m.text or "").strip() or None for m in metas
                 if m.get("property") == "dcterms:modified"), None)
    vistos, saida = set(), []
    for m in metas:
        rotulo = m.get("name") or m.get("property") or ""
        texto = (m.get("content") or m.text or "").strip()
        if "generator" not in rotulo.casefold() or not texto:
            continue
        nome, versao = _nome_versao(texto)
        if (nome, versao) not in vistos:
            vistos.add((nome, versao))
            saida.append({"nome": nome, "versao": versao, "data": data,
                          "fonte": "epub_opf_meta_generator"})
    return saida


# ---------- texto e encoding ----------

class _Extrator(HTMLParser):
    """Texto visível: sem tags, sem script/style/title, com quebra nas bordas de bloco."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.mudo = 0

    def handle_starttag(self, tag, attrs):
        if tag in MUDOS:
            self.mudo += 1
        elif tag in BLOCOS:
            self.partes.append(NL)

    def handle_endtag(self, tag):
        if tag in MUDOS:
            self.mudo = max(0, self.mudo - 1)
        elif tag in BLOCOS:
            self.partes.append(NL)

    def handle_data(self, dado):
        if not self.mudo:
            self.partes.append(_ESPACO.sub(" ", dado))


def _extrair_texto(html):
    p = _Extrator()
    p.feed(html)
    p.close()
    return _QUEBRAS.sub(NL, "".join(p.partes)).strip()


def _importar_detector():
    """charset_normalizer é opcional: sem ele o leitor cai no windows-1252."""
    try:
        import charset_normalizer
    except ImportError:
        return None
    return charset_normalizer


def _nome_canonico(nome):
    """Nome do codec como o Python o conhece; cp125x sai como windows-125x."""
    try:
        nome = codecs.lookup(nome).name
    except LookupError:
        nome = nome.lower()
    return "windows-" + nome[2:] if nome.startswith("cp125") else nome


def _decodificar(dados, palpite):
    """(nome, bom, texto, sem_palpite): BOM, UTF-8 estrito, palpite do detector, windows-1252."""
    for marca, nome in BOMS:
        if dados.startswith(marca):
            return nome, nome, dados[len(marca):].decode(nome, errors="replace"), False
    try:
        return "utf-8", None, dados.decode("utf-8"), False
    except UnicodeDecodeError:
        pass
    achado = palpite(dados) if palpite else None
    if achado:
        return achado[0], None, achado[1], False
    return "windows-1252", None, dados.decode("windows-1252", errors="replace"), True


def _decodificar_resto(dados, padrao):
    """Arquivos além dos 30 medidos: sem detector; o que não é UTF-8 usa o padrão do livro."""
    _, _, texto, sem_palpite = _decodificar(dados, None)
    if sem_palpite and padrao not in (None, "utf-8"):
        try:
            texto = dados.decode(padrao, errors="replace")
        except LookupError:
            pass
    return texto


def _declarado(texto):
    """Encoding da declaração <?xml ... encoding=...?>, em minúsculas; None se não há."""
    m = _DECLARACAO.match(texto[:1024])
    return m.group(1).strip().lower() if m else None


def _canon(nome):
    nome = _nome_canonico(nome)
    return nome[:-3] if nome.startswith(("utf-16", "utf-32")) and nome[-3:] in ("-le", "-be") else nome


def _ascii_compativel(nome):
    try:
        return "a".encode(nome) == b"a"
    except (LookupError, UnicodeError):
        return False


def _bate(declarado, detectado, dados):
    """A declaração bate se é o mesmo codec, ou se os bytes são só ASCII e o codec a lê igual."""
    if _canon(declarado) == _canon(detectado):
        return True
    return dados.isascii() and _ascii_compativel(declarado)


class _Encodings:
    """Junta o encoding de cada XHTML medido no bloco `encoding` do envelope."""

    def __init__(self):
        self.dets, self.boms, self.decls, self.batem = Counter(), Counter(), Counter(), []

    def somar(self, det, bom, declarado, bate):
        self.dets[det] += 1
        if bom:
            self.boms[bom] += 1
        if declarado:
            self.decls[declarado] += 1
            self.batem.append(bate)

    def padrao(self):
        return _mais_comum(self.dets)

    def resultado(self):
        return {"detectado": _mais_comum(self.dets), "confianca": None,
                "bom": _mais_comum(self.boms), "declarado": _mais_comum(self.decls),
                "declarado_bate": all(self.batem) if self.batem else None}


# ---------- o leitor ----------

def _resposta_vazia():
    return {
        "epub": {
            "mimetype_conforme": {"conforme": None, "primeiro_membro": None, "comprimido": None,
                                  "conteudo_exato": None, "bom": None},
            "rootfiles": None,
            "rootfiles_total": None,
            "versao": None,
            "identificador_unico": {"ref": None, "valor": None, "resolve": None},
            "manifest": {"itens": None},
            "spine": {"total": None, "linear_no": None},
            "sumario": {"fonte": None, "entradas": None, "profundidade": None,
                        "ramos_hidden": None, "page_list": None, "landmarks": None},
            "criptografia": {"encryption_xml": None, "algoritmos": None, "ofuscacao_fonte": None,
                             "outra_criptografia": None, "rights_xml": None},
            "membros": {"total": None, "xhtml_lidos": None},
        },
        "aplicacoes_criadoras": [],
        "inibidor": None,
        "lingua_declarada": None,
        "estrutura_declarada": [],
        "encoding": None,
        "_texto": None,
        "_paginas": None,
        "lacunas": {},
        "bibliotecas": {},
        "erro": None,
    }


class _Leitor:
    """Um passe de leitura: guarda o zip e o OPF e vai preenchendo a resposta."""

    def __init__(self, dados, ctx, r):
        self.dados = dados
        self.r = r
        self.b = r["epub"]
        self.lac = r["lacunas"]
        self.prazo = _Prazo(_numero(ctx.get("prazo_s")))
        self.pac = None
        self.raizes = []  # (full-path, media-type) de cada rootfile
        self.opf = None
        self.base = ""  # pasta do OPF dentro do zip
        self.itens = {}  # id -> {href, tipo, props}, na ordem do manifest
        self.refs = []  # idref de cada itemref da spine
        self.toc_id = None
        self.senha = []  # membros com o bit de criptografia geral
        self.pares = []  # (algoritmo, caminho) do encryption.xml
        self.n_fontes = 0
        self.cn = None
        self.n_chute = 0
        self.n_torto = 0
        self.faltas = []

    def falha(self, motivo):
        self.r["erro"] = motivo
        self.lac["epub"] = motivo

    def marcar_prazo(self, onde):
        self.lac.setdefault("prazo", f"prazo de {self.prazo.limite:g}s estourado ({onde}); resultado parcial")

    def rodar(self):
        if not self.dados:
            return self.falha("dados vazios (0 byte)")
        try:
            zf = zipfile.ZipFile(io.BytesIO(self.dados))
        except Exception as e:  # zip torto ou truncado: o arquivo é que está ruim
            return self.falha("zip inválido: " + _uma_linha(e))
        with zf:
            self.pac = _Pacote(zf)
            etapas = (self.membros, self.mimetype, self.criptografia, self.container,
                      self.pacote, self.sumario, self.texto)
            for etapa in etapas:
                if self.prazo.estourou():
                    self.marcar_prazo("antes de " + etapa.__name__)
                    break
                etapa()
            self.avisos()

    def xml(self, info, campo):
        """Lê e interpreta um membro XML; a falha vira lacuna de `campo`."""
        dados, motivo = self.pac.ler(info)
        raiz = None
        if dados is not None:
            raiz, motivo = _xml(dados)
        if raiz is None:
            self.lac[campo] = f"{info.filename}: {motivo}"
        return raiz

    def membro(self, item):
        """(bytes, None) ou (None, motivo) para um item do manifest."""
        href = item["href"]
        candidatos = _candidatos(self.base, href) if href else []
        if not candidatos:
            return None, f"href vazio ou externo: {href!r}"
        info = self.pac.achar(candidatos)
        if info is None:
            return None, f"{href} ausente do zip"
        dados, motivo = self.pac.ler(info)
        return dados, (f"{info.filename}: {motivo}" if motivo else None)

    # -- etapas --

    def membros(self):
        infos = self.pac.infos
        self.b["membros"]["total"] = sum(1 for i in infos if not i.filename.endswith("/"))
        self.b["membros"]["xhtml_lidos"] = 0
        self.senha = [i.filename for i in infos if i.flag_bits & 0x1]

    def mimetype(self):
        self.b["mimetype_conforme"] = _mimetype(self.pac)

    def criptografia(self):
        c = self.b["criptografia"]
        c["rights_xml"] = self.pac.achar(["META-INF/rights.xml"]) is not None
        enc = self.pac.achar(["META-INF/encryption.xml"])
        c["encryption_xml"] = enc is not None
        if enc is None:
            c["algoritmos"], c["ofuscacao_fonte"], c["outra_criptografia"] = [], False, False
            return
        raiz = self.xml(enc, "criptografia")
        if raiz is None:
            return
        metodos = [(m.get("Algorithm") or "").strip() for m in _descendentes(raiz, "EncryptionMethod")]
        c["algoritmos"] = sorted(set(metodos) - {""})
        c["ofuscacao_fonte"] = ALG_FONTE in c["algoritmos"]
        c["outra_criptografia"] = any(a != ALG_FONTE for a in c["algoritmos"])
        self.n_fontes = metodos.count(ALG_FONTE)
        for dado in _descendentes(raiz, "EncryptedData"):
            metodo = next(iter(_filhos(dado, "EncryptionMethod")), None)
            ref = next(iter(_descendentes(dado, "CipherReference")), None)
            alg = ((metodo.get("Algorithm") if metodo is not None else "") or "").strip()
            self.pares.append((alg, ref.get("URI") if ref is not None else None))

    def container(self):
        info = self.pac.achar(["META-INF/container.xml"])
        if info is None:
            self.lac["rootfiles"] = "META-INF/container.xml ausente"
            return
        raiz = self.xml(info, "rootfiles")
        if raiz is None:
            return
        self.raizes = [(rf.get("full-path"), rf.get("media-type"))
                       for rf in _descendentes(raiz, "rootfile") if rf.get("full-path")]
        self.b["rootfiles"] = [p for p, _ in self.raizes][:LIMITE_LISTA]
        self.b["rootfiles_total"] = len(self.raizes)

    def pacote(self):
        """Lê o OPF do primeiro rootfile: versão, identificador, manifest, spine, língua, criador."""
        if not self.raizes:
            self.lac.setdefault("opf", "sem rootfile para ler o pacote")
            return
        escolha = next((p for p, t in self.raizes if t == TIPO_OPF), self.raizes[0][0])
        if len(self.raizes) > 1:
            self.lac["rootfiles_demais"] = f"{len(self.raizes)} rootfiles; só {escolha} foi lido"
        info = self.pac.achar(_candidatos("", escolha))
        if info is None:
            self.lac["opf"] = f"{escolha} ausente do zip"
            return
        raiz = self.xml(info, "opf")
        if raiz is None:
            return
        if _local(raiz.tag) != "package":
            self.lac["opf"] = f"{info.filename}: raiz <{_local(raiz.tag)}>, esperado <package>"
            return
        self.opf = raiz
        self.base = posixpath.dirname(info.filename)
        self.b["versao"] = raiz.get("version")
        meta = _primeiro(raiz, "metadata")
        self.identificador(raiz, meta)
        self.manifest_e_spine(raiz)
        self.metadados(meta)

    def identificador(self, raiz, meta):
        ref = raiz.get("unique-identifier")
        valor = None
        if ref is not None and meta is not None:
            for el in _descendentes(meta, "identifier"):
                if el.get("id") == ref:
                    valor = (el.text or "").strip() or None
                    break
        self.b["identificador_unico"] = {"ref": ref, "valor": valor, "resolve": valor is not None}

    def manifest_e_spine(self, raiz):
        manifest = _primeiro(raiz, "manifest")
        itens = _filhos(manifest, "item") if manifest is not None else []
        for it in itens:
            if it.get("id") is not None:
                self.itens.setdefault(it.get("id"), {
                    "href": it.get("href"), "tipo": it.get("media-type"),
                    "props": (it.get("properties") or "").split()})
        self.b["manifest"] = {"itens": len(itens)}
        spine = _primeiro(raiz, "spine")
        refs = _filhos(spine, "itemref") if spine is not None else []
        self.refs = [r.get("idref") for r in refs]
        self.toc_id = spine.get("toc") if spine is not None else None
        nao_linear = sum(1 for r in refs if (r.get("linear") or "").strip().lower() == "no")
        self.b["spine"] = {"total": len(refs), "linear_no": nao_linear}

    def metadados(self, meta):
        if meta is None:
            self.lac["lingua_declarada"] = "OPF sem metadata"
            return
        for el in _descendentes(meta, "language"):
            if (el.text or "").strip():
                self.r["lingua_declarada"] = el.text.strip()
                break
        else:
            self.lac["lingua_declarada"] = "OPF sem dc:language"
        self.r["aplicacoes_criadoras"] = _aplicacoes(meta)

    def sumario(self):
        if self.opf is None:
            self.lac["sumario"] = "OPF ilegível: sem manifest para achar nav nem NCX"
            return
        epub2 = (self.b["versao"] or "").strip().startswith("2")
        motivos = []
        achado = None if epub2 else self.sumario_nav(motivos)
        if achado is None:
            achado = self.sumario_ncx(motivos)
        if achado is None:
            self.lac["sumario"] = "; ".join(motivos) or "sem sumário declarado"
            return
        if motivos and not epub2:
            self.lac["sumario_nav"] = "nav não usado (" + "; ".join(motivos) + "); valeu o NCX"
        self.b["sumario"] = achado
        self.r["estrutura_declarada"] = [{"fonte": "epub_" + achado["fonte"],
                                          "entradas": achado["entradas"],
                                          "profundidade": achado["profundidade"]}]

    def sumario_nav(self, motivos):
        candidatos = [i for i in self.itens.values() if "nav" in i["props"]]
        if not candidatos:
            motivos.append("sem item do manifest com properties=nav")
        for item in candidatos:
            dados, motivo = self.membro(item)
            if dados is None:
                motivos.append(motivo)
                continue
            try:
                achado = _nav_toc(_decodificar(dados, None)[2])
            except Exception as e:
                motivos.append(f"{item['href']}: {_uma_linha(e)}")
                continue
            if achado is not None:
                return achado
            motivos.append(f"{item['href']}: sem nav epub:type=toc")
        return None

    def sumario_ncx(self, motivos):
        if not self.toc_id:
            motivos.append("sem spine@toc")
            return None
        item = self.itens.get(self.toc_id)
        if item is None:
            motivos.append(f"spine@toc={self.toc_id} fora do manifest")
            return None
        dados, motivo = self.membro(item)
        if dados is None:
            motivos.append(motivo)
            return None
        raiz, motivo = _xml(dados)
        achado = _ncx(raiz) if raiz is not None else None
        if achado is None:
            motivos.append(f"NCX {item['href']}: {motivo or 'sem navMap'}")
        return achado

    def palpite(self, dados):
        """(nome, texto) pelo charset_normalizer; None se ausente ou sem palpite."""
        if self.cn is None:
            return None
        self.r["bibliotecas"]["charset_normalizer"] = _versao_lib("charset-normalizer")
        try:
            achado = self.cn.from_bytes(dados).best()
            if achado is None:
                return None
            return _nome_canonico(achado.encoding), dados.decode(achado.encoding, errors="replace")
        except Exception:
            return None

    def documento(self, dados, enc):
        """Texto visível de um XHTML da spine; os 30 primeiros também entram no encoding."""
        n = self.b["membros"]["xhtml_lidos"]
        if n < XHTML_ENCODING:
            det, bom, texto, sem_palpite = _decodificar(dados, self.palpite)
            self.n_chute += sem_palpite
            declarado = _declarado(texto)
            bate = None if declarado is None else _bate(declarado, det, dados)
            enc.somar(det, bom, declarado, bate)
        else:
            texto = _decodificar_resto(dados, enc.padrao())
        self.b["membros"]["xhtml_lidos"] = n + 1
        try:
            return _extrair_texto(texto)
        except Exception:
            self.n_torto += 1
            return ""

    def texto(self):
        if self.opf is None:
            self.lac["_texto"] = "OPF ilegível: sem spine para ler"
            return
        self.cn = _importar_detector()
        enc, pecas, total = _Encodings(), [], 0
        for idref in dict.fromkeys(self.refs):
            if self.prazo.estourou():
                self.marcar_prazo("leitura da spine")
                break
            if total >= LIMITE_TEXTO:
                self.lac["_texto"] = f"truncado em {LIMITE_TEXTO} caracteres"
                break
            item = self.itens.get(idref)
            if item is None:
                self.faltas.append(f"idref {idref!r} fora do manifest")
            elif _e_html(item):
                dados, motivo = self.membro(item)
                if dados is None:
                    self.faltas.append(motivo)
                    continue
                txt = self.documento(dados, enc)
                if txt:
                    pecas.append(txt)
                    total += len(txt) + 1
        self.fechar_texto(enc, pecas)

    def fechar_texto(self, enc, pecas):
        if self.faltas:
            self.lac["spine"] = (f"{len(self.faltas)} item(ns) da spine não lido(s): "
                                 + "; ".join(self.faltas[:5]))
        if self.n_torto:
            self.lac["html"] = f"{self.n_torto} documento(s) com HTML ilegível, ignorados"
        if not self.b["membros"]["xhtml_lidos"]:
            self.lac.setdefault("_texto", "nenhum XHTML da spine lido")
            self.lac["encoding"] = "nenhum XHTML da spine lido"
            return
        texto = NL.join(pecas)
        if len(texto) > LIMITE_TEXTO:
            self.lac["_texto"] = f"truncado em {LIMITE_TEXTO} caracteres"
        self.r["_texto"] = texto[:LIMITE_TEXTO]
        self.r["encoding"] = enc.resultado()
        if self.n_chute:
            quem = "charset_normalizer ausente" if self.cn is None else "charset_normalizer sem palpite"
            self.lac["encoding"] = (f"{quem}; windows-1252 assumido em {self.n_chute} "
                                    "arquivo(s) fora de UTF-8 e sem BOM")

    def avisos(self):
        self.inibidor()
        div = self.pac.divergentes
        if div:
            amostra = "; ".join(f"{p} -> {v}" for p, v in list(div.items())[:3])
            self.lac["caixa"] = (f"{len(div)} caminho(s) achado(s) só com grafia divergente "
                                 f"(caixa), sem correção: {amostra}")

    def inibidor(self):
        c = self.b["criptografia"]
        if self.senha:
            tipo, alvo = "Password protection", _resumo(self.senha, "membro(s)")
        elif c["outra_criptografia"] or c["rights_xml"]:
            tipo = "DRM"
            alvo = _alvo_drm(c["algoritmos"] or [], self.pares, bool(c["rights_xml"]))
        elif c["ofuscacao_fonte"]:
            tipo, alvo = "Font obfuscation", f"{self.n_fontes} fontes"
        else:
            return
        self.r["inibidor"] = {"tipo": tipo, "alvo": alvo}


def ler(dados, ctx):
    """Lê os bytes de um EPUB e devolve o envelope do censo. Nunca levanta."""
    r = _resposta_vazia()
    try:
        _Leitor(dados, ctx or {}, r).rodar()
    except Exception as e:  # o contrato manda voltar o erro, não levantar
        r["erro"] = "falha inesperada: " + _uma_linha(e)
    return r
