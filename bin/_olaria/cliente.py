"""O cliente do serviço de escrita da Olaria (card #4214).

Fala com `OLARIA_URL` por HTTP, só com a biblioteca padrão, e manda `OLARIA_CHAVE` no cabeçalho `X-Olaria-Chave`. O contrato é o de
`ontologia/olaria/__main__.py`: POST /ler, /listar, /preparar, /ensaiar, /criar, /trocar, /recompor, /renomear, /apagar, /gerar e /raciocinar; GET /ajuda; cabeçalhos `X-Olaria-Sujeito` (a
cadeira que chama, `PF_CADEIRA`) e `X-Olaria-Fornada` (o id uuid v7 que nasce aqui, no gravar e no apagar).

O prazo do verbo é um só para a chamada inteira: 110 s, abaixo do teto de 120 s da peça. Cada pedido usa o que resta dele. A
gravação cuja resposta se perde (conexão que cai, pedido que passa do tempo da chamada) reenvia o mesmo id a cada 5 s, porque o
serviço responde «já gravada» ao id que já gravou, e `em-curso` ao que ainda roda: o reenvio não grava duas vezes. Acabado o prazo,
sobe `PrazoAcabou`, e quem chamou diz o id e a chamada que reconsulta.

Nada aqui imprime a chave: ela só vai no cabeçalho.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import secrets
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

PRAZO_PADRAO_S = 110.0
REENVIO_PADRAO_S = 5.0
UUID_V7 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class AmbienteIncompleto(Exception):
    """Falta uma variável do ambiente; o nome dela é o argumento."""


class SemConexao(Exception):
    """O serviço não aceitou a conexão (recusada, nome que não resolve, rede fora)."""


class SemResposta(Exception):
    """A conexão abriu, mas a resposta não chegou: passou do tempo da chamada ou a conexão caiu no meio."""


class PrazoAcabou(Exception):
    """O prazo do verbo acabou antes de a resposta chegar."""


@dataclass
class Resposta:
    status: int
    corpo: dict


def novo_id(agora_ms: int | None = None) -> str:
    """Um uuid v7 escrito com a biblioteca padrão: 48 bits de milissegundos, a versão 7, 12 bits ao acaso, a variante e 62 ao acaso.
    Cresce com o tempo, e é o que o serviço exige no X-Olaria-Fornada."""
    ms = int(time.time() * 1000) if agora_ms is None else agora_ms
    ao_acaso = int.from_bytes(secrets.token_bytes(10), "big")                    # 80 bits
    valor = (ms & ((1 << 48) - 1)) << 80
    valor |= 0x7 << 76
    valor |= ((ao_acaso >> 68) & 0xFFF) << 64
    valor |= 0b10 << 62
    valor |= ao_acaso & ((1 << 62) - 1)
    h = f"{valor:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def e_uuid7(texto: str) -> bool:
    return bool(UUID_V7.match(texto or ""))


def _ler_cofre(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def preencher_do_cofre(env: dict[str, str]) -> None:
    """Completa OLARIA_URL e OLARIA_CHAVE do cofre da instância quando ausentes no ambiente do processo."""
    instancia = Path(env.get("PLATAFIRMA_INSTANCIA") or "/srv/platafirma/casa")
    if not (env.get("OLARIA_URL") or "").strip():
        env["OLARIA_URL"] = _ler_cofre(instancia / "segredos" / "olaria" / "OLARIA_URL") or "http://127.0.0.1:8103"
    if not (env.get("OLARIA_CHAVE") or "").strip():
        chave = _ler_cofre(instancia / "segredos" / "olaria" / "OLARIA_CHAVE")
        if chave:
            env["OLARIA_CHAVE"] = chave


@dataclass
class Ambiente:
    url: str
    chave: str
    sujeito: str

    @classmethod
    def do_ambiente(cls, env: Mapping | None = None) -> Ambiente:
        """O endereço e a chave vêm do ambiente ou, no processo vivo, do cofre da instância."""
        do_processo = env is None or env is os.environ
        env = os.environ if env is None else env
        instancia = Path(env.get("PLATAFIRMA_INSTANCIA") or "/srv/platafirma/casa")
        url = (env.get("OLARIA_URL") or "").strip()
        chave = (env.get("OLARIA_CHAVE") or "").strip()
        if do_processo:
            if not url:
                url = _ler_cofre(instancia / "segredos" / "olaria" / "OLARIA_URL") or "http://127.0.0.1:8103"
            if not chave:
                chave = _ler_cofre(instancia / "segredos" / "olaria" / "OLARIA_CHAVE")
        if not url:
            raise AmbienteIncompleto("OLARIA_URL")
        if not chave:
            raise AmbienteIncompleto("OLARIA_CHAVE")
        return cls(url=url.rstrip("/"), chave=chave, sujeito=env.get("PF_CADEIRA", ""))


def _numero(env: Mapping, nome: str, padrao: float | None) -> float | None:
    bruto = env.get(nome)
    if not bruto:
        return padrao
    try:
        valor = float(bruto)
    except ValueError:
        return padrao
    return valor if valor > 0 else padrao


class Cliente:
    def __init__(self, ambiente: Ambiente, *, prazo_s: float = PRAZO_PADRAO_S, chamada_s: float | None = None,
                 reenvio_s: float = REENVIO_PADRAO_S, relogio: Callable[[], float] = time.monotonic,
                 dormir: Callable[[float], None] = time.sleep):
        self._amb, self._chamada_s, self._reenvio_s = ambiente, chamada_s, reenvio_s
        self._relogio, self._dormir = relogio, dormir
        self.prazo_s = prazo_s
        self._fim = relogio() + prazo_s

    @classmethod
    def do_ambiente(cls, env: Mapping | None = None) -> Cliente:
        """O prazo, o tempo da chamada e o intervalo do reenvio têm padrão e se trocam pelo ambiente só para prova."""
        env = os.environ if env is None else env
        return cls(Ambiente.do_ambiente(env), prazo_s=_numero(env, "OLARIA_PRAZO_S", PRAZO_PADRAO_S),
                   chamada_s=_numero(env, "OLARIA_CHAMADA_S", None), reenvio_s=_numero(env, "OLARIA_REENVIO_S", REENVIO_PADRAO_S))

    @property
    def sujeito(self) -> str:
        return self._amb.sujeito

    @property
    def url(self) -> str:
        return self._amb.url

    def restante(self) -> float:
        return self._fim - self._relogio()

    # -- o pedido ---------------------------------------------------------------------------------------------------------

    def _pedir(self, metodo: str, rota: str, corpo: dict | None = None, *, pedido_id: str = "",
               origem: str = "") -> Resposta:
        resta = self.restante()
        if resta <= 0:
            raise PrazoAcabou()
        tempo = resta if self._chamada_s is None else min(resta, self._chamada_s)
        dados = None if corpo is None else json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self._amb.url + rota, data=dados, method=metodo)
        req.add_header("X-Olaria-Chave", self._amb.chave)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("User-Agent", "ontologia-verbo")
        if self._amb.sujeito:
            req.add_header("X-Olaria-Sujeito", self._amb.sujeito)
        if pedido_id:
            req.add_header("X-Olaria-Pedido", pedido_id)
            req.add_header("X-Olaria-Fornada", pedido_id)
        if origem:
            req.add_header("X-Olaria-Origem", origem)
        try:
            with urllib.request.urlopen(req, timeout=tempo) as r:
                bruto, status = r.read(), r.status
        except urllib.error.HTTPError as erro:
            bruto, status = erro.read(), erro.code
        except urllib.error.URLError as erro:
            if isinstance(erro.reason, (TimeoutError, socket.timeout)):
                raise SemResposta(f"{type(erro.reason).__name__}: {erro.reason}") from erro
            raise SemConexao(str(erro.reason)) from erro
        except (TimeoutError, socket.timeout, http.client.HTTPException, OSError) as erro:
            raise SemResposta(f"{type(erro).__name__}: {erro}" if str(erro) else type(erro).__name__) from erro
        return Resposta(status, _corpo(bruto))

    def _escrever_com_reenvio(self, rota: str, corpo: dict, pedido_id: str, origem: str = "") -> Resposta:
        enviado = False
        while True:
            try:
                r = self._pedir("POST", rota, corpo, pedido_id=pedido_id, origem=origem)
                enviado = True
            except SemConexao:
                if enviado:
                    raise PrazoAcabou() from None
                raise
            except SemResposta:
                enviado = True
                if self.restante() <= self._reenvio_s:
                    raise PrazoAcabou() from None
                self._dormir(self._reenvio_s)
                continue
            if r.status == 200 and r.corpo.get("estado") == "em-curso":
                if self.restante() <= self._reenvio_s:
                    raise PrazoAcabou()
                self._dormir(self._reenvio_s)
                continue
            return r

    # -- os atos e a ajuda ------------------------------------------------------------------------------------------------

    def ler(self, classe: str, chaves: Sequence[str] = (), fichas: bool = False) -> Resposta:
        return self._pedir("POST", "/ler", {"classe": classe, "chaves": list(chaves), "fichas": bool(fichas)},
                           origem="ontologia ler")

    def listar(self, classe: str = "", *, filhas: str | None = None, aponta_para: str | None = None,
               capacidade: str | None = None) -> Resposta:
        corpo: dict = {"classe": classe}
        if filhas is not None:
            corpo["filhas"] = filhas
        if aponta_para is not None:
            corpo["aponta_para"] = aponta_para
        if capacidade is not None:
            corpo["capacidade"] = capacidade
        return self._pedir("POST", "/listar", corpo, origem="ontologia listar")

    def preparar(self, classe: str, fichas: bool | Sequence[str] = False) -> Resposta:
        return self._pedir("POST", "/preparar",
                           {"classe": classe, "fichas": fichas if isinstance(fichas, bool) else list(fichas)},
                           origem="olaria preparar")

    def ensaiar(self, texto: str, ato: str | None = None, versao: str | None = None) -> Resposta:
        corpo: dict = {"yaml": texto}
        if ato:
            corpo["ato"] = ato
        if versao:
            corpo["versao"] = versao
        return self._pedir("POST", "/ensaiar", corpo, origem="ontologia ensaiar")

    def criar(self, texto: str, pedido_id: str, origem: str = "ontologia criar") -> Resposta:
        return self._escrever_com_reenvio("/criar", {"yaml": texto}, pedido_id, origem)

    def trocar(self, texto: str, versao: str | None, pedido_id: str, origem: str = "ontologia trocar", *,
               classe: str | None = None, chave: str | None = None) -> Resposta:
        corpo: dict = {"yaml": texto}
        if versao:
            corpo["versao"] = versao
        if classe:
            corpo["classe"] = classe
        if chave:
            corpo["chave"] = chave
        return self._escrever_com_reenvio("/trocar", corpo, pedido_id, origem)

    def recompor(self, texto: str, versao: str, pedido_id: str, origem: str = "ontologia recompor") -> Resposta:
        return self._escrever_com_reenvio("/recompor", {"yaml": texto, "versao": versao}, pedido_id, origem)

    def renomear(self, chave: str, nova_chave: str, fornada: str, origem: str = "ontologia renomear",
                 classe: str | None = None) -> Resposta:
        corpo = {"chave": chave, "nova_chave": nova_chave, "origem": origem}
        if classe:
            corpo["classe"] = classe
        return self._escrever_com_reenvio("/renomear", corpo, fornada, origem)

    def apagar(self, chave: str, motivo: str, fornada: str, origem: str = "ontologia apagar",
               classe: str | None = None, com: list | None = None) -> Resposta:
        corpo = {"chave": chave, "motivo": motivo, "origem": origem}
        if classe:
            corpo["classe"] = classe
        if com:
            corpo["com"] = [{"classe": c, "chave": k} for c, k in com]
        return self._escrever_com_reenvio("/apagar", corpo, fornada, origem)

    def transitar(self, classe: str, chave: str, para: str, fornada: str,
                  origem: str = "ontologia transitar") -> Resposta:
        corpo = {"classe": classe, "chave": chave, "para": para, "origem": origem}
        return self._escrever_com_reenvio("/transitar", corpo, fornada, origem)

    def nomes(self, ato: str, itens: list[dict], fornada: str,
              origem: str = "ontologia nomes") -> Resposta:
        corpo = {"ato": ato, "nomes": itens, "origem": origem}
        return self._escrever_com_reenvio("/nomes", corpo, fornada, origem)

    def gerar(self) -> Resposta:
        return self._pedir("POST", "/gerar", {}, origem="ontologia gerar")

    def raciocinar(self, alvo: str, *, origem: str = "conferir ontologia") -> Resposta:
        return self._pedir("POST", "/raciocinar", {"alvo": alvo}, origem=origem)

    def ajuda(self) -> Resposta:
        return self._pedir("GET", "/ajuda")


def _corpo(bruto: bytes) -> dict:
    """O corpo do serviço é sempre um objeto JSON; o que não for vira `erro` com o começo do texto, para a saída dizer o que veio."""
    try:
        corpo = json.loads(bruto or b"{}")
    except ValueError:
        return {"erro": bruto[:300].decode("utf-8", "replace")}
    return corpo if isinstance(corpo, dict) else {"erro": str(corpo)[:300]}
