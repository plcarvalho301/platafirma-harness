"""Poda, lavagem, ledger de sessão, derrame e resolvedor único de ato.

Requisitos cobertos:
- Resolvedor único `resolver_ato` compartilhado entre porta e poda para verbos
  com instância (ex.: `motor rag trocar` → `trocar`; `motor listar` → `listar`).
- Confirmações de escrita nunca saem deduplicadas no ledger (`[igual ao giro N]`).
- Listagens não escapam do teto rígido (`CAP_PADRAO`), com derrame em arquivo
  e `truncado` verdadeiro somente quando bytes ficaram de fora.
- Sem detecção de segredo.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CAP_PADRAO = 200 * 1024
LINHA_LONGA_LIMITE = 2_000
REPETICAO_MIN = 4
LEDGER_DISTANCIA_MAX = 15
SUFIXO_REENVIO = "inteiro=true reenvia"
SO_LE = "sim — só lê"


def poda_desligada() -> bool:
    """Retorna True quando PF_PODA=0 (ou equivalente) desliga a poda explicitamente."""
    val = os.environ.get("PF_PODA", "").strip().lower()
    return val in ("0", "false", "nao", "off")


def _ledger_distancia_max() -> int:
    bruto = os.environ.get("PF_LEDGER_DISTANCIA", "").strip()
    if bruto:
        try:
            v = int(bruto)
            if v >= 0:
                return v
        except ValueError:
            pass
    return LEDGER_DISTANCIA_MAX


def _eh_json_valido(texto: str) -> bool:
    s = texto.strip()
    if not s or s[0] not in ("{", "["):
        return False
    try:
        json.loads(s)
        return True
    except ValueError:
        return False

_RE_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_RE_BRANCOS_MULTI = re.compile(r"\n{3,}")
_RE_CHAVE = re.compile(r"^#\s*(forma|cauda|poda|instancia)\s*:\s*(\S+)", re.MULTILINE)
_RE_VOLTA = re.compile(r"^#\s*volta\s*:\s*([\w-]+)\s*=\s*(.*?)\s*$")
_RE_ATO_PAR = re.compile(r"([\w-]+)\s*\(([^,)]*),")
_FORMAS = ("json", "listagem", "relatorio", "log")

_PERFIS: dict[tuple[str, str], dict[str, Any]] = {}
_ESCREVEM: dict[tuple[str, str], frozenset[str]] = {}


def sha_servido(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8", "replace")).hexdigest()[:12]


def _instancias_declaradas(
    binario: str | Path | None = None,
    faces: dict[str, Any] | None = None,
) -> tuple[set[str], set[str]]:
    instancias: set[str] = set()
    sem_instancia: set[str] = set()
    if isinstance(faces, dict):
        for cfg in faces.values():
            if not isinstance(cfg, dict):
                continue
            inst = cfg.get("instancia")
            if isinstance(inst, str) and inst.strip():
                instancias.add(inst.strip())
            for ato_sem in cfg.get("sem_instancia") or ():
                if isinstance(ato_sem, str) and ato_sem.strip():
                    sem_instancia.add(ato_sem.strip())
    if binario:
        try:
            with open(binario, encoding="utf-8", errors="replace") as fh:
                cab = "".join(next(fh, "") for _ in range(60))
            for chave, valor in _RE_CHAVE.findall(cab):
                if chave == "instancia":
                    for item in valor.split(","):
                        if item.strip():
                            instancias.add(item.strip())
        except OSError:
            pass
    return instancias, sem_instancia


def resolver_ato(
    argv: list[str],
    *,
    binario: str | Path | None = None,
    faces: dict[str, Any] | None = None,
) -> str:
    """Resolvedor único de ato a partir do argv do verbo.

    Pula o executável (`argv[0]`) e flags (`-...`). Se o primeiro token posicional
    for uma instância declarada do verbo (ex.: `rag` em `motor rag trocar`) e houver
    um próximo token posicional, retorna esse próximo token como ato efetivo.
    """
    if not argv or len(argv) < 2:
        return ""
    instancias, sem_instancia = _instancias_declaradas(binario=binario, faces=faces)
    # Compatibilidade para o caso canônico `motor rag <ato>` mesmo sem faces explícitas
    nome_bin = Path(argv[0]).name
    if nome_bin == "motor" and not instancias:
        instancias.add("rag")
        sem_instancia.add("listar")

    posicionais = [tok for tok in argv[1:] if tok and not tok.startswith("-")]
    if not posicionais:
        return ""
    primeiro = posicionais[0]
    if primeiro in sem_instancia:
        return primeiro
    if primeiro in instancias and len(posicionais) >= 2:
        return posicionais[1]
    return primeiro


def perfil_verbo(slug: str, binario: str | Path | None) -> dict[str, Any]:
    """Lê forma, cauda e regime de poda do cabeçalho do verbo."""
    bin_str = str(binario or "")
    chave = (slug, bin_str)
    if chave in _PERFIS:
        return _PERFIS[chave]
    perfil: dict[str, Any] = {
        "forma": "listagem",
        "cauda": False,
        "poda": "inteira",
        "poda_atos": (),
    }
    if not bin_str:
        return perfil
    try:
        with open(bin_str, encoding="utf-8", errors="replace") as fh:
            cab = "".join(next(fh, "") for _ in range(40))
    except OSError:
        return perfil
    for k, valor in _RE_CHAVE.findall(cab):
        if k == "forma" and valor in _FORMAS:
            perfil["forma"] = valor
        elif k == "cauda":
            perfil["cauda"] = valor.lower() in ("sim", "1", "true")
        elif k == "poda":
            regime, _, atos = valor.partition("@")
            reg_low = regime.lower()
            if reg_low in ("cosmetica", "constitutiva"):
                perfil["poda"] = reg_low
                perfil["poda_atos"] = tuple(a for a in atos.split(",") if a)
    _PERFIS[chave] = perfil
    return perfil


def eh_cosmetica(perfil: dict[str, Any], ato: str | None) -> bool:
    if perfil.get("poda") != "cosmetica":
        return False
    atos = perfil.get("poda_atos") or ()
    return not atos or (ato or "") in atos


def eh_constitutiva(perfil: dict[str, Any], ato: str | None) -> bool:
    if perfil.get("poda") != "constitutiva":
        return False
    atos = perfil.get("poda_atos") or ()
    return not atos or (ato or "") in atos


def atos_que_escrevem(slug: str, binario: str | Path | None) -> frozenset[str]:
    """Extrai do cabeçalho do binário os atos que escrevem (cache indexado por slug+binário)."""
    bin_str = str(binario or "")
    if not bin_str:
        return frozenset()
    chave = (slug, bin_str)
    if chave in _ESCREVEM:
        return _ESCREVEM[chave]
    escrevem: set[str] = set()
    try:
        with open(bin_str, encoding="utf-8", errors="replace") as fh:
            linhas = [next(fh, "") for _ in range(80)]
    except OSError:
        # Lição c1290: não gravar frozenset() no cache quando o arquivo não abriu
        return frozenset()
    for linha in linhas:
        m_volta = _RE_VOLTA.match(linha)
        if m_volta:
            ato_v, desc = m_volta.group(1), m_volta.group(2).strip()
            if desc and desc != SO_LE:
                escrevem.add(ato_v)
        if linha.lstrip().startswith("#") and "atos:" in linha:
            for ato_p, acao in _RE_ATO_PAR.findall(linha):
                if "escrita" in acao.lower():
                    escrevem.add(ato_p)
    res = frozenset(escrevem)
    _ESCREVEM[chave] = res
    return res


def eh_escrita(slug: str, binario: str | Path | None, ato: str | None) -> bool:
    if not ato:
        return False
    return ato in atos_que_escrevem(slug, binario)


def lavar(
    texto: str,
    *,
    forma: str = "listagem",
    constitutiva: bool = False,
    preservar_branco: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Remove ruído preservando JSON válido, conteúdo sob poda constitutiva e brancos em leitura."""
    bytes_antes = len(texto.encode("utf-8", "replace"))
    classes: list[str] = []
    atual = texto

    sem_ansi = _RE_ANSI.sub("", atual)
    if sem_ansi != atual:
        classes.append("ansi")
        atual = sem_ansi

    if forma == "json" or _eh_json_valido(atual):
        return atual, {"classes": classes, "bytes_antes": bytes_antes}

    # Leitura de arquivo (`ler`) chega byte a byte; a poda de branco não se aplica a `ler`.
    if not preservar_branco:
        sem_branco = _RE_BRANCOS_MULTI.sub("\n\n", atual)
        sem_branco = "\n".join(ln.rstrip() for ln in sem_branco.split("\n"))
        if sem_branco != atual:
            classes.append("branco")
            atual = sem_branco

    if constitutiva:
        return atual, {"classes": classes, "bytes_antes": bytes_antes}

    linhas = atual.split("\n")
    novas_linhas: list[str] = []
    marcou_blob = False
    for ln in linhas:
        b = ln.encode("utf-8", "replace")
        if len(b) > LINHA_LONGA_LIMITE:
            marcou_blob = True
            h = hashlib.sha256(b).hexdigest()[:12]
            cab = ln[:120]
            rod = ln[-80:]
            novas_linhas.append(f"{cab} <linha longa bytes={len(b)} sha={h} …> {rod}")
        else:
            novas_linhas.append(ln)
    if marcou_blob:
        classes.append("blob")
    atual = "\n".join(novas_linhas)

    linhas = atual.split("\n")
    colapsadas: list[str] = []
    marcou_rep = False
    i = 0
    while i < len(linhas):
        j = i + 1
        while j < len(linhas) and linhas[j] == linhas[i] and linhas[i].strip():
            j += 1
        qtd = j - i
        if qtd >= REPETICAO_MIN:
            marcou_rep = True
            colapsadas.append(linhas[i])
            colapsadas.append(f"[… {qtd - 1} linhas idênticas omitidas]")
        else:
            colapsadas.extend(linhas[i:j])
        i = j
    if marcou_rep:
        classes.append("repeticao")
    atual = "\n".join(colapsadas)

    return atual, {"classes": classes, "bytes_antes": bytes_antes}


