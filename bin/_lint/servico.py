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

from .acervo import ErroAcervo, medir_acervo
from .card import verificar_card_regua
from .codigo import verificar_codigo
from .lista import resolver_lista
from .organizacao import CHAVE_LISTA as _CHAVE_LISTA_ORG
from .organizacao import verificar_organizacao
from .prosa import ESPECIES_REGUA as _ESPECIES_PROSA
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
        vereditos_parciais: Sequence[VereditoLint] = (),
    ) -> None:
        super().__init__(detalhe)
        self.saida = int(saida)
        self.codigo = str(codigo)
        self.detalhe = str(detalhe)
        self.itens_nao_julgados = tuple(itens_nao_julgados)
        self.vereditos_parciais = tuple(vereditos_parciais)


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
class _ReguaResolvida:
    slug: str
    classe: str
    lista: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class _ResultadoDetector:
    apontamentos: list[Apontamento]
    versao_regua: str
    nao_julgados: tuple[str, ...] = ()
    inconclusivo: bool = False


@dataclass(frozen=True, slots=True)
class _ContextoRodada:
    resolvidas: tuple[_ReguaResolvida, ...]
    fim: float
    rodar: Any
    usa_detector_real: bool
    nao_julgados: tuple[str, ...]
    tem_bloqueante_leitura: bool
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


def _carregar_lista_regua(slug: str, classe: str) -> dict[str, Any] | None:
    """Resolve a lista da régua uma única vez por chamada, respeitando aliases da classe."""
    if classe == "prosa":
        return resolver_lista(slug, especies=_ESPECIES_PROSA)
    lista = resolver_lista(slug)
    if lista is None and classe == "organizacao" and slug != _CHAVE_LISTA_ORG:
        lista = resolver_lista(_CHAVE_LISTA_ORG)
    return lista


def _analisar_leitura_da_lista(lista: dict[str, Any] | None) -> tuple[list[str], bool]:
    """Identifica itens de `leitura` na régua servida e se algum deles é bloqueante."""
    if not lista:
        return [], False
    nao_julgados: list[str] = []
    tem_bloqueante_leitura = False
    for item in lista.get("itens", []):
        detector = str(item.get("detector", "")).strip().lower()
        if detector == "leitura" or detector.startswith("leitura "):
            ident = str(item.get("id") or item.get("o_que_fere") or "").strip()
            if ident and ident not in nao_julgados:
                nao_julgados.append(ident)
            if str(item.get("severidade", "")).strip().lower() == "bloqueante":
                tem_bloqueante_leitura = True
    return nao_julgados, tem_bloqueante_leitura


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


def _traduzir_apontamentos_acervo(medida: dict[str, Any]) -> tuple[list[Apontamento], tuple[str, ...], bool]:
    apontamentos: list[Apontamento] = []
    for a in medida.get("apontamentos", []):
        cid = str(a.get("id") or "item").strip()
        desc = str(a.get("descricao") or cid).strip()
        apontamentos.append(
            Apontamento(
                arquivo=str(a.get("alvo") or "acervo"),
                linha=1,
                o_que_fere=f"{cid} {desc}",
                cura=str(a.get("cura") or ""),
                severidade=str(a.get("severidade") or "aviso"),
                id=cid,
            )
        )
    nao_rodou = medida.get("nao_rodou") or []
    nao_julgados = tuple(
        dict.fromkeys(str(x.get("id") or "").strip() for x in nao_rodou if str(x.get("id") or "").strip())
    )
    bloq_sem_medida = any(str(x.get("severidade") or "").strip().lower() == "bloqueante" for x in nao_rodou)
    return apontamentos, nao_julgados, bloq_sem_medida


def _adaptar_codigo(regua: _ReguaResolvida, alvo: AlvoLint, raiz: Path) -> _ResultadoDetector:
    apontamentos, _chave, rev, _avisos = verificar_codigo(raiz, alvo.caminho, leitura=False, lista=regua.lista)
    return _ResultadoDetector(apontamentos=apontamentos, versao_regua=f"rev{rev}")


