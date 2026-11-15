"""Cobertura dos DTs 445, 588, 607 e 652 em bin/repo."""

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN_REPO = RAIZ / "bin" / "repo"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _prepara_com_origin(tmp_path: Path):
    origem = tmp_path / "origem.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origem)], check=True)

    semente = tmp_path / "semente"
    subprocess.run(["git", "clone", "-q", str(origem), str(semente)], check=True)
    _git(semente, "config", "user.name", "Teste")
    _git(semente, "config", "user.email", "t@example.com")
    (semente / "dir1").mkdir()
    (semente / "dir1" / "a.txt").write_text(
        "Cultura organizacional\ndef bases():\n    return 1\n",
        encoding="utf-8",
    )
    _git(semente, "add", ".")
    _git(semente, "commit", "-q", "-m", "init")
    _git(semente, "push", "-q", "-u", "origin", "main")

    bancada = tmp_path / "bancada"
    bancada.mkdir()
    clone_base = bancada / "demo"
    subprocess.run(["git", "clone", "-q", str(origem), str(clone_base)], check=True)
    _git(clone_base, "config", "user.name", "Teste")
    _git(clone_base, "config", "user.email", "t@example.com")

    wt = bancada / "wt" / "demo" / "engenharia" / "dt-teste"
    wt.parent.mkdir(parents=True)
    _git(clone_base, "worktree", "add", "-q", "-b", "engenharia/dt-teste", str(wt), "origin/main")

    env = os.environ.copy()
    env["PLATAFIRMA_BANCADA"] = str(bancada)
    env["PF_CADEIRA"] = "engenharia"
    return env, bancada, origem, semente, wt


def _roda(env, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_dt445_repo_git_repassa_menos_h(tmp_path):
    env, *_ = _prepara_com_origin(tmp_path)

    r = _roda(env, "git", "demo", "grep", "-h", "Cultura", "HEAD", "--", "dir1")
    assert r.returncode == 0, r.stderr
    assert "Cultura organizacional" in r.stdout
    assert "dir1/a.txt:" not in r.stdout

    r_h = _roda(env, "git", "-h")
    assert r_h.returncode == 2
    assert "uso:" in r_h.stderr


def test_dt588_leitura_avisa_bancada_atras_de_origin_main(tmp_path):
    env, _, _, semente, wt = _prepara_com_origin(tmp_path)

    # Em dia: nenhum aviso de atraso
    r_ok = _roda(env, "ler", "demo", "dir1/a.txt")
    assert r_ok.returncode == 0, r_ok.stderr
    assert "atrás de origin/main" not in r_ok.stderr

    # Avanca origin/main em 2 commits sem atualizar a bancada
    for i in (1, 2):
        (semente / f"extra{i}.txt").write_text(f"v{i}\n", encoding="utf-8")
        _git(semente, "add", f"extra{i}.txt")
        _git(semente, "commit", "-q", "-m", f"extra {i}")
    _git(semente, "push", "-q", "origin", "main")
    _git(wt, "fetch", "-q", "origin")

    for cmd_args in (
        ("ler", "demo", "dir1/a.txt"),
        ("procurar", "demo", "Cultura"),
        ("historico", "demo"),
    ):
        r = _roda(env, *cmd_args)
        assert r.returncode == 0, r.stderr
        assert "atrás de origin/main por 2 commit(s)" in r.stderr


def test_dt652_procurar_preserva_espacos_no_termo(tmp_path):
    env, *_ = _prepara_com_origin(tmp_path)

    r_pos = _roda(env, "procurar", "demo", "def bases")
    assert r_pos.returncode == 0, r_pos.stderr
    assert "dir1/a.txt:2:def bases():" in r_pos.stdout

    r_flag = _roda(env, "procurar", "demo", "--termo", "def bases", "--json")
    assert r_flag.returncode == 0, r_flag.stderr
    dados = json.loads(r_flag.stdout)
    assert dados["termo"] == "def bases"
    assert dados["total"] == 1
    assert dados["ocorrencias"][0]["caminho"] == "dir1/a.txt"


def test_dt607_abrir_id_nao_numerico_recusa_e_ensina_slug(tmp_path):
    env, bancada, *_ = _prepara_com_origin(tmp_path)

    r_bad = _roda(env, "abrir", "demo", "dt605-verbo", "--slug", "infra-instalar")
    assert r_bad.returncode == 2
    assert "id de card deve ser numérico" in r_bad.stderr
    assert "--slug dt605-verbo-infra-instalar" in r_bad.stderr
    assert not (bancada / "wt" / "demo" / "engenharia" / "dt605-verbo-infra-instalar").exists()
    assert not (bancada / "wt" / "demo" / "engenharia" / "dt605-verbo").exists()

    r_good = _roda(env, "abrir", "demo", "--slug", "dt605-verbo-infra-instalar")
    assert r_good.returncode == 0, r_good.stderr
    assert "engenharia/dt605-verbo-infra-instalar" in r_good.stdout
