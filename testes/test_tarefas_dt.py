"""Verbo tarefas dt: o balde de débito técnico como dado do rastreador (card #3552; R11, R12, R27 e
R28 da spec tarefas).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele) que imita as rotas de
`/api/balde` do platafirma-rastreador, e o catálogo de stacks é um verbo `acervo` de mentira
(PF_ACERVO_BIN): o teste prova o que o VERBO faz — o que exige antes de chamar, o corpo que envia,
a tabela que imprime —, e não a regra de dado, que tem self-check no rastreador (api/balde.py).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"

SAIDA_EM = "2026-10-14 20:00:00+00:00"


def _linha(numero, **campos):
    """Uma linha do balde como a API a devolve; `saida=(jeito, ancora)` a dá por saída."""
    jeito, ancora = campos.pop("saida", (None, None))
    return {
        "numero": numero, "texto": f"defeito {numero}", "raio": None, "esperado": None,
        "stack": "harness", "medido_em": "2026-10-01", "onde": "onde mediu", "cadeira": "engenharia",
        "admitido_em": "2026-10-01 00:00:00+00:00", "saida_jeito": jeito, "saida_ancora": ancora,
        "saida_em": SAIDA_EM if jeito else None, "saida_por": None, "idade_dias": 3,
        **campos,
    }


class _Balde(BaseHTTPRequestHandler):
    linhas: ClassVar[list] = []
    indicadores: ClassVar[dict] = {}
    pedidos: ClassVar[list] = []  # (método, caminho, corpo, sujeito)
    recusa_post: ClassVar[tuple | None] = None  # (status, corpo) para o POST /balde

    def log_message(self, *a):  # silencioso
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _registra(self, corpo=None):
        type(self).pedidos.append(
            (self.command, self.path, corpo, self.headers.get("x-auth-request-preferred-username")))

    def do_GET(self):
        self._registra()
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path == "/balde/indicadores":
            return self._json(self.indicadores)
        if url.path == "/balde":
            situacao = q.get("situacao", ["abertas"])[0]
            stack = q.get("stack", [None])[0]
            achadas = [x for x in self.linhas
                       if (stack is None or x["stack"] == stack)
                       and (situacao == "todas"
                            or (x["saida_jeito"] is None) == (situacao == "abertas"))]
            # a mais antiga primeiro (R27): a API ordena por medido_em e número
            achadas.sort(key=lambda x: (-x["idade_dias"], x["numero"]))
            return self._json({"situacao": situacao, "stack": stack, "linhas": achadas,
                               "total": len(achadas)})
        self._json({"erro": "rota"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        self._registra(corpo)
        if self.path == "/balde":
            if self.recusa_post:
                return self._json(self.recusa_post[1], self.recusa_post[0])
            numero = max((x["numero"] for x in self.linhas), default=0) + 1
            linha = {**_linha(numero), **corpo, "numero": numero, "cadeira": self.headers.get(
                "x-auth-request-preferred-username")}
            type(self).linhas.append(linha)
            return self._json(linha, 201)
        m = re.match(r"^/balde/(\d+)/saida$", self.path)
        if m:
            numero = int(m.group(1))
            alvo = next((x for x in self.linhas if x["numero"] == numero), None)
            if alvo is None:
                return self._json({"erro": f"a linha {numero} do balde não existe"}, 404)
            if alvo["saida_jeito"]:
                return self._json({"erro": f"a linha {numero} já saiu como {alvo['saida_jeito']} "
                                           f"em {alvo['saida_em']}", "linha": alvo}, 409)
            alvo.update(saida_jeito=corpo["jeito"], saida_ancora=corpo["ancora"], saida_em=SAIDA_EM)
            return self._json(alvo)
        self._json({"erro": "rota"}, 404)


@pytest.fixture()
def balde():
    _Balde.linhas, _Balde.pedidos, _Balde.indicadores, _Balde.recusa_post = [], [], {}, None
    srv = HTTPServer(("127.0.0.1", 0), _Balde)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield _Balde, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture()
def acervo(tmp_path):
    """O verbo `acervo` de mentira: `acervo stack ver --json` devolve o catálogo, ou falha."""
    def faz(stacks=("harness", "rastreador"), rc=0):
        p = tmp_path / "acervo"
        corpo = json.dumps([{"slug": s} for s in stacks])
        p.write_text("#!/bin/sh\n" + (f"echo '{corpo}'\n" if rc == 0 else "") + f"exit {rc}\n")
        p.chmod(0o755)
        return str(p)
    return faz


def _run(args, base="http://127.0.0.1:9", acervo_bin="/nao/existe"):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia", PF_ACERVO_BIN=acervo_bin)
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env,
                          timeout=60, check=False)


ADMITE = ["dt", "admitir", "tarefas dt recusa x", "--medido-em", "2026-10-14",
          "--evidencia", "tarefas dt admitir, exit 1", "--raio", "platafirma-harness@bin/tarefas",
          "--esperado", "sai 0 com o débito admitido", "--stack", "harness"]


def _sem(args, flag):
    i = args.index(flag)
    return args[:i] + args[i + 2:]


def _linhas_da_tabela(stdout):
    return [linha.split("\t") for linha in stdout.splitlines()[1:]]


# --- admitir (R11) --------------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["--medido-em", "--evidencia", "--raio", "--esperado", "--stack"])
def test_admitir_sem_cada_campo_sai_2_e_nao_chama_a_api(balde, acervo, flag):
    s, base = balde
    p = _run(_sem(ADMITE, flag), base, acervo())
    assert p.returncode == 2, p.stderr
    assert "recusado" in p.stderr and not s.pedidos


def test_admitir_sem_texto_e_uso():
    assert _run(["dt", "admitir"]).returncode == 2


def test_admitir_stack_inventada_sai_4_com_a_lista_do_catalogo(balde, acervo):
    s, base = balde
    args = _sem(ADMITE, "--stack") + ["--stack", "inventada"]
    p = _run(args, base, acervo())
    assert p.returncode == 4, p.stderr
    assert "`inventada`" in p.stderr and "harness, rastreador" in p.stderr
    assert not s.pedidos


def test_admitir_catalogo_fora_do_ar_sai_5_e_nao_diz_que_a_stack_nao_existe(balde, acervo):
    s, base = balde
    p = _run(ADMITE, base, acervo(rc=1))
    assert p.returncode == 5, p.stderr
    assert "fora do ar" in p.stderr and "não está no catálogo" not in p.stderr
    assert not s.pedidos
    p = _run(ADMITE, base, "/nao/existe")
    assert p.returncode == 5 and "ausente" in p.stderr


def test_admitir_completo_grava_os_seis_campos_com_o_sujeito_da_cadeira(balde, acervo):
    s, base = balde
    s.linhas = [_linha(280)]
    p = _run(ADMITE, base, acervo())
    assert p.returncode == 0, p.stderr
    (met, caminho, corpo, sujeito), = s.pedidos
    assert (met, caminho, sujeito) == ("POST", "/balde", "engenharia")
    assert corpo == {
        "texto": "tarefas dt recusa x", "raio": ["platafirma-harness@bin/tarefas"],
        "esperado": "sai 0 com o débito admitido", "stack": "harness", "medido_em": "2026-10-14",
        "onde": "tarefas dt admitir, exit 1"}
    assert "débito 281 admitido" in p.stdout and "stack harness" in p.stdout


def test_admitir_aceita_mais_de_um_raio_e_o_verbo_e_a_solucao_no_texto(balde, acervo):
    s, base = balde
    args = ADMITE + ["--raio", "platafirma-harness@testes/test_tarefas_dt.py", "--verbo", "tarefas",
                     "--solucao", "ler da API"]
    p = _run(args, base, acervo())
    assert p.returncode == 0, p.stderr
    corpo = s.pedidos[0][2]
    assert corpo["raio"] == ["platafirma-harness@bin/tarefas",
                             "platafirma-harness@testes/test_tarefas_dt.py"]
    assert corpo["texto"] == "tarefas — tarefas dt recusa x · solução: ler da API"


def test_admitir_cadeira_deprecado_avisa_e_nao_vai_ao_corpo(balde, acervo):
    s, base = balde
    p = _run(ADMITE + ["--cadeira", "ti"], base, acervo())
    assert p.returncode == 0, p.stderr
    assert "deprecado" in p.stderr and "cadeira" not in s.pedidos[0][2]


def test_admitir_recusa_da_api_sai_1_com_a_causa_dela(balde, acervo):
    s, base = balde
    s.recusa_post = (400, {"erro": "`raio` tem de ser `repo@caminho`, sem espaço: `x y`"})
    p = _run(ADMITE, base, acervo())
    assert p.returncode == 1 and "repo@caminho" in p.stderr


# --- listar e vencidos (R27, R26) -----------------------------------------------------------


def test_listar_mostra_stack_e_idade_e_guarda_a_ordem_da_api(balde):
    s, base = balde
    s.linhas = [_linha(1, idade_dias=3), _linha(2, stack="rastreador", idade_dias=26),
                _linha(3, idade_dias=12)]
    p = _run(["dt", "listar"], base)
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines()[0] == "n\tidade\tstack\tdébito"
    assert [linha[:3] for linha in _linhas_da_tabela(p.stdout)] == [
        ["2", "26d", "rastreador"], ["3", "12d", "harness"], ["1", "3d", "harness"]]
    assert s.pedidos[0][1] == "/balde?situacao=abertas"


def test_listar_por_stack_pede_so_a_stack(balde):
    s, base = balde
    s.linhas = [_linha(1), _linha(2, stack="rastreador")]
    p = _run(["dt", "listar", "--stack", "rastreador"], base)
    assert p.returncode == 0, p.stderr
    assert [linha[0] for linha in _linhas_da_tabela(p.stdout)] == ["2"]
    assert s.pedidos[0][1] == "/balde?situacao=abertas&stack=rastreador"


def test_listar_leva_raio_esperado_e_onde_e_o_curto_leva_so_o_texto(balde):
    s, base = balde
    s.linhas = [_linha(7, texto="x" * 300, raio=["platafirma-harness@bin/tarefas", "a@b"],
                       esperado="sai 0", onde="repro\ncom quebra")]
    cheia = _run(["dt", "listar"], base).stdout.splitlines()[1]
    assert cheia.endswith(" · Raio: platafirma-harness@bin/tarefas, a@b · Esperado: sai 0"
                          " · Onde: repro com quebra"), cheia
    curta = _run(["dt", "listar", "--curto"], base).stdout.splitlines()[1].split("\t")[3]
    assert curta == "x" * 199 + "…"


def test_listar_nao_repete_o_que_o_texto_ja_traz(balde):
    s, base = balde
    texto = "a tela cai · Raio: platafirma-harness@bin/tarefas · Esperado: sai 0 · Onde: leitura de 18/10"
    s.linhas = [_linha(8, texto=texto, raio=["platafirma-harness@bin/tarefas"], esperado="sai 0",
                       onde="leitura de 18/10")]
    p = _run(["dt", "listar"], base)
    assert p.returncode == 0, p.stderr
    (so,) = _linhas_da_tabela(p.stdout)
    assert so[3] == texto, so[3]
    assert p.stdout.count("Raio:") == 1 and p.stdout.count("Esperado:") == 1


def test_listar_acrescenta_so_o_campo_que_o_texto_nao_traz(balde):
    s, base = balde
    s.linhas = [_linha(9, texto="defeito · Raio: a@b · Esperado: sai 0",
                       raio=["a@b", "c@d"], esperado="sai 0", onde="repro")]
    (so,) = _linhas_da_tabela(_run(["dt", "listar"], base).stdout)
    assert so[3] == "defeito · Raio: a@b · Esperado: sai 0 · Raio: c@d · Onde: repro", so[3]


def test_listar_desde_corta_pelo_numero(balde):
    s, base = balde
    s.linhas = [_linha(99), _linha(100), _linha(281)]
    p = _run(["dt", "listar", "--desde", "100"], base)
    assert [linha[0] for linha in _linhas_da_tabela(p.stdout)] == ["100", "281"]


def test_listar_saidas_traz_o_jeito_e_a_ancora(balde):
    s, base = balde
    s.linhas = [_linha(1), _linha(2, saida=("resolvida", "ab12cd3"))]
    p = _run(["dt", "listar", "--situacao", "saidas"], base)
    assert p.returncode == 0, p.stderr
    (so,) = _linhas_da_tabela(p.stdout)
    assert so[0] == "2" and so[3].endswith("· saiu resolvida: ab12cd3")


def test_listar_vazio_diz_qual_recorte_esta_vazio(balde):
    _, base = balde
    p = _run(["dt", "listar", "--stack", "rag"], base)
    assert p.returncode == 0 and p.stdout.strip() == "(balde vazio: nenhuma linha aberta na stack rag)"


@pytest.mark.parametrize("args", [["--stack", "Rastreador Tela"], ["--situacao", "mortas"],
                                  ["--desde", "x"], ["--curta"]])
def test_listar_opcao_ruim_sai_2_sem_chamar_a_api(balde, args):
    s, base = balde
    assert _run(["dt", "listar"] + args, base).returncode == 2 and not s.pedidos


def test_listar_com_o_rastreador_fora_diz_que_a_fonte_nao_respondeu():
    p = _run(["dt", "listar"])
    assert p.returncode == 1 and "falha ao falar com o rastreador" in p.stderr


def test_vencidos_so_acima_de_30_dias(balde):
    s, base = balde
    s.linhas = [_linha(1, idade_dias=31), _linha(2, idade_dias=30), _linha(3, idade_dias=5)]
    p = _run(["dt", "vencidos"], base)
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines()[0].startswith("PAUTA DA REVISÃO")
    assert [linha[0] for linha in _linhas_da_tabela(p.stdout)[1:]] == ["1"]
    s.linhas = [_linha(2, idade_dias=30)]
    assert _run(["dt", "vencidos"], base).stdout.startswith("pauta vazia")


# --- matar (R12) ----------------------------------------------------------------------------


@pytest.mark.parametrize("args", [["--como", "resolvida"], ["--como", "cancelada"],
                                  ["--como", "englobada"], [], ["--como", "pendente"],
                                  ["--como", "cancelada", "--commit", "ab12cd3"]])
def test_matar_cada_jeito_sem_a_ancora_sai_2_e_nao_chama_a_api(balde, args):
    s, base = balde
    s.linhas = [_linha(5)]
    p = _run(["dt", "matar", "5"] + args, base)
    assert p.returncode == 2, p.stderr
    assert not s.pedidos


def test_matar_sem_numero_e_uso():
    assert _run(["dt", "matar", "--como", "cancelada", "--motivo", "x"]).returncode == 2


@pytest.mark.parametrize("args,corpo", [
    (["--como", "resolvida", "--commit", "ab12cd3"], {"jeito": "resolvida", "ancora": "ab12cd3"}),
    (["--como", "cancelada", "--motivo", "o objeto saiu do ar"],
     {"jeito": "cancelada", "ancora": "o objeto saiu do ar"}),
    (["--como", "englobada", "--card", "#3551"], {"jeito": "englobada", "ancora": "3551"}),
])
def test_matar_manda_o_jeito_e_a_ancora_e_diz_como_saiu(balde, args, corpo):
    s, base = balde
    s.linhas = [_linha(5)]
    p = _run(["dt", "matar", "5"] + args, base)
    assert p.returncode == 0, p.stderr
    (met, caminho, enviado, sujeito), = s.pedidos
    assert (met, caminho, enviado, sujeito) == ("POST", "/balde/5/saida", corpo, "engenharia")
    assert p.stdout.strip() == (f"débito 5 saiu do balde: {corpo['jeito']} em 2026-10-14: "
                                f"{corpo['ancora']}")


def test_matar_segunda_saida_sai_1_e_diz_como_a_linha_ja_saiu(balde):
    s, base = balde
    s.linhas = [_linha(5, saida=("cancelada", "x"))]
    p = _run(["dt", "matar", "5", "--como", "cancelada", "--motivo", "y"], base)
    assert p.returncode == 1 and "já saiu como cancelada" in p.stderr


def test_matar_linha_que_nao_existe_sai_1(balde):
    _, base = balde
    p = _run(["dt", "matar", "99", "--como", "cancelada", "--motivo", "y"], base)
    assert p.returncode == 1 and "não existe" in p.stderr


@pytest.mark.parametrize("args,corpo", [
    (["--porta", "obsoleto", "--ancora", "consertado: 35cb504, no ar"],
     {"jeito": "resolvida", "ancora": "35cb504"}),
    (["--porta", "obsoleto", "--ancora", "o objeto saiu do ar"],
     {"jeito": "cancelada", "ancora": "o objeto saiu do ar"}),
    (["--porta", "decisao", "--ancora", "dono, 14/10"], {"jeito": "cancelada", "ancora": "dono, 14/10"}),
    (["--porta", "card", "--card", "3551"], {"jeito": "englobada", "ancora": "3551"}),
    (["--porta", "englobado", "--card", "#12"], {"jeito": "englobada", "ancora": "12"}),
])
def test_matar_porta_antiga_vira_o_jeito_novo_com_aviso(balde, args, corpo):
    s, base = balde
    s.linhas = [_linha(5)]
    p = _run(["dt", "matar", "5"] + args, base)
    assert p.returncode == 0, p.stderr
    assert "deprecado" in p.stderr and s.pedidos[0][2] == corpo


@pytest.mark.parametrize("args", [
    ["--porta", "obsoleto"], ["--porta", "decisao"], ["--porta", "englobado"], ["--porta", "x"],
    ["--porta", "card", "--card", "1", "--como", "englobada"]])
def test_matar_porta_antiga_sem_ancora_ou_misturada_sai_2(balde, args):
    s, base = balde
    s.linhas = [_linha(5)]
    assert _run(["dt", "matar", "5"] + args, base).returncode == 2 and not s.pedidos


# --- indicadores (R28) ----------------------------------------------------------------------

INDICADORES = {
    "abertos": 4,
    "por_stack": [
        {"stack": "harness", "abertos": 3, "mais_velho_numero": 12, "mais_velho_medido_em": "2026-09-18",
         "mais_velho_dias": 26},
        {"stack": "rastreador", "abertos": 1, "mais_velho_numero": 126,
         "mais_velho_medido_em": "2026-10-14", "mais_velho_dias": 0},
    ],
    "semana": {"dias": 7, "desde": "d", "ate": "a", "entradas": 57,
               "saidas": {"resolvida": 23, "cancelada": 19, "englobada": 12}, "saidas_total": 54},
}


def test_indicadores_uma_linha_por_stack_e_a_linha_da_semana(balde):
    s, base = balde
    s.indicadores = INDICADORES
    p = _run(["dt", "indicadores"], base)
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines() == [
        "stack\tabertos\tmais velho",
        "harness\t3\t26d (#12)",
        "rastreador\t1\t0d (#126)",
        "semana (7 dias): 57 entradas, 54 saídas (resolvida 23, cancelada 19, englobada 12)"]
    assert s.pedidos[0][1] == "/balde/indicadores"


def test_indicadores_dias_vai_na_consulta_e_balde_vazio_so_traz_a_semana(balde):
    s, base = balde
    s.indicadores = {"abertos": 0, "por_stack": [], "semana": {
        "dias": 30, "desde": "d", "ate": "a", "entradas": 0, "saidas": {}, "saidas_total": 0}}
    p = _run(["dt", "indicadores", "--dias", "30"], base)
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines()[1] == "semana (30 dias): 0 entradas, 0 saídas"
    assert s.pedidos[0][1] == "/balde/indicadores?dias=30"


def test_indicadores_dias_ruim_sai_2(balde):
    s, base = balde
    assert _run(["dt", "indicadores", "--dias", "sete"], base).returncode == 2 and not s.pedidos


def test_dt_sem_sub_e_uso_e_lista_os_atos():
    p = _run(["dt"])
    assert p.returncode == 2
    for ato in ("listar", "admitir", "matar", "vencidos", "indicadores"):
        assert f"tarefas dt {ato}" in p.stderr
