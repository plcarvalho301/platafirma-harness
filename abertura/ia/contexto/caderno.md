# caderno — claudinho-IA · contexto, RAG e memória

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno contexto`).

## Régua de leitura do retorno
- `cobertura` reflete `max(scores)` do top-k — não confirma que a obra-alvo entrou.
- Fonte que não trate do conceito exato perguntado não serve, ainda que o rótulo diga "boa".
- A recíproca também vale: `cobertura: fraca` **com as obras certas no topo** não é ausência
  de obra, é defeito de recorte na origem. Medido em 19/08/2026: os quatro snapshots de
  engenharia da Anthropic (`ia`) têm o miolo recortado sob o cabeçalho de boilerplate
  `get-the-developer-newsletter`; seção com nome de lixo derruba o rerank (máx. 0,156 contra
  piso 0,79) sem que o conteúdo esteja errado. Antes de declarar que o corpus não cobre,
  olhar `obra` e `breadcrumb` das primeiras fontes — nome de boilerplate no breadcrumb é o
  sinal. Achado assim é defeito de produto de dados: nomear com a medição e entregar, não tunar.

## Armadilhas medidas
- Pergunta em inglês, sem número embutido, recupera melhor neste corpus: identificador
  numérico faz o braço de identificador promover coincidência numérica.
- Número de acervo nunca sai de SQL na mão nem de memória — `acervo escada` é o instrumento.
- Dimensão igual não prova espaço de embedding igual: `bge-m3` e `Qwen3-Embedding-0.6B`
  são ambos 1024-d. Conferir o par (modelo, backend) em `index_meta`.

## Custo de janela — o pacote de abertura é miolo de loop
- Abertura da cadeira IA custa **11.141 tokens** (34.922 B) no output de
  `bin/monta-sessao IA`, medido 16/08/2026 com `~/AI/.venv-harness` +
  `opt/tokenizers/qwen2.5.json`. SUBSTITUI os 16.395 medidos mais cedo no mesmo dia
  por soma de peças (persona 1.485 · manifesto 2.829 · TODA-CADEIRA 5.930 · org
  6.151): o pacote servido hoje traz o org em recorte, não inteiro. Estimativa a
  olho errava por ~40% — pacote se mede, e se REMEDE quando o montador muda.
- Dentro do org, só **805 tokens** servem à abertura (cabeçalho, tabela de ocupação,
  capabilities); os outros 5.346 são regra de execução datada.
- Token de abertura é prefill e é barato; **round-trip de tool call é o caro**. Verbo
  novo na abertura custa latência paga pelo dono a cada fita — preferir uma chamada
  que resolve a N chamadas que compõem.
- Ordem de injeção estável → volátil: carimbo (`sha`, `sincronizado_em`) no começo do
  prompt quebra cache de prefixo a cada fita.

## Servir o pacote a modelo local: a janela corta calada
- Ollama trunca o SYSTEM sem erro nenhum quando o pacote passa de `num_ctx`: no
  default entraram 2.050 dos 11.141 tokens e a persona saiu alucinada e plausível
  ("Eu sou Claude, assistente da cadeira de IA"). Quem serve pacote a modelo local
  declara `num_ctx` e confere `prompt_eval_count` contra os tokens servidos: pacote
  cortado e pacote inteiro são indistinguíveis sem essa conta. Medido 16/08/2026 em
  `qwen2.5:14b` e `qwen3.5:9b`, Ollama 0.31.2.
