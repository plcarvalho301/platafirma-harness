#!/usr/bin/env python3
"""Gera conceitos.json a partir de acervo.conceito — NAO se edita o JSON a mao.

Rotulo escrito a mao e segunda fonte, e segunda fonte diverge em silencio
(spec_montagem-de-sessao.md §7). Aqui o canonico e o id; rotulo e origem saem do
banco a cada geracao. `cross` e MEDIDO: dominio das obras que sustentam o conceito.

uso:  python3 personas/chapeus/IA/.gerar-conceitos.py > \
        personas/chapeus/IA/conceitos.json

Oculto de proposito: nao e chapeu e nao deve aparecer em listagem de chapeu.
"""
import json
import subprocess

BLOCOS = {
    "harness": ["engenharia-contexto", "composicao-da-janela-de-contexto", "janela-de-contexto",
                "degradacao-em-contexto-longo", "degradacao-diferencial-sob-compressao",
                "cache-de-prefixo", "orcamento-de-raciocinio", "orcamento-de-vram",
                "quantizacao", "degradacao-por-quantizacao", "restricao-de-formato",
                "descricao-como-interface", "erro-legivel-por-modelo", "skills",
                "juiz-modelo", "consciencia-de-avaliacao",
                "confundimento-de-ambiente-em-avaliacao", "validade-de-construto",
                "carga-cognitiva-extranea", "degradacao-declarada", "paridade-de-superficie"],
    "contexto": ["pipeline-rag", "recuperacao-densa", "recuperacao-semantica",
                 "recuperacao-contextual", "embeddings", "modelos-embedding",
                 "ranqueamento-multiestagio", "fusao-reciproca-de-rankings",
                 "relevancia-graduada", "abstencao-calibrada", "calibragem-de-confianca",
                 "rag-antes-de-fine-tuning", "estimativa-de-cobertura-por-nao-vistos",
                 "vizinho-plausivel", "fossilizacao-de-memoria",
                 "transporte-de-estado-entre-sessoes", "invalidacao-na-escrita",
                 "sinal-implicito-de-uso", "unidade-de-registro", "problema-do-vocabulario",
                 "forrageamento-de-informacao", "proveniencia-de-assercao"],
    "agente": ["agente-de-ia", "loop-agentico", "mediacao-do-loop-agentico",
               "ferramenta-de-agente", "orquestracao-multi-agente", "quando-cabe-um-agente",
               "isolamento-de-contexto-por-delegacao", "assimetria-de-contexto",
               "custo-de-transferencia", "posse-exclusiva-de-tarefa", "criterio-de-parada",
               "invariante-de-laco", "erro-composto-de-trajetoria", "autonomia-e-custo-do-erro",
               "reversibilidade-de-acao", "operador-nao-humano", "menor-privilegio",
               "negar-por-padrao", "prompt-injection", "triagem-de-entrada",
               "mecanismo-de-coordenacao"],
    "inferencia": ["orcamento-de-vram", "quantizacao", "degradacao-por-quantizacao",
                   "pesos-do-modelo", "desenho-do-modelo-e-pesos", "lora-e-qlora",
                   "rede-neural", "mecanismo-de-atencao", "codificacao-posicional",
                   "cache-de-prefixo", "substrato-de-hospedagem", "recurso-indivisivel"],
}

MEU_DOMINIO = "ia"

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
    "cadeira": "claudinho-IA",
    "gerado_por": "personas/chapeus/IA/.gerar-conceitos.py",
    "fonte": "acervo.conceito (rag-extractor-pg)",
    "canonico": "id. rotulo e origem sao transcricao gerada, nao fonte",
    "cross": "medido: true quando NENHUMA obra que sustenta o conceito e do dominio ia. "
             "null quando o conceito nao tem obra-ancora e a origem nao e medivel",
    "nota": "conceito usado por mais de um chapeu e declarado em cada um: isto declara "
            "USO, nao particao. Sao 3 chapeus — harness, contexto, agente. `inferencia` "
            "nao e chapeu: e o MODO da cadeira e vive na POSTURA da base (#189, "
            "16/08/2026); o bloco fica como vocabulario declarado, sem chapeu que o "
            "carregue, e reabre quando inferencia local tiver consumidor rodando.",
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
