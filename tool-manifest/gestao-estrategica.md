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
- **`nivel` não é campo patchável** (`CAMPOS_PATCH`, api/logica.py). Não há como promover task
  a feature; item que perdeu o pai por violar "pai de nível estritamente menor" não é
  restaurável por PATCH. `POST /itens/<id>/converter` só faz incidente → story.
- **Escrita em lote é `PATCH /itens`** com `{"itens":[{"id":N,...}]}`, e a resposta é POR
  ITEM: 200 mesmo com falha dentro. Ler `resultados[].resultado` — `falha` não sobe no código
  da chamada.
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
