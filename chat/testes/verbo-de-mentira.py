#!/usr/bin/env python3
"""Verbo de mentira — dubles dos estados que o verbo de verdade nao encena.

O card 459 mergeou e `chat despachar` existe: este arquivo DEIXOU de ser
substituto do verbo, e por isso saiu de worker/ (codigo de producao) para
testes/. O que ele ainda faz, e que o verbo real nao faz sob comando, e produzir
cota estourada, stream mudo e contrato quebrado — sem gastar um giro de
inferencia e sem depender de o motor estar de humor.

A integracao com o verbo REAL se prova em testes/prova-giro.py, na cadeira
inexistente: exit 2 sem JSON no stdout, que o worker traduz em erro estruturado.

Cumpre o contrato ao pe da letra e nada alem dele:

    chamada : <duble> despachar --cadeira <slug> --fita <id-ou-vazio> [--silencioso]
              corpo da mensagem em stdin
    stdout  : UMA linha JSON
    stderr  : uma linha JSON por passo do stream
    exit    : 0 sempre que houver JSON valido em stdout

O corpo da mensagem escolhe o comportamento, para o teste poder pedir o caminho
que quer sem variavel de ambiente:

    DUBLE:cota      estouro de cota, com horario de volta
    DUBLE:erro      falha do giro
    DUBLE:pendura   fica vivo e MUDO — e o caso do watchdog
    DUBLE:demora    ~8 s batendo no stream, para o giro atravessar uma queda
    DUBLE:longo     resposta grande, para provar o fatiamento
    DUBLE:vazio     estado ok com texto vazio
    DUBLE:lixo      escreve ruido em stdout e nao cumpre o contrato

"""

from __future__ import annotations

import argparse
import json
import sys
import time

RESPOSTA = """Respondo como a cadeira, e com formatacao de verdade.

| criterio | o que prova |
|---|---|
| 4 | tabela renderiza como tabela |
| 5 | fatia em limite de linha |

Passos:

1. primeiro
2. segundo

```python
def prova():
    return "bloco de codigo inteiro"
```
"""


def passo(nome: str, **resto) -> None:
    """Uma linha JSON por passo do stream — e o que o watchdog do worker observa."""
    print(json.dumps({"tipo": nome, **resto}), file=sys.stderr, flush=True)


def main() -> int:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("acao")
    p.add_argument("--cadeira", required=True)
    p.add_argument("--fita", default="")
    p.add_argument("--silencioso", action="store_true")
    args, _ = p.parse_known_args()

    corpo = sys.stdin.read()
    passo("init", cadeira=args.cadeira, fita=args.fita or None)

    id_fita = args.fita or f"fita-de-{args.cadeira}"
    reiniciada = not args.fita

    if "DUBLE:pendura" in corpo:
        passo("assistant")
        while True:  # mudo de proposito: quem mata e o watchdog
            time.sleep(3600)

    if "DUBLE:demora" in corpo:
        for i in range(8):
            passo("assistant", n=i)
            time.sleep(1.0)
        fim = {"estado": "ok", "texto": "demorei, mas respondi.", "id_fita": id_fita,
               "detalhe": "", "reiniciada": reiniciada}
        passo("result", estado="ok")
        print(json.dumps(fim, ensure_ascii=False))
        return 0

    if "DUBLE:lixo" in corpo:
        print("isto nao e json")
        return 0

    for i in range(3):
        passo("assistant", n=i)
        time.sleep(0.05)

    if "DUBLE:cota" in corpo:
        fim = {"estado": "cota", "texto": "", "id_fita": id_fita,
               "detalhe": "03:40 de amanha", "reiniciada": reiniciada}
    elif "DUBLE:erro" in corpo:
        fim = {"estado": "erro", "texto": "", "id_fita": id_fita,
               "detalhe": "a cadeira nao conseguiu abrir a fita", "reiniciada": reiniciada}
    elif "DUBLE:vazio" in corpo:
        fim = {"estado": "ok", "texto": "", "id_fita": id_fita,
               "detalhe": "", "reiniciada": reiniciada}
    elif "DUBLE:longo" in corpo:
        miolo = "\n\n".join(f"Paragrafo {i} — " + "palavra " * 60 for i in range(400))
        fim = {"estado": "ok", "texto": RESPOSTA + "\n\n" + miolo, "id_fita": id_fita,
               "detalhe": "", "reiniciada": reiniciada}
    else:
        fim = {"estado": "ok", "texto": RESPOSTA, "id_fita": id_fita,
               "detalhe": "", "reiniciada": reiniciada}

    if args.silencioso:
        fim["texto"] = ""
    passo("result", estado=fim["estado"])
    print(json.dumps(fim, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
