# test_contrato_conferir — contrato --json dos quatro sub-atos de `bin/conferir`
# (card #390, LOTE 1). Dois testes por classe: formato OK e falha/divergencia.
#
# `bin/conferir` nao tem extensao .py — carregado via SourceFileLoader, apontando
# para o arquivo real no repo (a fonte de verdade continua sendo bin/conferir,
# isto so testa o contrato dela).
#
# Nada aqui toca docker/systemctl/redis: servico mocka as funcoes que falam com o
# mundo (containers/git_estado/env_declarado); verbo mocka origem() (symlink real
# exige permissao que a maquina de dev pode nao ter) mas deixa cabecalho() ler
# arquivo de verdade; skill e repo rodam contra git de verdade em repos-fixture
# descartaveis (temp dir), sem mock nenhum — a maquina tem git de verdade.
import importlib.machinery
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

# A implementacao virou sub-ato de `release` (arq:0110 §1, spec_release §4): bin/conferir e o
# despachante em bash; o contrato --json mora em bin/_release/conferir/conferir.py.
CONFERIR_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"


def _carregar_conferir():
    loader = importlib.machinery.SourceFileLoader("conferir_cli", str(CONFERIR_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


conferir = _carregar_conferir()


# Variáveis que o PRÓPRIO git injeta quando este processo roda dentro de um hook seu
# (pre-push, pre-commit): apontam pro repositório que disparou o hook, e um `git init`/
# `git commit` de fixture aqui dentro herdaria isso por padrão (subprocess.run repassa o
# ambiente do pai) — o "repo descartável" deixaria de ser descartável e a escrita cairia
# no repositório REAL. Medido: suíte que passa limpa rodada à mão e falha, com commit
# fantasma no branch de quem empurrou, rodada de dentro de `hooks/pre-push`.
_GIT_ENV_A_LIMPAR = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES",
)


def _git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_A_LIMPAR}
    subprocess.run(
        ["git", "-c", "user.email=teste@local", "-c", "user.name=teste", *args],
        cwd=cwd, check=True, capture_output=True, text=True, env=env,
    )


# --- servico ------------------------------------------------------------------
# Mocka containers()/git_estado()/env_declarado(): sao as tres funcoes que falam
# com docker/git no mundo real (regra do NOTAS-390.md para esta classe).


