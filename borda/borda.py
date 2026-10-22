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
4. Lê o token do dono de `X-Forwarded-Access-Token`, onde o gate do cubo o entrega cru (#2548), e recusa a
   escrita com 401 quando o `auth_time` dele passa de cinco minutos (#2572): a tela leva o dono a sair e
   entrar antes de repetir o ato. A leitura não tem esse corte, porque o `auth_time` não muda quando o gate
   renova o token e o dono olhando não repete a credencial a cada cinco minutos. Token sem `auth_time` passa e
   deixa a linha `sem-auth-time` no stdout; a conferência é o primeiro login real.
5. Leva a chamada à porta de verbos como `tools/call` do verbo, com o token do dono como Bearer,
   `turno_fonte=face` e o fundamento em `turno_texto` (R22, R30). A porta confere o client emissor
   (`azp`) e a audiência, projeta o `sub` como sujeito, recusa a escrita sem fundamento e grava o bruto.

O QUE NÃO FAZ: não autentica, não decide acesso e nunca afirma sujeito. O token do dono vem do gate e
vai à porta como veio; nenhum cabeçalho de sujeito vindo do navegador é lido; a borda não tem credencial
própria. Quem decide o que o dono pode é o PDP, na porta (R25). A borda também não confere o
fundamento: a regra «escrita da face sem fundamento» tem um dono só, a porta.

6. Serve a rota fixa da casca da Taipa, `GET|PUT /api/preferencia/tema` (card #3738; seg:0016 item 6; spec
   taipa R40), pelo verbo `preferencia` da face `casca`. Mesmas recusas dos itens 2 a 4, com duas
   diferenças: o fundamento da escrita é a frase fixa da instância (`BORDA_TEMA_FUNDAMENTO`), e o corte
   de login recente do item 4 não vale (o tema volta com um clique). O sujeito é o do token, tirado pela
   porta; a borda não o lê nem o manda.

PEDIDO E RESPOSTA (o contrato que a tela consome):

    GET  /api/<face>/<ato>?a=<arg>&a=<arg>            ato de leitura
    POST /api/<face>/<ato>   {"args": [...], "fundamento": "..."}     ato de escrita

A resposta é o envelope da porta (exit_code, stdout, stderr, ou recusado e motivo), sem reinterpretar;
só falha da borda ou do transporte vira status HTTP: 400 pedido fora da forma, 401 sem token, login antigo
(`{"login": "antigo"}`) ou token recusado pela porta, 403 recusa da borda, 404 rota ou face desconhecida, 405 método fora do contrato,
413 corpo grande, 502 porta fora do ar, 503 cabeçalho do verbo ilegível, 504 prazo. Erro da borda é
`{"erro": "..."}`.
"""

import asyncio
import base64
import http.client
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROTA = re.compile(r"^/api/([a-z][a-z0-9-]*)/([a-z][a-z0-9-]*)$")
# A rota fixa da casca da Taipa (spec taipa R40; seg:0016 item 6; card #3738): `GET` devolve `{"valor"}` e
# `PUT {"valor"}` escolhe, como `platafirma-ui@src/pf/pf-casca.js` (CAMINHOS.tema) pede. Ela chama o verbo
# `preferencia`, que a face `casca` declara no cabeçalho (`# face: ler=casca`, `# face: escrever=casca`).
ROTA_DO_TEMA = "/api/preferencia/tema"
# A `casca` não é face: é o componente que consome o mecanismo comum (arq:0124 §3, `# mecanismo: <ato>=casca`).
FACE_DA_CASCA = "casca"
# As outras duas leituras da casca (card #3899): a rota → o ato do verbo dono do objeto (release telas, tarefas
# espera-dono). O nome `/api/faces` é o que a seg:0016 item 6 fixa; o corpo da lista é provisorio (#3379).
ROTA_DAS_TELAS = "/api/faces"
ROTA_DA_ESPERA = "/api/espera-dono"
LEITURAS_DA_CASCA = {ROTA_DAS_TELAS: "telas", ROTA_DA_ESPERA: "espera-dono"}
# A escrita da face exige fundamento (a porta recusa sem ele), e trocar o tema não tem texto do dono para
# dar: o fundamento é uma frase FIXA da instância (`BORDA_TEMA_FUNDAMENTO`), posta pela borda e nunca
# aceita do navegador. Grava no bruto da porta o que é verdade: a escolha veio da casca.
FUNDAMENTO_DO_TEMA = "escolha do tema na casca da tela"
# O valor do tema que o navegador manda: só letras minúsculas e curto. O vocabulário é do verbo (que sai
# 2 fora dele); isto só garante que nada que pareça opção ou argumento extra chega à porta.
VALOR_DO_TEMA = re.compile(r"^[a-z]{1,16}$")
LIMITE_CORPO_DO_TEMA = 1024
METODOS_SEM_ESCRITA = ("GET", "HEAD", "OPTIONS")
CABECALHO_DA_TELA = "x-pf-tela"
TIPO_DO_CORPO = "application/json"
FONTE_DA_FACE = "face"
# Onde o gate do cubo (oauth2-proxy) entrega o access token do dono: cru, sem esquema (#2548, #3575).
CABECALHO_DO_GATE = "x-forwarded-access-token"
# Idade máxima do login para a escrita (#2572): o gate manda prompt=login, então o `auth_time` do token é
# o momento em que o dono digitou a credencial. Passou disso, 401 e a tela leva o dono a sair e entrar.
LOGIN_MAX_S = 300
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
_RE_LINHA = re.compile(r"^#\s*(atos|face|mecanismo)\s*:\s*(.*)$")


# --- o cabeçalho do verbo -------------------------------------------------------------------
def _ler_declaracoes(texto: str) -> tuple:
    """`(capacidades, faces, mecanismos)` do cabeçalho: `# atos:` dá a capacidade de cada ato, `# face:
    <ato>=<face>` põe o ato numa face e `# mecanismo: <ato>=<componente>` o põe no mecanismo comum de um
    componente (hoje só a `casca`; arq:0124 §3). Um ato não entra numa chave pela outra."""
    capacidades, faces, mecanismos = {}, {}, {}
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
            ato, _, dono = achou.group(2).partition("=")
            if ato.strip() and dono.strip():
                alvo = faces if achou.group(1) == "face" else mecanismos
                alvo.setdefault(dono.strip(), []).append(ato.strip())
    return capacidades, faces, mecanismos


def _com_capacidade(capacidades: dict, por_dono: dict) -> dict:
    return {dono: {ato: capacidades[ato] for ato in atos if ato in capacidades}
            for dono, atos in por_dono.items()}


def ler_cabecalho(texto: str) -> dict:
    """`{face: {ato: capacidades}}` do cabeçalho do verbo: `# atos: <ato> (<leitura|escrita>, <tipo>), …`
    dá a capacidade, `# face: <ato>=<face>` põe o ato na face. Ato que a face declara e `# atos:` não
    declara fica de fora: sem capacidade não há como casar o método, e a borda falha fechada. O
    cabeçalho acaba na primeira linha que não é comentário, como na porta (`_atos_do_cabecalho`)."""
    capacidades, faces, _ = _ler_declaracoes(texto)
    return _com_capacidade(capacidades, faces)


def ler_mecanismos(texto: str) -> dict:
    """`{componente: {ato: capacidades}}` das linhas `# mecanismo: <ato>=<componente>`, com a mesma regra de
    capacidade de `ler_cabecalho`. A chave `face:` não carrega a casca: ela é componente, não face."""
    capacidades, _, mecanismos = _ler_declaracoes(texto)
    return _com_capacidade(capacidades, mecanismos)


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

    def _carga(self, texto):
        """A carga desta face no cabeçalho: a `casca` é componente e vem de `# mecanismo:`; toda outra face
        vem de `# face:`."""
        lido = ler_mecanismos(texto) if self.nome == FACE_DA_CASCA else ler_cabecalho(texto)
        return lido.get(self.nome, {})

    def atos(self):
        """`{ato: capacidades}` da face, ou None se o cabeçalho não carregou."""
        if self.cabecalho is not None:
            return self._carga(self.cabecalho)
        try:
            mtime = os.stat(self.verbo).st_mtime_ns
            if self._visto is None or self._visto[0] != mtime:
                with open(self.verbo, encoding="utf-8", errors="replace") as fh:
                    atos = self._carga(fh.read(65536))
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
                 cabecalho_token=CABECALHO_DO_GATE, saida=None, login_max_s=LOGIN_MAX_S, agora=time.time,
                 fundamento_do_tema=FUNDAMENTO_DO_TEMA, origens_da_declaracao=None):
        # Uma face pode chamar mais de um verbo (#3518: o `contestar` do `fila` na face motor): cada verbo declara
        # no cabeçalho os atos dele para a face, e a carga da face é a união. O mesmo ato declarado por dois verbos
        # da mesma face não se resolve por ordem: a borda falha fechada (503).
        self.faces = {}
        for f in faces:
            self.faces.setdefault(f.nome, []).append(f)
        self.origens = tuple(o.strip() for o in origens if o and o.strip())
        # As origens da declaração das telas (registro/telas.json), relidas quando o arquivo muda; somam-se às da
        # configuração da instância. `callable() -> tuple`, vazia se a declaração não carregou (falha fechada).
        self._origens_da_declaracao = origens_da_declaracao or (lambda: ())
        self.cabecalho_token = cabecalho_token.strip().lower()
        self.login_max_s = login_max_s
        self._agora = agora
        self.fundamento_do_tema = fundamento_do_tema
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
        if caminho == ROTA_DO_TEMA:
            return await self._tema(scope, receive, send, metodo, cab)
        if caminho in LEITURAS_DA_CASCA:
            return await self._leitura_da_casca(scope, send, metodo, cab, LEITURAS_DA_CASCA[caminho])
        achou = ROTA.match(caminho)
        # a casca e componente, nao face: so as tres rotas fixas a alcancam, nunca /api/casca/<ato>
        verbos = self.faces.get(achou.group(1)) if achou and achou.group(1) != FACE_DA_CASCA else None
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
        if metodo == "POST" and self.login_max_s:
            idade = self._idade_do_login(token)
            if idade is None:
                self._linha({"evento": "sem-auth-time", "rota": caminho})
            elif idade > self.login_max_s:
                self._linha({"evento": "login-antigo", "rota": caminho, "idade_s": int(idade)})
                return await _responder(send, 401, {
                    "erro": f"login com mais de {self.login_max_s // 60} minutos: entre de novo",
                    "login": "antigo"})
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

    async def _tema(self, scope, receive, send, metodo, cab):
        """`GET|PUT /api/preferencia/tema`: a rota que a casca da Taipa pede (R40), pelo verbo `preferencia`.

        A mesma disciplina das outras rotas: a escrita de outro site já saiu em 403 antes (R31); o ato
        só vale se o cabeçalho do verbo o põe na face `casca` com a capacidade certa (R32); o token do gate
        vai à porta como veio, e é ela quem tira dele o sujeito (a spec `preferencia` R1: o sujeito nunca
        é argumento, e aqui nem o navegador nem a borda o mandam). Duas diferenças, ditas: o fundamento
        da escrita é a frase fixa da instância, e NÃO há o corte de login recente de #2572 — o tema volta
        com um clique (`volta: sim`), e pedir credencial nova a cada troca depois de cinco minutos seria
        o contrário do que a casca existe para fazer."""
        if metodo not in ("GET", "PUT"):
            return await _responder(send, 405, {"erro": "só GET e PUT"}, extra=[(b"allow", b"GET, PUT")])
        ato, capacidade = ("ler", "leitura") if metodo == "GET" else ("escrever", "escrita")
        face, falha = self._dono_na_casca(ato, capacidade)
        if falha is not None:
            return await self._falha_da_casca(falha, scope, cab, send)
        token = self._token(cab)
        if token is None:
            return await _responder(send, 401, {"erro": "sem sessão"})
        valor = None
        if metodo == "GET":
            argumentos = {"ato": "ler", "args": ["tema", "--json"], "turno_fonte": FONTE_DA_FACE}
        else:
            valor = await _pedido_do_tema(cab, receive)
            if isinstance(valor, tuple):
                return await _responder(send, valor[0], {"erro": valor[1]})
            argumentos = {"ato": "escrever", "args": ["tema", valor], "turno_fonte": FONTE_DA_FACE,
                          "turno_texto": self.fundamento_do_tema}
        status, corpo = await asyncio.to_thread(self._chamar, token, face.tool, argumentos)
        if status != 200:
            return await _responder(send, status, corpo)
        status, corpo = _resposta_do_tema(metodo, corpo, valor)
        return await _responder(send, status, corpo)

    def _dono_na_casca(self, ato, capacidade):
        """`(face, None)` do verbo que declara o `ato` no mecanismo da casca com a `capacidade`, ou `(None,
        falha)`: `sem-casca` (a instancia não atende a casca, 404), `sem-carga` (o cabeçalho não carregou ou
        declara o ato em dois verbos, 503) ou `fora-da-carga` (nenhum verbo declara o ato com essa
        capacidade, 403)."""
        verbos = self.faces.get(FACE_DA_CASCA)
        if not verbos:
            return None, "sem-casca"
        donos = []
        for f in verbos:
            atos = f.atos()
            if atos is None:
                return None, "sem-carga"
            if ato in atos:
                donos.append((f, atos[ato]))
        if len(donos) > 1:
            return None, "sem-carga"
        if not donos or capacidade not in donos[0][1]:
            return None, "fora-da-carga"
        return donos[0][0], None

    async def _falha_da_casca(self, falha, scope, cab, send):
        if falha == "sem-casca":
            return await _responder(send, 404, {"erro": "rota fora de /api/<face>/<ato>"})
        if falha == "sem-carga":
            return await _responder(send, 503, {"erro": "o cabeçalho do verbo não carregou"})
        return await self._recusar("ato-recusado", scope, cab, "ato fora da carga da face", send)

    async def _leitura_da_casca(self, scope, send, metodo, cab, ato):
        """`GET /api/faces` (release telas) e `GET /api/espera-dono` (tarefas espera-dono): as outras duas
        leituras da casca (arq:0124 §3; seg:0016 item 6). Mesma disciplina da rota do tema: a escrita de outro
        site já saiu em 403; o ato só vale se o cabeçalho do verbo o põe no mecanismo da casca como leitura;
        o token do gate vai à porta como veio. O corpo é o que o verbo imprime em `--json`, sem reler."""
        if metodo != "GET":
            return await _responder(send, 405, {"erro": "só GET"}, extra=[(b"allow", b"GET")])
        face, falha = self._dono_na_casca(ato, "leitura")
        if falha is not None:
            return await self._falha_da_casca(falha, scope, cab, send)
        token = self._token(cab)
        if token is None:
            return await _responder(send, 401, {"erro": "sem sessão"})
        argumentos = {"ato": ato, "args": ["--json"], "turno_fonte": FONTE_DA_FACE}
        status, corpo = await asyncio.to_thread(self._chamar, token, face.tool, argumentos)
        if status != 200:
            return await _responder(send, status, corpo)
        status, corpo = _resposta_da_leitura(ato, corpo)
        return await _responder(send, status, corpo)

    def _motivo_da_escrita(self, cab):
        """None quando a escrita passa; senão o motivo, em uma frase curta (R31)."""
        origem = cab.get("origin")
        if origem is None or (origem not in self.origens and origem not in self._origens_da_declaracao()):
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

    def _idade_do_login(self, token):
        """Segundos desde o login do dono (`auth_time` do payload do token), ou None se o token não é um JWT
        legivel ou não traz o claim. A assinatura não é conferida aqui: a validade do token é da porta, e
        token forjado sai 401 de la; esta leitura só mede a idade do login. Sem o claim a borda não inventa
        outro sinal (#2572): deixa passar e registra `sem-auth-time` no stdout."""
        partes = token.split(".")
        if len(partes) != 3:
            return None
        try:
            payload = partes[1] + "=" * (-len(partes[1]) % 4)
            valor = json.loads(base64.urlsafe_b64decode(payload)).get("auth_time")
        except (ValueError, AttributeError):
            return None
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None
        return self._agora() - valor

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


async def _pedido_do_tema(cab, receive):
    """O valor do `PUT {"valor": ...}` da casca, ou `(status, motivo)`. O corpo leva só a chave `valor`, e
    o valor só letras minúsculas e curtas: o navegador não manda fundamento, args nem opção."""
    declarado = cab.get("content-length", "")
    if declarado.isdigit() and int(declarado) > LIMITE_CORPO_DO_TEMA:
        return 413, f"corpo acima de {LIMITE_CORPO_DO_TEMA} bytes"
    corpo = await _ler_com_teto(receive, LIMITE_CORPO_DO_TEMA)
    if corpo is None:
        return 413, f"corpo acima de {LIMITE_CORPO_DO_TEMA} bytes"
    try:
        dado = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return 400, "corpo não é JSON"
    if not isinstance(dado, dict) or set(dado) != {"valor"}:
        return 400, "o corpo leva só valor"
    valor = dado["valor"]
    if not isinstance(valor, str) or not VALOR_DO_TEMA.match(valor):
        return 400, "valor é texto de letras minúsculas"
    return valor

def _resposta_do_tema(metodo, envelope, valor):
    """`(status, corpo)` da rota do tema, do envelope que a porta devolveu. A saída do verbo vira status:
    0 → 200 `{"valor"}`; 2 (valor fora do vocabulário) → 400; 3 (sem sujeito) → 401; 5 (banco mudo) e
    o resto → 502. A recusa da porta (`recusado`) → 403. O banco que não respondeu nunca vira `valor`
    vazio: a casca lê 502 como «não consegui olhar» e segue no tema do sistema."""
    if envelope.get("recusado"):
        return 403, {"erro": "recusado: " + str(envelope.get("motivo", ""))[:200]}
    codigo = envelope.get("exit_code")
    if codigo == 0:
        if metodo == "PUT":
            return 200, {"valor": valor}
        stdout = envelope.get("stdout")
        texto = stdout.get("texto", "") if isinstance(stdout, dict) else ""
        try:
            lido = json.loads(texto)
            atual = lido["valor"]
        except (ValueError, KeyError, TypeError):
            return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
        if atual is not None and not isinstance(atual, str):
            return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
        return 200, {"valor": atual}
    if metodo == "PUT" and codigo == 2:
        return 400, {"erro": "valor fora do vocabulário"}
    if codigo == 3:
        return 401, {"erro": "sem sessão"}
    return 502, {"erro": "as preferências não responderam"}

def _resposta_da_leitura(ato, envelope):
    """`(status, corpo)` de `GET /api/faces` e `GET /api/espera-dono`, do envelope que a porta devolveu: o corpo
    é o JSON que o verbo imprimiu. Saída 0 com JSON de objeto → 200 (na lista de telas, com a chave `telas`
    em lista); `recusado` → 403; qualquer outra coisa → 502, e o único texto que sobe é o da borda."""
    if envelope.get("recusado"):
        return 403, {"erro": "recusado: " + str(envelope.get("motivo", ""))[:200]}
    if envelope.get("exit_code") != 0:
        return 502, {"erro": "a leitura não respondeu"}
    stdout = envelope.get("stdout")
    texto = stdout.get("texto", "") if isinstance(stdout, dict) else ""
    try:
        corpo = json.loads(texto)
    except (ValueError, TypeError):
        return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
    if not isinstance(corpo, dict) or (ato == "telas" and not isinstance(corpo.get("telas"), list)):
        return 502, {"erro": "a porta devolveu uma resposta fora do contrato"}
    return 200, corpo


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


# --- a declaração das telas ----------------------------------------------------------------------
def origens_das_telas(caminho, ids=()):
    """`callable() -> tuple` das origens das telas de `registro/telas.json` que esta instância atende (`ids`;
    vazio, todas). Lê de novo quando o arquivo muda; arquivo ausente ou ilegível dá tupla vazia, e a escrita de
    navegador fica recusada (a borda falha fechada). A declaração é a fonte única das telas (comentário #3062
    do #3602), e também a lista de `release telas`."""
    visto = {}

    def origens():
        try:
            mtime = os.stat(caminho).st_mtime_ns
            if visto.get("mtime") != mtime:
                with open(caminho, encoding="utf-8") as fh:
                    dado = json.load(fh)
                telas = dado.get("telas", []) if isinstance(dado, dict) else dado
                visto["mtime"] = mtime
                visto["origens"] = tuple(
                    t["origem"].strip() for t in telas
                    if isinstance(t, dict) and isinstance(t.get("origem"), str) and t["origem"].strip()
                    and (not ids or t.get("id") in ids))
        except (OSError, ValueError, TypeError, AttributeError):
            return ()
        return visto["origens"]

    return origens


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
    try:
        login_max_s = int(env.get("BORDA_LOGIN_MAX_S") or LOGIN_MAX_S)
    except ValueError:
        login_max_s = LOGIN_MAX_S
    declaracao = (env.get("BORDA_TELAS") or "").strip()
    ids = [i.strip() for i in (env.get("BORDA_TELAS_ATENDE") or "").split(",") if i.strip()]
    return Borda(faces, origens=origens, porta_url=env.get("BORDA_PORTA_URL", ""),
                 origens_da_declaracao=origens_das_telas(declaracao, ids) if declaracao else None,
                 cabecalho_token=env.get("BORDA_CABECALHO_TOKEN") or CABECALHO_DO_GATE,
                 login_max_s=max(login_max_s, 0),
                 fundamento_do_tema=(env.get("BORDA_TEMA_FUNDAMENTO") or "").strip() or FUNDAMENTO_DO_TEMA)


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
# atos: listar (leitura, texto), buscar (leitura, busca), ajuste (leitura|escrita, config), trocar (escrita, geracao), sortear (escrita, bateria)
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

    token = {CABECALHO_DO_GATE: "a.b.c"}
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
    # o padrão é o cabeçalho do gate: um Authorization posto pelo navegador não vale como token
    assert rodar("GET", "/api/motor/buscar", {"authorization": "Bearer a.b.c"})[0] == 401
    assert rodar("POST", "/api/motor/trocar", {k: v for k, v in da_tela.items() if k != CABECALHO_DO_GATE}, b"{}")[0] == 401
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
    # 9. o login do dono (#2572, #3575): a escrita com `auth_time` de mais de cinco minutos sai 401 sem chegar
    #    à porta; a leitura não tem esse corte; sem o claim a borda deixa passar e deixa a linha no stdout.
    agora = 1_000_000.0

    def jwt(**claims):
        corpo = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        return f"e30.{corpo}.assinatura"

    log9 = io.StringIO()
    com_relogio = Borda([face], origens=(origem,), chamar_porta=porta, saida=log9, agora=lambda: agora)

    def rodar9(metodo, caminho, t, corpo=b"{}", consulta=b""):
        return asyncio.run(_chamar(com_relogio, metodo, caminho, {**da_tela, CABECALHO_DO_GATE: t}, corpo, consulta))

    chamadas.clear()
    assert rodar9("POST", "/api/motor/trocar", jwt(auth_time=agora - 299))[0] == 200
    assert rodar9("POST", "/api/motor/trocar", jwt(auth_time=agora - 300))[0] == 200, "exatos cinco minutos ainda passa"
    feitas = len(chamadas)
    velho = jwt(auth_time=agora - 301, sub="dono")
    status, cab_resp, corpo = rodar9("POST", "/api/motor/trocar", velho)
    assert status == 401 and json.loads(corpo)["login"] == "antigo", (status, corpo)
    assert cab_resp["cache-control"] == "no-store" and len(chamadas) == feitas, "login antigo não chega à porta"
    assert rodar9("POST", "/api/motor/ajuste", velho)[0] == 401
    assert rodar9("GET", "/api/motor/buscar", velho, consulta=b"a=x")[0] == 200, "a leitura não tem o corte"
    assert rodar9("GET", "/api/motor/ajuste", velho, consulta=b"a=piso")[0] == 200
    assert chamadas[-1][0] == velho, "o token vai à porta como veio"
    feitas = len(chamadas)
    for sem_claim in (jwt(sub="dono"), jwt(auth_time="ontem"), jwt(auth_time=True), "a.b.c", "nao-e-jwt"):
        assert rodar9("POST", "/api/motor/trocar", sem_claim)[0] == 200, sem_claim
    assert len(chamadas) == feitas + 5
    eventos = [json.loads(linha)["evento"] for linha in log9.getvalue().splitlines()]
    assert eventos.count("login-antigo") == 2 and eventos.count("sem-auth-time") == 5, eventos
    assert "assinatura" not in log9.getvalue() and "dono" not in log9.getvalue(), "a linha de log vazou o token"
    sem_corte = Borda([face], origens=(origem,), chamar_porta=porta, saida=io.StringIO(), login_max_s=0,
                      agora=lambda: agora)
    assert asyncio.run(_chamar(sem_corte, "POST", "/api/motor/trocar", {**da_tela, CABECALHO_DO_GATE: velho}, b"{}"))[0] == 200
    assert criar_app({"BORDA_LOGIN_MAX_S": "60"}).login_max_s == 60 and criar_app({}).login_max_s == LOGIN_MAX_S
    assert criar_app({"BORDA_LOGIN_MAX_S": "x"}).login_max_s == LOGIN_MAX_S
    assert criar_app({}).cabecalho_token == CABECALHO_DO_GATE
    print("borda: escrita com login de mais de cinco minutos sai 401 na borda; leitura e sem claim passam   ok")

    # 10. a rota fixa da casca (#3738, spec taipa R40): GET devolve {valor}, PUT {valor} escolhe, pelo verbo
    #     `preferencia` da face `casca`, com o fundamento fixo da instancia e sem o corte de login recente.
    cabecalho_pref = ("#!/usr/bin/env python3\n# preferencia — verbo de mentira do self-check\n"
                      "# atos: ler (leitura, preferencia), escrever (escrita, preferencia)\n"
                      "# mecanismo: ler=casca\n# mecanismo: escrever=casca\nimport sys\n")
    pref = Face(FACE_DA_CASCA, cabecalho=cabecalho_pref, tool="preferencia")
    lidas, grava = [], {"valor": None}

    def porta10(token_, tool, argumentos):
        lidas.append((token_, tool, argumentos))
        if argumentos["ato"] == "ler":
            texto = json.dumps({"preferencia": "tema", "valor": grava["valor"],
                                "motivo": None if grava["valor"] else "sem preferência gravada"})
            return 200, {"exit_code": 0, "stdout": {"texto": texto}, "stderr": {"texto": ""}, "cwd": "/host"}
        if argumentos["args"][1] not in ("claro", "escuro", "sistema"):
            return 200, {"exit_code": 2, "stdout": {"texto": ""}, "stderr": {"texto": "fora do vocabulário"}}
        grava["valor"] = argumentos["args"][1]
        return 200, {"exit_code": 0, "stdout": {"texto": "tema: → " + grava["valor"]}}

    log10 = io.StringIO()
    casca = Borda([pref], origens=(origem,), chamar_porta=porta10, saida=log10, agora=lambda: agora,
                  fundamento_do_tema="escolha do tema na casca da tela")

    def pedir10(metodo, cabecalhos, corpo=b"", borda_=None):
        return asyncio.run(_chamar(borda_ or casca, metodo, ROTA_DO_TEMA, cabecalhos, corpo))

    velho10 = jwt(auth_time=agora - 3600, sub="dono")
    da_tela10 = {"origin": origem, "x-pf-tela": "1", "content-type": "application/json",
                 CABECALHO_DO_GATE: velho10}

    # 10a. sem preferencia gravada o GET devolve valor nulo (a casca cai no tema do sistema); o token vai
    #      como veio, o ato e o `ler` com o JSON, e nada alem disso viaja.
    status, cab_resp, corpo = pedir10("GET", {CABECALHO_DO_GATE: velho10})
    assert status == 200 and json.loads(corpo) == {"valor": None}, (status, corpo)
    assert cab_resp["cache-control"] == "no-store" and cab_resp["x-content-type-options"] == "nosniff"
    assert lidas[-1] == (velho10, "preferencia", {"ato": "ler", "args": ["tema", "--json"], "turno_fonte": "face"})

    # 10b. o PUT grava o valor com o fundamento fixo da instancia; um login de uma hora passa (sem o corte
    #      de #2572); o GET seguinte devolve o que foi escolhido.
    status, _, corpo = pedir10("PUT", da_tela10, b'{"valor": "escuro"}')
    assert status == 200 and json.loads(corpo) == {"valor": "escuro"}, (status, corpo)
    assert lidas[-1] == (velho10, "preferencia", {"ato": "escrever", "args": ["tema", "escuro"],
                                                  "turno_fonte": "face",
                                                  "turno_texto": "escolha do tema na casca da tela"}), lidas[-1]
    assert json.loads(pedir10("GET", {CABECALHO_DO_GATE: velho10})[2]) == {"valor": "escuro"}

    # 10c. o que o navegador nao pode mandar: fundamento, args, opcao, maiuscula, tipo errado, chave extra.
    feitas = len(lidas)
    for corpo_ruim in (b'{"valor": "escuro", "fundamento": "x"}', b'{"valor": "escuro", "args": []}',
                       b'{"valor": "--sujeito"}', b'{"valor": "Escuro"}', b'{"valor": "escuro claro"}',
                       b'{"valor": 1}', b'{"valor": null}', b'{}', b'["escuro"]', b"nao e json", b'{"valor": ""}',
                       b'{"valor": "' + b"a" * 17 + b'"}'):
        assert pedir10("PUT", da_tela10, corpo_ruim)[0] == 400, corpo_ruim
    assert pedir10("PUT", {**da_tela10, "content-length": str(LIMITE_CORPO_DO_TEMA + 1)},
                   b"x" * (LIMITE_CORPO_DO_TEMA + 1))[0] == 413
    assert pedir10("PUT", da_tela10, b"x" * (LIMITE_CORPO_DO_TEMA + 1))[0] == 413
    assert len(lidas) == feitas, "corpo fora da forma chegou à porta"
    # o valor com a forma certa e fora do vocabulario o verbo recusa (exit 2), e a borda diz 400
    assert pedir10("PUT", da_tela10, b'{"valor": "roxo"}')[0] == 400 and grava["valor"] == "escuro"

    # 10d. as recusas da borda valem aqui: escrita de outro site (403 antes da porta), sem token (401),
    #      sujeito do navegador no lugar do token (401), metodo fora de GET e PUT (405).
    feitas = len(lidas)
    assert pedir10("PUT", {**da_tela10, "origin": de_fora}, b'{"valor": "claro"}')[0] == 403
    assert pedir10("PUT", {k: v for k, v in da_tela10.items() if k != "x-pf-tela"}, b'{"valor": "claro"}')[0] == 403
    assert pedir10("PUT", {**da_tela10, "content-type": "text/plain"}, b'{"valor": "claro"}')[0] == 403
    assert pedir10("GET", {})[0] == 401 and pedir10("GET", {"x-auth-request-user": "dono"})[0] == 401
    assert pedir10("GET", {"authorization": "Bearer " + velho10})[0] == 401
    sem_token = {k: v for k, v in da_tela10.items() if k != CABECALHO_DO_GATE}
    assert pedir10("PUT", sem_token, b'{"valor": "claro"}')[0] == 401
    for metodo in ("POST", "DELETE", "PATCH"):
        status, cab_resp, _ = pedir10(metodo, da_tela10, b"{}")
        assert status == 405 and cab_resp["allow"] == "GET, PUT", metodo
    assert len(lidas) == feitas and grava["valor"] == "escuro", "recusa chegou à porta ou gravou"
    assert "a.b.c" not in log10.getvalue() and velho10 not in log10.getvalue(), "a linha de log vazou o token"

    # 10e. a saida do verbo vira status: 3 (sem sujeito) 401, 5 (banco mudo) 502, a recusa da porta 403,
    #      o 401 da porta passa; o banco mudo nunca vira {valor: null}.
    def com_envelope(envelope):
        b = Borda([pref], origens=(origem,), chamar_porta=lambda t, tool, a: (200, envelope), saida=io.StringIO())
        return b

    for envelope, esperado in (({"exit_code": 3, "stdout": {"texto": ""}}, 401),
                               ({"exit_code": 5, "stdout": {"texto": ""}}, 502),
                               ({"exit_code": 1, "stdout": {"texto": ""}}, 502),
                               ({"recusado": True, "motivo": "a fonte face só vale com token do client do gate"}, 403),
                               ({"exit_code": 0, "stdout": {"texto": "nao e json"}}, 502),
                               ({"exit_code": 0, "stdout": {"texto": '{"valor": 3}'}}, 502),
                               ({"exit_code": 0, "stdout": {"texto": "{}"}}, 502)):
        status, _, corpo = pedir10("GET", {CABECALHO_DO_GATE: velho10}, borda_=com_envelope(envelope))
        assert status == esperado, (envelope, status)
        assert "valor" not in json.loads(corpo) or status == 200, corpo
    assert pedir10("PUT", da_tela10, b'{"valor": "claro"}',
                   borda_=com_envelope({"exit_code": 2, "stdout": {"texto": ""}}))[0] == 400
    for status_porta in (401, 502, 504):
        fora10 = Borda([pref], origens=(origem,), saida=io.StringIO(),
                       chamar_porta=lambda t, tool, a, s=status_porta: (s, {"erro": "x"}))
        assert pedir10("GET", {CABECALHO_DO_GATE: velho10}, borda_=fora10)[0] == status_porta

    # 10f. a carga da face: sem a face `casca` a rota e 404; verbo sem o ato `ler` ou `escrever` na face e
    #      403 so naquele metodo; cabecalho que nao carrega, 503.
    assert pedir10("GET", {CABECALHO_DO_GATE: velho10},
                   borda_=Borda([face], origens=(origem,), saida=io.StringIO()))[0] == 404
    so_escrever = Face(FACE_DA_CASCA, cabecalho="# atos: ler (leitura, p), escrever (escrita, p)\n# mecanismo: escrever=casca\n")
    sem_ler = Borda([so_escrever], origens=(origem,), chamar_porta=porta10, saida=io.StringIO())
    assert pedir10("GET", {CABECALHO_DO_GATE: velho10}, borda_=sem_ler)[0] == 403
    assert pedir10("PUT", da_tela10, b'{"valor": "claro"}', borda_=sem_ler)[0] == 200
    trocados = Face(FACE_DA_CASCA, cabecalho="# atos: ler (escrita, p), escrever (leitura, p)\n# mecanismo: ler=casca\n# mecanismo: escrever=casca\n")
    invertido = Borda([trocados], origens=(origem,), chamar_porta=porta10, saida=io.StringIO())
    assert pedir10("GET", {CABECALHO_DO_GATE: velho10}, borda_=invertido)[0] == 403
    assert pedir10("PUT", da_tela10, b'{"valor": "claro"}', borda_=invertido)[0] == 403
    ilegivel = Borda([Face(FACE_DA_CASCA, verbo="/nao/existe/preferencia")], origens=(origem,), saida=io.StringIO())
    assert pedir10("GET", {CABECALHO_DO_GATE: velho10}, borda_=ilegivel)[0] == 503
    # o fundamento da instancia e configuracao: o padrao esta no codigo, a troca e por variavel de ambiente
    assert criar_app({}).fundamento_do_tema == FUNDAMENTO_DO_TEMA
    assert criar_app({"BORDA_TEMA_FUNDAMENTO": "  outro texto "}).fundamento_do_tema == "outro texto"
    assert criar_app({"BORDA_TEMA_FUNDAMENTO": "   "}).fundamento_do_tema == FUNDAMENTO_DO_TEMA
    print("borda: rota do tema da casca — GET {valor}, PUT {valor} com fundamento fixo, recusas e status   ok")
    _autoteste_das_leituras_da_casca(saida, origem, de_fora, jwt, agora)
    print("borda OK (#3516, #3518, #3575, #3738, #3899)")


def _autoteste_das_leituras_da_casca(saida, origem, de_fora, jwt, agora):
    """#3899: `GET /api/faces` (release telas), `GET /api/espera-dono` (tarefas espera-dono), a carga pela
    chave `mecanismo:` e as origens que saem da declaração das telas."""
    import tempfile

    cab_release = ("#!/usr/bin/env python3\n# release — verbo de mentira\n# atos: telas (leitura, operacao), promover (escrita, operacao)\n"
                   "# mecanismo: telas=casca\nimport sys\n")
    cab_tarefas = ("#!/usr/bin/env python3\n# tarefas — verbo de mentira\n# atos: listar, espera-dono (leitura, trabalho)\n"
                   "# mecanismo: espera-dono=casca\nimport sys\n")
    telas = {"telas": [{"id": "rastreador", "rotulo": "Rastreador", "href": "https://tarefas.exemplo.org/",
                        "posicao": 1, "face": None},
                       {"id": "casa", "rotulo": "Casa", "href": "https://casa.exemplo.org/", "posicao": 2,
                        "face": None}]}
    espera = {"do_dono": {"total": 1, "perguntas": [], "prontos_para_aposta": [], "em_homologacao": []},
              "com_cadeiras": {"abertos": 0, "orfaos": 0, "cards": []}}
    chamadas = []

    def porta(token_, tool, argumentos):
        chamadas.append((token_, tool, argumentos))
        corpo = telas if argumentos["ato"] == "telas" else espera
        return 200, {"exit_code": 0, "stdout": {"texto": json.dumps(corpo)}, "cwd": "/host"}

    def casca(*cabecalhos, chamar=porta, **k):
        verbos = [Face(FACE_DA_CASCA, cabecalho=c, tool=t) for c, t in cabecalhos]
        return Borda(verbos, origens=(origem,), chamar_porta=chamar, saida=io.StringIO(), **k)

    def pedir(borda_, metodo, caminho, cabecalhos=None, corpo=b""):
        return asyncio.run(_chamar(borda_, metodo, caminho, cabecalhos or {}, corpo))

    token = {CABECALHO_DO_GATE: jwt(auth_time=agora - 3600, sub="dono")}
    tres = casca((cab_release, "release"), (cab_tarefas, "tarefas"))

    # 11a. as duas leituras chegam à porta como `--json` do verbo dono, com o token como veio e a fonte face; o
    #      corpo da resposta é o que o verbo imprimiu, sem o que é do host.
    status, cab_resp, corpo = pedir(tres, "GET", ROTA_DAS_TELAS, token)
    assert status == 200 and json.loads(corpo) == telas, (status, corpo)
    assert cab_resp["cache-control"] == "no-store" and cab_resp["x-content-type-options"] == "nosniff"
    assert chamadas[-1] == (token[CABECALHO_DO_GATE], "release",
                            {"ato": "telas", "args": ["--json"], "turno_fonte": "face"}), chamadas[-1]
    status, _, corpo = pedir(tres, "GET", ROTA_DA_ESPERA, token)
    assert status == 200 and json.loads(corpo) == espera, (status, corpo)
    assert chamadas[-1][1:] == ("tarefas", {"ato": "espera-dono", "args": ["--json"], "turno_fonte": "face"})

    # 11b. as mesmas recusas do tema: sem token (ou com sujeito do navegador) 401, escrita de outro site 403,
    #      método fora de GET 405, e nada disso chega à porta.
    feitas = len(chamadas)
    for rota in (ROTA_DAS_TELAS, ROTA_DA_ESPERA):
        assert pedir(tres, "GET", rota)[0] == 401
        assert pedir(tres, "GET", rota, {"x-auth-request-user": "dono"})[0] == 401
        assert pedir(tres, "GET", rota, {"authorization": "Bearer a.b.c"})[0] == 401
        da_tela = {"origin": origem, "x-pf-tela": "1", "content-type": "application/json", **token}
        assert pedir(tres, "POST", rota, {**da_tela, "origin": de_fora}, b"{}")[0] == 403
        assert pedir(tres, "PUT", rota, {k: v for k, v in da_tela.items() if k != "x-pf-tela"}, b"{}")[0] == 403
        status, cab_resp, _ = pedir(tres, "POST", rota, da_tela, b"{}")
        assert status == 405 and cab_resp["allow"] == "GET", rota
    assert len(chamadas) == feitas, "recusa chegou à porta"

    # 11c. a carga é do cabeçalho, pela chave `mecanismo:`: `face: telas=casca` não carrega nada (a casca é
    #      componente, não face), o ato sem par de capacidade fica de fora, e o ato em dois verbos falha fechado.
    assert ler_cabecalho(cab_release) == {} and ler_mecanismos(cab_release) == {
        "casca": {"telas": frozenset({"leitura"})}}
    por_face = casca((cab_release.replace("# mecanismo: telas=casca", "# face: telas=casca"), "release"))
    assert pedir(por_face, "GET", ROTA_DAS_TELAS, token)[0] == 403
    sem_par = casca((cab_release.replace("telas (leitura, operacao)", "telas"), "release"))
    assert pedir(sem_par, "GET", ROTA_DAS_TELAS, token)[0] == 403
    so_escrita = casca((cab_release.replace("telas (leitura", "telas (escrita"), "release"))
    assert pedir(so_escrita, "GET", ROTA_DAS_TELAS, token)[0] == 403, "leitura de ato de escrita"
    duas = casca((cab_release, "release"), (cab_release, "outro"))
    assert pedir(duas, "GET", ROTA_DAS_TELAS, token)[0] == 503
    sem_tarefas = casca((cab_release, "release"))
    assert pedir(sem_tarefas, "GET", ROTA_DA_ESPERA, token)[0] == 403, "o ato de outro verbo não está na carga"
    assert pedir(Borda([], origens=(origem,), saida=io.StringIO()), "GET", ROTA_DAS_TELAS, token)[0] == 404
    ilegivel = Borda([Face(FACE_DA_CASCA, verbo="/nao/existe/release")], origens=(origem,), saida=io.StringIO())
    assert pedir(ilegivel, "GET", ROTA_DAS_TELAS, token)[0] == 503
    # o tema segue na mesma carga: um verbo a mais na casca não o tira do ar
    cab_pref = ("# atos: ler (leitura, p), escrever (escrita, p)\n# mecanismo: ler=casca\n# mecanismo: escrever=casca\n")
    com_tema = casca((cab_release, "release"), (cab_pref, "preferencia"), (cab_tarefas, "tarefas"),
                     chamar=lambda t, tool, a: (200, {"exit_code": 0, "stdout": {"texto": json.dumps(
                         {"valor": "escuro"} if tool == "preferencia" else telas)}}))
    assert json.loads(pedir(com_tema, "GET", ROTA_DO_TEMA, token)[2]) == {"valor": "escuro"}
    assert json.loads(pedir(com_tema, "GET", ROTA_DAS_TELAS, token)[2]) == telas

    # 11d. a saída do verbo vira status: recusa da porta 403, saída diferente de 0 502, corpo fora da forma 502
    #      (a lista leva `telas` em lista), e o status da porta passa.
    def com_envelope(envelope):
        return casca((cab_release, "release"), (cab_tarefas, "tarefas"),
                     chamar=lambda t, tool, a: (200, envelope))

    for envelope, esperado in (({"recusado": True, "motivo": "a fonte face só vale com o gate"}, 403),
                               ({"exit_code": 3, "stdout": {"texto": ""}}, 502),
                               ({"exit_code": 5, "stdout": {"texto": ""}}, 502),
                               ({"exit_code": 0, "stdout": {"texto": "nao e json"}}, 502),
                               ({"exit_code": 0, "stdout": {"texto": '{"telas": 3}'}}, 502),
                               ({"exit_code": 0, "stdout": {"texto": "[]"}}, 502)):
        assert pedir(com_envelope(envelope), "GET", ROTA_DAS_TELAS, token)[0] == esperado, envelope
    assert pedir(com_envelope({"exit_code": 0, "stdout": {"texto": "[]"}}), "GET", ROTA_DA_ESPERA, token)[0] == 502
    for status_porta in (401, 502, 504):
        fora = casca((cab_release, "release"), chamar=lambda t, tool, a, s=status_porta: (s, {"erro": "x"}))
        assert pedir(fora, "GET", ROTA_DAS_TELAS, token)[0] == status_porta

    # 11e. as origens que podem escrever saem da declaração das telas, so as que a instância atende, e a borda
    #      relê o arquivo quando ele muda; declaração ausente ou ilegível recusa toda escrita.
    with tempfile.TemporaryDirectory() as pasta:
        arquivo = os.path.join(pasta, "telas.json")

        def declarar(*ids_e_origens):
            with open(arquivo, "w", encoding="utf-8") as fh:
                json.dump({"telas": [{"id": i, "origem": o} for i, o in ids_e_origens]}, fh)
            agora_ns = time.time_ns() + len(declarar.vezes) * 1_000_000_000
            declarar.vezes.append(1)
            os.utime(arquivo, ns=(agora_ns, agora_ns))

        declarar.vezes = []
        a, b = "https://a.exemplo.org", "https://b.exemplo.org"
        declarar(("a", a), ("b", b))
        motor = Face("motor", cabecalho=CABECALHO_DE_MENTIRA)

        def borda_da(ids):
            return Borda([motor], origens=(), chamar_porta=porta, saida=io.StringIO(), login_max_s=0,
                         origens_da_declaracao=origens_das_telas(arquivo, ids))

        def escrever(borda_, de):
            cab = {"origin": de, "x-pf-tela": "1", "content-type": "application/json", **token}
            return pedir(borda_, "POST", "/api/motor/trocar", cab, b"{}")[0]

        so_a = borda_da(("a",))
        assert escrever(so_a, a) == 200 and escrever(so_a, b) == 403, "a instância só atende o que declara atender"
        todas = borda_da(())
        assert escrever(todas, a) == 200 and escrever(todas, b) == 200 and escrever(todas, de_fora) == 403
        declarar(("a", a))
        assert escrever(todas, b) == 403, "tela tirada da declaração perde a escrita sem reiniciar a borda"
        with open(arquivo, "w", encoding="utf-8") as fh:
            fh.write("nao e json")
        os.utime(arquivo, ns=(time.time_ns() + 99_000_000_000,) * 2)
        assert escrever(todas, a) == 403, "declaração ilegível falha fechada"
        os.unlink(arquivo)
        assert escrever(todas, a) == 403, "declaração ausente falha fechada"
        # a configuração da instância se soma à declaração
        declarar(("a", a))
        env = {"BORDA_ORIGENS": b, "BORDA_TELAS": arquivo, "BORDA_TELAS_ATENDE": "a",
               "BORDA_FACES": json.dumps({"motor": {"verbo": "/a/motor"}})}
        app = criar_app(env)
        app._chamar = porta
        assert app.origens == (b,) and app._origens_da_declaracao() == (a,)
        assert criar_app({}).origens == () and criar_app({})._origens_da_declaracao() == ()
    print("borda: /api/faces e /api/espera-dono pelo mecanismo da casca; origens da declaração das telas   ok")


if __name__ == "__main__":
    _autoteste()
