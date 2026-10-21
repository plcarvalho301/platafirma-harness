"""`infra limpeza fossil` (bin/_infra/limpeza-fossil): o critério positivo, a recusa com job ativo, o evento antes do
expurgo e o que se guarda antes do rm (spec eixos-do-host R12 a R14; card #3920; comentário #3102 do #3878).

Roda o bin/infra de verdade, com `docker` e `systemctl` falsos à frente do PATH: nada toca o host. O teste monta os seis
alvos do comentário da engenharia: (a) contêiner com label de compose, (b) contêiner sem label com mais de 24 h, (c) sem
label com menos de 24 h, (d) unit platafirma-job-* failed e transiente, (e) unit do bot failed, (f) xdg-desktop-portal
failed. A limpeza tira só (b) e (d), escreve uma linha de marca para cada um e guarda o `docker logs` e o `docker inspect`
do (b) antes do rm.
"""
import fcntl
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("python3") is None, reason="sem bash ou python3 no PATH")

DOCKER = r"""#!/usr/bin/env bash
vivos="$STUB_DIR/conteineres"
cmd="$1"; shift
case "$cmd" in
  ps)
    [ -z "${FAKE_PS_FALHA:-}" ] || { echo "Cannot connect to the Docker daemon" >&2; exit 1; }
    cat "$vivos" 2>/dev/null ;;
  inspect)
    if [ -n "${FAKE_CINTO:-}" ] && [ "$#" -eq 1 ] && [ -f "$STUB_DIR/inspect-cinto-$1.json" ]; then
      cat "$STUB_DIR/inspect-cinto-$1.json"; exit 0
    fi
    out="["; sep=""
    for alvo in "$@"; do
      f="$STUB_DIR/inspect-$alvo.json"
      [ -f "$f" ] || { echo "Error: No such object: $alvo" >&2; exit 1; }
      out="$out$sep$(cat "$f")"; sep=","
    done
    echo "$out]" ;;
  logs)
    [ -z "${FAKE_LOGS_FALHA:-}" ] || { echo "logs: erro" >&2; exit 1; }
    nome="${@: -1}"
    echo "log do $nome"; echo "linha de erro do $nome" >&2 ;;
  rm)
    nome="${@: -1}"
    echo "rm $nome" >> "$STUB_DIR/rastro"
    grep -vx "id-$nome" "$vivos" > "$vivos.novo" || true; mv "$vivos.novo" "$vivos"
    rm -f "$STUB_DIR/inspect-$nome.json" "$STUB_DIR/inspect-id-$nome.json" ;;
  *) echo "docker-stub: nao coberto: $cmd $*" >&2; exit 1 ;;
esac
"""

# systemctl de mentira. O reset-failed anota se o evento de fim já estava no log do job NAQUELE instante.
SYSTEMCTL = r"""#!/usr/bin/env bash
[ "$1" = "--user" ] && shift
cmd="$1"; shift
case "$cmd" in
  list-units)
    [ -z "${FAKE_LISTA_FALHA:-}" ] || { echo "Failed to connect to bus" >&2; exit 1; }
    estado=""
    for a in "$@"; do case "$a" in --state=*) estado="${a#--state=}" ;; esac; done
    cat "$STUB_DIR/units-$estado" 2>/dev/null; exit 0 ;;
  show)
    u="${@: -1}"
    case "$*" in
      *Transient*) if grep -qx "$u" "$STUB_DIR/transientes" 2>/dev/null; then echo yes; else echo no; fi ;;
      *Result*) cat "$STUB_DIR/resultado-$u" 2>/dev/null || exit 1 ;;
      *) exit 1 ;;
    esac ;;
  reset-failed)
    u="${@: -1}"
    log="$LONGJOB_LOGDIR/${u%.service}.log"
    if grep -q '^# fim=' "$log" 2>/dev/null; then ev=sim; else ev=nao; fi
    echo "reset-failed $u evento_antes=$ev" >> "$STUB_DIR/rastro"
    [ -z "${FAKE_RESET_FALHA:-}" ] || exit 1
    awk -v u="$u" '$1 != u' "$STUB_DIR/units-failed" > "$STUB_DIR/units-failed.novo"; mv "$STUB_DIR/units-failed.novo" "$STUB_DIR/units-failed" ;;
  *) echo "systemctl-stub: nao coberto: $cmd $*" >&2; exit 1 ;;
esac
"""

