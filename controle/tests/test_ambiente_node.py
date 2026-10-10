"""Ambiente node da casa (card #3386): lock no git, instalacao sem script de pacote, chave por
hash, o mesmo construtor para `release promover` e `teste rodar`, e o inventario das travas.

Hermetico: node, npm e chromium sao falsos (scripts no tmp_path) e o registro, a bancada e a
raiz de release moram no tmp_path. Nada toca rede nem o npm real; o que se prova e o COMANDO que
o construtor monta (npm ci --ignore-scripts, sem config de usuario) e o que a suite faz com ele.
Precisa so do uv no host, que o ambiente_do_registro exige para toda stack, como nas outras suites.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTE = REPO_ROOT / "bin" / "teste"
VENV_SH = REPO_ROOT / "lib" / "venv.sh"
CONFERIR_DIR = REPO_ROOT / "bin" / "_release" / "conferir"

LOCK_V3 = {
    "name": "prova",
    "lockfileVersion": 3,
    "requires": True,
    "packages": {
        "": {"name": "prova", "dependencies": {"lit": "3.3.3"}, "devDependencies": {"puppeteer-core": "25.7.0"}},
        "node_modules/lit": {
            "version": "3.3.3", "resolved": "https://registry.npmjs.org/lit/-/lit-3.3.3.tgz",
            "integrity": "sha512-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "license": "BSD-3-Clause"},
        "node_modules/puppeteer-core": {
            "version": "25.7.0", "dev": True,
            "resolved": "https://registry.npmjs.org/puppeteer-core/-/puppeteer-core-25.7.0.tgz",
            "integrity": "sha512-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "hasInstallScript": True},
        "node_modules/de-git": {
            "version": "1.0.0", "resolved": "git+ssh://git@github.com/x/de-git.git#abc",
            "integrity": "sha512-CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"},
        "node_modules/sem-integridade": {
            "version": "2.0.0", "resolved": "https://registry.npmjs.org/s/-/s-2.0.0.tgz"},
    },
}

UV_LOCK = """version = 1
requires-python = ">=3.12"

[[package]]
name = "django"
version = "5.2.7"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/x.tar.gz", hash = "sha256:aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbb" }

[[package]]
name = "estranho"
version = "0.1.0"
source = { git = "https://github.com/x/estranho" }

