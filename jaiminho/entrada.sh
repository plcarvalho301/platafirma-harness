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
# nao arquivo dele.
cat > /home/jaiminho/.gemini/config/mcp_config.json <<JSON
{
  "mcpServers": {
    "platafirma": {
      "httpUrl": "http://127.0.0.1:8022/mcp",
      "trust": true
    },
    "platafirma-wiki": {
      "httpUrl": "http://127.0.0.1:8022/wiki",
      "trust": true
    }
  }
}
JSON

exec python3 -m uvicorn ponte:app --app-dir /opt/pf --host 127.0.0.1 --port 8022
