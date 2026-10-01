"""Contrato de `release conferir acervo` (pedido da engenharia, #3193 passo 14).

Régua de fixture (regua.py e contrato.py no formato do conversor servido) e um `ler` falso no
lugar do psql. Prova: predicado 7 diverge com servindo-com-espelho sem fidelidade e com classe A
com perda em papel de corpo (pela classe da medida e, sem ela, pela do tipo), e não diverge com
perda fora do corpo nem em classe B; servindo sem espelho é aviso, não divergência; predicado 9
diverge com veredito ausente e régua anterior; a pendência do motor lista só a selada indexada
sem índice aprovado e não mexe no exit; catálogo fora e régua ilegível saem 5. Não prova: o
catálogo e o motor reais.
"""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir"))

import predicados_acervo as pa  # noqa: E402
import resultado  # noqa: E402

REGUA = '''
VERSAO_REGUA = 2
PAPEL_DE_CORPO = frozenset(
    {"titulo", "paragrafo", "item", "citacao", "tabela", "legenda", "nota", "codigo", "formula"}
)
'''
CONTRATO = '''
TIPO_HTML = "text/html"
TIPO_PDF = "application/pdf"
CLASSE_A_TIPOS: frozenset[str] = frozenset({TIPO_HTML})
'''


def _regua(tmp_path, regua=REGUA):
    (tmp_path / "regua.py").write_text(regua)
    (tmp_path / "contrato.py").write_text(CONTRATO)
    return str(tmp_path)


def _fid(classe=None, perda=None, **outros):
    f = {"perda": perda or {}, "insercao": {}, "duplicacao": {}, **outros}
    if classe:
        f["classe"] = classe
    return f


def _imp(i, tipo="text/html", espelho=True, fid=None, tem=True, regua="2"):
    return {"id": f"{i:08d}-0000-0000-0000-000000000000", "tipo": tipo, "espelho": espelho,
            "fidelidade": fid if tem else None, "tem_fidelidade": tem and espelho, "regua": regua}


def _ler(servindo, seladas=(), indices=(), tem_coluna=False, fora=()):
    def ler(banco, sql):
        if banco in fora:
            raise pa.Indeterminavel(f"{banco} fora")
        if banco == "motor":
            return list(indices)
        if "information_schema" in sql:
            return {"tem": tem_coluna}
        if "em_construcao" in sql:
            return list(seladas)
        return list(servindo)
    return ler


def _estado(itens, prefixo):
    return next(v for n, v in itens if n.startswith(prefixo))


def test_tudo_conforme(tmp_path):
    itens, avisos, pend = pa.medir(_regua(tmp_path), _ler([_imp(1, fid=_fid("A")), _imp(2, espelho=False)]))
    assert resultado.agrega(itens)[0] == 0
    assert any("1 de 2 servindo sem espelho" in a for a in avisos)
    assert pend == []


def test_p7_sem_fidelidade_e_classe_a_com_perda_no_corpo(tmp_path):
    servindo = [
        _imp(1, tem=False),                                          # sem sinais.fidelidade
        _imp(2, fid=_fid("A", perda={"paragrafo": 3})),              # classe da medida
        _imp(3, fid=_fid(None, perda={"item": 1})),                  # classe pelo tipo (html = A)
        _imp(4, fid=_fid("A", perda={"rodape": 9})),                 # fora do corpo: não bloqueia
        _imp(5, tipo="application/pdf", fid=_fid(None, perda={"paragrafo": 9})),  # classe B
    ]
    itens, _, _ = pa.medir(_regua(tmp_path), _ler(servindo))
    v = _estado(itens, "§11 predicado 7")
    assert v.estado == "divergente"
    assert "1 sem sinais.fidelidade" in v.motivo and "2 de classe A" in v.motivo
    assert "00000004" not in v.motivo and "00000005" not in v.motivo
    assert resultado.agrega(itens)[0] == 1


def test_p9_veredito_ausente_ou_regua_anterior(tmp_path):
    servindo = [_imp(1, fid=_fid("A"), regua=None), _imp(2, fid=_fid("A"), regua="1"),
                _imp(3, fid=_fid("A")), _imp(4, espelho=False, regua=None)]
    itens, _, _ = pa.medir(_regua(tmp_path), _ler(servindo))
    v = _estado(itens, "§11 predicado 9")
    assert v.estado == "divergente"
    assert "1 sem veredito" in v.motivo and "1 julgadas por régua anterior à 2" in v.motivo
    assert "de 3 servindo com espelho" in v.motivo


def test_pendencia_do_motor_nao_pesa_no_exit(tmp_path):
    """Pendente é a selada indexada fora do gate (#3203): índice pela metade, sem faceta ou sem índice."""
    def selada(n, indexada=True):
        return {"id": f"000000{n}-0000-0000-0000-000000000000", "obra": f"o{n}", "titulo": n,
                "elegiveis": 3, "indexada": indexada}

    seladas = [selada(10), selada(11), selada(12, indexada=False), selada(13), selada(14)]
    indices = [{"impressao": seladas[0]["id"], "vetores": 1, "faceta": True},   # pela metade
               {"impressao": seladas[1]["id"], "vetores": 3, "faceta": True},   # aprovada
               {"impressao": seladas[3]["id"], "vetores": 3, "faceta": False}]  # sem faceta
    itens, avisos, pend = pa.medir(_regua(tmp_path), _ler([_imp(1, fid=_fid("A"))], seladas, indices))
    assert resultado.agrega(itens)[0] == 0
    assert [p["impressao"] for p in pend[0]["impressoes"]] == [seladas[0]["id"], seladas[3]["id"],
                                                               seladas[4]["id"]]
    assert pend[0]["para"] == "ia"
    assert any("3 selada(s) de 5" in a for a in avisos)


def test_catalogo_fora_sai_5(tmp_path):
    itens, avisos, _ = pa.medir(_regua(tmp_path), _ler([], fora=("rag",)))
    assert resultado.agrega(itens)[0] == 5
    assert any("não consegui olhar" in a for a in avisos)


def test_regua_ilegivel_sai_5(tmp_path):
    itens, _, _ = pa.medir(_regua(tmp_path, regua="X = 1\n"), _ler([_imp(1, fid=_fid("A"))]))
    assert all(v.estado == "indeterminavel" for _, v in itens)
    assert resultado.agrega(itens)[0] == 5


def test_regua_servida_se_le_quando_existe():
    """Na máquina com o conhecimento servido, a régua real se lê por AST (sem import)."""
    import os
    import pytest
    if not os.path.exists(os.path.join(pa.SERVIDO_CONVERSOR, "regua.py")):
        pytest.skip("sem platafirma-conhecimento servido nesta máquina")
    versao, corpo, classe_a = pa.regua_servida()
    assert versao >= 2 and "paragrafo" in corpo and "text/html" in classe_a
    assert "application/pdf" not in classe_a


def test_json_traz_avisos_e_pendencias(tmp_path):
    itens, avisos, pend = pa.medir(_regua(tmp_path), _ler([_imp(1, fid=_fid("A"))]))
    out = io.StringIO()
    with redirect_stdout(out):
        rc = resultado.relatorio("acervo", None, itens, "abc1234", como_json=True,
                                 extra={"avisos": avisos, "pendencias": pend})
    d = json.loads(out.getvalue())
    assert rc == 0 and d["classe"] == "acervo" and d["avisos"] and d["pendencias"] == []
    assert d["ancora"].startswith("release conferir acervo: 2 conforme")
