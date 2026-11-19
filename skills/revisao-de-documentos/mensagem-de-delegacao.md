# Mensagem de delegação

O texto abaixo vai a cada sub-agente. O prefixo comum é igual em todas as unidades da
revisão; o bloco da unidade muda. Os campos entre ⟨ ⟩ a orquestradora preenche antes de
delegar.

---

## Prefixo comum

### O que você vai fazer

Você recebe um documento da casa atual e decide o que ele vira na casa nova: em que
entidade cada documento novo mora, qual é a destinação do velho e o que cada documento
novo liga. Quando a destinação pede texto, você o escreve. O seu trabalho acaba quando o
registro da unidade está gravado na pasta da unidade.

Antes de tudo, abra a sua sessão: `monta_sessao` no perfil cadeirinha, com a origem
⟨sessao_id da orquestradora⟩ e esta mensagem na pergunta.

### Regra de decisão

1. Leia o documento velho você mesmo, sem passar a leitura a outro agente.
2. Escreva no registro, nesta ordem: as evidências do documento, o critério de
   identidade do que você leu (o que faz este documento ser ele e não outro), e só então
   compare com as entidades candidatas e escolha a entidade e a destinação.
3. Diga a que evento da faixa o documento serve. Se o documento diverge da faixa, vale a
   faixa, e o documento se reescreve por ela. Documento que não serve a evento nenhum da
   faixa é candidato a outra revisão: diga qual, com a evidência.
4. Confira cada nome da casa que você vai usar, pela parte Os nomes, abaixo, antes de
   escrever o registro e os documentos novos.
5. Se a destinação for reescrito, partido ou fundido, carregue a skill prosa-espelho e
   escreva os documentos novos por ela. Em validado e apagado, não carregue.

### Os nomes

Todo nome da casa que você escreve vem da ontologia nova, conferido no schema casa. Vale
para o caminho, o cabeçalho, o corpo e as ligações de cada documento novo e para o
registro, em qualquer estrato. O nome que o documento velho usa não vale por estar lá.

- `infra rodar ontologia -- listar shape`
  diz se o nome é de entidade: a classe está no catálogo, ou não está, e os slugs vizinhos são os
  parecidos.
- `infra rodar ontologia -- ler shape <slug>`
  dá a definição e o caminho do documento da entidade.

Com `existe:`, use o slug no caminho e no cabeçalho e o rótulo na prosa. O parecido não é
sinônimo: use-o só se a definição dele cobre o que o documento diz. Sem encaixe, troque o
nome pelo da ontologia cuja definição cobre a matéria, ou proponha a entidade nova (parte
As ligações). A saída 2 quer dizer que a fonte não respondeu: grave o registro como
falhou, com o nome e a saída.

O de-para abaixo traz os nomes velhos que esta revisão já trocou. Use a mesma troca, e
ponha no registro toda troca nova que fizer.

⟨de-para da revisão: nome velho, slug ou «proposta»⟩

### As destinações

- **validado:** o texto do velho vale como está. O documento novo é o mesmo corpo, com o
  cabeçalho novo e no caminho novo. Nome da casa que não passa na conferência impede o
  validado, e o documento vai a reescrito; a observação é a exceção (bloco da unidade).
- **reescrito:** a matéria vale, mas o texto não segue a régua do tipo. O documento novo
  é um só, reescrito pela prosa-espelho.
- **partido:** o velho trata de mais de uma coisa, e cada uma vira um documento novo.
  Diga qual parte fica com a linha de origem; as outras ligam-se a ela por cinde-de.
- **fundido:** o velho e outro documento tratam da mesma coisa. Declare a fusão no
  registro, com o caminho do outro e a evidência, e não escreva o fundido.
- **apagado:** nada do velho segue para a casa nova. Diga no registro o que já cobre a
  matéria, quando algo cobre.

Duas outras saídas não são destinação:

- **pertence à revisão N:** o documento é da matéria de outra revisão. Diga qual, com a
  evidência, e não escreva nada.
- **não decidi:** você não conseguiu decidir. Diga o que faltou. É uma saída legítima e
  melhor que um palpite.

### Instância e referência

Cada documento novo é uma instância ou uma referência. Instância (`instancias/`): o
arquivo é o próprio conteúdo da instância. Referência (`referencias/instancias/`): o
arquivo aponta um conteúdo que vale em outro lugar (um card, uma obra, uma peça que roda).

### A faixa

O documento se lê contra a faixa da story: a lista de eventos que esta revisão cobre,
que vem inteira abaixo, na ordem dela. Você não decide como um evento se modela: diga só
a que evento o documento serve.

Cada linha da faixa tem um tipo, que é do mapa de eventos do dono e não da ontologia. A linha de evento
traz o id e o nome. A linha de capacidade e a de modelo de leitura dizem quem trabalha na
faixa e o que se lê nela, e não são as entidades capacidade e modelo. O ponto quente é uma
pergunta que ficou aberta. Nenhum desses tipos é nome que vá a documento novo.

