# Card

Como se escreve o corpo do épico e da feature, os itens do inventário da feature e o
comentário. O inventário são as três listas ligadas à feature no rastreador: peças,
regras de negócio e produtos documentais. O que entra em cada seção está na régua dela,
na classe do card (`infra rodar ontologia -- ler epico`, `feature` ou `comentario`), e
`tarefas modelo` serve o mesmo. Leia a régua antes de escrever. Aqui fica só o que ela
não diz, e quando os dois brigam vale a classe.

O card tem dois leitores. O dono lê o corpo, aposta e valida as regras, e larga o card
quando trava num termo que não conhece ou num mecanismo que não é dele. Quem constrói lê
o inventário e precisa de exatidão. O corpo se escreve para o dono, e o inventário, para
quem constrói.

## A função de cada seção

- **Propor:** Problema, Resultado, Features, Serve a, Solução, Uso, Fora, Apetite e
  Risco aceito.
- **Conferir:** Medida, Sai quando e a linha Confere do requisito.
- **Obrigar:** Regra de negócio.
- **Contestar:** Caso, Tamanho e Porque do buraco.
- **Relatar:** Descartado e Dita em, na decisão.
- **O núcleo e a voz, pela redação abaixo:** a peça e as outras linhas do comentário.

## Em todo o card

- **Cada seção se lê sozinha.** O dono lê uma seção sem as outras. O termo da casa leva
  o nome comum ao lado na primeira vez em cada seção, e o nome que só outra seção
  explica não entra.
- **Uma palavra para cada coisa.** O termo que nomeia duas coisas no mesmo card obriga
  quem lê a adivinhar qual é. Dê um nome a cada coisa e não o troque.
- **O item pela chave ou pelo nome.** Em qualquer seção, peça, regra e produto
  documental se citam pela chave do item (5000.r3) ou pelo nome, e nunca pela posição
  numa lista: a posição muda quando um item sai.
- **O que o rastreador guarda fica fora.** Ordem, estado, executor, bloqueio e data de
  decisão aparecem na tela do card, e o texto que os repete envelhece sem aviso.

## O corpo do épico e da feature

### Título

No épico, o que passa a ser verdade, e para quem: «As cadeiras trabalham só na casa
nova». Na feature, a coisa que vai existir, pelo nome que quem a usa daria a ela. Nos
dois, nada de nome interno, metáfora ou dois-pontos seguido de lista.

### Problema

A pessoa entra pelo papel («a cadeira que executa uma story», «o dono»), e o custo, pelo
que ela perde: tempo, retrabalho, erro ou decisão às cegas. Quem não sabe o custo
pergunta à cadeira dona do card antes de escrever. Todas as frases contam o mesmo caso.

A solução escrita como falta tem dois sinais: «não tem um comando que…» e «mora em X e
não em Y». Reescreva pelo que a pessoa tenta e onde trava.

- Ruim: «A porta mora no repositório do harness, e não no core.»
- Bom: «A mesma cadeira recebe instruções diferentes conforme o programa em que o dono
  a abre, porque o texto que a põe para trabalhar foi escrito à mão para cada programa.
  O dono descobre quando a cadeira erra.»

### Resultado

O verbo é o que a pessoa passa a fazer. «O comando existe» é entrega, e não resultado.

- Bom: «A cadeira que executa uma story recebe as regras dela junto, onde hoje lê a
  feature inteira.»

### Medida

Com mais de quatro linhas, escreva a Medida em lista, um item por coisa medida, com as
partes dela juntas no mesmo item, porque quem lê não pareia listas separadas de cabeça.

### Features

- Ruim: «Porta e posto construídos no modelo novo: a porta servindo os gatilhos, os
  verbos e o pacote do espelho, o posto replicando a conduta a cada fornecedor e o site
  lendo a casa nova.»
- Bom: «Porta e posto no modelo novo: é por ela que a casa nova chega às cadeiras, em
  qualquer programa.»

### Serve a

Use as palavras do épico, para quem lê achar a linha lá.

### Solução

A primeira frase diz a troca: o que passa a existir no lugar do quê. A frase com
«quando» é cena de uso ou regra: mova-a para Uso ou para o inventário.

