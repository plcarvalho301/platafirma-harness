"""Leitura declarativa de registro/escrita.yaml e predicados de proteção da escrita."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .tipos import ErroEscrita, RecusaEscrita

_CONFIG_PADRAO = Path(__file__).resolve().parents[2] / "registro" / "escrita.yaml"
_NAO_EXECUTAVEIS = frozenset(
    {"README", "README.md", "VERDES", ".gitignore", "Dockerfile", "crontab-claudinho"}
)


@dataclass(frozen=True)
class PoliticaEscrita:
    """Configuração declarativa imutável carregada de registro/escrita.yaml."""

    versao: int
    entrada_max_bytes: int
    prazo_max_s: int
    retencao_repeticao_s: int
    espera_trava_passo_ms: int
    verbos_ligados: frozenset[str]
    nomes_vedados: frozenset[str]
    prefixos_nome_vedados: tuple[str, ...]
    sufixos_vedados: frozenset[str]
    segmentos_vedados: frozenset[str]
    prefixos_caminho_vedados: tuple[str, ...]
    caminhos_relativos_vedados: tuple[str, ...]
    caminhos_protegidos: dict[str, tuple[str, ...]]
    diretorios_executaveis: dict[str, tuple[str, ...]]


def _erro_politica(onde: str, recebido: str, cura: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="politica-indisponivel",
            onde=onde,
            recebido=recebido,
            regra="registro/escrita.yaml deve existir e declarar limites e listas válidas",
            cura=cura,
            proximo="",
        )
    )


def _int_positivo(mapa: dict[str, Any], chave: str, onde: str) -> int:
    valor = mapa.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise _erro_politica(
            f"{onde}.{chave}",
            repr(valor),
            f"declare inteiro positivo em {onde}.{chave}",
        )
    return valor


def _lista_texto(valor: Any, onde: str) -> tuple[str, ...]:
    if not isinstance(valor, list) or not all(isinstance(x, str) and x for x in valor):
        raise _erro_politica(onde, repr(valor), f"declare lista de strings em {onde}")
    return tuple(valor)


def _mapa_listas(valor: Any, onde: str) -> dict[str, tuple[str, ...]]:
    if not isinstance(valor, dict):
        raise _erro_politica(onde, repr(valor), f"declare mapa repositório -> lista em {onde}")
    return {
        str(repo): _lista_texto(itens, f"{onde}.{repo}")
        for repo, itens in valor.items()
    }


def caminho_politica_padrao() -> Path:
    """Resolve o caminho padrão de registro/escrita.yaml."""
    env = (os.environ.get("PF_ESCRITA_CONFIG") or "").strip()
    return Path(env) if env else _CONFIG_PADRAO


def carregar_politica(caminho: Path | None = None) -> PoliticaEscrita:
    """Lê e valida registro/escrita.yaml sem depender de banco vivo."""
    alvo = caminho_politica_padrao() if caminho is None else Path(caminho)
    try:
        bruto = alvo.read_text(encoding="utf-8")
    except OSError as exc:
        raise _erro_politica(
            str(alvo), str(exc), "confira o arquivo registro/escrita.yaml"
        ) from exc
    try:
        dados = yaml.safe_load(bruto)
    except yaml.YAMLError as exc:
        raise _erro_politica(
            str(alvo), str(exc), "corrija a sintaxe YAML de registro/escrita.yaml"
        ) from exc
    if not isinstance(dados, dict):
        raise _erro_politica(
            str(alvo),
            type(dados).__name__,
            "o topo de registro/escrita.yaml deve ser um objeto",
        )

    limites = dados.get("limites")
    vedadas = dados.get("superficies_vedadas")
    if not isinstance(limites, dict) or not isinstance(vedadas, dict):
        raise _erro_politica(
            str(alvo), "chaves ausentes", "declare limites e superficies_vedadas"
        )

    return PoliticaEscrita(
        versao=_int_positivo(dados, "versao", "raiz"),
        entrada_max_bytes=_int_positivo(limites, "entrada_max_bytes", "limites"),
        prazo_max_s=_int_positivo(limites, "prazo_max_s", "limites"),
        retencao_repeticao_s=_int_positivo(limites, "retencao_repeticao_s", "limites"),
        espera_trava_passo_ms=_int_positivo(limites, "espera_trava_passo_ms", "limites"),
        verbos_ligados=frozenset(_lista_texto(dados.get("verbos_ligados"), "verbos_ligados")),
        nomes_vedados=frozenset(
            _lista_texto(vedadas.get("nomes_arquivo"), "superficies_vedadas.nomes_arquivo")
        ),
        prefixos_nome_vedados=_lista_texto(
            vedadas.get("prefixos_nome"), "superficies_vedadas.prefixos_nome"
        ),
        sufixos_vedados=frozenset(
            _lista_texto(vedadas.get("sufixos_arquivo"), "superficies_vedadas.sufixos_arquivo")
        ),
        segmentos_vedados=frozenset(
            _lista_texto(vedadas.get("segmentos_caminho"), "superficies_vedadas.segmentos_caminho")
        ),
        prefixos_caminho_vedados=_lista_texto(
            vedadas.get("prefixos_caminho"), "superficies_vedadas.prefixos_caminho"
        ),
        caminhos_relativos_vedados=_lista_texto(
            vedadas.get("caminhos_relativos"), "superficies_vedadas.caminhos_relativos"
        ),
        caminhos_protegidos=_mapa_listas(dados.get("caminhos_protegidos"), "caminhos_protegidos"),
        diretorios_executaveis=_mapa_listas(
            dados.get("diretorios_executaveis"), "diretorios_executaveis"
        ),
    )


def _normalizar_rel(caminho: str) -> str:
    limpo = caminho.replace("\\", "/").strip()
    while limpo.startswith("./"):
        limpo = limpo[2:]
    return limpo.lstrip("/")


def _sob_prefixo(alvo: str, prefixo: str) -> bool:
    base = prefixo.rstrip("/")
    return alvo == base or alvo.startswith(base + "/")


def verbo_ligado(politica: PoliticaEscrita, verbo: str) -> bool:
    """Informa se o verbo já está ativado para usar o escritor único."""
    return verbo in politica.verbos_ligados


def eh_superficie_vedada(politica: PoliticaEscrita, caminho: str | Path) -> bool:
    """Predicado único de superfícies vedadas (segredos, política, trilha, fila, release, .git)."""
    bruto = str(caminho).replace("\\", "/")
    pp = PurePosixPath(bruto)
    nome = pp.name
    if nome in politica.nomes_vedados:
        return True
    if any(nome.startswith(pref) for pref in politica.prefixos_nome_vedados):
        return True
    if pp.suffix.lower() in politica.sufixos_vedados:
        return True
    if any(parte in politica.segmentos_vedados for parte in pp.parts):
        return True
    if any(_sob_prefixo(bruto, pref) for pref in politica.prefixos_caminho_vedados):
        return True
    rel = _normalizar_rel(bruto)
    if any(_sob_prefixo(rel, pref) for pref in politica.caminhos_relativos_vedados):
        return True
    return "/segredos/" in bruto or bruto.endswith("/segredos")


def eh_caminho_protegido(
    politica: PoliticaEscrita, repo: str, caminho_relativo: str
) -> bool:
    """Verifica se (repo, caminho_relativo) cai na lista de caminhos protegidos."""
    regras = politica.caminhos_protegidos.get(repo, ())
    rel = _normalizar_rel(caminho_relativo)
    for regra in regras:
        if regra.endswith("/"):
            if _sob_prefixo(rel, regra):
                return True
        elif rel == regra:
            return True
    return False


def eh_diretorio_executavel(
    politica: PoliticaEscrita, repo: str, caminho_relativo: str
) -> bool:
    """Verifica se (repo, caminho_relativo) mora em diretório de executáveis."""
    dirs = politica.diretorios_executaveis.get(repo, ())
    rel = _normalizar_rel(caminho_relativo)
    return any(_sob_prefixo(rel, d) for d in dirs)


def exige_shebang(
    politica: PoliticaEscrita, repo: str, caminho_relativo: str
) -> bool:
    """Informa se o arquivo em diretório de executáveis exige primeira linha `#!`."""
    if not eh_diretorio_executavel(politica, repo, caminho_relativo):
        return False
    pp = PurePosixPath(_normalizar_rel(caminho_relativo))
    if pp.name in _NAO_EXECUTAVEIS:
        return False
    return pp.suffix.lower() in ("", ".sh")
