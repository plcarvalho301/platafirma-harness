FROM python:3.13-slim

# Corpo do Application Service. mautrix-python e a lib decidida na minuta 0002 (decisao
# 7): tem caminho de cripto vivo, que e a condicao do arquiteto para nao fechar a porta
# do E2EE de v1. Versao pinada: contrato de AS muda pouco, mas a lib muda rapido.
RUN pip install --no-cache-dir "mautrix==0.21.1" "aiohttp==3.14.3"

RUN useradd -u 10001 -m -s /bin/bash as
USER as
WORKDIR /home/as

COPY --chown=as:as as.py /home/as/as.py

EXPOSE 8080
ENTRYPOINT ["python", "-u", "/home/as/as.py"]
