# componente: componente:verbo-teste
"""Degrau e quarentena nas listas de portão do verbo `teste` (arq:0129, card #3731)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from test_portao_familia import _arvore, _marca, _run
from test_portao_raio import _commita, _rodou, _tres

DEGRAUS = ("test_a1.py\n"
           "test_a2.py | degrau: imagem\n"
           "test_a3.py | degrau: rodada\n")


def _roda(env, arv, marcas: Path, *extra: str):
    """Uma rodada do portao do repositorio, sem memo, e o que ela rodou de fato."""
    if marcas.exists():
        marcas.unlink()
    r = _run(dict(env, PF_TESTE_SEM_MEMO="1"), "rodar", "demo", "--portao", "--arvore", str(arv), *extra)
    return r, _rodou(marcas)


def test_sem_campo_de_degrau_a_linha_e_pequena_e_o_padrao_roda_so_o_pequeno(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, DEGRAUS)
    r, rodou = _roda(env, arv, marcas)
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a1"}
    assert "degrau: pequeno · 1 linha(s) dele · fora: pequeno 0, imagem 1, rodada 1, demanda 0, quarentena 0" in r.stdout, r.stdout


def test_degrau_seleciona_so_as_linhas_dele(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, DEGRAUS)
    r, rodou = _roda(env, arv, marcas, "--degrau", "imagem")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a2"}
    r, rodou = _roda(env, arv, marcas, "--degrau", "rodada")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a3"}
    r, rodou = _roda(env, arv, marcas, "--degrau", "pequeno")
    assert rodou == {"a1"}
    r, rodou = _roda(env, arv, marcas, "--degrau", "todos")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a1", "a2", "a3"}


def test_quarentena_nao_roda_no_portao_e_roda_na_rodada(tmp_path):
    """arq:0129 D6: quarentena não é degrau, é estado com prazo; o campo `degrau:` continua escrito."""
    marcas = tmp_path / "marcas.txt"
    lista = ("test_a1.py\n"
             "test_a2.py | quarentena #77\n"
             "test_a3.py | degrau: imagem | quarentena #78\n")
    env, arv, _ = _tres(tmp_path, marcas, lista)
    r, rodou = _roda(env, arv, marcas)
    assert rodou == {"a1"}, r.stdout
    assert "quarentena 2" in r.stdout, r.stdout
    r, rodou = _roda(env, arv, marcas, "--degrau", "imagem")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == set()
    assert "nenhuma linha do degrau imagem" in r.stdout, r.stdout
    r, rodou = _roda(env, arv, marcas, "--degrau", "rodada")
    assert rodou == {"a2", "a3"}


def test_campos_em_qualquer_ordem_e_o_raio_continua_sendo_so_os_globs(tmp_path):
    """O raio da arq:0128 lê o campo de globs; `degrau:` e `regressivo` não são glob."""
    marcas = tmp_path / "marcas.txt"
    lista = ("test_a1.py | degrau: imagem | a/src/um/**\n"
             "test_a2.py | a/src/dois/** | degrau: imagem\n"
             "test_a3.py | regressivo #9 | degrau: imagem\n")
    env, arv, base = _tres(tmp_path, marcas, lista)
    _commita(arv, {"a/src/dois/x.txt": "x\n"})
    r, rodou = _roda(env, arv, marcas, "--degrau", "imagem", "--base", base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a2", "a3"}, r.stdout
    assert "seleção: 2 de 3 arquivos (pulados: test_a1.py)" in r.stdout, r.stdout


def test_campo_desconhecido_ou_degrau_invalido_nao_mede(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, "test_a1.py | foo: bar\ntest_a2.py | degrau: lua\ntest_a3.py\n")
    r, rodou = _roda(env, arv, marcas)
    assert r.returncode == 5, r.stdout + r.stderr
    assert "campo desconhecido 'foo:'" in r.stdout and "degrau: com valor 'lua'" in r.stdout, r.stdout
    assert rodou == set()


def test_degrau_so_vale_com_portao_e_so_com_valor_conhecido(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, DEGRAUS)
    r = _run(env, "rodar", "demo", "--degrau", "imagem", "--arvore", str(arv))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--degrau só com --portao" in r.stdout + r.stderr
    r = _run(env, "rodar", "demo", "--portao", "--degrau", "lua", "--arvore", str(arv))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "use pequeno, imagem, rodada, demanda ou todos" in r.stdout + r.stderr


def test_demanda_nao_roda_no_portao_nem_na_rodada_so_quando_pedida(tmp_path):
    """Card #3735 (decisão do dono, 17/10/2026): a prova de tela não roda no portão nem em 'todos'."""
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, "test_a1.py\ntest_a2.py | degrau: rodada\ntest_a3.py | degrau: demanda\n")
    r, rodou = _roda(env, arv, marcas)
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a1"}
    assert "demanda 1" in r.stdout, r.stdout
    r, rodou = _roda(env, arv, marcas, "--degrau", "todos")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a1", "a2"}
    r, rodou = _roda(env, arv, marcas, "--degrau", "rodada")
    assert rodou == {"a2"}
    r, rodou = _roda(env, arv, marcas, "--degrau", "demanda")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a3"}


