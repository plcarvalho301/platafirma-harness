"""Cobertura dos DTs 8, 452, 476 e 524 em bin/repo."""

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN_REPO = RAIZ / "bin" / "repo"


def _prepara_bancada(tmp_path: Path):
    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / "demo" / "engenharia" / "dt-teste"
    (wt / "dir1").mkdir(parents=True)
    (wt / "dir2").mkdir(parents=True)
    (wt / "dir3").mkdir(parents=True)

    (wt / "dir1" / "a.txt").write_text(
        "Cultura organizacional\n--necessidade\n-h flag\n--help flag\n",
        encoding="utf-8",
    )
    (wt / "dir2" / "b.txt").write_text("pressuposto basico\nCultura dois\n", encoding="utf-8")
    (wt / "dir3" / "c.txt").write_text("Cultura tres\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(wt), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "Teste"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "clone", "-q", str(wt), str(bancada / "demo")], check=True)

    env = os.environ.copy()
    env["PLATAFIRMA_BANCADA"] = str(bancada)
    env["PF_CADEIRA"] = "engenharia"
    return env, wt


def _roda(env, *args):
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_dt8_procurar_multiplos_caminhos_e_recusa_escape(tmp_path):
    env, _ = _prepara_bancada(tmp_path)

    r1 = _roda(env, "procurar", "demo", "Cultura", "dir1", "dir2")
    assert r1.returncode == 0, r1.stderr
    assert "dir1/a.txt:1:Cultura organizacional" in r1.stdout
    assert "dir2/b.txt:2:Cultura dois" in r1.stdout
    assert "dir3/c.txt" not in r1.stdout

    r2 = _roda(env, "procurar", "demo", "--termo", "Cultura", "--caminho", "dir1", "--caminho", "dir3")
    assert r2.returncode == 0, r2.stderr
    assert "dir1/a.txt" in r2.stdout
    assert "dir3/c.txt" in r2.stdout
    assert "dir2/b.txt" not in r2.stdout

    r_esc = _roda(env, "procurar", "demo", "Cultura", "dir1", "../fora")
    assert r_esc.returncode == 4


def test_dt8_pr_diff_filtro_caminho_stat_name_only_e_aviso_50kb(tmp_path):
    env, _ = _prepara_bancada(tmp_path)
    fake_gh = tmp_path / "fake_gh.sh"
    diff_body = tmp_path / "diff_body.txt"
    big_line = "+" + ("x" * 600) + "\n"
    diff_body.write_text(
        "diff --git a/dir1/a.txt b/dir1/a.txt\n"
        "--- a/dir1/a.txt\n+++ b/dir1/a.txt\n@@ -1 +1,2 @@\n+linha1\n"
        "diff --git a/dir2/b.txt b/dir2/b.txt\n"
        "--- a/dir2/b.txt\n+++ b/dir2/b.txt\n@@ -1 +1,100 @@\n" + (big_line * 90),
        encoding="utf-8",
    )
    fake_gh.write_text(
        f"""#!/usr/bin/env bash
if [ "$1" = "pr" ] && [ "$2" = "diff" ]; then
  if [ "${{4:-}}" = "--name-only" ]; then
    printf 'dir1/a.txt\\ndir2/b.txt\\n'
  else
    cat "{diff_body}"
  fi
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    env["PF_GH_BIN"] = str(fake_gh)

    r_dir1 = _roda(env, "pr-diff", "demo", "42", "dir1")
    assert r_dir1.returncode == 0, r_dir1.stderr
    assert "dir1/a.txt" in r_dir1.stdout
    assert "dir2/b.txt" not in r_dir1.stdout

    r_stat = _roda(env, "pr-diff", "demo", "42", "--stat", "--caminho", "dir1")
    assert r_stat.returncode == 0, r_stat.stderr
    assert "dir1/a.txt | +1 -0" in r_stat.stdout
    assert "dir2/b.txt" not in r_stat.stdout

    r_names = _roda(env, "pr-diff", "demo", "42", "--name-only", "--caminho", "dir2")
    assert r_names.returncode == 0, r_names.stderr
    assert r_names.stdout.strip() == "dir2/b.txt"

    r_big = _roda(env, "pr-diff", "demo", "42")
    assert r_big.returncode == 0
    assert "(> 50 KB)" in r_big.stderr


def test_dt452_repo_git_repassa_h_e_e_sem_cair_na_usage(tmp_path):
    env, _ = _prepara_bancada(tmp_path)

    r = _roda(env, "git", "demo", "grep", "-h", "-E", "-e", "Cultura", "-e", "pressuposto", "HEAD", "--", "dir1", "dir2")
    assert r.returncode == 0, r.stderr
    assert "Cultura organizacional" in r.stdout
    assert "pressuposto basico" in r.stdout
    assert "dir1/a.txt:" not in r.stdout  # -h do git grep suprimiu nome do arquivo

    r_help = _roda(env, "git", "--help")
    assert r_help.returncode == 2
    assert "uso:" in r_help.stderr


def test_dt476_procurar_termo_com_tracos_e_ajuda(tmp_path):
    env, _ = _prepara_bancada(tmp_path)

    r1 = _roda(env, "procurar", "demo", "--", "--necessidade")
    assert r1.returncode == 0, r1.stderr
    assert "dir1/a.txt:2:--necessidade" in r1.stdout

    r2 = _roda(env, "procurar", "demo", "--termo", "--help")
    assert r2.returncode == 0, r2.stderr
    assert "dir1/a.txt:4:--help flag" in r2.stdout

    r3 = _roda(env, "procurar", "demo", "--", "-h")
    assert r3.returncode == 0, r3.stderr
    assert "dir1/a.txt:3:-h flag" in r3.stdout


def test_dt524_procurar_regex_ere_e_ignore_case(tmp_path):
    env, _ = _prepara_bancada(tmp_path)

    r1 = _roda(env, "procurar", "demo", "[Cc]ultura|[Pp]ressup")
    assert r1.returncode == 0, r1.stderr
    assert "dir1/a.txt:1:Cultura organizacional" in r1.stdout
    assert "dir2/b.txt:1:pressuposto basico" in r1.stdout

    r2 = _roda(env, "procurar", "demo", "-i", "cultura")
    assert r2.returncode == 0, r2.stderr
    assert "dir1/a.txt:1:Cultura organizacional" in r2.stdout

    r3 = _roda(env, "procurar", "demo", "-F", "[Cc]ultura")
    assert r3.returncode == 0, r3.stderr
    assert "não encontrado" in r3.stdout
