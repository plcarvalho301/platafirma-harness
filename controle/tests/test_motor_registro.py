"""O cabecalho de bin/motor se registra no golden record e a descricao servida ensina a consulta montada (#3364).

A descricao que a porta serve em tools/list sai de acervo.ferramental_verbo, que `acervo registrar motor` compoe do
cabecalho. Ate 08/10/2026 o registrar recusava o motor (segunda linha `# atos:` em prosa e `# escreve:` sem
`<ato>=<recurso>`), e a descricao servida era a de antes do #3360: `buscar <particao> "<pergunta>"`, sem frase nem
`--necessidade`. Hermetico: o psql e um duble que guarda o SQL. Nao prova que o psql real aceita (FK de recurso).
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
loader = SourceFileLoader("registrar", str(REPO_ROOT / "bin" / "_acervo" / "registrar"))
spec = importlib.util.spec_from_loader("registrar", loader)
assert spec and spec.loader
registrar = importlib.util.module_from_spec(spec)
loader.exec_module(registrar)

MOTOR = REPO_ROOT / "bin" / "motor"
ATOS = ["listar", "ajuste", "buscar", "medir", "indexar", "trocar", "sortear", "lintar", "parear", "escrever", "julgar",
        "eleger", "consultas", "trabalhos"]   # julgar: #3350; consultas e trabalhos: #3513
# os 11 ids de acervo.ferramental_recurso (047): a FK reprova qualquer outro
RECURSOS = {"acervo.obra", "acervo.casa", "acervo.registro", "acervo.*", "release", "repo", "rastreador", "malha",
            "motor", "arquivo-local", "nada"}


# o tesauro do duble: os conceitos que o objeto do rotulo cita (#3448). O real e acervo.conceito.
# ajuste e obra entram pela carta de produto a dados (#3448, comentario #2218); ate existirem no
# tesauro real, o registro do motor recusa com exit 3, como o teste de baixo prova.
TESAURO = {"ajuste", "embeddings", "obra"}


def _psql_duble(enviados):
    def _psql(s, escreve=False):
        enviados.append(s)
        if "join acervo.conceito" in s:
            return "\n".join(sorted(x for x in re.findall(r"\('([a-z0-9-]+)'\)", s) if x in TESAURO))
        return ""
    return _psql


@pytest.fixture
def sql(monkeypatch):
    enviados: list[str] = []
    monkeypatch.setattr(registrar, "_psql", _psql_duble(enviados))
    cap, desc = registrar.registrar_um("motor")
    return cap, desc, "".join(enviados)


def test_os_atos_de_face_registram_rotulo_e_volta(sql):
    """#3448 e #3532: os atos de face declaram rotulo e volta; o trocar declara um controle por modo."""
    texto = sql[2]
    for rotulo in ("Aplicar {ajuste}", "Indexar {obra} pendente", "Buscar no acervo", "Medir o acerto da busca",
                   "Listar instancias do motor", "Listar consultas a busca", "Listar trabalhos longos do motor",
                   "Montar geracao em sombra com outro modelo de {embeddings}", "Virar a geracao em sombra"):
        assert rotulo in texto, rotulo
    assert "sim — motor rag ajuste <slug> <valor anterior>" in texto
    assert "sim — sem --promover o indice fica fora do ar" in texto


def _linhas_do_cabecalho():
    return [l.strip() for l in MOTOR.read_text(encoding="utf-8").splitlines() if l.startswith("# ")]


def _chaves(campo):
    padrao = re.compile(rf"^#\s*{campo}\s*:\s*([A-Za-z0-9_-]+(?: --[A-Za-z0-9_-]+)?)\s*=")
    return [m.group(1) for l in _linhas_do_cabecalho() if (m := padrao.match(l))]


