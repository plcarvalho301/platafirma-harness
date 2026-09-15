#!/usr/bin/env bash
# Frente harness-release-uv-porta (card #3010):
#   1. release acha o uv por ordem declarada ($PLATAFIRMA_UV, /usr/local/bin/uv, /usr/bin/uv,
#      command -v uv); nenhum -> exit 3 dizendo como instalar uv de sistema;
#   2. venv de produção se liga ao python de sistema ($PLATAFIRMA_PYTHON, default
#      /usr/bin/python3.12) com UV_PYTHON_PREFERENCE=only-system; ausente ou lock incompatível ->
#      exit 3, current intacto; a identidade do python entra no hash do venv;
#   3. infra (e o release ao chamá-lo) define XDG_RUNTIME_DIR e DBUS_SESSION_BUS_ADDRESS quando
#      ausentes, e o restart do ops-mcp segue destacado por systemd-run --user.
#
# Hermético: release e instância num tmp, HOME num tmp, forge local, uv/python/systemctl/
# systemd-run/docker falsos num PATH temporário. A parte 5 usa o uv real só se houver um no PATH
# de quem roda o teste, com cache e HOME no tmp e sem rede.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/release"
INFRA="$REPO_ROOT/bin/infra"
UV_REAL="$(command -v uv 2>/dev/null || true)"
UID_ATUAL="$(id -u)"

TMP_DIR="$(mktemp -d /tmp/pf-uv-porta.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

falha() { echo "FALHA: $*" >&2; exit 1; }
pulado() { echo "PULADO: $*"; }
command -v jq >/dev/null || falha "jq ausente (dependencia declarada do release)"

PROD_RAIZ="$TMP_DIR/opt"; INSTANCIA="$TMP_DIR/srv"; FORGE="$TMP_DIR/forge"; CLONES="$TMP_DIR/clones"
STUBS="$TMP_DIR/stubs"; UVDIR="$TMP_DIR/uvfalso"; CASA="$TMP_DIR/home"
mkdir -p "$PROD_RAIZ" "$INSTANCIA" "$FORGE" "$CLONES" "$STUBS" "$UVDIR" "$CASA" \
  "$TMP_DIR/py312" "$TMP_DIR/py313" "$TMP_DIR/py314"
unset PLATAFIRMA_BANCADA PLATAFIRMA_RELEASE PF_ABERTURA_DIR PLATAFIRMA_TERCEIROS PLATAFIRMA_VENVS \
  PLATAFIRMA_UV PLATAFIRMA_PYTHON XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS \
  UV_PYTHON UV_PYTHON_PREFERENCE UV_PYTHON_DOWNLOADS UV_PROJECT_ENVIRONMENT VIRTUAL_ENV
export HOME="$CASA" PF_RELEASE_RAIZ="$PROD_RAIZ" PLATAFIRMA_INSTANCIA="$INSTANCIA" \
  PLATAFIRMA_ARQUIVO_BANCADA="$TMP_DIR/sem-bancada" PF_RELEASE_PORTA=0
export UV_LOG="$TMP_DIR/uv.log" SYSD_LOG="$TMP_DIR/systemd.log"
: > "$UV_LOG"; : > "$SYSD_LOG"
PATH_BASE="$STUBS:/usr/bin:/bin"
export PATH="$PATH_BASE"

echo "=== release: uv por ordem, python de sistema, restart da porta com bus ==="

# ---------------------------------------------------------------- binários falsos
cat > "$STUBS/acervo" <<'EOF'
#!/usr/bin/env bash
echo '[]'
EOF
printf '#!/usr/bin/env bash\nexit 0\n' > "$STUBS/deploy"
# systemctl falso: sem XDG_RUNTIME_DIR (ou com FAKE_SEM_BUS) não há bus, como o real
cat > "$STUBS/systemctl" <<'EOF'
#!/usr/bin/env bash
printf 'systemctl %s | XDG=%s | DBUS=%s\n' "$*" "${XDG_RUNTIME_DIR:-}" "${DBUS_SESSION_BUS_ADDRESS:-}" >> "${SYSD_LOG:?}"
if [ -z "${XDG_RUNTIME_DIR:-}" ] || [ -n "${FAKE_SEM_BUS:-}" ]; then
  echo "Failed to connect to bus: No medium found" >&2; exit 1
