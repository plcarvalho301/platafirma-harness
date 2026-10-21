"""Contrato de `bin/mesa`.

(1) `mesa ver` mostra a anotação de mesa (substrato Valkey/`mesa anota`) como "anotação
    (expira em Xh)", nunca com a palavra "caderno" no rótulo (card #3141).
(2) `mesa anota` acrescenta, nunca apaga sem avisar, e respeita a guarda de fita (#3166).
(3) O caderno por entrada (arq:0120, #3218): a escrita declara categoria e o campo dela e
    recusa, com a instrução, o que falta e o que passa de 600 caracteres; o corpo serve só o
    vigente; a aresta pede as duas pontas na forma da curadoria e conta por fita; a colheita
    roda vazia no primeiro dia; o legado separa vazio, órfão e cabeça.
(4) A poda no código (#3884, Emenda de 19/10/2026): o teto corta o servido, não a escrita,
    na ordem preferência, premissa, lição pela confirmação; `mesa podar` retira, marca o
    tombamento e manda carta assinada pelo bot; a aresta sai tombada para o balde; o veredito
    saiu do caderno.

`bin/mesa` não tem sufixo .py (é despachado por shebang); carregado aqui por
SourceFileLoader, mesmo padrão de bin/_metrica/abertura.py. Teste não lê estado real
(lib/teste_isolado.py): Redis entra por fake mínimo, e o Postgres do caderno entra trocando
as funções de acesso do próprio verbo (`_entradas`, `_insere`, `_evento`, `pg`) por
registradores. O que isto NÃO prova: o SQL contra o banco — esse é provado pelo aceite
embutido na migração 0097 (as recusas no banco, ensaiadas sem gravar) e pela chamada real
depois da promoção, registrada no card.
"""

from __future__ import annotations

import argparse
import io
import json
from datetime import date, datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MESA_PATH = REPO_ROOT / "bin" / "mesa"
HOJE = date(2026, 10, 1)


def carrega_mesa():
    """Importa bin/mesa como módulo (sem sufixo .py, spec_from_file_location não acha
    loader sozinho — passa-se SourceFileLoader explícito, como bin/_metrica/abertura.py)."""
    loader = SourceFileLoader("_mesa", str(MESA_PATH))
    spec = spec_from_loader("_mesa", loader)
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _FakeRedis:
    """Só o que ato_ver usa da conexão: keys(padrao) e get(chave)."""

    def __init__(self, dados: dict[str, str]):
        self._dados = dados

    def keys(self, padrao: str):
        import fnmatch
        return sorted(k for k in self._dados if fnmatch.fnmatch(k, padrao))

    def get(self, chave: str):
        return self._dados.get(chave)

    def delete(self, chave: str):
        return 1 if self._dados.pop(chave, None) is not None else 0


def test_ato_ver_rotulo_anotacao_com_expira_e_sem_a_palavra_caderno(monkeypatch, capsys):
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)  # substrato de item indisponivel

    agora = 2_000_000.0
    monkeypatch.setattr(mesa.time, "time", lambda: agora)
    escrito_ha_46h = agora - 46 * 3600  # TTL 48h; restam 2h
    chave = "mem:mesateste:slotx"
    fake = _FakeRedis({chave: json.dumps({"t": int(escrito_ha_46h), "x": "texto de anotacao"})})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    rc = mesa.ato_ver(argparse.Namespace(slot=None))
    saida = capsys.readouterr().out

    assert rc == 0
    assert "[slotx] anotação (expira em 2 h)" in saida
    assert "texto de anotacao" in saida
    assert "caderno" not in saida
    assert "(prosa, substrato velho)" not in saida


def test_ato_ver_anotacao_vencida_expurga_e_nao_mostra(monkeypatch, capsys):
    """TTL estourado: expurgo físico no ato de servir (regra já existente), não regressão
    desta mudança — só confirma que o rótulo novo não quebrou esse caminho."""
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)

    agora = 2_000_000.0
    monkeypatch.setattr(mesa.time, "time", lambda: agora)
    escrito_ha_49h = agora - 49 * 3600  # TTL 48h: vencida
    chave = "mem:mesateste:slotv"
    fake = _FakeRedis({chave: json.dumps({"t": int(escrito_ha_49h), "x": "velha"})})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    rc = mesa.ato_ver(argparse.Namespace(slot=None))
    saida = capsys.readouterr().out

    assert rc == 0
    assert "slotv" not in saida
    assert chave not in fake._dados  # expurgada de verdade


# --- card #3166: anotar acrescenta, nunca apaga sem avisar -----------------------------

class _FakeRedisComEval(_FakeRedis):
    """Estende _FakeRedis com set/eval, o quanto basta pra exercitar LUA_ANOTA sem Redis
    real -- regra do dono (27/09): teste nao depende de estado real; a suite roda com
    MEM_REDIS_PORT apontado pra porta 9 de proposito (lib/teste_isolado.py). O eval aqui
    espelha linha a linha o script Lua do verbo: prova o contrato que ato_anota espera
    dele (CAS opcional, concatenacao, TTL), nao substitui a leitura do Lua real."""

    def set(self, chave, valor, ex=None):
        self._dados[chave] = valor
        return True

    def eval(self, script, numkeys, *args):
        chave_fita, chave_slot, fid, texto_novo, ttl, ts = args
        if fid and self._dados.get(chave_fita) != fid:
            return 0
        atual = self._dados.get(chave_slot)
        texto_final = texto_novo
        if atual:
            try:
                decodificado = json.loads(atual)
            except ValueError:
                decodificado = None
            if decodificado and decodificado.get("x"):
                texto_final = decodificado["x"] + "\n\n---\n\n" + texto_novo
        self.set(chave_slot, json.dumps({"t": int(ts), "x": texto_final}), ex=ttl)
        return 1


