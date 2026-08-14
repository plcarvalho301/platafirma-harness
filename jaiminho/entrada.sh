#!/bin/bash
# Sobe a ponte MCP e mantem o container vivo. O `agy` nao roda em laco: quem o
# chama e claudinho-TI (docker exec) ou, adiante, a ponte Matrix.
set -u
mkdir -p /home/jaiminho/.gemini/config /home/jaiminho/trabalho
cat > /home/jaiminho/.gemini/config/mcp_config.json <<JSON
{
  "mcpServers": {
    "platafirma": {
      "httpUrl": "http://127.0.0.1:8022/mcp",
      "trust": true
    }
  }
}
JSON
exec python3 -m uvicorn ponte:app --host 127.0.0.1 --port 8022
