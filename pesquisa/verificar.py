"""Gate de citação — de "afirmação tem chão" para "afirmação tem texto" (spec §4.6, §8.4).

O bench marcou isto como vazio sem equivalente de mercado. Lê marcadores `[m:<n>]` e,
quando presente, `[m:<n> «trecho»]` no relatório e confere cada um contra o manifesto do
trabalho, SEM inferência:

  linha existe        — o `n` citado tem linha no manifesto           (senão: sem_ancora)
  âncora íntegra      — sha256 presente · bruto/ no disco com o mesmo
                        hash · status 2xx                             (senão: ancora_quebrada)
  texto presente      — havendo trecho, o literal está em derivado/<n>.md (senão: trecho_ausente)

`nao_citado`: linhas do manifesto que produziram artefato e nenhuma afirmação usou —
coleta que não virou conhecimento também é dado de auditoria. Exit 1 se qualquer das três
primeiras listas não for vazia. Não julga o mérito da afirmação — julga se tem chão e texto.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import manifesto as M

_RE_MARCADOR = re.compile(r"\[m:(\d+)(?:\s+[«\"]([^»\"]*)[»\"])?\]")


def _indexa(linhas: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    por_n: dict[int, dict[str, Any]] = {}
    for ln in linhas:
        n = ln.get("n")
        if isinstance(n, int):
            por_n[n] = ln
    return por_n


def verificar(relatorio: str | Path, trab: "M.Trabalho") -> dict[str, Any]:
    caminho = Path(relatorio)
    if not caminho.exists():
        from .envelope import UsoInvalido

        raise UsoInvalido(f"relatorio-inexistente:{caminho}")
    texto = caminho.read_text(encoding="utf-8")

    linhas = trab.linhas()
    por_n = _indexa(linhas)
    # linhas que produziram artefato (candidatas a "não citado")
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

        # âncora íntegra: sha256 + bruto no disco com mesmo hash + status 2xx
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

        # texto presente (literal, grep) quando houver trecho
        if trecho:
            md = trab.derivado / f"{n}.md"
            corpo = md.read_text(encoding="utf-8") if md.exists() else ""
            if trecho not in corpo:
                trecho_ausente.append(n)
                reg["ok"] = False
                reg["falhas"].append("trecho_ausente")

        afirmacoes.append(reg)

    nao_citado = sorted(com_artefato - citados)
    reprovou = bool(sem_ancora or ancora_quebrada or trecho_ausente)
    return {
        "afirmacoes": afirmacoes,
        "sem_ancora": sorted(set(sem_ancora)),
        "ancora_quebrada": sorted(set(ancora_quebrada)),
        "trecho_ausente": sorted(set(trecho_ausente)),
        "nao_citado": nao_citado,
        "reprovou": reprovou,
    }
