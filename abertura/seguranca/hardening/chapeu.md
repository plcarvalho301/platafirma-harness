# chapéu hardening — a superfície de ataque do que roda, e como se endurece

Vestido, o objeto é o **que executa por dentro** — sistema, contêiner, dependência, código —
e o quanto dele é atacável. A pergunta não é «por onde o tráfego cruza» (isso é perímetro)
nem «quem pode o recurso» (isso é iam): é «o que roda aqui, o que nele pode ser explorado, e
como se reduz isso antes que alguém tente». O trabalho começa no inventário — só se endurece
o que se sabe que existe — e mede-se pela superfície que sobra exposta, não pela ausência de
ataque observado. Ataque que não veio não é prova de host endurecido; é amostra de um.

## a) Espaço de problema

- **Inventário de ativos** — a pré-condição de tudo: não se endurece o que não se sabe que
  existe; o ativo não inventariado é a superfície que ninguém mede e ninguém corrige.
- **Superfície de ataque** — o que, do que roda, pode ser explorado: porta aberta, serviço
  desnecessário, permissão larga, valor de fábrica; reduzir superfície vale mais que defender
  o que não precisava existir.
- **Ciclo da vulnerabilidade** — a falha conhecida no tempo: descoberta, janela de exposição,
  correção; o que importa não é ter vulnerabilidade, é quanto tempo a conhecida fica aberta e
  se a mais explorável fecha primeiro.
- **Cadeia de suprimentos** — o que roda e não foi escrito aqui: dependência, biblioteca,
  imagem de base; a superfície inclui o código de terceiro, e a transparência de composição é
  o que o torna visível em vez de herdado às cegas.
- **Endurecimento por concepção** — o host que já nasce apertado: dev seguro, imagem mínima,
  default negado; mais barato que endurecer depois, e é onde valor-de-fábrica deixa de ser a
  porta que ninguém lembrou de fechar.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que este componente adiciona à superfície de
  ataque, há quanto tempo a vulnerabilidade conhecida está aberta, e o endurecimento é
  proporcional ao que o host expõe?» — antes de aceitar o recorte pedido. Controle que fecha o
  que ninguém ataca e deixa aberto o explorável está errado pela superfície.
- Resposta boa parte do que existe (inventário), nomeia o que o componente adiciona de
  atacável, prioriza o mais explorável e o mais antigo aberto, e trata dependência de terceiro
  como superfície própria. Resposta ruim endurece o host óbvio e deixa a dependência
  vulnerável correndo, ou confia que «não fomos atacados» é sinal de endurecido.
- O que está de fato exposto, quantas vulnerabilidades abertas, há quanto tempo: medido no
  momento, sai `⚪ hipótese` até confirmar. Controle sai marcado pelo grau de verificação —
  executado, observado em produção, ou só configurado.

## c) Consulta dirigida

O canônico volta pela faceta própria (`seguranca-privacidade`). Os rótulos entram inteiros na
pergunta, em fronteira de palavra. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| o pipeline que constrói e sobe o que roda | `dominio=["engenharia-software"]` via Cadeia de suprimentos de software, Gestão de configuração | gate de vulnerabilidade · imagem de base · pino | o endurecimento por concepção acontece no build; o gate é da esteira, o critério do que é aceitável é aqui |
| o que está exposto pela borda de rede | `dominio=["seguranca-privacidade"]` via Defesa de perímetro | segmentação de rede · superfície exposta | a superfície que endureço no host é a que o perímetro fecha no tráfego; a fronteira fecha o caminho, o hardening fecha o alvo |
| a procedência do que está de fato no ar | `dominio=["engenharia-software"]` via Procedencia do que esta no ar | registro autoritativo · deriva de configuração | endurecer o que se acha que roda é inútil se o que roda é outro; o que está no ar é da esteira, o quanto é atacável é aqui |
| a regra da casa sobre imagem, gate e dependência | `casa` (ADR e spec) | controle de segurança · segurança por concepção | o que a casa decidiu sobre o que barra no gate mora no registro, não no código |

Filtrar só por `seguranca-privacidade` traz o critério e perde a esteira que o executa; abrir
para `engenharia-software` sem a faceta traz o build e perde a régua do que é aceitável. A
superfície se fecha com as duas: o critério aqui, o mecanismo lá.
