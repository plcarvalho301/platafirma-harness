"""`infra medir cpu` (bin/_infra/medir-cpu): a carga contra as threads da máquina, a pressão e a carga média do kernel, o
consumo por chave de serviço e o código de saída (spec eixos-do-host R2, R3, R4, R5 e R11; card #3921).

O /proc é uma árvore de mentira com duas fases: a leitura de antes e a de depois da amostra. O `dormir` do teste
avança os contadores de uma fase para a outra, então a amostra é determinística e não espera segundo nenhum.
`docker` e `acervo` ficam à frente do PATH. Nada toca o host.
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[2] / "bin"
MEDIR = BIN / "_infra" / "medir-cpu"
SHA = "e" * 40
ID_DO_EMBEDDER = "a" * 64
THREADS = 4
ESCOPO = "0::/user.slice/user-1001.slice/user@1001.service/app.slice/{unit}"
# pid -> (comm, cgroup, ticks de utime+stime antes, depois)
PROCESSOS = {
    100: ("python", f"0::/user.slice/user-1001.slice/user@1001.service/app.slice/docker-{ID_DO_EMBEDDER}.scope", 1000, 1090),
    150: ("my (odd) name", f"0::/user.slice/user-1001.slice/user@1001.service/app.slice/docker-{ID_DO_EMBEDDER}.scope", 40, 70),
    200: ("python", ESCOPO.format(unit="ops-mcp.service"), 500, 560),
    300: ("python", ESCOPO.format(unit="bench-embedder.service"), 90, 102),
    400: ("claude", "0::/user.slice/user-1001.slice/session-3.scope", 10, 13),
    500: ("parado", ESCOPO.format(unit="ops-mcp.service"), 77, 77),
}
# /proc/stat: user nice system idle iowait irq softirq steal. A amostra soma 400 ticks (4 threads x 100): 250 ocupados.
STAT_ANTES, STAT_DEPOIS = (1000, 0, 500, 8000, 100, 0, 0, 0), (1200, 0, 550, 8150, 100, 0, 0, 0)


def _carregar():
    carregador = importlib.machinery.SourceFileLoader("medir_cpu_bin", str(MEDIR))
    spec = importlib.util.spec_from_loader(carregador.name, carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


medir_cpu = _carregar()
eixos = medir_cpu.eixos


def _script(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


class Mundo:
    """O /proc de mentira e o relógio dele: `avancar()` é o `dormir` do ato."""

    def __init__(self, proc: Path):
        self.proc = proc

    def stat_da_maquina(self, campos):
        linhas = ["cpu  " + " ".join(str(c) for c in campos)]
        linhas += [f"cpu{i} 0 0 0 0 0 0 0 0 0 0" for i in range(THREADS)]
        (self.proc / "stat").write_text("\n".join(linhas) + "\nintr 0\n", encoding="utf-8")

    def processo(self, pid, comm, cgroup, ticks):
        pasta = self.proc / str(pid)
        pasta.mkdir(exist_ok=True)
        (pasta / "stat").write_text(f"{pid} ({comm}) S 1 1 1 0 -1 0 0 0 0 0 {ticks} 0 0 0 20 0 1 0 0 0 0\n", encoding="utf-8")
        (pasta / "cgroup").write_text(cgroup + "\n", encoding="utf-8")
        (pasta / "comm").write_text(comm + "\n", encoding="utf-8")
        (pasta / "cmdline").write_bytes(f"{comm} --pid {pid}".replace(" ", "\0").encode() + b"\0")

    def antes(self):
        self.stat_da_maquina(STAT_ANTES)
        for pid, (comm, cgroup, antes, _) in PROCESSOS.items():
            self.processo(pid, comm, cgroup, antes)
        self.processo(700, "efemero", ESCOPO.format(unit="ops-mcp.service"), 5)      # some durante a amostra

    def avancar(self, _espera=None):
        self.stat_da_maquina(STAT_DEPOIS)
        for pid, (comm, cgroup, _, depois) in PROCESSOS.items():
            self.processo(pid, comm, cgroup, depois)
        shutil.rmtree(self.proc / "700")
        self.processo(800, "novato", ESCOPO.format(unit="ops-mcp.service"), 400)     # nasce durante a amostra


def _mundo(tmp_path, monkeypatch, *, acervo_quebrado=False, psi=True):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    proc = tmp_path / "proc"
    (proc / "pressure").mkdir(parents=True)
    mundo = Mundo(proc)
    mundo.antes()
    if psi:
        (proc / "pressure" / "cpu").write_text(
            "some avg10=1.50 avg60=0.80 avg300=0.40 total=123456\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
            encoding="utf-8")
    (proc / "loadavg").write_text("0.52 0.40 0.30 1/200 1234\n", encoding="utf-8")
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text("".join(f"processor\t: {i}\nmodel name\t: x\n\n" for i in range(THREADS)), encoding="utf-8")
    labels = {"com.docker.compose.project": "platafirma-busca", "com.docker.compose.service": "embedder",
              "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-busca/{SHA}/docker-compose.yml"}
    _script(bindir / "docker", f"""
