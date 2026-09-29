"""A ficha do censo com os leitores de formato de verdade (card #3189, ato temporário).

Cada teste monta um arquivo pequeno em memória, passa por `montar_ficha` e confere que o envelope do leitor
entrou na ficha sem colidir com os blocos do orquestrador. Só stdlib; markdown-it-py e langdetect são opcionais.
"""
import hashlib
import io
import sys
import zipfile
from pathlib import Path

ACERVO = Path(__file__).resolve().parent.parent / "bin" / "_acervo"
sys.path.insert(0, str(ACERVO))

import censo_ficha as fic  # noqa: E402

ID = "aaaaaaaa-0000-4000-8000-000000000001"


def _ficha(dados: bytes, arquivo: str) -> dict:
    item = {"obra_id": ID, "arquivo": arquivo, "objeto": "acervo/" + hashlib.sha256(dados).hexdigest(), "titulo": "T",
            "expurgada": False, "impressao": {"metodo": {"perfil": "pdf", "needs_ocr": False}}, "n_servindo": 1,
            "estados": {"servindo": 1}, "secoes_n": 0, "trechos_n": 1, "secoes": []}
    return fic.montar_ficha(item, lambda o: (dados, None))


def _zip(membros: dict, mimetype_primeiro: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if mimetype_primeiro:
            z.writestr(zipfile.ZipInfo("mimetype"), membros.pop("mimetype"), compress_type=zipfile.ZIP_STORED)
        for n, c in membros.items():
            z.writestr(n, c)
    return buf.getvalue()


def _epub() -> bytes:
    container = ('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    opf = ('<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">urn:x</dc:identifier>'
           '<dc:language>pt-BR</dc:language></metadata><manifest>'
           '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/></spine></package>')
    nav = ('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>'
           '<nav epub:type="toc"><ol><li><a href="c1.xhtml">Capitulo 1</a><ol><li><a href="c1.xhtml">Secao</a></li></ol></li>'
           '<li><a href="c1.xhtml">Capitulo 2</a></li></ol></nav></body></html>')
    c1 = ('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body><p>Texto do primeiro capitulo '
          'em português, com acentuação e o bastante para existir.</p></body></html>')
    return _zip({"mimetype": "application/epub+zip", "META-INF/container.xml": container, "OEBPS/content.opf": opf,
                 "OEBPS/nav.xhtml": nav, "OEBPS/c1.xhtml": c1}, mimetype_primeiro=True)


def test_epub_entra_na_ficha_com_estrutura_lingua_e_texto():
    f = _ficha(_epub(), "livro.epub")
    assert f["erro"] is None and f["formato_id"] == "epub" and f["situacao_identificacao"] == "identificado"
    assert f["epub"]["versao"] == "3.0" and f["epub"]["mimetype_conforme"]["conforme"] is True
    assert f["epub"]["sumario"]["fonte"] == "nav" and f["epub"]["sumario"]["entradas"] == 3 and f["epub"]["sumario"]["profundidade"] == 2
    assert [e["fonte"] for e in f["estrutura_declarada"]] == ["epub_nav"]
    assert f["lingua_declarada"] == "pt-BR" and f["conteiner"]["zip"] is True
    assert f["texto"]["caracteres"] > 20 and f["texto"]["normalizacao_unicode"]["nfc"] is True
    assert "_texto" not in f and "_paginas" not in f


def test_docx_entra_na_ficha_com_titulos_por_nivel():
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    doc = (f'<w:document xmlns:w="{W}"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Titulo</w:t></w:r></w:p>'
           f'<w:p><w:r><w:t>Corpo do texto.</w:t></w:r></w:p></w:body></w:document>')
    estilos = f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>'
    tipos = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    f = _ficha(_zip({"[Content_Types].xml": tipos, "word/document.xml": doc, "word/styles.xml": estilos}), "a.docx")
    assert f["formato_id"] == "docx" and f["erro"] is None
    assert f["ooxml"]["docx"]["titulos_por_nivel"] == {"1": 1}
    assert [e["fonte"] for e in f["estrutura_declarada"]] == ["docx_titulos"]


def test_html_o_bloco_do_leitor_nao_apaga_as_metricas_de_texto():
    html = ('<!DOCTYPE html><html lang="pt"><head><meta charset="utf-8"><title>Doc</title></head><body><h1>A</h1><h2>B</h2>'
            '<p>Este é um parágrafo de exemplo, escrito em português, longo o bastante para a detecção de língua.</p></body></html>')
    f = _ficha(html.encode(), "a.html")
    assert f["formato_id"] == "html" and f["erro"] is None
    assert f["texto_formato"]["html"]["h"]["1"] == 1 and f["texto_formato"]["html"]["title"] == "Doc"
    assert f["texto"]["caracteres"] > 30 and "normalizacao_unicode" in f["texto"]
    assert f["lingua_declarada"] == "pt" and f["encoding"]["declarado"] == "utf-8"


def test_txt_ganha_estrutura_derivada_por_pseudo_paginas():
    corpo = "\n".join(["1 Introdução", "texto", "1.1 Contexto", "texto", "2 Método", "texto", "3 Resultados"] * 1)
    f = _ficha(corpo.encode(), "a.txt")
    assert f["formato_id"] == "txt" and f["estrutura"]["paginas_pseudo"] is True
    assert f["estrutura"]["indicativos"]["contagem"] == 4 and f["estrutura"]["mobilia"] is None
    assert f["estrutura"]["porte"] is None


def test_markdown_sem_biblioteca_ou_com_ela_nao_levanta():
    f = _ficha("# Titulo\n\ntexto\n\n## Secao\n\n- a\n- b\n".encode(), "a.md")
    assert f["formato_id"] == "md" and f["erro"] is None
    md = f["texto_formato"]["md"]
    if md is None:                                          # venv sem markdown-it-py: lacuna com motivo, sem contagem por regex
        assert any(k.endswith("md") for k in f["lacunas"])
    else:
        assert md["cabecalhos_atx"]["1"] == 1 and md["cabecalhos_atx"]["2"] == 1
        assert f["estrutura_declarada"][0]["fonte"] == "md_cabecalhos" and f["estrutura_declarada"][0]["entradas"] == 2


def test_mobi_curto_demais_vira_erro_do_leitor_e_a_ficha_segue():
    dados = bytearray(100)
    dados[60:68] = b"BOOKMOBI"
    f = _ficha(bytes(dados), "a.mobi")
    assert f["formato_id"] == "mobi" and f["situacao_identificacao"] == "identificado"
    assert f["erro"] is None and f["mobi"] is not None


def test_pdf_sem_leitor_ou_com_leitor_devolve_ficha_sem_levantar():
    f = _ficha(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF", "a.pdf")
    assert f["formato_id"] == "pdf" and f["erro"] is None
    assert "leitor" in f["lacunas"] or "pdf" in f or f.get("erro_leitor")
