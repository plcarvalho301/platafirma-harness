"""`descansar fita` aponta as candidatas de poda do caderno do chapeu tocado (card #3498).

O que se trava (arq:0120 §8 e §10.3): tres conferencias nas vigentes do chapeu tocado
(duplicata do canone, tombamento entre chapeus da cadeira, referencia morta), cada uma que cai
vira `mesa apontar`, e nada se retira nem se tomba pela maquina. O aceite do card: num caderno de
fixture com uma entrada de cada tipo, exatamente tres candidatas; entrada sa nao e apontada.
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("descansar_poda_bin", str(REPO_ROOT / "bin" / "descansar"))
spec = importlib.util.spec_from_loader("descansar_poda_bin", loader)
assert spec and spec.loader
descansar = importlib.util.module_from_spec(spec)
loader.exec_module(descansar)

DUPLICADA = "Migracao de schema recebe o maior numero da pasta mais um e e idempotente"
PAR_A = "Todo fake de teste nasce de um retorno real colado da API, porque o fake esconde o formato real"
PAR_B = "Fake de teste que devolve o campo esperado esconde o formato real: todo fake de API nasce de retorno real colado"
MORTA = "Ate a #3001 sair, o fecho do parecer vai num comentario a parte"
SA = "Juiz-modelo do mesmo modelo concorda com o gerador; a conferencia fica com modelo diferente"

CADERNO = [
    {"id": 1, "chapeu": "contexto", "categoria": "licao", "texto": DUPLICADA, "caso": "#3200", "candidata": None},
    {"id": 2, "chapeu": "contexto", "categoria": "licao", "texto": PAR_A, "caso": "#3201", "candidata": None},
    {"id": 3, "chapeu": "contexto", "categoria": "licao", "texto": MORTA, "caso": "#3202", "candidata": None},
    {"id": 4, "chapeu": "contexto", "categoria": "licao", "texto": SA, "caso": "#3001", "candidata": None},
    {"id": 5, "chapeu": "engenharia-de-harness", "categoria": "licao", "texto": PAR_B, "caso": "#3349",
     "candidata": None},
]

# Stubs dos verbos irmaos (PF_BIN): mesa serve o caderno e grava cada apontar; motor diz que so a
# entrada DUPLICADA repete o canone (e que um parecer, material, parece com a sa); tarefas diz
# que #3001 entregou; conferir acha todo verbo.
STUB_MESA = """#!/bin/sh
if [ "$1" = caderno ] && [ "$2" = --json ]; then cat "$STUB_DIR/caderno.json"; exit 0; fi
if [ "$1" = apontar ]; then echo "$2|$4" >> "$STUB_DIR/apontadas"; echo "apontada"; exit 0; fi
exit 2
"""
STUB_MOTOR = """#!/bin/sh
case "$4" in
  Migracao*) echo '{"fontes":[{"arquivo":"guia ddl-e-migracao","sim":0.73}]}' ;;
  Juiz*) echo '{"fontes":[{"arquivo":"parecer 2026-08-08-julgamento","sim":0.91},{"arquivo":"arq:0012","sim":0.55}]}' ;;
  *) echo '{"fontes":[{"arquivo":"arq:0120","sim":0.60}]}' ;;
esac
"""
STUB_TAREFAS = """#!/bin/sh
case "$2" in
  3001) printf '# titulo\\n#3001 \\302\\267 story \\302\\267 Entregue (terminal) \\302\\267 cadeira: ia\\n' ;;
  3002) printf '# titulo\\n#3002 \\302\\267 story \\302\\267 Englobada (terminal) \\302\\267 cadeira: ia\\n' ;;
  3003) echo "item 3003 foi apagado" >&2; exit 1 ;;
  *) printf '# titulo\\n#%s \\302\\267 story \\302\\267 Em execu\\303\\247\\303\\243o (delivery)\\n' "$2" ;;
