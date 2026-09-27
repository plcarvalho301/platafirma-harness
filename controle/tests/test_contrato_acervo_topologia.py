# Contrato de `acervo listar topologia --rotas|--acessos` (card #3145 frente D) — a
# porta de `deploy <stack> rotas|acessos` (bin/deploy, apagado nesta fita). Testa a
# resolucao de caminho e a leitura do compose/ingress a partir de um `docker` de
# fixture (delator sem stub, arq:0110/conftest); nunca toca psql/docker reais.
import os
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN_ACERVO = os.path.join(REPO, "bin", "acervo")


def _acervo(*args, env=None):
    return subprocess.run([BIN_ACERVO, *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def _docker_topologia(tmp_path, stacks_json):
    """`docker` de fixture: responde `exec -i rag-extractor-pg psql ...` com o array
    JSON dado (a mesma forma que `acervo stack ver` devolve) e recusa o resto — o
    contrato de `_psql_json` (bin/_acervo/listar) e so isso: um SELECT, uma linha."""
    d = tmp_path / "bin-docker"
    d.mkdir()
    p = d / "docker"
    p.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "exec" ]; then\n'
        f"  cat <<'JSON'\n{stacks_json}\nJSON\n"
        "  exit 0\n"
        "fi\n"
        'echo "docker-stub: comando desconhecido: $*" >&2\n'
        "exit 1\n"
    )
    p.chmod(0o755)
    return d


def _docker_topologia_e_compose(tmp_path, stacks_json, compose_yaml):
    """Como acima, e tambem responde `compose -f ... config` com o YAML dado (o
    `docker compose config` que `--acessos` roda para resolver o compose do gate)."""
    d = tmp_path / "bin-docker"
    d.mkdir()
    p = d / "docker"
    p.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "exec" ]; then\n'
        f"  cat <<'JSON'\n{stacks_json}\nJSON\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "compose" ]; then\n'
        f"  cat <<'YAML'\n{compose_yaml}\nYAML\n"
        "  exit 0\n"
        "fi\n"
        'echo "docker-stub: comando desconhecido: $*" >&2\n'
        "exit 1\n"
    )
    p.chmod(0o755)
    return d


# --- rotas -----------------------------------------------------------------------

