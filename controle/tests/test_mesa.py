"""Contrato de `bin/mesa` (card #3141 passo 6): estado de chegada da story #3141 —

(1) `mesa escrever` devolve onde ficou (ramo, PR) e quando fica achável: "achável por
    `mesa caderno <slot>` depois do merge [...]; a abertura publica caderno sozinha em
    até 10 min".
(2) `mesa ver` mostra a anotação de mesa (substrato Valkey/`mesa anota`) como "anotação
    (expira em Xh)", nunca com a palavra "caderno" no rótulo — o rótulo velho, "(prosa,
    substrato velho)", confundia a anotação efêmera com o caderno durável.

`bin/mesa` não tem sufixo .py (é despachado por shebang); carregado aqui por
SourceFileLoader, mesmo padrão de bin/_metrica/abertura.py. `ato_ver` isola Redis
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
    loader sozinho — passa-se SourceFileLoader explícito, como bin/_metrica/abertura.py)."""
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

    ramo = _ramo_da_saida(saida)
    assert _mostra(wt_harness, f"origin/{ramo}:abertura/{cad}/{slot}/caderno.md") == \
        "corpo do caderno de teste\n"
    # escreve em worktree efemero: o checkout do clone nao e tocado
    assert not (wt_harness / "abertura").exists()


def _ramo_da_saida(saida: str) -> str:
    import re
    return re.search(r"ramo: (\S+)", saida).group(1)


def _mostra(cwd: Path, spec: str) -> str:
    _git(cwd, "fetch", "-q", "origin")
    return subprocess.run(["git", "show", spec], cwd=str(cwd), capture_output=True,
                          text=True, check=True).stdout


# --- card #3166: anotar acrescenta, nunca apaga sem avisar -----------------------------

class _FakeRedisComEval(_FakeRedis):
    """Estende _FakeRedis com set/eval, o quanto basta pra exercitar LUA_ANOTA sem Redis
    real -- regra do dono (27/09): teste nao depende de estado real; a suite roda com
    MEM_REDIS_PORT apontado pra porta 9 de proposito (lib/teste_isolado.py). O eval aqui
    espelha linha a linha o script Lua do verbo: prova o contrato que ato_anota espera
    dele (CAS opcional, concatenacao, TTL), nao substitui a leitura do Lua real."""

    def set(self, chave, valor, ex=None):
        self._dados[chave] = valor
        return True

    def eval(self, script, numkeys, *args):
        chave_fita, chave_slot, fid, texto_novo, ttl, ts = args
        if fid and self._dados.get(chave_fita) != fid:
            return 0
        atual = self._dados.get(chave_slot)
        texto_final = texto_novo
        if atual:
            try:
                decodificado = json.loads(atual)
            except ValueError:
                decodificado = None
            if decodificado and decodificado.get("x"):
                texto_final = decodificado["x"] + "\n\n---\n\n" + texto_novo
        self.set(chave_slot, json.dumps({"t": int(ts), "x": texto_final}), ex=ttl)
        return 1


def test_ato_anota_acrescenta_sem_apagar_e_ver_mostra_as_duas(monkeypatch, capsys):
    """O defeito medido em 26 e 27/09 (tres vezes nos cadernos): `mesa anota` reescrevia
    o slot inteiro. Duas anotacoes seguidas no mesmo slot tem de aparecer as DUAS em
    `mesa ver`."""
    mesa = carrega_mesa()
    cad, slot = "mesateste", "acrescimo3166"
    monkeypatch.setenv("PF_CADEIRA", cad)
    fake = _FakeRedisComEval({})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    r1 = mesa.ato_anota(argparse.Namespace(slot=slot, texto="primeira nota", se_fita=None))
    capsys.readouterr()
    assert r1 == 0

    r2 = mesa.ato_anota(argparse.Namespace(slot=slot, texto="segunda nota", se_fita=None))
    capsys.readouterr()
    assert r2 == 0

    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)
    rv = mesa.ato_ver(argparse.Namespace(slot=slot))
    saida = capsys.readouterr().out
    assert rv == 0
    assert "primeira nota" in saida
    assert "segunda nota" in saida


def test_ato_anota_com_fita_errada_descarta_e_nao_acrescenta(monkeypatch, capsys):
    """A guarda de fita (criterio 18 da minuta 0002) segue valendo: ritual de fita velha
    nao acrescenta por cima da fita nova."""
    mesa = carrega_mesa()
    cad, slot = "mesateste", "guardafita3166"
    monkeypatch.setenv("PF_CADEIRA", cad)
    fake = _FakeRedisComEval({f"fita:{cad}": "fita-nova"})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    r = mesa.ato_anota(argparse.Namespace(slot=slot, texto="nota tardia", se_fita="fita-velha"))
    erro = capsys.readouterr().err
    assert r == 3
    assert "DESCARTADA" in erro
    assert fake._dados.get(f"mem:{cad}:{slot}") is None


