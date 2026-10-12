# O texto do controle por ato no registro do ferramental e o retrato que a Taipa consome
# (#3444; arq:0124 §3, arq:0125 U33). Sem banco e sem rede: o psql do registrar e a leitura do
# retrato sao trocados por falsos que devolvem o que o banco devolveria.
import importlib.machinery
import importlib.util
import json
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "bin")
ACERVO = os.path.join(BIN, "_acervo")


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


registrar = _carrega("acervo_registrar_controle", "registrar")
retrato = _carrega("acervo_ferramental_retrato", "ferramental-retrato")


# ------------------------------------------------------------------ registrar: o cabecalho

def _verbo(tmp_path, nome, linhas):
    f = tmp_path / nome
    f.write_text("#!/usr/bin/env bash\n" + "\n".join(linhas) + "\nset -e\n", encoding="utf-8")
    return f


def test_cabecalho_acumula_as_tres_chaves_por_ato(tmp_path):
    f = _verbo(tmp_path, "v", [
        "# v — faz coisa", "# capacidade: x", "# atos: ler, apagar",
        "# rotulo: ler=Ler {documento-de-arquivo}", "# rotulo: apagar=Apagar",
        "# volta: apagar=nao", "# atalho: apagar=Delete"])
    campos, _ = registrar._le_cabecalho(str(f))
    assert campos["rotulo"] == ["ler=Ler {documento-de-arquivo}", "apagar=Apagar"]
    assert campos["volta"] == ["apagar=nao"]
    assert campos["atalho"] == ["apagar=Delete"]


def test_cabecalho_de_26_atos_com_tres_chaves_cada_e_lido_inteiro(tmp_path):
    atos = ["a%d" % i for i in range(26)]
    linhas = ["# v — faz coisa", "# capacidade: x", "# atos: " + ", ".join(atos)]
    for chave in ("le", "escreve"):
        linhas += ["# %s: %s=nada" % (chave, a) for a in atos]
    for chave, valor in (("rotulo", "Faz"), ("volta", "nao"), ("atalho", "x")):
        linhas += ["# %s: %s=%s" % (chave, a, valor) for a in atos]
    campos, _ = registrar._le_cabecalho(str(_verbo(tmp_path, "grande", linhas)))
    assert len(linhas) > 80
    assert len(campos["rotulo"]) == len(campos["volta"]) == len(campos["atalho"]) == 26
    assert len(campos["escreve"]) == 26


def test_o_bloco_acaba_na_primeira_linha_de_codigo(tmp_path):
    f = _verbo(tmp_path, "v", ["# v — faz", "# capacidade: x", "# atos: a"])
    with open(f, "a", encoding="utf-8") as fh:
        fh.write("# rotulo: a=Solto no codigo\n")
    campos, _ = registrar._le_cabecalho(str(f))
    assert "rotulo" not in campos


def _verbos_do_bin():
    for nome in sorted(os.listdir(BIN)):
        p = os.path.join(BIN, nome)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                if f.read(2) == b"#!":
                    yield p


def test_ler_o_bloco_inteiro_nao_muda_o_que_a_janela_de_80_linhas_lia(tmp_path):
    """Todo verbo cujo cabecalho cabia em 80 linhas le o mesmo de antes."""
    comparados = 0
    for p in _verbos_do_bin():
        with open(p, encoding="utf-8", errors="replace") as f:
            todas = f.readlines()
        bloco = 0
        for l in todas:
            if l.strip() and not l.lstrip().startswith("#"):
                break
            bloco += 1
        if bloco > 80:
            continue
        corte = tmp_path / ("corte-" + os.path.basename(p))
        corte.write_text("".join(todas[:80]), encoding="utf-8")
        assert registrar._le_cabecalho(p) == registrar._le_cabecalho(str(corte)), p
        comparados += 1
    assert comparados > 10


# ------------------------------------------------------------------ registrar: a forma de cada chave

def _controle(*linhas_por_chave, verbo="v"):
    campos = {}
    for chave, valor in linhas_por_chave:
        campos.setdefault(chave, []).append(valor)
    return registrar._controle_por_ato(campos, verbo)


