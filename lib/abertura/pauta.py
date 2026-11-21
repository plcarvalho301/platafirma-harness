"""Montagem da distribuição pauta na abertura da sessão (regras 17, 20, 21 e 23 da F4269).

A pauta traz o turno do dono por referência, o trabalho guardado na lousa e as cartas da caixa.
Cada item guardado entra inteiro só quando a ocasião de voltar casa com a sessão:
- o card que o destrava mudou de estado depois que o item foi guardado;
- o turno do dono cita o número do card, a chave do trabalho ou o pedido da ocasião;
- o chapéu vestido na sessão é o chapéu da ocasião.
Card em estado terminal é evictado da lousa e não entra na pauta nem na contagem.
Fora disso, a pauta mostra só a conta dos guardados, sem o item. A pauta não leva marca de cache.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1]
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from postura.lousa import TETO_CORPO_CHARS, Fora, ItemDeTrabalho, LousaDeTrabalho

_RE_CARD = re.compile(r"(?:card\s+#?|#)(\d+)\b", re.IGNORECASE)
_RE_DIGITOS = re.compile(r"^\d+$")
_RE_ISO_VALIDO = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_TAM_MIN_TERMO = 3
_CAMPOS_MIN_CABECALHO = 3
ESTADOS_TERMINAIS = frozenset({
    "entregue",
    "recusada",
    "cancelada",
    "englobada",
    "encerrada",
    "resolvido",
    "descartada",
})

LeitorDeEstadoDeCard = Callable[[Iterable[str], list[str] | None], Mapping[str, object]]

# Reforço da cultura: os itens que chegam colados ao turno do dono no retorno da abertura.
# O texto é da produto; a ordem é a da leitura.
REFORCO: tuple[str, ...] = (
    "antes de afirmar, decidir ou agir sobre algo da casa, conferir no ar e depois no fichário",
    "antes de nomear algo da casa, achar a classe e a instância no fichário; o termo que não existe vai À margem",
    "antes de cada linha ✅, conferir contra o que está no ar",
    "a negação expressa se devolve ao dono com a regra que negou, e não se contorna",
)


def _sem_acento(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").casefold().strip()


def _normalizar_estado(estado: str | None) -> str:
    bruto = (estado or "").split("(", 1)[0].strip()
    return _sem_acento(bruto)


def _instante(valor: datetime | str | float | None) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc).timestamp()
        return valor.timestamp()
    if isinstance(valor, str):
        s = valor.strip()
        if not _RE_ISO_VALIDO.match(s):
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    return None


def estado_eh_terminal(info: object) -> bool:
    if info is None or isinstance(info, bool):
        return False
    if isinstance(info, Mapping):
        fase = _sem_acento(str(info.get("estado_fase") or info.get("fase") or ""))
        if fase == "terminal":
            return True
        estado = _normalizar_estado(str(info.get("estado") or info.get("estado_derivado") or ""))
        return estado in ESTADOS_TERMINAIS
    if isinstance(info, str):
        if _RE_ISO_VALIDO.match(info.strip()):
            return False
        return _normalizar_estado(info) in ESTADOS_TERMINAIS
    return False


def extrair_estado_de_cabecalho(saida: str) -> str | None:
    texto = (saida or "").strip()
    if not texto:
        return None
    if texto.startswith("{"):
        try:
            dado = json.loads(texto)
            if isinstance(dado, dict):
                est = dado.get("estado") or dado.get("estado_derivado")
                return str(est).strip() if est else None
        except ValueError:
            return None
    for linha in texto.splitlines():
        s = linha.strip()
        if s.startswith("#") and "·" in s:
            partes = [p.strip() for p in s.split("·")]
            if len(partes) >= 3 and partes[2]:
                return partes[2].split("(", 1)[0].strip()
    return None


def _achar_tarefas(pf_bin: Path | None = None) -> Path | None:
    candidatos: list[Path] = []
    if pf_bin is not None:
        candidatos.append(pf_bin)
    env_bin = (os.environ.get("PF_BIN") or "").strip()
    if env_bin:
        candidatos.append(Path(env_bin))
    candidatos.append(Path(__file__).resolve().parents[2] / "bin")
    for pasta in candidatos:
        for nome in ("tarefas", "tarefas.py"):
            cam = pasta / nome
            if cam.is_file():
                return cam
    no_path = shutil.which("tarefas")
    return Path(no_path) if no_path else None


def ler_estados_de_cards(
    cards: Iterable[str],
    avisos: list[str] | None = None,
    *,
    pf_bin: Path | None = None,
    timeout_s: float = 3.0,
) -> dict[str, object]:
    """Lê o estado atual dos cards informados (via PF_CARDS_FIXTURE ou `tarefas ler <card> --cabecalho`).

    Em falha ou timeout do rastreador, registra aviso e devolve apenas o que respondeu (sem evictar).
    """
    cards_unicos = sorted({str(c).strip().lstrip("#") for c in cards if c and str(c).strip()})
    fix = (os.environ.get("PF_CARDS_FIXTURE") or "").strip()
    if fix:
        cam = Path(fix)
        try:
            bruto = json.loads(cam.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            if avisos is not None:
                avisos.append(f"rastreador (PF_CARDS_FIXTURE) ilegível: {erro}")
            return {}
        if isinstance(bruto, Mapping):
            return _normalizar_transicoes(bruto)
        return {}

    if not cards_unicos:
        return {}

    exe = _achar_tarefas(pf_bin)
    if exe is None:
        return {}

    resultado: dict[str, object] = {}
    for card in cards_unicos:
        cmd = [sys.executable, str(exe), "ler", card, "--cabecalho"] if exe.suffix == ".py" else [str(exe), "ler", card, "--cabecalho"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
        except (OSError, subprocess.TimeoutExpired) as erro:
            if avisos is not None:
                avisos.append(f"rastreador indisponível ao consultar card #{card}: {erro}")
            continue
        if proc.returncode != 0:
            motivo = (proc.stderr or proc.stdout).strip()[:160] or f"exit {proc.returncode}"
            if avisos is not None:
                avisos.append(f"rastreador não respondeu para card #{card}: {motivo}")
            continue
        estado = extrair_estado_de_cabecalho(proc.stdout)
        if estado:
            resultado[card] = {"estado": estado}
    return resultado


@dataclass(frozen=True)
class Guardado:
    trabalho: str = ""
    chapeu: str | None = None
    card: int | str | None = None
    guardado_em: datetime | str | float | None = None
    card_mudou_em: datetime | str | float | None = None
    id: int | str | None = None
    ato: str = ""
    alvo: str = ""
    ocasiao: str = ""
    texto: str = ""
    chave: str | None = None
    estagio: str = ""
    proxima_jogada: str = ""
    estado_card_guardado: str | None = None
    ocasiao_card: str | None = None
    ocasiao_pedido: str | None = None
    ocasiao_chapeu: str | None = None
    corpo_chars: int = 0

    def __post_init__(self) -> None:
        card_str: str | None = None
        if self.card is not None and str(self.card).strip():
            card_str = str(self.card).strip().lstrip("#")
        elif self.chave and self.chave.startswith("card:"):
            card_str = self.chave.split(":", 1)[1].strip().lstrip("#") or None
        else:
            for fonte in (self.ocasiao, self.alvo, self.trabalho, self.ato, self.texto):
                m = _RE_CARD.search(fonte or "")
                if m:
                    card_str = m.group(1)
                    break
        oc_card = str(self.ocasiao_card).strip().lstrip("#") if self.ocasiao_card else None
        trabalho = self.trabalho
        if not trabalho and self.proxima_jogada:
            trabalho = self.proxima_jogada
        if not trabalho and (self.ato or self.alvo):
            trabalho = f"{self.ato} → {self.alvo}".strip(" →")
        object.__setattr__(self, "trabalho", trabalho)
        object.__setattr__(self, "card", card_str)
        object.__setattr__(self, "ocasiao_card", oc_card or None)

    @classmethod
    def de_item(cls, item: ItemDeTrabalho) -> Guardado:
        oc = item.ocasiao
        chapeu_ocasiao = oc.chapeu if oc is not None else item.chapeu
        return cls(
            trabalho=item.proxima_jogada or item.estagio or item.chave,
            chapeu=chapeu_ocasiao,
            card=item.card,
            guardado_em=item.guardado_em or item.atualizado_em,
            chave=item.chave,
            estagio=item.estagio,
            proxima_jogada=item.proxima_jogada,
            estado_card_guardado=oc.estado_card if oc is not None else None,
            ocasiao_card=oc.card if oc is not None else None,
            ocasiao_pedido=oc.pedido if oc is not None else None,
            ocasiao_chapeu=oc.chapeu if oc is not None else None,
            ocasiao=(oc.pedido or "") if oc is not None else "",
            corpo_chars=len(item.corpo),
        )

    def linha_completa(self) -> str:
        if self.chave:
            partes = [self.chave]
            if self.estagio:
                partes.append(f"[{self.estagio}]")
            if self.proxima_jogada:
                partes.append(self.proxima_jogada)
            elif self.trabalho and self.trabalho != self.chave:
                partes.append(self.trabalho)
            if self.ocasiao_card:
                partes.append(f"(ocasião: card #{self.ocasiao_card})")
            elif self.ocasiao_chapeu:
                partes.append(f"(ocasião: chapéu {self.ocasiao_chapeu})")
            elif self.ocasiao_pedido:
                partes.append(f"(ocasião: {self.ocasiao_pedido})")
            if self.corpo_chars > 0:
                partes.append(f"(corpo: {self.corpo_chars}/{TETO_CORPO_CHARS})")
            return " ".join(partes)

        prefixo = f"#{self.id} " if self.id is not None and str(self.id) != "" else ""
        bloco_chapeu = f"[{self.chapeu}] " if self.chapeu else ""
        if self.ato and self.alvo:
            corpo = f"{self.ato} → {self.alvo}"
        else:
            corpo = self.trabalho or self.texto or self.alvo or self.ato
        linha = f"{prefixo}{bloco_chapeu}{corpo}".strip()
        if self.texto and self.texto != corpo:
            extra = "\n".join(f"  {lin}" for lin in self.texto.splitlines() if lin.strip())
            if extra:
                linha = f"{linha}\n{extra}"
        return linha

    def como_dict(self) -> dict:
        d: dict = {
            "trabalho": self.trabalho,
            "chapeu": self.chapeu,
            "card": self.card,
        }
        if self.chave is not None:
            d["chave"] = self.chave
        if self.id is not None:
            d["id"] = self.id
        if self.estagio:
            d["estagio"] = self.estagio
        if self.proxima_jogada:
            d["proxima_jogada"] = self.proxima_jogada
        if self.ato:
            d["ato"] = self.ato
        if self.alvo:
            d["alvo"] = self.alvo
        if self.ocasiao:
            d["ocasiao"] = self.ocasiao
        if self.ocasiao_card:
            d["ocasiao_card"] = self.ocasiao_card
        if self.ocasiao_pedido:
            d["ocasiao_pedido"] = self.ocasiao_pedido
        if self.ocasiao_chapeu:
            d["ocasiao_chapeu"] = self.ocasiao_chapeu
        if self.estado_card_guardado:
            d["estado_card_guardado"] = self.estado_card_guardado
        if self.texto:
            d["texto"] = self.texto
        return d


@dataclass(frozen=True)
class Carta:
    id: str = ""
    de: str = ""
    assunto: str = ""
    corpo: str = ""
    texto: str = ""

    def linha_completa(self) -> str:
        if self.texto:
            return self.texto.strip()
        partes = [p for p in (self.id, self.de, self.assunto, self.corpo) if p]
        return " · ".join(partes)

    def como_dict(self) -> dict:
        return {
            "id": self.id,
            "de": self.de,
            "assunto": self.assunto,
            "corpo": self.corpo,
            "texto": self.linha_completa(),
        }


def _normalizar_transicoes(
    fonte: Mapping[int | str, object] | Iterable[int | str] | None,
) -> dict[str, object]:
    mapa: dict[str, object] = {}
    if isinstance(fonte, Mapping):
        for k, v in fonte.items():
            chave = str(k).strip().lstrip("#")
            if chave:
                mapa[chave] = v
    elif fonte is not None:
        for k in fonte:
            chave = str(k).strip().lstrip("#")
            if chave:
                mapa[chave] = True
    return mapa


@dataclass(frozen=True)
class ContextoDaSessao:
    cadeira: str = ""
    chapeu: str | None = None
    turno: str = ""
    transicoes_de_card: Mapping[int | str, object] | Iterable[int | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "transicoes_de_card", _normalizar_transicoes(self.transicoes_de_card))


@dataclass(frozen=True)
class Pauta:
    turno: str
    guardados: list[Guardado]
    total_guardados: int
    fora_da_ocasiao: int
    cartas: list[Carta]
    conteudo: str
    reforco: tuple[str, ...] = REFORCO
    lousa_erro: str | None = None
    caixa_erro: str | None = None

    @property
    def texto(self) -> str:
        return self.conteudo

    def como_dict(self) -> dict:
        d = {
            "turno": self.turno,
            "reforco": list(self.reforco),
            "guardados": [g.como_dict() for g in self.guardados],
            "total_guardados": self.total_guardados,
            "fora_da_ocasiao": self.fora_da_ocasiao,
            "cartas": [c.como_dict() for c in self.cartas],
            "conteudo": self.conteudo,
        }
        if self.lousa_erro:
            d["lousa_erro"] = self.lousa_erro
        if self.caixa_erro:
            d["caixa_erro"] = self.caixa_erro
        return d


def _info_card_mudou(
    info: object,
    ts_guardado: float | None,
    estado_guardado: str | None = None,
) -> bool:
    if isinstance(info, bool):
        return info
    if info is None or estado_eh_terminal(info):
        return False
    if isinstance(info, Mapping):
        if info.get("andou") is True:
            return True
        estado_atual = _normalizar_estado(str(info.get("estado") or info.get("estado_derivado") or ""))
        if estado_guardado and estado_atual and estado_atual != _normalizar_estado(estado_guardado):
            return True
        mudou = info.get("ultimo_movimento") or info.get("mudou_em") or info.get("atualizado_em")
        ts_mudou = _instante(mudou)
        if ts_mudou is not None:
            return ts_guardado is None or ts_mudou > ts_guardado
        return False
    ts_mudou = _instante(info)  # type: ignore[arg-type]
    if ts_mudou is not None:
        return ts_guardado is None or ts_mudou > ts_guardado
    if isinstance(info, str) and estado_guardado:
        return _normalizar_estado(info) != _normalizar_estado(estado_guardado)
    return False


def _card_andou(item: Guardado, sessao: ContextoDaSessao) -> bool:
    ts_guardado = _instante(item.guardado_em)
    if item.card_mudou_em is not None:
        ts_mudou = _instante(item.card_mudou_em)
        if ts_mudou is not None and (ts_guardado is None or ts_mudou > ts_guardado):
            return True
    cards_item = [c for c in (item.ocasiao_card, item.card) if c]
    if not cards_item:
        return False
    mapa = sessao.transicoes_de_card if isinstance(sessao.transicoes_de_card, Mapping) else {}
    for card in dict.fromkeys(cards_item):
        chave = str(card).strip().lstrip("#")
        if chave in mapa and _info_card_mudou(mapa[chave], ts_guardado, item.estado_card_guardado):
            return True
    return False


def _citado_no_turno(item: Guardado, turno: str) -> bool:
    if not turno or not turno.strip():
        return False
    if item.chave:
        chave_cf = item.chave.strip().casefold()
        turno_cf = turno.casefold()
        if chave_cf and chave_cf in turno_cf:
            return True
        if chave_cf.startswith("turno:"):
            id_turno = chave_cf.split(":", 1)[1].strip()
            if len(id_turno) >= _TAM_MIN_TERMO and id_turno in turno_cf:
                return True
    for card in (item.card, item.ocasiao_card):
        if card:
            num = re.escape(str(card).strip().lstrip("#"))
            if re.search(rf"(?<!\d)#?{num}(?!\d)", turno):
                return True
    turno_norm = _sem_acento(turno)
    for candidato in (item.ocasiao_pedido, item.trabalho, item.alvo, item.ocasiao):
        cand_norm = _sem_acento(candidato or "")
        if len(cand_norm) < _TAM_MIN_TERMO:
            continue
        sem_card = re.sub(r"^card\s+#?\d+\s*[:\-–—]?\s*", "", cand_norm).strip()
        for termo in (cand_norm, sem_card):
            if len(termo) >= _TAM_MIN_TERMO and not _RE_DIGITOS.match(termo) and termo in turno_norm:
                return True
    return False


def ocasiao_casa(item: Guardado, sessao: ContextoDaSessao) -> bool:
    """Retorna True se a ocasião do item guardado casa com a sessão atual."""
    chapeu_item = item.ocasiao_chapeu or item.chapeu
    if sessao.chapeu and chapeu_item and _sem_acento(sessao.chapeu) == _sem_acento(chapeu_item):
        return True
    if _card_andou(item, sessao):
        return True
    return bool(_citado_no_turno(item, sessao.turno))


def carregar_guardados_da_lousa(
    cadeira: str,
    lousa: LousaDeTrabalho,
    *,
    leitor_cards: LeitorDeEstadoDeCard | None = None,
    avisos: list[str] | None = None,
) -> tuple[list[Guardado], dict[str, object]]:
    """Carrega os guardados da lousa da cadeira e evicta itens cujo card está em estado terminal."""
    try:
        itens = lousa.listar_trabalhos(cadeira, situacao="guardado")
    except Fora as erro:
        if avisos is not None:
            avisos.append(f"lousa indisponível: {erro}")
        return [], {}

    cards_para_checar: list[str] = []
    for item in itens:
        if item.card:
            cards_para_checar.append(item.card)
        if item.ocasiao and item.ocasiao.card:
            cards_para_checar.append(item.ocasiao.card)

    leitor = leitor_cards or ler_estados_de_cards
    estados = _normalizar_transicoes(leitor(cards_para_checar, avisos))

    guardados: list[Guardado] = []
    for item in itens:
        cards_item = [c for c in (item.card, item.ocasiao.card if item.ocasiao else None) if c]
        terminal = any(estado_eh_terminal(estados.get(c)) for c in cards_item)
        if terminal:
            try:
                lousa.apagar_trabalho(cadeira, item.chave)
            except Fora as erro:
                if avisos is not None:
                    avisos.append(f"lousa indisponível ao evictar {item.chave}: {erro}")
            continue
        guardados.append(Guardado.de_item(item))

    return guardados, estados


def montar_pauta(
    guardados: list[Guardado],
    cartas: list[Carta],
    sessao: ContextoDaSessao,
    *,
    lousa_erro: str | None = None,
    caixa_erro: str | None = None,
) -> Pauta:
    """Monta a distribuição pauta ordenada pela leitura, sem marca de cache."""
    visiveis = [g for g in guardados if ocasiao_casa(g, sessao)]
    total = len(guardados)
    fora = total - len(visiveis)
    ref_turno = "turno do dono: por referência (já está na janela)"

    linhas: list[str] = [ref_turno, "reforço:"]
    linhas.extend(f"- {item}" for item in REFORCO)
    if lousa_erro:
        linhas.append(f"lousa: não foi possível ler ({lousa_erro})")
    elif total == 0:
        linhas.append("lousa: 0 guardados")
    elif fora > 0 and visiveis:
        linhas.append(f"lousa: {total} guardado(s) ({len(visiveis)} na ocasião, {fora} fora da ocasião)")
        for g in visiveis:
            linhas.append(f"- {g.linha_completa()}")
    elif fora > 0:
        linhas.append(f"lousa: {total} guardado(s) ({fora} fora da ocasião)")
    else:
        linhas.append(f"lousa: {total} guardado(s)")
        for g in visiveis:
            linhas.append(f"- {g.linha_completa()}")

    if caixa_erro:
        linhas.append(f"caixa: não foi possível ler ({caixa_erro})")
    elif not cartas:
        linhas.append("caixa: 0 cartas")
    else:
        linhas.append(f"caixa: {len(cartas)} carta(s)")
        for c in cartas:
            linhas.append(f"- {c.linha_completa()}")

    conteudo = "\n".join(linhas)
    return Pauta(
        turno=ref_turno,
        guardados=visiveis,
        total_guardados=total,
        fora_da_ocasiao=fora,
        cartas=list(cartas),
        conteudo=conteudo,
        lousa_erro=lousa_erro,
        caixa_erro=caixa_erro,
    )


def ler_cartas_da_fila(saida: str) -> list[Carta]:
    """Converte a saída de `fila ler` em lista de `Carta`."""
    texto = (saida or "").strip()
    if not texto or "nenhuma mensagem" in texto.lower() or "caixa vazia" in texto.lower() or texto == "(vazia)":
        return []
    if texto.startswith(("[", "{")):
        dados = json.loads(texto)
        lista = dados.get("mensagens") or dados.get("cartas") or [] if isinstance(dados, dict) else dados
        if isinstance(lista, list):
            return [
                Carta(
                    id=str(c.get("id") or c.get("msgid") or ""),
                    de=str(c.get("de") or c.get("remetente") or ""),
                    assunto=str(c.get("assunto") or ""),
                    corpo=str(c.get("corpo") or c.get("texto") or ""),
                )
                for c in lista
                if isinstance(c, dict)
            ]
    return [Carta(texto=linha.strip()) for linha in texto.splitlines() if linha.strip()]
