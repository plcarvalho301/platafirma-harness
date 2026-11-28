# componente: componente:verbo-release
"""Provas dos DTs 1199 (espera de reinício pendente da porta) e 1200 (retomada por etapa após SIGTERM)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BIN_RELEASE = RAIZ / "bin" / "release"


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


def test_bin_release_sintaxe_bash_valida() -> None:
    res = subprocess.run(["bash", "-n", str(BIN_RELEASE)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_dt1199_espera_reinicio_pendente_da_porta_ate_novo_timestamp(tmp_path: Path) -> None:
    pontos = tmp_path / "pontos"
    pontos.mkdir()
    marcador = pontos / ".porta.reinicio_pendente"
    marcador.write_text(
        f"agendado_em={int(time.time())}\nporta_inicio=1000\n",
        encoding="utf-8",
    )

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    contador = tmp_path / "contador"
    contador.write_text("0", encoding="utf-8")
    systemctl_stub = stubs / "systemctl"
    systemctl_stub.write_text(
        "#!/usr/bin/env bash\n"
        f"c=$(cat '{contador}')\n"
        "c=$((c + 1))\n"
        f"printf '%s' \"$c\" > '{contador}'\n"
        "if [[ \"$*\" == *ActiveState* ]]; then\n"
        "  echo active\n"
        "elif [[ \"$*\" == *ActiveEnterTimestampMonotonic* ]]; then\n"
        "  if [ \"$c\" -ge 4 ]; then echo 2000; else echo 1000; fi\n"
        "fi\n",
        encoding="utf-8",
    )
    systemctl_stub.chmod(0o755)

    # Extrai e testa a função esperar_reinicio_pendente_porta diretamente do bin/release
    script = (
        "set -euo pipefail\n"
        f"PONTOS='{pontos}'\n"
        "PF_PORTA_REINICIO_ESPERA=10\n"
        "PF_PORTA_REINICIO_PASSO=0.05\n"
        f"eval \"$(sed -n '/^esperar_reinicio_pendente_porta()/,/^}}/p' '{BIN_RELEASE}')\"\n"
        "esperar_reinicio_pendente_porta\n"
    )
    env = dict(os.environ)
    env["PATH"] = f"{stubs}:{env.get('PATH', '')}"
    res = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, res.stderr
    assert "reinício pendente da porta" in res.stderr
    assert "porta voltou" in res.stderr
    assert not marcador.exists()
    assert int(contador.read_text(encoding="utf-8")) >= 4


def test_dt1200_promover_retoma_etapa_pendente_quando_current_ja_trocou(tmp_path: Path) -> None:
    # Cria repositório bare + commit de origem
    origem = tmp_path / "origem.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origem)], check=True, capture_output=True)
    trab = tmp_path / "trab"
    subprocess.run(["git", "clone", str(origem), str(trab)], check=True, capture_output=True)
    _git(trab, "config", "user.email", "teste@platafirma.local")
    _git(trab, "config", "user.name", "Teste")
    (trab / "README.md").write_text("v1\n", encoding="utf-8")
    _git(trab, "add", "README.md")
    _git(trab, "commit", "-m", "v1")
    sha1 = _git(trab, "rev-parse", "HEAD")
    (trab / "README.md").write_text("v2\n", encoding="utf-8")
    _git(trab, "add", "README.md")
    _git(trab, "commit", "-m", "v2")
    sha2 = _git(trab, "rev-parse", "HEAD")
    _git(trab, "push", "origin", "main")

    prod_raiz = tmp_path / "prod"
    instancia = tmp_path / "instancia"
    repo_dir = prod_raiz / "platafirma-demo"
    repo_dir.mkdir(parents=True)
    espelho = repo_dir / ".repo.git"
    subprocess.run(["git", "clone", "--bare", str(origem), str(espelho)], check=True, capture_output=True)
    _git(espelho, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
    _git(espelho, "fetch", "origin")
    subprocess.run(
        ["git", f"--git-dir={espelho}", "worktree", "add", "--detach", str(repo_dir / sha2), sha2],
        check=True,
        capture_output=True,
    )
    subprocess.run(["chmod", "-R", "a-w", str(repo_dir / sha2)], check=True)
    os.symlink(repo_dir / sha2, repo_dir / "current")

    familias = tmp_path / "familias.json"
    familias.write_text(json.dumps({"platafirma-demo": str(origem)}), encoding="utf-8")
    venvs = tmp_path / "venvs.json"
    venvs.write_text("{}", encoding="utf-8")

    # Simula morte por SIGTERM após trocar_current, antes do fechamento
    pontos_repo = instancia / "var" / "release" / "platafirma-demo"
    pontos_repo.mkdir(parents=True)
    etapa_arq = pontos_repo / "etapa_pendente"
    etapa_arq.write_text(f"sha={sha2}\natual={sha1}\netapa=fechamento\n", encoding="utf-8")

    stubs_bin = prod_raiz / "current" / "harness" / "bin"
    stubs_bin.mkdir(parents=True)
    acervo_stub = stubs_bin / "acervo"
    acervo_stub.write_text("#!/usr/bin/env bash\nprintf '[]\\n'\n", encoding="utf-8")
    acervo_stub.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{stubs_bin}:/usr/bin:/bin"
    env.update(
        {
            "PF_RELEASE_RAIZ": str(prod_raiz),
            "PLATAFIRMA_RELEASE": str(prod_raiz / "current"),
            "PLATAFIRMA_INSTANCIA": str(instancia),
            "PLATAFIRMA_FAMILIAS": str(familias),
            "PLATAFIRMA_VENVS": str(venvs),
            "PF_RELEASE_PORTA": "0",
            "PF_PROMOVER_VERBOSO": "1",
        }
    )

    # 1) --ensaio reconhece a etapa pendente e sai 0 (antes saía 1 "nada a mover")
    r_ensaio = subprocess.run(
        [str(BIN_RELEASE), "promover", "platafirma-demo", sha2, "--ensaio"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_ensaio.returncode == 0, f"rc={r_ensaio.returncode} stderr={r_ensaio.stderr!r} stdout={r_ensaio.stdout!r}"
    assert "retomando etapa: fechamento" in r_ensaio.stdout
    assert etapa_arq.exists()

    # 2) Execução real retoma, conclui e limpa etapa_pendente
    r_real = subprocess.run(
        [str(BIN_RELEASE), "promover", "platafirma-demo", sha2],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_real.returncode == 0, f"rc={r_real.returncode} stderr={r_real.stderr!r} stdout={r_real.stdout!r}"
    assert "retomando etapa: fechamento" in r_real.stdout
    assert not etapa_arq.exists()

    # 3) Repetição após concluído volta a sair 1 ("já no ar, nada a mover")
    r_pos = subprocess.run(
        [str(BIN_RELEASE), "promover", "platafirma-demo", sha2, "--ensaio"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r_pos.returncode == 1
    assert "já no ar" in r_pos.stdout
