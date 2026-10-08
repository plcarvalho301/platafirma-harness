"""metrica com fonte (card #3353): `dia` e `verbos` leem a partição `log` para todo dia fechado, `turnos` lê D5.8, e
`eventos`, `ate-acerto`, `tateio`, `casos` e `comportamento` seguem no bruto, com «fonte: bruto» (D5.9).

Tudo contra uma API falsa (ou um servidor HTTP de loopback) e uma pasta em tmp_path: sem a porta, sem o banco e sem
o log real. O que não se prova aqui é o SQL de D5.7 e D5.8, que o Postgres executa; a conferência com o bruto de
verdade (`metrica dia 2026-09-23` nas duas fontes) sai no relato do card.
"""
import http.server
import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
from datetime import date
from pathlib import Path

import pytest

import oplog
import oplog_extracao as ex

RAIZ = Path(__file__).resolve().parents[2]
METRICA = RAIZ / "bin" / "metrica"
_spec = importlib.util.spec_from_loader("metrica_fonte", importlib.machinery.SourceFileLoader("metrica_fonte", str(METRICA)))
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)
particao = m.particao

DIA = "2026-09-23"
HOJE = date(2026, 10, 8)
SESSAO = "8f576862-23dd-4880-856f-4c9353096ee1"
VERSAO = "3f2a9c1b7d40"


# --- andaime --------------------------------------------------------------------------------------

def linha_dia(dia, cobertura="completo", motivo=None, versao=VERSAO):
    passada = None if cobertura == "ausente" else {
        "id": "7d0c0f3e-0000-4000-8000-000000000001", "versao_extrator": versao, "linhas_lidas": 12,
        "linhas_legiveis": 12, "linhas_ilegiveis": 0, "eventos_novos": 12, "eventos_existentes": 0, "amostra_n": 4}
    return {"dia": dia, "cobertura": cobertura, "motivo": motivo, "versao_extrator": None if passada is None else versao,
            "arquivo": f"ops-{dia}.jsonl", "bytes": 100, "sha256": "a" * 64, "passada": passada}


def serie(tool, ato, classe, origem, n, **mais):
    return {"chave": {"tool": tool, "ato": ato, "classe": classe, "origem": origem, **mais}, "n": n}


class ApiFalsa:
    """O que a API devolve de D5.5, D5.7 e D5.8. Dia que ela não conhece sai como o serviço o devolve: ausente,
    `nao_extraido`."""

    def __init__(self, dias=None, giros=(), turnos=None, erro=None):
        self.dias, self.giros, self.turnos, self.erro = dias or {}, list(giros), turnos, erro
        self.chamadas = []

    def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
        self.chamadas.append((metodo, caminho, dict(params or {})))
        if self.erro:
            raise self.erro
        if caminho == "/acervo/log/dias":
            itens = [self.dias.get(d) or linha_dia(d, "ausente", "nao_extraido")
                     for d in particao.dias_entre(params["desde"], params["ate"])]
            return 200, {"itens": itens}
        if caminho == "/acervo/log/giros/medida":
            return 200, {"fonte": "partição", "series": self.giros}
        if caminho == "/acervo/log/turnos/medida":
            return 200, self.turnos
        raise AssertionError(caminho)

    def medidas(self):
        return [c for c in self.chamadas if c[1].endswith("/medida")]


def roda(monkeypatch, capsys, api, *args, hoje=HOJE, ausente=lambda d: False):
    monkeypatch.setattr(m, "_api", lambda: api)
    monkeypatch.setattr(m, "_hoje", lambda: hoje)
    monkeypatch.setattr(m, "_bruto_ausente", ausente)
    codigo = m.main(["metrica", *args])
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def bruto_em(monkeypatch, pasta):
    """Aponta a leitura do bruto de `metrica` para uma pasta em tmp."""
    original = m.FonteJsonl
    monkeypatch.setattr(m, "FonteJsonl", lambda: original(str(pasta)))
    monkeypatch.setattr(m, "LOG_OPS", str(pasta))


def _ts(n):
    return f"{DIA}T10:{n:02d}:00.000-03:00"


