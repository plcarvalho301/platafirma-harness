"""jaiminho-server — servidor MCP do colaborador externo.

Por que existe: o `ops-server` e o MCP das cadeiras (run_command, arquivo, mesa,
fila). Colaborador externo nao e cadeira e nao tem o que fazer la dentro — servir
os dois publicos pelo mesmo processo obriga toda tool nova a lembrar que existe um
externo do outro lado. Aqui a superficie E o recorte: so o que o externo alcanca
existe neste servidor.

Superficie: MCP sobre HTTP em /mcp, alcancado pela ponte do container dele. Sem
porta publicada e sem rota no tunel — quem chama e o container vizinho, nao a
internet.

PEP: identidade e o JWT do realm; a decisao e do PDP embarcado, lendo o mesmo PAP
(`politica-acesso/`) que o ops-server le. Falha de carga NEGA — politica ilegivel e
defeito nosso, nao autorizacao.

Colecao: `firma` e forcada aqui, no servidor. O parametro do cliente nao entra na
chamada ao motor: `acervo:pessoal/*` e negativa dura de seg:0009 item 4, e negativa
que depende do cliente nao pedir nao e negativa.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.routing import Route

PDP_DIR = Path(os.environ.get("PDP_DIR", "/opt/pf/politica-acesso"))
LOG_DIR = Path(os.environ.get("JAIMINHO_LOG_DIR", "/var/log/jaiminho"))
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma")
OIDC_JWKS_URL = os.environ.get(
    "OIDC_JWKS_URL", f"{OIDC_ISSUER}/protocol/openid-connect/certs")
# Audiencia: hoje o client do Jaiminho emite token para `ops-mcp`. Audiencia propria
# deste servidor e ato no realm (dominio de identidade, que nao e meu) — ate la,
# aceitar a mesma audiencia e o que faz o token existente valer aqui.
OIDC_AUDIENCE = os.environ.get("OIDC_AUDIENCE", "ops-mcp")

RAG_API_URL = os.environ.get("RAG_API_URL", "http://rag-api:8000").rstrip("/")
RAG_API_TOKEN = os.environ.get("RAG_API_TOKEN", "")
RAG_TIMEOUT = float(os.environ.get("RAG_TIMEOUT", "120"))

COLECAO = "firma"          # unica colecao alcancavel por externo (seg:0009 item 4)
DOM_ACERVO = "plataforma-acervo"
TIPO_ACERVO = "acervo"
ACAO = "rag_buscar"

_pdp: dict = {"carimbo": None, "politica": None, "sujeitos": None, "erro": "nao carregada"}
_jwks_cli = None


# --- auditoria -------------------------------------------------------------
def _audit(**campos):
    linha = {"em": datetime.now(timezone.utc).isoformat(timespec="seconds"), **campos}
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        alvo = LOG_DIR / f"{datetime.now(timezone.utc):%Y-%m}.jsonl"
        with alvo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False, default=str)[:8000] + "\n")
    except OSError:
        print(json.dumps(linha, ensure_ascii=False, default=str), file=sys.stderr)


# --- identidade ------------------------------------------------------------
def _jwks():
    global _jwks_cli
    if _jwks_cli is None:
        from jwt import PyJWKClient
        _jwks_cli = PyJWKClient(OIDC_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks_cli


def _sujeito_do_jwt(header: str) -> dict:
    """{} = nao e JWT valido do realm. Nao ha rota de emergencia aqui: o token
    estatico e a mao do dono quando o realm cai, e o dono nao entra por esta porta."""
    if not header.startswith("Bearer "):
        return {}
    tok = header[len("Bearer "):].strip()
    if tok.count(".") != 2:
        return {}
    try:
        import jwt
        claims = jwt.decode(
            tok, _jwks().get_signing_key_from_jwt(tok).key,
            algorithms=["RS256", "ES256"], audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER,
            options={"require": ["exp", "iat", "sub"]})
        return {"sujeito": claims.get("preferred_username") or claims.get("sub"),
                "sub": claims.get("sub"), "azp": claims.get("azp", "-")}
    except Exception as e:                                   # noqa: BLE001
        _audit(evento="jwt_recusado", motivo=type(e).__name__)
        return {}


def _quem() -> dict:
    """Identidade de dentro da tool: o contexto do FastMCP e a unica fonte honesta."""
    try:
        req = getattr(mcp.get_context().request_context, "request", None)
        if req is not None:
            return _sujeito_do_jwt(req.headers.get("authorization", ""))
    except Exception:                                        # noqa: BLE001
        pass
    return {}


# --- PDP -------------------------------------------------------------------
def _carrega_politica() -> dict:
    """PAP e projecao de sujeito, relidos quando o mtime de um dos dois muda —
    merge no PAP vale sem restart, igual ao ops-server."""
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
        if str(PDP_DIR) not in sys.path:
            sys.path.insert(0, str(PDP_DIR))
        import yaml
        from pdp import Politica
        pol = Politica.de_arquivo(pol_f)
        suj = (yaml.safe_load(suj_f.read_text(encoding="utf-8")) or {}).get("sujeitos") or {}
        _pdp.update(carimbo=carimbo, politica=pol, sujeitos=suj, erro=None)
    except Exception as e:                                   # noqa: BLE001
        _pdp.update(carimbo=carimbo, politica=None, sujeitos=None,
                    erro=f"{type(e).__name__}: {e}")
    return _pdp


def _lista(v) -> list:
    if not v:
        return []
    return [x for x in ([v] if isinstance(v, str) else list(v)) if x]


def _autoriza(dominios: list) -> dict | None:
    """None = pode seguir. dict = negativa auditada, pronta para devolver.

    Um recurso por dominio pedido, e qualquer negativa nega o pedido inteiro: pedido
    de tres dominios com concessao de dois nao vira busca em dois — vira negativa, e
    o chamador sabe o que pedir de novo. Sem dominio, o alvo e o corpus da colecao,
    que e o que ele esta de fato pedindo.
    """
    est = _carrega_politica()
    if est["erro"]:
        _audit(evento="pep_sem_politica", motivo=est["erro"])
        return {"erro": "politica de acesso indisponivel", "detalhe": est["erro"]}

    ident = _quem()
    quem = ident.get("sujeito") or ""
    if not quem:
        _audit(evento="negado", motivo="sem identidade")
        return {"erro": "nao autenticado"}

    from pdp import Recurso, Sujeito, decide
    atrib = (est["sujeitos"] or {}).get(quem) or {}
    s = Sujeito(id=quem, natureza=atrib.get("natureza"),
                papeis=tuple(atrib.get("papeis") or ()),
                dominios=tuple(atrib.get("dominios") or ()),
                habilitacao=atrib.get("habilitacao", "publico"))

    alvos = [f"acervo:{COLECAO}/{d}/*" for d in dominios] or [f"acervo:{COLECAO}/*"]
    for alvo in alvos:
        d = decide(s, ACAO, Recurso(tipo=TIPO_ACERVO, id=alvo, dominio=DOM_ACERVO),
                   est["politica"])
        if not d.permitido:
            _audit(evento="negado", sujeito=quem, sobre=alvo, regra=d.regra,
                   motivo=d.motivo)
            return {"erro": "negado pela politica de acesso", "sobre": alvo,
                    "regra": d.regra, "motivo": d.motivo}
    _audit(evento="permitido", sujeito=quem, sobre=alvos, regra=ACAO)
    return None


# --- motor -----------------------------------------------------------------
_cli = httpx.Client(timeout=RAG_TIMEOUT)


def _motor(rota: str, corpo: dict | None = None, metodo: str = "POST") -> dict:
    """Erro de rede vira CAMPO, nao excecao: quem chama tem de conseguir ler a falha
    e seguir, em vez de ver a sessao inteira quebrar."""
    if not RAG_API_TOKEN:
        return {"erro": "RAG_API_TOKEN ausente neste servidor: busca indisponivel"}
    try:
        r = _cli.request(metodo, f"{RAG_API_URL}{rota}", json=corpo,
                         headers={"Authorization": f"Bearer {RAG_API_TOKEN}"})
    except Exception as e:                                   # noqa: BLE001
        return {"erro": f"motor inalcancavel: {type(e).__name__}", "detalhe": str(e)[:300]}
    if r.status_code == 503:
        return {"erro": "o acervo esta aquecendo (o embedder carrega uma vez por "
                        "processo, ~25 s). Tente de novo em instantes."}
    if r.status_code >= 400:
        return {"erro": f"motor devolveu {r.status_code}", "detalhe": r.text[:400]}
    return r.json()


# Protecao de DNS rebinding LIGADA, com os hosts nomeados: quem chama e sempre a
# ponte do contêiner vizinho, por alias de rede conhecido. O ops-server desliga a
# protecao porque atende cliente de fora; aqui a lista de chamadores e fechada, e
# fechada ela fica.
_HOSTS = [h for h in os.environ.get(
    "HOSTS_PERMITIDOS", "jaiminho-server:8000,jaiminho-server,127.0.0.1:8000,localhost:8000"
).split(",") if h]

mcp = FastMCP("jaiminho", stateless_http=True,
              transport_security=TransportSecuritySettings(
                  allowed_hosts=_HOSTS,
                  allowed_origins=[f"http://{h}" for h in _HOSTS]))


@mcp.tool()
def rag_buscar(pergunta: str | list[str], dominio: str | list[str] = "",
               subdominio: str | list[str] = "", frente: str | list[str] = "",
               k: int = 8, texto: str = "secao", rerank: bool = False) -> dict:
    """Busca semantica no acervo bibliografico de trabalho da PlataFirma.

    E o TEXTO das obras curadas — livros, guias, frameworks e normas de terceiros —,
    indexado trecho a trecho. NAO alcanca a wiki (o que a firma decidiu e o que ela
    faz) nem a colecao pessoal do titular.

    `pergunta`: linguagem natural. Cite o codigo exato quando houver ("clausula
    6.1.3", "AC-2") — o braco de identificador crava o trecho certo e a fonte volta
    com `codigo_exato: true`. Aceita LISTA de ate 4 perguntas quando o assunto tem
    lados separados: cada uma recupera sozinha e os rankings fundem.

    `dominio`/`subdominio`/`frente`: recorte por faceta (OR dentro do eixo, E entre
    eixos). Confira em `rag_facetas` antes de filtrar — faceta valida e despovoada
    devolve zero sem erro, e isso e indistinguivel de ausencia de cobertura.

    `texto`: "secao" (default) traz a secao inteira de cada fonte; "trecho" so o
    pedaco que casou; "nenhum" so metadado, para a pergunta "o corpus cobre X?".

    `rerank`: liga o revisor cross-encoder — custa ~325 ms e vale em pergunta
    conceitual, em que a ORDEM do topo decide o que voce vai citar; nao vale em
    busca por codigo exato.

    Quem redige e voce: toda frase cita [n], e so serve fonte que trate do conceito
    EXATO perguntado. Cobertura "fraca" sem nenhuma fonte `codigo_exato` quer dizer
    que o corpus provavelmente nao cobre — diga isso, nao responda pelo vizinho.
    """
    negativa = _autoriza(_lista(dominio))
    if negativa:
        return negativa
    return _motor("/search", {
        "pergunta": pergunta, "dominio": dominio, "subdominio": subdominio,
        "frente": frente, "colecao": COLECAO, "k": k, "texto": texto,
        "rerank": rerank,
    })


@mcp.tool()
def rag_facetas() -> dict:
    """Valores validos de `dominio`, `subdominio` e `frente` do acervo, com quantas
    obras e trechos cada um tem DE VERDADE.

    Chame antes de filtrar `rag_buscar`: valor legitimo com corpus vazio devolve
    zero sem erro nenhum, e e esse modo de falha que esta tool corta. `obras: 0`
    quer dizer "valor valido, corpus vazio nele", diferente de "valor nao existe".
    A colecao nao entra: o alcance externo e a colecao de trabalho, e so ela.
    """
    negativa = _autoriza([])
    if negativa:
        return negativa
    d = _motor("/facets", metodo="GET")
    if isinstance(d, dict):
        d.pop("colecao", None)
    return d


async def _health(_req):
    est = _carrega_politica()
    return JSONResponse({"ok": est["erro"] is None,
                         "politica": est["erro"] or "carregada",
                         "motor": RAG_API_URL, "colecao": COLECAO,
                         "medido_em": int(time.time())})


app = mcp.streamable_http_app()
app.router.routes.append(Route("/health", _health))
