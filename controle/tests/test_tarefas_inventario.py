# componente: componente:verbo-tarefas
"""Os atos do inventário no verbo `tarefas` (story #4317, feature 4314; API do rastreador, sql/033).

O que a casa decidiu: o verbo só fala com a API do rastreador; a chave que a pessoa digita é
<feature>.<p|r|d><n> (4314.r3); o número, a validação desfeita pela frase mudada e o evento de cada ato
são do banco; o nome do verbo e a forma de chamar dos outros atos não mudam.

PROVA: roda o `bin/tarefas` de verdade, com `bash`, contra um servidor HTTP de mentira em loopback
(`TAREFAS_BASE`), e confere o que o verbo envia (método, caminho, corpo, sujeito) e o que imprime.
NÃO PROVA: a API real nem o banco (isso é o teste da API, na story, e o `release promover`).
"""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

VERBO = Path(__file__).resolve().parents[2] / "bin" / "tarefas"


class Servidor:
    """Responde pela tabela {(método, caminho): (status, json)} e guarda o que chegou."""

    def __init__(self):
        self.rotas, self.recebido = {}, []
        dono = self

        class H(BaseHTTPRequestHandler):
            def _responde(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = self.rfile.read(n).decode() if n else ""
                dono.recebido.append({"metodo": self.command, "caminho": self.path.split("?")[0],
                                      "query": self.path.partition("?")[2], "corpo": corpo,
                                      "sujeito": self.headers.get("x-auth-request-preferred-username")})
                status, payload = dono.rotas.get((self.command, self.path.split("?")[0]),
                                                 (404, {"erro": "rota que o teste não conhece"}))
                bruto = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(bruto)))
                self.end_headers()
                self.wfile.write(bruto)

            do_GET = do_POST = do_PATCH = do_DELETE = _responde

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_port}/api"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def fecha(self):
        self.httpd.shutdown()


@pytest.fixture
def api():
    s = Servidor()
    yield s
    s.fecha()


def verbo(api, *args, tmp_path):
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "TAREFAS_BASE": api.base,
           "PF_CADEIRA": "engenharia", "XDG_RUNTIME_DIR": str(tmp_path), "TMPDIR": str(tmp_path)}
    return subprocess.run(["bash", str(VERBO), *args], env=env, capture_output=True, text=True, timeout=60)


REGRA3 = {"chave": "5000.r3", "frase": "a terceira", "porque": "porque sim", "casos": ["a → b"],
          "mecanismo": "o gatilho", "peca_numero": 1, "feature_inteira": False, "validada": False,
          "validada_em": None, "validada_por": None, "cortada": False}


