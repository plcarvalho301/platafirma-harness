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

Colecao: NAO ha filtro de colecao nesta superficie. Ordem do dono de 20/08/2026:
qualquer recorte de acesso ao RAG e exclusivamente authz policy assinada por ele, no
PAP, decidida pelo PDP — nao constante no servidor de recurso. O que o externo alcanca
do acervo e o que a politica permitir, e nada mais e nada menos.
"""
import json
import os
import sys
import time
from urllib.parse import quote as urllib_quote
from datetime import datetime, timezone
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

PDP_DIR = Path(os.environ.get("PDP_DIR", "/opt/pf/politica-acesso"))
if str(PDP_DIR) not in sys.path:
    sys.path.insert(0, str(PDP_DIR))
from identidade import _jwks, _sujeito_do_jwt

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

DOM_ACERVO = "plataforma-acervo"
TIPO_ACERVO = "acervo"
ACAO = "rag_buscar"

# --- wiki ------------------------------------------------------------------
# O wiki-mcp autentica por segredo estatico e NAO tem PEP: quem tem o token tem
# edit_page e upload_file junto. Por isso o token nao atravessa a ponte e nao mora
# no contêiner dele — mora aqui, e o externo so alcanca a wiki pelas duas tools de
# leitura abaixo, que passam por este PEP como qualquer outra.
WIKI_MCP_URL = os.environ.get("WIKI_MCP_URL", "http://mcp:8000/mcp")
WIKI_MCP_TOKEN = os.environ.get("WIKI_MCP_TOKEN", "")
WIKI_TIMEOUT = float(os.environ.get("WIKI_TIMEOUT", "60"))
DOM_WIKI = "plataforma-wiki"
TIPO_WIKI = "wiki"

# Repo: o externo escreve codigo PARA a PlataFirma, e precisa LER o codigo dela para
# escrever no padrao da casa (ordem do dono, 20/08/2026). Somente-leitura por
# construcao: as tres tools abaixo batem no ESPELHO do ref remoto, pelo wiki-mcp.
# Escrever, push e git local sao `run_command`, tipo `comando`, negado a este papel.
DOM_REPO = "plataforma-repo"
TIPO_REPO = "repo"
ACAO_REPO = "repo_ler"

# Recorte de namespace da wiki, forcado no servidor: so o namespace
# principal, que e o acervo de conceitos e obras. `PlataFirma:` (decisao, org,
# metodo), `Operar:` (runbook) e `Frente:` (trabalho em curso) sao a camada
# interna e nao se concedem a externo. No ns principal o titulo nao tem ":", e e
# essa a regra — dura, e nao dependente de o cliente pedir direito.
NS_INTERNOS = ("PlataFirma", "Operar", "Frente", "Category", "File", "Template",
               "Help", "User", "MediaWiki", "Talk", "Special", "Property")

_pdp: dict = {"carimbo": None, "politica": None, "sujeitos": None, "erro": "nao carregada"}


# --- auditoria -------------------------------------------------------------
# GUARDA DE REENTRANCIA, e nao e zelo: sem ela a porta CAI em todo token invalido.
# O ciclo e `_audit` -> `_quem` -> `_sujeito_do_jwt` -> (recusa chama) `auditor=_audit`
# -> `_quem` -> ... Reproduzido em 25/08/2026 na revisao do #2287: RecursionError
# depois de 67 voltas, em `ExigeJWT.dispatch` com Bearer malformado. O ops-server nao
# tem o defeito porque la `_audit` so resolve identidade quando `tool != "-"`, e a
# linha de recusa sai com `tool="-"` — a guarda existe por acidente de formato. Aqui
# ela e explicita, porque acidente nao e controle.
_em_audit = False


def _audit(**campos):
    global _em_audit
    if _em_audit:
        ident = {}
    else:
        _em_audit = True
        try:
            ident = _quem()
        finally:
            _em_audit = False
    linha = {"em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             **ident, **campos}
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        alvo = LOG_DIR / f"{datetime.now(timezone.utc):%Y-%m}.jsonl"
        with alvo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False, default=str)[:8000] + "\n")
    except OSError:
        print(json.dumps(linha, ensure_ascii=False, default=str), file=sys.stderr)


# --- identidade ------------------------------------------------------------
def _quem() -> dict:
    """Identidade de dentro da tool: o contexto do FastMCP e a unica fonte honesta."""
    try:
        req = getattr(mcp.get_context().request_context, "request", None)
        if req is not None:
            return _sujeito_do_jwt(req.headers.get("authorization", ""),
                                   auditor=_audit, jwks_url=OIDC_JWKS_URL,
                                   audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER)
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
        # Divergencia de vocabulario NAO derruba o servidor: o PDP ja nega sozinho.
        # O que faltava era o typo aparecer COMO typo, em vez de virar negativa
        # silenciosa por intersecao.
        vocab = set(pol.dominios)
        for d in (DOM_ACERVO, DOM_WIKI, DOM_REPO, DOM_DRIVE):
            if d not in vocab:
                _audit(evento="pep_vocabulario_divergente", onde="server", dominio=d)
        for nome, atrib in (suj or {}).items():
            for d in (atrib or {}).get("dominios") or ():
                if d not in vocab:
                    _audit(evento="pep_vocabulario_divergente",
                           onde="sujeitos.yaml", sujeito=nome, dominio=d)
    except Exception as e:                                   # noqa: BLE001
        _pdp.update(carimbo=carimbo, politica=None, sujeitos=None,
                    erro=f"{type(e).__name__}: {e}")
    return _pdp


def _lista(v) -> list:
    if not v:
        return []
    return [x for x in ([v] if isinstance(v, str) else list(v)) if x]


def _autoriza(acao: str, tipo: str, dominio_pdp: str, alvos: list) -> dict | None:
    """None = pode seguir. dict = negativa auditada, pronta para devolver.

    Um recurso por alvo pedido, e qualquer negativa nega o pedido inteiro: pedido de
    tres dominios com concessao de dois nao vira busca em dois — vira negativa, e o
    chamador sabe o que pedir de novo.

    A acao, o tipo e o dominio entram por parametro porque a superficie tem duas
    materias com concessoes separadas — acervo e wiki. Fundi-las num PEP so faria a
    concessao de uma valer para a outra, que e exatamente o que seg:0009 nao quer.
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

    for alvo in alvos:
        d = decide(s, acao, Recurso(tipo=tipo, id=alvo, dominio=dominio_pdp),
                   est["politica"])
        if not d.permitido:
            _audit(evento="negado", sujeito=quem, acao=acao, sobre=alvo, regra=d.regra,
                   motivo=d.motivo)
            return {"erro": "negado pela politica de acesso", "sobre": alvo,
                    "regra": d.regra, "motivo": d.motivo}
    _audit(evento="permitido", sujeito=quem, acao=acao, sobre=alvos)
    return None