[[package]]
name = "prova"
version = "0.0.0"
source = { virtual = "." }
dependencies = [{ name = "django" }]
"""


def _exec(caminho: Path, corpo: str) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def _python_de_sistema() -> str:
    casa = str(Path.home())
    for c in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if c and os.path.isabs(c) and os.access(c, os.X_OK) and not c.startswith(casa):
            return c
    pytest.skip("nenhum python de sistema fora do HOME")


@pytest.fixture()
def falsos(tmp_path):
    """node, npm e chromium falsos, e um HOME proprio (o node do tmp nao pode estar sob ele)."""
    d = tmp_path / "falsos"
    node = _exec(d / "node", 'if [ "${1:-}" = "--version" ]; then echo "${FALSO_NODE_VERSAO:-v22.1.0}"; exit 0; fi\n'
                 'if [ -n "${FALSO_ENV_OUT:-}" ]; then printf "%s\\n" "CHROME=${CHROME:-}" "PUP=${PUPPETEER_EXECUTABLE_PATH:-}" '
                 '"NM=$(readlink -f node_modules 2>/dev/null)" "ARQ=$1" >> "$FALSO_ENV_OUT"; fi\n'
                 'if grep -q VERMELHO "$1" 2>/dev/null; then echo "prova reprovou" >&2; exit 1; fi\n'
                 'echo ok; exit 0\n')
    npm = _exec(d / "npm", 'if [ "${1:-}" = "--version" ]; then echo 10.9.0; exit 0; fi\n'
                'printf "%s\\n" "$*" > "${FALSO_NPM_ARGS:-/dev/null}"\n'
                # o npm real recusa o mesmo caminho nas duas configs ("double-loading config"): o falso tambem
                'if [ "${npm_config_userconfig:-}" = "${npm_config_globalconfig:-}" ]; then '
                'echo "double-loading config as global, previously loaded as user" >&2; exit 1; fi\n'
                'printf "ignore_scripts=%s userempty=%s globalempty=%s\\n" "${npm_config_ignore_scripts:-}" '
                '"$([ -f "${npm_config_userconfig:-}" ] && [ ! -s "$npm_config_userconfig" ] && echo sim || echo nao)" '
                '"$([ -f "${npm_config_globalconfig:-}" ] && [ ! -s "$npm_config_globalconfig" ] && echo sim || echo nao)" '
                '>> "${FALSO_NPM_ARGS:-/dev/null}"\n'
                'if [ "${FALSO_NPM_FALHA:-0}" = 1 ]; then echo "npm ERR! lock fora de sincronia" >&2; exit 1; fi\n'
                'mkdir -p node_modules/lit && echo "{}" > node_modules/lit/package.json\n')
    chromium = _exec(d / "chromium", 'echo chromium falso\n')
    casa = tmp_path / "home"
    casa.mkdir()
    return {"node": node, "npm": npm, "chromium": chromium, "home": casa, "dir": d}


def _bash(falsos, tmp_path, script: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update({"HOME": str(falsos["home"]), "PLATAFIRMA_NODE": str(falsos["node"]),
                "FALSO_NPM_ARGS": str(tmp_path / "npm-args.txt"), "TMPDIR": str(tmp_path)})
    env.update(extra_env or {})
    return subprocess.run(["bash", "-c", f'. "{VENV_SH}"; {script}'], env=env,
                          capture_output=True, text=True, timeout=60)


def _projeto_node(raiz: Path) -> Path:
    p = raiz / "front"
    p.mkdir(parents=True, exist_ok=True)
    (p / "package.json").write_text(json.dumps({"name": "prova", "private": True}), encoding="utf-8")
    (p / "package-lock.json").write_text(json.dumps(LOCK_V3), encoding="utf-8")
    return p / "package-lock.json"


# --- a chave do ambiente -----------------------------------------------------------------

def test_hash_de_lock_python_e_a_formula_de_sempre(falsos, tmp_path):
    """Os venvs ja construidos nao mudam de chave: a formula antiga, byte a byte."""
    lock = tmp_path / "uv.lock"
    lock.write_text("version = 1\n", encoding="utf-8")
    r = _bash(falsos, tmp_path, f'hash_do_ambiente "{lock}" /usr/bin/python3.12 3.12')
    antigo = subprocess.run(
        ["bash", "-c", f'{{ cat "{lock}"; printf \'\\npython=%s %s\\n\' /usr/bin/python3.12 3.12; }} | sha256sum | cut -c1-12'],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == antigo.stdout.strip()


def test_hash_de_lock_node_soma_a_versao_do_node(falsos, tmp_path):
    lock = _projeto_node(tmp_path)
    h1 = _bash(falsos, tmp_path, f'hash_do_ambiente "{lock}" /usr/bin/python3.12 3.12',
               {"FALSO_NODE_VERSAO": "v22.1.0"}).stdout.strip()
    h2 = _bash(falsos, tmp_path, f'hash_do_ambiente "{lock}" /usr/bin/python3.12 3.12',
               {"FALSO_NODE_VERSAO": "v24.0.0"}).stdout.strip()
    assert len(h1) == 12 and len(h2) == 12
    assert h1 != h2


def test_node_no_home_e_recusado(falsos, tmp_path):
    no_home = _exec(falsos["home"] / ".nvm" / "node", 'echo v22.1.0\n')
    r = _bash(falsos, tmp_path, "resolver_node", {"PLATAFIRMA_NODE": str(no_home)})
    assert r.returncode == 3
    assert "home da conta" in r.stderr


def test_node_ausente_diz_como_resolver(falsos, tmp_path):
    r = _bash(falsos, tmp_path, "resolver_node", {"PLATAFIRMA_NODE": str(tmp_path / "nao-existe")})
    assert r.returncode == 3
    assert "PLATAFIRMA_NODE" in r.stderr


# --- o construtor ------------------------------------------------------------------------

def test_construir_node_instala_sem_script_de_pacote(falsos, tmp_path):
    lock = _projeto_node(tmp_path)
    dest = tmp_path / "venv" / "prova-abc"
    r = _bash(falsos, tmp_path, f'construir_venv "{lock}" "{dest}" /nao/usa/uv /usr/bin/python3.12 3.12')
    assert r.returncode == 0, r.stdout + r.stderr
    args = (tmp_path / "npm-args.txt").read_text(encoding="utf-8")
    assert "ci" in args.split("\n")[0].split()
    assert "--ignore-scripts" in args
    assert "ignore_scripts=true" in args          # nem por config de ambiente o script roda
    assert "userempty=sim globalempty=sim" in args  # .npmrc do usuario e global nao entram: dois arquivos vazios e distintos
    assert (dest / "node_modules" / "lit").is_dir()
    assert (dest / "package-lock.json").read_bytes() == lock.read_bytes()


def test_construir_node_falha_alto_quando_o_npm_recusa(falsos, tmp_path):
    lock = _projeto_node(tmp_path)
    dest = tmp_path / "venv" / "prova-abc"
    r = _bash(falsos, tmp_path, f'construir_venv "{lock}" "{dest}" /x /usr/bin/python3.12 3.12',
              {"FALSO_NPM_FALHA": "1"})
    assert r.returncode == 3
    assert "npm ci --ignore-scripts saiu" in r.stderr


def test_construir_node_sem_package_json_ao_lado(falsos, tmp_path):
    lock = _projeto_node(tmp_path)
    (lock.parent / "package.json").unlink()
    r = _bash(falsos, tmp_path, f'construir_venv "{lock}" "{tmp_path}/d" /x /usr/bin/python3.12 3.12')
    assert r.returncode == 3
    assert "package.json" in r.stderr


# --- teste rodar numa stack node ---------------------------------------------------------

class Bancada:
    def __init__(self, tmp_path: Path, falsos: dict):
        self.tmp = tmp_path
        bancada = tmp_path / "bancada"
        self.clone = bancada / "wt" / "alvo" / "cadeira"
        self.clone.mkdir(parents=True)
        (self.clone / ".git").mkdir()
        _projeto_node(self.clone)
        provas = self.clone / "front" / "provas"
        provas.mkdir()
        (provas / "verde.mjs").write_text("// passa\n", encoding="utf-8")
        (provas / "vermelha.mjs").write_text("// VERMELHO\n", encoding="utf-8")
        registro = {
            "prova": {"familia": "alvo", "lock": "front/package-lock.json", "testes": ["front/provas/verde.mjs"]},
            "prova-vermelha": {"familia": "alvo", "lock": "front/package-lock.json",
                                "testes": ["front/provas/vermelha.mjs"]},
            "prova-sem-suite": {"familia": "alvo", "lock": "front/package-lock.json"},
        }
        venvs = tmp_path / "venvs.json"
        venvs.write_text(json.dumps(registro), encoding="utf-8")
        self.env = dict(os.environ)
        self.env.update({
            "PLATAFIRMA_BANCADA": str(bancada), "PLATAFIRMA_VENVS": str(venvs),
            "PF_RELEASE_RAIZ": str(tmp_path / "opt"), "PLATAFIRMA_PYTHON": _python_de_sistema(),
            "PF_CADEIRA": "cadeira", "HOME": str(falsos["home"]),
            "PLATAFIRMA_NODE": str(falsos["node"]), "PLATAFIRMA_CHROMIUM": str(falsos["chromium"]),
            "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"), "TMPDIR": str(tmp_path),
            "FALSO_NPM_ARGS": str(tmp_path / "npm-args.txt"), "FALSO_ENV_OUT": str(tmp_path / "env-out.txt"),
        })
        self.env.pop("PF_SESSAO", None)

    def rodar(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(TESTE), "rodar", *args], env=self.env, capture_output=True,
                              text=True, timeout=120)


@pytest.fixture()
def banc(tmp_path, falsos):
    if shutil.which("uv") is None and not Path("/usr/local/bin/uv").exists():
        pytest.skip("uv ausente: ambiente_do_registro o exige para toda stack")
    return Bancada(tmp_path, falsos)


def test_rodar_stack_node_verde_com_chromium_do_host(banc):
    r = banc.rodar("prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "suite VERDE" in r.stdout
    saida = (banc.tmp / "env-out.txt").read_text(encoding="utf-8")
    assert f"CHROME={banc.env['PLATAFIRMA_CHROMIUM']}" in saida
    assert f"PUP={banc.env['PLATAFIRMA_CHROMIUM']}" in saida
    assert "NM=" in saida and "/venv/prova-" in saida   # node_modules e o do ambiente travado


def test_rodar_stack_node_deixa_a_arvore_limpa(banc):
    banc.rodar("prova")
    assert not (banc.clone / "front" / "node_modules").exists()
    assert not (banc.clone / "node_modules").exists()


def test_rodar_stack_node_vermelha_sai_1(banc):
    r = banc.rodar("prova-vermelha")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "suite VERMELHA" in r.stdout
    assert "vermelha.mjs" in r.stdout


def test_rodar_stack_node_reaproveita_o_ambiente(banc):
    banc.rodar("prova")
    r = banc.rodar("prova")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "reaproveitado" in r.stderr


def test_rodar_stack_node_recusa_node_modules_instalado_a_mao(banc):
    (banc.clone / "node_modules").mkdir()
    r = banc.rodar("prova")
    assert r.returncode == 5, r.stdout + r.stderr
    assert "instalado à mão" in r.stderr
    assert (banc.clone / "node_modules").is_dir()        # recusa, nao apaga


def test_rodar_stack_node_sem_suite_sai_5(banc):
    r = banc.rodar("prova-sem-suite")
    assert r.returncode == 5, r.stdout + r.stderr


def test_rodar_stack_node_sem_portao_ainda(banc):
    r = banc.rodar("prova", "--portao")
    assert r.returncode == 5, r.stdout + r.stderr
    assert "ainda sem portão" in r.stderr


# --- o inventario das travas -------------------------------------------------------------

def _arvore_servida(tmp_path: Path) -> tuple[Path, Path]:
    raiz = tmp_path / "opt"
    sha = "a" * 40
    arvore = raiz / "fam" / sha
    arvore.mkdir(parents=True)
    (raiz / "fam" / "current").symlink_to(arvore)
    _projeto_node(arvore)
    (arvore / "py").mkdir()
    (arvore / "py" / "uv.lock").write_text(UV_LOCK, encoding="utf-8")
    (arvore / "py" / "requirements.txt").write_text("starlette==0.47.0\nsolto>=1.0\n# comentario\n", encoding="utf-8")
    registro = tmp_path / "venvs.json"
    registro.write_text(json.dumps({
        "front": {"familia": "fam", "lock": "front/package-lock.json"},
        "py": {"familia": "fam", "lock": "py/uv.lock"},
        "req": {"familia": "fam", "lock": "py/requirements.txt"},
        "fantasma": {"familia": "fam", "lock": "nao/existe.lock"},
    }), encoding="utf-8")
    return raiz, registro


def _dependencias():
    sys.path.insert(0, str(CONFERIR_DIR))
    import importlib
    import dependencias
    return importlib.reload(dependencias)


def test_inventario_le_as_tres_formas_de_lock(tmp_path):
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    itens, linhas = dep.levantar(None, str(registro), str(raiz))
    por = {(l["stack"], l["pacote"]): l for l in linhas}

    lit = por[("front", "lit")]
    assert lit["direto"] and lit["ecossistema"] == "npm" and lit["licenca"] == "BSD-3-Clause"
    assert not lit["problema"] and lit["integridade"]
    pup = por[("front", "puppeteer-core")]
    assert pup["script_de_instalacao"] is True            # declara; a casa nunca o roda
    assert por[("front", "de-git")]["problema"].startswith("fonte fora do registro oficial")
    assert "integridade" in por[("front", "sem-integridade")]["problema"]

    assert por[("py", "django")]["direto"] is True
    assert por[("py", "django")]["fonte"] == "pypi.org"
    assert "fora do PyPI" in por[("py", "estranho")]["problema"]
    assert ("py", "prova") not in por                      # o proprio projeto nao e dependencia

    assert not por[("req", "starlette")]["problema"]
    assert "nao fixada" in por[("req", "solto")]["problema"]


def test_inventario_lista_o_ferramental_do_host(falsos, monkeypatch):
    """node, npm e chromium vem das MESMAS funcoes de lib/venv.sh que constroem o ambiente; o
    node no home da conta sai com o motivo no lugar da versao."""
    dep = _dependencias()
    monkeypatch.setenv("HOME", str(falsos["home"]))
    monkeypatch.setenv("PLATAFIRMA_NODE", str(falsos["node"]))
    monkeypatch.setenv("PLATAFIRMA_CHROMIUM", str(falsos["chromium"]))
    por = {f["ferramenta"]: f for f in dep.ferramental(str(REPO_ROOT))}
    assert por["node"]["caminho"] == str(falsos["node"]) and por["node"]["versao"] == "v22.1.0"
    assert por["npm"]["caminho"] == str(falsos["npm"]) and por["npm"]["versao"] == "10.9.0"
    assert por["chromium"]["caminho"] == str(falsos["chromium"])

    no_home = _exec(falsos["home"] / ".nvm" / "node", "echo v22.1.0\n")
    monkeypatch.setenv("PLATAFIRMA_NODE", str(no_home))
    recusado = {f["ferramenta"]: f for f in dep.ferramental(str(REPO_ROOT))}["node"]
    assert recusado["caminho"] == "-" and "home da conta" in recusado["versao"]


def test_requirements_nome_que_comeca_com_http_nao_e_url(tmp_path):
    """Medido no host em 10/10: `httpx>=0.27` saiu como fonte fora do PyPI por comecar com "http"."""
    dep = _dependencias()
    req = tmp_path / "r.txt"
    req.write_text("httpx>=0.27\nhttpx==0.28.1\nhttps://x.org/p.tar.gz\ngit+https://g.com/p.git\n", encoding="utf-8")
    por = {(p["pacote"], p["versao"]): p for p in dep.ler_requirements("s", str(req))}
    assert "nao fixada" in por[("httpx", "0.27")]["problema"]
    assert not por[("httpx", "0.28.1")]["problema"]
    urls = [p for p in por.values() if "url ou git" in p["problema"]]
    assert len(urls) == 2


def test_inventario_stack_ausente_na_release_e_indeterminavel(tmp_path):
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    itens, _ = dep.levantar("fantasma", str(registro), str(raiz))
    assert len(itens) == 1
    nome, v = itens[0]
    assert v.estado == "indeterminavel"
    assert "ausente na release servida" in v.motivo


def test_inventario_exit_agrega_o_pior_caso(tmp_path, capsys):
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    rc = dep.conferir("front", True, "abc1234", str(registro), str(raiz))
    saida = json.loads(capsys.readouterr().out)
    assert rc == 1                                         # de-git e sem-integridade divergem
    assert saida["classe"] == "dependencias"
    assert {p["pacote"] for p in saida["pacotes"]} == {"lit", "puppeteer-core", "de-git", "sem-integridade"}
    estados = {i["nome"]: i["estado"] for i in saida["itens"]}
    assert estados["front · npm · lit 3.3.3"] == "conforme"


def test_inventario_so_conforme_sai_0(tmp_path, capsys):
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    lock = json.loads((raiz / "fam" / "current" / "front" / "package-lock.json").read_text(encoding="utf-8"))
    for k in ("node_modules/de-git", "node_modules/sem-integridade"):
        lock["packages"].pop(k)
    (raiz / "fam" / "current" / "front" / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    assert dep.conferir("front", False, "abc1234", str(registro), str(raiz)) == 0
    assert "2 conforme · 0 divergente" in capsys.readouterr().out


def test_inventario_acha_trava_que_a_release_nao_constroi(tmp_path):
    """O inventario e o que ha na maquina, nao so o que o registro declara: lock fora do registro
    entra com o rotulo <familia>:<pasta> e marcado como nao construido; node_modules nao entra."""
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    arvore = raiz / "fam" / ("a" * 40)
    extra = arvore / "ui" / "provas"
    extra.mkdir(parents=True)
    (extra / "package-lock.json").write_text(json.dumps(LOCK_V3), encoding="utf-8")
    de_pacote = arvore / "node_modules" / "x"
    de_pacote.mkdir(parents=True)
    (de_pacote / "package-lock.json").write_text(json.dumps(LOCK_V3), encoding="utf-8")
    _, linhas = dep.levantar(None, str(registro), str(raiz))
    rotulos = {l["stack"] for l in linhas}
    assert "fam:ui/provas" in rotulos
    assert not any("node_modules" in r for r in rotulos)
    assert "fam:front" not in rotulos                      # declarada: ja entra como stack
    assert all(l.get("construido_pela_release") is False for l in linhas if l["stack"] == "fam:ui/provas")
    _, so_ela = dep.levantar("fam:ui/provas", str(registro), str(raiz))
    assert {l["stack"] for l in so_ela} == {"fam:ui/provas"}


def test_inventario_escreve_markdown_so_sob_a_bancada(tmp_path):
    """O retrato para o dono ler: Markdown datado, derivado das travas. E a unica escrita da
    classe, opt-in e contida: .md absoluto sob a bancada; fora dela, recusa e nada e escrito."""
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    bancada = tmp_path / "bancada"
    bancada.mkdir()
    destino = bancada / "casa" / "relatorio" / "x.md"
    rc = dep.conferir("front", False, "abc1234", str(registro), str(raiz),
                      md_para=str(destino), raiz_permitida=str(bancada))
    assert rc == 1                                          # o relatorio segue valendo: ha divergente
    texto = destino.read_text(encoding="utf-8")
    assert texto.startswith("# Dependências das travas da casa em ")
    assert "Espécie: relatorio" in texto
    assert "| lit | 3.3.3 | direto |" in texto
    assert "BSD-3-Clause" in texto
    assert "fonte fora do registro oficial do npm" in texto   # a seção "o que a trava não prende"
    assert "declara" in texto                                 # puppeteer-core declara script de instalação

    for ruim in (tmp_path / "fora" / "x.md", bancada / "x.txt"):
        rc = dep.conferir("front", False, "abc1234", str(registro), str(raiz),
                          md_para=str(ruim), raiz_permitida=str(bancada))
        assert rc == 4
        assert not ruim.exists()


def test_inventario_pela_linha_de_comando_com_md_para(tmp_path):
    raiz, registro = _arvore_servida(tmp_path)
    bancada = tmp_path / "bancada"
    bancada.mkdir()
    destino = bancada / "rel.md"
    env = dict(os.environ, PF_AI_DIR=str(bancada), PLATAFIRMA_VENVS=str(registro),
               PF_RELEASE_RAIZ=str(raiz), PF_HARNESS_DIR=str(tmp_path / "sem-git"))
    r = subprocess.run([sys.executable, str(CONFERIR_DIR / "conferir.py"), "dependencias", "front",
                        "--md-para", str(destino)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 1, r.stdout + r.stderr          # divergentes: de-git e sem-integridade
    assert "release conferir dependencias front: 2 conforme · 2 divergente" in r.stdout
    assert destino.exists()
    sem_alvo = subprocess.run([sys.executable, str(CONFERIR_DIR / "conferir.py"), "dependencias",
                               "--md-para", str(bancada / "todas.md")], env=env,
                              capture_output=True, text=True, timeout=60)
    assert (bancada / "todas.md").exists(), sem_alvo.stdout + sem_alvo.stderr


def test_inventario_stack_desconhecida_sai_1(tmp_path, capsys):
    dep = _dependencias()
    raiz, registro = _arvore_servida(tmp_path)
    assert dep.conferir("nao-existe", False, "abc1234", str(registro), str(raiz)) == 1
