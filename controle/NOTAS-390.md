# Notas de construção — card #390 (não é documento do produto, é bloco de referência da fábrica para esta branch)

Isto existe só para dar contexto completo aos agentes que implementam este card sem
precisar reabrir MCP/wiki a cada arquivo. Fonte de verdade continua sendo o card e a spec
— isto é cópia de trabalho, pode envelhecer.

## Card #390 (texto completo)

F3f/fábrica — plano de controle do harness: verbos --json, agregador e tela
#297 · projeto=46 · labels: claudinho-TI, FEATURE

Fábrica. Repo único: platafirma-harness.

O QUE SAI: Um serviço web em harness.platafirma.org que responde "o que está acontecendo
agora" com os quatro blocos da spec, mais /cadeira/<slug> e /feito. A spec é a fonte do que
a tela mostra. Este card dá a construção. Divergência entre os dois: a spec vence no
conteúdo, este card vence no mecanismo.

ENGINE — decidido, não é escolha da fábrica: Render no servidor, sem framework de front,
sem build, sem bundler. Python 3.12, venv por uv. Os wireframes são HTML sem uma linha de
JavaScript e o design/tokens.css é servido como arquivo estático, sem transformação.
Revalidação de 60s é recarga da página, não SPA. Cláusula de não-vínculo: nenhuma escolha
desta construção vincula a decisão de engine de front da PlataFirma (F5).

TRÊS LOTES, nesta ordem:

LOTE 1 — saída legível por máquina nos verbos. Nenhum dos verbos que alimentam bloco tem
--json hoje (medido em 10/08/2026: fila, tarefas, infra, conferir, todos zero). Acrescentar
--json a: fila status, infra estado, infra saude, conferir servico, conferir verbo,
conferir skill, conferir repo, tarefas listar.
Regras da flag: --json escreve JSON em stdout e nada mais, diagnóstico para stderr. Exit
code preservado (inclusive o 1 de conferir quando há divergência). Falha do verbo sai como
objeto com erro preenchido, nunca stdout vazio nem sucesso com zero fake. Texto atual sem a
flag não muda uma linha. Cada verbo leva teste de contrato.

LOTE 2 — agregador de estado. Processo que executa os verbos em timer e escreve UM arquivo
de estado em JSON. A tela lê o arquivo; nunca executa verbo em resposta a request. Cada
bloco de estado carrega o instante da leitura (idade) e o resultado: ok, ou indisponivel
com motivo. Verbo que falhou/timeout/não respondeu vira indisponivel com motivo, nunca
ausência do bloco, nunca zero. Zero legítimo != ausência de leitura. Timer independente por
verbo — verbo lento não segura os outros. Leitura de fila sempre fria (--tudo/--desde),
nunca fila ler quente. O agregador não escreve em lugar nenhum além do próprio arquivo de
estado.

LOTE 3 — tela. Rotas: / (recepção, 4 blocos na ordem da spec), /cadeira/<slug>, /feito.
Conteúdo/ordem/cor/ausência: spec §4-6, não inventar bloco nem reordenar. Duas ações só:
despachar recado (fila enviar) e reiniciar alvo (infra restart <alvo>) — ambas chamam o
verbo, nenhuma reimplementa. Exclusão dura no restart: cloudflared e oauth2-proxy NUNCA são
alvo selecionável (aparecem no bloco 1 como leitura, com a exclusão declarada na linha).
Restart exige alvo explícito + confirmação com o nome por extenso no botão. Sem
localStorage/sessionStorage, sem estado no cliente.

MODELO DE TESTE (decidido, é o precedente da casa): pytest, venv uv. Três camadas:
1. Contrato de verbo: por verbo com --json, um teste de formato + um de falha.
2. Agregador: unidade sobre a transformação saída-de-verbo→estado; caso inegociável: verbo
   morto → indisponivel com motivo.
3. Fumaça HTTP: serviço sobe, 3 rotas respondem, recepção tem os 4 blocos, verbo morto não
   pinta linha saudável.
