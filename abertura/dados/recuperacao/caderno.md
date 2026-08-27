# caderno — produtos (dados)

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