def _autoriza_acervo(dominios: list) -> dict | None:
    """Sem dominio, o alvo e o corpus inteiro — que e o que ele esta pedindo."""
    alvos = [f"acervo:{d}/*" for d in dominios] or ["acervo:*"]
    return _autoriza(ACAO, TIPO_ACERVO, DOM_ACERVO, alvos)


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
    indexado trecho a trecho. Sem recorte de colecao: alcanca todo o acervo indexado
    que a politica de acesso permitir. Nao alcanca a wiki: o que a firma decidiu e como
    ela nomeia esta em `wiki_buscar`, que e outra materia e outra concessao.

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
    negativa = _autoriza_acervo(_lista(dominio))
    if negativa:
        return negativa
    return _motor("/search", {
        "pergunta": pergunta, "dominio": dominio, "subdominio": subdominio,
        "frente": frente, "k": k, "texto": texto,
        "rerank": rerank,
    })


@mcp.tool()
def rag_facetas() -> dict:
    """Valores validos de `dominio`, `subdominio` e `frente` do acervo, com quantas
    obras e trechos cada um tem DE VERDADE.

    Chame antes de filtrar `rag_buscar`: valor legitimo com corpus vazio devolve
    zero sem erro nenhum, e e esse modo de falha que esta tool corta. `obras: 0`
    quer dizer "valor valido, corpus vazio nele", diferente de "valor nao existe".
    """
    negativa = _autoriza_acervo([])
    if negativa:
        return negativa
    return _motor("/facets", metodo="GET")


