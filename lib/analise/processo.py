"""A porta espera uma unidade irmã; o cálculo mantém sua unidade isolada."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

from . import Falha, json_canonico
from .unidade import _rodar


def incompleta(unit: str, causa: str) -> None:
    from .extrator import conectar

    with conectar("destino") as conn:
        conn.execute(
            "UPDATE analise.execucao SET estado='incompleta',causa=%s,terminada_em=clock_timestamp(),temporarios_ate=clock_timestamp()+interval '7 days' WHERE estado='ativa' AND manifesto->>'unidade'=%s",
            (causa, unit),
        )


def despachar(argv: list[str]) -> int:
    unit = "platafirma-analise-trabalho-" + uuid.uuid4().hex
    cmd = [
        "systemd-run",
        "--user",
        "--wait",
        "--pipe",
        "--unit=" + unit,
        "--property=MemoryHigh=1536M",
        "--property=MemoryMax=2048M",
        "--property=MemorySwapMax=0",
        "--property=CPUQuota=200%",
        "--property=TasksMax=64",
        "--property=KillMode=control-group",
        "--property=OOMPolicy=kill",
        "--property=RuntimeMaxSec=1800",
    ]
    for chave in (
        "PF_SUJEITO",
        "PF_CADEIRA",
        "PF_SESSAO",
        "PF_ORDEM_ID",
        "PF_SUPERFICIE",
        "PLATAFIRMA_INSTANCIA",
        "PF_RELEASE_RAIZ",
        "PLATAFIRMA_RELEASE",
        # #4185: a extração entra em cada banco por docker exec; a unidade precisa
        # achar o mesmo daemon (rootless) que a porta acha.
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "XDG_RUNTIME_DIR",
        # Só o ensaio o define; a porta não recebe ambiente do chamador.
        "PF_ANALISE_BANCOS",
    ):
        if chave in os.environ:
            cmd.append("--setenv=" + chave + "=" + os.environ[chave])
    # Configurações de endereço não são senhas e origem/destino seguem separados.
    for chave, valor in os.environ.items():
        if chave.startswith(
            ("ANALISE_ORIGEM_", "ANALISE_DESTINO_")
        ) and not chave.endswith("PASSWORD"):
            cmd.append("--setenv=" + chave + "=" + valor)
    cmd.append("--setenv=PF_ANALISE_UNIDADE=" + unit)
    cmd.extend(
        [
            "--",
            sys.executable,
            str(Path(__file__).resolve().parents[2] / "bin/analise"),
            "--_worker",
            *argv,
        ]
    )

    def terminar(signum: int, frame: object) -> None:
        _rodar(["systemctl", "--user", "stop", unit])
        incompleta(unit, "supervisor-interrompido")
        raise Falha(5, "supervisor-interrompido")

    anterior = signal.signal(signal.SIGTERM, terminar)
    try:
        p = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            close_fds=True,
            timeout=1810,
            check=False,
        )
        if p.stdout:
            sys.stdout.write(p.stdout)
            return p.returncode if p.returncode in {0, 1, 2, 3, 4, 5} else 5
        incompleta(unit, "unidade-incompleta")
        sys.stdout.write(
            json_canonico(
                {
                    "ato": argv[0] if argv else None,
                    "estado": "incompleta",
                    "exit": 5,
                    "causa": "unidade-incompleta",
                }
            )
            + "\n"
        )
        return 5
    except (OSError, subprocess.TimeoutExpired):
        _rodar(["systemctl", "--user", "stop", unit])
        incompleta(unit, "supervisor-interrompido")
        return 5
    finally:
        signal.signal(signal.SIGTERM, anterior)
        _rodar(["systemctl", "--user", "reset-failed", unit])
