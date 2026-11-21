# terceiros.sh — artefato de terceiro pinado entra na árvore medida (arq:0116 §7; card #4417).
#
# Um construtor só para release e teste: `release promover` o chama sobre a árvore da rev
# antes de trocar current; `teste rodar` o chama sobre a árvore que vai medir (bancada,
# árvore do pre-push, árvore do gate). O teste acha o artefato como o código de produção
# o acha, pelo caminho relativo à árvore.
#
# Declaração nas fichas de dependência externa e ligações `depende-de` na Olaria
# (atributos `nome`, `familia`, `destino`, `pino` e `url`). Sem a Olaria acessível, sai 3
# antes de tocar a árvore ou current.
# Fonte do conteúdo: o cache <release>/terceiros/sha256/<pino> (semeável à mão em host sem
# rede); faltando, baixa da url. Conteúdo que não bate o pino é recusado. Árvore a-w (a da
# release) abre só os diretórios do caminho, põe o arquivo e fecha de novo.
#
# Uso: . "$(dirname "$(readlink -f "$0")")/../lib/terceiros.sh"
PF_VENV_PREFIXO="${PF_VENV_PREFIXO:-release}"
_TERCEIROS_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sha256_de() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }

# [ -w ] retorna verdadeiro sob uid 0 mesmo sem bit de escrita; checar os bits de modo via stat (DT-696)
_dir_gravavel() { (( (8#$(stat -c '%a' "$1") & 8#222) != 0 )); }

# $1=familia $2=arvore $3=cache (dir por sha256)
# (aceita 4 args legados: $1=familia $2=arvore $3=ignorado $4=cache)
# 0 ok (ou nada declarado), 3 Olaria/dependência ausente, 4 conteúdo fora do pino, 5 não pôs
materializar_terceiros_em() {
  local familia="$1" arvore="$2" cache_dir
  if [ "$#" -ge 4 ]; then
    cache_dir="$4"
  else
    cache_dir="$3"
  fi
  local pfx="$PF_VENV_PREFIXO"
  local py_bin="/opt/platafirma/current/venv/harness/bin/python"
  [ -x "$py_bin" ] || py_bin="python3"
  local linhas nome destino pino url alvo cache tmp curl
  if ! linhas="$("$py_bin" "$_TERCEIROS_LIB_DIR/terceiros_olaria.py" --familia "$familia")"; then
    printf '%s: dependência ausente: não leu as fichas de terceiros na Olaria — current intacto\n' "$pfx" >&2
    return 3
  fi
  [ -n "$linhas" ] || return 0
  while IFS=$'\t' read -r nome destino pino url; do
    [ -n "$nome" ] || continue
    if ! [[ "$nome" =~ ^[A-Za-z0-9._-]+$ ]] || [[ "$destino" == /* ]] || [[ "$destino" == *..* ]] || [ -z "$destino" ] \
       || ! [[ "$pino" =~ ^[0-9a-f]{64}$ ]] || { [ -n "$url" ] && [[ "$url" != https://* ]]; }; then
      printf '%s: erro: terceiro mal declarado nas fichas da Olaria: %s (%s)\n' "$pfx" "$nome" "$destino" >&2
      return 3
    fi
    alvo="$arvore/$destino"
    if [ -f "$alvo" ] && [ "$(sha256_de "$alvo")" = "$pino" ]; then
      printf 'terceiro:  %s já na árvore (sha256 %s)\n' "$nome" "${pino:0:12}"
      continue
    fi
    cache="$cache_dir/$pino"
    if [ ! -f "$cache" ] || [ "$(sha256_de "$cache")" != "$pino" ]; then
      curl="$(command -v curl 2>/dev/null || true)"
      if [ -z "$url" ] || [ -z "$curl" ]; then
        printf '%s: dependência ausente: terceiro %s fora do cache (%s) e sem %s para baixar — current intacto\n' \
          "$pfx" "$nome" "$cache" "$([ -z "$url" ] && echo url || echo curl)" >&2
        return 3
      fi
      mkdir -p "$cache_dir"
      tmp="$(mktemp "$cache_dir/.baixando.XXXXXX")"
      if ! "$curl" -fsSL --proto '=https' --max-time 600 -o "$tmp" "$url"; then
        rm -f "$tmp"
        printf '%s: dependência ausente: terceiro %s não baixou de %s — semeie %s e repita; current intacto\n' "$pfx" "$nome" "$url" "$cache" >&2
        return 3
      fi
      local obtido; obtido="$(sha256_de "$tmp")"
      if [ "$obtido" != "$pino" ]; then
        rm -f "$tmp"
        printf '%s: recusa: terceiro %s veio de %s com sha256 %s, pinado %s — current intacto\n' "$pfx" "$nome" "$url" "$obtido" "$pino" >&2
        return 4
      fi
      chmod 444 "$tmp"; mv -f "$tmp" "$cache"
      printf 'terceiro:  %s baixado para o cache (sha256 %s)\n' "$nome" "${pino:0:12}"
    fi
    local d="$arvore" parte abertos=() fechar=()
    local -a partes
    IFS='/' read -ra partes <<<"$(dirname "$destino")"
    # só fecha de novo o que estava fechado: bancada gravável continua gravável
    _dir_gravavel "$d" || { chmod u+w "$d"; fechar+=("$d"); }
    abertos+=("$d")
    for parte in "${partes[@]}"; do
      [ -n "$parte" ] && [ "$parte" != "." ] || continue
      d="$d/$parte"
      if [ -d "$d" ]; then
        _dir_gravavel "$d" || { chmod u+w "$d"; fechar+=("$d"); }
      else
        mkdir "$d"
        [ "${#fechar[@]}" -eq 0 ] || fechar+=("$d")
      fi
      abertos+=("$d")
    done
    rm -f "$alvo"
    if cp "$cache" "$alvo.tmp" && mv -f "$alvo.tmp" "$alvo"; then
      chmod 444 "$alvo"
    else
      rm -f "$alvo.tmp"
      for d in "${fechar[@]}"; do chmod a-w "$d" 2>/dev/null || true; done
      printf '%s: indeterminável: não consegui pôr o terceiro %s em %s\n' "$pfx" "$nome" "$alvo" >&2
      return 5
    fi
    for d in "${fechar[@]}"; do chmod a-w "$d"; done
    printf 'terceiro:  %s -> %s (sha256 %s)\n' "$nome" "$destino" "${pino:0:12}"
  done <<<"$linhas"
  return 0
}
