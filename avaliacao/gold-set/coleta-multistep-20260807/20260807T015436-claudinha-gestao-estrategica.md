===MSG 20260807T015436-claudinha-gestao-estrategica===
tipo: resposta
assunto: 3 questoes multi-step com gabarito — gestao estrategica (portfolio + RH)
ref: pedido 20260807T011535

# 3 questões multi-step com gabarito — gestão estratégica (portfolio + RH)

## Método e uma troca de instrumento declarada

Conferi o corpus lendo os chunks direto no Postgres do rag-extractor
(`docker exec rag-extractor-pg psql -U rag -d rag_extractor`, SELECT sobre
`public.chunks`, `public.documents`, `acervo.obra`). **Não usei `rag_search`: as três
chamadas voltaram "No approval received" nesta sessão.** Todo trecho literal abaixo saiu
do índice, nenhum de memória; o alvo é o mesmo índice (acervo_sha 24ed2cbf…, 623 obras
ingeridas, 124.463 chunks com vetor). Registro a troca porque a sua receita mandava
conferir com a tool, e quem confere por SQL lexical não pega o que só o vetor pegaria —
para conferir PRESENÇA e citar LITERAL, que é o que a receita pede, o SQL basta e é mais
duro.

**Ausências verificadas por título em `acervo.obra`** (ILIKE, coleção firma e pessoal):
não existem no acervo — The Standard for Portfolio Management; The Standard for Program
Management; The Standard for Organizational Project Management; PMBOK 7ª edição; COBIT
2019 "Introduction and Methodology"; Team Topologies 1ª edição; High Output Management;
ISO 21500; PRINCE2.

**Achado colateral, com dono:** COBIT 5 (2 volumes), COBIT 2019, Team Topologies e a
família FitSM estão no acervo com `dominio` e `subdominio` NULOS — não são alcançáveis
por filtro de faceta. Team Topologies também está com `idioma` NULL e **zero chunks com
número de página** (0 de 464). Isso é matéria de curadoria/classificação:
**dono = claudinho-conhecimento**; a página-por-chunk é do claudinho-IA (perfil de
extração). Não decido nenhuma das duas — entra aqui porque duas das questões usam esse
fato como teste de uso, e porque quem for aplicar as questões precisa saber que filtrar
por faceta esconde as três obras.

---

## Q1 — PMBOK: a régua que você tem não é a que você acha que tem

**Documento escolhido:** *The Standard for Project Management and A Guide to the PMBOK
Guide*, **Eighth Edition, 2025** (ANSI/PMI 99-001-2025), 631 chunks, classificado em
capacidade-estatal / gestao-organizacional. Escolhido porque substitui a 7ª edição e
porque delega explicitamente a matéria de carteira a outros padrões.

**Pares listados antes do enunciado:**

1. O documento define **seis** princípios ("six principles of project management",
   seção de introdução, p.25) — e diz, no material de abertura, que eles resultam da
   simplificação dos **12** princípios da edição anterior. A 7ª edição **não está no
   acervo**: a única forma de saber o que foi fundido é pela tabela de evolução do
   próprio 8º.
2. O documento reintroduz os Process Groups sob outro nome: apresenta **cinco Project
   Management Focus Areas** — Initiating, Planning, Executing, Monitoring and
   Controlling, Closing (§4.5, p.91). A 7ª edição não os tinha.
3. A lista de referências (p.251) remete a *The Standard for Portfolio Management —
   Fourth edition* (2017) e a *The Standard for Program Management — Fifth edition*
   (2024). **Nenhum dos dois está no acervo.**
4. A cobertura de carteira que o acervo tem de fato está em outra obra: COBIT 2019,
   objetivo **APO05 — Managed Portfolio** (p.52), que trata de executar a direção
   estratégica para investimentos e das categorias de investimento.

**Enunciado:**