JOB = "platafirma-job-gate-6b61e97-20200101T000000.service"          # (d) failed e transiente
JOB_DE_FUTURO = "platafirma-job-portao-ui-20990101T000000.service"   # failed, mas com data de amanhã
BOT = "bot-agente-diario.service"                                    # (e)
PORTAL = "xdg-desktop-portal.service"                                # (f)


def _iso_ha(horas: float) -> str:
    quando = datetime.now(timezone.utc) - timedelta(hours=horas)
    return quando.strftime("%Y-%m-%dT%H:%M:%S.%f") + "789Z"


class Cena:
    def __init__(self, tmp_path: Path) -> None:
        self.dir = tmp_path / "stub"
        self.bin = tmp_path / "bin"
        self.inst = tmp_path / "instancia"
        self.logs = self.inst / "var" / "log" / "jobs"
        self.removidos = self.inst / "removidos"
        for p in (self.dir, self.bin, self.inst, self.logs):
            p.mkdir(parents=True)
        for nome, corpo in (("docker", DOCKER), ("systemctl", SYSTEMCTL)):
            f = self.bin / nome
            f.write_text(corpo)
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        for vazio in ("rastro", "conteineres", "units-failed", "units-active", "units-activating", "transientes"):
            (self.dir / vazio).write_text("")

    def conteiner(self, nome: str, projeto: str | None = None, horas: float = 72, imagem: str = "nginx:alpine") -> None:
        labels = {"com.docker.compose.project": projeto} if projeto else {}
        base = {"Id": f"id-{nome}", "Name": "/" + nome, "Created": _iso_ha(horas), "State": {"Status": "running"},
                "Config": {"Image": imagem, "Labels": labels}}
        for chave in (f"id-{nome}", nome):
            (self.dir / f"inspect-{chave}.json").write_text(json.dumps(base))
        with (self.dir / "conteineres").open("a") as f:
            f.write(f"id-{nome}\n")

    def com_label_agora(self, nome: str) -> None:
        """O que `docker inspect <nome>` devolve no cinto: o contêiner passou a ter label entre a lista e o rm."""
        veio = json.loads((self.dir / f"inspect-{nome}.json").read_text())
        veio["Config"]["Labels"] = {"com.docker.compose.project": "recriado"}
        (self.dir / f"inspect-cinto-{nome}.json").write_text(json.dumps([veio]))

    def unit_falha(self, unit: str, transiente: bool = True, resultado: tuple[str, str] | None = ("exit-code", "1")) -> None:
        with (self.dir / "units-failed").open("a") as f:
            f.write(f"{unit} loaded failed failed descricao\n")
        if transiente:
            with (self.dir / "transientes").open("a") as f:
                f.write(unit + "\n")
        if resultado:
            (self.dir / f"resultado-{unit}").write_text(f"Result={resultado[0]}\nExecMainStatus={resultado[1]}\n")

    def job_ativo(self, unit: str = "platafirma-job-prova-20261021T040000.service") -> str:
        (self.dir / "units-active").write_text(f"{unit} loaded active running descricao\n")
        return unit

    def seis_alvos(self) -> None:
        self.conteiner("core-keycloak-1", projeto="platafirma-core")        # (a)
        self.conteiner("kind_gould")                                       # (b)
        self.conteiner("pf-prova-nginx", horas=2)                          # (c)
        self.unit_falha(JOB)                                               # (d)
        self.unit_falha(BOT, transiente=False)                             # (e)
        self.unit_falha(PORTAL, transiente=False)                          # (f)

    def vivos(self) -> list[str]:
        return (self.dir / "conteineres").read_text().split()

    def falhas(self) -> list[str]:
        return [linha.split()[0] for linha in (self.dir / "units-failed").read_text().splitlines()]

    def rastro(self) -> list[str]:
        return (self.dir / "rastro").read_text().splitlines()

    def marca(self) -> str:
        arq = self.inst / "var" / "log" / "poda.log"
        return arq.read_text() if arq.exists() else ""

    def roda(self, *args: str, **env: str):
        e = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "STUB_DIR": str(self.dir),
             "PLATAFIRMA_INSTANCIA": str(self.inst), "LONGJOB_LOGDIR": str(self.logs),
             "INFRA_REMOVIDOS": str(self.removidos)}
        e.pop("PF_SUJEITO", None)
        e.update(env)
        return subprocess.run([BASH, str(INFRA), "limpeza", *args], capture_output=True, text=True, env=e,
                              timeout=60, check=False)


