"""Adaptador de mesa e caderno — a memória de trabalho da cadeira.

`spec_recuperador.md` §5: contrato = mapa por chave (`arq:0062`); classe exata; carimbo =
`v` no valor; prefixo `mem:*`. §4: chave `mem:<sufixo>:<slot>#<item>`.

**A fonte tem três metades hoje**, e o adaptador não pode fingir que tem uma (medido em
`bin/mesa`, 20/08/2026; o caderno entrou com a #3217):

| metade | onde | chave | versão |
|---|---|---|---|
| item de mesa | Postgres `sessao.mesa_item` | `mem:<sufixo>:<chapeu>#<id>` | `seq` = id do item |
| entrada de caderno | Postgres `sessao.caderno_entrada` | `mem:<sufixo>:<chapeu>#c<id>` | `seq` = id da entrada |
| prosa de slot | Valkey msg-mem, `mem:<sufixo>:<slot>` | `mem:<sufixo>:<slot>` | `digest` do valor |

Do caderno sai só o que `mesa caderno <chapéu>` serve (arq:0120 §6): a entrada vigente, sem a
premissa vencida e sem a aresta, que acumula para a curadoria e não orienta o chapéu. A entrada
não muda de texto (substituir cria outra), por isso o id basta de versão. `filtros["categoria"]`
pede só o caderno; `filtros["ato"]`, só a mesa.

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
from datetime import date, datetime

from ..envelope import Causa, Cobertura, Item, LinhaFonte, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel, Resultado

from .._raizes import instancia

HOST = os.environ.get("MEM_REDIS_HOST", "127.0.0.1")
PORTA = int(os.environ.get("MEM_REDIS_PORT", "6380"))  # msg-mem, não a malha

# A cadeira do caderno é o slug canônico (0097), que pode vir com prefixo; compara-se o sufixo.
_DA_CADEIRA = "lower(regexp_replace(cadeira, '^claudinh[oa]-', '', 'i')) = %s"
# O mesmo fuso da restrição de 60 dias da 0097 e do `mesa caderno`.
_HOJE = "(now() AT TIME ZONE 'America/Sao_Paulo')::date"
_ROTULO = {"licao": "lição", "preferencia": "preferência do dono", "premissa": "premissa"}
_PRAZO_LICAO = 90  # dias sem confirmação até «a revisar» (arq:0120 §7)


def _br(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "?"


def _campo(categoria, caso, dito_em, dito_onde, vale_ate, ate_que) -> str:
    """O campo obrigatório da categoria, como o corpo de `mesa caderno` o mostra."""
    if categoria == "licao":
        return f"caso: {caso}"
    if categoria == "preferencia":
        return f"o dono, {_br(dito_em)}, {dito_onde}"
    return f"vale até {_br(vale_ate)}" if vale_ate else f"até que {ate_que}"


def _arquivo_segredo() -> str:
    """Segredo da instância, lido por nome (desenho #3010 §3): um arquivo por variável em
    `segredos/<stack>/<NOME>`. Nunca `.env` em árvore de repo."""
    return os.path.join(str(instancia()), "segredos", "harness-sessao", "SESSAO_PG_PASSWORD")


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
        arq = _arquivo_segredo()
        if not senha and os.path.isfile(arq):
            with open(arq, encoding="utf-8") as f:
                senha = f.read().strip()
        if not senha:
            # Ausência é falha alta, nunca DSN sem senha; `pg()` a declara como metade caída.
            raise RuntimeError(f"segredo SESSAO_PG_PASSWORD ausente (ambiente e {arq})")
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

        Forma: `<max(id)>/<contagem>` da metade de item, o último evento do caderno com a
        data, mais o digest das chaves de prosa. Metade muda, carimbo muda. Metade caída vira
        `?`, e o carimbo diz que não sabe em vez de fingir que não mudou.
        """
        return f"i:{self._carimbo_item()} c:{self._carimbo_caderno()} p:{self._carimbo_prosa()}"

    def _carimbo_caderno(self) -> str:
        """Todo ato que nasce, marca ou muda uma entrada grava evento (0097), então o maior id de
        evento anda com o caderno. A data entra porque o servido muda sem evento: a premissa
        vencida sai no dia seguinte ao «vale até», e a lição passa a «a revisar» aos 90 dias."""
        con = self.pg()
        if con is None:
            return "?"
        try:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(max(v.id), 0), count(*) FROM sessao.caderno_evento v "
                    "JOIN sessao.caderno_entrada e ON e.id = v.entrada_id WHERE "
                    + _DA_CADEIRA.replace("cadeira", "e.cadeira"),
                    [self.sufixo],
                )
                maior, quantos = cur.fetchone()
            return f"{maior}/{quantos}@{date.today().isoformat()}"
        except Exception:  # noqa: BLE001 — metade muda declara `?`, não derruba a fonte
            return "?"

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
        return (self._prosa_filtrada(alvo, filtros, texto)
                + self._itens_de_mesa(alvo, filtros, texto)[0]
                + self._entradas_de_caderno(alvo, filtros, texto)[0])

    def busca(self, alvo: str = "", filtros: dict | None = None, k: int = 8,
              texto: str = "secao") -> Resultado:
        if not self.sufixo:
            raise FonteIndisponivel(Causa.SEM_CONCESSAO, "mesa é privada da cadeira (arq:0041)")
        prosa = self._prosa_filtrada(alvo, filtros, texto)
        itens_mesa, item_mudo = self._itens_de_mesa(alvo, filtros, texto)
        caderno, caderno_mudo = self._entradas_de_caderno(alvo, filtros, texto)
        itens = (prosa + itens_mesa + caderno)[:k]
        return Resultado(
            linha=LinhaFonte(
                fonte=self.fonte,
                cobertura=self.cobertura_com_item() if itens else Cobertura.VAZIA,
                carimbo=self._carimbo(),
                causa=Causa.SEM_ROTA if item_mudo or caderno_mudo else None,
            ),
            itens=itens,
        )

    def _prosa_filtrada(self, alvo: str, filtros: dict | None, texto: str) -> list[Item]:
        """A prosa não tem categoria: quem pede só o caderno não a recebe."""
        return [] if (filtros or {}).get("categoria") else self._prosa(alvo, texto)

    def _entradas_de_caderno(self, alvo: str, filtros: dict | None,
                             texto: str) -> tuple[list[Item], bool]:
        """(itens, metade_muda) do caderno no banco: só o que `mesa caderno` serve."""
        filtros = filtros or {}
        if filtros.get("ato"):
            return [], False  # filtro de item de mesa: a entrada de caderno não tem ato
        con = self.pg()
        if con is None:
            return [], True
        sql = ("SELECT id, chapeu, categoria, texto, caso, dito_em, dito_onde, vale_ate, ate_que, "
               f"confirmada_em FROM sessao.caderno_entrada WHERE {_DA_CADEIRA} "
               "AND estado = 'vigente' AND categoria <> 'aresta' AND NOT (categoria = 'premissa' "
               f"AND vale_ate IS NOT NULL AND vale_ate < {_HOJE})")
        args: list = [self.sufixo]
        if alvo:
            sql += " AND chapeu = %s"
            args.append(alvo)
        categorias = filtros.get("categoria")
        if categorias:
            if isinstance(categorias, str):
                categorias = [c.strip() for c in categorias.split(",") if c.strip()]
            sql += " AND categoria = ANY(%s)"
            args.append(list(categorias))
        sql += " ORDER BY chapeu, id"
        try:
            with con.cursor() as cur:
                cur.execute(sql, args)
                linhas = cur.fetchall()
        except Exception:  # noqa: BLE001 — metade muda vira `causa` na linha
            return [], True
        hoje = date.today()
        itens = []
        for id_, chapeu, cat, corpo, caso, dito_em, dito_onde, vale_ate, ate_que, conf in linhas:
            proc = Procedencia(
                fonte=Fonte.MESA,
                chave=f"mem:{self.sufixo}:{chapeu}#c{id_}",
                versao=Versao(tipo=VersaoTipo.SEQ, valor=str(id_)),
            )
            cabeca = f"c{id_} [{chapeu}] {_ROTULO.get(cat, cat)}"
            if texto == "nenhum":
                itens.append(Item(procedencia=proc, ref=cabeca))
                continue
            linha = f"{cabeca}: {corpo} ({_campo(cat, caso, dito_em, dito_onde, vale_ate, ate_que)})"
            conf_dia = conf.date() if isinstance(conf, datetime) else conf
            if cat == "licao" and conf_dia and (hoje - conf_dia).days > _PRAZO_LICAO:
                linha += f" · a revisar: não confirmada desde {_br(conf_dia)}"
            itens.append(Item(procedencia=proc, conteudo=linha))
        return itens, False

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
        filtros = filtros or {}
        if filtros.get("categoria"):
            return [], False  # filtro de caderno: o item de mesa não tem categoria
        con = self.pg()
        if con is None:
            return [], True
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
