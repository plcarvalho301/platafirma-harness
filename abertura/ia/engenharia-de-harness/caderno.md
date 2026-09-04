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
`bin/monta-sessao --json --sem-atualizar` nas quatro classes (comum, TI, dados e
**fábrica**, a única `fora_do_quadro`); boot-check com o env real, porque compilar
não é subir e o import roda no boot; e só então restart, confirmando **pela tool**,
que é a superfície que precisa provar.

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
