"""MCP de operação — run_command genérico + arquivo, sob um usuário do host.

Roda FORA do compose (systemd user service) de propósito: é a mão que sobe o compose
de volta — não pode morar dentro do raio de explosão. A fronteira dura é o usuário do
processo (rootless docker, sem alcance a /home de terceiro); a raiz declarada de arquivo
é ergonomia, não fronteira — decisão do épico (run_command genérico).

Auth: token OIDC do realm `platafirma`, validado por assinatura (JWKS) na borda —
`Authorization: Bearer <jwt>`. O servidor publica protected resource metadata (RFC 9728)
e responde 401 com `WWW-Authenticate`, que é o que faz o cliente MCP descobrir o
authorization server sozinho e rodar authorization_code + PKCE.
ROTA DE EMERGÊNCIA: OPS_AUTH_TOKEN estático continua aceito até OPS_TOKEN_ESTATICO_ATE
(prazo declarado, não indefinido) — é a mão que volta quando o realm cai, já que o dono
não tem shell no host. Vencido o prazo, só JWT entra. Query string `?token=` só vale por
essa rota; prefira sempre o header.

MULTI-INSTÂNCIA: o mesmo arquivo serve mais de uma instância, uma por usuário do host.
OPS_NAME, OPS_USER, OPS_ROOT e OPS_AUTH_TOKEN separam as instâncias; o default é a
instância histórica (platafirma-ops sob claudinho). OPS_USER e OPS_ROOT entram nas
descrições das tools em tempo de registro — sem isso a instância nova se descreve com
o usuário e a raiz da instância velha, e o cliente age sobre um caminho que não existe.

AUDITORIA: toda invocação de tool grava uma linha JSONL em OPS_ROOT/var/log/ops/, com
retenção declarada (OPS_LOG_RETENCAO_DIAS, podada por cron, não por este processo). O
campo `sessao` agrupa chamadas de uma mesma sessão de cliente; `sujeito` e `azp` vêm
do JWT e registram QUEM chamou e por qual cliente OAuth. Atribuição de PERSONA segue
dívida: as cadeiras compartilham um client (`claudinho-mcp`), então o log identifica o
humano e o cliente, não a cadeira — projetar a cadeira no token é o card #436.

PATH DO SUBPROCESSO: montado explicitamente, porque `bash -c` não-login não lê .bashrc
nem .profile — sem isto, tudo que vive em OPS_ROOT/bin e ~/.local/bin existe no disco e
é invisível para quem chama a tool. O env do subprocesso também é depurado dos segredos
da instância: um comando qualquer não deve conseguir ecoar o token que o autorizou.
"""
import hmac
import json
import logging
import os
import re
import signal
import socket
import subprocess
import sys
import time
from contextvars import ContextVar
from datetime import date, datetime
from pathlib import Path

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

OPS_NAME = os.environ.get("OPS_NAME", "platafirma-ops")
OPS_USER = os.environ.get("OPS_USER", "claudinho")
RAIZ = Path(os.environ.get("OPS_ROOT", "/home/claudinho/AI"))
OPS_AUTH_TOKEN = os.environ.get("OPS_AUTH_TOKEN", "")

# --- OIDC (card #435) ---
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma")
OIDC_JWKS_URL = os.environ.get(
    "OIDC_JWKS_URL",
    "http://127.0.0.1:8180/realms/platafirma/protocol/openid-connect/certs")
OIDC_AUDIENCE = os.environ.get("OIDC_AUDIENCE", "ops-mcp")
OPS_RESOURCE = os.environ.get("OPS_RESOURCE", "https://ops.platafirma.org")
# Prazo da rota de emergência. Vencido, o token estático deixa de ser aceito.
OPS_TOKEN_ESTATICO_ATE = os.environ.get("OPS_TOKEN_ESTATICO_ATE", "2026-09-30")
CAP = 50_000   # teto de bytes de stdout/stderr devolvidos (truncagem sempre declarada)

LOG_DIR = Path(os.environ.get("OPS_LOG_DIR", RAIZ / "var/log/ops"))
CMD_CAP = 2_000        # teto do comando gravado na auditoria
LINHA_CAP = 8_000      # teto da linha JSONL

# Segredos da instância não descem para o subprocesso.
ENV_OCULTO = ("OPS_AUTH_TOKEN", "TUNNEL_TOKEN")

_sessao: ContextVar[str] = ContextVar("sessao", default="-")


# --- helpers puros ---
def _token_ok(header: str, query: str, expected: str) -> bool:
    if not expected:
        return False
    if header.startswith("Bearer ") and hmac.compare_digest(header[len("Bearer "):], expected):
        return True
    return bool(query) and hmac.compare_digest(query, expected)


