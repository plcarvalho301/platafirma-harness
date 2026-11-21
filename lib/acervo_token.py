"""Resolução de `RAG_API_TOKEN` pelo ambiente ou pelo armário de chaves da release (regra 4406.r2).

A porta não carrega `EnvironmentFile` nem repassa segredos no ambiente dos verbos filhos
(4406.r2, DT 933). Os clientes HTTP da API do acervo resolvem o token por aqui:
  1. `RAG_API_TOKEN` no ambiente (vale mais — testes e terminal via `bin/pf`);
  2. primeiro segredo legível declarado em `$PLATAFIRMA_RELEASE/core/deploy/armario-de-chaves.yaml`,
     resolvido sob `$PLATAFIRMA_INSTANCIA`, na ordem `acervo-guarda/RAG_API_TOKEN`,
     `rag/RAG_API_TOKEN`, `busca/RAG_API_TOKEN`, `conhecimento/RAG_API_TOKEN`.
Sem ambiente nem armário legível, devolve `""` sem levantar exceção.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from lib import memoria_de_trabalho as _armario_mod
except ImportError:
    import memoria_de_trabalho as _armario_mod  # type: ignore[no-redef]

SEGREDOS_TOKEN_ACERVO = (
    "acervo-guarda/RAG_API_TOKEN",
    "rag/RAG_API_TOKEN",
    "busca/RAG_API_TOKEN",
    "conhecimento/RAG_API_TOKEN",
)


def ler_token_acervo(
    *,
    instancia_dir: Path | None = None,
    core_dir: Path | None = None,
) -> str:
    """Lê `RAG_API_TOKEN` do ambiente ou, sem ele, do armário de chaves da release."""
    do_env = os.environ.get("RAG_API_TOKEN", "").strip()
    if do_env:
        return do_env
    instancia = _armario_mod._instancia(instancia_dir)
    armario = _armario_mod._armario(core_dir)
    if not armario.is_file():
        return ""
    for nome in SEGREDOS_TOKEN_ACERVO:
        try:
            rel = _armario_mod._caminho_no_armario(armario, nome)
        except _armario_mod.SenhaIndisponivel:
            continue
        arq = Path(rel) if Path(rel).is_absolute() else instancia / rel
        try:
            valor = arq.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if valor:
            return valor
    return ""
