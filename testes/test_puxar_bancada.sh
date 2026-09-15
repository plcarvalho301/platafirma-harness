#!/usr/bin/env bash
# Testes de deploy-harness/puxar-bancada e de `repo abrir --da-producao` (card #3010): a bancada
# nasce no sha que a release serve, pelo repo DA RELEASE, nunca por reimplementacao.
#
# Hermetico: release falsa em tmp com duas familias (forge bare local, espelho .repo.git,
# checkout destacado por sha, current -> sha), instancia e HOME em tmp, bancada em tmp.
# Nenhuma rede, nenhum caminho de host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PUXAR="$REPO_ROOT/deploy-harness/puxar-bancada"

TMP_DIR="$(mktemp -d /tmp/platafirma-puxar-bancada.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

falha() { echo "FALHA: $*" >&2; exit 1; }
roda() { set +e; OUT="$("$@" 2>&1)"; RC=$?; set -e; }

RAIZ="$TMP_DIR/opt"; FORGE="$TMP_DIR/forge"; TRAB="$TMP_DIR/trabalho"; CASA="$TMP_DIR/home"
BANC="$TMP_DIR/bancada"
mkdir -p "$RAIZ" "$FORGE" "$TRAB" "$CASA" "$TMP_DIR/srv"
unset PLATAFIRMA_BANCADA PF_CADEIRA PLATAFIRMA_RELEASE PLATAFIRMA_ARQUIVO_BANCADA PLATAFIRMA_ARQUIVO_SHELLRC OPS_LOG_DIR PF_SESSAO
export HOME="$CASA" PF_RELEASE_RAIZ="$RAIZ" PLATAFIRMA_INSTANCIA="$TMP_DIR/srv"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t GIT_CONFIG_NOSYSTEM=1
ARQ_BANCADA="$CASA/.config/platafirma/bancada"
REPO_REL="$RAIZ/current/harness/bin/repo"

commita() {  # $1=clone $2=arquivo $3=conteudo ; imprime o sha
  printf '%s\n' "$3" > "$1/$2"
  git -C "$1" add -A && git -C "$1" commit -q -m "$2 $3"
  git -C "$1" rev-parse HEAD
}

# promove <familia> <sha>: espelho bare do forge, checkout destacado por sha, current -> sha
promove() {
  local fam="$1" sha="$2" esp="$RAIZ/$1/.repo.git"
  if [ ! -d "$esp" ]; then
    git clone -q --bare "$FORGE/$fam.git" "$esp"
  else
    git --git-dir="$esp" fetch -q "$FORGE/$fam.git" '+refs/heads/*:refs/heads/*'
  fi
  [ -d "$RAIZ/$fam/$sha" ] || git --git-dir="$esp" worktree add -q --detach "$RAIZ/$fam/$sha" "$sha" 2>/dev/null
  ln -sfn "$sha" "$RAIZ/$fam/current"
}

echo "=== puxar-bancada e repo abrir --da-producao ==="

# ---------------------------------------------------------------- fixture
for fam in platafirma-harness platafirma-alfa; do
  git init -q --bare -b main "$FORGE/$fam.git"
  git init -q -b main "$TRAB/$fam"
  git -C "$TRAB/$fam" remote add origin "$FORGE/$fam.git"
done
# o harness da release carrega o codigo sob teste: bin/repo e lib/raizes.sh desta arvore
H="$TRAB/platafirma-harness"
mkdir -p "$H/bin" "$H/lib" "$H/registro"
cp "$REPO_ROOT/bin/repo" "$H/bin/repo"; cp "$REPO_ROOT/lib/raizes.sh" "$H/lib/raizes.sh"
printf '{"platafirma-harness": "%s", "platafirma-alfa": "%s"}\n' "$FORGE/platafirma-harness.git" "$FORGE/platafirma-alfa.git" \
  > "$H/registro/familias.json"
C1="$(commita "$H" README.md v1)"; C2="$(commita "$H" README.md v2)"
git -C "$H" push -q origin main
A="$TRAB/platafirma-alfa"
A1="$(commita "$A" alfa.txt a1)"; A2="$(commita "$A" alfa.txt a2)"
git -C "$A" push -q origin main
git -C "$A" checkout -q -b lado "$A1"; AL="$(commita "$A" lado.txt fora-da-main)"
git -C "$A" push -q origin lado; git -C "$A" checkout -q main

promove platafirma-harness "$C1"; promove platafirma-alfa "$A1"
mkdir -p "$RAIZ/current" "$RAIZ/platafirma-nunca-promovida" "$RAIZ/venv"
ln -s ../platafirma-harness/current "$RAIZ/current/harness"
[ -x "$REPO_REL" ] || falha "fixture: repo da release ausente"
echo "OK: release falsa (harness @ ${C1:0:7}, main @ ${C2:0:7}; alfa @ ${A1:0:7}, main @ ${A2:0:7})"

