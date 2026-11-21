# componente: componente:verbo-release
"""Testes regressivos do Lote 4 de DTs: 256, 286, 333, 394 e 633 (bin/release e bin/_release/stack)."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

RAIZ = Path(__file__).resolve().parents[2]
RELEASE_BIN = RAIZ / "bin" / "release"
STACK_BIN = RAIZ / "bin" / "_release" / "stack"

SHA1 = "1" * 40
PRAZO_S = 30
EXIT_USO = 2
EXIT_PARCIAL = 5
MATCHES_ESPERADOS = 3


def _run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        check=check,
        timeout=PRAZO_S,
    )


def _chmod_ro(p: Path) -> None:
    for root, dirs, files in os.walk(p, topdown=False):
        for f in files:
            fp = Path(root) / f
            fp.chmod(fp.stat().st_mode & ~0o222)
        for d in dirs:
            dp = Path(root) / d
            dp.chmod(dp.stat().st_mode & ~0o222)
    p.chmod(p.stat().st_mode & ~0o222)


def _chmod_rw(p: Path) -> None:
    if not p.exists():
        return
    p.chmod(p.stat().st_mode | 0o200)
    for root, dirs, files in os.walk(p):
        for d in dirs:
            dp = Path(root) / d
            dp.chmod(dp.stat().st_mode | 0o200)
        for f in files:
            fp = Path(root) / f
            fp.chmod(fp.stat().st_mode | 0o200)


# ---- DT 286: bin/_release/stack separa fora do registro vs registrada sem compose ----

@pytest.fixture
def ambiente_dt286(tmp_path: Path) -> Iterator[dict[str, str]]:
    release_dir = tmp_path / "opt"
    instancia = tmp_path / "srv"
    arvore = release_dir / "platafirma-core" / SHA1
    arvore.mkdir(parents=True)
    (arvore / "docker-compose.yml").write_text(
        "name: pf-core\nservices:\n  app:\n    image: busybox\n",
        encoding="utf-8",
    )
    _chmod_ro(arvore)
    (release_dir / "platafirma-core" / "current").symlink_to(SHA1)

    topo = tmp_path / "topologia.json"
    topo.write_text(
        json.dumps(
            {
                "stacks": {
                    "core": {
                        "slug": "core",
                        "repo": "platafirma-core",
                        "compose": "docker-compose.yml",
                    },
                    "so-catalogo": {
                        "slug": "so-catalogo",
                        "repo": "platafirma-core",
                        "compose": [],
                    },
                    "sem-arq": {
                        "slug": "sem-arq",
                        "repo": "platafirma-core",
                        "compose": "ausente/docker-compose.yml",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env.update(
        {
            "PF_RELEASE_RAIZ": str(release_dir),
            "PLATAFIRMA_INSTANCIA": str(instancia),
            "PLATAFIRMA_BANCADA": str(tmp_path / "bancada-inexistente"),
            "DEPLOY_TOPO_ARQUIVO": str(topo),
            "DEPLOY_ENV_DIR": str(tmp_path / "run"),
        }
    )
    try:
        yield env
    finally:
        _chmod_rw(arvore)


def test_dt286_stack_separa_nao_registrada_de_registrada_sem_compose(
    ambiente_dt286: dict[str, str],
) -> None:
    r1 = _run([str(STACK_BIN), "compose", "fantasma", "ps"], ambiente_dt286)
    assert r1.returncode == EXIT_USO
    assert "stack não registrada em stacks.yaml: 'fantasma'" in r1.stderr
    assert "registradas:" in r1.stderr

    r2 = _run([str(STACK_BIN), "compose", "so-catalogo", "ps"], ambiente_dt286)
    assert r2.returncode == EXIT_USO
    assert "stack 'so-catalogo' registrada em stacks.yaml, mas sem compose" in r2.stderr
    assert "registradas:" not in r2.stderr

    r3 = _run([str(STACK_BIN), "compose", "sem-arq", "ps"], ambiente_dt286)
    assert r3.returncode == 1
    assert "stack 'sem-arq' registrada em stacks.yaml, mas sem compose em" in r3.stderr
    assert "ausente/docker-compose.yml" in r3.stderr


# ---- DT 633 + DT 333 + DT 394: release procurar (abertura, regex -E/-F, todos os matches) e release ler ----

@pytest.fixture
def ambiente_abertura(tmp_path: Path) -> Iterator[dict[str, str]]:
    srv = tmp_path / "srv"
    src = tmp_path / "src"
    (src / "docs").mkdir(parents=True)
    (src / "docs" / "guia.md").write_text(
        "\n"
        "# Dono\n"
        "\n"
        "Linha antes\n"
        "\n"
        "## Cenário: tombando legado\n"
        "A operação tem duas casas durante a transição.\n"
        "Outra menção: tombando legado na linha seguinte.\n"
        "Terceira menção: tombando legado no rodapé.\n",
        encoding="utf-8",
    )
    (src / "docs" / "conduta.md").write_text(
        "# Conduta\nRegra alfa\nRegra beta\n",
        encoding="utf-8",
    )
    git_env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=src, check=True, env=git_env)
    subprocess.run(["git", "add", "."], cwd=src, check=True, env=git_env)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=src, check=True, env=git_env)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=src, check=True,
                         capture_output=True, text=True).stdout.strip()
    fam_dir = tmp_path / "opt" / "fixture"
    alvo = fam_dir / sha
    fam_dir.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", str(src), str(alvo)], check=True, env=git_env)
    subprocess.run(["git", "checkout", "-q", "--detach", sha], cwd=alvo, check=True, env=git_env)
    _chmod_ro(alvo)
    (fam_dir / "current").symlink_to(sha)

    env = dict(os.environ)
    env.update(
        {
            "PLATAFIRMA_INSTANCIA": str(srv),
            "PF_RELEASE_RAIZ": str(tmp_path / "opt"),
        }
    )
    try:
        yield env
    finally:
        _chmod_rw(alvo)


def test_dt633_dt394_procurar_abertura_acha_dono_md_e_lista_todos_os_matches(
    ambiente_abertura: dict[str, str],
) -> None:
    r = _run([str(RELEASE_BIN), "procurar", "fixture", "tombando legado"], ambiente_abertura)
    assert r.returncode == 0, r.stderr
    linhas_dono = [
        linha for linha in r.stdout.splitlines() if "docs/guia.md:" in linha
    ]
    assert len(linhas_dono) == MATCHES_ESPERADOS, r.stdout
    assert "docs/guia.md:6:## Cenário: tombando legado" in linhas_dono[0]
    assert "docs/guia.md:8:Outra menção: tombando legado" in linhas_dono[1]
    assert "docs/guia.md:9:Terceira menção: tombando legado" in linhas_dono[2]

    r_pref1 = _run(
        [str(RELEASE_BIN), "procurar", "fixture", "tombando legado", "docs/guia.md"],
        ambiente_abertura,
    )
    assert r_pref1.returncode == 0
    assert len(r_pref1.stdout.splitlines()) == MATCHES_ESPERADOS


def test_dt333_procurar_usa_regex_ere_por_padrao_e_aceita_literal_e_ignore_case(
    ambiente_abertura: dict[str, str],
) -> None:
    r_ere = _run(
        [str(RELEASE_BIN), "procurar", "fixture", "tombando legado|Regra beta"],
        ambiente_abertura,
    )
    assert r_ere.returncode == 0, r_ere.stderr
    assert "docs/guia.md:6:" in r_ere.stdout
    assert "docs/conduta.md:3:Regra beta" in r_ere.stdout

    r_lit = _run(
        [str(RELEASE_BIN), "procurar", "fixture", "-F", "tombando legado|Regra beta"],
        ambiente_abertura,
    )
    assert r_lit.returncode == 0
    assert "não encontrado no servido fixture" in r_lit.stdout

    r_icase = _run(
        [str(RELEASE_BIN), "procurar", "fixture", "-i", "TOMBANDO LEGADO"],
        ambiente_abertura,
    )
    assert r_icase.returncode == 0
    assert "docs/guia.md:6:" in r_icase.stdout


def test_dt633_dt394_ler_com_linhas_preserva_primeira_linha_vazia_e_numeracao(
    ambiente_abertura: dict[str, str],
) -> None:
    r_faixa = _run(
        [str(RELEASE_BIN), "ler", "fixture", "docs/guia.md", "--linhas", "5-7"],
        ambiente_abertura,
    )
    assert r_faixa.returncode == 0, r_faixa.stderr
    partes = r_faixa.stdout.splitlines(keepends=True)
    assert partes == [
        "\n",
        "## Cenário: tombando legado\n",
        "A operação tem duas casas durante a transição.\n",
    ]

    r_num = _run(
        [str(RELEASE_BIN), "ler", "fixture", "docs/guia.md", "--linhas", "5-7", "--numerar"],
        ambiente_abertura,
    )
    assert r_num.returncode == 0, r_num.stderr
    assert r_num.stdout.splitlines() == [
        "5: ",
        "6: ## Cenário: tombando legado",
        "7: A operação tem duas casas durante a transição.",
    ]


# ---- DT 256: release promover retoma stacks pendentes após PROMOCAO PARCIAL ----

@dataclass
class AmbienteDt256:
    rel_copy: Path
    repo: str
    sha: str
    env: dict[str, str]
    falhar_marker: Path
    stack_log: Path


def _criar_origem_git(tmp_path: Path) -> tuple[Path, str]:
    origem = tmp_path / "origem.git"
    trab = tmp_path / "trab"
    script = tmp_path / "setup_git.sh"
    script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
git init --bare -q -b main "{origem}"
git clone -q "{origem}" "{trab}"
git -C "{trab}" config user.name Teste
git -C "{trab}" config user.email t@pf.org
printf 'v1\\n' > "{trab}/README.md"
git -C "{trab}" add .
git -C "{trab}" commit -q -m v1
git -C "{trab}" push -q origin main
git -C "{trab}" rev-parse HEAD
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    res = _run([str(script)], check=True)
    return origem, res.stdout.strip()


@pytest.fixture
def ambiente_dt256(tmp_path: Path) -> Iterator[AmbienteDt256]:
    prod_raiz = tmp_path / "opt"
    instancia = tmp_path / "srv"
    repo = "platafirma-demo"
    origem, sha = _criar_origem_git(tmp_path)

    fake_harness = tmp_path / "harness"
    (fake_harness / "bin" / "_release").mkdir(parents=True)
    for item in (RAIZ / "bin" / "_release").iterdir():
        if item.name != "stack":
            (fake_harness / "bin" / "_release" / item.name).symlink_to(item)
    (fake_harness / "lib").symlink_to(RAIZ / "lib")
    rel_copy = fake_harness / "bin" / "release"
    rel_copy.write_bytes(RELEASE_BIN.read_bytes())
    rel_copy.chmod(0o755)

    falhar_marker = tmp_path / "falhar_stack_b"
    falhar_marker.write_text("1", encoding="utf-8")
    stack_log = tmp_path / "stack_calls.log"

    stack_stub = fake_harness / "bin" / "_release" / "stack"
    stack_stub.write_text(
        f"""#!/usr/bin/env bash
