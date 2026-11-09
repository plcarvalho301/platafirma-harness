"""Catálogo e publicação transacional; nenhum objeto pronto pela metade."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

    from .publicacao import Catalogo
import csv
import hashlib
import io
import uuid
from datetime import timedelta

from . import Falha, agora, exigir, json_canonico
from .serializacao import canonizar


# O keycloak guarda credencial e conta: o que sai dele só é lido por segurança e TI.
BANCO_RESTRITO = "keycloak"
CADEIRAS_DO_KEYCLOAK = ("seguranca", "ti")

def restricao_das_origens(origens: list[dict], cadeira: str) -> list[str] | None:
    """As cadeiras que podem ler o objeto, ou None quando ele é livre. Receita que lê o
    keycloak só roda em segurança e TI."""
    if any(t.get("banco") == BANCO_RESTRITO for t in origens):
        exigir(cadeira in CADEIRAS_DO_KEYCLOAK, "keycloak-so-seguranca-e-ti", 4)
        return list(CADEIRAS_DO_KEYCLOAK)
    return None

def novo(prefixo: str) -> str:
    return prefixo + "-" + uuid.uuid4().hex


def vencimento(
    guarda: dict, limite: datetime | None = None, instante: datetime | None = None
) -> datetime | None:
    dt = (
        None
        if "ate_descarte" in guarda
        else (instante or agora()) + timedelta(days=guarda.get("dias", 7))
    )
    return min(dt, limite) if dt is not None and limite is not None else (limite or dt)


class Catalogo:
    def __init__(self, conn: Connection, sujeito: str, cadeira: str = "") -> None:
        conn.autocommit = True
        self.conn, self.sujeito, self.cadeira = conn, sujeito, cadeira

    def abrir_execucao(
        self, id: str, ato: str, sessao: str, ordem: str, origem: str | None = None
    ) -> None:
        self.conn.execute(
            "INSERT INTO analise.execucao(id,sujeito,sessao,ordem,ato,origem_id,manifesto) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)",
            (
                id,
                self.sujeito,
                sessao,
                ordem,
                ato,
                origem,
                json_canonico(
                    {"unidade": __import__("os").environ.get("PF_ANALISE_UNIDADE")}
                ),
            ),
        )

    def concluir(
        self, id: str, estado: object, manifesto: dict, causa: str | None = None
    ) -> None:
        self.conn.execute(
            "UPDATE analise.execucao SET estado=%s,manifesto=%s::jsonb,causa=%s,terminada_em=clock_timestamp(),temporarios_ate=clock_timestamp()+interval '7 days' WHERE id=%s AND sujeito=%s",
            (estado, json_canonico(manifesto), causa, id, self.sujeito),
        )

    def objeto(
        self, id: str, *, aceitar_vencido: bool = False, so_dono: bool = False
    ) -> dict:
        from psycopg.rows import dict_row

        tipo = (
            "base"
            if id.startswith("bs-")
            else "resultado"
            if id.startswith("rs-")
            else None
        )
        exigir(tipo, "identificador-desconhecido")
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM analise." + tipo + " WHERE id=%s", (id,))
            obj = cur.fetchone()
        exigir(obj, "identificador-desconhecido")
        exigir(
            obj["sujeito"] == self.sujeito or (not so_dono and self._entregue(id)),
            "acesso-negado",
            4,
        )
        restrita = (obj["manifesto"] or {}).get("restrita_a")
        exigir(so_dono or not restrita or self.cadeira in restrita, "acesso-negado", 4)
        exigir(
            aceitar_vencido or obj["expires_at"] is None or obj["expires_at"] > agora(),
            "objeto-vencido",
            5,
        )
        return {**obj, "tipo": tipo}

    def _entregue(self, id: str) -> bool:
        """O objeto foi entregue a este sujeito, ou a todo sujeito autorizado («*»)."""
        return (
            self.conn.execute(
                "SELECT 1 FROM analise.entrega WHERE objeto_id=%s AND sujeito IN (%s,'*')",
                (id, self.sujeito),
            ).fetchone()
            is not None
        )

    def entregar(self, id: str, destino: str) -> dict:
        """Só quem gerou o objeto o entrega, e só enquanto ele vive."""
        import re

        obj = self.objeto(id, so_dono=True)
        exigir(
            destino == "*" or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,80}", destino),
            "destino-invalido",
        )
        self.conn.execute(
            "INSERT INTO analise.entrega(objeto_id,sujeito,entregue_por) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
            (id, destino, self.sujeito),
        )
        return {"estado": "entregue", "expires_at": obj["expires_at"]}

    def execucao(self, id: str) -> dict:
        from psycopg.rows import dict_row

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM analise.execucao WHERE id=%s", (id,))
            ex = cur.fetchone()
        exigir(ex, "identificador-desconhecido")
        exigir(ex["sujeito"] == self.sujeito, "acesso-negado", 4)
        exigir(
            ex["temporarios_ate"] is None or ex["temporarios_ate"] > agora(),
            "execucao-vencida",
            5,
        )
        exigir(ex["estado"] in {"pronta", "divergente"}, "execucao-incompleta", 5)
        for k in ("base_id", "resultado_id"):
            obj = ex["manifesto"].get(k)
            if obj:
                self.objeto(obj)
        return ex

    def listar(self, tipo: str) -> list[dict]:
        from psycopg.rows import dict_row

        tabela = {"bases": "base", "resultados": "resultado", "execucoes": "execucao"}[
            tipo
        ]
        with self.conn.cursor(row_factory=dict_row) as cur:
            if tabela == "execucao":
                cur.execute(
                    "SELECT id,estado,temporarios_ate AS expires_at FROM analise.execucao WHERE sujeito=%s ORDER BY iniciada_em DESC",
                    (self.sujeito,),
                )
            else:
                cur.execute(
                    "SELECT id,expires_at FROM analise."
                    + tabela
                    + " WHERE sujeito=%s AND (expires_at IS NULL OR expires_at>clock_timestamp()) ORDER BY id",
                    (self.sujeito,),
                )
            return cur.fetchall()

    def publicar(
        self,
        id: str,
        receita: dict,
        slug: str,
        saida: Path,
        manifesto: dict,
        base: dict | None = None,
        antes_de_pronto: Callable[[], None] | None = None,
    ) -> str:
        from .manifesto import fase

        # O estado pronto só fica visível quando as medidas finais também estão
        # nos dois catálogos. A transação interna é um savepoint desta.
        with self.conn.transaction():
            with fase(manifesto, "publicar") as medida:
                objeto = self._publicar(
                    id, receita, slug, saida, manifesto, base, antes_de_pronto
                )
                medida["bytes"] = sum(
                    saida.get("bytes", 0) for saida in manifesto["saidas"].values()
                )
            tabela = "base" if base is None else "resultado"
            self.conn.execute(
                "UPDATE analise." + tabela + " SET manifesto=%s::jsonb WHERE id=%s AND sujeito=%s",
                (json_canonico(manifesto), objeto, self.sujeito),
            )
            self.concluir(id, "pronta", manifesto)
        return objeto

    def _publicar(
        self,
        id: str,
        receita: dict,
        slug: str,
        saida: Path,
        manifesto: dict,
        base: dict | None = None,
        antes_de_pronto: Callable[[], None] | None = None,
    ) -> str:
        from psycopg import sql

        objeto = novo("bs" if receita["tipo"] == "preparacao" else "rs")
        guarda = receita.get("guarda", {"dias": 7})
        exp = vencimento(guarda, base["expires_at"] if base else None)
        manifesto.update(
            {"expires_at": exp.isoformat() if exp else None, "guarda": guarda}
        )
        manifesto["base_id" if base is None else "resultado_id"] = objeto
        esperados = {t["nome"] + ".csv" for t in receita["saidas"].get("tabelas", [])}
        esperados |= {
            (p if isinstance(p, str) else p["nome"]) + ".png"
            for p in receita["saidas"].get("projecoes", [])
        }
        reais = set()
        for p in saida.iterdir():
            exigir(
                p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1,
                "saida-nao-regular",
                4,
            )
            reais.add(p.name)
        exigir(reais <= esperados, "saida-nao-declarada", 4)
        exigir(esperados <= reais, "saida-declarada-ausente", 4)
        tabelas = []
        manifesto["saidas"] = {}
        for t in receita["saidas"].get("tabelas", []):
            c = canonizar(saida / (t["nome"] + ".csv"), t, receita["serializacao"])
            manifesto["saidas"][t["nome"]] = {
                k: v for k, v in c.items() if k != "conteudo"
            }
            tabelas.append((t, c))
        n = next(
            (c["linhas"] for t, c in tabelas if t["nome"] == "turnos"),
            tabelas[0][1]["linhas"] if tabelas else 0,
        )
        tipos = {
            "texto": "text",
            "uuid": "uuid",
            "inteiro": "bigint",
            "real": "numeric",
            "decimal": "numeric",
            "instante": "timestamptz",
            "data": "date",
            "booleano": "boolean",
        }
        with self.conn.transaction():
            for t, c in tabelas:
                fisica = "t_" + uuid.uuid4().hex
                definicoes = sql.SQL(",").join(
                    sql.SQL("{} {}").format(
                        sql.Identifier(col["nome"]), sql.SQL(tipos[col["tipo"]])
                    )
                    for col in t["colunas"]
                )
                self.conn.execute(
                    sql.SQL("CREATE TABLE analise.{} ({})").format(
                        sql.Identifier(fisica), definicoes
                    )
                )
                rows = list(csv.reader(io.StringIO(c["conteudo"].decode())))[1:]
                with self.conn.cursor() as cur:
                    stmt = sql.SQL("INSERT INTO analise.{} VALUES ({})").format(
                        sql.Identifier(fisica),
                        sql.SQL(",").join(sql.Placeholder() for _ in t["colunas"]),
                    )
                    cur.executemany(
                        stmt,
                        [
                            tuple(
                                None if v == str(receita["serializacao"]["nulo"]) else v
                                for v in row
                            )
                            for row in rows
                        ],
                    )
                self.conn.execute(
                    "INSERT INTO analise.tabela(objeto_id,nome,fisica,colunas,ordem,linhas,sha256,bytes) VALUES(%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)",
                    (
                        objeto,
                        t["nome"],
                        fisica,
                        json_canonico(t["colunas"]),
                        json_canonico(t["ordem"]),
                        c["linhas"],
                        c["sha256"],
                        c["bytes"],
                    ),
                )
            for p in receita["saidas"].get("projecoes", []):
                nome = p if isinstance(p, str) else p["nome"]
                from .projecao import canonizar_png
                imagem=canonizar_png(saida/(nome+".png"))
                conteudo=imagem["conteudo"]
                sha=imagem["sha256"]
                largura,altura=imagem["dimensoes"]
                manifesto["saidas"][nome]={k:v for k,v in imagem.items() if k!="conteudo"}
                self.conn.execute(
                    "INSERT INTO analise.projecao VALUES(%s,%s,%s,%s,%s,%s)",
                    (objeto, nome, conteudo, sha, largura, altura),
                )
            if base is None:
                self.conn.execute(
                    "INSERT INTO analise.base VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                    (
                        objeto,
                        id,
                        self.sujeito,
                        slug,
                        n,
                        exp,
                        json_canonico(guarda),
                        json_canonico(manifesto),
                    ),
                )
            else:
                manifesto["base_id"] = base["id"]
                self.conn.execute(
                    "INSERT INTO analise.resultado VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                    (
                        objeto,
                        id,
                        base["id"],
                        self.sujeito,
                        slug,
                        exp,
                        json_canonico(guarda),
                        json_canonico(manifesto),
                    ),
                )
            if receita.get("entrega", "todos") != "privada":
                self.conn.execute(
                    "INSERT INTO analise.entrega(objeto_id,sujeito,entregue_por) VALUES(%s,'*',%s) ON CONFLICT DO NOTHING",
                    (objeto, self.sujeito),
                )
            if antes_de_pronto:
                antes_de_pronto()
            self.concluir(id, "pronta", manifesto)
        return objeto

    def descartar(self, id: str) -> None:
        from psycopg import sql

        objeto = self.objeto(id, aceitar_vencido=True, so_dono=True)
        with self.conn.transaction():
            if objeto["tipo"] == "base":
                exigir(
                    not self.conn.execute(
                        "SELECT 1 FROM analise.resultado WHERE base_id=%s", (id,)
                    ).fetchone(),
                    "base-com-resultado-vivo",
                )
            tabelas = self.conn.execute(
                "SELECT fisica FROM analise.tabela WHERE objeto_id=%s", (id,)
            ).fetchall()
            for (t,) in tabelas:
                self.conn.execute(
                    sql.SQL("DROP TABLE IF EXISTS analise.{}").format(sql.Identifier(t))
                )
            self.conn.execute("DELETE FROM analise.entrega WHERE objeto_id=%s", (id,))
            self.conn.execute("DELETE FROM analise.tabela WHERE objeto_id=%s", (id,))
            self.conn.execute("DELETE FROM analise.projecao WHERE objeto_id=%s", (id,))
            self.conn.execute(
                "DELETE FROM analise." + objeto["tipo"] + " WHERE id=%s", (id,)
            )
            # A execução permanece como prova sem conteúdo; o manifesto do objeto sai.
            self.conn.execute(
                "UPDATE analise.execucao SET manifesto='{}'::jsonb,estado='incompleta',causa='descartada' WHERE id=%s",
                (objeto["execucao_id"],),
            )
