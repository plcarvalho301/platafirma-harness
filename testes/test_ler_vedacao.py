# componente: componente:leitura
"""Testes da vedação de superfícies sensíveis em toda árvore de leitura (story #4442, t1)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from leitura.morada import eh_segredo
from leitura.verbo import ler_conteudo_verbo

RAIZ_HARNESS = Path(__file__).resolve().parents[1]
BIN_RELEASE = RAIZ_HARNESS / "bin" / "release"
BIN_REPO = RAIZ_HARNESS / "bin" / "repo"

CAMPOS_RECUSA = ("codigo", "onde", "recebido", "regra", "cura", "proximo")


@pytest.mark.parametrize(
    "caminho",
    [
        "",
        "   ",
        "a\x00b",
        ".env",
        ".env.local",
        "app/.env.production",
        "certs/priv.pem",
        "certs/server.key",
        "segredos/banco.txt",
        "a/segredos/token",
        "acesso/politica.yaml",
        "acesso/sub/../politica.yaml",
        "politica-acesso/regras.yaml",
        "sujeitos.yaml",
        "acesso/sujeitos.yaml",
        "var/trilha/2026-11-25.jsonl",
        "trilha/bruta.jsonl",
        "porta/trilha/turnos.jsonl",
        "logs/oplog.jsonl",
        "/srv/platafirma/casa/var/trilha/sessao.jsonl",
        "/srv/platafirma/casa/segredos/olaria",
    ],
)
def test_eh_segredo_bloqueia_superficies_vedadas(caminho: str) -> None:
    assert eh_segredo(caminho) is True


@pytest.mark.parametrize(
    "caminho",
    [
        "README.md",
        "lib/leitura/morada.py",
        "acesso/README.md",
        "testes/test_trilha.py",
        "docs/guia-env.md",
    ],
)
def test_eh_segredo_permite_caminhos_comuns(caminho: str) -> None:
    assert eh_segredo(caminho) is False


def test_verbo_recusa_vedado_antes_de_abrir_com_json_seis_campos(tmp_path: Path) -> None:
    vedado_existente = tmp_path / "acesso" / "politica.yaml"
    vedado_existente.parent.mkdir(parents=True)
    vedado_existente.write_text("segredo: sim\n", encoding="utf-8")
    vedado_inexistente = tmp_path / "acesso" / "sujeitos.yaml"

    for alvo in (vedado_existente, vedado_inexistente):
        rc, out_b, err_s, meta = ler_conteudo_verbo(caminho=alvo)
        assert rc == 4
        assert out_b == b""
        payload = json.loads(err_s)
        assert tuple(payload.keys()) == CAMPOS_RECUSA
        assert payload["codigo"] == "segredo-fora-do-leitor"
        assert meta["recusado"] is True


def _criar_arvore_git(dest: Path, *, destacado: bool = False) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "acesso").mkdir(exist_ok=True)
    (dest / "acesso" / "politica.yaml").write_text("regra_secreta_xyz: negar\n", encoding="utf-8")
    (dest / ".env").write_text("TOKEN_SECRETO_XYZ=123\n", encoding="utf-8")
    (dest / "trilha").mkdir(exist_ok=True)
    (dest / "trilha" / "sessao.jsonl").write_text('{"evento":"trilha_secreta_xyz"}\n', encoding="utf-8")
    (dest / "publico.txt").write_text("linha_publica_abc politica\n", encoding="utf-8")
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=dest, check=True, env=git_env)
    subprocess.run(["git", "add", "."], cwd=dest, check=True, env=git_env)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=dest, check=True, env=git_env)
    if destacado:
        subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], cwd=dest, check=True, env=git_env)


def test_release_ler_e_procurar_vedam_superficies(tmp_path: Path) -> None:
    rel_raiz = tmp_path / "release"
    familia = rel_raiz / "platafirma-core"
    tmp_dir = familia / "tmp_init"
    _criar_arvore_git(tmp_dir, destacado=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_dir, text=True).strip()
    versao_dir = familia / sha
    tmp_dir.rename(versao_dir)
    (familia / "current").symlink_to(versao_dir)
    subprocess.run(["chmod", "-R", "a-w", str(versao_dir)], check=True)
    try:
        env = {
            **os.environ,
            "PF_RELEASE_RAIZ": str(rel_raiz),
            "PLATAFIRMA_RELEASE_RAIZ": str(rel_raiz),
            "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
        }

        r_ler = subprocess.run(
            [str(BIN_RELEASE), "ler", "platafirma-core", "acesso/politica.yaml"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_ler.returncode == 4, r_ler.stderr
        assert r_ler.stdout == ""
        payload = json.loads(r_ler.stderr.strip().splitlines()[-1])
        assert tuple(payload.keys()) == CAMPOS_RECUSA
        assert payload["codigo"] == "segredo-fora-do-leitor"

        r_proc_so_vedado = subprocess.run(
            [str(BIN_RELEASE), "procurar", "platafirma-core", "regra_secreta_xyz"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_proc_so_vedado.returncode == 0, r_proc_so_vedado.stderr
        assert "acesso/politica.yaml" not in r_proc_so_vedado.stdout
        assert "não encontrado" in r_proc_so_vedado.stdout
        assert r_proc_so_vedado.stderr == ""

        r_proc_misto = subprocess.run(
            [str(BIN_RELEASE), "procurar", "platafirma-core", "politica|regra_secreta_xyz"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_proc_misto.returncode == 0, r_proc_misto.stderr
        assert "publico.txt" in r_proc_misto.stdout
        assert "acesso/politica.yaml" not in r_proc_misto.stdout
    finally:
        subprocess.run(["chmod", "-R", "u+w", str(versao_dir)], check=False)


def test_repo_ler_e_procurar_vedam_superficies(tmp_path: Path) -> None:
    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / "platafirma-core" / "engenharia" / "4442-teste"
    _criar_arvore_git(wt)

    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": "engenharia",
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
    }

    r_ler = subprocess.run(
        [str(BIN_REPO), "ler", "platafirma-core@4442-teste", "acesso/politica.yaml"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_ler.returncode == 4, r_ler.stderr
    assert r_ler.stdout == ""
    payload = json.loads(r_ler.stderr.strip().splitlines()[-1])
    assert tuple(payload.keys()) == CAMPOS_RECUSA
    assert payload["codigo"] == "segredo-fora-do-leitor"

    r_proc_so_vedado = subprocess.run(
        [str(BIN_REPO), "procurar", "platafirma-core@4442-teste", "TOKEN_SECRETO_XYZ"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_proc_so_vedado.returncode == 0, r_proc_so_vedado.stderr
    assert ".env" not in r_proc_so_vedado.stdout
    assert "não encontrado" in r_proc_so_vedado.stdout
    assert r_proc_so_vedado.stderr == ""

    r_proc_misto = subprocess.run(
        [str(BIN_REPO), "procurar", "platafirma-core@4442-teste", "politica|TOKEN_SECRETO_XYZ"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_proc_misto.returncode == 0
    assert "publico.txt" in r_proc_misto.stdout
    assert ".env" not in r_proc_misto.stdout
    assert "acesso/politica.yaml" not in r_proc_misto.stdout
