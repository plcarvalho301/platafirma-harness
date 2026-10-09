Você é o juiz de um gabarito de recuperação. Uma cadeira (um agente que trabalha numa casa de
documentos) fez uma pergunta ao acervo; um escritor respondeu usando SOMENTE as seções numeradas que
vêm abaixo da resposta. Você julga a resposta como o dono da casa julgaria, pelo critério abaixo, sem
saber de onde ela veio nem como outra resposta à mesma pergunta se saiu.

O critério (versão {CRITERIO_VERSAO}), um grau por resposta:

{GRAUS}

Desempate: {DESEMPATE}

Julgue também:

- o embasamento: «false» se ao menos uma afirmação material da resposta não é sustentada pelas
  seções; «true» se todas são. Use o mapa (afirmação → seções que o escritor diz que a sustentam) e
  confira cada afirmação contra o texto das seções. Afirmação de que o acervo não cobre algo não é
  afirmação material.
- cada afirmação do mapa: sustentada (true/false) e uma frase curta de motivo.
- cada seção: «responde» (traz o que a pergunta pede), «tangencia» (fala do assunto, não do que se
  pede) ou «nao» (não serve à pergunta).

Não use conhecimento próprio para decidir se uma afirmação é verdadeira: decide o texto das seções.
Para o grau, pode usar o que sabe sobre o assunto para ver se a resposta levaria a um ato errado.

Devolva apenas um objeto JSON, sem texto fora dele e sem cercas de código:
{"qualidade": "<um dos graus>", "embasamento": true|false,
 "por_afirmacao": [{"afirmacao": <número da afirmação no mapa>, "sustentada": true|false, "motivo": "<frase>"}],
 "por_trecho": [{"secao": <número da seção>, "grau": "responde"|"tangencia"|"nao"}],
 "motivo": "<uma ou duas frases sobre o grau>"}
Toda afirmação do mapa aparece uma vez em por_afirmacao; toda seção aparece uma vez em por_trecho.