Fora: teste de navegador, e2e, meta de cobertura. Suíte verde é aceite. NÃO instalar hook
de commit que rode a suíte.

BORDA (não é da fábrica, é de TI): DNS, rota cloudflared, oauth2-proxy, stack de deploy,
unidade que roda o agregador. Fábrica entrega: serviço em loopback, porta por env var,
compose que sobe agregador e tela. Não abrir porta publicada, não tocar cloudflared/
oauth2-proxy.

FORA DE ESCOPO: sonda/healthcheck (trilha C, #254, é de TI — bloco Sinal consome o que
existir, serviço sem sonda = "sem sinal" em caveat). Gestão de acessos/multiusuário (F6).
Qualquer escrita no rastreador/wiki/mesa de outra cadeira.

ACEITE:
1. As três rotas respondem atrás do proxy, recepção mostra os 4 blocos com idade do dado.
2. Verbo derrubado de propósito → linha correspondente vira indisponivel com motivo. Nenhum
   verde, nenhum zero, nenhum bloco sumido. Conferível derrubando o rag-extractor-api.
3. Caixa com carta parada + persona com componente defasado aparecem sem ninguém consultar.
4. Recado despachado da tela aparece em `fila ler --desde` com o mesmo envelope do verbo em
   linha de comando.
5. Suíte roda verde, cobre as três camadas.
6. `git grep` por localStorage, sessionStorage e nome de framework de front no diff volta
   vazio.

## Spec (platafirma-arquitetura/docs/spec_plano-de-controle-harness.md) — pontos que regem
o desenho de dado, não só de tela

- Réguas de admissão: (1) espelho humano — todo elemento operável espelha um processo que
  um humano faria; (2) verbo por trás — nada aparece na tela que não venha de verbo em
  bin/, e nenhuma ação é segunda implementação.
- Princípio central: ausência de dado se desenha como ausência, NUNCA como saúde. `0` e `—`
  são visualmente e semanticamente distintos.
- Papéis de cor: `alert` (fora/divergente), `caveat` (degradado/sem leitura/sem sonda),
  `accent` (só o número da faixa de topo), `danger` (declarado, não usado na v1). Máximo
  dois papéis de cor por tela — aqui: alert + caveat.
- **Bloco 1 — Sinal** ("quebrou alguma coisa?"): uma linha por serviço do compose + sonda
  de runtime + sonda externa. Três estados: no ar (neutro/calmo) / degradado (caveat) /
  fora (alert). Cada linha: caminho exercitado + idade. Serviço sem sonda → "sem sinal" em
  caveat (não some da lista). Ação: reiniciar (restart), com cloudflared/oauth2-proxy
  excluídos.
- **Bloco 2 — Caixas** ("tem mensagem parada?"): uma linha por caixa — persona,
  profundidade (pendentes), idade da mensagem mais antiga, data da última leitura. Acima do
  limiar → alert. Caixa encerrada declara o porteiro/roteamento, não some da lista. Leitura
  sempre fria. Ação: despachar recado.
- **Bloco 3 — Cadeiras** ("meus agentes estão inteiros?"): uma linha por cadeira — persona,
  sha/head_em/sincronizado_em do pacote, manifesto presente/ausente, ocupação (lock+TTL),
  idade da mesa. Componente defasado / manifesto ausente → alert. Cadeira suspensa aparece
  marcada, não desaparece. Sem ação na v1.
- **`/cadeira/<slug>`**: abre da lista do bloco 3. Três colunas — esquerda: lista de
  cadeiras com estado de ocupação (suspensa/externa marcadas, nunca omitidas); centro:
  cabeçalho (nome/head/gerências/procedência) + documento por seletor (persona · manifesto
  da cadeira · GERAL · org canônico · mesa · cadernos), cada doc carimba caminho+blob;
  direita: estado vivo (ocupação+TTL, profundidade/idade da caixa, idade da mesa, cards
  abertos, integridade por componente). "É a mesma composição que monta_sessao já serve à
  sessão, com o corpo dos cadernos sob demanda." Só leitura.
