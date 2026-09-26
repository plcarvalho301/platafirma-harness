"""Contrato de `conferir servico` sob a release (card #3150, estagio 3 da esteira).

Medido em 26/09: `release conferir servico harness-controle` saia 1 («nenhum container»)
com o servico de pe -- o filtro so casava o nome do container (harness-controle-tela-1),
nunca o projeto do compose, que e o nome da stack. E todo container servido de
/opt/platafirma/<familia>/<sha>/ saia DERIVA («nao e worktree de deploy»), a regua de
antes da release. A volta automatica do estagio 3 nao pode ligar em cima disso.

Prova: o filtro casa o projeto; container servido do sha que e o current e conforme;
de outro sha, divergente, nomeando os dois. Docker e git de stub (conferir.sh).
Nao prova: o docker real.
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path

CONFERIR_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"


def _carregar():
    loader = importlib.machinery.SourceFileLoader("conferir_servico_teste", str(CONFERIR_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


SHA_NO_AR = "a" * 40
SHA_VELHO = "b" * 40


def _montar(tmp_path, monkeypatch, sha_do_container):
    conferir = _carregar()
    raiz = tmp_path / "opt"
    for s in (SHA_NO_AR, SHA_VELHO):
        (raiz / "platafirma-harness" / s / "controle").mkdir(parents=True)
    os.symlink(SHA_NO_AR, raiz / "platafirma-harness" / "current")
    monkeypatch.setattr(conferir, "PROD_RAIZ", str(raiz))
    wd = str(raiz / "platafirma-harness" / sha_do_container / "controle")
    inspect = [{
        "Config": {
            "Labels": {
                "com.docker.compose.project": "harness-controle",
                "com.docker.compose.project.working_dir": wd,
                "com.docker.compose.service": "tela",
                "com.docker.compose.project.config_files": "",
            },
            "Env": [],
        },
        "State": {"StartedAt": "2026-09-26T20:00:00Z"},
    }]

    def sh(args, cwd=None):
        if args[:2] == ["docker", "ps"]:
            return 0, "harness-controle-tela-1\noutro-container-1", ""
        if args[:2] == ["docker", "inspect"]:
            if args[2] == "harness-controle-tela-1":
                return 0, json.dumps(inspect), ""
            return 0, json.dumps([{"Config": {"Labels": {"com.docker.compose.project": "outro"}, "Env": []}}]), ""
        if args[:2] == ["docker", "compose"]:
            return 0, json.dumps({"services": {"tela": {"environment": {}}}}), ""
        return 1, "", "stub"   # git: fora do escopo deste teste
    monkeypatch.setattr(conferir, "sh", sh)
    return conferir


def test_filtro_casa_o_projeto_do_compose_nao_so_o_nome(tmp_path, monkeypatch):
    conferir = _montar(tmp_path, monkeypatch, SHA_NO_AR)
    assert [c["nome"] for c in conferir.containers("harness-controle")] == ["harness-controle-tela-1"]
    assert [c["nome"] for c in conferir.containers("harness-controle-tela-1")] == ["harness-controle-tela-1"]
    assert list(conferir.containers("nao-existe")) == []


def test_origem_release_le_familia_e_sha(tmp_path, monkeypatch):
    conferir = _montar(tmp_path, monkeypatch, SHA_NO_AR)
    wd = Path(conferir.PROD_RAIZ) / "platafirma-harness" / SHA_NO_AR / "controle"
    assert conferir.origem_release(str(wd)) == ("platafirma-harness", SHA_NO_AR)
    assert conferir.origem_release(str(tmp_path)) is None
    assert conferir.sha_current("platafirma-harness") == SHA_NO_AR


def test_servido_do_current_e_conforme(tmp_path, monkeypatch, capsys):
    conferir = _montar(tmp_path, monkeypatch, SHA_NO_AR)
    rc = _roda(conferir, "harness-controle")
    saida = capsys.readouterr().out
    assert "nao e worktree de deploy" not in saida
    assert "1 conforme" in saida, saida
    assert rc == 0


def test_servido_de_outro_sha_e_divergente_e_nomeia(tmp_path, monkeypatch, capsys):
    conferir = _montar(tmp_path, monkeypatch, SHA_VELHO)
    rc = _roda(conferir, "harness-controle")
    saida = capsys.readouterr().out
    assert "stack fora do current" in saida, saida
    assert SHA_VELHO[:7] in saida and SHA_NO_AR[:7] in saida
    assert rc == 1


def _roda(conferir, alvo):
    try:
        r = conferir.conferir_servico(alvo)
    except SystemExit as e:
        return e.code
    return r if isinstance(r, int) else 0
