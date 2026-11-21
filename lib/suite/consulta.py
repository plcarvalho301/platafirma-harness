"""Consulta da suíte: calcula do código e da ontologia o que cada teste protege, quando roda e o alvo encerrado (#4298)."""
from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from suite.admissao import SERVICOS_CONHECIDOS_PREFIXO, OlariaIndisponivelErro
from suite.selecao import descobrir_arquivos_teste
from suite.vinculo import (
    VinculoArquivo,
    extrair_slug_componente,
    ler_vinculo,
    normalizar_componente,
)

_HTTP_ERRO_SERVIDOR = 500
_TIMEOUT_OLARIA_S = 30.0
MOMENTOS_VALIDOS = frozenset({"fita", "push", "integracao"})
ARQUIVOS_DUBLE_ARVORE = (".olaria.json", "olaria.json", ".olaria.yaml", "olaria.yaml")

SHAPES_PADRAO: dict[str, dict[str, Any]] = {
    "componente": {
        "slug": "componente",
        "capacidade": "capacidade:desenvolvimento",
        "estados": [],
        "transicoes": [],
    },
    "interface": {
        "slug": "interface",
        "capacidade": "capacidade:operacao",
        "estados": [],
        "transicoes": [],
    },
    "contrato-da-porta": {
        "slug": "contrato-da-porta",
        "capacidade": "capacidade:operacao",
        "estados": [],
        "transicoes": [],
    },
    "politica": {
        "slug": "politica",
        "capacidade": "capacidade:norma",
        "estados": ["descartada", "minuta", "revogada", "vigente"],
        "transicoes": [
            {"de": "minuta", "para": "descartada"},
            {"de": "minuta", "para": "vigente"},
            {"de": "vigente", "para": "revogada"},
            {"para": "minuta"},
        ],
    },
    "gabarito": {
        "slug": "gabarito",
        "capacidade": "capacidade:gestao-de-motores",
        "estados": [],
        "transicoes": [],
    },
    "configuracao": {
        "slug": "configuracao",
        "capacidade": "capacidade:operacao",
        "estados": [],
        "transicoes": [],
    },
    "servico": {
        "slug": "servico",
        "capacidade": "capacidade:operacao",
        "estados": ["declarado", "derrubado", "removido", "servindo"],
        "transicoes": [
            {"de": "declarado", "para": "servindo"},
            {"de": "derrubado", "para": "removido"},
            {"de": "derrubado", "para": "servindo"},
            {"de": "servindo", "para": "derrubado"},
            {"para": "declarado"},
        ],
    },
    "modelo": {
        "slug": "modelo",
        "capacidade": "capacidade:gestao-de-motores",
        "estados": [],
        "transicoes": [],
    },
    "embedder": {
        "slug": "embedder",
        "capacidade": "capacidade:gestao-de-motores",
        "estados": [],
        "transicoes": [],
    },
    "host": {
        "slug": "host",
        "capacidade": "capacidade:operacao",
        "estados": [],
        "transicoes": [],
    },
    "controle-de-seguranca": {
        "slug": "controle-de-seguranca",
        "capacidade": "capacidade:controles",
        "estados": ["proposto", "retirado", "vigente"],
        "transicoes": [
            {"de": "proposto", "para": "vigente"},
            {"de": "vigente", "para": "retirado"},
            {"para": "proposto"},
        ],
    },
}

AUTORIDADES_PADRAO: dict[str, str] = {
    "capacidade:acervo": "conhecimento",
    "capacidade:acesso": "seguranca",
    "capacidade:administracao": "direito",
    "capacidade:analise": "dados",
    "capacidade:apostas": "produto",
    "capacidade:arquitetura": "arquiteto",
    "capacidade:busca": "ia",
    "capacidade:canais": "engenharia",
    "capacidade:comportamento": "produto",
    "capacidade:controles": "seguranca",
    "capacidade:dados": "dados",
    "capacidade:delegacao": "ia",
    "capacidade:desenvolvimento": "engenharia",
    "capacidade:distribuicoes": "dados",
    "capacidade:gatilhos": "produto",
    "capacidade:gestao-de-motores": "ia",
    "capacidade:gestao-estrategica": "gestao-estrategica",
    "capacidade:harness": "ti",
    "capacidade:inteligencia": "inteligencia",
    "capacidade:memoria": "ia",
    "capacidade:mensageria": "dados",
    "capacidade:modelos-formais": "conhecimento",
    "capacidade:norma": "arquiteto",
    "capacidade:operacao": "ti",
    "capacidade:pesquisa": "inteligencia",
    "capacidade:producao-do-conhecimento": "inteligencia",
    "capacidade:propensoes": "ia",
    "capacidade:prosa": "produto",
    "capacidade:tarefas": "gestao-estrategica",
    "capacidade:tesauros": "conhecimento",
}


def _raiz_padrao() -> Path:
    atual = Path(__file__).resolve()
    for p in atual.parents:
        if (p / ".git").exists():
            return p
    return Path.cwd()


