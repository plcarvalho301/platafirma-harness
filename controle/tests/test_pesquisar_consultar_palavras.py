"""`pesquisar consultar` com a consulta em palavras soltas (#2856 linha 104).

Antes, `pesquisar consultar context engineering agents` consultava só «context» e saia 0, sem
aviso. Agora as palavras viram uma consulta so. O despachante roda de verdade, como subprocesso,
com `pesquisa.atos.consultar` trocado por um registrador: nao ha SearXNG, rede nem manifesto.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

CODIGO = """
import importlib.machinery, importlib.util, json, sys
raiz = sys.argv[1]
sys.path.insert(0, raiz)
from pesquisa import atos
chamadas = []
atos.consultar = lambda consulta, **kw: (chamadas.append(consulta) or {"ok": True})
carregador = importlib.machinery.SourceFileLoader("pesquisar_bin", raiz + "/bin/pesquisar")
spec = importlib.util.spec_from_loader("pesquisar_bin", carregador)
modulo = importlib.util.module_from_spec(spec)
carregador.exec_module(modulo)
rc = modulo.main(["pesquisar", "consultar", *sys.argv[2:]])
print(json.dumps({"rc": rc, "consultas": chamadas}))
"""


def _consultar(tmp_path: Path, *argumentos: str) -> dict:
    env = {**os.environ, "PF_PESQUISA_DIR": str(tmp_path / "pesquisa")}
    r = subprocess.run([sys.executable, "-c", CODIGO, str(RAIZ), *argumentos],
                       capture_output=True, text=True, env=env, timeout=60, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_palavras_soltas_viram_uma_consulta_so(tmp_path):
    saida = _consultar(tmp_path, "context", "engineering", "agents")
    assert saida == {"rc": 0, "consultas": ["context engineering agents"]}


def test_consulta_em_um_argumento_segue_igual(tmp_path):
    saida = _consultar(tmp_path, "context engineering agents")
    assert saida == {"rc": 0, "consultas": ["context engineering agents"]}


def test_flag_depois_das_palavras_nao_entra_na_consulta(tmp_path):
    saida = _consultar(tmp_path, "context", "engineering", "-k", "3")
    assert saida["consultas"] == ["context engineering"]
