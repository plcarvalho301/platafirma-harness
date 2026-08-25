# Catálogo de fontes da PlataFirma

As fontes que o Recuperador roteia, e só elas. Fonte nova entra aqui e aparece no
roteamento; fonte que sai, some. Uma cópia só — `arq:0064` §10.5.

Espelho de leitura humana: `Operar:catalogo-de-fontes` na wiki.

## Fontes da plataforma

Objeto próprio no índice do Recuperador, por `arq:0067` §5: é **desta** tabela que a
descrição de roteamento deriva no build (`arq:0064` §5.3).

| fonte | capacidade | dono | transporte | classe | contrato de leitura | gold |
|---|---|---|---|---|---|---|
| board | trabalho | TI | HTTP | exata | HTTP do rastreador + header de identidade | nao-calibrada |
| fila | mensagem | TI | stream | exata | XINFO STREAM · XRANGE no motor-msg | nao-calibrada |
| mesa | memoria | dados | postgres | exata | mapa por chave (arq:0062) | nao-calibrada |
| registro | decisao | gestao-estrategica | git | exata | decisions/INDICE.md, mantido na escrita | nao-calibrada |
| wiki | conhecimento | dados | HTTP | exata | API do MediaWiki | nao-calibrada |
| acervo | conhecimento | dados | HTTP | semantica | API do rag | nao-calibrada |

Conferidor do servido contra esta tabela: `conferir superficie` (`arq:0067` §6), de claudinho-TI.
