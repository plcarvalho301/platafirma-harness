"""Contrato de `repo lock --atualizar` (feature #3388): sobe um pacote só pelo lock, em node e em uv.

Git real contra bare local; node, npm e uv são scripts de fixture que registram a chamada e
escrevem o lock (e o package.json) pedidos. Prova: o argumento que chega ao npm e ao uv (direto
com versão troca o pino mantendo a seção e o pino exato; sem versão ou transitivo sobe dentro da
faixa, `npm update --no-save`; uv leva `--upgrade-package pacote[==versão]`); o relato
`atualizar: pacote antes -> depois`; versão pedida e não alcançada sai 1 e devolve lock e
package.json como estavam; pacote que não está no lock sai 1 sem chamar o resolvedor; nome
inválido (hífen na frente, espaço) sai 2 antes de qualquer chamada; --atualizar com --conferir sai
2; falha do npm depois de mexer no package.json o devolve. Não prova: o npm nem o uv de verdade.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
PY = os.path.realpath(sys.executable)

NODE_FIXTURE = "#!/bin/sh\necho v22.1.0\n"
NPM_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
printf '%s\\n' "$*" >> "$d/chamadas"
case "$1" in
  install|update)
    if [ -f "$d/falha_depois" ]; then
      [ -f "$d/novo.pkg" ] && cp "$d/novo.pkg" "$PWD/package.json"
      cat "$d/falha_depois" >&2; exit 1
    fi
    cp "$d/novo.lock" "$PWD/package-lock.json"
    [ -f "$d/novo.pkg" ] && cp "$d/novo.pkg" "$PWD/package.json"
    exit 0 ;;
esac
"""
UV_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
printf '%s\\n' "$*" >> "$d/chamadas"
proj=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) proj="$2"; shift 2 ;;
    *) shift ;;
  esac
