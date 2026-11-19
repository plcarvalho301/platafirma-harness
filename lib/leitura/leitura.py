"""Leitura de arquivo por linha, com versão, encoding, formatos e travas (story #4342)."""
from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Any

from . import formatos as _formatos

ORCAMENTO_PADRAO = 40_000
ORCAMENTO_MAX = 200_000
FIM = "fim do arquivo"
MODOS = ("texto", "sumario", "pagina", "visivel")

_ASSINATURAS = (
    (b"%PDF-", _formatos.PDF),
    (b"PK\x03\x04", _formatos.ZIP),
    (b"PK\x05\x06", _formatos.ZIP),
    (b"PK\x07\x08", _formatos.ZIP),
    (b"\x89PNG\r\n\x1a\n", _formatos.PNG),
    (b"\xff\xd8\xff", _formatos.JPEG),
    (b"GIF87a", _formatos.GIF),
    (b"GIF89a", _formatos.GIF),
    (b"\x7fELF", "application/x-elf"),
    (b"SQLite format 3\x00", "application/vnd.sqlite3"),
)

_NOMES_SEGREDO = frozenset(
    {
        ".credentials.json",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "authorized_keys",
        ".netrc",
        ".pgpass",
        ".git-credentials",
    }
)
_SUFIXOS_SEGREDO = frozenset({".key", ".pem", ".asc", ".kdbx"})


def envelope_erro(
    exit_code: int,
    falta: str,
    proximo: str | None = None,
    **extras: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {"exit_code": exit_code, "falta": falta}
    if proximo:
        out["proximo"] = proximo
    out.update(extras)
    return out


def eh_segredo(caminho: Path, *, instancia: Path | None = None) -> bool:
    alvo = caminho.resolve(strict=False)
    nome = alvo.name
    if nome.startswith(".env") or alvo.suffix.lower() in _SUFIXOS_SEGREDO or nome in _NOMES_SEGREDO:
        return True
    raizes = [Path("/srv/platafirma")]
    if instancia is not None:
        raizes.append(instancia.parent)
    for base in raizes:
        for cand in (alvo, caminho.absolute()):
            try:
                partes = cand.relative_to(base).parts
            except ValueError:
                continue
            if len(partes) >= 2 and partes[1] == "segredos":
                return True
    return False


def _sob_fila(caminho: Path, *, instancia: Path | None = None) -> bool:
    base = (instancia or Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))) / "var" / "fila"
    alvo = caminho.resolve(strict=False)
    fila_real = base.resolve(strict=False)
    return alvo == fila_real or fila_real in alvo.parents


def _detectar_tipo(caminho: Path, cabeca: bytes) -> str:
    for sig, mime in _ASSINATURAS:
        if cabeca.startswith(sig):
            if mime == _formatos.ZIP:
                with caminho.open("rb") as fh:
                    return _formatos.tipo_do_zip(fh)
            return mime
    if b"\x00" in cabeca[:4096]:
        return "application/octet-stream"
    guess, _ = mimetypes.guess_type(str(caminho))
    return _formatos.tipo_texto(cabeca, guess or "text/plain")


def _decodificar(bruto: bytes, encoding_pedido: str | None) -> tuple[str, dict[str, Any]]:
    if encoding_pedido:
        try:
            txt = bruto.decode(encoding_pedido)
            return txt, {"decidido": encoding_pedido, "por": "pedido", "invalidos": 0, "julgado": True}
        except UnicodeDecodeError:
            txt = bruto.decode(encoding_pedido, errors="replace")
            return txt, {
                "decidido": encoding_pedido,
                "por": "pedido",
                "invalidos": txt.count("\ufffd"),
                "julgado": True,
            }
    try:
        return bruto.decode("utf-8"), {"decidido": "utf-8", "por": "estrito", "invalidos": 0, "julgado": True}
    except UnicodeDecodeError:
        try:
            return bruto.decode("cp1252"), {"decidido": "cp1252", "por": "fallback", "invalidos": 0, "julgado": True}
        except UnicodeDecodeError:
            txt = bruto.decode("utf-8", errors="replace")
            return txt, {
                "decidido": "utf-8",
                "por": "replace",
                "invalidos": txt.count("\ufffd"),
                "julgado": True,
            }


def _parse_linhas(spec: str | None, total: int) -> tuple[int, int]:
    if not spec:
        return 1, total
    s = spec.strip()
    if "-" in s:
        a, _, b = s.partition("-")
        ini = int(a) if a.strip() else 1
        fim = int(b) if b.strip() else total
    else:
        ini = fim = int(s)
    ini = max(1, ini)
    fim = max(ini, min(fim, total)) if total > 0 else 0
    return ini, fim