def test_servico_json_divergente(monkeypatch, capsys):
    # card #3142: o contrato --json de `servico` trocou de {resultado, servicos:
    # [{divergencias}]} pro Veredito comum de resultado.py — {ancora, itens:
    # [{estado, desde, motivo}]}. Este teste prova o novo formato, nao o antigo.
    container = {
        "nome": "app-2", "servico": "app",
        "working_dir": "/nao/e/deploy",  # fora de DEPLOY -> DERIVA
        "config_files": "", "env": {}, "started_at": "2026-09-20T10:00:00Z",
    }
    monkeypatch.setattr(conferir, "containers", lambda alvo: [container])
    monkeypatch.setattr(conferir, "git_estado", lambda caminho: None)
    monkeypatch.setattr(conferir, "env_declarado", lambda c: ({"FOO": "bar"}, None))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_servico(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    assert dado["classe"] == "servico"
    assert dado["release"] == "abc1234"
    assert "1 divergente" in dado["ancora"]
    assert len(dado["itens"]) == 1
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "worktree de deploy" in item["motivo"]
    assert "FOO" in item["motivo"] and "nao servido" in item["motivo"]


def test_servico_json_indeterminavel_quando_compose_nao_renderiza(monkeypatch, capsys):
    # card #3142, passo 3: falha de render do compose vira indeterminavel, nunca
    # divergente — nao saber nao e a mesma coisa que achar defeito.
    container = {
        "nome": "app-3", "servico": "app",
        "working_dir": "/opt/platafirma/deploy/app",
        "config_files": "", "env": {}, "started_at": None,
    }
    monkeypatch.setattr(conferir, "DEPLOY", "/opt/platafirma/deploy")
    monkeypatch.setattr(conferir, "containers", lambda alvo: [container])
    monkeypatch.setattr(conferir, "git_estado", lambda caminho: None)
    monkeypatch.setattr(conferir, "env_declarado", lambda c: (None, "docker compose config falhou"))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_servico(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    assert "0 divergente" in dado["ancora"]
    assert "1 não consegui olhar" in dado["ancora"]
    item = dado["itens"][0]
    assert item["estado"] == "indeterminavel"
    assert item["desde"] == "indeterminavel"
    assert "nao consegui renderizar o compose" in item["motivo"]


# --- verbo ----------------------------------------------------------------
# Mocka origem(): classificar symlink real exige permissao que a maquina de dev
# pode nao ter (NOTAS-390.md). cabecalho() le arquivo de verdade — o parsing do
# cabecalho de tres linhas e o que este teste de contrato quer provar.

def test_verbo_json_formato_ok(tmp_path, monkeypatch, capsys):
    # card #3142, passo 4: capacidades_do_mapa()/canonica() sairam; a validacao agora
    # e por conferir._capacidade_veredito (acervo resolver capacidade <forma>), mockada
    # aqui pra nao chamar o acervo de verdade num teste unitario.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    verbo = bin_dir / "meuverbo"
    verbo.write_text(
        "#!/usr/bin/env bash\n"
        "# meuverbo - verbo de teste para o contrato --json\n"
        "# capacidade: verificacao-de-teste\n"
        "# dono: claudinho-TI\n"
        "# componente: nenhum\n"
        "echo ok\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(conferir, "BIN", str(bin_dir))
    monkeypatch.setattr(conferir, "_capacidade_veredito", lambda cap: conferir.resultado.conforme())
    monkeypatch.setattr(conferir, "_desde_familia", lambda familia: "2026-09-20T10:00:00Z")
    monkeypatch.setattr(
        conferir, "origem",
        lambda nome, caminho: ("symlink", str(bin_dir.parent / "origem-real" / nome)),
    )

    exit_code = conferir.conferir_verbo(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["classe"] == "verbo"
    itens = {i["nome"]: i for i in dado["itens"]}
    assert itens["meuverbo"]["estado"] == "conforme"
    assert itens["meuverbo"]["desde"] == "2026-09-20T10:00:00Z"
    assert itens["arq:0037 verificacao-de-teste"]["estado"] == "conforme"


def test_verbo_json_divergente(tmp_path, monkeypatch, capsys):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    verbo = bin_dir / "verboquebrado"
    # sem as tres linhas do cabecalho: proposito/capacidade/dono ficam faltando.
    verbo.write_text("#!/usr/bin/env bash\necho oi\n", encoding="utf-8")
    monkeypatch.setattr(conferir, "BIN", str(bin_dir))
    monkeypatch.setattr(conferir, "_capacidade_veredito", lambda cap: conferir.resultado.conforme())
    monkeypatch.setattr(conferir, "_desde_familia", lambda familia: None)
    monkeypatch.setattr(
        conferir, "origem",
        lambda nome, caminho: ("so-no-host", "sem contraparte em repo"),
    )

    exit_code = conferir.conferir_verbo(None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = next(i for i in dado["itens"] if i["nome"] == "verboquebrado")
    assert item["estado"] == "divergente"
    assert item["desde"] == "indeterminavel"
    assert "sem origem unica" in item["motivo"]
    assert "cabecalho incompleto" in item["motivo"]


def test_verbo_capacidade_ausente_e_indeterminavel_se_acervo_falha(tmp_path, monkeypatch, capsys):
    # card #3142: rc fora de {0,1,2} do acervo resolver (ou acervo fora do ar) e
    # indeterminavel, nao divergente — nao afirmar ausencia sem conseguir olhar.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    verbo = bin_dir / "meuverbo"
    verbo.write_text(
        "#!/usr/bin/env bash\n"
        "# meuverbo - verbo de teste\n"
        "# capacidade: verificacao-de-teste\n"
        "# dono: claudinho-TI\n"
        "echo ok\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(conferir, "BIN", str(bin_dir))
    monkeypatch.setattr(conferir, "_desde_familia", lambda familia: None)
    monkeypatch.setattr(
        conferir, "origem",
        lambda nome, caminho: ("symlink", str(bin_dir.parent / "origem-real" / nome)),
    )
    monkeypatch.setattr(
        conferir, "sh",
        lambda args: (3, "", "dependencia ausente: acervo") if "resolver" in args else (0, "", ""),
    )

    exit_code = conferir.conferir_verbo("meuverbo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = next(i for i in dado["itens"] if i["nome"] == "meuverbo")
    assert item["estado"] == "indeterminavel"


# --- skill ------------------------------------------------------------------
# Roda contra git de verdade: cria um "harness" fixture descartavel com um
# commit de skills/<nome>/SKILL.md e usa o blob real que o git gravou.

@pytest.fixture
def harness_fixture(tmp_path):
    harness = tmp_path / "harness"
    harness.mkdir()
    _git(harness, "init", "-q")
    skill_dir = harness / "skills" / "minhaskill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("conteudo da skill de teste\n", encoding="utf-8")
    _git(harness, "add", "skills/minhaskill/SKILL.md")
    _git(harness, "commit", "-q", "-m", "skill de teste")
    return harness


def test_skill_json_em_dia(harness_fixture, monkeypatch, capsys):
    monkeypatch.setattr(conferir, "HARNESS", str(harness_fixture))
    fonte_blob = subprocess.run(
        ["git", "-C", str(harness_fixture), "rev-parse", "HEAD:skills/minhaskill/SKILL.md"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    exit_code = conferir.conferir_skill("minhaskill", servido=fonte_blob, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["classe"] == "skill"
    item = next(i for i in dado["itens"] if i["nome"] == "minhaskill")
    assert item["estado"] == "conforme"
    assert item["motivo"] is None


def test_skill_json_sem_servido_e_indeterminavel(harness_fixture, monkeypatch, capsys):
    # Card #3142 substitui a regra do #390 ("indeterminado", exit 2): ausencia de
    # --servido e o mesmo "nao consegui olhar" das demais classes agora, e por isso
    # segue o Veredito comum — exit 5, nao 2. Continua NAO sendo bug a consertar.
    monkeypatch.setattr(conferir, "HARNESS", str(harness_fixture))

    exit_code = conferir.conferir_skill("minhaskill", servido=None, como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = next(i for i in dado["itens"] if i["nome"] == "minhaskill")
    assert item["estado"] == "indeterminavel"
    assert item["motivo"]


# --- repo ---------------------------------------------------------------------
# Roda contra git de verdade: cada teste cria um repo-fixture descartavel em
# tmp_path e aponta conferir.RAIZ pra la (a raiz real nao existe nesta
# maquina de dev, e mesmo se existisse nao queremos varrer o disco todo).

def test_repo_json_formato_ok(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "meurepo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("# meurepo\n", encoding="utf-8")
    (repo / "fonte.py").write_text("print('ok')\n", encoding="utf-8")
    _git(repo, "add", "README.md", "fonte.py")
    _git(repo, "commit", "-q", "-m", "inicial")
    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))

    exit_code = conferir.conferir_repo("meurepo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["classe"] == "repo"
    item = next(i for i in dado["itens"] if i["nome"] == "meurepo")
    assert item["estado"] == "conforme"
    assert item["motivo"] is None


def test_repo_json_divergente_sem_readme(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "semreadme"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "fonte.py").write_text("print('oi')\n", encoding="utf-8")
    _git(repo, "add", "fonte.py")
    _git(repo, "commit", "-q", "-m", "inicial")
    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path))

    exit_code = conferir.conferir_repo("semreadme", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = next(i for i in dado["itens"] if i["nome"] == "semreadme")
    assert item["estado"] == "divergente"
    assert "README ausente" in item["motivo"]
