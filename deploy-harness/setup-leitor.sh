#!/usr/bin/env bash
# setup-leitor.sh — instala e confere contas, grupo, unidades systemd, sudoers e ajudante do leitor único.
# Uso:
#   sudo bash deploy-harness/setup-leitor.sh           # instala/atualiza como root
#   bash deploy-harness/setup-leitor.sh --check        # confere sem root (exit 0 conforme, 1 divergente, 2 uso)
set -euo pipefail
IFS=$' \t\n'
PATH="/usr/sbin:/usr/bin:/sbin:/bin"

ORIGEM_PADRAO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ORIGEM="${PF_UNITS_ORIGEM:-$ORIGEM_PADRAO}"
SYSTEMD_DIR="${PF_SYSTEMD_DIR:-/etc/systemd/system}"
CREDSTORE_DIR="${PF_CREDSTORE_DIR:-/etc/credstore}"
# A senha do papel pf_leitor_ro, que `seg segredo rotacionar leitor/casa-db --postgres casa pf_leitor_ro` gera e guarda
# no cofre da instância; o roteiro a copia para o credstore que o leitor.service lê por LoadCredential=.
SEGREDO_CASA_DB="${PF_SEGREDO_LEITOR_CASA_DB:-/srv/platafirma/casa/segredos/leitor/casa-db}"
SUDOERS_ARQ="${PF_SUDOERS_ARQ:-/etc/sudoers.d/platafirma-leitor}"
AJUDANTE_LOGS="${PF_AJUDANTE_LOGS:-/usr/local/libexec/platafirma/leitor-logs}"
CHECK_SEM_CONTAS="${PF_CHECK_SEM_CONTAS:-0}"
CHECK_SEM_DONO="${PF_CHECK_SEM_DONO:-0}"

UNIDADES=(
  "leitor.socket"
  "leitor.service"
  "leitor-extrator.socket"
  "leitor-extrator@.service"
)

CONTA_LEITOR="pf-leitor"
CONTA_EXTRATOR="pf-leitor-extrator"
GRUPO_VERBOS="pf-verbos"
GRUPO_ESCRITA="platafirma-escrita"
CONTA_CHAMADORA="${PF_CONTA_CHAMADORA:-claudinho}"

MODO="instalar"
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODO="check" ;;
    -h|--help)
      printf 'uso: %s [--check]\n' "$0"
      exit 0
      ;;
    *)
      printf 'setup-leitor.sh: opção desconhecida: %s\n' "$1" >&2
      exit 2
      ;;
  esac
  shift
done

ERROS=0
divergencia() {
  printf 'divergente: %s\n' "$1"
  ERROS=$((ERROS + 1))
}

tem_diretiva() {
  local arq="$1" padrao="$2"
  grep -Eq -- "$padrao" "$arq"
}

