"""formatos.py — os leitores dos formatos do acervo (spec ler-arquivo §7.4, emenda de 04/10/2026).

Tudo o que o acervo guarda se lê pela porta. Este módulo é a parte da leitura que conhece
formato: decide o tipo real de um binário pelo que há dentro dele (§7.2, §7.4.4), abre o
arquivo original e devolve o texto de cada unidade em ordem de leitura do formato (§7.4.3),
a imagem da página quando o formato tem renderizador (§7.4.2) e o membro de um ZIP.

Puro, como o `leitura.py` que o chama: não importa FastMCP, não fala com a rede, não grava
nada — não gera espelho, índice nem impressão (isso é do transcritor, spec
espelho-de-leitura). Biblioteca padrão (zipfile, xml.etree, html.parser, email) mais o
pymupdf, que entra no venv `ops` da release (§7.4.7); sem ele o PDF recusa com nome.

Vocabulário: **unidade** é a divisão fixa do original (arq:0117 §6) — página no PDF, slide no
PPTX, planilha no XLSX, item do spine no EPUB; `nenhuma` no DOCX, HTML e MHTML. **Documento**
é o arquivo aberto: diz quantas unidades tem e devolve o texto (ou a imagem) de uma.
"""
from __future__ import annotations

import email
import email.policy
import io
import re
import struct
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

try:                                    # §7.4.7: software livre, no venv ops da release
    import pymupdf
except ImportError:                     # pragma: no cover — a recusa nomeia a falta
    pymupdf = None

# --- tipos (nome MIME) -------------------------------------------------------------------------
PDF = "application/pdf"
EPUB = "application/epub+zip"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HTML = "text/html"
MHTML = "application/x-mhtml"           # o nome que o catálogo da casa usa (conversor/contrato.py)
MOBI = "application/x-mobipocket-ebook"   # fora da tabela da §7.4, mas o acervo o guarda (2 obras
                                          # vivas em 04/10/2026): o MuPDF o abre, e lê-se por ele
ZIP = "application/zip"
PNG, JPEG, GIF, WEBP = "image/png", "image/jpeg", "image/gif", "image/webp"
IMAGENS = (PNG, JPEG, GIF, WEBP)

# A tabela da §7.4: tipo -> unidade. O que não está aqui e é binário recusa `sem_leitor`.
UNIDADE = {PDF: "pagina", EPUB: "item", PPTX: "slide", XLSX: "planilha",
           DOCX: "nenhuma", HTML: "nenhuma", MHTML: "nenhuma", ZIP: "nenhuma", MOBI: "nenhuma",
           PNG: "imagem", JPEG: "imagem", GIF: "imagem", WEBP: "imagem"}
# Rótulo da unidade na marca `<!-- p. N -->` e no cabeçalho.
ROTULO = {"pagina": "página", "item": "item", "slide": "slide", "planilha": "planilha"}
LEITORES = frozenset(UNIDADE)
DPI_PADRAO, DPI_MAX = 150, 300
IMAGEM_TETO = 4 * 1024 * 1024          # bytes de PNG por chamada em modo="pagina" (≥ 1 imagem)
MEMBRO_MAX = 64 * 1024 * 1024          # membro de ZIP lido em memória

# --- namespaces OOXML / EPUB -------------------------------------------------------------------
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_XML = "{http://www.w3.org/XML/1998/namespace}"
_OPF = "{http://www.idpf.org/2007/opf}"
_CNT = "{urn:oasis:names:tc:opendocument:xmlns:container}"
_XLINK = "{http://www.w3.org/1999/xlink}"


# ============================================================== tipo real (§7.2, §7.4.4)
def tipo_do_zip(fh) -> str:
    """O que um ZIP é, pelo que há dentro, nunca pelo nome (F2 da lista antipadroes-de-transcricao).

    EPUB tem `mimetype` (ou, faltando ele, `META-INF/container.xml`); DOCX tem
    `word/document.xml`; PPTX, `ppt/presentation.xml`; XLSX, `xl/workbook.xml`. O resto é ZIP.
    ZIP que não abre volta como ZIP e a leitura dirá que não abre.
    """
    try:
        fh.seek(0)
        with zipfile.ZipFile(fh) as zf:
            nomes = set(zf.namelist())
            if "mimetype" in nomes:
                try:
                    if zf.read("mimetype").strip() == b"application/epub+zip":
                        return EPUB
                except (zipfile.BadZipFile, KeyError, OSError):
                    pass
            if "META-INF/container.xml" in nomes:
                return EPUB
            if "word/document.xml" in nomes:
                return DOCX
            if "ppt/presentation.xml" in nomes:
                return PPTX
            if "xl/workbook.xml" in nomes:
                return XLSX
    except (zipfile.BadZipFile, OSError, ValueError):
        pass
    return ZIP


_HTML_MARCAS = (b"<!doctype html", b"<html", b"<head", b"<body", b"<?xml", b"<meta", b"<title")
_MHTML_CABECA = re.compile(rb"^(from:|mime-version:|content-type:\s*multipart/related|"
                           rb"subject:|snapshot-content-location:)", re.I | re.M)