def test_ato_escrever_recusa_quando_apagaria_publicado(tmp_path, wt_harness, monkeypatch, capsys):
    """O outro defeito do card: `mesa escrever` gravava o arquivo inteiro por cima sem
    olhar o que ja tinha (27/09: 6,4 KB trocados por 989 B, sem aviso, PR aberto). Corpo
    novo que nao estende o publicado recusa, mostrando o que se perderia. PF_ABERTURA_DIR
    tem de estar no ambiente ANTES de carrega_mesa(): CADERNOS e constante de modulo."""
    cad, slot = "mesateste", "recusa3166"
    pub_dir = tmp_path / "abertura-pub"
    caderno = pub_dir / "current" / "abertura" / cad / slot / "caderno.md"
    caderno.parent.mkdir(parents=True)
    caderno.write_text("CONHECIMENTO CURADO\n- linha antiga importante\n" * 50, encoding="utf-8")
    monkeypatch.setenv("PF_ABERTURA_DIR", str(pub_dir))
    mesa = carrega_mesa()

    monkeypatch.setenv("PF_CADEIRA", cad)
    monkeypatch.setattr("sys.stdin", io.StringIO("corpo novo, bem menor\n"))

    rc = mesa.ato_escrever(argparse.Namespace(slot=slot, sobrescrever=False))
    erro = capsys.readouterr().err

    assert rc == 4
    assert "recuso" in erro
    assert "linha antiga importante" in erro


def test_ato_escrever_que_estende_o_publicado_nao_precisa_de_sobrescrever(tmp_path, wt_harness, monkeypatch, capsys):
    cad, slot = "mesateste", "estende3166"
    pub_dir = tmp_path / "abertura-pub"
    caderno = pub_dir / "current" / "abertura" / cad / slot / "caderno.md"
    caderno.parent.mkdir(parents=True)
    caderno.write_text("velho\n", encoding="utf-8")
    monkeypatch.setenv("PF_ABERTURA_DIR", str(pub_dir))
    mesa = carrega_mesa()

    monkeypatch.setenv("PF_CADEIRA", cad)
    monkeypatch.setattr("sys.stdin", io.StringIO("velho\nmais uma linha\n"))

    rc = mesa.ato_escrever(argparse.Namespace(slot=slot, sobrescrever=False))
    saida = capsys.readouterr().out
    assert rc == 0, saida
    assert f"caderno {slot}: gravado" in saida


def test_ato_escrever_sobrescrever_confirma_a_troca(tmp_path, wt_harness, monkeypatch, capsys):
    cad, slot = "mesateste", "sobrescrever3166"
    pub_dir = tmp_path / "abertura-pub"
    caderno = pub_dir / "current" / "abertura" / cad / slot / "caderno.md"
    caderno.parent.mkdir(parents=True)
    caderno.write_text("velho, sem nada em comum com o novo\n", encoding="utf-8")
    monkeypatch.setenv("PF_ABERTURA_DIR", str(pub_dir))
    mesa = carrega_mesa()

    monkeypatch.setenv("PF_CADEIRA", cad)
    monkeypatch.setattr("sys.stdin", io.StringIO("corpo totalmente novo\n"))

    rc = mesa.ato_escrever(argparse.Namespace(slot=slot, sobrescrever=True))
    saida = capsys.readouterr().out
    assert rc == 0, saida
    assert f"caderno {slot}: gravado" in saida


def test_ato_escrever_parte_de_origin_main_mesmo_com_clone_em_ramo_velho(
        wt_harness, monkeypatch, capsys):
    """Incidente 26/09 (fila 20260926T120002-ia): clone compartilhado parado em ramo
    velho; `mesa escrever` commitava em cima dele e o push regrediria main. A escrita
    tem de partir de origin/main, e o clone fica onde estava."""
    mesa = carrega_mesa()
    cad, slot = "mesateste", "construcao"
    # clone parado num ramo velho com arquivo que main nao tem
    _git(wt_harness, "checkout", "-q", "-b", "caderno/produto/jornada")
    (wt_harness / "VELHO.md").write_text("so no ramo velho\n", encoding="utf-8")
    _git(wt_harness, "add", "-A")
    _git(wt_harness, "commit", "-q", "-m", "ramo velho")
    # main andou na origem depois disso
    _git(wt_harness, "checkout", "-q", "main")
    (wt_harness / "README.md").write_text("v2\n", encoding="utf-8")
    _git(wt_harness, "commit", "-q", "-am", "main anda")
    _git(wt_harness, "push", "-q", "origin", "main")
    _git(wt_harness, "checkout", "-q", "caderno/produto/jornada")

    monkeypatch.setenv("PF_CADEIRA", cad)
    monkeypatch.setattr("sys.stdin", io.StringIO("item novo\n"))
    rc = mesa.ato_escrever(argparse.Namespace(slot=slot))
    saida = capsys.readouterr().out
    assert rc == 0

    ramo = _ramo_da_saida(saida)
    assert ramo.startswith(f"caderno/{cad}/{slot}-")
    pai = subprocess.run(["git", "rev-parse", f"origin/{ramo}~1", "origin/main"],
                         cwd=str(wt_harness), capture_output=True, text=True,
                         check=True).stdout.split()
    assert pai[0] == pai[1], "a escrita tem de ter origin/main como pai"
    arquivos = subprocess.run(["git", "ls-tree", "-r", "--name-only", f"origin/{ramo}"],
                              cwd=str(wt_harness), capture_output=True, text=True,
                              check=True).stdout.split()
    assert "VELHO.md" not in arquivos
    # clone intacto e worktree efemero removido
    atual = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(wt_harness),
                           capture_output=True, text=True, check=True).stdout.strip()
    assert atual == "caderno/produto/jornada"
    wts = subprocess.run(["git", "worktree", "list"], cwd=str(wt_harness),
                         capture_output=True, text=True, check=True).stdout.splitlines()
    assert len(wts) == 1