conferir_diretivas_unidade() {
  local nome="$1" arq="$2"
  case "$nome" in
    leitor.socket)
      tem_diretiva "$arq" '^ListenStream=/run/platafirma/leitor/leitor\.sock$' || divergencia "$arq: falta ListenStream=/run/platafirma/leitor/leitor.sock"
      tem_diretiva "$arq" '^SocketUser=pf-leitor$' || divergencia "$arq: falta SocketUser=pf-leitor"
      tem_diretiva "$arq" '^SocketGroup=pf-verbos$' || divergencia "$arq: falta SocketGroup=pf-verbos"
      tem_diretiva "$arq" '^SocketMode=0660$' || divergencia "$arq: falta SocketMode=0660"
      ;;
    leitor.service)
      local d
      for d in \
        '^User=pf-leitor$' \
        '^Group=pf-verbos$' \
        '^UMask=0077$' \
        '^NoNewPrivileges=yes$' \
        '^ProtectSystem=strict$' \
        '^ProtectHome=yes$' \
        '^PrivateTmp=yes$' \
        '^PrivateDevices=yes$' \
        '^CapabilityBoundingSet=$' \
        '^RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6$' \
        '^IPAddressDeny=any$' \
        '^IPAddressAllow=localhost$' \
        '^SystemCallFilter=@system-service$' \
        '^SystemCallArchitectures=native$' \
        '^RestrictNamespaces=yes$' \
        '^LockPersonality=yes$' \
        '^ProtectKernelTunables=yes$' \
        '^ProtectKernelModules=yes$' \
        '^ProtectControlGroups=yes$' \
        '^KillMode=mixed$' \
        '^MemoryMax=.+$' \
        '^TasksMax=.+$' \
        '^TimeoutStopSec=.+$' \
        '^LoadCredential=.+$'; do
        tem_diretiva "$arq" "$d" || divergencia "$arq: diretiva obrigatória ausente ou alterada ($d)"
      done
      ;;
    leitor-extrator.socket)
      tem_diretiva "$arq" '^Accept=yes$' || divergencia "$arq: falta Accept=yes"
      tem_diretiva "$arq" '^SocketUser=pf-leitor$' || divergencia "$arq: falta SocketUser=pf-leitor"
      tem_diretiva "$arq" '^SocketMode=0600$' || divergencia "$arq: falta SocketMode=0600"
      tem_diretiva "$arq" '^SocketGroup=pf-verbos$' || divergencia "$arq: falta SocketGroup=pf-verbos"
      tem_diretiva "$arq" '^MaxConnections=[1-9][0-9]*$' || divergencia "$arq: falta MaxConnections="
      ;;
    leitor-extrator@.service)
      local d
      for d in \
        '^User=pf-leitor-extrator$' \
        '^PrivateNetwork=yes$' \
        '^ProtectSystem=strict$' \
        '^NoNewPrivileges=yes$' \
        '^SystemCallFilter=@system-service$' \
        '^LimitCORE=0$' \
        '^PrivateDevices=yes$' \
        '^CapabilityBoundingSet=$' \
        '^RestrictAddressFamilies=AF_UNIX$' \
        '^UMask=0077$' \
        '^MemoryMax=.+$'; do
        tem_diretiva "$arq" "$d" || divergencia "$arq: diretiva obrigatória ausente ou alterada ($d)"
      done
      if tem_diretiva "$arq" '^ReadWritePaths='; then
        divergencia "$arq: extrator não pode declarar ReadWritePaths="
      fi
      ;;
  esac
}