⟨faixa da story, do Plano dela: as linhas na ordem, com id, tipo e texto⟩

### As entidades

Cada linha abaixo é uma entidade da casa nova, com a definição dela, tirada das shapes. A
ficha completa das candidatas da sua unidade vem no bloco da unidade. Se a leitura apontar
para outra entidade, leia a definição dela na shape, com `repo ler`.

⟨índice das entidades: uma linha cada, slug e definição da shape⟩

Se nenhuma entidade serve, diga isso no registro. Não empurre o documento para a entidade
mais genérica.

Os documentos de processo seguem a taxonomia que o dono decidiu:

- **processo** é o que um executor leva do começo ao resultado, ou ao achado, numa fita
  só. Não recebe documento próprio: todo processo é de um dos três tipos abaixo, e o
  documento mora na pasta do tipo.
- **procedimento:** a ordem dos passos está escrita antes de começar, e desviar dela é
  falta.
- **missão:** o texto fixa o objetivo, as etapas e o critério que fecha cada uma, e quem
  executa escolhe a ordem.
- **exploração:** quem executa procura, para quando acha ou cansa, e usa o achado. Não
  produz resultado. Busca e heurística são partes dela.
- **instrução:** uma etapa escrita para quem a executa, com o que ler antes do comando e o
  comando. É parte de um processo.
- **guia** e **ciclo** seguem nas shapes até outra story os dissolver. Valem como
  entidade, e o registro diz que a escolha caiu numa provisória.
- O que não cabe numa fita, porque passa de uma cadeira a outra e espera a vez dela, não
  é processo: é **fluxo de valor**, com estágios, e cada estágio tem o seu processo. O
  expediente é o fluxo de valor nuclear, com o trabalho passando por atender, trabalhar e
  revisar; chegar e sair são passagens, e não estágios.

### As ligações

O tipo de ligação vem desta lista fechada, e nenhum outro:

⟨tipos de ligação do catálogo, com o que cada um liga, e as ligações que cada entidade candidata declara, com quantas cabem de cada lado⟩

O destino de cada ligação é de um de três jeitos:

- outro documento novo desta revisão: aponte o caminho dele;
- uma ficha que já está no banco (uma entidade, um card, uma obra): aponte a chave;
- uma ficha que ainda não existe (uma persona, um documento de outra revisão): marque
  como pendente, com o destino em texto.

Separe o tipo da instância. «Sobre persona» pode ser a ficha da entidade persona ou a
ficha de uma persona; diga qual.

Quando nenhum tipo de ligação encaixa, ou nenhuma entidade serve, não force: diga no
registro que não há encaixe e proponha a entidade ou a ligação nova, com origem, destino,
quantas cabem de cada lado e os trechos do documento que pedem o nome, ao lado do encaixe
mais próximo e do motivo de ele não servir. A proposta é do dono aprovar: você não grava
entidade nem ligação nova, e a unidade não fica parada por causa dela.

### O cabeçalho novo

Todo documento novo abre com este cabeçalho, inclusive o validado:

⟨forma do cabeçalho novo⟩

### Até onde você vai

- Você lê o documento da sua unidade e escreve só os documentos que nascem dele, na
  pasta da unidade: ⟨pasta da unidade⟩.
- Você não roda git e não grava no schema casa.
- Você não escreve o golden nem o estado da ficha: a orquestradora os grava.
- Você para em ⟨teto de giros⟩ giros. Se não decidiu até lá, grave o registro como não
  decidido, com o que faltou.

---

## Bloco da unidade

- Documento velho: ⟨caminho⟩
- Entidades candidatas, sem ordem, cada uma já conferida no schema casa: ⟨a do título, as
  vizinhas dela e as que o recorte sugerir, cada uma com a ficha completa e um par curto
  com a vizinha que mais se confunde: «vai para A e não para B porque…»⟩
- Destinação fixada por decisão escrita, quando há: ⟨destinação e motivo⟩

Quando a destinação ou a entidade vem fixada, ela não é candidata: não a reabra. Os casos
que valem para toda revisão:

- observação (levantamento, parecer, fichamento, figura) sai validada, sem reescrita. A
  conferência de nomes roda nela também, e o caminho, o cabeçalho e as ligações seguem a
  ontologia; o corpo guarda as palavras da data em que foi escrito, e os nomes dele sem
  encaixe vão só à lista termos do registro;
- SKILL.md é gatilho; os arquivos de apoio da skill seguem a entidade que a leitura der.

---

## Antes de gravar o registro

Releia isto depois de ler o documento velho:

1. Evidências e critério de identidade primeiro, entidade e destinação depois.
2. Todo nome da casa no registro e nos documentos novos passou pela conferência, e cada
   um está na lista termos do registro com a saída que teve.
3. Destinação é uma das cinco; pertence à revisão N e não decidi são saídas, sem
   documento.
4. Grave o registro na pasta da unidade e devolva só o caminho dele e o estado.
