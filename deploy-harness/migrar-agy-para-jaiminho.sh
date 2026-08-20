#!/usr/bin/env bash
# Migra os tres conteineres do motor `agy` para a conta `jaiminho` (uid 1003).
#
#   sudo bash migrar-agy-para-jaiminho.sh            # tudo
#   sudo bash migrar-agy-para-jaiminho.sh --so-bracos # para antes do jaiminho-server
#   sudo bash migrar-agy-para-jaiminho.sh --conferir  # so mede, nao muda nada
#   sudo bash migrar-agy-para-jaiminho.sh --voltar    # rollback
#
# POR QUE (seg:0013, card #2286): a fabrica executa `git`, `python3` e `uv` sob o
# daemon da conta `claudinho`, que e a conta das CADEIRAS. O perimetro efetivo do
# fornecedor Google e hoje o namespace delas. Braco novo nao se pendura ali.
#
# O QUE ESTE SCRIPT NAO E: controle de acesso. Quem o bot alcanca e decidido pelo
# PAP, por SUJEITO, e nao muda nada aqui — a wiki segue alcancavel por qualquer bot
# autenticado e autorizado, venha de que conta vier. Conta de SO responde por outra
# coisa: socket do daemon, volume, credencial em disco e o que um escape alcanca.
#
# IDEMPOTENTE: cada etapa confere o estado antes de agir. Rodar duas vezes nao
# duplica nada. COPIA volumes, nunca move — o rollback depende disso.
set -uo pipefail

DONO_CADEIRAS=claudinho
CONTA=jaiminho
UID_CONTA=1003
BASE=/srv/pf
DEPLOY=$BASE/agy
MIG=$BASE/mig
ENTRADA=$BASE/entrada-jaiminho
ORIGEM="/home/$DONO_CADEIRAS/AI/platafirma-harness"
VOLUMES=(jaiminho_casa jaiminho_credenciais jaiminho_trabalho
         jaiminho-fabrica_casa jaiminho-fabrica_credenciais)
BRACOS=(jaiminho jaiminho-fabrica)
SERVER=jaiminho-server

MODO=tudo
case "${1:-}" in
  --so-bracos) MODO=bracos ;;
  --conferir)  MODO=conferir ;;
  --voltar)    MODO=voltar ;;
  "")          ;;
  *) echo "opcao desconhecida: $1"; exit 2 ;;
esac

ok()   { printf '  \033[32mok\033[0m    %s\n' "$*"; }
falta(){ printf '  \033[33mfalta\033[0m %s\n' "$*"; }
erro() { printf '  \033[31mERRO\033[0m  %s\n' "$*"; }
passo(){ printf '\n\033[1m== %s\033[0m\n' "$*"; }

como_dono()  { sudo -u "$DONO_CADEIRAS" XDG_RUNTIME_DIR=/run/user/1001 "$@"; }
como_conta() { sudo -u "$CONTA" XDG_RUNTIME_DIR="/run/user/$UID_CONTA" "$@"; }

[ "$(id -u)" -eq 0 ] || { erro "precisa de root: os passos 1-3 e os binds fora de ~ exigem."; exit 1; }

# --- 0. estado ---------------------------------------------------------------
passo "0. estado atual"
getent passwd "$CONTA" >/dev/null && ok "conta $CONTA existe (uid $(id -u $CONTA))" || { erro "conta $CONTA nao existe"; exit 1; }
[ -f "/var/lib/systemd/linger/$CONTA" ] && ok "linger ligado" || falta "linger"
grep -q "^$CONTA:" /etc/subuid && ok "subuid: $(grep "^$CONTA:" /etc/subuid)" || falta "subuid"
grep -q "^$CONTA:" /etc/subgid && ok "subgid alocado" || falta "subgid"
if como_conta docker info >/dev/null 2>&1; then ok "dockerd rootless do $CONTA respondendo"; TEM_DOCKER=1
else falta "dockerd rootless do $CONTA"; TEM_DOCKER=0; fi
echo "  conteineres agy no daemon de $DONO_CADEIRAS:"
como_dono docker ps --format '    {{.Names}}  {{.Status}}' | grep -E 'jaiminho' || echo "    (nenhum)"

[ "$MODO" = conferir ] && exit 0

# --- rollback ----------------------------------------------------------------
if [ "$MODO" = voltar ]; then
  passo "rollback — volta para o daemon de $DONO_CADEIRAS"
  for c in "${BRACOS[@]}" "$SERVER"; do
    como_conta docker rm -f "$c" >/dev/null 2>&1 && ok "removido de $CONTA: $c"
  done
  (cd "$ORIGEM/jaiminho" && como_dono docker compose up -d) && ok "jaiminho + $SERVER de volta"
  (cd "$ORIGEM/jaiminho-fabrica" && como_dono docker compose up -d) && ok "jaiminho-fabrica de volta"
  echo
  echo "Os volumes originais nunca foram apagados: e por isso que isto e um comando so."
  exit 0
fi

