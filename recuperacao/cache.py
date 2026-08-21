"""Cache de recuperação — uma linha por fonte, e a medida desde o primeiro release.

`spec_recuperador.md` §9. O que este módulo faz valer, e por quê:

- **Uma linha por FONTE, não uma por envelope.** `rec:<fonte>:<carimbo>:<hash>`. O
  envelope é montado de N linhas, e board volátil não derruba cache de acervo estável.
  Cache por envelope tem taxa de acerto de envelope, que é o produto das taxas de fonte.
- **`sujeito` NÃO entra na chave.** O PEP roda por fonte ANTES do lookup (§6); o cache
  guarda resposta da fonte, nunca decisão de acesso. Hit sem PEP é vazamento entre
  sujeitos com cara de economia.
- **Instância própria** — `motor-cache`, `127.0.0.1:6381`, `allkeys-lru`, 1 GB, sem AOF
  (#2306, `platafirma-motor@b92c528`). **Nunca** a `msg-mem` (6380): ela guarda `mem:*` e
  `fita:*`, e `allkeys-lru` não distingue cache descartável de estado de trabalho —
  sob pressão despeja a mesa e nada acusa.
- **Instrumentação desde já**, `rec:stat:<fonte>` (HASH, `HINCRBY`): `hit`, `miss`,
  `bytes`, `idade`. Sem isso, o hit rate que decidiria o cache semântico nunca existe.

**Divergência declarada da carta de claudinho-TI (20/08/2026).** A sugestão de forma era
`rec:<fonte>:<sujeito>:<carimbo>`. O `<sujeito>` fica de fora: o §9 é explícito, e a
decisão é minha (o cache é do recuperador). Sujeito na chave não é só desperdício de
espaço — é a forma de esquecer que o PEP tem de rodar antes do lookup, porque a chave
passa a *parecer* segura por si.

**O cache de acervo está DESLIGADO, e isso é o §9, não uma omissão.** A pré-condição é a
ordem `#167 → #283 → cache`, e os dois estão em lapidação com claudinho-dados
(medido em 20/08/2026). Cache antes de `abrir_impressao` idempotente por sha mede o bug,
não o produto. `PF_CACHE_ACERVO=1` liga na bancada, nomeado; a validação no hit por
`rec:aposentadas` já está escrita e é o que ligará junto.

**O que não está aqui:** compressão acima de 4 K está (zlib), persistência é casual por
desenho (sem AOF, sem snapshot: toda chave é re-derivável), e `notify-keyspace-events`
está desligado de propósito — não há assinante de expiração neste desenho.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import unicodedata
import zlib

from .adaptadores.base import Adaptador, Resultado
from .envelope import (
    Casamento,
    Causa,
    Cobertura,
    Item,
    LinhaFonte,
    Procedencia,
    Sinal,
    Versao,
)
from .fontes import CLASSE, Classe, Fonte

HOST = os.environ.get("REC_CACHE_HOST", "127.0.0.1")
PORTA = int(os.environ.get("REC_CACHE_PORT", "6381"))  # motor-cache, NÃO msg-mem (6380)

PREFIXO = "rec"
STAT = "rec:stat"
APOSENTADAS = "rec:aposentadas"

# §9 — TTL por classe. ⚪ hipótese: os dois números são ponto de partida, e o que os fecha
# é a taxa de mudança por fonte que `rec:stat` passa a medir a partir de hoje.
TTL_S: dict[Classe, int] = {
    Classe.EXATA: 60,
    Classe.SEMANTICA: 7 * 24 * 3600,
}

LIMITE_COMPRESSAO = 4096
MARCA_ZLIB = b"z:"

# §9 — o acervo é a exceção com pré-condição, e ela não fechou.
ACERVO_LIGADO = os.environ.get("PF_CACHE_ACERVO", "") == "1"


class SemCache(Exception):
    """O cache não respondeu. Nunca sobe ao consumidor: cache mudo é miss, não falha."""


# ------------------------------------------------------------------ chave


def _normaliza(alvo: str) -> str:
    return unicodedata.normalize("NFC", (alvo or "")).strip()


def _canoniza(filtros: dict | None) -> str:
    """Filtros ordenados e sem espaço supérfluo: `{a:1,b:2}` e `{b:2,a:1}` são a mesma
    consulta, e chave diferente para a mesma consulta é miss fabricado."""
    return json.dumps(filtros or {}, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def digest_consulta(alvo: str, filtros: dict | None, k: int, texto: str) -> str:
    """`k` e `texto` entram: a mesma pergunta com k=3 e com k=8 devolve conteúdo
    diferente, e servir um pelo outro seria o cache mentindo dentro do contrato."""
    cru = f"{_normaliza(alvo)}\x1f{_canoniza(filtros)}\x1f{k}\x1f{texto}"
    return hashlib.sha256(cru.encode("utf-8")).hexdigest()[:16]


def chave(fonte: Fonte, carimbo: str | None, alvo: str, filtros: dict | None,
          k: int = 8, texto: str = "secao") -> str:
    """`rec:<fonte>:<carimbo>:<hash>` — e sem carimbo no acervo, de propósito (§9).

    Carimbo na chave do acervo invalidaria o acervo inteiro a cada re-corte de UMA obra;
    lá a linha é validada no hit, pela procedência que ela já carrega.
    """
    d = digest_consulta(alvo, filtros, k, texto)
    if Fonte(fonte) == Fonte("acervo"):
        return f"{PREFIXO}:{fonte}:{d}"
    return f"{PREFIXO}:{fonte}:{carimbo or '0'}:{d}"


# ------------------------------------------------------------------ (de)serialização


def _resultado_para_json(r: Resultado) -> dict:
    return {
        "t": int(time.time()),
        "linha": r.linha.para_json(),
        "carimbo": r.linha.carimbo,
        "itens": [i.para_json() for i in r.itens],
    }


def _item_de_json(d: dict) -> Item:
    p = d["procedencia"]
    proc = Procedencia(
        fonte=Fonte(p["fonte"]),
        chave=p["chave"],
        versao=Versao(tipo=p["versao"]["tipo"], valor=p["versao"]["valor"]),
        digest=p.get("digest"),
    )
    return Item(
        procedencia=proc,
        conteudo=d.get("conteudo"),
        ref=d.get("ref"),
        casamento=Casamento(d["casamento"]) if d.get("casamento") else None,
    )


def _resultado_de_json(d: dict) -> Resultado:
    """Passa pelos MESMOS construtores da leitura viva: linha de cache corrompida ou de
    um contrato velho levanta aqui e vira miss, em vez de entrar no envelope."""
    linha = d["linha"]
    sinal = linha.get("sinal")
    return Resultado(
        linha=LinhaFonte(
            fonte=Fonte(linha["fonte"]),
            cobertura=Cobertura(linha["cobertura"]),
            sinal=Sinal(**sinal) if sinal else None,
            carimbo=d.get("carimbo") or linha.get("carimbo"),
            causa=Causa(linha["causa"]) if linha.get("causa") else None,
        ),
        itens=[_item_de_json(i) for i in d.get("itens", [])],
    )


def _empacota(d: dict) -> bytes:
    cru = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(cru) > LIMITE_COMPRESSAO:
        return MARCA_ZLIB + zlib.compress(cru, 6)
    return cru


def _desempacota(bruto: bytes) -> dict:
    if bruto.startswith(MARCA_ZLIB):
        bruto = zlib.decompress(bruto[len(MARCA_ZLIB):])
    return json.loads(bruto)


# ------------------------------------------------------------------ o cache


class Cache:
    """Uma instância por processo. Cliente injetável — o contrato não sai à rede."""

    def __init__(self, cliente=None, host: str = HOST, porta: int = PORTA,
                 timeout_s: float = 0.25) -> None:
        self._cliente = cliente
        self.host, self.porta, self.timeout_s = host, porta, timeout_s

    # ---- transporte ---------------------------------------------------------------

    @property
    def cliente(self):
        if self._cliente is None:
            try:
                import redis
            except ImportError as e:  # pragma: no cover
                raise SemCache("módulo `redis` ausente") from e
            self._cliente = redis.Redis(
                host=self.host, port=self.porta, decode_responses=False,
                socket_timeout=self.timeout_s, socket_connect_timeout=self.timeout_s,
            )
        return self._cliente

    def ligado_para(self, fonte: Fonte) -> bool:
        """Acervo só com a pré-condição do §9 cumprida (`#167 → #283`), ou escape nomeado."""
        return ACERVO_LIGADO if Fonte(fonte) == Fonte("acervo") else True

    # ---- instrumentação -------------------------------------------------------------

    def _stat(self, fonte: Fonte, campo: str, quanto: int = 1) -> None:
        """A medida nunca derruba a leitura: cache mudo perde o contador, não a resposta."""
        try:
            self.cliente.hincrby(f"{STAT}:{fonte}", campo, quanto)
        except Exception:  # noqa: BLE001
            pass

    def estatistica(self, fonte: Fonte) -> dict:
        """`hit`, `miss`, `bytes`, `idade`. `idade` é SOMA em segundos: a média por hit é
        `idade / hit`, e guardar a soma é o que `HINCRBY` sabe fazer sem corrida."""
        try:
            cru = self.cliente.hgetall(f"{STAT}:{fonte}")
        except Exception as e:  # noqa: BLE001
            raise SemCache(str(e)) from e
        d = {}
        for ch, v in (cru or {}).items():
            ch = ch.decode() if isinstance(ch, bytes) else ch
            v = v.decode() if isinstance(v, bytes) else v
            d[ch] = int(v)
        for campo in ("hit", "miss", "bytes", "idade"):
            d.setdefault(campo, 0)
        return d

    # ---- validação de hit do acervo -------------------------------------------------

    def hit_do_acervo_vale(self, r: Resultado) -> bool:
        """§9 — a linha do acervo é validada NO HIT: toda `impressao.id` citada ainda tem
        de estar servindo. N `SISMEMBER` por hit, N ≈ 8. Cache mudo aqui reprova o hit:
        é o lado seguro (rebusca), nunca servir citação de impressão aposentada."""
        versoes = [i.procedencia.versao.valor for i in r.itens]
        if not versoes:
            return True
        try:
            for v in versoes:
                if self.cliente.sismember(APOSENTADAS, v):
                    return False
        except Exception:  # noqa: BLE001
            return False
        return True

    # ---- leitura e escrita ----------------------------------------------------------

    def le(self, fonte: Fonte, ch: str) -> Resultado | None:
        if not self.ligado_para(fonte):
            return None
        try:
            bruto = self.cliente.get(ch)
        except Exception:  # noqa: BLE001
            return None
        if not bruto:
            return None
        try:
            d = _desempacota(bruto)
            r = _resultado_de_json(d)
        except Exception:  # noqa: BLE001
            # Contrato velho ou valor corrompido: apaga e trata como miss. Servir isto
            # seria pôr no envelope um item que a leitura viva teria recusado.
            try:
                self.cliente.delete(ch)
            except Exception:  # noqa: BLE001
                pass
            return None
        if Fonte(fonte) == Fonte("acervo") and not self.hit_do_acervo_vale(r):
            return None
        idade = max(0, int(time.time()) - int(d.get("t", 0)))
        self._stat(fonte, "hit")
        self._stat(fonte, "bytes", len(bruto))
        self._stat(fonte, "idade", idade)
        return r

    def grava(self, fonte: Fonte, ch: str, r: Resultado) -> bool:
        """Só resposta ÚTIL entra. Fonte caída (`fonte-nao-indexada`) não se cacheia: o
        TTL transformaria uma indisponibilidade de um segundo em minuto de fonte morta."""
        if not self.ligado_para(fonte):
            return False
        if r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA:
            return False
        try:
            self.cliente.set(ch, _empacota(_resultado_para_json(r)),
                             ex=TTL_S[CLASSE[Fonte(fonte)]])
        except Exception:  # noqa: BLE001
            return False
        return True


# ------------------------------------------------------------------ o caminho servido


def busca_com_cache(adaptador: Adaptador, alvo: str = "", filtros: dict | None = None,
                    k: int = 8, texto: str = "secao",
                    cache: Cache | None = None) -> tuple[Resultado, bool]:
    """`(resultado, veio_do_cache)`.

    **O PEP não roda aqui, e é de propósito**: ele decide por fonte ANTES desta chamada
    (§6). Chamar `busca_com_cache` para um sujeito que o PEP negou seria o vazamento que
    o §9 nomeia — a negativa acontece antes, e nem chave se calcula.
    """
    cache = cache or Cache()
    fonte = adaptador.fonte
    carimbo = None
    if Fonte(fonte) != Fonte("acervo"):
        try:
            carimbo = adaptador._carimbo()
        except Exception:  # noqa: BLE001
            # Sem carimbo não há chave honesta: a leitura vai à fonte, sem cache.
            return adaptador.busca_declarada(alvo, filtros, k, texto), False

    ch = chave(fonte, carimbo, alvo, filtros, k, texto)
    guardado = cache.le(fonte, ch)
    if guardado is not None:
        return guardado, True

    cache._stat(fonte, "miss")
    r = adaptador.busca_declarada(alvo, filtros, k, texto)
    cache.grava(fonte, ch, r)
    return r, False
