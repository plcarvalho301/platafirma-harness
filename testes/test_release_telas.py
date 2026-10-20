"""release telas: a lista de telas do menu da casca (card #3899; arq:0124 §3; comentario #3062 do #3602).

Release de mentira: um registro de stacks num arquivo e uma raiz de release em tmp_path. O ato le a declaracao
unica (registro/telas.json) e devolve so as telas cuja stack esta promovida."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ATO = RAIZ / "bin" / "_release" / "telas" / "telas.py"
DECLARACAO = RAIZ / "registro" / "telas.json"
BIN_RELEASE = RAIZ / "bin" / "release"


def _stack(slug, repo, compose="/opt/c.yml", via="promover"):
    return {"slug": slug, "repo": repo, "compose": compose, "reversao": {"via": via}}


STACKS = [
    _stack("rastreador-tela", "platafirma-ui"),
    _stack("face-motor-tela", "platafirma-ui"),
    _stack("casa-site", "platafirma-conhecimento", via="up"),
    _stack("harness", "platafirma-harness", compose=None),
]


def _ambiente(tmp_path, stacks=STACKS, familias=("platafirma-ui", "platafirma-conhecimento"), declaracao=None):
    prod = tmp_path / "prod"
    for f in familias:
        (prod / f / "sha1").mkdir(parents=True)
        (prod / f / "current").symlink_to(prod / f / "sha1")
    registro = tmp_path / "stacks.json"
    registro.write_text(json.dumps(stacks), encoding="utf-8")
    env = dict(os.environ, PF_PROD_RAIZ=str(prod), PF_TELAS_STACKS=str(registro),
               PF_TELAS_DECLARACAO=str(declaracao or DECLARACAO))
    return env


def _rodar(env, *args):
    return subprocess.run([sys.executable, str(ATO), *args], capture_output=True, text=True, env=env)


def _telas(env):
    p = _rodar(env, "--json")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)["telas"]


def test_a_declaracao_tem_uma_linha_por_tela_sem_origem_repetida():
    dado = json.loads(DECLARACAO.read_text(encoding="utf-8"))
    telas = dado["telas"]
    assert [t["id"] for t in telas] == ["rastreador", "motor", "casa"]
    assert len({t["id"] for t in telas}) == len(telas)
    assert len({t["origem"] for t in telas}) == len(telas), "origem repetida"
    assert len({t["posicao"] for t in telas}) == len(telas)
    for t in telas:
        assert {"id", "rotulo", "origem", "href", "posicao", "face", "familia", "stack"} <= set(t), t
        assert t["href"].startswith(t["origem"] + "/") and not t["origem"].endswith("/")
        assert t["face"] is None or isinstance(t["face"], str)
    assert {t["id"]: t["face"] for t in telas} == {"rastreador": None, "motor": "motor", "casa": None}


def test_a_lista_traz_so_o_que_a_casca_le_na_ordem_do_menu(tmp_path):
    lista = _telas(_ambiente(tmp_path))
    assert [t["id"] for t in lista] == ["rastreador", "motor", "casa"]
    assert set(lista[0]) == {"id", "rotulo", "href", "posicao", "face"}
    assert lista[0]["face"] is None and lista[1]["face"] == "motor", "tela sem face leva face nula"


def test_a_tela_sem_stack_promovida_some_e_o_ato_sai_0(tmp_path):
    so_a_motor = [s for s in STACKS if s["slug"] != "rastreador-tela"]
    p = _rodar(_ambiente(tmp_path, stacks=so_a_motor), "--json")
    assert p.returncode == 0, p.stderr
    assert [t["id"] for t in json.loads(p.stdout)["telas"]] == ["motor", "casa"]


def test_a_tela_de_familia_sem_current_some(tmp_path):
    lista = _telas(_ambiente(tmp_path, familias=("platafirma-ui",)))
    assert [t["id"] for t in lista] == ["rastreador", "motor"]


@pytest.mark.parametrize("stack", [
    _stack("casa-site", "platafirma-conhecimento", compose=None),            # catalogo: nao sobe
    _stack("casa-site", "platafirma-conhecimento", via="teste"),             # estagio de teste
    _stack("casa-site", "outra-familia"),                                    # stack de outra familia
])
def test_stack_que_nao_sobe_em_conteiner_nao_conta_como_promovida(tmp_path, stack):
    stacks = [s for s in STACKS if s["slug"] != "casa-site"] + [stack]
    assert "casa" not in [t["id"] for t in _telas(_ambiente(tmp_path, stacks=stacks))]


def test_nenhuma_tela_promovida_e_lista_vazia_e_sai_0(tmp_path):
    env = _ambiente(tmp_path, stacks=[])
    p = _rodar(env, "--json")
    assert p.returncode == 0 and json.loads(p.stdout) == {"telas": []}
    assert "nenhuma tela" in _rodar(env).stdout


def test_sem_json_imprime_uma_linha_por_tela(tmp_path):
    p = _rodar(_ambiente(tmp_path))
    assert p.returncode == 0
    linhas = p.stdout.splitlines()
    assert len(linhas) == 3 and linhas[1].split("\t")[:2] == ["2", "motor"] and linhas[1].endswith("\tmotor")


def test_registro_ou_declaracao_ilegivel_sai_3_e_nao_inventa_lista(tmp_path):
    env = _ambiente(tmp_path)
    assert _rodar(dict(env, PF_TELAS_STACKS=str(tmp_path / "nao-existe.json")), "--json").returncode == 3
    ruim = tmp_path / "ruim.json"
    ruim.write_text("nao e json", encoding="utf-8")
    p = _rodar(dict(env, PF_TELAS_DECLARACAO=str(ruim)), "--json")
    assert p.returncode == 3 and p.stdout == "" and "dependência ausente" in p.stderr


def test_argumento_desconhecido_e_uso(tmp_path):
    assert _rodar(_ambiente(tmp_path), "--nada").returncode == 2


def test_o_verbo_release_despacha_o_ato_telas(tmp_path):
    """Ponta a ponta pelo despacho do bin/release, com a raiz de release e o registro de mentira."""
    env = _ambiente(tmp_path)
    env.update(PF_RELEASE_RAIZ=env["PF_PROD_RAIZ"], PLATAFIRMA_INSTANCIA=str(tmp_path / "instancia"))
    p = subprocess.run(["bash", str(BIN_RELEASE), "telas", "--json"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    assert [t["id"] for t in json.loads(p.stdout)["telas"]] == ["rastreador", "motor", "casa"]


def test_o_cabecalho_do_release_declara_o_ato_como_mecanismo_da_casca():
    texto = BIN_RELEASE.read_text(encoding="utf-8")
    assert "telas (leitura, operacao)" in texto and "# mecanismo: telas=casca" in texto
    assert "# face: telas=" not in texto
