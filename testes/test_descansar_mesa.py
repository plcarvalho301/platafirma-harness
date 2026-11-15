"""`descansar fita`: a mesa sai do mesmo `mesa ver` da abertura (debito #656).

O que se trava: o descanso nao le mais `mem:<cadeira>:*` direto no Valkey. O item vivo sai
como o `mesa ver` o serve (o feito ja saiu dele por `mesa fez`); a prosa de `mesa anota` sai
so com o cabecalho, marcada como anotacao sem ato, sem o corpo que dava como aberto o que
ja se fizera; o chapeu fora da persona sai marcado; mesa fora do ar sai dita, nunca vazia.
"""

from __future__ import annotations

import importlib.util
import os
import stat
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("descansar_mesa_bin", str(REPO_ROOT / "bin" / "descansar"))
spec = importlib.util.spec_from_loader("descansar_mesa_bin", loader)
assert spec and spec.loader
descansar = importlib.util.module_from_spec(spec)
loader.exec_module(descansar)

VER = """#1 [busca] lapidar a heuristica → card 4072   (plantado ha 28 min)
      corpo do item, que nao entra no descanso
#2 [agente] medir o loop → card 9999   (plantado ha 3 h)
  (executou? `mesa fez <n>` — leitura nao esvazia)

[contexto] anotação (expira em 40 h)
fazer o item 1 da lista
fazer o item 2 da lista

[recuperacao] anotação (expira em 2 h)
uma linha

"""


def _stub(tmp_path, ver_stdout, ver_exit=0, ver_stderr=""):
    mesa = tmp_path / "mesa"
    mesa.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "ver" ]; then\n'
        f"  cat <<'FIM'\n{ver_stdout}FIM\n"
        f"  printf '%s' '{ver_stderr}' >&2\n"
        f"  exit {ver_exit}\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8")
    mesa.chmod(mesa.stat().st_mode | stat.S_IEXEC)
    return str(tmp_path)


def _roda(monkeypatch, tmp_path, **kw):
    monkeypatch.setenv("PF_BIN", _stub(tmp_path, **kw))
    monkeypatch.setattr(descansar, "slugs_declarados",
                        lambda curto: ({"busca", "contexto", "orquestracao"}, None))
    return descansar.estado_memoria("ia")


def test_item_vivo_sai_como_o_mesa_ver_serve(monkeypatch, tmp_path):
    linhas, _ = _roda(monkeypatch, tmp_path, ver_stdout=VER)
    texto = "\n".join(linhas)
    assert "#1 [busca] lapidar a heuristica → card 4072" in texto
    assert "corpo do item" not in texto, "o descanso mostra o indice, nao o corpo"
    assert "2 item(ns) vivo(s)" in texto


def test_prosa_sai_sem_corpo_e_marcada_sem_ato(monkeypatch, tmp_path):
    linhas, orfaos = _roda(monkeypatch, tmp_path, ver_stdout=VER)
    texto = "\n".join(linhas)
    assert "fazer o item 1" not in texto, "o corpo da prosa dava o feito como aberto"
    assert "[contexto] anotação sem ato, 2 linha(s), expira em 40 h" in texto
    assert "não é item aberto" in texto
    assert orfaos == ["recuperacao"]


def test_chapeu_fora_da_persona_sai_marcado(monkeypatch, tmp_path):
    linhas, _ = _roda(monkeypatch, tmp_path, ver_stdout=VER)
    agente = next(l for l in linhas if "[agente]" in l)
    busca = next(l for l in linhas if "[busca]" in l)
    assert "ÓRFÃO" in agente and "ÓRFÃO" not in busca
    recup = next(l for l in linhas if "[recuperacao]" in l)
    assert "ÓRFÃO" in recup


def test_mesa_vazia_e_mesa_fora_do_ar_nao_se_confundem(monkeypatch, tmp_path):
    linhas, _ = _roda(monkeypatch, tmp_path, ver_stdout="mesa vazia\n")
    assert "  mesa vazia" in linhas
    fora = tmp_path / "fora"
    fora.mkdir()
    linhas, _ = _roda(monkeypatch, fora, ver_stdout="mesa vazia\n",
                      ver_stderr="(itens de mesa indisponiveis: sessao-db nao respondeu)")
    texto = "\n".join(linhas)
    assert "indisponiveis" in texto, "o substrato mudo se declara ao lado da prosa vazia"


def test_o_descanso_nao_le_mais_o_valkey_da_mesa():
    texto = (REPO_ROOT / "bin" / "descansar").read_text(encoding="utf-8")
    corpo = texto[texto.index("def estado_memoria"):texto.index("def _bin")]
    assert "rc.keys" not in corpo and '"mesa"), "ver"' in corpo