def _dia_misto(pasta, dia=DIA):
    """Um dia de bruto com tudo que importa à conta: linha antiga sem classe nem origem, linha nova com as duas, a
    sonda, a negada pelo PEP, e as linhas que têm `tool` mas não são giro na partição (abertura e consulta)."""
    linhas = [
        {"ts": _ts(0), "cadeira": "ti", "ordem_id": "o1", "sessao_id": SESSAO, "tool": "acervo", "ato": "ler", "exit_code": 0},
        {"ts": _ts(1), "cadeira": "ti", "ordem_id": "o1", "sessao_id": SESSAO, "tool": "acervo", "ato": "ler", "exit_code": 1},
        {"ts": _ts(2), "cadeira": "ti", "ordem_id": "o1", "sessao_id": SESSAO, "tool": "repo", "ato": "commitar", "exit_code": 3},
        {"ts": _ts(3), "cadeira": "ti", "ordem_id": "o1", "sessao_id": SESSAO, "tool": "repo", "ato": "commitar", "exit_code": 2},
        {"ts": _ts(4), "cadeira": "fabrica", "ordem_id": "o2", "sessao_id": SESSAO, "tool": "mesa", "ato": "ver", "exit_code": 0,
         "classe": "ok", "origem": "cadeira", "evento_id": "0198a000-0000-7000-8000-000000000001", "schema_v": 1},
        {"ts": _ts(5), "tool": "sessao", "exit_code": 0},                                              # a sonda
        {"ts": _ts(6), "cadeira": "ti", "ordem_id": "o1", "sessao_id": SESSAO, "tool": "acervo", "ato": "ler",
         "evento": "pep_negou", "exit_code": None},                                                    # negada pelo PEP
        {"ts": _ts(7), "cadeira": "ti", "ordem_id": "o3", "sessao_id": SESSAO, "tool": "monta_sessao", "exit_code": 0},
        {"ts": _ts(8), "cadeira": "ti", "ordem_id": "o3", "sessao_id": SESSAO, "tool": "motor", "evento": "consulta",
         "query": "q", "exit_code": 0},
        {"ts": _ts(9), "tool": "-", "evento": "http_req", "path": "/mcp"},
        "isto nao e json",
    ]
    corpo = "\n".join(l if isinstance(l, str) else json.dumps(l) for l in linhas) + "\n"
    (pasta / oplog.nome_do_dia(dia)).write_text(corpo, encoding="utf-8")


def json_de(saida):
    return json.loads(saida)


# --- metrica dia: a partição ---------------------------------------------------------------------

def test_dia_fechado_le_a_particao_e_diz_fonte_versao_e_cobertura(monkeypatch, capsys):
    api = ApiFalsa({DIA: linha_dia(DIA)}, [
        serie("acervo", "ler", "ok", "cadeira", 100), serie("acervo", "ler", "negativa", "cadeira", 7),
        serie("repo", "commitar", "execucao", "cadeira", 3), serie("repo", "commitar", "gramatica", "cadeira", 2),
        serie("sessao", None, "ok", "sonda", 1440), serie("monta_sessao", None, "ok", "agente", 5),
        serie("acervo", "ler", "negada", "cadeira", 4)])
    codigo, saida, _ = roda(monkeypatch, capsys, api, "dia", DIA)
    r = json_de(saida)
    assert codigo == 0
    assert r["fonte"] == "partição" and r["versao_extrator"] == VERSAO
    assert [(c["dia"], c["cobertura"], c["motivo"]) for c in r["cobertura"]] == [(DIA, "completo", None)]
    assert r["cobertura"][0]["passada"]["linhas_lidas"] == 12            # as contagens que fecham a conta do dia
    assert r["total"] == {"giros": 1561, "erros": 9, "negativas": 7,
                          "por_origem": {"sonda": 1440, "cadeira": 116, "agente": 5}}
    assert r["giros_por_tool_e_classe"]["acervo:ok"] == 100 and r["giros_por_tool_e_classe"]["sessao:ok"] == 1440
    assert r["giros_por_classe"]["negada"] == 4
    assert r["erros_por_verbo"]["repo"] == {"total": 5, "por_ato": {"commitar": 5}}
    assert r["erros_por_verbo"]["acervo"] == {"total": 4, "por_ato": {"ler": 4}}      # a negada é erro; a negativa, não
    assert r["regra_de_erro"] == {"erro": ["gramatica", "negada", "execucao", "interrompida"],
                                  "fora_do_erro": ["ok", "negativa"]}
    assert set(r["so_no_bruto"]) == {"giros_por_fita", "profundidade_de_cadeia", "giros_de_help"}
    assert api.medidas() == [("GET", "/acervo/log/giros/medida",
                              {"desde": DIA, "ate": DIA, "por": "tool,ato,classe,origem", "medida": "contagem"})]


def test_a_sonda_sai_separada_da_cadeira(monkeypatch, capsys):
    api = ApiFalsa({DIA: linha_dia(DIA)}, [serie("sessao", None, "ok", "sonda", 1440), serie("acervo", "ler", "ok", "cadeira", 9)])
    r = json_de(roda(monkeypatch, capsys, api, "dia", DIA)[1])
    assert r["giros_por_origem"] == {"sonda": 1440, "cadeira": 9}
    assert r["total"]["por_origem"]["cadeira"] == 9


