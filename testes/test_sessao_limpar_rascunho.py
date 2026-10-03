"""`sessao limpar --rascunho [<subpasta>] [--apply]` (balde #2856, linha 152; card #3162).

Apaga, e so, o rascunho da propria fita: <instancia>/var/tmp/<PF_ORDEM_ID da chamada>/<subpasta>.
Tudo em tmp_path: a instancia e falsa, nada real do host e tocado, msg-mem nao entra.

Verifica:
1. sem --apply mostra o plano (arquivos e bytes) e nao apaga nada;
2. com --apply apaga a subpasta nomeada e diz o que apagou; irma e pasta de outra ordem ficam;
3. raiz inteira sem subpasta nomeada (vazia, '.', 'x/..') recusa com exit 4;
4. `..`, caminho absoluto e link simbolico que saem da raiz recusam com exit 4 e a causa, nada apagado;
5. link simbolico DENTRO do rascunho apontando para fora: apaga o link, nunca o alvo;
6. sem PF_ORDEM_ID (ou '-', ou com '/') recusa com exit 4; subpasta inexistente sai 1;
7. --apply sem --rascunho e uso errado (exit 2): o `limpar` de sondas segue como era.
"""

from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("sessao_rascunho", str(REPO_ROOT / "bin" / "sessao"))
spec = importlib.util.spec_from_loader("sessao_rascunho", loader)
assert spec and spec.loader
sessao_mod = importlib.util.module_from_spec(spec)
loader.exec_module(sessao_mod)

ORDEM = "o20261003T142807-ff71ba"
OUTRA = "o20261003T090000-aaaaaa"


@pytest.fixture
def casa(tmp_path, monkeypatch):
    """Instancia falsa com o rascunho da fita (reextrair/, notas/) e o de outra ordem."""
    inst = tmp_path / "casa"
    raiz = inst / "var" / "tmp" / ORDEM
    (raiz / "reextrair" / "sub").mkdir(parents=True)
    (raiz / "reextrair" / "a.txt").write_bytes(b"x" * 1000)
    (raiz / "reextrair" / "sub" / "b.bin").write_bytes(b"y" * 234)
    (raiz / "notas").mkdir()
    (raiz / "notas" / "n.md").write_text("fica")
    outra = inst / "var" / "tmp" / OUTRA
    (outra / "reextrair").mkdir(parents=True)
    (outra / "reextrair" / "alheio.txt").write_text("de outra ordem")
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(inst))
    monkeypatch.setenv("PF_ORDEM_ID", ORDEM)
    return inst


