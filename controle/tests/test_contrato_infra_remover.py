"""`infra remover` e `infra limpeza jobs`: o resíduo fora do declarado ganha verbo (balde #2856 linha 17).

Antes, nenhum verbo derrubava contêiner avulso nem tirava unit, e o resíduo virava ato do dono no
host: o nginx kind_gould, subido à mão em 15/10/2026, e 15 jobs avulsos falhados acumulados em
`infra estado` entre 12 e 19/10. `infra remover` tira contêiner avulso (guardando a inspeção antes),
unit transitória parada (reset-failed) e unit da conta não declarada (arquivo para a quarentena);
recusa o declarado. `infra limpeza jobs` tira da lista os jobs do longjob falhados há mais de N
dias. Estes casos rodam o bin/infra de verdade com docker e systemctl de mentira no PATH: nada toca
a produção.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("python3") is None,
                                reason="sem bash ou python3 no PATH")

# docker de mentira: os contêineres vivos moram num arquivo; inspect lê a inspeção do arquivo
# do contêiner; rm tira da lista e deixa rastro.
DOCKER = r"""#!/usr/bin/env bash
vivos="$STUB_DIR/conteineres"
case "$1" in
  ps) cat "$vivos" 2>/dev/null ;;
  inspect)
    c="${@: -1}"
    grep -qx "$c" "$vivos" 2>/dev/null || exit 1
    cat "$STUB_DIR/inspect-$c.json" ;;
  rm)
    c="${@: -1}"
    echo "rm $c" >> "$STUB_DIR/rastro"
    grep -vx "$c" "$vivos" > "$vivos.novo" || true; mv "$vivos.novo" "$vivos" ;;
  *) echo "docker-stub: nao coberto: $*" >&2; exit 1 ;;
esac
"""

# systemctl de mentira: o estado de cada unit vem de variáveis; todo ato vai para o rastro.
SYSTEMCTL = r"""#!/usr/bin/env bash
[ "$1" = "--user" ] && shift
u="${@: -1}"
case "$1" in
  cat) case " ${STUB_UNITS:-} " in *" $u "*) exit 0 ;; *) exit 1 ;; esac ;;
  show-environment) exit 0 ;;
  show)
    case "$*" in
      *Transient*) echo "${STUB_TRANSIENT:-no}" ;;
      *ActiveState*) echo "${STUB_ATIVO:-inactive}" ;;
      *FragmentPath*) echo "${STUB_FRAG:-}" ;;
    esac ;;
  list-units) cat "$STUB_DIR/falhadas" 2>/dev/null ;;
  reset-failed|stop|disable|daemon-reload) echo "$1 ${u}" >> "$STUB_DIR/rastro" ;;
  *) echo "systemctl-stub: nao coberto: $*" >&2; exit 1 ;;
