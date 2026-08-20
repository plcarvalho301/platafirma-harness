# `recuperacao/` — o Recuperador

- **Dono:** claudinho-IA (contrato, envelope, medição e ordem de release)
- **Canônico:** `platafirma-arquitetura/docs/spec_recuperador.md` · `arq:0064`, `arq:0065`, `arq:0067`
- **Cards:** #2284 (épico) › #2291 (F0) › #2296 (envelope e enums) · #2297 (disjuntor e contrato)

Biblioteca importada, nunca subprocess. Vive no `ops-mcp` e em nenhum outro consumidor.
`bin/recuperar` é o verbo fino que importa daqui — e ainda não existe: ele entra com os
adaptadores, no F1.

## O que este commit entrega (F0)

| arquivo | o que é |
|---|---|
| `envelope.py` | `Envelope`, `Item`, `Procedencia`, `Versao`, `Sinal`, `LinhaFonte` e os quatro enums fechados |
| `fontes.py` | as seis fontes, classe de consulta, timeout por classe, prefixo de chave |
| `disjuntor.py` | `Disjuntor` por fonte e `Painel`, com estado observável |
| `test_contrato_envelope.py` · `test_contrato_disjuntor.py` | 58 testes; o gatilho é `.github/workflows/recuperacao-tests.yml` |

Não entra aqui: adaptador, PEP, roteamento, cache, gate de procedência. F1–F3.

```
python3 -m pytest recuperacao/ -q      # da raiz do repo; precisa de `tokenizers`
```

## Medição — 20/08/2026, tokenizador `qwen2.5.json` (vocab 151.643)

| envelope | tokens |
|---|---|
| sem itens, uma fonte, `vazia` | **14** |
| recusa de disjuntor, uma fonte | **36** |
| seis fontes, todas caídas | **113** (era 209 antes do corte da linha redundante) |
| um item do board, com carimbo | 69 |
| um item do acervo, com sinal, digest e casamento | 127 |

O teto de **40 tokens** do envelope sem itens (§3, inv. 3) é o único número duro da
spec, e é ele que impede o envelope de virar imposto por giro. O de 113 é teto de
**regressão**, não meta: existe para que uma volta a 209 apareça como falha.

## Três decisões de contrato tomadas aqui, e por quê

Todas dentro do remit do dono do envelope; nenhuma reabre decisão fechada.

1. **`linhas[]` é o campo por fonte.** A tabela do §3 lista `cobertura`, `sinal` e
   `aviso[]` como escalares no topo, e a invariante 4 exige uma linha por fonte — que
   escalar não carrega com N > 1. `linhas[]` é o dado; os três campos do §3 continuam
   saindo no JSON exatamente como a spec os descreve, porém **derivados**, nunca
   redigidos em paralelo. Duas verdades sobre o mesmo fato é o defeito que isto evita.

2. **A serialização não repete o que já disse.** Com uma fonte só, `linhas` seria a
   repetição do topo e não sai. Fonte caída também não sai de `linhas`: `{fonte,
   fonte-nao-indexada, causa}` já está inteiro em `aviso[]`. A união
   `linhas[].fonte ∪ aviso[].fonte` continua sendo as N fontes consultadas — e é isso
   que o teste confere, não a presença do campo.

3. **Cobertura agregada em duas escadas.** Havendo item, manda a melhor cobertura entre
   as fontes que **contribuíram** item; não havendo, a mais informativa entre todas.
   A separação impede o defeito de rotular de `vazia` ou `ausente` um envelope que tem
   item — e respeita `arq:0064` §2, que manda a fonte caída declarar o vão sem rebaixar
   quem respondeu.

## O que ainda não está medido

- ⚪ hipótese — os timeouts de 250 ms / 2 s são palpite calibrado, não distribuição.
  O que confirma: latência por fonte com a instrumentação do §9 no ar, depois do F2.
- ⚪ hipótese — `LIMIAR_FALHAS=5`, `ESPERA_S=30`, uma sondagem. Ponto de partida
  conservador; o que os fecha é a taxa de falha por fonte, também depois do F2.
- O teto do envelope **em uso**, contra o teto em teste (§16).
