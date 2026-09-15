"""raizes — as duas raizes de producao e a bancada declarada (card #3010).

Producao mora em duas raizes e so nelas: a release (codigo imutavel) e a instancia
(segredos, dados, estado, logs). Todo caminho de producao deriva delas. A bancada
(onde se escreve codigo) nunca e lida por producao; so os verbos de bancada chamam
bancada(), que falha alto quando a conta nao declarou onde ela fica.

As variaveis de ambiente existem para teste apontar tudo para um diretorio temporario.
"""
from __future__ import annotations

import os
from pathlib import Path


def release_raiz() -> Path:
    return Path(os.environ.get("PF_RELEASE_RAIZ", "/opt/platafirma"))


def release() -> Path:
    """Atalhos estaveis da release no ar: <raiz>/current/<familia-curta>."""
    return Path(os.environ.get("PLATAFIRMA_RELEASE", str(release_raiz() / "current")))


def instancia() -> Path:
    return Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))


def arquivo_bancada() -> Path:
    return Path(os.environ.get("PLATAFIRMA_ARQUIVO_BANCADA", str(Path.home() / ".config" / "platafirma" / "bancada")))


class BancadaNaoDeclarada(RuntimeError):
    """A conta nao declarou a bancada; verbo de bancada sai 3."""


def bancada() -> Path:
    valor = os.environ.get("PLATAFIRMA_BANCADA", "").strip()
    arq = arquivo_bancada()
    if not valor and arq.is_file():
        linhas = arq.read_text(encoding="utf-8").splitlines()
        valor = linhas[0].strip() if linhas else ""
    if not valor:
        raise BancadaNaoDeclarada(
            f"bancada nao declarada: defina PLATAFIRMA_BANCADA ou escreva a raiz em {arq}")
    return Path(valor)
