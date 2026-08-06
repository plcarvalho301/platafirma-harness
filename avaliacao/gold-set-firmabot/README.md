# Gold set — firmabot

Instrumento de avaliação do RAG da PlataFirma. Pasta autocontida: perguntas, procedimento e
resultados moram aqui, não em `docs/`.

    procedimento.md            protocolo de execução, congelado
    perguntas-simples.md       34 sondas (bloco A conceitual + bloco B dicionário estrito)
    perguntas-complexas.md     multi-hop — não desenhado
    t0_sonda_34.py             executor
    resultados/G0-rag-base/    recuperação pura (rag_search), sem gerador
    resultados/G0-<modelo>/    geração local, um diretório por modelo

`G0` é o degrau base da escada de ablação. Cada diretório de resultado carrega um
`carimbo.md` com o estado do ambiente que o produziu — resultado sem carimbo não é
comparável com nenhum outro, nem com ele mesmo repetido depois.

Fonte canônica das perguntas: `platafirma-conhecimento/rag/docs/gold-set-firmabot.md`.
Validação dos termos do bloco B como vocabulário canônico é de claudinho-conhecimento;
enquanto não validados, os alvos são proposta, não gabarito.
