#!/bin/bash
# Sobe a ponte MCP e mantem o container vivo. O `agy` nao roda em laco: quem o
# chama e claudinho-TI (docker exec) ou a recepcao do chat.
#
# Roda a cada boot porque o home e volume: o que este script garante e a casa
# do Jaiminho existir e estar configurada, sem sobrescrever o que ele fez la.
set -u

mkdir -p /home/jaiminho/.gemini/config \
         /home/jaiminho/bin \
         /home/jaiminho/lib \
         /home/jaiminho/trabalho \
         /home/jaiminho/pesquisas

# Home e volume: casa nova nasce sem .bashrc/.profile. Semeia do skel uma vez,
# sem sobrescrever o que ele ja tiver editado.
for f in .bashrc .profile; do
  [ -f "/home/jaiminho/$f" ] || cp "/etc/skel/$f" "/home/jaiminho/$f" 2>/dev/null || true
done

# Conectores MCP do CLI. Reescrito a cada boot de proposito — e contrato nosso,
# nao arquivo dele. Rota que a ponte serve e este JSON nao declara e rota
# inexistente para o `agy`: ele so sobe tool de servidor listado aqui.
#
# A chave e `serverUrl`, NAO `httpUrl`. O schema do Antigravity CLI tem dois
# transportes so — stdio (`command`/`args`/`env`) e remoto (`serverUrl`) —, e
# chave desconhecida ele descarta calado: nem sobe o servidor, nem loga erro.
# Medido em 16/08/2026: com `httpUrl` o `agy` respondia "nenhum servidor MCP
# conectado" para os TRES; trocada a chave, subiram na mesma casa e no mesmo
# boot. Fonte do schema, dentro da propria imagem dele:
# ~/.gemini/antigravity-cli/builtin/skills/agy-customizations/docs/mcp_servers.md
# `trust` tambem nao e do schema: o verbo chama `agy` com
# --dangerously-skip-permissions, entao aprovacao de tool ja nao passa por aqui.
#
# Sao DOIS conectores, nao tres: `platafirma-wiki` saiu em 16/08/2026. A wiki nao
# tem rota propria na ponte porque o wiki-mcp autentica por segredo estatico e sem
# PEP — o mesmo Bearer que le tambem edita. Ela entra pelas tools `wiki_*` do
# jaiminho-server, atras do PDP, no mesmo conector do acervo.
cat > /home/jaiminho/.gemini/config/mcp_config.json <<JSON
{
  "mcpServers": {
    "platafirma": { "serverUrl": "http://127.0.0.1:8022/mcp" },
    "platafirma-conhecimento": { "serverUrl": "http://127.0.0.1:8022/acervo" }
  }
}
JSON

exec python3 -m uvicorn ponte:app --app-dir /opt/pf --host 127.0.0.1 --port 8022
