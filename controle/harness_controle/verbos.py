# verbos — chama bin/<verbo> --json como subprocesso e normaliza o resultado.
# capacidade: expediente
# dono: claudinho-TI
"""Contrato único pro agregador (e, mais tarde, pras duas ações da tela): "rodou
e devolveu JSON parseável" é sucesso de LEITURA, mesmo que o JSON carregue um
objeto {"erro": ...} por dentro (falha do verbo relatada por ele mesmo) ou um
veredito que não é "tudo certo" (ex. `conferir skill` sem --servido vira
"indeterminado", exit 2 — isso NÃO é falha de execução, é ausência de dado por
desenho, ver NOTAS-390.md). Só timeout, crash do processo, ou stdout vazio/
não-JSON viram falha de EXECUÇÃO aqui — é a única coisa que este módulo decide;
decidir "isso é caveat ou alert" é problema de quem renderiza (LOTE 3).
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BIN = Path(__file__).resolve().parents[2] / "bin"


@dataclass(frozen=True)
class ResultadoVerbo:
    ok: bool  # rodou e devolveu JSON parseável em stdout
    dados: Any  # objeto/array decodificado; None se ok=False
    motivo: str | None  # preenchido quando ok=False — nunca None nesse caso
    exit_code: int | None
    duracao_seg: float


def chamar(
    argv: list[str],
    *,
    timeout: float = 20.0,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> ResultadoVerbo:
    """argv[0] é o nome do arquivo em bin/ (ex. "infra"); o resto são os
    argumentos — incluir "--json" é responsabilidade de quem chama, não é
    acrescentado aqui (verbos diferentes têm posição/forma diferentes)."""
    caminho = BIN / argv[0]
    t0 = time.monotonic()
    try:
        r = subprocess.run(
            [str(caminho), *argv[1:]],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env=env,
            cwd=cwd,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ResultadoVerbo(False, None, f"timeout apos {timeout:g}s", None, timeout)
    except OSError as e:
        return ResultadoVerbo(
            False, None, f"nao foi possivel executar {argv[0]}: {e}", None, time.monotonic() - t0
        )
    duracao = time.monotonic() - t0

    saida = r.stdout.strip()
    if not saida:
        motivo = r.stderr.strip() or f"stdout vazio (exit {r.returncode})"
        return ResultadoVerbo(False, None, motivo, r.returncode, duracao)
    try:
        dados = json.loads(saida)
    except json.JSONDecodeError as e:
        # Diagnóstico inclui um pedaço do stdout: verbo que regrediu e voltou a
        # imprimir texto humano (ou stdout truncado) precisa ser identificável
        # sem reproduzir a chamada na mão.
        pedaco = saida if len(saida) <= 200 else saida[:200] + "…"
        return ResultadoVerbo(
            False, None, f"stdout nao e JSON valido ({e}): {pedaco!r}", r.returncode, duracao
        )

    return ResultadoVerbo(True, dados, None, r.returncode, duracao)
