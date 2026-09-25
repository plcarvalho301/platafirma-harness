# test_conferir_veredito — o Veredito comum (resultado.py) e as classes que ja o usam:
# card #3142. Stub de git/tarefas via monkeypatch de conferir.sh; nada toca rede ou disco
# fora de tmp_path/monkeypatch.
import enum
import importlib.machinery
import importlib.util
import json
import sys
import types
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


def _stub_sh_repo(respostas):
    """Como _stub_sh, mas aceita cwd= (conferir_repo sempre chama sh(args, cwd=raiz))."""
    def sh(args, cwd=None):
        for pred, resp in respostas:
            if pred(args):
                return resp
        raise AssertionError(f"sh() nao stubado para: {args} (cwd={cwd})")
    return sh


# --- conferir_repo (card #3142) -----------------------------------------------

def test_repo_conforme_quando_nada_achado(monkeypatch, capsys, tmp_path):
    raiz_repo = tmp_path / "casa-boa"
    (raiz_repo / ".git").mkdir(parents=True)
    (raiz_repo / "src").mkdir()
    (raiz_repo / "src" / "oi.py").write_text("print('oi')\n", encoding="utf-8")
    (raiz_repo / "README.md").write_text("# casa boa\n\nDiretorios: src/\n", encoding="utf-8")

    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))
    monkeypatch.setattr(conferir, "sh", _stub_sh_repo([
        (lambda a: a[:2] == ["git", "ls-files"], (0, "src/oi.py\x00README.md\x00", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_repo("casa-boa", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "conforme"


def test_repo_divergente_cita_gerado_e_readme_ausente(monkeypatch, capsys, tmp_path):
    raiz_repo = tmp_path / "casa-suja"
    (raiz_repo / ".git").mkdir(parents=True)
    (raiz_repo / "modulo.pyc").write_bytes(b"fake-bytecode")

    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))
    monkeypatch.setattr(conferir, "sh", _stub_sh_repo([
        (lambda a: a[:2] == ["git", "ls-files"], (0, "modulo.pyc\x00", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_repo("casa-suja", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    item = json.loads(saida.out)["itens"][0]
    assert item["estado"] == "divergente"
    assert "GERADO" in item["motivo"]
    assert "README ausente" in item["motivo"]


def test_repo_indeterminavel_quando_git_ls_files_falha(monkeypatch, capsys, tmp_path):
    """card #3142: 'nao consegui olhar' nunca e conforme. Antes desta conversao o rc de
    `sh()` era descartado (`_, out, _ = sh(...)`): git falhando virava lista vazia e o
    repo caia no caminho de 'nada achado' — conforme por omissao. Aqui tem que sair
    indeterminavel (exit 5), nunca 0."""
    raiz_repo = tmp_path / "casa-quebrada"
    (raiz_repo / ".git").mkdir(parents=True)

    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))
    monkeypatch.setattr(conferir, "sh", _stub_sh_repo([
        (lambda a: a[:2] == ["git", "ls-files"],
         (128, "", "fatal: not a git repository (disco indisponivel)")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_repo("casa-quebrada", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    item = json.loads(saida.out)["itens"][0]
    assert item["estado"] == "indeterminavel"
    assert "ls-files" in item["motivo"]


def test_repo_staged_divergente_ainda_sugere_no_verify(monkeypatch, capsys, tmp_path):
    """O hook de pre-commit chama `conferir repo --staged` em TEXTO, nao --json — este
    caminho nao pode quebrar, e a dica de `git commit --no-verify` e o jeito declarado
    de passar por cima (card #3142)."""
    raiz_repo = tmp_path / "casa-staged"
    (raiz_repo / ".git").mkdir(parents=True)
    (raiz_repo / "modulo.pyc").write_bytes(b"x")

    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))

    def sh_staged(args, cwd=None):
        if args[:2] == ["git", "rev-parse"]:
            return (0, str(raiz_repo), "")
        if args[:2] == ["git", "ls-files"]:
            return (0, "modulo.pyc\x00", "")
        if args[:2] == ["git", "diff"]:
            return (0, "modulo.pyc\x00", "")
        raise AssertionError(args)

    monkeypatch.setattr(conferir, "sh", sh_staged)
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_repo(None, staged=True, como_json=False)
    saida = capsys.readouterr()

    assert exit_code == 1
    assert "git commit --no-verify" in saida.out

# --- conferir_ferramental (card #3142, classe ferramental) --------------------

def _stub_ferramental_psql(respostas):
    """respostas: lista de (predicado(sql) -> bool, (linhas|None, erro|None)). Primeira que bate, vale."""
    def _psql(sql):
        for pred, resp in respostas:
            if pred(sql):
                return resp
        raise AssertionError(f"_ferramental_psql nao stubado para: {sql}")
    return _psql


def test_ferramental_conforme_quando_1a1_integro_e_verbo_resolve_em_bin(monkeypatch, capsys, tmp_path):
    (tmp_path / "meuverbo").write_text("#!/bin/sh\n")
    monkeypatch.setattr(conferir, "BIN", str(tmp_path))
    monkeypatch.setattr(conferir, "_ferramental_psql", _stub_ferramental_psql([
        (lambda sql: "full outer join" in sql, ([], None)),
        (lambda sql: "order by slug" in sql, (["meuverbo|bin/meuverbo"], None)),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_ferramental(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 2
    assert all(item["estado"] == "conforme" for item in dado["itens"])


def test_ferramental_divergente_quando_quebra_1a1_capacidade_verbo(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(conferir, "BIN", str(tmp_path))
    monkeypatch.setattr(conferir, "_ferramental_psql", _stub_ferramental_psql([
        (lambda sql: "full outer join" in sql, (["capX|"], None)),
        (lambda sql: "order by slug" in sql, ([], None)),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_ferramental(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item_1a1 = next(i for i in dado["itens"] if "1:1" in i["nome"])
    item_bin = next(i for i in dado["itens"] if "bin" in i["nome"])
    assert item_1a1["estado"] == "divergente"
    assert "capX" in item_1a1["motivo"]
    assert item_bin["estado"] == "conforme"


def test_ferramental_indeterminavel_quando_acervo_inalcancavel(monkeypatch, capsys, tmp_path):
    # card #3142: acervo fora do ar NAO pode sair como conforme (exit 0) nem morrer
    # cedo em exit 2 sem lista — vira item indeterminavel para cada checagem, exit 5.
    monkeypatch.setattr(conferir, "BIN", str(tmp_path))
    monkeypatch.setattr(conferir, "_ferramental_psql",
                         lambda sql: (None, "psql saiu 2: connection refused"))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_ferramental(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 2
    assert all(item["estado"] == "indeterminavel" for item in dado["itens"])
    assert "acervo.ferramental" in dado["itens"][0]["motivo"]

# --- conferir_commit (card #3142): fail-open documentado, veredito interno --------

def _stub_git_toplevel(raiz):
    return _stub_sh([
        (lambda a: a == ["git", "rev-parse", "--show-toplevel"], (0, str(raiz), "")),
    ])


def test_commit_conforme_quando_rastreador_aceita(tmp_path, monkeypatch, capsys):
    raiz = tmp_path
    (raiz / ".conferir-commit").write_text("base: http://rastreador.teste\n", encoding="utf-8")
    msg = tmp_path / "MSG"
    msg.write_text("ajusta X\n\nItem: #42\n", encoding="utf-8")

    monkeypatch.setattr(conferir, "sh", _stub_git_toplevel(raiz))
    monkeypatch.setattr(
        conferir, "pergunta_ao_rastreador",
        lambda base, mensagem, timeout: ({"ids": ["42"], "recusas": [], "avisos": []}, None),
    )

    exit_code = conferir.conferir_commit(str(msg), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["resultado"] == "ok"
    assert dado["veredito"]["estado"] == "conforme"
    assert dado["veredito"]["motivo"] is None


def test_commit_divergente_quando_rastreador_recusa_id(tmp_path, monkeypatch, capsys):
    raiz = tmp_path
    (raiz / ".conferir-commit").write_text("base: http://rastreador.teste\n", encoding="utf-8")
    msg = tmp_path / "MSG"
    msg.write_text("ajusta Y\n\nItem: #7\n", encoding="utf-8")

    monkeypatch.setattr(conferir, "sh", _stub_git_toplevel(raiz))
    monkeypatch.setattr(
        conferir, "pergunta_ao_rastreador",
        lambda base, mensagem, timeout: (
            {"ids": ["7"], "recusas": [{"id": "7", "texto": "item #7 esta fechado"}], "avisos": []},
            None,
        ),
    )

    exit_code = conferir.conferir_commit(str(msg), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    assert dado["resultado"] == "divergente"
    assert dado["veredito"]["estado"] == "divergente"
    assert "item #7 esta fechado" in dado["veredito"]["motivo"]


def test_commit_indeterminavel_fail_open_quando_rastreador_nao_responde(tmp_path, monkeypatch, capsys):
    """card #3142: rastreador fora do ar vira Veredito indeterminavel, NUNCA conforme
    silencioso — mas o exit continua 0 (fail-open deliberado, limite 2/4 do cabecalho),
    porque isto e o hook commit-msg ao vivo, nao o relatorio humano de release conferir."""
    raiz = tmp_path
    (raiz / ".conferir-commit").write_text("base: http://rastreador.teste\n", encoding="utf-8")
    msg = tmp_path / "MSG"
    msg.write_text("ajusta Z\n", encoding="utf-8")

    monkeypatch.setattr(conferir, "sh", _stub_git_toplevel(raiz))
    monkeypatch.setattr(
        conferir, "pergunta_ao_rastreador",
        lambda base, mensagem, timeout: (None, "http://rastreador.teste nao respondeu (timeout)"),
    )

    exit_code = conferir.conferir_commit(str(msg), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["resultado"] == "sem-gate"
    assert dado["veredito"]["estado"] == "indeterminavel"
    assert "nao respondeu" in dado["veredito"]["motivo"]


def test_commit_nao_declarado_segue_exit_0_sem_veredito(tmp_path, monkeypatch, capsys):
    """Repo sem `.conferir-commit` nao e avaliado (opt-in por repo, limite 1): nao ha
    Veredito para montar, e o exit fica 0 sem citar rastreador nenhum."""
    raiz = tmp_path
    msg = tmp_path / "MSG"
    msg.write_text("ajusta W\n", encoding="utf-8")

    monkeypatch.setattr(conferir, "sh", _stub_git_toplevel(raiz))

    exit_code = conferir.conferir_commit(str(msg), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["resultado"] == "nao-declarado"
    assert "veredito" not in dado

# --- conferir_arranque (card #3142) --------------------------------------------

def test_arranque_aponta_e_sem_arranque_contam_como_conforme(monkeypatch, tmp_path, capsys):
    aponta = tmp_path / "aponta" / "CLAUDE.md"
    aponta.parent.mkdir()
    aponta.write_text("Arranque desta sessao: ver conduta/arranque.md.\n", encoding="utf-8")

    sem_arranque = tmp_path / "sem-arranque" / "CLAUDE.md"
    sem_arranque.parent.mkdir()
    sem_arranque.write_text("Este posto de trabalho nao tem nada sobre arranque.\n", encoding="utf-8")

    monkeypatch.setattr(conferir, "_claude_mds", lambda incluir_efemero=False: [str(aponta), str(sem_arranque)])
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_arranque(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    estados = {item["nome"]: item["estado"] for item in dado["itens"]}
    assert set(estados.values()) == {"conforme"}
    assert len(estados) == 2


def test_arranque_copia_e_divergente(monkeypatch, tmp_path, capsys):
    copia = tmp_path / "copia" / "CLAUDE.md"
    copia.parent.mkdir()
    # dois sinais de bloco proprio (monta_sessao + vasculha), sem o ponteiro.
    copia.write_text(
        "Aqui explicamos monta_sessao por conta propria e como vasculhar a mesa.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(conferir, "_claude_mds", lambda incluir_efemero=False: [str(copia)])
    monkeypatch.setattr(conferir, "_rastreado_em", lambda caminho: None)
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_arranque(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 1
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "bloco proprio" in item["motivo"]


def test_arranque_erro_de_leitura_e_indeterminavel_nunca_conforme(monkeypatch, tmp_path, capsys):
    aponta = tmp_path / "aponta" / "CLAUDE.md"
    aponta.parent.mkdir()
    aponta.write_text("ver conduta/arranque.md\n", encoding="utf-8")

    # um "caminho" que nao e arquivo legivel: open() estoura IsADirectoryError (OSError),
    # simulando falha de leitura sem depender de permissao de disco.
    quebrado = tmp_path / "quebrado" / "CLAUDE.md"
    quebrado.mkdir(parents=True)

    monkeypatch.setattr(conferir, "_claude_mds", lambda incluir_efemero=False: [str(aponta), str(quebrado)])
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_arranque(None, como_json=True)
    saida = capsys.readouterr()

    # regra dura do card: "nao consegui olhar" nunca e conforme, e nunca some da lista.
    assert exit_code == 5
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 2
    estados = {item["nome"]: item["estado"] for item in dado["itens"]}
    aponta_nome = next(n for n in estados if n.endswith("aponta/CLAUDE.md"))
    assert estados[aponta_nome] == "conforme"
    quebrado_nome = next(n for n in estados if n.endswith("quebrado/CLAUDE.md"))
    assert estados[quebrado_nome] == "indeterminavel"
    item_quebrado = next(i for i in dado["itens"] if i["nome"] == quebrado_nome)
    assert "nao consegui ler" in item_quebrado["motivo"]


def test_arranque_staged_preserva_modo_texto_do_pre_commit(monkeypatch, tmp_path, capsys):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("ver conduta/arranque.md\n", encoding="utf-8")

    def _stub_sh(args):
        if args[:3] == ["git", "diff", "--cached"]:
            return (0, "CLAUDE.md\n", "")
        if args[:2] == ["git", "rev-parse"]:
            return (0, str(tmp_path), "")
        raise AssertionError(f"sh() nao stubado para: {args}")

    monkeypatch.setattr(conferir, "sh", _stub_sh)
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    # --staged e chamado pelo pre-commit em TEXTO (nunca --json): so confere que o
    # modo continua funcionando e devolvendo exit de veredito, nao a saida byte a byte.
    exit_code = conferir.conferir_arranque(None, staged=True, como_json=False)
    saida = capsys.readouterr()

    assert exit_code == 0
    assert "release conferir arranque" in saida.out


# --- conferir_superficie (card #3142) -----------------------------------------

def _registro_superficie(tmp_path, dado):
    reg_dir = tmp_path / "registro"
    reg_dir.mkdir()
    (reg_dir / "superficies.json").write_text(json.dumps(dado), encoding="utf-8")
    return tmp_path


def test_superficie_conforme_quando_tudo_servido(tmp_path, monkeypatch, capsys):
    _registro_superficie(tmp_path, {
        "conectores": {"claudinho-mcp": {"serve": ["conferir"]}},
        "superficies": {
            "fabrica": {"verificavel_do_host": True, "produtor": "fabrica_prod",
                        "conectores": ["claudinho-mcp"]},
        },
        "capacidades": {},
        "aposentadas": {"nomes": []},
    })
    monkeypatch.setattr(conferir, "HARNESS", str(tmp_path))
    monkeypatch.setattr(conferir, "_conectores_do_produtor", lambda prod: ({"claudinho-mcp"}, None))
    monkeypatch.setattr(conferir, "_mcp_jsons_da_superficie", lambda nome: [])
    monkeypatch.setattr(conferir, "_texto_da_fita", lambda: [])
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie(None, False, True)
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert dado["itens"] and all(i["estado"] == "conforme" for i in dado["itens"])


def test_superficie_divergente_quando_conector_prometido_nao_servido(tmp_path, monkeypatch, capsys):
    _registro_superficie(tmp_path, {
        "conectores": {"claudinho-mcp": {"serve": ["conferir"]}},
        "superficies": {
            "fabrica": {"verificavel_do_host": True, "produtor": "fabrica_prod",
                        "conectores": ["claudinho-mcp"]},
        },
        "capacidades": {},
        "aposentadas": {"nomes": []},
    })
    monkeypatch.setattr(conferir, "HARNESS", str(tmp_path))
    monkeypatch.setattr(conferir, "_conectores_do_produtor", lambda prod: (set(), None))
    monkeypatch.setattr(conferir, "_mcp_jsons_da_superficie", lambda nome: [])
    monkeypatch.setattr(conferir, "_texto_da_fita", lambda: [])
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie(None, False, True)
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    item = next(i for i in dado["itens"] if i["nome"] == "fabrica")
    assert item["estado"] == "divergente"
    assert "claudinho-mcp" in item["motivo"]


def test_superficie_registro_ilegivel_sai_indeterminavel_nao_conforme(tmp_path, monkeypatch, capsys):
    # card #3142: registro que nao abre/parseia e "nao consegui olhar" — nunca
    # sucesso silencioso, e nunca reprovacao disfarcada de "achado real" (exit 1
    # de antes).
    monkeypatch.setattr(conferir, "HARNESS", str(tmp_path))  # sem tmp_path/registro/*
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie(None, False, True)
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 5
    assert dado["itens"][0]["estado"] == "indeterminavel"


def test_superficie_staged_nao_trava_por_nao_medido_herdado(tmp_path, monkeypatch, capsys):
    # card #3142 + #2823: nao_medido (claude.ai, sempre "nao medido") e passivo de
    # host que o commit em curso nao criou. Sob --staged tem de continuar so
    # observacao — hooks/pre-commit chama `conferir superficie --staged || exit 1`
    # sem distinguir exit 1 de exit 5; se nao_medido travasse, TODO commit
    # reprovaria pra sempre so por claude.ai nunca ser "medido do host".
    _registro_superficie(tmp_path, {
        "conectores": {},
        "superficies": {
            "claude.ai": {"verificavel_do_host": False, "porque": "nao verificavel do host"},
        },
        "capacidades": {},
        "aposentadas": {"nomes": []},
    })
    monkeypatch.setattr(conferir, "HARNESS", str(tmp_path))
    monkeypatch.setattr(conferir, "_quebradas_no_staged", lambda padrao, servidas: [])
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie(None, True, True)
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert dado["itens"] and all(i["estado"] == "conforme" for i in dado["itens"])


# --- conferir_superficie_descricao (card #3142) -------------------------------

def test_superficie_descricao_conforme_quando_indice_bate_com_servido(tmp_path, monkeypatch, capsys):
    catalogo = tmp_path / "catalogo-de-fontes.md"
    catalogo.write_text(
        "## Fontes da plataforma\n\n| fonte | x |\n|---|---|\n| acervo | y |\n", encoding="utf-8")
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie_descricao(
        None, como_json=True, caminho_catalogo=str(catalogo),
        descricao_fornecida="recuperar fontes:\n  - acervo (exata): ...\n")
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert dado["itens"][0]["estado"] == "conforme"


def test_superficie_descricao_divergente_quando_servido_cita_fonte_fora_do_indice(tmp_path, monkeypatch, capsys):
    catalogo = tmp_path / "catalogo-de-fontes.md"
    catalogo.write_text(
        "## Fontes da plataforma\n\n| fonte | x |\n|---|---|\n| acervo | y |\n", encoding="utf-8")
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie_descricao(
        None, como_json=True, caminho_catalogo=str(catalogo),
        descricao_fornecida="recuperar fontes:\n  - fonte-fantasma (exata): ...\n")
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert dado["itens"][0]["estado"] == "divergente"


def test_superficie_descricao_mcp_fora_do_ar_sai_indeterminavel_nao_conforme(monkeypatch, capsys):
    # card #3142: antes saia exit 0 (sucesso silencioso) quando o MCP nao
    # respondia ou a tabela do catalogo nao existia — exatamente o defeito que
    # o card corrige.
    monkeypatch.setattr(conferir, "_obtem_descricao_servida_mcp",
                         lambda url=None: (None, "servidor MCP nao respondeu (timeout)"))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_superficie_descricao(None, como_json=True)
    dado = json.loads(capsys.readouterr().out)

    assert exit_code == 5
    assert dado["itens"][0]["estado"] == "indeterminavel"


# --- conferir_front (card #3142): um item por tela; abertas so observam --------

def test_front_conforme_tela_unica_sem_violacao(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "_telas_de_front",
                         lambda: [("platafirma-ui/app/painel", "platafirma-ui", True, True)])
    monkeypatch.setattr(conferir, "_viola_segredo_ou_api", lambda dir_abs: (False, False, []))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_front(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 1
    assert dado["itens"][0]["estado"] == "conforme"
    assert dado["itens"][0]["nome"] == "platafirma-ui/app/painel"


def test_front_divergente_tela_fora_do_ui_repo(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "_telas_de_front",
                         lambda: [("platafirma-rastreador/tela", "platafirma-rastreador", True, True)])
    monkeypatch.setattr(conferir, "_viola_segredo_ou_api", lambda dir_abs: (False, False, []))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_front(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    item = json.loads(saida.out)["itens"][0]
    assert item["estado"] == "divergente"
    assert "platafirma-rastreador" in item["motivo"]


def test_front_divergente_monta_segredo_e_serve_api_motivo_combinado(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "_telas_de_front",
                         lambda: [("platafirma-ui/app/leak", "platafirma-ui", True, True)])
    monkeypatch.setattr(
        conferir, "_viola_segredo_ou_api",
        lambda dir_abs: (True, True, ["docker-compose.yml: env_file", "nginx.conf: proxy_pass"]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_front(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    item = json.loads(saida.out)["itens"][0]
    assert item["estado"] == "divergente"
    assert "monta segredo" in item["motivo"]
    assert "serve rota de API" in item["motivo"]


def test_front_tela_aberta_fica_fora_da_lista_de_itens(monkeypatch, capsys):
    # arq:0057 "Aberto": platafirma-core e observacao, nunca item — mesmo violando (2).
    monkeypatch.setattr(conferir, "_telas_de_front", lambda: [
        ("platafirma-core/app/legado", "platafirma-core", True, True),
        ("platafirma-ui/app/painel", "platafirma-ui", True, True),
    ])
    monkeypatch.setattr(conferir, "_viola_segredo_ou_api", lambda dir_abs: (False, False, []))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_front(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 1
    assert dado["itens"][0]["nome"] == "platafirma-ui/app/painel"
    assert all("core" not in item["nome"] for item in dado["itens"])

# Nao ha teste de "indeterminavel": ao contrario de servico/verbo/card, a nota desta
# tarefa define front com so 2 estados por item (divergente se fora/montam/servem;
# conforme caso contrario) — nao ha, nesta conversao, um caminho que produza item
# indeterminavel. Ver campo "decisao_dificil" do plano para a ressalva sobre
# _le()/_viola_segredo_ou_api engolir OSError como "sem violacao".


def _instalar_recuperacao_fake(monkeypatch, autoriza=None, acao="ler",
                                fontes=("acervo", "board", "fila")):
    """Instala recuperacao.pep/recuperacao.fontes falsos em sys.modules — conferir_alcance
    faz `from recuperacao.pep import PEP` e `from recuperacao.fontes import Fonte` dentro
    do corpo da função, então basta popular sys.modules antes da chamada."""
    Fonte = enum.Enum("Fonte", {n: n for n in fontes})

    class PEP:
        def __init__(self):
            pass

        def autoriza_fonte(self, sujeito, fonte):
            return autoriza

        def acao(self, fonte):
            return acao

    mod_pep = types.ModuleType("recuperacao.pep")
    mod_pep.PEP = PEP
    mod_fontes = types.ModuleType("recuperacao.fontes")
    mod_fontes.Fonte = Fonte
    mod_pkg = types.ModuleType("recuperacao")
    monkeypatch.setitem(sys.modules, "recuperacao", mod_pkg)
    monkeypatch.setitem(sys.modules, "recuperacao.pep", mod_pep)
    monkeypatch.setitem(sys.modules, "recuperacao.fontes", mod_fontes)
    return Fonte


def _quebrar_recuperacao(monkeypatch):
    """Simula o maquinario de acesso ilegivel: modulo presente, mas sem PEP —
    dispara ImportError determinístico em qualquer ambiente, sem depender do
    disco real."""
    mod_pep_quebrado = types.ModuleType("recuperacao.pep")
    mod_pkg = types.ModuleType("recuperacao")
    monkeypatch.setitem(sys.modules, "recuperacao", mod_pkg)
    monkeypatch.setitem(sys.modules, "recuperacao.pep", mod_pep_quebrado)
    monkeypatch.delitem(sys.modules, "recuperacao.fontes", raising=False)


def _stub_carrega_yaml(monkeypatch, sujeitos=None, superficies=None):
    def carrega(caminho):
        if caminho.endswith("sujeitos.yaml"):
            return (sujeitos or {}), None
        if caminho.endswith("superficies.yaml"):
            return (superficies or {}), None
        return {}, None
    monkeypatch.setattr(conferir, "_carrega_yaml", carrega)


class _Neg:
    def __init__(self, regra, motivo):
        self.regra = regra
        self.motivo = motivo


# --- conferir_alcance (card #3142) ---------------------------------------------

def test_alcance_uso_incorreto_sai_2_sem_medir(capsys):
    exit_code = conferir.conferir_alcance(None, None, como_json=True)
    saida = capsys.readouterr()
    assert exit_code == 2
    assert saida.out == ""  # uso vai por stderr, nao passa pelo Veredito


def test_alcance_conforme_quando_cadeia_inteira_fecha(monkeypatch, capsys):
    _instalar_recuperacao_fake(monkeypatch, autoriza=None, acao="ler")
    _stub_carrega_yaml(
        monkeypatch,
        sujeitos={"sujeitos": {"claudinho": {"papeis": ["leitor"], "client": "cli-x"}}},
        superficies={"superficies": {"acervo": {
            "alcancavel": True, "ingress": "interno", "rede": "vpc",
            "acl_canonica": True, "portao": "gate-acervo",
        }}},
    )
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_alcance("claudinho", "acervo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 1
    item = dado["itens"][0]
    assert item["nome"] == "claudinho -> acervo"
    assert item["estado"] == "conforme"
    assert item["motivo"] is None


def test_alcance_divergente_quando_pdp_nega(monkeypatch, capsys):
    _instalar_recuperacao_fake(
        monkeypatch,
        autoriza=_Neg("politica-explicita", "regra nega escrita para este papel"),
        acao="escrever",
    )
    _stub_carrega_yaml(
        monkeypatch,
        sujeitos={"sujeitos": {"claudinho": {"papeis": ["leitor"], "client": "cli-x"}}},
        superficies={"superficies": {"acervo": {
            "alcancavel": True, "ingress": "interno", "rede": "vpc",
            "acl_canonica": True, "portao": "gate-acervo",
        }}},
    )
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_alcance("claudinho", "acervo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "elo mais fraco: PDP" in item["motivo"]
    assert "politica-explicita" in item["motivo"]


def test_alcance_indeterminavel_quando_fonte_fora_do_catalogo(monkeypatch, capsys):
    _instalar_recuperacao_fake(monkeypatch, autoriza=None, acao="ler")
    _stub_carrega_yaml(
        monkeypatch,
        sujeitos={"sujeitos": {"claudinho": {"papeis": ["leitor"], "client": "cli-x"}}},
        superficies={"superficies": {}},  # "acervo" ausente do catalogo
    )
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_alcance("claudinho", "acervo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "indeterminavel"
    assert "nao esta no catalogo de superficies" in item["motivo"]


def test_alcance_indeterminavel_quando_maquinario_ilegivel(monkeypatch, capsys):
    _quebrar_recuperacao(monkeypatch)
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_alcance("claudinho", "acervo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "indeterminavel"
    assert "maquinario de acesso ilegivel" in item["motivo"]


def test_alcance_texto_preserva_saltos_detalhados(monkeypatch, capsys):
    _instalar_recuperacao_fake(monkeypatch, autoriza=None, acao="ler")
    _stub_carrega_yaml(
        monkeypatch,
        sujeitos={"sujeitos": {"claudinho": {"papeis": ["leitor"], "client": "cli-x"}}},
        superficies={"superficies": {"acervo": {
            "alcancavel": True, "ingress": "interno", "rede": "vpc",
            "acl_canonica": True, "portao": "gate-acervo",
        }}},
    )
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_alcance("claudinho", "acervo", como_json=False)
    saida = capsys.readouterr()

    assert exit_code == 0
    assert "alcance: claudinho -> acervo" in saida.out
    assert "1 identidade" in saida.out
    assert "cadeia INTEIRA" in saida.out
    assert "release conferir alcance claudinho acervo: 1 conforme" in saida.out


# --- conferir_pdp (card #3142) ---------------------------------------------

def _pdp_current_com_release(tmp_path):
    """Cria uma release fake e devolve o symlink current -> release, para testar
    o caminho onde a tag corrente E encontrada."""
    release = tmp_path / "rel-abc1234"
    release.mkdir()
    link = tmp_path / "current"
    link.symlink_to(release)
    return link


def test_pdp_conforme_quando_tag_encontrada(monkeypatch, tmp_path, capsys):
    link = _pdp_current_com_release(tmp_path)
    monkeypatch.setenv("PF_CURRENT_LINK", str(link))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_pdp("ops-server", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 1
    item = dado["itens"][0]
    assert item["nome"] == "ops-server"
    assert item["estado"] == "conforme"
    assert item["motivo"] is None


def test_pdp_indeterminavel_quando_current_nao_encontrada(monkeypatch, tmp_path, capsys):
    # card #3142: release em current ausente e "nao consegui medir a tag", nao
    # "medi e diverge" — antes desta correcao isto marcava os 4 servidores como
    # divergente (exit 1); agora sai indeterminavel (exit 5), sem mascarar a
    # falha de leitura como defeito medido.
    link_inexistente = tmp_path / "current-nao-existe"
    monkeypatch.setenv("PF_CURRENT_LINK", str(link_inexistente))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_pdp(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 4
    assert all(item["estado"] == "indeterminavel" for item in dado["itens"])
    assert all("nao encontrada" in item["motivo"] for item in dado["itens"])
    assert "4 não consegui olhar" in dado["ancora"]


def test_pdp_sem_caminho_de_divergencia_hoje(monkeypatch, tmp_path, capsys):
    """Documenta o estado real da classe: sem uma tag 'esperada' distinta para
    comparar, tag encontrada so pode sair conforme — nao ha hoje logica que
    produza divergente para pdp. Se essa comparacao for adicionada depois, este
    teste precisa mudar junto."""
    link = _pdp_current_com_release(tmp_path)
    monkeypatch.setenv("PF_CURRENT_LINK", str(link))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_pdp(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 4
    assert all(item["estado"] == "conforme" for item in dado["itens"])


# --- conferir_vocabulario (card #3142) ------------------------------------

def test_vocabulario_conforme_quando_todas_as_referencias_estao_no_catalogo(monkeypatch, tmp_path, capsys):
    alvo = tmp_path / "dono.md"
    alvo.write_text("texto com `verboA acaoA` no meio da frase.\n", encoding="utf-8")
    monkeypatch.setattr(conferir, "carregar_verbos_e_atos",
                         lambda bin_dir: ({"verboA": {"acaoA"}}, {}))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_vocabulario(str(alvo), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert len(dado["itens"]) == 1
    item = dado["itens"][0]
    assert item["estado"] == "conforme"
    assert item["nome"] == "1 referencia(s) conferida(s)"


def test_vocabulario_divergente_quando_ato_fora_do_catalogo(monkeypatch, tmp_path, capsys):
    alvo = tmp_path / "dono.md"
    alvo.write_text("usa `verboA acaoZ` que nao existe.\n", encoding="utf-8")
    monkeypatch.setattr(conferir, "carregar_verbos_e_atos",
                         lambda bin_dir: ({"verboA": {"acaoA"}}, {}))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_vocabulario(str(alvo), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    divergentes = [it for it in dado["itens"] if it["estado"] == "divergente"]
    assert len(divergentes) == 1
    item = divergentes[0]
    assert item["nome"].endswith("dono.md:1")
    assert "verbo 'verboA' nao serve ato 'acaoZ'" in item["motivo"]
    assert "dono.md:1" in item["motivo"]


def test_vocabulario_indeterminavel_quando_nao_consegue_ler_arquivo(monkeypatch, tmp_path, capsys):
    alvo = tmp_path / "dono.md"
    alvo.write_text("`verboA acaoA`\n", encoding="utf-8")
    monkeypatch.setattr(conferir, "carregar_verbos_e_atos",
                         lambda bin_dir: ({"verboA": {"acaoA"}}, {}))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    def _open_falha(*a, **k):
        raise OSError("entrada/saida: acervo indisponivel")
    monkeypatch.setattr(conferir, "open", _open_falha, raising=False)

    exit_code = conferir.conferir_vocabulario(str(alvo), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    indeterminaveis = [it for it in dado["itens"] if it["estado"] == "indeterminavel"]
    assert len(indeterminaveis) == 1
    assert "nao consegui ler" in indeterminaveis[0]["motivo"]


# --- conferir_diagrama (card #3142) --------------------------------------------

class _RespostaKrokiFake:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_diagrama_conforme_quando_kroki_compila(monkeypatch, capsys, tmp_path):
    alvo = tmp_path / "fluxo.mmd"
    alvo.write_text("graph TD; a-->b;", encoding="utf-8")
    monkeypatch.setenv("KROKI_URL", "http://kroki.test:8000")
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")
    monkeypatch.setattr(conferir.urllib.request, "urlopen",
                         lambda req, timeout=5: _RespostaKrokiFake(200))

    exit_code = conferir.conferir_diagrama(str(alvo), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["nome"] == str(alvo)
    assert item["estado"] == "conforme"


def test_diagrama_divergente_quando_kroki_recusa_o_render(monkeypatch, capsys, tmp_path):
    import io

    alvo = tmp_path / "quebrado.mmd"
    alvo.write_text("isto nao e mermaid valido", encoding="utf-8")
    monkeypatch.setenv("KROKI_URL", "http://kroki.test:8000")
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    def _urlopen(req, timeout=5):
        raise conferir.urllib.error.HTTPError(
            "http://kroki.test:8000/mermaid/svg", 400, "Bad Request",
            {}, io.BytesIO(b"erro de sintaxe na linha 1"))
    monkeypatch.setattr(conferir.urllib.request, "urlopen", _urlopen)

    exit_code = conferir.conferir_diagrama(str(alvo), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "erro de sintaxe" in item["motivo"]


def test_diagrama_indeterminavel_quando_kroki_inalcancavel(monkeypatch, capsys, tmp_path):
    alvo = tmp_path / "fluxo.d2"
    alvo.write_text("a -> b", encoding="utf-8")
    monkeypatch.setenv("KROKI_URL", "http://kroki.test:8000")
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    def _urlopen(req, timeout=5):
        raise conferir.urllib.error.URLError("connection refused")
    monkeypatch.setattr(conferir.urllib.request, "urlopen", _urlopen)

    exit_code = conferir.conferir_diagrama(str(alvo), como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "indeterminavel"
    assert "connection refused" in item["motivo"]
