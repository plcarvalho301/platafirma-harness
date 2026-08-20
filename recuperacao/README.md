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
| `adaptadores/` | núcleo + registro, fila, mesa (#2298), wiki (#2301) e acervo (#2302) |
| `pep.py` | PEP por fonte: decide, nega o pedido inteiro, monta a recusa (F1, #2303) |
| `test_contrato_*.py` | 85 testes; o gatilho é `.github/workflows/recuperacao-tests.yml` |

Não entra aqui: roteamento e tabela `fonte` (#2304), cache (F2), gate (F3) e o adaptador
de board (#2300), que espera a projeção #2299 de claudinho-TI.

```
# da raiz do repo; precisa de `tokenizers` e `pyyaml`
python3 -m pytest recuperacao/ politica-acesso/ -q     # 182 testes, 20/08/2026
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

## F1 · card #2303 — PEP por fonte e matriz sujeito × fonte

`pep.py` é o ponto que IMPÕE a decisão; quem decide é `politica-acesso/pdp.py`. A divisão
não é invenção da casa: PDP avalia, PEP impõe, PIP fornece atributo, PAP guarda a política
— os quatro pontos funcionais do mecanismo de controle de acesso (NIST SP 800-162 §2.4.3;
CSA Guidance v3.0 §12.7, que descreve o PEP como podendo ser tão simples quanto um `if`
dentro do serviço).

| peça | onde | papel |
|---|---|---|
| PDP | `politica-acesso/pdp.py` | avalia; biblioteca embarcada, sem rede (`seg:0008`) |
| PAP | `politica-acesso/politica.yaml` | as regras; muda por merge |
| PIP | `politica-acesso/sujeitos.yaml` | projeção interina, até o token carregar atributo |
| **PEP** | **`recuperacao/pep.py`** | **impõe, uma vez por fonte, antes de qualquer adaptador** |

### Cinco decisões, e o que cada uma evita

1. **Uma decisão por fonte**, com o par `(dominio, sobre)` que `fontes.py` já declara do
   §5. PEP único faria a concessão de uma matéria valer pela outra — que é o que
   `seg:0009` separa ao distinguir `plataforma-acervo` de `plataforma-wiki`.
2. **Negativa total** (§6): nem entre fontes, nem entre alvos da mesma fonte. Pedido de
   dois recortes com concessão de um não vira busca em um.
3. **Fail-closed em falha de mecanismo** — política ilegível, sujeito fora da projeção,
   atributo ausente: nega, e a `regra` da negativa (`politica`, `projecao`, `identidade`)
   diz que foi mecanismo, não regra do PAP. Negativa por regra é a política funcionando;
   por atributo ausente é defeito de projeção, e as duas não podem sair iguais no log.
4. **A ação é o verbo humano da matéria** — `rag_buscar`, `wiki_ler`, `msg_ler`; e
   `recuperar` nas três fontes que não têm verbo de leitura no PAP. **O recuperador não
   amplia o alcance de ninguém**: herda a concessão que já existe, e ampliar continua
   sendo merge no PAP, não linha de código.
5. **Alvo ausente vira `<prefixo>*`, nunca `*`.** `sobre` vazio vira `*` dentro do PDP e
   entrega a matéria inteira — a própria `politica.yaml` avisa. Com o prefixo, o pedido
   genérico bate na concessão nominal e é negado, como deve.

A identidade NÃO mora aqui: o PEP recebe o sujeito já resolvido. Dentro de tool, o
contexto do FastMCP é a única fonte honesta — biblioteca que adivinha identidade é
biblioteca que autoriza a si mesma. A trilha do §11 também é do host: `auditor` é
injetado, e sem ele o PEP decide igual e não registra.

### A recusa é declarada, e instrui

Recusa total mantém a invariante 4 — uma linha por fonte pedida, todas
`fonte-nao-indexada` com `sem-concessao`, porque a unidade autorizada é o PEDIDO. `falta`
nomeia o alvo e a regra que derrubaram; `proximo` diz o que pedir de novo e o que ainda
está alcançável. `sujeito` não entra no envelope (§3, inv. 5) — vai à trilha.

### Medido na bancada, 20/08/2026

| medida | valor | método |
|---|---|---|
| uma decisão | **0,017 ms** | 2.000 chamadas, PAP quente |
| pedido de 6 fontes (6 decisões) | **0,102 ms** | 200 pedidos, PAP quente |
| primeira chamada (carrega PAP + PIP) | 11,1 ms | processo novo; uma vez por vida do `ops-mcp` |
| recusa de 1 fonte | 71 tokens | `qwen2.5.json`, JSON compacto |
| recusa de 2 fontes | 92 tokens | idem |
| recusa das 6, pedido inteiro negado | 157 tokens | idem |

O PEP custa **0,04% do timeout de 250 ms** da classe exata: autorizar por fonte não é o
que vai decidir a latência do recuperador. O que custa é o envelope de recusa — 157
tokens contra os 113 de seis fontes caídas —, e o que paga a diferença é `falta`/`proximo`,
que evita a rodada seguinte.

### A matriz — `politica-acesso/test_matriz_sujeito_fonte.py`

41 casos literais, 5 sujeitos × 6 fontes. Mora junto do PAP porque quebra por merge no
PAP, não por mudança de biblioteca — e o workflow agora dispara em `politica-acesso/**`
por isso: vazamento entra por concessão, e o teste tem de ser chamado no dia em que ela
entra.

A expectativa é escrita à mão de propósito. Gerá-la da mesma política que ela confere
seria escrever o gabarito com a prova aberta: regra nova viraria linha nova nos dois
lados, sem alarme. Aqui, concessão nova só fica verde quando alguém declara que a quer.

**Prova de que ela pega, e não é verde por não haver caminho** (20/08/2026): num PAP
mutante, com as duas negativas explícitas removidas E as permissões nominais alargadas
para `wiki:*` e `acervo:*`, a suíte quebra em **9 casos**, entre eles os dois aceites
duros do §6. Só remover as negativas não vaza — o default deny e o recorte nominal
seguram sozinhos; o segundo cadeado só aparece quando alguém também alarga a permissão,
que é exatamente o cenário que `politica.yaml` descreve como "o dia em que uma tool nova
esquecer o corte".

**Achado, não defeito:** `jaiminho-fabrica` é negado nas seis fontes. O papel `fornecedor`
não tem regra de leitura de acervo, wiki nem fila, e `recuperar` não é verbo dele — a
fábrica fala por card. Está na matriz para que uma concessão futura apareça como
mudança de linha, não como silêncio.

## F1 · cards #2301 e #2302 — wiki e acervo

Cinco das seis fontes alcançadas. Falta o board, e ele não depende de mim.

| adaptador | contrato usado | chave | versão | carimbo |
|---|---|---|---|---|
| `wiki.py` | `api.php`: `prop=revisions`, `action=cargoquery`, `list=search` | `wiki:<page_id>[#seção]` | `rev_id` | `rc:<rc_id>` |
| `acervo.py` | `POST /search` e `GET /facets` do rag | `acervo:<objeto>#<âncora>` | `digest` do índice ⚠ | `acervo:<acervo_sha>` |

**Nem o wiki-mcp, nem o `rag_search`.** Os dois são outros consumidores da mesma API, com
a mesma dignidade destes. Encadear um no outro acoplaria a recuperação à superfície de
ferramenta de outra cadeira, e toda mudança de forma dela viraria quebra aqui.

### wiki — três caminhos, e quem escolhe é o alvo

| entrada | ato | por quê |
|---|---|---|
| `wiki:<Título>[#seção]` | `prop=revisions` | alvo nominal: uma página, com id e revid |
| `filtros={"tabela": …}` | `action=cargoquery` | faceta DECLARADA — predicado, não varredura de prosa |
| termo livre | `list=search` | significado na prosa, que é o que o Cargo não indexa |

`page_id`, e não título, porque **título é volátil e id não é**: mover a página troca o
título e preserva o id, e chave que muda em renomeação envelhece calada no artefato que a
citou. `rc_id` é o carimbo da FONTE (o ledger inteiro), `rev_id` é a versão do ITEM — a
spec pede os dois e eles não são a mesma coisa.

### acervo — a única que gradua

É a única fonte semântica, e por isso a única que carrega `sinal`. A régua viaja no
envelope porque duas chamadas na mesma sessão podem sair com réguas distintas: sem
`rerank`, `medida: "sim"` com piso `MIN_SIM`; com `rerank`, `medida: "rerank"` com piso
`MIN_CE`.

**`boa` do rag não vira `coberta` aqui** (§13): sem gold, `nao-calibrada`. O rótulo do rag
mede distância contra piso; o gold mediria se o retorno responde à pergunta. Promover um
ao outro é instrumento desligado fingindo medição — `cobertura_do_rag()` mantém o rótulo
dele legível ao lado, sem confundir os dois.

**`texto="secao"` desmembra a fita de `contexto`.** O rag não devolve a seção por fonte:
`fontes[].texto` é nulo e a seção recolada mora numa fita única, numerada `[n]`. Sem
partir, o envelope serviria rótulo onde a fonte serviu texto. O corte casa `[n]` com
`fontes[n-1]` **e só vale quando a contagem bate** — bloco a menos, cai para `ref`, porque
texto casado com a procedência errada é o pior defeito possível numa citação.

### Medido na bancada, 20/08/2026

| chamada | mediana | itens | envelope |
|---|---|---|---|
| wiki, alvo nominal | **12,8 ms** | 1 | 97 tok |
| wiki, `cargoquery` por domínio | **16,5 ms** | 5 | 339 tok |
| wiki, prosa (`list=search`) | **22,8 ms** | 3 | 196 tok |
| wiki, um item com trecho de 800 chars | — | 1 | 321 tok |
| acervo, `texto=nenhum` | **73 ms** | 3 | 330 tok |
| acervo, `texto=trecho` | 75 ms | 3 | 825 tok |
| acervo, `texto=secao` | 92 ms | 3 | **2.601 tok** |
| acervo, primeira chamada (com `/facets` frio) | 925 ms | — | — |

A wiki fica a 5% do timeout de 250 ms da classe exata. O acervo fica a **4% dos 2 s** da
classe semântica — o palpite do §8 sobrevive ao primeiro contato com a única fonte que o
justificava, e agora tem medição contra ele em vez de nenhuma.

**O custo do acervo é token, não latência.** Três itens em `secao` custam 2.601 tokens —
oito vezes o mesmo retorno em `nenhum`. O teto de 40 do envelope vazio não protege disto,
e é exatamente o que o §16 chama de teto **em uso** não medido.

### ⚠ Fail-closed na chave do acervo — achado de 20/08/2026

`/search` devolve `section_id` em **`curto-v1`**: um prefixo determinístico do
`document_id` (que é o sha256 do objeto), 8+ chars. O §4 é explícito — `curto-v1` é
projeção de exibição, nenhuma chave gravada em artefato o carrega, e o gate do §10 compara
o sha inteiro. **A API não expõe a forma completa por requisição**: o knob
`section_id_curto` é da instância, e desligá-lo pioraria o `rag_search` de todo mundo.

O adaptador não inventa a chave: sem forma completa, levanta `FonteIndisponivel` e a fonte
sai `fonte-nao-indexada` com `sem-indice` (34 tokens, 71 ms). `PF_ACERVO_CHAVE_CURTA=1` é
o escape de bancada, nomeado e desligado por default — escape que vira default é a forma
mais rápida de a projeção virar chave sem ninguém decidir. Todos os números acima foram
medidos com o escape ligado, para que existam quando a dependência fechar.

Dois pedidos a claudinho-dados, dono do produto (junto de #2313):

1. `section_id` completo por requisição — hoje só há knob de instância.
2. `impressao.id` no retorno de cada fonte. Sem ele a versão sai como o `acervo_sha`, que
   carimba o ÍNDICE e não a impressão da obra citada, e sai marcada `digest` justamente
   para não ser lida como a versão que o §4 pede.

Um teste de conformidade **falha no dia em que a API mudar de formato** — falhar ali é boa
notícia e tem de ser visível, e é o sinal de que o fail-closed pode sair.

### Achado na wiki: `Operar:` não é o ns 3000

O `CONTENT_NS` do `search_pages` do wiki-mcp é `0|4|12|3000`, e a docstring da tool diz
cobrir `Operar:`. No siteinfo, **3000 é `Frente:` e `Operar:` é o 3004** — nenhuma página
de `Operar:` aparece naquela busca, sem erro nem aviso. Este adaptador usa
`0|4|12|3000|3004` e passa a achar `Operar:fila`, que o verbo humano não acha. A
divergência é deliberada e está declarada no código: replicar o engano faria o teste de
conformidade passar por errar igual. Vai a claudinho-dados junto do resto.

## O que ainda não está medido

- O timeout de 2 s da classe semântica **deixou de ser palpite**: o acervo mede 73 ms de
  mediana e 925 ms na primeira chamada (com `/facets` frio). O de 250 ms tem agora cinco
  medições contra ele, a mais lenta sendo a fila com 57 ms.
- ⚪ hipótese — `LIMIAR_FALHAS=5`, `ESPERA_S=30`, uma sondagem. Ponto de partida
  conservador; o que os fecha é a taxa de falha por fonte, também depois do F2.
- O teto do envelope **em uso**, contra o teto em teste (§16).
- A trilha do §11 (uma linha por fonte, com as duas identidades) ainda não existe: o PEP
  entrega o material pelo `auditor`, e quem grava é o `ops-mcp` — que ainda não passa um.
  Enquanto não passar, negativa de acesso no recuperador não aparece em
  `~/AI/var/log/ops/`.
