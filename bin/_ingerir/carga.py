"""Carga da caixa de entrada e triagem inicial (#4120).

Fonte: story 4120 (Comportamento esperado itens 1-5).
- Cópia por `rclone copy` descendo em subpastas (rclone sync sai).
- Portão 1 compara o manifesto recursivo do rclone com todos os arquivos chegados.
- Itens endereçados na chegada por sha256 preservando pasta_origem como procedência.
- Arquivos .csv, .ods e .jsonl entram na lista de exceções como auxiliares (não somem em silêncio).
- Arquivo vazio, sem leitor e .json comum viram estado de exceção e nunca viram obra.
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_AUXILIAR_EXTS = (
    ".sidecar.json", ".sidecar.yaml", ".sidecar.yml",
    ".manifest", ".csv", ".jsonl", ".ods",
)
_AUXILIAR_NAMES = {
    "manifest.json", "manifest.yaml", "inventario.csv", "fila-lote.jsonl",
}
_FORMATOS_OBRA = (
    ".pdf", ".epub", ".docx", ".doc", ".md", ".txt",
    ".html", ".htm", ".mhtml", ".pptx", ".ppt", ".xlsx", ".xls",
)


def sha256_arquivo(caminho: str | Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def resolver_gdrive(caminho: str) -> str:
    c = caminho.strip()
    if c.startswith("gdrive:"):
        return c
    return f"gdrive:{c}"


def slug_origem(origem: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", origem.strip().lower()).strip("-")
    return s[:40] or "entrada"


def obter_manifesto_rclone(remote: str, timeout: int = 300) -> list[str]:
    """Obtém manifesto recursivo de arquivos via rclone lsf -R."""
    r = subprocess.run(
        ["rclone", "lsf", "-R", "--files-only", remote],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"rclone lsf falhou ({r.returncode}): {r.stderr.strip()}")
    itens = [l.strip().replace("\\", "/") for l in r.stdout.splitlines() if l.strip() and not l.strip().endswith("/")]
    return sorted(itens)


def conferir_manifesto_portao_1(manifesto: list[str], staging: str | Path) -> tuple[bool, str]:
    """Portão 1: compara manifesto recursivo do rclone com a árvore chegada."""
    staging_path = Path(staging)
    if not staging_path.is_dir():
        return False, f"PORTÃO 1: staging {staging} não é diretório"

    arquivos_staging: list[str] = []
    for raiz, dirs, arqs in os.walk(staging_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for a in arqs:
            if a.startswith("."):
                continue
            fp = Path(raiz) / a
            rel = fp.relative_to(staging_path).as_posix()
            arquivos_staging.append(rel)

    arquivos_staging.sort()
    manifesto_norm = sorted(manifesto)

    if len(manifesto_norm) != len(arquivos_staging):
        return (
            False,
            f"PORTÃO 1: contagem de rclone lsf ({len(manifesto_norm)}) diverge do staging ({len(arquivos_staging)}) — lote incompleto",
        )

    # Compara caminhos relativos
    if set(manifesto_norm) != set(arquivos_staging):
        dif_falta = set(manifesto_norm) - set(arquivos_staging)
        dif_sobra = set(arquivos_staging) - set(manifesto_norm)
        return (
            False,
            f"PORTÃO 1: arquivos divergentes entre rclone e staging (faltam: {len(dif_falta)}, sobram: {len(dif_sobra)})",
        )

    return True, f"PORTÃO 1 aprovado: {len(arquivos_staging)} arquivo(s) conferidos no staging"


def classificar_item_arquivo(nome: str, tamanho: int) -> tuple[str, str | None]:
    """Classifica o arquivo em: chegado, vazio, json_comum, sem_leitor ou auxiliar."""
    if tamanho == 0:
        return "vazio", "arquivo vazio (0 bytes); não é obra servível"

    low = nome.lower()
    base = Path(low).name

    if base in _AUXILIAR_NAMES or any(low.endswith(ext) for ext in _AUXILIAR_EXTS):
        return "auxiliar", "arquivo auxiliar ou planilha"

    if low.endswith(".json"):
        return "json_comum", "arquivo .json comum não é obra"

    if not any(low.endswith(ext) for ext in _FORMATOS_OBRA):
        return "sem_leitor", f"formato sem leitor suportado: {nome}"

    return "chegado", None


def itens_da_chegada(
    obras: list[dict[str, Any]],
    excecoes: list[dict[str, Any]],
    classificacoes: dict[str, dict] | None = None,
) -> list[dict[str, Any]]:
    """Os itens que a carga manda a `POST /acervo/chegada`: o que chegou e o que ficou de fora, cada um com o
    estado da triagem. A classificação da planilha vai presa ao sha256 do arquivo que ela descreve (item 3)."""
    classificacoes = classificacoes or {}
    itens: list[dict[str, Any]] = []
    for it in list(obras) + list(excecoes):
        item = {
            "sha256": it["sha256"], "nome": it["nome"], "pasta_origem": it.get("pasta_origem") or "",
            "tamanho": it["tamanho"], "estado": it["estado"],
        }
        classif = classificacoes.get(it.get("rel", "")) or classificacoes.get(it["nome"])
        if classif and it["estado"] == "chegado":
            item["classificacao"] = classif
        itens.append(item)
    return itens


def linhas_das_excecoes(excecoes: list[dict[str, Any]]) -> list[str]:
    """A lista do que a carga não fez obra (itens 4 e 5): vazio, sem leitor, .json comum e auxiliar (planilha,
    .jsonl, sidecar). Nada some em silêncio: cada um sai com o estado e a causa."""
    if not excecoes:
        return []
    linhas = ["Fora da carga (não viraram obra):"]
    for it in sorted(excecoes, key=lambda x: x.get("rel") or x["nome"]):
        motivo = it.get("motivo") or it["estado"]
        linhas.append(f"  [{it['estado']}] {it.get('rel') or it['nome']}: {motivo}")
    return linhas


def escanear_pasta_triagem(pasta: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict]]:
    """Escaneia pasta e subpastas separando obras válidas de exceções e sidecars."""
    pasta_path = Path(pasta)
    if pasta_path.is_file():
        sha = sha256_arquivo(pasta_path)
        sz = pasta_path.stat().st_size
        st, mot = classificar_item_arquivo(pasta_path.name, sz)
        item = {
            "rel": pasta_path.name,
            "caminho": str(pasta_path),
            "nome": pasta_path.name,
            "pasta_origem": "",
            "sha256": sha,
            "tamanho": sz,
            "estado": st,
            "motivo": mot,
        }
        if st == "chegado":
            return [item], [], {}
        return [], [item], {}

    sidecars: dict[str, dict] = {}
    obras: list[dict[str, Any]] = []
    excecoes: list[dict[str, Any]] = []

    for raiz, dirs, arqs in os.walk(pasta_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for a in sorted(arqs):
            if a.startswith("."):
                continue
            fp = Path(raiz) / a
            rel = fp.relative_to(pasta_path).as_posix()
            pasta_origem = Path(rel).parent.as_posix()
            if pasta_origem == ".":
                pasta_origem = ""

            sz = fp.stat().st_size
            sha = sha256_arquivo(fp)
            st, mot = classificar_item_arquivo(a, sz)

            info = {
                "rel": rel,
                "caminho": str(fp),
                "nome": a,
                "pasta_origem": pasta_origem,
                "sha256": sha,
                "tamanho": sz,
                "estado": st,
                "motivo": mot,
            }

            if st == "chegado":
                obras.append(info)
            else:
                excecoes.append(info)

    return obras, excecoes, sidecars
