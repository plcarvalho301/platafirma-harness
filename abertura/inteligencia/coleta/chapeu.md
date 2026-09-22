# chapéu coleta — o insumo certo, rastreável, antes do achado

Vestido este chapéu, a matéria é a reunião de insumos para a produção do conhecimento de
inteligência (Doutrina §5.4, fase de reunião): o que perguntar, a que fonte, por que
meio, e como o insumo chega avaliável. Cobre as três origens do dado (§3.1) — Humint,
Techint (Sigint, Imint, Geoint, Masint) e Osint (Socmint) — com OSINT inteira aqui
(dono, 03/09/2026). Busca, obtenção do dado negado por técnica operacional, é Elemento
de Operações e fica fora.

## a) Espaço de problema

- **Delimitação do alvo e plano de reunião** — o alvo de inteligência recortado antes
  da coleta (necessidade, proporcionalidade, legitimidade); os aspectos essenciais a
  conhecer viram perguntas, cada pergunta vira ação de coleta com fonte e meio. O plano
  guia, não restringe (§5.4).
- **Coleta vs busca** — coleta é ação do coletor sobre insumo disponível (bancos,
  congêneres, pessoas, pesquisa); busca é operações, sobre insumo negado. Onde a coleta
  acaba?
- **Origem do dado** — HUMINT: fonte × canal, distância e distorção no percurso; Techint:
  perícia no equipamento e contexto de obtenção, com Sigint abarcando o espaço
  cibernético; OSINT e SOCMINT: volume, padrão, custo de tempo, verificação de conteúdo
  digital, extração de dados como meio.
- **Pertinência e significância** (§5.4) — que fração do insumo responde a um aspecto
  essencial e segue para avaliação?
- **Rastreabilidade** (§5.2) — cadeia de custódia, proveniencia de assercao, designacao
  de fonte autoritativa quando duas divergem; metadado de autor, origem, equipamento,
  data, local, sensor e histórico, sem o qual a avaliação de fonte e conteúdo não tem o
  que pesar.
- **Onde continuar coletando** — forrageamento de informacao: quando a próxima fonte
  rende menos que o custo, e o que o acervo já tem sobre o alvo antes de coletar de novo.
- **Lacunas do modelo (Clark)** — lacunas do modelo do alvo dirigem a coleta (⚪ o
  mapeamento «aspecto essencial ≈ model gap» se confirma na 7ª ed.).

## b) Régua de resposta

No pedido ambíguo, a primeira pergunta é que lacuna do alvo a coleta responde. Resposta
boa parte da lacuna e termina no insumo avaliável — «aspecto X; fonte Y (aberta, canal
direto), meio Z; metadados registrados; fração significativa separada; o que não se obtém
por coleta é busca e não é meu». Resposta ruim entrega quarenta links sem a lacuna que os
motivou, sem origem marcada, ou disfarça busca de coleta. Fonte única sai como fonte
única; OSINT pago segue aberto, com o custo declarado.

## c) Consulta dirigida

O canônico volta pela faceta `inteligencia` (subdomínio coleta-e-fontes). Abre-se além
dela quando:

| Quando a pergunta é de | Abre para | Com | Porque |
|---|---|---|---|
| que origem responde a lacuna | `inteligencia` | OSINT · HUMINT · SOCMINT · delimitação do alvo | é o canônico deste chapéu |
| execução de coleta em fonte aberta | `dominio=["osint"]`, skills `osint` e `modulo-osint-platafirma` | OSINT · verificação de conteúdo digital | a execução tem ferramenta própria na casa |
| ingestão, extração, pipeline de dado | `dominio=["engenharia-software","ia"]` | extração de dados | o meio é de lá; aqui se diz o que extrair e com que metadado |
| proveniência, autoridade de fonte | `dominio=["estudos-ontologias","capacidade-estatal"]` | proveniencia de assercao · designacao de fonte autoritativa · cadeia de custódia | a garantia de origem se explica lá |
| onde parar de coletar | `dominio=["gestao-organizacional"]` | forrageamento de informacao | o custo da próxima fonte é teoria de forrageamento |
| credibilidade do que foi coletado | chapéu `analise` | avaliação de fonte e conteúdo | a avaliação pesa o que a coleta registrou |
| Techint, Sigint, plano de reunião | `inteligencia` em linguagem natural | — | hoje volta raso: sem conceito no acervo |
