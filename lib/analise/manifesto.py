"""Identidade e picos do cgroup por fase, sem dado nem segredo."""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import json_canonico


def identidade_receita(pasta: Path, registro: dict) -> dict:
    arquivos = {}
    for p in sorted(pasta.rglob("*")):
        if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts:
            arquivos[str(p.relative_to(pasta))] = hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
    return {
        **registro,
        "arquivos": arquivos,
        "sha256": hashlib.sha256(json_canonico(arquivos).encode()).hexdigest(),
    }


def _cgroup() -> Path:
    linha = next(
        linha
        for linha in Path("/proc/self/cgroup").read_text().splitlines()
        if linha.startswith("0:")
    )
    return Path("/sys/fs/cgroup") / linha.split(":", 2)[2].lstrip("/")


@contextmanager
def fase(manifesto: dict, nome: str) -> Iterator[dict]:
    inicio = time.monotonic()
    raiz = _cgroup()
    medida = {
        "duracao_s": 0,
        "bytes": 0,
        "pico_bytes": 0,
        "pico_metodo": "cgroup-memory.current-amostrado-10ms",
    }
    manifesto.setdefault("fases", {})[nome] = medida
    parar = threading.Event()

    def amostrar() -> None:
        while True:
            atual = int((raiz / "memory.current").read_text())
            medida["pico_bytes"] = max(medida["pico_bytes"], atual)
            if parar.wait(0.01):
                return

    thread = threading.Thread(target=amostrar, daemon=True)
    thread.start()
    try:
        yield medida
    finally:
        parar.set()
        thread.join(timeout=1)
        medida["duracao_s"] = round(time.monotonic() - inicio, 6)
        medida["pico_bytes"] = max(
            medida["pico_bytes"], int((raiz / "memory.current").read_text())
        )
        medida["pico_cgroup_acumulado"] = int((raiz / "memory.peak").read_text())
