"""Gate de citação — de "afirmação tem chão" para "afirmação tem texto" (spec §4.6, §8.4).

Renomeado de `pesquisa/verificar.py` para `pesquisa/citacoes.py` no card #4454 para reservar
a palavra `verificar` ao ato do catálogo (Política 0011).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import manifesto as M

_RE_MARCADOR = re.compile(r"\[m:(\d+)(?:\s+[«\"]([^»\"]*)[»\"])?\]")
_RE_ESPACO = re.compile(r"\s+")
DERIVADOS_DE_TEXTO = ("md", "raw.md", "json")


def _normaliza(texto: str) -> str:
    """Espaço, quebra de linha e tabulação viram um espaço só (#4457 t8)."""
    return _RE_ESPACO.sub(" ", texto).strip()


def _indexa(linhas: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    por_n: dict[int, dict[str, Any]] = {}
    for ln in linhas:
        n = ln.get("n")
        if isinstance(n, int):
            por_n[n] = ln
    return por_n


def _trecho_presente(trab: "M.Trabalho", n: int, trecho: str) -> bool:
    alvo = _normaliza(trecho)
    for ext in DERIVADOS_DE_TEXTO:
        p = trab.derivado / f"{n}.{ext}"
        if p.exists() and alvo in _normaliza(p.read_text(encoding="utf-8")):
            return True
    return False


def citacoes(relatorio: str | Path, trab: "M.Trabalho") -> dict[str, Any]:
    caminho = Path(relatorio)
    if not caminho.exists():
        from .envelope import UsoInvalido

        raise UsoInvalido(f"relatorio-inexistente:{caminho}")
    texto = caminho.read_text(encoding="utf-8")

    linhas = trab.linhas()
    por_n = _indexa(linhas)
    com_artefato = {n for n, ln in por_n.items() if ln.get("ato") in ("ler", "coletar", "resolver", "historico")}

    afirmacoes: list[dict[str, Any]] = []
    sem_ancora: list[int] = []
    ancora_quebrada: list[int] = []
    trecho_ausente: list[int] = []
    citados: set[int] = set()

    for m in _RE_MARCADOR.finditer(texto):
        n = int(m.group(1))
        trecho = (m.group(2) or "").strip()
        citados.add(n)
        reg = {"n": n, "trecho": trecho or None, "ok": True, "falhas": []}

        ln = por_n.get(n)
        if ln is None:
            sem_ancora.append(n)
            reg["ok"] = False
            reg["falhas"].append("sem_ancora")
            afirmacoes.append(reg)
            continue

        quebrou = False
        sha = ln.get("sha256")
        bruto = ln.get("bruto")
        status = ln.get("status")
        if not sha:
            quebrou = True
        elif bruto:
            p = Path(bruto)
            if not p.exists() or M.sha256_bytes(p.read_bytes()) != sha:
                quebrou = True
        if status is not None and not (200 <= int(status) < 300):
            quebrou = True
        if quebrou:
            ancora_quebrada.append(n)
            reg["ok"] = False
            reg["falhas"].append("ancora_quebrada")

        if trecho and not _trecho_presente(trab, n, trecho):
            trecho_ausente.append(n)
            reg["ok"] = False
            reg["falhas"].append("trecho_ausente")

        afirmacoes.append(reg)

    sem_marcador = not afirmacoes
    nao_citado = sorted(com_artefato - citados)
    reprovou = bool(sem_marcador or sem_ancora or ancora_quebrada or trecho_ausente)
    return {
        "afirmacoes": afirmacoes,
        "sem_marcador": sem_marcador,
        "sem_ancora": sorted(set(sem_ancora)),
        "ancora_quebrada": sorted(set(ancora_quebrada)),
        "trecho_ausente": sorted(set(trecho_ausente)),
        "nao_citado": nao_citado,
        "reprovou": reprovou,
    }
