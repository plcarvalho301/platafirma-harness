"""Adaptador de mesa e caderno — a memória de trabalho da cadeira.

`spec_recuperador.md` §5: contrato = mapa por chave (`arq:0062`); classe exata; carimbo =
`v` no valor; prefixo `mem:*`. §4: chave `mem:<sufixo>:<slot>#<item>`.

**A fonte tem duas metades hoje**, e o adaptador não pode fingir que tem uma (medido em
`bin/mesa`, 20/08/2026):

| metade | onde | chave | versão |
|---|---|---|---|
| item de mesa | Postgres `sessao.mesa_item` | `mem:<sufixo>:<chapeu>#<id>` | `seq` = id do item |
| prosa de slot | Valkey msg-mem, `mem:<sufixo>:<slot>` | `mem:<sufixo>:<slot>` | `digest` do valor |

A prosa é substrato velho e não carrega `v` — daí `digest` em vez de `seq`. Carimbo por
timestamp seria pior do que nenhum: o próprio §5 rejeita `max(atualizado_em)` no board
porque falha em dois atos no mesmo instante, e a prosa tem só `t`.

**Metade caída não derruba a fonte inteira, e também não passa calada.** Postgres mudo
com Valkey de pé devolve os itens que existem, com `nao-calibrada` e `causa` declarada —
degradação declarada, que é diferente de pacote menor em silêncio.

A chave usa o **sufixo** (`ia`, `ti`), não o slug canônico: é a decisão do dono de
18/08/2026 para `mem:`, `fita:` e `caderno/`. A caixa da fila continua canônica, e
colapsar os dois foi o que partiu a mesa em duas metades.
"""

from __future__ import annotations

import hashlib
import json
import os

from ..envelope import Causa, Cobertura, Item, LinhaFonte, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel, Resultado

HOST = os.environ.get("MEM_REDIS_HOST", "127.0.0.1")
PORTA = int(os.environ.get("MEM_REDIS_PORT", "6380"))  # msg-mem, não a malha
RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))


