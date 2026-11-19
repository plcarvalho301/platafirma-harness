"""Escrita atômica de arquivos, substituição por trecho e aplicação de patch (story #4342)."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from leitura.leitura import envelope_erro
from leitura.morada import ESCRITA_TETO, resolver_escrita

_RE_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _gravar_atomico(
    caminho: Path,
    conteudo: str,
    *,
    executavel: bool = False,
) -> tuple[int, str]:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = conteudo.encode("utf-8")
    fd, tmp_nome = tempfile.mkstemp(
        prefix=".wf-", suffix=".tmp", dir=str(caminho.parent)
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dados)
        if executavel:
            os.chmod(tmp_nome, 0o755)
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


def parse_patch(patch_texto: str) -> list[dict[str, Any]]:
    linhas = patch_texto.splitlines(keepends=True)
    arquivos: list[dict[str, Any]] = []
    i = 0
    while i < len(linhas):
        ln = linhas[i]
        if ln.startswith("--- ") and i + 1 < len(linhas) and linhas[i + 1].startswith("+++ "):
            old_p = ln[4:].strip().split("\t")[0].removeprefix("a/")
            new_p = linhas[i + 1][4:].strip().split("\t")[0].removeprefix("b/")
            i += 2
            hunks: list[dict[str, Any]] = []
            while i < len(linhas) and not linhas[i].startswith("--- "):
                m = _RE_HUNK.match(linhas[i])
                if not m:
                    i += 1
                    continue
                old_start = int(m.group(1))
                old_count = int(m.group(2)) if m.group(2) is not None else 1
                new_start = int(m.group(3))
                new_count = int(m.group(4)) if m.group(4) is not None else 1
                i += 1
                rem_old, rem_new = old_count, new_count
                hunk_lines: list[str] = []
                while i < len(linhas) and (rem_old > 0 or rem_new > 0):
                    hl = linhas[i]
                    if hl.startswith("\\"):
                        hunk_lines.append(hl)
                        i += 1
                    elif hl.startswith(" ") and rem_old > 0 and rem_new > 0:
                        hunk_lines.append(hl)
                        rem_old -= 1
                        rem_new -= 1
                        i += 1
                    elif hl.startswith("-") and rem_old > 0:
                        hunk_lines.append(hl)
                        rem_old -= 1
                        i += 1
                    elif hl.startswith("+") and rem_new > 0:
                        hunk_lines.append(hl)
                        rem_new -= 1
                        i += 1
                    else:
                        break
                hunks.append(
                    {
                        "old_start": old_start,
                        "old_count": old_count,
                        "new_start": new_start,
                        "new_count": new_count,
                        "lines": hunk_lines,
                    }
                )
            arquivos.append({"old_path": old_p, "new_path": new_p, "hunks": hunks})
        else:
            i += 1
    return arquivos


def aplicar_hunks(
    atual: str, hunks: list[dict[str, Any]], novo_arquivo: bool
) -> tuple[str | None, str | None]:
    linhas = [] if (novo_arquivo and atual == "") else atual.splitlines(keepends=True)
    offset = 0
    for h in hunks:
        esperadas: list[str] = []
        novas: list[str] = []
        ultimo_tipo = ""
        for hl in h["lines"]:
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
        if not esperadas:
            idx = 0 if novo_arquivo else max(0, min(len(linhas), h["old_start"] - 1 + offset))
        else:
            alvo_idx = max(0, h["old_start"] - 1 + offset)
            idx = None
            max_idx = len(linhas) - len(esperadas)
            for delta in range(0, 51):
                cands = (alvo_idx,) if delta == 0 else (alvo_idx + delta, alvo_idx - delta)
                for cand in cands:
                    if 0 <= cand <= max_idx and linhas[cand : cand + len(esperadas)] == esperadas:
                        idx = cand
                        break
                if idx is not None:
                    break
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


def escrever(
    path: str | Path,
    *,
    content: str = "",
    trecho: dict[str, Any] | None = None,
    patch: str = "",
    instancia: Path | None = None,
    bancada: Path | None = None,
    release: Path | None = None,
    pdp: Path | None = None,
    cadeira: str = "",
    ordem_id: str = "",
) -> dict[str, Any]:
    p_alvo, err_morada, exige_shebang = resolver_escrita(
        str(path),
        instancia=instancia,
        bancada_dir=bancada,
        release_dir=release,
        pdp=pdp,
        cadeira=cadeira,
        ordem_id=ordem_id,
    )
    if err_morada or p_alvo is None:
        motivo = err_morada or "fora de morada"
        return envelope_erro(4, motivo, recusado=True, path=str(path), motivo=motivo)
    p = p_alvo

    if patch:
        arquivos = parse_patch(patch)
        if not arquivos:
            return envelope_erro(2, "patch sem hunks válidos", path=str(p))
        entry = arquivos[0]
        novo_arq = entry["old_path"] == "/dev/null"
        atual = "" if novo_arq or not p.exists() else p.read_text(encoding="utf-8")
        novo_txt, err = aplicar_hunks(atual, entry["hunks"], novo_arq)
        if err or novo_txt is None:
            return envelope_erro(1, err or "falha ao aplicar patch", path=str(p))
        err_fin = _validar_final(novo_txt, path_str=str(p), exige_shebang=exige_shebang)
        if err_fin:
            return err_fin
        substituiu = p.exists()
        try:
            nbytes, sha = _gravar_atomico(p, novo_txt, executavel=exige_shebang)
        except PermissionError as exc:
            return envelope_erro(4, str(exc), recusado=True, path=str(p), motivo=str(exc))
        return {"ok": True, "path": str(p), "bytes": nbytes, "substituiu": substituiu, "sha256": sha}

    if trecho is not None:
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
        err_fin = _validar_final(novo_txt, path_str=str(p), exige_shebang=exige_shebang)
        if err_fin:
            return err_fin
        try:
            nbytes, sha = _gravar_atomico(p, novo_txt, executavel=exige_shebang)
        except PermissionError as exc:
            return envelope_erro(4, str(exc), recusado=True, path=str(p), motivo=str(exc))
        return {
            "ok": True,
            "path": str(p),
            "bytes": nbytes,
            "substituiu": True,
            "ocorrencias": ocorrencias if todos else 1,
            "sha256": sha,
        }

    err_fin = _validar_final(content, path_str=str(p), exige_shebang=exige_shebang)
    if err_fin:
        return err_fin
    substituiu = p.exists()
    try:
        nbytes, sha = _gravar_atomico(p, content, executavel=exige_shebang)
    except PermissionError as exc:
        return envelope_erro(4, str(exc), recusado=True, path=str(p), motivo=str(exc))
    return {
        "ok": True,
        "path": str(p),
        "bytes": nbytes,
        "substituiu": substituiu,
        "sha256": sha,
    }
