"""Adaptador da morada banco: PostgreSQL direto com pf_leitor_ro.

Executa consultas parametrizadas em transação curta
`BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` com
`SET LOCAL statement_timeout`, confere digest de fechamento antes de declarar
inexistência em universo fechado e pagina `listar` por chave de corte
`(ordem, chave) > (%s, %s) ORDER BY ordem ASC, chave ASC LIMIT %s`.
"""
from __future__ import annotations

import contextlib
import json
import unicodedata
from collections.abc import Callable, Sequence
from typing import Any

from ..tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)
from . import ErroMorada

PAPEL_LEITOR = "pf_leitor_ro"

SQL_BEGIN_RO = "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
SQL_SET_TIMEOUT = "SELECT set_config('statement_timeout', %s, true)"

SQL_LER_FICHA = """
SELECT f.uuid::text AS uuid,
       f.chave_humana AS chave,
       c.slug AS classe,
       coalesce(c.fornada::text, '0') AS versao,
       jsonb_build_object(
           'chave', f.chave_humana,
           'classe', c.slug,
           'criada_em', f.criada_em,
           'dados', coalesce((
               SELECT jsonb_object_agg(x.slug, x.valores)
                 FROM (SELECT p.slug,
                              jsonb_agg(coalesce(d.valor, to_jsonb(d.valor_de_dicionario)) ORDER BY d.id) AS valores
                         FROM casa.dado d
                         JOIN casa.restricao r ON r.id = d.restricao
                         JOIN casa.propriedade p ON p.id = r.propriedade
                        WHERE d.ficha = f.uuid AND d.terminou IS NULL
                        GROUP BY p.slug) x), '{}'::jsonb),
           'declaracao', (SELECT jsonb_strip_nulls(to_jsonb(s) - 'uuid' - 'fornada')
                            FROM casa.shape s WHERE s.uuid = f.uuid)
       ) AS corpo
  FROM casa.ficha f
  JOIN casa.shape c ON c.uuid = f.classe
 WHERE f.chave_humana = %s
"""

SQL_LER_OBRA = """
SELECT o.id::text AS chave,
       coalesce(o.versao::text, o.sha256, '0') AS versao,
       o.conteudo AS corpo
  FROM acervo.v_obra_leitura o
 WHERE o.id::text = %s
"""

SQL_LER_SECAO = """
SELECT s.secao_id::text AS chave,
       coalesce(s.versao::text, '0') AS versao,
       s.conteudo AS corpo
  FROM acervo.v_secao_leitura s
 WHERE s.secao_id::text = %s
"""

SQL_DIGEST_CLASSE = """
SELECT coalesce(max(c.fornada::text), '0') AS fornada,
       md5(coalesce(string_agg(f.chave_humana, E'\n' ORDER BY f.chave_humana), '')) AS digest,
       count(*)::int AS total
  FROM casa.ficha f
  JOIN casa.shape c ON c.uuid = f.classe
 WHERE c.slug = %s
"""

SQL_LISTAR_CHAVE_CORTE = """
SELECT 0 AS ordem,
       f.chave_humana AS chave,
       coalesce(
           sh.rotulo,
           dc.rotulo,
           (SELECT d.valor #>> '{}'
              FROM casa.dado d
              JOIN casa.restricao r ON r.id = d.restricao
              JOIN casa.propriedade p ON p.id = r.propriedade AND p.slug = 'rotulo'
             WHERE d.ficha = f.uuid AND d.terminou IS NULL
             LIMIT 1),
           f.chave_humana
       ) AS rotulo,
       coalesce(c.slug, '') AS resumo_curto
  FROM casa.ficha f
  JOIN casa.shape c ON c.uuid = f.classe
  LEFT JOIN casa.shape sh ON sh.uuid = f.uuid
  LEFT JOIN casa.dicionario dc ON dc.uuid = f.uuid
 WHERE c.slug = %s
   AND (%s::text IS NULL OR (0, f.chave_humana) > (%s::int, %s::text))
 ORDER BY ordem ASC, f.chave_humana ASC
 LIMIT %s
"""


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFC", texto).casefold()