@pytest.fixture
def cena(tmp_path):
    return Cena(tmp_path)


# --- os seis alvos: tira dois, deixa quatro --------------------------------------------------------

def test_o_duble_tira_os_dois_fosseis_e_deixa_os_quatro_vivos(cena):
    cena.seis_alvos()
    r = cena.roda("fossil")
    assert r.returncode == 0, r.stdout + r.stderr
    assert cena.vivos() == ["id-core-keycloak-1", "id-pf-prova-nginx"], "(a) e (c) seguem de pé"
    assert cena.falhas() == [BOT, PORTAL], "(e) e (f) seguem em failed"
    assert [linha.split(" evento_antes")[0] for linha in cena.rastro()] == [f"reset-failed {JOB}", "rm kind_gould"]
    assert "saiu: kind_gould" in r.stdout and f"saiu: {JOB}" in r.stdout
    for fica in ("core-keycloak-1", "pf-prova-nginx", BOT, PORTAL):
        assert f"fica: {fica}" in r.stdout


def test_uma_linha_de_marca_por_alvo_tirado(cena):
    cena.seis_alvos()
    cena.roda("fossil")
    marca = cena.marca()
    assert "saiu contêiner kind_gould" in marca and f"saiu unit {JOB} result=exit-code status=1" in marca
    assert "limpeza-fossil: 2 saíram, 4 ficam" in marca
    assert "core-keycloak-1" not in marca and BOT not in marca


def test_ver_lista_o_que_tiraria_e_nao_toca_em_nada(cena):
    cena.seis_alvos()
    r = cena.roda("fossil", "--ver")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sairia: kind_gould" in r.stdout and f"sairia: {JOB}" in r.stdout
    assert "limpeza-fossil: 2 sairiam, 4 ficam" in r.stdout
    assert cena.rastro() == [] and len(cena.vivos()) == 3 and len(cena.falhas()) == 3
    assert cena.marca() == "" and not cena.removidos.exists() and list(cena.logs.iterdir()) == []


def test_o_critico_e_positivo_o_nome_do_conteiner_nao_conta(cena):
    # acervo-api, conversor-2, motor-pg e searxng não seguem o molde projeto-serviço-n, mas têm o label de projeto
    for nome in ("acervo-api", "conversor-2", "motor-pg", "searxng"):
        cena.conteiner(nome, projeto="acervo")
    cena.conteiner("hash_aleatorio_12")
    r = cena.roda("fossil")
    assert r.returncode == 0 and cena.rastro() == ["rm hash_aleatorio_12"]
    assert len(cena.vivos()) == 4


def test_a_idade_minima_se_ajusta_pelo_ambiente(cena):
    cena.conteiner("pf-prova-nginx", horas=2)
    assert cena.roda("fossil").returncode == 0 and cena.vivos() == ["id-pf-prova-nginx"]
    r = cena.roda("fossil", INFRA_FOSSIL_IDADE_H="1")
    assert r.returncode == 0 and cena.vivos() == [] and cena.rastro() == ["rm pf-prova-nginx"]


# --- recusa com job da sessão ativo ----------------------------------------------------------------

def test_com_job_da_sessao_ativo_a_rodada_recusa_e_diz_quais(cena):
    cena.seis_alvos()
    ativo = cena.job_ativo()
    r = cena.roda("fossil")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "RECUSADO: job da sessão ativo" in r.stderr and ativo in r.stderr
    assert cena.rastro() == [] and len(cena.vivos()) == 3 and len(cena.falhas()) == 3
    assert "RECUSADO: job da sessão ativo" in cena.marca(), "a recusa fica na marca, para a observação ver"


def test_ver_com_job_ativo_diz_que_recusaria_mas_lista(cena):
    cena.seis_alvos()
    cena.job_ativo()
    r = cena.roda("fossil", "--ver")
    assert r.returncode == 0 and "recusaria: job da sessão ativo" in r.stdout and "sairia: kind_gould" in r.stdout
    assert cena.rastro() == []


