# Runbook — virada da Onda 2 (#3053, big-bang)

Ordem do dono, 14/09/2026: todos os verbos da Onda 2 num deploy só; quem vira a chave é
a cadeira ia. Este runbook é a sequência inteira, com quem faz cada passo e o que o dono
faz com a própria mão.

## Estado de partida (14/09, 10:40)

- Servido: `platafirma-harness` @ `bb4073a` (no ar desde 13/09 22:39Z; anterior `6590837`).
- Ramo: `fabrica/3053` @ `ca6ab41`, igual a origin (atrás 0, à frente 0); árvore suja só
  `agente/settings.json` (fora do PR).
- Régua Q1 (`release conferir verbo --ref fabrica/3053`) zero em sessao, expediente,
  acesso, persona; suite `testes/` 46 verdes; `test_contrato_monta_sessao` 25;
  `test_contrato_acesso` 27; lint limpo.
- OK da gestão (fila 20260914T103338) e da segurança (fila 20260914T103213).
- O servido de hoje NÃO tem `seg segredo` nem `seg keycloak entrar`: esses atos só
  existem a partir do promover. Logo os pré-requisitos de segurança são pós-promover,
  não pré.

## Quem faz o quê

| passo | quem |
|---|---|
| 1–3 (pré-voo, merge, promover), 5 (smoke), 7 (rollback) | ia (Elias) |
| 4 (keycloak, segredo, PAP), sign-off | seguranca (Leonardo) |
| P1–P4 | dono (Pedro) |

## 1. Pré-voo — bancada, sem efeito no servido

1. `repo atualizar platafirma-harness` — clone igual a `origin/fabrica/3053`.
2. `release conferir verbo sessao|expediente|acesso|seg|persona|mesa --ref fabrica/3053`
   — todos exit 0.
3. `teste rodar platafirma-harness testes` (46) e `controle/tests/test_contrato_monta_sessao.py`
   (25) e `test_contrato_acesso.py` (27) verdes; `lint rodar platafirma-harness` limpo.
4. `ops-server/test_monta_sessao_lote.py` e `test_run_command_lote_injecao.py` no venv da
   porta, `/opt/platafirma/current/venv/ops` (o venv harness da release não tem `mcp`). Se pela porta não rodar, declara-se e segue —
   carta branca da gestão para ajuste de mock.

Gate: qualquer item fora do verde é `PARADA:` — não vira.

## 2. Merge

5. `repo pr-abrir platafirma-harness` (`fabrica/3053` → `main`) e `repo pr-merge`.
   Push direto em main é permitido (ordem do dono, 07/09); o PR fica pelo diff legível.
6. `repo atualizar platafirma-harness` em main; anotar o SHA de main.

## 3. Promover — aqui o servido muda

7. `release promover platafirma-harness <sha de main>` — o gate `conferir verbo` roda
   dentro; recusa = parar aqui, servido intacto.
8. `infra restart ops-mcp` — a porta cai por segundos; chamada em voo numa conversa
   aberta do claude.ai pode falhar uma vez.
9. `publicar-abertura` só se `abertura/` mudou no diff do PR (`repo diff` confere).

## 4. Pré-requisitos de segurança — pós-promover (seguranca)

10. `seg keycloak entrar` — kcadm expirado desde 13/09; confirma client `agy-dono` no realm.
11. `seg segredo importar harness-sessao --de platafirma-harness/sessao/.env`; depois
    `seg segredo ler harness-sessao/SESSAO_PG_PASSWORD` responde ao `bin/sessao`.
    Sem o segredo: `duravel: false` na abertura — declarado, não trava.
12. PAP: tipo `expediente` ainda pende — só afeta chamada direta da tool `expediente`,
    não a projeção de `monta_sessao`.

Premissa a reconferir no 11: `seg segredo ler` recusa quando o pai é a porta
(lê `/proc/$PPID/cmdline`); `bin/sessao` chama `seg` como filho do binário, não da porta.
Se a checagem subir a árvore, `duravel` cai para false — aviso ao Leonardo, que ajusta.

## 5. Smoke — só aqui as hipóteses viram fato

13. ia: `monta_sessao(cadeira="IA", pergunta=…)` — esperado: `sessao` no topo, 7 peças
    (`oficio` e `caderno-head` fora), `sessao_id` cunhado por `sessao abrir`.
14. ia: `sessao ver <id>` mostra `sujeito` (sub do OIDC) e `autorizada_por: <regra>@<plano>`;
    `sessao listar`; `expediente catalogo`.
15. ia: `release conferir verbo sessao|expediente|persona|mesa` no servido — exit 0.
16. dono: P2 (abaixo).

Riscos que só o smoke mostra (gestão, 14/09):
- (a) rota de token estático dá `sub: -` → `sessao abrir` sai 3 → chat e fábrica caem
  na rede do `bin/monta-sessao` velho. Esperado; não bloqueia.
- (b) `motor rag buscar casa` está 503 → `acervo-consultado` sai indisponível declarado.
  Incidente de dados/ti, não desta virada.
- (c) PAP sem tipo `expediente` (passo 12).

## 6. Fechar

17. ia: `tarefas mover 3053 em-homologacao`; seguranca: `tarefas assinar`;
    `entregue` é ato do dono (P4).
18. Débito pós-merge, ia: `bin/monta-sessao` ainda cunha sozinho (`bin/chat` e o
    agregador passam por ele) — Prompt B da fábrica: casca sobre `sessao abrir` +
    `expediente montar`. A rede fica 14 dias; remoção após 28/09 (mesa da gestão).

## 7. Rollback — a qualquer ponto depois do passo 7

- `release reverter platafirma-harness` → volta a `bb4073a`; `infra restart ops-mcp`.
  A porta volta ao `monta-sessao` velho. Sessões abertas no intervalo ficam no ledger;
  nada se apaga.
- O ramo e o merge em main não se desfazem: reverter é do servido, não do git.

## O que o dono faz

- **P1 — antes do passo 7.** Dizer "vira". Até o 6 nada muda no servido; do 7 em diante
  muda.
- **P2 — depois do passo 8.** Abrir UMA conversa NOVA no claude.ai, qualquer cadeira, e
  colar aqui o retorno do `monta_sessao`: `sessao` no topo e `sujeito` preenchido. Tem de
  ser conversa nova — a aberta pode estar com o descritor da tool cacheado.
- **P3 — só se P2 falhar por conexão.** Reautorizar o connector `claudinho-mcp`
  (Settings → Connectors, fluxo OAuth). ⚪ hipótese — o restart da porta pode derrubar a
  sessão OAuth do connector; não medido. Se P2 abrir normal, P3 não existe.
- **P4 — depois do passo 17.** Mover #3053 a `entregue`.
- ⚪ **P5 — condicional.** Se `seg keycloak entrar` pedir credencial de admin do Keycloak
  fora do alcance do Leonardo, ele te pede nessa hora. Confirma-se no passo 10.
