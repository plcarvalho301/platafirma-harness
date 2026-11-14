"""Cobertura dos DTs 412, 475, 529 e 549 em bin/acervo, bin/_acervo/casa e bin/_acervo/listar."""

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN_ACERVO = RAIZ / "bin" / "acervo"


def _carregar_modulo(nome, caminho):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_dt529_acervo_listar_obra_sugere_biblioteca_obra():
    r = subprocess.run(
        ["bash", str(BIN_ACERVO), "listar", "obra", "--formato", "ttl"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert r.returncode == 2
    assert "acervo listar biblioteca obra --formato ttl" in r.stderr


def test_dt549_casa_le_documento_da_casa_nova_por_chave(tmp_path, monkeypatch, capsys):
    casa = _carregar_modulo("_acervo_casa_dt549", RAIZ / "bin" / "_acervo" / "casa")
    espelho = tmp_path / "platafirma-casa-espelho"
    obs_dir = espelho / "7-observacao" / "observacao"
    obs_dir.mkdir(parents=True)
    doc = obs_dir / "2026-11-09-inventario-dos-postgres.md"
    doc.write_text("# Inventário dos Postgres\n\nConteúdo de teste.\n", encoding="utf-8")

    monkeypatch.setenv("PF_CASA_ESPELHO", str(espelho))
    monkeypatch.setattr(casa, "_q", lambda sql, rotulo="consulta", falhar=True: None)

    rc = casa.ler("observacao", "2026-11-09-inventario-dos-postgres", True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo"] == "platafirma-casa-espelho"
    assert payload["path"] == "7-observacao/observacao/2026-11-09-inventario-dos-postgres.md"
    assert "Inventário dos Postgres" in payload["corpo"]


def test_dt549_casa_especie_nova_em_listar_aponta_repo_espelho(tmp_path, monkeypatch):
    casa = _carregar_modulo("_acervo_casa_dt549_listar", RAIZ / "bin" / "_acervo" / "casa")
    espelho = tmp_path / "platafirma-casa-espelho"
    (espelho / "7-observacao" / "observacao").mkdir(parents=True)
    (espelho / "7-observacao" / "observacao" / "2026-11-09-inventario-dos-postgres.md").write_text(
        "# Teste\n", encoding="utf-8"
    )
    monkeypatch.setenv("PF_CASA_ESPELHO", str(espelho))
    monkeypatch.setattr(casa, "_q", lambda sql, rotulo="consulta", falhar=True: None)

    with pytest.raises(SystemExit) as exc:
        casa._especie("observacao")
    assert exc.value.code == 2


def test_dt412_475_529_listar_obra_filtros_e_slug(monkeypatch, capsys):
    listar = _carregar_modulo("_acervo_listar_dts", RAIZ / "bin" / "_acervo" / "listar")
    sqls = []

    def _fake_psql_json(sql, rotulo="consulta"):
        sqls.append((rotulo, sql))
        if rotulo == "catalogo_obra":
            return [{"total": 10, "data": "2026-11-13"}]
        if rotulo == "conceito_existe":
            return []
        return [
            {
                "id": "1ac064f7-2c3d-403a-a31e-61ff88a704d5",
                "titulo": "OSINT Techniques",
                "objeto": "acervo/" + "a" * 64,
                "eixo": "obra",
                "subdominio": "seguranca",
                "conceito": "OSINT",
                "impressao_id": "11111111-1111-1111-1111-111111111111",
                "impressao_estado": "servindo",
                "autores": ["Michael Bazzell"],
                "formato": "application/pdf",
            }
        ]

    monkeypatch.setattr(listar, "_psql_json", _fake_psql_json)

    rc = listar.listar_obra(None, None, False, True, autor="bazzell", titulo="osint", formato="pdf")
    assert rc == 0
    itens = json.loads(capsys.readouterr().out)
    assert itens[0]["id"] == "1ac064f7-2c3d-403a-a31e-61ff88a704d5"
    assert itens[0]["autores"] == ["Michael Bazzell"]
    assert itens[0]["formato"] == "application/pdf"
    assert itens[0]["degrau"] == "vetorizada"
    sql_principal = [s for r, s in sqls if r == "listar obra"][0]
    assert "o2.emitido_por" in sql_principal
    assert "application/pdf" in sql_principal

    # DT 529: formato desconhecido recusa com exit 2
    with pytest.raises(SystemExit) as exc:
        listar.listar_obra(None, None, False, False, formato="ttl")
    assert exc.value.code == 2

    # DT 475: slug de conceito entra na query e ausencia explica que nao casou com rotulo nem slug
    sqls.clear()
    monkeypatch.setattr(
        listar,
        "_psql_json",
        lambda sql, rotulo="consulta": (
            [{"total": 10, "data": "2026-11-13"}]
            if rotulo == "catalogo_obra"
            else (sqls.append((rotulo, sql)) or [])
        ),
    )
    rc_vazio = listar.listar_obra("meu-conceito-slug", "conceito", False, False)
    assert rc_vazio == 0
    out_vazio = capsys.readouterr().out
    assert "não casou com rótulo nem com slug" in out_vazio
    sql_conceito = [s for r, s in sqls if r == "listar obra"][0]
    assert "lower(c.slug) = lower(" in sql_conceito
