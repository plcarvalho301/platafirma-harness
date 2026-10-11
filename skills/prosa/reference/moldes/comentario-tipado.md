# molde — comentário tipado (discovery)

Forma e régua fina: anexo de moldes, §8 (`acervo ler casa padrao styleguide-moldes-por-tipo`).
Onde ele entra no ciclo: guia discovery, Parecer e Formalizar (`acervo ler casa guia
discovery`). Divergiu, a fonte é o anexo.

Leitor: o autor do two-pager, que integra a contribuição ao corpo, e o dono, que passa os olhos
só pelas primeiras linhas para saber o que espera por ele.

Um tema por comentário, e um tipo por comentário. Tema é o que fecha num mesmo lugar.

## Esqueleto

```
<tipo> (<a quem ou quem, quando o tipo pede>): <o tema em uma frase>

<o que sustenta, em poucas linhas>
<as linhas fixas do tipo>
```

| tipo | primeira linha | linhas fixas | nasce | fecha com |
|---|---|---|---|---|
| insumo | `insumo: <nome do documento ou o fato>` | `Traz:` o que muda para este card | fechado | — |
| pergunta | `pergunta (<cadeira>): <a pergunta>` | — | aberto | respondida (onde entrou no corpo) · retirada |
| buraco | `buraco: <onde a solução quebra>` | `Caso:` medido, com repo@caminho ou spec e seção · `Remendo:` detalhe, corte ou volta à lapidação | aberto | remendado (onde) · cortado (foi ao Fora) · volta à lapidação |
| requisito | `requisito: <o comportamento exigido>` | `Confere:` o comando ou a consulta, e o resultado | aberto | aceito (`R3 da spec X`) · fundido em #N · retirado (motivo) |
| decisão | `decisão (<quem decidiu>): <a escolha>` | `Descartado:` alternativas e por quê · `Substitui:` #N, quando substitui | fechado | formalizada (`D2 da arq:NNNN`), quando vira ADR |

O fecho é a última linha do próprio comentário, escrita quando ele fecha:

```
fecho: <resultado> — <onde foi parar>
```

Até a #3410 dar `tarefas comentar <card> --fecha <n>`, o fecho sai como comentário próprio,
`fecho #<n>: <resultado> — <onde foi parar>`, e migra para dentro do comentário quando o ato
existir.

## A voz

1. **Primeira linha** — diz o tema inteiro, sem «sobre» nem «questão de».
2. **Sustentação** — fato no presente ou passado; inferência marcada.
3. **Linhas fixas** — cada uma em linha própria, rótulo na frente, uma linha cada.
4. **Fecho** — o resultado numa palavra do tipo e o destino com nome.

Quatro réguas que pegam a maior parte dos erros:

- Buraco por suposição é pergunta. Na dúvida se o problema existe, é pergunta.
- Buraco sem `Remendo:` é queixa; requisito sem `Confere:` é desejo.
- Decisão do dono registrada por uma cadeira abre com `decisão (dono):`. A aposta é
  `decisão (dono): apostar e formalizar`.
- Sete perguntas sobre o mesmo artefato são um comentário só, numeradas.

Não se aplica ao comentário de delivery (registro de negócio, conferência, registro de
trabalho), que tem os tipos da F3.
