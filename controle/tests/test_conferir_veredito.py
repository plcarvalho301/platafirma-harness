# test_conferir_veredito — o Veredito comum (resultado.py) e as classes que ja o usam:
# card #3142. Stub de git/tarefas via monkeypatch de conferir.sh; nada toca rede ou disco
# fora de tmp_path/monkeypatch.
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

CONFERIR_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"
RESULTADO_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "resultado.py"


def _carregar(caminho, nome):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


resultado = _carregar(RESULTADO_PATH, "resultado_teste")
conferir = _carregar(CONFERIR_PATH, "conferir_veredito_teste")


# --- resultado.py: o tipo Veredito --------------------------------------------

def test_veredito_conforme_nao_exige_motivo():
    v = resultado.conforme(desde="2026-09-20")
    assert v.estado == "conforme"
    assert v.motivo is None
    assert v.dict()["desde"] == "2026-09-20"


def test_veredito_divergente_e_indeterminavel_exigem_motivo():
    with pytest.raises(ValueError):
        resultado.Veredito("divergente")
    with pytest.raises(ValueError):
        resultado.Veredito("indeterminavel")


def test_veredito_desde_ausente_vira_string_indeterminavel_no_dict():
    v = resultado.divergente("motivo qualquer")
    assert v.dict()["desde"] == "indeterminavel"


@pytest.mark.parametrize("itens,exit_esperado", [
    ([("a", resultado.conforme())], 0),
    ([("a", resultado.conforme()), ("b", resultado.divergente("x"))], 1),
    ([("a", resultado.conforme()), ("b", resultado.indeterminavel("x"))], 5),
    ([("a", resultado.divergente("x")), ("b", resultado.indeterminavel("y"))], 1),
])
def test_agrega_prioriza_divergente_sobre_indeterminavel(itens, exit_esperado):
    exit_code, *_ = resultado.agrega(itens)
    assert exit_code == exit_esperado


def test_linha_ancora_tem_a_forma_do_card_3142():
    itens = [("a", resultado.conforme()), ("b", resultado.divergente("x"))]
    linha, exit_code = resultado.linha_ancora("servico", None, itens, "abc1234")
    assert linha == (
        "release conferir servico: 1 conforme · 1 divergente · 0 não consegui olhar "
        "— release abc1234"
    )
    assert exit_code == 1


# --- conferir_card (card #3142, passo 6) --------------------------------------

def _stub_sh(respostas):
    """respostas: lista de (predicado(args) -> bool, (rc, out, err)). Primeiro bate, vale."""
    def sh(args):
        for pred, resp in respostas:
            if pred(args):
                return resp
        raise AssertionError(f"sh() nao stubado para: {args}")
    return sh


