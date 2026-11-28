# componente: componente:verbo-repo
"""Cobertura dos DTs 809, 822, 853 e 884 em bin/repo."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests.test_repo_regressoes_lote_e import BIN_REPO, IDENT, _git


def _montar(tmp_path: Path, nome: str = "demo", arquivos: dict[str, str] | None = None) -> tuple[Path, Path]:
    origem, semente, bancada = tmp_path / f"{nome}-origem.git", tmp_path / f"{nome}-semente", tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    for rel, texto in (arquivos or {"LEIA.md": "v1\n"}).items():
        alvo = semente / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")
    for cmd in (("add", "."), ("commit", "-m", "semente"), ("remote", "add", "origin", str(origem)), ("push", "origin", "main")):
        _git(*cmd, cwd=semente)
    bancada.mkdir(exist_ok=True)
    _git("clone", str(origem), str(bancada / nome))
    return bancada, semente


def _repo(
    tmp_path: Path,
    bancada: Path,
    *args: str,
    cadeira: str = "engenharia",
    sessao: str = "s1",
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": cadeira,
        "PF_SESSAO": sessao,
        "PF_TAREFAS_BIN": "/bin/true",
        **IDENT,
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_dt809_abrir_sem_slug_nasce_em_fabrica_card(tmp_path: Path) -> None:
    """DT 809: repo abrir <repo> <card> sem --slug abre ramo fabrica/<card> (reconhecido no estagio 4)."""
    bancada, _ = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "abrir", "demo", "4319")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "engenharia" / "4319"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "fabrica/4319"


def test_dt822_pr_abrir_pr_revisar_e_pr_ver(tmp_path: Path) -> None:
    """DT 822: pr-abrir grava cadeira autora, pr-revisar registra leitura de outra cadeira e pr-ver exibe ambas."""
    bancada, _ = _montar(tmp_path)
    r_open = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "dt-822")
    assert r_open.returncode == 0, r_open.stderr
    wt = bancada / "wt" / "demo" / "engenharia" / "dt-822"
    (wt / "arq.txt").write_text("novo\n", encoding="utf-8")
    _git("add", "arq.txt", cwd=wt)
    _git("commit", "-m", "feat: dt 822", cwd=wt)
    _git("push", "-u", "origin", "engenharia/dt-822", cwd=wt)
    head_sha = _git("rev-parse", "HEAD", cwd=wt)

    estado_pr = tmp_path / "pr_state.json"
    gh_fake = tmp_path / "gh"
    gh_fake.write_text(
        f"""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

estado_path = Path({str(estado_pr)!r})
args = sys.argv[1:]

def carrega():
    if estado_path.exists():
        return json.loads(estado_path.read_text(encoding="utf-8"))
    return None

def salva(d):
    estado_path.write_text(json.dumps(d), encoding="utf-8")

if args[:2] == ["pr", "list"]:
    print("")
    sys.exit(0)
if args[:2] == ["pr", "create"]:
    titulo = args[args.index("--title") + 1]
    corpo = args[args.index("--body") + 1]
    base = args[args.index("--base") + 1]
    head = args[args.index("--head") + 1]
    salva({{
        "number": 42,
        "title": titulo,
        "state": "OPEN",
        "author": {{"login": "plcarvalho301"}},
        "headRefName": head,
        "headRefOid": {head_sha!r},
        "baseRefName": base,
        "url": "https://github.com/exemplo/demo/pull/42",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "mergeCommit": None,
        "body": corpo,
        "comments": [],
    }})
    sys.exit(0)
if args[:2] == ["pr", "comment"]:
    corpo = args[args.index("--body") + 1]
    d = carrega()
    d["comments"].append({{"body": corpo}})
    salva(d)
    sys.exit(0)
if args[:2] == ["pr", "view"]:
    d = carrega()
    if "--jq" in args:
        print(f"#{{d['number']}} {{d['state']}} {{d['url']}} (head {{d['headRefOid'][:7]}})")
    else:
        print(json.dumps(d))
    sys.exit(0)
