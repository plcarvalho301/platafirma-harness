"""resolvedor.py — da chave à ficha, e da ficha ao arquivo na morada (stories 4426 e 4427).

Contratos:
- platafirma-casa@referencias/instancias/interface-de-verbo/busca.md, «Leitura pela chave»
- platafirma-casa@referencias/instancias/verbo/busca.md, «O que o verbo faz com o que voltou»
- platafirma-casa@referencias/instancias/componente/leitor-universal.md, «As moradas que lê»
"""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from .tipos import AlvoResolvido, Recusa, TipoMorada

CLASSE_DAS_CLASSES = "shape"
MORADA_LIDA = "git"

SQL_FICHA = """
SELECT f.uuid::text AS uuid, f.chave_humana AS chave, c.slug AS classe, c.uuid::text AS classe_uuid
  FROM casa.ficha f JOIN casa.shape c ON c.uuid = f.classe
 WHERE f.chave_humana = $1
"""

# O molde do caminho e a morada da classe: o golden, a referência e a estrutura de documento.
SQL_MOLDE = """
SELECT 'golden' AS fonte, g.tipo AS tipo, g.endereco AS endereco
  FROM casa.golden g WHERE g.ficha = $1::uuid
UNION ALL
SELECT 'referencia', NULL, r.endereco
  FROM casa.referencia r WHERE r.ficha = $1::uuid
UNION ALL
SELECT 'estrutura', e.regime, e.morada
  FROM casa.estrutura_de_documento e WHERE e.shape = $1::uuid AND e.encerra_em IS NULL
"""

_SQL_DADOS_FICHA = """
         'chave', f.chave_humana,
         'classe', c.slug,
         'criada_em', f.criada_em,
         'dados', coalesce((
            SELECT jsonb_object_agg(x.slug, x.valores)
              FROM (SELECT p.slug, jsonb_agg(coalesce(d.valor, to_jsonb(d.valor_de_dicionario)) ORDER BY d.id) AS valores
                      FROM casa.dado d
                      JOIN casa.restricao r ON r.id = d.restricao
                      JOIN casa.propriedade p ON p.id = r.propriedade
                     WHERE d.ficha = f.uuid AND d.terminou IS NULL
                     GROUP BY p.slug) x), '{}'::jsonb),
"""

_SQL_DECLARACAO_E_FROM = """
         'declaracao', (SELECT jsonb_strip_nulls(to_jsonb(s) - 'uuid' - 'fornada')
                          FROM casa.shape s WHERE s.uuid = f.uuid)
       ) AS ficha
  FROM casa.ficha f JOIN casa.shape c ON c.uuid = f.classe
 WHERE f.uuid = $1::uuid
"""

_SQL_BLOCO_LIGACOES = """
         'ligacoes', jsonb_build_object(
            'saida', coalesce((
               SELECT jsonb_object_agg(y.slug, y.para)
                 FROM (SELECT p.slug, jsonb_agg(t.chave_humana ORDER BY l.posicao NULLS LAST, t.chave_humana) AS para
                         FROM casa.ligacao l
                         JOIN casa.propriedade p ON p.id = l.propriedade
                         JOIN casa.ficha t ON t.uuid = l.para
                        WHERE l."de" = f.uuid AND l.terminou IS NULL
                        GROUP BY p.slug) y), '{}'::jsonb),
            'chegada', coalesce((
               SELECT jsonb_object_agg(z.slug, z.origens)
                 FROM (SELECT p.slug, jsonb_agg(o.chave_humana ORDER BY l.posicao NULLS LAST, o.chave_humana) AS origens
                         FROM casa.ligacao l
                         JOIN casa.propriedade p ON p.id = l.propriedade
                         JOIN casa.ficha o ON o.uuid = l."de"
                        WHERE l.para = f.uuid AND l.terminou IS NULL
                        GROUP BY p.slug) z), '{}'::jsonb)
         ),
"""

