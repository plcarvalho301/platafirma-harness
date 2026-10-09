"""bin/_motor/kappa.py — o juiz contra a primeira passada do dono (card #3350; padrao protocolo-medicao-rag, «O juiz»).

Funções puras: tabela conhecida para o kappa, intervalo por pergunta, enganosa nos dois sentidos, a marca mais
recente na repetição, divergência por qualidade ou embasamento, tempo e o lote de conferência sem a nota do juiz.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import kappa  # noqa: E402


def test_kappa_de_tabela_conhecida_duas_classes():
    pares = [("s", "s")] * 20 + [("n", "n")] * 15 + [("s", "n")] * 5 + [("n", "s")] * 10
    assert kappa.cohen_kappa(pares) == pytest.approx(0.4)


def test_kappa_de_tabela_conhecida_tres_classes():
    pares = [("a", "a")] * 3 + [("b", "b")] * 3 + [("c", "c")] * 2 + [("a", "b"), ("c", "a")]
    assert kappa.cohen_kappa(pares) == pytest.approx((0.8 - 0.34) / 0.66)


def test_kappa_indefinido_e_none_nunca_concordancia_bruta():
    assert kappa.cohen_kappa([]) is None
    assert kappa.cohen_kappa([("boa", "boa")] * 5) is None


def test_intervalo_cobre_o_ponto_e_reamostra_pergunta():
    rodada = {f"p{i}": [("boa", "boa"), ("parcial", "boa" if i % 3 == 0 else "parcial")] for i in range(19)}
    rodada["p19"] = [("enganosa", "enganosa"), ("boa", "parcial")]
    ponto = kappa.cohen_kappa([p for v in rodada.values() for p in v])
    iv = kappa.bootstrap_por_pergunta(rodada, n=500)
    assert iv["baixo"] <= ponto <= iv["alto"]
    assert iv["reamostras"] == 500
    assert iv == kappa.bootstrap_por_pergunta(rodada, n=500)       # semente fixa: o mesmo intervalo


def test_enganosa_nos_dois_sentidos_com_n():
    pares = [("enganosa", "enganosa"), ("enganosa", "vazia"), ("boa", "enganosa"), ("boa", "boa")]
    assert kappa.enganosa(pares) == {"dono_marcou": 2, "juiz_acompanhou": 1, "juiz_marcou": 2, "dono_confirmou": 1}


def ev(i, tipo, **k):
    return {"id": i, "tipo": tipo, "passada": k.pop("passada", "primeira"), **k}


EVENTOS = [
    ev(1, "marca", resposta_id="r1", qualidade="boa", embasamento=True, ms_ativos=10000),
    ev(2, "marca", resposta_id="r2", qualidade="parcial", embasamento=True, ms_ativos=20000),
    ev(3, "preferencia", pergunta_id="p1", escolha="1", ms_ativos=4000),
    ev(4, "marca", resposta_id="r1", qualidade="parcial", embasamento=True, ms_ativos=8000),     # repetição: vale esta
    ev(5, "exclusao", pergunta_id="p3", motivo="nao-da-sem-a-ordem"),
    ev(6, "marca", resposta_id="r3", qualidade="enganosa", embasamento=False, ms_ativos=30000),
    ev(7, "marca", resposta_id="r4", qualidade="boa", embasamento=True, ms_ativos=12000),
    ev(8, "marca", resposta_id="r3", qualidade="boa", embasamento=True, ms_ativos=1, passada="conferencia"),
]

LOTE = {
    "lote_id": "L", "criterio_versao": "v1", "gabarito_versao_id": "g", "carimbo": {"escritor": {}},
    "corpo": {"lote_id": "L", "criterio_versao": "v1", "passada": "primeira", "perguntas": [
        {"pergunta_id": "p1", "texto": "pergunta 1", "cadeira": "x", "data": "d",
         "respostas": [{"resposta_id": "r1", "texto": "t1", "secoes": []}, {"resposta_id": "r2", "texto": "t2", "secoes": []}]},
        {"pergunta_id": "p2", "texto": "pergunta 2", "cadeira": "x", "data": "d",
         "respostas": [{"resposta_id": "r3", "texto": "t3", "secoes": []}, {"resposta_id": "r4", "texto": "t4", "secoes": []}]},
        {"pergunta_id": "p3", "texto": "pergunta 3", "cadeira": "x", "data": "d",
         "respostas": [{"resposta_id": "r5", "texto": "t5", "secoes": []}, {"resposta_id": "r6", "texto": "t6", "secoes": []}]},
    ]},
    "respostas": [{"resposta_id": f"r{i}", "pergunta_id": f"p{(i + 1) // 2}", "braco": "servido" if i % 2 else "lexico",
                   "secoes": [], "mapa": [], "carimbo": {}} for i in range(1, 7)],
}

JUIZ = {"r1": {"qualidade": "parcial", "embasamento": True}, "r2": {"qualidade": "parcial", "embasamento": False},
        "r3": {"qualidade": "vazia", "embasamento": False}, "r4": {"qualidade": "boa", "embasamento": True},
        "r5": {"qualidade": "boa", "embasamento": True}, "r6": {"qualidade": "boa", "embasamento": True}}


def test_vale_a_marca_mais_recente_da_primeira_passada_e_a_conferencia_nao_entra():
    dono = kappa.marcas_do_dono(EVENTOS)
    assert dono["r1"]["qualidade"] == "parcial" and dono["r1"]["marcas"] == 2
    assert dono["r3"]["qualidade"] == "enganosa"
    assert kappa.excluidas(EVENTOS) == {"p3"}


def test_concordancia_tira_a_excluida_e_diz_quem_ficou_sem_marca():
    dono = kappa.marcas_do_dono(EVENTOS)
    c = kappa.concordancia(LOTE, dono, JUIZ, kappa.excluidas(EVENTOS))
    assert c["n_respostas"] == 4 and c["n_perguntas"] == 2
    assert c["perguntas_excluidas"] == ["p3"] and not c["sem_marca_do_dono"] and not c["sem_marca_do_juiz"]
    assert c["enganosa"] == {"dono_marcou": 1, "juiz_acompanhou": 0, "juiz_marcou": 0, "dono_confirmou": 0}
    assert c["por_grau"]["parcial"] == {"dono": 2, "juiz": 2, "os_dois": 2}


def test_divergencia_e_qualidade_ou_embasamento_e_nao_traz_braco():
    dono = kappa.marcas_do_dono(EVENTOS)
    d = kappa.divergencias(LOTE, dono, JUIZ, kappa.excluidas(EVENTOS))
    assert [(x["resposta_id"], x["o_que_diverge"]) for x in d] == [("r2", ["embasamento"]), ("r3", ["qualidade"])]
    assert "braco" not in json.dumps(d) and "servido" not in json.dumps(d)


def test_tempo_por_resposta_e_por_pergunta():
    dono = kappa.marcas_do_dono(EVENTOS)
    t = kappa.tempo(LOTE, dono, kappa.preferencias(EVENTOS), kappa.excluidas(EVENTOS))
    assert t["por_resposta"]["n"] == 4 and t["por_resposta"]["mediana"] == pytest.approx(16.0)
    assert t["por_resposta"]["p90"] == pytest.approx(30.0)
    assert t["por_pergunta"]["n"] == 2 and t["por_pergunta"]["total"] == pytest.approx(8 + 20 + 4 + 30 + 12)


def test_lote_de_conferencia_so_divergentes_ids_novos_e_sem_nota_do_juiz():
    dono = kappa.marcas_do_dono(EVENTOS)
    divs = kappa.divergencias(LOTE, dono, JUIZ, kappa.excluidas(EVENTOS))
    cont = itertools.count(1)
    env = kappa.lote_de_conferencia(LOTE, divs, "L-conf", lambda: f"re-novo{next(cont)}", "s")
    assert env["passada"] == env["corpo"]["passada"] == "conferencia" and env["criterio_versao"] == "v1"
    ids = [r["resposta_id"] for p in env["corpo"]["perguntas"] for r in p["respostas"]]
    assert sorted(ids) == ["re-novo1", "re-novo2"]
    assert {r["carimbo"]["conferencia_de"] for r in env["respostas"]} == {"r2", "r3"}
    publico = json.dumps(env["corpo"])
    assert "vazia" not in publico and "juiz" not in publico and "braco" not in publico
    assert env["ativo"] is False
