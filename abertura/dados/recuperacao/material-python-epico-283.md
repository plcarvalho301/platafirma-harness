# material Python — épico #283 (ingestão incremental do acervo)

Orientação expressa para TODAS as sessões do épico #283. Repertório de DADO do eixo
1: onde as coisas moram, qual invocação não mente, o que já foi medido. Vale como
ponto de partida — não relê o caderno inteiro para redescobrir os mesmos quatro fatos
a cada sessão.

FRONTEIRA: o que é dado (morada, unidade, degraus, o que conta como servível) é
desta cadeira. O que é convenção de código Python puro — estilo, tipos, estrutura de
erro no toque do RAG/CLI — é TI/IA; aqui vai marcado `[código: TI/IA]` e não se fixa
sozinho.

## O módulo e o venv — a invocação que não mente

- `rag_extractor` mora em `platafirma-conhecimento/rag/rag_extractor/`, servido pelo
  **`.venv` raiz** de `~/AI`. NÃO está em `.venv-embed` nem `.venv-acervo` (medido
  26/08: `ModuleNotFoundError` nesses dois). A cópia em `deploy/conhecimento/rag/` é
  de deploy, não é o clone de trabalho.
- Invocação canônica: `MORADA=nova ~/AI/.venv/bin/python -m rag_extractor.cli <sub>`.
- **`MORADA=nova` é obrigatório em toda chamada.** O default `velha` aponta para
  tabela morta (`public.documents`/`public.chunks`, dropadas em 11/08) — silêncio,
  não erro. Esquecer `MORADA` é o modo de falha nº 1 do épico (#167).

Subcomandos vivos (`--help` de 26/08): `discover · ingest · ingest-planilha ·
reingest-planilha · migrar-acervo · exportar-acervo · carregar-cargo · extrair-prosa
· embed · carregar-acervo · materializar-acervo · embed-meta · reconciliar · ask ·
serve`.

## Os dois bancos — confundi-los custa um diagnóstico errado

| banco | porta | schema | tem embedding? |
|---|---|---|---|
| `rag-extractor-pg` | 5432 | `acervo` (obra, impressao, trecho, conceito) | NÃO |
| `motor-pg` | 5433 | `motor` (`indice`, `vetor` particionada d1024/d256) | SIM |

`acervo escada` (shim MCP) cruza os dois: `n_texto` no acervo × `n_emb` no motor, por
`impressao_id`. A escada mede impressão, não obra — ver unidade abaixo.

## MOTOR_DSN — monta na mão, chave certa é MOTOR_PG_PASSWORD

O default no código é `postgresql://motor@127.0.0.1:5433/motor` **sem senha**, e nada
monta o DSN do `.env`. A chave em `deploy/motor/.env` é **`MOTOR_PG_PASSWORD`** (não
`POSTGRES_PASSWORD`). Sintoma de errar: `fe_sendauth: no password supplied`. Não é
percent-encode (o #42/#167 registrava errado).

Contorno em uma chamada:

```python
# /tmp/mkdsn.py
import urllib.parse
env = {k: v.strip().strip('"').strip("'")
       for k, v in (l.strip().split('=', 1)
                    for l in open('/home/claudinho/AI/deploy/motor/.env')
                    if '=' in l and not l.startswith('#'))}
print("postgresql://motor:%s@127.0.0.1:5433/motor"
      % urllib.parse.quote(env['MOTOR_PG_PASSWORD'], safe=""))
```

## Unidade do contrato — obra × UMA impressão servindo por método

Fixado no #2796. `motor.indice.estado ∈ {servindo, aposentado, em_construcao}`.
Re-ingestão **aposenta e cria** — nenhum DELETE. Isso significa:

- Queda do degrau `d` da escada NUNCA é perda de vetor: é o denominador subindo.
  Antes de dizer que algo se perdeu, contar `motor.vetor`.
- Medido 26/08: 758 de 763 obras têm >1 impressão `servindo` (até 6). O
  aposentar-e-criar funciona DENTRO da impressão; entre impressões da mesma obra,
  nada aposenta. Por isso o contrato exige: servível = exatamente UMA impressão
  servindo por método; o resto, aposentado.
- Verificação de fuga: `SELECT obra, count(*) impressões servindo` deve devolver
  max 1 por método.

## Os 5 degraus (o contrato de servível)

Uma obra só é `servindo` quando os cinco fecham na mesma unidade de escrita, e o
verbo RECUSA ALTO nomeando o degrau que faltou:

- a **catalogada** — obra em `acervo.obra`
- b **armazenada** — objeto não-nulo e conferido no MinIO
- c **ingerida** — trechos no rag, impressão servindo
- d **embedded** — todo trecho elegível com vetor (`n_emb = n_texto`)
- e **vetorizada** — vetor de metadado por impressão

Fundamento DMBOK (Data Quality 2.3): completude (a–c) e integridade (d–e) medidas
contra regra conhecida, nunca contra sensação de carregado.

## Custo do embed — para orçar antes de disparar

Qwen3-Embedding-0.6B, backend torch, device cuda: **~35 trechos/s** com PDFs grandes
na fila (bem mais em obras pequenas). 92.189 trechos ≈ 35 min. Se a fila do `embed` é
muito maior que os trechos do lote, o `ingest` pegou obra alheia — escopo errado.

## Cinco armadilhas do núcleo que mordem aqui também

- Espelho de repo serve SHA velho depois do push → `repo_sync` ou ler o clone.
- `&&` no `run_command` some com o erro → usar `;` ou chamadas separadas.
- Faceta válida e despovoada devolve zero sem erro → `rag_facets` antes de filtrar.
- `longjob` não herda o ambiente → `bash -lc 'export MORADA=nova PATH=...; <verbo>'`.
- `edit_page` substitui a página inteira → `get_page` antes, sempre.

## Convenção de código — fronteira [código: TI/IA]

O CONTRATO acima é dado (desta cadeira). Como o código materializa recusa-alto,
tipagem, estrutura de exceção e estilo no toque do `rag_extractor.cli` é execução
TI/IA — não fixada aqui. Sessão que precisar do padrão de código pergunta à cadeira
dona do toque; este material dá o QUE tem de valer, não o COMO escrever a função.
