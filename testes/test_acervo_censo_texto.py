"""Card #3189, ato temporário: testes do leitor de texto (md, html, txt).

Fixtures sintéticas em memória. O que depende de markdown-it-py ou de
charset-normalizer usa importorskip; o resto roda só com a biblioteca padrão.
"""
import codecs
import os
import sys

import pytest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "_acervo")))

import censo_texto  # noqa: E402

FORM_FEED = chr(12)
CHAVES_ENVELOPE = {
    "texto", "aplicacoes_criadoras", "inibidor", "lingua_declarada", "estrutura_declarada",
    "encoding", "_texto", "_paginas", "lacunas", "bibliotecas", "erro",
}


def ler(dados, formato, **extra):
    ctx = {"nome_original": "x", "formato_id": formato, "bytes": len(dados), "prazo_s": 30.0}
    ctx.update(extra)
    return censo_texto.ler(dados, ctx)


def sem_detector(monkeypatch):
    monkeypatch.setitem(sys.modules, "charset_normalizer", None)


@pytest.fixture
def md_lib():
    return pytest.importorskip("markdown_it")


# ------------------------------------------------------------------ Markdown

def test_md_atx_e_setext_por_nivel(md_lib):
    fonte = "# Um\n\n## Dois\n\n### Tres\n\nSetext um\n==========\n\nSetext dois\n-----------\n"
    r = ler(fonte.encode(), "md")
    md = r["texto"]["md"]
    assert md["cabecalhos_atx"] == {"1": 1, "2": 1, "3": 1, "4": 0, "5": 0, "6": 0}
    assert md["cabecalhos_setext"] == {"1": 1, "2": 1}
    assert md["cabecalhos_html_cru"] == dict.fromkeys("123456", 0)
    assert r["estrutura_declarada"] == [{"fonte": "md_cabecalhos", "entradas": 5, "profundidade": 3}]
    assert "markdown-it-py" in r["bibliotecas"]
    assert r["erro"] is None and r["_paginas"] is None


def test_md_front_matter_nao_vira_setext_h2(md_lib):
    fonte = "---\ntitle: Teste\nlang: pt-BR\n---\n# Titulo\n"
    r = ler(fonte.encode(), "md")
    md = r["texto"]["md"]
    assert md["front_matter"] is True
    assert md["cabecalhos_setext"] == {"1": 0, "2": 0}
    assert md["cabecalhos_atx"]["1"] == 1
    assert r["lingua_declarada"] == "pt-BR"
    assert r["_texto"] == "# Titulo\n"


def test_md_front_matter_toml_e_aspas(md_lib):
    r = ler('+++\ntitle = "x"\nlanguage = "en" # comentario\n+++\n# H\n'.encode(), "md")
    assert r["texto"]["md"]["front_matter"] is True
    assert r["lingua_declarada"] == "en"


def test_md_regua_com_texto_no_meio_nao_e_front_matter(md_lib):
    r = ler("---\nsem chave nenhuma aqui\n---\n# H\n".encode(), "md")
    md = r["texto"]["md"]
    assert md["front_matter"] is False
    assert md["cabecalhos_setext"]["2"] == 1  # é setext de verdade para o CommonMark
    assert r["lingua_declarada"] is None


def test_md_front_matter_precisa_estar_colado_no_topo(md_lib):
    r = ler("\n---\ntitle: x\n---\n# H\n".encode(), "md")
    assert r["texto"]["md"]["front_matter"] is False


def test_md_cerca_nao_conta_cabecalho(md_lib):
    fonte = "```sh\n# comentario de shell\n## outro\n```\n\n~~~\n# x\n~~~\n"
    md = ler(fonte.encode(), "md")["texto"]["md"]
    assert md["cabecalhos_atx"] == dict.fromkeys("123456", 0)
    assert md["cercas"] == 2


def test_md_codigo_recuado(md_lib):
    md = ler("Texto\n\n    codigo recuado\n".encode(), "md")["texto"]["md"]
    assert md["codigo_recuado"] == 1
    assert md["cercas"] == 0


