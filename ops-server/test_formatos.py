"""C18 — os formatos do acervo lidos pela porta (spec ler-arquivo §7.4, emenda de 04/10/2026).

Uma fixture por linha da tabela da §7.4, gerada em código (nada binário versionado): PDF com
camada de texto e página escaneada, EPUB, DOCX, PPTX, XLSX, HTML, MHTML, PNG, ZIP de outro
tipo, e um binário fora da tabela (ELF) para a recusa `sem_leitor`. Sem subir a porta.
"""
import struct
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import formatos as F                                           # noqa: E402
import leitura as L                                            # noqa: E402

pymupdf = pytest.importorskip("pymupdf")


def pdf(destino: Path) -> Path:
    """3 páginas com camada de texto e 1 escaneada (só imagem), ASCII puro (a fonte base-14
    grava '·' no lugar de aspas curvas — caderno c48)."""
    doc = pymupdf.open()
    for i in range(1, 4):
        pg = doc.new_page()
        pg.insert_text((72, 72), f"Pagina {i} do PDF de prova.", fontsize=12)
        pg.insert_text((72, 100), "Segunda linha, com ponto final.", fontsize=12)
    pg = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 100), False)
    pix.set_rect(pix.irect, (200, 30, 30))
    pg.insert_image(pymupdf.Rect(50, 50, 450, 250), pixmap=pix)
    p = destino / "prova.pdf"
    doc.save(str(p))
    doc.close()
    return p


