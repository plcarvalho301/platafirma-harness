"""`motor rag parear biblioteca` e bin/_motor/par_consulta.py (card #3360, passo 9; spec motor-do-conhecimento §2b).

A lógica (frases do dono, as três consultas, sobreposição, o que o dono já julgou, o lote e o aceite) é medida em funções
puras. A fiação roda de verdade, como subprocesso, contra um rag-api falso (/search e /facets), um ollama falso (/api/chat) e uma
marcacao-api falsa (rotas /interno/ de leitura). Não prova o modelo nem a busca reais: isso se confere no ar, pelo `--plano` e
pelas respostas lidas. Os eventos da tela têm a forma que a marcacao-api devolve (marca por resposta_id, preferência por
pergunta_id com escolha «1», «2», «3» ou «empate», exclusão com motivo).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "lib"))
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import par_consulta as pc  # noqa: E402

P1, P2, P3 = "esc-aaaa1111", "esc-bbbb2222", "esc-cccc3333"
LISTA = [
    {"id": P1, "papel": "piloto", "posicao": 1, "cadeira": "desconhecida", "data": "2026-10-03",
     "pergunta": "UTF-8 decoding truncated multibyte sequence byte boundary continuation bytes"},
    {"id": P2, "papel": "piloto", "posicao": 2, "cadeira": "desconhecida", "data": "2026-10-04",
     "pergunta": "golden record de obra"},
    {"id": P3, "papel": "piloto", "posicao": 3, "cadeira": "desconhecida", "data": "2026-10-04",
     "pergunta": "raiz da casa entidade classe ficha especie"},
    {"id": "esc-dddd4444", "papel": "reserva", "posicao": 4, "cadeira": "desconhecida", "data": "2026-10-04", "pergunta": "reserva"},
]
FRASE1 = "como o decodificador trata uma sequência UTF-8 cortada no meio de um caractere?"
FRASE2 = "o que é o golden record de uma obra no acervo?"
ROTULOS = ["Complexidade assintotica", "asymptotic complexity", "big-o", "Pipeline RAG", "rag",
           "retrieval-augmented generation", "Ranqueamento multiestágio", "reranking", "Juiz-modelo"]


# --- funções puras -------------------------------------------------------------------------------------------


def test_frases_aceita_string_ou_objeto_e_normaliza_o_espaco():
    f = pc.ler_frases(json.dumps({P1: "  uma   frase  ", P2: {"frase": "outra", "cadeira": "ia", "chapeu": "agente"}}), [P1, P2, P3])
    assert f[P1] == {"frase": "uma frase", "chapeu": None, "cadeira": None}
    assert f[P2] == {"frase": "outra", "chapeu": "agente", "cadeira": "ia"}


@pytest.mark.parametrize("texto,trecho", [
    ("{não é json", "não é JSON"),
    ("[]", "objeto JSON"),
    ("{}", "objeto JSON"),
    (json.dumps({"esc-zzzz9999": "x"}), "não são do piloto"),
    (json.dumps({P1: ""}), "falta a frase"),
    (json.dumps({P1: {"cadeira": "ia"}}), "falta a frase"),
    (json.dumps({P1: {"frase": "x", "chapeu": "agente"}}), "vem com a cadeira"),
    (json.dumps({P1: {"frase": "x", "chapeu": 7}}), "chapeu é texto"),
])
def test_frases_invalidas_dizem_o_que_esta_errado(texto, trecho):
    with pytest.raises(ValueError, match=trecho):
        pc.ler_frases(texto, [P1, P2])


def test_tres_consultas_com_chapeu():
    c = pc.consultas("chamada do log", FRASE1, ROTULOS)
    assert c["servido"] == "chamada do log" and c["frase"] == FRASE1
    assert c["montada"] == [FRASE1, FRASE1 + ". Buscar também: " + ", ".join(ROTULOS[:8])]


def test_sem_chapeu_a_montada_seria_a_frase_e_nao_entra():
    assert list(pc.consultas("chamada do log", FRASE1, ())) == ["servido", "frase"]


def test_a_montada_do_par_nao_leva_o_pedido():
    """As chamadas do piloto sao anteriores ao #3345: nao ha pedido gravado, entao a lista tem a frase e a frase com os rotulos."""
    montada = pc.consultas("x", FRASE1, ROTULOS)["montada"]
    assert len(montada) == 2 and montada[0] == FRASE1 and montada[1].startswith(FRASE1 + ". Buscar também: ")


def _sec(i):
    return {"chave": f"s{i}", "titulo": f"Obra › Seção {i}", "texto": f"t{i}", "secao_id": f"s{i}"}


