# Registro anti-reabertura — harness

Índice do que está precluído no harness. Entrada não reabre sem, na mesma linha, (1) a
citação do que fechou e (2) um fato novo nomeado, posterior à data de fechamento.

## Decisões vigentes

### hrn:0001 — Ingestão de obra `wiki://` está fora de pauta (09/08/2026)
> "Ignora isso, bota antireabertura até eu mandar. Não é pra contar a wiki nisso."

Decisão do dono, 09/08/2026. Alcance:

- Obra com `acervo.obra.endereco LIKE 'wiki://%'` **não entra em conferência de estado do
  acervo**: nem como obra sem bytes, nem como obra não ingerida, nem como conceito sem
  faceta propagada. Não é fuga de degrau; está fora da escada por construção.
- **Não se abre pauta de leitor `wiki://`** — nem como órfão a arbitrar, nem como pedido
  de dono, nem como pendência declarada em artefato. O assunto volta quando o dono mandar,
  e só então.
- Vale para conferência ad-hoc também: contagem crua de `documents.trata_de` ou de
  `acervo.obra.objeto` que não exclua `wiki://` produz furo fantasma. O predicado canônico
  é o de `scripts/deriva-acervo.py`; `bin/acervo-status` já segrega as `wiki://` como
  "fora da escada".

Reabre quem: o dono, por ordem expressa.
