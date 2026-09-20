"""Testes de aceite do gerador de fontes e derivação do enum (#2320, arq:0076).

Aceite (executável por terceiro):
1. A tabela do catálogo tem as seis linhas do §5 da spec, e recuperacao/fontes.py
   não guarda mais lista própria de fontes — o enum é construído da tabela.
2. Removida uma linha da tabela, a fonte some da descrição gerada; acrescentada, aparece.
   Provado nos dois sentidos, em teste.
3. Linha malformada falha o build nomeando o número da linha e o defeito.
4. A suíte de contrato do F0 continua verde.
5. O commit declara o tamanho da descrição gerada em tokens, medido.
6. arq:0076 — com docs/catalogo-de-fontes.md ausente E RAG_API_URL inválido,
   `import recuperacao.fontes` não estoura e Fonte/CLASSE têm as 6 do seed embutido.
7. arq:0076 — com a API respondendo, `_constroi_fontes` monta o enum a partir DELA,
   não do seed nem do .md.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

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
    """Prova 1: Enum Fonte e mapa CLASSE construídos da tabela do catálogo.

    `texto=TABELA_6_FONTES` explícito — não depende de docs/catalogo-de-fontes.md, que
    não é mais a fonte da verdade (arq:0076) e pode nem existir no checkout.
    """
    fontes = le_tabela_fontes(texto=TABELA_6_FONTES)
    assert len(fontes) == 6
    assert [f.slug for f in fontes] == ["board", "fila", "mesa", "registro", "wiki", "acervo"]

    FonteX, ClasseX = _constroi_fontes(texto=TABELA_6_FONTES)
    assert {f.value for f in FonteX} == {"board", "fila", "mesa", "registro", "wiki", "acervo"}
    assert ClasseX[FonteX.ACERVO] is Classe.SEMANTICA
    assert all(ClasseX[f] is Classe.EXATA for f in FonteX if f is not FonteX.ACERVO)


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
    fontes = le_tabela_fontes(texto=TABELA_6_FONTES)
    desc = gera_descricao_tool(fontes)
    n = conta_tokens(desc)
    if n is not None:
        # TETO, nao igualdade. Igualdade quebra a cada linha nova na tabela — e a tabela
        # existe justamente para receber fonte nova sem tocar em codigo. O numero de hoje
        # (165, seis fontes, dono pela cadeira) fica no commit, nao na assercao.
        assert n < 300


def test_import_nao_estoura_sem_md_e_com_api_fora():
    """Prova 6 (arq:0076): sem docs/catalogo-de-fontes.md (já ausente no checkout) e com
    RAG_API_URL apontando para porta sem escuta, `import recuperacao.fontes` não estoura
    e Fonte/CLASSE têm as 6 do seed embutido. Subprocesso: prova o import do zero, sem o
    cache do módulo que a suíte já carregou.
    """
    raiz = Path(__file__).resolve().parent.parent
    env = {**os.environ, "RAG_API_URL": "http://127.0.0.1:1"}
    r = subprocess.run(
        [sys.executable, "-c",
         "import recuperacao.fontes as f; print(sorted(x.value for x in f.Fonte))"],
        cwd=str(raiz), env=env, capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"import estourou: {r.stderr}"
    slugs = ast.literal_eval(r.stdout.strip())
    assert slugs == ["acervo", "board", "fila", "mesa", "registro", "wiki"]


def test_repoint_monta_enum_a_partir_do_stub_da_api(monkeypatch):
    """Prova 7 (arq:0076): com `_le_fontes_do_acervo` devolvendo linhas do golden record,
    `_constroi_fontes()` monta o enum A PARTIR DELAS — não do seed nem do .md.

    `cofre` não está no seed nem em TABELA_6_FONTES: só aparecer aqui prova que a fonte é
    o stub da API, não um fallback disfarçado.
    """
    linhas = [
        FonteInfo(slug="cofre", capacidade="seguranca", dono="claudinho-seguranca",
                  transporte="vault", classe="exata", contrato_de_leitura="API do Vault",
                  gold="nao-calibrada", linha_num=1),
    ]
    monkeypatch.setattr("recuperacao.fontes._le_fontes_do_acervo", lambda: linhas)
    FonteX, ClasseX = _constroi_fontes()
    assert {f.value for f in FonteX} == {"cofre"}
    assert ClasseX[FonteX.COFRE] is Classe.EXATA
