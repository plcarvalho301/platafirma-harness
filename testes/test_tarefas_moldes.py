# componente: componente:verbo-tarefas
"""Verbo tarefas: moldes, conversão do corpo e fecho no próprio comentário.

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que
o VERBO faz — o que imprime, o corpo que envia, as recusas — sem tocar no board de verdade.

O MOLDE NÃO MORA AQUI (card #4058). O texto de cada variante e a lista de rótulos são de
`platafirma-rastreador@api/molde.py`, servidos em `GET /modelo`, e o conteúdo é provado lá
(`api/tests/test_molde_unico.py`). Aqui se prova só que o verbo imprime o que a API serve,
sem cópia própria, e que a conversão usa a lista que vem dela.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"

# A lista de rótulos que o stub serve em `GET /modelo`: oráculo do teste da conversão, não
# molde. Basta conter os rótulos que os testes abaixo exercitam.
ROTULOS_DO_STUB = [
    "Problema", "Solução", "Peças", "Fora", "Resultado", "Medida", "Apetite", "Aberto",
    "Produtos documentais", "Regras", "Sai quando", "Premissas", "Regras novas", "Unidades",
    "Traz", "Decidiu", "Ficha", "Golden", "Motivo", "Por que importa", "O que já se sabe",
    "Resposta esperada", "Consequência no corpo",
]
VARIANTES_DO_STUB = ["epico", "feature", "story", "story-derivada", "story-refinada", "task",
                     "comentario-insumo", "comentario-pergunta", "comentario-buraco",
                     "comentario-requisito", "comentario-decisao"]


class _Stub(BaseHTTPRequestHandler):
    comentarios: list = []
    fechos: list = []
    edicoes: list = []
    espera: dict = {}

    VOCAB = {
        "pergunta": ["respondida", "retirada"],
        "buraco": ["remendado", "cortado"],
        "requisito": ["aceito", "fundido", "retirado"],
    }

    def log_message(self, *a):  # silencioso
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/espera-dono":
            return self._json(self.espera)
        if self.path == "/modelo":
            return self._json({"variantes": VARIANTES_DO_STUB,
                               "rotulos_da_conversao": ROTULOS_DO_STUB})
        m = re.match(r"^/modelo/([a-z\-]+)$", self.path)
        if m:
            v = m.group(1)
            if v not in VARIANTES_DO_STUB:
                return self._json({"erro": f"molde desconhecido: `{v}`"}, 404)
            return self._json({"variante": v, "texto": f"TEXTO {v}\n",
                               "aviso": "AVISO" if v == "feature" else None})
        m = re.match(r"^/itens/(\d+)/comentarios$", self.path)
        if m:
            return self._json({"item": int(m.group(1)), "comentarios": self.comentarios})
        # O portão do funil confere o card antes de ler os comentários dele: o stub o serve aberto.
        m = re.match(r"^/itens/(\d+)$", self.path)
        if m:
            return self._json({"id": int(m.group(1)), "chave": m.group(1), "titulo": "card aberto",
                               "estado": "em-execucao", "estado_fase": "delivery",
                               "estado_derivado": None})
        self._json({"erro": "nao existe"}, 404)

    def do_PATCH(self):
        m = re.match(r"^/itens/(\d+)/comentarios/(\d+)$", self.path)
        if not m:
            return self._json({"erro": "rota"}, 404)
        item_id, cid = int(m.group(1)), int(m.group(2))
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        alvo = next((c for c in self.comentarios if c["id"] == cid), None)
        if alvo is None:
            return self._json({"erro": f"comentário {cid} não existe no item {item_id}"}, 404)
        if alvo.get("tipo") == "buraco" and "<p>buraco:" not in (corpo.get("corpo") or "").lower():
            return self._json({"erro": f"PATCH não pode trocar o tipo gravado (`buraco`) do comentário #{cid} (R13)"}, 400)
        alvo["corpo"] = corpo.get("corpo", "")
        type(self).edicoes.append((item_id, cid, dict(corpo), self.headers.get("x-auth-request-preferred-username")))
        return self._json({"id": cid, "item": item_id, "corpo": alvo["corpo"]})

    def do_POST(self):
        if self.path == "/para-html":
            n = int(self.headers.get("Content-Length", 0))
            corpo = json.loads(self.rfile.read(n) or b"{}")
            texto = corpo.get("texto", "")
            return self._json({"html": f"<p>{texto}</p>"})
        m = re.match(r"^/itens/(\d+)/comentarios/(\d+)/fecho$", self.path)
        if not m:
            return self._json({"erro": "rota"}, 404)
        item_id, cid = int(m.group(1)), int(m.group(2))
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        alvo = next((c for c in self.comentarios if c["id"] == cid), None)
        if alvo is None:
            return self._json({"erro": f"comentário {cid} não existe no item {item_id}"}, 404)
        vocab = self.VOCAB.get(alvo.get("tipo"))
        if not vocab:
            return self._json(
                {"erro": f"comentário #{cid} não tem tipo e não tem vocabulário de fecho (R6)",
                 "aceitos": []}, 400)
        if alvo.get("fecho_resultado") is not None:
            return self._json(
                {"erro": f"comentário #{cid} já está fechado — sem mudança (R7)",
                 "fecho_atual": {"resultado": alvo["fecho_resultado"], "destino": alvo.get("fecho_destino"),
                                 "por": alvo.get("fecho_por"), "em": alvo.get("fecho_em")}}, 409)
        resultado = (corpo.get("resultado") or "").strip().lower()
        if resultado not in vocab:
            return self._json(
                {"erro": f"`{corpo.get('resultado')}` não é um resultado de `{alvo['tipo']}` (R6)",
                 "aceitos": [{"codigo": v, "nome": v} for v in vocab]}, 400)
        alvo["fecho_resultado"] = resultado
        alvo["fecho_destino"] = corpo.get("destino")
        type(self).fechos.append((cid, dict(corpo)))
        return self._json({"id": cid, "item": item_id,
                            "fecho_resultado": resultado, "fecho_destino": corpo.get("destino")})


@pytest.fixture()
def stub():
    _Stub.comentarios, _Stub.fechos, _Stub.edicoes, _Stub.espera = [], [], [], {}
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base="http://127.0.0.1:9", stdin=None):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env,
                          input=stdin)


@pytest.mark.parametrize("args,variante", [
    (["modelo", "feature"], "feature"),
    (["modelo", "épico"], "epico"),
    (["modelo", "epico"], "epico"),
    (["modelo", "story"], "story"),
    (["modelo", "story", "refinada"], "story-refinada"),
    (["modelo", "story", "derivada"], "story-derivada"),
    (["modelo", "task"], "task"),
    (["modelo", "comentario", "insumo"], "comentario-insumo"),
    (["modelo", "comentario", "buraco"], "comentario-buraco"),
    (["modelo", "comentario", "decisão"], "comentario-decisao"),
])
def test_modelo_imprime_o_que_a_api_serve(stub, args, variante):
    s, base = stub
    p = _run(args, base)
    assert p.returncode == 0, p.stderr
    assert p.stdout == f"TEXTO {variante}\n"
    assert ("AVISO" in p.stderr) == (variante == "feature")


def test_modelo_sem_api_falha_e_nao_inventa():
    p = _run(["modelo", "feature"])
    assert p.returncode != 0 and p.stdout == ""


def test_modelo_comentario_sem_tipo_e_uso():
    assert _run(["modelo", "comentario"]).returncode == 2


def test_modelo_nivel_desconhecido_e_uso():
    assert _run(["modelo", "nada"]).returncode == 2


def test_o_verbo_nao_guarda_copia_do_molde():
    texto = BIN.read_text(encoding="utf-8")
    assert "Sai quando: na lapidação" not in texto
    assert "Medido em: <repo>" not in texto
    assert "Traz: <o que muda" not in texto
    assert 'R = ["' not in texto


def test_fecha_chama_a_rota_propria_com_resultado_e_destino(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "tipo": "buraco", "fecho_resultado": None}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado — momento «No parecer»"], base)
    assert p.returncode == 0, p.stderr
    (cid, corpo), = s.fechos
    assert cid == 7
    assert corpo == {"resultado": "remendado", "destino": "momento «No parecer»"}
    assert "remendado — momento «No parecer»" in p.stdout


def test_fecha_aceita_o_prefixo_fecho(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "tipo": "pergunta", "fecho_resultado": None}]
    p = _run(["comentar", "3408", "--fecha", "#7", "fecho: respondida — Solução"], base)
    assert p.returncode == 0, p.stderr
    assert s.fechos == [(7, {"resultado": "respondida", "destino": "Solução"})]


def test_fecha_recusa_sem_tipo(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "tipo": None, "fecho_resultado": None}]
    p = _run(["comentar", "3408", "--fecha", "7", "aceito — R3"], base)
    assert p.returncode == 4 and "vocabulário" in p.stderr and not s.fechos


def test_fecha_recusa_resultado_fora_do_vocabulario(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "tipo": "requisito", "fecho_resultado": None}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado — R3"], base)
    assert p.returncode == 4 and "aceito" in p.stderr and not s.fechos


def test_fecha_exige_destino(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "tipo": "buraco", "fecho_resultado": None}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado"], base)
    assert p.returncode == 2 and not s.fechos


def test_fecha_ja_fechado_nao_muda(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "tipo": "buraco", "fecho_resultado": "cortado", "fecho_destino": "Fora"}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado — x"], base)
    assert p.returncode == 1 and "sem mudança" in p.stderr and "cortado" in p.stderr and not s.fechos


def test_fecha_comentario_que_nao_existe(stub):
    s, base = stub
    p = _run(["comentar", "3408", "--fecha", "9", "remendado — x"], base)
    assert p.returncode == 1 and not s.fechos


def test_espera_dono_imprime_as_duas_partes_na_ordem(stub):
    s, base = stub
    s.espera = {
        "do_dono": {
            "perguntas": [{"id": 1, "item": 10, "titulo": "card do dono", "cadeira": "dados",
                           "primeira_linha": "pergunta (dono): x?", "carimbo": "2026-10-15T00:00:00Z"}],
            "prontos_para_aposta": [{"id": 11, "titulo": "pronta", "cadeira": "produto"}],
            "em_homologacao": [{"id": 12, "titulo": "em homolog", "cadeira": "engenharia"}],
            "total": 3,
        },
        "com_cadeiras": {
            "cards": [{"id": 20, "titulo": "card das cadeiras", "cadeira": "dados",
                       "abertos": [{"id": 2, "tipo": "buraco", "primeira_linha": "buraco: y",
                                    "carimbo": "2026-10-01T00:00:00Z", "orfao": True}]}],
            "abertos": 1,
            "orfaos": 1,
        },
        "gerado_em": "2026-10-15T19:00:00Z",
    }
    p = _run(["espera-dono"], base)
    assert p.returncode == 0, p.stderr
    linhas = p.stdout.splitlines()
    assert linhas[0] == "do dono (3):"
    assert any("pergunta #1" in l and "card do dono" in l for l in linhas)
    assert any("pronto para a aposta" in l and "#11" in l for l in linhas)
    assert any("em homologação" in l and "#12" in l for l in linhas)
    i_dono = linhas.index("do dono (3):")
    i_cadeiras = next(i for i, l in enumerate(linhas) if l.startswith("com as cadeiras"))
    assert i_dono < i_cadeiras, "do dono vem antes de com as cadeiras"
    assert linhas[i_cadeiras] == "com as cadeiras (1 abertos, 1 órfãos):"
    assert any("#20" in l and "card das cadeiras" in l for l in linhas)
    assert any("órfão" in l and "buraco: y" in l for l in linhas)


def test_espera_dono_json_devolve_o_corpo_da_api_como_veio(stub):
    """Card #3899: a borda serve o corpo da API a casca; o verbo não reformata nem calcula."""
    s, base = stub
    s.espera = {"do_dono": {"total": 0, "perguntas": [], "prontos_para_aposta": [], "em_homologacao": []},
                "com_cadeiras": {"abertos": 0, "orfaos": 0, "cards": []}, "gerado_em": "2026-10-20T00:00:00Z"}
    p = _run(["espera-dono", "--json"], base)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout) == s.espera
    assert _run(["espera-dono", "--nada"], base).returncode == 2


