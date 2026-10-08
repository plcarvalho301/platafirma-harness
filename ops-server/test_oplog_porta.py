"""A porta grava o bruto pelo lib/oplog (card #3344, arq:0123 §3-§5).

`_audit` monta o registro da linha e entrega a escrita ao modulo: a linha sai com `evento_id`,
`schema_v` e `classe`, o campo longo e aparado antes de serializar e nenhuma linha sai cortada
no meio. Vive em ops-server/ porque server.py precisa do venv com `mcp` (mesma fronteira de
test_origem_sessao_porta.py).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-oplog-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import server as s  # noqa: E402


@pytest.fixture(autouse=True)
def msgmem_mudo():
    """A auditoria nao pode depender do msg-mem: sem origem, sem espera."""
    s._ORIGENS.clear()
    with patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))):
        yield
    s._ORIGENS.clear()


def _grava(tmp_path, **campos) -> list[dict]:
    with patch.object(s, "LOG_DIR", tmp_path):
        s._audit(**campos)
    return [json.loads(l) for f in sorted(tmp_path.glob("ops-*.jsonl"))
            for l in f.read_text(encoding="utf-8").splitlines()]


def test_a_linha_da_porta_sai_com_chave_versao_e_classe(tmp_path):
    (linha,) = _grava(tmp_path, tool="tarefas", evento="verbo", ato="ler", exit_code=0)
    assert linha["schema_v"] == 1
    assert linha["evento_id"][14] == "7"
    assert linha["classe"] == "ok"
    assert linha["sessao_id"] == "-" and linha["tool"] == "tarefas"


def test_linha_de_20000_caracteres_sai_json_valido_e_aparada(tmp_path):
    (linha,) = _grava(tmp_path, tool="repo", evento="verbo", exit_code=0, args="x" * 20_000)
    assert linha["aparado"] == ["args"]
    bruto = next(tmp_path.glob("ops-*.jsonl")).read_bytes()
    assert bruto.endswith(b"\n") and len(bruto) <= 8000


def test_classe_vem_do_exit_e_do_erro_que_a_porta_observa(tmp_path):
    casos = [
        (dict(exit_code=1), "negativa"),
        (dict(exit_code=2), "gramatica"),
        (dict(exit_code=4), "negada"),
        (dict(exit_code=5), "execucao"),
        (dict(erro="timeout (120s) — grupo de processo morto"), "execucao"),
    ]
    for campos, esperada in casos:
        linhas = _grava(tmp_path, tool="teste", evento="verbo", **campos)
    assert [l["classe"] for l in linhas] == [c for _, c in casos]
    assert linhas[-1]["causa"] == "timeout"


def test_negacao_do_pep_e_recusa_de_argumento(tmp_path):
    linhas = _grava(tmp_path, tool="acervo", evento="pep_negou", regra="projecao")
    linhas = _grava(tmp_path, tool="run_command", evento="sem_verbo", motivo="nao e verbo")
    assert [l["classe"] for l in linhas] == ["negada", "gramatica"]


def test_classe_fonte_e_verbo_quando_o_cabecalho_declara_a_tabela_de_exit(tmp_path):
    with patch.object(s, "BIN_VERBOS", HARNESS_DIR / "bin"):
        s._DECLARA_EXIT.clear()
        assert s._declara_exit("metrica") is True            # `# exit:` no cabecalho do verbo
        (declara,) = _grava(tmp_path, tool="metrica", evento="verbo", exit_code=0)
        assert declara["classe_fonte"] == "verbo"
        assert s._declara_exit("verbo-que-nao-existe") is False
        assert s._declara_exit("-") is False
    s._DECLARA_EXIT.clear()


def test_linha_sem_verbo_nao_consulta_o_cabecalho(tmp_path):
    with patch.object(s, "_declara_exit") as declara:
        _grava(tmp_path, tool="-", evento="pep_vocabulario_divergente")
    declara.assert_not_called()


def test_falha_de_escrita_nao_derruba_a_operacao(tmp_path, capsys):
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x")
    with patch.object(s, "LOG_DIR", arquivo):
        s._audit(tool="x", evento="verbo", exit_code=0)          # nao levanta
    assert "[audit] FALHOU" in capsys.readouterr().err


def test_o_diretorio_do_bruto_e_o_do_modulo():
    import oplog
    assert s.LOG_DIR == oplog.diretorio()
