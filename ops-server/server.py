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
OPS_NAME, OPS_USER, PLATAFIRMA_INSTANCIA e OPS_AUTH_TOKEN separam as instâncias; o default é a
instância histórica (claudinho-mcp sob claudinho, instância /srv/platafirma/casa).
OPS_USER, o log e o bin servido entram nas descrições das tools em tempo de registro —
sem isso a instância nova se descreve com o usuário e os caminhos da instância velha, e
o cliente age sobre um caminho que não existe.

RAÍZES (card #3010): código servido vem da release (PF_RELEASE_RAIZ, default
/opt/platafirma); estado, log e rascunho vêm da instância (PLATAFIRMA_INSTANCIA, default
/srv/platafirma/casa). A bancada — onde se escreve código — não é raiz de produção: só
entra quando a chamada pede caminho relativo, e sem bancada declarada a porta recusa
esse pedido em vez de adivinhar lugar.

AUDITORIA: toda invocação de tool grava uma linha JSONL em PLATAFIRMA_INSTANCIA/var/log/ops/, com
retenção declarada (OPS_LOG_RETENCAO_DIAS, podada por cron, não por este processo). O
campo `sessao` agrupa chamadas de uma mesma sessão de cliente; `sujeito` e `azp` vêm
do JWT e registram QUEM chamou e por qual cliente OAuth. Atribuição de PERSONA segue
dívida: as cadeiras compartilham um client (`claudinho-mcp`), então o log identifica o
humano e o cliente, não a cadeira — projetar a cadeira no token é o card #436.