def test_jaccard_de_c_e_d_contra_a():
    rec = {"servido": [_sec(i) for i in range(1, 5)], "frase": [_sec(i) for i in range(3, 7)], "montada": [_sec(i) for i in range(1, 5)]}
    assert pc.jaccard_dos_bracos(rec) == {"CxA": round(2 / 6, 3), "DxA": 1.0}
    assert pc.jaccard_dos_bracos({k: rec[k] for k in ("servido", "frase")}) == {"CxA": round(2 / 6, 3)}


def _lote_antigo():
    """Forma de `lote ler <id> --com-braco`: o corpo público (a ordem em que a tela mostrou) e as respostas com braço."""
    return {"lote_id": "piloto-x", "ativo": False,
            "corpo": {"perguntas": [{"pergunta_id": P1, "respostas": [{"resposta_id": "re-p1b"}, {"resposta_id": "re-p1a"}]},
                                    {"pergunta_id": P2, "respostas": [{"resposta_id": "re-p2a"}, {"resposta_id": "re-p2b"}]},
                                    {"pergunta_id": P3, "respostas": [{"resposta_id": "re-p3a"}, {"resposta_id": "re-p3b"}]}]},
            "respostas": [{"resposta_id": "re-p1a", "pergunta_id": P1, "braco": "servido"},
                          {"resposta_id": "re-p1b", "pergunta_id": P1, "braco": "lexico"},
                          {"resposta_id": "re-p2a", "pergunta_id": P2, "braco": "servido"},
                          {"resposta_id": "re-p2b", "pergunta_id": P2, "braco": "lexico"},
                          {"resposta_id": "re-p3a", "pergunta_id": P3, "braco": "servido"},
                          {"resposta_id": "re-p3b", "pergunta_id": P3, "braco": "lexico"}]}


def _marca(i, rid, q, emb=True):
    return {"id": i, "tipo": "marca", "resposta_id": rid, "qualidade": q, "embasamento": emb, "pergunta_id": None, "escolha": None, "motivo": None}


def _pref(i, pid, escolha):
    return {"id": i, "tipo": "preferencia", "pergunta_id": pid, "escolha": escolha, "resposta_id": None, "qualidade": None, "motivo": None}


EVENTOS = [
    _marca(3, "re-p1a", "boa"), _marca(4, "re-p1b", "parcial"), _pref(5, P1, "2"),          # 1ª passada: preferiu a 2ª da tela
    _marca(6, "re-p1a", "boa"), _marca(7, "re-p1b", "irrelevante"), _pref(8, P1, "1"),       # revisou: a 1ª da tela
    _marca(9, "re-p2a", "enganosa", emb=False), _marca(10, "re-p2b", "boa"), _pref(11, P2, "empate"),
    {"id": 12, "tipo": "exclusao", "pergunta_id": P3, "motivo": "nao-da-sem-a-ordem", "resposta_id": None, "escolha": None},
]


def test_o_que_o_dono_ja_julgou_vale_o_ultimo_evento_e_a_ordem_da_tela_resolve_a_escolha():
    j = pc.julgamentos_anteriores(_lote_antigo(), EVENTOS)
    assert j[P1]["marcas"] == {"servido": {"qualidade": "boa", "embasamento": True},
                               "lexico": {"qualidade": "irrelevante", "embasamento": True}}
    assert j[P1]["preferiu"] == "lexico", "escolha 1 = a primeira resposta da tela, que era a lexica (re-p1b)"
    assert j[P2]["preferiu"] == "empate" and j[P2]["marcas"]["servido"] == {"qualidade": "enganosa", "embasamento": False}
    assert j[P3] == {"excluida": "nao-da-sem-a-ordem"}


def test_resumo_do_julgamento_em_uma_linha():
    j = pc.julgamentos_anteriores(_lote_antigo(), EVENTOS)
    assert pc.resumo_do_julgamento(j[P1]) == "lexico=irrelevante, A=boa; preferiu lexico"
    assert pc.resumo_do_julgamento(j[P2]) == "lexico=boa, A=enganosa sem embasamento; preferiu empate"
    assert pc.resumo_do_julgamento(j[P3]) == "excluída por você (nao-da-sem-a-ordem)"
    assert pc.resumo_do_julgamento(None) == "sem julgamento anterior"


def test_sem_lote_ou_sem_evento_nao_quebra():
    assert pc.julgamentos_anteriores({}, []) == {}
    assert pc.julgamentos_anteriores(_lote_antigo(), [_pref(1, "esc-fora", "1")]) == {"esc-fora": {"preferiu": "1"}}