def derrama(
    derrame_dir: Path,
    sessao_id: str,
    nome: str,
    texto: str,
) -> str:
    pasta = Path(derrame_dir) / (sessao_id or "sem-sessao")
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / nome
    caminho.write_text(texto, encoding="utf-8", errors="replace")
    return str(caminho)


def _prefixo_utf8(bruto: bytes, limite: int) -> bytes:
    """Recorta `bruto[:limite]` sem partir sequência UTF-8 multibyte no fim."""
    if limite >= len(bruto):
        return bruto
    if limite <= 0:
        return b""
    fatia = bruto[:limite]
    n = len(fatia)
    if fatia[-1] < 0x80:
        return fatia
    i = n - 1
    while i > 0 and (n - 1 - i) < 3 and 0x80 <= fatia[i] <= 0xBF:
        i -= 1
    lider = fatia[i]
    if lider < 0xC0:
        return fatia
    esperado = 4 if lider >= 0xF0 else (3 if lider >= 0xE0 else 2)
    if n - i < esperado:
        return fatia[:i]
    return fatia


def _sufixo_utf8(bruto: bytes, limite: int) -> bytes:
    """Recorta os últimos `limite` bytes avançando até o início de caractere UTF-8."""
    if limite >= len(bruto):
        return bruto
    if limite <= 0:
        return b""
    fatia = bruto[-limite:]
    i = 0
    while i < len(fatia) and i < 3 and 0x80 <= fatia[i] <= 0xBF:
        i += 1
    return fatia[i:]


