"""Testes dos DTs 885, 889 e 896 do verbo `descansar`.

- DT 885: `descansar publicar` devolve todos os campos obrigatórios que faltam e o esquema JSON.
- DT 889: recusa de etiqueta/destinatário sem ficha (local ou HTTP 422 `EtiquetaSemFicha`) devolve
  a forma aceita `<classe>:<slug>` com exemplo para chaves sem prefixo.
- DT 896: `descansar fita` encerra a sessão no mesmo ato por padrão; `descansar encerrar` fecha
  direto; `descansar fita --sem-encerrar` emite só o relatório sem matar a sessão.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.error
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
from descanso import publicar as pub  # noqa: E402

loader = SourceFileLoader("descansar_dts_bin", str(REPO_ROOT / "bin" / "descansar"))
spec = importlib.util.spec_from_loader("descansar_dts_bin", loader)
assert spec and spec.loader
descansar = importlib.util.module_from_spec(spec)
loader.exec_module(descansar)


class _RedisFalso:
    def __init__(self):
        self.apagadas = []
        self.sets = {}

    def get(self, chave):
        return None

    def set(self, chave, valor):
        self.sets[chave] = valor

    def delete(self, *chaves):
        self.apagadas.extend(chaves)
        return len(chaves)


# ---------------------------------------------------------------- DT 885: campos faltantes e esquema JSON
def test_dt885_publicar_lista_todos_os_campos_faltantes_e_esquema():
    with pytest.raises(pub.Recusada) as exc:
        pub.Mensagem.de_dict({})
    msg = str(exc.value)
    for campo in ("enunciado", "quem", "destinatario", "tipo-de-mensagem"):
        assert campo in msg
    assert "JSON esperado:" in msg


def test_dt885_publicar_vazio_ou_json_invalido_devolve_esquema(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{nao-json"))
    rc = descansar.ato_publicar(type("A", (), {"como_json": False})())
    assert rc == 2
    err = capsys.readouterr().err
    assert "JSON esperado:" in err and "enunciado" in err and "destinatario" in err


# ---------------------------------------------------------------- DT 889: forma aceita na recusa de ficha
def test_dt889_conferir_fichas_etiqueta_sem_prefixo_devolve_forma_aceita(tmp_path):
    fix = tmp_path / "fichas.json"
    fix.write_text(json.dumps(["persona:ia", "capacidade:busca"]), encoding="utf-8")
    msg = pub.Mensagem.de_dict({
        "enunciado": "teste",
        "quem": "ia",
        "destinatario": "persona:ia",
        "tipo-de-mensagem": "afirmacao",
        "etiqueta": ["busca"],
    })
    with pytest.raises(pub.Recusada) as exc:
        msg.conferir_fichas(pub.FicharioFixtura(fix))
    texto = str(exc.value)
    assert "<classe>:<slug>" in texto
    assert "capacidade:busca" in texto


def test_dt889_http_422_etiqueta_sem_ficha_devolve_forma_aceita(monkeypatch):
    corpo = json.dumps({"tipo": "EtiquetaSemFicha", "detalhe": "etiqueta sem ficha: busca"}).encode("utf-8")

    def _fake_urlopen(req, timeout=15.0):
        raise urllib.error.HTTPError(req.full_url, 422, "Unprocessable", {}, io.BytesIO(corpo))

    monkeypatch.setattr(pub.urllib.request, "urlopen", _fake_urlopen)
    msg = pub.Mensagem.de_dict({
        "enunciado": "teste",
        "quem": "ia",
        "destinatario": "persona:ia",
        "tipo-de-mensagem": "afirmacao",
        "etiqueta": ["busca"],
    })
    grav = pub.GravadorEventos(url="http://127.0.0.1:8111", token="tok")
    with pytest.raises(pub.Recusada) as exc:
        grav.gravar(msg)
    texto = str(exc.value)
    assert "EtiquetaSemFicha" in texto
    assert "<classe>:<slug>" in texto
    assert "capacidade:busca" in texto


# ---------------------------------------------------------------- DT 896: descansar fita e encerrar fecham a sessao
def _prepara_fita(monkeypatch, tmp_path):
    rc = _RedisFalso()
    monkeypatch.setenv("PF_CADEIRA", "ia")
    monkeypatch.setenv("PF_SESSAO", "2be6bc3b-36fd-43e2-a189-3e01b0ec5e36")
    monkeypatch.setenv("OPS_LOG_DIR", str(tmp_path / "ops"))
    monkeypatch.setenv("PF_DERRAME", str(tmp_path / "retornos"))
    monkeypatch.setattr(descansar, "conn", lambda: rc)
    monkeypatch.setattr(descansar, "estado_memoria", lambda curto: (["  mesa vazia"], []))
    monkeypatch.setattr(descansar, "puxado_de_fora", lambda *a, **kw: ["  nada"])
    monkeypatch.setattr(descansar, "_marca_encerrada_duravel", lambda sid: None)
    return rc


def test_dt896_descansar_fita_encerra_sessao_no_mesmo_ato(monkeypatch, tmp_path, capsys):
    rc = _prepara_fita(monkeypatch, tmp_path)
    monkeypatch.setattr(descansar.sys, "argv", ["descansar", "fita"])
    assert descansar.main() == 0
    out = capsys.readouterr().out
    assert "== descanso de ia ==" in out
    assert "== contrato de morte da sessao" in out
    assert "sessao:2be6bc3b-36fd-43e2-a189-3e01b0ec5e36" in rc.apagadas
    assert "mem:ia" in rc.sets


def test_dt896_descansar_encerrar_fecha_direto(monkeypatch, tmp_path, capsys):
    rc = _prepara_fita(monkeypatch, tmp_path)
    monkeypatch.setattr(descansar.sys, "argv", ["descansar", "encerrar", "--parada", "interrompida"])
    assert descansar.main() == 0
    out = capsys.readouterr().out
    assert "== contrato de morte da sessao" in out
    assert "parada=interrompida" in out
    assert "sessao:2be6bc3b-36fd-43e2-a189-3e01b0ec5e36" in rc.apagadas
    assert "mem:ia" in rc.sets


def test_dt896_descansar_fita_sem_encerrar_deixa_sessao_viva(monkeypatch, tmp_path, capsys):
    rc = _prepara_fita(monkeypatch, tmp_path)
    monkeypatch.setattr(descansar.sys, "argv", ["descansar", "fita", "--sem-encerrar"])
    assert descansar.main() == 0
    out = capsys.readouterr().out
    assert "== descanso de ia ==" in out
    assert "== contrato de morte da sessao" not in out
    assert rc.apagadas == []
    assert rc.sets == {}


# ---------------------------------------------------------------- #4380: fallback do token da instancia
def test_gravador_do_ambiente_le_token_da_instancia_como_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("PF_MENSAGEM_ARQUIVO", raising=False)
    monkeypatch.delenv("EVENTOS_NEGOCIO_TOKEN", raising=False)
    monkeypatch.delenv("EVENTOS_API_URL", raising=False)
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))
    seg = tmp_path / "segredos" / "eventos" / "EVENTOS_NEGOCIO_TOKEN"
    seg.parent.mkdir(parents=True)
    seg.write_text("tok-instancia\n", encoding="utf-8")

    grav = pub.gravador_do_ambiente()
    assert isinstance(grav, pub.GravadorEventos)
    assert grav.token == "tok-instancia"
    assert grav.url == pub.EVENTOS_API_PADRAO


def test_gravador_do_ambiente_prefere_env_sobre_arquivo_da_instancia(monkeypatch, tmp_path):
    monkeypatch.delenv("PF_MENSAGEM_ARQUIVO", raising=False)
    monkeypatch.setenv("EVENTOS_NEGOCIO_TOKEN", "tok-env")
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))
    seg = tmp_path / "segredos" / "eventos" / "EVENTOS_NEGOCIO_TOKEN"
    seg.parent.mkdir(parents=True)
    seg.write_text("tok-instancia\n", encoding="utf-8")

    grav = pub.gravador_do_ambiente()
    assert isinstance(grav, pub.GravadorEventos)
    assert grav.token == "tok-env"


def test_gravador_do_ambiente_sem_env_nem_arquivo_recusa(monkeypatch, tmp_path):
    monkeypatch.delenv("PF_MENSAGEM_ARQUIVO", raising=False)
    monkeypatch.delenv("EVENTOS_NEGOCIO_TOKEN", raising=False)
    monkeypatch.delenv("EVENTOS_API_URL", raising=False)
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))

    with pytest.raises(pub.SemDestino):
        pub.gravador_do_ambiente()
