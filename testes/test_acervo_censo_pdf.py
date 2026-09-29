"""card #3189, ato temporário: testes do leitor de PDF do censo (censo_pdf).

PDFs sintéticos montados aqui: bytes à mão para o que é estrutural (cabeçalho, revisões,
linearização, sumário, estrutura) e pypdf.PdfWriter para texto, fontes e imagens.
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "_acervo"))
import censo_pdf  # noqa: E402

CHAVES_ENVELOPE = {
    "pdf", "aplicacoes_criadoras", "inibidor", "lingua_declarada", "estrutura_declarada", "encoding",
    "_texto", "_paginas", "lacunas", "bibliotecas", "erro",
}
CHAVES_BLOCO = {
    "versao_cabecalho", "cabecalho_offset", "versao_catalogo", "versao_efetiva", "revisoes",
    "paginas_declaradas", "paginas_percorridas", "paginas_analisadas", "criptografado", "linearizado",
    "info", "xmp_presente", "xmp", "criador_vale", "sumario_embutido", "marcado", "suspects",
    "estrutura_presente", "estrutura_tipos", "rotulos_pagina", "anexos", "fontes", "paginas",
    "camada_texto",
}


@pytest.fixture
def pypdf():
    return pytest.importorskip("pypdf")


def ler(dados, prazo_s=60.0):
    ctx = {"nome_original": "x.pdf", "formato_id": "pdf", "bytes": len(dados), "prazo_s": prazo_s}
    return censo_pdf.ler(dados, ctx)


# ---------------------------------------------------------------- montagem à mão

def fluxo(dicionario, dados):
    return "<< {} /Length {} >>\nstream\n".format(dicionario, len(dados)).encode("latin-1") + dados + b"\nendstream"


def documento(texto="Ola", catalogo="", pagina="", raiz_paginas=""):
    """Objetos mínimos: catálogo, páginas, uma página com `BT /F1 12 Tf (texto) Tj ET` e uma fonte."""
    conteudo = "BT /F1 12 Tf 72 700 Td ({}) Tj ET".format(texto).encode("latin-1")
    return {
        1: "<< /Type /Catalog /Pages 2 0 R {} >>".format(catalogo).encode("latin-1"),
        2: "<< /Type /Pages /Kids [3 0 R] /Count 1 {} >>".format(raiz_paginas).encode("latin-1"),
        3: ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> {} >>".format(pagina)).encode("latin-1"),
        4: fluxo("", conteudo),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }


def montar(objetos, cabecalho="%PDF-1.4", prefixo=b"", trailer=""):
    """PDF clássico (xref + trailer) com offsets relativos ao `%PDF-`."""
    corpo = bytearray((cabecalho + "\n").encode("latin-1"))
    posicoes = {}
    for numero in sorted(objetos):
        posicoes[numero] = len(corpo)
        corpo += "{} 0 obj\n".format(numero).encode("latin-1") + objetos[numero] + b"\nendobj\n"
    inicio_xref = len(corpo)
    total = max(posicoes) + 1
    xref = "xref\n0 {}\n0000000000 65535 f \n".format(total)
    for numero in range(1, total):
        xref += "{:010d} 00000 n \n".format(posicoes.get(numero, 0))
    xref += "trailer\n<< /Size {} /Root 1 0 R {} >>\nstartxref\n{}\n%%EOF\n".format(total, trailer, inicio_xref)
    return prefixo + bytes(corpo) + xref.encode("latin-1")


def ultimo_startxref(pdf):
    achado = pdf.rfind(b"startxref")
    return int(pdf[achado:].split()[1])


def atualizar(pdf, objetos, prev=None, trailer_extra=""):
    """Atualização incremental: novos objetos e uma seção xref com /Prev."""
    prev = ultimo_startxref(pdf) if prev is None else prev
    novo = bytearray(pdf)
    posicoes = {}
    for numero in sorted(objetos):
        posicoes[numero] = len(novo)
        novo += "{} 0 obj\n".format(numero).encode("latin-1") + objetos[numero] + b"\nendobj\n"
    inicio_xref = len(novo)
    secao = "xref\n"
    for numero in sorted(posicoes):
        secao += "{} 1\n{:010d} 00000 n \n".format(numero, posicoes[numero])
    secao += "trailer\n<< /Size {} /Root 1 0 R /Prev {} {} >>\nstartxref\n{}\n%%EOF\n".format(
        max(posicoes) + 1, prev, trailer_extra, inicio_xref)
    return bytes(novo) + secao.encode("latin-1")


def entrada_xref_stream(offset):
    return bytes([1]) + offset.to_bytes(3, "big") + bytes([0])


def montar_xref_stream(objetos):
    """PDF 1.5 com xref stream sem filtro. Devolve (bytes, offset do xref stream)."""
    corpo = bytearray(b"%PDF-1.5\n")
    posicoes = {}
    for numero in sorted(objetos):
        posicoes[numero] = len(corpo)
        corpo += "{} 0 obj\n".format(numero).encode("latin-1") + objetos[numero] + b"\nendobj\n"
    numero_xref = max(posicoes) + 1
    inicio = len(corpo)
    posicoes[numero_xref] = inicio
    dados = bytes([0, 0, 0, 0, 255]) + b"".join(entrada_xref_stream(posicoes[n]) for n in range(1, numero_xref + 1))
    dicionario = "/Type /XRef /Size {} /W [1 3 1] /Root 1 0 R".format(numero_xref + 1)
    corpo += "{} 0 obj\n".format(numero_xref).encode("latin-1") + fluxo(dicionario, dados) + b"\nendobj\n"
    corpo += "startxref\n{}\n%%EOF\n".format(inicio).encode("latin-1")
    return bytes(corpo), inicio


def atualizar_xref_stream(pdf, numero, prev):
    """Atualização incremental cujo trailer mora no dicionário de um xref stream."""
    inicio = len(pdf)
    dados = entrada_xref_stream(inicio)
    dicionario = "/Type /XRef /Size {} /W [1 3 1] /Index [{} 1] /Root 1 0 R /Prev {}".format(numero + 1, numero, prev)
    novo = pdf + "{} 0 obj\n".format(numero).encode("latin-1") + fluxo(dicionario, dados) + b"\nendobj\n"
    return novo + "startxref\n{}\n%%EOF\n".format(inicio).encode("latin-1")


# ---------------------------------------------------------------- montagem com pypdf

def escritor_com_paginas(pypdf, paginas, fontes=None, xobjetos=None):
    """PdfWriter novo com uma página por conteúdo (bytes)."""
    return adicionar_paginas(pypdf.PdfWriter(), paginas, fontes, xobjetos)


def adicionar_paginas(escritor, paginas, fontes=None, xobjetos=None):
    """Acrescenta uma página por conteúdo. `fontes`/`xobjetos`: {nome: referência do MESMO escritor}."""
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    for conteudo in paginas:
        pagina = escritor.add_blank_page(612, 792)
        recursos = DictionaryObject()
        if fontes:
            recursos[NameObject("/Font")] = DictionaryObject({NameObject(k): v for k, v in fontes.items()})
        if xobjetos:
            recursos[NameObject("/XObject")] = DictionaryObject({NameObject(k): v for k, v in xobjetos.items()})
        pagina[NameObject("/Resources")] = recursos
        fluxo_conteudo = DecodedStreamObject()
        fluxo_conteudo.set_data(conteudo)
        pagina[NameObject("/Contents")] = escritor._add_object(fluxo_conteudo)
    return escritor


def adicionar_fonte(escritor, **campos):
    from pypdf.generic import DictionaryObject, NameObject

    fonte = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    for chave, valor in campos.items():
        fonte[NameObject("/" + chave)] = valor
    return escritor._add_object(fonte)


def adicionar_imagem(escritor):
    from pypdf.generic import DecodedStreamObject, NameObject, NumberObject

    imagem = DecodedStreamObject()
    imagem.set_data(bytes([0]))
    imagem.update({
        NameObject("/Type"): NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(1),
        NameObject("/Height"): NumberObject(1),
        NameObject("/ColorSpace"): NameObject("/DeviceGray"),
        NameObject("/BitsPerComponent"): NumberObject(8),
    })
    return escritor._add_object(imagem)


def bytes_do(escritor):
    saida = io.BytesIO()
    escritor.write(saida)
    return saida.getvalue()


def pdf_com_paginas(pypdf, conteudos, com_imagem=True, ajustar=None):
    """PDF de uma página por conteúdo, todas com a fonte /F1 (Helvetica) e a imagem /Im0 (1x1)."""
    escritor = pypdf.PdfWriter()
    fontes = {"/F1": adicionar_fonte(escritor)}
    xobjetos = {"/Im0": adicionar_imagem(escritor)} if com_imagem else None
    adicionar_paginas(escritor, conteudos, fontes, xobjetos)
    if ajustar:
        ajustar(escritor)
    return bytes_do(escritor)


def texto_de(n_caracteres, fonte="F1"):
    return "BT /{} 10 Tf 50 700 Td ({}) Tj ET".format(fonte, "x" * n_caracteres).encode("latin-1")


# ---------------------------------------------------------------- envelope e robustez

def test_envelope_tem_todas_as_chaves_e_o_bloco_pdf():
    r = ler(montar(documento()))
    assert set(r) == CHAVES_ENVELOPE
    assert set(r["pdf"]) == CHAVES_BLOCO
    assert r["encoding"] is None


def test_nunca_levanta_com_entradas_estranhas():
    for dados in (b"", b"%PDF-", b"nao e pdf", bytes(range(256)) * 4, b"%PDF-1.4\nlixo"):
        r = ler(dados)
        assert set(r) == CHAVES_ENVELOPE
        assert set(r["pdf"]) == CHAVES_BLOCO


def test_arquivo_vazio_e_texto_puro_dao_erro_de_uma_linha():
    pytest.importorskip("pypdf")
    for dados in (b"", b"nao e pdf nenhum"):
        r = ler(dados)
        assert r["erro"] and "\n" not in r["erro"]
        assert r["pdf"]["paginas_analisadas"] is None
        assert r["_texto"] is None and r["_paginas"] is None


def test_pdf_corrompido_devolve_o_que_os_bytes_dao():
    pytest.importorskip("pypdf")
    r = ler(b"%PDF-1.7\nlixo sem objetos nem xref")
    assert r["erro"] and "\n" not in r["erro"]
    assert r["pdf"]["versao_cabecalho"] == "1.7"
    assert r["pdf"]["cabecalho_offset"] == 0
    assert r["pdf"]["linearizado"] is False
    assert "revisoes" in r["lacunas"]


def test_pdf_truncado_nao_levanta_e_mantem_cabecalho():
    pdf = montar(documento())
    r = ler(pdf[: len(pdf) // 2])
    assert r["pdf"]["versao_cabecalho"] == "1.4"
    assert r["pdf"]["revisoes"] is None
    assert set(r["pdf"]) == CHAVES_BLOCO


def test_sem_pypdf_devolve_os_bytes_e_lacunas(monkeypatch):
    monkeypatch.setattr(censo_pdf, "_importar_pypdf", lambda bibliotecas: None)
    r = ler(montar(documento()))
    assert r["erro"] is None
    assert r["pdf"]["versao_cabecalho"] == "1.4" and r["pdf"]["revisoes"] == 1
    assert r["pdf"]["paginas"] is None and r["pdf"]["fontes"] is None
    assert "pypdf" in r["lacunas"]["paginas"] and r["bibliotecas"] == {}
    assert r["_texto"] is None


def test_determinismo(pypdf):
    pdf = montar(documento("Ola"))
    assert ler(pdf) == ler(pdf)


def test_bibliotecas_registra_pypdf_com_versao(pypdf):
    r = ler(montar(documento()))
    assert r["bibliotecas"]["pypdf"] == pypdf.__version__


# ---------------------------------------------------------------- cabeçalho e versão

def test_cabecalho_no_byte_zero():
    r = ler(montar(documento()))
    assert r["pdf"]["cabecalho_offset"] == 0 and r["pdf"]["versao_cabecalho"] == "1.4"


def test_cabecalho_deslocado_por_lixo_antes_do_pdf(pypdf):
    lixo = b"LIXO DE UM ENVELOPE QUALQUER " * 24   # 696 bytes
    r = ler(montar(documento("Ola"), prefixo=lixo))
    assert r["pdf"]["cabecalho_offset"] == len(lixo)
    assert r["pdf"]["versao_cabecalho"] == "1.4"
    assert r["pdf"]["revisoes"] == 1
    assert r["erro"] is None and r["pdf"]["paginas_percorridas"] == 1
    assert r["_texto"] == "Ola"


def test_cabecalho_alem_dos_1024_bytes_nao_vale():
    r = ler(montar(documento(), prefixo=b"." * 2000))
    assert r["pdf"]["cabecalho_offset"] is None and r["pdf"]["versao_cabecalho"] is None
    assert "versao_cabecalho" in r["lacunas"]


def test_versao_efetiva_e_a_maior_entre_cabecalho_e_catalogo(pypdf):
    r = ler(montar(documento(catalogo="/Version /1.7")))
    assert r["pdf"]["versao_cabecalho"] == "1.4" and r["pdf"]["versao_catalogo"] == "1.7"
    assert r["pdf"]["versao_efetiva"] == "1.7"
    r = ler(montar(documento(catalogo="/Version /1.5"), cabecalho="%PDF-1.7"))
    assert r["pdf"]["versao_efetiva"] == "1.7"
    r = ler(montar(documento(), cabecalho="%PDF-2.0"))
    assert r["pdf"]["versao_efetiva"] == "2.0" and r["pdf"]["versao_catalogo"] is None


# ---------------------------------------------------------------- revisões e linearização

def test_revisoes_uma_sem_atualizacao():
    assert ler(montar(documento()))["pdf"]["revisoes"] == 1


def test_revisoes_seguem_a_cadeia_prev():
    base = montar(documento())
    um = atualizar(base, {6: b"<< /Nota /a >>"})
    dois = atualizar(um, {7: b"<< /Nota /b >>"})
    assert ler(um)["pdf"]["revisoes"] == 2
    assert ler(dois)["pdf"]["revisoes"] == 3


def test_revisoes_com_cabecalho_deslocado():
    base = montar(documento(), prefixo=b"X" * 300)
    r = ler(base)
    assert r["pdf"]["cabecalho_offset"] == 300 and r["pdf"]["revisoes"] == 1


def test_revisoes_ciclo_em_prev_para():
    base = montar(documento())
    sondagem = atualizar(base, {6: b"<< /Nota /a >>"})
    ciclo = atualizar(base, {6: b"<< /Nota /a >>"}, prev=ultimo_startxref(sondagem))   # /Prev = a própria seção
    r = ler(ciclo)
    assert r["pdf"]["revisoes"] == 1
    assert "ciclo" in r["lacunas"]["revisoes"]


def test_revisoes_teto_de_elos(monkeypatch):
    monkeypatch.setattr(censo_pdf, "TETO_ELOS_XREF", 2)
    base = montar(documento())
    tres = atualizar(atualizar(base, {6: b"<< >>"}), {7: b"<< >>"})
    r = ler(tres)
    assert r["pdf"]["revisoes"] == 2 and "teto" in r["lacunas"]["revisoes"]


def test_revisoes_trailer_no_dicionario_do_xref_stream():
    base, inicio = montar_xref_stream(documento())
    assert ler(base)["pdf"]["revisoes"] == 1
    atualizado = atualizar_xref_stream(base, 7, inicio)
    assert ler(atualizado)["pdf"]["revisoes"] == 2


def test_revisoes_sem_startxref_fica_none_com_lacuna():
    r = ler(b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n")
    assert r["pdf"]["revisoes"] is None and r["lacunas"]["revisoes"] == "sem startxref"


def linearizado_minimo(anexo=False):
    """PDF no molde do Anexo F: objeto de linearização, xref da primeira página e xref principal."""
    def montar_com(tamanho):
        objetos = documento()
        corpo = bytearray(b"%PDF-1.4\n")
        lin = "6 0 obj\n<< /Linearized 1 /L {:010d} /H [ 0 0 ] /O 3 /E 9999 /N 1 /T 0 >>\nendobj\n".format(tamanho)
        corpo += lin.encode("latin-1")
        primeiro = len(corpo)
        corpo += b"xref\n6 1\n0000000009 00000 n \ntrailer\n<< /Size 7 /Root 1 0 R /Prev 000000000 >>\nstartxref\n0\n%%EOF\n"
        posicoes = {}
        for numero in sorted(objetos):
            posicoes[numero] = len(corpo)
            corpo += "{} 0 obj\n".format(numero).encode("latin-1") + objetos[numero] + b"\nendobj\n"
        principal = len(corpo)
        xref = "xref\n0 6\n0000000000 65535 f \n"
        for numero in range(1, 6):
            xref += "{:010d} 00000 n \n".format(posicoes[numero])
        xref += "trailer\n<< /Size 6 >>\nstartxref\n{}\n%%EOF\n".format(primeiro)
        corpo += xref.encode("latin-1")
        dados = bytes(corpo).replace(b"/Prev 000000000", "/Prev {:09d}".format(principal).encode("latin-1"))
        return dados

    dados = montar_com(0)
    dados = montar_com(len(dados))
    return atualizar(dados, {7: b"<< /Nota /a >>"}) if anexo else dados


def test_linearizado_com_l_igual_ao_tamanho_e_uma_revisao():
    dados = linearizado_minimo()
    r = ler(dados)
    assert r["pdf"]["linearizado"] is True
    assert r["pdf"]["revisoes"] == 1   # primeira página + principal formam uma revisão só


def test_linearizado_perde_o_titulo_se_o_arquivo_cresceu():
    r = ler(linearizado_minimo(anexo=True))
    assert r["pdf"]["linearizado"] is False
    assert r["pdf"]["revisoes"] == 2


def test_nao_linearizado_sem_o_marcador():
    assert ler(montar(documento()))["pdf"]["linearizado"] is False


def test_linearizado_exige_l_igual_ao_tamanho():
    dados = linearizado_minimo().replace(b"/L 00", b"/L 99", 1)
    assert ler(dados)["pdf"]["linearizado"] is False


# ---------------------------------------------------------------- páginas

def test_texto_paginas_e_versao_da_pagina_unica(pypdf):
    r = ler(montar(documento("Ola")))
    pdf = r["pdf"]
    assert pdf["paginas_declaradas"] == 1 and pdf["paginas_percorridas"] == 1 and pdf["paginas_analisadas"] == 1
    assert r["_texto"] == "Ola" and r["_paginas"] == ["Ola"]
    assert pdf["paginas"]["caracteres"]["total"] == 3


def test_count_diferente_das_paginas_percorridas(pypdf):
    objetos = documento()
    objetos[2] = b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 5 >>"
    objetos[6] = objetos[3]
    r = ler(montar(objetos))
    assert r["pdf"]["paginas_declaradas"] == 5 and r["pdf"]["paginas_percorridas"] == 2
    assert r["pdf"]["paginas_analisadas"] == 2


def test_kids_com_ciclo_nao_trava(pypdf):
    objetos = documento()
    objetos[2] = b"<< /Type /Pages /Kids [3 0 R 2 0 R] /Count 1 >>"
    r = ler(montar(objetos))
    assert r["pdf"]["paginas_percorridas"] == 1
    assert "paginas_percorridas" in r["lacunas"]


def test_recursos_herdados_do_no_de_paginas(pypdf):
    objetos = documento(pagina="")
    objetos[3] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>"
    objetos[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 /Resources << /Font << /F1 5 0 R >> >> >>"
    assert ler(montar(objetos))["_texto"] == "Ola"


def test_lingua_declarada_do_catalogo(pypdf):
    r = ler(montar(documento(catalogo="/Lang (pt-BR)")))
    assert r["lingua_declarada"] == "pt-BR"


def test_rotulos_e_anexos(pypdf):
    objetos = documento(catalogo=("/PageLabels << /Nums [0 << /S /D >>] >> /AF [8 0 R 9 0 R] "
                                  "/Names << /EmbeddedFiles 6 0 R >>"))
    objetos[6] = b"<< /Kids [7 0 R] >>"
    objetos[7] = b"<< /Names [(a.txt) 8 0 R (b.txt) 9 0 R (c.txt) 8 0 R] >>"
    objetos[8] = b"<< /Type /Filespec /F (a.txt) >>"
    objetos[9] = b"<< /Type /Filespec /F (b.txt) >>"
    pdf = ler(montar(objetos))["pdf"]
    assert pdf["rotulos_pagina"] is True
    assert pdf["anexos"] == {"embeddedfiles": 3, "af": 2}
    assert ler(montar(documento()))["pdf"]["rotulos_pagina"] is False


# ---------------------------------------------------------------- sumário embutido

def objetos_com_sumario(proximo_do_ultimo=""):
    objetos = documento(catalogo="/Outlines 6 0 R")
    objetos[6] = b"<< /Type /Outlines /First 7 0 R /Last 10 0 R /Count 4 >>"
    objetos[7] = b"<< /Title (A) /Parent 6 0 R /First 8 0 R /Last 8 0 R /Count -2 /Next 10 0 R >>"
    objetos[8] = b"<< /Title (A1) /Parent 7 0 R /First 9 0 R /Last 9 0 R /Count -1 >>"
    objetos[9] = b"<< /Title (A1a) /Parent 8 0 R >>"
    objetos[10] = "<< /Title (B) /Parent 6 0 R /Prev 7 0 R {} >>".format(proximo_do_ultimo).encode("latin-1")
    return objetos


def test_sumario_embutido_conta_por_first_e_next_mesmo_fechado(pypdf):
    r = ler(montar(objetos_com_sumario()))
    assert r["pdf"]["sumario_embutido"] == {"entradas": 4, "profundidade": 3}
    assert r["estrutura_declarada"] == [{"fonte": "pdf_outline", "entradas": 4, "profundidade": 3}]
    assert "sumario_embutido" not in r["lacunas"]


def test_sumario_com_ciclo_para_e_avisa(pypdf):
    r = ler(montar(objetos_com_sumario("/Next 7 0 R")))
    assert r["pdf"]["sumario_embutido"]["entradas"] == 4
    assert "ciclo" in r["lacunas"]["sumario_embutido"]


def test_sumario_ausente_e_vazio(pypdf):
    assert ler(montar(documento()))["pdf"]["sumario_embutido"] is None
    objetos = documento(catalogo="/Outlines 6 0 R")
    objetos[6] = b"<< /Type /Outlines /Count 0 >>"
    r = ler(montar(objetos))
    assert r["pdf"]["sumario_embutido"] == {"entradas": 0, "profundidade": 0}
    assert r["estrutura_declarada"] == []


def test_sumario_por_pypdf_writer_aninhado(pypdf):
    escritor = escritor_com_paginas(pypdf, [texto_de(5)] * 3, None)
    pai = escritor.add_outline_item("Capitulo", 0)
    filho = escritor.add_outline_item("Secao", 1, parent=pai)
    escritor.add_outline_item("Subsecao", 2, parent=filho)
    escritor.add_outline_item("Outro", 2)
    r = ler(bytes_do(escritor))
    assert r["pdf"]["sumario_embutido"] == {"entradas": 4, "profundidade": 3}


# ---------------------------------------------------------------- marcação e estrutura

def objetos_marcados(marcado=True):
    catalogo = "/StructTreeRoot 6 0 R"
    if marcado:
        catalogo += " /MarkInfo << /Marked true /Suspects true >>"
    objetos = documento(catalogo=catalogo)
    objetos[6] = (b"<< /Type /StructTreeRoot /K [7 0 R 8 0 R 9 0 R 10 0 R 11 0 R 12 0 R] "
                  b"/RoleMap << /Cabecalho /H1 /Paragrafo /P /Ciclo1 /Ciclo2 /Ciclo2 /Ciclo1 /Titulo /Cabecalho >> >>")
    objetos[7] = b"<< /Type /StructElem /S /H1 /P 6 0 R /K [13 0 R] >>"
    objetos[8] = b"<< /Type /StructElem /S /Cabecalho /P 6 0 R /K 0 >>"
    objetos[9] = b"<< /Type /StructElem /S /Paragrafo /P 6 0 R /K 1 >>"
    objetos[10] = b"<< /Type /StructElem /S /Ciclo1 /P 6 0 R /K 2 >>"
    objetos[11] = b"<< /Type /StructElem /S /H3 /P 6 0 R /K 3 >>"
    objetos[12] = b"<< /Type /StructElem /S /Titulo /P 6 0 R /K [<< /Type /MCR /Pg 3 0 R /MCID 0 >>] >>"
    objetos[13] = b"<< /Type /StructElem /S /Table /P 7 0 R /K [<< /Type /OBJR /Obj 3 0 R >>] >>"
    return objetos


def test_estrutura_resolve_rolemap_e_conta_tipos(pypdf):
    r = ler(montar(objetos_marcados()))
    pdf = r["pdf"]
    assert pdf["marcado"] is True and pdf["suspects"] is True and pdf["estrutura_presente"] is True
    tipos = pdf["estrutura_tipos"]
    assert tipos["H1"] == 3          # H1 direto, Cabecalho->H1 e Titulo->Cabecalho->H1
    assert tipos["H3"] == 1 and tipos["P"] == 1 and tipos["Table"] == 1
    assert tipos["H"] == 0 and tipos["Figure"] == 0 and tipos["TOC"] == 0 and tipos["Title"] == 0
    assert set(tipos) == {"H", "H1", "H2", "H3", "H4", "H5", "H6", "Title", "P", "Table", "Figure", "TOC"}
    assert {"fonte": "pdf_estrutura_h", "entradas": 4, "profundidade": 3} in r["estrutura_declarada"]


def test_struct_tree_root_sozinho_nao_marca_o_pdf(pypdf):
    pdf = ler(montar(objetos_marcados(marcado=False)))["pdf"]
    assert pdf["estrutura_presente"] is True and pdf["marcado"] is False and pdf["suspects"] is False


def test_sem_estrutura_tipos_none(pypdf):
    pdf = ler(montar(documento()))["pdf"]
    assert pdf["estrutura_presente"] is False and pdf["estrutura_tipos"] is None and pdf["marcado"] is False


def test_estrutura_teto_de_nos_deixa_lacuna(pypdf, monkeypatch):
    monkeypatch.setattr(censo_pdf, "TETO_NOS_ESTRUTURA", 3)
    r = ler(montar(objetos_marcados()))
    assert "teto" in r["lacunas"]["estrutura_tipos"]
    assert r["pdf"]["estrutura_tipos"] is not None


def test_marcado_com_fontes_sem_mapeamento(pypdf):
    objetos = objetos_marcados()
    objetos[5] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> "
                  b"/Encoding << /Differences [1 /g1 /g2] >> >>")
    objetos[4] = fluxo("", b"BT /F1 12 Tf 72 700 Td (" + bytes([1, 2, 1]) + b") Tj ET")
    r = ler(montar(objetos))
    assert r["pdf"]["camada_texto"]["marcado_com_fontes_sem_mapeamento"] is True
    assert r["pdf"]["fontes"]["sem_caminho"] == 1


# ---------------------------------------------------------------- Info, XMP e criador

def xmp(produtor="Acrobat Distiller 9.0.0", ferramenta="Microsoft Word 2016",
        criado="2020-01-02T03:04:05+01:00", modificado="2020-01-03T00:00:00Z"):
    texto = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:pdf="http://ns.adobe.com/pdf/1.3/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/" pdf:Producer="{}">'
        "<xmp:CreatorTool>{}</xmp:CreatorTool><xmp:CreateDate>{}</xmp:CreateDate>"
        "<xmp:ModifyDate>{}</xmp:ModifyDate></rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    ).format(produtor, ferramenta, criado, modificado)
    return texto.encode("utf-8")


def com_info_e_xmp(info, carga_xmp=None):
    objetos = documento(catalogo="/Metadata 7 0 R" if carga_xmp else "")
    objetos[6] = "<< {} >>".format(info).encode("latin-1")
    if carga_xmp:
        objetos[7] = fluxo("/Type /Metadata /Subtype /XML", carga_xmp)
    return montar(objetos, trailer="/Info 6 0 R")


def test_info_e_xmp_lidos_sem_divergencia_valendo_o_xmp(pypdf):
    info = "/Producer (Acrobat Distiller 9.0.0) /Creator (Microsoft Word 2016) /CreationDate (D:20200102030405+01'00')"
    r = ler(com_info_e_xmp(info, xmp()))
    pdf = r["pdf"]
    assert pdf["info"]["producer"] == "Acrobat Distiller 9.0.0"
    assert pdf["info"]["creation_date"] == "D:20200102030405+01'00'"
    assert pdf["xmp_presente"] is True
    assert pdf["xmp"] == {"pdf_producer": "Acrobat Distiller 9.0.0", "xmp_creator_tool": "Microsoft Word 2016",
                          "xmp_create_date": "2020-01-02T03:04:05+01:00",
                          "xmp_modify_date": "2020-01-03T00:00:00Z"}
    assert pdf["criador_vale"] == "xmp"
    nomes = [(a["nome"], a["versao"], a["data"]) for a in r["aplicacoes_criadoras"]]
    assert nomes == [("Acrobat Distiller", "9.0.0", "2020-01-02T03:04:05+01:00"),
                     ("Microsoft Word 2016", None, "2020-01-02T03:04:05+01:00")]
    assert r["aplicacoes_criadoras"][0]["fonte"] == "xmp_pdf_producer,pdf_info_producer"


def test_divergencia_vale_o_xmp_salvo_moddate_do_info_mais_recente(pypdf):
    velho = "/Producer (LibreOffice 7.3) /ModDate (D:20191231000000Z)"
    novo = "/Producer (LibreOffice 7.3) /ModDate (D:20200105000000Z)"
    r_velho = ler(com_info_e_xmp(velho, xmp()))
    r_novo = ler(com_info_e_xmp(novo, xmp()))
    assert r_velho["pdf"]["criador_vale"] == "xmp"
    assert r_novo["pdf"]["criador_vale"] == "info"
    assert r_novo["aplicacoes_criadoras"][0]["nome"] == "LibreOffice"
    assert r_novo["aplicacoes_criadoras"][0]["versao"] == "7.3"
    assert r_velho["aplicacoes_criadoras"][0]["nome"] == "Acrobat Distiller"


def test_so_info_ou_so_xmp_ou_nenhum(pypdf):
    assert ler(com_info_e_xmp("/Producer (pdfTeX-1.40.21)"))["pdf"]["criador_vale"] == "info"
    r = ler(com_info_e_xmp("/Title (x)", xmp()))
    assert r["pdf"]["criador_vale"] == "xmp"
    r = ler(com_info_e_xmp("/Title (x)"))
    assert r["pdf"]["criador_vale"] is None and r["aplicacoes_criadoras"] == []
    assert ler(com_info_e_xmp("/Producer (pdfTeX-1.40.21)"))["aplicacoes_criadoras"][0]["versao"] == "1.40.21"


def test_xmp_com_doctype_e_recusado_e_xmp_quebrado_vira_lacuna(pypdf):
    r = ler(com_info_e_xmp("/Title (x)", b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY b "c">]><a>&b;</a>'))
    assert r["pdf"]["xmp_presente"] is True and r["pdf"]["xmp"] is None
    assert "DOCTYPE" in r["lacunas"]["xmp"]
    r = ler(com_info_e_xmp("/Title (x)", b"<x:xmpmeta"))
    assert r["pdf"]["xmp_presente"] is True and r["pdf"]["xmp"] is None and "xmp" in r["lacunas"]


def test_data_iso_tolera_formatos_do_pdf():
    assert censo_pdf._data_iso("D:20240102030405+01'00'") == "2024-01-02T03:04:05+01:00"
    assert censo_pdf._data_iso("D:20240102030405Z") == "2024-01-02T03:04:05Z"
    assert censo_pdf._data_iso("D:20240102030405-03'30'") == "2024-01-02T03:04:05-03:30"
    assert censo_pdf._data_iso("D:20240102") == "2024-01-02"
    assert censo_pdf._data_iso("D:2024") == "2024"
    assert censo_pdf._data_iso("20240102030405") == "2024-01-02T03:04:05"
    assert censo_pdf._data_iso("D:20241302") == "2024"
    assert censo_pdf._data_iso("2020-01-02T03:04:05+01:00") == "2020-01-02T03:04:05+01:00"
    assert censo_pdf._data_iso("2020-01-02") == "2020-01-02"
    assert censo_pdf._data_iso("ontem") is None
    assert censo_pdf._data_iso(None) is None


def test_nome_versao_separa_quando_ha_versao_reconhecivel():
    assert censo_pdf._nome_versao("Adobe PDF Library 15.0") == ("Adobe PDF Library", "15.0")
    assert censo_pdf._nome_versao("Skia/PDF/1.2.3") == ("Skia/PDF", "1.2.3")
    assert censo_pdf._nome_versao("pdfTeX-1.40.21") == ("pdfTeX", "1.40.21")
    assert censo_pdf._nome_versao("Microsoft: Print To PDF") == ("Microsoft: Print To PDF", None)
    assert censo_pdf._nome_versao("Word 2016") == ("Word 2016", None)
    assert censo_pdf._nome_versao("1.2.3") == ("1.2.3", None)


# ---------------------------------------------------------------- critério de OCR e imagem

def test_tres_paginas_611_caracteres_com_carimbo_nao_caem_no_ocr(pypdf):
    conteudos = [texto_de(n) + b" q 40 0 0 40 500 20 cm /Im0 Do Q" for n in (204, 204, 203)]
    r = ler(pdf_com_paginas(pypdf, conteudos))
    paginas = r["pdf"]["paginas"]
    assert paginas["caracteres"]["total"] == 611
    assert paginas["ocr"] == {"paginas": [], "paginas_total": 0}
    assert paginas["imagem_area"]["paginas_gt50_total"] == 0
    assert paginas["imagem_area"]["max"] < 0.01
    assert r["pdf"]["camada_texto"]["paginas_ocr"] == 0


def test_pagina_de_imagem_cheia_com_pouco_texto_cai_no_ocr(pypdf):
    conteudos = [
        texto_de(200) + b" q 612 0 0 792 0 0 cm /Im0 Do Q",     # ocr
        texto_de(600) + b" q 612 0 0 792 0 0 cm /Im0 Do Q",     # imagem cheia, mas com texto de sobra
        texto_de(10),                                           # texto pouco, sem imagem
        b"q 612 0 0 792 0 0 cm /Im0 Do Q",                      # sem texto nenhum
    ]
    r = ler(pdf_com_paginas(pypdf, conteudos))
    paginas = r["pdf"]["paginas"]
    assert paginas["ocr"]["paginas"] == [1, 4]
    assert paginas["imagem_area"]["paginas_gt50"] == [1, 2, 4]
    assert paginas["sem_texto"]["paginas"] == [4]
    assert paginas["imagem_area"]["max"] == 1.0
    assert r["pdf"]["camada_texto"]["paginas_ocr"] == 2


def test_area_de_imagem_pela_ctm_com_q_rotacao_e_teto(pypdf):
    conteudos = [
        b"q 306 0 0 396 0 0 cm /Im0 Do Q",                              # um quarto da página
        b"q 0 396 -306 0 306 0 cm /Im0 Do Q",                           # girada, mesma área
        b"q 0.5 0 0 0.5 0 0 cm Q q 306 0 0 396 0 0 cm /Im0 Do Q",       # o Q restaura a CTM
        b"q 612 0 0 792 0 0 cm /Im0 Do /Im0 Do Q",                      # duas vezes a página: teto 1.0
    ]
    imagem = ler(pdf_com_paginas(pypdf, conteudos))["pdf"]["paginas"]["imagem_area"]
    assert imagem["mediana"] == 0.25 and imagem["max"] == 1.0
    assert imagem["paginas_gt50"] == [4]


def test_imagem_e_texto_dentro_de_form_xobject(pypdf):
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject)

    escritor = pypdf.PdfWriter()
    fonte = adicionar_fonte(escritor)
    imagem = adicionar_imagem(escritor)
    forma = DecodedStreamObject()
    forma.set_data(b"BT /F1 10 Tf 10 10 Td (dentro) Tj ET q 100 0 0 100 0 0 cm /Im0 Do Q")
    forma.update({
        NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Form"),
        NameObject("/BBox"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(100), FloatObject(100)]),
        NameObject("/Matrix"): ArrayObject([FloatObject(3), FloatObject(0), FloatObject(0), FloatObject(3),
                                            FloatObject(0), FloatObject(0)]),
        NameObject("/Resources"): DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): fonte}),
            NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): imagem}),
        }),
    })
    referencia = escritor._add_object(forma)
    adicionar_paginas(escritor, [b"/Fm0 Do"], None, {"/Fm0": referencia})
    r = ler(bytes_do(escritor))
    assert "dentro" in r["_texto"]
    # imagem 100x100 sob a matriz 3x do Form: 90000 pt2 de 484704 pt2 da página
    assert r["pdf"]["paginas"]["imagem_area"]["max"] == pytest.approx(90000 / (612 * 792), abs=1e-4)
    assert r["pdf"]["fontes"] == {"total": 1, "sem_tounicode": 1, "sem_caminho": 0, "type3": 0}


def test_userunit_nao_altera_a_razao_area_da_imagem_sobre_area_da_pagina(pypdf):
    def com_userunit(escritor):
        from pypdf.generic import FloatObject, NameObject

        escritor.pages[0][NameObject("/UserUnit")] = FloatObject(2.0)

    dados = pdf_com_paginas(pypdf, [b"q 306 0 0 396 0 0 cm /Im0 Do Q"], ajustar=com_userunit)
    assert ler(dados)["pdf"]["paginas"]["imagem_area"]["max"] == pytest.approx(0.25, abs=1e-4)


def test_imagem_inline_conta_area(pypdf):
    conteudo = b"q 612 0 0 792 0 0 cm BI /W 1 /H 1 /CS /G /BPC 8 ID " + bytes([0]) + b" EI Q"
    r = ler(pdf_com_paginas(pypdf, [conteudo]))
    assert r["pdf"]["paginas"]["imagem_area"]["max"] == 1.0


def test_texto_invisivel_modo_3(pypdf):
    conteudos = [b"BT /F1 10 Tf 3 Tr (oculto) Tj ET", b"BT /F1 10 Tf 3 Tr 0 Tr (visivel) Tj ET",
                 b"q BT /F1 10 Tf 3 Tr ET Q BT /F1 10 Tf (visivel) Tj ET"]
    r = ler(pdf_com_paginas(pypdf, conteudos))
    assert r["pdf"]["paginas"]["texto_invisivel"] == {"paginas": [1], "paginas_total": 1}


def test_lista_de_paginas_tem_teto_e_total():
    lista, total = censo_pdf._lista_teto(list(range(1, 2501)))
    assert len(lista) == 2000 and total == 2500 and lista[0] == 1


# ---------------------------------------------------------------- fontes e glifos sem caminho

@pytest.mark.parametrize("nome, esperado", [
    ("g123", False), ("cid00123", False), ("glyph45", False), ("G2A", False), ("C0021", False),
    ("/g123", False), (".notdef", False), ("", False),
    ("A", True), ("z", True), ("7", True), ("space", True), ("eacute", True), ("fi", True), ("endash", True),
    ("uni00E9", True), ("uni00410042", True), ("u1F600", True), ("f_i", True), ("a.sc", True),
    ("/quotesingle", True), ("bullet", True),
])
def test_nome_agl_aproximado(nome, esperado):
    assert censo_pdf._nome_agl(nome) is esperado


def pdf_de_uma_fonte(objeto_fonte, codigos, catalogo=""):
    objetos = documento(catalogo=catalogo)
    objetos[5] = objeto_fonte
    objetos[4] = fluxo("", b"BT /F1 12 Tf 72 700 Td (" + codigos + b") Tj ET")
    return montar(objetos)


def test_fonte_sem_tounicode_com_nomes_g123_nao_tem_caminho(pypdf):
    fonte = (b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> "
             b"/Encoding << /Type /Encoding /Differences [1 /g123 /g124 /g125] >> >>")
    r = ler(pdf_de_uma_fonte(fonte, bytes([1, 2, 3, 1, 2])))
    pdf = r["pdf"]
    assert pdf["fontes"] == {"total": 1, "sem_tounicode": 1, "sem_caminho": 1, "type3": 0}
    glifos = pdf["paginas"]["glifos_sem_caminho"]
    assert glifos["total"] == 5 and glifos["paginas_gt20"] == [1] and glifos["paginas_gt20_total"] == 1
    assert pdf["camada_texto"]["paginas_glifos_sem_caminho_gt20"] == 1
    assert pdf["camada_texto"]["marcado_com_fontes_sem_mapeamento"] is False   # não é PDF marcado


def test_fonte_com_tounicode_ou_winansi_ou_nomes_da_agl_tem_caminho(pypdf):
    casos = [
        b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> /ToUnicode 6 0 R "
        b"/Encoding << /Differences [1 /g123] >> >>",
        b"<< /Type /Font /Subtype /TrueType /BaseFont /Arial /Encoding /WinAnsiEncoding "
        b"/FontDescriptor << /Flags 4 >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> "
        b"/Encoding << /BaseEncoding /WinAnsiEncoding /Differences [1 /eacute /uni20AC /fi] >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> "
        b"/Encoding << /Differences [1 /Gamma /fi /uni0041] >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 32 >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for fonte in casos:
        objetos = documento()
        objetos[5] = fonte
        objetos[6] = fluxo("", b"BT")
        objetos[4] = fluxo("", b"BT /F1 12 Tf (" + bytes([1, 2, 3]) + b") Tj ET")
        r = ler(montar(objetos))
        assert r["pdf"]["fontes"]["sem_caminho"] == 0, fonte
        assert r["pdf"]["paginas"]["glifos_sem_caminho"]["total"] == 0, fonte


def test_fonte_simbolica_sem_encoding_e_base_desconhecida_nao_tem_caminho(pypdf):
    casos = [
        b"<< /Type /Font /Subtype /TrueType /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> "
        b"/Encoding << /Differences [1 /a /g5] >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+Sub /FontDescriptor << /Flags 4 >> "
        b"/Encoding /Identity-H >>",
    ]
    for fonte in casos:
        r = ler(pdf_de_uma_fonte(fonte, b"abc"))
        assert r["pdf"]["fontes"]["sem_caminho"] == 1, fonte


def test_type0_identity_sem_tounicode_nao_tem_caminho_e_cmap_predefinido_tem(pypdf):
    identity = (b"<< /Type /Font /Subtype /Type0 /BaseFont /ABCDEF+Sub /Encoding /Identity-H "
                b"/DescendantFonts [<< /Type /Font /Subtype /CIDFontType2 /BaseFont /ABCDEF+Sub "
                b"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> >>] >>")
    predefinido = identity.replace(b"/Identity-H", b"/UniJIS-UCS2-H")
    japones = identity.replace(b"(Identity)", b"(Japan1)")
    r = ler(pdf_de_uma_fonte(identity, bytes([0, 1, 0, 2])))
    assert r["pdf"]["fontes"]["sem_caminho"] == 1
    assert r["pdf"]["paginas"]["glifos_sem_caminho"]["total"] == 2      # dois códigos de dois bytes
    for fonte in (predefinido, japones):
        assert ler(pdf_de_uma_fonte(fonte, bytes([0, 1])))["pdf"]["fontes"]["sem_caminho"] == 0


def test_type3_conta_a_parte_e_nao_entra_em_sem_caminho(pypdf):
    fonte = (b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 10 10] /FontMatrix [0.1 0 0 0.1 0 0] "
             b"/CharProcs << >> /Encoding << /Type /Encoding /Differences [1 /a1] >> /FirstChar 1 /LastChar 1 "
             b"/Widths [10] >>")
    r = ler(pdf_de_uma_fonte(fonte, bytes([1, 1, 1])))
    assert r["pdf"]["fontes"] == {"total": 1, "sem_tounicode": 1, "sem_caminho": 0, "type3": 1}
    assert r["pdf"]["paginas"]["type3"]["total"] == 3
    assert r["pdf"]["paginas"]["glifos_sem_caminho"]["total"] == 0


def test_fonte_declarada_e_nao_usada_nao_conta(pypdf):
    objetos = documento()
    objetos[3] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources "
                  b"<< /Font << /F1 5 0 R /F2 6 0 R >> >> >>")
    objetos[6] = b"<< /Type /Font /Subtype /TrueType /BaseFont /X /FontDescriptor << /Flags 4 >> >>"
    r = ler(montar(objetos))
    assert r["pdf"]["fontes"]["total"] == 1 and r["pdf"]["fontes"]["sem_caminho"] == 0


def test_lacuna_agl_declarada(pypdf):
    assert "AGL" in ler(montar(documento()))["lacunas"]["agl"]


# ---------------------------------------------------------------- criptografia

def pdf_cifrado(pypdf, usuario, algoritmo):
    def cifrar(escritor):
        escritor.encrypt(usuario, owner_password="dono", algorithm=algoritmo)

    return pdf_com_paginas(pypdf, [b"BT /F1 12 Tf (segredo) Tj ET"], com_imagem=False, ajustar=cifrar)


def test_cifrado_abre_com_senha_vazia_le_normalmente(pypdf):
    r = ler(pdf_cifrado(pypdf, "", "RC4-128"))
    assert r["pdf"]["criptografado"]["filtro"] == "Standard"
    assert r["pdf"]["criptografado"]["abre_com_senha_vazia"] is True
    assert r["pdf"]["criptografado"]["v"] == 2 and r["pdf"]["criptografado"]["r"] == 3
    assert r["inibidor"] is None and r["_texto"] == "segredo"


def test_cifrado_com_senha_vira_inibidor_sem_vazar_a_senha(pypdf):
    r = ler(pdf_cifrado(pypdf, "abrasenha", "RC4-128"))
    assert r["pdf"]["criptografado"]["abre_com_senha_vazia"] is False
    assert r["inibidor"] == {"tipo": "Password protection", "alvo": "Standard V=2"}
    assert "abrasenha" not in repr(r) and "dono" not in repr(r)
    assert r["pdf"]["paginas"] is None and r["pdf"]["paginas_analisadas"] is None
    assert r["_texto"] is None and r["_paginas"] is None
    assert "paginas" in r["lacunas"] and "criptografado" in r["lacunas"]
    assert r["pdf"]["versao_cabecalho"] is not None and r["pdf"]["revisoes"] == 1
    assert r["erro"] is None


def test_cifrado_aes_com_senha(pypdf):
    pytest.importorskip("cryptography")
    r = ler(pdf_cifrado(pypdf, "abrasenha", "AES-256"))
    assert r["inibidor"]["tipo"] == "Password protection" and r["inibidor"]["alvo"] == "Standard V=5"
    r = ler(pdf_cifrado(pypdf, "", "AES-128"))
    assert r["inibidor"] is None and r["_texto"] == "segredo"
    assert "cryptography" in r["bibliotecas"]


def test_cifrado_sem_cryptography_vira_inibidor_encryption(pypdf, monkeypatch):
    from pypdf.errors import DependencyError

    def sem_aes(self, password):
        raise DependencyError("cryptography>=3.1 is required for AES algorithm")

    dados = pdf_cifrado(pypdf, "", "RC4-128")
    monkeypatch.setattr(pypdf.PdfReader, "decrypt", sem_aes)
    r = ler(dados)
    assert r["inibidor"] == {"tipo": "Encryption", "alvo": "Standard V=2"}
    assert "cryptography" in r["lacunas"]["criptografado"]
    assert r["pdf"]["paginas"] is None


# ---------------------------------------------------------------- prazo

def test_prazo_esgotado_devolve_parcial_com_lacuna(pypdf):
    escritor = escritor_com_paginas(pypdf, [texto_de(5)] * 3, None)
    r = ler(bytes_do(escritor), prazo_s=1e-9)
    assert r["pdf"]["paginas_percorridas"] == 3
    assert r["pdf"]["paginas_analisadas"] < 3
    assert "prazo" in r["lacunas"] and r["erro"] is None


class RelogioFalso:
    """Só as duas primeiras leituras do relógio cabem no prazo; a terceira já o estourou."""

    def __init__(self):
        self.leituras = 0

    def monotonic(self):
        self.leituras += 1
        return 0.0 if self.leituras <= 2 else 10.0


def test_prazo_no_meio_da_pagina_interrompe_a_extracao(pypdf, monkeypatch):
    dados = pdf_com_paginas(pypdf, [b"BT /F1 12 Tf (a) Tj ET " * 2000] * 2, com_imagem=False)
    monkeypatch.setattr(censo_pdf, "time", RelogioFalso())
    r = ler(dados, prazo_s=1.0)
    assert r["pdf"]["paginas_percorridas"] == 2 and r["pdf"]["paginas_analisadas"] == 0
    assert "página 1" in r["lacunas"]["prazo"]
    assert r["erro"] is None


def test_pagina_que_falha_fica_de_fora_e_vira_lacuna(pypdf, monkeypatch):
    dados = bytes_do(escritor_com_paginas(pypdf, [texto_de(5)] * 3, None))
    original = censo_pdf._medir_pagina
    chamadas = []

    def falha_na_segunda(pagina, fontes, fim):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise ValueError("pagina quebrada")
        return original(pagina, fontes, fim)

    monkeypatch.setattr(censo_pdf, "_medir_pagina", falha_na_segunda)
    r = ler(dados)
    assert r["pdf"]["paginas_percorridas"] == 3 and r["pdf"]["paginas_analisadas"] == 2
    assert "2" in r["lacunas"]["paginas"]
    assert len(r["_paginas"]) == 3 and r["_paginas"][1] == ""


# ---------------------------------------------------------------- texto e estatística

def test_caracteres_uteis_ignoram_espaco_controle_ffd_e_uso_privado():
    texto = "ab c" + chr(0xFFFD) + chr(0xE000) + chr(0x0007) + "\n\t" + chr(0xA0) + "d"
    assert censo_pdf._caracteres_uteis(texto) == 4


def test_mediana_e_resumo():
    assert censo_pdf._mediana([1, 2, 3]) == 2
    assert censo_pdf._mediana([1, 2]) == 1.5
    assert censo_pdf._mediana([]) is None
    assert censo_pdf._resumo([]) == {"min": None, "mediana": None, "max": None, "total": 0}
    assert censo_pdf._resumo([3, 9, 6]) == {"min": 3, "mediana": 6, "max": 9, "total": 18}


def test_texto_do_envelope_junta_paginas_com_quebra_de_linha(pypdf):
    conteudos = [b"BT /F1 12 Tf (um) Tj ET", b"BT /F1 12 Tf (dois) Tj ET"]
    r = ler(pdf_com_paginas(pypdf, conteudos, com_imagem=False))
    assert r["_paginas"] == ["um", "dois"] and r["_texto"] == "um\ndois"
