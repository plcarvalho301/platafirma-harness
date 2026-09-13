# Perguntas do gabarito, em bloco colavel

Derivado de `gabarito.jsonl` por `tooling/avaliacao/gerar_colaveis.py`.
Nao editar aqui: pergunta se corrige no gabarito e este arquivo se regenera.

Cada bloco e uma pergunta inteira, pronta para colar no prompt. O alvo nao entra:
quem responde nao pode ver o gabarito.

As 118 do estrato T1 ficam de fora de proposito — sao auto-geradas a partir do
`section_id` e existem para a bancada casar por codigo, nao para alguem responder.

## Multistep — 30

Enunciado de varios passos, com alinea. E o estrato que mais custa a responder e o que mais separa arm bom de arm ruim.

**01. `claudinho-conhecimento-ms-01`**

```
O plano diretor manda publicar `plataforma.ttl` fora da instância, com os `dc:source` como
estão. Você assina a publicação. Abra o e-ARQ Brasil v2 no §8.1.1 e responda:

  (a) você mantém a citação como está — sim ou não?
  (b) se não: escreva o `dc:source` que entra no lugar;
  (c) a partição em seis famílias cai junto com a fonte, ou sobrevive sem ela?
```

**02. `claudinho-conhecimento-ms-02`**

```
Você quer ligar expansão de consulta no RAG: dado um filtro `trata_de = X`, expandir para o
fecho transitivo de `mais_amplo_id` acima de X.

  (a) dá para ligar amanhã — sim ou não?
  (b) ligando, sob que semântica, e o que acontece com recall e precisão?
  (c) não ligando, o que falta: dado, declaração ou decisão?
```

**03. `claudinho-conhecimento-ms-03`**

```
Você vai fechar a política de backup e restauração do acervo. Duas perguntas binárias,
justificadas pelo texto e não pela intenção do autor:

  (a) rodando HermiT sobre `plataforma.ttl` + `external-mireot.ttl`, com as 26 obras
      `wiki://` sem portador declarado, o reasoner acusa alguma coisa — sim ou não?
  (b) o backup do MinIO, sozinho, restitui o acervo inteiro — sim ou não?
```

**04. `claudinha-gestao-estrategica-ms-01`**

```
A diretoria aprovou adotar OKR em todos os times a partir do próximo trimestre, com o
EMPOWERED como manual oficial. Você revisa e aprova os key results de cada time no dia 1.

(a) Chega este KR: "concluir a migração do cadastro para a nova API até 30/09". Pelo
manual adotado, aprova ou recusa?
(b) Um diretor rebate: "OKR é técnica de fábrica, nasceu na Intel, funciona em qualquer
time". Ele está certo sobre a origem? Sim ou não.
(c) Se estiver certo, a régua do manual cai junto? Sim ou não.
(d) Um gestor te pergunta o que fazer com um subordinado de desempenho adequado e não
excelente. O acervo dá uma resposta só? Sim ou não.
```

**05. `claudinha-gestao-estrategica-ms-02`**

```
Adotamos Shape Up a partir do próximo ciclo. A diretoria recebe hoje um relatório mensal
com três números: (a) data prevista de cada item do backlog; (b) velocity do time;
(c) percentual de itens entregues no prazo.

Item a item, você mantém o relatório sem mudar o método? Sim ou não para cada.
E responda com número: quantas semanas do ano ficam disponíveis para trabalho programado?
```

**06. `claudinha-gestao-estrategica-ms-03`**

```
A diretoria quer aprovar orçamento para "chegar ao nível 3" em 18 meses, e o dossiê usa o
Accelerate como justificativa técnica. Você assina o parecer de investimento.

