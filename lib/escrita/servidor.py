"""Daemon do escritor único ativado por soquete AF_UNIX."""
from __future__ import annotations

import base64
import errno
import json
import os
import selectors
import signal
import socket
import struct
import sys
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io_atomico import varrer_temporarios_orfaos
from .moradas import ExecucaoMorada, MoradaEscrita
from .moradas.git import MoradaGit
from .moradas.olaria import ConfigOlaria, MoradaOlaria
from .pedido import desligar_core_dump, parsear_pedido
from .politica import PoliticaEscrita, carregar_politica
from .portao import (
    AutorizadorSujeito,
    ContextoAutorizacao,
    CredencialPar,
    ProvedorRaio,
    VistaAlcance,
    carregar_vista_alcance,
    credencial_de_uid,
    criar_provedor_raio,
    decidir_portao,
)
from .registro import RegistroOperacoes
from .resolucao import resolver_alvo
from .tipos import (
    ContextoEscrita,
    ErroEscrita,
    PedidoEscrita,
    RecusaEscrita,
    ResultadoEscrita,
)

_HEADER_QUADRO = struct.Struct("!I")
_SD_LISTEN_FDS_START = 3
_MARGEM_QUADRO_BYTES = 512 * 1024
_TIMEOUT_LEITURA_QUADRO_S = 5.0
_MAX_CONEXOES_PADRAO = 32
_POLL_INTERVALO_PADRAO_S = 0.2
_VERSAO_PROTOCOLO = 1


def ler_exato(sock: socket.socket, tamanho: int) -> bytes:
    """Lê exatamente `tamanho` bytes do soquete ou levanta EOFError."""
    partes: list[bytes] = []
    restante = tamanho
    while restante > 0:
        bloco = sock.recv(restante)
        if not bloco:
            raise EOFError("conexão encerrada antes do fim do quadro")
        partes.append(bloco)
        restante -= len(bloco)
    return b"".join(partes)


def ler_quadro(sock: socket.socket, *, teto_bytes: int) -> dict[str, Any]:
    """Lê um quadro JSON prefixado por comprimento de 4 bytes big-endian."""
    cab = ler_exato(sock, _HEADER_QUADRO.size)
    (tamanho,) = _HEADER_QUADRO.unpack(cab)
    if tamanho == 0 or tamanho > teto_bytes:
        raise ValueError(f"tamanho de quadro fora do teto: {tamanho} > {teto_bytes}")
    corpo = ler_exato(sock, tamanho)
    dados = json.loads(corpo.decode("utf-8", errors="strict"))
    if not isinstance(dados, dict):
        raise TypeError("quadro JSON deve ser um objeto")
    return dados


def escrever_quadro(sock: socket.socket, obj: Mapping[str, Any]) -> None:
    """Serializa e envia um quadro JSON prefixado por comprimento de 4 bytes."""
    bruto = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sock.sendall(_HEADER_QUADRO.pack(len(bruto)) + bruto)


def extrair_credencial_par(conn: socket.socket) -> CredencialPar:
    """Extrai (uid, gid, pid) do processo chamador via SO_PEERCRED."""
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    pid, uid, gid = struct.unpack("3i", raw)
    return credencial_de_uid(uid, gid, pid)


def _carregar_decisor_core(pdp_dir: Path, core_dir: Path) -> Any:
    if str(core_dir) not in sys.path:
        sys.path.insert(0, str(core_dir))
    from porta.decisao import DecisorAcesso

    return DecisorAcesso(pdp_dir)


def criar_autorizador_pdp(
    pdp_dir: Path | None = None,
    *,
    core_dir: Path | None = None,
) -> AutorizadorSujeito | None:
    """Liga o portão ao DecisorAcesso da casa quando o diretório do PDP existe."""
    alvo_pdp = pdp_dir
    if alvo_pdp is None:
        env = (os.environ.get("PF_PDP_DIR") or "").strip()
        if env:
            alvo_pdp = Path(env)
        else:
            cand = Path("/opt/platafirma/current/core/acesso")
            if cand.is_dir():
                alvo_pdp = cand
    if alvo_pdp is None or not (alvo_pdp / "politica.yaml").is_file():
        return None
    raiz_core = core_dir or alvo_pdp.parent
    decisor = _carregar_decisor_core(alvo_pdp, raiz_core)

    def _autorizar(sujeito: str, cadeira: str, verbo: str, forma: str) -> bool:
        ident = {"sujeito": sujeito, "cadeira": cadeira}
        recusa = decisor.autorizar(
            verbo,
            "run_command",
            "comando",
            f"{verbo} {forma}".strip(),
            "plataforma-runtime",
            ident,
        )
        return recusa is None

    return _autorizar


