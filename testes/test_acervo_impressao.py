"""#3180: `acervo ler obra impressao` — contrato do verbo sem rede.

Uso e ato desconhecido por subprocesso; exit por classe de erro, primeira e última linha pelas
funções puras do sub-ato (spec espelho-de-leitura §5.4; arq:0110 §4).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IMPRESSAO = RAIZ / "bin" / "_acervo" / "impressao"
CURAR = RAIZ / "bin" / "curar"


def _mod():
    loader = importlib.machinery.SourceFileLoader("acervo_impressao", str(IMPRESSAO))
    spec = importlib.util.spec_from_loader("acervo_impressao", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _roda(*args):
    return subprocess.run([sys.executable, str(IMPRESSAO), *args], capture_output=True, text=True,
                          check=False)


SUMARIO = {
    "espelho": {"tipo": "application/pdf", "unidade": "pagina", "substituicoes": 0,
                "encoding": {"decidido": "utf-8", "por": "binario"},
                "metodo": {"conversor": {"nome": "perfil", "versao": "1"}},
                "qualidade": "nao-julgada", "motivo": None},
    "unidades": 12,
    "secoes": [{"ancora": "_preambulo"}, {"ancora": "capitulo-i"}, {"ancora": "capitulo-ii"}],
}


def _args(**kw):
    base = {"paginas": None, "capitulo": None, "papel": "corpo", "impressao": None, "formato": "md"}
    return Namespace(**{**base, **kw})


def test_sem_obra_e_uso_exit_2():
    r = _roda()
    assert r.returncode == 2 and "uso: acervo ler obra impressao" in r.stderr


def test_ajuda_exit_0():
    r = _roda("--ajuda")
    assert r.returncode == 0 and "--paginas a-b" in r.stdout


def test_opcao_desconhecida_exit_2():
    r = _roda("Lei 14.133", "--nada")
    assert r.returncode == 2 and "argumento desconhecido: --nada" in r.stderr


def test_paginas_e_capitulo_juntos_exit_2():
    assert _roda("x", "--paginas", "1-2", "--capitulo", "a").returncode == 2


def test_exit_por_classe():
    m = _mod()
    assert m.exit_de(404, "ObraNaoEncontrada") == 1
    assert m.exit_de(503, "FonteIndisponivel") == 5
    assert m.exit_de(409, "EspelhoDivergente") == 5
    assert m.exit_de(400, "UnidadeNenhuma") == 2
    assert m.exit_de(409, "SemEspelho") == 2


def test_primeira_linha_no_molde_da_casa():
    m = _mod()
    linha = m.primeira_linha("Lei 14.133", SUMARIO, "1-2", {"cabecalho-corrente": 3}, "corpo", None)
    assert linha == ("Lei 14.133 · application/pdf · pagina 1–2 de 12 · perfil@1 · utf-8 (binario) · "
                     "substituições 0 · fora do corpo: cabeçalho 3, rodapé 0, navegação 0 · "
                     "qualidade nao-julgada")


def test_primeira_linha_sem_espelho():
    m = _mod()
    assert m.primeira_linha("Obra velha", {"espelho": None}, None, {}, "corpo", None) == \
        "Obra velha · qualidade suspeita · sem página"


def test_faixa_lida_declara_o_pedido_quando_lido_inteiro():
    m = _mod()
    assert m.faixa_lida("1-2", None, None, "1-1") == "1-2"   # página 2 sem texto
    assert m.faixa_lida("1-6", None, "b9-abc", "1-3") == "1-3"
    assert m.faixa_lida("1-6", "b9-abc", None, "4-5") == "4-6"
    assert m.faixa_lida(None, None, None, "7-8") == "7-8"


def test_ultima_linha_cursor_leva_o_filtro():
    m = _mod()
    linha = m.ultima_linha("Lei 14.133", _args(paginas="1-2"), "abc", SUMARIO)
    assert linha == "proximo: acervo ler obra impressao 'Lei 14.133' --paginas 1-2 --cursor abc"


def test_ultima_linha_faixa_acabou_aponta_as_paginas_seguintes():
    m = _mod()
    assert m.ultima_linha("x", _args(paginas="1-2"), None, SUMARIO) == \
        "proximo: acervo ler obra impressao x --paginas 3-4"
    assert m.ultima_linha("x", _args(paginas="11-12"), None, SUMARIO) == "fim da obra"


def test_ultima_linha_capitulo_aponta_o_seguinte_e_fim_da_obra():
    m = _mod()
    assert m.ultima_linha("x", _args(capitulo="capitulo-i"), None, SUMARIO) == \
        "proximo: acervo ler obra impressao x --capitulo capitulo-ii"
    assert m.ultima_linha("x", _args(capitulo="capitulo-ii"), None, SUMARIO) == "fim da obra"
    assert m.ultima_linha("x", _args(), None, SUMARIO) == "fim da obra"


def test_curar_declara_e_despacha_os_atos_do_espelho():
    # `curar` importa `requests`, que o venv de teste do harness não tem (roda no python do
    # sistema): confere-se o texto do uso e o despacho, sem executar.
    fonte = CURAR.read_text(encoding="utf-8")
    uso = fonte.split('USO = """', 1)[1].split('"""', 1)[0]
    for ato in ("--recortar <obra>", "--reextrair <obra>", "--expurgar --espelhos",
                "--restaurar --espelhos"):
        assert ato in uso
    for chamada in ("acao_recortar(", "acao_reextrair(", "acao_espelhos(",
                    "/acervo/obras/{obra_id}/recortes", "/acervo/obras/{obra_id}/reextracoes",
                    "/acervo/espelhos/{rota}", "--espelhos acompanha --expurgar ou --restaurar"):
        assert chamada in fonte, chamada
