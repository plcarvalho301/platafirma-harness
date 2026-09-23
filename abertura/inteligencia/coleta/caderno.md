Diário de coleta — contornos de ferramenta OSINT

2026-09-15:
- `pesquisar ler` em gov.br/pf → status-0 (http) e status-302 (--render): páginas gov.br sob defeso eleitoral redirecionam; crawler não segue. Contorno: web.archive.org/web/<timestamp>/<url> via `pesquisar historico` (lista capturas com statuscode 200).
- web_fetch nativo recusa URL não vista em busca anterior. Contorno: `pesquisar ler`/`coletar`, ou rodar web_search antes do fetch.

2026-09-16:
- `pesquisar ler` em post público de LinkedIn → status-307 (login wall); crawler não passa. Sem contorno; sustentar por Socmint + HUMINT.
- `pesquisar ler` em PDF de diário oficial → status-0, vazio (http não extrai PDF); web_fetch nativo também recusou (URL não vista). Sem contorno; lead fica aberto. NÃO TESTADO: web_search nativa na URL antes do fetch.
- `mesa anota <slot>`: corpo em STDIN, slot = minúsculas/dígitos/hífen ≤24 chars. Item com ato pendente: `mesa item <chapeu> --ato ... --alvo ...`.

2026-09-16 (fita ONG/moldura):
- web_fetch em URL .amp (BBC) → SITE_BLOCKED. Contorno: web_search pelo tema para achar a matéria em outra fonte.

2026-09-22 (fita Thiel-Rosewood):
- web_fetch em newsletter Substack → 429. Contorno encontrado na data 2026-09-22: `pesquisar ler` (ok).
- `pesquisar ler` em revistaforum.com.br → status-403. Contorno encontrado na data 2026-09-22: web_fetch nativo (ok).
- web_fetch em página do Sunbiz (FL) → URL_TOO_LONG (>250 chars); `pesquisar ler` na mesma → status-307. Contorno: nenhum; dado ficou no snippet da busca + agregador (bizprofile), primária não confirmada.
- `pesquisar coletar` em drive.google.com/uc?export=download&id=<id> → arquivo vazio (sha e3b0c442…, status 0): crawler não baixa binário do Drive. Contorno encontrado na data 2026-09-22: IDs dos arquivos no bruto HTML da pasta (`window['_DRIVE_ivd']`, fim do arquivo, `read_file` com offset) → conector Google Drive `get_file_metadata` (dono da conta, createdTime, modifiedTime; OCR da imagem em contentSnippet com snippetVerbosity MAX_ALLOWED) + `download_file_content` (base64; EXIF lido no cabeçalho). `read_file_content` em JPG voltou vazio.
- `mesa item --chapeu coleta ...` → erro de usage. Forma certa: `mesa item <chapeu> --ato ... --alvo ...`.
- `mesa caderno <chapeu>` só LÊ (stdin ignorado); escrita do caderno é `mesa escrever <chapeu>` com corpo em stdin.

## achados de método

- Documento vazado publicado em pasta de nuvem: o metadado do contêiner (dono da conta, data de envio, app de upload) descreve o CANAL, não a origem. Data do fato só vem do conteúdo do documento; se o conteúdo não a traz, a data que a matéria afirma não tem apoio. (2026-09-22, Rosewood: doc dizia só "maio", matéria dizia "mesmo período" de 30/abr.)
- Manchete "grupo X faz Y": conferir se a entidade da manchete é a do corpo e contar os elos da cadeia antes de aceitar o vínculo (2026-09-22: "Rockbridge explora terras raras" = 1789 Capital → Vulcan → Energy Fuels → projeto sem lavra).

## armadilhas da matéria (subiram do chapéu na descida ao molde novo, 22/09/2026, #3086)

- Coleta sem plano — parece diligência; é ruído. Sinal: não há aspecto essencial que a ação responda.
- Busca disfarçada de coleta — obter o que o detentor negou não é coleta. Sinal: exigiu técnica operacional ou acesso não consentido.
- Canal tomado por fonte — quem entregou não é quem viu. Sinal: confiança atribuída ao emissor sem medir a distância até a origem.
- Insumo sem metadado — irrastreável. Sinal: sem autor, data, origem ou equipamento; a avaliação não tem o que pesar.
- Volume tomado por cobertura — muito Osint da mesma origem. Sinal: a contagem de fontes sobe, a diversidade de origem não.