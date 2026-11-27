"""servico — serviço sem estado de lint que julga gabaritos determinísticos (card #4454).

Embrulha os detectores de `bin/_lint/` sob uma interface estreita e sem estado:
recebe uma ou mais réguas da forma `gabarito` (concatenadas) e uma lista de alvos
já resolvidos, e devolve um veredito por alvo com apontamentos estruturados e
itens de leitura listados à parte como não julgados.

Não grava veredito em disco, evento ou banco e não mantém cache entre chamadas.
"""
from __future__ import annotations

import functools
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acervo import ErroAcervo, verificar_acervo
from .card import verificar_card_regua
from .codigo import verificar_codigo
from .lista import resolver_lista
from .organizacao import verificar_organizacao
from .prosa import verificar_prosa
from .resultado import Apontamento

SERVICO_CHAVE = "servico:harness:lint"
_EXIT_DETECTOR_DEPENDENCIA = 3
_EXIT_DETECTOR_SEM_LISTA = 5

# Mapa canônico de slug de gabarito → classe de detector do lint.
MAPA_REGUA_CLASSE: Mapping[str, str] = {
    "antipadroes-de-codigo": "codigo",
    "marcas-pt-br": "prosa",
    "antipadroes-de-discovery": "card",
    "forma-de-card": "card",
    "antipadroes-de-organizacao-documental": "organizacao",
    "checklist-antipadroes-organizacao-documental": "organizacao",
    "antipadroes-do-acervo": "acervo",
}


class ErroServicoLint(Exception):
    """Falha controlada do serviço de lint traduzível para a tabela de saídas 1–5."""

    def __init__(
        self,
        saida: int,
        codigo: str,
        detalhe: str,
        *,
        itens_nao_julgados: Sequence[str] = (),
    ) -> None:
        super().__init__(detalhe)
        self.saida = int(saida)
        self.codigo = str(codigo)
        self.detalhe = str(detalhe)
        self.itens_nao_julgados = tuple(itens_nao_julgados)


@dataclass(frozen=True, slots=True)
class AlvoLint:
    """Alvo já resolvido pelo verificador para julgamento pelo serviço de lint."""

    chave: str
    raiz: Path | None = None
    caminho: str | None = None
    texto: str | None = None
    versao: str = ""


@dataclass(frozen=True, slots=True)
class ApontamentoLint:
    """Apontamento estruturado emitido pelo serviço de lint."""

    item: str
    alvo: str
    lugar: str
    exigencia: str
    severidade: str
    cura: str

    def como_dict(self) -> dict[str, str]:
        return {
            "item": self.item,
            "alvo": self.alvo,
            "lugar": self.lugar,
            "exigencia": self.exigencia,
            "severidade": self.severidade,
            "cura": self.cura,
        }


@dataclass(frozen=True, slots=True)
class VereditoLint:
    """Veredito unitário devolvido pelo serviço de lint para um alvo."""

    alvo: str
    resultado: str
    constatacao: str
    modo: str
    apontamentos: tuple[ApontamentoLint, ...]
    nao_julgados: tuple[str, ...]
    motor: str
    versao_servico: str
    versao_regua: str = ""


@dataclass(frozen=True, slots=True)
class _ContextoRodada:
    resolvidas: tuple[tuple[str, str], ...]
    fim: float
    rodar: Any
    nao_julgados: tuple[str, ...]
    sha_servico: str


def normalizar_chave_regua(regua: str) -> str:
    """Extrai o slug da régua removendo prefixo de classe (`gabarito:`, `verificacao:`)."""
    limpo = regua.strip()
    if ":" in limpo:
        return limpo.split(":", 1)[1].strip()
    return limpo


def tem_detector(regua: str) -> bool:
    """Informa se a régua possui detector determinístico neste serviço."""
    return normalizar_chave_regua(regua) in MAPA_REGUA_CLASSE


