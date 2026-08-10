# Contrato de `fila status --json` (bin/fila_streams.py) — card #390, LOTE 1.
#
# Sem Redis rodando nesta maquina: a conexao e um fake in-memory (FakeRC) que
# devolve respostas canonicas de XLEN/XINFO GROUPS/XRANGE/XINFO CONSUMERS,
# injetado no lugar de `fila_streams.r_conn`. O verbo roda de ponta a ponta
# (main() -> cmd_status -> conta_novas) como rodaria com Redis de verdade.
import json
import sys
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parents[2] / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

import fila_streams
import redis


class FakeRC:
    """Conexao Redis fake, roteada por persona (a partir de "caixa:<persona>").

    `personas`: dict persona -> {"xlen": int, "groups": [...], "xrange": [...],
    "consumers": [...]} — os quatro comandos que conta_novas()/detalhe_status()
    usam. `ping_ok=False` simula queda da malha msg.
    """

    def __init__(self, personas: dict, ping_ok: bool = True):
        self._personas = personas
        self._ping_ok = ping_ok

    def ping(self):
        if not self._ping_ok:
            raise redis.exceptions.ConnectionError("connection refused")
        return True

    def xgroup_create(self, *a, **k):
        return True

    def _p(self, chave: str) -> dict:
        persona = chave.split(":", 1)[1]
        return self._personas[persona]

    def xlen(self, chave):
        return self._p(chave)["xlen"]

    def xinfo_groups(self, chave):
        return self._p(chave)["groups"]

    def xrange(self, chave, min="-", max="+", count=None):
        entradas = self._p(chave)["xrange"]
        return list(entradas[:count]) if count else list(entradas)

    def xinfo_consumers(self, chave, grupo):
        return self._p(chave)["consumers"]


def _rodar_cli(monkeypatch, capsys, argv, eu, rc):
    """Reproduz o caminho real: main() inteiro, com r_conn() trocado pelo fake."""
    monkeypatch.setattr(sys, "argv", ["fila"] + argv)
    monkeypatch.setenv("PF_CADEIRA", eu)
    monkeypatch.delenv("FILA_RAIZ", raising=False)
    monkeypatch.setattr(fila_streams, "r_conn", lambda: rc)
    try:
        fila_streams.main()
        exit_code = 0
    except SystemExit as e:
        exit_code = e.code
    return exit_code, capsys.readouterr()


# ---------- formato --json, caminho feliz ----------

def test_status_json_persona_unica_com_pendente(monkeypatch, capsys):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({
        "claudinho-TI": {
            "xlen": 5,
            "groups": [{"name": "cadeira", "pending": 0, "lag": None, "last-delivered-id": "100-0"}],
            "xrange": [
                ("100-1", {"id": "20260809T120000-claudinho-IA", "de": "claudinho-IA", "tipo": "pedido",
                            "assunto": "a", "ref": "", "responde": "", "corpo": "x"}),
                ("100-2", {"id": "20260809T130000-claudinho-IA", "de": "claudinho-IA", "tipo": "pedido",
                            "assunto": "b", "ref": "", "responde": "", "corpo": "y"}),
            ],
            "consumers": [{"name": "claudinho-TI", "idle": 45000, "pending": 0}],
        },
    })

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "claudinho-TI", "--json"], "claudinho-TI", rc)

    assert code == 0
    assert cap.err == ""
    saida = json.loads(cap.out)
    assert len(saida) == 1
    item = saida[0]
    idade = item.pop("idade_mais_antiga_seg")
    assert item == {
        "persona": "claudinho-TI",
        "pendentes": 2,
        "total_historico": 5,
        "estado": "parada",
        "ultima_leitura_seg": 45,
    }
    # idade da carta mais antiga: carimbo de 2026-08-09T12:00 local, positivo e plausivel
    assert isinstance(idade, int)
    assert idade > 0