# ---------------------------------------------------------------- 0. estatico
echo "--- 0: sintaxe, usage do repo < 1 KB, nenhuma referencia a pasta de trabalho da conta"
bash -n "$PUXAR" || falha "puxar-bancada nao passa bash -n"
bash -n "$REPO_ROOT/bin/repo" || falha "repo nao passa bash -n"
roda "$REPO_ROOT/bin/repo"
[ "$RC" -eq 2 ] || falha "repo sem argumento devia sair 2: $RC"
[ "$(printf '%s\n' "$OUT" | wc -c)" -lt 1024 ] || falha "usage do repo passou de 1 KB: $(printf '%s\n' "$OUT" | wc -c)"
grep -q -- "--da-producao" <<<"$OUT" || falha "usage do repo nao cita --da-producao"
roda "$PUXAR" --ajuda
[ "$RC" -eq 2 ] && grep -q -- "--declarar" <<<"$OUT" || falha "puxar-bancada --ajuda devia sair 2 com o uso: $RC $OUT"
padrao='(/home/[^/ ]+|\$HOME|\$\{HOME\}|~|%h)/A''I([/" ]|$)|home\(\) */ *"A''I"|-home-[a-z]+-A''I'
! grep -nE "$padrao" "$PUXAR" "$REPO_ROOT/bin/repo" "$0" || falha "referencia a pasta de trabalho da conta"
grep -q '"$PLATAFIRMA_RELEASE/harness/bin/repo"' "$PUXAR" || falha "puxar-bancada devia chamar o repo da release"
! grep -nE '^[^#]*(git|"\$GIT")[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?(clone|fetch|worktree)' "$PUXAR" \
  || falha "puxar-bancada reimplementa ato do repo"
# ont:0087: o ponto de entrada e platafirma; pf so aparece como o alias da conta
! grep -nE '(^|[^a-z_-])pf <verbo>|/usr/local/bin/pf([^a-z]|$)' "$PUXAR" || falha "puxar-bancada ainda cita pf como ponto de entrada"
grep -q -- "--alias" <<<"$OUT" || falha "puxar-bancada --ajuda nao cita --alias: $OUT"
echo "OK"

# ---------------------------------------------------------------- 1. sem declaracao
echo "--- 1: sem declaracao e sem --declarar sai 3 e nao cria nada"
roda "$PUXAR"
[ "$RC" -eq 3 ] || falha "sem bancada devia sair 3: $RC $OUT"
grep -q "bancada nao declarada" <<<"$OUT" || falha "causa ausente: $OUT"
[ ! -e "$CASA/.config" ] && [ ! -e "$BANC" ] || falha "criou config ou bancada sem declaracao"
roda "$PUXAR" --declarar relativa/bancada
[ "$RC" -eq 2 ] || falha "--declarar relativo devia sair 2: $RC $OUT"
[ ! -e "$ARQ_BANCADA" ] || falha "--declarar relativo gravou declaracao"
echo "OK"

# ---------------------------------------------------------------- 1a. --alias
echo "--- 1a: --alias grava pf -> platafirma no rc da conta: cria, conforme, nao duplica, preserva, recusa alheio"
RC_ARQ="$CASA/.bashrc"
[ ! -e "$RC_ARQ" ] || falha "fixture: rc da conta ja existe"
roda "$PUXAR" --alias --ensaio
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: criaria em $RC_ARQ (ensaio)" <<<"$OUT" && [ ! -e "$RC_ARQ" ] \
  || falha "ensaio do alias devia dizer criaria sem escrever: $RC $OUT"

# rc inexistente (default $HOME/.bashrc) e criado; alias sozinho nao declara nem puxa
roda "$PUXAR" --alias
[ "$RC" -eq 0 ] || falha "--alias devia sair 0: $RC $OUT"
grep -qx "alias pf -> platafirma: criado" <<<"$OUT" || falha "relato do alias criado: $OUT"
grep -q "proximo shell (ou: source $RC_ARQ)" <<<"$OUT" || falha "devia lembrar que vale no proximo shell: $OUT"
[ -f "$RC_ARQ" ] || falha "rc inexistente nao foi criado"
[ ! -e "$ARQ_BANCADA" ] && [ ! -e "$BANC" ] || falha "--alias sozinho declarou bancada ou puxou"
! grep -q "^verbos:\|bancada nao declarada" <<<"$OUT" || falha "--alias sozinho devia so gravar o alias e sair: $OUT"
[ "$(grep -cx '# >>> platafirma alias >>>' "$RC_ARQ")" = 1 ] && [ "$(grep -cx '# <<< platafirma alias <<<' "$RC_ARQ")" = 1 ] \
  || falha "marcadores do bloco: $(cat "$RC_ARQ")"
[ "$(bash --norc --noprofile -c 'shopt -s expand_aliases; . "$1"; alias pf' _ "$RC_ARQ")" = "alias pf='platafirma'" ] \
  || falha "o rc gravado nao define alias pf='platafirma'"

