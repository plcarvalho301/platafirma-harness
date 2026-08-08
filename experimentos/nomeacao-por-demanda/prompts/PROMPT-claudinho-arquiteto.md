# Nomear a partir da lacuna — capabilities de domínio

Trabalho de vocabulário: o produto é uma lista de conceitos, não um desenho. Os
conceitos delimitados na rodada anterior apresentaram vieses inaceitáveis relativos
ao próprio acervo: o acervo não é o objetivo, o acervo é veículo para os conceitos
que precisamos contemplar no corpo de conhecimento dos nossos domínios.

## A pergunta

**Que conceitos a PlataFirma precisaria ter lavrado para fechar as capabilities da
sua cadeira?**

Não "que conceitos já estão no acervo", nem "que conceitos aparecem no que já
escrevemos". O que está escrito é o compromisso que já assumimos; a pergunta é o que
falta para ele parar de ser promessa. Inclua o que os seus artefatos apontam e não
desenvolvem, o que uma repartição de remit entre cadeiras pressupõe sem nomear, e o
que a matéria órfã exigiria para virar decidível.

Comece relendo os compromissos escritos da sua cadeira — os READMEs, as decisões, as
páginas de frente que são suas. Ler os próprios artefatos é parte do trabalho e está
permitido; o que está proibido é o acervo (restrição 2).

Cada conceito que você propuser deve vir com **a obra que precisaríamos ler para
lavrá-lo** — o livro, a norma, o padrão. Se você sabe o nome da obra, dê o nome. Se
não sabe, descreva que tipo de obra seria e por quê. É legítimo dizer que uma obra
serve a mais de um conceito.

## Restrições de método — não negociáveis

### 1. Partida do zero

Este trabalho **não continua nenhum anterior**. Comece pelas capabilities, não pelo
que você já escreveu sobre coisa nenhuma.

Estão **proibidos** — não como âncora, não como pai, não como vizinho, não
reformulados sob outro rótulo, não citados na definição de outro conceito:

```
cascata-de-objetivos           dado-aberto-por-padrao
estruturacao-de-problema       fluxo-de-valor
fronteira-por-custo-de-transacaogovernanca-dados
mecanismo-de-coordenacao       problema-perverso
processo-de-negocio
```

Se um destes for a primeira coisa que vier à cabeça ao ler uma capability sua, **é o
sinal de que você está reciclando e não nomeando** — descarte e continue. Nenhum
deles é resposta a esta pergunta, ainda que pareça encaixar. Encaixar é justamente o
defeito: eles foram formulados para outro lote, e conceito que serve para tudo não
decide nada.

O mesmo vale para qualquer outro conceito que você tenha proposto recentemente, ainda
que não esteja nesta lista.

### 2. Sem consulta ao acervo

Nada de `rag_search`, `query_cargo`, `search_pages`, `repo_read` da ontologia, nem
Postgres. Este trabalho se faz do repertório que você já tem, mais os seus próprios
artefatos. Não abra `conceitos-existentes.csv` nem qualquer lista de conceitos
lavrados.

### 3. Sem verificar colisão

Se um conceito que você propõe já existir na base, tudo bem — proponha assim mesmo,
com a definição que você escreveria hoje. Colisão é problema do arquiteto de
informação depois, não seu agora. Não tente adivinhar o que já tem.

### 4. Sem escrever a capability

Nenhum ADR, nenhuma decisão, nenhum padrão, nenhuma recomendação de ferramenta ou
plataforma. Só a lista de conceitos e as obras.

Trabalhe sozinho até o fim. Perguntar antes de tentar é o que este trabalho não pode
ter.

## Formato

Um bloco por conceito, nesta forma exata:

```
## <slug>
rotulo: <Rótulo>
natureza: processo | disposicao | modelo | fenomeno
estatuto: instituido | doutrinario | natural
definicao: <o que é, em português, sem oração subordinada na primeira frase; depois
o mecanismo — o que decide, o que quebra sem ele. Um exemplo concreto vale mais que
precisão adicional.>
obra-necessaria: <nome da obra, ou o tipo de obra e por quê>
caso-falseador: <o caso que, ocorrendo, mostraria que o conceito não faz trabalho>
pai-proposto: <slug, ou vazio>
```

Sem preâmbulo, sem fecho, sem relatório do que você fez. A lista é a entrega.

## Cota

Quantos forem necessários para fechar as capabilities, e nenhum a mais. Conceito que
não muda decisão nenhuma é ornamento — não o proponha só para engordar a lista.