# --- wiki: cliente MCP minimo ----------------------------------------------
# O wiki-mcp e MCP COM sessao (nao stateless): initialize devolve `mcp-session-id`
# no header, e todo POST seguinte tem de carrega-lo. Cliente MCP completo aqui seria
# async dentro de tool sincrona; o handshake sao tres POSTs e cabe em httpx.
_wiki_cli = httpx.Client(timeout=WIKI_TIMEOUT)
_wiki_sessao: dict = {"id": None}
_WIKI_CAB = {"Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}


def _wiki_sse(texto: str) -> dict:
    """A resposta vem como SSE de um evento so: a carga esta na linha `data:`."""
    for linha in texto.splitlines():
        if linha.startswith("data:"):
            return json.loads(linha[5:].strip())
    return json.loads(texto) if texto.strip().startswith("{") else {}


def _wiki_abre_sessao() -> str:
    cab = {**_WIKI_CAB, "Authorization": f"Bearer {WIKI_MCP_TOKEN}"}
    r = _wiki_cli.post(WIKI_MCP_URL, headers=cab, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "jaiminho-server", "version": "1"}}})
    r.raise_for_status()
    sid = r.headers.get("mcp-session-id", "")
    if not sid:
        raise RuntimeError("wiki-mcp nao devolveu mcp-session-id")
    _wiki_cli.post(WIKI_MCP_URL, headers={**cab, "mcp-session-id": sid},
                   json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    _wiki_sessao["id"] = sid
    return sid


def _wiki(tool: str, args: dict, _renova: bool = True) -> dict:
    """Erro vira CAMPO, nunca excecao — mesma regra de `_motor`."""
    if not WIKI_MCP_TOKEN:
        return {"erro": "WIKI_MCP_TOKEN ausente neste servidor: wiki indisponivel"}
    try:
        sid = _wiki_sessao["id"] or _wiki_abre_sessao()
        cab = {**_WIKI_CAB, "Authorization": f"Bearer {WIKI_MCP_TOKEN}",
               "mcp-session-id": sid}
        r = _wiki_cli.post(WIKI_MCP_URL, headers=cab, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool, "arguments": args}})
    except Exception as e:                                   # noqa: BLE001
        return {"erro": f"wiki inalcancavel: {type(e).__name__}", "detalhe": str(e)[:300]}
    # Sessao expira do lado de la e volta 400/404: reabre UMA vez e repete. Sem isso,
    # o primeiro giro depois do restart da wiki falharia para o chamador.
    if r.status_code in (400, 404) and _renova:
        _wiki_sessao["id"] = None
        return _wiki(tool, args, _renova=False)
    if r.status_code >= 400:
        return {"erro": f"wiki devolveu {r.status_code}", "detalhe": r.text[:300]}
    corpo = _wiki_sse(r.text)
    if "error" in corpo:
        return {"erro": "wiki recusou a chamada",
                "detalhe": str(corpo["error"])[:300]}
    res = corpo.get("result", {})
    if "structuredContent" in res:
        return res["structuredContent"]
    # Sem `structuredContent`, a carga vem como texto JSON dentro de content[0].
    # Repassar o envelope faria o Jaiminho receber JSON dentro de JSON dentro de
    # content — desembrulhar aqui e o que mantem a tool com cara de tool.
    conteudo = res.get("content") or []
    if conteudo and isinstance(conteudo[0], dict) and "text" in conteudo[0]:
        try:
            return json.loads(conteudo[0]["text"])
        except (ValueError, TypeError):
            return {"texto": conteudo[0]["text"]}
    return res


def _interno(titulo: str) -> bool:
    prefixo = str(titulo).split(":", 1)[0].strip()
    return ":" in str(titulo) and prefixo in NS_INTERNOS


@mcp.tool()
def wiki_buscar(pergunta: str, k: int = 10) -> dict:
    """Busca por texto livre nas paginas de CONCEITO da wiki da PlataFirma.

    A wiki e o que a firma decidiu e como ela nomeia as coisas — distinta do acervo,
    que e o texto de obra de terceiro. Use esta tool quando a pergunta for sobre o
    vocabulario ou o conceito como a firma o define; use `rag_buscar` quando for
    sobre o que a norma ou o autor dizem.

    Alcance: o namespace principal, que e o acervo de conceitos, dominios e obras.
    A camada interna — decisao, org, metodo, runbook, trabalho em curso — NAO entra,
    e o corte e feito aqui no servidor: pagina interna nem aparece no resultado.

    Devolve titulo e trecho. Para o texto da pagina, chame `wiki_ler` com o titulo.
    """
    negativa = _autoriza("wiki_ler", TIPO_WIKI, DOM_WIKI, ["wiki:principal/*"])
    if negativa:
        return negativa
    # Pede folga na busca porque o filtro de namespace corta depois: pedir k e
    # filtrar devolveria menos que k sem que o chamador entendesse por que.
    d = _wiki("search_pages", {"query": pergunta, "limit": max(k * 3, 20)})
    if "erro" in d:
        return d
    achados = d.get("result", d) if isinstance(d, dict) else d
    if not isinstance(achados, list):
        return {"erro": "wiki devolveu formato inesperado", "detalhe": str(d)[:300]}
    abertos = [p for p in achados if not _interno(p.get("title", ""))]
    return {"paginas": abertos[:k], "alcance": "namespace principal da wiki"}


