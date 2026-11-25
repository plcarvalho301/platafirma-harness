"""formatos.py — os leitores dos formatos do acervo (spec ler-arquivo §7.4, DT 919).

Tudo o que o acervo guarda se lê pela porta. Este módulo é a parte da leitura que conhece
formato: decide o tipo real de um binário pelo que há dentro dele (§7.2, §7.4.4), abre o
arquivo original e devolve o texto de cada unidade em ordem de leitura do formato (§7.4.3),
a imagem da página quando o formato tem renderizador (§7.4.2) e o membro de um ZIP.

Puro, como o `leitura.py` que o chama: não importa FastMCP, não fala com a rede, não grava
nada — não gera espelho, índice nem impressão (isso é do transcritor, spec
espelho-de-leitura). Biblioteca padrão (zipfile, xml.etree, html.parser, email) mais o
pymupdf; sem ele o PDF recusa com nome.

Vocabulário: **unidade** é a divisão fixa do original (arq:0117 §6) — página no PDF, slide no
PPTX, planilha no XLSX, item do spine no EPUB; `nenhuma` no DOCX, HTML e MHTML. **Documento**
é o arquivo aberto: diz quantas unidades tem e devolve o texto (ou a imagem) de uma.
"""
from __future__ import annotations

import email
import email.policy
import gzip
import io
import re
import struct
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from xml.parsers import expat

try:                                    # §7.4.7: software livre, no venv do harness
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
MOBI = "application/x-mobipocket-ebook"
ZIP = "application/zip"
PNG, JPEG, GIF, WEBP = "image/png", "image/jpeg", "image/gif", "image/webp"
IMAGENS = (PNG, JPEG, GIF, WEBP)

# A tabela da §7.4: tipo -> unidade. O que não está aqui e é binário recusa `sem_leitor`.
UNIDADE = {
    PDF: "pagina",
    EPUB: "item",
    PPTX: "slide",
    XLSX: "planilha",
    DOCX: "nenhuma",
    HTML: "nenhuma",
    MHTML: "nenhuma",
    ZIP: "nenhuma",
    MOBI: "nenhuma",
    PNG: "imagem",
    JPEG: "imagem",
    GIF: "imagem",
    WEBP: "imagem",
}
ROTULO = {"pagina": "página", "item": "item", "slide": "slide", "planilha": "planilha"}
LEITORES = frozenset(UNIDADE)
DPI_PADRAO, DPI_MAX = 150, 300
IMAGEM_TETO = 4 * 1024 * 1024          # bytes de PNG por chamada em modo="pagina" (≥ 1 imagem)
MEMBRO_MAX = 64 * 1024 * 1024          # membro de ZIP/gzip lido em memória
MEMBROS_PACOTE_MAX = 10_000            # teto de quantidade de membros num pacote comprimido
SOMA_DESCOMPRIMIDA_MAX = 128 * 1024 * 1024  # teto da soma descomprimida numa mesma chamada
ANINHAMENTO_PACOTE_MAX = 1             # recusa pacote comprimido aninhado além de 1 nível
CHUNK_DESCOMPRESSAO = 64 * 1024        # bloco de leitura em fluxo contra bombas de compressão
RAZAO_COMPRESSAO_MAX = 100.0           # razão máxima descomprimido/comprimido acima de RAZAO_MIN_BYTES
RAZAO_MIN_BYTES = 64 * 1024            # abaixo disto, arquivos pequenos de zeros não disparam razão
CELULAS_XLSX_MAX = 200_000             # teto de células expandidas em planilha XLSX
GZIP = "application/gzip"
FORMATOS_ISOLADOS = frozenset({PDF, MOBI, EPUB, DOCX, PPTX, XLSX, ZIP, GZIP})
_FLOAT_REPR_MAX = 1e15
_PNG_CABECA_MIN = 24
_GIF_CABECA_MIN = 10
_WEBP_CABECA_MIN = 30
_JPEG_MARCADOR = 0xFF
_JPEG_RST_INI = 0xD0
_JPEG_RST_FIM = 0xD7

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


class ErroDescompressao(ValueError):
    """Arquivo comprimido ou XML viola limites de segurança (DT 832/899, story #4442)."""


class OrcamentoDescompressao:
    """Acumulador de bytes descomprimidos numa mesma chamada para conter soma de membros."""

    def __init__(self, limite_total: int = SOMA_DESCOMPRIMIDA_MAX) -> None:
        self.limite_total = limite_total
        self.acumulado = 0

    def consumir(self, n_bytes: int) -> None:
        self.acumulado += n_bytes
        if self.acumulado > self.limite_total:
            raise ErroDescompressao(
                f"soma descomprimida da chamada excedeu teto de {self.limite_total} bytes"
            )


def eh_assinatura_pacote(cabeca: bytes) -> bool:
    """Retorna True se os bytes iniciam pacote ZIP ou GZIP (para barrar aninhamento > 1)."""
    return cabeca.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\x1f\x8b"))


def _nome_clark(nome: str) -> str:
    if " " in nome:
        uri, local = nome.rsplit(" ", 1)
        return f"{{{uri}}}{local}"
    return nome


