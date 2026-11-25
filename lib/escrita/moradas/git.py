"""Adaptador da morada git: gravação atômica na bancada com versão por blob SHA-1."""
from __future__ import annotations

import time
from pathlib import Path

from ..caminho import BancadaConfinada, resolver_bancada
from ..edicao import ResultadoEdicao, aplicar_patch, aplicar_trecho
from ..io_atomico import DestinoIO, ResultadoIO, blob_sha1, executar_escrita_atomica
from ..pedido import decodificar_utf8_estrito
from ..politica import eh_diretorio_executavel, exige_shebang
from ..resolucao import EstadoAlvo, validar_precondicao_versao
from ..tipos import ErroEscrita, PedidoEscrita, RecusaEscrita, ResultadoEscrita
from . import ExecucaoMorada, proximo_repeticao_pedido, registrar_operacao_sucesso

_SAIDA_INDETERMINAVEL = 5


def _anexar_proximo_saida_5(
    recusa: RecusaEscrita, pedido: PedidoEscrita, classe: str
) -> RecusaEscrita:
    if recusa.saida != _SAIDA_INDETERMINAVEL:
        return recusa
    proximo = proximo_repeticao_pedido(pedido, classe)
    atualizados = tuple(
        ErroEscrita(
            saida=e.saida,
            codigo=e.codigo,
            onde=e.onde,
            recebido=e.recebido,
            regra=e.regra,
            cura=e.cura,
            proximo=e.proximo or proximo,
        )
        for e in recusa.erros
    )
    return RecusaEscrita(atualizados)


def _aplicar_edicao_git(
    pedido: PedidoEscrita, texto_atual: str
) -> tuple[str, int | None, int | None]:
    if pedido.formato == "trecho":
        if pedido.trecho is None:
            raise ValueError("pedido com formato trecho sem objeto TrocaTrecho")
        ed: ResultadoEdicao = aplicar_trecho(texto_atual, pedido.trecho)
        return ed.texto, ed.ocorrencias, None
    if pedido.formato == "patch":
        if pedido.patch is None:
            raise ValueError("pedido com formato patch sem objeto PatchEstrito")
        ed = aplicar_patch(texto_atual, pedido.chave, pedido.patch)
        return ed.texto, None, ed.hunks_aplicados
    return pedido.conteudo or "", None, None


def _validar_limites_e_shebang(
    texto_novo: str,
    execucao: ExecucaoMorada,
    bancada: BancadaConfinada,
) -> tuple[bytes, bool]:
    novos_bytes = texto_novo.encode("utf-8")
    teto = execucao.politica.entrada_max_bytes
    if len(novos_bytes) > teto:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="tamanho-excedido",
                onde="conteudo",
                recebido=f"{len(novos_bytes)} bytes",
                regra=f"resultado da escrita excede o teto de {teto} bytes",
                cura="reduza o conteúdo abaixo do teto configurado",
                proximo="",
            )
        )
    if exige_shebang(
        execucao.politica, bancada.repo, bancada.caminho_relativo
    ) and not texto_novo.startswith("#!"):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="sem-shebang",
                onde="conteudo",
                recebido=texto_novo.splitlines()[0] if texto_novo else "",
                regra="arquivo em diretório de executáveis exige linha de interpretador #!",
                cura="adicione #!/usr/bin/env ... na primeira linha",
                proximo="",
            )
        )
    eh_exec = eh_diretorio_executavel(
        execucao.politica, bancada.repo, bancada.caminho_relativo
    )
    return novos_bytes, eh_exec


