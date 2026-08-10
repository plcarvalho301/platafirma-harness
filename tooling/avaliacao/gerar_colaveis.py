#!/usr/bin/env python3
"""Deriva avaliacao/perguntas-colaveis.md do gabarito. Regenera; nao se edita a mao.

    python3 tooling/avaliacao/gerar_colaveis.py
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GAB = RAIZ / "avaliacao/gabarito.jsonl"
OUT = RAIZ / "avaliacao/perguntas-colaveis.md"

ORDEM = [
    ("T3-multistep", None, "Multistep — 30",
     "Enunciado de varios passos, com alinea. E o estrato que mais custa a responder "
     "e o que mais separa arm bom de arm ruim."),
    ("T2-cadeiras", "complexa", "T2 complexas — 40",
     "Coletadas nas cadeiras e validadas pelo dono em 03/08. Pergunta de dominio que "
     "exige juntar mais de uma fonte."),
    ("T2-cadeiras", "simples", "T2 simples — 40",
     "Mesma coleta, resposta direta. Servem de piso: arm que erra aqui nao vale medir "
     "no resto."),
]


def main():
    itens = [json.loads(l) for l in GAB.read_text().splitlines() if l.strip()]
    L = [
        "# Perguntas do gabarito, em bloco colavel",
        "",
        "Derivado de `gabarito.jsonl` por `tooling/avaliacao/gerar_colaveis.py`.",
        "Nao editar aqui: pergunta se corrige no gabarito e este arquivo se regenera.",
        "",
        "Cada bloco e uma pergunta inteira, pronta para colar no prompt. O alvo nao entra:",
        "quem responde nao pode ver o gabarito.",
        "",
        "As 118 do estrato T1 ficam de fora de proposito — sao auto-geradas a partir do",
        "`section_id` e existem para a bancada casar por codigo, nao para alguem responder.",
        "",
    ]
    for estrato, tipo, titulo, nota in ORDEM:
        sel = [x for x in itens if x["estrato"] == estrato and (tipo is None or x["tipo"] == tipo)]
        L += [f"## {titulo}", "", nota, ""]
        for i, x in enumerate(sel, start=1):
            marca = "" if x["pontuavel"] else "  · **nao pontuavel**"
            cab = f"**{i:02d}. `{x['id']}`**{marca}"
            if not x["pontuavel"] and x.get("nota"):
                cab += f" — {x['nota']}"
            L += [cab, "", "```", x["pergunta"].rstrip(), "```", ""]
    OUT.write_text("\n".join(L))
    print(f"{OUT}: {sum(1 for l in L if l == '```') // 2} perguntas")


if __name__ == "__main__":
    main()
