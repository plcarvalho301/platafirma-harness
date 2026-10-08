"""`motor rag escrever biblioteca` e bin/_motor/escritor.py (card #3349; padrao protocolo-medicao-rag, «Unidade da marca»).

A lógica (prompt, leitura da saída do modelo, rodapé, mapa, piloto, terceiro braço, envelope e aceite) é medida em
funções puras. A fiação roda de verdade, como subprocesso, contra um rag-api falso (/search e /facets), um ollama falso
(/api/chat) e um `docker` falso no PATH (o braço léxico dentro do contêiner e o env do servido). Não prova o modelo
real nem o `candidatos_lexicais` real: isso se confere no ar, pelo `--plano` e pelas respostas lidas.
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

import escritor  # noqa: E402


def sec(i, texto=None):
    return {"chave": f"obra#s{i}", "titulo": f"Obra › Seção {i}", "texto": texto or f"texto da seção {i}", "secao_id": f"id-{i}"}


SECOES = [sec(i) for i in range(1, 9)]


def saida(resposta="Resposta curta.", mapa=None):
    return json.dumps({"resposta": resposta, "mapa": [{"afirmacao": "x", "secoes": [1]}] if mapa is None else mapa})


# --- funções puras ---------------------------------------------------------------------------------------


def test_o_prompt_numera_as_secoes_corta_o_texto_longo_e_nao_leva_o_braco():
    m = escritor.montar_mensagens("o que é X?", [sec(1), sec(2, "palavra " * 1000)])
    assert [x["role"] for x in m] == ["system", "user"]
    u = m[1]["content"]
    assert u.startswith("Pergunta: o que é X?") and "[1] Obra › Seção 1" in u and "[2] Obra › Seção 2" in u
    assert u.count("palavra") < 1000 and "[…]" in u
    assert "braço" not in u.lower() and "servido" not in u.lower() and "léxico" not in u.lower()


CONTEXTO = ("[1] (a.pdf · s1) — T1\n(contexto do pai · p)\ncorpo um\n---\nlinha\n\n"
            "[2] (b.pdf · s2) — T2\n(contexto do pai · p2)\ncorpo dois\n\ncom segundo parágrafo\n\n"
            "[3] (a.pdf · s1) — T1 de novo\ncorpo repetido")


def test_o_texto_da_secao_vem_do_contexto_e_a_chave_e_o_uuid_da_secao():
    assert set(escritor.blocos_do_contexto(CONTEXTO)) == {1, 2, 3}
    assert escritor.blocos_do_contexto(CONTEXTO)[2].endswith("corpo dois\n\ncom segundo parágrafo")
    fontes = [{"n": 1, "obra": "Obra A", "arquivo": "a.pdf", "section_id": "s1", "secao_id": "uuid-1", "breadcrumb": ["Cap", "Seção"], "texto": None},
              {"n": 2, "obra": "Obra B", "arquivo": "b.pdf", "section_id": "s2", "secao_id": "uuid-2", "breadcrumb": [], "texto": None},
              {"n": 3, "obra": "Obra A", "arquivo": "a.pdf", "section_id": "s1", "secao_id": "uuid-1", "breadcrumb": ["Cap"], "texto": None},
              {"n": 4, "obra": "Sem bloco", "secao_id": "uuid-4", "breadcrumb": [], "texto": None}]
    out = escritor.secoes_do_servido({"fontes": fontes, "contexto": CONTEXTO})
    assert [s["chave"] for s in out] == ["uuid-1", "uuid-2"]  # repetida e sem texto saem
    assert out[0]["titulo"] == "Obra A › Cap › Seção" and out[1]["titulo"] == "Obra B"
    assert out[0]["texto"].startswith("(contexto do pai · p)\ncorpo um") and out[0]["section_id"] == "s1" and out[0]["arquivo"] == "a.pdf"
    assert len(escritor.secoes_do_servido({"fontes": fontes, "contexto": CONTEXTO}, k=1)) == 1
    assert escritor.secoes_do_servido({"fontes": fontes}) == [] and escritor.secoes_do_servido({}) == []


def test_interpretar_le_json_puro_embrulhado_e_com_raciocinio():
    for bruto in (saida(), "texto antes " + saida() + " depois", "<think>penso</think>" + saida()):
        texto, mapa, avisos, palavras = escritor.interpretar(bruto, SECOES)
        assert texto == "Resposta curta." and mapa == [{"afirmacao": "x", "secoes": ["obra#s1"]}] and palavras == 2


@pytest.mark.parametrize("bruto", ["", "sem json", "{}", '{"resposta": ""}', '{"resposta": 3}', "[1, 2]"])
def test_saida_que_nao_e_resposta_volta_none(bruto):
    assert escritor.interpretar(bruto, SECOES) is None


def test_marca_n_no_meio_do_texto_sai_e_fica_avisada():
    texto, _, avisos, _ = escritor.interpretar(saida("A regra vale [1] e também [2, 3]. Fim."), SECOES)
    assert texto == "A regra vale e também. Fim." or "[" not in texto
    assert "marcas [n] removidas do texto" in avisos


def test_afirmacao_sem_secao_valida_sai_do_mapa_e_fica_contada():
    mapa = [{"afirmacao": "boa", "secoes": [2, 2, 1]}, {"afirmacao": "sem lista", "secoes": []},
            {"afirmacao": "fora", "secoes": [99]}, {"afirmacao": "", "secoes": [1]}, {"afirmacao": "tipo", "secoes": ["1"]}, "lixo"]
    _, m, avisos, _ = escritor.interpretar(saida(mapa=mapa), SECOES)
    assert m == [{"afirmacao": "boa", "secoes": ["obra#s1", "obra#s2"]}]
    assert any("5 afirmação(ões) do mapa sem seção válida" in a for a in avisos)


def test_resposta_acima_do_teto_de_palavras_avisa_sem_cortar():
    _, _, avisos, palavras = escritor.interpretar(saida("palavra " * 500), SECOES)
    assert palavras == 500 and any("acima do teto" in a for a in avisos)


def test_rodape_lista_as_secoes_do_mapa_e_o_mapa_vazio_cai_nas_tres_primeiras_consultadas():
    foot, de = escritor.rodape([{"afirmacao": "a", "secoes": ["obra#s5", "obra#s2"]}], SECOES)
    assert [s["chave"] for s in foot] == ["obra#s2", "obra#s5"] and de is False
    foot, de = escritor.rodape([], SECOES)
    assert [s["chave"] for s in foot] == ["obra#s1", "obra#s2", "obra#s3"] and de is True


def _gerador(saidas):
    chamadas = []

    def gerar(mensagens, tentativa):
        chamadas.append(tentativa)
        return {"texto": saidas[len(chamadas) - 1], "tokens_prompt": 100, "tokens_saida": 50, "segundos": 2.0}
    return gerar, chamadas


def test_escrever_resposta_soma_o_custo_e_tenta_de_novo_com_outra_semente_ate_tres_vezes():
    gerar, ch = _gerador(["lixo", "mais lixo", saida()])
    r = escritor.escrever_resposta("p?", SECOES, gerar)
    assert ch == [0, 1, 2] and r["carimbo"] == {"tentativas": 3, "segundos": 6.0, "tokens_prompt": 300, "tokens_saida": 150, "avisos": []}
    gerar, ch = _gerador(["lixo"] * 3)
    with pytest.raises(RuntimeError):
        escritor.escrever_resposta("p?", SECOES, gerar)
    assert ch == [0, 1, 2]


def test_braco_sem_nenhuma_secao_nao_chama_o_modelo():
    gerar, ch = _gerador([])
    r = escritor.escrever_resposta("p?", [], gerar)
    assert ch == [] and r["resposta"] == escritor.SEM_SECOES and r["rodape"] == [] and "sem nenhuma seção" in r["carimbo"]["avisos"][0]


def test_o_piloto_repoe_a_recusada_pela_reserva_em_ordem():
    linhas = [{"id": f"p{i}", "papel": "piloto"} for i in range(1, 21)] + [{"id": f"r{i}", "papel": "reserva"} for i in range(1, 4)]
    ids = [l["id"] for l in escritor.escolher_piloto(linhas, {"p3", "p7"})]
    assert len(ids) == 20 and "p3" not in ids and "p7" not in ids and ids[-2:] == ["r1", "r2"]
    assert [l["id"] for l in escritor.escolher_piloto(linhas, {"p3", "r1"})][-1] == "r2"
    assert len(escritor.escolher_piloto(linhas[:5], set())) == 5


def test_terceiro_braco_vira_expansao_so_se_o_revisor_nao_mudou_nada_em_nenhuma_pergunta():
    a = [sec(i) for i in range(1, 4)]
    assert escritor.decidir_terceiro_braco([(a, a, 0)] * 5)[0] == "expansao"
    assert escritor.decidir_terceiro_braco([(a, a, 0), (a, a[::-1][:2] + [sec(9)], 0)])[0] == "revisor"
    assert escritor.decidir_terceiro_braco([(a, a, 310.0)])[0] == "revisor"  # igual mas pagou rerank: o revisor existe


def _resultados(n=20, vazio=False):
    return {f"esc-{i:08d}": {b: {"resposta": f"resposta {n}-{i}", "mapa": [{"afirmacao": "a", "secoes": ["obra#s1"]}],
                                 "rodape": [] if vazio else [sec(1)], "de_consulta": False, "palavras": 3,
                                 "carimbo": {"tentativas": 1, "segundos": 1.0, "tokens_prompt": 10, "tokens_saida": 5, "avisos": []}}
                             for n, b in enumerate(("servido", "lexico", "terceiro"))} for i in range(n)}


def _piloto(n=20):
    return [{"id": f"esc-{i:08d}", "pergunta": f"pergunta {i}?", "cadeira": "desconhecida", "data": "2026-10-01"} for i in range(n)]


CARIMBO = {"acervo": {"acervo_sha": "a"}, "motor": {"k": 8}, "vocabulario": {"versao": "v"}, "gabarito": {"versao_id": "g"}, "escritor": {"modelo": "m"}}


def _lote(**kw):
    return escritor.montar_lote("lote-1", "gv", "v1", _piloto(), _resultados(**kw), "revisor", CARIMBO, "42", False)


def test_o_lote_publico_tem_so_os_campos_que_a_tela_le_e_o_braco_e_o_mapa_ficam_nas_internas():
    e = _lote()
    assert set(e["corpo"]) == {"lote_id", "criterio_versao", "passada", "perguntas"}
    for p in e["corpo"]["perguntas"]:
        assert set(p) == {"pergunta_id", "texto", "cadeira", "data", "respostas"} and len(p["respostas"]) == 3
        for r in p["respostas"]:
            assert set(r) == {"resposta_id", "texto", "secoes"} and all(set(s) == {"chave", "titulo"} for s in r["secoes"])
    texto = json.dumps(e["corpo"])
    assert not re.search(r"servido|lexico|revisor|expansao|mapa|braco", texto)
    assert len(e["respostas"]) == 60 and {r["braco"] for r in e["respostas"]} == {"servido", "lexico", "revisor"}


def test_resposta_id_e_opaco_e_a_ordem_dos_bracos_varia_entre_perguntas():
    e = _lote()
    ids = [r["resposta_id"] for r in e["respostas"]]
    assert len(set(ids)) == 60 and all(re.fullmatch(r"re-[0-9a-f]{12}", i) for i in ids)
    por_id = {r["resposta_id"]: r["braco"] for r in e["respostas"]}
    ordens = {tuple(por_id[r["resposta_id"]] for r in p["respostas"]) for p in e["corpo"]["perguntas"]}
    assert len(ordens) >= 3  # embaralhado: não é sempre servido, léxico, revisor
    again = escritor.montar_lote("lote-1", "gv", "v1", _piloto(), _resultados(), "revisor", CARIMBO, "42", False)
    o2 = {tuple({r["resposta_id"]: r["braco"] for r in again["respostas"]}[x["resposta_id"]] for x in p["respostas"]) for p in again["corpo"]["perguntas"]}
    assert o2 == ordens  # mesma semente, mesma ordem de braços


def test_o_aceite_passa_no_lote_bom_e_acusa_cada_defeito():
    assert escritor.conferir_aceite(_lote(), 20) == []
    assert any("sem seção no rodapé" in p for p in escritor.conferir_aceite(_lote(vazio=True), 20))
    e = _lote()
    e["respostas"][0]["mapa"].append({"afirmacao": "solta", "secoes": []})
    e["corpo"]["perguntas"][0]["respostas"][0]["texto"] = "tem marca [3] no meio"
    del e["carimbo"]["vocabulario"]
    ps = escritor.conferir_aceite(e, 20)
    assert any("sem seção no mapa" in p for p in ps) and any("marca [n]" in p for p in ps) and any("«vocabulario»" in p for p in ps)
    assert any("esperava 21" in p for p in escritor.conferir_aceite(_lote(), 21))


# --- o verbo, de ponta a ponta com rag, ollama e docker falsos ---------------------------------------------


class _Rag(BaseHTTPRequestHandler):
    pedidos: list = []
    revisor_muda = True

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
        self._json({"indice": {"acervo_sha": "abc123456789", "embed_model": "m", "vocabulario_versao": "voc-1"}})

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.pedidos.append(corpo)
        ordem = list(range(1, 9))
        rerank_ms = 0.0
        if corpo.get("bracos") == ["rerank"] and self.revisor_muda:
            ordem, rerank_ms = [8, 7, 1, 2, 3, 4, 5, 6], 310.0
        # como o /search real: fontes[].texto vem nulo e o texto das secoes mora no `contexto`, em blocos [n]
        self._json({"fontes": [{"n": n, "obra": "Obra", "arquivo": "obra.pdf", "breadcrumb": [f"Seção {i}"], "section_id": f"s{i}",
                                "secao_id": f"id-{i}", "texto": None} for n, i in enumerate(ordem, 1)],
                    "contexto": "\n\n".join(f"[{n}] (obra.pdf · s{i}) — Seção {i}\n(contexto do pai · pai)\ntexto da seção {i}"
                                           for n, i in enumerate(ordem, 1)),
                    "tempos_ms": {"rerank": rerank_ms, "total": 20.0}})


class _Ollama(BaseHTTPRequestHandler):
    chamadas: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.chamadas.append(corpo)
        resposta = {"resposta": "A regra vale [1] e a exceção também [2].",
                    "mapa": [{"afirmacao": "A regra vale", "secoes": [1]}, {"afirmacao": "a exceção", "secoes": [2, 3]}]}
        dado = json.dumps({"message": {"content": json.dumps(resposta)}, "prompt_eval_count": 900, "eval_count": 120}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)


DOCKER_FALSO = """#!{python}
import json, sys
a = sys.argv[1:]
if a[0] == "inspect":
    print("RRF_K=60\\nHYBRID_LEXICAL=false\\nRETRIEVAL_MODE=hybrid")