fi
if [ "${2:-}" = cat ]; then [ "${4:-}" = ops-mcp ] || exit 1; fi
exit 0
EOF
cat > "$STUBS/systemd-run" <<'EOF'
#!/usr/bin/env bash
printf 'systemd-run %s | XDG=%s | DBUS=%s\n' "$*" "${XDG_RUNTIME_DIR:-}" "${DBUS_SESSION_BUS_ADDRESS:-}" >> "${SYSD_LOG:?}"
exit 0
EOF
printf '#!/usr/bin/env bash\nexit 0\n' > "$STUBS/docker"
# o infra do PATH é o infra desta árvore: release -> infra -> systemd-run falso, ponta a ponta
ln -s "$INFRA" "$STUBS/infra"

# uv falso: grava chamada e ambiente; cria o venv com pyvenv.cfg apontando para o --python pedido
cat > "$UVDIR/uv" <<'EOF'
#!/usr/bin/env bash
printf '%s | %s | PREF=%s | DL=%s\n' "$0" "$*" "${UV_PYTHON_PREFERENCE:-}" "${UV_PYTHON_DOWNLOADS:-}" >> "${UV_LOG:?}"
# como o uv 0.12.1 real: UV_MANAGED_PYTHON junto de preferencia explicita sai 2
if [ -n "${UV_MANAGED_PYTHON:-}" ] && [ -n "${UV_PYTHON_PREFERENCE:-}" ]; then
  echo "error: the argument \`UV_MANAGED_PYTHON\` (environment variable) cannot be used with \`--python-preference\`" >&2; exit 2
fi
sub="$1"; shift
py=""; dest=""
while [ $# -gt 0 ]; do
  case "$1" in
    --python) py="$2"; shift 2 ;;
    --project|-r) shift 2 ;;
    -*) shift ;;
    *) dest="$1"; shift ;;
  esac
done
mk() { mkdir -p "$1/bin"; : > "$1/bin/python"; printf 'home = %s\nversion_info = falso\n' "${FAKE_UV_HOME:-$(dirname "$py")}" > "$1/pyvenv.cfg"; }
case "$sub" in
  venv) [ -n "$py" ] || { echo "uv falso: venv sem --python" >&2; exit 9; }; mk "$dest" ;;
  sync) [ -n "$py" ] || { echo "uv falso: sync sem --python" >&2; exit 9; }
        if [ -n "${FAKE_UV_INCOMPATIVEL:-}" ]; then
          # deixa venv pela metade, como o uv real que cria o diretorio antes de resolver
          mkdir -p "${UV_PROJECT_ENVIRONMENT:?}/lib"
          echo "error: The requested interpreter resolved to Python 3.12, which is incompatible with the project's Python requirement: >=3.14" >&2
          exit 2
        fi
        mk "${UV_PROJECT_ENVIRONMENT:?}" ;;
  *) exit 0 ;;
esac
EOF
for v in 12 13 14; do printf '#!/bin/sh\necho 3.%s\n' "$v" > "$TMP_DIR/py3$v/python3.$v"; done
chmod +x "$STUBS"/acervo "$STUBS"/deploy "$STUBS"/systemctl "$STUBS"/systemd-run "$STUBS"/docker \
  "$UVDIR/uv" "$TMP_DIR"/py3*/python3.*
UV_FALSO="$UVDIR/uv"; PY312="$TMP_DIR/py312/python3.12"; PY313="$TMP_DIR/py313/python3.13"; PY314="$TMP_DIR/py314/python3.14"

