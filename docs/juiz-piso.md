# Juiz da banda curta

`avaliacao/juiz-piso/` julga cada seção curta do acervo (banda de menos de 40 tokens) como
`real`, `so-titulo` ou `ancora-ruido`, com LLM local (ollama), e grava o veredito em
`acervo.secao.qualidade`. Seções muito curtas concentram lixo estrutural (cabeçalho e rodapé
corridos, número de página, entrada de sumário, fragmento órfão de split); todas nascem
`qualidade='nao-julgada'`, e o juiz separa conteúdo de ruído para o ruído não subir na recuperação.

## Dois passos, o campo só no segundo

1. **`juiz_banda.py`** lê `banda_lt40.jsonl` (o dump da banda), julga item a item e grava
   checkpoint linha a linha em `juiz_banda.out.jsonl`. Não toca o banco. Dump e checkpoint moram em
   `$PLATAFIRMA_INSTANCIA/dados/avaliacao/juiz-piso/`.
   - Resumível: ao subir, pula ids já julgados; `erro` é tentado de novo no lance seguinte.
   - `flush` e `fsync` por item: matar no meio perde no máximo o item em voo.
   - Variáveis: `JUIZ_MODELO`, `JUIZ_BANDA`, `JUIZ_OUT`, `JUIZ_LIMIT` (0 = banda inteira),
     `JUIZ_LOG_A_CADA`.
2. **`juiz_aplica.py`** grava `secao.qualidade` a partir do checkpoint e imprime a distribuição
   corrigida. Recusa escrever com banda incompleta; `--parcial` força, `--dry` só relata.

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

Ordenar por `id` mantém a ordem estável entre lances, que é o que permite retomar.

## Lançar

A banda inteira leva cerca de 3 h em uma thread, a 1,2–1,5 item/s:

```
sessao longjob run juiz-banda-lt40 python3 /opt/platafirma/current/harness/avaliacao/juiz-piso/juiz_banda.py
sessao longjob run juiz-aplica python3 /opt/platafirma/current/harness/avaliacao/juiz-piso/juiz_aplica.py
```

O segundo, ao terminar o primeiro: grava e imprime a distribuição corrigida.

## Limite do número

O veredito é do juiz (qwen3.5:9b, temperatura 0), sem gold set próprio: a distribuição corrigida é
derivada do juiz, não verdade de campo. Calibrar contra amostra rotulada à mão vem antes de tratar
o número como assertivo.
