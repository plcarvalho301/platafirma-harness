"""Contrato de `repo hooks listar` e `repo hooks apagar` (card #3473, tarefa 2): webhook de
repositorio do forge pela porta.

Git real contra bare local; o forge e um `gh` de fixture (PF_GH_BIN) que guarda os webhooks de
cada repositorio em arquivo e registra cada chamada em `chamadas.log`. Prova: listar le um
repositorio ou todos os da bancada, filtra por trecho da url e nunca imprime o secret nem a
query da url; apagar exige `--url`, relê o hook pelo id, recusa (4) quando a url nao contem o
trecho e nao apaga, sai 1 para id que nao existe (idempotente), confirma no forge que o hook
saiu; sem permissao o ato sai 3 e diz o escopo que falta; falha de um repositorio nunca
vira exit 0.
Nao prova: o GitHub de verdade (paginacao real, mascara do secret, mensagens de erro de
cada versao do gh).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

SEGREDO = "SEGREDO-NUNCA-NA-SAIDA"
CREDENCIAL = "TOKEN-NA-QUERY"
URL_MORTA = "https://mcp.platafirma.org/github/webhook"
URL_VIVA = "https://hooks.exemplo.org/ci"

GH_FIXTURE = """#!@PY@
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
with open(os.path.join(d, "chamadas.log"), "a") as f:
    f.write(" ".join(args) + "\\n")
metodo, rest, i = "GET", [], 1
while i < len(args):
    if args[i] == "-X":
        metodo = args[i + 1]
        i += 2
    elif args[i].startswith("--"):
        i += 1
    else:
        rest.append(args[i])
        i += 1
if args[:1] != ["api"] or not rest:
    sys.exit(9)
partes = rest[0].split("/")  # repos/<dono>/<repo>[/hooks[/<id>]]
repo = partes[2]


def falha(msg):
    sys.stderr.write("gh: " + msg + "\\n")
    sys.exit(1)


def modo():
    p = os.path.join(d, repo + ".modo")
    return open(p).read().strip() if os.path.exists(p) else "ok"


m = modo()
if m == "inexistente":
    falha("Not Found (HTTP 404)")
if len(partes) == 3:
    print(json.dumps({"full_name": "/".join(partes[1:3]), "permissions": {"admin": m != "sem-admin"}}))
    sys.exit(0)
if m == "sem-admin":
    falha("Must have admin rights to Repository. (HTTP 403)")
arq = os.path.join(d, repo + ".json")
hooks = json.load(open(arq)) if os.path.exists(arq) else []
if len(partes) == 4:
    print(json.dumps(hooks))
    sys.exit(0)
alvo = [h for h in hooks if str(h["id"]) == partes[4]]
if metodo == "GET":
    if not alvo:
        falha("Not Found (HTTP 404)")
    print(json.dumps(alvo[0]))
elif metodo == "DELETE":
    if not alvo:
        falha("Not Found (HTTP 404)")
    json.dump([h for h in hooks if str(h["id"]) != partes[4]], open(arq, "w"))
else:
    sys.exit(9)
