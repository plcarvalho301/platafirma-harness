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

Projetos do rastreador: `46 Cards` · `1 Inbox` são projetos reais; id negativo
(`-6 Fabrica`, `-7 Carteira`, `-8 Triagem`, `-9 Parado`, `-10 Épico-Harness`,
`-11 Carteira pessoal`, `-12 Refino`) é **filtro salvo** — lê, não recebe card.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.
