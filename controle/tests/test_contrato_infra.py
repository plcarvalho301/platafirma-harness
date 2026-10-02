"""Contrato --json de `infra estado` e `infra saude` (card #390, LOTE 1); Q9 do
cabeçalho (usage, --ajuda, ato desconhecido, dependência, identidade) e os atos novos
de infra (up/down/ps/config/pull/build via bin/_release/stack, limpeza, agenda) do
card #3145.

Roda o bin/infra de verdade como subprocesso, com PATH apontando para stubs de
docker/systemctl/curl/free/df escritos aqui — esta máquina de desenvolvimento
não tem nenhum dos dois de verdade (nem systemd, nem docker, nem jq). Cada
stub imprime uma saída canônica fixa (sucesso) ou sai com erro (falha); nada
é baixado da internet. Verificação contra infra real fica para o host,
depois, via ops-server — não é o que esta suíte precisa provar (ver
NOTAS-390.md, seção "ambiente de desenvolvimento local").

Cobertura: as duas ramas de `estado --json` e `saude --json` (formato de
sucesso, falha real vira {"erro":...}, texto sem a flag não muda). Fora
desta suíte: `infra logs/exclusivo/cache` (não ganharam --json
neste card) e o caminho `systemctl --output=json` nativo do systemd — não
tentado na implementação (ver comentário em bin/infra) e por isso não
testado aqui.

Os atos novos (up/down/ps/config/pull/build/limpeza/agenda) dependem de arquivos
IRMÃOS localizados por caminho relativo ao próprio bin/infra (bin/_release/stack,
bin/_infra/limpeza-*) — nunca pelo PATH. Testá-los contra o bin/infra real desta
bancada dependeria de bin/_release/stack, que outro agente escreve ao mesmo tempo
nesta MESMA bancada (onda 1, frente C): por isso estes casos copiam bin/infra para
uma árvore isolada (fixture `arvore`), com ajudantes FAKE ao lado — o mesmo
contrato de vizinhança, sem a corrida.
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


def _roda(*args, path_dir, checa_exit=None, env_extra=None):
    env = dict(os.environ)
    env["PATH"] = str(path_dir) + os.pathsep + env.get("PATH", "")
    if env_extra:
        env.update(env_extra)
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


def test_estado_de_alvo_sem_conteiner_nem_unit_diz_que_nao_ha(path_ok):
    # #2856 linha 88: depois de `infra down`, `estado <stack>` só devolvia «Unit … could not be found»
    r = _roda("estado", "conversor", path_dir=path_ok, checa_exit=0)
    assert "conversor: sem contêiner" in r.stdout
    assert "could not be found" not in r.stdout + r.stderr


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


# --- Q9: cabeçalho / dispatch (card #3145) --------------------------------
#
# Estes casos não tocam docker/systemctl nem precisam deles: usage, --ajuda e ato
# desconhecido resolvem ANTES de qualquer chamada de substrato (Q2). Provamos isso
# com PATH cheio de DELATORES — programa que, se chamado, denuncia (saida 99, marca
# distinta) em vez de simular sucesso; se o teste ficar verde com um delator no meio,
# a garantia "sem efeito colateral" é real, não coincidência de stub gentil.

DELATORES = ("docker", "systemctl", "curl", "jq", "python3")


@pytest.fixture
def path_delator(tmp_path):
    d = tmp_path / "delatores"
    d.mkdir()
    for nome in DELATORES:
        _stub(d, nome, f'echo "DELATOR:{nome} chamado: $*" >&2\nexit 99\n')
    return d


def _sem_delator(r):
    assert "DELATOR:" not in r.stdout and "DELATOR:" not in r.stderr, (
        f"efeito colateral: {r.stdout!r} {r.stderr!r}"
    )


def test_infra_sem_argumento_exit_2_uso(path_delator):
    r = _roda(path_dir=path_delator, checa_exit=2)
    assert "uso:" in r.stderr
    _sem_delator(r)


@pytest.mark.parametrize("args", [
    ("--ajuda",), ("-h",), ("--help",),
    ("estado", "--ajuda"), ("up", "--ajuda"), ("agenda", "--ajuda"),
])
def test_infra_ajuda_exit_2_em_qualquer_posicao_sem_efeito(path_delator, args):
    r = _roda(*args, path_dir=path_delator, checa_exit=2)
    assert "uso:" in r.stderr
    _sem_delator(r)


def test_infra_ato_desconhecido_exit_2_com_lista(path_delator):
    r = _roda("bogus-ato", path_dir=path_delator, checa_exit=2)
    assert "infra: erro: ato desconhecido: bogus-ato" in r.stderr
    assert "atos:" in r.stderr
    assert "up" in r.stderr and "agenda" in r.stderr
    _sem_delator(r)


@pytest.fixture
def path_restart_ok(tmp_path):
    docker_restart = """
