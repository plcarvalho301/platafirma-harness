"""`acervo gerar` (débito 340 do balde #2856, card #3761): um verbo da porta roda `python -m gerador` na
bancada de `platafirma-conhecimento` e passa o `catalogo.sql` dele ao banco numa transação só.

Roda de verdade o que dá: o python do rag é o do próprio teste (RAG_PYTHON), a bancada é uma árvore de
arquivos com um `gerador` de brinquedo que escreve o que o gerador escreve (a linha `gerador: …`, o
`catalogo.sql` na pasta de `--saida` e a saída 0, 1 ou 5), e o banco é um dublê só no ponto em que o SQL sai
do processo (`aplica`). O que o brinquedo não prova é o gerador, que tem a suíte dele em
`platafirma-conhecimento` (rag/tests/test_gerador_*.py), nem o SQL no banco, que a migração 111 já provou."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin" / "acervo"
GERAR = RAIZ / "bin" / "_acervo" / "gerar"
REPO = "platafirma-conhecimento"

SQL = (
    "SELECT set_config('pf.gerador', 'on', true);\n"
    "INSERT INTO acervo.entidade_classe (slug) VALUES ('a')\nON CONFLICT (slug) DO NOTHING;\n"
    "INSERT INTO acervo.entidade_classe (slug) VALUES ('b')\nON CONFLICT (slug) DO NOTHING;\n"
    "UPDATE acervo.entidade_classe SET classe_mae = NULL WHERE slug = 'a';\n"
)

BRINQUEDO = '''\
import sys
from pathlib import Path

saida = Path(sys.argv[sys.argv.index("--saida") + 1])
saida.mkdir(parents=True, exist_ok=True)
if %(escreve)s:
    (saida / "catalogo.sql").write_text(%(sql)r, encoding="utf-8")
print("gerador: versão abc · 2 entidades")
print("gerador: tripla repetida", file=sys.stderr)
sys.exit(%(saida)d)
'''


def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_gerar_teste", str(GERAR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _bancada(raiz: Path, chave: str, saida: int | None = 0, escreve: bool = True) -> Path:
    wt = raiz / "wt" / REPO / "dados" / chave
    (wt / ".git").mkdir(parents=True)
    if saida is not None:
        gerador = wt / "ontologia" / "gerador"
        gerador.mkdir(parents=True)
        (gerador / "__init__.py").write_text("", encoding="utf-8")
        (gerador / "__main__.py").write_text(
            BRINQUEDO % {"saida": saida, "sql": SQL, "escreve": escreve}, encoding="utf-8")
    return wt


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    monkeypatch.setenv("PF_CADEIRA", "dados")
    monkeypatch.setenv("RAG_PYTHON", sys.executable)
    monkeypatch.delenv("PF_SESSAO", raising=False)
    return tmp_path


@pytest.fixture
def banco(monkeypatch):
    """Dublê do psql: guarda o que o ato mandou e devolve o que o teste pediu."""
    visto = {"chamadas": [], "retorno": (0, "on")}
    mod = _modulo()

    def aplica(sql, apply, docker_host):
        visto["chamadas"].append((sql, apply))
        return visto["retorno"]

    mod.aplica = aplica
    visto["mod"] = mod
    return visto


def test_plano_seco_roda_o_sql_e_diz_que_desfez(mundo, banco, capsys):
    wt = _bancada(mundo, "3761-a")
    assert banco["mod"].main([]) == 0
    assert banco["chamadas"] == [(SQL, False)]
    saida = capsys.readouterr().out
    assert "gerador: versão abc" in saida and f"bancada: {wt}" in saida
    assert saida.splitlines()[-1].startswith("gerar: plano seco, 2 linhas de entidade") and "desfeita" in saida


def test_apply_grava_e_diz_quantas_linhas(mundo, banco, capsys):
    _bancada(mundo, "3761-a")
    assert banco["mod"].main(["--apply"]) == 0
    assert banco["chamadas"] == [(SQL, True)]
    assert capsys.readouterr().out.splitlines()[-1] == "gerar: 2 linhas de entidade gravadas em acervo.entidade_classe"


def test_geracao_que_reprova_sai_como_o_gerador_e_nao_toca_o_banco(mundo, banco, capsys):
    _bancada(mundo, "3761-a", saida=1)
    assert banco["mod"].main(["--apply"]) == 1
    assert banco["chamadas"] == []
    assert "tripla repetida" in capsys.readouterr().err


def test_gerador_que_nao_olhou_sai_5_sem_tocar_o_banco(mundo, banco):
    _bancada(mundo, "3761-a", saida=5)
    assert banco["mod"].main([]) == 5 and banco["chamadas"] == []


def test_gerador_sem_catalogo_sql_recusa_nomeando_a_migracao_111(mundo, banco, capsys):
    _bancada(mundo, "3761-a", escreve=False)
    with pytest.raises(SystemExit) as e:
        banco["mod"].main(["--apply"])
    assert e.value.code == 3 and "111" in capsys.readouterr().err and banco["chamadas"] == []


def test_sql_com_erro_sai_1_e_diz_que_nada_foi_gravado(mundo, banco, capsys):
    _bancada(mundo, "3761-a")
    banco["retorno"] = (1, "ERROR:  gerador: 1 slug(s) de shape já são registro ou vocabulário no catálogo")
    assert banco["mod"].main(["--apply"]) == 1
    erro = capsys.readouterr().err
    assert "já são registro ou vocabulário" in erro and "nada foi gravado" in erro


def test_banco_fora_do_ar_sai_5(mundo, banco):
    _bancada(mundo, "3761-a")
    banco["retorno"] = (5, "Error response from daemon: No such container: rag-extractor-pg")
    assert banco["mod"].main([]) == 5


def test_sem_o_gerador_na_bancada_recusa_com_o_nome_do_ato(mundo, capsys):
    _bancada(mundo, "3194-a", saida=None)
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    assert e.value.code == 3
    assert capsys.readouterr().err.startswith("acervo gerar:")


def test_duas_bancadas_sem_chave_recusa_e_chave_escolhe(mundo, banco, capsys):
    _bancada(mundo, "3194-a")
    escolhida = _bancada(mundo, "3761-a")
    with pytest.raises(SystemExit) as e:
        banco["mod"].main([])
    assert e.value.code == 2 and "--bancada" in capsys.readouterr().err
    assert banco["mod"].main(["--bancada", "3761-a"]) == 0
    assert f"bancada: {escolhida}" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["--outra"], ["--bancada"], ["--bancada", ""], ["extra"]])
def test_uso_errado_sai_2(mundo, capsys, argv):
    assert _modulo().main(argv) == 2
    assert capsys.readouterr().err.startswith("uso: acervo gerar")


def test_o_sql_vai_ao_psql_dentro_de_uma_transacao(monkeypatch):
    """O que sai do processo: BEGIN antes, ROLLBACK no plano seco e COMMIT com --apply, e ON_ERROR_STOP."""
    mod = _modulo()
    vistos = []

    def falso(cmd, **kw):
        vistos.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0, stdout="on\n", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", falso)
    assert mod.aplica(SQL, False, "unix:///x")[0] == 0
    assert mod.aplica(SQL, True, "unix:///x")[0] == 0
    seco, grava = vistos[0][1]["input"], vistos[1][1]["input"]
    assert seco.startswith("BEGIN;\n") and seco.rstrip().endswith("ROLLBACK;") and "COMMIT" not in seco
    assert grava.startswith("BEGIN;\n") and grava.rstrip().endswith("COMMIT;") and "ROLLBACK" not in grava
    cmd = vistos[0][0]
    assert cmd[:5] == ["docker", "exec", "-i", "rag-extractor-pg", "psql"] and "ON_ERROR_STOP=1" in cmd
    assert vistos[0][1]["env"]["DOCKER_HOST"]


@pytest.mark.parametrize("stderr,esperado", [
    ("psql: error: connection to server failed: Connection refused", 5),
    ("Error response from daemon: No such container: rag-extractor-pg", 5),
    ("ERROR:  new row violates check constraint", 1),
])
def test_erro_do_psql_vira_1_ou_5_conforme_o_banco_tenha_respondido(monkeypatch, stderr, esperado):
    mod = _modulo()
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 3, stdout="", stderr=stderr))
    assert mod.aplica(SQL, True, "unix:///x")[0] == esperado


def test_a_contagem_e_uma_linha_de_entidade_por_insert():
    assert _modulo().contagem(SQL) == 2


def test_pela_porta_o_ato_existe_e_o_cabecalho_o_declara():
    r = subprocess.run([str(BIN), "gerar", "--outra"], capture_output=True, text=True)
    assert r.returncode == 2 and "uso: acervo gerar" in r.stderr
    cabecalho = BIN.read_text(encoding="utf-8")
    assert "gerar (escrita, acervo)" in cabecalho
    assert "# le: gerar=" in cabecalho and "# escreve: gerar=" in cabecalho
    desconhecido = subprocess.run([str(BIN), "nao-existe"], capture_output=True, text=True)
    assert "medir, gerar." in desconhecido.stderr