def _normalizar_stack(valor: str) -> tuple[str, str]:
    limpo = valor.strip()
    if limpo.startswith("stack:"):
        slug = limpo.removeprefix("stack:")
        return f"stack:{slug}", slug
    return f"stack:{limpo}", limpo


def _normalizar_momento(valor: str) -> str:
    limpo = valor.strip().lower().replace("ç", "c").replace("ã", "a")
    return limpo


def _como_lista_str(valor: Any) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        limpo = valor.strip()
        return [limpo] if limpo else []
    if isinstance(valor, Iterable):
        return [str(x).strip() for x in valor if str(x).strip()]
    return [str(valor).strip()]


def inferir_classe_entidade(chave: str, *, papel: str = "alvo") -> str:
    limpa = chave.strip()
    if ":" in limpa:
        pref = limpa.split(":", 1)[0].lower()
        if pref in SERVICOS_CONHECIDOS_PREFIXO or pref == "servico":
            return "servico"
        if pref in SHAPES_PADRAO:
            return pref
        if papel == "exige":
            return "servico"
        return pref
    baixa = limpa.lower()
    for prefixo, cls in (
        ("interface-", "interface"),
        ("contrato-", "contrato-da-porta"),
        ("politica-", "politica"),
        ("gabarito-", "gabarito"),
        ("configuracao-", "configuracao"),
        ("embedder-", "embedder"),
        ("modelo-", "modelo"),
        ("host-", "host"),
        ("servico-", "servico"),
    ):
        if baixa.startswith(prefixo):
            return cls
    if papel == "componente":
        return "componente"
    if papel == "exige":
        return "servico"
    return "interface"


@dataclass(frozen=True)
class MotivoRetirada:
    entidade: str
    papel: str
    classe: str
    codigo: str
    motivo: str
    responsavel: str

    def como_dict(self) -> dict[str, str]:
        return {
            "entidade": self.entidade,
            "papel": self.papel,
            "classe": self.classe,
            "codigo": self.codigo,
            "motivo": self.motivo,
            "responsavel": self.responsavel,
        }


@dataclass(frozen=True)
class VerificacaoConsultada:
    arquivo: str
    componente: str
    classe: str
    alvo: str | None
    exige: tuple[str, ...]
    incidentes: tuple[int, ...]
    momentos: tuple[str, ...]
    quando_roda: str
    lado_fronteira: str | None = None
    situacao_estado: str | None = None
    para_retirada: bool = False
    motivos_retirada: tuple[MotivoRetirada, ...] = ()
    responsavel_retirada: str | None = None

    def como_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "arquivo": self.arquivo,
            "componente": self.componente,
            "classe": self.classe,
            "alvo": self.alvo or "comportamento",
            "exige": list(self.exige),
            "incidentes": list(self.incidentes),
            "momentos": list(self.momentos),
            "quando_roda": self.quando_roda,
            "para_retirada": self.para_retirada,
        }
        if self.lado_fronteira is not None:
            d["lado_fronteira"] = self.lado_fronteira
        if self.situacao_estado is not None:
            d["situacao_estado"] = self.situacao_estado
        if self.motivos_retirada:
            d["motivos_retirada"] = [m.como_dict() for m in self.motivos_retirada]
            d["responsavel"] = self.responsavel_retirada
        return d

    def linha_texto(self, *, incluir_lado: bool = False) -> str:
        alvo_str = self.alvo or "comportamento"
        exige_str = ", ".join(self.exige) if self.exige else "nenhum"
        partes = [
            self.arquivo,
            f"componente={self.componente}",
            f"classe={self.classe}",
            f"alvo={alvo_str}",
            f"exige={exige_str}",
            f"momento={self.quando_roda}",
        ]
        if incluir_lado and self.lado_fronteira is not None:
            partes.append(f"lado={self.lado_fronteira}")
        if self.situacao_estado is not None:
            partes.append(f"estado={self.situacao_estado}")
        if self.para_retirada:
            detalhes = "; ".join(
                f"{m.papel} {m.entidade}: {m.motivo} (responde: {m.responsavel})"
                for m in self.motivos_retirada
            )
            partes.append(f"para retirada [{detalhes}]")
        return " | ".join(partes)


@dataclass(frozen=True)
class ResultadoConsultaComponente:
    componente: str
    verificacoes: tuple[VerificacaoConsultada, ...]

    def como_dict(self) -> dict[str, Any]:
        return {
            "componente": self.componente,
            "total": len(self.verificacoes),
            "para_retirada": [v.como_dict() for v in self.verificacoes if v.para_retirada],
            "verificacoes": [v.como_dict() for v in self.verificacoes],
        }

    def resumo_texto(self) -> str:
        if not self.verificacoes:
            return f"componente {self.componente}: 0 verificações"
        return "\n".join(v.linha_texto() for v in self.verificacoes)


