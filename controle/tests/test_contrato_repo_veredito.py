"""Contrato da publicacao do veredito do portao no forge (incidente #4196, feature #4027).

Git real contra bare local; o forge e um `gh` de fixture (PF_GH_BIN) que anota cada chamada
de `gh api`. A marca do portao e escrita a mao no lugar em que `hooks/pre-push` a grava
(<instancia>/var/pre-push/vereditos/portao-<repo>-<sha>). Prova: com marca `verde`, o
`empurrar` publica o commit status `esteira/portao` de sucesso no sha empurrado; sem marca,
nada se publica e o retorno diz que a esteira nao integra sem veredito; marca `sem-suite`
publica com o motivo escrito; forge que recusa o status nao muda o exit do push; `pr-abrir`
publica de novo e aponta `pr-ver`, nao mais `pr-merge`.
Nao prova: o hook gravando a marca (os clones de teste nao tem hooksPath), o GitHub de
verdade aceitando o status, nem o workflow esteira-integra.yml integrando o PR.
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

GH_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
if [ "$1" = api ]; then
  [ -f "$d/recusa" ] && exit 1
  echo "$*" >> "$d/api"
  exit 0
fi
case "$1 $2" in
  "pr list") [ -f "$d/pr" ] && cat "$d/pr"; exit 0 ;;
  "pr create") echo "#7 OPEN https://forge/pr/7 (head abc1234)" > "$d/pr"; exit 0 ;;
  "pr view") cat "$d/pr" ;;
  *) exit 9 ;;
esac
"""


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}).stdout.strip()


def _montar(tmp_path):
    origem = tmp_path / "origem.git"
    semente = tmp_path / "semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    (semente / "LEIA.md").write_text("x\n")
    _git("add", "LEIA.md", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    forge = tmp_path / "forge"
    forge.mkdir()
    gh = forge / "gh"
    gh.write_text(GH_FIXTURE)
    gh.chmod(0o755)
    return bancada, forge


def _repo(tmp_path, bancada, *args, extra=None):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "PF_GH_BIN": str(tmp_path / "forge" / "gh"),
        # sem hook por padrao (debito 604): o hook real mediria o clone de fixture; so os testes
        # do 604 apontam um hook de fixture
        "PF_HOOK_PREPUSH": "/nao-existe/pre-push",
        **IDENT,
        **(extra or {}),
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _commit_na_bancada(tmp_path, bancada, marca=None):
    """Bancada do card 42 com um commit ainda nao empurrado; grava a marca do portao, se pedida."""
    r = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "ti" / "42-x"
    (wt / "CARD.md").write_text("trabalho\n")
    _git("add", "CARD.md", cwd=wt)
    _git("commit", "-m", "card: CARD.md", cwd=wt)
    sha = _git("rev-parse", "HEAD", cwd=wt)
    if marca is not None:
        pasta = tmp_path / "instancia" / "var" / "pre-push" / "vereditos"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"portao-demo-{sha}").write_text(marca + "\n")
    return wt, sha


def test_marca_verde_publica_status_de_sucesso_no_sha_empurrado(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada, marca="verde harness-0123456789ab")
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    chamada = (forge / "api").read_text()
    assert f"repos/plcarvalho301/demo/statuses/{sha}" in chamada
    assert "state=success" in chamada
    assert "context=esteira/portao" in chamada
    assert "harness-0123456789ab" in chamada
    assert f"veredito publicado: esteira/portao verde em {sha[:7]} (verde)" in r.stdout


def test_sem_marca_nada_publica_e_diz_que_a_esteira_nao_integra(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada)
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (forge / "api").exists()
    assert f"sem medida do portão para {sha[:7]}" in r.stdout
    assert "não integra PR sem veredito" in r.stdout


HOOK_FIXTURE = """#!/bin/sh
# faz o papel do hooks/pre-push: le a linha do stdin e grava a marca da rev, como o hook real
read -r _ oid _ _
echo "$oid" >> "$(dirname "$0")/mediu"
d="$PLATAFIRMA_INSTANCIA/var/pre-push/vereditos"
mkdir -p "$d"
[ -f "$(dirname "$0")/vermelho" ] && exit 1
echo "verde demo-0123456789ab" > "$d/portao-demo-$oid"
"""


