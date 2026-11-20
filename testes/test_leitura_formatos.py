"""C18 — os formatos do acervo lidos pela porta (spec ler-arquivo §7.4, DT 919).

Migrado de `ops-server/test_formatos.py`: uma fixture por linha da tabela da §7.4, gerada em
código (PDF com camada de texto e página sem camada, EPUB, DOCX, PPTX, XLSX, HTML, MHTML, PNG,
ZIP de outro tipo + `caminho!membro`, GZIP, e binário fora da tabela ELF para `sem_leitor`).
"""
from __future__ import annotations

import base64
import gzip
import json
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ / "lib"))

from leitura import formatos as F  # noqa: E402
from leitura import leitura as L  # noqa: E402

BIN_LER = _RAIZ / "bin" / "ler_arquivo"
_PY_HARNESS = Path("/opt/platafirma/current/venv/harness/bin/python")


def _chamar(payload: dict) -> tuple[int, dict]:
    py = str(_PY_HARNESS) if _PY_HARNESS.is_file() else sys.executable
    cp = subprocess.run(
        [py, str(BIN_LER)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    assert cp.stdout.strip(), f"rc={cp.returncode} stderr={cp.stderr}"
    return cp.returncode, json.loads(cp.stdout)


def pdf(destino: Path) -> Path:
    """PDF de 4 páginas em Python puro: 3 com camada de texto e 1 só com retângulo (sem camada)."""
    streams = [
        f"BT /F1 12 Tf 72 720 Td (Pagina {i} do PDF de prova.) Tj 0 -28 Td (Segunda linha, com ponto final.) Tj ET".encode(
            "latin-1"
        )
        for i in range(1, 4)
    ] + [b"0.8 0.1 0.1 rg 50 50 400 200 re f"]

    # Obj 1: Catalog, Obj 2: Pages, Obj 3: Font, Objs 4..7: Pages, Objs 8..11: Contents
    objs: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [4 0 R 5 0 R 6 0 R 7 0 R] /Count 4 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    for idx in range(4):
        page_id = 4 + idx
        cont_id = 8 + idx
        objs.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {cont_id} 0 R >>\nendobj\n".encode()
        )
    for idx, st in enumerate(streams):
        cont_id = 8 + idx
        objs.append(
            f"{cont_id} 0 obj\n<< /Length {len(st)} >>\nstream\n".encode()
            + st
            + b"\nendstream\nendobj\n"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    p = destino / "prova.pdf"
    p.write_bytes(bytes(out))
    return p


def png(destino: Path) -> Path:
    def chunk(tipo, dados):
        c = tipo + dados
        return struct.pack(">I", len(dados)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    w, h = 4, 3
    raw = b"".join(b"\x00" + bytes([255, 0, 0] * w) for _ in range(h))
    dados = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    p = destino / "figura.png"
    p.write_bytes(dados)
    return p


def _zip(
    destino: Path,
    nome: str,
    membros: list[tuple[str, bytes]],
    mimetype: bytes | None = None,
) -> Path:
    p = destino / nome
    with zipfile.ZipFile(p, "w") as zf:
        if mimetype is not None:
            zf.writestr(zipfile.ZipInfo("mimetype"), mimetype, compress_type=zipfile.ZIP_STORED)
        for n, d in membros:
            zf.writestr(n, d, compress_type=zipfile.ZIP_DEFLATED)
    return p


def epub(destino: Path) -> Path:
    cont = (
        b'<?xml version="1.0"?><container version="1.0" '
        b'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
        b'<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        b"</rootfiles></container>"
    )
    opf = (
        b'<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        b'unique-identifier="id"><metadata/><manifest>\n'
        b'<item id="c2" href="cap%202.xhtml" media-type="application/xhtml+xml"/>\n'
        b'<item id="c1" href="cap1.xhtml" media-type="application/xhtml+xml"/>\n'
        b'<item id="img" href="img/fig.png" media-type="image/png"/>\n'
        b'</manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>'
    )
    c1 = (
        b'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml">'
        b"<head><title>Um</title><style>p{color:red}</style></head>"
        b'<body><h1>Capitulo Um</h1><p>Primeiro par&aacute;grafo do livro.</p>'
        b'<p><img src="img/fig.png" alt="figura um"/></p><script>alert(1)</script></body></html>'
    )
    c2 = (
        b'<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Capitulo Dois</h1>'
        b"<p>Segundo capitulo.</p><table><tr><th>a</th><th>b</th></tr>"
        b"<tr><td>1</td><td>2</td></tr></table></body></html>"
    )
    return _zip(
        destino,
        "livro.epub",
        [
            ("META-INF/container.xml", cont),
            ("OEBPS/content.opf", opf),
            ("OEBPS/cap1.xhtml", c1),
            ("OEBPS/cap 2.xhtml", c2),
            ("OEBPS/img/fig.png", png(destino).read_bytes()),
        ],
        mimetype=b"application/epub+zip",
    )


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx(destino: Path) -> Path:
    doc = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{_W}"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Titulo do documento</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Primeiro paragrafo</w:t></w:r><w:r><w:footnoteReference w:id="1"/></w:r><w:r><w:t>, com nota.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>item de lista</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>col a</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>col b</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>mesclada</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:r><w:t>Ultimo paragrafo</w:t></w:r><w:r><w:commentReference w:id="0"/></w:r></w:p>
<w:sectPr/></w:body></w:document>"""
    styles = f'<?xml version="1.0"?><w:styles xmlns:w="{_W}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>'
    notas = f'<?xml version="1.0"?><w:footnotes xmlns:w="{_W}"><w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote><w:footnote w:id="1"><w:p><w:r><w:t>Texto da nota de rodape.</w:t></w:r></w:p></w:footnote></w:footnotes>'
    coment = f'<?xml version="1.0"?><w:comments xmlns:w="{_W}"><w:comment w:id="0" w:author="Olga"><w:p><w:r><w:t>Revisar isto.</w:t></w:r></w:p></w:comment></w:comments>'
    ct = b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    return _zip(
        destino,
        "doc.docx",
        [
            ("[Content_Types].xml", ct),
            ("word/document.xml", doc.encode()),
            ("word/styles.xml", styles.encode()),
            ("word/footnotes.xml", notas.encode()),
            ("word/comments.xml", coment.encode()),
        ],
    )


_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def pptx(destino: Path) -> Path:
    pres = f'<?xml version="1.0"?><p:presentation xmlns:p="{_P}" xmlns:r="{_R}"><p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId1"/></p:sldIdLst></p:presentation>'
    prels = f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/></Relationships>'

    def slide(titulo, corpo):
        return f"""<?xml version="1.0"?><p:sld xmlns:p="{_P}" xmlns:a="{_A}" xmlns:r="{_R}"><p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:cNvPr id="2" name="T"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{titulo}</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr id="3" name="C"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:txBody><a:p><a:r><a:t>{corpo}</a:t></a:r></a:p><a:p><a:pPr lvl="1"/><a:r><a:t>subitem</a:t></a:r></a:p></p:txBody></p:sp>
<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>h1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>h2</a:t></a:r></a:p></a:txBody></a:tc></a:tr><a:tr><a:tc><a:txBody><a:p><a:r><a:t>v1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>v2</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>
</p:spTree></p:cSld></p:sld>"""

    s1rels = f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/></Relationships>'
    notas = f'<?xml version="1.0"?><p:notes xmlns:p="{_P}" xmlns:a="{_A}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="N"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Nota do apresentador do slide um.</a:t></a:r></a:p></p:txBody></p:sp><p:sp><p:nvSpPr><p:cNvPr id="3" name="num"/><p:cNvSpPr/><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>1</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:notes>'
    return _zip(
        destino,
        "apres.pptx",
        [
            ("ppt/presentation.xml", pres.encode()),
            ("ppt/_rels/presentation.xml.rels", prels.encode()),
            ("ppt/slides/slide1.xml", slide("Slide arquivo um", "Corpo um").encode()),
            ("ppt/slides/slide2.xml", slide("Slide arquivo dois", "Corpo dois").encode()),
            ("ppt/slides/_rels/slide1.xml.rels", s1rels.encode()),
            ("ppt/notesSlides/notesSlide1.xml", notas.encode()),
        ],
    )


_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def xlsx(destino: Path) -> Path:
    wb = f'<?xml version="1.0"?><workbook xmlns="{_S}" xmlns:r="{_R}"><sheets><sheet name="Vendas" sheetId="1" r:id="rId1"/><sheet name="Resumo" sheetId="2" r:id="rId2"/></sheets></workbook>'
    wrels = f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" Type="x/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="x/worksheet" Target="worksheets/sheet2.xml"/></Relationships>'
    ss = f'<?xml version="1.0"?><sst xmlns="{_S}" count="3" uniqueCount="3"><si><t>produto</t></si><si><t>total</t></si><si><r><t>ca</t></r><r><t>fe</t></r></si></sst>'
    s1 = f"""<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData>
<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><f>SUM(1,2)</f><v>3</v></c></row>
<row r="3"><c r="A3" t="inlineStr"><is><t>cha</t></is></c><c r="B3" t="b"><v>1</v></c></row>
</sheetData><mergeCells count="1"><mergeCell ref="A4:B4"/></mergeCells></worksheet>"""
    s2 = f'<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData><row r="1"><c r="A1" t="str"><v>so uma</v></c></row></sheetData></worksheet>'
    return _zip(
        destino,
        "plan.xlsx",
        [
            ("xl/workbook.xml", wb.encode()),
            ("xl/_rels/workbook.xml.rels", wrels.encode()),
            ("xl/sharedStrings.xml", ss.encode()),
            ("xl/worksheets/sheet1.xml", s1.encode()),
            ("xl/worksheets/sheet2.xml", s2.encode()),
        ],
    )


def html(destino: Path) -> Path:
    p = destino / "pagina.html"
    p.write_text(
        """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Página de prova</title>
<style>body{}</style><script>var x = 1;</script></head><body>
<h1>Cabeçalho</h1><p>Parágrafo <b>com</b> negrito e <a href="x">link</a>.</p>
<p hidden>escondido</p><p style="display:none">também escondido</p>
<ul><li>um</li><li>dois</li></ul>
<table><tr><th>a</th><th>b</th></tr><tr><td>1 | um</td><td>2</td></tr></table>
<pre>linha 1
  linha 2</pre><img src="img/x.png" alt="x"></body></html>""",
        encoding="utf-8",
    )
    return p


def mhtml(destino: Path) -> Path:
    p = destino / "snapshot.mhtml"
    p.write_bytes(
        b"""From: <Saved by Blink>
Snapshot-Content-Location: https://exemplo.org/a
Subject: Prova
MIME-Version: 1.0
Content-Type: multipart/related;\r\n\ttype="text/html";\r\n\tboundary="----MultipartBoundary--abc----"

------MultipartBoundary--abc----
Content-Type: text/html
Content-ID: <frame-1@mhtml.blink>
Content-Transfer-Encoding: quoted-printable
Content-Location: https://exemplo.org/a

<html><head><meta charset=3D"utf-8"></head><body><h1>T=C3=ADtulo do snapsh=
ot</h1><p>Corpo do snapshot.</p></body></html>
------MultipartBoundary--abc----
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: https://exemplo.org/x.png

iVBORw0KGgo=
------MultipartBoundary--abc------
"""
    )
    return p


def zip_generico(destino: Path) -> Path:
    return _zip(destino, "pacote.zip", [("a/leia.txt", b"ola\nmundo\n"), ("b.md", b"# t\n")])


def elf(destino: Path) -> Path:
    p = destino / "programa"
    p.write_bytes(b"\x7fELF\x02\x01\x01" + bytes(range(256)) * 4)
    return p


def todas(destino: Path) -> dict[str, Path]:
    return {
        "pdf": pdf(destino),
        "epub": epub(destino),
        "docx": docx(destino),
        "pptx": pptx(destino),
        "xlsx": xlsx(destino),
        "html": html(destino),
        "mhtml": mhtml(destino),
        "png": png(destino),
        "zip": zip_generico(destino),
        "elf": elf(destino),
    }


@pytest.fixture(scope="module")
def fx(tmp_path_factory) -> dict[str, Path]:
    return todas(tmp_path_factory.mktemp("formatos"))


def _segue(p: Path, **kw):
    pags = [L.le(p, **kw)]
    while pags[-1].get("proximo_args"):
        assert len(pags) < 5_000, "a continuação não anda"
        a = dict(pags[-1]["proximo_args"])
        pags.append(L.le(a.pop("caminho"), **a))
    return pags


def _segue_cli(p: Path, **kw):
    rc, pg = _chamar({"caminho": str(p), **kw})
    assert rc == 0, pg
    pags = [pg]
    while pags[-1].get("proximo_args"):
        assert len(pags) < 5_000, "a continuação não anda"
        rc, nxt = _chamar(dict(pags[-1]["proximo_args"]))
        assert rc == 0, nxt
        pags.append(nxt)
    return pags


def _soma(pags) -> str:
    return "".join(pg["conteudo"] for pg in pags)


# --- C18: toda linha da tabela lida inteira, sem recusa -------------------------------------------
@pytest.mark.parametrize(
    "nome,tipo",
    [
        ("epub", F.EPUB),
        ("docx", F.DOCX),
        ("pptx", F.PPTX),
        ("xlsx", F.XLSX),
        ("zip", F.ZIP),
    ],
)
def test_c18_formato_le_inteiro_sem_recusa(fx, nome, tipo):
    r = L.le(fx[nome])
    assert "recusado" not in r and "erro" not in r, r
    assert r["tipo"] == tipo and r["conteudo"] and r["encoding"]["por"] == "binario"
    assert tipo in r["cabecalho"]


@pytest.mark.parametrize("orcamento", (1, 7, 64, 300, 4_096, 40_000))
@pytest.mark.parametrize("nome", ["epub", "docx", "pptx", "xlsx"])
def test_c18_paginas_somadas_cobrem_toda_unidade_uma_vez(fx, nome, orcamento):
    L.esvazia_cache()
    ref = _soma(_segue(fx[nome], max_bytes=L.ORCAMENTO_MAX))
    L.esvazia_cache()
    pags = _segue(fx[nome], max_bytes=orcamento)
    assert _soma(pags) == ref
    assert pags[-1]["proximo"] == L.FIM and "proximo_args" not in pags[-1]
    if pags[0].get("paginas_total"):
        marcas = [ln for ln in ref.splitlines() if ln.startswith("<!-- p. ")]
        assert marcas == [f"<!-- p. {i} -->" for i in range(1, pags[0]["paginas_total"] + 1)]


def test_c18_tipo_pelos_bytes_e_nao_pelo_nome(fx, tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    p = tmp_path / "disfarce.txt"
    p.write_bytes(fx["pdf"].read_bytes())
    rc, rpdf = _chamar({"caminho": str(p)})
    assert rc == 0 and rpdf["tipo"] == F.PDF
    z = tmp_path / "disfarce.zip"
    z.write_bytes(fx["epub"].read_bytes())
    assert L.le(z)["tipo"] == F.EPUB and L.le(z)["unidade"] == "item"
    d = tmp_path / "sem_extensao"
    d.write_bytes(fx["html"].read_bytes())
    assert L.le(d)["tipo"] == F.HTML
    m = tmp_path / "snapshot"
    m.write_bytes(fx["mhtml"].read_bytes())
    assert L.le(m)["tipo"] == F.MHTML


# --- PDF: texto por página, imagem por página, página sem camada (via venv harness com pymupdf) ---
def test_c18_pdf_texto_por_pagina_e_paginacao(fx, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["pdf"].parent))
    rc, r = _chamar({"caminho": str(fx["pdf"])})
    assert rc == 0 and r["tipo"] == F.PDF and r["encoding"]["por"] == "binario"
    assert r["unidade"] == "pagina" and r["paginas_total"] == 4 and r["paginas"] == [1, 4]
    assert "<!-- p. 1 -->\nPagina 1 do PDF de prova." in r["conteudo"]
    assert "página 1–4 de 4" in r["cabecalho"]
    rc2, r2 = _chamar({"caminho": str(fx["pdf"]), "paginas": "2-3"})
    assert rc2 == 0 and r2["paginas"] == [2, 3]
    assert "Pagina 2" in r2["conteudo"] and "Pagina 4" not in r2["conteudo"]
    assert "Pagina 1" not in r2["conteudo"]
    rc3, r3 = _chamar({"caminho": str(fx["pdf"]), "paginas": "2-3", "linhas": "2-2"})
    assert rc3 == 0 and r3["conteudo"] == "Pagina 2 do PDF de prova.\n" and r3["linhas"] == [2, 2]
    # Páginas somadas em orçamento pequeno cobrem todas as unidades uma vez
    ref = _soma(_segue_cli(fx["pdf"], max_bytes=L.ORCAMENTO_MAX))
    assert _soma(_segue_cli(fx["pdf"], max_bytes=64)) == ref


def test_c18_pdf_modo_pagina_e_sem_camada(fx, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["pdf"].parent))
    rc, r = _chamar({"caminho": str(fx["pdf"]), "modo": "pagina"})
    assert rc == 0 and [i["pagina"] for i in r["imagens"]] == [1, 2, 3, 4]
    for i in r["imagens"]:
        raw = base64.b64decode(i["base64"])
        assert raw[:8] == b"\x89PNG\r\n\x1a\n" and i["mime"] == F.PNG and i["dpi"] == 150
        assert i["largura"] > 1000 and i["altura"] > i["largura"]
    assert r["proximo"] == L.FIM and "conteudo" not in r
    rc72, r72 = _chamar({"caminho": str(fx["pdf"]), "modo": "pagina", "paginas": "4-4", "dpi": 72})
    assert rc72 == 0 and len(r72["imagens"]) == 1 and r72["imagens"][0]["largura"] == 595
    # Página 4 sem camada de texto avisa e aponta modo="pagina"
    rc_sc, r_sc = _chamar({"caminho": str(fx["pdf"]), "paginas": "4-4"})
    assert rc_sc == 0 and r_sc["cabecalho"].startswith("SEM CAMADA DE TEXTO p. 4")
    assert r_sc["sem_texto"] == [4] and 'modo="pagina"' in r_sc["cura"]
    assert "<!-- p. 4 -->" in r_sc["conteudo"] and "sem camada de texto" in r_sc["conteudo"]
    # Lote de imagens conta pelos bytes do PNG
    rc_lote, r_lote = _chamar(
        {"caminhos": [str(fx["pdf"]), str(fx["pdf"])], "modo": "pagina", "teto": 1}
    )
    assert rc_lote == 0 and "imagens" in r_lote["lote"][0]
    assert r_lote["lote"][1] == {"omitido_por_teto": True}


# --- EPUB, DOCX, PPTX, XLSX: a ordem e as partes do formato ---------------------------------------
def test_c18_epub_spine_em_ordem_e_imagem_pelo_caminho(fx):
    r = L.le(fx["epub"])
    c = r["conteudo"]
    assert r["unidade"] == "item" and r["paginas_total"] == 2
    assert c.index("Capitulo Um") < c.index("Capitulo Dois")
    assert "Primeiro parágrafo" in c
    assert "alert(1)" not in c and "color:red" not in c
    assert "[imagem: OEBPS/img/fig.png" in c
    assert "| a | b |" in c and "| --- | --- |" in c
    img = L.le(fx["epub"], membro="OEBPS/img/fig.png", modo="pagina")
    assert img["imagens"][0]["png"] == fx["png"].read_bytes()
    assert img["caminho"].endswith("livro.epub!OEBPS/img/fig.png")


def test_c18_docx_paragrafos_tabelas_e_notas_ao_fim(fx):
    r = L.le(fx["docx"])
    c = r["conteudo"]
    assert r["unidade"] == "nenhuma" and "paginas_total" not in r
    assert c.startswith("# Titulo do documento\n")
    assert "Primeiro paragrafo[^1], com nota." in c and "- item de lista" in c
    assert "| col a | col b |" in c and "| mesclada | mesclada |" in c
    assert c.index("<!-- notas -->") > c.index("Ultimo paragrafo")
    assert "[^1]: Texto da nota de rodape." in c
    assert "<!-- comentários -->" in c and "[c0] Olga: Revisar isto." in c
    erro = L.le(fx["docx"], paginas="1-1")
    assert erro["classe_erro"] == "gramatica" and "unidade fixa" in erro["erro"]


def test_c18_pptx_ordem_da_apresentacao_e_notas(fx):
    r = L.le(fx["pptx"])
    c = r["conteudo"]
    assert r["unidade"] == "slide" and r["paginas_total"] == 2
    assert c.index("# Slide arquivo dois") < c.index("# Slide arquivo um")
    assert "<!-- p. 1 -->\n# Slide arquivo dois" in c
    assert "| h1 | h2 |" in c and "| v1 | v2 |" in c
    assert "<!-- notas do apresentador -->" in c and "Nota do apresentador do slide um." in c
    assert "- subitem" in c
    rec = L.le(fx["pptx"], modo="pagina")
    assert rec["recusado"] is True and rec["motivo"] == "sem_render"


def test_c18_xlsx_planilha_como_tabela_de_valores(fx):
    r = L.le(fx["xlsx"])
    c = r["conteudo"]
    assert r["unidade"] == "planilha" and r["nomes"] == ["Vendas", "Resumo"]
    assert "planilha: Vendas" in c and "| produto | total |" in c
    assert "| cafe | 3 |" in c
    assert "SUM(" not in c
    assert "| cha | VERDADEIRO |" in c
    assert "planilha: Resumo" in c and "| so uma |" in c
    r2 = L.le(fx["xlsx"], paginas="2-2")
    assert r2["paginas"] == [2, 2] and "Vendas" not in r2["conteudo"]


# --- HTML e MHTML: fonte em texto, visível em modo="visivel" --------------------------------------
def test_c18_html_texto_e_fonte_e_visivel_e_o_texto(fx):
    fonte = L.le(fx["html"])
    assert fonte["conteudo"] == fx["html"].read_text(encoding="utf-8")
    r = L.le(fx["html"], modo="visivel")
    c = r["conteudo"]
    assert r["tipo"] == F.HTML and r["encoding"]["por"] == "estrito"
    assert "var x" not in c and "body{}" not in c
    assert "escondido" not in c
    assert "# Cabeçalho" in c and "Parágrafo com negrito e link." in c
    assert "- um\n" in c and "- dois\n" in c
    assert "| 1 \\| um | 2 |" in c
    assert "linha 1\n  linha 2" in c
    assert "[imagem: img/x.png — x]" in c
    assert "proximo_args" not in r
    assert L.le(fx["html"], modo="visivel", max_bytes=20)["proximo_args"]["modo"] == "visivel"


def test_c18_mhtml_desembrulha_a_parte_html(fx):
    r = L.le(fx["mhtml"], modo="visivel")
    assert r["tipo"] == F.MHTML
    assert r["conteudo"] == "# Título do snapshot\n\nCorpo do snapshot.\n"
    assert L.le(fx["mhtml"])["conteudo"].startswith("From: <Saved by Blink>")


# --- imagem, ZIP (`caminho!membro`), GZIP e o que fica fora ---------------------------------------
def test_c18_imagem_nao_recusa_e_sai_inteira_em_modo_pagina(fx):
    r = L.le(fx["png"])
    assert "recusado" not in r and r["cabecalho"].startswith("IMAGEM") and r["conteudo"] == ""
    assert "4×3 px" in r["cabecalho"] and 'modo="pagina"' in r["cura"]
    img = L.le(fx["png"], modo="pagina")
    assert img["imagens"][0]["png"] == fx["png"].read_bytes() and img["imagens"][0]["mime"] == F.PNG


def test_c18_zip_lista_e_membro_se_le(fx, monkeypatch):
    r = L.le(fx["zip"])
    assert r["tipo"] == F.ZIP and r["conteudo"] == "a/leia.txt  10\nb.md  4\n"
    m = L.le(fx["zip"], membro="a/leia.txt")
    assert m["conteudo"] == "ola\nmundo\n" and m["tipo"] == "text/plain"
    assert m["caminho"].endswith("pacote.zip!a/leia.txt")
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["zip"].parent))
    m_bang = L.ler(f"{fx['zip']}!a/leia.txt")
    assert m_bang["conteudo"] == "ola\nmundo\n" and m_bang["caminho"].endswith("pacote.zip!a/leia.txt")
    rc, m_cli = _chamar({"caminho": f"{fx['zip']}!a/leia.txt"})
    assert rc == 0 and m_cli["conteudo"] == "ola\nmundo\n"
    falta = L.le(fx["zip"], membro="nao")
    assert falta["erro"] == "membro não existe" and falta["la_tem"] == ["a/leia.txt", "b.md"]


def test_c18_gzip_le_o_que_ha_dentro(fx, tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    g = tmp_path / "prova.pdf.gz"
    g.write_bytes(gzip.compress(fx["pdf"].read_bytes()))
    rc, r = _chamar({"caminho": str(g)})
    assert rc == 0 and "recusado" not in r and r["tipo"] == F.PDF
    assert r["gzip"]["bytes_comprimidos"] == g.stat().st_size
    assert "descomprimido de gzip" in r["cabecalho"] and "<!-- p. 1 -->" in r["conteudo"]
    t = tmp_path / "texto.txt.gz"
    t.write_bytes(gzip.compress("linha um\nlinha dois\n".encode()))
    assert L.le(t)["conteudo"] == "linha um\nlinha dois\n"
    assert L.le(t, modo="pagina")["classe_erro"] == "gramatica"
    ruim = tmp_path / "ruim.gz"
    ruim.write_bytes(b"\x1f\x8b\x08\x00" + b"\x00" * 20)
    assert L.le(ruim)["classe_erro"] == "binario" and "gzip não abre" in L.le(ruim)["erro"]


def test_c18_binario_fora_da_tabela_recusa_sem_leitor(fx):
    r = L.le(fx["elf"])
    assert r["recusado"] is True and r["motivo"] == "sem_leitor" and r["tipo"] == "application/x-elf"
    assert "conteudo" not in r and r["classe_erro"] == "binario" and "§7.4" in r["cura"]


def test_c18_gramatica_dos_parametros_novos(fx, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["pdf"].parent))
    assert _chamar({"caminho": str(fx["pdf"]), "paginas": "x"})[1]["classe_erro"] == "gramatica"
    assert _chamar({"caminho": str(fx["pdf"]), "paginas": "9-"})[1]["erro"] == "página além do fim"
    assert _chamar({"caminho": str(fx["pdf"]), "modo": "pagina", "dpi": 0})[1]["classe_erro"] == "gramatica"
    assert L.le(fx["html"], modo="pagina")["classe_erro"] == "gramatica"
    assert L.le(fx["html"], paginas="1-1")["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], offset=0)["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], modo="sumario")["sumario"] is None


def test_c18_versao_muda_avisa(fx, tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    p = tmp_path / "muda.pdf"
    p.write_bytes(fx["pdf"].read_bytes())
    v = _chamar({"caminho": str(p)})[1]["versao"]
    p.write_bytes(fx["pdf"].read_bytes() + b"\n%x")
    r = _chamar({"caminho": str(p), "versao": v})[1]
    assert r["mudou"]["de"] == v and r["cabecalho"].startswith("ARQUIVO MUDOU")
