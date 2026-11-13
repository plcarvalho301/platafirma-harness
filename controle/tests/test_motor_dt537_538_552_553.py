"""Regressões do balde #2856: contrato da busca e rótulos do tesauro."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bin" / "_motor"))
from retorno import completar, resolver_conceitos
from test_motor_buscar_consulta import api, _API

SID = "e31f9de8-9215-523b-89af-7a2a5d0dd87b"
CATALOGO = [
    {"slug": "ranqueamento-multiestagio", "rotulo": "Ranqueamento multiestágio",
     "outros_rotulos": ["reranking", "comum"]},
    {"slug": "outro", "rotulo": "Outro", "outros_rotulos": "comum / variante"},
]


def test_slug_rotulo_alias_normalizacao_e_duplicata():
    r, avisos = resolver_conceitos(
        ["ranqueamento-multiestagio", "RANQUEAMENTO MULTIESTÁGIO", "reranking", "variante"], CATALOGO)
    assert r == ["ranqueamento-multiestagio", "outro"]
    assert not avisos


def test_desconhecido_e_ambiguo_nao_escolhem_em_silencio():
    r, avisos = resolver_conceitos(["comum", "nao existe"], CATALOGO)
    assert r == []
    assert "ambiguo" in avisos[0] and "outro" in avisos[0]
    assert "nao reconhecido" in avisos[1]


def test_retorno_anuncia_texto_e_leitura_sem_mudar_conteudo():
    fonte = {"secao_id": SID, "texto": None, "sim": .7}
    r = completar({"fontes": [fonte], "cobertura": "boa"}, "biblioteca", "nenhum")
    assert r["texto_solicitado"] == "nenhum" and "--texto trecho" in r["aviso_texto"]
    assert fonte["ler"] == f"acervo ler biblioteca secao {SID}"
    assert fonte["texto"] is None and fonte["sim"] == .7 and r["cobertura"] == "boa"
    assert "aviso_texto" not in completar({"fontes": []}, "casa", "secao")


def test_verbo_mantem_default_e_avisa(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "O que é recuperação?")
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["texto"] == "nenhum"
    assert "texto nao solicitado" in r.stderr
    assert "--texto secao" in json.loads(r.stdout)["aviso_texto"]


def test_verbo_resolve_catalogo_antes_do_post_e_eco_aviso(api, tmp_path, monkeypatch):
    roda, pedidos, _, _ = api
    registro = tmp_path / "motor-instancias.json"
    reg = json.loads(registro.read_text())
    reg["rag"]["enderecos"] = {"api_acervo": reg["rag"]["endpoint"].removesuffix("/search")}
    registro.write_text(json.dumps(reg))

    def get(self):
        dado = json.dumps({"itens": CATALOGO, "proximo": None}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(dado)
    monkeypatch.setattr(_API, "do_GET", get, raising=False)
    r = roda("buscar", "biblioteca", "O que é recuperação?",
             "--conceito", "ranqueamento multiestágio", "--conceito", "inexistente")
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["conceitos"] == ["ranqueamento-multiestagio"]
    assert "filtro" not in pedidos[-1]
    assert "inexistente" in json.loads(r.stdout)["avisos_conceitos"][0]


@pytest.mark.parametrize("particao", ["registro", "log"])
def test_verbo_usa_nome_canonico_da_particao(api, particao):
    roda, pedidos, _, _ = api
    r = roda("buscar", particao, "O que é recuperação?")
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["particao"] == "log"
