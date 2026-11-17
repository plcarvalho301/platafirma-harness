"""Testes do padrão do verbo da casa nova em `acervo` para `conceito` e `indicacao` (DTs 805 e 806)."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ACERVO = RAIZ / "bin" / "acervo"
sys.path.insert(0, str(RAIZ / "bin" / "_acervo"))
import tesauro as ts  # noqa: E402


class ServidorFalso:
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, str, dict | None]] = []
        self.status_forcado: int | None = None
        self.corpo_forcado: dict | None = None
        self.atraso_s: float = 0.0
        self.versao_atual = "a1b2c3d4e5f6"
        self.pedidos: dict[str, tuple[dict, dict]] = {}
        srv_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _responder(self, status: int, corpo: dict) -> None:
                if srv_ref.atraso_s > 0:
                    time.sleep(srv_ref.atraso_s)
                dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                ct = "application/problem+json" if status >= 400 else "application/json"
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def _ler_corpo(self) -> dict:
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"{}")

            def do_GET(self) -> None:
                srv_ref.chamadas.append(("GET", self.path, None))
                if srv_ref.status_forcado is not None:
                    self._responder(srv_ref.status_forcado, srv_ref.corpo_forcado or {})
                    return
                if self.path == "/acervo/conceitos/inexistente":
                    self._responder(404, {"title": "ConceitoNaoEncontrado", "detail": "inexistente"})
                    return
                if self.path.startswith("/acervo/conceitos/") and self.path.endswith("/relacoes"):
                    self._responder(200, {"itens": [], "proximo": None})
                    return
                if self.path.startswith("/acervo/conceitos/"):
                    slug = self.path.rsplit("/", 1)[1]
                    self._responder(200, {
                        "id": "15a606f0-611f-4f44-b0e6-3ab7b445f44b",
                        "slug": slug,
                        "rotulo": "Técnica legislativa",
                        "lingua": "pt",
                        "definicao": "Arte de redigir leis.",
                        "natureza": "modelo",
                        "estatuto": "doutrinario",
                        "endereco": None,
                        "mais_amplo": None,
                        "filhos_exclusivos": False,
                        "obras_vivas": 2,
                        "rotulos": [{"rotulo": "Técnica legislativa", "lingua": "pt", "papel": "preferido"}],
                        "rotulos_alternativos": [{"rotulo": "legistics", "lingua": "en"}],
                        "versao": srv_ref.versao_atual,
                    })
                    return
                if self.path == "/acervo/conceitos":
                    self._responder(200, {"itens": [
                        {"slug": "tecnica-legislativa", "rotulo": "Técnica legislativa",
                         "natureza": "modelo", "estatuto": "doutrinario"},
                        {"slug": "revisao-de-codigo", "rotulo": "Revisão de código",
                         "natureza": "processo", "estatuto": "doutrinario"},
                    ], "proximo": None})
                    return
                if self.path.startswith("/acervo/indicacoes/"):
                    chave = self.path.rsplit("/", 1)[1]
                    if chave == "nao-existe":
                        self._responder(404, {"title": "IndicacaoNaoEncontrada", "detail": chave})
                        return
                    self._responder(200, {
                        "tipo": "termo",
                        "termo": "licença de software",
                        "slug": chave,
                        "obras_contagem": 0,
                        "obras": [],
                        "de_obra_retirada": ["ind-ret-1"],
                        "destino": {"acao": "sem_garantia", "motivo": "nenhuma obra viva sustenta o termo"},
                        "versao": "998877665544",
                    })
                    return
                if self.path.startswith("/acervo/indicacoes"):
                    self._responder(200, {"versao": "112233445566", "itens": [
                        {"id": "ind-1", "termo": "licença de software", "slug": "licenca-de-software",
                         "estado": "pendente", "obra_id": "obra-r", "obra_retirada": True},
                    ], "proximo": None})
                    return
                self._responder(404, {"title": "NaoEncontrado", "detail": self.path})

            def do_POST(self) -> None:
                corpo = self._ler_corpo()
                srv_ref.chamadas.append(("POST", self.path, corpo))
                if srv_ref.status_forcado is not None:
                    self._responder(srv_ref.status_forcado, srv_ref.corpo_forcado or {})
                    return
                if self.path == "/acervo/conceitos":
                    aplicar = bool(corpo.get("aplicar"))
                    resp = {
                        "modo": "aplicado" if aplicar else "plano",
                        "aprovado": True,
                        "versao": "f6e5d4c3b2a1",
                        "conceito": corpo,
                    }
                    if aplicar:
                        resp["id"] = "cid-novo"
                    self._responder(201 if aplicar else 200, resp)
                    return
                if self.path == "/acervo/indicacoes":
                    aplicar = bool(corpo.get("aplicar"))
                    decisao = corpo.get("decisao")
                    termos = corpo.get("termos") or []
                    if decisao == "descartar":
                        if not aplicar:
                            self._responder(200, {
                                "plano": True, "aprovado": True,
                                "itens": [], "descartes": [{"termo": "licença de software", "indicacoes": 1}],
                            })
                        else:
                            self._responder(201, {
                                "aplicado": True, "aprovado": True,
                                "criados": [], "ligados_a_existente": [], "sem_garantia": [],
                                "indicacoes_admitidas": 0, "indicacoes_descartadas": 1,
                                "motivo": corpo.get("motivo"),
                            })
                        return
                    tem_sem_garantia = ("licenca-de-software" in termos) or (not termos)
                    itens = [
                        {"termo": "protocolo HTTP", "slug": "protocolo-http", "obras_contagem": 1,
                         "obras": ["o1"], "indicacao_ids": ["i1"], "de_obra_retirada": [],
                         "acao": "ligar_existente", "conceito": "http"},
                        {"termo": "filtragem de URL", "slug": "filtragem-de-url", "obras_contagem": 2,
                         "obras": ["o2", "o3"], "indicacao_ids": ["i2", "i3"], "de_obra_retirada": ["i4"],
                         "acao": "criar", "conceito": "filtragem-de-url"},
                    ]
                    if tem_sem_garantia:
                        itens.append({
                            "termo": "licença de software", "slug": "licenca-de-software",
                            "obras_contagem": 0, "obras": [], "indicacao_ids": ["i5"],
                            "de_obra_retirada": ["i5"], "acao": "sem_garantia",
                            "motivo": "nenhuma obra viva sustenta o termo; descarte-o",
                        })
                    if not aplicar:
                        aprovado = not (decisao == "admitir" and tem_sem_garantia)
                        self._responder(200, {
                            "plano": True, "aprovado": aprovado, "total_termos": len(itens),
                            "itens": itens, "descartes": [{"termo": t, "indicacoes": 1} for t in (corpo.get("descartar") or [])],
                        })
                        return
                    if decisao == "admitir" and tem_sem_garantia:
                        self._responder(422, {
                            "title": "IndicacaoReprovada",
                            "detail": "obra retirada não sustenta indicação como garantia literária: licença de software",
                            "plano": {"aprovado": False, "itens": itens},
                        })
                        return
                    self._responder(201, {
                        "aplicado": True, "aprovado": True,
                        "criados": [{"id": "c-novo", "slug": "filtragem-de-url", "rotulo": "filtragem de URL"}],
                        "ligados_a_existente": [{"id": "c-http", "slug": "http", "termo": "protocolo HTTP"}],
                        "sem_garantia": [],
                        "indicacoes_admitidas": 3,
                        "indicacoes_descartadas": 1,
                        "motivo": corpo.get("motivo"),
                    })
                    return
                self._responder(404, {"title": "NaoEncontrado", "detail": self.path})

            def do_PATCH(self) -> None:
                corpo = self._ler_corpo()
                srv_ref.chamadas.append(("PATCH", self.path, corpo))
                if srv_ref.status_forcado is not None:
                    self._responder(srv_ref.status_forcado, srv_ref.corpo_forcado or {})
                    return
                aplicar = bool(corpo.get("aplicar"))
                ped_id = corpo.get("pedido")
                limpo = {k: v for k, v in corpo.items() if k not in ("pedido", "aplicar")}
                if aplicar and ped_id and ped_id in srv_ref.pedidos:
                    gravado_limpo, resp_grav = srv_ref.pedidos[ped_id]
                    if gravado_limpo != limpo:
                        self._responder(422, {"title": "PedidoComConteudoDiferente", "detail": ped_id})
                        return
                    self._responder(200, {**resp_grav, "pedido": ped_id, "estado_pedido": "ja-gravada"})
                    return
                if "versao" in corpo and corpo["versao"] != srv_ref.versao_atual:
                    self._responder(409, {
                        "title": "VersaoDiferente",
                        "detail": "versão divergente",
                        "versao_esperada": corpo["versao"],
                        "versao_atual": srv_ref.versao_atual,
                    })
                    return
                resp = {
                    "modo": "aplicado" if aplicar else "plano",
                    "aprovado": True,
                    "id": "15a606f0-611f-4f44-b0e6-3ab7b445f44b",
                    "versao_antes": srv_ref.versao_atual,
                    "versao": "c0ffee123456",
                    "conceito": {"slug": "tecnica-legislativa", "rotulo": corpo.get("rotulo") or "Técnica legislativa"},
                    "antes": {"rotulo": "Técnica legislativa", "definicao": "Antiga", "rotulos": []},
                    "depois": {
                        "rotulo": corpo.get("rotulo") or "Técnica legislativa",
                        "definicao": corpo.get("definicao") or "Antiga",
                        "rotulos": [{"rotulo": "Técnica legislativa", "lingua": corpo.get("lingua") or "pt", "papel": "preferido"}],
                    },
                    "colisoes": [],
                    "motivo": corpo.get("motivo"),
                    "emitido_por": corpo.get("autor") or "time-platafirma",
                }
                if aplicar and ped_id:
                    srv_ref.pedidos[ped_id] = (limpo, resp)
                    resp = {**resp, "pedido": ped_id, "estado_pedido": "gravada"}
                self._responder(200, resp)

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._http.server_address[1]}"
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()

    def fechar(self) -> None:
        self._http.shutdown()
        self._http.server_close()
        self._thread.join(timeout=5)

    def env(self) -> dict[str, str]:
        from test_acervo_atos_classificar import _acha_python

        py = _acha_python()
        env = {
            **os.environ,
            "MOTOR_ACERVO_URL": self.url,
            "RAG_API_URL": self.url,
            "RAG_API_BASE": self.url,
            "PF_CADEIRA": "engenharia",
        }
        if py:
            env["PATH"] = str(Path(py).parent) + os.pathsep + env.get("PATH", "")
        return env

    def rodar(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(ACERVO), *args],
            env=self.env(),
            capture_output=True,
            text=True,
            timeout=30,
        )


@pytest.fixture
def srv():
    s = ServidorFalso()
    try:
        yield s
    finally:
        s.fechar()


def _checar_erro_6_campos(proc: subprocess.CompletedProcess[str], exit_esperado: int, codigo: str) -> dict:
    assert proc.returncode == exit_esperado, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    if exit_esperado in (2, 3, 4, 5):
        ultima = [ln for ln in proc.stderr.splitlines() if ln.strip()][-1]
        obj_err = json.loads(ultima)["erro"]
        for k in ("codigo", "onde", "recebido", "regra", "cura", "proximo"):
            assert k in obj_err, (k, obj_err)
        assert obj_err["codigo"] == codigo
        return obj_err
    assert codigo in proc.stdout
    for trecho in ("recebido:", "regra:", "cura:", "proximo:"):
        assert trecho in proc.stdout
    return {}


@pytest.mark.parametrize("argv", [
    ("ler", "biblioteca", "conceito", "--help"),
    ("listar", "biblioteca", "conceito", "--help"),
    ("criar", "biblioteca", "conceito", "--help"),
    ("trocar", "biblioteca", "conceito", "--help"),
    ("renomear", "biblioteca", "conceito", "--help"),
    ("listar", "biblioteca", "indicacao", "--help"),
    ("ler", "biblioteca", "indicacao", "--help"),
    ("admitir", "biblioteca", "indicacao", "--help"),
    ("descartar", "biblioteca", "indicacao", "--help"),
    ("ensaiar", "--help"),
    ("curar", "conceitos", "--help"),
])
def test_help_por_ato_sai_0_sem_chamar_rede(srv, argv):
    r = srv.rodar(*argv)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip()
    assert srv.chamadas == []


def test_ler_e_listar_conceito_primeira_linha_fixa_e_404_sai_1(srv):
    r = srv.rodar("ler", "biblioteca", "conceito", "tecnica-legislativa")
    assert r.returncode == 0, r.stderr
    primeira = r.stdout.splitlines()[0]
    assert primeira == f"conceito · versao {srv.versao_atual} · tecnica-legislativa"
    assert "pt" in r.stdout and "en|legistics" in r.stdout

    rj = srv.rodar("ler", "conceito", "tecnica-legislativa", "--json")
    assert rj.returncode == 0
    assert json.loads(rj.stdout)["versao"] == srv.versao_atual

    rl = srv.rodar("listar", "biblioteca", "conceito", "--natureza", "modelo")
    assert rl.returncode == 0
    assert rl.stdout.splitlines()[0].startswith("conceito · versao ")
    assert rl.stdout.splitlines()[0].endswith("· 1 itens")

    r404 = srv.rodar("ler", "biblioteca", "conceito", "inexistente")
    _checar_erro_6_campos(r404, 1, "conceito-inexistente")


def test_gravar_em_classe_guardada_recusa_com_2_e_proximo(srv):
    r = srv.rodar("gravar", "biblioteca", "conceito", "tecnica-legislativa")
    err = _checar_erro_6_campos(r, 2, "ato-recusado")
    assert "acervo ler biblioteca conceito tecnica-legislativa" in err["proximo"]
    assert srv.chamadas == []


def test_dry_run_em_ato_de_escrita_recusa_com_2_e_aponta_ensaiar(srv):
    r = srv.rodar("criar", "biblioteca", "conceito", "x", "--dry-run")
    err = _checar_erro_6_campos(r, 2, "variante-de-flag")
    assert "ensaiar criar" in err["proximo"]
    assert srv.chamadas == []


def test_criar_e_ensaiar_criar_conceito(srv):
    re_ens = srv.rodar(
        "ensaiar", "criar", "biblioteca", "conceito", "code-review",
        "--rotulo", "Code review", "--lingua", "en",
        "--definicao", "Exame sistemático de código.",
        "--natureza", "processo", "--estatuto", "doutrinario",
        "--rotulo-alt", "pt|revisão de código",
    )
    assert re_ens.returncode == 0, re_ens.stderr
    assert re_ens.stdout.splitlines()[0].startswith("ensaio aprovado · criar conceito:code-review")
    assert srv.chamadas[-1][2]["aplicar"] is False

    r_cr = srv.rodar(
        "criar", "biblioteca", "conceito", "code-review",
        "--rotulo", "Code review", "--lingua", "en",
        "--definicao", "Exame sistemático de código.",
        "--natureza", "processo", "--estatuto", "doutrinario",
        "--rotulo-alt", "pt|revisão de código",
    )
    assert r_cr.returncode == 0, r_cr.stderr
    linhas = r_cr.stdout.splitlines()
    assert ts.validar_uuid(linhas[0])
    assert linhas[1].startswith("criada conceito:code-review · versao ")
    assert srv.chamadas[-1][2]["aplicar"] is True


def test_trocar_conceito_versao_rotulos_idempotencia_e_recusas(srv):
    # Slug em trocar recusa com 2 apontando para renomear
    r_slug = srv.rodar("trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
                       "--slug", "outro", "--motivo", "m")
    err_s = _checar_erro_6_campos(r_slug, 2, "flag-nao-aplicavel")
    assert "renomear" in err_s["proximo"]

    # Versão velha devolve 1 (versao-diferente) apontando para ler
    r_v = srv.rodar("trocar", "biblioteca", "conceito", "tecnica-legislativa", "000000000000",
                    "--lingua", "pt", "--motivo", "ont:0086")
    _checar_erro_6_campos(r_v, 1, "versao-diferente")
    assert "acervo ler biblioteca conceito tecnica-legislativa" in r_v.stdout

    # Ensaio não grava e mostra antes/depois
    r_ens = srv.rodar(
        "ensaiar", "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "pt", "--rotulo-alt", "en|legistics", "--sem-rotulo-alt", "velho",
        "--motivo", "ont:0086",
    )
    assert r_ens.returncode == 0, r_ens.stderr
    assert r_ens.stdout.splitlines()[0].startswith("ensaio aprovado · trocar conceito:tecnica-legislativa")
    assert srv.chamadas[-1][2]["aplicar"] is False

    # Escrita com --pedido explícito e idempotência
    ped = ts.gerar_uuid7()
    r1 = srv.rodar(
        "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "pt", "--rotulo-alt", "en|legistics", "--motivo", "ont:0086",
        "--pedido", ped,
    )
    assert r1.returncode == 0, r1.stderr
    assert r1.stdout.splitlines()[0] == ped
    assert r1.stdout.splitlines()[1].startswith("gravada conceito:tecnica-legislativa")

    r2 = srv.rodar(
        "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "pt", "--rotulo-alt", "en|legistics", "--motivo", "ont:0086",
        "--pedido", ped,
    )
    assert r2.returncode == 0
    assert r2.stdout.splitlines()[1].startswith("ja-gravada conceito:tecnica-legislativa")

    r3 = srv.rodar(
        "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "en", "--motivo", "outro", "--pedido", ped,
    )
    _checar_erro_6_campos(r3, 1, "pedido-com-conteudo-diferente")


def test_indicacao_listar_ler_admitir_e_descartar_com_garantia_viva(srv):
    rl = srv.rodar("listar", "biblioteca", "indicacao")
    assert rl.returncode == 0, rl.stderr
    assert rl.stdout.splitlines()[0].startswith("indicacao · versao ")
    assert "ligar ao existente http" in rl.stdout
    assert "sem garantia (só obra retirada)" in rl.stdout

    rler = srv.rodar("ler", "biblioteca", "indicacao", "licenca-de-software")
    assert rler.returncode == 0
    assert rler.stdout.splitlines()[0] == "indicacao · versao 998877665544 · licenca-de-software"

    # Admitir todas inclui termo sustentado só por obra retirada -> ensaio e escrita saem 1
    r_ens_fail = srv.rodar("ensaiar", "admitir", "biblioteca", "indicacao", "todas", "--motivo", "triagem")
    _checar_erro_6_campos(r_ens_fail, 1, "garantia-retirada")

    r_adm_fail = srv.rodar("admitir", "biblioteca", "indicacao", "todas", "--motivo", "triagem")
    _checar_erro_6_campos(r_adm_fail, 1, "garantia-retirada")

    # Admitir apenas os termos com garantia viva -> 0, liga ao existente e cria o novo
    r_adm_ok = srv.rodar(
        "admitir", "biblioteca", "indicacao", "todas",
        "--termos", "protocolo-http,filtragem-de-url", "--motivo", "obras vivas conferidas",
    )
    assert r_adm_ok.returncode == 0, r_adm_ok.stderr
    assert ts.validar_uuid(r_adm_ok.stdout.splitlines()[0])
    assert "1 criado(s) · 1 ligado(s) ao existente" in r_adm_ok.stdout

    # Descartar recusa --natureza com 2, e com --motivo passa a descartada
    r_desc_flag = srv.rodar(
        "descartar", "biblioteca", "indicacao", "todas",
        "--termos", "licenca-de-software", "--natureza", "modelo", "--motivo", "m",
    )
    _checar_erro_6_campos(r_desc_flag, 2, "flag-nao-aplicavel")

    r_desc = srv.rodar(
        "descartar", "biblioteca", "indicacao", "todas",
        "--termos", "licenca-de-software", "--motivo", "obra de garantia foi retirada",
    )
    assert r_desc.returncode == 0, r_desc.stderr
    assert "1 descartada(s)" in r_desc.stdout


def test_codigos_de_saida_3_4_e_5(srv):
    srv.status_forcado = 403
    srv.corpo_forcado = {"title": "Forbidden", "detail": "negado"}
    r4 = srv.rodar("ler", "biblioteca", "conceito", "tecnica-legislativa")
    _checar_erro_6_campos(r4, 4, "acesso-recusado")

    srv.status_forcado = 503
    srv.corpo_forcado = {"title": "FonteIndisponivel", "detail": "banco fora"}
    r3 = srv.rodar("ler", "biblioteca", "conceito", "tecnica-legislativa")
    _checar_erro_6_campos(r3, 3, "servico-indisponivel")
    srv.status_forcado = None

    # Timeout durante escrita -> exit 5 (indeterminável) com o pedido registrado
    ped = ts.gerar_uuid7()
    orig_req = ts.urllib.request.urlopen

    def _timeout_urlopen(*args, **kwargs):
        raise TimeoutError("prazo esgotado")

    ts.urllib.request.urlopen = _timeout_urlopen
    try:
        rc = ts.main([
            "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
            "--lingua", "pt", "--motivo", "teste", "--pedido", ped,
        ])
        assert rc == 5
    finally:
        ts.urllib.request.urlopen = orig_req


def test_atos_transicionais_recusam_flags_indevidas_e_enviam_motivo(srv):
    from test_acervo_atos_classificar import _acha_python

    if _acha_python():
        r_indev = srv.rodar(
            "definir", "biblioteca", "conceito", "tecnica-legislativa",
            "--lingua", "pt", "--endereco", "https://x.org", "--motivo", "m",
        )
        assert r_indev.returncode == 2
        assert "--endereco" in r_indev.stderr

        r_hum = srv.rodar(
            "definir", "biblioteca", "conceito", "tecnica-legislativa",
            "--lingua", "pt", "--rotulo-alt", "en|legistics", "--motivo", "ont:0086",
        )
        assert r_hum.returncode == 0, r_hum.stderr
        assert "Plano de descrição e rótulos" in r_hum.stdout
        assert "pt|Técnica legislativa (preferido)" in r_hum.stdout

    r_cur_desc = srv.rodar(
        "curar", "conceitos", "--indicacoes", "todas",
        "--descartar", "licenca-de-software", "--motivo", "obra retirada",
    )
    assert r_cur_desc.returncode == 0, r_cur_desc.stderr
    assert srv.chamadas[-1][2]["motivo"] == "obra retirada"

    r_cur_unk = srv.rodar("curar", "conceitos", "--indicacoes", "todas", "--flag-inexistente")
    assert r_cur_unk.returncode == 2
