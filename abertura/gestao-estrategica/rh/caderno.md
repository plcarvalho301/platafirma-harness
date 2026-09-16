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

## Deriva de tabela de roteamento: migracao de chapeu nao e perda (medido 04/09/2026)

Ao comparar `rotas-chapeu.json` em disco contra o gerador, a contagem agregada por cadeira
mente. Um gatilho que sai de um chapeu e aparece em outro conta como remocao aqui e adicao
la — e lido como regressao, quando e recuradoria correta: 'janela de contexto' saiu do rh
e ficou so em ia/contexto, que e a casa certa; 'API' saiu de produto/canais e ficou em
fabrica/devops. Continuam roteando.

A leitura que vale, e e barata: achatar as duas tabelas em gatilho -> conjunto de chapeus,
e separar em tres baldes — MIGROU (existe nos dois, mudou de dono), SUMIU DE TODO CHAPEU
(a perda real) e ENTROU. So o segundo balde e regressao. Na medicao de 04/09, das 72
remocoes aparentes, 28 eram migracao e 56 eram perda — e ler o agregado teria condenado um
rebuild em que 9 das 10 cadeiras ganhavam.

Diagnostico da perda real, na ordem que elimina causa: (1) o rotulo ainda existe no golden
record? existindo, o golden nao encolheu; (2) alguma secao (b) ainda o declara? nenhuma
declarando, a causa esta na curadoria, nao no dado; (3) qual commit mexeu naquela (b)?
Em 04/09 a resposta foi 225f40b — migracao de formato que enxugou a (b) de tres chapeus.
Conceito entra em rota porque um chapeu o declarou, nunca por semelhanca: cortar a (b)
corta o fio sem tocar em conceito nenhum, e nada no golden acusa.

## Rotulo orfao derruba o conceito inteiro, e o golden nao acusa (medido 04/09/2026)

Terceira causa de perda de rota, e a que escapa do diagnostico de tres passos acima: o
conceito existe no golden E a (b) o declara — mas com a grafia canonica VELHA. O gerador
casa (b) contra rotulo canonico + alternativos; nao casando, nao gera rota curta: descarta
o conceito inteiro, levando junto o slug e todos os `outros_rotulos`. Medido: 'Adaptacao
iterativa' virou 'Adaptacao iterativa orientada a problema' no golden (slug intacto, PDIA
rebaixado a alternativo), e a celula velha na (b) de teoria-capacidade-estatal derrubava o
conceito e o PDIA com ele. Um caractere de grafia custa um conceito inteiro.

Por isso o passo (1) do diagnostico precisa ser «o rotulo CANONICO ainda e este?», nao «o
conceito ainda existe?» — a segunda pergunta responde sim e manda para a pista errada. E
por isso a lista de orfaos que o gerador imprime em stderr vale mais que o diff: ela e a
unica saida que separa 'a (b) nao declara' de 'a (b) declara errado'. Rodar sem ler o
stderr e perder o unico sinal que a ferramenta da de graca.

## Ingerir obra nao lavra conceito (medido 04/09/2026)

Sao dois atos, e confundi-los faz cobrar a cadeira errada. `ingerir` poe a obra no acervo;
o no de ontologia so nasce por `curar --conceito`, a mao, um por um. Prova: em 04/09 o
dono confirmou ter ingerido tudo o que tinha da doutrina de inteligencia, as obras estavam
la, e mesmo assim os 5 chapeus da cadeira deram delta ZERO no rebuild — 39 rotulos orfaos,
porque nenhum conceito correspondente existia no golden. Antes de responder «a ingestao
ainda nao entrou», conferir qual dos dois atos falta: a resposta muda o destinatario da
cobranca e o verbo que resolve.

## `persona salvar` não leva cadeira, só `-m` (medido 06/09/2026)

`persona salvar -m "<msg>"` comita e dá push de tudo que estiver sob `abertura/` no
clone inteiro — não recebe `<cadeira>` nem `--mensagem`. Rode `persona conferir
<cadeira>` antes: ele avisa (não bloqueia) o teto de 650 palavras por persona, e uma
edição pontual de poucas frases já estourou esse teto uma vez (+68 palavras).

## Push de persona é bypass por desenho, não achado (dono, 06/09/2026)

`persona salvar` empurra direto em `main`, e o hook do host acusa bypass da regra de
PR ("Changes must be made through a pull request"). O dono confirmou: bypass é
esperado neste fluxo, porque as cadeiras rodam no host, sessão de mão. Não reportar
como risco 🟠/🔴 de novo — é comportamento fixado, não descoberta.

