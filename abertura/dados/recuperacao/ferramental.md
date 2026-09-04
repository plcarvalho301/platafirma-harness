# ferramental dados/recuperacao

## Em todo giro

| chamo | quando |
|---|---|
| motor rag buscar "<rótulos/frase inteiros>" | antes de afirmar que o acervo tem ou não tem algo — inclusive antes de ingerir, para não duplicar obra que já existe |
| acervo escada [--detalhe] | ao aceitar uma ingestão — a prova é servindo subir sem `!` novo na FUGA POR DEGRAU, não o "feito" do apply |

## Por matéria

**Representação para busca (preparo do corpus / ingestão)**

| chamo | quando |
|---|---|
| ingerir --lote <pasta> --motor rag --autor dados --colecao firma [--apply] | ao levar obra da entrada à vetorização; sem --apply é dry-run do plano (veredito criar/edicao) |
| ingerir ... --ocr | quando o lote tem scan sem camada de texto E não há cópia limpa da obra no acervo |
| ocrmypdf --force-ocr --deskew --rotate-pages -l <lang> ent.pdf sai.pdf | ao transformar scan porco em artefato de verdade (PDF pesquisável + camada de texto); é longjob |
| pdftotext -nopgbrk arq.pdf - | ao amostrar a qualidade da OCR no gate, e para extrair texto de PDF born-digital (sem OCR) |

## Ambiente

- host: ocrmypdf 17.10, tesseract 5.3.4 (eng/por/+150 langs), pandoc 3.1.3, poppler (pdftotext/pdfimages/pdftoppm), qpdf, gdown, rclone (remote gdrive:)
- ingestão de objeto exige a credencial da SESSÃO: rode `ingerir --apply` inline, não por longjob

## Armadilhas de ferramenta medidas aqui

- **OCR de obra já-existente** — parece que todo scan pede OCR; é que o acervo pode já ter cópia limpa (born-digital) da mesma obra, melhor que qualquer OCR. Sinal: `motor rag buscar "<título>"` devolve a obra sob outro arquivo. Varra ANTES de OCR-ar. (2026-09-04)
- **aviso "poor OCR" do tesseract** — parece texto ruim; é heurístico que dispara em corpo denso mesmo com saída limpa. Sinal: 255/256 páginas avisam, mas pdftotext mostra texto legível e não-ascii ~0%. Meça o texto, não conte avisos. (2026-09-04)
- **longjob leva 401 ao subir objeto** — parece falta de acesso; é o longjob (systemd) não herdando a credencial da sessão. Sinal: "erro ao subir objeto (401): unauthorized" no log, mas o mesmo apply inline conclui. Rode inline. (2026-09-04)