@dataclass(frozen=True)
class ResultadoConsultaStack:
    stack: str
    componentes: tuple[str, ...]
    verificacoes: tuple[VerificacaoConsultada, ...]
    fornece: tuple[VerificacaoConsultada, ...]
    consome: tuple[VerificacaoConsultada, ...]
    lado_nao_declarado: tuple[VerificacaoConsultada, ...]

    def como_dict(self) -> dict[str, Any]:
        return {
            "stack": self.stack,
            "componentes": list(self.componentes),
            "total": len(self.verificacoes),
            "verificacoes": [v.como_dict() for v in self.verificacoes],
            "fronteira": {
                "fornece": [v.como_dict() for v in self.fornece],
                "consome": [v.como_dict() for v in self.consome],
                "lado_nao_declarado": [v.como_dict() for v in self.lado_nao_declarado],
            },
            "para_retirada": [v.como_dict() for v in self.verificacoes if v.para_retirada],
        }

    def resumo_texto(self) -> str:
        linhas = [f"stack: {self.stack} ({len(self.verificacoes)} verificação(ões))"]
        internas = [v for v in self.verificacoes if v.classe != "teste-de-fronteira"]
        if internas:
            linhas.append("comportamento e regra:")
            for v in internas:
                linhas.append(f"  {v.linha_texto()}")
        linhas.append("fronteira — quem fornece:")
        if self.fornece:
            for v in self.fornece:
                linhas.append(f"  {v.linha_texto(incluir_lado=True)}")
        else:
            linhas.append("  (nenhuma)")
        linhas.append("fronteira — quem consome:")
        if self.consome:
            for v in self.consome:
                linhas.append(f"  {v.linha_texto(incluir_lado=True)}")
        else:
            linhas.append("  (nenhuma)")
        if self.lado_nao_declarado:
            linhas.append("fronteira — lado não declarado:")
            for v in self.lado_nao_declarado:
                linhas.append(f"  {v.linha_texto(incluir_lado=True)}")
        return "\n".join(linhas)


@dataclass(frozen=True)
class ResultadoConsultaMomento:
    momento: str
    roda_testes: bool
    descricao: str
    verificacoes: tuple[VerificacaoConsultada, ...]

    def como_dict(self) -> dict[str, Any]:
        return {
            "momento": self.momento,
            "roda_testes": self.roda_testes,
            "descricao": self.descricao,
            "total": len(self.verificacoes),
            "verificacoes": [v.como_dict() for v in self.verificacoes],
        }

    def resumo_texto(self) -> str:
        linhas = [f"momento: {self.momento} — {self.descricao}"]
        for v in self.verificacoes:
            linhas.append(f"  {v.linha_texto()}")
        return "\n".join(linhas)


@dataclass(frozen=True)
class ResultadoConsultaSoltos:
    arvore: str
    total_descobertos: int
    total_soltos: int
    com_vinculo: int
    arquivos: tuple[str, ...]

    def como_dict(self) -> dict[str, Any]:
        return {
            "arvore": self.arvore,
            "total_descobertos": self.total_descobertos,
            "total_soltos": self.total_soltos,
            "com_vinculo": self.com_vinculo,
            "arquivos": list(self.arquivos),
        }

    def resumo_texto(self) -> str:
        cabecalho = (
            f"soltos: {self.total_soltos} arquivo(s) sem vínculo "
            f"(de {self.total_descobertos} descobertos, {self.com_vinculo} com vínculo)"
        )
        linhas = [cabecalho]
        for arq in self.arquivos:
            linhas.append(f"  {arq}")
        return "\n".join(linhas)


