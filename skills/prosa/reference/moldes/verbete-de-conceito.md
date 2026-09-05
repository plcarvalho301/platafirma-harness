# molde — verbete de conceito

Página de wiki (Inteligência de Base). Régua fina: `spec_styleguide-da-wiki.md` §3.2 (fonte).

Distintivo: define um conceito da casa; a 1ª frase é a definição. Molde já lavrado (minuta 0022).

Quatro estratos, na ordem:

0. **Moldura derivada** — gerada do banco, datada, com o `sha` do export, nunca à
   mão. No topo, três campos que o leitor de uma leitura vê primeiro: *valia em
   ‹data›*, *estado* (nota autoral | revisada | validada) e *classificação/difusão*.
1. **Abertura** — a 1ª frase define o conceito; um a três parágrafos que se bastam
   sozinhos e resumem o resto; jargão de domínio com o nome comum ao lado.
2. **Corpo** — seções planas, um nível só, na ordem em que a pessoa usa ou em que a
   coisa funciona. Exemplo é seção, não nota de rodapé.
3. **Apêndice** — bloco DERIVADO, no regime do estrato 0 (banco → wiki, datado, com o
   `sha` do export, nunca à mão). Duas coisas, nenhuma de prosa: (1) teia de vizinhos
   — cada vizinho como «vizinho — motivo · garantia» (campos de
   `acervo.conceito_aresta`); (2) proveniência (`sha` do export, data, curador,
   garantia predominante — a fixar na ADR de tipologia). Saem o «veja também» à mão e
   a leitura relacionada: o vizinho já é campo, e a leitura é a mesma aresta
   obra→conceito que o estrato 0 serve. O verbo gerador ainda não existe (K6 da
   minuta 0022); até sair, o bloco NÃO aparece, e a skill não orienta placeholder à
   mão — a ausência é honesta e mostra onde falta o gerador.
