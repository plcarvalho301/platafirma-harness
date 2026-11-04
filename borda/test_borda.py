"""Testes da borda das faces (card #3516). O self-check de borda.py é o grosso: nove recusas em 403 sem
chegar à porta, o que passa, o que o navegador não pode pôr e o envelope da porta. Aqui ele roda no portão,
e o cabeçalho real do verbo `motor` (o que a release serve) é lido pelo mesmo parser."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import borda  # noqa: E402

MOTOR = AQUI.parent / "bin" / "motor"
REGISTRO = AQUI.parent / "registro" / "porta.yaml"      # o registro da porta (#4117): de onde saem as faces
TOKEN = {borda.CABECALHO_DO_GATE: "a.b.c"}


def test_autoteste_da_borda(capsys):
    borda._autoteste()
    assert "borda OK (#3516, #3518, #3575, #3738, #3899)" in capsys.readouterr().out


def test_a_casca_alcanca_dos_tres_verbos_reais_so_o_ato_do_mecanismo():
    """#3899: as tres leituras da casca (arq:0124 §3) saem do cabeçalho real de cada verbo, pela chave
    `mecanismo:`, e nenhum deles põe a casca em `face:`."""
    bin_ = AQUI.parent / "bin"
    assert borda.Face("casca", verbo=str(bin_ / "release")).atos() == {"telas": {"leitura"}}
    assert borda.Face("casca", verbo=str(bin_ / "tarefas")).atos() == {"espera-dono": {"leitura"}}
    for verbo in ("preferencia", "release", "tarefas"):
        texto = (bin_ / verbo).read_text(encoding="utf-8")
        assert "casca" not in borda.ler_cabecalho(texto), verbo


def test_a_face_casca_alcanca_do_preferencia_o_ler_e_o_escrever():
    """#3738: a rota do tema (spec taipa R40) so vale se o cabecalho REAL do verbo poe os dois atos na face
    `casca`, com a capacidade que a borda confere por metodo."""
    atos = borda.Face("casca", verbo=str(AQUI.parent / "bin" / "preferencia")).atos()
    assert atos == {"ler": {"leitura"}, "escrever": {"escrita"}}


def test_a_rota_do_tema_contra_o_cabecalho_real_do_verbo():
    chamadas = []

    def porta(token, tool, argumentos):
        chamadas.append((token, tool, argumentos))
        return 200, {"exit_code": 0, "stdout": {"texto": json.dumps({"preferencia": "tema", "valor": "claro",
                                                                  "motivo": None})}}

    app = borda.Borda([borda.Face("casca", verbo=str(AQUI.parent / "bin" / "preferencia"))],
                      origens=("https://tarefas.exemplo.org",), chamar_porta=porta)
    status, _, corpo = asyncio.run(borda._chamar(app, "GET", borda.ROTA_DO_TEMA, TOKEN))
    assert status == 200 and json.loads(corpo) == {"valor": "claro"}
    assert chamadas == [("a.b.c", "preferencia", {"ato": "ler", "args": ["tema", "--json"], "turno_fonte": "face"})]


def test_a_configuracao_da_borda_da_casca_sobe_do_ambiente_da_instancia():
    env = {"BORDA_REGISTRO": str(REGISTRO), "BORDA_FACES_ATENDE": "casca",
           "BORDA_ORIGENS": "https://tarefas.exemplo.org", "BORDA_LOGIN_MAX_S": "0"}
    app = borda.criar_app(env)
    assert list(app.faces) == ["casca"] and app.login_max_s == 0
    assert [Path(f.verbo).name for f in app.faces["casca"]] == ["preferencia", "release", "tarefas"]
    assert asyncio.run(borda._chamar(app, "GET", borda.ROTA_DO_TEMA, {}))[0] == 401


def test_o_compose_liga_cada_instancia_a_declaracao_das_telas_e_as_tres_leituras():
    """#3899: as tres instancias leem as origens da declaracao (nenhuma lista a mao), atendem uma tela que a
    declaracao tem, e a casca nelas chama os tres verbos donos das leituras."""
    yaml = pytest.importorskip("yaml")
    compose = yaml.safe_load((AQUI / "compose.yaml").read_text(encoding="utf-8"))
    declaradas = {t["id"] for t in json.loads(
        (AQUI.parent / "registro" / "telas.json").read_text(encoding="utf-8"))["telas"]}
    atendidas, faces = [], {}
    for nome, servico in compose["services"].items():
        env = servico["environment"]
        assert "registro/telas.json" in env["BORDA_TELAS"], nome
        assert env["BORDA_TELAS_ATENDE"] in declaradas, nome
        atendidas.append(env["BORDA_TELAS_ATENDE"])
        # as faces saem do registro da porta (#4117); BORDA_FACES saiu do compose
        assert "BORDA_FACES" not in env and "/current/harness/registro/porta.yaml" in env["BORDA_REGISTRO"], nome
        app = borda.criar_app({"BORDA_REGISTRO": str(REGISTRO), "BORDA_FACES_ATENDE": env["BORDA_FACES_ATENDE"]})
        assert [Path(f.verbo).name for f in app.faces["casca"]] == ["preferencia", "release", "tarefas"], nome
        faces[nome] = sorted(app.faces)
    assert faces == {"borda": ["casca", "motor"], "borda-casca-rastreador": ["casca"],
                     "borda-casca-site": ["casca"]}, "o cubo atende a face motor e a casca; as outras so a casca"
    assert sorted(atendidas) == ["casa", "motor", "rastreador"], "uma instancia por tela, sem repetir"
    redes = {n for s in compose["services"].values() for n in s["networks"] if n != "default"}
    assert redes <= set(compose["networks"]) and "casca-site" in redes


def test_a_lista_de_atos_da_face_motor_e_a_do_cabecalho_do_verbo_real():
    atos = borda.Face("motor", verbo=str(MOTOR)).atos()
    assert set(atos) == {"buscar", "medir", "listar", "ajuste", "indexar", "trocar", "consultas", "trabalhos",
                         "estado", "parar"}
    assert atos["ajuste"] == {"leitura", "escrita"}
    assert atos["trocar"] == {"escrita"} and atos["indexar"] == {"escrita"}
    assert atos["consultas"] == {"leitura"} and atos["trabalhos"] == {"leitura"}
    # o estado da troca e leitura (buraco #2553) e parar a sombra e escrita (buraco #2554), #3518
    assert atos["estado"] == {"leitura"} and atos["parar"] == {"escrita"}
    # a linha de exclusao (instrumento de medida da ia) nao tem face
    assert not {"sortear", "parear", "escrever", "julgar", "lintar", "eleger"} & set(atos)


def test_a_face_motor_alcanca_do_fila_so_o_contestar():
    """#3518, buraco #2555: o `fila` declara para a face motor so o `contestar`, de escrita; o `enviar` geral fica fora."""
    atos = borda.Face("motor", verbo=str(AQUI.parent / "bin" / "fila")).atos()
    assert atos == {"contestar": {"escrita"}}


