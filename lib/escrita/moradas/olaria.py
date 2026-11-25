"""Adaptador da morada banco (Olaria): criar, trocar e ensaiar via HTTP local."""
from __future__ import annotations

import http.client
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from ..registro import LinhaOperacao
from ..tipos import ErroEscrita, RecusaEscrita, ResultadoEscrita
from . import (
    ExecucaoMorada,
    proximo_repeticao_pedido,
    registrar_operacao_sucesso,
)

_HTTP_OK = 200
_HTTP_BAD_REQUEST = 400
_HTTP_FORBIDDEN = 403
_HTTP_UNPROCESSABLE = 422
_HTTP_SERVICE_UNAVAILABLE = 503

_MAPA_CODIGOS_OLARIA: dict[str, tuple[int, str]] = {
    "alvo-inexistente": (1, "alvo-inexistente"),
    "nao-existe": (1, "alvo-inexistente"),
    "ja-existe": (2, "ja-existe"),
    "versao-ausente": (2, "versao-ausente"),
    "versao-invalida": (2, "versao-invalida"),
    "versao-divergente": (2, "versao-divergente"),
    "versao-desatualizada": (2, "versao-divergente"),
    "pedido-com-conteudo-diferente": (2, "pedido-com-conteudo-diferente"),
    "em-curso": (2, "em-curso"),
    "conteudo-vazio": (2, "conteudo-vazio"),
}


@dataclass(frozen=True)
class ConfigOlaria:
    """Configuração de conexão com o serviço Olaria (chave nunca aparece no repr)."""

    url: str
    chave: str = field(repr=False)
    timeout_padrao_s: float = 15.0


@dataclass(frozen=True)
class RespostaHTTP:
    """Resposta bruta decodificada de uma chamada HTTP à Olaria."""

    status: int
    corpo: dict[str, Any]


TransporteOlaria = Callable[
    [str, str, dict[str, str], dict[str, Any], float], RespostaHTTP
]


class _ErroAntesEnvio(Exception):
    """Falha de conexão antes do envio da gravação (ponto de não volta não atingido)."""


class _ErroAposEnvio(Exception):
    """Falha após envio da gravação (timeout ou conexão perdida; indeterminável)."""

    def __init__(self, codigo: str, detalhe: str) -> None:
        self.codigo = codigo
        super().__init__(detalhe)


def _chamar_http_olaria(
    url_base: str,
    rota: str,
    cabecalhos: dict[str, str],
    corpo: dict[str, Any],
    timeout_s: float,
) -> RespostaHTTP:
    parsed = urlparse(url_base)
    host = parsed.hostname or "127.0.0.1"
    porta = parsed.port or (443 if parsed.scheme == "https" else 80)
    prefixo = parsed.path.rstrip("/")
    caminho = f"{prefixo}{rota}"
    conn_cls = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )
    conn = conn_cls(host, porta, timeout=max(0.05, timeout_s))
    try:
        try:
            conn.connect()
        except OSError as exc:
            raise _ErroAntesEnvio(str(exc)) from exc
        payload = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        hdrs = {
            **cabecalhos,
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(payload)),
        }
        try:
            conn.request("POST", caminho, body=payload, headers=hdrs)
            resp = conn.getresponse()
            bruto = resp.read()
        except TimeoutError as exc:
            raise _ErroAposEnvio("tempo-esgotado", str(exc)) from exc
        except (http.client.HTTPException, OSError) as exc:
            raise _ErroAposEnvio("resposta-perdida", str(exc)) from exc
        try:
            dados = json.loads(bruto or b"{}")
        except ValueError:
            dados = {"erro": bruto[:300].decode("utf-8", "replace")}
        if not isinstance(dados, dict):
            dados = {"erro": str(dados)[:300]}
        return RespostaHTTP(status=resp.status, corpo=dados)
    finally:
        conn.close()


def _prazo_restante_s(execucao: ExecucaoMorada, padrao_s: float) -> float:
    if execucao.prazo_ns <= 0:
        return padrao_s
    restante_ns = execucao.prazo_ns - time.monotonic_ns()
    if restante_ns <= 0:
        raise RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="morada-sem-resposta",
                onde="prazo",
                recebido="prazo esgotado antes do envio à Olaria",
                regra="falha antes do ponto de não volta sai 3",
                cura="repita a chamada com prazo suficiente",
                proximo="",
            )
        )
    return restante_ns / 1_000_000_000.0


