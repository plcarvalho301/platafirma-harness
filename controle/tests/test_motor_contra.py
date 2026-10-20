"""`motor <inst> medir <particao> --contra <outra>`: o top-8 de duas instâncias da busca lado a lado (card #3844,
tarefa 2; R27 da spec motor).

Como `test_motor_troca.py`: o verbo roda de verdade, como subprocesso, mas contra DUAS buscas falsas em 127.0.0.1 (a
servida e a nova), com registro, tokens e instância num diretório temporário. Prova o que o verbo MANDA às duas (corpo,
origem, partição), o que IMPRIME na primeira linha (a âncora que o card cita), o exit que decide a virada e o arquivo que
guarda a rodada. A conta pura de `bin/_motor/comparar.py` tem teste próprio, sem rede.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))
import comparar  # noqa: E402

INDICE = {"acervo_sha": "abc123456789", "embed_model": "Qwen/Qwen3-Embedding-0.6B", "embed_backend": "torch",
          "geracao": {"numero": 3, "parametros": {"embedder": "nvidia/Nemotron-3-Embed-1B-BF16"}}}


def _api(lado, estado):
    """Uma busca falsa. `estado[lado]`: `pedidos` (o que chegou), `indice` (o /facets) e `ajusta`, que recebe
    (particao, pergunta, lista) e devolve a lista que esta busca responde, para o teste desviar a nova."""
    meu = estado[lado]

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, corpo):
            dado = json.dumps(corpo).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dado)))
            self.end_headers()
            self.wfile.write(dado)

        def do_GET(self):
            meu["pedidos"].append(("GET", self.path, self.headers.get("Authorization"), None))
            if self.path == "/facets":
                return self._json({"indice": meu["indice"]})
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            meu["pedidos"].append(("POST", self.path, self.headers.get("Authorization"), corpo))
            lista = [f"{corpo['particao']}|{corpo['pergunta']}|{i}" for i in range(10)][: corpo["k"]]
            lista = meu["ajusta"](corpo["particao"], corpo["pergunta"], lista)
            return self._json({"fontes": [{"secao_id": s, "obra": "Obra", "section_id": "x"} for s in lista],
                               "cobertura": "boa"})
    return H


def _gabarito(tmp_path, positivas=3):
    itens = [{"id": f"P{i}", "pergunta": f"positiva {i} onde esta", "estrato": "T2-cadeiras",
              "alvo_obras": ["Obra"], "relevancia": "positiva", "pontuavel": True} for i in range(positivas)]
    itens.append({"id": "N0", "pergunta": "negbaixa 0", "estrato": "T2-cadeiras", "relevancia": "negativa",
                  "pontuavel": True, "nota": "sem obra no acervo"})
    gab = tmp_path / "gabarito.jsonl"
    gab.write_text("\n".join(json.dumps(x) for x in itens) + "\n", encoding="utf-8")
    return gab


@pytest.fixture
def duas(tmp_path):
    estado = {lado: {"pedidos": [], "indice": dict(INDICE), "ajusta": lambda p, q, l: l} for lado in ("rag", "busca")}
    servidores = {lado: HTTPServer(("127.0.0.1", 0), _api(lado, estado)) for lado in estado}
    for s in servidores.values():
        threading.Thread(target=s.serve_forever, daemon=True).start()
    base = {lado: f"http://127.0.0.1:{s.server_port}" for lado, s in servidores.items()}
    instancia = tmp_path / "inst"
    for lado, tok in (("rag", "toka"), ("busca", "tokb")):
        (instancia / "segredos" / lado).mkdir(parents=True)
        (instancia / "segredos" / lado / "RAG_API_TOKEN").write_text(tok + "\n")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({lado: {
        "estado": "ativa", "container": None, "stack": lado, "endpoint": f"{base[lado]}/search",
        "facets": f"{base[lado]}/facets", "token_em": f"{lado}/RAG_API_TOKEN",
        "medicoes_em": f"var/medicoes/{lado}", "ajustes": [], "nao_e_ajuste": {}} for lado in base}))

    def roda(*args):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", "medir", *args], capture_output=True, text=True,
                              env=env, timeout=120, check=False)

    yield roda, estado, instancia, _gabarito(tmp_path)
    for s in servidores.values():
        s.shutdown()


def _conta(stdout):
    m = re.search(r"top-8 identico em (\d+)/(\d+) perguntas \(Jaccard minimo ([\d.-]+)\) · "
                  r"trechos cruzando particao: (\d+) · rag contra busca", stdout.splitlines()[0])
    assert m, stdout.splitlines()[0]
    return int(m[1]), int(m[2]), m[3], int(m[4])


# --- o verbo, de ponta a ponta --------------------------------------------------------------------------

def test_busca_igual_nos_dois_lados_sai_0_e_diz_que_a_troca_pode_seguir(duas):
    roda, estado, instancia, gab = duas
    r = roda("biblioteca", "--gabarito", str(gab), "--contra", "busca")
    assert r.returncode == 0, r.stdout + r.stderr
    iguais, total, jmin, cruzados = _conta(r.stdout)
    assert iguais == total >= 1 and jmin == "1.000" and cruzados == 0
    assert "sem diferenca aberta: a troca dos enderecos pode seguir" in r.stdout
    salvo = next((instancia / "var" / "medicoes" / "rag" / "contra").glob("*-biblioteca-busca.json"))
    corpo = json.loads(salvo.read_text())
    assert corpo["resumo"]["limpo"] is True and corpo["servida"] == "rag" and corpo["nova"] == "busca"
    assert len(corpo["linhas"]) == total


def test_as_duas_buscas_recebem_origem_sombra_k_8_e_a_particao_nas_duas_pontas(duas):
    roda, estado, _, gab = duas
    assert roda("biblioteca", "--gabarito", str(gab), "--contra", "busca").returncode == 0
    for lado, token in (("rag", "Bearer toka"), ("busca", "Bearer tokb")):
        buscas = [p for p in estado[lado]["pedidos"] if p[1] == "/search"]
        assert buscas and all(p[2] == token for p in buscas)
        assert all(p[3]["origem"] == "sombra" and p[3]["k"] == 8 and p[3]["texto"] == "nenhum" for p in buscas)
        # cada pergunta vai na partição pedida e na outra: é do par que sai o cruzamento
        assert {p[3]["particao"] for p in buscas} == {"biblioteca", "casa"}
    assert len([p for p in estado["rag"]["pedidos"] if p[1] == "/search"]) == \
        len([p for p in estado["busca"]["pedidos"] if p[1] == "/search"])


def test_um_trecho_diferente_no_top_8_sai_1_e_a_virada_nao_segue(duas):
    roda, estado, _, gab = duas
    estado["busca"]["ajusta"] = lambda p, q, l: l[:-1] + ["so-na-nova"] if q.startswith("positiva 1") and p == "biblioteca" else l
    r = roda("biblioteca", "--gabarito", str(gab), "--contra", "busca")
    assert r.returncode == 1, r.stdout
    iguais, total, jmin, cruzados = _conta(r.stdout)
    assert iguais == total - 1 and float(jmin) < 1.0 and cruzados == 0
    assert "diferente (0.778) [biblioteca] positiva 1 onde esta" in r.stdout    # 7 em comum de 9 distintos
    assert "diferenca aberta: nada se troca" in r.stdout


def test_trecho_da_casa_na_resposta_da_biblioteca_e_cruzamento_de_particao(duas):
    roda, estado, _, gab = duas
    # a nova devolve, na biblioteca, um trecho que a servida só tem na casa
    estado["busca"]["ajusta"] = lambda p, q, l: (
        l[:-1] + [f"casa|{q}|0"] if q.startswith("positiva 0") and p == "biblioteca" else l)
    r = roda("biblioteca", "--gabarito", str(gab), "--contra", "busca")
    assert r.returncode == 1, r.stdout
    assert _conta(r.stdout)[3] == 1
    assert "cruzou (1) [biblioteca] positiva 0 onde esta" in r.stdout


def test_embedder_ou_geracao_diferente_entre_os_indices_sai_1_mesmo_com_top_8_igual(duas):
    roda, estado, _, gab = duas
    estado["busca"]["indice"] = {**INDICE, "geracao": {"numero": 4, "parametros": {"embedder": "outro"}}}
    r = roda("biblioteca", "--gabarito", str(gab), "--contra", "busca")
    assert r.returncode == 1, r.stdout
    iguais, total, _, cruzados = _conta(r.stdout)
    assert iguais == total and cruzados == 0
    assert "← DIFERE do da servida" in r.stdout and "diferenca aberta" in r.stdout


def test_json_leva_o_resumo_os_carimbos_e_o_arquivo(duas):
    roda, _, _, gab = duas
    r = roda("biblioteca", "--gabarito", str(gab), "--contra", "busca", "--json")
    assert r.returncode == 0, r.stderr
    saida = json.loads(r.stdout)
    assert saida["limpo"] is True and saida["resumo"]["cruzados"] == 0 and saida["k"] == 8
    assert saida["carimbos"]["rag"] == saida["carimbos"]["busca"]
    assert Path(saida["arquivo"]).is_file()


def test_uso_errado_sai_2_sem_chamar_nenhuma_busca(duas):
    roda, estado, _, gab = duas
    assert roda("biblioteca", "--gabarito", str(gab), "--contra", "rag").returncode == 2      # contra si mesma
    assert roda("biblioteca", "--gabarito", str(gab), "--contra", "nao-existe").returncode == 2
    assert roda("biblioteca", "--gabarito", str(gab), "--contra").returncode == 2             # sem valor
    assert roda("biblioteca", "--gabarito", str(gab), "--contra", "busca", "--k", "oito").returncode == 2
    assert roda("casa", "--contra", "busca").returncode == 2                                  # casa sem gabarito nem log
    assert not any(p[1] == "/search" for lado in estado.values() for p in lado["pedidos"])


# --- a conta, sem a API ---------------------------------------------------------------------------------

def test_a_chave_do_trecho_prefere_a_secao_e_cai_na_obra_com_a_coordenada():
    assert comparar.chave({"secao_id": "uuid-1", "chave": "c", "obra": "o", "section_id": "s"}) == "uuid-1"
    assert comparar.chave({"chave": "c", "obra": "o", "section_id": "s"}) == "c"
    assert comparar.chave({"obra": "o", "section_id": "s"}) == "o|s"


def test_top_corta_em_k_e_nao_repete_a_mesma_secao():
    fontes = [{"secao_id": s} for s in ("a", "b", "a", "c", "d")]
    assert comparar.top(fontes, 3) == ["a", "b", "c"]
    assert comparar.top(None) == []


def test_jaccard_e_cruzados():
    assert comparar.jaccard(["a", "b"], ["b", "a"]) == 1.0
    assert comparar.jaccard(["a", "b", "c"], ["b", "c", "d"]) == pytest.approx(0.5)
    assert comparar.jaccard([], []) == 0.0
    assert comparar.cruzados(["x", "y"], ["y", "z"]) == ["y"]


def test_resumo_so_fecha_limpo_com_tudo_igual_sem_cruzamento_e_ao_menos_uma_pergunta():
    item = {"q": "q", "particao": "biblioteca"}
    igual = comparar.linha(item, ["a", "b"], ["a", "b"], [])
    outra_ordem = comparar.linha(item, ["a", "b"], ["b", "a"], [])
    assert outra_ordem["jaccard"] == 1.0 and outra_ordem["mesma_ordem"] is False
    assert comparar.resumo([igual, outra_ordem])["limpo"] is True          # o conjunto é o que o card exige
    assert comparar.resumo([])["limpo"] is False
    assert comparar.resumo([comparar.linha(item, ["a"], ["b"], [])])["limpo"] is False
    assert comparar.resumo([comparar.linha(item, ["a"], ["a"], ["x"])])["limpo"] is False
