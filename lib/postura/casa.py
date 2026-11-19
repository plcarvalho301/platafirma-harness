"""As ligações e processos do schema casa que a composição e a abertura leem, do banco próprio da casa (`casa-db`):
postura-preferencial, da persona à postura que é o perfil dela; ativa, do cenário à circunstância; e processos_de_rotina,
os processos gravados com entrega rotina, os gatilhos que os disparam e as capacidades que produzem. Só leitura.

O banco vem das variáveis CASA_PG_* (com fallback para POSTGRES_*), as mesmas da peça casa (`ambiente: banco-casa`). Sem banco,
quem chama decide: o perfil ainda se lê da linha «Postura preferencial» da persona; a ligação ativa não tem outra fonte.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from urllib.parse import quote


class SemBanco(Exception):
    """O banco da casa não respondeu."""


@dataclass(frozen=True)
class FichaDeProcesso:
    chave: str
    gatilhos: tuple[str, ...] = ()
    produz: tuple[str, ...] = ()
    classe: str = ""
    conteudo: str = ""

    def __post_init__(self) -> None:
        g_bruto: Iterable[str] | str = self.gatilhos
        p_bruto: Iterable[str] | str = self.produz
        g_tup = (g_bruto,) if isinstance(g_bruto, str) else tuple(g for g in (g_bruto or ()) if g)
        p_tup = (p_bruto,) if isinstance(p_bruto, str) else tuple(p for p in (p_bruto or ()) if p)
        classe = self.classe or (self.chave.split(":", 1)[0] if ":" in self.chave else "")
        object.__setattr__(self, "gatilhos", g_tup)
        object.__setattr__(self, "produz", p_tup)
        object.__setattr__(self, "classe", classe)

    @property
    def slug(self) -> str:
        return self.chave.split(":", 1)[1] if ":" in self.chave else self.chave

    @property
    def gatilho(self) -> str | None:
        return self.gatilhos[0] if self.gatilhos else None

    @property
    def resultado(self) -> str | None:
        return self.produz[0] if self.produz else None


_PERFIL = (
    "SELECT d.chave_humana FROM casa.ligacao l "
    "JOIN casa.ficha o ON o.uuid = l.de JOIN casa.shape so ON so.uuid = o.classe "
    "JOIN casa.ficha d ON d.uuid = l.para JOIN casa.shape sd ON sd.uuid = d.classe "
    "JOIN casa.propriedade p ON p.id = l.propriedade "
    "WHERE p.slug = %s AND so.slug = %s AND sd.slug = %s AND o.chave_humana = ANY(%s) AND l.terminou IS NULL")
_ATIVA = (
    "SELECT o.chave_humana, d.chave_humana FROM casa.ligacao l "
    "JOIN casa.ficha o ON o.uuid = l.de JOIN casa.shape so ON so.uuid = o.classe "
    "JOIN casa.ficha d ON d.uuid = l.para JOIN casa.shape sd ON sd.uuid = d.classe "
    "JOIN casa.propriedade p ON p.id = l.propriedade "
    "WHERE p.slug = %s AND so.slug = %s AND sd.slug = %s AND o.chave_humana = ANY(%s) AND l.terminou IS NULL")
_ROTINAS = (
    "SELECT f.chave_humana, s.slug, "
    "COALESCE(array_agg(DISTINCT g.chave_humana) FILTER (WHERE g.chave_humana IS NOT NULL), '{}'), "
    "COALESCE(array_agg(DISTINCT c.chave_humana) FILTER (WHERE c.chave_humana IS NOT NULL), '{}') "
    "FROM casa.ficha f "
    "JOIN casa.shape s ON s.uuid = f.classe "
    "JOIN casa.dado d ON d.ficha = f.uuid AND d.terminou IS NULL "
    "JOIN casa.restricao r ON r.id = d.restricao "
    "JOIN casa.propriedade pe ON pe.id = r.propriedade "
    "LEFT JOIN (casa.ligacao lg JOIN casa.propriedade pg ON pg.id = lg.propriedade AND pg.slug = 'dispara' "
    "           JOIN casa.ficha g ON g.uuid = lg.de JOIN casa.shape sg ON sg.uuid = g.classe AND sg.slug = 'gatilho') "
    "  ON lg.para = f.uuid AND lg.terminou IS NULL "
    "LEFT JOIN (casa.ligacao lp JOIN casa.propriedade pp ON pp.id = lp.propriedade AND pp.slug = 'produz' "
    "           JOIN casa.ficha c ON c.uuid = lp.para) "
    "  ON lp.de = f.uuid AND lp.terminou IS NULL "
    "WHERE pe.slug = %s AND d.valor_de_dicionario = %s "
    "GROUP BY f.chave_humana, s.slug "
    "ORDER BY f.chave_humana")
_CONSTRUIDO_DE = (
    "SELECT sd.slug, d.chave_humana, l.posicao FROM casa.ligacao l "
    "JOIN casa.ficha o ON o.uuid = l.de JOIN casa.shape so ON so.uuid = o.classe "
    "JOIN casa.ficha d ON d.uuid = l.para JOIN casa.shape sd ON sd.uuid = d.classe "
    "JOIN casa.propriedade p ON p.id = l.propriedade "
    "WHERE p.slug = %s AND so.slug = %s AND o.chave_humana = ANY(%s) AND l.terminou IS NULL "
    "ORDER BY l.posicao NULLS LAST, sd.slug, d.chave_humana")


def _dsn(ambiente: Mapping[str, str] | None = None) -> str:
    env = os.environ if ambiente is None else ambiente
    host = env.get("CASA_PG_HOST") or env.get("POSTGRES_HOST") or "127.0.0.1"
    porta = env.get("CASA_PG_PORT") or env.get("POSTGRES_PORT") or "5439"
    usuario = quote(env.get("CASA_PG_USER") or env.get("POSTGRES_USER") or "casa", safe="")
    senha = quote(env.get("CASA_PG_PASSWORD") or env.get("POSTGRES_PASSWORD") or "", safe="")
    base = env.get("CASA_PG_DB") or env.get("POSTGRES_DB") or "casa"
    return f"postgresql://{usuario}:{senha}@{host}:{porta}/{base}"


class Ligacoes:
    def _consulta(self, sql: str, parametros: tuple) -> list:
        try:
            import psycopg
            with psycopg.connect(_dsn(), connect_timeout=3) as conn:
                conn.execute("SET TRANSACTION READ ONLY")
                return conn.execute(sql, parametros).fetchall()
        except Exception as erro:      # noqa: BLE001 — driver ausente, credencial, rede: tudo é «não consegui olhar»
            raise SemBanco(f"{type(erro).__name__}: {str(erro).splitlines()[0][:200] if str(erro) else ''}") from None

    def perfil(self, cadeira: str) -> str | None:
        """O slug da postura que a ligação postura-preferencial da persona aponta, ou None quando ela não tem a ligação."""
        linhas = self._consulta(_PERFIL, ("postura-preferencial", "persona", "postura", [cadeira, f"persona:{cadeira}"]))
        return linhas[0][0].removeprefix("postura:") if linhas else None

    def ativadas(self, cenarios: list[str]) -> dict[str, str]:
        """cenário -> circunstância que ele ativa, para os cenários dados."""
        if not cenarios:
            return {}
        chaves = [c for s in cenarios for c in (s, f"cenario:{s}")]
        linhas = self._consulta(_ATIVA, ("ativa", "cenario", "circunstancia", chaves))
        return {c.removeprefix("cenario:"): circ.removeprefix("circunstancia:") for c, circ in linhas}

    def fichas_existentes(self, chaves: list[str]) -> set[str]:
        """As chaves humanas, entre as dadas, que têm ficha: só essas valem como etiqueta e destinatário da mensagem
        (S4335, decisões 5271 e 5274)."""
        if not chaves:
            return set()
        linhas = self._consulta("SELECT chave_humana FROM casa.ficha WHERE chave_humana = ANY(%s)", (list(chaves),))
        return {c for (c,) in linhas}

    def processos_de_rotina(self) -> list[FichaDeProcesso]:
        """Os processos gravados com entrega rotina, cada um com os gatilhos que o disparam e as capacidades que produz."""
        linhas = self._consulta(_ROTINAS, ("entrega", "rotina"))
        return [
            FichaDeProcesso(
                chave=chave,
                gatilhos=tuple(sorted(gatilhos or ())),
                produz=tuple(sorted(produz or ())),
                classe=classe,
            )
            for chave, classe, gatilhos, produz in linhas
        ]

    def construido_de(self, roteiro: str = "porta") -> list[tuple[str, str] | tuple[str, str, int]]:
        """As peças (classe, chave_humana[, posicao]) ligadas por `construido-de` à ficha do roteiro."""
        slug = roteiro.removeprefix("roteiro:")
        linhas = self._consulta(_CONSTRUIDO_DE, ("construido-de", "roteiro", [slug, f"roteiro:{slug}"]))
        saida: list[tuple[str, str] | tuple[str, str, int]] = []
        for linha in linhas:
            if len(linha) > 2 and linha[2] is not None:
                saida.append((linha[0], linha[1], int(linha[2])))
            else:
                saida.append((linha[0], linha[1]))
        return saida
