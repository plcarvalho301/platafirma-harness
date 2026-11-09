"""A entrega de base e resultado a outro sujeito: o padrão é entregar a todos, e a receita privada não entrega."""
import pytest
from analise import Falha
from analise.publicacao import Catalogo, novo
from analise.receita import carregar


def publicar_base(cat, pasta, receita, entrega=None):
    r = carregar(receita)
    if entrega:
        r["entrega"] = entrega
    r["saidas"] = {"tabelas": [{"nome": "x", "colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]}]}
    (pasta / "x.csv").write_text("id\n1\n2\n")
    ex = novo("ex")
    cat.abrir_execucao(ex, "preparar", "s", "o")
    return cat.publicar(ex, r, "populacao-de-turnos", pasta, {"serializacao": r["serializacao"], "saidas": {}})


@pytest.fixture
def base_padrao(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    return publicar_base(catalogo, out, receita)


@pytest.fixture
def base(catalogo, base_padrao):
    """Base sem nenhuma entrega: a entrega do padrão sai, para provar cada caso."""
    catalogo.conn.execute("DELETE FROM analise.entrega WHERE objeto_id=%s", (base_padrao,))
    return base_padrao


def outro(catalogo, sujeito):
    return Catalogo(catalogo.conn, sujeito)


def exit_de(chamada):
    with pytest.raises(Falha) as e:
        chamada()
    return e.value.exit


def entregas(catalogo):
    return catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0]


def test_base_nova_nasce_entregue_a_todos(catalogo, base_padrao):
    assert outro(catalogo, "qualquer").objeto(base_padrao)["id"] == base_padrao
    assert catalogo.conn.execute(
        "SELECT sujeito, entregue_por FROM analise.entrega WHERE objeto_id=%s", (base_padrao,)
    ).fetchone() == ("*", "sujeito-teste")


def test_resultado_novo_nasce_entregue_a_todos(catalogo, base_padrao, tmp_path):
    out = tmp_path / "res"
    out.mkdir()
    (out / "y.csv").write_text("n\n7\n")
    r = {
        "tipo": "analise",
        "saidas": {"tabelas": [{"nome": "y", "colunas": [{"nome": "n", "tipo": "inteiro"}], "ordem": ["n"]}]},
        "serializacao": {"nulo": "", "nan": "NaN", "datas": "utc", "decimais": 3},
    }
    ex = novo("ex")
    catalogo.abrir_execucao(ex, "montar", "s", "o")
    rid = catalogo.publicar(ex, r, "x", out, {"serializacao": r["serializacao"], "saidas": {}}, catalogo.objeto(base_padrao))
    assert outro(catalogo, "qualquer").objeto(rid)["id"] == rid


def test_receita_privada_nao_entrega(catalogo, tmp_path, receita):
    out = tmp_path / "priv"
    out.mkdir()
    privada = publicar_base(catalogo, out, receita, entrega="privada")
    assert entregas(catalogo) == 0
    assert exit_de(lambda: outro(catalogo, "outro").objeto(privada)) == 4


def test_entrega_invalida_na_receita_recusa(receita):
    texto = (receita / "receita.yaml").read_text() + "entrega: aberta\n"
    (receita / "receita.yaml").write_text(texto)
    assert exit_de(lambda: carregar(receita)) == 2


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
    assert entregas(catalogo) == 0


def test_objeto_vencido_nao_se_entrega(catalogo, base):
    catalogo.conn.execute("UPDATE analise.base SET expires_at = now() - interval '1 day' WHERE id=%s", (base,))
    assert exit_de(lambda: catalogo.entregar(base, "*")) == 5
    assert entregas(catalogo) == 0


def test_destino_invalido_nao_grava(catalogo, base):
    assert exit_de(lambda: catalogo.entregar(base, "a b; drop")) == 2
    assert entregas(catalogo) == 0


def test_entregar_duas_vezes_grava_uma(catalogo, base):
    catalogo.entregar(base, "outro")
    catalogo.entregar(base, "outro")
    assert entregas(catalogo) == 1


def test_quem_recebeu_nao_descarta_e_o_descarte_limpa_a_entrega(catalogo, base_padrao):
    assert exit_de(lambda: outro(catalogo, "outro").descartar(base_padrao)) == 4
    catalogo.descartar(base_padrao)
    assert entregas(catalogo) == 0