case "$1" in
  ps) echo "meu-conteiner" ;;
  restart) echo "meu-conteiner" ;;
  *) echo "docker-stub: comando nao coberto: $*" >&2; exit 1 ;;
esac
"""
    return _monta_path(tmp_path, "bin-restart-ok", docker=docker_restart)


def test_infra_restart_segue_o_contrato_sem_exigir_identidade(path_restart_ok):
    # decisão 9 (card #3145): restart NÃO exige PF_SUJEITO — a promoção do harness
    # depende dele (release chama `infra restart ops-mcp` sem identidade de cadeira).
    r = _roda("restart", "meu-conteiner", path_dir=path_restart_ok, checa_exit=0,
              env_extra={"PF_SUJEITO": ""})
    assert "reiniciado" in r.stdout


# --- atos novos: up/down/ps/config/pull/build, limpeza, agenda -----------
#
# Dependem de irmãos localizados por caminho relativo ao PRÓPRIO bin/infra
# (bin/_release/stack, bin/_infra/limpeza-*) — nunca pelo PATH (contrato do
# card #3145). Copiamos bin/infra para uma árvore isolada com ajudantes FAKE
# na mesma vizinhança relativa, em vez de depender do bin/_release/stack real
# desta bancada (escrito por outro agente, em paralelo, na mesma onda).

FAKE_STACK = """
printf 'STACK_ARGS:'
for a in "$@"; do printf ' [%s]' "$a"; done
printf '\\n'
for a in "$@"; do
  if [ "$a" = "nao-existe" ]; then exit 1; fi