@functools.lru_cache(maxsize=1)
def versao_servico() -> str:
    """SHA da release do harness em que o serviço roda (para a chave do veredito)."""
    env_sha = os.environ.get("PLATAFIRMA_HARNESS_SHA", "").strip()
    if env_sha:
        return env_sha

    release_dir = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    for nome in ("harness/.release-sha", "VERSION"):
        try:
            linha = (release_dir / nome).read_text(encoding="utf-8").splitlines()[0].strip()
            if linha:
                return linha[:12]
        except (OSError, IndexError):
            continue

    proc = subprocess.run(
        ["git", "show", "-s", "--format=%h", "HEAD"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "desenvolvimento"


def _itens_de_leitura_da_regua(slug: str) -> list[str]:
    """Identifica itens marcados como `leitura` na régua servida."""
    lista = resolver_lista(slug)
    if not lista:
        return []
    nao_julgados: list[str] = []
    for item in lista.get("itens", []):
        detector = str(item.get("detector", "")).strip().lower()
        if detector == "leitura" or detector.startswith("leitura "):
            ident = str(item.get("id") or item.get("o_que_fere") or "").strip()
            if ident and ident not in nao_julgados:
                nao_julgados.append(ident)
    return nao_julgados


def _traduzir_apontamento(ap: Apontamento, chave_alvo: str) -> ApontamentoLint:
    lugar = f"{ap.arquivo}:{ap.linha}" if ap.arquivo else str(ap.linha)
    severidade = "bloqueante" if ap.severidade == "bloqueante" else "aviso"
    item_id = (ap.id or ap.o_que_fere.split(" ", 1)[0] or "item").strip()
    return ApontamentoLint(
        item=item_id,
        alvo=chave_alvo,
        lugar=lugar,
        exigencia=ap.o_que_fere,
        severidade=severidade,
        cura=ap.cura,
    )


def _traduzir_erro_detector(exc: ValueError, slug: str) -> ErroServicoLint:
    codigo_num = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
    msg = str(exc.args[1]) if len(exc.args) > 1 else str(exc)
    if codigo_num == _EXIT_DETECTOR_DEPENDENCIA:
        return ErroServicoLint(3, "dependencia-sem-resposta", msg)
    if codigo_num == _EXIT_DETECTOR_SEM_LISTA:
        return ErroServicoLint(1, "regua-inexistente", msg)
    return ErroServicoLint(3, "dependencia-sem-resposta", f"falha no detector de '{slug}': {msg}")


def _executar_detector(classe: str, slug: str, alvo: AlvoLint) -> tuple[list[Apontamento], str]:
    """Aciona o detector correspondente à classe do lint e devolve (apontamentos, versao_regua)."""
    raiz = alvo.raiz or Path(".")
    try:
        if classe == "codigo":
            apontamentos, _chave, rev, _avisos = verificar_codigo(raiz, alvo.caminho, leitura=False)
            return apontamentos, f"rev{rev}"
        if classe == "prosa":
            apontamentos, _chave, rev = verificar_prosa(raiz, alvo.caminho)
            return apontamentos, f"rev{rev or 1}"
        if classe == "card":
            texto = alvo.texto
            if texto is None and alvo.caminho:
                texto = (raiz / alvo.caminho).read_text(encoding="utf-8", errors="replace")
            apontamentos, _chave, rev, _avisos = verificar_card_regua(
                texto or "",
                nivel="story" if slug == "forma-de-card" else "feature",
            )
            return apontamentos, f"rev{rev or 1}"
        if classe == "organizacao":
            apontamentos, _chave, rev, _avisos = verificar_organizacao(raiz, alvo.caminho)
            return apontamentos, f"rev{rev or 1}"
        if classe == "acervo":
            apontamentos, _chave, rev, _avisos = verificar_acervo()
            return apontamentos, f"rev{rev or 1}"
    except ValueError as exc:
        raise _traduzir_erro_detector(exc, slug) from exc
    except (ErroAcervo, OSError) as exc:
        raise ErroServicoLint(3, "dependencia-sem-resposta", str(exc)) from exc

    raise ErroServicoLint(5, "sem-detector", f"classe de detector desconhecida: {classe}")


def _resolver_reguas(reguas: Sequence[str]) -> tuple[tuple[str, str], ...]:
    resolvidas: list[tuple[str, str]] = []
    for regua in reguas:
        slug = normalizar_chave_regua(regua)
        classe = MAPA_REGUA_CLASSE.get(slug)
        if classe is None:
            raise ErroServicoLint(
                5,
                "sem-detector",
                f"régua '{regua}' não possui detector determinístico no serviço de lint",
            )
        resolvidas.append((slug, classe))
    return tuple(resolvidas)


def _julgar_alvo(alvo: AlvoLint, ctx: _ContextoRodada) -> VereditoLint:
    apontamentos_alvo: list[ApontamentoLint] = []
    vistos: set[tuple[str, str, str]] = set()
    versoes_regua: list[str] = []

    for slug, classe in ctx.resolvidas:
        if time.monotonic() >= ctx.fim:
            raise ErroServicoLint(
                5,
                "tempo-esgotado",
                f"prazo esgotado ao aplicar a régua '{slug}' sobre '{alvo.chave}'",
            )
        achados, v_regua = ctx.rodar(classe, slug, alvo)
        if v_regua:
            versoes_regua.append(f"{slug}@{v_regua}")
        for ap in achados:
            trad = _traduzir_apontamento(ap, alvo.chave)
            chave_dedup = (trad.item, trad.lugar, trad.exigencia)
            if chave_dedup not in vistos:
                vistos.add(chave_dedup)
                apontamentos_alvo.append(trad)

    tem_bloqueante = any(a.severidade == "bloqueante" for a in apontamentos_alvo)
    return VereditoLint(
        alvo=alvo.chave,
        resultado="nao" if tem_bloqueante else "sim",
        constatacao="divergente" if tem_bloqueante else "conforme",
        modo="enquadrou",
        apontamentos=tuple(apontamentos_alvo),
        nao_julgados=ctx.nao_julgados,
        motor=SERVICO_CHAVE,
        versao_servico=ctx.sha_servico,
        versao_regua="+".join(versoes_regua),
    )


def julgar(
    reguas: Sequence[str],
    alvos: Sequence[AlvoLint],
    *,
    prazo_s: float = 60.0,
    executor_detector: Any = None,
) -> list[VereditoLint]:
    """Julga `alvos` contra a união das `reguas` (forma gabarito) e devolve um veredito por alvo.

    Sem estado: nunca lê nem grava cache de vereditos. Itens bloqueantes fecham `divergente`
    (`nao`); itens de `aviso` entram nos apontamentos sem alterar `conforme` (`sim`). Itens de
    `leitura` ficam fora do julgamento determinístico e retornam em `nao_julgados`.
    """
    if prazo_s <= 0:
        raise ErroServicoLint(5, "tempo-esgotado", "prazo esgotado antes de iniciar o serviço de lint")
    if not reguas:
        raise ErroServicoLint(1, "regua-inexistente", "nenhuma régua informada ao serviço de lint")

    resolvidas = _resolver_reguas(reguas)
    ctx = _ContextoRodada(
        resolvidas=resolvidas,
        fim=time.monotonic() + prazo_s,
        rodar=executor_detector or _executar_detector,
        nao_julgados=tuple(
            dict.fromkeys(
                item
                for slug, _ in resolvidas
                for item in _itens_de_leitura_da_regua(slug)
            )
        ),
        sha_servico=versao_servico(),
    )

    vereditos: list[VereditoLint] = []
    for alvo in alvos:
        if time.monotonic() >= ctx.fim:
            raise ErroServicoLint(
                5,
                "tempo-esgotado",
                f"prazo esgotado ao julgar o alvo '{alvo.chave}' no serviço de lint",
            )
        vereditos.append(_julgar_alvo(alvo, ctx))
    return vereditos