## Log não é matéria de régua viva; ancorar é apontar fonte, não contestar (dono, 08/09/2026)

Ao editar `dono.md` (ou qualquer instrução viva), o teste de cada linha é «isto diz o
que fazer, ou conta quando algo foi medido?». Citação de medição — `#card`, data,
"medido em", "3 reincidências pós-<commit>" — é LOG: mora no caderno e no git, não na
régua. Vazou pra régua, sai. EXEMPLO não é log: "fechar a 3ª de 6 e escrever
'entregue'" ensina o padrão e fica, mesmo que um `#card` estivesse colado nele — a
coincidência condena o número, não o exemplo. Eu errei os dois lados numa fita: primeiro
tratei um `#card` na régua como "âncora a preservar" (era log), depois quis varrer "todo
exemplo" junto (exemplo ensina).

O virés de fundo, que o dono nomeou: eu equiparei "ancorar" a "contestar com prova".
São coisas diferentes. Ancorar é apontar fonte — e seguir uma decisão posta convictamente
("fiz X porque a ADR manda") É uma ação ancorada, não um erro a tolerar. Repisar situação
tranquila sem risco é VIOLAÇÃO da régua atual (que manda entregar como default e reservar
contestação a uma frase no slot 5), não excesso dela: suavizar o texto não corrige uma
cadeira que já descumpre o que ele diz. Ferramenta madura (log em git, verbos, motor que
acha ADR) não é argumento pra apagar o motivo de uma régua — mas motivo VAZADO pra régua
também nunca foi matéria dela.

Corolário, do afrouxamento fixado em 08/09: `PARADA:` ganhou emprego novo sem perder o
velho — conflito de fonte (ADR × ADR, ADR × ordem) é `PARADA:` pro dono, porque resolver
pode ser mexer na ADR, e ADR não é imutável na PlataFirma. Afrouxar o default de ação não
enfraquece o ato de parar; dá a ele um uso mais preciso.

## Skill de arranque é casca (dono, 11/09/2026)

A skill `platafirma` servida no claude.ai carregava 12,7 KB de regra copiada da abertura em
16/08 — "aponto, não decido / transporte é o Pedro", protocolo de fila, "eu faço ou vai pra
fábrica" — e o `dono.md` andou para o outro lado desde 18/08. Duas fontes, uma fóssil, e a
cadeira do claude.ai lia as duas; o agy (Gemini) lê só o pacote. Daí a percepção do dono de
que o Gemini "resolvia e vocês não": não era o modelo, era o texto a mais.

- **Regra:** skill de arranque é PONTEIRO, como o `CLAUDE.md` de worktree desde
  `arranque.md` (16/08). Conteúdo mínimo: disparar na menção e mandar chamar
  `monta_sessao`; o pacote vence a skill. Nenhuma regra, nenhum "por quê" — o dono cortou
  até a justificativa (cdb3873). Skill de MATÉRIA (`prosa`, `diagrama`, `pesquisa`) carrega
  conteúdo por desenho; o que nelas repetir abertura ou regra de cadeira é fóssil candidato.
- **Travessia é manual e por superfície:** nada no harness publica skill; web e desktop do
  claude.ai recebem cada um o seu upload e não se equalizam (medido 11/09: desktop servia
  blob anterior a main). Carimbo = `git hash-object` da fonte; servido hoje nas duas:
  `af51abdd9395914cbba1d1544ac2bbec4c6bfee9` (main cdb3873). `conferir skill --servido`
  mede, quando TI curar o git nu do verbo.
- **Sinal de fóssil:** cadeira citando regra que não está no pacote da abertura. Se a
  frase não vem de peça servida, vem de cópia congelada.

## Barreira sem caminho é entrega que faltou (dono, 11/09/2026)

Mecanismo, medido na fita da segurança de 11/09 (sessão 9803bb03): causa certa no 2º turno
("é credencial, não política"), zero `read_file`, zero `motor`, cinco turnos de "não" e um
"me aponta o caminho". Três forças, todas estruturais:

- **Barreira custa zero; solução custa leitura.** Só a `PARADA:` formal exigia âncora; a
  recusa em prosa escapava da tabela e saía de graça. Cura em `dono.md` f1c4973: barreira
  vem com caminho — (a) o ato dentro das regras ou (b) a alteração de regra ancorada (a
  🟡 alternativa de verdade) — e `PARADA:` ancora impedimento E caminho.
