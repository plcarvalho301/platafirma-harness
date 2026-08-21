"""Contrato do adaptador de board (#2300) — e a conformidade contra o rastreador vivo.

Dois níveis, como em `test_contrato_adaptadores.py`:

- **contrato** — cliente falso, roda sempre. Julga o que o adaptador PRODUZ.
- **conformidade** — bate com o verbo humano (`tarefas`) sobre o mesmo estado (§5).
  PULADO com motivo quando o rastreador não está no ar.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error

import pytest

from recuperacao.adaptadores import AdaptadorBoard, monta_envelope
from recuperacao.adaptadores.board import BASE
from recuperacao.envelope import Causa, Cobertura, Fonte, VersaoTipo

# ------------------------------------------------------------------ cliente falso

ITENS = [
    {"id": 2300, "titulo": "Adaptador de board", "estado": "em-execucao",
     "cadeira": "claudinho-IA", "nivel": 2, "pai": 2292},
    {"id": 2308, "titulo": "Chave por fonte e rec:stat", "estado": "priorizada",
     "cadeira": "claudinho-IA", "nivel": 2, "pai": 2293},
    {"id": 2307, "titulo": "GET /api/carimbo no rastreador", "estado": "entregue",
     "cadeira": "claudinho-TI", "nivel": 2, "pai": 2293},
]


class BoardFalso:
    """Só as quatro rotas que o adaptador chama. Guarda as URLs para o teste julgar."""

    def __init__(self, carimbo=203, itens=None, eventos=None, sem_evento=()) -> None:
        self.carimbo, self.itens = carimbo, list(itens if itens is not None else ITENS)
        self.eventos = eventos or {2300: [73, 189], 2308: [155], 2307: [201, 202]}
        self.sem_evento = set(sem_evento)
        self.visitou: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.visitou.append(url)
        rota = url.split("/api/", 1)[-1]
        if rota.startswith("carimbo"):
            return json.dumps({"carimbo": self.carimbo, "itens": len(self.itens)}).encode()
        if rota.endswith("/eventos"):
            i = int(rota.split("/")[1])
            if i in self.sem_evento:
                return json.dumps({"eventos": []}).encode()
            return json.dumps({"eventos": [{"id": e, "item": i} for e in self.eventos.get(i, [])]}).encode()
        if rota.startswith("itens?") or rota == "itens":
            campos = [c for c in ITENS[0] if f"campos=" in rota]  # noqa: F841 — ver teste da projeção
            return json.dumps({"itens": self.itens, "estados": [], "total": len(self.itens)}).encode()
        if rota.startswith("itens/"):
            i = int(rota.split("/")[1])
            achado = [x for x in self.itens if x["id"] == i]
            if not achado:
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            return json.dumps(achado[0]).encode()
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)


def adaptador(**kw) -> tuple[AdaptadorBoard, BoardFalso]:
    falso = BoardFalso(**kw)
    return AdaptadorBoard(abre_url=falso, quem="claudinho-IA"), falso


# ================================================================= 1. procedência


def test_board_produz_procedencia_completa():
    a, _ = adaptador()
    r = a.busca("item:2300")
    assert len(r.itens) == 1
    p = r.itens[0].procedencia
    assert p.fonte is Fonte.BOARD
    assert p.chave == "item:2300"
    assert p.versao.tipo is VersaoTipo.SEQ
    assert p.versao.valor == "189", "versão = max(evento.id) DO ITEM (§4), não do board"


def test_board_aceita_as_tres_formas_do_alvo():
    a, _ = adaptador()
    for alvo in ("item:2300", "#2300", "2300"):
        assert a.busca(alvo).itens[0].procedencia.chave == "item:2300"


def test_board_item_sem_ledger_declara_a_ancora_global():
    """O ledger começou em #2307: item mais velho não tem linha. Declarar é o certo —
    timestamp está proibido (§5) e omitir violaria a invariante 1."""
    a, _ = adaptador(sem_evento={2300})
    assert a.busca("2300").itens[0].procedencia.versao.valor == "0@203"


# ================================================================= 2. carimbo


def test_board_carimbo_compoe_evento_e_contagem():
    a, _ = adaptador()
    assert a.busca("item:2300").linha.carimbo == "203/3"


def test_board_carimbo_nulo_nao_vira_carimbo_vazio():
    """`evento` vazio devolve `null` (medido por TI em 20/08). Vazio reprovaria no
    contrato de `Versao`; 0 é o valor honesto de ledger que ainda não andou."""
    a, _ = adaptador(carimbo=None)
    assert a.busca("item:2300").linha.carimbo == "0/3"


# ================================================================= 3. projeção


def test_board_pede_a_projecao_e_nunca_o_item_inteiro():
    a, falso = adaptador()
    a.busca("adaptador")
    listagem = [u for u in falso.visitou if "/itens?" in u]
    assert listagem, "a listagem tem de passar pela rota de itens"
    assert "campos=id%2Ctitulo%2Cestado%2Ccadeira%2Cnivel%2Cpai" in listagem[0]


def test_board_serve_ref_e_nunca_conteudo():
    """§5: `o resto vai por ref, nunca por conteudo` — vale para todo valor de `texto`."""
    a, _ = adaptador()
    for texto in ("secao", "trecho", "nenhum"):
        item = a.busca("item:2300", texto=texto).itens[0]
        assert item.conteudo is None
        assert item.ref and item.ref.startswith("#2300 — Adaptador de board")


def test_board_ref_traz_os_seis_campos():
    a, _ = adaptador()
    ref = a.busca("item:2300").itens[0].ref
    for pedaco in ("#2300", "Adaptador de board", "em-execucao", "claudinho-IA", "pai #2292"):
        assert pedaco in ref


# ================================================================= 4. filtro e recorte


def test_board_repassa_eixo_de_linha_para_a_fonte():
    a, falso = adaptador()
    a.busca("", filtros={"cadeira": "claudinho-IA", "estado": "priorizada"})
    url = [u for u in falso.visitou if "/itens?" in u][0]
    assert "cadeira=claudinho-IA" in url and "estado=priorizada" in url


def test_board_ignora_filtro_que_a_api_recusaria():
    """`?q=` devolve 400 nomeando o eixo (medido). Mandar assim mesmo derrubaria a fonte
    inteira por causa de um filtro que o adaptador sabe recortar sozinho."""
    a, falso = adaptador()
    r = a.busca("chave", filtros={"q": "chave"})
    assert "q=" not in [u for u in falso.visitou if "/itens?" in u][0]
    assert [i.procedencia.chave for i in r.itens] == ["item:2308"]


def test_board_recorta_por_termo_no_titulo():
    a, _ = adaptador()
    r = a.busca("carimbo rastreador")
    assert [i.procedencia.chave for i in r.itens] == ["item:2307"]


def test_board_respeita_k():
    a, _ = adaptador()
    assert len(a.busca("", k=2).itens) == 2


# ================================================================= 5. falha declarada


def test_board_id_inexistente_e_vazia_e_nao_falha():
    a, _ = adaptador()
    r = a.busca("item:999999")
    assert r.itens == []
    assert r.linha.cobertura is Cobertura.VAZIA
    assert r.linha.causa is None


def test_board_fora_do_ar_vira_linha_e_nao_excecao():
    def caiu(url):
        raise urllib.error.URLError("conexão recusada")

    r = AdaptadorBoard(abre_url=caiu).busca_declarada("item:2300")
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert r.linha.causa is Causa.SEM_ROTA
    assert r.itens == []


def test_board_sem_gold_nunca_diz_coberta():
    a, _ = adaptador()
    assert a.busca("item:2300").linha.cobertura is Cobertura.NAO_CALIBRADA


def test_board_entra_no_envelope_com_as_outras():
    a, _ = adaptador()
    env = monta_envelope([a.busca_declarada("item:2300")])
    assert [linha.fonte for linha in env.linhas] == [Fonte.BOARD]


# ================================================================= 6. identidade


def test_board_manda_o_header_de_identidade_quando_ha_cadeira():
    """§5: `HTTP do rastreador + header de identidade`. Sem `PF_CADEIRA`, leitura anônima
    continua legítima — o rastreador não tem auth por desenho."""
    import urllib.request

    vistos = {}

    def espia(req_url, timeout=None):  # pragma: no cover — substituído abaixo
        raise AssertionError

    a = AdaptadorBoard(quem="claudinho-IA")
    original = urllib.request.urlopen

    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"carimbo": 1, "itens": 1}).encode()

    def falso_urlopen(req, timeout=None):
        vistos.update(req.headers)
        return Resposta()

    urllib.request.urlopen = falso_urlopen
    try:
        a._carimbo()
    finally:
        urllib.request.urlopen = original
    assert vistos.get("X-auth-request-preferred-username") == "claudinho-IA"


# ================================================================= 7. conformidade


def rastreador_no_ar() -> bool:
    try:
        AdaptadorBoard()._carimbo()
    except Exception:  # noqa: BLE001
        return False
    return True


@pytest.mark.skipif(not rastreador_no_ar(), reason=f"rastreador fora do ar em {BASE}")
def test_conformidade_board_bate_com_o_verbo_humano():
    """§5: o resultado bate com o do verbo humano sobre o mesmo estado."""
    p = subprocess.run(["tarefas", "listar", "--cadeira", "claudinho-IA",
                        "--estado", "priorizada"],
                       capture_output=True, text=True, timeout=30,
                       env={**os.environ, "PF_CADEIRA": "claudinho-IA"})
    if p.returncode != 0:
        pytest.skip("verbo `tarefas` indisponível")
    do_verbo = {linha.split("\t")[0].strip() for linha in p.stdout.splitlines() if linha.strip()}
    r = AdaptadorBoard().busca("", filtros={"cadeira": "claudinho-IA",
                                            "estado": "priorizada"}, k=100)
    do_adaptador = {i.procedencia.chave.removeprefix("item:") for i in r.itens}
    assert do_adaptador == do_verbo


@pytest.mark.skipif(not rastreador_no_ar(), reason=f"rastreador fora do ar em {BASE}")
def test_conformidade_carimbo_nao_muda_por_leitura():
    """Aceite do #2307, do lado do consumidor: ler não move o ledger."""
    a = AdaptadorBoard()
    antes = a._carimbo()
    a.busca("", k=5)
    assert a._carimbo() == antes
