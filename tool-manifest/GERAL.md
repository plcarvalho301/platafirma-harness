# tool-manifest — GERAL, toda cadeira

Comum a todas as cadeiras. Redação de claudinho-TI; forma de RH. Manifesto de
cadeira não replica o que está aqui — aponta.

> **Verbo novo em `bin/`, mesmo commit:** linha aqui antes do push. Ferramenta
> existente e não indexada é ferramenta inexistente.


```
ver minha caixa                 : fila status <persona>
ler mensagens                   : fila ler <persona> [remetente]
baixar o que processei          : fila consumir <persona> <id>... | --de <rem> | --todas
mandar recado                   : fila enviar <dest> --de <rem> --tipo <t> --assunto <a>
                                  (corpo em stdin; --ref, --responde opcionais)
abrir sessão de uma cadeira     : monta-sessao <cadeira>   [tool monta_sessao é a via boa]

ler um card                     : tarefas ler <id>
listar projetos                 : tarefas projetos
listar cards abertos            : tarefas listar <projeto>        (listar-tudo inclui fechados)
abrir card                      : tarefas criar <projeto> "<título>" [--desc "<txt>"|--desc-stdin] [--prio N]
comentar                        : tarefas comentar <id> ["<txt>"]  sem txt, lê stdin
fechar                          : tarefas fechar <id>
amarrar subtarefa               : tarefas sub <pai> <filho>
o que o verbo não cobre         : tarefas api <MÉTODO> <caminho> | tarefas api-corpo (JSON em stdin)

estado do acervo (5 degraus)    : acervo-status            [--json | --detalhe]
                                  ÚNICA fonte de número do acervo — ver regra abaixo

o que está no ar                : infra estado
está tudo saudável?             : infra saude
log de contêiner ou unit        : infra logs <alvo> [n]     descobre qual dos dois é
reiniciar sem se matar          : infra restart <unit>      destacado por systemd-run
mexer no compose do core        : infra compose <args...>

estado do repo                  : git -C ~/AI/<repo> status --short
publicar                        : git -C ~/AI/<repo> add -A && git ... commit -m "..." && git ... push
job > 2 min                     : longjob run <nome> <cmd...>   | list, logs, status, log, stop

venv reprodutível               : uv venv / uv pip install / uvx <pkg>
rodar script solto              : python3 (3.12.3, sem shim de pip — usar uv pip)

buscar em ~/AI                  : rg <padrão>          (~16 ms; grep -r aposentado)
achar arquivo                   : fd <nome>
ler JSON / YAML / log           : jq · yq (não usar regex em config) · lnav
histórico de carga              : sar                  (única que responde "há 3 horas")
espaço                          : df -h · du -sh · ncdu
```

> **Número do acervo sai de `acervo-status`, nunca de SQL na mão.** Contagem crua
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

Projetos do rastreador: `46 Cards` · `1 Inbox` são projetos reais; id negativo
(`-6 Fabrica`, `-7 Carteira`, `-8 Triagem`, `-9 Parado`, `-10 Épico-Harness`,
`-11 Carteira pessoal`, `-12 Refino`) é **filtro salvo** — lê, não recebe card.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.
