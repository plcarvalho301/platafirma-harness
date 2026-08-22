#!/usr/bin/env bash
# alcance-claudinho.sh — devolve ao uid 1001 o alcance do daemon rootless da conta
# `jaiminho` (uid 1003), sem mover container nenhum. Resíduo do card #2286.
#
# RODAR COMO ROOT, do host. Idempotente. NÃO reinicia o daemon: os dois braços do
# `agy` seguem vivos durante a aplicação.
#
# O QUE QUEBROU, e por quê
#   Em 20/08/2026 19:44 os dois braços do `agy` passaram ao daemon rootless do uid
#   1003. O `chat-worker` — que é quem executa `jaiminho perguntar` quando o dono
#   fala na sala — roda como `claudinho` (uid 1001), e /run/user/1003 é 0700 do
#   dono. Desde então TODO giro das salas `jaiminho` e `jaiminho-fabrica` fecha
#   como erro em ~1,2 s. Medido em 22/08: giros 217 a 220, todos `fechou como erro`.
#   O braço está NO AR: o defeito é de alcance, não de serviço.
#
# O QUE ESTE SCRIPT FAZ
#   1. Drop-in no `docker.service` do usuário 1003 que reaplica a ACL a cada start
#      — o socket nasce novo a cada boot do daemon, e ACL em arquivo não sobrevive.
#   2. Aplica a ACL AGORA, no socket vivo, para o chat voltar sem reiniciar nada.
#
# O QUE ELE CUSTA — leia antes de rodar
#   Quem alcança o `docker.sock` do 1003 pode subir container montando os volumes
#   daquela conta, e o login do Google do dono mora no volume `jaiminho_casa`
#   (em `.gemini`, não no volume `credenciais`, que está vazio desde 14/08). Ou
#   seja: depois desta ACL, o uid 1001 alcança aquela credencial. O isolamento que
#   o #2286 comprou na direção "agy escapou → cai no 1003" continua intacto; o que
#   se abre é a direção inversa, operador → conta do externo.
#   A decisão de manter isto é de claudinho-seguranca, que foi quem migrou.
#
# REVERTER — duas linhas, efeito imediato:
#   rm /home/jaiminho/.config/systemd/user/docker.service.d/alcance-claudinho.conf
#   setfacl -x u:claudinho /run/user/1003/docker.sock; setfacl -x u:claudinho /run/user/1003
#
# Autor: claudinho-TI (chapéu plataforma), 22/08/2026.
set -euo pipefail

JAI=jaiminho
UID_JAI=1003
CLAUD=claudinho
DROPIN_DIR="/home/$JAI/.config/systemd/user/docker.service.d"
DROPIN="$DROPIN_DIR/alcance-claudinho.conf"

[ "$(id -u)" -eq 0 ] || { echo "rode como root (sudo)"; exit 1; }
id "$CLAUD" >/dev/null || { echo "sem usuário $CLAUD"; exit 1; }
command -v setfacl >/dev/null || { echo "FALTA o pacote acl: apt install acl"; exit 1; }

comoJai() {
  sudo -u "$JAI" XDG_RUNTIME_DIR="/run/user/$UID_JAI" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$UID_JAI/bus" bash -lc "$*"
}
passo() { printf '\n=== %s\n' "$*"; }

passo "1. drop-in que reaplica a ACL a cada start do daemon do $UID_JAI"
install -d -o "$JAI" -g "$JAI" -m 0755 "$DROPIN_DIR"
cat > "$DROPIN" <<EOF
# Resíduo do card #2286: o chat-worker roda como $CLAUD e precisa deste socket.
# '-' na frente: se o setfacl falhar, o daemon NÃO deixa de subir por causa disto.
[Service]
ExecStartPost=-/usr/bin/setfacl -m u:$CLAUD:x  /run/user/$UID_JAI
ExecStartPost=-/usr/bin/setfacl -m u:$CLAUD:rw /run/user/$UID_JAI/docker.sock
EOF
chown "$JAI":"$JAI" "$DROPIN"
chmod 0644 "$DROPIN"
comoJai "systemctl --user daemon-reload"

passo "2. aplicar no socket VIVO (sem restart: os dois braços seguem de pé)"
setfacl -m "u:$CLAUD:x"  "/run/user/$UID_JAI"
setfacl -m "u:$CLAUD:rw" "/run/user/$UID_JAI/docker.sock"

passo "3. prova — o que $CLAUD enxerga agora do daemon $UID_JAI"
sudo -u "$CLAUD" DOCKER_HOST="unix:///run/user/$UID_JAI/docker.sock" \
  docker ps --format '{{.Names}}\t{{.Status}}'

printf '\nPronto. Prove o caminho inteiro com:\n'
printf "  sudo -u %s bash -lc 'jaiminho estado'\n" "$CLAUD"
printf 'e mande "oi" na sala do Jaiminho. Reverter: ver o cabeçalho deste arquivo.\n'
