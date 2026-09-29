"""Testes do ato temporário `acervo censo obra` (card #3189): ficha, estrutura, regras e a pasta.

Só stdlib e fixtures em memória: nada de banco, balde nem docker. Os leitores de formato têm teste próprio
(test_acervo_censo_<formato>.py). Saem junto com o ato, no passo 4 da #3189.
"""
import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

ACERVO = Path(__file__).resolve().parent.parent / "bin" / "_acervo"
sys.path.insert(0, str(ACERVO))

import censo_estrutura as est  # noqa: E402
import censo_ficha as fic  # noqa: E402
import censo_regras as reg  # noqa: E402


def _carrega_censo():
    loader = SourceFileLoader("censo", str(ACERVO / "censo"))
    spec = importlib.util.spec_from_loader("censo", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["censo"] = mod
    loader.exec_module(mod)
    return mod


censo = _carrega_censo()
ID1, ID2, ID3 = "aaaaaaaa-0000-4000-8000-000000000001", "bbbbbbbb-0000-4000-8000-000000000002", "cccccccc-0000-4000-8000-000000000003"


# ---------------------------------------------------------------- estrutura derivável

def test_sumario_conta_a_maior_sequencia_de_folios_nao_decrescentes_e_ignora_lista_de_figuras():
    pag = "Sumário\n1 Introdução ........ 7\n2 Método ............. 15\n3 Resultados ......... 30\n4 Conclusão .......... 41\nFigura 1 Foo ........ 9\n"
    r = est.derivar([pag, "texto"])
    assert r["sumario_entradas"] == {"entradas": 4, "pagina": 1}


def test_indicativos_em_progressao_monotona_e_profundidade():
    corpo = "\n".join(["1 Introdução", "1.1 Contexto", "1.2 Objetivo", "2 Método", "2.1 Amostra", "2.1.1 Critério",
                       "3 Resultados", "5 Salto fora da ordem", "Texto qualquer."])
    r = est.derivar([corpo])
    assert r["indicativos"] == {"contagem": 7, "profundidade_max": 3}


def test_indicativo_de_linha_de_sumario_nao_conta():
    r = est.derivar(["1 Introdução ........ 7\n2 Método ........ 9\n3 Fim ........ 12"])
    assert r["indicativos"]["contagem"] == 0


def test_folio_offset_constante():
    paginas = ["Capa", "Folha de rosto"] + [f"Titulo corrente\ncorpo {i}\n{i - 2}" for i in range(3, 7)]
    r = est.derivar(paginas)
    assert r["folio_offset"] == {"paginas_com_folio": 4, "offset_modal": 2, "constante": True}


def test_hifen_de_fim_de_linha_por_mil_linhas():
    r = est.derivar(["uma pa-\nlavra quebrada\nsegue"])
    assert r["hifen_eol"]["total"] == 1 and r["hifen_eol"]["por_mil_linhas"] == 333.333


def test_mobilia_por_paridade_ignora_folio():
    paginas = [f"Titulo do Livro\ncorpo {i}\n{i}" for i in range(1, 7)]
    r = est.derivar(paginas)
    assert r["mobilia"]["impar"]["proporcao"] == 1.0 and r["mobilia"]["par"]["proporcao"] == 1.0
    assert r["mobilia"]["impar"]["pe"] is None


def test_porte_livro_e_folheto_e_pseudo_paginas():
    assert est.derivar(["x"] * 60)["porte"] == "livro"
    assert est.derivar(["x"] * 10)["porte"] == "folheto"
    pgs, pseudo = est.paginas_de_texto("a\nb\nc")
    assert pseudo is True and len(pgs) == 1
    pgs, pseudo = est.paginas_de_texto("a\fb")
    assert pseudo is False and pgs == ["a", "b"]
    assert est.derivar(pgs, True)["porte"] is None and est.derivar(pgs, True)["mobilia"] is None


def test_derivar_sem_paginas_devolve_none():
    assert est.derivar(None) is None and est.derivar([]) is None


# ---------------------------------------------------------------- B: formato pelos bytes

def _zip(nomes: dict, primeiro_sem_compressao: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, c in nomes.items():
            z.writestr(n, c)
    return buf.getvalue()


def test_pdf_com_lixo_antes_do_cabecalho_e_identificado_pelos_bytes():
    cands, _ = fic.detectar(b"\n\nlixo%PDF-1.4\n%%EOF")
    assert [c["formato_id"] for c in cands] == ["pdf"] and cands[0]["versao"] == "1.4"
    assert "byte 6" in cands[0]["base"]


def test_zip_epub_docx_pptx_e_zip_simples():
    epub = _zip({"mimetype": "application/epub+zip", "META-INF/container.xml": "<c/>"})
    docx = _zip({"[Content_Types].xml": "<t/>", "word/document.xml": "<d/>"})
    pptx = _zip({"[Content_Types].xml": "<t/>", "ppt/presentation.xml": "<p/>"})
    simples = _zip({"a.txt": "x"})
    assert fic.detectar(epub)[0][0]["formato_id"] == "epub"
    assert fic.detectar(docx)[0][0]["formato_id"] == "docx"
    assert fic.detectar(pptx)[0][0]["formato_id"] == "pptx"
    cands, cont = fic.detectar(simples)
    assert cands[0]["formato_id"] == "zip" and cont["membros_total"] == 1 and cont["membros_topo"] == ["a.txt"]


def test_epub_sem_mimetype_e_tentativo():
    cands, _ = fic.detectar(_zip({"META-INF/container.xml": "<c/>"}))
    assert cands[0]["formato_id"] == "epub" and cands[0]["tentativo"] is True


def test_mobi_pela_assinatura_do_palmdb_e_a_caixa_importa():
    dados = bytearray(100)
    dados[60:68] = b"BOOKMOBI"
    assert fic.detectar(bytes(dados))[0][0]["formato_id"] == "mobi"
    dados[60:68] = b"bookmobi"
    assert fic.detectar(bytes(dados))[0] == []


def test_textos_sem_assinatura():
    assert fic.detectar(b"<!DOCTYPE html><html><head></head><body>x</body></html>")[0][0]["formato_id"] == "html"
    assert fic.detectar("# Titulo\n\ntexto\n\n- a\n- b\n".encode())[0][0]["formato_id"] == "md"
    assert fic.detectar(b"apenas texto simples sem marcas\n" * 3)[0][0]["formato_id"] == "txt"
    j = fic.detectar(b'{"a": 1}')[0][0]
    assert j["formato_id"] == "json" and j["tentativo"] is True
    assert fic.detectar(b"")[0] == []
    assert fic.detectar(bytes(range(256)) * 4)[0] == []


def test_situacao_de_identificacao():
    pdf = [fic._f("pdf", "PDF", "1.7", "application/pdf", "b")]
    assert fic.situacao_identificacao(pdf, "pdf") == "identificado"
    assert fic.situacao_identificacao(pdf, "epub") == "extensao_diverge"
    assert fic.situacao_identificacao(pdf, "") == "identificado"
    assert fic.situacao_identificacao(pdf, "3") == "identificado"        # ".3" de "v2.3" não é extensão
    assert fic.situacao_identificacao([], "pdf") == "desconhecido"
    assert fic.situacao_identificacao(pdf + pdf, "pdf") == "disjuncao"
    txt = [fic._f("txt", "Plain text", None, "text/plain", "b", True)]
    assert fic.situacao_identificacao(txt, "md") == "tentativo"


# ---------------------------------------------------------------- C e J

def test_metricas_de_texto():
    m = fic.metricas_texto("ok " + chr(0xFB01) + chr(0xFFFD) + chr(0xE001) + "e" + chr(0x0301))
    assert m["ligaduras"] == 1 and m["substituicao"] == 1 and m["uso_privado"] == 1
    assert m["normalizacao_unicode"]["nfc"] is False and m["normalizacao_unicode"]["nfd"] is True
    assert fic.metricas_texto("abc")["normalizacao_unicode"] == {"nfc": True, "nfd": True}


def test_secoes_do_catalogo_tschichold_e_nbr6029():
    secoes = [["T H E", 1, 5], ["F O R M", 1, 5], ["4.2.3.5 Modelo", 2, 10], ["Apêndice A", 1, 20], ["Apêndice B", 1, 20],
              ["1 Introdução", 1, 30]]
    a = fic.analisar_secoes(secoes)
    assert a["caixa_espacada"] == 2 and a["nivel_diverge_indicativo"] == 1 and a["irmas_curtas"] == 2


def test_bloco_catalogo_e_fracao_da_maior_secao():
    item = {"titulo": "T", "expurgada": False, "impressao": {"metodo": {"perfil": "pdf", "needs_ocr": False}, "tem_espelho": True},
            "n_servindo": 1, "estados": {"servindo": 1}, "secoes_n": 2, "nivel_max": 1, "maior_chars": 900, "texto_chars": 1000,
            "trechos_n": 5, "secoes": []}
    c = fic.bloco_catalogo(item)
    assert c["aceite_universo"] is True and c["maior_secao_fracao"] == 0.9 and c["metodo_perfil"] == "pdf"
    assert fic.bloco_catalogo({"objeto": "x", "expurgada": True})["aceite_universo"] is False


# ---------------------------------------------------------------- a ficha, com balde de mentira

def _item(objeto, arquivo="livro.txt", **kw):
    base = {"obra_id": ID1, "arquivo": arquivo, "objeto": objeto, "titulo": "Livro", "expurgada": False,
            "impressao": {"metodo": {"perfil": "pdf", "needs_ocr": False}}, "n_servindo": 1, "estados": {"servindo": 1},
            "secoes_n": 0, "trechos_n": 3, "secoes": []}
    base.update(kw)
    return base


def test_ficha_de_objeto_ausente_e_vazio_e_erro_de_busca():
    f = fic.montar_ficha(_item("acervo/" + "1" * 64), lambda o: (None, "ausente"))
    assert f["objeto_ausente"] is True and f["situacao_identificacao"] == "desconhecido" and f["erro"] is None
    f = fic.montar_ficha(_item("acervo/" + fic.SHA_VAZIO), lambda o: (b"", None))
    assert f["objeto_vazio"] is True and f["fixidez_confere"] is True and f["situacao_identificacao"] == "desconhecido"
    f = fic.montar_ficha(_item("acervo/" + "1" * 64), lambda o: (None, "boom"))
    assert f["erro"] == "buscar: boom" and f["situacao_identificacao"] is None


def test_ficha_de_texto_com_fixidez_e_sem_fixidez():
    dados = b"texto simples\n" * 5
    sha = hashlib.sha256(dados).hexdigest()
    f = fic.montar_ficha(_item("acervo/" + sha), lambda o: (dados, None))
    assert f["fixidez_confere"] is True and f["bytes"] == len(dados) and f["formato_id"] == "txt"
    assert f["extensao"] == "txt" and f["sha256_guardado"] == sha and f["categoria"] == "file"
    f = fic.montar_ficha(_item("acervo/" + "0" * 64), lambda o: (b"abc", None))
    assert f["fixidez_confere"] is False


def test_ficha_nao_levanta_com_leitor_ausente_e_registra_lacuna():
    dados = b"%PDF-1.4\n%%EOF"
    f = fic.montar_ficha(_item("acervo/" + hashlib.sha256(dados).hexdigest(), arquivo="a.epub"), lambda o: (dados, None))
    assert f["formato_id"] == "pdf" and f["situacao_identificacao"] == "extensao_diverge"
    assert f["erro"] is None


# ---------------------------------------------------------------- regras

def F(**kw):
    base = {"obra_id": ID1, "nome_original": "a.pdf", "extensao": "pdf", "formato_id": "pdf", "situacao_identificacao": "identificado",
            "formatos": [{"nome": "PDF"}], "objeto_ausente": False, "objeto_vazio": False, "fixidez_confere": True,
            "inibidor": None, "estrutura_declarada": [], "estrutura": None, "erro": None,
            "catalogo": {"titulo": "A", "expurgada": False, "impressao_servindo": True, "impressoes_por_estado": {"servindo": 1},
                         "metodo_perfil": "BOOK", "needs_ocr": False, "secoes_n": 10, "secoes_n_nivel2": 3, "trechos_n": 9,
                         "maior_secao_fracao": 0.1, "secoes_analise": {}},
            "texto": None, "encoding": None, "pdf": None, "lingua_declarada": None}
    cat = kw.pop("catalogo", None)
    base.update(kw)
    if cat:
        base["catalogo"] = {**base["catalogo"], **cat}
    return base


def _regras(f):
    return {(c["regra"], c["clausula"]) for c in reg.avaliar_obra(f)}


def test_r1_r2_r9():
    assert ("R1", "") in _regras(F(situacao_identificacao="extensao_diverge", extensao="epub"))
    assert ("R1", "") in _regras(F(situacao_identificacao="disjuncao"))
    assert ("R2", "") in _regras(F(objeto_vazio=True))
    assert ("R2", "") in _regras(F(fixidez_confere=False, sha256_calculado="a", sha256_guardado="b"))
    assert ("R2", "") in _regras(F(objeto_ausente=True))
    assert ("R9", "") in _regras(F(inibidor={"tipo": "DRM", "alvo": "x"}))
    assert ("R9", "") not in _regras(F(inibidor={"tipo": "Font obfuscation", "alvo": "3 fontes"}))
    assert _regras(F()) == set()


def test_r3_estrutura_declarada_contra_poucas_secoes_livro_e_concentracao():
    f = F(formato_id="epub", estrutura_declarada=[{"fonte": "epub_nav", "entradas": 170, "profundidade": 3}],
          catalogo={"secoes_n": 1})
    assert ("R3", "estrutura") in _regras(f)
    assert ("R3", "livro") in _regras(F(estrutura={"porte": "livro", "paginas": 300}, catalogo={"secoes_n": 1}))
    assert ("R3", "concentracao") in _regras(F(catalogo={"maior_secao_fracao": 0.8, "maior_secao_chars": 80000, "secoes_n": 10}))
    assert ("R3", "estrutura") not in _regras(F(estrutura_declarada=[{"fonte": "x", "entradas": 4, "profundidade": 1}], catalogo={"secoes_n": 1}))
    assert ("R3", "estrutura") not in _regras(F(catalogo={"impressao_servindo": False, "secoes_n": 0},
                                                 estrutura_declarada=[{"fonte": "x", "entradas": 9, "profundidade": 1}]))


def test_r4_nivel_indicativo_irmas_e_caixa_espacada():
    f = F(estrutura_declarada=[{"fonte": "pdf_outline", "entradas": 30, "profundidade": 3}], catalogo={"secoes_n_nivel2": 0, "secoes_n": 20})
    assert ("R4", "nivel2") in _regras(f)
    an = {"nivel_diverge_indicativo": 1, "nivel_diverge_exemplos": ["4.2.3.5 (nível 2)"], "irmas_curtas": 2, "irmas_exemplos": ["A", "B"],
          "caixa_espacada": 2, "caixa_exemplos": ["T H E"]}
    r = _regras(F(catalogo={"secoes_analise": an}))
    assert {("R4", "nivel-indicativo"), ("R4", "excesso-de-corte"), ("R4", "caixa-espacada")} <= r


def test_r5_ocr_glifos_e_marcado_e_o_caso_da_iti_nao_cai():
    pdf = {"camada_texto": {"paginas_ocr": [1, 2], "paginas_glifos_sem_caminho_gt20": [4], "marcado_com_fontes_sem_mapeamento": True}}
    r = _regras(F(pdf=pdf))
    assert {("R5", "ocr"), ("R5", "glifos"), ("R5", "marcado")} <= r
    assert ("R5", "ocr") not in _regras(F(pdf=pdf, catalogo={"needs_ocr": True}))
    assert _regras(F(pdf={"camada_texto": {"paginas_ocr": [], "paginas_glifos_sem_caminho_gt20": [], "marcado_com_fontes_sem_mapeamento": False}})) == set()


def test_r6_charset_substituicao_nfc_e_lingua():
    f = F(encoding={"declarado": "iso-8859-1", "detectado": "utf-8", "declarado_bate": False},
          texto={"substituicao": 3, "normalizacao_unicode": {"nfc": False}, "lingua_detectada": {"codigo": "en"}}, lingua_declarada="pt-BR")
    assert {("R6", "charset"), ("R6", "substituicao"), ("R6", "nfc"), ("R6", "lingua")} <= _regras(f)
    assert ("R6", "lingua") not in _regras(F(texto={"lingua_detectada": {"codigo": "pt"}}, lingua_declarada="por"))


def test_r7_quatro_clausulas():
    assert ("R7", "a") in _regras(F(catalogo={"expurgada": True}))
    assert ("R7", "b") in _regras(F(catalogo={"trechos_n": 0}))
    assert ("R7", "c") in _regras(F(catalogo={"impressao_servindo": False, "impressoes_por_estado": {"em_construcao": 1}}))
    assert ("R7", "d") in _regras(F(formato_id="md", catalogo={"metodo_perfil": "pdf"}))
    assert ("R7", "d") not in _regras(F(formato_id="pdf", catalogo={"metodo_perfil": "pdf"}))


def test_obra_com_erro_de_busca_nao_gera_contradicao():
    assert reg.avaliar_obra(F(erro="buscar: boom", objeto_vazio=True)) == []


def test_r8_nome_igual_titulo_igual_e_titulo_nome_de_arquivo():
    a = F(obra_id=ID1, nome_original="1.pdf", catalogo={"titulo": "Documento Um"})
    b = F(obra_id=ID2, nome_original="1.pdf", formato_id="html", catalogo={"titulo": "Documento um"})
    c = F(obra_id=ID3, nome_original="x.pdf", catalogo={"titulo": "2408.09869v5"})
    d = F(obra_id="dddddddd-0000-4000-8000-000000000004", nome_original="y.pdf", catalogo={"titulo": "Documento Um"})
    out = reg.avaliar_identidade([a, b, c, d])
    pares = {(x["obra_id"][:8], x["clausula"]) for x in out}
    assert ("aaaaaaaa", "a") in pares and ("bbbbbbbb", "a") in pares          # mesmo nome de arquivo
    assert ("aaaaaaaa", "b") in pares and ("dddddddd", "b") in pares          # mesmo título e mesmo formato
    assert ("bbbbbbbb", "b") not in pares                                     # formato diferente
    assert ("cccccccc", "c") in pares                                         # título é nome de arquivo


def test_casos_conhecidos_e_resumo_e_tsv():
    e_arq = F(obra_id="0d9fc4f8-0000-4000-8000-000000000009", formato_id="pdf", catalogo={"secoes_n": 1},
              estrutura_declarada=[{"fonte": "pdf_outline", "entradas": 40, "profundidade": 2}])
    iti = F(obra_id="8d2864b1-0000-4000-8000-00000000000a", nome_original="IN35 ITI.pdf", pdf={"camada_texto": {"paginas_ocr": []}})
    fichas = [e_arq, iti]
    contra = []
    for f in fichas:
        contra += reg.avaliar_obra(f)
    casos = {c["caso"]: c for c in reg.conferir_casos(fichas, contra)}
    assert casos["e-ARQ Brasil v2 (0d9fc4f8): texto numa seção só"]["ok"] is True
    assert casos["IN ITI nº 35: NÃO cai no critério de OCR"]["ok"] is True
    assert casos["Bringhurst (nav do EPUB, 1 seção)"]["ok"] is None          # obra não está no lote: não achou
    res = reg.resumir(fichas, contra)
    assert res["regras"]["R3"]["violacoes"] >= 1 and set(res["regras"]) == set(reg.REGRAS)
    linhas = reg.linhas_tsv(contra, {f["obra_id"]: f for f in fichas})
    assert linhas[0].split("\t")[:5] == ["obra_id", "regra", "valor_do_arquivo", "valor_do_catalogo", "nota"]
    assert any(l.split("\t")[1] == "R3" for l in linhas[1:])


# ---------------------------------------------------------------- a pasta e o orquestrador

def test_ids_de_valida_e_le_arquivo(tmp_path):
    assert censo._ids_de("dc9412e9,3AEDF83B") == ["dc9412e9", "3aedf83b"]
    assert censo._ids_de(None) is None
    with pytest.raises(censo.Falha) as e:
        censo._ids_de("x;drop")
    assert e.value.codigo == 2
    arq = tmp_path / "ids.txt"
    arq.write_text("# comentário\ndc9412e9\n\n3aedf83b\n")
    assert censo._ids_de("@" + str(arq)) == ["dc9412e9", "3aedf83b"]


def test_pasta_de_saida_recusada_e_criada(tmp_path):
    with pytest.raises(censo.Falha) as e:
        censo.validar_pasta("/opt/platafirma/x")
    assert e.value.codigo == 2
    assert Path(censo.validar_pasta(str(tmp_path / "nova"))).is_dir()


def _fichas_jsonl(pasta, fichas, quebrada=False):
    with open(Path(pasta) / "ficha.jsonl", "w", encoding="utf-8") as f:
        for x in fichas:
            f.write(json.dumps(x) + "\n")
        if quebrada:
            f.write('{"obra_id": "cortada')


def test_status_conta_ficha_erro_pendente_e_linha_quebrada(tmp_path):
    (tmp_path / "universo.jsonl").write_text("".join(json.dumps({"obra_id": i}) + "\n" for i in (ID1, ID2, ID3)))
    _fichas_jsonl(tmp_path, [{"obra_id": ID1, "erro": None}, {"obra_id": ID2, "erro": "buscar: boom"}], quebrada=True)
    s = censo.status(str(tmp_path))
    assert (s["universo"], s["com_ficha"], s["com_erro"], s["pendentes"], s["linhas_quebradas"]) == (3, 2, 1, 1, 1)
    assert s["em_andamento"] is None and s["obras_com_erro"] == [ID2]
    with pytest.raises(censo.Falha):
        censo.status(str(tmp_path / "nao-existe"))


def test_ler_fichas_a_ultima_linha_da_obra_vale(tmp_path):
    _fichas_jsonl(tmp_path, [{"obra_id": ID1, "erro": "x"}, {"obra_id": ID1, "erro": None}])
    fichas, ruins = censo.ler_fichas(str(tmp_path))
    assert fichas[ID1]["erro"] is None and ruins == 0


def test_finalizar_grava_tsv_e_resumo(tmp_path):
    universo = [{"obra_id": ID1}, {"obra_id": ID2}]
    (tmp_path / "universo.jsonl").write_text("".join(json.dumps(u) + "\n" for u in universo))
    _fichas_jsonl(tmp_path, [F(obra_id=ID1, objeto_vazio=True), F(obra_id=ID2)])
    r = censo.finalizar(str(tmp_path), {"impressoes_servindo_antes": 10, "impressoes_servindo_depois": 10})
    assert r["regras"]["R2"]["violacoes"] == 1 and r["pendentes"] == 0
    assert r["impressoes_servindo"] == {"antes": 10, "depois": 10}
    tsv = (tmp_path / "contradicoes.tsv").read_text().splitlines()
    assert tsv[0].startswith("obra_id\tregra") and any("\tR2\t" in l for l in tsv[1:])
    assert json.loads((tmp_path / "resumo.json").read_text())["universo"] == 2
    base = (tmp_path / "levantamento-base.md").read_text()
    assert "## Contagem por formato identificado" in base and "### R2" in base and "objeto_vazio" in base


def _worker_falso(item):
    return {"obra_id": item["obra_id"], "erro": None, "formato_id": "txt", "tempos_ms": {"total": 1}}


def test_pool_grava_uma_linha_por_obra_e_a_pasta_e_retomavel(tmp_path, monkeypatch):
    monkeypatch.setattr(censo, "_init_worker", lambda cfg: None)
    monkeypatch.setattr(censo, "_worker", _worker_falso)
    itens = [{"obra_id": f"{n:08d}-0000-4000-8000-000000000000"} for n in range(7)]
    censo._executar(str(tmp_path), itens[:4], {"workers": 2, "prazo_obra_s": 5}, 2)
    fichas, _ = censo.ler_fichas(str(tmp_path))
    assert len(fichas) == 4
    (tmp_path / "ficha.jsonl").open("a").write('{"obra_id": "cortada')       # a rodada morreu no meio de uma linha
    censo._executar(str(tmp_path), itens[4:], {"workers": 2, "prazo_obra_s": 5}, 2)
    fichas, ruins = censo.ler_fichas(str(tmp_path))
    assert len(fichas) == 7 and ruins == 1


def test_main_sem_bancada_e_argumento_estranho():
    assert censo.main([]) == 2
    assert censo.main(["obra", "--bancada", "/tmp", "--tolice"]) == 2
