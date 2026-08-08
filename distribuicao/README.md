# Distribuição de domínios e conceitos — rodada 1

Instrumento da faixa F1. Reparte o acervo entre as cadeiras para que a primeira
teia de conceitos nasça com dono. O registro da deliberação é este diretório;
o banco (`acervo.obra.dominio_id`) só recebe o resultado depois de fechado.

## Base

`rodada-1/obras.csv` — as 644 obras da coleção `firma`, medidas em 2026-08-08.
Colunas: `obra_id`, `titulo`, `dominio_atual`, `subdominio_atual`, `especie`,
`colecao`. Coleção `pessoal` (49 obras, biblioteca particular do Pedro) fica
fora — não é corpus de trabalho da org.

**Bolo único, sem partição.** 305 dessas 644 já têm `dominio_atual`
preenchido (palpite herdado da triagem, não cerca); 339 estão em branco. A
rodada não separa as duas: toda cadeira reivindica sobre o arquivo inteiro, no
mesmo prompt, na mesma passada. A proximidade semântica entre obra já
classificada e obra em branco é o que deve gerar conflito — é onde a fronteira
entre domínios aparece; separar as duas listas mataria esse sinal.

## Como cada cadeira responde

Um arquivo por cadeira em `rodada-1/reivindicacoes/<persona>.csv`, com cabeçalho:

```
obra_id,nota
```

`<persona>` é o nome da própria cadeira que está respondendo — cada sessão se
identifica sozinha, não há edição de arquivo por fora. `nota` é uma linha de
defesa, opcional — o que a obra faz pelo domínio de quem reivindica. Sem teto
de quantidade: o freio é ter que defender a reivindicação na arbitragem.

## Consolidação

Contagem de reivindicações por obra:

- **zero** — órfã. Fica no corpus com o `dominio_atual` que já tem (ou em
  branco, se nunca teve); o dono classifica a mão, fora desta rodada.
- **uma** — fecha ali, sem arbitragem, ainda que contrarie o `dominio_atual`.
- **duas ou mais** — conflito. Arbitragem por claudinho-conhecimento e pelo
  dono; a decisão fica em `rodada-1/conflitos.csv`
  (`obra_id,reivindicantes,vencedor,motivo`).

Fechada a arbitragem, o dono de cada domínio define os subdomínios dele —
sem critério formal nem rodada própria; cada dono corta do jeito que fizer
sentido pra ele. Divergência entre cadeiras não trava esta etapa: se resolve
depois, na leitura do reasoner e do Pedro.

## Régua de arbitragem

A obra é de quem **produz o artefato que ela normatiza**. Não de quem a cita
mais, não de quem controla a variável que ela descreve, não do `dominio_atual`.
Disputada a mesma obra, vence a cadeira cujo artefato de trabalho é o objeto do
texto: ADR é do arquiteto, porque é ele quem escreve as ADR centrais; SBOM é de
TI, porque é a construção que emite o SBOM; enunciado de problema é de produto,
porque é produto que o escreve.

Cadeira normativa perde a obra que regula trabalho alheio. Isso é por design:
a régua não tira a matéria de quem regula — obriga que ela devolva a régua em
forma legível por quem executa. É o que a rodada 2 cobra.

## Réplica

Quem perdeu a arbitragem propõe o conceito da obra. No mesmo ato pode anexar
**uma linha** de contestação da arbitragem, citando a régua registrada em
`rodada-1/conflitos.csv`. Contestação sem a régua citada não conta. Quem arbitra
a réplica é o dono.

## Rodada 2 — o que já está fixo

- Cada cadeira propõe conceitos a partir das obras que ficaram com ela, exceto
  as que foram a conflito.
- Obra que foi a conflito: quem **perdeu** a arbitragem propõe o conceito dela.
- O domínio do conceito é declarado, não herdado da obra: a réplica torna obra
  e conceito derivado donos distintos por desenho.
- Cada cadeira propõe relações e hierarquia entre os próprios conceitos e
  entrega a claudinho-conhecimento, que reconcilia e monta a teia.

Aberto, a decidir antes de abrir a rodada 2:

- Quantos conceitos por cadeira, e se a cota é fixa ou proporcional ao tamanho
  do domínio (`seguranca-privacidade` tem 120 obras já classificadas na base;
  `inteligencia`, 1).
- O que fazer com os 205 conceitos que já existem em `acervo.conceito`, 62
  deles já com pai.
