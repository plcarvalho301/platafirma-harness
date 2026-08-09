# tool-manifest — claudinho-seguranca

Ambiente: host único, Linux Mint 22.3 (base Ubuntu 24.04), usuário `claudinho`
sem sudo geral. Docker rootless em `/run/user/1001/docker.sock`. Tudo em
user-space sob `~/AI`.

Verificação: cada linha declara **como** — `[exec]` binário executado ·
`[func]` importado e usado em trabalho real · `[inst]` presente, sem prova de
funcionamento. `[inst]` é confissão, não aval.

> **Regra de ouro:** existindo tool para o que vou fazer, chamo a tool.
> Responder de memória o que uma busca recupera, ou navegar na mão o que um
> filtro resolve, é o erro que este manifesto existe para cortar.

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/GERAL.md`.

## Conectores

**platafirma-ops** (`ops.platafirma.org/mcp`) — shell como `claudinho` no host.
- `run_command` — toda operação de estado no host. Grava auditoria em
  `~/AI/var/log/ops/`, não silenciável pelo chamador.
- `monta_sessao` (ops) — contexto de abertura da cadeira numa chamada: persona
  canônica, este manifesto, org canônico e estado da fila. Chamar em vez de
  encadear leitura. Sob demanda, não gate de entrada.

**PlataFirma Wiki** (`mcp.platafirma.org/mcp`) — acervo, wiki e espelho dos repos.
- `rag_search` — critério normativo antes de responder de memória: texto de
  norma, identificador de controle, parâmetro criptográfico. Citando cláusula ou
  código, o código exato entra na pergunta.
- `query_cargo` — faceta declarada do acervo. Predicado determinístico; não
  serve para assunto em prosa livre.
- `get_page` antes de `edit_page` — sempre. `edit_page` substitui a página
  inteira e sobrescreve em silêncio.
- `repo_read` / `repo_grep` — leitura de repo. Escrita é `run_command`.

## Verbo próprio — `seg`

Origem única: `platafirma-core/deploy/seguranca/seg`, alcançado por symlink em
`~/AI/bin/seg`. Capacidade por subcomando; o binário agrupa por toolkit
(`arq:0040`), não por capacidade.

| subcomando | quando chamar | capacidade | verif. |
|---|---|---|---|
| `seg oscap avaliar <perfil>` | medir o casco contra o datastream derivado | `politica` | `[exec]` |
| `seg oscap falhas <log>` | ler as regras que falharam numa avaliação | `politica` | `[exec]` |
| `seg oscap -- <nativos>` | qualquer ato do OpenSCAP que não seja os dois acima | `politica` | `[exec]` |
| `seg ssg derivar <datastream>` | compilar a régua: remover o CPE de SO | `politica` | `[exec]` |
| `seg keycloak -- <nativos>` | administrar realm, cliente, papel via kcadm.sh | `acesso` | `[inst]` |
| `seg openssl -- <nativos>` | OpenSSL com oqsprovider — ML-KEM, ML-DSA, SLH-DSA | `acesso` | `[exec]` |

**`seg` não é gate.** `oscap`, `openssl` e o contêiner do Keycloak seguem
alcançáveis fora dele; hoje é conveniência e trilha. Vira controle no dia em que
as ferramentas saírem do PATH do usuário e só o despachante as alcançar.

## Ferramenta de terceiro

Fora de `arq:0037` por decisão da mesa: item de configuração no PATH, não verbo
da plataforma. Chamada direta, sem invólucro.

```
age · age-keygen · cosign · dockle · gitleaks · grype · hurl · jwt · lynis
minisign · oauth2c · opa · osv-scanner · restic · sops · step · syft
testssl.sh · trivy · trufflehog · yq
```

Conferir imagem e artefato servido é `conferir <classe>`, de claudinho-TI — não
é meu, e não entra em `seg`.

## Armadilhas medidas

- **`seg oscap avaliar` sem root não é conformidade.** Regras de `/etc/shadow`,
  `/boot` e sysctl saem incompletas e o sumário parece completo. O verbo declara
  isso na primeira linha da saída; a saída bruta do `oscap` não declara.
- **Sem o datastream derivado toda regra sai `notapplicable`** — o Mint responde
  `ID=linuxmint` e o CPE de SO do Ubuntu descarta tudo. `notapplicable` em massa
  é sintoma de régua ausente, não de sistema limpo.
- **Filtro de subdomínio no RAG nega obra sem subdomínio.** `NULL = ANY(...)`
  não casa em SQL: obra sem subdomínio é invisível em qualquer filtro de
  subdomínio, sem erro. Verificação de ausência no acervo exige busca sem filtro.
- **`edit_page` da wiki substitui a página inteira**, sem aviso e sem merge.

## Pendências declaradas

- **Gate de acesso ao toolkit.** Enquanto as ferramentas ficarem no PATH, `seg`
  não controla nada. Falta decidir se saem, e o que quebra quando saírem.
- **`seg keycloak` está `[inst]`**: o invólucro roda, mas não executei ato de
  administração real por ele desde a consolidação.
- **`conferir casco` de claudinho-TI ainda não existe.** Quando existir, o
  insumo dele é o derivado que `seg ssg derivar` produz — falta o contrato de
  onde ele é lido e o que acontece quando está velho.
- **Termo não averbado.** `politica` e `politica/seguranca` estão em pedido de
  averbação com claudinho-conhecimento. O nome do verbo não depende do termo;
  a coluna `capacidade` desta tabela depende.
