# Inventário v1 — acessos privilegiados

**Programa:** #183 (Acessos privilegiados: inventário, cofre, rotação, break-glass) · Onda 3 do #402.
**Medido:** 25/08/2026, read-only (kcadm, getent, leitura de config). Sem valor de segredo — só nome, local, poder, custódia.
**Escopo v1:** contas de SO com poder, realm, credenciais com poder de alteração, operadores do PAP, break-glass. É o primeiro artefato concreto do programa; não fecha o programa.

## 1. Contas de SO com poder
| conta | uid | grupos de poder | user-manager | nota |
|---|---|---|---|---|
| megafone | 1000 | **sudo + docker** | lingering | dono. sudo→root e docker→daemon de SISTEMA. Foi o vetor do vazamento de rebuild 25/08. |
| claudinho | 1001 | dono do daemon rootless da prod | lingering | conta dos serviços; opera via `/run/user/1001/docker.sock`. Sem sudo. |
| jaiminho | 1003 | rootless próprio | lingering | braço agy (migrado #2286). |
| modulo-osint | 1002 | — | lingering | conta de SO órfã (achado do `acesso orfaos`, sem sujeito no PAP). |

## 2. Realm (Keycloak)
- **pedro-admin** — ÚNICO admin (realm master). Senha rotacionada 09/08 por exposição (#200).
- platafirma: **nenhum** usuário com `realm-management` direto — admin só via master/pedro-admin. Sem admins espalhados (bom).
- service accounts vivos: `jaiminho-fabrica` (fornecedor, ~9k calls/dia), `L0R8OJ`/jaiminho (pesquisador-externo). Os 7 por-cadeira foram extintos (#163) — privilégio ocioso zerado no realm.

## 3. Credenciais com poder de alteração
| segredo | onde vive | rotação | custódia |
|---|---|---|---|
| KC_ADMIN_PASSWORD (pedro-admin) | platafirma-core/.env | 09/08/2026 | **KeePass DESATUALIZADO (#200)** |
| KEYCLOAK_CLIENT_SECRET | .env | não declarada | não declarada |
| KC_DB / IDENTIDADE_DB / MDM_RH_DB _PASSWORD | .env | não declarada | não declarada |
| TODOIST_TOKEN | .env | não declarada | não declarada |
| OPS_AUTH_TOKEN (break-glass estático) | EnvironmentFile do unit (não inline) | expira 2026-09-30 (default de CÓDIGO, não declarado no unit) | em uso (74 chamadas via `token-estatico`) |
| Google token | ~/AI/var/google/token.json | — | **permissão 644 — world-readable** |

## 4. PAP — operadores (poder pleno)
- `megafone` (+ chave por sub `b6986be0…`) e `claudinho`. Dois operadores, ambos justificados (dono; conta de serviço / rota estática). Sem operador a mais.

## 5. Break-glass
- Embrião: conta `megafone` (sudo) + token estático `OPS_AUTH_TOKEN`. **Sem rito escrito** (o #183 item 4 pede um). Lacunas: janela de validade só em default de código; sem procedimento de uso com rastro posterior.

## Achados priorizados
1. 🔴 **pedro-admin: custódia KeePass velha (#200).** Break-glass do único admin do realm aponta credencial rotacionada — falha no momento em que existe pra servir. Ação do dono (escrever no KDBX4); sem ferramenta minha pra isso.
2. 🟠 **`token.json` do Google 644 (world-readable).** Qualquer conta do host lê o token OAuth. Correção reversível de uma linha (`chmod 600`), pendente só de confirmar o leitor pra não quebrar a integração.
3. 🟡 **Break-glass sem rito:** expiry só em default de código (2026-09-30); sem procedimento escrito.
4. 🟡 **Rotação não declarada** para segredos de DB, client secret e tokens — sem calendário.
5. 🟢 **Privilégio ocioso:** zerado no realm (#163). Resta a conta de SO órfã `modulo-osint` (1002).

## Próximos entregáveis do programa (não neste card)
- Rito de break-glass escrito (#183 item 4).
- Rotação declarada + calendário (item 3 do #183).
- Cofre com concessão sob demanda e menor tempo (item 2 do #183).
