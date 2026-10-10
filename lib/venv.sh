# venv.sh — construtor de venv por lock+python, um só para release e teste (card #3150).
#
# Extraído de bin/release (resolver_uv, python_gerenciado, resolver_python,
# construir_venv), sem mudar uma linha de comportamento: release continua se
# comportando exatamente como antes (PF_VENV_PREFIXO default "release" preserva as
# mensagens). teste (e, depois, hooks/pre-push) passam a reaproveitar o MESMO
# construtor em vez de ter escada própria (trava do card: "não trocar o construtor
# de venv por outro").
#
# Uso: . "$(dirname "$(readlink -f "$0")")/../lib/venv.sh"
PF_VENV_PREFIXO="${PF_VENV_PREFIXO:-release}"

# uv por ordem explícita: override, dois caminhos de sistema, PATH. A porta e o
# wrapper não carregam ~/.local/bin, e quem constrói venv não pode depender do
# PATH de quem chama.
resolver_uv() {  # imprime o caminho do uv; 3 ausente
  local c
  if [ -n "${PLATAFIRMA_UV:-}" ]; then
    if [[ "$PLATAFIRMA_UV" == /* ]] && [ -x "$PLATAFIRMA_UV" ] && [ ! -d "$PLATAFIRMA_UV" ]; then printf '%s' "$PLATAFIRMA_UV"; return 0; fi
    printf '%s: dependência ausente: PLATAFIRMA_UV=%s não é binário executável em caminho absoluto (override do uv)\n' "$PF_VENV_PREFIXO" "$PLATAFIRMA_UV" >&2
    return 3
  fi
  for c in /usr/local/bin/uv /usr/bin/uv; do
    if [ -x "$c" ] && [ ! -d "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  c="$(command -v uv 2>/dev/null || true)"
  if [ -n "$c" ] && [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
  {
    printf '%s: dependência ausente: uv (constrói venv do lock) — procurado em $PLATAFIRMA_UV, /usr/local/bin/uv, /usr/bin/uv e no PATH\n' "$PF_VENV_PREFIXO"
    printf '         instale uv de sistema, fora do home da conta: sudo install -m 0755 -o root -g root <binário uv> /usr/local/bin/uv\n'
    printf '         (ou: curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh), ou aponte PLATAFIRMA_UV\n'
  } >&2
  return 3
}

# 0 quando o caminho está sob o HOME da conta ou numa árvore de python gerenciado pelo uv
python_gerenciado() {  # $1=caminho
  local p="$1" casa="${HOME:-}"
  casa="${casa%/}"
  if [ -n "$casa" ] && { [ "$p" = "$casa" ] || [[ "$p" == "$casa"/* ]]; }; then return 0; fi
  case "$p" in */uv/python/*) return 0 ;; esac
  return 1
}

# python de sistema dos venvs. Imprime "<caminho>\t<caminho real>\t<major.minor>"; 3 ausente.
resolver_python() {
  local py="${PLATAFIRMA_PYTHON:-/usr/bin/python3.12}" real ver
  if [[ "$py" != /* ]] || [ ! -x "$py" ] || [ -d "$py" ]; then
    printf '%s: dependência ausente: python de sistema %s não existe ou não é executável (caminho absoluto) — venv de produção não se liga a python gerenciado no home da conta; instale python3.12 do sistema ou aponte PLATAFIRMA_PYTHON\n' "$PF_VENV_PREFIXO" "$py" >&2
    return 3
  fi
  real="$(readlink -f "$py")"
  # override também não liga venv de produção ao home da conta nem a python gerenciado pelo uv
  if python_gerenciado "$py" || python_gerenciado "$real"; then
    printf '%s: dependência ausente: python %s (real %s) está no home da conta ou é gerenciado pelo uv — venv de produção só se liga a python de sistema; aponte PLATAFIRMA_PYTHON para um python do sistema\n' "$PF_VENV_PREFIXO" "$py" "$real" >&2
    return 3
  fi
  ver="$("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null </dev/null)" || ver=""
  if ! [[ "$ver" =~ ^[0-9]+\.[0-9]+$ ]]; then
    printf '%s: dependência ausente: python de sistema %s não roda (não disse a versão)\n' "$PF_VENV_PREFIXO" "$py" >&2
    return 3
  fi
  printf '%s\t%s\t%s' "$py" "$real" "$ver"
}

# --- ambiente node (card #3386) ----------------------------------------------------
# Mesma regra do venv: o lock mora no git (package-lock.json), o ambiente é construído uma
# vez, por chave <nome>-<hash>, e fica só leitura. A instalação NUNCA roda script de pacote
# (npm ci --ignore-scripts): é o que fecha o vetor de verme de cadeia de suprimento, e é
# o mesmo comando que a platafirma-ui já usa no build. Config de usuário e global do npm
# não entram (userconfig/globalconfig em /dev/null), nem registro trocado por variável:
# o que se instala é o que o lock resolveu.

# node de sistema, fora do home da conta (como o python de sistema): override, dois caminhos
# de sistema, PATH. Imprime "<node>\t<versão>"; 3 ausente.
resolver_node() {
  local n="" c ver real
  if [ -n "${PLATAFIRMA_NODE:-}" ]; then
    if [[ "$PLATAFIRMA_NODE" == /* ]] && [ -x "$PLATAFIRMA_NODE" ] && [ ! -d "$PLATAFIRMA_NODE" ]; then
      n="$PLATAFIRMA_NODE"
    else
      printf '%s: dependência ausente: PLATAFIRMA_NODE=%s não é binário executável em caminho absoluto (override do node)\n' "$PF_VENV_PREFIXO" "$PLATAFIRMA_NODE" >&2
      return 3
    fi
  else
    for c in /usr/local/bin/node /usr/bin/node; do
      if [ -x "$c" ] && [ ! -d "$c" ]; then n="$c"; break; fi
    done
    if [ -z "$n" ]; then
      c="$(command -v node 2>/dev/null || true)"
      if [ -n "$c" ] && [ -x "$c" ]; then n="$c"; fi
    fi
  fi
  if [ -z "$n" ]; then
    {
      printf '%s: dependência ausente: node (constrói o ambiente de front do lock) — procurado em $PLATAFIRMA_NODE, /usr/local/bin/node, /usr/bin/node e no PATH\n' "$PF_VENV_PREFIXO"
      printf '         instale node de sistema, fora do home da conta, ou aponte PLATAFIRMA_NODE\n'
    } >&2
    return 3
  fi
  real="$(readlink -f "$n")"
  if python_gerenciado "$n" || python_gerenciado "$real"; then
    printf '%s: dependência ausente: node %s (real %s) está no home da conta — ambiente de front só se liga a node de sistema; aponte PLATAFIRMA_NODE para um node do sistema\n' "$PF_VENV_PREFIXO" "$n" "$real" >&2
    return 3
  fi
  ver="$("$n" --version 2>/dev/null </dev/null)" || ver=""
  if ! [[ "$ver" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
    printf '%s: dependência ausente: node %s não roda (não disse a versão)\n' "$PF_VENV_PREFIXO" "$n" >&2
    return 3
  fi
  printf '%s\t%s' "$n" "$ver"
}

# npm que acompanha o node $1 (mesmo diretório); senão o do PATH. Imprime o caminho; 3 ausente.
resolver_npm() {  # $1=node
  local d c
  d="$(dirname "$1")"
  if [ -x "$d/npm" ] && [ ! -d "$d/npm" ]; then printf '%s' "$d/npm"; return 0; fi
  c="$(command -v npm 2>/dev/null || true)"
  if [ -n "$c" ] && [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
  printf '%s: dependência ausente: npm (ao lado de %s e no PATH)\n' "$PF_VENV_PREFIXO" "$1" >&2
  return 3
}

# Chromium para a prova de navegador: o MESMO do Playwright que o Crawl4AI do harness usa
# (spec pesquisa-web §3.2: um navegador só, não dois). Override, depois o cache do Playwright,
# depois um chromium de sistema. Imprime o caminho; 3 ausente.
resolver_chromium() {
  local c base
  if [ -n "${PLATAFIRMA_CHROMIUM:-}" ]; then
    if [[ "$PLATAFIRMA_CHROMIUM" == /* ]] && [ -x "$PLATAFIRMA_CHROMIUM" ] && [ ! -d "$PLATAFIRMA_CHROMIUM" ]; then
      printf '%s' "$PLATAFIRMA_CHROMIUM"; return 0
    fi
    printf '%s: dependência ausente: PLATAFIRMA_CHROMIUM=%s não é binário executável em caminho absoluto\n' "$PF_VENV_PREFIXO" "$PLATAFIRMA_CHROMIUM" >&2
    return 3
  fi
  for base in "${PLAYWRIGHT_BROWSERS_PATH:-}" "${HOME:-}/.cache/ms-playwright"; do
    [ -n "$base" ] && [ -d "$base" ] || continue
    c="$(compgen -G "$base/chromium-*/chrome-linux*/chrome" 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "$c" ] && [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  for c in chromium chromium-browser google-chrome; do
    c="$(command -v "$c" 2>/dev/null || true)"
    if [ -n "$c" ] && [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  printf '%s: dependência ausente: chromium (procurado em $PLATAFIRMA_CHROMIUM, no cache do Playwright e no PATH)\n' "$PF_VENV_PREFIXO" >&2
  return 3
}

# Chave do ambiente: para lock Python é a fórmula de sempre (o hash dos venvs já construídos
# não muda); lock node soma a identidade do node, porque o binário de plataforma que o npm
# baixa depende dele. $1=lock $2=python real $3=python major.minor. Imprime 12 hex; 3 sem node.
hash_do_ambiente() {
  local lock="$1" node_id=""
  if [ "$(basename "$lock")" = package-lock.json ]; then
    node_id="$(resolver_node)" || return 3
    node_id="${node_id#*$'\t'}"
  fi
  { cat "$lock"; printf '\npython=%s %s\n' "$2" "$3"; [ -z "$node_id" ] || printf 'node=%s\n' "$node_id"; } | sha256sum | cut -c1-12
}

# Constrói o ambiente node $2 do package-lock.json $1 (package.json ao lado). 0 ok, 3 falhou.
construir_node() {  # $1=lock $2=destino
  local lock="$1" dest="$2" dir nodeinfo node npm cache rc=0
  dir="$(dirname "$lock")"
  if [ ! -f "$dir/package.json" ]; then
    printf '%s: falha alta: não há package.json ao lado de %s\n' "$PF_VENV_PREFIXO" "$lock" >&2
    return 3
  fi
  nodeinfo="$(resolver_node)" || return 3
  node="${nodeinfo%%$'\t'*}"
  npm="$(resolver_npm "$node")" || return 3
  mkdir -p "$dest" || return 3
  cp "$dir/package.json" "$lock" "$dest/" || return 3
  cache="$(mktemp -d "${TMPDIR:-/tmp}/npm-cache.XXXXXX")" || return 3
  ( cd "$dest" && env -u NODE_OPTIONS -u npm_config_registry -u NPM_CONFIG_REGISTRY \
      PATH="$(dirname "$node"):$PATH" \
      npm_config_userconfig=/dev/null npm_config_globalconfig=/dev/null \
      npm_config_ignore_scripts=true npm_config_audit=false npm_config_fund=false \
      npm_config_update_notifier=false npm_config_cache="$cache" \
      "$npm" ci --ignore-scripts --no-audit --no-fund </dev/null >&2 ) || rc=$?
  rm -rf "$cache"
  if [ "$rc" -ne 0 ] || [ ! -d "$dest/node_modules" ]; then
    printf '%s: falha alta: npm ci --ignore-scripts saiu %s construindo do lock %s com o node de sistema %s — lock fora de sincronia com o package.json, registro ou rede\n' \
      "$PF_VENV_PREFIXO" "$rc" "$lock" "$node" >&2
    return 3
  fi
}

# Constrói $2 (destino) a partir do lock $1, com o uv $3 e o python $4 (versão $5).
# uv.lock -> uv sync --frozen (projeto em modo biblioteca, sem instalar o próprio
# pacote); qualquer outro nome -> uv venv + pip install -r. Falha alta (3) se o uv
# sair != 0, ou se o venv resultante não ficar ligado ao python de sistema pedido
# (confere pyvenv.cfg: home tem de ser o dirname do python pedido, nunca gerenciado).
construir_venv() {  # $1=lock $2=destino $3=uv $4=python $5=versão do python
  local lock="$1" dest="$2" uv="$3" py="$4" ver="$5" rc=0 req home
  # only-system: o uv não escolhe python gerenciado; never: não baixa um quando o de
  # sistema não serve. Variáveis de quem chama que brigam com isso saem.
  local -a uvenv=(env -u UV_MANAGED_PYTHON -u UV_NO_MANAGED_PYTHON -u UV_PYTHON -u UV_SYSTEM_PYTHON
    -u VIRTUAL_ENV UV_PYTHON_PREFERENCE=only-system UV_PYTHON_DOWNLOADS=never)
  case "$(basename "$lock")" in
    uv.lock)
      "${uvenv[@]}" UV_PROJECT_ENVIRONMENT="$dest" "$uv" sync -q --frozen --no-dev --no-install-project \
        --python "$py" --project "$(dirname "$lock")" </dev/null >&2 || rc=$? ;;
    package-lock.json)
      # ambiente node (card #3386): npm ci --ignore-scripts; a mensagem de falha é do próprio construtor
      construir_node "$lock" "$dest" || return 3
      return 0 ;;
    *)
      "${uvenv[@]}" "$uv" venv -q --python "$py" "$dest" </dev/null >&2 || rc=$?
      if [ "$rc" -eq 0 ] && grep -qvE '^[[:space:]]*(#|$)' "$lock"; then
        "${uvenv[@]}" "$uv" pip install -q --python "$dest/bin/python" -r "$lock" </dev/null >&2 || rc=$?
      fi ;;
  esac
  if [ "$rc" -ne 0 ]; then
    req="$(sed -n 's/^requires-python[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$lock" 2>/dev/null | head -n 1)"
    printf '%s: falha alta: uv saiu %s construindo do lock %s com o python de sistema %s (%s)%s — lock que exige outra versão não se contorna com python gerenciado; ajuste o requires-python/.python-version da família ou aponte PLATAFIRMA_PYTHON\n' \
      "$PF_VENV_PREFIXO" "$rc" "$lock" "$py" "$ver" "${req:+; o lock pede requires-python $req}" >&2
    return 3
  fi
  # confere a ligação: o venv tem de apontar para o python pedido, não para outro que o uv achou
  home="$(sed -n 's/^home[[:space:]]*=[[:space:]]*//p' "$dest/pyvenv.cfg" 2>/dev/null | head -n 1)"
  if [ -z "$home" ] || python_gerenciado "$home" \
    || { [ "$home" != "$(dirname "$py")" ] && [ "$home" != "$(dirname "$(readlink -f "$py")")" ]; }; then
    printf '%s: falha alta: venv %s ficou ligado a %s, não ao python de sistema %s\n' "$PF_VENV_PREFIXO" "$dest" "${home:-(sem pyvenv.cfg)}" "$py" >&2
    return 3
  fi
}

