"""Fachada da camada comum do ato escrever e variante legada para write_file."""
from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from leitura.leitura import envelope_erro
from leitura.morada import ESCRITA_TETO, resolver_escrita

from .cliente import ConfigCliente, enviar_escrita
from .pedido import parsear_pedido
from .politica import PoliticaEscrita, carregar_politica, verbo_ligado
from .tipos import (
    ContextoEscrita,
    ErroEscrita,
    PedidoEscrita,
    RecusaEscrita,
    ResultadoEscrita,
)

_RE_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_MAX_DELTA_LEGADO = 51
_MODO_EXEC_LEGADO = (
    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
)


@dataclass(frozen=True)
class OpcoesExecucao:
    """Opções de despacho da fachada da camada comum do ato escrever."""

    contexto: ContextoEscrita | None = None
    politica: PoliticaEscrita | None = None
    socket_path: Path | None = None
    folga_s: float = 2.0
    fallback_desligado: Callable[[PedidoEscrita], ResultadoEscrita] | None = None


def verbo_esta_ligado(verbo: str, *, politica: PoliticaEscrita | None = None) -> bool:
    """Informa se o verbo está ativado em `registro/escrita.yaml`."""
    pol = carregar_politica() if politica is None else politica
    return verbo_ligado(pol, verbo)


def executar_ato_escrever(
    verbo: str,
    argv: Sequence[str],
    stdin_bytes: bytes | None,
    *,
    opcoes: OpcoesExecucao | None = None,
) -> ResultadoEscrita:
    """Ponto único da camada comum: valida na borda e delega ao escritor quando ligado."""
    opt = OpcoesExecucao() if opcoes is None else opcoes
    pol = carregar_politica() if opt.politica is None else opt.politica
    ctx = ContextoEscrita(verbo=verbo) if opt.contexto is None else opt.contexto
    pedido = parsear_pedido(verbo, argv, stdin_bytes, politica=pol, contexto=ctx)
    if not verbo_ligado(pol, verbo):
        if opt.fallback_desligado is not None:
            return opt.fallback_desligado(pedido)
        raise RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="escritor-indisponivel",
                onde="verbos_ligados",
                recebido=verbo,
                regra=f"verbo {verbo} ainda não está ligado ao escritor em registro/escrita.yaml",
                cura="use o caminho legado do verbo ou ative o verbo em registro/escrita.yaml",
                proximo="",
            )
        )
    cfg = ConfigCliente(politica=pol, socket_path=opt.socket_path, folga_s=opt.folga_s)
    return enviar_escrita(pedido, argv, stdin_bytes, cfg)