def test_unit_ativa_que_nao_e_job_da_sessao_nao_recusa(cena):
    cena.seis_alvos()
    (cena.dir / "units-active").write_text("ops-mcp.service loaded active running porta\n")
    assert cena.roda("fossil").returncode == 0 and len(cena.rastro()) == 2


# --- o evento antes do expurgo (R13) ---------------------------------------------------------------

def test_o_evento_de_fim_ja_esta_no_log_do_job_quando_o_reset_failed_roda(cena):
    cena.unit_falha(JOB, resultado=("signal", "9"))
    assert cena.roda("fossil").returncode == 0
    assert cena.rastro() == [f"reset-failed {JOB} evento_antes=sim"]
    log = (cena.logs / (JOB.removesuffix(".service") + ".log")).read_text()
    assert log.startswith("# fim=") and log.rstrip().endswith("result=signal status=9")


def test_sem_conseguir_gravar_o_evento_a_unit_nao_sai(cena, tmp_path):
    cena.unit_falha(JOB)
    arquivo = tmp_path / "arquivo-no-lugar-da-pasta"
    arquivo.write_text("")
    r = cena.roda("fossil", LONGJOB_LOGDIR=str(arquivo / "jobs"))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "não gravei o evento de fim" in r.stderr and cena.rastro() == [] and cena.falhas() == [JOB]


def test_unit_que_nao_diz_o_resultado_fica_com_a_unit(cena):
    cena.unit_falha(JOB, resultado=None)
    r = cena.roda("fossil")
    assert r.returncode == 1 and "não disse o resultado" in r.stderr
    assert cena.rastro() == [] and cena.falhas() == [JOB]


def test_reset_failed_recusado_deixa_o_evento_e_a_proxima_rodada_nao_duplica(cena):
    cena.unit_falha(JOB)
    r = cena.roda("fossil", FAKE_RESET_FALHA="1")
    assert r.returncode == 1 and "reset-failed recusado" in r.stderr
    log = cena.logs / (JOB.removesuffix(".service") + ".log")
    assert log.read_text().count("# fim=") == 1
    r = cena.roda("fossil")
    assert r.returncode == 0 and cena.falhas() == [] and log.read_text().count("# fim=") == 1
    assert "evento ja gravado" in r.stdout


def test_o_status_do_job_longo_le_o_evento_que_a_limpeza_gravou(cena):
    cena.unit_falha(JOB, resultado=("exit-code", "7"))
    cena.roda("fossil")
    longjob = INFRA.parent / "_sessao" / "longjob"
    systemctl_coletada = cena.bin / "systemctl"
    systemctl_coletada.write_text(
        '#!/usr/bin/env bash\n[ "$1" = "--user" ] && shift\ncase "$*" in *LoadState*) echo not-found ;; '
        '*) printf "Result=success\\nExecMainStatus=0\\n" ;; esac\n')
    r = subprocess.run([BASH, str(longjob), "status", JOB.removesuffix(".service")], capture_output=True, text=True,
                       env={**os.environ, "PATH": f"{cena.bin}{os.pathsep}{os.environ['PATH']}",
                            "LONGJOB_LOGDIR": str(cena.logs), "PLATAFIRMA_INSTANCIA": str(cena.inst)}, timeout=30)
    assert "Result=exit-code" in r.stdout and "ExecMainStatus=7" in r.stdout and "Result=success" not in r.stdout


# --- logs e inspect guardados antes do rm (R13) ----------------------------------------------------

def test_inspect_e_logs_do_conteiner_ficam_guardados_antes_do_rm(cena):
    cena.conteiner("kind_gould", imagem="nginx:1.29-alpine")
    assert cena.roda("fossil").returncode == 0 and cena.rastro() == ["rm kind_gould"]
    inspecoes = list(cena.removidos.glob("kind_gould-*.json"))
    logs = list(cena.removidos.glob("kind_gould-*.log"))
    assert len(inspecoes) == 1 and len(logs) == 1
    assert json.loads(inspecoes[0].read_text())[0]["Config"]["Image"] == "nginx:1.29-alpine"
    assert "log do kind_gould" in logs[0].read_text() and "linha de erro do kind_gould" in logs[0].read_text()