ato="$1"
st="$2"
rev="${{3:-}}"
echo "$ato $st $rev" >> "{stack_log}"
if [ "$ato" = "testar" ]; then
  exit 0
fi
if [ "$ato" = "promover" ]; then
  if [ "$st" = "stack-b" ] && [ -f "{falhar_marker}" ]; then
    echo "erro simulado no container de stack-b" >&2
    exit 5
  fi
  mkdir -p "{instancia}/var/deploy"
  printf '%s\\n' "$rev" > "{instancia}/var/deploy/$st.atual"
  exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    stack_stub.chmod(0o755)

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    acervo_stub = stubs / "acervo"
    acervo_stub.write_text(
        """#!/usr/bin/env bash
if [[ "$*" == *"stack"* ]]; then
  cat <<'JSON'
[
  {"slug": "stack-a", "repo": "platafirma-demo", "compose": "a.yml", "reversao": {"via": "promover"}},
  {"slug": "stack-b", "repo": "platafirma-demo", "compose": "b.yml", "reversao": {"via": "promover"}}
]
JSON
  exit 0
fi
echo "[]"
exit 0
""",
        encoding="utf-8",
    )
    acervo_stub.chmod(0o755)

    familias = tmp_path / "familias.json"
    familias.write_text(json.dumps({repo: str(origem)}), encoding="utf-8")
    from _olaria_local import subir_olaria_local

    venvs = tmp_path / "venvs.json"
    venvs.write_text("{}", encoding="utf-8")
    _srv_olaria, env_olaria = subir_olaria_local()

    env = dict(os.environ)
    env.update(
        {
            **env_olaria,
            "PATH": f"{stubs}:{env.get('PATH', '')}",
            "PF_RELEASE_RAIZ": str(prod_raiz),
            "PLATAFIRMA_INSTANCIA": str(instancia),
            "PLATAFIRMA_FAMILIAS": str(familias),
            "PLATAFIRMA_VENVS": str(venvs),
            "PF_PROMOVER_VERBOSO": "1",
            "PF_RELEASE_PORTA": "0",
        }
    )

    try:
        yield AmbienteDt256(
            rel_copy=rel_copy,
            repo=repo,
            sha=sha,
            env=env,
            falhar_marker=falhar_marker,
            stack_log=stack_log,
        )
    finally:
        _chmod_rw(prod_raiz)


