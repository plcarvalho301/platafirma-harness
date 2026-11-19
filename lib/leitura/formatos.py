"""Leitores de formatos binários e estruturados para `ler_arquivo` no harness (story #4342)."""
from __future__ import annotations

import base64
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

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

_HTML_MARCAS = (b"<!doctype html", b"<html", b"<head", b"<body", b"<?xml", b"<meta", b"<title")
_MHTML_CABECA = re.compile(
    rb"^(from:|mime-version:|content-type:\s*multipart/related|subject:|snapshot-content-location:)",
    re.I | re.M,
)


def tipo_do_zip(fh: Any) -> str:
    """Identifica o tipo real de um ZIP pelo conteúdo interno, nunca pela extensão."""
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
        xml_bytes = zf.read("word/document.xml")
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
    if tipo in (ZIP, EPUB, XLSX, PPTX):
        return _ler_zip(caminho)
    if tipo in (PNG, JPEG, GIF, WEBP):
        dados = caminho.read_bytes()
        return {
            "mime": tipo,
            "bytes_total": len(dados),
            "base64": base64.b64encode(dados).decode("ascii"),
        }
    return {"erro": f"formato sem leitor: {tipo}"}
