"""O isolamento do conftest está de pé: a suíte não enxerga estado real.

Se este arquivo fica vermelho, o conftest deixou de carregar ou alguém reabriu uma
porta para o mundo real, e todo o resto da suíte volta a poder passar por sorte.
"""
import os
import shutil
import subprocess

REAIS = ("/srv/platafirma", "/opt/platafirma", os.path.expanduser("~/AI"),
         os.path.expanduser("~/.config/platafirma"))


def test_raizes_apontam_para_temporario():
    for var in ("PLATAFIRMA_INSTANCIA", "PF_RELEASE_RAIZ", "PLATAFIRMA_RELEASE",
                "PLATAFIRMA_BANCADA", "PLATAFIRMA_ARQUIVO_BANCADA", "PF_ABERTURA_DIR"):
        valor = os.environ.get(var, "")
        assert valor, f"{var} ausente: o codigo cairia no default real"
        assert not valor.startswith(REAIS), f"{var}={valor} aponta estado real"


def test_sessao_e_cadeira_da_conta_nao_vazam():
    for var in ("PF_SESSAO", "PF_SESSAO_ID", "PF_CADEIRA", "PF_FITA", "PF_ORDEM_ID"):
        assert var not in os.environ, f"{var} herdado da conta que roda a suite"


def test_servicos_apontam_para_porta_morta():
    for var in ("RAG_API_URL", "MOTOR_ACERVO_URL", "TAREFAS_BASE", "MW_API_URL"):
        assert ":9" in os.environ[var], f"{var}={os.environ[var]}"
    for var in ("MEM_REDIS_PORT", "FILA_REDIS_PORT", "SESSAO_PG_PORT"):
        assert os.environ[var] == "9"


def test_programas_do_mundo_real_sao_delatores():
    for prog in ("docker", "gh", "systemctl", "psql", "redis-cli"):
        caminho = shutil.which(prog)
        assert caminho and "delatores" in caminho, f"{prog} resolve para {caminho}"
    r = subprocess.run(["gh", "pr", "list"], capture_output=True, text=True)
    assert r.returncode == 97
    assert "sem stub" in r.stderr
