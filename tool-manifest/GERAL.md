# tool-manifest — GERAL, toda cadeira

Comum a todas as cadeiras. Redação de claudinho-TI; forma de RH. Manifesto de
cadeira não replica o que está aqui — aponta.

> **Verbo novo em `bin/`, mesmo commit:** linha aqui antes do push. Ferramenta
> existente e não indexada é ferramenta inexistente.


```
ver minha caixa                 : fila status <persona>
ler mensagens                   : fila ler <persona> [remetente]     tira o token de posse
baixar o que processei          : fila consumir <persona> <id> --posse <tok> | --de <rem> | --todas
soltar sem consumir             : fila largar <persona> <id> --posse <tok>   (--forca: token perdido)
mandar recado                   : fila enviar <dest> --tipo <t> --assunto <a>
                                  (corpo em stdin; --ref opcional; --responde <id> exige --posse)
abrir sessão de uma cadeira     : monta-sessao <cadeira>   [tool monta_sessao é a via boa]

ler um card                     : tarefas ler <id>
listar projetos                 : tarefas projetos
listar cards abertos            : tarefas listar <projeto>        (listar-tudo inclui fechados)
abrir card                      : tarefas criar <projeto> "<título>" [--desc "<txt>"|--desc-stdin] [--prio N]
comentar                        : tarefas comentar <id> ["<txt>"]  sem txt, lê stdin
fechar                          : tarefas fechar <id>
amarrar subtarefa               : tarefas sub <pai> <filho>
o que o verbo não cobre         : tarefas api <MÉTODO> <caminho> | tarefas api-corpo (JSON em stdin)

estado do acervo (5 degraus)    : acervo status           [--json | --detalhe]
                                  ÚNICA fonte de número do acervo — ver regra abaixo
demais atos do acervo           : acervo                  sem argumento, lista os sub-atos
consulta ao RAG pela linha      : ragq "<pergunta>"       mesmo contrato do rag_search do MCP

o que está no ar                : infra estado [alvo]
está tudo saudável?             : infra saude  [alvo]
log de contêiner ou unit        : infra logs <alvo> [n]     descobre qual dos dois é
reiniciar sem se matar          : infra restart <alvo>      destacado; exige alvo explícito

promover release de uma stack   : deploy <stack> up -d      stack obrigatória, sem default
ver o declarado de uma stack    : deploy <stack>            não toca em nada
quais stacks existem            : deploy                    lista o registro

declarado x servido             : conferir servico [nome]   exit 1 = há divergência
verbo x arq:0037                : conferir verbo [nome]     origem, cabeçalho e a conta
repo x arq:0042                 : conferir repo  [nome]     o que esta rastreado x a regua
gate de commit (arq:0042)       : conferir repo --staged    o que o pre-commit chama
instalar o gate num clone       : git -C <clone> config core.hooksPath ~/AI/platafirma-harness/hooks
toolkit de segurança            : seg                       despachante (arq:0040)

estado do repo                  : git -C ~/AI/<repo> status --short
publicar                        : git -C ~/AI/<repo> add -A ; git ... commit -m "..." ; git ... push
job > 2 min                     : longjob run <nome> <cmd...>   | list, logs, status, log, stop

venv reprodutível               : uv venv / uv pip install / uvx <pkg>
rodar script solto              : python3 (3.12.3, sem shim de pip — usar uv pip)

buscar em ~/AI                  : rg <padrão>          (~16 ms; grep -r aposentado)
achar arquivo                   : fd <nome>
ler JSON / YAML / log           : jq · yq (não usar regex em config) · lnav
histórico de carga              : sar                  (única que responde "há 3 horas")
espaço                          : df -h · du -sh · ncdu
```

## O verbo declara a capacidade que serve

Todo verbo da plataforma carrega, nas primeiras linhas do arquivo: uma linha de
propósito, `capacidade:` (uma das do mapa da mesa), `dono:` e, quando ajuda,
`componente:`. Capacidade não se inventa no cabeçalho — nome fora do mapa reprova.

Forma extensa do BizBOK e contração valem as duas: `gestao-de-motores` e `motor`
são o mesmo termo, e a conferência as trata como equivalentes.

`conferir verbo` mede isso e a conta de `arq:0037` — um verbo por capacidade — e
sai 1 enquanto houver divergência. Catálogo completo, com origem de cada verbo:
`Ajuda:Catálogo de verbos` na wiki e `docs/catalogo-de-verbos.md` no harness.

Verbo que é despachante de toolkit (`acervo`, `seg`) é o par binário+subcomando,
por `arq:0040`: o binário agrupa, o subcomando é o ato.