# segunda execucao: conforme, arquivo intocado, bloco unico
antes_rc="$(md5sum < "$RC_ARQ")"
roda "$PUXAR" --alias
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: conforme" <<<"$OUT" || falha "segunda execucao devia ser conforme: $RC $OUT"
[ "$(md5sum < "$RC_ARQ")" = "$antes_rc" ] || falha "conforme reescreveu o rc"
[ "$(grep -c "^alias pf=" "$RC_ARQ")" = 1 ] || falha "alias duplicado: $(cat "$RC_ARQ")"

# resto do arquivo preservado byte a byte, e o modo (com e sem newline final)
for caso in com sem; do
  rc2="$TMP_DIR/rc-$caso-newline"
  printf '# rc da conta\nexport X="a b"  # comentario\nalias ll='"'"'ls -l'"'"'\n# alias pf=outra-coisa (comentario nao conta)\n\tultima' > "$rc2"
  [ "$caso" = sem ] || printf '\n' >> "$rc2"
  chmod 640 "$rc2"; cp -p "$rc2" "$rc2.orig"
  roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc2" "$PUXAR" --alias
  [ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: criado" <<<"$OUT" || falha "rc $caso newline devia ser criado: $RC $OUT"
  tam="$(stat -c %s "$rc2.orig")"
  cmp -s <(head -c "$tam" "$rc2") "$rc2.orig" || falha "rc $caso newline: resto do arquivo nao preservado byte a byte"
  [ "$(stat -c %a "$rc2")" = 640 ] || falha "rc $caso newline: modo mudou para $(stat -c %a "$rc2")"
  depois="$(tail -c +"$((tam + 1))" "$rc2")"
  if [ "$caso" = sem ]; then esperado_ini=$'\n# >>> platafirma alias >>>'; else esperado_ini='# >>> platafirma alias >>>'; fi
  [ "${depois:0:${#esperado_ini}}" = "$esperado_ini" ] || falha "rc $caso newline: bloco nao vem logo depois do original: $(printf '%q' "$depois")"
  roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc2" "$PUXAR" --alias
  [ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: conforme" <<<"$OUT" || falha "rc $caso newline: segunda devia ser conforme: $RC $OUT"
done
! ls -A "$TMP_DIR" | grep -q '^\.platafirma-alias\.' || falha "temporario da escrita atomica ficou para tras"

# rc que e symlink: o alvo recebe o bloco, o link continua link
printf 'export Z=1\n' > "$TMP_DIR/rc-alvo"
ln -s "$TMP_DIR/rc-alvo" "$TMP_DIR/rc-link"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$TMP_DIR/rc-link" "$PUXAR" --alias
[ "$RC" -eq 0 ] && [ -L "$TMP_DIR/rc-link" ] && grep -qx "alias pf='platafirma'" "$TMP_DIR/rc-alvo" \
  || falha "rc symlink devia editar o alvo e manter o link: $RC $OUT"

# alias pf alheio (no meio de uma lista de alias) e funcao pf: recusa 4, diz a linha, nao edita
rc4="$TMP_DIR/rc-alheio"
printf '# um\nexport Y=1\nalias gs="git status" pf='"'"'git pull --ff-only'"'"'\n' > "$rc4"; chmod 600 "$rc4"
antes_rc="$(md5sum < "$rc4")"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc4" "$PUXAR" --alias
[ "$RC" -eq 4 ] || falha "alias pf alheio devia sair 4: $RC $OUT"
grep -q "^alias pf -> platafirma: recusado ($rc4:3 ja define pf com outro alvo: alias gs=\"git status\" pf='git pull --ff-only'" <<<"$OUT" \
  || falha "recusa devia dizer a linha: $OUT"
[ "$(md5sum < "$rc4")" = "$antes_rc" ] && [ "$(stat -c %a "$rc4")" = 600 ] || falha "recusa editou o rc"
rc5="$TMP_DIR/rc-funcao"
printf 'export W=1\n\npf() { git pull; }\n' > "$rc5"; antes_rc="$(md5sum < "$rc5")"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc5" "$PUXAR" --alias
[ "$RC" -eq 4 ] && grep -q "recusado ($rc5:3 ja define pf" <<<"$OUT" && [ "$(md5sum < "$rc5")" = "$antes_rc" ] \
  || falha "funcao pf devia sair 4 sem editar: $RC $OUT"

# verificacao adversarial: \alias, CRLF, ~/.bash_aliases, comando pf no PATH, rc somente leitura
rc6="$TMP_DIR/rc-barra"; printf '\\alias pf=ls\n' > "$rc6"; antes_rc="$(md5sum < "$rc6")"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc6" "$PUXAR" --alias
[ "$RC" -eq 4 ] && [ "$(md5sum < "$rc6")" = "$antes_rc" ] || falha "\\alias pf alheio devia sair 4 sem editar: $RC $OUT"
# CRLF: alias pf=platafirma\r define pf='platafirma\r' no bash; nao e conforme
rc7="$TMP_DIR/rc-crlf-pf"; printf 'export A=1\r\nalias pf=platafirma\r\n' > "$rc7"; antes_rc="$(md5sum < "$rc7")"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc7" "$PUXAR" --alias
[ "$RC" -eq 4 ] && grep -q "recusado ($rc7:2 ja define pf" <<<"$OUT" && [ "$(md5sum < "$rc7")" = "$antes_rc" ] \
  || falha "alias pf=platafirma com CRLF devia sair 4 sem editar: $RC $OUT"
rc8="$TMP_DIR/rc-crlf"; printf 'export A=1\r\nalias ll=ls\r\n' > "$rc8"; cp "$rc8" "$rc8.orig"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc8" "$PUXAR" --alias
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: criado" <<<"$OUT" \
  && cmp -s <(head -c "$(stat -c %s "$rc8.orig")" "$rc8") "$rc8.orig" \
  && [ "$(bash --norc --noprofile -c 'shopt -s expand_aliases; . "$1" 2>/dev/null; alias pf' _ "$rc8")" = "alias pf='platafirma'" ] \
  || falha "rc CRLF sem pf devia ganhar o bloco LF e preservar o resto: $RC $OUT"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc8" "$PUXAR" --alias
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: conforme" <<<"$OUT" || falha "rc CRLF: segunda devia ser conforme: $RC $OUT"
# ~/.bash_aliases com pf alheio: recusa 4 citando o arquivo; definicao igual la nao vira conforme
CASA2="$TMP_DIR/casa-aliases"; mkdir -p "$CASA2"; printf 'alias pf=ls\n' > "$CASA2/.bash_aliases"
roda env HOME="$CASA2" "$PUXAR" --alias
[ "$RC" -eq 4 ] && grep -q "recusado ($CASA2/.bash_aliases:1 ja define pf" <<<"$OUT" && [ ! -e "$CASA2/.bashrc" ] \
  || falha "pf alheio em ~/.bash_aliases devia sair 4 sem criar o rc: $RC $OUT"
printf "alias pf='platafirma'\n" > "$CASA2/.bash_aliases"
roda env HOME="$CASA2" "$PUXAR" --alias
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: criado" <<<"$OUT" || falha "pf igual so em ~/.bash_aliases devia gravar o bloco: $RC $OUT"
# comando pf alheio no PATH: 4; pf que e copia de platafirma no PATH nao e alheio
BINPF="$TMP_DIR/bin-pf"; mkdir -p "$BINPF"; printf '#!/bin/sh\necho outro\n' > "$BINPF/pf"; chmod 755 "$BINPF/pf"
roda env PATH="$BINPF:$PATH" PLATAFIRMA_ARQUIVO_SHELLRC="$TMP_DIR/rc-cmd" "$PUXAR" --alias
[ "$RC" -eq 4 ] && grep -q "recusado (comando pf alheio no PATH: $BINPF/pf" <<<"$OUT" && [ ! -e "$TMP_DIR/rc-cmd" ] \
  || falha "comando pf alheio no PATH devia sair 4 sem escrever: $RC $OUT"
printf '#!/bin/sh\necho entrada\n' > "$BINPF/platafirma"; cp "$BINPF/platafirma" "$BINPF/pf"; chmod 755 "$BINPF/platafirma" "$BINPF/pf"
roda env PATH="$BINPF:$PATH" PLATAFIRMA_ARQUIVO_SHELLRC="$TMP_DIR/rc-cmd" "$PUXAR" --alias
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: criado" <<<"$OUT" || falha "pf igual a platafirma no PATH nao e alheio: $RC $OUT"
# rc somente leitura: 3, sem editar (rename no diretorio contornaria o modo do arquivo)
rc9="$TMP_DIR/rc-somente-leitura"; printf 'export R=1\n' > "$rc9"; chmod 444 "$rc9"; antes_rc="$(md5sum < "$rc9")"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc9" "$PUXAR" --alias
[ "$RC" -eq 3 ] && grep -q "recusado (nao gravavel" <<<"$OUT" && [ "$(md5sum < "$rc9")" = "$antes_rc" ] && [ "$(stat -c %a "$rc9")" = 444 ] \
  || falha "rc somente leitura devia sair 3 sem editar: $RC $OUT"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc9" "$PUXAR" --alias --ensaio
[ "$RC" -eq 3 ] && [ "$(md5sum < "$rc9")" = "$antes_rc" ] || falha "ensaio sobre rc somente leitura devia antecipar o 3: $RC $OUT"
# sem python3: recusa 3 com relato, nao 127 calado
SEMPY="$TMP_DIR/bin-sem-python"; mkdir -p "$SEMPY"
for c in bash dirname readlink cat; do ln -sf "$(command -v "$c")" "$SEMPY/$c"; done
roda env PATH="$SEMPY" PLATAFIRMA_ARQUIVO_SHELLRC="$TMP_DIR/rc-sem-py" "$SEMPY/bash" "$PUXAR" --alias
[ "$RC" -eq 3 ] && grep -q "recusado (python3 ausente" <<<"$OUT" && [ ! -e "$TMP_DIR/rc-sem-py" ] \
  || falha "sem python3 devia sair 3 com relato: $RC $OUT"

# --alias sozinho com --cadeira: uso, e nada escrito
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$TMP_DIR/rc-nao-criar" "$PUXAR" --alias --cadeira ti
[ "$RC" -eq 2 ] && [ ! -e "$TMP_DIR/rc-nao-criar" ] || falha "--alias --cadeira sem familia devia sair 2 sem escrever: $RC $OUT"
echo "OK"

# ---------------------------------------------------------------- 2. ensaio
echo "--- 2: --ensaio --declarar mostra o plano e nao escreve nada"
roda env -u PLATAFIRMA_INSTANCIA "$PUXAR" --declarar "$BANC" --ensaio
[ "$RC" -eq 0 ] || falha "ensaio devia sair 0: $RC $OUT"
grep -qx "platafirma-alfa ${A1:0:7} criaria (ensaio) $BANC/wt/platafirma-alfa/fabrica" <<<"$OUT" || falha "plano do alfa: $OUT"
grep -qx "platafirma-harness ${C1:0:7} criaria (ensaio) $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" || falha "plano do harness: $OUT"
! grep -q "nunca-promovida\|venv" <<<"$OUT" || falha "diretorio sem current entrou no plano: $OUT"
grep -q "instancia real" <<<"$OUT" || falha "sem PLATAFIRMA_INSTANCIA de teste devia avisar instancia real: $OUT"
[ ! -e "$ARQ_BANCADA" ] && [ ! -e "$BANC" ] || falha "ensaio escreveu declaracao ou bancada"
echo "OK"

# ---------------------------------------------------------------- 3. declarar e criar
echo "--- 3: --declarar grava 0600 e cria worktrees no sha de producao, nao em origin/main"
roda "$PUXAR" --declarar "$BANC"
[ "$RC" -eq 0 ] || falha "primeira puxada devia sair 0: $RC $OUT"
[ "$(cat "$ARQ_BANCADA")" = "$BANC" ] || falha "declaracao gravada errada: $(cat "$ARQ_BANCADA")"
[ "$(stat -c %a "$ARQ_BANCADA")" = 600 ] || falha "declaracao devia ser 0600: $(stat -c %a "$ARQ_BANCADA")"
grep -qx "platafirma-harness ${C1:0:7} criado $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" || falha "linha do harness: $OUT"
grep -qx "platafirma-alfa ${A1:0:7} criado $BANC/wt/platafirma-alfa/fabrica" <<<"$OUT" || falha "linha do alfa: $OUT"
[ "$(git -C "$BANC/wt/platafirma-harness/fabrica" rev-parse HEAD)" = "$C1" ] || falha "worktree do harness fora do sha de producao"
[ "$(git -C "$BANC/wt/platafirma-alfa/fabrica" rev-parse HEAD)" = "$A1" ] || falha "worktree do alfa fora do sha de producao"
! git -C "$BANC/wt/platafirma-alfa/fabrica" symbolic-ref -q HEAD >/dev/null || falha "worktree sem card devia ser destacado"
grep -q "^verbos: platafirma <verbo> \[args\] em qualquer conta" <<<"$OUT" || falha "linha de como chamar verbo ausente: $OUT"
grep -q "^verbos: .*atalho pf na conta: puxar-bancada --alias$" <<<"$OUT" || falha "linha de verbos devia citar o atalho opcional: $OUT"
grep -q "^testar verbo editado: PLATAFIRMA_INSTANCIA=<tmp>" <<<"$OUT" || falha "linha de como testar verbo ausente: $OUT"
grep -q "^aviso: .*instancia real" <<<"$OUT" || falha "o aviso de instancia real e sobre o verbo da bancada e sai sempre: $OUT"
echo "OK"

# ---------------------------------------------------------------- 4. conforme
echo "--- 4: segunda execucao da conforme"
roda "$PUXAR"
[ "$RC" -eq 0 ] || falha "segunda puxada devia sair 0: $RC $OUT"
grep -qx "platafirma-harness ${C1:0:7} conforme $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" || falha "harness devia estar conforme: $OUT"
grep -qx "platafirma-alfa ${A1:0:7} conforme $BANC/wt/platafirma-alfa/fabrica" <<<"$OUT" || falha "alfa devia estar conforme: $OUT"
roda "$PUXAR" --declarar "$BANC/"
[ "$RC" -eq 0 ] && grep -q "^bancada conforme $BANC$" <<<"$OUT" || falha "--declarar da mesma bancada devia ser conforme: $RC $OUT"
# --alias junto de familia: grava o alias e puxa; recusa do alias sobe o exit sem impedir a puxada
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$TMP_DIR/rc-com-familia" "$PUXAR" platafirma-harness --alias
[ "$RC" -eq 0 ] && grep -qx "alias pf -> platafirma: criado" <<<"$OUT" \
  && grep -qx "platafirma-harness ${C1:0:7} conforme $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" \
  || falha "--alias com familia devia gravar e puxar: $RC $OUT"
roda env PLATAFIRMA_ARQUIVO_SHELLRC="$rc4" "$PUXAR" platafirma-harness --alias
[ "$RC" -eq 4 ] && grep -q "^alias pf -> platafirma: recusado" <<<"$OUT" \
  && grep -qx "platafirma-harness ${C1:0:7} conforme $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" \
  || falha "alias recusado com familia devia sair 4 e ainda relatar a familia: $RC $OUT"
echo "OK"

# ---------------------------------------------------------------- 5. outra bancada
echo "--- 5: --declarar com outra bancada ja declarada sai 4 sem sobrescrever"
roda "$PUXAR" --declarar "$TMP_DIR/outra"
[ "$RC" -eq 4 ] || falha "outra bancada devia sair 4: $RC $OUT"
[ "$(cat "$ARQ_BANCADA")" = "$BANC" ] || falha "declaracao sobrescrita"
[ ! -e "$TMP_DIR/outra" ] || falha "criou a outra bancada"
echo "OK"

# ---------------------------------------------------------------- 6. sujo
echo "--- 6: worktree sujo e relatado e nao tocado"
echo rascunho > "$BANC/wt/platafirma-alfa/fabrica/rascunho.txt"
roda "$PUXAR"
[ "$RC" -eq 4 ] || falha "worktree sujo devia sair 4: $RC $OUT"
grep -q "^platafirma-alfa ${A1:0:7} impossivel: worktree sujo ([^/]*) no sha de producao ${A1:0:7} — nao mexo $BANC/wt/platafirma-alfa/fabrica$" <<<"$OUT" || falha "sujo nao relatado: $OUT"
grep -qx "platafirma-harness ${C1:0:7} conforme $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" || falha "harness devia seguir conforme: $OUT"
[ "$(cat "$BANC/wt/platafirma-alfa/fabrica/rascunho.txt")" = rascunho ] || falha "rascunho tocado"
echo "OK"

# ---------------------------------------------------------------- 7. ensaio nao cria
echo "--- 7: --ensaio com bancada declarada nao cria nada"
antes="$(find "$BANC" | sort | md5sum)"
roda "$PUXAR" --cadeira ti --ensaio
grep -qx "platafirma-harness ${C1:0:7} criaria (ensaio) $BANC/wt/platafirma-harness/ti" <<<"$OUT" || falha "plano da cadeira ti: $OUT"
roda "$PUXAR" --ensaio
grep -q "^platafirma-alfa ${A1:0:7} impossivel: worktree sujo, nao mexeria (ensaio)" <<<"$OUT" || falha "ensaio devia ver o sujo: $OUT"
[ "$(find "$BANC" | sort | md5sum)" = "$antes" ] || falha "ensaio mudou a bancada"
echo "OK"

# ---------------------------------------------------------------- 8. familia inexistente
echo "--- 8: familia inexistente reportada"
roda "$PUXAR" platafirma-nada
[ "$RC" -eq 1 ] || falha "familia fora da release devia sair 1: $RC $OUT"
grep -q "^platafirma-nada - impossivel: release $RAIZ (familia platafirma-nada sem current) $BANC/wt/platafirma-nada/fabrica$" <<<"$OUT" \
  || falha "familia inexistente mal relatada: $OUT"
[ ! -e "$BANC/platafirma-nada" ] && [ ! -e "$BANC/wt/platafirma-nada" ] || falha "familia inexistente criou algo"
roda "$PUXAR" ../fora
[ "$RC" -eq 2 ] || falha "familia com caminho devia sair 2: $RC"
echo "OK"

# ---------------------------------------------------------------- 9. card e slug
echo "--- 9: --card/--slug abre ramo fabrica/<card>-<slug> no sha de producao"
roda "$PUXAR" platafirma-harness --cadeira ti --card 77 --slug fita
[ "$RC" -eq 0 ] || falha "card devia sair 0: $RC $OUT"
wt="$BANC/wt/platafirma-harness/ti"
[ "$(git -C "$wt" symbolic-ref --short HEAD)" = fabrica/77-fita ] || falha "ramo errado: $(git -C "$wt" symbolic-ref --short HEAD 2>&1)"
[ "$(git -C "$wt" rev-parse HEAD)" = "$C1" ] || falha "ramo fora do sha de producao"
roda "$PUXAR" --slug x
[ "$RC" -eq 2 ] || falha "--slug sem --card devia sair 2: $RC"
echo "OK"

# ---------------------------------------------------------------- 10. repo da release ausente
echo "--- 10: sem repo da release sai 3 (nunca cai para o repo da bancada)"
roda env PLATAFIRMA_RELEASE="$TMP_DIR/sem-release" "$PUXAR"
[ "$RC" -eq 3 ] && grep -q "repo da release" <<<"$OUT" || falha "sem release devia sair 3: $RC $OUT"
echo "OK"

# ---------------------------------------------------------------- 11. repo abrir --da-producao
echo "--- 11: repo abrir --da-producao: recusas, busca no forge e o abrir antigo intacto"
export PLATAFIRMA_BANCADA="$BANC"

roda "$REPO_REL" abrir platafirma-sumida --da-producao --cadeira ti
[ "$RC" -eq 1 ] && grep -q "^varrido: " <<<"$OUT" && grep -q "^vizinho: " <<<"$OUT" \
  || falha "familia fora da release devia sair 1 com varrido/vizinho: $RC $OUT"

mkdir -p "$RAIZ/platafirma-pendurada"; ln -s 0123456789abcdef0123456789abcdef01234567 "$RAIZ/platafirma-pendurada/current"
roda "$REPO_REL" abrir platafirma-pendurada --da-producao --cadeira ti
[ "$RC" -eq 5 ] && grep -q "pendurado" <<<"$OUT" || falha "current pendurado devia sair 5: $RC $OUT"

mkdir -p "$RAIZ/platafirma-portag/v1"; ln -s v1 "$RAIZ/platafirma-portag/current"
roda "$REPO_REL" abrir platafirma-portag --da-producao --cadeira ti
[ "$RC" -eq 5 ] && grep -q "fora da forma de servido" <<<"$OUT" || falha "current por tag devia sair 5: $RC $OUT"
roda "$PUXAR" platafirma-portag --ensaio
grep -q "^platafirma-portag - impossivel: current fora da forma de servido (ensaio)" <<<"$OUT" || falha "ensaio por tag: $OUT"

promove platafirma-alfa "$AL"
roda "$REPO_REL" abrir platafirma-alfa --da-producao --cadeira dados
[ "$RC" -eq 4 ] && grep -q "nao descende de origin/main" <<<"$OUT" || falha "sha fora de origin/main devia sair 4: $RC $OUT"
[ ! -e "$BANC/wt/platafirma-alfa/dados" ] || falha "recusa de ancestralidade criou worktree"

A3="$(commita "$A" alfa.txt a3)"; git -C "$A" push -q origin main
! git -C "$BANC/platafirma-alfa" cat-file -e "$A3^{commit}" 2>/dev/null || falha "fixture: A3 ja estava no clone base"
promove platafirma-alfa "$A3"
roda "$REPO_REL" abrir platafirma-alfa --da-producao --cadeira dados
[ "$RC" -eq 0 ] || falha "sha que falta no clone base devia vir do forge: $RC $OUT"
[ "$(git -C "$BANC/wt/platafirma-alfa/dados" rev-parse HEAD)" = "$A3" ] || falha "worktree dados fora de A3"

roda "$PUXAR" platafirma-alfa
[ "$RC" -eq 4 ] || falha "worktree em outro sha devia sair 4: $RC $OUT"
grep -q "^platafirma-alfa ${A3:0:7} impossivel: worktree ja aberto em ${A1:0:7}" <<<"$OUT" || falha "outro sha mal relatado: $OUT"
[ "$(git -C "$BANC/wt/platafirma-alfa/fabrica" rev-parse HEAD)" = "$A1" ] || falha "worktree em outro sha foi mexido"
[ -f "$BANC/wt/platafirma-alfa/fabrica/rascunho.txt" ] || falha "rascunho sumiu"

git -C "$BANC/platafirma-harness" branch -q fabrica/88-velho "$C2"
roda "$REPO_REL" abrir platafirma-harness 88 --slug velho --da-producao --cadeira seg
[ "$RC" -eq 4 ] && grep -q "ja existe em ${C2:0:7}" <<<"$OUT" || falha "ramo existente em outro sha devia sair 4: $RC $OUT"

roda "$REPO_REL" abrir platafirma-harness --cadeira velho
[ "$RC" -eq 0 ] || falha "abrir sem --da-producao: $RC $OUT"
[ "$(git -C "$BANC/wt/platafirma-harness/velho" rev-parse HEAD)" = "$C2" ] || falha "abrir sem --da-producao devia seguir nascendo em origin/main"

roda "$REPO_REL" abrir platafirma-harness 5 --slug 'a~b' --da-producao --cadeira z
[ "$RC" -eq 2 ] && [ ! -e "$BANC/wt/platafirma-harness/z" ] || falha "slug invalido com --da-producao devia sair 2 sem criar: $RC $OUT"
echo "OK"

# ---------------------------------------------------------------- 12. declaracao que nao se sobrescreve
echo "--- 12: --declarar recusa raiz, espaco, release/instancia e arquivo que existe sem declarar"
unset PLATAFIRMA_BANCADA
mv "$ARQ_BANCADA" "$TMP_DIR/declaracao.guardada"
for ruim in / "$(printf '/tmp/x\ny')" "/tmp/com espaco" /tmp/a/../b; do
  roda "$PUXAR" --declarar "$ruim" --ensaio
  [ "$RC" -eq 2 ] || falha "--declarar '$ruim' devia sair 2: $RC $OUT"
done
roda "$PUXAR" --declarar "$RAIZ/bancada"
[ "$RC" -eq 4 ] || falha "bancada dentro da release devia sair 4: $RC $OUT"
roda "$PUXAR" --declarar /srv/qualquer --ensaio
[ "$RC" -eq 4 ] || falha "bancada em /srv devia sair 4: $RC $OUT"
[ ! -e "$ARQ_BANCADA" ] || falha "recusa gravou declaracao"
mkdir "$ARQ_BANCADA"
roda "$PUXAR" --declarar "$BANC"
[ "$RC" -eq 5 ] && [ -z "$(ls -A "$ARQ_BANCADA")" ] || falha "arquivo de declaracao que e diretorio devia sair 5 sem gravar dentro: $RC $OUT"
rmdir "$ARQ_BANCADA"
printf '%s\n' "$TMP_DIR/de-outro" > "$ARQ_BANCADA"; chmod 000 "$ARQ_BANCADA"
roda "$PUXAR" --declarar "$BANC"
chmod 600 "$ARQ_BANCADA"
[ "$RC" -eq 5 ] && [ "$(cat "$ARQ_BANCADA")" = "$TMP_DIR/de-outro" ] || falha "declaracao ilegivel devia sair 5 sem sobrescrever: $RC $OUT"
printf '\n%s\n' "$TMP_DIR/de-outro" > "$ARQ_BANCADA"
roda "$PUXAR" --declarar "$BANC"
[ "$RC" -eq 5 ] && [ "$(sed -n 2p "$ARQ_BANCADA")" = "$TMP_DIR/de-outro" ] || falha "primeira linha vazia devia sair 5 sem sobrescrever: $RC $OUT"
rm -f "$ARQ_BANCADA"
roda env PLATAFIRMA_BANCADA="$TMP_DIR/outra" "$PUXAR" --declarar "$BANC" --ensaio
[ "$RC" -eq 4 ] && [ ! -e "$ARQ_BANCADA" ] || falha "PLATAFIRMA_BANCADA diferente de --declarar devia sair 4: $RC $OUT"
roda env PLATAFIRMA_BANCADA="$BANC" "$PUXAR" platafirma-harness --declarar "$BANC"
[ "$RC" -eq 0 ] && [ "$(cat "$ARQ_BANCADA")" = "$BANC" ] || falha "PLATAFIRMA_BANCADA igual e sem arquivo devia gravar a declaracao: $RC $OUT"
rm -f "$TMP_DIR/declaracao.guardada"
echo "OK"

# ---------------------------------------------------------------- 13. worktree conforme em outro ramo, apagado, ilegivel
echo "--- 13: card sobre worktree destacado sai 4; wt apagado com registro refaz; indice corrompido sai 5"
roda "$PUXAR" platafirma-harness --card 99 --slug outro
[ "$RC" -eq 4 ] && grep -q "nao em fabrica/99-outro" <<<"$OUT" || falha "card sobre worktree destacado devia sair 4: $RC $OUT"
! git -C "$BANC/wt/platafirma-harness/fabrica" symbolic-ref -q HEAD >/dev/null || falha "worktree destacado ganhou ramo"
roda "$PUXAR" platafirma-harness --card 99 --slug outro --ensaio
[ "$RC" -eq 4 ] && grep -q "nao em fabrica/99-outro, nao mexeria (ensaio)" <<<"$OUT" || falha "ensaio devia ver o ramo divergente: $RC $OUT"
rm -rf "$BANC/wt/platafirma-harness/fabrica"
roda "$PUXAR" platafirma-harness
grep -qx "platafirma-harness ${C1:0:7} criado $BANC/wt/platafirma-harness/fabrica" <<<"$OUT" || falha "wt apagado com o registro de pe devia ser refeito: $RC $OUT"
idx="$(git -C "$BANC/wt/platafirma-harness/fabrica" rev-parse --path-format=absolute --git-path index)"
echo lixo > "$idx"
roda "$PUXAR" platafirma-harness
[ "$RC" -eq 5 ] && grep -q "git status falhou" <<<"$OUT" || falha "indice corrompido nao e limpo, devia sair 5: $RC $OUT"
mkdir -p "$RAIZ/platafirma-diretorio/current"
roda "$PUXAR" platafirma-diretorio --ensaio
[ "$RC" -eq 5 ] || falha "ensaio com current diretorio devia sair 5 como a execucao: $RC $OUT"
echo "OK"

# ---------------------------------------------------------------- 14. repo de dentro da bancada
echo "--- 14: PLATAFIRMA_RELEASE apontado para a bancada sai 4 e o repo de la nao roda"
mkdir -p "$BANC/falsa/harness/bin"
printf '#!/bin/sh\ntouch "%s"\n' "$TMP_DIR/repo-da-bancada-rodou" > "$BANC/falsa/harness/bin/repo"
chmod +x "$BANC/falsa/harness/bin/repo"
roda env PLATAFIRMA_RELEASE="$BANC/falsa" "$PUXAR" platafirma-harness
[ "$RC" -eq 4 ] && [ ! -e "$TMP_DIR/repo-da-bancada-rodou" ] || falha "repo dentro da bancada devia ser recusado: $RC $OUT"
echo "OK"

echo "=== puxar-bancada e repo abrir --da-producao: todos os casos passaram ==="