def _chamada_continuacao(alca: str | None, *, offset_continuacao: int | None = None) -> str | None:
    if not alca:
        return None
    if offset_continuacao is not None and offset_continuacao > 0:
        return f'ler_arquivo(caminho="{alca}", offset={offset_continuacao})'
    return f'ler_arquivo(caminho="{alca}")'


def corta(
    texto: str,
    cap: int,
    *,
    cauda: bool = False,
    alca: str | None = None,
    forcar_corte: bool = False,
    bytes_total_origem: int | None = None,
    offset_exato: bool = False,
) -> tuple[str, dict[str, Any]]:
    bruto = texto.encode("utf-8", "replace")
    total_efetivo = max(len(bruto), int(bytes_total_origem or 0))
    if len(bruto) <= cap and not forcar_corte:
        return texto, {"cortado": False, "bytes_omitidos": 0}

    def _montar_aviso(omitidos_v: int, como_ler_v: str | None) -> str:
        if alca:
            return (
                f"\n[AVISO: cortado por teto de {cap} bytes ({omitidos_v} de {total_efetivo} bytes omitidos); "
                f"inteiro em {alca} — {como_ler_v}]\n"
            )
        return f"\n[AVISO: cortado por teto de {cap} bytes ({omitidos_v} de {total_efetivo} bytes omitidos)]\n"

    como_ler_est = _chamada_continuacao(
        alca,
        offset_continuacao=total_efetivo if (offset_exato and not cauda) else None,
    )
    aviso_max_b = len(_montar_aviso(total_efetivo, como_ler_est).encode("utf-8"))
    disponivel = max(0, cap - aviso_max_b)

    if cauda:
        inicio_lim = disponivel // 3
        fim_lim = disponivel - inicio_lim
        pref_b = _prefixo_utf8(bruto, inicio_lim)
        suf_b = _sufixo_utf8(bruto, fim_lim)
        bytes_mantidos = len(pref_b) + len(suf_b)
        omitidos = max(1, total_efetivo - bytes_mantidos)
        como_ler = _chamada_continuacao(alca)
        aviso = _montar_aviso(omitidos, como_ler)
        servir = pref_b.decode("utf-8", "replace") + aviso + suf_b.decode("utf-8", "replace")
        if len(servir.encode("utf-8", "replace")) > cap:
            servir = _prefixo_utf8(servir.encode("utf-8", "replace"), cap).decode("utf-8", "replace")
        return servir, {
            "cortado": True,
            "bytes_omitidos": omitidos,
            "como_ler": como_ler,
        }

    pref_b = _prefixo_utf8(bruto, disponivel)
    bytes_mantidos = len(pref_b)
    omitidos = max(1, total_efetivo - bytes_mantidos)
    como_ler = _chamada_continuacao(
        alca,
        offset_continuacao=bytes_mantidos if offset_exato else None,
    )
    aviso = _montar_aviso(omitidos, como_ler)
    servir = pref_b.decode("utf-8", "replace") + aviso
    if len(servir.encode("utf-8", "replace")) > cap:
        servir = _prefixo_utf8(servir.encode("utf-8", "replace"), cap).decode("utf-8", "replace")
    return servir, {
        "cortado": True,
        "bytes_omitidos": omitidos,
        "offset_continuacao": bytes_mantidos if offset_exato else None,
        "como_ler": como_ler,
    }


