"""card #3189, ato temporário: testes do leitor de EPUB do censo (EPUBs sintéticos em memória)."""

import codecs
import io
import os
import struct
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "_acervo"))

import censo_epub  # noqa: E402

MIMETYPE = b"application/epub+zip"
NS_OPF = "http://www.idpf.org/2007/opf"
XHTML = "application/xhtml+xml"
ALG_FONTE = "http://www.idpf.org/2008/embedding"
ALG_DRM = "http://ns.adobe.com/adept/enc#aes128-cbc"

CHAVES = {"epub", "aplicacoes_criadoras", "inibidor", "lingua_declarada", "estrutura_declarada",
          "encoding", "_texto", "_paginas", "lacunas", "bibliotecas", "erro"}

NAV = (
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
    "<head><title>Nav</title></head><body>"
    '<nav epub:type="toc"><ol>'
    '<li><a href="c1.xhtml">Um</a><ol>'
    '<li><a href="c1.xhtml#a">Um.um</a><ol hidden="">'
    '<li><a href="c1.xhtml#b">Um.um.um</a></li>'
    '<li hidden=""><a href="c1.xhtml#c">Um.um.dois</a></li>'
    "</ol></li>"
    '<li><a href="c1.xhtml#d">Um.dois</a></li>'
    "</ol></li>"
    '<li hidden=""><a href="c2.xhtml">Dois</a></li>'
    "</ol></nav>"
    '<nav epub:type="page-list" hidden=""><ol><li>1</li><li>2</li><li>3</li></ol></nav>'
    '<nav epub:type="landmarks"><ol><li>a</li><li>b</li></ol></nav>'
    "</body></html>"
)

NCX = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head/>'
    "<docTitle><text>Livro</text></docTitle><navMap>"
    '<navPoint id="n1"><navLabel><text>1</text></navLabel><content src="c1.xhtml"/>'
    '<navPoint id="n11"><navLabel><text>1.1</text></navLabel><content src="c1.xhtml#a"/></navPoint>'
    '<navPoint id="n12"><navLabel><text>1.2</text></navLabel><content src="c1.xhtml#b"/>'
    '<navPoint id="n121"><navLabel><text>1.2.1</text></navLabel><content src="c1.xhtml#c"/></navPoint>'
    "</navPoint></navPoint>"
    '<navPoint id="n2"><navLabel><text>2</text></navLabel><content src="c2.xhtml"/></navPoint>'
    "</navMap>"
    '<pageList><pageTarget id="p1" value="1"><content src="c1.xhtml"/></pageTarget>'
    '<pageTarget id="p2" value="2"><content src="c2.xhtml"/></pageTarget></pageList></ncx>'
)

ITENS = [("nav", "nav.xhtml", XHTML, "nav"), ("c1", "c1.xhtml", XHTML, ""), ("c2", "c2.xhtml", XHTML, "")]
ITENS_2 = [("ncx", "toc.ncx", "application/x-dtbncx+xml", ""), ("c1", "c1.xhtml", XHTML, ""),
           ("c2", "c2.xhtml", XHTML, "")]


def xhtml(corpo, declaracao=""):
    return (declaracao + '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Titulo</title>'
            "<style>p { color: red }</style></head><body>" + corpo
            + "<script>var oculto = 1;</script></body></html>")


def container(caminhos=("OEBPS/content.opf",)):
    raizes = "".join(f'<rootfile full-path="{c}" media-type="application/oebps-package+xml"/>' for c in caminhos)
    return ('<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
            + raizes + "</rootfiles></container>")


def opf(versao="3.0", meta="", itens=ITENS, spine=(("c1", ""), ("c2", "no")), toc=None, unique="uid"):
    manifest = "".join(
        f'<item id="{i}" href="{h}" media-type="{t}"' + (f' properties="{p}"' if p else "") + "/>"
        for i, h, t, p in itens)
    refs = "".join(f'<itemref idref="{i}"' + (f' linear="{lin}"' if lin else "") + "/>" for i, lin in spine)
    atr_toc = f' toc="{toc}"' if toc else ""
    return (f'<?xml version="1.0" encoding="utf-8"?><package xmlns="{NS_OPF}" version="{versao}" '
            f'unique-identifier="{unique}"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:identifier id="uid">urn:uuid:1234</dc:identifier><dc:title>Livro</dc:title>'
            f"<dc:language>pt-BR</dc:language><dc:language>en</dc:language>{meta}</metadata>"
            f"<manifest>{manifest}</manifest><spine{atr_toc}>{refs}</spine></package>")


