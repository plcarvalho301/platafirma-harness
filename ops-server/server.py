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
não tem shell no host. Vencido o prazo, só JWT entra. O token vai SEMPRE no header:
o aceite via `?token=` saiu em 20/08/2026, porque redigir o nosso access log não
alcança o log do proxy, o Referer nem o histórico — e o que trafega ali é credencial
de portador.

MULTI-INSTÂNCIA: o mesmo arquivo serve mais de uma instância, uma por usuário do host.
OPS_NAME, OPS_USER, OPS_ROOT e OPS_AUTH_TOKEN separam as instâncias; o default é a
instância histórica (claudinho-mcp sob claudinho). OPS_USER e OPS_ROOT entram nas
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
import uuid
import re
import signal
import subprocess
import sys
import time
from contextvars import ContextVar
from datetime import date, datetime
from pathlib import Path

import anyio
import redis
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Route

OPS_NAME = os.environ.get("OPS_NAME", "claudinho-mcp")
OPS_USER = os.environ.get("OPS_USER", "claudinho")
RAIZ = Path(os.environ.get("OPS_ROOT", "/home/claudinho/AI"))
OPS_AUTH_TOKEN = os.environ.get("OPS_AUTH_TOKEN", "")
MEM_REDIS_HOST = os.environ.get("MEM_REDIS_HOST", "127.0.0.1")
MEM_REDIS_PORT = int(os.environ.get("MEM_REDIS_PORT", "6380"))

PF_HARNESS = Path(os.environ.get("PF_HARNESS", RAIZ / "platafirma-harness"))
# CODIGO do PDP (pdp.py, identidade.py, pep.py) mora no repo — versionado, importavel.
PDP_CODE_DIR = PF_HARNESS / "politica-acesso"
if str(PDP_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(PDP_CODE_DIR))
# DADOS de identidade (politica/sujeitos/superficies.yaml) moram FORA do working tree
# de fabrica (incidente #2956, minuta arq 0015 perna 1): nenhum ato de git de fabrica
# no harness reprojeta mais a identidade da plataforma. Override por PDP_DIR.
PDP_DIR = Path(os.environ.get("PDP_DIR", RAIZ / "var" / "politica-acesso"))
from identidade import _jwks, _sujeito_do_jwt

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

# ordem_id: identidade de UMA fita (uma ordem do dono), estavel do inicio ao fim,
# gravada identica em sessao_aberta e em consulta -> chave do join de D (#2902).
# sid (_sessao_atual) e por-conexao e reciclavel (#409); nao serve. monta_sessao
# gera o ordem_id na abertura e mapeia sid->ordem_id; run_command le esse mapa e
# injeta PF_ORDEM_ID no subprocesso, onde o motor ja o consome (bin/motor:281).
_ordem_por_sid: dict[str, str] = {}
_sessao_por_sid: dict[str, str] = {}


# --- helpers puros ---
def _token_ok(header: str, expected: str) -> bool:
    """So o header. `?token=` SAIU em 20/08/2026 (claudinho-seguranca).

    O access log ja era redigido, mas redigir o NOSSO log nao alcanca o log do
    proxy, o Referer nem o historico do navegador — e o que trafega ali e
    credencial de portador, que vale enquanto durar. O token estatico continua,
    com o prazo que ja tinha; o que morre e o transporte pela URL.
    """
    if not expected or not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[len("Bearer "):].strip(), expected)


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
    """Identidade da sessão MCP em curso, em três degraus.

    1. `Mcp-Session-Id` DO REQUEST, que é o valor bom. O comentário anterior dizia que
       ele não chegava aqui, e isso valia para o caminho tentado: contextvar setada no
       middleware não propaga, porque middleware e tool rodam em tasks diferentes. Mas o
       `RequestContext` do próprio FastMCP carrega o campo `request` — o Request do
       Starlette, na MESMA task da tool. Lendo o header dali, sem contextvar no meio, o
       valor chega.
    2. `id()` do ServerSession, o degrau velho. Estável enquanto a sessão vive e
       RECICLADO depois do GC: dois trabalhos distintos podem receber o mesmo `s<hex>`
       em horas diferentes, e foi isso que quase produziu uma atribuição errada de
       autoria em 18/08 (card #409).
    3. O contextvar, para o caminho que não é HTTP.

    O QUE ESTE VALOR NÃO É, e é preciso dizer para ninguém confiar demais: ele
    identifica a CONEXÃO do cliente, não a conversa. Medido em 17-18/08 sobre 350
    chamadas com cadeira declarada: 13 de 32 `mcp-session-id` aparecem com mais de uma
    cadeira — uma conexão do app atende várias abas. Serve para agrupar e para perícia;
    não serve para provar que duas ações são da mesma fita.
    """
    try:
        ctx = mcp.get_context()
        req = getattr(getattr(ctx, "request_context", None), "request", None)
        cab = getattr(req, "headers", None)
        if cab is not None:
            sid = cab.get("mcp-session-id")
            if sid:
                return sid
        s = getattr(ctx, "session", None)
        return f"s{id(s):x}" if s is not None else _sessao.get()
    except Exception:                                       # noqa: BLE001
        return _sessao.get()


# GUARDA DE REENTRANCIA explicita (#2481, Onda 2). O ciclo `_audit`->`_quem`->
# `_sujeito_do_jwt`->(recusa) `auditor=_audit` derrubava o jaiminho-server em todo
# Bearer malformado (RecursionError, 25/08). Aqui `tool=="-"` ja evita resolver
# identidade na recusa, mas 'acidente de formato nao e controle' (caderno iam 25/08):
# a guarda torna o ciclo impossivel mesmo que um chamador futuro audite a recusa com
# tool real. Par explicito do que o jaiminho-server ja tem.
_em_audit = False