> **Número do acervo sai de `acervo status`, nunca de SQL na mão.** Contagem crua
> `WHERE embedding IS NULL` inclui os chunks não-textuais (tabela, figura, layout),
> que nunca recebem vetor por contrato do embedder (`NOT is_not_text AND length(text)>0`)
> — subtrair total menos vetorizados fabrica uma pendência que não existe. Pendência
> real é a linha `embedding parcial` do próprio instrumento. Vale pra toda cadeira:
> quem afirma número do acervo sem ter rodado o instrumento está reportando, não medindo.

## Card por sessão — norma de conduta

Card técnico não tem gatilho de aceite visual: sem isto, ninguém lembra que
existe pra fechar.

- **Início de sessão de execução**: puxar/confirmar o card com pergunta
  binária (`card #N — <título> — é esse?`). Carregar como estado até trocar
  ou encerrar.
- **Fim de sessão**: perguntar fechamento por card do flag, um por um,
  critério explícito — nunca inferência sobre o diff da sessão.
- **Encaminhamento pra outra cadeira** (fila) cita `#N` do flag
  automaticamente quando aplicável.
- **Escrita de git/wiki é manual**, sob pedido explícito do dono — não é
  trigger automático de fim de sessão.

## Fila — o que merece mensagem (teste de admissão)

Medido em 09/08/2026 sobre as 40 mensagens vivas: 19 são `resposta`, contra 8
`pedido` e 7 `decisao`. Resposta é o tipo dominante — a fila virou esteira de
entrega em vez de canal de decisão, e caixa que não zera para de informar.

**Teste, antes de escrever qualquer mensagem: se eu não mandar isto, o que
para?** Nada para → não manda.

- **Manda** só o que precisa de decisão ou insumo de OUTRA cadeira para quem
  escreve continuar. Bloqueio real, não cortesia.
- **Não manda**: entrega concluída, achado registrado, retificação de número,
  aviso de commit, "de acordo", "recebido", agradecimento. Isso é card, commit
  ou nada.
- **Silêncio é aceite.** Concordância não se responde; discordância sim.
- **Profundidade máxima 2.** Pedido → resposta encerra a cadeia. Responder a uma
  resposta é proibido; se a resposta abriu assunto novo, o assunto novo é card
  com dono, não terceira mensagem.
- **Achado fora do escopo do pedido vira card**, não mensagem — salvo se o dono
  precisa decidir hoje para não perder trabalho.
- **Handoff é exceção** e continua valendo: é contexto de abertura, não tráfego.

Quem escreve carrega a prova de que passou no teste: a mensagem diz, em uma
linha, o que trava sem ela. Sem essa linha, a caixa do destinatário não deve
nada — pode consumir sem responder.

## Fila — consumir após ler

Mensagem lida e respondida na mesma sessão: consumir antes de encerrar. Se
precisar dela consistida em outro lugar depois, é disciplina de quem lê, não
motivo pra deixar a caixa acumulando.

**Gatilho é subir a mensagem pro contexto** (`fila ler`), não ela aparecer
como resultado de outra leitura (ex.: grep, listagem, ferramenta que varre o
diretório da fila por engano). Sem chamada explícita de leitura, não consome.

Mensagem que fica aberta por dependência não fechada não se consome — segue
na caixa até resolver.

**A caixa é a malha `msg` (Valkey/Streams), não arquivo.** `ler` tira um token de
posse por mensagem, com TTL de 60 min: `consumir` e `enviar --responde` exigem
esse token, e sessão paralela da mesma cadeira não consome o que a outra está
processando. Perdeu o token da própria leitura: `fila largar ... --forca`.
Retenção da caixa é 7 dias — mensagem é consumo curto; o que tem permanência
vira card, commit ou wiki antes disso.

Projetos do rastreador: `46 Cards` · `1 Inbox` são projetos reais; id negativo
(`-6 Fabrica`, `-7 Carteira`, `-8 Triagem`, `-9 Parado`, `-10 Épico-Harness`,
`-11 Carteira pessoal`, `-12 Refino`) é **filtro salvo** — lê, não recebe card.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.

## Escovação de bit — o que gira a cada fita

Régua do dono: escova-se o que é executado dez milhões de vezes. Aqui isso tem
escopo estreito e nomeável — o miolo do loop de inferência, ou seja tudo que
sobe no contexto a **cada giro de fita**. Meia dúzia de token economizada nesse
miolo é cobrada em todo giro de toda cadeira; a mesma economia fora dele não é
cobrada de ninguém.

- **Gira, logo escova-se**: nome de chave e de stream, nome de verbo e de
  sub-ato, campo de envelope da fila, tool-manifest, descrição de tool, saída
  default de verbo chamado por sessão.
- **Não gira, logo não se escova**: ADR, wiki, README, comentário de config,
  mensagem de commit, log, ajuda extensa de verbo, carta da fila.

A régua corta nos dois sentidos: fora do miolo, verbosidade é barata e a
clareza vence a contração. A pergunta que decide é uma só — *isto sobe no
contexto a cada giro?*
