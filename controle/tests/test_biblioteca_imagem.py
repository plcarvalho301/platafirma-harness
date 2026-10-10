"""bin/_release/biblioteca: a imagem platafirma/ui sai da arvore que sobe (card #3391, feature #3388).

O lock corrigido de platafirma-ui (89457fc) nao chegava ao conteiner: a imagem era montada a mao e
a tag nao se movia. O ajudante constroi platafirma/ui:<versao> da arvore servida e recusa lock novo
com versao velha. Aqui o docker e de mentira (um script no PATH que grava as chamadas), entao nada
toca o daemon real.
"""

import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
AJUDANTE = RAIZ / "bin" / "_release" / "biblioteca"

DOCKER_FALSO = """#!/usr/bin/env python3
import os, pathlib, sys
d = pathlib.Path(os.environ["FAKE_DOCKER_DIR"])
args = sys.argv[1:]
with (d / "chamadas.log").open("a") as f:
    f.write(" ".join(args) + "\\n")

def chave(tag):
    return d / ("img." + tag.replace("/", "_").replace(":", "_"))

if args[:2] == ["image", "inspect"]:
    f = chave(args[-1])
    if not f.exists():
        sys.exit(1)
    if "-f" in args:
        print(f.read_text().strip())
    sys.exit(0)
if args[:2] == ["image", "rm"]:
    chave(args[-1]).unlink()
    sys.exit(0)
if args[0] == "build":
    if (d / "falha_build").exists():
        print("erro: npm ci falhou")
        sys.exit(1)
    tag = args[args.index("-t") + 1]
    lock = [a.split("=", 1)[1] for a in args if a.startswith("pf.ui.lock=")][0]
    chave(tag).write_text(lock)
    sys.exit(0)
if args[0] == "run":
    print((d / "versao").read_text(), end="")
    sys.exit(0)
sys.exit(2)
"""


@pytest.fixture
def mundo(tmp_path):
    """PATH com docker de mentira; dir de estado do falso."""
    estado = tmp_path / "docker-estado"
    estado.mkdir()
    (estado / "versao").write_text("platafirma-ui 0.5.1\n")
    bin_com = tmp_path / "bin-com-docker"
    bin_com.mkdir()
    falso = bin_com / "docker"
    falso.write_text(DOCKER_FALSO)
    falso.chmod(falso.stat().st_mode | stat.S_IXUSR)
    # PATH sem docker: so o python3 (o ajudante e o docker de mentira rodam nele)
    bin_sem = tmp_path / "bin-sem-docker"
    bin_sem.mkdir()
    python = shutil.which("python3")
    assert python, "python3 ausente no ambiente de teste"
    (bin_sem / "python3").symlink_to(os.path.realpath(python))
    return {"estado": estado, "com": bin_com, "sem": bin_sem}


def arvore(raiz: Path, nome: str, versao: str, lock: str, com_dockerfile: bool = True) -> Path:
    a = raiz / nome
    (a / "src" / "base").mkdir(parents=True)
    if com_dockerfile:
        (a / "Dockerfile").write_text("FROM scratch\n")
    (a / "src" / "base" / "package.json").write_text(json.dumps({"name": "x", "version": versao}))
    (a / "src" / "base" / "package-lock.json").write_text(lock)
    return a


def rodar(mundo, *args, com_docker=True):
    env = {
        "PATH": str(mundo["com"] if com_docker else mundo["sem"]) + (":" + str(mundo["sem"]) if com_docker else ""),
        "FAKE_DOCKER_DIR": str(mundo["estado"]),
        "HOME": str(mundo["estado"]),
    }
    return subprocess.run([str(AJUDANTE), *map(str, args)], capture_output=True, text=True, env=env)


def chamadas(mundo):
    log = mundo["estado"] / "chamadas.log"
    return log.read_text().splitlines() if log.exists() else []


