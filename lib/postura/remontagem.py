"""Remontagem do comportamento da sessão após compactação da janela.

Lê as chaves da sessão na memória de trabalho e reconstrói por valor:
- persona (sem a linha de Postura preferencial)
- cultura (opcional; omitida na remontagem pós-compactação pela porta, story #4343)
- posturas em vigor
- cenários presentes
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from . import atos
from . import documentos as doc
from .atos import Contexto

TETO_REMONTAGEM_CHARS = 9_500  # abaixo do corte de 10.000 caracteres do Claude Code


def _truncar_no_teto(texto: str, teto: int) -> str:
    if teto <= 0 or len(texto) <= teto:
        return texto
    marcador = "\n… [truncado no teto de remontagem]"
    corte = max(0, teto - len(marcador))
    return texto[:corte].rstrip() + marcador


@dataclass
class Remontagem:
    persona: str
    cultura: str
    posturas: str
    cenarios: str
    rotulos_posturas: list[str]
    avisos: list[str]

    def por_valor(self) -> dict[str, Any]:
        return asdict(self)

    def texto_formatado(self, *, teto_caracteres: int | None = None) -> str:
        """Formata a remontagem em bloco pronto para a janela, respeitando o teto opcional."""
        blocos: list[str] = []
        if self.persona:
            blocos.append(self.persona.strip())
        if self.cultura:
            blocos.append(self.cultura.strip())
        if self.posturas:
            blocos.append(self.posturas.strip())
        if self.cenarios:
            blocos.append(self.cenarios.strip())
        texto = "\n\n".join(b for b in blocos if b)
        if teto_caracteres is not None:
            return _truncar_no_teto(texto, teto_caracteres)
        return texto


def remontar(
    ctx: Contexto,
    *,
    incluir_cultura: bool = True,
    teto_caracteres: int | None = None,
) -> Remontagem:
    """Remonta o comportamento da sessão lendo as chaves vivas da lousa.

    Na remontagem pós-compactação chamada pela porta (story #4343), `incluir_cultura=False`
    e `teto_caracteres=9500` mantêm o retorno abaixo do corte de 10.000 caracteres.
    """
    cultura_txt = ""
    if incluir_cultura:
        try:
            cultura_txt, _ = doc.cultura(ctx.base)
        except Exception:
            cultura_txt = ""

    persona_txt = ""
    try:
        persona_txt = atos._persona(ctx)
    except Exception:
        persona_txt = ""

    v = atos._compoe(ctx, fecha=True)
    posturas_txt = v.bloco()
    cenarios_txt = v.bloco_de_cenarios()
    rotulos = [l.rotulo() for l in v.servidas()]
    avisos = list(v.avisos)

    if teto_caracteres is not None and teto_caracteres > 0:
        # Preserva posturas e cenários primeiro; ajusta persona/cultura para caber no teto.
        fixos = "\n\n".join(b for b in (posturas_txt.strip(), cenarios_txt.strip()) if b)
        restante = teto_caracteres - len(fixos) - (2 if fixos else 0)
        if restante <= 0:
            persona_txt = ""
            cultura_txt = ""
            posturas_txt = _truncar_no_teto(posturas_txt, teto_caracteres)
            cenarios_txt = ""
        else:
            if cultura_txt:
                corte_cultura = max(0, restante // 3)
                cultura_txt = _truncar_no_teto(cultura_txt, corte_cultura)
                restante = max(0, restante - len(cultura_txt) - 2)
            if persona_txt and len(persona_txt) > restante:
                persona_txt = _truncar_no_teto(persona_txt, restante)

    return Remontagem(
        persona=persona_txt,
        cultura=cultura_txt,
        posturas=posturas_txt,
        cenarios=cenarios_txt,
        rotulos_posturas=rotulos,
        avisos=avisos,
    )
