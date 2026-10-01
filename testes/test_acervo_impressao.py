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


# --- a linha de avisos (spec conversor-pdf-combinado §11; card #3207) ------------------------------

TABELA = "tabela com coluna suspeita"
ORDEM = "ordem entre colunas suspeita"


def _aviso(codigo, rotulo, *faixas):
    return {"codigo": codigo, "rotulo": rotulo, "paginas": [list(f) for f in faixas]}


AVISOS_DO_EXEMPLO = [_aviso("tabela_coluna", TABELA, (120, 131)), _aviso("ordem_colunas", ORDEM, (3, 3))]


def test_a_linha_de_avisos_do_exemplo_da_spec():
    m = _mod()
    assert m.linha_de_avisos(AVISOS_DO_EXEMPLO) == (
        "avisos: p. 120–131 tabela com coluna suspeita; p. 3 ordem entre colunas suspeita")


def test_sem_aviso_nao_ha_linha():
    m = _mod()
    assert m.linha_de_avisos(None) is None and m.linha_de_avisos([]) is None
    assert m.linha_de_avisos([{"codigo": "ocr", "rotulo": "texto por OCR", "paginas": []}, None]) is None


def test_a_primeira_linha_leva_os_avisos_depois_da_qualidade():
    m = _mod()
    sumario = {**SUMARIO, "espelho": {**SUMARIO["espelho"], "avisos": AVISOS_DO_EXEMPLO}}
    linha = m.primeira_linha("Lei 14.133", sumario, "1-2", {"cabecalho-corrente": 3}, "corpo", None)
    assert linha.endswith(
        "qualidade nao-julgada · avisos: p. 120–131 tabela com coluna suspeita; p. 3 ordem entre colunas suspeita")
    assert "\n" not in linha and linha.count("avisos:") == 1


def test_a_primeira_linha_sem_avisos_fica_como_antes():
    m = _mod()
    com_lista_vazia = {**SUMARIO, "espelho": {**SUMARIO["espelho"], "avisos": []}}
    sem_chave = m.primeira_linha("Lei", SUMARIO, "1-2", {}, "corpo", None)
    assert m.primeira_linha("Lei", com_lista_vazia, "1-2", {}, "corpo", None) == sem_chave
    assert "avisos" not in sem_chave


def test_o_que_nao_cabe_na_largura_entra_contado_no_fim():
    m = _mod()
    longos = [_aviso("tabela_coluna", TABELA, (10, 12)), _aviso("ordem_colunas", ORDEM, (3, 3)),
              _aviso("sem_texto", "escaneada sem texto", (20, 29))]
    assert m.linha_de_avisos(longos, largura=70) == "avisos: p. 10–12 tabela com coluna suspeita; +11 páginas"
    assert m.linha_de_avisos(longos, largura=78) == (
        "avisos: p. 10–12 tabela com coluna suspeita; p. 3 ordem entre colunas suspeita; +10 páginas")
    assert m.linha_de_avisos(longos) == (
        "avisos: p. 10–12 tabela com coluna suspeita; p. 3 ordem entre colunas suspeita; p. 20–29 escaneada sem texto")
    assert m.linha_de_avisos(longos, largura=10) == "avisos: p. 10–12 tabela com coluna suspeita; +11 páginas"


def test_no_maximo_tantas_faixas_por_aviso_e_o_resto_vira_mais_n():
    m = _mod()
    aviso = _aviso("tabela_coluna", TABELA, (1, 1), (3, 3), (5, 6), (9, 9))
    assert m.linha_de_avisos([aviso], faixas_por_aviso=2) == "avisos: p. 1, 3 tabela com coluna suspeita; +3 páginas"
    assert m.linha_de_avisos([aviso], faixas_por_aviso=3) == "avisos: p. 1, 3, 5–6 tabela com coluna suspeita; +1 página"
    assert m.linha_de_avisos([aviso]) == "avisos: p. 1, 3, 5–6, 9 tabela com coluna suspeita"


def test_aviso_sem_rotulo_sai_com_o_codigo():
    m = _mod()
    assert m.linha_de_avisos([{"codigo": "novo_aviso", "paginas": [[4, 4]]}]) == "avisos: p. 4 novo_aviso"


def test_a_ajuda_do_verbo_fala_dos_avisos():
    r = _roda("--ajuda")
    assert r.returncode == 0 and "avisos: p. 120–131" in r.stdout


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
