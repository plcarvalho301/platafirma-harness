"""Testes de `busca ler`, `busca listar`, chave `registro/leitura.yaml` e `bin/pf` (story #4442, t9)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "lib"))


def _carregar_modulo(nome: str, caminho: Path) -> Any:
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_MOD_BUSCA = _carregar_modulo("bin_busca_t9", RAIZ / "bin" / "busca")
_MOD_PF = _carregar_modulo("bin_pf_t9", RAIZ / "bin" / "pf")


class _ClienteFalso:
    def __init__(self, resp_ler: dict[str, Any] | None = None, resp_listar: dict[str, Any] | None = None) -> None:
        self.resp_ler = resp_ler or {}
        self.resp_listar = resp_listar or {}
        self.chamadas: list[tuple[str, Any, Any]] = []

    def ler(self, contexto: Any, chaves: Any, **_kw: Any) -> dict[str, Any]:
        self.chamadas.append(("ler", chaves, contexto))
        return self.resp_ler

    def listar(self, contexto: Any, classe: Any, **_kw: Any) -> dict[str, Any]:
        self.chamadas.append(("listar", classe, contexto))
        return self.resp_listar


def test_registro_leitura_yaml_sobe_com_chave_desligada() -> None:
    cfg = _MOD_BUSCA.ler_config_leitura(raiz=RAIZ, env={})
    assert cfg["leitor_unico"] is False
    assert cfg["socket"] == "/run/platafirma/leitor/leitor.sock"


def test_busca_ler_pelo_leitor_unico_com_perda_e_aviso() -> None:
    cliente = _ClienteFalso(
        resp_ler={
            "ok": True,
            "exit_code": 0,
            "resultado": {
                "chave": "ato:ler",
                "classe": "ato",
                "ficha_da_classe": False,
                "versao": "abc1234",
                "parte": "linhas 1-2 de 10 (parcial)",
                "parcial": True,
                "com_perda": True,
                "avisos": [],
                "conteudo": "linha 1\nlinha 2\n",
                "proximo": "busca ler ato:ler --linhas 3-4",
            },
        }
    )
    out = io.StringIO()
    err = io.StringIO()
    rc = _MOD_BUSCA.main(
        ["ler", "ato:ler", "--linhas", "1-2"],
        saida=out,
        erro=err,
        cliente_leitor=cliente,
        env={"PF_SUJEITO": "engenharia", "PF_LEITOR_UNICO": "true"},
    )
    assert rc == 0
    texto = out.getvalue()
    assert texto.startswith("ato:ler · versão abc1234 · linhas 1-2 de 10 (parcial)\n")
    assert "proximo: busca ler ato:ler --linhas 3-4" in texto
    assert "com_perda=true" in texto
    assert len(cliente.chamadas) == 1
    assert cliente.chamadas[0][0] == "ler"


def test_busca_ler_caminho_solto_pelo_leitor_devolve_json_seis_campos() -> None:
    cliente = _ClienteFalso()
    out = io.StringIO()
    err = io.StringIO()
    rc = _MOD_BUSCA.main(
        ["ler", "/etc/passwd"],
        saida=out,
        erro=err,
        cliente_leitor=cliente,
        env={"PF_SUJEITO": "engenharia", "PF_LEITOR_UNICO": "true"},
    )
    assert rc == 2
    assert cliente.chamadas == []
    rec = json.loads(err.getvalue())
    assert rec["codigo"] == "caminho-solto-recusado"
    assert set(rec) >= {"codigo", "onde", "recebido", "regra", "cura", "proximo"}


def test_busca_listar_pelo_leitor_unico_json() -> None:
    cliente = _ClienteFalso(
        resp_listar={
            "ok": True,
            "exit_code": 0,
            "resultado": {
                "classe": "ato",
                "versao": "fornada-1",
                "universo_fechado": True,
                "total": 5,
                "itens": [
                    {"chave": "ato:ler"},
                    {"chave": "ato:listar"},
                    {"chave": "ato:escrever"},
                    {"chave": "ato:procurar"},
                    {"chave": "ato:remover"},
                ],
                "parcial": False,
                "avisos": [],
                "mudou": False,
                "proximo": None,
            },
        }
    )
    out = io.StringIO()
    err = io.StringIO()
    rc = _MOD_BUSCA.main(
        ["listar", "ato", "--json"],
        saida=out,
        erro=err,
        cliente_leitor=cliente,
        env={"PF_SUJEITO": "engenharia", "PF_LEITOR_UNICO": "true"},
    )
    assert rc == 0
    dados = json.loads(out.getvalue())
    assert dados["universo_fechado"] is True
    assert dados["total"] == 5
    assert len(dados["itens"]) == 5


def test_busca_ler_chave_desligada_roda_no_processo_local(monkeypatch: Any) -> None:
    chamado_local: list[list[str]] = []

    def _falso_ato_ler(args: list[str], **_kw: Any) -> dict[str, Any]:
        chamado_local.append(args)
        return {
            "cabecalho": "ato:ler · versão local1 · inteiro",
            "conteudo": "ok local\n",
            "parcial": False,
            "avisos": [],
            "json": False,
        }

    monkeypatch.setattr(_MOD_BUSCA, "ato_ler", _falso_ato_ler)
    out = io.StringIO()
    err = io.StringIO()
    rc = _MOD_BUSCA.main(
        ["ler", "ato:ler"],
        saida=out,
        erro=err,
        env={"PF_LEITOR_UNICO": "false"},
    )
    assert rc == 0
    assert chamado_local == [["ato:ler"]]
    assert "ok local" in out.getvalue()


def test_pf_percorre_proximo_args_em_laco_e_avisa_troca_de_versao() -> None:
    paginas = [
        (
            0,
            json.dumps({
                "versao": "v1",
                "conteudo": "parte-1\n",
                "parcial": True,
                "proximo_args": ["busca", "ler", "ato:ler", "--linhas", "2-2"],
            }),
            "",
        ),
        (
            0,
            json.dumps({
                "versao": "v2",
                "conteudo": "parte-2\n",
                "parcial": False,
                "proximo_args": [],
            }),
            "",
        ),
    ]
    chamadas: list[list[str]] = []

    def _exec(cmd: Any) -> tuple[int, str, str]:
        chamadas.append(list(cmd))
        return paginas[len(chamadas) - 1]

    out = io.StringIO()
    err = io.StringIO()
    rc = _MOD_PF.executar_com_paginacao(["busca", "ler", "ato:ler"], executor=_exec, saida=out, erro=err)
    assert rc == 0
    assert out.getvalue() == "parte-1\nparte-2\n"
    assert "versão mudou" in err.getvalue()
    assert "v1 -> v2" in err.getvalue()
    assert len(chamadas) == 2


def test_pf_nao_entra_em_laco_com_recorte_explicito() -> None:
    chamadas: list[list[str]] = []

    def _exec(cmd: Any) -> tuple[int, str, str]:
        chamadas.append(list(cmd))
        return 0, "linha 1\n", ""

    out = io.StringIO()
    err = io.StringIO()
    rc = _MOD_PF.executar_com_paginacao(
        ["busca", "ler", "ato:ler", "--linhas", "1-1"],
        executor=_exec,
        saida=out,
        erro=err,
    )
    assert rc == 0
    assert out.getvalue() == "linha 1\n"
    assert len(chamadas) == 1
