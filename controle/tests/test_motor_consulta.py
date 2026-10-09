"""bin/_motor/consulta.py: a consulta montada pelo verbo (card #3360, #3364; spec motor-do-conhecimento §2b).

Funções puras e leitura de arquivo, sem rede. rotas-chapeu.json tem a forma do arquivo da
abertura publicada (cadeira → chapéu → rótulos).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "lib"))
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import consulta  # noqa: E402

NEC = "qual piso de abstenção a geração Nemotron usa?"


# --- lint ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("texto,n,numeral", [
    ("SRE overload cascading failures; golden hammer lava flow; xUnit test smells", 3, "três"),
    ("o piso de abstenção; o corte do rerank", 2, "dois"),
    ("como o log grava o prompt | quem lê o log da porta", 2, "dois"),
])
def test_lint_a_assuntos_separados_recusa_e_diz_quantas_chamadas(texto, n, numeral):
    causa, jeito = consulta.lint(texto)
    assert causa == f"{numeral} assuntos em uma chamada"
    assert jeito == f"uma necessidade por chamada; mande {n} chamadas no mesmo lote"
    assert consulta.mensagem_de_recusa(causa, jeito).startswith(f"consulta recusada: {numeral} assuntos em uma chamada")


def test_lint_a_barra_de_alternativa_nao_e_separador_de_assunto():
    assert consulta.lint("como o motor trata entrada e/ou saída vazia no rerank?") is None


@pytest.mark.parametrize("texto", [
    "UTF-8 decoding truncated multibyte sequence byte boundary",
    "golden hammer lava flow antipattern",
    "piso abstenção Nemotron rerank top-k",
])
def test_lint_b_saco_de_palavras_sem_forma_de_frase(texto):
    causa, jeito = consulta.lint(texto)
    assert causa == "sem forma de frase"
    assert jeito == "escreva a necessidade em frase: o que você precisa saber para o próximo ato"


@pytest.mark.parametrize("texto", [
    "como o log da porta grava o prompt do dono?",
    "o que é RRF?",                                   # 4 palavras, 3 funcionais
    "qual piso de abstenção a geração Nemotron usa?",
    "Respondi o gold set todo",                       # prompt do dono (abertura): nunca recusa
    "what is the abstention floor for the Nemotron generation?",  # inglês passa (#1918)
    "what is the abstention floor of the Nemotron generation?",   # inglês passa (#1918)
])
def test_lint_frase_passa(texto):
    assert consulta.lint(texto) is None


def test_lint_curto_nao_tem_proporcao_a_medir():
    for texto in ("RRF", "piso Nemotron", "embedder bge m3"):
        assert consulta.lint(texto) is None


def test_lint_nao_reescreve_nada():
    texto = "UTF-8 decoding truncated multibyte sequence byte boundary"
    consulta.lint(texto)
    assert texto == "UTF-8 decoding truncated multibyte sequence byte boundary"


# --- montagem (#3364) ---------------------------------------------------------------------------

ROTULOS = ("Complexidade assintotica", "asymptotic complexity", "big-o", "Pipeline RAG", "rag",
           "retrieval-augmented generation", "Ranqueamento multiestágio", "reranking")


def test_montar_dois_itens_com_rotulos():
    ps = consulta.montar(NEC, ROTULOS)
    assert ps == [NEC, NEC + ". Buscar também: " + ", ".join(ROTULOS)]


def test_montar_sem_chapeu_so_necessidade():
    assert consulta.montar(NEC, ()) == [NEC]
    assert consulta.montar(NEC, None) == [NEC]


def test_montar_corta_os_rotulos_em_8():
    ps = consulta.montar(NEC, [f"r{i}" for i in range(12)])
    assert ps[1] == NEC + ". Buscar também: r0, r1, r2, r3, r4, r5, r6, r7"


def test_montar_nunca_passa_do_teto_da_api():
    assert len(consulta.montar(NEC, ROTULOS)) <= 2


def test_montar_compativel_com_tres_argumentos():
    assert consulta.montar(NEC, None, ROTULOS) == [NEC, NEC + ". Buscar também: " + ", ".join(ROTULOS)]


def test_bloco_consulta_declara_o_que_foi_enviado():
    c = consulta.consulta(NEC, "engenharia-de-harness", ROTULOS)
    assert "pedido" not in c and "fonte_pedido" not in c
    assert c["necessidade"] == NEC and c["chapeu"] == "engenharia-de-harness"
    assert c["rotulos"] == list(ROTULOS) and len(c["perguntas"]) == 2
    assert "lint" not in c


def test_bloco_consulta_sem_chapeu_declara_nulo():
    c = consulta.consulta(NEC, None, ())
    assert c["chapeu"] is None and c["rotulos"] == []
    assert c["perguntas"] == [NEC]


def test_bloco_consulta_sem_lint_grava_desligado():
    assert consulta.consulta(NEC, None, (), lint_desligado=True)["lint"] == "desligado"


# --- chapéu -------------------------------------------------------------------------------------

def _rotas(tmp_path, tabela):
    (tmp_path / "rotas-chapeu.json").write_text(json.dumps(tabela, ensure_ascii=False), encoding="utf-8")
    return tmp_path


TABELA = {"ia": {"engenharia-de-harness": list(ROTULOS) + ["Juiz-modelo", "LLM-as-a-judge", "rag"],
                 "agente": ["Loop agêntico"]},
          "dados": {"governanca": ["Governança de dados"]}}


def test_rotulos_do_chapeu_os_oito_primeiros(tmp_path):
    r = consulta.rotulos_do_chapeu("ia", "engenharia-de-harness", _rotas(tmp_path, TABELA))
    assert r == ROTULOS and len(r) == consulta.MAX_ROTULOS


def test_rotulos_do_chapeu_nao_repete(tmp_path):
    t = {"ia": {"x": ["a", "b", "a", " b ", "c"]}}
    assert consulta.rotulos_do_chapeu("ia", "x", _rotas(tmp_path, t)) == ("a", "b", "c")


@pytest.mark.parametrize("cadeira,chapeu", [
    ("ia", None), ("ia", ""), ("ia", "inexistente"), ("inexistente", "agente"), (None, "agente"), ("-", "agente"),
])
def test_rotulos_do_chapeu_sem_resposta_e_vazio(tmp_path, cadeira, chapeu):
    assert consulta.rotulos_do_chapeu(cadeira, chapeu, _rotas(tmp_path, TABELA)) == ()


def test_rotulos_do_chapeu_sem_arquivo_ou_arquivo_quebrado(tmp_path):
    assert consulta.rotulos_do_chapeu("ia", "agente", tmp_path) == ()
    (tmp_path / "rotas-chapeu.json").write_text("{não é json", encoding="utf-8")
    assert consulta.rotulos_do_chapeu("ia", "agente", tmp_path) == ()


def test_rotulos_do_chapeu_le_da_abertura_publicada_pelo_ambiente(tmp_path, monkeypatch):
    abertura = tmp_path / "current" / "abertura"
    abertura.mkdir(parents=True)
    _rotas(abertura, TABELA)
    monkeypatch.setenv("PF_ABERTURA_DIR", str(tmp_path))
    assert consulta.rotulos_do_chapeu("ia", "agente") == ("Loop agêntico",)


@pytest.mark.parametrize("valor,esperado", [
    ("engenharia-de-harness", "engenharia-de-harness"), ("-", None), ("", None), ("  ", None),
])
def test_chapeu_vestido_fallback_e_nulo(valor, esperado):
    assert consulta.chapeu_vestido({"PF_CHAPEU": valor}) == esperado
    assert consulta.chapeu_vestido({}) is None


def test_lingua_decide_so_pelas_funcionais_exclusivas():
    assert consulta.lingua(NEC) == "pt"
    assert consulta.lingua("what is the abstention floor of the Nemotron generation?") == "en"
    assert consulta.lingua("OpenID Connect Core copyright notice") is None