esac
"""
STUB_CONFERIR = """#!/bin/sh
case "$3" in sumido) echo "nao-existe: verbo sumido"; exit 1 ;; esac
echo "existe: verbo $3"; exit 0
"""


@pytest.fixture()
def stubs(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "bin"
    d.mkdir()
    for nome, corpo in (("mesa", STUB_MESA), ("motor", STUB_MOTOR), ("tarefas", STUB_TAREFAS),
                        ("conferir", STUB_CONFERIR)):
        f = d / nome
        f.write_text(corpo, encoding="utf-8")
        f.chmod(0o755)
    (tmp_path / "caderno.json").write_text(json.dumps(CADERNO), encoding="utf-8")
    monkeypatch.setenv("PF_BIN", str(d))
    monkeypatch.setenv("STUB_DIR", str(tmp_path))
    return tmp_path


def _apontadas(stubs: Path) -> dict:
    f = stubs / "apontadas"
    if not f.exists():
        return {}
    return dict(l.split("|", 1) for l in f.read_text(encoding="utf-8").splitlines())


def test_aceite_tres_candidatas_uma_de_cada_tipo_e_a_sa_fica(stubs):
    linhas = descansar.aponta_candidatas({"contexto"})
    ap = _apontadas(stubs)
    assert set(ap) == {"c1", "c2", "c3"}, "exatamente tres; a sa (c4) nao, o par fora do tocado (c5) nao"
    assert ap["c1"] == "duplicata do cânone guia ddl-e-migracao (sim 0.73)"
    assert ap["c2"].startswith("tombamento: par c5 em engenharia-de-harness")
    assert ap["c3"] == "referência morta #3001 (entregue)"
    assert linhas[0] == "  3 candidata(s) nova(s) em contexto"


def test_os_dois_chapeus_tocados_apontam_os_dois_lados_do_par(stubs):
    descansar.aponta_candidatas({"contexto", "engenharia-de-harness"})
    ap = _apontadas(stubs)
    assert "tombamento: par c2 em contexto" in ap["c5"]


def test_ja_candidata_nao_se_reaponta(stubs):
    caderno = [dict(CADERNO[0], candidata="duplicata do cânone guia x")]
    (stubs / "caderno.json").write_text(json.dumps(caderno), encoding="utf-8")
    linhas = descansar.aponta_candidatas({"contexto"})
    assert _apontadas(stubs) == {}
    assert "1 já apontada(s) esperando a cadeira" in linhas[0]


def test_parecer_e_material_nao_canone(stubs):
    assert descansar.duplicata_do_canone(SA) is None, "sim 0,91 contra parecer nao e duplicata"
    assert descansar.duplicata_do_canone(DUPLICADA) == "guia ddl-e-migracao (sim 0.73)"


def test_card_terminal_sem_herdeiro_e_morto_englobado_tem_herdeiro(stubs):
    cache = {}
    assert descansar.estado_card("3001", cache) == ("morto", "entregue")
    assert descansar.estado_card("3002", cache)[0] == "vivo"
    assert descansar.estado_card("3003", cache) == ("morto", "apagado")
    assert descansar.estado_card("3498", cache)[0] == "vivo"


def test_referencia_morta_le_o_texto_verbo_e_chapeu(stubs):
    texto = ("Rodar `sumido abrir x` e `mesa caderno contexto`, ou `git push`; ver chapeu:ia/extinto "
             "e chapeu:ia/contexto; #2856 linha 104")
    mortas = descansar.referencias_mortas(
        texto, {}, declarados_de=lambda cad: ({"contexto", "agente"}, None))
    assert mortas == ["verbo sumido", "chapéu ia/extinto"], "git fica fora; #2856 vivo"


def test_semelhanca_separa_a_mesma_licao_do_mesmo_assunto():
    assert descansar.semelhanca(PAR_A, PAR_B) >= descansar.LIMIAR_PAR
    assert descansar.semelhanca(PAR_A, SA) < descansar.LIMIAR_PAR


def test_chapeus_tocados_do_ambiente_e_do_log(monkeypatch):
    monkeypatch.setenv("PF_CHAPEU", "agente")
    regs = [{"tool": "persona", "ato": "ler", "args": "ia --chapeu contexto"},
            {"tool": "persona", "ato": "ler", "args": "dados --chapeu curadoria"},
            {"tool": "mesa", "ato": "caderno", "args": "engenharia-de-harness"},
            {"tool": "mesa", "ato": "caderno", "args": "--chapeu recuperacao"},
            {"tool": "mesa", "ato": "apontar", "args": "c12 --motivo x"}]
    assert descansar.chapeus_tocados("ia", regs) == {
        "agente", "contexto", "engenharia-de-harness", "recuperacao"}


def test_sem_chapeu_tocado_nao_confere_nada(monkeypatch):
    monkeypatch.delenv("PF_CHAPEU", raising=False)
    assert descansar.chapeus_tocados("ia", None) == set()
    assert "nenhum chapéu tocado" in descansar.aponta_candidatas(set())[0]


def test_o_que_foi_ao_debito_sai_do_caderno_com_a_linha(stubs):
    """#3501: o debito ja e a morada duravel; a poda retira, nao aponta."""
    caderno = [
        {"id": 7, "chapeu": "agente", "categoria": "licao", "candidata": None, "caso": "28/09",
         "texto": "Em pesquisar consultar a consulta vai num argumento so (débito #2856 linha 104)"},
        {"id": 8, "chapeu": "agente", "categoria": "licao", "candidata": "tombamento: par c1",
         "caso": "02/10", "texto": "Contorno do motor: ver #2856, linha 12"},
        {"id": 9, "chapeu": "agente", "categoria": "licao", "candidata": None, "caso": "#3155",
         "texto": SA},
    ]
    retiradas = {}
    linhas = descansar.aponta_candidatas(
        {"agente"}, entradas=caderno, canone=lambda t: None, mortas=lambda t, c: [],
        apontar=lambda eid, m: pytest.fail("nada a apontar"),
        retirar=lambda eid, m: retiradas.setdefault(eid, m) is not None)
    assert retiradas == {7: "foi ao débito técnico: #2856 linha 104",
                         8: "foi ao débito técnico: #2856 linha 12"}, "já candidata também sai"
    assert "2 retirada(s) por já ter morada durável" in linhas[0]
    assert any("agente/c7: retirada, foi ao débito técnico (#2856 linha 104)" in l for l in linhas)


def test_balde_sem_linha_nao_retira():
    assert descansar.foi_ao_debito("o balde #2856 tem a regra") is None


def test_caderno_mudo_sai_declarado(stubs):
    (stubs / "caderno.json").write_text("nao e json", encoding="utf-8")
    assert "NAO MEDIDO" in descansar.aponta_candidatas({"contexto"})[0]
