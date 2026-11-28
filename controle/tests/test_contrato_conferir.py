# componente: componente:verbo-conferir
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
    # e por conferir._capacidade_veredito (biblioteca _identidade, classe capacidade), mockada
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
    assert itens["capacidade verificacao-de-teste"]["estado"] == "conforme"


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
    # card #3142: rc fora de {0,1,2} da resolucao (ou acervo fora do ar) e
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
    # a Olaria nao respondeu: indeterminavel
    monkeypatch.setattr(
        conferir, "_capacidades_olaria",
        lambda: (None, "olaria indisponivel"),
    )

    exit_code = conferir.conferir_verbo("meuverbo", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    item = next(i for i in dado["itens"] if i["nome"] == "meuverbo")
    assert item["estado"] == "indeterminavel"


# Testes de _donos_ferramental removidos na casa nova (#4348): tabela acervo.ferramental_verbo saiu.


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


# --- existe chapeu | skill (#2856 linha 94) ------------------------------------------------

def _abertura_de_fixture(tmp_path):
    raiz = tmp_path / "raiz"
    abertura = raiz / "platafirma-harness" / "abertura"
    for caminho in ("engenharia/devops", "engenharia/front-end", "dados/ontologia"):
        (abertura / caminho).mkdir(parents=True)
        (abertura / caminho / "chapeu.md").write_text("# chapeu\n", encoding="utf-8")
    (abertura / "dados" / "sem-chapeu-md").mkdir()
    skills = raiz / "platafirma-harness" / "skills"
    for nome in ("prosa", "diagrama"):
        (skills / nome).mkdir(parents=True)
        (skills / nome / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    (skills / "pasta-sem-skill-md").mkdir()
    return raiz


def test_existe_chapeu_acha_pelo_slug_e_por_cadeira_barra_chapeu(tmp_path, monkeypatch, capsys):
    chaves = ["chapeu:dados/ontologia", "chapeu:engenharia/devops", "chapeu:engenharia/front-end"]
    monkeypatch.setattr(conferir, "_olaria_post", lambda rota, corpo: (200, {"chaves": chaves}, None))

    assert conferir.conferir_existe("chapeu", "devops") == 0
    assert capsys.readouterr().out.startswith("existe: chapeu devops — Olaria tem engenharia/devops")
    assert conferir.conferir_existe("chapeu", "engenharia/devops") == 0
    assert conferir.conferir_existe("chapeu", "claudinho-engenharia/devops") == 0
    capsys.readouterr()
    # o chapéu existe, mas não nessa cadeira
    assert conferir.conferir_existe("chapeu", "dados/devops") == 1
    capsys.readouterr()


def test_existe_chapeu_ausente_sai_1_com_a_lista_na_segunda_linha(tmp_path, monkeypatch, capsys):
    chaves = ["chapeu:dados/ontologia", "chapeu:engenharia/devops", "chapeu:engenharia/front-end"]
    monkeypatch.setattr(conferir, "_olaria_post", lambda rota, corpo: (200, {"chaves": chaves}, None))

    assert conferir.conferir_existe("chapeu", "sem-chapeu-md") == 1
    linhas = capsys.readouterr().out.splitlines()
    assert linhas[0].startswith("nao-existe: chapeu sem-chapeu-md — Olaria lista 3 chapeus")
    assert "dados/ontologia, engenharia/devops, engenharia/front-end" in linhas[1]


def test_existe_skill_pede_o_skill_md_e_sem_pasta_e_indeterminavel(tmp_path, monkeypatch, capsys):
    raiz = _abertura_de_fixture(tmp_path)
    monkeypatch.setattr(conferir, "RAIZ", str(raiz))

    assert conferir.conferir_existe("skill", "prosa") == 0
    assert capsys.readouterr().out.startswith("existe: skill prosa — skills/ lista 2: diagrama, prosa")
    assert conferir.conferir_existe("skill", "pasta-sem-skill-md") == 1
    capsys.readouterr()

    monkeypatch.setattr(conferir, "RAIZ", str(tmp_path / "vazia"))
    assert conferir.conferir_existe("skill", "prosa") == 5
    assert capsys.readouterr().out.startswith("indeterminavel: skill prosa")


# --- existe entidade (#4133; fonte removida em 13/11/2026) --------------------


def test_existe_entidade_sai_5_sem_chamar_o_acervo_e_aponta_a_shape(monkeypatch, capsys):
    chamadas = []
    monkeypatch.setattr(conferir, "sh", lambda cmd: chamadas.append(cmd) or (0, "", ""))

    assert conferir.conferir_existe("entidade", "substrato") == 5
    linhas = capsys.readouterr().out.splitlines()
    assert linhas[0].startswith("indeterminavel: entidade substrato")
    assert "ontologia -- ler shape substrato" in "\n".join(linhas)
    assert not any("consultar" in c for cmd in chamadas for c in cmd)


def test_existe_entidade_sem_nome_sai_2(capsys):
    assert conferir.conferir_existe("entidade", None) == 2


# --- servico: filtro por slug de stack (DT 803) -----------------------------------
# A familia platafirma-rastreador tem duas stacks: rastreador (promove por release) e
# bancada-rastreador (fora da promocao). `conferir servico rastreador` casava os dois
# grupos pela familia e acusava DERIVA na bancada, revertendo a promocao boa.


def _mundo_rastreador(monkeypatch):
    docker = {
        "rastreador-api": ("rastreador", "api", "/opt/platafirma/platafirma-rastreador/" + "b" * 40),
        "bancada-api": ("bancada-rastreador", "bancada-api", "/opt/platafirma/platafirma-rastreador/" + "a" * 40),
    }

    def sh(args, cwd=None, env=None):
        if args[:2] == ["docker", "ps"]:
            return 0, "\n".join(docker), ""
        if args[:2] == ["docker", "inspect"]:
            projeto, servico, wd = docker[args[2]]
            return 0, json.dumps([{"Config": {"Env": [], "Labels": {
                "com.docker.compose.project": projeto,
                "com.docker.compose.service": servico,
                "com.docker.compose.project.working_dir": wd}}, "State": {}}]), ""
        return 1, "", ""

    monkeypatch.setattr(conferir, "sh", sh)
    monkeypatch.setattr(conferir, "_topologia", lambda: [
        {"slug": "rastreador", "repo": "platafirma-rastreador"},
        {"slug": "bancada-rastreador", "repo": "platafirma-rastreador"}])
    monkeypatch.setattr(conferir, "stack_do_container", lambda c, t=None: c["projeto"])
    monkeypatch.setattr(conferir, "PROD_RAIZ", "/opt/platafirma")


def test_servico_por_slug_de_stack_ignora_a_outra_stack_da_familia(monkeypatch):
    _mundo_rastreador(monkeypatch)
    assert [c["nome"] for c in conferir.containers("rastreador")] == ["rastreador-api"]
    assert [c["nome"] for c in conferir.containers("bancada-rastreador")] == ["bancada-api"]


def test_servico_pela_familia_completa_segue_casando_as_duas_stacks(monkeypatch):
    _mundo_rastreador(monkeypatch)
    assert sorted(c["nome"] for c in conferir.containers("platafirma-rastreador")) == [
        "bancada-api", "rastreador-api"]


# --- escritor: deriva entre processo em memoria e current/harness (DT 1440) ---------


def test_conferir_escritor_acusa_divergencia_quando_revisao_em_memoria_difere(tmp_path, monkeypatch, capsys):
    """DT 1440: conferir escritor diverge quando escritor.service serve revisao anterior ao current."""
    sha_atual = "e995d04111111111111111111111111111111111"
    sha_antigo = "3c9406d000000000000000000000000000000000"

    prod = tmp_path / "prod"
    alvo_harness = prod / "platafirma-harness" / sha_atual
    alvo_harness.mkdir(parents=True)
    # link lib/ para o repositorio real para importar escrita.cliente
    raiz_repo = Path(__file__).resolve().parents[2]
    (alvo_harness / "lib").symlink_to(raiz_repo / "lib")
    (prod / "current").mkdir(parents=True)
    (prod / "current" / "harness").symlink_to(alvo_harness)

    setup = tmp_path / "setup-escritor.sh"
    setup.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    svc = tmp_path / "escritor.service"
    svc.write_text(
        "\n".join(f"{k}={v}" for k, v in conferir._ESCRITOR_DIRETIVAS_SERVICE) + "\n",
        encoding="utf-8",
    )
    sock_u = tmp_path / "escritor.socket"
    sock_u.write_text(
        "\n".join(f"{k}={v}" for k, v in conferir._ESCRITOR_DIRETIVAS_SOCKET) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("PF_PROD_RAIZ", str(prod))
    monkeypatch.setenv("PF_HARNESS_DIR", str(prod / "current" / "harness"))
    monkeypatch.setattr(conferir, "_sha_release", lambda: sha_atual[:8])

    import sys
    lib_str = str(raiz_repo / "lib")
    if lib_str not in sys.path:
        sys.path.insert(0, lib_str)
    import escrita.cliente as esc_cliente

    monkeypatch.setattr(esc_cliente, "consultar_saude", lambda _s, timeout_s=2.0: {"ok": True, "release": sha_antigo})
    rc_div = conferir.conferir_escritor(
        como_json=True,
        setup_script=setup,
        service_unit=svc,
        socket_unit=sock_u,
        socket_path=tmp_path / "e.sock",
        analyze_runner=lambda: (0, "Overall exposure level for escritor.service: 1.5 SAFE", ""),
    )
    dado_div = json.loads(capsys.readouterr().out)
    assert rc_div == 1
    itens_div = {it["nome"]: it for it in dado_div["itens"]}
    assert itens_div["revisao em memoria"]["estado"] == "divergente"
    assert "3c9406d" in itens_div["revisao em memoria"]["motivo"]
    assert "e995d04" in itens_div["revisao em memoria"]["motivo"]
    assert "sudo systemctl restart escritor.service" in itens_div["revisao em memoria"]["motivo"]

    monkeypatch.setattr(esc_cliente, "consultar_saude", lambda _s, timeout_s=2.0: {"ok": True, "release": sha_atual})
    rc_ok = conferir.conferir_escritor(
        como_json=True,
        setup_script=setup,
        service_unit=svc,
        socket_unit=sock_u,
        socket_path=tmp_path / "e.sock",
        analyze_runner=lambda: (0, "Overall exposure level for escritor.service: 1.5 SAFE", ""),
    )
    dado_ok = json.loads(capsys.readouterr().out)
    assert rc_ok == 0
    itens_ok = {it["nome"]: it for it in dado_ok["itens"]}
    assert itens_ok["revisao em memoria"]["estado"] == "conforme"


def test_release_promover_avisa_restart_escritor_quando_altera_escrita(tmp_path):
    """DT 1440: avisar_restart_escritor emite aviso quando diff altera lib/escrita/ ou registro/escrita.yaml."""
    raiz_repo = Path(__file__).resolve().parents[2]
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q")
    (work / "bin").mkdir()
    (work / "lib" / "escrita").mkdir(parents=True)
    (work / "bin" / "outro").write_text("v1\n", encoding="utf-8")
    (work / "lib" / "escrita" / "portao.py").write_text("v1\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "base")
    sha1 = subprocess.check_output(["git", "-C", str(work), "rev-parse", "HEAD"], text=True).strip()

    (work / "bin" / "outro").write_text("v2\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "sem escrita")
    sha2 = subprocess.check_output(["git", "-C", str(work), "rev-parse", "HEAD"], text=True).strip()

    (work / "lib" / "escrita" / "portao.py").write_text("v2\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "com escrita")
    sha3 = subprocess.check_output(["git", "-C", str(work), "rev-parse", "HEAD"], text=True).strip()

    bare = tmp_path / "espelho" / "platafirma-harness.git"
    bare.parent.mkdir(parents=True)
    _git(tmp_path, "clone", "--bare", "-q", str(work), str(bare))

    script = (
        f'source <(sed -n "/^avisar_restart_escritor()/,/^}}/p" "{raiz_repo / "bin" / "release"}")\n'
        'GIT=git\n'
        'FAMILIA_BIN=platafirma-harness\n'
        f'espelho_de() {{ printf "%s\\n" "{bare}"; }}\n'
        f'avisar_restart_escritor "{sha1}" "{sha2}"\n'
    )
    sem_aviso = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True)
    assert sem_aviso.stderr == ""

    script_com = script.replace(f'avisar_restart_escritor "{sha1}" "{sha2}"', f'avisar_restart_escritor "{sha2}" "{sha3}"')
    com_aviso = subprocess.run(["bash", "-c", script_com], capture_output=True, text=True, check=True)
    assert "escritor:  AVISO" in com_aviso.stderr
    assert "sudo systemctl restart escritor.service" in com_aviso.stderr
