# componente: componente:verbo-busca
"""Suíte de contrato de `busca consultar` e do leitor `casa_db` (`test_busca_consultar.py`).

Cobre os 24 códigos de saída da especificação, todos os pontos de «Como se confere» e a quarta
condição de «O que trava», em ambiente hermético com retrato falso que reproduz a semântica das
seis consultas de `lib/leitura/sql/` e de `casa.normalizar`.
"""
from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import io
import json
import re
import shlex
import sys
import textwrap
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BIN = RAIZ / "bin" / "busca"
ESQUEMA_ATUAL = RAIZ / "lib" / "busca" / "retorno.schema.json"
ESQUEMA_ANTERIOR = Path(__file__).resolve().parent / "fixtures" / "retorno.schema.v1.json"
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from busca.pedido import codificar_cursor
from leitura import casa_db, resolvedor
from leitura.recusa import CAMPOS, Recusa, Recusas, escrever_lista
from leitura.retrato import SQL, Retrato, _causa, literal

SAIDA_OK = 0
SAIDA_USO = 2
SAIDA_DEP = 3
SAIDA_NEGADO = 4
SAIDA_FALHA = 5
ORDEM_PADRAO = 2147483647
TOTAL_CODIGOS_TABELA = 24
TETO_CURTO_PAGINA = 1350

CODIGOS_DA_ESPECIFICACAO: dict[str, int] = {
    "termo-nao-casou": SAIDA_OK,
    "ato-desconhecido": SAIDA_USO,
    "termo-ausente": SAIDA_USO,
    "classe-ausente": SAIDA_USO,
    "termo-sem-letra": SAIDA_USO,
    "argumento-fora-do-modo": SAIDA_USO,
    "alvo-mal-formado": SAIDA_USO,
    "texto-longo-demais": SAIDA_USO,
    "passos-fora-da-faixa": SAIDA_USO,
    "continuacao-ilegivel": SAIDA_USO,
    "continuacao-divergente": SAIDA_USO,
    "classe-desconhecida": SAIDA_USO,
    "classe-ambigua": SAIDA_USO,
    "propriedade-desconhecida": SAIDA_USO,
    "valor-fora-do-dicionario": SAIDA_USO,
    "ligacao-desconhecida": SAIDA_USO,
    "alvo-inexistente": SAIDA_USO,
    "alvo-ambiguo": SAIDA_USO,
    "estado-desconhecido": SAIDA_USO,
    "banco-indisponivel": SAIDA_DEP,
    "conexoes-esgotadas": SAIDA_DEP,
    "acesso-negado": SAIDA_NEGADO,
    "prazo-estourado": SAIDA_FALHA,
    "falha-interna": SAIDA_FALHA,
}


def _carregar_bin():
    carregador = importlib.machinery.SourceFileLoader("busca_bin_consultar", str(BIN))
    spec = importlib.util.spec_from_loader("busca_bin_consultar", carregador)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    carregador.exec_module(mod)
    return mod


busca = _carregar_bin()


# ==================================================================== normalização fiel a casa.normalizar
def normalizar_casa(texto: str) -> str:
    """Reproduz `casa.normalizar`: NFD, tira U+0300..U+036F, minúscula ASCII e só [a-z0-9]."""
    decomp = unicodedata.normalize("NFD", texto)
    sem_marcas = "".join(ch for ch in decomp if not (0x0300 <= ord(ch) <= 0x036F))
    minusc = "".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in sem_marcas)
    return re.sub(r"[^a-z0-9]+", " ", minusc).strip()