def test_sem_conseguir_guardar_os_logs_o_conteiner_nao_sai(cena):
    cena.conteiner("kind_gould")
    r = cena.roda("fossil", FAKE_LOGS_FALHA="1")
    assert r.returncode == 1 and "não guardei a inspeção e os logs" in r.stderr
    assert cena.rastro() == [] and cena.vivos() == ["id-kind_gould"]


def test_cinto_contêiner_que_ganhou_label_entre_a_lista_e_o_rm_nao_sai(cena):
    cena.conteiner("kind_gould")
    cena.com_label_agora("kind_gould")
    r = cena.roda("fossil", FAKE_CINTO="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RECUSADO fora do critério: kind_gould" in r.stdout and cena.rastro() == []


# --- só os jobs: o caminho do cron do core -----------------------------------------------------------

def test_jobs_e_o_fossil_so_de_job_e_nao_toca_em_conteiner(cena):
    cena.seis_alvos()
    r = cena.roda("jobs")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [linha.split(" evento_antes")[0] for linha in cena.rastro()] == [f"reset-failed {JOB}"]
    assert len(cena.vivos()) == 3


def test_jobs_nao_recusa_com_job_ativo_porque_nenhum_conteiner_esta_em_jogo(cena):
    cena.seis_alvos()
    cena.job_ativo()
    r = cena.roda("jobs")
    assert r.returncode == 0 and len(cena.rastro()) == 1 and len(cena.vivos()) == 3


def test_dias_so_tira_o_job_com_a_idade_pelo_carimbo_do_nome(cena):
    cena.unit_falha(JOB)
    cena.unit_falha(JOB_DE_FUTURO)
    cena.unit_falha("platafirma-job-sem-carimbo.service")
    r = cena.roda("jobs", "--dias", "1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [linha.split(" evento_antes")[0] for linha in cena.rastro()] == [f"reset-failed {JOB}"]
    assert f"fica: {JOB_DE_FUTURO}" in r.stdout and "fica: platafirma-job-sem-carimbo.service (sem carimbo" in r.stdout


def test_sem_dias_nao_ha_janela_de_idade_job_morto_se_expurga_sempre(cena):
    cena.unit_falha(JOB_DE_FUTURO)
    cena.unit_falha("platafirma-job-sem-carimbo.service")
    assert cena.roda("jobs").returncode == 0 and cena.falhas() == []


def test_unit_do_prefixo_que_nao_e_transiente_fica(cena):
    cena.unit_falha("platafirma-job-fixa.service", transiente=False)
    r = cena.roda("fossil")
    assert r.returncode == 0 and cena.rastro() == [] and "unit não transiente" in r.stdout


# --- fonte muda, trava e uso -----------------------------------------------------------------------

def test_docker_fora_do_ar_sai_5_e_nada_e_limpo(cena):
    cena.seis_alvos()
    r = cena.roda("fossil", FAKE_PS_FALHA="1")
    assert r.returncode == 5 and "docker ps não respondeu" in r.stderr
    assert len(cena.vivos()) == 3


def test_systemd_fora_do_ar_sai_5(cena):
    cena.seis_alvos()
    r = cena.roda("fossil", FAKE_LISTA_FALHA="1")
    assert r.returncode == 5 and "systemctl --user não respondeu" in r.stderr and cena.rastro() == []


def test_outra_rodada_em_curso_nao_tira_nada_duas_vezes(cena):
    cena.seis_alvos()
    trava = cena.inst / "var" / "lock" / "limpeza-fossil.lock"
    trava.parent.mkdir(parents=True)
    with trava.open("w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        r = cena.roda("fossil")
    assert r.returncode == 0 and "outra execução em curso" in r.stdout and cena.rastro() == []


@pytest.mark.parametrize("args", [("fossil", "--dias"), ("fossil", "--dias", "sete"), ("fossil", "--tudo")])
def test_uso_errado_sai_2_sem_tocar_em_nada(cena, args):
    cena.seis_alvos()
    r = cena.roda(*args)
    assert r.returncode == 2 and "uso: infra limpeza fossil" in r.stderr and cena.rastro() == []


def test_idade_minima_ilegivel_sai_2(cena):
    r = cena.roda("fossil", INFRA_FOSSIL_IDADE_H="muito")
    assert r.returncode == 2 and "INFRA_FOSSIL_IDADE_H pede horas" in r.stderr
