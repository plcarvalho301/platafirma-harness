---
name: diagrama
description: Use quando for DESENHAR ou REFAZER figura de arquitetura — topologia, fluxo com ramo, estrutura em camadas, relação N:N — para wiki, LP ou slide. Dá o gerador (`gerar.py`), o formato do modelo, as duas vistas (engenharia, estilo provedor de nuvem; diretoria, estilo C4) e a régua de cor fixa por categoria, tudo lido de `tokens.css` em tempo de geração. Implementa `platafirma-arquitetura/design/diagramas.md` (§2 vocabulário de forma, §3 cor, §5 produção) — não tem régua própria. NÃO dispare para gráfico de dado (série, barra), para figura gerada de dado (teia do acervo), nem para ilustração de LP: aí é SVG autoral (§5).
cadeiras: todas (quem desenha figura). Dono da régua é produto (design/diagramas.md); catálogo de tipos é do arquiteto; dono da skill, como implementadora, é produto.
compatibility: lê `platafirma-ui/src/tokens.css` (clone em ~/AI) — sem ele não gera. PNG exige Playwright/Chromium no host (`--png`); medição de encaixe exige Inter instalada e PIL. Rota alternativa para wiki é Kroki (Mermaid, d2) com `aplicacao/mermaid-familias.mmd`.
---

# Diagrama — figura de arquitetura pela régua do DS

Os diagramas dos provedores de nuvem leem melhor que os desenhados à mão por um
motivo só: são um design system de diagrama aplicado sem exceção — cor fixa por
categoria de recurso, glifo por tipo, caixa branca, contenção por fronteira. Esta
skill faz o mesmo com o DS da casa. Quem desenha decide o **modelo** (o que existe e
quem fala com quem); forma, cor, tipo e fio não se decidem por figura.

## Quando a figura é obrigatória

Três casos (§1 do canônico): fluxo com 3+ passos e ramo; estrutura em camadas ou
contenção; relação N:N. Fora deles, prosa vence — figura decorativa é ruído com
custo de manutenção.

## O loop

1. **Escreve o modelo** em JSON (formato abaixo): zonas, caixas, arestas, fronteira.
   Cada caixa declara `categoria` (a do catálogo) e `tipo`. Copia de
   `exemplo/topologia.json` e edita.
2. **Escolhe a vista pelo público**, não pelo gosto:
   - `engenharia` — estilo provedor de nuvem: caixa branca, glifo de família no
     canto, zona com fio. Para slide técnico e wiki de operação.
   - `diretoria` — estilo C4: caixa cheia na cor da família, rótulo de tipo,
     fronteira do sistema. Para slide executivo e página de visão geral.
   Uma vista não substitui a outra; o modelo é um só.
3. **Gera:** `python3 skills/diagrama/gerar.py <modelo>.json --saida <dir>` (as duas
   vistas por padrão; `--vista` escolhe uma; `--png` acrescenta PNG a 2x, só para slide).
4. **Lê o veredito do gerador.** Ele trava em três casos e não tenta consertar por
   conta: mais de quatro categorias na figura; categoria fora do catálogo; rótulo
   que não cabe na caixa (medido com a Inter). Conserto é no modelo — junta caixas,
   corta a figura em duas, encurta o subtítulo, alarga a caixa.
5. **Publica a fonte, não só a saída.** O JSON mora em `diagramas/<nome>.json` na raiz
   do repo da matéria (`arq:0051`, uma figura uma fonte). SVG vai para wiki e LP;
   PNG só para slide, e sempre com o SVG ao lado.

## O modelo

```json
{
  "largura": 1000, "altura": 600,
  "fronteira": {"nome": "PlataFirma", "x": 50, "y": 215, "w": 920, "h": 345},
  "zonas":  [{"id": "sup", "nome": "superfícies", "categoria": "superficie",
              "x": 50, "y": 40, "w": 920, "h": 130, "fora_da_fronteira": true}],
  "caixas": [{"id": "mcp", "titulo": "claudinho-mcp", "subtitulo": "porta MCP",
              "categoria": "porta", "tipo": "MCP", "x": 160, "y": 250, "w": 340, "h": 84}],
  "arestas": [{"pontos": [[330, 170], [330, 250]], "rotulo": "chama"}]
}
```

- `categoria` — uma das oito: `persistencia`, `servico`, `superficie`, `porta`,
  `conhecimento`, `host`, `mensageria`, `identidade`. A cor vem daí e é a mesma em
  toda figura da casa. Caixa de **cadeira** (ator) não entra aqui — usa a cor de
  cadeira, e por ora se desenha à parte.
- `tipo` — texto livre dentro da categoria (`MCP`, `túnel`, `repo`, `wiki`…); vira o
  `[tipo]` da vista diretoria. `verbo` tem glifo próprio (⚙) dentro de `servico`.
- Componente com dois papéis (proxy de auth = porta + identidade) leva a
  `categoria` do papel **que a figura está contando**.
- Geometria é sua; o gerador não faz layout. Zona aninhada até dois níveis;
  terceiro nível vira figura própria.

## O que a skill fixa e você não redecide

- Tipo: rótulo 16px semibold, corpo 14px medium, nada abaixo de 14 — o que se lê a
  60 cm some em projeção. Fio 1,5px em tinta (`diagram-stroke`), não cinza de UI.
- Cor **fixa por categoria** (`family-1..8`), glifo repetindo a família, teto de
  quatro categorias por figura, semáforo reservado a estado, nada por caixa.
- Cor nunca carrega sozinha: em preto e branco a figura tem que continuar legível.
- Sem sombra, gradiente, 3D, ícone junto de rótulo curto, texto em caixa-alta.
- Tudo isso vem de `tokens.css` em tempo de geração. **Não copie hex para o modelo
  nem para o gerador** — é por onde o valor cru volta (§5).

## Slide

Slide de engenharia segue a régua. **Slide executivo pode variar da paleta por
ordem superior**; a variação é do slide e não volta para wiki, LP nem para o
catálogo. Prefira o SVG dentro do `.pptx`; PNG a 2x quando a ferramenta não
carregar SVG.

## Gabarito

`exemplo/topologia.json` → vistas aprovadas pelo dono em 05/09/2026, publicadas em
`platafirma-ui/exemplo/diagrama/`. Toda mudança no gerador regenera o gabarito e
compara.
