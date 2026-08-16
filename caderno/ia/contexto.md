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

## Custo de janela — o pacote de abertura é miolo de loop
- Abertura da cadeira IA custa **16.395 tokens** (persona 1.485 · manifesto 2.829 ·
  TODA-CADEIRA 5.930 · org 6.151), sem mesa e sem fila. Medido 16/08/2026 com
  `~/AI/.venv-harness` + `opt/tokenizers/qwen2.5.json`. Estimativa a olho errava por
  ~40%: pacote de abertura se mede, não se estima.
- Dentro do org, só **805 tokens** servem à abertura (cabeçalho, tabela de ocupação,
  capabilities); os outros 5.346 são regra de execução datada.
- Token de abertura é prefill e é barato; **round-trip de tool call é o caro**. Verbo
  novo na abertura custa latência paga pelo dono a cada fita — preferir uma chamada
  que resolve a N chamadas que compõem.
- Ordem de injeção estável → volátil: carimbo (`sha`, `sincronizado_em`) no começo do
  prompt quebra cache de prefixo a cada fita.