# A ficha inteira com ligações vigentes agrupadas por propriedade, primeiro saída e depois chegada.
SQL_FICHA_INTEIRA = "SELECT jsonb_build_object(\n" + _SQL_DADOS_FICHA + _SQL_BLOCO_LIGACOES + _SQL_DECLARACAO_E_FROM

# A ficha inteira sem ligações, para `--ligacoes sem`.
SQL_FICHA_SEM_LIGACOES = "SELECT jsonb_build_object(\n" + _SQL_DADOS_FICHA + _SQL_DECLARACAO_E_FROM

_MARCADORES = re.compile(r"<[^<>/]+>(?:[/-]<[^<>/]+>)*")
_SEGMENTO = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class Consulta(Protocol):
    def consultar(self, sql: str, *parametros: Any) -> list[dict]: ...


@dataclass(frozen=True)
class Ficha:
    uuid: str
    chave: str
    classe: str
    classe_uuid: str

    @property
    def e_classe(self) -> bool:
        return self.classe == CLASSE_DAS_CLASSES

    @property
    def chave_lida(self) -> str:
        """A chave no cabeçalho: a ficha de uma classe se lê como shape:<classe>."""
        return f"{CLASSE_DAS_CLASSES}:{self.chave}" if self.e_classe else self.chave


@dataclass(frozen=True)
class Alvo:
    ficha: Ficha
    caminho: Path | None      # o arquivo na morada; None: a ficha inteira
    documento: str | None     # o caminho relativo à casa na release
    motivo: str               # por que é arquivo ou ficha inteira


def ficha(retrato: Consulta, chave: str) -> Ficha | None:
    linhas = retrato.consultar(SQL_FICHA, chave)
    return Ficha(**linhas[0]) if linhas else None


def ficha_da_chave(retrato: Consulta, chave: str) -> Ficha | None:
    """A ficha que a chave aponta: a chave humana exata, ou `<classe>:` e `shape:<classe>`."""
    achada = ficha(retrato, chave)
    if achada is not None:
        return achada
    candidata = None
    if chave.endswith(":") and ":" not in chave[:-1]:
        candidata = chave[:-1]
    elif chave.startswith(f"{CLASSE_DAS_CLASSES}:"):
        candidata = chave[len(CLASSE_DAS_CLASSES) + 1:]
    if not candidata:
        return None
    achada = ficha(retrato, candidata)
    return achada if achada is not None and achada.e_classe else None


def caminho_do_molde(molde: str, f: Ficha) -> tuple[str | None, str]:
    """(caminho relativo, motivo); o caminho é None quando o molde não monta arquivo para a chave."""
    m = molde.split(",", 1)[0].strip()
    if not m.endswith(".md") or "<" not in m:
        return None, "molde-sem-arquivo"
    fixo = m[: m.index("<")]
    resto = m[len(fixo): -len(".md")]
    if not fixo.endswith(f"/{f.classe}/") or not _MARCADORES.fullmatch(resto):
        return None, "molde-nao-entendido"
    slug = f.chave.split(":", 1)[1] if ":" in f.chave else f.chave
    partes = slug.split(":")
    if not all(_SEGMENTO.fullmatch(p) and ".." not in p for p in partes):
        return None, "chave-fora-do-molde"
    if len(partes) != resto.count("/") + 1:
        return None, "chave-nao-cabe-no-molde"
    return fixo + "/".join(partes) + ".md", "molde"


def _molde_da_classe(linhas: list[dict]) -> tuple[str | None, str]:
    golden = [ln for ln in linhas if ln["fonte"] == "golden"]
    referencia = [ln for ln in linhas if ln["fonte"] == "referencia"]
    for ln in golden:
        if ln["tipo"] == "casa":
            return ln["endereco"], "golden"
    for ln in referencia:
        return ln["endereco"], "referencia"
    if golden:
        return None, f"golden-de-tipo-{golden[0]['tipo']}"
    return None, "classe-sem-documento"


