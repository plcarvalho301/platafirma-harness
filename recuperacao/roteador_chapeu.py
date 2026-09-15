"""Shim de compatibilidade: a lógica moveu para bin/_expediente/rotear (spec_expediente §1, §8, #3053).

Quem importa este módulo não quebra.
"""
from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
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
    "LIMIAR_SEMANTICO",
    "MARGEM_SEMANTICA",
    "Decisao",
    "Rota",
    "_carrega_gatilhos",
    "_normaliza",
    "_resolve_dir_chapeus",
    "casa",
    "decide",
    "escolhe",
    "rotas_do_disco",
    "roteia_semantico",
]

if __name__ == "__main__":
    import json
    cad = sys.argv[1] if len(sys.argv) > 1 else "IA"
    perg = sys.argv[2] if len(sys.argv) > 2 else "orcamento de janela de contexto"
    # morada publicada (arq:0097), a mesma que o sub-ato rotear resolve — nunca o clone
    raiz = _resolve_dir_chapeus()
    dec = escolhe(perg, cad, raiz)
    print(json.dumps({"slug": dec.slug, "via": dec.via, "motivo": dec.motivo,
                      "acertos": dec.acertos}, ensure_ascii=False, indent=2))