class DubleLeitorOlaria:
    """Dublê em processo do leitor da Olaria para testes e árvores de prova da consulta."""

    def __init__(
        self,
        fichas: Iterable[dict[str, Any] | str] | Mapping[str, Any] = (),
        *,
        estados: Mapping[str, str | None] | None = None,
        desfechos: Iterable[str | dict[str, Any]] = (),
        fora_do_ar: bool = False,
    ) -> None:
        self.fora_do_ar = fora_do_ar
        self.shapes: dict[str, dict[str, Any]] = {k: dict(v) for k, v in SHAPES_PADRAO.items()}
        self.autoridades: dict[str, str] = dict(AUTORIDADES_PADRAO)
        self._por_classe: dict[str, dict[str, dict[str, Any]]] = {}
        self._carregar_capacidades_padrao()
        self._carregar_fichas_iniciais(fichas)

        if estados:
            for chave, est in estados.items():
                self.definir_estado(chave, est)

        for d in desfechos:
            if isinstance(d, str):
                self.registrar_desfecho(d)
            elif isinstance(d, dict):
                self.registrar_ficha("desfecho", d)

    def _carregar_capacidades_padrao(self) -> None:
        caps = self._por_classe.setdefault("capacidade", {})
        for cap, persona in self.autoridades.items():
            caps[cap] = {
                "classe": "capacidade",
                "chave": cap,
                "ligacoes": {"sob-autoridade-de": persona},
            }

    def _carregar_item_mapeamento(self, chave: str, val: Any) -> None:
        if isinstance(val, list) and chave in self.shapes:
            for item in val:
                if isinstance(item, dict):
                    self.registrar_ficha(chave, item)
        elif isinstance(val, str):
            self.registrar_ficha(val, {"chave": chave})
        elif isinstance(val, dict):
            cls = str(val.get("classe") or inferir_classe_entidade(chave))
            copia = dict(val)
            copia.setdefault("chave", chave)
            self.registrar_ficha(cls, copia)

    def _carregar_fichas_iniciais(
        self,
        fichas: Iterable[dict[str, Any] | str] | Mapping[str, Any],
    ) -> None:
        if isinstance(fichas, Mapping):
            for k, val in fichas.items():
                self._carregar_item_mapeamento(k, val)
            return
        for item in fichas:
            if isinstance(item, str):
                self.registrar_ficha(inferir_classe_entidade(item), {"chave": item})
            elif isinstance(item, dict):
                chave = str(item.get("chave") or "")
                cls = str(item.get("classe") or inferir_classe_entidade(chave))
                self.registrar_ficha(cls, item)

    def registrar_ficha(self, classe: str, ficha: dict[str, Any]) -> None:
        copia = dict(ficha)
        chave = str(copia.get("chave") or "").strip()
        if not chave:
            return
        if classe == "componente" and not chave.startswith("componente:"):
            chave = f"componente:{chave}"
            copia["chave"] = chave
        copia["classe"] = classe
        copia.setdefault("dados", {})
        copia.setdefault("ligacoes", {})
        self._por_classe.setdefault(classe, {})[chave] = copia

    def definir_estado(self, chave: str, estado: str | None) -> None:
        for mapa in self._por_classe.values():
            if chave in mapa:
                if estado is None:
                    mapa[chave].pop("estado", None)
                else:
                    mapa[chave]["estado"] = estado
                return
        cls = inferir_classe_entidade(chave)
        ficha: dict[str, Any] = {"chave": chave, "classe": cls}
        if estado is not None:
            ficha["estado"] = estado
        self.registrar_ficha(cls, ficha)

    def registrar_desfecho(self, chave_alvo: str, chave_desfecho: str | None = None) -> None:
        ch_d = chave_desfecho or f"desfecho:encerra-{chave_alvo.replace(':', '-')}"
        self.registrar_ficha(
            "desfecho",
            {"chave": ch_d, "ligacoes": {"encerra": chave_alvo}},
        )

    @classmethod
    def de_arquivo(cls, caminho: str | Path) -> DubleLeitorOlaria:
        arq = Path(caminho)
        texto = arq.read_text(encoding="utf-8")
        dados = yaml.safe_load(texto) if arq.suffix.lower() in (".yaml", ".yml") else json.loads(texto)
        if not isinstance(dados, dict):
            return cls()
        inst = cls(
            fichas=dados.get("fichas") or (),
            estados=dados.get("estados"),
            desfechos=dados.get("desfechos") or (),
            fora_do_ar=bool(dados.get("fora_do_ar", False)),
        )
        for slug, sh in (dados.get("shapes") or {}).items():
            if isinstance(sh, dict):
                inst.shapes.setdefault(slug, {}).update(sh)
        if isinstance(dados.get("autoridades"), dict):
            inst.autoridades.update(dados["autoridades"])
            inst._carregar_capacidades_padrao()
        return inst

    def ler_shape(self, classe: str) -> dict[str, Any] | None:
        if self.fora_do_ar:
            raise OlariaIndisponivelErro("serviço da Olaria fora do ar")
        return self.shapes.get(classe)

    def ler_fichas(self, classe: str) -> list[dict[str, Any]]:
        if self.fora_do_ar:
            raise OlariaIndisponivelErro("serviço da Olaria fora do ar")
        return list(self._por_classe.get(classe, {}).values())

    def ler_ficha(self, classe: str, chave: str) -> dict[str, Any] | None:
        if self.fora_do_ar:
            raise OlariaIndisponivelErro("serviço da Olaria fora do ar")
        mapa = self._por_classe.get(classe, {})
        if chave in mapa:
            return mapa[chave]
        for outro_mapa in self._por_classe.values():
            if chave in outro_mapa:
                return outro_mapa[chave]
        return None


