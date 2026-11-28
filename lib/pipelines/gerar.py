"""gerar — compila `configuracao:<slug>` em `registro/pipelines/<slug>.yaml` na promoção (card #4472).

Lê as fichas `pipeline:<slug>` e `configuracao:<slug>` na Olaria (identidade, ligações e caminho do
arquivo `.yaml`), valida cada configuração em passada única contra:
1. o esquema literal `registro/esquemas/pipeline.schema.json` (versão 2);
2. o registro de verbos e atos (`registro/porta.yaml`);
3. a identidade da ficha `pipeline:<slug>` no fichário.

Quando tudo confere, grava o artefato canônico imutável em `registro/pipelines/<slug>.yaml` com
metadados de procedência (`ficha`, `configuracao`, `fornada`, `sha`, `compilado_em`, `digest`).
Em qualquer divergência, não grava nada, relata pipeline, instrução e regra, e sai `4`.
Quando a Olaria não responde, relata a indisponibilidade e sai `3`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from despacho.borda import _extrair_atos_descricao
from terceiros_olaria import (
    OLARIA_URL_PADRAO,
    OlariaIndisponivel,
    _consultar_classe,
    _ler_segredo,
)

SAIDA_OK = 0
SAIDA_DEPENDENCIA = 3
SAIDA_RECUSA = 4
VERSAO_ESQUEMA = 2
VERBOS_SUBSTRATO_EXTERNO = frozenset({"pesquisar"})
_RE_PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_-]+)\}")


@dataclass(frozen=True, slots=True)
class ErroCompilacaoItem:
    """Um desvio encontrado durante a validação de um pipeline."""

    pipeline: str
    onde: str
    regra: str
    detalhe: str

    def formatar(self) -> str:
        return f"pipeline:{self.pipeline} · {self.onde} · regra={self.regra} · {self.detalhe}"


class ErroCompilacaoPipeline(Exception):
    """Recusa de compilação (saída 4) com todos os desvios encontrados."""

    def __init__(self, erros: list[ErroCompilacaoItem]) -> None:
        self.erros = tuple(erros)
        super().__init__("; ".join(e.formatar() for e in self.erros))


@dataclass(frozen=True, slots=True)
class ArtefatoCompilado:
    """Resumo de um artefato compilado com procedência e digest."""

    slug: str
    caminho: Path
    digest: str
    fornada: str


def _resolver_ref(raiz: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    alvo: Any = raiz
    for parte in ref.removeprefix("#/").split("/"):
        alvo = alvo[parte]
    return alvo


def _onde_esquema(trilha: tuple[str | int, ...], bruto_raiz: Mapping[str, Any]) -> str:
    partes: list[str] = []
    instrucoes = bruto_raiz.get("instrucoes")
    i = 0
    while i < len(trilha):
        seg = trilha[i]
        if seg == "instrucoes" and i + 1 < len(trilha) and isinstance(trilha[i + 1], int):
            idx = int(trilha[i + 1])
            inst = instrucoes[idx] if isinstance(instrucoes, list) and idx < len(instrucoes) else None
            id_inst = inst.get("id") if isinstance(inst, dict) and isinstance(inst.get("id"), str) else f"#{idx}"
            partes.append(f"instrucao:{id_inst}")
            i += 2
            if i + 1 < len(trilha) and trilha[i] == "guardas" and isinstance(trilha[i + 1], int):
                g_idx = int(trilha[i + 1])
                guardas = inst.get("guardas") if isinstance(inst, dict) else None
                g_obj = guardas[g_idx] if isinstance(guardas, list) and g_idx < len(guardas) else None
                id_g = g_obj.get("id") if isinstance(g_obj, dict) and isinstance(g_obj.get("id"), str) else f"#{g_idx}"
                partes.append(f"guarda:{id_g}")
                i += 2
            continue
        partes.append(f"[{seg}]" if isinstance(seg, int) else str(seg))
        i += 1
    return "/".join(partes) if partes else "raiz"


def _validar_no(
    slug: str,
    instancia: Any,
    sub: Mapping[str, Any],
    raiz_esquema: Mapping[str, Any],
    bruto_raiz: Mapping[str, Any],
    trilha: tuple[str | int, ...],
) -> list[ErroCompilacaoItem]:
    if "$ref" in sub:
        return _validar_no(slug, instancia, _resolver_ref(raiz_esquema, str(sub["$ref"])), raiz_esquema, bruto_raiz, trilha)
    if "oneOf" in sub:
        ramos = [_validar_no(slug, instancia, r, raiz_esquema, bruto_raiz, trilha) for r in sub["oneOf"]]
        if sum(1 for r in ramos if not r) == 1:
            return []
        return [ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), "oneOf", f"valor fora de oneOf: {instancia!r}")]

    tipo = str(sub.get("type") or "")
    checar_tipo: dict[str, Callable[[Any], bool]] = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "boolean": lambda x: isinstance(x, bool),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
    }
    if tipo in checar_tipo and not checar_tipo[tipo](instancia):
        return [ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), f"type:{tipo}", f"esperado {tipo}, recebido {type(instancia).__name__}")]

    erros: list[ErroCompilacaoItem] = []
    if "const" in sub and instancia != sub["const"]:
        erros.append(ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), f"const:{sub['const']}", f"esperado {sub['const']!r}, recebido {instancia!r}"))
    if "enum" in sub and instancia not in sub["enum"]:
        erros.append(ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), "enum", f"valor {instancia!r} fora de {sub['enum']!r}"))

    if tipo == "string":
        if "minLength" in sub and len(instancia) < int(sub["minLength"]):
            erros.append(ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), f"minLength:{sub['minLength']}", f"texto muito curto: {instancia!r}"))
        if "pattern" in sub and re.fullmatch(str(sub["pattern"]), instancia) is None:
            erros.append(ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), f"pattern:{sub['pattern']}", f"valor {instancia!r} fora do padrão"))
    elif tipo == "integer":
        if "minimum" in sub and instancia < int(sub["minimum"]):
            erros.append(ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), f"minimum:{sub['minimum']}", f"inteiro {instancia} < {sub['minimum']}"))
    elif tipo == "array":
        if "minItems" in sub and len(instancia) < int(sub["minItems"]):
            erros.append(ErroCompilacaoItem(slug, _onde_esquema(trilha, bruto_raiz), f"minItems:{sub['minItems']}", f"lista vazia ou abaixo de {sub['minItems']}"))
        esquema_item = sub.get("items")
        if isinstance(esquema_item, Mapping):
            for idx, elem in enumerate(instancia):
                erros.extend(_validar_no(slug, elem, esquema_item, raiz_esquema, bruto_raiz, (*trilha, idx)))
    elif tipo == "object":
        props = sub.get("properties") or {}
        for obrig in sub.get("required") or ():
            if obrig not in instancia:
                erros.append(ErroCompilacaoItem(slug, _onde_esquema((*trilha, obrig), bruto_raiz), f"required:{obrig}", f"campo obrigatório '{obrig}' ausente"))
        if sub.get("additionalProperties") is False:
            for ch in sorted(instancia):
                if ch not in props:
                    erros.append(ErroCompilacaoItem(slug, _onde_esquema((*trilha, ch), bruto_raiz), "additionalProperties:false", f"chave não permitida '{ch}'"))
        for ch, val in instancia.items():
            if ch in props:
                erros.extend(_validar_no(slug, val, props[ch], raiz_esquema, bruto_raiz, (*trilha, ch)))
    return erros


def _carregar_mapa_verbos(porta_yaml: Path) -> dict[str, frozenset[str]]:
    bruto = yaml.safe_load(porta_yaml.read_text(encoding="utf-8"))
    verbos = bruto.get("verbos") if isinstance(bruto, dict) else None
    if not isinstance(verbos, dict):
        return {}
    out: dict[str, frozenset[str]] = {}
    for nome, entrada in verbos.items():
        desc = str(entrada.get("descricao") or "") if isinstance(entrada, dict) else ""
        out[str(nome)] = _extrair_atos_descricao(desc)
    return out


def _validar_registro_verbos(
    slug: str,
    dados: Mapping[str, Any],
    verbos: Mapping[str, frozenset[str]],
) -> list[ErroCompilacaoItem]:
    erros: list[ErroCompilacaoItem] = []
    entra_por = str(dados.get("entra_por") or "")
    if entra_por not in verbos:
        erros.append(ErroCompilacaoItem(slug, "entra_por", "verbo-registrado", f"verbo '{entra_por}' ausente em registro/porta.yaml"))
    elif "despachar" not in verbos[entra_por]:
        erros.append(ErroCompilacaoItem(slug, "entra_por", "verbo-declara-despachar", f"verbo '{entra_por}' não declara o ato 'despachar'"))

    for inst in dados.get("instrucoes") or ():
        if not isinstance(inst, Mapping):
            continue
        id_inst = str(inst.get("id") or "?")
        onde_inst = f"instrucao:{id_inst}"
        verbo = str(inst.get("verbo") or "")
        ato = str(inst.get("ato") or "")
        if verbo in VERBOS_SUBSTRATO_EXTERNO:
            erros.append(ErroCompilacaoItem(slug, onde_inst, "substrato-externo-vedado", f"verbo externo '{verbo}' vedado em pipeline"))
        elif verbo not in verbos:
            erros.append(ErroCompilacaoItem(slug, onde_inst, "verbo-registrado", f"verbo '{verbo}' ausente em registro/porta.yaml"))
        elif ato not in verbos[verbo]:
            erros.append(ErroCompilacaoItem(slug, onde_inst, "ato-declarado-no-verbo", f"ato '{ato}' não declarado no verbo '{verbo}'"))

        for g in inst.get("guardas") or ():
            if not isinstance(g, Mapping):
                continue
            gid = str(g.get("id") or "?")
            onde_g = f"{onde_inst}/guarda:{gid}"
            g_verbo = str(g.get("verbo") or "")
            if g_verbo not in verbos:
                erros.append(ErroCompilacaoItem(slug, onde_g, "verbo-registrado", f"verbo '{g_verbo}' da guarda ausente em registro/porta.yaml"))
            elif "verificar" not in verbos[g_verbo] and "ler" not in verbos[g_verbo]:
                erros.append(ErroCompilacaoItem(slug, onde_g, "ato-declarado-no-verbo", f"verbo '{g_verbo}' da guarda não declara 'verificar' nem 'ler'"))
    return erros


def _calcular_digest_corpo(dados: Mapping[str, Any]) -> str:
    corpo = {k: v for k, v in dados.items() if k != "procedencia"}
    canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonico).hexdigest()


def _consultar_fichario_olaria(env: Mapping[str, str]) -> tuple[str, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    amb = dict(env)
    url = (_ler_segredo("OLARIA_URL", amb) or OLARIA_URL_PADRAO).strip()
    chave = _ler_segredo("OLARIA_CHAVE", amb)
    if not chave:
        raise OlariaIndisponivel("OLARIA_CHAVE ausente no ambiente e no cofre")
    resp_pip = _consultar_classe("pipeline", url, chave)
    resp_cfg = _consultar_classe("configuracao", url, chave)

    pipelines: dict[str, dict[str, Any]] = {}
    fornada_ficha = ""
    for f in resp_pip.get("fichas") or ():
        if isinstance(f, Mapping):
            chave_f = str(f.get("chave") or f.get("slug") or "")
            slug = chave_f.removeprefix("pipeline:")
            if slug:
                pipelines[slug] = dict(f)
                if not fornada_ficha and f.get("versao"):
                    fornada_ficha = str(f["versao"])

    configs: dict[str, dict[str, Any]] = {}
    for f in resp_cfg.get("fichas") or ():
        if isinstance(f, Mapping):
            chave_f = str(f.get("chave") or f.get("slug") or "")
            slug = chave_f.removeprefix("configuracao:")
            if slug:
                configs[slug] = dict(f)
                if not fornada_ficha and f.get("versao"):
                    fornada_ficha = str(f["versao"])

    fornada = str(resp_pip.get("fornada") or resp_cfg.get("fornada") or fornada_ficha or "desconhecida")
    return fornada, pipelines, configs


def _caminho_fonte_config(slug: str, ficha_cfg: Mapping[str, Any] | None, arvore: Path) -> Path:
    if isinstance(ficha_cfg, Mapping):
        dados_f = ficha_cfg.get("dados") if isinstance(ficha_cfg.get("dados"), Mapping) else ficha_cfg
        cam = str(dados_f.get("caminho") or "").strip()
        if cam:
            p = Path(cam)
            return p if p.is_absolute() else (arvore / p)
    return arvore / "registro" / "pipelines" / "fontes" / f"{slug}.yaml"


def compilar_pipelines(
    *,
    arvore: Path,
    sha: str,
    saida_dir: Path | None = None,
    ensaio: bool = False,
    agora_iso: str | None = None,
    consultar_fichario: Callable[[], tuple[str, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]] | None = None,
) -> list[ArtefatoCompilado]:
    """Valida todas as configurações de pipeline e compila `registro/pipelines/<slug>.yaml`."""
    arvore_real = Path(arvore).resolve()
    esquema_path = arvore_real / "registro" / "esquemas" / "pipeline.schema.json"
    porta_yaml = arvore_real / "registro" / "porta.yaml"
    fontes_dir = arvore_real / "registro" / "pipelines" / "fontes"
    destino_dir = Path(saida_dir) if saida_dir is not None else (arvore_real / "registro" / "pipelines")

    esquema = json.loads(esquema_path.read_text(encoding="utf-8"))
    verbos = _carregar_mapa_verbos(porta_yaml)
    leitor_fichario = consultar_fichario or (lambda: _consultar_fichario_olaria(os.environ))
    fornada, fichas_pipeline, fichas_config = leitor_fichario()

    erros: list[ErroCompilacaoItem] = []
    slugs_fontes = (
        {p.stem for p in sorted(fontes_dir.glob("*.yaml"))}
        if fontes_dir.is_dir()
        else set()
    )
    todos_slugs = sorted(set(fichas_pipeline) | slugs_fontes)
    prontos: list[tuple[str, dict[str, Any], str]] = []
    compilado_em = agora_iso or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for slug in todos_slugs:
        if slug not in fichas_pipeline:
            erros.append(ErroCompilacaoItem(slug, "fichario", "ficha-pipeline-existente", f"arquivo fonte '{slug}.yaml' sem ficha pipeline:{slug} no fichário"))
            continue
        ficha_cfg = fichas_config.get(slug)
        if ficha_cfg is None:
            erros.append(ErroCompilacaoItem(slug, "fichario", "ficha-configuracao-existente", f"ficha configuracao:{slug} ausente no fichário"))
            continue

        arq_fonte = _caminho_fonte_config(slug, ficha_cfg, arvore_real)
        if not arq_fonte.is_file():
            erros.append(ErroCompilacaoItem(slug, "configuracao", "arquivo-configuracao-existente", f"arquivo '{arq_fonte}' não encontrado"))
            continue

        try:
            bruto = yaml.safe_load(arq_fonte.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            erros.append(ErroCompilacaoItem(slug, "sintaxe", "yaml-valido", str(exc)))
            continue

        if not isinstance(bruto, dict):
            erros.append(ErroCompilacaoItem(slug, "raiz", "type:object", "configuração de pipeline deve ser mapeamento YAML"))
            continue

        compilado = dict(bruto)
        compilado["versao_esquema"] = VERSAO_ESQUEMA
        digest = _calcular_digest_corpo(compilado)
        compilado["procedencia"] = {
            "ficha": f"pipeline:{slug}",
            "configuracao": f"configuracao:{slug}",
            "fornada": fornada,
            "sha": sha,
            "compilado_em": compilado_em,
            "digest": digest,
        }

        erros_item = _validar_no(slug, compilado, esquema, esquema, compilado, ())
        if compilado.get("pipeline") != slug:
            erros_item.append(ErroCompilacaoItem(slug, "pipeline", "identidade-do-pipeline", f"campo pipeline='{compilado.get('pipeline')}' diverge de '{slug}'"))
        erros_item.extend(_validar_registro_verbos(slug, compilado, verbos))

        if erros_item:
            erros.extend(erros_item)
        else:
            prontos.append((slug, compilado, digest))

    if erros:
        raise ErroCompilacaoPipeline(erros)

    compilados: list[ArtefatoCompilado] = []
    if not ensaio and prontos:
        destino_dir.mkdir(parents=True, exist_ok=True)
    for slug, corpo, digest in prontos:
        alvo = destino_dir / f"{slug}.yaml"
        if not ensaio:
            tmp = destino_dir / f".{slug}.yaml.tmp.{os.getpid()}"
            tmp.write_text(yaml.safe_dump(corpo, allow_unicode=True, sort_keys=False), encoding="utf-8")
            os.replace(tmp, alvo)
        compilados.append(ArtefatoCompilado(slug=slug, caminho=alvo, digest=digest, fornada=fornada))
    return compilados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m pipelines.gerar")
    parser.add_argument("--arvore", required=True, help="raiz da árvore do harness")
    parser.add_argument("--sha", required=True, help="SHA da revisão em promoção")
    parser.add_argument("--saida", default="", help="diretório de saída dos artefatos compilados")
    parser.add_argument("--ensaio", action="store_true", help="valida sem gravar artefatos")
    ns = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        itens = compilar_pipelines(
            arvore=Path(ns.arvore),
            sha=ns.sha,
            saida_dir=Path(ns.saida) if ns.saida else None,
            ensaio=bool(ns.ensaio),
        )
    except OlariaIndisponivel as exc:
        sys.stderr.write(f"pipelines: dependência indisponível (fichário): {exc}\n")
        return SAIDA_DEPENDENCIA
    except ErroCompilacaoPipeline as exc:
        for err in exc.erros:
            sys.stderr.write(f"pipelines: recusa: {err.formatar()}\n")
        return SAIDA_RECUSA

    modo = "ensaio" if ns.ensaio else "compilados"
    if not itens:
        sys.stdout.write(f"pipelines: 0 artefatos ({modo})\n")
    else:
        for item in itens:
            sys.stdout.write(f"pipelines: {modo} {item.slug} -> {item.caminho} ({item.digest[:19]})\n")
    return SAIDA_OK


if __name__ == "__main__":
    raise SystemExit(main())
