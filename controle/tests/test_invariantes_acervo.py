"""Os invariantes I1 a I13 de `release conferir acervo` e o gate contra o retrato (#3324).

Prova, sem banco e sem balde reais (os dados são dicts no formato de `coletar`): cada invariante tem um
caso que viola e o caso limpo; a chave de cada violação se atribui à obra; o gate sai 1 só com violação
bloqueante NOVA contra o retrato guardado, a herdada vai ao relato e não trava, e sem retrato o exit segue
nos predicados de hoje. Não prova: os bancos e o balde de verdade (a rodada em produção do card).
"""
import copy
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir"))

import predicados_acervo as pa  # noqa: E402
import resultado  # noqa: E402


def _obra(i="o1", marcacao="transcrita e indexada", retirada=False, tem_autoria=True, ficha_ok=True):
    return {"id": i, "titulo": f"Obra {i}", "retirada": retirada, "tem_autoria": tem_autoria,
            "marcacao": marcacao, "objeto": f"acervo/sha-{i}", "objeto_id": f"sha-{i}", "ficha_ok": ficha_ok}


def _imp(i="i1", obra="o1", estado="servindo", espelho=True, regua="7", reclamada=False):
    return {"id": i, "obra": obra, "estado": estado, "metodo": "m1", "espelho": espelho, "digest": f"dig-{i}",
            "regua": regua, "servivel": True, "imperfeita": False, "reclamada": reclamada}


def _ix(i="x1", imp="i1", obra="o1", estado="servindo", gran="trecho", part="biblioteca", gserv=True, n=3,
        h="h"):
    return {"id": i, "imp": imp, "obra": obra, "estado": estado, "gran": gran, "part": part,
            "geracao_servindo": gserv, "n": n, "h": h}


def _ger(i, particao="biblioteca", estado="servindo"):
    return {"id": i, "particao": particao, "estado": estado, "numero": 1, "embedder": "m",
            "dimensao_trecho": "1024", "dimensao_faceta": "256"}


def _base():
    """Uma obra exposta em trecho, uma impressão servindo, um índice com os três vetores: limpo."""
    return pa.completar({
        "obras": [_obra()], "impressoes": [_imp()], "aposentadas": [], "total": 1,
        "trechos": {"i1": {"imp": "i1", "n": 3, "h": "h"}},
        "motor": {"geracoes": [_ger("gb"), _ger("gc", "casa")], "indices": [_ix()], "faceta_alvo_errado": []},
        "i13": {"obra": [], "casa": [], "existentes": ["i1"]}, "i13_motor": ["i1"],
        "versao": 7, "balde": {"espelhos": {("sha-o1", "dig-i1")}, "objetos": {"acervo/sha-o1"}},
        "espelhos_orfaos": 0,
    })


def _com(**mudancas):
    d = _base()
    d.update(mudancas)
    return pa.completar(d)


def test_a_base_nao_viola_nenhum_invariante():
    atual = pa.avaliar_invariantes(_base())
    assert list(atual) == list(pa.INVARIANTES) and all(v == [] for v in atual.values())


def test_a_tabela_tem_a_classe_do_guia():
    bloqueantes = {c for c, (_, classe) in pa.INVARIANTES.items() if classe == "bloqueante"}
    assert bloqueantes == {"I1", "I2", "I3", "I4", "I5", "I8", "I11", "I13"}


# I1 ----------------------------------------------------------------------------------------------

def test_i1_duas_servindo_ou_nenhuma_viola():
    assert pa.i1(_com(impressoes=[_imp(), _imp("i2")])) == ["obra:o1"]
    assert pa.i1(_com(impressoes=[])) == ["obra:o1"]


def test_i1_obra_so_em_arquivo_ou_retirada_nao_cobra():
    assert pa.i1(_com(obras=[_obra(marcacao="inteira")], impressoes=[])) == []
    assert pa.i1(_com(obras=[_obra(retirada=True)], impressoes=[])) == []


# I2 ----------------------------------------------------------------------------------------------

def test_i2_vetor_a_menos_ou_sem_indice_viola():
    d = _base()
    d["motor"]["indices"][0]["n"] = 2
    assert pa.i2(d) == ["obra:o1"]
    d["motor"]["indices"] = []
    assert pa.i2(d) == ["obra:o1"]


