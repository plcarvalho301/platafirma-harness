"""`sessao longjob run` repassa a identidade da porta a unit (mesa ti #21).

O systemd --user nao herda o ambiente de quem chama: sem repasse explicito, verbo que
exige PF_SUJEITO (infra up, migrar aplicar) recusava dentro do job. O teste troca o
`systemd-run` por um stub que grava os argumentos e confere o que chegaria a unit.
"""
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LONGJOB = REPO_ROOT / "bin" / "_sessao" / "longjob"

IDENT = ("PF_SUJEITO", "PF_CADEIRA", "PF_SESSAO", "PF_ORDEM_ID", "PF_SUPERFICIE")


def _roda(tmp_path, extra):
    stubdir = tmp_path / "stub"
    stubdir.mkdir()
    capt = tmp_path / "args.txt"
    stub = stubdir / "systemd-run"
    # grava os argumentos e, a parte, o RAG_API_TOKEN que a unit receberia do ambiente do systemd-run
    stub.write_text(f'#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > "{capt}"\n'
                    f'printf "%s" "${{RAG_API_TOKEN:-}}" > "{capt}.token"\n')
    stub.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in IDENT and k != "RAG_API_TOKEN"}
    env.update({
        "PATH": f"{stubdir}:{env.get('PATH', '/usr/bin:/bin')}",
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
        "LONGJOB_LOGDIR": str(tmp_path / "log"),
    })
    env.update(extra)
    r = subprocess.run(["bash", str(LONGJOB), "run", "prova", "true"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    log = next((tmp_path / "log").glob("platafirma-job-prova-*.log")).read_text()
    return capt.read_text().splitlines(), log


def test_repassa_identidade_presente(tmp_path):
    args, log = _roda(tmp_path, {"PF_SUJEITO": "jose-123", "PF_CADEIRA": "ti",
                                  "PF_SESSAO": "s-1"})
    assert "--setenv=PF_SUJEITO=jose-123" in args
    assert "--setenv=PF_CADEIRA=ti" in args
    assert "--setenv=PF_SESSAO=s-1" in args
    assert "# sujeito=jose-123" in log
    # o comando continua depois do separador
    assert args[args.index("--") + 1:] == ["true"]


def test_ausente_segue_ausente(tmp_path):
    args, log = _roda(tmp_path, {})
    assert not [a for a in args if a.startswith("--setenv=PF_")]
    assert "# sujeito=(ausente)" in log
    assert "# agente=" not in log


def test_repassa_urls_do_motor_e_rag(tmp_path):
    """DT #215: repassa MOTOR_ACERVO_URL, RAG_API_URL e RAG_API_BASE à unit transiente."""
    urls = {
        "MOTOR_ACERVO_URL": "http://127.0.0.1:8100",
        "RAG_API_URL": "http://127.0.0.1:8120/api",
        "RAG_API_BASE": "http://127.0.0.1:8120",
    }
    args, _ = _roda(tmp_path, urls)
    for k, v in urls.items():
        assert f"--setenv={k}={v}" in args


def _token_visto(tmp_path):
    return (tmp_path / "args.txt.token").read_text()


def test_repassa_segredo_rag_token_do_ambiente_sem_poe_lo_no_argumento(tmp_path):
    args, log = _roda(tmp_path, {"RAG_API_TOKEN": "token-teste-env"})
    assert "--setenv=RAG_API_TOKEN" in args                  # so o nome: o systemd-run le o valor do ambiente
    assert _token_visto(tmp_path) == "token-teste-env"
    assert not [a for a in args if "token-teste-env" in a]   # nunca no argv (ps)
    assert "token-teste-env" not in log                      # nem no log do job


def test_repassa_segredo_rag_token_da_instancia(tmp_path):
    # Do arquivo da instancia quando ausente no ambiente (DT #64 e #400)
    segdir = tmp_path / "inst" / "segredos" / "rag"
    segdir.mkdir(parents=True)
    (segdir / "RAG_API_TOKEN").write_text("token-teste-disco\n")
    args, _ = _roda(tmp_path, {})
    assert "--setenv=RAG_API_TOKEN" in args
    assert _token_visto(tmp_path) == "token-teste-disco"


def test_token_do_motor_vale_mais_que_o_do_rag(tmp_path):
    # o motor declara o segredo em segredos/busca (registro/motor-instancias.json)
    for stk, val in (("busca", "token-do-motor"), ("rag", "token-do-rag")):
        d = tmp_path / "inst" / "segredos" / stk
        d.mkdir(parents=True)
        (d / "RAG_API_TOKEN").write_text(val + "\n")
    _roda(tmp_path, {})
    assert _token_visto(tmp_path) == "token-do-motor"


def test_sem_token_nao_cria_variavel(tmp_path):
    args, _ = _roda(tmp_path, {})
    assert "--setenv=RAG_API_TOKEN" not in args


# ---- atributos do agente (card #3156, spec agente §11.1: o job herda os cinco) ----

AGENTE = {"PF_AGENTE": "revisor", "PF_EM_NOME_DE": "engenharia", "PF_CONTA_AGENTE": "claudinho",
          "PF_ORIGEM_SESSAO": "11111111-1111-4111-8111-111111111111"}


def test_repassa_atributos_do_agente_e_os_registra(tmp_path):
    args, log = _roda(tmp_path, {"PF_SUJEITO": "jose-123", "PF_SESSAO": "s-1", **AGENTE})
    for k, v in AGENTE.items():
        assert f"--setenv={k}={v}" in args
    assert "# sujeito=jose-123" in log
    assert "# agente=revisor" in log and "# em_nome_de=engenharia" in log
    assert "# origem=11111111-1111-4111-8111-111111111111" in log and "# conta=claudinho" in log
    assert args[args.index("--") + 1:] == ["true"]


# ---- `sessao longjob run`: le a chave viva e poe os atributos no ambiente do exec ----

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from unittest.mock import patch

_loader = SourceFileLoader("sessao_longjob_heranca", str(REPO_ROOT / "bin" / "sessao"))
_spec = importlib.util.spec_from_loader("sessao_longjob_heranca", _loader)
sessao_mod = importlib.util.module_from_spec(_spec)
_loader.exec_module(sessao_mod)

FILHA = "22222222-2222-4222-8222-222222222222"
CHAVE = {"sujeito": "jose-123", "cadeira": "engenharia", "origem_sessao": AGENTE["PF_ORIGEM_SESSAO"],
         "agente": "revisor", "em_nome_de": "engenharia", "conta_agente": "claudinho"}


class _Mem:
    def __init__(self, d):
        self.d = d

    def get(self, k):
        return self.d.get(k)


def _exec_env(monkeypatch, env_extra, mem=(None, "sem"), resto=("run", "nome", "true")):
    for v in (*IDENT, *AGENTE):
        monkeypatch.delenv(v, raising=False)
    for k, v in env_extra.items():
        monkeypatch.setenv(k, v)
    with patch.object(sessao_mod, "_msgmem", return_value=mem), \
         patch.object(sessao_mod.os, "execve") as ex:
        sessao_mod.ato_longjob(list(resto))
    return ex.call_args[0][2]


def test_sessao_longjob_herda_da_chave(monkeypatch):
    env = _exec_env(monkeypatch, {"PF_SUJEITO": "jose-123", "PF_SESSAO": FILHA},
                    mem=(_Mem({f"sessao:{FILHA}": json.dumps(CHAVE)}), None))
    for k, v in AGENTE.items():
        assert env[k] == v
    assert env["PF_SUJEITO"] == "jose-123"


def test_sessao_longjob_nao_tira_sujeito_da_chave(monkeypatch):
    """spec_acesso §2: a pessoa vem da porta, nunca da chave; sem PF_SUJEITO segue sem."""
    env = _exec_env(monkeypatch, {"PF_SESSAO": FILHA},
                    mem=(_Mem({f"sessao:{FILHA}": json.dumps(CHAVE)}), None))
    assert "PF_SUJEITO" not in env
    assert env["PF_AGENTE"] == "revisor"


def test_sessao_longjob_ambiente_declarado_vence(monkeypatch):
    env = _exec_env(monkeypatch, {"PF_SESSAO": FILHA, "PF_AGENTE": "curador"},
                    mem=(_Mem({f"sessao:{FILHA}": json.dumps(CHAVE)}), None))
    assert env["PF_AGENTE"] == "curador"
    assert env["PF_EM_NOME_DE"] == "engenharia"


def test_sessao_longjob_sessao_comum_nao_ganha_atributo(monkeypatch):
    env = _exec_env(monkeypatch, {"PF_SESSAO": FILHA},
                    mem=(_Mem({f"sessao:{FILHA}": json.dumps({"sujeito": "x", "cadeira": "ti"})}), None))
    assert not set(AGENTE) & set(env)


def test_sessao_longjob_msgmem_mudo_sobe_sem_atributo(monkeypatch, capsys):
    env = _exec_env(monkeypatch, {"PF_SESSAO": FILHA}, mem=(None, "ConnectionError"))
    assert not set(AGENTE) & set(env)
    assert "nao herdados" in capsys.readouterr().err


def test_sessao_longjob_so_run_le_a_chave(monkeypatch):
    chamado = []
    monkeypatch.setenv("PF_SESSAO", FILHA)
    with patch.object(sessao_mod, "_msgmem", side_effect=lambda: chamado.append(1) or (None, "x")), \
         patch.object(sessao_mod.os, "execve"):
        sessao_mod.ato_longjob(["list"])
    assert chamado == []
