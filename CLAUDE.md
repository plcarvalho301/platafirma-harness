# Sessão da PlataFirma a partir deste clone

Esta pasta é **cliente**. Nada da plataforma roda aqui: todo trabalho executa na
máquina do dono, por tool call contra `claudinho-mcp` e `platafirma-wiki`. O clone
existe para carregar configuração — não para ser explorado.

## Arranque

**Fonte única: `platafirma-harness/conduta/arranque.md`.** Leia lá as duas linhas
que abrem qualquer sessão e a tabela de injeção por superfície.

Aqui não se copia o texto de arranque, e isto não é preferência de estilo: este
arquivo é rastreado em git, cada worktree o congela no branch em que nasceu, e
divergência entre 27 cópias do mesmo parágrafo não é visível de lugar nenhum. Foi
o que aconteceu até 16/08/2026. `conferir arranque` mede, e o `pre-commit`
reprova cópia nova.

**Worktree não injeta cadeira.** Ela isola branch, que é o que `git worktree` faz
bem; identidade lida de dentro dela é a cópia congelada que a peça elimina.

## O que esta estação não faz

`Bash`, `Write`, `Edit` e `NotebookEdit` estão negados em `.claude/settings.json`, e
`deny` vence `allow` em qualquer modo. Escrita e execução acontecem **só** por
`claudinho-mcp`, na máquina do dono, com auditoria em `~/AI/var/log/ops/`.

Ler o clone segue liberado. Editar o clone, não: mudança em persona, manifesto ou
skill se faz na máquina do dono, pelo caminho da cadeira dona daquele artefato.
