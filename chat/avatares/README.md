# chat/avatares — retrato de cada cadeira

O que `provisiona-cadeiras.sh` procura aqui: **um arquivo por cadeira, nomeado pelo
slug dela** no org canônico (`platafirma-arquitetura/docs/org-template-canonico.md`),
com extensão `.png`, `.jpg`, `.jpeg`, `.webp` ou `.gif`. O slug é aceito na caixa
original ou em caixa baixa:

```
claudinho-TI.png            claudinha-produto.png
claudinho-IA.png            claudinho-dados.png
claudinho-arquiteto.png     claudinho-seguranca.png
claudinha-gestao-estrategica.png
```

Cadeira sem imagem **não interrompe o provisionamento**: o script avisa nomeando a
cadeira, provisiona o resto e sai 0 (card 448/B-3). A cadeira fica de pé sem retrato,
e uma corrida posterior — depois que a imagem chegar — põe o avatar sem recriar
usuário nem sala.

A imagem só sobe ao Synapse quando muda: o script guarda o `sha256` do arquivo no
`account_data` da cadeira (`org.platafirma.avatar`) e compara antes de reenviar.

**Quem fornece as imagens não é a fábrica.** Retrato de cadeira é identidade visual,
não construção.
