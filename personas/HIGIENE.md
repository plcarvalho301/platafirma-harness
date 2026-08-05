---
tipo: régua de qualidade
aplica-se-a: personas/persona-*.md · tool-manifest/*.md · saída de persona (resposta, card, mensagem de fila)
dono: claudinha-gestao-estrategica (RH)
---

# Higiene de escrita — persona, manifesto e resposta

Nove regras. Cada uma nasceu de um defeito observado, não de gosto. Onde há
caso, ele está nomeado — regra sem caso é especulação e sai daqui.

## 1. Ponteiro, nunca valor

Texto de persona guarda **remit e regra**: matéria durável. Estado medido tem
sistema de registro próprio, e copiá-lo para dentro do prompt cria uma segunda
fonte que ninguém atualiza.

Sai de persona e de manifesto: contagem de obra, de chunk ou de card;
`acervo_sha`; lista de "o acervo tem / não tem"; data de verificação de acervo;
versão de dependência; qualquer número que uma ferramenta responde.

Entra no lugar: o nome da ferramenta que responde. Tamanho e composição do
acervo → `acervo-status`. Faceta e população → `rag_facets`. Estado de card →
o rastreador.

> Caso: a instruction do claudinho-TI declarava o acervo sem artesania de
> código, contra `acervo_sha 0eceb9cd`. Em 05/08/2026 o sha era outro e as três
> obras estavam lá. O Pedro tomou decisão de curadoria a partir do número
> fóssil.

## 2. Positivo, com a razão colada, sem absoluto

Peça o que fazer, não o que não fazer; ancore a ordem numa razão, porque
instrução com motivo sobrevive à paráfrase; evite o absoluto, que o modelo
quebra e depois abandona a regra inteira.

`Não responda de memória` → `Consulte o acervo antes de opinar sobre matéria
coberta, porque opinar de treino sobre o que o corpus responde é desperdício`.

NEGATIVAS é a exceção deliberada: ali o negativo é o efeito procurado, e por
isso a seção é curta e só entra com invasão observada.

## 3. Sem citação do acervo colada na frase

Card, comentário de card, mensagem de fila e resposta de conversa não citam
obra do acervo para justificar a própria afirmação. Quem lê não vai buscar a
obra, e a persona destinatária paga a revisão de uma citação que não muda o
argumento.

Corte: **se remover a referência não muda o que a frase afirma, ela sai.**

Fichamento, resenha e vínculo normativo continuam citando — ali a obra é
objeto, não autoridade. `ont:0077` já proíbe em artefato registrado; esta regra
é operacional e na mesma direção, não emenda de alcance.

O que substitui a citação: **confiança declarada**. Diga o que é medido, o que
é derivado e o que é leitura. Corpus ausente não é razão para não responder; é
razão para declarar confiança.

## 4. Sem log de processo na resposta

Não abrir com inventário do que se leu, não narrar chamada de ferramenta, não
fechar com bibliografia nem com "fontes consultadas". A resposta começa pela
resposta.

Recapitulação tem uma exceção só: a linha de estado de trabalho multi-turno.

## 5. Sem placeholder fóssil

`[texto fixo, sem alteração]`, `TODO`, `{gerência}` e seção comentada não
sobrevivem ao commit. Placeholder num prompt em produção é instrução literal
para o modelo: ele lê e obedece o que está escrito.

> Caso: `FRONTEIRA: [texto fixo, sem alteração]` esteve em produção na persona
> do claudinho-TI — a cadeira ficou sem a seção que suprime o default de
> ajudar.

## 6. Texto fixo é idêntico ao caractere

ATIVAÇÃO e FRONTEIRA se copiam do template sem reescrever. Mesma regra escrita
de dois jeitos é duas regras, e a diferença aparece como comportamento
divergente que ninguém consegue rastrear.

## 7. Uma fonte por artefato

Persona mora em `platafirma-harness/personas/`. Manifesto mora em
`platafirma-harness/tool-manifest/`. Quem precisar do texto em outro lugar
aponta o caminho; não copia.

Cópia de texto de persona em documento de outro repo é defeito a corrigir, não
redundância defensiva.

## 8. Ferramenta se descreve pelo uso, não pelo estoque

No tool-manifest: cada linha diz **quando chamar** e **o que a chamada
responde**. Presença sem uso declarado não justifica linha.

Cada item declara como foi verificado — `[exec]` executado · `[func]` usado de
verdade · `[inst]` presente, sem prova. `[inst]` é confissão, não aval.

## 9. Nada que as Profile Preferences já digam

Tom, formato de resposta, tamanho, uso de lista, proibição de bajulação — tudo
isso já está condicionado fora da persona. Repetir dentro não reforça: cria
duas instruções sobre a mesma coisa, com redações diferentes, e a divergência
é que vai ser obedecida.

Persona diz **o que a cadeira é e decide**. Preferences dizem **como se
escreve**.

## 10. Onde a régua mora depende de quem precisa alcançá-la

Régua de ferramenta é de quem é dona da ferramenta, e sai da persona. Mas o
veículo se escolhe por alcance, não por elegância:

- **Skill** alcança sessão de claude.ai. É o veículo de régua que vale para as
  cadeiras que conversam.
- **Skill não alcança Claude Code.** Instância que roda no Code — a fábrica —
  não carrega skill nenhuma. Régua que precise valer lá mora em **manifesto**,
  que é arquivo de repositório e se lê por chamada.

Antes de mover régua de persona para skill: a lista de instâncias que precisam
dela roda toda em claude.ai? Não rodando, o destino é manifesto.

O que a cadeira usa a ferramenta *para* continua na persona dela, sempre.

---

## Checklist de revisão

Antes de commitar persona ou manifesto:

1. Algum número que uma ferramenta responderia? → vira ponteiro.
2. Alguma seção sem efeito de condicionamento nomeado? → sai.
3. ATIVAÇÃO e FRONTEIRA batem ao caractere com o template? → `diff`.
4. Alguma instrução em negativo que caberia em positivo com razão? → reescreve.
5. Placeholder, TODO ou chave `{}` sobrando? → sai.
6. Núcleo dentro de 160–210 palavras; total dentro de 450? → conta.
7. Alguma regra que já está nas Profile Preferences? → sai.
8. Linha 1 na forma `Você é <nome-canônico>,` e `FERRAMENTAL:` apontando
   caminho que existe? → `monta_sessao(cadeira="<cadeira>")`.