def test_ato_anota_acrescenta_sem_apagar_e_ver_mostra_as_duas(monkeypatch, capsys):
    """O defeito medido em 26 e 27/09 (tres vezes nos cadernos): `mesa anota` reescrevia
    o slot inteiro. Duas anotacoes seguidas no mesmo slot tem de aparecer as DUAS em
    `mesa ver`."""
    mesa = carrega_mesa()
    cad, slot = "mesateste", "acrescimo3166"
    monkeypatch.setenv("PF_CADEIRA", cad)
    fake = _FakeRedisComEval({})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    r1 = mesa.ato_anota(argparse.Namespace(slot=slot, texto="primeira nota", se_fita=None))
    capsys.readouterr()
    assert r1 == 0

    r2 = mesa.ato_anota(argparse.Namespace(slot=slot, texto="segunda nota", se_fita=None))
    capsys.readouterr()
    assert r2 == 0

    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)
    rv = mesa.ato_ver(argparse.Namespace(slot=slot))
    saida = capsys.readouterr().out
    assert rv == 0
    assert "primeira nota" in saida
    assert "segunda nota" in saida


def test_ato_anota_com_fita_errada_descarta_e_nao_acrescenta(monkeypatch, capsys):
    """A guarda de fita (criterio 18 da minuta 0002) segue valendo: ritual de fita velha
    nao acrescenta por cima da fita nova."""
    mesa = carrega_mesa()
    cad, slot = "mesateste", "guardafita3166"
    monkeypatch.setenv("PF_CADEIRA", cad)
    fake = _FakeRedisComEval({f"fita:{cad}": "fita-nova"})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    r = mesa.ato_anota(argparse.Namespace(slot=slot, texto="nota tardia", se_fita="fita-velha"))
    erro = capsys.readouterr().err
    assert r == 3
    assert "DESCARTADA" in erro
    assert fake._dados.get(f"mem:{cad}:{slot}") is None


def test_item_novo_conta_os_vivos_de_qualquer_ciclo(monkeypatch, capsys):
    """#2856 linha 91: item de semana anterior ainda vivo dividia o número com o item novo, e
    `mesa fez <n>` apagava o mais recente. O número do novo sai do máximo dos vivos da cadeira."""
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setenv("PF_CHAPEU", "devops")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    cursor = _Cursor([[(22,)]])
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: _Conexao(cursor))
    monkeypatch.setattr(mesa, "fita_registrada", lambda con: None)

    rc = mesa.ato_item(argparse.Namespace(chapeu=None, ato="retomar", alvo="card:1"))

    assert rc == 0
    sql, _ = cursor.feitos[-1]
    subconsulta = sql.split("SELECT", 1)[1]
    assert "max(num)" in subconsulta and "ciclo" not in subconsulta
    assert "item #22 plantado em [devops]" in capsys.readouterr().out


# --- card #3218: o caderno por entrada (arq:0120) ---------------------------------------

class _Cursor:
    """Registra cada execute e devolve, em ordem, as respostas de fetchall/fetchone."""

    def __init__(self, respostas=None):
        self.feitos = []
        self._respostas = list(respostas or [])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.feitos.append((sql, params))

    def fetchall(self):
        return self._respostas.pop(0) if self._respostas else []

    def fetchone(self):
        linhas = self.fetchall()
        return linhas[0] if linhas else None


class _Conexao:
    def __init__(self, cursor):
        self.cursor_ = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self.cursor_


class _CursorExpurgo(_Cursor):
    """O DELETE do expurgo devolve `rowcount`; o resto é a leitura de sempre."""

    def __init__(self, expurgados):
        super().__init__()
        self.rowcount = expurgados


def test_ato_ver_avisa_na_propria_peca_o_item_vencido_que_expurgou(monkeypatch, capsys):
    """#3931: o item com mais de 48 h sai no ato de servir, e o aviso vai em stdout, na peça que a
    abertura captura; em stderr ele se perdia."""
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    cursor = _CursorExpurgo(2)
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: _Conexao(cursor))
    monkeypatch.setattr(mesa, "conn", lambda: _FakeRedis({}))

    rc = mesa.ato_ver(argparse.Namespace(slot=None))
    saida = capsys.readouterr()

    assert rc == 0
    assert "2 item(ns) vencido(s) expurgado(s) por TTL de 48h" in saida.out
    assert saida.err == ""
    delete, params = cursor.feitos[0]
    assert delete.startswith("DELETE FROM sessao.mesa_item") and params[1] == 48


def test_ato_ver_sem_item_vencido_nao_escreve_aviso(monkeypatch, capsys):
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: _Conexao(_CursorExpurgo(0)))
    monkeypatch.setattr(mesa, "conn", lambda: _FakeRedis({}))

    assert mesa.ato_ver(argparse.Namespace(slot=None)) == 0
    saida = capsys.readouterr()

    assert "vencido" not in saida.out and saida.err == ""
    assert "mesa vazia" in saida.out


def test_ato_ver_avisa_na_propria_peca_a_prosa_vencida_que_expurgou(monkeypatch, capsys):
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: None)
    agora = 2_000_000.0
    monkeypatch.setattr(mesa.time, "time", lambda: agora)
    fake = _FakeRedis({"mem:mesateste:slotv": json.dumps({"t": int(agora - 49 * 3600), "x": "velha"})})
    monkeypatch.setattr(mesa, "conn", lambda: fake)

    assert mesa.ato_ver(argparse.Namespace(slot=None)) == 0
    saida = capsys.readouterr()

    assert "1 slot(s) de prosa vencida expurgado(s) por TTL de 48h" in saida.out
    assert saida.err == ""


def _entrada(eid, categoria="licao", estado="vigente", texto="uma lição", chapeu="rh", **campos):
    e = {"id": eid, "cadeira": "mesateste", "chapeu": chapeu, "categoria": categoria,
         "estado": estado, "texto": texto, "caso": None, "dito_em": None, "dito_onde": None,
         "vale_ate": None, "ate_que": None, "de_ponta": None, "para_ponta": None,
         "em_tombamento": False, "candidata": None, "destino": None, "motivo": None,
         "substituida_por": None, "criada_em": datetime(2026, 9, 30, tzinfo=timezone.utc),
         "confirmada_em": datetime(2026, 9, 30, tzinfo=timezone.utc)}
    if categoria == "licao":
        e["caso"] = "#3218"
    e.update(campos)
    return e