class LeitorOlaria:
    """Cliente HTTP de leitura da Olaria (`POST /ler`) com cache por consulta."""

    def __init__(
        self,
        url: str | None = None,
        chave: str | None = None,
        timeout_s: float = _TIMEOUT_OLARIA_S,
    ) -> None:
        self.url = (url or os.environ.get("OLARIA_URL") or "").rstrip("/")
        self.chave = chave or os.environ.get("OLARIA_CHAVE") or ""
        self.timeout_s = timeout_s
        self._shapes_cache: dict[str, dict[str, Any]] = {}
        self._fichas_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._shapes_carregados = False

    def _cabecalhos_http(self) -> dict[str, str]:
        cab = {
            "X-Olaria-Chave": self.chave,
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "suite-consulta",
        }
        sujeito = os.environ.get("PF_CADEIRA", "engenharia")
        if sujeito:
            cab["X-Olaria-Sujeito"] = sujeito
        return cab

    def _post_ler(self, classe: str, chaves: list[str], *, fichas: bool) -> dict[str, Any]:
        if not self.url or not self.chave:
            raise OlariaIndisponivelErro("OLARIA_URL ou OLARIA_CHAVE ausente no ambiente")
        payload = {"classe": classe, "chaves": chaves, "fichas": fichas}
        req = urllib.request.Request(
            f"{self.url}/ler",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._cabecalhos_http(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                texto_resp, codigo_http = resp.read().decode("utf-8", "replace"), resp.status
        except urllib.error.HTTPError as exc:
            texto_resp, codigo_http = exc.read().decode("utf-8", "replace"), exc.code
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException, OSError) as exc:
            raise OlariaIndisponivelErro(f"falha de leitura na Olaria ({self.url}): {exc}") from exc

        try:
            objeto = json.loads(texto_resp or "{}")
        except ValueError as exc:
            raise OlariaIndisponivelErro(f"JSON inválido da Olaria (HTTP {codigo_http})") from exc

        if not isinstance(objeto, dict):
            return {}
        if codigo_http >= _HTTP_ERRO_SERVIDOR or objeto.get("estado") in ("fora-do-ar", "defeito"):
            raise OlariaIndisponivelErro(str(objeto.get("erro") or f"HTTP {codigo_http}"))
        return objeto

    def _garantir_shapes_basicos(self) -> None:
        if self._shapes_carregados:
            return
        self._shapes_carregados = True
        dados = self._post_ler("shape", list(SHAPES_PADRAO.keys()), fichas=False)
        yaml_txt = dados.get("yaml")
        if isinstance(yaml_txt, str) and yaml_txt.strip():
            doc = yaml.safe_load(yaml_txt)
            if isinstance(doc, dict):
                for item in doc.get("classes") or []:
                    if isinstance(item, dict) and item.get("slug"):
                        self._shapes_cache[str(item["slug"])] = item

    def ler_shape(self, classe: str) -> dict[str, Any] | None:
        self._garantir_shapes_basicos()
        if classe in self._shapes_cache:
            return self._shapes_cache[classe]
        dados = self._post_ler("shape", [classe], fichas=False)
        yaml_txt = dados.get("yaml")
        if isinstance(yaml_txt, str) and yaml_txt.strip():
            doc = yaml.safe_load(yaml_txt)
            if isinstance(doc, dict):
                for item in doc.get("classes") or []:
                    if isinstance(item, dict) and item.get("slug"):
                        self._shapes_cache[str(item["slug"])] = item
        return self._shapes_cache.get(classe) or SHAPES_PADRAO.get(classe)

    def ler_fichas(self, classe: str) -> list[dict[str, Any]]:
        if classe not in self._fichas_cache:
            dados = self._post_ler(classe, [], fichas=True)
            mapa: dict[str, dict[str, Any]] = {}
            yaml_txt = dados.get("yaml")
            if isinstance(yaml_txt, str) and yaml_txt.strip():
                doc = yaml.safe_load(yaml_txt)
                if isinstance(doc, dict):
                    for item in doc.get("fichas") or []:
                        if isinstance(item, dict) and item.get("chave"):
                            copia = dict(item)
                            copia.setdefault("classe", classe)
                            mapa[str(copia["chave"])] = copia
            self._fichas_cache[classe] = mapa
        return list(self._fichas_cache[classe].values())

    def ler_ficha(self, classe: str, chave: str) -> dict[str, Any] | None:
        self.ler_fichas(classe)
        return self._fichas_cache.get(classe, {}).get(chave)


def _resolver_leitor(raiz: Path, leitor: Any = None) -> Any:
    if leitor is not None:
        return leitor
    arq_env = os.environ.get("PF_SUITE_OLARIA_ARQUIVO")
    if arq_env and Path(arq_env).is_file():
        return DubleLeitorOlaria.de_arquivo(arq_env)
    for nome in ARQUIVOS_DUBLE_ARVORE:
        cand = raiz / nome
        if cand.is_file():
            return DubleLeitorOlaria.de_arquivo(cand)
    return LeitorOlaria()


def _calcular_momentos(v: VinculoArquivo) -> tuple[tuple[str, ...], str]:
    classe = v.classe or "teste-de-comportamento"
    if classe == "teste-de-comportamento":
        momentos = ("fita", "push")
        partes = ["fita", "push (quando alcançado)"]
    else:
        momentos = ("push",)
        partes = ["push (quando componente ou alvo verifica muda)"]

    if v.exige:
        partes.append("push (quando componente ou entidade exigida muda)")
    if v.incidentes:
        partes.append("todo push (incidente)")
    return momentos, ", ".join(partes)


def _resolver_responsavel(leitor: Any, classe: str) -> str:
    shape = leitor.ler_shape(classe) or SHAPES_PADRAO.get(classe) or {}
    cap = str(shape.get("capacidade") or "capacidade:desenvolvimento")
    ficha_cap = leitor.ler_ficha("capacidade", cap)
    if isinstance(ficha_cap, dict):
        ligs = ficha_cap.get("ligacoes") or {}
        aut = _como_lista_str(ligs.get("sob-autoridade-de"))
        if aut:
            return aut[0].removeprefix("persona:")
    return AUTORIDADES_PADRAO.get(cap, "engenharia")


def _estados_sem_saida(shape: dict[str, Any] | None) -> tuple[set[str], set[str]]:
    if not shape:
        return set(), set()
    estados = {str(e).strip() for e in (shape.get("estados") or []) if str(e).strip()}
    if not estados:
        return set(), set()
    com_saida = {
        str(t.get("de")).strip()
        for t in (shape.get("transicoes") or [])
        if isinstance(t, dict) and t.get("de")
    }
    return estados, estados - com_saida


def _chaves_encerradas_por_desfecho(leitor: Any) -> set[str]:
    encerradas: set[str] = set()
    for ficha in leitor.ler_fichas("desfecho"):
        ligs = ficha.get("ligacoes") or {}
        for alvo in _como_lista_str(ligs.get("encerra")):
            encerradas.add(alvo)
    return encerradas


def _avaliar_entidade(
    leitor: Any,
    chave: str,
    papel: str,
    encerradas_desfecho: set[str],
) -> tuple[MotivoRetirada | None, str | None]:
    classe = inferir_classe_entidade(chave, papel=papel)
    ficha = leitor.ler_ficha(classe, chave)
    if ficha is not None and ficha.get("classe"):
        classe = str(ficha["classe"])
    responsavel = _resolver_responsavel(leitor, classe)

    if ficha is None:
        return (
            MotivoRetirada(
                entidade=chave,
                papel=papel,
                classe=classe,
                codigo="sem-ficha",
                motivo="sem ficha",
                responsavel=responsavel,
            ),
            None,
        )

    # O embedder obsoleto que ainda serve uma geração segue vivo; só é acusado sem ficha.
    if classe == "embedder":
        return None, None

    if chave in encerradas_desfecho or bool((ficha.get("dados") or {}).get("encerrado")):
        return (
            MotivoRetirada(
                entidade=chave,
                papel=papel,
                classe=classe,
                codigo="evento-de-encerramento",
                motivo="evento de encerramento",
                responsavel=responsavel,
            ),
            None,
        )

    shape = leitor.ler_shape(classe) or SHAPES_PADRAO.get(classe)
    estados_decl, terminais = _estados_sem_saida(shape)
    if not estados_decl:
        return None, None

    dados_ficha = ficha.get("dados") if isinstance(ficha.get("dados"), dict) else {}
    estado_lido = ficha.get("estado") or dados_ficha.get("estado")
    if not estado_lido:
        return None, "estado não lido"

    est_str = str(estado_lido).strip()
    if est_str in terminais:
        return (
            MotivoRetirada(
                entidade=chave,
                papel=papel,
                classe=classe,
                codigo="estado-sem-saida",
                motivo=f"estado sem transição de saída ({est_str})",
                responsavel=responsavel,
            ),
            est_str,
        )
    return None, est_str


def _determinar_lado_fronteira(leitor: Any, componente: str, alvo: str | None) -> str | None:
    if not alvo:
        return None
    slug_comp = extrair_slug_componente(componente) or componente
    chaves_comp = {componente, slug_comp, f"componente:{slug_comp}"}

    ficha_iface = leitor.ler_ficha("interface", alvo) or leitor.ler_ficha("contrato-da-porta", alvo)
    if isinstance(ficha_iface, dict):
        ligs_if = ficha_iface.get("ligacoes") or {}
        garantidores = set(_como_lista_str(ligs_if.get("garantido-por")))
        if garantidores & chaves_comp:
            return "fornece"

    ficha_comp = leitor.ler_ficha("componente", componente)
    ligs_comp = (ficha_comp.get("ligacoes") or {}) if isinstance(ficha_comp, dict) else {}
    if alvo in _como_lista_str(ligs_comp.get("expoe")) or alvo in _como_lista_str(ligs_comp.get("fornece")):
        return "fornece"
    if alvo in _como_lista_str(ligs_comp.get("consome")):
        return "consome"

    servicos_do_comp = set(_como_lista_str(ligs_comp.get("componente-de"))) | set(
        _como_lista_str(ligs_comp.get("servico"))
    )
    for srv_chave in servicos_do_comp:
        ficha_srv = leitor.ler_ficha("servico", srv_chave)
        if not isinstance(ficha_srv, dict):
            continue
        ligs_srv = ficha_srv.get("ligacoes") or {}
        if alvo in _como_lista_str(ligs_srv.get("expoe")):
            return "fornece"
        if alvo in _como_lista_str(ligs_srv.get("consome")):
            return "consome"

    return "lado não declarado"


def _construir_verificacao(
    raiz: Path,
    v: VinculoArquivo,
    leitor: Any,
    encerradas_desfecho: set[str],
) -> VerificacaoConsultada:
    rel = v.caminho.relative_to(raiz).as_posix() if v.caminho.is_relative_to(raiz) else v.caminho.name
    comp = v.componente or ""
    classe = v.classe or "teste-de-comportamento"
    momentos, quando_roda = _calcular_momentos(v)

    motivos: list[MotivoRetirada] = []
    situacoes_estado: list[str] = []

    m_comp, est_comp = _avaliar_entidade(leitor, comp, "componente", encerradas_desfecho)
    if m_comp is not None:
        motivos.append(m_comp)
    if est_comp is not None:
        situacoes_estado.append(est_comp)

    if v.verifica is not None:
        m_alvo, est_alvo = _avaliar_entidade(leitor, v.verifica, "alvo", encerradas_desfecho)
        if m_alvo is not None:
            motivos.append(m_alvo)
        if est_alvo is not None:
            situacoes_estado.append(est_alvo)

    for ex in v.exige:
        m_ex, est_ex = _avaliar_entidade(leitor, ex, "exige", encerradas_desfecho)
        if m_ex is not None:
            motivos.append(m_ex)
        if est_ex is not None:
            situacoes_estado.append(est_ex)

    lado = _determinar_lado_fronteira(leitor, comp, v.verifica) if classe == "teste-de-fronteira" else None
    situacao = "estado não lido" if "estado não lido" in situacoes_estado else (
        situacoes_estado[0] if situacoes_estado else None
    )
    responsaveis = list(dict.fromkeys(m.responsavel for m in motivos))
    resp_str = ", ".join(responsaveis) if responsaveis else None

    return VerificacaoConsultada(
        arquivo=rel,
        componente=comp,
        classe=classe,
        alvo=v.verifica,
        exige=v.exige,
        incidentes=v.incidentes,
        momentos=momentos,
        quando_roda=quando_roda,
        lado_fronteira=lado,
        situacao_estado=situacao,
        para_retirada=bool(motivos),
        motivos_retirada=tuple(motivos),
        responsavel_retirada=resp_str,
    )


def _coletar_vinculos_com_componente(raiz: Path) -> list[VinculoArquivo]:
    vinculos: list[VinculoArquivo] = []
    for arq in descobrir_arquivos_teste(raiz):
        v = ler_vinculo(arq)
        if v.componente is not None:
            vinculos.append(v)
    return vinculos


def _componentes_da_stack(leitor: Any, chave_stack: str, slug_stack: str) -> set[str]:
    pertencentes: set[str] = set()
    prefixo_srv = f"{slug_stack}:"
    for ficha in leitor.ler_fichas("componente"):
        ch_comp = normalizar_componente(str(ficha.get("chave") or ""))
        if not ch_comp:
            continue
        ligs = ficha.get("ligacoes") or {}
        alvos = _como_lista_str(ligs.get("componente-de")) + _como_lista_str(ligs.get("stack"))
        for d in alvos:
            if d in (chave_stack, slug_stack) or d.startswith(prefixo_srv):
                pertencentes.add(ch_comp)
                break
    return pertencentes


def consultar_componente(
    componente: str,
    arvore: str | Path | None = None,
    *,
    leitor: Any = None,
) -> ResultadoConsultaComponente:
    """Consulta as verificações de um componente, seus momentos e se há alvo encerrado."""
    raiz = Path(arvore).resolve() if arvore is not None else _raiz_padrao()
    alvo_comp = normalizar_componente(componente) or componente
    olaria = _resolver_leitor(raiz, leitor)
    encerradas = _chaves_encerradas_por_desfecho(olaria)

    verificacoes = [
        _construir_verificacao(raiz, v, olaria, encerradas)
        for v in _coletar_vinculos_com_componente(raiz)
        if v.componente == alvo_comp
    ]
    return ResultadoConsultaComponente(
        componente=alvo_comp,
        verificacoes=tuple(verificacoes),
    )


def consultar_stack(
    stack: str,
    arvore: str | Path | None = None,
    *,
    leitor: Any = None,
) -> ResultadoConsultaStack:
    """Consulta as verificações dos componentes de uma stack e separa quem fornece e quem consome na fronteira."""
    raiz = Path(arvore).resolve() if arvore is not None else _raiz_padrao()
    chave_stack, slug_stack = _normalizar_stack(stack)
    olaria = _resolver_leitor(raiz, leitor)
    encerradas = _chaves_encerradas_por_desfecho(olaria)

    comps_stack = _componentes_da_stack(olaria, chave_stack, slug_stack)
    verificacoes = [
        _construir_verificacao(raiz, v, olaria, encerradas)
        for v in _coletar_vinculos_com_componente(raiz)
        if v.componente in comps_stack
    ]
    fornece = [
        v for v in verificacoes if v.classe == "teste-de-fronteira" and v.lado_fronteira == "fornece"
    ]
    consome = [
        v for v in verificacoes if v.classe == "teste-de-fronteira" and v.lado_fronteira == "consome"
    ]
    nao_decl = [
        v
        for v in verificacoes
        if v.classe == "teste-de-fronteira" and v.lado_fronteira not in ("fornece", "consome")
    ]
    comps_ordenados = sorted(comps_stack | {v.componente for v in verificacoes})
    return ResultadoConsultaStack(
        stack=chave_stack,
        componentes=tuple(comps_ordenados),
        verificacoes=tuple(verificacoes),
        fornece=tuple(fornece),
        consome=tuple(consome),
        lado_nao_declarado=tuple(nao_decl),
    )


def consultar_momento(
    momento: str,
    arvore: str | Path | None = None,
    *,
    leitor: Any = None,
) -> ResultadoConsultaMomento:
    """Consulta o que roda num momento (fita, push ou integracao)."""
    mom = _normalizar_momento(momento)
    if mom not in MOMENTOS_VALIDOS:
        raise ValueError(f"momento inválido '{momento}': escolha entre fita, push ou integracao")

    raiz = Path(arvore).resolve() if arvore is not None else _raiz_padrao()
    olaria = _resolver_leitor(raiz, leitor)
    encerradas = _chaves_encerradas_por_desfecho(olaria)

    todas = [
        _construir_verificacao(raiz, v, olaria, encerradas)
        for v in _coletar_vinculos_com_componente(raiz)
    ]

    if mom == "fita":
        selecionadas = [v for v in todas if "fita" in v.momentos]
        return ResultadoConsultaMomento(
            momento="fita",
            roda_testes=True,
            descricao="testes de comportamento do componente mexido (sem exige por padrão; com --ampliado inclui fronteira, regra e exige)",
            verificacoes=tuple(selecionadas),
        )
    if mom == "push":
        selecionadas = [v for v in todas if "push" in v.momentos]
        return ResultadoConsultaMomento(
            momento="push",
            roda_testes=True,
            descricao="comportamento alcançado, fronteira e regra quando componente ou alvo verifica muda, exige quando componente ou entidade muda e incidentes em todo push",
            verificacoes=tuple(selecionadas),
        )
    return ResultadoConsultaMomento(
        momento="integracao",
        roda_testes=False,
        descricao="a integração não roda teste: cobra o veredito do push sobre a ponta atual da main",
        verificacoes=tuple(todas),
    )


def consultar_soltos(arvore: str | Path | None = None) -> ResultadoConsultaSoltos:
    """Lista e conta os arquivos de teste descobertos na árvore que não têm componente no cabeçalho."""
    raiz = Path(arvore).resolve() if arvore is not None else _raiz_padrao()
    descobertos = descobrir_arquivos_teste(raiz)
    soltos: list[str] = []
    for arq in descobertos:
        v = ler_vinculo(arq)
        if v.componente is None:
            rel = arq.relative_to(raiz).as_posix() if arq.is_relative_to(raiz) else arq.name
            soltos.append(rel)
    total_desc = len(descobertos)
    total_soltos = len(soltos)
    return ResultadoConsultaSoltos(
        arvore=str(raiz),
        total_descobertos=total_desc,
        total_soltos=total_soltos,
        com_vinculo=total_desc - total_soltos,
        arquivos=tuple(soltos),
    )


def _extrair_flags_comuns(argv: list[str]) -> tuple[list[str], str | None, bool]:
    pos: list[str] = []
    arvore: str | None = None
    como_json = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            como_json = True
            i += 1
        elif arg == "--arvore":
            if i + 1 >= len(argv):
                raise ValueError("--arvore exige um caminho")
            arvore = argv[i + 1]
            i += 2
        elif arg.startswith("--arvore="):
            arvore = arg.split("=", 1)[1]
            i += 1
        else:
            pos.append(arg)
            i += 1
    return pos, arvore, como_json


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m suite consultar",
        description="Consulta o que cada teste protege, quando roda e quais alvos encerraram.",
    )
    p.add_argument("recorte", choices=("componente", "stack", "momento", "soltos"))
    p.add_argument("alvo", nargs="?", default=None)
    p.add_argument("--arvore", default=None, help="caminho da árvore do repositório (padrão: bancada)")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite o resultado em JSON")
    return p