- **Bloco 4 — Procedência** ("o módulo está externalizado?"): quatro predicados booleanos,
  um por sub-ato de `conferir` (servico/verbo/skill/repo). Verde/vermelho + nº de
  divergências + lista sob demanda. Lista de exceções nomeadas: ausência de lista reprova
  (é diferente de lista vazia).
- **Rodapé**: três saídas (wiki, git do harness, rastreador), link com endereço visível.
- **`/feito`**: cards fechados no rastreador + commits do harness, agrupados por dia,
  card/commit que se referenciam aparecem juntos, órfão aparece como órfão. Nada é escrito
  aqui — página derivada, sem estado próprio.
- Ações recusadas com motivo (não implementar): `fila ler` quente, `deploy`, `tarefas
  criar/fechar`, `mesa`/`encerrar` de outra cadeira.
- Design: consome só `design/tokens.css` — cartão=`.cartao` (bg-surface, border-default,
  radius-md, card-padding, sem stripe lateral); chip = cor+palavra sempre juntas; números/
  idade em tabular-nums, alinhados à direita; corpo em text-body (piso 15px), metadado em
  text-meta.
- Dependência nomeada: sinal do bloco 1 depende da trilha C (#254, sonda/healthcheck) — sem
  isso o bloco nasce inteiro "sem sinal", honesto e é o esperado nesta v1.

## Wireframes — classes CSS a reusar literalmente

`design/wireframes/harness-recepcao.html`: `.topo` (`.marca`, `nav a[aria-current]`,
`.dir`), `.folha`, `.cartao`, `.cab-bloco` (`h2`, `.pergunta`, `.idade num`), `.chip`
(`.alert`/`.caveat`/`.calmo`), tabelas com `td.dir`/`th.dir`, `td .alvo`, `td .caminho`,
`.acao`/`.acao.primaria`/`.acao[disabled]`, `.motivo`, `.indisponivel`, `.predicados`/
`.pred` (`.verbo mono`, `.valor`/`.valor.mal`), `.saidas`/`.saida` (`b`, `.pergunta`,
`.url`), `.nota`.

`design/wireframes/harness-cadeira.html`: mesmo `.topo` (nav diferente, sem botão
Atualizar, só `.revalida`), `.grade` (`grid-template-columns: 232px minmax(0,1fr) 272px`),
coluna 1 `.cadeiras li a[aria-current] .est`, coluna 2 `.cab` (`h1`, `.head`,
`.gerencias`, `.proc`) + `.docs button[aria-pressed]` + `.leitura .carimbo mono` +
`.leitura .corpo h4`, coluna 3 `.par dt/dd` (Agora / Integridade / Fila da cadeira),
`.indisponivel`.

`design/tokens.css`: variáveis semânticas a usar (nunca cor/tipo/espaço cru): `--platafirma-
fg-default/body/muted/accent`, `--platafirma-bg-page/surface/sunken/chip`, `--platafirma-
border-default`, `--platafirma-alert-bg/bd/fg`, `--platafirma-caveat-bg/bd/fg`,
`--platafirma-radius-md`, `--platafirma-card-padding`, `.chip` usa border-pill (radius
`pill`), `tabular-nums` já é regra global em `table, time, .platafirma-num`.

## LOTE 1 — mapa verbo → campo JSON → bloco (ver plano completo em
`../../../.claude/plans/wondrous-sprouting-bubble.md` se precisar do resto do contexto;
esta seção é a parte que interessa à implementação linha a linha)