def _montar_requisicao_olaria(
    execucao: ExecucaoMorada, chave_servico: str, prazo_s: float
) -> tuple[str, dict[str, str], dict[str, Any]]:
    ped = execucao.pedido
    dec = execucao.decisao
    alvo = execucao.alvo.alvo
    cabecalhos = {
        "X-Olaria-Chave": chave_servico,
        "X-Olaria-Sujeito": dec.sujeito,
        "X-Olaria-Origem": f"{dec.verbo} {dec.forma}",
        "X-Olaria-Prazo-Ms": str(max(1, int(prazo_s * 1000))),
    }
    if ped.forma == "ensaiar":
        corpo: dict[str, Any] = {"yaml": ped.conteudo or ""}
        if ped.forma_ensaiada:
            corpo["ato"] = ped.forma_ensaiada
        if ped.versao:
            corpo["versao"] = ped.versao
        return "/ensaiar", cabecalhos, corpo

    cabecalhos["X-Olaria-Pedido"] = ped.pedido
    cabecalhos["X-Olaria-Fornada"] = ped.pedido
    if ped.forma == "criar":
        return "/criar", cabecalhos, {"yaml": ped.conteudo or ""}
    corpo_trocar: dict[str, Any] = {
        "yaml": ped.conteudo or "",
        "classe": dec.classe,
        "chave": alvo.chave,
    }
    if ped.versao is not None:
        corpo_trocar["versao"] = ped.versao
    return "/trocar", cabecalhos, corpo_trocar


def _extrair_codigo_olaria(corpo: dict[str, Any]) -> tuple[int, str, str]:
    candidatos: list[str] = []
    for campo in ("codigo", "estado"):
        val = corpo.get(campo)
        if isinstance(val, str) and val:
            candidatos.append(val)
    erros = corpo.get("erros")
    detalhe = str(corpo.get("erro") or "")
    if isinstance(erros, list) and erros:
        primeiro = erros[0]
        if isinstance(primeiro, dict):
            for campo in ("codigo", "tipo"):
                val = primeiro.get(campo)
                if isinstance(val, str) and val:
                    candidatos.append(val)
            detalhe = detalhe or str(primeiro.get("mensagem") or primeiro.get("erro") or "")
        else:
            detalhe = detalhe or str(primeiro)
    for cand in candidatos:
        if cand in _MAPA_CODIGOS_OLARIA:
            saida, cod = _MAPA_CODIGOS_OLARIA[cand]
            return saida, cod, detalhe or cand
    return 2, "chave-invalida", detalhe or "recusado pela Olaria"


def _traduzir_erro_http(
    resp: RespostaHTTP, execucao: ExecucaoMorada
) -> RecusaEscrita:
    ped = execucao.pedido
    classe = execucao.decisao.classe
    if resp.status == _HTTP_FORBIDDEN:
        return RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="acesso-negado",
                onde="olaria",
                recebido="403",
                regra="Olaria recusou as credenciais ou permissões da chamada",
                cura="verifique a credencial de serviço da unidade do escritor",
                proximo="",
            )
        )
    if resp.status == _HTTP_SERVICE_UNAVAILABLE:
        return RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="morada-sem-resposta",
                onde="olaria",
                recebido=str(resp.corpo.get("erro") or "503"),
                regra="Olaria indisponível; a fornada foi desfeita antes de gravar",
                cura="aguarde o serviço da Olaria voltar e repita a chamada",
                proximo="",
            )
        )
    if resp.status in (_HTTP_BAD_REQUEST, _HTTP_UNPROCESSABLE):
        saida, codigo, detalhe = _extrair_codigo_olaria(resp.corpo)
        return RecusaEscrita(
            ErroEscrita(
                saida=saida,
                codigo=codigo,
                onde="olaria",
                recebido=detalhe,
                regra="a Olaria recusou o conteúdo ou a pré-condição da ficha",
                cura=str(resp.corpo.get("cura") or "corrija os dados da ficha e repita"),
                proximo=str(resp.corpo.get("proximo") or ""),
            )
        )
    if ped.forma == "ensaiar":
        return RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="morada-sem-resposta",
                onde="olaria",
                recebido=f"HTTP {resp.status}",
                regra="ensaio não grava e falhou por erro interno da Olaria",
                cura="repita o ensaio quando a Olaria estabilizar",
                proximo="",
            )
        )
    return RecusaEscrita(
        ErroEscrita(
            saida=5,
            codigo="resposta-perdida",
            onde="olaria",
            recebido=f"HTTP {resp.status}",
            regra="erro após envio da gravação à Olaria torna o desfecho indeterminável",
            cura="repita a chamada com o mesmo --pedido para dedup seguro",
            proximo=proximo_repeticao_pedido(ped, classe),
        )
    )


def _resultado_de_repeticao(
    execucao: ExecucaoMorada, linha: LinhaOperacao
) -> ResultadoEscrita:
    return ResultadoEscrita(
        chave=execucao.alvo.alvo.chave,
        classe=execucao.decisao.classe,
        forma=execucao.pedido.forma,
        morada="banco",
        release=execucao.release,
        pedido=execucao.pedido.pedido,
        alterou=False,
        ja_gravado=True,
        substituiu=False,
        bytes=linha.bytes,
        versao=linha.versao_gravada,
        versao_completa=linha.versao_gravada,
        versao_anterior=linha.versao_lida,
        fornada=linha.fornada or linha.versao_gravada,
    )





