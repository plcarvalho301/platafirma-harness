# Rollback da migracao do card #2286

Dois comandos. Funciona porque o passo 6 COPIA o volume: os originais do `claudinho`
continuam la, intactos, e a imagem tambem.

```
# como jaiminho:
sudo -u jaiminho XDG_RUNTIME_DIR=/run/user/1003 bash -lc \
  'cd /srv/pf/agy/jaiminho && docker compose down; cd /srv/pf/agy/jaiminho-fabrica && docker compose down'

# como claudinho:
sudo -u claudinho bash -lc \
  'cd ~/AI/platafirma-harness/jaiminho && docker compose up -d jaiminho; \
   cd ~/AI/platafirma-harness/jaiminho-fabrica && docker compose up -d'
```

O `jaiminho-server` nunca para em passo nenhum, entao nao entra no rollback.

So apagar `/srv/pf/mig` e os volumes antigos do `claudinho` depois de uma semana
estavel — antes disso, eles SAO o rollback.