@pytest.mark.parametrize("linha, bruto_sem_arquivo, motivo", [
    (None, True, "sem_arquivo"),                                    # a API não conhece o dia, e o arquivo não existe
    (None, False, "nao_extraido"),                                  # a API não conhece o dia, e o arquivo existe
    (linha_dia(DIA, "ausente", "nao_extraido"), True, "sem_arquivo"),
    (linha_dia(DIA, "ausente", "nao_extraido"), False, "nao_extraido"),
    (linha_dia(DIA, "ausente", "sem_arquivo"), False, "sem_arquivo"),     # o extrator declarou o dia ausente
    (linha_dia(DIA, "ausente", "extracao_falhou"), True, "extracao_falhou"),     # a passada reprovou: o motivo é dele
])
def test_dia_sem_passada_sai_ausente_com_o_motivo_e_sem_uma_contagem(monkeypatch, capsys, linha, bruto_sem_arquivo, motivo):
    api = ApiFalsa({DIA: linha} if linha else {}, [serie("acervo", "ler", "ok", "cadeira", 999)])
    codigo, saida, _ = roda(monkeypatch, capsys, api, "dia", DIA, ausente=lambda d: bruto_sem_arquivo)
    r = json_de(saida)
    assert codigo == 0 and r["fonte"] == "partição"
    assert r["resultado"] == "ausente" and r["motivo"] == motivo
    assert r["cobertura"] == [{"dia": DIA, "cobertura": "ausente", "motivo": motivo, "versao_extrator": None}]
    assert "total" not in r and not any(k.startswith("giros_por") for k in r), "ausente nunca sai zero nem número"
    assert api.medidas() == [], "dia sem passada não pede a medida"


def test_dia_sem_arquivo_de_um_dia_que_nunca_existiu_diz_sem_arquivo_no_resumo(monkeypatch, capsys):
    codigo, saida, _ = roda(monkeypatch, capsys, ApiFalsa(), "dia", "2026-09-10", "--resumo", ausente=lambda d: True)
    assert codigo == 0
    assert "fonte: partição" in saida and "ausente (sem_arquivo)" in saida and "dia sem passada não é zero" in saida


def test_dia_parcial_tem_numero_e_a_cobertura_diz_parcial(monkeypatch, capsys):
    api = ApiFalsa({DIA: linha_dia(DIA, "parcial")}, [serie("acervo", "ler", "ok", "cadeira", 3)])
    r = json_de(roda(monkeypatch, capsys, api, "dia", DIA)[1])
    assert r["cobertura"][0]["cobertura"] == "parcial" and r["total"]["giros"] == 3


def test_dia_com_cadeira_filtra_a_serie_pela_chave(monkeypatch, capsys):
    api = ApiFalsa({DIA: linha_dia(DIA)}, [serie("acervo", "ler", "ok", "cadeira", 5, cadeira="ti"),
                                           serie("acervo", "ler", "ok", "cadeira", 7, cadeira="fabrica")])
    r = json_de(roda(monkeypatch, capsys, api, "dia", DIA, "--cadeira", "ti")[1])
    assert r["total"]["giros"] == 5 and r["cadeira"] == "ti"
    assert api.medidas()[0][2]["por"] == "tool,ato,classe,origem,cadeira"


def test_dia_resumo_diz_a_fonte_o_extrator_e_o_que_so_o_bruto_responde(monkeypatch, capsys):
    api = ApiFalsa({DIA: linha_dia(DIA)}, [serie("repo", "commitar", "execucao", "cadeira", 3), serie("acervo", "ler", "ok", "cadeira", 4)])
    saida = roda(monkeypatch, capsys, api, "dia", DIA, "--resumo")[1]
    assert f"fonte: partição · extrator {VERSAO}" in saida and "cobertura: completo" in saida
    assert "7 giros · 3 erros · 0 negativas" in saida and "só no bruto (--fonte bruto): giros_por_fita" in saida


# --- metrica dia: o bruto, e a mesma conta nas duas fontes -----------------------------------------

def test_dia_aberto_sem_fonte_vai_ao_bruto_e_nao_toca_a_api(monkeypatch, capsys, tmp_path):
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    api = ApiFalsa(erro=AssertionError("o dia aberto não pede a partição"))
    codigo, saida, _ = roda(monkeypatch, capsys, api, "dia", DIA, hoje=date.fromisoformat(DIA))
    r = json_de(saida)
    assert codigo == 0 and r["fonte"] == "bruto" and api.chamadas == []
    assert r["total"]["giros"] > 0 and r["linhas_ilegiveis"] == 1