def _resultado(texto, i=1):
    return {"resposta": texto, "mapa": [{"afirmacao": "x", "secoes": [f"s{i}"]}], "rodape": [_sec(i)], "de_consulta": False,
            "palavras": len(texto.split()), "carimbo": {"tentativas": 1, "segundos": 1.0, "tokens_prompt": 10, "tokens_saida": 5, "avisos": []}}


CARIMBO = {k: {"v": 1} for k in ("acervo", "motor", "vocabulario", "gabarito", "escritor", "par")}


def _lote(**sobre):
    perguntas = [{"id": P1, "frase": FRASE1, "cadeira": "desconhecida", "data": "2026-10-03"},
                 {"id": P2, "frase": FRASE2, "cadeira": "desconhecida", "data": "2026-10-04"}]
    resultados = {P1: {"servido": _resultado("resposta A", 1), "frase": _resultado("resposta C", 2), "montada": _resultado("resposta D", 3)},
                  P2: {"servido": _resultado("outra A", 1), "frase": _resultado("outra C", 2)}}
    return pc.montar_lote_par("par-t", "versao-1", "v1", perguntas, resultados, CARIMBO, "42", False), perguntas, resultados


def test_o_lote_mostra_a_frase_do_dono_e_esconde_o_braco_na_parte_publica():
    env, _, _ = _lote()
    corpo = env["corpo"]
    assert [p["texto"] for p in corpo["perguntas"]] == [FRASE1, FRASE2]
    assert [len(p["respostas"]) for p in corpo["perguntas"]] == [3, 2]
    publico = json.dumps(corpo, ensure_ascii=False)
    assert not {"servido", "frase", "montada", "braco"} & {w.strip('",:{}[]') for w in publico.split()}
    assert {r["braco"] for r in env["respostas"]} == {"servido", "frase", "montada"}
    assert len({r["resposta_id"] for r in env["respostas"]}) == 5 and all(r["resposta_id"].startswith("re-") for r in env["respostas"])
    assert pc.conferir_aceite_par(env, 2) == []


def test_a_ordem_das_respostas_e_sorteada_por_pergunta_e_estavel_na_semente():
    a, _, _ = _lote()
    b, _, _ = _lote()
    ordem = lambda env, pid: [next(r["braco"] for r in env["respostas"] if r["resposta_id"] == x["resposta_id"])
                              for p in env["corpo"]["perguntas"] if p["pergunta_id"] == pid for x in p["respostas"]]
    assert ordem(a, P1) == ordem(b, P1) and sorted(ordem(a, P1)) == ["frase", "montada", "servido"]


def test_aceite_do_par_pega_resposta_igual_sem_rodape_marca_e_carimbo_faltando():
    env, perguntas, resultados = _lote()
    resultados[P1]["frase"] = _resultado("resposta A", 2)
    env2 = pc.montar_lote_par("par-t", "v", "v1", perguntas, resultados, {"acervo": {"v": 1}}, "42", False)
    problemas = " | ".join(pc.conferir_aceite_par(env2, 2))
    assert "duas respostas de texto idêntico" in problemas and "carimbo sem a versão «par»" in problemas
    resultados[P1]["montada"] = {**_resultado("com marca [3] no meio"), "rodape": []}
    problemas = " | ".join(pc.conferir_aceite_par(pc.montar_lote_par("par-t", "v", "v1", perguntas, resultados, CARIMBO, "42", False), 2))
    assert "sem seção no rodapé" in problemas and "marca [n]" in problemas
    assert "esperava 3" in " | ".join(pc.conferir_aceite_par(env, 3))


def test_a_tabela_tem_uma_linha_por_pergunta_e_diz_quando_d_e_c():
    j = pc.julgamentos_anteriores(_lote_antigo(), EVENTOS)
    l1 = pc.linha_da_tabela(1, P1, FRASE1, {"CxA": 0.25, "DxA": 0.5}, True, j[P1])
    l2 = pc.linha_da_tabela(2, P2, FRASE2, {"CxA": 0.0}, False, j[P2])
    assert "| 0.25 | 0.5 |" in l1 and "= C (sem chapéu)" in l2
    t = pc.tabela([l1, l2])
    assert t.splitlines()[0].startswith("| # | pergunta") and len(t.splitlines()) == 4


# --- o verbo, com rag, ollama e marcacao-api falsos -----------------------------------------------------------


