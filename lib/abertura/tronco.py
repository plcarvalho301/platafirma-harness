"""Resolução do tronco do trabalho (processo e passo do card) pela Olaria.

Invocado pela porta (`core/porta/tronco.py`) por subprocesso via `python -m abertura tronco`.
Lê a propriedade `conduz` das fichas de `processo` e suas filhas na Olaria (a mesma fonte do
ponteiro de estágio), sem guardar tabela de estado -> processo no código.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any

_NIVEIS_POR_NUMERO: dict[int, str] = {
    0: "epico",
    1: "feature",
    2: "story",
    3: "task",
    4: "ideia",
}


def _limpo(valor: str) -> str:
    return valor.strip().strip("'\"")


def _normalizar_nivel(card: dict[str, Any]) -> str:
    nome = card.get("nivel_nome")
    if isinstance(nome, str) and nome.strip():
        n = nome.strip().lower()
        return "epico" if n == "épico" else n
    num = card.get("nivel")
    if isinstance(num, int):
        return _NIVEIS_POR_NUMERO.get(num, "")
    if isinstance(num, str) and num.strip().isdigit():
        return _NIVEIS_POR_NUMERO.get(int(num.strip()), "")
    return ""


def _normalizar_estado(card: dict[str, Any]) -> str:
    for campo in ("estado_mostrado", "estado_derivado", "estado"):
        val = card.get(campo)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    return ""


def _conduz_por_ficha(texto: str) -> dict[str, list[str]]:
    achados: dict[str, list[str]] = {}
    chave: str | None = None
    lista = False
    for linha in texto.splitlines():
        s = linha.strip()
        if linha.startswith("- chave:"):
            chave, lista = _limpo(linha.split(":", 1)[1]), False
        elif chave is None:
            continue
        elif s.startswith("conduz:"):
            resto = _limpo(s.split(":", 1)[1])
            achados.setdefault(chave, [])
            if resto:
                achados[chave].append(resto)
            lista = not resto
        elif lista and s.startswith("- "):
            achados[chave].append(_limpo(s[2:]))
        else:
            lista = False
    return achados


def _endereco_da_classe(texto: str) -> str:
    blocos: dict[str, str] = {}
    atual: str | None = None
    for linha in texto.splitlines():
        s = linha.strip()
        if linha in ("  golden:", "  referencia:"):
            atual = s[:-1]
        elif atual and linha.startswith("    "):
            if s.startswith("endereco:"):
                blocos.setdefault(atual, _limpo(s.split(":", 1)[1]))
        elif linha.startswith("  ") and not linha.startswith("   "):
            atual = None
    return blocos.get("golden") or blocos.get("referencia") or ""


def _infra_bin() -> str:
    expl = (os.environ.get("PF_INFRA_BIN") or "").strip()
    if expl:
        return expl
    candidato = Path(__file__).resolve().parents[2] / "bin" / "infra"
    if candidato.is_file():
        return str(candidato)
    release = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    return str(release / "harness" / "bin" / "infra")


def _rodar_ontologia(infra: str, args: list[str], fim: float) -> dict[str, Any]:
    restante = fim - time.monotonic()
    if restante <= 0:
        raise TimeoutError("teto")
    proc = subprocess.Popen(
        [infra, "rodar", "ontologia", "--", *args, "--json"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        start_new_session=True,
    )
    try:
        saida, _ = proc.communicate(timeout=restante)
    except BaseException:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        raise
    if proc.returncode != 0:
        raise RuntimeError(f"ontologia saiu {proc.returncode}")
    return json.loads(saida)


def resolver_tronco(
    card: dict[str, Any],
    *,
    chapeu: str | None = None,
    decisao_aposta: Any = None,
    prazo_s: float = 8.0,
) -> dict[str, Any]:
    """Resolve processo, passo e documento que conduzem o estágio do card."""
    _ = chapeu
    nivel = _normalizar_nivel(card)
    estado = _normalizar_estado(card)
    if not nivel or not estado:
        return {"processo": None, "passo": None, "sem_processo": True}

    alvo = f"{nivel}:{estado}"
    infra = _infra_bin()
    fim = time.monotonic() + max(0.5, float(prazo_s))
    try:
        filhas = _rodar_ontologia(infra, ["listar", "shape", "--filhas", "processo"], fim).get("chaves") or []
        classes = ["processo"] + [c for c in filhas if c != "processo"]
        with ThreadPoolExecutor(max_workers=max(1, len(classes))) as pool:
            lidas = list(
                pool.map(
                    lambda c: (c, _conduz_por_ficha(_rodar_ontologia(infra, ["ler", c, "--fichas"], fim).get("yaml") or "")),
                    classes,
                )
            )
        ligados = sorted(
            (c, k)
            for c, fichas in lidas
            for k, valores in fichas.items()
            if alvo in valores
        )
        if not ligados:
            return {"processo": None, "passo": None, "sem_processo": True}
        classe, chave = ligados[0]
        endereco = _endereco_da_classe(
            _rodar_ontologia(infra, ["ler", "shape", classe], fim).get("yaml") or ""
        )
        slug = chave.split(":", 1)[-1]
        documento = endereco.replace("<slug>", slug) if endereco else None
        aposta = decisao_aposta if decisao_aposta is not None else card.get("decisao_aposta")
        return {
            "processo": chave,
            "passo": estado,
            "estagio": alvo,
            "documento": documento,
            "aposta_fechada": bool(aposta),
            "sem_processo": False,
        }
    except Exception:  # noqa: BLE001
        return {"processo": None, "passo": None, "sem_processo": True}
