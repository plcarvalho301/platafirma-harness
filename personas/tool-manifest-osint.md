|---|---|
| `exiftool` 12.76 | metadado de imagem, PDF, DOCX. Procedência começa aqui. `-a -G1 -s` mostra tudo com grupo |
| `jq` 1.7 | fatiar JSON no shell antes de decidir se vale Python |
| `sqlite3` 3.45.1 | abrir `.db`/`.sqlite`. `.tables` e `.schema` antes de consultar |
| `pandoc` 3.1.3 | conversão entre formatos de documento (md, docx, html, epub, latex) |
| `7z`, `unzip` | arquivo comprimido. `7z l` / `unzip -l` lista sem extrair — sempre listar antes |
| `soffice` 24.2.7.2 | converter formato de escritório em lote: `soffice --headless --convert-to pdf` |
| `ffmpeg` 6.1.1 | áudio/vídeo: extrair trilha, amostrar frames, ler metadado de contêiner |
| `file` | tipo real por conteúdo. **Rodar antes de confiar em extensão** — ver seção F |
 
### OCR
`tesseract` 5.3.4 — **161 idiomas instalados**.
 
```bash
pdftoppm -r 300 -png entrada.pdf /tmp/pag && tesseract /tmp/pag-1.png stdout -l deu
```
 
- `-l osd` ou `--psm 0` detecta orientação e script antes de escolher idioma.
- Vários idiomas na mesma página: `-l deu+eng+lat`.
- **Alemão gótico é `-l frk`** (ou `Fraktur`), nunca `deu`. `deu` erra fraktur inteiro.
- `--psm 6` para bloco único de texto, `--psm 11` para texto esparso em imagem.
- `tesseract --list-langs` lista os 161.
Cobertura confirmada dos que interessam: `por deu frk spa fra ita nld eng rus ara
fas heb chi_sim chi_tra jpn kor ell hin tha tur vie pol srp lat grc osd`.
 
---
 
## B. Camada apt já instalada
 
`tesseract-ocr` + `tesseract-ocr-all` · `libimage-exiftool-perl` · `jq` · `qpdf`
· `sqlite3` · `pandoc` · `ffmpeg` · `build-essential` · `python3-dev`
 
`libmagic` vem de **`libmagic1t64`** 1:5.45 + `libmagic-mgc` (confirmado por
`dpkg -l`). O pacote `libmagic1` não existe mais no Ubuntu 24.04 — **não pedir**.
 
Opcionais do `ocrmypdf` ainda ausentes, melhoram qualidade e tamanho, não função:
`pngquant`, `unpaper`, `jbig2enc`.
 
---
 
## C. Python no venv — `[func]`, todos importados e testados
 
### Coleta HTTP
`requests` 2.34.2 · `httpx` 0.28.1 (async, HTTP/2)
 
### HTML e XML
`beautifulsoup4` 4.15.0 · `lxml` 6.1.1 — `BeautifulSoup(html, "lxml")` usa os dois
 
### PDF em Python
| | quando |
|---|---|
| `pymupdf` 1.28.0 (`import fitz`) | o mais rápido e completo: texto com coordenadas, imagens, anotações, render. Primeira escolha |
| `pdfplumber` 0.11.10 | **tabela**. `page.extract_tables()` é o que pymupdf não faz bem |
| `pypdf` 6.14.2 | manipular estrutura: fundir, partir, ler `/Info`, decriptar |
| `ocrmypdf` 17.8.1 | PDF escaneado → pesquisável **preservando a imagem original**. `ocrmypdf -l por+deu --rotate-pages --deskew in.pdf out.pdf`. `--redo-ocr` refaz camada ruim, `--skip-text` pula página que já tem texto. Testado ponta a ponta |
 
