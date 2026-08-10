"""Contrato --json de `infra estado` e `infra saude` (card #390, LOTE 1).

Roda o bin/infra de verdade como subprocesso, com PATH apontando para stubs de
docker/systemctl/curl/free/df escritos aqui — esta máquina de desenvolvimento
não tem nenhum dos dois de verdade (nem systemd, nem docker, nem jq). Cada
stub imprime uma saída canônica fixa (sucesso) ou sai com erro (falha); nada
é baixado da internet. Verificação contra infra real fica para o host,
depois, via ops-server — não é o que esta suíte precisa provar (ver
NOTAS-390.md, seção "ambiente de desenvolvimento local").

Cobertura: as duas ramas de `estado --json` e `saude --json` (formato de
sucesso, falha real vira {"erro":...}, texto sem a flag não muda). Fora
desta suíte: `infra logs/restart/exclusivo/cache` (não ganharam --json
neste card) e o caminho `systemctl --output=json` nativo do systemd — não
tentado na implementação (ver comentário em bin/infra) e por isso não
testado aqui.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
INFRA = REPO_RAIZ / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="sem bash no PATH — nao da pra rodar bin/infra")


def _python3_de_verdade():
    """python3/python no PATH desta maquina Windows costuma ser o stub da
    Microsoft Store (nao executa nada) — sem um python3 que funcione de
    verdade no PATH do stub, todo `python3 -c` dentro do bin/infra falharia
    por motivo estranho ao que este teste quer provar."""
    candidatos = [sys.executable, shutil.which("python3"), shutil.which("python")]
    for c in candidatos:
        if c and "WindowsApps" not in c:
            return c
    return None


PYTHON3_REAL = _python3_de_verdade()


def _stub(diretorio, nome, corpo):
    """Escreve um executavel `nome` em `diretorio` com `corpo` (bash) — +x
    sempre, independente do que o checkout do git preservou de modo de
    arquivo (o fixture nasce e roda dentro do mesmo teste)."""
    caminho = diretorio / nome
    caminho.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + corpo, encoding="utf-8", newline="\n")
    modo = caminho.stat().st_mode
    caminho.chmod(modo | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


# --- corpos dos stubs --------------------------------------------------------

DOCKER_OK = """
if [ "$1" = "ps" ]; then
  cat <<'EOF'
{"Names":"rag-extractor-api","State":"running","Status":"Up 9 days (healthy)"}
{"Names":"ops-mcp","State":"exited","Status":"Exited (137) 2 hours ago"}
EOF
  exit 0
fi
echo "docker-stub: comando nao coberto: $*" >&2
exit 1
"""

DOCKER_FALHA = """
echo "docker-stub: Cannot connect to the Docker daemon" >&2
exit 1
"""

SYSTEMCTL_OK = """
args="$*"
case "$args" in
  *list-timers*)
    cat <<'EOF'
Mon 2026-08-10 03:00:00 -03 11h left Sun 2026-08-09 03:00:00 -03 13h ago pf-descansar.timer pf-descansar.service
EOF
    ;;
  *state=failed*)
    cat <<'EOF'
  pf-agregador.service loaded failed failed agregador harness
EOF
    ;;
  *list-units*)
    cat <<'EOF'
* pf-ops-mcp.service loaded active running ops-mcp service
  pf-agregador.service loaded failed failed agregador harness
EOF
    ;;
  *)
    echo "systemctl-stub: comando nao coberto: $args" >&2
    exit 1
    ;;
esac
"""

CURL_OK = """
echo '{"status":"ok"}'
"""

CURL_FALHA = """
echo "curl-stub: connection refused" >&2
exit 7
"""

FREE_OK = """
cat <<'EOF'
              total        used        free      shared  buff/cache   available
