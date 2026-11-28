"""Três guardas; a coleta nunca renova prazo nem toca execução ativa."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .publicacao import Catalogo

from .publicacao import Catalogo


def _forcar_escrita(func: Callable[[str], object], path: str, exc: BaseException) -> None:
    if not isinstance(exc, PermissionError):
        raise exc
    alvo = Path(path)
    if alvo.parent.exists() and not alvo.parent.is_symlink():
        os.chmod(alvo.parent, 0o700)
    if alvo.exists() and not alvo.is_symlink():
        os.chmod(alvo, 0o700)
    func(path)


def coletar(catalogo: Catalogo, temporarios: Path) -> int:
    conn = catalogo.conn
    # Somente quem possui o objeto o descarta; a coleta assume cada sujeito
    # explicitamente, depois de decidir o vencimento no catálogo.
    total = 0
    rows = conn.execute(
        "SELECT id,sujeito FROM analise.resultado WHERE expires_at IS NOT NULL AND expires_at<=clock_timestamp() "
        "UNION ALL SELECT id,sujeito FROM analise.base WHERE expires_at IS NOT NULL AND expires_at<=clock_timestamp()"
    ).fetchall()
    for id, sujeito in rows:
        c = Catalogo(conn, sujeito)
        c.descartar(id)
        total += 1
    ativos = {
        x[0]
        for x in conn.execute("SELECT id FROM analise.execucao WHERE estado='ativa'")
    }
    for id, ordem in conn.execute(
        "SELECT id,ordem FROM analise.execucao WHERE temporarios_ate<=clock_timestamp() AND estado<>'ativa'"
    ):
        p = temporarios / ordem / "analise" / id
        if id not in ativos and p.is_dir() and not p.is_symlink():
            try:
                shutil.rmtree(p, onexc=_forcar_escrita)
            except PermissionError:
                pass
    return total


def main() -> int:
    """Entrada privada da automação declarada, sem sujeito de pessoa."""
    import fcntl
    import os
    import sys

    from raizes import instancia

    from . import json_canonico
    from .extrator import conectar

    if "analise-coleta" not in os.environ.get("PF_AUTOMACAO_SLUGS", "").split(","):
        sys.stdout.write(
            json_canonico({"exit": 4, "causa": "coleta-so-pela-automacao"}) + "\n"
        )
        return 4
    raiz = instancia() / "var/analise"
    raiz.mkdir(parents=True, exist_ok=True)
    with open(raiz / "admissao.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with conectar("destino") as conn:
            cat = Catalogo(conn, "coleta")
            n = coletar(cat, instancia() / "var/tmp")
    sys.stdout.write(json_canonico({"exit": 0, "objetos_removidos": n}) + "\n")
    return 0


def recuperar_orfas(catalogo: Catalogo) -> None:
    # Só se chama sob o lock exclusivo de admissão; não há outra execução ativa.
    catalogo.conn.execute(
        "UPDATE analise.execucao SET estado='incompleta',causa='orfã',terminada_em=clock_timestamp(),temporarios_ate=clock_timestamp()+interval '7 days' WHERE estado='ativa'"
    )