def test_as_duas_fontes_dao_a_mesma_conta_de_giros_por_tool_e_classe(monkeypatch, capsys, tmp_path):
    """A conferência do card: o bruto e a partição, com a mesma regra de giro, de classe e de origem. A série da
    «partição» sai do que o extrator levaria ao serviço para o mesmo arquivo."""
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    do_bruto = json_de(roda(monkeypatch, capsys, ApiFalsa(), "dia", DIA, "--fonte", "bruto")[1])

    series = {}
    for item in ex.extrair(DIA, tmp_path).itens:
        if item["evento"]["tipo"] == "giro":
            g = item["giro"]
            chave = (g["tool"], g["ato"], g["classe"], item["evento"]["origem"])
            series[chave] = series.get(chave, 0) + 1
    api = ApiFalsa({DIA: linha_dia(DIA)}, [serie(*k, n) for k, n in series.items()])
    da_particao = json_de(roda(monkeypatch, capsys, api, "dia", DIA, "--fonte", "particao")[1])

    assert do_bruto["fonte"] == "bruto" and da_particao["fonte"] == "partição"
    for chave in ("giros_tipo_giro", "giros_por_tool_e_classe", "giros_por_classe", "giros_por_tool", "giros_por_origem"):
        assert do_bruto[chave] == da_particao[chave], chave
    assert do_bruto["giros_por_tool_e_classe"] == {"acervo:negada": 1, "acervo:negativa": 1, "acervo:ok": 1, "mesa:ok": 1,
                                                   "repo:execucao": 1, "repo:gramatica": 1, "sessao:ok": 1}
    assert do_bruto["giros_por_origem"] == {"cadeira": 6, "sonda": 1}
    # O bruto de antes conta toda linha com `tool`; a partição só o que é giro. A diferença são a abertura e a
    # consulta ao motor, e vem dita, não escondida.
    assert do_bruto["total"]["giros"] - do_bruto["giros_tipo_giro"] == 2


def test_contas_do_bruto_nao_conta_o_giro_que_o_extrator_nao_traduz():
    giros = [{"bruto": {"tool": "acervo", "ato": "ler", "exit_code": 0}},
             {"bruto": {"tool": "a b", "exit_code": 0}}]                 # tool fora da forma: o extrator recusa o dia
    r = particao.contas_do_bruto(giros)
    assert r["giros_por_tool_e_classe"] == {"acervo:ok": 1} and r["sem_traducao"] == {"(tool fora da forma)": 1}


def test_dia_do_bruto_no_resumo_diz_a_fonte(monkeypatch, capsys, tmp_path):
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    saida = roda(monkeypatch, capsys, ApiFalsa(), "dia", DIA, "--fonte", "bruto", "--resumo")[1]
    assert saida.startswith(f"== metrica dia — {DIA} · fonte: bruto ==")


def test_sessao_ou_azp_sem_fonte_levam_um_dia_fechado_ao_bruto(monkeypatch, capsys, tmp_path):
    """Identidade só existe no bruto (arq:0123 regra 8): quem a pede não leva um erro, leva o bruto."""
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    api = ApiFalsa(erro=AssertionError("sessão não existe na partição"))
    codigo, saida, _ = roda(monkeypatch, capsys, api, "dia", DIA, "--sessao", SESSAO[:8])
    assert codigo == 0 and json_de(saida)["fonte"] == "bruto" and api.chamadas == []


# --- metrica verbos -------------------------------------------------------------------------------

def _verbos_api():
    return ApiFalsa({"2026-09-22": linha_dia("2026-09-22"), DIA: linha_dia(DIA, "parcial")}, [
        serie("acervo", "ler", "ok", "cadeira", 90), serie("acervo", "ler", "execucao", "cadeira", 10),
        serie("repo", "commitar", "ok", "cadeira", 40), serie("repo", "commitar", "gramatica", "cadeira", 10),
        serie("repo", "pr-abrir", "negativa", "cadeira", 2),
        serie("malote", None, "ok", "cadeira", 500), serie("ler_arquivo", None, "gramatica", "cadeira", 5),
        serie("ler_arquivo", None, "ok", "cadeira", 95)])


