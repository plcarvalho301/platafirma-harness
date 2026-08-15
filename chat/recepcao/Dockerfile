FROM python:3.13-slim

# Corpo da recepcao — o lado Matrix do giro. mautrix-python e a lib decidida na minuta 0002 (decisao
# 7): tem caminho de cripto vivo, que e a condicao do arquiteto para nao fechar a porta
# do E2EE de v1. Versao pinada: contrato de AS muda pouco, mas a lib muda rapido.
#
# Markdown entra no card 458: e o criterio 4 (tabela, code block e lista renderizando
# como tal no cliente movel). Sem um renderizador de verdade, `formatted_body` viraria
# markdown cru embrulhado em <pre>, que e exatamente o defeito que o criterio reprova.
RUN pip install --no-cache-dir "mautrix==0.21.1" "aiohttp==3.14.3" "Markdown==3.10.3"

RUN useradd -u 10001 -m -s /bin/bash recepcao

# O contexto de build e chat/, e nao chat/recepcao/, por causa de comum/: `journal.py`
# e a fronteira com o worker do host e nao pode ter duas copias (esquema com duas
# verdades e corrida esperando data), e `cadeiras.py` e o modulo de costura de
# claudinho-TI, que traduz slug do org, sufixo do harness e MXID — importado, nunca
# reimplementado (comentario 311 do card 458). O COPY do diretorio leva os dois.
WORKDIR /opt/chat
COPY --chown=recepcao:recepcao comum/ /opt/chat/comum/
COPY --chown=recepcao:recepcao recepcao/recepcao.py recepcao/formata.py recepcao/anexo.py \
     recepcao/rotacao.py /opt/chat/

USER recepcao
EXPOSE 8080
ENTRYPOINT ["python", "-u", "/opt/chat/recepcao.py"]
