# Card #3435 (R27 da spec taipa, lado da API): as duas rotas de escrita da tela do harness
# so aceitam a origem exata da tela, de lista fechada por instancia. As seis tentativas de
# fora recebem 403 e NENHUMA chega ao verbo; o ato pela tela passa.
#
# A tela do harness e formulario HTML sem script: nao ha cabecalho proprio a exigir, e as
# seis tentativas se distinguem so pela Origin e pelo tipo do corpo. Os dois verbos (fila e
# infra) sao trocados por um registro de chamadas: o teste prova que a recusa vem ANTES.
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from harness_controle import web

ORIGEM_DA_TELA = "https://tela.exemplo.test"
OUTRA_ORIGEM_NA_LISTA = "https://segunda-tela.exemplo.test"

FORM_RECADO = {"destinatario": "claudinho-conhecimento", "tipo": "pedido",
               "assunto": "teste do card 3435", "corpo": "corpo auto-contido"}
FORM_REINICIO = {"alvo": "mediawiki"}
ROTAS = [
    ("/acoes/despachar-recado", FORM_RECADO),
    ("/acoes/reiniciar", FORM_REINICIO),
]


class _Retorno:
    returncode = 0
    stderr = ""


@pytest.fixture()
def tela(monkeypatch, tmp_path):
    """O app com a lista da instancia declarada e os dois verbos trocados por um registro.
    Devolve (cliente_sem_origem, chamadas)."""
    chamadas = []

    def _run_falso(argv, **kw):
        chamadas.append(argv)
        return _Retorno()

    monkeypatch.setattr("harness_controle.web.subprocess.run", _run_falso)
    monkeypatch.setattr(web, "ESTADO_PATH", tmp_path / "nao-existe.json")
    monkeypatch.setenv("HARNESS_CONTROLE_ORIGENS", f"{ORIGEM_DA_TELA}, {OUTRA_ORIGEM_NA_LISTA}")
    return TestClient(web.app), chamadas


# --- as seis tentativas de fora: 403, e o verbo nao roda ----------------------------


@pytest.mark.parametrize("rota,form", ROTAS)
def test_formulario_de_outro_site_recebe_403(tela, rota, form):
    cliente, chamadas = tela
    r = cliente.post(rota, data=form, headers={"origin": "https://sitio-malicioso.test"},
                     follow_redirects=False)
    assert r.status_code == 403
    assert chamadas == []


@pytest.mark.parametrize("rota,form", ROTAS)
def test_chamada_com_cabecalho_proprio_de_outro_site_recebe_403(tela, rota, form):
    # O cabecalho proprio nao compra passagem: quem vem de outro site e recusado pela origem.
    cliente, chamadas = tela
    r = cliente.post(rota, json=form, follow_redirects=False,
                     headers={"origin": "https://sitio-malicioso.test", "x-pf-tela": "1"})
    assert r.status_code == 403
    assert chamadas == []


@pytest.mark.parametrize("rota,form", ROTAS)
def test_chamada_sem_cabecalho_de_outro_site_recebe_403(tela, rota, form):
    cliente, chamadas = tela
    r = cliente.post(rota, json=form, follow_redirects=False,
                     headers={"origin": "https://sitio-malicioso.test"})
    assert r.status_code == 403
    assert chamadas == []


@pytest.mark.parametrize("rota,form", ROTAS)
def test_chamada_sem_origem_recebe_403(tela, rota, form):
    cliente, chamadas = tela
    r = cliente.post(rota, data=form, follow_redirects=False)
    assert r.status_code == 403
    assert chamadas == []


@pytest.mark.parametrize("rota,form", ROTAS)
def test_text_plain_de_outro_site_recebe_403(tela, rota, form):
    cliente, chamadas = tela
    corpo = "&".join(f"{k}={v}" for k, v in form.items())
    r = cliente.post(rota, content=corpo, follow_redirects=False,
                     headers={"origin": "https://sitio-malicioso.test",
                              "content-type": "text/plain"})
    assert r.status_code == 403
    assert chamadas == []


@pytest.mark.parametrize("rota,form", ROTAS)
@pytest.mark.parametrize("irmao", [
    "https://tela.exemplo.test.sitio-malicioso.test",   # a tela como prefixo de outro host
    "https://outro.exemplo.test",                        # irmao no mesmo dominio
    "http://tela.exemplo.test",                          # mesmo host, outro esquema
    "https://tela.exemplo.test:8443",                    # mesmo host, outra porta
    "null",                                              # pagina em sandbox
])
def test_host_irmao_recebe_403(tela, rota, form, irmao):
    cliente, chamadas = tela
    r = cliente.post(rota, data=form, headers={"origin": irmao}, follow_redirects=False)
    assert r.status_code == 403
    assert chamadas == []


# --- o ato pela tela passa -----------------------------------------------------------


@pytest.mark.parametrize("origem", [ORIGEM_DA_TELA, OUTRA_ORIGEM_NA_LISTA])
@pytest.mark.parametrize("rota,form", ROTAS)
def test_a_tela_com_a_origem_da_lista_passa(tela, rota, form, origem):
    cliente, chamadas = tela
    r = cliente.post(rota, data=form, headers={"origin": origem}, follow_redirects=False)
    assert r.status_code == 303
    assert len(chamadas) == 1


# --- lista vazia fecha, e leitura nao e tocada ----------------------------------------


@pytest.mark.parametrize("rota,form", ROTAS)
def test_lista_vazia_recusa_ate_a_origem_da_tela(tela, monkeypatch, rota, form):
    cliente, chamadas = tela
    monkeypatch.setenv("HARNESS_CONTROLE_ORIGENS", "")
    r = cliente.post(rota, data=form, headers={"origin": ORIGEM_DA_TELA},
                     follow_redirects=False)
    assert r.status_code == 403
    assert chamadas == []


def test_leitura_nao_pede_origem(tela):
    cliente, _ = tela
    assert cliente.get("/").status_code == 200
