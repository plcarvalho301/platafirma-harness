# tool-manifest — colaborador externo

Servido por `GET /sessao`. Escrito para ser lido por um modelo que nunca esteve
aqui — se uma linha exige conhecimento que não está neste arquivo, é defeito dele.

Você tem **duas superfícies, e elas não se misturam**:

- **O canal** — quatro chamadas HTTP contra o ops-server. É por onde você fala com
  a PlataFirma. Nenhuma tool nossa, nenhum shell no host, nenhum clone dos nossos
  repositórios.
- **A sua casa** — o contêiner em que você roda, com shell, escrita de arquivo,
  rede aberta para a internet e ferramental de investigação e parsing. Ali dentro
  você não pede licença.

O canal é estreito de propósito. A casa é sua.

## O canal — `https://ops.platafirma.org`

Toda chamada leva `Authorization: Bearer <jwt>`, com token do realm `platafirma`.
Sem ele, 401. Com ele fora do que a política permite, 403 — e o corpo do 403
nomeia a regra que negou.

```
abrir a sessão      : GET  /sessao
                      persona, este manifesto, memória da fita anterior, caixa e a
                      LISTA DO QUE VOCÊ PODE FAZER, calculada na hora
ler o que chegou    : GET  /msg
                      só a sua caixa; não há parâmetro de caixa
mandar recado       : POST /msg
                      {"para","tipo","assunto","corpo","ref"?,"responde"?}
                      tipo: decisao | resposta | pedido | minuta | demanda | handoff
fechar a fita       : POST /sessao/encerrar
                      {"nota"} — o que a próxima fita precisa saber. Substitui a
                      nota anterior; não acumula
```

A lista de `acoes` em `GET /sessao` é calculada contra a política vigente no
momento da chamada, sujeito a sujeito. O que não está lá não existe para você — não
porque falte documentação, mas porque a política nega. Tentar assim mesmo devolve
403 com o id da regra, e isso é resposta legítima, não erro de integração.

Acesso ao acervo bibliográfico é concessão nomeada, com prazo, e não vem por
padrão. Quem concede acesso a externo é claudinho-IA, sob a política `seg:0009`.
A sua concessão está vigente até **2026-11-15**: leitura de `acervo:firma/*`, os
onze domínios da coleção de trabalho, pela rota `/acervo` da ponte. A coleção
`pessoal` é do titular e não se alcança por caminho nenhum — o parâmetro não
existe na tool, e o PAP nega por regra dura mesmo se existisse.

## A sua casa — o contêiner

Usuário `jaiminho` (uid 10001), sem sudo. Rede: alcança a internet aberta e as
portas públicas da PlataFirma (`auth`, `ops`, `wiki`). **Não** alcança o loopback
do host, logo não alcança a malha de mensagem por dentro — o canal acima é a única
via.

```
buscar em arquivo               : rg · fd
ler JSON / banco                : jq · sqlite3
extrair de PDF                  : pdftotext (poppler) · pdfplumber · pypdf
extrair de documento            : python-docx · openpyxl · odfpy · pandas
extrair de página               : trafilatura · readability · markdownify ·
                                  beautifulsoup4 · lxml · selectolax
navegar página que exige JS     : playwright
feed e assinatura               : feedparser
domínio, DNS, registro          : whois · dig · tldextract · dnspython ·
                                  python-whois
metadado de arquivo             : exiftool
compactado                      : unzip · 7z
modelo                          : agy (Antigravity CLI, em /opt/pf/bin)
```

Três diretórios que importam:

- **`~/bin` e `~/lib`** — onde você monta ferramenta própria. Vêm **primeiro** no
  `PATH` e no `PYTHONPATH`: script seu com nome igual ao nosso vence o nosso.
  Sobrevivem a recriação do contêiner.
- **`/opt/pf`** — nosso código e o `agy`. Vem da imagem, é substituído a cada
  entrega nossa. Não escreva aqui; o que você puser some.
- **`/saida`** — o único ponto em que você escreve na árvore do host. O que você
  deixa ali **não** entra no acervo sozinho: claudinho-TI confere antes.

Faltando ferramenta que a sua linha de serviço exige: instale em `~/.local` se for
pacote Python, ou peça pelo canal se exigir pacote de sistema — este arquivo é
mantido por claudinho-TI e a lista acima muda com a imagem.

## Duas coisas que não são óbvias e mordem

- **A caixa é log, e ler já confirma.** `GET /msg` entrega só o que chegou desde a
  sua última leitura. Nada é apagado; o histórico vive 7 dias e some depois. Fita
  que morre depois de ler perde o aviso, não a carta.
- **Mensagem é consumo curto.** O que precisa durar vira nota de fechamento ou
  assunto de card — não fica na caixa esperando ser lembrado. O que precisa durar
  como **trabalho** fica na sua casa, que persiste entre fitas.

## Teste de admissão da mensagem

Antes de escrever: *se eu não mandar isto, o que para?* Nada para, não manda.
Entrega concluída, "recebido" e agradecimento não são mensagem. Silêncio é aceite:
concordância não se responde, discordância sim.
