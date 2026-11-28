"""Resolução da senha do Valkey das sessões (`motor/MSG_MEM_SENHA`) pelo armário de chaves.

O armário é versionado no platafirma-core e servido pela release em
`$PLATAFIRMA_RELEASE/core/deploy/armario-de-chaves.yaml`; o schema pertence ao core
(`porta/configuracao.py`). Aqui o harness apenas resolve o caminho de
`motor/MSG_MEM_SENHA` no armário, lê o arquivo da senha na instância e a devolve
para os clientes do msg-mem autenticarem com `AUTH default <senha>`.
"""
from __future__ import annotations

import os
from pathlib import Path

SEGREDO_MSG_MEM = "motor/MSG_MEM_SENHA"
USUARIO_MSG_MEM = "default"


class SenhaIndisponivel(RuntimeError):
    """Armário ausente/ilegível ou arquivo de senha ausente/vazio."""


def _instancia(instancia_dir: Path | None = None) -> Path:
    if instancia_dir is not None:
        return Path(instancia_dir)
    return Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))


def _armario(core_dir: Path | None = None) -> Path:
    if core_dir is None:
        release = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
        core_dir = release / "core"
    return Path(core_dir) / "deploy" / "armario-de-chaves.yaml"


def _caminho_no_armario_stdlib(texto: str, nome_alvo: str) -> str | None:
    """Fallback em stdlib para ambientes sem PyYAML (ex.: Python do sistema)."""
    em_alvo = False
    for linha_bruta in texto.splitlines():
        linha = linha_bruta.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("- nome:"):
            nome = linha.split(":", 1)[1].strip().strip("\"'")
            em_alvo = nome == nome_alvo
            continue
        if em_alvo and linha.startswith("caminho:"):
            return linha.split(":", 1)[1].strip().strip("\"'")
    return None


def _extrair_caminho_yaml(texto: str, nome_alvo: str, armario_path: Path) -> str | None:
    try:
        import yaml
    except ImportError:
        return _caminho_no_armario_stdlib(texto, nome_alvo)
    try:
        dados = yaml.safe_load(texto)
    except Exception as exc:
        raise SenhaIndisponivel(f"armário inválido em {armario_path}: {exc}") from exc
    if not isinstance(dados, dict) or not isinstance(dados.get("segredos"), list):
        return None
    for item in dados["segredos"]:
        if isinstance(item, dict) and item.get("nome") == nome_alvo:
            val = item.get("caminho")
            if isinstance(val, str) and val.strip():
                return val.strip()
            break
    return None


def _caminho_no_armario(armario_path: Path, nome_alvo: str) -> str:
    if not armario_path.is_file():
        raise SenhaIndisponivel(f"armário de chaves ausente em {armario_path}")
    try:
        texto = armario_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SenhaIndisponivel(f"armário ilegível em {armario_path}: {exc}") from exc
    caminho = _extrair_caminho_yaml(texto, nome_alvo, armario_path)
    if not caminho:
        raise SenhaIndisponivel(
            f"segredo {nome_alvo} não declarado em {armario_path}"
        )
    return caminho


def ler_senha_msg_mem(
    instancia_dir: Path | None = None, *, core_dir: Path | None = None
) -> str:
    """Resolve `motor/MSG_MEM_SENHA` no armário do core e lê a senha na instância."""
    inst = _instancia(instancia_dir)
    armario = _armario(core_dir)
    rel = _caminho_no_armario(armario, SEGREDO_MSG_MEM)
    arq = Path(rel) if Path(rel).is_absolute() else inst / rel
    if not arq.is_file():
        raise SenhaIndisponivel(f"segredo {SEGREDO_MSG_MEM} ausente em {arq}")
    try:
        valor = arq.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SenhaIndisponivel(
            f"segredo {SEGREDO_MSG_MEM} ilegível em {arq}: {exc}"
        ) from exc
    if not valor:
        raise SenhaIndisponivel(f"segredo {SEGREDO_MSG_MEM} vazio em {arq}")
    return valor


def kwargs_redis_msg_mem(
    instancia_dir: Path | None = None, *, core_dir: Path | None = None
) -> dict[str, str]:
    """Devolve `username` e `password` para `redis.Redis` autenticar no msg-mem."""
    return {
        "username": USUARIO_MSG_MEM,
        "password": ler_senha_msg_mem(instancia_dir, core_dir=core_dir),
    }
