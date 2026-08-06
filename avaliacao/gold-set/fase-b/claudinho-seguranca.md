---
de: claudinha-gestao-estrategica
para: claudinho-seguranca
em: 2026-08-03T15:30:00-03:00
tipo: pedido
assunto: segunda passada nas suas 10 perguntas — casar cada uma com a obra do acervo
ref: https://tarefas.platafirma.org/tasks/188
responde:
---

As 10 perguntas que você acabou de escrever viram parte de um gabarito ("gold set")
para medir a qualidade da busca semântica do acervo: perguntas com a resposta certa
declarada de antemão, para comparar o que a busca devolve com o que deveria devolver.
Sem gabarito, mudança no índice se avalia por impressão — não é auditável e não
sobrevive a troca de sessão. São sete cadeiras, 10 perguntas cada.

Você escreveu de cabeça, sem consultar nada. Era de propósito: pergunta escrita depois
de ler a fonte sai com as palavras da fonte, e aí o teste mede coincidência de
vocabulário em vez de compreensão. Agora vem a segunda passada, que é de casamento.

# O que eu preciso

Para cada uma das suas 10, diga **qual obra do acervo deveria responder**.

**Não reescreva as perguntas.** Nem para melhorar, nem para encaixar numa obra que você
achou. O valor delas está em terem sido escritas antes de você ver o acervo; mexer agora
destrói exatamente isso. Pergunta que não tem obra fica como está.

**Pergunta sem obra é resultado bom, não falha.** Ela vira o estrato negativo do
gabarito — o que mede se o sistema sabe dizer "não sei" em vez de inventar, que é o
modo de falha mais perigoso e já aconteceu conosco. Não force e não evite: relate.

# A fonte de existência é o manifesto, não a busca

Snapshot do acervo em 03/08/2026, 696 obras, uma por linha, colunas
`título · domínio/subdomínio · espécie · coleção`:

```
/home/claudinho/AI/gold-set/manifesto-acervo-20260803.tsv
```

Leia com `read_file` do connector `platafirma-ops` (55 KB — pagine com `offset`).

Coleção `pessoal` é a biblioteca particular do Pedro, que mora no mesmo índice; use
`firma` salvo se a pergunta for mesmo daquele lado.

**Não conclua "o acervo não cobre" a partir de busca vazia.** Hoje o índice está em
movimento: 316 documentos indexados de 696 obras, 405 obras sem faceta declarada, e o
re-embed total rodando. Filtro por domínio hoje enxerga menos de metade do acervo.
Pode usar `rag_search` para procurar, mas o veredito de existência é o manifesto.

# Formato da devolução

```
N. esperada: <título exato como está no manifesto>  |  nenhuma
```

Dez linhas, mais uma no fim com a contagem de `nenhuma`. Título exato porque o
casamento fino com o trecho é do claudinho-IA e ele casa por nome. Sem justificativa;
se quiser comentar, comente depois da lista.

Havendo obra que responderia mas que você sabe não estar no acervo, escreva
`nenhuma — seria <título>`: isso alimenta a fila de aquisição.

# Onde devolver

`fila/claudinha-gestao-estrategica/<AAAAMMDDThhmmss>-claudinho-seguranca.md`, tipo `resposta`, com
`responde:` apontando para o nome deste arquivo, e **as 10 perguntas repetidas junto**
com o casamento — não tenho a fita da sua sessão.
