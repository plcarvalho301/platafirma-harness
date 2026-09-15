#!/usr/bin/env bash
# Testes do verbo release — lote 3: `release conferir` absorve as classes do servido (spec_release §4, §8)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/release"
CONFERIR="$REPO_ROOT/bin/conferir"
IMPL="$REPO_ROOT/bin/_release/conferir/conferir.py"

falha() { echo "FALHA: $*" >&2; exit 1; }
echo "=== release lote 3: conferir absorvido ==="

echo "--- 1: implementacao e sub-ato fora do PATH; bin/conferir e despachante"
[ -f "$IMPL" ] || falha "sub-ato $IMPL ausente"
head -1 "$CONFERIR" | grep -q bash || falha "bin/conferir devia ser o despachante em bash"
python3 -m py_compile "$IMPL" || falha "conferir.py nao compila"
bash -n "$CONFERIR" || falha "bin/conferir com erro de sintaxe"
echo OK

echo "--- 2: release conferir recusa existe e bancada; --ref so em verbo"
set +e; out="$("$VERBO" conferir existe verbo x 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "conferir existe" <<<"$out" || falha "existe: rc=$rc $out"
set +e; out="$("$VERBO" conferir repo --staged 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "bancada" <<<"$out" || falha "repo: rc=$rc $out"
set +e; out="$("$VERBO" conferir servico --ref HEAD 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "so mede a classe verbo" <<<"$out" || falha "--ref fora de verbo: rc=$rc $out"
echo OK

echo "--- 3: classe do servido chamada por bin/conferir avisa deprecado uma vez por sessao e delega"
export PF_SESSAO="teste-lote3-$$"
rm -rf "/tmp/platafirma-avisos-$PF_SESSAO"
set +e; out1="$(PATH="$REPO_ROOT/bin:$PATH" bash "$CONFERIR" verbo release 2>&1 >/dev/null)"; set -e
grep -q "deprecado" <<<"$out1" || falha "primeira chamada sem aviso: $out1"
set +e; out2="$(PATH="$REPO_ROOT/bin:$PATH" bash "$CONFERIR" verbo release 2>&1 >/dev/null)"; set -e
! grep -q "deprecado" <<<"$out2" || falha "segunda chamada repetiu o aviso"
rm -rf "/tmp/platafirma-avisos-$PF_SESSAO"
echo OK

echo "=== lote 3: todos os testes passaram ==="
