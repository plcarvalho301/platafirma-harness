"""Borda da origem das faces do cubo de controle — a API que a tela de cada face chama.

Card #3516 (R22 e R30 a R32 da spec plano-de-controle-face-motor; seg:0015 §5; arq:0057). ASGI puro e
só biblioteca padrão, como a `Borda` do rastreador (platafirma-rastreador@api/borda.py, #3466): o
self-check roda no host sem uvicorn e sem porta (`python3 borda/borda.py`).

O QUE ESTA BORDA FAZ, e só isto:

1. Recebe `/api/<face>/<ato>` do navegador, atrás do gate do cubo. A face sai do caminho, e a lista de
   atos dela é a do cabeçalho do verbo (`# face: <ato>=<face>`, capacidade em `# atos:`), relida quando o
   arquivo muda. Ato fora dessa lista sai 403, e a lista da instância nunca é código.
2. Recusa a escrita de outro site (R31): todo método fora de GET, HEAD e OPTIONS só passa com `Origin`
   exata da lista da instância, `x-pf-tela: 1` e corpo `application/json`, sem exceção de classe (na rota
   pública não há chamada de verbo). Fora disso, 403, nada chega à porta e uma linha JSON vai ao stdout
   (rota, método, origem recebida, carimbo, motivo; sem corpo, sem cookie, sem token). A borda não
   responde CORS.
3. Casa o método com a capacidade do ato (R32): ato só de leitura por GET, só de escrita por POST, e o
   ato `leitura|escrita` aceita os dois. Escrita por GET e leitura por POST saem 403.
4. Leva a chamada à porta de verbos como `tools/call` do verbo, com o token do dono como Bearer,
   `turno_fonte=face` e o fundamento em `turno_texto` (R22, R30). A porta confere o client emissor
   (`azp`) e a audiência, projeta o `sub` como sujeito, recusa a escrita sem fundamento e grava o bruto.

O QUE NÃO FAZ: não autentica, não decide acesso e nunca afirma sujeito. O token do dono vem do gate e
vai à porta como veio; nenhum cabeçalho de sujeito vindo do navegador é lido; a borda não tem credencial
própria. Quem decide o que o dono pode é o PDP, na porta (R25). A borda também não confere o
fundamento: a regra «escrita da face sem fundamento» tem um dono só, a porta.

PEDIDO E RESPOSTA (o contrato que a tela consome):

    GET  /api/<face>/<ato>?a=<arg>&a=<arg>            ato de leitura
    POST /api/<face>/<ato>   {"args": [...], "fundamento": "..."}     ato de escrita

A resposta é o envelope da porta (exit_code, stdout, stderr, ou recusado e motivo), sem reinterpretar;
só falha da borda ou do transporte vira status HTTP: 400 pedido fora da forma, 401 sem token ou token
recusado pela porta, 403 recusa da borda, 404 rota ou face desconhecida, 405 método fora do contrato,
413 corpo grande, 502 porta fora do ar, 503 cabeçalho do verbo ilegível, 504 prazo. Erro da borda é
`{"erro": "..."}`.
"""

import asyncio
import http.client
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROTA = re.compile(r"^/api/([a-z][a-z0-9-]*)/([a-z][a-z0-9-]*)$")
METODOS_SEM_ESCRITA = ("GET", "HEAD", "OPTIONS")
CABECALHO_DA_TELA = "x-pf-tela"
TIPO_DO_CORPO = "application/json"
FONTE_DA_FACE = "face"
LIMITE_CORPO = 16 * 1024
LIMITE_RESPOSTA = 4 * 1024 * 1024
MAX_ARGS = 32
MAX_ARG = 2048
MAX_FUNDAMENTO = 4000
PRAZO_S = 55
USER_AGENT = "PlataFirma-borda/1.0 (+https://platafirma.org)"
# O que o envelope da porta traz do host e a tela não precisa: caminho de execução e contabilidade de poda.
INTERNOS_DA_PORTA = ("cwd", "poda", "poda_aviso")

_RE_ATOS = re.compile(r"([a-z][a-z0-9_-]*)\s*\(\s*([a-z|]+)\s*,")
_RE_LINHA = re.compile(r"^#\s*(atos|face)\s*:\s*(.*)$")


