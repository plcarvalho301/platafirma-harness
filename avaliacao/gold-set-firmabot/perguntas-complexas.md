# Perguntas complexas (multi-step) — desenho fechado

Estrato de sondas que exigem compor evidência de mais de um documento, ou de
documento mais estado da PlataFirma (wiki, ADR, repo), para admitir resposta
correta. As 34 de `perguntas-simples.md` são single-hop por construção e não
cobrem essa classe.

Coleta bruta: `avaliacao/gold-set/coleta-multistep-20260807/`
Gold montado:  `avaliacao/gold-set/gold-multistep-20260807.jsonl`

## 1. O que conta como salto

- Elo entre **documentos distintos**, ou entre documento e estado da
  PlataFirma (wiki, ADR, repo). Duas seções da mesma obra **não** contam.
- Cada conclusão do gabarito declara a **contagem de elos**. Conclusão de 1
  elo é admitida apenas quando o elo é a ausência declarada (ver §3).
- O enunciado não carrega identificador bibliográfico (título, autor, ano) nem
  código numérico de norma. Enunciado com número casa por string e mede a
  ferramenta, não quem responde.

## 2. Estrato próprio

Terceiro estrato, tabela e análise separadas. Não é o firmabot (single-hop,
instância sem persona, termo → obra) nem o T3 de
`avaliacao/rag-medicao/protocolo-escada-20260803.md`, que é o estrato negativo.
Aqui o que define o estrato é o número de elos, não a ausência de resposta.

Análise sempre por estrato, nunca agregada com os outros dois.

## 3. Como o alvo se crava

- O alvo sai da curadoria **antes** da execução, nunca do retorno da busca:
  os documentos do par e a composição entre eles, nomeados.
- Gabarito é **lista de conclusões**, uma linha por conclusão, cada uma com a
  contagem de elos. Não há rótulo único por questão.
- **Composição parcial tem rótulo próprio**: cada conclusão é atingida ou não
  atingida individualmente. Questão com 3 conclusões e 2 atingidas reporta
  2/3, nunca acerto ou erro por arredondamento.
- **Ausência declarada é conclusão certa.** Obra citada por remissão e fora do
  acervo: a resposta correta é "não dá para confirmar com este corpus". Alimenta
  o rótulo de abstenção, e é a única conclusão admitida com 1 elo.
- Questão cuja falha é reprodutível e vem do mecanismo de busca, não de quem
  responde, entra como **caso negativo declarado**, com a falha escrita no
  gabarito — não se descarta.

Quantidade e sequência da coleta são de claudinha-gestao-estrategica. Cálculo
das métricas sobre este estrato é de claudinho-IA. Vocabulário e alvo de
registro são de claudinho-conhecimento.
