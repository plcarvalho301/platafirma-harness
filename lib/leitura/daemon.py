"""Processo do leitor único sobre soquete UNIX com SO_PEERCRED, vagas e troca de release."""
from __future__ import annotations

import json
import os
import pwd
import socket
import struct
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .borda import VERSAO_CURSOR, assinar_cursor, calcular_query_hash, validar_cursor
from .morada import eh_segredo
from .moradas import ErroMorada, RegistroMoradas
from .moradas.balde import AdaptadorBalde
from .moradas.banco import AdaptadorBanco
from .moradas.cofre import AdaptadorCofre
from .moradas.fila import SUJEITO_ATUAL, AdaptadorFila
from .moradas.git import AdaptadorGit
from .moradas.rastreador import AdaptadorRastreador
from .moradas.wiki import AdaptadorWiki
from .nucleo import ErroNucleo, processar_objeto
from .resolvedor import (
    ErroResolucao,
    VistaAlcance,
    carregar_vista_alcance,
    resolver_alvo,
)
from .tipos import (
    AlvoResolvido,
    ContextoChamada,
    CursorDecodificado,
    FiltroCatalogo,
    Recusa,
    ResultadoLeitura,
    ResultadoListagem,
    SeletorParte,
)

SOCKET_PADRAO = Path("/run/platafirma/leitor/leitor.sock")
_CABECA_QUADRO = struct.Struct(">I")
_MAX_QUADRO_PEDIDO = 2 * 1024 * 1024
_MAX_QUADRO_RESPOSTA = 32 * 1024 * 1024
_BLOCO_SOCKET = 65_536
_VAGAS_PESADAS_PADRAO = 4
_ESPERA_VAGA_PADRAO_MS = 5_000
_PRIORIDADE_SAIDA: dict[int, int] = {5: 5, 3: 4, 4: 3, 2: 2, 1: 1, 0: 0}

AutorizadorLeitura = Callable[[str, str, str, str, str], bool]
LeitorRelease = Callable[[], str]
RegistradorTelemetria = Callable[[dict[str, Any]], None]
ExtratorPeerCred = Callable[[socket.socket], tuple[int, int, int]]


@dataclass(frozen=True, slots=True)
class CredencialChamador:
    """Identidade do processo chamador extraída do kernel via SO_PEERCRED."""

    pid: int
    uid: int
    gid: int
    conta: str


def combinar_codigos_saida(codigos: Sequence[int]) -> int:
    """Combina códigos de saída multi-chave sob precedência estrita 5 > 3 > 4 > 2 > 1 > 0."""
    if not codigos:
        return 0
    return max(codigos, key=lambda c: _PRIORIDADE_SAIDA.get(c, 0))


def extrair_peercred(sock: socket.socket) -> tuple[int, int, int]:
    """Lê (pid, uid, gid) do processo conectado via SO_PEERCRED."""
    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    pid, uid, gid = struct.unpack("3i", raw)
    return int(pid), int(uid), int(gid)


