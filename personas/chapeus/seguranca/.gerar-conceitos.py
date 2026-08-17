#!/usr/bin/env python3
"""Gera conceitos.json a partir de acervo.conceito — NAO se edita o JSON a mao.

Rotulo escrito a mao e segunda fonte, e segunda fonte diverge em silencio
(spec_montagem-de-sessao.md §7). Aqui o canonico e o id; rotulo e origem saem do
banco a cada geracao. `cross` e MEDIDO: dominio das obras que sustentam o conceito.

uso:  python3 personas/chapeus/seguranca/.gerar-conceitos.py > \
        personas/chapeus/seguranca/conceitos.json

Oculto de proposito: nao e chapeu e nao deve aparecer em listagem de chapeu.
"""
import json
import subprocess

BLOCOS = {
    "iam": ["iam", "autenticacao", "autorizacao", "autenticacao-multifator", "rbac", "abac",
            "federacao-de-identidade", "identidade-digital", "prova-de-identidade",
            "garantia-de-identidade", "criterio-de-identidade", "resolucao-de-identidade",
            "sortal-fornecedor-de-identidade", "acesso-privilegiado", "acesso-delegado",
            "superficie-unica-de-acesso", "menor-privilegio", "segregacao-de-funcoes",
            "necessidade-de-conhecer", "token-portador", "zero-trust",
            "credenciamento-de-seguranca", "operador-nao-humano", "triade-cid"],
    "privacidade": ["protecao-de-dados-pessoais", "base-legal-de-tratamento",
                    "controlador-e-operador", "avaliacao-de-impacto-a-privacidade",
                    "comunicacao-de-incidente-ao-titular", "dano-sem-vazamento",
                    "ciclo-de-vida-do-dado", "estados-do-dado", "retencao-e-descarte",
                    "tabela-de-temporalidade", "vida-util-do-sigilo", "sanitizacao-de-midia",
                    "classificacao-da-informacao", "regime-de-classificacao",
                    "necessidade-de-conhecer", "anonimizacao", "prevencao-de-vazamento",
                    "linhagem-de-dado", "falso-positivo-de-cobertura-por-jurisdicao"],
    "blueteam": ["superficie-de-ataque", "hardening", "piso-de-controle",
                 "linha-de-base-de-controles", "segmentacao-de-rede", "defesa-em-profundidade",
                 "zero-trust", "raio-de-alcance", "cadeia-de-suprimentos-de-software",
                 "transparencia-de-composicao", "gestao-de-vulnerabilidades",
                 "janela-de-exposicao", "imutabilidade-de-artefato",
                 "procedencia-do-que-esta-no-ar", "garantia-de-proveniencia",
                 "deriva-de-configuracao", "modelagem-de-ameacas",
                 "taticas-e-tecnicas-adversarias", "movimento-lateral", "gestao-de-incidentes",
                 "correlacao-de-eventos", "fadiga-de-alerta", "seguranca-por-concepcao",
                 "prompt-injection", "cadeia-de-ataque", "defesa-de-perimetro",
                 "inteligencia-de-ameacas", "engenharia-social", "ameaca-interna",
                 "inventario-ativos", "esteira-de-implantacao", "monitoramento-continuo",
                 "trilha-de-auditoria", "seguranca-ofensiva", "teste-de-intrusao",
                 "exercicio-adversarial", "regras-de-engajamento"],
    "cripto": ["criptografia", "primitiva-criptografica", "modulo-criptografico",
               "agilidade-criptografica", "transicao-pqc", "cifra-fim-a-fim",
               "algoritmo-de-estado", "gestao-de-chaves", "criptoperiodo", "cadeia-de-custodia",
               "raiz-de-confianca", "ancora-de-confianca", "cadeia-de-confianca",
               "modelo-de-confianca", "atestacao-confianca", "teia-de-confianca",
               "token-portador", "verificabilidade", "identidade-por-hash-de-conteudo"],
    "risco": ["gestao-de-risco", "tratamento-de-risco", "controle-de-seguranca",
              "tipologia-de-controles", "politica-de-seguranca-institucional",
              "avaliacao-de-conformidade", "maturidade-seguranca", "modelo-maturidade",
              "governanca", "gestao-de-terceiros", "objetivos-de-recuperacao",
              "exercicio-de-plano", "incidente-critico", "trilha-de-auditoria",
              "linha-de-base-de-controles"],
}

MEU_DOMINIO = "seguranca-privacidade"

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
    "cadeira": "claudinho-seguranca",
    "gerado_por": "personas/chapeus/seguranca/.gerar-conceitos.py",
    "fonte": "acervo.conceito (rag-extractor-pg)",
    "canonico": "id. rotulo e origem sao transcricao gerada, nao fonte",
    "cross": "medido: true quando NENHUMA obra que sustenta o conceito e do dominio "
             "seguranca-privacidade. null quando o conceito nao tem obra-ancora e a "
             "origem nao e medivel",
    "nota": "conceito usado por mais de um chapeu e declarado em cada um: isto declara "
            "USO, nao particao. `iam` e a head e nao tem chapeu (a head e o modo default "
            "da base); `risco` e gerencia sem chapeu por decisao do #189.",
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
