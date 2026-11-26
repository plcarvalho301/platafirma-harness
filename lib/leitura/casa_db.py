"""casa_db.py — o leitor do banco casa para o verbo busca (story 4427, t8 e t10).

Contratos:
- platafirma-casa@referencias/instancias/verbo/busca.md, «O SQL dentro do leitor»,
  «A caminhada pelas ligações», «A versão da classe» e «A conexão e o retrato».

Abre um retrato de leitura por chamada, autoriza uma vez por classe via `acesso decidir`,
executa as seis consultas fixas com parâmetros ligados, faz a caminhada em largura na
memória do processo, reconstrói o rastro só para as fichas da página e lê a configuração
`versao-da-classe.yaml` na release servida.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import yaml

from . import resolvedor
from .morada import release_raiz
from .recusa import Recusa
from .retrato import PRAZO_CHAMADA, SQL, Retrato

_RAIZ_HARNESS = Path(__file__).resolve().parents[2]
_REGRA_AUT = "verbo:busca §O que o verbo faz com o que voltou"
_REGRA_VERSAO = "verbo:busca §A versão da classe"
_PRAZO_ACESSO = 5.0
_TAMANHO_PAR = 2

_CHAVES_VERSAO = frozenset({"versao", "fontes", "casos", "eventos", "mais_recente"})
_FONTES_VERSAO = frozenset({
    "fornada-da-classe",
    "iniciou-do-dado-vigente",
    "iniciou-da-ligacao-vigente",
    "evento-que-cita-a-classe",
})
_CASOS_VERSAO = {
    "shape": ["fornada-de-toda-classe"],
    "dicionario": ["fornada-de-todo-dicionario", "fornada-de-todo-valor"],
}
_MAIS_RECENTE_VERSAO = ["ocorrido_em desc", "uuid desc"]

SQL_CLASSES_DISPONIVEIS = """
SELECT DISTINCT classe FROM casa_leitura.linhagem_das_classes ORDER BY classe
"""

SQL_FILHAS_DA_CLASSE = """
SELECT DISTINCT classe_uuid::text AS uuid, classe
  FROM casa_leitura.linhagem_das_classes
 WHERE ancestral_uuid = $1::uuid
 ORDER BY classe
"""

SQL_UUID_DA_CLASSE = """
SELECT uuid::text AS uuid, slug AS classe FROM casa.shape WHERE slug = $1
"""

SQL_VALORES_DO_DICIONARIO = """
SELECT v.slug, v.rotulo
  FROM casa.valor v
  JOIN casa.dicionario d ON d.uuid = v.dicionario
 WHERE d.slug = $1
 ORDER BY v.ordem, v.slug
