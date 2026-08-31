#!/usr/bin/env python3
"""Gera a tabela de rotas rótulo->chapéu do roteador determinístico (a), a partir do
golden record `acervo.conceito` cruzado com a curadoria da seção (b) de cada `chapeu.md`.

## Por que materializar, e não consultar na montagem

`acervo listar conceitos` lê o Postgres por `docker exec` (ver bin/_acervo/listar). Rodar
docker a cada montagem de sessão é custo proibido — o roteador precisa da tabela em
memória, barata. Então este gerador roda FORA da montagem (à mão, ou no deploy), e
materializa `abertura/rotas-chapeu.json`. `rotas_do_disco()` lê esse JSON, sem docker.

O golden record é a fonte de VERDADE do slug e dos gatilhos (rótulo canônico +
`outros_rotulos`). A seção (b) de cada `chapeu.md` é a curadoria de PERTENCIMENTO: qual
conceito dispara qual chapéu. Nenhum conceito entra numa rota por conta própria; entra
porque um chapéu o declarou na sua (b). Isso mantém a régua do (a): relação declarada,
não semelhança.

## Rótulo órfão é erro declarado, nunca silêncio

Rótulo escrito na (b) que não casa nenhum conceito do golden record vira aviso na saída
e código de saída != 0 com `--estrito`. Deriva de tabela mantida à mão (o modo de falha
que #250 existe para matar) só se pega se o gerador ACUSAR o descasamento, em vez de
gerar uma rota curta em silêncio.

## Contrato de saída (abertura/rotas-chapeu.json)

    { "<cadeira>": { "<slug-chapeu>": ["<gatilho>", ...], ... }, ... }

Gatilhos por chapéu: para cada rótulo da (b) que casou, o slug do conceito, o rótulo
canônico e cada `outros_rotulos`. Deduplicados, normalizados na leitura (não aqui — o
roteador normaliza com a mesma régua na hora de casar).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Fonte ÚNICA da régua de normalização: o próprio roteador. Importar em vez de recopiar
# garante que gerar e casar usem o mesmo _normaliza — recópia diverge no primeiro ajuste.
# Import qualificado pelo pacote (não `sys.path` na própria `recuperacao/`): o cliente REST
# usa import relativo (`..envelope`) e só resolve dentro do pacote `recuperacao`.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from recuperacao.roteador_chapeu import _normaliza  # noqa: E402
from recuperacao.adaptadores.motor_acervo_rest import conceitos as _conceitos_http  # noqa: E402

ABERTURA = os.path.join(RAIZ, "abertura")
SAIDA = os.path.join(ABERTURA, "rotas-chapeu.json")


def golden_record() -> list[dict]:
    """O golden record inteiro, via `GET /acervo/conceitos` (#2957, arq:0089 §2). Único
    ponto que toca a rede; roda uma vez, fora da montagem."""
    payload = _conceitos_http()
    return payload.get("itens", [])


def indice_por_rotulo(golden: list[dict]) -> dict[str, dict]:
    """rótulo normalizado -> conceito. Indexa pelo rótulo canônico E por cada
    `outros_rotulos`, para a (b) poder citar qualquer alias que o golden reconhece."""
    idx: dict[str, dict] = {}
    for c in golden:
        chaves = [c["rotulo"]]
        outros = c.get("outros_rotulos")
        if outros:
            # o --json serve outros_rotulos ora como str "a / b", ora lista; normaliza os dois
            partes = outros if isinstance(outros, list) else re.split(r"[/,]", outros)
            chaves.extend(partes)
        for k in chaves:
            n = _normaliza(k)
            if len(n) >= 3:
                idx.setdefault(n, c)
    return idx


def rotulos_da_secao_b(caminho_chapeu: str) -> list[str]:
    """Os rótulos da coluna 1 das tabelas na seção `## b)` de um chapeu.md. Lê só entre
    `## b)` e o próximo `## `, e só linhas de tabela cuja 1a célula não é cabeçalho nem
    separador. O travessão '—' na coluna Alternativo não entra: só a coluna Rótulo."""
    with open(caminho_chapeu, encoding="utf-8") as f:
        texto = f.read()
    m = re.search(r"^## b\).*?(?=^## )", texto, re.MULTILINE | re.DOTALL)
    if not m:
        return []
    rotulos = []
    for linha in m.group(0).splitlines():
        linha = linha.strip()
        if not linha.startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        if not celulas:
            continue
        primeira = celulas[0]
        if not primeira or primeira.lower() == "rótulo" or set(primeira) <= set("-: "):
            continue
        rotulos.append(primeira)
    return rotulos


def gatilhos(conceito: dict) -> list[str]:
    """Os disparadores de um conceito: rótulo canônico + outros_rotulos + o próprio slug.
    O roteador normaliza na hora de casar; aqui saem em forma legível, deduplicados."""
    saida = [conceito["rotulo"], conceito["slug"]]
    outros = conceito.get("outros_rotulos")
    if outros:
        partes = outros if isinstance(outros, list) else re.split(r"[/,]", outros)
        saida.extend(p.strip() for p in partes if p.strip())
    vistos, unicos = set(), []
    for g in saida:
        n = _normaliza(g)
        if n and n not in vistos:
            vistos.add(n)
            unicos.append(g)
    return unicos


def gerar(estrito: bool) -> tuple[dict, list[str]]:
    golden = golden_record()
    idx = indice_por_rotulo(golden)
    tabela: dict[str, dict[str, list[str]]] = {}
    orfaos: list[str] = []

    for cadeira in sorted(os.listdir(ABERTURA)):
        base = os.path.join(ABERTURA, cadeira)
        if not os.path.isdir(base):
            continue
        for chapeu in sorted(os.listdir(base)):
            chapeu_md = os.path.join(base, chapeu, "chapeu.md")
            if not os.path.isfile(chapeu_md):
                continue
            disparadores: list[str] = []
            vistos: set[str] = set()
            for rotulo in rotulos_da_secao_b(chapeu_md):
                conceito = idx.get(_normaliza(rotulo))
                if conceito is None:
                    orfaos.append(f"{cadeira}/{chapeu}: rótulo '{rotulo}' "
                                  f"não casa nenhum conceito do golden record")
                    continue
                for g in gatilhos(conceito):
                    n = _normaliza(g)
                    if n not in vistos:
                        vistos.add(n)
                        disparadores.append(g)
            if disparadores:
                tabela.setdefault(cadeira, {})[chapeu] = disparadores

    return tabela, orfaos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--estrito", action="store_true",
                    help="sai != 0 se houver rótulo órfão (para gate de deploy)")
    ap.add_argument("--dry-run", action="store_true",
                    help="imprime a tabela e os órfãos, não escreve o arquivo")
    args = ap.parse_args()

    tabela, orfaos = gerar(args.estrito)

    for o in orfaos:
        print(f"AVISO órfão: {o}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(tabela, ensure_ascii=False, indent=2))
    else:
        with open(SAIDA, "w", encoding="utf-8") as f:
            json.dump(tabela, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        n_rotas = sum(len(v) for v in tabela.values())
        n_gat = sum(len(r) for v in tabela.values() for r in v.values())
        print(f"escrito {os.path.relpath(SAIDA, RAIZ)}: "
              f"{len(tabela)} cadeiras, {n_rotas} chapéus, {n_gat} gatilhos, "
              f"{len(orfaos)} órfãos", file=sys.stderr)

    if args.estrito and orfaos:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