# --- 1. linger ---------------------------------------------------------------
passo "1. linger (o daemon precisa sobreviver ao logout)"
if [ -f "/var/lib/systemd/linger/$CONTA" ]; then ok "ja ligado"
else loginctl enable-linger "$CONTA" && ok "ligado"; fi

# --- 2. subuid/subgid --------------------------------------------------------
passo "2. faixa de uid para o namespace do rootless"
for arq in /etc/subuid /etc/subgid; do
  if grep -q "^$CONTA:" "$arq"; then ok "$arq ja tem $CONTA"
  else
    ini=$(awk -F: '{if($2+$3>m)m=$2+$3}END{print (m?m:100000)}' "$arq")
    echo "$CONTA:$ini:65536" >> "$arq" && ok "$arq: faixa $ini"
  fi
done

# --- 3. dockerd rootless -----------------------------------------------------
passo "3. dockerd rootless sob uid $UID_CONTA"
if [ "$TEM_DOCKER" = 1 ]; then ok "ja de pe"
else
  command -v dockerd-rootless-setuptool.sh >/dev/null || { erro "instale docker-ce-rootless-extras"; exit 1; }
  machinectl shell "$CONTA@" /bin/bash -lc \
    'dockerd-rootless-setuptool.sh install && systemctl --user enable --now docker' \
    || sudo -iu "$CONTA" bash -lc \
       'export XDG_RUNTIME_DIR=/run/user/'"$UID_CONTA"'; dockerd-rootless-setuptool.sh install; systemctl --user enable --now docker'
  sleep 3
  como_conta docker info >/dev/null 2>&1 && ok "dockerd de pe" || { erro "dockerd nao subiu; veja: journalctl --user -u docker (como $CONTA)"; exit 1; }
fi

# --- 4. arvore de deploy e binds fora de ~claudinho --------------------------
# /home/claudinho e 750: o uid 1003 NAO atravessa. Todo bind que hoje aponta para
# dentro da casa das cadeiras tem de sair de la — e o compose e o .env junto, que
# tambem moram la. Esta e a DIVIDA que a migracao cria e que fica declarada:
# /srv/pf/agy e copia, e copia enverdece sozinha. Sincronizar e de claudinho-TI.
passo "4. arvore de deploy da conta e area de escrita"
install -d -o "$CONTA" -g "$CONTA" -m 0755 "$BASE" "$DEPLOY" && ok "$DEPLOY"
install -d -o "$DONO_CADEIRAS" -g "$DONO_CADEIRAS" -m 0755 "$MIG" && ok "$MIG (area de passagem)"
# entrada-jaiminho: o conteiner escreve, e claudinho-TI le para chamar `acervo-drop`.
# setgid no grupo das cadeiras e o que faz o arquivo nascer legivel pelos dois.
install -d -o "$CONTA" -g "$DONO_CADEIRAS" -m 2770 "$ENTRADA" && ok "$ENTRADA (escrita do conteiner)"
if [ -d "/home/$DONO_CADEIRAS/AI/var/entrada-jaiminho" ]; then
  rsync -a "/home/$DONO_CADEIRAS/AI/var/entrada-jaiminho/" "$ENTRADA/" && ok "conteudo antigo copiado"
fi
install -d -o "$CONTA" -g "$CONTA" -m 0755 "$BASE/log-jaiminho" && ok "$BASE/log-jaiminho"

for stack in jaiminho jaiminho-fabrica; do
  install -d -o "$CONTA" -g "$CONTA" -m 0755 "$DEPLOY/$stack"
  sed -e 's|\${HOME}/AI/var/entrada-jaiminho|'"$ENTRADA"'|g' \
      -e 's|\${HOME}/AI/var/log/jaiminho|'"$BASE/log-jaiminho"'|g' \
      -e 's|\${HOME}/AI/platafirma-harness/politica-acesso|'"$DEPLOY/politica-acesso"'|g' \
      -e 's|\${HOME}/AI/var/google/token.json|'"$DEPLOY/google-token.json"'|g' \
      "$ORIGEM/$stack/docker-compose.yml" > "$DEPLOY/$stack/docker-compose.yml"
  sed -i '1i # GERADO por migrar-agy-para-jaiminho.sh — NAO EDITE AQUI.\n# A fonte e platafirma-harness/'"$stack"'/docker-compose.yml.' \
      "$DEPLOY/$stack/docker-compose.yml"
  [ -f "$ORIGEM/$stack/.env" ] && install -o "$CONTA" -g "$CONTA" -m 0600 "$ORIGEM/$stack/.env" "$DEPLOY/$stack/.env"
  chown -R "$CONTA:$CONTA" "$DEPLOY/$stack"
  ok "$DEPLOY/$stack (compose gerado)"
done
# PAP read-only: o processo nao pode reescrever a regra que o prende.
rsync -a --delete --exclude '__pycache__' --exclude '.pytest_cache' \
      "$ORIGEM/politica-acesso/" "$DEPLOY/politica-acesso/"