def _resultado_de_sucesso_olaria(
    execucao: ExecucaoMorada, corpo: dict[str, Any]
) -> ResultadoEscrita:
    ped = execucao.pedido
    alvo = execucao.alvo.alvo
    tamanho = len((ped.conteudo or "").encode("utf-8"))
    if ped.forma == "ensaiar":
        mudaria = bool(corpo.get("mudaria", True))
        return ResultadoEscrita(
            chave=alvo.chave,
            classe=execucao.decisao.classe,
            forma="ensaiar",
            morada="banco",
            release=execucao.release,
            pedido=ped.pedido,
            alterou=False,
            ja_gravado=False,
            substituiu=False,
            bytes=tamanho,
            versao=None,
            versao_completa=None,
            versao_anterior=ped.versao,
            ensaiado=True,
            mudaria=mudaria,
            fornada=None,
        )
    estado = str(corpo.get("estado") or "")
    ja_gravado = estado == "ja-gravada" or bool(corpo.get("ja_gravada"))
    fornada = str(corpo.get("fornada") or ped.pedido)
    return ResultadoEscrita(
        chave=alvo.chave,
        classe=execucao.decisao.classe,
        forma=ped.forma,
        morada="banco",
        release=execucao.release,
        pedido=ped.pedido,
        alterou=not ja_gravado,
        ja_gravado=ja_gravado,
        substituiu=(ped.forma == "trocar" and not ja_gravado),
        bytes=tamanho,
        versao=fornada,
        versao_completa=fornada,
        versao_anterior=ped.versao,
        fornada=fornada,
    )


class MoradaOlaria:
    """Morada banco pela API HTTP da Olaria, com ponto de não volta no envio."""

    nome = "banco"
    ponto_de_nao_volta = "envio-gravacao-olaria"

    def __init__(
        self,
        config: ConfigOlaria,
        *,
        transporte: TransporteOlaria | None = None,
    ) -> None:
        self.config = config
        self._transporte = _chamar_http_olaria if transporte is None else transporte

    def _despachar(
        self,
        execucao: ExecucaoMorada,
        rota: str,
        cabecalhos: dict[str, str],
        corpo: dict[str, Any],
        prazo_s: float,
    ) -> RespostaHTTP:
        try:
            return self._transporte(self.config.url, rota, cabecalhos, corpo, prazo_s)
        except _ErroAntesEnvio as exc:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="olaria",
                    recebido=str(exc),
                    regra="falha de conexão antes do envio da gravação sai 3",
                    cura="verifique se o serviço da Olaria está no ar e repita",
                    proximo="",
                )
            ) from exc
        except _ErroAposEnvio as exc:
            if execucao.pedido.forma == "ensaiar":
                raise RecusaEscrita(
                    ErroEscrita(
                        saida=3,
                        codigo="morada-sem-resposta",
                        onde="olaria",
                        recebido=str(exc),
                        regra="ensaio interrompido não grava e sai 3",
                        cura="repita o ensaio",
                        proximo="",
                    )
                ) from exc
            raise RecusaEscrita(
                ErroEscrita(
                    saida=5,
                    codigo=exc.codigo,
                    onde="olaria",
                    recebido=str(exc),
                    regra="falha após o envio da gravação torna o desfecho indeterminável",
                    cura="repita a chamada com o mesmo --pedido para idempotência segura",
                    proximo=proximo_repeticao_pedido(
                        execucao.pedido, execucao.decisao.classe
                    ),
                )
            ) from exc

    def executar(self, execucao: ExecucaoMorada) -> ResultadoEscrita:
        """Executa criar, trocar ou ensaiar na Olaria com repetição segura por pedido."""
        ped = execucao.pedido
        if ped.forma != "ensaiar" and execucao.registro is not None:
            repetida = execucao.registro.consultar_repeticao(
                ped,
                classe=execucao.decisao.classe,
                retencao_s=execucao.politica.retencao_repeticao_s,
            )
            if repetida is not None:
                return _resultado_de_repeticao(execucao, repetida)

        prazo_s = _prazo_restante_s(execucao, self.config.timeout_padrao_s)
        rota, cabecalhos, corpo = _montar_requisicao_olaria(
            execucao, self.config.chave, prazo_s
        )
        resp = self._despachar(execucao, rota, cabecalhos, corpo, prazo_s)
        if resp.status != _HTTP_OK:
            raise _traduzir_erro_http(resp, execucao)

        resultado = _resultado_de_sucesso_olaria(execucao, resp.corpo)
        registrar_operacao_sucesso(execucao, resultado)
        return resultado
