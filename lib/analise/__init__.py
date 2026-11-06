"""Execução reproduzível de receitas registradas, sem credencial no cálculo."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Falha(Exception):
    exit: int
    causa: str
    correcao: str = ""

    def __str__(self) -> str:
        return self.causa


def exigir(condicao: bool, causa: str, exit: int = 2, correcao: str = "") -> None:
    if not condicao:
        raise Falha(exit, causa, correcao)


def agora() -> datetime:
    return datetime.now(UTC)


def json_canonico(valor: object) -> str:
    return json.dumps(
        valor,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def hash_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def nome_seguro(nome: str) -> str:
    exigir(
        isinstance(nome, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,62}", nome),
        "nome-invalido",
    )
    return nome


def relativo(raiz: Path, nome: str) -> Path:
    from pathlib import Path

    exigir(
        isinstance(nome, str)
        and nome
        and not Path(nome).is_absolute()
        and ".." not in Path(nome).parts,
        "caminho-nao-declarado",
        4,
    )
    p = raiz / nome
    exigir(
        not p.is_symlink() and p.resolve().is_relative_to(raiz.resolve()),
        "caminho-nao-declarado",
        4,
    )
    return p


def gravar_atomico(caminho: Path, conteudo: str) -> None:
    import os
    import tempfile

    fd, nome = tempfile.mkstemp(dir=caminho.parent, prefix=".analise-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(conteudo)
            f.flush()
            os.fsync(f.fileno())
        os.replace(nome, caminho)
    finally:
        if os.path.exists(nome):
            os.unlink(nome)
