# caderno — produtos (dados)

## Corpus multilíngue: ingerir no ORIGINAL, wiring cross-lingual (decisão 30/08)

Vem literatura em chinês (e possivelmente árabe/alemão/turco). Decisão de arquitetura
de acervo — NÃO traduzir na ingestão:

- **Original + embedding cross-lingual, nunca traduzir-na-ingestão.** Tradução no
  trecho indexado é lossy e IRREVERSÍVEL: congela uma interpretação, colapsa termo
  técnico/ambiguidade/nome próprio. O trecho vira a tradução, não a obra. Trocar
  embedder depois NÃO recupera o que a tradução destruiu — esse é o lock-in real.
- **O embedder atual já é cross-lingual, então o wiring é grátis.** `EMBED_MODEL=
  Qwen/Qwen3-Embedding-0.6B` (medido no container 30/08), multilíngue 100+ línguas:
  query PT casa trecho ZH no mesmo espaço vetorial, sem tradutor no meio. `bge-m3` (a
  outra janela mapeada) também é multilíngue. Reavaliação de ferramental (pós-rerefactor)
  fica livre: os candidatos já estão em território cross-lingual.
- **Original é re-embeddável; a troca de embedder é `re-embed --all`.** cache-key
  carrega `model|backend|device`; aposentar-e-criar já previsto. Guardar original =
  reavaliar embedder sem perder nada.
- **Tradução só na BORDA, nunca no acervo:** query-side (traduz a query, 1 frase, se o
  embedder for fraco cross-lingual) e answer-side (trecho ZH vira PT na vitrine, exibição).
  A fonte no índice fica original.

