# Camada 3 do modelo de teste do card #390: fumaça HTTP. O serviço sobe, as
# três rotas respondem, a recepção contém os quatro blocos, e um verbo morto
# não pinta a linha como saudável (aceite 2 do card). Fora: teste de
# navegador, e2e, meta de cobertura.
from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from harness_controle import web
from harness_controle.agregador import bloco_de
from harness_controle.verbos import ResultadoVerbo

ESTADO_OK = {
    "infra_estado": bloco_de(ResultadoVerbo(True, {"conteineres": [
        {"nome": "mediawiki", "estado_docker": "running", "saude": "healthy", "desde": "3 dias"},
    ], "units": [], "timers": []}, None, 0, 0.01), agora=1000.0),
    "infra_saude": bloco_de(ResultadoVerbo(True, {
        "ops_health": {"ok": True, "motivo": None}, "doentes": [], "falhadas": [],
        "disco": {}, "memoria": {},
    }, None, 0, 0.01), agora=1000.0),
    "fila_status": bloco_de(ResultadoVerbo(True, [
        {"persona": "claudinho-TI", "pendentes": 0, "total_historico": 3, "estado": "em_dia",
         "idade_mais_antiga_seg": None, "ultima_leitura_seg": 120},
    ], None, 0, 0.01), agora=1000.0),
    "cadeiras": {
        "lido_em": 1000.0, "estado": "ok", "motivo": None,
        "itens": [
            {"cadeira": "TI", "lido_em": 1000.0, "estado": "ok", "motivo": None, "dados": {
                "cadeira": "TI",
                "persona": {"presente": True, "caminho": "personas/persona-TI.md", "nome_resolvido": "claudinho-TI"},
                "manifesto": {"presente": True, "caminho": "tool-manifest/TI.md"},
                "org": {"presente": True, "caminho": "docs/org-template-canonico.md"},
                "mesa": {"disponivel": True, "resumo": "resumo da fita"},
                "cadernos": {"disponivel": True, "resumo": "nenhum"},
                "fila": {"disponivel": True, "resumo": "claudinho-TI: caixa em dia"},
                "atualizado": True,
            }},
        ],
    },
    "conferir_servico": bloco_de(ResultadoVerbo(True, {"resultado": "ok", "servicos": []}, None, 0, 0.01), agora=1000.0),
    "conferir_verbo": bloco_de(ResultadoVerbo(True, {"resultado": "ok", "verbos": [], "arq0037": []}, None, 0, 0.01), agora=1000.0),
    "conferir_repo": bloco_de(ResultadoVerbo(True, {"resultado": "ok", "repos": []}, None, 0, 0.01), agora=1000.0),
    "skills": {"lido_em": 1000.0, "estado": "ok", "motivo": None, "itens": []},
}


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    estado_path = tmp_path / "estado.json"
    estado_path.write_text(json.dumps(ESTADO_OK), encoding="utf-8")
    monkeypatch.setattr(web, "ESTADO_PATH", estado_path)
    return TestClient(web.app)


# --- aceite 1: tres rotas respondem, recepcao tem os 4 blocos --------------