rodar_check() {
  local u src dst modo dono
  for u in "${UNIDADES[@]}"; do
    src="$ORIGEM/$u"
    dst="$SYSTEMD_DIR/$u"
    if [ ! -f "$src" ]; then
      divergencia "$src: unidade ausente na release"
      continue
    fi
    if [ -L "$dst" ]; then
      divergencia "$dst: deve ser cópia regular, não link simbólico"
      continue
    fi
    if [ ! -f "$dst" ]; then
      divergencia "$dst: unidade não instalada"
      continue
    fi
    if [ ! -r "$dst" ]; then
      divergencia "$dst: sem permissão de leitura"
      continue
    fi
    if ! cmp -s "$src" "$dst"; then
      divergencia "$dst: conteúdo diverge da release ($src)"
    fi
    modo="$(stat -c '%a' "$dst")"
    if [ "$modo" != "644" ]; then
      divergencia "$dst: modo esperado 644, encontrado $modo"
    fi
    if [ "$CHECK_SEM_DONO" != "1" ]; then
      dono="$(stat -c '%U:%G' "$dst")"
      if [ "$dono" != "root:root" ]; then
        divergencia "$dst: dono esperado root:root, encontrado $dono"
      fi
    fi
    conferir_diretivas_unidade "$u" "$dst"
  done

  if [ "$CHECK_SEM_CONTAS" != "1" ]; then
    getent group "$GRUPO_VERBOS" >/dev/null 2>&1 || divergencia "grupo $GRUPO_VERBOS ausente"
    local c
    for c in "$CONTA_LEITOR" "$CONTA_EXTRATOR"; do
      if ! getent passwd "$c" >/dev/null 2>&1; then
        divergencia "conta $c ausente"
      elif id -nG "$c" 2>/dev/null | tr ' ' '\n' | grep -Fxq "$GRUPO_ESCRITA"; then
        divergencia "conta $c não pode pertencer ao grupo $GRUPO_ESCRITA"
      fi
    done
    if [ -L "$AJUDANTE_LOGS" ] || [ ! -f "$AJUDANTE_LOGS" ]; then
      divergencia "$AJUDANTE_LOGS: ajudante de log ausente ou symlink"
    else
      modo="$(stat -c '%a' "$AJUDANTE_LOGS")"
      [ "$modo" = "755" ] || divergencia "$AJUDANTE_LOGS: modo esperado 755, encontrado $modo"
      if [ "$CHECK_SEM_DONO" != "1" ]; then
        dono="$(stat -c '%U:%G' "$AJUDANTE_LOGS")"
        [ "$dono" = "root:root" ] || divergencia "$AJUDANTE_LOGS: dono esperado root:root, encontrado $dono"
      fi
    fi
    if [ -r "$SUDOERS_ARQ" ]; then
      grep -Fq 'NOEXEC:' "$SUDOERS_ARQ" || divergencia "$SUDOERS_ARQ: regra sudoers sem NOEXEC:"
      grep -Fq '/usr/bin/systemctl restart leitor.service' "$SUDOERS_ARQ" || divergencia "$SUDOERS_ARQ: falta comando exato de restart"
      if grep -Eq '\*' "$SUDOERS_ARQ"; then
        divergencia "$SUDOERS_ARQ: curinga proibido em regra sudoers"
      fi
    fi
  fi

  if [ "$ERROS" -gt 0 ]; then
    exit 1
  fi
  printf 'conforme: leitor (%d unidades verificadas)\n' "${#UNIDADES[@]}"
  exit 0
}

instalar_ajudante_logs() {
  local dir tmp
  dir="$(dirname -- "$AJUDANTE_LOGS")"
  install -d -m 0755 -o root -g root "$dir"
  if [ -L "$AJUDANTE_LOGS" ]; then
    printf 'setup-leitor.sh: destino %s é symlink — abortado\n' "$AJUDANTE_LOGS" >&2
    exit 1
  fi
  tmp="$(mktemp "$dir/.leitor-logs.XXXXXX")"
  cat >"$tmp" <<'EOF'
#!/usr/bin/env bash
# Ajudante privilegiado de leitura de logs de leitor.service.
set -euo pipefail
IFS=$' \t\n'
PATH="/usr/bin:/bin"
n="${1:-50}"
if ! [[ "$n" =~ ^[1-9][0-9]{0,3}$ ]] || [ "$n" -gt 5000 ]; then
  printf 'leitor-logs: número de linhas inválido (1..5000): %s\n' "$n" >&2
  exit 2
fi
exec /usr/bin/journalctl --system --unit=leitor.service --no-pager -n "$n"
EOF
  chown root:root "$tmp"
  chmod 0755 "$tmp"
  mv -f "$tmp" "$AJUDANTE_LOGS"
}

instalar_sudoers() {
  local tmp
  if [ -L "$SUDOERS_ARQ" ]; then
    printf 'setup-leitor.sh: destino %s é symlink — abortado\n' "$SUDOERS_ARQ" >&2
    exit 1
  fi
  tmp="$(mktemp /etc/sudoers.d/.platafirma-leitor.XXXXXX)"
  cat >"$tmp" <<EOF
# Regras estreitas do leitor único — sem curingas. O restart leva NOEXEC; o ajudante
# não, porque ele é roteiro que precisa executar o interpretador e o journalctl, e NOEXEC barra os dois.
${CONTA_CHAMADORA} ALL=(root) NOPASSWD: NOEXEC: /usr/bin/systemctl restart leitor.service
${CONTA_CHAMADORA} ALL=(root) NOPASSWD: ${AJUDANTE_LOGS}
EOF
  chown root:root "$tmp"
  chmod 0440 "$tmp"
  if command -v visudo >/dev/null 2>&1; then
    visudo -cf "$tmp" >/dev/null || { rm -f "$tmp"; exit 1; }
  fi
  mv -f "$tmp" "$SUDOERS_ARQ"
}

