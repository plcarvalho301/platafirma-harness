"""read_file_ref.py — a `read_file` de e9eaea5, congelada para o bench (#3263, spec ler-arquivo §16.1).

Cópia literal do comportamento que a `ler_arquivo` substitui. Origem, em platafirma-harness@e9eaea5:

  ops-server/server.py  blob 2e1b7746143e6138e41c291f4c942bcdd5d4c33d
    `_le_um_arquivo` + `read_file`, linhas 1392-1471, sha256 aa177ff5e341281eebe9b60879b0f3c86fd93947c7d3b6d11b3d3a3c06c0a97a
    `_serve`, linhas 328-373, sha256 197dbf15c319012b9c2a840d770521a69bcb2f19a58bef722a1457b142fdbf96
  ops-server/poda.py    blob aa2504641c883884e5269ea997689644e695c6c3
    `poda_texto`, linhas 576-631, sha256 9064e71497b30cfc1b46ec0e047bd967b7fec78440917572f3be2c7b8734a0b7

(sha256 de `git show e9eaea5:<arquivo> | sed -n <faixa>p`.)

Fica de fora, e é o único corte: autorização (PDP), resolução de caminho relativo, negativas de
fila e de segredo e auditoria. São da porta, iguais nas duas tools, e o bench lê só a árvore do
repositório, onde nada é negado. Duas trocas mecânicas, nenhuma de comportamento: `open` vira o
`abre` recebido, para o bench contar os bytes lidos; e `_serve`/`poda_texto` levam o caminho
`tool == "read_file"` já resolvido (cap efetivo = o próprio texto, então `corta` e o derrame por
teto nunca agem). O aviso de releitura é o de e9eaea5: `Ledger.olha` sem sufixo.

Não se edita. Sai junto com o apelido `read_file` (spec §12.3).
"""
from __future__ import annotations

import uuid
from pathlib import Path

import poda as _poda

CAP = 50_000   # server.py:116 em e9eaea5


def _poda_texto(texto: str, *, alca: str, sessao_id: str, giro: int,
                ledger: _poda.Ledger | None, nome_derrame: str) -> tuple[str, dict]:
    # poda.py:576-631, no ramo tool == "read_file", cosmetica=False, constitutiva=False.
    tool = "read_file"
    cap = max(CAP, len(texto.encode("utf-8", "replace")))          # server.py:354
    lavado, rel = _poda.lava(texto, cap, cosmetica=False, preserva_branco=True,
                             janela=False, curar=False)
    meta = {"ato": tool, "giro": giro, "sha": _poda.sha_servido(lavado),
            "lavado": rel["classes"], "bytes_produzidos": rel["bytes_antes"]}
    cru = _poda.derrama(sessao_id, nome_derrame, texto) if "blob" in rel["classes"] else None
    if cru:
        meta["cru"] = cru
    servir = lavado
    if ledger is not None:
        d = ledger.olha(alca, lavado, giro, tool)
        servir = d["texto"]
        meta["ledger"] = d.get("ledger")
        if d.get("distancia") is not None:
            meta["distancia"] = d["distancia"]
        if d["modo"] != "inteiro":
            meta.update(giro_ref=d.get("giro_ref"), bytes_omitidos=d.get("bytes_omitidos"),
                        modo=d["modo"])
            meta["bytes_servidos"] = len(servir.encode("utf-8", "replace"))
            return servir, meta
    meta["bytes_servidos"] = len(servir.encode("utf-8", "replace"))
    return servir, meta


def _serve(r: dict, *, alca: str, ledger: _poda.Ledger | None, sessao_id: str) -> dict:
    # server.py:328-373, só o campo `content` (o único que a read_file devolve).
    if not isinstance(r, dict) or _poda.intocavel(r):
        return r
    giro = ledger.giro() if ledger is not None else 0
    texto = r.get("content")
    if not isinstance(texto, str) or not texto:
        return r
    servido, meta = _poda_texto(texto, alca=f"read_file:{alca}", sessao_id=sessao_id,
                                giro=giro, ledger=ledger, nome_derrame=f"g{giro:05d}-content.txt")
    r["content"] = servido
    r = _poda.enxuga_envelope(r)
    r["poda"] = meta
    humana = _poda.linha_humana(meta)
    if humana:
        r["poda_aviso"] = humana
    return r


def le_um_arquivo(p: Path, offset: int = 0, max_bytes: int = 40000, *,
                  ledger: _poda.Ledger | None = None, sessao_id: str = "-", abre=open) -> dict:
    # server.py:1392-1441, depois das negativas.
    p = Path(p)
    if not p.is_file():
        if p.is_dir():
            erro = "é um diretório, não um arquivo — read_file só lê arquivo"
        elif p.exists():
            erro = "existe mas não é arquivo comum (socket, fifo ou dispositivo)"
        else:
            erro = "não existe"
        return {"erro": erro, "path": str(p)}
    tamanho_total = p.stat().st_size
    offset = max(0, offset)
    max_bytes = max(1, min(max_bytes, 200000))
    with abre(p, "rb") as fh:
        if offset > 0:
            fh.seek(offset)
        chunk = fh.read(max_bytes)
    fim = offset + len(chunk)
    truncated = fim < tamanho_total
    next_offset = fim if truncated else None
    r = {"content": chunk.decode("utf-8", "replace"), "bytes_total": tamanho_total,
         "offset": offset, "bytes_lidos": len(chunk),
         "truncated": truncated, "next_offset": next_offset,
         "path": str(p)}
    return _serve(r, alca=f"{p}|{offset}", ledger=ledger, sessao_id=sessao_id)


def read_file(path: str = "", offset: int = 0, max_bytes: int = 40000, *,
              paths: list[str] | None = None, ledger: _poda.Ledger | None = None,
              sessao_id: str = "-", abre=open) -> dict:
    # server.py:1444-1471, com PF_TOOLS_LOTE=1 (o que está no ar).
    if paths:
        resultados = []
        acumulado = 0
        lote_next = None
        _ = uuid.uuid4().hex[:8]                                    # lote_id: só auditoria
        for _i, pth in enumerate(paths):
            if acumulado >= CAP:
                lote_next = _i
                break
            r = le_um_arquivo(Path(pth), offset, max_bytes, ledger=ledger,
                              sessao_id=sessao_id, abre=abre)
            acumulado += r.get("bytes_total", 0)
            resultados.append(r)
        for _i in range(len(resultados), len(paths)):
            resultados.append({"omitido_por_teto": True})
        return {"lote": resultados, "lote_n": len(paths), "lote_next": lote_next}
    return le_um_arquivo(Path(path), offset, max_bytes, ledger=ledger,
                         sessao_id=sessao_id, abre=abre)