def _cap(raw: bytes) -> dict:
    return {"texto": raw[:CAP].decode("utf-8", "replace"),
            "truncado": len(raw) > CAP, "bytes_total": len(raw)}


def _env_subprocesso() -> dict:
    """Env do subprocesso: PATH explícito + segredos removidos.

    `bash -c` não-login não lê .bashrc nem .profile, então o PATH herdado do systemd
    não contém OPS_ROOT/bin nem ~/.local/bin. Montar aqui é a única forma de o binário
    instalado em user-space ser encontrável por quem chama a tool.
    """
    env = {k: v for k, v in os.environ.items() if k not in ENV_OCULTO}
    casa = os.path.expanduser("~")
    env["PATH"] = f"{RAIZ}/bin:{casa}/.local/bin:" + os.environ.get("PATH", "")
    return env


def _sessao_atual() -> str:
    """Identidade da sessão MCP em curso.

    O header Mcp-Session-Id NÃO chega até aqui: o middleware roda numa task e o FastMCP
    processa a tool noutra, iniciada pelo session manager no lifespan — contextvar setada
    no meio do caminho não propaga. O que propaga é o contexto do próprio FastMCP, que
    carrega o ServerSession, um por transporte. `id()` do objeto é estável enquanto a
    sessão vive; recicla depois do GC, o que é aceitável porque o valor só precisa
    agrupar chamadas dentro de uma janela, não identificar através do tempo.
    """
    try:
        s = getattr(mcp.get_context(), "session", None)
        return f"s{id(s):x}" if s is not None else _sessao.get()
    except Exception:                                       # noqa: BLE001
        return _sessao.get()


