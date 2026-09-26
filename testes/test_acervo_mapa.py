"""#3084: `acervo listar casa guia --mapa` junta a seção `## Mapa` dos guias de rotina.

Testa a função pura `extrai_mapa` (sem banco): ordem fixa, bytes estáveis, rotina faltando
declarada, guia sem mapa ignorado.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

CASA = Path(__file__).resolve().parents[1] / "bin" / "_acervo" / "casa"


def _casa():
    loader = importlib.machinery.SourceFileLoader("acervo_casa", str(CASA))
    spec = importlib.util.spec_from_loader("acervo_casa", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _guia(*blocos: str) -> str:
    corpo = "\n\n".join(blocos)
    return f"# Guia\n\nEspécie: guia\n\n## Mapa\n\nTexto em volta.\n\n```\n{corpo}\n```\n\n## Resto\n\n```\nnao entra\n```\n"


LER = "LER — sei a chave\n  acervo ler casa <espécie> <chave>"
LEVANTAR = "LEVANTAR — tenho um termo\n  motor rag buscar casa '<termo>'"
CONFERIR = "CONFERIR — como está\n  release conferir <classe>"
REGISTRAR = "REGISTRAR — guardo\n  mesa"
PUBLICAR = "PUBLICAR — subo\n  release promover"
REPORTAR = "REPORTAR — presto contas\n  tarefas mover"


def test_ordem_fixa_independe_da_ordem_dos_guias():
    casa = _casa()
    corpos = [_guia(REPORTAR), _guia(PUBLICAR), _guia(LER, LEVANTAR),
              _guia(REGISTRAR), _guia(CONFERIR)]
    texto, faltam = casa.extrai_mapa(corpos)
    assert faltam == []
    nomes = [b.split(None, 1)[0] for b in texto.split("\n\n")[1:]]
    assert nomes == list(casa.ORDEM_MAPA)
    assert texto.startswith(casa.CAB_MAPA)
    assert "nao entra" not in texto


def test_bytes_estaveis():
    casa = _casa()
    corpos = [_guia(LER, LEVANTAR), _guia(CONFERIR)]
    assert casa.extrai_mapa(corpos) == casa.extrai_mapa(list(reversed(corpos)))


def test_rotina_faltando_e_declarada_e_guia_sem_mapa_ignorado():
    casa = _casa()
    texto, faltam = casa.extrai_mapa(["# sem mapa\n\nnada\n", _guia(LER)])
    assert faltam == ["LEVANTAR", "CONFERIR", "REGISTRAR", "PUBLICAR", "REPORTAR"]
    assert texto == casa.CAB_MAPA + "\n\n" + LER


def test_nenhum_mapa_devolve_none():
    casa = _casa()
    texto, faltam = casa.extrai_mapa(["# nada\n"])
    assert texto is None
    assert len(faltam) == 6
