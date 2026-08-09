"""Desvio conceitual: quão longe, na teia, a obra recuperada ficou da esperada.

Por que existe. O gold rotula recuperação como acerto/erro binário, e num corpus denso
isso mente: a obra "errada" costuma ser vizinha temática da certa, e a resposta que ela
sustenta pode ser correta e só um pouco pior. Binário joga essa diferença fora. Este
módulo devolve a DISTÂNCIA — e, com ela, o caminho percorrido.

O que NÃO faz, de propósito:

  - não julga se o vazamento foi bom ou ruim. Isso não está no grafo; sai da pergunta de
    avaliação. Aqui só se mede o quanto desviou;
  - não colapsa o desvio num escore único ponderado por tipo de aresta. Peso por tipo
    seria número inventado: ninguém mediu que `instrumental` vale 1,5 `generica`. Sai o
    número de saltos MAIS a composição do caminho, e quem pondera decide depois, com
    dado;
  - não expande consulta. Recuperação só pode subir por aresta hierárquica (ont:0080);
    MEDIR distância pode usar as nove famílias, porque proximidade temática é
    exatamente o que se quer medir. São usos distintos do mesmo grafo.

Insumo do pruning: `caminho` traz as arestas atravessadas. Aresta que só aparece em
vazamento julgado ruim é candidata a poda; a que aparece em vazamento bom está legítima.
O julgamento vem de fora — este módulo entrega a evidência.

    python desvio_conceitual.py --esperada <sha|arquivo> --recuperada <sha|arquivo>
    python desvio_conceitual.py --stats
"""

from __future__ import annotations

import argparse
import json
import os
from collections import deque

import psycopg

HIERARQUICAS = ("generica", "partitiva", "instancia")

SEM_CAMINHO = None  # distância infinita: nenhuma cadeia de arestas liga os dois


def conectar() -> psycopg.Connection:
    env = {}
    caminho = os.path.expanduser("~/AI/var/deploy-env/rag.env")
    if os.path.exists(caminho):
        for linha in open(caminho):
            if "=" in linha and not linha.startswith("#"):
                k, _, v = linha.strip().partition("=")
                env[k] = v
    return psycopg.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=env.get("POSTGRES_PORT", "5432"),
        dbname=env.get("POSTGRES_DB", "rag_extractor"),
        user=env.get("POSTGRES_USER", "rag"),
        password=env.get("POSTGRES_PASSWORD", ""),
    )


def carrega_teia(conn) -> tuple[dict, dict]:
    """Grafo não-direcionado da teia + slug/domínio por conceito.

    Não-direcionado de propósito: desvio é simetria de proximidade, não de subsunção.
    Quem precisa da direção (expansão de consulta) usa outro predicado, não este.
    """
    with conn.cursor() as cur:
        cur.execute("select id::text, slug, mais_amplo_id::text, mais_amplo_tipo from acervo.conceito")
        linhas = cur.fetchall()
    adj: dict[str, list[tuple[str, str]]] = {i: [] for i, _, _, _ in linhas}
    meta = {i: {"slug": s} for i, s, _, _ in linhas}
    for i, _, pai, tipo in linhas:
        if pai:
            adj[i].append((pai, tipo or "?"))
            adj.setdefault(pai, []).append((i, tipo or "?"))
    return adj, meta


def conceitos_da_obra(conn, chave: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """select t.conceito_id::text from acervo.obra_trata_de t
               join acervo.obra o on o.id = t.obra_id
               where o.arquivo = %s or o.objeto_id = %s or o.id::text = %s""",
            (chave, chave, chave),
        )
        return [r[0] for r in cur.fetchall()]


def caminho_minimo(adj: dict, origem: str, destino: str) -> list[tuple[str, str]] | None:
    """BFS não-ponderado. Sem peso por tipo — ver docstring do módulo."""
    if origem == destino:
        return []
    anterior: dict[str, tuple[str, str]] = {origem: ("", "")}
    fila = deque([origem])
    while fila:
        atual = fila.popleft()
        for viz, tipo in adj.get(atual, ()):
            if viz in anterior:
                continue
            anterior[viz] = (atual, tipo)
            if viz == destino:
                caminho = []
                no = viz
                while no != origem:
                    pai, tipo_aresta = anterior[no]
                    caminho.append((no, tipo_aresta))
                    no = pai
                return list(reversed(caminho))
            fila.append(viz)
    return SEM_CAMINHO


def desvio(adj: dict, meta: dict, esperados: list[str], recuperados: list[str]) -> dict:
    """Desvio = o MENOR caminho entre qualquer conceito esperado e qualquer recuperado.

    Mínimo, não média: a pergunta é "o que se recuperou tem alguma relação com o que se
    devia?", e uma relação basta para o vazamento não ser cego.
    """
    if not esperados or not recuperados:
        return {"saltos": None, "motivo": "obra sem conceito classificado", "caminho": []}
    if set(esperados) & set(recuperados):
        return {"saltos": 0, "motivo": "conceito em comum", "caminho": []}

    melhor = None
    for e in esperados:
        for r in recuperados:
            c = caminho_minimo(adj, e, r)
            if c is not None and (melhor is None or len(c) < len(melhor[0])):
                melhor = (c, e, r)
    if melhor is None:
        return {"saltos": None, "motivo": "sem caminho na teia", "caminho": []}

    caminho, origem, _ = melhor
    tipos = [t for _, t in caminho]
    return {
        "saltos": len(caminho),
        "motivo": "caminho na teia",
        "de": meta[origem]["slug"],
        "caminho": [{"conceito": meta[n]["slug"], "aresta": t} for n, t in caminho],
        "hierarquicas": sum(1 for t in tipos if t in HIERARQUICAS),
        "associativas": sum(1 for t in tipos if t not in HIERARQUICAS),
    }


def stats(adj: dict) -> dict:
    """Quanto da teia é navegável hoje. Sem isto, desvio None vira 'erro' na leitura."""
    nos = list(adj)
    vistos: set[str] = set()
    componentes = []
    for n in nos:
        if n in vistos:
            continue
        fila, tam = deque([n]), 0
        vistos.add(n)
        while fila:
            x = fila.popleft()
            tam += 1
            for viz, _ in adj.get(x, ()):
                if viz not in vistos:
                    vistos.add(viz)
                    fila.append(viz)
        componentes.append(tam)
    total_pares = len(nos) * (len(nos) - 1) // 2
    ligados = sum(c * (c - 1) // 2 for c in componentes)
    return {
        "conceitos": len(nos),
        "componentes": len(componentes),
        "maior_componente": max(componentes),
        "isolados": sum(1 for c in componentes if c == 1),
        "pares_com_caminho": round(ligados / total_pares, 4) if total_pares else 0.0,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--esperada", help="sha256 ou arquivo da obra do gabarito")
    p.add_argument("--recuperada", help="sha256 ou arquivo da obra que voltou")
    p.add_argument("--stats", action="store_true", help="navegabilidade da teia")
    a = p.parse_args()

    with conectar() as conn:
        adj, meta = carrega_teia(conn)
        if a.stats or not (a.esperada and a.recuperada):
            print(json.dumps(stats(adj), ensure_ascii=False, indent=2))
            return
        r = desvio(adj, meta, conceitos_da_obra(conn, a.esperada), conceitos_da_obra(conn, a.recuperada))
        print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