def test_md_h2_em_html_cru_conta_a_parte(md_lib):
    fonte = "<div>\n<h2>Titulo cru</h2>\n<H3 class=x>Outro</H3>\n</div>\n\n<!-- <h4>comentado</h4> -->\n"
    r = ler(fonte.encode(), "md")
    md = r["texto"]["md"]
    assert md["cabecalhos_html_cru"] == {"1": 0, "2": 1, "3": 1, "4": 0, "5": 0, "6": 0}
    assert md["cabecalhos_atx"]["2"] == 0
    assert r["estrutura_declarada"] == [{"fonte": "md_cabecalhos", "entradas": 2, "profundidade": 2}]


def test_md_cabecalho_dentro_de_citacao_e_lista(md_lib):
    md = ler("> ## Na citacao\n\n- # Na lista\n".encode(), "md")["texto"]["md"]
    assert md["cabecalhos_atx"]["2"] == 1
    assert md["cabecalhos_atx"]["1"] == 1


def test_md_tabela_gfm_e_extensao(md_lib):
    fonte = "# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    md = ler(fonte.encode(), "md")["texto"]["md"]
    assert md["tabelas_gfm"] == 1
    assert md["tabelas_gfm_e_extensao"] is True


def test_md_cabecalho_segue_commonmark_puro_mesmo_com_tabela(md_lib):
    # "| a |" + "---" é tabela para o GFM e setext h2 para o CommonMark: cada contagem no seu regime
    md = ler("| a |\n---\n".encode(), "md")["texto"]["md"]
    assert md["cabecalhos_setext"]["2"] == 1
    assert md["tabelas_gfm"] == 1


def test_md_sem_pipe_nao_tem_tabela(md_lib):
    assert ler("# So texto\n".encode(), "md")["texto"]["md"]["tabelas_gfm"] == 0


def test_md_bom_e_crlf(md_lib):
    dados = codecs.BOM_UTF8 + "---\r\nlang: es\r\n---\r\n# Hola\r\n".encode()
    r = ler(dados, "md")
    assert r["encoding"]["bom"] == "utf-8-sig"
    assert r["encoding"]["detectado"] == "utf-8"
    assert r["texto"]["md"]["front_matter"] is True
    assert r["lingua_declarada"] == "es"
    assert r["_texto"].startswith("# Hola")


def test_md_escala_de_um_epub_em_markdown(md_lib):
    fonte = "".join("## Capitulo %d\n\ntexto do capitulo %d\n\n" % (i, i) for i in range(1632))
    r = ler(fonte.encode(), "md")
    assert r["texto"]["md"]["cabecalhos_atx"]["2"] == 1632
    assert r["texto"]["md"]["tokens_total"] == 1632 * 6
    assert r["estrutura_declarada"][0]["entradas"] == 1632


def test_md_sem_biblioteca_fica_sem_contagem(monkeypatch):
    monkeypatch.setitem(sys.modules, "markdown_it", None)
    r = ler("---\nlang: pt\n---\n# H\n".encode(), "md")
    assert r["texto"]["md"] is None
    assert "markdown-it-py ausente" in r["lacunas"]["md"]
    assert r["estrutura_declarada"] == []
    assert r["bibliotecas"] == {}
    assert r["erro"] is None
    assert r["lingua_declarada"] == "pt"
    assert r["_texto"] == "# H\n"


# ------------------------------------------------------------------ HTML

def html_padrao(cabeca="", corpo="<p>x</p>"):
    return "<!DOCTYPE html>\n<html lang=\"pt-BR\"><head>%s<title>  Um   titulo </title></head><body>%s</body></html>" % (
        cabeca, corpo)


