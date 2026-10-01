"""Contrato de `bin/mesa`.

(1) `mesa ver` mostra a anotação de mesa (substrato Valkey/`mesa anota`) como "anotação
    (expira em Xh)", nunca com a palavra "caderno" no rótulo (card #3141).
(2) `mesa anota` acrescenta, nunca apaga sem avisar, e respeita a guarda de fita (#3166).
(3) O caderno por entrada (arq:0120, #3218): a escrita declara categoria e o campo dela e
    recusa, com a instrução, o que falta, o que passa de 600 caracteres e o que leva o
    chapéu acima de 1.500 tokens vigentes; o corpo serve só o vigente; a aresta pede as duas
    pontas na forma da curadoria e conta por fita; a colheita roda vazia no primeiro dia; o
    veredito é só da curadoria; o legado separa vazio, órfão e cabeça.

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


def test_escrita_alem_do_teto_recusa_e_mostra_as_vigentes(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    # 9 lições de ~600 caracteres medem ~1.400 tokens (len/4); a décima passa de 1.500.
    estado["entradas"] = [_entrada(i, texto=f"lição {i} " + "y" * 580) for i in range(1, 10)]
    rc = mesa.ato_escrever(_args_escrever(licao="z" * 580, caso="#3218"))
    erro = capsys.readouterr().err
    assert rc == 4
    assert "recuso" in erro and "1500" in erro and "medida de teste" in erro
    assert "mesa tombar" in erro and "mesa retirar" in erro
    assert "[c1]" in erro
    assert estado["inseridas"] == []


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


def test_licao_sem_confirmacao_ha_90_dias_sai_a_revisar(monkeypatch):
    mesa = carrega_mesa()
    velha = _entrada(1, confirmada_em=datetime(2026, 6, 1, 15, tzinfo=timezone.utc))
    nova = _entrada(2)
    assert "a revisar: não confirmada desde 01/06/2026" in mesa._linha(velha, HOJE)
    assert "a revisar" not in mesa._linha(nova, HOJE)


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
    for pedaco in ("2 vigentes", "/1500 tk", "última escrita há 3 h", "1 a revisar",
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


def test_veredito_e_so_da_curadoria(mesa_caderno, capsys):
    mesa, estado = mesa_caderno
    rc = mesa.ato_veredito(argparse.Namespace(de="conceito:a", para="conceito:b", tombar="x",
                                              pendente=False, retirar=None))
    assert rc == 4
    assert "curadoria (dados)" in capsys.readouterr().err
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