# ---------------------------------------------------------------- forge
mk_repo() {  # $1=nome ; um commit inicial, preparado por $2 (função) se dado
  local nome="$1" prep="${2:-}" wt="$CLONES/$1" bare="$FORGE/$1.git"
  git init -q --bare "$bare"; mkdir -p "$wt"; git -C "$wt" init -q -b main
  git -C "$wt" config user.name t; git -C "$wt" config user.email t@t
  echo v0 > "$wt/README.md"
  [ -z "$prep" ] || "$prep" "$wt"
  git -C "$wt" add .; git -C "$wt" commit -q -m c0
  git -C "$wt" remote add origin "$bare"; git -C "$wt" push -q origin main
}
novo_commit() {  # $1=repo $2=marca ; imprime o sha
  local wt="$CLONES/$1"
  echo "$2" > "$wt/README.md"; git -C "$wt" commit -q -am "$2"; git -C "$wt" push -q origin main
  git -C "$wt" rev-parse HEAD
}
prep_locks() {
  mkdir -p "$1/req" "$1/proj"
  echo 'pacote==1.0' > "$1/req/requirements.txt"
  printf '[project]\nname = "proj"\nversion = "0"\nrequires-python = ">=3.14"\n' > "$1/proj/pyproject.toml"
  printf 'version = 1\nrequires-python = ">=3.14"\n' > "$1/proj/uv.lock"
}
mk_repo platafirma-arquitetura prep_locks
mk_repo platafirma-harness

printf '{"platafirma-arquitetura": "%s", "platafirma-harness": "%s", "platafirma-motor": "%s"}\n' \
  "$FORGE/platafirma-arquitetura.git" "$FORGE/platafirma-harness.git" "$FORGE/platafirma-motor.git" > "$TMP_DIR/familias.json"
cat > "$TMP_DIR/venvs.json" <<'EOF'
{"_leia": "fixture",
 "req":  {"familia": "platafirma-arquitetura", "lock": "req/requirements.txt"},
 "proj": {"familia": "platafirma-arquitetura", "lock": "proj/uv.lock"},
 "real": {"familia": "platafirma-motor", "lock": "rag/uv.lock"},
 "realreq": {"familia": "platafirma-motor", "lock": "rag/requirements.txt"}}
EOF
echo '{"_leia": "fixture sem terceiro"}' > "$TMP_DIR/terceiros.json"
export PLATAFIRMA_FAMILIAS="$TMP_DIR/familias.json" PLATAFIRMA_VENVS="$TMP_DIR/venvs.json" PLATAFIRMA_TERCEIROS="$TMP_DIR/terceiros.json"

promover() {  # $@=args ; enche out e rc
  set +e; out="$("$VERBO" promover "$@" 2>&1)"; rc=$?; set -e
}
current_de() { readlink "$PROD_RAIZ/$1/current" 2>/dev/null || true; }
UV_SISTEMA=""
for c in /usr/local/bin/uv /usr/bin/uv; do [ -x "$c" ] && { UV_SISTEMA="$c"; break; }; done
FAM=platafirma-arquitetura

# ---------------------------------------------------------------- 1. uv
echo "--- 1: ordem do uv declarada no cabecalho e seguida no codigo"
head -n 40 "$VERBO" | grep -qF '$PLATAFIRMA_UV, /usr/local/bin/uv, /usr/bin/uv, `command -v uv`' \
  || falha "cabecalho do release nao declara a ordem do uv"
grep -q 'for c in /usr/local/bin/uv /usr/bin/uv; do' "$VERBO" || falha "codigo nao segue a ordem de sistema declarada"
echo OK

echo "--- 1a: nenhum uv (sem override, sem uv de sistema, PATH sem uv) sai 3 dizendo como instalar"
S1="$(novo_commit $FAM s1)"
if [ -n "$UV_SISTEMA" ]; then
  pulado "uv de sistema presente em $UV_SISTEMA; o caso 'nenhum uv' nao se monta neste host"
else
  : > "$UV_LOG"
  PLATAFIRMA_PYTHON="$PY312" promover $FAM "$S1"
  [ "$rc" -eq 3 ] || falha "sem uv devia sair 3: rc=$rc $out"
  grep -q 'dependência ausente: uv' <<<"$out" && grep -q '/usr/local/bin/uv' <<<"$out" \
    && grep -q 'instale uv de sistema' <<<"$out" || falha "mensagem sem ordem nem instalacao: $out"
  [ -z "$(current_de $FAM)" ] || falha "current nasceu sem uv"
  echo OK
fi

