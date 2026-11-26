"""Borda da camada comum do ato ler — estágios 1 e 2."""
from __future__ import annotations

import base64
import codecs
import hashlib
import hmac
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .tipos import (
    ContextoChamada,
    CursorDecodificado,
    FiltroCatalogo,
    ModoLeitura,
    PedidoLer,
    PedidoListar,
    Recusa,
    SeletorParte,
    cortar_recebido,
)

ORCAMENTO_PADRAO = 40_000
ORCAMENTO_MAX = 200_000
INTEIRO_MAX = 16 * 1024 * 1024
DPI_MIN = 36
DPI_MAX = 300
DPI_PADRAO = 150
LIMITE_PADRAO = 100
LIMITE_MAX = 500
MODOS_VALIDOS = frozenset({"texto", "pagina", "sumario", "visivel"})
FORMAS_VALIDAS = frozenset({"ler", "listar"})
VERSAO_CURSOR = "v1"
_PARTES_TOKEN_CURSOR = 3

_RE_CHAVE_CANONICA = re.compile(r"^[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9._/-]*$")
_RE_SO_CLASSE = re.compile(r"^[a-z0-9][a-z0-9-]*:?$")
_RE_SLUG_CURTO = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
_RE_DRIVE_WIN = re.compile(r"^[A-Za-z]:[\\/]")
_RE_SEGREDO_INLINE = re.compile(r"(?i)(bearer\s+\S+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)")

_SEGREDO_CURSOR_PROCESSO = os.urandom(32)


class ErroBorda(Exception):
    """Coleção de recusas estruturadas da borda (saída 2)."""

    def __init__(self, recusas: Sequence[Recusa]) -> None:
        if not recusas:
            raise ValueError("ErroBorda exige ao menos uma recusa")
        self.recusas = tuple(recusas)
        self.saida = self.recusas[0].saida
        super().__init__(self.recusas[0].codigo)

    def serializar_stderr(self) -> str:
        """Serializa uma recusa em JSON de seis campos ou múltiplas em erro+erros."""
        if len(self.recusas) == 1:
            return json.dumps(self.recusas[0].campos(), ensure_ascii=False) + "\n"
        itens = [r.campos() for r in self.recusas]
        return json.dumps({"erro": itens[0], "erros": itens}, ensure_ascii=False) + "\n"


def sanitizar_recebido(valor: object) -> str:
    """Remove possíveis tokens/segredos e corta no teto de 200 caracteres."""
    texto = "" if valor is None else str(valor)
    limpo = _RE_SEGREDO_INLINE.sub("[redigido]", texto)
    return cortar_recebido(limpo)


def _chave_hmac_cursor(segredo: bytes | None = None) -> bytes:
    if segredo is not None:
        return segredo
    env_chave = os.environ.get("PF_CURSOR_CHAVE", "")
    if env_chave:
        return hashlib.sha256(env_chave.encode("utf-8")).digest()
    return _SEGREDO_CURSOR_PROCESSO


