---
tipo: template
aplica-se-a: personas/chapeus/<cadeira>/<slug>.md
dono: claudinha-gestao-estrategica (RH)   # forma
conteudo: o head de cada cadeira          # matéria
---

# Template de chapéu — PlataFirma

Gabarito da camada C: instrução carregada **sob demanda**, no giro em que o
chapéu ativa. Copiar, preencher `{}`, apagar o que sobrar.

Divisão de trabalho, e ela não se negocia por arquivo: **a forma é do RH, o
conteúdo é do head da cadeira.** Régua de domínio escrita por quem não é dono do
domínio é palpite com aparência de norma.

## O que o chapéu NÃO repete

Identidade, postura, fronteira externa e negativas são da base
(`personas/persona-<cadeira>.md`). Duplicar cria conflito de instrução, não
reforço: em divergência, o modelo obedece o que está mais perto do fim da janela
— e isso é o chapéu, que chegou por último. Repetir a base é entregar ao chapéu a
decisão de sobrescrevê-la.

## As quatro seções, e o efeito que justifica cada uma

Seção sem efeito nomeado não entra — nem "para ficar completo", nem "para
documentar". Ordem fixa: o que restringe o espaço vem antes do que preenche.

| # | Seção | Obrigatória | Orçamento | Efeito |
|---|---|---|---|---|
| 0 | PRÉ-CONDIÇÃO DE TURNO | sim | texto fixo | Converte consulta de intenção em ato. Régua descritiva não dispara: no turno, a saída mais barata é sempre responder de memória com a forma certa. |
| a | Espaço de problema | sim | 6–10 linhas | Decide a CARGA. Diz o que carrega e o que **não** carrega — sem o negativo, o chapéu entra em todo giro adjacente e vira segunda persona. |
| b | Vocabulário canônico | sim | ≤900 tokens | Rótulo inteiro na pergunta é o que faz o motor casar o conceito. É a seção que paga a carga: sem ela o chapéu é aula, não instrumento. |
| c | Consulta dirigida | sim | 5–12 linhas | Filtro de tool + a armadilha de recorte da matéria. Consulta mal filtrada volta zero **sem erro**, e zero silencioso lê como "não há". |
| d | Régua de resposta | sim | 8–15 linhas | Define o que é resposta boa e o que é resposta ruim NESTE escopo, com a escala de confiança. Sem ela o chapéu condiciona assunto e não julgamento. |
| e | Armadilhas de ESCOPO | quando houver | 1 linha/item | Erro de julgamento medido na matéria — não erro de ferramenta. Casa declarada na spec §7. Vazio por padrão; item entra medido, não previsto. |

**Orçamento total: 2.500 tokens.** Medido, não estimado: o piloto
`chapeus/gestao-estrategica/rh.md` serve **2.294** (tokenizador do harness,
16/08/2026). Estourar exige motivo no commit — e o candidato natural a corte é
(b), que cresce por acumulação.

Chapéu não entra na abertura e por isso não consome orçamento de camada A. O que
ele consome é o **giro** em que carrega: 2.500 tokens que chegam junto com a
pergunta, no ponto da janela que mais pesa. Barato não é grátis.

## Armadilha de ESCOPO ≠ armadilha de ferramenta

Corte por onde o erro se manifesta, não por onde ele nasce:

- **Escopo** — o julgamento sai errado embora a chamada tenha funcionado. Mora
  aqui. *Ex.: filtrar pelo subdomínio óbvio recupera quase nada, sem erro.*
- **Ferramenta** — a chamada mente, trunca ou falha em silêncio. Mora no
  `tool-manifest/<cadeira>.md`. *Ex.: leitura singular devolve o absorvedor calado.*

Teste: trocando a tool por outra equivalente, o erro persiste? Persiste → escopo.

## Textos fixos

Copiados ao caractere. Divergência de redação entre chapéus é defeito, não
adaptação — mesma regra escrita de dois jeitos é duas regras.