instalar_credencial_casa_db() {
  local dst="$CREDSTORE_DIR/pf-leitor-casa-db" tmp
  if [ -L "$SEGREDO_CASA_DB" ] || [ ! -s "$SEGREDO_CASA_DB" ]; then
    printf 'setup-leitor.sh: segredo %s ausente ou vazio; gere com: seg segredo rotacionar leitor/casa-db --postgres casa pf_leitor_ro\n' "$SEGREDO_CASA_DB" >&2
    exit 1
  fi
  [ ! -L "$dst" ] || { printf 'setup-leitor.sh: destino %s é symlink — abortado\n' "$dst" >&2; exit 1; }
  tmp="$(mktemp "$CREDSTORE_DIR/.pf-leitor-casa-db.XXXXXX")"
  cat -- "$SEGREDO_CASA_DB" >"$tmp"
  chown root:root "$tmp"
  chmod 0600 "$tmp"
  mv -f "$tmp" "$dst"
}

rodar_instalar() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    printf 'setup-leitor.sh: instalação exige execução como root (use sudo); para conferir sem root use --check\n' >&2
    exit 4
  fi

  getent group "$GRUPO_VERBOS" >/dev/null 2>&1 || groupadd --system "$GRUPO_VERBOS"
  if ! getent passwd "$CONTA_LEITOR" >/dev/null 2>&1; then
    useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --gid "$GRUPO_VERBOS" "$CONTA_LEITOR"
  fi
  if ! getent passwd "$CONTA_EXTRATOR" >/dev/null 2>&1; then
    useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --user-group "$CONTA_EXTRATOR"
  fi
  if getent group "$GRUPO_ESCRITA" >/dev/null 2>&1; then
    local c
    for c in "$CONTA_LEITOR" "$CONTA_EXTRATOR"; do
      if id -nG "$c" | tr ' ' '\n' | grep -Fxq "$GRUPO_ESCRITA"; then
        gpasswd -d "$c" "$GRUPO_ESCRITA" >/dev/null
      fi
    done
  fi
  if getent passwd "$CONTA_CHAMADORA" >/dev/null 2>&1; then
    usermod -aG "$GRUPO_VERBOS" "$CONTA_CHAMADORA"
  fi

  install -d -m 0700 -o root -g root "$CREDSTORE_DIR"
  instalar_credencial_casa_db

  local u src dst
  for u in "${UNIDADES[@]}"; do
    src="$ORIGEM/$u"
    dst="$SYSTEMD_DIR/$u"
    [ -f "$src" ] || { printf 'setup-leitor.sh: unidade ausente em %s\n' "$src" >&2; exit 1; }
    [ ! -L "$dst" ] || { printf 'setup-leitor.sh: destino %s é symlink — abortado\n' "$dst" >&2; exit 1; }
    install -m 0644 -o root -g root "$src" "$dst"
  done

  instalar_ajudante_logs
  instalar_sudoers

  systemctl daemon-reload
  systemctl enable --now leitor-extrator.socket leitor.socket
  # O leitor já de pé só lê a credencial nova e a unidade nova depois de reiniciar.
  systemctl try-restart leitor.service

  # Smoke-test de leitura de release com a conta pf-leitor antes de ligar a chave em registro/leitura.yaml.
  su -s /bin/sh -c 'test -r /opt/platafirma/current/harness/registro/porta.yaml' "$CONTA_LEITOR" \
    || { printf 'setup-leitor.sh: aviso: %s não leu /opt/platafirma/current/harness/registro/porta.yaml\n' "$CONTA_LEITOR" >&2; exit 1; }

  printf 'instalado: leitor único e extrator (4 unidades, ajudante e sudoers)\n'
}

if [ "$MODO" = "check" ]; then
  rodar_check
else
  rodar_instalar
fi
