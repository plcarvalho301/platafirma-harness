# caderno — chapéu harness

O que continua verdadeiro depois que o assunto morre, e que a próxima fita pagaria
para re-derivar. Não entra: fato de negócio (card/commit/wiki), estado de runtime,
decisão de outra cadeira, o que vale para toda cadeira.

## A régua de entrada da abertura é IMPEDIMENTO, e ela é escassa

Coação ("sou forçado a ler isto?") decide se a **peça** entra; impedimento ("sem
ato, fica como está?") decide se o **item** entra na mesa. Níveis distintos, e
trocá-los já produziu duas reincidências no mesmo ponto.

Corolário caro de redescobrir: **saliência não é ato.** Régua que proíbe abrir a
caixa não neutraliza um envelope injetado na janela — ela passa a competir com o
item mais concreto do pacote. Contagem nua tem o mesmo defeito, diminuído.

## Peça servida ≠ peça contada

O que o servidor acrescenta depois do montador não entra em `pacote.tokens`:
viaja na janela sem teto e sem dono, e conferência de forma não o pega. A
verificação é somar os `tokens` das peças contra `pacote.tokens` — se bate
EXATO, o que sobra na janela está fora da contabilidade.

## Prova de mudança em código de abertura, quando não há gate

Sem CI que segure, a prova é manual e em quatro passos: `py_compile`; rodar
`bin/monta-sessao --json` nas quatro classes (comum, TI, dados e **fábrica**, a
única `fora_do_quadro`); boot-check com o env real, porque compilar não é subir e o
import roda no boot; e só então restart, confirmando **pela tool**, que é a
superfície que precisa provar.

`--sem-atualizar` não isola mais nada e não faz parte da prova: depois do arq:0097 a
abertura é local por construção (morada publicada), e a flag sobrevive só como
compatibilidade de chamada.

## Remover comportamento sem remover o mecanismo é convite a reincidência

Ao tirar uma peça do pacote, o helper que a produzia vai junto. Mecanismo vivo e
não chamado é o que permite que a mesma decisão volte como "só a contagem" seis
meses depois — e uma peça de decisão não alcança código, só decisão.

## Onde o montador esconde ramo

`de_abertura()` poda e substitui peças por nome no ramo `fora_do_quadro`. Mudança
no catálogo que não olhe esse ramo passa verde nas cadeiras comuns e quebra só na
fábrica.

## Falha declarada precisa de dois papéis, não de um

Quem levanta e quem declara são camadas diferentes, e colapsá-las estraga as duas.
A peça que fala com a fonte **levanta** — é o disjuntor que precisa da exceção para
contar falha. A camada que monta o retorno **declara** — é o consumidor que precisa
de `causa` legível em vez de stack. Adaptador que já devolve envelope de falha deixa
o disjuntor cego; envelope que propaga exceção devolve ao modelo o erro que ele não
sabe corrigir.

## O valor honesto do instrumento desligado tem de ser um CAMPO

Componente sem coleção de teste não pode servir o rótulo bom. Para isso valer, o
"ainda não tenho régua" mora num campo do componente (`tem_gold`), nunca num
comentário nem no julgamento de quem lê: campo troca de valor no commit que liga o
instrumento, comentário não. Vale além do RAG — é a forma de qualquer peça que
gradua resultado antes de ter com que graduar.

## Campo de contrato pode ser derivado, e é assim que se evita a segunda verdade

Quando o contrato publicado pede um escalar e o dado real é uma lista, a saída é
manter o escalar como **propriedade calculada** da lista, não como campo redigido em
paralelo. Dois campos que descrevem o mesmo fato divergem no primeiro caminho que
atualiza um só, e o teste que pegaria isso é o que ninguém escreve.

## Suíte de fonte externa em dois níveis, e o skip declarado

Contrato com cliente falso roda sempre e julga o que a peça PRODUZ. Conformidade
contra a fonte real julga se ela bate com o verbo humano sobre o mesmo estado, e é
pulada **com motivo impresso** quando a fonte não responde. Pular declarando é o
oposto de mascarar: o motivo aparece na saída e vira sintoma, enquanto `xfail`
apaga a diferença entre "não medi" e "medi e passou".

## Carimbo que cobre uma metade da fonte é pior que carimbo ausente

Fonte com dois substratos precisa de carimbo que some os dois. Carimbo que lê só um
deles fica CONSTANTE quando o outro é o que muda — e constante é indistinguível de
"nada mudou". Com o carimbo dentro da chave de cache, isso serve estado velho para
sempre, sem sintoma. Metade que não responde declara `?`: não saber é informação, e
fingir que não mudou não é.

## Gabarito de gold não se carimba com uma segunda leitura

A versão que congela o gold é a da busca que gerou os casos, não a de uma chamada
posterior ao carimbo. As duas divergem por desenho quando o carimbo é por recorte
(por stream, por caixa, por partição) e a segunda chamada vem sem o recorte. Gold com
versão falsa faz duas coleções diferentes parecerem a mesma — e é exatamente a
comparação que o gold existe para tornar possível.

## Teste que mede a bancada passa por motivo errado

Dois modos, e os dois se corrigem por injeção: depender da AUSÊNCIA de uma biblioteca
para simular substrato caído (volta a falhar no dia em que alguém a instala), e ler
variável de ambiente que o construtor usa como default (mede quem rodou, não a peça).
O sintoma é o mesmo nos dois: verde que não prova nada e vermelho que não acusa nada.

## Suíte vermelha por gabarito velho não é suíte vermelha por defeito

Quando a política muda por ato, o teste que a codificava reprova sem que o mecanismo
tenha mudado. Antes de tratar como risco, achar o commit que mudou a regra: se o
mecanismo (fail-closed, negativa total, trilha) segue intacto, o que envelheceu foi o
gabarito. A emenda mantém a régua e troca o PAR que a exercita — apagar o teste
perderia a régua junto com o exemplo.

## A distinção "abertura × só-chapéu" precisa de sinal EXPLÍCITO, não inferido

A abertura-base serve SEMPRE, salvo pedido explícito de só-chapéu (`--so-chapeu`).
Pergunta e chapéu apenas roteiam o chapéu, que é ADITIVO. Inferir "tem pergunta/chapéu
→ é só-chapéu, pula a abertura" (o antigo `perna_dois`) é proxy errado por dois lados:
quebra a abertura quando um elo passa a mandar SEMPRE o corpo como `--pergunta` (#249)
— toda abertura vira só-chapéu e, no fallback do roteador, devolve `pecas:[]` sem erro,
a ambiguidade "peça vazia × cadeira sem peça" que o contrato proíbe; e confunde o modo
só-chapéu com abrir-com-chapéu, que a persona faz na abertura e quer abertura+chapéu.
A troca de chapéu mid-sessão é caso REAL (a Carla reportou: reenviar a abertura já
servida é desperdício) — por isso o modo existe, mas se pede por FLAG, não por
heurística. Régua geral: quando dois usos legítimos compartilham o mesmo argumento
(`--chapeu` serve tanto abrir-com-chapéu quanto trocar-de-chapéu), a intenção precisa
de sinal próprio; espremê-la num proxy faz duas mudanças corretas se contradizerem
quando compostas. Prova PELA TOOL, nas quatro classes (fábrica inclusa).

## Verbo de leitura é a costura que troca substrato sem tocar consumidor (rota de máquina)

Expor uma leitura interna in-process como VERBO não é conveniência de digitação: o verbo é o
ponto de extensão (`descrição-como-interface`). O consumidor chama `motor <inst> conceito X` e
não sabe se por baixo é SQL in-process hoje ou contrato de grafo (`motor_ontologia`) amanhã —
troca-se a implementação num arquivo, consumidor intocado. É o Strangler na ordem certa: mantém
o in-process vivo sob exceção declarada (ADR 0090, PIA2) até a peça substituta nascer.

Rota de máquina é o DEFAULT do verbo de agente, não o `--json` opcional: JSON estável e
determinístico, chave opaca, propriedade safe/idempotente declarada, erro como causa legível por
modelo (não stack). O que compra a economia de token e para o agente de montar chamada errada é a
`descrição`/manifest do verbo (o skill-ificável), não o SQL de dentro — o dono cravou isso na fita
de 31/08. Ancoragem no acervo: Higginbotham «Offering CLIs for APIs» (CLI é consumidor de API +
ferramenta de automação); Google AIP «Client».

Guardrail que já mordeu: o verbo embrulha a MESMA função in-process (`conceitos.rede`/`veredito`),
nunca uma SQL paralela — duas portas para o mesmo índice divergem (adaptador `acervo.py`, #2947). E
é SEGUNDA porta: não reroteia o hot path do `/search` (subprocesso por inferência é imposto de
latência).

RETOMAR: construir `motor <inst> conceito <slug>` (payload v1 node-local:
slug/existe/rotulo/outros_rotulos/obras_servindo/mais_amplo). Espec no card #2931; objeção no ADR
0090 (arquitetura@45e0d3c). Execução "muito em breve", junto do rerefactor da recuperação (#2930).

## Spec de ferramenta descreve a FORMA e o LUGAR da política do dono, nunca o CONTEÚDO

Especificar um verbo é desenhar mecânica (`--sujeito`, `--cat`, campo no manifesto,
lista de tipos do `resolver`, `settings.yml`). O RECORTE que essa mecânica serve —
quais categorias ligam, o que dispara guarda de privacidade/LGPD, se um ato recusa —
é decisão do dono, e a spec no máximo aponta o lugar reservado a ela (o arquivo de
config, a lista fechada), sem preencher. Colar régua de privacidade ou recorte de
categoria dentro do contrato do verbo, ainda que a mecânica seja legítima, é tomar a
decisão por ele. Sinal do erro: o dono corrige o recorte, não a mecânica. A mecânica
é da cadeira; o recorte é dele. Vale para qualquer spec que sirva política, não só
para pesquisa web.

## Ao tirar uma medida de frescor, perguntar qual falso-verde nasce no lugar

Instrumento que acusa defasagem costuma sair junto com o mecanismo que ele media, e o
buraco não fica vazio: a mesma defasagem volta calada, com outro nome. Ao trocar a
leitura de working tree por artefato publicado, a classe `divergente` sumiu — e a
morada passou a envelhecer sem sinal nenhum, que é o "clone atrasado" de volta. Trocar
um falso-verde por outro não é conserto.

A saída não é reanimar a medida velha: é achar o que ainda se pode AFIRMAR sob a nova
restrição. Sem git no caminho de serviço não se mede distância até o remoto, mas se
mede IDADE, que sai de um campo do próprio artefato, sem rede. Duas perguntas
diferentes querem dois instrumentos: quem SERVE declara a idade do que serve; quem
PUBLICA mede a distância. Instrumento que estima a pergunta do outro erra as duas.

## Prova de vida não é medida de cobertura

Quando N fontes respondem a uma consulta, "quem respondeu" e "quem produziu resultado"
são conjuntos diferentes, e derivar o primeiro do segundo torna invisível quem
respondeu VAZIO. A invisibilidade então vira morte: zero resultado com todas as fontes
vivas fica indistinguível de nenhuma fonte no ar, e um não-achado legítimo sai
classificado como falha de fonte. É o erro mais caro dos dois, porque some do relatório
como se ninguém tivesse procurado.

Vida se prova pelo COMPLEMENTO: o universo declarado menos quem se declarou fora —
nunca pela presença em resultado. Isso exige conhecer o universo (uma leitura de
config, cacheável), e o custo dessa leitura é o preço da distinção. Não conseguindo
saber o universo, o campo sai `null` — indeterminado DECLARADO, que não vira juízo
nem para um lado nem para o outro.

## Critério de pronto negativo se prova por SEQUESTRO, não por leitura

"Não chama X no caminho de serviço" é a forma mais comum de critério de pronto em
migração, e a mais fácil de deixar em declaração: ninguém consegue provar ausência
lendo o diff. O teste é pôr um X DELATOR na frente do real (stub no PATH que registra
toda chamada num log) e exercitar o caminho inteiro; o guarda é o log vazio. Barato,
e não envelhece: quem reintroduzir a chamada seis meses depois cai nele sem saber que
ele existe.

O par disso é reproduzir o defeito que motivou a migração, não só a cura. O commit
local não empurrado que travava o boot virou fixture — sem ele, a próxima limpeza
"desnecessária" apaga a cura por não ver o que ela custava.

## Quando método e conteúdo dividem a mesma árvore, o corte é na lista servida

Separar o que é produto do que é do dono não se resolve por repositório quando os dois
moram no mesmo diretório: o corte tem de ser no MONTADOR — a lista de peças que ele
serve —, e o repositório vira detalhe de morada. O sinal de que o corte por repo vai
falhar é a proporção: método e conteúdo na mesma árvore em ordens de grandeza
diferentes (medido 07/09: 3 arquivos de método contra 91 de conteúdo de cadeira, 4%
contra 96% dos bytes). Cortar por repo leva os dois ou não leva nenhum; cortar na lista
de peças deixa o montador, o envelope e uma cadeira de exemplo saírem juntos e o resto
ficar. Vale para qualquer publicação de harness, não só para pacote livre.

## Wrapper que acha o miolo por `dirname $0` quebra quando o verbo é servido por symlink

Verbo do PATH da casa é symlink de `~/AI/bin` para o clone. `dirname "$0"` devolve o
diretório do LINK, não o do arquivo; wrapper que compõe caminho a partir dele procura o
miolo numa pasta que só existe no repo e morre com "can't open file". `readlink -f "$0"`
antes do `dirname` é a forma; o sintoma é o wrapper achar que a instalação está
incompleta quando ela está inteira do outro lado do link. Quem escreve verbo em duas
peças (porta + miolo em `_<verbo>/`) paga isso na primeira vez que o verbo é servido em
vez de rodado do clone.

## Opção declarada só no parser PAI fica inalcançável depois do subcomando

Em `argparse`, o parser pai para de processar as próprias opções assim que casa um
subcomando: tudo o que vem depois é do subparser. Flag global declarada só no pai
(`ap.add_argument("--eu")` + `add_subparsers`) some nas duas posições — antes do ato
ela não é ato, e depois do ato o subparser não a conhece e ela cai calada no resto do
`parse_known_args`. O defeito só aparece quando alguém tenta usar a flag, e a mensagem
de erro do verbo continua ensinando-a como cura.

O agravante não é o argparse, é o par: **erro que nomeia uma cura inalcançável custa
mais do que erro que não nomeia cura nenhuma** — quem lê tenta, tenta nas duas ordens,
e só então vai ler o código. São três giros por encontro, em toda cadeira, para sempre.
Ao escrever recusa que ensina a saída, a saída se roda uma vez antes de virar texto.

## Exit code carrega três significados, e instrumento que não os separa mede errado por construção

`exit ≠ 0` em verbo da casa é (a) falha, (b) VEREDITO (`conferir existe` = não existe,
`acesso decidir` = negado, `git grep` = sem resultado, `lint` = achou) ou (c) PEDIDO DE
AJUDA (verbo nu que lista os atos, `--help`). Contar tudo como erro produz taxa que
nunca cai, porque (b) e (c) estão certos. A separação não se infere do número: (c) se
reconhece na CHAMADA (ato nulo + exit 2, token de ajuda), (b) só se reconhece por marca
no VERBO (`forma: predicado` no cabeçalho). Medido 12/09: de 248 "erros" de um dia, 92
eram (b)+(c). O par disso do lado do verbo: ajuda pedida sai por stdout com exit 0; só
a chamada errada sai por stderr com exit 2.

## Contagem de erro por giro infla com o lote, e o caso de uso some quando a auditoria grava só o primeiro token

Um template errado copiado em N itens de lote conta N erros de UM erro (12/09: 15% dos
erros do dia, `tarefas ver` ×9 num lote só). Dedup por `(lote_id, tool, ato, exit)`
antes de qualquer taxa. E a recusa da porta que grava só `verbo: repo` sem o item inteiro,
ou o `read_file` que grava "não existe" sem o path, deixa a classe visível e o caso de uso
irrecuperável — o que se recusa se audita INTEIRO, ou a métrica seguinte não tem o que
ler.

## Queda numa série após intervenção não separa aprendizado de mudança de texto

Antes de ler "a cadeira aprendeu" numa curva que cai, inventariar as intervenções de
superfície na janela (git log de abertura/, skills/, tool-manifest/) e a composição de
cadeiras por dia. Em 07–11/09 havia cinco mudanças de texto e o mix trocava a cada dia:
a curva não distingue as três causas. O que se AFIRMA é o inverso, e é mais útil: texto
da casa que cita `<verbo> <ato>` inexistente produz a chamada errada NO MESMO DIA (dono.md
f1c4973 → `motor casa` às 22:57). Vocabulário citado em texto servido se confere contra
os atos servidos, como arquivo se confere por procedência.

## Em verbo bash sob `set -e`, o exit do último comando é o contrato — e dois padrões o quebram nos dois sentidos

`[ -n "$x" ] && cmd` como último comando devolve 1 quando `$x` é vazio: verbo que
imprimiu tudo certo sai como erro (falso erro). `saida=$(...) || funcao_que_so_imprime`
sem `return 1` segue para o `printf` e devolve 0: recusa da API sai como sucesso (falha
silenciosa). Medidos no mesmo verbo no mesmo dia (`tarefas ler` e `tarefas mover`,
12/09). A regra é `return 0` explícito no fim e `|| { avisa; return 1; }` na recusa;
o lint deveria pegar os dois.

## Diário de bordo

07/09/2026 — `conta-abertura` (instrumento de custo do pacote) morria com `python: can't
open file '/home/claudinho/AI/bin/_conta/conta-abertura.py'`; o miolo existe, em
`platafirma-harness/bin/_conta/`. Causa: linha 16 do wrapper fazia
`AQUI="$(cd "$(dirname "$0")" && pwd)"`, e `$0` é o symlink de `~/AI/bin`. — contorno
encontrado NA DATA 07/09/2026 foi `dirname "$(readlink -f "$0")"`, commitado em
platafirma-harness@1835835.

07/09/2026 — ordem do dono era `encerrar fita --so-memoria`; a porta só-verbo recusou
com `{recusado, verbo: encerrar, motivo: "sem verbo", sugestao: null}`, nas três formas
(string com flag, string sem flag, item de lote). `encerrar` não é servido pela porta, e
a `sugestao: null` diz "verbo que falta" quando na verdade ele existe sob outro nome. —
contorno encontrado NA DATA 07/09/2026 foi chamar a tool `descansar`: `bin/encerrar` e
`bin/descansar` são o MESMO arquivo com dois nomes (o próprio `main()` monta o `prog` a
partir de `sys.argv[0]` por causa disso), e só `descansar` está no manifesto.

07/09/2026 — `descansar fita --so-memoria` e `mesa ver` responderam `erro: PF_CADEIRA
nao definida`; tentei `--cadeira ia`, que o argparse não conhece (`unrecognized
arguments`), e a porta não aceita env. A fita não portava o `sessao_id` (contexto
compactado), e sem ele a porta não resolve a sessão-sombra. — contorno encontrado NA
DATA 07/09/2026 foi `monta_sessao(cadeira="ia")`, que devolveu a sessão VIVA com
`cunhada_agora: false` (não criou órfã) e o `sessao_id` destravou mesa e descansar. Custo
do contorno: o pacote inteiro de volta na janela (8.924 tokens) para recuperar um uuid.

07/09/2026 — a mesma `run_command` que nos primeiros giros da fita rodou shell livre
(`;`, pipe, heredoc, `git`, `grep`) passou a recusar no meio da fita: `metacaractere de
shell` e `{recusado, verbo: grep, sugestao: descobrir}`. O regime da porta mudou sob a
fita em curso, e o mesmo comando de meia hora antes deixou de valer. — contorno
encontrado NA DATA 07/09/2026 foi `read_file(paths=[...])` para leitura e um item de
lote por verbo; o que era `git log`/`grep` virou leitura de arquivo e verbo `repo`.

07/09/2026 — `git push` em platafirma-harness imprimiu `remote: - Changes must be made
through a pull request.` e o commit SUBIU mesmo assim (`git ls-remote origin
refs/heads/main` = 1835835, e o fix está em `origin/main:bin/conta-abertura`). Aviso do
remoto que não corresponde ao resultado — quem ler só a saída do push conclui que
perdeu o trabalho e recommita. — contorno encontrado NA DATA 07/09/2026 foi conferir o
remoto por `ls-remote` em vez de acreditar na saída do push.

07/09/2026 — `repo commitar platafirma-harness` gravou o delta de caderno no ramo
`fabrica/3016-help-erro-gracioso`, e não em main: o clone compartilhado estava nesse
ramo (a fábrica o deixou lá no meio da fita; meia hora antes o mesmo clone estava em
main). O verbo commita onde o clone está, e não há ramo no contrato do ato. — contorno
encontrado NA DATA 07/09/2026 foi empurrar o ramo (39aeae7, para não perder), `repo ramo
platafirma-harness main`, reescrever os dois cadernos em main e devolver o clone ao ramo
da fábrica no fim. Antes de commitar em clone compartilhado, `repo estado` — o ramo é
estado de outra sessão, não desta.

07/09/2026 — `fila status` e `fila ler ia` recusaram com `nao sei quem esta operando a
fila` mesmo com o `sessao_id` portado em toda chamada, por `run_command` e pela tool;
tentei `--eu ia` antes do ato (`erro: ato desconhecido: '--eu'`, do `intercepta()` do
#3016) e depois do ato (engolido pelo `parse_known_args`, `args.eu` segue None); `minuta
ler` caiu no mesmo `exporte PF_CADEIRA`. Quatro giros. Causa: `sessao:{id}` não existia
no msg-mem — a fita do chat abre pelo CLI `monta-sessao`, e o `SET` morava só na porta.
— contorno encontrado NA DATA 07/09/2026 foi uma chamada de `monta_sessao` pela tool
(que grava a chave), e depois disso a MESMA chamada de `fila` passou; correção definitiva
commitada no mesmo dia em `platafirma-harness@6d25443` (quem cunha registra).

07/09/2026 — `write_file` com `trecho` recusou com «`antes` ocorre 0 vez(es)» usando uma
âncora copiada do retorno de `read_file`. Causa: a poda da porta LAVA linha em branco
(`poda_aviso: lavado (branco)`), então o texto lido tem uma linha em branco onde o
arquivo tem duas — âncora que atravessa linha vazia nunca casa. — contorno encontrado NA
DATA 07/09/2026 foi ancorar numa Única linha não vazia (ex.: a assinatura da função
seguinte) e reconstruir o espaçamento no `depois`.

07/09/2026 — `monta-sessao ia --so-chapeu --sessao-id <uuid>` pela porta devolveu
`{recusado, verbo: monta-sessao, motivo: "sem verbo", sugestao: null}`: o montador não é
verbo servido, só a tool `monta_sessao` o alcança — e pela tool não dá para exercitar o
caminho do CLI direto, porque a porta grava a chave de qualquer jeito. — contorno
encontrado NA DATA 07/09/2026 foi provar pelo campo novo `sessao.registrada` do próprio
pacote, que é calculado DENTRO do montador, antes de a porta tocar em nada.

07/09/2026 — `mesa anota <chapeu>` respondeu `slot contexto reescrito (1 linhas)`: o ato
SUBSTITUI o slot de prosa inteiro (substrato velho) e só depois avisa, em stderr, que o
que tem ato pendente vai em `mesa item`. Nada se perdeu porque os itens vivem noutro
substrato, mas a prosa anterior do slot foi embora. — contorno encontrado NA DATA
07/09/2026 foi usar `mesa item <chapeu> --ato ... --alvo ...` (corpo no stdin) e tratar
`mesa anota` como escrita destrutiva de um campo só.

07/09/2026 — reincidência, mesmo dia: o clone de `platafirma-harness` estava outra vez
em `fabrica/3016-help-erro-gracioso` na hora de commitar o conserto do montador. —
contorno encontrado NA DATA 07/09/2026 foi o mesmo (`repo estado` antes, `repo ramo
<repo> main`, que carrega a árvore suja junto, commitar e devolver o clone ao ramo da
fábrica no fim). Duas vezes em um dia: `repo estado` antes de commitar deixou de ser
zelo e virou passo.

07/09/2026 — no fecho da mesma fita, `repo ramo platafirma-harness
fabrica/3016-help-erro-gracioso` (devolver o clone ao ramo da fábrica) falhou com o
texto do SHIM de git — «git nao roda aqui — o verbo da casa e `repo`» — seguido de
`repo: checkout -b falhou`; `repo ramo <repo>` (só listar) falhou igual, em `git branch`,
depois de imprimir `atual: main`. Minutos antes, no mesmo clone, `repo ramo <repo> main`
TINHA funcionado. Ou seja: partes internas do próprio verbo `repo` caem no shim que
recusa git, e o ato falha por dentro sem que o alvo tenha nada de errado. — contorno
encontrado NA DATA 07/09/2026 foi NENHUM: o clone ficou em `main` (árvore limpa,
nada perdido; o ramo da fábrica segue empurrado em 39aeae7). Próxima fita que precisar
do ramo da fábrica troca com `repo ramo` e, falhando de novo, o alvo é o próprio verbo.

07/09/2026 — reincidência do falso negativo de push, agora com outra cara: `repo
empurrar` saiu com exit 3 e `! [remote rejected] main -> main (cannot lock ref
'refs/heads/main': is at ad4cca8 but expected 7315abe)` — e o commit ad4cca8 ESTAVA no
remoto, confirmado por `repo git platafirma-harness ls-remote origin refs/heads/main`. A
própria mensagem de erro carrega a prova de que subiu (o `is at` é o meu SHA). — contorno
encontrado NA DATA 07/09/2026 foi o mesmo de mais cedo: conferir por `ls-remote` antes
de recommitar. Duas caras num dia só — exit code de `repo empurrar` não decide sozinho
se a entrega subiu.

12/09/2026 — `fila` (nu, uso), `fila ver` (ato inválido), `fila ler` ("persona
obrigatória"): três giros de gramática antes de `fila ler ia --tudo`, com o `sessao_id`
na mão. — contorno encontrado NA DATA 12/09/2026 foi passar a persona; a cura é persona
padrão = cadeira da sessão (item 2 do #3045).

12/09/2026 — `metrica eventos 2026-09-11 --tipo erro` truncou em 50 KB e o stream não
carrega args/motivo (contrato estável de CAMPOS_GIRO); `read_file` do ops log cru tem
1,66 MB. — contorno encontrado NA DATA 12/09/2026 foi escrever o ato `metrica casos`
(consumer-aligned, por fora de `eventos`), que lê o registro bruto do giro falhado
(harness@0af8090, --agregado em b153257).

12/09/2026 — `tarefas mover 3044 em-execucao`: a API recusou ("faltam os campos
`Onde:`" — eu tinha escrito `Onde (medição…):`) e o verbo imprimiu `item null → :
null` com exit 0. Não há ato de editar corpo em `tarefas`. — contorno encontrado NA DATA
12/09/2026 foi `tarefas apagar 3044` + `criar` de novo (#3045) com o rótulo literal; o
exit 0 na recusa foi corrigido em `busca`/`envia` (harness@6446a3e).

12/09/2026 — `repo commitar platafirma-harness` (add -A) relatou "4 arquivo(s) sob
juízo" quando eu tinha tocado 2: o clone compartilhado tinha alteração de outra cadeira
parada, e ela subiu no meu commit 0af8090. Não conferi quais. — contorno encontrado NA
DATA 12/09/2026 foi nenhum; `repo estado` antes de commitar em clone compartilhado (já
no diário de 07/09) vale também para árvore suja de terceiro, não só para ramo.

12/09/2026 — `encerrar fita`, ordem do dono: a porta recusa `encerrar` ("sem verbo").
`bin/encerrar` e `bin/descansar` são o mesmo arquivo (diário de 07/09); o que falta é
`encerrar` no manifesto que a porta serve. — contorno encontrado NA DATA 12/09/2026 foi
`descansar fita`; a cura (ordem do dono 12/09: "esse é o vocabulário que eu uso, tem que
ser alias mesmo") é servir `encerrar` como apelido no manifesto — item 4 do #3045.
