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

CHAVES_DA_BUSCA = ("endpoint", "facets", "indexacao", "troca", "ajustes_da_geracao", "trabalhos")


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


def test_o_registro_servido_declara_os_dois_enderecos_no_servido_de_hoje(monkeypatch):
    """A trava da story: nenhum endereço muda de destino. Os dois são o host:porta de `endpoint`, e as seis URLs
    completas da instância começam pela base da busca, para a virada trocar uma fonte só."""
    monkeypatch.delenv("PF_MOTOR_REG", raising=False)
    rag = json.loads(REGISTRO.read_text(encoding="utf-8"))["rag"]
    busca, acervo = me.busca(), me.api_acervo()
    destino = urlparse(rag["endpoint"])
    for base in (busca, acervo):
        assert (urlparse(base).hostname, urlparse(base).port) == (destino.hostname, destino.port)
    for chave in CHAVES_DA_BUSCA:
        assert rag[chave].startswith(busca + "/"), chave


def test_motor_listar_mostra_os_dois_enderecos(monkeypatch):
    monkeypatch.delenv("PF_MOTOR_REG", raising=False)
    r = subprocess.run([sys.executable, str(MOTOR), "listar"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    linhas = {l.split()[0]: l.split()[1] for l in r.stdout.splitlines() if l.startswith("  ")}
    assert linhas == {"busca": me.busca(), "api_acervo": me.api_acervo()}
