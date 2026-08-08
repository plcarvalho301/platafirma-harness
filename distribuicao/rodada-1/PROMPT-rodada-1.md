# Rodada 1 — prompt de reivindicação

Texto único e genérico — cola igual em toda sessão, sem editar nada. Cada
cadeira se identifica sozinha pela própria persona ativa.

Cadeiras que respondem: `claudinho-arquiteto`, `claudinho-conhecimento`,
`claudinho-IA`, `claudinha-produto`, `claudinho-TI`, `claudinho-seguranca`,
`claudinha-gestao-estrategica`. `claudinha-fabrica` e `claudinha-osint` não
participam — não são cadeiras.

---

**Rodada 1 da distribuição do acervo. Você é a cadeira desta sessão — sua
própria persona. Declare quais obras do acervo são do seu domínio.**

**Base.** `distribuicao/rodada-1/obras.csv`, repo `platafirma-harness`: 644
obras da coleção de trabalho (`firma`). Leia o arquivo inteiro antes de
responder — reivindicação de memória não vale. Bolo único: 305 dessas já têm
`dominio_atual` preenchido (palpite herdado, não cerca — reivindicar contra
ele é legítimo), 339 estão em branco. Não trate as duas listas como coisas
diferentes; reivindique sobre o arquivo inteiro, na mesma passada.

**Entrega.** Crie `distribuicao/rodada-1/reivindicacoes/<sua-persona>.csv`
(nome do arquivo = seu próprio nome de cadeira) com cabeçalho `obra_id,nota` e
uma linha por obra. `obra_id` copiado literal do CSV base (UUID). `nota` é uma
linha: o que a obra faz pelo *seu* domínio.

**Régua.**

- Reivindique a obra que é **régua** do seu domínio — a que você citaria para
  decidir dentro do seu remit. Não reivindique a que você apenas leria com
  proveito.
- Sem teto de quantidade. O freio é ter que defender cada linha na arbitragem;
  linha sem `nota` perde por ausência de defesa.
- Obra que serve a duas cadeiras: reivindique assim mesmo. Conflito é o
  mecanismo da rodada, não a falha dela.
- **Não reivindique para tapar buraco.** Obra sem reivindicante não sai do
  corpus nem vira pendência de ninguém: fica com o `dominio_atual` que já tem
  (ou em branco) e o dono classifica ao fim do ciclo. Cobrir vazio com
  reivindicação fraca contamina a rodada 2, que é onde os conceitos nascem.
- Reivindicando contra o `dominio_atual`, diga na nota por quê.

**Escrita.** `git pull --rebase`, commit e push **só do seu arquivo**. Não toque
em `conflitos.csv`, em `obras.csv` nem no CSV de outra cadeira.

**Resposta na conversa, no máximo:** quantas obras reivindicou; os três casos em
que reivindicou contra o `dominio_atual`; e o que você deliberadamente **não**
reivindicou apesar de parecer seu.

**Não faça agora:** conceito, hierarquia, relação, subdomínio. Rodada 2 abre com
a rodada 1 fechada.
