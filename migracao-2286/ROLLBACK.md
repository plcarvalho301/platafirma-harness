# Rollback da migracao do card #2286

## Perna `jaiminho` (OSINT): ENCERRADA, sem rollback — 02/09/2026, seguranca

O braco OSINT foi expurgado por ordem do dono em 02/09/2026: sujeito fora do PDP,
papel `pesquisador-externo` fora do PAP, client `L0R8OJ` e service account
desabilitados no realm. Nao ha para onde rolar de volta — a credencial que este
rollback reergueria nao autentica mais. Removidos nesta data: `jaiminho/` deste
diretorio (compose), `img-jaiminho.tar`, `jaiminho_casa.tar`,
`jaiminho_credenciais.tar` em `/srv/pf/mig` (~500 MB), e os volumes
`jaiminho_casa`/`jaiminho_credenciais`/`jaiminho_trabalho` do daemon do `claudinho`.

O deploy vivo em `/srv/pf/agy/jaiminho` (uid 1003) NAO foi tocado por esta cadeira —
permissao negada por segregacao de conta (seg:0011), sem sudo (`Permission denied`,
medido em 02/09/2026). Teardown do container/diretorio la e alcance de
claudinho-TI.

## Perna `jaiminho-fabrica`: continua viva, rollback abaixo continua valendo

Um comando (era dois; o de `jaiminho` saiu com a perna acima). Funciona porque o
passo 6 da migracao original COPIA o volume: os originais do `claudinho` continuam
la, intactos, e a imagem tambem.

```
# como jaiminho:
sudo -u jaiminho XDG_RUNTIME_DIR=/run/user/1003 bash -lc \
  'cd /srv/pf/agy/jaiminho-fabrica && docker compose down'

# como claudinho:
sudo -u claudinho bash -lc \
  'cd ~/AI/platafirma-harness/jaiminho-fabrica && docker compose up -d'
```

O `jaiminho-server` nunca para em passo nenhum, entao nao entra no rollback.