def ler_release_corrente(release_link: Path | None) -> str:
    """Lê o identificador da release apontada por `release_link`."""
    if release_link is None or not release_link.exists():
        return "local"
    alvo = os.path.realpath(str(release_link))
    return Path(alvo).name or "local"


def _listar_bancadas(raiz_bancadas: Path) -> list[Path]:
    raiz_wt = raiz_bancadas / "wt"
    if not raiz_wt.is_dir():
        return []
    achadas: list[Path] = []
    for repo_dir in raiz_wt.iterdir():
        if not repo_dir.is_dir() or repo_dir.is_symlink():
            continue
        for cad_dir in repo_dir.iterdir():
            if not cad_dir.is_dir() or cad_dir.is_symlink():
                continue
            for wt_dir in cad_dir.iterdir():
                if wt_dir.is_dir() and not wt_dir.is_symlink():
                    achadas.append(wt_dir)
    return achadas


def _socket_systemd() -> socket.socket | None:
    pid_txt = (os.environ.get("LISTEN_PID") or "").strip()
    fds_txt = (os.environ.get("LISTEN_FDS") or "").strip()
    if not (pid_txt.isdigit() and fds_txt.isdigit()):
        return None
    if int(pid_txt) != os.getpid() or int(fds_txt) < 1:
        return None
    return socket.fromfd(_SD_LISTEN_FDS_START, socket.AF_UNIX, socket.SOCK_STREAM)


@dataclass
class ConfigServidor:
    """Configuração de execução do daemon do escritor único."""

    socket_path: Path
    raiz_bancadas: Path
    estado_dir: Path
    politica: PoliticaEscrita
    vista: VistaAlcance | None = None
    moradas: dict[str, MoradaEscrita] = field(default_factory=dict)
    release_link: Path | None = None
    grupo_autorizado: str = "platafirma-escrita"
    uid_escritor: int | None = None
    raio_card: frozenset[tuple[str, str]] | None = None
    provedor_raio: ProvedorRaio | None = None
    autorizador_sujeito: AutorizadorSujeito | None = None
    pdp_dir: Path | None = None
    olaria: ConfigOlaria | None = None
    max_conexoes: int = _MAX_CONEXOES_PADRAO
    poll_intervalo_s: float = _POLL_INTERVALO_PADRAO_S
    varrer_orfaos_na_largada: bool = True
    idade_orfao_s: float | None = None


def _decodificar_stdin_b64(valor: Any) -> bytes | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="encoding-invalido",
                onde="stdin_b64",
                recebido=type(valor).__name__,
                regra="stdin_b64 deve ser string base64 ou nulo",
                cura="envie entrada válida pela camada comum",
                proximo="",
            )
        )
    try:
        return base64.b64decode(valor.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="encoding-invalido",
                onde="stdin_b64",
                recebido=str(exc),
                regra="stdin_b64 deve ser base64 válido",
                cura="reenvie pela camada comum",
                proximo="",
            )
        ) from exc


def _montar_contexto(quadro: Mapping[str, Any], prazo_ns: int) -> ContextoEscrita:
    ctx_raw = quadro.get("contexto")
    ctx = ctx_raw if isinstance(ctx_raw, Mapping) else {}
    return ContextoEscrita(
        verbo=str(quadro.get("verbo") or ""),
        cadeira=str(ctx.get("cadeira") or ""),
        sujeito=str(ctx.get("sujeito") or ""),
        sessao_id=str(ctx.get("sessao_id") or ""),
        ordem_id=str(ctx.get("ordem_id") or ""),
        card=str(ctx.get("card") or ""),
        prazo_ns=prazo_ns,
        token=str(ctx.get("token") or ""),
        classe_unica=ctx.get("classe_unica") if isinstance(ctx.get("classe_unica"), str) else None,
        exige_objeto_casa=bool(ctx.get("exige_objeto_casa", False)),
    )


def _calcular_prazo_ns(quadro: Mapping[str, Any], prazo_max_s: int) -> int:
    bruto = quadro.get("prazo_restante_s")
    if isinstance(bruto, (int, float)) and not isinstance(bruto, bool) and bruto > 0:
        efetivo = min(float(bruto), float(prazo_max_s))
    else:
        efetivo = float(prazo_max_s)
    return time.monotonic_ns() + int(efetivo * 1_000_000_000)


