"""Contrato de bin/_infra/conversor-sob-demanda (#4026, ordem do dono de 28/10/2026: o conversor só fica
ligado enquanto o pipeline de ingestão roda).

- `acordar` liga a stack quando alguma réplica não está de pé e saudável, espera todas saudáveis e marca a
  hora; com todas de pé não chama nada;
- `adormecer` para a stack (stop, nunca down) só quando todas as réplicas dizem no /saude que estão livres
  há o limite e o último acordar passou dele; réplica ocupada, recente ou sem `ocioso_s` segura ligada;
- fora da release, sem a chave do teste, não toca nada.

Roda o ajudante real desta árvore com docker e ajudante de stack falsos: o docker lê os contêineres de um
JSON de estado, e o ajudante de stack anota a chamada e muda esse estado (up liga, stop para).
"""
import json
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
AJUDANTE = REPO_RAIZ / "bin" / "_infra" / "conversor-sob-demanda"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("flock") is None, reason="precisa de bash e flock")

DOCKER_STUB = r'''#!/usr/bin/env python3
import json, os, sys
estado = json.load(open(os.environ["STUB_ESTADO"]))
args = sys.argv[1:]
if args[:1] == ["ps"]:
    for c in estado:
        print(c["nome"])
elif args[:1] == ["inspect"]:
    por_nome = {c["nome"]: c for c in estado}
    for n in args[3:]:
        c = por_nome[n]
        print(f"/{n} {c['estado']} {c['saude']}")
elif args[:1] == ["exec"]:
    c = {c["nome"]: c for c in estado}[args[1]]
    if c.get("ocioso") is None:
        sys.exit(1)
    print(c["ocioso"])
'''

STACK_STUB = r'''#!/usr/bin/env python3
import json, os, sys
open(os.environ["STUB_LOG"], "a").write(" ".join(sys.argv[1:]) + "\n")
caminho = os.environ["STUB_ESTADO"]
estado = json.load(open(caminho))
if sys.argv[3] == "up":
    for c in estado:
        c["estado"], c["saude"] = "running", "healthy"
elif sys.argv[3] == "stop":
    for c in estado:
        c["estado"], c["saude"] = "exited", "-"
json.dump(estado, open(caminho, "w"))
'''


def _exe(caminho, texto):
    caminho.write_text(texto)
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def mundo(tmp_path):
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    _exe(stubs / "docker", DOCKER_STUB)
    _exe(tmp_path / "stack", STACK_STUB)
    estado = tmp_path / "estado.json"
    instancia = tmp_path / "srv"
    env = {
        **os.environ,
        "PATH": f"{stubs}{os.pathsep}{os.environ.get('PATH', '')}",
        "PF_RELEASE_RAIZ": str(tmp_path / "opt"),
        "PLATAFIRMA_INSTANCIA": str(instancia),
        "PF_STACK_BIN": str(tmp_path / "stack"),
        "PF_CONVERSOR_FORA_DA_RELEASE": "1",
        "PF_CONVERSOR_OCIOSO_S": "900",
        "PF_CONVERSOR_ESPERA_S": "5",
        "PF_CONVERSOR_PASSO_S": "0.1",
        "STUB_ESTADO": str(estado),
        "STUB_LOG": str(tmp_path / "stack.log"),
    }
    return {"env": env, "estado": estado, "log": tmp_path / "stack.log",
            "marca": instancia / "var" / "conversor" / "acordado-em"}


def _conteineres(m, *replicas):
    m["estado"].write_text(json.dumps([
        {"nome": n, "estado": est, "saude": saude, "ocioso": ocioso} for n, est, saude, ocioso in replicas]))


def _roda(m, ato, **extra):
    return subprocess.run([BASH, str(AJUDANTE), ato], capture_output=True, text=True,
                          env={**m["env"], **extra}, timeout=60, check=False)


def _chamadas(m):
    return m["log"].read_text().splitlines() if m["log"].exists() else []


def _marca_antiga(m, segundos):
    m["marca"].parent.mkdir(parents=True, exist_ok=True)
    m["marca"].touch()
    antes = time.time() - segundos
    os.utime(m["marca"], (antes, antes))


def test_acordar_liga_a_stack_parada_e_espera_saudavel(mundo):
    _conteineres(mundo, ("conversor", "exited", "-", None), ("conversor-2", "exited", "-", None))
    r = _roda(mundo, "acordar")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo) == ["compose conversor up -d"]
    assert mundo["marca"].exists() and "conversor pronto" in r.stderr


def test_acordar_com_tudo_de_pe_nao_chama_nada(mundo):
    _conteineres(mundo, ("conversor", "running", "healthy", 0), ("conversor-2", "running", "healthy", 0))
    r = _roda(mundo, "acordar")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo) == [] and mundo["marca"].exists()


def test_acordar_sem_conteiner_nenhum_liga(mundo):
    _conteineres(mundo)
    STACK_QUE_CRIA = mundo["env"]["PF_STACK_BIN"]
    Path(STACK_QUE_CRIA).write_text(STACK_STUB.replace(
        'if sys.argv[3] == "up":',
        'if sys.argv[3] == "up" and not estado:\n    estado.append({"nome": "conversor", "estado": "x", "saude": "-"})\n'
        'if sys.argv[3] == "up":'))
    r = _roda(mundo, "acordar")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo) == ["compose conversor up -d"]


def test_fora_da_release_nao_toca_a_stack(mundo):
    _conteineres(mundo, ("conversor", "exited", "-", None))
    env = dict(mundo["env"])
    env.pop("PF_CONVERSOR_FORA_DA_RELEASE")
    r = subprocess.run([BASH, str(AJUDANTE), "acordar"], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0 and "fora da release" in r.stderr
    assert _chamadas(mundo) == []


def test_adormecer_para_com_todas_livres_e_acordar_antigo(mundo):
    _conteineres(mundo, ("conversor", "running", "healthy", 1000), ("conversor-2", "running", "healthy", 950))
    _marca_antiga(mundo, 1000)
    r = _roda(mundo, "adormecer")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo) == ["compose conversor stop"]
    assert r.stdout.startswith("parado: ocioso")


@pytest.mark.parametrize("ocioso", [100, None], ids=["uma-replica-trabalhou-ha-pouco", "replica-sem-ocioso_s"])
def test_adormecer_fica_quando_uma_replica_nao_esta_livre_ha_o_limite(mundo, ocioso):
    _conteineres(mundo, ("conversor", "running", "healthy", 1000), ("conversor-2", "running", "healthy", ocioso))
    _marca_antiga(mundo, 1000)
    r = _roda(mundo, "adormecer")
    assert r.returncode == 0, r.stderr
    assert _chamadas(mundo) == [] and r.stdout.startswith("fica: conversor-2")


def test_adormecer_fica_quando_o_acordar_e_recente(mundo):
    _conteineres(mundo, ("conversor", "running", "healthy", 5000))
    _marca_antiga(mundo, 60)
    r = _roda(mundo, "adormecer")
    assert r.returncode == 0 and _chamadas(mundo) == [] and r.stdout.startswith("fica: acordado")


def test_adormecer_com_tudo_parado_nao_chama_nada(mundo):
    _conteineres(mundo, ("conversor", "exited", "-", None))
    r = _roda(mundo, "adormecer")
    assert r.returncode == 0 and _chamadas(mundo) == [] and r.stdout.startswith("parado: nada rodando")