# ==================================================================== validador de esquema sem dependência
_VALIDADORES_TIPO: dict[str, Callable[[Any], bool]] = {
    "null": lambda v: v is None,
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _validar_one_of(instancia: Any, ramos: Sequence[Mapping[str, Any]], caminho: str) -> None:
    acertos = 0
    for sub in ramos:
        try:
            validar_contra_esquema(instancia, sub, caminho)
            acertos += 1
        except AssertionError:
            continue
    assert acertos == 1, f"{caminho}: {instancia!r} casou com {acertos} ramos de oneOf"


def _validar_objeto(instancia: dict[str, Any], esquema: Mapping[str, Any], caminho: str) -> None:
    obrigatorios = set(esquema.get("required") or ())
    faltando = obrigatorios - set(instancia)
    assert not faltando, f"{caminho}: campos obrigatórios ausentes: {sorted(faltando)}"
    props = esquema.get("properties") or {}
    if esquema.get("additionalProperties") is False:
        extras = set(instancia) - set(props)
        assert not extras, f"{caminho}: propriedades extras proibidas: {sorted(extras)}"
    for ch, val in instancia.items():
        if ch in props:
            validar_contra_esquema(val, props[ch], f"{caminho}.{ch}")


def validar_contra_esquema(instancia: Any, esquema: Mapping[str, Any], caminho: str = "$") -> None:
    """Valida recursivamente `instancia` contra um JSON Schema 2020-12 estruturado."""
    if "const" in esquema:
        assert instancia == esquema["const"], f"{caminho}: esperado const {esquema['const']!r}, veio {instancia!r}"
    if "enum" in esquema:
        assert instancia in esquema["enum"], f"{caminho}: {instancia!r} fora de enum {esquema['enum']!r}"
    if "oneOf" in esquema:
        _validar_one_of(instancia, esquema["oneOf"], caminho)
        return

    tipos = esquema.get("type")
    if tipos is not None:
        lista_tipos = [tipos] if isinstance(tipos, str) else list(tipos)
        assert any(_VALIDADORES_TIPO[t](instancia) for t in lista_tipos), (
            f"{caminho}: {instancia!r} não é de tipo {lista_tipos}"
        )
    if _VALIDADORES_TIPO["integer"](instancia) and "minimum" in esquema:
        assert instancia >= int(esquema["minimum"]), f"{caminho}: {instancia} < {esquema['minimum']}"
    if isinstance(instancia, list) and "items" in esquema:
        for i, item in enumerate(instancia):
            validar_contra_esquema(item, esquema["items"], f"{caminho}[{i}]")
    if isinstance(instancia, dict):
        _validar_objeto(instancia, esquema, caminho)


def _tipos_do_no(no: Mapping[str, Any]) -> set[str]:
    t = no.get("type")
    if isinstance(t, str):
        return {t}
    if isinstance(t, list):
        return set(t)
    if "oneOf" in no:
        uniao: set[str] = set()
        for sub in no["oneOf"]:
            uniao |= _tipos_do_no(sub)
        return uniao
    if "const" in no:
        return {f"const:{no['const']}"}
    return set()


def conferir_compatibilidade_esquema(anterior: Mapping[str, Any], novo: Mapping[str, Any]) -> list[str]:
    """Aponta quebras proibidas na mesma versão do esquema (remoção ou mudança de tipo/enum)."""
    v_ant = anterior.get("properties", {}).get("versao", {}).get("const")
    v_nov = novo.get("properties", {}).get("versao", {}).get("const")
    if v_ant != v_nov:
        return []

    quebras: list[str] = []
    props_ant = anterior.get("properties") or {}
    props_nov = novo.get("properties") or {}
    for campo, def_ant in props_ant.items():
        if campo not in props_nov:
            quebras.append(f"campo removido sem subir versão: {campo}")
            continue
        def_nov = props_nov[campo]
        if not _tipos_do_no(def_ant).issubset(_tipos_do_no(def_nov)):
            quebras.append(f"tipo estreitado em {campo}")
        if "enum" in def_ant and not set(def_ant["enum"]).issubset(set(def_nov.get("enum") or ())):
            quebras.append(f"enum estreitado em {campo}")
    return quebras


# ==================================================================== retrato falso completo do fichário
FORNADA_BASE = "019a0000-0000-7000-8000-000000000010"
FORNADA_NOVA = "019a0000-0000-7000-8000-000000000099"


@dataclass
class LinhaNomeFalsa:
    termo: str
    chave: str
    terminou: str | None = None


@dataclass
class LigacaoFalsa:
    de_uuid: str
    prop_id: str
    prop_slug: str
    para_uuid: str
    posicao: int | None = None
    terminou: str | None = None


@dataclass
class RetratoFalsoConsultar:
    """Banco `casa` em memória para exercitar todos os estágios do consultar."""

    fornada: str = FORNADA_BASE
    incluir_plural_gabaritos: bool = True
    classes: dict[str, dict[str, Any]] = field(default_factory=dict)
    dicionarios: dict[str, dict[str, Any]] = field(default_factory=dict)
    fichas: dict[str, dict[str, Any]] = field(default_factory=dict)
    nomes: list[LinhaNomeFalsa] = field(default_factory=list)
    catalogo: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    dados: list[dict[str, Any]] = field(default_factory=list)
    ligacoes: list[LigacaoFalsa] = field(default_factory=list)
    transicoes: list[tuple[str, str, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.classes:
            self._popular_padrao()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def _popular_padrao(self) -> None:
        self.classes = {
            "shape": {
                "uuid": "c-shape", "slug": "shape", "rotulo": "Classe", "definicao": "Molde de ficha.",
                "capacidade": "f-cap-ont", "mae": None, "raiz": "c-shape", "rigidez": "rigido",
                "modulo": "casa", "estrato": "formal", "categoria": "conteudo", "inicio": "2026-01",
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
            "dicionario": {
                "uuid": "c-dic", "slug": "dicionario", "rotulo": "Dicionário", "definicao": "Vocabulário fechado.",
                "capacidade": "f-cap-ont", "mae": None, "raiz": "c-dic", "rigidez": "rigido",
                "modulo": "casa", "estrato": "formal", "categoria": "conteudo", "inicio": None,
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
            "capacidade": {
                "uuid": "c-cap", "slug": "capacidade", "rotulo": "Capacidade", "definicao": "Capacidade de negócio.",
                "capacidade": "f-cap-ges", "mae": None, "raiz": "c-cap", "rigidez": "rigido",
                "modulo": "casa", "estrato": "formal", "categoria": "disposicao", "inicio": None,
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
            "regra": {
                "uuid": "c-regra", "slug": "regra", "rotulo": "Regra", "definicao": "Regra mãe.",
                "capacidade": "f-cap-ont", "mae": None, "raiz": "c-regra", "rigidez": "rigido",
                "modulo": "casa", "estrato": "norma", "categoria": "conteudo", "inicio": None,
                "variantes": [], "relacao_com_mae": None, "instanciavel": False, "fechada": True,
            },
            "gabarito": {
                "uuid": "c-gab", "slug": "gabarito", "rotulo": "Gabarito", "definicao": "Régua de conferência.",
                "capacidade": "f-cap-ont", "mae": "c-regra", "raiz": "c-regra", "rigidez": "rigido",
                "modulo": "casa", "estrato": "norma", "categoria": "conteudo", "inicio": None,
                "variantes": [], "relacao_com_mae": "generica", "instanciavel": True, "fechada": True,
            },
            "politica": {
                "uuid": "c-pol", "slug": "politica", "rotulo": "Política", "definicao": "Ato normativo interno.",
                "capacidade": "f-cap-ont", "mae": "c-regra", "raiz": "c-regra", "rigidez": "rigido",
                "modulo": "casa", "estrato": "norma", "categoria": "conteudo", "inicio": None,
                "variantes": ["norma interna"], "relacao_com_mae": "generica", "instanciavel": True, "fechada": True,
            },
            "exploracao": {
                "uuid": "c-exp", "slug": "exploracao", "rotulo": "Exploração", "definicao": "Processo de busca.",
                "capacidade": "f-cap-busca", "mae": None, "raiz": "c-exp", "rigidez": "anti-rigido",
                "modulo": "casa", "estrato": "processo", "categoria": "acontecimento", "inicio": "2026-10",
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
            "verbo": {
                "uuid": "c-verbo", "slug": "verbo", "rotulo": "Verbo", "definicao": "Comando de capacidade.",
                "capacidade": "f-cap-dev", "mae": None, "raiz": "c-verbo", "rigidez": "rigido",
                "modulo": "casa", "estrato": "construcao", "categoria": "coisa", "inicio": None,
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
            "persona": {
                "uuid": "c-persona", "slug": "persona", "rotulo": "Persona", "definicao": "Cadeira da casa.",
                "capacidade": "f-cap-ges", "mae": None, "raiz": "c-persona", "rigidez": "rigido",
                "modulo": "casa", "estrato": "formal", "categoria": "papel", "inicio": None,
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
            "segredo": {
                "uuid": "c-seg", "slug": "segredo", "rotulo": "Segredo", "definicao": "Credencial guardada.",
                "capacidade": "f-cap-dev", "mae": None, "raiz": "c-seg", "rigidez": "rigido",
                "modulo": "casa", "estrato": "construcao", "categoria": "coisa", "inicio": None,
                "variantes": [], "relacao_com_mae": None, "instanciavel": True, "fechada": True,
            },
        }

        self.dicionarios = {
            "rigidez": {
                "uuid": "d-rig", "slug": "rigidez", "rotulo": "Rigidez", "definicao": "Rigidez ontológica.",
                "capacidade": "f-cap-ont", "modulo": "casa", "estrato": "formal", "disjuntas": True,
                "do_framework": True, "resumo": "Rígido ou anti-rígido",
                "valores": [{"slug": "rigido", "rotulo": "rígido"}, {"slug": "anti-rigido", "rotulo": "anti-rígido"}],
            },
            "modulo": {
                "uuid": "d-mod", "slug": "modulo", "rotulo": "Módulo", "definicao": "Módulo da casa.",
                "capacidade": "f-cap-ont", "modulo": "casa", "estrato": "formal", "disjuntas": True,
                "do_framework": True, "resumo": None,
                "valores": [{"slug": "casa", "rotulo": "casa"}, {"slug": "biblioteca", "rotulo": "biblioteca"}],
            },
            "estrato": {
                "uuid": "d-est", "slug": "estrato", "rotulo": "Estrato", "definicao": "Estrato da casa.",
                "capacidade": "f-cap-ont", "modulo": "casa", "estrato": "formal", "disjuntas": True,
                "do_framework": True, "resumo": None,
                "valores": [
                    {"slug": "formal", "rotulo": "formal"},
                    {"slug": "norma", "rotulo": "norma"},
                    {"slug": "processo", "rotulo": "processo"},
                    {"slug": "construcao", "rotulo": "construção"},
                ],
            },
            "categoria": {
                "uuid": "d-cat", "slug": "categoria", "rotulo": "Categoria", "definicao": "Categoria raiz.",
                "capacidade": "f-cap-ont", "modulo": "casa", "estrato": "formal", "disjuntas": True,
                "do_framework": True, "resumo": None,
                "valores": [
                    {"slug": "coisa", "rotulo": "coisa"},
                    {"slug": "conteudo", "rotulo": "conteúdo"},
                    {"slug": "disposicao", "rotulo": "disposição"},
                    {"slug": "acontecimento", "rotulo": "acontecimento"},
                    {"slug": "papel", "rotulo": "papel"},
                ],
            },
            "esfera": {
                "uuid": "d-esf", "slug": "esfera", "rotulo": "Esfera", "definicao": "Esfera do verbo.",
                "capacidade": "f-cap-ont", "modulo": "casa", "estrato": "formal", "disjuntas": True,
                "do_framework": False, "resumo": "Negócio ou plataforma",
                "valores": [{"slug": "negocio", "rotulo": "negócio"}, {"slug": "plataforma", "rotulo": "plataforma"}],
            },
        }

        for slug, sh in self.classes.items():
            self.fichas[slug] = {
                "uuid": sh["uuid"], "chave": slug, "classe": "shape", "classe_uuid": "c-shape",
                "rotulo": sh["rotulo"], "definicao": sh["definicao"],
            }
        for slug, dc in self.dicionarios.items():
            ch = f"dicionario:{slug}"
            self.fichas[ch] = {
                "uuid": dc["uuid"], "chave": ch, "classe": "dicionario", "classe_uuid": "c-dic",
                "rotulo": dc["rotulo"], "definicao": dc["definicao"],
            }

        instancias = [
            ("f-cap-busca", "capacidade:busca", "capacidade", "c-cap", "Busca", "Achar e ler na casa."),
            ("f-cap-ont", "capacidade:ontologia", "capacidade", "c-cap", "Ontologia", "Modelos formais."),
            ("f-cap-dev", "capacidade:dev", "capacidade", "c-cap", "Desenvolvimento", "Construção de código."),
            ("f-cap-ges", "capacidade:gestao-estrategica", "capacidade", "c-cap", "Gestão estratégica", "Direção."),
            ("f-per-ges", "gestao-estrategica", "persona", "c-persona", "Gestão", "Cadeira de gestão."),
            ("f-verbo-busca", "verbo:busca", "verbo", "c-verbo", "Verbo busca", "Comando busca."),
            ("f-verbo-ont", "verbo:ontologia", "verbo", "c-verbo", "Verbo ontologia", "Comando ontologia."),
            ("f-gab-fw", "gabarito:framework-da-ontologia", "gabarito", "c-gab", "Framework da ontologia", "Régua."),
            ("f-gab-comp", "gabarito:comportamento", "gabarito", "c-gab", "Comportamento", "Régua de comportamento."),
            ("f-gab-acoes", "gabarito:acoes-padrao", "gabarito", "c-gab", "Ações padrão", "Régua de ações."),
            ("f-pol-1", "politica:0001-acesso", "politica", "c-pol", "Política de acesso", "Norma 1."),
            ("f-pol-2", "politica:0002-rascunho", "politica", "c-pol", "Política em minuta", "Norma 2."),
            ("f-pol-3", "politica:0003-sem-evento", "politica", "c-pol", "Política sem transição", "Norma 3."),
            ("f-seg-1", "segredo:chave-cofre", "segredo", "c-seg", "Chave cofre", "Segredo."),
        ]
        for uid, ch, cls, cls_uid, rot, defin in instancias:
            self.fichas[ch] = {
                "uuid": uid, "chave": ch, "classe": cls, "classe_uuid": cls_uid,
                "rotulo": rot, "definicao": defin,
            }

        self.nomes = [
            LinhaNomeFalsa("classe", "shape"),
            LinhaNomeFalsa("modelos formais", "capacidade:ontologia"),
            LinhaNomeFalsa("modelo formal", "capacidade:ontologia"),
            LinhaNomeFalsa("desenvolvimento", "capacidade:dev"),
            LinhaNomeFalsa("apelido-encerrado", "capacidade:busca", terminou=FORNADA_BASE),
            LinhaNomeFalsa("classe-dupla", "gabarito"),
            LinhaNomeFalsa("classe-dupla", "politica"),
            LinhaNomeFalsa("misto-aut", "gabarito:framework-da-ontologia"),
            LinhaNomeFalsa("misto-aut", "segredo:chave-cofre"),
        ]
        if self.incluir_plural_gabaritos:
            self.nomes.append(LinhaNomeFalsa("gabaritos", "gabarito"))

        self.catalogo = {
            "c-gab": [
                {"classe": "gabarito", "propriedade": "confere", "propriedade_id": "p-confere",
                 "restricao": "r-gab-conf", "tipo_de_valor": "ligacao", "sentido": "saida",
                 "dicionario": None, "valores": None, "estados": None},
                {"classe": "gabarito", "propriedade": "usa", "propriedade_id": "p-usa",
                 "restricao": "r-gab-usa", "tipo_de_valor": "ligacao", "sentido": "saida",
                 "dicionario": None, "valores": None, "estados": None},
                {"classe": "gabarito", "propriedade": "dependente", "propriedade_id": "p-usa",
                 "restricao": "r-gab-cheg", "tipo_de_valor": "ligacao", "sentido": "chegada",
                 "dicionario": None, "valores": None, "estados": None},
            ],
            "c-cap": [
                {"classe": "capacidade", "propriedade": "confere", "propriedade_id": "p-confere",
                 "restricao": "r-cap-conf-in", "tipo_de_valor": "ligacao", "sentido": "chegada",
                 "dicionario": None, "valores": None, "estados": None},
            ],
            "c-verbo": [
                {"classe": "verbo", "propriedade": "prazo-de-espera", "propriedade_id": "p-prazo",
                 "restricao": "r-verbo-prazo", "tipo_de_valor": "texto", "sentido": "saida",
                 "dicionario": None, "valores": None, "estados": None},
                {"classe": "verbo", "propriedade": "esfera", "propriedade_id": "p-esfera",
                 "restricao": "r-verbo-esfera", "tipo_de_valor": "dicionario", "sentido": "saida",
                 "dicionario": "d-esf", "valores": self.dicionarios["esfera"]["valores"], "estados": None},
            ],
            "c-pol": [
                {"classe": "politica", "propriedade": "normatiza", "propriedade_id": "p-norm",
                 "restricao": "r-pol-norm", "tipo_de_valor": "ligacao", "sentido": "saida",
                 "dicionario": None, "valores": None, "estados": ["minuta", "vigente", "revogada"]},
            ],
        }

        self.dados = [
            {"ficha": "f-verbo-busca", "restricao": "r-verbo-prazo", "valor": "10s", "valor_dic": None},
            {"ficha": "f-verbo-busca", "restricao": "r-verbo-esfera", "valor": "plataforma", "valor_dic": "plataforma"},
            {"ficha": "f-verbo-ont", "restricao": "r-verbo-prazo", "valor": "45s", "valor_dic": None},
        ]

        self.ligacoes = [
            LigacaoFalsa("f-gab-fw", "p-confere", "confere", "f-cap-ont", posicao=1),
            LigacaoFalsa("f-gab-comp", "p-confere", "confere", "f-cap-dev", posicao=2),
            LigacaoFalsa("f-gab-comp", "p-usa", "usa", "f-gab-fw", posicao=1),
            LigacaoFalsa("f-pol-1", "p-norm", "normatiza", "f-cap-busca", posicao=1),
        ]

        self.transicoes = [
            ("f-pol-1", "minuta", 1),
            ("f-pol-1", "vigente", 2),
            ("f-pol-2", "minuta", 1),
        ]

    # ---------------------------------------------------------------- métodos chamados pelo leitor
    def _pares_brutos_do_termo(self, norm: str) -> list[tuple[int, str]]:
        pares = [
            (1, self.fichas[ln.chave]["uuid"])
            for ln in self.nomes
            if ln.terminou is None and normalizar_casa(ln.termo) == norm and ln.chave in self.fichas
        ]
        for sh in self.classes.values():
            if normalizar_casa(sh["rotulo"]) == norm:
                pares.append((2, sh["uuid"]))
            pares.extend((3, sh["uuid"]) for v in sh["variantes"] if normalizar_casa(v) == norm)
        for f in self.fichas.values():
            slug_f = f["chave"].split(":", 1)[1] if ":" in f["chave"] else f["chave"]
            if normalizar_casa(slug_f) == norm:
                pares.append((4, f["uuid"]))
            if f["classe"] != "shape" and normalizar_casa(f.get("rotulo") or "") == norm:
                pares.append((2, f["uuid"]))
        return pares

    def _candidatas_do_termo(self, norm: str) -> dict[str, int]:
        melhor_passo: dict[str, int] = {}
        for passo, uid in self._pares_brutos_do_termo(norm):
            if uid not in melhor_passo or passo < melhor_passo[uid]:
                melhor_passo[uid] = passo
        return melhor_passo

    def resolver_nomes(self, termos: Sequence[str]) -> list[dict]:
        linhas_out: list[dict] = []
        por_uuid = {f["uuid"]: f for f in self.fichas.values()}

        for ord_n, cru in enumerate(termos, start=1):
            norm = normalizar_casa(cru)
            melhor_passo = self._candidatas_do_termo(norm) if norm else {}
            if not melhor_passo:
                linhas_out.append({
                    "ord": ord_n, "norm": norm, "passo": None, "chave": None,
                    "classe": None, "e_classe": None, "rotulo": None, "definicao": None,
                })
                continue
            ordenadas = sorted(melhor_passo.items(), key=lambda kv: (kv[1], por_uuid[kv[0]]["chave"]))
            for uid, passo in ordenadas:
                f = por_uuid[uid]
                linhas_out.append({
                    "ord": ord_n, "norm": norm, "passo": passo, "chave": f["chave"],
                    "classe": f["classe"], "e_classe": f["classe"] == "shape",
                    "rotulo": f.get("rotulo"), "definicao": f.get("definicao"),
                })
        return linhas_out

    def _despachar_sql_identidade(self, sql: str, params: Sequence[Any]) -> list[dict] | None:
        if sql is resolvedor.SQL_FICHA:
            f = self.fichas.get(str(params[0]))
            return [{"uuid": f["uuid"], "chave": f["chave"], "classe": f["classe"], "classe_uuid": f["classe_uuid"]}] if f else []
        if sql in (resolvedor.SQL_FICHA_INTEIRA, resolvedor.SQL_FICHA_SEM_LIGACOES):
            return self._sql_ficha_inteira(str(params[0]), com_ligacoes=(sql is resolvedor.SQL_FICHA_INTEIRA))
        if sql is casa_db.SQL_UUID_DA_CLASSE:
            sh = self.classes.get(str(params[0]))
            return [{"uuid": sh["uuid"], "classe": sh["slug"]}] if sh else []
        if sql is casa_db.SQL_CLASSES_DISPONIVEIS:
            return [{"classe": s} for s in sorted(self.classes)]
        if sql is casa_db.SQL_FILHAS_DA_CLASSE:
            return self._sql_filhas(str(params[0]))
        if sql is casa_db.SQL_VALORES_DO_DICIONARIO:
            dc = self.dicionarios.get(str(params[0]))
            return list(dc["valores"]) if dc else []
        return None

    def consultar(self, sql: str, *params: Any) -> list[dict]:
        direto = self._despachar_sql_identidade(sql, params)
        if direto is not None:
            return direto
        if "catalogo_da_classe" in sql:
            return [ln for cu in sorted(set(params[0])) for ln in self.catalogo.get(cu, [])]
        if "alcance_nivel" in sql:
            return self._sql_alcance_nivel(list(params[0]), params[1], str(params[2]))
        if "rastro" in sql:
            por_u = {f["uuid"]: f["chave"] for f in self.fichas.values()}
            return [{"uuid": u, "chave_humana": por_u[u]} for u in params[0] if u in por_u]
        if "valores_da_propriedade" in sql:
            return self._sql_valores_da_propriedade(str(params[0]), list(params[1]), params[2], set(params[3]))
        if "consultar_fichas" in sql:
            return self._sql_consultar_fichas(*params)
        raise AssertionError(f"SQL não mapeado no retrato falso: {sql[:80]}")

    def _sql_ficha_inteira(self, uid: str, *, com_ligacoes: bool) -> list[dict]:
        por_u = {f["uuid"]: f for f in self.fichas.values()}
        f = por_u.get(uid)
        if not f:
            return []
        corpo: dict[str, Any] = {"chave": f["chave"], "classe": f["classe"], "dados": {}}
        if com_ligacoes:
            saida: dict[str, list[str]] = {}
            chegada: dict[str, list[str]] = {}
            for g in self.ligacoes:
                if g.terminou is not None:
                    continue
                if g.de_uuid == uid:
                    saida.setdefault(g.prop_slug, []).append(por_u[g.para_uuid]["chave"])
                if g.para_uuid == uid:
                    chegada.setdefault(g.prop_slug, []).append(por_u[g.de_uuid]["chave"])
            corpo["ligacoes"] = {"saida": saida, "chegada": chegada}
        return [{"ficha": corpo}]

    def _sql_filhas(self, ancestral_uuid: str) -> list[dict]:
        res = [sh for sh in self.classes.values() if sh["uuid"] == ancestral_uuid]
        mudou = True
        vistos = {ancestral_uuid}
        while mudou:
            mudou = False
            for sh in self.classes.values():
                if sh["uuid"] not in vistos and sh.get("mae") in vistos and sh.get("relacao_com_mae") in ("generica", "restritiva"):
                    vistos.add(sh["uuid"])
                    res.append(sh)
                    mudou = True
        return [{"uuid": sh["uuid"], "classe": sh["slug"]} for sh in sorted(res, key=lambda x: x["slug"])]

    def _sql_alcance_nivel(self, fronteira: list[str], prop_id: str | None, sentido: str) -> list[dict]:
        por_u = {f["uuid"]: f for f in self.fichas.values()}
        front = set(fronteira)
        brutas: list[tuple[str, str, str, int | None]] = []
        for g in self.ligacoes:
            if g.terminou is not None or (prop_id and g.prop_id != prop_id):
                continue
            if sentido in ("saida", "qualquer") and g.para_uuid in front:
                brutas.append((g.de_uuid, g.para_uuid, g.prop_slug, g.posicao))
            if sentido in ("chegada", "qualquer") and g.de_uuid in front:
                brutas.append((g.para_uuid, g.de_uuid, g.prop_slug, g.posicao))
        brutas.sort(key=lambda t: (t[0], por_u[t[1]]["chave"], t[2], ORDEM_PADRAO if t[3] is None else t[3]))
        vistas: set[str] = set()
        out: list[dict] = []
        for ficha_u, pai_u, p_slug, pos in brutas:
            if ficha_u not in vistas:
                vistas.add(ficha_u)
                out.append({"ficha": ficha_u, "pai": pai_u, "propriedade": p_slug, "posicao": pos})
        return out

    def _estado_vigente(self, ficha_uid: str) -> str | None:
        evs = [(est, seq) for fu, est, seq in self.transicoes if fu == ficha_uid]
        return max(evs, key=lambda t: t[1])[0] if evs else None

    def _casa_prop_objeto(self, obj: Mapping[str, Any], pred: Mapping[str, Any]) -> bool:
        col = str(pred["coluna"])
        val_col = obj.get(col)
        if pred["valor"] is None and pred["alvo"] is None:
            return val_col not in (None, [], "")
        if pred["alvo"] is not None and str(val_col or "") == str(pred["alvo"]):
            return True
        if pred["valor"] is None:
            return False
        return (pred["valor"] in val_col) if isinstance(val_col, list) else (val_col == pred["valor"])

    def _ficha_cumpre_prop(self, f: Mapping[str, Any], pred: Mapping[str, Any]) -> bool:
        fonte = pred["fonte"]
        tem = False
        if fonte == "dado":
            restrs = set(pred["restricoes"])
            for d in self.dados:
                if d["ficha"] != f["uuid"] or d["restricao"] not in restrs:
                    continue
                if pred["valor"] is None or d.get("valor_dic") == pred["valor"] or d.get("valor") == pred["valor"]:
                    tem = True
                    break
        elif fonte == "shape":
            sh = next((s for s in self.classes.values() if s["uuid"] == f["uuid"]), None)
            tem = sh is not None and self._casa_prop_objeto(sh, pred)
        elif fonte == "dicionario":
            dc = next((c for c in self.dicionarios.values() if c["uuid"] == f["uuid"]), None)
            tem = dc is not None and self._casa_prop_objeto(dc, pred)
        return (not tem) if pred.get("sem") else tem

    def _sql_consultar_fichas(self, *params: Any) -> list[dict]:
        classes_uuids = set(params[0])
        preds_prop = json.loads(params[1])
        alcance_lista = json.loads(params[2])
        num_ligs = int(params[3])
        estado_ped = params[4] or None
        cur_ord = int(params[5]) if params[5] not in (None, "") else None
        cur_chv = params[6] or None
        limite = int(params[7])
        faltas_lig = json.loads(params[9])

        universo = sorted([f["chave"] for f in self.fichas.values() if f["classe_uuid"] in classes_uuids])
        digest = "v1:" + hashlib.sha256(json.dumps(universo, ensure_ascii=False).encode("utf-8")).hexdigest()

        alcance_por_n: dict[int, dict[str, int | None]] = {}
        for a in alcance_lista:
            alcance_por_n.setdefault(int(a["n"]), {})[str(a["ficha"])] = a["posicao"]

        casadas: list[dict[str, Any]] = []
        for f in self.fichas.values():
            if f["classe_uuid"] not in classes_uuids:
                continue
            if not all(self._ficha_cumpre_prop(f, p) for p in preds_prop):
                continue
            if not all(f["uuid"] in alcance_por_n.get(n, {}) for n in range(1, num_ligs + 1)):
                continue
            if self._tem_falta_ligacao_presente(f["uuid"], faltas_lig):
                continue
            est = self._estado_vigente(f["uuid"])
            if estado_ped is not None and est != estado_ped:
                continue
            pos1 = alcance_por_n.get(1, {}).get(f["uuid"])
            ordem = int(pos1) if pos1 is not None else ORDEM_PADRAO
            casadas.append({**f, "ordem": ordem, "estado": est})

        casadas.sort(key=lambda x: (x["ordem"], x["chave"]))
        total = len(casadas)
        antes = (
            sum(1 for k in casadas if (k["ordem"], k["chave"]) <= (cur_ord, cur_chv))
            if cur_chv is not None and cur_ord is not None
            else 0
        )
        depois = (
            [k for k in casadas if (k["ordem"], k["chave"]) > (cur_ord, cur_chv)]
            if cur_chv is not None and cur_ord is not None
            else casadas
        )[:limite]

        if not depois:
            return [{
                "total": total, "antes": antes, "digest": digest, "fornada": self.fornada,
                "uuid": None, "ordem": None, "chave": None, "classe": None, "rotulo": None, "estado": None,
            }]
        return [
            {
                "total": total, "antes": antes, "digest": digest, "fornada": self.fornada,
                "uuid": it["uuid"], "ordem": it["ordem"], "chave": it["chave"],
                "classe": it["classe"], "rotulo": it.get("rotulo"), "estado": it.get("estado"),
            }
            for it in depois
        ]

    def _tem_falta_ligacao_presente(self, ficha_uid: str, faltas_lig: Sequence[Mapping[str, Any]]) -> bool:
        for fl in faltas_lig:
            p_id, sent, alvo = fl["propriedade"], fl["sentido"], fl.get("alvo")
            for g in self.ligacoes:
                if g.terminou is not None or g.prop_id != p_id:
                    continue
                if sent == "saida" and g.de_uuid == ficha_uid and (alvo is None or g.para_uuid == alvo):
                    return True
                if sent == "chegada" and g.para_uuid == ficha_uid and (alvo is None or g.de_uuid == alvo):
                    return True
        return False

    def _sql_valores_da_propriedade(
        self, fonte: str, restricoes: list[str], coluna: str | None, classes_uuids: set[str],
    ) -> list[dict]:
        por_u = {f["uuid"]: f["chave"] for f in self.fichas.values()}
        contagem: dict[str, int] = {}
        if fonte == "dado":
            rset = set(restricoes)
            for d in self.dados:
                if d["restricao"] in rset:
                    v = str(d.get("valor_dic") or d.get("valor"))
                    contagem[v] = contagem.get(v, 0) + 1
        elif fonte in ("shape", "dicionario") and coluna:
            objs = self.classes.values() if fonte == "shape" else self.dicionarios.values()
            for o in objs:
                f = next((x for x in self.fichas.values() if x["uuid"] == o["uuid"]), None)
                if f is None or f["classe_uuid"] not in classes_uuids:
                    continue
                bruto = o.get(coluna)
                if bruto is not None:
                    val_txt = por_u.get(str(bruto), str(bruto))
                    contagem[val_txt] = contagem.get(val_txt, 0) + 1
        return [{"valor": k, "fichas": contagem[k]} for k in sorted(contagem)]


# ==================================================================== fixtures e executores auxiliares
@pytest.fixture(autouse=True)
def _versao_yaml_padrao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "versao-da-classe.yaml"
    cfg.write_text(
        "versao: 1\n"
        "fontes: [fornada-da-classe, iniciou-do-dado-vigente, iniciou-da-ligacao-vigente, evento-que-cita-a-classe]\n"
        "casos:\n"
        "  shape: [fornada-de-toda-classe]\n"
        "  dicionario: [fornada-de-todo-dicionario, fornada-de-todo-valor]\n"
        "eventos:\n"
        "  - modelos-formais.operacao-em-lote.olaria:olaria\n"
        "  - modelos-formais.pontual.olaria:olaria\n"
        "mais_recente: [ocorrido_em desc, uuid desc]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PF_VERSAO_CLASSE_YAML", str(cfg))
    return cfg


def rodar_consultar(
    args: Sequence[str],
    *,
    retrato: Any = None,
    autorizador: Callable[[str, str | None], bool] | None = None,
    ato: str = "consultar",
    **extras: Any,
) -> tuple[int, str, str]:
    banco = RetratoFalsoConsultar() if retrato is None else retrato
    fabrica = banco if callable(banco) else (lambda: banco)
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(
        [ato, *args],
        saida=out,
        erro=err,
        abrir_retrato=fabrica,
        autorizador=autorizador,
        **extras,
    )
    return rc, out.getvalue(), err.getvalue()


def _validar_recusa_stderr(
    err_txt: str,
    codigo_esperado: str,
    chamada_recebida: Sequence[str],
) -> dict[str, Any]:
    linhas = [ln for ln in err_txt.splitlines() if ln.strip()]
    assert linhas, "stderr vazio numa recusa"
    pacote = json.loads(linhas[-1])
    assert set(pacote) == {"erro", "erros"}
    assert isinstance(pacote["erros"], list) and pacote["erros"]
    assert pacote["erro"] == pacote["erros"][0]
    codigos = [item["codigo"] for item in pacote["erros"]]
    assert codigo_esperado in codigos, f"esperado {codigo_esperado}, vieram {codigos}"
    texto_chamada = f"busca {shlex.join(chamada_recebida)}"
    for item in pacote["erros"]:
        assert list(item) == list(CAMPOS)
        assert item["proximo"] != texto_chamada
    return pacote


def _falhar_banco_indisponivel():
    raise _causa("psql: error: connection to server failed: Connection refused")


def _falhar_conexoes_esgotadas():
    raise _causa('FATAL:  too many connections for role "analise_leitura"')


def _falhar_prazo_estourado():
    raise _causa("ERROR:  canceling statement due to statement timeout")


def _falhar_interna():
    raise RuntimeError("detalhe interno sensivel do processo")


def _negar_segredo(cls: str, _suj: str | None) -> bool:
    return cls != "segredo"


# ==================================================================== 1. tabela completa dos 24 códigos de saída
@dataclass(frozen=True)
class CasoRecusaTabela:
    codigo: str
    saida: int
    args: list[str]
    ato: str = "consultar"
    retrato_fn: Any = None
    aut_fn: Any = None


CASOS_RECUSA_TABELA: list[CasoRecusaTabela] = [
    CasoRecusaTabela("ato-desconhecido", SAIDA_USO, ["x"], ato="inexistente"),
    CasoRecusaTabela("termo-ausente", SAIDA_USO, []),
    CasoRecusaTabela("classe-ausente", SAIDA_USO, ["--prop", "esfera=negocio"]),
    CasoRecusaTabela("termo-sem-letra", SAIDA_USO, ["---"]),
    CasoRecusaTabela("argumento-fora-do-modo", SAIDA_USO, ["gabarito", "--classe", "shape"]),
    CasoRecusaTabela("alvo-mal-formado", SAIDA_USO, ["--classe", "gabarito", "--ligacao", "confere=---"]),
    CasoRecusaTabela("texto-longo-demais", SAIDA_USO, ["a" * 201]),
    CasoRecusaTabela("passos-fora-da-faixa", SAIDA_USO, ["--classe", "gabarito", "--ligacao", "confere/9=capacidade:ontologia"]),
    CasoRecusaTabela("continuacao-ilegivel", SAIDA_USO, ["--classe", "gabarito", "--cursor", "nao-decodifica$$$"]),
    CasoRecusaTabela(
        "continuacao-divergente",
        SAIDA_USO,
        ["--classe", "gabarito", "--prop", "inexistente=1", "--cursor", codificar_cursor(ordem=1, chave="gabarito:a", fornada=FORNADA_BASE, resumo="0" * 64)],
    ),
    CasoRecusaTabela("classe-desconhecida", SAIDA_USO, ["--classe", "classe-que-nao-existe"]),
    CasoRecusaTabela("classe-ambigua", SAIDA_USO, ["--classe", "classe-dupla"]),
    CasoRecusaTabela("propriedade-desconhecida", SAIDA_USO, ["--classe", "gabarito", "--prop", "propriedade-que-nao-existe=x"]),
    CasoRecusaTabela("valor-fora-do-dicionario", SAIDA_USO, ["--classe", "verbo", "--prop", "esfera=fora-do-dic"]),
    CasoRecusaTabela("ligacao-desconhecida", SAIDA_USO, ["--classe", "gabarito", "--ligacao", "nao-declara=capacidade:ontologia"]),
    CasoRecusaTabela("alvo-inexistente", SAIDA_USO, ["--classe", "gabarito", "--ligacao", "confere=ficha-que-nao-existe"]),
    CasoRecusaTabela("alvo-ambiguo", SAIDA_USO, ["--classe", "gabarito", "--ligacao", "confere=gestão estratégica"]),
    CasoRecusaTabela("estado-desconhecido", SAIDA_USO, ["--classe", "politica", "--estado", "estado-inventado"]),
    CasoRecusaTabela("banco-indisponivel", SAIDA_DEP, ["gabarito"], retrato_fn=_falhar_banco_indisponivel),
    CasoRecusaTabela("conexoes-esgotadas", SAIDA_DEP, ["gabarito"], retrato_fn=_falhar_conexoes_esgotadas),
    CasoRecusaTabela("acesso-negado", SAIDA_NEGADO, ["--classe", "segredo"], aut_fn=_negar_segredo),
    CasoRecusaTabela("prazo-estourado", SAIDA_FALHA, ["gabarito"], retrato_fn=_falhar_prazo_estourado),
    CasoRecusaTabela("falha-interna", SAIDA_FALHA, ["gabarito"], retrato_fn=_falhar_interna),
]


def test_cobertura_exata_dos_24_codigos_da_especificacao() -> None:
    assert len(CODIGOS_DA_ESPECIFICACAO) == TOTAL_CODIGOS_TABELA
    cobertos = {"termo-nao-casou", *(c.codigo for c in CASOS_RECUSA_TABELA)}
    assert cobertos == set(CODIGOS_DA_ESPECIFICACAO)

    rc, out, err = rodar_consultar(["termo completamente desconhecido", "--json"])
    assert rc == CODIGOS_DA_ESPECIFICACAO["termo-nao-casou"] == SAIDA_OK
    assert err == ""
    assert json.loads(out)["desfecho"] == "termo-nao-casou"


@pytest.mark.parametrize("caso", CASOS_RECUSA_TABELA, ids=lambda c: c.codigo)
def test_cada_codigo_de_recusa_da_tabela(caso: CasoRecusaTabela) -> None:
    assert CODIGOS_DA_ESPECIFICACAO[caso.codigo] == caso.saida
    rc, out, err = rodar_consultar(caso.args, ato=caso.ato, retrato=caso.retrato_fn, autorizador=caso.aut_fn)
    assert rc == caso.saida and out == ""
    pacote = _validar_recusa_stderr(err, caso.codigo, [caso.ato, *caso.args])
    serializado = json.dumps(pacote)
    assert "Connection refused" not in serializado
    assert "FATAL:" not in serializado
    assert "sensivel" not in serializado


# ==================================================================== 2. dicionário vs texto nas 3 fontes
@pytest.mark.parametrize(
    ("classe_arg", "prop_dic_errada", "prop_txt_errada", "valor_existente_esperado"),
    [
        ("verbo", "esfera=errado", "prazo-de-espera=999s", "10s"),
        ("classe", "rigidez=errado", "inicio=1999-01", "2026-01"),
        ("dicionario", "modulo=errado", "resumo=inexistente", "Negócio ou plataforma"),
    ],
)
def test_dicionario_errado_sai_2_e_texto_errado_sai_0_com_valores_nas_tres_fontes(
    classe_arg: str,
    prop_dic_errada: str,
    prop_txt_errada: str,
    valor_existente_esperado: str,
) -> None:
    rc_dic, out_dic, err_dic = rodar_consultar(["--classe", classe_arg, "--prop", prop_dic_errada])
    assert rc_dic == SAIDA_USO and out_dic == ""
    _validar_recusa_stderr(err_dic, "valor-fora-do-dicionario", ["consultar", "--classe", classe_arg, "--prop", prop_dic_errada])

    rc_txt, out_txt, err_txt = rodar_consultar(["--classe", classe_arg, "--prop", prop_txt_errada, "--json"])
    assert rc_txt == SAIDA_OK and err_txt == ""
    reg = json.loads(out_txt)
    assert reg["total"] == 0
    valores = [v["valor"] for v in reg["valores_existentes"] or ()]
    assert valor_existente_esperado in valores


# ==================================================================== 3. acento NFC/NFD, sinais, não-ASCII, plural e encerrada
def test_acento_inteiro_nfc_e_separado_nfd_dao_o_mesmo_resultado() -> None:
    nfc = unicodedata.normalize("NFC", "ações padrão")
    nfd = unicodedata.normalize("NFD", "ações padrão")
    assert nfc != nfd
    rc1, out1, _ = rodar_consultar([nfc, "--json"])
    rc2, out2, _ = rodar_consultar([nfd, "--json"])
    assert rc1 == rc2 == SAIDA_OK
    r1, r2 = json.loads(out1), json.loads(out2)
    assert r1["fichas"] == r2["fichas"]
    assert r1["fichas"][0]["chave"] == "gabarito:acoes-padrao"


@pytest.mark.parametrize("termo_vazio", ["--", "???", "Ω", "Жж", "漢字"])
def test_termo_so_de_sinais_ou_so_fora_do_ascii_sai_2_com_termo_sem_letra(termo_vazio: str) -> None:
    rc, out, err = rodar_consultar([termo_vazio])
    assert rc == SAIDA_USO and out == ""
    _validar_recusa_stderr(err, "termo-sem-letra", ["consultar", termo_vazio])


def test_plural_so_casa_pela_linha_da_tabela_de_nomes_e_linha_encerrada_nao_resolve() -> None:
    rc_com, out_com, _ = rodar_consultar(["gabaritos", "--json"], retrato=RetratoFalsoConsultar(incluir_plural_gabaritos=True))
    assert rc_com == SAIDA_OK
    assert [f["chave"] for f in json.loads(out_com)["fichas"]] == ["gabarito"]

    rc_sem, out_sem, _ = rodar_consultar(["gabaritos", "--json"], retrato=RetratoFalsoConsultar(incluir_plural_gabaritos=False))
    assert rc_sem == SAIDA_OK
    reg_sem = json.loads(out_sem)
    assert reg_sem["desfecho"] == "termo-nao-casou" and reg_sem["total"] == 0

    rc_enc, out_enc, _ = rodar_consultar(["apelido-encerrado", "--json"])
    assert rc_enc == SAIDA_OK and json.loads(out_enc)["desfecho"] == "termo-nao-casou"


# ==================================================================== 4. consulta por nome (1 ficha, várias, qualificador, não casou, autorização)
def test_nome_que_nomeia_duas_fichas_devolve_ambas_com_definicao_e_passo() -> None:
    rc, out_txt, err = rodar_consultar(["gestão estratégica"])
    assert rc == SAIDA_OK and err == ""
    linhas = out_txt.splitlines()
    assert linhas[0] == "nome «gestão estratégica» · 2 fichas"
    assert any(ln.startswith("capacidade:gestao-estrategica · capacidade · ") and "passo " in ln for ln in linhas[1:])
    assert any(ln.startswith("gestao-estrategica · persona · ") and "passo 4" in ln for ln in linhas[1:])


def test_ficha_unica_respeita_ligacoes_com_e_sem() -> None:
    rc_com, out_com, _ = rodar_consultar(["framework da ontologia", "--ligacoes", "com", "--json"])
    rc_pad, out_pad, _ = rodar_consultar(["framework da ontologia", "--json"])
    rc_sem, out_sem, _ = rodar_consultar(["framework da ontologia", "--ligacoes", "sem", "--json"])
    assert rc_com == rc_pad == rc_sem == SAIDA_OK

    reg_com = json.loads(out_com)
    assert reg_com == json.loads(out_pad)
    assert reg_com["ficha"]["ligacoes"] == {
        "saida": {"confere": ["capacidade:ontologia"]},
        "chegada": {"usa": ["gabarito:comportamento"]},
    }
    assert "ligacoes" not in json.loads(out_sem)["ficha"]

    _, txt_com, _ = rodar_consultar(["framework da ontologia", "--ligacoes", "com"])
    assert txt_com.index('"saida"') < txt_com.index('"chegada"')

    _, txt_uma, _ = rodar_consultar(["framework da ontologia", "--ligacoes", "sem"])
    assert txt_uma.splitlines()[0] == "nome «framework da ontologia» · 1 fichas"


def test_termo_com_qualificador_vira_condicao_e_demanda_nao_corta_dentro_da_palavra() -> None:
    rc_dem, out_dem, _ = rodar_consultar(["demanda", "--json"])
    assert rc_dem == SAIDA_OK and json.loads(out_dem)["desfecho"] == "termo-nao-casou"

    rc, out_txt, err = rodar_consultar(["gabaritos de modelos formais"])
    assert rc == SAIDA_OK and err == ""
    linhas = out_txt.splitlines()
    assert linhas[0].startswith(
        "nome «gabaritos de modelos formais» virou condição · gabarito ligada a capacidade:ontologia · fichas 1 a 1 de 1 · digest v1:"
    )
    assert any(ln.startswith("gabarito:framework-da-ontologia") for ln in linhas[1:])


def test_termo_que_nao_casa_devolve_candidatos_ou_disponiveis_sem_busca_pelo_sentido() -> None:
    rc_sem, out_sem, err_sem = rodar_consultar(["xyzzy inexistente plugh", "--json"])
    assert rc_sem == SAIDA_OK and err_sem == ""
    reg_sem = json.loads(out_sem)
    assert reg_sem["desfecho"] == "termo-nao-casou"
    assert reg_sem["candidatos"] is None
    assert "gabarito" in reg_sem["disponiveis"]["classes"]
    assert "--classe" in reg_sem["disponiveis"]["filtros"]
    assert reg_sem["proximo"] == [{"tipo": "nome-candidato", "termo": "xyzzy inexistente plugh"}]
    assert "buscar" not in out_sem

    rc_cand, out_cand, _ = rodar_consultar(["coisa sobre gabarito", "--json"])
    assert rc_cand == SAIDA_OK
    reg_cand = json.loads(out_cand)
    assert reg_cand["desfecho"] == "termo-nao-casou"
    assert reg_cand["disponiveis"] is None
    assert any(c["chave"] == "gabarito" for c in reg_cand["candidatos"])


def test_autorizacao_por_classe_nega_tudo_com_4_e_filtra_classes_mistas() -> None:
    rc_neg, out_neg, err_neg = rodar_consultar(["chave cofre"], autorizador=_negar_segredo)
    assert rc_neg == SAIDA_NEGADO and out_neg == ""
    _validar_recusa_stderr(err_neg, "acesso-negado", ["consultar", "chave cofre"])

    rc_misto, out_misto, err_misto = rodar_consultar(["misto-aut", "--json"], autorizador=_negar_segredo)
    assert rc_misto == SAIDA_OK and err_misto == ""
    assert [f["chave"] for f in json.loads(out_misto)["fichas"]] == ["gabarito:framework-da-ontologia"]


# ==================================================================== 5. --sem-prop, --sem-ligacao, alvos, coluna de ficha e --filhas
def test_falta_de_propriedade_com_e_sem_valor_nas_tres_fontes() -> None:
    _, out_dado_sem, _ = rodar_consultar(["--classe", "verbo", "--sem-prop", "esfera", "--json"])
    assert [f["chave"] for f in json.loads(out_dado_sem)["fichas"]] == ["verbo:ontologia"]

    _, out_dado_val, _ = rodar_consultar(["--classe", "verbo", "--sem-prop", "prazo-de-espera=10s", "--json"])
    assert [f["chave"] for f in json.loads(out_dado_val)["fichas"]] == ["verbo:ontologia"]

    _, out_sh_sem, _ = rodar_consultar(["--classe", "classe", "--sem-prop", "inicio", "--json"])
    chaves_sh_sem = {f["chave"] for f in json.loads(out_sh_sem)["fichas"]}
    assert "gabarito" in chaves_sh_sem and "shape" not in chaves_sh_sem

    _, out_sh_val, _ = rodar_consultar(["--classe", "classe", "--sem-prop", "rigidez=rigido", "--json"])
    assert [f["chave"] for f in json.loads(out_sh_val)["fichas"]] == ["exploracao"]

    _, out_dc_sem, _ = rodar_consultar(["--classe", "dicionario", "--sem-prop", "resumo", "--json"])
    chaves_dc_sem = {f["chave"] for f in json.loads(out_dc_sem)["fichas"]}
    assert "dicionario:modulo" in chaves_dc_sem and "dicionario:rigidez" not in chaves_dc_sem

    _, out_dc_val, _ = rodar_consultar(["--classe", "dicionario", "--sem-prop", "do_framework=sim", "--json"])
    assert [f["chave"] for f in json.loads(out_dc_val)["fichas"]] == ["dicionario:esfera"]


def test_falta_de_ligacao_nos_dois_sentidos_com_e_sem_alvo() -> None:
    _, out_s_sem, _ = rodar_consultar(["--classe", "gabarito", "--sem-ligacao", "confere", "--json"])
    assert [f["chave"] for f in json.loads(out_s_sem)["fichas"]] == ["gabarito:acoes-padrao"]

    _, out_s_alvo, _ = rodar_consultar(["--classe", "gabarito", "--sem-ligacao", "confere=capacidade:ontologia", "--json"])
    assert [f["chave"] for f in json.loads(out_s_alvo)["fichas"]] == ["gabarito:acoes-padrao", "gabarito:comportamento"]

    _, out_c_sem, _ = rodar_consultar(["--classe", "capacidade", "--sem-ligacao", "chegada:confere", "--json"])
    assert [f["chave"] for f in json.loads(out_c_sem)["fichas"]] == ["capacidade:busca", "capacidade:gestao-estrategica"]

    _, out_c_alvo, _ = rodar_consultar(
        ["--classe", "capacidade", "--sem-ligacao", "chegada:confere=gabarito:framework-da-ontologia", "--json"],
    )
    chaves_c_alvo = {f["chave"] for f in json.loads(out_c_alvo)["fichas"]}
    assert "capacidade:ontologia" not in chaves_c_alvo and "capacidade:dev" in chaves_c_alvo


def test_alvo_de_ligacao_por_chave_por_nome_ambiguo_e_inexistente() -> None:
    _, out_ch, _ = rodar_consultar(["--classe", "gabarito", "--ligacao", "confere=capacidade:ontologia", "--json"])
    _, out_nm, _ = rodar_consultar(["--classe", "gabarito", "--ligacao", "confere=modelo formal", "--json"])
    assert [f["chave"] for f in json.loads(out_ch)["fichas"]] == ["gabarito:framework-da-ontologia"]
    assert json.loads(out_ch)["fichas"] == json.loads(out_nm)["fichas"]

    rc_amb, _, err_amb = rodar_consultar(["--classe", "gabarito", "--ligacao", "confere=gestão estratégica"])
    assert rc_amb == SAIDA_USO
    pac_amb = _validar_recusa_stderr(err_amb, "alvo-ambiguo", ["consultar", "--classe", "gabarito", "--ligacao", "confere=gestão estratégica"])
    assert "capacidade:gestao-estrategica" in pac_amb["erro"]["cura"]
    assert "gestao-estrategica" in pac_amb["erro"]["cura"]

    rc_inex, _, err_inex = rodar_consultar(["--classe", "gabarito", "--ligacao", "confere=alvo-que-nao-ha"])
    assert rc_inex == SAIDA_USO
    pac_inex = _validar_recusa_stderr(err_inex, "alvo-inexistente", ["consultar", "--classe", "gabarito", "--ligacao", "confere=alvo-que-nao-ha"])
    assert "alvo-que-nao-ha" in pac_inex["erro"]["proximo"]
    assert "buscar" not in pac_inex["erro"]["proximo"]


def test_coluna_capacidade_restringe_resolucao_a_classe_apontada_e_primeira_linha_abre_com_classe() -> None:
    rc, out_txt, err = rodar_consultar(["--classe", "classe", "--prop", "capacidade=busca"])
    assert rc == SAIDA_OK and err == ""
    linhas = out_txt.splitlines()
    assert linhas[0].startswith(f"classe · fornada {FORNADA_BASE} · fichas 1 a 1 de 1 · digest v1:")
    assert linhas[1].startswith("exploracao")


def test_slug_exato_da_classe_vence_apelido_homonimo_de_outra_classe() -> None:
    banco = RetratoFalsoConsultar()
    banco.nomes.append(LinhaNomeFalsa("politica", "gabarito"))
    rc, out, err = rodar_consultar(["--classe", "politica", "--json"], retrato=banco)
    assert rc == SAIDA_OK and err == ""
    assert json.loads(out)["classe"] == "politica"


def test_filhas_inclui_descendentes_genericas_da_classe_pedida() -> None:
    _, out_sem, _ = rodar_consultar(["--classe", "regra", "--json"])
    _, out_com, _ = rodar_consultar(["--classe", "regra", "--filhas", "--json"])
    assert json.loads(out_sem)["total"] == 0
    chaves_filhas = {f["chave"] for f in json.loads(out_com)["fichas"]}
    assert "gabarito:framework-da-ontologia" in chaves_filhas and "politica:0001-acesso" in chaves_filhas


# ==================================================================== 6. ciclo, ordem canônica, estado, paginação, fecho por bytes e prazo
def test_caminhada_com_ciclo_e_dois_caminhos_do_mesmo_tamanho_devolve_sempre_o_mesmo() -> None:
    banco = RetratoFalsoConsultar()
    banco.fichas["gabarito:final"] = {
        "uuid": "f-gab-fin", "chave": "gabarito:final", "classe": "gabarito",
        "classe_uuid": "c-gab", "rotulo": "Final", "definicao": "d",
    }
    banco.ligacoes.extend([
        LigacaoFalsa("f-gab-acoes", "p-usa", "usa", "f-gab-fw", posicao=2),
        LigacaoFalsa("f-gab-fw", "p-usa", "usa", "f-gab-comp", posicao=1),
        LigacaoFalsa("f-gab-fin", "p-usa", "usa", "f-gab-comp", posicao=1),
        LigacaoFalsa("f-gab-fin", "p-usa", "usa", "f-gab-acoes", posicao=5),
    ])
    rc, out, err = rodar_consultar(
        ["--classe", "gabarito", "--ligacao", "usa/3=gabarito:framework-da-ontologia", "--json"],
        retrato=banco,
    )
    assert rc == SAIDA_OK and err == ""
    reg = json.loads(out)
    final = next(f for f in reg["fichas"] if f["chave"] == "gabarito:final")
    assert final["caminho"] == [
        {"de": "gabarito:framework-da-ontologia", "ligacao": "usa", "para": "gabarito:acoes-padrao"},
        {"de": "gabarito:acoes-padrao", "ligacao": "usa", "para": "gabarito:final"},
    ]


def test_mesmos_predicados_em_ordem_diferente_dao_mesma_pagina_e_mesma_continuacao() -> None:
    args_a = ["--classe", "classe", "--prop", "modulo=casa", "--prop", "rigidez=rigido", "--json"]
    args_b = ["--classe", "classe", "--prop", "rigidez=rigido", "--prop", "modulo=casa", "--json"]
    _, out_a, _ = rodar_consultar(args_a, tamanho_pagina=2)
    _, out_b, _ = rodar_consultar(args_b, tamanho_pagina=2)
    reg_a, reg_b = json.loads(out_a), json.loads(out_b)
    assert reg_a["fichas"] == reg_b["fichas"]
    assert reg_a["continuacao"] == reg_b["continuacao"] is not None


def test_estado_vigente_vem_do_ultimo_evento_e_ficha_sem_evento_nao_casa() -> None:
    _, out_vig, _ = rodar_consultar(["--classe", "politica", "--estado", "vigente", "--json"])
    _, out_min, _ = rodar_consultar(["--classe", "politica", "--estado", "minuta", "--json"])
    assert [f["chave"] for f in json.loads(out_vig)["fichas"]] == ["politica:0001-acesso"]
    assert [f["chave"] for f in json.loads(out_min)["fichas"]] == ["politica:0002-rascunho"]


def test_segunda_pagina_pela_continuacao_marca_mudou_e_reautoriza() -> None:
    chamadas_aut: list[str] = []

    def aut_conta(cls: str, _s: str | None) -> bool:
        chamadas_aut.append(cls)
        return True

    banco_p1 = RetratoFalsoConsultar(fornada=FORNADA_BASE)
    _, out_p1, _ = rodar_consultar(["--classe", "classe", "--json"], retrato=banco_p1, autorizador=aut_conta, tamanho_pagina=3)
    p1 = json.loads(out_p1)
    assert p1["mudou"] is None and p1["de"] == 1 and p1["ate"] == 3 and p1["continuacao"] is not None

    chamadas_aut.clear()
    _, out_p2_igual, _ = rodar_consultar(
        ["--classe", "classe", "--cursor", p1["continuacao"], "--json"],
        retrato=banco_p1, autorizador=aut_conta, tamanho_pagina=3,
    )
    p2_igual = json.loads(out_p2_igual)
    assert p2_igual["mudou"] is False and p2_igual["de"] == 4 and p2_igual["ate"] == 6
    assert "shape" in chamadas_aut

    banco_p2_novo = RetratoFalsoConsultar(fornada=FORNADA_NOVA)
    _, out_p2_mudou, _ = rodar_consultar(
        ["--classe", "classe", "--cursor", p1["continuacao"], "--json"],
        retrato=banco_p2_novo, tamanho_pagina=3,
    )
    assert json.loads(out_p2_mudou)["mudou"] is True


def test_pagina_fecha_por_bytes_antes_do_tamanho_pedido() -> None:
    rc, out, err = rodar_consultar(["--classe", "classe", "--json"], teto_bytes=TETO_CURTO_PAGINA, tamanho_pagina=50)
    assert rc == SAIDA_OK and err == ""
    assert len(out.encode("utf-8")) <= TETO_CURTO_PAGINA
    reg = json.loads(out)
    assert 1 <= reg["ate"] < reg["total"]
    assert reg["continuacao"] is not None

    _, out_seg, _ = rodar_consultar(
        ["--classe", "classe", "--cursor", reg["continuacao"], "--json"],
        teto_bytes=TETO_CURTO_PAGINA, tamanho_pagina=50,
    )
    assert json.loads(out_seg)["de"] == reg["ate"] + 1


def test_prazo_da_chamada_estoura_numa_caminhada_de_varios_niveis_curtos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Relógio determinístico: cada consulta avança o instante monotônico até consumir o orçamento global
    relogio = {"agora": 100.0}

    def _monotonic_falso() -> float:
        return relogio["agora"]

    monkeypatch.setattr("leitura.retrato.time.monotonic", _monotonic_falso)

    psql_rapido = tmp_path / "psql_rapido.py"
    psql_rapido.write_text(
        textwrap.dedent(
            """\
            import json, sys
            n = 0
            for linha in sys.stdin:
                s = linha.strip()
                if s.startswith("\\\\echo "):
                    sys.stdout.write(s.split(" ", 1)[1] + "\\n")
                    sys.stdout.flush()
                elif s.startswith("\\\\bind "):
                    n += 1
                    sys.stdout.write(json.dumps([{"ficha": f"u-{n}", "pai": "u-0", "propriedade": "usa", "posicao": 1}]) + "\\n")
                    sys.stdout.flush()
            """
        ),
        encoding="utf-8",
    )

    with (
        pytest.raises(Recusa) as exc_info,
        Retrato(prazo=1.0, comando=[sys.executable, str(psql_rapido)]) as con,
        casa_db.retrato(conexao=con, autorizador=lambda _c, _s: True) as sessao,
    ):
        consultar_real = con.consultar

        def _consultar_avancando_relogio(sql: str, *p: Any) -> list[dict]:
            res = consultar_real(sql, *p)
            relogio["agora"] += 0.4
            return res

        monkeypatch.setattr(con, "consultar", _consultar_avancando_relogio)
        pred = casa_db.PredicadoLigacao(n=1, propriedade_id="p-usa", sentido="saida", alvos=("u-0",), passos=6)
        sessao.caminhar_ligacao(pred)

    assert exc_info.value.saida == SAIDA_FALHA
    assert exc_info.value.codigo == "prazo-estourado"


# ==================================================================== 7. esquema JSON e compatibilidade com a versão anterior
@pytest.mark.parametrize(
    "args_chamada",
    [
        ["framework da ontologia", "--json"],
        ["framework da ontologia", "--ligacoes", "sem", "--json"],
        ["gestão estratégica", "--json"],
        ["gabaritos de modelos formais", "--json"],
        ["termo sem casamento nenhum", "--json"],
        ["coisa sobre gabarito", "--json"],
        ["--classe", "classe", "--prop", "capacidade=busca", "--json"],
        ["--classe", "verbo", "--prop", "prazo-de-espera=nao-existe", "--json"],
        ["--classe", "classe", "--json"],
    ],
)
def test_retorno_json_valida_contra_esquema(args_chamada: list[str]) -> None:
    esquema_atual = json.loads(ESQUEMA_ATUAL.read_text(encoding="utf-8"))
    rc, out, err = rodar_consultar(args_chamada, tamanho_pagina=3)
    assert rc == SAIDA_OK, err
    validar_contra_esquema(json.loads(out), esquema_atual)


def test_esquema_atual_e_compativel_com_versao_anterior() -> None:
    esquema_atual = json.loads(ESQUEMA_ATUAL.read_text(encoding="utf-8"))
    esquema_ant = json.loads(ESQUEMA_ANTERIOR.read_text(encoding="utf-8"))
    assert conferir_compatibilidade_esquema(esquema_ant, esquema_atual) == []

    esquema_quebrado = json.loads(ESQUEMA_ATUAL.read_text(encoding="utf-8"))
    esquema_quebrado["properties"].pop("mudou")
    assert conferir_compatibilidade_esquema(esquema_atual, esquema_quebrado) != []


# ==================================================================== 8. testes unitários diretos do leitor
def test_literal_liga_nulo_como_texto_vazio_e_seis_sqls_existem() -> None:
    assert literal(None) == "''"
    for nome in (
        "resolver_nomes.sql",
        "catalogo_da_classe.sql",
        "alcance_nivel.sql",
        "consultar_fichas.sql",
        "rastro.sql",
        "valores_da_propriedade.sql",
    ):
        assert (SQL / nome).is_file()


def test_escrever_lista_emite_erro_e_erros_na_ultima_linha() -> None:
    r1 = Recusa(SAIDA_USO, "propriedade-desconhecida", onde="--prop", recebido="x", regra="r", cura="c1", proximo="p1")
    r2 = Recusa(SAIDA_USO, "estado-desconhecido", onde="--estado", recebido="y", regra="r", cura="c2", proximo="p2")
    fluxo = io.StringIO()
    assert escrever_lista(Recusas([r1, r2]).erros, fluxo=fluxo) == SAIDA_USO
    dados = json.loads(fluxo.getvalue().splitlines()[-1])
    assert dados["erro"] == dados["erros"][0]
    assert [e["codigo"] for e in dados["erros"]] == ["propriedade-desconhecida", "estado-desconhecido"]


TOTAL_CLASSES_ESCALA = 168
TOTAL_AUTORIZADAS_ESCALA = 167
LIMITE_PRAZO_TESTE = 1.5
PRAZO_CURTO_ESTOURO = 0.15


def _retrato_168_classes() -> RetratoFalsoConsultar:
    banco = RetratoFalsoConsultar()
    mae_shape = banco.classes["shape"]["uuid"]
    faltam = TOTAL_CLASSES_ESCALA - len(banco.classes)
    for idx in range(faltam):
        slug = f"classe-escala-{idx:03d}"
        uid = f"00000000-0000-0000-9999-{idx:012d}"
        banco.classes[slug] = {
            "uuid": uid,
            "slug": slug,
            "rotulo": f"classe escala {idx}",
            "definicao": "classe sintética de escala",
            "variantes": [],
            "mae": mae_shape,
            "relacao_com_mae": "generica",
        }
        banco.fichas[slug] = {
            "uuid": uid,
            "chave": slug,
            "classe": "shape",
            "classe_uuid": mae_shape,
            "rotulo": f"classe escala {idx}",
            "definicao": "classe sintética de escala",
        }
    for sh in banco.classes.values():
        if sh["slug"] != "shape" and not sh.get("mae"):
            sh["mae"] = mae_shape
            sh["relacao_com_mae"] = "generica"
    return banco


class _RelogioSimulado:
    def __init__(self, passo_por_processo: float = 0.0) -> None:
        self.agora = 100.0
        self.passo = passo_por_processo

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float | None = None) -> None:
        self.agora += self.passo if segundos is None else segundos


def _criar_bin_acesso_100ms(tmp_path: Path) -> tuple[Path, Path]:
    contador = tmp_path / "acesso_invocacoes.txt"
    script = tmp_path / "acesso_100ms"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, select, sys\n"
        f"contador = pathlib.Path({str(contador)!r})\n"
        "with contador.open('a', encoding='utf-8') as fh:\n"
        "    fh.write('1\\n')\n"
        "select.select([], [], [], 0.10)\n"
        "recursos = [a for a in sys.argv[3:] if a.startswith('classe:')]\n"
        "itens = [\n"
        "    {'recurso': r, 'permitido': (r != 'classe:segredo'), 'regra': 'teste', 'motivo': 'x', 'faltou': []}\n"
        "    for r in recursos\n"
        "]\n"
        "if len(itens) == 1:\n"
        "    it = itens[0]\n"
        "    print(json.dumps({**it, 'plano': 'p', 'sujeito': 's', 'acao': 'ler'}))\n"
        "    sys.exit(0 if it['permitido'] else 1)\n"
        "print(json.dumps({'plano': 'p', 'sujeito': 's', 'acao': 'ler', 'itens': itens}))\n"
        "sys.exit(1 if any(not i['permitido'] for i in itens) else 0)\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script, contador


def test_autorizacao_em_lote_100ms_com_168_classes_nos_dois_caminhos(tmp_path: Path) -> None:
    banco = _retrato_168_classes()
    assert len(banco.classes) == TOTAL_CLASSES_ESCALA
    bin_acesso, contador = _criar_bin_acesso_100ms(tmp_path)

    rc_filhas, out_filhas, err_filhas = rodar_consultar(
        ["--classe", "shape", "--filhas", "--json"],
        retrato=banco,
        bin_acesso=bin_acesso,
        prazo=LIMITE_PRAZO_TESTE,
    )
    assert rc_filhas == SAIDA_OK, err_filhas
    assert len(contador.read_text(encoding="utf-8").splitlines()) == 1
    assert json.loads(out_filhas)["classe"] == "shape"

    contador.write_text("", encoding="utf-8")
    rc_disp, out_disp, err_disp = rodar_consultar(
        ["xyzzy inexistente plugh", "--json"],
        retrato=banco,
        bin_acesso=bin_acesso,
        prazo=LIMITE_PRAZO_TESTE,
    )
    assert rc_disp == SAIDA_OK, err_disp
    assert len(contador.read_text(encoding="utf-8").splitlines()) == 1
    disponiveis = json.loads(out_disp)["disponiveis"]["classes"]
    assert len(disponiveis) == TOTAL_AUTORIZADAS_ESCALA
    assert "segredo" not in disponiveis


def _autorizador_100ms_simulado(relogio: _RelogioSimulado) -> Callable[[str, str | None], bool]:
    def _decidir(_cls: str, _suj: str | None) -> bool:
        relogio.avancar(0.10)
        return True

    return _decidir


def test_autorizacao_que_excede_prazo_sai_5_nos_dois_caminhos() -> None:
    banco = _retrato_168_classes()
    rel1 = _RelogioSimulado()
    rc_filhas, out_filhas, err_filhas = rodar_consultar(
        ["--classe", "shape", "--filhas"],
        retrato=banco,
        autorizador=_autorizador_100ms_simulado(rel1),
        relogio=rel1,
        prazo=5.0,
    )
    assert rc_filhas == SAIDA_FALHA and out_filhas == ""
    _validar_recusa_stderr(err_filhas, "prazo-estourado", ["consultar", "--classe", "shape", "--filhas"])

    rel2 = _RelogioSimulado()
    rc_disp, out_disp, err_disp = rodar_consultar(
        ["xyzzy inexistente plugh"],
        retrato=banco,
        autorizador=_autorizador_100ms_simulado(rel2),
        relogio=rel2,
        prazo=5.0,
    )
    assert rc_disp == SAIDA_FALHA and out_disp == ""
    _validar_recusa_stderr(err_disp, "prazo-estourado", ["consultar", "xyzzy inexistente plugh"])


def _criar_pap_lote(tmp_path: Path) -> dict[str, str]:
    (tmp_path / "pdp.py").write_text(
        "from dataclasses import dataclass\n"
        "import yaml\n"
        "@dataclass\n"
        "class Sujeito:\n"
        "    id: str; natureza: str; papeis: tuple; dominios: tuple\n"
        "    temas: tuple = (); vetos: tuple = (); habilitacao: str = 'publico'\n"
        "@dataclass\n"
        "class Recurso:\n"
        "    tipo: str; id: str; dominio: str; tema: str = '-'; sigilo: str = 'publico'\n"
        "@dataclass\n"
        "class Decisao:\n"
        "    permitido: bool; regra: str; motivo: str; faltou: tuple = ()\n"
        "class Politica:\n"
        "    def __init__(self, dados): self.regras = dados.get('regras') or []\n"
        "    @classmethod\n"
        "    def de_arquivo(cls, p): return cls(yaml.safe_load(p.read_text('utf-8')) or {})\n"
        "def decide(suj, _acao, rec, pol):\n"
        "    if not suj.papeis: return Decisao(False, '', 'sem papel', ('papel',))\n"
        "    if rec.id == 'classe:segredo': return Decisao(False, 'nega-segredo', 'bloqueado')\n"
        "    return Decisao(True, 'operador-plataforma', 'ok')\n",
        encoding="utf-8",
    )
    (tmp_path / "politica.yaml").write_text("versao: 1\nregras: []\n", encoding="utf-8")
    (tmp_path / "sujeitos.yaml").write_text(
        "versao: 1\nsujeitos:\n  suj-op:\n    natureza: pessoa\n    papeis: [operador]\n    dominios: [plataforma]\n",
        encoding="utf-8",
    )
    return {"ACESSO_POLITICA_DIR": str(tmp_path)}


def test_bin_acesso_real_em_lote_e_erro_2_sai_5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_pap = _criar_pap_lote(tmp_path)
    monkeypatch.setenv("ACESSO_POLITICA_DIR", env_pap["ACESSO_POLITICA_DIR"])
    decisoes = casa_db.autorizar_classes(["gabarito", "segredo", "verbo"], "suj-op", bin_acesso=RAIZ / "bin" / "acesso")
    assert decisoes == {"gabarito": True, "segredo": False, "verbo": True}

    acesso_quebrado = tmp_path / "acesso_exit2"
    acesso_quebrado.write_text("#!/bin/sh\necho '{\"erro\": \"uso\"}' >&2\nexit 2\n", encoding="utf-8")
    acesso_quebrado.chmod(0o755)
    rc, out, err = rodar_consultar(["--classe", "gabarito"], bin_acesso=acesso_quebrado)
    assert rc == SAIDA_FALHA and out == ""
    _validar_recusa_stderr(err, "falha-interna", ["consultar", "--classe", "gabarito"])
