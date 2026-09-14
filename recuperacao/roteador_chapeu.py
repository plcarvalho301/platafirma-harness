"""Shim de compatibilidade: a lógica moveu para bin/_expediente/rotear (spec_expediente §1, §8, #3053).

Quem importa este módulo não quebra.
"""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import sys
from pathlib import Path

# O sub-ato nao tem extensao (verbo: sem extensao + shebang); o loader e explicito.
_ROTEAR_PATH = Path(__file__).resolve().parent.parent / "bin" / "_expediente" / "rotear"
_spec = importlib.util.spec_from_file_location(
    "_rotear", _ROTEAR_PATH, loader=SourceFileLoader("_rotear", str(_ROTEAR_PATH)))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Não foi possível carregar o sub-ato rotear em {_ROTEAR_PATH}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_rotear"] = _mod
_spec.loader.exec_module(_mod)

# Re-exporta símbolos
Rota = _mod.Rota
Decisao = _mod.Decisao
_normaliza = _mod._normaliza
_carrega_gatilhos = _mod._carrega_gatilhos
rotas_do_disco = _mod.rotas_do_disco
casa = _mod.casa
decide = _mod.decide
roteia_semantico = _mod.roteia_semantico
escolhe = _mod.escolhe
_resolve_dir_chapeus = _mod._resolve_dir_chapeus
LIMIAR_SEMANTICO = _mod.LIMIAR_SEMANTICO
MARGEM_SEMANTICA = _mod.MARGEM_SEMANTICA

__all__ = [
    "Rota",
    "Decisao",
    "_normaliza",
    "_carrega_gatilhos",
    "rotas_do_disco",
    "casa",
    "decide",
    "roteia_semantico",
    "escolhe",
    "_resolve_dir_chapeus",
    "LIMIAR_SEMANTICO",
    "MARGEM_SEMANTICA",
]

if __name__ == "__main__":
    import json
    import os
    cad = sys.argv[1] if len(sys.argv) > 1 else "IA"
    perg = sys.argv[2] if len(sys.argv) > 2 else "orcamento de janela de contexto"
    raiz = os.path.join(os.environ.get("PF_RAIZ", os.path.expanduser("~/AI")),
                        "platafirma-harness", "abertura")
    dec = escolhe(perg, cad, raiz)
    print(json.dumps({"slug": dec.slug, "via": dec.via, "motivo": dec.motivo,
                      "acertos": dec.acertos}, ensure_ascii=False, indent=2))