def _resposta_recusa(recusa: RecusaEscrita) -> dict[str, Any]:
    return {"ok": False, "exit_code": recusa.saida, "payload": recusa.como_payload()}


def _resposta_erro_interno(codigo: str, detalhe: str, saida: int = 3) -> dict[str, Any]:
    rec = RecusaEscrita(
        ErroEscrita(
            saida=saida,
            codigo=codigo,
            onde="escritor",
            recebido=detalhe,
            regra="falha interna ao processar chamada no escritor único",
            cura="repita a chamada ou consulte os logs do serviço escritor",
            proximo="",
        )
    )
    return _resposta_recusa(rec)


class ServidorEscritor:
    """Processo do escritor único com soquete AF_UNIX, drenagem e vigilância de release."""

    def __init__(self, config: ConfigServidor) -> None:
        self.config = config
        self.politica = config.politica
        self.vista = config.vista or carregar_vista_alcance()
        self.registro = RegistroOperacoes(config.estado_dir / "operacoes.jsonl")
        self.release_inicial = ler_release_corrente(config.release_link)
        self._autorizador = (
            config.autorizador_sujeito
            if config.autorizador_sujeito is not None
            else criar_autorizador_pdp(config.pdp_dir)
        )
        self._moradas: dict[str, MoradaEscrita] = self._construir_moradas(config)
        self._parar = threading.Event()
        self._lock = threading.Lock()
        self._em_voo: set[threading.Thread] = set()
        self._semaforo = threading.BoundedSemaphore(max(1, config.max_conexoes))
        self._sock: socket.socket | None = None
        self._dono_do_socket = False
        self.orfaos_removidos: list[str] = []
        self.motivo_saida: str = ""

    def _construir_moradas(self, config: ConfigServidor) -> dict[str, MoradaEscrita]:
        moradas: dict[str, MoradaEscrita] = {
            "git": MoradaGit(
                raiz_bancadas=config.raiz_bancadas,
                estado_dir=config.estado_dir,
            )
        }
        if config.olaria is not None:
            moradas["banco"] = MoradaOlaria(config.olaria)
        moradas.update(config.moradas)
        return moradas

    def _contexto_auth(self) -> ContextoAutorizacao:
        return ContextoAutorizacao(
            politica=self.politica,
            vista=self.vista,
            grupo_autorizado=self.config.grupo_autorizado,
            uid_escritor=self.config.uid_escritor,
            raio_card=self.config.raio_card,
            provedor_raio=self.config.provedor_raio,
            autorizador_sujeito=self._autorizador,
        )

    def varrer_orfaos(self) -> list[str]:
        """Remove temporários `.pf-esc-*.tmp` antigos sob trava de cada bancada."""
        idade = (
            float(self.politica.prazo_max_s)
            if self.config.idade_orfao_s is None
            else self.config.idade_orfao_s
        )
        removidos: list[str] = []
        for wt in _listar_bancadas(self.config.raiz_bancadas):
            try:
                itens = varrer_temporarios_orfaos(wt, self.config.estado_dir, idade)
                removidos.extend(f"{wt.name}/{x}" for x in itens)
            except (OSError, RecusaEscrita):
                continue
        self.orfaos_removidos = removidos
        return removidos

    def _abrir_soquete(self) -> socket.socket:
        herdado = _socket_systemd()
        if herdado is not None:
            self._dono_do_socket = False
            herdado.setblocking(False)
            return herdado
        caminho = self.config.socket_path
        caminho.parent.mkdir(parents=True, exist_ok=True)
        try:
            caminho.unlink()
        except FileNotFoundError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(caminho))
        srv.listen(self.config.max_conexoes)
        srv.setblocking(False)
        self._dono_do_socket = True
        return srv

    def _verificar_par_antes_borda(self, cred: CredencialPar) -> None:
        auth = self._contexto_auth()
        if auth.uid_escritor is not None and cred.uid == auth.uid_escritor:
            return
        if auth.grupo_autorizado in cred.grupos:
            return
        raise RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="acesso-negado",
                onde="soquete",
                recebido=cred.usuario or f"uid:{cred.uid}",
                regra=f"somente contas no grupo {auth.grupo_autorizado} podem chamar o escritor",
                cura="adicione a conta ao grupo autorizado ou use a porta da casa",
                proximo="",
            )
        )

    def _executar_escrita(
        self, quadro: Mapping[str, Any], cred: CredencialPar
    ) -> ResultadoEscrita:
        self._verificar_par_antes_borda(cred)
        prazo_ns = _calcular_prazo_ns(quadro, self.politica.prazo_max_s)
        verbo = str(quadro.get("verbo") or "").strip()
        argv_raw = quadro.get("argv")
        argv = [str(x) for x in argv_raw] if isinstance(argv_raw, list) else []
        stdin_bytes = _decodificar_stdin_b64(quadro.get("stdin_b64"))
        ctx = _montar_contexto(quadro, prazo_ns)
        pedido: PedidoEscrita = parsear_pedido(
            verbo,
            argv,
            stdin_bytes,
            politica=self.politica,
            contexto=ctx,
        )
        decisao = decidir_portao(pedido, cred, self._contexto_auth())
        alvo = resolver_alvo(
            pedido,
            decisao,
            self.vista,
            raiz_bancadas=self.config.raiz_bancadas,
        )
        morada = self._moradas.get(decisao.morada)
        if morada is None:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="forma-sem-morada",
                    onde="morada",
                    recebido=decisao.morada,
                    regra=f"morada {decisao.morada} não está ativa neste escritor",
                    cura="use uma morada suportada nesta entrega",
                    proximo="",
                )
            )
        execucao = ExecucaoMorada(
            pedido=pedido,
            decisao=decisao,
            alvo=alvo,
            politica=self.politica,
            release=self.release_inicial,
            prazo_ns=prazo_ns,
            registro=self.registro,
        )
        return morada.executar(execucao)

    def processar_quadro(
        self, quadro: Mapping[str, Any], cred: CredencialPar
    ) -> dict[str, Any]:
        """Despacha um quadro `saude` ou `escrever` já decodificado."""
        tipo = str(quadro.get("tipo") or "")
        if tipo == "saude":
            with self._lock:
                em_voo = len(self._em_voo)
            return {
                "ok": True,
                "exit_code": 0,
                "tipo": "saude",
                "versao": _VERSAO_PROTOCOLO,
                "release": self.release_inicial,
                "pid": os.getpid(),
                "em_voo": em_voo,
            }
        if tipo != "escrever":
            return _resposta_recusa(
                RecusaEscrita(
                    ErroEscrita(
                        saida=2,
                        codigo="ato-nao-aceito",
                        onde="tipo",
                        recebido=tipo,
                        regra="quadro do soquete deve ter tipo 'saude' ou 'escrever'",
                        cura="envie um quadro válido pela camada comum",
                        proximo="",
                    )
                )
            )
        try:
            resultado = self._executar_escrita(quadro, cred)
            return {"ok": True, "exit_code": 0, "resultado": resultado.como_dict()}
        except RecusaEscrita as exc:
            return _resposta_recusa(exc)
        except OSError as exc:
            codigo = "sem-espaco" if exc.errno == errno.ENOSPC else "falha-disco"
            saida = 3 if exc.errno == errno.ENOSPC else 5
            return _resposta_erro_interno(codigo, str(exc), saida=saida)
        except Exception as exc:  # noqa: BLE001
            return _resposta_erro_interno("escritor-indisponivel", str(exc), saida=3)

    def _atender_conexao(self, conn: socket.socket) -> None:
        teto = self.politica.entrada_max_bytes * 2 + _MARGEM_QUADRO_BYTES
        try:
            conn.settimeout(_TIMEOUT_LEITURA_QUADRO_S)
            cred = extrair_credencial_par(conn)
            quadro = ler_quadro(conn, teto_bytes=teto)
            resp = self.processar_quadro(quadro, cred)
            escrever_quadro(conn, resp)
        except (OSError, ValueError, TypeError, EOFError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass
            with self._lock:
                self._em_voo.discard(threading.current_thread())
            self._semaforo.release()

    def _despachar_conexao(self, conn: socket.socket) -> None:
        if not self._semaforo.acquire(blocking=False):
            try:
                escrever_quadro(
                    conn,
                    _resposta_erro_interno("bancada-ocupada", "teto de conexões atingido", saida=3),
                )
            except OSError:
                pass
            finally:
                conn.close()
            return
        t = threading.Thread(target=self._atender_conexao, args=(conn,), daemon=False)
        with self._lock:
            self._em_voo.add(t)
        t.start()

    def _release_mudou(self) -> bool:
        if self.config.release_link is None:
            return False
        return ler_release_corrente(self.config.release_link) != self.release_inicial

    def parar(self, motivo: str = "sinal") -> None:
        """Sinaliza parada graciosa (para de aceitar e drena chamadas em voo)."""
        if not self.motivo_saida:
            self.motivo_saida = motivo
        self._parar.set()

    def _drenar_em_voo(self) -> None:
        prazo_dreno = float(self.politica.prazo_max_s) + 5.0
        limite = time.monotonic() + prazo_dreno
        while True:
            with self._lock:
                ativas = list(self._em_voo)
            if not ativas:
                return
            restante = max(0.05, limite - time.monotonic())
            for t in ativas:
                t.join(timeout=min(0.2, restante))
            if time.monotonic() >= limite:
                return

    def _fechar_soquete(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._dono_do_socket:
            try:
                self.config.socket_path.unlink()
            except OSError:
                pass

    def iniciar(self) -> None:
        """Prepara o daemon (core dump desligado, varredura de órfãos e soquete)."""
        desligar_core_dump()
        self.config.estado_dir.mkdir(parents=True, exist_ok=True)
        if self.config.varrer_orfaos_na_largada:
            self.varrer_orfaos()
        self._sock = self._abrir_soquete()

    def servir(self, *, instalar_sinais: bool = False) -> int:
        """Executa o laço principal até parada graciosa ou troca de release."""
        if self._sock is None:
            self.iniciar()
        sock = self._sock
        if sock is None:
            raise RuntimeError("soquete do escritor não inicializado")
        if instalar_sinais and threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, lambda *_: self.parar("SIGTERM"))
            signal.signal(signal.SIGINT, lambda *_: self.parar("SIGINT"))

        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)
        try:
            while not self._parar.is_set():
                if self._release_mudou():
                    self.parar("release-trocada")
                    break
                eventos = sel.select(timeout=self.config.poll_intervalo_s)
                if self._parar.is_set():
                    break
                for _key, _mask in eventos:
                    try:
                        conn, _ = sock.accept()
                    except BlockingIOError:
                        continue
                    self._despachar_conexao(conn)
        finally:
            sel.close()
            self._fechar_soquete()
            self._drenar_em_voo()
        return 0