def _hook_de_fixture(tmp_path):
    pasta = tmp_path / "hookfix"
    pasta.mkdir()
    hook = pasta / "pre-push"
    hook.write_text(HOOK_FIXTURE)
    hook.chmod(0o755)
    return pasta, hook


def _repo_com_hook(tmp_path, bancada, hook, *args):
    return _repo(tmp_path, bancada, *args, extra={"PF_HOOK_PREPUSH": str(hook)})


def test_sem_marca_o_empurrar_mede_pelo_hook_e_publica_debito_604(tmp_path):
    """Clone sem core.hooksPath empurra sem o hook rodar (PR #66 do #4234): sem marca, o verbo
    chama o hook com a rev empurrada, e a marca que ele grava vira o status."""
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada)
    pasta, hook = _hook_de_fixture(tmp_path)
    r = _repo_com_hook(tmp_path, bancada, hook, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (pasta / "mediu").read_text().split() == [sha]
    assert f"statuses/{sha}" in (forge / "api").read_text()
    assert f"veredito publicado: esteira/portao verde em {sha[:7]}" in r.stdout


def test_hook_vermelho_nao_publica_debito_604(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada)
    pasta, hook = _hook_de_fixture(tmp_path)
    (pasta / "vermelho").write_text("x\n")
    r = _repo_com_hook(tmp_path, bancada, hook, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (forge / "api").exists()
    assert f"sem medida do portão para {sha[:7]}" in r.stdout


def test_marca_ja_gravada_nao_mede_de_novo_debito_604(tmp_path):
    bancada, forge = _montar(tmp_path)
    _commit_na_bancada(tmp_path, bancada, marca="verde harness-0123456789ab")
    pasta, hook = _hook_de_fixture(tmp_path)
    r = _repo_com_hook(tmp_path, bancada, hook, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (pasta / "mediu").exists()
    assert (forge / "api").exists()


def test_marca_sem_suite_publica_com_o_motivo(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada, marca="sem-suite")
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    chamada = (forge / "api").read_text()
    assert f"statuses/{sha}" in chamada
    assert "sem chave de teste" in chamada
    assert "(sem-suite)" in r.stdout


def test_marca_ilegivel_nao_publica(tmp_path):
    bancada, forge = _montar(tmp_path)
    _commit_na_bancada(tmp_path, bancada, marca="vermelho")
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (forge / "api").exists()
    assert "marca ilegível" in r.stdout


def test_forge_que_recusa_o_status_nao_derruba_o_push(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada, marca="verde harness-0123456789ab")
    (forge / "recusa").write_text("x\n")
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "empurrado: demo -> origin/fabrica/42-x" in r.stdout
    assert f"o forge recusou o status de {sha[:7]}" in r.stdout
    assert "veredito publicado" not in r.stdout


def test_pr_abrir_publica_e_aponta_pr_ver_no_lugar_de_pr_merge(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada, marca="verde harness-0123456789ab")
    assert _repo(tmp_path, bancada, "empurrar", "demo").returncode == 0
    (forge / "api").unlink()
    r = _repo(tmp_path, bancada, "pr-abrir", "demo", "--titulo", "t")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"statuses/{sha}" in (forge / "api").read_text()
    assert "a esteira integra o PR com veredito verde" in r.stdout
    assert "repo pr-ver demo 7" in r.stdout
    assert "repo pr-merge" not in r.stdout
    de_novo = _repo(tmp_path, bancada, "pr-abrir", "demo", "--titulo", "t")
    assert de_novo.returncode == 0, de_novo.stdout + de_novo.stderr
    assert "já feito: PR #7" in de_novo.stdout
    assert "repo pr-ver demo 7" in de_novo.stdout
    assert "repo pr-merge" not in de_novo.stdout
