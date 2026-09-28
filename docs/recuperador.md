# Recuperador

Contrato interno da biblioteca `recuperacao/`: o envelope, os adaptadores das seis fontes, o PEP por
fonte, o cache e o gerador de gold, com o que foi medido em cada um. O porquê do componente está em
`acervo ler casa adr arq:0064` e `acervo ler casa adr arq:0067`; a spec do recuperador é a régua
das invariantes citadas aqui.

Biblioteca importada, nunca subprocess.

## Envelope

| arquivo | o que é |
|---|---|
| `envelope.py` | `Envelope`, `Item`, `Procedencia`, `Versao`, `Sinal`, `LinhaFonte` e os quatro enums fechados |
| `fontes.py` | as seis fontes, classe de consulta, timeout por classe, prefixo de chave |
| `disjuntor.py` | `Disjuntor` por fonte e `Painel`, com estado observável |

Três escolhas de forma do envelope:

1. **`linhas[]` é o campo por fonte.** A spec lista `cobertura`, `sinal` e `aviso[]` como escalares
   no topo e exige uma linha por fonte, que escalar não carrega com N > 1. `linhas[]` é o dado; os
   três campos continuam saindo no JSON como a spec os descreve, porém derivados, nunca redigidos
   em paralelo.
2. **A serialização não repete o que já disse.** Com uma fonte só, `linhas` seria repetição do topo
   e não sai. Fonte caída também não sai de `linhas`: `{fonte, fonte-nao-indexada, causa}` já está
   inteiro em `aviso[]`. A união `linhas[].fonte ∪ aviso[].fonte` é sempre as N fontes consultadas,
   e é isso que o teste confere.
3. **Cobertura agregada em duas escadas.** Havendo item, manda a melhor cobertura entre as fontes
   que contribuíram item; não havendo, a mais informativa entre todas. Assim um envelope com item
   nunca sai rotulado `vazia` ou `ausente`, e a fonte caída declara o vão sem rebaixar quem respondeu.

Medido em 20/08/2026, tokenizador `qwen2.5.json`:

| envelope | tokens |
|---|---|
| sem itens, uma fonte, `vazia` | **14** |
| recusa de disjuntor, uma fonte | **36** |
| seis fontes, todas caídas | **113** |
| um item do board, com carimbo | 69 |
| um item do acervo, com sinal, digest e casamento | 127 |

O teto de **40 tokens** do envelope sem itens é o único número duro da spec, e é ele que impede o
envelope de virar imposto por giro. O de 113 é teto de regressão, não meta.

## Adaptadores

`adaptadores/base.py` fixa o contrato: o adaptador **levanta** `FonteIndisponivel` (quem precisa
saber é o disjuntor) e `busca_declarada()` a transforma em linha (o consumidor nunca vê exceção).
`busca_medida()` devolve o par (resultado, ms).

| adaptador | contrato usado | chave | versão | carimbo |
|---|---|---|---|---|
| `registro.py` | arquivos versionados de `decisions/`, três séries | `adr:` `seg:` `ont:` | blob sha do git, `digest` sem git | — |
| `fila.py` | `XRANGE` + `XINFO STREAM` (leitura fria) | `caixa:<slug>/<stream-id>` | o próprio stream-id | — |
| `mesa.py` | Postgres `sessao.mesa_item` + Valkey `mem:*` | `mem:<sufixo>:<slot>[#<id>]` | `seq` (item) · `digest` (prosa velha) | `i:<max(id)>/<contagem> p:<digest>` |
| `wiki.py` | `api.php`: `prop=revisions`, `action=cargoquery`, `list=search` | `wiki:<page_id>[#seção]` | `rev_id` | `rc:<rc_id>` |
| `acervo.py` | `POST /search` e `GET /facets` do rag | `acervo:<objeto>#<âncora>` | `digest` do índice | `acervo:<acervo_sha>` |
| `board.py` | `GET /api/itens?campos=`, `/api/itens/<id>`, `/api/itens/<id>/eventos`, `/api/carimbo` | `item:<id>` | `max(evento.id)` do item | `<max(evento.id)>/<contagem>` |

