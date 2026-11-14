# Perímetro

Entidade: chapeu

## Espaço de problema

- Que controle de borda esta interface pede: o que se admite cruzar por ela, e o que se recusa?
- Onde a rede da organização encontra o que não é ela: que interface publicada é ponto de entrada e de saída, o que se expõe e o que se esconde?
- A saída é vigiada tanto quanto a entrada? Saída sem controle é o canal de exfiltração e de comando que passa despercebido.
- Se o controle de borda falhar, a segmentação de rede contém, ou quem passou anda por toda a malha (movimento lateral)?
- O que se vê quando algo cruza, e isso é distinto de bloquear? Ver o que passou é o que permite responder ao que o bloqueio não pegou.
- A confiança vem de onde o pedido chega, ou cada pedido prova quem é, mesmo vindo de dentro (zero trust)?

## Régua de resposta

Resposta boa nomeia a interface por onde o tráfego cruza, o controle de borda sobre ela e o que contém se ele falhar, vigia a saída tanto quanto a entrada e deixa rastro do que cruzou.

Resposta ruim bloqueia a entrada e esquece a saída, deixa a rede interna plana, ou crê que o perímetro basta.

## Consulta dirigida

- Política de filtragem e arquitetura com camadas de firewall: NIST SP 800-41.
- Segmentação: os guias de certificação CISSP e CySA+ trazem a matéria em nível de referência.
- Confiança que não vem da rede: a busca vai por zero trust e defesa em profundidade.
- A regra da casa sobre rede e isolamento: os registros de decisão, que se leem antes de propor regra de borda.

## Rótulos de busca

- rótulos: defesa de perímetro · segmentação de rede · movimento lateral · zero trust · defesa em profundidade · negar por padrão
- recorte de domínio: seguranca-privacidade
- homônimos: perímetro, que neste ramo é a borda de rede, e não o escopo de um projeto · fronteira, que é a fronteira de rede, e não a fronteira de um contexto delimitado · interface, que é a chamada que a casa publica e por onde o tráfego cruza a borda, e não a tela que a pessoa usa