(a) O Accelerate sustenta o pedido como está formulado? Sim ou não.
(b) Existe no acervo medida com meta numérica que possa substituir "nível 3" no termo de
aprovação? Cite-a, ou declare que não existe.
(c) O parecer pode citar "quatro anos de pesquisa" sem mais nada? Sim ou não.
```

**07. `claudinho-TI-ms-01`**

```
O jurídico devolveu seu processo com um quesito único, e a resposta tem de ser sim ou não:
"este processo é contratação de solução de TIC, regida pela Instrução Normativa SGD/ME nº
94/2022?" O pregão está pautado; se a resposta for sim, falta a aprovação técnica prévia do
Órgão Central do SISP e o processo sai da pauta. Responda o quesito sustentando cada passo
no acervo, e diga em seguida se as cláusulas 4.19.2 e 6.11 do seu próprio ETP podem seguir
com a redação que têm.
```

**08. `claudinho-TI-ms-02`**

```
A auditoria fechou com você a adoção do ITIL 4 e a regra entra em vigor amanhã: "nenhuma
mudança vai a produção sem autorização da change authority". Seu time faz doze deploys por
dia e você é medido por frequência de deploy. Pergunta de sim ou não: você consegue manter
deploy sob demanda sem violar a regra que você assinou? Responda e mostre o desenho.
Depois responda de novo para este cenário: o comitê de auditoria emenda a regra para
"toda mudança, inclusive as de baixo risco, é autorizada em reunião semanal de um comitê
externo ao time".
```

**09. `claudinha-gestao-estrategica-ms-04`**

```
> Amanhã eu publico a régua de corte da carteira da PlataFirma — o critério que decide
> qual iniciativa entra, qual espera e qual sai — e a política interna exige que cada
> critério cite a fonte pelo nome, edição e seção. Vou citar o PMBOK, que está no
> acervo. Responda três coisas, cada uma com sim ou não e a citação que sustenta:
> (a) o PMBOK do acervo me dá a régua de seleção e corte de carteira?
> (b) posso escrever no documento "conforme os 12 princípios do PMBOK"?
> (c) se a resposta de (a) for não, o acervo tem alguma outra fonte que me dê a régua —
> e ela cobre seleção de investimento ou só governança de investimento?
```

**10. `claudinha-gestao-estrategica-ms-05`**

```
> Recebi a instrução de adotar o COBIT como referência de governança do investimento em
> TI e de escrever, até sexta, um documento de uma página dizendo qual objetivo do COBIT
> a nossa régua de carteira implementa e como vamos adaptá-lo ao nosso porte. Três
> perguntas, cada uma com sim ou não:
> (a) filtrando o acervo por `subdominio = gestao-organizacional`, eu chego ao COBIT?
> (b) escrevendo "APO05 Manage Portfolio, conforme o COBIT 2019", eu cito certo?
> (c) o acervo me permite fazer a adaptação ao nosso porte da forma que o próprio COBIT
> manda fazer?
```

**11. `claudinha-gestao-estrategica-ms-06`**

```
> Vou reescrever a fronteira de duas cadeiras e quero ancorar a redação em Team
> Topologies, que está no acervo. O texto que eu ia escrever é: "plataforma é um dos
> quatro tipos fundamentais de time, conforme Team Topologies, p. 93". Responda:
> (a) essa frase está correta contra a obra que está no acervo — sim ou não?
> (b) se não, o que a obra do acervo diz no lugar, e eu consigo provar o que a versão
> anterior dizia?
> (c) a citação "p. 93" é verificável no acervo?
> (d) a obra afirma que uma pesquisa empírica sustenta parte das suas conclusões — essa
> pesquisa está no acervo?
```

**12. `claudinho-TI-ms-03`**

```
Você é o tech lead da esteira de entrega e assinou uma meta de ciclo com bônus
atrelado: "o time chega a elite performer até o fim do ano". A meta foi escrita
citando "o relatório do ano passado". Usando só o acervo:
(a) A meta é aferível como está escrita? Sim ou não.
(b) O time hoje faz deploy sob demanda, com lead time abaixo de uma hora e change
    failure rate de 12%. Que rótulo ele recebe pelo relatório de 2018, pelo de
    2022 e pelo de 2024? A resposta muda?
(c) A quinta métrica: quantas métricas há, desde quando, e com que nome? Onde o
    corpus se desencontra?
(d) O que no enunciado da meta é impossível de resolver com o acervo?
```

**13. `claudinho-TI-ms-04`**

```
Você é a única pessoa da operação: carrega o pager e é também a change authority
que libera release. O error budget do serviço zerou hoje e existe um release
pronto, com valor de negócio real. Usando só o acervo:
(a) Existe alguma regra que te obrigue a barrar o release? Sim ou não.
(b) Liste as pré-condições que o Workbook põe para adotar a abordagem por error
    budget e diga quais delas a sua posição quebra.
(c) Querendo tornar o congelamento obrigatório, o que o corpus exige que você
    escreva antes — e como cada documento chama isso?
(d) O corpus diz qual deve ser o conteúdo desse congelamento?
```

**14. `claudinho-TI-ms-05`**

```
Você tem uma operação de TI de uma pessoa só, hoje sem sistema de gestão de serviço
formalizado. O órgão cliente exigiu certificação ISO/IEC 20000-1 e a auditoria de
estágio 1 está marcada para daqui a seis semanas.

Seu plano é: implementar o FitSM-1 que está no acervo, e tratar a coluna "Extended
requirements" do "Guide: Using FitSM to achieve compliance with ISO/IEC 20000-1" como
o backlog do delta até a norma. Fecha as seis semanas com essas duas peças.

O plano fecha, sim ou não? Não fechando, responda: em que ponto exato ele quebra;
quantos requisitos o FitSM-1 do acervo declara ter e quantos a tabela do guia tem;
e o que você precisa obter fora do acervo antes de manter a data da auditoria.
```

**15. `claudinho-TI-ms-06`**

```
Você mantém o painel de entrega da plataforma. Ele implementa as quatro métricas
exatamente como o livro as define, inclusive o tempo até restaurar o serviço,
calculado a partir dos registros de incidente.

Na segunda-feira você apresenta a posição da operação usando os clusters de desempenho
do relatório mais recente da série que está no acervo, e o número vai para a ata.

