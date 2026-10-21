"""`expediente montar --chapeu <pedaco>`.

Na cadeira (#3931) a abertura nao veste chapeu: `--chapeu` sai 0 com o aviso do ato que veste, sem
validar nem resolver pedaco, porque quem recusa slug fora do vocabulario e `persona ler`. Na
cadeirinha o chapeu e o da lente, e o dono nao decora slug: o nome exato passa calado; um pedaco que
casa com um chapeu so da cadeira vira o slug inteiro, com aviso; pedaco ambiguo sai 2 com as opcoes;
o que nao casa segue para a validacao de sempre.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_expediente import _run_expediente  # noqa: E402
from test_expediente_cadeirinha import raiz  # noqa: E402,F401  (fixture com os stubs)

CHAPEUS = ("agente", "contexto", "engenharia-de-harness")


@pytest.fixture()
def env(raiz, tmp_path):  # noqa: F811
    morada = tmp_path / "morada"
    for ch in CHAPEUS:
        d = morada / "current" / "abertura" / "ia" / ch
        d.mkdir(parents=True)
        (d / "chapeu.md").write_text(f"# {ch}\n", encoding="utf-8")
    return {"PF_CADEIRA": "ia", "PF_BIN": str(raiz / "bin"), "PF_ABERTURA_DIR": str(morada),
            "PF_ORIGEM_SESSAO": "11111111-1111-4111-8111-111111111111",
            "STUB_MOTOR_LOG": str(raiz / "motor.log")}


def _monta(raiz, env, chapeu, *extra):
    return _run_expediente(["montar", "--chapeu", chapeu, *extra, "--json"], raiz, env_extra=env)


def _monta_cadeirinha(raiz, env, chapeu):
    return _monta(raiz, env, chapeu, "--perfil", "cadeirinha", "--modo", "revisar")


# ---------------------------------------------------------------- a cadeira: aviso, nao veste
@pytest.mark.parametrize("dado", ["harness", "engenharia-de-harness", "en", "invalido"])
def test_na_cadeira_qualquer_chapeu_sai_0_e_o_aviso_nomeia_o_ato_que_veste(raiz, env, dado):  # noqa: F811
    proc = _monta(raiz, env, dado)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    assert "chapeu" not in d and "roteador" not in d
    assert "chapeu" not in [p["peca"] for p in d["pecas"]]
    assert any(f"persona ler ia --chapeu {dado}" in a for a in d["avisos"])
    assert not any("resolvido" in a for a in d["avisos"])


# ---------------------------------------------------------------- a cadeirinha: a lente tem chapeu
def test_pedaco_unico_vira_o_slug_inteiro_com_aviso(raiz, env):  # noqa: F811
    proc = _monta_cadeirinha(raiz, env, "harness")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "engenharia-de-harness"
    assert d["roteador"]["slug"] == "engenharia-de-harness"
    assert "chapéu 'harness' resolvido para 'engenharia-de-harness'" in d["avisos"]
    chapeu = next(p for p in d["pecas"] if p["peca"] == "chapeu")
    assert chapeu["ref"] == "verbo:persona ler ia --chapeu engenharia-de-harness"


def test_maiuscula_e_acento_nao_atrapalham(raiz, env):  # noqa: F811
    d = json.loads(_monta_cadeirinha(raiz, env, "Contéxto").stdout)
    assert d["chapeu"] == "contexto"


def test_nome_exato_passa_calado(raiz, env):  # noqa: F811
    d = json.loads(_monta_cadeirinha(raiz, env, "contexto").stdout)
    assert d["chapeu"] == "contexto"
    assert not any("resolvido" in a for a in d["avisos"])


def test_pedaco_ambiguo_sai_2_com_as_opcoes(raiz, env):  # noqa: F811
    proc = _monta_cadeirinha(raiz, env, "en")
    assert proc.returncode == 2
    erro = json.loads(proc.stdout)["erro"]
    assert "ambíguo" in erro and "agente" in erro and "engenharia-de-harness" in erro


def test_o_que_nao_casa_segue_para_a_validacao_de_sempre(raiz, env):  # noqa: F811
    proc = _monta_cadeirinha(raiz, env, "invalido")
    assert proc.returncode == 2
    assert "fora do vocabulário" in json.loads(proc.stdout)["erro"]
