#!/usr/bin/env python3
"""Gera o estrato de gabarito da EXPANSÃO — o instrumento que o gold canônico não alcança.

Por que existe: medido em 13/08/2026 contra o gabarito canônico, das 228 perguntas 38 casam
algum conceito declarado e só 14 têm conceito com pai hierárquico; no estrato
T1-determinístico, zero. Um ganho de 20% nessas 14 move a métrica global cerca de 1 p.p. —
dentro do ruído. A régua ("sem delta contra o gold, não promove") está certa e o instrumento
não a alcança: aplicada como está, ela reprova a expansão por AUSÊNCIA DE SINAL, que é coisa
diferente de ausência de efeito.

O que este estrato mede, e só ele: **travessia**. A pergunta usa o rótulo do conceito
ESTREITO; a resposta declarada está numa obra que trata do conceito que o CONTÉM e não trata
do estreito. É exatamente o caso em que sinônimo não ajuda (o vocabulário já está no vetor de
metadados) e só subir na árvore alcança.

Honestidade, e ela não é rodapé:

- É gold **sintético**, construído da própria rede que a expansão consome. Mede o MECANISMO
  (a travessia alcança a obra do pai?), não a naturalidade da pergunta de usuário. Não
  substitui pergunta real e não vira número de vitrine.
- É conjunto de TUNING enquanto o peso do braço for escolhido olhando para ele.
- O par (filho, pai) só entra quando a obra do pai NÃO trata do filho. Sem esse corte, a
  busca acha a obra sem expandir nenhuma e o estrato mediria o braço vetorial de novo.

Uso:
    python3 gerar-estrato-expansao.py > avaliacao/estrato-expansao.jsonl
"""

import json
import subprocess
import sys

SQL = """
SELECT f.slug, f.rotulo, f.mais_amplo_tipo, p.rotulo, o.titulo
  FROM acervo.conceito f
  JOIN acervo.conceito p        ON p.id = f.mais_amplo_id
  JOIN acervo.obra_trata_de tp  ON tp.conceito_id = p.id
  JOIN acervo.obra o            ON o.id = tp.obra_id
  JOIN acervo.impressao i       ON i.obra_id = o.id AND i.estado = 'servindo'
 WHERE f.mais_amplo_tipo IN ('generica','partitiva','instancia')
   AND NOT EXISTS (SELECT 1 FROM acervo.obra_trata_de tf
                    WHERE tf.conceito_id = f.id AND tf.obra_id = o.id)
 ORDER BY f.slug, o.titulo
"""

MOLDE = {
    "generica": "O que o acervo traz sobre {rotulo}?",
    "partitiva": "Onde {rotulo} se encaixa, e o que a obra diz a respeito?",
    "instancia": "O que se sabe sobre {rotulo}?",
}


def main() -> int:
    r = subprocess.run(
        ["docker", "exec", "-i", "rag-extractor-pg", "psql", "-U", "rag", "-d",
         "rag_extractor", "-At", "-F", "\t", "-c", SQL],
        capture_output=True, text=True,
        env={"DOCKER_HOST": "unix:///run/user/1001/docker.sock", "PATH": "/usr/bin:/bin"})
    if r.returncode:
        print(r.stderr, file=sys.stderr)
        return 1

    por_conceito: dict[str, dict] = {}
    for linha in r.stdout.splitlines():
        if not linha.strip():
            continue
        slug, rotulo, familia, pai, titulo = linha.split("\t")
        e = por_conceito.setdefault(slug, {
            "id": f"expansao-{slug}",
            "estrato": "T4-expansao",
            "tipo": "travessia",
            "pergunta": MOLDE[familia].format(rotulo=rotulo),
            "alvo_section_id": None,
            "alvo_obras": [],
            "relevancia": "positiva",
            "pontuavel": True,
            "familia_da_aresta": familia,
            "conceito": slug,
            "conceito_mais_amplo": pai,
            "origem": "gerado de acervo.conceito por gerar-estrato-expansao.py; gold "
                      "sintetico de MECANISMO, nao pergunta de usuario",
        })
        if titulo not in e["alvo_obras"]:
            e["alvo_obras"].append(titulo)

    for e in por_conceito.values():
        print(json.dumps(e, ensure_ascii=False))
    print(f"{len(por_conceito)} perguntas de travessia", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
