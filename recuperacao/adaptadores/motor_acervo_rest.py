"""Cliente HTTP das rotas de CATÁLOGO do `motor_acervo` (#2957, arq:0089/0090).

Distinto de `AdaptadorAcervo` (fala com o arquétipo CONSULTA — `/acervo/trechos/consulta`
e as facetas, via a classe `Adaptador`, com carimbo memoizado por sessão): este módulo
fala com as rotas de GOLDEN RECORD do mesmo `motor_acervo` — situação e descoberta.
`situacao.py` e `descobrir.py` chamam por aqui em vez de ler `ontologia/acervo/*.jsonl`
do disco, que era o que `acervo_leitor.py::carrega_catalogo` fazia (arq:0085 §4 — retrato,
não vivo). O módulo foi removido; a escada de degraus e o casamento de obra por
título/arquivo moraram para `motor_acervo/acervo_consulta.py`, do outro lado do HTTP.

Funções, não classe: as duas rotas não compartilham estado entre chamadas — nenhum
carimbo de sessão a memoizar aqui. `http=` é o ponto de injeção que os testes usam para
não sair à rede, no mesmo desenho de `AdaptadorAcervo.__init__(http=...)`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from ..envelope import Causa
from .base import FonteIndisponivel

BASE = os.environ.get("MOTOR_ACERVO_URL", os.environ.get("RAG_API_URL", "http://127.0.0.1:8100")).rstrip("/")
TOKEN = os.environ.get("RAG_API_TOKEN", "")
TIMEOUT_S = float(os.environ.get("RAG_TIMEOUT_S", "10"))


def _chama_real(rota: str, *, aceita_ausente: bool = False) -> dict | None:
    req = urllib.request.Request(
        f"{BASE}{rota}",
        headers={**({"authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if aceita_ausente and e.code == 404:
            return None
        corpo = e.read()[:200].decode(errors="replace")
        if e.code in (401, 403):
            raise FonteIndisponivel(Causa.SEM_CONCESSAO, corpo) from e
        if e.code == 503:                          # fonte aquecendo ou Postgres fora do ar
            raise FonteIndisponivel(Causa.FORA_DO_AR, corpo or "fonte indisponivel") from e
        raise FonteIndisponivel(Causa.FORA_DO_AR, f"HTTP {e.code}: {corpo}") from e
    except (urllib.error.URLError, OSError) as e:
        raise FonteIndisponivel(Causa.SEM_ROTA, f"{BASE}: {e}") from e
    except TimeoutError as e:
        raise FonteIndisponivel(Causa.TIMEOUT, BASE) from e
    except ValueError as e:
        raise FonteIndisponivel(Causa.FORA_DO_AR, "resposta não é JSON") from e


def situacao_obra(obra: str, *, http=None) -> dict | None:
    """`GET /acervo/obras/{obra_id}/situacao`. `None` = a API respondeu 404 (obra
    inexistente) — vira envelope vazio no chamador, nunca falha."""
    chamador = http or _chama_real
    return chamador(f"/acervo/obras/{urllib.parse.quote(obra, safe='')}/situacao",
                    aceita_ausente=True)


def descoberta(assunto: str, eixos: list[str], k: int, *, http=None) -> dict:
    """`GET /acervo/descoberta?assunto=&eixo=...&k=...`."""
    chamador = http or _chama_real
    qs = urllib.parse.urlencode({"assunto": assunto, "k": k})
    qs += "".join(f"&eixo={urllib.parse.quote(e)}" for e in eixos)
    return chamador(f"/acervo/descoberta?{qs}")


def conceitos(*, http=None) -> dict:
    """`GET /acervo/conceitos` — coleção `{itens, proximo}` do golden record."""
    chamador = http or _chama_real
    return chamador("/acervo/conceitos")