def test_controle_le_as_tres_chaves_por_ato():
    r = _controle(("rotulo", "apagar=Apagar {documento-de-arquivo}"), ("volta", "apagar=nao"),
                  ("atalho", "apagar=Delete"), ("volta", "retirar=sim — acervo restaurar"))
    assert r == {"apagar": {"rotulo": "Apagar {documento-de-arquivo}", "volta": "nao",
                            "atalho": "Delete"},
                 "retirar": {"volta": "sim — acervo restaurar"}}


def test_volta_com_hifen_grava_com_travessao():
    assert _controle(("volta", "a=sim - desfaz com b"))["a"]["volta"] == "sim — desfaz com b"


def test_verbo_sem_as_chaves_nao_tem_controle():
    assert registrar._controle_por_ato({"atos": "a"}, "v") == {}


@pytest.mark.parametrize("chave,linha", [
    ("rotulo", "sem-igual"), ("rotulo", "a="), ("rotulo", "a=Abre {chave solta"),
    ("rotulo", "a=Abre {Obra}"), ("volta", "a=talvez"), ("volta", "a=sim"),
    ("volta", "a=sim — "), ("atalho", "a=duas teclas"), ("atalho", "a=tecla-longa-demais"),
])
def test_controle_fora_da_forma_recusa_o_registro(chave, linha):
    with pytest.raises(SystemExit) as e:
        _controle((chave, linha))
    assert e.value.code == 3


def test_a_mesma_chave_duas_vezes_para_o_ato_recusa():
    with pytest.raises(SystemExit) as e:
        _controle(("rotulo", "a=Um"), ("rotulo", "a=Dois"))
    assert e.value.code == 3


# ------------------------------------------------------------------ registrar: o que vai ao banco

class Banco:
    """Troca o psql do registrar: guarda o SQL de escrita e responde as consultas."""

    def __init__(self, conceitos=(), atalhos_de_outros=()):
        self.conceitos, self.atalhos_de_outros = set(conceitos), list(atalhos_de_outros)
        self.escrita = None

    def __call__(self, sql, escreve=False):
        if escreve:
            self.escrita = sql
            return ""
        if "acervo.conceito" in sql:
            return "".join(s + "\n" for s in sorted(self.conceitos) if "'%s'" % s in sql)
        if "from acervo.ferramental_ato where verbo <>" in sql:
            return "".join("|".join(l) + "\n" for l in self.atalhos_de_outros)
        return ""


@pytest.fixture
def verbo(tmp_path, monkeypatch):
    monkeypatch.setattr(registrar, "BIN", str(tmp_path))
    return tmp_path


def _registra(verbo, monkeypatch, banco, linhas, nome="demo"):
    _verbo(verbo, nome, ["# %s — faz coisa" % nome, "# capacidade: x",
                         "# atos: ler (leitura, casa), apagar (escrita, casa)"] + linhas)
    monkeypatch.setattr(registrar, "_psql", banco)
    return registrar.registrar_um(nome)


def test_verbo_sem_controle_registra_igual_a_antes(verbo, monkeypatch):
    banco = Banco()
    _registra(verbo, monkeypatch, banco, [])
    assert ("insert into acervo.ferramental_ato (verbo, ato, capacidade, acao, tipo) "
            "values ('demo', 'ler', 'casa', 'leitura', 'casa') on conflict (verbo, ato) "
            "do update set capacidade=excluded.capacidade, acao=excluded.acao, "
            "tipo=excluded.tipo;") in banco.escrita
    assert "acao, tipo, rotulo" not in banco.escrita
    assert "atalho" not in banco.escrita


def test_verbo_com_controle_grava_as_tres_colunas_por_ato(verbo, monkeypatch):
    banco = Banco(conceitos=["documento-de-arquivo"])
    _registra(verbo, monkeypatch, banco, [
        "# rotulo: apagar=Apagar {documento-de-arquivo}", "# volta: apagar=nao",
        "# atalho: apagar=Delete"])
    assert ("insert into acervo.ferramental_ato (verbo, ato, capacidade, acao, tipo, rotulo, "
            "volta, atalho) values ('demo', 'apagar', 'casa', 'escrita', 'casa', "
            "'Apagar {documento-de-arquivo}', 'nao', 'Delete')") in banco.escrita
    # o ato que nao declara fica com as tres colunas nulas: sem texto inventado
    assert "values ('demo', 'ler', 'casa', 'leitura', 'casa', null, null, null)" in banco.escrita


