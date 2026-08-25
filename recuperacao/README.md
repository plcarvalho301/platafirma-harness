# `recuperacao/` — o Recuperador

- **Dono:** claudinho-IA (contrato, envelope, medição e ordem de release)
- **Canônico:** `platafirma-arquitetura/docs/specs/spec_recuperador.md` · `arq:0064`, `arq:0065`, `arq:0067`
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
| `adaptadores/` | núcleo + registro, fila, mesa (#2298), wiki (#2301), acervo (#2302) e board (#2300) |
| `pep.py` | PEP por fonte: decide, nega o pedido inteiro, monta a recusa (F1, #2303) |
| `gold.py` | gerador de gold das fontes exatas, um só e parametrizado (F2, #2309) |
| `cache.py` | chave por fonte, TTL por classe e `rec:stat:<fonte>` (F2, #2308) |
| `gold.py` | gerador de gold das fontes exatas, parametrizado (F2, #2309) |
| `test_contrato_*.py` | 85 testes; o gatilho é `.github/workflows/recuperacao-tests.yml` |

Não entra aqui: roteamento e tabela `fonte` (#2304) e gate (F3).

```
# desta pasta; ambiente resolvido de pyproject.toml + uv.lock, nao adivinhado
uv run --group dev pytest . -q   # 315 passed, 5 skipped (25/08/2026)
# deps de runtime (pyyaml, tokenizers) estao em pyproject.toml; `uv` monta o venv sozinho.
# gate: .github/workflows/recuperacao-tests.yml roda isto em push que toca recuperacao/**.
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

| `board` por chave exata (`item:2300`) | **27,0 ms** | 1 |
| `board` por eixo de linha, k=8 | **64,4 ms** | 8 |

Todas ficam abaixo do timeout de 250 ms da classe exata (§8) — o palpite calibrado
sobrevive ao contato com as cinco fontes exatas. A mais cara é a listagem do board, e o
que ela paga é a versão por item: uma chamada a `/eventos` por item, para que a versão
seja `max(evento.id)` DO ITEM como o §4 manda, e não o carimbo do board inteiro.

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

Cinco das seis fontes alcançadas aqui; a sexta (board) está na seção seguinte.

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

## F1 · card #2300 — board, a sexta fonte

| adaptador | contrato usado | chave | versão | carimbo |
|---|---|---|---|---|
| `board.py` | HTTP do rastreador: `GET /api/itens?campos=`, `/api/itens/<id>`, `/api/itens/<id>/eventos`, `/api/carimbo` | `item:<id>` | `max(evento.id)` do item | `<max(evento.id)>/<contagem>` |

**A versão é do ITEM, e isso deixou de ser aspiração.** `GET /api/itens/<id>/eventos`
existe e devolve o ledger do item, então o `evento.id` máximo do §4 é computável — não foi
preciso servir o carimbo global no lugar da versão, que é o desvio que estava no radar.
Custo medido: 5 ms por item no loopback, ~40 ms para k=8, dentro dos 250 ms.

**Item sem linha no ledger serve `0@<carimbo>`.** O ledger `evento` começou a ser escrito
em #2307 — antes dele a tabela estava vazia com 385 itens no board. Item mais velho que a
migração não tem `max(evento.id)`, e as três saídas eram: preencher com timestamp (o §5
proíbe: falha em dois atos no mesmo instante e em apagar-e-criar), omitir (viola a
invariante 1) ou declarar. Declara: `0@203` diz "ledger não cobre este item, e o board
inteiro está no carimbo 203". Vira número puro sozinho, conforme o ledger alcança os itens.

**Nunca `conteudo`, para nenhum valor de `texto`.** O §5 é literal — `id, título, fase,
cadeira, nível, pai` na linha e o resto por `ref`. `texto=secao` não muda o que o board
serve; a descrição do card mora atrás da `ref`. Servir corpo aqui transformaria leitura de
estado em despejo de board no contexto: `GET /api/itens` sem projeção são 493.576 bytes.

**A projeção do #2299 é o que torna o adaptador viável**, e é pedida sempre: 56.771 bytes
contra 493.576, 8,7× menor. Medido por claudinho-TI em 20/08; não remedido aqui.

**Filtro de linha vai à fonte; termo é recorte local.** `cadeira`, `estado`, `nivel` e
`origem` são os eixos que a API aceita — filtro fora deles devolve 400 nomeando o campo
(`?q=cache` reprova, medido). O adaptador não repassa o que a API recusaria: mandar assim
mesmo derrubaria a fonte inteira por causa de um filtro que ele sabe recortar sozinho.
Busca por termo no título é filtrada aqui, sobre o que a projeção já trouxe — o mesmo
recorte que o `registro` faz sobre `listdir`, e nenhum estado novo é derivado.

**Custo em token, medido com `qwen2.5.json`:** envelope de 1 item do board 115 tokens
(item só-`ref`: 78); envelope de 8 itens 731 tokens. Fica na mesma ordem do item de fila
(133) e confirma o que o F0 já dizia: a procedência custa mais que a referência.

**Conformidade contra o rastreador vivo, e ela roda:** o conjunto de ids do adaptador bate
com o de `tarefas listar --cadeira claudinho-IA --estado priorizada`, e dois `GET`
seguidos não movem o carimbo — o aceite do #2307 conferido do lado do consumidor.

## F2 · card #2308 — chave por fonte e `rec:stat`

`rec:<fonte>:<carimbo>:<sha256(alvo NFC/trim · filtros canonizados · k · texto)[:16]>`, no
`motor-cache` (`127.0.0.1:6381`, `allkeys-lru`, 1 GB, sem AOF — #2306). **Uma linha por
FONTE:** o envelope é montado de N linhas, e board volátil não derruba cache de acervo
estável. Cache por envelope teria taxa de acerto de envelope, que é o produto das taxas.

**`sujeito` não entra na chave, e diverge da forma sugerida na carta de claudinho-TI**
(`rec:<fonte>:<sujeito>:<carimbo>`, 20/08/2026). O §9 é explícito e a decisão é minha: o
PEP roda por fonte ANTES do lookup, e o cache guarda resposta da fonte, nunca decisão de
acesso. Sujeito na chave não é só espaço desperdiçado — é a forma de esquecer que o PEP
precisa rodar antes, porque a chave passa a *parecer* segura sozinha.

**`k` e `texto` entram no hash.** A mesma pergunta com `k=3` e com `k=8` devolve conteúdo
diferente; servir um pelo outro seria o cache mentindo dentro do contrato.

**A invalidação é chave nova mais LRU, sem varredura.** Carimbo novo produz chave nova, e
a velha é despejada por pressão — `notify-keyspace-events` está desligado de propósito, e
não há assinante de expiração neste desenho.

### O que NÃO se cacheia, e por quê

| caso | decisão |
|---|---|
| fonte caída (`fonte-nao-indexada`) | não grava — TTL transformaria 1 s de queda em 60 s de fonte morta |
| resposta vazia | **grava** — vazia é resposta da fonte, e o carimbo já a protege |
| carimbo indisponível | vai à fonte sem cache: chave com carimbo falso serviria board velho para sempre |
| valor de contrato velho ou corrompido | apaga e trata como miss — o construtor vivo é quem julga a linha |

### Acervo — desligado, e é o §9

A pré-condição é a ordem `#167 → #283 → cache`, e os dois estão **em lapidação** com
claudinho-dados (medido em 20/08/2026). Cache antes de `abrir_impressao` idempotente por
sha mede o bug, não o produto. `PF_CACHE_ACERVO=1` liga na bancada, nomeado.

A validação no hit já está escrita e liga junto: a chave do acervo não carrega carimbo — o
que invalidaria o acervo inteiro a cada re-corte de uma obra —, e cada `impressao.id`
citada é conferida contra `rec:aposentadas` (`SISMEMBER`, N ≈ 8 por hit). `SISMEMBER` que
não responde **reprova o hit**: não saber se a impressão ainda serve é motivo para
rebuscar, nunca para servir.

### `rec:stat:<fonte>` — HASH, `HINCRBY`, quatro campos

`hit`, `miss`, `bytes`, `idade`. `idade` é **soma em segundos**; a média por hit é
`idade / hit`, e guardar a soma é o que o `HINCRBY` faz sem corrida. Fonte nunca
consultada devolve os quatro campos zerados em vez de faltar: `{}` e "nenhum hit" são
indistinguíveis, e é justamente o hit rate que decide o cache semântico depois.

A medida nunca derruba a leitura — cache mudo perde o contador, não a resposta.

### Medido no Valkey vivo, 20/08/2026

| fonte | hit | leitura direta | o que isso diz |
|---|---|---|---|
| `board`, chave exata | **6,0 ms** | 23,7 ms | ~4× |
| `registro`, chave exata | **2,9 ms** | 3,4 ms | empate |

**O carimbo come o ganho nas fontes baratas, e o número mostra isso.** O hit ainda paga
`_carimbo()` — `GET /api/carimbo` no board (~5 ms), dois `git rev-parse` no registro
(~2,5 ms) —, porque o carimbo está NA chave e é ele que faz a invalidação existir. No
registro isso empata com ler a fonte inteira. Não é defeito do cache: é a conta de onde
ele paga, e o que decide se vale a pena por fonte é a série de `rec:stat`, que começa
agora. Cachear o carimbo seria cachear o invalidador — e aí nada mais invalida.

## F2 · card #2309 — gerador de gold das fontes exatas

Um só, parametrizado, em `gold.py` (§13). Roda por fonte, lê o estado PELA fonte e emite o
schema do §13. Cargo e acervo são de claudinho-dados e não saem daqui.

```
python -m recuperacao.gold --fonte board fila mesa registro wiki --saida-dir avaliacao/
```

| fonte | casos | pontuáveis | candidatos | carimbo da geração (20/08/2026) |
|---|---|---|---|---|
| `board` | 41 | 21 | 20 | `207/393` |
| `fila` | 41 | 21 | 20 | `1787275126636-0` |
| `mesa` | 15 | 8 | 7 | `i:169/7 p:e3b0c44298fc` |
| `registro` | 41 | 21 | 20 | `arquitetura:a9b380b conhecimento:bda62dd` |
| `wiki` | 19 | 10 | 9 | `rc:3015` |

**`tem_gold` continua `False` nas seis, e é o certo.** O gerador produz CANDIDATO; quem
torna a fonte calibrada é revisão humana do gabarito. Enquanto isso, `nao-calibrada` é o
rótulo honesto do instrumento desligado (§13).

**O caso `termo` sai despontuável de propósito.** Derivar o esperado do mesmo mecanismo que
o gold vai julgar é escrever o gabarito com a prova aberta. `resposta_certa: ausente` não é
gerável: é juízo sobre o corpus, e o §13 já o atribui a gabarito de autor.

### Dois defeitos que o gold achou, e é para isso que ele serve

- **Mesa lia coluna que não existe.** `feito_em` contra `esvaziado_em` no esquema vivo. O
  `UndefinedColumn` virava `sem-rota`: a mesa aparecia **caída com o Postgres de pé**, e
  nada acusava. Corrigido; os sete itens vivos voltaram.
- **Carimbo da mesa cobria uma metade só.** Era o digest das chaves do Valkey, hoje vazias
  — logo `e3b0c44298fc`, o sha do vazio, **constante** enquanto a mesa mudava. Com a chave
  do §9 isso serve mesa velha para sempre. Agora `i:<max(id)>/<contagem> p:<digest>`: as
  duas metades, e metade muda vira `?` em vez de fingir que não mudou.
- **Origem do gold carimbava com uma segunda chamada.** `AdaptadorFila._carimbo()` sem alvo
  devolve `0-0` por desenho, e 41 casos da caixa viva saíram carimbados assim. O carimbo
  agora é o da busca que gerou os casos — o §13 exige congelar por versão, e versão falsa
  faz duas coleções diferentes parecerem a mesma.

## F2 · card #2309 — gerador de gold das fontes exatas

Um só, parametrizado, no schema do §13:
`python -m recuperacao.gold --fonte board fila mesa registro wiki --saida-dir avaliacao`.
Não virou verbo em `bin/`: é bancada de medição, roda por ato meu, e verbo novo pede
linha no `tool-manifest` (dono claudinho-TI) no mesmo commit.

### Três classes de caso, e elas NÃO valem o mesmo

| classe | esperado vem de | `pontuavel` |
|---|---|---|
| `chave-exata` | do estado: a chave existe, logo resolvê-la devolve ela mesma | `true` |
| `chave-inexistente` | do estado: a chave está fora dele, logo a resposta certa é `vazia` | `true` |
| `termo` | do próprio mecanismo que será medido | **`false`** até revisão humana |

**O caso `termo` sai despontuável de propósito.** Derivar o esperado do caminho que o gold
vai julgar é escrever o gabarito com a prova aberta — mudança no recorte por termo viraria
linha nova nos dois lados, sem alarme. É a mesma disciplina da matriz sujeito × fonte.
Emite-se assim mesmo porque revisar candidato é barato e inventar caso do zero é caro, mas
quem o torna pontuável é uma pessoa.

**`resposta_certa: ausente` não é gerável, e é decisão, não lacuna.** `vazia` é «a fonte
respondeu e não há o que casar»; `ausente` é «a fonte não cobre este assunto», que é juízo
sobre o corpus. O §13 já o atribui a gabarito de autor.

**A wiki é a única que precisa de semente** (`--semente`, default `PlataFirma`): o
adaptador resolve título ou busca prosa, e não expõe `list=allpages`. A semente enviesa a
AMOSTRA, nunca o gabarito — o esperado continua vindo do estado.

**Fonte sem estado levanta em vez de emitir gold vazio**, e as outras continuam: gold vazio
é pior que gold ausente, porque parece medido.

### Rodado contra as cinco fontes exatas vivas, 20/08/2026

| fonte | casos | pontuáveis | candidatos |
|---|---|---|---|
| board | 41 | 21 | 20 |
| fila | 41 | 21 | 20 |
| mesa | 15 | 8 | 7 |
| registro | 41 | 21 | 20 |
| wiki | 19 | 10 | 9 |

### O gold achou defeito na primeira rodada, e é para isso que ele existe

Rodando os casos **pontuáveis** contra as próprias fontes:

| fonte | acerto | erro |
|---|---|---|
| `board` | **21** | 0 |
| `registro` | **21** | 0 |
| `fila` | 1 | **20** |
| `mesa` | 1 | **7** |
| `wiki` | 1 | **9** |

**A chave de procedência não é alvo aceito em três das seis fontes.** `board` resolve
`item:2300` e `registro` resolve `adr:0064`; `fila`, `mesa` e `wiki` esperam outra coisa
como alvo (a caixa, o chapéu, o título) e devolvem vazio quando recebem a chave que elas
mesmas emitiram. Não é defeito do gold: o §4 define a chave e o §10 vai pedir
re-resolução por ela no gate, então a assimetria é do contrato de alvo, não do gabarito.
**Fica nomeado, não consertado aqui** — uniformizar alvo mexe em três adaptadores
entregues e é decisão do dono, não do card do gerador.

### Achado corrigido no caminho: a mesa lia coluna que não existe

`adaptadores/mesa.py` consultava `feito_em`; a coluna do esquema vivo é `esvaziado_em`
(medido em `information_schema`, 20/08). O `UndefinedColumn` caía no `except` e virava
`sem-rota`: **a mesa aparecia CAÍDA com o Postgres de pé**, e nada acusava. Consertado no
mesmo commit — a fonte agora serve os itens que `mesa ver` mostra, e é por isso que o gold
dela existe. Presença de rota não é prova de leitura, e foi o gold que produziu a prova.

Dois testes de mesa também mediam a bancada em vez da peça: passavam porque `psycopg`
não estava instalado no ambiente do gate e porque `PF_CADEIRA` estava exportada. Agora
injetam uma metade muda e apagam a variável.
