"""DT 430 — a poda diz «igual ao giro N» de retorno que a sessão nunca recebeu.

O ledger grava o giro como servido quando a porta o produz, e a porta não sabe se o retorno chegou:
a fita foi compactada, a conversa foi retomada com o mesmo `sessao_id`, o transporte perdeu o corpo.
Duas travas fecham o caso, e este arquivo as prende:

1. o molde de card (`tarefas modelo ...`) é alça de constituição: a cadeira o copia literal para
   escrever o card, então sai inteiro em toda chamada, nunca como aviso;
2. nos demais atos o aviso diz como reaver (`inteiro=true`), e `inteiro=true` apaga a alça e devolve
   o texto inteiro.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-poda430-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import poda  # noqa: E402
import server as s  # noqa: E402

_SID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
# linhas distintas: a poda lava repetição («× 12») e o teste mediria o lavado, não o ledger
_MOLDE = "\n".join(f"Campo {i}: rótulo {i * 7} que a API exige no corpo do nível" for i in range(30)) + "\n"


class _Fake:
    def __init__(self):
        self.kv, self.h = {}, {}

    def incr(self, k):
        return self.incrby(k, 1)

    def incrby(self, k, n):
        self.kv[k] = int(self.kv.get(k, 0)) + n
        return self.kv[k]

    def get(self, k):
        return self.kv.get(k)

    def expire(self, k, ttl):
        return True

    def hget(self, k, f):
        return self.h.get(k, {}).get(f)

    def hset(self, k, f=None, v=None, mapping=None):
        if mapping:
            self.h.setdefault(k, {}).update(mapping)
        else:
            self.h.setdefault(k, {})[f] = v
        return 1

    def hdel(self, k, f):
        self.h.get(k, {}).pop(f, None)
        return 1


@pytest.fixture
def porta(monkeypatch, tmp_path):
    fake = _Fake()
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "derrame")
    monkeypatch.setattr(s, "_rc", lambda: fake)
    monkeypatch.setattr(s, "_poda_ligada", lambda: True)

    def serve(tool, alca, texto, **kw):
        r = {"exit_code": 0, "stdout": {"texto": texto, "truncado": False}}
        return s._serve(r, tool=tool, alca=alca, ident={"sessao_id": _SID}, **kw)

    return serve


def _texto(r):
    return r["stdout"]["texto"]


def test_molde_de_card_e_alca_de_constituicao():
    assert s._eh_constitutiva("tarefas", "tarefas modelo feature")
    assert s._eh_constitutiva("tarefas", "tarefas modelo story derivada")
    assert not s._eh_constitutiva("tarefas", "tarefas ler 4120")


def test_molde_sai_inteiro_na_segunda_chamada(porta):
    um = porta("tarefas", "tarefas modelo feature", _MOLDE)
    dois = porta("tarefas", "tarefas modelo feature", _MOLDE)
    assert not _texto(um).startswith("[igual")
    assert _texto(dois) == _texto(um)                   # o mesmo texto, nunca «igual ao giro N»


def test_ato_comum_repetido_vira_aviso_que_diz_como_reaver(porta):
    porta("tarefas", "tarefas ler 4120", _MOLDE)
    dois = porta("tarefas", "tarefas ler 4120", _MOLDE)
    assert _texto(dois).startswith("[igual ao giro")
    assert "inteiro=true reenvia" in _texto(dois)       # o aviso entrega a cura, em qualquer verbo


def test_inteiro_true_devolve_o_texto_que_o_registro_tinha_por_servido(porta):
    primeiro = porta("tarefas", "tarefas ler 4120", _MOLDE)
    assert porta("tarefas", "tarefas ler 4120", _MOLDE)["stdout"]["texto"].startswith("[igual")
    de_novo = porta("tarefas", "tarefas ler 4120", _MOLDE, esquece=True)
    assert _texto(de_novo) == _texto(primeiro)


def test_a_porta_do_verbo_aceita_inteiro():
    # a assinatura da tool do verbo e o item do lote carregam `inteiro` (texto: o FastMCP monta a
    # assinatura em tempo de importação, e o item de lote é lido de dict)
    fonte = (OPS_SERVER_DIR / "server.py").read_text()
    assert "inteiro: bool = False" in fonte
    assert 'esquece=bool(item.get("inteiro"))' in fonte
    assert "esquece=inteiro" in fonte
