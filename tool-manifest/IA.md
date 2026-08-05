# tool_manifest — claudinho-IA (harness)

Ambiente: Linux Mint 22.3 (base Ubuntu 24.04), usuário `claudinho` (uid 1001).
Sudo não direto — só via Pedro (janela presencial). Binários próprios em `~/AI/bin`
(já no PATH das sessões `run_command`); ferramentas Python isoladas via `uv`/`uv tool`.

Verificado em 2026-08-03 e 2026-08-04 executando cada item. Cada linha declara **como**:
`[exec]` binário executado · `[func]` importado e testado em uso real · `[inst]`
presente, sem prova de funcionamento.

Espelha o padrão do manifesto da claudinha-osint. O recorte é outro: aqui é
**harness** — a engenharia ao redor do modelo (contexto, tools, controle de loop,
avaliação). Organizado pelas três gerências: inferência, RAG/memória, agente.

> **Regra de ouro:** se existe tool pro que vou fazer, chamo a tool. Responder de
> memória o que `rag_search` recupera, navegar na mão o que `query_cargo` filtra,
> ou refazer o que uma tool já faz — é o erro que este manifesto existe pra cortar.

---

## Conectores — o que já tenho; chamar antes de fazer na mão

**platafirma-ops** (`ops.platafirma.org`) — minha caixa (uid 1001).
- `run_command` — shell como claudinho: git, docker rootless, `uv`, `systemctl --user`,
  tocar o Ollama (`127.0.0.1:11434`), ler estado do host.
- `read_file` / `write_file` — arquivos sob `~/AI`.
- `monta_sessao` — `[func]`. Contexto de abertura de qualquer cadeira numa chamada:
  persona canônica, tool-manifest que ELA declara, org canônico e estado da fila.
  Substitui as 4–6 leituras encadeadas da abertura de sessão — chamar em vez de
  encadear `read_file`. Nome canônico e caminho do manifesto saem do texto da persona
  (linha 1 e linha `FERRAMENTAL:`), nunca do nome do arquivo. Fila vem só em envelope;
  o corpo sai por `read_file`. Não traz acervo: faceta e população são ponteiro
  (`rag_facets`), nunca valor. Caixa fechada por arquivo-porteiro devolve o texto do
  porteiro, que é onde está o roteamento alternativo. Fallback de máquina:
  `~/AI/platafirma-harness/bin/monta-sessao <cadeira>`.

**PlataFirma Wiki** (`mcp.platafirma.org`) — conhecimento canônico + acervo + repos.
- `platafirma_index` — mapa de entrada; chamar UMA vez quando o assunto é a PlataFirma.
- `rag_search` — busca semântica no **acervo bibliográfico** (PDFs de terceiros). Usar
  antes de afirmar "o que a obra X diz" — nunca de memória.
- `rag_facets` — valores de filtro válidos do acervo; conferir antes de filtrar `rag_search`.
- `search_pages` / `get_page` / `list_pages` / `edit_page` — prosa e edição da wiki.
- `query_cargo` — facetas declaradas (tabelas `Referencias`/`Conceitos`); predicado
  determinístico, usar em vez de varrer prosa.
- `repo_tree` / `repo_read` / `repo_grep` / `repo_sync` — ler código dos repos (espelho
  read-only). `repo_grep` é o `git grep` do lado do repo.

**web_search / web_fetch** — estado atual do mundo (versões, releases, docs). Meu corte
é jan/2026; pra qualquer coisa que mudou desde então, buscar antes de afirmar.

**Ollama** (via `ops:run_command` → `127.0.0.1:11434`) — serving local, embed/completion.

Fronteira: tenho também o conector `modulo-osint` (ambiente da claudinha-osint) e os
conectores Google/Figma/Canva — fora do uso frequente do harness; não detalho aqui.

---

## 0. Base do ambiente — [exec]

| | o que | nota |
|---|---|---|
| GPU | RTX 5060 Ti 16 GB (Blackwell, sm_120) | driver 595.84; teto de runtime CUDA **13.2** |
| CPU / RAM | 12 threads / 30 GB | — |
| disco | 1,5 TB livres em `/` | — |
| Python | 3.12.3 | venvs geridos por `uv`, **sem `pip` shim** — usar `uv pip` |
| `uv` | 0.12.1 | instalador/gestor de venv e `uv tool` |
| `node` / `npm` | 24.18.1 / 11.16 | tooling JS (`npx`) |
| Docker | rootless, uid 1001 | `export DOCKER_HOST=unix:///run/user/1001/docker.sock` |
| build | gcc/g++/make/cmake/pkg-config + python3.12-dev | wheels binários dispensam libs `-dev` |

## 1. Inferência local — gerência: infra de inferência

**Ollama** — serving local, endpoint `127.0.0.1:11434` (OpenAI-compat em `/v1`).

| modelo | capability | uso | verif. |
|---|---|---|---|
| `bge-m3:latest` | embedding (1024-d) | disponível via Ollama; sem uso corrente no harness | `[inst]` |
| `qwen2.5:14b` | completion + tools | gerador / loop agêntico local | `[inst]` |
| `gemma2:27b-instruct-q4_1` | completion | gerador maior | `[inst]` |
| `qwen:latest` (4B) | completion | leve | `[inst]` |