def test_o_cabecalho_novo_do_verbo_vale_sem_reiniciar_a_borda(tmp_path):
    verbo = tmp_path / "motor"
    verbo.write_text("#!/bin/sh\n# atos: a (leitura, x), b (escrita, y)\n# face: a=motor\n", encoding="utf-8")
    face = borda.Face("motor", verbo=str(verbo))
    assert set(face.atos()) == {"a"}
    verbo.write_text("#!/bin/sh\n# atos: a (leitura, x), b (escrita, y)\n# face: a=motor\n# face: b=motor\n",
                     encoding="utf-8")
    assert set(face.atos()) == {"a", "b"}


def test_ato_declarado_na_face_sem_capacidade_fica_de_fora():
    assert borda.ler_cabecalho("# atos: a (leitura, x)\n# face: a=motor\n# face: b=motor\n") == {
        "motor": {"a": frozenset({"leitura"})}}


@pytest.mark.parametrize("caso", ["sem registro", "registro que nao existe", "registro que nao e yaml",
                                  "registro sem a forma", "sem face atendida"])
def test_configuracao_ilegivel_sobe_a_borda_sem_face_e_nada_passa(caso, tmp_path, capsys):
    (tmp_path / "nao.yaml").write_text("verbos: {a: {\n", encoding="utf-8")
    (tmp_path / "sem-forma.yaml").write_text("verbos: [a, b]\n", encoding="utf-8")
    env = {
        "sem registro": {"BORDA_FACES_ATENDE": "motor"},
        "registro que nao existe": {"BORDA_REGISTRO": str(tmp_path / "x.yaml"), "BORDA_FACES_ATENDE": "motor"},
        "registro que nao e yaml": {"BORDA_REGISTRO": str(tmp_path / "nao.yaml"), "BORDA_FACES_ATENDE": "motor"},
        "registro sem a forma": {"BORDA_REGISTRO": str(tmp_path / "sem-forma.yaml"), "BORDA_FACES_ATENDE": "motor"},
        "sem face atendida": {"BORDA_REGISTRO": str(REGISTRO)},
    }[caso]
    app = borda.criar_app(env)
    assert asyncio.run(borda._chamar(app, "GET", "/api/motor/buscar", TOKEN))[0] == 404


def test_as_faces_do_cubo_saem_do_registro_da_porta():
    """#4117: a face motor chama o `motor` (instancia rag, `listar` sem instancia) e o `fila`; a casca chama os tres
    verbos das leituras. O verbo de cada face e o bin da raiz do harness onde mora o registro."""
    app = borda.criar_app({"BORDA_REGISTRO": str(REGISTRO), "BORDA_FACES_ATENDE": "motor,casca"})
    motor = sorted((Path(f.verbo).name, f.instancia, sorted(f.sem_instancia)) for f in app.faces["motor"])
    assert motor == [("fila", None, []), ("motor", "rag", ["listar"])]
    assert {Path(f.verbo).parent for fs in app.faces.values() for f in fs} == {AQUI.parent / "bin"}
    assert sorted(Path(f.verbo).name for f in app.faces["casca"]) == ["preferencia", "release", "tarefas"]
    assert borda.criar_app({"BORDA_REGISTRO": str(REGISTRO), "BORDA_FACES_ATENDE": "casca"}).faces.keys() == {"casca"}


def test_a_lista_de_origens_e_a_configuracao_da_instancia():
    env = {"BORDA_REGISTRO": str(REGISTRO), "BORDA_FACES_ATENDE": "motor",
           "BORDA_ORIGENS": "https://a.exemplo, https://b.exemplo"}
    app = borda.criar_app(env)
    assert app.origens == ("https://a.exemplo", "https://b.exemplo")
    escrita = {"origin": "https://b.exemplo", "x-pf-tela": "1", "content-type": "application/json", **TOKEN}
    # a origem da lista passa pela recusa; a porta nao existe aqui, entao a chamada vira 502, nunca 403
    app._chamar = lambda token, tool, argumentos: (502, {"erro": "a porta está fora do ar"})
    assert asyncio.run(borda._chamar(app, "POST", "/api/motor/trocar", escrita, b"{}"))[0] == 502
    assert asyncio.run(borda._chamar(
        app, "POST", "/api/motor/trocar", {**escrita, "origin": "https://c.exemplo"}, b"{}"))[0] == 403
