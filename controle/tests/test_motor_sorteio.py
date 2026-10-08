"""`motor rag sortear biblioteca` e bin/_motor/sorteio.py (card #3349; padrao protocolo-medicao-rag, «Fonte e filtros»).

A lógica (filtros, estrato, cota por cadeira, ordem sorteada, sha do arquivo) é medida em funções puras. A fiação
do verbo roda de verdade, como subprocesso, com um `docker` falso no PATH (o log, as sessões e a gabarito_versao vêm
de um estado em arquivo) e um /facets falso no loopback. Não prova o SQL contra o Postgres real: a consulta se
confere no ar, pelo plano do verbo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import sorteio  # noqa: E402

S = {c: f"00000000-0000-4000-8000-{i:012d}" for i, c in enumerate(["ia", "dados", "ti", "rara"], 1)}


def ev(i, cadeira="ia", **kw):
    base = {"id": f"{i:08d}-0000-4000-8000-000000000000", "ordem_id": f"o{i}", "pergunta": f"pergunta de sentido número {i} sobre o tema {i}",
            "particao": "biblioteca", "origem": "busca", "sessao_id": S.get(cadeira), "criado_em": f"2026-10-0{1 + i % 8} 10:00:00+00",
            "secao_em_impressao": True}
    return {**base, **kw}


CAD = {v: k for k, v in S.items()}


def pool(n_ia=12, n_dados=8, n_ti=6, n_rara=3):
    out, i = [], 0
    for cad, n in (("ia", n_ia), ("dados", n_dados), ("ti", n_ti), ("rara", n_rara)):
        for _ in range(n):
            i += 1
            out.append(ev(i, cad))
    return out


# --- funções puras ---------------------------------------------------------------------------------------


def test_normalizar_junta_nfc_caixa_e_espaco():
    assert sorteio.normalizar("  Régua  de\tDecisão ") == sorteio.normalizar("REGUA DE DECISAO".replace("REGUA", "Régua").replace("DECISAO", "decisão"))
    assert sorteio.normalizar("é") == sorteio.normalizar("é")


@pytest.mark.parametrize("pergunta,estrato", [
    ("o que diz a arq:0121 sobre a geração", "identificador"),
    ("por que o card #3264 trocou o embedder", "identificador"),
    ("o que a spec motor manda sobre medir", "identificador"),
    ("como decido se um conceito entra no núcleo", "sentido"),
    ("qual a régua para o dono aprovar uma troca", "sentido"),
])
def test_estrato_proposto_pela_forma_da_pergunta(pergunta, estrato):
    assert sorteio.estrato_proposto(pergunta) == estrato


def test_cada_filtro_do_padrao_conta_o_seu_motivo():
    eventos = [
        ev(1, origem="abertura"), ev(2, origem="bench"), ev(3, origem="sombra"), ev(4, origem="autoteste"),
        ev(5, particao="casa"),
        ev(6, particao=None, secao_em_impressao=False),
        ev(7, ordem_id="ord"), ev(8, ordem_id="ord"),
        ev(9, ordem_id=None),
        ev(10, pergunta="  PERGUNTA do bench "),
        ev(11, pergunta="Pergunta repetida"), ev(12, pergunta="pergunta  REPETIDA"),
        ev(13, sessao_id=None),
        ev(14),
    ]
    cand, ex = sorteio.filtrar(eventos, CAD, {sorteio.normalizar("pergunta do bench")})
    assert [c["id"][:8] for c in cand] == ["00000007", "00000011", "00000014"]
    assert ex == Counter({
        "origem abertura": 1, "origem bench": 1, "origem sombra": 1, "origem autoteste": 1, "partição casa": 1,
        "sem partição inferível (sem seção servida da biblioteca)": 1, "reformulação na mesma ordem": 1, "sem ordem_id": 1,
        "igual a pergunta da bateria (gabarito, bench, sombra ou autoteste)": 1, "duplicata por forma normalizada": 1,
        "sem cadeira (sessao_id nulo ou sem linha em sessao.sessao)": 1,
    })


def test_evento_sem_particao_entra_se_serviu_secao_da_biblioteca():
    cand, ex = sorteio.filtrar([ev(1, particao=None, origem=None)], CAD, set())
    assert len(cand) == 1 and not ex


def test_relaxar_ordem_e_cadeira_so_com_a_flag_e_a_cadeira_vira_desconhecida():
    eventos = [ev(1, ordem_id=None, sessao_id=None), ev(2, ordem_id=None)]
    assert sorteio.filtrar(eventos, CAD, set())[0] == []
    cand, ex = sorteio.filtrar(eventos, CAD, set(), aceitar_sem_ordem=True, aceitar_sem_cadeira=True)
    assert [c["cadeira"] for c in cand] == [sorteio.SEM_CADEIRA, "ia"] and not ex


def test_a_primeira_de_cada_ordem_vale_mesmo_que_a_primeira_saia_depois():
    # a primeira da ordem é a do bench de texto; a segunda não "herda" a vaga
    eventos = [ev(1, ordem_id="x", pergunta="igual ao bench"), ev(2, ordem_id="x")]
    cand, ex = sorteio.filtrar(eventos, CAD, {sorteio.normalizar("igual ao bench")})
    assert cand == [] and ex["reformulação na mesma ordem"] == 1


def test_cadeira_com_menos_de_cinco_sai_do_sentido_e_o_identificador_vai_para_o_outro_estrato():
    eventos = pool() + [ev(900 + k, "ti", pergunta=f"o que diz a arq:01{k:02d}") for k in range(3)]
    cand, ex = sorteio.filtrar(eventos, CAD, set())
    sentido, pequenas = sorteio.separar_estratos(cand, ex)
    assert pequenas == ["rara"]
    assert Counter(c["cadeira"] for c in sentido) == {"ia": 12, "dados": 8, "ti": 6}
    assert ex["cadeira com menos de 5 no estrato sentido"] == 3
    assert ex["estrato identificador (rotulado por construção, fora deste sorteio)"] == 3


def test_alocar_proporcional_pelo_maior_resto_e_nunca_acima_do_que_a_cadeira_tem():
    cotas = sorteio.alocar({"a": 300, "b": 100, "c": 7}, 220)
    assert sum(cotas.values()) == 220 and cotas["a"] > cotas["b"] > cotas["c"]
    assert sorteio.alocar({"a": 5, "b": 3}, 220) == {"a": 5, "b": 3}
    assert all(v <= n for v, n in zip(sorteio.alocar({"a": 10, "b": 400}, 220).values(), (10, 400)))


def _grande(n=500):
    return [{"id": f"{i:08d}-0000-4000-8000-000000000000", "cadeira": ("ia", "dados", "ti")[i % 3], "pergunta": f"p{i}",
             "estrato": "sentido"} for i in range(n)]


def test_sortear_220_da_200_principais_20_de_reserva_e_20_de_piloto_nas_primeiras():
    lista = sorteio.sortear(_grande(), "semente")
    assert len(lista) == 220
    assert [c["posicao"] for c in lista] == list(range(1, 221))
    assert Counter(c["papel"] for c in lista) == {"piloto": 20, "principal": 180, "reserva": 20}
    assert all(c["papel"] == "piloto" for c in lista[:20]) and all(c["papel"] == "reserva" for c in lista[200:])
    assert len({c["id"] for c in lista}) == 220
    assert Counter(c["cadeira"] for c in lista).most_common()[0][1] - Counter(c["cadeira"] for c in lista).most_common()[-1][1] <= 1


def test_sortear_e_deterministico_na_semente_e_muda_com_ela():
    a = [c["id"] for c in sorteio.sortear(_grande(), "x")]
    assert a == [c["id"] for c in sorteio.sortear(_grande(), "x")]
    assert a != [c["id"] for c in sorteio.sortear(_grande(), "y")]
    assert a == [c["id"] for c in sorteio.sortear(list(reversed(_grande())), "x")]  # a ordem de entrada não conta


def test_pool_abaixo_do_tamanho_leva_tudo_sem_reserva_e_pool_pequeno_tem_piloto_menor():
    lista = sorteio.sortear(_grande(150), "s")
    assert len(lista) == 150 and Counter(c["papel"] for c in lista) == {"piloto": 20, "principal": 130}
    lista = sorteio.sortear(_grande(12), "s")
    assert Counter(c["papel"] for c in lista) == {"piloto": 12}


def test_jsonl_copia_o_que_nao_expira_e_o_sha_e_o_do_git():
    lista = sorteio.sortear([{**ev(1), "cadeira": "ia", "estrato": "sentido"}], "s")
    linha = json.loads(sorteio.linhas_jsonl(lista).decode())
    assert linha["id"] == "esc-00000001" and linha["evento_id"].startswith("00000001") and linha["cadeira"] == "ia"
    assert linha["pergunta"].startswith("pergunta de sentido") and linha["data"] == "2026-10-02"
    assert linha["estrato_proposto_por"] == "maquina" and linha["estrato_confirmado_pelo_dono"] is None
    assert sorteio.sha_blob_git(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"  # git hash-object


# --- o verbo, de ponta a ponta com docker e /facets falsos ---------------------------------------------------


class _Facets(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        dado = json.dumps({"indice": {"acervo_sha": "abc123456789def0"}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)


DOCKER_FALSO = """#!{python}
import json, os, sys
a = sys.argv[1:]
container = a[2]
sql = sys.stdin.read()
p = os.environ["FAKE_ESTADO"]
estado = json.load(open(p))
if container == "rag-extractor-pg":
    print(json.dumps(estado["eventos"]))