def _audit(**campos) -> None:
    """Grava uma linha JSONL de auditoria. Nunca derruba a operação — mas falha de
    auditoria vai para o stderr (journal), porque auditoria que falha em silêncio é
    pior que auditoria ausente: a ausência pelo menos é visível."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        global _em_audit
        if campos.get("tool", "-") != "-" and not _em_audit:
            _em_audit = True
            try:
                ident = _quem()
            finally:
                _em_audit = False
        else:
            ident = {}
        reg = {"ts": datetime.now().astimezone().isoformat(timespec="milliseconds"),
               "instancia": OPS_NAME, "usuario": OPS_USER,
               "sessao": _sessao_atual(), **ident, **campos}
        linha = (json.dumps(reg, ensure_ascii=False)[:LINHA_CAP] + "\n").encode()
        alvo = LOG_DIR / f"ops-{date.today().isoformat()}.jsonl"
        fd = os.open(alvo, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, linha)
        finally:
            os.close(fd)
    except Exception as e:                                  # noqa: BLE001
        print(f"[audit] FALHOU: {e!r}", file=sys.stderr, flush=True)


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
            header = req.headers.get("authorization", "")
            ident = _sujeito_do_jwt(header, auditor=_audit, jwks_url=OIDC_JWKS_URL,
                                    audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER)
            # A rota de emergencia tem de resolver AQUI tambem, e nao so no
            # middleware: com o PEP ligado, sujeito vazio nega por atributo ausente,
            # e a mao que volta quando o realm cai ficaria sem nenhuma tool. Medido
            # no ensaio de 13/08/2026, antes de o realm precisar cair.
            if not ident and _estatico_vigente() and _token_ok(header, OPS_AUTH_TOKEN):
                ident = {"sujeito": OPS_USER, "sub": "-", "username": OPS_USER,
                         "azp": "token-estatico", "sid": "-", "jti": "-"}
            return ident
    except Exception:                                       # noqa: BLE001
        pass
    return {}


# --- PEP: ponto de obediencia da politica de acesso (seg:0008, seg:0009) -----
# Ate 13/08/2026 este servidor validava a ASSINATURA do token e nada mais: quem
# tivesse JWT do realm chamava run_command como @USER@, porque `_quem()` so
# alimentava a auditoria. O PDP e biblioteca embarcada — entra pedido, sai decisao,
# sem rede e sem estado; obedecer e trabalho daqui.
#
# FALHA DE CARGA NEGA. Politica ilegivel e defeito nosso, nao autorizacao: o
# caminho de volta e a instancia anterior do ops, nao um servidor que libera tudo
# porque nao conseguiu ler a regra.
DOM_PLATAFORMA = "plataforma"
DOM_RUNTIME = "plataforma-runtime"
DOM_MENSAGERIA = "mensageria"     # fora do prefixo por ordem do dono, 13/08/2026
_pdp: dict = {"carimbo": None, "politica": None, "sujeitos": None, "erro": "nao carregada"}


# --- gate de ref canonico da fonte de identidade (incidente #2956) ---
# O PEP le sujeitos.yaml do WORKING TREE do harness. Um `git checkout`/rebase/stash
# nesse repo (sessao de fabrica) troca a arvore em vigor e reprojeta a identidade de
# TODA a plataforma. Antes de projetar, exigimos que a fonte esteja no ref canonico.
# Recusa por estado (diagnostico verdadeiro) em vez de negar por atributo ausente
# (diagnostico enganoso do #2956). Minuta arq 0015, perna (2).
#
# INDISPONIBILIDADE NAO E NAO-CANONICO. Se .git for ilegivel por causa transitoria
# (nao um checkout), tratamos como "nao consegui verificar" e NAO bloqueamos por isso
# sozinho — a falha de leitura do proprio sujeitos.yaml adiante ja nega fail-closed.
# O gate so morde o caso que ele existe para pegar: ref presente e != canonico.
def _carrega_politica() -> dict:
    """PAP e projecao de sujeito, relidos quando o mtime de um dos dois muda.

    Merge no PAP passa a valer sem restart — e o que torna `acesso conceder` um ato
    de deploy leve em vez de janela de manutencao."""
    pol_f, suj_f = PDP_DIR / "politica.yaml", PDP_DIR / "sujeitos.yaml"
    try:
        carimbo = (pol_f.stat().st_mtime_ns, suj_f.stat().st_mtime_ns)
    except OSError as e:
        _pdp.update(carimbo=None, politica=None, sujeitos=None,
                    erro=f"politica ilegivel: {e}")
        return _pdp
    if _pdp["carimbo"] == carimbo:
        return _pdp
    try:
        if str(PDP_CODE_DIR) not in sys.path:
            sys.path.insert(0, str(PDP_CODE_DIR))
        import yaml
        from pdp import Politica
        pol = Politica.de_arquivo(pol_f)
        suj = (yaml.safe_load(suj_f.read_text(encoding="utf-8")) or {}).get("sujeitos") or {}
        _pdp.update(carimbo=carimbo, politica=pol, sujeitos=suj, erro=None)
        # Divergencia de vocabulario NAO derruba o servidor: o PDP ja nega sozinho.
        # O que faltava era o typo aparecer COMO typo, em vez de virar negativa
        # silenciosa por intersecao.
        vocab = set(pol.dominios)
        for d in (DOM_PLATAFORMA, DOM_RUNTIME, DOM_MENSAGERIA):
            if d not in vocab:
                _audit(tool="-", evento="pep_vocabulario_divergente", onde="server",
                       dominio=d)
        for nome, atrib in (suj or {}).items():
            for d in (atrib or {}).get("dominios") or ():
                if d not in vocab:
                    _audit(tool="-", evento="pep_vocabulario_divergente",
                           onde="sujeitos.yaml", sujeito=nome, dominio=d)
    except Exception as e:                                  # noqa: BLE001
        _pdp.update(carimbo=carimbo, politica=None, sujeitos=None,
                    erro=f"{type(e).__name__}: {e}")
    return _pdp


def _autoriza(tool: str, acao: str, tipo: str, alvo: str, dominio: str,
              ident: dict | None = None) -> dict | None:
    """None = pode seguir. dict = negativa, ja auditada, pronta para devolver.

    `ident` so se passa nas rotas HTTP: dentro de tool o contexto do FastMCP e a
    unica fonte honesta (mesma razao de `_quem`)."""
    est = _carrega_politica()
    quem = (ident or _quem()).get("sujeito") or "-"
    if est.get("erro"):
        _audit(tool=tool, evento="pep_indisponivel", motivo=est["erro"], sujeito=quem)
        return {"erro": "politica de acesso indisponivel — nego por default",
                "detalhe": est["erro"]}
    from pdp import Recurso, Sujeito, decide
    atrib = (est["sujeitos"] or {}).get(quem)
    if not atrib:
        _audit(tool=tool, evento="pep_negou", regra="projecao", sujeito=quem,
               motivo="sujeito sem atributos declarados")
        return {"erro": f"sujeito {quem!r} nao tem atributos em "
                        "politica-acesso/sujeitos.yaml — o PDP nega por atributo ausente",
                "regra": "projecao"}
    s = Sujeito(id=quem, natureza=atrib.get("natureza"),
                papeis=tuple(atrib.get("papeis") or ()),
                dominios=tuple(atrib.get("dominios") or ()),
                habilitacao=atrib.get("habilitacao", "publico"))
    d = decide(s, acao, Recurso(tipo=tipo, id=alvo, dominio=dominio), est["politica"])
    if d.permitido:
        return None
    _audit(tool=tool, evento="pep_negou", regra=d.regra, motivo=d.motivo, sujeito=quem,
           por_atributo_ausente=d.por_atributo_ausente, alvo=alvo[:CMD_CAP])
    return {"erro": f"negado pela politica de acesso: {d.motivo}", "regra": d.regra}


mcp = FastMCP(
    OPS_NAME,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    stateless_http=True,  # incidente #2890 (27/08): sessao stateful expira em fita ociosa -> 400 -> some a lista inteira de verbos. ops-mcp e request/resposta puro (sem notificacao server->client), entao stateless nao custa funcao e mata o modo de falha.
)


# Por que thread + process group (rationale que morava no __doc__ de run_command):
# o FastMCP despacha tool síncrona inline (`fn(**args)`, sem offload) e o processo é
# single-threaded/asyncio cooperativo — um run_command inline travaria TODO o ops-mcp
# (outras tools, /health, accept()) até retornar. Por isso a parte bloqueante vai a
# anyio.to_thread (limite padrão 40) e roda em session própria (start_new_session):
# no timeout mata-se o grupo (os.killpg), senão `&`/nohup/docker exec sobrevivem e,
# herdando o fd do pipe, travam o communicate() driblando o timeout declarado.
def _run_blocking(command: str, d: Path, timeout: int, sessao_id: str = "-", oid: str = "-") -> dict:
    """Parte síncrona de run_command — roda em thread do anyio, nunca no event loop
    (ver docstring de run_command pra motivo)."""
    try:
        p = subprocess.Popen(["bash", "-c", command], cwd=d,
                              env={**_env_subprocesso(), "PF_SESSAO": sessao_id,
                                   "PF_ORDEM_ID": oid},
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
    """FALLBACK: executa um comando shell (`bash -c`) como o usuário @USER@, para o que
    não tem verbo — git, docker (rootless), systemctl --user, rg, fluxo de dado entre
    verbos. Verbo do núcleo tem tool própria (nome = slug); usá-lo por aqui é medido.

    cwd é relativo a @ROOT@ (vazio = a raiz). timeout em segundos (teto 600); estourou,
    o grupo de processo inteiro é morto. stdout/stderr voltam com truncagem declarada
    (`truncado`/`bytes_total`). `&&` engole o exit code — use `;` ou chamadas separadas.

    PATH já traz @ROOT@/bin e ~/.local/bin (bash -c não lê .bashrc). Segredos da instância
    NÃO descem para o ambiente. AUDITORIA: toda chamada grava JSONL em @ROOT@/var/log/ops/
    (comando, cwd, exit, duração) — não é silenciável.
    """
    negado = _autoriza("run_command", "run_command", "comando", command,
                       DOM_RUNTIME)
    if negado:
        return negado
    d = (RAIZ / cwd) if cwd else RAIZ
    timeout = max(1, min(timeout, 600))
    sid = _sessao_atual()  # capturado AQUI: dentro da thread do anyio,
    # mcp.get_context() nao acha o RequestContext e cairia no fallback '-' (#2911)
    t0 = time.monotonic()
    oid = _ordem_por_sid.get(sid, "-")
    sessao_id = _sessao_por_sid.get(sid, "-")
    r = await anyio.to_thread.run_sync(_run_blocking, command, d, timeout, sessao_id, oid)
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
    negado = _autoriza("read_file", "read_file", "documento", path, DOM_PLATAFORMA)
    if negado:
        return negado
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
    negado = _autoriza("write_file", "write_file", "documento", path, DOM_PLATAFORMA)
    if negado:
        return negado
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
PERSONAS = Path(os.environ.get("PF_PERSONAS", RAIZ / "platafirma-harness/abertura"))
ORG_CANONICO = Path(os.environ.get(
    "PF_ORG", RAIZ / "platafirma-arquitetura/docs/org-template-canonico.md"))
MANIFESTO_GERAL = Path(os.environ.get(
    "PF_MANIFESTO_GERAL", RAIZ / "platafirma-harness/abertura/oficio.md"))


RE_NOME = re.compile(r"^Você é ([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]*)")
RE_FERRAMENTAL = re.compile(r"^FERRAMENTAL:\s*(\S+\.md)")


def _cadeiras() -> list:
    # arq:0073: a cadeira e um subdir de abertura/, nao mais persona-<x>.md.
    return sorted(p.name for p in PERSONAS.iterdir() if p.is_dir())


def _ler(p: Path) -> dict:
    if not p.is_file():
        return {"path": str(p), "ausente": True}
    return {"path": str(p), "content": p.read_text(encoding="utf-8", errors="replace")}


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
                                  timeout=15, env={**_env_subprocesso(), "PF_CADEIRA": cadeira})
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


def _montar(cadeira: str, atualizar: bool, chapeu: str = "", pergunta: str = "") -> dict:
    """Delega ao verbo `bin/monta-sessao --json`, que monta por catálogo (#189 fase 5).

    Aqui havia uma SEGUNDA implementação da montagem: este servidor lia persona, org e
    manifestos por conta própria enquanto o verbo lia os seus. Duas fontes da mesma
    regra divergem em silêncio — é a razão pela qual a mesa e a fila já eram lidas pelo
    verbo, e agora vale para o pacote inteiro. A superfície não pode mudar o pacote:
    `registro/superficies.json` manda que o comportamento seja o mesmo nas três.

    O servidor não acrescenta nada ao pacote: o envelope da fila saiu daqui em
    17/08 (#189) e a camada B inteira é por ato, pelo verbo.
    """
    # Strip do prefixo claudinho-/claudinha- e do verbo (`_sufixo_sem_prefixo`, #2438):
    # segunda implementacao aqui divergiria em silencio. A porta passa o que recebeu.
    argv = [str(RAIZ / "bin" / "monta-sessao"), cadeira.strip(), "--json"]
    if not atualizar:
        argv.append("--sem-atualizar")
    if chapeu:
        argv += ["--chapeu", chapeu]
    if pergunta:
        argv += ["--pergunta", pergunta]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=90,
                              env={**_env_subprocesso(), "PF_SUPERFICIE": "claude.ai"})
        r = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        # Montador mudo se declara: pacote vazio seria indistinguível de cadeira sem peça.
        return {"erro": f"montador não respondeu: {type(e).__name__}: {e}",
                "verbo": " ".join(argv), "cadeiras": _cadeiras()}
    if "erro" in r:
        r.setdefault("cadeiras", _cadeiras())
        return r

    nome = r.get("nome_canonico") or ""
    r["nota_pecas"] = ("cada peça traz {peca, dono, ref, sha, regime, tokens, frescor} "
                       "e o conteúdo servido; a ordem é a de injeção (estável → volátil) "
                       "declarada no catálogo, não a de leitura")

    # A FILA NAO ENTRA NA ABERTURA (#189, ordem do dono 17/08).
    # Regra: a abertura carrega IMPEDIMENTO — o que, sem ato, deixa o estado como
    # esta. Hoje so a mesa; incidente entra nessa classe quando existir. A caixa nao
    # e impedimento: carta nao lida continua la, com retencao de 7 dias, e sai por
    # `fila ler` --tudo/--desde (leitura fria, sem mover o ponteiro).
    # Servir envelope aqui — ou so a contagem — devolve a fila ao lugar da mesa pela
    # saliencia, que e o defeito que ja tinha sido corrigido uma vez e voltou. A
    # conduta corta o ATO de abrir a caixa; enquanto o pacote injetava o texto da
    # carta, a proibicao competia com o item mais concreto da janela.
    # Fila e board sao verbos on-demand, chamados por ordem do dono como qualquer
    # outro. Nao ha peca, nao ha envelope, nao ha contagem.
    return r


async def monta_sessao(cadeira: str = "", atualizar: bool = True, chapeu: str = "", pergunta: str = "") -> dict:
    """Abre a sessão de uma cadeira numa chamada: devolve o pacote de abertura como
    catálogo de peças (persona, ofício, conduta do dono, alias de cadeiras, mesa, índice
    de cadernos, acervo consultado) e cunha `sessao_id` + `ordem_id` para as demais tools.

    NÃO traz fila nem board — abertura carrega só impedimento (a mesa); caixa e carteira
    saem por `fila` e `tarefas`, por ordem do dono.

    `cadeira`: sufixo da persona (`claudinho-`/`claudinha-` aceito e descartado). A lista
    viva de cadeiras NÃO mora neste texto: vem do disco (`abertura/<slug>/`), a cada
    chamada; vazia ou desconhecida devolve `cadeiras` com a lista válida. Afirmar que uma
    cadeira não existe exige essa chamada como âncora (conduta do dono, `NEGATIVA:`).

    `pergunta`: SEMPRE o corpo literal do turno do dono — é o sinal que roteia o chapéu
    (`roteador.via` = determinístico | semântico | fallback). Sem ela, `chapeu` sai null.
    `chapeu`: força o slug e pula o roteador — só quando o dono o disse.

    `atualizar`: aceito e SEM EFEITO desde arq:0097 — o runtime não lê working tree git.
    A abertura vem da morada publicada (`morada.abertura`), árvore imutável fixada pelo
    ponteiro `current`, e quem a atualiza é o ato deliberado `publicar-abertura`. Cada
    peça traz `{peca, dono, ref, sha, regime, volatilidade, tokens, frescor}` e o
    conteúdo; peça que falta vem com `frescor: indisponivel` e o motivo, nunca omitida.
    `pacote` traz a conta (peças, tokens, SHA do ref publicado, registro); `morada` traz
    `{sha, ref, publicado_em, frescor}`; `avisos` traz teto e peça indisponível. Morada
    não publicada é a única recusa de abrir, e o erro nomeia a cura.
    """
    negado = _autoriza("monta_sessao", "monta_sessao", "documento",
                       f"sessao:{cadeira or '-'}", DOM_PLATAFORMA)
    if negado:
        return negado
    t0 = time.monotonic()
    r = await anyio.to_thread.run_sync(_montar, cadeira, atualizar, chapeu, pergunta)
    _rot = (r.get("roteador") or {})
    _sessao_id = None
    # emite sessao_aberta AQUI (contexto MCP da tool), ancorado no MESMO
    # id(session) que run_command usa -> chave do join de D casa por construcao
    # dentro da conexao (#2902). A rota /sessao (externa) nao serve: cai em
    # sessao='-' e nao e o caminho que a fita usa.
    if not r.get("erro"):
        _sid = _sessao_atual()
        _oid = "o" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        _sessao_id = uuid.uuid4().hex
        _ordem_por_sid[_sid] = _oid
        if len(_ordem_por_sid) > 4096:
            for _k in list(_ordem_por_sid)[:-2048]:
                _ordem_por_sid.pop(_k, None)
        _sessao_por_sid[_sid] = _sessao_id
        if len(_sessao_por_sid) > 4096:
            for _k in list(_sessao_por_sid)[:-2048]:
                _sessao_por_sid.pop(_k, None)
        _aberto_em = datetime.now().astimezone().isoformat(timespec="milliseconds")
        try:
            _cad = r.get("cadeira") or cadeira or r.get("nome_canonico", "-")
            _rc = redis.Redis(host=MEM_REDIS_HOST, port=MEM_REDIS_PORT, decode_responses=True)
            _val = json.dumps({"cadeira": _cad, "ordem_id": _oid, "aberto_em": _aberto_em}, ensure_ascii=False)
            _rc.set(f"sessao:{_sessao_id}", _val, ex=172800)
        except Exception as e:  # noqa: BLE001
            print(f"[valkey] FALHOU persistir sessao:{_sessao_id}: {e!r}", file=sys.stderr, flush=True)
        r["ordem_id"] = _oid
        r["sessao_id"] = _sessao_id
        _audit(tool="sessao", evento="sessao_aberta",
               sujeito=r.get("nome_canonico", "-"), ordem_id=_oid, sessao_id=_sessao_id, via="tool")
    _audit(tool="monta_sessao", cadeira=cadeira, atualizar=atualizar,
           resolvida=r.get("nome_canonico"), erro=r.get("erro"),
           chapeu=(r.get("chapeu") or None),
           pergunta=(pergunta or None),
           roteador_via=_rot.get("via"), roteador_slug=_rot.get("slug"),
           dur_ms=round((time.monotonic() - t0) * 1000),
           sessao_id=_sessao_id)
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


# --- Cápsula de verbos: tools derivadas do golden record (spec_capsula-de-verbos) ---
# A porta não tem lista própria de verbos: projeta o whitelist do núcleo via
# `acervo listar ferramental --tools` (§3.2). Uma tool por slug, nome = slug, descrição
# = coluna `descricao`, execução fina de `bin/<verbo> <ato> <args>` sem shell no meio.
# O que a tool acrescenta a `run_command` é SÓ a identidade da sessão (arq:0068 §1):
# `sessao_id` explícito -> `sessao:{id}` em Valkey -> PF_CADEIRA/PF_ORDEM_ID/PF_SESSAO.
# Flag: PF_TOOLS_VERBOS=0 desliga a projeção inteira (rollback: env + restart, sem
# tocar banco nem ADR). Lote 2 (mudança, acesso, infra, solicitação) fica atrás de
# PF_TOOLS_LOTE2=1 até seguranca bater a régua acao/tipo por tool (§3.6, §8).
# Geração na subida: verbo novo = `systemctl --user restart ops-mcp` (por-chamada
# fica pro teste de superfície, §3.2/§7.3).
TOOLS_VERBOS = os.environ.get("PF_TOOLS_VERBOS", "1") != "0"
TOOLS_LOTE2 = os.environ.get("PF_TOOLS_LOTE2", "0") == "1"
# Quem é lote 2 NÃO mora aqui: é o marcador `lote:2` na linha do slug em
# abertura/oficio-ferramental.md, que `acervo listar ferramental --tools` projeta em `lote`.


def _sessao_resolve(sessao_id: str | None) -> dict:
    """cadeira/ordem da sessão: parâmetro -> join por conexão -> nada (§3.5)."""
    sid_conexao = _sessao_atual()
    if not sessao_id:
        sessao_id = _sessao_por_sid.get(sid_conexao) or None
    out = {"sessao_id": sessao_id or "-", "ordem_id": _ordem_por_sid.get(sid_conexao, "-"),
           "cadeira": ""}
    if not sessao_id:
        return out
    try:
        _rc = redis.Redis(host=MEM_REDIS_HOST, port=MEM_REDIS_PORT, decode_responses=True)
        raw = _rc.get(f"sessao:{sessao_id}")
        if raw:
            d = json.loads(raw)
            out["cadeira"] = d.get("cadeira") or ""
            out["ordem_id"] = d.get("ordem_id") or out["ordem_id"]
    except Exception as e:  # noqa: BLE001
        print(f"[valkey] sessao:{sessao_id} nao resolvida: {e!r}", file=sys.stderr, flush=True)
    return out


def _run_verbo_blocking(argv: list, stdin: str | None, timeout: int, ident: dict) -> dict:
    env = {**_env_subprocesso(), "PF_SESSAO": ident["sessao_id"], "PF_ORDEM_ID": ident["ordem_id"],
           "PF_CONTA": OPS_USER}
    if ident["cadeira"]:
        env["PF_CADEIRA"] = ident["cadeira"]
    try:
        p = subprocess.Popen(argv, cwd=RAIZ, env=env,
                             stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    except OSError as e:
        return {"erro": str(e), "cwd": str(RAIZ)}
    try:
        stdout, stderr = p.communicate(input=(stdin.encode() if stdin is not None else None),
                                       timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait()
        return {"erro": f"timeout ({timeout}s) — grupo de processo morto", "cwd": str(RAIZ)}
    return {"exit_code": p.returncode, "stdout": _cap(stdout),
            "stderr": _cap(stderr), "cwd": str(RAIZ)}


def _faz_tool_verbo(slug: str, binario: str, descricao: str):
    async def _tool(ato: str = "", args: list[str] | None = None, stdin: str | None = None,
                    sessao_id: str | None = None, timeout: int = 120) -> dict:
        args = list(args or [])
        linha = " ".join([slug] + ([ato] if ato else []) + args)
        # Lote 1: mesma decisão do fallback (acao/tipo de run_command), auditada pelo
        # slug. acao/tipo POR tool é a régua de lote 2 (seguranca).
        negado = _autoriza(slug, "run_command", "comando", linha, DOM_RUNTIME)
        if negado:
            return negado
        timeout = max(1, min(timeout, 600))
        ident = _sessao_resolve(sessao_id)  # aqui: dentro da task da tool (#2911)
        argv = [binario] + ([ato] if ato else []) + args
        t0 = time.monotonic()
        r = await anyio.to_thread.run_sync(_run_verbo_blocking, argv, stdin, timeout, ident)
        _audit(tool=slug, ato=ato or None, args=" ".join(args)[:CMD_CAP],
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
               ordem_id=ident["ordem_id"], exit_code=r.get("exit_code"), erro=r.get("erro"),
               bytes_stdout=r.get("stdout", {}).get("bytes_total"),
               dur_ms=round((time.monotonic() - t0) * 1000))
        return r
    _tool.__name__ = slug.replace("-", "_")
    _tool.__doc__ = descricao
    return _tool


def _gera_tools_verbos() -> list:
    """Lê a projeção do catálogo. Falha = zero tools derivadas e aviso; nunca aborta."""
    if not TOOLS_VERBOS or not PERSONAS.is_dir():
        return []
    try:
        cp = subprocess.run(["acervo", "listar", "ferramental", "--tools"],
                            env=_env_subprocesso(),  # projecao nao tem sujeito: nenhuma cadeira chumbada
                            capture_output=True, text=True, timeout=30, cwd=RAIZ)
    except Exception as e:  # noqa: BLE001
        print(f"[capsula] gerador falhou: {e!r} — sem tools derivadas", file=sys.stderr, flush=True)
        return []
    if cp.stderr.strip():
        print(f"[capsula] {cp.stderr.strip()}", file=sys.stderr, flush=True)
    if cp.returncode != 0:
        print(f"[capsula] gerador exit {cp.returncode} — sem tools derivadas", file=sys.stderr, flush=True)
        return []
    try:
        itens = json.loads(cp.stdout)
    except ValueError as e:
        print(f"[capsula] JSON do gerador invalido: {e!r}", file=sys.stderr, flush=True)
        return []
    servidas, retidas = [], []
    for i in itens:
        slug = i["tool"]
        if int(i.get("lote") or 1) >= 2 and not TOOLS_LOTE2:
            retidas.append(slug)
            continue
        # Descrição = coluna `descricao` do golden record, SEM edição (spec §3.1): o
        # contrato comum (ato, args, sessao_id) está no ofício, uma vez, não 17.
        desc = i.get("descricao") or ""
        mcp.tool(name=slug, description=desc)(_faz_tool_verbo(slug, i["binario"], desc))
        servidas.append(slug)
    print(f"[capsula] tools derivadas servidas ({len(servidas)}): {' '.join(servidas)}"
          + (f" · lote 2 retido: {' '.join(retidas)}" if retidas else ""),
          file=sys.stderr, flush=True)
    return servidas


TOOLS_DERIVADAS = _gera_tools_verbos()


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


# Nada sob /.well-known é segredo, e negar ali quebra a descoberta do cliente MCP
# antes de qualquer login. /authorize e /token só encaminham para o realm.
ABERTAS = ("/health", "/authorize", "/token")


class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        caminho = request.url.path.rstrip("/")
        if caminho in ABERTAS or caminho.startswith("/.well-known/"):
            return await call_next(request)

        header = request.headers.get("authorization", "")
        ident, via = _sujeito_do_jwt(header, auditor=_audit, jwks_url=OIDC_JWKS_URL,
                                    audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER), "oidc"
        if not ident and _estatico_vigente() and _token_ok(header, OPS_AUTH_TOKEN):
            ident, via = {"sujeito": OPS_USER, "sub": "-", "username": OPS_USER,
                          "azp": "token-estatico", "sid": "-", "jti": "-"}, "estatico"
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


async def _as_metadata(_req):
    """Authorization server metadata (RFC 8414) espelhada.

    O cliente MCP procura isto no próprio servidor de recurso antes de olhar o PRM.
    Os endpoints apontam para o realm: quem lê esta resposta fala direto com o
    Keycloak, sem passar por aqui."""
    oi = OIDC_ISSUER
    return JSONResponse({
        "issuer": oi,
        "authorization_endpoint": f"{oi}/protocol/openid-connect/auth",
        "token_endpoint": f"{oi}/protocol/openid-connect/token",
        "jwks_uri": f"{oi}/protocol/openid-connect/certs",
        "userinfo_endpoint": f"{oi}/protocol/openid-connect/userinfo",
        "revocation_endpoint": f"{oi}/protocol/openid-connect/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post",
                                                  "client_secret_basic"],
        "scopes_supported": ["openid", "profile", "email", "offline_access"],
    })


async def _authorize(req):
    """Fallback legado: cliente que não leu a metadata bate aqui. 302 para o realm,
    query preservada — o PKCE e o state seguem intactos."""
    q = req.url.query
    destino = f"{OIDC_ISSUER}/protocol/openid-connect/auth" + (f"?{q}" if q else "")
    return RedirectResponse(destino, status_code=302)


async def _token(req):
    """307 e não 302: o método e o corpo do POST precisam sobreviver ao redirecionamento."""
    q = req.url.query
    destino = f"{OIDC_ISSUER}/protocol/openid-connect/token" + (f"?{q}" if q else "")
    return RedirectResponse(destino, status_code=307)


# --- Canal mediado da colaboracao externa (card 344, seg:0009) ---------------
# O Jaiminho fala com claudinho-IA DENTRO da malha msg — mesmo broker, mesmo
# envelope, mesma retencao —, mas nao recebe credencial do Valkey e nao alcanca
# tool nenhuma. Estas duas rotas sao a superficie inteira dele: o PEP valida o JWT,
# consulta o PDP e escreve na caixa EM NOME dele. Quem obedece e este servidor;
# o broker nunca ve o externo.
# Caminho proprio, nao derivado de PF_HARNESS: uma instancia que aponte PF_HARNESS
# para um recorte do repo (persona e politica, sem `bin`) ficava sem o modulo da
# fila e devolvia 500 sem dizer por que. Medido no ensaio de 13/08/2026.
FILA_BIN = Path(os.environ.get("PF_BIN", RAIZ / "platafirma-harness/bin"))


def _fila_mod():
    """Levanta ModuleNotFoundError com o caminho tentado — quem chama devolve 503
    nomeando o defeito, em vez de 500 nomeando nada."""
    if str(FILA_BIN) not in sys.path:
        sys.path.insert(0, str(FILA_BIN))
    try:
        import fila_streams
    except ImportError as e:
        raise ModuleNotFoundError(
            f"modulo da fila nao encontrado em {FILA_BIN} — aponte PF_BIN") from e
    return fila_streams


def _ident_req(req) -> dict:
    """Mesma cadeia do middleware: JWT do realm, ou rota de emergencia enquanto vigente."""
    header = req.headers.get("authorization", "")
    ident = _sujeito_do_jwt(header, auditor=_audit, jwks_url=OIDC_JWKS_URL,
                            audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER)
    if not ident and _estatico_vigente() and _token_ok(header, OPS_AUTH_TOKEN):
        ident = {"sujeito": OPS_USER, "sub": "-", "username": OPS_USER,
                 "azp": "token-estatico", "sid": "-", "jti": "-"}
    return ident


# Catalogo de atos candidatos do externo. Nao e a lista do que ele PODE: e a lista
# do que existe para ser perguntado ao PDP. O que entra no pacote sai da decisao,
# sujeito a sujeito, na hora — por isso conceder por merge no PAP muda o manifesto
# sem tocar em documentacao.
ATOS_EXTERNOS = (
    ("msg_ler", "mensagem", DOM_MENSAGERIA, "caixa:{eu}",
     "GET /msg", "le a propria caixa; so o que chegou desde a ultima leitura"),
    ("msg_enviar", "mensagem", DOM_MENSAGERIA, "caixa:ia",
     "POST /msg", "manda recado para ia (Elias Elefante)"),
    ("rag_buscar", "acervo", "plataforma-acervo", "acervo:firma/*",
     "-", "leitura do acervo de trabalho — concedida em 15/08/2026; sem rota que a sirva"),
)


def _acoes_permitidas(quem: str, est: dict) -> list:
    from pdp import Recurso, Sujeito, decide
    atrib = (est["sujeitos"] or {}).get(quem) or {}
    s = Sujeito(id=quem, natureza=atrib.get("natureza"),
                papeis=tuple(atrib.get("papeis") or ()),
                dominios=tuple(atrib.get("dominios") or ()),
                habilitacao=atrib.get("habilitacao", "publico"))
    fora = []
    for acao, tipo, dom, molde, como, oque in ATOS_EXTERNOS:
        alvo = molde.format(eu=quem)
        d = decide(s, acao, Recurso(tipo=tipo, id=alvo, dominio=dom), est["politica"])
        if d.permitido:
            fora.append({"acao": acao, "como": como, "sobre": alvo, "o_que_faz": oque})
    return fora


async def _sessao_abrir(req):
    """Abertura de sessao de quem nao e cadeira. O equivalente de `monta_sessao`,
    pela superficie que o externo alcanca — e com o catalogo de acoes resolvido do
    token, nao escrito a mao (docs/fronteira-do-harness.md)."""
    ident = _ident_req(req)
    quem = ident.get("sujeito", "-")
    est = _carrega_politica()
    if est.get("erro"):
        return JSONResponse({"erro": "politica de acesso indisponivel",
                             "detalhe": est["erro"]}, status_code=503)
    if not (est["sujeitos"] or {}).get(quem):
        _audit(tool="sessao", evento="pep_negou", regra="projecao", sujeito=quem)
        return JSONResponse(
            {"erro": f"sujeito {quem!r} nao tem atributos declarados — nao abre sessao",
             "regra": "projecao"}, status_code=403)

    pac = {"sujeito": quem, "acoes": _acoes_permitidas(quem, est)}

    pf = PERSONAS / quem / "persona.md"
    if pf.is_file():
        pac["persona"] = {"path": str(pf), "content": pf.read_text(encoding="utf-8")}
    else:
        pac["persona"] = {"ausente": True, "path": str(pf),
                          "aviso": "persona ainda nao escrita (RH). Ausencia declarada, "
                                   "nao omissao: opere pelo que o manifesto e a caixa dizem."}

    mf = PF_HARNESS / "abertura/oficio.md"
    pac["manifesto"] = ({"path": str(mf), "content": mf.read_text(encoding="utf-8")}
                        if mf.is_file() else {"ausente": True, "path": str(mf)})

    pac["memoria"] = _memoria(quem)
    try:
        f = _fila_mod()
        rc = f.r_conn()
        f.garante_grupo(rc, quem)
        novas, no_historico = f.conta_novas(rc, quem)
        pac["fila"] = {"caixa": f"caixa:{quem}", "novas": novas,
                       "no_historico": no_historico,
                       "nota": "corpo por GET /msg — abrir sessao nao consome a caixa"}
    except Exception as e:                                  # noqa: BLE001
        pac["fila"] = {"indisponivel": True, "erro": f"{type(e).__name__}: {e}"}

    _sid = _sessao_atual()
    _oid = "o" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    _ordem_por_sid[_sid] = _oid
    if len(_ordem_por_sid) > 4096:            # nao vazar memoria: guarda so as fitas recentes
        for _k in list(_ordem_por_sid)[:-2048]:
            _ordem_por_sid.pop(_k, None)
    pac["ordem_id"] = _oid
    _audit(tool="sessao", evento="sessao_aberta", sujeito=quem, ordem_id=_oid,
           acoes=len(pac["acoes"]), persona_ausente=pac["persona"].get("ausente", False))
    return JSONResponse(pac)


async def _sessao_encerrar(req):
    """Fechamento da fita: a nota que a proxima precisa saber. Substitui, nao acumula
    — mesma classe `mem` da mesa das cadeiras (arq:0041)."""
    ident = _ident_req(req)
    quem = ident.get("sujeito", "-")
    est = _carrega_politica()
    if est.get("erro") or not (est["sujeitos"] or {}).get(quem):
        return JSONResponse({"erro": "sujeito sem atributos declarados"}, status_code=403)
    try:
        corpo = json.loads(await req.body() or b"{}")
    except ValueError:
        return JSONResponse({"erro": "corpo nao e JSON"}, status_code=400)
    nota = (corpo.get("nota") or "").strip()
    if not nota:
        return JSONResponse({"erro": "campo obrigatorio: nota"}, status_code=400)
    r = await anyio.to_thread.run_sync(_anota_mesa, quem, nota)
    # 3 primeiros giros auto-relatados -> sessao.giro (ordem do dono 02/09, #2945).
    # Best-effort: falha aqui nunca derruba o encerramento (a nota da mesa e o ato).
    giro = corpo.get("giro") or []
    if isinstance(giro, list) and giro:
        sid = (corpo.get("sessao_id") or os.environ.get("PF_SESSAO") or "").strip()
        r["giro"] = await anyio.to_thread.run_sync(
            _giro_carrega, sid, quem, corpo.get("chapeu"), giro[:3])
    _audit(tool="sessao", evento="fita_encerrada", sujeito=quem, bytes_nota=len(nota),
           ok=r.get("ok"))
    return JSONResponse(r, status_code=200 if r.get("ok") else 500)


def _anota_mesa(quem: str, nota: str) -> dict:
    """Pelo verbo `mesa`, nunca por cliente redis proprio: segunda implementacao da
    mesma regra diverge em silencio (mesma razao de `_memoria`)."""
    try:
        proc = subprocess.run([str(RAIZ / "bin" / "mesa"), "anota", quem],
                              input=nota, capture_output=True, text=True, timeout=15,
                              env={**_env_subprocesso(), "PF_CADEIRA": quem})
        if proc.returncode == 0:
            return {"ok": True, "slot": quem, "saida": proc.stdout.strip()}
        return {"ok": False, "erro": (proc.stderr or proc.stdout).strip()[:300]}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


def _giro_carrega(sessao_id: str, cadeira: str, chapeu, giro: list) -> dict:
    """Carrega os 3 primeiros giros auto-relatados em sessao.giro pelo verbo
    bin/_giro-carga.py — nunca cliente de banco proprio (ops-mcp roda em .venv-ops,
    sem driver de banco; mesma razao de _anota_mesa)."""
    if not sessao_id:
        return {"ok": False, "erro": "sem sessao_id"}
    payload = json.dumps({"sessao_id": sessao_id, "cadeira": cadeira,
                          "chapeu": chapeu, "giro": giro})
    try:
        proc = subprocess.run([str(RAIZ / "bin" / "_giro-carga.py")],
                              input=payload, capture_output=True, text=True,
                              timeout=15, env={**_env_subprocesso()})
        try:
            return json.loads(proc.stdout or "{}")
        except ValueError:
            return {"ok": False, "erro": (proc.stderr or proc.stdout).strip()[:300]}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


async def _msg_enviar(req):
    ident = _ident_req(req)
    try:
        corpo = json.loads(await req.body() or b"{}")
    except ValueError:
        return JSONResponse({"erro": "corpo nao e JSON"}, status_code=400)
    para = (corpo.get("para") or "").strip()
    tipo = (corpo.get("tipo") or "").strip()
    if not para or not tipo or not (corpo.get("corpo") or "").strip():
        return JSONResponse(
            {"erro": "campos obrigatorios: para, tipo, assunto, corpo"}, status_code=400)

    negado = _autoriza("msg_enviar", "msg_enviar", "mensagem", f"caixa:{para}",
                       DOM_MENSAGERIA, ident=ident)
    if negado:
        return JSONResponse(negado, status_code=403)

    try:
        f = _fila_mod()
    except ModuleNotFoundError as e:
        _audit(tool="msg_enviar", evento="malha_indisponivel", motivo=str(e))
        return JSONResponse({"erro": "malha msg indisponivel", "detalhe": str(e)},
                            status_code=503)
    if tipo not in f.TIPOS_VALIDOS:
        return JSONResponse({"erro": f"tipo invalido: {tipo}",
                             "validos": sorted(f.TIPOS_VALIDOS)}, status_code=400)
    de = ident.get("sujeito", "-")
    rc = f.r_conn()
    msgid = f.gerar_msgid(de, {m["msgid"] for m in f.frias(rc, para)})
    rc.xadd(f.stream_key(para), {
        "id": msgid, "de": de, "tipo": tipo,
        "assunto": corpo.get("assunto", ""), "ref": corpo.get("ref", ""),
        "responde": corpo.get("responde", ""), "corpo": corpo["corpo"],
    })
    _audit(tool="msg_enviar", evento="msg_enviada", sujeito=de, para=para,
           tipo=tipo, msgid=msgid)
    return JSONResponse({"ok": True, "msgid": msgid, "caixa": f"caixa:{para}"})


async def _msg_ler(req):
    """Le a PROPRIA caixa do chamador. Nao ha parametro de caixa por desenho: caixa
    alheia nao se le por engano de query string."""
    ident = _ident_req(req)
    quem = ident.get("sujeito", "-")
    negado = _autoriza("msg_ler", "msg_ler", "mensagem", f"caixa:{quem}",
                       DOM_MENSAGERIA, ident=ident)
    if negado:
        return JSONResponse(negado, status_code=403)
    try:
        f = _fila_mod()
    except ModuleNotFoundError as e:
        _audit(tool="msg_ler", evento="malha_indisponivel", motivo=str(e))
        return JSONResponse({"erro": "malha msg indisponivel", "detalhe": str(e)},
                            status_code=503)
    rc = f.r_conn()
    f.garante_grupo(rc, quem)
    msgs = f.novas(rc, quem)
    _audit(tool="msg_ler", evento="msg_lida", sujeito=quem, quantas=len(msgs))
    return JSONResponse({"caixa": f"caixa:{quem}", "novas": len(msgs),
                         "mensagens": msgs})


app = mcp.streamable_http_app()
app.router.routes.append(Route("/health", _health))
app.router.routes.append(Route("/.well-known/oauth-authorization-server", _as_metadata))
app.router.routes.append(Route("/.well-known/oauth-authorization-server/mcp", _as_metadata))
app.router.routes.append(Route("/.well-known/openid-configuration", _as_metadata))
app.router.routes.append(Route("/authorize", _authorize))
app.router.routes.append(Route("/token", _token, methods=["POST", "GET"]))
app.router.routes.append(Route("/.well-known/oauth-protected-resource", _prm))
app.router.routes.append(Route("/.well-known/oauth-protected-resource/mcp", _prm))
app.router.routes.append(Route("/sessao", _sessao_abrir))
app.router.routes.append(Route("/sessao/encerrar", _sessao_encerrar, methods=["POST"]))
app.router.routes.append(Route("/msg", _msg_enviar, methods=["POST"]))
app.router.routes.append(Route("/msg", _msg_ler, methods=["GET"]))
app.add_middleware(BearerAuth)
