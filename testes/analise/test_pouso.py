# componente: componente:analise
"""Pouso de arquivo externo em tabela declarada, com linhagem, corte e leitura por receita."""

from datetime import datetime, timezone
import json
import yaml
import psycopg
import pytest

from analise import Falha
from analise.atos import MotorAnalise, main
from analise.extrator import extrair
from analise.pouso import carregar, normalizar_tabela
from analise.receita import carregar as carregar_receita


def test_normalizar_tabela_recusa_schema_alheio():
    assert normalizar_tabela("github_migracao") == "pouso_github_migracao"
    assert normalizar_tabela("pouso_github_migracao") == "pouso_github_migracao"
    assert normalizar_tabela("analise.pouso_github_migracao") == "pouso_github_migracao"
    for ruim in ("acervo.log", "public.card", "../etc", ""):
        with pytest.raises(Falha) as e:
            normalizar_tabela(ruim)
        assert e.value.exit == 2


def test_carregar_e_ler_pela_receita_com_corte_e_linhagem(db, bancos, receita, tmp_path, monkeypatch, capsys):
    cfg, admin = db
    arq = tmp_path / "github_issues.jsonl"
    arq.write_text(
        json.dumps({"id": 101, "titulo": "Primeira issue", "autor": "dono"}) + "\n"
        + json.dumps({"id": 102, "titulo": "Segunda issue", "autor": "cadeira"}) + "\n",
        encoding="utf-8",
    )

    conexao = lambda parte: psycopg.connect(**{**cfg, "user": "analise_publicacao"})
    motor = MotorAnalise(
        raiz=tmp_path,
        conhecimento=tmp_path,
        registro={},
        instancia=tmp_path,
        sujeito="sujeito-teste",
        sessao="s",
        ordem="o",
        conexao=conexao,
        autorizar=lambda *a: {"versao": "teste"},
    )
    monkeypatch.setattr("analise.atos.runtime", lambda: motor)

    assert main([
        "carregar",
        "github_migracao",
        "--arquivo",
        str(arq),
        "--corte",
        "2026-11-10T00:00:00Z",
    ]) == 0
    bloco = json.loads(capsys.readouterr().out)
    assert bloco["tabela"] == "analise.pouso_github_migracao"
    assert bloco["linhas"] == 2
    assert bloco["fonte_sha256"]
    assert bloco["carga_id"].startswith("cg-")

    # Segunda carga incremental com corte posterior.
    arq2 = tmp_path / "github_issues_2.csv"
    arq2.write_text("id,titulo,autor\n103,Terceira issue,dono\n", encoding="utf-8")
    assert main([
        "carregar",
        "analise.pouso_github_migracao",
        "--arquivo",
        str(arq2),
        "--corte",
        "2026-11-15T00:00:00Z",
        "--modo",
        "acrescentar",
    ]) == 0
    bloco2 = json.loads(capsys.readouterr().out)
    assert bloco2["linhas"] == 1

    # Linhagem registrada no catálogo de cargas.
    cargas = admin.execute("SELECT count(*) FROM analise.pouso_carga WHERE tabela='analise.pouso_github_migracao'").fetchone()[0]
    assert cargas == 2

    # Receita lê a tabela de pouso do banco `analise` com corte temporal.
    r = yaml.safe_load((receita / "receita.yaml").read_text())
    r["tabelas_de_origem"] = [
        {
            "banco": "analise",
            "tabela": "analise.pouso_github_migracao",
            "colunas": ["id", "titulo", "autor", "corte_em", "fonte_sha256"],
        }
    ]
    r["corte"] = {
        "analise/analise.pouso_github_migracao": {
            "por": "instante",
            "coluna": "corte_em",
            "margem": "0s",
            "margem_estimada": False,
            "garantia": "fechado",
        }
    }
    r["consultas"] = [{"nome": "forge", "arquivo": "forge.sql"}]
    (receita / "forge.sql").write_text(
        "select p.id, p.titulo, p.fonte_sha256 from analise.pouso_github_migracao p where p.corte_em < :corte order by p.id\n"
    )
    (receita / "receita.yaml").write_text(yaml.safe_dump(r, allow_unicode=True))

    entrada = tmp_path / "entrada"
    entrada.mkdir()
    meta = extrair(None, carregar_receita(receita), receita, entrada, datetime(2026, 11, 12, tzinfo=timezone.utc))
    assert meta["forge"]["banco"] == "analise"
    assert meta["forge"]["linhas"] == 2
    conteudo = (entrada / "forge.csv").read_text()
    assert "Primeira issue" in conteudo
    assert "Terceira issue" not in conteudo


def test_carregar_recusa_symlink_e_arquivo_ausente(db, tmp_path):
    cfg, _ = db
    with psycopg.connect(**{**cfg, "user": "analise_publicacao"}) as conn:
        with pytest.raises(Falha) as e:
            carregar(conn, "s", "teste", tmp_path / "nao_existe.csv")
        assert e.value.exit == 2
        alvo = tmp_path / "real.csv"
        alvo.write_text("a\n1\n")
        link = tmp_path / "link.csv"
        link.symlink_to(alvo)
        with pytest.raises(Falha) as e2:
            carregar(conn, "s", "teste", link)
        assert e2.value.exit == 2