def _secoes_da(consulta):
    """Oito seções que dependem do texto da consulta: consultas iguais dão o mesmo top-8, diferentes dão outro."""
    chave = json.dumps(consulta, ensure_ascii=False, sort_keys=True)
    base = int(hashlib.sha1(chave.encode()).hexdigest()[:6], 16) % 20
    return [base + i for i in range(8)]


class _Rag(BaseHTTPRequestHandler):
    buscas: list = []

    def log_message(self, *a):
        pass

    def _json(self, obj):
        dado = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.buscas.append(corpo)
        ns = _secoes_da(corpo["pergunta"])
        fontes = [{"n": k, "obra": f"Obra {n}", "arquivo": f"o{n}.pdf", "section_id": f"s{n}", "secao_id": f"uuid-{n}",
                   "breadcrumb": [f"Seção {n}"], "texto": None} for k, n in enumerate(ns, 1)]
        contexto = "\n\n".join(f"[{k}] (o{n}.pdf · s{n}) — Seção {n}\ncorpo da seção {n}" for k, n in enumerate(ns, 1))
        self._json({"fontes": fontes, "contexto": contexto, "cobertura": "boa", "tempos_ms": {"total": 5.0}})

    def do_GET(self):
        self._json({"indice": {"acervo_sha": "abc123456789", "vocabulario_versao": "voc-1"}})


class _Ollama(BaseHTTPRequestHandler):
    pedidos: list = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        usuario = corpo["messages"][1]["content"]
        self.pedidos.append(usuario)
        resposta = f"Resposta {hashlib.sha1(usuario.encode()).hexdigest()[:8]} sobre as seções."
        dado = json.dumps({"message": {"content": json.dumps({"resposta": resposta, "mapa": [{"afirmacao": "x", "secoes": [1]}]})},
                           "prompt_eval_count": 100, "eval_count": 20}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)


class _Marcacao(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/interno/lote/piloto-x":
            obj = _lote_antigo()
        elif u.path == "/interno/eventos":
            obj = {"lote_id": parse_qs(u.query)["lote_id"][0], "eventos": EVENTOS}
        else:
            obj = {}
        dado = json.dumps(obj).encode()
        self.send_response(200 if obj else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)


def _sobe(handler):
    s = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


@pytest.fixture
def verbo(tmp_path):
    rag, olm, mk = _sobe(_Rag), _sobe(_Ollama), _sobe(_Marcacao)
    _Rag.buscas, _Ollama.pedidos = [], []
    instancia = tmp_path / "inst"
    for nome in ("rag/RAG_API_TOKEN", "marcacao-api/MARCACAO_TOKEN"):
        (instancia / "segredos" / nome.split("/")[0]).mkdir(parents=True, exist_ok=True)
        (instancia / "segredos" / nome).write_text("tok\n")
    abertura = tmp_path / "abertura" / "current" / "abertura"
    abertura.mkdir(parents=True)
    (abertura / "rotas-chapeu.json").write_text(json.dumps({"ia": {"engenharia-de-harness": ROTULOS}}, ensure_ascii=False), encoding="utf-8")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({
        "rag": {"estado": "ativa", "container": None, "stack": "rag", "endpoint": f"http://127.0.0.1:{rag.server_port}/search",
                "facets": f"http://127.0.0.1:{rag.server_port}/facets", "token_em": "rag/RAG_API_TOKEN",
                "medicoes_em": "var/medicoes/rag", "ajustes": [], "nao_e_ajuste": {}},
        "marcacao": {"estado": "ativa", "tipo": "marcacao-api", "endpoint": f"http://127.0.0.1:{mk.server_port}",
                     "token_em": "marcacao-api/MARCACAO_TOKEN"}}))
    lista = tmp_path / "escada.jsonl"
    lista.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in LISTA) + "\n", encoding="utf-8")
    frases = tmp_path / "frases.json"
    frases.write_text(json.dumps({P1: {"frase": FRASE1, "cadeira": "ia", "chapeu": "engenharia-de-harness"}, P2: FRASE2}, ensure_ascii=False),
                      encoding="utf-8")

    def roda(*args, estado_novo=False):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia), "OPS_LOG_DIR": str(tmp_path / "ops"),
               "PF_ABERTURA_DIR": str(tmp_path / "abertura"), "OLLAMA_BASE_URL": f"http://127.0.0.1:{olm.server_port}", "PF_CADEIRA": "ia"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", "parear", "biblioteca", "--lista", str(lista), *args],
                              capture_output=True, text=True, env=env, timeout=90, check=False, stdin=subprocess.DEVNULL)

    yield roda, tmp_path, frases, instancia
    for s in (rag, olm, mk):
        s.shutdown()


