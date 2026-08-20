"""Contrato e conformidade dos adaptadores de wiki e acervo (#2301, #2302).

    python3 -m pytest recuperacao/ -q

Dois níveis, como em `test_contrato_adaptadores.py`:

- **contrato** — cliente falso, sempre roda. Julga o que o adaptador PRODUZ: chave
  estrutural, versão do tipo certo, falha declarada em vez de exceção, e o fail-closed do
  acervo quando a chave que a fonte serve é projeção de exibição.
- **conformidade** — contra a fonte real, PULADO com motivo quando ela não responde.
  Julga a régua do §5: o adaptador projeta o que a fonte já sabe responder, e não outra
  coisa. A comparação é contra a chamada NUA à API com os mesmos parâmetros — é o mesmo
  caminho que o verbo humano usa por baixo, e o que sobra para este teste é justamente o
  mapeamento, que é a parte que pode divergir.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

from recuperacao.adaptadores.acervo import AdaptadorAcervo
from recuperacao.adaptadores.wiki import CONTENT_NS, AdaptadorWiki
from recuperacao.envelope import Casamento, Causa, Cobertura, VersaoTipo
from recuperacao.fontes import Fonte
from recuperacao.adaptadores.base import FonteIndisponivel

MW = os.environ.get("MW_API_URL", "http://127.0.0.1:8080/api.php")
RAG = os.environ.get("RAG_API_URL", "http://127.0.0.1:8100").rstrip("/")
RAG_TOKEN = os.environ.get("RAG_API_TOKEN", "")


# ============================ wiki — contrato ========================================

def wiki_falsa(respostas: dict) -> AdaptadorWiki:
    """`respostas` casa por substring da URL, para o teste declarar o ATO e não a query."""
    def abre(url: str) -> bytes:
        for marca, resp in respostas.items():
            if marca in url:
                return json.dumps(resp).encode()
        raise AssertionError(f"chamada não prevista: {url}")
    return AdaptadorWiki(abre_url=abre)


PAGINA = {"query": {"pages": [{"pageid": 633, "ns": 4, "title": "PlataFirma:Sec/contrato",
                               "revisions": [{"revid": 2916, "slots": {"main": {"content": "corpo"}}}]}]}}
RC = {"query": {"recentchanges": [{"rcid": 3013}]}}


def test_chave_e_page_id_nao_titulo():
    a = wiki_falsa({"list=recentchanges": RC, "prop=revisions": PAGINA})
    item = a.busca("wiki:PlataFirma:Sec/contrato", texto="nenhum").itens[0]
    assert item.procedencia.chave == "wiki:633", "título é volátil; page_id não"
    assert item.procedencia.versao.tipo is VersaoTipo.REVID
    assert item.procedencia.versao.valor == "2916"


def test_secao_do_alvo_entra_na_chave():
    a = wiki_falsa({"list=recentchanges": RC, "prop=revisions": PAGINA})
    item = a.busca("PlataFirma:Sec/contrato#§3", texto="nenhum").itens[0]
    assert item.procedencia.chave == "wiki:633#§3"


def test_alvo_e_secao_aceita_as_tres_formas():
    assert AdaptadorWiki.alvo_e_secao("wiki:A/B#x") == ("A/B", "x")
    assert AdaptadorWiki.alvo_e_secao("A/B") == ("A/B", "")
    assert AdaptadorWiki.alvo_e_secao("  wiki:A  ") == ("A", "")


def test_carimbo_e_o_rc_id_nao_o_rev_id():
    a = wiki_falsa({"list=recentchanges": RC, "prop=revisions": PAGINA})
    r = a.busca("PlataFirma:Sec/contrato", texto="nenhum")
    assert r.linha.carimbo == "rc:3013", "o ledger da wiki responde `mudou desde ontem?`"


def test_texto_nenhum_traz_ref_e_texto_secao_traz_conteudo():
    a = wiki_falsa({"list=recentchanges": RC, "prop=revisions": PAGINA})
    assert a.busca("PlataFirma:Sec/contrato", texto="nenhum").itens[0].ref
    assert a.busca("PlataFirma:Sec/contrato", texto="secao").itens[0].conteudo == "corpo"


def test_cargo_vira_titulos_e_depois_page_id():
    cargo = {"cargoquery": [{"title": {"pagina": "IA/x"}}, {"title": {"pagina": "IA/y"}}]}
    lote = {"query": {"pages": [
        {"pageid": 201, "ns": 0, "title": "IA/x", "revisions": [{"revid": 2650}]},
        {"pageid": 203, "ns": 0, "title": "IA/y", "revisions": [{"revid": 2652}]}]}}
    a = wiki_falsa({"list=recentchanges": RC, "action=cargoquery": cargo, "prop=revisions": lote})
    itens = a.busca("", {"tabela": "Referencias", "where": "dominio='ia'"}, k=5, texto="nenhum").itens
    assert [i.procedencia.chave for i in itens] == ["wiki:201", "wiki:203"]
    assert all(i.casamento is Casamento.EXATO for i in itens), "faceta declarada casa exato"


def test_cargo_forca_pageName_mesmo_quando_o_chamador_esquece():
    visto = {}

    def abre(url):
        if "action=cargoquery" in url:
            visto["url"] = url
            return json.dumps({"cargoquery": []}).encode()
        return json.dumps(RC).encode()
    AdaptadorWiki(abre_url=abre).busca("", {"tabela": "T", "campos": "tipo"}, texto="nenhum")
    assert "_pageName" in visto["url"], "sem `_pageName` não há como resolver o page_id"


def test_busca_em_prosa_cobre_os_namespaces_de_conteudo():
    """O default da API é só o ns 0 — com ele `PlataFirma:` e `Operar:` somem sem erro."""
    visto = {}

    def abre(url):
        if "list=search" in url:
            visto["url"] = url
            return json.dumps({"query": {"search": []}}).encode()
        if "list=recentchanges" in url:
            return json.dumps(RC).encode()
        return json.dumps({"query": {"pages": [{"missing": True}]}}).encode()
    AdaptadorWiki(abre_url=abre).busca("termo qualquer", texto="nenhum")
    assert "srnamespace" in visto["url"]
    assert "3004" in CONTENT_NS, "3004 é `Operar:`; 3000 é `Frente:` (siteinfo, 20/08)"


def test_termo_casa_aproximado_e_titulo_casa_exato():
    busca = {"query": {"search": [{"title": "IA/x"}]}}
    lote = {"query": {"pages": [{"pageid": 201, "ns": 0, "title": "IA/x",
                                 "revisions": [{"revid": 2650}]}]}}
    ordem = []

    def abre(url):
        if "list=recentchanges" in url:
            return json.dumps(RC).encode()
        if "list=search" in url:
            return json.dumps(busca).encode()
        ordem.append(url)
        # 1ª: alvo nominal não existe; 2ª: resolução em lote do que a busca achou
        return json.dumps({"query": {"pages": [{"missing": True}]}} if len(ordem) == 1
                          else lote).encode()
    itens = AdaptadorWiki(abre_url=abre).busca("nao existe", texto="nenhum").itens
    assert itens[0].casamento is Casamento.APROXIMADO


def test_erro_do_mediawiki_vem_no_json_com_200():
    a = wiki_falsa({"list=recentchanges": {"error": {"code": "readapidenied"}}})
    r = a.busca_declarada("qualquer", texto="nenhum")
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert r.linha.causa is Causa.FORA_DO_AR, "PARSE do JSON, nunca código de status"


def test_rede_fora_vira_linha_nao_excecao():
    def abre(_):
        raise urllib.error.URLError("sem rota")
    r = AdaptadorWiki(abre_url=abre).busca_declarada("x", texto="nenhum")
    assert r.linha.causa is Causa.SEM_ROTA and r.itens == []


def test_pagina_sem_revid_levanta_em_vez_de_servir_procedencia_capenga():
    sem = {"query": {"pages": [{"pageid": 1, "ns": 0, "title": "T", "revisions": [{}]}]}}
    a = wiki_falsa({"list=recentchanges": RC, "prop=revisions": sem})
    with pytest.raises(FonteIndisponivel):
        a.busca("T", texto="nenhum")


# ============================ acervo — contrato ======================================

BUSCA_CURTA = {
    "formato_section_id": "curto-v1",
    "cobertura": "boa",
    "sinal": {"medida": "sim", "valor": 0.612, "piso": 0.55},
    "fontes": [{"obra": "RRF", "section_id": "706e2556#abstract", "breadcrumb": ["A"],
                "codigo_exato": False, "texto": None}],
}
BUSCA_COMPLETA = {**BUSCA_CURTA, "formato_section_id": "completo-v1",
                  "fontes": [{**BUSCA_CURTA["fontes"][0],
                              "section_id": "706e2556" + "0" * 56 + "#abstract"}]}
FACETS = {"indice": {"acervo_sha": "443d4c309f75376f615ec5"}}


def acervo_falso(busca: dict, facets: dict = FACETS, **kw) -> AdaptadorAcervo:
    def http(rota, corpo=None):
        return busca if rota == "/search" else facets
    return AdaptadorAcervo(http=http, **kw)


def test_formato_curto_e_projecao_e_o_adaptador_nao_a_grava_como_chave():
    """§4: `curto-v1` é exibição; o gate do §10 compara o sha inteiro."""
    r = acervo_falso(BUSCA_CURTA).busca_declarada("p", texto="nenhum")
    assert r.itens == []
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert r.linha.causa is Causa.SEM_INDICE


def test_escape_de_bancada_existe_nomeado_e_desligado_por_default():
    r = acervo_falso(BUSCA_CURTA, chave_curta=True).busca("p", texto="nenhum")
    assert r.itens[0].procedencia.chave == "acervo:706e2556#abstract"


def test_formato_completo_serve_a_chave_estrutural():
    item = acervo_falso(BUSCA_COMPLETA).busca("p", texto="nenhum").itens[0]
    objeto = item.procedencia.chave.removeprefix("acervo:").split("#")[0]
    assert len(objeto) == 64, "sha256 inteiro do objeto"
    assert item.procedencia.chave.endswith("#abstract")


def test_versao_carrega_o_carimbo_do_indice_marcado_como_digest():
    """`impressao.id` não vem do `/search` (achado 20/08) — e o que sai não finge ser ela."""
    item = acervo_falso(BUSCA_COMPLETA).busca("p", texto="nenhum").itens[0]
    assert item.procedencia.versao.tipo is VersaoTipo.DIGEST
    assert item.procedencia.versao.valor == "443d4c309f75"


def test_sinal_repassa_a_regua_inclusive_a_medida():
    r = acervo_falso(BUSCA_COMPLETA).busca("p", texto="nenhum")
    assert r.linha.sinal.medida == "sim", "sem rerank a régua é outra, e isso viaja"
    assert (r.linha.sinal.valor, r.linha.sinal.piso) == (0.612, 0.55)


def test_rag_dizendo_boa_nao_vira_coberta_sem_gold():
    a = acervo_falso(BUSCA_COMPLETA)
    r = a.busca("p", texto="nenhum")
    assert r.linha.cobertura is Cobertura.NAO_CALIBRADA, "§13 — instrumento desligado"
    assert a.cobertura_do_rag() is Cobertura.COBERTA, "e o rótulo do rag segue legível"


def test_semantica_sem_sinal_seria_contrato_violado_e_por_isso_o_sinal_e_obrigatorio():
    sem_sinal = {**BUSCA_COMPLETA, "sinal": {}}
    r = acervo_falso(sem_sinal).busca("p", texto="nenhum")
    assert r.linha.sinal is None and r.linha.cobertura is Cobertura.NAO_CALIBRADA


@pytest.mark.parametrize("codigo,causa", [
    (401, Causa.SEM_CONCESSAO),   # negado é negado, não é fonte caída
    (403, Causa.SEM_CONCESSAO),
    (503, Causa.FORA_DO_AR),      # a API aquecendo o embedder está no ar, sem índice servido
    (500, Causa.FORA_DO_AR),
])
def test_status_http_vira_a_causa_certa(monkeypatch, codigo, causa):
    """A tradução mora em `_chama`, e é por isso que este teste NÃO injeta `http`: injetar
    pularia justo o código sob julgamento."""
    import io

    def urlopen(*_a, **_kw):
        raise urllib.error.HTTPError(RAG, codigo, "erro", {}, io.BytesIO(b"corpo"))
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    r = AdaptadorAcervo(base=RAG, token="t").busca_declarada("p", texto="nenhum")
    assert r.linha.causa is causa


def test_carimbo_e_constante_de_sessao_lido_uma_vez():
    chamadas = []

    def http(rota, corpo=None):
        chamadas.append(rota)
        return BUSCA_COMPLETA if rota == "/search" else FACETS
    a = AdaptadorAcervo(http=http)
    a.busca("p", texto="nenhum")
    a.busca("outra", texto="nenhum")
    assert chamadas.count("/facets") == 1, "reenviar o que não muda é contexto gasto"


def test_alvo_vazio_nao_vira_busca():
    r = acervo_falso(BUSCA_COMPLETA).busca("", texto="nenhum")
    assert r.itens == [] and r.linha.cobertura is Cobertura.VAZIA


FITA = ("[1] (a.pdf · 706e2556#abstract) — A › ABSTRACT\ntexto um\n"
        "[2] (b.pdf · 999#x) — B\ntexto dois")
BUSCA_SECAO = {**BUSCA_COMPLETA, "contexto": FITA,
               "fontes": [{**BUSCA_COMPLETA["fontes"][0], "n": 1},
                          {"n": 2, "obra": "B", "section_id": "9" * 64 + "#x",
                           "breadcrumb": [], "codigo_exato": False, "texto": None}]}


def test_texto_secao_desmembra_a_fita_de_contexto_por_fonte():
    """`fontes[].texto` é nulo em `texto=secao`: a seção recolada mora em `contexto`."""
    itens = acervo_falso(BUSCA_SECAO).busca("p", k=2, texto="secao").itens
    assert itens[0].conteudo.startswith("[1] (a.pdf")
    assert "texto dois" in itens[1].conteudo
    assert "texto dois" not in itens[0].conteudo, "bloco de um não vaza no do outro"


def test_fita_com_contagem_diferente_cai_para_ref_em_vez_de_emparelhar_errado():
    torta = {**BUSCA_SECAO, "contexto": "[1] (a.pdf · x#y) — A\nso um bloco"}
    itens = acervo_falso(torta).busca("p", k=2, texto="secao").itens
    assert all(i.ref and i.conteudo is None for i in itens), (
        "texto casado com a procedência errada é o pior defeito possível numa citação"
    )


# ============================ conformidade (fonte real) ==============================

def _vivo(url: str, headers: dict | None = None) -> bool:
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=3):  # noqa: S310
            return True
    except Exception:  # noqa: BLE001
        return False


wiki_no_ar = pytest.mark.skipif(
    not _vivo(f"{MW}?action=query&meta=siteinfo&format=json"),
    reason=f"MediaWiki não responde em {MW} — conformidade pulada, não mascarada")

rag_no_ar = pytest.mark.skipif(
    not _vivo(f"{RAG}/health"),
    reason=f"rag-api não responde em {RAG} — conformidade pulada, não mascarada")


@wiki_no_ar
def test_conformidade_wiki_cargo_bate_com_a_api_nua():
    a = AdaptadorWiki()
    itens = a.busca("", {"tabela": "Referencias", "campos": "dominio",
                         "where": "dominio='ia'"}, k=5, texto="nenhum").itens
    d = a._api(action="cargoquery", tables="Referencias", fields="_pageName=pagina",
               where="dominio='ia'", limit=5)
    titulos = [(l.get("title") or {}).get("pagina") for l in d.get("cargoquery") or []]
    assert len(itens) == len([t for t in titulos if t])
    for item in itens:
        assert item.procedencia.chave.startswith("wiki:")
        assert item.procedencia.versao.tipo is VersaoTipo.REVID


@wiki_no_ar
def test_conformidade_wiki_carimbo_e_o_topo_do_ledger():
    a = AdaptadorWiki()
    d = a._api(action="query", list="recentchanges", rclimit=1, rcprop="ids")
    rcid = d["query"]["recentchanges"][0]["rcid"]
    assert a._carimbo() == f"rc:{rcid}"


@rag_no_ar
@pytest.mark.skipif(not RAG_TOKEN, reason="RAG_API_TOKEN ausente no ambiente do teste")
def test_conformidade_acervo_section_id_bate_com_a_api_nua():
    a = AdaptadorAcervo(chave_curta=True)
    pergunta = "fusao reciproca de rankings"
    itens = a.busca(pergunta, {"dominio": ["ia"]}, k=3, texto="nenhum").itens
    d = a._chama("/search", {"pergunta": pergunta, "dominio": ["ia"], "k": 3,
                             "texto": "nenhum"})
    esperado = [f["section_id"] for f in d["fontes"]]
    obtido = [i.procedencia.chave.removeprefix("acervo:") for i in itens]
    assert obtido == esperado, "o adaptador projeta o que a fonte respondeu, não outra coisa"


@rag_no_ar
@pytest.mark.skipif(not RAG_TOKEN, reason="RAG_API_TOKEN ausente no ambiente do teste")
def test_conformidade_acervo_hoje_serve_curto_e_por_isso_o_fail_closed_vale():
    """Se um dia a API passar a servir `completo-v1`, este teste falha — e é o sinal de que
    o fail-closed pode sair. Falhar aqui é boa notícia, e tem de ser visível."""
    a = AdaptadorAcervo(chave_curta=True)
    a.busca("qualquer coisa", k=1, texto="nenhum")
    assert a._ultimo.get("formato_section_id") == "curto-v1", (
        "a API mudou de formato: rever o fail-closed de acervo.py e #2313"
    )