def _adaptar_prosa(regua: _ReguaResolvida, _alvo: AlvoLint, _raiz: Path) -> _ResultadoDetector:
    if not regua.lista:
        raise ErroServicoLint(1, "regua-inexistente", f"régua '{regua.slug}' não encontrada no acervo")
    rev = regua.lista.get("rev") or 1
    # O avaliador determinístico de prosa não julga marcas de máquina sobre texto;
    # responde inconclusivo (`nao-sei`) em vez de devolver `conforme` sem ler.
    return _ResultadoDetector(
        apontamentos=[],
        versao_regua=f"rev{rev}",
        nao_julgados=(regua.slug,),
        inconclusivo=True,
    )


def _adaptar_card(regua: _ReguaResolvida, alvo: AlvoLint, raiz: Path) -> _ResultadoDetector:
    texto = alvo.texto
    if texto is None and alvo.caminho:
        texto = (raiz / alvo.caminho).read_text(encoding="utf-8", errors="replace")
    nome_alvo = alvo.caminho or alvo.chave
    apontamentos, _chave, rev, _avisos = verificar_card_regua(
        alvo=nome_alvo,
        texto=texto,
        raiz=raiz,
        lista=regua.lista,
        fecha_existe=False,
    )
    rev_final = (regua.lista.get("rev") if regua.lista else None) or rev or 1
    return _ResultadoDetector(apontamentos=apontamentos, versao_regua=f"rev{rev_final}")


def _adaptar_organizacao(regua: _ReguaResolvida, alvo: AlvoLint, raiz: Path) -> _ResultadoDetector:
    apontamentos, _chave, rev = verificar_organizacao(
        raiz,
        alvo.caminho,
        com_bloqueantes=True,
        lista=regua.lista,
    )
    return _ResultadoDetector(apontamentos=apontamentos, versao_regua=f"rev{rev or 1}")


def _adaptar_acervo(regua: _ReguaResolvida, _alvo: AlvoLint, _raiz: Path) -> _ResultadoDetector:
    medida, rev = medir_acervo(lista=regua.lista)
    apontamentos, nao_rodou, bloq_sem_medida = _traduzir_apontamentos_acervo(medida)
    return _ResultadoDetector(
        apontamentos=apontamentos,
        versao_regua=f"rev{rev or 1}",
        nao_julgados=nao_rodou,
        inconclusivo=bloq_sem_medida,
    )


_ADAPTADORES = {
    "codigo": _adaptar_codigo,
    "prosa": _adaptar_prosa,
    "card": _adaptar_card,
    "organizacao": _adaptar_organizacao,
    "acervo": _adaptar_acervo,
}


def _executar_detector_real(regua: _ReguaResolvida, alvo: AlvoLint) -> _ResultadoDetector:
    """Aciona o detector real da classe do lint sem saída lateral nem verde falso."""
    adaptador = _ADAPTADORES.get(regua.classe)
    if adaptador is None:
        raise ErroServicoLint(5, "sem-detector", f"classe de detector desconhecida: {regua.classe}")
    raiz = alvo.raiz or Path(".")
    try:
        return adaptador(regua, alvo, raiz)
    except ErroServicoLint:
        raise
    except ValueError as exc:
        raise _traduzir_erro_detector(exc, regua.slug) from exc
    except ErroAcervo as exc:
        saida = 1 if exc.rc == _EXIT_DETECTOR_SEM_LISTA else 3
        codigo = "regua-inexistente" if saida == 1 else "dependencia-sem-resposta"
        raise ErroServicoLint(saida, codigo, exc.msg) from exc
    except OSError as exc:
        raise ErroServicoLint(3, "dependencia-sem-resposta", str(exc)) from exc


def _resolver_reguas(
    reguas: Sequence[str],
    *,
    carregar_listas: bool,
) -> tuple[_ReguaResolvida, ...]:
    resolvidas: list[_ReguaResolvida] = []
    for regua in reguas:
        slug = normalizar_chave_regua(regua)
        classe = MAPA_REGUA_CLASSE.get(slug)
        if classe is None:
            raise ErroServicoLint(
                5,
                "sem-detector",
                f"régua '{regua}' não possui detector determinístico no serviço de lint",
            )
        lista = _carregar_lista_regua(slug, classe) if carregar_listas else None
        resolvidas.append(_ReguaResolvida(slug=slug, classe=classe, lista=lista))
    return tuple(resolvidas)


def _fechar_constatacao(apontamentos: Sequence[ApontamentoLint], *, inconclusivo: bool) -> tuple[str, str]:
    if any(a.severidade == "bloqueante" for a in apontamentos):
        return "nao", "divergente"
    if inconclusivo:
        return "nao-sei", "inconclusivo"
    return "sim", "conforme"