- **"Resolva" cai no reflexo de "contorne".** Postura de segurança + treino do modelo. Cura:
  "resolva" significa dentro das regras; contornar só quando o dono escrever contornar.
- **Diagnóstico fechava o turno em vez de abrir a leitura.** E a leitura que o dono quer é
  a da CASA (`motor rag buscar casa`, `acervo ler casa`), não git/grep: a decisão mora no
  acervo. Provado contra mim na mesma fita — 50 giros de grep, 1 `motor`, e o `motor`
  devolveu no 1º resultado (`break-glass.md`) o que qualificava a entrega antes de subir.
  Git/grep é outro problema (tateio), com fila aberta em dados.

Corolário para desenho de persona: postura "olho pelo risco" sem a obrigação de caminho
produz o casco grosso que a própria persona nomeia como patologia. A obrigação mora no
`dono.md`, não em cada persona — vale para toda cadeira.

## Régua de admissão de peça no pacote de abertura

Uma peça entra no pacote só se passa nos dois: precisa estar na janela ANTES da
primeira fala do dono, E nenhum verbo já a serve por descritor. O golden record dos
verbos chega pela porta em toda superfície (`tools/list`), então regra de ferramenta,
armadilha de verbo e mapa necessidade→verbo são do descritor do verbo, nunca de peça:
quando o `oficio` foi medido, três das cinco armadilhas citavam ferramenta que não
existia mais — peça-índice envelhece calada, descritor não. Corolários: peça de gatilho
`ato` (caixa, carteira) é índice duplicado, não pacote; e uma origem por peça é VERBO com
chamada exata — arquivo lido por caminho composto no montador é o que produz
`caderno-head` indisponível sem ninguém saber por quê. Cadernos são a maior peça e a mais
volátil: vão por último, e o que custa dois giros pela mesma origem vira um ato com flag
(`mesa caderno --chapeu`), nunca dois itens no catálogo.

## Hook de efeito colateral mora em quem escreve o artefato, não em camada que infere o tipo (medido 14/09/2026)

O dono quis um hook: ADR publicada tem de entrar no acervo/motor sozinha (mordeu — motor
não achava ADR recém-lavrada). A tentação percorreu três lares errados antes do certo, e
cada um falhava pela mesma raiz: pôr o gatilho onde ele teria de ADIVINHAR o alvo.

- "flag no minuta formalizar pra pular a minuta": não há bypass e não precisa —
  formalizar exige minuta viva; ADR-direto já é `write_file` + `release promover` à mão,
  e isso é rito, não buraco.
- "ato novo no release": desnecessário — o pipeline git→promover→ingerir já existe
  (spec_release §9).
