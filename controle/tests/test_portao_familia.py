"""arq:0116 §4-§7 no verbo `teste`: lista de portão por subárvore, portão do repositório
inteiro e artefato pinado materializado na árvore medida.

Tudo em fixture: árvore sob uma raiz de release de tmp, registro de venvs e de terceiros
de tmp, cache de terceiros semeado à mão. Nenhum caso lê estado do mundo.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTE = REPO_ROOT / "bin" / "teste"


def _python() -> str:
    casa = str(Path.home())
    for c in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if c and os.path.isabs(c) and os.access(c, os.X_OK) and not c.startswith(casa):
            return c
    pytest.skip("nenhum python de sistema fora do HOME")


def _git(*args, cwd):
    # identidade explicita: o runner do CI nao tem user.name/email global e o `commit` saia 128
    ident = ["-c", "user.name=Teste", "-c", "user.email=teste@platafirma.org"]
    subprocess.run(["git", *ident, *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def _run(env, *args):
    # PYTEST_ fora: rodando sob o xdist do portão, PYTEST_XDIST_WORKER do trabalhador vazava
    # para o pytest da fixture e a rodada em série parecia paralela (#3335)
    e = {k: v for k, v in os.environ.items() if not k.startswith(("PF_", "PLATAFIRMA_", "PYTEST_"))}
    e.update(env)
    return subprocess.run([str(TESTE), *args], env=e, capture_output=True, text=True, timeout=240)


def _arvore(tmp_path, suites: dict[str, dict[str, str]], lista: dict[str, str | None],
            terceiro: bytes | None = None):
    """suites: {sub: {arquivo: conteudo}}; lista: {sub: texto da VERDES | None (ausente)}."""
    if not shutil.which("uv"):
        pytest.skip("uv ausente")
    raiz = tmp_path / "release"
    arv = raiz / "demo" / "rev1"
    arv.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=arv)
    stacks = {}
    for sub, arquivos in suites.items():
        (arv / sub).mkdir(parents=True)
        (arv / sub / "lock.txt").write_text("# fixture: venv vazio\n")
        for nome, texto in arquivos.items():
            (arv / sub / nome).write_text(texto)
        if lista.get(sub) is not None:
            (arv / sub / "VERDES").write_text(lista[sub])
        stacks[f"k-{sub}"] = {"familia": "demo", "lock": f"{sub}/lock.txt", "teste": sub}
    stacks["sem-suite"] = {"familia": "demo", "lock": f"{next(iter(suites))}/lock.txt"}
    _git("add", "-A", cwd=arv)
    _git("commit", "-q", "-m", "semente", cwd=arv)
    vjson = tmp_path / "venvs.json"
    vjson.write_text(json.dumps({"repositorios": {"demo": {"esteira": "codigo", "stack": "k-a"}},
                                 **stacks}))
    tjson = tmp_path / "terceiros.json"
    tjson.write_text("{}")
    if terceiro is not None:
        pino = hashlib.sha256(terceiro).hexdigest()
        cache = raiz / "terceiros" / "sha256"
        cache.mkdir(parents=True)
        (cache / pino).write_bytes(terceiro)
        tjson.write_text(json.dumps({"tok": {"familia": "demo", "destino": "terceiros/tok.json",
                                             "sha256": pino}}))
    env = {
        "PF_RELEASE_RAIZ": str(raiz),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PLATAFIRMA_VENVS": str(vjson),
        "PLATAFIRMA_TERCEIROS": str(tjson),
        "PLATAFIRMA_PYTHON": _python(),
    }
    return env, arv


VERDE = "def test_v(): assert True\n"
VERMELHO = "def test_f(): assert False\n"


def test_portao_do_repositorio_roda_toda_chave_com_subarvore(tmp_path):
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}, "b": {"test_b.py": VERDE}},
                       {"a": "test_a.py\n", "b": "test_b.py\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "portao demo: VERDE — k-a k-b" in r.stdout
    assert "sem-suite" not in r.stdout


def test_uma_chave_vermelha_barra_o_repositorio(tmp_path):
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}, "b": {"test_b.py": VERMELHO}},
                       {"a": "test_a.py\n", "b": "test_b.py\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "portao demo: VERMELHO — k-b" in r.stdout


def test_lista_ausente_e_suite_nao_medida(tmp_path):
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}, "b": {"test_b.py": VERDE}},
                       {"a": "test_a.py\n", "b": None})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 5, r.stdout + r.stderr
    assert "sem lista de portão em b/" in r.stdout
    assert "NAO MEDIDO — k-b" in r.stdout


def test_lista_vazia_vale_e_nao_roda_a_suite_inteira(tmp_path):
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERMELHO}}, {"a": "# nada no portão\n"})
    r = _run(env, "rodar", "k-a", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "lista de portão vazia" in r.stdout


def test_lista_com_arquivo_sumido_nao_mede(tmp_path):
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}}, {"a": "test_a.py\ntest_x.py\n"})
    r = _run(env, "rodar", "k-a", "--portao", "--arvore", str(arv))
    assert r.returncode == 5, r.stdout + r.stderr
    assert "test_x.py" in r.stdout


def test_artefato_pinado_entra_na_arvore_medida(tmp_path):
    conteudo = b'{"vocab": 3}'
    le = ("from pathlib import Path\n"
          "def test_tok():\n"
          "    p = Path(__file__).resolve().parents[1] / 'terceiros' / 'tok.json'\n"
          "    assert p.read_bytes() == b'{\"vocab\": 3}'\n")
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": le}}, {"a": "test_a.py\n"}, terceiro=conteudo)
    r = _run(env, "rodar", "k-a", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (arv / "terceiros" / "tok.json").read_bytes() == conteudo
    assert "terceiro:  tok" in r.stderr


def test_so_memo_nao_roda_e_devolve_6_ate_haver_veredito(tmp_path):
    """O gate lê o repositório inteiro pelo memo (PF_TESTE_SO_MEMO) antes de medir e
    enquanto o job mede: sem veredito, 6 e nada roda; depois da medição, o veredito."""
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}, "b": {"test_b.py": VERMELHO}},
                       {"a": "test_a.py\n", "b": "test_b.py\n"})
    so_memo = dict(env, PF_TESTE_SO_MEMO="1")
    r = _run(so_memo, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 6, r.stdout + r.stderr
    assert "AINDA NAO MEDIDO" in r.stdout
    assert not (tmp_path / "instancia" / "var" / "log" / "teste").exists()
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 1, r.stdout + r.stderr
    r = _run(so_memo, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "veredito reaproveitado" in r.stdout + r.stderr


def _marca(arquivo: Path, rotulo: str, dormir: float = 0.0) -> str:
    """Caso que grava rótulo, trabalhador do xdist e instante de início e fim."""
    return ("import os, time\n"
            f"def test_{rotulo}():\n"
            "    t0 = time.time()\n"
            f"    time.sleep({dormir})\n"
            f"    with open({str(arquivo)!r}, 'a') as f:\n"
            f"        f.write('{rotulo} ' + os.environ.get('PYTEST_XDIST_WORKER', '-')"
            " + f' {t0} {time.time()}\\n')\n")


def _marcas(arquivo: Path) -> dict[str, tuple[str, float, float]]:
    out = {}
    for linha in arquivo.read_text().splitlines():
        rotulo, trab, t0, t1 = linha.split()
        out[rotulo] = (trab, float(t0), float(t1))
    return out


def test_chaves_do_portao_rodam_ao_mesmo_tempo(tmp_path):
    """Incidente #3335: as chaves do repositório rodam juntas, não uma depois da outra;
    a saída de cada uma sai inteira, na ordem do registro."""
    marcas = tmp_path / "marcas.txt"
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": _marca(marcas, "a", 3)},
                                  "b": {"test_b.py": _marca(marcas, "b", 3)}},
                       {"a": "test_a.py\n", "b": "test_b.py\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    m = _marcas(marcas)
    assert m["b"][1] < m["a"][2] and m["a"][1] < m["b"][2], m
    assert r.stdout.index("suite VERDE: k-a") < r.stdout.index("suite VERDE: k-b"), r.stdout


def test_lista_do_portao_roda_com_xdist_por_arquivo(tmp_path):
    """Incidente #3335: a lista do portão roda em trabalhadores do pytest-xdist, nunca
    mais que os arquivos da lista; PF_TESTE_PARALELO=1 roda em série."""
    marcas = tmp_path / "marcas.txt"
    env, arv = _arvore(tmp_path, {"a": {"test_a1.py": _marca(marcas, "a1"),
                                        "test_a2.py": _marca(marcas, "a2")}},
                       {"a": "test_a1.py\ntest_a2.py\n"})
    r = _run(dict(env, PF_TESTE_PARALELO="8"), "rodar", "k-a", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2 passed" in r.stdout, r.stdout
    assert {t for t, _, _ in _marcas(marcas).values()} <= {"gw0", "gw1"}, _marcas(marcas)
    marcas.unlink()
    r = _run(dict(env, PF_TESTE_PARALELO="1", PF_TESTE_SEM_MEMO="1"),
             "rodar", "k-a", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert {t for t, _, _ in _marcas(marcas).values()} == {"-"}, _marcas(marcas)


def test_artefato_fora_do_cache_e_sem_url_e_dependencia_ausente(tmp_path):
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}}, {"a": "test_a.py\n"})
    Path(env["PLATAFIRMA_TERCEIROS"]).write_text(json.dumps(
        {"tok": {"familia": "demo", "destino": "terceiros/tok.json", "sha256": "0" * 64}}))
    r = _run(env, "rodar", "k-a", "--portao", "--arvore", str(arv))
    assert r.returncode == 3, r.stdout + r.stderr
    assert "fora do cache" in r.stderr