def tipo_texto(cabeca: bytes, tipo_nome: str) -> str:
    """HTML e MHTML pelos bytes: o «desconhecido» do catálogo quase sempre é um deles sem
    extensão. Só reclassifica texto plano ou o que o nome já dizia; não mexe no resto."""
    if tipo_nome not in ("text/plain", HTML, "application/xml"):
        return tipo_nome
    inicio = cabeca[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    if _MHTML_CABECA.match(inicio) and (b"multipart/related" in cabeca.lower()
                                        or b"boundary=" in cabeca.lower()):
        return MHTML
    baixo = inicio[:1024].lower()
    if any(baixo.startswith(m) for m in _HTML_MARCAS[:4]) or \
       (tipo_nome == HTML) or (b"<html" in baixo and b">" in baixo):
        return HTML
    return tipo_nome


def e_webp(cabeca: bytes) -> bool:
    return cabeca[:4] == b"RIFF" and cabeca[8:12] == b"WEBP"


# ============================================================== tabela GFM
def tabela_gfm(linhas: list[list[str]]) -> str:
    """Tabela GFM: a primeira linha é cabeçalho, as células escapam `|` e perdem a quebra
    (spec espelho-de-leitura §2.2: tabela como tabela, nunca uma célula por linha)."""
    if not linhas:
        return ""
    largura = max(len(l) for l in linhas)

    def cel(c: str) -> str:
        return re.sub(r"\s+", " ", (c or "")).strip().replace("|", "\\|")
    saida = []
    for i, l in enumerate(linhas):
        cells = [cel(c) for c in l] + [""] * (largura - len(l))
        saida.append("| " + " | ".join(cells) + " |")
        if i == 0:
            saida.append("|" + "|".join([" --- "] * largura) + "|")
    return "\n".join(saida)


def _limpa(texto: str) -> str:
    """Três ou mais linhas em branco viram duas; sem espaço pendurado; termina em `\\n`."""
    texto = "\n".join(l.rstrip() for l in texto.split("\n"))
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip("\n")
    return texto + "\n" if texto else ""


# ============================================================== o documento
@dataclass
class Documento:
    tipo: str
    unidade: str                                   # pagina · item · slide · planilha · nenhuma · imagem
    n: int                                         # unidades; 1 quando `nenhuma`
    nomes: list[str] = field(default_factory=list)  # rótulo por unidade (href do EPUB, nome da planilha)
    membros: list[tuple[str, int]] = field(default_factory=list)   # ZIP: (nome, bytes)
    render: bool = False                           # tem imagem da unidade (§7.4.2)
    imagem_propria: bytes | None = None            # PNG/JPEG/GIF/WEBP: o próprio arquivo
    dimensoes: tuple[int, int] | None = None
    _texto: dict = field(default_factory=dict, repr=False)
    _fonte: object = field(default=None, repr=False)

    def texto(self, i: int) -> str:
        """O texto da unidade `i` (base 1), em ordem de leitura do formato, terminado em `\\n`;
        vazio quando a unidade não tem caractere (página sem camada de texto)."""
        if i not in self._texto:
            self._texto[i] = _limpa(self._extrai(i))
        return self._texto[i]

    def _extrai(self, i: int) -> str:            # cada formato sobrescreve
        return ""

    def imagem(self, i: int, dpi: int = DPI_PADRAO) -> tuple[bytes | None, str, dict]:
        """(bytes, mime, extra) da unidade como imagem; `None` quando não há renderizador."""
        if self.imagem_propria is not None:
            return self.imagem_propria, self.tipo, {"dimensoes": self.dimensoes}
        return None, "", {}

    def fecha(self) -> None:
        pass


# ---------------------------------------------------------------- PDF (pymupdf)
class _Pdf(Documento):
    def __init__(self, fonte, nome: str = ""):
        if pymupdf is None:
            raise RuntimeError("pymupdf ausente do venv ops: PDF sem leitor")
        if isinstance(fonte, (bytes, bytearray)):
            doc = pymupdf.open(stream=bytes(fonte), filetype="pdf")
        else:
            doc = pymupdf.open(str(fonte))
        if doc.needs_pass:
            doc.close()
            raise ValueError("PDF cifrado: pede senha")
        super().__init__(tipo=PDF, unidade="pagina", n=doc.page_count, render=True)
        self._fonte = doc

    def _extrai(self, i: int) -> str:
        pagina = self._fonte[i - 1]
        # A camada de texto como o MuPDF a dá, em ordem de leitura do formato ("text", sem
        # reordenar); sem ligadura guardada e sem código de glifo no lugar de U+FFFD, para o
        # glifo sem mapa aparecer como o que é (spec espelho-de-leitura §2.9, FLAGS_R).
        flags = pymupdf.TEXT_PRESERVE_WHITESPACE
        if int(pagina.rotation) % 180 == 0:        # em página com /Rotate 90 ou 270 o recorte
            flags |= pymupdf.TEXT_MEDIABOX_CLIP     # pela mediabox descarta parte da camada
        return pagina.get_text("text", flags=flags)

    def imagem(self, i: int, dpi: int = DPI_PADRAO):
        dpi = max(36, min(int(dpi or DPI_PADRAO), DPI_MAX))
        pagina = self._fonte[i - 1]
        # `get_pixmap(dpi=N)` grava o DPI no PNG (caderno engenharia/devops, pymupdf 1.28);
        # o pixmap já sai no referencial girado da página (/Rotate aplicado).
        pix = pagina.get_pixmap(dpi=dpi, alpha=False)
        return pix.tobytes("png"), PNG, {"dimensoes": (pix.width, pix.height), "dpi": dpi}

    def fecha(self) -> None:
        try:
            self._fonte.close()
        except Exception:                                 # noqa: BLE001
            pass


class _Mobi(Documento):
    """MOBI pelo MuPDF (que o converte em fluxo): o original não tem unidade fixa, então o
    texto sai inteiro, em ordem, sem marca de página (as páginas do MuPDF são de layout, não
    do arquivo — arq:0117 §6: o leitor não inventa página)."""

    def __init__(self, fonte):
        if pymupdf is None:
            raise RuntimeError("pymupdf ausente do venv ops: MOBI sem leitor")
        if isinstance(fonte, (bytes, bytearray)):
            doc = pymupdf.open(stream=bytes(fonte), filetype="mobi")
        else:
            doc = pymupdf.open(str(fonte), filetype="mobi")
        super().__init__(tipo=MOBI, unidade="nenhuma", n=1)
        self._fonte = doc

    def _extrai(self, i: int) -> str:
        partes = []
        for pagina in self._fonte:
            partes.append(pagina.get_text("text"))
        return "\n".join(partes)

    def fecha(self) -> None:
        try:
            self._fonte.close()
        except Exception:                                 # noqa: BLE001
            pass


# ---------------------------------------------------------------- HTML (texto visível)
_IGNORA = {"script", "style", "noscript", "template", "svg", "math", "iframe", "object",
           "embed", "canvas", "audio", "video", "map", "datalist"}
_BLOCO = {"p", "div", "section", "article", "header", "footer", "nav", "aside", "main",
          "ul", "ol", "dl", "dt", "dd", "li", "blockquote", "pre", "hr", "table", "figure",
          "figcaption", "details", "summary", "address", "form", "fieldset", "legend",
          "h1", "h2", "h3", "h4", "h5", "h6", "tr", "caption", "thead", "tbody", "tfoot",
          "body", "html", "head", "title", "center", "menu", "option", "label"}
_BLOCO_CURTO = {"li", "dt", "dd", "tr", "option", "label", "title"}
_VAZIAS = {"br", "img", "hr", "meta", "link", "input", "wbr", "source", "col", "area", "base",
           "embed", "param", "track"}
_OCULTO = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)


