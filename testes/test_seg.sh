#!/usr/bin/env bash
# Testes do verbo seg nas raizes do desenho #3010: cofre em $PLATAFIRMA_INSTANCIA/segredos, trilha em
# $PLATAFIRMA_INSTANCIA/var/log/seg, evidencia e regua derivada em $PLATAFIRMA_INSTANCIA/var/oscap, ferramental
# de terceiro so lido (SEG_SSG_DIR). Tudo num tmp; bancada inexistente.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/seg"

TMP_DIR="$(mktemp -d /tmp/pf-seg-test.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT
falha() { echo "FALHA: $*" >&2; exit 1; }

INSTANCIA="$TMP_DIR/srv"
export PLATAFIRMA_INSTANCIA="$INSTANCIA" PLATAFIRMA_BANCADA="$TMP_DIR/bancada-inexistente" SEG_SSG_DIR="$TMP_DIR/ssg"
unset SEG_SECRETS_DIR SEG_LOG_DIR SEG_OSCAP_DIR SEG_OQS_DIR 2>/dev/null || true

echo "=== seg: instancia ==="

echo "--- 1: segredo gravar/ler/listar no cofre da instancia, 0700/0600"
out="$(printf 'valor-teste' | "$VERBO" segredo gravar core/TOKEN 2>&1)" || falha "gravar: $out"
grep -q "gravado: core/TOKEN (11 bytes)" <<<"$out" || falha "gravar: $out"
[ -f "$INSTANCIA/segredos/core/TOKEN" ] || falha "segredo fora de \$PLATAFIRMA_INSTANCIA/segredos"
[ "$(stat -c %a "$INSTANCIA/segredos")" = "700" ] && [ "$(stat -c %a "$INSTANCIA/segredos/core")" = "700" ] || falha "diretorios do cofre deviam ser 0700"
[ "$(stat -c %a "$INSTANCIA/segredos/core/TOKEN")" = "600" ] || falha "segredo devia ser 0600"
[ "$("$VERBO" segredo ler core/TOKEN)" = "valor-teste" ] || falha "ler devolveu outro valor"
out="$("$VERBO" segredo listar core)" || falha "listar"
grep -q "^TOKEN core 11 .* 600$" <<<"$out" || falha "listar: $out"
set +e; "$VERBO" segredo ler core/NAO >/dev/null 2>&1; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "segredo ausente devia sair 1: rc=$rc"
echo "OK"

echo "--- 2: trilha em \$PLATAFIRMA_INSTANCIA/var/log/seg sem valor de segredo"
LOG="$INSTANCIA/var/log/seg/seg-$(date +%F).jsonl"
[ -s "$LOG" ] || falha "trilha ausente em $LOG"
! grep -q "valor-teste" "$LOG" || falha "valor de segredo na trilha"
echo "OK"

echo "--- 3: ssg derivar le do ferramental (r-x) e grava a regua na instancia; avaliar le a regua de la"
mkdir -p "$SEG_SSG_DIR"
printf '<a:platform idref="cpe:/o:canonical:ubuntu"/>\n<b:platform idref="#machine"/>\n' > "$SEG_SSG_DIR/ssg-ubuntu2404-ds.xml"
chmod -R a-w "$SEG_SSG_DIR"
out="$("$VERBO" ssg derivar ssg-ubuntu2404-ds.xml 2>&1)" || falha "derivar: $out"
DEST="$INSTANCIA/var/oscap/regua/ssg-ubuntu2404-ds-sem-cpe.xml"
[ -f "$DEST" ] || falha "regua derivada fora de \$PLATAFIRMA_INSTANCIA/var/oscap/regua: $out"
! grep -q 'cpe:/o:' "$DEST" || falha "cpe de SO nao removido"
grep -q 'idref="#machine"' "$DEST" || falha "applicability de regra perdida"
rm -f "$DEST"
set +e; out="$("$VERBO" oscap avaliar cis_level1_server 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "$INSTANCIA/var/oscap/regua" <<<"$out" || falha "avaliar sem regua: rc=$rc $out"
echo "OK"

echo "=== seg: todos os testes passaram ==="