def test_status_json_todas_mistura_vazia_e_parada(monkeypatch, capsys):
    monkeypatch.setattr(fila_streams, "personas_validas",
                         lambda: {"claudinho-TI", "claudinha-produto"})
    rc = FakeRC({
        "claudinho-TI": {
            "xlen": 5,
            "groups": [{"name": "cadeira", "pending": 0, "lag": None, "last-delivered-id": "100-0"}],
            "xrange": [
                ("100-1", {"id": "20260809T120000-claudinho-IA", "de": "claudinho-IA", "tipo": "pedido",
                            "assunto": "a", "ref": "", "responde": "", "corpo": "x"}),
            ],
            "consumers": [{"name": "claudinho-TI", "idle": 1000, "pending": 0}],
        },
        "claudinha-produto": {
            "xlen": 0,
            "groups": [],
            "xrange": [],
            "consumers": [],
        },
    })

    code, cap = _rodar_cli(
        monkeypatch, capsys, ["status", "--todas", "--json"], "claudinha-gestao-estrategica", rc
    )

    assert code == 0
    assert cap.err == ""
    saida = json.loads(cap.out)
    por_persona = {item["persona"]: item for item in saida}

    assert por_persona["claudinha-produto"] == {
        "persona": "claudinha-produto",
        "pendentes": 0,
        "total_historico": 0,
        "estado": "vazia",
        "idade_mais_antiga_seg": None,
        "ultima_leitura_seg": None,
    }
    assert por_persona["claudinho-TI"]["estado"] == "parada"
    assert por_persona["claudinho-TI"]["pendentes"] == 1
    assert por_persona["claudinho-TI"]["ultima_leitura_seg"] == 1


def test_status_json_caixa_em_dia_sem_pendente(monkeypatch, capsys):
    """total > 0 mas pendentes == 0 -> em_dia; nunca leu -> ultima_leitura None."""
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({
        "claudinho-TI": {
            "xlen": 3,
            "groups": [{"name": "cadeira", "pending": 0, "lag": 0, "last-delivered-id": "100-0"}],
            "xrange": [],
            "consumers": [],
        },
    })

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "claudinho-TI", "--json"], "claudinho-TI", rc)

    assert code == 0
    saida = json.loads(cap.out)
    assert saida == [{
        "persona": "claudinho-TI",
        "pendentes": 0,
        "total_historico": 3,
        "estado": "em_dia",
        "idade_mais_antiga_seg": None,
        "ultima_leitura_seg": None,
    }]


# ---------- texto sem --json: nao muda nem uma linha ----------

def test_status_texto_sem_json_inalterado(monkeypatch, capsys):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({
        "claudinho-TI": {
            "xlen": 5,
            "groups": [{"name": "cadeira", "pending": 0, "lag": None, "last-delivered-id": "100-0"}],
            "xrange": [
                ("100-1", {"id": "20260809T120000-claudinho-IA", "de": "claudinho-IA", "tipo": "pedido",
                            "assunto": "a", "ref": "", "responde": "", "corpo": "x"}),
                ("100-2", {"id": "20260809T130000-claudinho-IA", "de": "claudinho-IA", "tipo": "pedido",
                            "assunto": "b", "ref": "", "responde": "", "corpo": "y"}),
            ],
            "consumers": [{"name": "claudinho-TI", "idle": 45000, "pending": 0}],
        },
    })

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "claudinho-TI"], "claudinho-TI", rc)

    assert code == 0
    assert cap.out == "claudinho-TI: 2 nova(s) · 5 no historico (7 dias)\n"
    assert cap.err == ""


# ---------- falha: objeto com "erro", nunca stdout vazio ----------

def test_status_json_conexao_falha_vira_objeto_erro(monkeypatch, capsys):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({}, ping_ok=False)

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "claudinho-TI", "--json"], "claudinho-TI", rc)

    assert code == 1
    assert cap.err == ""
    saida = json.loads(cap.out)
    assert set(saida.keys()) == {"erro"}
    assert saida["erro"]


def test_status_texto_conexao_falha_mensagem_solta_em_stderr(monkeypatch, capsys):
    """Sem --json o comportamento de hoje continua: mensagem em stderr, stdout vazio."""
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({}, ping_ok=False)

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "claudinho-TI"], "claudinho-TI", rc)

    assert code == 1
    assert cap.out == ""
    assert "nao alcancei a malha msg" in cap.err


def test_status_json_persona_desconhecida_vira_objeto_erro(monkeypatch, capsys):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({})

    code, cap = _rodar_cli(
        monkeypatch, capsys, ["status", "claudinha-fantasma", "--json"], "claudinho-TI", rc
    )

    assert code == 1
    assert cap.err == ""
    saida = json.loads(cap.out)
    assert set(saida.keys()) == {"erro"}
    assert "claudinha-fantasma" in saida["erro"]


