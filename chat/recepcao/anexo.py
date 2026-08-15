#!/usr/bin/env python3
"""Anexo recebido: da midia do celular ao caminho em anexos/ da fita (criterio 19).

O caminho do dado e curto e so tem um sentido: o dono manda um print, o receptor
baixa a midia pelo endpoint AUTENTICADO (spec >= v1.11) e grava em
~/AI/fitas/<cadeira>/anexos/. O que vai ao verbo e o CAMINHO, nunca os bytes — o
Claude Code le imagem do disco por `Read`, e anexos/ esta na allowlist da cadeira.

Quem grava e o receptor, de dentro do container, porque o bind mount de
~/AI/fitas e dele: partida por direcao, o worker nunca fala Matrix e o receptor
nunca chama verbo.

Duas guardas, e as duas produzem RECUSA EXPLICITA na sala — silencio aqui e o
defeito que o criterio 19 nomeia:

  - teto de 20 MiB, conferido duas vezes: no `info.size` que o cliente declara
    (barato, evita comecar o download) e no fluxo de bytes que chega (verdade,
    porque o `info.size` e do cliente e cliente mente).
  - allowlist de MIME, tambem duas vezes: no declarado e no Content-Type que o
    homeserver devolve.
"""

from __future__ import annotations

import os
import re

from mautrix.types import SpecVersions

TETO_PADRAO = 20 * 1024 * 1024  # 20 MiB, o numero da posicao de claudinho-TI
FITAS_RAIZ = "/home/claudinho/AI/fitas"

MIME_PERMITIDOS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
}

_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


class Recusado(Exception):
    """Anexo que nao entra. A mensagem e o que vai a sala, entao e escrita para
    o dono ler: diz o que houve e o limite, nunca traceback."""


def teto() -> int:
    try:
        return int(os.environ.get("CHAT_ANEXO_TETO", TETO_PADRAO))
    except ValueError:
        return TETO_PADRAO


def permitidos() -> dict[str, str]:
    bruto = os.environ.get("CHAT_MIME_PERMITIDOS", "").strip()
    if not bruto:
        return MIME_PERMITIDOS
    return {m.strip(): MIME_PERMITIDOS.get(m.strip(), "") for m in bruto.split(",") if m.strip()}


def _humano(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MiB"


def nome_seguro(nome: str, mime: str) -> str:
    """Nome de arquivo a partir do `body` do evento, que e texto do cliente.

    Vem de fora e vai virar caminho: `..`, barra e nome vazio sao tratados aqui
    e nao no open(). O basename sozinho nao basta — `..` sobrevive a ele.
    """
    nome = os.path.basename(nome or "").strip()
    nome = _SEGURO.sub("-", nome).strip("-.") or "anexo"
    if len(nome) > 96:
        raiz, ext = os.path.splitext(nome)
        nome = raiz[: 96 - len(ext)] + ext
    if not os.path.splitext(nome)[1]:
        nome += permitidos().get(mime) or MIME_PERMITIDOS.get(mime, "")
    return nome


def caminho_livre(diretorio: str, nome: str) -> str:
    """Primeiro nome nao ocupado. Anexo nao sobrescreve anexo: dois prints da
    mesma tela na mesma fita sao duas coisas, e a cadeira pode precisar das duas."""
    alvo = os.path.join(diretorio, nome)
    if not os.path.exists(alvo):
        return alvo
    raiz, ext = os.path.splitext(nome)
    for n in range(2, 1000):
        alvo = os.path.join(diretorio, f"{raiz}-{n}{ext}")
        if not os.path.exists(alvo):
            return alvo
    raise Recusado("anexos/ desta fita ja tem arquivos demais com esse nome.")


def anexos_de(cadeira: str) -> str:
    """Cria anexos/ da cadeira se faltar — o card poe a criacao do lado do
    receptor, que e quem tem o bind mount."""
    caminho = os.path.join(os.environ.get("CHAT_FITAS_RAIZ", FITAS_RAIZ), cadeira, "anexos")
    os.makedirs(caminho, exist_ok=True)
    return caminho


async def baixa(intent, *, mxc: str, nome: str, mime: str, tamanho_declarado: int,
                cadeira: str) -> tuple[str, int, str]:
    """Baixa e grava. Devolve (caminho, bytes, mime). Levanta Recusado com o
    texto que vai a sala."""
    mime = (mime or "application/octet-stream").split(";")[0].strip().lower()
    lista = permitidos()
    limite = teto()

    if mime not in lista:
        raise Recusado(
            f"nao recebo arquivo do tipo `{mime}`. Aceito: "
            + ", ".join(f"`{m}`" for m in sorted(lista))
        )
    if tamanho_declarado and tamanho_declarado > limite:
        raise Recusado(
            f"o arquivo tem {_humano(tamanho_declarado)} e o teto e {_humano(limite)}."
        )

    autenticado = (await intent.versions()).supports(SpecVersions.V111)
    url = intent.api.get_download_url(mxc, authenticated=autenticado)
    params: dict[str, str] = {"allow_redirect": "true"}
    headers: dict[str, str] = {}
    if autenticado:
        # Endpoint autenticado da spec v1.11: a midia deixou de ser publica, e
        # sem o Bearer o download volta 401. O `user_id` masquerada o pedido
        # como a cadeira, que e quem esta na sala.
        headers["Authorization"] = f"Bearer {intent.api.token}"
        if intent.api.as_user_id:
            params["user_id"] = intent.api.as_user_id

    diretorio = anexos_de(cadeira)
    alvo = caminho_livre(diretorio, nome_seguro(nome, mime))
    # Parcial + rename: download cortado no meio nunca aparece em anexos/ como
    # arquivo bom. A cadeira leria um PNG truncado e o erro sairia longe daqui.
    parcial = os.path.join(diretorio, "." + os.path.basename(alvo) + ".parcial")

    escritos = 0
    try:
        async with intent.api.session.get(url, params=params, headers=headers) as resposta:
            if resposta.status != 200:
                raise Recusado(f"o servidor de midia respondeu {resposta.status} ao download.")
            servido = (resposta.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if servido and servido not in lista:
                raise Recusado(f"o arquivo chegou como `{servido}`, que nao esta na lista.")
            with open(parcial, "wb") as saida:
                async for pedaco in resposta.content.iter_chunked(64 * 1024):
                    escritos += len(pedaco)
                    if escritos > limite:
                        # Teto de verdade: o `info.size` do cliente ja passou, e
                        # este e o numero que nao depende de ninguem declarar.
                        raise Recusado(
                            f"o arquivo passou de {_humano(limite)} durante o download."
                        )
                    saida.write(pedaco)
        os.replace(parcial, alvo)
    except Recusado:
        _apaga(parcial)
        raise
    except Exception as erro:
        _apaga(parcial)
        raise Recusado(f"nao consegui baixar o anexo ({type(erro).__name__}).") from erro

    return alvo, escritos, mime


def _apaga(caminho: str) -> None:
    try:
        os.unlink(caminho)
    except FileNotFoundError:
        pass


def linha_de_corpo(caminho: str, tamanho: int, mime: str, legenda: str = "") -> str:
    """O que o verbo recebe no lugar dos bytes.

    Caminho absoluto e valido no host tal como esta: o bind mount do receptor
    monta ~/AI/fitas no MESMO caminho absoluto de fora, justamente para o texto
    atravessar a fronteira sem traducao.
    """
    cabeca = f"[anexo recebido: {caminho} ({mime}, {_humano(tamanho)})]"
    return f"{cabeca}\n{legenda}".strip()