🟠 ARMADILHA que morde CJK/árabe — `CHUNK_CHARS_PER_TOKEN = 4` é PROXY, e o próprio
comentário admite "medir com o tokenizer do embedder derruba isto". Chinês tem ~1-2
char/token, não 4: o proxy superestima brutalmente o token count em ZH → orçamento de
fronteiras `ceil(tokens/400)` corta fronteira errada SÓ nesses idiomas. Antes de
ingerir a 1ª obra ZH/AR, o chunking tem de medir token real via tokenizer do embedder
montado (robusto à troca: "usar o tokenizer de quem estiver no ar", não assumir Qwen).
Latinos (alemão, turco) sofrem pouco; CJK e árabe sofrem muito. NÃO é tarefa de agora
— entra quando o 1º lote alienígena for pra ingestão, depois do rerefactor em PT (#48/#49).
Teto invariante de 4k cabe na janela dos dois embedders (Qwen3=32k, bge-m3=8k): a troca
não quebra o rerefactor.

## Onde os vetores moram (morada nova)

Dois bancos, e confundi-los custa um diagnóstico errado:

- **`rag-extractor-pg`** (porta 5432) — schema `acervo`: obra, impressao, trecho,
  conceito. **Não tem coluna de embedding.** `public.documents` e `public.chunks` não
  existem mais (dropadas em 11/08/2026).
- **`motor-pg`** (porta 5433) — schema `motor`: `indice` (impressao_id, obra_id,
  metodo, estado, criado_em) e `vetor` (indice_id, alvo_id, embedding, dimensao),
  particionada em `vetor_d1024` / `vetor_d256`.

`acervo escada` cruza os dois: mede `n_texto` no acervo e `n_emb` no motor, por
`impressao_id`.

## Nada é apagado: o mecanismo é aposentar-e-criar

`motor.indice.estado` ∈ {servindo, aposentado, em_construcao}. Re-ingestão aposenta o
índice antigo e cria outro; **nenhum DELETE acontece**. Vetor de impressão aposentada
continua no banco, íntegro e inútil.

Consequência para diagnóstico: queda do degrau `d` **nunca** é perda de vetor. É o
denominador subindo. Antes de dizer que algo se perdeu, contar `motor.vetor`.

## MOTOR_DSN — a causa real

O default no código é `postgresql://motor@127.0.0.1:5433/motor`, **sem senha**, e nada
monta o DSN a partir do `.env`: `deploy/motor/.env` declara a chave como
**`MOTOR_PG_PASSWORD`** (não `POSTGRES_PASSWORD`). Daí o `fe_sendauth: no password
supplied`. Não é problema de percent-encode, como o #42/#167 registrava.

Contorno em uma chamada:

```python
# /tmp/mkdsn.py
import urllib.parse
env = {k: v.strip().strip('"').strip("'")
       for k, v in (l.strip().split('=', 1) for l in open('/home/claudinho/AI/deploy/motor/.env')
                    if '=' in l and not l.startswith('#'))}
print("postgresql://motor:%s@127.0.0.1:5433/motor"
      % urllib.parse.quote(env['MOTOR_PG_PASSWORD'], safe=""))
```

`MORADA=nova` continua obrigatório em toda chamada de `rag_extractor.cli`; o default
`velha` aponta para tabela morta (#167).

## Custo medido do embed

Qwen3-Embedding-0.6B, backend torch, device cuda: **~35 trechos/s** com PDFs grandes na
fila, subindo bem acima disso em obras pequenas. 92.189 trechos levaram cerca de 35
minutos. Serve para orçar antes de disparar, e para saber quando o número denuncia
escopo errado: se a fila do `embed` é muito maior que os trechos do lote, o `ingest`
pegou obra alheia.

## A escada mede por obra; a unidade servível é a impressão

`acervo escada` conta degraus por OBRA, mas o motor serve por IMPRESSÃO, e uma obra
pode ter várias impressões `servindo` ao mesmo tempo — o aposentar-e-criar só aposenta
dentro da mesma impressão, nunca entre impressões distintas da mesma obra. Medido em
26/08: 758 de 763 obras com mais de uma impressão servindo (até 6).

Consequência para diagnóstico: degrau `d` baixo (ex.: d=4) é quase sempre
MULTIPLICIDADE, não buraco de embed. A escada soma impressões por obra; o buraco real
se mede POR IMPRESSÃO (n_emb vs n_texto), e costuma ser uma fração do que a escada
sugere — em 26/08, ~134 impressões (9 zero + 125 parciais) contra o "d=4" por obra.
Antes de orçar repassagem de embed, reconciliar impressões (uma servindo por obra e
método) para o escopo não sair inflado. Obra servível = exatamente uma impressão
servindo por método.

## Medir a busca servida: o runner que funciona (fita 27/08)

O caminho servido mede-se pelo próprio `/search`, de DENTRO do container (o host não
alcança o motor):

```
docker exec -w /app -e PYTHONPATH=/app rag-extractor-api python /tmp/<script>.py
# API: localhost:8000, token em $RAG_API_TOKEN do container; docker cp p/ levar script+gabarito
```

Scripts prontos (baseline 27/08 do #2882): `~/AI/var/tmp/x2882_m1_compreensao.py`
(casar/veredito/expandir offline), `x2882_m2d_direto.py` (recall do declarado, 419 conceitos),
`x2882_m23_recuperacao.py` (T4 travessia, expansao on/off). Gabarito canônico:
`platafirma-harness/avaliacao/gabarito.jsonl` + `estrato-expansao.jsonl` — o estrato é GERADO
do acervo (`gerar-estrato-expansao.py`): regenerar a cada mudança de corpus antes de comparar.

Três fatos medidos que valem régua (detalhe nos cards #2886-2888 e na wiki
`IA/recuperacao-e-busca/tuning-de-recuperacao`):

- **Braço de peso < 1.0 no RRF é cosmético**: candidato exclusivo dele entra ~26º com w=0.7;
  teste on/off antes de acreditar em braço novo.
- **obra_trata_de não participa da busca**: recall do declarado ~0.31, 50% zero no top-8.
- **RERANK_BLEND=0 no env do container**: `rerank=true` per-request paga o CE e não reordena.

## Seções-hub contaminam `secao_prior_passagem_chave` (medido 02/09/2026)

Seção curta e genérica ("Further reading", "9 Vigência", "15 Conformidade") vira passagem-chave
de 70–138 conceitos ao mesmo tempo: o vetor dela é próximo de tudo. Qualquer leitura de
vizinhança entre conceitos por passagem comum tem de excluir seção com mais de ~3 conceitos —
sem o filtro, `conhecimento-arquitetural ~ aprendizado-por-reforco` aparece com 10 seções em
comum. Mesmo mecanismo produz falso vizinho por homonímia (contexto-delimitado ~ janela-de-contexto).

## Ajuste de rede na busca só chega ao contêiner pelo compose (03/09/2026)

`ajustes_do_trilho` lê `VEREDITO_POR_CONCEITO`, `VIZINHANCA_DIRIGIDA` e afins do ambiente do
processo — e o rag-api recebe ambiente por lista EXPLÍCITA no `docker-compose.yml`, não por
`env_file`. Variável escrita no `rag/.env` sem a linha `NOME: ${NOME:-0}` no compose não existe
para o motor: `docker exec rag-extractor-api env` é a prova, antes de concluir que o código não
liga. O bloco lateral (`ontologia.vizinhanca`) é o caso vivido: nasceu desligado com os três
(1970020), foi ligado em 03/09 assim.

## Separação de corpus é `motor.indice`, não tabela, schema nem container (08/09/2026)

Medido em `deploy/motor@0f635ef`, o sha que motor-pg serve. Vale toda vez que alguém
quiser "um índice vetorial separado" para um corpus novo (foi a pergunta de TI sobre
`acervo.casa`, #3018/#3019):

- **Corpus separado = uma linha em `motor.indice`** (impressao_id, metodo,
  metodo_digest, dimensao, estado). A busca por `indice_id` já não cruza corpora. Não
  precisa de tabela de vetor nova, schema novo nem container novo.
- **`motor.vetor` particiona por LIST(`dimensao`)**, não por corpus: `vetor_d1024`
  (texto) e `vetor_d256` (faceta), HNSW próprio em cada
  (`003_particionar_vetor.sql:41-44,83-86`). Família nova de dimensão entra ali; sem
  partição declarada, a escrita levanta erro em vez de sumir.
- **Texto e vetor já vivem em containers distintos**: texto no schema `acervo`
  (rag-extractor-pg), vetor no motor-pg, ligados por `motor.vetor.alvo_id` —
  "referência lógica ao acervo, sem FK" (`002_tabelas.sql:27`). Tabela de acervo com
  coluna `embedding` é peça que não existe na casa; propor uma quebra o gatilho
  `motor.confere_dimensao`, a escada (que cruza acervo × motor por impressao_id) e o
  aposentar-e-criar por `estado`.

🟠 **"Partição" tem três referentes e isso já causou pergunta errada.** Em `acervo
escada` é o STORE de origem (blob-minio × wiki); em `motor.vetor` é a FAMÍLIA DE
DIMENSÃO; na spec_acervo-casa §4 é o CORPUS. Termo canônico proposto para corpus
separado: ÍNDICE. "Partição" fica com o que o Postgres particiona.

⚪ **Hipótese aberta — diluição de recall no HNSW compartilhado.** Corpora de mesma
dimensão dividem o mesmo grafo (`vetor_d1024_hnsw`), e a separação por `indice_id` é
filtro DEPOIS da travessia. Corpus minoritário dentro de ~123k vetores de texto pode
voltar top-k quase todo do majoritário — falha que aparece como resposta pobre, não
como lentidão. O que confirmaria: `motor rag medir` com gabarito do corpus pequeno,
contra o mesmo conjunto num índice isolado. Saída barata se confirmar: família própria
de dimensão (HNSW próprio, mesmo container, mesmo modelo) antes de cogitar container.

## Embedder é ferramental compartilhado — divergir é decisão de ferramental (08/09/2026)

A pergunta "corpus X pode ter modelo próprio, já que nunca busca junto com Y?" tem
resposta NÃO por razão operacional, não semântica. Recuperação separada torna a busca
federada irrelevante, e migração de conteúdo entre corpora distintos quase nunca é caso
real — os dois argumentos usuais caem. O que sobra e decide: um modelo no ar, um
cache-key `model|backend|device`, um `re-embed --all`. Dois modelos dobram VRAM,
pipeline de ingestão, escada e chunking (dois tokenizers, dois orçamentos de fronteira).

A porta de saída fica declarada e barata: `motor.indice.metodo`/`metodo_digest` já
registram o método POR ÍNDICE. Divergir depois é declarar outro método e criar a
partição de dimensão — uma linha, não migração de schema. Por isso se crava igual agora
sem fechar a porta.
