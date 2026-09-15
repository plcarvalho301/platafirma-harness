#!/usr/bin/env bash
# capacidade: seguranca-perimetro
# dono: claudinho-seguranca
#
# Migra o braco do provider `agy` da conta `claudinho` (uid 1001) para a conta
# `jaiminho` (uid 1003). Card #2286, seg:0013 §2 e §6.
#
# POR QUE ESTE ARQUIVO EXISTE: os passos exigem root, e nenhuma cadeira tem root.
# O dono roda; a cadeira escreve, mede e confere.
#
# ESCOPO DESTA VERSAO: o conteiner `jaiminho` (OSINT) e mais nada. `jaiminho-fabrica`
# e `jaiminho-server` ficam onde estao nesta rodada — a fabrica perde o alias de rede
# do servidor no momento em que muda de daemon, e isso e decisao de endereco, de
# claudinho-TI, ainda nao tomada. Migrar um so mantem o rollback em dois comandos.
#
# NADA E APAGADO. O passo de volume COPIA. Os volumes originais seguem no daemon do
# `claudinho` e sao a rota de volta enquanto existirem.
#
# USO:  sudo bash migrar-agy-para-jaiminho.sh preparar
#       sudo bash migrar-agy-para-jaiminho.sh docker
#       bash      migrar-agy-para-jaiminho.sh volume     # como claudinho, sem sudo
#       sudo bash migrar-agy-para-jaiminho.sh subir
#       sudo bash migrar-agy-para-jaiminho.sh conferir
#       sudo bash migrar-agy-para-jaiminho.sh rollback
#
# REGISTRO HISTORICO (migracao concluida em 20/08/2026). Naquele estado o compose de
# origem e a entrada do braco moravam na pasta de trabalho da conta `claudinho`; este
# arquivo nao nomeia mais essa pasta. Reexecutar exige declarar as duas origens:
#   MIGRAR_COMPOSE_ORIGEM  diretorio com docker-compose.yml e .env do braco (preparar, rollback)
#   MIGRAR_ENTRADA_ORIGEM  diretorio da entrada antiga do braco (preparar)
# sudo nao repassa o ambiente: declare na propria linha, por exemplo
#   sudo MIGRAR_COMPOSE_ORIGEM=<dir> MIGRAR_ENTRADA_ORIGEM=<dir> bash migrar-agy-para-jaiminho.sh preparar
set -euo pipefail

MIG=/srv/pf/mig
AGY=/srv/pf/agy
ENTRADA=/srv/pf/entrada-jaiminho

origem() {  # imprime a origem declarada ou falha alto; nunca adivinha caminho
  local nome="$1" valor="${!1:-}"
  [ -n "$valor" ] || { echo "falta $nome: declare a origem (ver cabecalho)" >&2; exit 3; }
  printf '%s' "$valor"
}

como_jaiminho() {
  runuser -u jaiminho -- env XDG_RUNTIME_DIR=/run/user/1003 \
    DOCKER_HOST=unix:///run/user/1003/docker.sock bash -lc "$*"
}

case "${1:-}" in

preparar)   # root. Cria a arvore da conta 1003 FORA de /home/claudinho, que e 750.
  COMPOSE_ORIGEM="$(origem MIGRAR_COMPOSE_ORIGEM)"
  ENTRADA_ORIGEM="$(origem MIGRAR_ENTRADA_ORIGEM)"
  install -d -o jaiminho  -g claudinho -m 2770 "$ENTRADA"
  install -d -o jaiminho  -g jaiminho  -m 0755 "$AGY"
  install -d -o claudinho -g claudinho -m 0755 "$MIG"
  rsync -a "$ENTRADA_ORIGEM/" "$ENTRADA/"
  cp "$COMPOSE_ORIGEM/docker-compose.yml" "$COMPOSE_ORIGEM/.env" "$AGY/"
  # O compose da conta 1003 tem UM servico. `jaiminho-server` e a rede `wiki` sao do
  # daemon do claudinho e nao atravessam para ca.
  python3 - "$AGY/docker-compose.yml" <<'PY'
import re
import sys
p = sys.argv[1]
t = open(p).read()
t = t.split("  # O MCP DELE.")[0].rstrip() + "\n"
# origem do bind da entrada, qualquer que fosse o prefixo da conta naquele estado
t = re.sub(r"[^\s:'\"]*/var/entrada-jaiminho", "/srv/pf/entrada-jaiminho", t)
t += "\nnetworks:\n  saida:\n    driver: bridge\n\nvolumes:\n  casa:\n  credenciais:\n"
open(p, "w").write(t)
PY
  chown -R jaiminho:jaiminho "$AGY"
  echo "ok: $AGY, $ENTRADA e $MIG prontos"
  ;;

docker)     # root. Liga o Docker rootless da conta 1003. linger e subuid ja estao feitos.
  loginctl enable-linger jaiminho
  grep -q '^jaiminho:' /etc/subuid || { echo "FALTA subuid para jaiminho"; exit 1; }
  como_jaiminho 'dockerd-rootless-setuptool.sh install && systemctl --user enable --now docker'
  como_jaiminho 'docker info --format "Rootless={{.SecurityOptions}}"'
  ;;

volume)     # como claudinho, SEM sudo. COPIA os dois volumes; os originais ficam.
  docker stop jaiminho
  for v in casa credenciais; do
    docker run --rm -v "jaiminho_$v:/from" -v "$MIG:/to" alpine tar -C /from -cf "/to/$v.tar" .
  done
  chmod -R a+rX "$MIG"
  echo "ok: tar em $MIG. Agora: sudo bash $0 subir"
  ;;

subir)      # root -> conta 1003. Restaura os volumes e sobe o conteiner do lado de la.
  como_jaiminho "docker volume create jaiminho_casa; docker volume create jaiminho_credenciais"
  for v in casa credenciais; do
    como_jaiminho "docker run --rm -v jaiminho_$v:/to -v $MIG:/from alpine tar -C /to -xf /from/$v.tar"
  done
  como_jaiminho "cd $AGY && docker compose up -d jaiminho"
  ;;

conferir)   # ordem importa: primeiro o lado de la vivo, depois o de ca vazio.
  echo "== conta 1003 =="
  como_jaiminho 'docker ps --format "{{.Names}} {{.Status}}"'
  echo "== ponte MCP viva dentro do conteiner =="
  como_jaiminho 'docker exec jaiminho python3 -c "import urllib.request;print(urllib.request.urlopen(\"http://127.0.0.1:8022/estado\",timeout=8).status)"'
  echo "== conta claudinho: NAO deve listar jaiminho =="
  runuser -u claudinho -- docker ps --format '{{.Names}}' | grep -x jaiminho \
    && echo "AINDA RODANDO AQUI" || echo "ok: saiu daqui"
  echo "== /saida escreve no lugar novo =="
  ls -la "$ENTRADA" | tail -3
  ;;

rollback)   # dois atos, e e por isso que este recorte e o seguro.
  como_jaiminho 'docker stop jaiminho; docker rm jaiminho' || true
  COMPOSE_ORIGEM="$(origem MIGRAR_COMPOSE_ORIGEM)"
  runuser -u claudinho -- bash -lc "cd $COMPOSE_ORIGEM && docker compose up -d jaiminho"
  echo "ok: voltou para o daemon do claudinho, com os volumes originais intactos"
  ;;

*) sed -n '1,25p' "$0"; exit 1 ;;
esac
