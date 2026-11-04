"""`motor rag buscar|medir` com `--filtro` e `--juncao` (card #4116, U8): as flags, as recusas e o corpo.

O verbo roda de verdade, como subprocesso, contra uma API falsa em 127.0.0.1 (como test_motor_contra.py e
test_motor_buscar_consulta.py). Prova o que o verbo MANDA (o objeto `filtro` no corpo, ou nada), o que RECUSA antes de
chamar a rede (exit 2, nenhum pedido), como traduz a recusa «filtro:» da API (exit 2 com a linha dela) e o que o `medir`
guarda e compara (`--igual-a`). O filtro em si, e o vocabulário, são da API e têm teste no motor.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"

NEC = "como o cache de prefixo reduz o custo"
DOMINIOS = "ia, engenharia-software, seguranca, juridico"
INDICE = {"acervo_sha": "abc123456789", "embed_model": "Qwen/Qwen3-Embedding-0.6B", "embed_backend": "torch",
          "geracao": {"numero": 3, "parametros": {"embedder": "nvidia/Nemotron-3-Embed-1B-BF16"}}}


def _api(estado):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, corpo, status=200):
            dado = json.dumps(corpo).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dado)))
            self.end_headers()
            self.wfile.write(dado)

        def do_GET(self):
            if self.path == "/facets":
                return self._json({"indice": INDICE})
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            estado["pedidos"].append(corpo)
            if estado.get("erro"):
                status, msg = estado["erro"]
                return self._json({"erro": msg}, status)
            if (corpo.get("filtro") or {}).get("dominio") == ["dados"]:
                return self._json({"erro": f"filtro: dominio=dados fora do vocabulário (válidos: {DOMINIOS})"}, 400)
            pergunta = corpo["pergunta"] if isinstance(corpo["pergunta"], str) else corpo["pergunta"][0]
            lista = [f"{pergunta}|{i}" for i in range(10)][: corpo.get("k", 8)]
            lista = estado["ajusta"](pergunta, lista)
            return self._json({"fontes": [{"secao_id": s, "obra": "Obra", "section_id": "x"} for s in lista],
                               "cobertura": "boa", "filtro": {"dominio": (corpo.get("filtro") or {}).get("dominio", [])},
                               "aviso": None, "tempos_ms": {"total": 5.0}})
    return H


def _gabarito(tmp_path, positivas=3):
    itens = [{"id": f"P{i}", "pergunta": f"positiva {i} onde esta", "estrato": "T2-cadeiras",
              "alvo_obras": ["Obra"], "relevancia": "positiva", "pontuavel": True} for i in range(positivas)]
    itens.append({"id": "N0", "pergunta": "negbaixa 0", "estrato": "T2-cadeiras", "relevancia": "negativa",
                  "pontuavel": True, "nota": "sem obra no acervo"})
    gab = tmp_path / "bateria.jsonl"
    gab.write_text("\n".join(json.dumps(x) for x in itens) + "\n", encoding="utf-8")
    return gab


@pytest.fixture
def api(tmp_path):
    estado = {"pedidos": [], "ajusta": lambda q, l: l, "erro": None}
    servidor = HTTPServer(("127.0.0.1", 0), _api(estado))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": f"{base}/search",
        "token_em": "rag/RAG_API_TOKEN", "facets": f"{base}/facets", "medicoes_em": "var/medicoes/rag",
        "ajustes": [], "nao_e_ajuste": {}}}))
    abertura = tmp_path / "abertura-publicada" / "current" / "abertura"
    abertura.mkdir(parents=True)
    (abertura / "rotas-chapeu.json").write_text(json.dumps({"ia": {"engenharia-de-harness": ["rag"]}}), encoding="utf-8")

    def roda(*args, stdin=subprocess.DEVNULL):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_ABERTURA_DIR": str(tmp_path / "abertura-publicada"),
               "PF_CADEIRA": "ia", "PF_CHAPEU": "engenharia-de-harness"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", *args], capture_output=True, text=True,
                              env=env, timeout=120, check=False, stdin=stdin)

    yield roda, estado, instancia, _gabarito(tmp_path)
    servidor.shutdown()


def _buscar(roda, *flags, part="biblioteca"):
    return roda("buscar", part, "--necessidade", NEC, "--previa", "--sem-lint", *flags)


# --- buscar: o que vai no corpo ---------------------------------------------------------------------------

def test_sem_filtro_o_corpo_nao_ganha_nada(api):
    roda, estado, *_ = api
    assert _buscar(roda).returncode == 0
    [corpo] = estado["pedidos"]
    assert "filtro" not in corpo and "juncao" not in corpo and "conceito" not in corpo


def test_filtro_de_um_eixo_com_dois_valores(api):
    roda, estado, *_ = api
    r = _buscar(roda, "--filtro", "dominio=ia,engenharia-software")
    assert r.returncode == 0, r.stderr
    assert estado["pedidos"][0]["filtro"] == {"dominio": ["ia", "engenharia-software"]}


def test_o_mesmo_eixo_em_duas_flags_soma_sem_repetir(api):
    roda, estado, *_ = api
    assert _buscar(roda, "--filtro", "dominio=ia", "--filtro", "dominio=engenharia-software,ia").returncode == 0
    assert estado["pedidos"][0]["filtro"] == {"dominio": ["ia", "engenharia-software"]}


def test_dois_eixos_vao_juntos_no_objeto(api):
    roda, estado, *_ = api
    assert _buscar(roda, "--filtro", "dominio=ia", "--filtro", "conceito=cache-de-prefixo").returncode == 0
    assert estado["pedidos"][0]["filtro"] == {"dominio": ["ia"], "conceito": ["cache-de-prefixo"]}


def test_juncao_ou_com_conceito_vai_no_objeto(api):
    roda, estado, *_ = api
    r = _buscar(roda, "--filtro", "dominio=ia", "--filtro", "conceito=cache-de-prefixo", "--juncao", "ou")
    assert r.returncode == 0, r.stderr
    assert estado["pedidos"][0]["filtro"] == {"dominio": ["ia"], "conceito": ["cache-de-prefixo"], "juncao": "ou"}


def test_conceito_e_conceitos_nao_se_misturam(api):
    """Trava do card: `--conceito` segue alimentando `conceitos` (a ontologia); o eixo vive em `filtro`."""
    roda, estado, *_ = api
    assert _buscar(roda, "--conceito", "rag", "--filtro", "conceito=cache-de-prefixo").returncode == 0
    corpo = estado["pedidos"][0]
    assert corpo["conceitos"] == ["rag"] and corpo["filtro"] == {"conceito": ["cache-de-prefixo"]}
    assert "conceito" not in corpo


def test_o_filtro_nao_passa_pelo_lint_da_necessidade(api):
    roda, estado, *_ = api
    r = roda("buscar", "biblioteca", "--necessidade", NEC, "--filtro", "dominio=ia")
    assert r.returncode == 0, r.stderr
    assert estado["pedidos"][0]["filtro"] == {"dominio": ["ia"]}
    assert "ia" not in estado["pedidos"][0]["consulta"]["necessidade"]


def test_json_e_aceito_e_a_saida_e_o_json_cru(api):
    roda, estado, *_ = api
    r = _buscar(roda, "--filtro", "dominio=ia", "--json")
    assert r.returncode == 0, r.stderr
    saida = json.loads(r.stdout)
    assert saida["filtro"]["dominio"] == ["ia"] and saida["aviso"] is None
    assert "json" not in json.dumps(estado["pedidos"][0])


# --- buscar: as recusas antes da rede ----------------------------------------------------------------------

@pytest.mark.parametrize("flags,pedaco", [
    (("--filtro", "tema=ia"), "eixos validos: dominio, subdominio, frente, colecao, conceito"),
    (("--filtro", "ia"), "eixo=valor"),
    (("--filtro", "dominio="), "sem valor"),
    (("--filtro", "dominio=ia", "--juncao", "ou"), "a junção pede dois eixos"),
    (("--filtro", "dominio=ia", "--juncao", "e"), "a junção pede dois eixos"),
    (("--juncao", "ou"), "a junção pede dois eixos"),
    (("--filtro", "dominio=ia", "--filtro", "colecao=pessoal", "--juncao", "ou"), "faltou o conceito"),
    (("--filtro", "dominio=ia", "--filtro", "conceito=x", "--juncao", "xor"), "--juncao aceita e|ou"),
    (("--filtro",), "exige um valor"),
])
def test_recusa_com_exit_2_e_sem_chamar_a_api(api, flags, pedaco):
    roda, estado, *_ = api
    r = _buscar(roda, *flags)
    assert r.returncode == 2, r.stdout + r.stderr
    assert pedaco in r.stderr
    assert estado["pedidos"] == [], "a recusa vem antes da rede"


def test_filtro_na_casa_sai_2_e_avisa_que_nao_vale(api):
    roda, estado, *_ = api
    r = _buscar(roda, "--filtro", "dominio=ia", part="casa")
    assert r.returncode == 2 and "o filtro não vale na casa" in r.stderr
    assert estado["pedidos"] == []


def test_a_recusa_do_eixo_diz_o_eixo_errado_e_a_junção_ou_sem_conceito_diz_o_que_faltou(api):
    roda, _, *_ = api
    assert "'tema'" in _buscar(roda, "--filtro", "tema=ia").stderr
    r = _buscar(roda, "--filtro", "dominio=ia", "--filtro", "frente=harness", "--juncao", "ou")
    assert "conceito" in r.stderr and "faltou" in r.stderr


# --- buscar: a recusa «filtro:» da API ----------------------------------------------------------------------

def test_valor_fora_do_vocabulario_vira_exit_2_com_a_linha_da_api(api):
    roda, estado, *_ = api
    r = _buscar(roda, "--filtro", "dominio=dados")
    assert r.returncode == 2, r.stdout + r.stderr
    [linha] = [l for l in r.stderr.splitlines() if "dominio=dados" in l]
    assert linha.startswith("motor: filtro: dominio=dados") and DOMINIOS in linha
    assert len(estado["pedidos"]) == 1


def test_outro_400_segue_exit_3_como_sempre(api):
    roda, estado, *_ = api
    estado["erro"] = (400, "`pergunta` é obrigatória")
    r = _buscar(roda)
    assert r.returncode == 3 and "HTTP 400" in r.stderr and "filtro:" not in r.stderr


def test_400_longo_do_filtro_vem_inteiro(api):
    roda, estado, *_ = api
    longa = "filtro: conceito=x fora do vocabulário (válidos: " + ", ".join(f"c{i:04d}" for i in range(200)) + ")"
    estado["erro"] = (400, longa)
    r = _buscar(roda, "--filtro", "conceito=x")
    assert r.returncode == 2 and longa in r.stderr


def test_502_nao_vira_exit_2(api):
    roda, estado, *_ = api
    estado["erro"] = (502, "falha interna (RuntimeError)")
    assert _buscar(roda, "--filtro", "dominio=ia").returncode == 3


# --- medir -------------------------------------------------------------------------------------------------

def _medir(roda, gab, *flags):
    return roda("medir", "biblioteca", "--bateria", str(gab), "--k", "8", *flags)


def _arquivos(instancia):
    return sorted((instancia / "var" / "medicoes" / "rag").glob("*.json"))


def _rodada(arquivo):
    return json.loads(arquivo.read_text())


def test_medir_sem_filtro_manda_o_corpo_de_antes_e_guarda_o_top(api):
    roda, estado, instancia, gab = api
    r = _medir(roda, gab, "--rotulo", "antes")
    assert r.returncode == 0, r.stdout + r.stderr
    assert estado["pedidos"] and all("filtro" not in p for p in estado["pedidos"])
    [arq] = _arquivos(instancia)
    rodada = _rodada(arq)
    assert rodada["filtro"] is None
    assert all(len(p["top"]) == 8 for p in rodada["perguntas"])
    assert rodada["perguntas"][0]["top"][0] == "positiva 0 onde esta|0"


def test_medir_com_filtro_manda_a_cada_pergunta_e_grava_na_rodada(api):
    roda, estado, instancia, gab = api
    r = _medir(roda, gab, "--filtro", "dominio=ia", "--filtro", "conceito=rag", "--juncao", "ou",
               "--rotulo", "filtro-ia")
    assert r.returncode == 0, r.stdout + r.stderr
    assert estado["pedidos"] and all(
        p["filtro"] == {"dominio": ["ia"], "conceito": ["rag"], "juncao": "ou"} for p in estado["pedidos"])
    assert _rodada(_arquivos(instancia)[0])["filtro"] == {"dominio": ["ia"], "conceito": ["rag"], "juncao": "ou"}
    assert "filtro desta rodada" in r.stdout


def test_medir_so_compara_com_a_rodada_do_mesmo_filtro(api):
    roda, _, instancia, gab = api
    assert _medir(roda, gab, "--rotulo", "sem").returncode == 0
    r = _medir(roda, gab, "--filtro", "dominio=ia", "--rotulo", "filtrada")
    assert "primeira medicao" in r.stdout, "a rodada filtrada nao tem baseline na de corpus inteiro"
    r = _medir(roda, gab, "--filtro", "dominio=ia", "--rotulo", "filtrada-2")
    assert "contra " in r.stdout and "primeira medicao" not in r.stdout
    r = _medir(roda, gab, "--rotulo", "sem-2")
    assert "contra " in r.stdout and "primeira medicao" not in r.stdout


def test_medir_recusa_antes_da_rede(api):
    roda, estado, _, gab = api
    for flags in (("--filtro", "tema=ia"), ("--filtro", "dominio=ia", "--juncao", "ou"), ("--juncao", "ou"),
                  ("--filtro", "dominio=ia", "--filtro", "frente=harness", "--juncao", "ou")):
        r = _medir(roda, gab, *flags)
        assert r.returncode == 2, (flags, r.stdout + r.stderr)
    assert estado["pedidos"] == []


def test_medir_filtro_na_casa_sai_2(api):
    roda, estado, _, gab = api
    r = roda("medir", "casa", "--bateria", str(gab), "--k", "8", "--filtro", "dominio=ia")
    assert r.returncode == 2 and "o filtro não vale na casa" in r.stderr
    assert estado["pedidos"] == []


def test_medir_com_valor_fora_do_vocabulario_sai_2_com_a_linha_da_api(api):
    roda, _, _, gab = api
    r = _medir(roda, gab, "--filtro", "dominio=dados")
    assert r.returncode == 2 and "filtro: dominio=dados" in r.stderr


# --- medir --igual-a ---------------------------------------------------------------------------------------

def _linha_do_top(stdout):
    m = re.search(r"top-8 identico em (\d+)/(\d+) perguntas", stdout)
    assert m, stdout
    return int(m[1]), int(m[2])


def test_igual_a_com_o_mesmo_top_sai_0_e_diz_n_de_n(api):
    roda, _, _, gab = api
    assert _medir(roda, gab, "--rotulo", "antes").returncode == 0
    r = _medir(roda, gab, "--rotulo", "depois", "--igual-a", "antes")
    assert r.returncode == 0, r.stdout + r.stderr
    iguais, total = _linha_do_top(r.stdout)
    assert iguais == total >= 4
    assert "sem diferenca aberta" in r.stdout


def test_igual_a_com_um_trecho_diferente_sai_1_e_nomeia_a_pergunta(api):
    roda, estado, _, gab = api
    assert _medir(roda, gab, "--rotulo", "antes").returncode == 0
    estado["ajusta"] = lambda q, l: l[:-1] + ["so-agora"] if q.startswith("positiva 1") else l
    r = _medir(roda, gab, "--rotulo", "depois", "--igual-a", "antes")
    assert r.returncode == 1, r.stdout + r.stderr
    iguais, total = _linha_do_top(r.stdout)
    assert iguais == total - 1
    assert "diferente" in r.stdout and "positiva 1 onde esta" in r.stdout and "diferenca aberta" in r.stdout


def test_igual_a_com_a_ordem_trocada_tambem_e_diferenca(api):
    roda, estado, _, gab = api
    assert _medir(roda, gab, "--rotulo", "antes").returncode == 0
    estado["ajusta"] = lambda q, l: [l[1], l[0]] + l[2:] if q.startswith("positiva 2") else l
    r = _medir(roda, gab, "--rotulo", "depois", "--igual-a", "antes")
    assert r.returncode == 1 and "ordem" in r.stdout


def test_igual_a_rotulo_que_nao_existe_sai_1(api):
    roda, _, _, gab = api
    assert _medir(roda, gab, "--rotulo", "antes").returncode == 0
    r = _medir(roda, gab, "--rotulo", "depois", "--igual-a", "nao-existe")
    assert r.returncode == 1 and "sem rodada com o rotulo 'nao-existe'" in r.stdout


def test_igual_a_pega_a_ultima_rodada_do_rotulo_e_nunca_a_propria(api):
    roda, estado, _, gab = api
    assert _medir(roda, gab, "--rotulo", "ref").returncode == 0
    time.sleep(1.1)       # o arquivo da rodada leva a hora em segundos: o mesmo rótulo no mesmo segundo o reescreve
    estado["ajusta"] = lambda q, l: l[:-1] + ["mudou"] if q.startswith("positiva 0") else l
    assert _medir(roda, gab, "--rotulo", "ref").returncode == 0           # a ref nova é a que vale
    time.sleep(1.1)
    r = _medir(roda, gab, "--rotulo", "ref", "--igual-a", "ref")
    assert r.returncode == 0, r.stdout        # igual à anterior de mesmo rótulo, e não a si própria
    assert _linha_do_top(r.stdout)[0] == _linha_do_top(r.stdout)[1]


def test_igual_a_com_json_sai_o_json_e_o_exit_acompanha(api):
    roda, estado, _, gab = api
    assert _medir(roda, gab, "--rotulo", "antes").returncode == 0
    r = _medir(roda, gab, "--rotulo", "depois", "--igual-a", "antes", "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["igual_a"]["igual"] is True
    estado["ajusta"] = lambda q, l: l[:-1] + ["so-agora"]
    r = _medir(roda, gab, "--rotulo", "depois-2", "--igual-a", "antes", "--json")
    assert r.returncode == 1 and json.loads(r.stdout)["igual_a"]["igual"] is False


def test_igual_a_contra_rodada_sem_top_gravado_nao_e_igual(api):
    """A rodada de antes do #4116 não guarda o top: não há o que comparar, e isso não passa por igual."""
    roda, _, instancia, gab = api
    assert _medir(roda, gab, "--rotulo", "antes").returncode == 0
    [arq] = _arquivos(instancia)
    rodada = _rodada(arq)
    for p in rodada["perguntas"]:
        p.pop("top")
    arq.write_text(json.dumps(rodada))
    r = _medir(roda, gab, "--rotulo", "depois", "--igual-a", "antes")
    assert r.returncode == 1 and "sem top na rodada de referencia" in r.stdout