# --- o cabeçalho do verbo -------------------------------------------------------------------
def ler_cabecalho(texto: str) -> dict:
    """`{face: {ato: capacidades}}` do cabeçalho do verbo: `# atos: <ato> (<leitura|escrita>, <tipo>), …`
    dá a capacidade, `# face: <ato>=<face>` põe o ato na face. Ato que a face declara e `# atos:` não
    declara fica de fora: sem capacidade não há como casar o método, e a borda falha fechada. O
    cabeçalho acaba na primeira linha que não é comentário, como na porta (`_atos_do_cabecalho`)."""
    capacidades, faces = {}, {}
    for n, linha in enumerate(texto.splitlines()):
        if n > 400 or (n and not linha.startswith("#")):
            break
        achou = _RE_LINHA.match(linha)
        if not achou:
            continue
        if achou.group(1) == "atos":
            for ato, acao in _RE_ATOS.findall(achou.group(2)):
                capacidades[ato] = frozenset(a for a in acao.split("|") if a)
        else:
            ato, _, face = achou.group(2).partition("=")
            if ato.strip() and face.strip():
                faces.setdefault(face.strip(), []).append(ato.strip())
    return {face: {ato: capacidades[ato] for ato in atos if ato in capacidades}
            for face, atos in faces.items()}


class Face:
    """Uma face e o verbo que ela chama. `verbo` é o arquivo do verbo na release (relido quando o mtime
    muda); `cabecalho` é o texto dele, só para teste. `instancia` entra antes do ato na linha do verbo
    (`motor rag ajuste`), menos nos atos de `sem_instancia` (`motor listar`)."""

    def __init__(self, nome, verbo=None, cabecalho=None, instancia=None, sem_instancia=(), tool=None):
        self.nome = nome
        self.verbo = verbo
        self.cabecalho = cabecalho
        self.instancia = instancia
        self.sem_instancia = frozenset(sem_instancia)
        self.tool = tool or (os.path.basename(verbo) if verbo else nome)
        self._visto = None

    def atos(self):
        """`{ato: capacidades}` da face, ou None se o cabeçalho não carregou."""
        if self.cabecalho is not None:
            return ler_cabecalho(self.cabecalho).get(self.nome, {})
        try:
            mtime = os.stat(self.verbo).st_mtime_ns
            if self._visto is None or self._visto[0] != mtime:
                with open(self.verbo, encoding="utf-8", errors="replace") as fh:
                    atos = ler_cabecalho(fh.read(65536)).get(self.nome, {})
                self._visto = (mtime, atos)
        except OSError:
            return None
        return self._visto[1]

    def chamada(self, ato, args):
        """`(ato, args)` do tool da porta: a instância vai no lugar do ato, e o ato passa a ser o 1º arg."""
        if self.instancia and ato not in self.sem_instancia:
            return self.instancia, [ato, *args]
        return ato, list(args)


# --- a porta ----------------------------------------------------------------------------------
def chamar_porta_http(url, token, tool, argumentos, prazo=PRAZO_S):
    """`tools/call` do verbo na porta (MCP por HTTP, sem estado). Devolve `(status, corpo)`: 200 e o
    envelope do verbo, ou o status da borda e `{"erro": ...}`. O token só viaja no cabeçalho."""
    pedido = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": tool, "arguments": argumentos}}).encode("utf-8")
    # `User-Agent` proprio: sem ele o urllib manda `Python-urllib/3.x`, que a borda da Cloudflare em frente
    # da porta (ops.platafirma.org) recusa antes de o pedido chegar a ela (medido em 15/10/2026, #3565:
    # a borda recebia um erro HTTP que nao era 401 e a porta nao registrava o pedido).
    req = urllib.request.Request(url, data=pedido, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=prazo) as resp:
            tipo = resp.headers.get("content-type", "")
            bruto = resp.read(LIMITE_RESPOSTA + 1)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return 401, {"erro": "a porta recusou o token"}
        return 502, {"erro": f"a porta respondeu {e.code}"}
    except (TimeoutError, urllib.error.URLError, http.client.HTTPException, OSError) as e:
        causa = getattr(e, "reason", e)
        if isinstance(causa, TimeoutError):
            return 504, {"erro": "a porta não respondeu no prazo"}
        return 502, {"erro": "a porta está fora do ar"}
    if len(bruto) > LIMITE_RESPOSTA:
        return 502, {"erro": "a resposta da porta passou do teto"}
    return _envelope_do_rpc(tipo, bruto)