@mcp.tool()
def wiki_ler(titulos: str | list[str]) -> dict:
    """Texto de uma pagina de conceito da wiki, pelo titulo exato.

    Titulo sai de `wiki_buscar`. Aceita lista. Pagina da camada interna
    (`PlataFirma:`, `Operar:`, `Frente:`) volta recusada e nomeada — a recusa e
    declarada, nao silencio, para voce saber que a pagina existe e nao e sua.
    """
    negativa = _autoriza("wiki_ler", TIPO_WIKI, DOM_WIKI, ["wiki:principal/*"])
    if negativa:
        return negativa
    pedidos = _lista(titulos)
    if not pedidos:
        return {"erro": "sem titulo: passe o titulo exato devolvido por wiki_buscar"}
    fora = [t for t in pedidos if _interno(t)]
    abertos = [t for t in pedidos if not _interno(t)]
    if not abertos:
        return {"erro": "fora do alcance: camada interna da wiki", "recusados": fora}
    d = _wiki("get_page", {"titles": abertos, "follow_redirects": True})
    if "erro" in d:
        return d
    return {"paginas": d.get("result", d), "recusados": fora} if fora else \
           {"paginas": d.get("result", d)}


# --- repositorios ----------------------------------------------------------
# Espelho somente-leitura do ref remoto, servido pelo mesmo wiki-mcp. O PEP decide
# por repositorio: o alvo e `repo:<nome>`, e a concessao de hoje nomeia
# `platafirma-*` e `modulo-*`. Repo fora disso volta negado e NOMEADO — recusa
# declarada, para o chamador saber que existe e nao e dele.


def _autoriza_repo(repo: str) -> dict | None:
    return _autoriza(ACAO_REPO, TIPO_REPO, DOM_REPO, [f"repo:{repo}"])


@mcp.tool()
def repo_mapa(repo: str, ref: str = "main", path_prefix: str = "",
              glob: str = "", limit: int = 500) -> dict:
    """Mapa de arquivos de um repositorio da PlataFirma, num ref (branch, tag ou SHA).

    Use ANTES de `repo_ler`: e daqui que sai o caminho exato. `path_prefix` restringe
    a subarvore, `glob` filtra por padrao (ex. "*.py"). A resposta traz o SHA lido, e
    e esse SHA que voce cita — ref movel muda debaixo de voce entre uma chamada e a
    seguinte.

    Alcance: leitura do espelho do ref REMOTO. Nao ha working tree, nao ha commit e
    nao ha push por aqui; entrega de codigo continua saindo pelo card e pelo Drive.
    """
    negativa = _autoriza_repo(repo)
    if negativa:
        return negativa
    return _wiki("repo_tree", {"repo": repo, "ref": ref, "path_prefix": path_prefix,
                               "glob": glob, "limit": limit})


@mcp.tool()
def repo_ler(repo: str, paths: str | list[str], ref: str = "main",
             offset: int = 0, max_bytes: int = 40000) -> dict:
    """Conteudo de ate 20 arquivos de um repositorio, num ref.

    Caminho sai de `repo_mapa` ou de `repo_buscar`. Arquivo inexistente ou binario
    volta com o erro preenchido, nunca omitido — omitir faria "nao existe" e "nao
    li" virarem a mesma resposta.

    Truncagem sempre declarada (`truncated`, `bytes_total`, `next_offset`, em bytes).
    Leia o teste junto com o codigo que ele julga: na PlataFirma o contrato de um
    verbo esta no teste, e codigo novo que ignora o teste em vigor volta no review.
    """
    negativa = _autoriza_repo(repo)
    if negativa:
        return negativa
    return _wiki("repo_read", {"repo": repo, "paths": paths, "ref": ref,
                               "offset": offset, "max_bytes": max_bytes})


@mcp.tool()
def repo_buscar(repo: str, padrao: str, ref: str = "main", path_glob: str = "",
                ignore_case: bool = False, context: int = 2, limit: int = 100) -> dict:
    """Busca por regex no conteudo de um ref do repositorio (git grep de verdade).

    E a tool para achar arquivo sem saber o nome: quem chama o verbo, onde a
    constante nasce, que teste cobre a regra. `padrao` e regex POSIX ESTENDIDA
    (ERE, `git grep -E`) — `a|b`, `(x)+`, `?`, `{n,m}` valem SEM escape, e escapar a
    alternacao a torna caractere literal. Zero resultado nao e erro.
    """
    negativa = _autoriza_repo(repo)
    if negativa:
        return negativa
    return _wiki("repo_grep", {"repo": repo, "pattern": padrao, "ref": ref,
                               "path_glob": path_glob, "ignore_case": ignore_case,
                               "context": context, "limit": limit})


