# Procedimento — gold set firmabot

Substitui: platafirma-conhecimento/rag/docs/T0-cabecalho-20260804.md (2026-08-04)

Rode exatamente como está. Não reescreva pergunta nenhuma.

## Execução

1. Instância **sem persona**.
2. Uma chamada `rag_search` por sonda, isolada. Parâmetros congelados:
   `texto="secao"`, `k=8`, **sem** filtro de `dominio`, `subdominio`, `frente` ou `colecao`.
3. Guarde o retorno **inteiro** em JSON, um arquivo por sonda, incluindo o bloco `indice` e o
   `acervo_sha`. Não resuma, não interprete, não comente o resultado.
4. Nome do arquivo: `T0-<NN>-<persona>.json`. Sem persona declarada:
   `T0-<NN>-persona-nao-declarada.json`.
5. Registre o estado de formalização no mesmo instante: existe página na wiki nomeando o
   termo? existe ADR no git? data de criação e da última edição de cada uma. **Ausência é
   dado** — registre como ausência, não omita a linha.

## Alvo esperado

Cravado antes de qualquer execução, saído da curadoria — nunca do retorno da busca.
`sem obra` é alvo legítimo. `ᴱ` marca conceito cujo termo coincide com título de obra:
subgrupo próprio na análise.

## Carimbo

Todo diretório de resultado carrega `carimbo.md` com, no mínimo: id e data de início do
container servido, `acervo_sha`, estado do reranker e do dispositivo do embedder, e — quando
houver gerador — digest do modelo, `num_ctx`, parâmetros de amostragem e o `PROCESSOR`
reportado pelo runtime.

Conferir o **container em execução** (`.State.StartedAt` e `.Image`), não a imagem no disco:
imagem reconstruída não implica container recriado.

## Vieses conhecidos

Nas sondas 6 e 8, dossiês autorais do próprio dono dominaram o retorno em W0. O cálculo
exclui `emitido_por = autoral` ou o reporta em coluna própria: "consolidação induzida por
autoria própria" é variável distinta de "consolidação do campo".

## Pendente

Passo 5 (estado de formalização wiki/ADR) não foi executado na rodada G0-rag-base de
2026-08-06. Scripts em `../rag-medicao/t0_wiki_estado.py` e `../rag-medicao/t0_adr_estado.sh`.
