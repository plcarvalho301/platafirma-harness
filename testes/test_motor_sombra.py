"""Testes unitários de bin/_motor/sombra.py (DT-774 e DT-776)."""
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_sombra(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "SOMBRA_ARGS",
        json.dumps({"id": "t", "saida": str(tmp_path), "particoes": ["biblioteca"], "modelos": []}),
    )
    for mod in ("numpy", "torch", "torch.nn", "torch.nn.functional", "psycopg", "pgvector", "pgvector.psycopg"):
        if mod not in sys.modules:
            m = ModuleType(mod)
            if mod == "numpy":
                m.float16 = float
                m.stack = lambda xs: list(xs)
                m.asarray = lambda x, dtype=None: list(x)
            elif mod == "torch":
                m.cuda = SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)
            elif mod == "pgvector.psycopg":
                m.register_vector = lambda c: None
            elif mod == "psycopg":
                class _Insuff(Exception):
                    pass
                m.errors = SimpleNamespace(InsufficientPrivilege=_Insuff)
            monkeypatch.setitem(sys.modules, mod, m)
    caminho = Path(__file__).resolve().parents[1] / "bin" / "_motor" / "sombra.py"
    spec = importlib.util.spec_from_file_location("sombra_dt_teste", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


def test_carrega_corpus_le_motor_trecho_quando_morada_e_motor(tmp_path, monkeypatch):
    """DT-776: com trecho_morada='motor', texto vem de motor.trecho e moldura de acervo.secao."""
    sombra = _load_sombra(tmp_path, monkeypatch)
    queries_cm, queries_conn = [], []

    class _CM:
        def execute(self, sql, params=()):
            queries_cm.append(sql)
            if "FROM motor.geracao" in sql:
                return _Cursor([("g4-id", "motor")])
            if "FROM motor.vetor" in sql:
                return _Cursor([("t1", [1.0, 0.0])])
            if "FROM motor.trecho" in sql:
                return _Cursor([("t1", "conteudo g4", "s1")])
            return _Cursor([])

    class _Conn:
        def execute(self, sql, params=()):
            queries_conn.append(sql)
            if "FROM acervo.secao" in sql:
                return _Cursor([("s1", "o1", "sec-1", "livro.md")])
            raise AssertionError(f"nao devia consultar acervo.trecho: {sql}")

    cm, conn = _CM(), _Conn()
    ger_id, morada = sombra.geracao_servindo(cm, "biblioteca")
    assert (ger_id, morada) == ("g4-id", "motor")
    corpus = sombra.carrega_corpus(conn, cm, "biblioteca", ["ind-1"], sel={"t1"},
                                   geracao_id=ger_id, trecho_morada=morada)
    assert corpus["ids"] == ["t1"]
    assert corpus["meta"]["t1"] == {
        "texto": "conteudo g4", "obra": "o1", "ancora": "sec-1", "arquivo": "livro.md",
    }
    assert any("FROM motor.trecho" in q for q in queries_cm)
    assert all("acervo.trecho" not in q for q in queries_conn)


def test_sombra_tem_fallback_de_bateria_recuperacao_para_evento_recuperacao(tmp_path):
    """DT-774: quando acervo.bateria_recuperacao falha por permissao, cai em acervo.evento_recuperacao."""
    src = (Path(__file__).resolve().parents[1] / "bin" / "_motor" / "sombra.py").read_text("utf-8")
    assert "except psycopg.errors.InsufficientPrivilege:" in src
    assert "FROM acervo.evento_recuperacao" in src
