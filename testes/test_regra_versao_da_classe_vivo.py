# componente: componente:leitura
# verifica: configuracao:versao-da-classe
"""Teste de regra `teste:leitura--configuracao-versao-da-classe` (story 4427, t11).

Compara, em toda classe do fichário (uma classe por vez para ocupar no máximo uma das
quatro conexões de `analise_leitura`), a versão devolvida por `ontologia ler <classe>` com
a fornada do cabeçalho de `busca consultar --classe <classe>`.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BIN_BUSCA = RAIZ / "bin" / "busca"
BIN_INFRA = RAIZ / "bin" / "infra"
_RE_FORNADA_OLARIA = re.compile(r"^[^·]+·\s*fornada\s+([0-9a-f-]+)\s*·")
_RE_FORNADA_BUSCA = re.compile(r"^classe\s*·\s*fornada\s+([0-9a-f-]+)\s*·")


def _listar_classes_do_fichario() -> list[str]:
    proc = subprocess.run(
        [str(BIN_INFRA), "rodar", "ontologia", "--", "listar", "shape", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"ontologia listar shape falhou ({proc.returncode}): {proc.stderr}"
    dados = json.loads(proc.stdout)
    chaves = [str(c) for c in dados.get("chaves") or ()]
    assert chaves, "nenhuma classe listada pela Olaria"
    return chaves


def _versao_pela_olaria(slug: str) -> str:
    proc = subprocess.run(
        [str(BIN_INFRA), "rodar", "ontologia", "--", "ler", slug],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"ontologia ler {slug} falhou ({proc.returncode}): {proc.stderr}"
    primeira = proc.stdout.splitlines()[0] if proc.stdout else ""
    m = _RE_FORNADA_OLARIA.match(primeira)
    assert m is not None, f"cabeçalho inesperado de ontologia ler {slug}: {primeira!r}"
    return m.group(1)


def _fornada_pelo_consultar(slug: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(BIN_BUSCA), "consultar", "--classe", slug],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"busca consultar --classe {slug} falhou ({proc.returncode}): {proc.stderr}"
    primeira = proc.stdout.splitlines()[0] if proc.stdout else ""
    m = _RE_FORNADA_BUSCA.match(primeira)
    assert m is not None, f"cabeçalho inesperado de busca consultar --classe {slug}: {primeira!r}"
    return m.group(1)


def _medir_divergencias(classes: list[str]) -> list[str]:
    divergencias: list[str] = []
    for slug in classes:
        v_olaria = _versao_pela_olaria(slug)
        v_leitor = _fornada_pelo_consultar(slug)
        if v_olaria != v_leitor:
            divergencias.append(f"{slug}: olaria={v_olaria} != leitor={v_leitor}")
    return divergencias


def test_olaria_e_leitor_dao_a_mesma_versao_em_toda_classe_do_fichario() -> None:
    divergencias = _medir_divergencias(_listar_classes_do_fichario())
    assert not divergencias, "divergências de versão da classe:\n" + "\n".join(divergencias)