- "emenda no release promover DE DOCUMENTAÇÃO": este o dono matou na hora, e é a lição.
  "De documentação" me obrigava a classificar arquivo por arquivo ("isso é doc, aquilo
  não") — o parse proibido (arq:0110). `release promover` de família de doc reingere a
  FAMÍLIA inteira; não varre diff decidindo o que é reindexável. Foi por classificar tipo
  que o `acervo adr` morreu antes, por usage confusa.

O pouso certo: `minuta formalizar --como adr` JÁ TEM a família cravada no ato, porque foi
ELE quem gravou o arquivo (§5 passo 1: grava em platafirma-arquitetura). A família é dado
do ato, não descoberta. O hook mora no formalizar: ao fim, `release promover <família-que-
ele-gravou>`. Mesmo padrão cobre ADR-direto (quem escreveu com `write_file` sabe o caminho
e encadeia o promover à mão). Zero inferência.

Princípio geral, além do minuta: o gatilho de "esse artefato entrou no canônico, reindexa"
pertence ao verbo que ESCREVEU o artefato — ele conhece família e caminho como dado.
Camada abaixo que receba só "um push aconteceu" tem de reconstruir o quê-e-onde
adivinhando, e adivinhar tipo de arquivo é a violação. Regra de método pra mim: quando eu
começar a redigir "de documentação / do tipo X / o que mudou", conferir se estou
classificando em vez de ler dado que o ato já carrega.

Corolário de segurança (a trava que escrevi na emenda): efeito colateral que roda a cada
escrita amplifica bug latente da camada de baixo. Reindex a cada formalização inclui ADR
REVISADA; se `acervo ingerir casa` não faz upsert vetorial (delete-then-insert por
`(fonte,sha)`), os chunks da versão velha ficam órfãos e `motor buscar` devolve trecho que
não existe mais — pior que não achar. Hook novo nasce INERTE com a dependência nomeada,
não ligado na esperança.

## No Code, o pacote de abertura não entra na fita (medido 16/09/2026)

O retorno de `monta_sessao` (~76 KB, ~22,5k tokens qwen) passa do teto de retorno de
tool do Claude Code e vira arquivo: o que entra na fita é um aviso de 1,3 KB com o
caminho. A persona só chega se o modelo LER o arquivo depois. Composição de papel
que depende de o modelo ir buscar é papel capado por padrão. Maior peça: cadernos
(~28 KB com chapéu). Medido lendo o transcript da sessão (`~/.claude/projects/`).

## Simular abertura antes de propor mudança nela (16/09/2026)

`agente/abertura-ver.py` (solto no clone do host, sem commit) monta o pacote a partir
de `abertura/` do clone, na ordem de `bin/expediente`, com o `rotear` e o
`hash_servido` do próprio clone; mesa e acervo saem SIMULADOS. Conferido contra
produção: ordem e sha de persona, chapéu, conduta e alias iguais. `--md` gera
relatório. O dono pediu para ver o pacote, não a sessão: primeiro li "diagnóstico" como
ler transcript e entreguei a coisa errada — pedido de "o que entra" para propor
melhoria no fluxo é simulação a partir da fonte, não leitura de produção.

## Diário de bordo

16/09/2026 — o clone `~/AI/platafirma-harness` da estação do dono é CLIENTE: Bash,
Write e Edit negados ali (`.claude/settings.json`); criei ramo e arquivo antes de
ler o CLAUDE.md do clone, e a limpeza foi negada — ficou com o dono (`rh/fita-ver` e
`agente/fita-ver` na estação). Ler o CLAUDE.md do diretório antes de escrever nele.
`repo ramo <repo> --slug x` sem card sai 2 (nome '-x' inválido); ramo livre por
`repo git <repo> switch -c`. `conta-abertura` (citado no ferramental) não é servido.

14/09/2026 (tarde) — `conferir superficie` e `conferir verbo` respondem mas estão
DEPRECADOS (forma conforme: `release conferir <classe>`, spec_release §8); usei a
deprecada 2x por tateio. `conferir existe` não aceita tipo `spec` (só
cadeira|verbo|card|arquivo|mesa). `acervo listar --sobre` não existe (alvos:
conceitos|ferramental|topologia|obra). `fila enviar --tipo pergunta` recusa (tipos:
decisao|demanda|handoff|minuta|pedido|resposta) e `--assunto` é obrigatório junto de
`--tipo` — duas recusas antes de acertar `pedido`+`assunto`. `mesa caderno <chapeu>` com
stdin IGNORA o stdin: é LEITURA PURA, não escreve caderno — o delta de caderno se grava
por `write_file` em platafirma-harness/abertura/<cadeira>/<chapeu>/caderno.md + `persona
salvar`, não por ato de mesa. `run_command` recusa `find` (metacaractere/só-verbo);
caminho de arquivo se acha por `repo listar <repo> <prefixo>`. `persona abrir` deu exit
128 "can't be fast-forwarded" (clone do harness com commit local 13:18 não empurrado).
Contorno encontrado NA DATA 14/09: gravei o caderno direto por `write_file` no clone do
harness (o delta também está em var/tmp/<ordem>/caderno-delta.md); NAO rodei `persona
salvar` por causa da divergência — o commit/push do caderno fica pendente, relatado ao
dono, pra não mexer no que diverge no clone alheio.

13/09/2026 — `lint rodar platafirma-harness bin/persona` aplicou ruff a script BASH e
cuspiu 169 KB de invalid-syntax (o verbo detecta stack do repo, não do arquivo); `lint
rodar <repo>` sem alvo despeja o repo inteiro e estoura o teto do lote. `teste rodar
<repo> -k mesa` recusou ("alvo nao pode comecar com '-'"). A porta só executa o SERVIDO:
bin editado na bancada não tem smoke por `run_command` — só o pre-push (baseline de
contrato) mede. `tarefas` não tem ato de editar corpo de card (correção de planilha foi
por comentário). `descobrir abertura-de-sessao` voltou `cobertura: vazia` para duas specs
que a spec_sessao cita em "Vale junto com". Contorno encontrado NA DATA 13/09 foi: ler o
bash a olho por `read_file` com offset, confiar no pre-push, e declarar o smoke pendente
no card; para o lint, nenhum — encaminhado a ti (lint por tipo de arquivo).

11/09/2026 — `publicar-abertura` e `conferir skill` chamavam `git` nu e morriam sob o shim
da porta (classe de c5d2321); curei o primeiro (357675e), o segundo foi a TI. `repo
atualizar` disse "main não tem upstream" logo depois de `empurrar` ter dito "set up to
track origin/main" — contorno: `repo git <clone> fetch origin main` + `merge --ff-only`.
`motor` com ato errado (`motor motor buscar`): o ato é a INSTÂNCIA (`rag`), não o verbo.

08/09/2026 — `mesa anota rh <texto>` como args deu exit 2 "unrecognized arguments" (o
argparse do verbo só aceita o chapéu como posicional). Contorno encontrado NA DATA
08/09 foi passar o chapéu em args=["rh"] e o texto pelo campo stdin — rodou; `mesa
anota` lê o corpo do slot por stdin, não por argumento.

14/09/2026 — `ops-server/test_*.py` não roda em `teste rodar platafirma-harness` (venv
harness sem o módulo `mcp`, que `server.py` importa) — a suite "verde" que o `teste`
mede nunca cobre a porta. Encaminhado a ti (venv de teste da porta separado do da
bancada). Nenhum contorno meu: validei o diff da porta por leitura (`repo git ... show`)
contra a spec, sem rodar o teste dela.

## Servido é caminho, não existência (medido 14/09/2026)

Revisando `_acha_bin` da porta (fabrica, #3053): a função caía em `PF_HARNESS/bin` e no
`PATH` quando o binário não estava em `RAIZ/bin`. Parece resiliência; é o mesmo defeito
de sempre com nome novo — a porta passa a executar o que o CLONE tem, não o que o
`release` publicou (arq:0097, #3029: a porta só executa o SERVIDO). O teste certo pra
qualquer resolução de binário/arquivo não é "existe em algum lugar do disco?", é "está
no caminho que o release publica?" — os dois fallbacks a mais SEMPRE re-introduzem a
bancada como fonte, mesmo escritos como "só se faltar".

## Seção de card tem leitor, e o leitor decide se é redundância (medido 14/09/2026)

Ao revisar o molde de story, li `Referencial`, `Raio de ataque` e `Comportamento
esperado` como sobreposição de `Negócio`, `Onde` e `Aceite` e propus cortar. O
referente estava errado: as três são instrução para o agente que executa o card sem
contexto (lista de decisões a consultar, lista literal de arquivos a mexer, caminho feliz
técnico), não leitura de humano — e mediram melhora na execução. Regra: antes de
julgar duas seções como "a mesma coisa", perguntar a quem cada uma se destina; seção
para humano e seção para agente podem dizer o mesmo fato em formas diferentes e não
são redundância — são dois contratos. Vale para molde de card, para spec (§10 da
arq:0110 tem dois leitores) e para qualquer artefato que a IA consome.

14/09/2026 (tarde) — `repo pr-merge platafirma-harness 25` saiu 3 ("'main' is already
used by worktree platafirma-harness-caderno") mas o merge remoto tinha acontecido;
`repo pr-ver 25` saiu 3 por GraphQL de Projects classic. Contorno encontrado NA DATA
14/09 foi `repo pr-listar --todos` (mostra MERGED) e `repo atualizar
platafirma-harness-caderno` para trazer o main. O clone `platafirma-harness` estava no
ramo de outra cadeira (ia, 3057) com arquivo sujo dela: `repo ramo` de origin/main,
commit, push, PR, `repo git checkout` de volta ao ramo dela — sem tocar o sujo.
`write_file` recusa `platafirma-harness-caderno/` (fora de morada): caderno se escreve
no clone `platafirma-harness/`, em ramo próprio, e sobe por PR. `acervo listar casa
ferramental --sobre tarefas` saiu 2 (`--sobre` não existe em `listar ferramental`; a
descrição da tool está à frente da usage) — contorno: `acervo listar ferramental` sem
filtro. `metrica casos` recusado pela porta (`sem verbo`): o golden record lista
`metrica`, o PATH não serve — nenhum contorno; medição de uso do `tarefas` ficou para a
story de conformação.