def png(destino: Path) -> Path:
    def chunk(tipo, dados):
        c = tipo + dados
        return struct.pack(">I", len(dados)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    w, h = 4, 3
    raw = b"".join(b"\x00" + bytes([255, 0, 0] * w) for _ in range(h))
    dados = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
             + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    p = destino / "figura.png"
    p.write_bytes(dados)
    return p


def _zip(destino: Path, nome: str, membros: list[tuple[str, bytes]], mimetype: bytes | None = None) -> Path:
    p = destino / nome
    with zipfile.ZipFile(p, "w") as zf:
        if mimetype is not None:
            zf.writestr(zipfile.ZipInfo("mimetype"), mimetype, compress_type=zipfile.ZIP_STORED)
        for n, d in membros:
            zf.writestr(n, d, compress_type=zipfile.ZIP_DEFLATED)
    return p


def epub(destino: Path) -> Path:
    cont = b"""<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    opf = b"""<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata/><manifest>
<item id="c2" href="cap%202.xhtml" media-type="application/xhtml+xml"/>
<item id="c1" href="cap1.xhtml" media-type="application/xhtml+xml"/>
<item id="img" href="img/fig.png" media-type="image/png"/>
</manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>"""
    c1 = b"""<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Um</title><style>p{color:red}</style></head><body><h1>Capitulo Um</h1><p>Primeiro par&aacute;grafo do livro.</p><p><img src="img/fig.png" alt="figura um"/></p><script>alert(1)</script></body></html>"""
    c2 = b"""<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Capitulo Dois</h1><p>Segundo capitulo.</p><table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table></body></html>"""
    return _zip(destino, "livro.epub", [("META-INF/container.xml", cont), ("OEBPS/content.opf", opf),
                                        ("OEBPS/cap1.xhtml", c1), ("OEBPS/cap 2.xhtml", c2),
                                        ("OEBPS/img/fig.png", png(destino).read_bytes())],
                mimetype=b"application/epub+zip")


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
    styles = f"""<?xml version="1.0"?><w:styles xmlns:w="{_W}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>"""
    notas = f"""<?xml version="1.0"?><w:footnotes xmlns:w="{_W}"><w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote><w:footnote w:id="1"><w:p><w:r><w:t>Texto da nota de rodape.</w:t></w:r></w:p></w:footnote></w:footnotes>"""
    coment = f"""<?xml version="1.0"?><w:comments xmlns:w="{_W}"><w:comment w:id="0" w:author="Olga"><w:p><w:r><w:t>Revisar isto.</w:t></w:r></w:p></w:comment></w:comments>"""
    ct = b"""<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>"""
    return _zip(destino, "doc.docx", [("[Content_Types].xml", ct), ("word/document.xml", doc.encode()),
                                      ("word/styles.xml", styles.encode()), ("word/footnotes.xml", notas.encode()),
                                      ("word/comments.xml", coment.encode())])


_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def pptx(destino: Path) -> Path:
    """A ordem da apresentação (slide2 antes de slide1) difere da do nome do arquivo (O2)."""
    pres = f"""<?xml version="1.0"?><p:presentation xmlns:p="{_P}" xmlns:r="{_R}"><p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId1"/></p:sldIdLst></p:presentation>"""
    prels = f"""<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/></Relationships>"""

    def slide(titulo, corpo):
        return f"""<?xml version="1.0"?><p:sld xmlns:p="{_P}" xmlns:a="{_A}" xmlns:r="{_R}"><p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:cNvPr id="2" name="T"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{titulo}</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr id="3" name="C"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:txBody><a:p><a:r><a:t>{corpo}</a:t></a:r></a:p><a:p><a:pPr lvl="1"/><a:r><a:t>subitem</a:t></a:r></a:p></p:txBody></p:sp>
<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>h1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>h2</a:t></a:r></a:p></a:txBody></a:tc></a:tr><a:tr><a:tc><a:txBody><a:p><a:r><a:t>v1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>v2</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>
</p:spTree></p:cSld></p:sld>"""
    s1rels = f"""<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/></Relationships>"""
    notas = f"""<?xml version="1.0"?><p:notes xmlns:p="{_P}" xmlns:a="{_A}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="N"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Nota do apresentador do slide um.</a:t></a:r></a:p></p:txBody></p:sp><p:sp><p:nvSpPr><p:cNvPr id="3" name="num"/><p:cNvSpPr/><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>1</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:notes>"""
    return _zip(destino, "apres.pptx", [("ppt/presentation.xml", pres.encode()), ("ppt/_rels/presentation.xml.rels", prels.encode()),
                                        ("ppt/slides/slide1.xml", slide("Slide arquivo um", "Corpo um").encode()),
                                        ("ppt/slides/slide2.xml", slide("Slide arquivo dois", "Corpo dois").encode()),
                                        ("ppt/slides/_rels/slide1.xml.rels", s1rels.encode()),
                                        ("ppt/notesSlides/notesSlide1.xml", notas.encode())])


_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def xlsx(destino: Path) -> Path:
    wb = f"""<?xml version="1.0"?><workbook xmlns="{_S}" xmlns:r="{_R}"><sheets><sheet name="Vendas" sheetId="1" r:id="rId1"/><sheet name="Resumo" sheetId="2" r:id="rId2"/></sheets></workbook>"""
    wrels = f"""<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" Type="x/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="x/worksheet" Target="worksheets/sheet2.xml"/></Relationships>"""
    ss = f"""<?xml version="1.0"?><sst xmlns="{_S}" count="3" uniqueCount="3"><si><t>produto</t></si><si><t>total</t></si><si><r><t>ca</t></r><r><t>fe</t></r></si></sst>"""
    s1 = f"""<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData>
<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><f>SUM(1,2)</f><v>3</v></c></row>
<row r="3"><c r="A3" t="inlineStr"><is><t>cha</t></is></c><c r="B3" t="b"><v>1</v></c></row>
</sheetData><mergeCells count="1"><mergeCell ref="A4:B4"/></mergeCells></worksheet>"""
    s2 = f"""<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData><row r="1"><c r="A1" t="str"><v>so uma</v></c></row></sheetData></worksheet>"""
    return _zip(destino, "plan.xlsx", [("xl/workbook.xml", wb.encode()), ("xl/_rels/workbook.xml.rels", wrels.encode()),
                                       ("xl/sharedStrings.xml", ss.encode()), ("xl/worksheets/sheet1.xml", s1.encode()),
                                       ("xl/worksheets/sheet2.xml", s2.encode())])


def html(destino: Path) -> Path:
    p = destino / "pagina.html"
    p.write_text("""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Página de prova</title>
<style>body{}</style><script>var x = 1;</script></head><body>
<h1>Cabeçalho</h1><p>Parágrafo <b>com</b> negrito e <a href="x">link</a>.</p>
<p hidden>escondido</p><p style="display:none">também escondido</p>
<ul><li>um</li><li>dois</li></ul>
<table><tr><th>a</th><th>b</th></tr><tr><td>1 | um</td><td>2</td></tr></table>
<pre>linha 1
  linha 2</pre><img src="img/x.png" alt="x"></body></html>""", encoding="utf-8")
    return p


def mhtml(destino: Path) -> Path:
    p = destino / "snapshot.mhtml"
    p.write_bytes(b"""From: <Saved by Blink>
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
""")
    return p


def zip_generico(destino: Path) -> Path:
    return _zip(destino, "pacote.zip", [("a/leia.txt", b"ola\nmundo\n"), ("b.md", b"# t\n")])


def elf(destino: Path) -> Path:
    p = destino / "programa"
    p.write_bytes(b"\x7fELF\x02\x01\x01" + bytes(range(256)) * 4)
    return p


def todas(destino: Path) -> dict:
    return {"pdf": pdf(destino), "epub": epub(destino), "docx": docx(destino), "pptx": pptx(destino),
            "xlsx": xlsx(destino), "html": html(destino), "mhtml": mhtml(destino), "png": png(destino),
            "zip": zip_generico(destino), "elf": elf(destino)}


@pytest.fixture(scope="module")
def fx(tmp_path_factory) -> dict:
    return todas(tmp_path_factory.mktemp("formatos"))


def _segue(p, **kw):
    pags = [L.le(p, **kw)]
    while pags[-1].get("proximo_args"):
        assert len(pags) < 5_000, "a continuação não anda"
        a = dict(pags[-1]["proximo_args"])
        pags.append(L.le(a.pop("caminho"), **a))
    return pags


def _soma(pags) -> str:
    return "".join(pg["conteudo"] for pg in pags)


# --- C18: toda linha da tabela lida inteira, sem recusa ------------------------------------
@pytest.mark.parametrize("nome,tipo", [
    ("pdf", F.PDF), ("epub", F.EPUB), ("docx", F.DOCX), ("pptx", F.PPTX), ("xlsx", F.XLSX),
    ("zip", F.ZIP),
])
def test_c18_formato_le_inteiro_sem_recusa(fx, nome, tipo):
    r = L.le(fx[nome])
    assert "recusado" not in r and "erro" not in r, r
    assert r["tipo"] == tipo and r["conteudo"] and r["encoding"]["por"] == "binario"
    assert tipo in r["cabecalho"]


@pytest.mark.parametrize("orcamento", (1, 7, 64, 300, 4_096, 40_000))
@pytest.mark.parametrize("nome", ["pdf", "epub", "docx", "pptx", "xlsx"])
def test_c18_paginas_somadas_cobrem_toda_unidade_uma_vez(fx, nome, orcamento):
    """§7.4.6: seguindo `proximo_args` até `fim do arquivo`, toda unidade aparece uma vez."""
    L.esvazia_cache()
    ref = _soma(_segue(fx[nome], max_bytes=L.ORCAMENTO_MAX))
    L.esvazia_cache()
    pags = _segue(fx[nome], max_bytes=orcamento)
    assert _soma(pags) == ref
    assert pags[-1]["proximo"] == L.FIM and "proximo_args" not in pags[-1]
    if pags[0].get("paginas_total"):
        marcas = [ln for ln in ref.splitlines() if ln.startswith("<!-- p. ")]
        assert marcas == [f"<!-- p. {i} -->" for i in range(1, pags[0]["paginas_total"] + 1)]


def test_c18_tipo_pelos_bytes_e_nao_pelo_nome(fx, tmp_path):
    """F2 da lista antipadroes-de-transcricao: PDF chamado .txt e EPUB chamado .zip leem certo."""
    p = tmp_path / "disfarce.txt"
    p.write_bytes(fx["pdf"].read_bytes())
    assert L.le(p)["tipo"] == F.PDF
    z = tmp_path / "disfarce.zip"
    z.write_bytes(fx["epub"].read_bytes())
    assert L.le(z)["tipo"] == F.EPUB and L.le(z)["unidade"] == "item"
    d = tmp_path / "sem_extensao"
    d.write_bytes(fx["html"].read_bytes())
    assert L.le(d)["tipo"] == F.HTML
    m = tmp_path / "snapshot"
    m.write_bytes(fx["mhtml"].read_bytes())
    assert L.le(m)["tipo"] == F.MHTML


# --- PDF: texto por página, imagem por página, página sem camada ----------------------------
def test_c18_pdf_texto_por_pagina(fx):
    r = L.le(fx["pdf"])
    assert r["unidade"] == "pagina" and r["paginas_total"] == 4 and r["paginas"] == [1, 4]
    assert "<!-- p. 1 -->\nPagina 1 do PDF de prova." in r["conteudo"]
    assert "página 1–4 de 4" in r["cabecalho"]
    r2 = L.le(fx["pdf"], paginas="2-3")
    assert r2["paginas"] == [2, 3] and "Pagina 2" in r2["conteudo"] and "Pagina 4" not in r2["conteudo"]
    assert "Pagina 1" not in r2["conteudo"]
    r3 = L.le(fx["pdf"], paginas="2-3", linhas="2-2")
    assert r3["conteudo"] == "Pagina 2 do PDF de prova.\n" and r3["linhas"] == [2, 2]


def test_c18_pdf_modo_pagina_uma_imagem_por_pagina(fx):
    r = L.le(fx["pdf"], modo="pagina")
    assert [i["pagina"] for i in r["imagens"]] == [1, 2, 3, 4]
    for i in r["imagens"]:
        assert i["png"][:8] == b"\x89PNG\r\n\x1a\n" and i["mime"] == F.PNG and i["dpi"] == 150
        assert i["largura"] > 1000 and i["altura"] > i["largura"]
    assert r["proximo"] == L.FIM and "conteudo" not in r
    r72 = L.le(fx["pdf"], modo="pagina", paginas="4-4", dpi=72)
    assert len(r72["imagens"]) == 1 and r72["imagens"][0]["largura"] == 595
    # o teto de bytes por chamada deixa a continuação por paginas
    teto, F.IMAGEM_TETO = F.IMAGEM_TETO, 1
    try:
        r1 = L.le(fx["pdf"], modo="pagina")
    finally:
        F.IMAGEM_TETO = teto
    assert len(r1["imagens"]) == 1 and r1["proximo_args"]["paginas"] == "2-"
    assert r1["proximo_args"]["modo"] == "pagina"


def test_c18_pdf_sem_camada_avisa_e_aponta_a_imagem(fx):
    r = L.le(fx["pdf"], paginas="4-4")
    assert r["cabecalho"].startswith("SEM CAMADA DE TEXTO p. 4")
    assert r["sem_texto"] == [4] and 'modo="pagina"' in r["cura"]
    assert "<!-- p. 4 -->" in r["conteudo"] and "sem camada de texto" in r["conteudo"]
    img = L.le(fx["pdf"], modo="pagina", paginas="4-4")
    assert img["imagens"][0]["png"][:4] == b"\x89PNG"


def test_c18_pdf_lote_conta_a_imagem_pelos_bytes_do_png(fx):
    r = L.lote([fx["pdf"], fx["pdf"]], lambda _i, p: L.le(p, modo="pagina"), teto=1)
    assert "imagens" in r["lote"][0] and r["lote"][1] == {"omitido_por_teto": True}
    assert L.servidos(r["lote"][0]) == sum(len(i["png"]) for i in r["lote"][0]["imagens"])


# --- EPUB, DOCX, PPTX, XLSX: a ordem e as partes do formato ---------------------------------
def test_c18_epub_spine_em_ordem_e_imagem_pelo_caminho(fx):
    r = L.le(fx["epub"])
    c = r["conteudo"]
    assert r["unidade"] == "item" and r["paginas_total"] == 2
    assert c.index("Capitulo Um") < c.index("Capitulo Dois")        # ordem do spine
    assert "Primeiro parágrafo" in c                                 # entidade decodificada
    assert "alert(1)" not in c and "color:red" not in c              # script e estilo fora
    assert "[imagem: OEBPS/img/fig.png" in c                         # listada pelo caminho
    assert "| a | b |" in c and "| --- | --- |" in c                 # tabela como tabela
    img = L.le(fx["epub"], membro="OEBPS/img/fig.png", modo="pagina")
    assert img["imagens"][0]["png"] == fx["png"].read_bytes()
    assert img["caminho"].endswith("livro.epub!OEBPS/img/fig.png")


def test_c18_docx_paragrafos_tabelas_e_notas_ao_fim(fx):
    r = L.le(fx["docx"])
    c = r["conteudo"]
    assert r["unidade"] == "nenhuma" and "paginas_total" not in r
    assert c.startswith("# Titulo do documento\n")
    assert "Primeiro paragrafo[^1], com nota." in c and "- item de lista" in c
    assert "| col a | col b |" in c and "| mesclada | mesclada |" in c   # gridSpan repete
    assert c.index("<!-- notas -->") > c.index("Ultimo paragrafo")
    assert "[^1]: Texto da nota de rodape." in c
    assert "<!-- comentários -->" in c and "[c0] Olga: Revisar isto." in c
    erro = L.le(fx["docx"], paginas="1-1")
    assert erro["classe_erro"] == "gramatica" and "unidade fixa" in erro["erro"]


def test_c18_pptx_ordem_da_apresentacao_e_notas(fx):
    r = L.le(fx["pptx"])
    c = r["conteudo"]
    assert r["unidade"] == "slide" and r["paginas_total"] == 2
    # O2: a ordem é a do presentation.xml (slide2 primeiro), não a do nome do arquivo
    assert c.index("# Slide arquivo dois") < c.index("# Slide arquivo um")
    assert "<!-- p. 1 -->\n# Slide arquivo dois" in c
    assert "| h1 | h2 |" in c and "| v1 | v2 |" in c                  # tabela do graphicFrame
    assert "<!-- notas do apresentador -->" in c and "Nota do apresentador do slide um." in c
    assert "- subitem" in c
    rec = L.le(fx["pptx"], modo="pagina")
    assert rec["recusado"] is True and rec["motivo"] == "sem_render"


def test_c18_xlsx_planilha_como_tabela_de_valores(fx):
    r = L.le(fx["xlsx"])
    c = r["conteudo"]
    assert r["unidade"] == "planilha" and r["nomes"] == ["Vendas", "Resumo"]
    assert "planilha: Vendas" in c and "| produto | total |" in c
    assert "| cafe | 3 |" in c                 # valor da fórmula, não a fórmula; rich text junto
    assert "SUM(" not in c
    assert "| cha | VERDADEIRO |" in c         # inlineStr e booleano
    assert "planilha: Resumo" in c and "| so uma |" in c
    r2 = L.le(fx["xlsx"], paginas="2-2")
    assert r2["paginas"] == [2, 2] and "Vendas" not in r2["conteudo"]


# --- HTML e MHTML: fonte em texto, visível em modo="visivel" --------------------------------
def test_c18_html_texto_e_fonte_e_visivel_e_o_texto(fx):
    fonte = L.le(fx["html"])
    assert fonte["conteudo"] == fx["html"].read_text(encoding="utf-8")   # read_file não encolhe
    r = L.le(fx["html"], modo="visivel")
    c = r["conteudo"]
    assert r["tipo"] == F.HTML and r["encoding"]["por"] == "estrito"
    assert "var x" not in c and "body{}" not in c
    assert "escondido" not in c                                     # hidden e display:none
    assert "# Cabeçalho" in c and "Parágrafo com negrito e link." in c
    assert "- um\n" in c and "- dois\n" in c
    assert "| 1 \\| um | 2 |" in c                                   # `|` da célula escapado
    assert "linha 1\n  linha 2" in c                                # pre preserva
    assert "[imagem: img/x.png — x]" in c
    assert r["proximo_args"] is None if "proximo_args" in r else True
    assert L.le(fx["html"], modo="visivel", max_bytes=20)["proximo_args"]["modo"] == "visivel"


def test_c18_mhtml_desembrulha_a_parte_html(fx):
    r = L.le(fx["mhtml"], modo="visivel")
    assert r["tipo"] == F.MHTML
    assert r["conteudo"] == "# Título do snapshot\n\nCorpo do snapshot.\n"
    assert L.le(fx["mhtml"])["conteudo"].startswith("From: <Saved by Blink>")


# --- imagem, ZIP e o que fica fora --------------------------------------------------------------
def test_c18_imagem_nao_recusa_e_sai_inteira_em_modo_pagina(fx):
    r = L.le(fx["png"])
    assert "recusado" not in r and r["cabecalho"].startswith("IMAGEM") and r["conteudo"] == ""
    assert "4×3 px" in r["cabecalho"] and 'modo="pagina"' in r["cura"]
    img = L.le(fx["png"], modo="pagina")
    assert img["imagens"][0]["png"] == fx["png"].read_bytes() and img["imagens"][0]["mime"] == F.PNG


def test_c18_zip_lista_e_membro_se_le(fx):
    r = L.le(fx["zip"])
    assert r["tipo"] == F.ZIP and r["conteudo"] == "a/leia.txt  10\nb.md  4\n"
    m = L.le(fx["zip"], membro="a/leia.txt")
    assert m["conteudo"] == "ola\nmundo\n" and m["tipo"] == "text/plain"
    assert m["caminho"].endswith("pacote.zip!a/leia.txt")
    falta = L.le(fx["zip"], membro="nao")
    assert falta["erro"] == "membro não existe" and falta["la_tem"] == ["a/leia.txt", "b.md"]


def test_c18_binario_fora_da_tabela_recusa_sem_leitor(fx):
    r = L.le(fx["elf"])
    assert r["recusado"] is True and r["motivo"] == "sem_leitor" and r["tipo"] == "application/x-elf"
    assert "conteudo" not in r and r["classe_erro"] == "binario" and "§7.4" in r["cura"]


def test_c18_gramatica_dos_parametros_novos(fx):
    assert L.le(fx["pdf"], paginas="x")["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], paginas="9-")["erro"] == "página além do fim"
    assert L.le(fx["pdf"], modo="pagina", dpi=0)["classe_erro"] == "gramatica"
    assert L.le(fx["html"], modo="pagina")["classe_erro"] == "gramatica"
    assert L.le(fx["html"], paginas="1-1")["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], offset=0)["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], modo="sumario")["sumario"] is None


def test_c18_apelido_read_file_le_o_formato(fx):
    r = L.como_read_file(L.le(fx["pdf"]))
    assert r["content"].startswith("<!-- p. 1 -->") and r["truncated"] is False
    assert r["next_offset"] is None and r["path"] == str(fx["pdf"])


def test_c18_versao_muda_avisa(fx, tmp_path):
    p = tmp_path / "muda.pdf"
    p.write_bytes(fx["pdf"].read_bytes())
    v = L.le(p)["versao"]
    p.write_bytes(fx["pdf"].read_bytes() + b"\n%x")
    r = L.le(p, versao=v)
    assert r["mudou"]["de"] == v and r["cabecalho"].startswith("ARQUIVO MUDOU")