def test_html_cabecalhos_titulo_lang_doctype():
    corpo = ("<h1>Um</h1><p>texto</p><h2>Dois</h2><h2>Dois b</h2><H3 id=x>Tres</H3>"
             "<script>var s = '<h4>nao</h4>';</script><style>h5 { }</style><template><h6>nao</h6></template>")
    r = ler(html_padrao(corpo=corpo).encode(), "html")
    html = r["texto"]["html"]
    assert html["h"] == {"1": 1, "2": 2, "3": 1, "4": 0, "5": 0, "6": 0}
    assert html["title"] == "Um titulo"
    assert html["lang"] == "pt-BR" and r["lingua_declarada"] == "pt-BR"
    assert html["doctype"] is True
    assert r["estrutura_declarada"] == [{"fonte": "html_cabecalhos", "entradas": 4, "profundidade": 3}]
    assert r["texto"]["md"] is None and r["texto"]["txt"] is None
    assert "precedencia_html" in r["lacunas"]
    assert r["bibliotecas"] == {}


def test_html_texto_visivel_sem_script_style_template():
    corpo = "<h1>Alfa</h1><p>beta <b>gama</b></p><script>ruido()</script><style>a{}</style><template>oculto</template><p>delta</p>"
    r = ler(html_padrao(corpo=corpo).encode(), "html")
    assert r["_texto"] == "Alfa\nbeta gama\ndelta"


def test_html_titulo_aparado_ate_300():
    r = ler(("<html><head><title>" + "a" * 400 + "</title></head></html>").encode(), "html")
    assert r["texto"]["html"]["title"] == "a" * 300


def test_html_sem_nada_de_html():
    r = ler("texto solto".encode(), "html")
    html = r["texto"]["html"]
    assert html["title"] is None and html["lang"] is None and html["doctype"] is False
    assert r["estrutura_declarada"] == []
    assert r["lingua_declarada"] is None


def test_html_xml_lang_e_declaracao_xml():
    fonte = '<?xml version="1.0" encoding="ISO-8859-1"?><html xmlns="x" xml:lang="fr"><body><p>caf' + "é</p></body></html>"
    r = ler(fonte.encode("latin-1"), "html")
    assert r["lingua_declarada"] == "fr"
    assert r["encoding"]["declarado"] == "iso-8859-1"
    assert r["encoding"]["declarado_bate"] is True
    assert "café" in r["_texto"]


def test_html_meta_charset_na_janela_latin1():
    dados = html_padrao(cabeca='<meta charset="ISO-8859-1">', corpo="<p>ação e informação</p>").encode("latin-1")
    r = ler(dados, "html")
    assert r["_texto"] == "ação e informação"
    assert r["encoding"]["declarado"] == "iso-8859-1"
    assert r["encoding"]["declarado_bate"] is True
    assert r["encoding"]["detectado"] == "iso-8859-1"
    assert r["texto"]["html"]["meta_charset"] == "iso-8859-1"
    assert r["texto"]["html"]["meta_charset_na_janela"] is True


def test_html_meta_charset_fora_da_janela_nao_vale():
    cabeca = "<!-- " + "x" * 1100 + " -->" + '<meta charset="iso-8859-1">'
    dados = html_padrao(cabeca=cabeca, corpo="<p>informação</p>").encode("utf-8")
    r = ler(dados, "html")
    html = r["texto"]["html"]
    assert html["meta_charset"] == "iso-8859-1"          # o parser o viu
    assert html["meta_charset_na_janela"] is False       # mas não vale como declaração
    assert r["encoding"]["declarado"] is None and r["encoding"]["declarado_bate"] is None
    assert r["encoding"]["detectado"] == "utf-8"
    assert r["_texto"] == "informação"


def test_html_meta_comentado_na_janela_nao_conta():
    cabeca = '<!-- <meta charset="iso-8859-1"> -->'
    r = ler(html_padrao(cabeca=cabeca, corpo="<p>informação</p>").encode("utf-8"), "html")
    assert r["encoding"]["declarado"] is None
    assert r["_texto"] == "informação"