def hash_lock(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


def test_ajudante_e_executavel():
    assert os.access(AJUDANTE, os.X_OK), "bin/_release/biblioteca sem bit de execucao"


def test_familia_sem_biblioteca_sai_zero_sem_tocar_docker(mundo, tmp_path):
    a = arvore(tmp_path, "sem-docker", "0.5.1", "{}", com_dockerfile=False)
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 0, p.stderr
    assert chamadas(mundo) == []


def test_imagem_ausente_constroi_rotula_e_confere_a_versao(mundo, tmp_path):
    lock = '{"lockfileVersion": 3, "a": 1}'
    a = arvore(tmp_path, "nova", "0.5.1", lock)
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 0, p.stderr
    build = [c for c in chamadas(mundo) if c.startswith("build ")]
    assert len(build) == 1
    assert "-t platafirma/ui:0.5.1" in build[0]
    assert f"pf.ui.lock={hash_lock(lock)}" in build[0]
    assert "pf.ui.revisao=nova" in build[0]
    assert "construida" in p.stdout


def test_imagem_existente_com_o_mesmo_lock_nao_reconstroi(mundo, tmp_path):
    lock = '{"a": 1}'
    (mundo["estado"] / "img.platafirma_ui_0.5.1").write_text(hash_lock(lock))
    a = arvore(tmp_path, "igual", "0.5.1", lock)
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 0, p.stderr
    assert not [c for c in chamadas(mundo) if c.startswith("build ")]
    assert "sem build" in p.stdout


def test_imagem_existente_sem_rotulo_e_reaproveitada(mundo, tmp_path):
    (mundo["estado"] / "img.platafirma_ui_0.5.1").write_text("")
    a = arvore(tmp_path, "antiga", "0.5.1", '{"a": 1}')
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 0, p.stderr
    assert not [c for c in chamadas(mundo) if c.startswith("build ")]
    assert "sem rotulo" in p.stdout


def test_mesma_tag_com_outro_lock_recusa_com_caminho(mundo, tmp_path):
    (mundo["estado"] / "img.platafirma_ui_0.5.1").write_text(hash_lock('{"velho": 1}'))
    a = arvore(tmp_path, "outro", "0.5.1", '{"novo": 1}')
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 4
    assert "imutavel" in p.stderr
    assert "caminho:" in p.stderr
    assert not [c for c in chamadas(mundo) if c.startswith("build ")]


def test_lock_mudou_e_versao_igual_recusa_antes_de_tocar_docker(mundo, tmp_path):
    ant = arvore(tmp_path, "no-ar", "0.5.0", '{"a": 1}')
    nova = arvore(tmp_path, "sobe", "0.5.0", '{"a": 2}')
    p = rodar(mundo, "garantir", nova, "--anterior", ant)
    assert p.returncode == 4
    assert "lock de src/base mudou" in p.stderr
    assert "caminho:" in p.stderr
    assert chamadas(mundo) == []


def test_lock_mudou_com_versao_nova_constroi(mundo, tmp_path):
    ant = arvore(tmp_path, "no-ar", "0.5.0", '{"a": 1}')
    nova = arvore(tmp_path, "sobe", "0.5.1", '{"a": 2}')
    p = rodar(mundo, "garantir", nova, "--anterior", ant)
    assert p.returncode == 0, p.stderr
    assert [c for c in chamadas(mundo) if c.startswith("build ")]


def test_lock_igual_e_versao_igual_nao_recusa(mundo, tmp_path):
    (mundo["estado"] / "img.platafirma_ui_0.5.0").write_text("")
    ant = arvore(tmp_path, "no-ar", "0.5.0", '{"a": 1}')
    nova = arvore(tmp_path, "sobe", "0.5.0", '{"a": 1}')
    p = rodar(mundo, "garantir", nova, "--anterior", ant)
    assert p.returncode == 0, p.stderr


def test_build_que_falha_sai_3_com_o_fim_do_log(mundo, tmp_path):
    (mundo["estado"] / "falha_build").write_text("")
    a = arvore(tmp_path, "quebra", "0.5.1", '{"a": 1}')
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 3
    assert "npm ci falhou" in p.stderr


def test_versao_servida_diferente_remove_a_tag_e_sai_3(mundo, tmp_path):
    (mundo["estado"] / "versao").write_text("platafirma-ui 0.4.0\n")
    a = arvore(tmp_path, "errada", "0.5.1", '{"a": 1}')
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 3
    assert "tag removida" in p.stderr
    assert not (mundo["estado"] / "img.platafirma_ui_0.5.1").exists()


def test_docker_ausente_sai_3(mundo, tmp_path):
    a = arvore(tmp_path, "sem-dk", "0.5.1", '{"a": 1}')
    p = rodar(mundo, "garantir", a, com_docker=False)
    assert p.returncode == 3
    assert "docker" in p.stderr


def test_versao_ilegivel_sai_3(mundo, tmp_path):
    a = arvore(tmp_path, "sem-versao", "latest", '{"a": 1}')
    p = rodar(mundo, "garantir", a)
    assert p.returncode == 3
    assert "versao ilegivel" in p.stderr


def test_uso_errado_sai_2(mundo):
    assert rodar(mundo).returncode == 2
    assert rodar(mundo, "outro", "x").returncode == 2