def ler(
    caminho: str | Path,
    *,
    linhas: str | None = None,
    paginas: str | None = None,
    termo: str | None = None,
    modo: str = "texto",
    encoding: str | None = None,
    dpi: int = _formatos.DPI_PADRAO,
    max_bytes: int | None = None,
    versao: str | None = None,
    instancia: Path | None = None,
) -> dict[str, Any]:
    p = Path(caminho)
    if eh_segredo(p, instancia=instancia):
        motivo = "segredo: fora do alcance da leitura de arquivo"
        return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
    if _sob_fila(p, instancia=instancia):
        motivo = "caminho sob a fila — use o verbo `fila`"
        return envelope_erro(4, motivo, 'fila(ato="status")', recusado=True, path=str(p), motivo=motivo)
    if not p.exists():
        return envelope_erro(1, f"arquivo não encontrado: {p}", erro="nao_existe", caminho=str(p))

    if p.is_dir():
        entradas = sorted(p.iterdir(), key=lambda x: x.name)
        if termo:
            t_low = termo.lower()
            entradas = [e for e in entradas if t_low in e.name.lower()]
        nomes = [e.name + ("/" if e.is_dir() else "") for e in entradas]
        return {
            "caminho": str(p),
            "tipo": "inode/directory",
            "entradas": nomes,
            "total": len(nomes),
            "conteudo": "\n".join(nomes),
        }

    if termo:
        return envelope_erro(
            2,
            "termo só se aplica a diretório: filtra a listagem pelo nome",
            f'ler_arquivo(caminho="{p}")',
            erro="termo só se aplica a diretório: filtra a listagem pelo nome",
            caminho=str(p),
        )

    bruto = p.read_bytes()
    ver_atual = hashlib.sha256(bruto).hexdigest()[:12]
    if versao and versao != ver_atual:
        return envelope_erro(
            1,
            f"versão mudou no disco ({versao} → {ver_atual})",
            f'ler_arquivo(caminho="{p}")',
            erro="versao_mudou",
            versao_esperada=versao,
            versao_atual=ver_atual,
            caminho=str(p),
        )

    tipo = _detectar_tipo(p, bruto[:8192])
    if tipo in _formatos.LEITORES and tipo != _formatos.HTML and tipo != _formatos.MHTML:
        extra = _formatos.extrair_texto_formato(p, tipo, paginas=paginas, modo=modo, dpi=dpi)
        if "erro" in extra:
            return envelope_erro(2, extra["erro"], caminho=str(p), tipo=tipo)
        return {
            "caminho": str(p),
            "tipo": tipo,
            "bytes_total": len(bruto),
            "versao": ver_atual,
            **extra,
        }
    if tipo == "application/octet-stream" or tipo.startswith("application/x-elf"):
        return envelope_erro(2, f"binário sem leitor ({tipo})", erro="sem_leitor", caminho=str(p), tipo=tipo)

    texto, enc_meta = _decodificar(bruto, encoding)
    todas = texto.splitlines(keepends=True)
    total_linhas = len(todas)
    orcamento = max(1024, min(int(max_bytes or ORCAMENTO_PADRAO), ORCAMENTO_MAX))

    ini, fim_pedido = _parse_linhas(linhas, total_linhas)
    selecionadas: list[str] = []
    bytes_acum = 0
    fim_real = ini - 1
    for idx in range(ini, fim_pedido + 1):
        ln = todas[idx - 1]
        b_ln = len(ln.encode("utf-8", errors="replace"))
        if selecionadas and bytes_acum + b_ln > orcamento:
            break
        selecionadas.append(ln)
        bytes_acum += b_ln
        fim_real = idx

    conteudo = "".join(selecionadas)
    chegou_fim = fim_real >= total_linhas
    proximo = (
        FIM
        if chegou_fim
        else f'ler_arquivo(caminho="{p}", linhas="{fim_real + 1}-", versao="{ver_atual}")'
    )
    out: dict[str, Any] = {
        "cabecalho": f"{p.name} · {tipo} · linhas {ini}–{fim_real} de {total_linhas} · {bytes_acum} de {len(bruto)} bytes · {enc_meta['decidido']} · versão {ver_atual}",
        "conteudo": conteudo,
        "proximo": proximo,
        "caminho": str(p),
        "bytes_total": len(bruto),
        "versao": ver_atual,
        "encoding": enc_meta,
        "tipo": tipo,
        "linhas": [ini, fim_real],
        "linhas_total": total_linhas,
    }
    if not chegou_fim:
        out["proximo_args"] = {
            "caminho": str(p),
            "linhas": f"{fim_real + 1}-",
            "versao": ver_atual,
        }
    return out
