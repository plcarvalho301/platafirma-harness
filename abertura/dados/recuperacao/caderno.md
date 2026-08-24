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