def _b64url_encode(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _b64url_decode(texto: str) -> bytes:
    pad = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode((texto + pad).encode("ascii"))


def calcular_query_hash(
    verbo: str,
    classe: str | None,
    filtros: Sequence[FiltroCatalogo],
    termo: str | None,
) -> str:
    """Calcula hash canônico SHA-256 dos filtros para amarração do cursor."""
    canon = {
        "verbo": verbo,
        "classe": classe or "",
        "filtros": sorted((f.tipo, f.nome, f.valor or "") for f in filtros),
        "termo": termo or "",
    }
    bruto = json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()


def assinar_cursor(cursor: CursorDecodificado, *, segredo: bytes | None = None) -> str:
    """Assina cursor opaco v1.<carga_base64url>.<assinatura> com HMAC-SHA256."""
    carga = {
        "sujeito": cursor.sujeito,
        "verbo": cursor.verbo,
        "classe": cursor.classe,
        "query_hash": cursor.query_hash,
        "versao_retrato": cursor.versao_retrato,
        "ultima_ordem": cursor.ultima_ordem,
        "ultima_chave": cursor.ultima_chave,
    }
    carga_b64 = _b64url_encode(json.dumps(carga, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    corpo = f"{VERSAO_CURSOR}.{carga_b64}".encode("ascii")
    mac = hmac.new(_chave_hmac_cursor(segredo), corpo, hashlib.sha256).digest()
    return f"{VERSAO_CURSOR}.{carga_b64}.{_b64url_encode(mac)}"


def validar_cursor(
    token: str,
    *,
    sujeito: str,
    verbo: str,
    classe: str,
    query_hash: str,
    segredo: bytes | None = None,
) -> CursorDecodificado | Recusa:
    """Valida integridade (HMAC em tempo constante) e amarração do cursor."""
    partes = token.split(".")
    if len(partes) != _PARTES_TOKEN_CURSOR or partes[0] != VERSAO_CURSOR:
        return _recusa_cursor_ilegivel(token)
    carga_b64, sig_b64 = partes[1], partes[2]
    try:
        corpo = f"{VERSAO_CURSOR}.{carga_b64}".encode("ascii")
        esperada = hmac.new(_chave_hmac_cursor(segredo), corpo, hashlib.sha256).digest()
        recebida = _b64url_decode(sig_b64)
        if not hmac.compare_digest(esperada, recebida):
            return _recusa_cursor_ilegivel(token)
        dados = json.loads(_b64url_decode(carga_b64).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return _recusa_cursor_ilegivel(token)

    campos_req = ("sujeito", "verbo", "classe", "query_hash", "versao_retrato", "ultima_ordem", "ultima_chave")
    if not isinstance(dados, dict) or any(k not in dados for k in campos_req):
        return _recusa_cursor_ilegivel(token)

    if (
        dados["sujeito"] != sujeito
        or dados["verbo"] != verbo
        or dados["classe"] != classe
        or dados["query_hash"] != query_hash
    ):
        return Recusa(
            saida=2,
            codigo="continuacao-divergente",
            onde="--cursor",
            recebido=sanitizar_recebido(token),
            regra="cursor-amarrado-ao-pedido",
            cura="repita a listagem com os mesmos filtros e sujeito ou reinicie sem --cursor",
            proximo=f"{verbo} listar {classe}".strip(),
        )

    return CursorDecodificado(
        versao_token=VERSAO_CURSOR,
        sujeito=str(dados["sujeito"]),
        verbo=str(dados["verbo"]),
        classe=str(dados["classe"]),
        query_hash=str(dados["query_hash"]),
        versao_retrato=str(dados["versao_retrato"]),
        ultima_ordem=dados["ultima_ordem"],
        ultima_chave=str(dados["ultima_chave"]),
    )


def _recusa_cursor_ilegivel(token: str) -> Recusa:
    return Recusa(
        saida=2,
        codigo="continuacao-ilegivel",
        onde="--cursor",
        recebido=sanitizar_recebido(token),
        regra="cursor-opaco-assinado",
        cura="use exatamente o cursor devolvido na página anterior ou omita --cursor",
        proximo="",
    )


def ler_e_fechar_token_fd(env: Mapping[str, str]) -> bytes | None:
    """Lê e fecha o descritor PF_TOKEN_FD na largada (sem validar assinatura)."""
    fd_str = (env.get("PF_TOKEN_FD") or "").strip()
    if not fd_str or not fd_str.isdigit():
        return None
    fd = int(fd_str)
    if fd <= 2:
        return None
    try:
        with os.fdopen(fd, "rb", closefd=True) as fh:
            _ = fh.read(65_536)
    except OSError:
        return None
    return None


def extrair_contexto(env: Mapping[str, str], *, verbo: str) -> ContextoChamada:
    """Estágio 1: extrai contexto e consome PF_TOKEN_FD mantendo sujeito_jwt vazio."""
    _ = ler_e_fechar_token_fd(env)
    sujeito = (env.get("PF_SUJEITO") or env.get("PF_CADEIRA") or env.get("USER") or "").strip()
    sessao_id = (env.get("PF_SESSAO_ID") or "").strip() or None
    ordem_id = (env.get("PF_ORDEM_ID") or "").strip() or None
    origem_aut = (env.get("PF_ORIGEM_AUTENTICADA") or "cli").strip()
    origem_dec = (env.get("PF_ORIGEM_DECLARADA") or origem_aut).strip()
    prazo_raw = (env.get("PF_PRAZO_MS") or "").strip()
    prazo_ms = int(prazo_raw) if prazo_raw.isdigit() and int(prazo_raw) > 0 else 30_000
    return ContextoChamada(
        sujeito_jwt=None,
        sujeito=sujeito,
        sessao_id=sessao_id,
        ordem_id=ordem_id,
        verbo=verbo,
        origem_autenticada=origem_aut,
        origem_declarada=origem_dec,
        prazo_ms=prazo_ms,
    )


def validar_lista_estrita(valor: Any, *, onde: str) -> tuple[list[str] | None, Recusa | None]:
    """Recusa texto escalar onde o contrato exige lista estrita."""
    if isinstance(valor, (str, bytes)) or not isinstance(valor, Sequence):
        return None, Recusa(
            saida=2,
            codigo="flag-invalida",
            onde=onde,
            recebido=sanitizar_recebido(valor),
            regra="lista-estrita",
            cura=f"envie uma lista de strings em {onde}, não texto escalar",
            proximo="",
        )
    itens = [str(item) for item in valor]
    return itens, None


def eh_caminho_solto(arg: str) -> bool:
    """Identifica argumento que é caminho de sistema de arquivos."""
    return (
        arg.startswith(("/", "./", "../", "~"))
        or arg in (".", "..")
        or bool(_RE_DRIVE_WIN.match(arg))
    )


def validar_chave(chave: str, *, verbo: str) -> tuple[str | None, str | None, Recusa | None]:
    """Valida a gramática de chave e membro interno opcional (<chave>!<membro>)."""
    if not chave or not chave.strip():
        return None, None, Recusa(
            saida=2,
            codigo="chave-ausente",
            onde="chave",
            recebido=sanitizar_recebido(chave),
            regra="gramatica-de-chave",
            cura="informe uma chave lógica como <classe>:<slug>",
            proximo=f"{verbo} listar",
        )
    if eh_caminho_solto(chave):
        return None, None, Recusa(
            saida=2,
            codigo="caminho-solto-recusado",
            onde="chave",
            recebido=sanitizar_recebido(chave),
            regra="chave-logica-obrigatoria",
            cura="passe a chave lógica do objeto em vez de caminho de sistema de arquivos",
            proximo="busca consultar",
        )

    base, membro = chave, None
    if "!" in chave:
        base, membro = chave.split("!", 1)
        if not membro or membro.startswith("/") or "\x00" in membro or ".." in membro.split("/"):
            return None, None, Recusa(
                saida=2,
                codigo="chave-mal-formada",
                onde="chave",
                recebido=sanitizar_recebido(chave),
                regra="membro-interno-posix",
                cura="use caminho relativo POSIX em <chave>!<membro> sem '/' inicial nem '..'",
                proximo=f"{verbo} ler {base}" if _RE_CHAVE_CANONICA.match(base) else "",
            )

    if _RE_CHAVE_CANONICA.match(base) or _RE_SO_CLASSE.match(base) or _RE_SLUG_CURTO.match(base):
        return base, membro, None

    return None, None, Recusa(
        saida=2,
        codigo="chave-mal-formada",
        onde="chave",
        recebido=sanitizar_recebido(chave),
        regra="gramatica-de-chave",
        cura="use <classe>:<slug>, <classe>: ou identificador curto válido",
        proximo="",
    )


def parsear_faixa(
    valor: str, *, onde: str
) -> tuple[tuple[int, int | None] | None, int | None, Recusa | None]:
    """Analisa faixa em base 1 inclusiva: N, N-M (1 <= N <= M), N- ou -N."""
    s = valor.strip()
    if not s:
        return None, None, _recusa_flag_invalida(onde, valor, "informe N, N-M, N- ou -N (>= 1)")
    if s.startswith("-"):
        resto = s[1:]
        if resto.isdigit() and int(resto) >= 1:
            return None, int(resto), None
        return None, None, _recusa_flag_invalida(onde, valor, "cauda -N exige inteiro >= 1")
    if "-" in s:
        partes = s.split("-", 1)
        ini_s, fim_s = partes[0], partes[1]
        if not ini_s.isdigit() or int(ini_s) < 1:
            return None, None, _recusa_flag_invalida(onde, valor, "início da faixa deve ser >= 1")
        ini = int(ini_s)
        if fim_s == "":
            return (ini, None), None, None
        if not fim_s.isdigit() or int(fim_s) < ini:
            return None, None, _recusa_flag_invalida(onde, valor, "fim da faixa deve ser >= início")
        return (ini, int(fim_s)), None, None
    if s.isdigit() and int(s) >= 1:
        n = int(s)
        return (n, n), None, None
    return None, None, _recusa_flag_invalida(onde, valor, "formato de faixa inválido (use N, N-M, N- ou -N)")


def _recusa_flag_invalida(onde: str, recebido: object, cura: str) -> Recusa:
    return Recusa(
        saida=2,
        codigo="flag-invalida",
        onde=onde,
        recebido=sanitizar_recebido(recebido),
        regra="valor-de-flag",
        cura=cura,
        proximo="",
    )


def _recusa_combinacao(onde: str, recebido: object, cura: str) -> Recusa:
    return Recusa(
        saida=2,
        codigo="combinacao-invalida",
        onde=onde,
        recebido=sanitizar_recebido(recebido),
        regra="combinacao-de-flags",
        cura=cura,
        proximo="",
    )


@dataclass
class _EstadoLer:
    posicionais: list[str] = field(default_factory=list)
    modo: ModoLeitura = "texto"
    linhas: tuple[int, int | None] | None = None
    cauda_linhas: int | None = None
    paginas: tuple[int, int | None] | None = None
    cauda_paginas: int | None = None
    offset: int | None = None
    max_bytes: int = ORCAMENTO_PADRAO
    max_bytes_explicito: bool = False
    inteiro: bool = False
    dpi: int = DPI_PADRAO
    dpi_explicito: bool = False
    encoding: str | None = None
    versao_pedida: str | None = None
    com_decisoes_ancestrais: bool = False
    como_json: bool = False
    avisos: list[str] = field(default_factory=list)
    erros: list[Recusa] = field(default_factory=list)


_FLAGS_VALOR_LER = frozenset(
    {"--linhas", "--paginas", "--offset", "--max-bytes", "--modo", "--dpi", "--encoding", "--versao"}
)
_FLAGS_BOOL_LER = frozenset({"--inteiro", "--com-decisoes-ancestrais", "--json"})


def _aplicar_flag_ler(est: _EstadoLer, flag: str, valor: str | None) -> None:
    if flag == "--inteiro":
        est.inteiro = True
        return
    if flag == "--com-decisoes-ancestrais":
        est.com_decisoes_ancestrais = True
        return
    if flag == "--json":
        est.como_json = True
        return
    if valor is None:
        est.erros.append(_recusa_flag_invalida(flag, "", f"{flag} exige um valor"))
        return
    _aplicar_flag_valor_ler(est, flag, valor)


def _aplicar_flag_valor_ler(est: _EstadoLer, flag: str, valor: str) -> None:
    if flag == "--linhas":
        faixa, cauda, err = parsear_faixa(valor, onde="--linhas")
        if err:
            est.erros.append(err)
        else:
            est.linhas, est.cauda_linhas = faixa, cauda
        return
    if flag == "--paginas":
        faixa, cauda, err = parsear_faixa(valor, onde="--paginas")
        if err:
            est.erros.append(err)
        else:
            est.paginas, est.cauda_paginas = faixa, cauda
        return
    if flag == "--offset":
        if not valor.isdigit():
            est.erros.append(_recusa_flag_invalida("--offset", valor, "--offset exige inteiro >= 0"))
        else:
            est.offset = int(valor)
        return
    if flag == "--max-bytes":
        _aplicar_max_bytes(est, valor)
        return
    _aplicar_flag_extra_ler(est, flag, valor)


def _aplicar_max_bytes(est: _EstadoLer, valor: str) -> None:
    if not valor.lstrip("-").isdigit() or int(valor) <= 0:
        est.erros.append(_recusa_flag_invalida("--max-bytes", valor, "--max-bytes exige inteiro > 0"))
        return
    est.max_bytes_explicito = True
    n = int(valor)
    if n > ORCAMENTO_MAX:
        est.max_bytes = ORCAMENTO_MAX
        est.avisos.append(f"max_bytes reduzido para o teto de {ORCAMENTO_MAX} bytes")
    else:
        est.max_bytes = n


def _aplicar_flag_extra_ler(est: _EstadoLer, flag: str, valor: str) -> None:
    if flag == "--modo":
        if valor not in MODOS_VALIDOS:
            est.erros.append(_recusa_flag_invalida("--modo", valor, "use texto, pagina, sumario ou visivel"))
        else:
            est.modo = valor  # type: ignore[assignment]
        return
    if flag == "--dpi":
        est.dpi_explicito = True
        if not valor.isdigit() or not (DPI_MIN <= int(valor) <= DPI_MAX):
            est.erros.append(_recusa_flag_invalida("--dpi", valor, f"--dpi exige inteiro entre {DPI_MIN} e {DPI_MAX}"))
        else:
            est.dpi = int(valor)
        return
    if flag == "--encoding":
        try:
            codecs.lookup(valor)
            est.encoding = valor
        except LookupError:
            est.erros.append(_recusa_flag_invalida("--encoding", valor, "informe um codificador Python conhecido"))
        return
    if flag == "--versao":
        if not valor.strip():
            est.erros.append(_recusa_flag_invalida("--versao", valor, "--versao exige identificador não vazio"))
        else:
            est.versao_pedida = valor.strip()


def _validar_combinacoes_ler(est: _EstadoLer) -> None:
    tem_linhas = est.linhas is not None or est.cauda_linhas is not None
    tem_paginas = est.paginas is not None or est.cauda_paginas is not None
    if tem_linhas and tem_paginas:
        est.erros.append(_recusa_combinacao("--linhas/--paginas", "--linhas + --paginas", "use apenas --linhas ou --paginas"))
    if tem_linhas and est.offset is not None:
        est.erros.append(_recusa_combinacao("--linhas/--offset", "--linhas + --offset", "use apenas --linhas ou --offset"))
    if est.dpi_explicito and est.modo != "pagina":
        est.erros.append(_recusa_combinacao("--dpi", f"--dpi {est.dpi} sem --modo pagina", "combine --dpi apenas com --modo pagina"))


def _parsear_ler(argv: Sequence[str], *, verbo: str) -> PedidoLer:
    est = _EstadoLer()
    i = 0
    fim_flags = False
    while i < len(argv):
        tok = argv[i]
        if not fim_flags and tok == "--":
            fim_flags = True
            i += 1
            continue
        if not fim_flags and tok.startswith("-"):
            if tok in _FLAGS_BOOL_LER:
                _aplicar_flag_ler(est, tok, None)
                i += 1
            elif tok in _FLAGS_VALOR_LER:
                val = argv[i + 1] if i + 1 < len(argv) else None
                _aplicar_flag_ler(est, tok, val)
                i += 2 if val is not None else 1
            else:
                est.erros.append(
                    Recusa(
                        saida=2,
                        codigo="flag-desconhecida",
                        onde=tok,
                        recebido=sanitizar_recebido(tok),
                        regra="flags-do-ato-ler",
                        cura="remova a flag desconhecida",
                        proximo="",
                    )
                )
                i += 1
            continue
        est.posicionais.append(tok)
        i += 1

    _validar_combinacoes_ler(est)
    classe, chaves, membro = _extrair_chaves_ler(est, verbo=verbo)
    if est.erros:
        raise ErroBorda(est.erros)

    max_bytes = INTEIRO_MAX if (est.inteiro and not est.max_bytes_explicito) else est.max_bytes
    seletor = SeletorParte(
        modo=est.modo,
        linhas=est.linhas,
        cauda_linhas=est.cauda_linhas,
        paginas=est.paginas,
        cauda_paginas=est.cauda_paginas,
        offset=est.offset,
        max_bytes=max_bytes,
        inteiro=est.inteiro,
        dpi=est.dpi,
        encoding=est.encoding,
        versao_pedida=est.versao_pedida,
        membro=membro,
        com_decisoes_ancestrais=est.com_decisoes_ancestrais,
    )
    return PedidoLer(
        verbo=verbo,
        classe=classe,
        chaves=tuple(chaves),
        seletor=seletor,
        como_json=est.como_json,
        avisos_borda=tuple(est.avisos),
    )


def _extrair_chaves_ler(est: _EstadoLer, *, verbo: str) -> tuple[str | None, list[str], str | None]:
    if not est.posicionais:
        est.erros.append(
            Recusa(
                saida=2,
                codigo="chave-ausente",
                onde="chave",
                recebido="",
                regra="chave-obrigatoria-no-ler",
                cura="informe ao menos uma chave lógica",
                proximo=f"{verbo} listar",
            )
        )
        return None, [], None

    classe: str | None = None
    brutas = list(est.posicionais)
    if len(brutas) >= 2 and ":" not in brutas[0] and not eh_caminho_solto(brutas[0]) and _RE_SLUG_CURTO.match(brutas[0]):
        if not eh_caminho_solto(brutas[1]) and ":" not in brutas[1]:
            classe = brutas[0]
            brutas = brutas[1:]

    chaves_ok: list[str] = []
    membro_unico: str | None = None
    for ch in brutas:
        base, mem, err = validar_chave(ch, verbo=verbo)
        if err:
            est.erros.append(err)
            continue
        assert base is not None
        chaves_ok.append(ch)
        if mem is not None and membro_unico is None:
            membro_unico = mem
    return classe, chaves_ok, membro_unico


@dataclass
class _EstadoListar:
    posicionais: list[str] = field(default_factory=list)
    filtros: list[FiltroCatalogo] = field(default_factory=list)
    termo: str | None = None
    limite: int = LIMITE_PADRAO
    cursor_raw: str | None = None
    como_json: bool = False
    avisos: list[str] = field(default_factory=list)
    erros: list[Recusa] = field(default_factory=list)


_FLAGS_VALOR_LISTAR = frozenset(
    {"--prop", "--sem-prop", "--ligacao", "--sem-ligacao", "--estado", "--filhas", "--termo", "--limite", "--cursor"}
)


def _aplicar_flag_listar(est: _EstadoListar, flag: str, valor: str | None) -> None:
    if flag == "--json":
        est.como_json = True
        return
    if valor is None:
        est.erros.append(_recusa_flag_invalida(flag, "", f"{flag} exige um valor"))
        return
    if flag in ("--prop", "--ligacao"):
        if "=" not in valor or not valor.split("=", 1)[0].strip():
            est.erros.append(_recusa_flag_invalida(flag, valor, f"use {flag} <nome>=<valor>"))
            return
        nome, val = valor.split("=", 1)
        tipo = "prop" if flag == "--prop" else "ligacao"
        est.filtros.append(FiltroCatalogo(tipo=tipo, nome=nome.strip(), valor=val.strip()))
        return
    if flag in ("--sem-prop", "--sem-ligacao", "--estado", "--filhas"):
        mapa = {"--sem-prop": "sem_prop", "--sem-ligacao": "sem_ligacao", "--estado": "estado", "--filhas": "filhas"}
        est.filtros.append(FiltroCatalogo(tipo=mapa[flag], nome=valor.strip(), valor=None))  # type: ignore[arg-type]
        return
    if flag == "--termo":
        est.termo = valor
        return
    if flag == "--limite":
        if not valor.lstrip("-").isdigit() or int(valor) <= 0:
            est.erros.append(_recusa_flag_invalida("--limite", valor, "--limite exige inteiro > 0"))
            return
        n = int(valor)
        if n > LIMITE_MAX:
            est.limite = LIMITE_MAX
            est.avisos.append(f"limite reduzido para o teto de {LIMITE_MAX} itens")
        else:
            est.limite = n
        return
    if flag == "--cursor":
        est.cursor_raw = valor


def _parsear_listar(
    argv: Sequence[str],
    *,
    ctx: ContextoChamada,
    segredo_cursor: bytes | None = None,
) -> PedidoListar:
    est = _EstadoListar()
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--json":
            _aplicar_flag_listar(est, tok, None)
            i += 1
        elif tok in _FLAGS_VALOR_LISTAR:
            val = argv[i + 1] if i + 1 < len(argv) else None
            _aplicar_flag_listar(est, tok, val)
            i += 2 if val is not None else 1
        elif tok.startswith("-"):
            est.erros.append(
                Recusa(
                    saida=2,
                    codigo="flag-desconhecida",
                    onde=tok,
                    recebido=sanitizar_recebido(tok),
                    regra="flags-do-ato-listar",
                    cura="remova a flag desconhecida",
                    proximo="",
                )
            )
            i += 1
        else:
            est.posicionais.append(tok)
            i += 1

    if len(est.posicionais) > 1:
        est.erros.append(
            Recusa(
                saida=2,
                codigo="chave-mal-formada",
                onde="argumentos",
                recebido=sanitizar_recebido(" ".join(est.posicionais[1:])),
                regra="listar-sem-chaves-posicionais",
                cura="listar aceita no máximo o nome da classe em posição",
                proximo=f"{ctx.verbo} listar {est.posicionais[0]}",
            )
        )
    classe = est.posicionais[0] if est.posicionais else None
    cursor_dec: CursorDecodificado | None = None
    if est.cursor_raw is not None:
        qhash = calcular_query_hash(ctx.verbo, classe, est.filtros, est.termo)
        res_cur = validar_cursor(
            est.cursor_raw,
            sujeito=ctx.sujeito,
            verbo=ctx.verbo,
            classe=classe or "",
            query_hash=qhash,
            segredo=segredo_cursor,
        )
        if isinstance(res_cur, Recusa):
            est.erros.append(res_cur)
        else:
            cursor_dec = res_cur

    if est.erros:
        raise ErroBorda(est.erros)

    return PedidoListar(
        verbo=ctx.verbo,
        classe=classe,
        filtros=tuple(est.filtros),
        termo=est.termo,
        limite=est.limite,
        cursor=cursor_dec,
        como_json=est.como_json,
        avisos_borda=tuple(est.avisos),
    )


def parsear_chamada_ler(
    argv: Sequence[str],
    env: Mapping[str, str],
    *,
    verbo: str = "busca",
    segredo_cursor: bytes | None = None,
) -> tuple[ContextoChamada, PedidoLer | PedidoListar]:
    """Estágios 1 e 2: lê PF_TOKEN_FD e converte argv em ContextoChamada + Pedido."""
    ctx = extrair_contexto(env, verbo=verbo)
    if not argv:
        raise ErroBorda(
            [
                Recusa(
                    saida=2,
                    codigo="ato-nao-aceito",
                    onde="ato",
                    recebido="",
                    regra="forma-obrigatoria",
                    cura="informe a forma ler ou listar",
                    proximo=f"{verbo} listar",
                )
            ]
        )

    forma = argv[0]
    resto = argv[1:]
    if forma not in FORMAS_VALIDAS:
        raise ErroBorda(
            [
                Recusa(
                    saida=2,
                    codigo="ato-nao-aceito",
                    onde="ato",
                    recebido=sanitizar_recebido(forma),
                    regra="formas-do-ato-ler",
                    cura="use ler ou listar",
                    proximo=f"{verbo} ler",
                )
            ]
        )
    if forma == "ler":
        return ctx, _parsear_ler(resto, verbo=verbo)
    return ctx, _parsear_listar(resto, ctx=ctx, segredo_cursor=segredo_cursor)
