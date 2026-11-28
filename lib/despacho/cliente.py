"""cliente — invocação por processo do ato `despachar` no core (card #4455, t6).

Cruza a fronteira do harness para o core por processo (`python -m porta.despachar.entrada`),
usando o python do venv da porta e a release no ar, sem importar nenhum módulo do core.
Quando o ponto de entrada do core está ausente ou não responde com contrato válido, levanta
`Recusa(3, "dependencia-sem-resposta", ...)`.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from leitura.recusa import Recusa

SAIDA_OK = 0
SAIDA_DEPENDENCIA = 3
SAIDA_MAX_TABELA = 5
PRAZO_ESPERA_PADRAO_S = 45.0
FOLGA_PROCESSO_S = 15.0
REGRA_FRONTEIRA_DESPACHAR = "ato:despachar §Fronteira entre harness e core"


@dataclass(frozen=True, slots=True)
class PedidoClienteDespacho:
    """Pedido serializado no `stdin` de `porta.despachar.entrada --stdin-json`."""

    verbo_entrada: str
    alvo_classe: str
    alvo_chave: str
    parametros: Mapping[str, Any] = field(default_factory=dict)
    ident: Mapping[str, Any] = field(default_factory=dict)
    pedido_id: str = ""
    fan_out: int = 1
    prazo_espera_s: float = PRAZO_ESPERA_PADRAO_S

    def como_dict(self) -> dict[str, Any]:
        return {
            "verbo_entrada": self.verbo_entrada,
            "alvo_classe": self.alvo_classe,
            "alvo_chave": self.alvo_chave,
            "parametros": dict(self.parametros),
            "ident": dict(self.ident),
            "pedido_id": self.pedido_id,
            "fan_out": self.fan_out,
            "prazo_espera_s": self.prazo_espera_s,
            "como_json": True,
        }


@dataclass(frozen=True, slots=True)
class RespostaClienteDespacho:
    """Retorno decodificado do processo `porta.despachar.entrada`."""

    exit_code: int
    execucao_id: str
    em_andamento: bool
    stdout: str
    stderr: str
    dados: Mapping[str, Any]
    proximo: str = ""


@dataclass(frozen=True, slots=True)
class ConfigClienteDespacho:
    """Caminhos e executor de processo injetáveis para o cliente do `despachar`."""

    python_porta: Path | None = None
    core_dir: Path | None = None
    release_dir: Path | None = None
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None
    env_extra: Mapping[str, str] = field(default_factory=dict)
    folga_processo_s: float = FOLGA_PROCESSO_S


def _resolver_caminhos_core(cfg: ConfigClienteDespacho) -> tuple[Path, Path]:
    release_raiz = cfg.release_dir or Path(
        os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current")
    )
    py_env = (os.environ.get("PF_PORTA_PYTHON") or "").strip()
    core_env = (os.environ.get("PF_CORE_DIR") or "").strip()
    py_porta = cfg.python_porta or (
        Path(py_env) if py_env else (release_raiz / "venv" / "porta" / "bin" / "python")
    )
    core_dir = cfg.core_dir or (Path(core_env) if core_env else (release_raiz / "core"))
    return py_porta, core_dir


def _decodificar_ultima_linha_json(texto: str) -> dict[str, Any] | None:
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    if not linhas:
        return None
    lido: Any = None
    with contextlib.suppress(ValueError):
        lido = json.loads(linhas[-1])
    return lido if isinstance(lido, dict) else None


def _ident_ambiente_padrao(ident: Mapping[str, Any]) -> dict[str, Any]:
    if ident:
        return dict(ident)
    return {
        "sujeito": os.environ.get("PF_SUJEITO") or "",
        "cadeira": os.environ.get("PF_CADEIRA") or "",
        "sessao_id": os.environ.get("PF_SESSAO") or "-",
        "ordem_id": os.environ.get("PF_ORDEM_ID") or "",
    }


def _levantar_sem_resposta(recebido: str, cura: str, causa: BaseException | None = None) -> None:
    recusa = Recusa(
        SAIDA_DEPENDENCIA,
        "dependencia-sem-resposta",
        onde="despachar",
        recebido=recebido,
        regra=REGRA_FRONTEIRA_DESPACHAR,
        cura=cura,
    )
    if causa is not None:
        raise recusa from causa
    raise recusa


def despachar_pelo_core(
    pedido: PedidoClienteDespacho,
    *,
    config: ConfigClienteDespacho | None = None,
) -> RespostaClienteDespacho:
    """Chama `porta.despachar.entrada --stdin-json` em processo filho e valida o retorno."""
    cfg = config or ConfigClienteDespacho()
    py_porta, core_dir = _resolver_caminhos_core(cfg)
    entrada_py = core_dir / "porta" / "despachar" / "entrada.py"

    if cfg.runner is None and (not py_porta.is_file() or not entrada_py.is_file()):
        _levantar_sem_resposta(
            f"python={py_porta} entrada={entrada_py}",
            "ponto de entrada porta.despachar.entrada ou venv da porta ausente na release no ar",
        )

    env_proc = dict(os.environ)
    py_path_atual = env_proc.get("PYTHONPATH", "").strip()
    env_proc["PYTHONPATH"] = f"{core_dir}:{py_path_atual}" if py_path_atual else str(core_dir)
    env_proc.update(cfg.env_extra)

    corpo_pedido = {**pedido.como_dict(), "ident": _ident_ambiente_padrao(pedido.ident)}
    payload = json.dumps(corpo_pedido, ensure_ascii=False)
    timeout_proc = max(1.0, float(pedido.prazo_espera_s) + float(cfg.folga_processo_s))
    executar_proc = cfg.runner or subprocess.run

    try:
        proc = executar_proc(
            [str(py_porta), "-m", "porta.despachar.entrada", "--stdin-json"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout_proc,
            check=False,
            env=env_proc,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _levantar_sem_resposta(
            f"{type(exc).__name__}: {exc}",
            "a porta/despachar não respondeu dentro da janela do processo",
            exc,
        )

    rc = int(proc.returncode)
    stdout_txt = proc.stdout or ""
    stderr_txt = proc.stderr or ""
    dados_out = _decodificar_ultima_linha_json(stdout_txt)
    dados_err = _decodificar_ultima_linha_json(stderr_txt)
    dados = dados_out if dados_out is not None else (dados_err or {})

    if rc < SAIDA_OK or rc > SAIDA_MAX_TABELA or not dados:
        _levantar_sem_resposta(
            stderr_txt.strip() or stdout_txt.strip() or f"returncode={rc}",
            "o processo porta.despachar.entrada encerrou sem envelope estruturado do contrato",
        )

    return RespostaClienteDespacho(
        exit_code=rc,
        execucao_id=str(dados.get("execucao_id") or ""),
        em_andamento=bool(dados.get("em_andamento", False)),
        stdout=stdout_txt,
        stderr=stderr_txt,
        dados=dados,
        proximo=str(dados.get("proximo") or ""),
    )
