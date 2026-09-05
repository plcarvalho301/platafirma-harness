# caderno — produtização

Aprendizado durável do chapéu; fato, card e estado ficam na mesa e no rastreador.

## Spec de produto é PRD, não racional

- Spec de produto se escreve publicizável e atemporal: presente do indicativo, para quem nunca esteve na conversa. Fora dela: card, ADR, commit, data de decisão, estado de código («hoje 0»), citação do dono, nome de cadeira, marca de tecnologia, bench de terceiro.
- Análise de mercado, concorrente e bench são MRD e ficam em documento de racional (baseline do épico). O PRD descreve o produto; o racional aponta para ele, nunca o contrário (人人都是产品经理 §3.3.1; Adzic, *Specification by Example*, cap. 8; *Cracking the PM Career*: curto, alternativas em apêndice).
- Forma que serviu: o que é · para quem (perfis com nome de papel, ordem de adoção) · por camada: o que entrega, requisitos, o que conta como pronto, o que é do adotante · adoção · fora do produto · glossário.
- Antes de escrever spec, consultar o acervo pelo gênero do documento — a primeira versão saiu sem isso e foi refeita inteira.

## Parecer e card na mesma régua da spec

- Documento que uma pessoa lê corrido não carrega ponteiro de seção nem citação entre aspas: a frase diz a coisa, não o endereço. Ponteiro só onde alguém vai conferir com ferramenta (âncora de contestação, commit, card).
- Card: uma linha por campo (Problema / Resultado / Medida / Fora / Sai quando), sem racional no corpo; o racional vai em comentário ou documento apontado.
- Rollout se escreve como escada: um release por perfil de usuário, na ordem de adoção; cada release lista o que entra, a ordem interna e um gate que acontece com gente de fora. Sem a escada, os goalposts ficam dispersos.

## Decisão que atravessa cadeira não é parecer, é minuta

- Parecer de produto julga o que já está escrito; ele não decide corte que muda o trabalho de outras cadeiras. Onde a decisão redistribui matéria alheia, o instrumento é a minuta circulada, e cada cadeira responde por posição ou abstenção declarada.
- O sinal de que errei o instrumento: levo ao dono como pergunta de sim-ou-não uma coisa que ele devolve como «é a decisão mais importante deste épico». Pergunta grande demais para caber em resposta binária é minuta, não item de lista.
- Deliberação é trabalho e por isso tem card próprio, com o `Fora` dizendo que a feature decide e não move. O que a minuta produz — a decisão de arquitetura — é o que vira gate na escada de release; gate se ancora em artefato conferível, nunca no juízo de quem embrulhou o pacote.

## Armadilhas medidas

- Reduzir «porta humana» à busca da wiki esquece a exposição do acervo — o operador lê o acervo pela tela.
- Design system é entregável do produto (biblioteca publicada que toda tela consome), não «só DS».
- «Entrega não é medida» rebaixa release e distro na fila, mas não os apaga: o que muda é a ordem.
- Pendurar card terminal (descartada) sob feature aberta mata a feature pelo derivado; conferir estado real antes de reparentar — a fila pode estar velha.
- Formalizar minuta em spec não termina na spec. A régua CANÔNICA (o documento) e a régua SERVIDA (a página viva que quem trabalha abre) são dois entregáveis, e só a segunda é usada. Publiquei a explicação de um styleguide apontando para a página servida antes de ela existir: ponteiro vermelho, entrega pela metade, e o handoff da outra cadeira só pedia os dois primeiros. Antes de relatar entrega, abrir todo ponteiro que a página publicada cria.

## Posicionar não é nomear a peça trocável

- O kernel fixou que o modelo e os atributos são trocáveis, a estrutura não. O corolário de posicionamento: os comandos da casa (o harness) e a LLM são as peças trocáveis; nomear o produto por elas é dar o nome à coisa que se joga fora. O produto é a estrutura — conhecimento organizado que sobrevive à troca de quem sai. A LLM aparece como consequência (operável por agente), nunca como manchete.
- O que é IA e é central não é a LLM, é o embedding — a busca por sentido em vez de palavra exata. Ela sustenta a promessa mesmo com a IA generativa desligada, a mesma condição do colega que lê a wiki sem agente. O público não distingue embedding de LLM e não precisa; a promessa se diz em português (acha pelo sentido, não pela palavra).
- Pitch e posicionamento são camadas distintas, e o erro caro é o pitch definir o posicionamento. O pitch pode entrar pela porta da moda (o assistente que entende os documentos do órgão); o posicionamento não pode mentir, senão a pessoa adota, se decepciona e sai, e adoção é o norte. A camada de dentro segura a régua: o conhecimento é do órgão, o modelo é trocável, sem aprisionamento a fornecedor. Uma abre a porta, a outra evita a devolução.
- No recorte entre produto e instância, a linha corta o dado, não a ferramenta. Comando é código genérico e vai inteiro ao pacote público; o que se reparte é o conteúdo que cada comando opera (personas, acervo, mesa). Perguntar em que camada fica o harness é a pergunta errada: ele atravessa as três e não se reparte.
- Decisão de discovery que o dono ainda não maturou não é cobrança minha, mesmo listada como aberta com ele na mesa. Quando o rosto do primeiro adotante depende de um pré-requisito que também é dele (o pronto de um artefato), os dois se olham no espelho — o rosto define o pronto e o pronto filtra os rostos. Empurrar o rosto antes do pré-requisito é chutar; o item espera o dono trazer.

## Régua que o dono devolve pede prova conferível

- Duas devoluções seguidas na mesma régua fina pediram a mesma coisa em formas diferentes: no benchmark, Medições como tabela candidato × funcionalidade; no parecer, a lista de fontes ao fim. Nenhuma pediu mais prosa nem mais rigor de voz — pediram a peça que se confere de relance. Quando ele devolve régua minha, a hipótese primeira é que falta o conferível, não que falta explicação.
- Corolário de escrita: o estrato central de um tipo carrega a PROVA (a tabela, a lista de fontes, o comando literal), e a prosa em volta existe para situá-la. Régua que descreve só voz, sem nomear a peça conferível do tipo, sai pela metade.

## Ordem do dono que cruza linha de titularidade

- Régua de escrita de cada estrato é minha; quais estratos e em que ordem é de dados. Ordem do dono que acrescenta ou tira estrato muda titularidade alheia por dentro da minha caneta. O que serviu: escrever assim mesmo — a ordem é dele —, declarar a divergência dentro do próprio documento, no estrato de aberto, e rotear o espelhamento por carta a quem é dono da estrutura. Recusar por titularidade trava o dono; absorver calado cria duas fontes da mesma coisa, que é o que o arq:0051 existe para impedir.