def test_plano_recupera_os_tres_bracos_na_mesma_hora_e_nao_escreve_nada(verbo):
    roda, tmp, frases, instancia = verbo
    r = roda("--frases", str(frases), "--plano", "--antes", "piloto-x", "--lote-id", "t1")
    assert r.returncode == 0, r.stderr
    assert "par t1 · 2 perguntas · D = C (sem chapeu, nao entra) em 1" in r.stdout
    assert len(_Rag.buscas) == 5, "pergunta 1: A, C e D; pergunta 2: A e C"
    for b in _Rag.buscas:
        assert b["origem"] == "bench" and b["particao"] == "biblioteca" and b["k"] == 8 and b["texto"] == "secao"
    consultas = [b["pergunta"] for b in _Rag.buscas]
    assert LISTA[0]["pergunta"] in consultas and FRASE1 in consultas and FRASE2 in consultas and LISTA[1]["pergunta"] in consultas
    montada = next(c for c in consultas if isinstance(c, list))
    assert montada == [FRASE1, FRASE1 + ". Buscar também: " + ", ".join(ROTULOS[:8])]
    assert sum(isinstance(c, list) for c in consultas) == 1, "a pergunta 2 não tem chapéu: D seria C, não vai"
    assert _Ollama.pedidos == []
    linhas = [l for l in r.stdout.splitlines() if l.startswith("| 1 ") or l.startswith("| 2 ")]
    assert len(linhas) == 2 and "= C (sem chapéu)" in linhas[1]
    assert "lexico=irrelevante, A=boa; preferiu lexico" in linhas[0]
    md = list((instancia / "var" / "medicoes" / "rag").glob("*-par-consulta.md"))
    js = list((instancia / "var" / "medicoes" / "rag").glob("*-par-consulta.json"))
    assert len(md) == 1 and len(js) == 1
    assert "**A — a chamada de hoje**" in md[0].read_text() and "**D — a lista montada**" in md[0].read_text()
    assert json.loads(js[0].read_text())["antes"] == "piloto-x"


def test_o_que_o_dono_julgou_antes_aparece_ao_lado_de_cada_pergunta(verbo):
    roda, _, frases, _ = verbo
    r = roda("--frases", str(frases), "--plano", "--antes", "piloto-x", "--lote-id", "t2")
    assert r.returncode == 0, r.stderr
    assert "A=boa" in r.stdout and "preferiu" in r.stdout
    sem = roda("--frases", str(frases), "--plano", "--lote-id", "t3")
    assert "sem julgamento anterior" in sem.stdout


def test_a_frase_que_o_lint_recusaria_vira_aviso_e_nao_trava(verbo):
    roda, tmp, _, _ = verbo
    f = tmp / "ruim.json"
    f.write_text(json.dumps({P1: "qual piso; qual corte; qual rerank"}), encoding="utf-8")
    r = roda("--frases", str(f), "--plano", "--lote-id", "t4")
    assert r.returncode == 0, r.stderr
    assert "AVISO 1. a sua frase seria recusada pelo lint" in r.stdout


def test_escreve_uma_resposta_por_braco_com_a_frase_como_pergunta_e_monta_o_lote(verbo):
    roda, tmp, frases, _ = verbo
    saida = tmp / "env.json"
    r = roda("--frases", str(frases), "--saida", str(saida), "--versao", "versao-1", "--criterio-versao", "v1", "--lote-id", "t5")
    assert r.returncode == 0, r.stderr
    assert "envelope em" in r.stdout and "gravar: motor marcacao lote gravar" in r.stdout
    env = json.loads(saida.read_text())
    assert [p["texto"] for p in env["corpo"]["perguntas"]] == [FRASE1, FRASE2]
    assert [len(p["respostas"]) for p in env["corpo"]["perguntas"]] == [3, 2] and len(env["respostas"]) == 5
    assert {r["braco"] for r in env["respostas"]} == {"servido", "frase", "montada"}
    assert len(_Ollama.pedidos) == 5
    assert all(p.startswith("Pergunta: " + FRASE1) or p.startswith("Pergunta: " + FRASE2) for p in _Ollama.pedidos), \
        "o escritor vê a frase do dono nos três braços, nunca a chamada de hoje"
    assert not any("UTF-8 decoding" in p for p in _Ollama.pedidos)
    assert env["carimbo"]["par"]["frases_sha256"] and env["carimbo"]["escritor"]["pergunta_do_escritor"]
    assert env["carimbo"]["acervo"]["acervo_sha"] == "abc123456789"
    assert env["gabarito_versao_id"] == "versao-1" and env["ativo"] is False