PATH DO SUBPROCESSO: montado explicitamente, porque `bash -c` não-login não lê .bashrc
nem .profile — sem isto, o bin da release e ~/.local/bin existem no disco e
é invisível para quem chama a tool. O env do subprocesso também é depurado dos segredos
da instância: um comando qualquer não deve conseguir ecoar o token que o autorizou.
"""
import hashlib
import hmac
import json
import logging
import os
import uuid
import re
import shlex
import signal
import resource
import subprocess
import tempfile
import sys
import time
from contextvars import ContextVar
from datetime import date, datetime
from pathlib import Path, PurePosixPath

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
OPS_AUTH_TOKEN = os.environ.get("OPS_AUTH_TOKEN", "")
MEM_REDIS_HOST = os.environ.get("MEM_REDIS_HOST", "127.0.0.1")
MEM_REDIS_PORT = int(os.environ.get("MEM_REDIS_PORT", "6380"))

# RAIZES (card #3010). Produção mora em duas raízes e só nelas: a release (código
# imutável, /opt/platafirma) e a instância (segredos, dados, estado, logs,
# /srv/platafirma/casa). Todo caminho abaixo deriva de uma das duas; a bancada (onde se
# escreve código) só é lida quando a chamada a nomeia — nunca no arranque. A porta sobe
# sem bancada declarada e sem criar diretório nenhum nela.
_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import raizes                                                 # noqa: E402

INSTANCIA = raizes.instancia()
# Cwd de quem não nomeia um: a casa da conta do processo. Não é raiz de produção — é o
# lugar neutro onde um comando sem endereço não escreve em árvore de ninguém.
CASA = Path(os.path.expanduser("~"))

PF_HARNESS = Path(os.environ.get("PF_HARNESS", raizes.release() / "harness"))
# Verbo servido: bin/ da release no ar. Override por PF_BIN (teste, ensaio).
BIN_VERBOS = Path(os.environ.get("PF_BIN", raizes.release() / "harness" / "bin"))
# CODIGO do PDP (pdp.py, identidade.py, pep.py) mora no repo — versionado, importavel.
PDP_CODE_DIR = PF_HARNESS / "politica-acesso"
if str(PDP_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(PDP_CODE_DIR))
# DADOS de identidade (politica/sujeitos/superficies.yaml) moram FORA do working tree
# de fabrica (incidente #2956, minuta arq 0015 perna 1, card #3014: release em current).
# Override por PDP_DIR; default e a release (arq:0102 D6), sem fallback: politica que
# falta nega por default, nunca cai numa copia de outro lugar.
PDP_DIR = Path(os.environ.get("PDP_DIR", raizes.release() / "politica-acesso"))
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

LOG_DIR = Path(os.environ.get("OPS_LOG_DIR", INSTANCIA / "var/log/ops"))
CMD_CAP = 2_000        # teto do comando gravado na auditoria
LINHA_CAP = 8_000      # teto da linha JSONL

# Segredos da instância não descem para o subprocesso.
ENV_OCULTO = ("OPS_AUTH_TOKEN", "TUNNEL_TOKEN")

_sessao: ContextVar[str] = ContextVar("sessao", default="-")

# ENTIDADE-SESSAO UNICA (arq:0101 §1, emenda ao arq:0091). Uma sessao, um `sessao_id`,
# cunhado UMA vez por `monta_sessao` e carregado PELA FITA em cada chamada. A porta nao
# infere sessao na abertura.
#
# Antes disto a entidade nascia em quatro pontos com tres identificadores (monta_sessao
# cunhava uuid; /sessao cunhava so ordem_id; o sid de conexao; _giro-carga.py cunhava um
# SEGUNDO uuid no encerrar) — e o ledger de dedup precisa de chave estavel, que nao havia.
#
# `ordem_id` e o `sid` de conexao sao ATRIBUTOS dentro de `sessao:{id}`, nunca identidade.
# Os dicionarios de RAM (_ordem_por_sid, _sessao_por_sid) sairam: o join conexao->sessao
# vive no msg-mem (`sessao:{id}`), e por isso sobrevive ao restart da porta — fita viva
# atravessa restart, e um join em RAM reabriria sessao nova do outro lado.
TTL_SESSAO_S = 172800          # 48 h — o mesmo de `sessao:{id}`, `ledger:` e `giro:`
_ULTIMA_SESSAO_ID: str | None = None


def _sessao_viva() -> str | None:
    """Busca o sessao_id vivo da porta: ContextVar, chave Redis 'sessao:viva', ou última montada."""
    try:
        sid = _sessao.get()
        if sid and sid != "-":
            return sid
    except Exception:
        pass
    try:
        sid = _rc().get("sessao:viva")
        if sid:
            return str(sid)
    except Exception:
        pass
    return _ULTIMA_SESSAO_ID


def _rc():
    """Cliente do msg-mem. Uma funcao, nao um cliente por chamador: connect_timeout
    curto porque banco mudo nunca pode segurar a porta."""
    return redis.Redis(host=MEM_REDIS_HOST, port=MEM_REDIS_PORT, decode_responses=True,
                       socket_connect_timeout=2, socket_timeout=3)


def _uuid_valido(bruto: str) -> str | None:
    """Normaliza para RFC-4122 (arq:0091 §4) — 32 hex sem hifen entra e sai com hifen.

    O formato voltou a ser o do 0091 porque a fita PORTA este valor: identificador que
    muda de forma entre quem cunha e quem devolve nao e o mesmo identificador."""
    try:
        return str(uuid.UUID(str(bruto).strip()))
    except (ValueError, AttributeError, TypeError):
        return None


def _extrai_sessao_id(texto: str) -> str | None:
    """Extrai sessao_id de uma saída de texto ou JSON."""
    if not texto:
        return None
    try:
        dados = json.loads(texto)
        if isinstance(dados, dict):
            sid = dados.get("sessao_id") or (dados.get("sessao") or {}).get("sessao_id")
            val = _uuid_valido(sid)
            if val:
                return val
    except Exception:
        pass
    m = re.search(r'"sessao_id"\s*:\s*"([0-9a-fA-F-]{32,36})"', texto)
    if not m:
        m = re.search(r'\bsessao_id[:=]\s*([0-9a-fA-F-]{32,36})\b', texto)
    if not m:
        m = re.search(r'\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b', texto, re.I)
    if m:
        return _uuid_valido(m.group(1))
    return None


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


# --- PODA (arq:0101 §3) — a régua mora em poda.py; aqui fica só a costura ------
# `PF_PODA=0` + restart reverte tudo abaixo sem tocar banco, ADR nem catálogo: é a
# reversão declarada da ADR, e por isso é lida em runtime, não capturada na subida.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import poda as _poda                                          # noqa: E402
import lote as _lote                                          # noqa: E402  (card:3149 passo 7)


def _poda_ligada() -> bool:
    return os.environ.get("PF_PODA", "1") != "0"


# R4 — perfil por verbo, lido do CABEÇALHO do próprio verbo (`# forma:`, `# cauda:`),
# mesmo parser por chave da spec cápsula §3.3. Sem tabela paralela: tabela paralela ao
# cabeçalho é a segunda fonte que diverge em silêncio. Ausente = listagem/cauda:nao,
# que é exatamente o comportamento de hoje — verbo que não declara nada não muda.
_PERFIS: dict[str, dict] = {}
_RE_CHAVE = re.compile(r"^#\s*(forma|cauda|poda)\s*:\s*(\S+)", re.MULTILINE)
FORMAS = ("json", "listagem", "relatorio", "log")


def _perfil_verbo(slug: str, binario: str) -> dict:
    if slug in _PERFIS:
        return _PERFIS[slug]
    perfil = {"forma": "listagem", "cauda": False, "poda": "inteira", "poda_atos": ()}
    try:
        with open(binario, encoding="utf-8", errors="replace") as fh:
            cab = "".join(next(fh, "") for _ in range(40))
        for chave, valor in _RE_CHAVE.findall(cab):
            if chave == "forma" and valor in FORMAS:
                perfil["forma"] = valor
            elif chave == "cauda":
                perfil["cauda"] = valor.lower() in ("sim", "1", "true")
            elif chave == "poda":
                regime, _, atos = valor.partition("@")
                if regime.lower() == "cosmetica":
                    perfil["poda"] = "cosmetica"
                    perfil["poda_atos"] = tuple(a for a in atos.split(",") if a)
    except OSError:
        pass
    _PERFIS[slug] = perfil
    return perfil


def _cosmetica(perfil: dict, ato: str | None) -> bool:
    """`# poda: cosmetica[@ato,ato]` — terceiro eixo do R4, ao lado de forma e cauda.

    O escopo por ato existe porque verbo MISTO não cabe num perfil só: `acervo casa` é
    recuperação semântica e `acervo listar` é listagem estruturada, e listagem sem teto
    derrama a fita. Sem `@`, o verbo inteiro é semântico — caso de `descobrir`, cujo ato
    é o próprio assunto consultado, e não haveria o que enumerar.
    """
    if perfil.get("poda") != "cosmetica":
        return False
    atos = perfil.get("poda_atos") or ()
    return not atos or (ato or "") in atos


def _argv_verbo(binario: str, ato: str, args: list) -> list:
    """O argv que vai ao execve de uma tool de verbo: `ato` vazio some, nao vira `''`."""
    return [binario] + ([ato] if ato else []) + list(args or [])


def _ato_efetivo(argv: list) -> str | None:
    """O ato que o escopo `cosmetica@ato` enxerga e o do argv, nao o do parametro `ato`.

    O cliente MCP chama o mesmo execve de duas formas: `ato="rag", args=["buscar", ...]`
    e `ato="", args=["rag", "buscar", ...]`. Medido em 18/09: decidir o perfil pelo
    parametro tirava o regime cosmetico da segunda forma, a janela de linha longa comia
    o JSON de linha unica do `motor rag buscar` (13 kB -> 289 bytes) e a cadeira ficava
    sem o corpo dos trechos — o caso que o #3022 fechou, reaberto pela forma da chamada.
    `run_command` ja decidia pelo argv; agora as quatro saidas decidem igual.
    """
    return argv[1] if len(argv) > 1 else None


# ALCA DE CONSTITUICAO (ordem do dono, 20/09/2026, insumo Hermes / arq:0061 par.5): estas
# nunca viram ponteiro nem aviso em Ledger.olha(), no caminho do verbo -- mesma garantia
# que _delta_pecas ja da na abertura (balde 1, #3067). alca aqui e a linha completa
# (tool + ato + args); o ato e o segundo token.
_ATOS_CONSTITUTIVOS = {
    ("persona", "conduta"), ("persona", "ler"),
    ("mesa", "caderno"), ("expediente", "montar"),
}


def _eh_constitutiva(tool: str, alca: str) -> bool:
    partes = (alca or "").split()
    ato = partes[1] if len(partes) > 1 else None
    return (tool, ato) in _ATOS_CONSTITUTIVOS


def _serve(r: dict, *, tool: str, alca: str, ident: dict, cauda: bool = False,
           cosmetica: bool = False) -> dict:
    """R8 — o único caminho por onde retorno de tool sai desta porta.

    Erro e `exit != 0` passam intocados (invariante iii): o diagnóstico inteiro vale
    mais que o byte poupado. O resto lava, deduplica contra o ledger da sessão, corta
    com alça e sai com o aviso em banda nos dois níveis (campo `poda` para o log e o
    ensaio; `poda_aviso` para quem lê o retorno).

    `cosmetica` vem do cabeçalho do verbo (`_cosmetica`) e vale só para retorno de
    recuperação semântica: lava o cosmético, deduplica igual, e NUNCA corta miolo.
    """
    if not isinstance(r, dict) or not _poda_ligada() or _poda.intocavel(r):
        return r
    sessao_id = ident.get("sessao_id") or "-"
    try:
        ledger = _poda.Ledger(_rc(), sessao_id, TTL_SESSAO_S)
        giro = ledger.giro()
    except Exception:                                         # noqa: BLE001
        ledger, giro = None, 0
    metas = []
    for campo, sub in (("stdout", "texto"), ("content", None)):
        alvo = r.get(campo)
        texto = (alvo or {}).get(sub) if sub else alvo
        if not isinstance(texto, str) or not texto:
            continue
        cap_efetivo = max(CAP, len(texto.encode("utf-8", "replace"))) if tool == "read_file" else CAP
        servido, meta = _poda.poda_texto(
            texto, cap=cap_efetivo, cauda=cauda, alca=f"{tool}:{alca}", sessao_id=sessao_id,
            giro=giro, tool=tool, ledger=ledger, cosmetica=cosmetica,
            constitutiva=_eh_constitutiva(tool, alca),
            nome_derrame=f"g{giro:05d}-{campo}.txt")
        if sub:
            r[campo] = {**alvo, sub: servido}
        else:
            r[campo] = servido
        metas.append(meta)
    if not metas:
        return r
    meta = metas[0] if len(metas) == 1 else {"campos": metas, **metas[0]}
    r = _poda.enxuga_envelope(r)
    r["poda"] = meta
    humana = _poda.linha_humana(meta)
    if humana:
        r["poda_aviso"] = humana
    return r


def _eh_balde_2(e: dict) -> bool:
    """Balde 2 da spec_contexto-na-porta: acervo-consultado e corpo de caderno.
    Só esses dois viram ponteiro a partir do 2º giro nesta rodada."""
    pid = e.get("peca") or ""
    ref = e.get("ref") or ""
    if pid == "acervo-consultado":
        return True
    if pid in ("caderno", "corpo-caderno", "caderno-corpo", "caderno-chapeu", "corpo de caderno"):
        return True
    if pid == "cadernos":
        if "--chapeu" in ref or (ref.startswith("verbo:mesa caderno") and ref.strip() != "verbo:mesa caderno"):
            return True
        return False
    return False



def _sha_publicado(pid: str, cadeira: str) -> str | None:
    """Busca o sha do arquivo na morada publicada (dono.md, persona.md)."""
    import os
    morada = os.environ.get("PF_ABERTURA_DIR", "/srv/platafirma/casa/var/abertura-publicada")
    if pid == "conduta":
        caminho = os.path.join(morada, "current", "abertura", "dono.md")
    elif pid == "persona":
        if not cadeira or cadeira == "-":
            return None
        caminho = os.path.join(morada, "current", "abertura", cadeira, "persona.md")
    else:
        return None
    if not os.path.isfile(caminho):
        return None
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
        return _poda.sha_servido(texto)
    except Exception:
        return None

def _falha_sha(e: dict, r: dict, pid: str, sha_declarado: str, conteudo: str) -> bool:
    """Recomputa o sha do que veio e compara; serve fail-closed em caso de divergência."""
    if conteudo and isinstance(conteudo, str):
        
        sha_calc = _poda.sha_servido(conteudo)
        if sha_declarado and sha_declarado != sha_calc:
            e["conteudo"] = None
            e["frescor"] = "indisponivel"
            e["motivo"] = f"sha divergente: declarado {sha_declarado}, calculado {sha_calc} (fail-closed)"
            e["recusa"] = "fail-closed"
            r["erro"] = f"sha que não bate na peça `{pid}`: declarado {sha_declarado}, calculado {sha_calc} (recusa fail-closed)"
            r["regra"] = "sha"
            r.setdefault("avisos", []).append(f"peça `{pid}`: sha que não bate — recusa fail-closed")
            return True
    return False

def _delta_pecas(r: dict, sessao_id: str) -> dict:
    """R2 na abertura — dedup por baldes (spec_contexto-na-porta §4, §5).

    Balde 1: persona, conduta -> NUNCA ponteiro (#3067).
    Balde 2: acervo-consultado, corpo de caderno -> vira ponteiro (ref, sha) do 2º giro em diante.
    Balde 3: mesa do chapéu ativo, alias-cadeiras, índice de cadernos, turno, erro -> SEMPRE inteiro.
    Conferência de sha: recomputa sha e recusa fail-closed se não bater.
    """
    pecas = r.get("pecas")

    if not _poda_ligada() or not isinstance(pecas, list) or not sessao_id or sessao_id == "-":
        return {"bytes_servidos": None}
    try:
        rc, chave = _rc(), f"ledger:{sessao_id}"
        vistos = rc.hgetall(chave) or {}
    except Exception:                                         # noqa: BLE001
        return {"bytes_servidos": None, "ledger": "indisponivel"}
    servidos = deduplicadas = 0
    novos = {}
    for e in pecas:
        sha, pid = e.get("sha"), e.get("peca")
        conteudo = e.get("conteudo")
        if not sha or not pid:
            continue
        if pid in ("persona", "conduta"):
            if _superficie() == "claude.ai":
                if _falha_sha(e, r, pid, sha, conteudo):
                    continue
                
                cadeira = r.get("nome_canonico", "")
                sha_pub = _sha_publicado(pid, cadeira)

                
                if sha_pub:
                    bytes_omitidos = len(conteudo.encode()) if isinstance(conteudo, str) else 0
                    e["regime"] = "ponteiro"
                    e["conteudo"] = None
                    e["tokens"] = 0
                    e["poda"] = {"ato": "monta_sessao", "modo": "ponteiro", "sha": sha_pub,
                                 "ref": e.get("ref"), "bytes_omitidos": bytes_omitidos}
                    deduplicadas += 1
                    continue
                
                # Se não temos o sha publicado (arquivo ausente ou cadeira irresolvida),
                # degradamos de forma segura servindo a peça inteira. Fall-through para o comportamento padrão.
            
            # Balde 1 (outras superfícies): prefixo estável é cache, nunca ponteiro (#3067).
            servidos += len(conteudo.encode()) if isinstance(conteudo, str) else 0
            continue
        if not _eh_balde_2(e):
            # Balde 3 (SEMPRE inteiro, nunca ponteiro): mesa, alias-cadeiras, índice de cadernos, etc.
            servidos += len(conteudo.encode()) if isinstance(conteudo, str) else 0
            continue

        # Balde 2: acervo-consultado e corpo de caderno
        # Conferência do sha de graça: recomputa o sha do que veio e compara; serve fail-closed
        if _falha_sha(e, r, pid, sha, conteudo):
            continue

        alca = f"peca:{pid}"
        antes = vistos.get(alca)
        if antes and isinstance(antes, (str, bytes)):
            try:
                d = json.loads(antes)
            except ValueError:
                d = {}
            if d.get("sha") == sha:
                # Vira ponteiro (par ref, sha) do 2º giro em diante
                bytes_omitidos = len(conteudo.encode()) if isinstance(conteudo, str) else 0
                e["regime"] = "ponteiro"
                e["conteudo"] = None
                e["tokens"] = 0
                e["poda"] = {"ato": "monta_sessao", "modo": "ponteiro", "sha": sha,
                             "ref": e.get("ref"), "bytes_omitidos": bytes_omitidos}
                deduplicadas += 1
                continue
        novos[alca] = json.dumps({"sha": sha, "ref": e.get("ref"), "giro": 0, "tool": "monta_sessao"})
        servidos += len(conteudo.encode()) if isinstance(conteudo, str) else 0
    try:
        if novos:
            rc.hset(chave, mapping=novos)
        rc.expire(chave, TTL_SESSAO_S)
    except Exception:                                         # noqa: BLE001
        pass
    if deduplicadas:
        r.setdefault("avisos", []).append(
            f"{deduplicadas} peça(s) já servidas nesta sessão vieram como ponteiro (arq:0101 R2)")
    return {"bytes_servidos": servidos, "pecas_dedup": deduplicadas or None}


def _campos_poda(r: dict) -> dict:
    """O que o ops log grava por retorno (arq:0101 §4): bytes SERVIDOS e sha do servido.

    A porta gravava bytes PRODUZIDOS e nenhum hash — por isso o dup de conteúdo entre
    chamadas nunca esteve medido, e a perícia teve de estimá-lo.
    """
    p = (r or {}).get("poda") or {}
    if p:
        return {"bytes_servidos": p.get("bytes_servidos"), "sha": p.get("sha"),
                "poda_modo": p.get("modo"), "ledger": p.get("ledger")}
    # Retorno que a poda nao tocou — erro e exit != 0 saem inteiros (invariante iii) —
    # tambem OCUPA contexto, e ficava com `bytes_servidos: null`. Efeito medido em
    # 11/09: todo dia do log fecha com "0 KB em giro que falhou", como se tateio fosse
    # de graca. A invariante continua: nao se corta o diagnostico; passa-se a CONTA-LO,
    # com `poda_modo: intocavel` dizendo que nao houve corte.
    return {"bytes_servidos": _bytes_crus(r), "sha": None,
            "poda_modo": "intocavel", "ledger": None}


def _bytes_crus(r: dict) -> int | None:
    """Tamanho do que saiu, nos mesmos campos que a poda mede — mais `stderr`, onde o
    diagnostico de erro mora. Comparavel com `bytes_servidos` de retorno podado."""
    if not isinstance(r, dict):
        return None
    total = 0
    for campo, sub in (("stdout", "texto"), ("stderr", "texto"), ("content", None),
                       ("erro", None)):
        alvo = r.get(campo)
        texto = (alvo or {}).get(sub) if sub else alvo
        if isinstance(texto, str):
            total += len(texto.encode("utf-8", "replace"))
    return total


def _env_subprocesso() -> dict:
    """Env do subprocesso: PATH explícito + segredos removidos.

    `bash -c` não-login não lê .bashrc nem .profile, então o PATH herdado do systemd
    não contém o bin da release nem ~/.local/bin. Montar aqui é a única forma de o
    verbo servido (/opt/platafirma/current/harness/bin) ser encontrável por quem chama
    a tool.
    """
    env = {k: v for k, v in os.environ.items() if k not in ENV_OCULTO}
    env["PATH"] = f"{BIN_VERBOS}:{CASA}/.local/bin:" + os.environ.get("PATH", "")
    return env


def _bancada() -> Path | None:
    """Bancada declarada pela conta, lida NA HORA da chamada — nunca no arranque.

    None quando não há declaração: quem chama recusa o pedido que dependia dela. A
    porta nunca cria a bancada nem nada dentro dela por conta própria."""
    try:
        return raizes.bancada()
    except raizes.BancadaNaoDeclarada:
        return None


_SEM_BANCADA = ("caminho relativo pede bancada declarada (PLATAFIRMA_BANCADA ou "
                "~/.config/platafirma/bancada) — sem ela, use caminho absoluto")


def _resolve_relativo(caminho: str) -> tuple[Path | None, str | None]:
    """(caminho, erro). Absoluto vale como está; relativo é relativo à bancada declarada."""
    p = Path(caminho)
    if p.is_absolute():
        return p, None
    b = _bancada()
    if b is None:
        return None, _SEM_BANCADA
    return b / p, None


def _cwd_de(cwd: str) -> tuple[Path | None, str | None]:
    """Cwd de run_command: vazio = a casa da conta; relativo = na bancada declarada."""
    return (CASA, None) if not cwd else _resolve_relativo(cwd)


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


def _mapa_azp_superficie() -> dict[str, str]:
    """Lê o mapa azp -> superfície de registro/superficies.json (dado, não código)."""
    caminhos = [
        PF_HARNESS / "registro" / "superficies.json",
        Path(__file__).resolve().parent.parent / "registro" / "superficies.json",
    ]
    for c in caminhos:
        if c.is_file():
            try:
                with open(c, encoding="utf-8") as f:
                    dados = json.load(f)
                mapa = dados.get("azp_superficie")
                if isinstance(mapa, dict):
                    return mapa
                ext = {}
                for sup_nome, sup_info in dados.get("superficies", {}).items():
                    if isinstance(sup_info, dict) and "azp" in sup_info:
                        ext[sup_info["azp"]] = sup_nome
                if ext:
                    return ext
            except Exception:
                pass
    return {"jaiminho-fabrica": "fabrica"}


def _superficie() -> str:
    """Superfície do request em curso, por eliminação com fallback."""
    try:
        ctx = mcp.get_context()
        req = getattr(getattr(ctx, "request_context", None), "request", None)
        # Degrau 4: sem request (caminho stdio/ensaio) -> desconhecida
        if req is None:
            return os.environ.get("PF_SUPERFICIE", "desconhecida")

        cab = getattr(req, "headers", None)
        if cab is not None:
            # Degrau 1: header x-pf-superficie presente -> vale o que veio
            sup = None
            if hasattr(cab, "get"):
                sup = cab.get("x-pf-superficie") or cab.get("X-PF-Superficie")
            if not sup and hasattr(cab, "items"):
                for k, v in cab.items():
                    if k.lower() == "x-pf-superficie":
                        sup = v
                        break
            if sup:
                return sup

        # Degraus 2 e 3: sem header, resolve por azp
        ident = _quem()
        azp = ident.get("azp") if isinstance(ident, dict) else None
        if azp and azp != "-":
            mapa = _mapa_azp_superficie()
            # Degrau 2: mapa azp -> superfície lido de registro/superficies.json
            if azp in mapa:
                return mapa[azp]
            # Degrau 3: sem header e azp == claudinho-mcp -> claude.ai
            if azp == "claudinho-mcp":
                return "claude.ai"

        # azp fora do mapa e != claudinho-mcp -> desconhecida
        return os.environ.get("PF_SUPERFICIE", "desconhecida")
    except Exception:                                       # noqa: BLE001
        pass
    return os.environ.get("PF_SUPERFICIE", "desconhecida")


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
        # `sessao_id` em TODA linha, mesmo ausente (arq:0101 §4): campo que so aparece
        # quando tem valor obriga quem periciar a distinguir "nao havia sessao" de
        # "esta versao ainda nao gravava" — e as duas leituras dao numeros diferentes.
        reg.setdefault("sessao_id", "-")
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
def _run_blocking(command: str, d: Path, timeout: int, sessao_id: str = "-", oid: str = "-",
                  cadeira: str = "") -> dict:
    """Parte síncrona de run_command — roda em thread do anyio, nunca no event loop
    (ver docstring de run_command pra motivo)."""
    env = {**_env_subprocesso(), "PF_SESSAO": sessao_id, "PF_ORDEM_ID": oid}
    if cadeira:
        env["PF_CADEIRA"] = cadeira
    try:
        p = subprocess.Popen(["bash", "-c", command], cwd=d, env=env,
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


PF_RUN_SO_VERBO = os.environ.get("PF_RUN_SO_VERBO", "1") != "0"
_OPERADORES_SHELL = {"|", ";", "&&", "||", ">", "<", ">>", "&"}

# spec_porta-so-verbo §3.5: programa que era fallback -> quem o cobre. `null` = verbo que falta.
_SUGESTAO = {
    # git/gh SAIRAM daqui: viram verbos finos (bin/git, bin/gh, shims), servidos pela
    # capsula (decisao 2b do dono, 07/09/2026). Verbo servido nao tem sugestao de
    # substituto — ele proprio roda. O shim git nega `push` e aponta `repo empurrar`;
    # o `repo` continua para a operacao contida (trava de producao + gate de release).
    "cat": "read_file", "head": "read_file", "tail": "read_file", "sed": "read_file",
    "less": "read_file", "ls": "read_file", "stat": "read_file", "wc": "read_file",
    "rg": "descobrir", "grep": "descobrir", "fd": "descobrir", "find": "descobrir",
    "docker": "infra", "systemctl": "infra", "journalctl": "infra", "loginctl": "infra",
    "curl": "pesquisar", "wget": "pesquisar",
    "python3": "teste", "python": "teste", "pytest": "teste", "uv": "teste", "ruff": "lint",
    "psql": "motor", "tee": "write_file", "cp": "write_file", "mv": "write_file",
    "read_file": "é tool, não verbo: read_file(path=...)",
    "write_file": "é tool, não verbo: write_file(path=..., content=...)",
    "monta_sessao": "é tool, não verbo: monta_sessao(cadeira=...)",
    "monta-sessao": "é tool, não verbo: monta_sessao(cadeira=...)",
    "run_command": "é a própria tool que você está chamando",
}

def _recusa(verbo: str, motivo: str) -> dict:
    r = {"recusado": True, "verbo": verbo[:80], "motivo": motivo,
         "sugestao": _SUGESTAO.get(verbo.split("/")[-1])}
    if motivo == "sem verbo" and r["sugestao"] is None:
        # sem reflexo conhecido: nao devolve so o null seco (spec_porta-so-verbo,
        # card fabrica/devops) — a lista inteira + o golden de uso, incondicional.
        r["verbos_servidos"] = sorted(SLUGS_SERVIDOS)
        r["golden"] = "<verbo> sem ato lista os atos, e a descricao da tool e o golden record"
    return r


def _stdin_texto(v):
    """Normaliza stdin de tool/lote pra string, ou None — nunca dict/list cru (#3124).

    O transporte MCP desserializa um stdin que e JSON valido ANTES de chegar aqui; a
    tool de verbo (`_faz_tool_verbo`) declarava `stdin: str | None` e o pydantic recusava
    o pedido inteiro, sem rodar nada ("Input should be a valid string"). None passa. str
    passa. dict/list vira `json.dumps` (o verbo que le stdin como JSON volta a funcionar
    do outro lado do pipe). bytes decodifica. Resto vira `str(v)` — nunca estoura aqui.
    """
    if v is None or isinstance(v, str):
        return v
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return str(v)


def _eh_pipe_stdin(v) -> bool:
    """So o marcador de pipe {"de": <int>} — chaves EXATAS, nada mais. Qualquer outro
    dict/list e conteudo (JSON), nunca pipe; vira texto por `_stdin_texto` (#3124)."""
    return (isinstance(v, dict) and set(v.keys()) == {"de"}
            and isinstance(v.get("de"), int) and not isinstance(v.get("de"), bool))


def _item_de_lote(x):
    """item de run_command -> (argv, stdin, recusa). argv[0] e o binario do whitelist."""
    stdin = None
    if isinstance(x, str):
        try:
            toks = shlex.split(x)
        except ValueError as e:
            return None, None, _recusa(x, f"nao parte: {e}")
        if not toks:
            return None, None, _recusa("", "item vazio")
        if toks[0] == "run_command" and len(toks) > 1:
            toks = toks[1:]
        for t in toks:
            if t in _OPERADORES_SHELL:
                return None, None, _recusa(toks[0], "metacaractere de shell — um verbo por item; "
                                                    "pipe vira stdin.de, ';' vira dois itens")
        verbo, resto = toks[0], toks[1:]
    elif isinstance(x, dict):
        verbo = str(x.get("verbo") or "")
        ato = str(x.get("ato") or "")
        args = x.get("args") or []
        if verbo == "run_command" and ato:
            verbo = ato
            ato = str(args[0]) if args else ""
            args = args[1:] if args else []
        # #3026: args STRING itera char-a-char ('motor' -> ['m','o','t',...]) e roda o
        # verbo com token corrompido, sem erro. O contrato quer lista; string e erro de
        # uso, e a porta o recusa aqui em vez de mascarar (custou a fita e8a97d73, 08/09).
        if isinstance(args, (str, bytes)):
            return None, None, _recusa(
                verbo, "args deve ser lista de tokens, recebido string; use args: [ ... ]")
        resto = ([ato] if ato else []) + [str(a) for a in args]
        stdin = x.get("stdin")
        if not _eh_pipe_stdin(stdin):
            stdin = _stdin_texto(stdin)
    else:
        return None, None, _recusa(str(x)[:40], "item nem string nem {verbo, ato, args, stdin}")
    slug = verbo.split("/")[-1]
    if slug not in SLUGS_SERVIDOS:
        if slug in SLUGS_RETIDOS:
            return None, None, _recusa(slug, "leva 2 desligada (PF_TOOLS_LEVA2)")
        return None, None, _recusa(slug, "sem verbo")
    return [BINARIOS[slug]] + resto, stdin, None

async def run_command(command: str = "", cwd: str = "", timeout: int = 120,
                       sessao_id: str | None = None,
                       commands: list | None = None,
                       encadeado: bool = False) -> dict:
    """Lote entre verbos DISTINTOS numa chamada so — sem shell, sem fallback (spec_porta-so-verbo).

    `commands`: lista de itens, cada um `{verbo, ato, args, stdin}` ou a string
    `"<verbo> <ato> <args...>"` (partida com shlex; `| & > < $ \\` * ? ( ) ;` recusam o item).
    Um `execve` por item (`bin/<verbo> <ato> <args>`), nunca `bash -c`; item roda na casa da
    conta e `cwd` e ignorado. `stdin` e texto ou `{"de": n}` = stdout do item n do mesmo lote
    (substitui o pipe). Programa que NAO e verbo servido nao roda: volta
    `{recusado, verbo, motivo, sugestao}` com o verbo que o cobre (`sugestao: null` = verbo
    que falta — vira card; junto vem `verbos_servidos` e `golden`, incondicional, nunca so
    o null seco). Sequencial; erro ou recusa num item nao derruba os outros; teto
    `CAP` por lote com `omitido_por_teto`/`lote_next`. `command` escalar = lote de 1 e
    devolve o resultado do item. `sessao_id` e o do `monta_sessao`. AUDITORIA: um JSONL
    por item em @LOG@/ — nao e silenciavel. Rollback: PF_RUN_SO_VERBO=0 + restart.
    `encadeado=true`: cadeia fixa — item com exit 0 ou 1 segue; qualquer outro (2..5,
    recusa, negado, timeout, exit fora da tabela) PARA, e os seguintes voltam
    `nao_rodou`; o bloco `cadeia` diz exit e primeira linha de cada item, `parou_em` e o
    exit do topo. Retomar = rerodar a cadeia: o que ja fez devolve "ja feito".
    """
    if not PF_RUN_SO_VERBO:
        return await _run_command_legado(command, cwd, timeout, sessao_id, commands)
    itens = list(commands) if commands else ([command] if command else [])
    if not itens:
        return {"recusado": True, "motivo": "sem item", "verbos_servidos": sorted(SLUGS_SERVIDOS)}
    timeout = max(1, min(timeout, 600))
    ident = _sessao_resolve(sessao_id)
    lote_id = uuid.uuid4().hex[:8]
    brutos: list = []
    _estado = {"ident": ident}

    async def _roda(_i, x, resultados):
        ident = _estado["ident"]
        r = await _roda_item_run_command(_i, x, resultados, brutos, ident, timeout,
                                         lote_id, encadeado)
        # Injeção entre itens do lote (Aberto spec_sessao/expediente, #3053):
        # se o item executado foi sessao abrir com sucesso, extrai sessao_id e
        # chama ident = _sessao_resolve(sid_novo) antes do item seguinte (n+1)
        if r.pop("_sessao_abriu", False):
            sid_novo = _extrai_sessao_id(brutos[-1])
            if sid_novo:
                _estado["ident"] = _sessao_resolve(sid_novo)
        return r

    out = await _lote.itera(itens, _roda, encadeado=encadeado, cap=CAP,
                            bytes_de=_lote.bytes_stdout)
    if encadeado:
        _c = out["cadeia"]
        _audit(tool="run_command", evento="lote_encadeado", lote_id=lote_id,
               lote_n=len(itens), parou_em=_c["parou_em"], exit_code=_c["exit"],
               nao_rodou=len(_c["nao_rodou"]), cadeira=ident["cadeira"] or None,
               sessao_id=ident["sessao_id"], ordem_id=ident["ordem_id"])
        return out
    if len(itens) == 1:
        return out["lote"][0]
    return out


async def _roda_item_run_command(_i, x, resultados, brutos, ident, timeout, lote_id,
                                 encadeado=False) -> dict:
    """Um item de `run_command commands[]`: parte, confere stdin.de, autoriza, roda,
    serve e audita. A ordem e a parada da cadeia sao de `lote.itera`."""
    aviso_dup = False
    if isinstance(x, str):
        try:
            _t = shlex.split(x)
            if _t and _t[0] == "run_command" and len(_t) > 1:
                aviso_dup = True
        except Exception:
            pass
    elif isinstance(x, dict) and str(x.get("verbo") or "") == "run_command" and x.get("ato"):
        aviso_dup = True
    argv, stdin, recusa = _item_de_lote(x)
    if recusa is None and _eh_pipe_stdin(stdin):
        n = stdin.get("de")
        slug0 = argv[0].rsplit("/", 1)[-1]
        if not isinstance(n, int) or n < 0 or n >= _i:
            recusa = _recusa(slug0, f"stdin.de={n!r} fora do lote (0..{_i - 1})")
        elif resultados[n].get("recusado") or resultados[n].get("erro"):
            recusa = _recusa(slug0, f"insumo do item {n} nao rodou")
        elif encadeado and _lote.exit_do_item(resultados[n]) != 0:
            # comentario #939 A4: na cadeia, insumo que saiu 1 ("nao existe") e vazio;
            # rodar o seguinte sobre nada e efeito sobre entrada vazia.
            recusa = _recusa(slug0, f"insumo do item {n} saiu {_lote.exit_do_item(resultados[n])}")
        else:
            stdin = brutos[n]
    if recusa:
        _audit(tool="run_command", evento="sem_verbo", verbo=recusa["verbo"],
               item=str(x)[:CMD_CAP],
               motivo=recusa["motivo"], sugestao=recusa["sugestao"],
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
               ordem_id=ident["ordem_id"], lote_id=lote_id, lote_n=_i,
               encadeado=encadeado or None)
        brutos.append("")
        return recusa
    slug = argv[0].rsplit("/", 1)[-1]
    linha = " ".join([slug] + argv[1:])
    negado = _autoriza(slug, "run_command", "comando", linha, DOM_RUNTIME)
    if negado:
        r = negado
        brutos.append("")
    else:
        t0 = time.monotonic()
        r = await anyio.to_thread.run_sync(_run_verbo_blocking, argv, stdin, timeout, ident)
        so = r.get("stdout")
        brutos.append(so.get("texto", "") if isinstance(so, dict) else "")
        _perf = _perfil_verbo(slug, argv[0])
        r = _serve(r, tool=slug, alca=linha, ident=ident, cauda=_perf["cauda"],
                   cosmetica=_cosmetica(_perf, argv[1] if len(argv) > 1 else None))
        if aviso_dup and isinstance(r, dict):
            r.setdefault("avisos", []).append("run_command: primeiro token 'run_command' desduplicado com aviso")
            if "aviso" not in r:
                r["aviso"] = "run_command: primeiro token 'run_command' desduplicado com aviso"
        _audit(tool=slug, evento="verbo", via="run_command",
               ato=argv[1] if len(argv) > 1 else None, args=" ".join(argv[2:])[:CMD_CAP],
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
               ordem_id=ident["ordem_id"], exit_code=r.get("exit_code"), erro=r.get("erro"),
               bytes_stdout=(r.get("stdout") or {}).get("bytes_total") if isinstance(r.get("stdout"), dict) else None,
               dur_ms=round((time.monotonic() - t0) * 1000),
               lote_id=lote_id, lote_n=_i, encadeado=encadeado or None, **_campos_poda(r))
    ato = argv[1] if len(argv) > 1 else ""
    if slug == "sessao" and ato == "abrir" and r.get("exit_code") == 0:
        r["_sessao_abriu"] = True     # quem itera troca o ident antes do item n+1
    return r

async def _run_command_legado(command: str = "", cwd: str = "", timeout: int = 120,
                       sessao_id: str | None = None,
                       commands: list[str] | None = None) -> dict:
    """FALLBACK: executa um comando shell (`bash -c`) como o usuário @USER@, para o que
    não tem verbo — git, docker (rootless), systemctl --user, rg, fluxo de dado entre
    verbos. Verbo do núcleo tem tool própria (nome = slug); usá-lo por aqui é medido.

    cwd vazio = a casa da conta; absoluto vale como está; relativo é relativo à bancada
    declarada (PLATAFIRMA_BANCADA ou ~/.config/platafirma/bancada) e, sem ela, a chamada é
    recusada. timeout em segundos (teto 600); estourou,
    o grupo de processo inteiro é morto. stdout/stderr voltam com truncagem declarada
    (`truncado`/`bytes_total`). `&&` engole o exit code — use `;` ou chamadas separadas.

    `commands`: lista de comandos, cada um seu próprio `bash -c`, sequencial, mesmo
    `ident`; erro num item não derruba o lote. Atrás de `PF_TOOLS_LOTE` (§5c); teto de
    bytes do lote = `CAP` (D4), item excedente volta `{"omitido_por_teto": True}` com
    `lote_next`. `command` escalar segue válido quando `commands` não vem.

    PATH já traz @BIN@ e ~/.local/bin (bash -c não lê .bashrc). Segredos da instância
    NÃO descem para o ambiente. AUDITORIA: toda chamada grava JSONL em @LOG@/
    (comando, cwd, exit, duração) — não é silenciável.
    """
    d, erro_cwd = _cwd_de(cwd)
    if erro_cwd:
        _audit(tool="run_command", evento="cwd_recusado", cwd=cwd, motivo=erro_cwd)
        return {"recusado": True, "cwd": cwd, "motivo": erro_cwd}
    if commands and PF_TOOLS_LOTE:
        timeout = max(1, min(timeout, 600))
        ident = _sessao_resolve(sessao_id)
        lote_id = uuid.uuid4().hex[:8]
        resultados = []
        acumulado = 0
        lote_next = None
        for _i, cmd in enumerate(commands):
            if acumulado >= CAP:
                lote_next = _i
                break
            negado_item = _autoriza("run_command", "run_command", "comando", cmd, DOM_RUNTIME)
            if negado_item:
                r = negado_item
            else:
                t0 = time.monotonic()
                r = await anyio.to_thread.run_sync(_run_blocking, cmd, d, timeout,
                                                   ident["sessao_id"], ident["ordem_id"], ident["cadeira"])
                so = r.get("stdout")
                txt_bruto = so.get("texto", "") if isinstance(so, dict) else (so if isinstance(so, str) else "")
                r = _serve(r, tool="run_command", alca=f"{d}|{cmd}", ident=ident)
                _audit(tool="run_command", comando=cmd[:CMD_CAP], evento="fallback",
                       cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
                       ordem_id=ident["ordem_id"], exit_code=r.get("exit_code"), erro=r.get("erro"),
                       bytes_stdout=r.get("stdout", {}).get("bytes_total"),
                       dur_ms=round((time.monotonic() - t0) * 1000),
                       lote_id=lote_id, lote_n=_i, **_campos_poda(r))
                if r.get("exit_code") == 0 and re.search(r"\bsessao\s+abrir\b", cmd):
                    sid_novo = _extrai_sessao_id(txt_bruto)
                    if sid_novo:
                        ident = _sessao_resolve(sid_novo)
            acumulado += (r.get("stdout") or {}).get("bytes_total", 0)
            resultados.append(r)
        for _i in range(len(resultados), len(commands)):
            resultados.append({"omitido_por_teto": True})
        return {"lote": resultados, "lote_n": len(commands), "lote_next": lote_next}
    negado = _autoriza("run_command", "run_command", "comando", command,
                       DOM_RUNTIME)
    if negado:
        return negado
    timeout = max(1, min(timeout, 600))
    ident = _sessao_resolve(sessao_id)
    if PF_GATE:
        segs = [s.strip() for s in command.split(";") if s.strip()]
        elegivel = bool(segs)
        argvs = []
        if elegivel:
            for seg in segs:
                try:
                    argv = shlex.split(seg)
                except ValueError:
                    elegivel = False
                    break
                if not argv or argv[0] not in SLUGS_SERVIDOS:
                    elegivel = False
                    break
                # Barreira DEPOIS do shlex: procura metacaracteres nus nos tokens
                if any(t in ("|", "&", ">", "<", "$", "`", "*", "?", "(", ")") for t in argv):
                    elegivel = False
                    break
                argvs.append(argv)
        if elegivel:
            resultados = []
            for argv in argvs:
                r = await anyio.to_thread.run_sync(
                    _run_verbo_blocking, argv, None, timeout, ident)
                _perf = _perfil_verbo(argv[0], str(BIN_VERBOS / argv[0]))
                r = _serve(r, tool=argv[0], alca=" ".join(argv), ident=ident,
                           cauda=_perf["cauda"],
                           cosmetica=_cosmetica(_perf, argv[1] if len(argv) > 1 else None))
                _audit(tool=argv[0], evento="verbo_contornado", comando=" ".join(argv)[:CMD_CAP],
                       cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
                       ordem_id=ident["ordem_id"], exit_code=r.get("exit_code"),
                       erro=r.get("erro"), **_campos_poda(r))
                resultados.append(r)
            if len(resultados) == 1:
                return {**resultados[0], "aviso": f"tem tool {argvs[0][0]} — chamada roteada pela porta"}
            return {"lote": resultados, "aviso": f"{len(resultados)} verbos roteados"}
    t0 = time.monotonic()
    r = await anyio.to_thread.run_sync(_run_blocking, command, d, timeout,
                                       ident["sessao_id"], ident["ordem_id"], ident["cadeira"])
    r = _serve(r, tool="run_command", alca=f"{d}|{command}", ident=ident)
    _audit(tool="run_command", comando=command[:CMD_CAP], evento="fallback",
           comando_truncado=len(command) > CMD_CAP, cwd=str(d),
           cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"], ordem_id=ident["ordem_id"],
           exit_code=r.get("exit_code"), erro=r.get("erro"),
           bytes_stdout=r.get("stdout", {}).get("bytes_total"),
           dur_ms=round((time.monotonic() - t0) * 1000), **_campos_poda(r))
    return r


# --- fila: fora do alcance de read_file/write_file ---------------------------
# A fila tem verbo proprio (`fila`), que faz append sob flock e sabe de quem e a
# caixa. write_file SUBSTITUI: em 05/08/2026 apagou 23.120 bytes da caixa de uma
# persona alheia numa tacada. Arquivo de fila so se toca pelo verbo. A fila v0 em
# arquivo e fossil (Valkey Streams a substituiu); a negativa fica ate ela sair do estado.
FILA_RAIZ = Path(os.environ.get("PF_FILA", INSTANCIA / "var" / "fila")).resolve()


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


_PDP_DIR = Path(os.environ["PDP_DIR"]).resolve() if os.environ.get("PDP_DIR") else None
_SEGREDO_DIRS = tuple(d for d in (_PDP_DIR,) if d)
# Toda instancia guarda segredo em <raiz-das-instancias>/<instancia>/segredos (desenho
# §3). A negativa e POR CONSTRUCAO, por forma de caminho, e nao pela lista de instancias
# que existem hoje: instancia nova nasce negada sem ninguem lembrar de acrescentar.
_RAIZES_DE_INSTANCIA = tuple(dict.fromkeys((Path("/srv/platafirma"), INSTANCIA.parent)))


def _sob_segredos_de_instancia(alvo: Path) -> bool:
    for base in _RAIZES_DE_INSTANCIA:
        try:
            partes = alvo.relative_to(base).parts
        except ValueError:
            continue
        if len(partes) >= 2 and partes[1] == "segredos":
            return True
    return False


def _nega_segredo(p: Path, tool: str):
    """spec_porta-so-verbo §4.6: .env*, *.key|*.pem, .credentials.json, <instancia>/segredos/, PDP_DIR."""
    try:
        alvo = p.resolve()
    except OSError:
        return None
    nome = alvo.name
    if (nome.startswith(".env") or alvo.suffix in (".key", ".pem") or nome == ".credentials.json"
            or _sob_segredos_de_instancia(alvo) or _sob_segredos_de_instancia(p.absolute())
            or any(d == alvo or d in alvo.parents for d in _SEGREDO_DIRS)):
        _audit(tool=tool, evento="leitura_recusada", path=str(p), motivo="segredo")
        return {"recusado": True, "path": str(p),
                "motivo": "segredo: fora do alcance de read_file (spec_porta-so-verbo §4.6)"}
    return None

def _le_um_arquivo(path: str, offset: int, max_bytes: int, ident: dict,
                   lote_id: str | None = None, lote_n: int | None = None) -> dict:
    negado = _autoriza("read_file", "read_file", "documento", path, DOM_PLATAFORMA)
    if negado:
        return negado
    p, erro_caminho = _resolve_relativo(path)
    if erro_caminho:
        _audit(tool="read_file", evento="leitura_recusada", path=path, motivo=erro_caminho,
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
               ordem_id=ident["ordem_id"], lote_id=lote_id, lote_n=lote_n)
        return {"recusado": True, "path": path, "motivo": erro_caminho}
    bloqueio = _nega_fila(p, "read_file") or _nega_segredo(p, "read_file")
    if bloqueio:
        return bloqueio
    if not p.is_file():
        # A mensagem distingue os tres casos que antes colapsavam numa frase so
        # (diagnostico invertido custou 4 giros na fita o20260909T163333-79b32d):
        # diretorio existente != caminho ausente != no de outro tipo (socket, fifo).
        if p.is_dir():
            erro = "é um diretório, não um arquivo — read_file só lê arquivo"
        elif p.exists():
            erro = "existe mas não é arquivo comum (socket, fifo ou dispositivo)"
        else:
            erro = "não existe"
        _audit(tool="read_file", path=str(p), erro=erro,
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"], ordem_id=ident["ordem_id"],
               lote_id=lote_id, lote_n=lote_n)
        return {"erro": erro, "path": str(p)}
    tamanho_total = p.stat().st_size
    offset = max(0, offset)
    max_bytes = max(1, min(max_bytes, 200000))
    with open(p, "rb") as fh:
        if offset > 0:
            fh.seek(offset)
        chunk = fh.read(max_bytes)
    fim = offset + len(chunk)
    truncated = fim < tamanho_total
    next_offset = fim if truncated else None
    r = {"content": chunk.decode("utf-8", "replace"), "bytes_total": tamanho_total,
         "offset": offset, "bytes_lidos": len(chunk),
         "truncated": truncated, "next_offset": next_offset,
         "path": str(p)}
    # O dup exato mais caro medido na perícia de 5 dias é o MESMO caminho relido: a alça
    # é (path, offset), e é por ela que a releitura idêntica sai como aviso e a mudada
    # sai como diff. `path` é identificador exato — nunca entra na poda (invariante iv).
    r = _serve(r, tool="read_file", alca=f"{p}|{offset}", ident=ident)
    _audit(tool="read_file", path=str(p), bytes_lidos=len(chunk), bytes_total=tamanho_total,
           cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"], ordem_id=ident["ordem_id"],
           lote_id=lote_id, lote_n=lote_n, **_campos_poda(r))
    return r


def read_file(path: str = "", offset: int = 0, max_bytes: int = 40000,
              sessao_id: str | None = None, paths: list[str] | None = None) -> dict:
    """Lê um arquivo: `path` absoluto, ou relativo à bancada declarada (sem ela, recusa).

    Truncagem sempre declarada: truncated/bytes_total/next_offset para paginar.
    Inexistente volta com erro preenchido, nunca exceção.

    `paths`: lista de caminhos, um item por leitura, atrás de `PF_TOOLS_LOTE` (§5c);
    teto de bytes do lote = `CAP` (D4), item excedente volta `{"omitido_por_teto": True}`
    com `lote_next`. `path` escalar segue válido quando `paths` não vem.
    """
    ident = _sessao_resolve(sessao_id)
    if paths and PF_TOOLS_LOTE:
        lote_id = uuid.uuid4().hex[:8]
        resultados = []
        acumulado = 0
        lote_next = None
        for _i, pth in enumerate(paths):
            if acumulado >= CAP:
                lote_next = _i
                break
            r = _le_um_arquivo(pth, offset, max_bytes, ident, lote_id, _i)
            acumulado += r.get("bytes_total", 0)
            resultados.append(r)
        for _i in range(len(resultados), len(paths)):
            resultados.append({"omitido_por_teto": True})
        return {"lote": resultados, "lote_n": len(paths), "lote_next": lote_next}
    return _le_um_arquivo(path, offset, max_bytes, ident)


# --- write_file: tipo x morada, sem symlink, atomico (spec_porta-so-verbo §4) ----
# .php e .mjs entraram em 25/09/2026 (#3133): a skin da wiki (platafirma-conhecimento, .php)
# e as provas do rastreador (platafirma-ui, .mjs) sao texto plano da mesma classe de .js e
# .html, e ficavam sem porta — citacao a corrigir neles nao tinha como ser escrita.
TIPOS_TEXTO = {".py", ".md", ".mmd", ".d2", ".sh", ".sql", ".yaml", ".yml", ".json", ".toml",
               ".css", ".html", ".js", ".mjs", ".php", ".txt", ".conf"}
# Texto de build que se reconhece pelo nome, nao pela extensao. Entrou em 23/09/2026: sem
# ele, stack nova com imagem propria (Dockerfile, conf do nginx) nao tinha como ser escrita
# pela porta, e a saida era esconder o Dockerfile dentro do compose.
NOMES_TEXTO = {"Dockerfile", ".dockerignore", "VERDES"}  # VERDES: baseline do pre-push (guia portoes-do-codigo)
# platafirma-ui entrou em 22/09/2026 (hotfix): o clone existia na bancada e o front do
# rastreador mora nele, mas a lista nomeada o deixava fora e a tela nao tinha como ser
# corrigida pela porta.
# platafirma-casa entrou em 23/09/2026 (arq:0115 §1.2): e o suporte do documento de casa;
# sem ele na lista, a bancada wt/platafirma-casa/<cadeira> e o clone <bancada>/platafirma-casa
# recusavam write_file ("fora de morada") e o conteudo nao tinha como ser escrito pela porta.
# platafirma-rastreador entrou em 25/09/2026 (#3132): a API do rastreador mora nele e o
# clone ja existia na bancada, mas ficava fora da lista — a Frente 2 do #3115 parou ai.
CLONES = ("platafirma-core", "platafirma-conhecimento", "platafirma-arquitetura",
          "platafirma-harness", "platafirma-motor", "platafirma-posto", "platafirma-ui",
          "platafirma-casa", "platafirma-rastreador", "modulo-osint")
ESCRITA_TETO = 1_048_576
TMP_FITA = INSTANCIA / "var" / "tmp"


def _negadas_escrita() -> dict:
    """Negativas por caminho absoluto. Avaliadas antes das moradas: vencem sempre."""
    return {
        raizes.release_raiz(): "release e imutavel — muda por `release promover`, nunca por escrita",
        FILA_RAIZ: "use o verbo `fila` (append sob flock, com identidade)",
        INSTANCIA / "var" / "abertura-publicada": "arvore imutavel — so `publicar-abertura` (arq:0097)",
        INSTANCIA / "var" / "log": "log nao se edita",
        INSTANCIA / "segredos": "segredo se grava por `seg segredo gravar`",
    }


def _real(p: Path) -> Path:
    try:
        return p.resolve()
    except OSError:
        return p


def _moradas_escrita():
    """Rascunho da fita (instancia) + clones e worktrees da bancada DECLARADA.

    Sem bancada declarada sobra so o rascunho: a porta nao inventa lugar de codigo.
    `<bancada>/<repo>` e o clone base (o `repo` cai nele sem worktree da cadeira) e
    `<bancada>/wt/<repo>/<cadeira>` o worktree por cadeira (arq:0109 §2)."""
    moradas = [(_real(TMP_FITA), TIPOS_TEXTO)]
    b = _bancada()
    if b is not None:
        b = _real(b)
        moradas += [(b / "wt" / c, TIPOS_TEXTO) for c in CLONES]
        moradas += [(b / c, TIPOS_TEXTO) for c in CLONES]
    return moradas


def _em_bin_do_harness(real_pai: Path) -> bool:
    """bin/ de um clone ou worktree do harness na bancada: morada de verbo (sem extensao)."""
    b = _bancada()
    if b is None:
        return False
    b = _real(b)
    # profundidade do bin/ sob a raiz: clone base 0; worktree plano ou por sessao
    # wt/platafirma-harness/<x>/bin 1; worktree por cadeira e card
    # wt/platafirma-harness/<cadeira>/<card-ou-slug>/bin 2 (card:3149 passo 3)
    for raiz_clone, profs in ((b / "platafirma-harness", (0,)),
                              (b / "wt" / "platafirma-harness", (1, 2))):
        try:
            partes = real_pai.relative_to(raiz_clone).parts
        except ValueError:
            continue
        if any(len(partes) > p and partes[p] == "bin" for p in profs):
            return True
    return False


def _clone_ausente(raiz: Path, real_pai: Path) -> str | None:
    """Morada na bancada so vale sobre clone ou worktree que JA existe no disco.

    Sem isto o mkdir do `_escreve_atomico` recriaria a bancada apagada (ou um worktree
    que nunca foi aberto) como diretorio comum, sem git — criacao silenciosa que o
    desenho §6 proibe. Clone e worktree nascem por `repo abrir`, nunca por write_file."""
    rel = real_pai.relative_to(raiz).parts
    if raiz.parent.name == "wt":
        if not rel:
            return f"morada: {raiz}/<cadeira>/<arquivo> — worktree da cadeira e obrigatorio"
        base = raiz / rel[0]
    else:
        base = raiz
    if not base.is_dir():
        return (f"fora de morada: {base}/ nao existe — clone e worktree nascem por "
                f"`repo abrir {raiz.name}`, write_file nao os cria")
    return None


def _resolve_escrita(path: str, ident: dict):
    """(alvo_real, erro). Lexico -> realpath do PAI -> negativas -> morada -> tipo -> symlink.
    So o pai se resolve (TLPI cap. 18, tab. 18-1: componente symlink no meio escapa da
    comparacao de string); o alvo se confere por lstat e o rename final nunca segue link."""
    pp = PurePosixPath(path or "")
    partes = pp.parts
    if not partes or ".." in partes or any(ord(ch) < 32 for ch in path):
        return None, "caminho: absoluto ou relativo a bancada, sem '..' nem caractere de controle"
    if ".git" in partes:
        return None, "fora de morada: .git nao se escreve por write_file — use `repo`"
    alvo, erro = _resolve_relativo(str(pp))
    if erro:
        return None, erro
    pai = alvo.parent
    anc = pai
    while not anc.exists():
        anc = anc.parent
    try:
        real_pai = anc.resolve() / pai.relative_to(anc)
    except OSError as e:
        return None, f"caminho: {e}"
    for neg, porque in _negadas_escrita().items():
        for n in dict.fromkeys((neg, _real(neg))):
            if real_pai == n or n in real_pai.parents:
                return None, f"fora de morada: {neg}/ — {porque}"
    ext = alvo.suffix.lower()
    tmp_fita = _real(TMP_FITA)
    for raiz, tipos in _moradas_escrita():
        if not (real_pai == raiz or raiz in real_pai.parents):
            continue
        if _em_bin_do_harness(real_pai):
            tipos = tipos | {""}
        if ext not in tipos and alvo.name not in NOMES_TEXTO:
            return None, (f"tipo: '{ext or '(sem extensao)'}' fora de "
                          f"{sorted(t or '(sem)' for t in tipos)} (e dos nomes "
                          f"{sorted(NOMES_TEXTO)}) em {raiz}/")
        if raiz == tmp_fita:
            rel = real_pai.relative_to(tmp_fita).parts
            if not rel:
                return None, f"morada: {TMP_FITA}/<ordem_id>/<arquivo> — subpasta da fita e obrigatoria"
            if ident["ordem_id"] not in ("-", rel[0]):
                return None, f"morada: {TMP_FITA}/{rel[0]}/ nao e a pasta desta fita ({ident['ordem_id']})"
        else:
            erro_clone = _clone_ausente(raiz, real_pai)
            if erro_clone:
                return None, erro_clone
        real_alvo = real_pai / alvo.name
        if real_alvo.is_symlink():
            return None, "alvo e symlink — write_file nao escreve atraves de link"
        return real_alvo, None
    moradas = ", ".join(str(r) + "/" for r, _ in _moradas_escrita())
    if _bancada() is None:
        moradas += " (bancada nao declarada: clones e worktrees fora de alcance)"
    return None, "fora de morada: " + moradas

def _escreve_atomico(real_alvo: Path, data: bytes, modo: int) -> None:
    """mkstemp no MESMO dir -> write -> fsync -> rename -> fsync do dir. Inteira ou nada
    (Secure Programs HOWTO §7.11.1.1); temporario nunca em /tmp (§7.11.1.2)."""
    real_alvo.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(real_alvo.parent), prefix=f".{real_alvo.name}.pf-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, modo)
        os.rename(tmp, real_alvo)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    dfd = os.open(str(real_alvo.parent), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)

def write_file(path: str, content: str = "", sessao_id: str | None = None,
               trecho: dict | None = None) -> dict:
    """Escreve arquivo de TIPO declarado em MORADA declarada, atomico (spec_porta-so-verbo §4).

    `path` absoluto, ou relativo à bancada declarada (sem ela, recusa). Moradas: na
    bancada, clones platafirma-*/modulo-osint e seus worktrees em wt/<repo>/<cadeira>
    (working tree, fora de .git), com bin/ do harness aceitando verbo (sem extensao +
    shebang); na instancia, @TMP@/<ordem_id>/ (rascunho da fita). Tipos: .py .md .mmd .d2 .sh
    .sql .yaml .yml .json .toml .css .html .js .mjs .php .txt .conf. Fora disso volta
    `{recusado, motivo}` nomeando o porque (release, fila, abertura publicada, log, segredos, .git, symlink,
    tipo, tamanho). `content` = arquivo
    INTEIRO (teto 1 MiB). `trecho={"antes","depois"}` = edicao por trecho: `antes` tem de
    ocorrer exatamente UMA vez no arquivo; zero ou mais recusa com a contagem. Escrita por
    mkstemp no mesmo dir + fsync + rename: inteira ou nada. Auditoria com sha256 antes/depois.
    """
    negado = _autoriza("write_file", "write_file", "documento", path, DOM_PLATAFORMA)
    if negado:
        return negado
    ident = _sessao_resolve(sessao_id)

    def _rec(motivo):
        _audit(tool="write_file", evento="escrita_recusada", path=path, motivo=motivo,
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
               ordem_id=ident["ordem_id"])
        return {"recusado": True, "path": path, "motivo": motivo}

    real_alvo, erro = _resolve_escrita(path, ident)
    if erro:
        return _rec(erro)
    existia = real_alvo.is_file()
    antes_sha = hashlib.sha256(real_alvo.read_bytes()).hexdigest() if existia else None
    if trecho:
        if not existia:
            return _rec("trecho: arquivo nao existe")
        a, d = str(trecho.get("antes") or ""), str(trecho.get("depois") or "")
        if not a:
            return _rec("trecho: `antes` vazio")
        atual = real_alvo.read_text("utf-8", "replace")
        n = atual.count(a)
        if n == 1:
            content = atual.replace(a, d, 1)
        else:
            pat = re.sub(r'(\r?\n[ \t]*)+', r'(?:\\r?\\n[ \\t]*)+', re.escape(a))
            matches = list(re.finditer(pat, atual))
            if len(matches) == 1:
                m = matches[0]
                content = atual[:m.start()] + d + atual[m.end():]
            else:
                return _rec(f"trecho: `antes` ocorre {len(matches) if matches else n} vez(es) — precisa ser exatamente 1")
    data = (content or "").encode("utf-8")
    if len(data) > ESCRITA_TETO:
        return _rec(f"tamanho: {len(data)} B > teto {ESCRITA_TETO} B")
    em_bin = _em_bin_do_harness(real_alvo.parent)
    if em_bin and not real_alvo.suffix and not data.startswith(b"#!"):
        return _rec("tipo: verbo sem shebang na primeira linha")
    if existia:
        modo = real_alvo.stat().st_mode & 0o777
    else:
        modo = 0o755 if (em_bin and not real_alvo.suffix) else 0o644
    try:
        _escreve_atomico(real_alvo, data, modo)
    except OSError as e:
        return {"erro": str(e), "path": str(real_alvo)}
    depois_sha = hashlib.sha256(data).hexdigest()
    _audit(tool="write_file", evento="escrita", path=str(real_alvo), bytes=len(data),
           substituiu=existia, trecho=bool(trecho), sha256_antes=antes_sha, sha256=depois_sha,
           cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
           ordem_id=ident["ordem_id"])
    return {"ok": True, "path": str(real_alvo), "bytes": len(data), "substituiu": existia,
            "sha256": depois_sha}


# --- contexto de abertura de cadeira -----------------------------------------
# As duas variáveis saem do TEXTO da persona, nunca do nome do arquivo: a linha 1
# ("Você é <nome>,") dá o nome canônico — que é o diretório da fila — e a linha
# FERRAMENTAL: dá o caminho do manifesto. Convenção de nome de arquivo não produz o
# "claudinha" de persona-fabrica.md.
# A abertura servida e a MORADA PUBLICADA da instancia (arq:0097), nunca o clone.
PERSONAS = Path(os.environ.get(
    "PF_PERSONAS", INSTANCIA / "var/abertura-publicada/current/abertura"))
ORG_CANONICO = Path(os.environ.get(
    "PF_ORG", raizes.release() / "arquitetura/docs/org-template-canonico.md"))


RE_NOME = re.compile(r"^Você é ([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]*)")
RE_FERRAMENTAL = re.compile(r"^FERRAMENTAL:\s*(\S+\.md)")


def _cadeiras() -> list:
    # arq:0073: a cadeira e um subdir de abertura/, nao mais persona-<x>.md.
    if not PERSONAS.is_dir():
        return []
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
    verbo = str(BIN_VERBOS / "mesa")
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


def _acha_bin(nome: str) -> str:
    """Resolve o binário SERVIDO (BINARIOS -> bin da release). A porta executa o que está
    no ar (release), nunca o working tree do clone (arq:0097; #3029): faltando no servido,
    o caminho volta inexistente e o execve declara — não se cai em PF_HARNESS/bin nem no
    PATH, que é como o SHA velho (ou o novo demais) entra calado na abertura."""
    if nome in BINARIOS and os.path.isfile(BINARIOS[nome]):
        return BINARIOS[nome]
    return str(BIN_VERBOS / nome)


def _exec_argv(binario: str, *args) -> list[str]:
    """Monta argv para execução. Se o shebang apontar para python inexistente, executa via sys.executable."""
    if os.path.isfile(binario):
        try:
            with open(binario, "rb") as f:
                first_line = f.readline()
                if first_line.startswith(b"#!"):
                    interp = first_line[2:].decode("utf-8", "ignore").strip().split()[0]
                    if not os.path.exists(interp) and "python" in interp:
                        return [sys.executable, binario, *args]
        except Exception:
            pass
    return [binario, *args]


def _montar(cadeira: str, atualizar: bool = True, chapeu: str = "", pergunta: str = "",
            sessao_id: str | None = None, sub: str | None = None) -> dict:
    """Projeção do lote sessao abrir -> expediente montar (spec_sessao §6, #3053).

    (a) execve `bin/sessao abrir <slug> [--sessao-id <uuid>] --json` com PF_SUJEITO = o `sub`
        do token validado. Sem sub -> execve roda sem PF_SUJEITO e devolve o exit 3 de abrir
        como está, não fabrica sujeito.
    (b) Lê sessao_id do JSON de abrir; RELÊ a chave `sessao:{id}` no msg-mem e dela tira
        cadeira, ordem_id — em slug puro (arq:0110 §5). A porta NÃO escreve na chave.
    (c) execve `bin/expediente montar [--chapeu <slug>] --json` com
        PF_CADEIRA/PF_SESSAO/PF_ORDEM_ID/PF_SUPERFICIE injetados e a pergunta por STDIN
        (nunca por argumento).
    (d) Resposta = JSON do expediente com o bloco `sessao` (saída do abrir) no topo,
        campo `chapeu` preservado; `atualizar` continua aceito e sem efeito. Falha em `abrir`
        (exit ≠ 0) interrompe — não roda expediente e devolve o erro do abrir com o id, se houver.
    """
    bin_sessao = _acha_bin("sessao")
    bin_expediente = _acha_bin("expediente")

    # A porta passa a cadeira COMO RECEBEU: canonizar (prefixo fora, minúsculas, alias)
    # é a etapa 3 de `sessao abrir`, por `persona foto` — um chamador só (spec_sessao §2;
    # arq:0108: resolução por um ato, parsing é violação). Segunda implementação aqui
    # divergiria em silêncio (#2438).
    slug = (cadeira or "").strip()

    # (a) execve `bin/sessao abrir <slug> [--sessao-id <uuid>] --json` com PF_SUJEITO = sub
    argv_abrir = _exec_argv(bin_sessao, "abrir")
    if slug:
        argv_abrir.append(slug)
    if sessao_id:
        argv_abrir += ["--sessao-id", sessao_id]
    argv_abrir.append("--json")

    env_abrir = {
        **_env_subprocesso(),
        "PF_SUPERFICIE": _superficie(),
    }
    if sub and sub != "-":
        env_abrir["PF_SUJEITO"] = sub

    d_cwd = CASA if CASA.is_dir() else Path.cwd()
    try:
        proc_abrir = subprocess.run(
            argv_abrir,
            capture_output=True,
            text=True,
            timeout=30,
            env=env_abrir,
            cwd=d_cwd,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return {"erro": f"falha ao executar sessao abrir: {type(e).__name__}: {e}",
                "verbo": " ".join(argv_abrir), "cadeiras": _cadeiras()}

    # Falha em abrir (exit ≠ 0) interrompe — não roda expediente e devolve o erro do abrir com o id, se houver.
    if proc_abrir.returncode != 0:
        try:
            err_json = json.loads(proc_abrir.stdout)
            if isinstance(err_json, dict):
                return err_json
        except Exception:
            pass
        msg = proc_abrir.stderr.strip() or proc_abrir.stdout.strip() or f"exit {proc_abrir.returncode}"
        return {"erro": msg, "exit_code": proc_abrir.returncode}

    try:
        abrir_json = json.loads(proc_abrir.stdout)
    except Exception as e:
        return {"erro": f"sessao abrir devolveu JSON inválido: {e}", "stdout": proc_abrir.stdout[:200]}

    if not isinstance(abrir_json, dict):
        return {"erro": f"sessao abrir saída inesperada: {proc_abrir.stdout[:200]}"}

    # (b) Lê sessao_id do JSON de abrir; RELÊ sessao:{id} no msg-mem (arq:0110 §5)
    sid = abrir_json.get("sessao_id")
    cad_slug = None
    oid = None
    if sid:
        try:
            raw = _rc().get(f"sessao:{sid}")
            if raw:
                dados_chave = json.loads(raw)
                cad_slug = dados_chave.get("cadeira")
                oid = dados_chave.get("ordem_id")
        except Exception as e:
            print(f"[valkey] releitura sessao:{sid} falhou: {e!r}", file=sys.stderr, flush=True)

    # Slug puro da cadeira e ordem_id da chave (ou fallback do próprio abrir_json)
    # Slug puro vem da CHAVE (quem cunhou canonizou); faltando a releitura, do json de
    # `abrir`, que já sai canonizado (spec_sessao §3). Nunca se normaliza aqui: se o que
    # chegar não for slug puro, `expediente` sai 3 declarado — melhor que parse calado.
    cad_slug = cad_slug or abrir_json.get("cadeira") or slug
    oid = oid or abrir_json.get("ordem_id") or ""

    # (c) execve `bin/expediente montar [--chapeu <slug>] --json` com
    # PF_CADEIRA/PF_SESSAO/PF_ORDEM_ID/PF_SUPERFICIE injetados e a pergunta por STDIN
    argv_exp = _exec_argv(bin_expediente, "montar", "--json")
    if chapeu:
        argv_exp += ["--chapeu", chapeu]

    env_exp = {
        **_env_subprocesso(),
        "PF_CADEIRA": cad_slug,
        "PF_SESSAO": sid or "",
        "PF_ORDEM_ID": oid or "",
        "PF_SUPERFICIE": _superficie(),
    }

    try:
        proc_exp = subprocess.run(
            argv_exp,
            input=pergunta or "",
            capture_output=True,
            text=True,
            timeout=90,
            env=env_exp,
            cwd=d_cwd,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return {"erro": f"falha ao executar expediente montar: {type(e).__name__}: {e}",
                "verbo": " ".join(argv_exp)}

    if proc_exp.returncode != 0:
        try:
            err_exp = json.loads(proc_exp.stdout)
            if isinstance(err_exp, dict):
                return err_exp
        except Exception:
            pass
        msg = proc_exp.stderr.strip() or proc_exp.stdout.strip() or f"expediente exit {proc_exp.returncode}"
        return {"erro": msg, "exit_code": proc_exp.returncode}

    try:
        exp_json = json.loads(proc_exp.stdout)
    except Exception as e:
        return {"erro": f"expediente montar devolveu JSON inválido: {e}", "stdout": proc_exp.stdout[:200]}

    # (d) Resposta = JSON do expediente com o bloco `sessao` (saída do abrir) no topo,
    # campo `chapeu` preservado; `atualizar` continua aceito e sem efeito.
    resposta = {"sessao": abrir_json}
    resposta.update(exp_json)

    # Porta marca o prefixo estável com cache_control (spec_contexto-na-porta, #3067).
    # O prefixo e DERIVADO da ordem servida, nao lista fixa: a corrida contigua, desde
    # a primeira peca, das pecas nomeadas estaveis pela spec expediente rev 1.2
    # (persona, chapeu, conduta) ou declaradas `volatilidade: estavel` pelo expediente
    # (ex.: rotinas). A primeira peca fora disso fecha o prefixo — cache de prefixo so
    # vale ate o primeiro byte que muda. Lista fixa ficou velha duas vezes (#3146 poe o
    # chapeu entre persona e conduta; #3084 poe rotinas logo depois).
    prefixo = []
    for p in resposta.get("pecas", []):
        if p.get("peca") in ("persona", "chapeu", "conduta") or p.get("volatilidade") == "estavel":
            p["cache_control"] = {"type": "ephemeral"}
            p["cacheavel"] = True
            prefixo.append(p.get("peca"))
            continue
        break

    if isinstance(resposta.get("pacote"), dict):
        resposta["pacote"]["prefixo_cacheavel"] = prefixo
        resposta["pacote"]["cache_control"] = {"type": "ephemeral"}

    return resposta


def _primeiro_giro(pergunta: str) -> bool:
    """Predicado auxiliar mantido para compatibilidade."""
    return bool((pergunta or "").strip())


async def monta_sessao(cadeira: str = "", atualizar: bool = True, chapeu: str = "",
                        pergunta: str = "", sessao_id: str | None = None) -> dict:
    """Abre a sessão de uma cadeira numa chamada (projeção do lote sessao abrir -> expediente montar).

    Devolve o pacote de expediente com o bloco `sessao` no topo.
    `cadeira`: slug da cadeira.
    `pergunta`: corpo literal do turno do dono, enviado via STDIN para expediente montar.
    `chapeu`: força o slug do chapéu (ignora o roteador).
    `atualizar`: aceito e sem efeito desde arq:0097.
    `sessao_id`: uuid da sessão quando portado da conversa anterior; sem ele, sessao abrir cunha um novo.
    """
    negado = _autoriza("monta_sessao", "monta_sessao", "documento",
                       f"sessao:{cadeira or '-'}", DOM_PLATAFORMA)
    if negado:
        return negado
    # Regra (c) da porta (ordem do dono, 06/09/2026; arq:0101 §1): reabertura sem portar
    # o `sessao_id` não cunha outro — a porta nega, não adivinha. Abertura de verdade
    # traz o prompt do dono; id malformado quem recusa é `sessao abrir` (exit 2).
    if not sessao_id and not _primeiro_giro(pergunta):
        _audit(tool="monta_sessao", evento="sessao_id_ausente_na_reabertura", cadeira=cadeira)
        return {"erro": "sessao_id ausente numa reabertura — a fita deve portar o "
                        "`sessao_id` da primeira abertura (arq:0101 §1); a primeira "
                        "abertura envia a pergunta e NÃO envia `sessao_id`",
                "regra": "sessao"}

    t0 = time.monotonic()
    _q = _quem()  # async: no contexto da task MCP (#2911)
    _sub = _q.get("sub")
    if _sub == "-":
        _sub = None

    r = await anyio.to_thread.run_sync(_montar, cadeira, atualizar, chapeu, pergunta,
                                       sessao_id, _sub)

    _rot = (r.get("roteador") or {})
    _sessao_id = r.get("sessao_id") or (r.get("sessao") or {}).get("sessao_id")
    _delta = None

    if not r.get("erro") and _sessao_id:
        global _ULTIMA_SESSAO_ID
        _ULTIMA_SESSAO_ID = _sessao_id
        _sessao.set(_sessao_id)
        try:
            _rc().set("sessao:viva", _sessao_id, ex=TTL_SESSAO_S)
        except Exception:
            pass
        _cunhou = bool((r.get("sessao") or {}).get("cunhada_agora"))
        _oid = r.get("ordem_id") or (r.get("sessao") or {}).get("ordem_id") or "-"
        _audit(tool="sessao", evento="sessao_aberta",
               sujeito=_q.get("sujeito", "-"), cadeira=r.get("cadeira", "-"),
               ordem_id=_oid, sessao_id=_sessao_id,
               via="tool", cunhada=_cunhou)
        _delta = _delta_pecas(r, _sessao_id)   # R2: peça repetida na mesma sessão sai como aviso

    _audit(tool="monta_sessao", cadeira=cadeira, atualizar=atualizar,
           resolvida=r.get("cadeira"), erro=r.get("erro"),
           chapeu=(r.get("chapeu") or None),
           pergunta=(pergunta or None),
           roteador_via=_rot.get("via"), roteador_slug=_rot.get("slug"),
           dur_ms=round((time.monotonic() - t0) * 1000),
           sessao_id=_sessao_id or "-", **(_delta or {}))
    return r


# Registro tardio: o __doc__ é a descrição que o cliente lê, e ela precisa nomear o
# usuário e os caminhos DESTA instância. Substituir depois de registrar não adianta — o
# FastMCP copia a descrição no momento do mcp.tool().
_TOOLS = [run_command, read_file, write_file]
# monta_sessao só existe onde há personas: numa instância sem abertura publicada (osint)
# a tool não teria o que montar, e tool inútil no catálogo é contexto desperdiçado.
if PERSONAS.is_dir():
    _TOOLS.append(monta_sessao)

for _fn in _TOOLS:
    _fn.__doc__ = ((_fn.__doc__ or "").replace("@LOG@", str(LOG_DIR))
                   .replace("@BIN@", str(BIN_VERBOS)).replace("@TMP@", str(TMP_FITA))
                   .replace("@USER@", OPS_USER))
    mcp.tool()(_fn)


# --- Cápsula de verbos: tools derivadas do golden record (spec_capsula-de-verbos) ---
# A porta não tem lista própria de verbos: projeta o whitelist do núcleo via
# `acervo listar ferramental --tools` (§3.2). Uma tool por slug, nome = slug, descrição
# = coluna `descricao`, execução fina de `bin/<verbo> <ato> <args>` sem shell no meio.
# O que a tool acrescenta a `run_command` é SÓ a identidade da sessão (arq:0068 §1):
# `sessao_id` explícito -> `sessao:{id}` em Valkey -> PF_CADEIRA/PF_ORDEM_ID/PF_SESSAO.
# Flag: PF_TOOLS_VERBOS=0 desliga a projeção inteira (rollback: env + restart, sem
# tocar banco nem ADR). Leva 2 (mudança, acesso, infra, solicitação) fica atrás de
# PF_TOOLS_LEVA2=1 até seguranca bater a régua acao/tipo por tool (§3.6, §8).
# Geração na subida: verbo novo = `systemctl --user restart ops-mcp` (por-chamada
# fica pro teste de superfície, §3.2/§7.3).
TOOLS_VERBOS = os.environ.get("PF_TOOLS_VERBOS", "1") != "0"
TOOLS_LEVA2 = os.environ.get("PF_TOOLS_LEVA2", "0") == "1"
PF_GATE = os.environ.get("PF_GATE", "1") != "0"          # gate transparente (§4)
PF_TOOLS_LOTE = os.environ.get("PF_TOOLS_LOTE", "0") == "1" # chamada em lote (§5) — Leva 2
# Quem é leva 2 NÃO mora aqui: é o marcador `leva:2` na linha do slug em
# abertura/oficio-ferramental.md, que `acervo listar ferramental --tools` projeta em `leva`.


def _sessao_resolve(sessao_id: str | None) -> dict:
    """cadeira/ordem da sessão: SÓ o `sessao_id` que a fita porta, cunhado por `monta_sessao`.

    Se ausente/vazio/'-', tenta o default da sessão viva (Item 12 #3065).
    """
    if not sessao_id or sessao_id == "-":
        sessao_id = _sessao_viva()
    if sessao_id:
        sessao_id = _uuid_valido(sessao_id) or sessao_id   # legado 32-hex normaliza
    out = {"sessao_id": sessao_id or "-", "ordem_id": "-", "cadeira": ""}
    if not sessao_id or sessao_id == "-":
        return out
    try:
        raw = _rc().get(f"sessao:{sessao_id}")
        if raw:
            d = json.loads(raw)
            out["cadeira"] = d.get("cadeira") or ""
            out["ordem_id"] = d.get("ordem_id") or out["ordem_id"]
    except Exception as e:  # noqa: BLE001
        print(f"[valkey] sessao:{sessao_id} nao resolvida: {e!r}", file=sys.stderr, flush=True)
    return out


def _rlimits_filho():
    """Teto por verbo (TLPI cap. 36): processos e tamanho de arquivo. Nunca sobe o hard."""
    for lim, val in ((resource.RLIMIT_NPROC, 2048), (resource.RLIMIT_FSIZE, 2 * 1024 ** 3)):
        try:
            soft, hard = resource.getrlimit(lim)
            novo = val if hard == resource.RLIM_INFINITY else min(val, hard)
            resource.setrlimit(lim, (novo, hard))
        except (ValueError, OSError):
            pass

# Contrato item 2 (#3053): todo execve de verbo chamado com sessao_id válido injeta
# PF_CADEIRA/PF_SESSAO/PF_ORDEM_ID lidos da chave pelo _sessao_resolve (linhas 1431-1450).
def _run_verbo_blocking(argv: list, stdin: str | dict | list | None, timeout: int, ident: dict) -> dict:
    env = {**_env_subprocesso(), "PF_SESSAO": ident["sessao_id"], "PF_ORDEM_ID": ident["ordem_id"],
           "PF_CONTA": OPS_USER}
    if ident["cadeira"]:
        env["PF_CADEIRA"] = ident["cadeira"]
    d_cwd = CASA if CASA.is_dir() else Path.cwd()
    try:
        p = subprocess.Popen(argv, cwd=d_cwd, env=env, preexec_fn=_rlimits_filho,
                             stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    except OSError as e:
        return {"erro": str(e), "cwd": str(d_cwd)}
    # Defesa extra (#3124): quem chega aqui deveria vir normalizado dos pontos de
    # entrada (_stdin_texto na tool, no lote, em _item_de_lote) — mas se nao veio, nao
    # estoura no .encode() de um dict/list.
    if stdin is not None and not isinstance(stdin, str):
        stdin = _stdin_texto(stdin)
    try:
        stdout, stderr = p.communicate(input=(stdin.encode() if stdin is not None else None),
                                       timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait()
        return {"erro": f"timeout ({timeout}s) — grupo de processo morto", "cwd": str(d_cwd)}
    return {"exit_code": p.returncode, "stdout": _cap(stdout),
            "stderr": _cap(stderr), "cwd": str(d_cwd)}


def _faz_tool_verbo(slug: str, binario: str, descricao: str):
    async def _tool(ato: str = "", args: list[str] | None = None,
                    stdin: str | dict | list | None = None,
                    sessao_id: str | None = None, timeout: int = 120,
                    lote: list[dict] | None = None, encadeado: bool = False) -> dict:
        # #3124: o cliente MCP desserializa stdin JSON valido antes de chegar aqui; a
        # anotacao velha (str | None) fazia o pydantic recusar sem rodar nada.
        stdin = _stdin_texto(stdin)
        if lote and PF_TOOLS_LOTE:
            timeout = max(1, min(timeout, 600))
            ident = _sessao_resolve(sessao_id)
            lote_id = uuid.uuid4().hex[:8]

            # card:3149 passo 7: mesmo iterador de run_command; `encadeado` para a cadeia
            # no primeiro item fora de exit 0/1 (lote.py tem a regra).
            async def _roda(_i, item, _resultados):
                if not isinstance(item, dict):
                    return _recusa(slug, "item do lote deve ser {ato, args, stdin}")
                _ato = item.get("ato", "")
                _args = item.get("args") or []
                if isinstance(_args, (str, bytes)):
                    return _recusa(slug, "args deve ser lista de tokens, recebido string; use args: [ ... ]")
                _args = [str(a) for a in _args]
                _stdin = _stdin_texto(item.get("stdin"))
                _linha = " ".join([slug] + ([_ato] if _ato else []) + _args)
                negado_item = _autoriza(slug, "run_command", "comando", _linha, DOM_RUNTIME)
                if negado_item:
                    return negado_item
                argv = _argv_verbo(binario, _ato, _args)
                t0 = time.monotonic()
                r = await anyio.to_thread.run_sync(_run_verbo_blocking, argv, _stdin, timeout, ident)
                _perf = _perfil_verbo(slug, binario)
                r = _serve(r, tool=slug, alca=_linha, ident=ident, cauda=_perf["cauda"],
                           cosmetica=_cosmetica(_perf, _ato_efetivo(argv)))
                _audit(tool=slug, ato=_ato or None, args=" ".join(_args)[:CMD_CAP],
                       cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
                       ordem_id=ident["ordem_id"], exit_code=r.get("exit_code"), erro=r.get("erro"),
                       bytes_stdout=(r.get("stdout") or {}).get("bytes_total"),
                       dur_ms=round((time.monotonic() - t0) * 1000),
                       lote_id=lote_id, lote_n=_i, encadeado=encadeado or None,
                       **_campos_poda(r))
                return r

            out = await _lote.itera(list(lote), _roda, encadeado=encadeado, cap=CAP,
                                    bytes_de=_lote.bytes_stdout)
            if encadeado:
                _c = out["cadeia"]
                _audit(tool=slug, evento="lote_encadeado", lote_id=lote_id, lote_n=len(lote),
                       parou_em=_c["parou_em"], exit_code=_c["exit"],
                       nao_rodou=len(_c["nao_rodou"]), cadeira=ident["cadeira"] or None,
                       sessao_id=ident["sessao_id"], ordem_id=ident["ordem_id"])
            return out
        args = list(args or [])
        linha = " ".join([slug] + ([ato] if ato else []) + args)
        # Leva 1: mesma decisão do fallback (acao/tipo de run_command), auditada pelo
        # slug. acao/tipo POR tool é a régua de leva 2 (seguranca).
        negado = _autoriza(slug, "run_command", "comando", linha, DOM_RUNTIME)
        if negado:
            return negado
        timeout = max(1, min(timeout, 600))
        ident = _sessao_resolve(sessao_id)  # aqui: dentro da task da tool (#2911)
        argv = _argv_verbo(binario, ato, args)
        t0 = time.monotonic()
        r = await anyio.to_thread.run_sync(_run_verbo_blocking, argv, stdin, timeout, ident)
        # R4: a forma e a cauda saem do cabeçalho DESTE verbo. `descansar` é o caso que
        # nomeia a regra — batia o teto e era cortado só na cabeça, perdendo o veredito.
        _perf = _perfil_verbo(slug, binario)
        r = _serve(r, tool=slug, alca=linha, ident=ident, cauda=_perf["cauda"],
                   cosmetica=_cosmetica(_perf, _ato_efetivo(argv)))
        _audit(tool=slug, ato=ato or None, args=" ".join(args)[:CMD_CAP],
               cadeira=ident["cadeira"] or None, sessao_id=ident["sessao_id"],
               ordem_id=ident["ordem_id"], exit_code=r.get("exit_code"), erro=r.get("erro"),
               bytes_stdout=r.get("stdout", {}).get("bytes_total"),
               dur_ms=round((time.monotonic() - t0) * 1000), **_campos_poda(r))
        return r
    _tool.__name__ = slug.replace("-", "_")
    _tool.__doc__ = descricao
    return _tool


BINARIOS: dict = {}
SLUGS_RETIDOS: set = set()

def _gera_tools_verbos() -> list:
    """Lê a projeção do catálogo. Falha = zero tools derivadas e aviso; nunca aborta."""
    if not TOOLS_VERBOS or not PERSONAS.is_dir():
        return []
    try:
        cp = subprocess.run(["acervo", "listar", "ferramental", "--tools"],
                            env=_env_subprocesso(),  # projecao nao tem sujeito: nenhuma cadeira chumbada
                            capture_output=True, text=True, timeout=30,
                            cwd=CASA if CASA.is_dir() else None)
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
        BINARIOS[slug] = i["binario"]
        if int(i.get("leva") or 1) >= 2 and not TOOLS_LEVA2:
            retidas.append(slug)
            SLUGS_RETIDOS.add(slug)
            continue
        # Descrição = coluna `descricao` do golden record, SEM edição (spec §3.1): o
        # contrato comum (ato, args, sessao_id) está no ofício, uma vez, não 17.
        desc = i.get("descricao") or ""
        mcp.tool(name=slug, description=desc)(_faz_tool_verbo(slug, i["binario"], desc))
        servidas.append(slug)
    print(f"[capsula] tools derivadas servidas ({len(servidas)}): {' '.join(servidas)}"
          + (f" · leva 2 retido: {' '.join(retidas)}" if retidas else ""),
          file=sys.stderr, flush=True)
    return servidas


def _slugs_do_bin() -> set:
    """Fallback: verbos = executaveis em PF_HARNESS/bin sem prefixo _ e sem extensao.
    Nao depende de nenhum verbo (o gerador chama `acervo`, que pode estar quebrado —
    foi o que derrubou a porta em 08/09: refatoracao arq:0106 mudou a gramatica do
    acervo, `acervo listar ferramental` passou a recusar, gerador caiu em [] e a
    porta subiu sem verbo nenhum). Aqui a fonte e o filesystem, imune a isso."""
    binp = PF_HARNESS / "bin"
    if not binp.is_dir():
        return set()
    slugs = set()
    for p in binp.iterdir():
        n = p.name
        if n.startswith("_") or "." in n or not p.is_file():
            continue
        if os.access(p, os.X_OK):
            slugs.add(n)
            BINARIOS.setdefault(n, str(p))
    return slugs

TOOLS_DERIVADAS = _gera_tools_verbos()
SLUGS_SERVIDOS = set(TOOLS_DERIVADAS)
if not SLUGS_SERVIDOS:
    # gerador veio vazio (acervo quebrado, etc): degrada, nao derruba. run_command
    # resolve verbo pelo bin/; a projecao de tools MCP fica degradada ate o gerador
    # voltar, mas a porta NUNCA sobe cega recusando todo verbo.
    SLUGS_SERVIDOS = _slugs_do_bin()
    print(f"[capsula] gerador vazio — fallback bin/ ({len(SLUGS_SERVIDOS)} verbos): "
          f"{' '.join(sorted(SLUGS_SERVIDOS))}", file=sys.stderr, flush=True)


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
# fila e devolvia 500 sem dizer por que. Medido no ensaio de 13/08/2026. E o bin
# servido (PF_BIN, default a release).
FILA_BIN = BIN_VERBOS


def _fila_mod():
    """Levanta ModuleNotFoundError com o caminho tentado — quem chama devolve 503
    nomeando o defeito, em vez de 500 nomeando nada."""
    # arq:0110 §1: ajudante mora em bin/_<verbo>/ — o modulo e bin/_fila/streams.py.
    fila_dir = str(FILA_BIN / "_fila")
    if fila_dir not in sys.path:
        sys.path.insert(0, fila_dir)
    try:
        import streams as fila_streams
    except ImportError as e:
        raise ModuleNotFoundError(
            f"modulo da fila nao encontrado em {fila_dir} — aponte PF_BIN") from e
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

    # ROTA FOSSIL (arq:0101 §2): serve a classe «externo/DMZ» de um modelo de seguranca
    # que o seg:0011 substituiu em 15/08 — sob ele a unidade de segregacao e a CONTA, a
    # persona e inquilina dela, e nao ha eixo «externo». Sai quando quem a usa
    # (jaiminho-fabrica) abrir por `monta_sessao`; migrar ANTES de remover, sob pena de
    # 404 em 5.523 aberturas/periodo. Enquanto isso, NAO cunha entidade-sessao: devolve
    # ordem_id ao chamador e nao escreve join nenhum — quem cunha sessao e monta_sessao.
    _oid = "o" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    pac["ordem_id"] = _oid
    pac["aviso_rota"] = ("rota fóssil (arq:0101 §2) — abra por `monta_sessao`, que cunha "
                         "`sessao_id`; esta rota sai assim que o último cliente migrar")
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
        proc = subprocess.run([str(BIN_VERBOS / "mesa"), "anota", quem],
                              input=nota, capture_output=True, text=True, timeout=15,
                              env={**_env_subprocesso(), "PF_CADEIRA": quem})
        if proc.returncode == 0:
            return {"ok": True, "slot": quem, "saida": proc.stdout.strip()}
        return {"ok": False, "erro": (proc.stderr or proc.stdout).strip()[:300]}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}


def _giro_carrega(sessao_id: str, cadeira: str, chapeu, giro: list) -> dict:
    """Carrega os 3 primeiros giros auto-relatados em sessao.giro pelo verbo
    bin/_sessao/giro-carga.py — nunca cliente de banco proprio (ops-mcp roda no venv ops
    da release, sem driver de banco; mesma razao de _anota_mesa)."""
    if not sessao_id:
        return {"ok": False, "erro": "sem sessao_id"}
    payload = json.dumps({"sessao_id": sessao_id, "cadeira": cadeira,
                          "chapeu": chapeu, "giro": giro})
    try:
        proc = subprocess.run([str(BIN_VERBOS / "_sessao" / "giro-carga.py")],
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