def _envelope_do_rpc(tipo, bruto):
    """O envelope do verbo dentro da resposta JSON-RPC (corpo JSON ou fluxo de eventos)."""
    try:
        texto = bruto.decode("utf-8", "replace")
        if "text/event-stream" in tipo:
            dados = [linha[5:].strip() for linha in texto.splitlines() if linha.startswith("data:")]
            msg = json.loads(dados[-1])
        else:
            msg = json.loads(texto)
        resultado = msg["result"]
    except (ValueError, KeyError, IndexError, TypeError):
        return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
    if resultado.get("isError"):
        return 502, {"erro": "a porta recusou a chamada do verbo"}
    envelope = resultado.get("structuredContent")
    if not isinstance(envelope, dict):
        try:
            envelope = json.loads(resultado["content"][0]["text"])
        except (ValueError, KeyError, IndexError, TypeError):
            return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
    if not isinstance(envelope, dict):
        return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
    return 200, envelope


# --- a borda ----------------------------------------------------------------------------------
class Borda:
    """Aplicação ASGI. `faces` é a lista de `Face`; `origens` é a lista fechada de origens das telas da
    instância, configuração e não código (`BORDA_ORIGENS`, lida em `criar_app`); vazia, nenhuma escrita
    de navegador passa. `chamar_porta(token, tool, argumentos) -> (status, corpo)` existe para o
    self-check; `saida` é onde vai a linha JSON da recusa (stdout)."""

    def __init__(self, faces, origens=(), porta_url="", chamar_porta=None,
                 cabecalho_token="authorization", saida=None):
        # Uma face pode chamar mais de um verbo (#3518: o `contestar` do `fila` na face motor): cada verbo declara
        # no cabeçalho os atos dele para a face, e a carga da face é a união. O mesmo ato declarado por dois verbos
        # da mesma face não se resolve por ordem: a borda falha fechada (503).
        self.faces = {}
        for f in faces:
            self.faces.setdefault(f.nome, []).append(f)
        self.origens = tuple(o.strip() for o in origens if o and o.strip())
        self.cabecalho_token = cabecalho_token.strip().lower()
        self._chamar = chamar_porta or (
            lambda token, tool, argumentos: chamar_porta_http(porta_url, token, tool, argumentos))
        self.saida = saida

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await _lifespan(receive, send)
        if scope["type"] != "http":
            return None
        try:
            return await self._atender(scope, receive, send)
        except Exception as e:                              # noqa: BLE001
            self._linha({"evento": "falha", "rota": scope.get("path"), "tipo": type(e).__name__})
            return await _responder(send, 500, {"erro": "falha da borda"})

    async def _atender(self, scope, receive, send):
        metodo, cab, caminho = scope["method"].upper(), _cabecalhos(scope), scope["path"]
        if metodo not in METODOS_SEM_ESCRITA:
            motivo = self._motivo_da_escrita(cab)
            if motivo is not None:
                return await self._recusar("escrita-recusada", scope, cab, motivo, send)
        achou = ROTA.match(caminho)
        verbos = self.faces.get(achou.group(1)) if achou else None
        if not verbos:
            return await _responder(send, 404, {"erro": "rota fora de /api/<face>/<ato>"})
        if metodo not in ("GET", "POST"):
            return await _responder(send, 405, {"erro": "só GET e POST"},
                                    extra=[(b"allow", b"GET, POST")])
        ato = achou.group(2)
        donos = []
        for f in verbos:
            atos = f.atos()
            if atos is None:
                return await _responder(send, 503, {"erro": "o cabeçalho do verbo não carregou"})
            if ato in atos:
                donos.append((f, atos[ato]))
        if len(donos) > 1:
            return await _responder(send, 503, {"erro": "o ato é declarado por dois verbos da face"})
        if not donos:
            return await self._recusar("ato-recusado", scope, cab, "ato fora da carga da face", send)
        face, capacidades = donos[0]
        if metodo == "GET" and "leitura" not in capacidades:
            return await self._recusar("ato-recusado", scope, cab, "ato de escrita por GET", send)
        if metodo == "POST" and "escrita" not in capacidades:
            return await self._recusar("ato-recusado", scope, cab, "ato de leitura por POST", send)
        token = self._token(cab)
        if token is None:
            return await _responder(send, 401, {"erro": "sem sessão"})
        if metodo == "GET":
            pedido = _pedido_de_leitura(scope)
        else:
            pedido = await _pedido_de_escrita(cab, receive)
        if isinstance(pedido[0], int):
            return await _responder(send, pedido[0], {"erro": pedido[1]})
        args, fundamento = pedido
        ato_porta, args_porta = face.chamada(ato, args)
        argumentos = {"ato": ato_porta, "args": args_porta, "turno_fonte": FONTE_DA_FACE}
        if fundamento:
            argumentos["turno_texto"] = fundamento
        status, corpo = await asyncio.to_thread(self._chamar, token, face.tool, argumentos)
        if status == 200:
            corpo = {k: v for k, v in corpo.items() if k not in INTERNOS_DA_PORTA}
        return await _responder(send, status, corpo)

    def _motivo_da_escrita(self, cab):
        """None quando a escrita passa; senão o motivo, em uma frase curta (R31)."""
        origem = cab.get("origin")
        if origem is None or origem not in self.origens:
            return "origem fora da lista da instancia"
        if cab.get(CABECALHO_DA_TELA) != "1":
            return f"sem o cabecalho {CABECALHO_DA_TELA}: 1"
        if cab.get("content-type", "").split(";", 1)[0].strip().lower() != TIPO_DO_CORPO:
            return f"corpo fora de {TIPO_DO_CORPO}"
        return None

    def _token(self, cab):
        """O token do dono que o gate repassou, ou None. Em `authorization` vem como Bearer; em outro
        cabeçalho (configuração, para o gate trocar) vem cru. Só o formato é conferido aqui: a validade é
        da porta."""
        valor = cab.get(self.cabecalho_token, "").strip()
        if self.cabecalho_token == "authorization":
            esquema, _, valor = valor.partition(" ")
            if esquema.lower() != "bearer":
                return None
            valor = valor.strip()
        if not valor or len(valor) > 8192 or any(c.isspace() or not c.isprintable() for c in valor):
            return None
        return valor

    async def _recusar(self, evento, scope, cab, motivo, send):
        """403 e UMA linha no stdout, que é o que `infra logs` lê. Sem corpo, sem cookie e sem token; a
        origem entra cortada, porque é o navegador que a escreve."""
        self._linha({"evento": evento, "rota": scope["path"], "metodo": scope["method"].upper(),
                     "origem": cab.get("origin", "")[:200] or None,
                     "carimbo": self._token(cab) is not None, "motivo": motivo})
        return await _responder(send, 403, {"erro": f"recusado: {motivo}"})

    def _linha(self, linha):
        print(json.dumps(linha, ensure_ascii=False), file=self.saida or sys.stdout, flush=True)


