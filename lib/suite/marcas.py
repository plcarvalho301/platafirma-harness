"""Plugin pytest da suíte que registra as marcas `exige` e `incidente` e filtra casos com ambiente na fita."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_CONTAGEM_SESSAO: dict[str, int] = {
    "rodados": 0,
    "aprovados": 0,
    "reprovados": 0,
    "fora_exige": 0,
}


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        "exige(chave): caso que exige uma entidade de ambiente (serviço, modelo, embedder ou host).",
    )
    config.addinivalue_line(
        "markers",
        "incidente(numero): caso que reproduz um incidente fechado.",
    )
    config._suite_contagem = {
        "rodados": 0,
        "aprovados": 0,
        "reprovados": 0,
        "fora_exige": 0,
    }


def pytest_sessionstart(session: Any) -> None:
    _CONTAGEM_SESSAO["rodados"] = 0
    _CONTAGEM_SESSAO["aprovados"] = 0
    _CONTAGEM_SESSAO["reprovados"] = 0
    _CONTAGEM_SESSAO["fora_exige"] = 0


def pytest_collection_modifyitems(session: Any, config: Any, items: list[Any]) -> None:
    sem_exige = os.environ.get("PF_SUITE_SEM_EXIGE") == "1"
    if not sem_exige:
        return
    mantidos: list[Any] = []
    fora: list[Any] = []
    for item in items:
        if item.get_closest_marker("exige") is not None:
            fora.append(item)
        else:
            mantidos.append(item)
    if fora:
        config.hook.pytest_deselected(items=fora)
        items[:] = mantidos
    _CONTAGEM_SESSAO["fora_exige"] = len(fora)
    contagem = getattr(config, "_suite_contagem", None)
    if isinstance(contagem, dict):
        contagem["fora_exige"] = len(fora)


def pytest_runtest_logreport(report: Any) -> None:
    if report.when == "call":
        _CONTAGEM_SESSAO["rodados"] += 1
        if report.passed:
            _CONTAGEM_SESSAO["aprovados"] += 1
        elif report.failed:
            _CONTAGEM_SESSAO["reprovados"] += 1
    elif report.when == "setup" and report.failed:
        _CONTAGEM_SESSAO["rodados"] += 1
        _CONTAGEM_SESSAO["reprovados"] += 1


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    contagem_cfg = getattr(session.config, "_suite_contagem", {}) or {}
    fora_exige = contagem_cfg.get("fora_exige", _CONTAGEM_SESSAO["fora_exige"])
    rel = os.environ.get("PF_SUITE_RELATORIO")
    if rel:
        dados = {
            "rodados": _CONTAGEM_SESSAO["rodados"],
            "aprovados": _CONTAGEM_SESSAO["aprovados"],
            "reprovados": _CONTAGEM_SESSAO["reprovados"],
            "fora_exige": fora_exige,
            "exitstatus": int(exitstatus),
        }
        try:
            Path(rel).write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
