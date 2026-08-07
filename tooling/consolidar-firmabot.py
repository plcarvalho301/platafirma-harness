#!/usr/bin/env python3
"""Consolida G0-rag-base (retrieval) + G0-claude-referencia (geração) num arquivo
só: pergunta, obras que apareceram na recuperação, resposta do gerador. Puramente
factual -- não classifica cobertura nem escolhe "a fonte certa": isso é da
claudinho-IA (cálculo das métricas é dela, protocolo-medicao.md).

Uso: python3 tooling/consolidar-firmabot.py > resultados/consolidado-T0.md
"""
import json, pathlib, sys

BASE = pathlib.Path(__file__).resolve().parent.parent
RESULT_DIR = BASE / "avaliacao/gold-set-firmabot/resultados"
RETRIEVAL_DIR = RESULT_DIR / "G0-rag-base"
GERACAO_DIR = RESULT_DIR / "G0-claude-referencia"

files = sorted(RETRIEVAL_DIR.glob("T0-*.json"), key=lambda p: int(p.stem.split("-")[1]))

print("# Consolidado T0 — recuperação + geração (claude-sonnet-5)\n")
print("Gerado por `tooling/consolidar-firmabot.py`. Junta `G0-rag-base` (o que o")
print("rag_search devolveu) com `G0-claude-referencia` (o que o gerador respondeu")
print("em cima disso). Lista de obras é só o que apareceu nas fontes — não é")
print("julgamento de qual é \"a\" fonte certa, isso é da claudinho-IA.\n")
print("---\n")

for f in files:
    data = json.loads(f.read_text())
    n = data["n"]
    pergunta = data["pergunta"]
    bloco = data["bloco"]

    obras = []
    for fonte in data["retorno"]["fontes"]:
        obra = fonte.get("obra") or f"[sem obra] {fonte['arquivo']}"
        if obra not in obras:
            obras.append(obra)

    resp_path = GERACAO_DIR / f"T0-{n}-resposta.md"
    resposta = resp_path.read_text().strip() if resp_path.exists() else "(sem resposta)"

    print(f"## {n}. {pergunta}  \n*(bloco {bloco})*\n")
    print("**Obras na recuperação:** " + "; ".join(obras) + "\n")
    print("**Resposta (claude-sonnet-5):**\n")
    print(resposta + "\n")
    print("---\n")
