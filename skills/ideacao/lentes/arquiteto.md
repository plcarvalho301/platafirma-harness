# Lentes da arquiteto

Este arquivo vale quando a cadeira que roda a sessão é o arquiteto. Ele diz que alvo ela
recebe, como é a ficha de uma ideia, que lentes ela usa e onde ela procura na casa.

## O alvo

O alvo do arquiteto é uma forma que ainda não existe ou que deixou de servir: onde uma
capacidade mora, onde ela acaba, que estrutura amarra duas cadeiras que decidem coisas
que não fecham entre si, que forma de sistema atende uma parte. O parágrafo do alvo diz
que capacidade de negócio está em jogo, quem a usa e onde a forma atual quebra.

A pergunta devolvida fala da estrutura: «como a firma poderia organizar X para que Y?».
O alvo é solução única quando se escolhe uma estrutura, como o lugar de uma peça ou a
forma que atende uma capacidade. É catálogo quando o resultado é um conjunto que cabe
junto, como o mapa de capacidades, os contextos ou os repositórios.

## A ficha da ideia

Cada ideia da primeira rodada leva sete campos, um por linha:

- **Título:** de três a sete palavras.
- **Capacidade ou fronteira:** a capacidade de negócio que a ideia serve, ou a fronteira
  que ela move.
- **A forma:** a estrutura proposta, em uma frase.
- **O que exige:** o que precisa mudar ao redor, em time, código e norma.
- **O que abre:** o que passa a ser possível.
- **O que a derruba:** o fato que a tornaria errada.
- **A lente:** a que gerou a ideia.

## As lentes

Use pelo menos três por rodada. Na segunda rodada, use as que a primeira não usou.

- **Capacidade.** Reescreva o alvo como capacidade de negócio. A ideia dá nome ao que
  falta, une duas que cuidam do mesmo assunto ou divide uma que carrega duas.
- **Custo de transação.** Junte o que custa caro transferir e separe o que não custa. A
  ideia move uma fronteira por esse critério.
- **Convergência.** Software, time e negócio se desenham juntos. A ideia mexe em um dos
  três e diz o que muda nos outros dois.
- **Atributo de qualidade.** Troque o adjetivo por um cenário com estímulo, resposta e
  medida. A ideia nasce de qual atributo deveria mandar na forma.
- **Essencial.** Tire a camada ou a abstração que nenhum pedido exige. A ideia é o que
  sobra.
- **Soberania.** Procure a forma aberta antes da paga. A ideia que depende de fornecedor
  diz que alternativa aberta foi procurada.
- **Legado.** O que todos contornam e ninguém mexe. A ideia evolui ou aposenta o legado.

## Onde buscar na casa

Procure o que a casa já decidiu sobre o alvo, nesta ordem:

1. As decisões do dono nos cards que tocam o alvo: `tarefas listar`, depois
   `tarefas ler <card>` e `tarefas comentarios <card> --indice`.
2. As capacidades e as classes já gravadas: `infra rodar ontologia -- listar capacidade`
   e `infra rodar ontologia -- listar shape`.
3. Os pareceres, as observações e as referências de repositório, stack e componente, em
   `referencias/instancias/parecer`, `referencias/instancias/observacao`,
   `referencias/instancias/repositorio`, `referencias/instancias/stack` e
   `referencias/instancias/componente`.
4. A busca pelo sentido: `busca buscar casa "<pergunta do alvo>" --texto trecho`.
