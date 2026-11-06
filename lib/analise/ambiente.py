"""Ambiente por lock com o construtor da casa, sempre sem dado ou segredo."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import Falha, exigir, hash_arquivo
from .unidade import executar

RAIZ = Path(__file__).resolve().parents[2]


def construir(pasta: Path, cache: Path) -> tuple[Path, dict]:
    validar_projeto(pasta)
    lock = pasta / "uv.lock"
    exigir(lock.is_file(), "lock-ausente", 3)
    import tomllib

    dados = tomllib.loads(lock.read_text())
    for pacote in dados.get("package", []):
        source = pacote.get("source", {})
        exigir(
            "registry" in source or source.get("virtual") == ".",
            "dependencia-fora-do-indice",
            4,
        )
        if "registry" in source:
            exigir(
                pacote.get("wheels")
                and all(
                    w.get("hash", "").startswith("sha256:") for w in pacote["wheels"]
                ),
                "pacote-sem-wheel:" + pacote["name"],
            )
    chave = hashlib.sha256(lock.read_bytes() + sys_identidade().encode() + Path(__file__).read_bytes()).hexdigest()[
        :24
    ]
    destino = cache / chave
    if not (destino / "bin/python").exists():
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            stage = Path(tmp) / "receita"
            stage.mkdir()
            out = Path(tmp) / "saida"
            out.mkdir()
            shutil.copy2(lock, stage / "uv.lock")
            shutil.copy2(pasta / "pyproject.toml", stage / "pyproject.toml")
            shutil.copy2(RAIZ / "lib/venv.sh", stage / "venv.sh")
            (stage / "construir.sh").write_text(
                'set -eu\n. /receita/venv.sh\nuv="$(resolver_uv)"\n'
                'info="$(resolver_python)"\npy="$(printf "%s" "$info" | cut -f1)"\n'
                'ver="$(printf "%s" "$info" | cut -f3)"\n'
                "export UV_NO_BUILD=1\n"
                'construir_venv /receita/uv.lock /saida/venv "$uv" "$py" "$ver"\n'
            )
            rc, _ = executar(
                ["/bin/bash", "/receita/construir.sh"],
                pasta=stage,
                saida=out,
                rede=True,
            )
            exigir(rc == 0, "ambiente-nao-se-reconstroi", 3)
            if any(p.get("name")=="matplotlib" for p in dados.get("package",[])):
                fontes=Path(tmp)/"fontes";fontes.mkdir()
                rc,_=executar([str(out/"venv/bin/python"),"-I","-B","-c",
                    "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.figure(); plt.close('all')"],
                    pasta=stage,saida=fontes,ambiente=out/"venv")
                exigir(rc==0,"fontes-graficas-indisponiveis",3)
                shutil.copytree(fontes/".mpl",out/"venv/analise-mpl")
            try:
                (out / "venv").rename(destino)
            except FileExistsError:
                pass
    proc = subprocess.run(
        [
            str(destino / "bin/python"),
            "-I",
            "-c",
            "import importlib.metadata as m,json,platform; print(json.dumps({'python':platform.python_version(),'plataforma':platform.platform(),'pacotes':sorted((d.metadata['Name'],d.version) for d in m.distributions())}))",
        ],
        capture_output=True,
        check=False,
        text=True,
        close_fds=True,
        timeout=20,
        env={"PATH": "/usr/bin:/bin"},
    )
    exigir(proc.returncode == 0, "identidade-ambiente-indisponivel", 3)
    identidade = json.loads(proc.stdout)
    identidade.update(
        {
            "lock_sha256": hash_arquivo(lock),
            "uv": subprocess.run(
                ["/usr/local/bin/uv", "--version"],
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            ).stdout.strip(),
            "imagem": None,
            "tipo_ambiente": "systemd-host",
            "artefato": hashlib.sha256(b"".join(f.read_bytes() for f in sorted(Path(__file__).parent.glob("*.py")))).hexdigest(),
            "python_sha256": hash_arquivo(Path("/usr/bin/python3.12")),
            "nativas": {
                str(p.relative_to(destino)): hash_arquivo(p)
                for p in sorted(destino.rglob("*.so*"))
                if p.is_file()
            },
            "sistema_nativo": hash_arquivo(Path("/etc/ld.so.cache")),
            "fontes": hashlib.sha256(
                b"".join(
                    p.read_bytes()
                    for p in sorted(Path("/usr/share/fonts").rglob("*"))
                    if p.is_file()
                )
            ).hexdigest(),
            "blas_lapack": {
                str(p.relative_to(destino)): hash_arquivo(p)
                for p in sorted(destino.rglob("*.so*"))
                if p.is_file() and any(t in str(p).lower() for t in ("blas", "lapack"))
            },
            "graphviz": shutil.which("dot") or None,
        }
    )
    return destino, identidade


def sys_identidade() -> str:
    return platform.python_version() + " " + platform.platform()


def travar(pasta: Path, cache: Path) -> str:
    validar_projeto(pasta)
    exigir((pasta / "pyproject.toml").is_file(), "pyproject-ausente")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        stage = Path(tmp) / "receita"
        stage.mkdir()
        out = Path(tmp) / "saida"
        out.mkdir()
        shutil.copy2(pasta / "pyproject.toml", stage / "pyproject.toml")
        (stage / "travar.sh").write_text(
            "set -eu\nmkdir /saida/projeto\ncp /receita/pyproject.toml /saida/projeto/\n"
            "uv=/usr/local/bin/uv\n"
            '"$uv" lock --no-build --python /usr/bin/python3.12 --project /saida/projeto 2>/saida/erro\n'
            '"$uv" sync --frozen --no-build --no-dev --no-install-project --python /usr/bin/python3.12 --project /saida/projeto 2>>/saida/erro\n'
        )
        rc, _ = executar(
            ["/bin/bash", "/receita/travar.sh"], pasta=stage, saida=out, rede=True
        )
        if rc:
            erro = (out / "erro").read_text() if (out / "erro").exists() else ""
            rede = any(
                x in erro.lower()
                for x in ("failed to download", "connection", "dns", "network")
            )
            import re
            import tomllib

            dependencias = (
                tomllib.loads((pasta / "pyproject.toml").read_text())
                .get("project", {})
                .get("dependencies", [])
            )
            nomes = [re.match(r"[A-Za-z0-9_.-]+", d).group() for d in dependencias]
            pacote = next(
                (n for n in nomes if n.lower() in erro.lower()),
                ",".join(nomes) or "pyproject",
            )
            raise Falha(
                3 if rede else 2,
                "indice-fora-do-alcance"
                if rede
                else "dependencia-sem-wheel-ou-incompativel:" + pacote,
            )
        lock = out / "projeto/uv.lock"
        exigir(lock.is_file(), "lock-nao-gerado", 3)
        import tomllib

        for p in tomllib.loads(lock.read_text()).get("package", []):
            if "registry" in p.get("source", {}):
                exigir(
                    p.get("wheels")
                    and all("sha256:" in w.get("hash", "") for w in p["wheels"]),
                    "pacote-sem-wheel:" + p["name"],
                )
        shutil.copy2(lock, pasta / "uv.lock")
    return hash_arquivo(pasta / "uv.lock")


def validar_projeto(pasta: Path) -> None:
    """O resolvedor só recebe nomes do índice; nenhuma fonte executável."""
    import re
    import tomllib

    try:
        projeto = tomllib.loads((pasta / "pyproject.toml").read_text())
    except FileNotFoundError:
        raise Falha(2, "pyproject-ausente") from None
    for dep in projeto.get("project", {}).get("dependencies", []):
        exigir(
            isinstance(dep, str)
            and re.match(
                r"^[a-zA-Z0-9_.-]+(?:\[[a-zA-Z0-9_,.-]+\])?(?:[ <>=!~;].*)?$", dep
            )
            and "@" not in dep
            and "://" not in dep,
            "dependencia-fora-do-indice",
        )
    uv = projeto.get("tool", {}).get("uv", {})
    exigir(
        not any(
            k in uv
            for k in ("sources", "index", "index-url", "extra-index-url", "find-links")
        ),
        "indice-nao-autorizado",
    )