def casa_na_release(release: Path) -> Path:
    """A casa na release servida: <raiz da release>/current/casa."""
    return Path(release) / "current" / "casa"


def resolver(retrato: Consulta, f: Ficha, release: Path) -> Alvo:
    """O arquivo da ficha na morada que a classe declara, ou a ficha inteira."""
    linhas = retrato.consultar(SQL_MOLDE, f.classe_uuid)
    molde, fonte = _molde_da_classe(linhas)
    if molde is None:
        return Alvo(f, None, None, fonte)
    estrutura = [ln for ln in linhas if ln["fonte"] == "estrutura"]
    morada = estrutura[0]["endereco"] if estrutura else MORADA_LIDA
    if morada != MORADA_LIDA:
        return Alvo(f, None, None, f"morada-{morada}-nao-lida")
    rel, motivo = caminho_do_molde(molde, f)
    if rel is None:
        return Alvo(f, None, None, motivo)
    base = casa_na_release(release)
    alvo = base / rel
    base_real = os.path.realpath(base)
    if not os.path.realpath(alvo).startswith(base_real.rstrip(os.sep) + os.sep):
        return Alvo(f, None, None, "caminho-fora-da-morada")
    if not alvo.is_file():
        return Alvo(f, None, rel, "arquivo-ausente-na-release")
    return Alvo(f, alvo, rel, fonte)


def _ordenar_ficha(crua: dict[str, Any], *, com_ligacoes: bool) -> dict[str, Any]:
    dados_brutos = crua.get("dados")
    dados = dict(sorted(dados_brutos.items())) if isinstance(dados_brutos, dict) else {}
    decl_bruta = crua.get("declaracao")
    decl = dict(sorted(decl_bruta.items())) if isinstance(decl_bruta, dict) else decl_bruta
    ordenada: dict[str, Any] = {}
    for ch in ("chave", "classe", "criada_em"):
        if ch in crua:
            ordenada[ch] = crua[ch]
    ordenada["dados"] = dados
    if com_ligacoes:
        ligs = crua.get("ligacoes") if isinstance(crua.get("ligacoes"), dict) else {}
        saida = ligs.get("saida") if isinstance(ligs.get("saida"), dict) else {}
        chegada = ligs.get("chegada") if isinstance(ligs.get("chegada"), dict) else {}
        ordenada["ligacoes"] = {
            "saida": dict(sorted(saida.items())),
            "chegada": dict(sorted(chegada.items())),
        }
    if "declaracao" in crua:
        ordenada["declaracao"] = decl
    for ch, val in crua.items():
        if ch not in ordenada and (com_ligacoes or ch != "ligacoes"):
            ordenada[ch] = val
    return ordenada


def ficha_inteira(retrato: Consulta, f: Ficha, *, com_ligacoes: bool = True) -> dict:
    sql = SQL_FICHA_INTEIRA if com_ligacoes else SQL_FICHA_SEM_LIGACOES
    linhas = retrato.consultar(sql, f.uuid)
    if not linhas:
        return {}
    return _ordenar_ficha(dict(linhas[0]["ficha"]), com_ligacoes=com_ligacoes)


# ================================================================== estágios 3 e 4 (story #4442, t5)

_RE_CHAVE_CAN = re.compile(r"^[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9._/-]*$")
_RE_SLUG_VALIDO = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
_RE_CLASSE_VALIDA = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RE_DRIVE_WIN = re.compile(r"^[A-Za-z]:[\\/]")
_RAIZ_REGISTRO_PORTA = Path(__file__).resolve().parents[2] / "registro" / "porta.yaml"

_CLASSES_RASTREADOR = frozenset(
    {"card", "epico", "feature", "story", "task", "ideia", "incidente", "comentario"}
)


