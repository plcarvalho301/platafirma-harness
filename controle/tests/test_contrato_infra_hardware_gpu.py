"""`infra hardware` e `infra gpu`: leitura do hardware e da GPU pela porta (03/10/2026).

Nasceram para dimensionar o nobreak do host: modelo de CPU e GPU e consumo em W, sem
pedir ao dono que rode nvidia-smi e lscpu à mão. O nvidia-smi é um stub no PATH;
/proc/cpuinfo, /proc/meminfo e o contador RAPL entram por INFRA_CPUINFO, INFRA_MEMINFO e
INFRA_RAPL, para o teste não depender do host.
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

GPU_HW = "NVIDIA GeForce RTX 4060 Ti, 16380, 18.70, 165.00, 180.00, 550.120"
GPU_VIVO = "0, NVIDIA GeForce RTX 4060 Ti, 37, 1597, 16380, 52, 48.10, 165.00, 1920, P2"
APPS = "00000000:01:00.0, 4242, /usr/bin/python3, 1200"

CPUINFO = "".join(
    f"processor\t: {i}\nmodel name\t: AMD Ryzen 7 5700X 8-Core Processor\n"
    f"physical id\t: 0\ncore id\t\t: {i % 8}\n\n" for i in range(16))
MEMINFO = "MemTotal:       32768000 kB\nMemFree:        1000 kB\n"


def _ambiente(tmp_path, hw_rc=0, apps_rc=0, sem_nvidia=False, rapl=None):
    d = tmp_path / "bin"
    d.mkdir()
    if not sem_nvidia:
        f = d / "nvidia-smi"
        f.write_text(
            "#!/usr/bin/env bash\n"
            'case "$*" in\n'
            f"  *query-compute-apps*) [ {apps_rc} -eq 0 ] && echo '{APPS}'; exit {apps_rc} ;;\n"
            f"  *index,name*) [ {hw_rc} -eq 0 ] && echo '{GPU_VIVO}'; exit {hw_rc} ;;\n"
            f"  *name,memory.total*) [ {hw_rc} -eq 0 ] && echo '{GPU_HW}'; exit {hw_rc} ;;\n"
            "esac\nexit 9\n")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    cpu = tmp_path / "cpuinfo"
    cpu.write_text(CPUINFO)
    mem = tmp_path / "meminfo"
    mem.write_text(MEMINFO)
    if rapl is None:
        rapl_path = tmp_path / "nao-existe"
    else:
        rapl_path = tmp_path / "energy_uj"
        rapl_path.write_text(str(rapl))
    # PATH sem o nvidia-smi do host: um diretório de links para tudo de /usr/bin e /bin,
    # menos ele. O stub, quando existe, entra antes.
    sist = tmp_path / "sist"
    sist.mkdir()
    for raiz in ("/usr/bin", "/bin"):
        if not Path(raiz).is_dir():
            continue
        for nome in os.listdir(raiz):
            alvo = sist / nome
            if nome != "nvidia-smi" and not alvo.exists():
                alvo.symlink_to(Path(raiz) / nome)
    return {**os.environ, "PATH": f"{d}{os.pathsep}{sist}", "INFRA_CPUINFO": str(cpu),
            "INFRA_MEMINFO": str(mem), "INFRA_RAPL": str(rapl_path)}


def _infra(env, *args):
    return subprocess.run([BASH, str(INFRA), *args], capture_output=True, text=True,
                          env=env, timeout=30)


def test_hardware_texto_nomeia_cpu_gpu_e_diz_que_a_fonte_nao_se_le(tmp_path):
    r = _infra(_ambiente(tmp_path), "hardware")
    assert r.returncode == 0, r.stderr
    assert "AMD Ryzen 7 5700X 8-Core Processor · 8 núcleos / 16 threads" in r.stdout
    assert "31.2 GiB" in r.stdout
    assert "NVIDIA GeForce RTX 4060 Ti · 16 GiB · driver 550.120" in r.stdout
    assert "teto configurado: 165 W" in r.stdout and "teto máximo da placa: 180 W" in r.stdout
    assert "etiqueta" in r.stdout
    assert "não legível desta conta" in r.stdout and "soma medida" not in r.stdout


def test_hardware_com_rapl_legivel_soma_cpu_e_gpu(tmp_path):
    r = _infra(_ambiente(tmp_path, rapl=1000000), "hardware", "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["cpu"]["watts"] == 0  # contador parado no stub: 0 W medido, não ausente
    assert d["soma_cpu_gpu_w"] == 19
    assert d["psu"]["legivel"] is False
    assert d["gpus"][0]["teto_max_w"] == 180.0


def test_hardware_json_sem_rapl_deixa_watts_nulo(tmp_path):
    d = json.loads(_infra(_ambiente(tmp_path), "hardware", "--json").stdout)
    assert d["cpu"]["watts"] is None and d["soma_cpu_gpu_w"] is None
    assert d["cpu"]["nucleos"] == 8 and d["cpu"]["threads"] == 16


def test_gpu_texto_mostra_uso_vram_temperatura_watts_e_processo(tmp_path):
    r = _infra(_ambiente(tmp_path), "gpu")
    assert r.returncode == 0, r.stderr
    assert "== GPU 0: NVIDIA GeForce RTX 4060 Ti (P2)" in r.stdout
    assert "uso 37% · VRAM 1597 / 16380 MiB · 52 °C · 48.1 / 165 W · 1920 MHz" in r.stdout
    assert "4242  /usr/bin/python3  1200 MiB" in r.stdout


def test_gpu_sem_lista_de_processos_diz_em_vez_de_calar(tmp_path):
    r = _infra(_ambiente(tmp_path, apps_rc=6), "gpu", "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["processos"] is None and d["processos_motivo"]


def test_sem_nvidia_smi_sai_3(tmp_path):
    env = _ambiente(tmp_path, sem_nvidia=True)
    for ato in ("hardware", "gpu"):
        r = _infra(env, ato)
        assert r.returncode == 3 and "nvidia-smi: ausente" in r.stderr


def test_nvidia_smi_que_falha_sai_5(tmp_path):
    env = _ambiente(tmp_path, hw_rc=9)
    for ato in ("hardware", "gpu"):
        r = _infra(env, ato)
        assert r.returncode == 5 and "nvidia-smi falhou" in r.stderr


def test_argumento_desconhecido_sai_2(tmp_path):
    env = _ambiente(tmp_path)
    for ato in ("hardware", "gpu"):
        assert _infra(env, ato, "--qualquer").returncode == 2