def roda(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = sessao_mod.main(["limpar", *argv])
    return rc, out.getvalue(), err.getvalue()


def roda_json(*argv: str) -> tuple[int, dict]:
    rc, out, _ = roda(*argv, "--json")
    return rc, json.loads(out)


def test_sem_apply_mostra_plano_e_nao_apaga(casa):
    rc, res = roda_json("--rascunho", "reextrair")
    assert rc == 0
    assert res["apagado"] is False
    assert res["bytes"] == 1234
    assert res["arquivos"] == 2
    assert any(p.endswith("a.txt") for p in res["plano"])
    assert (casa / "var/tmp" / ORDEM / "reextrair" / "a.txt").exists()


def test_plano_em_texto_diz_bytes_e_que_nada_foi_apagado(casa):
    rc, out, _ = roda("--rascunho", "reextrair")
    assert rc == 0
    assert "1234" in out and "--apply" in out


def test_apply_apaga_so_a_subpasta_nomeada(casa):
    rc, res = roda_json("--rascunho", "reextrair", "--apply")
    assert rc == 0
    assert res["apagado"] is True
    assert res["bytes"] == 1234
    tmp = casa / "var" / "tmp"
    assert not (tmp / ORDEM / "reextrair").exists()
    assert (tmp / ORDEM / "notas" / "n.md").exists()          # irma fica
    assert (tmp / ORDEM).is_dir()                             # a raiz fica
    assert (tmp / OUTRA / "reextrair" / "alheio.txt").exists()  # outra ordem fica


def test_apply_em_texto_diz_o_que_apagou(casa):
    rc, out, _ = roda("--rascunho", "reextrair", "--apply")
    assert rc == 0
    assert "apagou" in out and "1234" in out


def test_apply_de_arquivo_unico(casa):
    rc, res = roda_json("--rascunho", "notas/n.md", "--apply")
    assert rc == 0
    assert not (casa / "var/tmp" / ORDEM / "notas" / "n.md").exists()
    assert (casa / "var/tmp" / ORDEM / "notas").is_dir()


@pytest.mark.parametrize("sub", ["", ".", "./", "reextrair/..", "notas/../"])
def test_raiz_inteira_sem_subpasta_nomeada_recusa(casa, sub):
    rc, res = roda_json("--rascunho", sub, "--apply")
    assert rc == 4
    assert "raiz" in res["erro"]
    assert (casa / "var/tmp" / ORDEM / "reextrair" / "a.txt").exists()
    assert (casa / "var/tmp" / ORDEM / "notas" / "n.md").exists()


def test_rascunho_sem_valor_recusa_a_raiz_inteira(casa):
    rc, res = roda_json("--rascunho", "--apply")
    assert rc == 4
    assert (casa / "var/tmp" / ORDEM / "reextrair" / "a.txt").exists()


@pytest.mark.parametrize("sub", [f"../{OUTRA}", f"../{OUTRA}/reextrair", "../../..", "reextrair/../../x"])
def test_ponto_ponto_que_sai_da_raiz_recusa(casa, sub):
    rc, res = roda_json("--rascunho", sub, "--apply")
    assert rc == 4
    assert "fora" in res["erro"]
    assert (casa / "var/tmp" / OUTRA / "reextrair" / "alheio.txt").exists()
    assert (casa / "var/tmp" / ORDEM / "reextrair" / "a.txt").exists()


def test_caminho_absoluto_fora_da_raiz_recusa(casa, tmp_path):
    alvo = tmp_path / "real"
    alvo.mkdir()
    (alvo / "f.txt").write_text("nao apagar")
    rc, res = roda_json("--rascunho", str(alvo), "--apply")
    assert rc == 4
    assert (alvo / "f.txt").exists()


def test_link_simbolico_para_fora_recusa(casa, tmp_path):
    alvo = tmp_path / "real"
    alvo.mkdir()
    (alvo / "f.txt").write_text("nao apagar")
    (casa / "var/tmp" / ORDEM / "atalho").symlink_to(alvo)
    rc, res = roda_json("--rascunho", "atalho", "--apply")
    assert rc == 4
    assert "fora" in res["erro"]
    assert (alvo / "f.txt").exists()


def test_link_simbolico_dentro_do_rascunho_apaga_o_link_nunca_o_alvo(casa, tmp_path):
    alvo = tmp_path / "real"
    alvo.mkdir()
    (alvo / "f.txt").write_text("nao apagar")
    (casa / "var/tmp" / ORDEM / "reextrair" / "para-fora").symlink_to(alvo)
    rc, res = roda_json("--rascunho", "reextrair", "--apply")
    assert rc == 0
    assert not (casa / "var/tmp" / ORDEM / "reextrair").exists()
    assert (alvo / "f.txt").read_text() == "nao apagar"


def test_pasta_da_ordem_que_e_link_simbolico_recusa(casa, tmp_path):
    real = tmp_path / "fora"
    (real / "reextrair").mkdir(parents=True)
    (real / "reextrair" / "f.txt").write_text("nao apagar")
    ordem = casa / "var/tmp" / ORDEM
    for p in sorted(ordem.rglob("*"), reverse=True):
        p.unlink() if p.is_file() or p.is_symlink() else p.rmdir()
    ordem.rmdir()
    ordem.symlink_to(real)
    rc, res = roda_json("--rascunho", "reextrair", "--apply")
    assert rc == 4
    assert (real / "reextrair" / "f.txt").exists()


@pytest.mark.parametrize("ordem", [None, "", "-", "..", "a/b"])
def test_sem_ordem_id_valido_recusa(casa, monkeypatch, ordem):
    if ordem is None:
        monkeypatch.delenv("PF_ORDEM_ID")
    else:
        monkeypatch.setenv("PF_ORDEM_ID", ordem)
    rc, res = roda_json("--rascunho", "reextrair", "--apply")
    assert rc == 4
    assert "PF_ORDEM_ID" in res["erro"]
    assert (casa / "var/tmp" / ORDEM / "reextrair" / "a.txt").exists()


def test_nunca_toca_pasta_de_outra_ordem_mesmo_com_o_mesmo_nome(casa):
    rc, _ = roda_json("--rascunho", "reextrair", "--apply")
    assert rc == 0
    assert (casa / "var/tmp" / OUTRA / "reextrair" / "alheio.txt").exists()


def test_subpasta_inexistente_sai_1(casa):
    rc, res = roda_json("--rascunho", "nao-existe", "--apply")
    assert rc == 1
    assert "nao existe" in res["erro"]


def test_apply_sem_rascunho_e_uso(casa):
    rc, res = roda_json("--apply")
    assert rc == 2
    assert "--rascunho" in res["erro"]


def test_limpar_de_sondas_segue_sem_rascunho(casa, monkeypatch):
    """Sem --rascunho o ato e o de sempre (chaves-sonda no msg-mem); aqui so se confere o roteamento."""
    chamado = {}
    monkeypatch.setattr(sessao_mod, "ato_limpar",
                        lambda dry_run, saida: chamado.update(dry_run=dry_run) or 0)
    rc, _, _ = roda("--dry-run")
    assert rc == 0 and chamado == {"dry_run": True}