Mem:            15Gi        4.2Gi        3.1Gi       512Mi        7.7Gi         10Gi
Swap:            2Gi           0B         2Gi
EOF
"""

DF_OK = """
cat <<'EOF'
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        99G   42G   53G  45% /
EOF
"""

DF_FALHA = """
echo "df-stub: Input/output error" >&2
exit 1
"""


def _monta_path(tmp_path, nome, **stubs):
    """Cria tmp_path/nome com os stubs pedidos (docker=DOCKER_OK, etc.) mais
    um python3 real (nao o stub da Microsoft Store) — devolve o diretorio."""
    if PYTHON3_REAL is None:
        pytest.skip("nao achei um python3 de verdade nesta maquina para o stub")
    d = tmp_path / nome
    d.mkdir()
    _stub(d, "python3", f'exec "{PYTHON3_REAL}" "$@"\n')
    for prog, corpo in stubs.items():
        _stub(d, prog, corpo)
    return d


def _roda(*args, path_dir, checa_exit=None):
    env = dict(os.environ)
    env["PATH"] = str(path_dir) + os.pathsep + env.get("PATH", "")
    r = subprocess.run(
        [BASH, str(INFRA), *args],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
        check=False,
    )
    if checa_exit is not None:
        assert r.returncode == checa_exit, (
            f"exit {r.returncode} != {checa_exit}\nstdout={r.stdout!r}\nstderr={r.stderr!r}"
        )
    return r


# --- fixtures de PATH ---------------------------------------------------

@pytest.fixture
def path_ok(tmp_path):
    return _monta_path(
        tmp_path, "bin-ok",
        docker=DOCKER_OK, systemctl=SYSTEMCTL_OK, curl=CURL_OK, free=FREE_OK, df=DF_OK,
    )


@pytest.fixture
def path_docker_falha(tmp_path):
    return _monta_path(
        tmp_path, "bin-docker-falha",
        docker=DOCKER_FALHA, systemctl=SYSTEMCTL_OK, curl=CURL_OK, free=FREE_OK, df=DF_OK,
    )


@pytest.fixture
def path_curl_falha(tmp_path):
    return _monta_path(
        tmp_path, "bin-curl-falha",
        docker=DOCKER_OK, systemctl=SYSTEMCTL_OK, curl=CURL_FALHA, free=FREE_OK, df=DF_OK,
    )


@pytest.fixture
def path_df_falha(tmp_path):
    return _monta_path(
        tmp_path, "bin-df-falha",
        docker=DOCKER_OK, systemctl=SYSTEMCTL_OK, curl=CURL_OK, free=FREE_OK, df=DF_FALHA,
    )


# --- infra estado --json -----------------------------------------------

def test_estado_json_formato(path_ok):
    r = _roda("estado", "--json", path_dir=path_ok, checa_exit=0)
    assert r.stderr == "" or "docker-stub" not in r.stderr
    dado = json.loads(r.stdout)  # estoura se stdout nao for SO o JSON
    assert dado == {
        "conteineres": [
            {"nome": "rag-extractor-api", "estado_docker": "running", "saude": "healthy", "desde": "Up 9 days"},
            {"nome": "ops-mcp", "estado_docker": "exited", "saude": None, "desde": "Exited (137) 2 hours ago"},
        ],
        "units": [
            {"nome": "pf-ops-mcp.service", "estado": "running"},
            {"nome": "pf-agregador.service", "estado": "failed"},
        ],
        "timers": [
            {"nome": "pf-descansar.service", "proxima_execucao": "Mon 2026-08-10 03:00:00"},
        ],
    }


def test_estado_json_filtra_por_alvo(path_ok):
    r = _roda("estado", "ops-mcp", "--json", path_dir=path_ok, checa_exit=0)
    dado = json.loads(r.stdout)
    assert [c["nome"] for c in dado["conteineres"]] == ["ops-mcp"]
    assert dado["units"] == []
    assert dado["timers"] == []


def test_estado_json_alvo_antes_ou_depois_da_flag(path_ok):
    a = json.loads(_roda("estado", "--json", "ops-mcp", path_dir=path_ok, checa_exit=0).stdout)
    b = json.loads(_roda("estado", "ops-mcp", "--json", path_dir=path_ok, checa_exit=0).stdout)
    assert a == b


def test_estado_json_falha_vira_objeto_erro(path_docker_falha):
    r = _roda("estado", "--json", path_dir=path_docker_falha)
    assert r.returncode != 0
    dado = json.loads(r.stdout)  # nunca stdout vazio
    assert set(dado) == {"erro"}
    assert dado["erro"]  # motivo preenchido, nao string vazia
    assert "docker-stub" in r.stderr  # diagnostico foi pro stderr


def test_estado_texto_sem_flag_nao_muda(path_ok):
    r = _roda("estado", path_dir=path_ok, checa_exit=0)
    assert "== contêineres" in r.stdout
    assert "== units de usuário (ativas e falhadas)" in r.stdout
    assert "== timers" in r.stdout
    # nao e JSON — e o texto tabulado de sempre.
    with pytest.raises(json.JSONDecodeError):
        json.loads(r.stdout)


# --- infra saude --json --------------------------------------------------

def test_saude_json_formato(path_ok):
    r = _roda("saude", "--json", path_dir=path_ok, checa_exit=0)
    dado = json.loads(r.stdout)
    assert dado["ops_health"] == {"ok": True, "motivo": None}
    assert dado["doentes"] == [{"nome": "ops-mcp", "status": "Exited (137) 2 hours ago"}]
    assert dado["falhadas"] == [{"nome": "pf-agregador.service", "estado": "failed"}]
    assert dado["disco"] == {
        "sistema_arquivos": "/dev/sda1", "tamanho": "99G", "usado": "42G",
        "disponivel": "53G", "uso_pct": "45%", "montado_em": "/",
    }
    assert dado["memoria"] == {
        "total": "15Gi", "usado": "4.2Gi", "livre": "3.1Gi",
        "compartilhado": "512Mi", "buffer_cache": "7.7Gi", "disponivel": "10Gi",
    }


def test_saude_json_ops_indisponivel_nao_e_erro_de_execucao(path_curl_falha):
    # curl falhando e DADO (ops fora do ar), nao falha de execucao do infra —
    # o resto do objeto continua populado, exit 0 preservado.
    r = _roda("saude", "--json", path_dir=path_curl_falha, checa_exit=0)
    dado = json.loads(r.stdout)
    assert dado["ops_health"]["ok"] is False
    assert dado["ops_health"]["motivo"]
    assert "erro" not in dado
    assert dado["disco"]["montado_em"] == "/"


def test_saude_json_falha_real_vira_objeto_erro(path_df_falha):
    r = _roda("saude", "--json", path_dir=path_df_falha)
    assert r.returncode != 0
    dado = json.loads(r.stdout)
    assert set(dado) == {"erro"}
    assert dado["erro"]
    assert "df-stub" in r.stderr


def test_saude_texto_sem_flag_nao_muda(path_ok):
    r = _roda("saude", path_dir=path_ok, checa_exit=0)
    assert r.stdout.startswith("ops-mcp /health: ")
    assert "== contêiner parado ou não-saudável" in r.stdout
    assert "== unit falhada" in r.stdout
    assert "== disco e memória" in r.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(r.stdout)
