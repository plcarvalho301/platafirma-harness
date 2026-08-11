# caderno — claudinho-IA · contexto, RAG e memória

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno contexto`).

## Régua de leitura do retorno
- `cobertura` reflete `max(scores)` do top-k — não confirma que a obra-alvo entrou.
- Fonte que não trate do conceito exato perguntado não serve, ainda que o rótulo diga "boa".

## Armadilhas medidas
- Pergunta em inglês, sem número embutido, recupera melhor neste corpus: identificador
  numérico faz o braço de identificador promover coincidência numérica.
- Número de acervo nunca sai de SQL na mão nem de memória — `acervo escada` é o instrumento.
- Dimensão igual não prova espaço de embedding igual: `bge-m3` e `Qwen3-Embedding-0.6B`
  são ambos 1024-d. Conferir o par (modelo, backend) em `index_meta`.

## Propriedade (dono, 10/08/2026)
- O RAG é meu, ponta a ponta. claudinho-conhecimento é USUÁRIO do RAG, não dono de
  parte dele: não se pede aceite, parecer nem validação a ele em nada do RAG —
  ingestão, trilho, ajuste, documentação de uso.
- Vale contra o reflexo de tratar acervo↔RAG como remit compartilhado: o acervo é
  matéria dele; o motor que o indexa e recupera é minha.
