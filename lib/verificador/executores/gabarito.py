"""gabarito — adaptador do verificador para o serviço de lint (card #4454)."""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from leitura.recusa import Recusa

from ..tipos import (
    SERVICO_LINT,
    AlvoVerificado,
    AmbienteVerificacao,
    ReguaCasada,
    VereditoItem,
)
from . import traduzir_apontamentos

_REGRA_GABARITO = "ato:verificar §Contra que régua e como ocorre o casamento?"


def _importar_servico_lint() -> Any:
    bin_dir = str(Path(__file__).resolve().parents[3] / "bin")
    if bin_dir not in sys.path:
        sys.path.insert(0, bin_dir)
    from _lint import servico

    return servico


def executar_gabarito(
    regua_casada: ReguaCasada,
    alvos: Sequence[AlvoVerificado],
    ambiente: AmbienteVerificacao,
) -> tuple[VereditoItem, ...]:
    """Aciona o serviço de lint diretamente no processo do verbo e traduz os vereditos."""
    if regua_casada.servico != SERVICO_LINT:
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="servico",
            recebido=regua_casada.servico,
            regra=_REGRA_GABARITO,
            cura=f"o serviço '{regua_casada.servico}' não possui adaptador determinístico nesta story",
        )

    servico = _importar_servico_lint()
    julgar_fn = ambiente.executor_lint or servico.julgar
    alvos_lint = [
        servico.AlvoLint(
            chave=a.chave,
            raiz=a.raiz,
            caminho=a.caminho,
            texto=a.texto,
            versao=a.versao,
        )
        for a in alvos
    ]

    try:
        vereditos_lint = julgar_fn(regua_casada.chaves, alvos_lint, prazo_s=ambiente.prazo_s)
    except servico.ErroServicoLint as exc:
        codigo = "sem-motor-deterministico" if exc.codigo == "sem-detector" else exc.codigo
        raise Recusa(
            exc.saida,
            codigo,
            onde="servico-lint",
            recebido=", ".join(regua_casada.chaves),
            regra=_REGRA_GABARITO,
            cura=exc.detalhe,
        ) from exc

    return tuple(
        VereditoItem(
            alvo=vl.alvo,
            resultado=vl.resultado,
            constatacao=vl.constatacao,
            apontamentos=traduzir_apontamentos(vl.apontamentos),
            modo=vl.modo,
            quesito=", ".join(regua_casada.chaves),
            motor=vl.motor,
            versao_servico=vl.versao_servico,
            versao_regua=vl.versao_regua,
            nao_julgados=tuple(vl.nao_julgados),
        )
        for vl in vereditos_lint
    )