class AdaptadorMesa(Adaptador):
    fonte = Fonte.MESA
    tem_gold = False

    def __init__(self, sufixo: str | None = None, cliente=None, conexao_pg=None) -> None:
        self.sufixo = (sufixo or os.environ.get("PF_CADEIRA", "")).strip().lower()
        # PF_CADEIRA chega nas duas formas; a chave do substrato é o sufixo.
        if self.sufixo.startswith(("claudinho-", "claudinha-")):
            self.sufixo = self.sufixo.split("-", 1)[1]
        self._cliente = cliente
        self._pg = conexao_pg

    # ---- substratos -----------------------------------------------------------------

    def cliente(self):
        if self._cliente is not None:
            return self._cliente
        try:
            import redis
        except ImportError as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, "módulo `redis` ausente") from e
        try:
            self._cliente = redis.Redis(host=HOST, port=PORTA, decode_responses=True,
                                        socket_timeout=1)
            self._cliente.ping()
        except Exception as e:  # noqa: BLE001
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"{HOST}:{PORTA}") from e
        return self._cliente

    def pg(self):
        """`None` quando a metade de item não responde — quem declara é `busca`."""
        if self._pg is not None:
            return self._pg
        try:
            import psycopg
        except ImportError:
            return None
        try:
            self._pg = psycopg.connect(self._dsn(), connect_timeout=2)
        except Exception:  # noqa: BLE001
            return None
        return self._pg

    @staticmethod
    def _dsn() -> str:
        d = os.environ.get("SESSAO_PG_DSN")
        if d:
            return d
        senha = os.environ.get("SESSAO_PG_PASSWORD", "")
        env = os.path.join(RAIZ, "platafirma-harness", "sessao", ".env")
        if not senha and os.path.isfile(env):
            for linha in open(env, encoding="utf-8"):
                if linha.startswith("SESSAO_PG_PASSWORD="):
                    senha = linha.split("=", 1)[1].strip()
                    break
        porta = os.environ.get("SESSAO_PG_PORT", "5437")
        return f"host=127.0.0.1 port={porta} dbname=sessao user=sessao password={senha}"

    # ---- carimbo --------------------------------------------------------------------

    def _carimbo(self) -> str:
        """As DUAS metades, e é o ponto: carimbo que cobre uma só mente sobre a outra.

        Medido em 20/08/2026 ao gerar o gold (#2309): o Valkey msg-mem não tem hoje
        nenhuma chave `mem:ia:*`, e os sete itens vivos da mesa estão no Postgres. O
        carimbo anterior era só o digest das chaves do Valkey — logo, `e3b0c44298fc`, o
        sha do vazio, CONSTANTE enquanto a mesa mudava. Com a chave de cache do §9
        (`rec:<fonte>:<carimbo>:...`, #2308) isso serve mesa velha para sempre, que é o
        modo de falha que o #2307 nomeia: carimbo que não anda é pior que carimbo ausente.

        Forma: `<max(id)>/<contagem>` da metade de item, mais o digest das chaves de prosa.
        Metade muda, carimbo muda. Metade caída vira `?`, e o carimbo diz que não sabe em
        vez de fingir que não mudou.
        """
        return f"i:{self._carimbo_item()} p:{self._carimbo_prosa()}"

    def _carimbo_item(self) -> str:
        con = self.pg()
        if con is None:
            return "?"
        try:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(max(id), 0), count(*) FROM sessao.mesa_item "
                    "WHERE lower(cadeira) LIKE %s AND esvaziado_em IS NULL",
                    [f"%{self.sufixo}"],
                )
                maior, quantos = cur.fetchone()
            return f"{maior}/{quantos}"
        except Exception:  # noqa: BLE001 — metade muda declara `?`, não derruba a fonte
            return "?"

    def _carimbo_prosa(self) -> str:
        try:
            rc = self.cliente()
            chaves = sorted(rc.keys(f"mem:{self.sufixo}:*"))
        except FonteIndisponivel:
            return "?"
        return hashlib.sha256("|".join(str(c) for c in chaves).encode()).hexdigest()[:12]

    # ---- busca ----------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        return self._prosa(alvo, texto) + self._itens_de_mesa(alvo, filtros, texto)[0]

    def busca(self, alvo: str = "", filtros: dict | None = None, k: int = 8,
              texto: str = "secao") -> Resultado:
        if not self.sufixo:
            raise FonteIndisponivel(Causa.SEM_CONCESSAO, "mesa é privada da cadeira (arq:0041)")
        prosa = self._prosa(alvo, texto)
        itens_mesa, metade_muda = self._itens_de_mesa(alvo, filtros, texto)
        itens = (prosa + itens_mesa)[:k]
        return Resultado(
            linha=LinhaFonte(
                fonte=self.fonte,
                cobertura=self.cobertura_com_item() if itens else Cobertura.VAZIA,
                carimbo=self._carimbo(),
                causa=Causa.SEM_ROTA if metade_muda else None,
            ),
            itens=itens,
        )

    def _prosa(self, alvo: str, texto: str) -> list[Item]:
        rc = self.cliente()
        padrao = f"mem:{self.sufixo}:{alvo}" if alvo else f"mem:{self.sufixo}:*"
        itens = []
        for chave in sorted(rc.keys(padrao)):
            bruto = rc.get(chave)
            if bruto is None:
                continue
            try:
                corpo = json.loads(bruto).get("x", "")
            except (ValueError, AttributeError):
                corpo = bruto
            proc = Procedencia(
                fonte=Fonte.MESA,
                chave=chave,
                versao=Versao(tipo=VersaoTipo.DIGEST,
                              valor=hashlib.sha256(str(bruto).encode()).hexdigest()[:12]),
            )
            if texto == "nenhum":
                itens.append(Item(procedencia=proc, ref=chave))
            else:
                if texto == "trecho":
                    corpo = corpo[:800] + ("\n[…]" if len(corpo) > 800 else "")
                itens.append(Item(procedencia=proc, conteudo=corpo))
        return itens

    def _itens_de_mesa(self, alvo: str, filtros: dict | None,
                       texto: str) -> tuple[list[Item], bool]:
        """(itens, metade_muda). `metade_muda` é o que vira `causa` na linha."""
        con = self.pg()
        if con is None:
            return [], True
        filtros = filtros or {}
        # `esvaziado_em`, e não `feito_em`: a coluna do esquema vivo chama-se assim
        # (medido em `information_schema` em 20/08/2026). A versão anterior levantava
        # `UndefinedColumn`, que o `except` abaixo transformava em `sem-rota` — a fonte
        # aparecia CAÍDA com o Postgres de pé, e nada acusava. Achado ao gerar o gold
        # da mesa (#2309), que é para o que o gold serve.
        sql = ("SELECT id, chapeu, ato, alvo, texto FROM sessao.mesa_item "
               "WHERE lower(cadeira) LIKE %s AND esvaziado_em IS NULL")
        args: list = [f"%{self.sufixo}"]
        if alvo:
            sql += " AND chapeu = %s"
            args.append(alvo)
        if filtros.get("ato"):
            sql += " AND ato = %s"
            args.append(filtros["ato"])
        sql += " ORDER BY id"
        try:
            with con.cursor() as cur:
                cur.execute(sql, args)
                linhas = cur.fetchall()
        except Exception:  # noqa: BLE001
            return [], True
        itens = []
        for id_, chapeu, ato, alvo_item, corpo in linhas:
            proc = Procedencia(
                fonte=Fonte.MESA,
                chave=f"mem:{self.sufixo}:{chapeu}#{id_}",
                versao=Versao(tipo=VersaoTipo.SEQ, valor=str(id_)),
            )
            cabeca = f"#{id_} [{chapeu}] {ato} → {alvo_item}"
            if texto == "nenhum":
                itens.append(Item(procedencia=proc, ref=cabeca))
            else:
                itens.append(Item(procedencia=proc,
                                  conteudo=f"{cabeca}\n{corpo or ''}".rstrip()))
        return itens, False