echo "--- 1b: PLATAFIRMA_UV que nao executa (ou relativo) sai 3, sem cair para o uv do PATH"
# o uv falso esta no PATH: cair para ele construiria e daria 0
ln -sfn "$UVDIR/uv" "$TMP_DIR/uv"
for o in "$TMP_DIR/nao-existe/uv" uv; do
  : > "$UV_LOG"
  (cd "$TMP_DIR" && PATH="$UVDIR:$PATH_BASE" PLATAFIRMA_UV="$o" PLATAFIRMA_PYTHON="$PY312" "$VERBO" promover $FAM "$S1") >"$TMP_DIR/1b.out" 2>&1 && rc=0 || rc=$?
  out="$(cat "$TMP_DIR/1b.out")"
  [ "$rc" -eq 3 ] && grep -q "PLATAFIRMA_UV=$o " <<<"$out" || falha "override '$o' devia sair 3: rc=$rc $out"
  [ ! -s "$UV_LOG" ] || falha "override '$o' quebrado caiu para outro uv: $(cat "$UV_LOG")"
  [ -z "$(current_de $FAM)" ] || falha "current nasceu com override '$o'"
done
rm -f "$TMP_DIR/uv"
echo OK

echo "--- 1c: sem override e sem uv de sistema, o uv do PATH e usado"
if [ -n "$UV_SISTEMA" ]; then
  pulado "uv de sistema presente em $UV_SISTEMA vence o PATH, como declarado"
else
  : > "$UV_LOG"
  PATH="$UVDIR:$PATH_BASE" PLATAFIRMA_PYTHON="$PY312" promover $FAM "$S1"
  [ "$rc" -eq 0 ] || falha "uv no PATH devia construir: rc=$rc $out"
  [ -s "$UV_LOG" ] && ! grep -qv "^$UV_FALSO " "$UV_LOG" || falha "uv chamado nao foi o do PATH: $(cat "$UV_LOG")"
  [ "$(current_de $FAM)" = "$S1" ] || falha "current nao trocou com uv do PATH"
  echo OK
fi

# ---------------------------------------------------------------- 2. python de sistema
echo "--- 2a: python de sistema ausente (ou relativo) sai 3 com o motivo, antes de chamar uv"
S2="$(novo_commit $FAM s2)"
for p in "$TMP_DIR/sem-python/python3.12" python3.12; do
  : > "$UV_LOG"
  PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$p" promover $FAM "$S2"
  [ "$rc" -eq 3 ] && grep -q "python de sistema $p" <<<"$out" || falha "python '$p' devia sair 3: rc=$rc $out"
  [ ! -s "$UV_LOG" ] || falha "uv chamado sem python de sistema: $(cat "$UV_LOG")"
  [ "$(current_de $FAM)" != "$S2" ] || falha "current trocou sem python de sistema"
done
echo OK

echo "--- 2b: override de uv e python: venv e sync pedem o python de sistema, only-system, sem download"
: > "$UV_LOG"
PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$PY313" promover $FAM "$S2"
[ "$rc" -eq 0 ] || falha "promover com override devia dar 0: rc=$rc $out"
grep -q "^$UV_FALSO | venv -q --python $PY313 " "$UV_LOG" || falha "uv venv sem --python de sistema: $(cat "$UV_LOG")"
grep -q "^$UV_FALSO | sync .*--python $PY313 " "$UV_LOG" || falha "uv sync sem --python de sistema: $(cat "$UV_LOG")"
grep -q "^$UV_FALSO | pip install " "$UV_LOG" || falha "requirements nao instalado: $(cat "$UV_LOG")"
! grep -v 'PREF=only-system | DL=never$' "$UV_LOG" | grep -q . || falha "chamada de uv sem only-system/never: $(cat "$UV_LOG")"
[ "$(current_de $FAM)" = "$S2" ] || falha "current nao trocou"
for n in req proj; do
  v="$(readlink -f "$PROD_RAIZ/current/venv/$n")"
  [ "$(sed -n 's/^home = //p' "$v/pyvenv.cfg")" = "$TMP_DIR/py313" ] || falha "venv $n nao ligado ao python pedido"
  [ -f "$v/.pronto" ] || falha "venv $n sem .pronto"
done
[ -z "${UV_PYTHON_PREFERENCE:-}" ] || falha "UV_PYTHON_PREFERENCE vazou para o shell do teste"
echo OK