sys.exit(0)
""",
        encoding="utf-8",
    )
    gh_fake.chmod(0o755)
    extra = {"PF_GH_BIN": str(gh_fake)}

    # 1. engenharia abre PR — corpo recebe marcador da cadeira autora
    r_pr = _repo(
        tmp_path, bancada, "pr-abrir", "demo", "--titulo", "feat: teste", "--corpo", "resumo do PR",
        cadeira="engenharia", extra_env=extra,
    )
    assert r_pr.returncode == 0, r_pr.stdout + r_pr.stderr
    salvo = json.loads(estado_pr.read_text(encoding="utf-8"))
    assert "<!-- pf-autor: engenharia -->" in salvo["body"]

    # 2. mesma cadeira autora nao pode revisar o proprio PR (exit 4)
    r_auto = _repo(
        tmp_path, bancada, "pr-revisar", "demo", "42", "--veredito", "junta",
        cadeira="engenharia", extra_env=extra,
    )
    assert r_auto.returncode == 4
    assert "autora do PR #42" in r_auto.stderr

    # 3. veredito volta sem motivo sai 2
    r_sem_mot = _repo(
        tmp_path, bancada, "pr-revisar", "demo", "42", "--veredito", "volta",
        cadeira="ti", extra_env=extra,
    )
    assert r_sem_mot.returncode == 2
    assert "--motivo" in r_sem_mot.stderr

    # 4. outra cadeira registra volta com motivo e depois junta
    r_volta = _repo(
        tmp_path, bancada, "pr-revisar", "demo", "42", "--veredito", "volta", "--motivo", "falta cobrir erro 404",
        cadeira="ti", extra_env=extra,
    )
    assert r_volta.returncode == 0, r_volta.stdout + r_volta.stderr
    assert "cadeira=ti · veredito=volta" in r_volta.stdout

    r_junta = _repo(
        tmp_path, bancada, "pr-revisar", "demo", "42", "--veredito", "junta",
        cadeira="ti", extra_env=extra,
    )
    assert r_junta.returncode == 0, r_junta.stdout + r_junta.stderr
    assert "cadeira=ti · veredito=junta" in r_junta.stdout

    # 5. pr-ver mostra cadeira autora e as leituras registradas sem vazar marcador HTML
    r_ver = _repo(tmp_path, bancada, "pr-ver", "demo", "42", cadeira="engenharia", extra_env=extra)
    assert r_ver.returncode == 0, r_ver.stdout + r_ver.stderr
    assert "autor : plcarvalho301 (cadeira: engenharia)" in r_ver.stdout
    assert "revisão :" in r_ver.stdout
    assert f"- ti: volta (head {head_sha[:7]}) — falta cobrir erro 404" in r_ver.stdout
    assert f"- ti: junta (head {head_sha[:7]})" in r_ver.stdout
    assert "<!-- pf-autor:" not in r_ver.stdout
    assert "resumo do PR" in r_ver.stdout


def test_dt853_leitura_origin_main_e_atualizar_head_destacado(tmp_path: Path) -> None:
    """DT 853: <repo>@origin/main e <repo>@main leem origin/main direto; atualizar avanca HEAD destacado limpo."""
    bancada, semente = _montar(tmp_path, arquivos={"LEIA.md": "v1\n"})
    sha_v1 = _git("rev-parse", "HEAD", cwd=bancada / "demo")
    fam = tmp_path / "release" / "demo"
    (fam / sha_v1).mkdir(parents=True)
    (fam / "current").symlink_to(fam / sha_v1)

    # Abre bancada em ramo antigo (fabrica/4280-antigo)
    r_open = _repo(tmp_path, bancada, "abrir", "demo", "4280", "--slug", "antigo")
    assert r_open.returncode == 0, r_open.stderr

    # origin/main avanca para v2
    (semente / "LEIA.md").write_text("v2\n", encoding="utf-8")
    (semente / "NOVO.md").write_text("novo\n", encoding="utf-8")
    _git("add", ".", cwd=semente)
    _git("commit", "-m", "v2 em main", cwd=semente)
    _git("push", "origin", "main", cwd=semente)

    # Leitura direta de origin/main ignora a bancada parada
    r_ler = _repo(tmp_path, bancada, "ler", "demo@origin/main", "LEIA.md")
    assert r_ler.returncode == 0, r_ler.stderr
    assert r_ler.stdout.strip() == "v2"

    r_ler_main = _repo(tmp_path, bancada, "ler", "demo@main", "LEIA.md")
    assert r_ler_main.returncode == 0, r_ler_main.stderr
    assert r_ler_main.stdout.strip() == "v2"

    r_list = _repo(tmp_path, bancada, "listar", "demo@origin/main")
    assert r_list.returncode == 0, r_list.stderr
    assert "NOVO.md" in r_list.stdout

    # Bancada de leitura aberta com --da-producao (HEAD destacado) avanca com repo atualizar
    r_prod = _repo(tmp_path, bancada, "abrir", "demo", "--da-producao", cadeira="ti")
    assert r_prod.returncode == 0, r_prod.stderr
    r_at = _repo(tmp_path, bancada, "atualizar", "demo", cadeira="ti")
    assert r_at.returncode == 0, r_at.stdout + r_at.stderr
    assert "atualizado: demo/HEAD ->" in r_at.stdout
    r_ler_ti = _repo(tmp_path, bancada, "ler", "demo", "LEIA.md", cadeira="ti")
    assert r_ler_ti.returncode == 0, r_ler_ti.stderr
    assert r_ler_ti.stdout.strip() == "v2"


def test_dt884_abrir_pela_dona_mantem_executor_formalizado(tmp_path: Path) -> None:
    """DT 884: dona (ti) abrindo story 4369 com executor engenharia nao sobrescreve executor."""
    bancada, _ = _montar(tmp_path)
    log = tmp_path / "tarefas.log"
    tarefas_mock = tmp_path / "tarefas-mock"
    tarefas_mock.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['TAREFAS_LOG'], 'a', encoding='utf-8') as f:\n"
        "    f.write(' '.join(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:3] == ['api', 'GET']:\n"
        "    print(json.dumps({'classe': 'tecnico', 'nivel_nome': 'story', 'estado': 'priorizada', "
        "'estado_fase': 'execucao', 'cadeira': 'ti', 'executor': 'engenharia'}))\n"
        "elif sys.argv[1] == 'mover':\n"
        "    print('movido')\n",
        encoding="utf-8",
    )
    tarefas_mock.chmod(0o755)
    extra = {"PF_TAREFAS_BIN": str(tarefas_mock), "TAREFAS_LOG": str(log)}

    # Abertura nova pela dona ti
    r1 = _repo(tmp_path, bancada, "abrir", "demo", "4369", cadeira="ti", extra_env=extra)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert "executor mantido (engenharia)" in r1.stdout

    # Reabertura da bancada ja aberta pela dona ti
    r2 = _repo(tmp_path, bancada, "abrir", "demo", "4369", cadeira="ti", extra_env=extra)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "executor mantido (engenharia)" in r2.stdout

    chamadas = log.read_text(encoding="utf-8").splitlines()
    assert not any(c.startswith("editar ") for c in chamadas), chamadas


def test_dt1434_ler_aceita_chave_com_dois_pontos_e_devolve_sha_do_blob(tmp_path: Path) -> None:
    """DT 1434: repo ler aceita <repo>@<chave>:<caminho> (proximo do gravar) e devolve o sha do blob."""
    bancada, _ = _montar(tmp_path)
    r_open = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "dt-1434")
    assert r_open.returncode == 0, r_open.stderr
    wt = bancada / "wt" / "demo" / "engenharia" / "dt-1434"
    blob_sha = _git("hash-object", str(wt / "LEIA.md"), cwd=wt)[:12]

    r_colon = _repo(tmp_path, bancada, "ler", "demo@dt-1434:LEIA.md")
    assert r_colon.returncode == 0, r_colon.stderr
    assert r_colon.stdout == "v1\n"
    primeira = r_colon.stderr.splitlines()[0]
    assert primeira.startswith(f"versão: {blob_sha} · "), primeira

    r_espaco = _repo(tmp_path, bancada, "ler", "demo@dt-1434", "LEIA.md")
    assert r_espaco.returncode == 0, r_espaco.stderr
    assert r_espaco.stdout == "v1\n"
    assert r_espaco.stderr.splitlines()[0].startswith(f"versão: {blob_sha} · "), r_espaco.stderr
