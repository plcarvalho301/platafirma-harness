# chapéu recuperação — o corpus como se apresenta ao motor

Vestido, o objeto é a cobertura: o corpus tem a resposta, está seccionado e rotulado de
modo que um motor a alcance, e há gabarito para saber se alcançou? O motor achar bem —
embedding, rerank, harness de avaliação, abstenção, latência — é de ia. Aqui se
responde pela metade que é propriedade do corpus: a busca que falhou se diagnostica
primeiro no corpus, depois no motor, nunca na ordem inversa.

## a) Espaço de problema

- **Cobertura** — a obra que responde está na partição certa, servível na escada
  (impressão, índice, vetor), ou o «não tem» é obra que existe e não foi servida?
- **Seção** — a obra está seccionada por estrutura (título, seção, breadcrumb) com
  razão declarada, ou por tamanho fixo que corta a resposta ao meio?
- **Metadado** — espécie, subdomínio, conceito declarado e obra-âncora estão
  preenchidos, para o filtro do chapéu apontar para a prateleira certa?
- **Gabarito** — há consultas com resposta conhecida no próprio corpus, por partição e
  por chapéu, para medir qualquer mudança de seção, metadado ou motor?
- **Vocabulário** — a expansão semântica (conceito declarado, rótulo alternativo) cobre
  o problema do vocabulário, ou a consulta no termo do dono cai fora do termo da
  prateleira?
- **Vitrine** — a leitura humana do baseline (o que serve, o que mede) está no ar e diz
  o mesmo que a cadeia viva, ou reporta de uma visão defasada?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «a resposta está no corpus, e servível?» —
  antes de culpar o modelo ou trocar o embedding. Diagnosticar o motor com o corpus
  furado é a falha nativa desta matéria.
- Resposta boa diz onde a cobertura falhou (partição, escada, seção, metadado,
  vocabulário) e o que fecha; quando o corpus cobre e o motor não traz, diz isso e
  passa a ia com o gabarito na mão. Resposta ruim é «o motor não achou» sem ter medido
  o que havia para achar.
- «X obras já na bancada» sem a escada de cada uma é número, não estado; a vitrine
  diz `indeterminavel` quando não sabe, não zero.

## c) Consulta dirigida

O canônico volta pela faceta `curadoria-acervo` (escada, partição, impressão, seção)
com apoio de `estudos-ontologias` para o vocabulário. Os rótulos entram inteiros na
pergunta, em fronteira de palavra: «cobertura da partição obra para governança» casa;
«a busca não acha» casa raso. Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| a obra existe e está servível | `curadoria-acervo` + `casa` | escada de serviço · partição · impressão · índice · spec_acervo · spec_motor | a cadeia de quatro elos se confere na fonte, não se lembra |
| como seccionar e com que metadado | `curadoria-acervo` | seção · breadcrumb · espécie · subdomínio · conceito declarado | chunk por estrutura é decisão arquivística, não de modelo |
| o termo do dono não casa o da prateleira | `estudos-ontologias` | problema do vocabulário · controle de autoridade · expansão semântica | a expansão é vocabulário controlado aplicado à consulta |
| o gabarito a entregar a ia | `curadoria-acervo` | gabarito rotulado · cobertura | é o insumo declarado que o harness de avaliação consome |
| o motor pôr a resposta no topo | `dominio=["ia"]` | rerank · embedding · avaliação de recuperação · abstenção | leio para saber o que perguntar; o veredito de modelo é da ia |
| o custo de servir a consulta | consultar chapéu engenharia | índice · partição | a forma do dado decide o que o motor paga |

Filtrar por `ia` traz o mecanismo, não a cobertura: o canônico de «está lá?» vem sempre
de `curadoria-acervo`. Conceito «recuperação como produto de dado» segue sem obra-âncora
no acervo — lacuna a fechar na repartição, não a inventar.
