# Registro da unidade

Cada unidade grava um registro por documento velho, em JSON, na pasta da unidade. A
justificativa vem antes dos campos fixos, em texto livre. A orquestradora lê os campos
fixos; a justificativa é para quem confere a decisão.

```json
{
  "documento_velho": "platafirma-casa-espelho@instancias/padrao/molde-de-readme.md",
  "justificativa": {
    "evidencias": "o que o documento diz, com o trecho que sustenta a decisão",
    "criterio_de_identidade": "o que faz este documento ser ele e não outro"
  },
  "estado": "decidido",
  "faltou": null,
  "entidade": "padrao",
  "entidade_provisoria": false,
  "destinacao": "reescrito",
  "confianca": { "valor": "firme", "entre": [] },
  "coberto_por": null,
  "funde_com": [],
  "pertence_a_revisao": null,
  "eventos": ["dia-e1"],
  "termos": [
    { "nome": "molde", "onde": "título do velho", "saida": "nao_existe", "parecido": null, "fica": "padrao" }
  ],
  "proposta": null,
  "documentos_novos": [
    {
      "caminho": "referencias/instancias/repositorio/molde-de-readme.md",
      "chave_humana": "molde-de-readme",
      "titulo": "Molde de README",
      "forca": "decisao",
      "formato": "markdown",
      "suporte": "instancia",
      "fica_com_a_linha": true,
      "ligacoes": [
        { "tipo": "<tipo da lista fechada>", "destino": "<caminho, chave ou texto>", "destino_e": "caminho", "modo": "decisao" }
      ]
    }
  ]
}
```

## Os campos

| campo | valores | quando |
|---|---|---|
| estado | decidido, nao_decidido, falhou | sempre |
| faltou | texto | em nao_decidido e falhou |
| entidade | o slug que `conferir existe entidade` confirmou, ou nenhuma | em decidido |
| entidade_provisoria | true quando a shape diz que a entidade espera ser dissolvida, como guia e ciclo | em decidido |
| destinacao | validado, reescrito, partido, fundido, apagado | em decidido, salvo pertence_a_revisao |
| confianca.valor | firme, ambigua, nenhuma_serve | em decidido |
| confianca.entre | as duas entidades | só em ambigua |
| coberto_por | o que já cobre a matéria | em apagado, quando algo cobre |
| funde_com | caminho do outro documento e a evidência | em fundido |
| pertence_a_revisao | número da revisão e a evidência | quando o documento é de outra revisão |
| eventos | os ids das linhas de evento da faixa que o documento serve; vazio com a evidência quando nenhum serve | em decidido |
| termos | um item por nome da casa que o velho usa ou que os novos usam, com a saída da conferência | sempre que houver documento novo, e em validado de observação |
| proposta | entidade ou ligação nova: nome, origem, destino, quantas cabem de cada lado, os trechos que pedem o nome, o encaixe mais próximo e por que ele não serve; nulo quando algo encaixa | quando nenhuma entidade ou nenhum tipo de ligação encaixa |
| documentos_novos | um item por documento novo | em validado, reescrito e partido |

Em cada item de termos:

| campo | valores |
|---|---|
| nome | o nome como aparece no documento |
| onde | o trecho ou a parte em que aparece: caminho, cabeçalho, corpo, ligação |
| saida | existe, nao_existe, indeterminavel |
| parecido | o nome parecido que o schema devolveu, ou nulo |
| fica | o slug que o documento novo usa, «proposta», ou «mantido» no corpo de observação |

Em cada documento novo:

| campo | valores |
|---|---|
| caminho | o `pf:original` da shape da entidade, com a chave no lugar de `<slug>` |
| chave_humana | o slug do caminho, único dentro da entidade |
| forca | decisao, proposta, registro |
| formato | o formato do arquivo |
| suporte | original, referencia |
| fica_com_a_linha | true na parte que fica com a linha de origem; no partido, uma só |
| ligacoes.destino_e | caminho, chave, pendente |
| ligacoes.modo | decisao nas ligações da casa e no cinde-de |

O caminho não se monta de cabeça: sai do `golden` ou `referencia` da shape (`instancias/<classe>/` ou `referencias/instancias/<classe>/`), e observação, parecer, levantamento e fichamento levam a data na frente da chave.

O registro não tem golden, estado da ficha, sha nem uuid. O golden de documento em git é
o próprio arquivo, e o resto a orquestradora grava a partir do commit e da tabela de
transições.
