# componente: componente:porta
"""O registro da porta (registro/porta.yaml, card #4117 e decisão #5322 da F4073).

Hermetico: le registro/porta.yaml sem depender da porta legada nem do registro de ferramental do banco.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRO = REPO_ROOT / "registro" / "porta.yaml"
FORA_DA_LISTA = {"chat", "minuta", "persona", "preferencia", "sinal", "situacao", "sessao"}
TRANSPORTE_ESPERADO = {"malote", "ler_arquivo", "write_file", "monta_sessao"}


@pytest.fixture(scope="module")
def registro():
    return yaml.safe_load(REGISTRO.read_text(encoding="utf-8"))


def test_transporte_declara_exatamente_as_quatro_tools_sem_legados(registro):
    transporte = set(registro["transporte"])
    assert transporte == TRANSPORTE_ESPERADO
    assert not ({"run_command", "read_file"} & transporte)


def test_ocultas_e_removidas_da_lista(registro):
    verbos = registro["verbos"]
    assert not ({"chat", "minuta", "sinal", "situacao"} & set(verbos))
    for oculto in ("preferencia", "sessao", "persona"):
        assert oculto in verbos and verbos[oculto].get("modelo") is False
    visiveis = {k for k, v in verbos.items() if (v or {}).get("modelo", True) is not False}
    assert not (visiveis & FORA_DA_LISTA)
    assert "metrica" in visiveis


def _verbos_visiveis(registro: dict) -> list[tuple[str, dict]]:
    return [
        (slug, meta or {})
        for slug, meta in registro["verbos"].items()
        if (meta or {}).get("modelo", True) is not False
    ]


def _tools_visiveis(registro: dict) -> set[str]:
    visiveis = set(registro["transporte"])
    for slug, meta in _verbos_visiveis(registro):
        visiveis.add(meta.get("nome") or slug)
    return visiveis


def test_todo_verbo_visivel_tem_descricao_no_manifesto(registro):
    """Decisão #5322: a toolstring mora em registro/porta.yaml."""
    for slug, meta in _verbos_visiveis(registro):
        desc = meta.get("descricao") or ""
        assert desc.strip(), f"{slug}: sem descricao em registro/porta.yaml"
        assert len(desc.strip()) > 20, f"{slug}: descricao curta demais"


def _descricoes_visiveis(registro: dict) -> list[tuple[str, str]]:
    saida: list[tuple[str, str]] = []
    for secao in ("verbos", "transporte"):
        for slug, meta in registro[secao].items():
            if (meta or {}).get("modelo", True) is False:
                continue
            saida.append((f"{secao}.{slug}", ((meta or {}).get("descricao") or "").strip()))
    return saida


def test_nenhuma_descricao_ultrapassa_teto_1024_chars(registro):
    """DT 944: clientes MCP (Antigravity/Gemini) descartam tools com description > 1024 chars."""
    excedentes = [
        f"{chave} ({len(desc)} chars)"
        for chave, desc in _descricoes_visiveis(registro)
        if len(desc) > 1024
    ]
    assert not excedentes, f"descrições acima de 1024 chars: {excedentes}"


def test_repo_nao_esta_retido(registro):
    """DT 944: repo deve ficar exposto de forma estável no catálogo da porta."""
    assert not registro["verbos"]["repo"].get("retido", False)


def test_faces_da_borda_saem_do_registro(registro):
    faces: dict[str, list[str]] = {}
    for slug, v in registro["verbos"].items():
        for face in (v or {}).get("faces") or {}:
            faces.setdefault(face, []).append(slug)
    assert sorted(faces) == ["casca", "motor"]
    assert sorted(faces["casca"]) == ["preferencia", "release", "tarefas"]
    assert sorted(faces["motor"]) == ["fila", "motor"]


def test_registro_expoe_exatamente_as_26_tools_visiveis_do_ar(registro):
    esperadas = {
        "acervo", "acesso", "agente", "analise", "bot", "busca", "conferir",
        "descansar", "expediente", "fila", "infra", "ler_arquivo", "lint",
        "malote", "mesa", "metrica", "monta_sessao", "motor", "ontologia",
        "pesquisar", "release", "repo", "seg", "tarefas", "teste", "write_file",
    }
    assert len(esperadas) == 26
    assert _tools_visiveis(registro) == esperadas
    assert "busca" in registro["verbos"]
    assert registro["verbos"]["motor"].get("nome") is None
    assert "nome: busca" not in REGISTRO.read_text(encoding="utf-8")


def test_toolstring_do_malote_no_registro(registro):
    desc = registro["transporte"]["malote"]["descricao"]
    assert "cadeia que para no primeiro erro" in desc
    assert "duto" in desc
    assert "verbo sem tool própria" in desc
    assert "em paralelo" in desc
    assert "lote_next" in desc
    assert "SEMPRE que for chamar dois ou mais verbos" not in desc


