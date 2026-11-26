"""A mensagem e o ato publicar (regra 30 da F4269; decisões 5268, 5269, 5271 e 5274; t3 da S4335; S4355).

A forma é a da classe mensagem (referencias/classes/mensagem.md), que vem da micropublicação de Clark, Ciccarese e
Goble (2014) com dois campos a mais, o destinatário e o tipo:

  enunciado                 uma frase que se entende sozinha                                obrigatório
  quem                      a parte que disse                                               obrigatório
  destinatario              a chave de ficha de cada parte a quem a mensagem se dirige      obrigatório
  tipo-de-mensagem          um valor do dicionário tipo-de-mensagem                         obrigatório
  etiqueta                  a chave de cada ficha de que a mensagem trata
  apoio                     a chave de cada evidência, uma entrada por evidência
  cita                      onde a parte citada disse a frase
  responde-a                a mensagem anterior a que esta responde
  relacao-com-a-anterior    atualiza, corrige ou retrata
  sobre, ocorrido_em, correlacao   como no núcleo do evento (a sessão vem de PF_SESSAO quando falta)

O ato grava qualquer mensagem, sem ato nem campo por categoria: a lição, a preferência do dono, a premissa e a aresta
se distinguem pela forma, e não por rótulo. Recusa (exit 2) a sem enunciado, sem quem, sem destinatário, sem tipo, de
tipo fora do dicionário, de etiqueta ou destinatário que não é chave de ficha e de relação fora das três.

A mensagem mora no banco de eventos, esfera de negócio, família mensagem (decisão 5269; story 4355).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1]
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

DESTINO = "banco de eventos, esfera de negócio, família mensagem"
NAMESPACE_NEGOCIO = uuid.UUID("18e2a69a-4215-516c-8ee6-18dd0f185f62")
EVENTOS_API_PADRAO = "http://127.0.0.1:8111"
# O dicionário tipo-de-mensagem da mensageria (decisão 5274).
TIPOS = ("afirmacao", "negativa", "pedido", "recusa", "contestacao", "decisao")
RELACOES = ("atualiza", "corrige", "retrata")
FORMA_CHAVE = "<classe>:<slug> ou <cadeira> (ex.: capacidade:busca, chapeu:busca, ia)"
ESQUEMA_JSON = (
    'JSON esperado: {"enunciado": "<frase>", "destinatario": "<classe>:<slug>" ou ["..."], '
    f'"tipo-de-mensagem": "{"|".join(TIPOS)}", '
    '"quem": "<cadeira>" (injetado pela sessão), '
    'opcionais: "etiqueta": "<classe>:<slug>" ou ["..."], "apoio": [...], "cita": "...", '
    f'"responde-a": "<chave>", "relacao-com-a-anterior": "{"|".join(RELACOES)}"'
    "}"
)


def _ajuda_chave(chaves: list[str]) -> str:
    sem_prefixo = [c for c in chaves if ":" not in c]
    dica = f"use chave de ficha na forma {FORMA_CHAVE}"
    if sem_prefixo:
        exemplos = ", ".join(f"capacidade:{c}" for c in sem_prefixo[:3])
        dica += f" (ex.: {exemplos})"
    return dica


class Recusada(ValueError):
    """A mensagem não cumpre a forma."""


class SemDestino(RuntimeError):
    """Nenhum destino de gravação, ou o fichário não respondeu para conferir as chaves."""


# --- o fichário: etiqueta e destinatário só valem como chave de uma ficha que existe ------------------------------

class FicharioFixtura:
    """PF_FICHARIO_FIXTURE: um JSON com a lista das chaves que existem (teste)."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def existentes(self, chaves: list[str]) -> set[str]:
        try:
            todas = set(json.loads(self.caminho.read_text(encoding="utf-8")))
        except (OSError, ValueError) as erro:
            raise SemDestino(f"fichário de teste ilegível: {erro}") from None
        return {c for c in chaves if c in todas}


class FicharioCasa:
    """casa.ficha no banco da casa (casa-db), só leitura."""

    def existentes(self, chaves: list[str]) -> set[str]:
        from postura.casa import Ligacoes, SemBanco
        try:
            return Ligacoes().fichas_existentes(chaves)
        except SemBanco as erro:
            raise SemDestino(f"o fichário não respondeu para conferir as chaves: {erro}") from None


def fichario_do_ambiente():
    fixtura = (os.environ.get("PF_FICHARIO_FIXTURE") or "").strip()
    return FicharioFixtura(fixtura) if fixtura else FicharioCasa()


# --- a mensagem ---------------------------------------------------------------------------------------------------

def _lista(valor) -> list:
    if valor is None or valor == "":
        return []
    return [valor] if isinstance(valor, str) else list(valor)


def _chaves(valor, campo: str) -> list[str]:
    lista = _lista(valor)
    if not all(isinstance(c, str) and c.strip() for c in lista):
        raise Recusada(f"{campo} é a chave de uma ficha, em texto")
    return [c.strip() for c in lista]


