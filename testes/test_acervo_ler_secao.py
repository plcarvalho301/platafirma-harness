"""acervo ler <particao> secao — o texto pelo endereço da busca (#3312). Sem banco: o psql é
injetado; o que se prova é a validação, o SQL montado e a forma da saída."""
import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ARQ = RAIZ / "bin" / "_acervo" / "secao"
_loader = importlib.machinery.SourceFileLoader("acervo_secao", str(ARQ))
_spec = importlib.util.spec_from_loader("acervo_secao", _loader)
secao = importlib.util.module_from_spec(_spec)
_loader.exec_module(secao)

SID = "8cc00b2e-5280-52bc-b230-232d157ac62c"
OUTRO = "bfe93174-298e-56bd-ad2e-181bde227c2f"


def _psql_fake(linhas):
    vistos = []

    def f(sql):
        vistos.append(sql)
        return linhas
    return f, vistos


def test_sql_por_particao_usa_a_tabela_certa_e_so_o_servido():
    casa = secao.montar_sql("casa", [SID])
    bib = secao.montar_sql("biblioteca", [SID.upper()])
    assert "acervo.casa_trecho" in casa and "i.estado = 'servindo'" in casa
    assert "c.retirada_em is null" in casa
    assert "acervo.trecho " in bib and "o.expurgada_em is null" in bib
    assert "'{" + SID + "}'" in bib  # uuid normalizado em minúscula


def test_ordem_do_texto_igual_a_do_motor():
    for p in ("casa", "biblioteca"):
        sql = secao.montar_sql(p, [SID])
        assert "order by t.part_idx nulls first, t.ordem_leitura nulls first" in sql
        assert "filter (where not t.is_not_text)" in sql


def test_achada_e_nao_achada_saem_com_exit_1(capsys):
    f, _ = _psql_fake([{"secao_id": SID, "arquivo": "guia ddl-e-migracao", "ancora": "x#mapa",
                        "breadcrumb": ["a"], "texto": "corpo"}])
    rc = secao.ler("casa", [SID, OUTRO], True, psql=f)
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert [s["secao_id"] for s in out["secoes"]] == [SID]
    assert out["secoes"][0]["texto"] == "corpo" and out["secoes"][0]["particao"] == "casa"
    assert out["nao_achadas"] == [OUTRO]


def test_todas_achadas_texto_cru_exit_0(capsys):
    f, _ = _psql_fake([{"secao_id": SID, "arquivo": "a", "ancora": "b", "breadcrumb": [],
                        "texto": "linha 1\nlinha 2"}])
    assert secao.ler("biblioteca", [SID], False, psql=f) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("== " + SID) and "linha 1\nlinha 2" in saida


@pytest.mark.parametrize("args,rc", [
    (["casa"], 2),
    (["registro", SID], 2),
    (["casa", "nao-e-uuid"], 2),
    (["casa", SID + "'; drop table x; --"], 2),
])
def test_uso_recusa(args, rc):
    r = subprocess.run(["python3", str(ARQ), *args], capture_output=True, text=True)
    assert r.returncode == rc


def test_despachante_roteia_secao_antes_do_generico():
    corpo = (RAIZ / "bin" / "acervo").read_text()
    rota = corpo.index("ler:casa:secao|ler:biblioteca:secao)")
    generico = corpo.index("ler:casa:*)")
    assert rota < generico