def test_topologia_rotas_stack_fixture(tmp_path):
    inst = tmp_path / "instancia"
    ingress = inst / "deploy" / "web" / "ingress.yaml"
    ingress.parent.mkdir(parents=True)
    ingress.write_text(
        "ingress:\n"
        "  - hostname: web.example.com\n"
        "    path: /\n"
        "    service: web\n"
        "  - service: catchall\n"
    )
    stacks = ('[{"slug":"web","papel":"front","critico":false,"repo":"platafirma-web",'
              '"compose":"docker-compose.yml","rotas":"%s","segredos":[],'
              '"reversao":null,"gate":null,"profiles":[],"nota":null,"instancias":null}]'
              % ingress)
    docker_dir = _docker_topologia(tmp_path, stacks)
    env = {"PLATAFIRMA_INSTANCIA": str(inst),
           "PATH": f"{docker_dir}{os.pathsep}{os.environ['PATH']}"}

    r = _acervo("listar", "casa", "topologia", "web", "--rotas", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "web.example.com" in r.stdout
    assert "web" in r.stdout
    assert "catchall" in r.stdout
    assert "(catch-all)" in r.stdout


def test_topologia_rotas_stack_sem_ingress_declarado(tmp_path):
    stacks = ('[{"slug":"sozinha","papel":null,"critico":false,"repo":"platafirma-sozinha",'
              '"compose":"docker-compose.yml","rotas":null,"segredos":null,'
              '"reversao":null,"gate":null,"profiles":null,"nota":null,"instancias":null}]')
    docker_dir = _docker_topologia(tmp_path, stacks)
    env = {"PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
           "PATH": f"{docker_dir}{os.pathsep}{os.environ['PATH']}"}

    r = _acervo("listar", "casa", "topologia", "sozinha", "--rotas", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nao declara ingress" in r.stdout


def test_topologia_rotas_stack_inexistente(tmp_path):
    docker_dir = _docker_topologia(tmp_path, "[]")
    env = {"PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
           "PATH": f"{docker_dir}{os.pathsep}{os.environ['PATH']}"}

    r = _acervo("listar", "casa", "topologia", "naoexiste", "--rotas", env=env)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "nao esta no registro" in r.stderr


def test_topologia_rotas_forma_do_aceite_sem_particao(tmp_path):
    """`acervo listar topologia <stack> --rotas` (sem `casa`, a forma do card #3145) tem
    de responder igual a forma conforme, nao so avisar e morrer no ramo deprecado."""
    inst = tmp_path / "instancia"
    ingress = inst / "deploy" / "web" / "ingress.yaml"
    ingress.parent.mkdir(parents=True)
    ingress.write_text("ingress:\n  - hostname: web.example.com\n    service: web\n")
    stacks = ('[{"slug":"web","papel":null,"critico":false,"repo":"platafirma-web",'
              '"compose":"docker-compose.yml","rotas":"%s","segredos":[],'
              '"reversao":null,"gate":null,"profiles":[],"nota":null,"instancias":null}]'
              % ingress)
    docker_dir = _docker_topologia(tmp_path, stacks)
    env = {"PLATAFIRMA_INSTANCIA": str(inst),
           "PATH": f"{docker_dir}{os.pathsep}{os.environ['PATH']}"}

    r_conforme = _acervo("listar", "casa", "topologia", "web", "--rotas", env=env)
    r_aceite = _acervo("listar", "topologia", "web", "--rotas", env=env)
    assert r_conforme.returncode == 0 == r_aceite.returncode
    assert r_conforme.stdout == r_aceite.stdout


# --- acessos ----------------------------------------------------------------------

def test_topologia_acessos_com_gate_declarado(tmp_path):
    inst = tmp_path / "instancia"
    gate = inst / "deploy" / "gateway" / "gate.yaml"
    gate.parent.mkdir(parents=True)
    gate.write_text("services: {}\n")  # conteudo real nao importa: docker e fixture
    allow = inst / "deploy" / "gateway" / "allow.txt"
    allow.write_text("alice@example.com\nbob@example.com\n")

    stacks = ('[{"slug":"gateway","papel":"gw","critico":true,"repo":"platafirma-gw",'
              '"compose":"docker-compose.yml","rotas":null,"segredos":[],'
              '"reversao":null,"gate":"%s","profiles":[],"nota":null,"instancias":null}]'
              % gate)
    compose_yaml = (
        "name: gw-project\n"
        "services:\n"
        "  oauth2-proxy-gateway:\n"
        "    command:\n"
        '      - "--authenticated-emails-file=/etc/allow.txt"\n'
        "    volumes:\n"
        "      - source: %s\n"
        "        target: /etc/allow.txt\n" % allow
    )
    docker_dir = _docker_topologia_e_compose(tmp_path, stacks, compose_yaml)
    env = {"PLATAFIRMA_INSTANCIA": str(inst),
           "PATH": f"{docker_dir}{os.pathsep}{os.environ['PATH']}"}

    r = _acervo("listar", "casa", "topologia", "gateway", "--acessos", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "gate    :" in r.stdout
    assert "oauth2-proxy-gateway" in r.stdout
    assert "alice@example.com" in r.stdout
    assert "bob@example.com" in r.stdout


def test_topologia_acessos_stack_inexistente(tmp_path):
    docker_dir = _docker_topologia(tmp_path, "[]")
    env = {"PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
           "PATH": f"{docker_dir}{os.pathsep}{os.environ['PATH']}"}

    r = _acervo("listar", "casa", "topologia", "naoexiste", "--acessos", env=env)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "nao esta no registro" in r.stderr


# --- usage/--ajuda ------------------------------------------------------------------

def test_topologia_rotas_sem_stack_e_uso():
    r = _acervo("listar", "casa", "topologia", "--rotas")
    assert r.returncode == 2
    assert "exige <stack>" in r.stderr
    assert "uso" in r.stderr.lower()


def test_topologia_rotas_e_acessos_juntos_e_uso():
    r = _acervo("listar", "casa", "topologia", "web", "--rotas", "--acessos")
    assert r.returncode == 2
    assert "escolha --rotas OU --acessos" in r.stderr


def test_topologia_ajuda_universal():
    r = _acervo("listar", "casa", "topologia", "web", "--rotas", "--ajuda")
    assert r.returncode == 2
    assert "uso" in r.stderr.lower()
