#!/usr/bin/env python3
"""Monta o gold set multi-step em jsonl a partir da coleta bruta fatiada.

Uso: python3 fatiar_multistep.py && python3 montar_multistep.py

Entrada:  /tmp/fatias.json (saida do fatiador)
Saida:    gold-multistep-20260807.jsonl  +  gold-multistep-20260807-descartes.tsv
"""
import json
import re
from pathlib import Path

AQUI = Path(__file__).parent
DATA = "20260807"

# De-duplicacao: (arquivo, indice_da_questao) -> motivo do descarte.
# TI mandou 3 conjuntos em sessoes paralelas (card 326); colisao por
# documento-ancora + tese, nao por mensagem.
DESCARTES = {
    ("20260807T014245-claudinho-TI.md", 1): (
        "dup de 015650-Q2 (mesmo doc DORA SoDR 2024, mesma tese: a quarta metrica "
        "trocou de evento ancora); 015650 decompoe por elo numerado"
    ),
    ("20260807T015629-claudinho-TI.md", 0): (
        "dup de 015650-Q1 (mesmo doc Guide FitSM->ISO 20000-1, mesmos pares: v2.0 "
        "declarada x v3.0.1 no acervo, ISO ausente)"
    ),
    ("20260807T015650-claudinho-TI.md", 2): (
        "contida em 014245-Q3 (mesmo doc ITIL 4 5.2.4; o cenario do comite ja e a "
        "segunda parte do enunciado de 014245)"
    ),
}
# Conjunto inteiro descartado por substituicao declarada pela propria cadeira.
ARQUIVOS_DESCARTADOS = {
    "20260807T020138-claudinha-produto.md": "substituido por 080529 (declarado pela cadeira)",
    "20260807T021325-claudinho-IA.md": "adendo sem questao nova",
}

# Ressalva de ingestao: obra ingerida como casca; reingestao muda a conclusao.
RESSALVAS = {
    ("20260807T022540-claudinho-seguranca.md", 0): (
        "pendente-refacao: depende da IN ITI no 35/2026, hoje ingerida como casca "
        "(1 trecho, so a URL do DOU). Reingerir antes de congelar."
    ),
}

RE_ELO = re.compile(r"(\d+)\s*elos?\b", re.I)
RE_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
RE_CADEIRA = re.compile(r"-((?:claudinh[oa])-[a-zA-Z-]+)\.md$")


def main():
    fatias = json.load(open("/tmp/fatias.json"))
    linhas, descartes = [], []
    contador = {}

    for arquivo in sorted(fatias):
        cadeira = RE_CADEIRA.search(arquivo).group(1)
        if arquivo in ARQUIVOS_DESCARTADOS:
            for q in fatias[arquivo]:
                descartes.append((arquivo, q["n"], q["titulo"], ARQUIVOS_DESCARTADOS[arquivo]))
            continue
        for i, q in enumerate(fatias[arquivo]):
            if (arquivo, i) in DESCARTES:
                descartes.append((arquivo, q["n"], q["titulo"], DESCARTES[(arquivo, i)]))
                continue
            s = q["secoes"]
            bruto = "\n".join(s.values())
            elos = [int(m) for m in RE_ELO.findall(s.get("gabarito", ""))]
            contador[cadeira] = contador.get(cadeira, 0) + 1
            reg = {
                "id": f"{cadeira}-ms-{contador[cadeira]:02d}",
                "cadeira": cadeira,
                "tipo": "multistep",
                "estrato": f"multistep-{DATA}",
                "titulo": q["titulo"],
                "pergunta": s.get("enunciado", ""),
                "documento_ancora": s.get("documento", ""),
                "pares": s.get("pares", ""),
                "posicao": s.get("posicao", ""),
                "gabarito": s.get("gabarito", ""),
                "elos_max": max(elos) if elos else None,
                "obra_ids": sorted(set(RE_UUID.findall(bruto))),
                "relevancia": "positiva",
                "pontuavel": True,
                "ressalva": RESSALVAS.get((arquivo, i)),
                "fonte": {"arquivo": arquivo, "questao": q["n"]},
            }
            linhas.append(reg)

    saida = AQUI / f"gold-multistep-{DATA}.jsonl"
    with open(saida, "w", encoding="utf-8") as fh:
        for r in linhas:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    tsv = AQUI / f"gold-multistep-{DATA}-descartes.tsv"
    with open(tsv, "w", encoding="utf-8") as fh:
        fh.write("arquivo\tquestao\ttitulo\tmotivo\n")
        for d in descartes:
            fh.write("\t".join(str(x).replace("\t", " ") for x in d) + "\n")

    print(f"{len(linhas)} questoes -> {saida.name}")
    print(f"{len(descartes)} descartes -> {tsv.name}")
    for c, n in sorted(contador.items()):
        print(f"  {c}: {n}")
    sem_elo = [r["id"] for r in linhas if r["elos_max"] is None]
    if sem_elo:
        print(f"  sem contagem de elo no gabarito: {sem_elo}")


if __name__ == "__main__":
    main()