else:
    env = [x for x in a if x.startswith("LEX_ARGS=")][0][len("LEX_ARGS="):]
    itens = json.loads(env)["itens"]
    print("linha de log antes")
    print(json.dumps({{pid: {{"modo": "and", "secoes": [{{"chave": f"lex#{{i}}", "secao_id": f"lex-{{i}}", "titulo": f"Lexica › {{i}}", "texto": f"trecho lexico {{i}}"}}
                            for i in range(1, 9)]}} for pid, q in itens}}))
"""


@pytest.fixture
def verbo(tmp_path):
    rag = HTTPServer(("127.0.0.1", 0), _Rag)
    olm = HTTPServer(("127.0.0.1", 0), _Ollama)
    for s in (rag, olm):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    _Rag.pedidos, _Rag.revisor_muda, _Ollama.chamadas = [], True, []
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": "rag-extractor-api", "stack": "rag", "endpoint": f"http://127.0.0.1:{rag.server_port}/search",
        "facets": f"http://127.0.0.1:{rag.server_port}/facets", "token_em": "rag/RAG_API_TOKEN", "medicoes_em": "var/medicoes/rag",
        "ajustes": [], "nao_e_ajuste": {}}}))
    lista = tmp_path / "escada.jsonl"
    linhas = ([{"id": f"esc-p{i}", "pergunta": f"pergunta {i}?", "cadeira": "desconhecida", "data": "2026-10-01", "papel": "piloto", "posicao": i}
               for i in range(1, 5)]
              + [{"id": f"esc-r{i}", "pergunta": f"reserva {i}?", "cadeira": "desconhecida", "data": "2026-10-02", "papel": "reserva", "posicao": 200 + i}
                 for i in range(1, 3)])
    lista.write_text("\n".join(json.dumps(l) for l in linhas) + "\n")

    def roda(*args, **kw):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia), "OPS_LOG_DIR": str(tmp_path / "ops"),
               "PF_CADEIRA": "ia", "OLLAMA_BASE_URL": f"http://127.0.0.1:{olm.server_port}", "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", "escrever", "biblioteca", "--lista", str(lista), *args],
                              capture_output=True, text=True, env=env, timeout=120, check=False)

    yield roda, tmp_path, instancia
    rag.shutdown()
    olm.shutdown()


COMUNS = ("--versao", "gv-1", "--criterio-versao", "v1", "--lote-id", "t1")


def test_plano_decide_o_terceiro_braco_pelo_revisor_e_nao_escreve_nada(verbo):
    roda, tmp, inst = verbo
    r = roda("--plano", "--lote-id", "t1")
    assert r.returncode == 0, r.stderr
    assert "lote t1 · 4 perguntas" in r.stdout
    assert "terceiro braco: revisor (o revisor rodou (rerank acima de 0 ms) ou mudou o top-8" in r.stdout and "nada escrito" in r.stdout
    assert "mesmo conjunto do servido em 4/4 e na mesma ordem em 0/4" in r.stdout  # o falso so reordena, como o revisor real
    assert "sem nenhuma secao: {'servido': 0, 'lexico': 0, 'terceiro': 0}" in r.stdout and "lexico por modo: {'and': 4}" in r.stdout
    assert _Ollama.chamadas == []
    assert (inst / "var" / "medicoes" / "rag" / "escritor-t1.json").is_file()


def test_revisor_que_nao_muda_nada_vira_expansao_e_a_busca_do_terceiro_manda_bracos_expansao(verbo):
    roda, tmp, _ = verbo
    _Rag.revisor_muda = False
    r = roda("--plano", "--lote-id", "t2")
    assert r.returncode == 0, r.stderr
    assert "terceiro braco: expansao (o revisor não mudou o top-8" in r.stdout
    assert ["expansao"] in [p.get("bracos") for p in _Rag.pedidos]


def test_escreve_o_piloto_com_a_recusada_reposta_e_monta_o_envelope_que_passa_no_aceite(verbo):
    roda, tmp, _ = verbo
    saida_ = tmp / "envelope.json"
    r = roda(*COMUNS, "--saida", str(saida_), "--recusar", "esc-p2")
    assert r.returncode == 0, r.stderr + r.stdout
    assert "aceite: 4 perguntas e 12 respostas" in r.stdout and "FORA DO ACEITE" not in r.stdout
    e = json.loads(saida_.read_text())
    ids = [p["pergunta_id"] for p in e["corpo"]["perguntas"]]
    assert ids == ["esc-p1", "esc-p3", "esc-p4", "esc-r1"] and len(e["respostas"]) == 12
    assert e["gabarito_versao_id"] == "gv-1" and e["criterio_versao"] == "v1" and e["passada"] == "primeira" and e["ativo"] is False
    assert {r_["braco"] for r_ in e["respostas"]} == {"servido", "lexico", "revisor"}
    assert e["carimbo"]["vocabulario"]["versao"] == "voc-1" and e["carimbo"]["acervo"]["acervo_sha"] == "abc123456789"
    assert e["carimbo"]["gabarito"]["recusadas"] == ["esc-p2"] and e["carimbo"]["motor"]["servido"]["RRF_K"] == "60"
    assert e["carimbo"]["escritor"]["modelo"] == "qwen3.5:9b" and e["carimbo"]["custo"]["lexico"]["tokens_saida"] == 480
    assert not re.search(r"\[\d", json.dumps(e["corpo"]))  # nenhuma marca [n] no meio do texto
    # mesmo modelo, prompt e semente nos três braços
    assert {c["model"] for c in _Ollama.chamadas} == {"qwen3.5:9b"}
    assert {c["options"]["seed"] for c in _Ollama.chamadas} == {42} and {c["options"]["temperature"] for c in _Ollama.chamadas} == {0}
    assert len({c["messages"][0]["content"] for c in _Ollama.chamadas}) == 1
    lex = [r_ for r_ in e["respostas"] if r_["braco"] == "lexico"][0]
    assert lex["secoes"][0]["chave"].startswith("lex#") and [m["secoes"] for m in lex["mapa"]] == [["lex#1"], ["lex#2", "lex#3"]]


def test_a_redacao_retoma_do_estado_sem_reescrever_o_que_ja_estava(verbo):
    roda, tmp, _ = verbo
    saida_ = tmp / "envelope.json"
    r1 = roda(*COMUNS, "--saida", str(saida_), "--tempo", "0")
    assert r1.returncode == 1 and "INCOMPLETO: 0/12" in r1.stdout
    antes = len(_Ollama.chamadas)
    r2 = roda(*COMUNS, "--saida", str(saida_))
    assert r2.returncode == 0, r2.stderr
    assert len(_Ollama.chamadas) - antes == 12 and saida_.is_file()
    n_busca = len(_Rag.pedidos)
    r3 = roda(*COMUNS, "--saida", str(saida_))
    assert r3.returncode == 0 and len(_Ollama.chamadas) - antes == 12 and len(_Rag.pedidos) == n_busca  # nada refeito


@pytest.mark.parametrize("args", [(), ("--saida", "x.json"), ("--saida", "x.json", "--versao", "g"), ("--terceiro-braco", "outro", "--plano"),
                                  ("--sem-isso",), ("--tempo",)])
def test_uso_errado_sai_2_sem_chamar_nada(verbo, args):
    roda, _, _ = verbo
    assert roda(*args).returncode == 2
    assert _Rag.pedidos == [] and _Ollama.chamadas == []
