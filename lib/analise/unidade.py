"""Sonda dos mecanismos exigidos pela unidade de análise (#4130).

Não recebe credencial nem dado de produção. Uma opção só é candidata quando
o kernel executa a propriedade; declarar a propriedade não prova o isolamento.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

MEMORY_HIGH = 1536 * 1024**2
MEMORY_MAX = 2048 * 1024**2
PRAZO_CALCULO = 600
TASKS_MAX = 64


def bytes_regulares(raiz: Path) -> int:
    """O arquivo temporário do construtor pode sumir entre listar e medir."""
    import stat

    total = 0
    for arquivo in raiz.rglob("*"):
        try:
            meta = arquivo.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISREG(meta.st_mode):
            total += meta.st_size
    return total


def _rodar(argv: list[str]) -> dict:
    try:
        p = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=20,
            close_fds=True,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "XDG_RUNTIME_DIR": os.environ.get(
                    "XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"
                ),
                "DBUS_SESSION_BUS_ADDRESS": os.environ.get(
                    "DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus"
                ),
            },
        )
        return {
            "exit": p.returncode,
            "stdout": p.stdout[-4000:],
            "stderr": p.stderr[-4000:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit": 3, "erro": type(exc).__name__}


def sondar() -> dict:
    """Mede systemd, bwrap e unshare, na ordem fixada no plano."""
    py = "/usr/bin/python3.12"
    codigo = """import json, pathlib, socket
out = {}
for nome, familia in [('inet', socket.AF_INET), ('unix', socket.AF_UNIX)]:
    try:
        s = socket.socket(familia, socket.SOCK_STREAM)
        s.close()
        out[nome] = 'permitido'
    except OSError as exc:
        out[nome] = exc.errno
