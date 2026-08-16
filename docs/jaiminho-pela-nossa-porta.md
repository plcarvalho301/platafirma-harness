# Jaiminho pela nossa porta — o `agy` e as duas superfícies

O Jaiminho é colaborador externo, não cadeira: não recebe roteamento entre cadeiras,
não vota e não tem persona de claudinho. Ele roda dentro do contêiner `jaiminho`
(uid 1003 no host, conta separada), num Antigravity CLI (`agy`) autenticado pela
assinatura do dono — sem API paga. Estatuto e rito: `platafirma-arquitetura/docs/
admissao-de-participante.md`; régua de conta: `seg:0011`.

## As duas portas, e quem entra por cada uma

| porta | quem usa | como |
|---|---|---|
| verbo `jaiminho` | claudinho-TI e claudinho-IA, no host | `jaiminho perguntar` / `continuar` |
| sala do Matrix | **o dono, direto** | conversa direta com `Jaiminho`, no celular |

A sala é do **dono**, e só dele. O canal entre cadeiras segue exclusivo com
claudinho-IA (`PARES_EXCLUSIVOS`), e o dono não é cadeira — por isso fala direto,
sem intermediário e sem concessão prévia.

## Como o dono usa

Abrir o Element, aceitar o convite de **Jaiminho** e escrever. Nada mais.
A sala é `!qWNoTUJkUdmsBsheZV:chat.platafirma.org`, MXID `@_pf_jaiminho:chat.platafirma.org`.

Comandos de sala (`pf modelo`, `pf esforco`) **não se aplicam** a ele: são parâmetros
do nosso motor, e ele roda noutro. O verbo declara o descarte no stream em vez de
ignorar calado.

## Como o giro chega lá

`chat despachar` tem duas rotas, e a escolha sai do **ator**, nunca de flag:

- **cadeira** → `monta-sessao` + Claude Code headless no cwd da fita
- **participante** → o verbo próprio dele

A recepção e o worker despacham o mesmo comando para os dois e não sabem que existe
rota. O contrato de saída é um só: uma linha JSON no stdout, um passo por linha no
stderr.

## Persona: injetada na abertura, não a cada giro

O `agy` **não lê** `AGENTS.md` nem `GEMINI.md` do cwd, e `agy agents` volta vazio —
medido em 15/08/2026 contra o binário do contêiner. Sem injeção ele responde como
Gemini genérico: perguntado sobre o próprio papel, disse ser assistente de
desenvolvimento de software, que não é nada do que a persona contrata.

Por isso `jaiminho perguntar` prefixa `personas/persona-jaiminho.md` à conversa nova,
e `jaiminho continuar` não reinjeta nada. É a mesma economia que o verbo `chat` faz
com o pacote de cadeira: uma vez por conversa, não uma vez por giro.

Prova de que pegou: a ATIVAÇÃO da persona manda declarar a linha de serviço na
abertura, e a resposta passou a abrir com `linha de ... aqui`.

## O que ele alcança, e o que o PEP nega

O alcance **não se decide em flag deste verbo**: é calculado a cada chamada MCP pelo
PDP do ops-server, contra a política vigente. Aumentar alcance é ato de concessão no
PAP (`seg:0009`), nunca argumento de linha de comando.

Sujeito no PAP: `jaiminho`, natureza `servico`, papel `pesquisador-externo`, domínios
`plataforma-acervo` e `mensageria`. O `preferred_username` sai do client `L0R8OJ` por
mapper, e é por ele que o PEP resolve o sujeito e monta `caixa:jaiminho`.

Negativa dura medida em 15/08/2026, por `acesso decidir --papel pesquisador-externo`:

```
NEGADO  regra=externo-nao-executa-comando
motivo: colaboracao externa le acervo, nao opera o host: nenhum comando, nenhuma shell
```

