"""Card #3949: `infra cache modelos` lê revisão e digest dos pesos no cache do Hugging Face.

O cache é de mentira, em tmp (INFRA_HF_CACHE), no formato do hub: models--org--nome/refs/main,
snapshots/<rev>/ com o .safetensors apontando para blobs/<sha256>. Nada aqui toca o host.
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")
REV = "a" * 40

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None,
                                reason="sem bash ou jq no PATH — bin/infra cache precisa dos dois")


def _modelo(hub, nome, rev=REV, pesos=None, link=True):
    pesos = pesos or {"model.safetensors": b"pesos"}
    d = hub / ("models--" + nome.replace("/", "--"))
    (d / "refs").mkdir(parents=True)
    if rev:
        (d / "refs" / "main").write_text(rev + "\n")
    snap = d / "snapshots" / (rev or "b" * 40)
    snap.mkdir(parents=True)
    (d / "blobs").mkdir()
    (snap / "config.json").write_text("{}")
    digests = {}
    for arq, conteudo in pesos.items():
        sha = hashlib.sha256(conteudo).hexdigest()
        digests[arq] = sha
        if link:
            (d / "blobs" / sha).write_bytes(conteudo)
            (snap / arq).symlink_to(Path("../../blobs") / sha)
        else:
            (snap / arq).write_bytes(conteudo)
    return digests


def _rodar(raiz, *args):
    env = {**os.environ, "INFRA_HF_CACHE": str(raiz)}
    return subprocess.run([BASH, str(INFRA), "cache", "modelos", *args], capture_output=True,
                          text=True, env=env, timeout=30)


def test_le_revisao_e_digest_de_cada_modelo(tmp_path):
    hub = tmp_path / "hub"
    q = _modelo(hub, "Qwen/Qwen3-Embedding-0.6B")
    n = _modelo(hub, "nvidia/Nemotron-3-Embed-1B-BF16",
                pesos={"model-00001.safetensors": b"um", "model-00002.safetensors": b"dois"})
    r = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    linhas = r.stdout.splitlines()
    assert linhas[0].startswith(f"Qwen/Qwen3-Embedding-0.6B | {REV} | model.safetensors={q['model.safetensors']} | ")
    assert linhas[1].startswith(
        f"nvidia/Nemotron-3-Embed-1B-BF16 | {REV} | "
        f"model-00001.safetensors={n['model-00001.safetensors']},"
        f"model-00002.safetensors={n['model-00002.safetensors']} | ")


def test_json_traz_modelo_revisao_pesos_e_bytes(tmp_path):
    d = _modelo(tmp_path / "hub", "perplexity-ai/pplx-embed-v1-0.6b")
    r = _rodar(tmp_path, "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [{
        "modelo": "perplexity-ai/pplx-embed-v1-0.6b", "revisao": REV,
        "pesos": [{"arquivo": "model.safetensors", "digest": d["model.safetensors"]}], "bytes": 5}]


def test_arquivo_que_nao_e_link_sai_pelo_sha256(tmp_path):
    d = _modelo(tmp_path / "hub", "org/copiado", link=False)
    r = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    assert f"model.safetensors={d['model.safetensors']}" in r.stdout


def test_raiz_sem_hub_le_a_propria_raiz(tmp_path):
    _modelo(tmp_path, "org/direto")
    r = _rodar(tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("org/direto | ")


def test_modelo_sem_refs_main_diz_sem_revisao_e_sai_1(tmp_path):
    _modelo(tmp_path / "hub", "org/sem-ref", rev="")
    r = _rodar(tmp_path)
    assert r.returncode == 1
    assert "org/sem-ref | sem revisao | sem pesos" in r.stdout


def test_cache_que_nao_existe_sai_3_sem_inventar(tmp_path):
    r = _rodar(tmp_path / "nao-existe")
    assert r.returncode == 3 and r.stdout == ""
    assert "nao lido" in r.stderr


def test_cache_vazio_sai_1(tmp_path):
    (tmp_path / "hub").mkdir()
    r = _rodar(tmp_path)
    assert r.returncode == 1 and "nenhum modelo" in r.stderr


def test_argumento_desconhecido_sai_2(tmp_path):
    r = _rodar(tmp_path, "--apagar")
    assert r.returncode == 2 and "uso: infra cache modelos" in r.stderr


def test_nao_muda_nada_no_cache(tmp_path):
    hub = tmp_path / "hub"
    _modelo(hub, "org/intocado")
    antes = sorted((p.relative_to(tmp_path), p.is_symlink()) for p in tmp_path.rglob("*"))
    _rodar(tmp_path)
    _rodar(tmp_path, "--json")
    assert sorted((p.relative_to(tmp_path), p.is_symlink()) for p in tmp_path.rglob("*")) == antes