@dataclass
class Mensagem:
    enunciado: str
    quem: str
    destinatario: list
    tipo: str
    ocorrido_em: str = ""
    correlacao: str | None = None
    sobre: str | None = None
    etiqueta: list = field(default_factory=list)
    apoio: list = field(default_factory=list)
    cita: str | None = None
    responde_a: str | None = None
    relacao_com_a_anterior: str | None = None

    @classmethod
    def de_dict(cls, dado, *, sessao: str | None = None) -> "Mensagem":
        if not isinstance(dado, dict):
            raise Recusada(f"a mensagem é um objeto JSON · {ESQUEMA_JSON}")
        faltam = []
        enunciado = dado.get("enunciado")
        if not isinstance(enunciado, str) or not enunciado.strip():
            faltam.append("enunciado")
        quem = dado.get("quem")
        if not isinstance(quem, str) or not quem.strip():
            faltam.append("quem")
        destinatario = _chaves(dado.get("destinatario"), "destinatario")
        if not destinatario:
            faltam.append("destinatario")
        tipo = dado.get("tipo-de-mensagem")
        if not tipo:
            faltam.append("tipo-de-mensagem")
        if faltam:
            raise Recusada(f"mensagem sem {', '.join(faltam)} · {ESQUEMA_JSON}")
        if tipo not in TIPOS:
            raise Recusada(f"tipo-de-mensagem fora do dicionário ({', '.join(TIPOS)}): {tipo!r}")
        responde_a, relacao = dado.get("responde-a"), dado.get("relacao-com-a-anterior")
        if relacao is not None and relacao not in RELACOES:
            raise Recusada(f"relacao-com-a-anterior fora de {', '.join(RELACOES)}: {relacao!r}")
        if relacao and not responde_a:
            raise Recusada("relacao-com-a-anterior sem responde-a")
        return cls(
            enunciado=enunciado.strip(), quem=quem.strip(), destinatario=destinatario, tipo=tipo,
            ocorrido_em=str(dado.get("ocorrido_em") or datetime.now().astimezone().isoformat(timespec="seconds")),
            correlacao=dado.get("correlacao") or sessao or None, sobre=dado.get("sobre") or None,
            etiqueta=_chaves(dado.get("etiqueta"), "etiqueta"), apoio=_lista(dado.get("apoio")),
            cita=dado.get("cita") or None, responde_a=responde_a or None, relacao_com_a_anterior=relacao or None,
        )

    def conferir_fichas(self, fichario) -> None:
        """Etiqueta e destinatário só valem como chave de ficha que existe."""
        todas = sorted(set(self.etiqueta) | set(self.destinatario))
        existem = fichario.existentes(todas)
        sem_ficha_dest = sorted(set(self.destinatario) - existem)
        if sem_ficha_dest:
            raise Recusada(f"destinatário que não é chave de ficha: {', '.join(sem_ficha_dest)} · {_ajuda_chave(sem_ficha_dest)}")
        sem_ficha_etq = sorted(set(self.etiqueta) - existem)
        if sem_ficha_etq:
            raise Recusada(f"etiqueta que não é chave de ficha: {', '.join(sem_ficha_etq)} · {_ajuda_chave(sem_ficha_etq)}")

    def chave(self) -> str:
        """A mesma frase, da mesma parte, ao mesmo destinatário, do mesmo tipo e na mesma sessão não grava duas vezes."""
        base = json.dumps([self.enunciado, self.quem, sorted(self.destinatario), self.tipo, self.correlacao,
                           sorted(self.etiqueta)], ensure_ascii=False)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def linha(self) -> dict:
        return {"chave": self.chave(), "enunciado": self.enunciado, "quem": self.quem,
                "destinatario": self.destinatario, "tipo-de-mensagem": self.tipo,
                "ocorrido_em": self.ocorrido_em, "correlacao": self.correlacao, "sobre": self.sobre,
                "etiqueta": self.etiqueta, "apoio": self.apoio, "cita": self.cita,
                "responde-a": self.responde_a, "relacao-com-a-anterior": self.relacao_com_a_anterior}


# --- o destino ----------------------------------------------------------------------------------------------------