def test_objeto_do_rotulo_fora_do_tesauro_recusa_o_registro(verbo, monkeypatch):
    banco = Banco(conceitos=[])
    with pytest.raises(SystemExit) as e:
        _registra(verbo, monkeypatch, banco, ["# rotulo: apagar=Apagar {obra}"])
    assert e.value.code == 3
    assert banco.escrita is None


def test_controle_de_ato_que_atos_nao_lista_recusa(verbo, monkeypatch):
    with pytest.raises(SystemExit) as e:
        _registra(verbo, monkeypatch, Banco(), ["# volta: voa=nao"])
    assert e.value.code == 3


def test_atalho_ja_em_uso_e_aviso_e_nao_recusa(verbo, monkeypatch, capsys):
    banco = Banco(atalhos_de_outros=[("tarefas", "apagar", "x")])
    _registra(verbo, monkeypatch, banco, ["# atalho: apagar=x"])
    assert banco.escrita is not None
    assert "tarefas apagar" in capsys.readouterr().err


# ------------------------------------------------------------------ registrar: capacidade por ato (#3465)
#
# O segundo campo do par de `# atos:` e o tipo que o ato manda ao PEP (arq:0110 Q1, Q12) e o registrar
# o grava em `tipo` e, sem a chave propria, tambem em `capacidade`. A capacidade filha da arq:0119 §4
# (leitura, descoberta) vai por `# capacidade-ato:` e so toca `capacidade`: o par fica.

def test_capacidade_ato_grava_a_capacidade_e_deixa_o_tipo_do_par(verbo, monkeypatch):
    banco = Banco()
    _registra(verbo, monkeypatch, banco, ["# capacidade-ato: ler=leitura"])
    # capacidade vem da chave; acao e tipo, do par
    assert "values ('demo', 'ler', 'leitura', 'leitura', 'casa')" in banco.escrita
    # o ato sem a chave grava capacidade = segundo campo, como sempre
    assert "values ('demo', 'apagar', 'casa', 'escrita', 'casa')" in banco.escrita


def test_capacidade_ato_entra_na_descricao_servida(verbo, monkeypatch):
    _, desc = _registra(verbo, monkeypatch, Banco(),
                        ["# capacidade-ato: ler=leitura", "# capacidade-ato: apagar=retirada"])
    assert desc.endswith("capacidade por ato: ler=leitura, apagar=retirada")
    assert "atos: ler (leitura, casa), apagar (escrita, casa)" in desc


def test_verbo_sem_capacidade_ato_tem_a_mesma_descricao_de_antes(verbo, monkeypatch):
    _, desc = _registra(verbo, monkeypatch, Banco(), [])
    assert "capacidade por ato" not in desc


@pytest.mark.parametrize("linha", ["sem-igual", "=leitura", "ler=", "ler=Leitura", "ler=duas palavras"])
def test_capacidade_ato_fora_da_forma_recusa_o_registro(verbo, monkeypatch, linha):
    banco = Banco()
    with pytest.raises(SystemExit) as e:
        _registra(verbo, monkeypatch, banco, ["# capacidade-ato: " + linha])
    assert e.value.code == 3
    assert banco.escrita is None


def test_capacidade_ato_de_ato_que_atos_nao_lista_recusa(verbo, monkeypatch):
    banco = Banco()
    with pytest.raises(SystemExit) as e:
        _registra(verbo, monkeypatch, banco, ["# capacidade-ato: voa=leitura"])
    assert e.value.code == 3
    assert banco.escrita is None


def test_capacidade_ato_duas_vezes_para_o_mesmo_ato_recusa(verbo, monkeypatch):
    with pytest.raises(SystemExit) as e:
        _registra(verbo, monkeypatch, Banco(),
                  ["# capacidade-ato: ler=leitura", "# capacidade-ato: ler=descoberta"])
    assert e.value.code == 3


