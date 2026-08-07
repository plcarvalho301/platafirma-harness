#!/usr/bin/env python3
"""Fatia a coleta multi-step em blocos de questao e emite o gold set em jsonl.

Entrada: avaliacao/gold-set/coleta-multistep-20260807/*.md (coleta bruta, uma
mensagem por arquivo). Saida: gold-multistep-<data>.jsonl.

O corpo do gabarito e copiado por fatiamento, nao reescrito.
"""
import json
import re
import sys
from pathlib import Path

DIR = Path(__file__).parent / "coleta-multistep-20260807"

# cabecalho de questao: tolera "## QUESTÃO 1 — x", "QUESTÃO 1 — x", "# Q1 — x", "Q1 — x"
RE_Q = re.compile(r"^\s*(?:#{1,4}\s*)?(?:QUEST[AÃ]O|Q)\s*(\d)\s*[—\-:]\s*(.+?)\s*$", re.I)
# sub-secao: tolera "## X", "**X**", "X" em caixa alta
RE_SEC = re.compile(
    r"^\s*(?:#{1,4}\s*|\*\*|__)?"
    r"(DOCUMENTOS? ESCOLHIDOS?|(?:OS )?PARES[^:*.\n]*|ENUNCIADO|POSI[CÇ][AÃ]O[^:*.\n]*|GABARITO[^:*.\n]*)"
    r"\s*[:.]?\s*(?:\*\*|__)?\s*[:.]?\s*(?:\(.*?\))?\s*(?P<resto>.*)$",
    re.I,
)
RE_ELO = re.compile(r"(\d+)\s*elos?", re.I)
RE_RULE = re.compile(r"^[=\u2550\-\u2014_]{10,}\s*$")

CANON = {
    "documento": "documento",
    "documentos": "documento",
    "os pares": "pares",
    "enunciado": "enunciado",
    "posicao": "posicao",
    "gabarito": "gabarito",
}


def canon(titulo: str) -> str:
    t = titulo.lower()
    if t.startswith("documento"):
        return "documento"
    if "pares" in t:
        return "pares"
    if t.startswith("posi"):
        return "posicao"
    if t.startswith("enunciado"):
        return "enunciado"
    return "gabarito"


def fatiar(path: Path):
    linhas = path.read_text(encoding="utf-8").splitlines()
    questoes, atual, sec = [], None, None
    for ln in linhas:
        if RE_RULE.match(ln):
            continue
        m = RE_Q.match(ln)
        if m and (atual is None or m.group(1) != atual["n"]):
            if atual:
                questoes.append(atual)
            atual = {"n": m.group(1), "titulo": m.group(2).strip(), "secoes": {}}
            sec = None
            continue
        if atual is None:
            continue
        m = RE_SEC.match(ln)
        if m:
            sec = canon(m.group(1))
            atual["secoes"].setdefault(sec, [])
            resto = (m.group("resto") or "").strip().lstrip(":.").strip()
            if resto:
                atual["secoes"][sec].append(resto)
            continue
        if sec:
            atual["secoes"][sec].append(ln)
    if atual:
        questoes.append(atual)
    for q in questoes:
        # fallback: cadeira que nomeia o documento no proprio titulo da questao
        if "documento" not in q["secoes"]:
            q["secoes"]["documento"] = [q["titulo"]]
        q["secoes"] = {k: "\n".join(v).strip() for k, v in q["secoes"].items()}
    return questoes


def main():
    arquivos = sorted(p for p in DIR.glob("2026*.md"))
    problemas = []
    todas = {}
    for p in arquivos:
        qs = fatiar(p)
        todas[p.name] = qs
        faltando = [
            (q["n"], sorted({"documento", "enunciado", "gabarito"} - set(q["secoes"])))
            for q in qs
            if not {"documento", "enunciado", "gabarito"} <= set(q["secoes"])
        ]
        print(f"{p.name}: {len(qs)} questoes", end="")
        if faltando:
            print(f"  FALTA {faltando}")
            problemas.append((p.name, faltando))
        else:
            print("  ok")
    json.dump(
        {k: v for k, v in todas.items()},
        open("/tmp/fatias.json", "w"),
        ensure_ascii=False,
    )
    print(f"\n{sum(len(v) for v in todas.values())} blocos; /tmp/fatias.json escrito")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
