"""DT 522 (#2856 linha 522): todo contêiner Postgres de pé está em registro/bancos.json
ou declarado em _fora_da_casa com motivo.

No incidente #4185, `infra estado` listava nove Postgres enquanto `release migrar`
só alcançava cinco. Este teste protege o portão diário contra contêineres Postgres
subidos sem registro.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "registro" / "bancos.json"
MARCADORES_IMAGEM_PG = ("postgres", "pgvector", "postgis", "timescaledb")


def eh_imagem_postgres(imagem: str) -> bool:
    """Verdadeiro quando a imagem Docker é Postgres ou derivada declarada."""
    low = (imagem or "").lower()
    return any(m in low for m in MARCADORES_IMAGEM_PG)


def conteineres_cobertos(dados: dict) -> set[str]:
    """Contêineres registrados em bancos.json ou declarados em _fora_da_casa com motivo."""
    cobertos: set[str] = set()
    for chave, info in dados.items():
        if not chave.startswith("_") and isinstance(info, dict):
            nome = str(info.get("conteiner") or "").strip()
            if nome:
                cobertos.add(nome)

    fora = dados.get("_fora_da_casa")
    if isinstance(fora, dict):
        for chave, info in fora.items():
            if not isinstance(info, dict):
                continue
            motivo = str(info.get("motivo") or "").strip()
            if not motivo:
                continue
            nome = str(info.get("conteiner") or "").strip()
            if nome:
                cobertos.add(nome)
            elif not info.get("servico"):
                cobertos.add(chave)
    return cobertos


def conteineres_postgres_descobertos(conteineres: list[dict], dados: dict) -> list[dict]:
    """Retorna os contêineres de imagem Postgres que não estão cobertos pelo registro."""
    cobertos = conteineres_cobertos(dados)
    return [
        c
        for c in conteineres
        if eh_imagem_postgres(c.get("imagem", "")) and c.get("nome") not in cobertos
    ]


def test_conteiner_postgres_registrado_passa():
    dados = {"rag": {"conteiner": "rag-extractor-pg", "base": "rag_extractor", "dono": "rag"}}
    vivos = [
        {"nome": "rag-extractor-pg", "imagem": "pgvector/pgvector:pg16"},
        {"nome": "plataforma-wiki-db-1", "imagem": "mariadb:11.4"},
    ]
    assert conteineres_postgres_descobertos(vivos, dados) == []


def test_conteiner_postgres_fora_do_registro_falha():
    dados = {"rag": {"conteiner": "rag-extractor-pg", "base": "rag_extractor", "dono": "rag"}}
    vivos = [
        {"nome": "rag-extractor-pg", "imagem": "pgvector/pgvector:pg16"},
        {"nome": "banco-clandestino", "imagem": "postgres:16-alpine"},
    ]
    assert conteineres_postgres_descobertos(vivos, dados) == [
        {"nome": "banco-clandestino", "imagem": "postgres:16-alpine"}
    ]


def test_conteiner_postgres_em_fora_da_casa_exige_motivo():
    dados_com_motivo = {
        "_fora_da_casa": {
            "legado": {"conteiner": "pg-legado", "motivo": "migração pendente"}
        }
    }
    dados_sem_motivo = {
        "_fora_da_casa": {
            "legado": {"conteiner": "pg-legado", "motivo": "   "}
        }
    }
    vivos = [{"nome": "pg-legado", "imagem": "postgres:16"}]
    assert conteineres_postgres_descobertos(vivos, dados_com_motivo) == []
    assert conteineres_postgres_descobertos(vivos, dados_sem_motivo) == vivos


def test_conteineres_postgres_de_pe_estao_registrados():
    """Portão diário: todo contêiner de imagem Postgres de pé no host está em registro/bancos.json."""
    docker = shutil.which("docker") or ("/usr/bin/docker" if Path("/usr/bin/docker").exists() else None)
    if docker is None:
        pytest.skip("docker não instalado neste ambiente")
    proc = subprocess.run(
        [docker, "ps", "--format", "{{json .}}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if proc.returncode != 0:
        pytest.skip(f"daemon docker indisponível: {proc.stderr.strip()}")

    vivos = []
    for linha in proc.stdout.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        item = json.loads(linha)
        vivos.append({"nome": item.get("Names", ""), "imagem": item.get("Image", "")})

    dados = json.loads(REGISTRO.read_text(encoding="utf-8"))
    descobertos = conteineres_postgres_descobertos(vivos, dados)
    assert not descobertos, (
        "Contêiner(es) Postgres de pé fora de registro/bancos.json "
        f"(nem declarados em _fora_da_casa com motivo): {descobertos}"
    )
