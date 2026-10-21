"""Verbo tarefas: moldes do two-pager, do comentário tipado e da story derivada, e o fecho
no próprio comentário (card #3410).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que
o VERBO faz — o molde que imprime, o corpo que envia, as recusas da forma do comentário —
sem tocar no board de verdade. A regra de transição é do rastreador e tem self-check lá.
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


class _Stub(BaseHTTPRequestHandler):
    """Imita só o que `fechar_comentario` precisa da rota própria (card #3593, #3597): a
    recusa de tipo sem vocabulário, a de resultado fora dele e a de fecho repetido são regra
    da API, com self-check lá — aqui só o status e o dado que viajam na resposta."""

    comentarios: list = []
    fechos: list = []
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
        m = re.match(r"^/itens/(\d+)/comentarios$", self.path)
        if m:
            return self._json({"item": int(m.group(1)), "comentarios": self.comentarios})
        self._json({"erro": "nao existe"}, 404)

    def do_POST(self):
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
    _Stub.comentarios, _Stub.fechos, _Stub.espera = [], [], {}
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base="http://127.0.0.1:9", stdin=None):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env,
                          input=stdin)


def _rotulos(texto):
    return [m.group(1) for m in re.finditer(r"(?m)^([A-ZÀ-Úa-zà-ú][^:\n]{0,30}):", texto)]


def test_modelo_feature_e_o_two_pager_na_ordem():
    p = _run(["modelo", "feature"])
    assert p.returncode == 0, p.stderr
    assert _rotulos(p.stdout) == ["Problema", "Solução", "Peças", "Fora", "Resultado", "Medida",
                                  "Apetite", "Aberto", "Produtos documentais", "Regras", "Sai quando"]
    assert "Continuidade" not in p.stdout and "Fontes" not in p.stdout and "Quebra" not in p.stdout
    assert "título" in p.stderr


def test_modelo_feature_e_story_refinada_levam_as_regras_uma_vez():
    """Card #3937 (arq:0096, emenda de 21/10/2026): Regras na feature, Regras novas no Plano."""
    feature = _run(["modelo", "feature"])
    assert feature.returncode == 0, feature.stderr
    assert _rotulos(feature.stdout).count("Regras") == 1
    assert "Regras novas" not in _rotulos(feature.stdout)
    plano = _run(["modelo", "story", "refinada"])
    assert plano.returncode == 0, plano.stderr
    rotulos = _rotulos(plano.stdout)
    assert rotulos.count("Regras novas") == 1 and "Regras" not in rotulos
    assert rotulos.index("Premissas") < rotulos.index("Regras novas") < rotulos.index("Unidades")
    story = _run(["modelo", "story"])
    assert story.returncode == 0, story.stderr
    regras = [l for l in story.stdout.splitlines() if l.startswith("Regras:")]
    assert len(regras) == 1 and "só story sem pai" in regras[0]
    assert "Regras:" not in _run(["modelo", "épico"]).stdout


def test_para_html_separa_regras_e_regras_novas():
    """Card #3937: sem os rótulos na lista, o bloco caía no parágrafo anterior."""
    assert _para_html("Produtos documentais: d\nRegras:\n1. a → b") == (
        "<p><strong>Produtos documentais:</strong> d</p><p><strong>Regras:</strong><br>1. a → b</p>")
    assert _para_html("Premissas: p\nRegras novas:\n1. a → b") == (
        "<p><strong>Premissas:</strong> p</p><p><strong>Regras novas:</strong><br>1. a → b</p>")


def test_modelo_epico_sem_indice_de_feature():
    p = _run(["modelo", "épico"])
    assert p.returncode == 0, p.stderr
    assert _rotulos(p.stdout) == ["Problema", "Solução", "Peças", "Fora", "Resultado", "Medida",
                                  "Apetite", "Aberto"]
    assert "Quebra" not in p.stdout


@pytest.mark.parametrize("tipo,fixas", [
    ("insumo", ["Traz"]), ("pergunta", []), ("buraco", ["Caso", "Remendo"]),
    ("requisito", ["Confere"]), ("decisão", ["Descartado", "Substitui"]),
])
def test_modelo_comentario_topo_fixas_branco_argumento(tipo, fixas):
    p = _run(["modelo", "comentario", tipo])
    assert p.returncode == 0, p.stderr
    linhas = p.stdout.splitlines()
    assert linhas[0].startswith(tipo)
    assert [l.split(":")[0] for l in linhas[1:1 + len(fixas)]] == fixas
    assert linhas[1 + len(fixas)] == "" and linhas[2 + len(fixas)].startswith("<argumento")


def test_modelo_comentario_sem_tipo_e_uso():
    assert _run(["modelo", "comentario"]).returncode == 2


def test_modelo_story_derivada_aponta_o_item():
    p = _run(["modelo", "story", "derivada"])
    assert p.returncode == 0, p.stderr
    neg = next(l for l in p.stdout.splitlines() if l.startswith("Negócio:"))
    assert "R<a>" in neg and "D<n>" in neg and "Peça <n>" in neg
    assert "R<n> ou D<n>" in next(l for l in p.stdout.splitlines() if l.startswith("Aceite:"))


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


def test_para_html_separa_os_rotulos_do_two_pager(stub):
    """O achado do #3408: Solução e Peças caíam dentro de Medida e de Fora."""
    s, base = stub
    s.comentarios = [{"id": 1, "corpo": "<p>pergunta (x): y</p>"}]
    corpo = "Medida: m\nSolução:\n- Ao lapidar: a\nPeças:\n1. p\nAberto: z\nProdutos documentais:\n- d"
    p = subprocess.run(["bash", "-c", f'source <(sed -n "/^para_html()/,/^}}/p" {BIN}); para_html'],
                       input=corpo, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    for r in ("Medida", "Solução", "Peças", "Aberto", "Produtos documentais"):
        assert f"<p><strong>{r}:</strong>" in p.stdout, (r, p.stdout)


def _para_html(texto):
    p = subprocess.run(["bash", "-c", f'source <(sed -n "/^para_html()/,/^}}/p" {BIN}); para_html'],
                       input=texto, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p.stdout.rstrip("\n")


def test_para_html_liga_url_solta_so_http_e_https():
    """Card #3740. Mesmos textos e mesmas saídas da prova de platafirma-rastreador@api/logica.py (R34)."""
    assert _para_html("veja https://exemplo.org/a/b.") == (
        '<p>veja <a href="https://exemplo.org/a/b">https://exemplo.org/a/b</a>.</p>')
    assert _para_html("Traz: http://x.org/p?a=1&b=2, e (https://y.org/z)") == (
        '<p><strong>Traz:</strong> <a href="http://x.org/p?a=1&amp;b=2">http://x.org/p?a=1&amp;b=2</a>,'
        ' e (<a href="https://y.org/z">https://y.org/z</a>)</p>')
    assert _para_html("<https://x.org>") == '<p>&lt;<a href="https://x.org">https://x.org</a>&gt;</p>'
    assert "<a " not in _para_html("javascript:alert(1) e ftp://x.org e https:// vazio")
    assert "<script>" not in _para_html('"><script>https://x.org')
    assert _para_html("veja `https://exemplo.test/a` fim") == (
        '<p>veja `<a href="https://exemplo.test/a">https://exemplo.test/a</a>` fim</p>')
    assert "<a " not in _para_html("os esquemas `http://` e `https://`")
    assert _para_html("_Generated by [Claude Code](https://claude.ai/code)_") == (
        '<p>_Generated by [Claude Code](<a href="https://claude.ai/code">https://claude.ai/code</a>)_</p>')


def test_para_html_poe_em_negrito_os_rotulos_de_decisao_e_de_insumo():
    """Card #3740 (comentário #2862): a tela só destaca o que a conversão marca."""
    for r in ("Decidiu", "Ficha", "Golden", "Motivo", "Por que importa", "O que já se sabe",
              "Resposta esperada", "Consequência no corpo"):
        assert _para_html(f"antes\n{r}: z") == f"<p>antes</p><p><strong>{r}:</strong> z</p>", r
    assert _para_html("o Motivo: x") == "<p>o Motivo: x</p>"
    assert _para_html("Decidiu: a\nAlgo que não é rótulo: y") == (
        "<p><strong>Decidiu:</strong> a<br>Algo que não é rótulo: y</p>")
