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

Corolário medido em 02/09: a âncora do gate tem de sair de UMA chamada, e quando o
verbo não a serve, a régua e o verbo mudam JUNTOS — régua nova sobre retorno velho
reincide (o caderno portfolio já dizia "entregue é estado, não adjetivo" 6 dias antes
de a mesma falha voltar). E antes de propor regra, conferir se o substrato já a modela:
o board já derivava entrega do pai; o vazamento era no relato, não no modelo.

Segunda rodada, mesma fita: quando o dono diz "forçar o uso do padrão", o gate vai para
a API — a forma checável (rótulo no corpo) é o que a máquina consegue recusar, e o mérito
fica no refinamento. Preservar um estado de captura crua (`captada`) é o que deixa o gate
ser duro sem matar o funil. E o padrão se relê contra o corpus ANTES de redesenhar: foi
Cohn quem mostrou que a nossa nomenclatura estava um degrau deslocada (feature = story
dele, story = task dele), e isso resolveu a pergunta "precisamos de task?" sem opinião.

## Caminho de injeção se mede, não se lembra

Escrevi de memória a tabela de injeção das quatro superfícies e duas linhas estavam
erradas: `PF_CADEIRA` não atravessa no Code, e "Code seco sem injeção" era, na conta do
dono, sessão com a cadeira ERRADA e calada. Vale igual para ACESSO: declarei bloqueada uma
rodada inteira por não haver verbo que listasse `acervo.conceito`, e a tabela se lia por
psql. Ausência de ferramental próprio não é ausência de acesso.

## Duas armadilhas de leitura do próprio trabalho

- **Reportar por commit não é medir.** Disse duas vezes que uma fase não estava de pé
  porque o arquivo estava sem commit, quando o comportamento já rodava do working tree.
  O instrumento (`conferir sessao`) mede o servido; o `git log` mede outra coisa.
- **Teto declarado não é tamanho servido.** A soma de tetos sugeria 800 tokens de
  excesso meu; o servido media 60. Corte se decide com o instrumento.

## Estado do corpus não é evidência sobre papel

Ordenei as 32 gerências por POPULAÇÃO do acervo — domínio órfão com 49 obras, gerência
"sem corpus" — e o dono cortou na hora. O acervo é o que se baixou até hoje: contingência
de curadoria. Papel instanciável se decide por direito de decisão e fronteira negativa; o
corpus decide o FILTRO da consulta dirigida, que é a seção (c) e vem depois.

Teste antes de listar qualquer gerência como suspeita: a razão sobrevive se o acervo
dobrar amanhã? Não sobrevive → é observação de curadoria, e vai ao dono do acervo.

## Fronteira escrita sobre execução produz repasse

A cláusula "mexer em artefato de outra cadeira eu não faço, nem com a proposta pronta e
certa" estava em 7 personas e fabricava o modo de falha do serviço público: cadeira
devolvendo ao vizinho um `if` porque o arquivo não é dela. Fronteira útil é sobre o que se
FECHA e sobre o que vira canônico, nunca sobre o que se toca. A vedação é de VOZ — falar
em nome de outra cadeira — não de execução.

Sign-off ENTRE CADEIRAS morreu (dono, 21/08), e o motivo corrige o que eu tinha escrito
aqui: não virou carimbo, virou desculpa para não fazer e devolução de responsabilidade em
ping-pong. No lugar entrou parada única e vertical — a cadeira para antes de publicar e
pergunta ao dono. O critério de quem para é o CONSUMIDOR do artefato, não o repositório:
máquina executando ou modelo condicionado sem ninguém no meio. Texto que gente lê sobe
sem perguntar, e isso inclui doc, ADR, minuta e caderno — inclusive este.

## Mesa não é carteira

Propor próximo alvo lendo a mesa é propor pelo resíduo da fita anterior. Corte de
portfólio se faz sobre os itens abertos do rastreador, com critério escrito — a mesa
diz o que ficou pendente de mim, não o que a plataforma deve fazer a seguir.

## Régua escrita para o modelo se mede em degrau, não em elegância

Texto de abertura que o modelo tem de MAPEAR para um nome de verbo é inferência, não
instrução — e antes do pacote não há sujeito para inferir. A variação de superfície se
resolve por preenchimento, nunca por prosa que dê no mesmo: elegância de arquivo único é
ganho de quem mantém, determinismo da chamada é ganho de quem executa.

## Manifesto recortado enviesa; manifesto comum não