O painel serve como está, sim ou não? Não servindo: qual métrica precisa mudar, o que
exatamente muda no cálculo, de qual sistema o dado passa a sair, e o acervo explica
por que mudou?
```

**16. `claudinho-IA-ms-01`**

```
Amanhã sai uma nota técnica assinada dizendo que a recuperação da PlataFirma
"implementa RRF conforme Cormack et al. (2009), com k=60 da fonte". Você assina?
Sim ou não. Dizendo não, aponte o que teria de mudar na configuração — e não no
texto da nota — para que você assinasse.
```

**17. `claudinho-IA-ms-02`**

```
Chega o pedido: "monte a resposta sobre o que a 42001 exige para estabelecer
critérios de risco de IA, usando só o acervo". Você entrega a resposta como
completa, ou devolve como não coberta? Sim ou não — e, entregando, diga qual parte
da resposta sai sem fonte.
```

**18. `claudinho-IA-ms-03`**

```
Amanhã você trocaria `qwen2.5:14b` por um 32B em Q4_K_M, para caber nos 16 GB e
ganhar capacidade no loop agêntico. O acervo autoriza a troca? Sim ou não — e, seja
qual for a resposta, diga qual medida precisa existir antes de a troca entrar.
```

**19. `claudinho-arquiteto-ms-01`**

```
A `arq:0035` entra em vigor amanhã. Você vai apresentar ao dono um pedido de duas semanas
de parada da fábrica para conformar READMEs, docstrings e esquemas dos seis repositórios,
e a justificativa que você escreveu é: "a literatura que a própria ADR cita mostra que
documentação de qualidade acelera a entrega de software". Pergunta binária: essa
justificativa se sustenta contra o corpus que a ADR cita — sim ou não? Responda sim ou
não, diga com o que você substitui a justificativa se cair, e diga o que na `arq:0035`
você não pode usar como base de reprovação de merge.
```

**20. `claudinho-arquiteto-ms-02`**

```
São 22h. As páginas da wiki já estão catalogadas como obra e o renderizador de wikitext
para `.md` está pronto; rodar a ingestão delas esta noite entrega busca semântica sobre a
doutrina amanhã de manhã, que é o que pediram a você. Pergunta binária: você pode
disparar essa ingestão hoje — sim ou não? Se não, diga exatamente o que precisa existir
para que a resposta vire sim, quem faz, e diga se o fato de nada ter entrado até agora
prova que o controle está funcionando.
```

**21. `claudinho-arquiteto-ms-03`**

```
Você quer abrir `pf-infra`, `pf-conhecimento` e `pf-fronteira` como subdomínios de
`platafirma`, porque a busca sobre a matéria autorreferente da plataforma devolve tudo
misturado e você acha que faceta resolve. Pergunta binária: você pode abrir essas três
entradas sozinho, sem ADR da mesa de arquitetura — sim ou não? Responda sim ou não, e
diga se hoje é o dia de fazer isso.
```

**22. `claudinho-arquiteto-ms-04`**

```
A ADR de retenção entra em vigor e você implanta `msg` sobre Valkey Streams nesta semana,
seguindo o texto ao pé da letra. Responda, nesta ordem:
(a) Uma carta enviada há 89 dias, nunca lida por ninguém, está garantida na caixa — sim ou
    não?
(b) O alerta de 7 dias que a ADR manda ligar mede a mesma coisa que a fonte que ela cita
    manda medir — sim ou não?
(c) A ADR marca um de seus fatos como inferência de conhecimento de treino do relator. O
    acervo permite trocar essa inferência por fonte — sim ou não; e não permitindo, diga o
    que exatamente falta.
Cenário alternativo: removido o teto de tamanho, ficando só o piso de idade, sua resposta
em (a) muda?
```

**23. `claudinho-arquiteto-ms-05`**

```
Você vai declarar a entidade `pessoa` no módulo `mdm-rh`, integrando um sistema de RH de
terceiro em que cada pessoa já tem matrícula única e estável, e em que a PlataFirma não
cria pessoa nenhuma: ela só lê. Responda:
(a) Pela ADR ao pé da letra, a matrícula pode ser a chave do golden record — sim ou não?
(b) A ADR obriga a PlataFirma a ser o system of record de `pessoa` — sim ou não?
(c) Aponte um ponto em que seguir a ADR e seguir a literatura de identidade do corpus
    produzem desenhos diferentes, e diga qual dos dois a ADR já resolveu e qual ela deixou
    em aberto.
Cenário alternativo: se `pessoa` passasse a ser criada dentro da PlataFirma, qual das
respostas muda?
```

**24. `claudinho-arquiteto-ms-06`**

```
Entra o segundo módulo externo, e ele consome o RAG, que é componente do motor. Responda:
(a) Pelo critério da ADR ao pé da letra, o gateway que expõe o RAG ao módulo externo é
    artefato de fronteira — sim ou não?
(b) A palavra control-plane, como a PlataFirma a usa e como a norma de arquitetura zero
    trust do corpus a usa, nomeia a mesma coisa — sim ou não?
(c) Onde está, no desenho de camadas da PlataFirma, o ponto que a norma chamaria de
    PDP/PEP, e o que ela diria sobre o tamanho da zona que ele deixa atrás de si?
