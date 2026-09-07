#!/usr/bin/env bash
# Toolchain nao-Python da conta de provider `jaiminho` (uid 1003), sem container.
#
#   bash toolchain-conta-jaiminho.sh --conferir   # so mede, nao muda nada (default)
#   bash toolchain-conta-jaiminho.sh --aceite     # roda o aceite do #3005 ponta a ponta
#   bash toolchain-conta-jaiminho.sh --limpar     # apaga a area de trabalho do aceite
#
# POR QUE (card #3005, sob #3003): o mundo-alvo do provider e SEM container — o
# perimetro e a conta/uid, nao uma imagem. A story (d) #3007 pos a execucao sob uid
# 1003; esta aqui responde a pergunta seguinte: um build que NAO e Python (npm ci +
# npm run build) fecha dentro desse perimetro?
#
# O QUE FICOU MEDIDO (07/09/2026, e o que `--conferir` reafere):
#   - node/npm/npx sao PACOTE DE HOST em /usr/bin, ja no PATH da conta. Era o ponto
#     branco do card ("sob o HOME da conta vs pacote de host"): nao ha o que instalar
#     sob o HOME, e instalar la duplicaria toolchain sem ganho de isolamento. O
#     isolamento e o uid, e ler um binario de /usr/bin nao o afrouxa — a conta nao
#     escreve la, e `npm config prefix` = /usr so pesa em `npm i -g`, que a conta nao
#     faz (dependencia de projeto vive em node_modules, sob o HOME).
#   - /home/claudinho e 0750: a conta NAO le ~/AI. O repo entra no perimetro pelo
#     entreposto /srv/pf/entrada-jaiminho, como bundle git — nao por leitura lateral.
#
# O QUE ESTE SCRIPT NAO E: caminho de producao para disparar build. Pela porta
# so-verbo (spec_porta-so-verbo §3.5) `npm`/`node`/`npx` nao tem verbo que os cubra
# (`_SUGESTAO` em ops-server/server.py devolve `sugestao: null` = verbo que falta).
# Aqui o disparo e do operador do host, por sudo; o build e que roda na conta.
#
# IDEMPOTENTE: `--aceite` recria a area de trabalho do zero a cada corrida, e usa
# cache npm frio de proposito — a corrida tem de provar rede + instalacao, nao
# reaproveitar o que uma corrida anterior deixou em ~/.npm.
set -uo pipefail

CONTA=jaiminho
UID_CONTA=1003
ENTREPOSTO=/srv/pf/entrada-jaiminho/3005
TRABALHO=/home/jaiminho/trabalho/3005
REPO_FONTE=${REPO_FONTE:-/home/claudinho/AI/platafirma-ui}
REPO_NOME=platafirma-ui
SUBDIR=src/base          # o unico pacote da stack com script de build de verdade

falhou=0
ok()    { printf '  ok   %s\n' "$*"; }
falha() { printf '  FALHA %s\n' "$*"; falhou=1; }

# Roda na conta, sempre a partir de /tmp: herdar cwd de ~/AI da EACCES no uid 1003
# antes mesmo de o comando comecar (git morre em `failed to stat`).
na_conta() { (cd /tmp && sudo -n -u "$CONTA" bash -lc "$1"); }

conferir() {
  echo "== toolchain da conta $CONTA (uid $UID_CONTA)"
  if ! sudo -n -u "$CONTA" true 2>/dev/null; then
    falha "sudo -u $CONTA indisponivel — sem a regra de sudoers nao ha o que medir"
    return
  fi
  ok "sudo -u $CONTA responde"
  local id_visto
  id_visto=$(na_conta 'id -u')
  [ "$id_visto" = "$UID_CONTA" ] && ok "uid efetivo $id_visto" \
                                 || falha "uid efetivo $id_visto (esperado $UID_CONTA)"
  local prog
  for prog in node npm npx; do
    local onde ver
    onde=$(na_conta "command -v $prog" 2>/dev/null)
    ver=$(na_conta "$prog --version" 2>/dev/null)
    if [ -n "$onde" ]; then ok "$prog $ver em $onde"
    else falha "$prog ausente no PATH da conta"; fi
  done
  na_conta 'timeout 20 npm ping >/dev/null 2>&1' \
    && ok "registry alcancavel de dentro da conta" \
    || falha "registry inalcancavel de dentro da conta"
  na_conta "test -r $REPO_FONTE" 2>/dev/null \
    && falha "a conta LE $REPO_FONTE — o perimetro do host esta frouxo" \
    || ok "a conta nao le ~/AI (perimetro do host fechado)"
}

aceite() {
  echo "== aceite #3005: build nao-Python na conta $CONTA, sem container"
  # 1. repo da stack entra no perimetro como bundle, pelo entreposto.
  rm -rf "$ENTREPOSTO"; mkdir -p "$ENTREPOSTO" || { falha "entreposto"; return; }
  git -C "$REPO_FONTE" bundle create "$ENTREPOSTO/$REPO_NOME.bundle" main >/dev/null 2>&1 \
    && ok "bundle de $REPO_NOME no entreposto" || { falha "bundle"; return; }
  chmod 0644 "$ENTREPOSTO/$REPO_NOME.bundle"

  # 2. daqui para baixo, tudo roda como uid 1003.
  na_conta "rm -rf $TRABALHO; mkdir -p $TRABALHO" || { falha "area de trabalho"; return; }
  na_conta "cd $TRABALHO && git clone -b main $ENTREPOSTO/$REPO_NOME.bundle $REPO_NOME" \
    >/dev/null 2>&1 && ok "clone do bundle dentro do perimetro" || { falha "clone"; return; }

  # 3. npm ci com cache frio (prova rede) + build.
  local base="$TRABALHO/$REPO_NOME/$SUBDIR"
  na_conta "cd $base && npm ci --cache $TRABALHO/npmcache-frio" \
    && ok "npm ci (cache frio) fechou" || falha "npm ci"
  na_conta "cd $base && npm run build" \
    && ok "npm run build fechou" || falha "npm run build"

  # 4. a saida tem de sair com owner da conta — e a prova do perimetro no disco.
  local dono
  dono=$(na_conta "stat -c %u:%g $TRABALHO/$REPO_NOME/dist/pf-ui.js" 2>/dev/null)
  [ "$dono" = "$UID_CONTA:$UID_CONTA" ] \
    && ok "dist/pf-ui.js com owner $dono" \
    || falha "dist/pf-ui.js com owner $dono (esperado $UID_CONTA:$UID_CONTA)"
  local baixado
  baixado=$(na_conta "du -sm $TRABALHO/npmcache-frio 2>/dev/null | cut -f1")
  [ "${baixado:-0}" -gt 0 ] 2>/dev/null \
    && ok "cache frio populado: ${baixado} MB vieram do registry" \
    || falha "cache frio vazio — o npm ci nao foi buscar nada"
}

limpar() {
  na_conta "rm -rf $TRABALHO"
  rm -rf "$ENTREPOSTO"
  echo "area de trabalho e entreposto do #3005 apagados"
}

case "${1:---conferir}" in
  --conferir) conferir ;;
  --aceite)   conferir; aceite ;;
  --limpar)   limpar ;;
  *) echo "uso: $0 [--conferir|--aceite|--limpar]" >&2; exit 2 ;;
esac
exit "$falhou"
