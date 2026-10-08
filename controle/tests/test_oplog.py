"""lib/oplog: chave, versao, aparo, classe e leitura por dia do bruto da porta (card #3344).

arq:0123 §3-§5. O modulo e o unico que escreve e le `ops-AAAA-MM-DD.jsonl`; estes testes o
exercitam contra uma pasta em tmp_path, sem porta, sem motor e sem o log real.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import oplog

RAIZ = Path(__file__).resolve().parents[2]
LIB = RAIZ / "lib"


def _linhas(pasta, dia):
    arq = pasta / f"ops-{dia}.jsonl"
    return [json.loads(x) for x in arq.read_text(encoding="utf-8").splitlines()]


def _agora(dia="2026-10-08", hora="12:00:00"):
    return datetime.fromisoformat(f"{dia}T{hora}+00:00").astimezone(timezone.utc)


# --- chave e versao -------------------------------------------------------------------

def test_evento_id_ordena_por_tempo():
    ids = [oplog.uuid7(1_790_000_000_000 + 1000 * n) for n in range(20)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 20
    assert all(i[14] == "7" and i[19] in "89ab" for i in ids)   # versao 7, variante 10


def test_emitir_carimba_chave_e_versao_e_grava_o_dia(tmp_path):
    ok = oplog.emitir({"tool": "tarefas", "ato": "ler", "exit_code": 0},
                      diretorio_=tmp_path, agora=_agora())
    assert ok
    (linha,) = _linhas(tmp_path, "2026-10-08")
    assert linha["schema_v"] == oplog.SCHEMA_V == 1
    assert linha["evento_id"] and linha["evento_id"][14] == "7"
    assert linha["classe"] == "ok" and linha["classe_fonte"] == "tabela"
    assert list(linha)[:3] == ["ts", "evento_id", "schema_v"]


def test_emitir_nao_aceita_chave_de_fora(tmp_path):
    oplog.emitir({"tool": "x", "evento_id": "forjado", "schema_v": 99},
                 diretorio_=tmp_path, agora=_agora())
    (linha,) = _linhas(tmp_path, "2026-10-08")
    assert linha["evento_id"] != "forjado" and linha["schema_v"] == 1


def test_emitir_so_acrescenta(tmp_path):
    for n in range(3):
        oplog.emitir({"tool": "x", "n": n}, diretorio_=tmp_path, agora=_agora())
    assert [l["n"] for l in _linhas(tmp_path, "2026-10-08")] == [0, 1, 2]


def test_emitir_nunca_levanta(tmp_path, capsys):
    arquivo = tmp_path / "isto-e-um-arquivo"
    arquivo.write_text("x")
    assert oplog.emitir({"tool": "x"}, diretorio_=arquivo, agora=_agora()) is False
    assert "[audit] FALHOU" in capsys.readouterr().err


# --- aparo ----------------------------------------------------------------------------

def test_linha_de_20000_caracteres_sai_json_valido_com_aparado(tmp_path):
    oplog.emitir({"tool": "repo", "evento": "verbo", "exit_code": 0, "args": "a" * 20_000},
                 diretorio_=tmp_path, agora=_agora())
    bruto = (tmp_path / "ops-2026-10-08.jsonl").read_bytes()
    assert bruto.endswith(b"\n") and len(bruto) <= oplog.LINHA_MAX
    (linha,) = _linhas(tmp_path, "2026-10-08")
    assert linha["aparado"] == ["args"]
    assert len(linha["args"].encode()) <= oplog.LIMITE_CAMPO
    assert linha["classe"] == "ok" and linha["tool"] == "repo"


def test_varios_campos_abaixo_do_limite_mas_juntos_acima_da_linha_sao_aparados(tmp_path):
    oplog.emitir({"tool": "motor", "exit_code": 0, "args": "a" * 6900, "query": "q" * 6900,
                  "erro": "e" * 6900}, diretorio_=tmp_path, agora=_agora())
    bruto = (tmp_path / "ops-2026-10-08.jsonl").read_bytes()
    assert len(bruto) <= oplog.LINHA_MAX
    (linha,) = _linhas(tmp_path, "2026-10-08")
    assert linha["aparado"] and set(linha["aparado"]) <= {"args", "query", "erro"}
    assert linha["tool"] == "motor" and linha["classe"] == "ok"   # exit 0 vence o texto de erro


def test_aparo_nao_parte_caractere_multibyte(tmp_path):
    oplog.emitir({"tool": "x", "pergunta": "ação " * 5000}, diretorio_=tmp_path, agora=_agora())
    (linha,) = _linhas(tmp_path, "2026-10-08")      # json.loads falharia com byte partido
    assert "�" not in linha["pergunta"] and linha["aparado"] == ["pergunta"]


def test_valor_que_nao_e_texto_e_aparado_como_texto(tmp_path):
    oplog.emitir({"tool": "x", "lista": list(range(5000))}, diretorio_=tmp_path, agora=_agora())
    (linha,) = _linhas(tmp_path, "2026-10-08")
    assert linha["aparado"] == ["lista"] and isinstance(linha["lista"], str)


def test_campo_curto_nao_e_tocado():
    reg = {"ts": "t", "tool": "x", "args": "curto"}
    assert oplog.aparar(reg) == reg


# --- classe ---------------------------------------------------------------------------

@pytest.mark.parametrize("exit_code, classe", [
    (0, "ok"), (1, "negativa"), (2, "gramatica"), (4, "negada"), (3, "execucao"), (5, "execucao")])
def test_classe_dos_exits_da_tabela(exit_code, classe):
    assert oplog.classificar({"exit_code": exit_code})["classe"] == classe


def test_exit_3_e_5_dizem_a_causa_e_exit_fora_da_tabela_tambem():
    assert oplog.classificar({"exit_code": 3})["causa"] == "exit_3"
    assert oplog.classificar({"exit_code": 5})["causa"] == "exit_5"
    fora = oplog.classificar({"exit_code": 137})
    assert fora["classe"] == "execucao" and fora["causa"] == "exit_fora_da_tabela"


def test_timeout_e_execucao():
    r = oplog.classificar({"erro": "timeout (120s) — grupo de processo morto"})
    assert r["classe"] == "execucao" and r["causa"] == "timeout"


def test_falha_ao_abrir_o_processo_e_execucao():
    r = oplog.classificar({"erro": "falha ao abrir o processo: [Errno 2]"})
    assert r["classe"] == "execucao" and r["causa"] == "abrir_processo"


def test_chamador_que_cancelou_e_interrompida():
    assert oplog.classificar({"cancelado": True})["classe"] == "interrompida"
    assert oplog.classificar({"evento": "interrompida", "exit_code": 0})["classe"] == "interrompida"


def test_recusa_de_argumento_e_gramatica_e_negacao_do_pep_e_negada():
    assert oplog.classificar({"evento": "sem_verbo", "motivo": "x"})["classe"] == "gramatica"
    assert oplog.classificar({"evento": "cwd_recusado"})["classe"] == "gramatica"
    assert oplog.classificar({"evento": "pep_negou"})["classe"] == "negada"
    assert oplog.classificar({"evento": "pep_indisponivel"})["classe"] == "execucao"


def test_classe_fonte_e_verbo_quando_o_verbo_declara_a_tabela():
    assert oplog.classificar({"exit_code": 1}, declara_exit=True)["classe_fonte"] == "verbo"
    assert oplog.classificar({"exit_code": 1}, declara_exit=False)["classe_fonte"] == "tabela"
    assert oplog.classificar({"exit_code": 1})["classe_fonte"] == "tabela"


def test_emitir_grava_a_classe_e_a_fonte(tmp_path):
    oplog.emitir({"tool": "teste", "evento": "verbo", "exit_code": 1},
                 diretorio_=tmp_path, agora=_agora(), declara_exit=True)
    (linha,) = _linhas(tmp_path, "2026-10-08")
    assert (linha["classe"], linha["classe_fonte"]) == ("negativa", "verbo")


def test_linha_que_nao_e_giro_nao_leva_classe(tmp_path):
    oplog.emitir({"tool": "-", "evento": "pep_vocabulario_divergente"},
                 diretorio_=tmp_path, agora=_agora())
    oplog.emitir({"tool": "x", "evento": "http_req"}, diretorio_=tmp_path, agora=_agora())
    assert all("classe" not in l for l in _linhas(tmp_path, "2026-10-08"))


# --- ler ------------------------------------------------------------------------------

def _escreve(pasta, dia, *linhas):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"ops-{dia}.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def test_ler_um_dia_conta_legiveis_e_ilegiveis(tmp_path):
    _escreve(tmp_path, "2026-10-07", json.dumps({"tool": "a", "exit_code": 0}),
             '{"tool": "cortada no meio', "", json.dumps({"tool": "b", "exit_code": 1}), "[1, 2]")
    leitura = oplog.ler("2026-10-07", diretorio_=tmp_path)
    eventos = list(leitura)
    assert [e["tool"] for e in eventos] == ["a", "b"]
    d = leitura.dias["2026-10-07"]
    assert (d.estado, d.legiveis, d.ilegiveis) == ("presente", 2, 2)
    assert leitura.legiveis == 2 and leitura.ilegiveis == 2


def test_dia_sem_arquivo_e_ausente_nunca_zero(tmp_path):
    leitura = oplog.ler("2026-10-07", diretorio_=tmp_path)
    assert list(leitura) == []
    assert leitura.dias["2026-10-07"].estado == "ausente"
    assert leitura.ausentes() == ["2026-10-07"]


def test_janela_e_em_dias_corridos_e_marca_o_buraco(tmp_path):
    _escreve(tmp_path, "2026-10-05", json.dumps({"tool": "a"}))
    _escreve(tmp_path, "2026-10-07", json.dumps({"tool": "b"}))
    leitura = oplog.ler("2026-10-05", "2026-10-07", diretorio_=tmp_path)
    assert [e["tool"] for e in leitura] == ["a", "b"]
    assert {d: i.estado for d, i in leitura.dias.items()} == {
        "2026-10-05": "presente", "2026-10-06": "ausente", "2026-10-07": "presente"}


def test_janela_invertida_e_erro():
    with pytest.raises(ValueError):
        oplog.ler("2026-10-07", "2026-10-05")
    with pytest.raises(ValueError):
        oplog.ler("ontem")


def test_a_leitura_da_classe_a_linha_antiga(tmp_path):
    _escreve(tmp_path, "2026-09-23",
             json.dumps({"tool": "tarefas", "exit_code": 4}),
             json.dumps({"tool": "read_file", "erro": "timeout (30s)"}),
             json.dumps({"tool": "x", "evento": "http_req"}))
    a, b, c = list(oplog.ler("2026-09-23", diretorio_=tmp_path))
    assert (a["classe"], a["classe_fonte"]) == ("negada", "tabela")
    assert (b["classe"], b["causa"]) == ("execucao", "timeout")
    assert "classe" not in c


def test_o_que_emitir_grava_ler_devolve_igual(tmp_path):
    oplog.emitir({"tool": "motor", "exit_code": 3}, diretorio_=tmp_path, agora=_agora())
    (e,) = list(oplog.ler("2026-10-08", diretorio_=tmp_path))
    assert e["classe"] == "execucao" and e["causa"] == "exit_3" and e["schema_v"] == 1


def test_filtros_de_sessao_por_prefixo_e_de_tool(tmp_path):
    _escreve(tmp_path, "2026-10-08",
             json.dumps({"tool": "a", "sessao_id": "abc-111"}),
             json.dumps({"tool": "b", "sessao_id": "abc-222"}),
             json.dumps({"tool": "a", "sessao_id": "zzz"}))
    assert len(list(oplog.ler("2026-10-08", diretorio_=tmp_path, sessao="abc"))) == 2
    assert len(list(oplog.ler("2026-10-08", diretorio_=tmp_path, tool="a"))) == 2
    assert len(list(oplog.ler("2026-10-08", diretorio_=tmp_path, sessao="abc", tool="a"))) == 1


# --- onde mora ------------------------------------------------------------------------

def test_diretorio_obedece_a_ordem_dos_nomes(monkeypatch, tmp_path):
    for nome in ("OPS_LOG_DIR", "PF_LOG_OPS", "PF_OPS_LOG_DIR"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))
    assert oplog.diretorio() == tmp_path / "var" / "log" / "ops"
    monkeypatch.setenv("PF_OPS_LOG_DIR", str(tmp_path / "c"))
    assert oplog.diretorio() == tmp_path / "c"
    monkeypatch.setenv("PF_LOG_OPS", str(tmp_path / "b"))
    assert oplog.diretorio() == tmp_path / "b"
    monkeypatch.setenv("OPS_LOG_DIR", str(tmp_path / "a"))
    assert oplog.diretorio() == tmp_path / "a"


# --- CLI ------------------------------------------------------------------------------

def _cli(tmp_path, *args):
    env = {**os.environ, "PYTHONPATH": str(LIB), "OPS_LOG_DIR": str(tmp_path)}
    return subprocess.run([sys.executable, "-m", "oplog", *args], capture_output=True,
                          text=True, env=env, timeout=30)


def test_cli_ler_devolve_uma_linha_json_por_evento(tmp_path):
    _escreve(tmp_path, "2026-10-08", json.dumps({"tool": "a", "sessao_id": "s1"}),
             json.dumps({"tool": "b", "sessao_id": "s2"}))
    r = _cli(tmp_path, "ler", "2026-10-08", "--tool", "b")
    assert r.returncode == 0, r.stderr
    (linha,) = [json.loads(x) for x in r.stdout.splitlines()]
    assert linha["tool"] == "b" and linha["classe"] == "ok"


def test_cli_desde_ate_e_dia_ausente_no_stderr(tmp_path):
    _escreve(tmp_path, "2026-10-08", json.dumps({"tool": "a"}))
    r = _cli(tmp_path, "ler", "--desde", "2026-10-07", "--ate", "2026-10-08")
    assert r.returncode == 0 and len(r.stdout.splitlines()) == 1
    assert "ausente" in r.stderr and "2026-10-07" in r.stderr


def test_cli_janela_inteira_sem_arquivo_e_fonte_indisponivel_sai_3(tmp_path):
    r = _cli(tmp_path, "ler", "--desde", "2026-10-06", "--ate", "2026-10-08")
    assert r.returncode == 3 and r.stdout == ""
    assert "ausente" in r.stderr


def test_cli_uso_errado_sai_2(tmp_path):
    assert _cli(tmp_path).returncode == 2
    assert _cli(tmp_path, "ler").returncode == 2
    assert _cli(tmp_path, "ler", "ontem").returncode == 2
