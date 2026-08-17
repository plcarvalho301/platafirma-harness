#!/usr/bin/env python3
"""Gera conceitos.json a partir de acervo.conceito — NAO se edita o JSON a mao.

Rotulo escrito a mao e segunda fonte, e segunda fonte diverge em silencio
(spec_montagem-de-sessao.md §7). Aqui o canonico e o id; rotulo e origem saem do
banco a cada geracao. `cross` e MEDIDO: dominio das obras que sustentam o conceito.

uso:  python3 personas/chapeus/politicas-publicas/.gerar-conceitos.py > \
        personas/chapeus/politicas-publicas/conceitos.json

Oculto de proposito: nao e chapeu e nao deve aparecer em listagem de chapeu.
"""
import json
import subprocess

BLOCOS = {
    "tecnica": ["estruturacao-de-problema", "politica-publica", "exigencia-sem-instrumento",
                "carga-prematura", "direcionamento-vs-implementabilidade", "plano-de-gabinete",
                "metis", "gap-desenho-realidade",
                "capacidade-estatal", "armadilha-de-capacidade", "capacidade-absortiva",
                "adaptacao-iterativa", "retencao-estrutural", "responsabilidade-de-traduzir",
                "legibilidade-do-sistema",
                "governanca-federada", "antinomia-de-coordenacao", "meta-governanca-normativa",
                "isomorfismo-institucional", "gradiente-de-isomorfismo-na-importacao",
                "nova-gestao-publica",
                "avaliacao-de-politica-publica", "requisito-verificavel", "gestao-por-metricas",
                "mudanca-de-comportamento", "orcamento-publico"],
    "politica": ["janela-de-politica", "isomorfismo-institucional",
                 "gradiente-de-isomorfismo-na-importacao", "nova-gestao-publica",
                 "producao-de-sentido", "porta-para-fora-porta-para-dentro",
                 "plano-de-gabinete", "metis", "armadilha-de-capacidade",
                 "antinomia-de-coordenacao", "governanca-federada",
                 "independencia-gerencial", "meta-governanca-normativa",
                 "fronteira-por-custo-de-transacao", "soberania-tecnologica",
                 "dependencia-de-fornecedor", "titularidade-do-core",
                 "capacidade-estatal"],
}

MEU_DOMINIO = "capacidade-estatal"

SQL = """
select c.slug, c.id, c.rotulo, coalesce(array_to_string(c.outros_rotulos,' / '),''),
       coalesce(string_agg(distinct d.slug, ','), ''), count(distinct t.obra_id)
from acervo.conceito c
left join acervo.obra_trata_de t on t.conceito_id = c.id
left join acervo.obra o on o.id = t.obra_id
left join acervo.dominio d on d.id = o.dominio_id
group by c.slug, c.id, c.rotulo, c.outros_rotulos;
"""

saida = subprocess.run(
    ["docker", "exec", "-i", "rag-extractor-pg", "psql", "-U", "rag", "-d", "rag_extractor",
     "-tAF|", "-c", SQL], capture_output=True, text=True, check=True).stdout

banco = {}
for linha in saida.strip().split("\n"):
    slug, cid, rotulo, alt, doms, obras = linha.split("|")
    banco[slug] = (cid, rotulo, alt, [d for d in doms.split(",") if d], int(obras))

doc = {
    "cadeira": "claudinho-politicas-publicas",
    "gerado_por": "personas/chapeus/politicas-publicas/.gerar-conceitos.py",
    "fonte": "acervo.conceito (rag-extractor-pg)",
    "canonico": "id. rotulo e origem sao transcricao gerada, nao fonte",
    "cross": "medido: true quando NENHUMA obra que sustenta o conceito e do dominio "
             "capacidade-estatal. null quando o conceito nao tem obra-ancora",
    "nota": "sao 3 chapeus — tecnica, politica, mentoria. So `tecnica` esta escrito "
            "(17/08/2026); os outros dois entram aqui quando forem redigidos. Conceito "
            "usado por mais de um chapeu se declara em cada um: declara USO, nao particao.",
    "lacunas": [
        "tecnica: teoria de mudanca — usada na materia, sem conceito no acervo (17/08/2026)",
        "politica: coalizao de defesa, ponto de veto, empreendedor de politica, captura "
        "regulatoria, accountability horizontal — o acervo e forte em Estado e fraco em "
        "processo politico (17/08/2026). Pedido de obra em aberto.",
    ],
    "blocos": {},
}

for chapeu, slugs in BLOCOS.items():
    itens = []
    for slug in slugs:
        cid, rotulo, alt, doms, obras = banco[slug]
        item = {"id": cid, "slug": slug, "rotulo": rotulo, "obras_ancora": obras,
                "origem": doms or None,
                "cross": None if obras == 0 else (MEU_DOMINIO not in doms)}
        if alt:
            item["outros_rotulos"] = alt
        itens.append(item)
    doc["blocos"][chapeu] = itens

print(json.dumps(doc, ensure_ascii=False, indent=2))
