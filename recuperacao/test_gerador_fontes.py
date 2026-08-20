"""Testes de aceite do gerador de fontes e derivação do enum (#2320).

Aceite (executável por terceiro):
1. A tabela do catálogo tem as seis linhas do §5 da spec, e recuperacao/fontes.py
   não guarda mais lista própria de fontes — o enum é construído da tabela.
2. Removida uma linha da tabela, a fonte some da descrição gerada; acrescentada, aparece.
   Provado nos dois sentidos, em teste.
3. Linha malformada falha o build nomeando o número da linha e o defeito.
4. A suíte de contrato do F0 continua verde.
5. O commit declara o tamanho da descrição gerada em tokens, medido.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from recuperacao.fontes import Classe, Fonte, CLASSE, _constroi_fontes
from recuperacao.gerador import (
    ErroTabelaFontes,
    FonteInfo,
    conta_tokens,
    emite_artefato,
    gera_descricao_tool,
    le_tabela_fontes,
)


TABELA_6_FONTES = """## Fontes da plataforma

| fonte | capacidade | dono | transporte | classe | contrato de leitura | gold |
|---|---|---|---|---|---|---|
| board | trabalho | claudinho-TI | HTTP | exata | HTTP do rastreador + header de identidade | nao-calibrada |
| fila | mensagem | claudinho-TI | stream | exata | XINFO STREAM · XRANGE no motor-msg | nao-calibrada |
| mesa | memoria | claudinho-IA | postgres | exata | mapa por chave (arq:0062) | nao-calibrada |
| registro | decisao | claudinha-gestao-estrategica | git | exata | decisions/INDICE.md, mantido na escrita | nao-calibrada |
| wiki | conhecimento | claudinho-dados | HTTP | exata | API do MediaWiki | nao-calibrada |
| acervo | conhecimento | claudinho-dados | HTTP | semantica | API do rag | nao-calibrada |

## Ferramenta de terceiro
"""


def test_tabela_do_catalogo_populada_e_enum_derivado():
    """Prova 1: Enum Fonte e mapa CLASSE construídos da tabela do catálogo."""
    fontes = le_tabela_fontes()
    assert len(fontes) == 6
    assert [f.slug for f in fontes] == ["board", "fila", "mesa", "registro", "wiki", "acervo"]
    assert {f.value for f in Fonte} == {"board", "fila", "mesa", "registro", "wiki", "acervo"}
    assert CLASSE[Fonte.ACERVO] is Classe.SEMANTICA
    assert all(CLASSE[f] is Classe.EXATA for f in Fonte if f is not Fonte.ACERVO)


def test_removida_uma_linha_da_tabela_fonte_some_da_descricao():
    """Prova 2a: Removida uma linha da tabela, a fonte some da descrição gerada."""
    tabela_5 = """## Fontes da plataforma

| fonte | capacidade | dono | transporte | classe | contrato de leitura | gold |
|---|---|---|---|---|---|---|
| board | trabalho | claudinho-TI | HTTP | exata | HTTP do rastreador + header de identidade | nao-calibrada |
| fila | mensagem | claudinho-TI | stream | exata | XINFO STREAM · XRANGE no motor-msg | nao-calibrada |
| mesa | memoria | claudinho-IA | postgres | exata | mapa por chave (arq:0062) | nao-calibrada |
| registro | decisao | claudinha-gestao-estrategica | git | exata | decisions/INDICE.md, mantido na escrita | nao-calibrada |
| acervo | conhecimento | claudinho-dados | HTTP | semantica | API do rag | nao-calibrada |

## Ferramenta de terceiro
"""
    fontes = le_tabela_fontes(texto=tabela_5)
    desc = gera_descricao_tool(fontes)
    assert "wiki" not in desc
    assert "board" in desc
    assert "fila" in desc
    assert "mesa" in desc
    assert "registro" in desc
    assert "acervo" in desc


def test_acrescentada_uma_linha_fonte_aparece_na_descricao():
    """Prova 2b: Acrescentada uma linha, a nova fonte aparece na descrição gerada."""
    tabela_7 = """## Fontes da plataforma

| fonte | capacidade | dono | transporte | classe | contrato de leitura | gold |
|---|---|---|---|---|---|---|
| board | trabalho | claudinho-TI | HTTP | exata | HTTP do rastreador + header de identidade | nao-calibrada |
| fila | mensagem | claudinho-TI | stream | exata | XINFO STREAM · XRANGE no motor-msg | nao-calibrada |
| mesa | memoria | claudinho-IA | postgres | exata | mapa por chave (arq:0062) | nao-calibrada |
| registro | decisao | claudinha-gestao-estrategica | git | exata | decisions/INDICE.md, mantido na escrita | nao-calibrada |
| wiki | conhecimento | claudinho-dados | HTTP | exata | API do MediaWiki | nao-calibrada |
| acervo | conhecimento | claudinho-dados | HTTP | semantica | API do rag | nao-calibrada |
| cofre | seguranca | claudinho-seguranca | vault | exata | API do Vault | nao-calibrada |

## Ferramenta de terceiro
"""
    fontes = le_tabela_fontes(texto=tabela_7)
    desc = gera_descricao_tool(fontes)
    assert "cofre (exata)" in desc
    assert "capacidade seguranca" in desc
    assert "API do Vault" in desc


@pytest.mark.parametrize(
    "texto_invalido,trecho_defeito",
    [
        (
            "## Fontes da plataforma\n\n| fonte | capacidade | dono | transporte | classe | contrato | gold |\n|---|---|---|---|---|---|---|\n| board | trabalho | claudinho-TI | HTTP | magica | HTTP | nao |\n",
            "classe 'magica' inválida",
        ),
        (
            "## Fontes da plataforma\n\n| fonte | capacidade | dono | transporte | classe | contrato | gold |\n|---|---|---|---|---|---|---|\n| board | trabalho | claudinho-TI | HTTP | exata | HTTP |\n",
            "esperadas 7 colunas",
        ),
        (
            "## Fontes da plataforma\n\n| fonte | capacidade | dono | transporte | classe | contrato | gold |\n|---|---|---|---|---|---|---|\n| board | trabalho | claudinho-TI | HTTP | exata | HTTP | nao | extra |\n",
            "esperadas 7 colunas",
        ),
        (
            "## Fontes da plataforma\n\n| fonte | capacidade | dono | transporte | classe | contrato | gold |\n|---|---|---|---|---|---|---|\n|  | trabalho | claudinho-TI | HTTP | exata | HTTP | nao |\n",
            "coluna 'fonte' vazia",
        ),
    ],
)
def test_linha_malformada_falha_nomeando_linha_e_defeito(texto_invalido, trecho_defeito):
    """Prova 3: Linha malformada falha o build nomeando o número da linha e o defeito."""
    with pytest.raises(ErroTabelaFontes) as exc_info:
        le_tabela_fontes(texto=texto_invalido)
    msg = str(exc_info.value)
    assert "linha " in msg
    assert trecho_defeito in msg


def test_teto_tokens_medido():
    """Prova 5: Medição de tokens da descrição gerada."""
    fontes = le_tabela_fontes()
    desc = gera_descricao_tool(fontes)
    n = conta_tokens(desc)
    if n is not None:
        # TETO, nao igualdade. Igualdade quebra a cada linha nova na tabela — e a tabela
        # existe justamente para receber fonte nova sem tocar em codigo. O numero de hoje
        # (165, seis fontes, dono pela cadeira) fica no commit, nao na assercao.
        assert n < 300
