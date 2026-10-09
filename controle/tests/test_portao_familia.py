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


# --- card #3370: o portao roda so o que o diff da base alcanca -------------------------

def _commita(arv: Path, arquivos: dict[str, str]) -> str:
    for rel, texto in arquivos.items():
        p = arv / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto)
    _git("add", "-A", cwd=arv)
    _git("commit", "-q", "-m", "mudanca", cwd=arv)
    return _rev(arv)

def _rev(arv: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(arv), check=True,
                          capture_output=True, text=True).stdout.strip()

def _tres(tmp_path, marcas: Path, lista: str):
    env, arv = _arvore(tmp_path, {"a": {"test_a1.py": _marca(marcas, "a1"),
                                        "test_a2.py": _marca(marcas, "a2"),
                                        "test_a3.py": _marca(marcas, "a3")}},
                       {"a": lista})
    return env, arv, _rev(arv)

RAIOS = "test_a1.py | a/src/um/**\ntest_a2.py | a/src/dois/**\ntest_a3.py\n"

def _rodou(marcas: Path) -> set[str]:
    return set(_marcas(marcas)) if marcas.exists() else set()

def test_selecao_roda_o_que_o_diff_alcanca_e_a_linha_sem_raio(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/src/um/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 2 de 3 arquivos (pulados: test_a2.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a1", "a3"}

def test_o_proprio_teste_mudado_roda_mesmo_com_raio_declarado(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/test_a2.py": _marca(marcas, "a2") + "# editado\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 2 de 3 arquivos (pulados: test_a1.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a2", "a3"}

def test_raio_total_roda_a_lista_inteira_e_diz_o_arquivo(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"lib/venv.sh": "# x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("raio total: lib/venv.sh") == 1, r.stdout
    assert "seleção:" not in r.stdout
    assert _rodou(marcas) == {"a1", "a2", "a3"}

def test_mudar_a_lista_ou_conftest_e_raio_total(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/conftest.py": "# x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert "raio total: a/conftest.py" in r.stdout, r.stdout + r.stderr
    assert _rodou(marcas) == {"a1", "a2", "a3"}

def test_sem_base_ou_base_ilegivel_roda_a_lista_inteira(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/src/um/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção:" not in r.stdout
    assert _rodou(marcas) == {"a1", "a2", "a3"}
    marcas.unlink()
    r = _run(dict(env, PF_TESTE_SEM_MEMO="1"), "rodar", "demo", "--portao", "--arvore", str(arv),
             "--base", "f" * 40)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ilegível" in r.stderr, r.stderr
    assert _rodou(marcas) == {"a1", "a2", "a3"}

def test_selecao_vazia_nao_roda_nada_e_passa(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, "test_a1.py | a/src/um/**\ntest_a2.py | a/src/dois/**\n")
    _commita(arv, {"docs/x.md": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 0 de 2 arquivos" in r.stdout, r.stdout
    assert "nenhum arquivo da lista alcançado" in r.stdout, r.stdout
    assert _rodou(marcas) == set()

def test_veredito_parcial_nao_responde_pela_rodada_inteira(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/src/um/x.txt": "x\n"})
    so_memo = dict(env, PF_TESTE_SO_MEMO="1")
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    # a mesma selecao acha o veredito parcial; a rodada inteira, nao
    r = _run(so_memo, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "veredito reaproveitado" in r.stdout + r.stderr
    r = _run(so_memo, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 6, r.stdout + r.stderr
    assert "AINDA NAO MEDIDO" in r.stdout

def test_raio_declarado_nas_listas_reais_casa_arquivo_que_existe():
    """Glob que nao casa nada e raio morto: o teste nunca roda pela mudanca que devia alcanca-lo.
    Le so a arvore da rev: as quatro listas de portao e os arquivos do checkout."""
    import fnmatch
    listas = [REPO_ROOT / p for p in ("controle/tests/VERDES", "testes/VERDES",
                                      "recuperacao/VERDES", "ops-server/VERDES")]
    arquivos = []
    for raiz, dirs, nomes in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d != ".git"]
        arquivos += [Path(raiz, n).relative_to(REPO_ROOT).as_posix() for n in nomes]
    def casa(f: str, g: str) -> bool:
        return fnmatch.fnmatchcase(f, g) or (g.startswith("**/") and fnmatch.fnmatchcase(f, g[3:]))
    mortos = []
    for lista in listas:
        for linha in lista.read_text().splitlines():
            if not linha.strip() or linha.lstrip().startswith("#"):
                continue
            _, _, globs = linha.partition("|")
            mortos += [f"{lista.relative_to(REPO_ROOT)}: {g}" for g in globs.split()
                       if not any(casa(f, g) for f in arquivos)]
    assert not mortos, f"raio declarado que nao casa arquivo nenhum: {mortos}"

def test_origin_main_mede_a_main_do_clone_base_e_a_arvore_some(tmp_path):
    """A rodada diaria do bot (#3370): a lista inteira sobre origin/main do clone base da
    bancada, numa arvore descartavel; main vermelha sai 1; a arvore nao fica."""
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": VERDE}}, {"a": "test_a.py\n"})
    banc = tmp_path / "bancada"
    banc.mkdir()
    subprocess.run(["git", "clone", "-q", str(arv), str(banc / "demo")], check=True,
                   capture_output=True)
    com_banc = dict(env, PLATAFIRMA_BANCADA=str(banc))
    r = _run(com_banc, "rodar", "demo", "--portao", "--origin-main")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "origem:    origin/main de demo" in r.stderr, r.stderr
    assert "portao demo: VERDE" in r.stdout, r.stdout
    arvores = tmp_path / "instancia" / "var" / "pre-push" / "arvores"
    assert not list(arvores.glob("diaria.*"))
    _commita(arv, {"a/test_a.py": VERMELHO})   # a main andou e ficou vermelha
    r = _run(com_banc, "rodar", "demo", "--portao", "--origin-main")
    assert r.returncode == 1, r.stdout + r.stderr
    assert not list(arvores.glob("diaria.*"))
    r = _run(com_banc, "rodar", "demo", "--origin-main")   # sem --portao
    assert r.returncode == 2, r.stdout + r.stderr

def test_veredito_da_rodada_inteira_verde_responde_pela_parcial(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/src/um/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    marcas.unlink()
    r = _run(dict(env, PF_TESTE_SO_MEMO="1"), "rodar", "demo", "--portao", "--arvore", str(arv),
             "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rodada inteira da mesma arvore" in r.stdout + r.stderr
    assert _rodou(marcas) == set()
