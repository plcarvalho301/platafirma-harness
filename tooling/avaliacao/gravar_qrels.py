#!/usr/bin/env python3
"""Grava qrels no gold set multi-step, em dois niveis de confianca.

- `qrels_ancora`: obra do "documento escolhido" da questao. Casamento por
  sequencia de titulo dentro do campo `documento_ancora`; e o alvo minimo que a
  recuperacao tem de trazer. Confiavel para Recall@k.
- `qrels_par`: obras citadas nos pares. Casamento automatico, NAO conferido item
  a item — conjunto expandido, use com a ressalva declarada em `qrels_nota`.

Questao ancorada em repo/banco/ontologia (ADR, ttl, schema) fica com lista vazia
e `fonte_evidencia` declarando onde a evidencia mora. Vazio ali e correto, nao
falha de casamento.

Uso: python3 gravar_qrels.py /tmp/catalogo.csv
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).parent
GOLD = AQUI / "gold-multistep-20260807.jsonl"

# Ancora fora do acervo: a evidencia mora no repo, no banco ou na ontologia.
FONTE_INTERNA = {
    "claudinho-conhecimento-ms-01": ["ontologia", "acervo"],
    "claudinho-conhecimento-ms-02": ["banco", "acervo"],
    "claudinho-conhecimento-ms-03": ["ontologia", "banco", "acervo"],
    "claudinho-arquiteto-ms-01": ["repo", "acervo"],
    "claudinho-arquiteto-ms-02": ["repo", "banco"],
    "claudinho-arquiteto-ms-03": ["repo", "wiki", "banco"],
    "claudinho-arquiteto-ms-04": ["repo", "acervo"],
    "claudinho-arquiteto-ms-05": ["repo", "acervo"],
    "claudinho-arquiteto-ms-06": ["repo", "acervo"],
    "claudinho-IA-ms-01": ["repo", "acervo"],
    "claudinho-IA-ms-03": ["host", "acervo"],
}

# Ancora que o casamento por titulo nao alcanca: a cadeira nomeou por arquivo,
# por autor ou pelo titulo ISO completo, nao pelo titulo do catalogo.
ANCORA_MANUAL = {
    "claudinha-gestao-estrategica-ms-03": ["ac6ffd6c-935f-4f68-b22e-7585f87bdf1b"],
    "claudinho-TI-ms-03": ["f36f4767-21c4-4825-94be-9d783c9a1563"],
    "claudinho-IA-ms-02": ["a88e7493-9ce7-4e11-b032-5117dde68c96"],
}

# Falso positivo do casador, conferido a mao: a expressao generica casou titulo
# de obra que a questao nao usa.
EXCLUSAO = {
    "claudinha-gestao-estrategica-ms-03": ["a41d1cb6-899d-4c2c-8aab-d2c31cc2ad20"],
}

# Par que o casador nao alcanca: a questao nomeia a obra pela sigla (e-ARQ,
# SKOS, BFO), nao pelo titulo do catalogo.
PAR_MANUAL = {
    "claudinho-conhecimento-ms-01": ["0d9fc4f8-c022-44e3-9979-d66e0ccbdbc0"],
    "claudinho-conhecimento-ms-02": [
        "c86ee1f8-6e5b-4982-975a-685190a7d75d",
        "81d6664e-1172-4da8-b611-14181782c6a9",
    ],
    "claudinho-conhecimento-ms-03": ["81d6664e-1172-4da8-b611-14181782c6a9"],
}

NOTA = (
    "qrels_ancora conferido por casamento de titulo dentro do campo "
    "documento_ancora. qrels_par e casamento automatico sobre os pares, sem "
    "conferencia item a item — nao usar como denominador de Recall sem revisar."
)


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


VAZIAS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "por", "uma",
    "para", "dos", "das", "sobre", "como", "que", "guide", "manual", "lista",
    "modelo", "introduction", "overview", "using", "novo", "nova", "estudo",
}


def substantivo(pref):
    """Prefixo com pelo menos duas palavras de conteudo, ou uma bem longa."""
    toks = [t for t in pref.split() if len(t) >= 4 and t not in VAZIAS]
    return len(toks) >= 2 or (len(toks) == 1 and len(toks[0]) >= 8)


def chavear(catalogo):
    """Chave = menor prefixo de titulo que identifica a obra sozinha no catalogo.

    Sem isso, quatro Instrucoes Normativas GSI/PR casam entre si: o prefixo de
    tamanho fixo nao distingue familia de norma que so difere no numero.
    """
    for o in catalogo:
        toks = norm(o["titulo"]).split()
        pref = " ".join(toks)          # titulo curto: a chave e o titulo inteiro
        for n in range(2, min(len(toks), 14) + 1):
            cand = " ".join(toks[:n])
            # prefixo so de palavra vazia ("por uma", "guide to") casa qualquer coisa
            if not substantivo(cand) and n < len(toks):
                continue
            iguais = sum(1 for x in catalogo if " ".join(norm(x["titulo"]).split()[:n]) == cand)
            if iguais == 1:
                pref = cand
                break
        o["chave"] = pref
    return catalogo


def casa(catalogo, texto):
    t = norm(texto)
    achados = []
    for o in catalogo:
        seq = o["chave"]
        if len(seq) >= 7 and re.search(r"\b" + re.escape(seq) + r"\b", t):
            achados.append(o)
    # descarta titulo que e prefixo de outro casado (fica o mais especifico)
    ids = set()
    for o in achados:
        mais = [x for x in achados if x["id"] != o["id"] and norm(o["titulo"]) in norm(x["titulo"])]
        if not mais:
            ids.add(o["id"])
    return [o for o in achados if o["id"] in ids]


def main(catalogo_path):
    catalogo = []
    with open(catalogo_path, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) >= 3 and row[1]:
                catalogo.append({"id": row[0], "titulo": row[1], "chunks": int(row[2])})
    catalogo = chavear(catalogo)
    porid = {o["id"]: o for o in catalogo}

    regs = [json.loads(l) for l in open(GOLD, encoding="utf-8")]
    for r in regs:
        ancora = casa(catalogo, r["titulo"] + " " + r["documento_ancora"])
        # uuid escrito a mao pela propria cadeira, ou casamento manual, conta como ancora
        for oid in list(r.get("obra_ids", [])) + ANCORA_MANUAL.get(r["id"], []):
            if oid in porid and oid not in {o["id"] for o in ancora}:
                ancora.append(porid[oid])
        excl = set(EXCLUSAO.get(r["id"], []))
        ancora = [o for o in ancora if o["id"] not in excl]
        pares = [
            o for o in casa(catalogo, r["pares"])
            if o["id"] not in {a["id"] for a in ancora} and o["id"] not in excl
        ]
        for oid in PAR_MANUAL.get(r["id"], []):
            if oid in porid and oid not in {x["id"] for x in ancora + pares}:
                pares.append(porid[oid])
        r["qrels_ancora"] = [{"obra_id": o["id"], "titulo": o["titulo"], "chunks": o["chunks"]} for o in ancora]
        r["qrels_par"] = [{"obra_id": o["id"], "titulo": o["titulo"], "chunks": o["chunks"]} for o in pares]
        r["fonte_evidencia"] = FONTE_INTERNA.get(r["id"], ["acervo"])
        r["qrels_nota"] = NOTA
        r.pop("obra_ids", None)

    with open(GOLD, "w", encoding="utf-8") as fh:
        for r in regs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    sem = [r["id"] for r in regs if not r["qrels_ancora"] and "acervo" in r["fonte_evidencia"][:1]]
    print(f"{len(regs)} questoes gravadas")
    print(f"  com ancora no acervo: {sum(1 for r in regs if r['qrels_ancora'])}")
    print(f"  obras distintas em qrels_ancora: {len({o['obra_id'] for r in regs for o in r['qrels_ancora']})}")
    print(f"  obras distintas em qrels_par: {len({o['obra_id'] for r in regs for o in r['qrels_par']})}")
    if sem:
        print(f"  ancora de acervo NAO casada (conferir): {sem}")
    for r in regs:
        if r["qrels_ancora"]:
            print(f"  {r['id']}: " + " | ".join(o["titulo"][:52] for o in r["qrels_ancora"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/catalogo.csv")
