"""Seleção por raio de ataque, regressivo, preparo e --origin-main no verbo `teste` (arq:0128)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from test_portao_familia import (
    REPO_ROOT,
    VERDE,
    VERMELHO,
    _arvore,
    _commita,
    _marca,
    _marcas,
    _rev,
    _run,
)


def _tres(tmp_path, marcas: Path, lista: str):
    env, arv = _arvore(tmp_path, {"a": {"test_a1.py": _marca(marcas, "a1"),
                                        "test_a2.py": _marca(marcas, "a2"),
                                        "test_a3.py": _marca(marcas, "a3")}},
                       {"a": lista})
    return env, arv, _rev(arv)


RAIOS = "test_a1.py | a/src/um/**\ntest_a2.py | a/src/dois/**\ntest_a3.py\n"


def _rodou(marcas: Path) -> set[str]:
    return set(_marcas(marcas)) if marcas.exists() else set()


def test_selecao_roda_so_o_que_o_diff_alcanca_e_a_linha_sem_raio_fica_fora(tmp_path):
    """arq:0128: linha sem raio não é alcançada por diff nenhum, nem por código fora das outras chaves."""
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/src/um/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 1 de 3 arquivos (pulados: test_a2.py test_a3.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a1"}


def test_lista_sem_nenhum_raio_roda_zero_com_diff_de_codigo(tmp_path):
    """O cenário da arq:0128: diff só num arquivo de código, nenhuma linha da lista com raio:
    seleção 0, sem raio total, e o portão passa sem rodar prova nenhuma."""
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, "test_a1.py\ntest_a2.py\ntest_a3.py\n")
    _commita(arv, {"a/src/um/tela.js": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 0 de 3 arquivos" in r.stdout, r.stdout
    assert "raio total" not in r.stdout, r.stdout
    assert _rodou(marcas) == set()


def test_o_proprio_teste_mudado_roda_mesmo_com_raio_declarado(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/test_a2.py": _marca(marcas, "a2") + "# editado\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 1 de 3 arquivos (pulados: test_a1.py test_a3.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a2"}


def test_o_proprio_teste_sem_raio_mudado_roda(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, RAIOS)
    _commita(arv, {"a/test_a3.py": _marca(marcas, "a3") + "# editado\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 1 de 3 arquivos (pulados: test_a1.py test_a2.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a3"}


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


def test_sem_base_roda_a_lista_inteira_e_base_ilegivel_nao_mede(tmp_path):
    """arq:0128 §5: sem --base (bancada, rodada diária) a lista inteira; base que não se lê é
    falha de ambiente (sai 5), nunca lista inteira."""
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
    assert r.returncode == 5, r.stdout + r.stderr
    assert "NAO MEDIDO" in r.stdout and "ilegível" in r.stdout, r.stdout
    assert _rodou(marcas) == set()
    # a mesma regra na chave sozinha
    r = _run(dict(env, PF_TESTE_SEM_MEMO="1"), "rodar", "k-a", "--portao", "--arvore", str(arv),
             "--base", "f" * 40)
    assert r.returncode == 5, r.stdout + r.stderr
    assert "ilegível" in r.stdout, r.stdout
    assert _rodou(marcas) == set()


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
            globs, _, _ = globs.partition("|")   # ignora sufixo opcional `| degrau: ...`
            if globs.split()[:1] in (["regressivo"], ["preparo"]):   # #3535, arq:0128: marca, nao glob
                continue
            mortos += [f"{lista.relative_to(REPO_ROOT)}: {g}" for g in globs.split()
                       if not any(casa(f, g) for f in arquivos)]
    assert not mortos, f"raio declarado que nao casa arquivo nenhum: {mortos}"


# --- regra do dono de 14/10/2026 (#3535): o raio de ataque e os regressivos, e mais nenhum ----

def test_regressivo_roda_em_toda_mudanca_e_o_resto_so_pelo_raio(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, "test_a1.py | a/src/um/**\ntest_a2.py | regressivo #9\n"
                                             "test_a3.py | a/src/tres/**\n")
    _commita(arv, {"a/src/tres/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 2 de 3 arquivos (pulados: test_a1.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a2", "a3"}


def test_mudanca_em_lib_alcanca_o_teste_do_verbo_que_a_usa(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, "test_a1.py | bin/verbo\ntest_a2.py | bin/outro\n"
                                             "test_a3.py | a/src/tres/**\n")
    base = _commita(arv, {"bin/verbo": '. "$AQUI/../lib/apoio.sh"\n', "bin/outro": "true\n",
                          "lib/apoio.sh": "x=1\n"})
    _commita(arv, {"lib/apoio.sh": "x=2\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "raio total" not in r.stdout, r.stdout
    assert _rodou(marcas) == {"a1"}


def test_linha_que_entra_na_lista_roda_sozinha(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres(tmp_path, marcas, "test_a1.py | a/src/um/**\n")
    _commita(arv, {"a/VERDES": "test_a1.py | a/src/um/**\ntest_a2.py | a/src/dois/**\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "raio total" not in r.stdout, r.stdout
    assert _rodou(marcas) == {"a2"}


def test_linha_sem_raio_nao_roda_por_documentacao_nem_por_codigo(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": _marca(marcas, "a")}, "b": {"test_b.py": VERDE}},
                       {"a": "test_a.py\n", "b": "test_b.py\n"})
    base = _rev(arv)
    _commita(arv, {"docs/x.md": "x\n", "b/src/y.txt": "y\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _rodou(marcas) == set()
    base = _rev(arv)
    _commita(arv, {"src/z.txt": "z\n"})   # código: arq:0128, linha sem raio continua fora
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _rodou(marcas) == set()


def _tres_com_preparo(tmp_path, marcas: Path):
    env, arv = _arvore(tmp_path, {"a": {"test_prep.py": _marca(marcas, "prep"),
                                        "test_a1.py": _marca(marcas, "a1"),
                                        "test_a2.py": _marca(marcas, "a2")}},
                       {"a": "test_prep.py | preparo\ntest_a1.py | a/src/um/**\ntest_a2.py | a/src/dois/**\n"})
    return env, arv, _rev(arv)


def test_preparo_roda_antes_quando_a_selecao_nao_e_vazia_e_nao_conta(tmp_path):
    """arq:0128 §6: a linha `| preparo` não entra na contagem nem é selecionada por si; roda
    quando alguma outra linha é selecionada."""
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres_com_preparo(tmp_path, marcas)
    _commita(arv, {"a/src/um/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 1 de 2 arquivos (pulados: test_a2.py)" in r.stdout, r.stdout
    assert _rodou(marcas) == {"prep", "a1"}


def test_preparo_nao_roda_com_selecao_vazia(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres_com_preparo(tmp_path, marcas)
    _commita(arv, {"a/src/tres/x.txt": "x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 0 de 2 arquivos" in r.stdout, r.stdout
    assert _rodou(marcas) == set()


def test_preparo_mudado_sozinho_nao_se_seleciona_por_si(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres_com_preparo(tmp_path, marcas)
    _commita(arv, {"a/test_prep.py": _marca(marcas, "prep") + "# editado\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "seleção: 0 de 2 arquivos" in r.stdout, r.stdout
    assert _rodou(marcas) == set()


def test_preparo_roda_na_lista_inteira_sem_base(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _tres_com_preparo(tmp_path, marcas)
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _rodou(marcas) == {"prep", "a1", "a2"}


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


# --- F4277 regra 1: o lock de uma stack alcança só aquela stack (carta 20261116T195115) ----

def _duas(tmp_path, marcas: Path):
    env, arv = _arvore(tmp_path, {"a": {"test_a1.py": _marca(marcas, "a1")},
                                  "b": {"test_b1.py": _marca(marcas, "b1")}},
                       {"a": "test_a1.py | a/src/**\n", "b": "test_b1.py | b/src/**\n"})
    return env, arv, _rev(arv)


def test_lock_na_pasta_de_uma_stack_e_raio_total_so_dela(tmp_path):
    """O rag/uv.lock rodava conversor e casa-site inteiras: agora só a dona roda a lista toda."""
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _duas(tmp_path, marcas)
    _commita(arv, {"a/uv.lock": "# x\n", "a/requirements-teste.txt": "# x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("raio total: a/") == 1, r.stdout
    assert "seleção: 0 de 1 arquivos" in r.stdout, r.stdout
    assert _rodou(marcas) == {"a1"}


def test_lock_na_raiz_segue_raio_total_de_toda_stack(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, base = _duas(tmp_path, marcas)
    _commita(arv, {"uv.lock": "# x\n"})
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("raio total: uv.lock") == 2, r.stdout
    assert _rodou(marcas) == {"a1", "b1"}


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
