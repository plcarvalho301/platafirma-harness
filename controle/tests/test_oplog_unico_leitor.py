"""Fora de lib/oplog.py ninguem abre o bruto da porta (card #3344, arq:0123 §3).

«O teste da suite reprova acesso a `var/log/ops` fora dele»: o diretorio do bruto, o nome do
arquivo do dia e as variaveis que o apontam (`OPS_LOG_DIR` e os dois aliases) so aparecem em
codigo dentro de `lib/oplog.py`. Comentario e docstring nao contam; teste, ensaio e bench
tambem nao (leem o arquivo para provar o que a porta gravou). A excecao que fica e declarada
abaixo, com o motivo, e uma excecao que nao casa mais reprova.
"""
import ast
import io
import re
import tokenize
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ESCOPO = ("bin", "lib", "ops-server")
DONO = "lib/oplog.py"

PADRAO = re.compile(
    r"OPS_LOG_DIR|PF_LOG_OPS|PF_OPS_LOG_DIR|var/log/ops|"
    r"""["']var["']\s*/\s*["']log["']\s*/\s*["']ops["']|ops-\*\.jsonl|ops-\{|ops-%""")

# Excecao declarada: arquivo -> por que ele nao abre o bruto de verdade.
EXCECOES = {
    "bin/_infra/limpeza-logs": "so conta o nome e a idade dos arquivos de var/log/ops para a linha "
                               "de vida (#3343); nao le conteudo e nao apaga (arq:0123 §12)",
}


def _eh_python(caminho: Path, texto: str) -> bool:
    return caminho.suffix == ".py" or texto.startswith("#!") and "python" in texto.splitlines()[0]


def _sem_comentario_nem_docstring_py(texto: str) -> str:
    linhas = texto.splitlines()
    for no in ast.walk(ast.parse(texto)):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            corpo = no.body
            if (corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant)
                    and isinstance(corpo[0].value.value, str)):
                for n in range(corpo[0].lineno - 1, corpo[0].end_lineno):
                    linhas[n] = ""
    limpo = "\n".join(linhas) + "\n"
    # remove so o trecho do comentario de cada linha, mantendo o resto do codigo
    por_linha = limpo.splitlines()
    for tok in tokenize.generate_tokens(io.StringIO(limpo).readline):
        if tok.type == tokenize.COMMENT:
            n, col = tok.start
            por_linha[n - 1] = por_linha[n - 1][:col]
    return "\n".join(por_linha)


def _sem_comentario_sh(texto: str) -> str:
    return "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))


def achados(caminho: Path, texto: str) -> list[str]:
    """As linhas de CODIGO do arquivo que citam o bruto da porta."""
    try:
        codigo = (_sem_comentario_nem_docstring_py(texto) if _eh_python(caminho, texto)
                  else _sem_comentario_sh(texto))
    except (SyntaxError, tokenize.TokenError):
        codigo = _sem_comentario_sh(texto)
    return [f"{n}: {l.strip()[:100]}" for n, l in enumerate(codigo.splitlines(), 1) if PADRAO.search(l)]


def _fontes():
    for pasta in ESCOPO:
        for arq in sorted((RAIZ / pasta).rglob("*")):
            rel = arq.relative_to(RAIZ).as_posix()
            if (not arq.is_file() or arq.is_symlink() or "__pycache__" in arq.parts
                    or "bench" in arq.parts or rel == DONO or arq.name.startswith("test_")
                    or arq.name in ("_ensaio.py", "VERDES") or arq.suffix in (".md", ".json", ".txt")):
                continue
            try:
                texto = arq.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            yield rel, arq, texto


def test_so_o_oplog_abre_o_bruto_da_porta():
    violacoes = {}
    for rel, arq, texto in _fontes():
        if rel in EXCECOES:
            continue
        if (a := achados(arq, texto)):
            violacoes[rel] = a
    assert not violacoes, (
        "fora de lib/oplog.py ninguem abre var/log/ops nem OPS_LOG_DIR (arq:0123 §3); "
        "leia por `oplog.ler` e escreva por `oplog.emitir`:\n"
        + "\n".join(f"  {k}: {v}" for k, v in violacoes.items()))


def test_excecao_declarada_ainda_casa():
    fontes = {rel: (arq, texto) for rel, arq, texto in _fontes()}
    for rel, motivo in EXCECOES.items():
        assert rel in fontes, f"excecao a um arquivo que nao existe mais: {rel}"
        assert achados(*fontes[rel]), f"{rel} nao cita mais o bruto: tire a excecao ({motivo})"


def test_escritores_e_leitores_chamam_o_modulo():
    chamam = {
        "ops-server/server.py": "oplog.emitir(",
        "bin/motor": "oplog.emitir(",
        "bin/metrica": "oplog.ler(",
        "bin/descansar": "oplog.ler(",
        "bin/_acesso/desligar.py": "oplog.ler(",
        "bin/repo": "python3 -m oplog ler",
    }
    for rel, uso in chamam.items():
        assert uso in (RAIZ / rel).read_text(encoding="utf-8"), f"{rel} devia chamar {uso}"


# --- o detector -------------------------------------------------------------------------

@pytest.mark.parametrize("codigo", [
    'import glob\nglob.glob("/srv/platafirma/casa/var/log/ops/ops-*.jsonl")\n',
    'import os\nd = os.environ.get("OPS_LOG_DIR")\n',
    'p = instancia() / "var" / "log" / "ops"\n',
    'x = os.environ.get("PF_LOG_OPS", "")\n',
])
def test_detector_pega_python_que_abre_o_bruto(codigo):
    assert achados(Path("x.py"), codigo)


def test_detector_pega_shell_que_abre_o_bruto():
    assert achados(Path("verbo"), '#!/usr/bin/env bash\nlog_dir="${OPS_LOG_DIR:-$I/var/log/ops}"\n')


def test_detector_ignora_comentario_e_docstring():
    py = ('#!/usr/bin/env python3\n# le OPS_LOG_DIR e var/log/ops\n'
          '"""docstring que cita var/log/ops e ops-*.jsonl"""\n'
          'def f():\n    """cita OPS_LOG_DIR"""\n    return 1  # var/log/ops\n')
    assert achados(Path("v"), py) == []
    assert achados(Path("v.sh"), "#!/bin/sh\n# OPS_LOG_DIR\necho ok\n") == []


def test_detector_nao_ignora_texto_de_uso_que_nao_e_docstring():
    codigo = 'def uso():\n    print("le o log em var/log/ops")\n'
    assert achados(Path("x.py"), codigo)