def _resolver_conta(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return f"uid:{uid}"


def ler_release_harness_padrao() -> str:
    """Lê o identificador da release ativa da harness no host."""
    env_rel = (os.environ.get("PF_RELEASE_HARNESS") or "").strip()
    if env_rel:
        return env_rel
    alvo = Path(os.environ.get("PLATAFIRMA_RELEASE_RAIZ", "/opt/platafirma")) / "current" / "harness"
    try:
        return os.path.realpath(alvo)
    except OSError:
        return "desconhecida"


def _ler_exato(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        bloco = sock.recv(min(n - len(buf), _BLOCO_SOCKET))
        if not bloco:
            raise EOFError("conexão encerrada antes do fim do quadro")
        buf.extend(bloco)
    return bytes(buf)


def receber_quadro_json(sock: socket.socket, *, max_bytes: int = _MAX_QUADRO_PEDIDO) -> dict[str, Any]:
    """Recebe um quadro JSON com prefixo de 4 bytes big-endian."""
    cabeca = _ler_exato(sock, 4)
    (tam,) = _CABECA_QUADRO.unpack(cabeca)
    if tam <= 0 or tam > max_bytes:
        raise ValueError(f"tamanho de quadro inválido: {tam}")
    corpo = _ler_exato(sock, tam)
    obj = json.loads(corpo.decode("utf-8"))
    if not isinstance(obj, dict):
        raise TypeError("quadro JSON deve ser objeto")
    return obj


def enviar_quadro_json(
    sock: socket.socket, dados: Mapping[str, Any], *, max_bytes: int = _MAX_QUADRO_RESPOSTA
) -> None:
    """Envia objeto JSON em quadro com prefixo de 4 bytes big-endian."""
    corpo = json.dumps(dict(dados), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(corpo) > max_bytes:
        raise ValueError(f"resposta excede teto de enquadramento ({len(corpo)} > {max_bytes})")
    sock.sendall(_CABECA_QUADRO.pack(len(corpo)) + corpo)


def _seletor_de_dict(bruto: Mapping[str, Any] | None) -> SeletorParte:
    d = dict(bruto or {})
    linhas_raw = d.get("linhas")
    paginas_raw = d.get("paginas")
    linhas = (int(linhas_raw[0]), None if linhas_raw[1] is None else int(linhas_raw[1])) if linhas_raw else None
    paginas = (int(paginas_raw[0]), None if paginas_raw[1] is None else int(paginas_raw[1])) if paginas_raw else None
    return SeletorParte(
        modo=d.get("modo", "texto"),
        linhas=linhas,
        cauda_linhas=d.get("cauda_linhas"),
        paginas=paginas,
        cauda_paginas=d.get("cauda_paginas"),
        offset=d.get("offset"),
        max_bytes=int(d.get("max_bytes", 40_000)),
        inteiro=bool(d.get("inteiro", False)),
        dpi=int(d.get("dpi", 150)),
        encoding=d.get("encoding"),
        versao_pedida=d.get("versao_pedida"),
        membro=d.get("membro"),
        com_decisoes_ancestrais=bool(d.get("com_decisoes_ancestrais", False)),
    )


def _contexto_de_dict(bruto: Mapping[str, Any]) -> ContextoChamada:
    return ContextoChamada(
        sujeito_jwt=None,
        sujeito=str(bruto.get("sujeito") or ""),
        sessao_id=bruto.get("sessao_id"),
        ordem_id=bruto.get("ordem_id"),
        verbo=str(bruto.get("verbo") or "busca"),
        origem_autenticada=str(bruto.get("origem_autenticada") or "cli"),
        origem_declarada=str(bruto.get("origem_declarada") or "cli"),
        prazo_ms=max(50, int(bruto.get("prazo_ms") or 30_000)),
    )


def _filtros_de_lista(brutos: Sequence[Mapping[str, Any]]) -> tuple[FiltroCatalogo, ...]:
    return tuple(
        FiltroCatalogo(
            tipo=f["tipo"],
            nome=str(f.get("nome") or ""),
            valor=None if f.get("valor") is None else str(f["valor"]),
        )
        for f in brutos
    )


def _resultado_ler_para_dict(res: ResultadoLeitura) -> dict[str, Any]:
    d = asdict(res)
    d["avisos"] = list(res.avisos)
    if res.imagens is not None:
        d["imagens"] = list(res.imagens)
    if res.bytes is not None:
        d["bytes"] = list(res.bytes)
    if res.linhas is not None:
        d["linhas"] = list(res.linhas)
    if res.paginas is not None:
        d["paginas"] = list(res.paginas)
    if res.sem_texto is not None:
        d["sem_texto"] = list(res.sem_texto)
    return d


def _resultado_listar_para_dict(res: ResultadoListagem) -> dict[str, Any]:
    d = asdict(res)
    d["itens"] = list(res.itens)
    d["avisos"] = list(res.avisos)
    return d


def _eh_leitura_pesada_padrao(alvo: AlvoResolvido, seletor: SeletorParte) -> bool:
    return (
        alvo.morada == "balde"
        or seletor.modo in ("pagina", "sumario")
        or seletor.inteiro
        or seletor.membro is not None
    )


def _resposta_erro(recusa: Recusa, *, release: str) -> dict[str, Any]:
    return {
        "ok": False,
        "exit_code": recusa.saida,
        "recusa": recusa.campos(),
        "release": release,
    }


def _registrar_telemetria_stderr(evento: dict[str, Any]) -> None:
    sys.stderr.write(json.dumps(evento, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stderr.flush()


class DaemonLeitor:
    """Servidor do leitor único em soquete UNIX com portão no estágio 5, vagas e troca de release."""

    def __init__(  # noqa: PLR0913 -- injeção explícita das dependências do daemon
        self,
        *,
        moradas: RegistroMoradas,
        vista: VistaAlcance | None = None,
        uids_autorizados: frozenset[int] | None = None,
        autorizador: AutorizadorLeitura | None = None,
        vagas_pesadas: int = _VAGAS_PESADAS_PADRAO,
        espera_vaga_ms: int = _ESPERA_VAGA_PADRAO_MS,
        ler_release: LeitorRelease | None = None,
        telemetria: RegistradorTelemetria | None = None,
        extrator_peercred: ExtratorPeerCred | None = None,
        segredo_cursor: bytes | None = None,
        eh_pesada: Callable[[AlvoResolvido, SeletorParte], bool] | None = None,
    ) -> None:
        self._moradas = moradas
        self._vista = vista if vista is not None else carregar_vista_alcance()
        self._uids_autorizados = uids_autorizados
        self._autorizador = autorizador
        self._semaforo = threading.BoundedSemaphore(max(1, vagas_pesadas))
        self._espera_vaga_ms = max(10, espera_vaga_ms)
        self._ler_release = ler_release or ler_release_harness_padrao
        self._release_inicial = self._ler_release()
        self._telemetria = telemetria or _registrar_telemetria_stderr
        self._peercred = extrator_peercred or extrair_peercred
        self._segredo_cursor = segredo_cursor
        self._eh_pesada = eh_pesada or _eh_leitura_pesada_padrao
        self._encerrar = threading.Event()
        self._release_mudou = False

    @property
    def release_inicial(self) -> str:
        return self._release_inicial

    @property
    def release_mudou(self) -> bool:
        return self._release_mudou

    def parar(self) -> None:
        self._encerrar.set()

    def _conferir_release(self) -> bool:
        atual = self._ler_release()
        if atual != self._release_inicial:
            self._release_mudou = True
            self._encerrar.set()
            return False
        return True

    def _autorizar_chamador(self, cred: CredencialChamador) -> Recusa | None:
        if self._uids_autorizados is not None and cred.uid not in self._uids_autorizados:
            return Recusa(
                saida=4,
                codigo="acesso-negado",
                onde="so_peercred",
                recebido=f"uid={cred.uid}",
                regra="chamador-autorizado-no-socket",
                cura="conta do processo chamador não está autorizada a conectar no leitor único",
                proximo="",
            )
        return None

    def _autorizar_chave(
        self, ctx: ContextoChamada, forma: str, classe: str, chave_canonica: str
    ) -> Recusa | None:
        if self._autorizador is None:
            return None
        if not self._autorizador(ctx.sujeito, ctx.verbo, forma, classe, chave_canonica):
            return Recusa(
                saida=4,
                codigo="acesso-negado",
                onde="estagio-5",
                recebido=chave_canonica,
                regra="portao-de-acesso-sujeito",
                cura="acesso negado para este sujeito sobre a chave solicitada",
                proximo="",
            )
        return None

    def _executar_chave_unica(
        self,
        ctx: ContextoChamada,
        chave: str,
        classe_explicita: str | None,
        seletor: SeletorParte,
        *,
        forcar_pesada: bool = False,
    ) -> tuple[int, dict[str, Any], str, str]:
        try:
            alvo, membro = resolver_alvo(
                ctx.verbo, chave, classe_explicita=classe_explicita, vista=self._vista
            )
        except ErroResolucao as exc:
            return exc.saida, {"chave": chave, "exit_code": exc.saida, "recusa": exc.recusa.campos()}, "", ""

        seletor_ef = SeletorParte(
            **{**asdict(seletor), "membro": membro if membro is not None else seletor.membro}
        )

        # Estágio 5: decide só pela chamada e pela chave ANTES de abrir a morada
        neg = self._autorizar_chave(ctx, "ler", alvo.classe, alvo.chave_canonica)
        if neg is not None:
            return 4, {"chave": chave, "exit_code": 4, "recusa": neg.campos()}, alvo.classe, alvo.morada

        if eh_segredo(Path(alvo.endereco)) or eh_segredo(Path(chave)):
            rec = Recusa(
                saida=4,
                codigo="segredo-fora-do-leitor",
                onde="estagio-5",
                recebido=chave,
                regra="vedacao-de-segredo",
                cura="superfície vedada no leitor geral",
                proximo="",
            )
            return 4, {"chave": chave, "exit_code": 4, "recusa": rec.campos()}, alvo.classe, alvo.morada

        pesada = forcar_pesada or self._eh_pesada(alvo, seletor_ef)
        adquiriu = False
        if pesada:
            espera_s = min(self._espera_vaga_ms, ctx.prazo_ms) / 1000.0
            adquiriu = self._semaforo.acquire(timeout=espera_s)
            if not adquiriu:
                rec = Recusa(
                    saida=3,
                    codigo="leitor-ocupado",
                    onde="leitor",
                    recebido=chave,
                    regra="limite-de-vagas-pesadas",
                    cura="leitor atingiu o limite de leituras pesadas simultâneas; repita a chamada",
                    proximo=f"{ctx.verbo} ler {chave}",
                )
                return 3, {"chave": chave, "exit_code": 3, "recusa": rec.campos()}, alvo.classe, alvo.morada

        try:
            bruto = self._moradas.ler_objeto(alvo, seletor_ef, ctx.prazo_ms)
            resultado = processar_objeto(bruto, seletor_ef)
            item = _resultado_ler_para_dict(resultado)
            item["exit_code"] = 0
            return 0, item, alvo.classe, alvo.morada
        except (ErroMorada, ErroNucleo) as exc:
            return (
                exc.saida,
                {"chave": chave, "exit_code": exc.saida, "recusa": exc.recusa.campos()},
                alvo.classe,
                alvo.morada,
            )
        finally:
            if adquiriu:
                self._semaforo.release()

    def _tratar_ler(
        self, ctx: ContextoChamada, pedido: Mapping[str, Any]
    ) -> tuple[dict[str, Any], str, str]:
        chaves_raw = pedido.get("chaves")
        if not isinstance(chaves_raw, list) or not chaves_raw:
            rec = Recusa(
                saida=2,
                codigo="chave-ausente",
                onde="chaves",
                recebido="",
                regra="chave-obrigatoria",
                cura="informe ao menos uma chave para ler",
                proximo="",
            )
            return _resposta_erro(rec, release=self._release_inicial), "", ""

        chaves = [str(c) for c in chaves_raw]
        classe_exp = pedido.get("classe")
        seletor = _seletor_de_dict(pedido.get("seletor"))
        forcar_pesada = bool(pedido.get("pesada", False))

        if len(chaves) == 1:
            saida, item, classe, morada = self._executar_chave_unica(
                ctx, chaves[0], classe_exp, seletor, forcar_pesada=forcar_pesada
            )
            if saida == 0:
                return {"ok": True, "exit_code": 0, "resultado": item, "release": self._release_inicial}, classe, morada
            return {"ok": False, "exit_code": saida, "recusa": item["recusa"], "release": self._release_inicial}, classe, morada

        # Multi-chave: deduplica (chave, membro) preservando a ordem pedida e precedência 5>3>4>2>1>0
        cache_exec: dict[tuple[str, str | None], tuple[int, dict[str, Any], str, str]] = {}
        itens: list[dict[str, Any]] = []
        saidas: list[int] = []
        classe_log, morada_log = "", ""
        for ch in chaves:
            par_chave = (ch, seletor.membro)
            if par_chave not in cache_exec:
                cache_exec[par_chave] = self._executar_chave_unica(
                    ctx, ch, classe_exp, seletor, forcar_pesada=forcar_pesada
                )
            saida, item, cl, mo = cache_exec[par_chave]
            itens.append(item)
            saidas.append(saida)
            if not classe_log and cl:
                classe_log, morada_log = cl, mo

        saida_final = combinar_codigos_saida(saidas)
        ok_n = sum(1 for s in saidas if s == 0)
        resp = {
            "ok": saida_final == 0,
            "exit_code": saida_final,
            "itens": itens,
            "resumo": {
                "total": len(itens),
                "ok": ok_n,
                "falhas": len(itens) - ok_n,
                "exit_code": saida_final,
            },
            "release": self._release_inicial,
        }
        return resp, classe_log, morada_log

    def _tratar_listar(
        self, ctx: ContextoChamada, pedido: Mapping[str, Any]
    ) -> tuple[dict[str, Any], str, str]:
        classe = str(pedido.get("classe") or "")
        info = self._vista.classes.get(classe)
        if info is None:
            rec = Recusa(
                saida=1,
                codigo="classe-fora-do-verbo",
                onde="classe",
                recebido=classe,
                regra="classe-registrada",
                cura=f"classe {classe!r} não encontrada na vista de alcance",
                proximo="",
            )
            return _resposta_erro(rec, release=self._release_inicial), classe, ""

        alcance = self._vista.alcance_verbo.get(ctx.verbo, frozenset())
        if "*" not in alcance and classe not in alcance:
            rec = Recusa(
                saida=1,
                codigo="classe-fora-do-verbo",
                onde="classe",
                recebido=classe,
                regra="verbo-alcanca-classe",
                cura=f"o verbo {ctx.verbo!r} não alcança a classe {classe!r}",
                proximo=f"{info.verbo_dono} listar {classe}",
            )
            return _resposta_erro(rec, release=self._release_inicial), classe, info.morada

        neg = self._autorizar_chave(ctx, "listar", classe, f"{classe}:*")
        if neg is not None:
            return _resposta_erro(neg, release=self._release_inicial), classe, info.morada

        filtros = _filtros_de_lista(pedido.get("filtros") or ())
        termo = pedido.get("termo")
        limite = max(1, min(500, int(pedido.get("limite") or 100)))
        qhash = calcular_query_hash(ctx.verbo, classe, filtros, termo)

        cursor_dec: CursorDecodificado | None = None
        cursor_raw = pedido.get("cursor")
        if cursor_raw:
            res_cur = validar_cursor(
                str(cursor_raw),
                sujeito=ctx.sujeito,
                verbo=ctx.verbo,
                classe=classe,
                query_hash=qhash,
                segredo=self._segredo_cursor,
            )
            if isinstance(res_cur, Recusa):
                return _resposta_erro(res_cur, release=self._release_inicial), classe, info.morada
            cursor_dec = res_cur

        try:
            pag = self._moradas.listar_chaves(
                info.morada, classe, filtros, termo, limite, cursor_dec, ctx.prazo_ms
            )
        except ErroMorada as exc:
            return _resposta_erro(exc.recusa, release=self._release_inicial), classe, info.morada

        prox_cursor: str | None = None
        if pag.proxima_tupla is not None:
            prox_cursor = assinar_cursor(
                CursorDecodificado(
                    versao_token=VERSAO_CURSOR,
                    sujeito=ctx.sujeito,
                    verbo=ctx.verbo,
                    classe=classe,
                    query_hash=qhash,
                    versao_retrato=pag.versao,
                    ultima_ordem=pag.proxima_tupla[0],
                    ultima_chave=pag.proxima_tupla[1],
                ),
                segredo=self._segredo_cursor,
            )

        n_itens = len(pag.itens)
        parte = f"1-{n_itens} de {pag.total}" if n_itens > 0 else "0 itens"
        res_lst = ResultadoListagem(
            cabecalho=f"{classe} · versão {pag.versao} · {parte}",
            classe=classe,
            versao=pag.versao,
            digest=pag.digest,
            universo_fechado=pag.universo_fechado,
            total=pag.total,
            itens=pag.itens,
            parcial=prox_cursor is not None,
            avisos=pag.avisos,
            mudou=pag.mudou,
            proximo=f"{ctx.verbo} listar {classe} --cursor {prox_cursor}" if prox_cursor else None,
            cursor=prox_cursor,
        )
        return (
            {
                "ok": True,
                "exit_code": 0,
                "resultado": _resultado_listar_para_dict(res_lst),
                "release": self._release_inicial,
            },
            classe,
            info.morada,
        )

    def processar_pedido(
        self, pedido: Mapping[str, Any], cred: CredencialChamador
    ) -> dict[str, Any]:
        """Processa um pedido completo com conferência de chamador, estágio 5 e telemetria."""
        t0 = time.monotonic()
        ctx = _contexto_de_dict(pedido.get("contexto") or {})
        forma = str(pedido.get("forma") or "ler")

        neg_cred = self._autorizar_chamador(cred)
        if neg_cred is not None:
            resp = _resposta_erro(neg_cred, release=self._release_inicial)
            self._emitir_telemetria(ctx, cred, forma, "", "", resp, t0)
            return resp

        tok = SUJEITO_ATUAL.set(ctx.sujeito)
        try:
            if forma == "ler":
                resp, classe, morada = self._tratar_ler(ctx, pedido)
            elif forma == "listar":
                resp, classe, morada = self._tratar_listar(ctx, pedido)
            else:
                rec = Recusa(
                    saida=2,
                    codigo="ato-nao-aceito",
                    onde="forma",
                    recebido=forma,
                    regra="forma-valida-do-leitor",
                    cura="use forma 'ler' ou 'listar'",
                    proximo="",
                )
                resp, classe, morada = _resposta_erro(rec, release=self._release_inicial), "", ""
        finally:
            SUJEITO_ATUAL.reset(tok)

        self._emitir_telemetria(ctx, cred, forma, classe, morada, resp, t0)
        return resp

    def _emitir_telemetria(  # noqa: PLR0913 -- campos obrigatórios da linha de telemetria (ler.md §9)
        self, ctx: ContextoChamada, cred: CredencialChamador, forma: str,
        classe: str, morada: str, resp: Mapping[str, Any], t0: float,
    ) -> None:
        dur_ms = int((time.monotonic() - t0) * 1000)
        serial = json.dumps(dict(resp), ensure_ascii=False).encode("utf-8")
        evento = {
            "dur_ms": dur_ms,
            "verbo": ctx.verbo,
            "forma": forma,
            "classe": classe,
            "morada": morada,
            "bytes_produzidos": len(serial),
            "bytes_servidos": len(serial),
            "exit_code": int(resp.get("exit_code", 0)),
            "sujeito": ctx.sujeito,
            "conta_chamadora": cred.conta,
            "release": self._release_inicial,
            "origem_autenticada": ctx.origem_autenticada,
            "origem_declarada": ctx.origem_declarada,
        }
        self._telemetria(evento)

    def atender_conexao(self, conn: socket.socket) -> None:
        """Atende uma única conexão no soquete UNIX."""
        try:
            if not self._conferir_release():
                return
            pid, uid, gid = self._peercred(conn)
            cred = CredencialChamador(pid=pid, uid=uid, gid=gid, conta=_resolver_conta(uid))
            conn.settimeout(5.0)
            pedido = receber_quadro_json(conn)
            resp = self.processar_pedido(pedido, cred)
            enviar_quadro_json(conn, resp)
        except (EOFError, OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def servir_socket(self, srv: socket.socket) -> None:
        """Loop de aceitação concorrente (uma thread por conexão) até `parar()` ou troca de release."""
        srv.settimeout(0.2)
        while not self._encerrar.is_set():
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            if not self._conferir_release():
                conn.close()
                break
            t = threading.Thread(target=self.atender_conexao, args=(conn,), daemon=True)
            t.start()

    def servir_caminho(self, caminho: Path | str = SOCKET_PADRAO, *, modo: int = 0o660) -> None:
        """Cria e serve o soquete UNIX no caminho indicado."""
        alvo = Path(caminho)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        try:
            alvo.unlink()
        except FileNotFoundError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            srv.bind(str(alvo))
            os.chmod(alvo, modo)
            srv.listen(64)
            self.servir_socket(srv)
        finally:
            srv.close()
            try:
                alvo.unlink()
            except OSError:
                pass


_RELEASE_CURRENT_PADRAO = Path("/opt/platafirma/current")
CREDENCIAL_CASA_DB = "casa-db"
PAPEL_LEITOR_BANCO = "pf_leitor_ro"


class CredencialAusente(LookupError):
    """A credencial que a unidade entrega por LoadCredential= não chegou ao processo."""


def ler_credencial(nome: str, env: Mapping[str, str] | None = None) -> str:
    """O valor da credencial `nome` em $CREDENTIALS_DIRECTORY, sem o fim de linha."""
    ambiente = os.environ if env is None else env
    pasta = ambiente.get("CREDENTIALS_DIRECTORY", "")
    if not pasta:
        raise CredencialAusente(f"{nome}: CREDENTIALS_DIRECTORY ausente (a unidade não entregou credencial)")
    try:
        valor = (Path(pasta) / nome).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise CredencialAusente(f"{nome}: {exc.strerror or exc}") from None
    if not valor:
        raise CredencialAusente(f"{nome}: credencial vazia")
    return valor


def dsn_casa_db(env: Mapping[str, str] | None = None) -> str:
    """DSN do banco casa no papel pf_leitor_ro, com a senha da credencial casa-db."""
    ambiente = os.environ if env is None else env
    senha = quote(ler_credencial(CREDENCIAL_CASA_DB, ambiente), safe="")
    host = ambiente.get("CASA_PG_HOST", "127.0.0.1")
    porta = ambiente.get("CASA_PG_PORT", "5439")
    base = ambiente.get("CASA_PG_DB", "casa")
    return f"postgresql://{PAPEL_LEITOR_BANCO}:{senha}@{host}:{porta}/{base}"


def montar_moradas_producao(
    env: Mapping[str, str] | None = None,
    *,
    avisar: RegistradorTelemetria | None = None,
) -> RegistroMoradas:
    """As moradas que esta instância alcança; a que fica de fora sai 3 morada-sem-resposta na chamada.

    Wiki, fila e rastreador atendem em localhost sem segredo, como para os outros verbos; só o
    banco pede a credencial. O balde da casa é MinIO, e o adaptador só abre pasta local: sem
    PF_BALDE_RAIZ ele fica de fora e o motivo vai ao log.
    """
    ambiente = os.environ if env is None else env
    registrar_aviso = avisar or _registrar_telemetria_stderr
    release = Path(ambiente.get("PF_RELEASE_CURRENT") or str(_RELEASE_CURRENT_PADRAO))
    registro = RegistroMoradas()
    registro.registrar("git", AdaptadorGit(release / "casa"))
    registro.registrar("wiki", AdaptadorWiki())
    registro.registrar("fila", AdaptadorFila())
    registro.registrar("rastreador", AdaptadorRastreador())
    registro.registrar("cofre", AdaptadorCofre())
    try:
        registro.registrar("banco", AdaptadorBanco(dsn=dsn_casa_db(ambiente)))
    except CredencialAusente as exc:
        registrar_aviso({"evento": "morada-fora", "morada": "banco", "motivo": str(exc)})
    raiz_balde = ambiente.get("PF_BALDE_RAIZ", "")
    if raiz_balde:
        extrator = ambiente.get("PF_EXTRATOR_SOCKET") or None
        registro.registrar("balde", AdaptadorBalde(raiz_local=Path(raiz_balde), socket_extrator=extrator))
    else:
        registrar_aviso({"evento": "morada-fora", "morada": "balde", "motivo": "PF_BALDE_RAIZ ausente"})
    return registro


_MIN_ARGS_SOCKET = 2


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada de `leitor.service` (systemd socket activation ou caminho direto)."""
    args = sys.argv[1:] if argv is None else argv
    caminho = Path(os.environ.get("PF_LEITOR_SOCKET") or str(SOCKET_PADRAO))
    if len(args) >= _MIN_ARGS_SOCKET and args[0] == "--socket":
        caminho = Path(args[1])
    leitor = DaemonLeitor(moradas=montar_moradas_producao())
    if os.environ.get("LISTEN_FDS") == "1":
        srv = socket.socket(fileno=3)
        try:
            leitor.servir_socket(srv)
        finally:
            srv.close()
        return 0
    leitor.servir_caminho(caminho)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
