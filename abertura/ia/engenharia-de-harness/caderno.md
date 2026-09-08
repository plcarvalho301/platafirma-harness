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
