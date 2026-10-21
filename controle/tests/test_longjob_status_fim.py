"""`sessao longjob status` de uma unit que já saiu lê o evento de fim, e nunca success (spec eixos-do-host R13; card #3920).

O `systemctl show` de unit descarregada devolve os valores padrão do systemd: Result=success e ExecMainStatus=0. Sem o
evento, um job que falhou leria verde depois que a limpeza de fóssil o tirasse da lista (medido no #3100). O evento é a
linha `# fim=<ts> result=<Result> status=<ExecMainStatus>` que a limpeza grava no log do job antes do reset-failed.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

LONGJOB = Path(__file__).resolve().parents[2] / "bin" / "_sessao" / "longjob"
BASH = shutil.which("bash")
UNIT = "platafirma-job-gate-6b61e97-20261019T111355"

pytestmark = pytest.mark.skipif(BASH is None, reason="sem bash no PATH")

# systemctl de mentira. Unit carregada: devolve o que o job teve. Unit descarregada (FAKE_CARGA=not-found): devolve os
# valores padrão do systemd, que é justamente a armadilha.
SYSTEMCTL = r"""#!/usr/bin/env bash
[ "$1" = "--user" ] && shift
[ "$1" = "show" ] || exit 2
shift
unit="$1"
case "$*" in
  *LoadState*) echo "${FAKE_CARGA:-loaded}" ;;
  *)
    if [ "${FAKE_CARGA:-loaded}" = "not-found" ]; then
      printf 'Id=%s\nSubState=dead\nResult=success\nExecMainPID=0\nExecMainStatus=0\n' "$unit"
    else
      printf 'Id=%s\nSubState=failed\nResult=exit-code\nExecMainPID=123\nExecMainStatus=3\n' "$unit"
    fi ;;
esac
"""


@pytest.fixture
def cena(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    f = bindir / "systemctl"
    f.write_text(SYSTEMCTL)
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    logs = tmp_path / "jobs"
    logs.mkdir()

    def status(unit=UNIT, carga="loaded"):
        env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "LONGJOB_LOGDIR": str(logs),
               "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"), "FAKE_CARGA": carga}
        return subprocess.run([BASH, str(LONGJOB), "status", unit], capture_output=True, text=True, env=env,
                              timeout=30, check=False)

    status.logs = logs
    return status


def test_unit_coletada_com_evento_de_fim_le_falho_e_o_codigo_do_job(cena):
    (cena.logs / f"{UNIT}.log").write_text(
        "# unit=x\n# inicio=2026-10-19T11:13:55-03:00\nsaida do job\n# fim=2026-10-21T04:50:01-03:00 result=exit-code status=3\n")
    r = cena(carga="not-found")
    assert r.returncode == 0, r.stderr
    assert "Result=exit-code" in r.stdout and "ExecMainStatus=3" in r.stdout
    assert "Result=success" not in r.stdout, "a unit descarregada leria verde, e o job falhou"
    assert "LoadState=not-found (coletada)" in r.stdout and "Fim=2026-10-21T04:50:01-03:00" in r.stdout


def test_unit_coletada_sem_evento_diz_que_nao_sabe_e_nunca_success(cena):
    (cena.logs / f"{UNIT}.log").write_text("# unit=x\nsaida do job\n")
    r = cena(carga="not-found")
    assert "Result=desconhecido" in r.stdout and "ExecMainStatus=desconhecido" in r.stdout
    assert "Result=success" not in r.stdout and "sem evento de fim" in r.stdout


def test_unit_coletada_sem_log_nenhum_tambem_nao_le_verde(cena):
    r = cena(carga="not-found")
    assert "Result=success" not in r.stdout and "Result=desconhecido" in r.stdout and "(sem log)" in r.stdout


def test_o_evento_vale_pelo_ultimo_fim_do_log(cena):
    (cena.logs / f"{UNIT}.log").write_text(
        "# fim=2026-10-20T04:50:01-03:00 result=timeout status=124\n# fim=2026-10-21T04:50:01-03:00 result=signal status=9\n")
    assert "Result=signal" in cena(carga="not-found").stdout


def test_unit_ainda_carregada_mostra_o_que_a_unit_diz_como_antes(cena):
    r = cena(carga="loaded")
    assert "Result=exit-code" in r.stdout and "ExecMainStatus=3" in r.stdout
    assert "coletada" not in r.stdout


def test_o_nome_com_ponto_service_acha_o_mesmo_log(cena):
    (cena.logs / f"{UNIT}.log").write_text("# fim=2026-10-21T04:50:01-03:00 result=exit-code status=3\n")
    r = cena(unit=f"{UNIT}.service", carga="not-found")
    assert "Result=exit-code" in r.stdout and "ExecMainStatus=3" in r.stdout


def test_o_rabo_do_log_continua_saindo(cena):
    (cena.logs / f"{UNIT}.log").write_text("linha 1\n# fim=2026-10-21T04:50:01-03:00 result=exit-code status=3\n")
    r = cena(carga="not-found")
    assert "--- log ---" in r.stdout and "linha 1" in r.stdout