done
exit 0
"""

FAKE_LIMPEZA = """
printf '{marca}:'
for a in "$@"; do printf ' [%s]' "$a"; done
printf '\\n'
exit 0
"""

FAKE_CRONTAB = """
printf 'CRONTAB_ARGS:'
for a in "$@"; do printf ' [%s]' "$a"; done
printf '\\n'
exit 0
"""


@pytest.fixture
def arvore(tmp_path):
    """bin/infra copiado para uma árvore isolada, com lib/raizes.sh irmão (de quem
    ele depende) e bin/_release/, bin/_infra/ vazios — cada teste põe o ajudante
    fake que precisa dentro deles."""
    raiz = tmp_path / "arvore"
    (raiz / "bin" / "_release").mkdir(parents=True)
    (raiz / "bin" / "_infra").mkdir(parents=True)
    (raiz / "lib").mkdir(parents=True)
    shutil.copy2(INFRA, raiz / "bin" / "infra")
    (raiz / "bin" / "infra").chmod(0o755)
    shutil.copy2(REPO_RAIZ / "lib" / "raizes.sh", raiz / "lib" / "raizes.sh")
    return raiz


def _roda_arvore(raiz, *args, env_extra=None, checa_exit=None):
    env = dict(os.environ)
    env.pop("PF_SUJEITO", None)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(
        [BASH, str(raiz / "bin" / "infra"), *args],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
        check=False,
    )
    if checa_exit is not None:
        assert r.returncode == checa_exit, (
            f"exit {r.returncode} != {checa_exit}\nstdout={r.stdout!r}\nstderr={r.stderr!r}"
        )
    return r


def test_up_sem_ajudante_dependencia_ausente_exit_3(arvore):
    # ato de leitura (ps) na mesma família de compose: nem chega a pedir identidade —
    # prova a dependência isolada do resto da regra (arq:0110 §4: dependência = 3).
    r = _roda_arvore(arvore, "ps", "minha-stack", checa_exit=3)
    assert "dependência" in r.stderr
    assert "bin/_release/stack" in r.stderr


def test_ps_alvo_inexistente_propaga_exit_1(arvore):
    _stub(arvore / "bin" / "_release", "stack", FAKE_STACK)
    r = _roda_arvore(arvore, "ps", "nao-existe", checa_exit=1)
    assert "STACK_ARGS: [compose] [nao-existe] [ps]" in r.stdout


def test_up_sem_pf_sujeito_exit_3(arvore):
    _stub(arvore / "bin" / "_release", "stack", FAKE_STACK)
    r = _roda_arvore(arvore, "up", "minha-stack", checa_exit=3)
    assert "PF_SUJEITO" in r.stderr


@pytest.mark.parametrize("acao", ["up", "down", "build", "pull"])
def test_stack_mutacao_chama_ajudante_com_args_certos(arvore, acao):
    _stub(arvore / "bin" / "_release", "stack", FAKE_STACK)
    r = _roda_arvore(arvore, acao, "minha-stack", "-d", "servico1",
                      env_extra={"PF_SUJEITO": "G48UFN"}, checa_exit=0)
    assert f"STACK_ARGS: [compose] [minha-stack] [{acao}] [-d] [servico1]" in r.stdout


def test_ps_config_nao_exigem_pf_sujeito(arvore):
    _stub(arvore / "bin" / "_release", "stack", FAKE_STACK)
    for acao in ("ps", "config"):
        r = _roda_arvore(arvore, acao, "minha-stack", checa_exit=0)
        assert f"[{acao}]" in r.stdout


def test_limpeza_logs_despacha_para_bin_infra(arvore):
    _stub(arvore / "bin" / "_infra", "limpeza-logs", FAKE_LIMPEZA.format(marca="LOGS"))
    r = _roda_arvore(arvore, "limpeza", "logs", "--foo", checa_exit=0)
    assert "LOGS: [--foo]" in r.stdout


def test_limpeza_quarentena_despacha_para_bin_infra(arvore):
    _stub(arvore / "bin" / "_infra", "limpeza-quarentena", FAKE_LIMPEZA.format(marca="QUAR"))
    r = _roda_arvore(arvore, "limpeza", "quarentena", checa_exit=0)
    assert "QUAR:" in r.stdout


def test_limpeza_valor_desconhecido_exit_2(arvore):
    r = _roda_arvore(arvore, "limpeza", "bogus", checa_exit=2)
    assert "limpeza desconhecida" in r.stderr


def test_agenda_conferir_chama_script_com_check(arvore):
    fake = _stub(arvore / "bin" / "_infra", "crontab-fake.sh", FAKE_CRONTAB)
    r = _roda_arvore(arvore, "agenda", "conferir",
                      env_extra={"INFRA_CRONTAB_SCRIPT": str(fake)}, checa_exit=0)
    assert "CRONTAB_ARGS: [--check]" in r.stdout


def test_agenda_aplicar_chama_script_sem_check(arvore):
    fake = _stub(arvore / "bin" / "_infra", "crontab-fake.sh", FAKE_CRONTAB)
    r = _roda_arvore(arvore, "agenda", "aplicar",
                      env_extra={"INFRA_CRONTAB_SCRIPT": str(fake)}, checa_exit=0)
    assert r.stdout.strip() == "CRONTAB_ARGS:"


def test_agenda_nao_exige_pf_sujeito(arvore):
    fake = _stub(arvore / "bin" / "_infra", "crontab-fake.sh", FAKE_CRONTAB)
    r = _roda_arvore(arvore, "agenda", "conferir",
                      env_extra={"INFRA_CRONTAB_SCRIPT": str(fake), "PF_SUJEITO": ""},
                      checa_exit=0)
    assert "CRONTAB_ARGS:" in r.stdout
