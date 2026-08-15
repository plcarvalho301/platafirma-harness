"""Os dois corpos de giro silencioso, e o unico lugar onde eles se escrevem.

Ritual de encerramento e ancora de compactacao sao a mesma mecanica — um giro a
mais na fita, com `--silencioso` no verbo — e diferem so no que pedem a cadeira.
Quem enfileira o ritual e a recepcao (na rotacao); quem enfileira a ancora e o
worker (ao ver a fronteira de compactacao, ou ao bater o contador). Texto em
duas copias divergiria no dia em que so uma fosse revista.

Sao PEDIDOS a cadeira, nao comandos ao harness: quem escreve a mesa e o modelo
dentro da fita, com o que ele sabe do assunto. Verbo nenhum sabe o que anotar.
"""

from __future__ import annotations

# Escovacao (TODA-CADEIRA.md): isto sobe no contexto a cada rotacao e a cada
# compactacao — nao a cada giro, mas perto. Curto de proposito.

ENCERRAMENTO = (
    "A sala desta conversa foi rodada e esta fita esta sendo encerrada. "
    "Rode `encerrar fita --so-memoria` e nao responda nada: o produto deste "
    "giro e a memoria, e nao ha sala para onde falar."
)

ANCORA = (
    "A janela de contexto acabou de ser compactada. Anote a mesa AGORA, com "
    "`mesa anota <chapeu>`, incluindo o que voce perderia se o resto do "
    "contexto sumisse: assunto, decisao tomada, proximo passo e ponta solta. "
    "Nao responda nada — o produto deste giro e a mesa."
)

ANCORA_POR_CONTAGEM = (
    "Marco de giros nesta fita. Anote a mesa AGORA, com `mesa anota <chapeu>`, "
    "incluindo assunto, decisao tomada, proximo passo e ponta solta. Nao "
    "responda nada — o produto deste giro e a mesa."
)