def _construir_resultado_git(
    execucao: ExecucaoMorada,
    res_io: ResultadoIO,
    ocorrencias: int | None,
    hunks_aplicados: int | None,
) -> ResultadoEscrita:
    ver_curta = res_io.versao_nova[:12]
    ver_ant = res_io.versao_anterior[:12] if res_io.versao_anterior else None
    desfazer = (
        f"{execucao.pedido.verbo} gravar {execucao.decisao.classe} "
        f"{execucao.pedido.chave} {ver_curta}"
    )
    return ResultadoEscrita(
        chave=execucao.pedido.chave,
        classe=execucao.decisao.classe,
        forma=execucao.pedido.forma,
        morada="git",
        release=execucao.release,
        pedido=execucao.pedido.pedido,
        alterou=res_io.alterou,
        ja_gravado=res_io.ja_gravado,
        substituiu=res_io.substituiu,
        bytes=res_io.bytes_gravados,
        versao=ver_curta,
        versao_completa=res_io.versao_nova,
        versao_anterior=ver_ant,
        ocorrencias=ocorrencias,
        hunks_aplicados=hunks_aplicados,
        desfazer=desfazer,
    )


class MoradaGit:
    """Morada git sobre bancada worktree com ponto de não volta em `os.replace`."""

    nome = "git"
    ponto_de_nao_volta = "os.replace"

    def __init__(self, *, raiz_bancadas: Path, estado_dir: Path) -> None:
        self.raiz_bancadas = Path(raiz_bancadas)
        self.estado_dir = Path(estado_dir)

    def executar(self, execucao: ExecucaoMorada) -> ResultadoEscrita:
        """Executa gravação atômica na bancada com versão por blob SHA-1."""
        if execucao.prazo_ns > 0 and time.monotonic_ns() >= execucao.prazo_ns:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="prazo",
                    recebido="prazo esgotado antes da gravação",
                    regra="operação expirada antes do ponto de não volta sai 3",
                    cura="repita a chamada com prazo suficiente",
                    proximo="",
                )
            )
        bancada = execucao.alvo.bancada or resolver_bancada(
            execucao.pedido.chave, execucao.decisao.cadeira, self.raiz_bancadas
        )
        destino = DestinoIO(
            raiz_wt=bancada.raiz_wt,
            componentes_bancada=bancada.componentes_bancada,
            componentes_alvo=bancada.componentes_alvo,
            estado_dir=self.estado_dir,
            prazo_ns=execucao.prazo_ns,
            passo_ms=execucao.politica.espera_trava_passo_ms,
            teto_leitura_bytes=execucao.politica.entrada_max_bytes,
        )
        metricas: dict[str, int | None] = {"ocorrencias": None, "hunks": None}

        def _transformar(dados_atuais: bytes | None) -> tuple[bytes, bool]:
            pedido = execucao.pedido
            if (
                pedido.formato == "inteiro"
                and dados_atuais is not None
                and blob_sha1((pedido.conteudo or "").encode("utf-8"))
                == blob_sha1(dados_atuais)
            ):
                return _validar_limites_e_shebang(
                    pedido.conteudo or "", execucao, bancada
                )
            texto_atual = (
                decodificar_utf8_estrito(dados_atuais, onde=bancada.caminho_relativo)
                if dados_atuais is not None
                else ""
            )
            sha_atual = blob_sha1(dados_atuais) if dados_atuais is not None else None
            estado = EstadoAlvo(
                existe=dados_atuais is not None,
                versao=sha_atual[:12] if sha_atual else None,
                versao_completa=sha_atual,
            )
            validar_precondicao_versao(pedido, execucao.alvo.alvo, estado)
            texto_novo, ocorrencias, hunks = _aplicar_edicao_git(pedido, texto_atual)
            metricas["ocorrencias"] = ocorrencias
            metricas["hunks"] = hunks
            return _validar_limites_e_shebang(texto_novo, execucao, bancada)

        try:
            res_io = executar_escrita_atomica(destino, _transformar)
        except RecusaEscrita as exc:
            raise _anexar_proximo_saida_5(
                exc, execucao.pedido, execucao.decisao.classe
            ) from exc

        resultado = _construir_resultado_git(
            execucao, res_io, metricas["ocorrencias"], metricas["hunks"]
        )
        registrar_operacao_sucesso(
            execucao,
            resultado,
            repo=bancada.repo,
            caminho_relativo=bancada.caminho_relativo,
        )
        return resultado
