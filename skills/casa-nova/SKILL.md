---
name: casa-nova
description: Use para procurar, gravar ou mover documento da casa nova (platafirma-casa), refinar ou executar story do E3650, ou saber onde algo mora e o que o dono decidiu. NÃO dispare para a casa atual, operação, incidente, jurídico ou forma do texto.
---

# Casa nova

A casa nova mora no repositório platafirma-casa e na Olaria. Esta skill diz onde cada coisa
da casa nova mora e o que o dono já decidiu sobre ela, sempre com a fonte. Quando nenhuma
fonte responde, ela diz «não achei» e para.

O que vale dentro do tombamento (fonte única, casa antiga como objeto, onde se grava) já
está na conduta, no cenário Tombando legado. Siga-o de lá; esta skill não o repete.

## As duas fontes

Procure nesta ordem, e cite de qual veio a resposta:

1. O catálogo gravado pela olaria no schema casa do banco (`infra rodar ontologia -- ler shape <classe>`
   ou `infra rodar ontologia -- listar shape`). É a fonte: o que ele diz vale sobre a outra.
2. Os cards da árvore do E3650: primeiro o corpo, que traz as decisões do dono já
   consolidadas, depois os comentários que seguem abertos. Guardam o que o dono decidiu e
   ainda não virou documento.

A planilha Ontologia da Casa está aposentada: não se lê nem se atualiza. Vão que nenhuma
fonte resolve vai ao dono como vão da classe.

## Onde cada coisa mora

O repositório se arruma por papel epistemológico:

- `instancias/<classe>/<chave>.md`: instâncias cujo texto vale em produção (onde a peça existe no próprio texto).
- `referencias/classes/<classe>.md`: páginas de catálogo das classes (uma por shape).
- `referencias/instancias/<classe>/<chave>.md`: documentos de referência de instâncias (como dicionários e peças cujo golden é código/infra).
- `verbetes/<dicionario>/<valor>.md`: verbetes dos valores de dicionário.
- Documento de chave numerada (registro de decisão, política interna) se chama
  `<número>-<trecho do título>.md`.
- Pasta nasce com o primeiro documento; não há README nem índice.

Não monte o caminho de cabeça: leia a classe na olaria.

## Ler a classe na olaria

Liste as classes com `infra rodar ontologia -- listar shape` e leia a da entidade com `infra rodar ontologia -- ler shape <slug>`, que devolve o YAML da classe com a `linhagem` inteira (da filha até a raiz) e as restrições `herdadas` das ancestrais.
Antes de concluir que algo não existe na árvore de uma classe, liste as descendentes com `infra rodar ontologia -- listar shape --filhas <slug>`; sem classe com o slug procurado, leia também as de nome parecido.
Antes de partir, renomear ou apagar uma classe, confira quem depende dela com `infra rodar ontologia -- listar shape --aponta-para <slug>`.
Para saber se uma classe, uma capacidade ou um estrato já gravados seguem o framework e passam no raciocinador, rode `infra rodar conferir -- ontologia <estrato:slug|capacidade:slug|classe>` (`conferir ontologia <alvo>`). Os campos que decidem a resposta:

- `golden` e `referencia`: o caminho do golden e o da referência; a classe pode
  declarar os dois;
- `tabela_do_golden`: a tabela do módulo onde mora o golden;
- `sem_forma`: o texto que diz por que a classe não tem documento;
- `mae`: a mãe da classe.

## Achar uma decisão do dono

1. Liste a árvore: `tarefas sub 3650`, depois `tarefas sub <feature>` em cada filha. A
   árvore tem épico, features e stories.
2. Em cada card dos três níveis, leia o corpo do card com `tarefas ler <card>`: a decisão do
   dono já consolidada mora nas Regras, no Referencial ou na seção onde muda o que o executor
   faz.
3. Depois, `tarefas comentarios <card> --indice` e separe, entre os comentários sem fecho, os
   que abrem com «decisão (dono)», «decisão do dono» ou «insumo» que relata o chat do dono.
   Leia esses inteiros com `tarefas comentarios <card> --id <n>`.
4. Responda com card e seção do corpo, ou com card, número do comentário e a primeira linha
   dele.

Card e comentário dividem a mesma numeração: diga sempre de qual card é o comentário.

## Como responder

Aplique na ordem; a primeira que casar decide.

1. Pedido sobre a casa antiga: a skill não se aplica.
2. A entidade descende de evento ou é da categoria acontecimento: «evento tipado: não tem
   instância própria na casa».
3. A shape declara tabela de módulo ou «projeção de banco»: «mora no módulo: a casa tem só
   a entidade; procure lá», com a tabela.
4. A shape traz outro texto em `sem_forma`: devolva o texto da shape.
5. A shape declara arquivo e ele não está no repositório: «prevista: ainda não está no repositório»,
   com o caminho que a shape dá.
6. A shape não declara arquivo, módulo nem forma: «desconformidade: deveria declarar onde
   mora e não declara; leve ao dono».
7. Duas decisões do dono sobre o mesmo ponto, a nova corrigindo a anterior: vale a nova,
   com a anterior citada ao lado, sem marcar conflito.
8. Insumo que relata decisão do dono no chat, no corpo ou em comentário: vale como decisão
   do dono.
9. Decisão achada no corpo do card: card e seção. Achada em comentário: card, número do
   comentário e primeira linha.
10. Duas fontes em desacordo fora do caso 7: as duas lado a lado, como conflito para o dono.
11. Nenhuma fonte responde: «não achei em <fontes procuradas>: não preencha por palpite».