def test_i2_indice_fora_da_geracao_servindo_viola():
    d = _base()
    d["motor"]["indices"][0]["geracao_servindo"] = False
    assert pa.i2(d) == ["obra:o1"]


def test_i2_obra_so_em_texto_nao_cobra_vetor():
    d = _com(obras=[_obra(marcacao="transcrita")])
    d["motor"]["indices"] = []
    assert pa.i2(d) == []


# I3 ----------------------------------------------------------------------------------------------

def test_i3_retirada_com_impressao_ou_indice_servindo_viola():
    assert pa.i3(_com(obras=[_obra(retirada=True)])) == ["obra:o1"]
    d = _com(obras=[_obra(retirada=True)], impressoes=[])
    assert pa.i3(d) == ["obra:o1"]          # sobrou o índice
    d["motor"]["indices"] = []
    assert pa.i3(d) == []


# I4 ----------------------------------------------------------------------------------------------

def test_i4_alvos_diferentes_com_a_mesma_contagem_viola():
    d = _base()
    d["motor"]["indices"][0]["h"] = "outro"
    assert pa.i4(d) == ["indice:x1"]


def test_i4_faceta_apontando_para_outra_impressao_viola():
    d = _base()
    d["motor"]["faceta_alvo_errado"] = ["xf"]
    assert pa.i4(d) == ["indice:xf"]


# I5 ----------------------------------------------------------------------------------------------

def test_i5_indice_servindo_de_impressao_que_nao_serve_viola():
    assert pa.i5(_com(impressoes=[_imp(estado="em_construcao")])) == ["indice:x1"]


# I6 ----------------------------------------------------------------------------------------------

def test_i6_sem_espelho_declarado_ou_fora_do_balde_viola():
    assert pa.i6(_com(impressoes=[_imp(espelho=False)])) == ["impressao:i1"]
    d = _base()
    d["balde"]["espelhos"] = set()
    assert pa.i6(d) == ["impressao:i1"]


def test_i6_sem_a_listagem_do_balde_so_olha_o_catalogo():
    assert pa.i6(_com(balde=None)) == []
    assert pa.i6(_com(balde=None, impressoes=[_imp(espelho=False)])) == ["impressao:i1"]


# I7 ----------------------------------------------------------------------------------------------

def test_i7_sem_ficha_ou_objeto_fora_do_balde_viola():
    assert pa.i7(_com(obras=[_obra(ficha_ok=False)])) == ["obra:o1"]
    d = _base()
    d["balde"]["objetos"] = set()
    assert pa.i7(d) == ["obra:o1"]


# I8 ----------------------------------------------------------------------------------------------

def test_i8_duas_geracoes_servindo_ou_indice_fora_dela_viola():
    d = _base()
    d["motor"]["geracoes"].append(_ger("gb2"))
    assert pa.i8(d) == ["geracao:biblioteca"]
    d = _base()
    d["motor"]["geracoes"] = [_ger("gb", estado="em_construcao"), _ger("gc", "casa")]
    assert pa.i8(d) == ["geracao:biblioteca"]
    d = _base()
    d["motor"]["indices"][0]["geracao_servindo"] = False
    assert pa.i8(d) == ["indice:x1"]


# I9 ----------------------------------------------------------------------------------------------

def test_i9_regua_anterior_ou_sem_veredito_viola_e_regua_ilegivel_nao_mede():
    assert pa.i9(_com(impressoes=[_imp(regua="5")])) == ["impressao:i1"]
    assert pa.i9(_com(impressoes=[_imp(regua=None)])) == ["impressao:i1"]
    assert pa.i9(_com(versao=None)) is None


# I10 ---------------------------------------------------------------------------------------------

def test_i10_retirada_sem_autoria_viola():
    assert pa.i10(_com(obras=[_obra(retirada=True, tem_autoria=False)])) == ["obra:o1"]


# I11 ---------------------------------------------------------------------------------------------

def test_i11_arquivo_com_impressao_servindo_viola():
    assert pa.i11(_com(obras=[_obra(marcacao="inteira")])) == ["obra:o1"]


def test_i11_texto_com_indice_servindo_viola():
    assert pa.i11(_com(obras=[_obra(marcacao="transcrita")])) == ["obra:o1"]


# I12 ---------------------------------------------------------------------------------------------

