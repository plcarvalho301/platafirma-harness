"""Contrato do estágio 4 de `release promover` (card #3150, trava "sem resposta do
arquiteto, implementar como cliente de tarefas"): depois de trocar current, resolve
o card pelo PR que mesclou o sha (nunca da mensagem de commit), comenta e move para
em-homologacao, e confere o card — tudo via `tarefas`/`release conferir card`
diretos. Ramo fora do padrão `fabrica/<card>-...`, ou `gh`/registro indisponível,
pula o estágio sem barrar a promoção.

Isola o mesmo Ambiente de test_release_construir_venv_registro.py, com um `gh` e um
`tarefas` de mentira em PATH (gravam o que foram chamados; git redireciona a URL
"github.com" declarada para o forge bare local via url.insteadOf — sem rede).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "release"

LOCK_SEM_DEP = "# fixture: venv vazio, sem dependência\n"
URL_FAKE = "https://github.com/exemplo/fixture.git"


def _python_de_sistema() -> str:
    casa = str(Path.home())
    for candidato in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if candidato and os.path.isabs(candidato) and os.access(candidato, os.X_OK) \
                and not candidato.startswith(casa):
            return candidato
    pytest.skip("nenhum python de sistema fora do HOME para construir venv de fixture")


def _git(cwd: Path, *args: str, env=None) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True, env=env)


def _escreve(base: Path, rel: str, texto: str) -> None:
    caminho = base / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def _commit(wt: Path, msg: str, env=None) -> str:
    _git(wt, "add", "-A", env=env)
    _git(wt, "commit", "-q", "-m", msg, env=env)
    r = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"],
                        capture_output=True, text=True, check=True, env=env)
    return r.stdout.strip()


class Ambiente:
    def __init__(self, tmp_path: Path, python_exe: str):
        self.tmp = tmp_path
        self.wt = tmp_path / "wt" / "fixture"
        self.forge = tmp_path / "forge" / "fixture.git"
        self.wt.mkdir(parents=True)
        self.forge.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)],
                        check=True, capture_output=True)

        # url.insteadOf: a URL "github.com" declarada no registro de familias e
        # exigida pelo regex de resolver_card_do_sha, mas o git de fato usa o
        # forge bare local — sem rede.
        gitconfig = tmp_path / "gitconfig"
        gitconfig.write_text(
            f'[url "{self.forge}"]\n    insteadOf = {URL_FAKE}\n', encoding="utf-8")

        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        self.tarefas_log = tmp_path / "tarefas.log"
        self.release_log = tmp_path / "release-chamadas.log"

        acervo_stub = stub_bin / "acervo"
        acervo_stub.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = ler ] && [ \"$2\" = casa ] && [ \"$3\" = stack ]; then echo '[]'; exit 0; fi\n"
            "exit 1\n", encoding="utf-8")
        acervo_stub.chmod(0o755)

        gh_stub = stub_bin / "gh"
        gh_stub.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = api ]; then printf '%s\\n' \"${GH_STUB_REF:-}\"; exit 0; fi\n"
            "exit 1\n", encoding="utf-8")
        gh_stub.chmod(0o755)

        tarefas_stub = stub_bin / "tarefas"
        tarefas_stub.write_text(
            "#!/usr/bin/env bash\n"
            "{\n"
            "  printf 'ARGS: %s\\n' \"$*\"\n"
            "  if [ \"$1\" = comentar ]; then printf 'STDIN: '; cat; printf '\\n'; fi\n"
            "  printf -- '---\\n'\n"
            "} >> \"$TAREFAS_LOG\"\n"
            "exit 0\n", encoding="utf-8")
        tarefas_stub.chmod(0o755)

        release_stub = stub_bin / "release"
        release_stub.write_text(
            "#!/usr/bin/env bash\n"
            "printf 'ARGS: %s\\n' \"$*\" >> \"$RELEASE_LOG\"\n"
            "exit 0\n", encoding="utf-8")
        release_stub.chmod(0o755)

        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        _escreve(self.wt, "lock.txt", LOCK_SEM_DEP)
        self.sha1 = _commit(self.wt, "fixture inicial")
        _git(self.wt, "remote", "add", "origin", str(self.forge))
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        self.env = dict(os.environ)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
        self.env["PLATAFIRMA_FAMILIAS"] = str(tmp_path / "familias.json")
        self.env["PLATAFIRMA_VENVS"] = str(tmp_path / "venvs.json")
        self.env["PLATAFIRMA_TERCEIROS"] = str(tmp_path / "terceiros.json")
        self.env["PLATAFIRMA_PYTHON"] = python_exe
        self.env["PF_RELEASE_PORTA"] = "0"
        self.env["GIT_CONFIG_GLOBAL"] = str(gitconfig)
        self.env["TAREFAS_LOG"] = str(self.tarefas_log)
        self.env["RELEASE_LOG"] = str(self.release_log)
        Path(self.env["PLATAFIRMA_FAMILIAS"]).write_text(
            json.dumps({"fixture": URL_FAKE}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text(
            json.dumps({"fx": {"familia": "fixture", "lock": "lock.txt"}}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")
        self.env["PATH"] = f"{stub_bin}{os.pathsep}" + self.env.get("PATH", "")

    def run(self, *args: str, gh_ref: str = "") -> subprocess.CompletedProcess:
        env = dict(self.env)
        env["GH_STUB_REF"] = gh_ref
        return subprocess.run([str(SCRIPT), *args], env=env,
                               capture_output=True, text=True, timeout=90)

    def commit(self, arquivos: dict) -> str:
        for rel, texto in arquivos.items():
            _escreve(self.wt, rel, texto)
        sha = _commit(self.wt, f"fixture: {', '.join(arquivos)}")
        _git(self.wt, "push", "-q", "origin", "main")
        return sha


@pytest.fixture()
def amb(tmp_path):
    return Ambiente(tmp_path, _python_de_sistema())


def test_estagio_card_resolve_e_comenta_e_move(amb):
    r = amb.run("promover", "fixture", gh_ref="fabrica/4242-teste-estagio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "card:      4242 comentado" in r.stdout

    log = amb.tarefas_log.read_text(encoding="utf-8")
    assert "ARGS: comentar 4242" in log
    assert "Estagio 4" in log
    assert "ARGS: mover 4242 em-homologacao" in log

    release_log = amb.release_log.read_text(encoding="utf-8")
    assert "ARGS: conferir card 4242" in release_log


def test_estagio_card_pula_sem_pr_fabrica(amb):
    r = amb.run("promover", "fixture", gh_ref="ti/algum-ramo-de-mesa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "estagio 4 pulado" in r.stdout
    assert not amb.tarefas_log.exists()


def test_estagio_card_pula_sem_pr_nenhum(amb):
    r = amb.run("promover", "fixture", gh_ref="")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "estagio 4 pulado" in r.stdout
    assert not amb.tarefas_log.exists()