def _cabecalhos(scope) -> dict:
    return {chave.decode("latin-1").lower(): valor.decode("latin-1")
            for chave, valor in scope.get("headers", [])}


def _pedido_de_leitura(scope):
    """`(args, None)` ou `(status, motivo)`: GET leva só `a=` repetido."""
    consulta = urllib.parse.parse_qs(scope.get("query_string", b"").decode("latin-1"),
                                     keep_blank_values=True)
    if set(consulta) - {"a"}:
        return 400, "a leitura leva só o parâmetro a"
    return _conferir_args(consulta.get("a", []), None)


async def _pedido_de_escrita(cab, receive):
    declarado = cab.get("content-length", "")
    if declarado.isdigit() and int(declarado) > LIMITE_CORPO:
        return 413, f"corpo acima de {LIMITE_CORPO} bytes"
    corpo = await _ler_com_teto(receive, LIMITE_CORPO)
    if corpo is None:
        return 413, f"corpo acima de {LIMITE_CORPO} bytes"
    try:
        dado = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return 400, "corpo não é JSON"
    if not isinstance(dado, dict) or set(dado) - {"args", "fundamento"}:
        return 400, "o corpo leva só args e fundamento"
    fundamento = dado.get("fundamento")
    if fundamento is not None and (not isinstance(fundamento, str) or len(fundamento) > MAX_FUNDAMENTO):
        return 400, f"fundamento é texto de até {MAX_FUNDAMENTO} caracteres"
    return _conferir_args(dado.get("args", []), (fundamento or "").strip() or None)


