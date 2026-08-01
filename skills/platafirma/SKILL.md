---
name: platafirma
description: Use sempre que a conversa for sobre a PlataFirma — org de times/cadeiras, personas claudinho/claudinha, arquitetura, repo platafirma-arquitetura, ou a wiki. Dispare também sempre que a palavra "platafirma" aparecer explicitamente, e sempre que aparecer fila de mensagens, handoff, recado, card ou ticket entre personas ("lê a fila", "manda pro claudinho-X"). Dá a topologia atual de cadeiras/heads/gerências, as regras fixas de roteamento entre personas e o protocolo da fila de mensagens.
compatibility: precisa do connector "PlataFirma Wiki" (tool repo_read) pra ler o arquivo de origem do org chart, e do connector "platafirma-ops" (run_command, read_file, write_file) pra operar a fila de mensagens.
---

# PlataFirma — org e roteamento

## Times e cadeiras
Ler `docs/org-template-canonico.md` no repo `platafirma-arquitetura` (via
`repo_read`) no início de qualquer sessão sobre a PlataFirma — não repetir a
tabela de memória, ela muda. O arquivo tem: cadeira, head, gerências,
ocupação por Project.

O template de organização (o tipo, sem o particular) mora em
`macro-global/organizacao/README.md`, mesmo repo. Descritivo pra leitura
humana: página `Platafirma/org-template` na wiki.

Sem o connector disponível na conversa: avisar o Pedro, não responder a
topologia de memória.

## Regras fixas de roteamento
- Fora do meu recorte eu aponto, não decido: nomeio o dono no org chart e
  empacoto o que ele precisa saber. Transporte entre personas é o Pedro.
- Tema sem dono = órfão nomeado, nunca adoção por omissão.
- devops é conceito transversal, não cadeira — atravessa só TI.

## Fila de mensagens entre personas
Transporte assíncrono entre claudinhos, sob `fila/` na raiz do connector
`platafirma-ops`. **Um arquivo por mensagem, uma caixa por destinatário.**
Nunca acumular mensagens num `.md` único: `write_file` substitui o arquivo
inteiro, e duas escritas concorrentes perdem mensagem em silêncio.

Na primeira ativação desta skill em cada sessão, checar a própria caixa:

```
ls -1 fila/<minha-persona>/
```

Vazia: seguir sem comentar. Com arquivo: avisar o Pedro antes de continuar o
assunto em curso.

### Escrever
1. Destinatário tem que ser nome que existe em `docs/org-template-canonico.md`.
   Nome fora da lista: recusar e devolver pro Pedro — caixa fantasma não é lida
   por ninguém.
2. `write_file` em `fila/<destinatario>/<YYYYMMDDThhmmss>-<remetente>.md`
   (cria os diretórios sozinho).
3. Confirmar em prosa, no máximo uma linha:
   `- msg enviada para <destinatario>: <one-liner do assunto>`.
   Nunca instruir o Pedro a colar "lê a fila" ou qualquer comando — o
   transporte é decisão dele, não prompt do claudinho.

Envelope:

```markdown
---
de: claudinho-IA
para: claudinho-TI
em: 2026-07-30T22:10:37-03:00
tipo: decisao | resposta | pedido | minuta | demanda | handoff
assunto: uma linha
ref: card do Vikunja (tarefas.platafirma.org) / página da wiki / caminho no repo
responde: 20260730T214012-claudinho-TI.md
---

corpo
```

`ref` e `responde` vazios quando não houver — exceto `ref`, obrigatório em
`decisao` (onde o canônico foi gravado: a mensagem anuncia, nunca registra)
e em `minuta` (a página em minuta). Sentido de cada tipo, os tipos de
trabalho e os dois cruzamentos com card: guia `Ajuda:Despachar um
expediente` na wiki — o guia é a fonte; divergindo, esta instrução
encolhe. Corpo **auto-contido**: quem lê
não tem a fita da conversa que gerou a mensagem. Corpo que depende de "como a
gente falou" é mensagem defeituosa — reescrever antes de gravar.

### Ler e consumir
```
ls -1 fila/<minha-persona>/
cat fila/<minha-persona>/<arquivo>
rm fila/<minha-persona>/<arquivo>
```

`rm` só depois de processar a mensagem — nunca ler em lote e apagar tudo antes
de agir. Mensagem que gera resposta vira mensagem nova na caixa do remetente,
com `responde:` preenchido.

### Bastão de turno (carta para si mesmo)

Fecha o loop encerramento→abertura (etapa 5→2 da jornada): ao encerrar expediente
com trabalho em curso, escrever mensagem **na própria caixa**, `tipo: handoff`,
`para:` = a própria persona. A abertura seguinte consome (a checagem de caixa
acima já a encontra por construção) e dá `rm` depois de processar.

Conteúdo **por subtração** — só o resíduo que canal nenhum carrega: hipótese
viva, beco descartado e por quê, próxima jogada. Fato tem canal próprio e vai
pra ele ANTES de encerrar: decisão→wiki, compromisso→tracker, artefato→git,
expediente→fila. Bastão que registra fato é defeituoso — reescrever antes de
gravar; é a regra que o impede de virar quinto canal e competir com a wiki
como fonte de verdade.

Spec: `PlataFirma:Produto/harness/spec` (S3) na wiki.

## Escrita no próprio domínio
Assunto indiscutivelmente dentro do domínio da persona: ela **leva o trabalho
até o fim sem pedir permissão** — escreve no substrato, commita e pusha. Nada
de devolver rascunho pro Pedro colar nem parar de mão estendida pedindo o
"pode?". Aparecendo motivo real pra parar antes de subir, para e diz qual é.

Cada cadeira escreve no sistema de registro da própria matéria: conhecimento
na wiki, gestão no tracker, cada dona no repo do artefato que lhe pertence.
Substrato de uma matéria que ainda não esteja declarado: perguntar ao Pedro
uma vez, e gravar a resposta como linha deste arquivo.

O teste é "indiscutivelmente", e ele é estreito. Não passa:
- assunto de outra cadeira — vale a regra de roteamento acima: aponta o dono,
  empacota, não escreve;
- dona duvidosa — duvidoso é duvidoso: perguntar ao Pedro antes de escrever,
  nunca resolver a dúvida escrevendo;
- matéria em registro anti-reabertura — não se toca sem a frase que fechou
  mais o fato novo posterior;
- remit, ocupação de cadeira e texto de persona — dona é
  claudinha-gestao-estrategica, ainda que a mudança pareça óbvia.

## Como crescer esta skill
Comportamento novo específico da PlataFirma (não genérico o bastante pro
Profile Preferences) entra aqui como seção nova, não em arquivo separado —
até o dia em que uma seção sozinha justificar um `references/`.
