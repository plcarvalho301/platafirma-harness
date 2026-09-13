# juiz-piso — classificação estrutural da banda <40 toks

Runner resumível que julga cada seção curta do acervo (**banda <40 tokens**, ~14,5k
seções) como `real | so-titulo | ancora-ruido` via LLM local (ollama), e grava o
veredito em `acervo.secao.qualidade`. Produtiza os smokes `tmp/judge_smoke.py` e
`tmp/juiz_piso.py`.

## Por que a banda <40

Seções muito curtas concentram lixo estrutural — cabeçalho/rodapé corrido, número de
página, entrada de sumário, fragmento órfão de split ruim. Todas nascem
`qualidade='nao-julgada'`; o juiz separa o conteúdo real do ruído para que o ruído não
suba na recuperação.

## Fluxo (dois passos, o campo só no segundo)

1. **`juiz_banda.py`** — lê `banda_lt40.jsonl` (dump da banda), julga item a item,
   faz **checkpoint linha-a-linha** em `juiz_banda.out.jsonl`. **Não toca o banco.**
   - Resumível: ao subir, pula ids já julgados; `erro` é re-tentado no próximo lance.
   - Kill-safe: `flush`+`fsync` por item; matar no meio perde no máximo o item em voo.
   - `JUIZ_MODELO`, `JUIZ_BANDA`, `JUIZ_OUT`, `JUIZ_LIMIT` (0=banda inteira), `JUIZ_LOG_A_CADA`.
2. **`juiz_aplica.py`** — grava `secao.qualidade` a partir do checkpoint e imprime a
   distribuição corrigida. **Gate**: recusa escrever com banda incompleta (`--parcial`
   força; `--dry` só relata). É o passo "aí gravo qualidade" — antes dele, nada no campo.

## Regenerar o dump da banda

```sql
with tk as (select secao_id, sum(token_count) toks from acervo.trecho
            where secao_id is not null group by secao_id),
banda as (select s.id, s.titulo, tk.toks from acervo.secao s
          join tk on tk.secao_id=s.id where tk.toks < 40),
corpo as (select t.secao_id, string_agg(t.texto, E'\n' order by t.ordem_leitura) corpo
          from acervo.trecho t join banda b on b.id=t.secao_id group by t.secao_id)
select json_build_object('id',b.id::text,'titulo',coalesce(b.titulo,''),
                         'corpo',coalesce(c.corpo,''),'toks',b.toks)::text
from banda b left join corpo c on c.secao_id=b.id order by b.id;
```

Ordenar por `id` mantém a ordem estável entre relances (resumibilidade).

## Lançar (longjob, ~3h single-thread a ~1,2–1,5 it/s)

```
longjob run juiz-banda-lt40 bash -lc 'cd ~/AI/tmp && python3 juiz_banda.py'
python3 juiz_aplica.py           # ao terminar: grava + distribuição corrigida
```

## Ressalva

O veredito é do juiz (qwen3.5:9b, temp 0), sem gold set do próprio juiz — a
distribuição corrigida é **juiz-derivada**, não verdade de campo. Calibrar contra
amostra rotulada à mão é passo separado antes de tratar o número como assertivo.