# --- google drive ----------------------------------------------------------
# Por que existe: o externo nao tem wiki, nao tem git e nao tem rede com o dono.
# A pasta do Drive e a area de transferencia de MAO UNICA — ele deposita, o dono le.
#
# Escopo: `drive.file`, que e o recorte do PROPRIO Google — o token so alcanca
# arquivo criado por este app. Nao e promessa nossa: o que o dono guarda no resto
# do Drive dele nao existe para esta credencial, e nenhum defeito de codigo aqui
# muda isso. O segundo cadeado, esse sim nosso, e a ancestralidade em PASTA_RAIZ:
# arquivo que o app criou e foi movido para fora da pasta deixa de ser alcancavel.
#
# O token NAO atravessa a ponte e nao mora no container dele — mora aqui, por bind
# read-only, e a superficie dele sao as sete tools abaixo, todas pelo mesmo PEP.
GOOGLE_TOKEN_F = Path(os.environ.get("GOOGLE_TOKEN", "/opt/pf/google/token.json"))
PASTA_RAIZ = os.environ.get("GDRIVE_PASTA", "")
DOM_DRIVE = "plataforma-drive"
TIPO_DRIVE = "drive"
DRIVE_TIMEOUT = float(os.environ.get("DRIVE_TIMEOUT", "60"))

_MIMES = {
    "doc": "application/vnd.google-apps.document",
    "planilha": "application/vnd.google-apps.spreadsheet",
    "pasta": "application/vnd.google-apps.folder",
    "texto": "text/plain",
    "markdown": "text/markdown",
    "csv": "text/csv",
}
# Google Doc/Sheet nao tem bytes: sai por export. O resto baixa como esta.
_EXPORTA = {"application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv"}

_gcli = httpx.Client(timeout=DRIVE_TIMEOUT)
_gtok: dict = {"valor": None, "vence": 0}


