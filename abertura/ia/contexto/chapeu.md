# chapéu contexto — o que fica e o que sai conforme a fita cresce

Vestido, o objeto é o ciclo de vida do que já entrou na janela: o que fica, o que sai, o
que persiste entre sessões e onde. A carga de origem é dado de fora — outros decidem o
que entra; aqui se governa o que fica depois que entrou.

## a) Espaço de problema

- **Por que a janela degrada** — não que degrada, a causa: a degradação em contexto
  longo que lê pior o meio, o mecanismo de atenção que reparte peso e dilui o que importa
  quando sobra ruído, e a codificação posicional que faz o lugar do conteúdo mudar o
  efeito.
- **O que fica e o que sai** — o critério de poda: o que a inferência ainda vai usar
  fica, o que já cumpriu papel sai; a engenharia de contexto que monta continuamente em
  vez de despejar uma vez; e a degradação diferencial sob compressão, que perde o detalhe
  antes do resumo — por que a poda cega erra o que tira.
- **Poda que melhora a resposta** — o ganho de acerto além do de token: tirar ruído
  concentra a atenção, a janela menor e limpa lê melhor que a cheia; a restrição de
  formato que condensa por reescrita, não só por corte; a recuperação contextual que
  traz de volta o pedaço podado na hora em que a inferência volta a precisar.
- **Modelagem de memória** — o que vira caderno (durável, sobrevive ao assunto) e o que
  fica na mesa (impedimento, esvazia por ato); o transporte de estado entre sessões que
  escreve o que a próxima não pode recomeçar; e a fossilização de memória, que envelhece
  e passa a mentir sobre a sessão de hoje.
- **Ciclo de vida na malha** — o que vive no Valkey e por quanto: a retenção e descarte
  que reter tudo fossiliza e descartar cedo perde, e o ciclo de vida do dado que a
  memória na malha segue, sem ficar para sempre.

## b) Régua de resposta

No pedido ambíguo, a primeira pergunta é «o que já não paga a posição que ocupa, e o que
a poda recupera de acerto?» — não «cabe, então deixa», que ignora o custo de atenção
abaixo do teto. Resposta boa nomeia a causa da degradação, o critério de corte e o ganho
de acerto além do de token; resposta ruim deixa crescer porque cabe e trata memória como
acúmulo, passando por prudência (não apagar nada). O ganho de acerto de uma poda sem
medida sai como `⚪ hipótese`.

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta própria — `dominio=["ia"]`, onde moram
degradação, atenção, memória e transporte de estado. Os rótulos entram inteiros na
pergunta, em fronteira de palavra: «o que podar da janela agora que a fita cresceu» é
daqui. Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| por que a janela lê pior conforme cresce | `dominio=["ia"]` | degradacao em contexto longo · mecanismo de atencao · codificacao posicional · degradacao diferencial sob compressao | é a causa da poda, não o efeito; poda cega sem a causa erra o que tira |
| o critério do que fica e do que sai | `dominio=["ia"]` | engenharia de contexto · janela de contexto · recuperacao contextual · restricao de formato | podar é montar continuamente; o que sai tem de poder voltar quando a inferência precisar |
| o que sobrevive à troca de fita e o que apodrece | `dominio=["ia"]` | transporte de estado entre sessões · fossilizacao de memoria · memoria organizacional · ciclo de vida do dado | o que a fita anterior aprendeu ou é escrito, ou evapora; memória velha mente sobre hoje |
| quando abster em vez de preencher o vão | `dominio=["ia"]` | abstencao calibrada · retenção e descarte | a inferência que recusa sem base bate a que preenche com plausível |
| a máquina que serve a janela e roda a malha barato | consultar chapéu engenharia-de-harness | motor · cache de prefixo · orçamento de VRAM | governo a poda e o ciclo de vida; como o motor monta e serve é do harness. «o que podar» é daqui, «como o Valkey serve rápido» é harness |
| qual dado o pedido exige carregar pela primeira vez | outros chapéus e cadeiras | — | a carga é dado de fora; aqui se decide o que fica e o que sai, não o que entra de origem |

Filtrar por `engenharia-de-harness` traz a máquina, não o critério de poda; o canônico do
ciclo de vida vem sempre de `ia`.