cg = next(x.split(':',2)[2] for x in pathlib.Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0:'))
raiz = pathlib.Path('/sys/fs/cgroup') / cg.lstrip('/')
for chave in ['memory.high','memory.max','memory.swap.max','pids.max','cpu.max']:
    p = raiz / chave
    out[chave] = p.read_text().strip() if p.exists() else None
print(json.dumps(out))
"""
    unit = "platafirma-analise-sonda-" + uuid.uuid4().hex
    systemd = _rodar(
        [
            "systemd-run",
            "--user",
            "--wait",
            "--pipe",
            "--collect",
            "--unit=" + unit,
            "--property=PrivateNetwork=yes",
            "--property=IPAddressDeny=any",
            "--property=RestrictAddressFamilies=AF_NETLINK",
            "--property=MemoryHigh=1536M",
            "--property=MemoryMax=2048M",
            "--property=MemorySwapMax=0",
            "--property=CPUQuota=200%",
            "--property=TasksMax=64",
            "--property=RuntimeMaxSec=20",
            "--property=KillMode=control-group",
            py,
            "-I",
            "-c",
            codigo,
        ]
    )
    bwrap = (
        _rodar(
            [
                "bwrap",
                "--unshare-user",
                "--unshare-net",
                "--die-with-parent",
                "--ro-bind",
                "/usr",
                "/usr",
                "--symlink",
                "usr/bin",
                "/bin",
                "--symlink",
                "usr/lib",
                "/lib",
                "--symlink",
                "usr/lib64",
                "/lib64",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",
                py,
                "-I",
                "-c",
                "print('namespace-ok')",
            ]
        )
        if shutil.which("bwrap")
        else {"exit": 3, "erro": "bwrap ausente"}
    )
    unshare = (
        _rodar(
            [
                "unshare",
                "--user",
                "--map-root-user",
                "--net",
                py,
                "-I",
                "-c",
                "print('namespace-ok')",
            ]
        )
        if shutil.which("unshare")
        else {"exit": 3, "erro": "unshare ausente"}
    )
    return {"systemd": systemd, "bwrap": bwrap, "unshare": unshare}


def executar(
    comando: list[str],
    *,
    pasta: Path,
    entrada: Path | None = None,
    saida: Path | None = None,
    ambiente: Path | None = None,
    rede: bool = False,
    prazo: float = PRAZO_CALCULO,
    _tetos_memoria: tuple[int, int] | None = None,
) -> tuple[int, dict]:
    """Unidade transiente limitada; bwrap expõe somente arquivos enumerados."""
    import time

    from . import Falha, exigir

    exigir(
        shutil.which("bwrap") and shutil.which("systemd-run"), "isolamento-ausente", 3
    )
    pasta = Path(pasta).resolve()
    saida = Path(saida).resolve()
    unit = "platafirma-analise-" + uuid.uuid4().hex
    memoria_high, memoria_max = _tetos_memoria or (MEMORY_HIGH, MEMORY_MAX)
    props = [
        f"MemoryHigh={memoria_high}",
        f"MemoryMax={memoria_max}",
        "MemorySwapMax=0",
        "CPUQuota=200%",
        "TasksMax=64",
        "RuntimeMaxSec=" + str(prazo),
        "KillMode=control-group",
        "OOMPolicy=kill",
        "TimeoutStopSec=2",
        "NoNewPrivileges=yes",
        "LimitFSIZE=2147483648",
        "UMask=0077",
    ]
    if not rede:
        props += ["PrivateNetwork=yes", "IPAddressDeny=any"]
    else:
        # O construtor não recebe dado nem credencial, e só alcança o índice.
        import socket

        enderecos = set()
        try:
            for host in ("pypi.org", "files.pythonhosted.org"):
                enderecos.update(
                    item[4][0]
                    for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                )
        except OSError:
            raise Falha(3, "indice-fora-do-alcance") from None
        for linha in Path("/etc/resolv.conf").read_text().splitlines():
            if linha.startswith("nameserver "):
                enderecos.add(linha.split()[1])
        props += ["IPAddressDeny=any"]
        props += ["IPAddressAllow=" + endereco for endereco in sorted(enderecos)]
    # Não monta a instância, o home, a release inteira nem o runtime do host.
    bw = [
        "bwrap",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        str(pasta),
        "/receita",
        "--bind",
        str(saida),
        "/saida",
        "--chdir",
        "/receita",
    ]
    if not rede:
        bw += ["--unshare-net"]
    else:
        for x in ("/etc/resolv.conf", "/etc/hosts", "/etc/ssl", "/etc/ld.so.cache"):
            if Path(x).exists():
                bw += ["--ro-bind", x, x]
    if entrada:
        bw += ["--ro-bind", str(Path(entrada).resolve()), "/entrada"]
    if ambiente:
        # O executável do venv precisa do caminho real de sys.prefix.
        amb = Path(ambiente).resolve()
        bw += ["--ro-bind", str(amb), str(amb)]
    bootstrap = Path(__file__).with_name("executor.py").resolve()
    if not rede:
        bw += ["--ro-bind", str(bootstrap), "/executor.py"]
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(Path(ambiente).resolve()/"analise-mpl") if ambiente and (Path(ambiente)/"analise-mpl").is_dir() else "/saida/.mpl",
        "ANALISE_ENTRADA": "/entrada",
        "ANALISE_SAIDA": "/saida",
        "OMP_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "NUMEXPR_NUM_THREADS": "2",
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_CACHE_DIR": "/saida/.cache",
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_PYTHON_PREFERENCE": "only-system",
        "UV_PROJECT_ENVIRONMENT": "/saida/venv",
    }
    for k, v in env.items():
        bw += ["--setenv", k, v]
    bw += ["--remount-ro", "/tmp", "--", *comando]
    props += ["RemainAfterExit=yes", "StandardOutput=null", "StandardError=null"]
    cmd = ["systemd-run", "--user", "--no-block", "--unit=" + unit]
    cmd += ["--property=" + p for p in props]
    cmd += ["--", *bw]
    inicio = time.monotonic()
    iniciado = _rodar(cmd)
    exigir(iniciado["exit"] == 0, "unidade-nao-iniciada", 5)
    causa = None
    estado = {}
    tamanho = 0
    try:
        while True:
            info = _rodar(
                [
                    "systemctl",
                    "--user",
                    "show",
                    unit,
                    "-p",
                    "Result",
                    "-p",
                    "ExecMainStatus",
                    "-p",
                    "MemoryPeak",
                    "-p",
                    "MemoryMax",
                    "-p",
                    "MemoryHigh",
                    "-p",
                    "MemorySwapMax",
                    "-p",
                    "TasksMax",
                    "-p",
                    "CPUQuotaPerSecUSec",
                    "-p",
                    "SubState",
                    "-p",
                    "ActiveState",
                ]
            )
            estado = dict(
                linha.split("=", 1)
                for linha in info.get("stdout", "").splitlines()
                if "=" in linha
            )
            tamanho = bytes_regulares(Path(entrada).parent if entrada else saida)
            if tamanho > 2 * 1024**3 or time.monotonic() - inicio > prazo + 5:
                causa = "teto-disco" if tamanho > 2 * 1024**3 else "prazo-calculo"
                _rodar(["systemctl", "--user", "stop", unit])
                break
            if estado.get("SubState") in {"exited", "failed", "dead"}:
                break
            time.sleep(0.05)
        exigir(
            info["exit"] == 0
            and estado.get("MemoryMax") == str(memoria_max)
            and estado.get("MemoryHigh") == str(memoria_high)
            and estado.get("MemorySwapMax") == "0"
            and estado.get("TasksMax") == str(TASKS_MAX),
            "limites-nao-conferidos",
            5,
        )
        pico = estado.get("MemoryPeak", "")
        exigir(pico.isdigit(), "pico-cgroup-indisponivel", 5)
        status = int(estado.get("ExecMainStatus", "255"))
        if causa or estado.get("Result") in {"oom-kill", "timeout", "resources"}:
            raise Falha(5, causa or "teto-" + estado["Result"])
        exigir(status in {0, 1, 2, 3, 4, 5}, "receita-terminou-por-sinal", 5)
        return status, {
            "duracao_s": round(time.monotonic() - inicio, 6),
            "pico_bytes": int(pico),
            "isolamento": "systemd-rede+bwrap-arquivos-v1",
            "bytes": tamanho,
        }
    finally:
        _rodar(["systemctl", "--user", "stop", unit])
        _rodar(["systemctl", "--user", "reset-failed", unit])