def _audit(**campos) -> None:
    """Grava uma linha JSONL de auditoria. Nunca derruba a operação — mas falha de
    auditoria vai para o stderr (journal), porque auditoria que falha em silêncio é
    pior que auditoria ausente: a ausência pelo menos é visível."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        reg = {"ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
               "instancia": OPS_NAME, "usuario": OPS_USER,
               "sessao": _sessao_atual(), **campos}
        if "sujeito" not in reg and campos.get("tool", "-") != "-":
            reg.update(_quem())
        linha = (json.dumps(reg, ensure_ascii=False)[:LINHA_CAP] + "\n").encode()
        alvo = LOG_DIR / f"ops-{date.today().isoformat()}.jsonl"
        fd = os.open(alvo, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, linha)
        finally:
            os.close(fd)
    except Exception as e:                                  # noqa: BLE001
        print(f"[audit] FALHOU: {e!r}", file=sys.stderr, flush=True)


_jwks_cli = None


def _jwks():
    """Cliente JWKS com cache — a chave do realm só se busca quando o `kid` muda."""
    global _jwks_cli
    if _jwks_cli is None:
        from jwt import PyJWKClient
        _jwks_cli = PyJWKClient(OIDC_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks_cli


def _sujeito_do_jwt(header: str) -> dict:
    """Valida o Bearer como JWT do realm e devolve a identidade. {} = não é JWT válido.

    Devolver {} em vez de levantar é deliberado: quem chama decide se cai na rota de
    emergência ou nega. A negativa loga o motivo, nunca o token."""
    if not header.startswith("Bearer "):
        return {}
    tok = header[len("Bearer "):].strip()
    if tok.count(".") != 2:                 # token estático não é JWT — nem tenta
        return {}
    try:
        import jwt
        claims = jwt.decode(
            tok, _jwks().get_signing_key_from_jwt(tok).key,
            algorithms=["RS256", "ES256"], audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER,
            options={"require": ["exp", "iat", "sub"]})
        return {"sujeito": claims.get("preferred_username") or claims.get("sub"),
                "sub": claims.get("sub"), "azp": claims.get("azp", "-")}
    except Exception as e:                                  # noqa: BLE001
        _audit(tool="-", evento="jwt_recusado", motivo=type(e).__name__)
        return {}


def _estatico_vigente() -> bool:
    try:
        return date.today() <= date.fromisoformat(OPS_TOKEN_ESTATICO_ATE)
    except ValueError:
        return False


def _quem() -> dict:
    """Identidade de quem chamou, do ponto de vista de DENTRO da tool.

    O contextvar setado no middleware não propaga até aqui (mesma razão de
    `_sessao_atual`), então o caminho honesto é reler o header do request que o FastMCP
    carrega no seu próprio contexto e revalidar. O JWKS está em cache: custa uma
    verificação de assinatura, não uma ida à rede."""
    try:
        req = getattr(mcp.get_context().request_context, "request", None)
        if req is not None:
            return _sujeito_do_jwt(req.headers.get("authorization", ""))
    except Exception:                                       # noqa: BLE001
        pass
    return {}


mcp = FastMCP(
    OPS_NAME,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _run_blocking(command: str, d: Path, timeout: int) -> dict:
    """Parte síncrona de run_command — roda em thread do anyio, nunca no event loop
    (ver docstring de run_command pra motivo)."""
    try:
        p = subprocess.Popen(["bash", "-c", command], cwd=d,
                              env=_env_subprocesso(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True)
    except OSError as e:
        return {"erro": str(e), "cwd": str(d)}
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait()
        return {"erro": f"timeout ({timeout}s) — grupo de processo morto", "cwd": str(d)}
    return {"exit_code": p.returncode, "stdout": _cap(stdout),
            "stderr": _cap(stderr), "cwd": str(d)}


async def run_command(command: str, cwd: str = "", timeout: int = 120) -> dict:
    """Executa um comando shell (bash -c) como o usuário @USER@. Verbo único e
    genérico por decisão: git, docker (rootless), systemctl --user, tudo passa por aqui.

    cwd é relativo a @ROOT@ (vazio = a própria raiz). timeout em segundos
    (teto 600). stdout/stderr voltam com truncagem declarada (truncado/bytes_total).

    PATH: @ROOT@/bin e ~/.local/bin JÁ ESTÃO no PATH do comando — o servidor os injeta,
    porque `bash -c` não-login não lê .bashrc nem .profile. Não é preciso exportar PATH
    nem usar caminho absoluto para o ferramental instalado em user-space. Os segredos da
    instância (OPS_AUTH_TOKEN, TUNNEL_TOKEN) NÃO descem para o ambiente do comando.

    AUDITORIA: toda chamada grava linha JSONL em @ROOT@/var/log/ops/ com o comando, o
    cwd, o exit code e a duração. Não é opcional e não é silenciável pelo chamador.

    A parte bloqueante roda em thread separada via anyio.to_thread (limite padrão 40
    concorrentes) — NUNCA inline no event loop. O FastMCP despacha tool síncrona com
    `fn(**args)` direto (mcp/server/fastmcp/utilities/func_metadata.py), sem offload
    próprio; sem esse anyio.to_thread aqui, um run_command em andamento — mesmo dentro
    do timeout declarado — trava TODO o resto do ops-mcp (outras tool calls, /health,
    accept() de conexão nova) até retornar, porque o processo é single-threaded e
    asyncio é cooperativo. Roda também em session/process group próprio
    (start_new_session=True): no timeout, mata o grupo inteiro (os.killpg), não só o
    bash direto — sem isso, algo em background (&, nohup, docker exec ...) sobrevive
    ao run_command que o criou, e se herdou o fd do pipe de stdout/stderr, trava o
    communicate() driblando o timeout declarado.
    """
    d = (RAIZ / cwd) if cwd else RAIZ
    timeout = max(1, min(timeout, 600))
    t0 = time.monotonic()
    r = await anyio.to_thread.run_sync(_run_blocking, command, d, timeout)
    _audit(tool="run_command", comando=command[:CMD_CAP],
           comando_truncado=len(command) > CMD_CAP, cwd=str(d),
           exit_code=r.get("exit_code"), erro=r.get("erro"),
           bytes_stdout=r.get("stdout", {}).get("bytes_total"),
           dur_ms=round((time.monotonic() - t0) * 1000))
    return r


# --- fila: fora do alcance de read_file/write_file ---------------------------
# A fila tem verbo proprio (`fila`), que faz append sob flock e sabe de quem e a
# caixa. write_file SUBSTITUI: em 05/08/2026 apagou 23.120 bytes da caixa de uma
# persona alheia numa tacada. Arquivo de fila so se toca pelo verbo.
FILA_RAIZ = Path(os.environ.get("PF_FILA", RAIZ / "fila")).resolve()


def _nega_fila(p: Path, tool: str):
    try:
        alvo = p.resolve()
    except OSError:
        return None
    if alvo == FILA_RAIZ or FILA_RAIZ in alvo.parents:
        _audit(tool=tool, path=str(p), erro="fila: use o verbo `fila`")
        return {"erro": "caminho sob a fila — read_file/write_file nao operam ai. "
                        "Use o verbo: `fila status|ler|consumir|enviar` (append sob "
                        "flock, com identidade). Motivo: write_file substitui.",
                "path": str(p)}
    return None


def read_file(path: str, offset: int = 0, max_bytes: int = 40000) -> dict:
    """Lê um arquivo sob @ROOT@ (path relativo à raiz).

    Truncagem sempre declarada: truncated/bytes_total/next_offset para paginar.
    Inexistente volta com erro preenchido, nunca exceção.
    """
    p = RAIZ / path
    bloqueio = _nega_fila(p, "read_file")
    if bloqueio:
        return bloqueio
    if not p.is_file():
        _audit(tool="read_file", path=str(p), erro="não existe ou não é arquivo")
        return {"erro": "não existe ou não é arquivo", "path": str(p)}
    data = p.read_bytes()
    offset = max(0, offset)
    max_bytes = max(1, min(max_bytes, 200000))
    chunk = data[offset:offset + max_bytes]
    fim = offset + len(chunk)
    _audit(tool="read_file", path=str(p), bytes_lidos=len(chunk), bytes_total=len(data))
    return {"content": chunk.decode("utf-8", "replace"), "bytes_total": len(data),
            "truncated": fim < len(data), "next_offset": fim if fim < len(data) else None,
            "path": str(p)}


def write_file(path: str, content: str) -> dict:
    """Cria ou substitui um arquivo sob @ROOT@ (path relativo à raiz),
    criando diretórios intermediários. Conteúdo é o arquivo INTEIRO."""
    p = RAIZ / path
    bloqueio = _nega_fila(p, "write_file")
    if bloqueio:
        return bloqueio
    existia = p.is_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    _audit(tool="write_file", path=str(p), bytes=len(content.encode()),
           substituiu=existia)
    return {"ok": True, "path": str(p), "bytes": len(content.encode())}


# --- contexto de abertura de cadeira -----------------------------------------
# As duas variáveis saem do TEXTO da persona, nunca do nome do arquivo: a linha 1
# ("Você é <nome>,") dá o nome canônico — que é o diretório da fila — e a linha
# FERRAMENTAL: dá o caminho do manifesto. Convenção de nome de arquivo não produz o
# "claudinha" de persona-fabrica.md.
PERSONAS = Path(os.environ.get("PF_PERSONAS", RAIZ / "platafirma-harness/personas"))
ORG_CANONICO = Path(os.environ.get(
    "PF_ORG", RAIZ / "platafirma-arquitetura/docs/org-template-canonico.md"))
FILA = Path(os.environ.get("PF_FILA", RAIZ / "fila"))
REPOS_SESSAO = ("platafirma-harness", "platafirma-arquitetura")
MANIFESTO_GERAL = Path(os.environ.get(
    "PF_MANIFESTO_GERAL", RAIZ / "platafirma-harness/tool-manifest/TODA-CADEIRA.md"))
FM_CAMPOS = ("de", "para", "em", "tipo", "assunto", "ref", "responde")
MSG_HOST = os.environ.get("PF_MSG_HOST", "127.0.0.1")
MSG_PORT = int(os.environ.get("PF_MSG_PORT", "6379"))


def _personas_com_caixa() -> set:
    """Quem tem caixa na malha: a lista `fila/.personas`, mesma fonte do verbo."""
    lista = FILA / ".personas"
    if not lista.is_file():
        return set()
    return {ln.strip() for ln in lista.read_text(encoding="utf-8").splitlines() if ln.strip()}
RE_NOME = re.compile(r"^Você é ([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]*)")
RE_FERRAMENTAL = re.compile(r"^FERRAMENTAL:\s*(\S+\.md)")
RE_MSG = re.compile(r"^===MSG\s+(.+?)\s*===\s*$", re.M)


def _cadeiras() -> list:
    return sorted(p.name[len("persona-"):-len(".md")]
                  for p in PERSONAS.glob("persona-*.md"))


def _ler(p: Path) -> dict:
    if not p.is_file():
        return {"path": str(p), "ausente": True}
    return {"path": str(p), "content": p.read_text(encoding="utf-8", errors="replace")}


def _envelope(p: Path) -> dict:
    """Campos do envelope da mensagem, SEM o corpo — o corpo sai por read_file.

    Estado da fila é quem mandou, quando e sobre o quê; despejar corpo aqui é
    pré-carregar contexto que a sessão pode não usar.
    """
    cab = {"arquivo": p.name, "bytes": p.stat().st_size}
    linhas = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if not linhas or linhas[0].strip() != "---":
        cab["aviso"] = "mensagem sem envelope YAML"
        return cab
    for linha in linhas[1:30]:
        if linha.strip() == "---":
            break
        chave, sep, valor = linha.partition(":")
        if sep and chave.strip() in FM_CAMPOS and valor.strip():
            cab[chave.strip()] = valor.strip()
    return cab


class _Resp:
    """Cliente RESP minimo para a malha msg. Socket puro de proposito: o servico
    nao ganha dependencia nova por causa da leitura de uma caixa."""

    def __init__(self, host="127.0.0.1", port=6379, timeout=3):
        self.s = socket.create_connection((host, port), timeout)
        self.s.settimeout(timeout)
        self.buf = b""

    def _linha(self):
        while b"\r\n" not in self.buf:
            pedaco = self.s.recv(65536)
            if not pedaco:
                raise ConnectionError("conexao fechada pelo servidor")
            self.buf += pedaco
        linha, self.buf = self.buf.split(b"\r\n", 1)
        return linha

    def _bytes(self, n):
        while len(self.buf) < n + 2:
            pedaco = self.s.recv(65536)
            if not pedaco:
                raise ConnectionError("conexao fechada pelo servidor")
            self.buf += pedaco
        dado, self.buf = self.buf[:n], self.buf[n + 2:]
        return dado

    def _ler(self):
        linha = self._linha()
        tag, corpo = linha[:1], linha[1:]
        if tag == b"+":
            return corpo.decode()
        if tag == b"-":
            raise RuntimeError(corpo.decode())
        if tag == b":":
            return int(corpo)
        if tag == b"$":
            n = int(corpo)
            return None if n == -1 else self._bytes(n).decode("utf-8", "replace")
        if tag == b"*":
            n = int(corpo)
            return None if n == -1 else [self._ler() for _ in range(n)]
        raise RuntimeError(f"RESP inesperado: {linha!r}")

    def cmd(self, *args):
        saida = b"*%d\r\n" % len(args)
        for a in args:
            a = str(a).encode()
            saida += b"$%d\r\n%s\r\n" % (len(a), a)
        self.s.sendall(saida)
        return self._ler()

    def fecha(self):
        try:
            self.s.close()
        except OSError:
            pass


def _envelopes_stream(nome: str) -> tuple:
    """Envelopes NOVOS da caixa na malha msg, sem corpo.

    Novo = depois do ponteiro do consumer group da cadeira. Devolve
    (mensagens, bytes, total_no_historico, erro). Leitura FRIA por XRANGE: montar
    sessao nao pode mover o ponteiro, senao abrir a sessao consumiria a caixa e o
    `fila ler` seguinte viria vazio. Quem move o ponteiro e o verbo, ao entregar.

    Erro preenchido significa malha inalcancavel: quem chama declara a falha,
    nunca reporta caixa vazia por nao ter conseguido ler.
    """
    c = None
    try:
        c = _Resp(MSG_HOST, MSG_PORT)
        chave = f"caixa:{nome}"
        total = c.cmd("XLEN", chave)
        ponteiro, pendentes = "0-0", 0
        for g in c.cmd("XINFO", "GROUPS", chave) or []:
            campos = dict(zip(g[::2], g[1::2]))
            if campos.get("name") == "cadeira":
                ponteiro = campos.get("last-delivered-id", "0-0")
                pendentes = campos.get("pending", 0) or 0
        entradas = c.cmd("XRANGE", chave, f"({ponteiro}", "+")
    except (OSError, RuntimeError, ConnectionError) as e:
        return [], 0, 0, f"malha msg inalcancavel em {MSG_HOST}:{MSG_PORT} — {e}"
    finally:
        if c:
            c.fecha()
    saida, tamanho = [], 0
    for _tecnico, plano in entradas or []:
        campos = dict(zip(plano[::2], plano[1::2]))
        corpo = campos.get("corpo", "")
        tamanho += len(corpo.encode())
        ident = campos.get("id", "")
        cab = {"id": ident, "bytes": len(corpo.encode()), "em": ident.partition("-")[0]}
        for k in FM_CAMPOS:
            if campos.get(k):
                cab[k] = campos[k]
        saida.append(cab)
    return saida, tamanho, total, ""


def _envelopes_caixa(texto: str) -> list:
    """Envelopes da caixa-arquivo: um bloco por `===MSG <carimbo>-<remetente>===`.

    Mesmo contrato do `_envelope`: cabeçalho, nunca corpo. Carimbo e remetente saem
    do próprio marcador; linha explícita no cabeçalho sobrescreve o derivado.
    """
    saida = []
    marcas = list(RE_MSG.finditer(texto))
    for i, m in enumerate(marcas):
        ident = m.group(1).strip()
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        corpo = texto[m.end():fim]
        carimbo, _, remetente = ident.partition("-")
        cab = {"id": ident, "bytes": len(corpo.encode()), "em": carimbo}
        if remetente:
            cab["de"] = remetente
        linhas = corpo.splitlines()
        while linhas and not linhas[0].strip():
            linhas.pop(0)
        for linha in linhas:
            if not linha.strip():
                break
            chave, sep, valor = linha.partition(":")
            if sep and chave.strip() in FM_CAMPOS and valor.strip():
                cab[chave.strip()] = valor.strip()
        saida.append(cab)
    return saida


def _idade(d: Path, estado: dict) -> None:
    """Carimba sha, data do HEAD e data do ultimo fetch. Sem rede."""
    try:
        sha = subprocess.run(["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
                             capture_output=True, timeout=10)
        if sha.returncode == 0:
            estado["sha"] = sha.stdout.decode().strip()
        dt = subprocess.run(["git", "-C", str(d), "log", "-1", "--format=%cI"],
                            capture_output=True, timeout=10)
        if dt.returncode == 0:
            estado["head_em"] = dt.stdout.decode().strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    fh = d / ".git" / "FETCH_HEAD"
    estado["sincronizado_em"] = (
        datetime.fromtimestamp(fh.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        if fh.exists() else None)


def _estado_repos() -> dict:
    """Estado dos clones sem ida a rede: e o que torna 'servir do clone' auditavel.
    Sem isto, clone velho e clone no head sao indistinguiveis para a sessao."""
    estado = {}
    for r in REPOS_SESSAO:
        d = RAIZ / r
        if not (d / ".git").is_dir():
            estado[r] = {"atualizado": False, "erro": "nao e clone git"}
            continue
        estado[r] = {"atualizado": False, "motivo": "sem pull nesta chamada"}
        _idade(d, estado[r])
    return estado


def _pull(timeout: int = 25) -> dict:
    """Traz os clones ao dia. Falha de rede não é exceção: vira estado declarado —
    o pacote continua servindo do clone, com `atualizado: false` no repo que falhou.
    """
    estado = {}
    for r in REPOS_SESSAO:
        d = RAIZ / r
        if not (d / ".git").is_dir():
            estado[r] = {"atualizado": False, "erro": "não é clone git"}
            continue
        try:
            p = subprocess.run(["git", "-C", str(d), "pull", "--ff-only", "-q"],
                               capture_output=True, timeout=timeout)
            estado[r] = ({"atualizado": True} if p.returncode == 0 else
                         {"atualizado": False,
                          "erro": p.stderr.decode("utf-8", "replace").strip()[:200]})
        except (subprocess.TimeoutExpired, OSError) as e:
            estado[r] = {"atualizado": False, "erro": f"{e.__class__.__name__}: {e}"}
        _idade(d, estado[r])
    return estado


def _memoria(cadeira: str) -> dict:
    """Memória da cadeira, lida pelo verbo `mesa` — nunca por cliente redis próprio
    aqui dentro: segunda implementação da mesma regra diverge em silêncio, que é o
    mesmo motivo de a fila ser lida pelo verbo.

    A mesa (classe `mem`, arq:0041) entra INTEIRA — é o resíduo curto da fita
    anterior. Do caderno durável entra só o ÍNDICE; o corpo sai por
    `mesa caderno <chapéu>`, na fita que o quiser. Carregar o caderno de todos os
    chapéus a cada giro anularia a razão de a memória ser partida por chapéu.
    """
    out = {}
    verbo = str(RAIZ / "bin" / "mesa")
    for chave, args in (("mesa", ["ver"]), ("cadernos", ["caderno"])):
        try:
            proc = subprocess.run([verbo, *args], capture_output=True, text=True,
                                  timeout=15, env={**os.environ, "PF_CADEIRA": cadeira})
            if proc.returncode == 0:
                out[chave] = {"texto": proc.stdout.strip()}
            else:
                out[chave] = {"indisponivel": True,
                              "erro": (proc.stderr or proc.stdout).strip()[:300]}
        except (OSError, subprocess.SubprocessError) as e:
            out[chave] = {"indisponivel": True, "erro": f"{type(e).__name__}: {e}"}
    out["nota"] = ("chapéu declarado na persona é o slot nos dois: `mesa anota <slot>` "
                   "escreve a mesa, `mesa caderno <slot>` abre o caderno. Substrato "
                   "fora do ar é declarado como indisponivel, nunca como memória vazia")
    return out


def _montar(cadeira: str, atualizar: bool) -> dict:
    alvo = cadeira.strip()
    for prefixo in ("claudinho-", "claudinha-"):
        if alvo.lower().startswith(prefixo):
            alvo = alvo[len(prefixo):]
    p = PERSONAS / f"persona-{alvo}.md"
    if not p.is_file():
        return {"erro": f"não existe persona para '{cadeira}'",
                "procurado": str(p), "cadeiras": _cadeiras()}

    repos = _pull() if atualizar else _estado_repos()
    texto = p.read_text(encoding="utf-8", errors="replace")
    linha1 = texto.splitlines()[0] if texto else ""
    m_nome = RE_NOME.match(linha1)
    nome = m_nome.group(1) if m_nome else ""

    manifesto = None
    for linha in texto.splitlines():
        m = RE_FERRAMENTAL.match(linha)
        if m:
            manifesto = m.group(1)
            break

    r = {"cadeira": alvo, "nome_canonico": nome or None, "repos": repos,
         "persona": _ler(p), "org": _ler(ORG_CANONICO)}
    if not nome:
        r["aviso_nome"] = (f"linha 1 de {p} não casa 'Você é <nome>' — nome canônico "
                           "não resolvido, fila não localizada")
    r["manifesto_geral"] = _ler(MANIFESTO_GERAL)
    if manifesto:
        r["manifesto"] = _ler(RAIZ / manifesto)
    else:
        r["manifesto"] = {"ausente": True, "aviso": (
            f"{p} não declara linha FERRAMENTAL: — manifesto não entrou no pacote. "
            "Ausência declarada de propósito: omitir em silêncio faria a sessão "
            "supor ferramental que a persona não declara.")}

    r["memoria"] = _memoria(alvo)

    # A caixa VIVA é o stream `caixa:<nome>` na malha msg (arq:0018, arq:0036),
    # escrito e consumido pelo verbo `fila`. O arquivo `fila/<nome>.md` é o
    # transporte anterior e não recebe mais escrita — ler dele devolveria estado
    # congelado sem erro, que é o modo de falha que esta troca fecha.
    # Endereço encerrado (porteiro) mora em `fila/.encerradas/<nome>.md` e o texto
    # dele É a resposta: diz por onde entra. O diretório `fila/<nome>/` é o formato
    # anterior — enquanto tiver mensagem dentro entra como `legado`, porque
    # re-apontar sem reportar troca uma omissão silenciosa por outra.
    caixa = FILA / f"{nome}.md" if nome else None
    encerrada = FILA / ".encerradas" / f"{nome}.md" if nome else None
    legado = FILA / nome if nome else None

    if nome and nome in _personas_com_caixa():
        msgs, tamanho, total, erro = _envelopes_stream(nome)
        r["fila"] = {"path": f"caixa:{nome}", "estado": "aberta",
                     "novas": len(msgs), "no_historico": total,
                     "bytes": tamanho,
                     "mensagens": msgs,
                     "nota": "só o que chegou desde a última leitura da cadeira; o "
                             "resto do histórico (7 dias) sai por `fila ler <persona> "
                             "--tudo`. Corpo sempre por `fila ler`, nunca por read_file"}
        if erro:
            r["fila"]["estado"] = "indisponivel"
            r["fila"]["erro"] = erro
    elif encerrada and encerrada.is_file():
        r["fila"] = {"path": str(encerrada), "estado": "fechada", "total": 0,
                     "porteiro": encerrada.read_text(encoding="utf-8", errors="replace"),
                     "nota": "endereço fechado por decisão — o texto acima diz por onde entra"}
    else:
        r["fila"] = {"path": str(caixa) if caixa else None, "estado": "inexistente",
                     "total": 0,
                     "nota": "não há caixa neste endereço — demanda entra por outra porta"}

    if legado and legado.is_dir():
        antigas = sorted(legado.glob("*.md"))
        if antigas:
            r["fila"]["legado"] = {
                "dir": str(legado), "total": len(antigas),
                "mensagens": [_envelope(m) for m in antigas],
                "nota": "formato anterior (um arquivo por mensagem), NÃO migrado: "
                        "não estão na caixa viva, o verbo `fila` não as enxerga e "
                        "read_file não abre caminho sob a fila — corpo só por "
                        "run_command"}
    return r


async def monta_sessao(cadeira: str = "", atualizar: bool = True) -> dict:
    """Devolve, numa chamada, o contexto de abertura de uma cadeira da PlataFirma:
    persona canônica, tool-manifest que ELA declara, org canônico e o estado da fila.

    Chamar no lugar de encadear leituras na abertura de sessão — é o que esta tool
    existe para matar. Ler o manifesto NÃO é pré-condição para pensar nem para
    responder: a tool é chamável sob demanda, não obrigatória na entrada.

    `cadeira`: sufixo da persona (`TI`, `IA`, `fabrica`) — o prefixo `claudinho-`/
    `claudinha-` é aceito e descartado. Vazia ou desconhecida devolve `cadeiras`
    com a lista válida, nunca erro mudo.

    `atualizar` (default true): dá `git pull --ff-only` nos clones de persona e org
    antes de ler. Falha de rede não interrompe — o pacote vem do clone com
    `atualizado: false` declarado. Com ou sem pull, `repos` traz sempre `sha`,
    `head_em` (data do commit servido) e `sincronizado_em` (último fetch): clone
    velho e clone no head são indistinguíveis sem isso, e servir do clone só é
    seguro quando a idade vem declarada.

    O pacote traz DOIS manifestos: `manifesto` (o que a persona declara em
    FERRAMENTAL:) e `manifesto_geral` (tool-manifest/TODA-CADEIRA.md, operacional comum
    a toda cadeira). O manifesto da cadeira remete ao geral e não repete o que
    está lá — entregar só um obrigava a sessão a uma segunda leitura para
    qualquer verbo comum.

    Traz também a MEMÓRIA da cadeira, particionada por chapéu (arq:0041): `memoria.mesa`
    é a memória de trabalho da fita anterior, inteira; `memoria.cadernos` é só o ÍNDICE
    dos cadernos duráveis — o corpo sai por `mesa caderno <chapéu>`, sob demanda.

    O que NÃO vem: corpo das mensagens da fila (só o envelope — `read_file` traz o
    corpo), o corpo dos cadernos (só o índice) e nada de acervo (faceta e população entram como ponteiro, nunca como
    valor: `rag_facets` é a tool própria disso). Pré-carregar o que a sessão não vai
    usar é o custo que esta tool existe para reduzir, não para reproduzir.

    Persona sem linha `FERRAMENTAL:` devolve `manifesto.ausente` com aviso explícito
    — hoje é o caso de claudinha-osint. Ausência declarada, nunca omissão silenciosa.
    """
    t0 = time.monotonic()
    r = await anyio.to_thread.run_sync(_montar, cadeira, atualizar)
    _audit(tool="monta_sessao", cadeira=cadeira, atualizar=atualizar,
           resolvida=r.get("nome_canonico"), erro=r.get("erro"),
           fila_total=r.get("fila", {}).get("total"),
           dur_ms=round((time.monotonic() - t0) * 1000))
    return r


# Registro tardio: o __doc__ é a descrição que o cliente lê, e ela precisa nomear o
# usuário e a raiz DESTA instância. Substituir depois de registrar não adianta — o
# FastMCP copia a descrição no momento do mcp.tool().
_TOOLS = [run_command, read_file, write_file]
# monta_sessao só existe onde há personas: numa instância com outra OPS_ROOT (osint)
# a tool não teria o que montar, e tool inútil no catálogo é contexto desperdiçado.
if PERSONAS.is_dir():
    _TOOLS.append(monta_sessao)

for _fn in _TOOLS:
    _fn.__doc__ = (_fn.__doc__ or "").replace("@ROOT@", str(RAIZ)).replace("@USER@", OPS_USER)
    mcp.tool()(_fn)


# ponytail: tool git dedicada não existe — git é comando e run_command cobre; adicionar
# verbo próprio só se o uso mostrar necessidade.


class RedigeToken(logging.Filter):
    """Tira `?token=` do access log do uvicorn. O access log vai para o journal, o
    journal persiste e é legível por qualquer processo do usuário — sem isto, o token
    que autoriza shell fica gravado em claro numa linha por request."""
    _RE = re.compile(r"token=[^&\s\"']+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._RE.sub("token=<redigido>", a) if isinstance(a, str) else a
                for a in record.args)
        record.msg = self._RE.sub("token=<redigido>", record.msg) if isinstance(record.msg, str) else record.msg
        return True


for _nome in ("uvicorn.access", "uvicorn.error", "uvicorn"):
    logging.getLogger(_nome).addFilter(RedigeToken())


ABERTAS = ("/health", "/.well-known/oauth-protected-resource")


class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        caminho = request.url.path.rstrip("/")
        if caminho in ABERTAS or caminho.startswith(ABERTAS[1] + "/"):
            return await call_next(request)

        header = request.headers.get("authorization", "")
        ident, via = _sujeito_do_jwt(header), "oidc"
        if not ident and _estatico_vigente() and _token_ok(
                header, request.query_params.get("token", ""), OPS_AUTH_TOKEN):
            ident, via = {"sujeito": OPS_USER, "sub": "-", "azp": "token-estatico"}, "estatico"
        if not ident:
            _audit(tool="-", evento="auth_negada", path=request.url.path,
                   cliente=request.client.host if request.client else "-")
            # Sem este header o cliente MCP não descobre o authorization server e o
            # fluxo morre antes da tela de login (RFC 9728).
            return JSONResponse(
                {"error": "unauthorized"}, status_code=401,
                headers={"WWW-Authenticate": 'Bearer resource_metadata='
                         f'"{OPS_RESOURCE}/.well-known/oauth-protected-resource"'})

        _sessao.set(request.headers.get("mcp-session-id", "-"))
        _audit(tool="-", evento="http_req", path=request.url.path, via=via, **ident,
               mcp_session=request.headers.get("mcp-session-id", "-"))
        return await call_next(request)


async def _health(_req):
    return PlainTextResponse("ok")


async def _prm(_req):
    """Protected resource metadata (RFC 9728) — é por aqui que o cliente MCP descobre
    contra qual realm autenticar. `resource` tem de bater com a URL do MCP."""
    return JSONResponse({
        "resource": f"{OPS_RESOURCE}/mcp",
        "authorization_servers": [OIDC_ISSUER],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["openid", "profile", "offline_access"],
    })


app = mcp.streamable_http_app()
app.router.routes.append(Route("/health", _health))
app.router.routes.append(Route("/.well-known/oauth-protected-resource", _prm))
app.router.routes.append(Route("/.well-known/oauth-protected-resource/mcp", _prm))
app.add_middleware(BearerAuth)