### Tipo, encoding, tabular
| | uso |
|---|---|
| `python-magic` (`import magic`) | tipo real por conteúdo, ignorando extensão. `magic.from_file(p)` — testado, responde |
| `charset-normalizer` 3.4.9 | detecção de encoding. Melhor que chardet em texto curto e não latino |
| `chardet` 7.4.3 | segunda opinião de encoding |
| `pandas` 3.0.5 | CSV/Excel/tabular. Sempre `dtype=str` na primeira leitura, para não perder zero à esquerda |
| `openpyxl` 3.1.5 | `.xlsx` célula a célula, fórmula e formatação |
 
### Idioma e alfabeto — o bloco do §6 da skill
| | uso |
|---|---|
| `ftfy` 6.3.1 | conserta mojibake (`Ã§` → `ç`). Primeira coisa a rodar em texto suspeito |
| `unidecode` | transliteração para ASCII. **Derivado, nunca sobrescreve o bruto**; esquema vai no manifesto |
| `langdetect` | detectar idioma antes de citar. Evita a obra em alemão citada sem aviso |
| `regex` 2026.7.19 | o `re` da stdlib não faz classe Unicode (`\p{Han}`, `\p{Cyrillic}`). Este faz |
 
Normalização Unicode é `unicodedata.normalize("NFC", s)` da stdlib — NFC/NFKC no
derivado, nunca no bruto, e declarado.
 
### Correlação e organização documental
| | uso |
|---|---|
| `rdflib` 7.6.0 | grafo RDF, SPARQL, SKOS. Vocabulário e esquema de classificação |
| `networkx` 3.6.1 | grafo genérico: componentes, caminhos, centralidade. Correlacionar entidades |
| `rapidfuzz` 3.14.5 | casamento difuso de nome e título. `process.extract` deduplica acervo |
| `jsonschema` 4.26.0 | validar dado semi-estruturado contra esquema declarado |
| `pyyaml` 6.0.3 | YAML, front-matter |
 
### Navegador
`playwright` + `chromium` e `chromium_headless_shell` **já baixados** no cache.
Só para alvo que não rende sem JS — `curl` primeiro, sempre. Identificável como
nosso: sem UA falso, sem persona.
 
---
 
## D. Pendências — `[inst]`, instalado sem prova
 
**OCR de escrita RTL (`ara`, `fas`, `heb`) não foi verificado.** O teste
sintético não serviu: a fonte usada corrompeu o texto antes do OCR acontecer
(confirmado extraindo o PDF-fonte de volta — o árabe já estava quebrado ali). O
pacote está instalado e há `Noto Naskh Arabic` entre as 544 fontes do sistema.
Prova só com documento RTL real. Até lá, não afirmar que funciona.
 
---
 
## E. O que o `modulo-osint` não tem, por desenho
 
Sem sudo · sem docker · sem alcance a `/home/claudinho` ou `/home/megafone` ·
loopback fechado por iptables (`127.0.0.1` não responde, exceto DNS e o próprio
MCP — serviço local da plataforma não é fonte e não está ao alcance).
 
Não é permissão faltando. Não tentar contornar.
 
---
 
## F. Corpus de referência — `/mnt/project/`, outro ambiente
 
Máquina diferente do `modulo-osint`: aqui há `pypdf` e poppler, **não** há
pymupdf, não há o venv, não há os pacotes da camada C.
 
### Os `.pdf` do Project não são PDFs
 
A ingestão converteu tudo. `pdftotext` e `pypdf` falham em **todos** com
`invalid pdf header`. Formato real, verificado com `file`:
 
- **7 arquivos → ZIP** com `N.jpeg` + `N.txt` por página:
  ```bash
  unzip -l /mnt/project/paper9.pdf        # inventário de páginas
  unzip -p /mnt/project/paper9.pdf 4.txt  # texto da página 4
  ```
- **Texto UTF-8 puro** (ler com `grep`/`sed`/`head` direto): `EARQV203MAI2022.pdf`,
  `Miriely_..._2019.pdf` e os quatro `.epub`.
### Consultar por problema
 