def test_i12_sombra_sem_lote_viola_e_com_lote_nao():
    assert pa.i12(_com(impressoes=[_imp(), _imp("i2", estado="em_construcao")])) == ["impressao:i2"]
    assert pa.i12(_com(impressoes=[_imp(), _imp("i2", estado="em_construcao", reclamada=True)])) == []


def test_i12_indice_e_geracao_em_construcao_entram():
    d = _base()
    d["motor"]["indices"].append(_ix("x2", "i1", estado="em_construcao"))
    d["motor"]["geracoes"].append(_ger("gn", estado="em_construcao"))
    assert pa.i12(d) == ["geracao:gn", "indice:x2"]


# I13 ---------------------------------------------------------------------------------------------

def test_i13_aposentada_de_obra_viva_viola_e_se_atribui_a_obra():
    d = _com(aposentadas=[{"id": "ia", "obra": "o1"}])
    assert pa.i13(d) == ["impressao:ia"]
    assert pa.obra_da_chave("impressao:ia", d) == "o1"


def test_i13_casa_indice_orfao_e_espelho_sem_dono_violam():
    d = _com(i13={"obra": [], "casa": ["ci1"], "existentes": ["i1"]}, i13_motor=["i1", "sumiu"],
             espelhos_orfaos=2)
    assert pa.i13(d) == ["casa_impressao:ci1", "indice-orfao:sumiu", "espelho-orfao:0", "espelho-orfao:1"]


def test_i13_balde_que_nao_respondeu_nao_mede():
    assert pa.i13(_com(espelhos_orfaos=None)) is None


# chave -> obra, resumo -----------------------------------------------------------------------------

def test_resumo_traz_contagem_e_obras_de_cada_um():
    d = _com(obras=[_obra(marcacao="inteira"), _obra("o2")], impressoes=[_imp(), _imp("i2", "o2")],
             trechos={"i1": {"n": 3, "h": "h"}, "i2": {"n": 3, "h": "h"}})
    res = pa.resumo(pa.avaliar_invariantes(d), d)
    assert set(res) == set(pa.INVARIANTES)
    assert res["I11"]["n"] == 1 and res["I11"]["obras"] == ["o1"]
    assert res["I1"]["n"] == 0 and res["I1"]["obras"] == []
    assert res["I11"]["classe"] == "bloqueante" and res["I6"]["classe"] == "aviso"


def test_chave_sem_obra_fica_sem_obra():
    assert pa.obra_da_chave("geracao:biblioteca", _base()) is None
    assert pa.obra_da_chave("espelho-orfao:3", _base()) is None


# o balde: a rota corta a listagem em 1000 itens, sem avisar ----------------------------------------------

SHA = "a1" * 32
DIG = "b2" * 32
CHAVE_ESPELHO = f"acervo/espelho/{SHA}/{DIG}/espelho.md"


def _item(chave):
    return {"objeto": chave, "bytes": 1, "modificado_em": "2026-10-07T00:00:00+00:00"}


def _listagem(por_colecao, vistos=None):
    """A rota falsa: lista `por_colecao[coleção]` filtrada pelo prefixo e cortada em 1000, como a de verdade."""
    def listagem(colecao, prefixo):
        if vistos is not None:
            vistos.append((colecao, prefixo))
        chaves = [c for c in por_colecao.get(colecao, []) if not prefixo or c.split("/", 1)[1].startswith(prefixo)]
        return [_item(c) for c in chaves[:pa.TETO_LISTAGEM]]
    return listagem


def test_balde_pequeno_lista_uma_vez_por_colecao_e_separa_espelho_de_objeto():
    vistos = []
    balde = pa.listar_balde(_listagem({"firma": [CHAVE_ESPELHO, f"acervo/espelho/{SHA}/{DIG}/indice.json",
                                                 f"acervo/{SHA}"]}, vistos))
    assert balde == {"espelhos": {(SHA, DIG)}, "objetos": {f"acervo/{SHA}"}}
    assert vistos == [("firma", None), ("pessoal", None)]


def test_balde_no_teto_lista_por_faixa_e_nao_perde_o_que_a_rota_cortaria():
    objetos = [f"acervo/{i:02x}{'0' * 62}" for i in range(256)]
    espelhos = [f"acervo/espelho/{i % 16:x}{i:063x}/{DIG}/espelho.md" for i in range(1200)]
    vistos = []
    balde = pa.listar_balde(_listagem({"firma": objetos + espelhos}, vistos))
    assert len(balde["espelhos"]) == 1200 and len(balde["objetos"]) == 256       # a rota cortaria em 1000
    assert ("firma", "espelho/0") in vistos and ("firma", "ff") in vistos


