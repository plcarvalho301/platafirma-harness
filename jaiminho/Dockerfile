FROM debian:12-slim

# Corpo do Jaiminho: o Antigravity CLI (`agy`) e a ponte que o autentica no
# ops-server. Sem API paga — o CLI entra com a assinatura Google do dono.
#
# REGRA DA IMAGEM: nada nosso mora em /home/jaiminho. O home inteiro e volume
# (a casa dele, persistente entre recreates); codigo nosso e binario de terceiro
# ficam em /opt/pf, que vem da imagem e e sempre fresco. Sem isso, volume velho
# mascara ponte.py nova e `agy` congela na versao do primeiro build.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates python3 python3-pip python3-venv git jq tmux procps \
      ripgrep fd-find poppler-utils unzip p7zip-full libimage-exiftool-perl \
      whois dnsutils sqlite3 \
    && ln -s /usr/bin/fdfind /usr/local/bin/fd \
    && rm -rf /var/lib/apt/lists/*

# Ponte (starlette/uvicorn/httpx) + ferramental de OSINT e parsing do Jaiminho.
RUN pip3 install --no-cache-dir --break-system-packages \
      "starlette==0.41.3" "uvicorn==0.32.1" "httpx==0.28.1" \
      beautifulsoup4 lxml selectolax trafilatura markdownify readability-lxml \
      feedparser pyyaml python-dateutil \
      pdfplumber pypdf python-docx openpyxl odfpy pandas \
      tldextract dnspython python-whois \
      playwright rich typer \
      lxml_html_clean

RUN useradd -u 10001 -m -s /bin/bash jaiminho

# `agy` instalado como jaiminho (o instalador oficial exige HOME de usuario),
# depois movido para /opt/pf/bin — fora do volume.
USER jaiminho
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash || true
USER root
RUN mkdir -p /opt/pf/bin \
    && mv /home/jaiminho/.local/bin/agy /opt/pf/bin/agy \
    && chmod 0755 /opt/pf/bin/agy \
    && rm -rf /home/jaiminho/.local /home/jaiminho/.cache

COPY ponte.py /opt/pf/ponte.py
COPY entrada.sh /opt/pf/entrada.sh
RUN chmod 0755 /opt/pf/entrada.sh

# `bash -lc` reconstroi o PATH pelo /etc/profile e descarta o ENV da imagem:
# sem esta linha o `agy` some em shell de login, que e como o CLI acaba sendo
# chamado. Medido em 15/08.
RUN printf '%s\n' 'export PATH="$HOME/bin:$HOME/.local/bin:/opt/pf/bin:$PATH"' \
      > /etc/profile.d/pf-path.sh

USER jaiminho
WORKDIR /home/jaiminho
# ~/bin e ~/.local/bin vem PRIMEIRO: e onde o Jaiminho monta ferramenta propria,
# e ferramenta dele vence a nossa em caso de nome igual.
ENV PATH="/home/jaiminho/bin:/home/jaiminho/.local/bin:/opt/pf/bin:${PATH}"
ENV PYTHONPATH="/home/jaiminho/lib"

EXPOSE 8022
ENTRYPOINT ["/bin/bash", "/opt/pf/entrada.sh"]
