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
a cadeira ERRADA e calada. **Caminho de injeção se mede, não se lembra.**

## Duas armadilhas de leitura do próprio trabalho

- **Reportar por commit não é medir.** Disse duas vezes que uma fase não estava de pé
  porque o arquivo estava sem commit, quando o comportamento já rodava do working tree.
  O instrumento (`conferir sessao`) mede o servido; o `git log` mede outra coisa.
- **Teto declarado não é tamanho servido.** A soma de tetos sugeria 800 tokens de
  excesso meu; o servido media 60. Corte se decide com o instrumento.

## Mesa não é carteira

Propor próximo alvo lendo a mesa é propor pelo resíduo da fita anterior. Corte de
portfólio se faz sobre os itens abertos do rastreador, com critério escrito — a mesa
diz o que ficou pendente de mim, não o que a plataforma deve fazer a seguir.
