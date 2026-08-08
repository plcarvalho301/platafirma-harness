# Rodada 2 — extrato de julgamento `[claudinha-produto]`

Objeto: as 84 propostas de `b-propostas-consolidado.md` (66 conceitos únicos), cada conceito considerado isoladamente. Réguas aplicadas: definição e solução de problemas + affordance, contra `Ajuda:Escrever uma página` e `Estudos-ontologias/conceito`. Fora do escopo: relacionamentos entre conceitos, duplicações e colisões com a base (tarefa de conhecimento; já flagradas em `c-propostas-ficha.md`).

Perguntas do julgamento:

* **(a)** o conceito ajuda o leitor a entender um problema concreto?
* **(b)** a definição é compreensível para um humano?
* **(c)** o conceito tem aptidão de uso fora do domínio em alguma escala (não tunnel-visioned)?
* **(d)** a definição sustenta uma página completa de conceito?

## Veredito geral

* **(a)** não todos — 5 falhas ou quase-falhas. Padrão da falha: definição que recita o instrumento (decreto, framework) sem dizer o que quebra na ausência do conceito. O falseador em geral carrega o problema que a definição omitiu — sinal de que o proponente sabia o problema e não o escreveu na régua.
* **(b)** não todos — 1 falha dura, 4 borderline. Padrão da falha: jargão da tradição de origem sem desempacotamento (OntoClean, BIZBOK, COBIT, IR).
* **(c)** quase todos passam — os falseadores forçaram mecanismo transponível na maioria. 4 falhas/quase-falhas, todas por régua soldada ao instrumento que a instituiu.
* **(d)** todos os aprovados em (a)(b)(c) sustentam página; os reprovados exigem reescrita da definição antes. Achado sistemático adicional abaixo.

## Casos mais graves (ordem de gravidade)

* **criterio-de-identidade** `[claudinho-conhecimento]` — falha (b), dura
   * "tipo sortal", "tipo anti-rígido (papel, fase)", "subsumir o tipo rígido": três termos técnicos de OntoClean encadeados sem desempacotamento. Humano fora da ontologia formal não extrai a régua.
   * conceito excelente, definição ilegível; reescrever articulando o mecanismo em termos próprios (quando dois registros são a mesma coisa; o que pode mudar sem deixar de ser).
* **governanca-publica** `[claudinha-gestao-estrategica]` — falha (a), quase-falha (c), affordance ausente
   * recitação do Decreto 9.203: "mecanismos de liderança, estratégia e controle... avaliar, direcionar e monitorar". Não diz o que quebra sem governança; a tríade é a do pai proposto (`governanca`) e a distinção própria fica só em "valor público".
   * sem sinal de uso: a definição não permite ao leitor operar veredito algum.
* **credenciamento-de-seguranca** `[claudinho-seguranca]` — falha (a), falha (c)
   * recitação legal: enumera requisitos do decreto; "sem habilitação não há tratamento lícito" é a norma, não o problema. Mecanismo só decide dentro do universo do próprio decreto.
   * contraste com o vizinho `necessidade-de-conhecer`, que extrai mecanismo transponível (dois eixos independentes, conjunção obrigatória) da mesma família normativa — prova de que dava para fazer.
* **fluxo-de-valor** `[claudinho-arquiteto]` — falha (b), quase-falha (a)
   * "acumula itens de valor até a proposição de valor final", "habilitado por capacidades": BIZBOK-speak com dois termos indefinidos dentro da régua. Definição inteira por contraste taxonômico (vs capability, vs processo); o problema que o conceito resolve não aparece.
* **gestao-por-resultado-pactuado** `[claudinha-gestao-estrategica]` — falha (c)
   * régua soldada ao instrumento: "termo de ciência e responsabilidade" é peça do PGD, não mecanismo. O mecanismo real (aferição contra o pactuado substitui controle de presença) transpõe; como escrito, só decide dentro do programa federal.
* **interacao-tardia** `[claudinho-IA]` — quase-falha (a), quase-falha (c)
   * ficha de catálogo de técnica (ColBERT): o trade-off está dito ("granularidade ao preço de ordem de grandeza de índice") mas o problema do leitor fica implícito — a consulta multi-conceito que o vetor único borra num ponto médio sem documento correspondente.
   * o mecanismo não decide nada fora de recuperação, diferente dos vizinhos da mesma cadeira (`ranqueamento-multiestagio` transpõe para triagem em funil; `transporte-de-estado-entre-sessoes`, para handoff). O mais estreito do lote.
   * único caso do lote em que a natureza parece ser variante de implementação, não conceito: cabe como seção de `recuperacao-densa`, que a própria régua declara como pai. Decisão de vocabulário — claudinho-conhecimento com claudinho-IA.
* **gestao-estrategica** `[claudinha-gestao-estrategica]` — quase-falha (a)
   * descrição genérica de processo (formular, desdobrar, monitorar, revisar); a distinção própria ("revisão por desvio medido, não por calendário" + plano ≠ processo) existe mas está enterrada. Reescrever com ela na frente.

## Casos borderline (aprovam com reparo pontual)

* **expressividade-vs-tratabilidade** `[claudinho-conhecimento]` — (b): "construtor", "fragmento (perfil)", "axioma admissível" pesam, mas a frase-núcleo ("ganhar poder de afirmação custa computabilidade") é clara e salva. Reordenar: núcleo primeiro.
* **cascata-de-objetivos** `[claudinho-arquiteto]` — (b): "objetivo de alinhamento" é termo COBIT sem definição. Uma aposição resolve.
* **abertura-por-padrao** `[claudinho-arquiteto]` — (b): segunda frase é voltada ao classificador ("decide contra classificação da informação... regimes de base legal") e pressupõe outras réguas. A primeira frase sozinha passa.
* **design-centrado-no-humano** `[claudinha-produto]` — (a): moldura de checklist de conformidade ISO; o problema (sistemas rejeitados pelos usuários) mora no falseador, não na definição. Trazer para a régua.
* **servico-de-ti** `[claudinho-TI]` — (a): a distinção serviço/componente está posta, mas não o que quebra ao confundi-los (catálogo inflado, cobrança de item sem valor). Uma frase resolve.

## Achado sistemático — rótulo dentro da definição

Regra derivada nº 1 de `Estudos-ontologias/conceito`: a definição não pode conter o rótulo. Cinco propostas contêm, no padrão "Algo é X se...":

* **esteira-de-implantacao**, **fabrica-de-software**, **desempenho-de-entrega**, **servico-de-ti** `[claudinho-TI]`; **registro-de-decisao-arquitetural** `[claudinho-TI]` (variante "Um documento é registro de decisão se...").

Não é circularidade — a cláusula articula o teste de decidibilidade, o espírito da regra está atendido. Mas a letra reprova, e a correção é mecânica: reescrever o teste sem o rótulo ("nenhuma mudança chega ao ar por fora dela" já decide sozinha). Concentrado em claudinho-TI; vale aviso de estilo à cadeira.

## O que passa limpo

Os 49 restantes aprovam nas quatro perguntas. Destaques de qualidade de régua, como referência de forma para as reescritas: **janela-de-exposicao**, **padrao-como-politica**, **requisito-verificavel**, **delegado-confuso** `[claudinho-seguranca]`; **erro-de-tipo-tres**, **corte-por-capacidade** `[claudinha-gestao-estrategica]`; **mediacao-do-loop-agentico**, **transporte-de-estado-entre-sessoes** `[claudinho-IA]`; **descricao-multinivel**, **documento-de-arquivo** `[claudinho-conhecimento]` — todos nomeiam o problema, decidem sozinhos e transpõem sem analogia.
