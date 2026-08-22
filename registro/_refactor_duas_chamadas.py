#!/usr/bin/env python3
"""Refatora o catálogo de peças para o fluxo de duas chamadas (abertura-novo-pedro/P2).

Não é peça servida — é o script que aplica a mudança de catálogo, uma vez, com
guarda de contagem (padrão do harness: read → assert → write). Roda uma vez e vai
ao commit junto com o resto; fica no repo como registro do que foi aplicado.

O que faz, e por quê (fonte: docs/abertura-de-sessao/abertura-novo-pedro/P2 - monta-sessao.md):

  1a chamada monta_sessao(cadeira)  -> serve gatilho.evento == "abertura"
     a) persona   b) oficio(tool-manifest-geral)  c) dono(conduta-dono)  d) caderno-head
  2a chamada monta_sessao(cadeira, chapeu=<slug>) -> serve gatilho.evento == "chapeu" + mesa
     a) chapeu  b) tool-manifest-cadeira  c) caderno-chapeu  d) risco  e) catalogo-chapeu  f) mesa ver

Deltas aplicados aqui:
  - tool-manifest-cadeira: evento abertura -> chapeu   (migra para a 2a chamada, P2 item b)
  - mesa:                  evento abertura -> chapeu   (2a chamada, P2 item f)
  - antirreabertura:       APOSENTADA                  (P2 item d: risco substitui o conceito)
  - risco:                 CRIADA, evento chapeu       (P2 item d, matriz de risco)
  - caderno-head:          CRIADA, evento abertura     (P2 1a item d — de onde saem os slugs)
  - caderno-chapeu:        CRIADA, evento chapeu       (P2 2a item c — papel na org por chapeu)
  - catalogo-chapeu:       CRIADA, evento chapeu       (P2 2a item e — candidato a subsumir; ver nota)

DECISOES DEIXADAS ABERTAS NO P2 (nao fecho aqui; ficam nomeadas para o TI/dono):
  - catalogo-<chapeu> subsumido no chapeu? O P2 marca "candidato". Criei a peca
    SEPARADA por ora, para que o refactor nao force a decisao. Se subsumir, apagar
    catalogo-chapeu.json e a peca vira secao do chapeu. Decisao de desenho do dono.
  - risco.md ainda nao tem conteudo (P4 - matriz-riscos.md, 0 bytes). A peca risco
    serve o arquivo; ate a matriz existir, sai `indisponivel` DECLARADO — que e o
    comportamento certo (ausencia declarada, nao peca vazia). Conteudo e da Carla.
"""
from __future__ import annotations

import json
import os
import sys

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
PECAS = os.path.join(RAIZ, "platafirma-harness", "registro", "pecas")


def carrega(nome: str) -> dict:
    with open(os.path.join(PECAS, f"{nome}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def grava(nome: str, obj: dict) -> None:
    caminho = os.path.join(PECAS, f"{nome}.json")
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"  gravado: {nome}.json")


def migra_evento(nome: str, de: str, para: str) -> None:
    """read -> assert -> write: so migra se o evento atual for exatamente `de`."""
    p = carrega(nome)
    atual = (p.get("gatilho") or {}).get("evento")
    assert atual == de, f"{nome}: evento esperado {de!r}, achei {atual!r} — abortando sem tocar"
    p["gatilho"]["evento"] = para
    grava(nome, p)
    print(f"  {nome}: evento {de} -> {para}")


def aposenta(nome: str) -> None:
    caminho = os.path.join(PECAS, f"{nome}.json")
    assert os.path.isfile(caminho), f"{nome}.json nao existe — nada a aposentar"
    os.rename(caminho, caminho + ".aposentado")
    print(f"  aposentada: {nome}.json -> {nome}.json.aposentado")


def cria(nome: str, obj: dict) -> None:
    caminho = os.path.join(PECAS, f"{nome}.json")
    assert not os.path.isfile(caminho), f"{nome}.json ja existe — nao sobrescrevo as cegas"
    grava(nome, obj)


def main() -> int:
    print("== 1. migracoes de evento (abertura -> chapeu) ==")
    migra_evento("tool-manifest-cadeira", "abertura", "chapeu")
    migra_evento("mesa", "abertura", "chapeu")

    print("== 2. aposentar antirreabertura (risco assume) ==")
    aposenta("antirreabertura")

    print("== 3. pecas novas ==")
    cria("caderno-head", {
        "id": "caderno-head",
        "dono": "claudinho-dados",
        "artefato": "verbo:mesa caderno {cadeira} head",
        "regime": "valor",
        "gatilho": {
            "evento": "abertura",
            "condicao": "sempre na 1a chamada: traz as heuristicas de escolha do chapeu e os slugs; e o que a 1a chamada devolve para o modelo decidir o chapeu",
        },
        "volatilidade": "morna",
        "teto_tokens": 900,
    })
    cria("risco", {
        "id": "risco",
        "dono": "claudinha-gestao-estrategica",
        "artefato": "platafirma-arquitetura@docs/abertura-de-sessao/abertura-novo-pedro/P4 - matriz-riscos.md",
        "regime": "valor",
        "gatilho": {
            "evento": "chapeu",
            "condicao": "ler antes de tratar risco: matriz de risco vivo. Fora da matriz e proposta de risco; proposta vetada nao e risco. Substitui o conceito de antirreabertura (P2 item d)",
        },
        "volatilidade": "morna",
        "teto_tokens": 800,
        "emenda": "antirreabertura",
    })
    cria("caderno-chapeu", {
        "id": "caderno-chapeu",
        "dono": "claudinho-dados",
        "artefato": "verbo:mesa caderno {cadeira} {chapeu}",
        "regime": "valor",
        "gatilho": {
            "evento": "chapeu",
            "condicao": "sempre na 2a chamada: o caderno do chapeu ativo, onde o papel na org entra (P2 2a item c)",
        },
        "volatilidade": "volatil",
        "teto_tokens": 1200,
    })
    cria("catalogo-chapeu", {
        "id": "catalogo-chapeu",
        "dono": "claudinho-IA",
        "artefato": "platafirma-harness@personas/chapeus/{cadeira}/catalogo-{chapeu}.md",
        "regime": "indice",
        "gatilho": {
            "evento": "chapeu",
            "condicao": "2a chamada: catalogo de existencia do dominio do chapeu (P2 2a item e). CANDIDATO A SUBSUMIR no proprio chapeu — decisao de desenho do dono ainda aberta",
        },
        "volatilidade": "volatil",
        "teto_tokens": 250,
    })

    print("\nOK — catalogo refatorado. Rode `git status` para ver o delta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