class ErroResolucao(Exception):
    """Recusa estruturada emitida nos estágios 3 ou 4 do componente leitura."""

    def __init__(self, recusa: Recusa) -> None:
        self.recusa = recusa
        self.saida = recusa.saida
        super().__init__(recusa.codigo)


@dataclass(frozen=True, slots=True)
class ClasseAlcance:
    """Entrada de uma classe na vista de alcance compilada."""

    classe: str
    morada: TipoMorada
    verbo_dono: str
    molde: str = ""
    universo_fechado: bool = True
    digest_release: str | None = None


@dataclass(frozen=True, slots=True)
class VistaAlcance:
    """Vista local de alcance de verbos e classes sem consulta ao banco vivo."""

    verbos_aceitam_ler: frozenset[str]
    alcance_verbo: Mapping[str, frozenset[str]]
    classes: Mapping[str, ClasseAlcance]
    digest_release: str | None = None


_CLASSES_PADRAO: dict[str, ClasseAlcance] = {
    "shape": ClasseAlcance("shape", "banco", "ontologia", universo_fechado=True),
    "dicionario": ClasseAlcance("dicionario", "banco", "ontologia", universo_fechado=True),
    "sessao": ClasseAlcance("sessao", "banco", "ontologia", universo_fechado=True),
    "ato": ClasseAlcance("ato", "git", "busca", molde="referencias/instancias/ato/<slug>.md"),
    "verbo": ClasseAlcance("verbo", "git", "busca", molde="referencias/instancias/verbo/<slug>.md"),
    "politica": ClasseAlcance("politica", "git", "busca", molde="instancias/politica/<slug>.md"),
    "capacidade": ClasseAlcance("capacidade", "git", "busca", molde="referencias/instancias/capacidade/<slug>.md"),
    "persona": ClasseAlcance("persona", "git", "busca", molde="instancias/persona/<slug>.md"),
    "gabarito": ClasseAlcance("gabarito", "git", "busca", molde="instancias/gabarito/<slug>.md"),
    "card": ClasseAlcance("card", "rastreador", "tarefas", universo_fechado=True),
    "epico": ClasseAlcance("epico", "rastreador", "tarefas", universo_fechado=True),
    "feature": ClasseAlcance("feature", "rastreador", "tarefas", universo_fechado=True),
    "story": ClasseAlcance("story", "rastreador", "tarefas", universo_fechado=True),
    "task": ClasseAlcance("task", "rastreador", "tarefas", universo_fechado=True),
    "ideia": ClasseAlcance("ideia", "rastreador", "tarefas", universo_fechado=True),
    "incidente": ClasseAlcance("incidente", "rastreador", "tarefas", universo_fechado=True),
    "comentario": ClasseAlcance("comentario", "rastreador", "tarefas", universo_fechado=True),
    "obra": ClasseAlcance("obra", "banco", "acervo", universo_fechado=False),
    "secao": ClasseAlcance("secao", "banco", "acervo", universo_fechado=False),
    "pagina": ClasseAlcance("pagina", "wiki", "acervo", universo_fechado=False),
    "objeto": ClasseAlcance("objeto", "balde", "acervo", universo_fechado=False),
    "mensagem": ClasseAlcance("mensagem", "fila", "fila", universo_fechado=True),
    "lousa": ClasseAlcance("lousa", "fila", "mesa", universo_fechado=True),
    "execucao": ClasseAlcance("execucao", "fila", "analise", universo_fechado=True),
    "segredo": ClasseAlcance("segredo", "cofre", "seg", universo_fechado=True),
}

_ALCANCE_PADRAO: dict[str, frozenset[str]] = {
    "busca": frozenset({"*"}),
    "ontologia": frozenset({"shape", "dicionario", "sessao"}),
    "tarefas": _CLASSES_RASTREADOR,
    "acervo": frozenset({"obra", "secao", "pagina", "objeto"}),
    "fila": frozenset({"mensagem"}),
    "mesa": frozenset({"lousa"}),
    "analise": frozenset({"execucao"}),
    "seg": frozenset({"segredo"}),
    "repo": frozenset({"ato", "verbo", "politica", "capacidade", "persona", "gabarito"}),
    "release": frozenset({"ato", "verbo", "politica", "capacidade", "persona", "gabarito"}),
}


