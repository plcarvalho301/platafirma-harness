# jaiminho-fabrica — o compose saiu daqui em 20/08/2026

O braco `jaiminho-fabrica` migrou para o daemon rootless da conta `jaiminho`
(uid 1003) no card **#2286**, por ato de root do dono.

- **Deploy vivo:** `/srv/pf/agy/jaiminho-fabrica` (dono `jaiminho`, 0750).
- **Fonte versionada:** `platafirma-harness/migracao-2286/jaiminho-fabrica/`.
- **Rollback:** `platafirma-harness/migracao-2286/ROLLBACK.md`.

O `docker-compose.yml` que morava aqui foi **removido**, nao movido nem comentado.
Enquanto ele existisse, um `docker compose up -d` nesta pasta subiria um SEGUNDO
braco no daemon do `claudinho`, contra os volumes velhos — dois bracos vivos com a
mesma credencial e estados divergentes. Pedido de claudinho-seguranca no handoff
`20260820T195257`, item 2.

**Esta conta nao se opera de `claudinho`:** outro daemon, outro netns, outro uid, e
`claudinho` nao tem sudo. `docker ps|logs|exec|restart` daqui nao enxerga o braco.
