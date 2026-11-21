# componente: componente:verbo-metrica
"""Testes de separacao transporte/verbo e pareamento de tateio em bin/metrica (card #4369)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import types
from datetime import date
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
METRICA_BIN = HARNESS / "bin" / "metrica"


def _carrega_metrica(monkeypatch):
    lib_dir = str(HARNESS / "lib")
    bin_dir = str(HARNESS / "bin")
    if lib_dir not in sys.path:
        monkeypatch.syspath_prepend(lib_dir)
    if bin_dir not in sys.path:
        monkeypatch.syspath_prepend(bin_dir)

    # Stubs minimos dos modulos auxiliares do harness principal.
    if "oplog_extracao" not in sys.modules:
        ext = types.ModuleType("oplog_extracao")
        ext.hoje_local = lambda: date.today()
        ext.Api = object
        monkeypatch.setitem(sys.modules, "oplog_extracao", ext)

    pkg = types.ModuleType("_metrica")
    pkg.__path__ = [str(HARNESS / "bin" / "_metrica")]
    abertura = types.ModuleType("_metrica.abertura")
    abertura.main = lambda *a, **kw: 0
    particao = types.ModuleType("_metrica.particao")
    particao.BRUTO = "bruto"
    particao.contas_do_bruto = lambda giros: {}
    investigar = types.ModuleType("_metrica.investigar")
    investigar.dica_de_argumentos = lambda dia: ""
    tokens_main = types.ModuleType("_metrica.tokens_main")
    tokens_main.main = lambda *a, **kw: 0

    for nome, mod in (
        ("_metrica", pkg),
        ("_metrica.abertura", abertura),
        ("_metrica.particao", particao),
        ("_metrica.investigar", investigar),
        ("_metrica.tokens_main", tokens_main),
    ):
        monkeypatch.setitem(sys.modules, nome, mod)

    loader = importlib.machinery.SourceFileLoader("metrica_mod_4369", str(METRICA_BIN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _escreve_log(tmp_path: Path, dia: str, eventos: list[dict]) -> Path:
    arq = tmp_path / f"ops-{dia}.jsonl"
    arq.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in eventos) + "\n", encoding="utf-8")
    return arq


def test_verbos_conta_transporte_separado_do_verbo(tmp_path, monkeypatch):
    metrica = _carrega_metrica(monkeypatch)
    dia = date.today().isoformat()
    eventos = [
        {"ts": f"{dia}T10:00:01Z", "cadeira": "engenharia", "ordem_id": "ord-1", "sessao_id": "s1",
         "tool": "repo", "evento": "verbo", "via": "malote", "ato": "estado",
         "exit_code": 0, "lote_id": "L1", "lote_n": 0, "bytes_servidos": 100},
        {"ts": f"{dia}T10:00:02Z", "cadeira": "engenharia", "ordem_id": "ord-1", "sessao_id": "s1",
         "tool": "tarefas", "evento": "verbo", "via": "malote", "ato": "ler",
         "exit_code": 0, "lote_id": "L1", "lote_n": 1, "bytes_servidos": 120},
        {"ts": f"{dia}T10:00:03Z", "cadeira": "engenharia", "ordem_id": "ord-1", "sessao_id": "s1",
         "tool": "fila", "evento": "verbo", "via": "malote", "ato": "status",
         "exit_code": 0, "lote_id": "L1", "lote_n": 2, "bytes_servidos": 80},
        {"ts": f"{dia}T10:00:04Z", "cadeira": "engenharia", "ordem_id": "ord-1", "sessao_id": "s1",
         "tool": "malote", "evento": "lote", "lote_id": "L1", "lote_n": 3,
         "dur_ms": 42, "bytes_servidos": 300, "recusas": 0, "exit_code": 0},
    ]
    _escreve_log(tmp_path, dia, eventos)

    fonte = metrica.FonteJsonl(str(tmp_path))
    giros, _par, _cad = metrica.classifica(fonte, dia)
    res = metrica.verbos(giros)

    assert "malote" not in res["por_verbo"]
    assert res["total"]["giros"] == 3
    assert res["transporte"]["malote"]["giros"] == 1
    assert res["transporte"]["malote"]["itens"] == 3
    assert res["transporte"]["malote"]["lotes"] == 1
    assert res["transporte"]["malote"]["bytes_servidos"] == 300


def test_main_metrica_verbos_dias_1(tmp_path, monkeypatch, capsys):
    metrica = _carrega_metrica(monkeypatch)
    dia = date.today().isoformat()
    eventos = [
        {"ts": f"{dia}T11:00:01Z", "cadeira": "engenharia", "ordem_id": "ord-2", "sessao_id": "s2",
         "tool": "repo", "evento": "verbo", "via": "malote", "ato": "estado",
         "exit_code": 0, "lote_id": "L2", "lote_n": 0, "bytes_servidos": 50},
        {"ts": f"{dia}T11:00:02Z", "cadeira": "engenharia", "ordem_id": "ord-2", "sessao_id": "s2",
         "tool": "tarefas", "evento": "verbo", "via": "malote", "ato": "ler",
         "exit_code": 0, "lote_id": "L2", "lote_n": 1, "bytes_servidos": 60},
        {"ts": f"{dia}T11:00:03Z", "cadeira": "engenharia", "ordem_id": "ord-2", "sessao_id": "s2",
         "tool": "fila", "evento": "verbo", "via": "malote", "ato": "status",
         "exit_code": 0, "lote_id": "L2", "lote_n": 2, "bytes_servidos": 40},
        {"ts": f"{dia}T11:00:04Z", "cadeira": "engenharia", "ordem_id": "ord-2", "sessao_id": "s2",
         "tool": "malote", "evento": "lote", "lote_id": "L2", "lote_n": 3,
         "dur_ms": 20, "bytes_servidos": 150, "recusas": 0, "exit_code": 0},
    ]
    _escreve_log(tmp_path, dia, eventos)

    monkeypatch.setattr(metrica, "LOG_OPS", str(tmp_path))
    monkeypatch.setattr(metrica, "FonteJsonl", lambda diretorio=str(tmp_path): metrica.FonteJsonl(str(tmp_path)) if diretorio != str(tmp_path) else _fonte_real(metrica, tmp_path))
    rc = metrica.main(["metrica", "verbos", dia, "--fonte", "bruto"])
    assert rc == 0
    dados = json.loads(capsys.readouterr().out)
    assert dados["transporte"]["malote"]["giros"] == 1
    assert dados["total"]["giros"] == 3


def _fonte_real(metrica, tmp_path):
    class _F:
        def __init__(self):
            self.diretorio = str(tmp_path)
            self.ilegiveis = 0

        def caminho(self, dia):
            return str(metrica.oplog.caminho_do_dia(dia, self.diretorio))

        def linhas(self, dia):
            leitura = metrica.oplog.ler(dia, diretorio_=self.diretorio)
            if leitura.dias[dia].estado == "ausente":
                raise metrica.FonteAusente(self.caminho(dia), dia)
            yield from leitura
            self.ilegiveis += leitura.ilegiveis

    return _F()


def test_tateio_pareia_recusa_do_malote_pelo_verbo_pretendido(tmp_path, monkeypatch):
    metrica = _carrega_metrica(monkeypatch)
    dia = date.today().isoformat()
    eventos = [
        {"ts": f"{dia}T12:00:01Z", "cadeira": "engenharia", "ordem_id": "ord-3", "sessao_id": "s3",
         "tool": "malote", "evento": "sem_verbo", "verbo": "tarefas",
         "motivo": "item deve ser objeto", "exit_code": 2, "lote_id": "L3", "lote_n": 0},
        {"ts": f"{dia}T12:00:05Z", "cadeira": "engenharia", "ordem_id": "ord-3", "sessao_id": "s3",
         "tool": "tarefas", "evento": "verbo", "via": "malote", "ato": "ler",
         "exit_code": 0, "lote_id": "L4", "lote_n": 0},
    ]
    _escreve_log(tmp_path, dia, eventos)

    fonte = metrica.FonteJsonl(str(tmp_path))
    giros, par, _cad = metrica.classifica(fonte, dia)
    tat = metrica.tateio(giros, par)

    gastos = tat["gramatica"]["gasto_ate_acerto"]
    assert len(gastos) == 1
    assert gastos[0]["tool"] == "tarefas"
    assert gastos[0]["giros_de_gramatica"] == 1
    assert gastos[0]["acertou_em"] == "ler"
