"""Protege os temporários analíticos também na leitura genérica da porta."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .publicacao import Catalogo
from .extrator import conectar
from .publicacao import Catalogo


def delegar(caminho: Path, sujeito: str, instancia: Path) -> bool:
    """O ops não instala driver de banco: a checagem usa o venv do harness."""
    import subprocess

    from raizes import release

    py = release() / "venv/harness/bin/python"
    lib = Path(__file__).resolve().parents[1]
    codigo = (
        "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
        "from analise.acesso_arquivo import negar; "
        "sys.exit(4 if negar(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4])) else 0)"
    )
    try:
        p = subprocess.run(
            [
                str(py),
                "-I",
                "-c",
                codigo,
                str(lib),
                str(caminho),
                sujeito,
                str(instancia),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    return p.returncode != 0


def negar(
    caminho: Path, sujeito: str, instancia: Path, conexao: Callable = conectar
) -> bool:
    try:
        partes = caminho.resolve().relative_to((instancia / "var/tmp").resolve()).parts
    except ValueError:
        return False
    if len(partes) < 3 or partes[1] != "analise" or not partes[2].startswith("ex-"):
        return False
    import importlib.util

    if conexao is conectar and importlib.util.find_spec("psycopg") is None:
        return delegar(caminho, sujeito, instancia)
    conn = None
    try:
        if not sujeito:
            return True
        conn = conexao("destino")
        catalogo = Catalogo(conn, sujeito)
        catalogo.execucao(partes[2])
        return False
    except Exception:
        return True
    finally:
        if conn is not None:
            conn.close()
