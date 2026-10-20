"""`infra config <stack>` não imprime credencial embutida em URL (incidente #3888).

A máscara de `bin/_release/stack` (`mascara_segredos`) reconhecia o NOME da variável (SECRET, TOKEN, PASSWORD...).
`MOTOR_DSN` não casa, e a senha do motor-pg saiu inteira dentro da URL, nas formas yaml e json. A máscara passa a
cobrir também `usuario:senha@host` em qualquer valor, e deixa URL sem credencial como está.

Roda o ajudante real (`stack compose x config`) com a release, a topologia e o docker falsos; o docker falso imprime
o texto que o teste pôs em STUB_CONFIG_TEXTO no lugar do `docker compose config`.
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

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None, reason="precisa de bash e jq")

SENHA = "senha-de-ensaio-que-nao-e-segredo"

DOCKER_STUB = '''#!/usr/bin/env python3
import os, sys
if "config" in sys.argv[1:]:
    print(os.environ.get("STUB_CONFIG_TEXTO", ""))
sys.exit(0)
'''


@pytest.fixture
def config(tmp_path):
    raiz = tmp_path / "opt"
    sha = "b" * 40
    (raiz / "platafirma-x" / sha / "deploy" / "x").mkdir(parents=True)
    (raiz / "platafirma-x" / sha / "deploy" / "x" / "compose.yaml").write_text("name: x\nservices: {}\n")
    (raiz / "platafirma-x" / "current").symlink_to(sha)
    topo = tmp_path / "topo.json"
    topo.write_text(json.dumps({"stacks": {"x": {
        "slug": "x", "repo": "platafirma-x", "projeto": "x", "compose": "deploy/x/compose.yaml",
        "reversao": {"via": "up"}}}}))
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    docker = stubs / "docker"
    docker.write_text(DOCKER_STUB)
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    env = {**os.environ, "PATH": f"{stubs}{os.pathsep}{os.environ.get('PATH', '')}",
           "PF_RELEASE_RAIZ": str(raiz), "PLATAFIRMA_RELEASE": str(raiz / "current"),
           "PLATAFIRMA_INSTANCIA": str(tmp_path / "srv"), "DEPLOY_PONTOS": str(tmp_path / "pontos"),
           "DEPLOY_ENV_DIR": str(tmp_path / "env"), "DEPLOY_TOPO_ARQUIVO": str(topo)}

    def roda(texto):
        r = subprocess.run([BASH, str(STACK), "compose", "x", "config"], capture_output=True, text=True,
                           env={**env, "STUB_CONFIG_TEXTO": texto}, timeout=60)
        assert r.returncode == 0, r.stderr
        return r.stdout
    return roda


def test_dsn_em_yaml_sai_sem_a_senha(config):
    saida = config(f"      MOTOR_DSN: postgresql://motor:{SENHA}@indice:5432/motor")
    assert SENHA not in saida
    assert "postgresql://motor:***@indice:5432/motor" in saida


def test_dsn_em_json_sai_sem_a_senha(config):
    saida = config(f'        "MOTOR_DSN": "postgresql://motor:{SENHA}@indice:5432/motor",')
    assert SENHA not in saida
    assert "postgresql://motor:***@indice:5432/motor" in saida


def test_duas_urls_na_mesma_linha_saem_mascaradas(config):
    saida = config(f"      URLS: postgresql://a:{SENHA}@h1/db,redis://b:{SENHA}@h2/0")
    assert SENHA not in saida
    assert "postgresql://a:***@h1/db" in saida and "redis://b:***@h2/0" in saida


def test_url_sem_credencial_e_a_variavel_por_nome_seguem_como_estavam(config):
    saida = config("      MOTOR_API_URL: http://127.0.0.1:8000/health\n      RAG_API_TOKEN: valor-do-token")
    assert "http://127.0.0.1:8000/health" in saida
    assert "valor-do-token" not in saida and "RAG_API_TOKEN: ***" in saida