def _gravar_atomico(
    caminho: Path,
    conteudo: str,
    *,
    executavel: bool = False,
) -> tuple[int, str]:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = conteudo.encode("utf-8")
    fd, tmp_nome = tempfile.mkstemp(prefix=".wf-", suffix=".tmp", dir=str(caminho.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dados)
        if executavel:
            os.chmod(tmp_nome, _MODO_EXEC_LEGADO)
        if caminho.is_symlink():
            raise PermissionError("alvo e symlink — write_file nao escreve atraves de link")
        os.replace(tmp_nome, caminho)
    except OSError:
        try:
            os.unlink(tmp_nome)
        except OSError:
            pass
        raise
    return len(dados), hashlib.sha256(dados).hexdigest()


def _consumir_linhas_hunk(
    linhas: list[str], idx: int, old_count: int, new_count: int
) -> tuple[list[str], int]:
    rem_old, rem_new = old_count, new_count
    hunk_lines: list[str] = []
    while idx < len(linhas) and (rem_old > 0 or rem_new > 0):
        hl = linhas[idx]
        if hl.startswith("\\"):
            hunk_lines.append(hl)
        elif hl.startswith(" ") and rem_old > 0 and rem_new > 0:
            hunk_lines.append(hl)
            rem_old -= 1
            rem_new -= 1
        elif hl.startswith("-") and rem_old > 0:
            hunk_lines.append(hl)
            rem_old -= 1
        elif hl.startswith("+") and rem_new > 0:
            hunk_lines.append(hl)
            rem_new -= 1
        else:
            break
        idx += 1
    return hunk_lines, idx


def _parsear_bloco_arquivo_legado(
    linhas: list[str], idx: int
) -> tuple[dict[str, Any], int]:
    old_p = linhas[idx][4:].strip().split("\t")[0].removeprefix("a/")
    new_p = linhas[idx + 1][4:].strip().split("\t")[0].removeprefix("b/")
    idx += 2
    hunks: list[dict[str, Any]] = []
    invalidos: list[str] = []
    while idx < len(linhas) and not linhas[idx].startswith("--- "):
        m = _RE_HUNK.match(linhas[idx])
        if not m:
            if linhas[idx].startswith("@@"):
                invalidos.append(linhas[idx].strip())
            idx += 1
            continue
        old_start = int(m.group(1))
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        new_start = int(m.group(3))
        new_count = int(m.group(4)) if m.group(4) is not None else 1
        hunk_lines, idx = _consumir_linhas_hunk(linhas, idx + 1, old_count, new_count)
        hunks.append(
            {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "lines": hunk_lines,
            }
        )
    return (
        {
            "old_path": old_p,
            "new_path": new_p,
            "hunks": hunks,
            "hunks_invalidos": invalidos,
        },
        idx,
    )


def parse_patch(patch_texto: str) -> list[dict[str, Any]]:
    """Parser legado de unified diff preservado para a variante depreciada write_file."""
    linhas = patch_texto.splitlines(keepends=True)
    arquivos: list[dict[str, Any]] = []
    idx = 0
    while idx < len(linhas):
        tem_par = (
            linhas[idx].startswith("--- ")
            and idx + 1 < len(linhas)
            and linhas[idx + 1].startswith("+++ ")
        )
        if tem_par:
            bloco, idx = _parsear_bloco_arquivo_legado(linhas, idx)
            arquivos.append(bloco)
        else:
            idx += 1
    return arquivos


def _extrair_esperadas_e_novas(hunk_lines: list[str]) -> tuple[list[str], list[str]]:
    esperadas: list[str] = []
    novas: list[str] = []
    ultimo_tipo = ""
    for hl in hunk_lines:
        if hl.startswith("\\"):
            if ultimo_tipo in (" ", "-") and esperadas:
                esperadas[-1] = esperadas[-1].rstrip("\r\n")
            if ultimo_tipo in (" ", "+") and novas:
                novas[-1] = novas[-1].rstrip("\r\n")
            continue
        tag, body = hl[0], hl[1:]
        ultimo_tipo = tag
        if tag in (" ", "-"):
            esperadas.append(body)
        if tag in (" ", "+"):
            novas.append(body)
    return esperadas, novas


def _localizar_hunk_legado(
    linhas: list[str], esperadas: list[str], alvo_idx: int
) -> int | None:
    max_idx = len(linhas) - len(esperadas)
    for delta in range(_MAX_DELTA_LEGADO):
        cands = (alvo_idx,) if delta == 0 else (alvo_idx + delta, alvo_idx - delta)
        for cand in cands:
            if 0 <= cand <= max_idx and linhas[cand : cand + len(esperadas)] == esperadas:
                return cand
    return None


def aplicar_hunks(
    atual: str, hunks: list[dict[str, Any]], *, novo_arquivo: bool = False
) -> tuple[str | None, str | None]:
    """Aplicador legado de hunks preservado para a variante depreciada write_file."""
    if not hunks:
        return None, "patch sem hunks válidos"
    linhas = [] if (novo_arquivo and atual == "") else atual.splitlines(keepends=True)
    offset = 0
    for h in hunks:
        if not h.get("lines"):
            return None, f"patch: hunk @@ -{h['old_start']} +{h['new_start']} @@ vazio ou malformado"
        esperadas, novas = _extrair_esperadas_e_novas(h["lines"])
        if not esperadas:
            idx: int | None = (
                0 if novo_arquivo else max(0, min(len(linhas), h["old_start"] - 1 + offset))
            )
        else:
            idx = _localizar_hunk_legado(linhas, esperadas, max(0, h["old_start"] - 1 + offset))
        if idx is None:
            return None, f"patch: hunk @@ -{h['old_start']} +{h['new_start']} @@ não casa no arquivo"
        linhas[idx : idx + len(esperadas)] = novas
        offset += len(novas) - len(esperadas)
    return "".join(linhas), None


def _validar_final(texto: str, *, path_str: str, exige_shebang: bool) -> dict[str, Any] | None:
    if exige_shebang and not texto.startswith("#!"):
        motivo = "executavel sem extensao exige primeira linha #!"
        return envelope_erro(4, motivo, recusado=True, path=path_str, motivo=motivo)
    nbytes = len(texto.encode("utf-8"))
    if nbytes > ESCRITA_TETO:
        motivo = f"conteudo excede teto de {ESCRITA_TETO} bytes ({nbytes})"
        return envelope_erro(4, motivo, recusado=True, path=path_str, motivo=motivo)
    return None


def _gravar_com_validacao(
    p: Path, texto: str, *, exige_shebang: bool, extras: dict[str, Any] | None = None
) -> dict[str, Any]:
    err_fin = _validar_final(texto, path_str=str(p), exige_shebang=exige_shebang)
    if err_fin:
        return err_fin
    substituiu = p.exists()
    try:
        nbytes, sha = _gravar_atomico(p, texto, executavel=exige_shebang)
    except PermissionError as exc:
        return envelope_erro(4, str(exc), recusado=True, path=str(p), motivo=str(exc))
    out: dict[str, Any] = {
        "ok": True,
        "path": str(p),
        "bytes": nbytes,
        "substituiu": substituiu,
        "sha256": sha,
    }
    if extras:
        out.update(extras)
    return out


def _escrever_patch_legado(p: Path, patch: str, *, exige_shebang: bool) -> dict[str, Any]:
    dica = "use unified diff com números de linha (@@ -l,c +l,c @@) ou o parâmetro trecho"
    arquivos = parse_patch(patch)
    if not arquivos:
        return envelope_erro(2, "patch sem hunks válidos", proximo=dica, path=str(p))
    entry = arquivos[0]
    if entry.get("hunks_invalidos"):
        cab = entry["hunks_invalidos"][0]
        return envelope_erro(2, f"patch com cabeçalho de hunk inválido ({cab})", proximo=dica, path=str(p))
    if not entry["hunks"]:
        return envelope_erro(2, "patch sem hunks válidos", proximo=dica, path=str(p))
    novo_arq = entry["old_path"] == "/dev/null"
    atual = "" if novo_arq or not p.exists() else p.read_text(encoding="utf-8")
    novo_txt, err = aplicar_hunks(atual, entry["hunks"], novo_arquivo=novo_arq)
    if err or novo_txt is None:
        return envelope_erro(1, err or "falha ao aplicar patch", path=str(p))
    if not novo_arq and novo_txt == atual:
        return envelope_erro(1, "patch não alterou o arquivo", path=str(p))
    return _gravar_com_validacao(p, novo_txt, exige_shebang=exige_shebang)


def _escrever_trecho_legado(
    p: Path, trecho: dict[str, Any], *, exige_shebang: bool
) -> dict[str, Any]:
    if not p.is_file():
        return envelope_erro(1, f"arquivo não existe para troca de trecho: {p}", path=str(p))
    antes = str(trecho.get("antes") or "")
    depois = str(trecho.get("depois") or "")
    todos = bool(trecho.get("todos", False))
    if not antes:
        return envelope_erro(2, "trecho.antes obrigatório", path=str(p))
    atual = p.read_text(encoding="utf-8")
    ocorrencias = atual.count(antes)
    if ocorrencias == 0:
        return envelope_erro(1, "trecho.antes não encontrado no arquivo", path=str(p))
    if ocorrencias > 1 and not todos:
        return envelope_erro(
            2,
            f"trecho.antes aparece {ocorrencias} vezes; amplie o contexto ou passe todos=true",
            path=str(p),
        )
    novo_txt = atual.replace(antes, depois) if todos else atual.replace(antes, depois, 1)
    return _gravar_com_validacao(
        p,
        novo_txt,
        exige_shebang=exige_shebang,
        extras={"substituiu": True, "ocorrencias": ocorrencias if todos else 1},
    )


def escrever(path: str | Path, **opcoes: Any) -> dict[str, Any]:
    """Caminho legado de `write_file`, preservado durante a janela de convivência."""
    p_alvo, err_morada, exige_shebang = resolver_escrita(
        str(path),
        instancia=opcoes.get("instancia"),
        bancada_dir=opcoes.get("bancada"),
        release_dir=opcoes.get("release"),
        pdp=opcoes.get("pdp"),
        cadeira=str(opcoes.get("cadeira") or ""),
        ordem_id=str(opcoes.get("ordem_id") or ""),
    )
    if err_morada or p_alvo is None:
        motivo = err_morada or "fora de morada"
        return envelope_erro(4, motivo, recusado=True, path=str(path), motivo=motivo)
    patch = str(opcoes.get("patch") or "")
    if patch:
        return _escrever_patch_legado(p_alvo, patch, exige_shebang=exige_shebang)
    trecho = opcoes.get("trecho")
    if trecho is not None:
        return _escrever_trecho_legado(p_alvo, trecho, exige_shebang=exige_shebang)
    return _gravar_com_validacao(
        p_alvo, str(opcoes.get("content") or ""), exige_shebang=exige_shebang
    )


__all__ = [
    "OpcoesExecucao",
    "aplicar_hunks",
    "escrever",
    "executar_ato_escrever",
    "parse_patch",
    "verbo_esta_ligado",
]
