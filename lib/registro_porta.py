"""O leitor único do registro da porta (registro/porta.yaml, card #4117).

O registro diz quais verbos a porta executa e quais o modelo vê na lista de tools. Quem precisa dele importa
este módulo: a porta (ops-server/server.py), `acervo listar casa ferramental` e `acervo registrar --todos`.
A borda das telas lê só as faces, em borda/borda.py, porque a imagem dela leva só a biblioteca padrão e o
pyyaml. O bloco cercado de abertura/oficio-ferramental.md, que tinha três leitores à mão, saiu.

Forma: duas chaves, `verbos` (slug -> atributos) e `transporte` (nome da tool -> mapa vazio). Atributos de
verbo, todos opcionais: `nome` (slug opcional: nome exibido na lista de tools), `modelo` (booleano, padrão true),
`retido` (booleano, padrão false: só serve com PF_TOOLS_LEVA2=1) e `faces` (face -> {instancia, sem_instancia}).
Chave fora desta lista é erro, e o registro inteiro passa a ilegível: a porta falha fechada, sobe só com as
tools de transporte e diz o motivo no journal.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

SLUG = re.compile(r"^[a-z][a-z0-9_-]*$")
ATRIBUTOS = frozenset({"modelo", "retido", "faces", "nome"})
ATRIBUTOS_DA_FACE = frozenset({"instancia", "sem_instancia"})

class RegistroIlegivel(Exception):
    """O arquivo não existe, não é YAML ou não tem a forma do registro."""

def caminho_do(harness: str | Path) -> Path:
    """O registro dentro de uma raiz de harness (a release no ar, ou a bancada)."""
    return Path(harness) / "registro" / "porta.yaml"

def carrega(arquivo: str | Path) -> dict:
    """`{"verbos": {slug: {"modelo": bool, "retido": bool, "faces": {face: {...}}}}, "transporte": [nome, ...]}`
    (e `nome` no dict do verbo só quando declarado), na ordem do arquivo, com os padrões preenchidos. Levanta
    `RegistroIlegivel` com o motivo."""
    arquivo = Path(arquivo)
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except OSError as e:
        raise RegistroIlegivel(f"{arquivo}: {e.strerror or type(e).__name__}") from e
    try:
        doc = yaml.safe_load(texto)
    except yaml.YAMLError as e:
        raise RegistroIlegivel(f"{arquivo}: não é YAML ({type(e).__name__})") from e
    if not isinstance(doc, dict) or set(doc) != {"verbos", "transporte"}:
        raise RegistroIlegivel(f"{arquivo}: esperadas as duas chaves `verbos` e `transporte`")
    verbos = {}
    for slug, atr in _mapa(doc["verbos"], arquivo, "verbos").items():
        verbos[_slug(slug, arquivo)] = _verbo(slug, atr, arquivo)
    transporte = []
    for nome, vazio in _mapa(doc["transporte"], arquivo, "transporte").items():
        if vazio not in (None, {}):
            raise RegistroIlegivel(f"{arquivo}: `transporte.{nome}` não tem atributo, só o nome")
        transporte.append(_slug(nome, arquivo))

    transporte_set = set(transporte)
    nomes_vistos = {}
    for slug, v in verbos.items():
        if "nome" in v:
            n = v["nome"]
            if n in transporte_set:
                raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.nome` ({n!r}) repete tool de transporte")
            if n in verbos and n != slug:
                raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.nome` ({n!r}) repete slug de outro verbo")
            if n in nomes_vistos:
                raise RegistroIlegivel(
                    f"{arquivo}: `verbos.{slug}.nome` ({n!r}) repete nome de outro verbo (`verbos.{nomes_vistos[n]}`)")
            nomes_vistos[n] = slug

    return {"verbos": verbos, "transporte": transporte}

def visiveis(registro: dict) -> list[str]:
    """Os verbos que o modelo vê na lista de tools: `modelo` verdadeiro (os retidos entram: quem os segura é a
    porta, por PF_TOOLS_LEVA2)."""
    return [slug for slug, v in registro["verbos"].items() if v["modelo"]]

def retidos(registro: dict) -> set[str]:
    return {slug for slug, v in registro["verbos"].items() if v["retido"]}

def exibido(registro: dict, slug: str) -> str:
    """O nome exibido da tool: o atributo `nome`, se declarado no verbo; senão, o próprio `slug`."""
    v = registro.get("verbos", {}).get(slug)
    if v and "nome" in v:
        return v["nome"]
    return slug

def _mapa(valor: object, arquivo: Path, onde: str) -> dict:
    if not isinstance(valor, dict) or not valor:
        raise RegistroIlegivel(f"{arquivo}: `{onde}` tem de ser um mapa com pelo menos um item")
    return valor

def _slug(slug: object, arquivo: Path) -> str:
    if not isinstance(slug, str) or not SLUG.match(slug):
        raise RegistroIlegivel(f"{arquivo}: nome fora da forma de slug: {slug!r}")
    return slug

def _verbo(slug: str, atr: object, arquivo: Path) -> dict:
    atr = {} if atr is None else atr
    if not isinstance(atr, dict) or set(atr) - ATRIBUTOS:
        raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}` com atributo fora de {sorted(ATRIBUTOS)}")
    for chave in ("modelo", "retido"):
        if chave in atr and not isinstance(atr[chave], bool):
            raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.{chave}` tem de ser booleano")
    faces = {}
    for face, cfg in (atr.get("faces") or {}).items():
        cfg = {} if cfg is None else cfg
        if not isinstance(cfg, dict) or set(cfg) - ATRIBUTOS_DA_FACE:
            raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.faces.{face}` com atributo fora de "
                                   f"{sorted(ATRIBUTOS_DA_FACE)}")
        sem = cfg.get("sem_instancia") or []
        if not isinstance(sem, list) or not all(isinstance(a, str) for a in sem):
            raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.faces.{face}.sem_instancia` tem de ser lista de atos")
        if "instancia" in cfg and not isinstance(cfg["instancia"], str):
            raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.faces.{face}.instancia` tem de ser texto")
        faces[_slug(face, arquivo)] = {k: cfg[k] for k in ("instancia", "sem_instancia") if k in cfg}
    res = {"modelo": atr.get("modelo", True), "retido": atr.get("retido", False), "faces": faces}
    if "nome" in atr:
        nome = atr["nome"]
        if not isinstance(nome, str) or not SLUG.match(nome):
            raise RegistroIlegivel(f"{arquivo}: `verbos.{slug}.nome` fora da forma de slug: {nome!r}")
        res["nome"] = nome
    return res
