#!/usr/bin/env python3
"""Lê arquivos de terceiro declarados nas fichas da Olaria (card #4417).

Consulta `POST <OLARIA_URL>/ler` para a classe `stack` (e opcionalmente outras
classes consumidoras) e extrai cada ligação `depende-de` que carrega `destino` e
`pino`, devolvendo nome, família, destino, sha256 e url.

Sem a Olaria acessível ou sem credencial, escreve o motivo no stderr e sai 3.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - fallback sem PyYAML no python do sistema
    _yaml = None

_SHA256_RE = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")
_SEGREDO_PADRAO = Path("/srv/platafirma/casa/segredos/olaria")
OLARIA_URL_PADRAO = "http://127.0.0.1:8103"


class OlariaIndisponivel(RuntimeError):
    """Falha ao ler as fichas de dependência externa na Olaria."""


def _ler_segredo(nome: str, env: dict[str, str]) -> str:
    val = env.get(nome, "").strip()
    if val:
        return val
    inst = Path(env.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    arq = inst / "segredos" / "olaria" / nome
    try:
        if arq.is_file():
            texto = arq.read_text(encoding="utf-8").strip()
            if texto:
                return texto
    except OSError:
        pass
    return ""


def _parse_yaml_minimo(texto: str) -> dict:
    """Parser mínimo para o YAML emitido pela Olaria quando PyYAML não está no python."""
    if _yaml is not None:
        dado = _yaml.safe_load(texto)
        return dado if isinstance(dado, dict) else {}
    fichas: list[dict] = []
    ficha_atual: dict | None = None
    em_ligacoes = False
    em_depende = False
    item_atual: dict | None = None
    for linha_bruta in texto.splitlines():
        if not linha_bruta.strip() or linha_bruta.lstrip().startswith("#"):
            continue
        indent = len(linha_bruta) - len(linha_bruta.lstrip(" "))
        s = linha_bruta.strip()
        if indent == 0 and s.startswith("- "):
            ficha_atual = {"ligacoes": {}}
            fichas.append(ficha_atual)
            em_ligacoes = False
            em_depende = False
            item_atual = None
            resto = s[2:].strip()
            if ":" in resto:
                k, v = resto.split(":", 1)
                ficha_atual[k.strip()] = v.strip().strip("'\"")
            continue
        if ficha_atual is None:
            continue
        if indent == 2:
            em_depende = False
            item_atual = None
            if s == "ligacoes:":
                em_ligacoes = True
            else:
                em_ligacoes = False
                if ":" in s:
                    k, v = s.split(":", 1)
                    ficha_atual[k.strip()] = v.strip().strip("'\"")
        elif indent == 4 and em_ligacoes:
            item_atual = None
            if s.startswith("depende-de:"):
                em_depende = True
                ficha_atual["ligacoes"]["depende-de"] = []
                val = s.split(":", 1)[1].strip().strip("'\"")
                if val:
                    ficha_atual["ligacoes"]["depende-de"].append(val)
            else:
                em_depende = False
        elif em_depende and indent == 4 and s.startswith("- "):
            resto = s[2:].strip()
            if ":" in resto and not resto.startswith("dependencia-externa:"):
                k, v = resto.split(":", 1)
                item_atual = {k.strip(): v.strip().strip("'\"")}
                ficha_atual["ligacoes"]["depende-de"].append(item_atual)
            else:
                item_atual = None
                ficha_atual["ligacoes"]["depende-de"].append(resto.strip("'\""))
        elif em_depende and indent >= 6 and item_atual is not None and ":" in s:
            k, v = s.split(":", 1)
            item_atual[k.strip()] = v.strip().strip("'\"")
    return {"fichas": fichas}


def _consultar_classe(classe: str, url: str, chave: str, prazo_s: float = 15.0) -> dict:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/ler",
        data=json.dumps({"classe": classe, "chaves": [], "fichas": True}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Olaria-Chave": chave,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=prazo_s) as resp:
            status = getattr(resp, "status", 200)
            bruto = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        raise OlariaIndisponivel(f"Olaria inacessível em {url}: {erro}") from erro
    if status != 200:
        raise OlariaIndisponivel(f"Olaria respondeu HTTP {status} ao ler classe {classe}")
    try:
        corpo = json.loads(bruto.decode("utf-8"))
    except ValueError as erro:
        raise OlariaIndisponivel(f"Olaria devolveu resposta inválida: {erro}") from erro
    texto_yaml = corpo.get("yaml")
    if not isinstance(texto_yaml, str):
        raise OlariaIndisponivel("Olaria não devolveu campo yaml na leitura de fichas")
    return _parse_yaml_minimo(texto_yaml)


def extrair_terceiros(mudanca: dict) -> list[dict[str, str]]:
    itens: list[dict[str, str]] = []
    for ficha in mudanca.get("fichas") or []:
        if not isinstance(ficha, dict):
            continue
        ligs = ficha.get("ligacoes") or {}
        if not isinstance(ligs, dict):
            continue
        brutos = ligs.get("depende-de")
        if brutos is None:
            continue
        lista = brutos if isinstance(brutos, list) else [brutos]
        for dep in lista:
            if not isinstance(dep, dict):
                continue
            destino = str(dep.get("destino") or "").strip()
            pino = str(dep.get("pino") or "").strip()
            familia = str(dep.get("familia") or "").strip()
            if not destino or not pino or not familia:
                continue
            sha256 = pino.removeprefix("sha256:")
            alvo = str(dep.get("alvo") or "")
            nome = str(dep.get("nome") or (alvo.rsplit(":", 1)[-1] if alvo else "")).strip()
            url = str(dep.get("url") or "").strip()
            itens.append({
                "nome": nome,
                "familia": familia,
                "destino": destino,
                "sha256": sha256,
                "url": url,
            })
    return itens


def ler_terceiros_da_olaria(env: dict[str, str] | None = None, prazo_s: float = 15.0) -> list[dict[str, str]]:
    amb = os.environ if env is None else env
    chave = _ler_segredo("OLARIA_CHAVE", amb)
    url = _ler_segredo("OLARIA_URL", amb)
    if not url and chave and "OLARIA_URL" not in amb:
        url = OLARIA_URL_PADRAO
    if not url:
        raise OlariaIndisponivel("OLARIA_URL ausente")
    if not chave:
        raise OlariaIndisponivel("OLARIA_CHAVE ausente")
    mudanca = _consultar_classe("stack", url, chave, prazo_s=prazo_s)
    return extrair_terceiros(mudanca)


def shas_declarados(env: dict[str, str] | None = None) -> set[str]:
    return {
        item["sha256"]
        for item in ler_terceiros_da_olaria(env)
        if item["sha256"]
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="terceiros_olaria")
    parser.add_argument("--familia", default="")
    parser.add_argument("--shas", action="store_true")
    ns = parser.parse_args(argv)
    try:
        itens = ler_terceiros_da_olaria()
    except OlariaIndisponivel as erro:
        print(f"terceiros: não leu as fichas da Olaria ({erro})", file=sys.stderr)
        return 3
    if ns.shas:
        for sha in sorted({i["sha256"] for i in itens if _SHA256_RE.match(i["sha256"])}):
            print(sha)
        return 0
    for i in itens:
        if ns.familia and i["familia"] != ns.familia:
            continue
        print(f"{i['nome']}\t{i['destino']}\t{i['sha256']}\t{i['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