echo "--- 2c: mesma rev de lock e mesmo python reaproveitam; outro python constroi ao lado"
antes_req="$(readlink "$PROD_RAIZ/current/venv/req")"
S3="$(novo_commit $FAM s3)"
: > "$UV_LOG"
PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$PY313" promover $FAM "$S3"
[ "$rc" -eq 0 ] && grep -q 'já construído (lock e python inalterados)' <<<"$out" || falha "reuso: rc=$rc $out"
[ ! -s "$UV_LOG" ] || falha "reuso chamou uv"
S4="$(novo_commit $FAM s4)"
PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$PY314" promover $FAM "$S4"
[ "$rc" -eq 0 ] || falha "outro python: rc=$rc $out"
depois_req="$(readlink "$PROD_RAIZ/current/venv/req")"
[ "$antes_req" != "$depois_req" ] || falha "venv com outro python reaproveitou o nome: $depois_req"
[ -d "$PROD_RAIZ/venv/${antes_req##*/}" ] || falha "venv anterior sumiu do disco"
echo OK

echo "--- 2d: lock que exige versao incompativel falha alta, current intacto, venv pela metade apagado"
S5="$(novo_commit $FAM s5)"
# python 3.12 em caminho proprio: o hash do venv inclui o caminho real do python, e o PY312 ja
# construiu em 1c (quando nao pulado) — reaproveitar esconderia a falha que este caso mede
for n in d e; do
  mkdir -p "$TMP_DIR/py312$n"; printf '#!/bin/sh\necho 3.12\n' > "$TMP_DIR/py312$n/python3.12"
  chmod +x "$TMP_DIR/py312$n/python3.12"
done
PY312D="$TMP_DIR/py312d/python3.12"; PY312E="$TMP_DIR/py312e/python3.12"
FAKE_UV_INCOMPATIVEL=1 PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$PY312D" promover $FAM "$S5"
[ "$rc" -eq 3 ] || falha "lock incompativel devia sair 3: rc=$rc $out"
grep -q 'falha alta' <<<"$out" && grep -q 'requires-python >=3.14' <<<"$out" || falha "falha sem motivo: $out"
[ "$(current_de $FAM)" = "$S4" ] || falha "current mudou com lock incompativel"
grep -q "^$UV_FALSO | sync " "$UV_LOG" || falha "2d nao chegou ao uv sync (o caso nao mediu nada): $out"
! ls -d "$PROD_RAIZ"/venv/proj-* 2>/dev/null | while read -r d; do [ -f "$d/.pronto" ] || echo "$d"; done | grep -q . \
  || falha "venv pela metade ficou no disco: $(ls -d "$PROD_RAIZ"/venv/proj-*)"
echo OK

echo "--- 2e: venv que o uv ligou a outro python e recusado"
FAKE_UV_HOME="$CASA/.local/share/uv/python/cpython-3.14/bin" PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$PY312E" promover $FAM "$S5"
[ "$rc" -eq 3 ] && grep -q 'ficou ligado a' <<<"$out" || falha "ligacao errada devia sair 3: rc=$rc $out"
[ "$(current_de $FAM)" = "$S4" ] || falha "current mudou com venv mal ligado"
echo OK

echo "--- 2g: python sob o HOME da conta ou gerenciado pelo uv e recusado, override incluido, sem chamar uv"
mkdir -p "$CASA/bin" "$TMP_DIR/gerido/uv/python/cpython-3.12/bin" "$TMP_DIR/venv-no-home"
ln -sfn "$PY312" "$CASA/bin/python3.12"                                  # caminho no home, real fora
printf '#!/bin/sh\necho 3.12\n' > "$TMP_DIR/gerido/uv/python/cpython-3.12/bin/python3.12"
chmod +x "$TMP_DIR/gerido/uv/python/cpython-3.12/bin/python3.12"
ln -sfn "$TMP_DIR/gerido/uv/python/cpython-3.12/bin/python3.12" "$TMP_DIR/venv-no-home/python"  # caminho fora, real gerido
for p in "$CASA/bin/python3.12" "$TMP_DIR/gerido/uv/python/cpython-3.12/bin/python3.12" "$TMP_DIR/venv-no-home/python"; do
  : > "$UV_LOG"
  PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$p" promover $FAM "$S5"
  [ "$rc" -eq 3 ] && grep -q 'home da conta ou é gerenciado pelo uv' <<<"$out" || falha "python '$p' devia ser recusado: rc=$rc $out"
  [ ! -s "$UV_LOG" ] || falha "uv chamado com python recusado '$p': $(cat "$UV_LOG")"
  [ "$(current_de $FAM)" = "$S4" ] || falha "current mudou com python '$p'"