"""


@dataclass(frozen=True)
class ColunaFixa:
    """Metadado de uma coluna consultável de `casa.shape` ou `casa.dicionario`."""

    nome: str
    fonte: str
    tipo: str
    classe_alvo: str | None = None
    dicionario_slug: str | None = None


COLUNAS_SHAPE: dict[str, ColunaFixa] = {
    c.nome: c
    for c in (
        ColunaFixa("slug", "shape", "texto"),
        ColunaFixa("rotulo", "shape", "texto"),
        ColunaFixa("iri", "shape", "texto"),
        ColunaFixa("capacidade", "shape", "ficha", classe_alvo="capacidade"),
        ColunaFixa("mae", "shape", "ficha", classe_alvo="shape"),
        ColunaFixa("raiz", "shape", "ficha", classe_alvo="shape"),
        ColunaFixa("instanciavel", "shape", "booleano"),
        ColunaFixa("fechada", "shape", "booleano"),
        ColunaFixa("calculada_de_eventos", "shape", "booleano"),
        ColunaFixa("definicao", "shape", "texto"),
        ColunaFixa("criterio", "shape", "texto"),
        ColunaFixa("porque", "shape", "texto"),
        ColunaFixa("canais", "shape", "lista"),
        ColunaFixa("variantes", "shape", "lista"),
        ColunaFixa("resumo", "shape", "texto"),
        ColunaFixa("inicio", "shape", "texto"),
        ColunaFixa("fim", "shape", "texto"),
        ColunaFixa("categoria", "shape", "dicionario", dicionario_slug="categoria"),
        ColunaFixa("estrato", "shape", "dicionario", dicionario_slug="estrato"),
        ColunaFixa("rigidez", "shape", "dicionario", dicionario_slug="rigidez"),
        ColunaFixa("modulo", "shape", "dicionario", dicionario_slug="modulo"),
        ColunaFixa("relacao_com_mae", "shape", "dicionario", dicionario_slug="tipo-de-relacao"),
        ColunaFixa("genero", "shape", "dicionario", dicionario_slug="genero-de-prosa"),
    )
}

COLUNAS_DICIONARIO: dict[str, ColunaFixa] = {
    c.nome: c
    for c in (
        ColunaFixa("slug", "dicionario", "texto"),
        ColunaFixa("rotulo", "dicionario", "texto"),
        ColunaFixa("definicao", "dicionario", "texto"),
        ColunaFixa("criterio", "dicionario", "texto"),
        ColunaFixa("capacidade", "dicionario", "ficha", classe_alvo="capacidade"),
        ColunaFixa("disjuntas", "dicionario", "booleano"),
        ColunaFixa("do_framework", "dicionario", "booleano"),
        ColunaFixa("endereco_das_entradas", "dicionario", "texto"),
        ColunaFixa("resumo", "dicionario", "texto"),
        ColunaFixa("modulo", "dicionario", "dicionario", dicionario_slug="modulo"),
        ColunaFixa("estrato", "dicionario", "dicionario", dicionario_slug="estrato"),
    )
}


def colunas_da_classe(slug: str) -> dict[str, ColunaFixa]:
    if slug == "shape":
        return COLUNAS_SHAPE
    if slug == "dicionario":
        return COLUNAS_DICIONARIO
    return {}


@dataclass(frozen=True)
class PredicadoLigacao:
    """Um predicado de ligação pronto para a caminhada por nível."""

    n: int
    propriedade_id: str | None
    sentido: str
    alvos: tuple[str, ...]
    passos: int


@dataclass(frozen=True)
class NoAlcance:
    """Ficha alcançada na caminhada por nível, no primeiro nível que a visitou."""

    ficha: str
    nivel: int
    pai: str
    propriedade: str
    posicao: int | None


@dataclass(frozen=True)
class ResultadoNome:
    """Saída autorizada de `resolver_nomes`."""

    linhas: list[dict]
    ords_negados: frozenset[int]


def _falha_versao(detalhe: str) -> Recusa:
    return Recusa(5, "falha-interna", onde="versao-da-classe.yaml", regra=_REGRA_VERSAO, cura=detalhe)


def carregar_eventos_da_versao(release: Path | None = None) -> list[str]:
    """Lê e valida `versao-da-classe.yaml` na release servida (ou `PF_VERSAO_CLASSE_YAML` em teste).

    Recusa com saída 5 (`falha-interna`) quando o arquivo falta ou traz chave, fonte, caso
    ou critério fora dos que `consultar_fichas.sql` implementa.
    """
    env = os.getenv("PF_VERSAO_CLASSE_YAML")
    arq = Path(env) if env else (release_raiz(release) / "current/conhecimento/ontologia/olaria/versao-da-classe.yaml")
    try:
        dados = yaml.safe_load(arq.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        raise _falha_versao(f"a configuração {arq} não se lê na release") from None
    if not isinstance(dados, dict) or set(dados) != _CHAVES_VERSAO or dados.get("versao") != 1:
        raise _falha_versao("chaves ou versão inválidas em versao-da-classe.yaml")
    fontes = dados.get("fontes")
    if not isinstance(fontes, list) or len(fontes) != len(set(fontes)) or set(fontes) != _FONTES_VERSAO:
        raise _falha_versao("fontes de versao-da-classe.yaml divergem das suportadas pelo leitor")
    if dados.get("casos") != _CASOS_VERSAO or dados.get("mais_recente") != _MAIS_RECENTE_VERSAO:
        raise _falha_versao("casos ou critério mais_recente de versao-da-classe.yaml divergem do leitor")
    eventos = dados.get("eventos")
    if not isinstance(eventos, list) or not eventos or not all(isinstance(e, str) and e.strip() for e in eventos):
        raise _falha_versao("eventos ausentes ou inválidos em versao-da-classe.yaml")
    return list(eventos)


def _interpretar_saida_acesso(unicos: list[str], texto_stdout: str, amostra: str) -> dict[str, bool]:
    try:
        dados = json.loads(texto_stdout)
    except ValueError:
        raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="a decisão de acesso devolveu JSON inválido") from None
    if not isinstance(dados, dict):
        raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="a decisão de acesso devolveu formato inesperado")
    if len(unicos) == 1 and "permitido" in dados:
        if dados.get("faltou"):
            raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                         regra=_REGRA_AUT, cura="faltou atributo na projeção do sujeito")
        return {unicos[0]: bool(dados["permitido"])}
    itens = dados.get("itens")
    if not isinstance(itens, list):
        raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="a decisão em lote de acesso não trouxe a lista itens")
    mapa: dict[str, bool] = {}
    for it in itens:
        if not isinstance(it, dict) or it.get("faltou"):
            raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                         regra=_REGRA_AUT, cura="faltou atributo na projeção do sujeito")
        rec = str(it.get("recurso") or "")
        if rec.startswith("classe:"):
            mapa[rec.removeprefix("classe:")] = bool(it.get("permitido"))
    if any(s not in mapa for s in unicos):
        raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="a decisão em lote não respondeu para todas as classes pedidas")
    return mapa


def autorizar_classes(
    slugs: Sequence[str],
    sujeito: str | None = None,
    *,
    prazo_restante: float | None = None,
    bin_acesso: Path | None = None,
) -> dict[str, bool]:
    """Decide `(ler, classe:<slug>)` num único processo `acesso decidir` para o lote de classes."""
    unicos = list(dict.fromkeys(str(s) for s in slugs if s))
    if not unicos:
        return {}
    amostra = f"classe:{unicos[0]}" if len(unicos) == 1 else f"classe:{unicos[0]}+{len(unicos) - 1}"
    limite = _PRAZO_ACESSO if prazo_restante is None else prazo_restante
    if limite <= 0:
        raise Recusa(5, "prazo-estourado", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="o prazo da chamada acabou antes da autorização")
    exe = bin_acesso or Path(os.getenv("PF_ACESSO_BIN") or (_RAIZ_HARNESS / "bin" / "acesso"))
    cmd = [str(exe), "decidir", "ler", *(f"classe:{s}" for s in unicos), "--json"]
    if sujeito:
        cmd.extend(["--sujeito", sujeito])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=limite, check=False)
    except subprocess.TimeoutExpired:
        raise Recusa(5, "prazo-estourado", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="a decisão de acesso excedeu o prazo da chamada") from None
    except OSError:
        raise Recusa(3, "banco-indisponivel", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="o executável de acesso não pôde ser chamado") from None
    if proc.returncode == 3:  # noqa: PLR2004 - código 3 do contrato de saída dos verbos (dependência)
        raise Recusa(3, "banco-indisponivel", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="a política ou projeção de acesso está indisponível")
    if proc.returncode not in (0, 1):
        raise Recusa(5, "falha-interna", onde="autorizacao", recebido=amostra,
                     regra=_REGRA_AUT, cura="o verbo acesso falhou ao decidir a autorização")
    return _interpretar_saida_acesso(unicos, proc.stdout, amostra)


def autorizar_classe(
    slug: str,
    sujeito: str | None = None,
    *,
    bin_acesso: Path | None = None,
    prazo_restante: float | None = None,
) -> bool:
    """Decide `(ler, classe:<slug>)` pelo verbo `acesso decidir` servido."""
    return autorizar_classes([slug], sujeito, prazo_restante=prazo_restante, bin_acesso=bin_acesso)[slug]


def _sql_arquivo(nome: str) -> str:
    return (SQL / nome).read_text(encoding="utf-8")


class SessaoLeitura:
    """Retrato aberto do banco casa com autorização por classe e as seis consultas do leitor."""

    def __init__(
        self,
        contexto: Mapping[str, Any] | None = None,
        par: tuple[str, str | None] | None = None,
        prazo: float = PRAZO_CHAMADA,
        **opcoes: Any,
    ) -> None:
        conexao = opcoes.get("conexao")
        autorizador: Callable[[str, str | None], bool] | None = opcoes.get("autorizador")
        self._contexto = dict(contexto or {})
        self._par = par
        self._origem: str | None = opcoes.get("origem")
        self._prazo = prazo
        self._inicio = 0.0
        self._conexao_injetada = conexao
        self._con: Any = None
        self._dono_conexao = conexao is None
        self._autorizador = autorizador
        self._bin_acesso: Path | None = opcoes.get("bin_acesso")
        self._relogio: Callable[[], float] = opcoes.get("relogio") or time.monotonic
        self._release: Path | None = opcoes.get("release")
        self._cache_aut: dict[str, bool] = {}

    def __enter__(self) -> Self:
        self._inicio = self._relogio()
        if self._dono_conexao:
            self._con = Retrato(prazo=self._prazo).__enter__()
        else:
            entrar = getattr(self._conexao_injetada, "__enter__", None)
            self._con = entrar() if entrar is not None else self._conexao_injetada
        try:
            if self._par is not None and len(self._par) == _TAMANHO_PAR and self._par[1]:
                self.exigir_autorizacao(str(self._par[1]))
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._con is not None and hasattr(self._con, "__exit__"):
            self._con.__exit__(exc_type, exc_val, exc_tb)
        self._con = None

    @property
    def sujeito(self) -> str | None:
        val = self._contexto.get("sujeito") or os.getenv("PF_SUJEITO")
        return str(val) if val else None

    def _tempo_restante(self) -> float:
        if self._con is not None and hasattr(self._con, "resta"):
            return float(self._con.resta())
        if self._inicio > 0:
            return self._prazo - (self._relogio() - self._inicio)
        return self._prazo

    def _conferir_prazo(self) -> float:
        resta = self._tempo_restante()
        if resta <= 0:
            raise Recusa(
                5,
                "prazo-estourado",
                onde="autorizacao",
                regra=_REGRA_AUT,
                cura="o prazo da chamada acabou durante a autorização",
                proximo="busca consultar --classe shape",
            )
        return resta

    def autorizar_lote(self, slugs: Sequence[str]) -> dict[str, bool]:
        """Confere `(ler, classe:<slug>)` uma vez por classe não cacheada, num único processo."""
        faltantes = [s for s in dict.fromkeys(str(x) for x in slugs if x) if s not in self._cache_aut]
        if faltantes:
            if self._autorizador is not None:
                for s in faltantes:
                    self._conferir_prazo()
                    self._cache_aut[s] = bool(self._autorizador(s, self.sujeito))
                self._conferir_prazo()
            else:
                decisoes = autorizar_classes(
                    faltantes,
                    self.sujeito,
                    prazo_restante=self._conferir_prazo(),
                    bin_acesso=self._bin_acesso,
                )
                self._conferir_prazo()
                self._cache_aut.update(decisoes)
        return {str(s): self._cache_aut[str(s)] for s in slugs if s}

    def autorizar(self, classe_slug: str) -> bool:
        """Confere `(ler, classe:<slug>)` no máximo uma vez por classe nesta chamada."""
        return self.autorizar_lote([classe_slug])[classe_slug]

    def exigir_autorizacao(self, classe_slug: str) -> None:
        if not self.autorizar(classe_slug):
            raise Recusa(
                4,
                "acesso-negado",
                onde="classe",
                recebido=classe_slug,
                regra=_REGRA_AUT,
                cura=f"acesso negado para ler a classe {classe_slug}",
                proximo="busca consultar --classe shape",
            )

    # ---------------------------------------------------------------- as seis consultas e auxiliares
    def resolver_nomes(self, termos: Sequence[str]) -> ResultadoNome:
        """Resolve os termos e filtra pelas classes autorizadas, marcando os `ord` totalmente negados."""
        if hasattr(self._con, "resolver_nomes"):
            brutas = self._con.resolver_nomes(list(termos))
        else:
            brutas = self._con.consultar(_sql_arquivo("resolver_nomes.sql"), list(termos))
        por_ord: dict[int, list[dict]] = {}
        todas_classes: list[str] = []
        for ln in brutas:
            por_ord.setdefault(int(ln["ord"]), []).append(ln)
            if ln.get("chave") and ln.get("classe"):
                todas_classes.append(str(ln["classe"]))
        if todas_classes:
            self.autorizar_lote(todas_classes)

        filtradas: list[dict] = []
        negados: set[int] = set()
        for ord_n, grupo in sorted(por_ord.items()):
            com_chave = [ln for ln in grupo if ln.get("chave")]
            if not com_chave:
                filtradas.extend(grupo)
                continue
            autorizadas = [ln for ln in com_chave if self.autorizar(str(ln["classe"]))]
            if not autorizadas:
                negados.add(ord_n)
                base = dict(com_chave[0])
                filtradas.append({
                    "ord": ord_n,
                    "norm": base.get("norm") or "",
                    "passo": None,
                    "chave": None,
                    "classe": None,
                    "e_classe": None,
                    "rotulo": None,
                    "definicao": None,
                })
            else:
                filtradas.extend(autorizadas)
        return ResultadoNome(filtradas, frozenset(negados))

    def ficha_da_chave(self, chave: str) -> resolvedor.Ficha | None:
        f = resolvedor.ficha_da_chave(self._con, chave)
        if f is None:
            return None
        if not self.autorizar(f.classe):
            raise Recusa(
                4,
                "acesso-negado",
                onde="chave",
                recebido=chave,
                regra=_REGRA_AUT,
                cura=f"acesso negado para ler fichas da classe {f.classe}",
                proximo="busca consultar --classe shape",
            )
        return f

    def resolver_alvo(self, ficha: resolvedor.Ficha, raiz: Path) -> resolvedor.Alvo:
        return resolvedor.resolver(self._con, ficha, raiz)

    def ficha_inteira(self, ficha: resolvedor.Ficha, *, com_ligacoes: bool = True) -> dict:
        return resolvedor.ficha_inteira(self._con, ficha, com_ligacoes=com_ligacoes)

    def ler_ficha(self, chave: str, *, com_ligacoes: bool = True) -> dict:
        f = resolvedor.ficha_da_chave(self._con, chave)
        if f is None:
            return {}
        self.exigir_autorizacao(f.classe)
        return resolvedor.ficha_inteira(self._con, f, com_ligacoes=com_ligacoes)

    def uuid_da_classe(self, slug: str) -> str | None:
        linhas = self._con.consultar(SQL_UUID_DA_CLASSE, slug)
        return str(linhas[0]["uuid"]) if linhas else None

    def filhas_da_classe_brutas(self, classe_uuid: str) -> list[tuple[str, str]]:
        linhas = self._con.consultar(SQL_FILHAS_DA_CLASSE, classe_uuid)
        return [(str(ln["uuid"]), str(ln["classe"])) for ln in linhas]

    def filhas_da_classe(self, classe_uuid: str) -> list[tuple[str, str]]:
        """Devolve `(uuid, slug)` da classe e das descendentes genéricas/restritivas autorizadas."""
        pares = self.filhas_da_classe_brutas(classe_uuid)
        self.autorizar_lote([slug for _, slug in pares])
        return [(uid, slug) for uid, slug in pares if self.autorizar(slug)]

    def classes_disponiveis(self) -> list[str]:
        linhas = self._con.consultar(SQL_CLASSES_DISPONIVEIS)
        slugs = [str(ln["classe"]) for ln in linhas]
        self.autorizar_lote(slugs)
        return [s for s in slugs if self.autorizar(s)]

    def valores_do_dicionario(self, dicionario_slug: str) -> list[dict]:
        """Devolve `[{slug, rotulo}]` de um dicionário para colunas fixas de `shape` e `dicionario`."""
        linhas = self._con.consultar(SQL_VALORES_DO_DICIONARIO, dicionario_slug)
        return [{"slug": str(ln["slug"]), "rotulo": ln.get("rotulo")} for ln in linhas]

    def catalogo_da_classe(self, classes_uuids: Sequence[str]) -> list[dict]:
        return self._con.consultar(_sql_arquivo("catalogo_da_classe.sql"), list(classes_uuids))

    def caminhar_ligacao(self, pred: PredicadoLigacao) -> dict[str, NoAlcance]:
        """Busca em largura por nível em memória do processo, até `pred.passos`."""
        sql = _sql_arquivo("alcance_nivel.sql")
        visitadas: set[str] = set(pred.alvos)
        fronteira: list[str] = list(pred.alvos)
        alcance: dict[str, NoAlcance] = {}
        for nivel in range(1, pred.passos + 1):
            if not fronteira:
                break
            linhas = self._con.consultar(sql, fronteira, pred.propriedade_id, pred.sentido)
            proxima: list[str] = []
            for ln in linhas:
                f_uid = str(ln["ficha"])
                if f_uid in visitadas:
                    continue
                visitadas.add(f_uid)
                pos = ln.get("posicao")
                alcance[f_uid] = NoAlcance(
                    ficha=f_uid,
                    nivel=nivel,
                    pai=str(ln["pai"]),
                    propriedade=str(ln["propriedade"]),
                    posicao=int(pos) if pos is not None else None,
                )
                proxima.append(f_uid)
            fronteira = proxima
        return alcance

    def _reconstruir_caminhos(
        self,
        alcances: Sequence[dict[str, NoAlcance]],
        uuids_pagina: Sequence[str],
    ) -> dict[str, list[dict[str, str]]]:
        if not alcances or not uuids_pagina:
            return {}
        primario = alcances[0]
        trilhas_uuid: dict[str, list[tuple[str, str, str]]] = {}
        participantes: set[str] = set()
        for f_uid in uuids_pagina:
            if f_uid not in primario:
                continue
            passos: list[tuple[str, str, str]] = []
            atual = f_uid
            while atual in primario:
                no = primario[atual]
                passos.append((no.pai, no.propriedade, no.ficha))
                participantes.add(no.pai)
                participantes.add(no.ficha)
                atual = no.pai
            passos.reverse()
            trilhas_uuid[f_uid] = passos
        if not participantes:
            return {}
        linhas_rastro = self._con.consultar(_sql_arquivo("rastro.sql"), sorted(participantes))
        chaves = {str(ln["uuid"]): str(ln["chave_humana"]) for ln in linhas_rastro}
        return {
            f_uid: [
                {"de": chaves.get(pai, pai), "ligacao": prop, "para": chaves.get(filho, filho)}
                for pai, prop, filho in passos
            ]
            for f_uid, passos in trilhas_uuid.items()
        }

    def consultar_fichas(
        self,
        filtro: Mapping[str, Any],
        cursor: tuple[int, str] | None = None,
        *,
        cursor_ordem: int | None = None,
        cursor_chave: str | None = None,
        tamanho_pagina: int = 50,
    ) -> dict[str, Any]:
        """Executa a caminhada das ligações, `consultar_fichas.sql` e o rastro da página."""
        if cursor is not None:
            cursor_ordem, cursor_chave = cursor
        eventos = carregar_eventos_da_versao(self._release)
        classes_uuids: list[str] = list(filtro["classes_uuids"])
        preds_prop: list[dict] = list(filtro.get("propriedades") or [])
        preds_lig: list[PredicadoLigacao] = list(filtro.get("ligacoes") or [])
        faltas_lig: list[dict] = list(filtro.get("faltas_ligacao") or [])
        estado: str | None = filtro.get("estado")

        alcances_por_pred: list[dict[str, NoAlcance]] = []
        alcance_json: list[dict[str, Any]] = []
        for pred in preds_lig:
            mapa = self.caminhar_ligacao(pred)
            alcances_por_pred.append(mapa)
            for no in mapa.values():
                alcance_json.append({
                    "n": pred.n,
                    "ficha": no.ficha,
                    "passos": no.nivel,
                    "posicao": no.posicao,
                })

        linhas = self._con.consultar(
            _sql_arquivo("consultar_fichas.sql"),
            classes_uuids,
            json.dumps(preds_prop, ensure_ascii=False),
            json.dumps(alcance_json, ensure_ascii=False),
            str(len(preds_lig)),
            estado,
            str(cursor_ordem) if cursor_ordem is not None else None,
            cursor_chave,
            str(tamanho_pagina),
            eventos,
            json.dumps(faltas_lig, ensure_ascii=False),
        )
        if not linhas:
            raise Recusa(5, "falha-interna", onde="consultar_fichas", regra="verbo:busca §consultar_fichas",
                         cura="consultar_fichas voltou sem linha de cabeçalho",
                         proximo="busca consultar --classe shape")

        cab = linhas[0]
        itens_pagina = [ln for ln in linhas if ln.get("chave") is not None]
        itens_pagina.sort(key=lambda r: (int(r["ordem"]), str(r["chave"])))
        caminhos = self._reconstruir_caminhos(alcances_por_pred, [str(ln["uuid"]) for ln in itens_pagina])

        fichas = [
            {
                "uuid": str(ln["uuid"]),
                "ordem": int(ln["ordem"]),
                "chave": str(ln["chave"]),
                "classe": str(ln["classe"]),
                "rotulo": ln.get("rotulo"),
                "estado": ln.get("estado"),
                "caminho": caminhos.get(str(ln["uuid"])),
            }
            for ln in itens_pagina
        ]
        return {
            "total": int(cab.get("total") or 0),
            "antes": int(cab.get("antes") or 0),
            "digest": str(cab.get("digest") or ""),
            "fornada": str(cab["fornada"]) if cab.get("fornada") is not None else None,
            "fichas": fichas,
        }

    def valores_da_propriedade(
        self,
        fonte: str,
        restricoes: Sequence[str],
        coluna: str | None,
        classes_uuids: Sequence[str],
    ) -> list[dict[str, Any]]:
        linhas = self._con.consultar(
            _sql_arquivo("valores_da_propriedade.sql"),
            fonte,
            list(restricoes),
            coluna,
            list(classes_uuids),
        )
        return [{"valor": str(ln["valor"]), "contagem": int(ln["fichas"])} for ln in linhas]

    def ligacoes_opostas(
        self,
        classes_uuids: Sequence[str],
        ligacoes: Sequence[PredicadoLigacao],
    ) -> list[dict[str, Any]]:
        """No vazio de `--ligacao`, verifica ligações no sentido oposto ou por outra propriedade."""
        if not ligacoes:
            return []
        if hasattr(self._con, "ligacoes_opostas"):
            linhas = self._con.ligacoes_opostas(list(classes_uuids), list(ligacoes))
        else:
            preds_json = [
                {
                    "propriedade_id": p.propriedade_id,
                    "sentido": p.sentido,
                    "alvos": list(p.alvos),
                }
                for p in ligacoes
            ]
            linhas = self._con.consultar(
                _sql_arquivo("ligacoes_opostas.sql"),
                list(classes_uuids),
                json.dumps(preds_json, ensure_ascii=False),
            )
        return [
            {
                "propriedade": str(ln["propriedade"]),
                "sentido": str(ln["sentido"]),
                "alvo": str(ln["alvo"]),
                "contagem": int(ln["fichas"]),
            }
            for ln in linhas
            if int(ln.get("fichas") or 0) > 0
        ]


def retrato(
    contexto: Mapping[str, Any] | None = None,
    par: tuple[str, str | None] | None = None,
    prazo: float = PRAZO_CHAMADA,
    **opcoes: Any,
) -> SessaoLeitura:
    """Abre um retrato de leitura do banco casa para uma chamada do verbo."""
    return SessaoLeitura(contexto, par, prazo, **opcoes)