def test_html_http_equiv_charset():
    cabeca = '<meta http-equiv="Content-Type" content="text/html; charset=windows-1252">'
    r = ler(html_padrao(cabeca=cabeca, corpo="<p>café</p>").encode("cp1252"), "html")
    assert r["texto"]["html"]["http_equiv_charset"] == "windows-1252"
    assert r["texto"]["html"]["meta_charset"] is None
    assert r["texto"]["html"]["meta_charset_na_janela"] is True
    assert r["encoding"]["declarado"] == "windows-1252"
    assert r["encoding"]["declarado_bate"] is True
    assert r["_texto"] == "café"


def test_html_latin1_declarado_com_bytes_c1_e_cp1252():
    dados = (b'<html><head><meta charset="iso-8859-1"></head><body><p>'
             + bytes([0x93]) + b"aspas" + bytes([0x94]) + b"</p></body></html>")
    r = ler(dados, "html")
    assert r["encoding"]["detectado"] == "windows-1252"
    assert chr(0x201C) + "aspas" + chr(0x201D) in r["_texto"]


def test_html_declara_utf8_mas_bytes_sao_latin1(monkeypatch):
    sem_detector(monkeypatch)
    dados = html_padrao(cabeca='<meta charset="utf-8">', corpo="<p>informação</p>").encode("latin-1")
    r = ler(dados, "html")
    assert r["encoding"]["declarado"] == "utf-8"
    assert r["encoding"]["declarado_bate"] is False
    assert r["encoding"]["detectado"] == "windows-1252"
    assert r["lacunas"]["encoding"] == "sem detector; assumido cp1252"
    assert r["encoding"]["confianca"] is None
    assert r["_texto"] == "informação"


def test_html_declara_latin1_mas_bytes_sao_utf8():
    dados = html_padrao(cabeca='<meta charset="iso-8859-1">', corpo="<p>é</p>").encode("utf-8")
    r = ler(dados, "html")
    assert r["encoding"]["declarado_bate"] is False  # UTF-8 válido com bytes altos contradiz o latin-1


def test_html_declara_utf16_sem_bom_nao_vale():
    dados = html_padrao(cabeca='<meta charset="utf-16">', corpo="<p>é</p>").encode("utf-8")
    r = ler(dados, "html")
    assert r["encoding"]["declarado"] == "utf-16"
    assert r["encoding"]["declarado_bate"] is False
    assert r["encoding"]["detectado"] == "utf-8"
    assert r["_texto"] == "é"


def test_html_charset_desconhecido():
    r = ler(html_padrao(cabeca='<meta charset="klingon">', corpo="<p>é</p>").encode("utf-8"), "html")
    assert r["encoding"]["declarado"] == "klingon"
    assert r["encoding"]["declarado_bate"] is False
    assert "klingon" in r["lacunas"]["charset_declarado"]


def test_html_bom_utf8_vence_o_meta():
    dados = codecs.BOM_UTF8 + html_padrao(cabeca='<meta charset="iso-8859-1">', corpo="<p>é</p>").encode("utf-8")
    r = ler(dados, "html")
    assert r["encoding"]["bom"] == "utf-8-sig"
    assert r["encoding"]["detectado"] == "utf-8"
    assert r["encoding"]["declarado"] == "iso-8859-1"
    assert r["encoding"]["declarado_bate"] is False
    assert r["_texto"] == "é"


def test_html_bom_utf16_le():
    fonte = html_padrao(cabeca='<meta charset="utf-16">', corpo="<p>ação</p>")
    r = ler(codecs.BOM_UTF16_LE + fonte.encode("utf-16-le"), "html")
    assert r["encoding"]["bom"] == "utf-16-le"
    assert r["encoding"]["detectado"] == "utf-16-le"
    assert r["encoding"]["confianca"] == 1.0
    assert r["encoding"]["declarado_bate"] is True
    assert r["texto"]["html"]["meta_charset_na_janela"] is True
    assert r["_texto"] == "ação"


def test_html_bom_utf32_be():
    r = ler(codecs.BOM_UTF32_BE + "<p>olá</p>".encode("utf-32-be"), "html")
    assert r["encoding"]["bom"] == "utf-32-be"
    assert r["_texto"] == "olá"


