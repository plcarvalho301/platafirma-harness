"""poda.py — poda determinística do retorno na porta (arq:0101 §3, card #3013).

A janela degrada com o tamanho da fita, e o consumo é giros × tokens/giro. A série M3
atacou os giros; isto ataca tokens/giro, no único ponto comum às três superfícies: o
retorno de tool, na porta, ANTES de virar `tool_result`. Nada aqui depende de sessão,
compactação ou edição de contexto do fornecedor do modelo.

ORDEM (R8), e ela não é gosto: `verbo produz → lavar → deduplicar → cortar → envelope
enxuto → fita`. Lavar antes de deduplicar porque hash de conteúdo lavado é estável (o
mesmo `git status` com um `\\r` a mais não pode virar conteúdo novo); deduplicar antes
de cortar porque o delta cabe onde o inteiro não cabia.

INVARIANTES de toda poda, em ordem de dureza:
  (i)   declara-se em banda — `poda` no envelope e uma linha humana no corpo;
  (ii)  deixa alça de restauração — caminho, offset, giro;
  (iii) erro e `exit != 0` NÃO se podam, em hipótese nenhuma (`intocavel`);
  (iv)  identificador exato (caminho, URL, SHA, id) não se toca;
  (v)   lava antes de cortar;
  (vi)  resumo por LLM e mascaramento por idade ficam de fora — o retorno mais recente
        e o erro entram inteiros.

O que este módulo NÃO faz: não fala com a rede, não decide política de acesso, não
conhece FastMCP. Recebe texto e dicionário, devolve texto e dicionário — é o que o
torna testável sem subir a porta (ver `_ensaio.py`, bloco arq:0101).
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

_COMUM = Path(__file__).resolve().parent.parent / "comum"
if str(_COMUM) not in sys.path:
    sys.path.insert(0, str(_COMUM))
from hash_servido import sha_servido                          # noqa: E402

# --- réguas. Número aqui é palpite declarado, não medida: a proporção cabeça/cauda
# por tipo de verbo fecha na medição pós-implantação (arq:0101, itens abertos).
ENTRADA_MAX_X_CAP = 4        # guardrail R1: não se lava o que nem cabe na memória
LINHA_LONGA = 1_000          # acima disto a linha é blob ou é linha a janelar
BLOB_MIN = 200               # base64/hex contíguo a partir daqui vira marcador
JANELA = 120                 # ±N caracteres preservados nas pontas da linha longa
REPETE_MIN = 3               # `linha × N` só a partir daqui (2× cabe inteiro)
MOLDE_MIN = 5                # linhas no mesmo molde antes de virar 2 exemplos + conta
RG_MAX_MATCH = 5             # matches por arquivo antes de `(+N)`
RG_PROPORCAO = 0.6           # fração de linhas no formato path:linha: para tratar como busca
CABECA_FRACAO = 0.7          # com `cauda: sim`, 70% cabeça / 30% cauda (palpite declarado)
DIFF_MAX_LINHAS = 200        # diff maior que isto não é delta, é reenvio disfarçado
TTL_DERRAME_S = 48 * 3600

RAIZ = Path(os.environ.get("OPS_ROOT", os.path.expanduser("~/AI")))
DERRAME = Path(os.environ.get("PF_DERRAME", RAIZ / "var/tmp/retornos"))

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)")
_BLOB = re.compile(r"[A-Za-z0-9+/=]{%d,}|[0-9a-fA-F]{%d,}" % (BLOB_MIN, BLOB_MIN))
# `arquivo:linha:conteúdo` — e o campo do arquivo NÃO pode ter espaço nem deixar de
# parecer caminho. Sem estas duas guardas, `18:58:05` de um timestamp casa como
# arquivo `18`, linha `58`, e a saída de `journalctl` inteira era remontada como se
# fosse resultado de busca. Medido no primeiro retorno real depois de subir (06/09).
_RG_LINHA = re.compile(r"^(?P<arq>[^\s:]+):(?P<lin>\d+):(?P<resto>.*)$")
_NUMERO = re.compile(r"\d+")
# Rastro fixo de gerenciador de pacote e de git: linha que existe para o humano ver
# progresso e que nenhuma decisão jamais leu.
_RASTRO = re.compile(
    r"^\s*("
    r"Collecting |Downloading |Requirement already satisfied|Installing collected|"
    r"Using cached |Resolved \d+ packages|Downloaded \d+ packages|Prepared \d+ packages|"
    r"Installed \d+ packages|Building wheel|Created wheel|Stored in directory|"
    r"npm (WARN|notice)|added \d+ packages|audited \d+ packages|"
    r"remote: (Counting|Compressing|Total|Enumerating)|"
    r"Receiving objects:|Resolving deltas:|Unpacking objects:|Counting objects:"
    r")")
# Linha de pontos do pytest (`....sF..  [ 87%]`) — o veredito vem no rodapé, não aqui.
_PYTEST_DOTS = re.compile(r"^[.sFExX~]+\s*(\[\s*\d+%\])?$")


# ---------------------------------------------------------------- R1: lavador
def _sem_ansi(t: str) -> str:
    t = _ANSI.sub("", t)
    # `\r` de progress bar: sobra o último quadro da linha, que é o estado final.
    return "\n".join(l.split("\r")[-1] if "\r" in l else l for l in t.split("\n"))


def _marca_blob(linha: str) -> tuple[str, bool]:
    """Base64/hex longo vira marcador com sha; linha longa qualquer vira janela ±120.

    A alça aqui é o próprio sha: o inteiro está no derrame, e o que o modelo precisa
    para pedi-lo de volta é saber que existe e qual é.
    """
    m = _BLOB.search(linha)
    if m and len(m.group(0)) >= BLOB_MIN:
        bruto = m.group(0)
        tipo = "hex" if re.fullmatch(r"[0-9a-fA-F]+", bruto) else "base64"
        marca = f"<blob tipo={tipo} bytes={len(bruto)} sha={sha_servido(bruto)}>"
        return linha[:m.start()] + marca + linha[m.end():], True
    if len(linha) > LINHA_LONGA:
        return (f"{linha[:JANELA]} <linha longa bytes={len(linha)} "
                f"sha={sha_servido(linha)} …> {linha[-JANELA:]}"), True
    return linha, False


def _colapsa_repeticao(linhas: list[str]) -> tuple[list[str], int]:
    """Idêntica consecutiva → `linha × N`. Molde variando número → 2 exemplos + conta."""
    fora: list[str] = []
    cortadas = 0
    i = 0
    while i < len(linhas):
        j = i
        while j + 1 < len(linhas) and linhas[j + 1] == linhas[i]:
            j += 1
        n = j - i + 1
        if n >= REPETE_MIN:
            fora.append(f"{linhas[i]}   × {n}")
            cortadas += n - 1
            i = j + 1
            continue
        # molde: mesma linha a menos dos números
        molde = _NUMERO.sub("#", linhas[i])
        k = i
        while (k + 1 < len(linhas) and _NUMERO.sub("#", linhas[k + 1]) == molde
               and linhas[k + 1] != linhas[k]):
            k += 1
        n = k - i + 1
        if n >= MOLDE_MIN:
            fora.extend([linhas[i], linhas[i + 1]])
            fora.append(f"… +{n - 2} linhas no mesmo molde")
            cortadas += n - 3
            i = k + 1
            continue
        fora.extend(linhas[i:i + (j - i + 1)])
        i = j + 1
    return fora, cortadas


def _parece_caminho(arq: str) -> bool:
    """`src/a.py` e `README.md` são caminho; `18` (de um timestamp) não é."""
    return ("/" in arq or "." in arq) and not arq.isdigit()


def _agrupa_busca(linhas: list[str]) -> tuple[list[str], int] | None:
    """Saída de `rg`/`fd` no formato `arquivo:linha:conteúdo` agrupada por arquivo.

    Devolve None quando a saída não é busca — a heurística é a proporção de linhas no
    formato, nunca o nome do comando: `rg` chamado dentro de um pipe não se anuncia.

    LINHA QUE NÃO CASA NÃO SE PERDE. A primeira versão descartava tudo que não era
    match e devolvia só os grupos: numa saída mista, `MainPID=…` e `health=200`
    sumiam sem uma palavra — poda silenciosa é o oposto do que a régua manda. Agora
    cada grupo sai na posição da PRIMEIRA ocorrência daquele arquivo, e o que não é
    match sai onde estava, intacto.
    """
    casadas = [(_RG_LINHA.match(l), l) for l in linhas if l.strip()]
    uteis = [m for m, _ in casadas if m and _parece_caminho(m.group("arq"))]
    if not casadas or len(uteis) / len(casadas) < RG_PROPORCAO or len(uteis) < MOLDE_MIN:
        return None
    por_arq: dict[str, list[tuple[str, str]]] = {}
    roteiro: list[tuple[str, str]] = []          # ("arq", nome) | ("literal", linha)
    for linha in linhas:
        m = _RG_LINHA.match(linha)
        if m and _parece_caminho(m.group("arq")):
            arq = m.group("arq")
            if arq not in por_arq:
                por_arq[arq] = []
                roteiro.append(("arq", arq))
            por_arq[arq].append((m.group("lin"), m.group("resto")))
        else:
            roteiro.append(("literal", linha))
    fora, cortadas = [], 0
    for tipo, valor in roteiro:
        if tipo == "literal":
            fora.append(valor)
            continue
        ms = por_arq[valor]
        fora.append(f"{valor}  ({len(ms)} matches)")
        for lin, resto in ms[:RG_MAX_MATCH]:
            fora.append(f"  {lin}: {resto.strip()[:LINHA_LONGA]}")
        if len(ms) > RG_MAX_MATCH:
            fora.append(f"  … +{len(ms) - RG_MAX_MATCH} matches neste arquivo")
            cortadas += len(ms) - RG_MAX_MATCH
    return fora, cortadas


def lava(texto: str, cap: int = 50_000) -> tuple[str, dict]:
    """R1 — lavador determinístico, ANTES do teto. Devolve (lavado, relatório).

    Determinístico é o ponto: mascaramento por regra iguala resumo por LLM à metade do
    custo (Lindenbauer et al., arXiv:2508.21433) e, ao contrário do resumo, não inventa.
    """
    if not texto:
        return texto or "", {"classes": [], "bytes_antes": 0, "bytes_depois": 0}
    bruto = texto
    limite = cap * ENTRADA_MAX_X_CAP
    guardrail = len(bruto.encode("utf-8", "replace")) > limite
    if guardrail:                        # não se lava o que nem cabe: corta e declara
        bruto = bruto.encode("utf-8", "replace")[:limite].decode("utf-8", "replace")
    antes = len(bruto.encode("utf-8", "replace"))
    classes: list[str] = []

    t = _sem_ansi(bruto)
    if t != bruto:
        classes.append("terminal")
    linhas = t.split("\n")

    limpas = [l for l in linhas if not _RASTRO.match(l) and not _PYTEST_DOTS.match(l)]
    if len(limpas) != len(linhas):
        classes.append("rastro")
        linhas = limpas

    # vazias consecutivas → uma só
    enxutas: list[str] = []
    for l in linhas:
        if not l.strip() and enxutas and not enxutas[-1].strip():
            continue
        enxutas.append(l)
    if len(enxutas) != len(linhas):
        classes.append("branco")
        linhas = enxutas

    busca = _agrupa_busca(linhas)
    if busca:
        linhas, _cortadas = busca
        classes.append("busca")
    else:
        linhas, cortadas = _colapsa_repeticao(linhas)
        if cortadas:
            classes.append("repeticao")

    houve_blob = False
    fora = []
    for l in linhas:
        nova, marcou = _marca_blob(l)
        houve_blob = houve_blob or marcou
        fora.append(nova)
    if houve_blob:
        classes.append("blob")

    lavado = "\n".join(fora)
    if guardrail:
        classes.append("guardrail")
        lavado += f"\n[entrada acima de {ENTRADA_MAX_X_CAP}×CAP — lavada só a cabeça]"
    return lavado, {"classes": classes, "bytes_antes": antes,
                    "bytes_depois": len(lavado.encode("utf-8", "replace"))}


def enxuga_envelope(r: dict) -> dict:
    """R1 classe 5 / R6 — `stderr` vazio, `cwd` repetido e campo nulo saem do lote.

    `cwd` igual à raiz é o caso de 99% das chamadas: repeti-lo em todo retorno é pagar
    por uma constante. Diferente da raiz, fica: aí ele informa.
    """
    fora = {}
    for k, v in r.items():
        if v is None:
            continue
        if k == "stderr" and isinstance(v, dict) and not (v.get("texto") or "").strip():
            continue
        if k == "cwd" and str(v) == str(RAIZ):
            continue
        fora[k] = v
    return fora


# ---------------------------------------------------------------- R3: corte
def _dir_derrame(sessao_id: str) -> Path:
    d = DERRAME / (sessao_id or "sem-sessao")
    d.mkdir(parents=True, exist_ok=True)
    return d


def derrama(sessao_id: str, nome: str, texto: str) -> str | None:
    """Grava o inteiro cru, sob TTL de 48 h, e devolve o caminho relativo à raiz.

    Cru de propósito: o derrame é o que se lê de volta com `read_file offset=`, e
    formatação adicional ali é ruído a mais no giro que for buscá-lo.
    """
    try:
        alvo = _dir_derrame(sessao_id) / nome
        alvo.write_text(texto, encoding="utf-8", errors="replace")
        return str(alvo.relative_to(RAIZ)) if alvo.is_relative_to(RAIZ) else str(alvo)
    except OSError as e:                                      # noqa: BLE001
        print(f"[poda] derrame falhou ({nome}): {e!r}", file=sys.stderr, flush=True)
        return None


def prune_derrame() -> int:
    """TTL 48 h por varredura preguiçosa — quem grava também limpa o vencido."""
    limite = time.time() - TTL_DERRAME_S
    n = 0
    try:
        for p in DERRAME.rglob("*.txt"):
            try:
                if p.stat().st_mtime < limite:
                    p.unlink()
                    n += 1
            except OSError:
                pass
    except OSError:
        pass
    return n


def corta(texto: str, cap: int, *, cauda: bool, alca: str | None) -> tuple[str, dict]:
    """R3 — cabeça + cauda + derrame declarado. Substitui o corte só-de-cabeça.

    `descansar` batia o teto e era cortado só na cabeça, perdendo a cauda onde mora o
    veredito (perícia 02–06/09). Com `cauda: sim` no cabeçalho do verbo, o fim volta.
    """
    dados = texto.encode("utf-8", "replace")
    if len(dados) <= cap:
        return texto, {"cortado": False}
    if cauda:
        n_cab = int(cap * CABECA_FRACAO)
        n_cau = cap - n_cab
        cab = dados[:n_cab].decode("utf-8", "replace")
        cau = dados[-n_cau:].decode("utf-8", "replace")
    else:
        cab, cau = dados[:cap].decode("utf-8", "replace"), ""
    omitido = len(dados) - len(cab.encode()) - len(cau.encode())
    miolo = f"\n[… {omitido} bytes omitidos"
    miolo += f" — inteiro em {alca}; `read_file offset=`]" if alca else " — sem alça]"
    return cab + miolo + ("\n" + cau if cau else ""), {
        "cortado": True, "bytes_omitidos": omitido, "alca": alca, "cauda": cauda}


# ---------------------------------------------------------------- R2: ledger
class Ledger:
    """Dedup por sessão, no msg-mem — não em dicionário de processo.

    Chave `ledger:{sessao_id}`, campo = alça (o que identifica a MESMA leitura), valor
    = `{sha, giro, tool}`. Sobrevive ao restart da porta, que é o ponto: fita viva
    atravessa restart, e um ledger em RAM reenviaria tudo de novo depois dele.

    Regra única, e ela é curta: **executa sempre, serve só o delta.** Nunca se pula a
    execução por já ter servido — o mundo pode ter mudado, e o que se poupa é o
    reenvio, não o trabalho.
    """

    def __init__(self, rc, sessao_id: str, ttl: int = TTL_DERRAME_S):
        self.rc = rc
        self.sessao_id = sessao_id or ""
        self.ttl = ttl
        self.ativo = bool(rc) and bool(self.sessao_id) and self.sessao_id != "-"

    @property
    def chave(self) -> str:
        return f"ledger:{self.sessao_id}"

    def giro(self) -> int:
        if not self.ativo:
            return 0
        try:
            n = self.rc.incr(f"giro:{self.sessao_id}")
            self.rc.expire(f"giro:{self.sessao_id}", self.ttl)
            return int(n)
        except Exception:                                     # noqa: BLE001
            return 0

    def _arquivo(self, alca: str) -> Path:
        return _dir_derrame(self.sessao_id) / f"lg-{sha_servido(alca)}.txt"

    def olha(self, alca: str, lavado: str, giro: int, tool: str) -> dict:
        """Devolve o que servir: `{modo: inteiro|igual|diff, texto, ...}`.

        Três desfechos e nada além: nunca visto → inteiro; visto com o mesmo sha →
        aviso estável (SEM timestamp: aviso que muda a cada giro é conteúdo novo
        disfarçado, e volta a custar o que se queria poupar); visto e mudado → diff
        unificado contra o servido, quando o diff for menor que o inteiro.
        """
        sha = sha_servido(lavado)
        if not self.ativo:
            return {"modo": "inteiro", "texto": lavado, "sha": sha, "ledger": "sem_sessao"}
        try:
            bruto = self.rc.hget(self.chave, alca)
        except Exception:                                     # noqa: BLE001
            return {"modo": "inteiro", "texto": lavado, "sha": sha, "ledger": "indisponivel"}
        antes = {}
        if bruto:
            try:
                antes = json.loads(bruto)
            except ValueError:
                antes = {}
        if not antes:
            self._grava(alca, sha, giro, tool, lavado)
            return {"modo": "inteiro", "texto": lavado, "sha": sha, "ledger": "novo"}
        if antes.get("sha") == sha:
            # NÃO se regrava: o aviso aponta o giro do PRIMEIRO envio e tem de sair
            # idêntico na terceira e na décima releitura. Aviso que muda de número a
            # cada giro é conteúdo novo disfarçado — volta a custar o que se poupou.
            n = len(lavado.encode("utf-8", "replace"))
            aviso = (f"[igual ao giro {antes.get('giro')} — sha {sha}, "
                     f"{n} bytes não reenviados]")
            # Poda que engorda o retorno não é poda: retorno curto (um `git rev-parse`,
            # duas linhas de requirements) cabe inteiro por menos que o aviso custaria.
            if len(aviso.encode("utf-8", "replace")) >= n:
                return {"modo": "inteiro", "texto": lavado, "sha": sha, "ledger": "curto"}
            return {"modo": "igual", "sha": sha, "giro_ref": antes.get("giro"),
                    "bytes_omitidos": n, "texto": aviso, "ledger": "igual"}
        # A base do diff se lê ANTES de gravar a nova: gravar primeiro compara o texto
        # com ele mesmo e devolve `igual` para um arquivo que mudou — falso-verde caro,
        # porque o conteúdo novo não chega e nada denuncia.
        velho = ""
        try:
            velho = self._arquivo(alca).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        self._grava(alca, sha, giro, tool, lavado)
        if not velho:
            return {"modo": "inteiro", "texto": lavado, "sha": sha, "ledger": "sem_base"}
        d = list(difflib.unified_diff(velho.splitlines(), lavado.splitlines(),
                                      fromfile=f"giro {antes.get('giro')}",
                                      tofile=f"giro {giro}", lineterm="", n=1))
        corpo = "\n".join(d)
        if not d:                     # mesmo texto a menos do strip: trata como igual
            return {"modo": "igual", "sha": sha, "giro_ref": antes.get("giro"),
                    "texto": f"[igual ao giro {antes.get('giro')} — sha {sha}]",
                    "ledger": "igual"}
        if len(d) > DIFF_MAX_LINHAS or len(corpo) >= len(lavado):
            return {"modo": "inteiro", "texto": lavado, "sha": sha, "ledger": "diff_maior"}
        return {"modo": "diff", "sha": sha, "giro_ref": antes.get("giro"),
                "bytes_omitidos": len(lavado.encode("utf-8", "replace")) - len(corpo.encode()),
                "texto": f"[mudou desde o giro {antes.get('giro')} — diff unificado; "
                         f"inteiro por nova leitura]\n{corpo}",
                "ledger": "diff"}

    def _grava(self, alca: str, sha: str, giro: int, tool: str, lavado: str) -> None:
        try:
            self.rc.hset(self.chave, alca,
                         json.dumps({"sha": sha, "giro": giro, "tool": tool},
                                    ensure_ascii=False))
            self.rc.expire(self.chave, self.ttl)
            self._arquivo(alca).write_text(lavado, encoding="utf-8", errors="replace")
        except Exception as e:                                # noqa: BLE001
            print(f"[poda] ledger nao gravou: {e!r}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------- R8: orquestra
def intocavel(r: dict) -> bool:
    """Erro e `exit != 0` não se podam — invariante (iii), sem exceção nem flag.

    Quem lê um erro precisa do erro inteiro: a linha que importa costuma ser a última,
    e um erro pela metade custa o giro que o corte economizou, com juros.
    """
    return bool(r.get("erro")) or (r.get("exit_code") not in (None, 0))


def poda_texto(texto: str, *, cap: int, cauda: bool, alca: str, sessao_id: str,
               giro: int, tool: str, ledger: Ledger | None,
               nome_derrame: str) -> tuple[str, dict]:
    """Um retorno textual, a régua inteira na ordem do R8. Devolve (texto, campo `poda`)."""
    lavado, rel = lava(texto, cap)
    meta = {"ato": tool, "giro": giro, "sha": sha_servido(lavado),
            "lavado": rel["classes"], "bytes_produzidos": rel["bytes_antes"]}
    servir = lavado
    if ledger is not None:
        d = ledger.olha(alca, lavado, giro, tool)
        servir = d["texto"]
        meta["ledger"] = d.get("ledger")
        if d["modo"] != "inteiro":
            meta.update(giro_ref=d.get("giro_ref"), bytes_omitidos=d.get("bytes_omitidos"),
                        modo=d["modo"])
            meta["bytes_servidos"] = len(servir.encode("utf-8", "replace"))
            return servir, meta
    caminho = None
    if len(servir.encode("utf-8", "replace")) > cap:
        caminho = derrama(sessao_id, nome_derrame, texto)
    servir, cm = corta(servir, cap, cauda=cauda, alca=caminho)
    if cm.get("cortado"):
        meta.update(modo="corte", bytes_omitidos=cm["bytes_omitidos"], alca=caminho,
                    cauda=cauda)
    meta["bytes_servidos"] = len(servir.encode("utf-8", "replace"))
    return servir, meta


def linha_humana(meta: dict) -> str:
    """R7 nível 2 — o que o MODELO lê. O nível 1 é o campo `poda` no envelope, que é o
    que o ops log grava e o ensaio testa. Dois níveis porque são dois leitores."""
    modo = meta.get("modo")
    if modo == "igual":
        return f"poda: igual ao giro {meta.get('giro_ref')} (sha {meta.get('sha')})"
    if modo == "diff":
        return (f"poda: delta desde o giro {meta.get('giro_ref')} — "
                f"{meta.get('bytes_omitidos', 0)} bytes não reenviados")
    if modo == "corte":
        alca = meta.get("alca")
        return (f"poda: {meta.get('bytes_omitidos', 0)} bytes omitidos no miolo"
                + (f" — inteiro em {alca}" if alca else ""))
    if meta.get("lavado"):
        return "poda: lavado (" + ", ".join(meta["lavado"]) + ")"
    return ""
