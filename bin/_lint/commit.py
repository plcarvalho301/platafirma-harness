"""commit — verificacao de mensagens de commit contra o rastreador (F9 / arq:0096)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .resultado import Apontamento

DECLARACAO_DE_COMMIT = ".conferir-commit"
BASE_RASTREADOR = os.environ.get("PF_RASTREADOR_BASE", "http://127.0.0.1:8120")
TIMEOUT_RASTREADOR = 3.0


def declaracao_de_commit(raiz: Path) -> Optional[dict]:
    caminho = raiz / DECLARACAO_DE_COMMIT
    if not caminho.is_file():
        return None
    config = {"base": BASE_RASTREADOR, "timeout": TIMEOUT_RASTREADOR}
    try:
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            linha = linha.split("#", 1)[0].strip()
            if not linha or ":" not in linha:
                continue
            k, v = [x.strip() for x in linha.split(":", 1)]
            if k == "base" and v:
                config["base"] = v.rstrip("/")
            elif k == "timeout" and v:
                try:
                    config["timeout"] = float(v)
                except ValueError:
                    pass
    except OSError:
        pass
    return config


def pergunta_ao_rastreador(base: str, mensagem: str, timeout: float = TIMEOUT_RASTREADOR) -> tuple[Optional[dict], Optional[str]]:
    url = f"{base}/commits/conferir"
    corpo = json.dumps({"mensagem": mensagem}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=corpo,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        corpo_err = e.read().decode("utf-8", errors="replace")[:200]
        return None, f"rastreador em {url} respondeu HTTP {e.code}: {corpo_err}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, f"nao consegui falar com o rastreador em {url}: {e}"
    except ValueError as e:
        return None, f"resposta do rastreador em {url} nao e JSON valido: {e}"


def verificar_commit(
    raiz: Path | str,
    alvo: str = "-",
    texto_mensagem: Optional[str] = None,
) -> list[Apontamento]:
    """Verifica se mensagem de commit cita IDs validos e abertos no rastreador."""
    raiz = Path(raiz)
    if texto_mensagem is not None:
        mensagem = texto_mensagem
    elif alvo == "-":
        mensagem = sys.stdin.read()
    else:
        caminho = Path(alvo) if Path(alvo).is_absolute() else (raiz / alvo)
        try:
            mensagem = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return [
                Apontamento(
                    str(alvo),
                    1,
                    f"nao consegui ler arquivo de mensagem: {e}",
                    "fornecer arquivo legivel ou usar '-' para ler de stdin",
                    severidade="bloqueante",
                )
            ]

    # Se repo tiver declaracao de commit, usa config
    decl = declaracao_de_commit(raiz)
    base = decl["base"] if decl else BASE_RASTREADOR
    timeout = decl["timeout"] if decl else TIMEOUT_RASTREADOR

    veredito, erro = pergunta_ao_rastreador(base, mensagem, timeout)
    if veredito is None:
        # Rastreador fora do ar: fail-open com aviso
        return []

    apontamentos: list[Apontamento] = []
    recusas = veredito.get("recusas") or []
    avisos = veredito.get("avisos") or []

    for r in recusas:
        item_id = r.get("id", "?")
        texto_recusa = r.get("texto") or f"item #{item_id} invalido ou fechado"
        apontamentos.append(
            Apontamento(
                str(alvo),
                1,
                f"recusa do rastreador: {texto_recusa}",
                f"corrigir ou remover a citacao #{item_id} no commit",
                severidade="bloqueante",
                id="ID_RECUSADO",
            )
        )

    for a in avisos:
        texto_aviso = a.get("texto", str(a))
        apontamentos.append(
            Apontamento(
                str(alvo),
                1,
                f"aviso do rastreador: {texto_aviso}",
                "revisar citacao de card no commit",
                severidade="aviso",
                id="ID_AVISO",
            )
        )

    return apontamentos