def test_card_conforme_quando_nenhum_commit_cita(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "sh", _stub_sh([
        (lambda a: a[:2] == ["git", "-C"] and "log" in a, (0, "", "")),
        (lambda a: a[:2] == ["git", "-C"] and "branch" in a, (0, "", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_card("9999", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "conforme"


def test_card_divergente_quando_commit_cita_e_estado_nao_andou(monkeypatch, capsys):
    log_saida = "deadbeef1234 2026-09-24T10:00:00-03:00\n"
    monkeypatch.setattr(conferir, "sh", _stub_sh([
        (lambda a: a[:2] == ["git", "-C"] and "log" in a and "origin/main" in a,
         (0, log_saida, "")),
        (lambda a: a[:2] == ["git", "-C"] and "branch" in a, (0, "", "")),
        (lambda a: len(a) >= 2 and a[-2] == "ler",
         (0, "#42 story · Em refinamento técnico (delivery)\n", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_card("42", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "Em refinamento técnico" in item["motivo"]
    assert item["desde"] == "2026-09-24T10:00:00-03:00"


def test_card_conforme_quando_estado_ja_avancou(monkeypatch, capsys):
    log_saida = "deadbeef1234 2026-09-24T10:00:00-03:00\n"
    monkeypatch.setattr(conferir, "sh", _stub_sh([
        (lambda a: a[:2] == ["git", "-C"] and "log" in a and "origin/main" in a,
         (0, log_saida, "")),
        (lambda a: a[:2] == ["git", "-C"] and "branch" in a, (0, "", "")),
        (lambda a: len(a) >= 2 and a[-2] == "ler",
         (0, "#42 story · Em execução (delivery)\n", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_card("42", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "conforme"


def test_card_sem_alvo_e_uso_incorreto(capsys):
    exit_code = conferir.conferir_card(None, como_json=True)
    saida = capsys.readouterr()
    assert exit_code == 2
    assert "uso" in json.loads(saida.out)["erro"]


# --- existe: indeterminavel sai 5, nao mais 2 (card #3142, passo 7) -----------

def test_existe_indeterminavel_sai_5(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "sh", lambda args: (1, "", "tarefas: sem rede"))
    exit_code = conferir.conferir_existe("card", "999999", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    assert dado["existe"] is None


# --- conferir_skill (card #3142) -----------------------------------------------

def _stub_sh_skill(fonte_sha, log_linhas=None, blob_por_sha=None, log_rc=0):
    """sh() stub para conferir_skill: rev-parse HEAD:<caminho> -> fonte_sha; git log
    -- <caminho> -> log_linhas (ou rc=log_rc quando != 0, simulando git log falho);
    rev-parse <sha>:<caminho> -> blob_por_sha.get(sha) (default: nao bate com nada)."""
    log_linhas = log_linhas or []
    blob_por_sha = blob_por_sha or {}

    def sh(args):
        if "rev-parse" in args and any(isinstance(a, str) and a.startswith("HEAD:") for a in args):
            return (0, fonte_sha, "")
        if "log" in args and "--" in args:
            if log_rc != 0:
                return (log_rc, "", "git log falhou (stub)")
            return (0, "\n".join(log_linhas), "")
        if "rev-parse" in args:
            sha = args[-1].split(":", 1)[0]
            return (0, blob_por_sha.get(sha, "0" * 40), "")
        raise AssertionError(f"sh() nao stubado para: {args}")
    return sh


def test_skill_conforme_quando_fonte_bate_com_servido(monkeypatch, capsys):
    fonte = "abc123def4567890abc123def4567890abc123d"
    monkeypatch.setattr(conferir, "sh", _stub_sh_skill(fonte))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_skill("minha-skill", servido=fonte[:12], como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "conforme"


def test_skill_divergente_quando_servido_nao_esta_na_historia(monkeypatch, capsys):
    fonte = "1111111111111111111111111111111111aaaa"
    log_linhas = ["2222222222222222222222222222222222bbbb 2222222 2026-09-20 10:00:00 -0300 msg"]
    monkeypatch.setattr(conferir, "sh", _stub_sh_skill(fonte, log_linhas=log_linhas))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_skill("minha-skill", servido="deadbeefcafe", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "nao existe na historia" in item["motivo"]


def test_skill_indeterminavel_quando_servido_nao_informado(monkeypatch, capsys):
    """card #3142: sem servido pra comparar e 'nao consegui olhar', nao sucesso — o exit
    fixo 2 de antes vira 5 (o mesmo exit de qualquer indeterminavel, via agrega())."""
    fonte = "1111111111111111111111111111111111aaaa"
    monkeypatch.setattr(conferir, "sh", _stub_sh_skill(fonte))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_skill("minha-skill", servido=None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "indeterminavel"


def test_skill_indeterminavel_quando_git_log_falha(monkeypatch, capsys):
    """card #3142, regra dura: git log falhando (rc != 0) ao listar o historico nao pode
    virar 'servido nao existe na historia' (falso divergente) — vira indeterminavel."""
    fonte = "1111111111111111111111111111111111aaaa"
    monkeypatch.setattr(conferir, "sh", _stub_sh_skill(fonte, log_rc=128))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_skill("minha-skill", servido="deadbeefcafe", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "indeterminavel"
    assert "historico" in item["motivo"]

# --- conferir_procedencia (card #3142) ------------------------------------------
# harness/excecao/excecao-classe = conforme; fora = divergente; quebrado (symlink
# sem destino) = indeterminavel; cada erro de excecoes_de_procedencia() vira item
# divergente proprio ("lista de exceções #N"). Filesystem real em tmp_path — mais
# fiel que stubar os.listdir/os.path.* aqui, e conferir_procedencia so faz IO real.

def _preparar_bin_procedencia(tmp_path, monkeypatch):
    harness_dir = tmp_path / "platafirma-harness"
    harness_dir.mkdir()
    (harness_dir / "verbo-real").write_text("#!/usr/bin/env bash\necho ok\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))
    monkeypatch.setattr(conferir, "HARNESS", str(harness_dir))
    monkeypatch.setattr(conferir, "BIN", str(bin_dir))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")
    monkeypatch.delenv("PF_PROD_RAIZ", raising=False)
    return harness_dir, bin_dir


def test_procedencia_tres_estados_por_entrada(tmp_path, monkeypatch, capsys):
    harness_dir, bin_dir = _preparar_bin_procedencia(tmp_path, monkeypatch)
    monkeypatch.setattr(conferir, "excecoes_de_procedencia", lambda: ({}, {}, []))

    (bin_dir / "verbo-do-harness").symlink_to(harness_dir / "verbo-real")
    (bin_dir / "arquivo-solto").write_text("echo nao e do harness\n")
    (bin_dir / "link-quebrado").symlink_to(tmp_path / "nao-existe")

    exit_code = conferir.conferir_procedencia(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1  # divergente pesa mais que indeterminavel
    dado = json.loads(saida.out)
    itens = {i["nome"]: i for i in dado["itens"]}
    assert itens["verbo-do-harness"]["estado"] == "conforme"
    assert itens["arquivo-solto"]["estado"] == "divergente"
    assert "copia nao e forma valida" in itens["arquivo-solto"]["motivo"]
    assert itens["link-quebrado"]["estado"] == "indeterminavel"
    assert "symlink sem destino" in itens["link-quebrado"]["motivo"]


def test_procedencia_so_quebrado_sai_5_nao_1(tmp_path, monkeypatch, capsys):
    """A correcao do card: quebrado nao e mais contado junto com "fora" (que forcava
    exit 1 como se fosse divergencia real) — vira indeterminavel isolado, exit 5."""
    harness_dir, bin_dir = _preparar_bin_procedencia(tmp_path, monkeypatch)
    monkeypatch.setattr(conferir, "excecoes_de_procedencia", lambda: ({}, {}, []))

    (bin_dir / "verbo-do-harness").symlink_to(harness_dir / "verbo-real")
    (bin_dir / "link-quebrado").symlink_to(tmp_path / "nao-existe")

    exit_code = conferir.conferir_procedencia(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    itens = {i["nome"]: i for i in dado["itens"]}
    assert itens["link-quebrado"]["estado"] == "indeterminavel"
    assert itens["verbo-do-harness"]["estado"] == "conforme"


def test_procedencia_excecao_declarada_e_conforme(tmp_path, monkeypatch, capsys):
    harness_dir, bin_dir = _preparar_bin_procedencia(tmp_path, monkeypatch)
    monkeypatch.setattr(
        conferir, "excecoes_de_procedencia",
        lambda: ({"ferramenta-terceira": ("claudinho-TI", "instalada por apt, nao pelo harness")}, {}, []))

    (bin_dir / "ferramenta-terceira").write_text("binario qualquer\n")

    exit_code = conferir.conferir_procedencia(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["nome"] == "ferramenta-terceira"
    assert dado["itens"][0]["estado"] == "conforme"


def test_procedencia_erro_na_lista_de_excecoes_vira_item_divergente_proprio(tmp_path, monkeypatch, capsys):
    harness_dir, bin_dir = _preparar_bin_procedencia(tmp_path, monkeypatch)
    monkeypatch.setattr(
        conferir, "excecoes_de_procedencia",
        lambda: ({}, {}, [
            "linha 7: `permite:` sem nome",
            "linha 12: excecao 'foo' sem dono e/ou motivo declarados",
        ]))

    (bin_dir / "verbo-do-harness").symlink_to(harness_dir / "verbo-real")

    exit_code = conferir.conferir_procedencia(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    nomes = [i["nome"] for i in dado["itens"]]
    assert "lista de exceções #1" in nomes
    assert "lista de exceções #2" in nomes
    erro1 = next(i for i in dado["itens"] if i["nome"] == "lista de exceções #1")
    assert erro1["estado"] == "divergente"
    assert erro1["motivo"] == "linha 7: `permite:` sem nome"


def test_procedencia_alvo_ausente_em_bin_e_erro_de_uso(tmp_path, monkeypatch, capsys):
    """Preservado sem mudanca: alvo que nao e entrada de BIN e erro de uso (exit 1,
    fora do envelope de resultado.relatorio), igual ao padrao de conferir_servico/verbo."""
    harness_dir, bin_dir = _preparar_bin_procedencia(tmp_path, monkeypatch)
    monkeypatch.setattr(conferir, "excecoes_de_procedencia", lambda: ({}, {}, []))

    exit_code = conferir.conferir_procedencia("nao-existe-no-bin", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    assert "nao e entrada de" in json.loads(saida.out)["erro"]

