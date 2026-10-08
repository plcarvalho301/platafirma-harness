"""bin/_motor/consulta.py: a consulta montada pelo verbo (card #3360; spec motor-do-conhecimento §2b).

Funções puras e leitura de arquivo, sem rede. O log da porta falso é escrito pelo próprio `oplog.emitir`
(o escritor real), com a forma das linhas de turno e de abertura que o servidor grava
(ops-server/test_turno_texto_porta.py, spec log-de-negocio §3); `rotas-chapeu.json` tem a forma do arquivo
da abertura publicada (cadeira → chapéu → rótulos).
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "lib"))
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import consulta  # noqa: E402
import oplog  # noqa: E402

PEDIDO = "mede o piso de abstenção da geração Nemotron e me diz se ele ainda vale"
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
    "what is the abstention floor for the Nemotron generation?",
])
def test_lint_frase_passa(texto):
    assert consulta.lint(texto) is None


def test_lint_curto_nao_tem_proporcao_a_medir():
    for texto in ("RRF", "piso Nemotron", "embedder bge m3"):
        assert consulta.lint(texto) is None


def test_lint_c_necessidade_em_ingles_com_pedido_em_portugues():
    causa, jeito = consulta.lint("what is the abstention floor of the Nemotron generation?", PEDIDO)
    assert causa == "língua diferente da do pedido"
    assert jeito == "na língua do pedido"


def test_lint_c_sem_pedido_a_vista_nao_dispara():
    assert consulta.lint("what is the abstention floor of the Nemotron generation?", None) is None


def test_lint_c_pedido_em_ingles_nao_dispara():
    assert consulta.lint("what is the abstention floor?", "measure the abstention floor of the new generation") is None


def test_lint_nao_reescreve_nada():
    texto = "UTF-8 decoding truncated multibyte sequence byte boundary"
    consulta.lint(texto)
    assert texto == "UTF-8 decoding truncated multibyte sequence byte boundary"


# --- montagem -----------------------------------------------------------------------------------

ROTULOS = ("Complexidade assintotica", "asymptotic complexity", "big-o", "Pipeline RAG", "rag",
           "retrieval-augmented generation", "Ranqueamento multiestágio", "reranking")


def test_montar_tres_itens_na_ordem_do_contrato():
    ps = consulta.montar(NEC, PEDIDO, ROTULOS)
    assert ps == [NEC, PEDIDO, NEC + " — " + ", ".join(ROTULOS)]


def test_montar_sem_pedido_sai_o_segundo_item():
    assert consulta.montar(NEC, None, ROTULOS) == [NEC, NEC + " — " + ", ".join(ROTULOS)]
    assert consulta.montar(NEC, "   ", ROTULOS) == [NEC, NEC + " — " + ", ".join(ROTULOS)]


def test_montar_sem_chapeu_sai_o_terceiro_item():
    assert consulta.montar(NEC, PEDIDO, ()) == [NEC, PEDIDO]


def test_montar_so_necessidade():
    assert consulta.montar(NEC, None, ()) == [NEC]


def test_montar_corta_o_pedido_em_600_e_os_rotulos_em_8():
    longo = "palavra " * 200
    ps = consulta.montar(NEC, longo, [f"r{i}" for i in range(12)])
    assert len(ps[1]) <= consulta.PEDIDO_MAX
    assert ps[2].endswith("r0, r1, r2, r3, r4, r5, r6, r7")


def test_montar_nao_manda_duas_vezes_o_mesmo_texto():
    assert consulta.montar(NEC, NEC, ()) == [NEC]


def test_montar_nunca_passa_do_teto_da_api():
    assert len(consulta.montar(NEC, PEDIDO, ROTULOS)) <= 4


def test_bloco_consulta_declara_o_que_foi_enviado():
    c = consulta.consulta(NEC, PEDIDO, "porta", "engenharia-de-harness", ROTULOS)
    assert c["fonte_pedido"] == "porta" and c["pedido"] == PEDIDO
    assert c["necessidade"] == NEC and c["chapeu"] == "engenharia-de-harness"
    assert c["rotulos"] == list(ROTULOS) and len(c["perguntas"]) == 3
    assert "lint" not in c


def test_bloco_consulta_sem_pedido_declara_ausente():
    c = consulta.consulta(NEC, None, "porta", None, ())
    assert c["fonte_pedido"] == "ausente" and c["pedido"] is None and c["chapeu"] is None
    assert c["perguntas"] == [NEC]


def test_bloco_consulta_sem_lint_grava_desligado():
    assert consulta.consulta(NEC, None, "porta", None, (), lint_desligado=True)["lint"] == "desligado"


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


# --- pedido do dono, do log da porta ------------------------------------------------------------

SID = "36bd629a-8784-4e24-b34e-ca92000bb7b6"
OUTRA = "11111111-2222-4333-8444-555555555555"
HOJE = date(2026, 10, 8)


def _agora(dia, hora=10, minuto=0):
    return datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=timezone(timedelta(hours=-3)))


def _abertura(pasta, sessao, pergunta, dia=HOJE, hora=10):
    oplog.emitir({"tool": "monta_sessao", "sessao_id": sessao, "chapeu": "engenharia-de-harness",
                  "pergunta": pergunta, "pergunta_bytes": len((pergunta or "").encode())},
                 diretorio_=pasta, agora=_agora(dia, hora))


def _turno(pasta, sessao, texto, dia=HOJE, hora=11, turno_id="T1"):
    oplog.emitir({"tool": "sessao", "evento": "turno", "sessao_id": sessao, "turno_id": turno_id,
                  "turno_fonte": "declarado", "texto": texto},
                 diretorio_=pasta, agora=_agora(dia, hora))


def _giro(pasta, sessao, dia=HOJE, hora=12):
    oplog.emitir({"tool": "repo", "ato": "ler", "sessao_id": sessao, "args": ["x"], "exit_code": 0},
                 diretorio_=pasta, agora=_agora(dia, hora))


def test_pedido_e_a_abertura_quando_so_ela_traz_a_mensagem(tmp_path):
    _abertura(tmp_path, SID, "Card 3360")
    _giro(tmp_path, SID)
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "Card 3360"


def test_pedido_e_o_ultimo_turno_com_texto(tmp_path):
    _abertura(tmp_path, SID, "Card 3360", hora=9)
    _turno(tmp_path, SID, "só a migração agora", hora=11, turno_id="T1")
    _turno(tmp_path, SID, "e depois o verbo", hora=13, turno_id="T2")
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "e depois o verbo"


def test_turno_sem_texto_nao_apaga_o_pedido_anterior(tmp_path):
    """claude.ai da segunda mensagem em diante: o turno sai sem texto (spec log-de-negocio §3)."""
    _abertura(tmp_path, SID, "Card 3360")
    _turno(tmp_path, SID, None, turno_id="T1")
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "Card 3360"


def test_abertura_reaberta_sem_pergunta_nao_vira_pedido(tmp_path):
    _abertura(tmp_path, SID, "Card 3360", hora=9)
    _abertura(tmp_path, SID, None, hora=14)
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "Card 3360"


def test_pedido_de_outra_sessao_nao_entra(tmp_path):
    _abertura(tmp_path, OUTRA, "assunto de outra fita")
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) is None


def test_pedido_acha_o_dia_anterior_quando_hoje_nao_tem_linha_da_sessao(tmp_path):
    _abertura(tmp_path, SID, "Card 3360", dia=HOJE - timedelta(days=1))
    _abertura(tmp_path, OUTRA, "outra", dia=HOJE)
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "Card 3360"


def test_dia_mais_novo_vence_o_mais_velho(tmp_path):
    _abertura(tmp_path, SID, "primeira", dia=HOJE - timedelta(days=2))
    _turno(tmp_path, SID, "a de hoje", dia=HOJE)
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "a de hoje"


def test_pedido_fora_da_janela_de_72_horas_nao_se_acha(tmp_path):
    _abertura(tmp_path, SID, "velha", dia=HOJE - timedelta(days=3))
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) is None


@pytest.mark.parametrize("sessao", [None, "", "-", "  "])
def test_sem_sessao_nao_ha_pedido(tmp_path, sessao):
    _abertura(tmp_path, SID, "Card 3360")
    assert consulta.pedido_da_porta(sessao, tmp_path, HOJE) is None


def test_sem_nenhum_arquivo_de_log_nao_ha_pedido(tmp_path):
    assert consulta.pedido_da_porta(SID, tmp_path / "nao-existe", HOJE) is None


def test_linha_ilegivel_no_log_nao_derruba(tmp_path):
    _abertura(tmp_path, SID, "Card 3360")
    with open(oplog.caminho_do_dia(HOJE, tmp_path), "a", encoding="utf-8") as f:
        f.write("{linha cortada\n")
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "Card 3360"


def test_da_porta_traz_pedido_chapeu_e_cadeira_do_log(tmp_path):
    """No claude.ai a porta nao poe PF_CHAPEU no ambiente do verbo: o chapeu vem da abertura no log."""
    _abertura(tmp_path, SID, "Card 3360", hora=9)
    oplog.emitir({"tool": "repo", "ato": "ler", "sessao_id": SID, "cadeira": "ia", "exit_code": 0},
                 diretorio_=tmp_path, agora=_agora(HOJE, 10))
    assert consulta.da_porta(SID, tmp_path, HOJE) == {"pedido": "Card 3360", "chapeu": "engenharia-de-harness",
                                                      "cadeira": "ia"}


def test_da_porta_chapeu_da_ultima_abertura_e_traco_nao_conta(tmp_path):
    oplog.emitir({"tool": "monta_sessao", "sessao_id": SID, "chapeu": "agente", "pergunta": "a"},
                 diretorio_=tmp_path, agora=_agora(HOJE, 9))
    oplog.emitir({"tool": "monta_sessao", "sessao_id": SID, "chapeu": "-", "pergunta": "b"},
                 diretorio_=tmp_path, agora=_agora(HOJE, 10))
    achado = consulta.da_porta(SID, tmp_path, HOJE)
    assert achado["chapeu"] == "agente" and achado["pedido"] == "b"


def test_da_porta_completa_o_chapeu_com_o_dia_anterior_sem_trocar_o_pedido(tmp_path):
    _abertura(tmp_path, SID, "primeira", dia=HOJE - timedelta(days=1))
    _turno(tmp_path, SID, "a de hoje", dia=HOJE)
    achado = consulta.da_porta(SID, tmp_path, HOJE)
    assert achado["pedido"] == "a de hoje" and achado["chapeu"] == "engenharia-de-harness"


def test_da_porta_sem_sessao_ou_sem_log_devolve_tudo_nulo(tmp_path):
    nulo = {"pedido": None, "chapeu": None, "cadeira": None}
    assert consulta.da_porta(None, tmp_path, HOJE) == nulo
    assert consulta.da_porta(SID, tmp_path / "nao-existe", HOJE) == nulo


def test_lingua_decide_so_pelas_funcionais_exclusivas():
    assert consulta.lingua(NEC) == "pt"
    assert consulta.lingua("what is the abstention floor of the Nemotron generation?") == "en"
    assert consulta.lingua("OpenID Connect Core copyright notice") is None


def test_so_a_mensagem_do_dono_vira_pedido_nunca_a_resposta_ou_o_pacote(tmp_path):
    """c198 (#3345): o pedido vem de `texto`/`pergunta`, nenhum outro campo da linha."""
    oplog.emitir({"tool": "sessao", "evento": "turno", "sessao_id": SID, "turno_id": "T1",
                  "turno_fonte": "declarado", "texto": "a mensagem do dono", "resposta": "x"},
                 diretorio_=tmp_path, agora=_agora(HOJE))
    assert consulta.pedido_da_porta(SID, tmp_path, HOJE) == "a mensagem do dono"
