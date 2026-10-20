"""Dependência entre stacks no registro (card #3842, R29 da spec motor): `reversao.depois` e `reversao.exige`.

- `depois` (lista de slugs da mesma família) põe a stack depois das que nomeia na ordem da promoção. O registro vem
  ordenado por slug, e `busca` viria antes de `motor`; com `depois: [motor]` a busca sobe depois do motor.
  Ciclo ou nome de fora da família não trava: vale a ordem do registro.
- `exige` (lista de slugs, de qualquer família) faz o ajudante recusar a subida (exit 1, com o nome) quando nenhuma
  das exigidas tem contêiner rodando no projeto compose dela. Sem o campo, nada muda.

O primeiro grupo roda `bin/release promover --ensaio` com forge local e `acervo` de mentira, como o teste do catálogo.
O segundo roda o ajudante real com a release, a topologia e o docker falsos, como o teste da imagem pinada.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
RELEASE = REPO_RAIZ / "bin" / "release"
STACK = REPO_RAIZ / "bin" / "_release" / "stack"
BASH = shutil.which("bash")
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    BASH is None or GIT is None or shutil.which("jq") is None,
    reason="precisa de bash, git e jq",
)


def _git(cwd, *args):
    return subprocess.run([GIT, *args], cwd=str(cwd), capture_output=True, text=True, check=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}).stdout.strip()


# --- a ordem da promoção (bin/release) ------------------------------------------------------------------

def _stack(slug, **reversao):
    return {"slug": slug, "repo": "fixture", "compose": f"deploy/{slug}/compose.yaml",
            "reversao": {"via": "promover", **reversao}}


def _ensaio(tmp_path, registro):
    """Promoção em ensaio de uma família `fixture` cujo registro (na ordem dada) é `registro`."""
    wt, forge = tmp_path / "wt", tmp_path / "forge.git"
    wt.mkdir()
    subprocess.run([GIT, "init", "-q", "--bare", str(forge)], check=True, capture_output=True)
    _git(wt, "init", "-q", "-b", "main")
    (wt / "README.md").write_text("um\n", encoding="utf-8")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "inicial")
    sha = _git(wt, "rev-parse", "HEAD")
    _git(wt, "remote", "add", "origin", str(forge))
    _git(wt, "push", "-q", "-u", "origin", "main")

    stub = tmp_path / "stub-bin"
    stub.mkdir()
    (tmp_path / "stacks.json").write_text(json.dumps(registro), encoding="utf-8")
    acervo = stub / "acervo"
    acervo.write_text('#!/usr/bin/env bash\n'
                      'if [ "$1" = ler ] && [ "$2" = casa ] && [ "$3" = stack ]; then\n'
                      f"  cat '{tmp_path / 'stacks.json'}'\n  exit 0\nfi\nexit 1\n", encoding="utf-8")
    acervo.chmod(0o755)

    env = dict(os.environ)
    env.update({
        "PF_RELEASE_RAIZ": str(tmp_path / "opt"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "srv"),
        "PLATAFIRMA_FAMILIAS": str(tmp_path / "familias.json"),
        "PLATAFIRMA_VENVS": str(tmp_path / "venvs.json"),
        "PLATAFIRMA_TERCEIROS": str(tmp_path / "terceiros.json"),
        "PF_RELEASE_PORTA": "0",
        "PATH": f"{stub}{os.pathsep}" + env.get("PATH", ""),
    })
    Path(env["PLATAFIRMA_FAMILIAS"]).write_text(json.dumps({"fixture": str(forge)}), encoding="utf-8")
    Path(env["PLATAFIRMA_VENVS"]).write_text("{}", encoding="utf-8")
    Path(env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")
    fam = Path(env["PF_RELEASE_RAIZ"]) / "fixture"
    fam.mkdir(parents=True)
    _git(fam, "clone", "-q", "--bare", str(forge), str(fam / ".repo.git"))
    return subprocess.run([str(RELEASE), "promover", "fixture", sha, "--ensaio"], env=env,
                          capture_output=True, text=True, timeout=90)


def _ordem(r):
    linha = next(l for l in r.stdout.splitlines() if l.startswith("stacks:") and "bin/_release/stack promover" in l)
    return linha.split("(")[0].split(":", 1)[1].split()


def test_sem_o_campo_a_ordem_e_a_do_registro(tmp_path):
    r = _ensaio(tmp_path, [_stack("busca"), _stack("motor")])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _ordem(r) == ["busca", "motor"]


def test_depois_poe_a_busca_depois_do_motor_mesmo_vindo_antes_por_slug(tmp_path):
    r = _ensaio(tmp_path, [_stack("busca", depois=["motor"]), _stack("motor")])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _ordem(r) == ["motor", "busca"]


def test_depois_mantem_a_ordem_das_demais(tmp_path):
    r = _ensaio(tmp_path, [_stack("a"), _stack("busca", depois=["motor"]), _stack("motor"), _stack("z")])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _ordem(r) == ["a", "motor", "busca", "z"]


def test_ciclo_ou_nome_de_fora_nao_trava_e_vale_a_ordem_do_registro(tmp_path):
    (tmp_path / "c").mkdir()
    ciclo = _ensaio(tmp_path / "c", [_stack("a", depois=["b"]), _stack("b", depois=["a"])])
    assert ciclo.returncode == 0, ciclo.stdout + ciclo.stderr
    assert _ordem(ciclo) == ["a", "b"]
    (tmp_path / "f").mkdir()
    fora = _ensaio(tmp_path / "f", [_stack("busca", depois=["rag"]), _stack("motor")])
    assert fora.returncode == 0, fora.stdout + fora.stderr
    assert _ordem(fora) == ["busca", "motor"]


# --- a conferência de dependência (bin/_release/stack) -------------------------------------------------

DOCKER_STUB = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
open(os.environ["STUB_LOG"], "a").write(" ".join(args) + "\n")
if args[:1] == ["ps"]:
    proj = [a.split("=", 2)[2] for a in args if a.startswith("label=com.docker.compose.project=")]
    if proj and proj[0] in os.environ.get("STUB_DE_PE", "").split(","):
        print("abc123")
    sys.exit(0)
if args[:2] == ["image", "inspect"]:
    sys.exit(1)
if args[:1] == ["compose"] and "config" in args:
    print(json.dumps({"services": {}}))
sys.exit(0)
'''


@pytest.fixture
def mundo(tmp_path):
    raiz = tmp_path / "opt"
    sha = "a" * 40
    (raiz / "platafirma-x" / sha / "deploy" / "x").mkdir(parents=True)
    (raiz / "platafirma-x" / sha / "deploy" / "x" / "compose.yaml").write_text("name: x\nservices: {}\n")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    docker = stubs / "docker"
    docker.write_text(DOCKER_STUB)
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    log = tmp_path / "docker.log"

    def topo(**x):
        arquivo = tmp_path / "topo.json"
        arquivo.write_text(json.dumps({"stacks": {
            "x": {"slug": "x", "repo": "platafirma-x", "projeto": "x", "compose": "deploy/x/compose.yaml",
                  "reversao": {"via": "promover", **x}},
            "y": {"slug": "y", "repo": "platafirma-y", "projeto": "projeto-y", "compose": "deploy/y/compose.yaml",
                  "reversao": {"via": "promover"}},
        }}))
        return arquivo

    env = {**os.environ, "PATH": f"{stubs}{os.pathsep}{os.environ.get('PATH', '')}",
           "PF_RELEASE_RAIZ": str(raiz), "PLATAFIRMA_RELEASE": str(raiz / "current"),
           "PLATAFIRMA_INSTANCIA": str(tmp_path / "srv"), "DEPLOY_PONTOS": str(tmp_path / "pontos"),
           "DEPLOY_ENV_DIR": str(tmp_path / "env"), "STUB_LOG": str(log)}
    env.pop("PF_STACK_RECRIAR", None)
    return {"sha": sha, "env": env, "log": log, "topo": topo}


def _promove(m, topo, **extra):
    env = {**m["env"], "DEPLOY_TOPO_ARQUIVO": str(topo), **extra}
    return subprocess.run([BASH, str(STACK), "promover", "x", m["sha"]], capture_output=True, text=True,
                          env=env, timeout=60)


def _subiu(m):
    return m["log"].exists() and any(" up " in f" {l} " for l in m["log"].read_text().splitlines())


def test_exigida_de_pe_deixa_subir(mundo):
    r = _promove(mundo, mundo["topo"](exige=["y"]), STUB_DE_PE="projeto-y")
    assert r.returncode == 0, r.stderr
    assert _subiu(mundo)


def test_exigida_parada_recusa_com_1_e_o_nome_e_nada_sobe(mundo):
    r = _promove(mundo, mundo["topo"](exige=["y"]), STUB_DE_PE="outro")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "exige de pe: y" in r.stderr
    assert not _subiu(mundo)


def test_exigida_fora_do_registro_conta_como_parada(mundo):
    r = _promove(mundo, mundo["topo"](exige=["nao-existe"]), STUB_DE_PE="projeto-y")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "nao-existe" in r.stderr
    assert not _subiu(mundo)


def test_sem_o_campo_nada_muda_e_o_docker_nao_e_perguntado_se_ha_conteiner(mundo):
    r = _promove(mundo, mundo["topo"](), STUB_DE_PE="")
    assert r.returncode == 0, r.stderr
    assert _subiu(mundo)
    assert not any(l.startswith("ps ") for l in mundo["log"].read_text().splitlines())