def _atos_da_descricao(descricao: str) -> list[str]:
    m = re.search(r"\batos:\s*([^·\n]+)", descricao)
    assert m, f"descricao sem bloco 'atos:': {descricao!r}"
    bloco = re.sub(r"\([^)]*\)", "", m.group(1))
    return [parte.strip() for parte in bloco.split(",") if parte.strip()]


def _atos_validos_do_mesa() -> tuple[str, ...]:
    arvore = ast.parse((REPO_ROOT / "bin" / "mesa").read_text(encoding="utf-8"))
    for no in arvore.body:
        if isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id == "ATOS_VALIDOS":
                    valor = ast.literal_eval(no.value)
                    assert isinstance(valor, tuple) and valor
                    return tuple(str(a) for a in valor)
    raise AssertionError("bin/mesa sem constante ATOS_VALIDOS")


def test_atos_do_mesa_no_registro_batem_com_o_verbo(registro):
    """DT 934: a lista de atos na descrição de mesa não diverge de bin/mesa."""
    atos_verbo = _atos_validos_do_mesa()
    desc = registro["verbos"]["mesa"]["descricao"]
    atos_desc = _atos_da_descricao(desc)
    assert len(atos_desc) == len(set(atos_desc)), f"atos duplicados na descrição: {atos_desc}"
    assert set(atos_desc) == set(atos_verbo), (
        f"descrição de mesa em porta.yaml ({atos_desc}) diverge de bin/mesa ({list(atos_verbo)})"
    )

    doc = ast.get_docstring(ast.parse((REPO_ROOT / "bin" / "mesa").read_text(encoding="utf-8"))) or ""
    assert set(_atos_da_descricao(doc)) == set(atos_verbo)

    ajuda = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "mesa"), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert ajuda.returncode == 0
    assert f"<{'|'.join(atos_verbo)}>" in ajuda.stdout

    recusa = subprocess.run(
        [sys.executable, str(REPO_ROOT / "bin" / "mesa"), "substituir"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert recusa.returncode == 2
    assert f"atos disponíveis: {', '.join(atos_verbo)}" in recusa.stderr

def test_atos_do_descansar_no_registro_batem_com_o_verbo(registro):
    """DT 945 e 955: a descrição de descansar anunciava fita e varredura, que o verbo não aceita mais."""
    fonte = (REPO_ROOT / "bin" / "descansar").read_text(encoding="utf-8")
    cabecalho = re.search(r"^# atos:\s*(.+)$", fonte, re.MULTILINE)
    assert cabecalho, "bin/descansar sem linha '# atos:' no cabeçalho"
    atos_verbo = _atos_da_descricao(f"atos: {cabecalho.group(1)}")
    atos_desc = _atos_da_descricao(registro["verbos"]["descansar"]["descricao"])
    assert len(atos_desc) == len(set(atos_desc)), f"atos duplicados na descrição: {atos_desc}"
    assert set(atos_desc) == set(atos_verbo), (
        f"descrição de descansar em porta.yaml ({atos_desc}) diverge de bin/descansar ({atos_verbo})"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("PF_")}
    for ato in atos_desc:
        p = subprocess.run(
            [sys.executable, str(REPO_ROOT / "bin" / "descansar"), ato],
            capture_output=True, text=True, timeout=20, check=False, input="", env=env,
        )
        assert "ato desconhecido" not in p.stderr, f"descansar {ato}: o verbo não aceita o ato do catálogo"


def _atos_do_cabecalho(verbo: str) -> tuple[str, list[str]]:
    fonte = (REPO_ROOT / "bin" / verbo).read_text(encoding="utf-8")
    cabecalho = re.search(r"^# atos:\s*(.+)$", fonte, re.MULTILINE)
    assert cabecalho, f"bin/{verbo} sem linha '# atos:' no cabeçalho"
    bruto = cabecalho.group(1).strip()
    return bruto, _atos_da_descricao(f"atos: {bruto}")


def test_atos_do_busca_e_do_motor_no_registro_batem_com_o_verbo(registro):
    """Story #4427 (t2): os atos na descrição de busca e motor batem com bin/busca e bin/motor."""
    for verbo in ("busca", "motor"):
        bruto_verbo, atos_verbo = _atos_do_cabecalho(verbo)
        desc = registro["verbos"][verbo]["descricao"]
        atos_desc = _atos_da_descricao(desc)
        assert len(atos_desc) == len(set(atos_desc)), f"atos duplicados em {verbo}: {atos_desc}"
        assert atos_desc == atos_verbo, (
            f"descrição de {verbo} em porta.yaml ({atos_desc}) diverge de bin/{verbo} ({atos_verbo})"
        )
        m = re.search(r"\batos:\s*([^·\n]+)", desc)
        assert m is not None and m.group(1).strip() == bruto_verbo

    env = {k: v for k, v in os.environ.items() if not k.startswith("PF_")}
    for ato in ("consultar", "ler"):
        p = subprocess.run(
            [sys.executable, str(REPO_ROOT / "bin" / "busca"), ato],
            capture_output=True, text=True, timeout=15, check=False, input="", env=env,
        )
        assert "ato-desconhecido" not in p.stderr, f"busca {ato}: recusado como ato desconhecido"
