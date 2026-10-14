"""A chamada ao rag-api que o `motor` repete em mais de um ato (card #3513).

O ajuste da geração e os trabalhos falam com as rotas `/motor/...` da #3510; a lista de trabalhos
também serve a recusa do ajuste. Aqui mora só o transporte: JSON de ida e de volta, e o erro da API
traduzido para o código de saída da tabela da casa (400 → 2, 404 → 1, 409 → 4, o resto → 3).
`Falha` leva o código e a mensagem; quem chama decide se imprime e sai (`motor`) ou se segue (leitura
que pode dizer «não consegui olhar»).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

_EXIT_DA_API = {400: 2, 404: 1, 409: 4, 422: 1}


class Falha(Exception):
    """A API não respondeu ou recusou. `codigo` é o exit do verbo; `mensagem` já diz a causa."""

    def __init__(self, codigo: int, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


def _detalhe(e: urllib.error.HTTPError) -> str:
    try:
        bruto = e.read(2000).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — a causa é best-effort; o código HTTP já diz o essencial
        return str(e.reason or "")
    try:
        pj = json.loads(bruto)
        if isinstance(pj, dict) and (pj.get("title") or pj.get("detail")):
            return ": ".join(str(x) for x in (pj.get("title"), pj.get("detail")) if x)
    except ValueError:
        pass
    return bruto.strip()[:200] or str(e.reason or "")


def chamar(url: str, tok: str, corpo: dict | None = None, *, metodo: str | None = None,
           consulta: dict | None = None, timeout: float = 60) -> dict:
    """GET (sem corpo) ou POST/PUT (com corpo) em `url`, com o token da instância. Devolve o JSON."""
    if consulta:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(consulta)
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode() if corpo is not None else None, method=metodo,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise Falha(_EXIT_DA_API.get(e.code, 3), f"HTTP {e.code} — {_detalhe(e)}") from None
    except urllib.error.URLError as e:
        raise Falha(3, f"erro de rede — {e.reason}") from None
    except (OSError, ValueError) as e:
        raise Falha(3, f"sem resposta legível — {type(e).__name__}: {e}") from None
