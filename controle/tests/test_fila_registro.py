"""O cabecalho de bin/fila se registra no golden record, com o contestar da face motor (#3518, buraco #2555).

Ate 15/10/2026 a linha `# escreve:` da fila era prosa, sem `<ato>=<recurso>`, e `acervo registrar fila` saia 3: a
fila nunca tinha entrado no registro do ferramental, e o retrato da Taipa nao tinha o `fila contestar` que a face
pede. Hermetico: o psql e um duble que guarda o SQL. Nao prova que o psql real aceita (FK de recurso).
"""

from __future__ import annotations

import importlib.util
import re
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
loader = SourceFileLoader("registrar_fila", str(REPO_ROOT / "bin" / "_acervo" / "registrar"))
spec = importlib.util.spec_from_loader("registrar_fila", loader)
assert spec and spec.loader
registrar = importlib.util.module_from_spec(spec)
loader.exec_module(registrar)

ATOS = ["status", "ler", "tratar", "enviar", "tipos", "contestar"]
# os ids de acervo.ferramental_recurso: a FK reprova qualquer outro
RECURSOS = {"acervo.obra", "acervo.casa", "acervo.registro", "acervo.*", "release", "repo", "rastreador", "malha",
            "motor", "arquivo-local", "nada", "minio", "sessao.preferencia_sujeito"}


@pytest.fixture
def sql(monkeypatch):
    enviados: list[str] = []

    def _psql(s, escreve=False):
        enviados.append(s)
        return ""

    monkeypatch.setattr(registrar, "_psql", _psql)
    cap, desc = registrar.registrar_um("fila")
    return cap, desc, "".join(enviados)


def test_a_fila_registra_com_os_seis_atos(sql):
    cap, desc, texto = sql
    assert cap == "mensagem"
    registrados = re.findall(r"into acervo\.ferramental_ato \(verbo, ato, capacidade, acao, tipo[^)]*\) "
                             r"values \('fila', '([^']+)'", texto)
    assert registrados == ATOS


def test_cada_ato_declara_le_e_escreve_com_recurso_do_enum(sql):
    acessos = re.findall(r"into acervo\.ferramental_acesso \(verbo, ato, recurso_id, modo\) values "
                         r"\('fila', '([\w-]+)', '([^']+)', '(le|escreve)'\)", sql[2])
    assert {r for _, r, _ in acessos} <= RECURSOS
    for ato in ATOS:
        assert {m for a, _, m in acessos if a == ato} == {"le", "escreve"}, f"{ato}: uma linha le e uma escreve"


def test_o_contestar_registra_rotulo_e_volta(sql):
    assert re.search(r"values \('fila', 'contestar', '[^']+', '[^']+', '[^']+', 'Contestar o indicador', 'nao', null\)",
                     sql[2])
    # o enviar geral nao ganha controle de face
    assert re.search(r"values \('fila', 'enviar', '[^']+', '[^']+', '[^']+', null, null, null\)", sql[2])