Nenhuma fonte serve `coberta` enquanto `tem_gold=False`: servem `nao-calibrada`. O rótulo `boa` do
rag também não vira `coberta`; `cobertura_do_rag()` mantém o rótulo dele legível ao lado.

Wiki e acervo não passam pelo wiki-mcp nem pelo `rag_search`: são consumidores da mesma API, e
encadear um no outro acoplaria a recuperação à superfície de ferramenta de outra cadeira.

**Wiki, três caminhos.** Alvo nominal `wiki:<Título>[#seção]` vai a `prop=revisions`; faceta
declarada (`filtros={"tabela": …}`) vai a `action=cargoquery`; termo livre vai a `list=search`. A
chave usa `page_id` porque título muda em renomeação e id não. A busca usa os namespaces
`0|4|12|3000|3004`: `Operar:` é o 3004, e o 3000 é `Frente:`.

**Acervo, a única que gradua.** É a única fonte semântica, e por isso a única com `sinal`: sem
`rerank`, `medida: "sim"` com piso `MIN_SIM`; com `rerank`, `medida: "rerank"` com piso `MIN_CE`.
`texto="secao"` parte a fita de `contexto` casando `[n]` com `fontes[n-1]`, e só quando a contagem
bate; bloco a menos cai para `ref`.

**Acervo, chave fail-closed.** `/search` devolve `section_id` em `curto-v1`, projeção de exibição que
nenhuma chave gravada pode carregar, e a API não expõe a forma completa por requisição. Sem ela, o
adaptador levanta `FonteIndisponivel` e a fonte sai `fonte-nao-indexada` com `sem-indice`.
`PF_ACERVO_CHAVE_CURTA=1` é o escape de bancada, desligado por default. A versão sai como
`acervo_sha` marcada `digest` até o retorno trazer `impressao.id` por fonte.

**Board, versão do item.** `max(evento.id)` vem de `/api/itens/<id>/eventos`. Item sem linha no
ledger serve `0@<carimbo>`. O adaptador nunca serve `conteudo`, para nenhum valor de `texto`: id,
título, fase, cadeira, nível e pai na linha, o resto por `ref`. A projeção `?campos=` é pedida
sempre (56.771 bytes contra 493.576). Filtros aceitos pela API: `cadeira`, `estado`, `nivel`,
`origem`; termo no título é recortado localmente.

Medido na bancada em 20/08/2026, estado real:

| chamada | mediana | itens | envelope |
|---|---|---|---|
| `registro` por chave exata | 4,5 ms | 1 | — |
| `fila`, caixa própria, `XRANGE` inteiro | 56,9 ms | 8 | — |
| `mesa`, duas metades | 45,5 ms | 1 | — |
| `board` por chave exata | 27,0 ms | 1 | 115 tok |
| `board` por eixo de linha, k=8 | 64,4 ms | 8 | 731 tok |
| wiki, alvo nominal | 12,8 ms | 1 | 97 tok |
| wiki, `cargoquery` por domínio | 16,5 ms | 5 | 339 tok |
| acervo, `texto=nenhum` | 73 ms | 3 | 330 tok |
| acervo, `texto=secao` | 92 ms | 3 | 2.601 tok |
| acervo, primeira chamada (`/facets` frio) | 925 ms | — | — |

Todas as fontes exatas ficam abaixo do timeout de 250 ms; o acervo fica a 4% dos 2 s da classe
semântica. O custo do acervo é token, não latência, e a procedência custa mais que a referência: o
teto de 40 do envelope vazio não protege o envelope em uso, que segue sem teto medido.

`test_contrato_adaptadores.py` roda contrato com cliente falso sempre, e conformidade contra a
fonte real quando ela responde (pulado com motivo quando não). A conformidade de `mesa` contra
`mesa ver` não está escrita.

## PEP por fonte

`pep.py` impõe; quem decide é `politica-acesso/pdp.py` (PDP), com as regras em
`politica-acesso/politica.yaml` (PAP) e os atributos em `politica-acesso/sujeitos.yaml` (PIP).

