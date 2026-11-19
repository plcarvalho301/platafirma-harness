"""Leitores de formatos binários e estruturados para `ler_arquivo` no harness (story #4342, DT 900)."""
from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

PDF = "application/pdf"
EPUB = "application/epub+zip"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
ZIP = "application/zip"
HTML = "text/html"
MHTML = "message/rfc822"
MOBI = "application/x-mobipocket-ebook"
PNG = "image/png"
JPEG = "image/jpeg"
GIF = "image/gif"
WEBP = "image/webp"

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
MEMBRO_MAX = 64 * 1024 * 1024
CHUNK_DESCOMPRESSAO = 64 * 1024
RAZAO_COMPRESSAO_MAX = 100.0
RAZAO_MIN_BYTES = 64 * 1024
CELULAS_XLSX_MAX = 200_000

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_OPF = "{http://www.idpf.org/2007/opf}"
_CNT = "{urn:oasis:names:tc:opendocument:xmlns:container}"

_HTML_MARCAS = (b"<!doctype html", b"<html", b"<head", b"<body", b"<?xml", b"<meta", b"<title")
_MHTML_CABECA = re.compile(
    rb"^(from:|mime-version:|content-type:\s*multipart/related|subject:|snapshot-content-location:)",
    re.IGNORECASE | re.MULTILINE,
)


class ErroDescompressao(ValueError):
    """Membro comprimido excede teto de bytes ou razão máxima de compressão."""


def ler_zip_seguro(
    zf: zipfile.ZipFile,
    nome: str,
    limite: int = MEMBRO_MAX,
    razao_max: float = RAZAO_COMPRESSAO_MAX,
) -> bytes:
    """Descomprime membro de ZIP em fluxo com teto de bytes e razão de compressão."""
    info = zf.getinfo(nome)
    if info.file_size > limite:
        raise ErroDescompressao(f"membro {nome!r} declara {info.file_size} bytes (teto {limite})")
    if (
        info.compress_size > 0
        and info.file_size > RAZAO_MIN_BYTES
        and (info.file_size / info.compress_size) > razao_max
    ):
        raise ErroDescompressao(f"razão de compressão acima de {int(razao_max)}x em {nome!r}")
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
            if (
                info.compress_size > 0
                and total > RAZAO_MIN_BYTES
                and (total / info.compress_size) > razao_max
            ):
                raise ErroDescompressao(f"razão de compressão acima de {int(razao_max)}x em {nome!r}")
            partes.append(bloco)
    return b"".join(partes)


def _ooxml_rels(zf: zipfile.ZipFile, nome: str) -> dict[str, str]:
    try:
        raiz = ET.fromstring(ler_zip_seguro(zf, nome))
    except (KeyError, ET.ParseError):
        return {}
    return {
        r.get("Id") or "": r.get("Target") or ""
        for r in raiz.iter(f"{_REL}Relationship")
        if r.get("TargetMode") != "External" and r.get("Id") and r.get("Target")
    }


def _resolve_posix(base: str, ref: str) -> str:
    ref = unquote(ref.split("#")[0].split("?")[0])
    if not base or ref.startswith(("/", "http:", "https:")):
        return ref.lstrip("/")
    partes: list[str] = []
    for seg in PurePosixPath(base, ref).parts:
        if seg == "..":
            if partes:
                partes.pop()
        elif seg not in (".", ""):
            partes.append(seg)
    return "/".join(partes)