def arquivos(**kw):
    """Os membros de um EPUB 3 mínimo; `kw` troca o nav, o OPF, o container e os capítulos."""
    return {
        "META-INF/container.xml": kw.get("container", container()),
        "OEBPS/content.opf": kw.get("opf", opf()),
        "OEBPS/nav.xhtml": kw.get("nav", NAV),
        "OEBPS/c1.xhtml": kw.get("c1", xhtml("<h1>Um</h1><p>Texto um.</p>")),
        "OEBPS/c2.xhtml": kw.get("c2", xhtml("<h1>Dois</h1><p>Texto dois.</p>")),
    }


def montar(membros, mimetype="primeiro", comprimido=False, conteudo=MIMETYPE):
    buf = io.BytesIO()
    metodo = zipfile.ZIP_DEFLATED if comprimido else zipfile.ZIP_STORED
    with zipfile.ZipFile(buf, "w") as zf:
        if mimetype == "primeiro":
            zf.writestr("mimetype", conteudo, compress_type=metodo)
        for nome, dados in membros.items():
            zf.writestr(nome, dados, compress_type=zipfile.ZIP_DEFLATED)
        if mimetype == "depois":
            zf.writestr("mimetype", conteudo, compress_type=metodo)
    return buf.getvalue()


def epub(**kw):
    extras = kw.pop("extras", {})
    membros = arquivos(**kw)
    membros.update(extras)
    return montar(membros)


def ler(dados, **ctx):
    base = {"nome_original": "livro.epub", "formato_id": "epub", "bytes": len(dados or b""),
            "prazo_s": 60.0}
    base.update(ctx)
    return censo_epub.ler(dados, base)


def criptografia_xml(*pares):
    itens = "".join(
        f'<EncryptedData xmlns="http://www.w3.org/2001/04/xmlenc#"><EncryptionMethod Algorithm="{alg}"/>'
        f'<CipherData><CipherReference URI="{uri}"/></CipherData></EncryptedData>' for alg, uri in pares)
    return '<?xml version="1.0"?><encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">' + itens + "</encryption>"


def marcar_senha(dados, nome):
    """Liga o bit de criptografia geral do membro no diretório central do zip."""
    b = bytearray(dados)
    marca = b"PK" + bytes([1, 2])
    pos = b.find(marca)
    while pos >= 0:
        tam = struct.unpack("<H", bytes(b[pos + 28:pos + 30]))[0]
        if bytes(b[pos + 46:pos + 46 + tam]).decode() == nome:
            b[pos + 8] |= 1
        pos = b.find(marca, pos + 4)
    return bytes(b)


# ---------- o caso feliz ----------

def test_epub3_conforme_completo():
    r = ler(epub())
    b = r["epub"]
    assert set(r) == CHAVES
    assert r["erro"] is None
    assert b["mimetype_conforme"] == {"conforme": True, "primeiro_membro": "mimetype",
                                      "comprimido": False, "conteudo_exato": True, "bom": False}
    assert b["rootfiles"] == ["OEBPS/content.opf"]
    assert b["rootfiles_total"] == 1
    assert b["versao"] == "3.0"
    assert b["identificador_unico"] == {"ref": "uid", "valor": "urn:uuid:1234", "resolve": True}
    assert b["manifest"] == {"itens": 3}
    assert b["spine"] == {"total": 2, "linear_no": 1}
    assert b["sumario"] == {"fonte": "nav", "entradas": 6, "profundidade": 3, "ramos_hidden": 2,
                            "page_list": 3, "landmarks": 2}
    assert b["criptografia"] == {"encryption_xml": False, "algoritmos": [], "ofuscacao_fonte": False,
                                 "outra_criptografia": False, "rights_xml": False}
    assert b["membros"] == {"total": 6, "xhtml_lidos": 2}
    assert r["estrutura_declarada"] == [{"fonte": "epub_nav", "entradas": 6, "profundidade": 3}]
    assert r["lingua_declarada"] == "pt-BR"
    assert r["inibidor"] is None
    assert r["aplicacoes_criadoras"] == []
    assert r["_paginas"] is None
    assert "_texto" not in b and "_paginas" not in b
    assert r["encoding"] == {"detectado": "utf-8", "confianca": None, "bom": None,
                             "declarado": None, "declarado_bate": None}


