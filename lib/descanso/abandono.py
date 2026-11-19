"""A sessão que parou sem descanso fecha como abandonada (regra 29 da F4269, t2 da S4335).

Abandonada é a sessão que tem `sessao_aberta` e não tem `sessao_encerrada` no oplog, com a chave do Valkey já
vencida. Quem a fecha é a abertura seguinte do mesmo sujeito: emite `sessao_encerrada` com desfecho `abandonada`
para cada uma e diz numa linha quantas fechou. Com a memória fora, não conta zero: diz que não conseguiu olhar.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1]
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import oplog  # noqa: E402
from descanso import eventos  # noqa: E402
from descanso.memoria import Fora  # noqa: E402

JANELA_DIAS = 7     # a chave vive 48 h; sete dias cobrem o fim de semana e a semana sem abertura


@dataclass
class Fechamento:
    fechadas: list[str] = field(default_factory=list)
    olhou: bool = True
    motivo: str | None = None

    @property
    def quantas(self) -> int | None:
        return len(self.fechadas) if self.olhou else None

    def linha(self) -> str:
        if not self.olhou:
            return f"não consegui olhar se alguma sessão sua terminou sem descanso: {self.motivo}"
        n = len(self.fechadas)
        if n == 1:
            return "1 sessão sua terminou sem descanso desde a última abertura"
        return f"{n} sessões suas terminaram sem descanso desde a última abertura"

    def como_dict(self) -> dict:
        return {"quantas": self.quantas, "fechadas": self.fechadas, "linha": self.linha(),
                **({"motivo": self.motivo} if self.motivo else {})}


def candidatas(sujeito: str, *, excluir: str | None = None, diretorio_=None, hoje=None) -> list[tuple[str, str | None]]:
    """(sessao_id, cadeira) das sessões abertas pelo sujeito na janela, sem encerrada, na ordem em que abriram."""
    h = hoje or oplog.hoje_local()
    # +1 dia: o arquivo do dia sai no fuso da máquina, e hoje_local é o fuso da porta
    leitura = oplog.ler(h - timedelta(days=JANELA_DIAS), h + timedelta(days=1), diretorio_=diretorio_)
    abertas: dict[str, str | None] = {}
    encerradas: set[str] = set()
    for reg in leitura:
        evento = reg.get("evento")
        if reg.get("correlacao") != sujeito:
            continue
        sid = reg.get("sobre") or reg.get("sessao_id")
        if not sid:
            continue
        if evento == eventos.SESSAO_ABERTA:
            abertas.setdefault(sid, reg.get("cadeira"))
        elif evento == eventos.SESSAO_ENCERRADA:
            encerradas.add(sid)
    return [(sid, cad) for sid, cad in abertas.items() if sid not in encerradas and sid != excluir]


def fechar_abandonadas(sujeito: str, memoria, *, sessao_atual: str | None = None, diretorio_=None,
                       hoje=None) -> Fechamento:
    lista = candidatas(sujeito, excluir=sessao_atual, diretorio_=diretorio_, hoje=hoje)
    fech = Fechamento()
    if not lista:
        return fech
    try:
        paradas = [(sid, cad) for sid, cad in lista if not memoria.existe(sid)]
    except Fora as erro:
        return Fechamento(olhou=False, motivo=str(erro))
    for sid, cad in paradas:
        if eventos.emitir_encerrada(sid, sujeito=sujeito, cadeira=cad, desfecho="abandonada",
                                    diretorio_=diretorio_):
            fech.fechadas.append(sid)
    return fech
