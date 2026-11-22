# lib/segredo/postgres.sh — senha de papel de banco da casa (débito 1343).
#
# Dono: seguranca (chapéu cripto). O ciclo da senha de um papel do Postgres é do verbo `seg`:
# `seg segredo rotacionar <stack>/<nome>... --postgres <banco> <papel>` cunha a primeira senha e
# faz cada troca seguinte pela mesma chamada. `release migrar senha` (card #3375) repassa a esta
# função com aviso de deprecação até sair.
#
# O valor não passa pelo chamador nem pela tela: nasce aqui, vai ao psql por stdin e a cada
# arquivo 0600 por rename atômico. A ordem protege o par: o banco aceita primeiro; recusou, os
# temporários somem e nada muda. Uma geração, um ALTER ROLE, N cópias (a mãe e cada `deriva-de`
# do armário de chaves), e por isso a troca nunca descasa as cópias entre si.
#
# O banco vem da allowlist registro/bancos.json (a mesma do `release migrar` e do `analise`); o
# papel é só [a-z0-9_]; o alvo é <stack>/<nome>, sem barra extra nem `..`.
#
# Uso (sourced):  pg_senha_trocar <banco> <papel> <stack>/<nome> [<stack>/<nome>...]
# Ambiente:       PG_SENHA_VERBO (rótulo das mensagens) · PLATAFIRMA_INSTANCIA · PF_SUJEITO (obrigatório)
# Saída:          0 ok · 1 o banco recusou · 2 uso · 3 dependência · 4 banco fora da allowlist ·
#                 5 senha trocada no banco e cópia não gravada (rode de novo)

_pg_senha_morre() { printf '%s: %s\n' "${PG_SENHA_VERBO:-seg segredo rotacionar}" "$1" >&2; exit "${2:-3}"; }