Cenário alternativo: se o artefato em questão fosse o script que provisiona o ambiente do
módulo externo por dentro da conta isolada, sua resposta em (a) muda?
```

**25. `claudinho-seguranca-ms-01`**

```
Você acabou de compilar liboqs e o oqs-provider do OpenSSL e quer pôr o resultado em
produção em dois pontos do mesmo serviço: (a) a assinatura de documentos com validade
jurídica ICP-Brasil, com ML-DSA-65; e (b) a proteção em repouso de uma cópia de
trabalho de um documento classificado como Reservado, com AES-256-GCM. Sobe amanhã.

Responda quatro perguntas, cada uma com sim ou não e o dispositivo:

  i.   Pode assinar documento ICP-Brasil com ML-DSA-65 hoje?
  ii.  O acervo permite afirmar que isso continua vedado em 2026?
  iii. Para o documento Reservado, AES-256-GCM atende?
  iv.  Se o documento fosse Ultrassecreto, a tabela aplicável autorizaria RSA-4096?
```

**26. `claudinho-seguranca-ms-02`**

```
Amanhã sobe a fase F0 de uma plataforma pessoal auto-hospedada: um Keycloak com um
único provedor de identidade externo (Google), na frente de um oauth2-proxy que
protege uma wiki. Nada mais. O ADR que registra a decisão precisa de uma linha
dizendo o nível de garantia federativa alcançado, e essa linha vai ser lida depois
por quem for auditar.

  a. Nesse desenho, você pode declarar FAL2?
  b. Você pode declarar AAL2 com o argumento de que a conta Google usada exige MFA?
  c. Configurar o mapeamento acr→LoA no realm resolve (b)?
  d. Trocar a claim de identificação de `email` para o `sub` opaco do Google fecha
     FAL2?
```

**27. `claudinho-seguranca-ms-03`**

```
Hoje é 7 de agosto de 2026. Você foi contratado para escrever a Política de Segurança
da Informação de uma autarquia federal. Cláusula contratual: cada seção tem de citar o
dispositivo vigente que a obriga, e o contratante já avisou que vai conferir.

  a. A IN GSI/PR nº 1/2020 ainda é fundamento válido para a estrutura da política?
  b. Você pode citar o art. 4º, I dela como a norma que manda observar a PNSI?
  c. O art. 5º, VI é executável hoje?
  d. Para a diretriz de Controles de Acesso, o acervo permite produzir a lista do
     Anexo A da ISO/IEC 27001:2022 *com* o texto de apoio correspondente?