def carregar_chave_credencial(nome: str = "olaria-chave") -> str:
    """Lê credencial de serviço via CREDENTIALS_DIRECTORY do systemd."""
    cred_dir = (os.environ.get("CREDENTIALS_DIRECTORY") or "").strip()
    if not cred_dir:
        return ""
    alvo = Path(cred_dir) / nome
    if not alvo.is_file():
        return ""
    return alvo.read_text(encoding="utf-8").strip()


def montar_config_padrao(
    *,
    socket_path: Path | None = None,
    raiz_bancadas: Path | None = None,
    estado_dir: Path | None = None,
    release_link: Path | None = None,
    pdp_dir: Path | None = None,
) -> ConfigServidor:
    """Monta a configuração de produção do daemon a partir de variáveis e defaults."""
    politica = carregar_politica()
    sock = socket_path or Path(
        os.environ.get("PF_ESCRITOR_SOCKET") or "/run/platafirma/escritor.sock"
    )
    wt = raiz_bancadas or Path(
        os.environ.get("PF_BANCADAS_RAIZ") or "/home/claudinho/AI"
    )
    est = estado_dir or Path(
        os.environ.get("PF_ESCRITOR_ESTADO") or "/var/lib/platafirma-escritor"
    )
    rel = release_link
    if rel is None:
        env_rel = (os.environ.get("PF_RELEASE_CURRENT") or "/opt/platafirma/current").strip()
        rel = Path(env_rel) if env_rel else None
    olaria_url = (os.environ.get("PF_OLARIA_URL") or "").strip()
    olaria_chave = carregar_chave_credencial()
    cfg_olaria = (
        ConfigOlaria(url=olaria_url, chave=olaria_chave)
        if olaria_url and olaria_chave
        else None
    )
    return ConfigServidor(
        socket_path=sock,
        raiz_bancadas=wt,
        estado_dir=est,
        politica=politica,
        release_link=rel,
        uid_escritor=os.geteuid(),
        provedor_raio=criar_provedor_raio(),
        pdp_dir=pdp_dir,
        olaria=cfg_olaria,
    )


__all__ = [
    "ConfigServidor",
    "ServidorEscritor",
    "carregar_chave_credencial",
    "criar_autorizador_pdp",
    "escrever_quadro",
    "extrair_credencial_par",
    "ler_exato",
    "ler_quadro",
    "ler_release_corrente",
    "montar_config_padrao",
]