class _TextoVisivel(HTMLParser):
    """O texto visível em ordem de documento: sem script e estilo, bloco em linha própria,
    título com `#`, item de lista com `- `, tabela como tabela GFM, `<img>` listada pelo
    caminho (§7.4: «imagens internas listadas pelo caminho, e lidas como imagem»)."""

    def __init__(self, base: str = ""):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.partes: list[str] = []
        self.oculto: list[str] = []            # pilha das tags abertas dentro de trecho oculto
        self.pre = 0
        self.tabelas: list[dict] = []           # pilha: {"linhas": [], "linha": None, "cel": None}
        self.imagens: list[str] = []

    # -- saída
    def _emite(self, s: str) -> None:
        if self.tabelas and self.tabelas[-1]["cel"] is not None:
            self.tabelas[-1]["cel"].append(s)
        else:
            self.partes.append(s)

    def _quebra(self, n: int = 1) -> None:
        self._emite("\n" * n)

    # -- eventos
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.oculto:
            if tag not in _VAZIAS:
                self.oculto.append(tag)
            return
        if tag in _IGNORA or ("hidden" in a and a.get("hidden") != "false") or \
           _OCULTO.search(a.get("style") or ""):
            if tag not in _VAZIAS:
                self.oculto.append(tag)
            return
        if tag == "br":
            self._quebra()
        elif tag == "img":
            src = (a.get("src") or a.get("data-src") or "").strip()
            alt = (a.get("alt") or "").strip()
            if src and not src.startswith("data:"):
                caminho = _resolve(self.base, src)
                self.imagens.append(caminho)
                self._emite(f"[imagem: {caminho}{' — ' + alt if alt else ''}]")
            elif alt:
                self._emite(f"[imagem: {alt}]")
        elif tag == "table":
            self._quebra(2)
            self.tabelas.append({"linhas": [], "linha": None, "cel": None})
        elif tag == "tr" and self.tabelas:
            t = self.tabelas[-1]
            t["linha"] = []
            t["linhas"].append(t["linha"])
        elif tag in ("td", "th") and self.tabelas and self.tabelas[-1]["linha"] is not None:
            t = self.tabelas[-1]
            t["cel"] = []
            t["linha"].append(t["cel"])
            try:
                span = max(1, int(a.get("colspan") or 1))
            except ValueError:
                span = 1
            t["span"] = span
        elif tag in _BLOCO:
            self._quebra(2 if tag not in _BLOCO_CURTO else 1)
            if tag[0] == "h" and tag[1:].isdigit():
                self._emite("#" * int(tag[1]) + " ")
            elif tag == "li":
                self._emite("- ")
            elif tag == "pre":
                self.pre += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VAZIAS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.oculto:
            # fecha o trecho oculto no fim da própria tag que o abriu (pilha de aninhamento)
            if tag in self.oculto:
                while self.oculto and self.oculto.pop() != tag:
                    pass
            return
        if tag in ("td", "th") and self.tabelas and self.tabelas[-1]["cel"] is not None:
            t = self.tabelas[-1]
            texto = "".join(t["cel"])
            t["linha"][-1] = texto
            for _ in range(t.get("span", 1) - 1):      # célula mesclada repete (§2.2 do espelho)
                t["linha"].append(texto)
            t["cel"] = None
        elif tag == "table" and self.tabelas:
            t = self.tabelas.pop()
            linhas = [[c if isinstance(c, str) else "".join(c) for c in l] for l in t["linhas"]]
            linhas = [l for l in linhas if any(c.strip() for c in l)]
            self._emite(tabela_gfm(linhas))
            self._quebra(2)
        elif tag in _BLOCO:
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
            self._quebra(2 if tag not in _BLOCO_CURTO else 1)

    def handle_data(self, data):
        if self.oculto:
            return
        if not self.pre:
            data = re.sub(r"[ \t\r\n\f]+", " ", data)
            if not data.strip():
                return
            alvo = self.tabelas[-1]["cel"] if self.tabelas and self.tabelas[-1]["cel"] is not None \
                else self.partes
            if not alvo or alvo[-1].endswith("\n"):
                data = data.lstrip(" ")
        self._emite(data)

    def texto(self) -> str:
        bruto = "".join(self.partes)
        # espaço antes da quebra some (o de depois fica: é o recuo do <pre>)
        return re.sub(r" +\n", "\n", bruto)


