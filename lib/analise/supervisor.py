"""Admissão exclusiva, reserva e prazo de extração externo ao SQL."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

import fcntl
import shutil
import threading
from contextlib import contextmanager

from . import Falha, exigir


@contextmanager
def admitir(raiz: Path, temporarios: Path | None = None) -> Iterator[None]:
    raiz.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(raiz / "admissao.lock", "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Falha(
                5, "fila-ocupada", "tente novamente após a execução ativa"
            ) from None
        mem = dict(
            linha.split(":", 1)
            for linha in Path("/proc/meminfo").read_text().splitlines()
        )
        exigir(
            int(mem["MemAvailable"].split()[0]) * 1024 >= 6 * 1024**3, "fila-memoria", 5
        )
        exigir(shutil.disk_usage(raiz).free >= 2 * 1024**3, "fila-disco", 5)
        total = sum(
            p.stat().st_size
            for p in raiz.rglob("*")
            if p.is_file() and not p.is_symlink()
        )
        if temporarios is not None:
            from .unidade import bytes_regulares
            total += sum(bytes_regulares(p) for p in temporarios.glob("*/analise") if p.is_dir())
        exigir(total + 2 * 1024**3 <= 10 * 1024**3, "fila-disco-total", 5)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


@contextmanager
def prazo_extracao(conn: Connection, segundos: float = 120) -> Iterator[None]:
    venceu = threading.Event()

    def cancelar() -> None:
        venceu.set()
        try:
            conn.cancel()
        finally:
            conn.close()

    timer = threading.Timer(segundos, cancelar)
    timer.daemon = True
    timer.start()
    try:
        yield
        exigir(not venceu.is_set(), "prazo-extracao", 5)
    except Exception:
        if venceu.is_set():
            raise Falha(5, "prazo-extracao") from None
        raise
    finally:
        timer.cancel()
        timer.join(timeout=2)
