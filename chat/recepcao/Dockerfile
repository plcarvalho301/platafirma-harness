FROM python:3.13-slim

# Corpo da recepcao — o Application Service do Matrix. mautrix-python e a lib decidida na minuta 0002 (decisao
# 7): tem caminho de cripto vivo, que e a condicao do arquiteto para nao fechar a porta
# do E2EE de v1. Versao pinada: contrato de AS muda pouco, mas a lib muda rapido.
RUN pip install --no-cache-dir "mautrix==0.21.1" "aiohttp==3.14.3"

RUN useradd -u 10001 -m -s /bin/bash recepcao
USER recepcao
WORKDIR /home/recepcao

COPY --chown=recepcao:recepcao recepcao.py /home/recepcao/recepcao.py

EXPOSE 8080
ENTRYPOINT ["python", "-u", "/home/recepcao/recepcao.py"]