| problema | obra | arquivo | pág. |
|---|---|---|---|
| extrair metadado e referência de artigo científico | CERMINE (Tkaczyk, IJDAR 2015) | `CERMINE_automatic_...` | 19 |
| idem, pipeline de produção | GROBID (Lopez) | `GROBID_Combining_...` | 2 |
| parsing de string bibliográfica (CRF) | ParsCit (Councill, Giles, Kan) | `166_paper.pdf` | 7 |
| layout de documento, PDF que texto puro não resolve | PubLayNet (Zhong, IBM) | `1908_07836v1.pdf` | 8 |
| texto + layout aprendidos juntos | LayoutLM (Xu et al.) | `1912_13318v5.pdf` | 9 |
| ontologia formal, classe, relação, upper ontology | Building Ontologies with BFO (Arp, Smith, Spear, MIT 2015) | `Building_Ontologies_...epub` | — |
| taxonomia mal formada, erro de modelagem conceitual | Ontological Anti-Patterns (Sales & Guizzardi) | `paper9.pdf` | 13 |
| requisito de gestão arquivística, fundo, série, retenção | **e-ARQ Brasil** (norma BR) | `EARQV203MAI2022.pdf` | 225 |
| vocabulário controlado, LAI, governo eletrônico | Dissertação Miriely S. Souza, 2019 | `Miriely_..._2019.pdf` | — |
| estrutura interna de PDF, objeto, encoding, fonte | Developing with PDF (Rosenthol, O'Reilly) | `Developing_with_PDF_...epub` | — |
| regex não trivial, backtracking, Unicode em padrão | Mastering Regular Expressions (Friedl, 2ª ed.) | `Mastering_rchive.pdf` | 36 |
| coleta web, sessão, robots, prática de scraping | Practical Web Scraping for Data Science (Broucke & Baesens) | `Practical_Web_Scraping_...epub` | — |
| automação de tarefa em Python, manipulação de arquivo | Automate the Boring Stuff (Sweigart) | `Automate_the_Boring_...epub` | — |
 
Consulta é dirigida: escolher a linha, abrir **a página**, não varrer o corpus.
Uma página de `.txt` custa ~400 tokens; o corpus inteiro custa a sessão.
 
### Fronteira
 
Corpus é insumo de leitura. **Nada do Project entra em `saida/`**, e a entrega
sai pelo `modulo-osint` — travessia entre os dois ambientes é feita por mim
relendo e reescrevendo, nunca por cópia de arquivo.
 
---
 
## G. Repositórios de referência — verificados por HTTP em 2026-08-02
 
Quatro se moveram desde o endereço antigo; o destino está anotado.
 
### Extração de documento — as implementações dos papers da seção F
| repo | por quê |
|---|---|
| `grobidOrg/grobid` *(era `kermitt2/`)* | o GROBID do paper, mantido. Serviço que devolve TEI-XML |
| `docling-project/docling` *(era `DS4SD/`)* | IBM. Primeira escolha hoje: PDF/DOCX/PPTX → markdown com layout e tabela |
| `opendatalab/MinerU` | concorrente do docling, forte em fórmula e CJK |
| `datalab-to/marker` *(era `VikParuchuri/`)* | PDF → markdown, rápido |
| `datalab-to/surya` *(era `VikParuchuri/`)* | OCR + detecção de layout multilíngue; motor do marker |
| `microsoft/unilm` | onde LayoutLM v1/v2/v3 mora de fato |
| `CeON/CERMINE` · `knmnyn/ParsCit` | os do paper, históricos; valem como arquitetura |
| `allenai/science-parse` | alternativa da AI2, mais simples que GROBID |
| `ibm-aur-nlp/PubLayNet` | o dataset |
 
### Organização documental
| repo | por quê |
|---|---|
| `BFO-ontology/BFO` | a ontologia do livro do Arp/Smith/Spear, canônica |
| `protegeproject/protege` | editor de ontologia de referência |
| `NatLibFi/Skosmos` | publicar vocabulário SKOS navegável |
| `artefactual/archivematica` | preservação digital, implementa OAIS |
| `artefactual/atom` | descrição arquivística ISAD(G)/ISAAR — par do e-ARQ |
| `archivesspace/archivesspace` | gestão de fundo e série |
 
### Coleta e preservação
`webrecorder/browsertrix-crawler` (captura WACZ com browser real, padrão atual de
arquivamento web) · `internetarchive/heritrix3` · `ArchiveBox/ArchiveBox` ·
`Y2Z/monolith` (página inteira em um HTML — ótimo para `bruto/`) · `scrapy/scrapy`
· `mikf/gallery-dl` · `yt-dlp/yt-dlp`
 
### Linha secundária — só com recorte escrito do Pedro
`owasp-amass/amass` · `projectdiscovery/subfinder` · `trufflesecurity/trufflehog`
· `laramies/theHarvester` · `smicallef/spiderfoot`
 
Enumeração de superfície e credencial vazada. Existem e funcionam, mas derrapam
para pessoa natural com facilidade (theHarvester coleta e-mail e nome; SpiderFoot
correlaciona pessoa por padrão). Não instalar por conveniência — §8 da skill vale.
 
---
 
## H. Instalar esta stack de OCR em outro ambiente
 
Prompt pronto para colar em sessão de outra persona:
 
```
Instale e verifique a stack de OCR neste ambiente.
 
APT (precisa de sudo — se você não tiver, devolva o comando para quem tem):
  sudo apt-get update && sudo apt-get install -y \
    tesseract-ocr tesseract-ocr-all \
    ghostscript poppler-utils \
    pngquant unpaper \
    libmagic1t64 build-essential python3-dev
 
  Notas:
  - tesseract-ocr-all traz ~161 idiomas (~1 GB). Para instalação enxuta, troque por
    tesseract-ocr-{osd,eng,por,deu,spa,fra,ita,rus,ara,heb,fas,chi-sim,chi-tra,jpn,kor,ell}.
  - No Ubuntu 24.04 o pacote é libmagic1t64, NÃO libmagic1 (renomeado na transição time_t).
  - Se um nome de pacote não existir, o apt aborta a invocação inteira e nada é
    instalado. Ao primeiro erro, instale em blocos menores.
 
PIP (em venv, nunca no Python do sistema):
  pip install ocrmypdf pymupdf pdfplumber pypdf pytesseract ftfy charset-normalizer regex
 
VERIFICAÇÃO — não relate sucesso por instalação bem-sucedida; prove executando:
  1. tesseract --version && tesseract --list-langs | wc -l
  2. Gere um PDF-imagem sem camada de texto; confirme com `pdffonts x.pdf`
     (tabela vazia) e `pdftotext x.pdf -` (saída vazia).
  3. Rode `ocrmypdf -l por x.pdf y.pdf` e confirme que `pdftotext y.pdf -`
     agora devolve o texto correto.
  Relate o que passou e o que não passou. Não afirme que um idioma funciona sem ter
  OCRado uma amostra real naquele idioma.
 
ARMADILHAS já pagas em tempo:
  - Alemão gótico é `-l frk` (ou `Fraktur`), nunca `-l deu`. `deu` erra fraktur inteiro.
  - `-l osd` ou `--psm 0` detecta orientação/script antes de escolher o idioma.
  - Múltiplos idiomas na mesma página: `-l deu+eng+lat`.
  - 300 dpi em `pdftoppm -r 300 -png` é o piso; abaixo disso o OCR degrada.
  - Teste sintético mente em escrita RTL (árabe, persa, hebraico): a fonte usada para
    gerar a amostra costuma corromper o texto ANTES do OCR. Se falhar, extraia o texto
    do PDF-fonte de volta para separar falha de amostra de falha de OCR.
```
