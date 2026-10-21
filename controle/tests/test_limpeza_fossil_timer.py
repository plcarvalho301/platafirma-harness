"""O timer diário da limpeza de fóssil (spec eixos-do-host R14; card #3920): roda sozinha, sem passo de aprovação, e só existe
com o teste da limpeza no portão. O `infra estado` o mostra depois do `deploy-harness/instalar`.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DEPLOY = RAIZ / "deploy-harness"


def _servico() -> str:
    return (DEPLOY / "limpeza-fossil.service").read_text(encoding="utf-8")


def _timer() -> str:
    return (DEPLOY / "limpeza-fossil.timer").read_text(encoding="utf-8")


def test_o_service_roda_a_limpeza_de_fossil_da_release_sem_ver_e_sem_aprovacao():
    servico = _servico()
    execs = re.findall(r"^ExecStart=(.*)$", servico, re.MULTILINE)
    assert execs == ["/opt/platafirma/current/harness/bin/infra limpeza fossil"], "uma linha, sem --ver"
    assert "Type=oneshot" in servico and "WorkingDirectory=/opt/platafirma/current/harness" in servico
    assert "--ver" not in "\n".join(execs) and "PF_APROVACAO" not in servico, "sem passo de aprovação (R14)"


def test_a_recusa_por_job_ativo_nao_falha_a_unit_mas_o_alvo_que_nao_saiu_falha():
    status = re.findall(r"^SuccessExitStatus=(.*)$", _servico(), re.MULTILINE)
    assert status == ["0 4"], "4 é a recusa da limpeza (resposta); 1 e 5 falham a unit e aparecem em `release conferir jobs`"


def test_o_timer_e_diario_pega_a_execucao_perdida_e_entra_no_timers_target():
    timer = _timer()
    assert re.search(r"^OnCalendar=\*-\*-\* \d\d:\d\d:00$", timer, re.MULTILINE)
    assert "Persistent=true" in timer and "WantedBy=timers.target" in timer


def test_o_timer_roda_depois_do_cron_do_core_que_chama_o_mesmo_fossil():
    # O cron do core chama `infra limpeza jobs --dias 1` às 04:25; as duas passam pelo mesmo flock e a segunda não acha nada.
    hora = re.search(r"^OnCalendar=\*-\*-\* (\d\d):(\d\d):00$", _timer(), re.MULTILINE)
    assert (int(hora.group(1)), int(hora.group(2))) > (4, 25)


def test_o_instalar_converge_o_service_como_alvo_de_timer_e_o_timer_como_habilitado_depois_do_corte():
    instalar = (DEPLOY / "instalar").read_text(encoding="utf-8")
    lista = re.findall(r'"deploy-harness/([a-z-]+\.(?:service|timer))\|', instalar)
    assert lista.index("limpeza-fossil.service") > lista.index("corte-bruto.timer")
    assert '"deploy-harness/limpeza-fossil.service|alvo-de-timer"' in instalar
    assert '"deploy-harness/limpeza-fossil.timer|habilita"' in instalar


def test_o_timer_so_existe_com_o_teste_da_limpeza_no_portao():
    """R14: o teste do R12 está no portão (a lista VERDES) antes de o timer existir."""
    verdes = (RAIZ / "controle" / "tests" / "VERDES").read_text(encoding="utf-8")
    linhas = [linha for linha in verdes.splitlines() if linha.startswith("tests/test_infra_limpeza_fossil.py ")]
    assert len(linhas) == 1 and "bin/_infra/**" in linhas[0]
    assert (RAIZ / "controle" / "tests" / "test_infra_limpeza_fossil.py").is_file()


def test_o_service_nao_e_habilitado_sozinho_so_o_timer_dispara():
    assert "[Install]" not in _servico(), "service de timer não se habilita: roda só quando o timer o chama"
