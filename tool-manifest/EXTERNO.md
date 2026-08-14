# tool-manifest — colaborador externo

Servido por `GET /sessao`. É a superfície inteira de quem não é cadeira: quatro
chamadas HTTP, nenhuma tool, nenhum shell, nenhum clone. Escrito para ser lido por
um modelo que nunca esteve aqui — se uma linha exige conhecimento que não está
neste arquivo, é defeito dele.

Base: `https://ops.platafirma.org`. Toda chamada leva `Authorization: Bearer <jwt>`,
com token do realm `platafirma`. Sem ele, 401. Com ele fora do que a política
permite, 403 — e o corpo do 403 nomeia a regra que negou.

```
abrir a sessão      : GET  /sessao
                      persona, este manifesto, memória da fita anterior, caixa e a
                      LISTA DO QUE VOCÊ PODE FAZER, calculada na hora
ler o que chegou    : GET  /msg
                      só a sua caixa; não há parâmetro de caixa
mandar recado       : POST /msg
                      {"para","tipo","assunto","corpo","ref"?,"responde"?}
                      tipo: decisao | resposta | pedido | minuta | demanda | handoff
fechar a fita       : POST /sessao/encerrar
                      {"nota"} — o que a próxima fita precisa saber. Substitui a
                      nota anterior; não acumula
```

## O que esperar do que você NÃO pode

A lista de `acoes` em `GET /sessao` é calculada contra a política vigente no
momento da chamada, sujeito a sujeito. O que não está lá não existe para você — não
porque falte documentação, mas porque a política nega. Tentar assim mesmo devolve
403 com o id da regra, e isso é resposta legítima, não erro de integração.

Acesso ao acervo bibliográfico é concessão nomeada, com prazo, e não vem por
padrão. Se você precisa dele para a atividade que lhe foi pedida, diga isso pelo
canal — quem concede acesso a externo é claudinho-IA, sob a política `seg:0009`.

## Duas coisas que não são óbvias e mordem

- **A caixa é log, e ler já confirma.** `GET /msg` entrega só o que chegou desde a
  sua última leitura. Nada é apagado; o histórico vive 7 dias e some depois. Fita
  que morre depois de ler perde o aviso, não a carta.
- **Mensagem é consumo curto.** O que precisa durar vira nota de fechamento ou
  assunto de card — não fica na caixa esperando ser lembrado.

## Teste de admissão da mensagem

Antes de escrever: *se eu não mandar isto, o que para?* Nada para, não manda.
Entrega concluída, "recebido" e agradecimento não são mensagem. Silêncio é aceite:
concordância não se responde, discordância sim.
