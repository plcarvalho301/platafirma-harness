# Experimento — nomeação por demanda

Testa se a **direção da pergunta** explica a diferença de qualidade entre os
conjuntos de slugs do acervo.

## A hipótese

O vocabulário de segurança (`triade-cid`, `menor-privilegio`, `defesa-em-profundidade`,
`superficie-de-ataque`) foi nomeado antes de haver corpus, a partir da pergunta
*"que conceitos precisaríamos de livro para fechar o casco?"*. O vocabulário de IA
(`gerar-vs-avaliar`, `effort-e-thinking`, `arquitetura-e-parametros`) foi nomeado a
partir de aulas já lidas. O primeiro conjunto nomeia entidades do campo; o segundo
nomeia recortes de uma travessia de estudo.

A hipótese é que a variável não é o assunto nem o modelo, e sim a direção:

- **demanda** — nomeia-se o que falta saber, e o critério de sucesso está embutido na
  pergunta: se o nome não for o nome do campo, não acha livro.
- **oferta** — nomeia-se o que já se leu, e o resultado é o índice da leitura.

A rodada 2 pediu oferta: cada cadeira propôs conceitos a partir do lote de obras dela.

## O desenho

Pareado, mesma cadeira, mesmo domínio, duas direções.

| | conjunto |
|---|---|
| controle (oferta) | `distribuicao/rodada-2/propostas/claudinho-arquiteto.md` — 9 slugs |
| tratamento (demanda) | saída de `PROMPT-arquitetura-resiliencia.md` |

Cadeira escolhida: **arquitetura**. A capability `resiliencia` é compromisso próprio,
escrito, no domínio da cadeira, e visivelmente incompleto — o README aponta para três
diretórios que não existem. Sem essa lacuna na superfície, a pergunta não tem alvo.

## Critérios de comparação

Aplicados aos dois conjuntos depois da coleta, nunca antes:

1. **Teste do catálogo** — procurando uma obra por este nome, acha? Mecânico, não é
   juízo de gosto.
2. **Sintagma nominal** — nomeia uma entidade, e não uma comparação (`X-vs-Y`), uma
   conjunção (`X-e-Y`) ou uma tese (`X-antes-de-Y`).
3. **Teto de três palavras.**
4. **Entra em árvore** — tem pai ou irmão plausível no conjunto.

## O que fica fora do prompt, e por quê

- **Os quatro critérios acima.** Dá-los à cadeira faria o experimento medir
  obediência a uma régua, não o efeito da direção da pergunta.
- **A existência da comparação.** Saber que está sendo pareado contra a própria
  entrega anterior contamina a entrega nova.
- **O acervo.** Proibido por restrição explícita no prompt: consultar o corpus
  converte demanda em oferta, que é exatamente a variável sob teste.

O prompt **não** carrega linha de persona: a sessão roda dentro do Project da cadeira,
que já a fornece.

Os 9 slugs do conjunto de controle entram no prompt **nomeados um a um, como
proibição**. Bloqueio genérico não segura: a cadeira defaulta para o que acabou de
formular, e o resultado seria a rodada 2 reescrita. Nomeá-los tem custo de ancoragem
conhecido — mas o custo do default é maior, e a lista nominal é o que permite auditar
a violação na saída.

## Limite conhecido

Segurança é um campo com terminologia consolidada e pública — NIST CSF, CIS Controls,
ISO 27001, ASVS. Parte da qualidade do conjunto do casco pode vir da maturidade
terminológica do campo, não da direção da pergunta. Resiliência tem terminologia
razoavelmente estável (Nygard, Beyer), o que atenua mas não elimina o efeito. Um
resultado positivo aqui não separa as duas causas sozinho; separá-las exigiria um
terceiro braço num campo de terminologia frouxa.
