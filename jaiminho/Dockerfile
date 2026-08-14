FROM debian:12-slim

# Corpo do Jaiminho: o Antigravity CLI (`agy`) e a ponte que o autentica no
# ops-server. Sem API paga — o CLI entra com a assinatura Google do dono.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates python3 python3-pip git jq tmux procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
      "starlette==0.41.3" "uvicorn==0.32.1" "httpx==0.28.1"

RUN useradd -u 10001 -m -s /bin/bash jaiminho
USER jaiminho
WORKDIR /home/jaiminho

# Instalador oficial: deixa o binario em ~/.local/bin/agy.
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash || true
ENV PATH="/home/jaiminho/.local/bin:${PATH}"

COPY --chown=jaiminho:jaiminho ponte.py /home/jaiminho/ponte.py
COPY --chown=jaiminho:jaiminho entrada.sh /home/jaiminho/entrada.sh

EXPOSE 8022
ENTRYPOINT ["/bin/bash", "/home/jaiminho/entrada.sh"]