chown -R root:"$CONTA" "$DEPLOY/politica-acesso"; chmod -R u=rwX,g=rX,o= "$DEPLOY/politica-acesso"
ok "PAP copiado, root:$CONTA, so leitura para a conta"
if [ -f "/home/$DONO_CADEIRAS/AI/var/google/token.json" ]; then
  install -o "$CONTA" -g "$CONTA" -m 0600 "/home/$DONO_CADEIRAS/AI/var/google/token.json" "$DEPLOY/google-token.json"
  ok "credencial do Google copiada (modo 600)"
fi

# --- 5. imagens --------------------------------------------------------------
passo "5. imagens no daemon da conta"
for img in platafirma/jaiminho:local platafirma/jaiminho-server:local; do
  if como_conta docker image inspect "$img" >/dev/null 2>&1; then ok "$img ja la"
  else
    como_dono docker save "$img" | como_conta docker load >/dev/null && ok "$img transferida"
  fi
done

# --- 6. volumes (COPIA) ------------------------------------------------------
passo "6. volumes — copia, nunca move"
for v in "${VOLUMES[@]}"; do
  como_dono docker volume inspect "$v" >/dev/null 2>&1 || { falta "$v (nao existe na origem)"; continue; }
  if como_conta docker volume inspect "$v" >/dev/null 2>&1; then ok "$v ja existe no destino"; continue; fi
  # Parar antes de copiar: volume de conteiner vivo copia num estado intermediario.
  como_dono docker stop "${v%%_*}" >/dev/null 2>&1
  como_dono docker run --rm -v "$v:/de" -v "$MIG:/para" alpine \
      tar -C /de -cf "/para/$v.tar" . >/dev/null 2>&1 || { erro "falhou export de $v"; continue; }
  chmod a+r "$MIG/$v.tar"
  como_conta docker volume create "$v" >/dev/null
  como_conta docker run --rm -v "$v:/para" -v "$MIG:/de" alpine \
      tar -C /para -xf "/de/$v.tar" >/dev/null 2>&1 || { erro "falhou import de $v"; continue; }
  ok "$v copiado ($(du -sh "$MIG/$v.tar" | cut -f1))"
done

# --- 7. subir ----------------------------------------------------------------
passo "7. subir do lado da conta"
if [ "$MODO" = bracos ]; then
  # `jaiminho-server` fica no daemon das cadeiras. NAO e razao de seguranca — e
  # conectividade: ele resolve `keycloak`, `mcp` e `rag-api` por alias da rede
  # `plataforma-wiki_default`, que e de la, e essas portas estao em 127.0.0.1 do
  # host, que o bridge rootless daqui nao alcanca. Enquanto ficar assim, a fabrica
  # perde a rota /acervo. Resolver o endereco e de claudinho-TI.
  como_conta bash -lc "cd $DEPLOY/jaiminho && docker compose up -d jaiminho" && ok "jaiminho de pe em $CONTA"
  como_conta bash -lc "cd $DEPLOY/jaiminho-fabrica && docker compose up -d" && ok "jaiminho-fabrica de pe em $CONTA"
  como_dono docker rm -f jaiminho jaiminho-fabrica >/dev/null 2>&1 && ok "removidos do daemon de $DONO_CADEIRAS"
else
  como_conta bash -lc "cd $DEPLOY/jaiminho && docker compose up -d" && ok "jaiminho + $SERVER de pe em $CONTA"
  como_conta bash -lc "cd $DEPLOY/jaiminho-fabrica && docker compose up -d" && ok "jaiminho-fabrica de pe em $CONTA"
  como_dono docker rm -f jaiminho jaiminho-fabrica "$SERVER" >/dev/null 2>&1 && ok "removidos do daemon de $DONO_CADEIRAS"
fi

# --- 8. conferir -------------------------------------------------------------
passo "8. conferir (controle so vale verificado)"
if como_dono docker ps --format '{{.Names}}' | grep -q jaiminho
then erro "ainda ha conteiner agy no daemon de $DONO_CADEIRAS:"; como_dono docker ps --format '    {{.Names}}' | grep jaiminho
else ok "nenhum conteiner agy no daemon de $DONO_CADEIRAS — era este o ponto"; fi
como_conta docker ps --format '  %s  {{.Names}}  {{.Status}}' 2>/dev/null | grep -E 'jaiminho' || erro "nada de pe em $CONTA"
como_conta docker exec jaiminho python3 -c \
  "import urllib.request;print('ponte:',urllib.request.urlopen('http://127.0.0.1:8022/estado',timeout=8).status)" \
  2>/dev/null || falta "ponte do jaiminho (pode levar ~30s para o healthcheck)"
echo
echo "FALTA CONFERIR A MAO, e o script nao mede por voce:"
echo "  1. a credencial do \`agy\` sobreviveu (a sessao nao pede login de novo)"
echo "  2. \`jaiminho-fabrica perguntar\` gira"
echo "  3. escrita em /saida aparece em $ENTRADA"
echo
echo "Rollback: sudo bash $0 --voltar"
echo "Os volumes de origem em ~$DONO_CADEIRAS seguem intactos. So apague depois de"
echo "uma semana estavel — enquanto existirem, a volta e um comando."
