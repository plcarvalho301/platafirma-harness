"""Contrato de `repo lock` para projeto node (card #3386): o mesmo ato do uv.lock, agora com
package.json -> package-lock.json, sem script de pacote.

Git real contra bare local; node e npm sao scripts de fixture (PLATAFIRMA_NODE; o npm mora ao
lado do node) que registram a chamada e o ambiente e escrevem o lock pedido. Prova: o lock sai
de `npm install --package-lock-only --ignore-scripts` com a config de usuario e global
desligadas; a diferenca de pacotes (+ - ~) lida dos dois locks; nada commitado; lock igual diz
"ja em dia"; falha de indice sai 3 e deixa o lock como estava; sem solucao sai 1; --conferir
so mede (`npm ci --dry-run`: 0 em dia, 1 defasado) e nao escreve; node no home da conta e
recusado (3). Nao prova: o npm de verdade nem o registro de pacotes.
"""
import json
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

NODE_FIXTURE = "#!/bin/sh\necho v22.1.0\n"
NPM_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
printf '%s\\n' "$*" >> "$d/chamadas"
# o npm real recusa o mesmo caminho nas duas configs ("double-loading config", medido em 10/10): o falso tambem
if [ "${npm_config_userconfig:-}" = "${npm_config_globalconfig:-}" ]; then
  echo "double-loading config as global, previously loaded as user" >&2; exit 1
fi
u=sim; g=sim
[ -f "${npm_config_userconfig:-}" ] && [ ! -s "$npm_config_userconfig" ] || u=nao
[ -f "${npm_config_globalconfig:-}" ] && [ ! -s "$npm_config_globalconfig" ] || g=nao
printf '%s|%s|%s\\n' "$u" "$g" "${npm_config_registry:-}" > "$d/env"
case "$1" in
  ci)
    [ -f "$d/ci_err" ] && cat "$d/ci_err" >&2
    exit "$(cat "$d/ci_rc" 2>/dev/null || echo 0)" ;;
  install)
    if [ -f "$d/falha" ]; then cat "$d/falha" >&2; exit 1; fi
    cp "$d/novo.lock" "$PWD/package-lock.json" ;;
esac
"""


def _lock(pacotes: dict) -> str:
    return json.dumps({"name": "p", "lockfileVersion": 3, "packages": {
        "": {"name": "p"},
        **{f"node_modules/{n}": {"version": v} for n, v in pacotes.items()}}}, indent=2) + "\n"


LOCK_ANTES = _lock({"a": "1.0.0", "b": "1.0.0"})
LOCK_DEPOIS = _lock({"a": "1.1.0", "c": "2.0.0"})


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}).stdout.strip()


def _montar(tmp_path, com_lock=True):
    origem = tmp_path / "origem.git"
    semente = tmp_path / "semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    proj = semente / "front" / "prova"
    proj.mkdir(parents=True)
    (proj / "package.json").write_text('{"name": "p", "private": true}\n')
    if com_lock:
        (proj / "package-lock.json").write_text(LOCK_ANTES)
    _git("add", "front", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    ferr = tmp_path / "nodefix"
    ferr.mkdir()
    for nome, corpo in (("node", NODE_FIXTURE), ("npm", NPM_FIXTURE)):
        f = ferr / nome
        f.write_text(corpo)
        f.chmod(0o755)
    (ferr / "novo.lock").write_text(LOCK_DEPOIS)
    (tmp_path / "casa").mkdir()
    return bancada, ferr


def _repo(tmp_path, bancada, *args, node=None):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path / "casa"),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "PF_GH_BIN": "/bin/false",
        "PLATAFIRMA_NODE": node or str(tmp_path / "nodefix" / "node"),
        "npm_config_registry": "https://espelho.invalido/",   # nao pode chegar ao npm
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _aberta(tmp_path, com_lock=True):
    bancada, ferr = _montar(tmp_path, com_lock)
    r = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "l")
    assert r.returncode == 0, r.stderr
    return bancada, ferr, bancada / "wt" / "demo" / "ti" / "l"


def test_gera_lock_sem_script_de_pacote_e_relata_diferenca(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "lock: front/prova/package-lock.json atualizado" in r.stdout
    assert "  ~ a 1.0.0 -> 1.1.0" in r.stdout
    assert "  - b 1.0.0" in r.stdout
    assert "  + c 2.0.0" in r.stdout
    assert "próximo: repo commitar demo" in r.stdout
    assert (wt / "front" / "prova" / "package-lock.json").read_text() == LOCK_DEPOIS
    chamada = (ferr / "chamadas").read_text()
    assert "install --package-lock-only --ignore-scripts" in chamada
    # configs de usuario e global vazias e distintas, e registro trocado por variavel nao chega ao npm
    assert (ferr / "env").read_text().strip() == "sim|sim|"


def test_nao_commita(tmp_path):
    bancada, _, wt = _aberta(tmp_path)
    antes = _git("rev-parse", "HEAD", cwd=wt)
    _repo(tmp_path, bancada, "lock", "demo", "front/prova")
    assert _git("rev-parse", "HEAD", cwd=wt) == antes
    assert "package-lock.json" in _git("status", "--porcelain", cwd=wt)


def test_lock_igual_diz_ja_em_dia(tmp_path):
    bancada, ferr, _ = _aberta(tmp_path)
    (ferr / "novo.lock").write_text(LOCK_ANTES)
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "já em dia" in r.stdout


def test_projeto_novo_cria_o_lock(tmp_path):
    bancada, _, wt = _aberta(tmp_path, com_lock=False)
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "package-lock.json criado" in r.stdout
    assert (wt / "front" / "prova" / "package-lock.json").read_text() == LOCK_DEPOIS


def test_falha_de_indice_sai_3_e_deixa_o_lock_como_estava(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    (ferr / "falha").write_text("npm ERR! code ECONNREFUSED\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova")
    assert r.returncode == 3, r.stdout + r.stderr
    assert (wt / "front" / "prova" / "package-lock.json").read_text() == LOCK_ANTES


def test_sem_solucao_sai_1(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    (ferr / "falha").write_text("npm ERR! code ETARGET\nnpm ERR! notarget No matching version found\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova")
    assert r.returncode == 1, r.stdout + r.stderr
    assert (wt / "front" / "prova" / "package-lock.json").read_text() == LOCK_ANTES


def test_conferir_em_dia_nao_escreve(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova", "--conferir")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "em dia" in r.stdout
    assert "ci --dry-run --ignore-scripts" in (ferr / "chamadas").read_text()
    assert (wt / "front" / "prova" / "package-lock.json").read_text() == LOCK_ANTES


def test_conferir_defasado_sai_1(tmp_path):
    bancada, ferr, _ = _aberta(tmp_path)
    (ferr / "ci_rc").write_text("1")
    (ferr / "ci_err").write_text("npm ERR! `npm ci` can only install packages when your package.json "
                                 "and package-lock.json are in sync\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova", "--conferir")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "defasado" in r.stdout


def test_conferir_sem_lock_diz_defasado(tmp_path):
    bancada, _, _ = _aberta(tmp_path, com_lock=False)
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova", "--conferir")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "não existe" in r.stdout


def test_node_no_home_da_conta_e_recusado(tmp_path):
    bancada, _, _ = _aberta(tmp_path)
    no_home = tmp_path / "casa" / "node"
    no_home.write_text(NODE_FIXTURE)
    no_home.chmod(0o755)
    r = _repo(tmp_path, bancada, "lock", "demo", "front/prova", node=str(no_home))
    assert r.returncode == 3, r.stdout + r.stderr
    assert "home da conta" in r.stderr