| Verbo | Bloco | Campos mínimos do `--json` |
|---|---|---|
| `fila status <persona>\|--todas --json` | 2 — Caixas | por persona: `persona`, `pendentes` (int), `total_historico` (int), `estado` (`vazia`\|`em_dia`\|`parada`\|`fechada`), `idade_mais_antiga_seg` (int ou null), `ultima_leitura_seg` (int ou null, idle do consumer). Hoje `conta_novas()` só devolve `(novas, total)` — precisa estender pra também expor idade/última leitura (dado já existe no Redis: timestamp no `msgid`, `XINFO CONSUMERS` idle). Caixa fechada (porteiro) não é erro — é um estado, com o texto do porteiro em `motivo`. |
| `infra estado [alvo] --json` | 1 — Sinal | `{"conteineres": [{"nome","estado_docker","saude","desde"}], "units": [...], "timers": [...]}` — estruturar o que hoje vira texto tabulado, direto de `docker ps --format json` / `systemctl --user list-units --output=json` em vez do texto atual. |
| `infra saude --json` | 1 — Sinal (saúde agregada) | `{"ops_health": {"ok", "motivo"}, "doentes": [...], "falhadas": [...], "disco": {...}, "memoria": {...}}`. |
| `conferir servico [nome] --json` | 4 — Procedência | `{"resultado": "ok"\|"divergente", "servicos": [{"nome", "divergencias": [...]}]}`, exit 0/1 preservado (função `conferir_servico` já devolve 0/1 — só precisa passar a **também** montar isto como dict e, se `--json`, `json.dumps` em vez de `print`). |
| `conferir verbo [nome] --json` | 4 | idem, `{"resultado", "verbos": [{"nome","origem","capacidade","conforme","motivos":[...]}]}`. |
| `conferir skill <nome> --servido <blob> --json` | 4 | `{"skill","fonte_blob","servido_blob","veredito": "em_dia"\|"divergente"\|"indeterminado","detalhe"}`. Sem `--servido`: veredito `indeterminado`, exit 2 — é o comportamento correto (ausência, não conformidade), não "consertar". |
| `conferir repo [nome\|--staged] --json` | 4 | `{"resultado","repos": [{"nome","achados": {"GERADO":[...],"ACERVO":[...],...}, "readme_ok"}]}`. |
| `tarefas listar <projeto> --json` | rodapé/roteamento | Mais simples dos oito: `paginas(...)` já devolve um array JSON antes de `linhas_de_card` reformatar em texto — `--json` é só imprimir esse array direto, sem o `jq -r` de tabulação. |
| `monta-sessao <cadeira> --json [--sem-atualizar]` (extensão assumida, ver comentário no card) | 3 — Cadeiras (via agregador, sempre com `--sem-atualizar`) e `/cadeira/<slug>` (on-demand, sem a flag — pode puxar) | `{"cadeira","persona": {"presente","caminho"}, "manifesto": {"presente","caminho"}, "org": {"caminho"}, "mesa": {...}, "cadernos": {...}, "fila": {...}, "atualizado": bool}`. `--sem-atualizar` pula o `git pull --ff-only` das duas linhas do script atual. |

Regra comum a todos: quando `--json`, stdout é só o JSON (diagnóstico em stderr); texto
atual sem a flag não muda; falha do verbo é `{"erro": "<motivo>"}` em vez de stdout vazio,
com o exit code que já era o de falha.

## Ambiente de desenvolvimento local (esta máquina Windows)

Sem docker, sem systemctl, sem jq, sem redis rodando. `uv`/python 3.13/git/bash/curl
disponíveis. Os testes de contrato (camada 1) **não** devem depender de infra viva:
- Verbos Python (`conferir`, `fila_streams.py`, `monta-sessao` se virar Python ou ganhar
  wrapper): isolar a função que fala com o mundo (`sh()`, `redis.Redis`, `subprocess.run`)
  atrás de algo mockável (`unittest.mock.patch`/monkeypatch), testar a lógica de
  formatação/contrato injetando saída canônica.
- Verbos Bash (`infra`, `tarefas`): se o teste precisar rodar o script de verdade, usar um
  `PATH` de teste com stubs (scripts fake de `docker`/`systemctl`/`curl`/`jq`) escritos à
  mão nos fixtures — nada de baixar binário nenhum. Alternativa mais simples: testar a
  parte que decide o formato (se ela puder ser isolada em um trecho `python3 -c` dentro do
  script) via chamada direta.
Verificação end-to-end contra infra real (docker de verdade, redis de verdade) acontece
depois, no host, via ops-server ou na integração que claudinho-TI roda ao aceitar — não é
o que a suíte local precisa provar.
