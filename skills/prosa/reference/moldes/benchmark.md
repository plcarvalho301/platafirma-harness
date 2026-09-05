# molde — benchmark

Família `instrumento-de-processo`. Régua fina de escrita: `docs/styleguide-moldes-por-tipo.md` §2 (fonte; divergiu, vence o anexo).

Distintivo: mede e compara alternativas nomeadas sob método declarado — não é
levantamento (que só reúne) nem parecer (que recomenda sem medir). Sem setup que
deixe refazer, é opinião com tabela.

Estratos, na ordem:

1. **Objeto e pergunta** — nomeia o que se compara e a pergunta de escolha entre
   alternativas nomeadas («qual X para Y»); fecha listando as alternativas. Não
   «o que é X».
2. **Método/setup declarado** — o que se mediu, como, em que ambiente, critérios de
   corte, o que ficou fora; exaustivo para refazer. Toda escolha que enviesa vai
   declarada aqui, não escondida.
3. **Medições** — uma TABELA comparativa, e é ela o centro do benchmark: colunas =
   os candidatos, linhas = as funcionalidades, critérios ou métricas; cada célula
   traz o número na mesma unidade ou o `atende / parcial / não atende`. Fato cru, sem
   adjetivo de juízo (o juízo é do veredito). Mede-se o que a pergunta pede, não tudo
   o que dá; o que não cabe em célula (observação crua, ressalva de medição) vai em
   nota abaixo da tabela, não dissolvido em prosa. Uma leitura basta.
4. **Veredito/recomendação** — qual ganhou, sob que condição, com o trade-off;
   **condicional ao método**, não verdade universal. A mudança de contexto que
   viraria o resultado vai dita; o que passa do medido vai marcado como inferência.
