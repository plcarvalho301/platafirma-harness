#!/usr/bin/env python3
"""Casa as questoes do gold set multi-step com obras do catalogo (qrels).

Gera candidatos por sobreposicao de tokens entre o titulo do catalogo e o texto
da questao. A saida e material de revisao humana, nao qrels final: o casamento
so entra no jsonl depois de conferido.

Uso: python3 casar_obras.py /tmp/catalogo.csv
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).parent
GOLD = AQUI / "gold-multistep-20260807.jsonl"

STOP = {
    "the", "and", "for", "with", "that", "this", "from", "your", "guide", "com",
    "para", "dos", "das", "sobre", "uma", "como", "por", "que", "nao", "brasil",
    "edition", "second", "third", "first", "version", "volume", "part", "parte",
    "manual", "livro", "book", "report", "relatorio", "sobre", "geral",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def toks(s: str) -> set:
    return {t for t in norm(s).split() if len(t) >= 4 and t not in STOP}


def main(catalogo_path):
    catalogo = []
    with open(catalogo_path, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) < 3 or not row[1]:
                continue
            catalogo.append({"id": row[0], "titulo": row[1], "chunks": int(row[2]), "toks": toks(row[1])})

    regs = [json.loads(l) for l in open(GOLD, encoding="utf-8")]
    saida = []
    for r in regs:
        # so ancora + pares: o gabarito traz bibliografia solta e lista de ausencia,
        # que inflam o casamento com obra que a questao nao exige recuperar
        texto = norm(" ".join([r["titulo"], r["documento_ancora"], r["pares"]]))
        tset = set(texto.split())
        cands = []
        for o in catalogo:
            if not o["toks"] or len(o["toks"]) < 2:
                continue
            # 1) sequencia: o titulo (ou seu prefixo significativo) aparece na ordem
            seq = " ".join(norm(o["titulo"]).split()[:5])
            if len(seq) >= 8 and re.search(r"\b" + re.escape(seq) + r"\b", texto):
                cands.append((1.0, o["chunks"], o["id"], o["titulo"]))
                continue
            # 2) sobreposicao de tokens raros, exigindo cobertura quase total
            hit = o["toks"] & tset
            score = len(hit) / len(o["toks"])
            if score >= 0.9 and len(o["toks"]) >= 3:
                cands.append((round(score, 2), o["chunks"], o["id"], o["titulo"]))
        cands.sort(reverse=True)
        saida.append({"id": r["id"], "titulo": r["titulo"], "candidatos": cands[:8]})

    json.dump(saida, open("/tmp/candidatos.json", "w"), ensure_ascii=False, indent=1)
    for s in saida:
        print(f"\n=== {s['id']} — {s['titulo'][:70]}")
        for score, chunks, oid, tit in s["candidatos"]:
            print(f"   {score}  [{chunks:>5} chunks]  {oid}  {tit[:78]}")
        if not s["candidatos"]:
            print("   (nenhum)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/catalogo.csv")