def test_sem_tempo_fica_incompleto_e_a_mesma_chamada_retoma(verbo):
    roda, tmp, frases, _ = verbo
    saida = tmp / "env.json"
    args = ("--frases", str(frases), "--saida", str(saida), "--versao", "v", "--criterio-versao", "v1", "--lote-id", "t6")
    r = roda(*args, "--tempo", "-1")
    assert r.returncode == 1 and "INCOMPLETO: 0/5" in r.stdout and not saida.exists()
    r2 = roda(*args)
    assert r2.returncode == 0, r2.stderr
    assert json.loads(saida.read_text())["lote_id"] == "t6"


@pytest.mark.parametrize("args,trecho", [
    (("--plano",), "pede --frases"),
    (("--frases", "NAO", "--plano"), "No such file"),
    (("--frases", "FRASES"), "pede --frases"),
])
def test_uso_errado_sai_2(verbo, args, trecho):
    roda, tmp, frases, _ = verbo
    args = tuple(str(frases) if a == "FRASES" else a for a in args)
    r = roda(*args)
    assert r.returncode == 2 and trecho in r.stderr


def test_frase_de_pergunta_fora_do_piloto_sai_2(verbo):
    roda, tmp, _, _ = verbo
    f = tmp / "fora.json"
    f.write_text(json.dumps({"esc-dddd4444": "a reserva não é do piloto"}), encoding="utf-8")
    r = roda("--frases", str(f), "--plano")
    assert r.returncode == 2 and "não são do piloto" in r.stderr and _Rag.buscas == []


def test_sem_do_log_o_par_e_o_de_hoje_e_nao_manda_chapeu_nem_eleicao(verbo):
    roda, _, frases, _ = verbo
    r = roda("--frases", str(frases), "--plano", "--lote-id", "t7")
    assert r.returncode == 0, r.stderr
    assert "par t7 · 2 perguntas · D = C (sem chapeu, nao entra) em 1" in r.stdout and len(_Rag.buscas) == 5
    assert all("chapeu" not in b and "eleicao_chapeu" not in b for b in _Rag.buscas)


# --- `--do-log` (card #3378): a população são as chamadas do log com eleito -------------------------------------------


def test_consultas_do_log_so_o_eleito_leva_chapeu_e_eleicao():
    c = pc.consultas_do_log("a necessidade", "ia", "engenharia-de-harness", ROTULOS)
    assert list(c) == list(pc.BRACOS_DO_LOG) == ["frase", "eleito"]
    assert c["frase"] == {"pergunta": "a necessidade", "corpo": {}}
    assert c["eleito"]["pergunta"] == "a necessidade"
    assert c["eleito"]["corpo"] == {"chapeu": {"cadeira": "ia", "chapeu": "engenharia-de-harness", "rotulos": ROTULOS},
                                    "eleicao_chapeu": True}


def test_jaccard_do_eleito_contra_a_busca_de_hoje():
    rec = {"frase": [_sec(i) for i in range(1, 5)], "eleito": [_sec(i) for i in range(3, 7)]}
    assert pc.jaccard_eleito(rec) == {"ExC": round(2 / 6, 3)}
    assert pc.jaccard_eleito({"frase": rec["frase"]}) == {}


def test_a_tabela_do_log_tem_uma_linha_por_chamada():
    l1 = pc.linha_da_tabela_log(1, "ev-1", "qual a necessidade", "ia", "engenharia-de-harness", {"ExC": 0.25})
    t = pc.tabela_log([l1])
    assert "Jaccard E×C" in t.splitlines()[0] and "| 0.25 |" in l1 and len(t.splitlines()) == 3


S_IA, S_DADOS = "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"
EV1, EV2 = "10000000-0000-4000-8000-000000000001", "10000000-0000-4000-8000-000000000002"
NEC_ELEITA = "como usar a capacidade absortiva do órgão?"
# quatro chamadas do log: duas com eleito (a segunda repete a necessidade, com outra caixa e espaço a mais) e duas sem
EVENTOS_LOG = [
    {"id": EV1, "sessao_id": S_IA, "criado_em": "2026-10-08 12:00:00+00", "necessidade": NEC_ELEITA, "chapeu": "engenharia-de-harness"},
    {"id": EV2, "sessao_id": S_IA, "criado_em": "2026-10-09 09:00:00+00",
     "necessidade": "Como  usar a capacidade absortiva do órgão?", "chapeu": "engenharia-de-harness"},
    {"id": "10000000-0000-4000-8000-000000000003", "sessao_id": S_IA, "criado_em": "2026-10-09 10:00:00+00",
     "necessidade": "qual o protocolo de medição do rag?", "chapeu": "engenharia-de-harness"},
    {"id": "10000000-0000-4000-8000-000000000004", "sessao_id": S_DADOS, "criado_em": "2026-10-09 11:00:00+00",
     "necessidade": "qual o catálogo de metadados da governança?", "chapeu": "governanca"},
]

