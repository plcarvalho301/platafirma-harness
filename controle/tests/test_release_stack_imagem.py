"""Contrato de bin/_release/stack no que o card #3192 acrescentou (spec
conversor-pdf-combinado §2 e §13; guia portoes-do-codigo, gate de promoção):

- imagem pinada pelo sha: stack cujo compose dá a todo serviço com build uma image
  terminada em :${PF_RELEASE_SHA} sobe SEM --build quando a imagem daquele sha já
  existe (volta sem rebuild), e constrói só a que falta;
- stack sem esse pino sobe como sempre (up --build);
- recria só a stack cujo artefato mudou: entre o sha que a stack tem no ar e o que sobe,
  nada mudou nos compose, contextos de build e binds, e os contêineres estão de pé ->
  nada se recria e o ponto avança;
- `stack testar`: sem serviço no perfil `teste`, nada a medir (0, sem build); com ele,
  constrói e roda; reprovado sai 4.

Roda o ajudante real desta árvore, com a release, a topologia e o docker falsos
(DEPLOY_TOPO_ARQUIVO, PF_RELEASE_RAIZ, stub de docker no PATH). O stub responde o
`docker compose config --format json` a partir de um modelo com ${ARVORE} e
${PF_RELEASE_SHA}, e registra cada chamada num log que o teste lê.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
STACK = REPO_RAIZ / "bin" / "_release" / "stack"
BASH = shutil.which("bash")
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    BASH is None or GIT is None or shutil.which("jq") is None,
    reason="precisa de bash, git e jq",
)

FAMILIA = "platafirma-x"

DOCKER_STUB = r'''#!/usr/bin/env python3
import json, os, sys
log = open(os.environ["STUB_LOG"], "a")
args = sys.argv[1:]
log.write(" ".join(args) + "\n"); log.close()
if args[:2] == ["image", "inspect"]:
    imgs = open(os.environ["STUB_IMAGENS"]).read().split()
    sys.exit(0 if args[2] in imgs else 1)
if args[:1] != ["compose"]:
    sys.exit(0)
perfis, sub, i, arquivos = [], None, 1, []
while i < len(args):
    a = args[i]
    if a in ("-p", "-f", "--env-file", "--profile"):
        if a == "--profile":
            perfis.append(args[i + 1])
        if a == "-f":
            arquivos.append(args[i + 1])
        i += 2
        continue
    sub = a
    break
resto = args[i + 1:] if sub else []
if sub == "config":
    arvore = arquivos[0].split("/deploy/")[0]
    modelo = json.load(open(os.environ["STUB_MODELO"]))
    texto = json.dumps(modelo).replace("${ARVORE}", arvore).replace(
        "${PF_RELEASE_SHA}", os.environ.get("PF_RELEASE_SHA", "local"))
    d = json.loads(texto)
    d["services"] = {n: s for n, s in d["services"].items()
                     if not s.get("profiles") or set(s["profiles"]) & set(perfis)}
    print(json.dumps(d))
    sys.exit(0)
if sub == "ps":
    if os.environ.get("STUB_RODANDO") == "1":
        print("abc123")
    sys.exit(0)
if sub == "run":
    sys.exit(int(os.environ.get("STUB_TESTE_RC", "0")))
sys.exit(0)
'''

MODELO_PINADO = {
    "services": {
        "app": {"build": {"context": "${ARVORE}/app", "dockerfile": "Dockerfile"},
                "image": "x/app:${PF_RELEASE_SHA}"},
    }
}
MODELO_TESTE = {
    "services": {
        "app": {"build": {"context": "${ARVORE}/app", "dockerfile": "Dockerfile"},
                "image": "x/app:${PF_RELEASE_SHA}"},
        "app-teste": {"build": {"context": "${ARVORE}/app", "dockerfile": "Dockerfile", "target": "teste"},
                      "image": "x/app-teste:${PF_RELEASE_SHA}", "profiles": ["teste"],
                      "volumes": [{"type": "bind", "source": "${ARVORE}/app/tests", "target": "/t"}]},
    }
}
MODELO_LEGADO = {
    "services": {
        "app": {"build": {"context": "${ARVORE}/app", "dockerfile": "Dockerfile"}, "image": "x/app"},
    }
}


def _git(cwd, *args):
    return subprocess.run([GIT, *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}).stdout.strip()


@pytest.fixture
def mundo(tmp_path):
    """Família com três revs: c1 (base), c2 (só README muda), c3 (app/ muda); espelho bare
    e cada rev materializada em <raiz>/<familia>/<sha>, como o release deixa."""
    fonte = tmp_path / "fonte"
    (fonte / "deploy" / "x").mkdir(parents=True)
    (fonte / "app" / "tests").mkdir(parents=True)
    (fonte / "deploy" / "x" / "compose.yaml").write_text("name: x\nservices: {}\n")
    (fonte / "app" / "Dockerfile").write_text("FROM scratch\n")
    (fonte / "app" / "tests" / "t.py").write_text("x = 1\n")
    (fonte / "README.md").write_text("um\n")
    _git(fonte, "init", "-q", "-b", "main")
    _git(fonte, "add", "-A"); _git(fonte, "commit", "-qm", "c1")
    c1 = _git(fonte, "rev-parse", "HEAD")
    (fonte / "README.md").write_text("dois\n")
    _git(fonte, "commit", "-qam", "c2")
    c2 = _git(fonte, "rev-parse", "HEAD")
    (fonte / "app" / "Dockerfile").write_text("FROM scratch\nLABEL v=3\n")
    _git(fonte, "commit", "-qam", "c3")
    c3 = _git(fonte, "rev-parse", "HEAD")

    raiz = tmp_path / "opt"
    fam = raiz / FAMILIA
    fam.mkdir(parents=True)
    _git(tmp_path, "clone", "-q", "--bare", str(fonte), str(fam / ".repo.git"))
    for sha in (c1, c2, c3):
        _git(fam / ".repo.git", "worktree", "add", "-q", "--detach", str(fam / sha), sha)

    topo = tmp_path / "topo.json"
    topo.write_text(json.dumps({"stacks": {"x": {
        "slug": "x", "repo": FAMILIA, "projeto": "x", "compose": "deploy/x/compose.yaml",
        "reversao": {"via": "promover"}}}}))

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    d = stubs / "docker"
    d.write_text(DOCKER_STUB)
    d.chmod(d.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    pontos = tmp_path / "pontos"
    log = tmp_path / "docker.log"
    imagens = tmp_path / "imagens.txt"
    imagens.write_text("")
    modelo = tmp_path / "modelo.json"
    modelo.write_text(json.dumps(MODELO_PINADO))
    env = {
        **os.environ,
        "PATH": f"{stubs}{os.pathsep}{os.environ.get('PATH', '')}",
        "PF_RELEASE_RAIZ": str(raiz),
        "PLATAFIRMA_RELEASE": str(raiz / "current"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "srv"),
        "DEPLOY_PONTOS": str(pontos),
        "DEPLOY_ENV_DIR": str(tmp_path / "env"),
        "DEPLOY_TOPO_ARQUIVO": str(topo),
        "STUB_LOG": str(log),
        "STUB_IMAGENS": str(imagens),
        "STUB_MODELO": str(modelo),
        "STUB_RODANDO": "1",
    }
    env.pop("PF_STACK_RECRIAR", None)
    return {"c1": c1, "c2": c2, "c3": c3, "env": env, "log": log, "imagens": imagens,
            "modelo": modelo, "pontos": pontos}


def _roda(m, *args, **extra):
    env = {**m["env"], **extra}
    return subprocess.run([BASH, str(STACK), *args], capture_output=True, text=True,
                          env=env, timeout=60, check=False)


def _chamadas(m, sub):
    if not m["log"].exists():
        return []
    return [l for l in m["log"].read_text().splitlines() if f" {sub}" in f" {l}" and l.startswith("compose")
            and sub in l.split()]


def _limpa_log(m):
    if m["log"].exists():
        m["log"].unlink()


def test_pinada_com_imagem_do_sha_sobe_sem_build(mundo):
    mundo["imagens"].write_text(f"x/app:{mundo['c1']}\n")
    r = _roda(mundo, "promover", "x", mundo["c1"])
    assert r.returncode == 0, r.stderr
    ups = _chamadas(mundo, "up")
    assert ups and "--no-build" in ups[-1] and "--build" not in ups[-1].split()
    assert not _chamadas(mundo, "build")
    assert "ja existe" in r.stdout
    assert (mundo["pontos"] / "x.atual").read_text().strip() == mundo["c1"]


def test_pinada_sem_imagem_constroi_so_ela_e_sobe_sem_build(mundo):
    r = _roda(mundo, "promover", "x", mundo["c1"])
    assert r.returncode == 0, r.stderr
    builds = _chamadas(mundo, "build")
    assert builds and builds[-1].endswith("build app")
    assert "--no-build" in _chamadas(mundo, "up")[-1]


def test_legada_sobe_com_build_como_sempre(mundo):
    mundo["modelo"].write_text(json.dumps(MODELO_LEGADO))
    r = _roda(mundo, "promover", "x", mundo["c1"])
    assert r.returncode == 0, r.stderr
    up = _chamadas(mundo, "up")[-1].split()
    assert "--build" in up and "--force-recreate" in up


def test_inalterada_nao_recria_e_avanca_o_ponto(mundo):
    mundo["pontos"].mkdir()
    (mundo["pontos"] / "x.atual").write_text(mundo["c1"] + "\n")
    r = _roda(mundo, "promover", "x", mundo["c2"])
    assert r.returncode == 0, r.stderr
    assert "inalterada" in r.stdout
    assert not _chamadas(mundo, "up")
    assert (mundo["pontos"] / "x.atual").read_text().strip() == mundo["c2"]


def test_inalterada_mas_parada_recria(mundo):
    mundo["pontos"].mkdir()
    (mundo["pontos"] / "x.atual").write_text(mundo["c1"] + "\n")
    r = _roda(mundo, "promover", "x", mundo["c2"], STUB_RODANDO="0")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo, "up")


def test_contexto_mudou_recria(mundo):
    mundo["pontos"].mkdir()
    (mundo["pontos"] / "x.atual").write_text(mundo["c2"] + "\n")
    r = _roda(mundo, "promover", "x", mundo["c3"])
    assert r.returncode == 0, r.stderr
    assert "inalterada" not in r.stdout
    assert _chamadas(mundo, "up")
    assert (mundo["pontos"] / "x.anterior").read_text().strip() == mundo["c2"]


def test_recriar_forcado_ignora_inalterada(mundo):
    mundo["pontos"].mkdir()
    (mundo["pontos"] / "x.atual").write_text(mundo["c1"] + "\n")
    r = _roda(mundo, "promover", "x", mundo["c2"], PF_STACK_RECRIAR="1")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo, "up")


def test_volta_a_sha_ja_promovido_sem_build(mundo):
    mundo["imagens"].write_text(f"x/app:{mundo['c1']}\nx/app:{mundo['c3']}\n")
    mundo["pontos"].mkdir()
    (mundo["pontos"] / "x.atual").write_text(mundo["c3"] + "\n")
    r = _roda(mundo, "promover", "x", mundo["c1"])
    assert r.returncode == 0, r.stderr
    assert not _chamadas(mundo, "build")
    assert "--no-build" in _chamadas(mundo, "up")[-1]


def test_testar_sem_perfil_teste_nada_a_medir(mundo):
    r = _roda(mundo, "testar", "x", mundo["c1"])
    assert r.returncode == 0, r.stderr
    assert "nada a medir" in r.stdout
    assert not _chamadas(mundo, "build") and not _chamadas(mundo, "run")


def test_testar_verde_constroi_e_roda(mundo):
    mundo["modelo"].write_text(json.dumps(MODELO_TESTE))
    r = _roda(mundo, "testar", "x", mundo["c1"])
    assert r.returncode == 0, r.stderr
    assert "verde" in r.stdout
    runs = _chamadas(mundo, "run")
    assert runs and runs[-1].split()[-1] == "app-teste" and "--profile teste" in runs[-1]
    assert not _chamadas(mundo, "up")
    assert not (mundo["pontos"] / "x.atual").exists()


def test_testar_reprovado_sai_4(mundo):
    mundo["modelo"].write_text(json.dumps(MODELO_TESTE))
    r = _roda(mundo, "testar", "x", mundo["c1"], STUB_TESTE_RC="1")
    assert r.returncode == 4
    assert "REPROVOU" in r.stderr


def test_testar_exige_rev(mundo):
    r = _roda(mundo, "testar", "x")
    assert r.returncode == 2