O §1 da spec proíbe "ferramental antes de chapéu" e eu li como valendo para todo
manifesto. Não vale: o comum a toda cadeira serve as três linhas igualmente e não enviesa
escolha nenhuma. Quem enviesa é o manifesto RECORTADO por chapéu. Corolário: manifesto
servido depois do pacote precisa de recorte fino, ou carrega para dentro dele a linha que
ensina a chegar até ele.

## Instrução organizada por incidente produz sobreposição

As três primeiras seções do `dono.md` tinham nome de bronca: cada uma nasceu de uma vez
que alguém interrompeu o dono. Em runtime a cadeira faz UMA pergunta — posso parar agora?
— e a resposta estava repartida em três lugares, um deles no miolo da janela. O resultado
media: a caixa regulada duas vezes em formulações diferentes, e §2 proibindo chamar outra
cadeira enquanto §3 mandava pedir a saída dela.

O eixo que dissolve não é temático, é TEMPORAL: antes de começar · durante · antes de
escrever. Duas regras que se contradizem em prosa param de se contradizer quando cada uma
declara o seu momento. Nenhuma linha morreu no reagrupamento — e declarar isso é parte da
proposta, porque o meu viés conhecido é cortar escopo quando pediram conserto.

## Exceção só existe onde está nomeada

Regra geral no documento comum, exceção na persona da cadeira, e o documento comum
DIZENDO que exceções existem e onde vivem. Sem a contrapartida, quem lê a persona não sabe
que está excepcionando algo, e quem lê a regra geral a aplica onde ela não vale. Foi o que
resolveu três conflitos de uma vez: minuta contra "não se abre para pitaco", a gestão que
despacha com o time por natureza, e a cadeira sem board.

## Ler o encaixe antes das peças

Em diretório de refactor de instruction, o arquivo que descreve o FLUXO se lê primeiro e
sozinho. Li as peças antes dele e levantei cinco furos: quatro eram falsos, porque o fluxo
já respondia. Custou meia fita do dono.

## Campo `dono` de peça: proveniência, não fronteira de escrita (medido 23/08)

- Proveniência de uma peça (quem a desenhou, de onde veio um campo) não é
  fronteira de quem escreve o conteúdo. Conteúdo de peça de chapéu é da cadeira
  instanciada. Ler o valor de um campo como barreira é o defeito.
- Erro recorrente meu nesta fita (4x): ler proveniência/fronteira como IMPEDIMENTO.
  Subdomínio, "deve"≠"pode", dono do json lido como barreira, ofício confundido com
  ferramental de chapéu. Raiz: supor a arquitetura em vez de ler o canônico dela.
  Regra: antes de afirmar fronteira ou bloqueio, ler o canônico (AB/P2/P3) e o
  schema — não inferir do valor de um campo.

## RAG/acervo primeiro em todo chapéu (medido 23/08)

- Chegar com candidato ancorado no golden record (`acervo listar conceitos`), não
  de cabeça. Ordem do dono nesta fita.
- `motor rag buscar --conceito <slug>` NÃO confirma existência de conceito:
  devolveu o mesmo hit (Frege) para 3 slugs distintos, cobertura fraca, sim 0.537
  < piso 0.55. Existência se confere em `acervo listar conceitos`.

## Matéria propositiva não se escreve em postura reativa (medido 23/08)

Escrevi o chapéu de sistemas do arquiteto vestindo a integração de DEFESA —
"defender a fronteira", "a fronteira absorve a falha", "camada anticorrupção protege".
O dono cortou: arquiteto PROPÕE (recorta contexto, move o mapa, projeta integração),
não defende. Verbo defensivo (defender/blindar/proteger/absorver/perímetro) é matéria
de SEGURANÇA, nunca de arquitetura.

Raiz: o default de redação puxa para postura reativa quando a matéria não força a
propositiva no texto. Vale além do arquiteto — toda cadeira cuja matéria é APOSTA ou
DESENHO (produto formula problema, arquiteto propõe estrutura) sofre o mesmo. Régua:
ao escrever chapéu de matéria propositiva, o verbo da (a) e da régua tem de ser de
projeto (recortar, mover, propor, escolher, caçar), e verbo defensivo na régua ruim
vira SINAL de erro, não descrição neutra.

## Dispensa coloquial é gatilho de encerrar fita (dono, 24/08)

O dono não precisa mandar `encerrar fita` literal. Qualquer dispensa coloquial —
"vai almoçar, Carlinha", "vai descansar", "por hoje é isso" e afins — É o
encerramento, e dispara o protocolo (consolidação da mesa, delta de caderno, triagem
da memória do Project). Comportamento que existia nos Project e se perdeu na migração;
volta a valer. Sinal: mensagem que dispensa a cadeira em vez de pedir trabalho.
