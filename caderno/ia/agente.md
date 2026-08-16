# caderno — agente e integração multiagente

## Citar argumento para `bash -lc`: `shlex.quote`, nunca `json.dumps`
`json.dumps` cita para JSON (aspas duplas). Passado a `subprocess.run([...,"bash","-lc",cmd])`,
o bash ainda interpreta o conteúdo entre aspas duplas: crase executa, `$`/`$(...)` expande,
`\n` chega como dois caracteres literais em vez de quebra de linha. Efeito: crase come trecho
da mensagem e dispara `command not found` no worker; texto com `$VAR` perde o literal.
`shlex.quote` cita para shell POSIX (aspas simples com escape) — é o certo sempre que o
destino for `bash -lc`/`sh -c`, não só no verbo `jaiminho`. Caso resolvido: bin/jaiminho
linhas 110 e 160 (commit f10a9f8, platafirma-harness).
