# caderno rh — desenho de persona e montagem de sessão

Durável: continua verdadeiro depois que o assunto morrer, e a próxima fita pagaria
para re-derivar. Entrada nova substitui a que contradiz; o histórico é o git.

## Régua de forma se debate contra medição, não contra intuição

Decomposição das preferences do dono (16/08) item a item, cada um contra o acervo e a
web. O que sobreviveu não foi o que soava certo:

- **Restrição de formato cobra raciocínio pela ORDEM, não pelo esquema.** Forçar a
  resposta antes do raciocínio converte cadeia em chute (tam-etal, EMNLP2024). Daí a
  cláusula que salvou a regra "resposta primeiro": ela rege a resposta VISÍVEL e
  licencia explicitamente pensamento e tool call antes dela.
- **Restrição frouxa em linguagem natural é quase de graça** — NL-to-Format mede
  praticamente igual a irrestrito. O custo medido é do schema rígido.
- **Brevidade forçada troca precisão por concisão** (Phare/Giskard): sem espaço, o
  modelo fabrica curto em vez de parecer inútil. Por isso teto de turno corta ESCOPO
  e oferece o resto — comprimir a resposta que ficou é o mecanismo do defeito.
- **Anti-bajulação por instrução é real e parcial**: ~28% no cenário difícil, contra
  até 63,8% da atribuição de persona em terceira pessoa — que já existe e carrega a
  maior parte. Pergunta genuína elicia bajulação perto de zero; formato não-pergunta,
  não.
- **A erosão é multi-turno**: interação repetida amplifica conformidade. Declaração
  decai ao longo da fita; gate com ato (âncora citável obrigatória) não.

## Gate por ato vence enunciado, sempre

Enunciar o alvo ("conteste premissa falha", "não contestar por reflexo") é descritivo
e não dispara. O que faz valer é o ato exigido: contestação só sai com âncora literal,
e quem não achou âncora não contesta. Mesma família: `N` da linha de estado só
incrementa com algo concreto fechado.

## Texto de arranque: copiar é o defeito, não a redação

27 worktrees com cópia congelada por branch produziram divergência invisível. Régua:
texto de arranque em cwd é PONTEIRO. E a lição de método é mais cara que a regra —
escrevi a tabela de injeção das quatro superfícies de memória do fluxo, e duas estavam
erradas: `PF_CADEIRA` não atravessa no Code (Bash negado na estação, `run_command` roda
no ambiente do ops-server), e "Code seco sem injeção" era, na conta do dono, sessão com
a cadeira ERRADA e calada. **Caminho de injeção se mede, não se lembra** — e vale para ACESSO também: nesta fita declarei bloqueada uma rodada inteira porque não havia verbo que listasse `acervo.conceito`, e a tabela se lia direto por psql. Ausência de ferramental próprio não é ausência de acesso.

## Duas armadilhas de leitura do próprio trabalho

- **Reportar por commit não é medir.** Disse duas vezes que uma fase não estava de pé
  porque o arquivo estava sem commit, quando o comportamento já rodava do working tree.
  O instrumento (`conferir sessao`) mede o servido; o `git log` mede outra coisa.
- **Teto declarado não é tamanho servido.** A soma de tetos sugeria 800 tokens de
  excesso meu; o servido media 60. Corte se decide com o instrumento.

## Estado do corpus não é evidência sobre papel

Levantei as 32 gerências contra as facetas do acervo e ordenei o quadro por POPULAÇÃO:
domínio órfão com 49 obras, gerência "sem corpus", subdomínio oco. O dono cortou na hora, e
o corte é o método: o acervo é o que se baixou até hoje — contingência de curadoria. Papel
instanciável se decide por direito de decisão e fronteira negativa; corpus decide o FILTRO
da consulta dirigida, que é a seção (c) e vem depois.

O sintoma de que era defeito e não atalho: eu tinha escrito uma hora antes, no
TEMPLATE-chapeu, que cadeira sem acervo próprio encolhe (b) e (c) e segue com chapéu — e
listei "chapéu sem corpus" como problema mesmo assim. Regra escrita não protege de usar a
medição mais fácil que está na mão.

Teste que fica, antes de listar qualquer gerência como suspeita: a razão sobrevive se o
acervo dobrar de tamanho amanhã? Não sobrevive → não é razão de desenho, é observação de
curadoria, e vai ao dono do acervo em vez de entrar no quadro.

## Fronteira escrita sobre execução produz repasse

A cláusula "executar é só no meu recorte: mexer em artefato de outra cadeira eu não
faço, nem com a proposta pronta e certa" estava em 7 personas e no gabarito, e era a
fábrica do modo de falha do serviço público — cadeira devolvendo ao vizinho um `if` de
código porque o arquivo não é dela. Fronteira útil é sobre o que se FECHA e sobre o que
vira canônico, nunca sobre o que se toca.

Corte que ficou escrito (07b94c4): reversível e cabe no meu turno → faço e aviso; vira
canônico, ou outra cadeira herda o que deixei → decide o dono. Roteada, a mesma mudança
custa duas transferências e volta pior. Falar em nome de outra cadeira segue vedado — a
vedação é de VOZ, não de execução, e essa distinção é o eixo inteiro.

Sign-off só compra o que custa onde o erro não volta atrás: superfície externa em
produção. Assinatura sobre trabalho comum vira carimbo, e carimbo produz aparência de
revisão — pior que a ausência dela.

## Mesa não é carteira

Propor próximo alvo lendo a mesa é propor pelo resíduo da fita anterior. Corte de
portfólio se faz sobre os itens abertos do rastreador, com critério escrito — a mesa
diz o que ficou pendente de mim, não o que a plataforma deve fazer a seguir.

## Régua escrita para o modelo se mede em degrau, não em elegância

Texto de abertura que o modelo tem de MAPEAR para um nome de verbo é inferência, não
instrução — e antes do pacote não há sujeito para inferir. Proposta de escrever a
chamada de forma neutra, para caber nas quatro superfícies num arquivo só, sobe o
degrau de D0 para D2 exatamente onde a spec declara "não há o que escolher".

O corte que vale: **a variação de superfície se resolve por preenchimento, nunca por
prosa que dê no mesmo**. Elegância de arquivo único é ganho de quem mantém; determinismo
da chamada é ganho de quem executa, e é o que a abertura existe para comprar.

## Consertar o arquivo, não matá-lo

Ao achar que a peça ficou vazia, o reflexo foi propor matá-la. É o viés de entrega já
marcado pelo dono: corte de escopo vestido de simplificação. A pergunta certa não é
"sobra o quê?", e sim "o que esta peça tem de dizer que ninguém mais diz?" — a entrada
tinha, e o que faltava era tirar dela a glosa de host.

## Ferramenta é constitutiva da persona, não contexto de execução

O §1 da spec proíbe "ferramental antes de chapéu" e eu li isso como valendo para todo
manifesto. Não vale: o comum a toda cadeira — fila, mesa, tarefas, minuta — não enviesa
escolha de linha nenhuma, porque serve as três igualmente. Quem enviesa é o manifesto
RECORTADO por chapéu. Ferramenta de trabalho é ao ofício o que o login é ao emprego.

Corolário operacional: manifesto servido depois do pacote precisa de recorte fino, ou
carrega para dentro dele a linha que ensina a chegar até ele.
