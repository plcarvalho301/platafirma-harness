# `recuperacao/` — o Recuperador

- **Dono:** claudinho-IA (contrato, envelope, medição e ordem de release)
- **Canônico:** `platafirma-arquitetura/docs/spec_recuperador.md` · `arq:0064`, `arq:0065`, `arq:0067`
- **Cards:** #2284 (épico) › #2291 (F0: #2296, #2297) · #2292 (F1: #2298 e seguintes)

Biblioteca importada, nunca subprocess. Vive no `ops-mcp` e em nenhum outro consumidor.
`bin/recuperar` é o verbo fino que importa daqui — e ainda não existe: ele entra com os
adaptadores, no F1.

## O que este commit entrega (F0)

| arquivo | o que é |
|---|---|
| `envelope.py` | `Envelope`, `Item`, `Procedencia`, `Versao`, `Sinal`, `LinhaFonte` e os quatro enums fechados |
| `fontes.py` | as seis fontes, classe de consulta, timeout por classe, prefixo de chave |
| `disjuntor.py` | `Disjuntor` por fonte e `Painel`, com estado observável |
| `adaptadores/` | núcleo do adaptador + registro, fila e mesa (F1, #2298) |
| `test_contrato_*.py` | 85 testes; o gatilho é `.github/workflows/recuperacao-tests.yml` |

Não entra aqui: PEP (#2303), roteamento e tabela `fonte` (#2304), cache (F2), gate (F3),
e os adaptadores de board (#2300), wiki (#2301) e acervo (#2302).

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

## F1 · card #2298 — núcleo de adaptador e as três fontes baratas

`adaptadores/base.py` fixa o contrato: o adaptador **levanta** `FonteIndisponivel`
(porque quem precisa saber é o disjuntor) e `busca_declarada()` transforma em linha
(porque o consumidor nunca deve ver exceção). `busca_medida()` devolve o par
(resultado, ms) — a latência por fonte não existe se ninguém a medir desde o começo.

| adaptador | contrato usado | chave | versão |
|---|---|---|---|
| `registro.py` | arquivos versionados de `decisions/`, três séries | `adr:` `seg:` `ont:` | blob sha do git, `digest` sem git |
| `fila.py` | `XRANGE` + `XINFO STREAM` (leitura **fria**) | `caixa:<slug>/<stream-id>` | o próprio stream-id |
| `mesa.py` | Postgres `sessao.mesa_item` + Valkey `mem:*` | `mem:<sufixo>:<slot>[#<id>]` | `seq` (item) · `digest` (prosa velha) |

**Nenhuma serve `coberta`, e é de propósito:** `tem_gold=False` nas três, então elas
servem `nao-calibrada` (§13). O rótulo vira `coberta` quando o gold existir (#2309).

### Medido na bancada, 20/08/2026 — estado real, não fixture

| chamada | latência | itens |
|---|---|---|
| `registro` por chave exata | **4,5 ms** | 1 |
| `registro` por termo no título | **5,0 ms** | 2 |
| `fila`, caixa própria, `XRANGE` inteiro | **56,9 ms** | 8 |
| `mesa`, duas metades | **45,5 ms** | 1 |

As três ficam bem abaixo do timeout de 250 ms da classe exata (§8) — o palpite calibrado
sobrevive ao primeiro contato com as fontes baratas. Falta o board, a wiki e o acervo.

**A procedência custa mais que o item.** Item de fila só-`ref`: 133 tokens, dos quais
**60 são procedência** e 67 o texto da referência. Um envelope de 3 fontes com 5 itens
só-`ref` sai a **645 tokens**. O teto de 40 do envelope vazio não protege disto, e é
disto que o §16 fala quando diz que o teto **em uso** não está medido.

### Conformidade — a régua do §5

`test_contrato_adaptadores.py` roda em dois níveis: contrato com cliente falso (sempre)
e conformidade contra a fonte real (pulado **com motivo** quando ela não responde).
Medido em 20/08: `registro` bate arquivo a arquivo com o diretório, e `fila` bate
carta a carta com `fila ler <caixa> --tudo` — mesmo conjunto de msgid. **Falta a
conformidade de `mesa` contra `mesa ver`**, e ela está nomeada aqui em vez de suposta.

## O que ainda não está medido

- ⚪ hipótese — o timeout de 2 s da classe semântica segue sendo palpite: o acervo é o
  único da classe e ainda não tem adaptador. O de 250 ms já tem três medições contra ele.
- ⚪ hipótese — `LIMIAR_FALHAS=5`, `ESPERA_S=30`, uma sondagem. Ponto de partida
  conservador; o que os fecha é a taxa de falha por fonte, também depois do F2.
- O teto do envelope **em uso**, contra o teto em teste (§16).