def test_versao_e_o_literal_do_pacote():
    assert ler(epub(opf=opf(versao="3.3")))["epub"]["versao"] == "3.3"
    assert ler(epub(opf=opf(versao="3.0")))["epub"]["versao"] == "3.0"


def test_nav_grande_conta_todas_as_entradas():
    itens = "".join(f'<li><a href="c1.xhtml#{i}">Cap {i}</a></li>' for i in range(170))
    nav = NAV.replace("<ol>", "<ol>" + itens, 1)
    r = ler(epub(nav=nav))
    assert r["epub"]["sumario"]["entradas"] == 176
    assert r["epub"]["sumario"]["profundidade"] == 3


def test_ramo_hidden_de_dentro_de_ramo_hidden_conta_uma_vez():
    r = ler(epub())
    assert r["epub"]["sumario"]["ramos_hidden"] == 2


# ---------- sumário: NCX ----------

def test_epub2_le_o_ncx_pelo_spine_toc():
    meta = '<meta name="generator" content="Sigil 0.9.10"/>'
    dados = epub(opf=opf(versao="2.0", meta=meta, itens=ITENS_2, toc="ncx"),
                 extras={"OEBPS/toc.ncx": NCX})
    r = ler(dados)
    assert r["epub"]["versao"] == "2.0"
    assert r["epub"]["sumario"] == {"fonte": "ncx", "entradas": 5, "profundidade": 3,
                                    "ramos_hidden": None, "page_list": 2, "landmarks": None}
    assert r["estrutura_declarada"] == [{"fonte": "epub_ncx", "entradas": 5, "profundidade": 3}]
    assert r["aplicacoes_criadoras"] == [{"nome": "Sigil", "versao": "0.9.10", "data": None,
                                          "fonte": "epub_opf_meta_generator"}]


def test_nav_vale_mesmo_havendo_ncx():
    itens = ITENS + [("ncx", "toc.ncx", "application/x-dtbncx+xml", "")]
    r = ler(epub(opf=opf(itens=itens, toc="ncx"), extras={"OEBPS/toc.ncx": NCX}))
    assert r["epub"]["sumario"]["fonte"] == "nav"
    assert "sumario_nav" not in r["lacunas"]


def test_epub3_sem_nav_cai_no_ncx_com_lacuna():
    itens = [i for i in ITENS if i[0] != "nav"] + [("ncx", "toc.ncx", "application/x-dtbncx+xml", "")]
    r = ler(epub(opf=opf(itens=itens, toc="ncx"), extras={"OEBPS/toc.ncx": NCX}))
    assert r["epub"]["sumario"]["fonte"] == "ncx"
    assert "sumario_nav" in r["lacunas"]


def test_sem_sumario_nenhum_deixa_lacuna():
    itens = [i for i in ITENS if i[0] != "nav"]
    r = ler(epub(opf=opf(itens=itens)))
    assert r["epub"]["sumario"]["fonte"] is None
    assert r["estrutura_declarada"] == []
    assert "sumario" in r["lacunas"]
    assert r["erro"] is None


# ---------- criptografia e inibidor ----------

def test_so_ofuscacao_de_fonte_nao_e_drm():
    enc = criptografia_xml((ALG_FONTE, "OEBPS/f1.otf"), (ALG_FONTE, "OEBPS/f2.otf"))
    r = ler(epub(extras={"META-INF/encryption.xml": enc}))
    assert r["epub"]["criptografia"] == {"encryption_xml": True, "algoritmos": [ALG_FONTE],
                                         "ofuscacao_fonte": True, "outra_criptografia": False,
                                         "rights_xml": False}
    assert r["inibidor"] == {"tipo": "Font obfuscation", "alvo": "2 fontes"}


def test_outro_algoritmo_e_drm_com_alvo():
    enc = criptografia_xml((ALG_FONTE, "OEBPS/f1.otf"), (ALG_DRM, "OEBPS/c1.xhtml"),
                           (ALG_DRM, "OEBPS/c2.xhtml"))
    r = ler(epub(extras={"META-INF/encryption.xml": enc}))
    c = r["epub"]["criptografia"]
    assert c["outra_criptografia"] is True and c["ofuscacao_fonte"] is True
    assert c["algoritmos"] == sorted([ALG_FONTE, ALG_DRM])
    assert r["inibidor"]["tipo"] == "DRM"
    assert ALG_DRM in r["inibidor"]["alvo"] and "OEBPS/c1.xhtml" in r["inibidor"]["alvo"]
    assert ALG_FONTE not in r["inibidor"]["alvo"]


