"""Suíte de verificação de fronteira, vínculo, seleção, admissão e eficácia por mutação."""
from __future__ import annotations

import importlib

_EXPORTS = {
    "DubleOlaria": "suite.admissao",
    "EnsaiadorOlaria": "suite.admissao",
    "OlariaIndisponivelErro": "suite.admissao",
    "RecusaAdmissao": "suite.admissao",
    "ResultadoAdmissao": "suite.admissao",
    "admitir": "suite.admissao",
    "ContratoErro": "suite.contrato",
    "VerificacaoContratoErro": "suite.contrato",
    "ler_copia": "suite.contrato",
    "ler_openapi": "suite.contrato",
    "trazer": "suite.contrato",
    "verificar_fornecedor": "suite.contrato",
    "gerar_duble": "suite.duble",
    "ApontamentoTeste": "suite.executor",
    "ErroExecutorTestes": "suite.executor",
    "OpcoesExecucaoTeste": "suite.executor",
    "VereditoTeste": "suite.executor",
    "julgar_ficha": "suite.executor",
    "ErroLaudoSuite": "suite.motor",
    "LaudoSuite": "suite.motor",
    "julgar_laudo": "suite.motor",
    "MAX_MUTANTES_POR_LINHA": "suite.mutacao",
    "MedidaComponente": "suite.mutacao",
    "MutacaoErro": "suite.mutacao",
    "Mutante": "suite.mutacao",
    "ResultadoCaso": "suite.mutacao",
    "formatar_relatorio": "suite.mutacao",
    "gerar_mutantes_arquivo": "suite.mutacao",
    "medir_componente": "suite.mutacao",
    "ResultadoSelecao": "suite.selecao",
    "descobrir_arquivos_teste": "suite.selecao",
    "selecionar": "suite.selecao",
    "CasoTeste": "suite.vinculo",
    "VinculoArquivo": "suite.vinculo",
    "deduzir_classe": "suite.vinculo",
    "extrair_slug_componente": "suite.vinculo",
    "ler_cabecalho": "suite.vinculo",
    "ler_vinculo": "suite.vinculo",
    "normalizar_componente": "suite.vinculo",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str):
    mod_name = _EXPORTS.get(name)
    if mod_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod = importlib.import_module(mod_name)
    val = getattr(mod, name)
    globals()[name] = val
    return val
