"""executor — serviço sem estado de execução de testes por ficha (card #4454).

Julga exatamente uma ficha de teste (`teste:<componente>` ou `teste:<componente>--<alvo>`)
sobre uma árvore da construção, reutilizando o executor isolado, a repetição de erráticos
e a quarentena válida de `lib/suite/esteira.py` e `lib/suite/coletor.py`.

Nunca lê nem grava vereditos memoizados nem a pasta de vereditos da rodada da suíte.
"""
from __future__ import annotations

import functools
import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analise import Falha as FalhaUnidade

from suite.coletor import (
    PRAZO_QUARENTENA_DIAS,
    CasoSelecionado,
    LinhaBalde,
    estado_quarentena_caso,
)
from suite.esteira import (
    ExecutorIsoladoUnidade,
    _executar_com_repeticao_erratico,
    isolamento_disponivel_no_host,
)
from suite.selecao import descobrir_arquivos_teste
from suite.vinculo import ler_vinculo

SERVICO_CHAVE = "servico:harness:executor-de-testes"
_MAX_SAIDA_CURA = 300
_MARCADORES_INFRA = (
    "execução isolada terminou com status",
    "resultado isolado ilegível",
    "execução com exige terminou com status",
)


class ErroExecutorTestes(Exception):
    """Falha controlada do executor de testes traduzível para as saídas 1, 3 ou 5."""

    def __init__(self, saida: int, codigo: str, detalhe: str) -> None:
        super().__init__(detalhe)
        self.saida = int(saida)
        self.codigo = str(codigo)
        self.detalhe = str(detalhe)


@dataclass(frozen=True, slots=True)
class ApontamentoTeste:
    """Apontamento emitido para cada caso que falhou na ficha julgada."""

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
class VereditoTeste:
    """Veredito unitário devolvido pelo executor de testes para uma ficha."""

    alvo: str
    quesito: str
    resultado: str
    constatacao: str
    modo: str
    apontamentos: tuple[ApontamentoTeste, ...]
    motor: str
    versao_servico: str
    casos_total: int = 0
    casos_quarentena: int = 0


@dataclass(frozen=True, slots=True)
class OpcoesExecucaoTeste:
    """Parâmetros de execução injetáveis do executor de testes e da suíte."""

    alvo: str = ""
    executor_isolado: Callable[[Path, list[str]], Mapping[str, Any]] | None = None
    abertas_quarentena: Sequence[LinhaBalde] = ()
    prazo_s: float = 300.0
    prazo_quarentena_dias: int = PRAZO_QUARENTENA_DIAS
    ficha_confirmada: bool = False


