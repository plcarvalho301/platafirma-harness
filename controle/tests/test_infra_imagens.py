"""`infra imagens` e `infra limpeza imagens` (bin/_infra/imagens): separação entre imagens
Docker referenciadas por contêineres em produção e imagens inativas/órfãs, e poda reversível
em inspeção (--ver) ou efetiva (`docker image prune -a -f`).

Roda o bin/infra real com stubs de `docker` no PATH; nada toca o host.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or shutil.which("python3") is None,
    reason="sem bash ou python3 no PATH",
)

DOCKER_STUB = r"""#!/usr/bin/env bash
cmd="$1"; shift
case "$cmd" in
  ps)
    [ -z "${FAKE_PS_FALHA:-}" ] || { echo "Cannot connect to the Docker daemon" >&2; exit 1; }
    cat "$STUB_DIR/ps.jsonl" 2>/dev/null
    ;;
  images)
    [ -z "${FAKE_IMAGES_FALHA:-}" ] || { echo "Cannot connect to the Docker daemon" >&2; exit 1; }
    cat "$STUB_DIR/images.jsonl" 2>/dev/null
    ;;
  image)
    sub="$1"; shift
    if [ "$sub" = "prune" ]; then
      echo "image prune $*" >> "$STUB_DIR/rastro"
      [ -z "${FAKE_PRUNE_FALHA:-}" ] || { echo "prune error" >&2; exit 1; }
      cat "$STUB_DIR/inativas_ids" > "$STUB_DIR/removidas" 2>/dev/null || true
      echo "Total reclaimed space: 63.52GB"
      exit 0
    elif [ "$sub" = "rm" ]; then
      echo "image rm $*" >> "$STUB_DIR/rastro"
      [ -z "${FAKE_PRUNE_FALHA:-}" ] || { echo "rm error" >&2; exit 1; }
      exit 0
    fi
    echo "docker-stub: image sub desconhecido: $sub" >&2
    exit 1
    ;;
  builder)
    echo "builder $*" >> "$STUB_DIR/rastro"
    echo "Total: 256.7GB"
    ;;
  *)
    echo "docker-stub: comando nao coberto: $cmd $*" >&2
    exit 1
    ;;
