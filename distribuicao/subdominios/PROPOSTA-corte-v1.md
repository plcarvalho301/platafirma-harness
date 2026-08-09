# Subdomínios — corte v1

Substitui: distribuicao/subdominios/PROPOSTA-corte-v0.md (2026-08-09)

Recorte de prateleira para os dez domínios da coleção `firma`. Propõe a grade,
não a designação: nenhuma obra é pré-classificada aqui. Quem designa é a cadeira
dona do domínio.

Grade original: claudinha-produto. Emendas: claudinho-TI, claudinho-IA,
claudinho-arquiteto, claudinho-conhecimento, claudinho-seguranca.
Consolidação: claudinha-gestao-estrategica. Passe de rótulo:
claudinho-conhecimento. O modelo de autorização que consome esta grade é de
claudinho-seguranca:
https://wiki.platafirma.org/index.php/PlataFirma:Sec/politica-de-autorizacao

Donos de domínio: `distribuicao/README.md`, seção "Donos de domínio".

## Régua

Teto de **6 subdomínios por domínio**. O subdomínio é eixo de atuação do modelo
de autorização, e a pergunta que corta é:

> O que aqui dentro não pode ser lido por quem não trabalha exatamente com isto?

Não é "onde se acha isto". Onde as duas perguntas dão o mesmo corte — a maioria
dos casos — nada muda; onde divergem, vence a de restrição. A navegação fina
entre assuntos é da teia de conceitos, não daqui.

Quatro regras de corte:

1. **Corta por assunto**, não por natureza do texto — "norma" e "livro-texto"
   não são prateleiras, são espécie de obra e já existem como campo próprio.
2. **Partição estrita.** Uma obra pertence a um subdomínio só. Duas prateleiras
   para a mesma obra quebram a restrição de leitura.
3. **Prateleira sem trabalho previsto não existe.** Subdomínio vazio some da
   grade quando nada na organização o alimenta. Vazio com frente declarada
   permanece: ali o vazio é diagnóstico de lacuna de aquisição, não de grade
   errada, e apagar a prateleira apaga o sinal. Subdomínio sem nenhuma restrição
   declarada não é vazio nesse sentido — não se funde por isso.
4. **Mesma gramática entre domínios**, salvo domínio de estudo puro. O leitor
   que troca de domínio de trabalho troca de assunto, não de lógica de
   organização.

### Quatro regras que a v1 institui

5. **Troca de domínio se declara em separado.** Obra que muda de domínio, e não
   de prateleira, sai em bloco próprio com o passe da cadeira que a recebe. É
   outra coluna e outra decisão.
6. **Obra geral fica no domínio, sem subdomínio, de propósito.** Não há dívida
   de designação a cobrar, nem meta de zerar. Efeito no eixo de autorização,
   medido em `rag/rag_extractor/runtime.py` (`Scope.sql`): o filtro é
   `AND c.subdominio = ANY(...)` e NULL não casa com `= ANY` — busca por domínio
   alcança a obra geral, busca por subdomínio nunca a entrega. O default é
   **negar por mecânica**, não por política. Obra sem subdomínio não fica mais
   visível: fica visível no recorte largo e invisível no estreito.
7. **Domínio e subdomínio são filtros independentes** no mesmo `Scope.sql`, não
   um par. Chamada que filtra só por subdomínio cruza domínios — logo slug
   idêntico em dois domínios é colisão de recuperação, não ambiguidade de
   leitura.
8. **A grade despacha como hipótese.** Vazio observado hoje não prova ausência
   de trabalho: prova ausência de designação (no domínio `ia`, 49% das obras não
   têm subdomínio). Ordem: despachar, designar, e só então fundir o que
   continuar vazio.

## A grade

### seguranca-privacidade (179 obras · hoje 9 subdomínios)

| subdomínio | escopo |
|---|---|
| `governanca-e-risco` | política, framework de controle, gestão de risco, certificação, papel de conselho, norma de sistema de gestão |
| `identidade-e-acesso` | identidade, autenticação, federação, autorização, zero trust |
| `criptografia` | algoritmo, chave, módulo criptográfico, PQC, homologação |
| `privacidade-e-dados-pessoais` | LGPD e GDPR, encarregado, anonimização, ciclo de vida do dado pessoal |
| `defesa-de-plataforma` | aplicação, container, rede, host, hardening, cadeia de suprimento |
| `deteccao-e-resposta` | incidente, forense, continuidade, inteligência de ameaça, teste ofensivo |

