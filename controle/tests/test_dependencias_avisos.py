"""`release conferir dependencias --avisos` (feature #3388): o rol cruzado com o OSV.

Hermético: o OSV é uma função falsa injetada (a mesma assinatura de `_osv_http`: método,
caminho, corpo -> JSON). Prova: pacote e versão exatos do lock vão ao querybatch; aviso aberto
vira divergente com id, gravidade, resumo e a versão corrigida; aviso retirado não conta; resposta
paginada é seguida; pacote sem versão fixada não é consultado; id fora do formato não vira URL;
OSV fora do ar sai 5 (nunca "sem aviso"); sem --avisos o OSV não é chamado. Não prova: o OSV de
verdade (a primeira rodada real é a prova de formato).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _dependencias():
    pasta = REPO_ROOT / "bin" / "_release" / "conferir"
    spec = importlib.util.spec_from_file_location("dependencias_avisos_teste",
                                                  pasta / "dependencias.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(pasta))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(pasta))
    return mod


GHSA = {
    "id": "GHSA-aaaa-bbbb-cccc", "summary": "Poluicao de prototipo no pacote",
    "database_specific": {"severity": "HIGH"},
    "affected": [
        {"package": {"name": "vulneravel", "ecosystem": "npm"},
         "ranges": [{"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "2.0.1"}]}]},
        {"package": {"name": "outro", "ecosystem": "npm"},
         "ranges": [{"type": "SEMVER", "events": [{"fixed": "9.9.9"}]}]},
    ],
}


class OsvFalso:
    def __init__(self, vulns=None, detalhes=None, paginas=None, erro=None):
        self.vulns = vulns or {}          # (nome, versao) -> [ids]
        self.detalhes = detalhes or {}    # id -> JSON do OSV
        self.paginas = paginas or {}      # token -> {"vulns": [...]} da pagina seguinte
        self.erro = erro
        self.chamadas = []

    def __call__(self, metodo, caminho, corpo=None):
        self.chamadas.append((metodo, caminho, corpo))
        if self.erro:
            raise OSError(self.erro)
        if caminho == "/v1/querybatch":
            saida = []
            for q in corpo["queries"]:
                ids = self.vulns.get((q["package"]["name"], q["version"]), [])
                item = {"vulns": [{"id": i} for i in ids]} if ids else {}
                if (q["package"]["name"], q["version"]) in self.paginas.get("_primeira", {}):
                    item["next_page_token"] = self.paginas["_primeira"][(q["package"]["name"], q["version"])]
                saida.append(item)
            return {"results": saida}
        if caminho == "/v1/query":
            return self.paginas[corpo["page_token"]]
        if caminho.startswith("/v1/vulns/"):
            return self.detalhes[caminho.rsplit("/", 1)[1]]
        raise AssertionError(f"chamada inesperada: {metodo} {caminho}")


def _linha(dep, nome, versao, eco="npm", stack="s"):
    return dep._linha(stack, eco, nome, versao, True, "registry.npmjs.org", "abc")


def test_aviso_aberto_traz_id_gravidade_resumo_e_versao_corrigida():
    dep = _dependencias()
    osv = OsvFalso({("vulneravel", "2.0.0"): ["GHSA-aaaa-bbbb-cccc"]},
                   {"GHSA-aaaa-bbbb-cccc": GHSA})
    achados = dep.consultar_avisos([_linha(dep, "vulneravel", "2.0.0"),
                                    _linha(dep, "limpo", "1.0.0")], osv)
    assert list(achados) == [("npm", "vulneravel", "2.0.0")]
    a = achados[("npm", "vulneravel", "2.0.0")][0]
    assert a["id"] == "GHSA-aaaa-bbbb-cccc" and a["gravidade"] == "HIGH"
    assert a["corrigido_em"] == "2.0.1"      # o 9.9.9 e de outro pacote do mesmo aviso
    consulta = osv.chamadas[0][2]["queries"]
    assert {"package": {"name": "vulneravel", "ecosystem": "npm"}, "version": "2.0.0"} in consulta


def test_pypi_vai_com_o_nome_do_ecossistema_do_osv_e_nome_normalizado():
    dep = _dependencias()
    detalhe = {"id": "PYSEC-1", "summary": "x", "affected": [
        {"package": {"name": "Foo_Bar", "ecosystem": "PyPI"},
         "ranges": [{"type": "ECOSYSTEM", "events": [{"fixed": "1.2"}]}]}]}
    osv = OsvFalso({("foo-bar", "1.0"): ["PYSEC-1"]}, {"PYSEC-1": detalhe})
    achados = dep.consultar_avisos([_linha(dep, "foo-bar", "1.0", eco="pypi")], osv)
    assert osv.chamadas[0][2]["queries"][0]["package"]["ecosystem"] == "PyPI"
    assert achados[("pypi", "foo-bar", "1.0")][0]["corrigido_em"] == "1.2"


def test_aviso_retirado_nao_conta():
    dep = _dependencias()
    retirado = {**GHSA, "withdrawn": "2026-01-01T00:00:00Z"}
    osv = OsvFalso({("vulneravel", "2.0.0"): ["GHSA-aaaa-bbbb-cccc"]},
                   {"GHSA-aaaa-bbbb-cccc": retirado})
    assert dep.consultar_avisos([_linha(dep, "vulneravel", "2.0.0")], osv) == {}


def test_resposta_paginada_e_seguida():
    dep = _dependencias()
    outro = {**GHSA, "id": "GHSA-dddd-eeee-ffff"}
    osv = OsvFalso({("vulneravel", "2.0.0"): ["GHSA-aaaa-bbbb-cccc"]},
                   {"GHSA-aaaa-bbbb-cccc": GHSA, "GHSA-dddd-eeee-ffff": outro},
                   {"_primeira": {("vulneravel", "2.0.0"): "tok1"},
                    "tok1": {"vulns": [{"id": "GHSA-dddd-eeee-ffff"}]}})
    achados = dep.consultar_avisos([_linha(dep, "vulneravel", "2.0.0")], osv)
    ids = [a["id"] for a in achados[("npm", "vulneravel", "2.0.0")]]
    assert ids == ["GHSA-aaaa-bbbb-cccc", "GHSA-dddd-eeee-ffff"]


def test_pacote_sem_versao_fixada_nao_e_consultado():
    dep = _dependencias()
    osv = OsvFalso()
    assert dep.consultar_avisos([_linha(dep, "solto", "?", eco="pypi")], osv) == {}
    assert osv.chamadas == []


def test_id_fora_do_formato_nao_vira_url():
    dep = _dependencias()
    osv = OsvFalso({("vulneravel", "2.0.0"): ["../../admin"]}, {})
    assert dep.consultar_avisos([_linha(dep, "vulneravel", "2.0.0")], osv) == {}
    assert not any(c[0] == "GET" for c in osv.chamadas)


def test_querybatch_com_numero_errado_de_resultados_levanta():
    dep = _dependencias()

    def torto(metodo, caminho, corpo=None):
        return {"results": []}
    with pytest.raises(OSError, match="0 resultados para 1 consultas"):
        dep.consultar_avisos([_linha(dep, "a", "1.0.0")], torto)


# ---- a classe inteira, com registro e arvore servida de mentira ------------------------------

UV_LOCK = '''version = 1
[[package]]
name = "vulneravel"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://x/p.tar.gz", hash = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
[[package]]
name = "limpo"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://x/q.tar.gz", hash = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" }
'''


def _servida(tmp_path):
    registro = tmp_path / "venvs.json"
    registro.write_text(json.dumps({"stacks": {"s": {"familia": "f", "lock": "uv.lock"}}}))
    atual = tmp_path / "prod" / "f" / "current"
    atual.mkdir(parents=True)
    (atual / "uv.lock").write_text(UV_LOCK)
    return str(registro), str(tmp_path / "prod")


DET_PY = {"id": "PYSEC-9", "summary": "Execucao remota", "database_specific": {"severity": "CRITICAL"},
          "affected": [{"package": {"name": "vulneravel", "ecosystem": "PyPI"},
                        "ranges": [{"type": "ECOSYSTEM", "events": [{"fixed": "2.0.1"}]}]}]}


def test_conferir_com_aviso_sai_1_e_diz_o_que_e_e_onde_corrige(tmp_path, capsys):
    dep = _dependencias()
    registro, prod = _servida(tmp_path)
    osv = OsvFalso({("vulneravel", "2.0.0"): ["PYSEC-9"]}, {"PYSEC-9": DET_PY})
    rc = dep.conferir("s", True, "abc1234", registro, prod, avisos=True, osv=osv)
    assert rc == 1
    saida = json.loads(capsys.readouterr().out)
    por = {i["nome"]: i for i in saida["itens"]}
    ruim = por["s · pypi · vulneravel 2.0.0"]
    assert ruim["estado"] == "divergente"
    assert "PYSEC-9 (CRITICAL)" in ruim["motivo"] and "corrigido em 2.0.1" in ruim["motivo"]
    assert por["s · pypi · limpo 1.0.0"]["estado"] == "conforme"
    pac = {p["pacote"]: p for p in saida["pacotes"]}
    assert pac["vulneravel"]["avisos"][0]["id"] == "PYSEC-9" and pac["limpo"]["avisos"] == []


def test_conferir_sem_aviso_sai_0(tmp_path, capsys):
    dep = _dependencias()
    registro, prod = _servida(tmp_path)
    rc = dep.conferir("s", True, "abc1234", registro, prod, avisos=True, osv=OsvFalso())
    assert rc == 0
    capsys.readouterr()


def test_osv_fora_do_ar_e_indeterminavel_nunca_sem_aviso(tmp_path, capsys):
    dep = _dependencias()
    registro, prod = _servida(tmp_path)
    rc = dep.conferir("s", False, "abc1234", registro, prod, avisos=True,
                      osv=OsvFalso(erro="sem rota"))
    assert rc == 5
    assert "nao consegui olhar" in capsys.readouterr().err


def test_sem_avisos_o_osv_nao_e_chamado(tmp_path, capsys):
    dep = _dependencias()
    registro, prod = _servida(tmp_path)

    def proibido(*_a, **_k):
        raise AssertionError("o OSV nao pode ser chamado sem --avisos")
    rc = dep.conferir("s", True, "abc1234", registro, prod, osv=proibido)
    assert rc == 0
    capsys.readouterr()