DOCKER_FALSO = """#!{python}
import json, os, sys
a = sys.argv[1:]
container = a[2]
estado = json.load(open(os.environ["FAKE_ESTADO"]))
if container == "rag-extractor-pg":
    print(json.dumps(estado["eventos"]))
elif container == "harness-sessao-db":
    print(json.dumps(estado["cadeiras"]))
else:
    print("[]")
"""


class _RagLog(_Rag):
    """/search e /eleger. A busca com `eleicao_chapeu` devolve outro top-8 que a sem, para o Jaccard não ser 1."""
    buscas: list = []
    eleger: list = []

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/eleger":
            self.eleger.append(corpo)
            self._json({"itens": [{"eleito_do_chapeu": "capacidade-absortiva" if "capacidade absortiva" in i["necessidade"].lower() else None,
                                   "sinais": []} for i in corpo["itens"]]})
            return
        self.buscas.append(corpo)
        ns = _secoes_da({"p": corpo["pergunta"], "eleicao": bool(corpo.get("eleicao_chapeu"))})
        fontes = [{"n": k, "obra": f"Obra {n}", "arquivo": f"o{n}.pdf", "section_id": f"s{n}", "secao_id": f"uuid-{n}",
                   "breadcrumb": [f"Seção {n}"], "texto": None} for k, n in enumerate(ns, 1)]
        contexto = "\n\n".join(f"[{k}] (o{n}.pdf · s{n}) — Seção {n}\ncorpo da seção {n}" for k, n in enumerate(ns, 1))
        self._json({"fontes": fontes, "contexto": contexto, "cobertura": "boa", "tempos_ms": {"total": 5.0}})


@pytest.fixture
def verbo_log(tmp_path):
    rag, olm = _sobe(_RagLog), _sobe(_Ollama)
    _RagLog.buscas, _RagLog.eleger, _Ollama.pedidos = [], [], []
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)
    estado = tmp_path / "estado.json"
    estado.write_text(json.dumps({"eventos": EVENTOS_LOG, "cadeiras": [{"sessao_id": S_IA, "cadeira": "ia"},
                                                                    {"sessao_id": S_DADOS, "cadeira": "dados"}]}))
    abertura = tmp_path / "abertura" / "current" / "abertura"
    abertura.mkdir(parents=True)
    (abertura / "rotas-chapeu.json").write_text(json.dumps({"ia": {"engenharia-de-harness": ROTULOS},
                                                           "dados": {"governanca": ["Governança de dados"]}}, ensure_ascii=False),
                                                encoding="utf-8")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": f"http://127.0.0.1:{rag.server_port}/search",
        "facets": f"http://127.0.0.1:{rag.server_port}/facets", "token_em": "rag/RAG_API_TOKEN", "medicoes_em": "var/medicoes/rag",
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
               "PF_ABERTURA_DIR": str(tmp_path / "abertura"), "OLLAMA_BASE_URL": f"http://127.0.0.1:{olm.server_port}", "PF_CADEIRA": "ia",
               "FAKE_ESTADO": str(estado), "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", "parear", "biblioteca", *args],
                              capture_output=True, text=True, env=env, timeout=90, check=False, stdin=subprocess.DEVNULL)

    yield roda, tmp_path, instancia
    for s in (rag, olm):
        s.shutdown()


def test_do_log_a_populacao_e_so_a_chamada_com_eleito_e_deduplica_por_necessidade(verbo_log):
    roda, _, instancia = verbo_log
    r = roda("--do-log", "--plano", "--lote-id", "l1")
    assert r.returncode == 0, r.stderr
    assert "chamadas do log com eleito 2 de 4" in r.stdout and "1 necessidades distintas" in r.stdout
    assert len(_RagLog.eleger) == 1 and len(_RagLog.eleger[0]["itens"]) == 4
    assert len(_RagLog.buscas) == 2, "uma necessidade com eleito (a repetida sai): a busca de hoje e a do eleito"
    assert _Ollama.pedidos == []
    assert "Jaccard E×C" in r.stdout and f"| 1 | ev-{EV1} |" in r.stdout
    medicoes = instancia / "var" / "medicoes" / "rag"
    md, js = list(medicoes.glob("*-par-eleito.md")), list(medicoes.glob("*-par-eleito.json"))
    assert len(md) == 1 and len(js) == 1 and "**E — a busca com o eleito do chapéu**" in md[0].read_text()
    assert json.loads(js[0].read_text())["chamadas"] == {"lidas": 4, "com_eleito": 2, "distintas": 1}


