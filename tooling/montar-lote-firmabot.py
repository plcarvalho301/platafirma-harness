#!/usr/bin/env python3
"""Monta um prompt único (system + 34 blocos) a partir do prompt-firmabot.md e dos
34 retornos T0-*.json de resultados/G0-rag-base/. Cada bloco carrega só o `contexto`
daquela sonda -- sem misturar fontes entre perguntas, mesmo indo tudo num envio só.

Uso: python3 tooling/montar-lote-firmabot.py > /tmp/lote-firmabot.md
"""
import json, pathlib, sys

BASE = pathlib.Path(__file__).resolve().parent.parent
SYSTEM = (BASE / "avaliacao/gold-set-firmabot/prompt-firmabot.md").read_text()
RESULT_DIR = BASE / "avaliacao/gold-set-firmabot/resultados/G0-rag-base"

files = sorted(RESULT_DIR.glob("T0-*.json"), key=lambda p: int(p.stem.split("-")[1]))

out = [SYSTEM.strip(), "", "---", "",
       f"{len(files)} perguntas abaixo. Cada uma é independente: responda usando só as",
       "fontes do PRÓPRIO bloco dela. Não use fonte de um bloco pra responder outro,",
       "e não deixe a resposta de um bloco influenciar a de outro. Numere as respostas",
       "igual à numeração das perguntas.", "", "---"]

total_chars = len(SYSTEM)
for f in files:
    data = json.loads(f.read_text())
    n = data["n"]
    pergunta = data["pergunta"]
    contexto = data["retorno"]["contexto"]
    bloco = f"\n## Pergunta {n}\n\n{pergunta}\n\nFontes:\n\n{contexto}\n"
    out.append(bloco)
    total_chars += len(bloco)

sys.stderr.write(f"total: {total_chars} chars (~{total_chars//4} tokens estimados)\n")
print("\n".join(out))
