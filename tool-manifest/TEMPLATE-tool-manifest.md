---
tipo: template
aplica-se-a: tool-manifest/<cadeira>.md
dono do template: claudinha-gestao-estrategica (RH) — forma
dono do conteúdo: a própria cadeira
---

# Template de tool-manifest

Um manifesto por cadeira, em `tool-manifest/<cadeira>.md`. **Quem preenche é a
cadeira**, na sessão dela: RH fixa a forma, não o conteúdo — ninguém de fora
sabe qual ferramenta a cadeira chama nem por quê.

Manifesto vazio é estado legítimo. Manifesto com linha que ninguém verificou
não é.

## Como a persona aponta para cá

Uma linha na persona, nesta redação:

```
FERRAMENTAL: platafirma-harness/tool-manifest/<cadeira>.md — ler antes de usar
ferramenta. Não é pré-condição para pensar nem para responder.
```

A ressalva final não é gentileza: sem ela a persona trata a leitura do
manifesto como gate e queima uma chamada antes de qualquer resposta, inclusive
nas que não tocam ferramenta nenhuma.

Nenhuma persona embute o inventário. Ver `personas/HIGIENE.md`, regras 1 e 8.

## Esqueleto

```markdown
# tool-manifest — <cadeira>

Ambiente: <host / usuário / o que a cadeira precisa saber para não descobrir na
falha>.

Verificação: cada linha declara **como** — `[exec]` binário executado ·
`[func]` importado e usado em trabalho real · `[inst]` presente, sem prova de
funcionamento. `[inst]` é confissão, não aval.

> **Regra de ouro:** existindo tool para o que vou fazer, chamo a tool.
> Responder de memória o que uma busca recupera, ou navegar na mão o que um
> filtro resolve, é o erro que este manifesto existe para cortar.

## Conectores

**<conector>** (`<endpoint>`) — <o que ele é, em uma linha>.
- `monta_sessao` (ops) — contexto de abertura da cadeira numa chamada: persona
  canônica, este manifesto, org canônico e estado da fila. Chamar em vez de
  encadear leitura. Sob demanda, não gate de entrada.
- `<tool>` — quando chamar, e o que a chamada responde.

## <gerência 1> — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| | | |

## <gerência 2> — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| | | |

## Armadilhas medidas

<Comportamento que já enganou alguém: retorno que parece uma coisa e é outra,
flag que muda o resultado em silêncio, filtro que devolve zero sem erro. Uma
linha cada, com o caso.>

## Pendências declaradas

<Ferramenta que falta, com para que serviria e o que falta para entrar. Sem
prazo — prazo é card no rastreador.>
```

## O que não entra

- **Número que a ferramenta responde.** Contagem, sha, versão de índice,
  tamanho de acervo. O manifesto diz qual binário responde; o valor sai dele.
- **Ferramenta que a cadeira não usa.** Estar disponível no pool não é motivo
  para ocupar linha. Conector de outra cadeira que aparece na sessão: uma linha
  de fronteira dizendo que não é seu, e só.
- **Tutorial.** Manifesto é mapa de chamada, não manual. Uso extenso vira skill
  ou página de wiki, com ponteiro daqui.
- **Log de mudança.** Estado atual mora no Git.
