# Catálogo de verbos da PlataFirma

Tudo que é executável pelo nome no host da plataforma, agrupado pela capacidade
de negócio que serve (`docs/arquitetura-negocio-operacao.md`, `arq:0037`).

Espelho de leitura humana: `Ajuda:Catálogo de verbos` na wiki.

## Contrato de cabeçalho

Todo verbo da plataforma carrega, nas primeiras linhas do arquivo:

```
# <nome> — <uma linha de propósito, em verbo ativo>
# capacidade: <uma das 13 do mapa>
# dono: <cadeira>
```

Regras verificáveis, na ordem em que `conferir verbo` as aplica:

1. Cabeçalho presente e com as três linhas. Sem cabeçalho, o verbo não entra no
   PATH.
2. Chamada sem argumento imprime o uso e sai com código 2.
3. Ato de mutação exige alvo explícito; ausência de alvo recusa, nunca opera
   sobre tudo.
4. Ausência se declara. Verbo que não olhou um lugar não afirma que ele está
   vazio.
5. Origem única: o arquivo mora no repo dono e chega ao host por symlink. Cópia
   não é forma válida de instalação.

## Verbos da plataforma

| Verbo | Capacidade | Dono | Propósito | Origem |
|---|---|---|---|---|
| `tarefas` | `trabalho` | claudinho-TI | cliente do rastreador de tarefas | harness |
| `fila` | `mensagem` | claudinho-TI (verbo com claudinho-IA) | caixa de mensagens entre personas | harness |
| `monta-sessao` | `expediente` | claudinho-IA | contexto de abertura de uma cadeira, numa volta | harness |
| `acervo-status` | `conhecimento` | claudinho-conhecimento | estado do acervo por obra, nos cinco degraus | harness |
| `acervo-get` | `conhecimento` | claudinho-conhecimento | baixa uma obra do acervo pelo título | só no host |
| `acervo-pacote` | `conhecimento` | claudinho-conhecimento | sem cabeçalho — propósito não declarado | só no host |
| `ragq` | `conhecimento` | claudinho-IA | consulta direta ao rag-api, contrato do `rag_search` | só no host |
| `rag.py` | `conhecimento` | claudinho-IA | sem cabeçalho — e diverge da cópia em repo | divergente |
| `exporta-acervo-xlsx.py` | `conhecimento` | claudinho-conhecimento | sem cabeçalho — propósito não declarado | só no host |
| `infra` | `infra` | claudinho-TI | estado e operação da infra local | harness |
| `longjob` | pendurado | claudinho-TI | dispara trabalho longo como unit transiente | core |
| `conferir-servido` | `verificacao` | claudinho-TI | compara declarado com servido em contêiner | harness |
| `oscap-casco` | `verificacao` | claudinho-seguranca | avaliação CIS via OpenSCAP | cópia |
| `oscap-casco-falhas` | `verificacao` | claudinho-seguranca | lista as regras que falharam num log | cópia |
| `ssg-deriva` | `verificacao` | claudinho-seguranca | regenera o datastream derivado do OpenSCAP | cópia |
| `kcadm` | `acesso` | claudinho-seguranca | `kcadm.sh` do Keycloak, via contêiner | cópia |
| `openssl-pqc` | `acesso` | claudinho-seguranca | openssl com oqsprovider (ML-KEM, ML-DSA, SLH-DSA) | cópia |
| `ops-log-prune` | órfão | claudinho-TI | poda o log de operação por idade; cron diário | só no host |

Legenda de origem: **harness** = symlink para `platafirma-harness/bin`, versionado ·
**core** = symlink para `platafirma-core/deploy/ops` · **cópia** = arquivo duplicado
no host, idêntico ao repo por sorte, não por mecanismo · **só no host** = sem
contraparte em repo nenhum · **divergente** = host e repo diferem.

## Ferramenta de terceiro

Instalada, não construída aqui. Não é espinha da plataforma e não segue o
contrato de cabeçalho.

```
age · age-keygen · cosign · ctop · dive · dockle · fd · gitleaks · grype
hadolint · hurl · jwt · lnav · minisign · nvcc · oauth2c · opa · osv-scanner
restic · rg · sops · step · syft · testssl.sh · trivy · trufflehog · uv · uvx · yq
lynis
```

## Capacidades sem verbo

Do mapa de capacidades, seguem sem instância executável:

- `solicitacao` — pedido do humano ao sistema. Não há superfície pela qual o
  operador humano descubra o que a máquina faz sem perguntar a uma persona.
- `comunicacao` — anúncio por difusão retida. Desenhado em `arq:0036`, sem verbo;
  hoje vaza pela fila.
- `decisao` — sem verbo de lavrar nem de consultar.
- `canal` — design system em git, sem verbo que o distribua aos canais.

## Pendências de origem

Doze dos dezoito verbos não têm origem declarada em repo: cinco existem só no
host, cinco são cópia, um diverge e um mora em repo alheio à espinha. Perdida a
máquina, perdem-se os cinco primeiros.