def _acumular_apontamentos(
    achados: Sequence[Apontamento],
    chave_alvo: str,
    destino: list[ApontamentoLint],
    vistos: set[tuple[str, str, str]],
) -> None:
    for ap in achados:
        trad = _traduzir_apontamento(ap, chave_alvo)
        chave_dedup = (trad.item, trad.lugar, trad.exigencia)
        if chave_dedup not in vistos:
            vistos.add(chave_dedup)
            destino.append(trad)


def _executar_regua_no_alvo(regua: _ReguaResolvida, alvo: AlvoLint, ctx: _ContextoRodada) -> _ResultadoDetector:
    if ctx.usa_detector_real:
        return _executar_detector_real(regua, alvo)
    achados, v_regua = ctx.rodar(regua.classe, regua.slug, alvo)
    return _ResultadoDetector(apontamentos=list(achados), versao_regua=str(v_regua or ""))


def _julgar_alvo(
    alvo: AlvoLint,
    ctx: _ContextoRodada,
    vereditos_anteriores: Sequence[VereditoLint],
) -> VereditoLint:
    apontamentos_alvo: list[ApontamentoLint] = []
    vistos: set[tuple[str, str, str]] = set()
    versoes_regua: list[str] = []
    nao_julgados_alvo: list[str] = list(ctx.nao_julgados)
    inconclusivo = ctx.tem_bloqueante_leitura

    for regua in ctx.resolvidas:
        if time.monotonic() >= ctx.fim:
            raise ErroServicoLint(
                5,
                "tempo-esgotado",
                f"prazo esgotado ao aplicar a régua '{regua.slug}' sobre '{alvo.chave}'",
                vereditos_parciais=vereditos_anteriores,
            )
        res = _executar_regua_no_alvo(regua, alvo, ctx)
        if res.versao_regua:
            versoes_regua.append(f"{regua.slug}@{res.versao_regua}")
        for nj in res.nao_julgados:
            if nj not in nao_julgados_alvo:
                nao_julgados_alvo.append(nj)
        inconclusivo = inconclusivo or res.inconclusivo
        _acumular_apontamentos(res.apontamentos, alvo.chave, apontamentos_alvo, vistos)

    resultado, constatacao = _fechar_constatacao(apontamentos_alvo, inconclusivo=inconclusivo)
    return VereditoLint(
        alvo=alvo.chave,
        resultado=resultado,
        constatacao=constatacao,
        modo="enquadrou",
        apontamentos=tuple(apontamentos_alvo),
        nao_julgados=tuple(nao_julgados_alvo),
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
    `leitura` ficam fora do julgamento determinístico e retornam em `nao_julgados`; bloqueante
    sem medida determinística fecha `inconclusivo` (`nao-sei`), nunca verde falso.
    """
    if prazo_s <= 0:
        raise ErroServicoLint(5, "tempo-esgotado", "prazo esgotado antes de iniciar o serviço de lint")
    if not reguas:
        raise ErroServicoLint(1, "regua-inexistente", "nenhuma régua informada ao serviço de lint")

    usa_real = executor_detector is None
    resolvidas = _resolver_reguas(reguas, carregar_listas=usa_real)

    nao_julgados_acum: list[str] = []
    tem_bloqueante_leitura = False
    for r in resolvidas:
        itens_leitura, tem_bloq = _analisar_leitura_da_lista(r.lista)
        for item in itens_leitura:
            if item not in nao_julgados_acum:
                nao_julgados_acum.append(item)
        if tem_bloq:
            tem_bloqueante_leitura = True

    ctx = _ContextoRodada(
        resolvidas=resolvidas,
        fim=time.monotonic() + prazo_s,
        rodar=executor_detector,
        usa_detector_real=usa_real,
        nao_julgados=tuple(nao_julgados_acum),
        tem_bloqueante_leitura=tem_bloqueante_leitura,
        sha_servico=versao_servico(),
    )

    vereditos: list[VereditoLint] = []
    for alvo in alvos:
        if time.monotonic() >= ctx.fim:
            raise ErroServicoLint(
                5,
                "tempo-esgotado",
                f"prazo esgotado ao julgar o alvo '{alvo.chave}' no serviço de lint",
                vereditos_parciais=vereditos,
            )
        vereditos.append(_julgar_alvo(alvo, ctx, vereditos))
    return vereditos
