# componente: componente:analise
"""Conjunto de casos de comportamento do componente analise: receita, comparação, projeção, publicação, coleta, entrega, keycloak, extrator, migração, travamento, executor, processo, atos e aceite."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid
import zlib

import psycopg
import pytest
import yaml

from conftest import CONHECIMENTO, RAIZ
from analise import Falha, agora
from analise.acesso_arquivo import negar
from analise.ambiente import construir, travar
from analise.atos import MotorAnalise, main as analise_main
from analise.coleta import coletar
from analise.comparacao import comparar
from analise.extrator import conectar, configuracao, extrair
from analise.leitura import ler
from analise.materializacao import materializar
from analise.projecao import ASSINATURA, canonizar_png
from analise.publicacao import Catalogo, novo, restricao_das_origens, vencimento
from analise.receita import carregar, parametros, pre_voo, validar_sql
from analise.serializacao import canonizar
from analise.supervisor import prazo_extracao
from analise.unidade import MEMORY_HIGH, MEMORY_MAX, executar, sondar
import analise.unidade as mod_unidade


# ==============================================================================================
# Apoio comum do conjunto
# ==============================================================================================


def semear(admin, n=3):
    for i in range(n):
        ev_id = str(uuid.UUID(int=i + 1))
        ordem = "turno-" + str(i // 2)
        admin.execute(
            "INSERT INTO acervo.log VALUES(%s,'2026-11-01T00:00:00Z','engenharia',%s,%s,'segredo-nao-ler')",
            (ev_id, str(uuid.UUID(int=100)), ordem),
        )
        admin.execute(
            "INSERT INTO acervo.log_giro VALUES(%s,'repo','ler',0,'leitura',1,%s)",
            (ev_id, "codex" if i < 2 else "cli"),
        )


def publicar_minima(cat, pasta, receita):
    r = carregar(receita)
    r["saidas"] = {"tabelas": [{"nome": "x", "colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]}]}
    (pasta / "x.csv").write_text("id\n10\n2\n")
    ex = novo("ex")
    cat.abrir_execucao(ex, "preparar", "s", "o")
    m = {"serializacao": r["serializacao"], "saidas": {}}
    obj_id = cat.publicar(ex, r, "populacao-de-turnos", pasta, m)
    return obj_id, r, m, ex


def exit_de(chamada):
    with pytest.raises(Falha) as e:
        chamada()
    return e.value.exit


# ==============================================================================================
# Seção 1 — Receita: admissão antes do banco, tipos e estimativa quadrática
# ==============================================================================================


@pytest.mark.parametrize(
    "campo",
    [
        "tipo", "pergunta", "populacao", "metodo", "saidas", "serializacao",
        "codigo", "pilha", "corte", "consultas", "tabelas_de_origem", "chave_do_turno",
    ],
)
def test_campo_ausente_sai_2(receita, campo):
    r = yaml.safe_load((receita / "receita.yaml").read_text())
    r.pop(campo)
    (receita / "receita.yaml").write_text(yaml.safe_dump(r))
    with pytest.raises(Falha) as e:
        carregar(receita, "preparar")
    assert e.value.exit == 2


@pytest.mark.parametrize(
    "sql_texto,exit_esp",
    [
        ("select l.ts from acervo.log l", 2),
        ("select l.segredo from acervo.log l where l.ts < :corte", 4),
        ("select l.ts from acervo.log l where l.ts < :corte or true", 4),
        ("select pg_read_file('/etc/passwd') from acervo.log l where l.ts < :corte", 4),
        ("select l.ts from acervo.log l where l.ts < :corte; set transaction read write", 4),
        ("select l.ts from acervo.log l where l.ts < :corte union select l.ts from acervo.log l", 4),
    ],
)
def test_sql_contido(receita, sql_texto, exit_esp):
    r = carregar(receita)
    with pytest.raises(Falha) as e:
        validar_sql(sql_texto, r)
    assert e.value.exit == exit_esp


def test_coluna_corte_fora_da_declaracao(receita):
    r = yaml.safe_load((receita / "receita.yaml").read_text())
    r["corte"]["acervo.log"]["coluna"] = "segredo"
    (receita / "receita.yaml").write_text(yaml.safe_dump(r))
    with pytest.raises(Falha) as e:
        carregar(receita)
    assert e.value.exit == 2


def test_receita_usa_release_servida(receita, tmp_path):
    nova = tmp_path / "artefatos" / ("b" * 40)
    shutil.copytree(receita, nova / "analise/populacao-de-turnos")
    reg = {
        "populacao-de-turnos": {
            "tipo": "preparacao",
            "repositorio": "platafirma-conhecimento",
            "caminho": "analise/populacao-de-turnos",
        }
    }
    m = MotorAnalise(
        raiz=tmp_path, conhecimento=nova, registro=reg, instancia=tmp_path,
        sujeito="s", sessao="s", ordem="o",
    )
    p, _, reg_servido = m.receita("populacao-de-turnos", "preparar")
    assert p == nova / "analise/populacao-de-turnos"
    assert reg_servido["versao"] == "b" * 40


def test_receita_ausente_na_release_sai_3(tmp_path):
    nova = tmp_path / "artefatos" / ("b" * 40)
    nova.mkdir(parents=True)
    reg = {
        "populacao-de-turnos": {
            "tipo": "preparacao",
            "repositorio": "platafirma-conhecimento",
            "caminho": "analise/populacao-de-turnos",
        }
    }
    m = MotorAnalise(
        raiz=tmp_path, conhecimento=nova, registro=reg, instancia=tmp_path,
        sujeito="s", sessao="s", ordem="o",
    )
    with pytest.raises(Falha) as e:
        m.receita("populacao-de-turnos", "preparar")
    assert e.value.exit == 3
    assert e.value.causa == "receita-ausente-na-release"


def test_pre_voo_nao_aloca():
    with pytest.raises(Falha) as e:
        pre_voo({"metodo": "agrupamento-hierarquico", "populacao": {"n": 232916}})
    assert e.value.exit == 5
    assert pre_voo({"metodo": "linear", "populacao": {"n": 232916}}) == 0


@pytest.mark.parametrize("p", ["outro=1", "desde=sem-data", "desde=2026-01-01"])
def test_parametro_invalido(receita, p):
    with pytest.raises(Falha) as e:
        parametros(carregar(receita), [p])
    assert e.value.exit == 2


# ==============================================================================================
# Seção 2 — Refazer: comparação em três camadas
# ==============================================================================================


@pytest.mark.parametrize(
    "chave,camada",
    [
        ("ambiente", "ambiente"),
        ("receita", "ambiente"),
        ("entradas", "entrada"),
        ("saidas", "calculo"),
    ],
)
def test_camada_da_divergencia(chave, camada):
    original = {
        "receita": {"sha": "a"},
        "ambiente": {"python": "3.12.3"},
        "entradas": {"x": {"sha256": "a"}},
        "saidas": {"y": {"sha256": "b"}},
    }
    nova = {**original, chave: {"x": {"sha256": "z"}}}
    assert comparar(original, nova) == (1, camada)


def test_dependencia_ausente_sai_3(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="sem-lock"\nversion="1"\nrequires-python=">=3.12"\ndependencies=[]\n'
    )
    with pytest.raises(Falha) as e:
        construir(tmp_path, tmp_path / "cache")
    assert e.value.exit == 3


# ==============================================================================================
# Seção 3 — Projeção PNG e publicação
# ==============================================================================================


def _png_bytes(texto=b""):
    def chunk(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)

    return (
        ASSINATURA
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + (chunk(b"tEXt", texto) if texto else b"")
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff"))
        + chunk(b"IEND", b"")
    )


def test_metadado_variavel_nao_muda_hash(tmp_path):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(_png_bytes(b"data\x00ontem"))
    b.write_bytes(_png_bytes(b"data\x00hoje"))
    assert canonizar_png(a) == canonizar_png(b)
    assert canonizar_png(a)["dimensoes"] == [1, 1]


@pytest.mark.exige("host:casa")
def test_projecao_publicada(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    (out / "grafico.png").write_bytes(_png_bytes())
    r = carregar(receita)
    r["saidas"] = {"projecoes": ["grafico"]}
    ex = novo("ex")
    catalogo.abrir_execucao(ex, "preparar", "s", "o")
    obj = catalogo.publicar(ex, r, "png", out, {"serializacao": r["serializacao"]})
    assert catalogo.conn.execute("SELECT largura,altura FROM analise.projecao WHERE objeto_id=%s", (obj,)).fetchone() == (1, 1)


def test_crc_errado_recusa(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes()[:-1] + b"x")
    with pytest.raises(Falha) as e:
        canonizar_png(p)
    assert e.value.exit == 4


@pytest.mark.exige("host:casa")
def test_publicacao_atomica(catalogo, tmp_path, receita):
    r = carregar(receita)
    r["saidas"] = {"tabelas": [{"nome": "x", "colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]}]}
    out = tmp_path / "out"
    out.mkdir()
    (out / "x.csv").write_text("id\n1\n")
    ex = novo("ex")
    catalogo.abrir_execucao(ex, "preparar", "s", "o")

    def quebrar():
        raise RuntimeError("interrupcao")

    with pytest.raises(RuntimeError):
        catalogo.publicar(ex, r, "p", out, {"serializacao": r["serializacao"]}, antes_de_pronto=quebrar)
    assert catalogo.conn.execute("SELECT count(*) FROM analise.base").fetchone()[0] == 0
    assert catalogo.conn.execute("SELECT count(*) FROM analise.tabela").fetchone()[0] == 0
    assert catalogo.conn.execute("SELECT estado FROM analise.execucao WHERE id=%s", (ex,)).fetchone()[0] == "ativa"


@pytest.mark.exige("host:casa")
def test_base_adulterada(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id, _, _, _ = publicar_minima(catalogo, out, receita)
    base = catalogo.objeto(obj_id)
    receita_analise = {"base": {"receitas": ["populacao-de-turnos"], "tabelas": ["x"]}}
    a = tmp_path / "a"
    a.mkdir()
    b = tmp_path / "b"
    b.mkdir()
    assert materializar(catalogo, base, receita_analise, a) == materializar(catalogo, base, receita_analise, b)
    from psycopg import sql
    fisica = catalogo.conn.execute("SELECT fisica FROM analise.tabela WHERE objeto_id=%s", (obj_id,)).fetchone()[0]
    catalogo.conn.execute(sql.SQL("UPDATE analise.{} SET id=999 WHERE id=2").format(sql.Identifier(fisica)))
    c = tmp_path / "c"
    c.mkdir()
    with pytest.raises(Falha) as e:
        materializar(catalogo, base, receita_analise, c)
    assert e.value.exit == 5


def test_ordem_com_empate_recusa(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("id\n2\n2\n")
    with pytest.raises(Falha) as e:
        canonizar(
            p,
            {"colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]},
            {"nulo": "", "nan": "NaN", "datas": "utc", "decimais": 3},
        )
    assert e.value.exit == 4


@pytest.mark.exige("host:casa")
def test_manifesto_publicado_tem_medidas_finais(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id, _, m, ex = publicar_minima(catalogo, out, receita)
    publicado = catalogo.objeto(obj_id)["manifesto"]
    execucao = catalogo.execucao(ex)["manifesto"]
    assert publicado == execucao == m
    fase = publicado["fases"]["publicar"]
    assert fase["bytes"] == sum(x["bytes"] for x in publicado["saidas"].values()) > 0
    assert fase["duracao_s"] > 0 and fase["pico_bytes"] > 0


# ==============================================================================================
# Seção 4 — Coleta e guarda
# ==============================================================================================


@pytest.mark.exige("host:casa")
def test_ate_descarte_sobrevive(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id, _, _, _ = publicar_minima(catalogo, out, receita)
    assert catalogo.objeto(obj_id)["expires_at"] is None
    assert coletar(catalogo, tmp_path) == 0


def test_resultado_nao_supera_base():
    limite = agora() + timedelta(days=1)
    assert vencimento({"dias": 100}, limite) == limite
    assert vencimento({"ate_descarte": "homologacao"}, limite) == limite


@pytest.mark.exige("host:casa")
def test_vencido_impede_leitura(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id, _, _, ex = publicar_minima(catalogo, out, receita)
    catalogo.conn.execute("UPDATE analise.base SET expires_at=clock_timestamp()-interval '1 second' WHERE id=%s", (obj_id,))
    with pytest.raises(Falha) as e:
        catalogo.objeto(obj_id)
    assert e.value.exit == 5
    with pytest.raises(Falha) as e:
        catalogo.execucao(ex)
    assert e.value.exit == 5
    assert coletar(catalogo, tmp_path) == 1


@pytest.mark.exige("host:casa")
def test_outro_sujeito_le_pelo_padrao_e_nao_lista(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id, _, _, _ = publicar_minima(catalogo, out, receita)
    outro_cat = Catalogo(catalogo.conn, "outro")
    assert outro_cat.listar("bases") == []
    assert outro_cat.objeto(obj_id)["id"] == obj_id
    catalogo.conn.execute("DELETE FROM analise.entrega WHERE objeto_id=%s", (obj_id,))
    with pytest.raises(Falha) as e:
        outro_cat.objeto(obj_id)
    assert e.value.exit == 4


# ==============================================================================================
# Seção 5 — Entrega de base e resultado
# ==============================================================================================


def _publicar_base_entrega(cat, pasta, receita, entrega=None):
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
    return _publicar_base_entrega(catalogo, out, receita)


@pytest.fixture
def base(catalogo, base_padrao):
    catalogo.conn.execute("DELETE FROM analise.entrega WHERE objeto_id=%s", (base_padrao,))
    return base_padrao


def _outro_cat(catalogo, sujeito):
    return Catalogo(catalogo.conn, sujeito)


def _entregas_count(catalogo):
    return catalogo.conn.execute("SELECT count(*) FROM analise.entrega").fetchone()[0]


@pytest.mark.exige("host:casa")
def test_base_nova_nasce_entregue_a_todos(catalogo, base_padrao):
    assert _outro_cat(catalogo, "qualquer").objeto(base_padrao)["id"] == base_padrao
    assert catalogo.conn.execute(
        "SELECT sujeito, entregue_por FROM analise.entrega WHERE objeto_id=%s", (base_padrao,)
    ).fetchone() == ("*", "sujeito-teste")


@pytest.mark.exige("host:casa")
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
    assert _outro_cat(catalogo, "qualquer").objeto(rid)["id"] == rid


@pytest.mark.exige("host:casa")
def test_receita_privada_nao_entrega(catalogo, tmp_path, receita):
    out = tmp_path / "priv"
    out.mkdir()
    privada = _publicar_base_entrega(catalogo, out, receita, entrega="privada")
    assert _entregas_count(catalogo) == 0
    assert exit_de(lambda: _outro_cat(catalogo, "outro").objeto(privada)) == 4


def test_entrega_invalida_na_receita_recusa(receita):
    texto = (receita / "receita.yaml").read_text() + "entrega: aberta\n"
    (receita / "receita.yaml").write_text(texto)
    assert exit_de(lambda: carregar(receita)) == 2


@pytest.mark.exige("host:casa")
def test_sujeito_sem_entrega_recebe_exit_4(catalogo, base):
    assert exit_de(lambda: _outro_cat(catalogo, "outro").objeto(base)) == 4


@pytest.mark.exige("host:casa")
def test_entrega_a_um_sujeito_so_abre_para_ele(catalogo, base):
    assert catalogo.entregar(base, "outro")["estado"] == "entregue"
    assert _outro_cat(catalogo, "outro").objeto(base)["id"] == base
    assert exit_de(lambda: _outro_cat(catalogo, "terceiro").objeto(base)) == 4


@pytest.mark.exige("host:casa")
def test_entrega_a_todos_abre_para_qualquer_sujeito(catalogo, base):
    catalogo.entregar(base, "*")
    assert _outro_cat(catalogo, "terceiro").objeto(base)["id"] == base


@pytest.mark.exige("host:casa")
def test_so_quem_gerou_entrega(catalogo, base):
    assert exit_de(lambda: _outro_cat(catalogo, "outro").entregar(base, "*")) == 4
    assert _entregas_count(catalogo) == 0


@pytest.mark.exige("host:casa")
def test_objeto_vencido_nao_se_entrega(catalogo, base):
    catalogo.conn.execute("UPDATE analise.base SET expires_at = now() - interval '1 day' WHERE id=%s", (base,))
    assert exit_de(lambda: catalogo.entregar(base, "*")) == 5
    assert _entregas_count(catalogo) == 0


@pytest.mark.exige("host:casa")
def test_destino_invalido_nao_grava(catalogo, base):
    assert exit_de(lambda: catalogo.entregar(base, "a b; drop")) == 2
    assert _entregas_count(catalogo) == 0


@pytest.mark.exige("host:casa")
def test_entregar_duas_vezes_grava_uma(catalogo, base):
    catalogo.entregar(base, "outro")
    catalogo.entregar(base, "outro")
    assert _entregas_count(catalogo) == 1


@pytest.mark.exige("host:casa")
def test_quem_recebeu_nao_descarta_e_o_descarte_limpa_a_entrega(catalogo, base_padrao):
    assert exit_de(lambda: _outro_cat(catalogo, "outro").descartar(base_padrao)) == 4
    catalogo.descartar(base_padrao)
    assert _entregas_count(catalogo) == 0


# ==============================================================================================
# Seção 6 — Restrição por origem (Keycloak)
# ==============================================================================================

ORIGENS_COM_KEYCLOAK = [
    {"banco": "rag", "tabela": "acervo.log"},
    {"banco": "keycloak", "tabela": "public.user_entity"},
]


def _publicar_restrita(cat, pasta, receita):
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


@pytest.mark.exige("host:casa")
def test_objeto_restrito_so_abre_para_seguranca_e_ti(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id = _publicar_restrita(catalogo, out, receita)
    for cadeira in ("seguranca", "ti"):
        assert Catalogo(catalogo.conn, "sujeito-teste", cadeira).objeto(obj_id)["id"] == obj_id
    for cadeira in ("dados", "produto", ""):
        assert exit_de(lambda: Catalogo(catalogo.conn, "sujeito-teste", cadeira).objeto(obj_id)) == 4


@pytest.mark.exige("host:casa")
def test_a_entrega_a_todos_nao_abre_o_objeto_restrito(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id = _publicar_restrita(catalogo, out, receita)
    assert Catalogo(catalogo.conn, "outro", "ti").objeto(obj_id)["id"] == obj_id
    assert exit_de(lambda: Catalogo(catalogo.conn, "outro", "dados").objeto(obj_id)) == 4


@pytest.mark.exige("host:casa")
def test_quem_gerou_ainda_descarta_o_objeto_restrito(catalogo, tmp_path, receita):
    out = tmp_path / "out"
    out.mkdir()
    obj_id = _publicar_restrita(catalogo, out, receita)
    catalogo.descartar(obj_id)
    assert catalogo.conn.execute("SELECT count(*) FROM analise.base").fetchone()[0] == 0


# ==============================================================================================
# Seção 7 — Extrator e configuração de destino
# ==============================================================================================

ANALISE_DESTINO = {"conteiner": "analise-db", "base": "analise", "dono": "analise", "porta": 5440}


def _registro_destino(tmp_path, monkeypatch, reg):
    arq = tmp_path / "bancos-destino.json"
    arq.write_text(json.dumps(reg))
    monkeypatch.setenv("PF_ANALISE_BANCOS", str(arq))


def _cofre_destino(tmp_path, monkeypatch, senha="senha-de-teste"):
    instancia = tmp_path / "instancia"
    cofre = instancia / "segredos/analise-db"
    cofre.mkdir(parents=True, exist_ok=True)
    if senha is not None:
        (cofre / "ANALISE_DESTINO_PASSWORD").write_text(senha + "\n")
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(instancia))


@pytest.mark.exige("host:casa")
def test_extracao_corte_e_rollback(db, bancos, receita, tmp_path):
    _, admin = db
    semear(admin)
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    meta = extrair(None, carregar(receita), receita, entrada, datetime(2026, 11, 2, tzinfo=timezone.utc))
    assert meta["giros"]["linhas"] == 3
    assert meta["giros"]["banco"] == "rag" and meta["giros"]["role"] == "analise_leitura@rag"
    assert "segredo-nao-ler" not in (entrada / "giros.csv").read_text()
    assert meta["giros"]["snapshot"]
    pasta = tmp_path / "vazia"
    pasta.mkdir()
    assert extrair(None, carregar(receita), receita, pasta, datetime(2026, 10, 1, tzinfo=timezone.utc))["giros"]["linhas"] == 0
    assert not admin.execute("SELECT 1 FROM pg_stat_activity WHERE usename='analise_leitura' AND state like 'idle in%'").fetchone()


@pytest.mark.exige("host:casa")
def test_cruza_dois_bancos_na_mesma_receita(db, bancos, receita, tmp_path):
    _, admin = db
    semear(admin)
    admin.execute("CREATE TABLE IF NOT EXISTS public.card(id integer PRIMARY KEY,titulo text,estado text)")
    admin.execute("TRUNCATE public.card")
    admin.execute("INSERT INTO public.card VALUES(4185,'analise lê todo banco','em-mitigacao'),(4184,'cadernos','priorizada')")
    r = yaml.safe_load((receita / "receita.yaml").read_text())
    r["tabelas_de_origem"].append({"banco": "rastreador", "tabela": "public.card", "colunas": ["id", "titulo", "estado"]})
    r["corte"]["rastreador/public.card"] = {"por": "snapshot"}
    r["consultas"].append({"nome": "cards", "arquivo": "cards.sql"})
    (receita / "cards.sql").write_text("select c.id, c.titulo, c.estado from public.card c order by c.id\n")
    (receita / "receita.yaml").write_text(yaml.safe_dump(r, allow_unicode=True))
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    meta = extrair(None, carregar(receita), receita, entrada, datetime(2026, 11, 2, tzinfo=timezone.utc))
    assert meta["giros"]["banco"] == "rag" and meta["cards"]["banco"] == "rastreador"
    assert meta["cards"]["linhas"] == 2
    assert "analise lê todo banco" in (entrada / "cards.csv").read_text()


def test_consulta_que_cruza_bancos_no_sql_recusa(receita, tmp_path, monkeypatch):
    _registro_destino(
        tmp_path, monkeypatch,
        {
            "rag": {"conteiner": "rag-pg", "base": "postgres", "dono": "postgres"},
            "rastreador": {"conteiner": "rastreador-pg", "base": "postgres", "dono": "postgres"},
        },
    )
    r = yaml.safe_load((receita / "receita.yaml").read_text())
    r["tabelas_de_origem"].append({"banco": "rastreador", "tabela": "public.card", "colunas": ["id"]})
    r["corte"]["rastreador/public.card"] = {"por": "snapshot"}
    r["consultas"].append({"nome": "mistura", "arquivo": "mistura.sql"})
    (receita / "mistura.sql").write_text("select c.id from public.card c join acervo.log l on l.ordem_id = c.id where l.ts < :corte\n")
    (receita / "receita.yaml").write_text(yaml.safe_dump(r, allow_unicode=True))
    with pytest.raises(Falha) as e:
        carregar(receita)
    assert e.value.causa == "consulta-cruza-bancos"


def test_banco_fora_do_registro_recusa(receita, tmp_path, monkeypatch):
    _registro_destino(
        tmp_path, monkeypatch,
        {"rag": {"conteiner": "rag-pg", "base": "postgres", "dono": "postgres"}},
    )
    r = yaml.safe_load((receita / "receita.yaml").read_text())
    r["tabelas_de_origem"][0]["banco"] = "inventado"
    (receita / "receita.yaml").write_text(yaml.safe_dump(r, allow_unicode=True))
    with pytest.raises(Falha) as e:
        carregar(receita)
    assert e.value.causa == "banco-fora-do-registro:inventado"


@pytest.mark.exige("host:casa")
def test_leitura_alcanca_toda_coluna(db):
    _, admin = db
    semear(admin, 1)
    import conftest
    p = subprocess.run(
        ["docker", "exec", "-i", conftest.CONTEINER_PG, "psql", "-X", "-A", "-t", "-U", "analise_leitura", "-d", "postgres"],
        input="SELECT segredo FROM acervo.log;", capture_output=True, text=True, timeout=30,
    )
    assert p.returncode == 0 and p.stdout.strip() == "segredo-nao-ler"


@pytest.mark.exige("host:casa")
def test_leitura_nao_escreve(db):
    import conftest
    for sql_cmd in (
        "INSERT INTO acervo.log(ordem_id) VALUES('fuga');",
        "BEGIN READ WRITE; INSERT INTO acervo.log(ordem_id) VALUES('fuga'); COMMIT;",
        "CREATE TABLE public.fuga(x int);",
    ):
        p = subprocess.run(
            ["docker", "exec", "-i", conftest.CONTEINER_PG, "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "analise_leitura", "-d", "postgres"],
            input=sql_cmd, capture_output=True, text=True, timeout=30,
        )
        assert p.returncode != 0
    _, admin = db
    assert admin.execute("SELECT count(*) FROM acervo.log WHERE ordem_id='fuga'").fetchone()[0] == 0


@pytest.mark.exige("host:casa")
def test_role_ausente_diz_o_conserto(db, bancos, receita, tmp_path, monkeypatch):
    import conftest
    arq = tmp_path / "sem-role.json"
    arq.write_text(json.dumps({"rag": {"conteiner": conftest.CONTEINER_PG, "base": "banco_que_nao_existe", "dono": "postgres"}}))
    monkeypatch.setenv("PF_ANALISE_BANCOS", str(arq))
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    with pytest.raises(Falha) as e:
        extrair(None, carregar(receita), receita, entrada, datetime(2026, 11, 2, tzinfo=timezone.utc))
    assert e.value.exit in (3, 5) and e.value.causa.endswith(":rag")


@pytest.mark.exige("host:casa")
def test_prazo_fecha_transacao(db):
    cfg, admin = db
    c = psycopg.connect(**{**cfg, "user": "analise_extracao"})
    pid = c.info.backend_pid
    with pytest.raises(Falha) as e:
        with prazo_extracao(c, 0.1):
            c.execute("BEGIN READ ONLY")
            c.execute("SELECT pg_sleep(5)")
    assert e.value.exit == 5 and c.closed
    assert not admin.execute("SELECT 1 FROM pg_stat_activity WHERE pid=%s", (pid,)).fetchone()


@pytest.mark.exige("host:casa")
def test_duas_consultas_mesmo_snapshot(db, bancos, receita, tmp_path):
    _, admin = db
    semear(admin)
    r = carregar(receita)
    r["consultas"] = [{"nome": "primeira", "arquivo": "giros.sql"}, {"nome": "segunda", "arquivo": "giros.sql"}]
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    m = extrair(None, r, receita, entrada, datetime(2026, 11, 2, tzinfo=timezone.utc))
    assert m["primeira"]["linhas"] == m["segunda"]["linhas"] == 3
    assert m["primeira"]["snapshot"] == m["segunda"]["snapshot"]


def test_destino_lido_do_registro(tmp_path, monkeypatch):
    _registro_destino(
        tmp_path, monkeypatch,
        {"rag": {"conteiner": "rag-extractor-pg", "base": "rag_extractor", "dono": "rag"}, "analise": ANALISE_DESTINO},
    )
    _cofre_destino(tmp_path, monkeypatch)
    for chave in ("ANALISE_DESTINO_HOST", "ANALISE_DESTINO_PORT", "ANALISE_DESTINO_DB"):
        monkeypatch.setenv(chave, "desvio" if chave != "ANALISE_DESTINO_PORT" else "5432")
    c = configuracao("destino")
    assert (c["host"], c["port"], c["dbname"], c["user"]) == ("127.0.0.1", 5440, "analise", "analise_publicacao")
    assert c["password"] == "senha-de-teste"


def test_destino_fora_do_registro_sai_3(tmp_path, monkeypatch):
    _registro_destino(
        tmp_path, monkeypatch,
        {"rag": {"conteiner": "rag-extractor-pg", "base": "rag_extractor", "dono": "rag"}},
    )
    _cofre_destino(tmp_path, monkeypatch)
    with pytest.raises(Falha) as e:
        configuracao("destino")
    assert e.value.exit == 3 and e.value.causa == "destino-fora-do-registro:analise"


def test_destino_sem_porta_sai_3(tmp_path, monkeypatch):
    _registro_destino(
        tmp_path, monkeypatch,
        {"analise": {k: v for k, v in ANALISE_DESTINO.items() if k != "porta"}},
    )
    _cofre_destino(tmp_path, monkeypatch)
    with pytest.raises(Falha) as e:
        configuracao("destino")
    assert e.value.exit == 3 and e.value.causa == "destino-incompleto-no-registro:analise"


@pytest.mark.parametrize("senha", [None, "", "   "])
def test_destino_sem_senha_sai_3(tmp_path, monkeypatch, senha):
    _registro_destino(tmp_path, monkeypatch, {"analise": ANALISE_DESTINO})
    _cofre_destino(tmp_path, monkeypatch, senha)
    with pytest.raises(Falha) as e:
        configuracao("destino")
    assert e.value.exit == 3 and e.value.causa == "credencial-ausente:segredos/analise-db/ANALISE_DESTINO_PASSWORD"


def test_destino_que_nao_responde_sai_5_sem_fallback(tmp_path, monkeypatch):
    _registro_destino(
        tmp_path, monkeypatch,
        {"rag": {"conteiner": "rag-extractor-pg", "base": "rag_extractor", "dono": "rag"}, "analise": ANALISE_DESTINO},
    )
    _cofre_destino(tmp_path, monkeypatch)
    tentativas = []

    def recusa(**kw):
        tentativas.append(kw)
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", recusa)
    with pytest.raises(Falha) as e:
        conectar("destino")
    assert e.value.exit == 5 and e.value.causa == "banco-indisponivel"
    assert [(t["port"], t["dbname"]) for t in tentativas] == [(5440, "analise")]


# ==============================================================================================
# Seção 8 — Migração e privilégios no PostgreSQL 16
# ==============================================================================================


@pytest.mark.exige("host:casa")
def test_grants_e_limites(pg):
    cfg, admin = pg
    assert admin.execute("SHOW server_version_num").fetchone()[0].startswith("16")
    assert not admin.execute("SELECT has_table_privilege('analise_extracao','acervo.log','SELECT')").fetchone()[0]
    assert admin.execute("SELECT has_column_privilege('analise_extracao','acervo.log','ts','SELECT')").fetchone()[0]
    assert not admin.execute("SELECT has_column_privilege('analise_extracao','acervo.log','segredo','SELECT')").fetchone()[0]
    assert not admin.execute("SELECT has_table_privilege('analise_publicacao','acervo.log','SELECT')").fetchone()[0]
    assert not admin.execute("SELECT has_schema_privilege('analise_extracao','analise','USAGE')").fetchone()[0]
    with psycopg.connect(**{**cfg, "user": "analise_extracao"}, autocommit=True) as conn:
        assert conn.execute("SHOW temp_file_limit").fetchone()[0] == "256MB"
        assert conn.execute("SHOW default_transaction_read_only").fetchone()[0] == "on"
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT segredo FROM acervo.log")


@pytest.mark.exige("host:casa")
def test_migracao_idempotente(pg):
    _, admin = pg
    with admin.transaction():
        admin.execute((CONHECIMENTO / "rag/db/init/159_schema_analise.sql").read_text())
    assert admin.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='analise' AND table_name IN ('execucao','base','resultado','tabela','projecao')"
    ).fetchone()[0] == 5


# ==============================================================================================
# Seção 9 — Travamento de pilha (uv lock)
# ==============================================================================================


@pytest.mark.exige("host:casa")
def test_travar_pilha_sem_pacotes(tmp_path):
    p = tmp_path / "receita"
    p.mkdir()
    (p / "pyproject.toml").write_text('[project]\nname="analise-vazia"\nversion="1"\nrequires-python=">=3.12"\ndependencies=[]\n')
    sha = travar(p, tmp_path / "cache")
    assert len(sha) == 64 and (p / "uv.lock").is_file()
    env, ident = construir(p, tmp_path / "ambientes")
    assert (env / "bin/python").is_file()
    assert ident["python"].startswith("3.12")


@pytest.mark.exige("host:casa")
def test_travar_dependencia_impossivel(tmp_path):
    p = tmp_path / "receita"
    p.mkdir()
    (p / "pyproject.toml").write_text('[project]\nname="analise-impossivel"\nversion="1"\nrequires-python=">=3.12"\ndependencies=["pandas==0.0.0"]\n')
    with pytest.raises(Falha) as e:
        travar(p, tmp_path / "cache")
    assert e.value.exit == 2 and "pandas" in e.value.causa


# ==============================================================================================
# Seção 10 — Executor e unidade de isolamento
# ==============================================================================================


@pytest.mark.exige("host:casa")
def test_host_tem_mecanismo_de_isolamento(tmp_path):
    resultado = sondar()
    relatorio = tmp_path / "sonda.json"
    relatorio.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    assert resultado["systemd"]["exit"] == 0, resultado
    medido = json.loads(resultado["systemd"]["stdout"].strip())
    assert medido["memory.max"] == str(MEMORY_MAX), medido
    assert medido["memory.high"] == str(MEMORY_HIGH), medido
    assert medido["memory.swap.max"] == "0", medido
    assert medido["pids.max"] == "64", medido
    assert medido["inet"] != "permitido", medido
    assert medido["unix"] != "permitido", medido


@pytest.mark.exige("host:casa")
@pytest.mark.parametrize(
    "codigo,esperado",
    [
        ("from pathlib import Path\nPath('/saida/tabela.csv').write_text('a\\n1\\n')", 0),
        ("import socket\nsocket.socket()", 4),
        ("import socket\nsocket.socket(socket.AF_UNIX)", 4),
        ("open('/srv/platafirma/casa/segredos/rag/POSTGRES_PASSWORD').read()", 4),
        ("open('/entrada/dado','w').write('x')", 4),
        ("open('/tmp/fuga','w').write('x')", 4),
        ("import subprocess\nsubprocess.Popen(['/usr/bin/sleep','30'])", 4),
        ("import modulo_inexistente_4130", 4),
    ],
)
def test_calculo_contem_tentativas(tmp_path, codigo, esperado):
    receita = tmp_path / "receita"
    receita.mkdir()
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    saida = tmp_path / "saida"
    saida.mkdir()
    (receita / "rodar.py").write_text(codigo)
    rc, metricas = executar(
        [sys.executable, "-I", "-B", "/executor.py", "rodar.py"],
        pasta=receita, entrada=entrada, saida=saida, ambiente=Path(sys.prefix),
    )
    assert rc == esperado
    assert metricas["pico_bytes"] > 0


@pytest.mark.exige("host:casa")
def test_calculo_importa_pacote_do_venv_fora_de_opt(tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    sitio = next((venv / "lib").glob("python3*/site-packages"))
    (sitio / "modulo_4140.py").write_text("VALOR=1\n")
    receita = tmp_path / "receita"
    receita.mkdir()
    saida = tmp_path / "saida"
    saida.mkdir()
    (receita / "rodar.py").write_text("import modulo_4140\nassert modulo_4140.VALOR==1")
    rc, _ = executar(
        [str(venv / "bin/python"), "-I", "-B", "/executor.py", "rodar.py"],
        pasta=receita, saida=saida, ambiente=venv,
    )
    assert rc == 0


@pytest.mark.exige("host:casa")
def test_prazo_mata_so_a_unidade(tmp_path):
    receita = tmp_path / "receita"
    receita.mkdir()
    saida = tmp_path / "saida"
    saida.mkdir()
    (receita / "rodar.py").write_text("import time\ntime.sleep(30)")
    with pytest.raises(Falha) as e:
        executar(
            [sys.executable, "-I", "-B", "/executor.py", "rodar.py"],
            pasta=receita, saida=saida, ambiente=Path(sys.prefix), prazo=1,
        )
    assert e.value.exit == 5


def test_oom_mata_so_a_unidade(tmp_path, monkeypatch):
    receita = tmp_path / "receita"
    receita.mkdir()
    saida = tmp_path / "saida"
    saida.mkdir()
    (receita / "rodar.py").write_text("x = bytearray(1024 * 1024)\n")
    teto = 128 * 1024**2

    def _rodar_falso(argv: list[str]) -> dict:
        if argv[:2] == ["systemctl", "--user"] and argv[2] == "show":
            return {
                "exit": 0,
                "stdout": (
                    "Result=oom-kill\n"
                    "ExecMainStatus=9\n"
                    f"MemoryPeak={teto}\n"
                    f"MemoryMax={teto}\n"
                    f"MemoryHigh={teto}\n"
                    "MemorySwapMax=0\n"
                    "TasksMax=64\n"
                    "SubState=failed\n"
                    "ActiveState=failed\n"
                ),
                "stderr": "",
            }
        return {"exit": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(mod_unidade, "_rodar", _rodar_falso)
    with pytest.raises(Falha) as e:
        executar(
            [sys.executable, "-I", "-B", "/executor.py", "rodar.py"],
            pasta=receita, saida=saida, ambiente=Path(sys.prefix),
            _tetos_memoria=(teto, teto),
        )
    assert e.value.exit == 5 and e.value.causa == "teto-oom-kill"


# ==============================================================================================
# Seção 11 — Processo, atos e aceite ponta a ponta
# ==============================================================================================


@pytest.mark.exige("host:casa")
def test_cli_em_unidade_dedicada(db, bancos, tmp_path):
    cfg, admin = db
    semear(admin)
    servido = tmp_path / "release"
    servido.mkdir()
    (servido / "conhecimento").symlink_to(CONHECIMENTO, target_is_directory=True)
    politica = servido / "core/acesso"
    politica.mkdir(parents=True)
    from raizes import release

    acesso_core = (
        RAIZ.parent / "core/acesso"
        if (RAIZ.parent / "core/acesso").is_dir()
        else release() / "core/acesso"
    )
    for nome in ("pdp.py", "politica.yaml"):
        shutil.copy2(acesso_core / nome, politica / nome)
    (politica / "sujeitos.yaml").write_text(
        "sujeitos:\n  teste:\n    natureza: pessoa\n    papeis: [operador]\n    dominios: [plataforma]\n"
    )
    instancia = tmp_path / "instancia"
    cofre = instancia / "segredos/analise-db"
    cofre.mkdir(parents=True)
    (cofre / "ANALISE_DESTINO_PASSWORD").write_text(cfg["password"])
    env = {
        **os.environ,
        "PLATAFIRMA_RELEASE": str(servido),
        "PLATAFIRMA_INSTANCIA": str(instancia),
        "PF_SUJEITO": "teste",
        "PF_SESSAO": "teste",
        "PF_ORDEM_ID": "teste-cli",
        "PF_CADEIRA": "engenharia",
    }
    p = subprocess.run(
        [sys.executable, str(RAIZ / "bin/analise"), "preparar", "populacao-de-turnos", "--corte", "2026-11-02T00:00:00Z"],
        env=env, capture_output=True, text=True, timeout=60, check=False,
    )
    assert p.returncode == 0, p.stdout
    doc = json.loads(p.stdout)
    assert doc["exit"] == 0 and doc["base_id"]
    assert doc["manifesto"]["fases"]["extrair"]["pico_bytes"] > 0
    assert doc["manifesto"]["unidade"].startswith("platafirma-analise-trabalho-")


@pytest.mark.parametrize("args", [["--ajuda"], ["preparar", "inexistente"], ["montar", "contagem-por-fonte"]])
def test_jornada_termina_no_guia(args, capsys, monkeypatch, tmp_path):
    motor = MotorAnalise(raiz=tmp_path, conhecimento=tmp_path, registro={}, instancia=tmp_path, sujeito="s", sessao="s", ordem="o")
    monkeypatch.setattr("analise.atos.runtime", lambda: motor)
    rc = analise_main(args)
    assert rc == (0 if args == ["--ajuda"] else 2)
    assert capsys.readouterr().out.rstrip().splitlines()[-1] == "analise --guia preparacao"


def test_guia_lido_na_chamada(monkeypatch, capsys):
    monkeypatch.setattr("analise.guia.ler", lambda: "guia em vigor\n")
    assert analise_main(["--guia", "preparacao"]) == 0
    assert capsys.readouterr().out == "guia em vigor\n"


def test_guia_sem_acesso_sai_3(monkeypatch, capsys):
    from analise.guia import CAMINHO

    def indisponivel():
        raise Falha(3, "guia-indisponivel", CAMINHO)

    monkeypatch.setattr("analise.guia.ler", indisponivel)
    assert analise_main(["--guia", "preparacao"]) == 3
    assert CAMINHO in capsys.readouterr().out


@pytest.mark.exige("host:casa")
def test_arquivo_de_outro_sujeito_recusa(catalogo, tmp_path, receita, db):
    cfg, _ = db
    out = tmp_path / "out"
    out.mkdir()
    _, _, _, ex = publicar_minima(catalogo, out, receita)
    instancia = tmp_path / "instancia"
    p = instancia / "var/tmp/o/analise" / ex / "entrada/x.csv"
    p.parent.mkdir(parents=True)
    p.write_text("privado")
    conexao = lambda parte: psycopg.connect(**{**cfg, "user": "analise_publicacao"})
    assert not negar(p, "sujeito-teste", instancia, conexao)
    assert negar(p, "outro", instancia, conexao)
    assert negar(p, "", instancia, conexao)


@pytest.mark.exige("host:casa")
def test_listar_bases_e_resultados_com_receita_corte_guarda_e_estado(catalogo, tmp_path, db, monkeypatch, capsys):
    cfg, _ = db
    out1 = tmp_path / "out1"
    out1.mkdir()
    r1 = {
        "tipo": "preparacao",
        "pergunta": "Pergunta da base A",
        "guarda": {"ate_descarte": "homologacao"},
        "saidas": {"tabelas": [{"nome": "x", "colunas": [{"nome": "id", "tipo": "inteiro"}], "ordem": ["id"]}]},
        "serializacao": {"nulo": "", "nan": "NaN", "datas": "utc", "decimais": 3},
    }
    (out1 / "x.csv").write_text("id\n10\n2\n")
    ex1 = novo("ex")
    catalogo.abrir_execucao(ex1, "preparar", "s", "o")
    catalogo.publicar(ex1, r1, "populacao-de-turnos", out1, {"serializacao": r1["serializacao"], "corte": "2026-11-02T00:00:00Z", "saidas": {}})

    out2 = tmp_path / "out2"
    out2.mkdir()
    (out2 / "x.csv").write_text("id\n1\n")
    ex2 = novo("ex")
    catalogo.abrir_execucao(ex2, "preparar", "s", "o")
    b2 = catalogo.publicar(ex2, r1, "mineracao-ocel", out2, {"serializacao": r1["serializacao"], "corte": "2026-11-10T00:00:00Z", "saidas": {}})

    out_res = tmp_path / "res"
    out_res.mkdir()
    (out_res / "y.csv").write_text("n\n7\n")
    r_res = {
        "tipo": "analise",
        "pergunta": "Pergunta do resultado",
        "guarda": {"dias": 7},
        "saidas": {"tabelas": [{"nome": "y", "colunas": [{"nome": "n", "tipo": "inteiro"}], "ordem": ["n"]}]},
        "serializacao": r1["serializacao"],
    }
    ex_res = novo("ex")
    catalogo.abrir_execucao(ex_res, "montar", "s", "o")
    res_id = catalogo.publicar(ex_res, r_res, "contagem-por-fonte", out_res, {"serializacao": r1["serializacao"], "saidas": {}}, catalogo.objeto(b2))

    conexao = lambda parte: psycopg.connect(**{**cfg, "user": "analise_publicacao"})
    motor = MotorAnalise(
        raiz=tmp_path, conhecimento=tmp_path, registro={}, instancia=tmp_path,
        sujeito="sujeito-teste", sessao="s", ordem="o", conexao=conexao, autorizar=lambda *a: {"versao": "teste"},
    )
    monkeypatch.setattr("analise.atos.runtime", lambda: motor)

    assert analise_main(["listar", "bases", "--receita", "mineracao-ocel"]) == 0
    bloco = json.loads(capsys.readouterr().out)
    assert [it["id"] for it in bloco["itens"]] == [b2]
    item = bloco["itens"][0]
    assert item["receita"] == "mineracao-ocel"
    assert item["pergunta"] == "Pergunta da base A"
    assert item["corte"] == "2026-11-10T00:00:00Z"
    assert item["guarda"] == {"ate_descarte": "homologacao"}
    assert item["estado"] == "pronta"

    assert analise_main(["listar", "resultados", "--receita", "contagem-por-fonte"]) == 0
    bloco_r = json.loads(capsys.readouterr().out)
    assert [it["id"] for it in bloco_r["itens"]] == [res_id]
    it_r = bloco_r["itens"][0]
    assert it_r["receita"] == "contagem-por-fonte"
    assert it_r["base_id"] == b2
    assert it_r["pergunta"] == "Pergunta do resultado"
    assert it_r["corte"] == "2026-11-10T00:00:00Z"
    assert it_r["guarda"] == {"dias": 7}
    assert it_r["estado"] == "pronta"


@pytest.fixture
def motor(db, bancos, tmp_path):
    cfg, admin = db
    semear(admin)
    reg = {
        "populacao-de-turnos": {"tipo": "preparacao", "repositorio": "platafirma-conhecimento", "caminho": "analise/populacao-de-turnos", "versao": "teste"},
        "contagem-por-fonte": {"tipo": "analise", "repositorio": "platafirma-conhecimento", "caminho": "analise/contagem-por-fonte", "versao": "teste"},
    }
    conhecimento = tmp_path / "conhecimento"
    shutil.copytree(CONHECIMENTO / "analise", conhecimento / "analise")
    for slug in reg:
        travar(conhecimento / "analise" / slug, tmp_path / "cache")

    def conexao(parte):
        return psycopg.connect(**{**cfg, "user": "analise_extracao" if parte == "origem" else "analise_publicacao"})

    return MotorAnalise(
        raiz=RAIZ, conhecimento=conhecimento, registro=reg,
        instancia=tmp_path / "instancia", sujeito="sujeito-teste", sessao="s", ordem="o",
        conexao=conexao, autorizar=lambda *args: {"versao": "teste"},
    )


@pytest.mark.exige("host:casa")
def test_preparar_montar_e_refazer(motor, db):
    rc, base_doc = motor.rodar("preparar", "populacao-de-turnos", corte="2026-11-02T00:00:00Z")
    assert rc == 0, base_doc
    assert base_doc["manifesto"]["entradas"]["giros"]["linhas"] == 3
    assert base_doc["manifesto"]["saidas"]["turnos"]["linhas"] == 2
    assert base_doc["expires_at"] is None
    rc, resultado = motor.rodar("montar", "contagem-por-fonte", base_id=base_doc["base_id"])
    assert rc == 0, resultado
    cat = motor.catalogo()
    dados = ler(cat, resultado["resultado_id"], "contagem", "1-10", None, motor.tmp / "o")
    assert dados["linhas"] == [("cli", 1), ("codex", 1)]
    with pytest.raises(Falha) as erro:
        cat.descartar(base_doc["base_id"])
    assert erro.value.exit == 2
    cat.conn.close()
    for ex in (base_doc["execucao_id"], resultado["execucao_id"]):
        rc, repetido = motor.rodar("refazer", origem=ex)
        assert rc == 0, repetido
    _, admin = db
    ev_id = str(uuid.UUID(int=99))
    admin.execute(
        "INSERT INTO acervo.log VALUES(%s,'2026-11-01T01:00:00Z','engenharia',%s,'turno-tardio','segredo')",
        (ev_id, str(uuid.UUID(int=100))),
    )
    admin.execute("INSERT INTO acervo.log_giro VALUES(%s,'repo','ler',0,'leitura',1,'codex')", (ev_id,))
    rc, divergente = motor.rodar("refazer", origem=base_doc["execucao_id"], reler=True)
    assert rc == 1 and divergente["causa"] == "entrada", divergente


def test_receita_desconhecida_sem_abrir_banco(tmp_path):
    def nao_conectar(_):
        raise AssertionError("abriu banco antes da admissão")

    m = MotorAnalise(
        raiz=RAIZ, conhecimento=tmp_path, registro={}, instancia=tmp_path,
        sujeito="s", sessao="s", ordem="o", conexao=nao_conectar,
    )
    rc, r = m.rodar("preparar", "inexistente")
    assert rc == 2 and r["causa"] == "receita-fora-do-registro"