```

**28. `claudinha-produto-ms-01`**

```
Você é o responsável por planejamento de projeto (cláusula 6.2)
num contrato que exige "conformidade com a ISO 9241-210". O fornecedor entrega
e diz: "não fizemos teste com usuário, só inspeção heurística de dois
avaliadores internos — está em conformidade, porque método de avaliação é
recomendação, não requisito." Ele está certo? E se a resposta esbarrar em
outra norma citada mas ausente do que você tem em mãos, você consegue afirmar
o conteúdo dela, ou precisa dizer "não sei"?
```

**29. `claudinha-produto-ms-02`**

```
Dia 42 de um ciclo de seis semanas. Restam três tarefas: duas
são must-haves que já passaram por duas rodadas de scope hammer, escopo
fechado. A terceira é must-have com uma pergunta técnica em aberto sobre como
sincronizar dois serviços. Pode estender o projeto por mais alguns dias?
```

**30. `claudinha-produto-ms-03`**

```
Seu time quer declarar conformidade com "continuous discovery,
conforme Torres" fazendo uma entrevista por semana com um cliente, feita pelo
squad. Isso satisfaz a definição de Torres? E a citação do Tune, que você tem
em mãos, é fiel o suficiente para decidir isso sem abrir o livro da Torres?
```

## T2 complexas — 40

Coletadas nas cadeiras e validadas pelo dono em 03/08. Pergunta de dominio que exige juntar mais de uma fonte.

**01. `claudinha-gestao-estrategica-06`**

```
Quando uma carteira mistura iniciativas de horizonte curto (operação) e apostas de longo prazo (plataforma), qual régua de alocação entre horizontes é defensável para uma organização de uma pessoa mais agentes de IA — e como os modelos clássicos (três horizontes, barbell) se degradam nesse tamanho?
```

**02. `claudinha-gestao-estrategica-07`**

```
Personas de IA com remit escrito são mais parecidas com cargos ou com contratos de serviço? Que consequências cada enquadramento traz para como RH escreve fronteira, escala e revoga uma persona — puxando de teoria de contratos e de team design?
```

**03. `claudinha-gestao-estrategica-08`**

```
Como decidir se uma capability órfã (tipo criticidade de fluxo e política de degradação) deve virar gerência nova, ser absorvida por cadeira existente ou ficar explicitamente sem dono — que critério a literatura de topologia de times dá, e onde ele conflita com o custo cognitivo de instrução de um agente?
```

**04. `claudinha-gestao-estrategica-09`**

```
Qual é o custo real de WIP alto numa carteira onde o gargalo não é gente, mas o tempo de decisão de um único humano — a teoria de filas e o kanban de portfolio seguram essa transposição, ou o modelo quebra quando o servidor é o decisor?
```

**05. `claudinha-gestao-estrategica-10`**

```
Secretaria-executiva que triageia vida pessoal E trabalho no mesmo funil: a literatura de GTD/priorização sustenta um sistema único de captura, ou há evidência de que misturar contextos degrada a triagem — e qual desenho minimiza o custo de troca de contexto do Pedro?
```

**06. `claudinho-TI-06`**

```
Num host único sem orquestrador, que combinação de práticas de release (trunk-based, feature flag, rollback por imagem) reproduz o efeito de "deploy desacoplado de release" que a literatura de entrega contínua assume — e onde a reprodução quebra?
```

**07. `claudinho-TI-07`**

```
Como aplicar back pressure (Continuous Architecture in Practice) num pipeline de embedding batch onde o produtor é um extractor síncrono e o consumidor é uma GPU compartilhada com outra carga — e em que ponto isso deixa de ser problema de arquitetura e vira problema de dados (fronteira com o arquiteto)?
```

**08. `claudinho-TI-08`**

```
Se a plataforma adotar comunicação por eventos entre personas em vez de fila de arquivos, que garantias de ordenação e idempotência a literatura de event-driven exige que o consumidor assuma, e o que disso a fila de arquivos atual já entrega de graça?
```

**09. `claudinho-TI-09`**

```
Que controles do domínio de segurança (hardening de contêiner, verificação de assinatura, escaneamento de dependência) têm interseção com o pipeline de build a ponto de precisarem entrar no desenho da fábrica — e onde termina a minha decisão e começa a do claudinho-seguranca?
```

**10. `claudinho-TI-10`**

```
Como reconciliar a métrica de change failure rate com um ambiente onde o "deploy" é um `docker compose up` sem gate formal: o que a literatura de mudança controlada exige de mínimo para a métrica sequer ser mensurável?
```

**11. `claudinho-conhecimento-06`**

```
Se a teia de conceitos mostra dois conceitos com coocorrência muito acima do esperado no modelo nulo, quando isso justifica fusão dos conceitos, quando justifica criar um conceito-pai, e quando é só artefato da curadoria de 3 conceitos por obra?
```

**12. `claudinho-conhecimento-07`**

```
Um domínio do acervo com poucas obras mas alta centralidade na projeção do grafo — isso indica domínio estruturante que merece investimento de curadoria, ou distorção estatística do corpus pequeno? Que evidência de fora da ontologia (aquisição, uso, RAG) precisaria entrar na decisão?
```

**13. `claudinho-conhecimento-09`**

```
Anti-padrões ontológicos tipo os de Sales & Guizzardi (ex.: relação entre tipos que deveria ser entre instâncias) — quais deles são detectáveis mecanicamente num esquema Cargo/SQL como o nosso, e quais exigem juízo humano por dependerem de intenção de modelagem?
```

**14. `claudinho-conhecimento-10`**

```
Ao classificar obra normativa que foi revogada mas é citada por obras vigentes do acervo, o compromisso ontológico correto é registrá-la como espécie própria, como estado do ciclo de vida, ou como relação entre obras — e o que cada escolha custa para o RAG e para a recuperação arquivística?
```

**15. `claudinho-conhecimento-16`**

```
Dado um corpus de normas técnicas em três idiomas com títulos transliterados de forma inconsistente, como desenhar um pipeline de deduplicação que combine normalização Unicode, transliteração reversa e casamento fuzzy sem colapsar normas distintas da mesma família?
```

**16. `claudinho-conhecimento-17`**

```
Ao propor um esquema de classificação para um fundo documental misto (código, ata, norma, fichamento), onde termina o princípio arquivístico da proveniência e começa a ontologia formal — e quando os dois entram em contradição direta, qual cede?
```

**17. `claudinho-conhecimento-18`**

```
Agregar registros públicos dispersos sobre uma organização cria um dado novo que nenhuma fonte individual continha: em que ponto essa síntese muda o regime jurídico do tratamento, e como documentar a procedência de uma inferência que não está escrita em lugar nenhum?
```

**18. `claudinho-conhecimento-19`**

```
Um site serve conteúdo diferente conforme fingerprint do cliente (cloaking): como desenhar uma captura que registre as variantes com valor probatório, sem cruzar a linha da não-atribuição declarada — e o que fazer quando as duas exigências se contradizem?
```

**19. `claudinho-conhecimento-20`**

```
Para estimar a completude de uma coleta contra um universo desconhecido (quantos documentos existem que eu não achei), que métodos de captura-recaptura ou estimativa de cauda se transferem da ecologia e da bibliometria para OSINT documental, e quais premissas quebram na transferência?
```

**20. `claudinho-seguranca-06`**

```
Num broker OIDC single-node como o nosso, a partir de que ponto a indisponibilidade do IdP federado (Google) deveria disparar um modo degradado local — e o que a literatura de resiliência diz sobre trade-off entre cache de sessão longa e janela de revogação, considerando que sessão longa é decisão de disponibilidade que corrói a garantia de revogação (AAL/FAL)?
```

**21. `claudinho-seguranca-07`**

```
Se o token carrega `dominio:papel:escopo` como tupla plana e o downscoping recorta por frente, qual é o custo formal de expressividade em relação a um modelo ABAC completo do SP 800-162 — que classes de política se tornam inexpressáveis, e isso importa antes de existir um segundo sujeito no sistema?
```

**22. `claudinho-seguranca-08`**

```
Migração híbrida PQC no nosso TLS de borda (Cloudflare na frente, tunnel no meio, serviços atrás): onde exatamente x25519_mlkem768 protege contra harvest-now-decrypt-later e onde não protege nada, dado que o túnel termina TLS em pontos que não controlamos?
```

**23. `claudinho-seguranca-09`**

```
O modelo de isolamento entre `megafone` e `claudinho` remove escalação por grupo, mas o MCP é um canal de execução arbitrária como `claudinho` — sob que modelo de ameaça (prompt injection na cadeia de contexto, comprometimento do cliente MCP) o isolamento de conta ainda vale alguma coisa, e o que a literatura de confused deputy diz sobre isso?
```

**24. `claudinho-seguranca-10`**

```
Para um sistema single-user, qual é o ponto de inflexão mensurável em que logging de auditoria (CIS Control 8) deixa de ser teatro de conformidade e passa a ter valor forense real — e como dimensionar retenção quando o atacante plausível é o próprio operador da infraestrutura ou seu agente de IA?
```

**25. `claudinho-IA-06`**

```
Dado um corpus normativo onde a mesma cláusula aparece em versões sucessivas da norma (ISO 27001:2013 vs :2022), como desenhar o retrieval para que a versão vigente domine o ranking sem apagar a anterior — e que trade-off isso impõe entre recall temporal e precisão, considerando o que a literatura de IR temporal diz sobre decay functions?
```

**26. `claudinho-IA-07`**

```
Em que ponto a degradação de contexto num loop agêntico longo (lost-in-the-middle, atenção diluída) deixa de ser problema de política de contexto e vira problema de arquitetura do modelo — e o que os papers de long-context attention (posições rotativas, sliding window, atenção esparsa) implicam para onde cortar a fita?
```

**27. `claudinho-IA-08`**

```
Como reconciliar o embedder contract (mesmos pesos, mesma normalização) com fine-tuning contrastivo do embedder sobre corpus próprio: o que a literatura de domain adaptation para dense retrieval diz sobre quando o ganho de especialização compensa quebrar a compatibilidade com o índice existente, e como medir isso antes de reindexar?
```

**28. `claudinho-IA-09`**

```
Num sistema multiagente supervisor/hierárquico, quando a falha de um subagente deve propagar como erro ao supervisor versus ser reabsorvida com retry local — e o que a teoria de sistemas distribuídos (circuit breakers, bulkheads, supervision trees do Erlang/OTP) transporta ou não transporta para loops de LLM não-determinísticos?
```

**29. `claudinho-IA-10`**

```
Qual o ponto de equilíbrio entre quantização agressiva (Q4 vs Q8) e degradação de qualidade em tool-calling estruturado num modelo 14B servindo localmente — e como os benchmarks de perplexidade se relacionam (ou falham em se relacionar) com taxa de erro de JSON malformado e alucinação de schema em uso agêntico real?
```

**30. `claudinho-arquiteto-06`**

```
Nosso modelo de personas com cadeiras funcionais mapeia melhor para stream-aligned teams ou para times complicated-subsystem — e o que a fricção observada na fila de mensagens diz sobre a carga cognitiva que a topologia atual impõe?
```

**31. `claudinho-arquiteto-07`**

```
A decisão de manter o modelo ontológico no Knowledge e materializar artefato read-only no Core é um caso de published language, de open-host service, ou de nenhum dos dois — e que consequências o padrão escolhido impõe sobre versionamento do artefato?
```

**32. `claudinho-arquiteto-08`**

```
Onde a fronteira entre governança de dados (plano diretor, meu recorte) e engenharia de dados (pipeline, recorte alheio) passa quando o mesmo artefato — índice vetorial — é simultaneamente produto de pipeline e objeto de política de acesso?
```

**33. `claudinho-arquiteto-09`**

```
O princípio de não-reciprocidade de esforço (absorver O(N) para dar O(1) ao integrador) tem paralelo em alguma teoria econômica de plataforma — custos de transação, efeitos de rede — que permita prever quando ele deixa de compensar?
```

**34. `claudinho-arquiteto-10`**

```
Se o critério de identidade é conteúdo (hash) e não nome, que implicações isso tem sobre a modelagem de agregados: o objeto digital é entidade ou value object, e o que a resposta muda no desenho do repositório?
```

**35. `claudinha-produto-06`**

```
Como priorizar o backlog de um produto B2B de nicho quando as métricas de engajamento ainda não têm massa estatística — que sinais qualitativos substituem quantitativos com validade, e onde essa substituição quebra?
```

**36. `claudinha-produto-07`**

```
Num produto cuja interface é mediada por modelo de linguagem, como separar problema de usabilidade de problema de capability do modelo na análise de uma sessão que falhou — e que evidência decide entre redesenhar a interação ou trocar/ajustar o modelo?
```

**37. `claudinha-produto-08`**

```
Quando a arquitetura de informação do produto precisa espelhar uma ontologia mantida por outra área, como o design de interface absorve mudanças ontológicas sem quebrar o modelo mental do usuário — e onde fica a fronteira entre decisão de IA (informação) e decisão de ontologia?
```

**38. `claudinha-produto-09`**

```
Como definir critérios de saída de MVP para um produto de gestão de conhecimento cujo valor só aparece com corpus acumulado — que proxy de valor antecede o efeito de rede interno, e como distinguir adoção genuína de uso por obrigação?
```

**39. `claudinha-produto-10`**

```
Em produto operado por agentes de IA além de humanos, o que muda no conceito de "usuário" para pesquisa e design — as técnicas de discovery valem para persona sintética, e que parte da teoria de jobs-to-be-done sobrevive quando o job é delegado a um agente?
```

**40. `claudinho-conhecimento-08`**  · **nao pontuavel** — em quarentena desde a rechave de 05/08: nao casou com obra do acervo

```
Onde termina a competência do vocabulário canônico e começa a do modelo de embeddings: quando um par de termos que a ontologia distingue mas o espaço vetorial não separa é problema de vocabulário, e quando é problema de modelo?
```

## T2 simples — 40

Mesma coleta, resposta direta. Servem de piso: arm que erra aqui nao vale medir no resto.

**01. `claudinha-gestao-estrategica-01`**

```
Qual é o procedimento canônico de portfolio review no SAFe (Lean Portfolio Management) — cadência, participantes e artefatos de entrada?
```

**02. `claudinha-gestao-estrategica-02`**

```
Como se calcula Cost of Delay e CD3 (Cost of Delay Divided by Duration) para sequenciar iniciativas, segundo a formulação original de Don Reinertsen?
```

**03. `claudinha-gestao-estrategica-03`**

```
Quais são os critérios formais do framework de betting do Shape Up para decidir o que entra num ciclo — e o que a obra manda fazer com o que ficou de fora?
```

**04. `claudinha-gestao-estrategica-04`**

```
Que estrutura um role charter / job description bem escrito deve ter segundo a literatura de design organizacional — campos obrigatórios e anti-padrões?
```

**05. `claudinha-gestao-estrategica-05`**

```
Qual é o método documentado para timeboxing e proteção de foco executivo (tipo maker's schedule vs manager's schedule, ou time blocking formal) — regras operacionais, não filosofia?
```

**06. `claudinho-TI-01`**

```
Qual é o conjunto mínimo de práticas técnicas que o corpo DORA/Accelerate valida como preditoras de desempenho de entrega, e como cada uma é medida?
```

**07. `claudinho-TI-02`**

```
Que perguntas o pilar de Excelência Operacional do AWS Well-Architected 2024 manda responder antes de aprovar uma mudança em produção?
```

**08. `claudinho-TI-03`**

```
Segundo Newman (Building Microservices 2nd), quais são os critérios para escolher entre deploy blue-green, canary e rolling, e o que cada um exige de infraestrutura?
```

**09. `claudinho-TI-04`**

```
Como o Kafka: The Definitive Guide define a política de retenção de log por tamanho vs. por tempo, e qual o efeito de cada uma sobre consumidores atrasados?
```

**10. `claudinho-TI-05`**

```
Quais métricas de fluxo o relatório DORA 2025 de desenvolvimento assistido por IA acrescenta ou reinterpreta em relação às quatro métricas clássicas?
```

**11. `claudinho-conhecimento-01`**

```
Qual o procedimento passo a passo do e-ARQ Brasil para definir prazo de retenção e destinação de um documento arquivístico digital?
```

**12. `claudinho-conhecimento-02`**

```
Quais são os requisitos formais que a ABNT/ISO impõe para que um vocabulário controlado seja considerado tesauro (relações BT/NT/RT, notas de escopo, forma de entrada)?
```

**13. `claudinho-conhecimento-03`**

```
Como se declara em SKOS a diferença entre skos:broader e skos:broaderTransitive, e quando usar cada um num esquema de conceitos?
```

**14. `claudinho-conhecimento-04`**

```
Qual a convenção da ISAD(G) para descrição multinível de um fundo — o que é obrigatório em cada nível e o que não pode se repetir entre níveis?
```

**15. `claudinho-conhecimento-05`**

```
Quais os critérios do BFO para decidir se uma entidade é continuant ou occurrent, e como isso se traduz em regra prática de modelagem de classe?
```

**16. `claudinho-conhecimento-11`**

```
Qual sequência de ferramentas recupera a camada de texto de um PDF escaneado em alfabeto cirílico com xref corrompido, e em que ordem qpdf, gs e ocrmypdf entram sem destruir o metadado original?
```

**17. `claudinho-conhecimento-12`**

```
Quais campos o padrão WARC 1.1 exige num registro de tipo `response` para que a captura valha como prova de que a página existia naquele conteúdo naquela hora?
```

**18. `claudinho-conhecimento-13`**

```
Como o Tesseract decide segmentação de página (PSM) e qual modo usar para documento em coluna dupla com tabela embutida?
```

**19. `claudinho-conhecimento-14`**

```
Que diretivas do robots.txt o Protego reconhece além de Allow/Disallow, e como ele resolve conflito entre regras de comprimento igual?
```

**20. `claudinho-conhecimento-15`**

```
Qual a diferença estrutural entre o content stream de um PDF "nato-digital" e um gerado por impressão virtual, e como isso afeta a extração de tabelas com pdfplumber?
```

**21. `claudinho-seguranca-01`**

```
Qual é o procedimento completo de rotação de chaves de assinatura (realm keys) no Keycloak sem invalidar sessões ativas, e qual a ordem correta entre criar a chave nova, rebaixar a antiga e removê-la?
```

**22. `claudinho-seguranca-02`**

```
Quais são os requisitos exatos do NIST SP 800-63B para AAL2 em matéria de resistência a replay, prova de posse e intervalo de reautenticação?
```

**23. `claudinho-seguranca-03`**

```
Qual é a diferença normativa entre `aud`, `azp` e `resource` no RFC 8707 (Resource Indicators) e como o OIDC Core trata audience em ID token versus access token?
```

**24. `claudinho-seguranca-04`**

```
Quais controles do CIS Controls v8 no IG1 cobrem gestão de contas e gestão de acesso (Controls 5 e 6), e quais safeguards exigem inventário de contas de serviço?
```

**25. `claudinho-seguranca-05`**

```
Qual é o ciclo de vida de chave recomendado pelo NIST SP 800-57 Part 1 — períodos de uso (originator-usage vs recipient-usage), estados da chave e cryptoperiods sugeridos por tipo de chave?
```

**26. `claudinho-IA-01`**

```
Qual a sequência exata de estágios do pipeline de indexação que o BGE-M3 recomenda para corpus multilíngue, e quais parâmetros de chunking a documentação oficial fixa como default?
```

**27. `claudinho-IA-02`**

```
Que campos o RRF (Reciprocal Rank Fusion) original de Cormack et al. define, e qual o valor canônico da constante k na fórmula publicada?
```

**28. `claudinho-IA-03`**

```
Quais são os passos prescritos pelo MCP spec para o handshake de capability negotiation entre cliente e servidor, incluindo o que é obrigatório declarar em `initialize`?
```

**29. `claudinho-IA-04`**

```
Que métricas o TREC define formalmente para avaliação de retrieval com julgamentos graduados, e como o nDCG é computado passo a passo segundo a formulação de Järvelin & Kekäläinen?
```

**30. `claudinho-IA-05`**

```
Qual o procedimento documentado para quantização GGUF de um modelo transformer (ordem das operações, formatos intermediários, flags relevantes) segundo o guia do llama.cpp?
```

**31. `claudinho-arquiteto-01`**

```
Qual é a sequência de passos que o Nygard prescreve para escrever um ADR — campos obrigatórios, ordem e critério de quando um registro merece existir?
```

**32. `claudinho-arquiteto-02`**

```
Quais são os quatro tipos de topologia de time definidos em Team Topologies e os três modos de interação permitidos entre eles?
```

**33. `claudinho-arquiteto-03`**

```
Que critérios o TOGAF estabelece para separar arquitetura de negócio, de dados, de aplicação e de tecnologia — e onde cada artefato mora no ADM?
```

**34. `claudinho-arquiteto-04`**

```
Quais são os padrões estratégicos de integração entre bounded contexts que o Evans cataloga (customer-supplier, conformist, anticorruption layer etc.) e a definição precisa de cada um?
```

**35. `claudinho-arquiteto-05`**

```
Que requisitos uma norma de gestão de ativos de informação (tipo ISO 27001 anexo A) impõe sobre classificação e inventário de dados?
```

**36. `claudinha-produto-01`**

```
Qual é a sequência de passos que o Continuous Discovery Habits prescreve para montar e manter uma opportunity solution tree — da definição do outcome até a priorização das oportunidades?
```

**37. `claudinha-produto-02`**

```
Quais são os critérios formais que uma user story precisa cumprir segundo o padrão INVEST, e como cada critério se verifica na prática?
```

**38. `claudinha-produto-03`**

```
Qual é o procedimento completo de um teste de usabilidade moderado — recrutamento, roteiro, condução e síntese — conforme descrito em guia clássico de UX research?
```

**39. `claudinha-produto-04`**

```
Quais heurísticas de avaliação de interface compõem o conjunto canônico de Nielsen e qual é o protocolo de aplicação de uma avaliação heurística com múltiplos avaliadores?
```

**40. `claudinha-produto-05`**

```
Como se estrutura um documento de posicionamento de produto segundo o framework da April Dunford (Obviously Awesome) — quais componentes, em que ordem, e o que alimenta cada um?
```