class GravadorArquivo:
    """Ensaio fora do banco de eventos: um JSONL só de acréscimo, que não duplica pela chave."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def _gravadas(self) -> set[str]:
        try:
            texto = self.caminho.read_text(encoding="utf-8")
        except FileNotFoundError:
            return set()
        return {json.loads(l)["chave"] for l in texto.splitlines() if l.strip()}

    def gravar(self, msg: Mensagem) -> bool:
        linha = msg.linha()
        if linha["chave"] in self._gravadas():
            return False
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(self.caminho, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        return True


def _ts_utc(valor: str) -> str:
    d = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _formatar_recusados(recusados) -> str:
    if not isinstance(recusados, list) or not recusados:
        return ""
    partes: list[str] = []
    for item in recusados:
        if not isinstance(item, dict):
            partes.append(str(item))
            continue
        indice = item.get("indice")
        prefixo = f"[{indice}] " if indice is not None else ""
        motivo = str(item.get("motivo") or "").strip()
        campo = str(item.get("campo") or "").strip()
        det = str(item.get("detalhe") or "").strip()
        cab = motivo
        if campo:
            cab = f"{cab} ({campo})" if cab else f"({campo})"
        if cab and det:
            partes.append(f"{prefixo}{cab}: {det}")
        elif cab or det:
            partes.append(f"{prefixo}{cab or det}")
    return "; ".join(partes)


class GravadorEventos:
    """Grava a mensagem pela rota POST /eventos/mensagem do banco de eventos (#4355)."""

    def __init__(self, url: str = EVENTOS_API_PADRAO, token: str = "", timeout: float = 15.0):
        self.url = url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout

    def evento_de(self, msg: Mensagem) -> dict:
        origem = msg.chave()
        ev = {
            "evento_id": str(uuid.uuid5(NAMESPACE_NEGOCIO, f"mensagem|{origem}")),
            "ts": _ts_utc(msg.ocorrido_em),
            "produtor": "descansar-publicar",
            "origem": origem,
            "enunciado": msg.enunciado,
            "quem": msg.quem,
            "tipo_de_mensagem": msg.tipo,
            "sobre": msg.sobre or msg.destinatario[0],
            "destinatarios": list(msg.destinatario),
            "etiquetas": list(msg.etiqueta),
            "apoios": list(msg.apoio),
        }
        for chave_ev, valor in (
            ("correlacao", msg.correlacao),
            ("cita", msg.cita),
            ("responde_a", msg.responde_a),
            ("relacao_com_a_anterior", msg.relacao_com_a_anterior),
        ):
            if valor is not None:
                ev[chave_ev] = valor
        return ev

    def gravar(self, msg: Mensagem) -> bool:
        if not self.token:
            raise SemDestino("sem token da esfera de negócio (EVENTOS_NEGOCIO_TOKEN)")
        ev = self.evento_de(msg)
        corpo = json.dumps({"eventos": [ev]}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/eventos/mensagem",
            data=corpo,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                dado = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            try:
                detalhe = json.loads(erro.read().decode("utf-8"))
            except (OSError, ValueError):
                detalhe = {}
            msg_erro = detalhe.get("detalhe") or str(erro)
            if erro.code in (409, 422):
                tipo_erro = str(detalhe.get("tipo", erro.code))
                recusados_txt = _formatar_recusados(detalhe.get("recusados"))
                if recusados_txt:
                    msg_erro = f"{msg_erro} — recusados: {recusados_txt}"
                texto_busca = f"{tipo_erro} {msg_erro}".lower()
                complemento = ""
                if "etiqueta" in texto_busca and msg.etiqueta:
                    complemento = f" · {_ajuda_chave(msg.etiqueta)}"
                elif "destinat" in texto_busca and msg.destinatario:
                    complemento = f" · {_ajuda_chave(msg.destinatario)}"
                raise Recusada(f"{tipo_erro}: {msg_erro}{complemento}") from None
            raise SemDestino(f"banco de eventos respondeu {erro.code}: {msg_erro}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            raise SemDestino(f"banco de eventos mudo ({self.url}): {erro}") from None
        return ev["evento_id"] in dado.get("inseridos", [])


def _token_da_instancia() -> str:
    inst = Path(os.environ.get("PLATAFIRMA_INSTANCIA") or "/srv/platafirma/casa")
    caminho = inst / "segredos" / "eventos" / "EVENTOS_NEGOCIO_TOKEN"
    try:
        return caminho.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def gravador_do_ambiente():
    arquivo = (os.environ.get("PF_MENSAGEM_ARQUIVO") or "").strip()
    if arquivo:
        return GravadorArquivo(arquivo)
    token = (os.environ.get("EVENTOS_NEGOCIO_TOKEN") or "").strip() or _token_da_instancia()
    url = (os.environ.get("EVENTOS_API_URL") or "").strip()
    if token or url:
        if not token:
            raise SemDestino("sem token da esfera de negócio (EVENTOS_NEGOCIO_TOKEN)")
        return GravadorEventos(url=url or EVENTOS_API_PADRAO, token=token)
    raise SemDestino(
        f"sem destino para a mensagem: defina EVENTOS_NEGOCIO_TOKEN ou forneça "
        f"$PLATAFIRMA_INSTANCIA/segredos/eventos/EVENTOS_NEGOCIO_TOKEN para gravar no {DESTINO}"
    )


def publicar(
    dado, gravador=None, fichario=None, *, sessao: str | None = None, cadeira: str | None = None
) -> tuple[Mensagem, bool]:
    """Confere a forma e as chaves de ficha e grava. Devolve a mensagem e se gravou (False: a chave já estava)."""
    if cadeira and isinstance(dado, dict):
        dado = {**dado, "quem": cadeira}
    msg = Mensagem.de_dict(dado, sessao=sessao)
    alvo = gravador or gravador_do_ambiente()
    if fichario is not None or (os.environ.get("PF_FICHARIO_FIXTURE") or "").strip() or not isinstance(alvo, GravadorEventos):
        msg.conferir_fichas(fichario or fichario_do_ambiente())
    return msg, alvo.gravar(msg)