def test_criar_regra_manda_o_corpo_e_o_sujeito_e_imprime_a_chave_que_a_api_deu(api, tmp_path):
    api.rotas[("POST", "/api/itens/5000/inventario/regras")] = (201, REGRA3)
    r = verbo(api, "inventario", "criar", "5000", "regra", "--frase", "a terceira", "--peca", "1",
              "--caso", "a → b", "--caso", "c → d", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "5000.r3 criado"
    pedido = api.recebido[0]
    assert pedido["sujeito"] == "engenharia"
    assert json.loads(pedido["corpo"]) == {"frase": "a terceira", "peca": 1, "casos": ["a → b", "c → d"]}


def test_a_regra_solta_volta_recusada_com_o_motivo_da_api_e_o_verbo_sai_com_erro(api, tmp_path):
    api.rotas[("POST", "/api/itens/5000/inventario/regras")] = (
        400, {"erro": "a regra pertence a uma peça da feature ou vale para a feature inteira, uma das duas"})
    r = verbo(api, "inventario", "criar", "5000", "regra", "--frase", "solta", tmp_path=tmp_path)
    assert r.returncode != 0
    assert "uma das duas" in r.stderr + r.stdout


def test_validar_manda_a_frase_que_o_dono_leu_e_imprime_quem_e_quando(api, tmp_path):
    api.rotas[("POST", "/api/itens/5000/inventario/regras/3/validar")] = (
        200, dict(REGRA3, validada=True, validada_por="engenharia", validada_em="2026-11-17T01:00:00+00:00"))
    r = verbo(api, "inventario", "validar", "5000.r3", "--frase", "a terceira", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "5000.r3 validada por engenharia em 2026-11-17T01:00:00+00:00"
    assert json.loads(api.recebido[0]["corpo"]) == {"frase": "a terceira"}


def test_so_regra_se_valida(api, tmp_path):
    r = verbo(api, "inventario", "validar", "5000.p1", tmp_path=tmp_path)
    assert r.returncode == 2 and "só regra se valida" in r.stderr
    assert not api.recebido


def test_editar_a_frase_avisa_que_a_validacao_se_desfez(api, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000/inventario/regras/3")] = (200, dict(REGRA3, frase="nova"))
    r = verbo(api, "inventario", "editar", "5000.r3", "--frase", "nova", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "5000.r3 editado · não validada"


def test_cortar_ligar_e_desligar_usam_as_rotas_certas(api, tmp_path):
    api.rotas[("POST", "/api/itens/5000/inventario/regras/3/cortar")] = (200, dict(REGRA3, cortada=True))
    api.rotas[("POST", "/api/itens/5000/inventario/regras/3/stories")] = (201, {"chave": "5000.r3"})
    api.rotas[("DELETE", "/api/itens/5000/inventario/regras/3/stories/4317")] = (200, {"chave": "5000.r3"})
    assert verbo(api, "inventario", "cortar", "5000.r3", tmp_path=tmp_path).stdout.strip() == "5000.r3 cortado"
    assert verbo(api, "inventario", "ligar", "5000.r3", "4317", tmp_path=tmp_path).stdout.strip() \
        == "5000.r3 ligada à story 4317"
    assert verbo(api, "inventario", "desligar", "5000.r3", "4317", tmp_path=tmp_path).stdout.strip() \
        == "5000.r3 desligada da story 4317"
    assert json.loads(api.recebido[1]["corpo"]) == {"story": 4317}


def test_chave_invalida_sai_2_sem_chamar_a_api(api, tmp_path):
    r = verbo(api, "inventario", "cortar", "5000.x3", tmp_path=tmp_path)
    assert r.returncode == 2 and "chave inválida" in r.stderr
    assert not api.recebido


def test_ler_a_feature_mostra_a_linha_e_os_itens_por_lista(api, tmp_path):
    api.rotas[("GET", "/api/itens/5000/inventario")] = (200, {
        "linha": "Inventário: 1 peças, 1 regras (0 validadas, 1 sem story), 0 produtos documentais",
        "contagens": {}, "itens": {"pecas": [{"chave": "5000.p1", "descricao": "o serviço", "cortada": False}],
                                   "regras": [REGRA3], "documentos": []}})
    r = verbo(api, "inventario", "ler", "5000", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    saida = r.stdout
    assert saida.splitlines()[0].startswith("Inventário: 1 peças, 1 regras")
    assert "5000.p1 · o serviço" in saida
    assert "5000.r3 · não validada · rege p1 · a terceira" in saida
    assert "caso: a → b" in saida and "mecanismo: o gatilho" in saida
    assert "produtos documentais:" not in saida, "lista vazia não aparece"


def test_ler_com_lista_e_cortados_manda_a_query(api, tmp_path):
    api.rotas[("GET", "/api/itens/5000/inventario")] = (200, {"linha": "x", "itens": {"regras": []}})
    verbo(api, "inventario", "ler", "5000", "--lista", "regra", "--cortados", tmp_path=tmp_path)
    assert api.recebido[0]["query"] == "lista=regras&cortados=1"


def _card(nivel, inventario):
    return {"id": 4317 if nivel == 2 else 5000, "titulo": "o card", "nivel": nivel,
            "nivel_nome": "story" if nivel == 2 else "feature", "estado_nome": "Em execução",
            "estado_fase": "delivery", "estado_derivado": None, "cadeira": "engenharia", "ancestrais": [],
            "bloqueia": [], "bloqueado_por": [], "sign_offs": [], "descricao": "o corpo", "filhas": [],
            "inventario": inventario}


def test_ler_a_feature_acrescenta_so_a_linha_das_contagens_e_nenhum_item(api, tmp_path):
    linha = "Inventário: 7 peças, 40 regras (31 validadas, 5 sem story), 6 produtos documentais"
    api.rotas[("GET", "/api/itens/5000")] = (200, _card(1, {"linha": linha, "contagens": {}}))
    api.rotas[("GET", "/api/registro")] = (200, {"estados": []})   # as filhas abertas da feature
    r = verbo(api, "ler", "5000", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert linha in r.stdout and "o corpo" in r.stdout
    assert "5000.r" not in r.stdout, "os itens não vêm na leitura da feature"
    assert len(r.stdout) < 6000


def test_ler_a_story_traz_as_tres_regras_inteiras_e_os_produtos_documentais(api, tmp_path):
    regras = [dict(REGRA3, chave=f"5000.r{i}", frase=f"regra {i}") for i in (1, 2, 3)]
    docs = [{"chave": "5000.d1", "descricao": "a referência do verbo", "ato_documental": "nasce",
             "natureza": "referencia", "classe_declarada": "referencia-de-verbo", "cortada": False}]
    api.rotas[("GET", "/api/itens/4317")] = (200, _card(2, {"regras": regras, "documentos": docs}))
    r = verbo(api, "ler", "4317", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "regras que esta story cumpre:" in r.stdout
    for i in (1, 2, 3):
        assert f"5000.r{i} · não validada · rege p1 · regra {i}" in r.stdout
    assert r.stdout.count("caso: a → b") == 3 and r.stdout.count("mecanismo: o gatilho") == 3
    assert "produtos documentais que esta story muda:" in r.stdout
    assert "5000.d1 · nasce/referencia · a referência do verbo · classe: referencia-de-verbo" in r.stdout


def test_card_sem_inventario_le_como_antes(api, tmp_path):
    card = _card(2, None)
    del card["inventario"]
    api.rotas[("GET", "/api/itens/4317")] = (200, card)
    r = verbo(api, "ler", "4317", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "regras que esta story cumpre:" not in r.stdout and "o corpo" in r.stdout


def test_o_modelo_dos_outros_atos_segue_como_estava(api, tmp_path):
    r = verbo(api, "inventario", tmp_path=tmp_path)
    assert r.returncode == 2 and "tarefas inventario ler" in r.stderr
    ajuda = verbo(api, "--ajuda", tmp_path=tmp_path)
    assert ajuda.returncode == 0 and "tarefas listar" in ajuda.stdout and "tarefas inventario" in ajuda.stdout
