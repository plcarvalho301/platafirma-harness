"""Adaptador da fila — a caixa de cada cadeira.

`spec_recuperador.md` §5: contrato = `XINFO STREAM` · `XRANGE` no motor-msg; carimbo =
`last-generated-id`; classe exata; prefixo de `sobre` = `caixa:<quem>`. §4: chave =
`caixa:<slug>/<stream-id>`, versão = o próprio id.

**Leitura FRIA, sempre.** `XRANGE`, nunca `XREADGROUP`: recuperar não pode consumir a
caixa de ninguém. Se o Recuperador movesse o ponteiro, a carta lida por ele sumiria da
`fila ler` da cadeira dona — recuperação que destrói o que recupera. É o mesmo caminho
que `fila ler --tudo` usa por baixo, e é essa a delegação ao contrato.

A caixa continua endereçada pelo slug **canônico** (`claudinho-IA`), não pelo sufixo do
substrato de mesa: são endereços de coisas diferentes, e colapsar os dois foi o que
partiu a mesa em duas metades (medido em 16/08, `bin/mesa`).
"""

from __future__ import annotations

import os

from ..envelope import Causa, Item, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel

HOST = os.environ.get("FILA_REDIS_HOST", "127.0.0.1")
PORTA = int(os.environ.get("FILA_REDIS_PORT", "6379"))

CAMPOS = ("de", "tipo", "assunto", "ref", "responde", "corpo")


class AdaptadorFila(Adaptador):
    fonte = Fonte.FILA
    tem_gold = False

    def __init__(self, cliente=None, host: str = HOST, porta: int = PORTA) -> None:
        self._cliente = cliente
        self.host, self.porta = host, porta

    def cliente(self):
        if self._cliente is not None:
            return self._cliente
        try:
            import redis
        except ImportError as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, "módulo `redis` ausente") from e
        try:
            self._cliente = redis.Redis(host=self.host, port=self.porta,
                                        decode_responses=True, socket_timeout=1)
            self._cliente.ping()
        except Exception as e:  # noqa: BLE001
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"{self.host}:{self.porta}") from e
        return self._cliente

    # ---- alvo -----------------------------------------------------------------------

    @staticmethod
    def caixa(alvo: str) -> str:
        """`claudinho-IA` e `caixa:claudinho-IA` são o mesmo alvo."""
        alvo = (alvo or "").strip()
        return alvo[len("caixa:"):] if alvo.startswith("caixa:") else alvo

    def _chave_stream(self, alvo: str) -> str:
        return f"caixa:{self.caixa(alvo)}"

    # ---- carimbo --------------------------------------------------------------------

    def _carimbo(self, alvo: str = "") -> str:
        rc = self.cliente()
        try:
            info = rc.xinfo_stream(self._chave_stream(alvo)) if alvo else None
        except Exception:  # noqa: BLE001 — stream inexistente é caixa vazia, não falha
            return "0-0"
        return str(info.get("last-generated-id", "0-0")) if info else "0-0"

    # ---- busca ----------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        filtros = filtros or {}
        caixa = self.caixa(alvo)
        if not caixa:
            raise FonteIndisponivel(Causa.SEM_ROTA, "fila exige a caixa no alvo")
        self._ultimo_alvo = caixa
        rc = self.cliente()
        try:
            entradas = rc.xrange(self._chave_stream(caixa), min="-", max="+")
        except Exception as e:  # noqa: BLE001
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"xrange caixa:{caixa}") from e

        itens = []
        for sid, campos in entradas:
            if not self._casa(campos, filtros):
                continue
            itens.append(self._item(caixa, str(sid), campos, texto))
        return list(reversed(itens))[:k] if itens else []

    @staticmethod
    def _casa(campos: dict, filtros: dict) -> bool:
        for chave in ("tipo", "de", "responde"):
            esperado = filtros.get(chave)
            if esperado and str(campos.get(chave, "")) != str(esperado):
                return False
        termo = (filtros.get("assunto") or "").lower()
        if termo and termo not in str(campos.get("assunto", "")).lower():
            return False
        return True

    def _item(self, caixa: str, sid: str, campos: dict, texto: str) -> Item:
        proc = Procedencia(
            fonte=Fonte.FILA,
            chave=f"caixa:{caixa}/{sid}",
            versao=Versao(tipo=VersaoTipo.STREAM_ID, valor=sid),
        )
        # O `id` da carta é o carimbo HUMANO (`20260820T125326-<remetente>`) — é ele que
        # `fila responder` consome e é por ele que o verbo humano imprime. O stream-id
        # fica na procedência, que é a chave estrutural; os dois são precisos e servem a
        # leitores diferentes.
        msgid = campos.get("id") or campos.get("msgid") or sid
        cabeca = (f"{msgid} · {campos.get('tipo', '?')} de {campos.get('de', '?')}: "
                  f"{campos.get('assunto', '')}")
        if texto == "nenhum":
            return Item(procedencia=proc, ref=cabeca)
        corpo = str(campos.get("corpo", ""))
        if texto == "trecho":
            corpo = corpo[:800] + ("\n[…]" if len(corpo) > 800 else "")
        return Item(procedencia=proc, conteudo=f"{cabeca}\n\n{corpo}".rstrip())

    # ---- carimbo depende do alvo, então `busca` é sobrescrita ------------------------

    def busca(self, alvo: str, filtros: dict | None = None, k: int = 8,
              texto: str = "secao"):
        from ..envelope import Cobertura, LinhaFonte
        from .base import Resultado

        itens = self._busca(alvo, filtros, k, texto)[:k]
        return Resultado(
            linha=LinhaFonte(
                fonte=self.fonte,
                cobertura=self.cobertura_com_item() if itens else Cobertura.VAZIA,
                carimbo=self._carimbo(alvo),
            ),
            itens=itens,
        )