def test_a_face_cobre_os_atos_da_emenda_e_deixa_a_exclusao_de_fora():
    """#3532 (arq:0124 §3): buscar, medir, listar, ajuste, indexar, trocar, consultas e trabalhos tem face;
    sortear, parear, escrever, julgar, lintar e eleger ficam na exclusao "instrumento de medida da ia"."""
    faces = _chaves("face")
    assert sorted(faces) == sorted(["buscar", "medir", "listar", "ajuste", "indexar", "trocar", "consultas", "trabalhos"])
    for excluido in ("sortear", "parear", "escrever", "julgar", "lintar", "eleger"):
        assert excluido not in faces
    assert all(f in ATOS for f in faces)


def test_todo_controle_tem_rotulo_e_volta_e_o_trocar_vem_por_modo():
    rotulos, voltas = _chaves("rotulo"), _chaves("volta")
    assert sorted(rotulos) == sorted(voltas)
    assert "trocar" not in rotulos and sorted(r for r in rotulos if r.startswith("trocar ")) == [
        "trocar --embedder", "trocar --virar"]
    # cada ato de face tem o controle dele, ou o de cada modo
    for ato in _chaves("face"):
        assert any(r == ato or r.startswith(ato + " --") for r in rotulos), ato


def test_o_registro_grava_um_controle_por_modo_do_trocar(sql):
    texto = sql[2]
    assert re.search(r"values \('motor', 'trocar --embedder', '[^']+', '[^']+', '[^']+', "
                     r"'Montar geracao em sombra com outro modelo de \{embeddings\}', "
                     r"'sim — motor rag trocar biblioteca --descartar <id> desfaz a sombra enquanto ela nao virou', null\)",
                     texto)
    assert re.search(r"values \('motor', 'trocar --virar', '[^']+', '[^']+', '[^']+', "
                     r"'Virar a geracao em sombra', 'nao', null\)", texto)
    # o ato puro segue como linha do registro, sem texto de controle inventado
    assert re.search(r"values \('motor', 'trocar', '[^']+', '[^']+', '[^']+', null, null, null\)", texto)


def test_slug_fora_do_tesauro_recusa_o_registro(monkeypatch):
    monkeypatch.setattr(registrar, "_psql", lambda s, escreve=False: "")
    with pytest.raises(SystemExit) as e:
        registrar.registrar_um("motor")
    assert e.value.code == 3


def test_a_descricao_servida_ensina_a_necessidade_em_frase(sql):
    cap, desc, _ = sql
    assert cap == "motor"
    assert desc.startswith("busca semantica sobre uma particao do acervo")
    assert "--necessidade" in desc and "saco de palavras" in desc
    assert '"<pergunta>"' not in desc, "a forma de antes do #3360 nao volta"


def test_os_atos_sao_so_os_do_verbo(sql):
    texto = sql[2]
    registrados = re.findall(r"into acervo\.ferramental_ato \(verbo, ato, capacidade, acao, tipo[^)]*\) values \('motor', '([^']+)'", texto)
    # os atos de `# atos:` e, depois, uma linha por modo do trocar (#3532); linha em prosa vira ato inexistente (o 'a' de 08/10)
    assert registrados == ATOS + ["trocar --embedder", "trocar --virar"]


def test_cada_ato_declara_le_e_escreve_com_recurso_do_enum(sql):
    acessos = re.findall(r"into acervo\.ferramental_acesso \(verbo, ato, recurso_id, modo\) values "
                         r"\('motor', '([\w-]+)', '([^']+)', '(le|escreve)'\)", sql[2])
    assert {r for _, r, _ in acessos} <= RECURSOS
    for ato in ATOS:
        assert {m for a, _, m in acessos if a == ato} == {"le", "escreve"}, f"{ato}: uma linha le e uma escreve"


def test_a_ajuda_do_buscar_mostra_a_necessidade():
    r = subprocess.run([sys.executable, str(MOTOR)], capture_output=True, text=True)
    linha = next(x for x in r.stdout.splitlines() if "buscar <particao>" in x)
    assert "--necessidade" in linha
    assert "saco de palavras" in r.stdout
