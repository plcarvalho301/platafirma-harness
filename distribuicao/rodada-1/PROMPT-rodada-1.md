# Rodada 1 — prompt de reivindicação

Texto para colar na abertura da sessão de cada cadeira. Trocar `<CADEIRA>` pelo
nome da persona. Um envio por cadeira; as sessões não se falam.

Cadeiras que respondem: `claudinho-arquiteto`, `claudinho-conhecimento`,
`claudinho-IA`, `claudinha-produto`, `claudinho-TI`, `claudinho-seguranca`,
`claudinha-gestao-estrategica`. `claudinha-fabrica` e `claudinha-osint` não
participam — não são cadeiras.

---

**Rodada 1 da distribuição do acervo. Você é `<CADEIRA>`. Declare quais obras
do acervo são do seu domínio.**

**Base.** `distribuicao/rodada-1/obras-305.csv`, repo `platafirma-harness`: 305
obras com domínio preenchido. Leia o arquivo inteiro antes de responder —
reivindicação de memória não vale. As 388 obras sem domínio estão fora desta
rodada. O campo `dominio_atual` é palpite herdado da triagem, não cerca:
reivindicar contra ele é legítimo e esperado.

**Entrega.** Crie `distribuicao/rodada-1/reivindicacoes/<CADEIRA>.csv` com
cabeçalho `obra_id,nota` e uma linha por obra. `obra_id` copiado literal do CSV
base (UUID). `nota` é uma linha: o que a obra faz pelo *seu* domínio.

**Régua.**

- Reivindique a obra que é **régua** do seu domínio — a que você citaria para
  decidir dentro do seu remit. Não reivindique a que você apenas leria com
  proveito.
- Sem teto de quantidade. O freio é ter que defender cada linha na arbitragem;
  linha sem `nota` perde por ausência de defesa.
- Obra que serve a duas cadeiras: reivindique assim mesmo. Conflito é o
  mecanismo da rodada, não a falha dela.
- **Não reivindique para tapar buraco.** Obra sem reivindicante não sai do
  corpus nem vira pendência de ninguém: fica com o `dominio_atual` e o dono
  classifica ao fim do ciclo. Cobrir vazio com reivindicação fraca contamina a
  rodada 2, que é onde os conceitos nascem.
- Reivindicando contra o `dominio_atual`, diga na nota por quê.

**Escrita.** `git pull --rebase`, commit e push **só do seu arquivo**. Não toque
em `conflitos.csv`, em `obras-305.csv` nem no CSV de outra cadeira.

**Resposta na conversa, no máximo:** quantas obras reivindicou; os três casos em
que reivindicou contra o `dominio_atual`; e o que você deliberadamente **não**
reivindicou apesar de parecer seu.

**Não faça agora:** conceito, hierarquia, relação, subdomínio. Rodada 2 abre com
a rodada 1 fechada.

---

## Terreno da base (para calibrar, não para respeitar)

| `dominio_atual` | obras |
|---|---|
| seguranca-privacidade | 120 |
| capacidade-estatal | 54 |
| ia | 38 |
| engenharia-software | 31 |
| estudos-ontologias | 20 |
| arquiteturas | 17 |
| produtos-digitais | 14 |
| gestao-organizacional | 8 |
| platafirma | 2 |
| inteligencia | 1 |

56 das 305 estão sem subdomínio. Espécie predominante: guia (72), livro (69),
paper (33), norma técnica (25).