for ultimo; do :; done
[ "$ultimo" = "{ID_DO_EMBEDDER}" ] || {{ echo "No such object" >&2; exit 1; }}
printf '/platafirma-busca-embedder-1\\t%s\\n' '{json.dumps(labels)}'
""")
    topologia = [{"slug": "busca", "compose": "/opt/platafirma/current/busca/docker-compose.yml"}]
    corpo_acervo = 'echo "acervo stack: psql falhou" >&2; exit 3\n' if acervo_quebrado else (
        'if [ "$1 $2" = "stack ver" ]; then\n'
        f"  echo '{json.dumps(topologia)}'; exit 0\nfi\n"
        'if [ "$1 $2" = "stack resolver" ]; then\n'
        '  [ "$3" = "ops-mcp.service" ] && { echo "harness/ops-mcp"; exit 0; }\n'
        '  echo "unit_sem_stack: $3" >&2; exit 1\nfi\nexit 2\n')
    acervo = _script(bindir / "acervo", corpo_acervo)
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("INFRA_PROC", str(proc))
    monkeypatch.setenv("INFRA_CPUINFO", str(cpuinfo))
    monkeypatch.setenv("INFRA_ACERVO", str(acervo))
    monkeypatch.setenv("INFRA_CPU_AMOSTRA", "1")
    return mundo


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    return _mundo(tmp_path, monkeypatch)


def medir(mundo):
    return medir_cpu.medir(dormir=mundo.avancar)


def por_chave(j):
    return {c.get("servico") or c["desvio"]: c for c in j["consumidores"]}


# --- a carga, o teto e a pressão ----------------------------------------------------------------

def test_a_carga_vem_em_threads_contra_as_threads_da_maquina_com_a_fonte(mundo, tmp_path):
    j = medir(mundo)
    assert j["estado_leitura"] == "lida" and j["eixo"] == "cpu"
    assert (j["unidade"], j["teto"]) == ("threads", THREADS)
    assert j["valor"] == pytest.approx(2.5), "250 de 400 ticks ocupados em 4 threads"
    assert "processor" in j["teto_fonte"] and str(tmp_path) in j["teto_fonte"], "o teto sai da máquina, com a fonte"
    assert j["janela"] == 1.0 and eixos.validar(j) == []


def test_pressao_do_kernel_e_carga_media_vem_ao_lado_do_numero(mundo):
    j = medir(mundo)
    assert (j["pressao_avg10"], j["pressao_avg60"], j["pressao_avg300"]) == (1.5, 0.8, 0.4)
    assert (j["carga_media_1"], j["carga_media_5"], j["carga_media_15"]) == (0.52, 0.4, 0.3)
    frase = eixos.frase(j)
    assert "2,5 threads de 4 threads" in frase
    assert "pressão do kernel 1,5/0,8/0,4% em 10, 60 e 300 s" in frase and "carga média 0,52/0,4/0,3" in frase


# --- quem consome (R4) --------------------------------------------------------------------------

def test_o_consumo_soma_os_processos_de_cada_chave_e_vem_do_maior_ao_menor(mundo):
    j = medir(mundo)
    chaves = [c.get("servico") or c["desvio"] for c in j["consumidores"]]
    assert chaves == ["busca/embedder", "harness/ops-mcp", "unit_sem_stack", "fora_de_compose_e_unit"]
    c = por_chave(j)
    assert c["busca/embedder"]["valor"] == pytest.approx(1.2) and c["busca/embedder"]["processos"] == 2
    assert c["busca/embedder"]["conteiner"] == "platafirma-busca-embedder-1" and c["busca/embedder"]["pid"] == 100
    assert c["harness/ops-mcp"]["valor"] == pytest.approx(0.6) and c["harness/ops-mcp"]["unit"] == "ops-mcp.service"
    assert all(c["unidade"] == "threads" for c in j["consumidores"])


def test_o_que_nao_resolve_sai_como_desvio_com_pid_e_linha_de_comando_e_nunca_some(mundo):
    c = por_chave(medir(mundo))
    assert c["unit_sem_stack"]["unit"] == "bench-embedder.service" and c["unit_sem_stack"]["pid"] == 300
    assert c["fora_de_compose_e_unit"]["linha_de_comando"] == "claude --pid 400"
    assert "servico" not in c["unit_sem_stack"] and "servico" not in c["fora_de_compose_e_unit"]


def test_processo_parado_nascido_ou_morto_durante_a_amostra_nao_tem_consumo(mundo):
    pids = {c["pid"] for c in medir(mundo)["consumidores"]}
    assert pids.isdisjoint({500, 700, 800}), "sem delta nas duas leituras não há consumo a atribuir"


def test_a_frase_diz_as_threads_de_cada_consumidor(mundo):
    frase = eixos.frase(medir(mundo))
    assert "busca/embedder (1,2 threads)" in frase and "harness/ops-mcp (0,6 threads)" in frase
    assert "sem dono (unit_sem_stack: bench-embedder.service, pid 300" in frase


def test_so_os_mais_pesados_se_resolvem_e_o_resto_vai_em_campo_sem_rotulo_de_total(mundo, monkeypatch):
    monkeypatch.setattr(medir_cpu, "PROCESSOS_RESOLVIDOS", 2)
    j = medir(mundo)
    assert [c.get("servico") for c in j["consumidores"]] == ["busca/embedder", "harness/ops-mcp"]
    assert j["fora_da_lista_threads"] == pytest.approx(0.3 + 0.12 + 0.03)
    assert not [k for k in j if k.startswith(("soma", "total"))] and eixos.validar(j) == []


def test_maquina_ociosa_le_e_nao_tem_consumidor(tmp_path, monkeypatch):
    mundo = _mundo(tmp_path, monkeypatch)
    j = medir_cpu.medir(dormir=lambda _: mundo.stat_da_maquina(STAT_DEPOIS))      # a máquina andou, os processos não
    assert j["estado_leitura"] == "lida" and j["consumidores"] == [] and eixos.validar(j) == []


# --- fonte muda (R3) ----------------------------------------------------------------------------

def test_psi_ausente_sai_nao_consegui_olhar_valor_nulo_e_saida_5(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch, psi=False)
    assert medir_cpu.main(["--json"]) == 5
    j = json.loads(capsys.readouterr().out)
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["valor"] is None
    assert j["causa"] == "psi_ausente" and "pressure/cpu" in j["fonte"] and eixos.validar(j) == []


@pytest.mark.parametrize("apagar,causa", [("stat", "stat_ilegivel"), ("loadavg", "loadavg_ilegivel")])
def test_arquivo_do_kernel_ilegivel_sai_5_com_a_causa(mundo, apagar, causa):
    (mundo.proc / apagar).unlink()
    j = medir(mundo)
    assert (j["estado_leitura"], j["causa"], j["valor"]) == ("nao_consegui_olhar", causa, None)


def test_cpuinfo_ilegivel_sai_5(mundo, monkeypatch, tmp_path):
    monkeypatch.setenv("INFRA_CPUINFO", str(tmp_path / "nao-existe"))
    j = medir(mundo)
    assert (j["estado_leitura"], j["causa"]) == ("nao_consegui_olhar", "ilegivel")


def test_amostra_em_que_o_relogio_da_maquina_nao_andou_sai_5(mundo):
    j = medir_cpu.medir(dormir=lambda _: None)
    assert (j["estado_leitura"], j["causa"], j["valor"]) == ("nao_consegui_olhar", "amostra_vazia", None)


def test_registro_de_stacks_fora_do_ar_nao_vira_desvio_inventado(tmp_path, monkeypatch):
    mundo = _mundo(tmp_path, monkeypatch, acervo_quebrado=True)
    j = medir(mundo)
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["causa"] == "registro_de_stack_indisponivel"
    assert j["valor"] is None and j["consumidores"] == []


# --- medida não reprova -------------------------------------------------------------------------

def test_maquina_saturada_le_e_sai_0(tmp_path, monkeypatch, capsys):
    mundo = _mundo(tmp_path, monkeypatch)
    cheio = (1000, 0, 500, 8000, 100, 0, 0, 0)
    saturado = (1400, 0, 600, 8000, 100, 0, 0, 0)         # 500 ticks na amostra, todos ocupados
    mundo.stat_da_maquina(cheio)
    monkeypatch.setattr(medir_cpu.time, "sleep", lambda _: mundo.stat_da_maquina(saturado))
    assert medir_cpu.main(["--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["valor"] == pytest.approx(THREADS) and j["estado_leitura"] == "lida"


def test_o_schema_recusa_cpu_fora_de_threads_e_consumidor_sem_valor(mundo):
    j = medir(mundo)
    assert eixos.validar({**j, "unidade": "fracao"}) != []
    sem_valor = [{k: v for k, v in c.items() if k != "valor"} for c in j["consumidores"]]
    assert any("threads" in e for e in eixos.validar({**j, "consumidores": sem_valor}))


def test_argumento_desconhecido_sai_2(capsys):
    assert medir_cpu.main(["--ram"]) == 2
    assert "não conhece --ram" in capsys.readouterr().err


def test_a_frase_impressa_e_a_funcao_unica_aplicada_ao_json(mundo, capsys):
    j = medir(mundo)
    assert eixos.imprimir_saida(j, como_json=False) == 0
    assert capsys.readouterr().out.strip() == eixos.frase(j)


def test_pela_linha_de_comando_o_json_sai_valido_e_o_codigo_acompanha(mundo, monkeypatch):
    monkeypatch.setenv("INFRA_CPU_AMOSTRA", "0")      # nada avança no /proc: a amostra vem vazia
    p = subprocess.run([sys.executable, str(MEDIR), "--json"], capture_output=True, text=True, timeout=60)
    j = json.loads(p.stdout)
    assert p.returncode == 5 and j["causa"] == "amostra_vazia" and eixos.validar(j) == []
