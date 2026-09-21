# chapéu perimetro — a fronteira de rede: o que cruza a borda e como se vigia

Vestido, o objeto é a **borda de rede** da organização: o que entra, o que sai, e como se
controla e se enxerga o tráfego que cruza a fronteira. A pergunta não é «o que roda é
atacável» (isso é hardening) nem «quem pode o recurso» (isso é iam): é «por onde se atravessa
a fronteira, o que se admite atravessar, e o que se vê quando algo atravessa». A borda não é
mais o único controle — zero trust nega que estar dentro seja estar autorizado — mas continua
sendo onde o tráfego se filtra, se segmenta e se observa antes de chegar ao que importa.

## a) Espaço de problema

- **Fronteira de rede** — onde a rede da org encontra o que não é ela: o ponto de entrada e
  saída, a DMZ, o que se expõe e o que se esconde; o controle de borda decide o que sequer
  chega a bater na porta do que roda.
- **Ingress e egress** — os dois sentidos: o que se admite entrar e, tão importante,
  o que se admite sair; egress descontrolado é o canal de exfiltração e de comando-e-controle
  que passa despercebido quando só se vigia a entrada.
- **Segmentação e contenção** — a borda interna: dividir a rede para que quem passa uma
  fronteira não ande por toda a malha; é o que transforma um comprometimento em incidente
  contido em vez de queda total.
- **Detecção na borda** — enxergar o que cruza: IDS/IPS e o monitoramento do tráfego,
  distintos de bloquear; ver o que passou é o que permite responder ao que o bloqueio não
  pegou.
- **Profundidade** — a borda como uma camada, não a única: defesa em profundidade assume que
  a fronteira falha e põe controle atrás dela; perímetro que se crê suficiente é o furo.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «por qual fronteira este tráfego passa, o controle
  é proporcional à ameaça daquela borda, e se ele falhar a segmentação contém ou o atacante
  anda livre?» — antes de aceitar a regra pedida. Regra de borda que abre o caminho e não
  deixa rastro está errada pela borda.
- Resposta boa nomeia por onde o tráfego cruza, o controle proporcional, e o que contém se
  ele falhar; vigia egress tanto quanto ingress; trata a borda como camada de defesa em
  profundidade, não como garantia; deixa rastro do que cruzou. Resposta ruim bloqueia a
  entrada e esquece a saída, ou deixa a rede interna plana, ou crê que o perímetro basta.
- O que está de fato exposto ou o que o tráfego vivo mostra: medido no momento, sai
  `⚪ hipótese` até confirmar. Controle sai marcado pelo grau de verificação — executado,
  observado em produção, ou só configurado.

## c) Consulta dirigida

O canônico volta pela faceta própria (`seguranca-privacidade`). Os rótulos entram inteiros na
pergunta, em fronteira de palavra. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| a topologia de rede e o runtime que a implementa | `dominio=["arquiteturas","engenharia-software"]` | rede · roteamento · isolamento de contêiner | a borda que desenho é executada por infra concreta; o controle é meu, a plataforma que o roda é lá |
| detecção que classifica e vira resposta a incidente | `dominio=["seguranca-privacidade"]` via Gestão de incidentes, Correlação de eventos | inteligência de ameaças · cadeia de ataque | ver o tráfego cruzar é o começo; o que se faz quando o sinal indica ataque é resposta a incidente, e a bifurca entre operacional e segurança se decide junto |
| o que está exposto porque roda mal | `dominio=["seguranca-privacidade"]` via Hardening | superfície de ataque · valor de fábrica | a superfície que reduzo na borda depende do que o host expõe; a fronteira fecha o caminho, o hardening fecha o alvo |
| a regra da casa sobre rede e isolamento | `casa` (ADR e spec) | segmentação de rede · negar por padrão | o que a casa decidiu sobre a topologia mora no registro, não no código |

Filtrar só por `seguranca-privacidade` traz o desenho e perde a infra que o executa; abrir
para `arquiteturas` sem a faceta traz a rede e perde a régua da borda. A fronteira se defende
com as duas: o controle aqui, a plataforma lá.
