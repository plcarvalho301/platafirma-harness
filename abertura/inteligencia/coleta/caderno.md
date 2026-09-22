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

## armadilhas da matéria (subiram do chapéu na descida ao molde novo, 22/09/2026, #3086)

- Coleta sem plano — parece diligência; é ruído. Sinal: não há aspecto essencial que a ação responda.
- Busca disfarçada de coleta — obter o que o detentor negou não é coleta. Sinal: exigiu técnica operacional ou acesso não consentido.
- Canal tomado por fonte — quem entregou não é quem viu. Sinal: confiança atribuída ao emissor sem medir a distância até a origem.
- Insumo sem metadado — irrastreável. Sinal: sem autor, data, origem ou equipamento; a avaliação não tem o que pesar.
- Volume tomado por cobertura — muito Osint da mesma origem. Sinal: a contagem de fontes sobe, a diversidade de origem não.