Absorve os nove atuais sem redesignar obra: `seg-governanca-controles` →
`governanca-e-risco`; `seg-acessos` → `identidade-e-acesso`; `seg-cripto` →
`criptografia`; `seg-dados-privacidade` → `privacidade-e-dados-pessoais`;
`seg-plataforma-aplicacoes` + `seg-redes` + `seg-operacional` →
`defesa-de-plataforma`; `seg-deteccao-resposta` + `seg-ofensiva` →
`deteccao-e-resposta`.

### capacidade-estatal (130 · hoje 4)

Grade atual mantida, **com os slugs atuais**: `ce-fundamentacao` (44),
`ce-implementacao` (35), `ce-normativo` (26), `ce-prescritivo` (25). Zero obras
sem subdomínio.

Corta por natureza do texto porque é domínio de estudo puro, não domínio de
trabalho — a exceção declarada da regra 3. Aqui a prateleira separa profundidade
de leitura, não área de atuação.

**A exceção alcança o rótulo, não só o critério.** Sem o prefixo, os quatro
rótulos ficam genéricos e dois deles (`normativo`, `prescritivo`) viram
homônimos de espécie de obra, que é campo próprio — a regra 1 é justamente
contra isso. Pela regra 7, slug genérico é também risco de colisão entre
domínios em busca filtrada só por subdomínio. O prefixo `ce-` é o que segura as
duas coisas, e mantê-lo custa zero migração contra 130 obras redesignadas.

### ia (65 · hoje 7, um vazio)

| subdomínio | escopo |
|---|---|
| `fundamentos-de-modelo` | arquitetura de modelo, treino, quantização, contexto longo |
| `recuperacao-e-busca` | RAG, embedding, ranqueamento, **avaliação de recuperador** |
| `agentes-e-harness` | agente, skill, engenharia de contexto, ferramenta, multiagente |
| `infra-e-serving` | execução local, formato de peso, integração, protocolo de ferramenta |
| `avaliacao-e-governanca` | eval e benchmark **de modelo**, risco de modelo |
| `produto-baseado-em-modelo` | concepção, lançamento e melhoria de produto sobre modelo |

Desempate entre as duas prateleiras de avaliação: **o objeto avaliado decide.**
Avaliar recuperador é `recuperacao-e-busca`; avaliar modelo — capacidade,
segurança, benchmark — é `avaliacao-e-governanca`.

Norma de sistema de gestão de IA (ISO/IEC 42001 e parentes) **não fica aqui**:
é sistema de gestão, mesma família da 27001, e vai para
`seguranca-privacidade/governanca-e-risco`.

`produto-baseado-em-modelo` nasce vazio (medido: `ia-produto`, 0 obras). O vazio
é pedido de aquisição, e o remit é de **claudinha-produto** dentro do domínio de
claudinho-IA — quem encomenda a aquisição é ela.

Absorção: pendente de claudinho-IA. `ia-fundamento` → `fundamentos-de-modelo`;
`ia-rag` → `recuperacao-e-busca`; `ia-agente` + `ia-harness` →
`agentes-e-harness`; `ia-infra` + `ia-integracao` → `infra-e-serving`;
`ia-produto` → `produto-baseado-em-modelo`. `avaliacao-e-governanca` não absorve
nenhum dos sete: falta declarar se puxa as obras de eval hoje em `ia-rag` ou se
nasce vazia.

### inteligencia (49 · hoje nenhum)

| subdomínio | escopo |
|---|---|
| `doutrina-e-analise` | técnica analítica estruturada, psicologia da análise, doutrina |
| `marco-legal-e-controle` | lei, decreto orgânico, controle externo, composição de sistema |
| `politica-e-estrategia` | política e estratégia nacional, plano, portaria de diretriz |
| `protecao-do-conhecimento` | infraestrutura crítica, área sensível, credenciamento, salvaguarda |

Dono provisório: Pedro. Passa à cadeira de inteligência quando ela for criada,
depois de F6.

### estudos-ontologias (52 · hoje 3)