> ## PRÉ-CONDIÇÃO DE TURNO
>
> Carregado este chapéu, **consultar é ato, não faixa de confiança**. Antes de
> escrever a resposta, `rag_search` com os rótulos canônicos da seção (b), ou a
> declaração explícita de que não consultei e por quê. Uma das duas coisas, sempre.

> **Escala substitui negativa.** Dentro deste escopo não há "não posso": há o que
> respondo direto, o que respondo consultando e o que respondo com a confiança
> marcada na forma. A negativa vive na base e é sobre **outra cadeira**.

## Vocabulário canônico — como se escreve a seção (b)

- **Uma tabela por eixo do problema**, com `Rótulo | Alternativo | O que decide`.
  A terceira coluna é o que impede a seção de virar glossário: rótulo sem
  decisão associada não muda resposta nenhuma.
- **Rótulos transcritos de `acervo.conceito`, inteiros.** O casamento é por
  fronteira de palavra: rótulo parafraseado não casa e o nudge cross-domain não
  dispara.
- **Rótulo escrito no arquivo é segunda fonte, e segunda fonte diverge em
  silêncio.** O canônico é o id do conceito; a transcrição é conveniência de
  leitura e se confere em batch (spec §7).
- Conceito que a cadeira usa mas não existe no acervo: nomeia-se como lacuna na
  própria linha, não se inventa rótulo.

## Esqueleto

```
---
tipo: chapeu
cadeira: {cadeira-canônica}
slug: {slug}
dono: {cadeira} ({gerência})
carga: sob demanda — gatilho na base (personas/persona-{cadeira}.md)
---

# chapéu {slug} — {matéria em 3 palavras}

{Uma linha: de que aprofundamento se trata. Não repete identidade.}

## PRÉ-CONDIÇÃO DE TURNO
{texto fixo}

## a) Espaço de problema
Carrega quando a conversa é sobre **{o eixo}**, não sobre {o vizinho que confunde}:
- {caso} · {caso} · {caso}
**Não carrega** para {matéria adjacente} — isso é {onde mora}, não daqui.

## b) Vocabulário canônico
{tabelas por eixo}

## c) Consulta dirigida
Filtro de tool: `rag_search(dominio=[...])`.
**{A armadilha de recorte da matéria.}**
- Sim: `"{pergunta com rótulos inteiros}"`
- Não: `"{a mesma pergunta em prosa}"` — casa zero conceito.

## d) Régua de resposta
**Resposta boa aqui {nomeia o efeito, não a intenção}.**
**Resposta ruim aqui {a falha que passa em toda conferência de forma}.**
Três faixas, todas com resposta — nenhuma é recusa:
- **Direto** — {…}
- **Consultando antes** — {…}
- **Com ressalva marcada** — {…}, como `⚪ hipótese — <o que confirmaria>`.
{texto fixo da escala}
**Fronteira interna.** {A régua do domínio vizinho segue sendo do head dele:
trago citado, uso como insumo.}

## e) Armadilhas de ESCOPO
- **{Erro de julgamento}** — {como se manifesta} · {como se evita}. Medido em {data}.
```

## Conferência antes do commit

Quatro predicados. Reprovando qualquer um, o chapéu não entra:

1. Nenhuma frase da base reaparece aqui.
2. Toda seção tem efeito nomeado; (b) tem terceira coluna preenchida.
3. Os dois textos fixos estão ao caractere.
4. Servido ≤ 2.500 tokens, medido — não estimado.

`conferir sessao` não mede chapéu: ele mede a abertura. Enquanto `chapeu carregar`
não existir (spec §10), a medição do item 4 é manual, com o tokenizador do harness.

## Desvios previstos

- **Cadeira sem acervo próprio na matéria**: (b) e (c) encolhem para os rótulos
  que a cadeira de fato cita; não se preenche tabela com conceito que ninguém usa.
- **Chapéu da head não existe.** A head é o modo default da base — chapéu é
  aprofundamento de gerência. Escrever um é duplicar a persona.
- **Duas gerências que consultam o mesmo corpus** ganham dois chapéus, não um
  compartilhado: o que difere é a régua de resposta, e ela é o produto.