def test_verbos_da_particao_numa_janela_com_dia_ausente(monkeypatch, capsys):
    api = _verbos_api()
    codigo, saida, _ = roda(monkeypatch, capsys, api, "verbos", "--desde", "2026-09-22", "--ate", "2026-09-24")
    r = json_de(saida)
    assert codigo == 0 and r["fonte"] == "partição" and r["versoes_extrator"] == [VERSAO]
    assert r["dias"] == ["2026-09-22", DIA, "2026-09-24"] and r["dias_sem_log"] == ["2026-09-24"]
    assert [(c["dia"], c["cobertura"], c["motivo"]) for c in r["cobertura"]] == [
        ("2026-09-22", "completo", None), (DIA, "parcial", None), ("2026-09-24", "ausente", "nao_extraido")]
    assert list(r["por_verbo"]) == ["acervo", "repo"]                     # erros desc, e em empate o de mais giros
    assert r["por_verbo"]["acervo"] == {"giros": 100, "erros": 10, "taxa": 0.1, "gramatica": 0, "execucao": 10,
                                        "negativa": 0, "negada": 0, "interrompida": 0}
    assert r["por_verbo"]["repo"]["erros"] == 10 and r["por_verbo"]["repo"]["negativa"] == 2
    assert r["por_verbo"]["repo"]["taxa"] == round(10 / 52, 4)
    assert set(r["transporte"]) == {"malote", "ler_arquivo"} and "malote" not in r["por_verbo"]
    assert r["total"] == {"verbos": 2, "giros": 152, "erros": 20, "taxa": round(20 / 152, 4)}
    assert "giros_distintos" in r["so_no_bruto"] and "ajuda" in r["so_no_bruto"]
    assert api.medidas()[0][2] == {"desde": "2026-09-22", "ate": "2026-09-24", "por": "tool,ato,classe", "medida": "contagem"}


def test_verbos_csv_tem_as_colunas_da_particao(monkeypatch, capsys):
    codigo, saida, _ = roda(monkeypatch, capsys, _verbos_api(), "verbos", "--desde", "2026-09-22", "--ate", DIA, "--csv")
    linhas = saida.splitlines()
    assert codigo == 0 and linhas[0] == ",".join(particao.COLS_VERBOS_PARTICAO)
    assert linhas[1].split(",")[:4] == ["acervo", "100", "10", "0.1"]
    assert linhas[2].split(",")[:4] == ["repo", "52", "10", str(round(10 / 52, 4))]


def test_verbos_resumo_lista_o_dia_ausente_e_o_que_so_o_bruto_responde(monkeypatch, capsys):
    saida = roda(monkeypatch, capsys, _verbos_api(), "verbos", "--desde", "2026-09-22", "--ate", "2026-09-24", "--resumo")[1]
    assert "fonte: partição" in saida and "2026-09-24  ausente (nao_extraido)" in saida
    assert "só no bruto (--fonte bruto): giros_distintos" in saida


def test_verbos_sem_nenhum_dia_na_particao_e_ausente_e_nao_pede_a_medida(monkeypatch, capsys):
    api = ApiFalsa(giros=[serie("acervo", "ler", "ok", "cadeira", 1)])
    codigo, saida, _ = roda(monkeypatch, capsys, api, "verbos", "--desde", "2026-09-01", "--ate", "2026-09-03")
    r = json_de(saida)
    assert codigo == 0 and r["resultado"] == "ausente" and "total" not in r and "por_verbo" not in r
    assert len(r["dias_sem_log"]) == 3 and api.medidas() == []


def test_verbos_de_hoje_sem_fonte_le_o_bruto(monkeypatch, capsys, tmp_path):
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    api = ApiFalsa(erro=AssertionError("só o dia aberto: o bruto responde"))
    codigo, saida, _ = roda(monkeypatch, capsys, api, "verbos", DIA, hoje=date.fromisoformat(DIA))
    r = json_de(saida)
    assert codigo == 0 and r["fonte"] == "bruto" and "taxa_distinta" in next(iter(r["por_verbo"].values()))


def test_verbos_do_bruto_no_resumo_diz_a_fonte(monkeypatch, capsys, tmp_path):
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    saida = roda(monkeypatch, capsys, ApiFalsa(), "verbos", DIA, "--fonte", "bruto", "--resumo")[1]
    assert f"== metrica verbos — {DIA} · fonte: bruto ==" in saida


def test_janela_com_dia_aberto_e_fechado_vai_a_particao_e_o_aberto_sai_ausente(monkeypatch, capsys):
    api = ApiFalsa({"2026-10-07": linha_dia("2026-10-07")}, [serie("acervo", "ler", "ok", "cadeira", 5)])
    r = json_de(roda(monkeypatch, capsys, api, "verbos", "--desde", "2026-10-07", "--ate", "2026-10-08")[1])
    assert r["fonte"] == "partição"
    assert r["cobertura"][1] == {"dia": "2026-10-08", "cobertura": "ausente", "motivo": "dia_aberto", "versao_extrator": None}
    assert api.chamadas[0] == ("GET", "/acervo/log/dias", {"desde": "2026-10-07", "ate": "2026-10-07"})


# --- metrica turnos -------------------------------------------------------------------------------