| subdomínio | escopo |
|---|---|
| `fundamentos-ontologicos` | ontologia de fundamentação, lógica descritiva, categoria formal |
| `engenharia-de-ontologia` | construção, alinhamento, avaliação, linguagem de representação, teoria de grafo como instrumento |
| `organizacao-do-conhecimento` | vocabulário controlado, taxonomia, tesauro, arquitetura de informação |
| `arquivistica-e-registro` | descrição arquivística, requisito de sistema de registro, política de arquivo |
| `cognicao-e-aprendizagem` | aprendizagem, memória organizacional, prática reflexiva, resolução de problema |

Régua da separação entre a terceira e a quarta: a primeira governa
**vocabulário** (como as coisas se chamam e se relacionam — Z39.19, SKOS, VCGE,
DCAT-BR); a segunda governa **documento** (o que se guarda, sob que requisito e
por quanto tempo — e-ARQ, ISAD(G), NOBRADE, Lei 8.159, Decreto 4.073).

Absorção: `onto-fundamento` (8) → `fundamentos-ontologicos`; `onto-engenharia`
(7) → `engenharia-de-ontologia`; `onto-engenharia` (3: ISAD(G) pt+en, NOBRADE) →
`arquivistica-e-registro`, que corrige classificação errada vigente;
`onto-modelos` (2) → `engenharia-de-ontologia`.

Sexto slot deixado vago de propósito: prateleira se abre quando o trabalho
aparece, não para ocupar teto.

### engenharia-software (51 · hoje 5, um vazio)

| subdomínio | escopo |
|---|---|
| `artesania-e-design-de-codigo` | padrão, refatoração, teste, legado, qualidade do código escrito |
| `entrega-e-operacao` | pipeline, DORA, confiabilidade, observabilidade, patch |
| `gestao-de-servico-de-ti` | ITIL, FitSM, COBIT, CMMI, catálogo de serviço |
| `dados-e-persistencia` | engenharia de dados, streaming, banco, formato de arquivo |
| `interfaces-e-integracao` | REST, contrato de API, protocolo de interoperação, BFF |
| `front-end` | modelo de renderização (servidor, cliente, híbrido), framework e biblioteca de componente, build e pipeline de front, distribuição de design token, topologia do repositório de cliente, SDK de cliente |

Rótulo `front-end` sem sufixo: `front-end-e-interface` colidia com
`interfaces-e-integracao` no mesmo domínio, e "interface" nesta organização é
palavra de claudinha-produto. Lido composto com o domínio,
`engenharia-software / front-end` já diz engenharia de front-end. O vazamento
com design não é defeito a evitar: design é o lado de claudinha-produto,
front-end é o de claudinho-TI, e a fronteira vaza por natureza.

`front-end` nasce **vazio** — zero obras, medido em 09/08. É remit nomeado de
claudinho-TI com frente no roadmap: o vazio é pedido de aquisição, regra 3.
Renomeia o slug `engenharia-front-end`, que já existe com zero obras — sem custo
de migração.

Design token: obra que o trata como **decisão de design** vai para
`produtos-digitais/design-de-interacao`; obra sobre como ele é construído e
distribuído fica aqui. A prateleira segue o assunto da obra, não o artefato.

Absorção: `artesania-software` (4) → `artesania-e-design-de-codigo`;
`engenharia-dados` (2) → `dados-e-persistencia`; `engenharia-front-end` (0) →
`front-end`; `gestao-engenharia` (16) → **parte** entre `entrega-e-operacao` e
`gestao-de-servico-de-ti`.

Regra da partição de `gestao-engenharia`, para execução por terceiro:

- Assunto é o **fluxo de entrega** — DORA, Accelerate, trunk-based, feature
  toggle, confiabilidade, observabilidade, patch → `entrega-e-operacao`.
- Assunto é o **arranjo de serviço** — ITIL, FitSM, COBIT, CMMI, catálogo de
  serviço, processo de mudança e incidente → `gestao-de-servico-de-ti`.
- Ambíguo entre as duas: vence `gestao-de-servico-de-ti`, porque a pergunta que
  corta é de restrição de leitura e o arranjo de serviço tem público mais
  estreito.

### produtos-digitais (41 · hoje 2)

| subdomínio | escopo |
|---|---|
| `descoberta-e-estrategia` | discovery, posicionamento, trabalho a ser feito, armadilha de build |
| `design-de-interacao` | usabilidade, heurística, affordance, interação humano-sistema, design token como decisão |
| `especificacao-e-entrega` | história de usuário, mapeamento de impacto, recorte de escopo, caso de uso |
| `produto-publico-digital` | usuário de serviço público, lacuna projeto-realidade, direito do usuário |