elif container == "harness-sessao-db":
    print(json.dumps(estado["cadeiras"]))
elif container == "motor-pg":
    if "INSERT INTO avaliacao.gabarito_versao" in sql:
        estado["versoes"].append(sql)
        json.dump(estado, open(p, "w"))
        print(json.dumps({{"id": "00000000-0000-4000-8000-0000000000aa"}}))
    elif estado["versoes"] and estado["versoes"][-1].count(sql.split("sha_git = ")[1].split(" ")[0]):
        print(json.dumps({{"id": "00000000-0000-4000-8000-0000000000aa"}}))
    else:
        print("null")
"""


@pytest.fixture
def verbo(tmp_path):
    servidor = HTTPServer(("127.0.0.1", 0), _Facets)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)
    estado = tmp_path / "estado.json"
    estado.write_text(json.dumps({"eventos": pool(), "cadeiras": [{"sessao_id": v, "cadeira": k} for k, v in S.items()], "versoes": []}))
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": "http://127.0.0.1:9/search",
        "facets": f"http://127.0.0.1:{servidor.server_port}/facets", "token_em": "rag/RAG_API_TOKEN",
        "banco": {"container": "rag-extractor-pg", "db": "rag_extractor", "user": "rag"},
        "bancos": {"motor": {"container": "motor-pg", "db": "motor", "user": "motor"},
                   "sessao": {"container": "harness-sessao-db", "db": "sessao", "user": "sessao"}},
        "ajustes": [], "nao_e_ajuste": {}}}))

    def roda(*args, eventos=None):
        if eventos is not None:
            e = json.loads(estado.read_text())
            e["eventos"] = eventos
            estado.write_text(json.dumps(e))
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia), "OPS_LOG_DIR": str(tmp_path / "ops"),
               "PF_CADEIRA": "ia", "FAKE_ESTADO": str(estado), "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", "sortear", *args], capture_output=True, text=True, env=env,
                              timeout=60, check=False)

    yield roda, tmp_path, estado
    servidor.shutdown()


def test_plano_estrito_conta_o_pool_e_nao_grava_nada(verbo):
    roda, tmp, estado = verbo
    r = roda("biblioteca")
    assert r.returncode == 0, r.stderr
    assert "26 no estrato sentido · 26 sorteadas" in r.stdout and "POOL ABAIXO DE 220: 26" in r.stdout
    assert "cadeiras fora por ter menos de cinco: rara" in r.stdout and "3  cadeira com menos de 5" in r.stdout
    assert "plano: nada gravado" in r.stdout and json.loads(estado.read_text())["versoes"] == []
    assert r.stdout.count("\n  ") >= 20  # as 20 do piloto listadas


def test_json_traz_o_relatorio_e_a_lista(verbo):
    roda, _, _ = verbo
    r = roda("biblioteca", "--json", "--semente", "outra")
    rel = json.loads(r.stdout)
    assert rel["sorteadas"] == 26 and rel["piloto"] == 20 and rel["semente"] == "outra" and len(rel["lista"]) == 26
    assert rel["flags"]["aceitar_sem_ordem"] is False and len(rel["sha_git"]) == 40


def test_flags_de_relaxar_ampliam_o_pool_e_ficam_no_relatorio(verbo):
    roda, _, _ = verbo
    sem_ordem = [ev(i, "ia", ordem_id=None) for i in range(1, 11)]
    assert json.loads(roda("biblioteca", "--json", eventos=sem_ordem).stdout)["sorteadas"] == 0
    rel = json.loads(roda("biblioteca", "--json", "--aceitar-sem-ordem", eventos=sem_ordem).stdout)
    assert rel["sorteadas"] == 10 and rel["flags"]["aceitar_sem_ordem"] is True


def test_apply_grava_arquivo_e_versao_e_o_mesmo_apply_diz_ja_existe(verbo):
    roda, tmp, estado = verbo
    saida = tmp / "escada.jsonl"
    r = roda("biblioteca", "--apply", "--saida", str(saida))
    assert r.returncode == 0, r.stderr
    assert "gabarito_versao 00000000-0000-4000-8000-0000000000aa gravada" in r.stdout and "sha_acervo abc123456789" in r.stdout
    linhas = [json.loads(l) for l in saida.read_text().splitlines()]
    assert len(linhas) == 26 and linhas[0]["papel"] == "piloto"
    assert len(json.loads(estado.read_text())["versoes"]) == 1
    r2 = roda("biblioteca", "--apply", "--saida", str(saida))
    assert r2.returncode == 0 and "ja existe: gabarito_versao" in r2.stdout
    assert len(json.loads(estado.read_text())["versoes"]) == 1


@pytest.mark.parametrize("args", [("casa",), ("biblioteca", "--apply"), ("biblioteca", "--semente"), ("biblioteca", "--sem-isso")])
def test_uso_errado_sai_2(verbo, args):
    roda, _, estado = verbo
    assert roda(*args).returncode == 2
    assert json.loads(estado.read_text())["versoes"] == []
