"""Varredura do acervo (spec ler-arquivo §7.4, aceite): o objeto de toda obra viva lido pela
primeira página, sem recusa; 20 PDFs sorteados em `modo="pagina"` com imagem legível.

Lê estado do host (catálogo e balde), então fica FORA de `VERDES`, do portão e do padrão
`test_*` (o pytest não o coleta sozinho): roda à mão, pela porta, com o arquivo nomeado:

    sessao longjob run varredura teste rodar ops@<bancada> ops-server/bench/varredura_acervo.py

Sem a pasta da varredura, pula. É retomável: objeto já baixado não baixa de novo. O relatório
sai em `relatorio.json` e `relatorio.md` dentro da pasta, e vai ao card/fila de quem pediu.
Os subprocessos (`acervo psql`, `acervo ler biblioteca objeto`) recebem o ambiente real da
conta, não o isolado da suíte (lib/teste_isolado.py), porque a varredura É sobre o real.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import pytest
except ImportError:                       # como script, fora do pytest (venv ops sem pytest)
    class pytest:                         # noqa: N801 — só o decorador que o módulo usa
        class mark:
            @staticmethod
            def skipif(_cond, reason=""):
                return lambda f: f

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import leitura as L                                            # noqa: E402

PASTA = Path("/home/claudinho/AI/varredura-ler-formatos")
ACERVO = Path("/opt/platafirma/current/harness/bin/acervo")
SQL = ("select id||E'\\t'||coalesce(arquivo,'')||E'\\t'||objeto from acervo.obra "
       "where expurgada_em is null and objeto is not null order by id")
# a saída alinhada do psql expande o tab em espaços: o objeto (`<balde>/<sha256>`) fecha a linha
_UUID = re.compile(r"^\s*([0-9a-f-]{36})\s+(.*?)\s+(\S+/[0-9a-f]{64})\s*$")
AMOSTRA_PDF = 20
ENV = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
       "HOME": "/home/claudinho", "USER": "claudinho", "LOGNAME": "claudinho",
       "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
       "PLATAFIRMA_INSTANCIA": "/srv/platafirma/casa", "PF_RELEASE_RAIZ": "/opt/platafirma",
       "PLATAFIRMA_RELEASE": "/opt/platafirma/current", "PLATAFIRMA_BANCADA": "/home/claudinho/AI"}


def _obras() -> list[dict]:
    cache = PASTA / "obras.tsv"
    if cache.exists():
        texto = cache.read_text(encoding="utf-8")
    else:
        r = subprocess.run([str(ACERVO), "psql", "--banco", "rag"], input=SQL, text=True,
                           capture_output=True, env=ENV, timeout=300)
        assert r.returncode == 0, r.stderr[-500:]
        texto = r.stdout
        cache.write_text(texto, encoding="utf-8")
    obras = []
    for linha in texto.splitlines():
        m = _UUID.match(linha)
        if m:
            obras.append({"id": m.group(1), "arquivo": m.group(2), "objeto": m.group(3)})
    return obras


def _baixa(obra: dict) -> tuple[Path | None, str | None]:
    pasta = PASTA / "objetos" / obra["id"]
    if pasta.is_dir():
        arquivos = [p for p in pasta.iterdir() if p.is_file() and not p.name.endswith(".parte")]
        if arquivos:
            return arquivos[0], None
    erro = ""
    for argv in ([obra["id"], "--destino", str(pasta)], [obra["id"], str(pasta)]):
        try:
            r = subprocess.run([str(ACERVO), "ler", "biblioteca", "objeto", *argv], text=True,
                               capture_output=True, env=ENV, timeout=900)
        except subprocess.TimeoutExpired:
            return None, "download: prazo de 900 s"
        if r.returncode == 0 and pasta.is_dir():
            arquivos = [p for p in pasta.iterdir() if p.is_file() and not p.name.endswith(".parte")]
            if arquivos:
                return arquivos[0], None
        erro = (r.stderr or r.stdout).strip()[-300:]
        if r.returncode != 4:
            return None, f"download exit {r.returncode}: {erro}"
    return None, f"download exit 4: {erro}"


def _le(p: Path) -> dict:
    t0 = time.monotonic()
    try:
        r = L.le(p)
    except Exception as e:                                        # noqa: BLE001
        return {"resultado": "excecao", "detalhe": f"{type(e).__name__}: {str(e)[:200]}"}
    ms = round((time.monotonic() - t0) * 1000)
    if r.get("recusado"):
        return {"resultado": "recusa", "motivo": r.get("motivo"), "tipo": r.get("tipo"), "ms": ms}
    if r.get("erro"):
        return {"resultado": "erro", "detalhe": r["erro"][:200], "classe": r.get("classe_erro"),
                "tipo": r.get("tipo"), "ms": ms}
    return {"resultado": "ok", "tipo": r.get("tipo"), "unidade": r.get("unidade"),
            "paginas_total": r.get("paginas_total"), "cabecalho": r.get("cabecalho", "")[:200],
            "comeco": (r.get("conteudo") or "")[:160], "sem_texto": r.get("sem_texto"),
            "ms": ms}


def _imagem(p: Path) -> dict:
    t0 = time.monotonic()
    try:
        r = L.le(p, modo="pagina", paginas="1-1")
    except Exception as e:                                        # noqa: BLE001
        return {"resultado": "excecao", "detalhe": f"{type(e).__name__}: {str(e)[:200]}"}
    ms = round((time.monotonic() - t0) * 1000)
    img = (r.get("imagens") or [{}])[0]
    png = img.get("png") or b""
    ok = png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1_000 and (img.get("largura") or 0) > 300
    return {"resultado": "ok" if ok else "falha", "bytes": len(png), "largura": img.get("largura"),
            "altura": img.get("altura"), "ms": ms, "detalhe": None if ok else str(r)[:200]}


@pytest.mark.skipif(not PASTA.is_dir(), reason="sem pasta da varredura: roda à mão pela porta")
def test_varredura_toda_obra_viva_le_pela_primeira_pagina():
    obras = _obras()
    assert obras, "nenhuma obra viva com objeto"
    linhas, por_tipo = [], {}
    for obra in obras:
        p, erro = _baixa(obra)
        if p is None:
            item = {"id": obra["id"], "arquivo": obra["arquivo"], "resultado": "download", "detalhe": erro}
        else:
            L.esvazia_cache()
            item = {"id": obra["id"], "arquivo": obra["arquivo"], "caminho": str(p),
                    "bytes": p.stat().st_size, **_le(p)}
        linhas.append(item)
        chave = (item.get("tipo") or "?", item["resultado"])
        por_tipo[chave] = por_tipo.get(chave, 0) + 1
        (PASTA / "andamento.json").write_text(json.dumps(
            {"lidas": len(linhas), "total": len(obras), "por_tipo": {f"{t} · {r}": n for (t, r), n in por_tipo.items()}},
            ensure_ascii=False, indent=1), encoding="utf-8")
    pdfs = sorted((i for i in linhas if i.get("tipo") == "application/pdf" and i["resultado"] == "ok"),
                  key=lambda i: hashlib.sha256(i["id"].encode()).hexdigest())[:AMOSTRA_PDF]
    imagens = []
    for i in pdfs:
        imagens.append({"id": i["id"], "arquivo": i["arquivo"], **_imagem(Path(i["caminho"]))})
    recusas = [i for i in linhas if i["resultado"] in ("recusa", "erro", "excecao")]
    downloads = [i for i in linhas if i["resultado"] == "download"]
    imagens_ruins = [i for i in imagens if i["resultado"] != "ok"]
    relatorio = {"gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "obras": len(obras),
                 "por_tipo": {f"{t} · {r}": n for (t, r), n in sorted(por_tipo.items())},
                 "recusas": recusas, "downloads_falhos": downloads,
                 "pdf_modo_pagina": imagens, "linhas": linhas}
    (PASTA / "relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    md = ["# Varredura do acervo — ler_arquivo §7.4", "",
          f"Gerado em {relatorio['gerado_em']} · {len(obras)} obras vivas com objeto", "",
          "| tipo | resultado | obras |", "|---|---|---|"]
    md += [f"| {t} | {r} | {n} |" for (t, r), n in sorted(por_tipo.items())]
    md += ["", f"Recusas ou erros do leitor: {len(recusas)}"]
    md += [f"- {i['id']} {i['arquivo']}: {i.get('motivo') or i.get('detalhe')}" for i in recusas]
    md += ["", f"Downloads que falharam (não é o leitor): {len(downloads)}"]
    md += [f"- {i['id']} {i['arquivo']}: {i['detalhe']}" for i in downloads]
    md += ["", f"PDF em modo=\"pagina\" (p. 1 de {len(imagens)} obras sorteadas): "
               f"{len(imagens) - len(imagens_ruins)} legíveis"]
    md += [f"- {i['id']} {i['arquivo']}: {i['largura']}×{i['altura']} px, {i['bytes']} bytes, {i['ms']} ms"
           for i in imagens]
    (PASTA / "relatorio.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    assert not recusas, f"{len(recusas)} recusa(s) do leitor — ver relatorio.md"
    assert not imagens_ruins, f"{len(imagens_ruins)} PDF sem imagem legível — ver relatorio.md"


if __name__ == "__main__":
    # Como script, com o python do venv `ops` (o `teste rodar` tem prazo de 300 s e a varredura
    # inteira passa dele): `sessao longjob run varredura <venv>/bin/python <este arquivo>`.
    if not PASTA.is_dir():
        sys.exit("sem pasta da varredura: " + str(PASTA))
    try:
        test_varredura_toda_obra_viva_le_pela_primeira_pagina()
    except AssertionError as e:
        print(f"VARREDURA REPROVADA: {e}")
        sys.exit(1)
    print("VARREDURA PASSOU: zero recusa; relatório em", PASTA / "relatorio.md")
