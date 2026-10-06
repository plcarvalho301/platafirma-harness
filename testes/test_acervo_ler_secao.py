"""acervo ler <particao> secao — cliente da rota POST /acervo/secoes/consulta (#3312). Sem rede:
o POST é injetado; o que se prova é a validação, o corpo enviado e a forma da saída."""
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


def _post_fake(resposta):
    enviados = []

    def f(corpo):
        enviados.append(corpo)
        return resposta
    return f, enviados


def test_le_pela_rota_nao_pelo_banco():
    corpo = ARQ.read_text()
    assert "/acervo/secoes/consulta" in corpo
    assert "docker" not in corpo and "psql" not in corpo


def test_achada_e_nao_achada_saem_com_exit_1(capsys):
    achada = {"secao_id": SID, "arquivo": "guia ddl-e-migracao", "ancora": "x#mapa",
              "breadcrumb": ["a"], "texto": "corpo", "particao": "casa"}
    f, enviados = _post_fake({"secoes": [achada], "nao_achadas": [OUTRO]})
    rc = secao.ler("casa", [SID, OUTRO], True, post=f)
    assert enviados == [{"particao": "casa", "secao_ids": [SID, OUTRO]}]
    assert rc == 1
    assert json.loads(capsys.readouterr().out) == {"secoes": [achada], "nao_achadas": [OUTRO]}


def test_todas_achadas_texto_cru_exit_0(capsys):
    f, _ = _post_fake({"secoes": [{"secao_id": SID, "arquivo": "a", "ancora": "b",
                                   "breadcrumb": [], "texto": "linha 1\nlinha 2"}], "nao_achadas": []})
    assert secao.ler("biblioteca", [SID], False, post=f) == 0
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
    assert corpo.index("ler:casa:secao|ler:biblioteca:secao)") < corpo.index("ler:casa:*)")