"""


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}, timeout=60).stdout.strip()


def _hook(id_, url, *, ativo=True, eventos=("push",)):
    return {"id": id_, "name": "web", "active": ativo, "events": list(eventos),
            "config": {"url": url, "content_type": "json", "secret": SEGREDO,
                       "insecure_ssl": "0"},
            "url": f"https://api.github.com/repos/x/y/hooks/{id_}"}


def _montar(tmp_path, repos=("demo",)):
    origem = tmp_path / "origem.git"
    semente = tmp_path / "semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    (semente / "LEIA.md").write_text("x\n")
    _git("add", "LEIA.md", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    for nome in repos:
        _git("clone", str(origem), str(bancada / nome))
    forge = tmp_path / "forge"
    forge.mkdir()
    gh = forge / "gh"
    gh.write_text(GH_FIXTURE.replace("@PY@", sys.executable))
    gh.chmod(0o755)
    return bancada, forge


def _hooks_do_repo(forge, repo, hooks, modo=None):
    (forge / f"{repo}.json").write_text(json.dumps(hooks))
    if modo:
        (forge / f"{repo}.modo").write_text(modo)


def _repo(tmp_path, bancada, *args, **extra):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "PF_GH_BIN": str(tmp_path / "forge" / "gh"),
        **IDENT,
        **extra,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True,
                          check=False, timeout=60)


def _chamadas(forge):
    p = forge / "chamadas.log"
    return p.read_text().splitlines() if p.exists() else []


def _apagou(forge):
    return [c for c in _chamadas(forge) if "-X DELETE" in c]


def _ids(forge, repo):
    return [h["id"] for h in json.loads((forge / f"{repo}.json").read_text())]


# --- listar ---------------------------------------------------------------------------


def test_listar_um_repositorio_traz_id_url_eventos_e_ativo(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [
        _hook(101, URL_MORTA, eventos=("push", "pull_request")),
        _hook(102, URL_VIVA, ativo=False),
    ])
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    linhas = r.stdout.splitlines()
    assert linhas[0] == "hooks: 1 repositório lido, 2 hooks, 2 casando"
    corpo = "\n".join(linhas[1:])
    assert "demo" in corpo and "#101" in corpo and URL_MORTA in corpo
    assert "push,pull_request" in corpo
    assert "#102" in corpo and URL_VIVA in corpo and "inativo" in corpo
    assert "ativo" in corpo
    assert _apagou(forge) == []


def test_listar_todos_le_cada_clone_da_bancada(tmp_path):
    bancada, forge = _montar(tmp_path, repos=("demo", "outro"))
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA), _hook(102, URL_VIVA)])
    _hooks_do_repo(forge, "outro", [_hook(201, URL_MORTA)])
    r = _repo(tmp_path, bancada, "hooks", "listar", "--todos")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines()[0] == "hooks: 2 repositórios lidos, 3 hooks, 3 casando"
    for esperado in ("#101", "#102", "#201"):
        assert esperado in r.stdout
    leituras = [c for c in _chamadas(forge) if c.endswith("/hooks")]
    assert any("repos/plcarvalho301/demo/hooks" in c for c in leituras)
    assert any("repos/plcarvalho301/outro/hooks" in c for c in leituras)


def test_listar_filtra_por_trecho_da_url(tmp_path):
    bancada, forge = _montar(tmp_path, repos=("demo", "outro"))
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA), _hook(102, URL_VIVA)])
    _hooks_do_repo(forge, "outro", [_hook(201, URL_MORTA)])
    r = _repo(tmp_path, bancada, "hooks", "listar", "--todos", "--url", "mcp.platafirma.org")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines()[0] == "hooks: 2 repositórios lidos, 3 hooks, 2 casando"
    assert "#101" in r.stdout and "#201" in r.stdout
    assert "#102" not in r.stdout and URL_VIVA not in r.stdout


def test_listar_sem_hook_casando_sai_0_e_diz_zero(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(102, URL_VIVA)])
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo", "--url", "mcp.platafirma.org")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines()[0] == "hooks: 1 repositório lido, 1 hook, 0 casando"
    assert "#102" not in r.stdout


def test_listar_nunca_imprime_secret_nem_query_da_url(tmp_path):
    bancada, forge = _montar(tmp_path)
    com_credencial = f"https://usuario:senha@mcp.platafirma.org/hook?token={CREDENCIAL}"
    _hooks_do_repo(forge, "demo", [_hook(101, com_credencial)])
    for extra in ((), ("--json",)):
        r = _repo(tmp_path, bancada, "hooks", "listar", "demo", *extra)
        assert r.returncode == 0, r.stdout + r.stderr
        saida = r.stdout + r.stderr
        assert SEGREDO not in saida
        assert CREDENCIAL not in saida
        assert "usuario" not in saida and "senha" not in saida
        assert "mcp.platafirma.org/hook" in saida
    # o filtro casa na url inteira, mesmo a parte que nao sai
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo", "--url", CREDENCIAL.lower())
    assert r.stdout.splitlines()[0] == "hooks: 1 repositório lido, 1 hook, 1 casando"


def test_listar_json_tem_resumo_e_hooks(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA), _hook(102, URL_VIVA)])
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo", "--url", "mcp.platafirma.org", "--json")
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["resumo"] == {"repositorios_lidos": 1, "hooks": 2, "casando": 1, "nao_lidos": 0}
    assert [h["id"] for h in d["hooks"]] == [101]
    assert d["hooks"][0]["repo"] == "demo" and d["hooks"][0]["url"] == URL_MORTA
    assert d["hooks"][0]["ativo"] is True and d["hooks"][0]["eventos"] == ["push"]


def test_ato_aceita_a_forma_com_hifen_da_porta(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA)])
    r = _repo(tmp_path, bancada, "hooks-listar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines()[0] == "hooks: 1 repositório lido, 1 hook, 1 casando"
    r = _repo(tmp_path, bancada, "hooks-apagar", "demo", "101", "--url", "mcp.platafirma.org")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _ids(forge, "demo") == []


def test_listar_sem_repo_nem_todos_sai_2(tmp_path):
    bancada, forge = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "hooks", "listar")
    assert r.returncode == 2, r.stdout + r.stderr
    assert _chamadas(forge) == []


def test_listar_repo_desconhecido_sai_2(tmp_path):
    bancada, forge = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "hooks", "listar", "nao-ha")
    assert r.returncode == 2, r.stdout + r.stderr
    assert _chamadas(forge) == []


# --- apagar ---------------------------------------------------------------------------


def test_apagar_com_url_que_casa_apaga_so_aquele_e_confirma(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA), _hook(102, URL_VIVA)])
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "101", "--url", "mcp.platafirma.org")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "apagado" in r.stdout and "demo" in r.stdout and "#101" in r.stdout
    assert URL_MORTA in r.stdout
    assert SEGREDO not in r.stdout + r.stderr
    assert _ids(forge, "demo") == [102]
    assert len(_apagou(forge)) == 1
    assert "repos/plcarvalho301/demo/hooks/101" in _apagou(forge)[0]


def test_apagar_recusa_com_exit_4_quando_a_url_nao_casa_e_nao_apaga(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA), _hook(102, URL_VIVA)])
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "102", "--url", "mcp.platafirma.org")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "nada apagado" in r.stderr
    assert URL_VIVA in r.stderr
    assert _ids(forge, "demo") == [101, 102]
    assert _apagou(forge) == []


def test_apagar_id_inexistente_sai_1_ja_feito(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(102, URL_VIVA)])
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "999", "--url", "mcp.platafirma.org")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "já feito" in r.stdout and "#999" in r.stdout
    assert _apagou(forge) == []
    assert _ids(forge, "demo") == [102]


def test_apagar_e_idempotente_a_segunda_vez_sai_1_sem_apagar_nada(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA), _hook(102, URL_VIVA)])
    args = ("hooks", "apagar", "demo", "101", "--url", "mcp.platafirma.org")
    assert _repo(tmp_path, bancada, *args).returncode == 0
    r = _repo(tmp_path, bancada, *args)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "já feito" in r.stdout
    assert len(_apagou(forge)) == 1
    assert _ids(forge, "demo") == [102]


def test_apagar_sem_url_sai_2_e_nao_toca_o_forge(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA)])
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "101")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--url" in r.stderr
    assert _chamadas(forge) == []
    assert _ids(forge, "demo") == [101]


def test_apagar_com_url_vazia_sai_2(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA)])
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "101", "--url", "")
    assert r.returncode == 2, r.stdout + r.stderr
    assert _chamadas(forge) == []


def test_apagar_id_que_nao_e_numero_sai_2(tmp_path):
    bancada, forge = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "../x", "--url", "mcp")
    assert r.returncode == 2, r.stdout + r.stderr
    assert _chamadas(forge) == []


# --- permissao e dependencia ------------------------------------------------------------


def test_listar_sem_permissao_sai_3_e_diz_o_escopo_que_falta(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA)], modo="sem-admin")
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "admin:repo_hook" in r.stdout + r.stderr
    assert "admin" in (r.stdout + r.stderr)
    assert SEGREDO not in r.stdout + r.stderr


def test_apagar_sem_permissao_sai_3_e_nao_apaga(tmp_path):
    bancada, forge = _montar(tmp_path)
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA)], modo="sem-admin")
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "101", "--url", "mcp.platafirma.org")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "admin:repo_hook" in r.stderr
    assert _apagou(forge) == []


def test_listar_todos_nao_esconde_o_repositorio_que_falhou(tmp_path):
    bancada, forge = _montar(tmp_path, repos=("demo", "outro"))
    _hooks_do_repo(forge, "demo", [_hook(101, URL_MORTA)])
    _hooks_do_repo(forge, "outro", [_hook(201, URL_MORTA)], modo="sem-admin")
    r = _repo(tmp_path, bancada, "hooks", "listar", "--todos")
    assert r.returncode == 3, r.stdout + r.stderr
    assert r.stdout.splitlines()[0] == "hooks: 1 repositório lido, 1 hook, 1 casando, 1 não lido"
    assert "#101" in r.stdout
    assert "FALHOU outro" in r.stdout and "admin:repo_hook" in r.stdout


def test_repositorio_inexistente_no_forge_nao_vira_zero_hooks(tmp_path):
    bancada, forge = _montar(tmp_path)
    (forge / "demo.modo").write_text("inexistente")
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo")
    assert r.returncode == 3, r.stdout + r.stderr
    assert r.stdout.splitlines()[0] == "hooks: 0 repositórios lidos, 0 hooks, 0 casando, 1 não lido"
    assert "FALHOU demo" in r.stdout


def test_sem_gh_sai_3(tmp_path):
    bancada, _ = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "hooks", "listar", "demo",
              PF_GH_BIN=str(tmp_path / "nao-ha-gh"))
    assert r.returncode == 3, r.stdout + r.stderr
    r = _repo(tmp_path, bancada, "hooks", "apagar", "demo", "1", "--url", "x",
              PF_GH_BIN=str(tmp_path / "nao-ha-gh"))
    assert r.returncode == 3, r.stdout + r.stderr
