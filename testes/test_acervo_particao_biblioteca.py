"""#3197: a partição `obra` passa a `biblioteca` (arq:0106 §2, emendada em 29/09).

A forma nova roteia; `obra` como partição segue servindo, com aviso em stderr que nomeia
`biblioteca` (arq:0084). Os casos usam ramos do despachante que não chamam o motor nem o
banco: a ajuda, a recusa de partição desconhecida e a recusa de `escrever` na biblioteca.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACERVO = RAIZ / "bin" / "acervo"


def _acervo(*argv, sessao: str):
    # o aviso sai uma vez por sessao (trava em /tmp): cada chamada leva sessao nova
    env = {**os.environ, "PF_SESSAO_ID": f"{sessao}-{uuid.uuid4().hex}"}
    return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True,
                          env=env, timeout=30, check=False)


def test_ajuda_lista_biblioteca_casa_registro(tmp_path):
    r = _acervo("--ajuda", sessao=f"t-ajuda-{tmp_path.name}")
    assert r.returncode == 2
    assert "as particoes: biblioteca, casa, registro" in r.stderr
    assert "acervo ler      biblioteca impressao <obra>" in r.stderr


def test_particao_desconhecida_devolve_o_vocabulario_novo(tmp_path):
    r = _acervo("ler", "livro", "obra", "x", sessao=f"t-desc-{tmp_path.name}")
    assert r.returncode == 2
    assert "(biblioteca, casa, registro)" in r.stderr


def test_forma_nova_roteia_sem_aviso(tmp_path):
    r = _acervo("escrever", "biblioteca", "obra", "x", sessao=f"t-nova-{tmp_path.name}")
    assert r.returncode == 2
    assert "acervo ingerir biblioteca <raiz>" in r.stderr
    assert "forma vigente" not in r.stderr


def test_forma_velha_serve_com_aviso_que_nomeia_biblioteca(tmp_path):
    r = _acervo("escrever", "obra", "obra", "x", sessao=f"t-velha-{tmp_path.name}")
    assert r.returncode == 2
    assert "`acervo escrever obra` e a forma vigente" in r.stderr
    assert "`acervo escrever biblioteca`" in r.stderr
    # caiu no mesmo ramo da forma nova
    assert "acervo ingerir biblioteca <raiz>" in r.stderr