def carregar_vista_alcance(registro_porta: Path | None = None) -> VistaAlcance:
    """Carrega a vista provisória de alcance a partir de `registro/porta.yaml` (sem banco)."""
    arq = registro_porta if registro_porta is not None else _RAIZ_REGISTRO_PORTA
    verbos_ler = set(_ALCANCE_PADRAO)
    try:
        dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
        verbos = dados.get("verbos") if isinstance(dados, dict) else {}
        if isinstance(verbos, dict):
            for slug, info in verbos.items():
                desc = str(info.get("descricao") or "") if isinstance(info, dict) else ""
                if "ler" in desc or slug in _ALCANCE_PADRAO:
                    verbos_ler.add(str(slug))
    except (OSError, yaml.YAMLError):
        pass
    return VistaAlcance(
        verbos_aceitam_ler=frozenset(verbos_ler),
        alcance_verbo=dict(_ALCANCE_PADRAO),
        classes=dict(_CLASSES_PADRAO),
    )


def _separar_membro(chave: str) -> tuple[str, str | None]:
    if "!" not in chave:
        return chave, None
    base, membro = chave.split("!", 1)
    partes = membro.split("/") if membro else []
    if not membro or membro.startswith("/") or "\x00" in membro or any(p in ("", "..") for p in partes):
        raise ErroResolucao(
            Recusa(
                saida=2,
                codigo="chave-mal-formada",
                onde="chave",
                recebido=chave,
                regra="seletor-membro-posix-relativo",
                cura="membro interno deve ser caminho relativo POSIX sem '/' inicial nem '..'",
                proximo=f"busca ler {base}" if base else "",
            )
        )
    return base, membro


def _validar_sem_caminho_solto(chave: str) -> None:
    if chave.startswith(("/", "./", "../", "~")) or _RE_DRIVE_WIN.match(chave):
        raise ErroResolucao(
            Recusa(
                saida=2,
                codigo="caminho-solto-recusado",
                onde="chave",
                recebido=chave,
                regra="chave-logica-obrigatoria",
                cura="passe chave lógica (<classe>:<slug>) em vez de caminho de sistema de arquivos",
                proximo="busca buscar",
            )
        )


def _montar_endereco(classe_info: ClasseAlcance, slug: str, chave_canonica: str) -> str:
    if classe_info.morada == "git" and classe_info.molde:
        return classe_info.molde.replace("<slug>", slug)
    return chave_canonica


def _erro_chave_mal_formada(base: str, cura: str) -> ErroResolucao:
    return ErroResolucao(
        Recusa(
            saida=2,
            codigo="chave-mal-formada",
            onde="chave",
            recebido=base,
            regra="gramatica-da-chave",
            cura=cura,
            proximo="",
        )
    )


def _extrair_ficha_de_classe(base: str) -> tuple[str, str, bool] | None:
    if base.endswith(":") and ":" not in base[:-1]:
        cl = base[:-1]
        if not _RE_CLASSE_VALIDA.fullmatch(cl):
            raise _erro_chave_mal_formada(base, "informe nome de classe válido antes de ':'")
        return "shape", cl, True
    if base.startswith("shape:"):
        cl = base.split(":", 1)[1]
        if not _RE_CLASSE_VALIDA.fullmatch(cl):
            raise _erro_chave_mal_formada(base, "informe shape:<classe> com slug válido")
        return "shape", cl, True
    return None