def test_html_gerador_com_e_sem_versao():
    cabeca = ('<meta name="generator" content="Microsoft Word 15">'
              '<meta name="Generator" content="pandoc">'
              '<meta name="generator" content="Microsoft Word 15">')
    r = ler(html_padrao(cabeca=cabeca).encode(), "html")
    assert r["aplicacoes_criadoras"] == [
        {"nome": "Microsoft Word", "versao": "15", "data": None, "fonte": "meta_generator"},
        {"nome": "pandoc", "versao": None, "data": None, "fonte": "meta_generator"},
    ]


def test_html_grande_em_fatias_conta_tudo():
    corpo = "<h2>x</h2>" * 40000  # passa de varias fatias do parser
    r = ler(html_padrao(corpo=corpo).encode(), "html")
    assert r["texto"]["html"]["h"]["2"] == 40000


def test_html_prazo_estourado_devolve_parcial():
    r = ler(html_padrao(corpo="<h1>a</h1>").encode(), "html", prazo_s=-1.0)
    assert "prazo" in r["lacunas"]
    assert r["texto"]["html"] is None
    assert r["_texto"] is not None
    assert r["erro"] is None


# ------------------------------------------------------------------ codificação (qualquer formato)

def test_ascii_puro():
    r = ler(b"so ascii\n", "txt")
    assert r["encoding"] == {"detectado": "ascii", "confianca": 1.0, "bom": None,
                             "declarado": None, "declarado_bate": None}


def test_utf8_estrito_com_bytes_altos():
    r = ler("ação e coração\n".encode("utf-8"), "txt")
    assert r["encoding"]["detectado"] == "utf-8" and r["encoding"]["confianca"] == 1.0
    assert r["texto"]["decode"] == {"substituicoes": 0, "erro": None}
    assert r["_texto"] == "ação e coração\n"


def test_utf8_remendado_conta_substituicoes():
    dados = ("ação e coração " * 50).encode("utf-8") + bytes([0xFF]) + b" fim"
    r = ler(dados, "txt")
    assert r["encoding"]["detectado"] == "utf-8"
    assert 0.9 < r["encoding"]["confianca"] < 1.0
    assert r["texto"]["decode"]["substituicoes"] == 1
    assert chr(0xFFFD) in r["_texto"]


def test_fffd_que_ja_estava_no_arquivo_nao_e_substituicao():
    r = ler(("ok " + chr(0xFFFD) + " ok ação").encode("utf-8"), "txt")
    assert r["texto"]["decode"]["substituicoes"] == 0
    assert chr(0xFFFD) in r["_texto"]


def test_latin1_sem_declaracao_e_sem_detector_cai_em_cp1252(monkeypatch):
    sem_detector(monkeypatch)
    r = ler("informação técnica\n".encode("latin-1"), "txt")
    assert r["encoding"]["detectado"] == "windows-1252"
    assert r["encoding"]["confianca"] is None
    assert r["lacunas"]["encoding"] == "sem detector; assumido cp1252"
    assert r["_texto"] == "informação técnica\n"
    assert r["bibliotecas"] == {}


def test_cp1252_com_byte_indefinido_conta_substituicao(monkeypatch):
    sem_detector(monkeypatch)
    r = ler(b"a" + bytes([0xE9, 0x81]) + b"b", "txt")
    assert r["texto"]["decode"]["substituicoes"] == 1


def test_latin1_com_detector_real():
    pytest.importorskip("charset_normalizer")
    fonte = ("A Administração Pública direta e indireta obedecerá aos princípios de legalidade, "
             "impessoalidade, moralidade, publicidade e eficiência. Ação civil pública e opinião.\n") * 3
    r = ler(fonte.encode("latin-1"), "txt")
    assert r["encoding"]["detectado"] not in (None, "utf-8", "ascii")
    assert isinstance(r["encoding"]["confianca"], float) and 0.0 <= r["encoding"]["confianca"] <= 1.0
    assert "charset-normalizer" in r["bibliotecas"]
    assert "ção" in r["_texto"]
    assert "encoding" not in r["lacunas"]