def test_so_rights_xml_e_drm():
    r = ler(epub(extras={"META-INF/rights.xml": "<rights/>"}))
    assert r["epub"]["criptografia"]["rights_xml"] is True
    assert r["epub"]["criptografia"]["encryption_xml"] is False
    assert r["inibidor"] == {"tipo": "DRM", "alvo": "META-INF/rights.xml"}


def test_membro_com_bit_de_senha_e_protecao_por_senha():
    dados = marcar_senha(epub(), "OEBPS/c1.xhtml")
    r = ler(dados)
    assert r["inibidor"] == {"tipo": "Password protection", "alvo": "1 membro(s): OEBPS/c1.xhtml"}
    assert r["erro"] is None
    assert r["epub"]["membros"]["xhtml_lidos"] == 1
    assert "spine" in r["lacunas"]


def test_encryption_xml_ilegivel_fica_none_com_lacuna():
    r = ler(epub(extras={"META-INF/encryption.xml": "isto nao e xml"}))
    c = r["epub"]["criptografia"]
    assert c["encryption_xml"] is True and c["algoritmos"] is None and c["outra_criptografia"] is None
    assert "criptografia" in r["lacunas"]
    assert r["inibidor"] is None


# ---------- rootfiles e mimetype ----------

def test_mais_de_um_rootfile_e_caso():
    cont = container(("OEBPS/content.opf", "OEBPS/outro.opf"))
    r = ler(epub(container=cont))
    assert r["epub"]["rootfiles"] == ["OEBPS/content.opf", "OEBPS/outro.opf"]
    assert r["epub"]["rootfiles_total"] == 2
    assert r["epub"]["versao"] == "3.0"
    assert "rootfiles_demais" in r["lacunas"]


def test_mimetype_fora_de_ordem_e_comprimido():
    dados = montar(arquivos(), mimetype="depois", comprimido=True)
    m = ler(dados)["epub"]["mimetype_conforme"]
    assert m["conforme"] is False
    assert m["primeiro_membro"] == "META-INF/container.xml"
    assert m["comprimido"] is True
    assert m["conteudo_exato"] is True


def test_mimetype_com_bom_ou_com_quebra_de_linha_nao_e_exato():
    com_bom = ler(montar(arquivos(), conteudo=codecs.BOM_UTF8 + MIMETYPE))["epub"]["mimetype_conforme"]
    assert com_bom["bom"] is True and com_bom["conteudo_exato"] is False and com_bom["conforme"] is False
    com_nl = ler(montar(arquivos(), conteudo=MIMETYPE + bytes([10])))["epub"]["mimetype_conforme"]
    assert com_nl["conteudo_exato"] is False and com_nl["bom"] is False and com_nl["conforme"] is False


def test_sem_mimetype_nao_e_conforme():
    m = ler(montar(arquivos(), mimetype="ausente"))["epub"]["mimetype_conforme"]
    assert m["conforme"] is False and m["comprimido"] is None and m["conteudo_exato"] is None


# ---------- entradas ruins: nunca levanta ----------

@pytest.mark.parametrize("dados", [b"", b"isto nao e um zip", None])
def test_dados_vazios_ou_invalidos_voltam_com_erro(dados):
    r = ler(dados)
    assert set(r) == CHAVES
    assert isinstance(r["erro"], str) and r["erro"] and len(r["erro"].splitlines()) == 1
    b = r["epub"]
    assert b["mimetype_conforme"]["conforme"] is None
    assert b["rootfiles"] is None and b["versao"] is None
    assert b["manifest"]["itens"] is None and b["sumario"]["fonte"] is None
    assert r["_texto"] is None and r["encoding"] is None and r["estrutura_declarada"] == []


def test_zip_truncado_volta_com_erro():
    r = ler(epub()[:60])
    assert r["erro"] and r["epub"]["versao"] is None


def test_zip_sem_membros_nao_levanta():
    buf = io.BytesIO()
    zipfile.ZipFile(buf, "w").close()
    r = ler(buf.getvalue())
    assert r["erro"] is None
    assert r["epub"]["mimetype_conforme"]["conforme"] is False
    assert "rootfiles" in r["lacunas"]


