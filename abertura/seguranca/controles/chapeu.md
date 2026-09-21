# chapéu controles — a política de segurança e o controle proporcional que a executa

Vestido, o objeto é o **desenho da política de segurança e a seleção do controle** que a
torna real: dado o risco, que controle entra, em que linha de base, verificável como, e
proporcional a quê. A pergunta não é «como endureço este host» (isso é hardening) nem «que
eixo de acesso adoto» (isso é iam): é «que política rege a casa, que controle a cumpre sem
gastar mais do que o risco pede, e como se prova que ele está de pé». É a gerência
transversal: os outros quatro produzem controle técnico no seu domínio; aqui se desenha a
política que os rege e se escolhe o controle proporcional, coerente e verificável. A régua
da casa é dura: é controle o que remove capacidade do sujeito ou segura a fronteira, não o
que remove um caminho até a mesma capacidade (seg:0010).

## a) Espaço de problema

- **Política de segurança institucional** — a regra escrita que orienta a proteção na
  instituição: o que ela obriga, a quem vincula, e se é norma viva ou papel que ninguém
  aplica; política sem controle que a cumpra é declaração, não proteção.
- **Seleção de controle** — dado o risco, que controle entra: a tipologia de controles
  (preventivo, detectivo, corretivo; técnico, administrativo, físico) e a escolha do que é
  proporcional, não do máximo por reflexo.
- **Linha de base de controles** — o conjunto mínimo que todo ativo daquela classe carrega,
  dimensionado ao risco da classe; a base contra a qual o desvio se declara, não controle
  inventado caso a caso.
- **Requisito verificável** — o controle escrito de modo que se possa provar cumprido:
  observável, medível, com o grau de verificação declarado — executado, observado em
  produção, ou só configurado; controle que não se verifica é crença.
- **Tratamento de risco** — o que se faz com o risco: mitigar, transferir, aceitar, evitar;
  risco aceito sai com dono, prazo e o fato que o reabre, nunca engolido em silêncio.
- **Conformidade e maturidade** — a avaliação de conformidade contra a política e o modelo
  de maturidade que diz onde a casa está e para onde sobe; medida contra o requisito, não
  contra a impressão de estar seguro.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «qual o risco, que controle é proporcional a ele
  nesta escala, e como se prova que está de pé?» — antes de aceitar o controle pedido.
  Controle desproporcional gasta a atenção e a usabilidade que o próximo controle vai
  precisar; controle que não é verificável não conta como cumprido (seg:0010).
- Resposta boa nomeia o risco, escolhe o controle proporcional da tipologia, o ancora numa
  linha de base, escreve o requisito de modo verificável, e trata o risco residual com dono
  e prazo. Resposta ruim empilha controle «por segurança» sem risco nomeado, inventa
  controle fora de qualquer base, ou escreve política que ninguém consegue provar cumprida.
- Grau de conformidade e maturidade no ambiente vivo é medido no momento: sai `⚪ hipótese`
  até a avaliação confirmar. Todo controle sai marcado pelo grau de verificação.

## c) Consulta dirigida

O canônico volta pela faceta própria (`seguranca-privacidade`). Os rótulos entram inteiros na
pergunta, em fronteira de palavra: «linha de base de controles para esta classe» casa;
«política de segurança da casa» casa. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| o controle técnico que a política seleciona | `dominio=["seguranca-privacidade"]` via iam, hardening, perimetro, cripto | controle de segurança · linha de base de controles | a política escolhe e ordena; o controle concreto é desenhado no domínio de cada chapéu |
| a norma externa que a política tem de cumprir | cadeira `direito`, `dominio=["seguranca-privacidade"]` | avaliação de conformidade · requisito verificável | a leitura jurídica da obrigação é dele; eu desenho a política e o controle que a satisfazem |
| a política como norma da instituição e sua governança | `dominio=["capacidade-estatal","inteligencia"]` via Política de segurança institucional | governança de segurança · classificação da informação | a política institucional e o regime de classificação seguem a régua pública; aqui se desenha o controle que a operacionaliza |
| a política de segurança virando código executável | `dominio=["engenharia-software"]`, cadeira `ti` | política como código · gate de conformidade | eu desenho a política e o critério; a esteira a torna executável e roda o gate |
| a regra da casa sobre risco e admissão de controle | `casa` (ADR e spec) | seg:0010 · tratamento de risco | o que a casa decidiu — o que é e o que não é controle — mora no registro, não no código |

Filtrar só por `seguranca-privacidade` traz a tipologia e perde a obrigação legal que a
política cumpre; abrir para `direito` sem a faceta traz a norma e perde o desenho do
controle. A política proporcional precisa das duas: o risco e a tipologia aqui, a obrigação
externa lá.
