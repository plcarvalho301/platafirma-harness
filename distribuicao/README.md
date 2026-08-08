# Distribuição de domínios e conceitos — rodada 1

Instrumento da faixa F1. Reparte o acervo entre as cadeiras para que a primeira
teia de conceitos nasça com dono. O registro da deliberação é este diretório;
o banco (`acervo.obra.dominio_id`) só recebe o resultado depois de fechado.

## Base

`rodada-1/obras-305.csv` — as 305 obras que têm `dominio_id` preenchido,
medidas em 2026-08-08. Colunas: `obra_id`, `titulo`, `dominio_atual`,
`subdominio_atual`, `especie`, `colecao`.

O `dominio_atual` é palpite herdado da triagem, não cerca: qualquer cadeira
pode reivindicar qualquer obra da base, inclusive contra o domínio de hoje.

As 388 obras sem domínio ficam fora desta rodada.

## Como cada cadeira responde

Um arquivo por cadeira em `rodada-1/reivindicacoes/<persona>.csv`, com cabeçalho:

```
obra_id,nota
```

`nota` é uma linha de defesa, opcional — o que a obra faz pelo domínio de quem
reivindica. Sem teto de quantidade: o freio é ter que defender a reivindicação
na arbitragem.

## Consolidação

Contagem de reivindicações por obra:

- **zero** — órfã. Candidata a sair do corpus; a lista vai para o dono.
- **uma** — fecha ali, sem arbitragem, ainda que contrarie o `dominio_atual`.
- **duas ou mais** — conflito. Arbitragem por claudinho-conhecimento e pelo
  dono; a decisão fica em `rodada-1/conflitos.csv`
  (`obra_id,reivindicantes,vencedor,motivo`).

Fechada a arbitragem, o dono de cada domínio define os subdomínios dele.

## Rodada 2 — o que já está fixo

- Cada cadeira propõe conceitos a partir das obras que ficaram com ela, exceto
  as que foram a conflito.
- Obra que foi a conflito: quem **perdeu** a arbitragem propõe o conceito dela.
- Cada cadeira propõe relações e hierarquia entre os próprios conceitos e
  entrega a claudinho-conhecimento, que reconcilia e monta a teia.

Aberto, a decidir antes de abrir a rodada 2:

- Quantos conceitos por cadeira, e se a cota é fixa ou proporcional ao tamanho
  do domínio (`seguranca-privacidade` tem 106 obras na base; `inteligencia`, 1).
- O que fazer com os 205 conceitos que já existem em `acervo.conceito`, 62
  deles já com pai.
