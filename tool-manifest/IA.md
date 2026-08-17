# tool_manifest — claudinho-IA (harness)

Índice de abertura da cadeira. Uma linha por ato: **o que existe**, não a flag.
Recorte: a engenharia ao redor do modelo.

- Operacional comum a toda cadeira: `tool-manifest/nucleo.md`.
- Contrato, armadilha, versão e prova de cada item: `tool-manifest/IA-detalhe.md`,
  por ato. É lá que moram ambiente, modelos servidos, CUDA e as pendências.

> **Regra de ouro:** se existe tool pro que vou fazer, chamo a tool. Responder de
> memória o que `rag_search` recupera, navegar na mão o que `query_cargo` filtra,
> ou refazer o que uma tool já faz — é o erro que este manifesto existe pra cortar.

## Sempre — abertura e canônico

```
monta_sessao <cadeira>        abertura; pacote servido com sha, tokens e frescor
platafirma_index              mapa de entrada; UMA vez, quando o assunto e a firma
get_page|search_pages|edit_page|list_pages    wiki (edit_page substitui a pagina INTEIRA)
query_cargo                   faceta declarada; predicado, nao varredura de prosa
repo_tree|repo_read|repo_grep|repo_sync       ler codigo no SHA citavel
run_command · read_file · write_file          bancada sob ~/AI (uid 1001)
web_search · web_fetch        o que mudou desde jan/2026
```

## chapéu `harness` — janela, instrução, prova

```
tokenizador do harness        conta de token pre-voo; qwen2.5.json (tiktoken NAO serve)
conferir sessao|peca|verbo    o servido contra o registrado
ranx                          Recall@k, nDCG, MAP, MRR + significancia entre runs
nvitop                        VRAM e processo ao vivo, durante bench
registro/pecas/*.json         catalogo de peca; teto, volatilidade, dono
```

## chapéu `contexto` — recuperação e memória

```
rag_facets                    populacao por faceta; SEMPRE antes de filtrar
rag_search                    acervo bibliografico; lista de perguntas quando ha lados
acervo escada                 UNICA fonte de numero do acervo + contrato do indice
motor rag buscar|medir|ajuste tunar com baseline antes e depois
```

## chapéu `agente` — alcance e mediação

```
acesso listar|conceder|revogar|decidir|politica|orfaos     --tipo acervo para RAG
fila status|ler|enviar        caixa da cadeira e o canal do agente externo
Ollama 127.0.0.1:11434        serving local (OpenAI-compat em /v1)
minuta ler|escrever|circular|formalizar    so por ping ou ordem; nunca leitura automatica
```

## Quatro armadilhas de FERRAMENTA desta cadeira

Erro de julgamento da matéria mora no chapéu, não aqui. Aqui: a chamada mente,
trunca ou falha calada.

- **`rag_search` com faceta válida e despovoada devolve zero sem erro** — `rag_facets`
  antes, sempre.
- **Sem `rerank`, o `sinal` é só distância vetorial** — régua mais fraca, piso outro:
  duas chamadas na mesma sessão podem sair com réguas distintas.
- **Espelho de repo serve o SHA velho depois do push** — `repo_sync`, ou ler o clone
  local por `run_command`.
- **`docker` não herda o socket** — `export DOCKER_HOST=unix:///run/user/1001/docker.sock`.