class LedgerSessao:
    """Ledger persistido em JSON por sessão para deduplicação entre processos."""

    def __init__(self, caminho: Path) -> None:
        self._caminho = Path(caminho)
        self._lock_caminho = self._caminho.with_name(f".{self._caminho.name}.lock")
        self._dados = self._carregar()

    @contextlib.contextmanager
    def _trava_exclusiva(self) -> Iterator[None]:
        """Serializa leitura-modificação-escrita entre processos via flock num inode fixo."""
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._lock_caminho, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _carregar(self) -> dict[str, Any]:
        try:
            d = json.loads(self._caminho.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                d.setdefault("giro", 0)
                d.setdefault("entradas", {})
                return d
        except (OSError, ValueError):
            pass
        return {"giro": 0, "entradas": {}}

    def _salvar(self) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=".ledger-", suffix=".json", dir=str(self._caminho.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._dados, fh, ensure_ascii=False)
            os.replace(tmp, self._caminho)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def proximo_giro(self) -> int:
        with self._trava_exclusiva():
            self._dados = self._carregar()
            self._dados["giro"] = int(self._dados.get("giro") or 0) + 1
            self._salvar()
            return self._dados["giro"]

    def olha(
        self,
        alca: str,
        texto: str,
        giro: int,
        *,
        esquece: bool = False,
        escrita: bool = False,
        distancia_max: int | None = None,
    ) -> dict[str, Any]:
        h = sha_servido(texto)
        tamanho = len(texto.encode("utf-8", "replace"))
        if escrita:
            # Escrita nunca deduplica (incidente #3503)
            return {"modo": "inteiro", "ledger": "escrita", "texto": texto}
        with self._trava_exclusiva():
            self._dados = self._carregar()
            entradas: dict[str, Any] = self._dados.setdefault("entradas", {})
            anterior = entradas.get(alca)
            if not esquece and isinstance(anterior, dict) and anterior.get("sha") == h:
                giro_ref = int(anterior.get("giro") or 0)
                limite = distancia_max if distancia_max is not None else _ledger_distancia_max()
                if (giro - giro_ref) <= limite:
                    ponteiro = f"[igual ao giro {giro_ref} — sha {h}, {tamanho} bytes não reenviados; {SUFIXO_REENVIO}]"
                    return {
                        "modo": "igual",
                        "ledger": "igual",
                        "giro_ref": giro_ref,
                        "bytes_omitidos": tamanho,
                        "texto": ponteiro,
                    }
                entradas[alca] = {"sha": h, "giro": giro, "bytes": tamanho}
                self._salvar()
                return {
                    "modo": "inteiro",
                    "ledger": "expirado",
                    "giro_ref": giro_ref,
                    "texto": texto,
                }
            entradas[alca] = {"sha": h, "giro": giro, "bytes": tamanho}
            self._salvar()
            return {"modo": "inteiro", "ledger": "novo", "texto": texto}


def linha_humana(meta: dict[str, Any]) -> str:
    modo = meta.get("modo")
    if modo == "igual":
        return f"poda: igual ao giro {meta.get('giro_ref')} (sha {meta.get('sha')})"
    if modo == "derrame":
        return f"poda: retorno semântico inteiro, sem corte — cru em {meta.get('alca')}"
    if modo == "corte":
        alca = meta.get("alca")
        como_ler = meta.get("como_ler") or _chamada_continuacao(alca)
        teto = meta.get("teto_bytes")
        produzidos = meta.get("bytes_produzidos")
        omitidos = meta.get("bytes_omitidos", 0)
        detalhe = (
            f"{omitidos} de {produzidos} bytes omitidos no teto de {teto} bytes"
            if teto and produzidos
            else f"{omitidos} bytes omitidos"
        )
        return (
            f"poda — AVISO: saída cortada por teto ({detalhe})"
            + (f" — inteiro em {alca} ({como_ler})" if alca and como_ler else "")
        )
    if meta.get("lavado"):
        return "poda: lavado (" + ", ".join(meta["lavado"]) + ")"
    return ""


def podar_texto(
    texto: str,
    *,
    tool: str,
    alca: str,
    sessao_id: str,
    derrame_dir: Path,
    ledger: LedgerSessao | None = None,
    cap: int = CAP_PADRAO,
    cauda: bool = False,
    cosmetica: bool = False,
    constitutiva: bool = False,
    preservar_branco: bool = False,
    forma: str = "listagem",
    escrita: bool = False,
    esquece: bool = False,
    distancia_max: int | None = None,
    truncado_origem: bool = False,
    bytes_origem: int | None = None,
    cru_origem: str | None = None,
) -> tuple[str, dict[str, Any]]:
    giro = ledger.proximo_giro() if ledger is not None else 1
    lavado, rel = lavar(
        texto,
        forma=forma,
        constitutiva=constitutiva,
        preservar_branco=preservar_branco,
    )
    bytes_produzidos = max(int(bytes_origem or 0), rel["bytes_antes"])
    meta: dict[str, Any] = {
        "ato": tool,
        "giro": giro,
        "sha": sha_servido(lavado),
        "lavado": rel["classes"],
        "bytes_produzidos": bytes_produzidos,
    }
    if cosmetica:
        meta["perfil"] = "cosmetica"
    elif constitutiva:
        meta["perfil"] = "constitutiva"

    nome_derrame = f"g{giro:05d}-stdout.txt"
    tira_conteudo = bool({"blob", "repeticao"} & set(rel["classes"]))
    if cru_origem:
        cru: str | None = cru_origem
    elif tira_conteudo:
        cru = derrama(derrame_dir, sessao_id, nome_derrame, texto)
    else:
        cru = None
    if cru:
        meta["cru"] = cru

    servir = lavado
    # Saída já truncada pelo executor de pipe nunca pode ser resumida sem aviso de corte
    if ledger is not None and not truncado_origem:
        dec = ledger.olha(
            alca,
            lavado,
            giro,
            esquece=esquece,
            escrita=escrita,
            distancia_max=distancia_max,
        )
        servir = dec["texto"]
        meta["ledger"] = dec.get("ledger")
        if dec["modo"] != "inteiro":
            meta.update(
                giro_ref=dec.get("giro_ref"),
                bytes_omitidos=dec.get("bytes_omitidos"),
                modo=dec["modo"],
            )
            meta["bytes_servidos"] = len(servir.encode("utf-8", "replace"))
            return servir, meta
    elif ledger is not None:
        meta["ledger"] = "escrita" if escrita else "novo"

    precisa_cortar = truncado_origem or (len(servir.encode("utf-8", "replace")) > cap)
    caminho: str | None = None
    if precisa_cortar:
        caminho = cru or derrama(derrame_dir, sessao_id, nome_derrame, texto)

    # Teto rígido de saída: nenhum retorno entregue à sessão ultrapassa `cap`,
    # mesmo em perfil cosmético — o excedente vai ao derrame com aviso de corte.
    if precisa_cortar:
        servir, cm = corta(
            servir,
            cap,
            cauda=cauda,
            alca=caminho,
            forcar_corte=truncado_origem,
            bytes_total_origem=bytes_produzidos,
            offset_exato=(not rel["classes"] and not cauda),
        )
        if cm.get("cortado"):
            meta.update(
                modo="corte",
                bytes_omitidos=cm["bytes_omitidos"],
                alca=caminho,
                cauda=cauda,
                teto_bytes=cap,
            )
            if cm.get("como_ler"):
                meta["como_ler"] = cm["como_ler"]
            if cm.get("offset_continuacao") is not None:
                meta["offset_continuacao"] = cm["offset_continuacao"]

    meta["bytes_servidos"] = len(servir.encode("utf-8", "replace"))
    return servir, meta


def podar_envelope(
    envelope: dict[str, Any],
    *,
    verbo: str,
    argv: list[str],
    binario: str | Path | None,
    sessao_id: str,
    alca: str,
    derrame_dir: Path,
    ledger_dir: Path | None = None,
    cap: int = CAP_PADRAO,
    inteiro: bool = False,
    faces: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aplica poda ao envelope de retorno de um verbo, preservando teto em erro e sucesso."""
    out = dict(envelope)
    if out.get("em_andamento"):
        return out
    so = out.get("stdout")
    if not isinstance(so, dict):
        return out
    texto = str(so.get("texto") or "")
    ja_truncado = bool(so.get("truncado"))
    bytes_reais = int(so.get("bytes_total") or 0)
    cru_origem = str(so["cru"]) if so.get("cru") else None

    ato_ef = resolver_ato(argv, binario=binario, faces=faces)
    if poda_desligada():
        tamanho = max(bytes_reais, len(texto.encode("utf-8", "replace")))
        out["poda"] = {
            "desligada": True,
            "ato_efetivo": ato_ef,
            "bytes_produzidos": tamanho,
            "bytes_servidos": len(texto.encode("utf-8", "replace")),
        }
        return out

    perf = perfil_verbo(verbo, binario)
    cosmetica = eh_cosmetica(perf, ato_ef)
    constitutiva = eh_constitutiva(perf, ato_ef) or (ato_ef == "ler")
    escrita = eh_escrita(verbo, binario, ato_ef)
    ledger = (
        LedgerSessao(Path(ledger_dir) / f"{sessao_id or 'sem-sessao'}.json")
        if ledger_dir is not None
        else None
    )

    servido, meta = podar_texto(
        texto,
        tool=verbo,
        alca=alca,
        sessao_id=sessao_id,
        derrame_dir=derrame_dir,
        ledger=ledger,
        cap=cap,
        cauda=bool(perf.get("cauda")),
        cosmetica=cosmetica,
        constitutiva=constitutiva,
        preservar_branco=(ato_ef == "ler"),
        forma=str(perf.get("forma") or "listagem"),
        escrita=escrita,
        esquece=inteiro,
        truncado_origem=ja_truncado,
        bytes_origem=bytes_reais,
        cru_origem=cru_origem,
    )
    meta["ato_efetivo"] = ato_ef
    novo_so = dict(so)
    novo_so["texto"] = servido
    if meta.get("cru") and not novo_so.get("cru"):
        novo_so["cru"] = meta["cru"]
    if meta.get("alca") and not novo_so.get("cru"):
        novo_so["cru"] = meta["alca"]
    cortado_agora = meta.get("modo") == "corte"
    novo_so["truncado"] = ja_truncado or cortado_agora
    novo_so["bytes_total"] = meta["bytes_produzidos"]
    out["stdout"] = novo_so
    out["poda"] = meta
    aviso = linha_humana(meta)
    if aviso:
        out["poda_aviso"] = aviso
    if cortado_agora:
        como_ler = meta.get("como_ler")
        aviso_topo = (
            f"AVISO: saída cortada pelo teto da poda ({cap} bytes; "
            f"{meta['bytes_omitidos']} de {meta['bytes_produzidos']} bytes omitidos). "
            "O retorno está incompleto"
            + (f" — leia o restante com {como_ler}" if como_ler else "")
        )
        cab_corte: dict[str, Any] = {"aviso": aviso_topo}
        if como_ler:
            cab_corte["como_ler"] = como_ler
        out = {**cab_corte, **out}
    return out