def test_veredito_do_pequeno_nao_responde_pela_lista_inteira(tmp_path):
    """O pre-push e o gate leem o veredito da árvore: pequeno verde não pode valer pela lista inteira."""
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, DEGRAUS)
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    so_memo = dict(env, PF_TESTE_SO_MEMO="1")
    r = _run(so_memo, "rodar", "demo", "--portao", "--arvore", str(arv))          # o mesmo degrau acha
    assert r.returncode == 0, r.stdout + r.stderr
    assert "veredito reaproveitado" in r.stdout + r.stderr
    r = _run(so_memo, "rodar", "demo", "--portao", "--degrau", "todos", "--arvore", str(arv))
    assert r.returncode == 6, r.stdout + r.stderr                                  # a lista inteira, não
    assert "AINDA NAO MEDIDO" in r.stdout
    r = _run(so_memo, "rodar", "demo", "--portao", "--degrau", "imagem", "--arvore", str(arv))
    assert r.returncode == 6, r.stdout + r.stderr


def test_degrau_atravessa_as_chaves_do_repositorio(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv = _arvore(tmp_path, {"a": {"test_a.py": _marca(marcas, "a")}, "b": {"test_b.py": _marca(marcas, "b")}},
                       {"a": "test_a.py | degrau: imagem\n", "b": "test_b.py\n"})
    r, rodou = _roda(env, arv, marcas)
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"b"}
    assert "nenhuma linha do degrau pequeno" in r.stdout, r.stdout      # a chave a não tem linha pequena
    r, rodou = _roda(env, arv, marcas, "--degrau", "imagem")
    assert r.returncode == 0, r.stdout + r.stderr
    assert rodou == {"a"}


def test_rodada_diaria_roda_os_tres_degraus(tmp_path):
    """arq:0129 D5: `--origin-main` sem `--degrau` mede a lista inteira, quarentena inclusive."""
    marcas = tmp_path / "marcas.txt"
    lista = DEGRAUS + ""
    env, arv, _ = _tres(tmp_path, marcas, lista + "test_q.py | quarentena #5\n")
    _commita(arv, {"a/test_q.py": _marca(marcas, "q")})
    banc = tmp_path / "bancada"
    banc.mkdir()
    subprocess.run(["git", "clone", "-q", str(arv), str(banc / "demo")], check=True, capture_output=True)
    r = _run(dict(env, PLATAFIRMA_BANCADA=str(banc), PF_TESTE_SEM_MEMO="1"),
             "rodar", "demo", "--portao", "--origin-main")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _rodou(marcas) == {"a1", "a2", "a3", "q"}, r.stdout
