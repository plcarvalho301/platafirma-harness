# tool-manifest — claudinho-seguranca

Índice. O comum a toda cadeira é `tool-manifest/nucleo.md`, e não se
repete aqui. Ambiente: host único, `claudinho` sem sudo, Docker rootless, sob `~/AI`.
Tudo abaixo é `[exec]`: executado em trabalho real.

> Existindo tool para o que vou fazer, chamo a tool. Responder de memória o que uma
> busca recupera é o erro que este manifesto corta.

## Conectores

- **platafirma-ops** — `run_command`: operação de estado no host; audita em
  `var/log/ops/`, não silenciável. `monta_sessao`: abertura da cadeira.
- **platafirma-wiki** — `rag_search`: critério normativo antes de responder de
  memória, com o código exato na pergunta. `query_cargo`: faceta declarada.
  `repo_read`/`repo_grep`: leitura — escrita é `run_command`.

## Verbo próprio — `seg`

```
seg oscap avaliar|falhas|-- <nativos>   o casco contra o datastream derivado
seg ssg derivar <datastream>            compilar a régua: remover o CPE de SO
seg keycloak -- <nativos>               realm, cliente e papel, via kcadm.sh
seg openssl -- <nativos>                OpenSSL com oqsprovider (ML-KEM, ML-DSA, SLH-DSA)
```

Sem argumento, lista os próprios sub-atos. Fonte: `platafirma-harness/bin/seg`.
**Não é gate** (card 199): as ferramentas seguem no PATH fora dele.
**`seg keycloak` exige `kcadm.sh config credentials` na sessão** — credencial em
`platafirma-core/.env`, fora do git.

## Ferramenta de terceiro

Item de configuração no PATH, não verbo (fora de `arq:0037`, decisão de mesa).

```
age · age-keygen · cosign · dockle · gitleaks · grype · hurl · jwt · lynis
minisign · oauth2c · opa · osv-scanner · restic · sops · step · syft
testssl.sh · trivy · trufflehog · yq
```

Conferir imagem e artefato servido é `conferir <classe>`, de claudinho-TI.

## Armadilhas de FERRAMENTA

Armadilha de ESCOPO migrou para os chapéus `cripto` e `blueteam` (#189).

- **`seg oscap avaliar` sem root não é conformidade** — `/etc/shadow`, `/boot` e
  sysctl saem incompletos e o sumário parece completo. O verbo declara na 1ª linha
  da saída; o `oscap` cru não.
- **Sem datastream derivado toda regra sai `notapplicable`** — o Mint responde
  `ID=linuxmint` e o CPE de SO do Ubuntu descarta tudo.
- **Filtro de subdomínio no RAG nega obra sem subdomínio** — `NULL = ANY(...)` não
  casa: a obra some de qualquer filtro, sem erro. Ausência se verifica SEM filtro.
- **Chave `no` em `politica.yaml` vira booleano** — YAML 1.1 lê `no` como `false` sem
  erro, e a política passa no `conferir` quebrada. Eixo novo confere a lista
  reservada (`no/yes/on/off/true/false`).

## O que não está aqui

Pendência é estado e envelhece: vive em card (`tarefas listar --cadeira seguranca`),
não neste índice. `minuta` está no núcleo, e nunca é leitura automática.
