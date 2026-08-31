# caderno arquiteto — lições duráveis do desenho arquitetural

Durável: continua verdadeiro depois que o assunto morrer, e a próxima fita pagaria
para re-derivar. Entrada nova substitui a que contradiz; o histórico é o git.

## Capacidade na cadeia capacidade:verbo:ferramenta É a capability de negócio BIZBOK

O termo "capacidade" da lógica `capacidade : verbo : ferramenta` SEMPRE foi a
**business capability do BIZBOK** — a mesma coisa do mapa em
`platafirma-arquitetura/docs/arquitetura-negocio-operacao.md` (§1, 20 capacidades em
4 tiers, régua `arq:0059`). Não é taxonomia própria do ferramental.

- Diferença é só de nomenclatura, não de conceito: `iam == acesso`,
  `gestao-de-motores == motor`. Ao casar verbo/stack com capacidade, o alvo é o rótulo
  BIZBOK do mapa de negócio, não um vocabulário paralelo do golden record.
- Modo de falha observado (fita 26/08/2026): tratar o golden record de
  `acervo.ferramental` como se a coluna "capacidade" fosse taxonomia interna do
  tooling, e não a capability de negócio. Causa: distância semântica no RAG. Sintoma:
  procurar correspondência dentro do catálogo de ferramental em vez de no mapa BIZBOK.
- Regra prática: capacidade órfã de stack/verbo resolve-se contra o mapa de negócio
  (`§1` e os níveis 2), nunca inventando capability nova sem passar pela régua de
  `arq:0059` (capacidade é única na org; duplicada funde, ambígua parte — ato da mesa
  gerência `negocio`).
- Corolário BIZBOK princípio 1: sistema não é capacidade. Tela, corpo de colaborador,
  artefato de front são INSTÂNCIA que serve uma capability existente — não capability
  nova. (Ex.: jaiminho serve `mensagem-externa`; toda "tela" é `canal/exposicao` sobre
  o objeto de outra capacidade.)

## Resolução de identidade de cadeira: um ponto canônico, uma fonte (o ledger)

A tradução "nome do ator → cadeira" tem UM ponto canônico correto:
`chat/comum/cadeiras.py::sufixo_canonico`. É o único resolvedor que lê a fonte
canônica (ledger de vínculo, `registro/eventos-org.jsonl`, arq:0073) e aceita todas
as formas de entrada — sufixo, slug com prefixo, MXID/localpart e, desde #2431, o
nome humano (alias). Qualquer outro resolvedor é candidato a divergir.

- Fonte única de "quem é cadeira" é o LEDGER DE VÍNCULO, nunca um arquivo de roster
  mantido à mão. Hazard medido (fita 27/08/2026): existiam 3 resolvedores divergentes
  (`monta-sessao::_sufixo_sem_prefixo`, `fila::canoniza_persona`, `comum::sufixo_canonico`)
  e 2 fontes (ledger vs `fila/.personas`). A fonte paralela envelhece em silêncio e a
  divergência vira caixa fantasma — destinatário aceito que ninguém lê.
- Nome humano (alias) é a ÚLTIMA forma tentada, atrás de sufixo/slug/MXID reais, para
  que uma forma já válida nunca seja sequestrada. Primeiro-nome só resolve se único
  entre os aliases; homônimo exige o nome inteiro. Acento e caixa se dobram.
