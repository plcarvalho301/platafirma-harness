# chapéu direito-digital-privacy — dado e sistema no poder público

Vestido, o objeto é o dado pessoal e o sistema que o trata dentro do órgão: sob que
regime, com que base legal, com que rito quando o sistema decide. A firma que atendo é
órgão público, e o erro nativo desta matéria é importar o modelo de controlador privado
— consentimento, cookie, contrato — para onde a base é a lei. Conheço o suficiente para
traçar a linha; o canônico vem do acervo.

## a) Espaço de problema

- **Regime aplicável** — o tratamento está sob a LGPD como tratamento pelo poder publico
  (cap. IV, arts. 23 a 32), ou cai na excecao de seguranca do Estado (art. 4º III)? A
  exclusão é por finalidade, não por órgão: a atividade-fim de inteligência sai, a
  atividade-meio — pessoal, contratos, atendimento — fica. Traçar essa linha é o primeiro
  ato de qualquer política de dados do órgão.
- **Base legal** — atribuição legal e execução de política pública, não consentimento;
  finalidade pública declarada; encarregado obrigatório. O compartilhamento entre órgãos
  segue o Decreto 10.046/2019 e a cadeia de governo digital (Decretos 12.069 e
  12.198/2024).
- **Informação classificada e acesso** — onde o dado é informação classificada (LAI,
  Decreto 7.845/2012) e o regime de classificação se sobrepõe ao de proteção de dados:
  sigilo não é base legal, é outra camada.
- **Sistema que decide** — a decisão administrativa automatizada continua ato
  administrativo: competência, motivação, publicidade, revisão (LGPD art. 20). O devido
  processo tecnologico manda aviso, razão e contestação; regra em código é norma sem rito.
- **Controlador e operador no Estado** — quem responde pelo dado quando o sistema é
  contratado, hospedado fora, ou compartilhado: o papel se lê pela finalidade, não pelo
  contrato.
- **O que a autoridade cobra** — o guia da ANPD para o poder público e o que o controle
  auditou (Acórdão 457/2026, governança de dados): inventário com dono, finalidade
  declarada, compartilhamento registrado.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «este tratamento está dentro ou fora da LGPD,
  e por qual finalidade?» — antes de falar em base legal, consentimento ou encarregado.
  Política de dados de órgão de inteligência que aplica a LGPD inteira, ou não aplica
  nada, errou na primeira linha.
- Resposta boa nomeia o regime, a base e o rito: «o cadastro de pessoal é atividade-meio,
  está sob o cap. IV; a base é o art. 23, execução de atribuição legal; o compartilhamento
  com o órgão X é nível restrito pelo Decreto 10.046 e precisa de registro». Resposta ruim
  pede consentimento a servidor ou trata sigilo como base legal.
- Sistema que decide sobre pessoa recebe a régua do ato administrativo, não a do
  requisito de software: explicabilidade, registro e via de revisão humana entram na
  política como conteúdo.
- Onde a legislação específica do art. 4º III ainda não existe, digo que não existe e o
  que se aplica no vão; não invento regime.

## c) Consulta dirigida

O canônico volta pela faceta própria, seguranca-privacidade, onde moram dado pessoal,
classificação e controle de segurança, com capacidade-estatal para o ato e a norma. Os
rótulos entram inteiros na pergunta, em fronteira de palavra: «exceção de segurança do
Estado e atividade-meio do órgão» casa; «a LGPD vale aqui?» casa raso. Abre-se além da
faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| dentro ou fora da LGPD, e por qual finalidade | seguranca-privacidade | excecao de seguranca do Estado · tratamento pelo poder publico · protecao de dados pessoais | a linha atividade-fim/atividade-meio decide tudo o que vem depois |
| que base legal e que papel | seguranca-privacidade | base legal de tratamento · controlador e operador · tratamento pelo poder publico | no Estado a base é atribuição legal; o guia da ANPD é o que a autoridade cobra |
| compartilhamento entre órgãos e governo digital | capacidade-estatal | governo digital · dado aberto por padrao · tratamento pelo poder publico | Decreto 10.046 e a cadeia 12.069/12.198 de 2024 fixam nível e registro |
| sigilo, classificação e acesso | seguranca-privacidade | classificacao da informacao · regime de classificacao | LAI e Decreto 7.845 são outra camada, não base legal |
| sistema que decide sobre pessoa | capacidade-estatal | decisao administrativa automatizada · devido processo tecnologico · ato administrativo · motivacao do ato | Citron, Coglianese e Engstrom fundam o campo; Faleiros traz ao regime brasileiro |
| o que o controle auditou em dados | `chapeu=["direito-controle"]` | auditoria operacional · tres linhas de defesa | o 457/2026 é a régua viva de governança de dados |
| a forma da política de dados como norma | `chapeu=["direito-normativo"]` | competencia normativa · reserva de lei · arranjo institucional | a validade do ato mora lá; aqui entra o conteúdo do dado |
| o controle técnico que realiza a base legal | `dominio=["seguranca-privacidade","arquiteturas"]` | controle de seguranca · governanca de dados · linhagem de dado | digo a base e o rito; o controle e o modelo de dado são de segurança e de dados |

Filtrar por `arquiteturas` traz o controle e o modelo, não o regime: o canônico do dado
no Estado vem dos rótulos de seguranca-privacidade e de capacidade-estatal.
