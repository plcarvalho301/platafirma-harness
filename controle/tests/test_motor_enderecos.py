"""Os dois endereços do motor, lidos só do registro das instâncias (card #3843, R28 da spec motor)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

import motor_enderecos as me

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "registro" / "motor-instancias.json"
MOTOR = RAIZ / "bin" / "motor"

CHAVES_DA_BUSCA = ("endpoint", "facets", "ajustes_da_geracao")
# O registro dos lotes do motor (acervo.lote_motor) ainda mora no banco do acervo, que a role `busca` nao alcanca
# (migracao 120): na busca nova essas tres rotas voltam 502. Ficam no rag-extractor-api (8100) ate o registro mudar
# de banco; quando mudar, voltam para CHAVES_DA_BUSCA e este grupo some (#3844).
CHAVES_DOS_LOTES = ("indexacao", "troca", "trabalhos")


@pytest.fixture
def registro(tmp_path, monkeypatch):
    def faz(enderecos):
        arq = tmp_path / "motor-instancias.json"
        arq.write_text(json.dumps({"rag": {"estado": "ativa", "enderecos": enderecos}}), encoding="utf-8")
        monkeypatch.setenv("PF_MOTOR_REG", str(arq))
        return arq
    return faz


def test_os_dois_grupos_leem_cada_um_o_seu(registro):
    registro({"busca": "http://busca:1/", "api_acervo": "http://acervo:2"})
    assert me.busca() == "http://busca:1"
    assert me.api_acervo() == "http://acervo:2"


def test_mudar_um_endereco_nao_muda_o_outro(registro):
    registro({"busca": "http://nova:9", "api_acervo": "http://acervo:2"})
    assert me.api_acervo() == "http://acervo:2"
    registro({"busca": "http://busca:1", "api_acervo": "http://outra:8"})
    assert me.busca() == "http://busca:1"


@pytest.mark.parametrize("enderecos, chave", [({}, "busca"), ({"busca": "http://b:1"}, "api_acervo"),
                                              ({"busca": "  ", "api_acervo": "http://a:2"}, "busca")])
def test_endereco_nao_declarado_diz_a_chave_e_o_registro(registro, enderecos, chave):
    arq = registro(enderecos)
    with pytest.raises(me.EnderecoNaoDeclarado) as e:
        (me.busca if chave == "busca" else me.api_acervo)()
    assert f"enderecos.{chave}" in str(e.value) and str(arq) in str(e.value)


def test_registro_ilegivel_nao_vira_default_calado(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_MOTOR_REG", str(tmp_path / "nao-existe.json"))
    with pytest.raises(me.EnderecoNaoDeclarado):
        me.api_acervo()


def test_o_registro_servido_declara_a_busca_no_motor_busca_e_o_acervo_na_acervo_guarda(monkeypatch):
    """A virada da #3844 (tarefa 4): a busca é o host:porta de `endpoint` (motor-busca, 8101) e as seis URLs
    completas da instância começam pela base dela; a API do acervo é outro serviço (acervo-guarda, 8102), e os dois
    já não dividem a porta do rag-extractor-api (8100)."""
    monkeypatch.delenv("PF_MOTOR_REG", raising=False)
    rag = json.loads(REGISTRO.read_text(encoding="utf-8"))["rag"]
    busca, acervo = me.busca(), me.api_acervo()
    destino = urlparse(rag["endpoint"])
    assert (urlparse(busca).hostname, urlparse(busca).port) == (destino.hostname, destino.port) == ("127.0.0.1", 8101)
    assert (urlparse(acervo).hostname, urlparse(acervo).port) == ("127.0.0.1", 8102)
    for chave in CHAVES_DA_BUSCA:
        assert rag[chave].startswith(busca + "/"), chave
    for chave in CHAVES_DOS_LOTES:
        assert rag[chave].startswith("http://127.0.0.1:8100/motor/"), chave
    assert (rag["container"], rag["servico"], rag["stack"]) == ("motor-busca", "busca", "busca")


def test_motor_listar_mostra_os_dois_enderecos(monkeypatch):
    monkeypatch.delenv("PF_MOTOR_REG", raising=False)
    r = subprocess.run([sys.executable, str(MOTOR), "listar"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    linhas = {l.split()[0]: l.split()[1] for l in r.stdout.splitlines() if l.startswith("  ")}
    assert linhas == {"busca": me.busca(), "api_acervo": me.api_acervo()}