def _extrair_classe_e_slug(
    verbo: str,
    base: str,
    classe_explicita: str | None,
    vista: VistaAlcance,
) -> tuple[str, str, bool]:
    # 1. Chave só com a classe: `<classe>:` ou `shape:<classe>`
    ficha = _extrair_ficha_de_classe(base)
    if ficha is not None:
        return ficha

    # 2. Chave canônica `<classe>:<slug>`
    if ":" in base:
        if not _RE_CHAVE_CAN.fullmatch(base):
            raise _erro_chave_mal_formada(base, "use chave canônica <classe>:<slug>")
        cl, sl = base.split(":", 1)
        return cl, sl, False

    # 3. Identificador curto `<slug>` ou nome de classe puro
    if not _RE_SLUG_VALIDO.fullmatch(base):
        raise _erro_chave_mal_formada(
            base, "use chave canônica <classe>:<slug> ou identificador curto válido"
        )
    if classe_explicita:
        return classe_explicita, base, False
    if base in vista.classes:
        return "shape", base, True

    alcance = vista.alcance_verbo.get(verbo, frozenset())
    concretas = sorted(c for c in alcance if c != "*")
    if len(concretas) == 1:
        return concretas[0], base, False
    raise ErroResolucao(
        Recusa(
            saida=2,
            codigo="chave-ambigua",
            onde="chave",
            recebido=base,
            regra="classe-obrigatoria-para-verbo-multiclasse",
            cura=f"informe a classe explicitamente; classes aceitas: {', '.join(concretas) or 'todas'}",
            proximo=f"{verbo} ler <classe> {base}",
        )
    )


def resolver_alvo(
    verbo: str,
    chave: str,
    *,
    classe_explicita: str | None = None,
    vista: VistaAlcance | None = None,
) -> tuple[AlvoResolvido, str | None]:
    """Estágios 3 e 4: resolve chave na vista de alcance e aplica portão do verbo antes da morada."""
    v = vista if vista is not None else carregar_vista_alcance()
    _validar_sem_caminho_solto(chave)
    base, membro = _separar_membro(chave)

    classe, slug, eh_ficha_classe = _extrair_classe_e_slug(verbo, base, classe_explicita, v)
    chave_canonica = f"shape:{slug}" if eh_ficha_classe else f"{classe}:{slug}"
    info = v.classes.get(classe)
    if info is None:
        info = ClasseAlcance(
            classe=classe,
            morada="banco",
            verbo_dono="busca",
            universo_fechado=True,
            digest_release=v.digest_release,
        )

    # Portão do verbo (estágio 4a): verbo aceita ato:ler?
    if verbo not in v.verbos_aceitam_ler:
        raise ErroResolucao(
            Recusa(
                saida=2,
                codigo="ato-nao-aceito",
                onde="verbo",
                recebido=verbo,
                regra="verbo-aceita-ato-ler",
                cura=f"o verbo {verbo!r} não aceita o ato ler",
                proximo=f"{info.verbo_dono} ler {chave_canonica}",
            )
        )

    # Portão do verbo (estágio 4b): verbo alcança a classe (antes de abrir qualquer morada)?
    alcance = v.alcance_verbo.get(verbo, frozenset())
    if "*" not in alcance and classe not in alcance:
        raise ErroResolucao(
            Recusa(
                saida=1,
                codigo="classe-fora-do-verbo",
                onde="classe",
                recebido=classe,
                regra="verbo-alcanca-classe",
                cura=f"o verbo {verbo!r} não alcança a classe {classe!r}",
                proximo=f"{info.verbo_dono} ler {chave_canonica}",
            )
        )

    endereco = _montar_endereco(info, slug, chave_canonica)
    alvo = AlvoResolvido(
        chave_pedida=chave,
        chave_canonica=chave_canonica,
        classe=classe,
        morada=info.morada,
        endereco=endereco,
        universo_fechado=info.universo_fechado,
        digest_release=info.digest_release or v.digest_release,
        eh_ficha_da_classe=eh_ficha_classe,
    )
    return alvo, membro
