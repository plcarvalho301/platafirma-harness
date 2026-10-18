"""Verbo tarefas: originação, executor, ordem, vínculo, despriorizar e carteira (card #3526; R19,
R21, R23, R24 e R25 da spec tarefas).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que o VERBO
faz — o corpo que envia, a query que monta, o que imprime e o que recusa — e não a regra, que é do
rastreador e tem self-check lá (#3521 a #3525). O stub devolve o que a API no ar devolve (campos de
`api/logica.py` e `api/app.py` em platafirma-rastreador).
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"

REGISTRO = {
    "estados": [
        {"estado": "captada", "ordem": 10, "natureza": "fila", "fase": "funil"},
        {"estado": "priorizada", "ordem": 40, "natureza": "fila", "fase": "funil"},
        {"estado": "despriorizada", "ordem": 55, "natureza": "fila", "fase": "funil"},
        {"estado": "em-execucao", "ordem": 70, "natureza": "trabalho", "fase": "delivery"},
        {"estado": "entregue", "ordem": 100, "natureza": "terminal", "fase": "terminal"},
        {"estado": "cancelada", "ordem": 110, "natureza": "terminal", "fase": "terminal"},
    ],
    "motivos": [],
}
MOTIVOS = [{"codigo": c, "nome": n} for c, n in [
    ("outra-aposta", "Outra aposta passou na frente"),
    ("incidente", "Incidente tomou a vez"),
    ("espera-dependencia", "Espera uma dependência"),
    ("espera-decisao-externa", "Espera decisão externa"),
    ("sem-tokens", "Sem tokens"),
]]


class _Stub(BaseHTTPRequestHandler):
    rotas: dict = {}      # (método, caminho sem query) -> (status, corpo) | função(corpo) -> (status, corpo)
    chamadas: list = []   # (método, caminho com query, corpo)

    def log_message(self, *a):  # silencioso
        pass

    def _atende(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}") if n else None
        partes = urlsplit(self.path)
        type(self).chamadas.append((self.command, self.path, corpo))
        r = type(self).rotas.get((self.command, partes.path))
        if r is None:
            status, payload = 404, {"erro": f"sem rota: {self.command} {partes.path}"}
        else:
            status, payload = r(corpo) if callable(r) else r
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    do_GET = do_POST = do_PATCH = do_DELETE = _atende


@pytest.fixture()
def stub():
    _Stub.rotas, _Stub.chamadas = {("GET", "/registro"): (200, REGISTRO)}, []
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base="http://127.0.0.1:9", stdin=None, **env_extra):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia", **env_extra)
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env, input=stdin)


def _item(id, estado="em-execucao", **resto):
    fase = {"priorizada": "funil", "despriorizada": "funil", "captada": "funil",
            "em-execucao": "delivery"}.get(estado, "terminal")
    return {"id": id, "titulo": f"item {id}", "estado": estado, "estado_fase": fase,
            "estado_derivado": None, "cadeira": "engenharia", "pai": None, **resto}


def _lista(*itens):
    return (200, {"itens": list(itens), "estados": REGISTRO["estados"], "total": len(itens)})


def _caminhos(s, metodo=None):
    return [c for m, c, _ in s.chamadas if metodo is None or m == metodo]


# --- criar e editar: originação e executor (R19) ------------------------------------------

def test_criar_manda_originacao_e_executor(stub):
    s, base = stub
    s.rotas[("POST", "/itens")] = (201, {"id": 9, "titulo": "prova"})
    p = _run(["criar", "prova", "--originacao", "tecnico", "--executor", "dados"], base)
    assert p.returncode == 0, p.stderr
    corpo = s.chamadas[-1][2]
    assert corpo["tipo_demanda"] == "tecnico" and corpo["executor"] == "dados"
    assert "item 9 criado" in p.stdout


def test_criar_sem_os_campos_nao_os_manda(stub):
    """Sem eles a API herda (originação do pai, executor igual à cadeira): o verbo não decide."""
    s, base = stub
    s.rotas[("POST", "/itens")] = (201, {"id": 9, "titulo": "prova"})
    assert _run(["criar", "prova"], base).returncode == 0
    assert "tipo_demanda" not in s.chamadas[-1][2] and "executor" not in s.chamadas[-1][2]


def test_criar_originacao_fora_do_registro_sai_1_com_a_recusa_da_api(stub):
    s, base = stub
    s.rotas[("POST", "/itens")] = (422, {"erro": "tipo_demanda `xyz` fora do registro (negocio, tecnico, incidente)"})
    p = _run(["criar", "prova", "--originacao", "xyz"], base)
    assert p.returncode == 1
    assert "fora do registro" in p.stderr


def test_editar_manda_originacao_e_executor(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/3")] = (200, {"id": 3, "titulo": "t", "estado_nome": "Em execução",
                                            "tipo_demanda": "tecnico", "executor": "dados"})
    p = _run(["editar", "3", "--originacao", "tecnico", "--executor", "dados"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[-1][2] == {"tipo_demanda": "tecnico", "executor": "dados"}
    assert "originação tecnico" in p.stdout and "executor dados" in p.stdout


def test_editar_so_com_executor_nao_e_nada_a_editar(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/3")] = (200, {"id": 3, "titulo": "t", "estado_nome": "x"})
    assert _run(["editar", "3", "--executor", "dados"], base).returncode == 0
    assert _run(["editar", "3"], base).returncode == 2


# --- listar: filtros, ordem do posto e paradas escondidas (R19, R21, R25) ---------------

def test_listar_passa_os_filtros_novos_e_o_estado_novo_adiante(stub):
    s, base = stub
    s.rotas[("GET", "/itens")] = _lista()
    p = _run(["listar", "--originacao", "tecnico", "--executor", "dados", "--estado", "despriorizada"], base)
    assert p.returncode == 0, p.stderr
    q = _caminhos(s, "GET")[-1]
    assert "tipo_demanda=tecnico" in q and "executor=dados" in q and "estado=despriorizada" in q


def test_listar_estado_desconhecido_e_recusa_da_api_nao_do_verbo(stub):
    s, base = stub
    s.rotas[("GET", "/itens")] = (400, {"erro": "estado desconhecido: `xyz` (válidos: captada, priorizada)"})
    p = _run(["listar", "--estado", "xyz"], base)
    assert p.returncode == 1 and "válidos" in p.stderr
    assert _caminhos(s, "GET"), "a chamada tem de chegar na API: o verbo não guarda lista de estados"


def test_listar_esconde_as_paradas_salvo_quando_pedidas(stub):
    s, base = stub
    s.rotas[("GET", "/itens")] = _lista(_item(1), _item(2, "despriorizada"), _item(3, "priorizada"))
    ids = lambda p: [l.split("\t")[0] for l in p.stdout.splitlines()]  # noqa: E731
    assert ids(_run(["listar"], base)) == ["1", "3"]
    assert ids(_run(["listar", "--paradas"], base)) == ["1", "2", "3"]
    assert ids(_run(["listar", "--estado", "despriorizada"], base)) == ["1", "2", "3"], \
        "o estado pedido pelo nome mostra a parada (o filtro é da API; o stub devolve tudo)"


def test_listar_json_sem_paradas_tira_do_total(stub):
    s, base = stub
    s.rotas[("GET", "/itens")] = _lista(_item(1), _item(2, "despriorizada"))
    corpo = json.loads(_run(["listar", "--json"], base).stdout)
    assert [i["id"] for i in corpo["itens"]] == [1] and corpo["total"] == 1
    corpo = json.loads(_run(["listar", "--json", "--paradas"], base).stdout)
    assert [i["id"] for i in corpo["itens"]] == [1, 2] and corpo["total"] == 2


def test_listar_mantem_a_ordem_que_a_api_entrega(stub):
    s, base = stub
    s.rotas[("GET", "/itens")] = _lista(_item(7), _item(5), _item(6))
    out = _run(["listar"], base).stdout.splitlines()
    assert [l.split("\t")[0] for l in out] == ["7", "5", "6"]


# --- ler: campos novos e filhas do próprio detalhe (R19, R23) -------------------------------

def _detalhe(id, **resto):
    return {"id": id, "titulo": f"card {id}", "nivel_nome": "feature", "estado_nome": "Em execução",
            "estado_fase": "delivery", "estado_derivado": None, "cadeira": "engenharia",
            "ancestrais": [], "sign_offs": [], "descricao": "<p>corpo</p>", **resto}


def test_ler_mostra_originacao_executor_e_vinculo(stub):
    s, base = stub
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(
        10, tipo_demanda="tecnico", executor="dados",
        bloqueia=[{"id": 11, "titulo": "b", "estado": "captada"}],
        bloqueado_por=[{"id": 12, "titulo": "c", "estado": "em-execucao"}]))
    p = _run(["ler", "10"], base)
    assert p.returncode == 0, p.stderr
    assert "originação: tecnico" in p.stdout and "executor: dados" in p.stdout
    assert "bloqueia: #11 (captada)" in p.stdout
    assert "bloqueado por: #12 (em-execucao)" in p.stdout


def test_ler_sem_vinculo_nao_inventa_linha(stub):
    s, base = stub
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(10, bloqueia=[], bloqueado_por=[]))
    p = _run(["ler", "10"], base)
    assert "bloqueia:" not in p.stdout and "bloqueado por:" not in p.stdout and "travada por:" not in p.stdout


def test_ler_mostra_travada_por_somente_com_bloqueador_aberto(stub):
    s, base = stub
    # com um bloqueador entregue e um em-execucao: a linha lista só o segundo
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(
        10,
        bloqueado_por=[
            {"id": 12, "titulo": "fechado", "estado": "entregue"},
            {"id": 13, "titulo": "em andamento", "estado": "em-execucao"},
        ]))
    p = _run(["ler", "10"], base)
    assert p.returncode == 0, p.stderr
    assert "bloqueado por: #12 (entregue), #13 (em-execucao)" in p.stdout
    assert "travada por: #13 (em-execucao)" in p.stdout
    linha_travada = next(linha for linha in p.stdout.splitlines() if "travada por:" in linha)
    assert "#12" not in linha_travada

    # com todos os bloqueadores em terminal, a linha não aparece
    s.rotas[("GET", "/itens/11")] = (200, _detalhe(
        11,
        bloqueado_por=[
            {"id": 12, "titulo": "fechado", "estado": "entregue"},
            {"id": 14, "titulo": "cancelado", "estado": "cancelada"},
        ]))
    p2 = _run(["ler", "11"], base)
    assert p2.returncode == 0, p2.stderr
    assert "bloqueado por: #12 (entregue), #14 (cancelada)" in p2.stdout
    assert "travada por:" not in p2.stdout


def test_ler_imprime_as_filhas_abertas_na_ordem_da_api_e_marca_a_travada(stub):
    s, base = stub
    filhas = [
        {"id": 22, "titulo": "primeira", "estado": "em-execucao", "estado_derivado": None,
         "cadeira": "engenharia", "travada": False, "bloqueada_por": []},
        {"id": 21, "titulo": "feita", "estado": "entregue", "estado_derivado": None,
         "cadeira": "engenharia", "travada": False, "bloqueada_por": []},
        {"id": 20, "titulo": "espera", "estado": "priorizada", "estado_derivado": None,
         "cadeira": "dados", "travada": True, "bloqueada_por": [{"id": 22}]},
    ]
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(10, filhas=filhas))
    p = _run(["ler", "10"], base)
    assert p.returncode == 0, p.stderr
    bloco = [l.strip() for l in p.stdout.split("filhas (abertas):")[1].strip().splitlines()]
    assert len(bloco) == 2, "a entregue sai: filha fechada é auditoria"
    assert bloco[0].startswith("#22") and bloco[1].startswith("#20")
    assert "[travada por #22]" in bloco[1] and "[travada" not in bloco[0]


def test_ler_nao_puxa_o_board_inteiro(stub):
    """O defeito que a story fecha: `ler` baixava GET /itens e peneirava por pai."""
    s, base = stub
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(10, filhas=[]))
    assert _run(["ler", "10"], base).returncode == 0
    assert "/itens" not in _caminhos(s, "GET")


def test_ler_card_sem_filha_sai_0(stub):
    s, base = stub
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(10))
    p = _run(["ler", "10"], base)
    assert p.returncode == 0 and "filhas" not in p.stdout


def test_mover_traz_o_pai_e_as_irmas_do_detalhe_do_pai(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/30")] = (200, {"id": 30, "titulo": "story", "estado_nome": "Em execução",
                                             "estado_derivado": None, "pai": 10})
    s.rotas[("GET", "/itens/10")] = (200, _detalhe(10, filhas=[
        {"id": 31, "titulo": "irmã", "estado": "priorizada", "estado_derivado": None,
         "cadeira": "engenharia", "travada": False, "bloqueada_por": []}]))
    p = _run(["mover", "30", "em-execucao"], base)
    assert p.returncode == 0, p.stderr
    assert "abertas no pai" in p.stdout and "#31" in p.stdout
    assert "/itens" not in _caminhos(s, "GET")


def test_mover_em_execucao_item_travado_sai_0_e_repete_travada_por(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/40")] = (200, {
        "id": 40, "titulo": "story travada", "estado_nome": "Em execução",
        "estado_derivado": None, "pai": None,
        "bloqueado_por": [
            {"id": 41, "titulo": "bloqueador feito", "estado": "entregue"},
            {"id": 42, "titulo": "bloqueador aberto", "estado": "em-execucao"},
        ],
    })
    s.rotas[("GET", "/itens/40")] = (200, _detalhe(
        40,
        bloqueado_por=[
            {"id": 41, "titulo": "bloqueador feito", "estado": "entregue"},
            {"id": 42, "titulo": "bloqueador aberto", "estado": "em-execucao"},
        ],
    ))
    p = _run(["mover", "40", "em-execucao"], base)
    assert p.returncode == 0, p.stderr
    assert "item 40 → Em execução: story travada" in p.stdout
    assert "travada por: #42 (em-execucao)" in p.stdout
    linha_travada = next(linha for linha in p.stdout.splitlines() if "travada por:" in linha)
    assert "#41" not in linha_travada

    # card sem bloqueador aberto: move sem a linha travada por
    s.rotas[("PATCH", "/itens/50")] = (200, {
        "id": 50, "titulo": "story livre", "estado_nome": "Em execução",
        "estado_derivado": None, "pai": None,
        "bloqueado_por": [
            {"id": 51, "titulo": "bloqueador feito", "estado": "entregue"},
        ],
    })
    s.rotas[("GET", "/itens/50")] = (200, _detalhe(
        50,
        bloqueado_por=[
            {"id": 51, "titulo": "bloqueador feito", "estado": "entregue"},
        ],
    ))
    p2 = _run(["mover", "50", "em-execucao"], base)
    assert p2.returncode == 0, p2.stderr
    assert "item 50 → Em execução: story livre" in p2.stdout
    assert "travada por:" not in p2.stdout


# --- ordenar (R21) -----------------------------------------------------------------------

def test_ordenar_manda_o_vizinho_e_o_servidor_calcula_o_posto(stub):
    s, base = stub
    s.rotas[("POST", "/itens/5/posto")] = (200, {"id": 5, "titulo": "A", "posto": "000a8000"})
    p = _run(["ordenar", "5", "--antes-de", "7"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[-1][2] == {"antes_de": 7}
    assert "antes de #7" in p.stdout
    p = _run(["ordenar", "5", "--depois-de", "#8"], base)
    assert s.chamadas[-1][2] == {"depois_de": 8} and "depois de #8" in p.stdout


def test_ordenar_sem_lado_ou_com_os_dois_recusa_antes_de_chamar(stub):
    s, base = stub
    assert _run(["ordenar", "5"], base).returncode == 2
    assert _run(["ordenar", "5", "--antes-de", "7", "--depois-de", "8"], base).returncode == 2
    assert _run(["ordenar", "5", "--antes-de", "abc"], base).returncode == 2
    assert not s.chamadas


# --- bloquear e desbloquear (R23) ----------------------------------------------------------

def test_bloquear_declara_o_vinculo_e_mostra_os_dois_lados(stub):
    s, base = stub
    s.rotas[("POST", "/itens/5/bloqueia")] = (200, {"id": 5, "bloqueia": [{"id": 8, "titulo": "b", "estado": "captada"}],
                                                    "bloqueado_por": []})
    p = _run(["bloquear", "5", "8"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[-1][2] == {"bloqueado": 8}
    assert "#5 bloqueia: #8" in p.stdout and "#5 bloqueado por: ninguém" in p.stdout


def test_bloquear_que_fecharia_ciclo_sai_1_com_o_caminho(stub):
    s, base = stub
    s.rotas[("POST", "/itens/8/bloqueia")] = (409, {"erro": "o vínculo fecharia um ciclo", "restricao": "bloqueio_sem_ciclo",
                                                    "caminho": [8, 5, 8]})
    p = _run(["bloquear", "8", "5"], base)
    assert p.returncode == 1
    assert "fecharia um ciclo" in p.stderr and "caminho: #8 → #5 → #8" in p.stderr


def test_desbloquear_retira_o_vinculo(stub):
    s, base = stub
    s.rotas[("DELETE", "/itens/5/bloqueia/8")] = (200, {"id": 5, "bloqueia": [], "bloqueado_por": []})
    p = _run(["desbloquear", "5", "8"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[-1][:2] == ("DELETE", "/itens/5/bloqueia/8")
    assert "#5 bloqueia: ninguém" in p.stdout


def test_desbloquear_o_que_nao_existe_sai_1(stub):
    s, base = stub
    s.rotas[("DELETE", "/itens/5/bloqueia/8")] = (404, {"erro": "o item 5 não bloqueia o item 8"})
    p = _run(["desbloquear", "5", "8"], base)
    assert p.returncode == 1 and "não bloqueia" in p.stderr


# --- mover para despriorizada: a lista de motivos é da API (R24) -------------------------------

def _despriorizar(corpo):
    if corpo.get("motivo") in {m["codigo"] for m in MOTIVOS}:
        return 200, {"id": 6, "titulo": "story", "estado_nome": "Despriorizada", "estado_derivado": None, "pai": None}
    return 400, {"erro": "despriorizar pede um motivo da lista", "motivos": MOTIVOS}


def test_despriorizar_sem_motivo_imprime_a_lista_da_recusa(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/6")] = _despriorizar
    p = _run(["mover", "6", "despriorizada"], base)
    assert p.returncode == 1
    assert "despriorizar pede um motivo da lista" in p.stderr
    codigos = [l.split("\t")[0].strip() for l in p.stderr.splitlines() if l.startswith("  ")]
    assert codigos == [m["codigo"] for m in MOTIVOS], p.stderr
    assert "Outra aposta passou na frente" in p.stderr
    assert "motivo" not in s.chamadas[-1][2], "o verbo não decide: sem --motivo, manda sem"


def test_despriorizar_com_codigo_da_lista_passa(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/6")] = _despriorizar
    p = _run(["mover", "6", "despriorizada", "--motivo", "outra-aposta"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[-1][2] == {"estado": "despriorizada", "motivo": "outra-aposta"}
    p = _run(["mover", "6", "despriorizada", "--motivo", "qualquer coisa"], base)
    assert p.returncode == 1 and "sem-tokens" in p.stderr


# --- carteira (R25) ------------------------------------------------------------------------

# O balde é dado do rastreador (R26, #3551): a linha da carteira conta as saídas por `GET /balde`.
BALDE = (200, {"situacao": "saidas", "stack": None, "total": 3, "linhas": [
    {"numero": n, "saida_jeito": "cancelada", "saida_ancora": "x", "saida_em": quando}
    for n, quando in [(2, "2026-09-20 00:00:00+00:00"), (3, "2026-10-13 00:00:00+00:00"),
                      (4, "2026-10-14 00:00:00+00:00")]]})


def _carteira_itens():
    def e(id, tipo, quando, **r):
        return _item(id, "entregue", **{"tipo_demanda": tipo, "origem": "planejado",
                                        "ultimo_movimento": quando, **r})

    return _lista(
        e(1, "negocio", "2026-10-13 19:22:01.1+00:00"),
        e(2, "negocio", "2026-10-11 10:00:00+00:00"),               # antes da segunda: fora
        e(3, "negocio", "2026-10-13 09:00:00+00:00", origem="prova"),   # prova: fora
        e(4, "tecnico", "2026-10-12 00:00:01+00:00"),
        e(5, "tecnico", "2026-10-14 08:00:00+00:00"),
        e(6, "incidente", "2026-10-14 09:00:00+00:00"),
        _item(7, "cancelada", tipo_demanda="negocio", origem="planejado", ultimo_movimento="2026-10-13 09:00:00+00:00"),
        _item(8, "despriorizada", pai=100, pai_estado="priorizada", ultimo_movimento="2026-10-04 12:00:00+00:00"),
        _item(9, "despriorizada", pai=None, ultimo_movimento="2026-10-13 12:00:00+00:00"),
        _item(10, "despriorizada", pai=101, pai_estado="captada", ultimo_movimento="2026-09-30 12:00:00+00:00"),
    )


def _rotas_da_carteira(s):
    s.rotas[("GET", "/itens")] = _carteira_itens()
    s.rotas[("GET", "/balde")] = BALDE


def _linhas(p):
    return [l.split("\t") for l in p.stdout.splitlines()]


def test_carteira_fatia_por_originacao_balde_ao_lado_e_paradas_com_idade(stub):
    s, base = stub
    _rotas_da_carteira(s)
    p = _run(["carteira"], base, TAREFAS_HOJE="2026-10-14")   # quarta: a semana começa em 12/10
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines()[0].startswith("carteira desde 2026-10-12")
    por_nome = {l[0].strip(): l[1] for l in _linhas(p) if len(l) > 1}
    assert por_nome["negocio"] == "1" and por_nome["tecnico"] == "2" and por_nome["incidente"] == "1"
    assert por_nome["balde"].startswith("2 saídas desde 2026-10-12"), "só as duas saídas de 13 e 14/10"
    assert "ao lado" in por_nome["balde"]
    # a fatia são três linhas, e a do balde vem ao lado, sem somar
    fatia = [n for n in por_nome if n in ("negocio", "tecnico", "incidente")]
    assert fatia == ["negocio", "tecnico", "incidente"]
    # paradas, separadas, com a idade em dias
    assert "paradas (despriorizada): 3" in p.stdout
    assert por_nome["sob pai apostado"] == "1" and por_nome["sem pai (autônomas)"] == "1"
    assert por_nome["sob pai ainda não apostado"] == "1"
    linhas_parada = {l[0].strip(): l[1:] for l in _linhas(p) if l[0].strip().startswith("#")}
    assert linhas_parada["#8"][0] == "10d" and linhas_parada["#9"][0] == "1d" and linhas_parada["#10"][0] == "14d"


def test_carteira_desde_muda_a_janela(stub):
    s, base = stub
    _rotas_da_carteira(s)
    p = _run(["carteira", "--desde", "2026-09-01"], base, TAREFAS_HOJE="2026-10-14")
    por_nome = {l[0].strip(): l[1] for l in _linhas(p) if len(l) > 1}
    assert por_nome["negocio"] == "2" and por_nome["balde"].startswith("3 saídas desde 2026-09-01")


@pytest.mark.parametrize("hoje,segunda", [("2026-10-12", "2026-10-12"), ("2026-10-18", "2026-10-12"), ("2026-10-19", "2026-10-19")])
def test_carteira_por_padrao_comeca_na_segunda_da_semana(stub, hoje, segunda):
    s, base = stub
    _rotas_da_carteira(s)
    p = _run(["carteira"], base, TAREFAS_HOJE=hoje)
    assert p.stdout.splitlines()[0].startswith(f"carteira desde {segunda}")


def test_carteira_busca_so_story_e_task_e_nao_soma_o_balde(stub):
    s, base = stub
    _rotas_da_carteira(s)
    _run(["carteira"], base, TAREFAS_HOJE="2026-10-14")
    q = _caminhos(s, "GET")
    assert "/itens?nivel=2&nivel=3" in q
    assert not any(c == "/itens" for c in q)


def test_carteira_balde_ilegivel_nao_derruba_a_fatia(stub):
    s, base = stub
    s.rotas[("GET", "/itens")] = _carteira_itens()
    s.rotas[("GET", "/balde")] = (500, {"erro": "balde fora do ar"})
    p = _run(["carteira"], base, TAREFAS_HOJE="2026-10-14")
    assert p.returncode == 0, p.stderr
    assert "ilegível" in p.stdout and "negocio" in p.stdout


def test_carteira_data_ruim_e_opcao_desconhecida_sao_uso(stub):
    s, base = stub
    assert _run(["carteira", "--desde", "ontem"], base).returncode == 2
    assert _run(["carteira", "--semana"], base).returncode == 2


# --- uso ---------------------------------------------------------------------------------

def test_sem_argumento_o_uso_lista_os_atos_e_flags_novos():
    p = _run([])
    assert p.returncode == 2
    for trecho in ("tarefas ordenar", "tarefas bloquear", "tarefas desbloquear", "tarefas carteira",
                   "--originacao", "--executor", "--paradas", "--antes-de", "--depois-de"):
        assert trecho in p.stderr, trecho


def test_cabecalho_declara_face_rotulo_e_volta_dos_atos_novos():
    texto = BIN.read_text(encoding="utf-8")
    for ato in ("ordenar", "bloquear", "desbloquear", "carteira"):
        for chave in ("face", "rotulo", "volta"):
            assert f"# {chave}: {ato}=" in texto, (chave, ato)
    atos = next(l for l in texto.splitlines() if l.startswith("# atos:"))
    for ato in ("ordenar", "bloquear", "desbloquear", "carteira"):
        assert ato in atos