def _conferir_args(args, fundamento):
    if (not isinstance(args, list) or len(args) > MAX_ARGS
            or any(not isinstance(a, str) or len(a) > MAX_ARG for a in args)):
        return 400, f"args é uma lista de até {MAX_ARGS} textos de até {MAX_ARG} caracteres"
    return list(args), fundamento


async def _ler_com_teto(receive, teto):
    """O corpo inteiro, ou None se passar do teto. Lê aos pedaços e para ao passar."""
    pedacos, total = [], 0
    while True:
        mensagem = await receive()
        if mensagem["type"] != "http.request":
            return b"".join(pedacos)
        pedaco = mensagem.get("body", b"")
        total += len(pedaco)
        if total > teto:
            return None
        pedacos.append(pedaco)
        if not mensagem.get("more_body"):
            return b"".join(pedacos)


async def _responder(send, status, corpo, extra=()):
    cabecalhos = [(b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"),
                  (b"content-type", b"application/json; charset=utf-8")]
    cabecalhos.extend(extra)
    dado = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": status, "headers": cabecalhos})
    await send({"type": "http.response.body", "body": dado})


async def _lifespan(receive, send):
    while True:
        mensagem = await receive()
        if mensagem["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif mensagem["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


# --- a instância ------------------------------------------------------------------------------
def criar_app(env=None):
    """A borda da instância, da configuração dela: nada disto é código. `BORDA_FACES` é um JSON
    `{"<face>": {"verbo": "<arquivo do verbo na release>", "instancia": "rag", "sem_instancia": ["listar"]}}`;
    a face que chama mais de um verbo leva a lista deles: `{"<face>": [{"verbo": ...}, {"verbo": ...}]}`."""
    env = os.environ if env is None else env
    faces = []
    try:
        declaradas = json.loads(env.get("BORDA_FACES") or "{}")
        for nome, ds in declaradas.items():
            for d in (ds if isinstance(ds, list) else [ds]):
                faces.append(Face(nome, verbo=d["verbo"], instancia=d.get("instancia"),
                                  sem_instancia=d.get("sem_instancia", ())))
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        print(json.dumps({"evento": "config-ilegivel", "variavel": "BORDA_FACES", "tipo": type(e).__name__}),
              flush=True)
        faces = []
    origens = [o for o in (env.get("BORDA_ORIGENS") or "").split(",")]
    return Borda(faces, origens=origens, porta_url=env.get("BORDA_PORTA_URL", ""),
                 cabecalho_token=env.get("BORDA_CABECALHO_TOKEN", "authorization"))


app = criar_app()


# --- self-check ---------------------------------------------------------------------------------
# Um chamador ASGI de uma função só, sem rede: monta o escopo, entrega o corpo e devolve (status,
# cabeçalhos, corpo). É o que dá para provar no host sem a porta nem o uvicorn.
async def _chamar(app_, metodo, caminho, cabecalhos=None, corpo=b"", consulta=b"", pedacos=None):
    escopo = {"type": "http", "method": metodo, "path": caminho, "query_string": consulta,
              "headers": [(k.lower().encode(), v.encode()) for k, v in dict(cabecalhos or {}).items()]}
    partes = pedacos if pedacos is not None else [corpo]
    entrega = [{"type": "http.request", "body": parte, "more_body": i < len(partes) - 1}
               for i, parte in enumerate(partes)]

    async def receive():
        return entrega.pop(0) if entrega else {"type": "http.disconnect"}

    visto = {}

    async def send(mensagem):
        if mensagem["type"] == "http.response.start":
            visto["status"] = mensagem["status"]
            visto["cabecalhos"] = {k.decode(): v.decode() for k, v in mensagem["headers"]}
        else:
            visto["corpo"] = mensagem.get("body", b"")

    await app_(escopo, receive, send)
    return visto["status"], visto["cabecalhos"], visto["corpo"]


CABECALHO_DE_MENTIRA = """#!/usr/bin/env python3
# motor — verbo de mentira do self-check
# atos: listar (leitura, texto), buscar (leitura, busca), ajuste (leitura|escrita, config), trocar (escrita, geracao), sortear (escrita, gabarito)
# face: listar=motor
# face: buscar=motor
# face: ajuste=motor
# face: trocar=motor
# face: inexistente=motor
import sys
"""


def _autoteste():
    saida, chamadas = io.StringIO(), []
    origem = "https://controle.exemplo.org"

    def porta(token, tool, argumentos):
        chamadas.append((token, tool, argumentos))
        return 200, {"exit_code": 0, "stdout": {"texto": "{}"}, "cwd": "/host/segredo", "poda": {"giro": 1}}

    face = Face("motor", cabecalho=CABECALHO_DE_MENTIRA, instancia="rag", sem_instancia=("listar",))
    borda = Borda([face], origens=(origem,), chamar_porta=porta, saida=saida)

    def rodar(*a, **k):
        return asyncio.run(_chamar(borda, *a, **k))

    token = {"authorization": "Bearer a.b.c"}
    da_tela = {"origin": origem, "x-pf-tela": "1", "content-type": "application/json", **token}
    de_fora = "https://outro.exemplo"

    # 1. o cabeçalho do verbo: a capacidade de cada ato, e o que a face não declara fica de fora.
    atos = face.atos()
    assert atos == {"listar": {"leitura"}, "buscar": {"leitura"}, "ajuste": {"leitura", "escrita"},
                    "trocar": {"escrita"}}, atos
    print("borda: a lista de atos e a capacidade de cada um vêm do cabeçalho do verbo      ok")

    # 2. as nove recusas em 403, nenhuma chega à porta: as seis tentativas de fora da #3466 (R31), o ato
    #    fora da carga, o ato sem face (a linha de exclusão) e a escrita por GET (R32).
    nove = {
        "origem de fora": ("POST", "/api/motor/trocar", {**da_tela, "origin": de_fora}),
        "sem x-pf-tela": ("POST", "/api/motor/trocar", {k: v for k, v in da_tela.items() if k != "x-pf-tela"}),
        "text/plain": ("POST", "/api/motor/trocar", {**da_tela, "content-type": "text/plain"}),
        "host irmão": ("POST", "/api/motor/trocar", {**da_tela, "origin": "https://casa.exemplo.org"}),
        "formulário de outro site": ("POST", "/api/motor/trocar", {
            **token, "origin": de_fora, "sec-fetch-site": "cross-site",
            "content-type": "application/x-www-form-urlencoded"}),
        "sem Origin": ("POST", "/api/motor/trocar", {k: v for k, v in da_tela.items() if k != "origin"}),
        "ato fora da carga": ("POST", "/api/motor/inexistente", da_tela),
        "ato sem face (exclusão)": ("POST", "/api/motor/sortear", da_tela),
        "escrita por GET": ("GET", "/api/motor/trocar", token),
    }
    for nome, (metodo, caminho, cab) in nove.items():
        status, cab_resp, _ = rodar(metodo, caminho, cab, b"{}")
        assert status == 403, (nome, status)
        assert cab_resp["cache-control"] == "no-store" and cab_resp["x-content-type-options"] == "nosniff"
    assert chamadas == [], f"recusa que chegou à porta: {chamadas}"
    linhas = [json.loads(linha) for linha in saida.getvalue().splitlines()]
    assert len(linhas) == 9, linhas
    assert linhas[0] == {"evento": "escrita-recusada", "rota": "/api/motor/trocar", "metodo": "POST",
                         "origem": de_fora, "carimbo": True, "motivo": "origem fora da lista da instancia"}
    assert [x["evento"] for x in linhas[-3:]] == ["ato-recusado"] * 3 and linhas[-1]["metodo"] == "GET"
    assert "a.b.c" not in saida.getvalue(), "a linha de log vazou o token"
    print("borda: nove recusas em 403 (seis de outro site, fora da carga, exclusão, GET), nenhuma chega à porta  ok")

    # 3. o que passa: leitura por GET, escrita por POST com o fundamento, o ato misto pelos dois métodos.
    status, _, corpo = rodar("GET", "/api/motor/buscar", token, consulta=b"a=biblioteca&a=o%20que%20%C3%A9")
    assert status == 200 and json.loads(corpo) == {"exit_code": 0, "stdout": {"texto": "{}"}}, corpo
    assert chamadas[-1] == ("a.b.c", "motor", {"ato": "rag", "turno_fonte": "face",
                                              "args": ["buscar", "biblioteca", "o que é"]})
    status, _, _ = rodar("GET", "/api/motor/listar", token)
    assert status == 200 and chamadas[-1][2] == {"ato": "listar", "args": [], "turno_fonte": "face"}
    escrita = json.dumps({"args": ["biblioteca", "--embedder", "x"], "fundamento": " o piso estava alto "})
    status, _, _ = rodar("POST", "/api/motor/trocar", da_tela, escrita.encode())
    assert status == 200 and chamadas[-1][2] == {
        "ato": "rag", "turno_fonte": "face", "turno_texto": "o piso estava alto",
        "args": ["trocar", "biblioteca", "--embedder", "x"]}, chamadas[-1]
    assert rodar("GET", "/api/motor/ajuste", token, consulta=b"a=piso")[0] == 200
    assert rodar("POST", "/api/motor/ajuste", da_tela, b'{"args": ["piso", "0.6"]}')[0] == 200
    assert "turno_texto" not in chamadas[-1][2], "sem fundamento a borda não inventa texto: quem recusa é a porta"
    print("borda: GET lê, POST escreve com o fundamento no turno, ajuste (misto) aceita os dois       ok")

    # 4. o navegador não põe sujeito, sessão, turno nem fundamento por fora do corpo.
    for corpo_ruim in (b'{"args": [], "sessao_id": "x"}', b'{"args": [], "turno_fonte": "hook"}',
                       b'{"args": "nao-lista"}', b'{"args": [1]}', b'{"fundamento": 7}', b"nao e json"):
        assert rodar("POST", "/api/motor/trocar", da_tela, corpo_ruim)[0] == 400, corpo_ruim
    assert rodar("GET", "/api/motor/buscar", token, consulta=b"a=x&turno_fonte=hook")[0] == 400
    assert rodar("POST", "/api/motor/trocar", {**da_tela, "content-length": str(LIMITE_CORPO + 1)},
                 b"x" * (LIMITE_CORPO + 1))[0] == 413
    assert rodar("POST", "/api/motor/trocar", da_tela, pedacos=[b"x" * 9000, b"x" * 9000])[0] == 413
    print("borda: corpo e parâmetro fora da forma saem 400 ou 413, e nada disto chega à porta        ok")

    # 5. sem token, 401 sem chegar à porta; o cabeçalho de sujeito do navegador não é lido.
    antes = len(chamadas)
    assert rodar("GET", "/api/motor/buscar")[0] == 401
    assert rodar("GET", "/api/motor/buscar", {"x-auth-request-user": "dono"})[0] == 401
    assert rodar("GET", "/api/motor/buscar", {"authorization": "Basic abc"})[0] == 401
    assert rodar("POST", "/api/motor/trocar", {k: v for k, v in da_tela.items() if k != "authorization"}, b"{}")[0] == 401
    assert len(chamadas) == antes
    print("borda: sem token (ou com cabeçalho de sujeito no lugar dele), 401 e nada chega à porta   ok")

    # 6. método e rota fora do contrato; a borda não responde CORS; porta fora e prazo viram 502 e 504.
    assert rodar("PUT", "/api/motor/trocar", da_tela, b"{}")[0] == 405
    assert rodar("DELETE", "/api/motor/trocar", {**da_tela, "origin": de_fora}, b"{}")[0] == 403
    status, cab_resp, _ = rodar("OPTIONS", "/api/motor/buscar", {"origin": origem})
    assert status == 405 and not any(k.startswith("access-control") for k in cab_resp)
    assert rodar("GET", "/api/outra/buscar", token)[0] == 404 and rodar("GET", "/api/motor", token)[0] == 404
    assert rodar("GET", "/api/motor/../x", token)[0] == 404
    for status_porta in (401, 502, 504):
        fora = Borda([face], origens=(origem,), saida=io.StringIO(),
                     chamar_porta=lambda t, tool, a, s=status_porta: (s, {"erro": "x"}))
        assert asyncio.run(_chamar(fora, "GET", "/api/motor/buscar", token))[0] == status_porta
    sem_verbo = Borda([Face("motor", verbo="/nao/existe/motor")], origens=(origem,), saida=io.StringIO())
    assert asyncio.run(_chamar(sem_verbo, "GET", "/api/motor/buscar", token))[0] == 503
    sem_lista = Borda([face], chamar_porta=porta, saida=io.StringIO())
    assert asyncio.run(_chamar(sem_lista, "POST", "/api/motor/trocar", da_tela, b"{}"))[0] == 403
    print("borda: PUT 405, OPTIONS sem CORS, rota 404, porta fora 502/504, lista de origens vazia recusa   ok")

    # 7. o envelope da porta se lê do corpo JSON e do fluxo de eventos (o cwd sai na borda, passo 3).
    evento = ("event: message\ndata: " + json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
        "content": [{"type": "text", "text": "x"}],
        "structuredContent": {"exit_code": 0, "cwd": "/host", "stdout": {"texto": "ok"}}}}) + "\n\n")
    assert _envelope_do_rpc("text/event-stream", evento.encode()) == (
        200, {"exit_code": 0, "cwd": "/host", "stdout": {"texto": "ok"}})
    texto = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
        "content": [{"type": "text", "text": json.dumps({"recusado": True, "motivo": "m"})}]}})
    assert _envelope_do_rpc("application/json", texto.encode()) == (200, {"recusado": True, "motivo": "m"})
    assert _envelope_do_rpc("application/json", b'{"result": {"isError": true}}')[0] == 502
    assert _envelope_do_rpc("application/json", b"nao e json")[0] == 502
    print("borda: o envelope da porta se lê do corpo JSON e do fluxo de eventos                       ok")

    # 8. uma face com dois verbos (#3518): a carga é a união, cada ato vai ao verbo que o declara, sem a
    #    instância do outro; o mesmo ato em dois verbos da face falha fechado.
    fila = Face("motor", cabecalho=("#!/usr/bin/env python3\n# fila\n"
                                   "# atos: enviar (escrita, mensagem) · contestar (escrita, mensagem)\n"
                                   "# face: contestar=motor\nimport sys\n"), tool="fila")
    chamadas.clear()
    duas = Borda([face, fila], origens=(origem,), chamar_porta=porta, saida=io.StringIO())
    corpo = json.dumps({"args": ["ia", "--indicador", "taxa"], "fundamento": "a amostra é pequena"}).encode()
    assert asyncio.run(_chamar(duas, "POST", "/api/motor/contestar", da_tela, corpo))[0] == 200
    assert chamadas[-1] == ("a.b.c", "fila", {"ato": "contestar", "turno_fonte": "face", "turno_texto": "a amostra é pequena",
                                            "args": ["ia", "--indicador", "taxa"]}), chamadas[-1]
    assert asyncio.run(_chamar(duas, "GET", "/api/motor/buscar", token, consulta=b"a=biblioteca"))[0] == 200
    assert chamadas[-1][1] == "motor" and chamadas[-1][2]["ato"] == "rag"
    assert asyncio.run(_chamar(duas, "POST", "/api/motor/enviar", da_tela, b"{}"))[0] == 403, "enviar não é da face"
    assert asyncio.run(_chamar(duas, "GET", "/api/motor/contestar", token))[0] == 403, "contestar é escrita"
    gemeo = Face("motor", cabecalho="# outro\n# atos: buscar (leitura, busca)\n# face: buscar=motor\n", tool="outro")
    ambigua = Borda([face, gemeo], origens=(origem,), chamar_porta=porta, saida=io.StringIO())
    antes = len(chamadas)
    assert asyncio.run(_chamar(ambigua, "GET", "/api/motor/buscar", token))[0] == 503
    assert len(chamadas) == antes
    lista = criar_app({"BORDA_FACES": json.dumps({"motor": [{"verbo": "/a/motor", "instancia": "rag"}, {"verbo": "/a/fila"}]})})
    assert [(f.tool, f.instancia) for f in lista.faces["motor"]] == [("motor", "rag"), ("fila", None)]
    print("borda: face com dois verbos — cada ato ao verbo que o declara, o ato duplicado falha fechado   ok")
    print("borda OK (#3516, #3518)")


if __name__ == "__main__":
    _autoteste()