def _turnos(*fontes):
    series = [{"chave": {"turno_fonte": f, "superficie": s}, "giros_por_turno": {"1": 3, "2-5": 9},
               "turnos_por_sessao": {"1": 2}, "sessoes": 2, "turnos": 12, "ajuste": ajuste}
              for f, s, ajuste in fontes]
    return {"fonte": "partição", "desde": "2026-10-07", "ate": "2026-10-07", "cobertura": [], "giros_sem_turno": 41,
            "series": series}


def test_turnos_sem_dia_le_ontem_e_mantem_as_series_separadas_por_turno_fonte(monkeypatch, capsys):
    api = ApiFalsa({"2026-10-07": linha_dia("2026-10-07")},
                   turnos=_turnos(("hook", "claude-code", None), ("transcript", "claude.ai", "+1 giro por turno"),
                                  ("gap", "nao_declarada", None)))
    codigo, saida, _ = roda(monkeypatch, capsys, api, "turnos")
    r = json_de(saida)
    assert codigo == 0 and r["fonte"] == "partição" and r["dia"] == "2026-10-07"
    assert r["turno_fontes"] == ["gap", "hook", "transcript"] and r["soma_entre_fontes"] == "nunca"
    assert all("turno_fonte" in s["chave"] for s in r["series"]) and len(r["series"]) == 3
    assert r["giros_sem_turno"] == 41 and r["por"] == ["superficie"]
    assert api.medidas() == [("GET", "/acervo/log/turnos/medida", {"desde": "2026-10-07", "ate": "2026-10-07", "por": "superficie"})]


def test_turnos_de_hoje_sai_ausente_dia_aberto_sem_serie(monkeypatch, capsys):
    api = ApiFalsa(turnos=_turnos(("hook", "claude-code", None)))
    r = json_de(roda(monkeypatch, capsys, api, "turnos", "2026-10-08")[1])
    assert r["resultado"] == "ausente" and r["cobertura"][0]["motivo"] == "dia_aberto" and "series" not in r
    assert api.medidas() == []


def test_turnos_por_cadeira_e_resumo(monkeypatch, capsys):
    api = ApiFalsa({"2026-10-07": linha_dia("2026-10-07")}, turnos=_turnos(("hook", "claude-code", None), ("runner", "agente", None)))
    saida = roda(monkeypatch, capsys, api, "turnos", "2026-10-07", "--por", "cadeira,dia", "--resumo")[1]
    assert api.medidas()[0][2]["por"] == "cadeira,dia"
    assert "fonte: partição" in saida and "turno_fonte=hook" in saida and "turno_fonte=runner" in saida
    assert "séries de turno_fonte diferentes não se somam" in saida


def test_turnos_serie_sem_turno_fonte_e_contrato_violado_e_nao_sai_numero(monkeypatch, capsys):
    ruim = _turnos(("hook", "claude-code", None))
    ruim["series"].append({"chave": {"superficie": "x"}, "giros_por_turno": {}, "turnos_por_sessao": {}})
    api = ApiFalsa({"2026-10-07": linha_dia("2026-10-07")}, turnos=ruim)
    codigo, saida, err = roda(monkeypatch, capsys, api, "turnos", "2026-10-07")
    assert codigo == 5 and saida == "" and "turno_fonte" in err and "Traceback" not in err


@pytest.mark.parametrize("args", [
    ["--fonte", "bruto"], ["--cadeira", "ti"], ["--sessao", "abc"], ["--azp", "x"], ["--por", "tool"], ["--tipo", "giro"]])
def test_turnos_recusa_o_que_nao_filtra_com_exit_2_e_o_caminho(monkeypatch, capsys, args):
    api = ApiFalsa(erro=AssertionError("uso errado não toca a API"))
    codigo, saida, err = roda(monkeypatch, capsys, api, "turnos", "2026-10-07", *args)
    assert codigo == 2 and saida == "" and err.startswith("erro: metrica") and "corrija:" in err


# --- os atos do bruto, e as recusas ---------------------------------------------------------------

@pytest.mark.parametrize("ato", ["eventos", "ate-acerto", "tateio", "casos"])
def test_atos_que_leem_argumento_seguem_no_bruto_e_dizem_fonte_bruto(monkeypatch, capsys, tmp_path, ato):
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    api = ApiFalsa(erro=AssertionError(f"{ato} não lê a partição"))
    codigo, saida, _ = roda(monkeypatch, capsys, api, ato, DIA)
    assert codigo == 0 and json_de(saida)["fonte"] == "bruto" and api.chamadas == []


def test_comportamento_diz_fonte_bruto_no_json_e_no_texto(monkeypatch, capsys, tmp_path):
    _dia_misto(tmp_path)
    bruto_em(monkeypatch, tmp_path)
    api = ApiFalsa(erro=AssertionError("comportamento não lê a partição"))
    assert json_de(roda(monkeypatch, capsys, api, "comportamento", DIA)[1])["fonte"] == "bruto"
    assert "Fonte: bruto" in roda(monkeypatch, capsys, api, "comportamento", DIA, "--resumo")[1]