Absorção: pendente de claudinha-produto (13 obras hoje classificadas).

### arquiteturas (37 · hoje 4)

| subdomínio | escopo |
|---|---|
| `decisao-arquitetural` | registro de decisão, conhecimento arquitetural, atributo de qualidade |
| `estilos-e-decomposicao` | microsserviço, modularidade como teoria, evento, sistema distribuído, topologia de integração |
| `modelagem-de-dominio` | DDD, contexto delimitado, modernização por fronteira |
| `arquitetura-de-dados` | governança de dados, malha de dados, maturidade, política de dado aberto |
| `arquitetura-corporativa-e-processo` | arquitetura corporativa, processo de negócio, capacidade |

`arquitetura-de-dados-e-negocio` parte em duas: era o único slug da grade que
nomeava duas disciplinas, quem lê DMBOK e Data Mesh não é quem lê TOGAF e
BIZBOK, e as duas nascem povoadas (5 e 4 obras).

Regra de desempate interna, declarada por claudinho-arquiteto: obra que ensina o
**processo de decidir** e atributo de qualidade vai para `decisao-arquitetural`;
obra que ensina **um estilo** vai para `estilos-e-decomposicao`.

Fronteiras cedidas, por escrito:

- **Desenho de time, lei de Conway, isomorfismo** → `gestao-organizacional/
  estrutura-e-topologia`. A prateleira é de quem decide sobre pessoas;
  `estilos-e-decomposicao` consome Conway como insumo, não como matéria.
- **Contrato de API e protocolo de interoperação** (REST, OpenAPI) →
  `engenharia-software/interfaces-e-integracao`. Fica aqui a topologia: qual
  componente fala com qual e por qual estilo.
- **Qualidade do código escrito** (Ousterhout) →
  `engenharia-software/artesania-e-design-de-codigo`. Modularidade como teoria
  (Parnas, Baldwin & Clark) fica aqui.
- **Systems thinking mole** (Checkland) → `gestao-organizacional`.

Absorção: pendente de claudinho-arquiteto (15 obras hoje classificadas).

### gestao-organizacional (34 · hoje 3, dois vazios)

| subdomínio | escopo |
|---|---|
| `estrategia-e-resultado` | estratégia, objetivo e resultado-chave, medição, portfólio |
| `estrutura-e-topologia` | desenho de time, lei de Conway, estrutura organizacional, isomorfismo |
| `governanca-institucional` | governança pública e corporativa, conselho, norma de governança |
| `trabalho-e-fluxo` | fluxo de trabalho, produtividade, regime de trabalho, execução pessoal |
| `papeis-e-competencias` | desenho de papel, remit e fronteira, competência, gestão de pessoas |

`papeis-e-competencias` entra porque RH é gerência declarada de
claudinha-gestao-estrategica — persona, remit, fronteira — e a v0 não tinha
prateleira para ela.

Absorção: `gestao-pessoas` (1) → `papeis-e-competencias`.

Sexto slot vago de propósito.

### platafirma (2)

Sem corte. Dois itens não sustentam prateleira. Dono: claudinho-conhecimento.

## Troca de domínio (regra 5 — coluna separada)

| obra | de | para | passe |
|---|---|---|---|
| `microsservicos` (1) | `engenharia-software` | `arquiteturas/estilos-e-decomposicao` | claudinho-arquiteto, por remit: quem decompõe é o arquiteto |
| *Knowing when to stop: insights from ecology for building catalogues* | `estudos-ontologias` | `curadoria-acervo` | claudinho-conhecimento, na execução |
| Ousterhout, Brooks, Checkland, cartilha de governança vol. 3 | `arquiteturas` | a declarar | claudinho-arquiteto, com claudinho-conhecimento |

## O que fica em aberto

- **Precedência entre domínios** quando a obra cabe nos dois (ISO 42001 é o caso
  que a levantou). Decisão do dono; sem ela, a mesma norma vai para prateleiras
  diferentes conforme quem classifica.
- **Absorção pendente**: `ia`, `arquiteturas`, `produtos-digitais`.
- **Aquisição** para `front-end` (claudinho-TI) e `produto-baseado-em-modelo`
  (claudinha-produto).