def test_container_ausente_e_opf_ilegivel_viram_lacuna():
    sem = arquivos()
    del sem["META-INF/container.xml"]
    r = ler(montar(sem))
    assert r["erro"] is None and r["epub"]["rootfiles"] is None and "rootfiles" in r["lacunas"]
    ruim = ler(epub(opf="isto nao e xml"))
    assert ruim["erro"] is None and ruim["epub"]["versao"] is None
    assert "opf" in ruim["lacunas"] and "sumario" in ruim["lacunas"]
    assert ruim["epub"]["identificador_unico"]["resolve"] is None
    assert ruim["_texto"] is None


def test_ler_nao_levanta_com_ctx_vazio():
    assert censo_epub.ler(epub(), {})["epub"]["versao"] == "3.0"
    assert censo_epub.ler(epub(), None)["erro"] is None


def test_prazo_estourado_devolve_parcial_com_lacuna():
    r = ler(epub(), prazo_s=0)
    assert "prazo" in r["lacunas"]
    assert r["erro"] is None and set(r) == CHAVES


# ---------- identificador, língua, criador ----------

def test_identificador_que_nao_resolve():
    r = ler(epub(opf=opf(unique="outro")))
    assert r["epub"]["identificador_unico"] == {"ref": "outro", "valor": None, "resolve": False}


def test_aplicacoes_criadoras_por_programa_com_data():
    meta = ('<meta property="dcterms:modified">2024-05-01T10:00:00Z</meta>'
            '<meta name="generator" content="calibre (5.44.0)"/>'
            '<meta property="ibooks:generator">InDesign 18.0</meta>'
            '<meta name="generator" content="calibre (5.44.0)"/>')
    r = ler(epub(opf=opf(meta=meta)))
    assert r["aplicacoes_criadoras"] == [
        {"nome": "calibre", "versao": "5.44.0", "data": "2024-05-01T10:00:00Z",
         "fonte": "epub_opf_meta_generator"},
        {"nome": "InDesign", "versao": "18.0", "data": "2024-05-01T10:00:00Z",
         "fonte": "epub_opf_meta_generator"}]


# ---------- caminhos ----------

def test_href_com_percent_e_grafia_divergente():
    itens = [("nav", "nav.xhtml", XHTML, "nav"), ("c1", "cap%C3%ADtulo%201.xhtml", XHTML, ""),
             ("c2", "C2.XHTML", XHTML, "")]
    dados = epub(opf=opf(itens=itens), extras={"OEBPS/capítulo 1.xhtml": xhtml("<p>Com acento.</p>")})
    r = ler(dados)
    assert r["epub"]["membros"]["xhtml_lidos"] == 2
    assert "Com acento." in r["_texto"] and "Texto dois." in r["_texto"]
    assert "caixa" in r["lacunas"] and "OEBPS/C2.XHTML" in r["lacunas"]["caixa"]
    assert "spine" not in r["lacunas"]


def test_item_da_spine_ausente_do_zip_vira_lacuna():
    membros = arquivos()
    del membros["OEBPS/c2.xhtml"]
    r = ler(montar(membros))
    assert r["epub"]["membros"]["xhtml_lidos"] == 1
    assert "c2.xhtml" in r["lacunas"]["spine"]


# ---------- texto ----------

def test_texto_na_ordem_da_spine_sem_script_nem_style():
    dados = epub(opf=opf(spine=(("c2", ""), ("c1", ""))))
    texto = ler(dados)["_texto"]
    assert texto.index("Texto dois.") < texto.index("Texto um.")
    assert "oculto" not in texto and "color" not in texto and "Titulo" not in texto
    assert "Dois" in texto


def test_texto_separa_blocos_e_guarda_espaco_duro():
    corpo = "<p>fim.</p><p>inicio&#160;junto</p>"
    texto = ler(epub(c1=xhtml(corpo)))["_texto"]
    assert "fim." + chr(10) + "inicio" + chr(0xA0) + "junto" in texto


def test_texto_respeita_o_limite(monkeypatch):
    monkeypatch.setattr(censo_epub, "LIMITE_TEXTO", 15)
    r = ler(epub())
    assert len(r["_texto"]) == 15
    assert "_texto" in r["lacunas"]


# ---------- encoding ----------

