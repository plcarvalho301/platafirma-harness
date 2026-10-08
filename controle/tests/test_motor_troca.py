"""`motor rag trocar biblioteca`, a bateria por geração e a calibração do sinal de abstenção (card #3264;
arq:0121 §7).

Como `test_motor_indexar.py`: o verbo roda de verdade, como subprocesso, contra um rag-api falso em
127.0.0.1, com registro, token, instância e log num diretório temporário. Prova o que o verbo MANDA à API
(corpo, rota, confirmação) e o que IMPRIME, que é o que o dono lê antes do «sim». A troca em si, o
expurgo e a virada são do rag-api (platafirma-conhecimento, rag/tests/test_troca.py); o critério da
calibração, de `bin/_motor/calibra.py`, tem a conta testada aqui sem a API.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))
import calibra  # noqa: E402

LOTE = "0f0f0f0f-1111-4222-8333-444444444444"
GERACAO = "9c1b0f0e-5a4d-4c60-9a52-1b2c3d4e5f60"
OUTRA = "11111111-2222-4333-8444-555555555555"

# valor cru que a API falsa devolve por tipo de pergunta, por braço ligado na chamada
_NOTA = {
    "sim":     {"positiva": 0.80, "negbaixa": 0.30, "negalta": 0.85, "negobra": 0.60},
    "rerank":  {"positiva": 0.95, "negbaixa": 0.20, "negalta": 0.40, "negobra": 0.30},
}


class _API(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []
    falha: ClassVar[dict] = {}

    def log_message(self, *a):
        pass

    def _responde(self, status, corpo, tipo="application/json"):
        dado = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def _problema(self, status, titulo, detalhe):
        return self._responde(status, {"type": "about:blank", "title": titulo, "detail": detalhe},
                              "application/problem+json")

    def _busca(self, corpo):
        bracos = corpo.get("bracos") or []
        medida = "rerank" if "rerank" in bracos else "sim"
        tipo = next(t for t in _NOTA[medida] if t in corpo["pergunta"].replace("-", ""))
        valor = _NOTA[medida][tipo]
        resposta = {"fontes": [{"obra": "Obra" if tipo == "positiva" else "Outra",
                                "section_id": "sec-1"}],
                    "cobertura": "boa" if valor >= 0.5 else "fraca",
                    "sinal": {"medida": medida, "valor": valor, "piso": 0.5},
                    "tempos_ms": {"total": 5.0}}
        if "veredito" in bracos and "semconceito" in corpo["pergunta"].replace("-", ""):
            resposta["ontologia"] = {"veredito": {"estado": "sem_obra"}}
            resposta["cobertura"] = "ausente"
        return resposta

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        self.pedidos.append(("POST", self.path, self.headers.get("Authorization"), corpo))
        if self.path in self.falha:
            return self._problema(*self.falha[self.path])
        if self.path == "/search":
            return self._responde(200, self._busca(corpo))
        if self.path == "/motor/trocas":
            if corpo.get("aplicar"):
                return self._responde(200, {
                    "modo": "aplicado", "lote": LOTE, "geracao": 7, "a_montar": 5,
                    "impressoes_servindo": 9, "prontas": 4, "trechos_elegiveis": 100,
                    "acompanhar": f"motor rag trocar biblioteca --relatorio {LOTE}"})
            return self._responde(200, {
                "modo": "plano", "particao": "biblioteca", "impressoes_servindo": 9,
                "trechos_elegiveis": 100,
                "servindo": {"geracao": 6, "embedder": "Qwen/Qwen3-Embedding-0.6B"},
                "parametros": {"embedder": corpo["embedder"], "dimensao_trecho": corpo["dimensao"],
                               "prefixo_da_pergunta": "query: ", "prefixo_do_trecho": "passage: ",
                               "fatia_mrl_trecho": True, "dimensao_faceta": 256, "dtype": "bfloat16"},
                "estimativa": {"disco_gb": 5.6, "tempo_h": 1.2, "vazao_trechos_por_s": 60.0,
                               "vram_do_modelo_gb": 2.4},
                "ambiente": {"lotes_de_ingestao_abertos": 0, "lote_de_indexacao_aberto": False,
                             "vram": {"livre_gb": 11.0}}})
        if self.path == "/motor/trocas/virar":
            if corpo.get("aplicar"):
                return self._responde(200, {
                    "modo": "virada", "particao": "biblioteca", "geracao": {"numero": 7},
                    "resultado": {"anterior_numero": 6, "indices_da_anterior_apagados": 540,
                                  "indices_da_nova_servindo": 540},
                    "index_meta": {"apagadas": 2}})
            return self._responde(200, {
                "modo": "plano", "ato": "virar", "geracao": {"numero": 7, "embedder": "nvidia/nemotron"},
                "cobertura": {"aprovadas": 540, "total": 540, "percentual": 100.0}, "hnsw": True,
                "indices_a_servir": 540, "reprovadas": [],
                "apaga": {"geracao": 6, "embedder": "Qwen", "vetores": 261380, "indices": 540,
                          "indices_em_construcao": 0, "folhas": ["vetor_g6_d1024"],
                          "chaves_index_meta": ["embed_model"]},
                "retrato_mais_recente": None, "ajustes": corpo.get("ajustes"),
                "volta": "uma troca nova para o Qwen"})
        if self.path == "/motor/trocas/descartar":
            if corpo.get("aplicar"):
                return self._responde(200, {"modo": "descartada", "resultado": {"folhas_apagadas": 2}})
            return self._responde(200, {
                "modo": "plano", "ato": "descartar", "geracao": {"geracao": 7, "embedder": "nvidia/nemotron"},
                "apaga": {"vetores": 10, "indices": 1, "indices_em_construcao": 1,
                          "folhas": ["vetor_g7_d1024"], "chaves_index_meta": []}})
        return self._problema(404, "RotaDesconhecida", self.path)

    def do_GET(self):
        self.pedidos.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path == "/facets":
            return self._responde(200, {"indice": {"acervo_sha": "abc123456789", "embed_model": "model",
                                                   "embed_backend": "torch"}})
        if self.path == "/motor/trocas/biblioteca":
            return self._responde(200, {
                "particao": "biblioteca", "servindo": {"geracao": 6, "embedder": "Qwen"},
                "sombra": {"geracao": 7, "embedder": "nvidia/nemotron",
                           "cobertura": {"aprovadas": 300, "total": 540, "percentual": 55.6},
                           "faltam_amostra": []},
                "ambiente": {"lotes_de_ingestao_abertos": 0, "lote_de_indexacao_aberto": False,
                             "vram": {"livre_gb": 11.0}}})
        if self.path == f"/motor/trocas/lote/{LOTE}":
            return self._responde(200, {"lote": LOTE, "estado": "concluido", "por_estado": {"montada": 5},
                                        "embedados": 800, "ms": 4000, "itens": [],
                                        "cobertura": {"aprovadas": 9, "total": 9, "percentual": 100.0}})
        return self._problema(404, "LoteNaoEncontrado", "planeje de novo")


@pytest.fixture
def api(tmp_path):
    _API.pedidos, _API.falha = [], {}
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": f"{base}/search",
        "indexacao": f"{base}/motor/indexacoes/lote", "troca": f"{base}/motor/trocas",
        "token_em": "rag/RAG_API_TOKEN", "facets": f"{base}/facets", "medicoes_em": "var/medicoes/rag",
        "ajustes": [], "nao_e_ajuste": {}}}))

    def roda(*args, ambiente=None):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia", **(ambiente or {})}
        return subprocess.run([sys.executable, str(MOTOR), "rag", *args], capture_output=True, text=True,
                              env=env, timeout=120, check=False)

    yield roda, _API.pedidos, instancia
    servidor.shutdown()


# --- trocar: o que o verbo manda e o que mostra ao dono ----------------------------------------------

def test_o_plano_da_troca_manda_embedder_e_dimensao_sem_aplicar_e_mostra_a_estimativa_como_hipotese(api):
    roda, pedidos, _ = api
    r = roda("trocar", "biblioteca", "--embedder", "nvidia/nemotron", "--dimensao", "1024")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith("plano: trocar a biblioteca de g6 (Qwen/Qwen3-Embedding-0.6B) "
                                               "para nvidia/nemotron em 1024 dimensoes")
    assert "estimativa (hipotese, confirma na primeira impressao)" in r.stdout
    assert "para valer: o mesmo comando com --apply" in r.stdout
    assert pedidos[-1] == ("POST", "/motor/trocas", "Bearer tok",
                           {"particao": "biblioteca", "embedder": "nvidia/nemotron", "dimensao": 1024,
                            "aplicar": False, "autor": "ia"})


def test_apply_abre_o_lote_e_diz_como_acompanhar_e_a_memoria_vai_no_corpo(api):
    roda, pedidos, _ = api
    r = roda("trocar", "biblioteca", "--embedder", "nvidia/nemotron", "--dimensao", "1024", "--apply",
             "--memoria", "2GB", "--autor", "dados")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith(f"lote {LOTE} aberto no rag-api, em segundo plano: g7 · 5 a montar")
    assert f"motor rag trocar biblioteca --relatorio {LOTE}" in r.stdout
    assert pedidos[-1][3] == {"particao": "biblioteca", "embedder": "nvidia/nemotron", "dimensao": 1024,
                              "aplicar": True, "autor": "dados", "memoria": "2GB"}


def test_estado_e_relatorio_sao_leitura_e_a_primeira_linha_e_a_cobertura(api):
    roda, pedidos, _ = api
    e = roda("trocar", "biblioteca", "--estado")
    assert e.returncode == 0, e.stderr
    assert e.stdout.splitlines()[0].startswith("cobertura 300/540 impressoes com indice aprovado (55.6%) na g7")
    assert pedidos[-1][:2] == ("GET", "/motor/trocas/biblioteca")
    sem_flag = roda("trocar", "biblioteca")
    assert sem_flag.returncode == 0 and sem_flag.stdout == e.stdout
    rel = roda("trocar", "biblioteca", "--relatorio", LOTE)
    assert rel.returncode == 0, rel.stderr
    assert rel.stdout.splitlines()[0].startswith("cobertura 9/9 impressoes com indice aprovado (100.0%) · "
                                                 f"lote {LOTE}: concluido")
    assert all(p[0] == "GET" for p in pedidos)


def test_o_plano_da_virada_mostra_o_que_apaga_e_a_volta_e_nao_vira(api):
    roda, pedidos, _ = api
    r = roda("trocar", "biblioteca", "--virar", "g7", "--ajuste", "aviso_de_cobertura_fraca=0.583")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0] == ("virada da g7 (nvidia/nemotron): cobertura 540/540 impressoes com "
                                        "indice aprovado (100.0%) · HNSW pronto · 540 indices a servir")
    assert "apaga a g6 (Qwen): 261380 vetores, 540 indices" in r.stdout
    assert "volta: uma troca nova para o Qwen" in r.stdout
    corpo = pedidos[-1][3]
    assert pedidos[-1][1] == "/motor/trocas/virar" and corpo["aplicar"] is False
    assert corpo["ajustes"] == {"aviso_de_cobertura_fraca": 0.583}
    assert "sim" not in corpo and "confirma" not in corpo


def test_a_virada_leva_confirma_sim_e_ajustes_tipados_e_o_sim_do_dono_vai_inteiro(api):
    roda, pedidos, _ = api
    sim = "sim, pode virar e expurgar a g6"
    r = roda("trocar", "biblioteca", "--virar", "g7", "--apply", "--confirma", "g7", "--sim", sim,
             "--ajuste", "aviso_de_cobertura_fraca=0.583", "--ajuste", "veredito-por-conceito=true",
             "--autor", "dados")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0] == ("virada feita: a g7 serve a biblioteca e a g6 foi expurgada "
                                        "(540 indices apagados, 540 servindo na nova)")
    assert pedidos[-1][3] == {"particao": "biblioteca", "geracao": "g7", "aplicar": True, "autor": "dados",
                              "confirma": "g7", "sim": sim,
                              "ajustes": {"aviso_de_cobertura_fraca": 0.583, "veredito_por_conceito": True}}


def test_virgula_decimal_no_ajuste_vira_numero_e_nao_texto(api):
    # `0,61` entrava como texto, a virada o gravava e a busca da biblioteca estourava (revisao de 08/10/2026)
    roda, pedidos, _ = api
    r = roda("trocar", "biblioteca", "--virar", "g7", "--ajuste", "aviso_de_cobertura_fraca=0,61",
             "--ajuste", "aviso_com_revisor=0.7", "--ajuste", "revisor=BAAI/bge-reranker-v2-m3")
    assert r.returncode == 0, r.stderr
    assert pedidos[-1][3]["ajustes"] == {"aviso_de_cobertura_fraca": 0.61, "aviso_com_revisor": 0.7,
                                         "revisor": "BAAI/bge-reranker-v2-m3"}


def test_buscar_na_geracao_fora_de_servico_leva_geracao_no_corpo(api):
    roda, pedidos, _ = api
    r = roda("buscar", "biblioteca", "positiva espaco vetorial", "--geracao", GERACAO)
    assert r.returncode == 0, r.stderr
    corpo = pedidos[-1][3]
    assert pedidos[-1][1] == "/search" and corpo["geracao"] == GERACAO and corpo["particao"] == "biblioteca"
    sem = roda("buscar", "biblioteca", "positiva pergunta")
    assert sem.returncode == 0 and "geracao" not in pedidos[-1][3]


def test_descartar_leva_so_a_confirmacao_e_nunca_o_sim_nem_ajustes(api):
    roda, pedidos, _ = api
    plano = roda("trocar", "biblioteca", "--descartar", "g7")
    assert plano.returncode == 0, plano.stderr
    assert "para valer: --apply --confirma g7" in plano.stdout
    feito = roda("trocar", "biblioteca", "--descartar", "g7", "--apply", "--confirma", "g7",
                 "--sim", "ignorado", "--ajuste", "x=1")
    assert feito.returncode == 0, feito.stderr
    assert feito.stdout.startswith("geracao descartada:")
    assert pedidos[-1][1] == "/motor/trocas/descartar"
    assert pedidos[-1][3] == {"particao": "biblioteca", "geracao": "g7", "aplicar": True, "autor": "ia",
                              "confirma": "g7"}


def test_a_recusa_da_api_vira_exit_da_tabela_da_casa_com_o_motivo(api):
    roda, pedidos, _ = api
    _API.falha["/motor/trocas/virar"] = (409, "ConfirmacaoAusente", "a virada pede --confirma g7")
    r = roda("trocar", "biblioteca", "--virar", "g7", "--apply")
    assert r.returncode == 4 and "ConfirmacaoAusente: a virada pede --confirma g7" in r.stderr
    _API.falha["/motor/trocas/virar"] = (422, "NaoPodeVirar", "cobertura 97%")
    assert roda("trocar", "biblioteca", "--virar", "g7", "--apply").returncode == 1
    _API.falha["/motor/trocas/virar"] = (400, "Invalido", "ajuste desconhecido")
    assert roda("trocar", "biblioteca", "--virar", "g7", "--apply").returncode == 2


def test_uso_errado_sai_2_sem_chamar_a_api(api):
    roda, pedidos, _ = api
    assert roda("trocar", "casa", "--embedder", "x", "--dimensao", "1024").returncode == 2  # a casa fica no Qwen
    assert roda("trocar", "biblioteca", "--embedder", "x").returncode == 2                   # falta a dimensão
    assert roda("trocar", "biblioteca", "--embedder", "x", "--dimensao", "mil").returncode == 2
    assert roda("trocar", "biblioteca", "--virar", "g7", "--descartar", "g7").returncode == 2  # um ato por chamada
    assert roda("trocar", "biblioteca", "--relatorio", "nao-e-uuid").returncode == 2
    assert roda("trocar", "biblioteca", "--virar", "g7", "--ajuste", "sem-igual").returncode == 2
    assert roda("trocar", "biblioteca", "--sem-isso").returncode == 2
    assert roda("trocar", "biblioteca", "--virar").returncode == 2
    assert pedidos == []


def test_o_ajuste_nunca_troca_embedder_o_caminho_da_troca_e_so_o_trocar(api):
    # regra do dono, 03/10/2026: `motor rag ajuste` não troca embedder; só o `trocar`, com plano e virada
    roda, pedidos, _ = api
    r = roda("ajuste", "embed_model", "nvidia/nemotron")
    assert r.returncode != 0
    assert not any(p[1].startswith("/motor/trocas") for p in pedidos)


# --- medir: braços por chamada, geração medida, recorte das negativas ------------------------------

def _gabarito(tmp_path, positivas=24, sem_obra=22, com_obra=2):
    itens = [{"id": f"P{i}", "pergunta": f"positiva {i} onde esta", "estrato": "T2-cadeiras",
              "alvo_obras": ["Obra"], "relevancia": "positiva", "pontuavel": True} for i in range(positivas)]
    for i in range(sem_obra):
        # metade o sinal separa (nota baixa); a outra metade tem nota alta e só o conceito sem obra a pega
        tipo, conceito = ("negbaixa", "") if i % 2 == 0 else ("negalta", " semconceito")
        itens.append({"id": f"N{i}", "pergunta": f"{tipo} {i}{conceito}", "estrato": "T2-cadeiras",
                      "relevancia": "negativa", "pontuavel": True, "nota": "sem obra no acervo"})
    for i in range(com_obra):
        itens.append({"id": f"C{i}", "pergunta": f"negobra {i}", "estrato": "T2-cadeiras",
                      "relevancia": "negativa", "pontuavel": True, "nota": "ganhou obra na reforma"})
    gab = tmp_path / "gabarito.jsonl"
    gab.write_text("\n".join(json.dumps(x) for x in itens) + "\n", encoding="utf-8")
    return gab


def _mede(roda, gab, rotulo, *extra):
    r = roda("medir", "biblioteca", "--gabarito", str(gab), "--k", "8", "--rotulo", rotulo, *extra)
    assert r.returncode == 0, r.stderr
    return r


def test_medir_liga_os_bracos_por_chamada_em_bracos_e_leva_a_geracao(api, tmp_path):
    roda, pedidos, instancia = api
    gab = _gabarito(tmp_path, positivas=1, sem_obra=2, com_obra=1)
    r = _mede(roda, gab, "nova-tudo", "--rerank", "--expansao", "--veredito", "--geracao", GERACAO)
    buscas = [p[3] for p in pedidos if p[1] == "/search"]
    assert buscas and all(b["bracos"] == ["rerank", "expansao", "veredito"] for b in buscas)
    assert all(b["geracao"] == GERACAO for b in buscas)
    # a flag solta que a bateria mandava e a API não lê (#3264) não vai mais no corpo
    assert all("rerank" not in b and "expansao" not in b for b in buscas)
    assert f"GERACAO MEDIDA: {GERACAO}" in r.stdout and "veredito por conceito LIGADO" in r.stdout
    salvo = json.loads(next((instancia / "var" / "medicoes" / "rag").glob("*-nova-tudo.json")).read_text())
    assert salvo["geracao"] == GERACAO and salvo["veredito"] is True
    assert salvo["bracos"] == ["rerank", "expansao", "veredito"]


def test_medir_sem_flag_nao_manda_bracos_nem_geracao_e_mede_o_servido(api, tmp_path):
    roda, pedidos, _ = api
    _mede(roda, _gabarito(tmp_path, positivas=1, sem_obra=1, com_obra=0), "servido")
    corpo = [p[3] for p in pedidos if p[1] == "/search"][0]
    assert "bracos" not in corpo and "geracao" not in corpo


def test_medir_separa_as_negativas_sem_obra_das_que_ganharam_obra(api, tmp_path):
    roda, pedidos, instancia = api
    gab = _gabarito(tmp_path, positivas=2, sem_obra=22, com_obra=2)
    r = _mede(roda, gab, "servido")
    # nota 0,30 e 0,85 contra o piso 0,5 da API falsa: a «fraca» é só a de nota baixa (metade das 22);
    # a negativa com obra tem 0,60 («boa»), e a conta a mostra à parte, sem somá-la às 22
    assert "abstenção 11/24" in r.stdout
    assert "sem obra 11/22 · com obra 0/2 (abster nelas e erro)" in r.stdout
    salvo = json.loads(next((instancia / "var" / "medicoes" / "rag").glob("*-servido.json")).read_text())
    assert salvo["abstencao_por_grupo"] == {"sem_obra": "11/22", "com_obra": "0/2"}
    grupos = {l["grupo"] for l in salvo["perguntas"]}
    assert grupos == {"t2", "neg_sem_obra", "neg_com_obra"}
    linha = next(l for l in salvo["perguntas"] if l["id"] == "N0")
    assert (linha["medida"], linha["valor"], linha["piso"], linha["cobertura"]) == ("sim", 0.3, 0.5, "fraca")


def test_o_delta_so_compara_rodadas_da_mesma_geracao(api, tmp_path):
    roda, _, _ = api
    gab = _gabarito(tmp_path, positivas=1, sem_obra=1, com_obra=0)
    _mede(roda, gab, "servido")
    nova = _mede(roda, gab, "nova", "--geracao", GERACAO)
    assert "primeira medicao: nao ha baseline" in nova.stdout     # a servida não é baseline da sombra
    de_novo = _mede(roda, gab, "nova-2", "--geracao", GERACAO, "--veredito")
    assert "contra " in de_novo.stdout and "mudou na rodada: veredito False -> True" in de_novo.stdout


# --- calibrar: do que a bateria salvou ao sinal que vence -------------------------------------------

def _rodadas(roda, gab, *, geracao=GERACAO):
    _mede(roda, gab, "nova-sim", "--geracao", geracao)
    _mede(roda, gab, "nova-revisor", "--geracao", geracao, "--rerank")
    _mede(roda, gab, "nova-veredito", "--geracao", geracao, "--veredito")


def test_calibrar_escolhe_o_revisor_quando_ele_separa_as_22_e_a_similaridade_so_11(api, tmp_path):
    roda, _, instancia = api
    _rodadas(roda, _gabarito(tmp_path))
    n_busca = len([p for p in _API.pedidos if p[1] == "/search"])
    r = roda("medir", "biblioteca", "--calibrar", "nova-sim,nova-revisor")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len([p for p in _API.pedidos if p[1] == "/search"]) == n_busca      # calibrar não chama a busca
    assert "VENCE: nova-revisor com 22/22 (minimo 16)" in r.stdout
    # o revisor so vale na busca se a geracao o liga por padrao (`revisor`), e a virada exige o piso da
    # similaridade da mesma geracao: o comando impresso roda como esta
    assert ("--ajuste aviso_com_revisor=0.95 --ajuste aviso_de_cobertura_fraca=0.6 "
            "--ajuste revisor=BAAI/bge-reranker-v2-m3") in r.stdout
    assert "as negativas com obra (abster nelas e erro) saem a parte: 2 no gabarito" in r.stdout
    salvo = json.loads(next((instancia / "var" / "medicoes" / "rag").glob("*-calibracao.json")).read_text())
    assert salvo["ajuste"] == ["aviso_com_revisor=0.95", "aviso_de_cobertura_fraca=0.6",
                                "revisor=BAAI/bge-reranker-v2-m3"]
    assert salvo["resultado"]["vencedora"] == "nova-revisor"


def test_calibrar_com_veredito_leva_os_dois_ajustes_e_a_similaridade_sozinha_nao_chega_a_16(api, tmp_path):
    roda, _, _ = api
    _rodadas(roda, _gabarito(tmp_path))
    r = roda("medir", "biblioteca", "--calibrar", "nova-sim,nova-veredito")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VENCE: nova-veredito com 22/22" in r.stdout
    assert "--ajuste aviso_de_cobertura_fraca=0.6 --ajuste veredito_por_conceito=true" in r.stdout
    so_sim = roda("medir", "biblioteca", "--calibrar", "nova-sim")
    assert so_sim.returncode == 4
    assert "NENHUM SINAL ATINGE 16/22 (melhor: nova-sim com 11)" in so_sim.stdout
    assert "a particao NAO vira" in so_sim.stdout and "VENCE" not in so_sim.stdout


def test_calibrar_empate_vence_o_primeiro_da_lista(api, tmp_path):
    roda, _, _ = api
    _rodadas(roda, _gabarito(tmp_path))
    barato = roda("medir", "biblioteca", "--calibrar", "nova-sim,nova-veredito,nova-revisor")
    caro = roda("medir", "biblioteca", "--calibrar", "nova-sim,nova-revisor,nova-veredito")
    assert "VENCE: nova-veredito com 22/22" in barato.stdout
    assert "VENCE: nova-revisor com 22/22" in caro.stdout


def test_calibrar_recusa_rodada_que_falta_e_rodadas_de_geracoes_diferentes(api, tmp_path):
    roda, _, _ = api
    gab = _gabarito(tmp_path, positivas=1, sem_obra=2, com_obra=0)
    _mede(roda, gab, "nova-sim", "--geracao", GERACAO)
    _mede(roda, gab, "outra-sim", "--geracao", OUTRA)
    falta = roda("medir", "biblioteca", "--calibrar", "nova-sim,nunca-medida")
    assert falta.returncode == 1 and "sem medicao salva" in falta.stderr and "nunca-medida" in falta.stderr
    mistura = roda("medir", "biblioteca", "--calibrar", "nova-sim,outra-sim")
    assert mistura.returncode == 1 and "nao sao da mesma geracao" in mistura.stderr
    filtrada = roda("medir", "biblioteca", "--calibrar", "nova-sim,outra-sim", "--geracao", OUTRA)
    assert filtrada.returncode == 1 and "nova-sim" in filtrada.stderr   # o filtro tira a rodada da outra geração
    assert roda("medir", "biblioteca", "--calibrar").returncode == 2
    assert roda("medir", "biblioteca", "--calibrar", "a,a").returncode == 2


# --- a conta, sem a API ------------------------------------------------------------------------------

def _linha(grupo, valor, **extra):
    return {"grupo": grupo, "valor": valor, "cobertura": "boa" if (valor or 0) >= 0.5 else "fraca",
            "medida": "sim" if valor is not None else None, **extra}


def test_abstem_por_nota_abaixo_do_piso_por_busca_vazia_e_por_conceito_sem_obra_mas_nunca_por_codigo_exato():
    assert calibra.abstem(_linha("t2", 0.40), 0.5) is True
    assert calibra.abstem(_linha("t2", 0.50), 0.5) is False            # no piso serve: abstém quem está ABAIXO
    assert calibra.abstem({"grupo": "t2", "cobertura": "vazia", "valor": None}, 0.0) is True
    assert calibra.abstem({"grupo": "t2", "cobertura": "boa", "valor": 0.9, "veredito": "sem_obra"}, 0.0) is True
    assert calibra.abstem({"grupo": "t2", "cobertura": "boa", "medida": "codigo_exato", "valor": None}, 0.9) is False


def test_o_piso_sai_arredondado_para_baixo_sem_perder_um_ulp():
    assert calibra._arredonda_para_baixo(0.583) == 0.583    # int(0.583 * 1000) dá 582
    assert calibra._arredonda_para_baixo(0.5829) == 0.582
    assert calibra._arredonda_para_baixo(0.57) == 0.57


def test_o_controle_paga_a_perda_de_t2_que_a_similaridade_tem_e_as_outras_rodadas_cabem_nela():
    sim = ([_linha("t2", v) for v in (0.9, 0.8, 0.45)]
           + [_linha("neg_sem_obra", v) for v in (0.1, 0.2, 0.3, 0.7)])
    res = calibra.calibrar({"sim": sim}, "sim")
    r = res["rodadas"]["sim"]
    # o piso que erra menos cala as tres negativas baixas e serve as tres T2: orcamento zero
    assert (res["piso_do_controle"], res["orcamento_t2"]) == (0.45, 0)
    assert (r["piso"], r["neg_sem_obra"], r["t2_abstidas"]) == (0.45, 3, 0)


def test_rodada_que_cala_t2_de_qualquer_jeito_fica_fora_do_orcamento_e_nao_vence():
    # o veredito por conceito cala pelo conceito, qualquer que seja o piso: se cala T2 que a busca achou,
    # paga alem do que a similaridade paga
    sim = [_linha("t2", 0.9), _linha("neg_sem_obra", 0.3)]
    ver = [_linha("t2", 0.9, veredito="sem_obra"), _linha("neg_sem_obra", 0.3)]
    res = calibra.calibrar({"sim": sim, "ver": ver}, "sim")
    assert res["rodadas"]["ver"].get("fora_do_orcamento") is True
    assert res["vencedora"] == "sim"


def test_t2_que_a_busca_errou_nao_custa_orcamento_quando_o_piso_a_cala():
    # a T2 sem `rank` (a busca nao a achou) abstida nao e perda: ninguem perdeu uma resposta certa
    sim = ([_linha("t2", 0.9, rank=1) for _ in range(30)] + [_linha("t2", 0.2, rank=None) for _ in range(5)]
           + [_linha("neg_sem_obra", v) for v in (0.1, 0.15, 0.5)])
    res = calibra.calibrar({"sim": sim}, "sim")
    r = res["rodadas"]["sim"]
    assert r["de_t2"] == 30 and r["t2_abstidas"] == 0
    assert r["neg_sem_obra"] == 3 and r["piso"] == 0.9


def test_abaixo_de_16_das_22_a_particao_nao_vira_e_16_vira():
    def rodada(n_abstidas):
        # T2 em numero maior que as negativas servidas: o piso que erra menos nao e o de calar tudo
        return ([_linha("t2", 0.9) for _ in range(30)]
                + [_linha("neg_sem_obra", 0.1) for _ in range(n_abstidas)]
                + [_linha("neg_sem_obra", 0.95) for _ in range(22 - n_abstidas)])
    assert calibra.calibrar({"s": rodada(15)}, "s")["atinge_o_minimo"] is False
    assert calibra.calibrar({"s": rodada(16)}, "s")["atinge_o_minimo"] is True
    assert calibra.MINIMO_NEGATIVAS == 16


def test_as_cinco_que_ganharam_obra_aparecem_a_parte_e_nao_somam_as_22():
    linhas = ([_linha("t2", 0.9)] + [_linha("neg_sem_obra", 0.1) for _ in range(22)]
              + [_linha("neg_com_obra", 0.05) for _ in range(5)])
    r = calibra.calibrar({"s": linhas}, "s")["rodadas"]["s"]
    assert r["neg_sem_obra"] == 22 and r["de_neg_sem_obra"] == 22
    assert (r["neg_com_obra_abstidas"], r["de_neg_com_obra"]) == (5, 5)


def test_calibrar_sem_o_controle_nas_rodadas_e_erro():
    with pytest.raises(KeyError):
        calibra.calibrar({"a": []}, "b")