done
cp "$d/novo.lock" "$proj/uv.lock"
"""


def _npm_lock(pacotes: dict) -> str:
    return json.dumps({"name": "p", "lockfileVersion": 3, "packages": {
        "": {"name": "p"},
        **{f"node_modules/{n}": {"version": v} for n, v in pacotes.items()}}}, indent=2) + "\n"


def _uv_lock(pacotes: dict) -> str:
    return "version = 1\n" + "".join(
        f'[[package]]\nname = "{n}"\nversion = "{v}"\n' for n, v in pacotes.items())


PKG_ANTES = json.dumps({"name": "p", "private": True,
                        "dependencies": {"a": "1.0.0"},
                        "devDependencies": {"d": "^1.0.0"}}, indent=2) + "\n"
NPM_ANTES = _npm_lock({"a": "1.0.0", "b": "1.0.0", "d": "1.0.0"})
UV_ANTES = _uv_lock({"a": "1.0", "foo-bar": "1.0"})


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}).stdout.strip()


def _montar(tmp_path, eco, com_lock=True):
    origem, semente, bancada = tmp_path / "origem.git", tmp_path / "semente", tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    proj = semente / "mod" / "x"
    proj.mkdir(parents=True)
    if eco == "npm":
        (proj / "package.json").write_text(PKG_ANTES)
        if com_lock:
            (proj / "package-lock.json").write_text(NPM_ANTES)
    else:
        (proj / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0"\n')
        if com_lock:
            (proj / "uv.lock").write_text(UV_ANTES)
    _git("add", "mod", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    fix = tmp_path / "fix"
    fix.mkdir()
    for nome, corpo in (("node", NODE_FIXTURE), ("npm", NPM_FIXTURE), ("uv", UV_FIXTURE)):
        f = fix / nome
        f.write_text(corpo)
        f.chmod(0o755)
    (fix / "novo.lock").write_text(NPM_ANTES if eco == "npm" else UV_ANTES)
    (tmp_path / "casa").mkdir()
    return bancada, fix


def _repo(tmp_path, bancada, *args):
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
        "PLATAFIRMA_NODE": str(tmp_path / "fix" / "node"),
        "PLATAFIRMA_UV": str(tmp_path / "fix" / "uv"),
        "PLATAFIRMA_PYTHON": PY,
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _aberta(tmp_path, eco, com_lock=True):
    bancada, fix = _montar(tmp_path, eco, com_lock)
    r = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "l")
    assert r.returncode == 0, r.stderr
    return bancada, fix, bancada / "wt" / "demo" / "ti" / "l" / "mod" / "x"


def _chamadas(fix):
    arq = fix / "chamadas"
    return arq.read_text() if arq.exists() else ""


# ---- node ----------------------------------------------------------------------------------

def test_node_direto_com_versao_troca_o_pino_exato_e_relata(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "npm")
    (fix / "novo.lock").write_text(_npm_lock({"a": "1.1.0", "b": "1.0.0", "d": "1.0.0"}))
    (fix / "novo.pkg").write_text(PKG_ANTES.replace('"1.0.0"', '"1.1.0"'))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a@1.1.0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "atualizar: a 1.0.0 -> 1.1.0" in r.stdout
    assert "package.json: ~ a 1.0.0 -> 1.1.0" in r.stdout
    assert "  ~ a 1.0.0 -> 1.1.0" in r.stdout
    assert "install a@1.1.0 --save-prod --save-exact --package-lock-only --ignore-scripts" in _chamadas(fix)
    assert "package.json" in r.stdout.split("próximo:")[1]


def test_node_dev_com_faixa_mantem_a_secao_e_nao_fixa_exato(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm")
    (fix / "novo.lock").write_text(_npm_lock({"a": "1.0.0", "b": "1.0.0", "d": "1.2.0"}))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "d@1.2.0")
    assert r.returncode == 0, r.stdout + r.stderr
    chamada = _chamadas(fix)
    assert "install d@1.2.0 --save-dev --package-lock-only" in chamada
    assert "--save-exact" not in chamada


def test_node_transitivo_sem_versao_sobe_dentro_da_faixa_sem_salvar(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "npm")
    (fix / "novo.lock").write_text(_npm_lock({"a": "1.0.0", "b": "1.0.1", "d": "1.0.0"}))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "b")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "atualizar: b 1.0.0 -> 1.0.1" in r.stdout
    assert "update b --no-save --package-lock-only --ignore-scripts" in _chamadas(fix)
    assert (wt / "package.json").read_text() == PKG_ANTES


def test_node_sem_mudanca_diz_que_segue_e_ja_em_dia(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "atualizar: a segue em 1.0.0" in r.stdout
    assert "já em dia" in r.stdout


def test_node_versao_pedida_e_nao_alcancada_sai_1_e_devolve_tudo(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "npm")
    (fix / "novo.lock").write_text(_npm_lock({"a": "1.0.0", "b": "1.0.1", "d": "1.0.0"}))
    (fix / "novo.pkg").write_text(PKG_ANTES.replace("^1.0.0", "^1.5.0"))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "b@2.0.0")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "atualizar: b pedido em 2.0.0 e o lock ficou em 1.0.1" in r.stdout
    assert "não chegou à versão pedida" in r.stderr
    assert (wt / "package-lock.json").read_text() == NPM_ANTES
    assert (wt / "package.json").read_text() == PKG_ANTES


def test_node_falha_do_npm_depois_de_mexer_no_package_json_o_devolve(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "npm")
    (fix / "novo.pkg").write_text(PKG_ANTES.replace('"1.0.0"', '"9.9.9"'))
    (fix / "falha_depois").write_text("npm ERR! code ECONNREFUSED\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a@9.9.9")
    assert r.returncode == 3, r.stdout + r.stderr
    assert (wt / "package.json").read_text() == PKG_ANTES
    assert (wt / "package-lock.json").read_text() == NPM_ANTES


def test_node_pacote_fora_do_lock_sai_1_sem_chamar_o_npm(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "zzz")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "zzz não está em" in r.stderr
    assert _chamadas(fix) == ""


def test_node_sem_lock_manda_gerar_antes(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm", com_lock=False)
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "Gere antes: repo lock demo mod/x" in r.stderr
    assert _chamadas(fix) == ""


# ---- uv ------------------------------------------------------------------------------------

def test_uv_sem_versao_leva_upgrade_package_e_relata(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "uv")
    (fix / "novo.lock").write_text(_uv_lock({"a": "1.1", "foo-bar": "1.0"}))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "atualizar: a 1.0 -> 1.1" in r.stdout
    assert "--upgrade-package a\n" in _chamadas(fix)
    assert "==" not in _chamadas(fix)


def test_uv_com_versao_aceita_arroba_e_igual_duplo(tmp_path):
    for forma in ("a@1.1", "a==1.1"):
        sub = tmp_path / forma.replace("@", "_").replace("=", "")
        sub.mkdir()
        bancada, fix, _ = _aberta(sub, "uv")
        (fix / "novo.lock").write_text(_uv_lock({"a": "1.1", "foo-bar": "1.0"}))
        r = _repo(sub, bancada, "lock", "demo", "mod/x", "--atualizar", forma)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "--upgrade-package a==1.1" in _chamadas(fix)


def test_uv_versao_pedida_e_nao_alcancada_sai_1_e_devolve_o_lock(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "uv")
    (fix / "novo.lock").write_text(_uv_lock({"a": "1.1", "foo-bar": "1.0"}))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a==9.9")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "atualizar: a pedido em 9.9 e o lock ficou em 1.1" in r.stdout
    assert (wt / "uv.lock").read_text() == UV_ANTES


def test_uv_nome_normalizado_acha_o_pacote(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "uv")
    (fix / "novo.lock").write_text(_uv_lock({"a": "1.0", "foo-bar": "1.1"}))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "Foo_Bar")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "atualizar: Foo_Bar 1.0 -> 1.1" in r.stdout


def test_uv_pacote_fora_do_lock_sai_1_sem_chamar_o_uv(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "uv")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "zzz")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "zzz não está em" in r.stderr
    assert _chamadas(fix) == ""


# ---- uso -----------------------------------------------------------------------------------

def test_nome_invalido_sai_2_antes_de_qualquer_chamada(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm")
    for ruim in ("--evil", "-x", "a b", "a@", "a==", "../a"):
        r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", ruim)
        assert r.returncode == 2, (ruim, r.stdout + r.stderr)
    assert _chamadas(fix) == ""


def test_atualizar_sem_pacote_e_uso(tmp_path):
    bancada, _, _ = _aberta(tmp_path, "npm")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar")
    assert r.returncode == 2, r.stdout + r.stderr


def test_atualizar_com_conferir_nao_se_combinam(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--conferir", "--atualizar", "a")
    assert r.returncode == 2, r.stdout + r.stderr
    assert _chamadas(fix) == ""


def test_nao_commita(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "uv")
    (fix / "novo.lock").write_text(_uv_lock({"a": "1.1", "foo-bar": "1.0"}))
    antes = _git("rev-parse", "HEAD", cwd=wt)
    _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar", "a")
    assert _git("rev-parse", "HEAD", cwd=wt) == antes
    assert "uv.lock" in _git("status", "--porcelain", cwd=wt)


# ---- --atualizar-tudo ----------------------------------------------------------------------

def test_uv_tudo_leva_upgrade_sem_pacote_e_relata_todos(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "uv")
    (fix / "novo.lock").write_text(_uv_lock({"a": "1.1", "foo-bar": "2.0"}))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar-tudo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--upgrade\n" in _chamadas(fix)
    assert "--upgrade-package" not in _chamadas(fix)
    assert "  ~ a 1.0 -> 1.1" in r.stdout
    assert "  ~ foo-bar 1.0 -> 2.0" in r.stdout


def test_node_tudo_roda_update_do_lock_e_relata_o_package_json(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "npm")
    (fix / "novo.lock").write_text(_npm_lock({"a": "1.0.0", "b": "1.0.1", "d": "1.4.0"}))
    (fix / "novo.pkg").write_text(PKG_ANTES.replace("^1.0.0", "^1.4.0"))
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar-tudo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "update --package-lock-only --ignore-scripts" in _chamadas(fix)
    assert "install" not in _chamadas(fix)
    assert "  ~ b 1.0.0 -> 1.0.1" in r.stdout
    assert "  ~ d 1.0.0 -> 1.4.0" in r.stdout
    assert "package.json: ~ d ^1.0.0 -> ^1.4.0" in r.stdout


def test_node_tudo_falha_do_npm_devolve_lock_e_package_json(tmp_path):
    bancada, fix, wt = _aberta(tmp_path, "npm")
    (fix / "novo.pkg").write_text(PKG_ANTES.replace("^1.0.0", "^9.0.0"))
    (fix / "falha_depois").write_text("npm ERR! code ECONNREFUSED\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar-tudo")
    assert r.returncode == 3, r.stdout + r.stderr
    assert (wt / "package.json").read_text() == PKG_ANTES
    assert (wt / "package-lock.json").read_text() == NPM_ANTES


def test_tudo_nao_se_combina_com_conferir_nem_com_atualizar(tmp_path):
    bancada, fix, _ = _aberta(tmp_path, "npm")
    for extra in (["--conferir"], ["--atualizar", "a"]):
        r = _repo(tmp_path, bancada, "lock", "demo", "mod/x", "--atualizar-tudo", *extra)
        assert r.returncode == 2, (extra, r.stdout + r.stderr)
    assert _chamadas(fix) == ""