# Allowlist slug -> "contêiner:dono:base". Bash puro: o verbo roda com PATH mínimo, e o
# registro tem uma chave por linha.
_pg_senha_bancos() {
  local reg="$1" _l _s="" _c="" _b="" _d=""
  declare -gA PG_SENHA_BANCOS=()
  [ -r "$reg" ] || return 1
  while IFS= read -r _l || [ -n "$_l" ]; do
    if [[ "$_l" =~ ^\ \ \"([a-z_][a-z0-9_]*)\":\ \{ ]]; then _s="${BASH_REMATCH[1]}" _c="" _b="" _d=""
    elif [[ "$_l" =~ \"conteiner\":\ \"([^\"]+)\" ]]; then _c="${BASH_REMATCH[1]}"
    elif [[ "$_l" =~ \"base\":\ \"([^\"]+)\" ]]; then _b="${BASH_REMATCH[1]}"
    elif [[ "$_l" =~ \"dono\":\ \"([^\"]+)\" ]]; then _d="${BASH_REMATCH[1]}"
    elif [[ "$_l" =~ ^\ \ \} ]] && [ -n "$_s" ] && [ -n "$_c" ] && [ -n "$_b" ] && [ -n "$_d" ]; then
      PG_SENHA_BANCOS[$_s]="$_c:$_d:$_b"; _s=""
    fi
  done <"$reg"
  [ "${#PG_SENHA_BANCOS[@]}" -gt 0 ]
}

pg_senha_trocar() {
  local banco="${1:-}" role="${2:-}"
  shift 2 2>/dev/null || true
  local alvos=("$@")
  [ -n "$banco" ] && [ -n "$role" ] && [ "${#alvos[@]}" -gt 0 ] \
    || _pg_senha_morre "erro: uso: <banco> <papel> <stack>/<nome> [<stack>/<nome>...]" 2

  local reg
  reg="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/registro/bancos.json"
  _pg_senha_bancos "$reg" || _pg_senha_morre "erro: registro de bancos ausente ou ilegível: $reg" 3
  [ -n "${PG_SENHA_BANCOS[$banco]:-}" ] \
    || _pg_senha_morre "erro: banco '$banco' fora da allowlist — validos: ${!PG_SENHA_BANCOS[*]}" 4
  [[ "$role" =~ ^[a-z_][a-z0-9_]{0,62}$ ]] \
    || _pg_senha_morre "erro: role '$role' invalida — so [a-z0-9_], comecando por letra ou _" 2

  local raiz_seg="${PLATAFIRMA_INSTANCIA:-/srv/platafirma/casa}/segredos" alvo destinos=()
  for alvo in "${alvos[@]}"; do
    [[ "$alvo" =~ ^([A-Za-z0-9][A-Za-z0-9_.-]*)/([A-Za-z0-9][A-Za-z0-9_.-]*)$ ]] \
      || _pg_senha_morre "erro: segredo '$alvo' invalido — forma <stack>/<nome>, sem barra extra nem .." 2
    case "$alvo" in *..*) _pg_senha_morre "erro: segredo '$alvo' invalido — sem .." 2 ;; esac
    destinos+=("$raiz_seg/$alvo")
  done

  [ -n "${PF_SUJEITO:-}" ] \
    || _pg_senha_morre "erro: variável PF_SUJEITO: ausente — trocar senha de papel exige identidade; rode dentro da sessão" 3

  local ctr usr base
  IFS=: read -r ctr usr base <<<"${PG_SENHA_BANCOS[$banco]}"
  command -v docker >/dev/null 2>&1 || _pg_senha_morre "erro: dependência docker: ausente — 'docker' nao esta no PATH desta conta" 3
  docker inspect -f '{{.State.Running}}' "$ctr" 2>/dev/null | grep -qx true \
    || _pg_senha_morre "erro: dependência $ctr: ausente — contêiner nao esta de pe; \`infra estado\`" 3

  umask 077
  PG_SENHA_TMPS=()
  PG_SENHA_ERRLOG="$(mktemp)"
  trap 'rm -f "${PG_SENHA_TMPS[@]}" "$PG_SENHA_ERRLOG"' EXIT
  local senha destino dir t i
  senha="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  [ "${#senha}" -eq 48 ] || _pg_senha_morre "erro: nao consegui gerar a senha (/dev/urandom)" 3
  for destino in "${destinos[@]}"; do
    dir="$(dirname "$destino")"
    mkdir -p "$dir" || _pg_senha_morre "erro: nao consegui criar $dir" 3
    chmod 700 "$dir" 2>/dev/null || true
    t="$(mktemp "$dir/.$(basename "$destino").XXXXXX")" || _pg_senha_morre "erro: nao consegui escrever em $dir" 3
    PG_SENHA_TMPS+=("$t")
    printf '%s' "$senha" >"$t"
  done

  # -q -X: sem eco, sem psqlrc. stderr filtrado: a linha LINE de erro de sintaxe traria o valor.
  if ! printf "ALTER ROLE %s LOGIN PASSWORD '%s';\n" "$role" "$senha" \
      | docker exec -i "$ctr" psql -U "$usr" -d "$base" -X -q -v ON_ERROR_STOP=1 -1 -f - >/dev/null 2>"$PG_SENHA_ERRLOG"; then
    grep -v '^LINE' "$PG_SENHA_ERRLOG" | sed "s/$senha/***/g" >&2
    unset senha
    _pg_senha_morre "erro: psql recusou em '$banco' — senha nao trocada, segredo nao gravado" 1
  fi
  unset senha
  i=0
  for destino in "${destinos[@]}"; do
    chmod 600 "${PG_SENHA_TMPS[$i]}" && mv -f "${PG_SENHA_TMPS[$i]}" "$destino" \
      || _pg_senha_morre "erro: senha trocada em $banco mas o segredo nao foi gravado em $destino — rode de novo" 5
    i=$((i + 1))
  done
  trap 'rm -f "$PG_SENHA_ERRLOG"' EXIT
  printf '%s: role %s em %s com senha nova; segredo em segredos/%s (0600) — o valor nao se imprime%s\n' \
    "${PG_SENHA_VERBO:-seg segredo rotacionar}" "$role" "$banco" "$(IFS=,; echo "${alvos[*]}")" \
    "${PF_SUJEITO:+ (sujeito=$PF_SUJEITO)}"
}