def parse_xml_seguro(dados: bytes | str) -> ET.Element:
    """Abre XML por parser Expat endurecido, recusando DTD, entidades e rede."""
    builder = ET.TreeBuilder()
    exp = expat.ParserCreate(namespace_separator=" ")
    exp.buffer_text = True

    def _recusar_dtd(*_args: object) -> None:
        raise ErroDescompressao("XML com declaração DOCTYPE recusado")

    def _recusar_entidade(*_args: object) -> None:
        raise ErroDescompressao("XML com declaração ENTITY recusado")

    def _recusar_notacao(*_args: object) -> None:
        raise ErroDescompressao("XML com declaração NOTATION recusado")

    def _recusar_externa(*_args: object) -> int:
        raise ErroDescompressao("XML com referência a entidade externa recusado")

    def _inicio(nome: str, attrs: dict[str, str]) -> None:
        attrs_clark = {_nome_clark(k): v for k, v in attrs.items()}
        builder.start(_nome_clark(nome), attrs_clark)

    def _fim(nome: str) -> None:
        builder.end(_nome_clark(nome))

    exp.StartDoctypeDeclHandler = _recusar_dtd
    exp.EntityDeclHandler = _recusar_entidade
    exp.UnparsedEntityDeclHandler = _recusar_entidade
    exp.NotationDeclHandler = _recusar_notacao
    exp.ExternalEntityRefHandler = _recusar_externa
    exp.StartElementHandler = _inicio
    exp.EndElementHandler = _fim
    exp.CharacterDataHandler = builder.data
    if hasattr(exp, "SetParamEntityParsing"):
        exp.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)

    try:
        exp.Parse(dados, True)
    except expat.ExpatError as exc:
        raise ET.ParseError(str(exc)) from exc
    return builder.close()


def validar_pacote_zip(
    zf: zipfile.ZipFile,
    *,
    nivel_aninhamento: int = 0,
    max_membros: int = MEMBROS_PACOTE_MAX,
    soma_max: int = SOMA_DESCOMPRIMIDA_MAX,
) -> None:
    """Valida limites de aninhamento, contagem de membros e soma declarada de um ZIP."""
    if nivel_aninhamento > ANINHAMENTO_PACOTE_MAX:
        raise ErroDescompressao(
            f"aninhamento de pacote comprimido excede o teto de {ANINHAMENTO_PACOTE_MAX} nível"
        )
    infos = zf.infolist()
    if len(infos) > max_membros:
        raise ErroDescompressao(
            f"pacote possui {len(infos)} membros (teto {max_membros})"
        )
    soma_declarada = sum(max(0, i.file_size) for i in infos if not i.is_dir())
    if soma_declarada > soma_max:
        raise ErroDescompressao(
            f"soma declarada do pacote ({soma_declarada} bytes) excede teto de {soma_max} bytes"
        )


def _valida_razao(descomprimido: int, comprimido: int | None, razao_max: float) -> None:
    if (
        comprimido
        and comprimido > 0
        and descomprimido > RAZAO_MIN_BYTES
        and (descomprimido / comprimido) > razao_max
    ):
        raise ErroDescompressao(
            f"razão de compressão acima de {int(razao_max)}x "
            f"({descomprimido} bytes de {comprimido} comprimidos)"
        )


def ler_zip_seguro(
    zf: zipfile.ZipFile,
    nome: str,
    limite: int = MEMBRO_MAX,
    razao_max: float = RAZAO_COMPRESSAO_MAX,
    *,
    orcamento: OrcamentoDescompressao | None = None,
    nivel_aninhamento: int = 0,
) -> bytes:
    """Lê membro de ZIP em fluxo até `limite` bytes, `razao_max` e teto de soma (DT 832/899)."""
    if nivel_aninhamento > ANINHAMENTO_PACOTE_MAX:
        raise ErroDescompressao(
            f"aninhamento de pacote comprimido excede o teto de {ANINHAMENTO_PACOTE_MAX} nível"
        )
    info = zf.getinfo(nome)
    if info.file_size > limite:
        raise ErroDescompressao(f"membro {nome!r} declara {info.file_size} bytes (teto {limite})")
    _valida_razao(info.file_size, info.compress_size, razao_max)
    partes: list[bytes] = []
    total = 0
    with zf.open(info, "r") as stream:
        while True:
            bloco = stream.read(CHUNK_DESCOMPRESSAO)
            if not bloco:
                break
            total += len(bloco)
            if total > limite:
                raise ErroDescompressao(f"membro {nome!r} atingiu teto de {limite} bytes")
            _valida_razao(total, info.compress_size, razao_max)
            if orcamento is not None:
                orcamento.consumir(len(bloco))
            partes.append(bloco)
    dados = b"".join(partes)
    if nivel_aninhamento >= ANINHAMENTO_PACOTE_MAX and eh_assinatura_pacote(dados[:8]):
        raise ErroDescompressao(
            f"membro {nome!r} é pacote comprimido aninhado além de {ANINHAMENTO_PACOTE_MAX} nível"
        )
    return dados


def ler_gzip_seguro(
    fh: Any,
    limite: int = MEMBRO_MAX,
    razao_max: float = RAZAO_COMPRESSAO_MAX,
    tamanho_comprimido: int | None = None,
    *,
    orcamento: OrcamentoDescompressao | None = None,
) -> bytes:
    """Descomprime gzip em fluxo até `limite` bytes e `razao_max` (DT 832/899)."""
    fh.seek(0)
    partes: list[bytes] = []
    total = 0
    with gzip.GzipFile(fileobj=fh, mode="rb") as gz:
        while True:
            bloco = gz.read(CHUNK_DESCOMPRESSAO)
            if not bloco:
                break
            total += len(bloco)
            if total > limite:
                raise ErroDescompressao(f"gzip atingiu teto de {limite} bytes descomprimidos")
            _valida_razao(total, tamanho_comprimido, razao_max)
            if orcamento is not None:
                orcamento.consumir(len(bloco))
            partes.append(bloco)
    return b"".join(partes)


