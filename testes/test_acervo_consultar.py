"""`acervo consultar` removido por ordem do dono (13/11/2026).

O ato lia o schema casa antigo, apagado no #4211, e so devolvia erro cru de SQL. A rota recusa com
exit 2 e diz onde a resposta mora (a shape da entidade no espelho), sem chamar docker nem banco; o
cabecalho do verbo deixa de anunciar o ato, para a porta nao o servir.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACERVO = RAIZ / "bin" / "acervo"

DOCKER_DELATOR = "#!/usr/bin/env bash\ntouch \"$DOCKER_LOG\"\nexit 97\n"


def _acervo(*argv, tmp_path: Path):
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir(exist_ok=True)
    docker = bin_falso / "docker"
    docker.write_text(DOCKER_DELATOR, encoding="utf-8")
    docker.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_falso}{os.pathsep}{os.environ.get('PATH', '')}",
           "DOCKER_LOG": str(tmp_path / "docker-chamado")}
    return subprocess.run(["bash", str(ACERVO), "consultar", *argv], capture_output=True, text=True,
                          env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)


def test_consultar_recusa_com_exit_2_e_aponta_a_shape(tmp_path):
    for argv in (("casa", "onde-mora", "persona"), ("casa", "documento", "postura"), ()):
        r = _acervo(*argv, tmp_path=tmp_path)
        assert r.returncode == 2, (argv, r.stderr)
        assert "removido por ordem do dono" in r.stderr
        assert "shapes/entidade/<slug>.ttl" in r.stderr
        assert "repo ler platafirma-casa-espelho" in r.stderr
    assert not (tmp_path / "docker-chamado").exists()


def test_cabecalho_e_usage_nao_anunciam_o_ato():
    texto = ACERVO.read_text(encoding="utf-8")
    cabecalho = "\n".join(l for l in texto.splitlines() if l.startswith("# "))
    assert "consultar (leitura" not in cabecalho
    assert "consultar=" not in cabecalho
    assert "acervo consultar casa <pergunta>" not in texto
    assert "pipeline, consultar," not in texto


def test_sub_ato_saiu_da_arvore():
    assert not (RAIZ / "bin" / "_acervo" / "consultar").exists()
