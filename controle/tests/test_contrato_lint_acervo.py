"""test_contrato_lint_acervo — `lint acervo` sobre a lista antipadroes-do-acervo (card #3161).

Tudo em fixture: a lista vem de um acervo falso (PF_LINT_ACERVO) e as linhas de obra e
conceito de um psql falso (PF_LINT_ACERVO_PSQL). O caso nao muda de cor quando o acervo
real e curado.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[2]
LINT_BIN = HARNESS_ROOT / "bin" / "lint"
sys.path.insert(0, str(HARNESS_ROOT / "bin"))

from _lint import acervo as ac  # noqa: E402
from _lint.lista import parse_lista  # noqa: E402


def _linha(cid, fere, det, sev, cura):
    return f"| {cid} | {fere} | lei | {det} | {sev} | {cura} |"


def lista_texto(trocar=None):
    """Lista na forma servida, com os detectores literais da rev 4."""
    trocar = trocar or {}
    sev = {"A1": "bloqueante", "A2": "bloqueante", "A3": "bloqueante", "A4": "bloqueante",
           "T2": "bloqueante", "B1": "bloqueante", "B2": "bloqueante", "B6": "bloqueante",
           "D7": "bloqueante", "D8": "bloqueante"}
    linhas = [_linha(c, f"fere {c}", trocar.get(c, d), sev.get(c, "aviso"), "K1")
              for c, d in ac.DETECTORES.items()]
    linhas += [_linha("C2", "sem lastro", "nenhum trecho da obra casa o rótulo", "aviso", "K9"),
               _linha("A5", "versões", "leitura", "aviso", "K3")]
    return (
        "força não declarada · vigente — lista-de-verificacao antipadroes-do-acervo · Antipadrões\n"
        "# Antipadrões do acervo\n\nEspécie: lista-de-verificacao\nRev: 4\n\n## Critérios\n\n"
        "| # | antipadrão | lei da casa | detector | severidade | cura |\n|---|---|---|---|---|---|\n"
        + "\n".join(linhas) + "\n\n## Contrapontos que o detector já respeita\n\n"
        "- **Organismos de normalização que T2 aceita:** ISO, IEC, ABNT,\n  BSI. A lista cresce por emenda.\n"
        "- **D7 não conta palavra funcional:** de, da, do, to, be, the. Anglicismo passa.\n"
    )


def obra(**kw):
    base = {"id": "o1", "titulo": "Um título qualquer", "anotacao": None, "especie": "livro",
            "familia": "academico-editorial", "tem_especie": True, "emitido_por": ["Fulano"],
            "publicacao": "2020", "id_canonico": None, "incide_emitido_por": "comporta",
            "incide_publicacao": "comporta", "incide_id_canonico": "comporta",
            "tem_dominio": True, "tem_subdominio": True, "n_conceitos": 3, "deriva": None}
    base.update(kw)
    return base


def conceito(**kw):
    base = {"slug": "governanca-de-dados", "outros_rotulos": ["gd"], "tem_mais_amplo": True,
            "tem_filho": False, "tem_aresta": False, "n_obras_vivas": 4}
    base.update(kw)
    return base


ESQUEMA = {"incidencia": True, "derivacao": True}


def _medir(obras=(), conceitos=(), esquema=ESQUEMA, texto=None):
    lista = parse_lista(texto or lista_texto())
    return ac.medir(lista, esquema, list(obras), list(conceitos))


def _ids(m, cid):
    return [a["alvo"] for a in m["apontamentos"] if a["id"] == cid]


# ---------- predicados, contra o texto do detector ----------

@pytest.mark.parametrize("titulo,esperado", [
    ("relatorio_final-v2", True), ("Relatório final", False), ("fukuyama2013", False)])
def test_a1_nome_de_arquivo(titulo, esperado):
    assert ac.a1(obra(titulo=titulo)) is esperado


def test_a1_a3_a4_respeitam_titulo_conferido():
    marca = "nota [B-titulo: conferido] ok"
    for f, t in ((ac.a1, "x-y"), (ac.a3, "COBIT"), (ac.a4, "GOVERNANÇA DE DADOS")):
        assert f(obra(titulo=t))
        assert not f(obra(titulo=t, anotacao=marca))


@pytest.mark.parametrize("titulo", [
    "Livro -- Autor -- 2019", "Livro _ Autor", "Livro (Anna's Archive)", "x libgen.rs",
    "z-lib.org Livro", "Livro 0123456789abcdef0123456789ABCDEF"])
def test_a2_registro_de_catalogo(titulo):
    assert ac.a2(obra(titulo=titulo))


def test_a3_chave_de_citacao():
    assert ac.a3(obra(titulo="fukuyama2013"))
    assert not ac.a3(obra(titulo="fukuyama-2013"))  # esse e A1
    assert not ac.a3(obra(titulo=None))


def test_a4_caixa_alta_fora_de_ato_normativo_e_mais():
    assert ac.a4(obra(titulo="GOVERNANÇA DE DADOS"))
    assert not ac.a4(obra(titulo="GOVERNANÇA DE DADOS", familia="ato-normativo"))
    assert not ac.a4(obra(titulo="LGPD ANOTADA"))  # menos de 12 letras
    assert ac.a4(obra(titulo="Lei 1+1", familia="ato-normativo"))  # o + continua pegando


def test_t2_emissor_fora_dos_organismos_da_lista():
    orgs = ac.organismos(lista_texto())
    assert orgs == ["ISO", "IEC", "ABNT", "BSI"]
    assert ac.t2(obra(especie="norma-tecnica", emitido_por=["CIS"]), orgs)
    assert ac.t2(obra(especie="norma-tecnica", emitido_por=[]), orgs)
    assert not ac.t2(obra(especie="norma-tecnica", emitido_por=["ISO/IEC JTC 1"]), orgs)
    assert not ac.t2(obra(especie="padrao", emitido_por=["CIS"]), orgs)


def test_b1_b2_pela_incidencia_da_especie():
    o = obra(incide_id_canonico="exige", id_canonico=None, incide_publicacao="nao-comporta",
             publicacao="2020", incide_emitido_por="exige", emitido_por=[])
    assert ac.b1(o) == ["emitido_por", "id_canonico"]
    assert ac.b2(o) == ["publicacao"]


def test_b6_lista_sem_derivacao():
    assert ac.b6(obra(especie="lista-de-verificacao", deriva=False))
    assert not ac.b6(obra(especie="lista-de-verificacao", deriva=True))


def test_d7_d8_slug():
    funcionais = ac.palavras_funcionais(lista_texto())
    assert ac.d7(conceito(slug="indice-de-maturidade-de-governanca-digital"), funcionais)
    assert not ac.d7(conceito(slug="job-to-be-done"), funcionais)
    assert ac.d8(conceito(slug="dado-vs-informacao"))
    assert not ac.d8(conceito(slug="deteccao-como-codigo"))


# ---------- medida ----------

def test_medir_conta_por_criterio_e_severidade_vem_da_lista():
    m = _medir(obras=[obra(id="a", titulo="arquivo_1"), obra(id="b", n_conceitos=0)],
               conceitos=[conceito(slug="a-vs-b", outros_rotulos=[])])
    assert _ids(m, "A1") == ["a"]
    assert _ids(m, "C1") == ["b"]
    assert _ids(m, "D8") == ["a-vs-b"] and _ids(m, "D3") == ["a-vs-b"]
    assert m["criterios"]["A1"]["severidade"] == "bloqueante"
    assert m["criterios"]["C1"]["severidade"] == "aviso"
    assert m["criterios"]["T2"]["n"] == 0  # bloqueante limpo aparece com zero
    assert "A5" not in m["criterios"]  # leitura nao roda
    assert [x["id"] for x in m["nao_rodou"]] == ["C2"]


def test_b1_b2_b6_acusam_zero_sem_o_esquema():
    o = obra(incide_id_canonico="exige", especie="lista-de-verificacao", deriva=None)
    m = _medir(obras=[o], esquema={"incidencia": False, "derivacao": False})
    for cid in ("B1", "B2", "B6"):
        assert m["criterios"][cid]["n"] == 0 and "schema" in m["criterios"][cid]["nota"]


def test_detector_divergente_da_lista_nao_roda_e_torna_indeterminavel(capsys):
    texto = lista_texto(trocar={"A1": "`titulo` sem espaço"})
    m = _medir(obras=[obra(titulo="x_y")], texto=texto)
    assert "A1" not in m["criterios"]
    assert any(x["id"] == "A1" and "mudou" in x["motivo"] for x in m["nao_rodou"])
    assert ac.relatorio(m, 5) == 5


def test_relatorio_exit_1_so_com_bloqueante(capsys):
    assert ac.relatorio(_medir(obras=[obra(n_conceitos=0)]), 4) == 0  # so aviso
    assert ac.relatorio(_medir(obras=[obra(titulo="a_b")]), 4) == 1
    saida = capsys.readouterr().out.splitlines()
    assert saida[-1].strip().startswith("A1: obra o1")


# ---------- CLI ----------

@pytest.fixture
def ambiente(tmp_path):
    lista = tmp_path / "lista.md"
    lista.write_text(lista_texto())
    acervo = tmp_path / "acervo"
    acervo.write_text("#!/bin/sh\n"
                      '[ "$1 $2 $3 $4" = "ler casa lista-de-verificacao antipadroes-do-acervo" ] '
                      f'&& exec cat "{lista}"\nexit 1\n')
    acervo.chmod(0o755)
    dados = {"esquema": ESQUEMA,
             "obras": [obra(id="o-a", titulo="COBIT2019"), obra(id="o-b")],
             "conceitos": [conceito(slug="antes-vs-depois")]}
    (tmp_path / "dados.json").write_text(json.dumps(dados))
    psql = tmp_path / "psql"
    psql.write_text(
        f"#!{sys.executable}\nimport json, sys\n"
        f"d = json.load(open({str(tmp_path / 'dados.json')!r}))\nsql = sys.stdin.read()\n"
        "k = 'esquema' if 'information_schema' in sql else 'obras' if 'from acervo.obra o' in sql else 'conceitos'\n"
        "print(json.dumps(d[k]))\n")
    psql.chmod(0o755)
    return {"PF_LINT_ACERVO": str(acervo), "PF_LINT_ACERVO_PSQL": str(psql)}


def _lint(*args, env):
    return subprocess.run([str(LINT_BIN), *args], capture_output=True, text=True,
                          env={**os.environ, **env})


def test_cli_acervo_ancora_contagem_e_exit(ambiente):
    p = _lint("acervo", env=ambiente)
    assert p.returncode == 1, p.stdout + p.stderr
    linhas = p.stdout.splitlines()
    assert linhas[0] == "«lint acervo firma: 2 apontamentos, 2 bloqueantes — antipadroes-do-acervo@rev4»"
    assert any(ln.split()[:3] == ["A3", "bloqueante", "1"] for ln in linhas)
    assert any(ln.split()[:3] == ["D8", "bloqueante", "1"] for ln in linhas)


def test_cli_acervo_json_resumo(ambiente):
    p = _lint("acervo", "--json", "--resumo", env=ambiente)
    d = json.loads(p.stdout)
    assert d["rev"] == 4 and d["exit"] == 1 and "apontamentos" not in d
    assert d["criterios"]["A3"]["n"] == 1 and d["criterios"]["A1"]["n"] == 0


def test_cli_acervo_lista_ausente_exit_5(ambiente, tmp_path):
    vazio = tmp_path / "vazio"
    vazio.write_text("#!/bin/sh\nexit 1\n")
    vazio.chmod(0o755)
    p = _lint("acervo", env={**ambiente, "PF_LINT_ACERVO": str(vazio)})
    assert p.returncode == 5 and "antipadroes-do-acervo" in p.stderr


def test_cli_acervo_sem_transporte_exit_3(ambiente):
    p = _lint("acervo", env={**ambiente, "PF_LINT_ACERVO_PSQL": "/nao/existe"})
    assert p.returncode == 3 and "transporte" in p.stderr
