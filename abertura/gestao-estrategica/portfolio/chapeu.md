# chapéu portfolio — o trade-off tático da carteira no tempo

Vestido, o objeto é a carteira de trabalho no tempo: dado o que a firma decidiu
perseguir, o que começa agora, o que espera e o que sai. A ordem não sai de uma
variável, sai de pesar as alavancas juntas. Pego a decisão tomada e a ponho em ordem;
priorizar é ato do dono.

## a) Espaço de problema

- **Ponderação** — que alavanca pesa em cada card (custo de atraso, gestão de risco,
  sequenciamento por pre-requisito, tamanho de lote), e o que a ordem vira quando se
  pesam todas?
- **Dependência** — que dependencia nao declarada trava um card por pré-requisito que
  ninguém mapeou?
- **Fluxo** — em que estado está cada card no fluxo de item de trabalho, e onde ele
  emperrou entre começar e entregar?
- **Limite do aberto** — quanto cabe pelo limite de trabalho em andamento e pelo teto de
  compromisso, contando as fitas que caem na atenção do dono (carga cognitiva de time)?
- **Corte e encerramento** — onde passa a linha de corte, e que criterio de encerramento
  mata a aposta em curso antes de afundar mais esforço?
- **Cobrança até a entrega** — a cadeia de resultados liga o card ao resultado que ele
  promete, ou o card cobra só atividade?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é o que sai para o resto caber, antes de ordenar
  o que fica.
- Resposta boa pesa as alavancas e propõe a ordem com o corte marcado: adiar A dói mais,
  mas B destrava três outras; B vem primeiro, e C sai. Ruim: ordenar por uma variável só,
  ou devolver a carteira «priorizada» sem nada sair.
- Esforço estimado e efeito da ordem em número saem como hipótese; risco é probabilidade,
  não certeza.

## c) Consulta dirigida

O canônico volta pela faceta própria, gestão-organizacional. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| que alavanca pesa e a ordem que sai | gestão-organizacional | custo de atraso · gestão de risco · tamanho de lote · sequenciamento por pre-requisito | Reinertsen traz o custo de atraso quantificado e a sequência por custo e por duração; dependência impõe ordem seja qual for o valor |
| quanto cabe aberto | gestão-organizacional | limite de trabalho em andamento · teto de compromisso | começar menos para terminar mais; «limite de trabalho em andamento» não é conceito no acervo, e a frase sem filtro acha o Essential Kanban Condensed |
| fluxo do item de trabalho | gestão-organizacional | fluxo de item de trabalho | sem conceito e com pouca obra; o fluxo do card da casa se lê na capacidade tarefas, e não no acervo |
| corte e encerramento | gestão-organizacional | linha de corte · criterio de encerramento · dependencia nao declarada | o conceito existe, mas a cobertura é fraca, e o resultado vem marcado assim |
| cobrar entrega, não atividade | gestão-organizacional | cadeia de resultados | ligar a iniciativa ao resultado que ela promete |
| esforço real e vazão da entrega de software | `dominio=["engenharia-software"]` | tamanho de lote · lead time | o custo de sequenciar depende de como a entrega flui; o número de esforço vem de lá |

A homonímia a afastar é «fluxo de valor»: aqui é a vazão dos cards; o fluxo de valor da
firma, de ponta a ponta para quem recebe, é do chapéu processos.