done
echo OK

echo "--- 2h: UV_MANAGED_PYTHON/UV_PYTHON de quem chama nao chegam ao uv (o real sairia 2)"
mkdir -p "$TMP_DIR/py312h"; printf '#!/bin/sh\necho 3.12\n' > "$TMP_DIR/py312h/python3.12"; chmod +x "$TMP_DIR/py312h/python3.12"
: > "$UV_LOG"
UV_MANAGED_PYTHON=1 UV_PYTHON=3.14 VIRTUAL_ENV="$CASA/.venv" PLATAFIRMA_UV="$UV_FALSO" PLATAFIRMA_PYTHON="$TMP_DIR/py312h/python3.12" promover $FAM "$S5"
[ "$rc" -eq 0 ] || falha "ambiente de uv herdado derrubou a construcao: rc=$rc $out"
grep -q "^$UV_FALSO | sync .*--python $TMP_DIR/py312h/python3.12 " "$UV_LOG" || falha "2h nao construiu com o python pedido: $(cat "$UV_LOG")"
[ "$(current_de $FAM)" = "$S5" ] || falha "current nao trocou em 2h"
echo OK

echo "--- 2f: sem PLATAFIRMA_PYTHON o default e /usr/bin/python3.12"
S6="$(novo_commit $FAM s6)"
: > "$UV_LOG"
PLATAFIRMA_UV="$UV_FALSO" promover $FAM "$S6"
if [ -x /usr/bin/python3.12 ]; then
  [ "$rc" -eq 0 ] || falha "default python: rc=$rc $out"
  grep -q -- "--python /usr/bin/python3.12 " "$UV_LOG" || falha "default nao foi /usr/bin/python3.12: $(cat "$UV_LOG")"
else
  [ "$rc" -eq 3 ] && grep -q 'python de sistema /usr/bin/python3.12' <<<"$out" || falha "sem python3.12 de sistema devia sair 3: rc=$rc $out"
fi
echo OK

# ---------------------------------------------------------------- 3. infra e bus
echo "--- 3a: infra restart ops-mcp sem XDG_RUNTIME_DIR define o bus e despacha destacado"
: > "$SYSD_LOG"
set +e; out="$(env -u XDG_RUNTIME_DIR -u DBUS_SESSION_BUS_ADDRESS bash "$INFRA" restart ops-mcp 2>&1)"; rc=$?; set -e
[ "$rc" -eq 0 ] && grep -q 'despachado destacado' <<<"$out" || falha "infra restart: rc=$rc $out"
grep -qF "systemd-run --user --collect --quiet --unit=infra-restart-" "$SYSD_LOG" || falha "restart nao foi por systemd-run: $(cat "$SYSD_LOG")"
grep -F "systemd-run " "$SYSD_LOG" | grep -qF "systemctl --user restart ops-mcp | XDG=/run/user/$UID_ATUAL | DBUS=unix:path=/run/user/$UID_ATUAL/bus" \
  || falha "systemd-run sem o bus da conta: $(cat "$SYSD_LOG")"
! grep -q '^systemctl --user restart' "$SYSD_LOG" || falha "restart sincrono: a chamada nao voltaria antes da queda"
echo OK

echo "--- 3b: XDG_RUNTIME_DIR e DBUS ja dados vencem"
: > "$SYSD_LOG"
XDG_RUNTIME_DIR="$TMP_DIR/xdg" DBUS_SESSION_BUS_ADDRESS="unix:path=$TMP_DIR/outro-bus" bash "$INFRA" restart ops-mcp >/dev/null 2>&1 \
  || falha "infra restart com bus dado"
grep -F "systemd-run " "$SYSD_LOG" | grep -qF "XDG=$TMP_DIR/xdg | DBUS=unix:path=$TMP_DIR/outro-bus" || falha "valor dado foi sobrescrito: $(cat "$SYSD_LOG")"
echo OK

