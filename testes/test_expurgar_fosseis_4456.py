"""Regressão do incidente #4456: expurgar_fosseis preserva árvore usada por contêiner."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[1]
BIN_RELEASE = RAIZ_REPO / "bin" / "release"
SHA_ATUAL = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHA_EM_USO = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
SHA_LIVRE = "cccccccccccccccccccccccccccccccccccccccc"


def _criar_docker_falso(bin_dir: Path, origem_bind: Path) -> None:
    """Cria um stub de `docker` que reporta um contêiner `searxng` montando `origem_bind`."""
    inspecao = [
        {
            "Id": "abc123",
            "Name": "/searxng",
            "Config": {
                "Labels": {
                    "com.docker.compose.project.working_dir": str(origem_bind.parent),
                }
            },
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": str(origem_bind),
                    "Destination": "/etc/searxng/settings.yml",
                }
            ],
        }
    ]
    script = bin_dir / "docker"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "ps" ]; then\n'
        "  echo abc123\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "inspect" ]; then\n'
        f"  cat <<'JSON'\n{json.dumps(inspecao)}\nJSON\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _montar_cenario_release(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """Monta PF_RELEASE_RAIZ temporário com três revisões e stub de docker."""
    prod = tmp_path / "opt"
    inst = tmp_path / "srv"
    core = prod / "platafirma-core"
    for sha in (SHA_ATUAL, SHA_EM_USO, SHA_LIVRE):
        (core / sha / "deploy" / "searxng").mkdir(parents=True)
    settings_em_uso = core / SHA_EM_USO / "deploy" / "searxng" / "settings.yml"
    settings_em_uso.write_text("use_default_settings: true\n", encoding="utf-8")
    (core / "current").symlink_to(SHA_ATUAL)

    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    _criar_docker_falso(bin_falso, settings_em_uso)

    env = os.environ.copy()
    env.update(
        {
            "PF_RELEASE_RAIZ": str(prod),
            "PLATAFIRMA_INSTANCIA": str(inst),
            "PF_RELEASE_EXPURGO_DOCKER": "0",
            "PF_EXPURGO_SEM_PROC": "1",
            "PATH": f"{bin_falso}:{env.get('PATH', '')}",
        }
    )
    return core, settings_em_uso, env


def test_expurgar_fosseis_preserva_arvore_em_uso_por_conteiner(tmp_path: Path) -> None:
    """Árvore antiga montada por contêiner vivo (ex.: searxng) não pode ser apagada (#4456)."""
    core, settings_em_uso, env = _montar_cenario_release(tmp_path)
    proc = subprocess.run(
        [str(BIN_RELEASE), "expurgar"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert (core / SHA_ATUAL).is_dir()
    assert (core / SHA_EM_USO).is_dir(), "árvore em uso pelo contêiner searxng foi apagada!"
    assert settings_em_uso.is_file()
    assert not (core / SHA_LIVRE).exists(), "árvore sem uso devia ter sido expurgada"
    assert "contêiner searxng" in proc.stdout
