"""DT 930 / Política 0009: expurgo de fósseis da release, sem anterior e sem reverter."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

RELEASE = str(Path(__file__).resolve().parents[2] / "bin" / "release")


def _env(tmp_path: Path) -> dict[str, str]:
    raiz = tmp_path / "opt"
    inst = tmp_path / "srv"
    e = dict(os.environ)
    e["PF_RELEASE_RAIZ"] = str(raiz)
    e["PLATAFIRMA_RELEASE"] = str(raiz / "current")
    e["PLATAFIRMA_INSTANCIA"] = str(inst)
    e["PF_ABERTURA_DIR"] = str(inst / "var" / "abertura-publicada")
    e["PF_RELEASE_EXPURGO_DOCKER"] = "0"
    return e


def _montar_fosseis(tmp_path: Path) -> tuple[Path, Path, Path]:
    raiz = tmp_path / "opt"
    inst = tmp_path / "srv"
    abertura = inst / "var" / "abertura-publicada"

    # Fósseis na raiz
    (raiz / "v0.1.0").mkdir(parents=True)
    (raiz / "v0.2.0").mkdir(parents=True)
    (raiz / "anterior").mkdir(parents=True)

    # Família core: current + 2 revisões fósseis (somente-leitura) + anterior + .repo.git
    core = raiz / "platafirma-core"
    cur_sha = "1" * 40
    old_sha = "2" * 40
    (core / cur_sha).mkdir(parents=True)
    (core / cur_sha / "vivo.txt").write_text("ok\n", encoding="utf-8")
    (core / old_sha).mkdir(parents=True)
    (core / old_sha / "velho.txt").write_text("fossil\n", encoding="utf-8")
    os.chmod(core / old_sha / "velho.txt", stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.chmod(core / old_sha, stat.S_IRUSR | stat.S_IXUSR)
    (core / ".repo.git").mkdir(parents=True)
    (core / "current").symlink_to(cur_sha)
    (core / "anterior").symlink_to(old_sha)
    ponto_ant = inst / "var" / "release" / "platafirma-core" / "anterior"
    ponto_ant.parent.mkdir(parents=True)
    ponto_ant.write_text(old_sha + "\n", encoding="utf-8")

    # Atalhos em current/ (um vivo, um quebrado)
    atalhos = raiz / "current"
    atalhos.mkdir(parents=True)
    (atalhos / "core").symlink_to("../platafirma-core/current")
    (atalhos / "arquitetura").symlink_to("../v0.1.0/arquitetura")

    # Venvs: um vivo (harness), um fóssil sem atalho, um atalho não declarado (espelho-controle)
    venv_vivo = raiz / "venv" / "harness-aaaa1111"
    venv_morto = raiz / "venv" / "harness-bbbb2222"
    venv_espelho = raiz / "venv" / "espelho-controle-cccc3333"
    for d in (venv_vivo, venv_morto, venv_espelho):
        d.mkdir(parents=True)
    (atalhos / "venv").mkdir(parents=True)
    (atalhos / "venv" / "harness").symlink_to("../../venv/harness-aaaa1111")
    (atalhos / "venv" / "espelho-controle").symlink_to("../../venv/espelho-controle-cccc3333")

    # Registro de venvs declarando apenas harness
    reg_venvs = tmp_path / "venvs.json"
    reg_venvs.write_text(
        json.dumps({"harness": {"familia": "platafirma-harness", "lock": "venvs/harness/uv.lock"}}),
        encoding="utf-8",
    )

    # Abertura publicada fóssil
    (abertura / "refs" / "74bc644").mkdir(parents=True)
    (abertura / "current").symlink_to("refs/74bc644")

    return raiz, inst, reg_venvs


def test_release_reverter_retirado_politica_0009(tmp_path: Path):
    e = _env(tmp_path)
    p = subprocess.run([RELEASE, "reverter", "platafirma-core"], env=e, capture_output=True, text=True)
    assert p.returncode == 2
    assert "política 0009" in p.stderr.lower()


def test_release_expurgar_ver_nao_apaga_e_expurgar_limpa_tudo_fora_do_current(tmp_path: Path):
    raiz, inst, reg_venvs = _montar_fosseis(tmp_path)
    e = _env(tmp_path)
    e["PLATAFIRMA_VENVS"] = str(reg_venvs)

    # Dry-run (--ver): relata sem apagar
    r_ver = subprocess.run([RELEASE, "expurgar", "--ver"], env=e, capture_output=True, text=True)
    assert r_ver.returncode == 0, r_ver.stderr
    assert "raiz:v0.1.0" in r_ver.stdout
    assert "raiz:v0.2.0" in r_ver.stdout
    assert "anterior:platafirma-core" in r_ver.stdout
    assert "venv:harness-bbbb2222" in r_ver.stdout
    assert "atalho-venv:espelho-controle" in r_ver.stdout
    assert "abertura-publicada" in r_ver.stdout
    assert (raiz / "v0.1.0").exists()
    assert (inst / "var" / "abertura-publicada").exists()

    # Execução efetiva: apaga todos os fósseis e preserva current, .repo.git e venv em uso
    r = subprocess.run([RELEASE, "expurgar"], env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    assert not (raiz / "v0.1.0").exists()
    assert not (raiz / "v0.2.0").exists()
    assert not (raiz / "anterior").exists()
    assert not (raiz / "platafirma-core" / "anterior").exists()
    assert not (raiz / "platafirma-core" / ("2" * 40)).exists()
    assert not (inst / "var" / "release" / "platafirma-core" / "anterior").exists()
    assert not (raiz / "current" / "arquitetura").is_symlink()
    assert not (raiz / "current" / "venv" / "espelho-controle").is_symlink()
    assert not (raiz / "venv" / "harness-bbbb2222").exists()
    assert not (raiz / "venv" / "espelho-controle-cccc3333").exists()
    assert not (inst / "var" / "abertura-publicada").exists()

    # Preservados:
    assert (raiz / "platafirma-core" / "current").is_symlink()
    assert (raiz / "platafirma-core" / ("1" * 40) / "vivo.txt").is_file()
    assert (raiz / "platafirma-core" / ".repo.git").is_dir()
    assert (raiz / "current" / "core").is_symlink()
    assert (raiz / "current" / "venv" / "harness").is_symlink()
    assert (raiz / "venv" / "harness-aaaa1111").is_dir()
