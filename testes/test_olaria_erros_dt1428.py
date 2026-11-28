# componente: componente:escrita
"""Regressão do DT 1428: propagação integral de recusas da Olaria."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from escrita.moradas import ExecucaoMorada
from escrita.moradas.olaria import (
    ConfigOlaria,
    MoradaOlaria,
    RespostaHTTP,
)
from escrita.politica import carregar_politica
from escrita.portao import DecisaoPortao
from escrita.resolucao import AlvoResolvido
from escrita.tipos import (
    AlvoEscrita,
    ContextoEscrita,
    PedidoEscrita,
    RecusaEscrita,
)


def _execucao_ensaio(versao: str = "019a0000-0000-7000-8000-000000000001") -> ExecucaoMorada:
    pedido = PedidoEscrita(
        verbo="casa",
        forma="ensaiar",
        chave="shape:motor",
        classe="shape",
        forma_ensaiada="trocar",
        versao=versao,
        conteudo="classes:\n- slug: motor\n  _remendo: true\n",
        pedido="019a0000-0000-7000-8000-000000000099",
        contexto=ContextoEscrita(verbo="casa", cadeira="engenharia", sujeito="engenharia"),
    )
    decisao = DecisaoPortao(
        verbo="casa",
        classe="shape",
        forma="ensaiar",
        regime="guardada",
        morada="banco",
        sujeito="engenharia",
        cadeira="engenharia",
        conta_par="engenharia",
        uid_par=1000,
        gid_par=1000,
        pid_par=1,
    )
    alvo = AlvoResolvido(
        alvo=AlvoEscrita(
            classe="shape",
            chave="shape:motor",
            regime="guardada",
            morada="banco",
            endereco="shape:motor",
        )
    )
    return ExecucaoMorada(
        pedido=pedido,
        decisao=decisao,
        alvo=alvo,
        politica=carregar_politica(RAIZ / "registro" / "escrita.yaml"),
        release="test-release",
        registro=None,
        prazo_ns=0,
    )


def test_olaria_versao_diferente_chega_inteiro_e_mapeado() -> None:
    v_lida = "019a0000-0000-7000-8000-000000000001"
    v_atual = "019a0000-0000-7000-8000-000000000002"

    def _stub(_url, _rota, _hdrs, _corpo, _timeout):
        return RespostaHTTP(
            422,
            {
                "estado": "recusada",
                "total": 1,
                "erros": [
                    {
                        "codigo": "versao-diferente",
                        "onde": "/classes/0/versao",
                        "recebido": v_lida,
                        "regra": "A versão lida coincide com a gravada.",
                        "cura": f"A versão atual de motor é {v_atual}.",
                        "proximo": "ontologia ler shape motor",
                    }
                ],
            },
        )

    morada = MoradaOlaria(ConfigOlaria(url="http://127.0.0.1:1", chave="k"), transporte=_stub)
    with pytest.raises(RecusaEscrita) as exc:
        morada.executar(_execucao_ensaio(v_lida))

    assert exc.value.saida == 2
    err = exc.value.primeiro
    assert err.codigo == "versao-divergente"
    assert err.onde == "/classes/0/versao"
    assert err.recebido == v_lida
    assert err.regra == "A versão lida coincide com a gravada."
    assert err.cura == f"A versão atual de motor é {v_atual}."
    assert err.proximo == "ontologia ler shape motor"


def test_olaria_preserva_multiplos_erros_e_codigo_fora_do_mapa() -> None:
    def _stub(_url, _rota, _hdrs, _corpo, _timeout):
        return RespostaHTTP(
            422,
            {
                "estado": "recusada",
                "erros": [
                    {
                        "codigo": "versao-diferente",
                        "onde": "/classes/0/versao",
                        "recebido": "v1",
                        "regra": "versao-bate",
                        "cura": "releia motor",
                        "proximo": "busca ler shape:motor",
                    },
                    {
                        "codigo": "campo-desconhecido",
                        "onde": "/classes/1/foo",
                        "recebido": "bar",
                        "regra": "campo-na-gramatica",
                        "cura": "remova foo",
                        "proximo": "",
                    },
                ],
            },
        )

    morada = MoradaOlaria(ConfigOlaria(url="http://127.0.0.1:1", chave="k"), transporte=_stub)
    with pytest.raises(RecusaEscrita) as exc:
        morada.executar(_execucao_ensaio())

    assert len(exc.value.erros) == 2
    assert exc.value.erros[0].codigo == "versao-divergente"
    assert exc.value.erros[1].codigo == "chave-invalida"
    assert exc.value.erros[1].onde == "/classes/1/foo"
    assert exc.value.erros[1].recebido == "bar"
    assert "campo-desconhecido" in exc.value.erros[1].regra
    assert exc.value.erros[1].cura == "remova foo"
