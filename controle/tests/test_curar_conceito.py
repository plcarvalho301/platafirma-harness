"""DT #315: `curar --conceito <slug>` sem `--pai` (criação de conceito isolado / raiz).

Verifica que:
1. Conceito sem pai roda o HermiT pelo mesmo caminho do conceito com pai (_hermit_com).
2. O plano seco usa formatação própria de conceito (`Plano de conceito:`), não descreve aresta
   inexistente (`Plano de aresta: ...`) e sai 0 quando aprovado.
3. O retorno de `--apply` (`Conceito gravado:`) não oferece desrelacionar com o id do conceito.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import pytest

from test_curar_renomear import PATCH_EXPORT, PY, _curar, _hermit_falso, ambiente  # noqa: F401

pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")

SLUG = "novo-conceito"
ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EDGE_ID = "edge-1111-2222-3333-4444"
BASE_ARGS = (
    "--conceito", SLUG,
    "--rotulo", "Novo Conceito",
    "--definicao", "Definição do novo conceito",
    "--natureza", "modelo",
    "--estatuto", "preliminar",
    "--autor", "dados",
)
CONFERENCIAS = ("ciclo", "categoria", "exclusividade", "ciclo_coluna")


def plano_conceito(corpo, **over):
    """O que o servidor mock responde para criação de conceito."""
    modo = "aplicado" if corpo.get("aplicar") else "plano"
    tem_pai = "pai" in corpo
    p = {
        "modo": modo,
        "aprovado": True,
        "conceito": {
            "id": ID,
            "slug": corpo.get("slug") or SLUG,
            "rotulo": corpo.get("rotulo") or "Novo Conceito",
            "natureza": corpo.get("natureza") or "modelo",
            "estatuto": corpo.get("estatuto") or "preliminar",
        },
        "emitido_por": corpo.get("autor") or "dados",
        "conferencias": {n: {"antes": 0, "depois": 0, "novas": []} for n in CONFERENCIAS},
    }
    if tem_pai:
        pai = corpo["pai"]
        p["aresta"] = {
            "de": corpo.get("slug") or SLUG,
            "para": pai.get("slug"),
            "tipo": pai.get("tipo"),
            "familia": "hierarquica",
            "garantia": pai.get("garantia"),
            "motivo": pai.get("motivo"),
            "id": EDGE_ID,
        }
        p["molde"] = "A é um tipo de B"
    if modo == "aplicado":
        p["id"] = EDGE_ID if tem_pai else ID
    p.update(over)
    return p


class FalsoConceito:
    def __init__(self):
        self.cenario_get = lambda caminho: (404, {"type": "about:blank", "title": "ConceitoNaoEncontrado"})
        self.cenario_post = lambda corpo, caminho: (200, plano_conceito(corpo))
        self.cenario_patch = lambda corpo, caminho: (200, plano_conceito(corpo))
        self.chamadas = []
        falso = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _resp(self, status, obj):
                dados = json.dumps(obj).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/problem+json" if status >= 400 else "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_GET(self):
                falso.chamadas.append(("GET", self.path, None))
                self._resp(*falso.cenario_get(self.path))

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
                falso.chamadas.append(("POST", self.path, corpo))
                self._resp(*falso.cenario_post(corpo, self.path))

            def do_PATCH(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
                falso.chamadas.append(("PATCH", self.path, corpo))
                self._resp(*falso.cenario_patch(corpo, self.path))

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def fecha(self):
        self.servidor.shutdown()
        self.servidor.server_close()


@pytest.fixture
def falso():
    f = FalsoConceito()
    yield f
    f.fecha()


def test_plano_seco_sem_pai_sem_hermit_sai_0_e_formata_conceito(ambiente, falso):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    s = p.stdout
    assert f"Plano de conceito: {SLUG}  «Novo Conceito»" in s
    assert "natureza/estatuto: modelo / preliminar" in s
    assert "veredito: APROVADO — repita com --apply para gravar" in s
    assert "Plano de aresta" not in s
    assert "desrelacionar" not in s
    assert [c for c in falso.chamadas if c[0] == "POST"] == [
        ("POST", "/acervo/conceitos", {
            "slug": SLUG,
            "rotulo": "Novo Conceito",
            "definicao": "Definição do novo conceito",
            "natureza": "modelo",
            "estatuto": "preliminar",
            "autor": "dados",
            "aplicar": False,
        })
    ]


def test_plano_seco_sem_pai_com_hermit_roda_projecao_e_aprova(ambiente, tmp_path):
    env, anotados = _hermit_falso(tmp_path, ambiente)
    p = _curar(env, *BASE_ARGS)
    assert p.returncode == 0, p.stdout + p.stderr
    s = p.stdout
    assert f"Plano de conceito: {SLUG}  «Novo Conceito»" in s
    assert "HermiT insatisfazíveis 0 -> 0  OK" in s
    assert "veredito: APROVADO — repita com --apply para gravar" in s
    assert "HermiT: indisponível" not in s
    chamadas = anotados.read_text(encoding="utf-8").splitlines()
    assert len(chamadas) >= 1


def test_apply_sem_pai_grava_sem_oferecer_desrelacionar(ambiente, falso):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 0, p.stdout + p.stderr
    s = p.stdout
    assert f"Conceito gravado: {SLUG}  «Novo Conceito»" in s
    assert f"id     : {ID}" in s
    assert "export : regenerado no clone" in s
    assert "desrelacionar" not in s
    assert "Plano de aresta" not in s
    posts = [c for c in falso.chamadas if c[0] == "POST"]
    assert len(posts) == 2
    assert posts[0][2]["aplicar"] is False
    assert posts[1][2]["aplicar"] is True


def test_plano_seco_sem_pai_reprovado_sai_1(ambiente, falso):
    falso.cenario_post = lambda corpo, caminho: (200, plano_conceito(corpo, aprovado=False))
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 1, p.stdout + p.stderr
    assert "veredito: REPROVADO — nada gravado" in p.stdout


def test_conceito_com_pai_usa_formato_de_aresta_e_oferece_desrelacionar(ambiente, falso):
    args_com_pai = BASE_ARGS + (
        "--pai", "conceito-pai",
        "--tipo", "generica",
        "--garantia", "instituida",
        "--motivo", "o novo conceito é especialização de conceito-pai",
    )
    p = _curar(ambiente, *args_com_pai, "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 0, p.stdout + p.stderr
    s = p.stdout
    assert "Aresta aplicada: novo-conceito -generica-> conceito-pai" in s
    assert f"(desfazer: curar --desrelacionar {EDGE_ID})" in s
