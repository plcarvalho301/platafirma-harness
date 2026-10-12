"""`conferir servico` e o filtro de e-mail dos gates oauth2-proxy (card #3476, nascido do #3339).

O oauth2-proxy autoriza o e-mail que casa o dominio OU consta da lista, e `*` casa todos: com
`--email-domain=*` junto de `--authenticated-emails-file` a lista deixou de filtrar ninguem nos
cinco gates do core, e a conferencia nao olhava o `command`, so o `environment`.

Prova: o par (curinga junto da lista) e divergente com o nome do conteiner e do servico, no
compose renderizado e no que o conteiner serve; o curinga sozinho e o gate sem filtro tambem; o
command dos cinco gates na forma da release corrente sai conforme; compose que nao renderiza e
indeterminavel (exit 5), salvo quando o servido ja prova o defeito; servico que nao e gate nao
muda de veredito. Docker e git de stub (como test_conferir_servico_release).
Nao prova: o docker real nem o compose do core (mora em platafirma-core).
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path

CONFERIR_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"
SHA = "a" * 40
IMAGEM = "quay.io/oauth2-proxy/oauth2-proxy:v7.15.3"
LISTA = "--authenticated-emails-file=/etc/oauth2-proxy/authenticated-emails.txt"
CURINGA = "--email-domain=*"
SERVICOS = ("oauth2-proxy", "oauth2-proxy-harness", "oauth2-proxy-rastreador",
            "oauth2-proxy-docs", "oauth2-proxy-casa")


def _carregar():
    loader = importlib.machinery.SourceFileLoader("conferir_gate_email_teste", str(CONFERIR_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


def _command_limpo(lista=LISTA):
    """O command de um gate na forma da release corrente: lista de e-mails, sem --email-domain."""
    return ["--provider=oidc", "--code-challenge-method=S256", "--skip-provider-button=true",
            "--skip-oidc-discovery=true", "--redirect-url=https://wiki.platafirma.org/oauth2/callback",
            lista, "--http-address=0.0.0.0:4180", "--upstream=http://mediawiki:80",
            "--reverse-proxy=true", "--trusted-proxy-ip=10.203.19.2/32", "--cookie-secure=true"]


def _container(servico):
    return f"platafirma-core-{servico}-1"


def _inspecao(servico, wd, imagem, cmd):
    return [{
        "Config": {
            "Labels": {
                "com.docker.compose.project": "platafirma-core",
                "com.docker.compose.project.working_dir": wd,
                "com.docker.compose.service": servico,
                "com.docker.compose.project.config_files": "",
            },
            "Env": [], "Cmd": cmd, "Image": imagem,
        },
        "State": {"StartedAt": "2026-10-12T12:00:00Z"},
    }]


def _docker_de_stub(cenario, wd):
    """O `sh` do conferir com docker de mentira. `cenario`: declarado/servido {servico: command},
    extra {servico: (imagem, command)} de servico que nao e gate, render_falha."""
    gates = {s: (IMAGEM, None) for s in SERVICOS}
    gates.update(cenario.get("extra") or {})
    declarado, servido = cenario.get("declarado") or {}, cenario.get("servido") or {}

    def command(sobreposto, servico):
        return sobreposto.get(servico) or gates[servico][1] or _command_limpo()

    def sh(args, cwd=None, **kw):
        if args[:2] == ["docker", "ps"]:
            return 0, "\n".join(_container(s) for s in gates), ""
        if args[:2] == ["docker", "inspect"]:
            achado = [s for s in gates if _container(s) == args[2]]
            if achado:
                s = achado[0]
                return 0, json.dumps(_inspecao(s, wd, gates[s][0], command(servido, s))), ""
        if args[:2] == ["docker", "compose"]:
            if cenario.get("render_falha"):
                return 1, "", "required variable KEYCLOAK_CLIENT_SECRET is missing a value"
            return 0, json.dumps({"services": {
                s: {"command": command(declarado, s), "environment": {}, "image": img}
                for s, (img, _) in gates.items()}}), ""
        return 1, "", "stub"   # git e acervo: fora do escopo deste teste
    return sh


def _mundo(tmp_path, monkeypatch, cenario=None):
    """Stack `platafirma-core` de teste, servida de <raiz>/platafirma-core/<sha>, que e o current."""
    conferir = _carregar()
    raiz = tmp_path / "opt"
    (raiz / "platafirma-core" / SHA / "core").mkdir(parents=True)
    os.symlink(SHA, raiz / "platafirma-core" / "current")
    monkeypatch.setattr(conferir, "PROD_RAIZ", str(raiz))
    wd = str(raiz / "platafirma-core" / SHA / "core")
    monkeypatch.setattr(conferir, "sh", _docker_de_stub(cenario or {}, wd))
    return conferir


def _roda(conferir, *, como_json=False):
    try:
        r = conferir.conferir_servico(None, como_json=como_json)
    except SystemExit as e:
        return e.code
    return r if isinstance(r, int) else 0


# --- a regra, pura -----------------------------------------------------------------

def test_regra_curinga_junto_da_lista_e_divergente():
    motivo = _carregar().divergencia_do_gate([CURINGA, LISTA])
    assert motivo and "--email-domain=*" in motivo and "nao filtra ninguem" in motivo


def test_regra_curinga_sozinho_e_gate_sem_filtro_sao_divergentes():
    c = _carregar()
    assert c.divergencia_do_gate([CURINGA])
    assert c.divergencia_do_gate(["--provider=oidc", "--http-address=0.0.0.0:4180"])
    assert c.divergencia_do_gate([])


def test_regra_lista_sem_curinga_e_dominio_especifico_sao_conformes():
    c = _carregar()
    assert c.divergencia_do_gate(_command_limpo()) is None
    assert c.divergencia_do_gate(["--email-domain=exemplo.org", "--provider=oidc"]) is None
    assert c.divergencia_do_gate(["--email-domain=exemplo.org", LISTA]) is None


def test_regra_le_a_forma_com_espaco_a_string_de_shell_e_o_env():
    c = _carregar()
    assert c.divergencia_do_gate(["--email-domain", "*", LISTA])
    assert c.divergencia_do_gate(c._args_do_comando(f"oauth2-proxy {CURINGA} {LISTA}"))
    assert c.divergencia_do_gate([LISTA], {"OAUTH2_PROXY_EMAIL_DOMAINS": "exemplo.org,*"})
    assert c.divergencia_do_gate([], {"OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE": "/e.txt"}) is None


# --- a conferencia, com docker de stub ----------------------------------------------

def test_command_dos_cinco_gates_na_forma_da_release_sai_conforme(tmp_path, monkeypatch, capsys):
    conferir = _mundo(tmp_path, monkeypatch)
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert "5 conforme · 0 divergente" in saida, saida
    assert "GATE" not in saida
    assert rc == 0


def test_curinga_junto_da_lista_no_compose_sai_1_com_o_nome_da_instancia(tmp_path, monkeypatch, capsys):
    declarado = {"oauth2-proxy-casa": [*_command_limpo(), CURINGA]}
    conferir = _mundo(tmp_path, monkeypatch, {"declarado": declarado})
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert rc == 1, saida
    assert "4 conforme · 1 divergente" in saida
    assert "platafirma-core-oauth2-proxy-casa-1" in saida and "declarado" in saida
    assert "--email-domain=* junto de --authenticated-emails-file" in saida


def test_curinga_servido_com_compose_limpo_sai_1(tmp_path, monkeypatch, capsys):
    """O compose foi consertado e o conteiner nao foi recriado: o gate segue aberto."""
    servido = {"oauth2-proxy-harness": [*_command_limpo(), CURINGA]}
    conferir = _mundo(tmp_path, monkeypatch, {"servido": servido})
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert rc == 1, saida
    assert "platafirma-core-oauth2-proxy-harness-1" in saida and "servido" in saida


def test_gate_sem_lista_nem_dominio_sai_1(tmp_path, monkeypatch, capsys):
    sem_nada = [a for a in _command_limpo() if not a.startswith("--authenticated-emails-file")]
    conferir = _mundo(tmp_path, monkeypatch, {"declarado": {"oauth2-proxy-docs": sem_nada}})
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert rc == 1, saida
    assert "platafirma-core-oauth2-proxy-docs-1" in saida
    assert "sem --authenticated-emails-file nem --email-domain" in saida


def test_json_traz_o_item_divergente_com_o_nome(tmp_path, monkeypatch, capsys):
    declarado = {"oauth2-proxy": [CURINGA, *_command_limpo()]}
    conferir = _mundo(tmp_path, monkeypatch, {"declarado": declarado})
    rc = _roda(conferir, como_json=True)
    itens = json.loads(capsys.readouterr().out)["itens"]
    ruim = [i for i in itens if i["estado"] == "divergente"]
    assert rc == 1 and len(ruim) == 1
    assert "platafirma-core-oauth2-proxy-1" in ruim[0]["nome"]
    assert "--email-domain=*" in ruim[0]["motivo"]


def test_compose_que_nao_renderiza_e_indeterminavel_nao_conforme(tmp_path, monkeypatch, capsys):
    conferir = _mundo(tmp_path, monkeypatch, {"render_falha": True})
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert rc == 5, saida
    assert "0 conforme · 0 divergente · 5 não consegui olhar" in saida
    assert "nao consegui renderizar o compose" in saida


def test_compose_que_nao_renderiza_mas_servido_com_o_par_e_divergente(tmp_path, monkeypatch, capsys):
    """O que o conteiner serve ja prova o defeito: nao vira «nao consegui olhar»."""
    servido = {"oauth2-proxy-rastreador": [*_command_limpo(), CURINGA]}
    conferir = _mundo(tmp_path, monkeypatch, {"servido": servido, "render_falha": True})
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert rc == 1, saida
    assert "1 divergente · 4 não consegui olhar" in saida


def test_servico_que_nao_e_gate_nao_e_julgado(tmp_path, monkeypatch, capsys):
    extra = {"tela": ("nginx:1.29", [CURINGA, "-g", "daemon off;"])}
    conferir = _mundo(tmp_path, monkeypatch, {"extra": extra})
    rc = _roda(conferir)
    saida = capsys.readouterr().out
    assert "6 conforme · 0 divergente" in saida, saida
    assert rc == 0