def test_recepcao_responde_com_os_quatro_blocos(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    corpo = r.text
    for id_bloco in ("sinal", "caixas", "cadeiras"):
        assert f'id="{id_bloco}"' in corpo
    for titulo in ("Sinal", "Caixas", "Cadeiras", "Procedência"):
        assert f">{titulo}<" in corpo
    # idade do dado presente em cada bloco (spec: nunca sem carimbo)
    assert corpo.count("lido há") >= 4


def test_cadeira_responde(cliente):
    r = cliente.get("/cadeira/TI")
    assert r.status_code == 200
    assert "TI" in r.text
    assert "Documentos" in r.text


def test_cadeira_desconhecida_nao_quebra(cliente):
    r = cliente.get("/cadeira/fantasma")
    assert r.status_code == 200
    assert "não encontrada" in r.text or "indisponivel" in r.text.lower()


def test_feito_responde(cliente, monkeypatch):
    monkeypatch.setattr(web, "_monta_feito", lambda *a, **k: [])
    r = cliente.get("/feito")
    assert r.status_code == 200


def test_tokens_css_responde(cliente, tmp_path, monkeypatch):
    tokens = tmp_path / "tokens.css"
    tokens.write_text(":root { --platafirma-gray-100: #fff; }", encoding="utf-8")
    monkeypatch.setattr(web, "TOKENS_PATH", tokens)
    r = cliente.get("/estatico/tokens.css")
    assert r.status_code == 200
    assert "platafirma-gray-100" in r.text
    assert r.headers["content-type"].startswith("text/css")


# --- aceite 2: verbo morto nunca pinta linha como saudavel -----------------


def test_verbo_morto_nao_pinta_linha_saudavel(cliente, tmp_path, monkeypatch):
    """Derruba infra_estado/infra_saude no estado (equivalente a
    rag-extractor-api cair): a linha correspondente vira indisponivel, nunca
    verde, nunca zero, nunca bloco sumido."""
    estado_quebrado = dict(ESTADO_OK)
    estado_quebrado["infra_estado"] = {
        "lido_em": 1000.0, "estado": "indisponivel",
        "motivo": "timeout apos 15s", "dados": None,
    }
    estado_quebrado["infra_saude"] = {
        "lido_em": 1000.0, "estado": "indisponivel",
        "motivo": "timeout apos 15s", "dados": None,
    }
    caminho = tmp_path / "estado_quebrado.json"
    caminho.write_text(json.dumps(estado_quebrado), encoding="utf-8")
    monkeypatch.setattr(web, "ESTADO_PATH", caminho)

    r = cliente.get("/")
    assert r.status_code == 200
    corpo = r.text
    assert "chip calmo" not in corpo.split('id="sinal"')[1].split("</section>")[0]
    assert "indisponivel" in corpo.lower() or "sem leitura" in corpo.lower()
    assert "timeout" in corpo


def test_bloco_ausente_do_estado_vira_indisponivel_nao_bloco_sumido(cliente, tmp_path, monkeypatch):
    """estado.json sem a chave "cadeiras" nenhuma (agregador nunca leu essa
    sonda ainda) — o bloco continua aparecendo na pagina, so como
    indisponivel, nunca desaparece."""
    parcial = {k: v for k, v in ESTADO_OK.items() if k != "cadeiras"}
    caminho = tmp_path / "estado_parcial.json"
    caminho.write_text(json.dumps(parcial), encoding="utf-8")
    monkeypatch.setattr(web, "ESTADO_PATH", caminho)

    r = cliente.get("/")
    assert r.status_code == 200
    assert ">Cadeiras<" in r.text  # o bloco continua la


def test_estado_json_ausente_nao_derruba_a_pagina(cliente, tmp_path, monkeypatch):
    monkeypatch.setattr(web, "ESTADO_PATH", tmp_path / "nao-existe.json")
    r = cliente.get("/")
    assert r.status_code == 200
    assert "indisponivel" in r.text.lower() or "sem leitura" in r.text.lower()


# --- exclusao dura: cloudflared/oauth2-proxy nunca reiniciaveis -------------


def test_reiniciar_cloudflared_e_recusado(cliente):
    r = cliente.post("/acoes/reiniciar", data={"alvo": "cloudflared"})
    assert r.status_code == 403


def test_reiniciar_oauth2_proxy_e_recusado(cliente):
    r = cliente.post("/acoes/reiniciar", data={"alvo": "oauth2-proxy"})
    assert r.status_code == 403


def test_reiniciar_sem_alvo_e_recusado(cliente):
    r = cliente.post("/acoes/reiniciar", data={})
    assert r.status_code == 400


def test_reiniciar_alvo_normal_chama_o_verbo(cliente, monkeypatch):
    chamadas = []

    class FalsoResultado:
        returncode = 0
        stderr = ""

    def _run_falso(argv, **kw):
        chamadas.append(argv)
        return FalsoResultado()

    monkeypatch.setattr("harness_controle.web.subprocess.run", _run_falso)
    r = cliente.post("/acoes/reiniciar", data={"alvo": "mediawiki"}, follow_redirects=False)
    assert r.status_code == 303
    assert chamadas and chamadas[0][-1] == "mediawiki"
    assert chamadas[0][-2] == "restart"


# --- despachar recado --------------------------------------------------


def test_despachar_recado_chama_fila_enviar(cliente, monkeypatch):
    chamadas = []

    class FalsoResultado:
        returncode = 0
        stderr = ""

    def _run_falso(argv, input=None, env=None, **kw):
        chamadas.append((argv, input, env.get("PF_CADEIRA")))
        return FalsoResultado()

    monkeypatch.setattr("harness_controle.web.subprocess.run", _run_falso)
    r = cliente.post(
        "/acoes/despachar-recado",
        data={"destinatario": "claudinho-conhecimento", "tipo": "pedido",
              "assunto": "teste do card 390", "corpo": "corpo auto-contido"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    argv, corpo_enviado, cadeira_env = chamadas[0]
    assert argv[1] == "enviar"
    assert argv[2] == "claudinho-conhecimento"
    assert "--tipo" in argv and "pedido" in argv
    assert "--assunto" in argv and "teste do card 390" in argv
    assert corpo_enviado == "corpo auto-contido"
    assert cadeira_env  # identidade da tela propagada, nao vazia


def test_despachar_recado_tipo_invalido_e_recusado(cliente):
    r = cliente.post(
        "/acoes/despachar-recado",
        data={"destinatario": "claudinho-TI", "tipo": "bagunca",
              "assunto": "x", "corpo": "y"},
    )
    assert r.status_code == 400


def test_despachar_recado_campo_ausente_e_recusado(cliente):
    r = cliente.post("/acoes/despachar-recado", data={"destinatario": "claudinho-TI"})
    assert r.status_code == 400


# --- zero JS, zero estado no cliente (aceite 6, medido tambem aqui) --------


def test_paginas_nao_tem_javascript_nem_storage(cliente):
    for rota in ("/", "/cadeira/TI"):
        corpo = cliente.get(rota).text.lower()
        assert "<script" not in corpo
        assert "onclick" not in corpo
        assert "localstorage" not in corpo
        assert "sessionstorage" not in corpo
