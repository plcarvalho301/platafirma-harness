# Rodada 2 — prompt de proposta de conceitos

Texto único e genérico — cola igual em toda sessão, sem editar nada. Cada
cadeira se identifica sozinha pela própria persona ativa.

Cadeiras que respondem: `claudinho-arquiteto`, `claudinho-conhecimento`,
`claudinho-IA`, `claudinha-produto`, `claudinho-TI`,
`claudinha-gestao-estrategica`. `claudinha-fabrica` e `claudinha-osint` não
participam — não são cadeiras. `claudinho-seguranca` usa
`PROMPT-rodada-2-seguranca.md`.

---

**Rodada 2 da distribuição do acervo. Você é a cadeira desta sessão — sua
própria persona. Proponha os conceitos que as obras do seu lote sustentam.**

Trabalho em oito passos, na ordem. **Nenhuma linha de proposta se escreve antes
do passo 5 concluído.** Conceito cravado a partir de título é o modo de falha
desta rodada, e ele não aparece na entrega — aparece meses depois, como régua
que não decide nada.

**Conceito não tem dono.** Você propõe **régua**, não posse. Não existe campo de
domínio na entrada: o conceito existe sozinho, individuado pela definição, e é o
domínio que declara pertencimento do lado dele. Duas cadeiras propondo a mesma
régua não é conflito — é a mesma entrada, e uma das duas sai.

## Passo 1 — montar o lote

Repo `platafirma-harness`:

- `distribuicao/rodada-1/reivindicacoes/<sua-persona>.csv` — o que você ganhou,
  **menos** as obras que aparecem em `conflitos.csv`;
- `distribuicao/rodada-1/conflitos.csv` — as obras em que você foi reivindicante
  e **perdeu**: o conceito delas é seu. Quem levou a obra não propõe o conceito
  dela.

Leia os arquivos inteiros. Escreva a lista fechada de obras do seu lote antes de
seguir, separando as duas origens.

## Passo 2 — ler as obras no RAG (obrigatório, antes de qualquer candidato)

**Título não é leitura.** Toda obra que virar âncora de conceito tem que ter
sido consultada no acervo nesta sessão.

- Ferramenta: `rag_search`, com `colecao="firma"` e `texto="secao"`. Não há
  filtro por obra — você pergunta pelo assunto e confere o campo `obra` de cada
  fonte para saber o que de fato leu.
- **Duas consultas por obra, em ângulos diferentes:** uma pela tese que o título
  anuncia, outra pelo mecanismo que você suspeita que ela sustente. Se a segunda
  não trouxer a obra, sua suspeita é sua, não dela.
- **Comece pelas obras que você perdeu na arbitragem.** São as que você conhece
  menos e as que mais chance têm de sustentar régua que você não anteciparia —
  é para isso que a réplica existe. Ler estas por cima esvazia a rodada inteira.
- Obra que não retorna em nenhuma consulta: marque **não recuperável**, não use
  como âncora e reporte no passo 8. Não invente régua sobre o que você não leu.
- Leia o retorno com a régua da skill `platafirma` (`cobertura`, `sim`,
  `rerank`, idioma). Cobertura fraca sem `codigo_exato` é sinal de que você não
  leu a obra — é sinal de que ela não está lá.

## Passo 3 — extrair candidatos da leitura

Dos trechos lidos, não dos títulos: liste os candidatos e, para cada um, escreva
em uma frase o **mecanismo** — a relação que a obra afirma e que produz veredito.
Candidato sem mecanismo identificável morre aqui.

## Passo 4 — as sete heurísticas, uma de cada vez

1. **Régua antes de rótulo.** Escreva o mecanismo e só depois nomeie. Definição
   que contém o próprio rótulo, ou a fórmula "o que se considera X", volta.
2. **Teste dos três casos.** Aplique a régua a três obras: uma que entra, uma que
   não entra, uma duvidosa. Quem mede é a duvidosa. Se ela não decide só com o
   texto da régua, a régua está frouxa.
3. **Teste de transposição.** Aplique a régua fora do universo da obra de origem.
   Precisou de "é meio como se fosse", é metáfora, não transposição: conceito
   diferente, régua própria.
4. **Caso falseador, uma linha.** Que caso, se aparecesse, mostraria que esta
   régua está errada. Régua que nenhum caso contraria não delimita nada.
5. **Teste do parônimo.** Se dois curadores competentes redigiriam definições
   incompatíveis para o termo nu, ele não vira entrada: quebre em compostos
   (`inteligencia-de-ameacas`, nunca `inteligencia`).
6. **Prateleira não é régua.** Candidato que só agrupa obras é subdomínio —
   devolva ao dono do domínio. Coincidência lexical entre rótulo e domínio não
   infere nada.
7. **Varredura antes de propor.** Leia
   `distribuicao/rodada-2/conceitos-existentes.csv` (205 entradas). Rótulo
   diferente que decide a mesma coisa **é a mesma entrada**: não proponha em
   paralelo. Discordando da régua existente, proponha **substituição** dela, com
   o motivo, em vez de entrada nova.

Registre o que morreu em cada teste — isso é pedido no passo 8.

## Passo 5 — cota por lastro

Sem número. Cada conceito precisa de **≥2 obras do seu lote** que a régua
classifique, e todas as âncoras têm que ter passado pelo passo 2. Teto duro de
**10** conceitos por cadeira: existe para forçar seleção, não para ser atingido.
Lote pequeno propõe pouco ou nada, e isso é resultado correto.

## Passo 6 — escrever a proposta

`distribuicao/rodada-2/propostas/<sua-persona>.md` (nome do arquivo = seu próprio
nome de cadeira), um bloco por conceito:

```
## <slug>
rotulo: <nome legível>
natureza: fenomeno | processo | disposicao | modelo
estatuto: natural | doutrinario | instituido
definicao: <a régua: o mecanismo, em uma a três frases>
obras-ancora: <obra_id>, <obra_id>   # ≥2, UUID literal do CSV
caso-falseador: <o caso que mostraria a régua errada>
pai-proposto: <slug do conceito mais amplo, ou vazio>
substitui: <slug existente, ou vazio>
```

`pai-proposto` só quando a régua do pai decide todo caso que a do filho decide.
Hierarquia por afinidade temática não vale — deixe vazio.

## Passo 7 — commit

`git pull --rebase`, commit e push **só do seu arquivo**. Não toque em
`conceitos-existentes.csv`, nos artefatos da rodada 1 nem no arquivo de outra
cadeira.

## Passo 8 — resposta na conversa, completa

Depois do commit, **cole na conversa o conteúdo inteiro do seu
`propostas/<sua-persona>.md`** — todo bloco, todo campo. O Pedro lê aqui, não no
repo; arquivo sem cópia na conversa não foi entregue.

Junto, no máximo:

- quantos conceitos propôs, e quantas obras do lote você consultou no RAG;
- as obras **não recuperáveis** (consultadas e ausentes do acervo);
- um candidato que morreu no teste de transposição, e um que morreu na varredura
  contra os existentes;
- o conceito que saiu de obra que você **perdeu** na arbitragem — se nenhum saiu,
  diga isso explicitamente.

**Não faça agora:** escrever em `acervo.conceito`, criar ou editar página de
wiki, criar subdomínio, declarar relação entre conceitos de cadeiras diferentes.
A reconciliação e a teia são de `claudinho-conhecimento`, depois que todas as
propostas estiverem no repo.
