# chapéu corpus — o corpus achável, até a seção

Vestido, o objeto é a cobertura: o corpus tem a resposta, está seccionado e catalogado de
modo que um motor a alcance, e há gabarito ancorado na seção para saber se alcançou? Do
índice à busca é de ia (`arq:0119` §1): o corte da seção em trecho, o embedder, o rerank, a
avaliação, a abstenção, a latência, o que se monitora e o que o gabarito precisa cobrir.
Aqui se responde pela metade que é propriedade do corpus: a busca que falhou se
diagnostica primeiro no corpus, depois no motor, nunca na ordem inversa.

## a) Espaço de problema

- **Cobertura** — a obra que responde está na partição certa, servível na escada
  (impressão, índice), ou o «não tem» é obra que existe e não foi servida?
- **Seção** — a obra está seccionada pela estrutura que o documento tem (título, artigo,
  capítulo, breadcrumb), com razão declarada? A seção é fato do texto; o corte dela em
  trecho, o teto e a subdivisão da seção gorda são da ia.
- **Metadado e ficha de conceitos** — espécie, subdomínio, conceito declarado e
  obra-âncora estão preenchidos, para o filtro do chapéu e a expansão do motor apontarem
  para a prateleira certa?
- **Gabarito** — o gabarito cobre o que a ia pediu, com o alvo ancorado na seção (chave,
  digest, hash do trecho), versionado e com linhagem a cada re-âncora?
- **Vocabulário** — o vocabulário que a expansão usa (conceito declarado, rótulo
  alternativo) cobre o problema do vocabulário, ou a consulta no termo do dono cai fora do
  termo da prateleira?
- **Vitrine** — a leitura humana do baseline (o que serve, o que mede) está no ar e diz
  o mesmo que a cadeia viva, ou reporta de uma visão defasada?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «a resposta está no corpus, e servível?» —
  antes de culpar o modelo ou trocar o embedding. Diagnosticar o motor com o corpus
  furado é a falha nativa desta matéria.
- Resposta boa diz onde a cobertura falhou (partição, escada, seção, metadado,
  vocabulário) e o que fecha; quando o corpus cobre e o motor não traz, diz isso e
  passa à ia, chapéu recuperacao, com o gabarito na mão. Resposta ruim é «o motor não
  achou» sem ter medido o que havia para achar.
- «X obras já na bancada» sem a escada de cada uma é número, não estado; a vitrine
  diz `indeterminavel` quando não sabe, não zero.

## c) Consulta dirigida

O canônico volta pela faceta `curadoria-acervo` (escada, partição, impressão, seção)
com apoio de `estudos-ontologias` para o vocabulário. Os rótulos entram inteiros na
pergunta, em fronteira de palavra: «cobertura da partição obra para governança» casa;
«a busca não acha» casa raso. Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| a obra existe e está servível | `curadoria-acervo` + `casa` | escada de serviço · partição · impressão · spec_acervo | a cadeia se confere na fonte, não se lembra |
| como seccionar e com que metadado | `curadoria-acervo` | seção · breadcrumb · espécie · subdomínio · conceito declarado | a seção estrutural é decisão arquivística; o corte em trecho é da ia |
| o termo do dono não casa o da prateleira | `estudos-ontologias` | problema do vocabulário · controle de autoridade · expansão semântica | a expansão é vocabulário controlado aplicado à consulta |
| o gabarito que a ia pediu | `curadoria-acervo` + `casa` | gabarito rotulado · protocolo-medicao-rag | a ia diz o que cobrir; a âncora e a versão são daqui |
| o motor pôr a resposta no topo | consultar ia, chapéu recuperacao | ranqueamento multiestágio · embedding · avaliação de recuperação | leio para saber o que perguntar; o veredito do motor é da ia |
| o custo de servir a consulta | consultar chapéu engenharia | índice · partição | a forma do dado decide o que o motor paga |

Filtrar por `ia` traz o mecanismo, não a cobertura: o canônico de «está lá?» vem sempre
de `curadoria-acervo`. Conceito «recuperação como produto de dado» segue sem obra-âncora
no acervo — lacuna a fechar na repartição, não a inventar.
