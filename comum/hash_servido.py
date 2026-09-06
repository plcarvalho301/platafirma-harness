# hash_servido.py — o hash do que foi SERVIDO. Uma lib, dois consumidores.
# capacidade: harness-sessao · dono: claudinho-TI
#
# arq:0101 R7 fixa hash unico: `sha256(lavado.strip())[:12]`, "uma lib importada pela
# porta e pelo montador". Antes havia duas implementacoes da mesma conta —
# `bin/monta-sessao::sha_conteudo` (sem strip) e o que a porta precisaria cunhar para
# o ledger de dedup. Duas contas do mesmo numero divergem em silencio, e o ledger
# compara justamente peca de abertura servida pelo montador com peca reservida pela
# porta: divergir aqui e nunca deduplicar nada.
#
# O `.strip()` e parte do contrato, nao detalhe: o mesmo conteudo servido por verbo
# ora vem com \n final, ora nao (subprocess.stdout x leitura de arquivo), e sem o
# strip o ledger via dois conteudos onde ha um.
#
# Sem dependencia externa de proposito: a porta roda em .venv-ops (sem driver de
# banco) e o montador em .venv-harness. O que os dois tem em comum e a stdlib.
import hashlib

TAM = 12


def sha_servido(texto: str) -> str:
    """sha256 do conteudo servido, hex, 12 caracteres (arq:0101 R7).

    Entra `str`; `bytes` decodifica-se com replace antes, porque conteudo binario
    lavado ja chega como texto marcado (`<blob …>`), nunca cru.
    """
    if isinstance(texto, bytes):                # tolerancia: nunca o caminho normal
        texto = texto.decode("utf-8", "replace")
    return hashlib.sha256((texto or "").strip().encode("utf-8")).hexdigest()[:TAM]
