# caderno — IA · contexto, RAG e memória

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
- Corolário: o pacote se dimensiona pela MENOR janela em que ele vai rodar, não pela do
  modelo de nuvem. Os locais instalados declaram `context_length` 16.384 (`/api/tags`,
  07/09/2026), e a abertura de uma cadeira é 7.564 tokens na `ia` e 10.502 no
  `arquiteto` (`conta-abertura --tudo`): metade da janela gasta antes da primeira
  palavra do dono, com o histórico da fita ainda por entrar. Enquanto o pacote crescer
  contra a janela do Claude, "trocar de modelo" continua verdadeiro no papel e falso na
  primeira fita longa — a troca só é real se o orçamento de abertura couber na janela
  menor com folga para a conversa.
- Composição medida em 07/09/2026 (cadeira `ia`, abertura COM pergunta, 8.194 tokens):
  conduta do dono 4.476 (54,6%) · ofício 1.495 (18,2%) · mesa 1.188 (14,5%) · persona 744
  (9,1%) · alias 106 · índice de cadernos 83 · `acervo-consultado` 102 (1,2%). O RAG de
  obras deixou de ser o gasto que se corta — o portão de cobertura (arq:0101 R5) já o
  retém quando o sinal fica abaixo do piso, e os 28% que a bibliografia da casa ainda
  cita são o TETO de quando ele serve, não a média. O que sobrou é texto de conduta:
  abertura mínima que corte ofício, alias e índice fica em ~5,2k (36% a menos) e o
  `dono.md` segue sendo metade do pacote. Antes de vender ganho de abertura, medir QUAL
  peça paga — a peça óbvia já foi podada por outro mecanismo.

## Golden record que só sabe CRIAR acumula erro até virar carta

Ferramenta de curadoria costuma nascer com o ato de inserir e a régua formal em volta
dele (plano seco, conferências, export), e sem os atos de CORRIGIR e RETIRAR. O efeito
não é ergonômico, é de conteúdo: nó com definição errada não tem caminho de conserto,
então dura — e o custo aparece longe, como discussão entre cadeiras sobre um defeito
que ninguém podia consertar sozinho. Antes de aceitar "está ruim mas foi assim que
entrou", conferir se o ato de correção existe; não existindo, isso é a demanda, e a
correção pontual é o sintoma.

Corolário para quando a correção tem de sair na mão: antes de retirar um nó, separar o
que o cascade leva entre DERIVADO e CURADO. Derivado (top-k por similaridade, prior de
seção, qualquer coisa que um recálculo refaz) pode ir junto sem perda. Curado (lastro
de obra, classificação de gente) tem de ser repontado ANTES — e a FK que trava o delete
até isso acontecer é feature, não obstáculo. Subsumir também não é esquecer: o termo
que sai do golden record vira rótulo alternativo do que fica, senão quem procura pelo
nome antigo não acha nada.

## A sessão se registra no ATO de nascer, nunca na volta pela camada que a consome

Quem cunha o identificador tem o dado na mão; quem o consome, não. Registrar o estado
da sessão na volta — na porta, no adaptador, em quem recebe — abre uma janela do
tamanho do resto da montagem mais um round-trip, e dentro dela a fita já carrega um id
legítimo que ninguém do outro lado sabe de quem é. A janela não aparece em teste: quem
abre PELA camada que registra nunca a vê, e quem abre pelo caminho direto falha longe
dali, num verbo qualquer que só sabe dizer "não sei quem está operando". Duas vias de
abertura, uma só registrando, e a assimetria é invisível de dentro de cada uma.

Régua: **o ato que cria a entidade grava o estado dela, síncrono, antes de devolver** —
e cria como PRIMEIRA ação, não depois do trabalho caro. Assíncrono aqui não serve mesmo
sendo barato: devolver o pacote antes de a chave existir põe a primeira chamada da fita
exatamente na janela que se quer fechar.

Medido e corrigido em 07/09/2026 (`platafirma-harness@6d25443`): `monta-sessao` cunhava
o `sessao_id` no FIM da montagem e o `SET sessao:{id}` morava só no caminho da tool, de
modo que abertura por CLI direto (fita do chat e fábrica) nascia sem registro.
