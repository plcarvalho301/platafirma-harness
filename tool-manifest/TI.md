# tool-manifest — claudinho-TI

Substitui: ~/AI/tool_manifest.md (03/08/2026)

Linux Mint 22.3, uid 1001 `claudinho`, **sem sudo** — pacote de sistema se pede ao dono,
em duas linhas (`apt update`, `apt install`, nunca com `&&`). `~/AI/bin` e `~/.local/bin`
já no PATH; `cwd` default `~/AI`; segredos não descem. Opção de verbo sai dele **sem
argumento**. O comum a toda cadeira: `tool-manifest/nucleo.md`.

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
Jaiminho     jaiminho perguntar|continuar|estado|logs — externo em contêiner próprio,
             alcance decidido pelo PEP e nunca por flag do verbo
acervo       acervo ingerir <raiz> [--planilha x.ods] [--apply]; a fila é
             platafirma-conhecimento/rag/scripts/acervo-drop, fora do PATH
inferência   curl 127.0.0.1:11434/... · nvitop · nvcc (CUDA 13.2)
```

Ferramental de segurança: catálogo em `tool-manifest/seguranca.md`, não se duplica aqui.
Usar, sim; decidir, não. `~/AI/.venv` e `~/AI/.venv-harness` são de outras cadeiras: ler,
não escrever.

## Armadilhas de ferramenta — medidas

- **`infra compose` não existe**: promover é `deploy <stack>`, stack obrigatória de
  `registro/stacks.json`, sem default nem "todas"; `down` em stack crítica pede `PF_SIM=1`.
- **Restart do ops-mcp mata a chamada em curso**: `infra restart ops-mcp` despacha
  destacado; `systemctl --user restart` direto, não.
- **Unit alterada no disco exige `daemon-reload` ANTES do restart** — `infra restart` não
  recarrega. Em 10/08 rodou a versão em memória com `WorkingDirectory` morto: `200/CHDIR`,
  105 tentativas, conector fora para todas as cadeiras. `reset-failed` antes do restart bom.
- **`systemctl --user enable` nega unit servida por symlink** — `ln -sfn <unit>
  <target>.wants/<nome>` e `daemon-reload`.
- **`~/.config/systemd/user/ops-mcp.service` é root-owned**: mudar no código, não na unit.
- **Acima de 2 minutos no `run_command`** morre no timeout e leva o process group junto —
  é `longjob`.
- **Push é `git push origin main`, nunca `origin HEAD`**: `HEAD` segue o branch do clone, e
  clone parado em branch de fábrica já mandou entrega para branch que ninguém consome.