esac
"""


class Cena:
    def __init__(self, tmp_path: Path) -> None:
        self.dir = tmp_path / "stub"
        self.bin = tmp_path / "bin"
        self.inst = tmp_path / "instancia"
        for p in (self.dir, self.bin, self.inst):
            p.mkdir(parents=True)
        docker = self.bin / "docker"
        docker.write_text(DOCKER_STUB, encoding="utf-8")
        docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
        uv = self.bin / "uv"
        uv.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
        for arq in ("ps.jsonl", "images.jsonl", "rastro", "inativas_ids"):
            (self.dir / arq).write_text("", encoding="utf-8")

    def conteiner(self, nome: str, imagem: str) -> None:
        with (self.dir / "ps.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"Names": nome, "Image": imagem}) + "\n")

    def imagem(self, ref: str, img_id: str, tamanho: str = "1.2GB", *, ativa: bool = False) -> None:
        repo, _, tag = ref.partition(":")
        with (self.dir / "images.jsonl").open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "Repository": repo,
                        "Tag": tag or "<none>",
                        "ID": img_id,
                        "Size": tamanho,
                        "CreatedSince": "9 days ago",
                    }
                )
                + "\n"
            )
        if not ativa:
            with (self.dir / "inativas_ids").open("a", encoding="utf-8") as f:
                f.write(img_id + "\n")

    def roda(self, *args: str, **env: str):
        e = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "STUB_DIR": str(self.dir),
            "PLATAFIRMA_INSTANCIA": str(self.inst),
        }
        e.update(env)
        return subprocess.run(
            [BASH, str(INFRA), *args],
            capture_output=True,
            text=True,
            env=e,
            timeout=30,
            check=False,
        )

    def rastro(self) -> list[str]:
        return (self.dir / "rastro").read_text(encoding="utf-8").splitlines()


@pytest.fixture
def cena(tmp_path: Path) -> Cena:
    c = Cena(tmp_path)
    c.conteiner("platafirma-core-keycloak-1", "quay.io/keycloak/keycloak:26.0")
    c.conteiner("rag-extractor-api", "sha256:1111111111112222222222223333333333334444444444445555555555556666")
    c.imagem("quay.io/keycloak/keycloak:26.0", "sha256:aaaa", "900MB", ativa=True)
    c.imagem(
        "platafirma-rag:current",
        "sha256:1111111111112222222222223333333333334444444444445555555555556666",
        "4.5GB",
        ativa=True,
    )
    c.imagem("platafirma-rag:velha", "sha256:bbbb", "4.2GB", ativa=False)
    c.imagem("<none>:<none>", "sha256:cccc", "500MB", ativa=False)
    return c


def test_imagens_separa_producao_de_inativas(cena: Cena):
    r = cena.roda("imagens")
    assert r.returncode == 0, r.stderr
    assert "== em produção (2 imagens, 5.40 GB)" in r.stdout
    assert "quay.io/keycloak/keycloak:26.0  [platafirma-core-keycloak-1]" in r.stdout
    assert "platafirma-rag:current  [rag-extractor-api]" in r.stdout
    assert "== fora de produção / recuperáveis (2 imagens, 4.70 GB)" in r.stdout
    assert "platafirma-rag:velha" in r.stdout
    assert "sha256:cccc" in r.stdout


def test_imagens_json_estruturado(cena: Cena):
    r = cena.roda("imagens", "--json")
    assert r.returncode == 0, r.stderr
    dado = json.loads(r.stdout)
    assert dado["resumo"]["em_uso_qtd"] == 2
    assert dado["resumo"]["inativas_qtd"] == 2
    assert [x["referencia"] for x in dado["em_uso"]] == [
        "platafirma-rag:current",
        "quay.io/keycloak/keycloak:26.0",
    ]
    assert [x["referencia"] for x in dado["inativas"]] == [
        "platafirma-rag:velha",
        "sha256:cccc",
    ]


def test_limpeza_imagens_ver_nao_apaga_nada(cena: Cena):
    r = cena.roda("limpeza", "imagens", "--ver")
    assert r.returncode == 0, r.stderr
    assert "sairia: platafirma-rag:velha" in r.stdout
    assert "sairia: sha256:cccc" in r.stdout
    assert "fica: platafirma-rag:current" in r.stdout
    assert "limpeza-imagens: 2 sairiam (~4.70 GB), 2 ficam" in r.stdout
    assert cena.rastro() == []


def test_limpeza_imagens_poda_e_grava_marca(cena: Cena):
    r = cena.roda("limpeza", "imagens")
    assert r.returncode == 0, r.stderr
    assert cena.rastro() == ["image prune -a -f"]
    assert "limpeza-imagens: 2 saíram (Total reclaimed space: 63.52GB), 2 ficam" in r.stdout
    marca = (cena.inst / "var" / "log" / "poda.log").read_text(encoding="utf-8")
    assert "limpeza-imagens: 2 saíram" in marca


def test_docker_fora_do_ar_sai_5(cena: Cena):
    r = cena.roda("imagens", FAKE_PS_FALHA="1")
    assert r.returncode == 5
    assert "docker ps não respondeu" in r.stderr


def test_limpeza_cache_poda_build_e_imagens(cena: Cena):
    r = cena.roda("limpeza", "cache")
    assert r.returncode == 0, r.stderr
    assert cena.rastro() == ["builder prune -a -f", "image prune -a -f"]


def test_opcao_desconhecida_sai_2(cena: Cena):
    assert cena.roda("imagens", "--bogus").returncode == 2
    assert cena.roda("limpeza", "imagens", "--bogus").returncode == 2


def test_biblioteca_current_protegida_do_expurgo(cena: Cena, tmp_path: Path):
    rel_raiz = tmp_path / "release"
    pkg = rel_raiz / "platafirma-ui" / "current" / "src" / "base" / "package.json"
    pkg.parent.mkdir(parents=True)
    pkg.write_text(json.dumps({"version": "0.22.0"}), encoding="utf-8")
    cena.imagem("platafirma/ui:0.22.0", "sha256:ui0220", "120MB", ativa=False)

    r_list = cena.roda("imagens", PF_RELEASE_RAIZ=str(rel_raiz))
    assert r_list.returncode == 0, r_list.stderr
    assert "== em produção (3 imagens" in r_list.stdout
    assert "platafirma/ui:0.22.0  [biblioteca:current]" in r_list.stdout

    r_prune = cena.roda("limpeza", "imagens", PF_RELEASE_RAIZ=str(rel_raiz))
    assert r_prune.returncode == 0, r_prune.stderr
    rastro = cena.rastro()
    assert len(rastro) == 1
    assert rastro[0].startswith("image rm -f ")
    assert "platafirma/ui:0.22.0" not in rastro[0]
    assert "platafirma-rag:velha" in rastro[0]