# --- veredito memoizado por (hash da árvore, chave, hash do ambiente) -------------
# Convencão COMPARTILHADA entre hooks/pre-push e o gate de `release promover`
# (card #3150): quem mediu primeiro grava, o outro reaproveita sem rodar de novo.
# Nunca hash de commit (o squash muda o commit e mantém a árvore).
caminho_veredito() {  # $1=vereditos_dir $2=arvore_hash $3=chave $4=chave_hash
  printf '%s/%s-%s-%s.json' "$1" "$2" "$3" "$4"
}

ler_veredito() {  # $1=arquivo ; imprime verde|vermelho ; vazio = nao medido/ilegivel
  [ -f "$1" ] || return 0
  sed -n 's/.*"resultado"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$1" 2>/dev/null | head -n 1
}

gravar_veredito() {  # $1=arquivo $2=verde|vermelho $3=rev
  local arq="$1" resultado="$2" rev="$3" tmp
  tmp="$(mktemp "$(dirname "$arq")/.tmp.XXXXXX" 2>/dev/null)" || return 0
  printf '{"resultado": "%s", "rev": "%s", "quando": "%s"}\n' \
    "$resultado" "$rev" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$tmp" 2>/dev/null && mv -f "$tmp" "$arq" 2>/dev/null
}

