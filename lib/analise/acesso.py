"""PDP por objeto e posse no catálogo, sem herdar autorização do manifesto."""

from __future__ import annotations

import sys

from . import Falha, exigir, hash_arquivo


def autorizar(sujeito: str, ato: str, recurso: str) -> dict:
    from raizes import release

    pasta = release() / "harness/politica-acesso"
    exigir(pasta.is_dir(), "pdp-ausente", 3)
    try:
        import yaml

        sys.path.insert(0, str(pasta))
        from pdp import Politica, Recurso, Sujeito, decide

        politica = Politica.de_arquivo(pasta / "politica.yaml")
        atrib = (
            (yaml.safe_load((pasta / "sujeitos.yaml").read_text()) or {})
            .get("sujeitos", {})
            .get(sujeito)
        )
        exigir(atrib, "acesso-negado", 4)
        s = Sujeito(
            id=sujeito,
            natureza=atrib.get("natureza"),
            papeis=tuple(atrib.get("papeis", ())),
            dominios=tuple(atrib.get("dominios", ())),
            temas=tuple(atrib.get("temas", ())),
            vetos=tuple(atrib.get("vetos", ())),
            habilitacao=atrib.get("habilitacao", "publico"),
        )
        d = decide(
            s,
            "analise_" + ato,
            Recurso(tipo="registro", id=recurso, dominio="plataforma"),
            politica,
        )
        exigir(d.permitido, "acesso-negado", 4)
        return {"versao": hash_arquivo(pasta / "politica.yaml"), "regra": d.regra}
    except Falha:
        raise
    except Exception:
        raise Falha(3, "pdp-indisponivel") from None