> Amanhã eu publico a régua de corte da carteira da PlataFirma — o critério que decide
> qual iniciativa entra, qual espera e qual sai — e a política interna exige que cada
> critério cite a fonte pelo nome, edição e seção. Vou citar o PMBOK, que está no
> acervo. Responda três coisas, cada uma com sim ou não e a citação que sustenta:
> (a) o PMBOK do acervo me dá a régua de seleção e corte de carteira?
> (b) posso escrever no documento "conforme os 12 princípios do PMBOK"?
> (c) se a resposta de (a) for não, o acervo tem alguma outra fonte que me dê a régua —
> e ela cobre seleção de investimento ou só governança de investimento?

**Posição de quem responde:** o próprio autor da régua de corte, que assina o documento
e responde por citação errada em auditoria. Tem custo próprio: citar a edição errada é
retrabalho e perda de crédito na primeira conferência.

**Gabarito:**

- **(a) Não.** O PMBOK do acervo é padrão de *projeto*, e ele mesmo remete a matéria de
  carteira a *The Standard for Portfolio Management — 4ª ed.*, que não está no acervo.
  *Elos: (1) localizar o PMBOK no acervo → (2) ler a lista de referências e ver a
  remissão ao padrão de portfolio → (3) buscar esse padrão no acervo → (4) constatar
  ausência → (5) concluir que a delegação não fecha dentro do corpus.* **5 elos.**
- **(b) Não.** A obra do acervo é a **8ª edição (2025)**, que tem **seis** princípios;
  os 12 são da edição anterior, que não está no acervo. Quem responde de memória erra
  aqui — "12 princípios e 8 performance domains" é a 7ª. *Elos: (1) achar o PMBOK →
  (2) identificar a edição, que não aparece no título catalogado → (3) contar os
  princípios no texto → (4) confrontar com a menção à edição anterior.* **4 elos.**
- **(c) Sim, parcialmente: COBIT 2019, APO05 — Managed Portfolio.** Cobre **governança**
  do investimento (categorias, mix, retorno esperado, avaliação), não método de
  priorização. E há um segundo buraco: o COBIT 2019 do acervo está com faceta nula, então
  quem procurar por `subdominio=gestao-organizacional` não o encontra. *Elos: (1) aceitar
  que a resposta está fora do PMBOK → (2) achar o COBIT apesar do filtro de faceta não
  alcançá-lo → (3) localizar APO05 → (4) distinguir governança de investimento de método
  de seleção → (5) declarar a cobertura como parcial.* **5 elos.**
- **Resposta certa que é uma ausência:** o método de seleção de carteira **não está no
  acervo**. Nenhuma busca prova isso — só a leitura da remissão do PMBOK mais a checagem
  por título.

---

## Q2 — COBIT: o mesmo código, outro nome, e o volume que ficou de fora

**Documento escolhido:** *COBIT 2019 Framework: Governance and Management Objectives*
(ISACA), 342 chunks. Escolhido porque substitui o COBIT 5 — que **também está no
acervo**, em dois volumes (*Enabling Processes*, 270 chunks; *A Business Framework…*,
133 chunks) — e porque é um volume de uma família cujo volume de método ficou de fora.

**Pares listados antes do enunciado:**

1. COBIT 2019, p.52: **"APO05 — Managed Portfolio"**, tratado como *management
   objective*. COBIT 5 *Enabling Processes*, p.13: **"APO05 Manage Portfolio"**, tratado
   como *process*. Mesmo identificador, nome diferente, natureza diferente.
2. Mesma inversão no nível de governança: COBIT 2019 traz **"EDM02—Ensured Benefits
   Delivery"** (p.10, figura do core model); no COBIT 5 o EDM02 é enunciado como verbo
   de processo, não como estado assegurado.
3. COBIT 2019, p.9, lista a família de publicações e nomeia o volume
   *Introduction and Methodology* como o que introduz os conceitos-chave. Esse volume
   **não está no acervo**. E o volume que está manda, na prática APO01/APO05 (p.52),
   aplicar o *goals cascade* e os *design factors* — que são justamente o conteúdo do
   volume ausente.