class _HtmlSimples(HTMLParser):
    _IGNORA = frozenset({"script", "style", "noscript", "template"})
    _BLOCO = frozenset({"p", "div", "section", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br"})

    def __init__(self) -> None:
        super().__init__()
        self.partes: list[str] = []
        self._ignora_prof = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._IGNORA:
            self._ignora_prof += 1
        elif not self._ignora_prof and tag in self._BLOCO:
            self.partes.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORA and self._ignora_prof > 0:
            self._ignora_prof -= 1
        elif not self._ignora_prof and tag in self._BLOCO:
            self.partes.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignora_prof:
            self.partes.append(data)

    def texto(self) -> str:
        bruto = "".join(self.partes)
        linhas = [re.sub(r"[ \t]+", " ", ln).strip() for ln in bruto.splitlines()]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(ln for ln in linhas if ln)).strip()


def _tabela_gfm(linhas: list[list[str]]) -> str:
    if not linhas:
        return ""
    largura = max(len(ln) for ln in linhas)

    def cel(c: str) -> str:
        return re.sub(r"\s+", " ", c or "").strip().replace("|", "\\|")

    saida = []
    for i, ln in enumerate(linhas):
        cells = [cel(c) for c in ln] + [""] * (largura - len(ln))
        saida.append("| " + " | ".join(cells) + " |")
        if i == 0:
            saida.append("|" + "|".join([" --- "] * largura) + "|")
    return "\n".join(saida)


def tipo_do_zip(fh: Any) -> str:
    """Identifica o tipo real de um ZIP pelo conteúdo interno, nunca pela extensão."""
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


def tipo_texto(cabeca: bytes, tipo_nome: str) -> str:
    if tipo_nome not in ("text/plain", HTML, "application/xml"):
        return tipo_nome
    inicio = cabeca[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    if _MHTML_CABECA.match(inicio) and (
        b"multipart/related" in cabeca.lower() or b"boundary=" in cabeca.lower()
    ):
        return MHTML
    baixo = inicio[:1024].lower()
    if any(baixo.startswith(m) for m in _HTML_MARCAS[:4]) or tipo_nome == HTML or (
        b"<html" in baixo and b">" in baixo
    ):
        return HTML
    return tipo_nome


def _parse_faixa(spec: str | None, total: int) -> tuple[int, int]:
    if total <= 0:
        return 0, 0
    if not spec:
        return 1, min(total, 10)
    s = spec.strip()
    if "-" in s:
        a, _, b = s.partition("-")
        ini = int(a) if a.strip() else 1
        fim = int(b) if b.strip() else total
    else:
        ini = fim = int(s)
    ini = max(1, min(ini, total))
    fim = max(ini, min(fim, total))
    return ini, fim


def _ler_pdf(caminho: Path, *, paginas: str | None = None, modo: str = "texto", dpi: int = DPI_PADRAO) -> dict[str, Any]:
    import pymupdf as fitz  # PyMuPDF (declarado no venv do harness)

    with fitz.open(caminho) as doc:
        total = len(doc)
        if total == 0:
            return {"conteudo": "", "paginas": [0, 0], "paginas_total": 0}
        ini, fim = _parse_faixa(paginas, total)
        if modo == "pagina":
            escala = max(72, min(int(dpi or DPI_PADRAO), DPI_MAX)) / 72.0
            imagens = []
            for pno in range(ini, fim + 1):
                pix = doc[pno - 1].get_pixmap(matrix=fitz.Matrix(escala, escala))
                imagens.append(
                    {
                        "pagina": pno,
                        "mime": PNG,
                        "base64": base64.b64encode(pix.tobytes("png")).decode("ascii"),
                    }
                )
            return {"imagens": imagens, "paginas": [ini, fim], "paginas_total": total}
        blocos = []
        for pno in range(ini, fim + 1):
            blocos.append(f"<!-- p. {pno} -->\n{doc[pno - 1].get_text('text')}")
        return {
            "conteudo": "\n".join(blocos),
            "paginas": [ini, fim],
            "paginas_total": total,
        }


def _ler_docx(caminho: Path) -> dict[str, Any]:
    with zipfile.ZipFile(caminho) as zf:
        xml_bytes = ler_zip_seguro(zf, "word/document.xml")
    raiz = ET.fromstring(xml_bytes)
    paragrafos = []
    for p in raiz.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        partes = [
            t.text or ""
            for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        ]
        linha = "".join(partes).strip()
        if linha:
            paragrafos.append(linha)
    return {"conteudo": "\n".join(paragrafos)}


def _ler_epub(caminho: Path, *, paginas: str | None = None) -> dict[str, Any]:
    with zipfile.ZipFile(caminho) as zf:
        opf = None
        try:
            cont = ET.fromstring(ler_zip_seguro(zf, "META-INF/container.xml"))
            for rf in cont.iter(f"{_CNT}rootfile"):
                if rf.get("full-path"):
                    opf = rf.get("full-path")
                    break
        except (KeyError, ET.ParseError):
            pass
        if not opf:
            opf = next((n for n in zf.namelist() if n.lower().endswith(".opf")), None)
        if not opf:
            return {"erro": "EPUB sem OPF"}
        base = str(PurePosixPath(opf).parent)
        base = "" if base == "." else base
        raiz = ET.fromstring(ler_zip_seguro(zf, opf))
        manifesto = {
            item.get("id"): (_resolve_posix(base, item.get("href") or ""), item.get("media-type") or "")
            for item in raiz.iter(f"{_OPF}item")
        }
        spine = [ref.get("idref") for ref in raiz.iter(f"{_OPF}itemref")]
        itens = [manifesto[i][0] for i in spine if i in manifesto]
        if not itens:
            itens = [h for h, mt in manifesto.values() if "html" in mt or "xml" in mt]
        nomes = set(zf.namelist())
        itens = [h for h in itens if h in nomes]
        total = len(itens)
        if total == 0:
            return {"conteudo": "", "paginas": [0, 0], "paginas_total": 0, "unidade": "item"}
        ini, fim = _parse_faixa(paginas, total)
        blocos = []
        for idx in range(ini, fim + 1):
            href = itens[idx - 1]
            parser = _HtmlSimples()
            parser.feed(ler_zip_seguro(zf, href).decode("utf-8", errors="replace"))
            blocos.append(f"<!-- p. {idx} -->\nitem: {href}\n\n{parser.texto()}")
        return {
            "conteudo": "\n\n".join(blocos),
            "paginas": [ini, fim],
            "paginas_total": total,
            "unidade": "item",
        }


def _col_idx(ref: str) -> int:
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n


def _ler_xlsx(caminho: Path, *, paginas: str | None = None) -> dict[str, Any]:
    with zipfile.ZipFile(caminho) as zf:
        wb = ET.fromstring(ler_zip_seguro(zf, "xl/workbook.xml"))
        rels = _ooxml_rels(zf, "xl/_rels/workbook.xml.rels")
        folhas = []
        for sh in wb.iter(f"{_S}sheet"):
            alvo = rels.get(sh.get(f"{_R}id") or "")
            if alvo:
                dest = _resolve_posix("xl", alvo) if not alvo.startswith("/") else alvo.lstrip("/")
                folhas.append((sh.get("name") or "", dest))
        shared: list[str] = []
        try:
            ss = ET.fromstring(ler_zip_seguro(zf, "xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{_S}t")) for si in ss.iter(f"{_S}si")]
        except (KeyError, ET.ParseError):
            pass
        total = len(folhas)
        if total == 0:
            return {"conteudo": "", "paginas": [0, 0], "paginas_total": 0, "unidade": "planilha"}
        ini, fim = _parse_faixa(paginas, total)
        blocos = []
        for idx in range(ini, fim + 1):
            nome, arq = folhas[idx - 1]
            try:
                raiz = ET.fromstring(ler_zip_seguro(zf, arq))
            except (KeyError, ET.ParseError):
                blocos.append(f"<!-- p. {idx} -->\nplanilha: {nome}\n\n(planilha sem dados)")
                continue
            celulas: dict[tuple[int, int], str] = {}
            for row in raiz.iter(f"{_S}row"):
                rn = int(row.get("r") or 0) if (row.get("r") or "").isdigit() else 0
                for col_auto, c in enumerate(row.findall(f"{_S}c"), 1):
                    if len(celulas) >= CELULAS_XLSX_MAX:
                        break
                    ref = c.get("r") or ""
                    cn = _col_idx(ref) or col_auto
                    if not rn:
                        rn = int(re.sub(r"\D", "", ref) or 0)
                    t = c.get("t") or "n"
                    if t == "inlineStr":
                        is_ = c.find(f"{_S}is")
                        val = "".join(x.text or "" for x in is_.iter(f"{_S}t")) if is_ is not None else ""
                    else:
                        v = c.find(f"{_S}v")
                        val = (v.text or "") if v is not None else ""
                        if t == "s" and val.isdigit() and int(val) < len(shared):
                            val = shared[int(val)]
                        elif t == "b":
                            val = "VERDADEIRO" if val == "1" else "FALSO"
                    if val != "":
                        celulas[(rn, cn)] = val
            if not celulas:
                blocos.append(f"<!-- p. {idx} -->\nplanilha: {nome}\n\n(planilha vazia)")
                continue
            linhas_idx = sorted({r for r, _ in celulas})
            cols_idx = sorted({c for _, c in celulas})
            grade = [[celulas.get((r, c), "") for c in cols_idx] for r in linhas_idx]
            blocos.append(f"<!-- p. {idx} -->\nplanilha: {nome}\n\n{_tabela_gfm(grade)}")
        return {
            "conteudo": "\n\n".join(blocos),
            "paginas": [ini, fim],
            "paginas_total": total,
            "unidade": "planilha",
        }


def _ler_pptx(caminho: Path, *, paginas: str | None = None) -> dict[str, Any]:
    with zipfile.ZipFile(caminho) as zf:
        rels = _ooxml_rels(zf, "ppt/_rels/presentation.xml.rels")
        raiz = ET.fromstring(ler_zip_seguro(zf, "ppt/presentation.xml"))
        slides = []
        for sid in raiz.iter(f"{_P}sldId"):
            alvo = rels.get(sid.get(f"{_R}id") or "")
            if alvo:
                slides.append(_resolve_posix("ppt", alvo))
        total = len(slides)
        if total == 0:
            return {"conteudo": "", "paginas": [0, 0], "paginas_total": 0, "unidade": "slide"}
        ini, fim = _parse_faixa(paginas, total)
        blocos = []
        for idx in range(ini, fim + 1):
            sraiz = ET.fromstring(ler_zip_seguro(zf, slides[idx - 1]))
            pars = []
            for p in sraiz.iter(f"{_A}p"):
                txt = "".join(t.text or "" for t in p.iter(f"{_A}t")).strip()
                if txt:
                    pars.append(txt)
            blocos.append(f"<!-- p. {idx} -->\n" + "\n".join(pars))
        return {
            "conteudo": "\n\n".join(blocos),
            "paginas": [ini, fim],
            "paginas_total": total,
            "unidade": "slide",
        }


def _ler_zip(caminho: Path) -> dict[str, Any]:
    with zipfile.ZipFile(caminho) as zf:
        nomes = sorted(zf.namelist())
    return {"conteudo": "\n".join(nomes), "membros_total": len(nomes)}


def extrair_texto_formato(
    caminho: Path,
    tipo: str,
    *,
    paginas: str | None = None,
    modo: str = "texto",
    dpi: int = DPI_PADRAO,
) -> dict[str, Any]:
    if tipo == PDF:
        return _ler_pdf(caminho, paginas=paginas, modo=modo, dpi=dpi)
    if tipo == DOCX:
        return _ler_docx(caminho)
    if tipo == EPUB:
        return _ler_epub(caminho, paginas=paginas)
    if tipo == XLSX:
        return _ler_xlsx(caminho, paginas=paginas)
    if tipo == PPTX:
        return _ler_pptx(caminho, paginas=paginas)
    if tipo == ZIP:
        return _ler_zip(caminho)
    if tipo in (PNG, JPEG, GIF, WEBP):
        dados = caminho.read_bytes()
        return {
            "mime": tipo,
            "bytes_total": len(dados),
            "base64": base64.b64encode(dados).decode("ascii"),
        }
    return {"erro": f"formato sem leitor: {tipo}"}
