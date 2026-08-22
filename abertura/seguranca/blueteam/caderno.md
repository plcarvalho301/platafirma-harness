# caderno — seguranca / blueteam

## Login wall na raiz e indistinguivel de site vazio para qualquer crawler

Um hostname cuja raiz responde redirect-para-autenticacao com corpo vazio bate na
definicao literal de "conteudo insuficiente" dos produtos de URL filtering. Na
Palo Alto a categoria e `insufficient-content` e a acao que a propria fabricante
recomenda e block. Nao e especifico dela: Fortinet, Zscaler, Netskope e Umbrella
tem equivalente, varios ligados por padrao.

Consequencias que nao sao obvias na hora:
- O bloqueio acontece do lado do visitante. Sem log nosso, sem bounce, sem aviso.
  Perda silenciosa — nao ha sinal a monitorar.
- `insufficient-content` e `newly-registered-domain` (registro ha menos de 32
  dias) NAO aceitam pedido de recategorizacao na Palo Alto: sao system-defined ou
  atribuidas dinamicamente. Pedir reclassificacao nessas duas e caminho morto; a
  saida e custom URL Category no firewall de quem bloqueia, ou mudar o que a raiz
  serve.
- Categoria e por hostname, atribuida quando o crawler passa em CADA um. Dois
  hostnames com comportamento identico hoje podem ter carimbos diferentes so por
  idade. Hostname sem carimbo cai em `unknown`/`not-resolved`, categoria distinta
  e comumente permitida — logo "passa hoje" nao significa "esta limpo", significa
  "ainda nao foi olhado".

Correcao estrutural: raiz publica com conteudo real, gate comecando no path da
aplicacao. Nao afrouxa autenticacao nenhuma — muda so o que o anonimo recebe.

## Atras de CDN anycast, excecao por IP e larga e frágil ao mesmo tempo

Todos os hostnames sob um mesmo proxy de CDN resolvem para os mesmos poucos IPs
anycast. Liberar por IP no firewall de um terceiro (a) libera o front inteiro da
CDN, com milhoes de destinos junto, (b) provavelmente nao produz efeito, porque
URL filtering decide por hostname/SNI e nao por IP de destino, e (c) morre em
silencio quando a CDN troca o IP. Quando alguem propuser liberacao por IP, o
pedido esta no eixo errado: o certo e entrada por hostname em custom URL Category.

## Diante de "por que A passou e B nao", medir A e B antes de teorizar

Padrao de erro observado e caro: explicar assimetria com estrutura inventada
(regra, lista, excecao) quando o dado que a distinguiria nunca foi coletado.
O teste barato que resolve quase sempre: buscar os dois hostnames anonimamente,
lado a lado, e comparar status, headers, destino de redirect e robots.txt. Se
vierem identicos, a causa nao esta no que servimos — esta no outro lado, e
qualquer teoria sobre a nossa configuracao e ruido.

## Chapeu que EXECUTA se descreve por oficio, nao por regua

Pedido para listar o que uma linha de execucao precisa saber — skill, conceito,
vocabulario — puxa de mim o vocabulario de DECISAO: norma, controle, conformidade,
severidade, tipologia. Medido em 17/08: a lista saiu inteira de auditoria, sem uma
linha de shell, systemd, permissao de arquivo ou depuracao de codigo alheio, que e
com o que o executor passa o dia. O dono cortou, e a correcao dobrou a lista.

Teste barato, item a item, antes de entregar: isto e uma REGUA sob a qual ele
responde, ou uma FERRAMENTA com a qual ele mexe? Lista sem nenhuma ferramenta
descreve quem audita o trabalho, nao quem o faz.

Corolario: o mesmo assunto tem os dois vocabularios e eles nao se substituem.
Inteligencia de ameaca e regua (decide o que tratar primeiro); tatica e tecnica
adversaria e ferramenta (descreve o comportamento que se procura no log). Entregar
a regua no lugar da ferramenta passa em qualquer revisao de forma e nao habilita
ninguem a executar nada.
