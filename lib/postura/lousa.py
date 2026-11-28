"""A lousa: o que a sessão tem em vigor e o trabalho da cadeira, guardados na memória de trabalho (Valkey msg-mem).

Fala o protocolo do Valkey direto no socket, sem biblioteca de cliente, para rodar igual no venv do harness, no do rag e no
python do sistema.

Chaves por sessão (com prazo de 4h, renovado pela porta):

  lousa:{<sessao_id>}:postura   um campo por eixo invocado: {peca, sha, motivo, ocorrencia, hora}
  lousa:{<sessao_id>}:ritual    o ritual em vigor: slug, ocorrencia, card, hora
  lousa:{<sessao_id>}:cenario   um campo por cenário presente: {sha, hora}

Chave por cadeira (sem prazo de relógio; sai quando o trabalho fecha):

  lousa:trabalho:{<cadeira>}    um campo por trabalho (card:<N> ou turno:<ordem_id>): JSON de ItemDeTrabalho

Perfil e ramo não se gravam: leem-se do documento a cada chamada.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

PRAZO_S = 4 * 3600      # quatro horas sem chamada da sessão; a porta renova a cada chamada
ENTIDADES = ("postura", "ritual", "cenario")
SITUACOES_TRABALHO = frozenset({"em_curso", "guardado"})
TETO_CORPO_CHARS = 6000  # ~duas folhas A4 de texto corrido; checado só na escrita


class Fora(Exception):
    """A memória de trabalho não respondeu."""


class OcasiaoAusente(ValueError):
    """Tentativa de guardar trabalho na lousa sem ocasião de voltar."""


class CorpoExcedido(ValueError):
    """Corpo do item excede o teto permitido na escrita."""


def validar_teto_corpo(corpo: str, *, teto: int = TETO_CORPO_CHARS) -> None:
    """Valida o tamanho do corpo apenas na escrita; leitura nunca falha por teto."""
    if len(corpo) > teto:
        raise CorpoExcedido(
            f"corpo excede o teto da lousa ({len(corpo)}/{teto} caracteres): "
            "apague o que venceu antes de gravar"
        )


@dataclass(frozen=True)
class EdicaoDeCorpo:
    """Operação única sobre o corpo de um item da lousa, sem tocar na moldura."""

    anexar: str | None = None
    antes: str | None = None
    depois: str | None = None
    substituir: str | None = None
    limpar: bool = False
    todos: bool = False


def _anexar_corpo(atual: str, trecho: str) -> str:
    if not atual:
        return trecho
    if atual.endswith("\n") or trecho.startswith("\n"):
        return atual + trecho
    return f"{atual}\n{trecho}"


def _trocar_trecho_corpo(atual: str, antes: str, depois: str | None, *, todos: bool) -> str:
    if not antes:
        raise ValueError("--antes não pode ser vazio")
    if depois is None:
        raise ValueError("--antes exige --depois (use --depois '' para apagar o trecho)")
    ocorrencias = atual.count(antes)
    if ocorrencias == 0:
        raise ValueError("trecho não encontrado no corpo do item")
    if ocorrencias > 1 and not todos:
        raise ValueError(
            f"trecho aparece {ocorrencias} vezes no corpo; informe mais contexto ou use --todos"
        )
    return atual.replace(antes, depois) if todos else atual.replace(antes, depois, 1)


def editar_corpo(atual: str, edicao: EdicaoDeCorpo, *, teto: int = TETO_CORPO_CHARS) -> str:
    """Edita exclusivamente o corpo do item e valida o resultado contra o teto."""
    modos = sum(
        bool(cond)
        for cond in (
            edicao.limpar,
            edicao.substituir is not None,
            edicao.anexar is not None,
            edicao.antes is not None,
        )
    )
    if modos != 1:
        raise ValueError("informe exatamente uma operação: --anexar, --antes/--depois, --substituir ou --limpar")

    if edicao.limpar:
        novo = ""
    elif edicao.substituir is not None:
        novo = edicao.substituir
    elif edicao.anexar is not None:
        novo = _anexar_corpo(atual, edicao.anexar)
    else:
        novo = _trocar_trecho_corpo(atual, edicao.antes or "", edicao.depois, todos=edicao.todos)

    validar_teto_corpo(novo, teto=teto)
    return novo


def chave(sessao_id: str, entidade: str) -> str:
    return "lousa:{%s}:%s" % (sessao_id, entidade)


def chave_trabalho(cadeira: str) -> str:
    return "lousa:trabalho:{%s}" % cadeira.strip()


def normalizar_card(card: int | str | None) -> str | None:
    if card is None:
        return None
    texto = str(card).strip().lstrip("#").strip()
    return texto or None


def chave_item_trabalho(card: int | str | None = None, turno: str | None = None) -> str:
    card_norm = normalizar_card(card)
    if card_norm:
        return f"card:{card_norm}"
    turno_norm = (turno or "").strip()
    if turno_norm:
        return f"turno:{turno_norm}"
    raise ValueError("chave do trabalho exige card ou id do turno")


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Ocasiao:
    card: str | None = None
    pedido: str | None = None
    chapeu: str | None = None
    estado_card: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "card", normalizar_card(self.card))
        pedido = (self.pedido or "").strip() or None
        chapeu = (self.chapeu or "").strip() or None
        estado = (self.estado_card or "").strip() or None
        object.__setattr__(self, "pedido", pedido)
        object.__setattr__(self, "chapeu", chapeu)
        object.__setattr__(self, "estado_card", estado)

    def vazia(self) -> bool:
        return not (self.card or self.pedido or self.chapeu)

    def como_dict(self) -> dict:
        return {
            "card": self.card,
            "pedido": self.pedido,
            "chapeu": self.chapeu,
            "estado_card": self.estado_card,
        }

    @classmethod
    def de_dict(cls, dado: dict | None) -> Ocasiao | None:
        if not isinstance(dado, dict):
            return None
        oc = cls(
            card=dado.get("card"),
            pedido=dado.get("pedido"),
            chapeu=dado.get("chapeu"),
            estado_card=dado.get("estado_card"),
        )
        return None if oc.vazia() and oc.estado_card is None else oc


@dataclass(frozen=True)
class ItemDeTrabalho:
    chave: str
    cadeira: str
    situacao: str = "em_curso"
    card: str | None = None
    turno: str | None = None
    estagio: str = ""
    proxima_jogada: str = ""
    corpo: str = ""
    chapeu: str | None = None
    ocasiao: Ocasiao | None = None
    guardado_em: str | None = None
    atualizado_em: str | None = None

    def __post_init__(self) -> None:
        chave_norm = (self.chave or "").strip()
        cadeira_norm = (self.cadeira or "").strip()
        situacao_norm = (self.situacao or "em_curso").strip()
        if not chave_norm:
            raise ValueError("chave do trabalho não pode ser vazia")
        if not cadeira_norm:
            raise ValueError("cadeira do trabalho não pode ser vazia")
        if situacao_norm not in SITUACOES_TRABALHO:
            raise ValueError(f"situação inválida: {situacao_norm!r}")
        if situacao_norm == "guardado" and (self.ocasiao is None or self.ocasiao.vazia()):
            raise OcasiaoAusente("ocasião de voltar falta para guardar o trabalho")

        card_norm = normalizar_card(self.card)
        if card_norm is None and chave_norm.startswith("card:"):
            card_norm = normalizar_card(chave_norm.split(":", 1)[1])
        turno_norm = (self.turno or "").strip() or None
        if turno_norm is None and chave_norm.startswith("turno:"):
            turno_norm = chave_norm.split(":", 1)[1].strip() or None

        agora = agora_iso()
        atualizado = (self.atualizado_em or "").strip() or agora
        guardado = (self.guardado_em or "").strip() or (atualizado if situacao_norm == "guardado" else None)

        object.__setattr__(self, "chave", chave_norm)
        object.__setattr__(self, "cadeira", cadeira_norm)
        object.__setattr__(self, "situacao", situacao_norm)
        object.__setattr__(self, "card", card_norm)
        object.__setattr__(self, "turno", turno_norm)
        object.__setattr__(self, "estagio", (self.estagio or "").strip())
        object.__setattr__(self, "proxima_jogada", (self.proxima_jogada or "").strip())
        object.__setattr__(self, "corpo", "" if self.corpo is None else str(self.corpo))
        object.__setattr__(self, "chapeu", (self.chapeu or "").strip() or None)
        object.__setattr__(self, "guardado_em", guardado)
        object.__setattr__(self, "atualizado_em", atualizado)

    def como_dict(self) -> dict:
        return {
            "chave": self.chave,
            "cadeira": self.cadeira,
            "situacao": self.situacao,
            "card": self.card,
            "turno": self.turno,
            "estagio": self.estagio,
            "proxima_jogada": self.proxima_jogada,
            "corpo": self.corpo,
            "chapeu": self.chapeu,
            "ocasiao": self.ocasiao.como_dict() if self.ocasiao is not None else None,
            "guardado_em": self.guardado_em,
            "atualizado_em": self.atualizado_em,
        }

    @classmethod
    def de_dict(cls, dado: dict) -> ItemDeTrabalho:
        return cls(
            chave=str(dado.get("chave") or ""),
            cadeira=str(dado.get("cadeira") or ""),
            situacao=str(dado.get("situacao") or "em_curso"),
            card=dado.get("card"),
            turno=dado.get("turno"),
            estagio=str(dado.get("estagio") or ""),
            proxima_jogada=str(dado.get("proxima_jogada") or ""),
            corpo=str(dado.get("corpo") or ""),
            chapeu=dado.get("chapeu"),
            ocasiao=Ocasiao.de_dict(dado.get("ocasiao")),
            guardado_em=dado.get("guardado_em"),
            atualizado_em=dado.get("atualizado_em"),
        )


@runtime_checkable
class LousaDeTrabalho(Protocol):
    def gravar_trabalho(self, cadeira: str, item: ItemDeTrabalho) -> None: ...
    def ler_trabalho(self, cadeira: str, chave_item: str) -> ItemDeTrabalho | None: ...
    def listar_trabalhos(self, cadeira: str, situacao: str | None = None) -> list[ItemDeTrabalho]: ...
    def apagar_trabalho(self, cadeira: str, chave_item: str) -> bool: ...


def _ordenar_itens(itens: list[ItemDeTrabalho]) -> list[ItemDeTrabalho]:
    return sorted(itens, key=lambda i: (i.atualizado_em or "", i.chave))


class Lousa:
    def __init__(
        self,
        host: str | None = None,
        porta: int | None = None,
        espera_s: float = 2.0,
        *,
        senha: str | None = None,
        instancia_dir: Path | None = None,
    ):
        self.host = host or os.environ.get("MEM_REDIS_HOST", "127.0.0.1")
        self.porta = int(porta or os.environ.get("MEM_REDIS_PORT", "6380"))
        self.espera_s = espera_s
        self._senha = senha
        self._instancia_dir = instancia_dir

    def _obter_senha(self) -> str:
        if self._senha is not None:
            return self._senha
        from pegar_chave_do_armario import SenhaIndisponivel, ler_senha_msg_mem  # noqa: PLC0415

        try:
            return ler_senha_msg_mem(self._instancia_dir)
        except SenhaIndisponivel as erro:
            raise Fora(f"memória de trabalho em {self.host}:{self.porta}: {erro}") from None

    # --- o protocolo -------------------------------------------------------------------------------------------------
    def _manda(self, comandos: list[tuple]) -> list:
        senha = self._obter_senha()
        envio = [("AUTH", "default", senha), *comandos] if senha else list(comandos)
        carga = b""
        for comando in envio:
            partes = [str(p).encode("utf-8") for p in comando]
            carga += b"*%d\r\n" % len(partes) + b"".join(b"$%d\r\n%s\r\n" % (len(p), p) for p in partes)
        try:
            with socket.create_connection((self.host, self.porta), timeout=self.espera_s) as s:
                s.sendall(carga)
                with s.makefile("rb") as f:
                    respostas = [self._le(f) for _ in envio]
                    return respostas[1:] if senha else respostas
        except (OSError, ValueError) as erro:
            msg = str(erro).replace(senha, "[redigido]") if senha else str(erro)
            raise Fora(f"memória de trabalho em {self.host}:{self.porta}: {msg}") from None

    def _le(self, f):
        linha = f.readline()
        if not linha.endswith(b"\r\n"):
            raise ValueError("resposta cortada")
        tipo, resto = linha[:1], linha[1:-2]
        if tipo == b"+":
            return resto.decode()
        if tipo == b"-":
            raise ValueError(resto.decode())
        if tipo == b":":
            return int(resto)
        if tipo == b"$":
            n = int(resto)
            if n < 0:
                return None
            dado = f.read(n + 2)
            return dado[:-2].decode("utf-8", errors="replace")
        if tipo == b"*":
            n = int(resto)
            return None if n < 0 else [self._le(f) for _ in range(n)]
        raise ValueError(f"resposta desconhecida: {linha[:20]!r}")

    def _transacao(self, comandos: list[tuple]) -> list:
        return self._manda([("MULTI",), *comandos, ("EXEC",)])[-1]

    # --- leitura (sessão) --------------------------------------------------------------------------------------------
    def _campos(self, sessao_id: str, entidade: str) -> dict:
        plano = self._manda([("HGETALL", chave(sessao_id, entidade))])[0] or []
        bruto = dict(zip(plano[0::2], plano[1::2]))
        saida = {}
        for campo, valor in bruto.items():
            try:
                saida[campo] = json.loads(valor)
            except ValueError:
                saida[campo] = valor
        return saida

    def invocacoes(self, sessao_id: str) -> dict:
        return {k: v for k, v in self._campos(sessao_id, "postura").items() if isinstance(v, dict)}

    def ritual(self, sessao_id: str) -> dict:
        return self._campos(sessao_id, "ritual")

    def cenarios(self, sessao_id: str) -> dict:
        return {k: v for k, v in self._campos(sessao_id, "cenario").items() if isinstance(v, dict)}

    def chapeu_da_sessao(self, sessao_id: str) -> str:
        """O chapéu gravado na chave hash da sessão."""
        return self.ler_campo_sessao(sessao_id, "chapeu")

    def ler_campo_sessao(self, sessao_id: str, campo: str) -> str:
        """Lê um campo específico do hash `sessao:{sessao_id}`."""
        bruto = self._manda([("HGET", f"sessao:{sessao_id}", campo)])[0]
        return str(bruto or "").strip()

    def gravar_campo_sessao(self, sessao_id: str, campo: str, valor: str) -> None:
        """Grava um campo específico do hash `sessao:{sessao_id}` por HSET atômico."""
        if not sessao_id or not campo:
            return
        self._manda([("HSET", f"sessao:{sessao_id}", campo, str(valor))])

    def prazo(self, sessao_id: str) -> int:
        """Quatro horas, e nunca além do que resta à chave da sessão."""
        resta = self._manda([("TTL", f"sessao:{sessao_id}")])[0]
        return min(PRAZO_S, resta) if isinstance(resta, int) and resta > 0 else PRAZO_S

    # --- escrita (sessão) --------------------------------------------------------------------------------------------
    def _renova(self, sessao_id: str, prazo: int) -> list[tuple]:
        return [("EXPIRE", chave(sessao_id, e), prazo) for e in ENTIDADES]

    def gravar_invocacoes(self, sessao_id: str, campos: dict, ritual: dict | None = None) -> None:
        """Grava um campo por eixo e, quando a invocação vem de um ritual, o ritual, na mesma transação e com o mesmo prazo."""
        prazo = self.prazo(sessao_id)
        comandos: list[tuple] = []
        for eixo, valor in campos.items():
            comandos.append(("HSET", chave(sessao_id, "postura"), eixo, json.dumps(valor, ensure_ascii=False)))
        if ritual:
            comandos.append(("DEL", chave(sessao_id, "ritual")))
            for campo, valor in ritual.items():
                comandos.append(("HSET", chave(sessao_id, "ritual"), campo, str(valor)))
        self._transacao(comandos + self._renova(sessao_id, prazo))

    def apagar_invocacoes(self, sessao_id: str, eixos: list[str], ritual_tambem: bool = False) -> None:
        prazo = self.prazo(sessao_id)
        comandos: list[tuple] = [("HDEL", chave(sessao_id, "postura"), *eixos)] if eixos else []
        if ritual_tambem:
            comandos.append(("DEL", chave(sessao_id, "ritual")))
        if comandos:
            self._transacao(comandos + self._renova(sessao_id, prazo))

    def entrar_cenario(self, sessao_id: str, slug: str, valor: dict) -> None:
        prazo = self.prazo(sessao_id)
        self._transacao([("HSET", chave(sessao_id, "cenario"), slug, json.dumps(valor, ensure_ascii=False)),
                         *self._renova(sessao_id, prazo)])

    def sair_cenario(self, sessao_id: str, slug: str) -> None:
        self._transacao([("HDEL", chave(sessao_id, "cenario"), slug), *self._renova(sessao_id, self.prazo(sessao_id))])

    def apagar_tudo(self, sessao_id: str) -> None:
        """Some com as chaves da sessão, como faria o prazo vencido ou o reinício. Só o ensaio chama."""
        self._manda([("DEL", *[chave(sessao_id, e) for e in ENTIDADES])])

    # --- trabalho por chave (fora da chave da sessão, sem EXPIRE) ----------------------------------------------------
    def gravar_trabalho(self, cadeira: str, item: ItemDeTrabalho) -> None:
        if item.situacao == "guardado" and (item.ocasiao is None or item.ocasiao.vazia()):
            raise OcasiaoAusente("ocasião de voltar falta para guardar o trabalho")
        validar_teto_corpo(item.corpo)
        carga = json.dumps(item.como_dict(), ensure_ascii=False)
        self._manda([("HSET", chave_trabalho(cadeira), item.chave, carga)])

    def ler_trabalho(self, cadeira: str, chave_item: str) -> ItemDeTrabalho | None:
        bruto = self._manda([("HGET", chave_trabalho(cadeira), chave_item)])[0]
        if not bruto:
            return None
        try:
            dado = json.loads(bruto)
        except ValueError:
            return None
        if not isinstance(dado, dict):
            return None
        return ItemDeTrabalho.de_dict(dado)

    def listar_trabalhos(self, cadeira: str, situacao: str | None = None) -> list[ItemDeTrabalho]:
        plano = self._manda([("HGETALL", chave_trabalho(cadeira))])[0] or []
        bruto = dict(zip(plano[0::2], plano[1::2]))
        itens: list[ItemDeTrabalho] = []
        for valor in bruto.values():
            try:
                dado = json.loads(valor)
            except ValueError:
                continue
            if not isinstance(dado, dict):
                continue
            try:
                item = ItemDeTrabalho.de_dict(dado)
            except ValueError:
                continue
            if situacao is None or item.situacao == situacao:
                itens.append(item)
        return _ordenar_itens(itens)

    def apagar_trabalho(self, cadeira: str, chave_item: str) -> bool:
        removidos = self._manda([("HDEL", chave_trabalho(cadeira), chave_item)])[0]
        return bool(removidos)


class LousaEmMemoria:
    """Implementação em memória para testes de unidade, com o mesmo contrato de trabalho da Lousa."""

    def __init__(self, *, fora: bool = False):
        self.fora = fora
        self._trabalhos: dict[str, dict[str, dict]] = {}

    def _checa(self) -> None:
        if self.fora:
            raise Fora("memória de trabalho fora (memória)")

    def gravar_trabalho(self, cadeira: str, item: ItemDeTrabalho) -> None:
        self._checa()
        if item.situacao == "guardado" and (item.ocasiao is None or item.ocasiao.vazia()):
            raise OcasiaoAusente("ocasião de voltar falta para guardar o trabalho")
        validar_teto_corpo(item.corpo)
        self._trabalhos.setdefault(cadeira.strip(), {})[item.chave] = item.como_dict()

    def ler_trabalho(self, cadeira: str, chave_item: str) -> ItemDeTrabalho | None:
        self._checa()
        dado = self._trabalhos.get(cadeira.strip(), {}).get(chave_item)
        return ItemDeTrabalho.de_dict(dado) if isinstance(dado, dict) else None

    def listar_trabalhos(self, cadeira: str, situacao: str | None = None) -> list[ItemDeTrabalho]:
        self._checa()
        itens = [
            ItemDeTrabalho.de_dict(d)
            for d in self._trabalhos.get(cadeira.strip(), {}).values()
            if isinstance(d, dict)
        ]
        if situacao is not None:
            itens = [i for i in itens if i.situacao == situacao]
        return _ordenar_itens(itens)

    def apagar_trabalho(self, cadeira: str, chave_item: str) -> bool:
        self._checa()
        mapa = self._trabalhos.get(cadeira.strip())
        if not mapa or chave_item not in mapa:
            return False
        del mapa[chave_item]
        return True


class LousaFixtura:
    """Fixtura em JSON (`PF_VALKEY_FIXTURE`) compartilhada com `lib/descanso/memoria.py`.

    Armazena a seção `"trabalhos": {<cadeira>: {<chave>: {...}}}` preservando chaves desconhecidas
    (como `"chaves"`) e gravando de forma atômica via arquivo temporário + `os.replace`.
    """

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def _ler(self) -> dict:
        try:
            dado = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            raise Fora(f"fixtura da memória ilegível: {erro}") from None
        if not isinstance(dado, dict):
            raise Fora("fixtura da memória fora de forma")
        if dado.get("fora"):
            raise Fora("memória de trabalho fora (fixtura)")
        return dado

    def _gravar(self, dado: dict) -> None:
        pasta = self.caminho.parent
        pasta.mkdir(parents=True, exist_ok=True)
        fd, tmp_nome = tempfile.mkstemp(prefix=".lousa-", suffix=".json", dir=str(pasta))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as arq:
                json.dump(dado, arq, ensure_ascii=False)
            os.replace(tmp_nome, self.caminho)
        except OSError as erro:
            try:
                os.unlink(tmp_nome)
            except OSError:
                pass
            raise Fora(f"falha ao gravar fixtura da memória: {erro}") from None

    def gravar_trabalho(self, cadeira: str, item: ItemDeTrabalho) -> None:
        if item.situacao == "guardado" and (item.ocasiao is None or item.ocasiao.vazia()):
            raise OcasiaoAusente("ocasião de voltar falta para guardar o trabalho")
        validar_teto_corpo(item.corpo)
        dado = self._ler()
        trabalhos = dado.get("trabalhos")
        if not isinstance(trabalhos, dict):
            trabalhos = {}
        por_cadeira = trabalhos.get(cadeira.strip())
        if not isinstance(por_cadeira, dict):
            por_cadeira = {}
        por_cadeira[item.chave] = item.como_dict()
        trabalhos[cadeira.strip()] = por_cadeira
        dado["trabalhos"] = trabalhos
        self._gravar(dado)

    def ler_trabalho(self, cadeira: str, chave_item: str) -> ItemDeTrabalho | None:
        dado = self._ler()
        trabalhos = dado.get("trabalhos")
        if not isinstance(trabalhos, dict):
            return None
        por_cadeira = trabalhos.get(cadeira.strip())
        if not isinstance(por_cadeira, dict):
            return None
        item_dict = por_cadeira.get(chave_item)
        return ItemDeTrabalho.de_dict(item_dict) if isinstance(item_dict, dict) else None

    def listar_trabalhos(self, cadeira: str, situacao: str | None = None) -> list[ItemDeTrabalho]:
        dado = self._ler()
        trabalhos = dado.get("trabalhos")
        if not isinstance(trabalhos, dict):
            return []
        por_cadeira = trabalhos.get(cadeira.strip())
        if not isinstance(por_cadeira, dict):
            return []
        itens: list[ItemDeTrabalho] = []
        for item_dict in por_cadeira.values():
            if not isinstance(item_dict, dict):
                continue
            try:
                item = ItemDeTrabalho.de_dict(item_dict)
            except ValueError:
                continue
            if situacao is None or item.situacao == situacao:
                itens.append(item)
        return _ordenar_itens(itens)

    def apagar_trabalho(self, cadeira: str, chave_item: str) -> bool:
        dado = self._ler()
        trabalhos = dado.get("trabalhos")
        if not isinstance(trabalhos, dict):
            return False
        por_cadeira = trabalhos.get(cadeira.strip())
        if not isinstance(por_cadeira, dict) or chave_item not in por_cadeira:
            return False
        del por_cadeira[chave_item]
        trabalhos[cadeira.strip()] = por_cadeira
        dado["trabalhos"] = trabalhos
        self._gravar(dado)
        return True

    def ler_campo_sessao(self, sessao_id: str, campo: str) -> str:
        dado = self._ler()
        sessoes = dado.get("sessoes")
        if not isinstance(sessoes, dict):
            return ""
        mapa = sessoes.get(sessao_id)
        if not isinstance(mapa, dict):
            return ""
        return str(mapa.get(campo) or "").strip()

    def gravar_campo_sessao(self, sessao_id: str, campo: str, valor: str) -> None:
        if not sessao_id or not campo:
            return
        import fcntl

        lock_path = self.caminho.with_suffix(self.caminho.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lk:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
            try:
                dado = self._ler() if self.caminho.exists() else {}
                sessoes = dado.get("sessoes")
                if not isinstance(sessoes, dict):
                    sessoes = {}
                mapa = sessoes.get(sessao_id)
                if not isinstance(mapa, dict):
                    mapa = {}
                mapa[campo] = str(valor)
                sessoes[sessao_id] = mapa
                dado["sessoes"] = sessoes
                self._gravar(dado)
            finally:
                fcntl.flock(lk.fileno(), fcntl.LOCK_UN)


def lousa_do_ambiente() -> LousaDeTrabalho:
    fixtura = (os.environ.get("PF_VALKEY_FIXTURE") or "").strip()
    return LousaFixtura(fixtura) if fixtura else Lousa()


def _cli_sessao(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "gravar-sessao":
        sessao_id = (os.environ.get("PF_SESSAO") or "").strip()
        if not sessao_id or sessao_id == "-":
            return 0
        try:
            lousa_do_ambiente().gravar_campo_sessao(sessao_id, argv[1], argv[2])
        except Fora:
            return 0
        return 0
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_cli_sessao(sys.argv[1:]))
