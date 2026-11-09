"""O keycloak guarda credencial e conta: só segurança e TI rodam a receita que o lê e leem o que sai dela."""
import pytest
from analise import Falha
from analise.publicacao import Catalogo, novo, restricao_das_origens
from analise.receita import carregar

ORIGENS_COM_KEYCLOAK = [
    {"banco": "rag", "tabela": "acervo.log"},
    {"banco": "keycloak", "tabela": "public.user_entity"},
]


def exit_de(chamada):
    with pytest.raises(Falha) as e:
        chamada()
    return e.value.exit


def publicar_restrita(cat, pasta, receita):
    r = carregar(receita)
    r["saidas"] = {"tabelas": [{"nome": "x", "colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]}]}
    (pasta / "x.csv").write_text("id\n1\n")
    ex = novo("ex")
    cat.abrir_execucao(ex, "preparar", "s", "o")
    manifesto = {"serializacao": r["serializacao"], "saidas": {}, "restrita_a": ["seguranca", "ti"]}
    return cat.publicar(ex, r, "populacao-de-turnos", pasta, manifesto)


@pytest.mark.parametrize("cadeira", ["seguranca", "ti"])
def test_seguranca_e_ti_rodam_a_receita_do_keycloak(cadeira):
    assert restricao_das_origens(ORIGENS_COM_KEYCLOAK, cadeira) == ["seguranca", "ti"]


@pytest.mark.parametrize("cadeira", ["dados", "produto", "engenharia", ""])
def test_outra_cadeira_nao_roda_a_receita_do_keycloak(cadeira):
    assert exit_de(lambda: restricao_das_origens(ORIGENS_COM_KEYCLOAK, cadeira)) == 4


def test_mdm_rh_e_identidade_seguem_livres():
    origens = [{"banco": "mdm_rh", "tabela": "a.b"}, {"banco": "identidade", "tabela": "a.c"}, {"tabela": "acervo.log"}]
    assert restricao_das_origens(origens, "dados") is None


def test_objeto_restrito_so_abre_para_seguranca_e_ti(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    id = publicar_restrita(catalogo, out, receita)
    for cadeira in ("seguranca", "ti"):
        assert Catalogo(catalogo.conn, "sujeito-teste", cadeira).objeto(id)["id"] == id
    for cadeira in ("dados", "produto", ""):
        assert exit_de(lambda: Catalogo(catalogo.conn, "sujeito-teste", cadeira).objeto(id)) == 4


def test_a_entrega_a_todos_nao_abre_o_objeto_restrito(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    id = publicar_restrita(catalogo, out, receita)
    assert Catalogo(catalogo.conn, "outro", "ti").objeto(id)["id"] == id
    assert exit_de(lambda: Catalogo(catalogo.conn, "outro", "dados").objeto(id)) == 4


def test_quem_gerou_ainda_descarta_o_objeto_restrito(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    id = publicar_restrita(catalogo, out, receita)
    catalogo.descartar(id)
    assert catalogo.conn.execute("SELECT count(*) FROM analise.base").fetchone()[0] == 0