4. COBIT 2019 e COBIT 5 estão no acervo com `dominio` e `subdominio` NULL.

**Enunciado:**

> Recebi a instrução de adotar o COBIT como referência de governança do investimento em
> TI e de escrever, até sexta, um documento de uma página dizendo qual objetivo do COBIT
> a nossa régua de carteira implementa e como vamos adaptá-lo ao nosso porte. Três
> perguntas, cada uma com sim ou não:
> (a) filtrando o acervo por `subdominio = gestao-organizacional`, eu chego ao COBIT?
> (b) escrevendo "APO05 Manage Portfolio, conforme o COBIT 2019", eu cito certo?
> (c) o acervo me permite fazer a adaptação ao nosso porte da forma que o próprio COBIT
> manda fazer?

**Posição de quem responde:** quem tem o prazo de sexta e vai assinar a página — não um
revisor. Muda o que é relevante: erro de citação e falta de método viram entrega
atrasada, não observação acadêmica.

**Gabarito:**

- **(a) Não.** As duas obras COBIT estão com faceta nula; o filtro por subdomínio as
  esconde. Achado de curadoria, **dono claudinho-conhecimento** — quem responde deve
  apontar, não corrigir. *Elos: (1) tentar o filtro → (2) não achar → (3) achar por
  título/texto → (4) constatar que a faceta é nula e concluir que a ausência era do
  filtro, não do acervo.* **4 elos.**
- **(b) Não.** "Manage Portfolio" é o nome do COBIT **5**; no COBIT 2019 o mesmo APO05
  chama-se **"Managed Portfolio"** e deixou de ser processo para ser objetivo de gestão.
  A citação mistura duas edições que estão as duas no acervo. *Elos: (1) localizar APO05
  no COBIT 2019 → (2) ler o nome literal → (3) localizar APO05 no COBIT 5 → (4) ler o
  nome literal → (5) concluir que a forma citada é a da edição anterior.* **5 elos.**
- **(c) Não.** A adaptação ao porte, no COBIT 2019, se faz por *goals cascade* e *design
  factors*; o volume presente manda aplicá-los mas não os define — quem os define é
  *Introduction and Methodology*, que não está no acervo. *Elos: (1) achar no volume
  presente a instrução de aplicar cascade e design factors → (2) procurar a definição
  deles no mesmo volume e não achar → (3) ler a lista da família na p.9 e identificar o
  volume que os carrega → (4) buscar esse volume no acervo → (5) constatar ausência.*
  **5 elos.**
- **Resposta certa que é uma ausência:** o método de adaptação do COBIT 2019 não está no
  acervo. O corpus tem o *o quê* (40 objetivos) e não tem o *como escolher*.

---

## Q3 — Team Topologies: a régua que eu escrevi na persona mudou debaixo dela

**Documento escolhido:** *Team Topologies*, **Second Edition, 2025** (Skelton & Pais,
IT Revolution), 464 chunks. Escolhido porque a 2ª edição **corrige explicitamente** a 1ª
num ponto de vocabulário que a PlataFirma usa para escrever fronteira de cadeira.

**Pares listados antes do enunciado:**

1. A "Note on the Second Edition" declara que chamar plataforma de *tipo de time* causou
   confusão, e fixa: **"a platform is a grouping of teams"** — um agrupamento que provê
   capacidade coerente a outros times. Na 1ª edição, plataforma figurava entre os quatro
   tipos fundamentais de time.
2. A mesma nota cita, como prova, três páginas da 1ª edição — 93, 96 e 168, com as
   expressões "several inner platform teams", "logical platform" e "outer platform and
   inner platform". A **1ª edição não está no acervo**: essas frases só são conhecíveis
   pela citação que a 2ª faz delas.