def _ooxml_rels(
    zf: zipfile.ZipFile, nome: str, *, orcamento: OrcamentoDescompressao | None = None
) -> dict[str, str]:
    """Helper XML OOXML isolado: mapa Id -> Target de um arquivo `.rels` (DT 899)."""
    try:
        raiz = parse_xml_seguro(ler_zip_seguro(zf, nome, orcamento=orcamento))
    except (KeyError, ET.ParseError):
        return {}
    return {
        r.get("Id") or "": r.get("Target") or ""
        for r in raiz.iter(f"{_REL}Relationship")
        if r.get("TargetMode") != "External" and r.get("Id") and r.get("Target")
    }


def _ooxml_rels_tipo(
    zf: zipfile.ZipFile,
    nome: str,
    sufixo: str,
    *,
    orcamento: OrcamentoDescompressao | None = None,
) -> str | None:
    """Helper XML OOXML isolado: primeiro Target cujo Type termina em `sufixo`."""
    try:
        raiz = parse_xml_seguro(ler_zip_seguro(zf, nome, orcamento=orcamento))
    except (KeyError, ET.ParseError):
        return None
    for r in raiz.iter(f"{_REL}Relationship"):
        if (r.get("Type") or "").endswith(sufixo):
            return r.get("Target")
    return None


# ============================================================== tipo real (§7.2, §7.4.4)
def tipo_do_zip(fh: Any) -> str:
    """O que um ZIP é, pelo que há dentro, nunca pelo nome (F2 da lista antipadroes-de-transcricao)."""
    try:
        fh.seek(0)
        with zipfile.ZipFile(fh) as zf:
            nomes = set(zf.namelist())
            if "mimetype" in nomes:
                try:
                    if ler_zip_seguro(zf, "mimetype", limite=4096).strip() == b"application/epub+zip":
                        return EPUB
                except (zipfile.BadZipFile, KeyError, OSError, ErroDescompressao):
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
_MHTML_CABECA = re.compile(
    rb"^(from:|mime-version:|content-type:\s*multipart/related|"
    rb"subject:|snapshot-content-location:)",
    re.IGNORECASE | re.MULTILINE,
)


def tipo_texto(cabeca: bytes, tipo_nome: str) -> str:
    """HTML e MHTML pelos bytes: só reclassifica texto plano ou o que o nome já dizia."""
    if tipo_nome not in ("text/plain", HTML, "application/xml"):
        return tipo_nome
    inicio = cabeca[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    if _MHTML_CABECA.match(inicio) and (
        b"multipart/related" in cabeca.lower() or b"boundary=" in cabeca.lower()
    ):
        return MHTML
    baixo = inicio[:1024].lower()
    if (
        any(baixo.startswith(m) for m in _HTML_MARCAS[:4])
        or (tipo_nome == HTML)
        or (b"<html" in baixo and b">" in baixo)
    ):
        return HTML
    return tipo_nome


def e_webp(cabeca: bytes) -> bool:
    return cabeca[:4] == b"RIFF" and cabeca[8:12] == b"WEBP"


# ============================================================== tabela GFM
def tabela_gfm(linhas: list[list[str]]) -> str:
    """Tabela GFM: a primeira linha é cabeçalho, as células escapam `|` e perdem a quebra."""
    if not linhas:
        return ""
    largura = max(len(linha) for linha in linhas)

    def cel(c: str) -> str:
        return re.sub(r"\s+", " ", (c or "")).strip().replace("|", "\\|")

    saida = []
    for i, linha in enumerate(linhas):
        cells = [cel(c) for c in linha] + [""] * (largura - len(linha))
        saida.append("| " + " | ".join(cells) + " |")
        if i == 0:
            saida.append("|" + "|".join([" --- "] * largura) + "|")
    return "\n".join(saida)


def _limpa(texto: str) -> str:
    """Três ou mais linhas em branco viram duas; sem espaço pendurado; termina em `\\n`."""
    texto = "\n".join(linha.rstrip() for linha in texto.split("\n"))
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip("\n")
    return texto + "\n" if texto else ""


# ============================================================== o documento
@dataclass
class Documento:
    tipo: str
    unidade: str                                   # pagina · item · slide · planilha · nenhuma · imagem
    n: int                                         # unidades; 1 quando `nenhuma`
    nomes: list[str] = field(default_factory=list)
    membros: list[tuple[str, int]] = field(default_factory=list)
    render: bool = False
    imagem_propria: bytes | None = None
    dimensoes: tuple[int, int] | None = None
    avisos: list[str] = field(default_factory=list)
    sem_texto: list[int] = field(default_factory=list)
    truncado: bool = False
    _texto: dict = field(default_factory=dict, repr=False)
    _fonte: object = field(default=None, repr=False)

    def texto(self, i: int) -> str:
        """O texto da unidade `i` (base 1), em ordem de leitura do formato, terminado em `\\n`."""
        if i not in self._texto:
            self._texto[i] = _limpa(self._extrai(i))
        return self._texto[i]

    def _extrai(self, i: int) -> str:
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
    def __init__(self, fonte: Any, nome: str = ""):
        if pymupdf is None:
            raise RuntimeError("pymupdf ausente do venv harness: PDF sem leitor")
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
        flags = pymupdf.TEXT_PRESERVE_WHITESPACE
        if int(pagina.rotation) % 180 == 0:
            flags |= pymupdf.TEXT_MEDIABOX_CLIP
        texto = pagina.get_text("text", flags=flags)
        if not texto.strip():
            if i not in self.sem_texto:
                self.sem_texto.append(i)
            aviso = f"pagina_{i}_sem_texto"
            if aviso not in self.avisos:
                self.avisos.append(aviso)
        return texto

    def imagem(self, i: int, dpi: int = DPI_PADRAO) -> tuple[bytes | None, str, dict]:
        dpi = max(36, min(int(dpi or DPI_PADRAO), DPI_MAX))
        pagina = self._fonte[i - 1]
        pix = pagina.get_pixmap(dpi=dpi, alpha=False)
        return pix.tobytes("png"), PNG, {"dimensoes": (pix.width, pix.height), "dpi": dpi}

    def fecha(self) -> None:
        if self._fonte is not None:
            try:
                self._fonte.close()
            except RuntimeError:
                return


class _Mobi(Documento):
    """MOBI pelo MuPDF: o original não tem unidade fixa, então o texto sai inteiro."""

    def __init__(self, fonte: Any):
        if pymupdf is None:
            raise RuntimeError("pymupdf ausente do venv harness: MOBI sem leitor")
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
        if self._fonte is not None:
            try:
                self._fonte.close()
            except RuntimeError:
                return


# ---------------------------------------------------------------- HTML (texto visível)
_IGNORA = {
    "script", "style", "noscript", "template", "svg", "math", "iframe", "object",
    "embed", "canvas", "audio", "video", "map", "datalist",
}
_BLOCO = {
    "p", "div", "section", "article", "header", "footer", "nav", "aside", "main",
    "ul", "ol", "dl", "dt", "dd", "li", "blockquote", "pre", "hr", "table", "figure",
    "figcaption", "details", "summary", "address", "form", "fieldset", "legend",
    "h1", "h2", "h3", "h4", "h5", "h6", "tr", "caption", "thead", "tbody", "tfoot",
    "body", "html", "head", "title", "center", "menu", "option", "label",
}
_BLOCO_CURTO = {"li", "dt", "dd", "tr", "option", "label", "title"}
_VAZIAS = {
    "br", "img", "hr", "meta", "link", "input", "wbr", "source", "col", "area",
    "base", "embed", "param", "track",
}
_OCULTO = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)


