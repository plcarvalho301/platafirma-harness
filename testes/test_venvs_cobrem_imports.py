"""O venv que o release constroi cobre o que o codigo servido importa (card #3010).

O venv `ops` nasce de ops-server/requirements.txt (registro/venvs.json). Um import de
terceiro que so existia no venv montado a mao derruba a porta na primeira subida de uma
release limpa. Este teste le os imports de ops-server/*.py (fora dos testes) e exige que
cada distribuicao de terceiro esteja declarada no arquivo que o registro aponta.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# modulo importado -> distribuicao que o fornece
DISTRIBUICAO = {"yaml": "pyyaml"}
# chegam como dependencia de uma distribuicao declarada
TRANSITIVOS = {"anyio": "mcp", "starlette": "mcp"}
# modulos da propria arvore que a porta poe no sys.path
LOCAIS_FORA_DO_DIRETORIO = {"hash_servido", "streams", "identidade", "pdp", "pep", "raizes"}


def _imports_de_terceiros(diretorio: Path) -> set[str]:
    locais = {p.stem for p in diretorio.glob("*.py")} | LOCAIS_FORA_DO_DIRETORIO
    achados: set[str] = set()
    for arquivo in diretorio.glob("*.py"):
        if arquivo.name.startswith("test_"):
            continue
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if isinstance(no, ast.Import):
                achados |= {a.name.split(".")[0] for a in no.names}
            elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
                achados.add(no.module.split(".")[0])
    return {m for m in achados if m not in sys.stdlib_module_names and m not in locais}


def _declarados(requirements: Path) -> set[str]:
    nomes = set()
    for linha in requirements.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if linha:
            nomes.add(re.split(r"[\[=<>!~ ]", linha, maxsplit=1)[0].lower())
    return nomes


def test_venv_ops_cobre_os_imports_da_porta():
    registro = json.loads((RAIZ / "registro" / "venvs.json").read_text(encoding="utf-8"))
    requirements = RAIZ / registro["ops"]["lock"]
    declarados = _declarados(requirements)
    faltam = []
    for modulo in sorted(_imports_de_terceiros(RAIZ / "ops-server")):
        dist = DISTRIBUICAO.get(modulo, modulo).lower()
        if dist in declarados or TRANSITIVOS.get(modulo, "") in declarados:
            continue
        faltam.append(f"{modulo} (distribuicao {dist})")
    assert not faltam, f"{requirements.relative_to(RAIZ)} nao declara: {', '.join(faltam)}"


def test_requirements_do_ops_e_pinado():
    registro = json.loads((RAIZ / "registro" / "venvs.json").read_text(encoding="utf-8"))
    requirements = RAIZ / registro["ops"]["lock"]
    soltos = [
        linha.strip()
        for linha in requirements.read_text(encoding="utf-8").splitlines()
        if linha.strip() and not linha.strip().startswith("#") and "==" not in linha
    ]
    assert not soltos, f"dependencia sem versao pinada em {requirements.name}: {soltos}"
