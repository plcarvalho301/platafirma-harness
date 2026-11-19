# Gabarito: o card que se lê sem quem o escreveu

Entidade: gabarito

Rode antes de pedir parecer sobre um épico ou uma feature, e antes de gravar um
comentário, sobre o que você escreveu ou reescreveu: seção a seção no corpo, item a item
no inventário (as listas de peças, regras de negócio e produtos documentais ligadas à
feature), a primeira linha e o argumento no comentário. Ele responde uma pergunta só:
cada parte do card se entende na primeira leitura, por quem não a escreveu?

O lint do card confere a forma por máquina. Os itens daqui se conferem pela leitura, e
quem roda é quem escreveu.

Na feature aberta que ainda traz Peças, Regras e Produtos documentais no corpo, C8 não
vale, e os itens do inventário valem para as linhas do corpo até a cadeira dona
reescrever a feature.

## Corpo do épico e da feature

- **C1 · Problema.** Passa quando todo termo da casa leva o nome comum ao lado. Se
  falha, ponha o nome comum na primeira vez.
- **C2 · Problema.** Passa quando nenhuma frase diz o que falta construir («não tem»,
  «falta um comando que», «mora em X e não em Y»). Se falha, reescreva pelo que a pessoa
  tenta e onde trava.
- **C3 · Problema.** Passa quando o custo de quem sofre está dito. Se falha, diga o
  custo; sem ele, pergunte à cadeira dona antes de pedir parecer.
- **C4 · Solução.** Passa quando as frases dizem a ideia, sem «quando». Se falha, leve a
  frase com «quando» a Uso ou ao inventário.
- **C5 · Uso.** Passa quando, em cada cena, quem age é uma pessoa ou uma cadeira. Se
  falha, leve a cena em que age um componente ao inventário, como regra.
- **C6 · Sai quando.** Passa quando cada conferência tem a linha dela, com as três
  partes. Se falha, parta a linha ou complete as partes.
- **C7 · Feature apostada.** Passa quando o Apetite está escrito, em fitas e com o corte.
  Se falha, escreva o que o dono apostou.
- **C8 · Feature.** Passa quando o corpo não repete peça, regra nem produto documental do
  inventário. Se falha, tire do corpo; vale o item.
- **C9 · Épico.** Passa quando nenhuma linha fora de Features nomeia peça, verbo, arquivo
  ou card. Se falha, troque pelo que muda para quem usa.
- **C10 · Épico.** Passa quando cada linha do Resultado tem a dela na Medida. Se falha,
  escreva a medida, ou corte o resultado.
- **C11 · Épico.** Passa quando cada linha de Features diz o papel da feature, e não o
  que ela tem dentro. Se falha, corte o conteúdo, que mora na feature.

## Inventário da feature

- **I1 · Regra.** Passa quando mudar a frase altera o que a casa faz, guarda ou cita. Se
  falha, é mecanismo: leve-o ao mecanismo de uma regra ou à story.
- **I2 · Regra.** Passa quando a frase diz a regra, e não um caso. Se falha, escreva a
  regra numa oração; o caso desce para os casos.
- **I3 · Regra.** Passa quando o porquê diz um motivo, e não a frase com outras palavras.
  Se falha, escreva o motivo; sem ele, pergunte a quem pediu a regra.
- **I4 · Peça.** Passa quando o item nomeia uma coisa que se aponta e diz o que ela faz
  para quem a usa. Se falha, o comportamento de outra peça vira regra, o documento vira
  produto documental e a ação vira story.

## Comentário

- **M1 · Primeira linha.** Passa quando cabe em 90 caracteres e diz o ponto inteiro, pelo
  nome das coisas. Se falha, corte até caber; o detalhe desce para o argumento.
- **M2 · Primeira linha.** Passa quando trata um tema só. Se falha, parta em dois
  comentários.
- **M3 · Comentário.** Passa quando cita item do inventário pela chave ou pelo nome, e
  nunca pela posição numa lista. Se falha, troque pela chave.
- **M4 · Porque.** Passa quando, fora do insumo, cabe num parágrafo. Se falha, leve o
  resto a um insumo e aponte para ele.
- **M5 · Porque.** Passa quando, fora do insumo, não cita obra de fora. Se falha, leve a
  obra a um insumo; fica o fato medido na casa.
- **M6 · Buraco.** Passa quando a linha Tamanho diz se a falha derruba a feature,
  restringe o que ela entrega ou é custo a pesar. Se falha, escreva a linha Tamanho.
- **M7 · Insumo.** Passa quando a linha Traz diz o que muda para este card. Se falha,
  escreva a linha.
- **M8 · Fecho.** Passa quando diz em palavras o que mudou no corpo ou no inventário. Se
  falha, troque o rótulo solto pelo que mudou.

Aprovado, o texto segue. Reprovado, volta ao texto, e o gabarito roda de novo até nenhum
item falhar.