def test_balde_com_faixa_no_teto_e_indeterminavel_e_nao_cortado_em_silencio():
    espelhos = [f"acervo/espelho/0{i:063x}/{DIG}/espelho.md" for i in range(1200)]      # tudo na faixa espelho/0
    with pytest.raises(pa.Indeterminavel, match="espelho/0.*teto"):
        pa.listar_balde(_listagem({"firma": espelhos}))


def test_balde_fora_do_ar_e_indeterminavel():
    def fora(colecao, prefixo):
        raise pa.Indeterminavel("balde firma: HTTP 503")

    with pytest.raises(pa.Indeterminavel, match="503"):
        pa.listar_balde(fora)


def test_i6_e_i7_leem_o_balde_listado_por_faixa():
    d = _base()
    d["balde"] = pa.listar_balde(_listagem({"firma": ["acervo/espelho/sha-o1/dig-i1/espelho.md", "acervo/sha-o1"]}))
    assert d["balde"]["espelhos"] == set() and pa.i6(d) == ["impressao:i1"]   # chave que não é sha de 64 hex não conta
    d["balde"] = pa.listar_balde(_listagem({"firma": [f"acervo/espelho/{SHA}/{DIG}/espelho.md", f"acervo/{SHA}"]}))
    d["obras"][0].update(objeto_id=SHA, objeto=f"acervo/{SHA}")
    d["impressoes"][0]["digest"] = DIG
    assert pa.i6(d) == [] and pa.i7(d) == []


# o gate --------------------------------------------------------------------------------------------

def _retrato(**chaves):
    return {"id": "11111111-aaaa", "tirado_em": "2026-10-07T12:00:00Z",
            "invariantes": {c: {"chaves": v} for c, v in chaves.items()}}


def _atual(**chaves):
    return {c: list(chaves.get(c, [])) for c in pa.INVARIANTES}


def _gate(atual, anterior, itens=()):
    d = _base()
    itens, avisos, res = pa.aplicar_gate(list(itens), [], atual, anterior, d)
    return itens, avisos, res


def test_gate_so_barra_violacao_bloqueante_nova():
    anterior = _retrato(I11=["obra:o2"], I13=["impressao:ia"])
    herdada = _gate(_atual(I11=["obra:o2"], I13=["impressao:ia"]), anterior)
    assert resultado.agrega(herdada[0])[0] == 0
    assert any("I11 herdada" in a for a in herdada[1])
    nova = _gate(_atual(I11=["obra:o2", "obra:o3"], I13=["impressao:ia"]), anterior)
    assert resultado.agrega(nova[0])[0] == 1
    veredito = dict(nova[0])["I11: sobra"]
    assert veredito.estado == "divergente" and "1 violação" in veredito.motivo and "1 herdada" in veredito.motivo


def test_gate_viola_nova_de_aviso_nao_barra():
    anterior = _retrato()
    itens, avisos, _ = _gate(_atual(I6=["impressao:i1"], I12=["indice:x2"]), anterior)
    assert resultado.agrega(itens)[0] == 0
    assert any(a.startswith("I6 espelho presente [aviso]: 1") for a in avisos)


def test_gate_invariante_bloqueante_que_nao_mediu_sai_5():
    atual = _atual()
    atual["I13"] = None
    itens, _, _ = _gate(atual, _retrato())
    assert resultado.agrega(itens)[0] == 5


def test_gate_lista_as_obras_que_pioraram():
    d = _com(obras=[_obra(marcacao="inteira"), _obra("o2", marcacao="inteira")],
             impressoes=[_imp(), _imp("i2", "o2")])
    atual = pa.avaliar_invariantes(d)
    itens, _, _ = pa.aplicar_gate([], [], atual, _retrato(I11=["obra:o1"]), d)
    motivo = dict(itens)["I11: sobra"].motivo
    assert "o2" in motivo and "o1" not in motivo.split("herdada")[0]