@pytest.mark.parametrize("ato", ["eventos", "ate-acerto", "tateio", "casos", "comportamento"])
def test_fonte_particao_nos_atos_do_bruto_e_exit_2_com_o_caminho(monkeypatch, capsys, ato):
    codigo, saida, err = roda(monkeypatch, capsys, ApiFalsa(), ato, DIA, "--fonte", "particao")
    assert codigo == 2 and saida == "" and "D5.9" in err and f"metrica {ato}" in err and "corrija:" in err


def test_fonte_desconhecida_e_por_fora_de_turnos_sao_exit_2(monkeypatch, capsys):
    codigo, _, err = roda(monkeypatch, capsys, ApiFalsa(), "dia", DIA, "--fonte", "nuvem")
    assert codigo == 2 and "fonte desconhecida 'nuvem'" in err and "particao, bruto" in err
    codigo, _, err = roda(monkeypatch, capsys, ApiFalsa(), "dia", DIA, "--por", "tool")
    assert codigo == 2 and "--por so vale em `turnos`" in err


def test_sessao_com_fonte_particao_explicita_e_exit_2_e_diz_onde_ela_existe(monkeypatch, capsys):
    codigo, _, err = roda(monkeypatch, capsys, ApiFalsa(), "dia", DIA, "--fonte", "particao", "--sessao", "abc")
    assert codigo == 2 and "--sessao/--azp nao existem na particao" in err and "--fonte bruto" in err


def test_aceita_a_grafia_com_cedilha_na_fonte(monkeypatch, capsys):
    api = ApiFalsa({DIA: linha_dia(DIA)}, [serie("acervo", "ler", "ok", "cadeira", 1)])
    assert json_de(roda(monkeypatch, capsys, api, "dia", DIA, "--fonte", "partição")[1])["fonte"] == "partição"


# --- a partição fora do ar ------------------------------------------------------------------------

@pytest.mark.parametrize("ato", ["dia", "verbos"])
def test_particao_fora_do_ar_e_exit_3_e_aponta_o_bruto(monkeypatch, capsys, ato):
    api = ApiFalsa(erro=ex.Falha(3, "GET /acervo/log/dias: http://127.0.0.1:8100 não respondeu (Connection refused)"))
    codigo, saida, err = roda(monkeypatch, capsys, api, ato, DIA)
    assert codigo == 3 and saida == ""
    assert "a particao nao respondeu" in err and f"metrica {ato} ... --fonte bruto" in err and "Traceback" not in err


def test_turnos_com_a_particao_fora_do_ar_e_exit_3_e_diz_que_so_ha_particao(monkeypatch, capsys):
    api = ApiFalsa(erro=ex.Falha(3, "GET /acervo/log/dias: não respondeu"))
    codigo, _, err = roda(monkeypatch, capsys, api, "turnos", "2026-10-07")
    assert codigo == 3 and "D5.8" in err and "--fonte bruto" not in err


def test_token_recusado_e_exit_4(monkeypatch, capsys):
    api = ApiFalsa(erro=ex.Falha(4, "GET /acervo/log/dias: HTTP 403"))
    assert roda(monkeypatch, capsys, api, "dia", DIA)[0] == 4


# --- a CLI de ponta a ponta, contra um servidor de loopback -----------------------------------------