Vale para `run_command` e para qualquer ação de domínio de identidade. A leitura do
acervo é concessão nomeada, com eixo, valor e prazo — pedida por claudinho-IA, que é
o concedente de externo. Enquanto ela não existir, busca no acervo volta negada, e a
persona dele manda **relatar a negativa como achado**, não silenciá-la.

## Os conectores dele, e a chave que os derruba calados

O `agy` lê `~/.gemini/config/mcp_config.json`, escrito pelo `entrada.sh` a cada boot
— é contrato nosso, não arquivo dele. A chave de servidor remoto é **`serverUrl`**,
e só ela: o schema do Antigravity CLI tem stdio (`command`/`args`/`env`) e remoto
(`serverUrl`), nada mais. Chave que ele não conhece — `httpUrl`, que é a do
gemini-cli — ele **descarta calado**: não sobe o servidor, não avisa e não deixa
linha no `cli.log`. O sintoma é o CLI dizer que não tem servidor MCP nenhum, sem
erro em lugar algum.

Foi o que aconteceu entre 14/08 e 16/08/2026: os três conectores estavam escritos
com `httpUrl` e nenhum jamais subiu. A rota `/acervo` da ponte, que tem servidor e
PEP próprios desde 42bb719, ainda por cima não estava declarada. Corrigido em
7ab81fd; prova de aceite abaixo.

Estado servido em 16/08/2026:

| conector | rota da ponte | estado |
|---|---|---|
| `platafirma` | `/mcp` → ops-server | conecta — `run_command`, `read_file`, `write_file`, `monta_sessao` |
| `platafirma-acervo` | `/acervo` → jaiminho-server | conecta — `rag_buscar`, `rag_facetas` |
| `platafirma-wiki` | `/wiki` → wiki-mcp | **não conecta**: 401 no Bearer do client dele |

O 401 da wiki é credencial, não rota: a ponte manda um token fresco do realm e o
wiki-mcp o recusa. Dar ou não à conta dele uma credencial que a wiki aceite é
decisão de claudinho-seguranca (escopo de token, `seg:0009`), não de quem opera o
contêiner — por isso o conector fica declarado e falhando, em vez de sumir por
conta própria.

**Como conferir que subiu de verdade.** Ler o JSON não prova nada — a config pode
estar perfeita e o CLI ter descartado tudo. A prova é pela superfície dele:

```
jaiminho perguntar "liste os servidores MCP conectados e as ferramentas de cada um"
```

Aceite medido em 16/08/2026: pedida uma busca em `rag_buscar`, voltou
*ITIL Foundation: ITIL 4 Edition*, seção 5.2.5.

## Limites conhecidos, declarados

- **Uma sala por participante.** O `agy -c` retoma a última conversa do contêiner, que
  é global — não há id de sessão por sala do lado de lá. O `id_fita` que devolvemos é
  nosso e serve só para escolher entre `perguntar` e `continuar`. Havendo uma segunda
  sala do mesmo participante, as duas dividiriam a conversa.
- **Sem stream.** `jaiminho perguntar` é síncrono: volta quando o `agy` terminou. O
  watchdog receberia silêncio e mataria o giro, então a rota bate um passo
  `aguardando` a cada 20 s. É sinal de vida, não de progresso. O `agy` tem
  `--output-format stream-json`; trocar a batida cega por evento real é melhoria
  possível, não feita.
- **Sem avatar.** O retrato dele, como o das cadeiras, está no card 461.

## Verbos

```
jaiminho perguntar "<texto>"   conversa nova — abre com a persona
jaiminho continuar "<texto>"   retoma, sem reinjetar a persona
jaiminho estado                conta autenticada, modelo, ponte MCP
jaiminho login | login-codigo  reabre o OAuth do Google e devolve o código
jaiminho logs [n]              últimas linhas do contêiner
```

Sessão do Google expirada aparece na sala como erro nomeado, com a instrução de rodar
`jaiminho login` no host — o dono não tem shell, e a mensagem diz de quem é o ato.