@functools.lru_cache(maxsize=1)
def versao_servico() -> str:
    """SHA da release do harness em que o executor roda."""
    sha = os.environ.get("PLATAFIRMA_HARNESS_SHA", "").strip()
    if sha:
        return sha
    release_dir = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    for arq in (release_dir / "harness" / ".release-sha", release_dir / "VERSION"):
        try:
            texto = arq.read_text(encoding="utf-8").strip()
            if texto:
                return texto.splitlines()[0].strip()[:12]
        except OSError:
            continue
    res = subprocess.run(
        ["git", "show", "-s", "--format=%h", "HEAD"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else "desenvolvimento"


def _selecionar_casos_da_ficha(raiz: Path, chave_ficha: str) -> tuple[bool, list[CasoSelecionado]]:
    """Seleciona os casos dos arquivos da árvore cujo cabeçalho produz `chave_ficha`."""
    achou_arquivo = False
    selecionados: list[CasoSelecionado] = []

    for arq in descobrir_arquivos_teste(raiz):
        vinculo = ler_vinculo(arq)
        if vinculo.chave_ficha != chave_ficha:
            continue
        achou_arquivo = True
        rel = arq.relative_to(raiz).as_posix() if arq.is_relative_to(raiz) else arq.name
        selecionados.extend(
            CasoSelecionado(
                id_caso=f"{rel}::{caso.nome}",
                arquivo=rel,
                nome_caso=caso.nome,
                componente=vinculo.componente or "",
                classe=vinculo.papel or "teste-de-comportamento",
                exige=caso.exige,
                incidentes=caso.incidentes,
                no_alcance=True,
                stack="harness",
            )
            for caso in vinculo.casos
        )
    return achou_arquivo, selecionados


def _resolver_executor_isolado(opcoes: OpcoesExecucaoTeste) -> Callable[[Path, list[str]], Mapping[str, Any]]:
    if opcoes.executor_isolado is not None:
        return opcoes.executor_isolado
    if not isolamento_disponivel_no_host():
        raise ErroExecutorTestes(
            3,
            "dependencia-sem-resposta",
            "isolamento ausente no host (systemd-run e bwrap são exigidos para executar testes)",
        )
    return ExecutorIsoladoUnidade(prazo_s=opcoes.prazo_s)


def _fechar_veredito(
    alvo_chave: str,
    chave_ficha: str,
    casos: Sequence[CasoSelecionado],
    resultados: Mapping[str, Any],
    opcoes: OpcoesExecucaoTeste,
) -> VereditoTeste:
    apontamentos: list[ApontamentoTeste] = []
    casos_ativos = 0
    casos_quarentena = 0

    for caso in casos:
        estado_q = estado_quarentena_caso(
            caso.id_caso,
            opcoes.abertas_quarentena,
            prazo_dias=opcoes.prazo_quarentena_dias,
        )
        if estado_q == "ativa":
            casos_quarentena += 1
            continue

        casos_ativos += 1
        res = resultados.get(caso.id_caso)
        if res is None:
            raise ErroExecutorTestes(
                3,
                "dependencia-sem-resposta",
                f"executor isolado não devolveu resultado para o caso '{caso.id_caso}'",
            )
        if res.aprovado or res.passou_em_repeticao:
            continue

        saida_res = str(res.saida or "").strip()
        if any(m in saida_res for m in _MARCADORES_INFRA):
            raise ErroExecutorTestes(3, "dependencia-sem-resposta", saida_res)

        cura = saida_res[:_MAX_SAIDA_CURA] if saida_res else "corrigir o caso que falhou na ficha"
        apontamentos.append(
            ApontamentoTeste(
                item=caso.nome_caso,
                alvo=alvo_chave,
                lugar=caso.arquivo,
                exigencia=f"caso {caso.id_caso} da ficha {chave_ficha} falhou",
                severidade="bloqueante",
                cura=cura,
            )
        )

    sha_servico = versao_servico()
    if casos_ativos == 0:
        return VereditoTeste(
            alvo=alvo_chave,
            quesito=chave_ficha,
            resultado="nao-sei",
            constatacao="inconclusivo",
            modo="enquadrou",
            apontamentos=(),
            motor=SERVICO_CHAVE,
            versao_servico=sha_servico,
            casos_total=len(casos),
            casos_quarentena=casos_quarentena,
        )

    tem_falha = bool(apontamentos)
    return VereditoTeste(
        alvo=alvo_chave,
        quesito=chave_ficha,
        resultado="nao" if tem_falha else "sim",
        constatacao="divergente" if tem_falha else "conforme",
        modo="enquadrou",
        apontamentos=tuple(apontamentos),
        motor=SERVICO_CHAVE,
        versao_servico=sha_servico,
        casos_total=len(casos),
        casos_quarentena=casos_quarentena,
    )


def julgar_ficha(
    chave_ficha: str,
    arvore: str | Path,
    *,
    opcoes: OpcoesExecucaoTeste | None = None,
) -> VereditoTeste:
    """Julga uma ficha de teste sobre `arvore` e emite o veredito sem estado.

    Seleciona os arquivos cujo cabeçalho de vínculo gera `chave_ficha`, executa os casos
    pelo executor isolado com repetição de erráticos e quarentena válida, e devolve:
    - `sim` / `conforme` quando todo caso que conta passou;
    - `nao` / `divergente` com apontamentos por caso que falhou;
    - `nao-sei` / `inconclusivo` quando nenhum caso ativo julga o alvo.
    """
    cfg = opcoes or OpcoesExecucaoTeste()
    if cfg.prazo_s <= 0:
        raise ErroExecutorTestes(5, "tempo-esgotado", "prazo esgotado antes de iniciar o executor de testes")
    if not isinstance(chave_ficha, str) or not chave_ficha.strip():
        raise ErroExecutorTestes(1, "regua-inexistente", "chave de ficha de teste vazia ou inválida")

    raiz = Path(arvore).resolve()
    chave = chave_ficha.strip()
    alvo_chave = cfg.alvo or raiz.name
    fim = time.monotonic() + cfg.prazo_s

    achou_arquivo, casos = _selecionar_casos_da_ficha(raiz, chave)
    if not achou_arquivo and not cfg.ficha_confirmada:
        raise ErroExecutorTestes(
            1,
            "regua-inexistente",
            f"nenhum arquivo na árvore '{raiz.name}' declara cabeçalho para '{chave}'",
        )
    if not casos:
        return VereditoTeste(
            alvo=alvo_chave,
            quesito=chave,
            resultado="nao-sei",
            constatacao="inconclusivo",
            modo="enquadrou",
            apontamentos=(),
            motor=SERVICO_CHAVE,
            versao_servico=versao_servico(),
            casos_total=0,
            casos_quarentena=0,
        )

    exec_fn = _resolver_executor_isolado(cfg)
    try:
        resultados = _executar_com_repeticao_erratico(
            raiz,
            casos,
            exec_fn,
            cfg.abertas_quarentena,
            prazo_quarentena_dias=cfg.prazo_quarentena_dias,
        )
    except TimeoutError as exc:
        raise ErroExecutorTestes(5, "tempo-esgotado", str(exc) or "prazo esgotado na execução de testes") from exc
    except (FalhaUnidade, OSError, RuntimeError) as exc:
        raise ErroExecutorTestes(3, "dependencia-sem-resposta", str(exc)) from exc

    if time.monotonic() >= fim:
        raise ErroExecutorTestes(5, "tempo-esgotado", f"prazo esgotado ao julgar a ficha '{chave}'")

    return _fechar_veredito(alvo_chave, chave, casos, resultados, cfg)