def test_gate_com_retrato_os_predicados_de_hoje_viram_aviso_herdado():
    velhos = [("§11 predicado 7: fidelidade", resultado.divergente("21 de classe A")),
              ("§11 predicado 9: veredito da régua vigente", resultado.conforme()),
              ("I13: nenhum derivado anterior depois da promoção",
               resultado.divergente("1069 impressões aposentadas"))]
    itens, avisos, _ = _gate(_atual(), _retrato(), velhos)
    assert resultado.agrega(itens)[0] == 0
    assert any("herdado — §11 predicado 7" in a for a in avisos)
    assert any("herdado — I13" in a for a in avisos)


def test_sem_retrato_o_exit_segue_nos_predicados_de_hoje():
    velhos = [("§11 predicado 7: fidelidade", resultado.divergente("21 de classe A"))]
    itens, avisos, res = _gate(_atual(I11=["obra:o2"]), None, velhos)
    assert itens == velhos and resultado.agrega(itens)[0] == 1
    assert any("sem retrato guardado" in a for a in avisos)
    assert any(a.startswith("I11 sobra [bloqueante]: 1") for a in avisos)
    assert res["I11"]["n"] == 1


def test_sem_retrato_invariante_novo_nao_derruba_o_que_hoje_passa():
    itens, _, _ = _gate(_atual(I1=["obra:o1"]), None, [("I13: x", resultado.conforme())])
    assert resultado.agrega(itens)[0] == 0


# a chamada inteira, com a porta falsa ------------------------------------------------------------------

def _ler(d, retrato=None, fora=()):
    def ler(banco, sql):
        if banco in fora:
            raise pa.Indeterminavel(f"{banco} fora")
        if sql is pa.SQL_COLETA_RAG:
            return {"obras": d["obras"], "impressoes": d["impressoes"], "aposentadas": d["aposentadas"],
                    "total": d["total"]}
        if sql is pa.SQL_COLETA_TRECHOS:
            return list(d["trechos"].values())
        if sql is pa.SQL_COLETA_MOTOR:
            return d["motor"]
        if sql is pa.SQL_I13_RAG:
            return d["i13"]
        if sql is pa.SQL_I13_MOTOR:
            return d["i13_motor"]
        if sql is pa.SQL_ULTIMO_RETRATO:
            return retrato
        raise AssertionError(sql)
    return ler


@pytest.fixture(autouse=True)
def _regua_7(monkeypatch):
    monkeypatch.setattr(pa, "regua_servida", lambda raiz=None: (7, frozenset(), frozenset()))


def test_conferir_invariantes_de_ponta_a_ponta():
    d = _com(obras=[_obra(marcacao="inteira")])
    itens, avisos, res = pa.conferir_invariantes([], [], _ler(d, _retrato()), balde=lambda: d["balde"],
                                                 orfaos=lambda: 0)
    assert res["I11"]["n"] == 1
    assert dict(itens)["I11: sobra"].estado == "divergente"
    assert resultado.agrega(itens)[0] == 1


def test_conferir_invariantes_banco_fora_sai_5():
    d = _base()
    itens, _, res = pa.conferir_invariantes([], [], _ler(d, fora=("motor",)), balde=lambda: d["balde"],
                                            orfaos=lambda: 0)
    assert res is None and resultado.agrega(itens)[0] == 5


def test_conferir_invariantes_balde_fora_avisa_e_nao_derruba():
    d = _base()

    def balde():
        raise pa.Indeterminavel("balde: 401")

    itens, avisos, res = pa.conferir_invariantes([], [], _ler(d, _retrato()), balde=balde, orfaos=lambda: 0)
    assert res["I6"]["n"] == 0 and any("balde: não medido" in a for a in avisos)
    assert resultado.agrega(itens)[0] == 0


def test_o_json_traz_a_contagem_e_as_obras_de_cada_invariante(monkeypatch):
    d = _com(obras=[_obra(marcacao="inteira")])
    monkeypatch.setattr(pa, "medir", lambda *a, **k: ([], [], []))
    saida = io.StringIO()
    with redirect_stdout(saida):
        rc = pa.conferir_acervo(None, "abc1234", como_json=True, ler=_ler(d), balde=lambda: d["balde"],
                                orfaos=lambda: 0)
    doc = json.loads(saida.getvalue())
    assert rc == 0 and doc["invariantes"]["I11"] == {
        "nome": "sobra", "classe": "bloqueante", "n": 1, "obras": ["o1"]}
    assert set(doc["invariantes"]) == set(pa.INVARIANTES) and "chaves" not in doc["invariantes"]["I1"]
    assert doc["invariantes"]["I1"]["n"] == 0