- Colapsar os 3 resolvedores em 1 lib compartilhada cruza venv (empacotamento) e é
  decisão canônica → do dono; adiado. Até lá, o mínimo que mata a divergência sem
  refatorar é unificar a FONTE: todo resolvedor lê o ledger (feito na fila, #2431).
- Corolário: participante (jaiminho) não é cadeira e não está no ledger de vínculo;
  fica em constante local do consumidor até a lib compartilhada existir.

## Fronteira instância-individual × instância-de-órgão vive no plano de acesso, não no de conhecimento

Medido na fita 27/08/2026 (produtização #180). Registro canônico: `platafirma-arquitetura/docs/kernel-platafirma-rascunho.md` + `docs/fronteira-tecnica-produtizacao.md`.

- O módulo `conhecimento` (wiki+RAG+acervo+ontologia) e o MOTOR do harness são **invariantes** entre a instância-de-um e a de-órgão. O delta de órgão é inteiro no **plano de identidade/acesso**: Keycloak passa de emissor de token de cadeira a **IdP de gente**, a grade concessão/PDP acorda (hoje vazia por decisão — falha fechada), e entra o namespace/lockdown da F5.
- O harness se parte **motor × personas** na MESMA linha MIREOT da ontologia (product-spec §4.2): motor (`ops-server`, `bin`, `mcp`, `sessao`, `politica-acesso`, `tooling`, `deploy-harness`) = plataforma; `abertura/<cadeira>`, `chat`, `registro` (ledger), `distribuicao`, `jaiminho` = instância. O corte às vezes passa POR DENTRO de um componente: `cadeiras.py` é motor, o ledger que ele lê é instância — produtizar o harness exige extrair o motor e tratar `abertura/`+`registro/` como pacote de instância.
- Keycloak no compose do core hoje só provisiona service accounts de cadeira (`client_credentials`, `provisiona-realm.sh`); o papel de IdP humano é o que o órgão exige. README do core chama IAM de "próximo épico" — scaffoldado, não vivo. Individual sobrevive sem Keycloak "de gente" (token de agente é até substituível por estático, product-spec §8).
- Régua de produto da casa (dono, 27/08): **não há venda** (dono é servidor público estável); norte é **adoção como valor público, foco APF**. Consequência arquitetural: `canal` é adoção/distribuição, nunca funil comercial; a fronteira produto×vendas da gap-de-estrategia (16/08) se dissolve.

## Conformidade de fóssil e alarme falso são a fábrica de Frankenstein

Lição do dono, fita 31/08/2026 — a maior de um mês e meio de vibecoding, nas palavras
dele. A causa raiz da degradação da codebase NÃO foi falta de check; foi check demais,
aplicado errado. Duas patologias, uma raiz:

- **Conformidade de fóssil** — rodar gate de conformidade retroativo sobre código legado
  intocado e "consertar" para passar. Cada conserto forçado sem alguém tocando aquele
  código por necessidade real adiciona camada que ninguém pediu. O Frankenstein nasce daí.
- **Alarme falso** — check que dispara sobre o que está de fato certo, e a "correção" do
  falso positivo estraga o que funcionava.

Regra que sai disso, e que reenquadra o gate do `arq:0089`:

- Gate só vale a pena quando **estrangula no contato** — reprova o que se está tocando
  agora, por trabalho real. Ligado como **varredura retroativa** sobre o parado, o mesmo
  gate vira a fábrica de Frankenstein que deveria evitar.
- **Fóssil intocado espera.** Não se refatora o que ninguém encostou só para satisfazer
  uma regra nova. A dívida fica visível (medida), não consertada à força.
- **Hiperfoco em check é modo de falha da cadeira**, observado pelo dono. Antes de propor
  ou implementar qualquer verificação automática, o ônus é provar que ela morde no
  contato e não vira varredura de fóssil nem alarme sobre o são.
- Corolário para o `conferir`: implementar a checagem do `arq:0089` foi **segurado de
  propósito** pelo dono. Check decidido não é check para já — a implementação espera o
  caso vivo, não a ansiedade de conformidade.

## Exceção arquitetural se funda na inadequação da tecnologia, não em reancoragem formal

Lição do dono, fita 31/08/2026 (minuta 0016/ADR 0090, exceção de grafo): formalismo não
se sobrepõe à inadequação absoluta da tecnologia — REST não foi feito para grafo, e isso
BASTA como fundamento da exceção. A reancoragem em fronteira-de-contexto que o arquiteto
tentou tinha a perna fraca à mostra (conceito é entidade do dados lida pelo motor da IA —
"mesmo contexto" não se sustentava) e era desnecessária: quando a tecnologia não serve a
forma do dado, a inadequação é o argumento, direto.

- Regra: o que ADMITE exceção a norma estrutural é a inadequação da tecnologia para a
  forma do dado/fluxo — nunca inconveniência, nunca custo de conformidade. A norma verga
  à natureza da tecnologia; o contrário ("enfiar token quântico no keycloak") é a norma
  falhando, não o implementador.
- Forma de registro (o-que-fica-fora · critério · porta de retorno) é higiene que mantém
  a exceção revisável — jamais fundamento para forçar conformidade.
- Salvaguarda ≠ fundamento: o read-model declarado (acoplamento visível no schema) segue
  como proteção operacional, sem carregar a justificativa da exceção.