def _google_token() -> str | None:
    """Access token renovado pelo refresh token. None = credencial ausente ou recusada."""
    if _gtok["valor"] and time.time() < _gtok["vence"]:
        return _gtok["valor"]
    try:
        t = json.loads(GOOGLE_TOKEN_F.read_text(encoding="utf-8"))
    except OSError:
        return None
    try:
        r = _gcli.post(t["token_uri"], data={
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token"})
        r.raise_for_status()
        d = r.json()
    except Exception as e:                                   # noqa: BLE001
        _audit(evento="drive_sem_token", motivo=f"{type(e).__name__}: {e}"[:200])
        return None
    _gtok.update(valor=d["access_token"], vence=time.time() + d.get("expires_in", 3600) - 60)
    return _gtok["valor"]


def _g(metodo: str, url: str, **kw) -> dict:
    """Erro de rede e de API viram CAMPO, nunca excecao — igual ao `_motor`."""
    at = _google_token()
    if not at:
        return {"erro": "credencial do Drive indisponivel neste servidor"}
    h = kw.pop("headers", {})
    h["Authorization"] = f"Bearer {at}"
    try:
        r = _gcli.request(metodo, url, headers=h, **kw)
    except Exception as e:                                   # noqa: BLE001
        return {"erro": f"Drive inalcancavel: {type(e).__name__}", "detalhe": str(e)[:300]}
    if r.status_code == 404:
        return {"erro": "arquivo inexistente ou fora do alcance deste app"}
    if r.status_code >= 400:
        return {"erro": f"Drive devolveu {r.status_code}", "detalhe": r.text[:400]}
    if not r.content:
        return {}
    try:
        return r.json()
    except ValueError:
        return {"_texto": r.text}


def _autoriza_drive(acao: str, alvos: list | None = None) -> dict | None:
    return _autoriza(acao, TIPO_DRIVE, DOM_DRIVE, alvos or [f"drive:{PASTA_RAIZ}/*"])


def _dentro(file_id: str) -> bool:
    """Ancestralidade ate PASTA_RAIZ. Subida limitada: cadeia de parent nao e arvore
    infinita aqui, e loop no Drive existe (atalho, pasta em dois pais)."""
    if not PASTA_RAIZ or not file_id:
        return False
    atual, visto = file_id, set()
    for _ in range(6):
        if atual == PASTA_RAIZ:
            return True
        if atual in visto:
            return False
        visto.add(atual)
        d = _g("GET", f"https://www.googleapis.com/drive/v3/files/{atual}",
               params={"fields": "parents"})
        pais = d.get("parents") or []
        if not pais:
            return False
        atual = pais[0]
    return False


def _fora(file_id: str) -> dict:
    _audit(evento="negado", acao="drive", sobre=file_id, motivo="fora da pasta concedida")
    return {"erro": "fora da area de transferencia concedida",
            "detalhe": "so alcanco o que EU criei dentro da pasta do dono"}


@mcp.tool()
def drive_listar(pasta_id: str = "", tipo: str = "") -> dict:
    """Lista o que voce ja criou na area de transferencia com o dono.

    Esta pasta e o unico jeito de ele LER o que voce produz: ele nao tem acesso a
    sua rede, e voce nao tem wiki nem git. Documento, planilha e csv que voce
    depositar aqui ele abre no navegador.

    `pasta_id` vazio = a raiz da area. `tipo` filtra por `doc`, `planilha`, `pasta`,
    `csv`, `texto`. Devolve id, nome, tipo e link — o id alimenta as demais tools.
    """
    negativa = _autoriza_drive("drive_ler")
    if negativa:
        return negativa
    alvo = pasta_id or PASTA_RAIZ
    if alvo != PASTA_RAIZ and not _dentro(alvo):
        return _fora(alvo)
    q = f"'{alvo}' in parents and trashed=false"
    if tipo:
        m = _MIMES.get(tipo)
        if not m:
            return {"erro": f"tipo desconhecido: {tipo}", "validos": sorted(_MIMES)}
        q += f" and mimeType='{m}'"
    d = _g("GET", "https://www.googleapis.com/drive/v3/files",
           params={"q": q, "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",
                   "orderBy": "modifiedTime desc", "pageSize": 100})
    if "erro" in d:
        return d
    return {"arquivos": d.get("files", []), "pasta": alvo}


@mcp.tool()
def drive_ler(arquivo_id: str) -> dict:
    """Texto de um arquivo que voce criou. Documento sai como texto puro; planilha,
    como csv (para celula por celula, use `sheets_ler`).

    Serve para retomar trabalho de sessao anterior: o que voce escreveu ontem esta
    la, e voce le antes de continuar.
    """
    negativa = _autoriza_drive("drive_ler", [f"drive:{PASTA_RAIZ}/{arquivo_id}"])
    if negativa:
        return negativa
    if not _dentro(arquivo_id):
        return _fora(arquivo_id)
    meta = _g("GET", f"https://www.googleapis.com/drive/v3/files/{arquivo_id}",
              params={"fields": "id,name,mimeType,webViewLink"})
    if "erro" in meta:
        return meta
    mime = meta.get("mimeType", "")
    if mime == _MIMES["pasta"]:
        return {"erro": "isto e pasta, nao arquivo: use drive_listar"}
    if mime in _EXPORTA:
        d = _g("GET", f"https://www.googleapis.com/drive/v3/files/{arquivo_id}/export",
               params={"mimeType": _EXPORTA[mime]})
    elif mime.startswith("text/") or mime in ("application/json",):
        d = _g("GET", f"https://www.googleapis.com/drive/v3/files/{arquivo_id}",
               params={"alt": "media"})
    else:
        return {"erro": "arquivo binario: nao leio o conteudo aqui",
                "nome": meta.get("name"), "link": meta.get("webViewLink")}
    if "erro" in d:
        return d
    return {"nome": meta.get("name"), "tipo": mime,
            "conteudo": d.get("_texto", json.dumps(d, ensure_ascii=False)),
            "link": meta.get("webViewLink")}


@mcp.tool()
def drive_criar(nome: str, tipo: str = "doc", conteudo: str = "",
                pasta_id: str = "") -> dict:
    """Cria arquivo na area de transferencia, para o dono ler.

    `tipo`: `doc` (documento formatado, o default para entregar texto), `planilha`
    (grade editavel — o caso de lista de alvos, com uma linha por item), `csv`,
    `texto`, `markdown`, `pasta`.

    `conteudo` e o texto inicial; em `doc` ele entra e o Google converte. Para
    planilha, crie vazia e preencha com `sheets_escrever`, que e onde voce controla
    linha e coluna. Devolve id e link — mande o link ao dono pela mensagem.
    """
    negativa = _autoriza_drive("drive_escrever")
    if negativa:
        return negativa
    m = _MIMES.get(tipo)
    if not m:
        return {"erro": f"tipo desconhecido: {tipo}", "validos": sorted(_MIMES)}
    pai = pasta_id or PASTA_RAIZ
    if pai != PASTA_RAIZ and not _dentro(pai):
        return _fora(pai)
    meta = {"name": nome, "mimeType": m, "parents": [pai]}
    if m == _MIMES["pasta"] or not conteudo:
        d = _g("POST", "https://www.googleapis.com/drive/v3/files", json=meta,
               params={"fields": "id,name,webViewLink"})
        return d if "erro" in d else {"criado": d}
    # Upload multipart: metadado + bytes numa chamada. Doc/planilha convertem no
    # servidor do Google a partir do texto enviado.
    origem = "text/csv" if m == _MIMES["planilha"] else "text/plain"
    lim = "==pf=="
    corpo = (f"--{lim}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
             f"{json.dumps(meta)}\r\n--{lim}\r\nContent-Type: {origem}\r\n\r\n"
             f"{conteudo}\r\n--{lim}--")
    d = _g("POST", "https://www.googleapis.com/upload/drive/v3/files",
           params={"uploadType": "multipart", "fields": "id,name,webViewLink"},
           content=corpo.encode("utf-8"),
           headers={"Content-Type": f"multipart/related; boundary={lim}"})
    return d if "erro" in d else {"criado": d}


@mcp.tool()
def drive_editar(arquivo_id: str, conteudo: str) -> dict:
    """Substitui o conteudo INTEIRO de um arquivo seu. Nao ha append nem patch:
    leia com `drive_ler`, monte o texto novo completo, escreva.

    Para planilha, prefira `sheets_escrever`: ela mexe no intervalo pedido e deixa o
    resto quieto, enquanto esta aqui refaz a grade inteira.
    """
    negativa = _autoriza_drive("drive_escrever", [f"drive:{PASTA_RAIZ}/{arquivo_id}"])
    if negativa:
        return negativa
    if not _dentro(arquivo_id):
        return _fora(arquivo_id)
    meta = _g("GET", f"https://www.googleapis.com/drive/v3/files/{arquivo_id}",
              params={"fields": "mimeType"})
    if "erro" in meta:
        return meta
    mime = meta.get("mimeType", "")
    if mime == _MIMES["pasta"]:
        return {"erro": "isto e pasta, nao arquivo"}
    origem = ("text/csv" if mime == _MIMES["planilha"]
              else "text/plain" if mime in _EXPORTA or mime.startswith("text/")
              else None)
    if origem is None:
        return {"erro": "arquivo binario: nao reescrevo aqui"}
    d = _g("PATCH", f"https://www.googleapis.com/upload/drive/v3/files/{arquivo_id}",
           params={"uploadType": "media", "fields": "id,name,webViewLink"},
           content=conteudo.encode("utf-8"), headers={"Content-Type": origem})
    return d if "erro" in d else {"editado": d}


@mcp.tool()
def drive_apagar(arquivo_id: str) -> dict:
    """Manda para a LIXEIRA um arquivo que voce criou. Nao apaga de vez: o dono
    recupera em 30 dias se voce errar o alvo.

    Serve para limpar rascunho e versao vencida — area de transferencia entulhada
    para de servir para transferir.
    """
    negativa = _autoriza_drive("drive_apagar", [f"drive:{PASTA_RAIZ}/{arquivo_id}"])
    if negativa:
        return negativa
    if arquivo_id == PASTA_RAIZ:
        return {"erro": "a pasta raiz e do dono, nao sua"}
    if not _dentro(arquivo_id):
        return _fora(arquivo_id)
    d = _g("PATCH", f"https://www.googleapis.com/drive/v3/files/{arquivo_id}",
           json={"trashed": True}, params={"fields": "id,name"})
    return d if "erro" in d else {"na_lixeira": d}


@mcp.tool()
def sheets_ler(planilha_id: str, intervalo: str = "A1:Z200") -> dict:
    """Le celulas de uma planilha sua, em notacao A1 (`A1:C50`, `Alvos!A:D`).

    Devolve lista de linhas; linha curta vem curta, porque celula vazia no fim nao
    volta como vazio — conte pelo indice, nao pelo tamanho da linha.
    """
    negativa = _autoriza_drive("drive_ler", [f"drive:{PASTA_RAIZ}/{planilha_id}"])
    if negativa:
        return negativa
    if not _dentro(planilha_id):
        return _fora(planilha_id)
    d = _g("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{planilha_id}"
                  f"/values/{urllib_quote(intervalo)}")
    if "erro" in d:
        return d
    return {"intervalo": d.get("range"), "linhas": d.get("values", [])}


@mcp.tool()
def sheets_escrever(planilha_id: str, intervalo: str, linhas: list) -> dict:
    """Escreve celulas numa planilha sua. `linhas` e lista de listas, uma por linha:
    `[["alvo","tipo","status"],["exemplo.com","dominio","pendente"]]`.

    O intervalo tem de comportar o bloco (`A1:C3` para 3x3). Sobrescreve o que
    estiver la e nao toca no resto da grade — para acrescentar linha, leia antes com
    `sheets_ler`, veja onde acaba, e escreva a partir da proxima.
    """
    negativa = _autoriza_drive("drive_escrever", [f"drive:{PASTA_RAIZ}/{planilha_id}"])
    if negativa:
        return negativa
    if not _dentro(planilha_id):
        return _fora(planilha_id)
    if not isinstance(linhas, list) or not all(isinstance(x, list) for x in linhas):
        return {"erro": "linhas tem de ser lista de listas, uma lista por linha"}
    d = _g("PUT", f"https://sheets.googleapis.com/v4/spreadsheets/{planilha_id}"
                  f"/values/{urllib_quote(intervalo)}",
           params={"valueInputOption": "USER_ENTERED"}, json={"values": linhas})
    if "erro" in d:
        return d
    return {"escrito": d.get("updatedRange"), "celulas": d.get("updatedCells")}


async def _health(_req):
    est = _carrega_politica()
    return JSONResponse({"ok": est["erro"] is None,
                         "politica": est["erro"] or "carregada",
                         "motor": RAG_API_URL,
                         "wiki": WIKI_MCP_URL if WIKI_MCP_TOKEN else "sem token",
                         "drive": PASTA_RAIZ if _google_token() else "sem credencial",
                         "medido_em": int(time.time())})


# --- auth de borda: negativa em 401, nao em 200 (#2382) --------------------
# O PEP nega DENTRO da tool, e o transporte MCP embrulha essa negativa num 200 com
# erro no corpo. Duas consequencias, medidas de fora por claudinho-seguranca em
# 20/08/2026 contra a porta publicada pelo #2380:
#
#   1. `tools/list` sem credencial devolvia o catalogo inteiro. Enumeracao nao e
#      vazamento de dado — o `tools/call` continua negando —, mas e superficie que
#      nao precisa estar aberta, e some sozinha quando a borda exige identidade.
#   2. Cliente MCP novo aprende ONDE autenticar pelo 401 com WWW-Authenticate
#      (RFC 9728). Recebendo 200, ele nao aprende, e quem confere o controle por
#      status code le 200 e conclui que passou. Controle so vale verificado.
#
# O sign-off que autorizou a porta (#2380) dizia «sem JWT do realm com aud=ops-mcp,
# 401». Isto e o que faz a frase virar verdade.
#
# NAO ha rota de emergencia aqui, pela mesma razao de `_sujeito_do_jwt`: o token
# estatico e a mao do dono quando o realm cai, e o dono nao entra por esta porta.
RECURSO_URL = os.environ.get("JAIMINHO_RESOURCE", "")


def _base_do_pedido(request) -> str:
    """Endereco publico desta superficie. Env manda; sem ela, o que o cliente usou.

    Derivar do pedido evita o metadata apontar para `localhost` quando o alcance
    real e a LAN — que seria descoberta que nao descobre nada.
    """
    return (RECURSO_URL or str(request.base_url)).rstrip("/")


LIVRES = ("/health", "/.well-known/oauth-protected-resource")


async def _oauth_metadata(req):
    """RFC 9728: onde este recurso manda o cliente autenticar."""
    return JSONResponse({"resource": _base_do_pedido(req),
                         "authorization_servers": [OIDC_ISSUER],
                         "bearer_methods_supported": ["header"]})


class ExigeJWT(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.rstrip("/") in LIVRES:
            return await call_next(request)
        ident = _sujeito_do_jwt(request.headers.get("authorization", ""),
                                auditor=_audit, jwks_url=OIDC_JWKS_URL,
                                audience=OIDC_AUDIENCE, issuer=OIDC_ISSUER)
        if not ident:
            _audit(evento="auth_negada", path=request.url.path, status=401)
            desafio = f'Bearer realm="{OIDC_ISSUER}", resource_metadata="{_base_do_pedido(request)}/.well-known/oauth-protected-resource"'
            return JSONResponse({"erro": "nao autenticado"}, status_code=401,
                                headers={"WWW-Authenticate": desafio})
        request.state.sujeito = ident.get("sujeito")
        return await call_next(request)


app = mcp.streamable_http_app()
app.router.routes.append(Route("/health", _health))
app.router.routes.append(Route("/.well-known/oauth-protected-resource", _oauth_metadata))
app.add_middleware(ExigeJWT)