def _executar_recorte(recorte: str, alvo: str | None, arvore: str | None) -> Any:
    if recorte == "soltos":
        return consultar_soltos(arvore or alvo)
    if not alvo:
        raise ValueError(f"consultar {recorte} exige a chave do {recorte}")
    if recorte == "componente":
        return consultar_componente(alvo, arvore=arvore)
    if recorte == "stack":
        return consultar_stack(alvo, arvore=arvore)
    if recorte == "momento":
        return consultar_momento(alvo, arvore=arvore)
    raise ValueError(f"recorte desconhecido: {recorte}")


def main(argv: list[str] | None = None) -> int:
    brutos = list(sys.argv[1:] if argv is None else argv)
    if not brutos or any(a in ("-h", "--help", "ajuda") for a in brutos):
        _parser().print_help(sys.stdout)
        return 0
    try:
        pos, arvore_flag, como_json = _extrair_flags_comuns(brutos)
        args = _parser().parse_args(
            [*pos, *(["--arvore", arvore_flag] if arvore_flag else []), *(["--json"] if como_json else [])]
        )
        res = _executar_recorte(args.recorte, args.alvo, args.arvore)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    except ValueError as exc:
        sys.stderr.write(f"suite consultar: {exc}\n")
        return 2
    except OlariaIndisponivelErro as exc:
        sys.stderr.write(f"suite consultar: NAO MEDIDO — {exc}\n")
        return 3

    if args.como_json:
        sys.stdout.write(json.dumps(res.como_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(res.resumo_texto() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
