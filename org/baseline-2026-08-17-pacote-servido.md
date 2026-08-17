# Baseline pós — medição de 17/08/2026, depois de 9e4c266

`conferir sessao <cadeira>`, tokenizador do harness. Orçamento declarado: 6.300.

| Cadeira | Zero (16/08) | Pós (17/08) | Δ |
|---|---|---|---|
| IA | 9.157 | 6.873 | −2.284 |
| TI | 8.298 | 7.499 | −799 |
| dados | 7.925 | 10.289 | +2.364 |
| gestão | 7.366 | 7.866 | +500 |
| segurança | 7.015 | 7.466 | +451 |
| produto | 6.670 | 8.612 | +1.942 |
| arquiteto | 5.550 | 7.263 | +1.713 |
| fábrica | 5.408 | 7.386 | +1.978 |
| jaiminho | 4.511 | 6.137 | +1.626 |
| políticas-públicas | 3.811 | 6.813 | +3.002 |

**O delta bruto não é comparável, e ler assim inverte o sinal.** Duas peças ENTRARAM no
pacote entre as duas medições, ambas por decisão da própria spec: `conduta-dono` (1.460,
fase 3) e `antirreabertura` (751, fase 4). Somam **2.211 tokens em toda cadeira**. Quem
cortou manifesto aparece caindo; quem não tinha o que cortar aparece subindo — e não
mexeu em nada.

Descontadas as duas peças novas, o corte líquido por cadeira é: IA −4.495 · TI −3.010 ·
jaiminho −585 · políticas-públicas +791 · arquiteto −498 · fábrica −233 · segurança
−1.760 · gestão −1.711 · produto −269 · dados +153.

## O que reprova hoje

- **`tool-manifest-cadeira`** — teto 900. dados serve **3.339**, produto **2.428**. São as
  duas cadeiras que não fizeram a poda que IA (2.827→897), TI (→743) e segurança
  (2.144→898) fizeram. Sozinhas respondem por 3.967 dos tokens acima do teto.
- **`persona`** — teto 1.500. Faixa servida 1.421–2.024; dados é a maior. O teto está
  errado, não as personas: claudinho-IA propôs 1.650 com a faixa medida na mão, e não há
  como cortar sem tirar FRONTEIRA ou NEGATIVAS.
- **`antirreabertura`** — 751 contra teto 650, em **toda** cadeira. A peça é minha e o
  teto fui eu que declarei; cresceu hoje com a seção Papéis. Ou sobe para 800, ou a peça
  passa a ser índice com o corpo por ato.
- **`mesa`** — teto 250, servido 641–1.163. Já estava reprovando; o defeito de montagem
  (9e4c266) a escondia atrás de um zero.

## O que isto ainda não mede

Token servido, não efeito. Se o pacote menor responde melhor, ninguém mediu — e a medição
de fundo que a spec cita (`tam-etal-let-me-speak-freely`) diz que restrição de formato
muda raciocínio. Baseline de EFEITO é da fase 9 e é de claudinho-IA; isto aqui é o insumo
dela.