def _resolve(base: str, ref: str) -> str:
    from urllib.parse import unquote
    ref = unquote(ref.split("#")[0].split("?")[0])
    if not base or ref.startswith(("/", "http:", "https:")):
        return ref.lstrip("/") if not ref.startswith("http") else ref
    try:
        from posixpath import normpath, join
        return normpath(join(base, ref))
    except Exception:                                     # noqa: BLE001
        return ref


def html_para_texto(dados: bytes | str, *, base: str = "", encoding: str | None = None) -> tuple[str, list[str]]:
    """(texto visível, imagens por caminho) de um HTML ou XHTML."""
    if isinstance(dados, (bytes, bytearray)):
        s = decodifica(bytes(dados), encoding)
    else:
        s = dados
    p = _TextoVisivel(base)
    try:
        p.feed(s)
        p.close()
    except Exception:                                     # noqa: BLE001 — HTML torto segue
        pass
    return p.texto(), p.imagens


def decodifica(dados: bytes, declarado: str | None = None) -> str:
    """Os bytes decidem antes da declaração (P7 da lista antipadroes-de-transcricao; o leitor
    de referência da casa viu o charset declarado produzir U+FFFD aos milhares): UTF-8
    estrito; senão o charset declarado (parâmetro, XML ou meta); senão cp1252."""
    if dados.startswith(b"\xef\xbb\xbf"):
        dados = dados[3:]
    try:
        return dados.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for enc in (declarado, _charset_declarado(dados)):
        if enc and enc not in ("utf-8", "utf8"):
            try:
                return dados.decode(enc, "replace")
            except LookupError:
                continue
    return dados.decode("cp1252", "replace")


_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?\s*([-\w.:]+)""", re.I)
_XML_ENC = re.compile(rb"""^\s*<\?xml[^>]*encoding=["']([-\w.:]+)""", re.I)


def _charset_declarado(dados: bytes) -> str | None:
    cabeca = dados[:4096]
    m = _XML_ENC.match(cabeca) or _META_CHARSET.search(cabeca)
    if m:
        try:
            import codecs
            return codecs.lookup(m.group(1).decode("ascii", "ignore")).name
        except LookupError:
            return None
    return None


class _Html(Documento):
    def __init__(self, dados: bytes, encoding: str | None = None):
        super().__init__(tipo=HTML, unidade="nenhuma", n=1)
        self._dados, self._enc = dados, encoding

    def _extrai(self, i: int) -> str:
        texto, _imgs = html_para_texto(self._dados, encoding=self._enc)
        return texto


class _Mhtml(Documento):
    """Desembrulha a parte HTML (a primeira `text/html`) e a lê como HTML (§7.4)."""

    def __init__(self, dados: bytes):
        super().__init__(tipo=MHTML, unidade="nenhuma", n=1)
        self._dados = dados

    def _extrai(self, i: int) -> str:
        msg = email.message_from_bytes(self._dados, policy=email.policy.compat32)
        partes = [msg] if not msg.is_multipart() else list(msg.walk())
        for parte in partes:
            if parte.get_content_type() == HTML:
                corpo = parte.get_payload(decode=True) or b""
                texto, _ = html_para_texto(corpo, encoding=parte.get_content_charset())
                return texto
        # Sem parte HTML: a primeira parte de texto que houver.
        for parte in partes:
            if parte.get_content_maintype() == "text":
                corpo = parte.get_payload(decode=True) or b""
                return decodifica(corpo, parte.get_content_charset())
        return ""


# ---------------------------------------------------------------- EPUB
class _Epub(Documento):
    """Itens do spine em ordem; cada um é uma unidade (`item`), lido como XHTML visível.
    Imagens internas aparecem pelo caminho dentro do ZIP e se leem por `caminho!membro`."""

    def __init__(self, fh):
        self._zf = zipfile.ZipFile(fh)
        opf_caminho = self._acha_opf()
        base = str(PurePosixPath(opf_caminho).parent)
        base = "" if base == "." else base
        raiz = ET.fromstring(self._zf.read(opf_caminho))
        manifesto = {}
        for item in raiz.iter(f"{_OPF}item"):
            manifesto[item.get("id")] = (_resolve(base, item.get("href") or ""),
                                         item.get("media-type") or "")
        spine = [ref.get("idref") for ref in raiz.iter(f"{_OPF}itemref")]
        self._itens = [(manifesto[i][0]) for i in spine if i in manifesto]
        if not self._itens:                      # sem spine: todo XHTML do manifesto, em ordem
            self._itens = [h for h, mt in manifesto.values() if "html" in mt or "xml" in mt]
        nomes = set(self._zf.namelist())
        self._itens = [h for h in self._itens if h in nomes]
        super().__init__(tipo=EPUB, unidade="item", n=len(self._itens), nomes=list(self._itens))
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist()
                        if not i.is_dir()]

    def _acha_opf(self) -> str:
        try:
            cont = ET.fromstring(self._zf.read("META-INF/container.xml"))
            for rf in cont.iter(f"{_CNT}rootfile"):
                if rf.get("full-path"):
                    return rf.get("full-path")
        except (KeyError, ET.ParseError):
            pass
        for nome in self._zf.namelist():         # container ausente: o primeiro .opf
            if nome.lower().endswith(".opf"):
                return nome
        raise ValueError("EPUB sem OPF (nem container.xml nem arquivo .opf)")

    def _extrai(self, i: int) -> str:
        href = self._itens[i - 1]
        base = str(PurePosixPath(href).parent)
        texto, _ = html_para_texto(self._zf.read(href), base="" if base == "." else base)
        return f"item: {href}\n\n{texto}"

    def membro(self, nome: str) -> bytes:
        return self._zf.read(nome)

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- DOCX
_TITULO_RE = re.compile(r"^(?:heading|t[ií]tulo|ttulo)\s*(\d)$", re.I)


