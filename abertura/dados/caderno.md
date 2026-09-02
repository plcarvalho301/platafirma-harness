# caderno — head (dados)

## Entrega é a dinâmica capturada inteira — não completude garantida (dono, 02/09/2026)

Quando o dono pede "quero X e Y acontecendo", ele pede uma DINÂMICA. Entrega é
essa dinâmica capturada ponta a ponta e rodando. **Não** é garantia absoluta de
que nunca falha, não é gate, não é prova de completude — o dono NÃO pede isso e
recusa quando aparece.

- **Meia-entrega** = capturar só metade da dinâmica (ex.: o server coleta mas nada
  crava). Isso é não-entrega: a dinâmica pedida não acontece.
- **Entrega** = a dinâmica acontece inteira (ex.: encerrar → 3 giros no banco,
  rodando e provado). Capturou a dinâmica, parou.
- Os dois erros simétricos: entregar metade e chamar de progresso; ou, do outro
  lado, travar a entrega caçando garantia absoluta. Ambos ignoram o pedido.
- Morde dados mais que as outras cadeiras: o caminho é uma cadeia
  (schema → carga → transporte → consumo). Antes de dizer "feito", confira que a
  dinâmica corre ponta a ponta — não que um elo isolado passou a existir.

Corolário vivo (#2945): a dinâmica "encerrar → 3 primeiros giros no banco" está
capturada — `_sessao_encerrar` coleta e chama `bin/_giro-carga.py` (cria a fita
por `sessao_id`, upsert idempotente), migrações 0088/0089 aplicadas, prova cravada
nesta fita. Capturado.