def _args_escrever(**kw):
    base = dict(slot="rh", licao=None, preferencia=None, premissa=None, caso=None, dito_em=None,
                onde=None, vale_ate=None, ate_que=None)
    base.update(kw)
    return argparse.Namespace(**base)


def _args_aresta(**kw):
    base = dict(chapeu="rh", de="conceito:contrato-de-dado", para="conceito:linhagem-de-dado",
                para_que="o contrato pede a linhagem de cada campo", quem="cadeira", declarada=False)
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture()
def mesa_caderno(monkeypatch):
    """bin/mesa com o banco do caderno trocado por registradores: `_entradas` devolve o que o
    teste põe em `estado['entradas']`, `_insere` e `_evento` anotam o que gravariam."""
    mesa = carrega_mesa()
    monkeypatch.setenv("PF_CADEIRA", "mesateste")
    monkeypatch.setenv("PF_SESSAO", "sessao-de-teste")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr(mesa, "_hoje", lambda: HOJE)
    monkeypatch.setattr(mesa, "_medidor", lambda: (lambda s: len(s) // 4, "medida de teste"))
    estado = {"entradas": [], "inseridas": [], "eventos": [], "cursor": _Cursor()}
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: _Conexao(estado["cursor"]))
    monkeypatch.setattr(mesa, "_trava_chapeu", lambda *a: None)
    monkeypatch.setattr(mesa, "_entradas", lambda cur, cad, chapeu=None: list(estado["entradas"]))

    def _insere(cur, cad, chapeu, categoria, texto, campos):
        estado["inseridas"].append((cad, chapeu, categoria, texto, dict(campos)))
        return 100 + len(estado["inseridas"])

    def _evento(cur, eid, ato, de, para, porque=None):
        estado["eventos"].append((eid, ato, de, para, porque))

    monkeypatch.setattr(mesa, "_insere", _insere)
    monkeypatch.setattr(mesa, "_evento", _evento)
    return mesa, estado


def test_licao_sem_o_caso_sai_2_com_a_instrucao(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    rc = mesa.ato_escrever(_args_escrever(licao="corte por passagem, uma story por passagem"))
    erro = capsys.readouterr().err
    assert rc == 2
    assert "--caso" in erro and "arq:0120" in erro
    assert estado["inseridas"] == []


def test_entrada_sem_categoria_recusa_e_ensina_as_tres(mesa_caderno, capsys):
    mesa, _ = mesa_caderno
    rc = mesa.ato_escrever(_args_escrever())
    erro = capsys.readouterr().err
    assert rc == 2
    assert "--licao" in erro and "--preferencia" in erro and "--premissa" in erro


def test_caderno_inteiro_em_stdin_nao_se_grava_mais(mesa_caderno, monkeypatch, capsys):
    mesa, estado = mesa_caderno
    monkeypatch.setattr("sys.stdin", io.StringIO("## conhecimento curado\n- tudo junto\n"))
    rc = mesa.ato_escrever(_args_escrever())
    erro = capsys.readouterr().err
    assert rc == 2
    assert "por entrada" in erro
    assert estado["inseridas"] == []


def test_preferencia_sem_onde_e_premissa_alem_de_60_dias_recusam(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    assert mesa.ato_escrever(_args_escrever(preferencia="mapa antes da story",
                                            dito_em="2026-10-01")) == 2
    assert "--onde" in capsys.readouterr().err
    longe = (HOJE + timedelta(days=61)).isoformat()
    assert mesa.ato_escrever(_args_escrever(premissa="X está aposentado", vale_ate=longe)) == 2
    assert "60 dias" in capsys.readouterr().err
    assert mesa.ato_escrever(_args_escrever(premissa="X está aposentado", vale_ate=longe,
                                            ate_que="o card fechar")) == 2
    assert estado["inseridas"] == []


def test_entrada_acima_de_600_caracteres_recusa_4(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    rc = mesa.ato_escrever(_args_escrever(licao="x" * 601, caso="#3218"))
    erro = capsys.readouterr().err
    assert rc == 4
    assert "600" in erro
    assert estado["inseridas"] == []


def test_escrita_alem_do_teto_grava_e_corta_o_servido(mesa_caderno, capsys):
    """#3884: o teto corta o servido, não a escrita; a mais antiga espera a poda."""
    mesa, estado = mesa_caderno
    # 9 lições de ~600 caracteres medem ~1.400 tokens (len/4); a décima passa de 1.500.
    estado["entradas"] = [_entrada(i, texto=f"lição {i} " + "y" * 580) for i in range(1, 10)]
    rc = mesa.ato_escrever(_args_escrever(licao="z" * 580, caso="#3218"))
    saida = capsys.readouterr().out
    assert rc == 0
    assert len(estado["inseridas"]) == 1
    assert "c101 escrita (lição)" in saida
    assert "1 entrada(s) fora do servido até a poda" in saida


def test_escrita_dentro_do_teto_grava_entrada_e_evento(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    estado["entradas"] = [_entrada(1)]
    rc = mesa.ato_escrever(_args_escrever(licao="corte por passagem", caso="#3212"))
    saida = capsys.readouterr().out
    assert rc == 0
    assert estado["inseridas"] == [("mesateste", "rh", "licao", "corte por passagem",
                                    {"caso": "#3212"})]
    assert estado["eventos"] == [(101, "escrever", None, "vigente", None)]
    assert "c101 escrita (lição)" in saida and "/1500 tokens" in saida


# --- card #3500: a lição que traz resíduo de episódio avisa, não recusa ------------------

# c16, c203 e c205 do caderno ia/engenharia-de-harness, sem o sufixo «(caso: …)» que o corpo
# acrescenta; c206 reescrita como diretriz (quando X, faça Y, porque Z), com o episódio no caso.
LICAO_C16 = ("Trabalho em lote que precisa do encoder roda no processo que já o tem carregado "
             "(o rag-api), tomando a trava de encode da busca por fatia pequena: não há segunda "
             "cópia do modelo em memória e o espaço vetorial é o da pergunta por construção. "
             "Medido: 27 trechos em 2 s em CPU.")
LICAO_C203 = ("Antes de montar o sorteio de um gabarito a partir do log, contar o que o log tem "
              "por campo (ordem_id, sessao_id, origem): 100 de 5.607 linhas tinham ordem_id e o "
              "filtro estrito do padrão deu pool 0. O verbo conta cada exclusão por motivo, e "
              "relaxar vai por flag, nunca em silêncio.")
LICAO_C205 = ("Promover o platafirma-motor recria a stack motor (motor-pg, uns 8 s) sempre que "
              "mexe em deploy/indice/init, que é bind do compose; a stack nova de API vai com "
              "reversão via=up para a promoção do motor não tocá-la.")
LICAO_C206_DIRETRIZ = ("Quando o card faz do dono a fonte de um insumo (frase, necessidade, "
                       "julgamento), confira antes de construir a medida se ele tem como saber; "
                       "pedir o que ele não tem é pedir invenção, e o log já guarda o contexto.")


@pytest.mark.parametrize("texto, trecho", [
    (LICAO_C16, "27 trechos"),
    (LICAO_C203, "5.607 linhas"),
    (LICAO_C205, "8 s"),
    ("A rodada de 05/10 morreu por RAM, na fita o20261013T195717-5ec96a", "05/10"),
    ("Conferir o caso #3349 antes de codar", "#3349"),
    ("O sha 71ef9d4e já estava no ar", "71ef9d4e"),
    ("A rodada o20261013T195717-5ec96a travou", "o20261013T195717-5ec96a"),
])
def test_licao_com_residuo_de_episodio_grava_e_avisa_o_trecho(mesa_caderno, capsys, texto, trecho):
    mesa, estado = mesa_caderno
    rc = mesa.ato_escrever(_args_escrever(licao=texto, caso="#3500"))
    saida = capsys.readouterr()
    assert rc == 0
    assert len(estado["inseridas"]) == 1
    assert "aviso" in saida.err and f"«{trecho}»" in saida.err
    assert "quando X, faça Y, porque Z" in saida.err and "--caso" in saida.err
    assert "escrita (lição)" in saida.out


def test_licao_escrita_como_diretriz_nao_avisa(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    rc = mesa.ato_escrever(_args_escrever(licao=LICAO_C206_DIRETRIZ, caso="#3360"))
    saida = capsys.readouterr()
    assert rc == 0
    assert len(estado["inseridas"]) == 1
    assert saida.err == ""


def test_preferencia_do_dono_com_data_nao_avisa(mesa_caderno, capsys):
    # a data e o campo da palavra dele; so a licao e diretriz
    mesa, estado = mesa_caderno
    rc = mesa.ato_escrever(_args_escrever(preferencia="funde, quebra fina demais (08/10/2026)",
                                          dito_em="2026-10-01", onde="chat, #3340"))
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_substituir_licao_com_residuo_tambem_avisa(mesa_caderno, monkeypatch, capsys):
    mesa, estado = mesa_caderno
    monkeypatch.setattr(mesa, "_entrada_da_cadeira", lambda cur, eid: _entrada(eid, chapeu="rh"))
    args = _args_escrever(caso=None)
    args.id, args.texto = "c7", LICAO_C16
    rc = mesa.ato_substituir(args)
    saida = capsys.readouterr()
    assert rc == 0
    assert "«27 trechos»" in saida.err
    assert "c7 substituída por c101" in saida.out
    args.texto = LICAO_C206_DIRETRIZ
    assert mesa.ato_substituir(args) == 0
    assert capsys.readouterr().err == ""


def test_premissa_com_vale_ate_grava_o_prazo(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    prazo = (HOJE + timedelta(days=30)).isoformat()
    rc = mesa.ato_escrever(_args_escrever(premissa="por ora, carta", vale_ate=prazo))
    capsys.readouterr()
    assert rc == 0
    assert estado["inseridas"][0][4] == {"vale_ate": HOJE + timedelta(days=30), "ate_que": None}


def test_aresta_sem_uma_das_pontas_recusa(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    rc = mesa.ato_aresta(_args_aresta(para=None))
    erro = capsys.readouterr().err
    assert rc == 2
    assert "--de e --para" in erro
    assert estado["cursor"].feitos == []


def test_aresta_com_ponta_fora_da_forma_recusa(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    assert mesa.ato_aresta(_args_aresta(para="obra:nao-e-uuid")) == 2
    assert "o uuid da obra" in capsys.readouterr().err
    assert mesa.ato_aresta(_args_aresta(de="obra:4f0c1c1e-0000-0000-0000-000000000000")) == 2
    assert "fora da forma" in capsys.readouterr().err
    assert estado["cursor"].feitos == []


def test_aresta_para_chapeu_da_propria_cadeira_recusa(mesa_caderno, capsys):
    mesa, _ = mesa_caderno
    rc = mesa.ato_aresta(_args_aresta(para="chapeu:mesateste/governanca"))
    assert rc == 4
    assert "fora da cadeira" in capsys.readouterr().err


def test_aresta_sem_fita_nem_sessao_recusa(mesa_caderno, monkeypatch, capsys):
    mesa, _ = mesa_caderno
    monkeypatch.delenv("PF_SESSAO", raising=False)
    monkeypatch.delenv("PF_FITA", raising=False)
    assert mesa.ato_aresta(_args_aresta()) == 4
    assert "uma vez por fita" in capsys.readouterr().err


def test_aresta_nova_nasce_e_conta_a_fita(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    # respostas: SELECT da vigente (nenhuma), INSERT do uso (contou), count de fitas (1)
    estado["cursor"] = _Cursor([[], [(101,)], [(1,)]])
    rc = mesa.ato_aresta(_args_aresta())
    saida = capsys.readouterr().out
    assert rc == 0
    assert estado["inseridas"][0][2:] == ("aresta", "o contrato pede a linhagem de cada campo",
                                         {"de_ponta": "conceito:contrato-de-dado",
                                          "para_ponta": "conceito:linhagem-de-dado"})
    uso = [p for s, p in estado["cursor"].feitos if "caderno_aresta_uso" in s and "INSERT" in s]
    assert uso and uso[0][1] == "sessao-de-teste"
    assert "contada; 1 fita(s)" in saida


def test_corpo_serve_so_o_vigente(monkeypatch):
    mesa = carrega_mesa()
    monkeypatch.setattr(mesa, "_medidor", lambda: (lambda s: len(s) // 4, "medida de teste"))
    entradas = [
        _entrada(1, texto="VIGENTE-LICAO"),
        _entrada(2, categoria="preferencia", texto="VIGENTE-PREFERENCIA",
                 dito_em=date(2026, 9, 20), dito_onde="fita de 20/09"),
        _entrada(3, estado="retirada", texto="RETIRADA", motivo="duplicata de guia registrar"),
        _entrada(4, estado="substituida", texto="SUBSTITUIDA", substituida_por=1),
        _entrada(5, estado="tombada", texto="TOMBADA", destino="chapeu rh"),
        _entrada(6, categoria="premissa", texto="PREMISSA-VENCIDA", vale_ate=date(2026, 9, 1)),
        _entrada(7, categoria="premissa", texto="PREMISSA-VALIDA", vale_ate=date(2026, 11, 1)),
        _entrada(8, texto="DE-OUTRO-CHAPEU", chapeu="portfolio"),
    ]
    corpo = mesa._corpo_texto("mesateste", "rh", entradas, [], {}, HOJE)
    for dentro in ("VIGENTE-LICAO", "VIGENTE-PREFERENCIA", "PREMISSA-VALIDA", "[c1]", "## lição"):
        assert dentro in corpo
    for fora in ("RETIRADA", "SUBSTITUIDA", "TOMBADA", "PREMISSA-VENCIDA", "DE-OUTRO-CHAPEU"):
        assert fora not in corpo
    todas = mesa._corpo_texto("mesateste", "rh", entradas, [], {}, HOJE, todas=True)
    assert "RETIRADA" in todas and "retirada: duplicata de guia registrar" in todas
    so_premissa = mesa._corpo_texto("mesateste", "rh", entradas, [], {}, HOJE,
                                    categorias=["premissa"])
    assert "PREMISSA-VALIDA" in so_premissa and "VIGENTE-LICAO" not in so_premissa


def test_aresta_fora_do_corpo_servido_e_lida_por_categoria(monkeypatch):
    """#3501: a aresta e coleta da curadoria, nao conduta do chapeu."""
    mesa = carrega_mesa()
    monkeypatch.setattr(mesa, "_medidor", lambda: (lambda s: len(s) // 4, "medida de teste"))
    entradas = [_entrada(1, texto="A-LICAO"),
                _entrada(2, categoria="aresta", texto="A-ARESTA", de_ponta="termo:x",
                         para_ponta="casa:guia/y")]
    corpo = mesa._corpo_texto("mesateste", "rh", entradas, [], {2: 1}, HOJE)
    assert "A-LICAO" in corpo and "A-ARESTA" not in corpo and "## aresta" not in corpo
    so_aresta = mesa._corpo_texto("mesateste", "rh", entradas, [], {2: 1}, HOJE,
                                  categorias=["aresta"])
    assert "A-ARESTA" in so_aresta
    assert "1 aresta(s) acumulando" in mesa._indice_texto(entradas, [], {}, HOJE, 0)


# --- card #3505: o balde de arestas -----------------------------------------------------------
EM = datetime(2026, 10, 13, 16, 0, tzinfo=timezone.utc)
USOS = [(1, "ia", "contexto", "termo:caderno", "casa:adr/arq:0120", "f1", "a regra 'do Sair'", "cadeira", False, EM),
        (1, "ia", "contexto", "termo:caderno", "casa:adr/arq:0120", "f2", "de novo", None, True, EM),
        (2, "dados", "curadoria", "conceito:x", "conceito:y", "f1", "liga x a y", "dono", False, EM)]


def _balde(monkeypatch, no_balde, exec_ok=True):
    mesa = carrega_mesa()
    leitura = _Cursor([USOS])
    escrita = _Cursor([[(1,)], [("f1",), ("f2",)], [(2,)], [("f1",)]])
    conexoes = iter([_Conexao(leitura), _Conexao(escrita)])
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: next(conexoes))
    enviados = []
    monkeypatch.setattr(mesa, "_acervo_exec", lambda sql: (enviados.append(sql) or (exec_ok, "recusa")))
    monkeypatch.setattr(mesa, "_acervo_json", lambda sql: no_balde)
    return mesa, escrita, enviados


def _retiradas(cursor):
    return [p[1] for s, p in cursor.feitos if s.startswith("UPDATE sessao.caderno_entrada")]


def test_balde_copia_confere_e_so_entao_tomba(monkeypatch, capsys):
    mesa, escrita, enviados = _balde(monkeypatch, [[1, "f1"], [1, "f2"], [2, "f1"]])
    assert mesa.ato_balde(argparse.Namespace(plano=False)) == 0
    sql = enviados[0]
    assert "ON CONFLICT ON CONSTRAINT observacao_aresta_origem_uq DO NOTHING" in sql
    assert "'a regra ''do Sair'''" in sql, "para que livre com aspa dobrada"
    assert "'cadeira', true" in sql, "quem nulo vira cadeira"
    assert _retiradas(escrita) == [1, 2]
    # #3884: o balde e a morada da aresta; ela sai tombada, com o balde por destino
    assert all("estado = 'tombada'" in s and p[0] == mesa.DESTINO_BALDE
               for s, p in escrita.feitos if s.startswith("UPDATE"))
    eventos = [s for s, _ in escrita.feitos if "caderno_evento" in s]
    assert len(eventos) == 2
    assert all("'tombar', 'vigente', 'tombada'" in s for s in eventos)
    assert ("3 uso(s) conferido(s) no balde; 2 aresta(s) tombada(s) → acervo.observacao_aresta"
            in capsys.readouterr().out)


def test_uso_que_nao_chegou_ao_balde_segura_a_entrada(monkeypatch, capsys):
    mesa, escrita, _ = _balde(monkeypatch, [[1, "f1"], [2, "f1"]])
    assert mesa.ato_balde(argparse.Namespace(plano=False)) == 0
    assert _retiradas(escrita) == [2], "c1 tem uso f2 fora do balde: fica para a próxima"
    assert "1 ficou(aram) para a próxima passada" in capsys.readouterr().out


def test_acervo_recusou_nada_sai_do_caderno(monkeypatch, capsys):
    mesa, escrita, _ = _balde(monkeypatch, [], exec_ok=False)
    assert mesa.ato_balde(argparse.Namespace(plano=False)) == 3
    assert escrita.feitos == []
    assert "nada saiu do caderno" in capsys.readouterr().err


def test_plano_nao_escreve(monkeypatch, capsys):
    mesa, escrita, enviados = _balde(monkeypatch, [])
    assert mesa.ato_balde(argparse.Namespace(plano=True)) == 0
    assert enviados == [] and escrita.feitos == []
    assert "3 uso(s) de 2 aresta(s) iriam ao balde" in capsys.readouterr().out


def test_colheita_conta_o_balde_na_forma_das_linhas():
    mesa = carrega_mesa()
    bruto = [[1, "ia", "contexto", "termo:caderno", "casa:adr/arq:0120", "f1", "pq", "cadeira",
              False, "2026-10-13T16:00:00+00:00"]]
    linhas = mesa._usos_do_balde(ler=lambda sql: bruto)
    assert linhas == [(1, "ia", "contexto", "termo:caderno", "casa:adr/arq:0120", False, None, "f1",
                       "pq", "cadeira", False, EM)]
    caderno = [(5, "dados", "curadoria", "termo:caderno", "casa:adr/arq:0120", False, None, "f7",
                "outro", "cadeira", False, EM)]
    par = mesa._agrega_pares(linhas + caderno)[0]
    assert par["fitas"] == 2 and par["cadeiras"] == ["dados", "ia"] and par["limiar"]
    assert mesa._usos_do_balde(ler=lambda sql: None) is None


# --- card #3884: o teto no servido e a poda por relógio --------------------------------------

def test_corte_serve_preferencia_primeiro_e_licao_pela_confirmacao(monkeypatch):
    mesa = carrega_mesa()
    monkeypatch.setattr(mesa, "_medidor", lambda: (lambda s: len(s) // 4, "medida de teste"))
    # 9 preferências de ~150 tokens (len/4) e duas lições de ~146: cabe a lição mais nova.
    prefs = [_entrada(10 + i, categoria="preferencia", texto=f"PREF{i} " + "p" * 560,
                      dito_em=date(2026, 9, 1 + i), dito_onde="chat") for i in range(9)]
    velha = _entrada(1, texto="VELHA " + "v" * 560,
                     confirmada_em=datetime(2026, 9, 1, tzinfo=timezone.utc))
    nova = _entrada(2, texto="NOVA " + "n" * 560,
                    confirmada_em=datetime(2026, 9, 29, tzinfo=timezone.utc))
    tombando = _entrada(3, texto="TOMBANDO", em_tombamento=True, destino="chapeu:mesateste/rh")
    entradas = [velha, nova, tombando] + prefs
    servidas, fora, tk = mesa._corte(entradas, HOJE)
    assert {e["id"] for e in servidas} == {2} | {p["id"] for p in prefs}
    assert [e["id"] for e in fora] == [1], "a lição confirmada há mais tempo espera a poda"
    assert tk <= mesa.TETO_CHAPEU
    corpo = mesa._corpo_texto("mesateste", "rh", entradas, [], {}, HOJE)
    assert "NOVA" in corpo and "VELHA" not in corpo and "TOMBANDO" not in corpo
    assert "1 fora do servido até a poda" in corpo.splitlines()[0]
    todas = mesa._corpo_texto("mesateste", "rh", entradas, [], {}, HOJE, todas=True)
    assert "## fora do servido pelo teto, até a poda" in todas and "VELHA" in todas
    assert "em tombamento → chapeu:mesateste/rh" in todas
    assert "1 fora do servido até a poda" in mesa._indice_texto(entradas, [], {}, HOJE, 0)


def test_licao_velha_nao_traz_mais_a_marca_a_revisar():
    """#3884: a lição vencida sai pela poda; a cadeira não resolve nada antes de escrever."""
    mesa = carrega_mesa()
    velha = _entrada(1, confirmada_em=datetime(2026, 6, 1, 15, tzinfo=timezone.utc))
    assert "a revisar" not in mesa._linha(velha, HOJE)


def _podar(monkeypatch, entradas, retirar, tombar, envia_ok=True):
    """bin/mesa com a leitura, cada transação e a carta trocadas por registradores."""
    mesa = carrega_mesa()
    monkeypatch.setattr(mesa, "_hoje", lambda: HOJE)
    monkeypatch.setattr(mesa, "_serviveis", lambda cur: list(entradas))
    leitura = _Cursor([[(2, 2)]])
    escrita = _Cursor([[(e["id"],)] for e, _ in retirar])
    cadeiras = sorted({e["cadeira"] for e, _ in tombar})
    por_cadeira = [_Cursor([[(e["id"],)] for e, _ in tombar if e["cadeira"] == c]) for c in cadeiras]
    conexoes = iter([_Conexao(leitura), _Conexao(escrita)] + [_Conexao(c) for c in por_cadeira])
    monkeypatch.setattr(mesa, "pg", lambda *a, **k: next(conexoes))
    vistos, cartas = {}, []

    def decide(es, hoje, conf):
        vistos.update(conf=conf, hoje=hoje, n=len(es))
        return retirar, tombar

    def envia(cadeira, n, corpo):
        cartas.append((cadeira, n, corpo))
        return envia_ok, "20261020T061000-bot-caderno-poda" if envia_ok else "recusa da malha"

    return mesa, escrita, por_cadeira, cartas, vistos, decide, envia


def test_podar_retira_marca_o_tombamento_e_manda_carta_por_cadeira(monkeypatch, capsys):
    vencida = _entrada(1, cadeira="ia", chapeu="contexto")
    par_ia = _entrada(2, cadeira="ia", chapeu="contexto", texto="Fake nasce de retorno real")
    par_dados = _entrada(3, cadeira="dados", chapeu="curadoria", texto="Fake nasce de retorno real")
    retirar = [(vencida, "venceu sem confirmação desde 30/08/2026 (30 dias)")]
    tombar = [(par_ia, "a mesma lição em dados/curadoria c3 (1.00)"),
              (par_dados, "a mesma lição em ia/contexto c2 (1.00)")]
    mesa, escrita, por_cadeira, cartas, vistos, decide, envia = _podar(
        monkeypatch, [vencida, par_ia, par_dados], retirar, tombar)
    rc = mesa.ato_podar(argparse.Namespace(plano=False), decide=decide, envia=envia)
    saida = capsys.readouterr().out
    assert rc == 0
    assert vistos == {"conf": {2: 2}, "hoje": HOJE, "n": 3}
    assert "'retirada'" in escrita.feitos[0][0] and escrita.feitos[0][1][1] == 1
    eventos = [p for s, p in escrita.feitos if "caderno_evento" in s]
    assert eventos == [(1, "retirar", "retirada", "bot:caderno-poda",
                        "venceu sem confirmação desde 30/08/2026 (30 dias)")]
    marca_dados, marca_ia = (c.feitos for c in por_cadeira)
    assert marca_ia[0][1] == ("chapeu:ia/contexto", 2)
    assert marca_dados[0][1] == ("chapeu:dados/curadoria", 3)
    assert marca_ia[1][1][:4] == (2, "tombar", "vigente", "bot:caderno-poda")
    assert [(c, n) for c, n, _ in cartas] == [("dados", 1), ("ia", 1)]
    corpo_ia = cartas[1][2]
    assert "Tito Tesourinha" in corpo_ia and "c2 (contexto)" in corpo_ia
    assert "mesa tombar c<id> --destino" in corpo_ia and "mesa retirar" in corpo_ia
    assert "poda: 1 retirada(s), 2 em tombamento" in saida


def test_podar_plano_so_diz(monkeypatch, capsys):
    vencida = _entrada(1, cadeira="ia", chapeu="contexto")
    mesa, escrita, _, cartas, _, decide, envia = _podar(
        monkeypatch, [vencida], [(vencida, "premissa vencida em 01/09/2026")], [])
    assert mesa.ato_podar(argparse.Namespace(plano=True), decide=decide, envia=envia) == 0
    saida = capsys.readouterr().out
    assert "poda (plano): 1 entrada(s) em 1 caderno(s); 1 a retirar, 0 a tombar" in saida
    assert "retirar ia/contexto/c1: premissa vencida em 01/09/2026" in saida
    assert escrita.feitos == [] and cartas == []


def test_carta_que_nao_sai_desfaz_a_marca_da_cadeira(monkeypatch, capsys):
    par = _entrada(2, cadeira="ia", chapeu="contexto")
    mesa, _, _, cartas, _, decide, envia = _podar(
        monkeypatch, [par], [], [(par, "confirmada 2 vezes")], envia_ok=False)
    assert mesa.ato_podar(argparse.Namespace(plano=False), decide=decide, envia=envia) == 3
    assert "carta não saiu, marca desfeita: ia: recusa da malha" in capsys.readouterr().out
    assert len(cartas) == 1


def test_json_da_poda_traz_so_a_servida_sem_aresta():
    """`mesa caderno --json` (#3498): o que o descansar confere, e so isso."""
    mesa = carrega_mesa()
    entradas = [
        _entrada(1, texto="VIGENTE", candidata="duplicata do cânone guia x"),
        _entrada(2, estado="retirada", texto="RETIRADA"),
        _entrada(3, categoria="premissa", texto="VENCIDA", vale_ate=date(2026, 9, 1)),
        _entrada(4, categoria="aresta", texto="ARESTA", de_ponta="termo:x", para_ponta="casa:guia/y"),
        _entrada(5, texto="OUTRO-CHAPEU", chapeu="portfolio"),
    ]
    todas = mesa._servidas_json(entradas, HOJE)
    assert [e["id"] for e in todas] == [1, 5]
    assert todas[0] == {"id": 1, "chapeu": "rh", "categoria": "licao", "texto": "VIGENTE",
                        "caso": "#3218", "candidata": "duplicata do cânone guia x"}
    assert [e["id"] for e in mesa._servidas_json(entradas, HOJE, "portfolio")] == [5]


def test_indice_conta_vigentes_marcas_e_legado(monkeypatch):
    mesa = carrega_mesa()
    monkeypatch.setattr(mesa, "_medidor", lambda: (lambda s: len(s) // 4, "medida de teste"))
    entradas = [
        _entrada(1, confirmada_em=datetime(2026, 6, 1, tzinfo=timezone.utc)),
        _entrada(2, candidata="duplicata de guia registrar"),
        _entrada(3, categoria="aresta", texto="para quê", de_ponta="conceito:a",
                 para_ponta="conceito:b"),
    ]
    legados = [{"chave_origem": "abertura/mesateste/portfolio/caderno.md", "chapeu": "portfolio",
                "bytes": 10986, "capturado_em": None, "texto": "..."}]
    movimento = {"rh": (datetime(2026, 10, 1, tzinfo=timezone.utc), 2)}
    agora = datetime(2026, 10, 1, 3, tzinfo=timezone.utc).timestamp()
    indice = mesa._indice_texto(entradas, legados, movimento, HOJE, agora)
    linha_rh = next(l for l in indice.splitlines() if l.strip().startswith("rh"))
    for pedaco in ("2 vigentes", "/1500 tk", "última escrita há 3 h",
                   "2 retirada(s) em 7 d", "1 candidata(s)", "1 aresta(s) acumulando"):
        assert pedaco in linha_rh
    assert "legado 10986 B a triar" in indice
    assert indice.rstrip().endswith("(corpo sob demanda: `mesa caderno <chapeu>`)")


def test_agrega_pares_conta_fitas_e_cadeiras_distintas_e_o_limiar():
    mesa = carrega_mesa()
    t = datetime(2026, 10, 1, tzinfo=timezone.utc)
    de, para = "conceito:contrato-de-dado", "conceito:linhagem-de-dado"
    linhas = [
        (1, "dados", "engenharia", de, para, False, None, "f1", "pede linhagem", "cadeira", True, t),
        (1, "dados", "engenharia", de, para, False, None, "f2", "pede linhagem", "dono", False, t),
        (2, "ia", "contexto", de, para, False, None, "f2", "outra relação", "cadeira", False, t),
        (3, "ia", "contexto", "conceito:x", "obra:4f0c1c1e-0000-0000-0000-000000000000", False, None,
         "f9", "só uma", "cadeira", False, t),
    ]
    pares = mesa._agrega_pares(linhas)
    primeiro = pares[0]
    assert (primeiro["de"], primeiro["para"]) == (de, para)
    assert primeiro["fitas"] == 2, "a mesma fita em duas cadeiras conta uma vez"
    assert primeiro["cadeiras"] == ["dados", "ia"]
    assert primeiro["limiar"] is True, "2 cadeiras distintas bastam"
    assert primeiro["declarada"] == 1 and primeiro["marcacoes"] == 3
    assert primeiro["quem"] == {"dono": 1, "cadeira": 2}
    assert primeiro["para_que"] == ["pede linhagem", "outra relação"]
    assert pares[1]["limiar"] is False


def test_cruzamento_so_leva_slug_e_uuid_validos_ao_sql():
    mesa = carrega_mesa()
    pares = [{"de": "conceito:a-b", "para": "conceito:c"},
             {"de": "conceito:a-b", "para": "obra:4f0c1c1e-0000-0000-0000-000000000000"},
             {"de": "termo:o que é isso", "para": "conceito:c"},
             {"de": "conceito:a-b", "para": "casa:adr/arq:0120"}]
    sql = mesa._sql_cruzamento(pares)
    assert "('a-b', 'c')" in sql and "('a-b', '4f0c1c1e-0000-0000-0000-000000000000')" in sql
    assert "o que é isso" not in sql and "arq:0120" not in sql
    assert mesa._sql_cruzamento([{"de": "termo:x", "para": "casa:adr/arq:0120"}]) is None


def test_rotulos_declarados_le_a_coluna_com():
    mesa = carrega_mesa()
    quatro = ("# chapéu\n\n## c) Consulta dirigida\n\n"
              "| quando a pergunta é de | abre para | com | porque |\n|---|---|---|---|\n"
              "| dono, produto | `arquiteturas` | data mesh · contrato de dado | é onde |\n"
              "| custo | `dominio=[\"ia\"]` | — | x |\n\n## d) outra\n| a | b | com | d |\n| 1 | 2 | fora | 4 |\n")
    assert mesa._rotulos_declarados(quatro) == ["data mesh", "contrato de dado"]
    tres = ("## Consulta dirigida\n\n| Quando a pergunta é de | Abre para | Porque |\n"
            "|---|---|---|\n| x | y | z |\n")
    assert mesa._rotulos_declarados(tres) == []


def test_declaradas_sem_uso_casa_pelo_golden_e_declara_o_casamento():
    mesa = carrega_mesa()
    declaradas = {("dados", "engenharia"): ["data mesh", "Contrato de dado"]}
    usados = [("dados", "engenharia", "conceito:contrato-de-dado")]
    golden = [{"slug": "contrato-de-dado", "rotulos": ["contrato de dado"]},
              {"slug": "malha-de-dados", "rotulos": ["malha de dados", "data mesh"]}]
    saida, casamento = mesa._declaradas_sem_uso(declaradas, usados, golden)
    assert casamento.startswith("golden record")
    assert saida[0]["usadas"] == 1
    assert saida[0]["sem_uso"] == [{"rotulo": "data mesh", "conceito": "malha-de-dados",
                                    "no_acervo": True}]
    _, sem_acervo = mesa._declaradas_sem_uso(declaradas, usados, None)
    assert "acervo indisponível" in sem_acervo


def test_colheita_roda_vazia_no_primeiro_dia(mesa_caderno, monkeypatch, capsys):
    mesa, estado = mesa_caderno
    estado["cursor"] = _Cursor([[], []])
    monkeypatch.setattr(mesa, "_acervo_json", lambda sql: [])
    monkeypatch.setattr(mesa, "_declaradas", lambda raiz: {})
    rc = mesa.ato_colheita(argparse.Namespace(janela=15, json=False))
    saida = capsys.readouterr().out
    assert rc == 0
    assert "0 par(es) acumulando" in saida and "lote vazio" in saida
    rc = mesa.ato_colheita(argparse.Namespace(janela=15, json=True))
    lote = json.loads(capsys.readouterr().out)
    assert rc == 0 and lote["pares"] == [] and lote["acervo"] == "ok"


def test_veredito_saiu_do_caderno_e_aponta_o_balde(mesa_caderno, monkeypatch, capsys):
    """#3884: a aresta sai tombada em até uma hora; o veredito mora do lado do balde."""
    mesa, estado = mesa_caderno
    monkeypatch.setenv("PF_CADEIRA", "dados")
    rc = mesa.ato_veredito(argparse.Namespace(de="conceito:a", para="conceito:b", tombar="x",
                                              pendente=False, retirar=None))
    assert rc == 4
    erro = capsys.readouterr().err
    assert "saiu do caderno" in erro and "acervo.observacao_aresta" in erro
    assert estado["cursor"].feitos == []


def test_legado_separa_vazio_orfao_e_cabeca(tmp_path):
    mesa = carrega_mesa()
    raiz = tmp_path / "abertura"
    for caminho, texto in {
        "rh/chapeu.md": "# chapéu", "rh/caderno.md": "## conhecimento curado\n- uma\n",
        "rh2/chapeu.md": "# chapéu", "rh2/caderno.md": "  \n",
        "construcao/caderno.md": "# cópia sem chapéu\n",
    }.items():
        f = raiz / "gestao-estrategica" / caminho
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(texto, encoding="utf-8")
    (raiz / "gestao-estrategica" / "caderno.md").write_text("", encoding="utf-8")
    achados, fora = mesa._cadernos_em_arquivo(str(raiz))
    assert [a[0] for a in achados] == ["abertura/gestao-estrategica/rh/caderno.md"]
    assert achados[0][1:3] == ("gestao-estrategica", "rh")
    assert fora == {"vazio": ["abertura/gestao-estrategica/rh2/caderno.md"],
                    "órfão": ["abertura/gestao-estrategica/construcao/caderno.md"],
                    "cabeça": ["abertura/gestao-estrategica/caderno.md"]}
