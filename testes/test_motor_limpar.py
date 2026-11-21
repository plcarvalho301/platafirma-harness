# componente: componente:verbo-motor
"""Testes unitários de bin/_motor/limpeza.py (DT-787)."""
import sys
from pathlib import Path

import pytest

_BIN_MOTOR = Path(__file__).resolve().parents[1] / "bin" / "_motor"
if str(_BIN_MOTOR) not in sys.path:
    sys.path.insert(0, str(_BIN_MOTOR))

import limpeza  # noqa: E402


def _cria_modelo(hub: Path, repo_id: str, tamanho: int = 16) -> Path:
    pasta = hub / f"models--{repo_id.replace('/', '--')}"
    snap = pasta / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "model.safetensors").write_bytes(b"x" * tamanho)
    lock = hub / ".locks" / pasta.name
    lock.mkdir(parents=True)
    (lock / "blob.lock").write_text("")
    return pasta


def test_selecionar_sombras_separa_encerradas_e_em_curso():
    sombras = [
        {"id": "20261117T054708", "fim": 0, "vivo": False},
        {"id": "20261117T055225", "fim": None, "vivo": False},
        {"id": "20261118T090000", "fim": None, "vivo": True},
    ]
    apagar, em_curso = limpeza.selecionar_sombras(sombras)
    assert apagar == ["20261117T054708", "20261117T055225"]
    assert em_curso == ["20261118T090000"]


def test_selecionar_sombras_recusa_sombra_viva_explicita():
    sombras = [{"id": "20261118T090000", "fim": None, "vivo": True}]
    with pytest.raises(limpeza.ErroLimpeza) as exc:
        limpeza.selecionar_sombras(sombras, sid="20261118T090000")
    assert exc.value.codigo == 4


def test_selecionar_modelos_protege_em_uso_e_reranker(tmp_path):
    hub = tmp_path / "hub"
    _cria_modelo(hub, "Qwen/Qwen3-Embedding-0.6B", 10)
    _cria_modelo(hub, "microsoft/harrier-oss-v1-0.6b", 24)
    _cria_modelo(hub, "BAAI/bge-reranker-v2-m3", 32)

    em_uso = {"Qwen/Qwen3-Embedding-0.6B"}
    conhecidos = {"Qwen/Qwen3-Embedding-0.6B", "microsoft/harrier-oss-v1-0.6b"}

    apagar, mantidos = limpeza.selecionar_modelos(hub, em_uso, conhecidos)
    assert [m.modelo for m in apagar] == ["microsoft/harrier-oss-v1-0.6b"]
    assert apagar[0].bytes == 24
    assert mantidos == ["BAAI/bge-reranker-v2-m3", "Qwen/Qwen3-Embedding-0.6B"]


def test_selecionar_modelos_recusa_em_uso_ou_reranker_explicito(tmp_path):
    hub = tmp_path / "hub"
    _cria_modelo(hub, "Qwen/Qwen3-Embedding-0.6B")
    _cria_modelo(hub, "BAAI/bge-reranker-v2-m3")
    em_uso = {"Qwen/Qwen3-Embedding-0.6B"}
    conhecidos = {"Qwen/Qwen3-Embedding-0.6B"}

    with pytest.raises(limpeza.ErroLimpeza) as exc_uso:
        limpeza.selecionar_modelos(hub, em_uso, conhecidos, modelo="Qwen/Qwen3-Embedding-0.6B")
    assert exc_uso.value.codigo == 4

    with pytest.raises(limpeza.ErroLimpeza) as exc_rr:
        limpeza.selecionar_modelos(hub, em_uso, conhecidos, modelo="BAAI/bge-reranker-v2-m3")
    assert exc_rr.value.codigo == 4


def test_executar_limpeza_respeita_ver_e_apaga_real(tmp_path):
    hub = tmp_path / "hub"
    pasta_harrier = _cria_modelo(hub, "microsoft/harrier-oss-v1-0.6b", 20)
    pasta_qwen = _cria_modelo(hub, "Qwen/Qwen3-Embedding-0.6B", 10)

    apagadas = []
    modelos, mantidos = limpeza.selecionar_modelos(
        hub,
        {"Qwen/Qwen3-Embedding-0.6B"},
        {"Qwen/Qwen3-Embedding-0.6B", "microsoft/harrier-oss-v1-0.6b"},
    )

    sim = limpeza.executar_limpeza(
        ["20261117T054708"], [], modelos, mantidos, hub, apagadas.append, ver=True
    )
    assert sim["ver"] is True
    assert apagadas == []
    assert pasta_harrier.exists()

    real = limpeza.executar_limpeza(
        ["20261117T054708"], [], modelos, mantidos, hub, apagadas.append, ver=False
    )
    assert real["ver"] is False
    assert apagadas == ["20261117T054708"]
    assert not pasta_harrier.exists()
    assert not (hub / ".locks" / pasta_harrier.name).exists()
    assert pasta_qwen.exists()
    assert real["bytes_liberados"] == 20
