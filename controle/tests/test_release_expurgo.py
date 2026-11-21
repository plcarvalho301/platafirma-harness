"""Provas do expurgo da release e da classe fossil (card #4404, regras r15, r27 e r28).

Cobre as cenas do Comportamento esperado:
  1. `release conferir fossil` limpo sai 0 com «0 divergente»;
  2. árvore plantada em `<PF_RELEASE_RAIZ>/<família>/<sha velho>` faz `release conferir fossil`
     sair 1 com o caminho dela;
  3. árvore fora do `current` em uso por processo vivo (cwd) não é apagada pelo expurgo e sai
     divergente em `release conferir fossil` dizendo quem a usa;
  4. `expurgo` remove atalhos órfãos/quebrados em `current/` e `current/venv/`, entradas
     estranhas na raiz (`v0.1.0/`, `v0.2.0/`), venvs não declarados, cache de terceiros
     fora do declarado, ponto `anterior` e árvores extras não em uso;
  5. `release reverter <família>` sai 2 dizendo que a volta é reverter o commit na main e promover;
  6. `release promover abertura` sai 2 dizendo que abertura não é família;
  7. `release estado` não mostra «anterior:» nem linha «abertura».
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
RELEASE = REPO_RAIZ / "bin" / "release"
EXPURGO = REPO_RAIZ / "bin" / "_release" / "expurgo"
BASH = shutil.which("bash")


def _montar_host_falso(tmp_path: Path) -> dict:
    raiz = tmp_path / "opt"
    inst = tmp_path / "srv"
    (inst / "var" / "release").mkdir(parents=True)
    reg = tmp_path / "reg"
    reg.mkdir()

    familias = {"platafirma-harness": "https://example.invalid/harness.git"}
    (reg / "familias.json").write_text(json.dumps(familias), encoding="utf-8")
    venvs = {
        "harness": {"familia": "platafirma-harness", "lock": "venvs/harness/uv.lock"},
    }
    (reg / "venvs.json").write_text(json.dumps(venvs), encoding="utf-8")
    from _olaria_local import subir_olaria_local

    terceiros = {
        "tok": {"familia": "platafirma-harness", "destino": "t.json", "sha256": "aaa111"},
    }
    srv, env_olaria = subir_olaria_local(terceiros)

    sha_cur = "a" * 40
    fam = raiz / "platafirma-harness"
    (fam / ".repo.git").mkdir(parents=True)
    (fam / sha_cur).mkdir(parents=True)
    (fam / sha_cur / ".git").write_text("gitdir: ../.repo.git\n", encoding="utf-8")
    os.symlink(sha_cur, fam / "current")

    (raiz / "venv" / "harness-1234").mkdir(parents=True)
    (raiz / "current" / "venv").mkdir(parents=True)
    os.symlink("../platafirma-harness/current", raiz / "current" / "harness")
    os.symlink("../../venv/harness-1234", raiz / "current" / "venv" / "harness")

    (raiz / "terceiros" / "sha256").mkdir(parents=True)
    (raiz / "terceiros" / "sha256" / "aaa111").write_text("ok", encoding="utf-8")

    env = {
        **os.environ,
        **env_olaria,
        "PF_RELEASE_RAIZ": str(raiz),
        "PLATAFIRMA_RELEASE": str(raiz / "current"),
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PLATAFIRMA_FAMILIAS": str(reg / "familias.json"),
        "PLATAFIRMA_VENVS": str(reg / "venvs.json"),
        "PF_EXPURGO_SEM_DOCKER": "1",
    }
    return {"raiz": raiz, "inst": inst, "sha_cur": sha_cur, "env": env, "_srv": srv}


def _roda_release(env: dict, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, str(RELEASE), *args],
        capture_output=True, text=True, env=env, timeout=30, check=False,
    )


def test_conferir_fossil_limpo_sai_0(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    r = _roda_release(m["env"], "conferir", "fossil")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 divergente" in r.stdout


def test_conferir_fossil_arvore_plantada_sai_1_com_caminho(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    sha_velho = "b" * 40
    arvore_velha = m["raiz"] / "platafirma-harness" / sha_velho
    arvore_velha.mkdir(parents=True)
    r = _roda_release(m["env"], "conferir", "fossil")
    assert r.returncode == 1, r.stdout + r.stderr
    assert str(arvore_velha) in r.stdout


def test_expurgo_remove_fosseis_e_zera_conferir_fossil(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    raiz, inst = m["raiz"], m["inst"]
    sha_velho = "c" * 40
    arvore_velha = raiz / "platafirma-harness" / sha_velho
    arvore_velha.mkdir(parents=True)
    (arvore_velha / "arq.txt").write_text("velho", encoding="utf-8")
    os.chmod(arvore_velha / "arq.txt", 0o444)
    os.chmod(arvore_velha, 0o555)

    os.symlink(sha_velho, raiz / "platafirma-harness" / "anterior")
    (inst / "var" / "release" / "platafirma-harness").mkdir(parents=True)
    (inst / "var" / "release" / "platafirma-harness" / "anterior").write_text(sha_velho + "\n", encoding="utf-8")

    # Entradas estranhas na raiz (v0.1.0, v0.2.0)
    (raiz / "v0.1.0").mkdir()
    (raiz / "v0.2.0").mkdir()

    # Atalhos órfãos/quebrados em current/ e current/venv/ + venv órfão + terceiro órfão
    os.symlink("../platafirma-extinta/current", raiz / "current" / "arquitetura")
    (raiz / "venv" / "espelho-antigo-9999").mkdir()
    os.symlink("../../venv/espelho-antigo-9999", raiz / "current" / "venv" / "espelho-antigo")
    (raiz / "terceiros" / "sha256" / "bbb222").write_text("lixo", encoding="utf-8")

    # Antes do expurgo: conferir fossil sai 1
    r_antes = _roda_release(m["env"], "conferir", "fossil")
    assert r_antes.returncode == 1

    # Roda o expurgo
    r_exp = subprocess.run(
        [sys.executable, str(EXPURGO), "--sem-docker"],
        capture_output=True, text=True, env=m["env"], timeout=30, check=False,
    )
    assert r_exp.returncode == 0, r_exp.stderr
    assert "expurgo:" in r_exp.stdout
    assert not arvore_velha.exists()
    assert not (raiz / "v0.1.0").exists()
    assert not (raiz / "v0.2.0").exists()
    assert not (raiz / "current" / "arquitetura").is_symlink()
    assert not (raiz / "current" / "venv" / "espelho-antigo").is_symlink()
    assert not (raiz / "venv" / "espelho-antigo-9999").exists()
    assert not (raiz / "terceiros" / "sha256" / "bbb222").exists()
    assert (raiz / "platafirma-harness" / ".repo.git").is_dir()
    assert (raiz / "platafirma-harness" / m["sha_cur"]).is_dir()

    # Depois do expurgo: conferir fossil sai 0
    r_depois = _roda_release(m["env"], "conferir", "fossil")
    assert r_depois.returncode == 0, r_depois.stdout + r_depois.stderr
    assert "0 divergente" in r_depois.stdout


def test_arvore_em_uso_por_processo_vivo_fica_e_diverge_em_fossil(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    sha_velho = "d" * 40
    arvore_velha = m["raiz"] / "platafirma-harness" / sha_velho
    arvore_velha.mkdir(parents=True)

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=str(arvore_velha),
    )
    try:
        time.sleep(0.2)
        r_exp = subprocess.run(
            [sys.executable, str(EXPURGO), "--sem-docker"],
            capture_output=True, text=True, env=m["env"], timeout=30, check=False,
        )
        assert r_exp.returncode == 0, r_exp.stderr
        assert arvore_velha.is_dir(), "árvore em uso não pode ser apagada"
        assert "mantido" in r_exp.stdout

        r_fos = _roda_release(m["env"], "conferir", "fossil")
        assert r_fos.returncode == 1, r_fos.stdout
        assert str(arvore_velha) in r_fos.stdout
        assert f"pid {proc.pid}" in r_fos.stdout
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_arvore_preservada_da_porta_fica_no_expurgo(tmp_path: Path):
    """Incidente #4407: a arvore do core da qual a porta ainda roda nao sai antes de a porta religar."""
    m = _montar_host_falso(tmp_path)
    sha_velho = "e" * 40
    arvore_velha = m["raiz"] / "platafirma-harness" / sha_velho
    arvore_velha.mkdir(parents=True)
    env = {**m["env"], "PF_EXPURGO_PRESERVAR": str(arvore_velha), "PF_EXPURGO_SEM_PROC": "1"}
    r_exp = subprocess.run(
        [sys.executable, str(EXPURGO), "--sem-docker"],
        capture_output=True, text=True, env=env, timeout=30, check=False,
    )
    assert r_exp.returncode == 0, r_exp.stderr
    assert arvore_velha.is_dir(), "arvore da porta nao pode sair antes de a porta religar"
    assert "#4407" in r_exp.stdout

    r_sem = subprocess.run(
        [sys.executable, str(EXPURGO), "--sem-docker"],
        capture_output=True, text=True, env={**m["env"], "PF_EXPURGO_SEM_PROC": "1"},
        timeout=30, check=False,
    )
    assert r_sem.returncode == 0, r_sem.stderr
    assert not arvore_velha.exists(), "sem a preservacao, o expurgo seguinte leva a arvore"

def test_release_reverter_sai_2_com_mensagem_de_main(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    r = _roda_release(m["env"], "reverter", "platafirma-harness")
    assert r.returncode == 2
    assert "reverter o commit na main" in r.stderr


def test_release_promover_abertura_sai_2(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    r = _roda_release(m["env"], "promover", "abertura")
    assert r.returncode == 2
    assert "abertura não é família" in r.stderr


def test_release_estado_sem_anterior_nem_abertura(tmp_path: Path):
    m = _montar_host_falso(tmp_path)
    r = _roda_release(m["env"], "estado")
    assert "anterior:" not in r.stdout
    assert not any(l.startswith("abertura") for l in r.stdout.splitlines())
