"""#3324: `acervo listar biblioteca obra --situacao --retrato [--guardar]` — o retrato da biblioteca (arq:0121 §9).

Contrato das colunas e do rodapé, sem banco e sem rede: os dados são os de `predicados_acervo.coletar`
(dicts), a projeção do motor e o gravador são trocados por funções. Prova: uma linha por obra do catálogo
com id, título, situação, exposição, impressão servindo, geração e índice, cobertura e invariantes violados;
o rodapé soma cada entidade e fecha com o total, e escreve a linha que não fecha; `--guardar` grava as duas
tabelas numa transação, só com identidade, e não guarda o retrato que diverge do `--situacao`. Não prova:
o banco e o motor de verdade (a rodada em produção do card).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "bin" / "_release" / "conferir"))
sys.path.insert(0, str(RAIZ / "bin" / "_acervo"))

import predicados_acervo as pa  # noqa: E402
import retrato  # noqa: E402

AGORA = "2026-10-07T22:00:00Z"


def _obra(i, marcacao="transcrita e indexada", retirada=False):
    return {"id": i, "titulo": f"Obra {i}", "retirada": retirada, "tem_autoria": True, "marcacao": marcacao,
            "objeto": f"acervo/sha-{i}", "objeto_id": f"sha-{i}", "ficha_ok": True}


def _imp(i, obra, servivel=True):
    return {"id": i, "obra": obra, "estado": "servindo", "metodo": "a1b2c3d4e5f6", "espelho": True,
            "digest": f"dig-{i}", "regua": "7", "servivel": servivel, "imperfeita": False, "reclamada": False}


def _ix(i, imp, obra, n=3):
    return {"id": i, "imp": imp, "obra": obra, "estado": "servindo", "gran": "trecho", "part": "biblioteca",
            "geracao_servindo": True, "n": n, "h": "h"}


def _dados():
    """Três obras: o1 viva e coberta; o2 viva, exposta só em arquivo, com impressão (viola o I11); o3 retirada."""
    d = {
        "obras": [_obra("o1"), _obra("o2", marcacao="inteira"), _obra("o3", retirada=True)],
        "impressoes": [_imp("i1", "o1"), _imp("i2", "o2")], "aposentadas": [], "total": 3,
        "trechos": {"i1": {"imp": "i1", "n": 3, "h": "h"}, "i2": {"imp": "i2", "n": 0, "h": "z"}},
        "motor": {"geracoes": [{"id": "g1", "particao": "biblioteca", "estado": "servindo", "numero": 1,
                                "embedder": "Qwen/Qwen3-Embedding-0.6B", "dimensao_trecho": "1024",
                                "dimensao_faceta": "256"}],
                  "indices": [_ix("x1", "i1", "o1")], "faceta_alvo_errado": []},
        "i13": {"obra": [], "casa": [], "existentes": ["i1", "i2"]}, "i13_motor": ["i1"],
        "versao": 7, "balde": {"espelhos": {("sha-o1", "dig-i1"), ("sha-o2", "dig-i2")},
                               "objetos": {"acervo/sha-o1", "acervo/sha-o2", "acervo/sha-o3"}},
        "espelhos_orfaos": 0,
    }
    return pa.completar(d)


PROJECAO = {
    "o1": {"obra_id": "o1", "servivel": True, "degrau": "ancorado", "impressao_id": "i1", "geracao": 1,
           "embedder": "Qwen/Qwen3-Embedding-0.6B", "dimensao": 1024, "trechos_com_vetor": 3,
           "trechos_elegiveis": 3},
    "o2": {"obra_id": "o2", "servivel": True, "degrau": "ancorado", "impressao_id": "i2", "geracao": None,
           "embedder": None, "dimensao": None, "trechos_com_vetor": 0, "trechos_elegiveis": 0},
}


def _retrato(d=None, proj=None):
    d = d or _dados()
    return retrato.montar(d, pa.avaliar_invariantes(d), PROJECAO if proj is None else proj, AGORA)


def test_uma_linha_por_obra_com_as_colunas_do_contrato():
    r = _retrato()
    assert [l["obra_id"] for l in r["linhas"]] == ["o1", "o2", "o3"]
    o1 = r["linhas"][0]
    assert o1 == {
        "obra_id": "o1", "titulo": "Obra o1", "situacao": "viva", "exposicao": "trecho",
        "impressao_id": "i1", "impressao_metodo": "a1b2c3d4e5f6", "espelho_qualidade": "servível",
        "geracao": {"numero": 1, "embedder": "Qwen/Qwen3-Embedding-0.6B", "dimensao": 1024},
        "trechos_com_vetor": 3, "trechos_elegiveis": 3, "cobertura": "completa", "invariantes": []}


def test_a_obra_retirada_e_a_sem_indice_entram_com_o_que_tem():
    o2, o3 = _retrato()["linhas"][1:]
    assert o2["geracao"] is None and o2["cobertura"] == "sem índice" and o2["exposicao"] == "arquivo"
    assert o2["invariantes"] == ["I11"]            # exposta só em arquivo, com impressão servindo
    assert o3["situacao"] == "retirada" and o3["impressao_id"] is None
    assert o3["espelho_qualidade"] == "sem impressão servindo" and o3["geracao"] is None


def test_o_cabecalho_diz_base_data_geracao_e_papeis():
    cab = _retrato()["cabecalho"]
    assert cab["base"] == "biblioteca" and cab["tirado_em"] == AGORA
    assert cab["geracao_servindo"] == {"numero": 1, "embedder": "Qwen/Qwen3-Embedding-0.6B",
                                       "dimensao_trecho": "1024", "dimensao_faceta": "256"}
    assert cab["papeis"]["proprietario"] == "dono, sem delegação"
    assert "ti" in cab["papeis"]["custodia"] and "backup" in cab["papeis"]["copia"]


def test_o_rodape_soma_cada_entidade_e_fecha_com_o_total():
    rod = _retrato()["rodape"]
    assert rod["total"] == 3 and rod["fecha"] is True and rod["nao_fecha"] == []
    assert rod["obra"] == {"retirada": 1, "viva": 2}
    assert rod["exposicao"] == {"arquivo": 1, "trecho": 2}
    assert rod["impressao_servindo"] == {"com": 2, "sem": 1}
    assert rod["indice_servindo"] == {"geração 1": 1, "sem impressão servindo": 1, "sem índice": 1}
    assert rod["cobertura"] == {"completa": 1, "sem impressão servindo": 1, "sem índice": 1}
    assert all(sum(rod[e].values()) == 3 for e in
               ("obra", "exposicao", "impressao_servindo", "espelho_qualidade", "indice_servindo", "cobertura"))
    assert rod["invariantes"]["I11"]["n"] == 1 and rod["invariantes"]["I1"]["n"] == 0


def test_o_rodape_escreve_a_linha_que_nao_fecha():
    d = _dados()
    d["total"] = 5                                  # o catálogo tem 5; o retrato leu 3
    rod = _retrato(d)["rodape"]
    assert rod["fecha"] is False
    assert any("obra: soma 3 ≠ 5" in l for l in rod["nao_fecha"])
    assert any("linhas do retrato: 3 ≠ 5" in l for l in rod["nao_fecha"])


def test_o_texto_traz_cabecalho_uma_linha_por_obra_e_rodape():
    texto = retrato.texto(_retrato())
    assert texto.startswith("retrato da biblioteca · 2026-10-07T22:00:00Z")
    assert "geração servindo: 1 (Qwen/Qwen3-Embedding-0.6B, trecho 1024, faceta 256)" in texto
    assert "papéis: proprietario: dono, sem delegação" in texto
    assert texto.count("Obra o") == 3
    assert "violados: I11" in texto and "vet 3/3" in texto
    assert "rodapé · count(*) acervo.obra = 3" in texto and "fecha: sim" in texto


def test_o_texto_escreve_a_linha_que_nao_fecha():
    d = _dados()
    d["total"] = 4
    assert "NÃO FECHA:" in retrato.texto(_retrato(d))


def test_divergencia_entre_o_retrato_e_o_situacao_aparece():
    proj = {**PROJECAO, "o1": {**PROJECAO["o1"], "impressao_id": "outra"}}
    r = _retrato(proj=proj)
    assert any("o1: impressão servindo i1 no retrato, outra no --situacao" in x for x in r["divergencias"])
    assert "DIVERGE do --situacao" in retrato.texto(r)
    assert _retrato()["divergencias"] == []


def test_servivel_que_difere_do_situacao_diverge():
    proj = {**PROJECAO, "o1": {**PROJECAO["o1"], "servivel": False}}
    assert any("servível True no retrato, False no --situacao" in x for x in _retrato(proj=proj)["divergencias"])


# executar -----------------------------------------------------------------------------------------

def _portas(d, proj=None, guardados=None):
    def ler(banco, sql):
        return {pa.SQL_COLETA_RAG: {"obras": d["obras"], "impressoes": d["impressoes"],
                                    "aposentadas": d["aposentadas"], "total": d["total"]},
                pa.SQL_COLETA_TRECHOS: list(d["trechos"].values()), pa.SQL_COLETA_MOTOR: d["motor"],
                pa.SQL_I13_RAG: d["i13"], pa.SQL_I13_MOTOR: d["i13_motor"]}[sql]

    def escrever(sql):
        guardados.append(sql)
        return {"id": "11111111-aaaa", "tirado_em": AGORA, "linhas": len(d["obras"])}

    return {"ler": ler, "balde": lambda: d["balde"], "orfaos": lambda: 0,
            "projecao": lambda: PROJECAO if proj is None else proj, "escrever": escrever, "agora": AGORA}


@pytest.fixture(autouse=True)
def _regua_7(monkeypatch):
    monkeypatch.setattr(pa, "regua_servida", lambda raiz=None: (7, frozenset(), frozenset()))


def test_executar_imprime_e_sai_0_quando_fecha(capsys):
    assert retrato.executar(**_portas(_dados())) == 0
    assert "fecha: sim" in capsys.readouterr().out


def test_executar_json_traz_cabecalho_linhas_e_rodape(capsys):
    assert retrato.executar(quero_json=True, **_portas(_dados())) == 0
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"cabecalho", "linhas", "rodape", "total", "divergencias"} and len(doc["linhas"]) == 3


def test_executar_sai_1_quando_nao_fecha(capsys):
    d = _dados()
    d["total"] = 9
    assert retrato.executar(**_portas(d)) == 1


def test_guardar_grava_as_duas_tabelas_numa_transacao(capsys):
    guardados = []
    rc = retrato.executar(guardar=True, quem="dados@2b7d43b6", **_portas(_dados(), guardados=guardados))
    assert rc == 0 and len(guardados) == 1
    sql = guardados[0]
    assert sql.startswith("begin;") and sql.rstrip().endswith("commit;")
    assert "insert into acervo.retrato (base, tirado_em, tirado_por, cabecalho, rodape, total)" in sql
    assert "insert into acervo.retrato_obra" in sql and "json_to_recordset" in sql
    assert "dados@2b7d43b6" in sql and "'biblioteca'" in sql and AGORA in sql
    assert "retrato guardado: 11111111-aaaa" in capsys.readouterr().err


def test_guardar_sem_identidade_recusa_e_nao_escreve(capsys):
    guardados = []
    rc = retrato.executar(guardar=True, quem="", **_portas(_dados(), guardados=guardados))
    assert rc == 4 and guardados == [] and "PF_CADEIRA" in capsys.readouterr().err


def test_guardar_nao_guarda_o_que_diverge_do_situacao(capsys):
    guardados = []
    proj = {**PROJECAO, "o1": {**PROJECAO["o1"], "impressao_id": "outra"}}
    rc = retrato.executar(guardar=True, quem="dados@x", **_portas(_dados(), proj=proj, guardados=guardados))
    assert rc == 1 and guardados == [] and "não guardei" in capsys.readouterr().err


def test_guardar_pela_metade_sai_1():
    d = _dados()
    portas = _portas(d, guardados=[])
    portas["escrever"] = lambda sql: {"id": "x", "tirado_em": AGORA, "linhas": 1}
    assert retrato.executar(guardar=True, quem="dados@x", **portas) == 1


def test_motor_fora_sai_5(capsys):
    portas = _portas(_dados())

    def fora():
        raise pa.Indeterminavel("estado das obras fora do ar (HTTP 503)")

    portas["projecao"] = fora
    assert retrato.executar(**portas) == 5
    assert "indeterminável" in capsys.readouterr().err


def test_o_sql_nao_quebra_com_aspas_e_cifrao_no_titulo():
    d = _dados()
    d["obras"][0]["titulo"] = "O'Brien $r0$ — \"citação\""
    sql = retrato.sql_guardar(_retrato(d), "dados@x")
    assert "$r1$" in sql                              # a etiqueta escolhida não colide com o título


def test_o_adaptador_do_balde_monta_a_rota_com_e_sem_prefixo():
    sys.path.insert(0, str(RAIZ))
    from recuperacao.adaptadores import motor_acervo_rest
    vistos = []

    def http(rota, **_):
        vistos.append(rota)
        return {"itens": []}

    motor_acervo_rest.baldes_objetos("firma", "espelho/a", http=http)
    motor_acervo_rest.baldes_objetos("pessoal", http=http)
    assert vistos == ["/acervo/baldes/firma/objetos?prefixo=espelho%2Fa", "/acervo/baldes/pessoal/objetos"]


# o ato: sem verbo novo -----------------------------------------------------------------------------

def _listar():
    loader = importlib.machinery.SourceFileLoader("acervo_listar_3324", str(RAIZ / "bin" / "_acervo" / "listar"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("argv", [
    ["obra", "--retrato"],                                   # sem --situacao: o retrato reusa o ato
    ["obra", "--guardar"],                                   # --guardar sem --retrato
    ["obra", "--situacao", "--retrato", "--sobre", "lei"],   # filtro: o retrato é o catálogo inteiro
    ["obra", "--situacao", "--retrato", "--qualidade"],
    ["conceitos", "--retrato"],                              # só vale em obra
])
def test_o_listar_recusa_a_combinacao_errada(argv, capsys):
    with pytest.raises(SystemExit) as e:
        _listar().main(argv)
    assert e.value.code == 2


def test_o_listar_despacha_o_retrato(monkeypatch):
    visto = {}
    monkeypatch.setattr(retrato, "executar", lambda quero_json, guardar: visto.update(j=quero_json, g=guardar) or 0)
    with pytest.raises(SystemExit) as e:
        _listar().main(["obra", "--situacao", "--retrato", "--json", "--guardar"])
    assert e.value.code == 0 and visto == {"j": True, "g": True}


def test_o_uso_documenta_o_retrato():
    fonte = (RAIZ / "bin" / "_acervo" / "listar").read_text(encoding="utf-8")
    uso = fonte.split('USO = """', 1)[1].split('"""', 1)[0]
    assert "--situacao --retrato [--json] [--guardar]" in uso and "count(*) de acervo.obra" in uso