class _Servidor:
    def __init__(self, respostas):
        recebidas = self.recebidas = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                recebidas.append((self.path, self.headers.get("authorization")))
                status, corpo = respostas.get(self.path.split("?")[0], (404, {}))
                dados = json.dumps(corpo).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def fecha(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def servidor():
    criados = []

    def novo(respostas):
        s = _Servidor(respostas)
        criados.append(s)
        return s
    yield novo
    for s in criados:
        s.fecha()


def _cli(tmp_path, base, *args, token="SEGREDO-TOKEN"):
    env = {**os.environ, "OPS_LOG_DIR": str(tmp_path), "MOTOR_ACERVO_URL": base, "RAG_API_TOKEN": token}
    return subprocess.run([sys.executable, str(METRICA), *args], capture_output=True, text=True, env=env, timeout=60)


def test_cli_dia_pela_particao_sem_vazar_o_token(servidor, tmp_path):
    s = servidor({"/acervo/log/dias": (200, {"itens": [linha_dia(DIA)]}),
                  "/acervo/log/giros/medida": (200, {"series": [serie("acervo", "ler", "ok", "cadeira", 4)]})})
    r = _cli(tmp_path, s.base, "dia", DIA)
    assert r.returncode == 0, r.stderr
    saida = json.loads(r.stdout)
    assert saida["fonte"] == "partição" and saida["total"]["giros"] == 4
    assert "SEGREDO-TOKEN" not in r.stdout + r.stderr
    assert {auth for _, auth in s.recebidas} == {"Bearer SEGREDO-TOKEN"}


def test_cli_dia_sem_arquivo_sai_ausente_sem_arquivo_pelo_modulo(servidor, tmp_path):
    """O dia de 2026-09-10 do aceite: a API não o conhece e a pasta do bruto não tem o arquivo."""
    s = servidor({"/acervo/log/dias": (200, {"itens": [linha_dia("2026-09-10", "ausente", "nao_extraido")]})})
    r = _cli(tmp_path, s.base, "dia", "2026-09-10")
    saida = json.loads(r.stdout)
    assert r.returncode == 0 and saida["resultado"] == "ausente" and saida["motivo"] == "sem_arquivo"


def test_cli_dia_com_o_bruto_no_disco_e_sem_passada_diz_nao_extraido(servidor, tmp_path):
    _dia_misto(tmp_path)
    s = servidor({"/acervo/log/dias": (200, {"itens": [linha_dia(DIA, "ausente", "nao_extraido")]})})
    saida = json.loads(_cli(tmp_path, s.base, "dia", DIA).stdout)
    assert saida["resultado"] == "ausente" and saida["motivo"] == "nao_extraido"


def test_cli_particao_que_nao_responde_sai_3(tmp_path):
    r = _cli(tmp_path, "http://127.0.0.1:9", "dia", DIA)
    assert r.returncode == 3 and "a particao nao respondeu" in r.stderr and "SEGREDO-TOKEN" not in r.stderr


def test_cli_turnos_pela_particao(servidor, tmp_path):
    s = servidor({"/acervo/log/dias": (200, {"itens": [linha_dia("2026-10-07")]}),
                  "/acervo/log/turnos/medida": (200, _turnos(("hook", "claude-code", None)))})
    r = _cli(tmp_path, s.base, "turnos", "2026-10-07")
    saida = json.loads(r.stdout)
    assert r.returncode == 0 and saida["turno_fontes"] == ["hook"] and saida["fonte"] == "partição"


def test_cli_ajuda_e_ato_desconhecido_dizem_turnos_e_fonte(tmp_path):
    ajuda = _cli(tmp_path, "http://127.0.0.1:9", "--ajuda")
    assert ajuda.returncode == 0 and "metrica turnos" in ajuda.stdout and "--fonte" in ajuda.stdout
    erro = _cli(tmp_path, "http://127.0.0.1:9", "resumir")
    assert erro.returncode == 2 and "eventos, dia, ate-acerto" in erro.stderr and "turnos" in erro.stderr


# --- a lista do que ainda não atravessa -----------------------------------------------------------

def test_os_sinais_que_faltam_nao_estao_no_bloco_giro_e_o_bruto_ainda_os_le():
    """A lista que vai ao comentário do card (antes do primeiro corte, #3354) tem de ser verdade: cada nome é lido por
    `bin/metrica` e não está no bloco `giro` que o extrator leva à partição."""
    texto = METRICA.read_text(encoding="utf-8")
    reg = {"tool": "repo", "ato": "x", "exit_code": 0, "classe_erro": "caminho", "via": "malote", "poda_modo": "igual",
           "evento": "sem_verbo", "verbo": "nao-existe", "args": "--help"}
    bloco = ex.bloco_giro(reg)
    for nome in ("classe_erro", "evento", "verbo", "via", "poda_modo"):
        assert nome not in bloco, nome
    for nome in ("classe_erro", "poda_modo", "sem_verbo"):
        assert nome in texto, nome
    assert '"via"' in texto
    assert set(particao.SINAIS_QUE_FALTAM) == {"classe_erro", "evento", "verbo recusado", "ajuda", "veredito", "via", "poda_modo"}


def test_o_cabecalho_do_verbo_guarda_a_linha_exit_nas_40_primeiras_linhas():
    """A porta lê o cabeçalho (40 linhas, `ops-server/server.py::_declara_exit`) para dar `classe_fonte=verbo` ao giro de
    `metrica`; um parágrafo a mais antes da linha `# exit:` a perde, e o pre-push barra (`test_oplog_porta`)."""
    cabecalho = "".join(METRICA.read_text(encoding="utf-8").splitlines(keepends=True)[:40])
    assert re.search(r"^#\s*exit\s*:", cabecalho, re.MULTILINE)


def test_a_particao_nao_abre_o_bruto_por_conta_propria():
    from test_oplog_unico_leitor import achados
    caminho = RAIZ / "bin" / "_metrica" / "particao.py"
    assert achados(caminho, caminho.read_text(encoding="utf-8")) == []
