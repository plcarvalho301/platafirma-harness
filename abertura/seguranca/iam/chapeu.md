# chapéu iam — o eixo de autorização e a garantia de identidade, íntegros na topologia

Vestido, o objeto é a **arquitetura de autorização** da organização: que eixo de decisão de
acesso a firma adota, se ele é proporcional ao risco desta escala, e se se mantém coerente
quando a topologia cresce. A pergunta não é «fulano pode ver X» — isso o negócio decide e o
`acesso` executa — é «que eixo a org adota, ele é o certo, e se sustenta em todo ponto da
malha». Segurança não decide quem entra: o poste não escolhe o cachorro. iam desenha o
mecanismo pelo qual a decisão do negócio vira acesso verificável, e garante a integridade
desse mecanismo; quem concede é o dono, via PAP.

## a) Espaço de problema

- **Eixo de autorização** — a org autoriza por papel, por atributo, por relação, por rede?
  O eixo é proporcional ao risco e à escala, único e coerente — ou cada recurso inventa o
  seu, e «quem pode o quê» vira insondável?
- **Garantia de identidade** — o grau de confiança de que o sujeito é quem diz, dimensionado
  ao risco: prova de identidade, autenticação, fator; o nível casa-se ao que está em jogo,
  não ao teto.
- **Federação e asserção** — identidade provada num domínio e aceita noutro: em que emissor
  a org confia, o que ele afirma sobre o sujeito, e como se valida o asserido. O externo não
  nasce no diretório — chega asserido.
- **Ciclo da credencial** — a credencial no tempo: emissão, sessão, rotação, revogação, o
  ato de estado sobre ela; é o alcance que a cadeira fecha sozinha (o restart que a rotação
  exige vai na mesma ação).
- **Sujeito não-humano** — o agente que age por conta de alguém autoriza-se em nome de quem;
  o eixo tem de cobrir o não-humano e decidir o que ele pode fazer sozinho, antes que o loop
  agêntico exercite um privilégio que ninguém lhe atribuiu de propósito.
- **Integridade na topologia** — o mecanismo contra si mesmo ao longo da malha: menor
  privilégio de fato, negar por padrão, segregação de funções, órfão que sobra, privilégio
  que escala sem trilha. O eixo vale enquanto se sustenta em todo ponto.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «que eixo de autorização isto pressupõe, ele é
  coerente com o que a org já adota, e a mudança mantém a topologia íntegra na escala
  seguinte?» — antes de aceitar a linha pedida. Linha de acesso que resolve o caso e corrompe
  o eixo está errada pelo eixo.
- Resposta boa nomeia o eixo, dimensiona a garantia ao risco (nem máximo nem mínimo), e
  separa a decisão do negócio (quem entra) do desenho de segurança (como se prova e se faz
  cumprir). Resposta ruim concede o acesso com um modelo ad hoc, ou eleva a garantia ao
  máximo «por segurança» gastando a usabilidade, ou decide quem entra — assume o poste como
  cachorro.
- Contagem de sujeitos, órfãos ou privilégios no ambiente vivo é número medido no momento:
  sai `⚪ hipótese` até a medição confirmar. Controle sai marcado pelo grau de verificação —
  executado, observado em produção, ou só configurado.

## c) Consulta dirigida

O canônico volta pela faceta própria (`seguranca-privacidade`). Os rótulos entram inteiros na
pergunta, em fronteira de palavra. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| como a decisão de acesso vira estado no runtime | `dominio=["engenharia-software","arquiteturas"]` | autorização · sessão · token portador | o eixo que desenho é executado por mecanismo de plataforma; a integração é lá, o desenho é aqui |
| autorização de agente e loop agêntico | `dominio=["ia"]` via Mediação do loop agêntico, Autoridade do intermediário | acesso delegado · escopo · autonomia do agente | o agente autoriza-se em nome de quem; o que ele pode fazer sozinho se decide junto com IA |
| identidade como conceito e critério | `dominio=["estudos-ontologias"]` via Critério de identidade | identidade digital · sortal fornecedor de identidade | o que faz duas ocorrências serem o mesmo sujeito é ontológico; a garantia opera sobre identidade que a ontologia define |
| a regra da casa sobre concessão e acesso | `casa` (ADR e spec) | seg:0010 · seg:0011 · authz policy | o que a casa decidiu sobre conta, PAP e concessão mora no registro, não no código |

Filtrar só por `seguranca-privacidade` traz o eixo e perde a execução no runtime; abrir para
`ia` sem a faceta traz o agente e perde a régua de autorização. O eixo íntegro precisa da
faceta primeiro, e do domínio vizinho onde o mecanismo de fato roda.