class _TextoVisivel(HTMLParser):
    """Texto visível em ordem de documento: sem script/estilo, tabela GFM, `<img>` listada."""

    def __init__(self, base: str = ""):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.partes: list[str] = []
        self.oculto: list[str] = []
        self.pre = 0
        self.tabelas: list[dict] = []
        self.imagens: list[str] = []

    def _emite(self, s: str) -> None:
        if self.tabelas and self.tabelas[-1]["cel"] is not None:
            self.tabelas[-1]["cel"].append(s)
        else:
            self.partes.append(s)

    def _quebra(self, n: int = 1) -> None:
        self._emite("\n" * n)

    def _abre_img(self, attrs_map: dict[str, str | None]) -> None:
        src = (attrs_map.get("src") or attrs_map.get("data-src") or "").strip()
        alt = (attrs_map.get("alt") or "").strip()
        if src and not src.startswith("data:"):
            caminho = _resolve(self.base, src)
            self.imagens.append(caminho)
            self._emite(f"[imagem: {caminho}{' — ' + alt if alt else ''}]")
        elif alt:
            self._emite(f"[imagem: {alt}]")

    def _abre_tabela(self, tag: str, attrs_map: dict[str, str | None]) -> None:
        if tag == "table":
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
                t["span"] = max(1, int(attrs_map.get("colspan") or 1))
            except ValueError:
                t["span"] = 1

    def _abre_bloco(self, tag: str) -> None:
        self._quebra(2 if tag not in _BLOCO_CURTO else 1)
        if tag[0] == "h" and tag[1:].isdigit():
            self._emite("#" * int(tag[1]) + " ")
        elif tag == "li":
            self._emite("- ")
        elif tag == "pre":
            self.pre += 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        eh_oculto = (
            bool(self.oculto)
            or tag in _IGNORA
            or ("hidden" in a and a.get("hidden") != "false")
            or bool(_OCULTO.search(a.get("style") or ""))
        )
        if eh_oculto:
            if tag not in _VAZIAS:
                self.oculto.append(tag)
            return
        if tag == "br":
            self._quebra()
        elif tag == "img":
            self._abre_img(a)
        elif tag in ("table", "tr", "td", "th"):
            self._abre_tabela(tag, a)
        elif tag in _BLOCO:
            self._abre_bloco(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VAZIAS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.oculto:
            if tag in self.oculto:
                while self.oculto and self.oculto.pop() != tag:
                    pass
            return
        if tag in ("td", "th") and self.tabelas and self.tabelas[-1]["cel"] is not None:
            t = self.tabelas[-1]
            texto = "".join(t["cel"])
            t["linha"][-1] = texto
            for _ in range(t.get("span", 1) - 1):
                t["linha"].append(texto)
            t["cel"] = None
        elif tag == "table" and self.tabelas:
            t = self.tabelas.pop()
            linhas = [[c if isinstance(c, str) else "".join(c) for c in row] for row in t["linhas"]]
            linhas = [row for row in linhas if any(c.strip() for c in row)]
            self._emite(tabela_gfm(linhas))
            self._quebra(2)
        elif tag in _BLOCO:
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
            self._quebra(2 if tag not in _BLOCO_CURTO else 1)

    def handle_data(self, data: str) -> None:
        if self.oculto:
            return
        if not self.pre:
            data = re.sub(r"[ \t\r\n\f]+", " ", data)
            if not data.strip():
                return
            alvo = (
                self.tabelas[-1]["cel"]
                if self.tabelas and self.tabelas[-1]["cel"] is not None
                else self.partes
            )
            if not alvo or alvo[-1].endswith("\n"):
                data = data.lstrip(" ")
        self._emite(data)

    def texto(self) -> str:
        bruto = "".join(self.partes)
        return re.sub(r" +\n", "\n", bruto)


def _resolve(base: str, ref: str) -> str:
    ref = unquote(ref.split("#")[0].split("?")[0])
    if not base or ref.startswith(("/", "http:", "https:")):
        return ref.lstrip("/") if not ref.startswith("http") else ref
    try:
        from posixpath import join, normpath

        return normpath(join(base, ref))
    except Exception:                                     # noqa: BLE001
        return ref


def html_para_texto(
    dados: bytes | str, *, base: str = "", encoding: str | None = None
) -> tuple[str, list[str]]:
    """(texto visível, imagens por caminho) de um HTML ou XHTML."""
    if isinstance(dados, (bytes, bytearray)):
        s = decodifica(bytes(dados), encoding)
    else:
        s = dados
    p = _TextoVisivel(base)
    try:
        p.feed(s)
        p.close()
    except (ValueError, AssertionError):
        return p.texto(), p.imagens
    return p.texto(), p.imagens


def decodifica(dados: bytes, declarado: str | None = None) -> str:
    """Os bytes decidem antes da declaração: UTF-8 estrito; senão charset declarado; senão cp1252."""
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


_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?\s*([-\w.:]+)""", re.IGNORECASE)
_XML_ENC = re.compile(rb"""^\s*<\?xml[^>]*encoding=["']([-\w.:]+)["']""", re.IGNORECASE)


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
        for parte in partes:
            if parte.get_content_maintype() == "text":
                corpo = parte.get_payload(decode=True) or b""
                return decodifica(corpo, parte.get_content_charset())
        return ""


# ---------------------------------------------------------------- EPUB
class _Epub(Documento):
    """Itens do spine em ordem; cada um é uma unidade (`item`), lido como XHTML visível."""

    def __init__(self, fh: Any):
        self._zf = zipfile.ZipFile(fh)
        validar_pacote_zip(self._zf)
        self._orcamento = OrcamentoDescompressao()
        opf_caminho = self._acha_opf()
        base = str(PurePosixPath(opf_caminho).parent)
        base = "" if base == "." else base
        raiz = parse_xml_seguro(ler_zip_seguro(self._zf, opf_caminho, orcamento=self._orcamento))
        manifesto = {}
        for item in raiz.iter(f"{_OPF}item"):
            manifesto[item.get("id")] = (
                _resolve(base, item.get("href") or ""),
                item.get("media-type") or "",
            )
        spine = [ref.get("idref") for ref in raiz.iter(f"{_OPF}itemref")]
        self._itens = [manifesto[i][0] for i in spine if i in manifesto]
        if not self._itens:
            self._itens = [h for h, mt in manifesto.values() if "html" in mt or "xml" in mt]
        nomes = set(self._zf.namelist())
        self._itens = [h for h in self._itens if h in nomes]
        super().__init__(tipo=EPUB, unidade="item", n=len(self._itens), nomes=list(self._itens))
        self.membros = [
            (i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()
        ]

    def _acha_opf(self) -> str:
        try:
            cont = parse_xml_seguro(
                ler_zip_seguro(self._zf, "META-INF/container.xml", orcamento=self._orcamento)
            )
            for rf in cont.iter(f"{_CNT}rootfile"):
                if rf.get("full-path"):
                    return rf.get("full-path")
        except (KeyError, ET.ParseError):
            pass
        for nome in self._zf.namelist():
            if nome.lower().endswith(".opf"):
                return nome
        raise ValueError("EPUB sem OPF (nem container.xml nem arquivo .opf)")

    def _extrai(self, i: int) -> str:
        href = self._itens[i - 1]
        base = str(PurePosixPath(href).parent)
        texto, _ = html_para_texto(
            ler_zip_seguro(self._zf, href, orcamento=self._orcamento),
            base="" if base == "." else base,
        )
        return f"item: {href}\n\n{texto}"

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- DOCX
_TITULO_RE = re.compile(r"^(?:heading|t[ií]tulo|ttulo)\s*(\d)$", re.IGNORECASE)


class _Docx(Documento):
    """Parágrafos e tabelas na ordem do `word/document.xml`; notas e comentários ao fim."""

    def __init__(self, fh: Any):
        self._zf = zipfile.ZipFile(fh)
        validar_pacote_zip(self._zf)
        self._orcamento = OrcamentoDescompressao()
        super().__init__(tipo=DOCX, unidade="nenhuma", n=1)
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()]

    def _ler(self, nome: str) -> ET.Element | None:
        try:
            return parse_xml_seguro(ler_zip_seguro(self._zf, nome, orcamento=self._orcamento))
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
    def _texto_paragrafo(p: ET.Element) -> str:
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

    def _paragrafo(self, p: ET.Element, estilos: dict) -> str:
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

    def _tabela(self, tbl: ET.Element, estilos: dict) -> str:
        linhas: list[list[str]] = []
        for tr in tbl.findall(f"{_W}tr"):
            linha: list[str] = []
            for tc in tr.findall(f"{_W}tc"):
                texto = " ".join(
                    t for t in (self._paragrafo(p, estilos) for p in tc.findall(f"{_W}p")) if t
                )
                tcpr = tc.find(f"{_W}tcPr")
                span, vmerge = 1, None
                if tcpr is not None:
                    gs = tcpr.find(f"{_W}gridSpan")
                    if gs is not None and (gs.get(f"{_W}val") or "").isdigit():
                        span = int(gs.get(f"{_W}val"))
                    vm = tcpr.find(f"{_W}vMerge")
                    if vm is not None:
                        vmerge = vm.get(f"{_W}val") or "continue"
                if vmerge == "continue" and linhas:
                    col = len(linha)
                    texto = linhas[-1][col] if col < len(linhas[-1]) else texto
                linha.extend([texto] * span)
            linhas.append(linha)
        return tabela_gfm(linhas)

    def _blocos(self, pai: ET.Element, estilos: dict, saida: list[str]) -> None:
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
            corpo: list[str] = []
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
            corpo: list[str] = []
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
        notas = self._notas("word/footnotes.xml", "footnote", "", estilos) + self._notas(
            "word/endnotes.xml", "endnote", "e", estilos
        )
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
    """Um slide por unidade, na ordem do `presentation.xml`; texto das formas e notas."""

    def __init__(self, fh: Any):
        self._zf = zipfile.ZipFile(fh)
        validar_pacote_zip(self._zf)
        self._orcamento = OrcamentoDescompressao()
        rels = _ooxml_rels(self._zf, "ppt/_rels/presentation.xml.rels", orcamento=self._orcamento)
        raiz = parse_xml_seguro(
            ler_zip_seguro(self._zf, "ppt/presentation.xml", orcamento=self._orcamento)
        )
        slides = []
        for sid in raiz.iter(f"{_P}sldId"):
            alvo = rels.get(sid.get(f"{_R}id") or "")
            if alvo:
                slides.append(_resolve("ppt", alvo))
        super().__init__(tipo=PPTX, unidade="slide", n=len(slides), nomes=slides)
        self._slides = slides
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()]

    @staticmethod
    def _paragrafos(txbody: ET.Element) -> list[str]:
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
                lvl = (
                    int(ppr.get("lvl") or 0)
                    if ppr is not None and (ppr.get("lvl") or "0").isdigit()
                    else 0
                )
                saida.append(("  " * lvl + "- " + t) if lvl else t)
        return saida

    def _forma_sp(self, el: ET.Element, blocos: list[str]) -> None:
        ph = el.find(f"{_P}nvSpPr/{_P}nvPr/{_P}ph")
        tipo_ph = ph.get("type") if ph is not None else None
        tx = el.find(f"{_P}txBody")
        if tx is None:
            return
        pars = self._paragrafos(tx)
        if not pars:
            return
        if tipo_ph in ("title", "ctrTitle"):
            blocos.append("# " + " ".join(pars))
        elif tipo_ph == "subTitle":
            blocos.append("## " + " ".join(pars))
        elif tipo_ph in ("sldNum", "dt", "ftr"):
            blocos.append(f"<!-- {tipo_ph}: {' '.join(pars)} -->")
        else:
            blocos.append("\n".join(pars))

    def _forma_grafico(self, el: ET.Element, blocos: list[str]) -> None:
        tbl = next(el.iter(f"{_A}tbl"), None)
        if tbl is None:
            textos = [t.text or "" for t in el.iter(f"{_A}t")]
            if any(x.strip() for x in textos):
                blocos.append(" ".join(x for x in textos if x.strip()))
            return
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

    def _formas(self, pai: ET.Element, blocos: list[str], caminho_slide: str) -> None:
        for el in pai:
            tag = el.tag
            if tag == f"{_P}sp":
                self._forma_sp(el, blocos)
            elif tag == f"{_P}graphicFrame":
                self._forma_grafico(el, blocos)
            elif tag == f"{_P}grpSp":
                self._formas(el, blocos, caminho_slide)
            elif tag == f"{_P}pic":
                blip = next(el.iter(f"{_A}blip"), None)
                rid = blip.get(f"{_R}embed") if blip is not None else None
                alvo = _ooxml_rels(self._zf, _rels_de(caminho_slide)).get(rid or "")
                if alvo:
                    blocos.append(
                        f"[imagem: {_resolve(str(PurePosixPath(caminho_slide).parent), alvo)}]"
                    )

    def _extrai_notas(self, caminho: str) -> list[str]:
        notas_alvo = _ooxml_rels_tipo(self._zf, _rels_de(caminho), "/notesSlide")
        if not notas_alvo:
            return []
        nome = _resolve(str(PurePosixPath(caminho).parent), notas_alvo)
        try:
            nraiz = parse_xml_seguro(ler_zip_seguro(self._zf, nome, orcamento=self._orcamento))
        except (KeyError, ET.ParseError):
            return []
        narv = nraiz.find(f"{_P}cSld/{_P}spTree")
        if narv is None:
            return []
        notas: list[str] = []
        for sp in narv.iter(f"{_P}sp"):
            ph = sp.find(f"{_P}nvSpPr/{_P}nvPr/{_P}ph")
            if ph is not None and ph.get("type") in ("sldNum", "sldImg", "hdr", "ftr", "dt"):
                continue
            tx = sp.find(f"{_P}txBody")
            if tx is not None:
                notas.extend(self._paragrafos(tx))
        return notas

    def _extrai(self, i: int) -> str:
        caminho = self._slides[i - 1]
        raiz = parse_xml_seguro(ler_zip_seguro(self._zf, caminho, orcamento=self._orcamento))
        arvore = raiz.find(f"{_P}cSld/{_P}spTree")
        blocos: list[str] = []
        if arvore is not None:
            self._formas(arvore, blocos, caminho)
        notas = self._extrai_notas(caminho)
        if notas:
            blocos.append("<!-- notas do apresentador -->\n\n" + "\n\n".join(notas))
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
    """Uma planilha por unidade, na ordem do `workbook.xml`; tabela GFM com valores."""

    def __init__(self, fh: Any):
        self._zf = zipfile.ZipFile(fh)
        validar_pacote_zip(self._zf)
        self._orcamento = OrcamentoDescompressao()
        raiz = parse_xml_seguro(
            ler_zip_seguro(self._zf, "xl/workbook.xml", orcamento=self._orcamento)
        )
        rels = _ooxml_rels(self._zf, "xl/_rels/workbook.xml.rels", orcamento=self._orcamento)
        folhas = []
        for sh in raiz.iter(f"{_S}sheet"):
            alvo = rels.get(sh.get(f"{_R}id") or "")
            if alvo:
                destino = (
                    _resolve("xl", alvo.lstrip("/"))
                    if not alvo.startswith("/")
                    else alvo.lstrip("/")
                )
                folhas.append((sh.get("name") or "", destino))
        super().__init__(tipo=XLSX, unidade="planilha", n=len(folhas), nomes=[n for n, _ in folhas])
        self._folhas = folhas
        self._ss: list[str] | None = None
        self.membros = [(i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()]

    def _shared(self) -> list[str]:
        if self._ss is None:
            self._ss = []
            try:
                raiz = parse_xml_seguro(
                    ler_zip_seguro(self._zf, "xl/sharedStrings.xml", orcamento=self._orcamento)
                )
                for si in raiz.iter(f"{_S}si"):
                    self._ss.append("".join(t.text or "" for t in si.iter(f"{_S}t")))
            except (KeyError, ET.ParseError):
                pass
        return self._ss

    def _valor(self, c: ET.Element) -> str:
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
                return repr(f) if abs(f) < _FLOAT_REPR_MAX else val
            except ValueError:
                return val
        return val

    def _coleta_celulas(self, raiz: ET.Element) -> dict[tuple[int, int], str]:
        celulas: dict[tuple[int, int], str] = {}
        for row in raiz.iter(f"{_S}row"):
            try:
                rn = int(row.get("r") or 0)
            except ValueError:
                rn = 0
            for col_auto, c in enumerate(row.findall(f"{_S}c"), 1):
                if len(celulas) >= CELULAS_XLSX_MAX:
                    self.truncado = True
                    if "planilha_truncada" not in self.avisos:
                        self.avisos.append("planilha_truncada")
                    return celulas
                ref = c.get("r") or ""
                cn = _col_idx(ref) or col_auto
                if not rn:
                    rn = int(re.sub(r"\D", "", ref) or 0)
                val = self._valor(c)
                if val != "":
                    celulas[(rn, cn)] = val
        return celulas

    def _aplica_mesclas(self, raiz: ET.Element, celulas: dict[tuple[int, int], str]) -> None:
        for mc in raiz.iter(f"{_S}mergeCell"):
            ref = mc.get("ref") or ""
            if ":" not in ref:
                continue
            a, b = ref.split(":", 1)
            r1_s, r2_s = re.sub(r"\D", "", a), re.sub(r"\D", "", b)
            if not r1_s or not r2_s:
                continue
            r1, c1 = int(r1_s), _col_idx(a)
            r2, c2 = int(r2_s), _col_idx(b)
            val = celulas.get((r1, c1), "")
            if val == "" or (r2 - r1 + 1) * (c2 - c1 + 1) > CELULAS_XLSX_MAX:
                continue
            for r in range(r1, r2 + 1):
                for cc in range(c1, c2 + 1):
                    if len(celulas) >= CELULAS_XLSX_MAX:
                        self.truncado = True
                        if "planilha_truncada" not in self.avisos:
                            self.avisos.append("planilha_truncada")
                        return
                    celulas.setdefault((r, cc), val)

    def _extrai(self, i: int) -> str:
        nome, caminho = self._folhas[i - 1]
        try:
            raiz = parse_xml_seguro(
                ler_zip_seguro(self._zf, caminho, orcamento=self._orcamento)
            )
        except KeyError:
            return f"planilha: {nome}\n\n(planilha sem dados)"
        celulas = self._coleta_celulas(raiz)
        self._aplica_mesclas(raiz, celulas)
        if not celulas:
            return f"planilha: {nome}\n\n(planilha vazia)"
        linhas_idx = sorted({r for r, _ in celulas})
        cols_idx = sorted({c for _, c in celulas})
        grade = [[celulas.get((r, c), "") for c in cols_idx] for r in linhas_idx]
        return f"planilha: {nome}\n\n" + tabela_gfm(grade)

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- ZIP de outro tipo
class _Zip(Documento):
    """Listagem como diretório (§9.2); o membro se lê por `caminho!membro`."""

    def __init__(self, fh: Any):
        self._zf = zipfile.ZipFile(fh)
        validar_pacote_zip(self._zf)
        self._orcamento = OrcamentoDescompressao()
        super().__init__(tipo=ZIP, unidade="nenhuma", n=1)
        self.membros = sorted(
            (i.filename, i.file_size) for i in self._zf.infolist() if not i.is_dir()
        )

    def listar_membros_detalhados(self) -> list[tuple[str, int, int, float]]:
        """Retorna (nome, tamanho_bruto, tamanho_comprimido, razao) ordenado."""
        saida: list[tuple[str, int, int, float]] = []
        for info in sorted(self._zf.infolist(), key=lambda x: x.filename):
            if info.is_dir():
                continue
            comp = info.compress_size
            razao = (info.file_size / comp) if comp > 0 else 1.0
            saida.append((info.filename, info.file_size, comp, razao))
        return saida

    def _extrai(self, i: int) -> str:
        return "".join(f"{n}  {t}\n" for n, t in self.membros)

    def fecha(self) -> None:
        self._zf.close()


# ---------------------------------------------------------------- imagem
_JPEG_SOF = frozenset({0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF})


def _dimensoes_webp(cabeca: bytes) -> tuple[int, int] | None:
    if len(cabeca) < _WEBP_CABECA_MIN:
        return None
    subtipo = cabeca[12:16]
    if subtipo == b"VP8 ":
        w, h = struct.unpack("<HH", cabeca[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if subtipo == b"VP8L":
        b = cabeca[21:25]
        return (
            (b[0] | ((b[1] & 0x3F) << 8)) + 1,
            ((b[1] >> 6) | (b[2] << 2) | ((b[3] & 0x0F) << 10)) + 1,
        )
    if subtipo == b"VP8X":
        return (
            1 + int.from_bytes(cabeca[24:27], "little"),
            1 + int.from_bytes(cabeca[27:30], "little"),
        )
    return None


def _dimensoes_jpeg(cabeca: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 < len(cabeca):
        if cabeca[i] != _JPEG_MARCADOR:
            i += 1
            continue
        marca = cabeca[i + 1]
        if marca in _JPEG_SOF:
            h, w = struct.unpack(">HH", cabeca[i + 5 : i + 9])
            return w, h
        if marca in (0xD8, 0x01) or _JPEG_RST_INI <= marca <= _JPEG_RST_FIM:
            i += 2
            continue
        tam = struct.unpack(">H", cabeca[i + 2 : i + 4])[0]
        i += 2 + tam
    return None


def dimensoes_imagem(cabeca: bytes, tipo: str) -> tuple[int, int] | None:
    try:
        if tipo == PNG and len(cabeca) >= _PNG_CABECA_MIN:
            return struct.unpack(">II", cabeca[16:24])
        if tipo == GIF and len(cabeca) >= _GIF_CABECA_MIN:
            return struct.unpack("<HH", cabeca[6:10])
        if tipo == WEBP:
            return _dimensoes_webp(cabeca)
        if tipo == JPEG:
            return _dimensoes_jpeg(cabeca)
    except (struct.error, IndexError):
        return None
    return None


class _Imagem(Documento):
    def __init__(self, dados: bytes, tipo: str):
        super().__init__(
            tipo=tipo,
            unidade="imagem",
            n=1,
            render=True,
            imagem_propria=dados,
            dimensoes=dimensoes_imagem(dados[:64], tipo),
        )

    def _extrai(self, i: int) -> str:
        return ""


_ZIP_CLASSES = {EPUB: _Epub, DOCX: _Docx, PPTX: _Pptx, XLSX: _Xlsx, ZIP: _Zip}


# ============================================================== abertura
def abre(
    tipo: str,
    *,
    fh: Any = None,
    caminho: Any = None,
    dados: bytes | None = None,
    encoding: str | None = None,
) -> Documento:
    """O Documento do tipo."""
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
    if tipo in _ZIP_CLASSES:
        return _ZIP_CLASSES[tipo](fonte)
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


def eh_formato_isolado(tipo: str) -> bool:
    """Indica se o formato deve rodar na instância isolada do extrator."""
    return tipo in FORMATOS_ISOLADOS


def delegar_extrator(
    fd: int,
    pedido: dict[str, Any],
    *,
    socket_path: str | None = None,
    prazo_ms: int = 10_000,
) -> dict[str, Any]:
    """Delega a extração binária ao módulo isolado `lib/leitura/extrator.py`."""
    from . import extrator

    if socket_path:
        return extrator.extrair_via_socket(socket_path, fd, pedido, prazo_ms=prazo_ms)
    return extrator.extrair_em_subprocesso(fd, pedido, prazo_ms=prazo_ms)


def membro_de(doc: Documento, nome: str, *, nivel_aninhamento: int = 0) -> bytes:
    """Os bytes de um membro de ZIP, EPUB ou OOXML, para ler por `caminho!membro`."""
    zf = getattr(doc, "_zf", None)
    if zf is None:
        raise KeyError(nome)
    orcamento = getattr(doc, "_orcamento", None)
    return ler_zip_seguro(
        zf,
        nome,
        MEMBRO_MAX,
        orcamento=orcamento,
        nivel_aninhamento=nivel_aninhamento,
    )
