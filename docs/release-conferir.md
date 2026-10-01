# release conferir

`bin/_release/conferir/conferir.py` implementa as classes de conferência: sub-ato do verbo
`release`, fora do PATH. As classes do servido (`verbo`, `servico`, `skill`, `procedencia`,
`superficie`, `ferramental`, `front`, `sessao`, `chapeu`, `pdp`, `alcance`, `card`, `jobs`, `acervo`) se chamam
por `release conferir <classe>`. `bin/conferir` ainda as aceita, com aviso de deprecado, e delega;
as classes de bancada (`repo`, `commit`, `arranque`, `vocabulario`, `diagrama`) respondem com aviso
apontando `lint <classe>`, e `existe` segue em `bin/conferir`.

Para saber qual classe olhar para cada pergunta, o guia é `acervo ler casa guia conferir`
em platafirma-casa. Este documento é a referência do instrumento: o que cada resultado quer dizer.

## Veredito de três estados

`resultado.py`, ao lado de `conferir.py`, dá o veredito comum. Toda classe que o adota devolve uma
lista de itens, cada um com um `Veredito` de um destes estados:

- `conforme`, sem motivo. A fábrica `conforme(desde=None)` nem aceita motivo: quem tem algo a dizer
  além de «bateu» não está conforme.
- `divergente`, motivo obrigatório: olhou, e a diferença tem descrição.
- `indeterminavel`, motivo obrigatório: não deu para olhar (fonte fora do ar, uso incompleto,
  dependência ausente). Não conseguir olhar nunca sai `conforme`.

`Veredito.__init__` recusa com `ValueError` `divergente` ou `indeterminavel` sem motivo.

`desde` é opcional nos três estados: quando a classe sabe desde quando o item está assim
(`started_at` do contêiner, `quando` da promoção), ela registra. Armadilha no `--json`:
`Veredito.dict()` grava `"desde": "indeterminavel"` (a string) quando `desde` está ausente, que não
é o `estado` do item; são dois campos que podem usar a mesma palavra.

## Linha-âncora

A primeira linha de toda saída em texto, e a chave `"ancora"` no `--json`, é colável como
referência:

```
release conferir <classe> [<alvo>]: N conforme · N divergente · N não consegui olhar — release <sha>
```

Vem de `resultado.linha_ancora`. `<sha>` é o HEAD curto do harness servido no momento da medição
(`_sha_release()`); na classe `verbo` com `--ref <rev>`, é a rev candidata materializada para medir.
Abaixo da âncora, cada item imprime `<marca> <nome>[ (desde <desde>)]` e, havendo, o motivo numa
linha indentada.

## Exit

`resultado.agrega()` decide o exit pela lista inteira, pior caso primeiro:

- `0`: tudo `conforme`;
- `1`: ao menos um `divergente` (divergente pesa mais que indeterminável: não conseguir olhar não
  pode mascarar uma divergência);
- `5`: nenhum divergente e ao menos um `indeterminavel`.

`2` (uso), `3` (dependência) e `4` (política) saem antes de qualquer item existir: classe
desconhecida, `--ref` sem rev válida, git ou docker fora do ar. Só depois que a classe produziu
itens o exit vem de `agrega()`, restrito a 0, 1 e 5. Classe conhecida e sem implementação
(`CLASSES_ABERTAS`: `canal`, `casco`) sai com aviso dedicado.

## Quem usa o veredito comum

- Servido: `servico`, `verbo`, `skill`, `procedencia`, `superficie` (`--caso conectores` e
  `--caso descricao`), `ferramental`, `front`, `pdp`, `alcance`, `card`, `jobs`, `acervo` passam por
  `resultado.relatorio()`. `acervo` usa o `extra` do relatorio para o que nao pesa no exit:
  avisos (servindo sem espelho, predicados ainda fora da classe) e a pendencia do motor dirigida
  a ia (spec espelho-de-leitura §4.2 item 6). `sessao` é medição de tokens do pacote de abertura, não veredito.
- Bancada: `repo --staged` e `arranque --staged` usam o veredito comum. `commit` usa o vocabulário
  (estado, desde, motivo) sem passar por `agrega()`: o exit vem das recusas e fica 0 mesmo com
  veredito indeterminável. `existe` tem par próprio existe/não-existe, com exit 0/1/5, fora de
  `resultado.Veredito`.