def test_dt256_promover_repetido_apos_promocao_parcial_retoma_stacks_pendentes(
    ambiente_dt256: AmbienteDt256,
) -> None:
    amb = ambiente_dt256
    r1 = _run([str(amb.rel_copy), "promover", amb.repo, amb.sha], amb.env)
    assert r1.returncode == EXIT_PARCIAL, (r1.stdout, r1.stderr)
    assert "PROMOCAO PARCIAL" in r1.stderr
    assert f"release promover {amb.repo} {amb.sha[:7]}" in r1.stderr
    assert "infra up stack-b -d --build --force-recreate" in r1.stderr

    amb.falhar_marker.unlink()
    amb.stack_log.write_text("", encoding="utf-8")
    r2 = _run([str(amb.rel_copy), "promover", amb.repo, amb.sha], amb.env)
    assert r2.returncode == 0, (r2.stdout, r2.stderr)
    assert "retomando stacks pendentes: stack-b" in r2.stdout
    assert f"no ar:     {amb.repo} {amb.sha[:7]}" in r2.stdout
    calls = amb.stack_log.read_text(encoding="utf-8").splitlines()
    assert calls == [f"promover stack-b {amb.sha}"]

    r3 = _run([str(amb.rel_copy), "promover", amb.repo, amb.sha], amb.env)
    assert r3.returncode == 1
    assert "já no ar:" in r3.stdout