def test_espera_dono_e_mecanismo_da_casca_e_nao_face():
    texto = BIN.read_text(encoding="utf-8")
    assert "# mecanismo: espera-dono=casca" in texto
    for chave in ("face", "rotulo", "volta"):
        assert f"# {chave}: espera-dono=" not in texto, chave


def test_para_html_chama_api_sem_copia_local():
    """DT 292: `para_html` envia o texto para `POST /para-html` e não mantém cópia do algoritmo."""
    script = (
        f'envia() {{ local corpo; corpo=$(cat); printf \'{{"html":"<p>%s</p>"}}\' '
        f'"$(printf \'%s\' "$corpo" | jq -r .texto)"; }}; '
        f'source <(sed -n "/^para_html()/,/^}}/p" {BIN}); para_html'
    )
    p = subprocess.run(["bash", "-c", script], input="Problema: x", capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert p.stdout.rstrip("\n") == "<p>Problema: x</p>"


def test_para_html_falha_da_api_recusa():
    """Se `POST /para-html` falhar ou devolver payload inválido, `para_html` falha com exit != 0."""
    script = f'envia() {{ return 1; }}; source <(sed -n "/^para_html()/,/^}}/p" {BIN}); para_html'
    p = subprocess.run(["bash", "-c", script], input="Problema: x", capture_output=True, text=True)
    assert p.returncode != 0 and "POST /para-html" in p.stderr


def test_exec_curl_401_sem_corpo_expoe_http_status_e_rota(tmp_path):
    """DT 641: erro HTTP sem corpo JSON (ex: 401 no POST /para-html) relata rota e código HTTP."""
    curl_falso = tmp_path / "curl"
    curl_falso.write_text("#!/usr/bin/env bash\nprintf '\\n401'\nexit 22\n", encoding="utf-8")
    curl_falso.chmod(0o755)
    script = (
        f'PATH="{tmp_path}:$PATH"; BASE="http://127.0.0.1:8120/api"; QUEM=""; '
        f'eval "$(sed -n "/^_recusa()/,/^para_html()/p" {BIN} | sed "\\$d")"; '
        f'envia POST /para-html <<< \'{{"texto":"x"}}\''
    )
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert p.returncode != 0
    assert "HTTP 401" in p.stderr
    assert "POST /para-html" in p.stderr


def test_exec_curl_detail_json_expoe_detalhe(tmp_path):
    """DT 641: resposta JSON com `.detail` (FastAPI) é extraída em `_recusa`."""
    curl_falso = tmp_path / "curl"
    curl_falso.write_text(
        '#!/usr/bin/env bash\nprintf \'{"detail":"sujeito ausente"}\\n401\'\nexit 22\n',
        encoding="utf-8",
    )
    curl_falso.chmod(0o755)
    script = (
        f'PATH="{tmp_path}:$PATH"; BASE="http://127.0.0.1:8120/api"; QUEM=""; '
        f'eval "$(sed -n "/^_recusa()/,/^para_html()/p" {BIN} | sed "\\$d")"; '
        f'envia POST /para-html <<< \'{{"texto":"x"}}\''
    )
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert p.returncode != 0
    assert "sujeito ausente" in p.stderr


def test_comentar_edita_converte_para_html_e_envia_patch(stub):
    """DT 743: `tarefas comentar <id> --edita <n> <txt>` converte via /para-html e envia PATCH."""
    s, base = stub
    s.comentarios.append({"id": 5161, "tipo": "insumo", "corpo": "<p>insumo: antigo</p>"})
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    p = subprocess.run(
        [str(BIN), "comentar", "4314", "--edita", "5161", "insumo: novo corpo"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert p.returncode == 0, p.stderr
    assert "comentário #5161 do item 4314 editado" in p.stdout
    assert s.edicoes == [(4314, 5161, {"corpo": "<p>insumo: novo corpo</p>"}, "engenharia")]


def test_comentar_edita_aceita_sustenido_e_stdin(stub):
    """DT 743: `--edita #<n>` sem texto lê o corpo de stdin e converte em HTML."""
    s, base = stub
    s.comentarios.append({"id": 5161, "tipo": "insumo", "corpo": "<p>insumo: antigo</p>"})
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    p = subprocess.run(
        [str(BIN), "comentar", "4314", "--edita", "#5161"],
        input="insumo: via stdin", capture_output=True, text=True, env=env, timeout=30,
    )
    assert p.returncode == 0, p.stderr
    assert "comentário #5161 do item 4314 editado" in p.stdout
    assert s.edicoes == [(4314, 5161, {"corpo": "<p>insumo: via stdin</p>"}, "engenharia")]


def test_comentar_edita_recusa_r13_sai_4_e_404_sai_1(stub):
    """DT 743: recusa 400 (R13) sai exit 4 com mensagem; 404 sai exit 1."""
    s, base = stub
    s.comentarios.append({"id": 5161, "tipo": "buraco", "corpo": "<p>buraco: antigo</p>"})
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    p400 = subprocess.run(
        [str(BIN), "comentar", "4314", "--edita", "5161", "pergunta: trocou tipo"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert p400.returncode == 4
    assert "R13" in p400.stderr
    p404 = subprocess.run(
        [str(BIN), "comentar", "4314", "--edita", "9999", "texto"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert p404.returncode == 1
    assert "não existe" in p404.stderr


def test_comentar_edita_uso_errado_sai_2(stub):
    """DT 743: id de comentário inválido, ausente, opção desconhecida ou corpo vazio saem exit 2."""
    _, base = stub
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    for args in (
        ["comentar", "4314", "--edita"],
        ["comentar", "4314", "--edita", "abc", "texto"],
        ["comentar", "4314", "--edita", "5161", "--nada"],
        ["comentar", "4314", "--edita", "5161", "   "],
    ):
        p = subprocess.run([str(BIN), *args], input="", capture_output=True, text=True, env=env, timeout=30)
        assert p.returncode == 2, (args, p.stdout, p.stderr)


def test_comentarios_indice_com_tag_html_cortada_nao_cola_linhas(stub):
    """DT-775: tag HTML aberta perto do byte 100 nao engole o comentario seguinte no --indice."""
    s, base = stub
    corpo1 = "<p>" + ("a" * 94) + "<br>restante do primeiro</p>"
    corpo2 = "<p>segundo comentario</p>"
    s.comentarios.extend([
        {"id": 5128, "autor": "ia", "carimbo": "2026-11-16T12:00:00Z", "corpo": corpo1},
        {"id": 5135, "autor": "ia", "carimbo": "2026-11-16T12:05:00Z", "corpo": corpo2},
    ])
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    p = subprocess.run(
        [str(BIN), "comentarios", "4314", "--indice"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert p.returncode == 0, p.stderr
    linhas = [ln for ln in p.stdout.splitlines() if ln.strip()]
    assert len(linhas) == 2, p.stdout
    assert linhas[0].startswith("#5128 · ")
    assert linhas[1].startswith("#5135 · ")


def test_dt_767_espera_dono_exibe_card_orfao_e_aberto_parado(stub):
    s, base = stub
    s.espera = {
        "do_dono": {"perguntas": [], "prontos_para_aposta": [], "em_homologacao": [], "total": 0},
        "com_cadeiras": {
            "cards": [
                {"id": 100, "titulo": "story sem cadeira", "cadeira": None, "orfao": True, "abertos": []},
                {"id": 102, "titulo": "story com buraco antigo", "cadeira": "engenharia",
                 "abertos": [{"id": 9, "tipo": "buraco", "primeira_linha": "buraco: antigo",
                              "carimbo": "2026-10-01T00:00:00Z", "parado": True}]},
            ],
            "abertos": 1,
            "orfaos": 1,
            "parados": 1,
        },
        "gerado_em": "2026-11-17T12:00:00Z",
    }
    p = _run(["espera-dono"], base)
    assert p.returncode == 0, p.stderr
    assert "com as cadeiras (1 abertos, 1 órfãos, 1 parados):" in p.stdout
    assert "  #100 [—] story sem cadeira · órfão" in p.stdout
    assert "    #9 buraco · parado — buraco: antigo" in p.stdout


def test_inventario_subcomandos_e_leitura(tmp_path):
    """DTs 903/906: `tarefas inventario` expõe ler, criar, editar, validar, cortar, ligar, desligar."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    pedidos = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _resp(self, codigo, corpo):
            b = json.dumps(corpo).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            pedidos.append(("GET", self.path, None))
            if self.path == "/registro":
                self._resp(200, {"estados": []})
            elif self.path.startswith("/itens/4376/inventario"):
                self._resp(200, {
                    "linha": "Inventário: 1 peça, 1 regra (0 validadas, 1 sem story), 0 produtos documentais",
                    "itens": {
                        "pecas": [{"chave": "4376.p1", "descricao": "leitor", "classe_declarada": "componente"}],
                        "regras": [{"chave": "4376.r1", "peca_numero": 1, "frase": "lê tudo", "validada": False}],
                        "documentos": [],
                    },
                })
            elif self.path == "/itens/4376":
                self._resp(200, {
                    "id": 4376, "nivel": 1, "titulo": "Busca", "estado": "em-parecer",
                    "cadeira": "ti", "descricao": "Problema: p",
                    "inventario": {"linha": "Inventário: 1 peça, 0 regras, 0 produtos documentais"},
                })
            else:
                self._resp(404, {"erro": "nao achou"})

        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(tam).decode() or "{}")
            pedidos.append(("POST", self.path, body))
            if self.path == "/itens/4376/inventario/pecas":
                self._resp(200, {"chave": "4376.p1"})
            elif self.path == "/itens/4376/inventario/regras/1/validar":
                self._resp(200, {"chave": "4376.r1", "validada_por": "dono", "validada_em": "2026-11-19"})
            elif self.path == "/itens/4376/inventario/pecas/1/cortar":
                self._resp(200, {"chave": "4376.p1"})
            elif self.path == "/itens/4376/inventario/regras/1/stories":
                self._resp(200, {"chave": "4376.r1"})
            else:
                self._resp(404, {"erro": "nao achou"})

        def do_PATCH(self):
            tam = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(tam).decode() or "{}")
            pedidos.append(("PATCH", self.path, body))
            self._resp(200, {"chave": "4376.r1", "validada": False})

        def do_DELETE(self):
            pedidos.append(("DELETE", self.path, None))
            self._resp(200, {"chave": "4376.r1"})

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        assert "# atos:" in BIN.read_text(encoding="utf-8") and "inventario" in BIN.read_text(encoding="utf-8")
        assert _run(["inventario"], base).returncode == 2
        p_ler = _run(["inventario", "ler", "4376"], base)
        assert p_ler.returncode == 0 and "4376.p1 · leitor" in p_ler.stdout
        p_criar = _run(["inventario", "criar", "4376", "peca", "--descricao", "leitor", "--classe", "componente"], base)
        assert p_criar.returncode == 0 and "4376.p1 criado" in p_criar.stdout
        p_edit = _run(["inventario", "editar", "4376.r1", "--frase", "nova"], base)
        assert p_edit.returncode == 0 and "4376.r1 editado · não validada" in p_edit.stdout
        p_val = _run(["inventario", "validar", "4376.r1", "--frase", "nova"], base)
        assert p_val.returncode == 0 and "4376.r1 validada por dono" in p_val.stdout
        p_cort = _run(["inventario", "cortar", "4376.p1"], base)
        assert p_cort.returncode == 0 and "4376.p1 cortado" in p_cort.stdout
        p_lig = _run(["inventario", "ligar", "4376.r1", "4400"], base)
        assert p_lig.returncode == 0 and "4376.r1 ligada à story 4400" in p_lig.stdout
        p_des = _run(["inventario", "desligar", "4376.r1", "4400"], base)
        assert p_des.returncode == 0 and "4376.r1 desligada da story 4400" in p_des.stdout
        p_card = _run(["ler", "4376"], base)
        assert p_card.returncode == 0 and "Inventário: 1 peça, 0 regras, 0 produtos documentais" in p_card.stdout
    finally:
        srv.shutdown()
        srv.server_close()
