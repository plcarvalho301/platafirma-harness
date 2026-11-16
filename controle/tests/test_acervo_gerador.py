"""`acervo gerador` (card #4077): um verbo da porta roda `python -m gerador` de
`outros_repos/conhecimento/ontologia` na bancada de `platafirma-casa-espelho`, sem banco, com a saída numa
pasta temporária. Chamada temporária, por ordem do dono de 01/11/2026.

Roda de verdade o que dá: o python do rag é o do próprio teste (RAG_PYTHON), a bancada é uma árvore de
arquivos com um `gerador` de brinquedo que escreve o que o gerador escreve (a linha `gerador: …`, a DDL na
pasta de `--saida` e a saída 0, 1 ou 5). O que o brinquedo não prova é o gerador, que tem a suíte dele no
repositório de destino."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin" / "acervo"
GERADOR = RAIZ / "bin" / "_acervo" / "gerador"
REPO = "platafirma-casa-espelho"

BRINQUEDO = '''\
import json
import sys
from pathlib import Path

args = sys.argv[1:]
saida = Path(args[args.index("--saida") + 1])
saida.mkdir(parents=True, exist_ok=True)
if %(saida)d == 0:
    (saida / "ddl").mkdir(exist_ok=True)
    (saida / "ddl" / "casa.sql").write_text("CREATE SCHEMA casa;\\n", encoding="utf-8")
    for solto in ("plataforma.ttl", "gerado.ttl", "catalogo.jsonl", "catalogo.sql", "manifesto.json"):
        (saida / solto).write_text("solto\\n", encoding="utf-8")
    (saida / "tabelas").mkdir(exist_ok=True)
    (saida / "tabelas" / "obra.md").write_text("# obra\\n", encoding="utf-8")
    if "--migracao" in args:
        mig = Path(args[args.index("--migracao") + 1])
        mig.parent.mkdir(parents=True, exist_ok=True)
        mig.write_text("-- 149\\nCREATE SCHEMA IF NOT EXISTS casa;\\n", encoding="utf-8")
    (saida / "argv.json").write_text(json.dumps(args), encoding="utf-8")
    print("gerador: versão abc · 2 entidades")
elif %(saida)d == 1:
    print("gerador: reprova: shapes/entidade/gatilho.ttl: categorias cruzadas", file=sys.stderr)
sys.exit(%(saida)d)
'''


def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_gerador_teste", str(GERADOR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _bancada(raiz: Path, chave: str, saida: int | None = 0) -> Path:
    wt = raiz / "wt" / REPO / "dados" / chave
    (wt / ".git").mkdir(parents=True)
    if saida is not None:
        gerador = wt / "outros_repos" / "conhecimento" / "ontologia" / "gerador"
        gerador.mkdir(parents=True)
        (gerador / "__init__.py").write_text("", encoding="utf-8")
        (gerador / "__main__.py").write_text(BRINQUEDO % {"saida": saida}, encoding="utf-8")
    return wt


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    bancada, instancia = tmp_path / "bancada", tmp_path / "instancia"
    bancada.mkdir()
    (instancia / "var" / "tmp").mkdir(parents=True)
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(bancada))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(instancia))
    monkeypatch.setenv("PF_CADEIRA", "dados")
    monkeypatch.setenv("PF_ORDEM_ID", "o-teste")
    monkeypatch.setenv("RAG_PYTHON", sys.executable)
    monkeypatch.delenv("PF_SESSAO", raising=False)
    return {"bancada": bancada, "instancia": instancia}


def test_gera_numa_pasta_temporaria_da_instancia_e_diz_a_ddl(mundo, capsys):
    wt = _bancada(mundo["bancada"], "3972-shapes-v8")
    assert _modulo().main([]) == 0
    saida = capsys.readouterr().out
    assert "gerador: versão abc" in saida and f"bancada: {wt}" in saida
    linha = next(l for l in saida.splitlines() if l.startswith("saida: "))
    pasta = Path(linha[len("saida: "):])
    assert pasta.is_relative_to(mundo["instancia"] / "var" / "tmp" / "o-teste")
    assert (pasta / "ddl" / "casa.sql").is_file()
    assert saida.splitlines()[-1] == "ddl: ddl/casa.sql"


def test_saida_pedida_na_bancada_vale(mundo, capsys):
    _bancada(mundo["bancada"], "3972-shapes-v8")
    pedida = mundo["bancada"] / "rascunho" / "ger"
    assert _modulo().main(["--saida", str(pedida)]) == 0
    assert (pedida / "ddl" / "casa.sql").is_file()
    assert f"saida: {pedida.resolve()}" in capsys.readouterr().out


def test_saida_fora_da_bancada_e_da_instancia_recusa(mundo, tmp_path, capsys):
    _bancada(mundo["bancada"], "3972-shapes-v8")
    with pytest.raises(SystemExit) as e:
        _modulo().main(["--saida", str(tmp_path / "fora")])
    assert e.value.code == 2 and "fora da bancada" in capsys.readouterr().err


def test_gerador_que_reprova_sai_1_com_a_shape(mundo, capsys):
    _bancada(mundo["bancada"], "3972-shapes-v8", saida=1)
    assert _modulo().main([]) == 1
    assert "gatilho.ttl: categorias cruzadas" in capsys.readouterr().err


def test_gerador_que_nao_rodou_sai_5(mundo):
    _bancada(mundo["bancada"], "3972-shapes-v8", saida=5)
    assert _modulo().main([]) == 5


def test_sem_gerador_na_bancada_sai_3_com_o_caminho(mundo, capsys):
    _bancada(mundo["bancada"], "3972-shapes-v8", saida=None)
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    erro = capsys.readouterr().err
    assert e.value.code == 3 and erro.startswith("acervo gerador:")
    assert "outros_repos/conhecimento/ontologia" in erro


def test_bancada_e_do_espelho_e_nao_do_conhecimento(mundo, capsys):
    outra = mundo["bancada"] / "wt" / "platafirma-conhecimento" / "dados" / "x"
    (outra / ".git").mkdir(parents=True)
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    assert e.value.code == 3 and REPO in capsys.readouterr().err


def test_duas_bancadas_sem_chave_recusa_e_chave_escolhe(mundo, capsys):
    _bancada(mundo["bancada"], "a")
    escolhida = _bancada(mundo["bancada"], "b")
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    assert e.value.code == 2 and "--bancada" in capsys.readouterr().err
    assert _modulo().main(["--bancada", "b"]) == 0
    assert f"bancada: {escolhida}" in capsys.readouterr().out


def test_repassa_migracao_na_bancada(mundo, capsys):
    wt = _bancada(mundo["bancada"], "3972-shapes-v8")
    mig = wt / "outros_repos" / "conhecimento" / "rag" / "db" / "init" / "149_schema_casa.sql"
    assert _modulo().main(["--migracao", str(mig)]) == 0
    assert mig.is_file() and "CREATE SCHEMA IF NOT EXISTS casa;" in mig.read_text(encoding="utf-8")


def test_migracao_fora_da_bancada_e_da_instancia_recusa(mundo, tmp_path, capsys):
    _bancada(mundo["bancada"], "3972-shapes-v8")
    with pytest.raises(SystemExit) as e:
        _modulo().main(["--migracao", str(tmp_path / "fora.sql")])
    assert e.value.code == 2 and "fora da bancada" in capsys.readouterr().err


def test_arvore_grava_so_ddl_e_migracao_sem_arquivos_soltos(mundo, capsys):
    wt = _bancada(mundo["bancada"], "3972-shapes-v8")
    ontologia = wt / "outros_repos" / "conhecimento" / "ontologia"
    mig = wt / "outros_repos" / "conhecimento" / "rag" / "db" / "init" / "149_schema_casa.sql"
    assert _modulo().main(["--arvore", "--migracao", str(mig)]) == 0
    saida = capsys.readouterr().out
    assert "arvore: ddl/casa.sql" in saida
    assert (ontologia / "ddl" / "casa.sql").is_file()
    assert mig.is_file()
    for solto in ("plataforma.ttl", "gerado.ttl", "catalogo.jsonl", "catalogo.sql", "manifesto.json", "tabelas"):
        assert not (ontologia / solto).exists()


def test_repassa_opcoes_apos_duplo_traco(mundo, capsys):
    import json

    _bancada(mundo["bancada"], "3972-shapes-v8")
    pedida = mundo["bancada"] / "rascunho" / "extras"
    assert _modulo().main(["--saida", str(pedida), "--", "--shapes", "custom"]) == 0
    argv_gerador = json.loads((pedida / "argv.json").read_text(encoding="utf-8"))
    assert argv_gerador[-2:] == ["--shapes", "custom"]


@pytest.mark.parametrize("argv", [
    ["--outra"], ["--bancada"], ["--saida", ""], ["--saida", "a", "--saida", "b"],
    ["--migracao"], ["--migracao", ""], ["--migracao", "a", "--migracao", "b"],
    ["--arvore", "--arvore"], ["--arvore", "--saida", "a"], ["extra"],
])
def test_uso_errado_sai_2(mundo, capsys, argv):
    assert _modulo().main(argv) == 2
    assert capsys.readouterr().err.startswith("uso: acervo gerador")


def test_o_ato_nao_fala_com_banco():
    texto = GERADOR.read_text(encoding="utf-8")
    assert "psql" not in texto and "docker" not in texto


def test_pela_porta_o_ato_existe_e_o_cabecalho_o_declara():
    r = subprocess.run([str(BIN), "gerador", "--outra"], capture_output=True, text=True)
    assert r.returncode == 2 and "uso: acervo gerador" in r.stderr
    cabecalho = BIN.read_text(encoding="utf-8")
    assert "gerador (escrita, acervo)" in cabecalho
    assert "# le: gerador=" in cabecalho and "# escreve: gerador=" in cabecalho
