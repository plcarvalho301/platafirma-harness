"""`motor rag lintar` e o lint sobre as 20 do piloto da escada (card #3360, passo 7).

O piso de palavras funcionais (consulta.PISO_FUNCIONAIS) é um chute declarado; o que ele pega do que as
cadeiras de fato perguntaram se mede aqui, nas 20 do piloto (avaliacao/escada-sentido-v1.jsonl, copiadas do
log e versionadas), e no verbo `lintar`, que roda o mesmo lint sobre o log inteiro, só leitura.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "lib"))
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import consulta  # noqa: E402

# posicao no piloto -> veredito do lint no piso de 0,15. «passa» não quer dizer «é boa consulta»: o lint só vê a
# forma (assuntos juntos, ausência de palavras funcionais). Um título em inglês com «of the» tem forma de frase.
VEREDITO_NO_PISO_0_15 = {
    1: "frase", 2: "assuntos", 3: "frase", 4: "frase", 5: "passa", 6: "passa", 7: "assuntos", 8: "passa",
    9: "frase", 10: "frase", 11: "passa", 12: "passa", 13: "frase", 14: "frase", 15: "assuntos", 16: "frase",
    17: "frase", 18: "frase", 19: "frase", 20: "frase",
}


def _piloto():
    with open(RAIZ / "avaliacao" / "escada-sentido-v1.jsonl", encoding="utf-8") as f:
        linhas = [json.loads(l) for l in f if l.strip()]
    return [c for c in linhas if c["papel"] == "piloto"]


def _curta(causa):
    return "assuntos" if consulta.CAUSA_ASSUNTOS in causa else "frase" if causa == consulta.CAUSA_FRASE else "lingua"


def test_o_piloto_tem_as_20_e_a_posicao_confere():
    assert [c["posicao"] for c in _piloto()] == list(range(1, 21))


def test_lint_das_20_do_piloto_uma_a_uma():
    obtido = {}
    for c in _piloto():
        v = consulta.lint(c["pergunta"])
        obtido[c["posicao"]] = "passa" if v is None else _curta(v[0])
    assert obtido == VEREDITO_NO_PISO_0_15


def test_as_cinco_com_ponto_e_virgula_saem_todas_por_assuntos():
    com_ponto_e_virgula = [c["posicao"] for c in _piloto() if ";" in c["pergunta"]]
    assert com_ponto_e_virgula == [2, 7, 15]
    assert all(VEREDITO_NO_PISO_0_15[p] == "assuntos" for p in com_ponto_e_virgula)


# --- o verbo, com docker falso -------------------------------------------------------------------

DOCKER_FALSO = """#!{python}
import json, os, sys
sys.stdin.read()
print(json.dumps(json.load(open(os.environ["FAKE_ESTADO"]))["eventos"]))
"""


def _ev(i, pergunta, origem="busca"):
    return {"id": f"{i:08d}-0000-4000-8000-000000000000", "pergunta": pergunta, "origem": origem,
            "criado_em": f"2026-10-0{1 + i % 8} 10:00:00+00"}


EVENTOS = [
    _ev(1, "como o log da porta grava o prompt do dono?"),
    _ev(2, "como o log da porta grava o prompt do dono?"),
    _ev(3, "UTF-8 decoding truncated multibyte sequence byte boundary"),
    _ev(4, "SRE overload cascading failures; golden hammer lava flow; xUnit test smells"),
    _ev(5, "Respondi o gold set todo", "abertura"),
    _ev(6, "OpenID Connect Core copyright notice OpenID Foundation", "abertura"),
    _ev(7, "o que é um espaço vetorial para recuperação", None),
    _ev(8, "what is the abstention floor of the Nemotron generation?"),
    {**_ev(9, "qual piso de abstenção a geração Nemotron usa?"), "necessidade": "qual piso de abstenção a geração Nemotron usa?",
     "pedido": "Card 3360", "chapeu": "engenharia-de-harness", "lint": None,
     "perguntas": ["qual piso de abstenção a geração Nemotron usa?", "Card 3360"]},
]


@pytest.fixture
def lintar(tmp_path):
    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)
    estado = tmp_path / "estado.json"
    estado.write_text(json.dumps({"eventos": EVENTOS}))
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": "http://127.0.0.1:9/search",
        "token_em": "rag/RAG_API_TOKEN", "banco": {"container": "rag-extractor-pg", "db": "rag_extractor", "user": "rag"},
        "ajustes": [], "nao_e_ajuste": {}}}))

    def roda(*args):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "FAKE_ESTADO": str(estado),
               "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", "lintar", *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)

    return roda


def test_lintar_conta_por_origem_e_por_causa(lintar):
    r = lintar("--json")
    assert r.returncode == 0, r.stderr
    rel = json.loads(r.stdout)
    assert rel["eventos"] == 9 and rel["piso"] == consulta.PISO_FUNCIONAIS
    busca = rel["por_origem"]["busca"]
    assert (busca["eventos"], busca["distintas"], busca["passam"]) == (6, 5, 4)
    assert busca["recusadas"] == {"frase": 1, "assuntos": 1}
    assert busca["ingles"] == 1, "a pergunta em ingles passa por (a) e (b); (c) a pegaria com pedido em portugues"
    assert rel["por_origem"]["abertura"]["ingles"] == 0
    assert rel["montadas"]["eventos"] == 1
    assert rel["montadas"]["ultimos"][0]["chapeu"] == "engenharia-de-harness"
    assert rel["montadas"]["ultimos"][0]["n_perguntas"] == 2 and rel["montadas"]["ultimos"][0]["pedido"] == "Card 3360"
    assert rel["por_origem"]["nao declarada"]["passam"] == 1
    assert rel["por_origem"]["abertura"]["recusadas"] == {"frase": 1}
    assert rel["por_origem"]["abertura"]["exemplos_recusados"] == ["OpenID Connect Core copyright notice OpenID Foundation"]
    assert [p["veredito"] for p in rel["piloto"]] == [VEREDITO_NO_PISO_0_15[i] for i in range(1, 21)]
    # Com o pedido em portugues a causa de lingua pega as duas em ingles que passavam: 17 recusadas, 3 passam,
    # que e o que o card esperava das 20 (e so se fecha com (c), que o piloto, anterior ao #3345, nao tem como medir).
    assert [p["posicao"] for p in rel["piloto"] if p["veredito_com_pedido_pt"] == "passa"] == [5, 8, 11]
    assert {p["posicao"] for p in rel["piloto"] if p["veredito_com_pedido_pt"] == "lingua"} == {6, 12}


def test_lintar_em_texto_traz_a_tabela_e_o_piloto_uma_a_uma(lintar):
    r = lintar()
    assert r.returncode == 0, r.stderr
    linhas = r.stdout.splitlines()
    assert linhas[0].startswith("lint da consulta sobre 9 eventos do log")
    assert "piloto com pedido em portugues (causa de lingua somada): 17 recusadas, 3 passam: 5, 8, 11" in r.stdout
    assert "eventos com consulta montada (087): 1" in r.stdout and "chapeu=engenharia-de-harness perguntas=2" in r.stdout
    assert any(l.strip().startswith("busca") for l in linhas)
    assert "abertura recusada (prompt do dono: o piso nao pode pegar):" in r.stdout
    assert "piloto: 15 recusadas, 5 passam" in r.stdout
    assert sum(1 for l in linhas if l.startswith("  ") and " palavras · funcionais " in l) == 20


def test_lintar_nao_aceita_outro_argumento(lintar):
    assert lintar("biblioteca").returncode == 2
    assert lintar("--apply").returncode == 2