def test_do_log_o_braco_eleito_manda_chapeu_e_eleicao_e_o_da_frase_nao_manda_nenhum(verbo_log):
    roda, _, _ = verbo_log
    assert roda("--do-log", "--plano", "--lote-id", "l2").returncode == 0
    por_eleicao = {bool(b.get("eleicao_chapeu")): b for b in _RagLog.buscas}
    assert set(por_eleicao) == {True, False}
    frase, eleito = por_eleicao[False], por_eleicao[True]
    assert "chapeu" not in frase and "eleicao_chapeu" not in frase
    assert eleito["eleicao_chapeu"] is True
    assert eleito["chapeu"]["cadeira"] == "ia" and eleito["chapeu"]["chapeu"] == "engenharia-de-harness"
    assert eleito["chapeu"]["rotulos"] and set(eleito["chapeu"]["rotulos"]) <= set(ROTULOS)
    assert frase["pergunta"] == eleito["pergunta"] == NEC_ELEITA
    for b in (frase, eleito):
        assert b["origem"] == "bench" and b["particao"] == "biblioteca" and b["k"] == 8 and b["texto"] == "secao"


def test_do_log_desde_corta_as_chamadas_anteriores(verbo_log):
    roda, _, _ = verbo_log
    r = roda("--do-log", "--plano", "--desde", "2026-10-09", "--lote-id", "l3")
    assert r.returncode == 0, r.stderr
    assert "parear --do-log desde 2026-10-09: chamadas do log com eleito 1 de 3" in r.stdout
    assert f"ev-{EV2}" in r.stdout and f"ev-{EV1}" not in r.stdout


def test_do_log_sem_chamada_com_eleito_sai_0_dizendo_que_nao_ha_par_e_sem_lote(verbo_log):
    roda, tmp, instancia = verbo_log
    saida = tmp / "env.json"
    r = roda("--do-log", "--saida", str(saida), "--versao", "v", "--criterio-versao", "v1", eventos=EVENTOS_LOG[2:])
    assert r.returncode == 0, r.stderr
    assert "chamadas do log com eleito 0 de 2" in r.stdout and "nao ha par a medir" in r.stdout
    assert not saida.exists() and _RagLog.buscas == [] and _Ollama.pedidos == []
    assert list((instancia / "var" / "medicoes" / "rag").glob("*par-*")) == []


def test_do_log_escreve_uma_resposta_por_braco_e_monta_o_lote(verbo_log):
    roda, tmp, _ = verbo_log
    saida = tmp / "env.json"
    r = roda("--do-log", "--saida", str(saida), "--versao", "versao-1", "--criterio-versao", "v1", "--lote-id", "l5")
    assert r.returncode == 0, r.stderr
    assert "gravar: motor marcacao lote gravar" in r.stdout
    env = json.loads(saida.read_text())
    assert [p["texto"] for p in env["corpo"]["perguntas"]] == [NEC_ELEITA]
    assert len(env["respostas"]) == 2 and {x["braco"] for x in env["respostas"]} == {"frase", "eleito"}
    assert len(_Ollama.pedidos) == 2 and all(p.startswith("Pergunta: " + NEC_ELEITA) for p in _Ollama.pedidos)
    assert env["carimbo"]["gabarito"]["perguntas"] == [f"ev-{EV1}"]
    assert env["carimbo"]["par"]["chamadas"] == {"lidas": 4, "com_eleito": 2, "distintas": 1}
    assert env["gabarito_versao_id"] == "versao-1" and env["ativo"] is False


@pytest.mark.parametrize("args,trecho", [
    (("--do-log",), "--do-log pede --plano"),
    (("--do-log", "--frases", "x.json", "--plano"), "nao combina com --frases"),
    (("--desde", "2026-10-09", "--plano"), "--desde so vale com --do-log"),
])
def test_do_log_uso_errado_sai_2(verbo_log, args, trecho):
    roda, _, _ = verbo_log
    r = roda(*args)
    assert r.returncode == 2 and trecho in r.stderr and _RagLog.buscas == []
