# tool-manifest — claudinha-gestao-estrategica

Forma em `tool-manifest/TEMPLATE.md`.

Verificação: `[exec]` executado · `[func]` usado em trabalho real ·
`[inst]` presente, sem prova.

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/TODA-CADEIRA.md`.

## Verbos próprios

```
escrita das personas            : persona abrir | conferir | salvar -m "<msg>"
abrir cadeira                   : persona prover <cadeira> [--alias "<Nome>"]
dar/tirar gerência              : persona designar | dispensar <cadeira> <gerência>
migrar competência              : persona remover <gerência> <de> <para>
suspender / reabrir             : persona afastar <cadeira> --gatilho "<cond>" | reverter <cadeira>
encerrar cadeira                : persona desligar <cadeira> --motivo "<txt>"
estado atual, por replay        : persona foto
a série datada                  : persona filme [cadeira]
```

Vocabulário emprestado do `dom_tipo_evento` do mdm-rh: a cadeira é o vínculo, a gerência
é a função. Ledger append-only em `personas/eventos-org.jsonl` — **não se edita**: erro
se corrige com evento novo, como no golden source de RH. `--em AAAA-MM-DD` é a data do
FATO, não a da digitação; `--autor` responde quem decidiu.

## Conectores

## Armadilhas medidas

As quatro anteriores eram do Vikunja (bucket, label, projeto 46) e morreram com ele em
16/08/2026. Estas são do rastreador próprio, medidas na mesma data:

- **Leitura singular de item ENGLOBADO devolve o absorvedor, calado.** `GET /itens/173`,
  englobado no 169, responde com `id: 169` e o título do 169; a listagem devolve 173 certo,
  como `Englobada`. Testado em cinco ids não-englobados: singular e lista batem. Quem confere
  englobamento pelo singular conclui que a escrita não pegou. Conferir pela lista.
- **`nivel` É patchável, mas só como INTEIRO** — 0 épico, 1 feature, 2 story, 3 task
  (`CAMPOS_PATCH`, api/logica.py:83; medido em 18/08/2026 com item descartável). `{"nivel":
  "story"}` devolve erro de tipo, e a mensagem fala de tipo sem dar a escala: quem tenta a
  string desiste achando o campo imutável. `POST /itens/<id>/converter` continua só fazendo
  incidente → story.
- **Promover item COM filhas é recusado**: o nível do pai é copiado em cada filha
  (`pai_nivel`). Despendurar, promover, rependurar.
- **`nivel` e `pai` no mesmo PATCH falham** quando os dois mudam: a validação de vínculo roda
  contra o pai antigo. Dois patches.
- **Escrita em lote é `PATCH /itens`** com `{"itens":[{"id":N,...}]}`, e a resposta é POR
  ITEM: 200 mesmo com falha dentro. Ler `resultados[].resultado` — `falha` não sobe no código
  da chamada.
- **`tarefas mover <pai>` propaga o carimbo à SUBÁRVORE INTEIRA, netas inclusive.** Medido em
  20/08/2026: `tarefas mover 2284 em-execucao` respondeu `filhas movidas junto:` e levou onze
  cards de F2, F3 e F4 para `em-execucao` — nenhum deles em execução. Pior, o pai NÃO muda de
  estado próprio: ele exibe estado derivado (`[derivado; cru: Em parecer]`), e continuou em
  `captada` no banco. Ou seja, mover o pai não faz o que o nome diz e faz o que ninguém pediu.
  Carimbar fase é carimbar as filhas que estão sendo tocadas, uma a uma. Reversão para
  `priorizada` é aceita e foi usada.
- **`pessoa` não é patchável** — `{"pessoa": "..."}` devolve `campo não atualizável: pessoa (vem
  do cabeçalho da borda)`. Transferir card entre cadeiras não se faz por escrita: acontece no
  despacho pela fila. Medido em 20/08/2026 no #2343.
- **`tarefas ler <id>` não mostra comentário nenhum**, e é onde o trabalho das cadeiras é
  escrito. `tarefas comentarios <id>` é o verbo. Card com `tem_descricao: false` e o trabalho
  todo em comentário é o caso comum, não a exceção — quem confere entrega pelo `ler` conclui
  que ninguém fez nada. Nomeado a claudinho-TI pela claudinho-dados no #283 do #2313.
- **Sign-off não tem verbo.** Só por `tarefas api-corpo POST /itens/<id>/sign-offs`, com
  `aprovador` e, opcionalmente, `decisao` — decisão AUSENTE é o aprovador pendente, que é a
  forma de registrar quem ainda não assinou. `recusado` exige `texto`, senão a API recusa.
  Sign-off NÃO move o item.

## Pendências declaradas

- Seção `## Conectores` ainda vazia: nenhuma tool de conector foi verificada por
  esta cadeira com prova de uso.

## Minuta — deliberação entre cadeiras

`minuta ler` · `escrever` · `circular` · `formalizar`, no manifesto comum
(`tool-manifest/TODA-CADEIRA.md`). Verbo de toda cadeira; dona da matéria:
claudinha-gestao-estrategica. **Nunca é leitura automática** — só roda chamada,
por ping `tipo: minuta` na caixa ou ordem do dono. Protocolo:
`platafirma-arquitetura/minutas/PROTOCOLO.md`.
