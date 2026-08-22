# Camada 3 do modelo de teste do card #390: fumaça HTTP. O serviço sobe, as
# três rotas respondem, a recepção contém os quatro blocos, e um verbo morto
# não pinta a linha como saudável (aceite 2 do card). Fora: teste de
# navegador, e2e, meta de cobertura.
from __future__ import annotations

import json
import re

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
                "manifesto": {"presente": True, "caminho": "abertura/ti/plataforma/ferramental.md"},
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


def test_repo_harness_aponta_pro_repo_de_verdade():
    """REPO_HARNESS precisa ser a raiz do clone (onde `git log` funciona), nao
    um nivel a mais/a menos por engano no numero de .parents — achado ao
    testar /feito manualmente contra um servidor real: `.parents[3]` (errado)
    apontava pro pai do clone (D:\\, no dev), onde `git log` falha silencioso
    e /feito sempre mostrava "nada a mostrar", mascarado pelos outros testes
    porque todos mockam `_monta_feito` inteiro."""
    import subprocess

    r = subprocess.run(
        ["git", "-C", str(web.REPO_HARNESS), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == "true"
    assert (web.REPO_HARNESS / "bin").is_dir()


def test_commits_por_dia_encontra_commits_reais():
    """Nao mocka nada — roda contra o proprio clone da branch, que tem
    commits de verdade (os dos LOTEs deste card). Prova que _commits_por_dia
    esta de fato lendo o repo certo, nao um caminho vazio/errado."""
    commits = web._commits_por_dia(limite_dias=365)
    assert commits
    todas_mensagens = [c["mensagem"] for dia in commits.values() for c in dia]
    assert any("card #390" in m or "#390" in m for m in todas_mensagens)


def test_front_vem_do_diretorio_da_imagem_nao_do_host(tmp_path):
    """Card #476: o front e servido do diretorio que o COPY --from do release
    deixou DENTRO da imagem. Nao ha mais TOKENS_PATH nem leitura de
    platafirma-arquitetura em tempo de requisicao — e essa ausencia e parte da
    assercao, senao a rota nova conviveria com o caminho velho."""
    assert not hasattr(web, "TOKENS_PATH")
    assert not hasattr(web, "tokens_css")

    d = tmp_path / "pf-ui"
    (d / "fontes").mkdir(parents=True)
    (d / "pf-ui.css").write_text(
        '@font-face{src:url("./fontes/inter.woff2")}:root{--platafirma-gray-100:#fff}',
        encoding="utf-8",
    )
    (d / "pf-ui.js").write_text("customElements.define('pf-botao', class extends HTMLElement{});",
                                encoding="utf-8")
    (d / "versao.txt").write_text("platafirma-ui 0.1.0\n", encoding="utf-8")
    (d / "fontes" / "inter.woff2").write_bytes(b"wOF2")

    c = TestClient(web.cria_app(pf_ui_dir=d))

    r = c.get("/estatico/pf-ui/pf-ui.css")
    assert r.status_code == 200
    assert "platafirma-gray-100" in r.text
    assert r.headers["content-type"].startswith("text/css")

    r = c.get("/estatico/pf-ui/pf-ui.js")
    assert r.status_code == 200
    assert "pf-botao" in r.text

    # o @font-face do release pede a fonte por caminho relativo: ela tem de
    # responder sob a MESMA base do css, senao a tela cai pra fonte do sistema.
    assert c.get("/estatico/pf-ui/fontes/inter.woff2").status_code == 200

    # a versao do release fica legivel em runtime sem abrir a imagem
    r = c.get("/estatico/pf-ui/versao.txt")
    assert r.status_code == 200
    assert r.text.strip() == "platafirma-ui 0.1.0"

    # rota antiga nao sobrevive
    assert c.get("/estatico/tokens.css").status_code == 404


def test_head_aponta_para_o_release(cliente):
    """A pagina carrega dois arquivos do release (css + modulo js) e nenhum
    tokens.css. tela.css continua valendo — nao pode ter sumido junto."""
    corpo = cliente.get("/").text
    assert '<link rel="stylesheet" href="/estatico/pf-ui/pf-ui.css">' in corpo
    assert '<script type="module" src="/estatico/pf-ui/pf-ui.js"></script>' in corpo
    assert '<link rel="stylesheet" href="/estatico/tela.css">' in corpo
    assert "tokens.css" not in corpo
    assert "platafirma-arquitetura" not in corpo


def test_tela_css_continua_respondendo(cliente):
    """Rota de camada 2, que o #476 NAO substitui: mora no pacote e segue viva."""
    r = cliente.get("/estatico/tela.css")
    assert r.status_code == 200
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


def test_caixa_parada_acima_do_limiar_vira_alert(cliente, tmp_path, monkeypatch):
    """Aceite 3 do card: "caixa com carta parada aparece sem ninguém
    consultar" — acima do limiar de idade (1h default), a linha e alert, nao
    so caveat, senao "parada" nao se distingue visualmente de "recem-parada"."""
    estado = dict(ESTADO_OK)
    estado["fila_status"] = {
        "lido_em": 1000.0, "estado": "ok", "motivo": None,
        "dados": [
            {"persona": "claudinho-TI", "pendentes": 3, "total_historico": 10, "estado": "parada",
             "idade_mais_antiga_seg": 7200, "ultima_leitura_seg": 7200},
        ],
    }
    caminho = tmp_path / "estado_parada.json"
    caminho.write_text(json.dumps(estado), encoding="utf-8")
    monkeypatch.setattr(web, "ESTADO_PATH", caminho)

    r = cliente.get("/")
    trecho = r.text.split('id="caixas"')[1].split("</section>")[0]
    assert "chip alert" in trecho
    assert "claudinho-TI" in trecho


def test_container_exited_sem_healthcheck_vira_fora_nao_sem_sinal(cliente, tmp_path, monkeypatch):
    """Cenario literal do aceite 2: rag-extractor-api derrubado de proposito.
    docker inspect da um estado_docker="exited" MESMO sem HEALTHCHECK nativo
    configurado (saude=None) -- isto tem que virar "fora"/alert, nunca "sem
    sinal"/caveat (que e reservado pra container RODANDO sem sonda, nao pra
    container confirmadamente parado). Achado ao testar manualmente contra um
    servidor real antes deste teste existir."""
    estado = dict(ESTADO_OK)
    estado["infra_estado"] = {
        "lido_em": 1000.0, "estado": "ok", "motivo": None,
        "dados": {"conteineres": [
            {"nome": "rag-extractor-api", "estado_docker": "exited", "saude": None, "desde": "2 minutes"},
        ], "units": [], "timers": []},
    }
    caminho = tmp_path / "estado_derrubado.json"
    caminho.write_text(json.dumps(estado), encoding="utf-8")
    monkeypatch.setattr(web, "ESTADO_PATH", caminho)

    r = cliente.get("/")
    assert r.status_code == 200
    trecho_sinal = r.text.split('id="sinal"')[1].split("</section>")[0]
    assert "chip alert" in trecho_sinal
    assert "fora" in trecho_sinal
    assert "sem sinal" not in trecho_sinal
    assert "rag-extractor-api" in trecho_sinal


def test_container_rodando_sem_healthcheck_e_sem_sinal_de_verdade(cliente, tmp_path, monkeypatch):
    """O caso oposto: container RUNNING sem HEALTHCHECK nativo (nem sonda
    externa, trilha C fora de escopo) -- este SIM e "sem sinal" honesto, nao
    "fora" nem "no ar" fingido."""
    estado = dict(ESTADO_OK)
    estado["infra_estado"] = {
        "lido_em": 1000.0, "estado": "ok", "motivo": None,
        "dados": {"conteineres": [
            {"nome": "keycloak-db", "estado_docker": "running", "saude": None, "desde": "10 days"},
        ], "units": [], "timers": []},
    }
    caminho = tmp_path / "estado_sem_sonda.json"
    caminho.write_text(json.dumps(estado), encoding="utf-8")
    monkeypatch.setattr(web, "ESTADO_PATH", caminho)

    r = cliente.get("/")
    trecho_sinal = r.text.split('id="sinal"')[1].split("</section>")[0]
    assert "sem sinal" in trecho_sinal
    assert "chip caveat" in trecho_sinal
    assert "chip alert" not in trecho_sinal


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


# --- zero JS PROPRIO, zero estado no cliente (aceite 6, medido tambem aqui) --
#
# O aceite 6 do card #390 dizia "zero JavaScript", e ate o #476 isso era
# literal. O #476 manda consumir o release platafirma/ui, e o release e um
# modulo: pf-ui.js registra os primitivos pf-* como custom elements. A regra que
# o aceite protegia continua de pe e e esta — o que ela proibia era logica de
# tela no cliente, nao um artefato versionado servido da propria imagem:
#   - nenhum script INLINE (nada de logica escrita aqui dentro),
#   - nenhum handler on*= no HTML,
#   - nenhum estado no cliente (local/sessionStorage),
#   - e o UNICO <script> da pagina e o do release, do nosso proprio /estatico.
# Script de terceiro, ou script com corpo, reprova.


def test_paginas_nao_tem_javascript_proprio_nem_storage(cliente):
    for rota in ("/", "/cadeira/TI"):
        corpo = cliente.get(rota).text.lower()
        assert "onclick" not in corpo
        assert "localstorage" not in corpo
        assert "sessionstorage" not in corpo
        scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", corpo, re.DOTALL)
        assert len(scripts) == 1, scripts
        assert scripts[0].strip() == "", "script com corpo e logica de tela, nao artefato"
        assert '<script type="module" src="/estatico/pf-ui/pf-ui.js"></script>' in corpo


# ---------- seletor fechado: a tela nao oferece o que o verbo nao aceita ----------
#
# "Claudinho-TI" digitado no campo livre criou uma caixa nova em producao. Duas
# causas, e as duas viraram teste: a validacao do verbo estava desligada quando
# .personas nao era legivel, e a tela oferecia texto livre onde o verbo tem
# lista fechada. Fluxo humano e fluxo de maquina sao o mesmo fluxo: se o verbo
# enumera, a tela enumera.


def test_destinatario_e_select_nao_texto_livre():
    from harness_controle import render
    bloco = {"estado": "ok", "lido_em": 0, "dados": [
        {"persona": "claudinho-TI", "pendentes": 0, "estado": "vazia"},
        {"persona": "claudinha-produto", "pendentes": 2, "estado": "parada"},
    ]}
    html = render.bloco_caixas(bloco)
    assert '<input type="text" name="destinatario"' not in html
    assert '<select name="destinatario"' in html
    assert 'value="claudinho-TI"' in html
    assert 'value="claudinha-produto"' in html


def test_sem_leitura_de_caixa_nao_ha_formulario():
    """Sem lista nao se despacha: a acao some, nao vira campo aberto."""
    from harness_controle import render
    html = render.bloco_caixas({"estado": "indisponivel", "motivo": "verbo morto"})
    assert "despachar-recado" not in html
    assert "verbo morto" in html


def test_tipo_continua_fechado():
    from harness_controle import render
    bloco = {"estado": "ok", "lido_em": 0, "dados": [{"persona": "claudinho-TI", "pendentes": 0, "estado": "vazia"}]}
    html = render.bloco_caixas(bloco)
    assert '<select name="tipo"' in html
    for t in ("decisao", "resposta", "pedido", "minuta", "demanda", "handoff"):
        assert f'value="{t}"' in html
