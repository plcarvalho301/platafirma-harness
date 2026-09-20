#!/usr/bin/env bash
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
BIN="$AQUI/../bin"
export PATH="$BIN:$PATH"

# (a) duas sessões, duas árvores, git cru recusa add -A e commit cruzado
echo "=== Teste (a) ==="
export PF_CADEIRA="claudinho-fabrica"
export PF_SESSAO="sessao-a1"
# abrir cria wt/.../sessao-a1
repo abrir platafirma-harness --cadeira claudinho-fabrica >/dev/null
arv1="$(repo git platafirma-harness rev-parse --show-toplevel)"

export PF_SESSAO="sessao-a2"
# abrir cria wt/.../sessao-a2
repo abrir platafirma-harness --cadeira claudinho-fabrica >/dev/null
arv2="$(repo git platafirma-harness rev-parse --show-toplevel)"

if [ "$arv1" = "$arv2" ]; then
  echo "erro: arvores deveriam ser diferentes ($arv1 == $arv2)"
  exit 1
fi
echo "arvores diferentes: ok ($arv1 != $arv2)"

# git cru recusa add -A
if (repo git platafirma-harness add -A 2>&1 || true) | grep -q "recusa add -A"; then
  echo "recusa add -A: ok"
else
  echo "erro: não recusou add -A"
  exit 1
fi

# commit cruzado
# let's create a branch 'dados/teste' while being in 'fabrica'
repo ramo platafirma-harness dados/teste >/dev/null || true
if (repo git platafirma-harness commit -m "teste" 2>&1 || true) | grep -q "recusado: o ramo"; then
  echo "recusa commit cruzado: ok"
else
  echo "erro: não recusou commit cruzado"
  exit 1
fi
# clean up
repo ramo platafirma-harness main >/dev/null || true
repo git platafirma-harness branch -D dados/teste >/dev/null || true

# (b) verbo responde o estado do lote e manifesto gravado no run
echo "=== Teste (b) ==="

# Simulate ingerir writing the manifesto (because real API requires authentication)
LOTE_ID="mock-1234"
mkdir -p "$HOME/AI/registro/lotes"
cat <<JSON > "$HOME/AI/registro/lotes/$LOTE_ID.json"
{
  "id": "$LOTE_ID",
  "estado": "pendente",
  "itens": [
    {"origem": {"objeto": "mock-obj"}, "veredito": "aceito"}
  ]
}
JSON

res="$(acervo lote "$LOTE_ID")"
if echo "$res" | grep -q "lote $LOTE_ID"; then
  echo "acervo lote responde: ok"
else
  echo "erro: acervo lote falhou"
  exit 1
fi


# (c) conferir diagrama compila/recusa e repo commitar barra
echo "=== Teste (c) ==="
export PF_SESSAO="sessao-c"

# Simulate Kroki
python3 -c '
import http.server, socketserver
class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        c = self.rfile.read(int(self.headers["Content-Length"])).decode()
        if "bad syntax" in c:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Syntax error in line 1")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<svg></svg>")
    def log_message(self, *args): pass
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", 8011), Handler)
httpd.serve_forever()
' &
KROKI_PID=$!
sleep 1
export KROKI_URL="http://127.0.0.1:8011"

repo abrir platafirma-harness --cadeira claudinho-fabrica >/dev/null
repo ramo platafirma-harness fabrica/teste-diag >/dev/null || true
arvc="$(repo git platafirma-harness rev-parse --show-toplevel)"
cd "$arvc"
echo "graph TD; A-->B" > bom.mmd
echo "graph XX; bad syntax" > ruim.mmd
if conferir diagrama bom.mmd >/dev/null; then
  echo "conferir diagrama bom: ok"
else
  echo "erro: falhou diagrama bom"
  exit 1
fi

if conferir diagrama ruim.mmd >/dev/null 2>&1; then
  echo "erro: passou diagrama ruim"
  exit 1
else
  echo "conferir diagrama ruim (recusa): ok"
fi

# repo commitar barra diagrama quebrado
repo git platafirma-harness add bom.mmd ruim.mmd || echo "GIT ADD FAILED"
out="$(repo commitar platafirma-harness -m "teste" bom.mmd ruim.mmd 2>&1 || true)"
if echo "$out" | grep -q "Kroki recusou a compilacao"; then
  echo "repo commitar barra diagrama ruim: ok"
else
  echo "erro: repo commitar não barrou diagrama ruim. Saida foi:"
echo "$out"
  exit 1
fi

# clean up
git reset HEAD bom.mmd ruim.mmd >/dev/null
rm bom.mmd ruim.mmd
repo ramo platafirma-harness main >/dev/null || true
repo git platafirma-harness branch -D fabrica/teste-diag >/dev/null || true

echo "SUCESSO."

kill $KROKI_PID || true