def test_acervo_declara_leitura_e_descoberta_sem_mexer_no_par_do_pep():
    campos, desc = registrar._le_cabecalho(os.path.join(BIN, "acervo"))
    assert "ler (leitura, casa)" in campos["atos"] and "listar (leitura, casa)" in campos["atos"]
    assert registrar._capacidade_por_ato(campos, "acervo") == {"ler": "leitura", "listar": "descoberta"}
    assert "capacidade por ato: ler=leitura, listar=descoberta" in desc


# ------------------------------------------------------------------ o retrato

OBRA = {"documento-de-arquivo": "Documento de arquivo", "pdp": "PDP"}


def test_objeto_resolve_pelo_rotulo_do_conceito_com_a_inicial_no_meio_da_frase():
    assert retrato.resolve("Apagar {documento-de-arquivo}", OBRA) == "Apagar documento de arquivo"
    assert retrato.resolve("Ler {pdp}", OBRA) == "Ler PDP"
    assert retrato.resolve("{documento-de-arquivo} sem uso", OBRA) == "Documento de arquivo sem uso"


def test_retrato_traz_so_o_que_o_ato_declara():
    linhas = [
        {"verbo": "acervo", "ato": "apagar", "rotulo": "Apagar {documento-de-arquivo}",
         "volta": "nao", "atalho": "Delete"},
        {"verbo": "acervo", "ato": "retirar", "rotulo": None,
         "volta": "sim — acervo restaurar", "atalho": None},
        {"verbo": "acervo", "ato": "ler", "rotulo": None, "volta": None, "atalho": None}]
    r = retrato.retrato(linhas, OBRA)
    assert r["esquema"] == "retrato-ferramental/1"
    assert r["atos"] == {
        "acervo apagar": {"rotulo": "Apagar documento de arquivo",
                          "objeto": ["documento-de-arquivo"], "volta": {"desfaz": False},
                          "atalho": "Delete"},
        "acervo retirar": {"volta": {"desfaz": True, "como": "acervo restaurar"}},
        "acervo ler": {}}
    assert r["avisos"] == []


def test_sha_muda_com_o_cabecalho_e_com_o_rotulo_do_conceito_e_so_entao():
    linhas = [{"verbo": "v", "ato": "a", "rotulo": "Abrir {pdp}", "volta": "nao", "atalho": None}]
    base = retrato.retrato(linhas, OBRA)["sha"]
    assert retrato.retrato(list(linhas), dict(OBRA))["sha"] == base
    assert retrato.retrato([dict(linhas[0], volta="sim — fecha")], OBRA)["sha"] != base
    assert retrato.retrato(linhas, {"pdp": "Politica"})["sha"] != base
    # conceito alheio ao retrato nao mexe no sha
    assert retrato.retrato(linhas, dict(OBRA, outro="Outro"))["sha"] == base


def test_conceito_sem_rotulo_no_tesauro_derruba_a_emissao():
    linhas = [{"verbo": "v", "ato": "a", "rotulo": "Abrir {sumiu}", "volta": None, "atalho": None}]
    with pytest.raises(SystemExit) as e:
        retrato.retrato(linhas, {})
    assert e.value.code == 3


def test_atalho_repetido_vira_aviso():
    linhas = [{"verbo": "v", "ato": "a", "rotulo": None, "volta": None, "atalho": "x"},
              {"verbo": "w", "ato": "b", "rotulo": None, "volta": None, "atalho": "x"}]
    assert retrato.retrato(linhas, {})["avisos"] == ["atalho x repetido em v a, w b (unico em toda face)"]


def test_main_emite_json_em_stdout(monkeypatch, capsys):
    linhas = [{"verbo": "v", "ato": "a", "rotulo": "Abrir", "volta": "nao", "atalho": None}]
    monkeypatch.setattr(retrato, "le_atos", lambda: linhas)
    monkeypatch.setattr(retrato, "le_conceitos", lambda slugs: {})
    assert retrato.main(["--retrato", "--json"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert saida["atos"]["v a"] == {"rotulo": "Abrir", "volta": {"desfaz": False}}
    assert len(saida["sha"]) == 64


def test_main_sem_retrato_ou_com_opcao_desconhecida_e_uso():
    for argv in ([], ["--retrato", "--guardar"]):
        with pytest.raises(SystemExit) as e:
            retrato.main(argv)
        assert e.value.code == 2