def _ordenar_corpo(corpo: Any) -> str:
    if isinstance(corpo, str):
        return corpo
    return json.dumps(corpo, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _mapear_erro_banco(exc: Exception, alvo_desc: str) -> Recusa:
    msg = str(exc).lower()
    nome = type(exc).__name__.lower()
    if "statement timeout" in msg or "canceling statement" in msg or "querycanceled" in nome:
        return Recusa(
            saida=5,
            codigo="tempo-esgotado",
            onde="morada:banco",
            recebido=alvo_desc,
            regra="prazo-da-transacao-banco",
            cura="a consulta ao banco excedeu o prazo da chamada; tente um recorte menor",
            proximo="",
        )
    if (
        "permission denied" in msg
        or "read-only transaction" in msg
        or "insufficientprivilege" in nome
    ):
        return Recusa(
            saida=4,
            codigo="acesso-negado",
            onde="morada:banco",
            recebido=alvo_desc,
            regra="papel-somente-leitura",
            cura=f"o papel {PAPEL_LEITOR} não tem permissão nesta consulta",
            proximo="",
        )
    sqlstate = str(getattr(exc, "sqlstate", "") or "")
    if (
        (sqlstate.startswith(("42", "22")) and sqlstate != "42501")
        or any(
            k in nome
            for k in (
                "undefinedfunction",
                "undefinedtable",
                "undefinedcolumn",
                "syntaxerror",
                "programmingerror",
                "dataerror",
            )
        )
        or "does not exist" in msg
        or "syntax error" in msg
    ):
        return Recusa(
            saida=5,
            codigo="erro-consulta-banco",
            onde="morada:banco",
            recebido=alvo_desc,
            regra="consulta-sql-valida",
            cura=f"consulta SQL rejeitada pelo banco ({type(exc).__name__}); reporte a TI",
            proximo="",
        )
    return Recusa(
        saida=3,
        codigo="morada-sem-resposta",
        onde="morada:banco",
        recebido=alvo_desc,
        regra="conexao-postgresql-direta",
        cura="banco indisponível ou sem conexões livres; tente novamente",
        proximo="",
    )


def _conectar_psycopg(dsn: str) -> Any:
    import psycopg

    return psycopg.connect(dsn, autocommit=False)


class AdaptadorBanco:
    """Adaptador da morada `banco` sobre PostgreSQL direto com papel `pf_leitor_ro`."""

    def __init__(
        self,
        *,
        dsn: str = "",
        fabrica_conexao: Callable[[], Any] | None = None,
        papel: str = PAPEL_LEITOR,
    ) -> None:
        self._dsn = dsn
        self._fabrica = fabrica_conexao
        self._papel = papel

    @property
    def papel(self) -> str:
        return self._papel

    def _abrir_conexao(self, alvo_desc: str) -> Any:
        try:
            if self._fabrica is not None:
                return self._fabrica()
            if not self._dsn:
                raise ConnectionError("DSN PostgreSQL não configurado")
            return _conectar_psycopg(self._dsn)
        except Exception as exc:  # noqa: BLE001
            raise ErroMorada(_mapear_erro_banco(exc, alvo_desc)) from None

    def _executar_em_transacao_ro(
        self,
        alvo_desc: str,
        prazo_ms: int,
        acao: Callable[[Any], Any],
    ) -> Any:
        con = self._abrir_conexao(alvo_desc)
        try:
            with con.cursor() as cur:
                cur.execute(SQL_BEGIN_RO)
                cur.execute(SQL_SET_TIMEOUT, (str(max(1, int(prazo_ms))),))
                resultado = acao(cur)
            con.rollback()
            return resultado
        except ErroMorada:
            with contextlib.suppress(Exception):
                con.rollback()
            raise
        except Exception as exc:  # noqa: BLE001
            with contextlib.suppress(Exception):
                con.rollback()
            raise ErroMorada(_mapear_erro_banco(exc, alvo_desc)) from None
        finally:
            with contextlib.suppress(Exception):
                con.close()

    def _conferir_digest_fechamento(self, cur: Any, alvo: AlvoResolvido) -> str | None:
        if not alvo.universo_fechado or alvo.classe in ("obra", "secao"):
            return None
        cur.execute(SQL_DIGEST_CLASSE, (alvo.classe,))
        linha = cur.fetchone()
        digest_vivo = str(linha[1]) if linha and linha[1] is not None else ""
        if alvo.digest_release and digest_vivo and digest_vivo != alvo.digest_release:
            raise ErroMorada(
                Recusa(
                    saida=3,
                    codigo="digest-divergente",
                    onde="morada:banco",
                    recebido=alvo.chave_pedida,
                    regra="fechamento-consistente-com-release",
                    cura=(
                        f"digest da release ({alvo.digest_release}) diverge do fechamento vivo "
                        f"({digest_vivo}); não é seguro afirmar inexistência"
                    ),
                    proximo=f"busca ler {alvo.chave_pedida}",
                )
            )
        return digest_vivo or alvo.digest_release

    @staticmethod
    def _ler_vista_acervo(cur: Any, alvo: AlvoResolvido, sql: str) -> tuple[str, str]:
        slug = alvo.chave_canonica.split(":", 1)[1] if ":" in alvo.chave_canonica else alvo.chave_canonica
        cur.execute(sql, (slug,))
        row = cur.fetchone()
        if row is None:
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:banco",
                    recebido=alvo.chave_pedida,
                    regra=f"{alvo.classe}-no-acervo",
                    cura=f"{alvo.classe} não encontrada no escopo varrido da biblioteca",
                    proximo=f"busca buscar {alvo.chave_pedida}",
                )
            )
        return str(row[1]), _ordenar_corpo(row[2])

    def ler_objeto(
        self,
        alvo: AlvoResolvido,
        seletor: SeletorParte,
        prazo_ms: int,
    ) -> ObjetoBruto:
        def _ler(cur: Any) -> tuple[str, str]:
            if alvo.classe == "obra":
                return self._ler_vista_acervo(cur, alvo, SQL_LER_OBRA)
            if alvo.classe == "secao":
                return self._ler_vista_acervo(cur, alvo, SQL_LER_SECAO)

            chave_busca = (
                alvo.chave_canonica.split(":", 1)[1]
                if alvo.eh_ficha_da_classe and alvo.chave_canonica.startswith("shape:")
                else alvo.chave_canonica
            )
            cur.execute(SQL_LER_FICHA, (chave_busca,))
            row = cur.fetchone()
            if row is None:
                digest = self._conferir_digest_fechamento(cur, alvo)
                cura = (
                    f"chave {alvo.chave_canonica!r} não existe na classe {alvo.classe!r} "
                    f"(universo fechado, digest={digest})"
                    if digest
                    else f"chave {alvo.chave_canonica!r} não encontrada"
                )
                raise ErroMorada(
                    Recusa(
                        saida=1,
                        codigo="chave-inexistente",
                        onde="morada:banco",
                        recebido=alvo.chave_pedida,
                        regra="existencia-no-fichario",
                        cura=cura,
                        proximo=f"busca consultar --classe {alvo.classe}",
                    )
                )
            return str(row[3]), _ordenar_corpo(row[4])

        versao, texto = self._executar_em_transacao_ro(alvo.chave_pedida, prazo_ms, _ler)
        if seletor.versao_pedida and seletor.versao_pedida != versao:
            raise ErroMorada(
                Recusa(
                    saida=2,
                    codigo="versao-divergente",
                    onde="--versao",
                    recebido=seletor.versao_pedida,
                    regra="versao-vigente-na-morada-banco",
                    cura=f"a versão vigente é {versao}, diferente de {seletor.versao_pedida}",
                    proximo=f"busca ler {alvo.chave_pedida}",
                )
            )
        dados = texto.encode("utf-8")
        return ObjetoBruto(
            alvo=alvo,
            versao=versao,
            dados=dados,
            nome_arquivo=f"{alvo.classe}.json",
            total_bytes=len(dados),
        )

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        del filtros  # filtros de propriedade/ligação entram por consulta específica da shape

        def _listar(cur: Any) -> tuple[str, str, int, list[tuple[int, str, str, str]]]:
            cur.execute(SQL_DIGEST_CLASSE, (classe,))
            cab = cur.fetchone()
            fornada = str(cab[0]) if cab and cab[0] is not None else "0"
            digest = str(cab[1]) if cab and cab[1] is not None else ""
            total = int(cab[2]) if cab and cab[2] is not None else 0

            ult_ordem = int(cursor.ultima_ordem) if cursor is not None else 0
            ult_chave = cursor.ultima_chave if cursor is not None else None
            cur.execute(
                SQL_LISTAR_CHAVE_CORTE,
                (classe, ult_chave, ult_ordem, ult_chave, limite + 1),
            )
            linhas = [
                (int(r[0]), str(r[1]), str(r[2] or ""), str(r[3] or ""))
                for r in cur.fetchall()
            ]
            return fornada, digest, total, linhas

        fornada, digest, total, linhas = self._executar_em_transacao_ro(
            f"listar:{classe}", prazo_ms, _listar
        )
        if termo:
            termo_n = _normalizar(termo)
            linhas = [
                ln for ln in linhas
                if termo_n in _normalizar(ln[1]) or termo_n in _normalizar(ln[2])
            ]

        tem_mais = len(linhas) > limite
        pagina = linhas[:limite]
        itens = tuple(
            {"chave": ch, "rotulo": rot, "resumo_curto": res}
            for _ord, ch, rot, res in pagina
        )
        prox_tupla = (pagina[-1][0], pagina[-1][1]) if (tem_mais and pagina) else None

        mudou: dict[str, str] | None = None
        avisos: list[str] = []
        if cursor is not None and cursor.versao_retrato != fornada:
            mudou = {"de": cursor.versao_retrato, "para": fornada}
            avisos.append("versao_alterada_entre_paginas")

        return PaginaBruta(
            classe=classe,
            versao=fornada,
            digest=digest or None,
            universo_fechado=True,
            total=total,
            itens=itens,
            proxima_tupla=prox_tupla,
            mudou=mudou,
            avisos=tuple(avisos),
        )
