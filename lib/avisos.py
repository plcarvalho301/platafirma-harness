#!/usr/bin/env python3
"""Rodada de avisos de vulnerabilidade sobre dependências externas (card #4417).

Cruza o pino de cada dependência externa (PyPI e npm) nas ligações `depende-de`
lidas da Olaria com a base OSV (`POST /v1/querybatch` + hidratação dos IDs
atingidos em `GET /v1/vulns/<id>`), sob prazo monotônico global e teto de bytes.

Grava início, alertas novos (com `sobre`, `dono`, `prazo` e deduplicação por
`(aviso, dependente)`) e desfecho em `$SEG_LOG_DIR/avisos.jsonl`.
Se a base OSV ou a Olaria falhar, sai 5, registra o evento de falha na trilha e
não grava alerta parcial ou falso.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    _yaml = None

PRAZO_GLOBAL_PADRAO_S = 30.0
TETO_BYTES_PADRAO = 2 * 1024 * 1024
PRAZO_ALERTA_DIAS = 30
OSV_API_PADRAO = "https://api.osv.dev"
_SEGREDO_OLARIA = Path("/srv/platafirma/casa/segredos/olaria")

_ECOSSISTEMA_POR_ORIGEM = {
    "pypi.org": "PyPI",
    "pypi": "PyPI",
    "registry.npmjs.org": "npm",
    "npmjs.org": "npm",
    "npm": "npm",
}

_DONO_POR_PREFIXO = {
    "receita:": "ti",
    "stack:harness": "ti",
    "stack:porta": "ti",
    "stack:rag": "conhecimento",
    "stack:busca": "ia",
    "stack:motor": "ia",
    "stack:ui": "engenharia",
    "stack:rastreador": "engenharia",
    "host:": "ti",
}


class ErroBaseAvisos(RuntimeError):
    """Falha ao consultar a base de avisos OSV ou a Olaria."""


@dataclass(frozen=True)
class DependenciaPinada:
    dependente: str
    dono: str
    dependencia: str
    ecossistema: str
    pacote: str
    versao: str
    pino: str


def _uuid7(agora: datetime) -> str:
    ms = int(agora.timestamp() * 1000)
    rand = int.from_bytes(secrets.token_bytes(10), "big")
    val = ((ms & ((1 << 48) - 1)) << 80) | (0x7 << 76) | (((rand >> 68) & 0xFFF) << 64) | (0b10 << 62) | (rand & ((1 << 62) - 1))
    h = f"{val:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _versao_do_pino(pino: str) -> str:
    bruto = (pino or "").strip()
    if not bruto or bruto.startswith("sha256:"):
        return ""
    if "+sha256:" in bruto:
        bruto = bruto.split("+sha256:", 1)[0]
    return bruto.strip()


def _dono_do_dependente(chave: str, ficha: dict) -> str:
    dados = ficha.get("dados") or {}
    if isinstance(dados, dict) and isinstance(dados.get("dono"), str) and dados["dono"].strip():
        return dados["dono"].strip()
    for prefixo, dono in _DONO_POR_PREFIXO.items():
        if chave.startswith(prefixo):
            return dono
    return "seguranca"


def _ler_http_com_teto(
    req: urllib.request.Request,
    *,
    fim: float,
    teto_bytes: int,
    relogio: Callable[[], float] = time.monotonic,
) -> dict:
    resta = fim - relogio()
    if resta <= 0:
        raise ErroBaseAvisos("prazo global esgotado antes da chamada HTTP")
    try:
        with urllib.request.urlopen(req, timeout=resta) as resp:
            status = getattr(resp, "status", 200)
            if status != 200:
                raise ErroBaseAvisos(f"HTTP {status} em {req.full_url}")
            pedacos: list[bytes] = []
            lidos = 0
            while True:
                if relogio() >= fim:
                    raise ErroBaseAvisos("prazo global esgotado durante leitura HTTP")
                bloco = resp.read(65536)
                if not bloco:
                    break
                lidos += len(bloco)
                if lidos > teto_bytes:
                    raise ErroBaseAvisos(f"resposta acima do teto de {teto_bytes} bytes")
                pedacos.append(bloco)
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        raise ErroBaseAvisos(f"falha HTTP em {req.full_url}: {erro}") from erro
    try:
        dado = json.loads(b"".join(pedacos).decode("utf-8"))
    except ValueError as erro:
        raise ErroBaseAvisos(f"JSON inválido de {req.full_url}: {erro}") from erro
    if not isinstance(dado, dict):
        raise ErroBaseAvisos(f"resposta inesperada de {req.full_url}")
    return dado


def _ler_segredo_olaria(nome: str, env: dict[str, str]) -> str:
    val = env.get(nome, "").strip()
    if val:
        return val
    inst = Path(env.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    for base in (inst / "segredos" / "olaria", _SEGREDO_OLARIA):
        arq = base / nome
        try:
            if arq.is_file():
                texto = arq.read_text(encoding="utf-8").strip()
                if texto:
                    return texto
        except OSError:
            continue
    return ""


def _carregar_yaml(texto: str) -> dict:
    if _yaml is not None:
        dado = _yaml.safe_load(texto)
        return dado if isinstance(dado, dict) else {}
    raise ErroBaseAvisos("PyYAML ausente no interpretador")


def coletar_dependencias_da_olaria(
    url: str,
    chave: str,
    *,
    fim: float,
    teto_bytes: int,
    relogio: Callable[[], float] = time.monotonic,
) -> list[DependenciaPinada]:
    def ler_classe(classe: str) -> list[dict]:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/ler",
            data=json.dumps({"classe": classe, "chaves": [], "fichas": True}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json", "X-Olaria-Chave": chave},
            method="POST",
        )
        corpo = _ler_http_com_teto(req, fim=fim, teto_bytes=teto_bytes, relogio=relogio)
        mudanca = _carregar_yaml(str(corpo.get("yaml") or ""))
        return [f for f in (mudanca.get("fichas") or []) if isinstance(f, dict)]

    deps_por_chave: dict[str, tuple[str, str]] = {}
    for f in ler_classe("dependencia-externa"):
        chave_dep = str(f.get("chave") or "")
        dados = f.get("dados") or {}
        if not chave_dep or not isinstance(dados, dict):
            continue
        origem = str(dados.get("origem") or "").strip().lower()
        nome = str(dados.get("nome") or "").strip()
        eco = _ECOSSISTEMA_POR_ORIGEM.get(origem)
        if eco and nome:
            deps_por_chave[chave_dep] = (eco, nome)

    resultado: list[DependenciaPinada] = []
    for classe in ("receita", "stack", "host"):
        for f in ler_classe(classe):
            dep_chave = str(f.get("chave") or "")
            ligs = f.get("ligacoes") or {}
            if not dep_chave or not isinstance(ligs, dict):
                continue
            brutos = ligs.get("depende-de")
            if brutos is None:
                continue
            lista = brutos if isinstance(brutos, list) else [brutos]
            dono = _dono_do_dependente(dep_chave, f)
            for item in lista:
                if not isinstance(item, dict):
                    continue
                alvo = str(item.get("alvo") or "")
                pino = str(item.get("pino") or "").strip()
                if alvo not in deps_por_chave or not pino:
                    continue
                versao = _versao_do_pino(pino)
                if not versao:
                    continue
                eco, nome = deps_por_chave[alvo]
                resultado.append(DependenciaPinada(
                    dependente=dep_chave,
                    dono=dono,
                    dependencia=alvo,
                    ecossistema=eco,
                    pacote=nome,
                    versao=versao,
                    pino=pino,
                ))
    return resultado


def _alertas_abertos(trilha: Path) -> set[tuple[str, str]]:
    abertos: set[tuple[str, str]] = set()
    if not trilha.is_file():
        return abertos
    try:
        for linha in trilha.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            ev = json.loads(linha)
            if ev.get("tipo-de-evento") != "seg.aviso.vulnerabilidade":
                continue
            sobre = ev.get("sobre")
            payload = ev.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except ValueError:
                    payload = {}
            aviso_id = payload.get("aviso") if isinstance(payload, dict) else None
            if isinstance(sobre, str) and isinstance(aviso_id, str):
                abertos.add((aviso_id, sobre))
    except (OSError, ValueError):
        return abertos
    return abertos


def _gravar_eventos(trilha: Path, eventos: list[dict]) -> None:
    trilha.parent.mkdir(parents=True, exist_ok=True)
    with trilha.open("a", encoding="utf-8") as fh:
        for ev in eventos:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def avaliar_avisos(
    dependencias: list[DependenciaPinada],
    *,
    consultar_lote: Callable[[list[dict]], list[dict]],
    consultar_aviso: Callable[[str], dict],
    trilha: Path,
    agora_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    prazo_dias: int = PRAZO_ALERTA_DIAS,
) -> tuple[int, list[dict]]:
    agora = agora_fn().astimezone(timezone.utc)
    correlacao = _uuid7(agora)
    iso_agora = agora.isoformat().replace("+00:00", "Z")
    iso_prazo = (agora + timedelta(days=prazo_dias)).isoformat().replace("+00:00", "Z")

    ev_inicio = {
        "evento-id": _uuid7(agora),
        "tipo-de-evento": "seg.avisos.rodada-iniciada",
        "correlacao": correlacao,
        "esfera": "operacao",
        "sobre": "componente:verbo-seg",
        "ocorrido-em": iso_agora,
        "registrado-em": iso_agora,
        "payload": json.dumps({"dependencias_consultadas": len(dependencias)}, ensure_ascii=False),
    }

    if not dependencias:
        ev_fim = {
            "evento-id": _uuid7(agora),
            "tipo-de-evento": "seg.avisos.rodada-concluida",
            "correlacao": correlacao,
            "esfera": "operacao",
            "sobre": "componente:verbo-seg",
            "ocorrido-em": iso_agora,
            "registrado-em": iso_agora,
            "payload": json.dumps({"alertas_novos": 0, "dependencias": 0}, ensure_ascii=False),
        }
        _gravar_eventos(trilha, [ev_inicio, ev_fim])
        return 0, []

    consultas = [
        {"package": {"ecosystem": d.ecossistema, "name": d.pacote}, "version": d.versao}
        for d in dependencias
    ]
    try:
        resultados = consultar_lote(consultas)
        if not isinstance(resultados, list) or len(resultados) != len(dependencias):
            raise ErroBaseAvisos("resposta de querybatch com tamanho incompatível")
        ids_unicos: list[str] = []
        vistos: set[str] = set()
        for res in resultados:
            for vuln in (res.get("vulns") or []) if isinstance(res, dict) else []:
                vid = vuln.get("id") if isinstance(vuln, dict) else None
                if isinstance(vid, str) and vid and vid not in vistos:
                    vistos.add(vid)
                    ids_unicos.append(vid)
        detalhes: dict[str, dict] = {}
        for vid in ids_unicos:
            detalhes[vid] = consultar_aviso(vid)
    except Exception as erro:
        ev_falha = {
            "evento-id": _uuid7(agora),
            "tipo-de-evento": "seg.avisos.rodada-falhou",
            "correlacao": correlacao,
            "esfera": "operacao",
            "sobre": "componente:verbo-seg",
            "ocorrido-em": iso_agora,
            "registrado-em": iso_agora,
            "payload": json.dumps({"erro": str(erro)}, ensure_ascii=False),
        }
        _gravar_eventos(trilha, [ev_inicio, ev_falha])
        return 5, []

    ja_abertos = _alertas_abertos(trilha)
    alertas_novos: list[dict] = []
    for dep, res in zip(dependencias, resultados):
        vulns = (res.get("vulns") or []) if isinstance(res, dict) else []
        for v in vulns:
            vid = v.get("id") if isinstance(v, dict) else None
            if not isinstance(vid, str) or not vid:
                continue
            chave_dedup = (vid, dep.dependente)
            if chave_dedup in ja_abertos:
                continue
            ja_abertos.add(chave_dedup)
            det = detalhes.get(vid) or {}
            resumo = str(det.get("summary") or det.get("details") or "")[:240]
            alerta = {
                "evento-id": _uuid7(agora),
                "tipo-de-evento": "seg.aviso.vulnerabilidade",
                "correlacao": correlacao,
                "esfera": "operacao",
                "sobre": dep.dependente,
                "dono": dep.dono,
                "prazo": iso_prazo,
                "ocorrido-em": iso_agora,
                "registrado-em": iso_agora,
                "payload": json.dumps({
                    "aviso": vid,
                    "dependencia": dep.dependencia,
                    "pacote": dep.pacote,
                    "ecossistema": dep.ecossistema,
                    "pino": dep.pino,
                    "resumo": resumo,
                }, ensure_ascii=False),
            }
            alertas_novos.append(alerta)

    ev_fim = {
        "evento-id": _uuid7(agora),
        "tipo-de-evento": "seg.avisos.rodada-concluida",
        "correlacao": correlacao,
        "esfera": "operacao",
        "sobre": "componente:verbo-seg",
        "ocorrido-em": iso_agora,
        "registrado-em": iso_agora,
        "payload": json.dumps({
            "alertas_novos": len(alertas_novos),
            "dependencias": len(dependencias),
        }, ensure_ascii=False),
    }
    _gravar_eventos(trilha, [ev_inicio, *alertas_novos, ev_fim])
    return 0, alertas_novos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seg avisos")
    parser.add_argument("--json", action="store_true", dest="como_json")
    ns = parser.parse_args(argv)

    env = dict(os.environ)
    inst = Path(env.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    log_dir = Path(env.get("SEG_LOG_DIR", str(inst / "var" / "log" / "seg")))
    trilha = log_dir / "avisos.jsonl"
    osv_url = env.get("OSV_API_URL", OSV_API_PADRAO).rstrip("/")
    prazo_s = float(env.get("SEG_AVISOS_PRAZO_S", PRAZO_GLOBAL_PADRAO_S))
    teto_bytes = int(env.get("SEG_AVISOS_MAX_BYTES", TETO_BYTES_PADRAO))
    fim = time.monotonic() + prazo_s

    olaria_url = _ler_segredo_olaria("OLARIA_URL", env)
    olaria_chave = _ler_segredo_olaria("OLARIA_CHAVE", env)
    if not olaria_url or not olaria_chave:
        print("seg avisos: OLARIA_URL ou OLARIA_CHAVE ausente", file=sys.stderr)
        return 5

    try:
        deps = coletar_dependencias_da_olaria(olaria_url, olaria_chave, fim=fim, teto_bytes=teto_bytes)
    except ErroBaseAvisos as erro:
        print(f"seg avisos: falha ao ler dependências da Olaria ({erro})", file=sys.stderr)
        return 5

    def consultar_lote(queries: list[dict]) -> list[dict]:
        req = urllib.request.Request(
            f"{osv_url}/v1/querybatch",
            data=json.dumps({"queries": queries}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        corpo = _ler_http_com_teto(req, fim=fim, teto_bytes=teto_bytes)
        res = corpo.get("results")
        if not isinstance(res, list):
            raise ErroBaseAvisos("OSV querybatch sem campo results")
        return res

    def consultar_aviso(vid: str) -> dict:
        req = urllib.request.Request(
            f"{osv_url}/v1/vulns/{urllib.parse.quote(vid, safe='')}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        return _ler_http_com_teto(req, fim=fim, teto_bytes=teto_bytes)

    rc, alertas = avaliar_avisos(deps, consultar_lote=consultar_lote, consultar_aviso=consultar_aviso, trilha=trilha)
    if rc != 0:
        print("seg avisos: base de avisos OSV indisponível — rodada encerrada sem alerta parcial", file=sys.stderr)
        return rc
    if ns.como_json:
        print(json.dumps({"alertas": alertas, "total": len(alertas), "dependencias": len(deps)}, ensure_ascii=False))
    else:
        print(f"seg avisos: {len(alertas)} alerta(s) novo(s) em {len(deps)} dependência(s) pinada(s)")
        for a in alertas:
            p = json.loads(a["payload"])
            print(f"  alerta: {p['aviso']} sobre {a['sobre']} (dono={a['dono']}, prazo={a['prazo']}, pino={p['pino']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
