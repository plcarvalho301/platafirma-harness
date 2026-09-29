"""Card #3189, ato temporario: testes do leitor OOXML (docx, pptx, xlsx) com pacotes sinteticos."""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "_acervo")))

import censo_ooxml as leitor  # noqa: E402

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
CT_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
CT_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
CHAVES_ENVELOPE = {"ooxml", "aplicacoes_criadoras", "inibidor", "lingua_declarada", "estrutura_declarada",
                   "encoding", "_texto", "_paginas", "lacunas", "bibliotecas", "erro"}
CHAVES_BLOCO = {"tipo", "conteudo_tipo", "aplicacao", "core", "docx", "pptx", "xlsx", "membros_total"}


# ------------------------------------------------------------------ fabricas

def _zip(membros, cifrar=()):
    """Zip em memoria; `cifrar` liga o bit de criptografia geral no diretorio central."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in membros.items():
            zf.writestr(nome, conteudo)
        for info in zf.filelist:
            if info.filename in cifrar:
                info.flag_bits |= 0x1
    return buf.getvalue()


def _ctx(formato, prazo=30.0):
    return {"nome_original": "obra." + formato, "formato_id": formato, "bytes": 0, "prazo_s": prazo}


def _tipos(parte, conteudo):
    return (DECL + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/{parte}" ContentType="{conteudo}"/></Types>')


def _rels_raiz(parte, com_props=True):
    props = ""
    if com_props:
        props = ('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/'
                 'metadata/core-properties" Target="docProps/core.xml"/>'
                 f'<Relationship Id="rId3" Type="{NS_R}/extended-properties" Target="docProps/app.xml"/>')
    return (DECL + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{NS_R}/officeDocument" Target="{parte}"/>{props}</Relationships>')


def _app(programa="Microsoft Office Word", versao="16.0000"):
    return (DECL + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            f"<Application>{programa}</Application><AppVersion>{versao}</AppVersion>"
            "<Company>Órgão X</Company><Template>Normal.dotm</Template><TotalTime>12</TotalTime>"
            "<Pages>3</Pages><Words>250</Words><Slides>3</Slides></Properties>")


def _core(lingua="pt-BR"):
    tag_lingua = f"<dc:language>{lingua}</dc:language>" if lingua else ""
    return (DECL + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
            'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:title>Obra de teste</dc:title><dc:creator>Ana</dc:creator>"
            "<cp:lastModifiedBy>Beto</cp:lastModifiedBy>"
            '<dcterms:created xsi:type="dcterms:W3CDTF">2024-03-01T10:00:00Z</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">2024-04-02T11:30:00Z</dcterms:modified>'
            f"{tag_lingua}</cp:coreProperties>")


def _estilo(sid, nome, base=None, outline=None):
    base_xml = f'<w:basedOn w:val="{base}"/>' if base else ""
    ppr = f'<w:pPr><w:outlineLvl w:val="{outline}"/></w:pPr>' if outline is not None else ""
    return f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{nome}"/>{base_xml}{ppr}</w:style>'


def _styles(lingua="en-US"):
    estilos = "".join([
        _estilo("Normal", "Normal"),
        _estilo("Ttulo1", "Título 1"),                       # pt-BR
        _estilo("Heading2", "heading 2"),                    # ingles
        _estilo("MeuTitulo", "Meu título", base="Ttulo1"),   # herda por basedOn
        _estilo("Corpo", "Corpo", outline=1),                # so outlineLvl no estilo
        _estilo("Title", "Title"),
        _estilo("CicloA", "Ciclo A", base="CicloB"),         # ciclo de basedOn
        _estilo("CicloB", "Ciclo B", base="CicloA"),
    ])
    return (DECL + f'<w:styles xmlns:w="{NS_W}"><w:docDefaults><w:rPrDefault><w:rPr>'
            f'<w:lang w:val="{lingua}" w:eastAsia="pt-BR"/></w:rPr></w:rPrDefault></w:docDefaults>{estilos}</w:styles>')


def _p(texto="", estilo=None, outline=None, extra_ppr=""):
    ppr = ""
    if estilo:
        ppr += f'<w:pStyle w:val="{estilo}"/>'
    if outline is not None:
        ppr += f'<w:outlineLvl w:val="{outline}"/>'
    ppr = f"<w:pPr>{ppr}{extra_ppr}</w:pPr>" if ppr or extra_ppr else ""
    run = f"<w:r><w:t>{texto}</w:t></w:r>" if texto else ""
    return f"<w:p>{ppr}{run}</w:p>"


def _documento(corpo, ns=NS_W):
    return DECL + f'<w:document xmlns:w="{ns}" xmlns:mc="{NS_MC}"><w:body>{corpo}</w:body></w:document>'


def _corpo_completo():
    caixa = ('<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><w:txbxContent>'
             + _p("caixa") + "</w:txbxContent></w:drawing></mc:Choice><mc:Fallback><w:pict><w:txbxContent>"
             + _p("caixa") + "</w:txbxContent></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>")
    mudou = ('<w:p><w:pPr><w:pPrChange w:id="1"><w:pPr><w:pStyle w:val="Heading3"/></w:pPr></w:pPrChange></w:pPr>'
             "<w:r><w:t>Mudou</w:t></w:r></w:p>")
    tabulado = "<w:p><w:r><w:t>a</w:t><w:tab/><w:t>b</w:t></w:r></w:p>"
    return "".join([
        _p("Capítulo um", "Ttulo1"),
        _p("Seção 1.1", "Heading2"),
        _p("Herdado", "MeuTitulo"),
        _p("Por outline", outline=2),
        _p("Corpo com outline", "Corpo"),
        _p("Texto comum", "Normal"),
        f"<w:tbl><w:tr><w:tc>{_p('célula')}</w:tc></w:tr></w:tbl>",
        _p("Nome da obra", "Title"),
        _p("Sem título", "CicloA"),
        tabulado,
        caixa,
        mudou,
        _p("Fim", extra_ppr="<w:sectPr/>"),
        "<w:sectPr/>",
    ])


def _docx(corpo=None, com_core=True, com_styles=True, lingua_core="pt-BR", ns=NS_W):
    membros = {
        "[Content_Types].xml": _tipos("word/document.xml", CT_DOCX),
        "_rels/.rels": _rels_raiz("word/document.xml", com_props=True),
        "word/document.xml": _documento(corpo if corpo is not None else _corpo_completo(), ns),
        "docProps/app.xml": _app(),
    }
    if com_core:
        membros["docProps/core.xml"] = _core(lingua_core)
    if com_styles:
        membros["word/styles.xml"] = _styles()
    return _zip(membros)


def _slide(*formas):
    return (DECL + f'<p:sld xmlns:a="{NS_A}" xmlns:p="{NS_P}"><p:cSld><p:spTree>' + "".join(formas)
            + "</p:spTree></p:cSld></p:sld>")


def _forma(tipo_ph, *paragrafos):
    ph = f'<p:ph type="{tipo_ph}"/>' if tipo_ph else ""
    corpo = "".join("<a:p>" + "".join(f"<a:r><a:t>{t}</a:t></a:r>" for t in runs) + "</a:p>" for runs in paragrafos)
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="f"/><p:cNvSpPr/><p:nvPr>{ph}</p:nvPr></p:nvSpPr><p:spPr/>'
            f"<p:txBody><a:bodyPr/>{corpo}</p:txBody></p:sp>")


def _pptx():
    return _zip({
        "[Content_Types].xml": _tipos("ppt/presentation.xml", CT_PPTX),
        "_rels/.rels": _rels_raiz("ppt/presentation.xml"),
        "ppt/presentation.xml": DECL + f'<p:presentation xmlns:p="{NS_P}"/>',
        "docProps/app.xml": _app("Microsoft Office PowerPoint", "16.0000"),
        "docProps/core.xml": _core(),
        "ppt/slides/slide1.xml": _slide(_forma("ctrTitle", ["Tít", "ulo"]), _forma("subTitle", ["Sub"])),
        "ppt/slides/slide10.xml": _slide(_forma(None, ["Terceiro"])),   # numero 10 vem depois do 2
        "ppt/slides/slide2.xml": _slide(_forma("body", ["Segundo", " slide"], ["Outra linha"])),
        "ppt/slides/_rels/slide1.xml.rels": DECL + "<Relationships/>",
        "ppt/notesSlides/notesSlide1.xml": _slide(_forma("body", ["nota"])),
        "ppt/notesSlides/_rels/notesSlide1.xml.rels": DECL + "<Relationships/>",
    })


def _xlsx(com_textos=True):
    membros = {
        "[Content_Types].xml": _tipos("xl/workbook.xml", CT_XLSX),
        "_rels/.rels": _rels_raiz("xl/workbook.xml"),
        "xl/workbook.xml": DECL + f'<workbook xmlns="{NS_S}" xmlns:r="{NS_R}"><sheets>'
                                  '<sheet name="Plan1" sheetId="1" r:id="rId1"/>'
                                  '<sheet name="Dados" sheetId="2" r:id="rId2"/></sheets></workbook>',
        "docProps/app.xml": _app("Microsoft Excel", "16.0300"),
        "docProps/core.xml": _core(None),
    }
    if com_textos:
        membros["xl/sharedStrings.xml"] = (
            DECL + f'<sst xmlns="{NS_S}" count="3" uniqueCount="3"><si><t>Nome</t></si>'
            "<si><r><t>Rico </t></r><r><t>texto</t></r></si>"
            '<si><t>Kanji</t><rPh sb="0" eb="1"><t>fonetica</t></rPh></si></sst>')
    return _zip(membros)


def _grande(n):
    """Documento com n paragrafos (varios blocos de leitura)."""
    return _docx("".join(_p(f"Paragrafo numero {i} com algum texto de enchimento") for i in range(n)))


# --------------------------------------------------------------------- DOCX

def test_docx_titulos_por_nivel_e_estrutura():
    r = leitor.ler(_docx(), _ctx("docx"))
    assert r["erro"] is None
    d = r["ooxml"]["docx"]
    assert d["paragrafos"] == 14
    # Título 1 (pt-BR, styleId Ttulo1), basedOn herdado e Title: nivel 1
    # heading 2 (ingles) e estilo com outlineLvl 1: nivel 2; outlineLvl direto 2: nivel 3
    assert d["titulos_por_nivel"] == {"1": 3, "2": 2, "3": 1}
    assert d["paragrafos_titulo"] == 6
    assert d["outline_lvl"] == {"2": 1, "3": 1}
    assert d["tabelas"] == 1
    assert d["secoes"] == 2
    assert r["estrutura_declarada"] == [{"fonte": "docx_titulos", "entradas": 6, "profundidade": 3}]


def test_docx_texto_um_paragrafo_por_linha():
    r = leitor.ler(_docx(), _ctx("docx"))
    assert r["_texto"].split("\n") == [
        "Capítulo um", "Seção 1.1", "Herdado", "Por outline", "Corpo com outline", "Texto comum", "célula",
        "Nome da obra", "Sem título", "a b", "caixa", "", "Mudou", "Fim"]
    assert r["_paginas"] is None and r["encoding"] is None


def test_docx_fallback_do_mc_nao_conta_em_dobro_e_pprchange_nao_e_titulo():
    corpo = _p("x") + _corpo_completo().split(_p("Fim", extra_ppr="<w:sectPr/>"))[0]
    d = leitor.ler(_docx(corpo), _ctx("docx"))["ooxml"]["docx"]
    assert d["titulos_por_nivel"] == {"1": 3, "2": 2, "3": 1}   # Heading3 do pPrChange nao entra
    assert d["paragrafos"] == 1 + 13                             # caixa contada uma vez


def test_docx_propriedades_e_aplicacao_criadora():
    r = leitor.ler(_docx(), _ctx("docx"))
    o = r["ooxml"]
    assert o["tipo"] == "docx" and o["conteudo_tipo"] == CT_DOCX
    assert o["membros_total"] == 6
    assert o["aplicacao"] == {"application": "Microsoft Office Word", "app_version": "16.0000",
                              "company": "Órgão X", "template": "Normal.dotm", "total_time": 12,
                              "paginas": 3, "palavras": 250, "slides": 3}
    assert o["core"] == {"creator": "Ana", "last_modified_by": "Beto", "created": "2024-03-01T10:00:00Z",
                         "modified": "2024-04-02T11:30:00Z", "title": "Obra de teste", "language": "pt-BR"}
    assert r["aplicacoes_criadoras"] == [{"nome": "Microsoft Office Word", "versao": "16.0000",
                                          "data": "2024-03-01T10:00:00Z", "fonte": "docProps/app.xml"}]
    assert r["lingua_declarada"] == "pt-BR"
    assert r["inibidor"] is None and r["bibliotecas"] == {}


def test_docx_lingua_cai_para_docdefaults_sem_dc_language():
    r = leitor.ler(_docx(lingua_core=None), _ctx("docx"))
    assert r["lingua_declarada"] == "en-US"
    sem_core = leitor.ler(_docx(com_core=False), _ctx("docx"))
    assert sem_core["lingua_declarada"] == "en-US"
    assert "core" in sem_core["lacunas"] and sem_core["ooxml"]["core"]["creator"] is None


def test_docx_sem_lingua_declarada_vira_lacuna():
    r = leitor.ler(_docx(com_core=False, com_styles=False), _ctx("docx"))
    assert r["lingua_declarada"] is None
    assert "lingua_declarada" in r["lacunas"]


def test_docx_sem_styles_usa_so_o_style_id():
    corpo = _p("a", "Heading1") + _p("b", "Ttulo2") + _p("c", "Personalizado") + _p("d")
    r = leitor.ler(_docx(corpo, com_styles=False), _ctx("docx"))
    assert r["ooxml"]["docx"]["titulos_por_nivel"] == {"1": 1, "2": 1}
    assert "estilos_docx" in r["lacunas"]


def test_docx_sem_titulos_estrutura_vazia():
    r = leitor.ler(_docx(_p("so texto") + _p("mais texto")), _ctx("docx"))
    assert r["estrutura_declarada"] == []
    assert r["ooxml"]["docx"]["titulos_por_nivel"] == {} and r["ooxml"]["docx"]["paragrafos_titulo"] == 0


def test_docx_namespace_strict():
    ns = "http://purl.oclc.org/ooxml/wordprocessingml/main"
    r = leitor.ler(_docx(_p("a") + _p("b", "Heading1"), ns=ns), _ctx("docx"))
    assert r["ooxml"]["docx"]["paragrafos"] == 2
    assert r["ooxml"]["docx"]["titulos_por_nivel"] == {"1": 1}


def test_docx_texto_truncado_no_teto(monkeypatch):
    monkeypatch.setattr(leitor, "TETO_TEXTO", 200)
    r = leitor.ler(_grande(50), _ctx("docx"))
    assert len(r["_texto"]) <= 200
    assert r["ooxml"]["docx"]["paragrafos"] == 50
    assert "truncado" in r["lacunas"]["_texto"]


def test_docx_xml_truncado_devolve_parcial():
    membros = {"[Content_Types].xml": _tipos("word/document.xml", CT_DOCX)}
    completo = _documento("".join(_p(f"Paragrafo {i} com texto de enchimento suficiente") for i in range(3000)))
    membros["word/document.xml"] = completo[: len(completo) * 2 // 3]
    r = leitor.ler(_zip(membros), _ctx("docx"))
    assert r["erro"] is None
    assert 0 < r["ooxml"]["docx"]["paragrafos"] < 3000
    assert r["lacunas"]["docx"].startswith("XML malformado")


def test_docx_entidade_xml_recusada():
    corpo = (DECL + '<!DOCTYPE w [<!ENTITY a "bbbb">]>'
             + f'<w:document xmlns:w="{NS_W}"><w:body>{_p("&a;")}</w:body></w:document>')
    membros = {"[Content_Types].xml": _tipos("word/document.xml", CT_DOCX), "word/document.xml": corpo}
    r = leitor.ler(_zip(membros), _ctx("docx"))
    assert r["erro"] is None and r["ooxml"]["docx"] is None
    assert r["lacunas"]["docx"] == "XML com declaracao de entidade"


def test_docx_parte_principal_e_estilos_por_relacao():
    """Sem depender de word/document.xml: a parte vem de _rels/.rels, os estilos de document.xml.rels."""
    rels_doc = (DECL + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="{NS_R}/styles" Target="estilos.xml"/></Relationships>')
    dados = _zip({
        "[Content_Types].xml": _tipos("word/principal.xml", CT_DOCX),
        "_rels/.rels": _rels_raiz("/word/principal.xml", com_props=False),
        "word/principal.xml": _documento(_p("a", "Ttulo1") + _p("b")),
        "word/_rels/principal.xml.rels": rels_doc,
        "word/estilos.xml": _styles("fr-FR"),
    })
    r = leitor.ler(dados, _ctx("docx"))
    assert r["ooxml"]["tipo"] == "docx" and r["ooxml"]["conteudo_tipo"] == CT_DOCX
    assert r["ooxml"]["docx"]["titulos_por_nivel"] == {"1": 1}
    assert r["lingua_declarada"] == "fr-FR"
    assert "estilos_docx" not in r["lacunas"]


def test_docx_sem_relacoes_usa_caminho_padrao_e_content_type_default():
    dados = _zip({
        "[Content_Types].xml": DECL + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                                      '<Default Extension="xml" ContentType="application/xml"/></Types>',
        "word/document.xml": _documento(_p("a") + _p("b", "Heading2")),
    })
    r = leitor.ler(dados, _ctx("docx"))
    assert r["ooxml"]["tipo"] == "docx" and r["ooxml"]["conteudo_tipo"] == "application/xml"
    assert r["ooxml"]["docx"]["paragrafos"] == 2 and r["estrutura_declarada"][0]["entradas"] == 1


# --------------------------------------------------------------------- PPTX

def test_pptx_slides_titulo_notas_e_texto():
    r = leitor.ler(_pptx(), _ctx("pptx"))
    assert r["erro"] is None
    o = r["ooxml"]
    assert o["tipo"] == "pptx" and o["conteudo_tipo"] == CT_PPTX
    assert o["pptx"] == {"slides": 3, "slides_com_titulo": 1, "notas": 1}
    assert o["docx"] is None and o["xlsx"] is None
    assert r["estrutura_declarada"] == []
    # slide 1, 2 e 10 nessa ordem (numerica); corridas do paragrafo se juntam
    assert r["_texto"].split("\n") == ["Título", "Sub", "Segundo slide", "Outra linha", "Terceiro"]
    assert o["aplicacao"]["slides"] == 3
    assert r["aplicacoes_criadoras"][0]["nome"] == "Microsoft Office PowerPoint"
    assert r["lingua_declarada"] == "pt-BR"


# --------------------------------------------------------------------- XLSX

def test_xlsx_planilhas_e_shared_strings():
    r = leitor.ler(_xlsx(), _ctx("xlsx"))
    assert r["erro"] is None
    o = r["ooxml"]
    assert o["tipo"] == "xlsx" and o["conteudo_tipo"] == CT_XLSX
    assert o["xlsx"] == {"planilhas": 2, "nomes": ["Plan1", "Dados"]}
    assert r["_texto"].split("\n") == ["Nome", "Rico texto", "Kanji"]
    assert r["estrutura_declarada"] == []
    assert r["lingua_declarada"] is None and "lingua_declarada" in r["lacunas"]
    assert r["aplicacoes_criadoras"][0]["versao"] == "16.0300"


def test_xlsx_sem_shared_strings_nao_tem_texto():
    r = leitor.ler(_xlsx(com_textos=False), _ctx("xlsx"))
    assert r["_texto"] is None and "_texto" in r["lacunas"]
    assert r["ooxml"]["xlsx"]["planilhas"] == 2


# ------------------------------------------------- pacote, inibidor, falhas

def test_tipo_vem_dos_bytes_nao_do_formato_id():
    assert leitor.ler(_xlsx(), _ctx("docx"))["ooxml"]["tipo"] == "xlsx"
    assert leitor.ler(_docx(), _ctx("txt"))["ooxml"]["tipo"] == "docx"


def test_zip_sem_membros():
    buf = io.BytesIO()
    zipfile.ZipFile(buf, "w").close()
    r = leitor.ler(buf.getvalue(), _ctx("docx"))
    assert r["erro"] is None
    assert r["ooxml"]["membros_total"] == 0 and r["ooxml"]["docx"] is None
    assert r["_texto"] is None and "parte_principal" in r["lacunas"] and "_texto" in r["lacunas"]
    assert r["aplicacoes_criadoras"] == [] and r["inibidor"] is None


def test_zip_invalido_vira_erro_de_uma_linha():
    for lixo in (b"", b"isto nao e um zip\nnem de longe", b"PK" + bytes([3, 4]) + b"truncado"):
        r = leitor.ler(lixo, _ctx("docx"))
        assert set(r) == CHAVES_ENVELOPE
        assert r["erro"].startswith("zip invalido") and "\n" not in r["erro"]
        assert r["ooxml"]["tipo"] == "docx" and r["_texto"] is None


def test_zip_qualquer_sem_parte_principal_nao_e_erro():
    r = leitor.ler(_zip({"a.txt": "oi"}), _ctx("pptx"))
    assert r["erro"] is None and r["ooxml"]["tipo"] == "pptx"
    assert r["ooxml"]["membros_total"] == 1 and "parte_principal" in r["lacunas"]


def test_membro_cifrado_por_flag():
    membros = {
        "[Content_Types].xml": _tipos("word/document.xml", CT_DOCX),
        "_rels/.rels": _rels_raiz("word/document.xml"),
        "word/document.xml": _documento(_p("segredo")),
        "docProps/app.xml": _app(),
    }
    r = leitor.ler(_zip(membros, cifrar=("word/document.xml", "docProps/app.xml")), _ctx("docx"))
    assert r["erro"] is None
    assert r["inibidor"] == {"tipo": "Password protection", "alvo": "2 membros"}
    assert r["ooxml"]["docx"] is None and r["lacunas"]["docx"] == "membro cifrado"
    assert r["_texto"] is None and r["aplicacoes_criadoras"] == []


def test_encrypted_package_no_zip():
    r = leitor.ler(_zip({"EncryptionInfo": bytes([4, 0]), "EncryptedPackage": bytes(16)}), _ctx("docx"))
    assert r["erro"] is None
    assert r["inibidor"] == {"tipo": "Password protection", "alvo": "OOXML cifrado"}


def test_prazo_zero_devolve_parcial_com_lacuna():
    r = leitor.ler(_docx(), _ctx("docx", prazo=0))
    assert r["erro"] is None and "prazo" in r["lacunas"]
    assert r["ooxml"]["docx"] is None and r["ooxml"]["membros_total"] == 6
    assert r["ooxml"]["aplicacao"]["application"] == "Microsoft Office Word"


def test_prazo_estoura_no_meio_do_corpo(monkeypatch):
    chamadas = []

    def estourou(self):
        chamadas.append(1)
        return len(chamadas) > 4   # deixa passar o pacote e os primeiros blocos de leitura

    monkeypatch.setattr(leitor._Prazo, "estourou", estourou)
    r = leitor.ler(_grande(4000), _ctx("docx"))
    assert "prazo" in r["lacunas"]
    assert 0 < r["ooxml"]["docx"]["paragrafos"] < 4000
    assert r["_texto"]


def test_nunca_levanta_excecao():
    for dados, ctx in ((None, _ctx("docx")), (b"PK", None), (123, {}), (_docx(), {"prazo_s": "abc"})):
        r = leitor.ler(dados, ctx)
        assert set(r) == CHAVES_ENVELOPE
    assert leitor.ler(None, _ctx("docx"))["erro"]


def test_envelope_completo_e_deterministico():
    for dados, formato in ((_docx(), "docx"), (_pptx(), "pptx"), (_xlsx(), "xlsx")):
        a, b = leitor.ler(dados, _ctx(formato)), leitor.ler(dados, _ctx(formato))
        assert a == b
        assert set(a) == CHAVES_ENVELOPE
        assert set(a["ooxml"]) == CHAVES_BLOCO
        assert "_texto" not in a["ooxml"] and "_paginas" not in a["ooxml"]
