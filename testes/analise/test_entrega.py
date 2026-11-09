"""A entrega de base e resultado a outro sujeito: quem lê, quem entrega e o que a entrega não muda."""
import pytest
from analise import Falha
from analise.publicacao import Catalogo, novo
from analise.receita import carregar


def publicar_base(cat, pasta, receita):
    r = carregar(receita)
    r["saidas"] = {"tabelas": [{"nome": "x", "colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]}]}
    (pasta / "x.csv").write_text("id\n1\n2\n")
    ex = novo("ex")
    cat.abrir_execucao(ex, "preparar", "s", "o")
    return cat.publicar(ex, r, "populacao-de-turnos", pasta, {"serializacao": r["serializacao"], "saidas": {}})


@pytest.fixture
def base(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    return publicar_base(catalogo, out, receita)


def outro(catalogo, sujeito):
    return Catalogo(catalogo.conn, sujeito)


def exit_de(chamada):
    with pytest.raises(Falha) as e:
        chamada()
    return e.value.exit


def test_sujeito_sem_entrega_recebe_exit_4(catalogo, base):
    assert exit_de(lambda: outro(catalogo, "outro").objeto(base)) == 4


def test_entrega_a_um_sujeito_so_abre_para_ele(catalogo, base):
    assert catalogo.entregar(base, "outro")["estado"] == "entregue"
    assert outro(catalogo, "outro").objeto(base)["id"] == base
    assert exit_de(lambda: outro(catalogo, "terceiro").objeto(base)) == 4


def test_entrega_a_todos_abre_para_qualquer_sujeito(catalogo, base):
    catalogo.entregar(base, "*")
    assert outro(catalogo, "terceiro").objeto(base)["id"] == base


def test_so_quem_gerou_entrega(catalogo, base):
    assert exit_de(lambda: outro(catalogo, "outro").entregar(base, "*")) == 4
    assert catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0] == 0


def test_objeto_vencido_nao_se_entrega(catalogo, base):
    catalogo.conn.execute("UPDATE analise.base SET expires_at = now() - interval '1 day' WHERE id=%s", (base,))
    assert exit_de(lambda: catalogo.entregar(base, "*")) == 5
    assert catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0] == 0


def test_destino_invalido_nao_grava(catalogo, base):
    assert exit_de(lambda: catalogo.entregar(base, "a b; drop")) == 2
    assert catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0] == 0


def test_entregar_duas_vezes_grava_uma(catalogo, base):
    catalogo.entregar(base, "outro")
    catalogo.entregar(base, "outro")
    assert catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0] == 1


def test_quem_recebeu_nao_descarta_e_o_descarte_limpa_a_entrega(catalogo, base):
    catalogo.entregar(base, "outro")
    assert exit_de(lambda: outro(catalogo, "outro").descartar(base)) == 4
    catalogo.descartar(base)
    assert catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0] == 0
