# caderno — dados / conhecimento

Método da cadeira. Não guarda estado (o instrumento mede), nem fato de negócio
(card, commit, wiki). Só o que continua verdadeiro depois que o assunto morre.

## Classificar vem ANTES de vetorizar, e a inversão não dá erro

O vetor de faceta é feito de um cabeçalho — `titulo · emitido_por · dominio ·
subdominio · tipo · trata_de · colecao`. Vetorizar antes de classificar grava
vetor pobre **sem erro nenhum**, e a busca por faceta passa a responder mal sem
nada acusar. Vale para `emitido_por` tanto quanto para `trata_de`: preencher
autoria depois de vetorizar exige re-rodar.

Corolário barato: `embed-meta --all` é idempotente e custa segundos. Na dúvida,
re-rode depois de qualquer mudança de classificação.

## Ao criar conceito, o tipo da aresta decide se a afirmação é verificável

Só `mais_amplo_tipo = generica` vira `rdfs:subClassOf` na projeção. As outras
(patologica, instrumental, condicional, tematica, partitiva…) não produzem
asserção lógica — o conceito entra como classe solta e o raciocinador não tem
o que checar.

Consequência prática: `generica` entre naturezas que o BFO declara disjuntas é
insatisfazível na hora. O mapa é `modelo` → ICE, `processo` e `fenomeno` →
process, `disposicao` → disposition. Antes de usar `generica`, conferir a
natureza dos dois lados. Toda a fila de reparo da `ont:0080` é esse mesmo erro
repetido — não são casos avulsos.

E o inverso é a armadilha: passar no reasoner com aresta não-genérica não é
mérito, é ausência de afirmação.

## Coerência de família manda sobre proposta isolada

Antes de fixar natureza/estatuto de um conceito novo, olhar os irmãos de
prefixo. A família `deriva-*` é toda `patologica/fenomeno/natural`; propor um
membro novo como `doutrinario` cria divergência que nada detecta depois.

## O reasoner não cobre o vocabulário inteiro

A projeção filtra `where c.mais_amplo_id is not null`: conceito **ilhado** —
sem pai e sem filho — nunca é projetado e nunca é verificado. "TBox
consistente" é afirmação sobre o subconjunto conectado, não sobre o
vocabulário. Ao reportar consistência, dizer a cobertura junto.

## Garantia literária é a régua para criar termo

Antes de aceitar termo novo (inclusive sugerido pelo dono), contar trechos no
acervo que o sustentam. Termo bonito com 2 trechos perde para termo feio com
12. A régua é nosso próprio conceito `garantia-literaria`, e aplicá-la a nós
mesmos é o teste de que ela vale.

## Título de normativo não é evidência

Ler o texto. Um decreto catalogado com a ementa de outro decreto sobreviveu ao
catálogo, à classificação e à vetorização sem ninguém notar — e fez o acervo
parecer ter uma norma que nunca teve. O número no título também não basta:
confere-se contra o corpo, que é barato quando a obra já está indexada.

Generaliza: para qualquer obra de título opaco, ler dois trechos custa segundos
e muda a resposta com frequência alta.

## Duplicata de obra: fundir, nunca deletar direto

Duplicatas raramente são cópias — cada entrada costuma carregar metade da
catalogação (uma com `id_canonico`, outra com espécie e conceitos). Deletar
direto joga fora juízo, não lixo.

Ordem: escolher sobrevivente → migrar para ela só o que está NULL, com guarda
que recusa subdomínio de domínio alheio → migrar âncoras com `ON CONFLICT DO
NOTHING` → só então apagar.

O índice vetorial mora em **outra instância** (`motor-pg`) e não há FK entre
elas: apagar obra aqui deixa vetor órfão lá. Apagar no motor **primeiro**.

## Ao gravar classificação em lote

Todo UPDATE leva `AND <campo> IS NULL` — o dono classifica em paralelo pelo
NocoDB e sobrescrever o trabalho dele é invisível. Backup em tabela `_backup_*`
antes. E rodar guardas que falham alto: padrão que não casou com obra nenhuma,
padrão ambíguo que casou com várias, termo inexistente no vocabulário. Foi uma
guarda de padrão ambíguo que revelou duplicata de obra.

## Casar obra por título falha nos dois sentidos — a régua é o conceito

Conferir fila de aquisição, dedup ou "já temos isso?" por casamento de título produz as
duas falhas opostas, e nenhuma delas dá erro:

- **falso negativo em massa** — o acervo usa título hifenizado (`Vocabulary-Problem-Furnas-et-al`),
  e `ILIKE '%Vocabulary Problem%'`, com espaço, não casa. Uma fila de 70 pedidos sobreviveu
  inteira a uma passada dessas com 18 achados, quando os atendidos eram 52.
- **falso positivo** — homônimo e parente casam: FRAD casa com FRSAD, Knuth com *Art of UNIX
  Programming*, o *Guia* de Dados Abertos com o Decreto que institui a política.

Ordem que funciona: (1) normalizar dos dois lados — sem acento, hífen e sublinhado viram
espaço — e usar similaridade, nunca `LIKE`; (2) **perguntar ao acervo pelo conceito**, que é
o que de fato se quer saber; (3) abrir o primeiro trecho do candidato antes de decidir. Os
três passos custam segundos e mudam o veredito com frequência alta.

O corolário vale para a curadoria inteira: o que decide é o conceito estar carregado, não a
obra ser a mesma. Obra de outro autor que carrega o conceito fecha o pedido; obra homônima
que não o carrega, não.

## Estar no acervo não é estar recuperável

Obra pode ter objeto no store, impressão, classificação e vetor de faceta — e **zero trecho
elegível**. PDF sem camada de texto atravessa catálogo, classificação e `embed-meta` sem
acusar nada, e some da busca sem sumir da contagem.

Antes de afirmar que o acervo cobre um assunto por causa de uma obra, conferir:

```sql
SELECT count(*) FROM acervo.impressao i JOIN acervo.trecho t ON t.impressao_id = i.id
WHERE i.obra_id = '<uuid>' AND t.elegivel;
```

Zero aqui é pendência de **ingestão** (OCR), não de aquisição — e são estados diferentes,
que pedem atos diferentes de quem lê a fila.
