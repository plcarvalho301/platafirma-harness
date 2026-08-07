#!/usr/bin/env python3
"""Junta o T2 (gold set simples) num unico JSON, pronto pra render.

Fontes:
- gold-t2-20260803.jsonl      -> pergunta, esperada (prosa), tipo, nota
- gold-t2-obraid-20260805.jsonl -> obra_ids casados, pontuavel, motivo
- rechave/quarentena-20260805.jsonl -> item excluido por obra sem chunk

Saida: /tmp/t2.json — lista de cadeiras, cada uma com suas perguntas.
"""
import json
from pathlib import Path

AQUI = Path(__file__).parent


# Titulo de catalogo (Anna's Archive/arquivo cru) -> titulo de leitura. So entra
# aqui o que precisa de limpeza; o resto passa direto.
TITULO_LIMPO = {
    "z39-19-2005r2010": "ANSI/NISO Z39.19-2005 (R2010) \u2014 Guidelines for Controlled Vocabularies",
    "Building_Ontologies_with_Basic_Formal_On": "Building Ontologies with Basic Formal Ontology",
    "The Intellectual Foundation of Information Organization -- Svenonius, Elaine -- Digital libraries and electronic publishing, 1st MIT Press -- The MIT -- isbn13 9780262194334 -- 0c56bc153bf168d2e0e0a9698fa463e1 -- Anna's Archive": "The Intellectual Foundation of Information Organization (Elaine Svenonius)",
    "A World Without Email -- Cal Newport -- null, null, 2021 -- Penguin Publishing Group -- 01df625471dd63018ce970fcf3a96b69 -- Anna's Archive": "A World Without Email (Cal Newport, 2021)",
    "Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive": "Team Topologies (Skelton & Pais, 2\u00aa ed., 2025)",
    "DMBOK": "DAMA-DMBOK",
    "mcp-spec-2026-07-28": "MCP Specification (28/07/2026)",
    "Release it!_ design and deploy production-ready software -- Michael T_ Nygard -- The pragmatic programmers, Raleigh, N_C, North Carolina, -- Pragmatic -- isbn13 9780978739218 -- 93af097dc316b957068154ab9d210307 -- Anna's Archive": "Release It! (Michael T. Nygard)",
    "Don't Make Me Think, Revisited_ A Common Sense Approach to -- Krug, Steve -- Voices That Matter, 3rd Edition, 2013 -- chenjin5_com \u4e07\u5343\u4e66\u53cb\u805a\u96c6\u5730 -- 8829b1f4be50f8eec5fbb20f207ebe55 -- Anna's Archive": "Don't Make Me Think, Revisited (Steve Krug, 3\u00aa ed., 2013)",
    "Heuristic_Summary1_A4_compressed": "10 Heur\u00edsticas de Nielsen (sum\u00e1rio A4)",
    "The Mom Test -- Rob Fitzpatrick -- ad8211428498baf5e6197a2579e4acf2 -- Anna's Archive": "The Mom Test (Rob Fitzpatrick)",
    "Information_Architecture_For_The_Web_And_Beyond_Fourth_Edition": "Information Architecture for the Web and Beyond (4\u00aa ed.)",
    "wellarchitected-framework-2024-06-27": "AWS Well-Architected Framework (jun/2024)",
    "2025_state_of_ai_assisted_software_development": "DORA \u2014 State of AI-Assisted Software Development 2025",
    "nist.sp.800-218": "NIST SP 800-218 (SSDF)",
    "Final_ OpenID Connect Core 1.0 incorporating errata set 2": "OpenID Connect Core 1.0 (errata set 2)",
    "nist.sp.800-57pt1r5": "NIST SP 800-57 Part 1 Rev. 5",
    "nist.sp.800-162": "NIST SP 800-162 (ABAC)",
    "Relat\u00f3rio Executivo_ A Transi\u00e7\u00e3o para a Criptografia P\u00f3s-Qu\u00e2ntica (PQC) e a Prote\u00e7\u00e3o das Infraestruturas Cr\u00edticas no Brasil": "Relat\u00f3rio Executivo \u2014 Transi\u00e7\u00e3o para Criptografia P\u00f3s-Qu\u00e2ntica no Brasil",
    "Security Engineering_ A Guide to Building Dependable -- Ross J_ Anderson [Anderson, Ross J_] -- 2010 -- Wiley -- 214b8251993da512c72cf9ba0da7837a -- Anna's Archive": "Security Engineering (Ross Anderson, 2010)",
    "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods": "Reciprocal Rank Fusion (Cormack et al.)",
    "M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation": "M3-Embedding (paper do BGE-M3)",
}


def limpar(t):
    if t is None:
        return None
    return TITULO_LIMPO.get(t, t)


base = {r["id"]: r for r in (json.loads(l) for l in open(AQUI / "gold-t2-20260803.jsonl"))}
obraid = {r["id"]: r for r in (json.loads(l) for l in open(AQUI / "gold-t2-obraid-20260805.jsonl"))}
quarentena = {r["id"]: r for r in (json.loads(l) for l in open(AQUI / "rechave/quarentena-20260805.jsonl"))}

ORDEM_CADEIRA = [
    "claudinho-conhecimento",
    "claudinha-gestao-estrategica",
    "claudinho-arquiteto",
    "claudinho-IA",
    "claudinha-produto",
    "claudinho-TI",
    "claudinho-seguranca",
]

cadeiras = {c: [] for c in ORDEM_CADEIRA}
for id_, r in base.items():
    c = r["cadeira"]
    q = {
        "id": id_,
        "pergunta": r["pergunta"],
        "tipo": r["tipo"],
        "esperada": limpar(r.get("esperada")),
        "nota": r.get("nota"),
        "pontuavel": True,
        "motivo_exclusao": None,
    }
    if id_ in quarentena:
        q["pontuavel"] = False
        q["motivo_exclusao"] = quarentena[id_]["motivo"]
    cadeiras.setdefault(c, []).append(q)

for c in cadeiras:
    cadeiras[c].sort(key=lambda q: q["id"])

saida = [{"cadeira": c, "perguntas": cadeiras[c]} for c in ORDEM_CADEIRA if cadeiras.get(c)]
json.dump(saida, open("/tmp/t2.json", "w"), ensure_ascii=False, indent=1)

total = sum(len(c["perguntas"]) for c in saida)
neg = sum(1 for c in saida for q in c["perguntas"] if q["esperada"] is None)
flag = sum(1 for c in saida for q in c["perguntas"] if q["nota"])
exc = sum(1 for c in saida for q in c["perguntas"] if not q["pontuavel"])
print(f"{total} perguntas, {neg} negativas, {flag} com ressalva, {exc} excluida(s) de pontuacao")
for c in saida:
    print(f"  {c['cadeira']}: {len(c['perguntas'])}")
