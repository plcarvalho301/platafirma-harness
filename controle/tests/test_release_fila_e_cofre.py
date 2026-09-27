"""Incidente de 27/09 (14:17): promocao do harness reiniciou a porta no meio da promocao do
conhecimento, e o `release conferir servico` acusava segredo ausente que nunca faltou.

Dois contratos:
  1. fila de promocao — com o lock da instancia tomado, `release promover` ESPERA e, passado
     PF_PROMOCAO_ESPERA, sai 3 dizendo que ha promocao em andamento, sem tocar nada; --ensaio
     nao entra na fila.
  2. conferir servico renderiza o compose com o cofre da stack e nunca imprime valor de segredo.
"""
import fcntl
import importlib.machinery
import importlib.util
import os
import subprocess

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RELEASE = os.path.join(RAIZ, "bin", "release")
CONFERIR = os.path.join(RAIZ, "bin", "_release", "conferir", "conferir.py")


def _ambiente(tmp_path):
    inst = tmp_path / "instancia"
    (inst / "var" / "release").mkdir(parents=True)
    rel = tmp_path / "release"
    rel.mkdir()
    env = dict(os.environ)
    env.update({
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PF_RELEASE_RAIZ": str(rel),
        "PLATAFIRMA_RELEASE": str(rel / "current"),
        "PF_PROMOCAO_ESPERA": "1",
        "PF_CADEIRA": "teste",
    })
    return env, inst / "var" / "release" / ".promocao.lock"


def test_promover_espera_e_sai_3_com_lock_tomado(tmp_path):
    env, lock = _ambiente(tmp_path)
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        p = subprocess.run([RELEASE, "promover", "familia-que-nao-existe", "abc"],
                           capture_output=True, text=True, env=env, timeout=60)
    assert p.returncode == 3, p.stderr
    assert "aguardando a vez" in p.stderr
    assert "promoção em andamento" in p.stderr
    assert "nada tocado" in p.stderr


def test_reverter_tambem_entra_na_fila(tmp_path):
    env, lock = _ambiente(tmp_path)
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        p = subprocess.run([RELEASE, "reverter", "familia-que-nao-existe"],
                           capture_output=True, text=True, env=env, timeout=60)
    assert p.returncode == 3, p.stderr
    assert "aguardando a vez" in p.stderr


def test_ensaio_nao_entra_na_fila(tmp_path):
    env, lock = _ambiente(tmp_path)
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        p = subprocess.run([RELEASE, "promover", "familia-que-nao-existe", "abc", "--ensaio"],
                           capture_output=True, text=True, env=env, timeout=60)
    assert "aguardando a vez" not in p.stderr


def test_reentrada_do_reverter_automatico_nao_espera_por_si(tmp_path):
    # o promover que reverte sozinho chama `release reverter` como filho, ja com a vez
    env, lock = _ambiente(tmp_path)
    env["PF_PROMOCAO_NA_FILA"] = "123"
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        p = subprocess.run([RELEASE, "reverter", "familia-que-nao-existe"],
                           capture_output=True, text=True, env=env, timeout=60)
    assert "aguardando a vez" not in p.stderr


def _conferir(monkeypatch, tmp_path):
    monkeypatch.setenv("PF_AI_DIR", str(tmp_path))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path / "inst"))
    loader = importlib.machinery.SourceFileLoader("conferir_cofre", CONFERIR)
    spec = importlib.util.spec_from_loader("conferir_cofre", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_stack_do_container_casa_pelo_caminho_relativo(monkeypatch, tmp_path):
    c = _conferir(monkeypatch, tmp_path)
    c._TOPO = [
        {"slug": "rag", "compose": ["/opt/platafirma/current/conhecimento/rag/docker-compose.yml",
                                    "/opt/platafirma/current/conhecimento/rag/docker-compose.gpu.yml"]},
        {"slug": "acervo-api", "compose": "/opt/platafirma/current/conhecimento/acervo-api/docker-compose.yml"},
    ]
    cont = {"config_files": "/opt/platafirma/platafirma-conhecimento/" + "a" * 40 + "/rag/docker-compose.yml"}
    assert c.stack_do_container(cont) == "rag"
    cont = {"config_files": "/outro/lugar/docker-compose.yml"}
    assert c.stack_do_container(cont) is None


def test_segredos_da_stack_segue_a_regra_do_ajudante(monkeypatch, tmp_path):
    c = _conferir(monkeypatch, tmp_path)
    pasta = tmp_path / "inst" / "segredos" / "rag"
    pasta.mkdir(parents=True)
    (pasta / "POSTGRES_PASSWORD").write_text("s3gredo-longo\n")
    (pasta / "multi").write_text("a\nb\n")
    (pasta / "nome-invalido").write_text("x")
    assert c.segredos_da_stack("rag") == {"POSTGRES_PASSWORD": "s3gredo-longo"}


def test_conferir_servico_nunca_imprime_segredo(monkeypatch, tmp_path, capsys):
    c = _conferir(monkeypatch, tmp_path)
    c._SEGREDOS_VISTOS.add("s3gredo-longo")
    cont = {"nome": "x", "projeto": "p", "servico": "api", "working_dir": str(tmp_path),
            "config_files": "", "env": {"DSN": "postgres://u:outro-antigo@h/db"}, "started_at": None}
    monkeypatch.setattr(c, "containers", lambda alvo: iter([cont]))
    monkeypatch.setattr(c, "git_estado", lambda wd: None)
    monkeypatch.setattr(c, "env_declarado", lambda cc: ({"DSN": "postgres://u:s3gredo-longo@h/db"}, None))
    c.conferir_servico("x")
    saida = capsys.readouterr().out
    assert "s3gredo-longo" not in saida
    assert "outro-antigo" not in saida
    assert "DIFERE" in saida