esac
"""


def inspecao(nome, projeto=None):
    labels = {"com.docker.compose.project": projeto} if projeto else {}
    return [{
        "Name": "/" + nome, "Created": "2026-10-15T13:22:13Z",
        "State": {"Status": "running"},
        "Config": {"Image": "nginx:alpine", "Labels": labels,
                   "Entrypoint": ["/docker-entrypoint.sh"], "Cmd": ["nginx", "-g", "daemon off;"]},
        "Mounts": [{"Source": "/home/claudinho/AI/medida/nginx.conf",
                    "Destination": "/etc/nginx/conf.d/default.conf", "RW": False}],
        "NetworkSettings": {"Ports": {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8099"}]}},
    }]


class Cena:
    def __init__(self, tmp_path):
        self.dir = tmp_path / "stub"
        self.bin = tmp_path / "bin"
        self.inst = tmp_path / "instancia"
        self.units = tmp_path / "home" / ".config" / "systemd" / "user"
        self.decl = tmp_path / "release" / "core" / "deploy"
        for p in (self.dir, self.bin, self.inst, self.units, self.decl):
            p.mkdir(parents=True)
        for nome, corpo in (("docker", DOCKER), ("systemctl", SYSTEMCTL)):
            f = self.bin / nome
            f.write_text(corpo)
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        (self.dir / "rastro").write_text("")
        (self.dir / "conteineres").write_text("")
        (self.decl / "units-da-instancia.json").write_text('{"units": ["ops-healthcheck", "sinal"]}\n')

    def conteiner(self, nome, projeto=None):
        with (self.dir / "conteineres").open("a") as f:
            f.write(nome + "\n")
        (self.dir / f"inspect-{nome}.json").write_text(json.dumps(inspecao(nome, projeto)))

    def vivos(self):
        return (self.dir / "conteineres").read_text().split()

    def rastro(self):
        return (self.dir / "rastro").read_text().splitlines()

    def roda(self, *args, sujeito="ti@teste", **env):
        e = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
             "STUB_DIR": str(self.dir), "PLATAFIRMA_INSTANCIA": str(self.inst),
             "INFRA_UNITS_DIR": str(self.units), "INFRA_DECLARADOS": str(self.decl),
             "INFRA_REMOVIDOS": str(self.inst / "removidos"),
             "INFRA_QUARENTENA": str(self.inst / "quarentena")}
        e.pop("PF_SUJEITO", None)
        if sujeito:
            e["PF_SUJEITO"] = sujeito
        e.update(env)
        return subprocess.run([BASH, str(INFRA), *args], capture_output=True, text=True,
                              env=e, timeout=30, check=False)


@pytest.fixture
def cena(tmp_path):
    return Cena(tmp_path)


# --- contêiner avulso ------------------------------------------------------------------------

def test_ver_mostra_a_inspecao_e_nao_remove(cena):
    cena.conteiner("kind_gould")
    r = cena.roda("remover", "kind_gould", "--ver", sujeito=None)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "imagem:    nginx:alpine" in r.stdout
    assert "/home/claudinho/AI/medida/nginx.conf -> /etc/nginx/conf.d/default.conf (ro)" in r.stdout
    assert "80/tcp -> 127.0.0.1:8099" in r.stdout
    assert "nenhuma (avulso)" in r.stdout and "removível: sim" in r.stdout
    assert cena.vivos() == ["kind_gould"] and cena.rastro() == []


def test_remove_o_avulso_guardando_a_inspecao_antes(cena):
    cena.conteiner("kind_gould")
    r = cena.roda("remover", "kind_gould")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cena.vivos() == [] and cena.rastro() == ["rm kind_gould"]
    guardadas = list((cena.inst / "removidos").glob("kind_gould-*.json"))
    assert len(guardadas) == 1
    assert json.loads(guardadas[0].read_text())[0]["Config"]["Image"] == "nginx:alpine"
    assert "removido: kind_gould" in r.stdout and "nginx:alpine segue no disco" in r.stdout


def test_conteiner_de_stack_recusa_com_4_e_aponta_o_down(cena):
    cena.conteiner("motor-pg", projeto="motor")
    for args in (("remover", "motor-pg"), ("remover", "motor-pg", "--ver")):
        r = cena.roda(*args)
        assert r.returncode == 4, r.stdout + r.stderr
        assert "stack compose 'motor'" in r.stderr and "infra down" in r.stderr
    assert cena.vivos() == ["motor-pg"] and cena.rastro() == []


def test_sem_identidade_nao_remove(cena):
    cena.conteiner("kind_gould")
    r = cena.roda("remover", "kind_gould", sujeito=None)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "PF_SUJEITO" in r.stderr
    assert cena.vivos() == ["kind_gould"] and cena.rastro() == []


# --- unit transitória ------------------------------------------------------------------------

JOB = "platafirma-job-gate-6b61e97-20261019T111355.service"


def test_transitoria_falhada_sai_da_lista(cena):
    r = cena.roda("remover", JOB, STUB_UNITS=JOB, STUB_TRANSIENT="yes", STUB_ATIVO="failed")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cena.rastro() == [f"reset-failed {JOB}"]
    assert "infra logs" in r.stdout


def test_transitoria_rodando_recusa(cena):
    r = cena.roda("remover", JOB, STUB_UNITS=JOB, STUB_TRANSIENT="yes", STUB_ATIVO="active")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "sessao longjob stop" in r.stderr and cena.rastro() == []


# --- unit da conta ---------------------------------------------------------------------------

def test_unit_da_conta_nao_declarada_vai_para_a_quarentena(cena):
    arq = cena.units / "jaiminho-server.service"
    arq.write_text("[Service]\nExecStart=/bin/true\n")
    (cena.units / "jaiminho-server.service.d").mkdir()
    r = cena.roda("remover", "jaiminho-server", STUB_UNITS="jaiminho-server.service",
                  STUB_FRAG=str(arq), STUB_ATIVO="active")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not arq.exists()
    levas = list((cena.inst / "quarentena").glob("*-infra-remover"))
    assert len(levas) == 1
    assert (levas[0] / "jaiminho-server.service").exists()
    assert (levas[0] / "jaiminho-server.service.d").is_dir()
    assert cena.rastro()[:2] == ["stop jaiminho-server.service", "disable jaiminho-server.service"]
    assert any(linha.startswith("daemon-reload") for linha in cena.rastro())


def test_unit_declarada_recusa_e_nomeia_onde(cena):
    arq = cena.units / "sinal.service"
    arq.write_text("[Service]\n")
    r = cena.roda("remover", "sinal", STUB_UNITS="sinal.service", STUB_FRAG=str(arq))
    assert r.returncode == 4, r.stdout + r.stderr
    assert "units-da-instancia.json" in r.stderr
    assert arq.exists() and cena.rastro() == []


def test_unit_fora_da_conta_recusa(cena):
    r = cena.roda("remover", "xdg-desktop-portal", STUB_UNITS="xdg-desktop-portal.service",
                  STUB_FRAG="/usr/lib/systemd/user/xdg-desktop-portal.service")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "não da conta" in r.stderr and cena.rastro() == []


def test_a_porta_nao_sai(cena):
    arq = cena.units / "ops-mcp.service"
    arq.write_text("[Service]\n")
    r = cena.roda("remover", "ops-mcp", STUB_UNITS="ops-mcp.service", STUB_FRAG=str(arq))
    assert r.returncode == 4, r.stdout + r.stderr
    assert arq.exists() and cena.rastro() == []


def test_alvo_inexistente_sai_1(cena):
    r = cena.roda("remover", "nao-existe")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "nada removido" in r.stderr


def test_sem_alvo_e_dois_alvos_saem_2(cena):
    assert cena.roda("remover").returncode == 2
    assert cena.roda("remover", "a", "b").returncode == 2
    assert cena.rastro() == []


# --- limpeza jobs ----------------------------------------------------------------------------

VELHO = "platafirma-job-gate-282131d-20200101T000000.service"
NOVO = "platafirma-job-gate-aaaaaaa-20990101T000000.service"
SEM = "platafirma-job-sem-carimbo.service"


def _falhadas(cena):
    (cena.dir / "falhadas").write_text(
        "".join(f"{u} loaded failed failed descricao\n" for u in (VELHO, NOVO, SEM)))


def test_limpeza_jobs_ver_lista_e_nao_toca(cena):
    _falhadas(cena)
    r = cena.roda("limpeza", "jobs", "--ver")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"sairia: {VELHO}" in r.stdout and f"fica: {NOVO}" in r.stdout and f"fica: {SEM}" in r.stdout
    assert cena.rastro() == []
    assert not (cena.inst / "var" / "log" / "poda.log").exists()


def test_limpeza_jobs_tira_so_os_velhos_e_anota(cena):
    _falhadas(cena)
    r = cena.roda("limpeza", "jobs")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cena.rastro() == [f"reset-failed {VELHO}"]
    assert "1 saíram, 1 ficam" in r.stdout
    assert "limpeza-jobs: 1 saíram" in (cena.inst / "var" / "log" / "poda.log").read_text()


def test_limpeza_jobs_dias_zero_tira_todo_carimbado(cena):
    _falhadas(cena)
    r = cena.roda("limpeza", "jobs", "--dias", "0")
    assert r.returncode == 0, r.stdout + r.stderr
    # o do futuro tem idade negativa: fica mesmo com janela zero; sem carimbo nunca sai
    assert cena.rastro() == [f"reset-failed {VELHO}"]


def test_limpeza_jobs_dias_invalido_sai_2(cena):
    r = cena.roda("limpeza", "jobs", "--dias", "sete")
    assert r.returncode == 2 and cena.rastro() == []


# --- cabeçalho e usage -----------------------------------------------------------------------

def test_o_ato_esta_no_cabecalho_com_o_par_de_restart_e_na_usage():
    cab = INFRA.read_text(encoding="utf-8").splitlines()[:30]
    atos = next(linha for linha in cab if linha.startswith("# atos:"))
    assert "remover (escrita, operacao)" in atos and "restart (escrita, operacao)" in atos
    assert any(linha.startswith("# escreve:") and "remover=" in linha for linha in cab)
    r = subprocess.run([BASH, str(INFRA), "--ajuda"], capture_output=True, text=True, timeout=30,
                       check=False)
    assert r.returncode == 2
    assert "infra remover  <alvo> [--ver]" in r.stderr and "logs|quarentena|jobs" in r.stderr
