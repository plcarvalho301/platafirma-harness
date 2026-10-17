"""Stack de catálogo (registrada sem compose) não entra na promoção por release.

Regressivo do dia 14/10/2026: o #3551 registrou a stack `harness` com `compose: null`, de propósito
(existe para dar stack a verbo, porta e documento, e não sobe em contêiner). O `ler_stacks_da_familia`
de `bin/release` a pôs entre as que promovem, o passo de teste da imagem chamou `stack testar harness`,
que recusa stack sem compose (exit 2), e toda promoção do `platafirma-harness` parou com
«passo de teste da imagem da stack harness não rodou … current intacto».

Prova, com forge bare local, `acervo` de mentira (só `ler casa stack`) e a release em tmp: a stack sem
compose não vai a `STACKS_PROMOVER`, a promoção inteira chega ao fim, a linha do ensaio a nomeia como de
catálogo, e a stack com compose (ou de fixture antiga, sem a chave) segue promovendo como sempre.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "release"

CATALOGO = {"slug": "cat", "repo": "fixture", "compose": None, "reversao": {"via": "promover"}}
COM_COMPOSE = {"slug": "x", "repo": "fixture", "compose": "deploy/x/compose.yaml",
               "reversao": {"via": "promover"}}
SEM_A_CHAVE = {"slug": "velha", "repo": "fixture", "reversao": {"via": "promover"}}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          check=True).stdout.strip()


class Ambiente:
    def __init__(self, tmp_path: Path, registro: list):
        self.wt = tmp_path / "wt" / "fixture"
        self.forge = tmp_path / "forge" / "fixture.git"
        self.wt.mkdir(parents=True)
        self.forge.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)], check=True, capture_output=True)
        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        (self.wt / "README.md").write_text("um\n", encoding="utf-8")
        _git(self.wt, "add", "-A")
        _git(self.wt, "commit", "-q", "-m", "fixture inicial")
        self.sha = _git(self.wt, "rev-parse", "HEAD")
        _git(self.wt, "remote", "add", "origin", str(self.forge))
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        (tmp_path / "stacks.json").write_text(json.dumps(registro), encoding="utf-8")
        acervo = stub_bin / "acervo"
        acervo.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = ler ] && [ "$2" = casa ] && [ "$3" = stack ]; then\n'
            f"  cat '{tmp_path / 'stacks.json'}'\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n", encoding="utf-8")
        acervo.chmod(0o755)

        self.env = dict(os.environ)
        self.env.update({
            "PF_RELEASE_RAIZ": str(tmp_path / "opt"),
            "PLATAFIRMA_INSTANCIA": str(tmp_path / "srv"),
            "PLATAFIRMA_FAMILIAS": str(tmp_path / "familias.json"),
            "PLATAFIRMA_VENVS": str(tmp_path / "venvs.json"),
            "PLATAFIRMA_TERCEIROS": str(tmp_path / "terceiros.json"),
            "PF_RELEASE_PORTA": "0",
            "PATH": f"{stub_bin}{os.pathsep}" + self.env.get("PATH", ""),
        })
        Path(self.env["PLATAFIRMA_FAMILIAS"]).write_text(json.dumps({"fixture": str(self.forge)}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text("{}", encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")

    def com_espelho(self):
        """Família já conhecida: o ensaio de família nova sai antes de listar as stacks."""
        fam = Path(self.env["PF_RELEASE_RAIZ"]) / "fixture"
        fam.mkdir(parents=True)
        _git(fam, "clone", "-q", "--bare", str(self.forge), str(fam / ".repo.git"))
        return self

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), *args], env=self.env, capture_output=True, text=True, timeout=90)


def _amb(tmp_path, *stacks):
    return Ambiente(tmp_path, list(stacks))


def test_ensaio_nomeia_a_stack_de_catalogo_e_nao_a_promove(tmp_path):
    amb = _amb(tmp_path, CATALOGO).com_espelho()
    r = amb.run("promover", "fixture", "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "de catálogo, sem compose" in r.stdout and "cat" in r.stdout
    assert "(bin/_release/stack promover)" not in r.stdout


def test_familia_so_de_catalogo_promove_inteira_sem_passar_pelo_passo_de_imagem(tmp_path):
    """O defeito: `stack testar cat` saía 2 e a promoção parava com current intacto."""
    amb = _amb(tmp_path, CATALOGO)
    r = amb.run("promover", "fixture")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "passo de teste da imagem" not in r.stderr
    assert "no ar:" in r.stdout


def test_stack_com_compose_continua_na_lista_de_promocao_ao_lado_da_de_catalogo(tmp_path):
    amb = _amb(tmp_path, CATALOGO, COM_COMPOSE).com_espelho()
    r = amb.run("promover", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "stacks:    x (bin/_release/stack promover)" in r.stdout
    assert "de catálogo, sem compose — nada sobe nem se mede: cat" in r.stdout


def test_registro_sem_a_chave_compose_segue_como_stack_de_promocao(tmp_path):
    """Fixtures e registros antigos não trazem `compose`: só a chave presente e nula é catálogo."""
    amb = _amb(tmp_path, SEM_A_CHAVE).com_espelho()
    r = amb.run("promover", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "stacks:    velha (bin/_release/stack promover)" in r.stdout
    assert "de catálogo" not in r.stdout


# --- stack de teste (`reversao.via: teste`, card #3733, arq:0129 D4) --------------------------------
#
# A biblioteca de front nao tem servico no ar: a stack dela so existe para o passo de imagem. Nao sobe,
# nao promove e nao reverte; o `gate_imagem` a mede, e o vermelho do estagio barra a promocao.

TESTE_STACK = {"slug": "t", "repo": "fixture", "compose": "deploy/t/compose.yaml", "projeto": "t",
               "reversao": {"via": "teste"}}

DOCKER_FALSO = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
if args[:2] == ["image", "inspect"]:
    sys.exit(1)
if args[:1] != ["compose"]:
    sys.exit(0)
perfis, arquivos, i, sub = [], [], 1, None
while i < len(args):
    a = args[i]
    if a in ("-p", "-f", "--env-file", "--profile"):
        if a == "--profile":
            perfis.append(args[i + 1])
        if a == "-f":
            arquivos.append(args[i + 1])
        i += 2
        continue
    sub = a
    break
if sub == "config":
    servicos = {"t-teste": {"build": {"context": os.path.dirname(arquivos[0]), "dockerfile": "Dockerfile"},
                            "image": "x/t-teste:" + os.environ.get("PF_RELEASE_SHA", "local"),
                            "profiles": ["teste"], "labels": {"pf.teste": "raio"}}}
    print(json.dumps({"services": servicos if "teste" in perfis else {}}))
    sys.exit(0)
if sub == "run":
    sys.exit(int(os.environ.get("STUB_TESTE_RC", "0")))
sys.exit(0)
'''

TESTE_FALSO = '''#!/usr/bin/env bash
"$PF_TESTE_ESTAGIO" estagio "$PF_TESTE_ESTAGIO_STACK" "$PF_TESTE_ESTAGIO_REV" preparar || exit 5
"$PF_TESTE_ESTAGIO" estagio "$PF_TESTE_ESTAGIO_STACK" "$PF_TESTE_ESTAGIO_REV" rodar provas/a.mjs || exit 1
'''


def _stack_de_teste_na_familia(amb, tmp_path):
    """Promove uma rev sem stack (o current existe), depois traz a stack de teste e uma rev nova."""
    assert amb.run("promover", "fixture").returncode == 0
    primeiro = amb.sha
    (amb.wt / "deploy" / "t").mkdir(parents=True)
    (amb.wt / "deploy" / "t" / "compose.yaml").write_text("name: t\nservices: {}\n", encoding="utf-8")
    (amb.wt / "deploy" / "t" / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    _git(amb.wt, "add", "-A")
    _git(amb.wt, "commit", "-q", "-m", "traz a stack de teste")
    _git(amb.wt, "push", "-q", "origin", "main")
    segundo = _git(amb.wt, "rev-parse", "HEAD")
    (tmp_path / "stacks.json").write_text(json.dumps([TESTE_STACK]), encoding="utf-8")
    (tmp_path / "topo.json").write_text(json.dumps({"stacks": {"t": TESTE_STACK}}), encoding="utf-8")
    stub = tmp_path / "stub-bin"
    (stub / "docker").write_text(DOCKER_FALSO, encoding="utf-8")
    (stub / "docker").chmod(0o755)
    (tmp_path / "teste-falso").write_text(TESTE_FALSO, encoding="utf-8")
    (tmp_path / "teste-falso").chmod(0o755)
    amb.env.update(DEPLOY_TOPO_ARQUIVO=str(tmp_path / "topo.json"), DEPLOY_ENV_DIR=str(tmp_path / "envs"),
                   DEPLOY_PONTOS=str(tmp_path / "pontos"), PF_TESTE_BIN=str(tmp_path / "teste-falso"),
                   PF_TRAVA_IMAGEM=str(tmp_path / "srv" / "trava.lock"),
                   PF_GATE_SINCRONO="1")      # mede aqui: o `sessao` real nao dispara job no teste
    return primeiro, segundo


def _sessao_falsa(amb, tmp_path):
    """`sessao longjob run|list`: o run roda o comando em segundo plano e diz unit e log como o verbo
    real diz; o list mostra um job ativo da medida de imagem quando FAKE_JOB_ATIVO traz o sha."""
    chamadas = tmp_path / "sessao-run.log"
    saida = tmp_path / "job.log"
    stub = tmp_path / "stub-bin" / "sessao"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = longjob ] && [ \"$2\" = list ]; then\n"
        "  [ -z \"${FAKE_JOB_ATIVO:-}\" ] || echo \"platafirma-job-imagem-x.service loaded active running \""
        "\"/x/bin/release _medir-imagem fixture $FAKE_JOB_ATIVO t\"\n"
        "  exit 0\nfi\n"
        "[ \"$1\" = longjob ] && [ \"$2\" = run ] || exit 2\n"
        f"echo run >> '{chamadas}'\n"
        "shift 3\n"
        f"nohup \"$@\" >'{saida}' 2>&1 &\n"
        f"echo 'unit: platafirma-job-imagem-teste'\necho 'log: {saida}'\n", encoding="utf-8")
    stub.chmod(0o755)
    del amb.env["PF_GATE_SINCRONO"]
    return chamadas


def test_ensaio_nomeia_a_stack_de_teste_e_nao_a_promove(tmp_path):
    amb = _amb(tmp_path, TESTE_STACK).com_espelho()
    r = amb.run("promover", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "de teste, só o passo de imagem as mede — nada sobe nem reverte: t" in r.stdout
    assert "(bin/_release/stack promover)" not in r.stdout


def test_estagio_vermelho_barra_a_promocao_com_4_e_o_current_fica(tmp_path):
    amb = _amb(tmp_path)
    primeiro, segundo = _stack_de_teste_na_familia(amb, tmp_path)
    amb.env["STUB_TESTE_RC"] = "1"
    r = amb.run("promover", "fixture", segundo)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "passo de teste da imagem da stack t reprovou" in r.stderr
    atual = (tmp_path / "opt" / "fixture" / "current").resolve().name
    assert atual == primeiro, f"current devia ficar em {primeiro[:7]} e esta em {atual[:7]}"


def test_estagio_que_nao_constroi_ou_nao_roda_barra_com_3(tmp_path):
    amb = _amb(tmp_path)
    primeiro, segundo = _stack_de_teste_na_familia(amb, tmp_path)
    (tmp_path / "teste-falso").write_text("#!/usr/bin/env bash\nexit 5\n", encoding="utf-8")
    r = amb.run("promover", "fixture", segundo)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "não rodou" in r.stderr
    assert (tmp_path / "opt" / "fixture" / "current").resolve().name == primeiro


def test_estagio_como_job_dentro_do_teto_barra_com_o_exit_do_job(tmp_path):
    """A medida passa do teto da chamada da porta: roda como job, e o promover espera ate o teto."""
    amb = _amb(tmp_path)
    primeiro, segundo = _stack_de_teste_na_familia(amb, tmp_path)
    chamadas = _sessao_falsa(amb, tmp_path)
    amb.env.update(PF_GATE_TETO_S="60", STUB_TESTE_RC="1")
    r = amb.run("promover", "fixture", segundo)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "passo de teste da imagem da stack t reprovou" in r.stderr
    assert chamadas.read_text().count("run") == 1
    assert (tmp_path / "opt" / "fixture" / "current").resolve().name == primeiro


def test_estagio_acima_do_teto_devolve_em_andamento_e_a_repeticao_acha_a_medida(tmp_path):
    import time
    amb = _amb(tmp_path)
    primeiro, segundo = _stack_de_teste_na_familia(amb, tmp_path)
    chamadas = _sessao_falsa(amb, tmp_path)
    amb.env.update(PF_GATE_TETO_S="0", STUB_TESTE_RC="1")
    r = amb.run("promover", "fixture", segundo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "imagem em andamento" in r.stdout and "platafirma-job-imagem-teste" in r.stdout, r.stdout
    assert "repita: release promover" in r.stderr
    assert (tmp_path / "opt" / "fixture" / "current").resolve().name == primeiro      # nada subiu
    marca = next((tmp_path / "srv" / "var" / "log" / "release-gate").glob("imagem-fixture-*-t.rc"), None)
    for _ in range(60):
        marca = next((tmp_path / "srv" / "var" / "log" / "release-gate").glob("imagem-fixture-*-t.rc"), None)
        if marca is not None and marca.exists():
            break
        time.sleep(1)
    assert marca is not None and marca.read_text().strip() == "4", marca
    amb.env["PF_GATE_TETO_S"] = "30"
    r2 = amb.run("promover", "fixture", segundo)
    assert r2.returncode == 4, r2.stdout + r2.stderr                       # a medida pronta vale
    assert chamadas.read_text().count("run") == 1, "abriu outro job para a mesma rev"


def test_estagio_anexa_ao_job_que_ja_mede_a_rev(tmp_path):
    amb = _amb(tmp_path)
    primeiro, segundo = _stack_de_teste_na_familia(amb, tmp_path)
    chamadas = _sessao_falsa(amb, tmp_path)
    amb.env.update(PF_GATE_TETO_S="0", FAKE_JOB_ATIVO=segundo)
    r = amb.run("promover", "fixture", segundo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ja roda no job platafirma-job-imagem-x" in r.stdout + r.stderr, r.stdout + r.stderr
    assert not chamadas.exists(), "abriu outro job de medicao para a mesma rev"


def test_reverter_tambem_nomeia_a_stack_de_catalogo(tmp_path):
    amb = _amb(tmp_path, CATALOGO)
    assert amb.run("promover", "fixture").returncode == 0
    (amb.wt / "README.md").write_text("dois\n", encoding="utf-8")
    _git(amb.wt, "commit", "-q", "-am", "dois")
    _git(amb.wt, "push", "-q", "origin", "main")
    assert amb.run("promover", "fixture").returncode == 0
    r = amb.run("reverter", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "de catálogo, sem compose — nada a reverter: cat" in r.stdout