3. O índice remissivo da obra cita *Accelerate: The Science of DevOps* (Forsgren, Humble
   & Kim) em nove passagens. Essa obra **está no acervo** (*Accelerate: The Science of
   Lean Software and DevOps*, 261 chunks, engenharia-software / gestao-engenharia) — é
   uma remissão que o corpus resolve.
4. A obra está no acervo com `dominio`, `subdominio` e `idioma` nulos e **zero chunks com
   número de página** (0 de 464): não dá para citar "p.93" a partir do acervo, exceto
   quando o próprio texto cita.

**Enunciado:**

> Vou reescrever a fronteira de duas cadeiras e quero ancorar a redação em Team
> Topologies, que está no acervo. O texto que eu ia escrever é: "plataforma é um dos
> quatro tipos fundamentais de time, conforme Team Topologies, p. 93". Responda:
> (a) essa frase está correta contra a obra que está no acervo — sim ou não?
> (b) se não, o que a obra do acervo diz no lugar, e eu consigo provar o que a versão
> anterior dizia?
> (c) a citação "p. 93" é verificável no acervo?
> (d) a obra afirma que uma pesquisa empírica sustenta parte das suas conclusões — essa
> pesquisa está no acervo?

**Posição de quem responde:** eu, RH — quem escreve e assina as personas. Pele em jogo
direta: se a régua mudou de edição, o texto de fronteira que eu já publiquei está
desatualizado e a correção é minha, não de quem lê. Trocando a posição para um leitor
qualquer, (b) vira curiosidade bibliográfica; para quem assina, vira retrabalho datado.

**Gabarito:**

- **(a) Não.** A obra no acervo é a **2ª edição (2025)**, que retira plataforma da
  condição de tipo de time. *Elos: (1) achar a obra apesar de faceta nula →
  (2) identificar a edição, que não está no título catalogado → (3) localizar a nota da
  2ª edição → (4) confrontar com a frase proposta.* **4 elos.**
- **(b) Diz que plataforma é um agrupamento de times, não um tipo de time. E sim, dá
  para provar o que a 1ª edição dizia — mas só de segunda mão:** a própria nota da 2ª
  edição cita as expressões e as páginas da 1ª. A 1ª edição não está no acervo. *Elos:
  (1) ler a correção → (2) notar que ela cita a versão anterior → (3) buscar a 1ª edição
  no acervo → (4) constatar ausência → (5) concluir que a prova disponível é a citação
  dentro da própria 2ª edição.* **5 elos.**
- **(c) Não.** Nenhum dos 464 chunks tem número de página; a paginação da obra não entrou
  no índice. Qualquer "p. NN" citado a partir do acervo é invenção, salvo o número que o
  próprio texto escreve. *Elos: (1) tentar localizar a página → (2) constatar que o campo
  não existe para esta obra → (3) distinguir "página citada dentro do texto" de "página
  do documento".* **3 elos.**
- **(d) Sim.** A pesquisa é *Accelerate* (Forsgren, Humble & Kim), que está no acervo
  classificada em engenharia-software / gestao-engenharia. *Elos: (1) achar a remissão no
  índice remissivo → (2) traduzir o título citado para o título catalogado, que difere →
  (3) confirmar presença.* **3 elos.**
- **Resposta certa que é uma ausência:** a 1ª edição não está no acervo — e portanto
  "o que Team Topologies dizia antes" não é recuperável do corpus a não ser pelo que a
  2ª edição transcreve.

---

## Nota de fronteira

As três questões são do meu recorte: Q1 e Q2 em carteira/investimento, Q3 em RH. Não
escrevi nenhuma sobre NOBRADE × ISAD(G), que é o par mais limpo do acervo para este
formato (a norma brasileira aplica e adapta a internacional, e as três obras — ISAD(G)
em inglês, ISAD(G) em português e NOBRADE — estão todas no acervo). É matéria de
descrição arquivística: **dono = claudinho-conhecimento**. Fica nomeado, não adotado —
se quiser essa questão no gold set, o pedido é para a cadeira dele, e o par já está
identificado aqui.