def test_encoding_declarado_que_bate():
    c1 = xhtml("<p>Ola.</p>", '<?xml version="1.0" encoding="UTF-8"?>')
    r = ler(epub(c1=c1, c2=c1))
    assert r["encoding"]["declarado"] == "utf-8"
    assert r["encoding"]["declarado_bate"] is True


def test_encoding_declarado_que_nao_bate():
    c1 = xhtml("<p>caf" + chr(0xE9) + "</p>", '<?xml version="1.0" encoding="iso-8859-1"?>')
    r = ler(epub(c1=c1.encode("utf-8")))
    assert r["encoding"]["detectado"] == "utf-8"
    assert r["encoding"]["declarado"] == "iso-8859-1"
    assert r["encoding"]["declarado_bate"] is False


def test_encoding_declarado_diferente_com_bytes_so_ascii_bate():
    c1 = xhtml("<p>Ola.</p>", '<?xml version="1.0" encoding="iso-8859-1"?>')
    assert ler(epub(c1=c1))["encoding"]["declarado_bate"] is True


def test_encoding_windows_1252_sem_detector_cai_com_lacuna(monkeypatch):
    monkeypatch.setitem(sys.modules, "charset_normalizer", None)  # import falha
    c = xhtml("<p>caf" + chr(0xE9) + "</p>", '<?xml version="1.0" encoding="windows-1252"?>')
    r = ler(epub(c1=c.encode("windows-1252"), c2=c.encode("windows-1252")))
    assert r["encoding"]["detectado"] == "windows-1252"
    assert r["encoding"]["declarado_bate"] is True
    assert "caf" + chr(0xE9) in r["_texto"]
    assert "ausente" in r["lacunas"]["encoding"]
    assert "charset_normalizer" not in r["bibliotecas"]


def test_encoding_com_charset_normalizer_registra_a_biblioteca():
    pytest.importorskip("charset_normalizer")
    texto = "<p>" + "A tarde caiu, a a" + chr(0xE7) + chr(0xE3) + "o continuou " * 40 + "</p>"
    c = xhtml(texto).encode("windows-1252")
    r = ler(epub(c1=c, c2=c))
    assert "charset_normalizer" in r["bibliotecas"]
    assert isinstance(r["encoding"]["detectado"], str)
    assert r["_texto"]


def test_encoding_mede_30_arquivos_mas_o_texto_vem_de_todos(monkeypatch):
    monkeypatch.setitem(sys.modules, "charset_normalizer", None)
    n = 32
    itens = [("nav", "nav.xhtml", XHTML, "nav")] + [(f"k{i}", f"k{i}.xhtml", XHTML, "") for i in range(n)]
    membros = arquivos(opf=opf(itens=itens, spine=[(f"k{i}", "") for i in range(n)]))
    for i in range(n):
        membros[f"OEBPS/k{i}.xhtml"] = xhtml(f"<p>capitulo {i}</p>")
    membros["OEBPS/k31.xhtml"] = xhtml("<p>caf" + chr(0xE9) + "</p>").encode("windows-1252")
    r = ler(montar(membros))
    assert r["epub"]["membros"]["xhtml_lidos"] == 32
    assert r["encoding"]["detectado"] == "utf-8"
    assert "encoding" not in r["lacunas"]
    assert "caf" + chr(0xE9) in r["_texto"]


def test_encoding_utf16_com_bom():
    decl = '<?xml version="1.0" encoding="utf-16"?>'
    c = codecs.BOM_UTF16_LE + xhtml("<p>ola utf16</p>", decl).encode("utf-16-le")
    r = ler(epub(c1=c, c2=c))
    assert r["encoding"]["detectado"] == "utf-16-le"
    assert r["encoding"]["bom"] == "utf-16-le"
    assert r["encoding"]["declarado_bate"] is True
    assert "ola utf16" in r["_texto"]


def test_encoding_utf8_com_bom():
    c = codecs.BOM_UTF8 + xhtml("<p>com bom</p>").encode("utf-8")
    r = ler(epub(c1=c, c2=c))
    assert r["encoding"]["bom"] == "utf-8" and "com bom" in r["_texto"]


# ---------- determinismo ----------

def test_mesma_entrada_mesma_saida():
    dados = epub(extras={"META-INF/encryption.xml": criptografia_xml((ALG_DRM, "OEBPS/c1.xhtml"))})
    assert ler(dados) == ler(dados)