**CUDA toolkit 13.2** — `[exec]`. `nvcc` em `/usr/local/cuda` (symlink → alternatives),
exposto em `~/AI/bin/nvcc`. `CUDA_HOME=/usr/local/cuda`.

- Pacote `cuda-toolkit-13-2` (versionado, **não** o metapackage `cuda`/`cuda-drivers`):
  toolkit-only, não toca o driver.
- Pin em **13.2** casa com o teto de runtime do driver 595 (`nvidia-smi` → CUDA 13.2).
  Toolkit 13.3 compila mas o binário não sobe neste driver. Ao subir o driver
  (595 → 610+), libera pinar 13.3.
- Prova: kernel `-arch=sm_120` compilado e **executado** na 5060 Ti, `compute_capability=12.0`,
  resultado correto.
- Serve: compilar extensão CUDA (fine-tune / quant local; kernel custom, flash-attn ou
  llama.cpp-CUDA from source). Para **rodar** GPU, torch/sentence-transformers trazem
  runtime próprio no wheel — o toolkit é só pra compilar.

**`nvitop` 1.7.1** — `[exec]`. Monitor de GPU/VRAM ao vivo (NVML), process-level. CLI
global via `uv tool` (`~/.local/bin/nvitop`, `nvisel`). Orçamento de VRAM durante
indexação/bench. TUI exige TTY; a API `from nvitop import Device` serve leitura
programática (não instrumentada ainda).

## 2. RAG e avaliação — gerência: RAG e memória

Ferramentas de eval moram no **venv de harness** `~/AI/.venv-harness`. O venv do rag
(`rag/.venv`) é do megafone/container — não escrevível pelo claudinho. Eval desacoplado:
consome o endpoint do rag, não vive dentro dele.

**`ranx`** — `[func]`. Métricas de IR sobre qrels+runs: Recall@k, nDCG, MAP, MRR e
**teste de significância entre runs**. Testado contra TREC-Eval (upstream). Fecha a
lacuna de Recall@k real do rag. Prova: `ndcg@3=0.9197`, `recall@3=1.0` em par
qrels/run mínimo. Warnings de Numba/LaTeX no import são cosméticos.

**`tokenizers` 0.23.1** — `[func]`. Contagem de token pré-voo pra política de contexto.
Tokenizer do qwen2.5 em `~/AI/opt/tokenizers/qwen2.5.json` (7 MB). Prova: frase-teste →
13 tokens. `tiktoken` não serve (tokeniza qwen errado). Para gemma2, baixar o
`tokenizer.json` correspondente sob demanda.

**Embedder e revisor do RAG** — vivem no `rag/.venv` do próprio repo `platafirma-conhecimento`,
não no Ollama e não neste manifesto por padrão; registrados aqui porque medidos por mim
diretamente em 04/08/2026.

- **`Qwen/Qwen3-Embedding-0.6B`** — `[func]`. Embedder de indexação e query do RAG, torch/GPU.
  Carimbado em `public.index_meta` (`embed_backend=torch`). 1024-d — mesma dimensão do
  `bge-m3`, o que torna conferência por dimensão insuficiente pra distinguir os dois.
- **`BAAI/bge-reranker-v2-m3`** — `[func]`. Cross-encoder do gate de abstenção (`cobertura`).
  VRAM residente ~1,1 GiB fp16. AUC 0,873 contra 0,782 do sinal por similaridade, medido sobre
  47 perguntas cobertas × 36 não cobertas. Custo: busca sobe de ~250 ms pra ~1.100 ms de
  mediana com pool de 40 candidatos — otimização de latência é o item 1 do card
  `tarefas.platafirma.org/tasks/299`.

**`acervo-status`** — `[exec]`. Monitor do acervo: estado corrente por **obra** nos cinco
degraus do fluxo — catalogada, armazenada, ingerida (chunkada), embedded (vetor de texto),
vetorizada (vetor de metadado) — e a **fuga por degrau**: quantas obras vazam entre dois
degraus e por qual causa. Binário próprio em `~/AI/bin/acervo-status` (formatador em
`_acervo-status-fmt.py`); `--json` para máquina, `--detalhe` nomeia quem está fora do lugar.

- Lê o substrato, não o discurso: `armazenada` confere objeto a objeto no MinIO (`mc ls`
  nos buckets `acervo` e `pessoal`) em vez de acreditar em `acervo.obra.objeto`. Foi assim
  que apareceu obra catalogada com 189 chunks vivos e bruto inexistente.
- Read-only e fora do repo do rag: temp table, nenhuma view criada, nenhuma escrita. Roda
  a qualquer tempo, inclusive durante carga.
- Imprime o contrato do índice (`index_meta`) no cabeçalho — número de vetor sem o par
  (modelo, backend) que o gerou não quer dizer nada.
- **Chamar antes de afirmar qualquer número do acervo.** Contagem de obra dita de memória
  ou de mensagem de outra persona é exatamente o que este binário existe para aposentar.

---

## Pendências declaradas

- **`deepeval`** — fase 2 (fidelidade de síntese via juiz + eval de tool-use de agente).
  Entra quando a checagem estrutural de citação (determinística) estiver feita. Não instalado.
- **`llama-benchy`** — bench de inferência estilo llama-bench contra o endpoint Ollama,
  via `uvx` (sob demanda, não instala). Não executado ainda.
