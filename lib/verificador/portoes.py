"""portoes — os dois portões do verbo (`aceita` e `alcanca`) sobre a vista de alcance (card #4454).

O verificador não consulta o ponto de decisão de acesso nem cria escopo próprio:
o acesso ao ato é o acesso de leitura ao verbo que o integra, já decidido pela porta.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml
from leitura.recusa import Recusa

from .tipos import PedidoVerificacao, VistaVerificar

_RAIZ_VISTA = Path(__file__).resolve().parents[2] / "registro" / "vista-alcance.yaml"
_REGRA_PORTOES = "ato:verificar §Contra que régua e como ocorre o casamento?"


def carregar_vista_verificar(caminho: Path | None = None) -> VistaVerificar:
    """Lê o bloco `verificar` da vista de alcance compilada na release."""
    arq = caminho or _RAIZ_VISTA
    try:
        bruto = yaml.safe_load(arq.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="vista-alcance",
            recebido=str(arq),
            regra=_REGRA_PORTOES,
            cura=f"não foi possível ler a vista de alcance ({exc})",
        ) from exc

    if not isinstance(bruto, Mapping) or not isinstance(bruto.get("verificar"), Mapping):
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="vista-alcance",
            recebido=str(arq),
            regra=_REGRA_PORTOES,
            cura="bloco `verificar` ausente ou mal formado em registro/vista-alcance.yaml",
        )

    bloco = bruto["verificar"]
    verbos_aceitam: set[str] = set()
    alcance_por_verbo: dict[str, frozenset[str]] = {}

    for nome_verbo, cfg in bloco.items():
        if not isinstance(cfg, Mapping):
            raise Recusa(
                3,
                "dependencia-sem-resposta",
                onde="vista-alcance",
                recebido=str(nome_verbo),
                regra=_REGRA_PORTOES,
                cura="entrada mal formada no bloco `verificar` de registro/vista-alcance.yaml",
            )
        verbo = str(nome_verbo).strip().lower()
        if cfg.get("aceita"):
            verbos_aceitam.add(verbo)
        classes = cfg.get("alcanca") or []
        if not isinstance(classes, list):
            raise Recusa(
                3,
                "dependencia-sem-resposta",
                onde="vista-alcance",
                recebido=verbo,
                regra=_REGRA_PORTOES,
                cura="campo `alcanca` deve ser lista no bloco `verificar`",
            )
        alcance_por_verbo[verbo] = frozenset(str(c).strip() for c in classes if str(c).strip())

    return VistaVerificar(
        verbos_aceitam=frozenset(verbos_aceitam),
        alcance_por_verbo=alcance_por_verbo,
    )


def classe_da_chave(chave: str) -> str:
    """Extrai a classe de uma chave canônica `<classe>:<slug>`."""
    return chave.split(":", 1)[0].strip()


def conferir_portoes(pedido: PedidoVerificacao, vista: VistaVerificar) -> str:
    """Confere `aceita` e `alcanca` do verbo para os alvos do pedido e devolve a classe única."""
    if pedido.verbo not in vista.verbos_aceitam:
        raise Recusa(
            2,
            "ato-nao-aceito",
            onde="verbo",
            recebido=pedido.verbo,
            regra=_REGRA_PORTOES,
            cura=f"o verbo '{pedido.verbo}' não declara ligação aceita para ato:verificar",
            proximo="casa verificar <alvo> --regua <regua>",
        )

    alcance = vista.alcance_por_verbo.get(pedido.verbo, frozenset())
    classes: list[str] = []
    for alvo in pedido.alvos:
        classe = classe_da_chave(alvo)
        if "*" not in alcance and classe not in alcance:
            raise Recusa(
                1,
                "classe-fora-do-verbo",
                onde="alvo",
                recebido=alvo,
                regra=_REGRA_PORTOES,
                cura=f"o verbo '{pedido.verbo}' não alcança a classe '{classe}'",
                proximo=f"{pedido.verbo} verificar <alvo-alcançado>",
            )
        if classe not in classes:
            classes.append(classe)

    if len(classes) > 1:
        raise Recusa(
            2,
            "regua-incompativel",
            onde="alvo",
            recebido=", ".join(pedido.alvos),
            regra=_REGRA_PORTOES,
            cura="múltiplos alvos na mesma chamada devem pertencer à mesma classe",
            proximo=f"{pedido.verbo} verificar <alvo> --regua <regua>",
        )

    return classes[0]