class _Docx(Documento):
    """Parágrafos e tabelas na ordem do `word/document.xml`; notas e comentários ao fim,
    marcados (§7.4). Sem unidade: a página do DOCX é do renderizador (espelho §2.6)."""

    def __init__(self, fh):
        self._zf = zipfile.ZipFile(fh)
        super().__init__(tipo=DOCX, unidade="nenhuma", n=1)
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()]

    def _ler(self, nome: str):
        try:
            return ET.fromstring(self._zf.read(nome))
        except (KeyError, ET.ParseError):
            return None

    def _estilos(self) -> dict:
        raiz = self._ler("word/styles.xml")
        estilos = {}
        if raiz is None:
            return estilos
        for st in raiz.iter(f"{_W}style"):
            sid = st.get(f"{_W}styleId") or ""
            nome_el = st.find(f"{_W}name")
            nome = nome_el.get(f"{_W}val") if nome_el is not None else sid
            nivel = None
            m = _TITULO_RE.match((nome or "").strip()) or _TITULO_RE.match(sid)
            if m:
                nivel = int(m.group(1))
            ol = st.find(f"{_W}pPr/{_W}outlineLvl")
            if nivel is None and ol is not None and (ol.get(f"{_W}val") or "").isdigit():
                nivel = int(ol.get(f"{_W}val")) + 1
            estilos[sid] = nivel
        return estilos

    @staticmethod
    def _texto_paragrafo(p) -> str:
        partes = []
        for el in p.iter():
            tag = el.tag
            if tag == f"{_W}t":
                partes.append(el.text or "")
            elif tag == f"{_W}tab":
                partes.append("\t")
            elif tag in (f"{_W}br", f"{_W}cr"):
                partes.append("\n")
            elif tag == f"{_W}footnoteReference":
                partes.append(f"[^{el.get(f'{_W}id')}]")
            elif tag == f"{_W}endnoteReference":
                partes.append(f"[^e{el.get(f'{_W}id')}]")
            elif tag == f"{_W}commentReference":
                partes.append(f"[c{el.get(f'{_W}id')}]")
            elif tag == f"{_W}delText":
                continue
        return "".join(partes)

    def _paragrafo(self, p, estilos: dict) -> str:
        texto = self._texto_paragrafo(p).strip()
        if not texto:
            return ""
        ppr = p.find(f"{_W}pPr")
        nivel = None
        lista = False
        if ppr is not None:
            ps = ppr.find(f"{_W}pStyle")
            if ps is not None:
                nivel = estilos.get(ps.get(f"{_W}val"))
            ol = ppr.find(f"{_W}outlineLvl")
            if nivel is None and ol is not None and (ol.get(f"{_W}val") or "").isdigit():
                nivel = int(ol.get(f"{_W}val")) + 1
            lista = ppr.find(f"{_W}numPr") is not None
        if nivel:
            return "#" * min(nivel, 6) + " " + texto
        if lista:
            return "- " + texto
        return texto

    def _tabela(self, tbl, estilos: dict) -> str:
        linhas: list[list[str]] = []
        for tr in tbl.findall(f"{_W}tr"):
            linha: list[str] = []
            for tc in tr.findall(f"{_W}tc"):
                texto = " ".join(t for t in (self._paragrafo(p, estilos)
                                             for p in tc.findall(f"{_W}p")) if t)
                tcpr = tc.find(f"{_W}tcPr")
                span, vmerge = 1, None
                if tcpr is not None:
                    gs = tcpr.find(f"{_W}gridSpan")
                    if gs is not None and (gs.get(f"{_W}val") or "").isdigit():
                        span = int(gs.get(f"{_W}val"))
                    vm = tcpr.find(f"{_W}vMerge")
                    if vm is not None:
                        vmerge = vm.get(f"{_W}val") or "continue"
                if vmerge == "continue" and linhas:          # mescla vertical repete o de cima
                    col = len(linha)
                    texto = linhas[-1][col] if col < len(linhas[-1]) else texto
                linha.extend([texto] * span)
            linhas.append(linha)
        return tabela_gfm(linhas)

    def _blocos(self, pai, estilos: dict, saida: list[str]) -> None:
        for el in pai:
            tag = el.tag
            if tag == f"{_W}p":
                t = self._paragrafo(el, estilos)
                if t:
                    saida.append(t)
            elif tag == f"{_W}tbl":
                saida.append(self._tabela(el, estilos))
            elif tag == f"{_W}sdt":
                cont = el.find(f"{_W}sdtContent")
                if cont is not None:
                    self._blocos(cont, estilos, saida)
            elif tag in (f"{_W}sectPr", f"{_W}bookmarkStart", f"{_W}bookmarkEnd"):
                continue
            else:
                self._blocos(el, estilos, saida)

    def _notas(self, nome: str, tag: str, prefixo: str, estilos: dict) -> list[str]:
        raiz = self._ler(nome)
        if raiz is None:
            return []
        saida = []
        for nota in raiz.iter(f"{_W}{tag}"):
            if nota.get(f"{_W}type") in ("separator", "continuationSeparator"):
                continue
            corpo = []
            self._blocos(nota, estilos, corpo)
            if corpo:
                saida.append(f"[^{prefixo}{nota.get(f'{_W}id')}]: " + " ".join(corpo))
        return saida

    def _comentarios(self, estilos: dict) -> list[str]:
        raiz = self._ler("word/comments.xml")
        if raiz is None:
            return []
        saida = []
        for c in raiz.iter(f"{_W}comment"):
            corpo = []
            self._blocos(c, estilos, corpo)
            autor = c.get(f"{_W}author") or ""
            saida.append(f"[c{c.get(f'{_W}id')}] {autor + ': ' if autor else ''}" + " ".join(corpo))
        return saida

    def _extrai(self, i: int) -> str:
        raiz = self._ler("word/document.xml")
        if raiz is None:
            raise ValueError("DOCX sem word/document.xml legível")
        estilos = self._estilos()
        corpo = raiz.find(f"{_W}body")
        blocos: list[str] = []
        if corpo is not None:
            self._blocos(corpo, estilos, blocos)
        saida = "\n\n".join(blocos)
        notas = self._notas("word/footnotes.xml", "footnote", "", estilos) + \
            self._notas("word/endnotes.xml", "endnote", "e", estilos)
        if notas:
            saida += "\n\n<!-- notas -->\n\n" + "\n".join(notas)
        coment = self._comentarios(estilos)
        if coment:
            saida += "\n\n<!-- comentários -->\n\n" + "\n".join(coment)
        return saida

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- PPTX
class _Pptx(Documento):
    """Um slide por unidade, na ordem do `presentation.xml` (nunca a do nome do arquivo:
    O2 da lista antipadroes-de-transcricao); texto das formas e as notas do apresentador."""

    def __init__(self, fh):
        self._zf = zipfile.ZipFile(fh)
        rels = self._rels("ppt/_rels/presentation.xml.rels")
        raiz = ET.fromstring(self._zf.read("ppt/presentation.xml"))
        slides = []
        for sid in raiz.iter(f"{_P}sldId"):
            alvo = rels.get(sid.get(f"{_R}id"))
            if alvo:
                slides.append(_resolve("ppt", alvo))
        super().__init__(tipo=PPTX, unidade="slide", n=len(slides), nomes=slides)
        self._slides = slides
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()]

    def _rels(self, nome: str) -> dict:
        try:
            raiz = ET.fromstring(self._zf.read(nome))
        except (KeyError, ET.ParseError):
            return {}
        return {r.get("Id"): r.get("Target") for r in raiz.iter(f"{_REL}Relationship")
                if r.get("TargetMode") != "External"}

    def _rels_tipo(self, nome: str, sufixo: str) -> str | None:
        try:
            raiz = ET.fromstring(self._zf.read(nome))
        except (KeyError, ET.ParseError):
            return None
        for r in raiz.iter(f"{_REL}Relationship"):
            if (r.get("Type") or "").endswith(sufixo):
                return r.get("Target")
        return None

    @staticmethod
    def _paragrafos(txbody) -> list[str]:
        saida = []
        for p in txbody.findall(f"{_A}p"):
            partes = []
            for el in p.iter():
                if el.tag == f"{_A}t":
                    partes.append(el.text or "")
                elif el.tag == f"{_A}br":
                    partes.append("\n")
            t = "".join(partes).strip()
            if t:
                ppr = p.find(f"{_A}pPr")
                lvl = int(ppr.get("lvl") or 0) if ppr is not None and (ppr.get("lvl") or "0").isdigit() else 0
                saida.append(("  " * lvl + "- " + t) if lvl else t)
        return saida

    def _formas(self, pai, blocos: list[str], caminho_slide: str) -> None:
        for el in pai:
            tag = el.tag
            if tag == f"{_P}sp":
                ph = el.find(f"{_P}nvSpPr/{_P}nvPr/{_P}ph")
                tipo_ph = ph.get("type") if ph is not None else None
                tx = el.find(f"{_P}txBody")
                if tx is None:
                    continue
                pars = self._paragrafos(tx)
                if not pars:
                    continue
                if tipo_ph in ("title", "ctrTitle"):
                    blocos.append("# " + " ".join(pars))
                elif tipo_ph == "subTitle":
                    blocos.append("## " + " ".join(pars))
                elif tipo_ph in ("sldNum", "dt", "ftr"):
                    blocos.append(f"<!-- {tipo_ph}: {' '.join(pars)} -->")
                else:
                    blocos.append("\n".join(pars))
            elif tag == f"{_P}graphicFrame":
                tbl = next(el.iter(f"{_A}tbl"), None)
                if tbl is not None:
                    linhas = []
                    for tr in tbl.findall(f"{_A}tr"):
                        linha = []
                        for tc in tr.findall(f"{_A}tc"):
                            tx = tc.find(f"{_A}txBody")
                            texto = " ".join(self._paragrafos(tx)) if tx is not None else ""
                            span = int(tc.get("gridSpan") or 1)
                            linha.extend([texto] * max(1, span))
                        linhas.append(linha)
                    blocos.append(tabela_gfm(linhas))
                else:
                    textos = [t.text or "" for t in el.iter(f"{_A}t")]
                    if any(x.strip() for x in textos):
                        blocos.append(" ".join(x for x in textos if x.strip()))
            elif tag == f"{_P}grpSp":
                self._formas(el, blocos, caminho_slide)
            elif tag == f"{_P}pic":
                blip = next(el.iter(f"{_A}blip"), None)
                rid = blip.get(f"{_R}embed") if blip is not None else None
                rels = self._rels(_rels_de(caminho_slide))
                alvo = rels.get(rid)
                if alvo:
                    blocos.append(f"[imagem: {_resolve(str(PurePosixPath(caminho_slide).parent), alvo)}]")

    def _extrai(self, i: int) -> str:
        caminho = self._slides[i - 1]
        raiz = ET.fromstring(self._zf.read(caminho))
        arvore = raiz.find(f"{_P}cSld/{_P}spTree")
        blocos: list[str] = []
        if arvore is not None:
            self._formas(arvore, blocos, caminho)
        notas_alvo = self._rels_tipo(_rels_de(caminho), "/notesSlide")
        if notas_alvo:
            nome = _resolve(str(PurePosixPath(caminho).parent), notas_alvo)
            try:
                nraiz = ET.fromstring(self._zf.read(nome))
                narv = nraiz.find(f"{_P}cSld/{_P}spTree")
                notas: list[str] = []
                if narv is not None:
                    for sp in narv.iter(f"{_P}sp"):
                        ph = sp.find(f"{_P}nvSpPr/{_P}nvPr/{_P}ph")
                        if ph is not None and ph.get("type") in ("sldNum", "sldImg", "hdr", "ftr", "dt"):
                            continue
                        tx = sp.find(f"{_P}txBody")
                        if tx is not None:
                            notas.extend(self._paragrafos(tx))
                if notas:
                    blocos.append("<!-- notas do apresentador -->\n\n" + "\n\n".join(notas))
            except (KeyError, ET.ParseError):
                pass
        return "\n\n".join(blocos)

    def fecha(self) -> None:
        self._zf.close()


