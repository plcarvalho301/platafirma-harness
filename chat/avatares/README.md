# chat/avatares — retrato de cada cadeira

O que `provisiona-cadeiras.sh` procura aqui: **um arquivo por cadeira**, com extensão
`.png`, `.jpg`, `.jpeg`, `.webp` ou `.gif`. O nome do arquivo pode ser qualquer uma das
formas da cadeira, em caixa original ou baixa — o **slug** do org canônico
(`platafirma-arquitetura/docs/org-template-canonico.md`), o **sufixo** do harness
(`personas/persona-<sufixo>.md`) ou o **localpart** do Matrix:

```
claudinho-TI.png       TI.png       _pf_ti.png
claudinha-produto.png  produto.png  _pf_produto.png
```

Slug e sufixo não são a mesma coisa, e por isso as duas formas valem: a tabela do org
cobre as cadeiras que têm slug lá; **cadeira fora da tabela só tem sufixo** — é o caso
de `politicas-publicas`, assessor do dono, que tem sala mas não linha no org
(card 460). Para ela, nomeie a imagem `politicas-publicas.png`.

Cadeira sem imagem **não interrompe o provisionamento**: o script avisa nomeando a
cadeira, provisiona o resto e sai 0 (card 448/B-3). A cadeira fica de pé sem retrato,
e uma corrida posterior — depois que a imagem chegar — põe o avatar sem recriar
usuário nem sala.

A imagem só sobe ao Synapse quando muda: o script guarda o `sha256` do arquivo no
`account_data` da cadeira (`org.platafirma.avatar`) e compara antes de reenviar.

**Quem fornece as imagens não é a fábrica.** Retrato de cadeira é identidade visual,
não construção.
