"""Contrato de `bin/mesa` (card #3141 passo 6): estado de chegada da story #3141 —

(1) `mesa escrever` devolve onde ficou (ramo, PR) e quando fica achável: "achável por
    `mesa caderno <slot>` depois do merge [...]; a abertura publica caderno sozinha em
    até 10 min".
(2) `mesa ver` mostra a anotação de mesa (substrato Valkey/`mesa anota`) como "anotação
    (expira em Xh)", nunca com a palavra "caderno" no rótulo — o rótulo velho, "(prosa,
    substrato velho)", confundia a anotação efêmera com o caderno durável.

`bin/mesa` não tem sufixo .py (é despachado por shebang); carregado aqui por
SourceFileLoader, mesmo padrão de bin/_conta/conta-abertura.py. `ato_ver` isola Redis
com um fake mínimo (só os métodos que a função usa: keys/get/delete) e desliga o
substrato de item (`pg() -> None`) — a mesma régua "banco fora do ar se declara
indisponível" que o próprio verbo já segue. `ato_escrever` roda contra um git real
(bare local, sem rede) porque a mensagem que se testa é o produto final do fluxo de
commit+push, não um trecho isolável sem reescrever o verbo. O ramo de PR (gh achado)
não entra aqui: `gh_bin` resolve por caminho fixo (/usr/bin/gh etc.), não por PATH —
testá-lo exigiria escrever nesse caminho do host, fora do que este teste deve tocar.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MESA_PATH = REPO_ROOT / "bin" / "mesa"


def carrega_mesa():
    """Importa bin/mesa como módulo (sem sufixo .py, spec_from_file_location não acha
    loader sozinho — passa-se SourceFileLoader explícito, como conta-abertura.py)."""
    loader = SourceFileLoader("_mesa", str(MESA_PATH))
    spec = spec_from_loader("_mesa", loader)
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


class _FakeRedis:
    """Só o que ato_ver usa da conexão: keys(padrao) e get(chave)."""

    def __init__(self, dados: dict[str, str]):
        self._dados = dados

    def keys(self, padrao: str):
        import fnmatch
        return sorted(k for k in self._dados if fnmatch.fnmatch(k, padrao))

    def get(self, chave: str):
        return self._dados.get(chave)

    def delete(self, chave: str):
        return 1 if self._dados.pop(chave, None) is not None else 0


def test_ato_ver_rotulo_anotacao_com_expira_e_sem_a_palavra_caderno(monkeypatch, capsys):
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)  # substrato de item indisponivel

    agora = 2_000_000.0
    monkeypatch.setattr(mesa.time, "time", lambda: agora)
    escrito_ha_46h = agora - 46 * 3600  # TTL 48h; restam 2h
    chave = "mem:mesateste:slotx"
    fake = _FakeRedis({chave: json.dumps({"t": int(escrito_ha_46h), "x": "texto de anotacao"})})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    rc = mesa.ato_ver(argparse.Namespace(slot=None))
    saida = capsys.readouterr().out

    assert rc == 0
    assert "[slotx] anotação (expira em 2 h)" in saida
    assert "texto de anotacao" in saida
    assert "caderno" not in saida
    assert "(prosa, substrato velho)" not in saida


def test_ato_ver_anotacao_vencida_expurga_e_nao_mostra(monkeypatch, capsys):
    """TTL estourado: expurgo físico no ato de servir (regra já existente), não regressão
    desta mudança — só confirma que o rótulo novo não quebrou esse caminho."""
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)

    agora = 2_000_000.0
    monkeypatch.setattr(mesa.time, "time", lambda: agora)
    escrito_ha_49h = agora - 49 * 3600  # TTL 48h: vencida
    chave = "mem:mesateste:slotv"
    fake = _FakeRedis({chave: json.dumps({"t": int(escrito_ha_49h), "x": "velha"})})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    rc = mesa.ato_ver(argparse.Namespace(slot=None))
    saida = capsys.readouterr().out

    assert rc == 0
    assert "slotv" not in saida
    assert chave not in fake._dados  # expurgada de verdade


@pytest.fixture()
def wt_harness(tmp_path, monkeypatch):
    """Bancada mínima: platafirma-harness com origin bare local, no candidato que
    _acha_worktree() resolve de primeira (raiz/platafirma-harness), sem `repo abrir`."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True, capture_output=True)

    wt = tmp_path / "platafirma-harness"
    wt.mkdir()
    _git(wt, "init", "-q", "-b", "main")
    _git(wt, "config", "user.email", "fixture@test.local")
    _git(wt, "config", "user.name", "fixture")
    (wt / "README.md").write_text("v1\n", encoding="utf-8")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "inicial")
    _git(wt, "remote", "add", "origin", str(origin))
    _git(wt, "push", "-q", "-u", "origin", "main")

    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    monkeypatch.delenv("PF_BIN", raising=False)
    return wt


def test_ato_escrever_devolve_ramo_e_quando_fica_achavel(wt_harness, monkeypatch, capsys):
    mesa = carrega_mesa()
    cad, slot = "mesateste", "construcao"
    monkeypatch.setenv("PF_CADEIRA", cad)
    monkeypatch.setattr("sys.stdin", io.StringIO("corpo do caderno de teste\n"))

    rc = mesa.ato_escrever(argparse.Namespace(slot=slot))
    saida = capsys.readouterr().out

    assert rc == 0
    assert f"caderno {slot}: gravado" in saida
    assert f"ramo: caderno/{cad}/{slot}" in saida
    assert (f"achável por `mesa caderno {slot}` depois do merge em main; "
            "a abertura publica caderno sozinha em até 10 min") in saida

    caderno = wt_harness / "abertura" / cad / slot / "caderno.md"
    assert caderno.read_text(encoding="utf-8") == "corpo do caderno de teste\n"