def _rels_de(caminho: str) -> str:
    p = PurePosixPath(caminho)
    return str(p.parent / "_rels" / (p.name + ".rels"))


# ---------------------------------------------------------------- XLSX
def _col_idx(ref: str) -> int:
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n


class _Xlsx(Documento):
    """Uma planilha por unidade, na ordem do `workbook.xml`; cada uma como tabela GFM com os
    valores (nunca a fórmula) e o nome da planilha (§7.4)."""

    def __init__(self, fh):
        self._zf = zipfile.ZipFile(fh)
        raiz = ET.fromstring(self._zf.read("xl/workbook.xml"))
        rels = _Pptx._rels(self, "xl/_rels/workbook.xml.rels")
        folhas = []
        for sh in raiz.iter(f"{_S}sheet"):
            alvo = rels.get(sh.get(f"{_R}id"))
            if alvo:
                folhas.append((sh.get("name") or "", _resolve("xl", alvo.lstrip("/")) if not alvo.startswith("/") else alvo.lstrip("/")))
        super().__init__(tipo=XLSX, unidade="planilha", n=len(folhas), nomes=[n for n, _ in folhas])
        self._folhas = folhas
        self._ss: list[str] | None = None
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()]

    def _shared(self) -> list[str]:
        if self._ss is None:
            self._ss = []
            try:
                raiz = ET.fromstring(self._zf.read("xl/sharedStrings.xml"))
                for si in raiz.iter(f"{_S}si"):
                    self._ss.append("".join(t.text or "" for t in si.iter(f"{_S}t")))
            except (KeyError, ET.ParseError):
                pass
        return self._ss

    def _valor(self, c) -> str:
        t = c.get("t") or "n"
        if t == "inlineStr":
            is_ = c.find(f"{_S}is")
            return "".join(x.text or "" for x in is_.iter(f"{_S}t")) if is_ is not None else ""
        v = c.find(f"{_S}v")
        val = (v.text or "") if v is not None else ""
        if t == "s":
            ss = self._shared()
            try:
                return ss[int(val)]
            except (ValueError, IndexError):
                return val
        if t == "b":
            return "VERDADEIRO" if val == "1" else "FALSO"
        if t == "n" and val:
            try:
                f = float(val)
                if f.is_integer() and "e" not in val.lower() and "." not in val:
                    return val
                return repr(f) if abs(f) < 1e15 else val
            except ValueError:
                return val
        return val

    def _extrai(self, i: int) -> str:
        nome, caminho = self._folhas[i - 1]
        try:
            raiz = ET.fromstring(self._zf.read(caminho))
        except KeyError:
            return f"planilha: {nome}\n\n(planilha sem dados)"
        celulas: dict[tuple[int, int], str] = {}
        for row in raiz.iter(f"{_S}row"):
            try:
                rn = int(row.get("r") or 0)
            except ValueError:
                rn = 0
            for col_auto, c in enumerate(row.findall(f"{_S}c"), 1):
                ref = c.get("r") or ""
                cn = _col_idx(ref) or col_auto
                if not rn:
                    rn = int(re.sub(r"\D", "", ref) or 0)
                val = self._valor(c)
                if val != "":
                    celulas[(rn, cn)] = val
        # mescla: o valor da célula de cima/esquerda repete na área coberta (espelho §2.2)
        for mc in raiz.iter(f"{_S}mergeCell"):
            ref = mc.get("ref") or ""
            if ":" in ref:
                a, b = ref.split(":")
                r1, c1 = int(re.sub(r"\D", "", a)), _col_idx(a)
                r2, c2 = int(re.sub(r"\D", "", b)), _col_idx(b)
                val = celulas.get((r1, c1), "")
                if val == "":
                    continue
                for r in range(r1, r2 + 1):
                    for cc in range(c1, c2 + 1):
                        celulas.setdefault((r, cc), val)
        if not celulas:
            return f"planilha: {nome}\n\n(planilha vazia)"
        linhas_idx = sorted({r for r, _ in celulas})
        c_min = min(c for _, c in celulas)
        c_max = max(c for _, c in celulas)
        grade = [[celulas.get((r, c), "") for c in range(c_min, c_max + 1)] for r in linhas_idx]
        return f"planilha: {nome}\n\n" + tabela_gfm(grade)

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- ZIP de outro tipo
class _Zip(Documento):
    """Listagem como diretório (§9.2); o membro se lê por `caminho!membro`."""

    def __init__(self, fh):
        self._zf = zipfile.ZipFile(fh)
        super().__init__(tipo=ZIP, unidade="nenhuma", n=1)
        self.membros = sorted((i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir())

    def _extrai(self, i: int) -> str:
        return "".join(f"{n}  {t}\n" for n, t in self.membros)

    def membro(self, nome: str) -> bytes:
        return self._zf.read(nome)

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- imagem
def dimensoes_imagem(cabeca: bytes, tipo: str) -> tuple[int, int] | None:
    try:
        if tipo == PNG and len(cabeca) >= 24:
            return struct.unpack(">II", cabeca[16:24])
        if tipo == GIF and len(cabeca) >= 10:
            return struct.unpack("<HH", cabeca[6:10])
        if tipo == WEBP and len(cabeca) >= 30:
            if cabeca[12:16] == b"VP8 ":
                return struct.unpack("<HH", cabeca[26:30])[0] & 0x3FFF, struct.unpack("<HH", cabeca[26:30])[1] & 0x3FFF
            if cabeca[12:16] == b"VP8L":
                b = cabeca[21:25]
                return (b[0] | ((b[1] & 0x3F) << 8)) + 1, ((b[1] >> 6) | (b[2] << 2) | ((b[3] & 0x0F) << 10)) + 1
            if cabeca[12:16] == b"VP8X":
                w = 1 + int.from_bytes(cabeca[24:27], "little")
                h = 1 + int.from_bytes(cabeca[27:30], "little")
                return w, h
        if tipo == JPEG:
            i = 2
            while i + 9 < len(cabeca):
                if cabeca[i] != 0xFF:
                    i += 1
                    continue
                marca = cabeca[i + 1]
                if marca in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", cabeca[i + 5:i + 9])
                    return w, h
                if marca in (0xD8, 0x01) or 0xD0 <= marca <= 0xD7:
                    i += 2
                    continue
                tam = struct.unpack(">H", cabeca[i + 2:i + 4])[0]
                i += 2 + tam
    except (struct.error, IndexError):
        return None
    return None


class _Imagem(Documento):
    def __init__(self, dados: bytes, tipo: str):
        super().__init__(tipo=tipo, unidade="imagem", n=1, render=True,
                         imagem_propria=dados, dimensoes=dimensoes_imagem(dados[:64], tipo))

    def _extrai(self, i: int) -> str:
        return ""


# ============================================================== abertura
def abre(tipo: str, *, fh=None, caminho=None, dados: bytes | None = None,
         encoding: str | None = None) -> Documento:
    """O Documento do tipo. `fh` é o arquivo aberto em binário (zip e OOXML leem dele);
    `caminho` serve ao PDF (abre do disco, sem carregar tudo); `dados` são bytes em memória
    (membro de ZIP, HTML já decodificado)."""
    if tipo in (PDF, MOBI):
        classe = _Pdf if tipo == PDF else _Mobi
        if dados is not None:
            return classe(dados)
        if caminho is not None:
            return classe(caminho)
        fh.seek(0)
        return classe(fh.read())
    fonte = io.BytesIO(dados) if dados is not None else fh
    if fonte is not None:
        fonte.seek(0)
    if tipo == EPUB:
        return _Epub(fonte)
    if tipo == DOCX:
        return _Docx(fonte)
    if tipo == PPTX:
        return _Pptx(fonte)
    if tipo == XLSX:
        return _Xlsx(fonte)
    if tipo == ZIP:
        return _Zip(fonte)
    if dados is None:
        fonte.seek(0)
        dados = fonte.read()
    if tipo == HTML:
        return _Html(dados, encoding)
    if tipo == MHTML:
        return _Mhtml(dados)
    if tipo in IMAGENS:
        return _Imagem(dados, tipo)
    raise ValueError(f"sem leitor para {tipo}")


def membro_de(doc: Documento, nome: str) -> bytes:
    """Os bytes de um membro de ZIP, EPUB ou OOXML, para ler por `caminho!membro`."""
    zf = getattr(doc, "_zf", None)
    if zf is None:
        raise KeyError(nome)
    info = zf.getinfo(nome)
    if info.file_size > MEMBRO_MAX:
        raise ValueError(f"membro acima de {MEMBRO_MAX // (1024 * 1024)} MiB")
    return zf.read(nome)