echo "--- 3c: sem bus nenhum o infra diz a causa e sai 3, sem despachar"
: > "$SYSD_LOG"
set +e; out="$(FAKE_SEM_BUS=1 bash "$INFRA" restart ops-mcp 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q 'sem bus do systemd --user' <<<"$out" || falha "sem bus: rc=$rc $out"
! grep -q '^systemd-run' "$SYSD_LOG" || falha "despachou sem bus"
echo OK

echo "--- 3e: com bus, alvo que nao e conteiner nem unit segue saindo 2 (comportamento anterior)"
: > "$SYSD_LOG"
set +e; out="$(env -u XDG_RUNTIME_DIR bash "$INFRA" restart nao-existe 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q 'não é contêiner conhecido' <<<"$out" || falha "alvo desconhecido com bus: rc=$rc $out"
! grep -q '^systemd-run' "$SYSD_LOG" || falha "despachou alvo desconhecido"
echo OK

echo "--- 3f: XDG_RUNTIME_DIR herdado de outra conta e trocado pelo desta; DBUS dentro dele sai junto"
if [ "$UID_ATUAL" -eq 0 ] || [ -O /usr ]; then
  pulado "rodando como dono de /usr; nao ha diretorio de outra conta para simular"
else
  : > "$SYSD_LOG"
  XDG_RUNTIME_DIR=/usr DBUS_SESSION_BUS_ADDRESS="unix:path=/usr/bus" bash "$INFRA" restart ops-mcp >/dev/null 2>&1 \
    || falha "infra restart com XDG de outra conta"
  grep -F "systemd-run " "$SYSD_LOG" | grep -qF "XDG=/run/user/$UID_ATUAL | DBUS=unix:path=/run/user/$UID_ATUAL/bus" \
    || falha "XDG de outra conta nao foi trocado: $(cat "$SYSD_LOG")"
  : > "$SYSD_LOG"
  XDG_RUNTIME_DIR=/usr DBUS_SESSION_BUS_ADDRESS="unix:path=$TMP_DIR/meu-bus" bash "$INFRA" restart ops-mcp >/dev/null 2>&1 \
    || falha "infra restart com XDG de outra conta e DBUS proprio"
  grep -F "systemd-run " "$SYSD_LOG" | grep -qF "XDG=/run/user/$UID_ATUAL | DBUS=unix:path=$TMP_DIR/meu-bus" \
    || falha "DBUS fora do XDG estranho devia ser mantido: $(cat "$SYSD_LOG")"
  echo OK
fi

echo "--- 3d: release promover do harness, sem XDG_RUNTIME_DIR, reinicia a porta pelo infra com bus"
H1="$(novo_commit platafirma-harness h1)"
: > "$SYSD_LOG"
set +e; out="$(env -u XDG_RUNTIME_DIR -u DBUS_SESSION_BUS_ADDRESS PF_RELEASE_PORTA=1 "$VERBO" promover platafirma-harness "$H1" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 0 ] || falha "promover harness: rc=$rc $out"
grep -q '^porta: .*despachado destacado' <<<"$out" || falha "release nao relatou o restart despachado: $out"
grep -F "systemd-run " "$SYSD_LOG" | grep -qF "systemctl --user restart ops-mcp | XDG=/run/user/$UID_ATUAL | DBUS=unix:path=/run/user/$UID_ATUAL/bus" \
  || falha "release -> infra sem bus: $(cat "$SYSD_LOG")"
echo OK

echo "--- 3g: release com XDG_RUNTIME_DIR de outra conta passa ao infra o bus desta (infra de release velha)"
if [ "$UID_ATUAL" -eq 0 ] || [ -O /usr ]; then
  pulado "rodando como dono de /usr; nao ha diretorio de outra conta para simular"