def test_utf16_sem_bom():
    r = ler("olá mundo\nsegunda linha\n".encode("utf-16-le"), "txt")
    assert r["encoding"]["detectado"] == "utf-16-le"
    assert r["_texto"] == "olá mundo\nsegunda linha\n"


# ------------------------------------------------------------------ TXT

def test_txt_metricas_crlf_e_form_feed():
    fonte = "aa\r\nbbbb\r\n\r\ncc" + FORM_FEED + "\r\nd\r\n"
    r = ler(fonte.encode(), "txt")
    assert r["texto"]["txt"] == {"linhas": 5, "linhas_vazias": 1, "maior_linha": 4, "linha_media": 2.5,
                                 "form_feed": True, "crlf": True}
    assert r["texto"]["md"] is None and r["texto"]["html"] is None
    assert r["estrutura_declarada"] == []
    assert r["aplicacoes_criadoras"] == []
    assert r["_texto"] == fonte


def test_txt_sem_crlf_sem_form_feed_e_sem_quebra_final():
    txt = ler(b"um\ndois", "txt")["texto"]["txt"]
    assert txt["linhas"] == 2 and txt["crlf"] is False and txt["form_feed"] is False
    assert txt["linha_media"] == 3.0 and txt["maior_linha"] == 4


def test_txt_form_feed_nao_quebra_linha():
    txt = ler(("a" + FORM_FEED + "b\n").encode(), "txt")["texto"]["txt"]
    assert txt["linhas"] == 1 and txt["maior_linha"] == 3


def test_texto_truncado_em_quatro_milhoes():
    r = ler(b"a" * 4_000_001, "txt")
    assert len(r["_texto"]) == 4_000_000
    assert "4000000" in r["lacunas"]["_texto"]
    assert r["texto"]["txt"]["maior_linha"] == 4_000_001


# ------------------------------------------------------------------ envelope e robustez

@pytest.mark.parametrize("formato", ["md", "html", "txt"])
def test_dados_vazios(formato):
    r = ler(b"", formato)
    assert r["erro"] is None
    assert r["_texto"] == ""
    assert r["texto"]["bytes"] == 0 and r["texto"]["formato"] == formato
    assert r["encoding"]["detectado"] is None and r["encoding"]["bom"] is None
    assert "encoding" in r["lacunas"]
    assert r["estrutura_declarada"] == []
    if formato == "txt":
        assert r["texto"]["txt"]["linhas"] == 0


@pytest.mark.parametrize("formato", ["md", "html", "txt"])
def test_envelope_completo(formato):
    r = ler(b"# x\n", formato)
    assert set(r) == CHAVES_ENVELOPE
    assert set(r["texto"]) == {"formato", "bytes", "decode", "md", "html", "txt"}
    assert r["inibidor"] is None and r["_paginas"] is None


@pytest.mark.parametrize("formato", ["md", "html", "txt"])
def test_lixo_binario_nunca_levanta(formato):
    r = ler(bytes(range(256)) * 4, formato)
    assert r["erro"] is None
    assert r["encoding"]["detectado"] is not None


def test_formato_nao_coberto_vira_lacuna_e_nao_erro():
    r = ler(b"%PDF-1.7", "pdf")
    assert r["erro"] is None
    assert "pdf" in r["lacunas"]["formato"]
    assert r["_texto"] is None and r["encoding"] is None


def test_falha_inesperada_volta_em_erro():
    r = censo_texto.ler(None, {"formato_id": "txt", "prazo_s": 5.0})
    assert r["erro"] and "\n" not in r["erro"]
    assert set(r) == CHAVES_ENVELOPE


def test_mesma_entrada_mesma_saida():
    dados = html_padrao(cabeca='<meta charset="utf-8"><meta name="generator" content="X 1.0">', corpo="<h1>a</h1>é").encode()
    assert ler(dados, "html") == ler(dados, "html")
