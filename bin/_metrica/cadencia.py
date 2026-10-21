"""cadencia — o que vence a cada passada da sonda (spec eixos-do-host R15; card #3922).

O registro `registro/cadencia-eixos.json` diz de quanto em quanto tempo cada eixo, stack e serviço é lido. O código não
guarda número de cadência nenhum além da definição: o intervalo é múltiplo de um minuto, porque o timer da sonda passa
de minuto em minuto e não alcança menos. Registro que não cumpre o formato recusa, e a passada para com a causa: a
cadência nunca vem de outro lugar.

COMO UM INTERVALO SE RESOLVE. Para o consumidor de um eixo: a entrada do serviço, depois a da stack, depois a do eixo,
depois o `padrao_s`. O intervalo do eixo é o piso do total, não o teto: serviço lido com mais frequência que o eixo
leva o total junto, da mesma coleta, e o eixo não é lido de novo por isso.

O QUE UMA PASSADA FAZ COM ISSO. `planejar` olha o estado (quando cada coisa entrou na série pela última vez) e diz,
por eixo, se ele é lido (`le`), se a lista dele vence (`lista_vence`: os consumidores sem entrada própria entram na
amostra), quais entradas explícitas do registro venceram e qual é a `janela` da amostra: o menor intervalo aplicável
ao eixo, que é o maior intervalo até a amostra seguinte. `registrar` anota no estado o que a passada fez. O estado é
um JSON na pasta da instância, escrito atômico; arquivo ausente ou ilegível vale estado vazio, e estado vazio vence
tudo (a série prefere uma amostra a mais a uma a menos).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EIXOS = ("rede", "ram", "vram", "cpu")
MINUTO_S = 60
PARTES_DA_CHAVE_DE_SERVICO = 2   # `<stack>/<serviço>`
REGISTRO = Path(__file__).resolve().parents[2] / "registro" / "cadencia-eixos.json"
ESTADO_NOME = "cadencia.json"
_CHAVES_DO_REGISTRO = frozenset({"padrao_s", "eixos", "stacks", "servicos"})


class RegistroInvalido(ValueError):
    """O registro não cumpre o formato: a passada para com a causa."""


def _segundos(valor: object, onde: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise RegistroInvalido(f"{onde}: o intervalo é um inteiro de segundos, veio {valor!r}")
    if valor < MINUTO_S or valor % MINUTO_S:
        raise RegistroInvalido(
            f"{onde}: {valor} s não é múltiplo de um minuto (o timer da sonda passa de minuto em minuto)")
    return valor


def _por_eixo(valor: object, onde: str, *, aceita_numero: bool) -> dict[str, int]:
    """Um objeto {eixo: intervalo}; com `aceita_numero`, um número só vale nos quatro eixos."""
    if isinstance(valor, dict):
        fora = sorted(set(valor) - set(EIXOS))
        if fora:
            raise RegistroInvalido(f"{onde}: eixo fora de {EIXOS}: {fora}")
        return {eixo: _segundos(v, f"{onde}.{eixo}") for eixo, v in valor.items()}
    if not aceita_numero:
        raise RegistroInvalido(f"{onde}: esperava um objeto {{eixo: segundos}}, veio {valor!r}")
    numero = _segundos(valor, onde)
    return dict.fromkeys(EIXOS, numero)


def _entradas(bruto: object, onde: str, *, com_barra: bool) -> dict[str, dict[str, int]]:
    if not isinstance(bruto, dict):
        raise RegistroInvalido(f"{onde}: esperava um objeto, veio {bruto!r}")
    saida = {}
    for chave, valor in bruto.items():
        partes = chave.split("/")
        if (len(partes) == PARTES_DA_CHAVE_DE_SERVICO) != com_barra or not all(partes):
            forma = "<stack>/<serviço>" if com_barra else "<stack>, sem barra"
            raise RegistroInvalido(f"{onde}: a chave {chave!r} não tem a forma {forma}")
        saida[chave] = _por_eixo(valor, f"{onde}.{chave}", aceita_numero=True)
    return saida


def validar(bruto: object) -> dict:
    """O registro normalizado: `padrao_s`, `eixos` e, por stack e por serviço, o intervalo de cada eixo."""
    if not isinstance(bruto, dict):
        raise RegistroInvalido("o registro é um objeto JSON")
    desconhecidos = sorted(c for c in bruto if not c.startswith("_") and c not in _CHAVES_DO_REGISTRO)
    if desconhecidos:
        raise RegistroInvalido(f"campo desconhecido: {desconhecidos}")
    if "padrao_s" not in bruto:
        raise RegistroInvalido("falta `padrao_s`: a cadência não mora no código")
    return {
        "padrao_s": _segundos(bruto["padrao_s"], "padrao_s"),
        "eixos": _por_eixo(bruto.get("eixos") or {}, "eixos", aceita_numero=False),
        "stacks": _entradas(bruto.get("stacks") or {}, "stacks", com_barra=False),
        "servicos": _entradas(bruto.get("servicos") or {}, "servicos", com_barra=True),
    }


def carregar(caminho: str | Path | None = None) -> dict:
    """Lê e valida o registro (o do harness, ou o que `SINAL_CADENCIA` aponta, para teste)."""
    arquivo = Path(caminho or os.environ.get("SINAL_CADENCIA") or REGISTRO)
    try:
        bruto = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise RegistroInvalido(f"{arquivo}: {type(e).__name__}") from None
    return validar(bruto)


# --- o intervalo de cada coisa ------------------------------------------------------------------------

def intervalo(reg: dict, eixo: str, servico: str | None = None) -> int:
    """Segundos entre duas entradas do `servico` (ou do eixo, sem ele) na série do `eixo`."""
    if servico:
        proprio = reg["servicos"].get(servico, {}).get(eixo)
        if proprio is not None:
            return proprio
        da_stack = reg["stacks"].get(servico.split("/", 1)[0], {}).get(eixo)
        if da_stack is not None:
            return da_stack
    return reg["eixos"].get(eixo, reg["padrao_s"])


def entradas_do_eixo(reg: dict, eixo: str) -> dict[str, int]:
    """As entradas explícitas do registro que alcançam o eixo: {`servico:<chave>` ou `stack:<slug>`: intervalo}."""
    saida = {f"stack:{stack}": por[eixo] for stack, por in reg["stacks"].items() if eixo in por}
    saida.update({f"servico:{chave}": por[eixo] for chave, por in reg["servicos"].items() if eixo in por})
    return saida


def entrada_do_consumidor(reg: dict, eixo: str, servico: str | None) -> str | None:
    """A entrada explícita que manda no consumidor (a do serviço, senão a da stack), ou None se ele segue o eixo."""
    if not servico:
        return None
    if eixo in reg["servicos"].get(servico, {}):
        return f"servico:{servico}"
    stack = servico.split("/", 1)[0]
    if eixo in reg["stacks"].get(stack, {}):
        return f"stack:{stack}"
    return None


def janela_s(reg: dict, eixo: str) -> int:
    """A janela da amostra: o menor intervalo que alcança o eixo, o maior intervalo até a amostra seguinte."""
    return min([intervalo(reg, eixo), *entradas_do_eixo(reg, eixo).values()])


# --- o que vence ------------------------------------------------------------------------------------

def minuto_de(agora: datetime) -> datetime:
    return agora.astimezone(timezone.utc).replace(second=0, microsecond=0)


def _instante(texto: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")) if texto else None
    except (ValueError, AttributeError):
        return None


def vence(ultimo: str | None, minuto: datetime, intervalo_s: int) -> bool:
    """O intervalo venceu desde a última vez? Sem última vez, ou com ela ilegível, vence."""
    anterior = _instante(ultimo)
    return anterior is None or (minuto - anterior).total_seconds() >= intervalo_s


@dataclass(frozen=True)
class Plano:
    eixo: str
    le: bool
    lista_vence: bool
    entradas_vencidas: frozenset[str]
    janela_s: int


def planejar(reg: dict, estado: dict, minuto: datetime) -> dict[str, Plano]:
    """Por eixo: lê quando a lista dele vence ou quando vence alguma entrada explícita que o alcança."""
    planos = {}
    for eixo in EIXOS:
        lista_vence = vence(estado.get("lista", {}).get(eixo), minuto, intervalo(reg, eixo))
        vencidas = frozenset(
            entrada for entrada, segundos in entradas_do_eixo(reg, eixo).items()
            if vence(estado.get("entradas", {}).get(f"{eixo}|{entrada}"), minuto, segundos))
        planos[eixo] = Plano(eixo, lista_vence or bool(vencidas), lista_vence, vencidas, janela_s(reg, eixo))
    return planos


def entra(reg: dict, plano: Plano, consumidor: dict) -> bool:
    """O consumidor entra na amostra? O que tem entrada própria entra quando ela vence; o resto segue a lista do eixo."""
    entrada = entrada_do_consumidor(reg, plano.eixo, consumidor.get("servico"))
    return entrada in plano.entradas_vencidas if entrada else plano.lista_vence


def registrar(estado: dict, plano: Plano, minuto: datetime) -> None:
    """Anota no estado o que a passada fez no eixo: a lista, se entrou, e cada entrada explícita que venceu."""
    marca = minuto.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if plano.lista_vence:
        estado.setdefault("lista", {})[plano.eixo] = marca
    for entrada in plano.entradas_vencidas:
        estado.setdefault("entradas", {})[f"{plano.eixo}|{entrada}"] = marca


# --- o estado ---------------------------------------------------------------------------------------

def ler_estado(pasta: Path) -> dict:
    try:
        estado = json.loads((pasta / ESTADO_NOME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return estado if isinstance(estado, dict) else {}


def gravar_estado(pasta: Path, estado: dict) -> None:
    """Escrita atômica: quem lê nunca vê meio estado."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / ESTADO_NOME
    provisorio = pasta / f".{ESTADO_NOME}.{os.getpid()}"
    with open(provisorio, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(provisorio, destino)
