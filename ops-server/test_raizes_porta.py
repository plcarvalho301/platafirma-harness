"""A porta sem a pasta de trabalho da conta (card #3010, desenho §1/§3/§6).

Aceite coberto, tudo com as raizes em tmp:
- a porta importa sem bancada declarada e nao cria diretorio em bancada nenhuma;
- log, rascunho, derrame e abertura derivam da instancia; bin e PDP, da release;
- run_command sem cwd roda na casa da conta; cwd relativo e relativo a bancada
  declarada, e sem ela a chamada e recusada;
- read_file relativo sem bancada recusa; absoluto le;
- read_file nega <instancia>/segredos por construcao;
- write_file: morada = rascunho da fita + clones/worktrees da bancada declarada;
  release e log sao negados; sem bancada, clone fica fora de alcance.

    PF_BANCADA nao precisa existir: o teste declara e desdeclara por monkeypatch.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-raizes-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
# Raiz herdada so vale se ja for tmp (outro modulo de teste chegou antes): o teste
# escreve em rascunho e log, e nunca pode cair numa instancia de verdade.
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PF_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)
# Arranque SEM bancada: nem variavel nem arquivo de declaracao.
_BANCADA_ANTES = os.environ.pop("PF_BANCADA", None)
os.environ.setdefault("PF_ARQUIVO_BANCADA", str(_TMP / "sem-declaracao"))

import poda  # noqa: E402
import server as s  # noqa: E402

if _BANCADA_ANTES is not None:
    os.environ["PF_BANCADA"] = _BANCADA_ANTES


@pytest.fixture
def sem_bancada(monkeypatch, tmp_path):
    monkeypatch.delenv("PF_BANCADA", raising=False)
    monkeypatch.setenv("PF_ARQUIVO_BANCADA", str(tmp_path / "nao-declarada"))


@pytest.fixture
def bancada(monkeypatch, tmp_path):
    b = tmp_path / "bancada"
    (b / "platafirma-harness" / "bin").mkdir(parents=True)
    (b / "wt" / "platafirma-core" / "fabrica").mkdir(parents=True)
    monkeypatch.setenv("PF_BANCADA", str(b))
    return b


@pytest.fixture
def sem_pep():
    with patch.object(s, "_autoriza", return_value=None), patch.object(s, "_audit"):
        yield


def test_nenhuma_raiz_resolve_para_a_casa_da_conta():
    """Toda raiz de producao da porta deriva de PF_RELEASE_RAIZ ou PF_INSTANCIA."""
    inst, rel = Path(os.environ["PF_INSTANCIA"]), Path(os.environ["PF_RELEASE_RAIZ"])
    assert s.LOG_DIR == inst / "var/log/ops"
    assert s.TMP_FITA == inst / "var/tmp"
    assert s.PERSONAS == inst / "var/abertura-publicada/current/abertura"
    assert poda.DERRAME == inst / "var/tmp/retornos"
    assert s.BIN_VERBOS == rel / "current/harness/bin"
    assert s.PDP_DIR == rel / "current/politica-acesso"


def test_arranque_sem_bancada_nao_cria_nada():
    assert not (_TMP / "sem-declaracao").exists()
    assert not any(p.name == "bancada" for p in _TMP.iterdir())


def test_path_do_subprocesso_traz_o_bin_da_release():
    assert s._env_subprocesso()["PATH"].split(":")[0] == str(s.BIN_VERBOS)


def test_run_command_sem_cwd_roda_na_casa(sem_bancada, sem_pep):
    with patch.object(s, "PF_RUN_SO_VERBO", False), patch.object(s, "PF_GATE", False):
        r = asyncio.run(s.run_command(command="pwd"))
    assert r["exit_code"] == 0
    assert r["stdout"]["texto"].strip() == str(Path(os.path.expanduser("~")).resolve())


def test_run_command_cwd_relativo_sem_bancada_recusa(sem_bancada, sem_pep):
    with patch.object(s, "PF_RUN_SO_VERBO", False), patch.object(s, "PF_GATE", False):
        r = asyncio.run(s.run_command(command="pwd", cwd="platafirma-core"))
    assert r["recusado"] and "bancada" in r["motivo"]


def test_run_command_cwd_relativo_e_na_bancada(bancada, sem_pep):
    with patch.object(s, "PF_RUN_SO_VERBO", False), patch.object(s, "PF_GATE", False):
        r = asyncio.run(s.run_command(command="pwd", cwd="platafirma-harness"))
    assert r["stdout"]["texto"].strip() == str((bancada / "platafirma-harness").resolve())


def test_read_file_relativo_sem_bancada_recusa_e_absoluto_le(sem_bancada, sem_pep):
    r = s.read_file(path="platafirma-harness/ops-server/requirements.txt")
    assert r.get("recusado") and "bancada" in r["motivo"]
    r = s.read_file(path=str(OPS_SERVER_DIR / "requirements.txt"))
    assert "mcp==" in r["content"]


def test_read_file_nega_segredos_de_qualquer_instancia(tmp_path, monkeypatch, sem_pep):
    monkeypatch.setattr(s, "_RAIZES_DE_INSTANCIA", (Path("/srv/platafirma"), tmp_path))
    seg = tmp_path / "outra" / "segredos" / "core"
    seg.mkdir(parents=True)
    (seg / "POSTGRES").write_text("nao-leia")
    r = s.read_file(path=str(seg / "POSTGRES"))
    assert r.get("recusado") and r["motivo"].startswith("segredo")
    assert s._sob_segredos_de_instancia(Path("/srv/platafirma/casa/segredos/x/Y"))


def test_write_file_sem_bancada_so_rascunho(sem_bancada, sem_pep):
    ok = s.write_file(path=str(s.TMP_FITA / "o-teste" / "nota.md"), content="x\n")
    assert ok.get("ok"), ok
    r = s.write_file(path="platafirma-core/README.md", content="x\n")
    assert r.get("recusado") and "bancada" in r["motivo"]


def test_write_file_na_bancada_worktree_e_bin(bancada, sem_pep):
    r = s.write_file(path="wt/platafirma-core/fabrica/nota.md", content="x\n")
    assert r.get("ok"), r
    assert (bancada / "wt/platafirma-core/fabrica/nota.md").is_file()
    sem_shebang = s.write_file(path="platafirma-harness/bin/verbo", content="echo\n")
    assert sem_shebang.get("recusado") and "shebang" in sem_shebang["motivo"]
    verbo = s.write_file(path="platafirma-harness/bin/verbo", content="#!/bin/sh\necho\n")
    assert verbo.get("ok"), verbo
    assert os.access(bancada / "platafirma-harness/bin/verbo", os.X_OK)
    fora = s.write_file(path="outro-lugar/x.md", content="x\n")
    assert fora.get("recusado") and "fora de morada" in fora["motivo"]


def test_write_file_nao_recria_bancada_nem_worktree(monkeypatch, tmp_path, sem_pep):
    """Bancada declarada e apagada (ou worktree nunca aberto): recusa, e nada nasce."""
    apagada = tmp_path / "bancada-apagada"
    monkeypatch.setenv("PF_BANCADA", str(apagada))
    r = s.write_file(path="wt/platafirma-core/fabrica/nota.md", content="x\n")
    assert r.get("recusado") and "repo abrir" in r["motivo"], r
    r = s.write_file(path="platafirma-core/README.md", content="x\n")
    assert r.get("recusado") and "repo abrir" in r["motivo"], r
    assert not apagada.exists()
    viva = tmp_path / "bancada-viva"
    (viva / "wt" / "platafirma-core").mkdir(parents=True)
    monkeypatch.setenv("PF_BANCADA", str(viva))
    r = s.write_file(path="wt/platafirma-core/outra-cadeira/nota.md", content="x\n")
    assert r.get("recusado") and "repo abrir" in r["motivo"], r
    assert not (viva / "wt" / "platafirma-core" / "outra-cadeira").exists()


def test_write_file_nega_release_e_log(bancada, sem_pep):
    rel = s.write_file(path=str(s.BIN_VERBOS / "x.md"), content="x\n")
    assert rel.get("recusado") and "release" in rel["motivo"]
    log = s.write_file(path=str(s.LOG_DIR / "x.txt"), content="x\n")
    assert log.get("recusado") and "log" in log["motivo"]


def test_derrame_devolve_caminho_absoluto(monkeypatch, tmp_path):
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "retornos")
    caminho = poda.derrama("sessao-x", "g1.txt", "inteiro")
    assert Path(caminho).is_absolute() and Path(caminho).read_text() == "inteiro"