else
  # infra velho: repassa o ambiente sem corrigir, para medir so o que o release entrega
  mkdir -p "$TMP_DIR/infra-velho"
  printf '#!/usr/bin/env bash\nexec systemd-run --user --collect --quiet --unit=infra-restart-$$ systemctl --user restart "$2"\n' > "$TMP_DIR/infra-velho/infra"
  chmod +x "$TMP_DIR/infra-velho/infra"
  H2="$(novo_commit platafirma-harness h2)"
  : > "$SYSD_LOG"
  set +e; out="$(env -u DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR=/usr PATH="$TMP_DIR/infra-velho:$PATH_BASE" PF_RELEASE_PORTA=1 "$VERBO" promover platafirma-harness "$H2" 2>&1)"; rc=$?; set -e
  [ "$rc" -eq 0 ] || falha "promover harness com XDG estranho: rc=$rc $out"
  grep -F "systemd-run " "$SYSD_LOG" | grep -qF "XDG=/run/user/$UID_ATUAL | DBUS=unix:path=/run/user/$UID_ATUAL/bus" \
    || falha "release passou XDG de outra conta ao infra: $(cat "$SYSD_LOG")"
  echo OK
fi

# ---------------------------------------------------------------- 4. uv real (opcional)
echo "--- 4: uv real, python de sistema, .python-version pedindo 3.14 e sem rede"
if [ -z "$UV_REAL" ] || [ ! -x /usr/bin/python3.12 ]; then
  pulado "sem uv no PATH de quem roda o teste ou sem /usr/bin/python3.12"
else
  export UV_CACHE_DIR="$TMP_DIR/uv-cache" UV_OFFLINE=1
  prep_real() {
    mkdir -p "$1/rag"
    printf '[project]\nname = "fixture"\nversion = "0"\nrequires-python = ">=3.12"\ndependencies = []\n' > "$1/rag/pyproject.toml"
    echo 3.14 > "$1/rag/.python-version"
    echo '# sem dependencia: exercita uv venv --python sem rede' > "$1/rag/requirements.txt"
    UV_PYTHON_PREFERENCE=only-system UV_PYTHON_DOWNLOADS=never "$UV_REAL" lock -q --project "$1/rag" --python /usr/bin/python3.12
  }
  if ! (mkdir -p "$TMP_DIR/sonda" && prep_real "$TMP_DIR/sonda") >/dev/null 2>&1; then
    pulado "uv real nao gerou lock offline de projeto sem dependencia"
  else
    mk_repo platafirma-motor prep_real
    M1="$(git -C "$CLONES/platafirma-motor" rev-parse HEAD)"
    PLATAFIRMA_UV="$UV_REAL" promover platafirma-motor "$M1"
    [ "$rc" -eq 0 ] || falha "uv real: rc=$rc $out"
    v="$(readlink -f "$PROD_RAIZ/current/venv/real")"
    [ "$(sed -n 's/^home = //p' "$v/pyvenv.cfg")" = /usr/bin ] || falha "uv real ligou o venv fora de /usr/bin: $(cat "$v/pyvenv.cfg")"
    [ "$("$v/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" = 3.12 ] || falha "venv real nao roda 3.12"
    v="$(readlink -f "$PROD_RAIZ/current/venv/realreq")"
    [ "$(sed -n 's/^home = //p' "$v/pyvenv.cfg")" = /usr/bin ] || falha "uv venv real (requirements) fora de /usr/bin: $(cat "$v/pyvenv.cfg")"
    [ "$("$v/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" = 3.12 ] || falha "venv real (requirements) nao roda 3.12"
    echo "OK (uv real)"
    wt="$CLONES/platafirma-motor"
    sed -i 's/>=3.12/>=3.99/' "$wt/rag/pyproject.toml"
    if UV_PYTHON_PREFERENCE=only-system UV_PYTHON_DOWNLOADS=never "$UV_REAL" lock -q --project "$wt/rag" --python /usr/bin/python3.12 >/dev/null 2>&1; then
      git -C "$wt" commit -q -am incompativel; git -C "$wt" push -q origin main
      M2="$(git -C "$wt" rev-parse HEAD)"
      PLATAFIRMA_UV="$UV_REAL" promover platafirma-motor "$M2"
      [ "$rc" -eq 3 ] && grep -q 'falha alta' <<<"$out" || falha "uv real com lock >=3.99 devia sair 3: rc=$rc $out"
      [ "$(current_de platafirma-motor)" = "$M1" ] || falha "current mudou com lock incompativel (uv real)"
      echo "OK (uv real, lock incompativel)"
    else
      pulado "uv real nao trava requires-python >=3.99 com python 3.12; caso coberto pelo uv falso em 2d"
    fi
  fi
fi

echo "=== uv/python/porta: todos os casos passaram ==="
