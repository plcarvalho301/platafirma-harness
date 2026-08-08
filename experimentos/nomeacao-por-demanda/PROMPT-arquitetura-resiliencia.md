# Nomear a partir da lacuna — capability `resiliencia`

Trabalho de vocabulário, não de arquitetura: o produto é uma lista de conceitos, não
um desenho.

## O artefato

`platafirma-arquitetura/macro-global/capabilities/resiliencia/README.md`, que hoje
diz isto e nada mais:

> Tolerância a falha: timeout, retry, circuit breaker, degradação.
>
> **Fronteira.** Esta capability decide **como** se tolera falha — os padrões e seus
> defaults. Ela **não** decide **o que** é crítico nem o que pode degradar: a
> criticidade de um fluxo é juízo de negócio.
>
> O mecanismo (padrões de resiliência) é uniforme e aplicável sem conhecer a regra de
> negócio; mas a decisão "este fluxo não pode degradar, aquele pode" depende de saber
> o que o fluxo significa para o domínio.
>
> **Por onde ler:** `decisions/` — o mecanismo: padrões de tolerância a falha,
> plataforma. `formas/` — o que seu domínio preenche: a criticidade de cada fluxo, a
> política de degradação. `padroes/` — defaults de timeout, retry, backoff.
>
> **Relações.** Consome a topologia de `integracao/`: resiliência se aplica nos
> pontos onde domínios se integram.

Os três diretórios citados — `decisions/`, `formas/`, `padroes/` — **não existem**.
O README promete o conteúdo e o conteúdo não foi escrito.

Duas decisões de org já fechadas que recortam a capability:

- Resiliência é repartida: conformação de camadas e topologia de integração com
  claudinho-arquiteto; definição, instrumentação e resposta à degradação com
  claudinho-TI. Critério: mecanismo é de quem instrumenta, não de quem desenha a
  topologia.
- **Criticidade de fluxo e política de degradação está sem dono.** Juízo de negócio
  sobre qual fluxo pode degradar e qual não — não é arquitetura, que dá a topologia,
  nem TI, que dá o mecanismo.

## A pergunta

**Que conceitos a PlataFirma precisaria ter lavrado para fechar esta capability?**

Não "que conceitos aparecem no texto acima". O texto é curto de propósito: ele é o
compromisso que já assumimos, e a pergunta é o que falta para ele parar de ser
promessa. Inclua o que o README aponta e não desenvolve, o que a repartição entre as
duas cadeiras pressupõe sem nomear, e o que a matéria órfã exigiria para virar
decidível.

Cada conceito que você propuser deve vir com **a obra que precisaríamos ler para
lavrá-lo** — o livro, a norma, o padrão. Se você sabe o nome da obra, dê o nome. Se
não sabe, descreva que tipo de obra seria e por quê. É legítimo dizer que uma obra
serve a mais de um conceito.

## Restrições de método — não negociáveis

### 1. Partida do zero

Este trabalho **não continua nenhum anterior**. Comece pela capability, não pelo que
você já escreveu sobre coisa nenhuma.

Estão **proibidos** — não como âncora, não como pai, não como vizinho, não
reformulados sob outro rótulo, não citados na definição de outro conceito:

```
problema-perverso              estruturacao-de-problema
mecanismo-de-coordenacao       fronteira-por-custo-de-transacao
processo-de-negocio            fluxo-de-valor
cascata-de-objetivos           governanca-dados
dado-aberto-por-padrao
```

Se um destes for a primeira coisa que vier à cabeça ao ler a capability, **é o sinal
de que você está reciclando e não nomeando** — descarte e continue. Nenhum deles é
resposta a esta pergunta, ainda que pareça encaixar. Encaixar é justamente o defeito:
eles foram formulados para outro lote, e conceito que serve para tudo não decide
nada.

O mesmo vale para qualquer outro conceito que você tenha proposto recentemente, ainda
que não esteja nesta lista.

### 2. Sem consulta ao acervo

Nada de `rag_search`, `query_cargo`, `search_pages`, `repo_read` de ontologia, nem
Postgres. Este trabalho se faz do repertório que você já tem. Não abra
`conceitos-existentes.csv` nem qualquer lista de conceitos lavrados.

### 3. Sem verificar colisão

Se um conceito que você propõe já existir na base, tudo bem — proponha assim mesmo,
com a definição que você escreveria hoje. Colisão é problema meu depois, não seu
agora. Não tente adivinhar o que já tem.

### 4. Sem escrever a capability

Nenhum ADR, nenhum padrão, nenhum default de timeout, nenhuma recomendação de
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

Quantos forem necessários para fechar a capability, e nenhum a mais. Conceito que não
muda decisão nenhuma é ornamento — não o proponha só para engordar a lista.
