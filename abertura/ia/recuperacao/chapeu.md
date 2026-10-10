# chapéu recuperacao — a busca achando bem, do índice ao serviço

Vestido, o objeto é o acerto da busca: dada a obra seccionada e catalogada que dados
entrega, o motor põe no topo o trecho que responde, diz «não sei» quando o acervo não
tem, e o acerto se mede contra o gabarito? Do índice ao serviço é daqui: o corte da seção
em trecho, o embedder, a fusão, o rerank, o prior, o que se monitora e o que o gabarito
precisa cobrir. A obra até a seção, a ficha de conceitos e a guarda do gabarito são de
dados (`arq:0119` §1). Quanto custa servir é do chapéu engenharia-de-harness.

## a) Espaço de problema

- **Trecho** — o corte da seção em trecho é projeção do índice: o teto sai da janela do
  embedder, a seção gorda se subdivide, o corte semântico usa o mesmo embedder que serve.
  Trocou o embedder, o corte se revê no mesmo ato; o trecho nunca reescreve a seção.
- **Busca** — o embedder, o braço léxico, a fusão, o rerank e o prior põem o trecho certo
  no topo, ou o certo estava no índice e afundou?
- **O que se monitora** — que métrica, por estrato e por partição, com que limiar e que
  alarme, mostra na face motor do plano de controle se a busca melhorou, piorou ou empatou;
  métrica sem ato que a siga sai.
- **Gabarito** — o que ele precisa cobrir (estratos, tamanho, sem obra) para a métrica
  valer; dados o monta, ancora na seção e versiona, o dono marca o domínio.
- **Abstenção** — a cobertura que o motor declara bate com o que o acervo tem, nas três
  direções: correta, falsa, inventada.
- **Juiz** — o juiz-modelo que julga as rodadas passou do piso contra a marca do dono, ou
  a métrica sobe sem a coisa que importa subir?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o trecho certo estava no índice, e onde ele
  ficou na lista?» — depois de dados ter dito que a obra está no corpus e seccionada.
  Cobertura antes de relevância: culpar o motor com o corpus furado é erro; culpar o
  corpus com o trecho certo no índice e fora do topo é o erro nativo daqui.
- Resposta boa sai em delta contra o servido, por estrato, com o carimbo da rodada e o
  parâmetro a mudar (`motor ajuste`); resposta ruim é número absoluto sem comparação, ou
  medida sem corte.
- Mudança de corte, de embedder ou de rerank invalida a linha de base: a rodada nova se
  carimba e se compara sobre a mesma versão do gabarito.

## c) Consulta dirigida

O canônico volta pela faceta `dominio=["ia"]` (recuperação, avaliação, abstenção), com
`casa` para o contrato e o protocolo. Os rótulos entram inteiros na pergunta, em fronteira
de palavra: «ranqueamento multiestágio no estrato sentido» casa; «a busca está ruim» casa
raso. Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| o trecho certo não veio ao topo | `dominio=["ia"]` | ranqueamento multiestágio · embedding · avaliação de recuperação | a relevância é do motor; o mecanismo vem do canônico de IA |
| como cortar a seção em trecho | `dominio=["ia"]` + `casa` | chunking · janela de contexto · spec deteccao-semantica-de-secao | o teto e o corte semântico dependem do embedder |
| o que medir e com que tamanho | `casa` | protocolo-medicao-rag · gabarito rotulado · validade de construto | o protocolo fixa estrato, poder e regra de decisão antes da rodada |
| o motor dizer «não sei» com critério | `dominio=["ia"]` | abstenção calibrada · cobertura e relevância | gerar e julgar são competências distintas |
| a obra está no corpus e seccionada | consultar dados, chapéu corpus | cobertura · seção · ficha de conceitos | cobertura é de dados e se diagnostica antes |
| quanto custa servir a busca | consultar chapéu engenharia-de-harness | custo por inferência · complexidade assintótica | o acerto é daqui, o custo é de lá |

Filtrar por `dados` traz a cobertura, não a relevância; o canônico de «o motor achou
bem?» vem sempre de `ia`.
