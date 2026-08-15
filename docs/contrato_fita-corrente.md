# Contrato do slot de fita corrente

Peça que o adaptador do chat (card 448) e o verbo de memória (card 449) partilham
para que a rotação não faça a fita nova acordar com a mesa da anterior — nem pior,
ter a própria mesa esmagada pelo ritual atrasado da fita que morreu.

Origem do desenho: minuta 0002, posição de claudinho-IA, §2 e critério de aceite 18.

## O slot

- **Chave:** `fita:<cadeira>` na instância **msg-mem** (`127.0.0.1:6380`), a mesma
  do `mesa`. Não é a malha `pf:msg` — o critério 13 continua atendido.
- **Valor:** o id da fita, string pura. Sem JSON: o compare-and-swap é comparação
  de string, e a idade sai do TTL restante.
- **TTL:** 14 dias, igual ao da mesa. Expira para não fossilizar, não para
  caducar fita viva.
- **Fora do padrão `mem:<cadeira>:<slot>` de propósito:** `mesa ver` e
  `encerrar varredura` varrem aquele padrão e acusariam a fita como chapéu órfão.

## Os atos

```
mesa fita                     mostra o id corrente e há quanto tempo abriu
mesa fita abre [--id ID]      grava o slot; sem --id gera um. stdout = o id
mesa fita fecha --id ID       limpa o slot, e só se ID ainda for o corrente
mesa anota <chapeu>           escreve a mesa; com PF_FITA no ambiente, sob guarda
```

- **A guarda é opt-in pelo ambiente.** `mesa anota` lê `PF_FITA` como já lê
  `PF_CADEIRA`. Havendo id, a escrita só passa se o slot ainda for aquele id;
  não havendo, comportamento de sempre — sessão de mão (claude.ai, terminal) não
  tem fita registrada e não deve travar.
- **Recusa é declarada:** saída 3 e linha em stderr nomeando a fita corrente.
  Nunca silêncio, nunca escrita parcial.
- `--se-fita ID` sobrescreve o ambiente; serve para prova e para chamada avulsa.

## O que o adaptador faz

1. **Abrir fita:** `export PF_FITA=$(mesa fita abre --id <session_id do Code>)`
   antes de invocar o motor. Passando o `session_id` do Code como id, o slot e a
   sessão têm a mesma chave e não há segundo cadastro a reconciliar.
2. **Todo giro** herda `PF_FITA` no ambiente do processo. Nada mais é preciso: a
   guarda viaja no ambiente, não na lembrança do modelo de passar uma flag.
3. **Rotação:** registra o id velho, dispara o ritual (`encerrar fita
   --so-memoria`) com `PF_FITA=<id velho>`, e abre a fita nova sem esperar. A
   ordem deixa de importar — o ritual atrasado se descarta sozinho.
4. **Fechar:** `mesa fita fecha --id <id velho>` depois do ritual.

## Fronteira — o que o verbo não faz

- **O `flock` é do adaptador.** A guarda por id é o que dá correção; o lock só
  aumenta a chance de a fita nova nascer com a mesa já fechada. Correção não
  depende dele.
- **A purga do JSONL é do adaptador, depois do giro.** O ritual roda *dentro* da
  fita que morre: apagar o próprio JSONL no meio do giro não funciona — o Code
  reescreve o arquivo ao terminar. Quem apaga é quem sobrevive ao processo.
- **O par sala↔fita é do adaptador.** O slot guarda o id corrente da cadeira, não
  o endereço da sala.
