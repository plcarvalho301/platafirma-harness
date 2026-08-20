#!/usr/bin/env bash
# Migracao dos bracos do motor `agy` para a conta `jaiminho` (uid 1003) — card #2286.
# RODAR COMO ROOT, do host. Idempotente: pode rodar de novo se parar no meio.
# Autor: claudinho-seguranca (chapeu iam), 20/08/2026.
#
# NAO APAGA NADA. Volume e imagem sao COPIADOS; os originais do `claudinho` ficam
# intactos, e e isso que torna o rollback imediato (ver ROLLBACK.md).
set -euo pipefail

CLAUD=claudinho
JAI=jaiminho
UID_JAI=1003
ORIGEM=/home/claudinho/AI/var/migracao-2286
MIG=/srv/pf/mig

comoJai() { sudo -u "$JAI" XDG_RUNTIME_DIR=/run/user/$UID_JAI DOCKER_HOST=unix:///run/user/$UID_JAI/docker.sock bash -lc "$*"; }
comoClaud() { sudo -u "$CLAUD" bash -lc "$*"; }
passo() { printf '\n=== %s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "rode como root"; exit 1; }

passo "0. pre-condicoes (ja medidas em 20/08: linger e subuid OK)"
loginctl enable-linger "$JAI"
grep -q "^${JAI}:" /etc/subuid || { echo "FALTA subuid para $JAI"; exit 1; }
grep -q "^${JAI}:" /etc/subgid || { echo "FALTA subgid para $JAI"; exit 1; }

passo "1. diretorios fora de /home/claudinho (0750 nao deixa o 1003 entrar)"
install -d -o "$JAI"    -g "$CLAUD" -m 2770 /srv/pf/entrada-jaiminho
install -d -o "$JAI"    -g "$JAI"   -m 0755 /srv/pf/agy
install -d -o "$CLAUD"  -g "$CLAUD" -m 0777 "$MIG"
rsync -a /home/claudinho/AI/var/entrada-jaiminho/ /srv/pf/entrada-jaiminho/ || true
chown -R "$JAI":"$CLAUD" /srv/pf/entrada-jaiminho

passo "2. arvore de deploy da conta 1003"
for d in jaiminho jaiminho-fabrica; do
  install -d -o "$JAI" -g "$JAI" -m 0750 "/srv/pf/agy/$d"
  install -o "$JAI" -g "$JAI" -m 0640 "$ORIGEM/$d/docker-compose.yml" "/srv/pf/agy/$d/docker-compose.yml"
  install -o "$JAI" -g "$JAI" -m 0600 "/home/claudinho/AI/platafirma-harness/$d/.env" "/srv/pf/agy/$d/.env"
done

passo "3. docker rootless sob o uid $UID_JAI"
if ! comoJai "docker info >/dev/null 2>&1"; then
  sudo -u "$JAI" XDG_RUNTIME_DIR=/run/user/$UID_JAI bash -lc \
    'dockerd-rootless-setuptool.sh install --force'
  sudo -u "$JAI" XDG_RUNTIME_DIR=/run/user/$UID_JAI bash -lc \
    'systemctl --user enable --now docker'
fi
comoJai "docker info --format '{{.Name}} rootless={{.SecurityOptions}}'"

passo "4. imagem (save/load, sem segunda arvore de build)"
comoClaud "docker save platafirma/jaiminho:local -o $MIG/img-jaiminho.tar"
chmod 0644 "$MIG/img-jaiminho.tar"
comoJai "docker load -i $MIG/img-jaiminho.tar"

passo "5. parar os dois bracos do lado do claudinho (o server NAO para)"
comoClaud "docker stop jaiminho jaiminho-fabrica"

passo "6. copiar os volumes (COPIA — o original fica)"
for v in jaiminho_casa jaiminho_credenciais jaiminho-fabrica_casa jaiminho-fabrica_credenciais; do
  comoClaud "docker run --rm -v ${v}:/from -v $MIG:/to alpine tar -C /from -cf /to/${v}.tar ."
  chmod 0644 "$MIG/${v}.tar"
  comoJai "docker volume create ${v} >/dev/null"
  comoJai "docker run --rm -v ${v}:/to -v $MIG:/from alpine tar -C /to -xf /from/${v}.tar"
  echo "  volume ${v}: copiado"
done

passo "7. subir do lado da conta 1003"
comoJai "cd /srv/pf/agy/jaiminho        && docker compose up -d"
comoJai "cd /srv/pf/agy/jaiminho-fabrica && docker compose up -d"

passo "8. conferir"
echo "-- daemon do claudinho: NAO deve listar jaiminho nem jaiminho-fabrica"
comoClaud "docker ps --format '{{.Names}}'" | grep -E '^jaiminho' || echo "   (limpo)"
echo "-- daemon do jaiminho: os dois bracos"
comoJai "docker ps --format '{{.Names}}\t{{.Status}}'"
echo "-- ponte viva dentro do braco osint"
comoJai "docker exec jaiminho python3 -c \"import urllib.request;print('ponte:',urllib.request.urlopen('http://127.0.0.1:8022/estado',timeout=8).status)\"" || echo "   ponte NAO respondeu — ver ROLLBACK.md"
echo "-- credencial do agy sobreviveu?"
comoJai "docker exec jaiminho ls -la /home/jaiminho/.antigravity | head -5"

passo "FIM. Nada foi apagado. $MIG pode ser removido depois de uma semana estavel."