1. **Uma decisão por fonte**, com o par `(dominio, sobre)` que `fontes.py` declara.
2. **Negativa total**: pedido de dois recortes com concessão de um não vira busca em um.
3. **Fail-closed em falha de mecanismo**: política ilegível, sujeito fora da projeção ou atributo
   ausente nega, e a `regra` da negativa (`politica`, `projecao`, `identidade`) diz que foi mecanismo.
4. **A ação é o verbo humano da matéria** (`rag_buscar`, `wiki_ler`, `msg_ler`; `recuperar` nas
   três fontes sem verbo de leitura). O recuperador herda a concessão que existe; ampliar é merge no PAP.
5. **Alvo ausente vira `<prefixo>*`, nunca `*`**, para o pedido genérico bater na concessão nominal.

A identidade não mora aqui: o PEP recebe o sujeito já resolvido, e `auditor` é injetado pelo host.
A recusa mantém uma linha por fonte pedida, todas `fonte-nao-indexada` com `sem-concessao`; `falta`
nomeia o alvo e a regra, `proximo` diz o que pedir de novo. `sujeito` não entra no envelope.

Medido em 20/08/2026: uma decisão 0,017 ms; pedido de 6 fontes 0,102 ms; primeira chamada (carrega
PAP e PIP) 11,1 ms; recusa das seis fontes 157 tokens.

A matriz sujeito × fonte mora em `politica-acesso/test_matriz_sujeito_fonte.py`, junto do PAP,
porque quebra por merge no PAP. A expectativa é escrita à mão: gerá-la da mesma política que ela
confere não pegaria concessão nova.

## Cache

Chave `rec:<fonte>:<carimbo>:<sha256(alvo NFC/trim · filtros canonizados · k · texto)[:16]>`, no
`motor-cache` (`127.0.0.1:6381`, `allkeys-lru`, sem AOF). Uma linha por fonte: board volátil não
derruba cache de acervo estável. `sujeito` não entra na chave: o PEP roda por fonte antes do lookup,
e o cache guarda resposta da fonte, nunca decisão de acesso. `k` e `texto` entram no hash. A
invalidação é chave nova mais LRU, sem varredura.

| caso | tratamento |
|---|---|
| fonte caída | não grava |
| resposta vazia | grava; o carimbo a protege |
| carimbo indisponível | vai à fonte sem cache |
| valor de contrato velho ou corrompido | apaga e trata como miss |

Acervo fica fora do cache por default (`PF_CACHE_ACERVO=1` liga na bancada). Ligado, cada
`impressao.id` citada é conferida contra `rec:aposentadas` (`SISMEMBER`), e `SISMEMBER` que não
responde reprova o hit.

`rec:stat:<fonte>` é HASH com `hit`, `miss`, `bytes`, `idade` (soma em segundos), por `HINCRBY`.
Fonte nunca consultada devolve os quatro zerados. A medida nunca derruba a leitura.

Medido no Valkey em 20/08/2026: hit do board 6,0 ms contra 23,7 ms de leitura direta; hit do
registro 2,9 ms contra 3,4 ms. O hit ainda paga o carimbo, que está na chave.

## Gold das fontes exatas

```
python -m recuperacao.gold --fonte board fila mesa registro wiki --saida-dir avaliacao/
```

Um gerador só, parametrizado. Três classes de caso:

| classe | esperado vem de | `pontuavel` |
|---|---|---|
| `chave-exata` | do estado | `true` |
| `chave-inexistente` | do estado; a resposta certa é `vazia` | `true` |
| `termo` | do próprio mecanismo medido | `false` até revisão humana |

`tem_gold` segue `False`: o gerador produz candidato, e quem calibra a fonte é revisão humana.
`resposta_certa: ausente` não é gerável: é juízo sobre o corpus. A wiki precisa de `--semente`
(default `PlataFirma`), que enviesa a amostra, nunca o gabarito. Fonte sem estado levanta em vez de
emitir gold vazio.

Rodando os casos pontuáveis contra as fontes: `board` e `registro` acertam todos; `fila`, `mesa` e
`wiki` devolvem vazio quando recebem como alvo a chave que elas mesmas emitem. A assimetria é do
contrato de alvo, não do gabarito, e uniformizá-la é decisão do dono do envelope.
