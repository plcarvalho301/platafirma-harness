"""O descanso da sessão (story 4335, feature 4269, peça 6, regras 28 a 31).

eventos     sessão aberta e sessão encerrada, pelo oplog.emitir
memoria     a chave da sessão no Valkey msg-mem: existe? apaga
abandono    a sessão aberta sem encerrada, com a chave vencida, fecha como abandonada
publicar    a mensagem (forma da micropublicação, com destinatário e tipo), as chaves conferidas no fichário e onde ela grava
coletas     as três coletas que o descanso dispara em segundo plano
"""
