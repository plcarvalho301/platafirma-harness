"""Limpeza de sobras do bench de embedder (DT-787).

Remove duas sobras do bench (`motor medir --sombra`):
1. Pastas `/tmp/sombra-<id>` (com venv) no contêiner da instância quando a sombra já terminou
   (`fim` presente) ou caiu (`vivo` falso). Sombras em curso nunca são removidas.
2. Pesos de embedders no cache do Hugging Face (`edm_hf_models`) que nenhuma geração `servindo`
   ou `em_construcao` em `motor.geracao` usa, restrito aos embedders declarados no catálogo
   (nunca toca rerankers ou outros modelos fora de `embedders.toml`).
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

SID_RE = re.compile(r"^\d{8}T\d{6}$")


class ErroLimpeza(Exception):
    """Erro com código de saída explícito (tabela arq:0110 §4)."""

    def __init__(self, codigo: int, mensagem: str) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


@dataclass(frozen=True)
class ModeloCache:
    modelo: str
    pasta: Path
    bytes: int


def raiz_hf_cache() -> Path:
    """Resolve o diretório `hub` do cache Hugging Face (`edm_hf_models`)."""
    base = Path(
        os.environ.get("INFRA_HF_CACHE")
        or os.path.expanduser("~/.local/share/docker/volumes/edm_hf_models/_data")
    )
    hub = base / "hub"
    return hub if hub.is_dir() else base


def tamanho_dir(pasta: Path) -> int:
    """Soma em bytes dos arquivos regulares (ou alvos dos symlinks de snapshot)."""
    total = 0
    for raiz, _, arquivos in os.walk(pasta):
        for arq in arquivos:
            caminho = Path(raiz) / arq
            try:
                if caminho.is_symlink():
                    continue
                total += caminho.stat().st_size
            except OSError:
                pass
    return total


def selecionar_sombras(
    sombras: list[dict],
    sid: str | None = None,
) -> tuple[list[str], list[str]]:
    """Devolve `(apagar, em_curso)` a partir dos fatos lidos por `trabalhos.ler_sombras`."""
    em_curso = [
        s["id"]
        for s in sombras
        if s.get("fim") is None and s.get("vivo") and SID_RE.fullmatch(s.get("id") or "")
    ]
    if sid is not None:
        if not SID_RE.fullmatch(sid):
            raise ErroLimpeza(2, f"motor limpar: id de sombra invalido {sid!r} (forma AAAAMMDDTHHMMSS)")
        achada = next((s for s in sombras if s.get("id") == sid), None)
        if achada is None:
            raise ErroLimpeza(1, f"motor limpar: sombra {sid} nao existe no conteiner")
        if achada.get("fim") is None and achada.get("vivo"):
            raise ErroLimpeza(
                4,
                f"motor limpar: sombra {sid} esta em curso; pare antes com `motor rag parar biblioteca --sombra {sid}`",
            )
        return [sid], em_curso
    apagar = [
        s["id"]
        for s in sombras
        if (s.get("fim") is not None or not s.get("vivo")) and SID_RE.fullmatch(s.get("id") or "")
    ]
    return apagar, em_curso


def selecionar_modelos(
    hub: Path,
    em_uso: set[str],
    embedders_conhecidos: set[str],
    modelo: str | None = None,
) -> tuple[list[ModeloCache], list[str]]:
    """Devolve `(apagar, mantidos)` no cache HF, protegendo gerações em uso e não-embedders."""
    if not hub.is_dir():
        if modelo is not None:
            raise ErroLimpeza(1, f"motor limpar: cache Hugging Face ausente em {hub}")
        return [], []

    if modelo is not None:
        if modelo in em_uso:
            raise ErroLimpeza(
                4,
                f"motor limpar: modelo {modelo} esta em uso por geracao servindo ou em construcao",
            )
        if embedders_conhecidos and modelo not in embedders_conhecidos:
            raise ErroLimpeza(
                4,
                f"motor limpar: {modelo} nao esta no catalogo de embedders declarados (protegido)",
            )
        if not embedders_conhecidos and "reranker" in modelo.lower():
            raise ErroLimpeza(4, f"motor limpar: {modelo} e reranker (protegido)")
        pasta = hub / f"models--{modelo.replace('/', '--')}"
        if not pasta.is_dir():
            raise ErroLimpeza(1, f"motor limpar: modelo {modelo} nao encontrado no cache ({hub})")
        return [ModeloCache(modelo=modelo, pasta=pasta, bytes=tamanho_dir(pasta))], sorted(em_uso)

    apagar: list[ModeloCache] = []
    mantidos: list[str] = []
    for pasta in sorted(hub.glob("models--*")):
        if not pasta.is_dir():
            continue
        nome = pasta.name[len("models--") :].replace("--", "/", 1)
        if nome in em_uso or nome not in embedders_conhecidos:
            mantidos.append(nome)
            continue
        apagar.append(ModeloCache(modelo=nome, pasta=pasta, bytes=tamanho_dir(pasta)))
    return apagar, mantidos


def executar_limpeza(
    sombras_apagar: list[str],
    sombras_em_curso: list[str],
    modelos_apagar: list[ModeloCache],
    modelos_mantidos: list[str],
    hub: Path,
    apaga_sombra_fn,
    ver: bool = False,
) -> dict:
    """Executa (ou simula com `ver=True`) a remoção das sombras encerradas e pesos não usados."""
    if not ver:
        for sid in sombras_apagar:
            if not SID_RE.fullmatch(sid):
                raise ErroLimpeza(2, f"motor limpar: id de sombra invalido {sid!r}")
            apaga_sombra_fn(sid)
        for item in modelos_apagar:
            shutil.rmtree(item.pasta)
            lock = hub / ".locks" / item.pasta.name
            if lock.exists():
                shutil.rmtree(lock, ignore_errors=True)

    bytes_liberados = sum(m.bytes for m in modelos_apagar)
    return {
        "ver": ver,
        "sombras_apagadas": list(sombras_apagar),
        "sombras_em_curso": list(sombras_em_curso),
        "modelos_apagados": [{"modelo": m.modelo, "bytes": m.bytes} for m in modelos_apagar],
        "modelos_mantidos": list(modelos_mantidos),
        "bytes_liberados": bytes_liberados,
    }