def test_status_json_todas_sem_espia_vira_objeto_erro(monkeypatch, capsys):
    """--todas continua so de claudinha-gestao-estrategica; com --json o
    controle de acesso nao muda, so o formato da falha."""
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({})

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "--todas", "--json"], "claudinho-TI", rc)

    assert code == 1
    assert cap.err == ""
    saida = json.loads(cap.out)
    assert set(saida.keys()) == {"erro"}


def test_status_todas_via_cli_de_verdade(monkeypatch, capsys):
    """Achado no LOTE 1: `fila status --todas` invocado de verdade via argv
    falhava no argparse antes desta mudança — a posicional simples `persona`
    não aceitava um token "--todas" ("the following arguments are required:
    persona", exit 2), mesmo reproduzido contra o HEAD sem nenhuma mudança
    desta fatia. Bloqueava o agregador do LOTE 2, que precisa exatamente
    desta chamada pro Bloco 2 (Caixas) — corrigido aqui: "persona" virou
    posicional opcional e "--todas" virou flag de verdade (`--todas` deixa
    de ser comparado como valor de "persona"). Este teste passa pela CLI
    real (main() + argparse), não por um Namespace montado à mão."""
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({
        "claudinho-TI": {"xlen": 0, "groups": [], "xrange": [], "consumers": []},
    })

    code, cap = _rodar_cli(
        monkeypatch, capsys, ["status", "--todas", "--json"], "claudinha-gestao-estrategica", rc
    )

    assert code == 0
    assert cap.err == ""
    saida = json.loads(cap.out)
    assert saida == [{
        "persona": "claudinho-TI",
        "pendentes": 0,
        "total_historico": 0,
        "estado": "vazia",
        "idade_mais_antiga_seg": None,
        "ultima_leitura_seg": None,
    }]


def test_status_sem_persona_e_sem_todas_vira_uso_incorreto(monkeypatch, capsys):
    """Nem persona nem --todas: antes o argparse pegava sozinho (persona
    obrigatória); com persona opcional, cmd_status precisa do próprio
    guard — confere que ele cobre o buraco que abriu."""
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({})

    code, cap = _rodar_cli(monkeypatch, capsys, ["status", "--json"], "claudinho-TI", rc)
    assert code == 2
    saida = json.loads(cap.out)
    assert saida.get("erro")

    code, cap = _rodar_cli(monkeypatch, capsys, ["status"], "claudinho-TI", rc)
    assert code == 2
    assert cap.out == ""
    assert "uso" in cap.err


def test_status_json_sem_identidade_vira_objeto_erro(monkeypatch, capsys):
    """PF_CADEIRA ausente e sem --eu: falha antes mesmo de tocar o Redis."""
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"claudinho-TI"})
    rc = FakeRC({})

    monkeypatch.setattr(sys, "argv", ["fila", "status", "claudinho-TI", "--json"])
    monkeypatch.delenv("PF_CADEIRA", raising=False)
    monkeypatch.delenv("FILA_RAIZ", raising=False)
    monkeypatch.setattr(fila_streams, "r_conn", lambda: rc)

    with pytest.raises(SystemExit) as exc:
        fila_streams.main()
    cap = capsys.readouterr()

    assert exc.value.code == 2
    assert cap.err == ""
    saida = json.loads(cap.out)
    assert set(saida.keys()) == {"erro"}


# ---------- conta_novas(): unidade da extensao detalhado=True ----------

def test_conta_novas_detalhado_sem_pendente_idade_none():
    rc = FakeRC({
        "claudinho-TI": {
            "xlen": 2,
            "groups": [{"name": "cadeira", "pending": 0, "lag": 0, "last-delivered-id": "100-0"}],
            "xrange": [],
            "consumers": [{"name": "claudinho-TI", "idle": 5000, "pending": 0}],
        },
    })
    n, total, idade, ultima = fila_streams.conta_novas(rc, "claudinho-TI", detalhado=True)
    assert (n, total, idade, ultima) == (0, 2, None, 5)


def test_conta_novas_nao_detalhado_e_tupla_de_dois():
    rc = FakeRC({
        "claudinho-TI": {
            "xlen": 2,
            "groups": [{"name": "cadeira", "pending": 0, "lag": 0, "last-delivered-id": "100-0"}],
            "xrange": [],
            "consumers": [],
        },
    })
    resultado = fila_streams.conta_novas(rc, "claudinho-TI")
    assert resultado == (0, 2)
