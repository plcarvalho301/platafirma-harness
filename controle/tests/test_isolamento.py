# componente: componente:suite
"""O isolamento do conftest está de pé: a suíte não enxerga estado real.

Se este arquivo fica vermelho, o conftest deixou de carregar ou alguém reabriu uma
porta para o mundo real, e todo o resto da suíte volta a poder passar por sorte.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REAIS = ("/srv/platafirma", "/opt/platafirma", os.path.expanduser("~/AI"),
         os.path.expanduser("~/.config/platafirma"))


def test_raizes_apontam_para_temporario():
    for var in ("PLATAFIRMA_INSTANCIA", "PF_RELEASE_RAIZ", "PLATAFIRMA_RELEASE",
                "PLATAFIRMA_BANCADA", "PLATAFIRMA_ARQUIVO_BANCADA"):
        valor = os.environ.get(var, "")
        assert valor, f"{var} ausente: o codigo cairia no default real"
        assert not valor.startswith(REAIS), f"{var}={valor} aponta estado real"


def test_sessao_e_cadeira_da_conta_nao_vazam():
    for var in ("PF_SESSAO", "PF_SESSAO_ID", "PF_CADEIRA", "PF_FITA", "PF_ORDEM_ID"):
        assert var not in os.environ, f"{var} herdado da conta que roda a suite"


def test_servicos_apontam_para_porta_morta():
    for var in ("RAG_API_URL", "MOTOR_ACERVO_URL", "TAREFAS_BASE", "MW_API_URL"):
        assert ":9" in os.environ[var], f"{var}={os.environ[var]}"
    for var in ("MEM_REDIS_PORT", "FILA_REDIS_PORT", "SESSAO_PG_PORT"):
        assert os.environ[var] == "9"


def test_programas_do_mundo_real_sao_delatores():
    for prog in ("docker", "gh", "systemctl", "psql", "redis-cli"):
        caminho = shutil.which(prog)
        assert caminho and "delatores" in caminho, f"{prog} resolve para {caminho}"
    r = subprocess.run(["gh", "pr", "list"], capture_output=True, text=True)
    assert r.returncode == 97
    assert r.stderr.startswith("isolamento:")
    assert "sem stub" in r.stderr


def _injetar_real_bin_apos_delatores(tmp_path, monkeypatch):
    real_bin = tmp_path / "real_bin"
    real_bin.mkdir()
    psql_real = real_bin / "psql"
    psql_real.write_text("#!/bin/sh\necho \"real-psql:$*\"\n", encoding="utf-8")
    psql_real.chmod(0o755)
    delatores_dir = str(Path(shutil.which("psql")).parent)
    resto = os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep) if p != delatores_dir)
    monkeypatch.setenv("PATH", f"{delatores_dir}{os.pathsep}{real_bin}{os.pathsep}{resto}")


@pytest.mark.isolamento_libera("psql")
def test_marcador_libera_apenas_verbos_listados(tmp_path, monkeypatch):
    _injetar_real_bin_apos_delatores(tmp_path, monkeypatch)

    r_ok = subprocess.run(["psql", "-c", "select 1"], capture_output=True, text=True)
    assert r_ok.returncode == 0
    assert "real-psql:-c select 1" in r_ok.stdout

    r_bloqueado = subprocess.run(["gh", "pr", "list"], capture_output=True, text=True)
    assert r_bloqueado.returncode == 97
    assert r_bloqueado.stderr.startswith("isolamento:")


def test_marcador_nao_vaza_para_proximo_teste(tmp_path, monkeypatch):
    _injetar_real_bin_apos_delatores(tmp_path, monkeypatch)

    r = subprocess.run(["psql", "-c", "select 1"], capture_output=True, text=True)
    assert r.returncode == 97
    assert r.stderr.startswith("isolamento:")


def test_identidade_git_global_nao_vaza(tmp_path):
    assert os.environ.get("GIT_CONFIG_NOSYSTEM") == "1"
    gitconfig = os.environ.get("GIT_CONFIG_GLOBAL")
    assert gitconfig, "GIT_CONFIG_GLOBAL ausente"
    # commit sem identidade explicita falha porque useConfigOnly=true e sem user.name/email (#2856 linha 181)
    repo = tmp_path / "repo-sem-identidade"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, timeout=20)
    (repo / "arq.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "arq.txt"], cwd=repo, check=True, timeout=20)
    r = subprocess.run(["git", "commit", "-m", "teste"], cwd=repo, capture_output=True, text=True, timeout=20)
    assert r.returncode == 128
    assert "auto-detection is disabled" in r.stderr or "Please tell me who you are" in r.stderr
