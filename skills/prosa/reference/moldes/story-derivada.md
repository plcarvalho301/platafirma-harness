# molde — story derivada (sai de uma formalização)

Forma: a story da ADR 0096 (padrão de card por nível), com quatro rótulos que mudam; o
esqueleto da story sai de `tarefas modelo story`. Onde ela nasce: guia discovery, Formalizar,
passo 5 (`acervo ler casa guia discovery`).

Leitor: quem executa, um agente sem conversa com quem decidiu. Por isso o contrato e o
ponteiro para o item que a story atende.

A story derivada não repete o que a ADR e a spec dizem: carrega a execução e aponta o item.
Dois tipos, pelo documento de que deriva:

- **conformação** — faz o que roda obedecer a uma ADR;
- **implementação** — constrói o que uma spec descreve, ou escreve o próprio documento
  derivado (a emenda à ADR, a spec nova).

## O que muda contra a ADR 0096

```
Negócio:      #<feature> · R<a>, R<b> da spec <peça>   |   D<n> da arq:NNNN   |   Peça <n>, enquanto não há R nem D
Referencial:  a ADR e a spec de que deriva; story que escreve o próprio derivado aponta os comentários decisão e requisito do card
Tarefas:      as tasks que esta fita faz, uma por linha, na ordem: o que faz · repo@caminho · como se confere; a task não tem card
Aceite:       o item derivado que a fatia atende (R<n> ou D<n>); o comando literal se materializa no Plano, em Aceite × prova
Travas:       trava que vem de ADR vira ponteiro D<n>; trava de execução fica escrita
```

A story é uma fita do executor, nem mais nem menos (arq:0060 §3, revista em 12/10/2026). A
formalização quebra primeiro em tasks e depois agrupa as tasks em stories, pelas condições do
guia discovery, seção «A quebra».

O resto segue a ADR 0096: Raio de ataque, Comportamento esperado, Ambiente, Onde, Passos,
Entrega, e o Plano no refinamento técnico. O Plano registra a versão servida da spec que
leu: o `Medido em` traz repo e sha.

## A voz

1. **Negócio** — só o ponteiro: a feature e o item. Nada de contexto de negócio.
2. **Referencial** — lista fechada; não é leitura recomendada.
3. **Aceite** — aponta o item, sem repetir o texto dele.
4. **Travas** — imperativo e motivo; a que vem de ADR é só o ponteiro.

Régua:

- Toda peça tem ao menos uma task, numa story, ou foi para o Fora. Toda story aponta ao menos
  um R, um D ou uma Peça.
- Story menor que uma fita que podia correr junto com outra do mesmo executor e repositório é
  task mal posta: vai para a lista Tarefas da outra.
- Requisito aceito sem story que o atenda é buraco da formalização.
- Quando a frente não constrói nada, a story é a escrita do documento.
- Vale só para a story derivada. Story sem pai e task seguem a ADR 0096 inteira.
