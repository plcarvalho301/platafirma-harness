# tool-manifest — claudinho-TI

Substitui: ~/AI/tool_manifest.md (03/08/2026)

Índice de abertura. Uma linha por ato: **o que existe**, não como se chama cada flag.

- Opção de um verbo: chamá-lo **sem argumento**.
- Armadilha de ferramenta, contrato e o porquê de cada um: `tool-manifest/TI-detalhe.md`,
  por ato. Armadilha de escopo mora no chapéu da gerência.
- O comum a toda cadeira: `tool-manifest/nucleo.md`.

Linux Mint 22.3, uid 1001 `claudinho`, **sem sudo** — pacote de sistema se pede ao dono.
`~/AI/bin` e `~/.local/bin` já no PATH do subprocesso; `cwd` default `~/AI`; segredos não
descem.

> **Regra de ouro:** havendo verbo para o que vou fazer, chamo o verbo.

## Conectores

- **platafirma-ops** (`ops.platafirma.org`) — `run_command`, `read_file`, `write_file`,
  `monta_sessao`. É a caixa do uid 1001.
- **PlataFirma Wiki** (`mcp.platafirma.org`) — `platafirma_index` uma vez por sessão ·
  `search_pages`/`get_page`/`edit_page`/`query_cargo` · `repo_tree`/`repo_read`/
  `repo_grep`/`repo_sync` · `rag_search`/`rag_facets` só para **critério**; fato da
  PlataFirma nunca sai do RAG.

## Por domínio — ponteiro, não manual

```
carregar chapeu   monta-sessao <cadeira> --chapeus | --chapeu <slug> — camada C, sob
                  demanda; NAO vem na abertura. `conferir chapeu` julga os quatro
                  predicados do TEMPLATE, teto de 2500 tokens medido
promover release  deploy <stack> [up -d|rotas|acessos|segredos] — stack obrigatória
serviço no ar     infra estado|saude|logs|restart|exclusivo|cache|backup · sinal
comando longo     longjob run <nome> <cmd...>
poda de retencao  ops-log-prune (log de ops/jobs, 90d) · quarentena-prune (levas de
                  var/quarentena, 7d) — os dois no cron do claudinho, nao no ops-mcp
Jaiminho          jaiminho perguntar|continuar|estado|logs — externo em contêiner
                  próprio, alcance decidido pelo PEP e nunca por flag do verbo
fábrica no agy    jaiminho-fabrica <mesmos sub-atos> — 2a conta da fábrica (org:0020);
                  mesmo verbo por env, container e client próprios, papel fornecedor
acervo            acervo ingerir <raiz> [--planilha x.ods] [--apply]; a fila é
                  platafirma-conhecimento/rag/scripts/acervo-drop, fora do PATH
inferência        curl 127.0.0.1:11434/... · nvitop · nvcc (CUDA 13.2)
conferência       conferir servico|verbo|skill|repo|peca|sessao|procedencia|superficie|arranque|commit|chapeu
                  superficie [--caso conectores|descricao] mede meio (default) ou servido × catálogo
```

Ferramental de segurança: catálogo em `tool-manifest/seguranca.md`, não se duplica aqui.
Usar, sim; decidir, não. `~/AI/.venv` e `~/AI/.venv-harness` são de outras cadeiras: ler,
não escrever.

Clones de trabalho em `~/AI`: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`. Entrega só existe em git — `git push origin main`, e o branch se confere
antes de relatar.