# controle/tests/VERDES da árvore em $1 (raiz do checkout) — caminhos que existem, um por linha.
listar_verdes() {  # $1=raiz
  local raiz="$1" lista="$1/controle/tests/VERDES" linha
  [ -r "$lista" ] || return 0
  while IFS= read -r linha; do
    case "$linha" in ''|'#'*) continue ;; esac
    linha="${linha%%|*}"; linha="${linha%"${linha##*[![:space:]]}"}"   # raio depois de `|` (card #3370)
    [ -f "$raiz/controle/$linha" ] && printf '%s\n' "$linha"
  done < "$lista"
}

# O avesso de listar_verdes: o que VERDES lista e nao existe na arvore. Lista que aponta
# arquivo sumido e baseline que ninguem mede -- o gate barra (5), o pre-push avisa.
verdes_ausentes() {  # $1=raiz
  local raiz="$1" lista="$1/controle/tests/VERDES" linha
  [ -r "$lista" ] || return 0
  while IFS= read -r linha; do
    case "$linha" in ''|'#'*) continue ;; esac
    linha="${linha%%|*}"; linha="${linha%"${linha##*[![:space:]]}"}"   # raio depois de `|` (card #3370)
    [ -f "$raiz/controle/$linha" ] || printf '%s\n' "$linha"
  done < "$lista"
}

# Reprovados nomeados pelo junit.xml (classe::teste + 1a linha da asserção), até 5.
# Compartilhado (hooks/pre-push e o gate de release) para nunca dependerem de
# `tail -n N`, que corta no meio de traceback e não nomeia o teste.
nomear_reprovados() {  # $1=junit.xml
  local xml="$1"
  [ -f "$xml" ] || { printf '(sem junit.xml para nomear os reprovados)\n'; return; }
  python3 - "$xml" <<'PY' 2>/dev/null
import sys
import xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
except Exception:
    sys.exit(0)
n = 0
for tc in root.iter("testcase"):
    ruim = tc.find("failure")
    if ruim is None:
        ruim = tc.find("error")
    if ruim is None:
        continue
    n += 1
    if n > 5:
        print("... e mais reprovados (saída inteira aponta o resto)")
        break
    nome = "%s::%s" % (tc.get("classname", ""), tc.get("name", ""))
    msg = (ruim.get("message") or "").splitlines()[0] if ruim.get("message") else ""
    print("%s — %s" % (nome, msg))
PY
}