- Ruim: «Quando a cadeira lapida a feature, ela grava cada peça, regra e produto
  documental como item do inventário.»
- Bom: «A lista sai do corpo do card e vira dado do rastreador, ligada à feature. O
  corpo fica com a aposta, que o dono lê numa tela. O rastreador entrega a lista em
  fatias a quem precisa dela e confere as ligações que em texto ninguém conferia.»

### Uso

Uma cena por linha, no presente, com quem age como sujeito da frase.

- Bom: «O dono abre a feature na tela, lê a aposta e vê o inventário numa aba à parte,
  com a contagem das regras por validar.»

### Apetite

A fita é a sessão de trabalho de uma cadeira. O Apetite é o limite de quem aposta, e
não a estimativa de quem constrói, que vai a um comentário.

### Sai quando

O como é o comando pronto para copiar, ou a leitura que alguém faz, dita pelo nome. Com
mais de quatro conferências, ou com o valor de hoje ao lado, use lista, uma conferência
por item.

## O inventário da feature

Cada item se lê sem o corpo, porque a aba do card e a leitura da story o servem sozinho.
Classe, chave e ligações são campos do item, e o texto não os repete.

### Peça

O nome da coisa, como substantivo, e o que ela faz para quem a usa, numa frase: «A aba
Inventário, na tela do card aberto, que mostra ao dono as três listas, uma peça por
vez.» Ação não é peça: «criar o comando X» é tarefa de story. O comportamento de uma
peça («a leitura em fatias», «a conferência da entrega») é regra dela.

### Regra de negócio

A regra guarda quatro partes separadas, e cada uma tem um leitor.

- **A frase** diz a regra, e não um caso: o que a casa passa a fazer, guardar ou
  proibir, numa oração que o dono valida lendo só ela, pela régua de
  `funcoes/obrigar.md`. Teste: mudar a frase muda o que a casa faz, guarda ou cita? Se
  só muda o jeito de a máquina chegar ao mesmo resultado, é mecanismo.
- **O porquê** diz o motivo numa oração, sem repetir a frase com outras palavras. É
  dele que quem constrói tira o caso vizinho.
- **Os casos**, de um a três, na forma «caso → resultado», na língua de quem usa. A
  seta liga a situação ao resultado, e não faz as vezes do verbo da regra.
- **O mecanismo** diz como a máquina cumpre a regra: campo, formato, prazo, lugar do
  código. É de quem constrói, e não vai ao dono.

Exemplo:

```
frase:  todo arquivo que um programa lê é cópia gerada, e nunca fonte
porquê: a cópia escrita à mão diverge sem ninguém ver
casos:  arquivo do posto editado à mão → a geração seguinte o sobrescreve
        cópia diferente da gerada → a esteira do posto reprova
```

## O comentário

O comentário é uma micropublicação pontual e imutável ligada ao card. Os metadados e
ligações (ato, destinatário, alvo, evidências de apoio, resposta e revisão) vão como dado
estruturado na chamada, sem prefixos redundantes (`Para:`, `Caso:`, `Onde:`, `Dita em:`,
`Substitui:`) no texto livre.

### Primeira linha

Traz a conclusão primeiro (até 256 caracteres), pelo nome das coisas, sem repetir
metadados que já vão nos campos da micropublicação.

- Ruim: «buraco: o lint casa_por_caminho da regra 13 e da medida hoje não detecta
  caminhos da casa atual em platafirma-posto nem em platafirma-harness»
- Bom: «buraco: o lint de caminho da casa velha não acusa nada; a medida passaria com o
  erro»

### Campos exclusivos do papel e justificativa

Permanecem no texto apenas os campos próprios do papel (`Decide` na pergunta; `Tamanho` e
`Remendo` no buraco; `Confere` no requisito; `Descartado` na decisão) e no máximo um
parágrafo de justificativa. O que passa de um parágrafo vira insumo do card (`tarefas
insumo criar`), apontado em `apoio`.

### Fecho e revisão

Fechar, corrigir ou retratar grava uma nova mensagem ligada à anterior (`--responde-a` ou
`--revisa` com `--relacao corrige|retrata`), sem apagar nem sobrescrever a original. No
fecho, diga em palavras o que mudou no corpo ou no inventário, e não só o rótulo da seção
ou a chave do item.
