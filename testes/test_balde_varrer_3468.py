"""#3468: `acervo balde varrer <bucket> [--limite n] [--retomar]` — a varredura de integridade do balde.

Sem rede, sem docker, sem MinIO e sem Postgres: o armazém (o que lê o MinIO) e a fila (o que guarda o estado
no banco) são os dois pontos de contato do verbo com o mundo e saem trocados aqui por dublês. A fila falsa
sobrevive de uma chamada à outra do verbo, como o banco sobreviveria ao processo: é isso que a retomada prova.

O que o teste prova: a classificação (ok, ilegível, divergente, ausente, sem comparação), a primeira linha do
retorno, o exit (0 tudo ok, 1 há problema, 5 não olhou tudo), a retomada depois de interrupção, o item em voo de
executor morto que volta à fila, o `--limite`, e o que o SQL da fila promete (reivindica com SKIP LOCKED, só fecha
o item que ainda é do executor, escapa a chave). Não prova o MinIO nem o Postgres de verdade: o primeiro uso é
`--limite` pequeno em produção.
"""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
VARRER = RAIZ / "bin" / "_acervo" / "varrer_balde.py"


@functools.cache
def _mod():
    spec = importlib.util.spec_from_file_location("acervo_varrer_balde", str(VARRER))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo          # o @dataclass do módulo procura o próprio módulo aqui
    spec.loader.exec_module(modulo)
    return modulo


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


OK1, OK2 = _sha(b"conteudo um"), _sha(b"conteudo dois")
ILEGIVEL = _sha(b"o que o disco nao devolve")
DIVERGENTE = _sha(b"o que devia ter sido gravado")
AUSENTE = _sha(b"o que sumiu entre a listagem e a leitura")
CAUSA_ILEGIVEL = "SlowDownRead: Resource requested is unreadable"
VID = "0" * 8 + "-0000-4000-8000-" + "0" * 12


def _cinco() -> dict:
    """Dois ok, um ilegível, um divergente (a chave é o sha256 de outros bytes) e um ausente, nesta ordem."""
    return {
        OK1: ("bytes", b"conteudo um"),
        OK2: ("bytes", b"conteudo dois"),
        ILEGIVEL: ("ilegivel", CAUSA_ILEGIVEL),
        DIVERGENTE: ("bytes", b"bytes que nao sao os da chave"),
        AUSENTE: ("ausente",),
    }


class ArmazemFalso:
    """O que o verbo pede ao MinIO: `listar` e `ler`. A ordem da listagem é a do dicionário."""

    def __init__(self, objetos: dict):
        self.objetos = objetos
        self.lidos: list[str] = []

    def listar(self, bucket, prefixo=""):
        for chave, (tipo, *resto) in self.objetos.items():
            if chave.startswith(prefixo):
                yield chave, len(resto[0]) if tipo == "bytes" else 4096

    def ler(self, bucket, chave, teto_s):
        self.lidos.append(chave)
        tipo, *resto = self.objetos[chave]
        m = _mod()
        if tipo == "bytes":
            return _sha(resto[0]), len(resto[0])
        if tipo == "ilegivel":
            raise m.ObjetoIlegivel(resto[0])
        if tipo == "ausente":
            raise m.ObjetoAusente("NoSuchKey: The specified key does not exist.")
        if tipo == "fora":
            raise m.FonteFora(resto[0])
        raise KeyboardInterrupt


class FilaFalsa:
    """O que o verbo pede ao banco, com a mesma promessa da `FilaPg`: reivindica por posição, só fecha o que
    ainda é do executor. Mora fora da chamada do verbo: é o banco, que sobrevive ao processo."""

    def __init__(self):
        self.varreduras: dict[str, dict] = {}
        self.linhas: dict[str, dict] = {}     # chave -> linha (uma varredura aberta por vez nos testes)
        self._n = 0

    def aberta(self, colecao):
        return next((v for v, d in self.varreduras.items() if d["colecao"] == colecao and d["estado"] == "aberta"),
                    None)

    def abrir(self, colecao, prefixo, quem, itens):
        abandonadas = []
        for v, d in self.varreduras.items():
            if d["colecao"] == colecao and d["estado"] == "aberta":
                d["estado"] = "abandonada"
                abandonadas.append(v)
        self._n += 1
        vid = f"00000000-0000-4000-8000-{self._n:012d}"
        self.varreduras[vid] = {"colecao": colecao, "prefixo": prefixo, "estado": "aberta", "quem": quem}
        self.linhas = {chave: {"posicao": i, "bytes": n, "estado": "pendente", "executor": None, "idade_s": 0,
                               "causa": None, "bytes_lidos": None, "devolucoes": 0}
                       for i, (chave, n) in enumerate(itens, start=1)}
        return vid, abandonadas

    def em_voo(self, vid):
        return [{"chave": c, "executor": r["executor"], "idade_s": r["idade_s"]}
                for c, r in self.linhas.items() if r["estado"] == "em_voo"]

    def devolver(self, vid, chave, executor, *, contar=False):
        r = self.linhas[chave]
        if r["estado"] != "em_voo" or r["executor"] != executor:
            return False
        r.update(estado="pendente", executor=None, idade_s=0)
        r["devolucoes"] += 1 if contar else 0
        return True

    def reivindicar(self, vid, executor):
        for chave, r in sorted(self.linhas.items(), key=lambda kv: kv[1]["posicao"]):
            if r["estado"] == "pendente":
                r.update(estado="em_voo", executor=executor, idade_s=0)
                return chave, r["bytes"]
        return None

    def fechar(self, vid, chave, executor, achado):
        r = self.linhas[chave]
        if r["estado"] != "em_voo" or r["executor"] != executor:
            return False
        r.update(estado=achado.estado, causa=achado.causa, bytes_lidos=achado.bytes_lidos)
        return True

    def concluir(self, vid):
        if not any(r["estado"] in ("pendente", "em_voo") for r in self.linhas.values()):
            self.varreduras[vid]["estado"] = "concluida"

    def resumo(self, vid):
        contagem: dict[str, int] = {}
        for r in self.linhas.values():
            contagem[r["estado"]] = contagem.get(r["estado"], 0) + 1
        problemas = [{"estado": r["estado"], "chave": c, "bytes": r["bytes_lidos"] or r["bytes"], "causa": r["causa"]}
                     for c, r in sorted(self.linhas.items(), key=lambda kv: kv[1]["posicao"])
                     if r["estado"] in ("ilegivel", "divergente", "ausente")]
        d = self.varreduras[vid]
        return {"varredura": vid, "colecao": d["colecao"], "prefixo": d["prefixo"], "estado": d["estado"],
                "contagem": contagem, "problemas": problemas}


def _varre(capsys, armazem, fila, *argv, colecao="firma"):
    rc = _mod().main([colecao, *argv], armazem=armazem, fila=fila, executor="host-do-teste:1:aaaa")
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


# --- a classificação e o retorno ----------------------------------------------------------------

def test_cinco_objetos_classifica_cada_um_e_sai_1(capsys):
    armazem, fila = ArmazemFalso(_cinco()), FilaFalsa()
    rc, out, err = _varre(capsys, armazem, fila)
    assert rc == 1, err
    linhas = out.splitlines()
    assert linhas[0].startswith("balde firma: 5 lidos, 2 ok, 1 ilegíveis, 1 divergentes, 1 ausentes"), linhas[0]
    problemas = [x for x in linhas[1:] if x.startswith("  ")]
    assert len(problemas) == 3, out
    ileg = next(x for x in problemas if ILEGIVEL in x)
    assert ileg.split()[0] == "ilegivel" and f"acervo/{ILEGIVEL}" in ileg and "4096 B" in ileg
    assert CAUSA_ILEGIVEL in ileg
    dive = next(x for x in problemas if DIVERGENTE in x)
    assert dive.split()[0] == "divergente" and _sha(b"bytes que nao sao os da chave") in dive
    assert "≠" in dive and f"{len(b'bytes que nao sao os da chave')} B" in dive
    ause = next(x for x in problemas if AUSENTE in x)
    assert ause.split()[0] == "ausente" and "NoSuchKey" in ause
    assert OK1 not in out and OK2 not in out
    assert armazem.lidos == [OK1, OK2, ILEGIVEL, DIVERGENTE, AUSENTE]     # um por vez, na ordem da listagem


def test_balde_todo_ok_sai_0_e_a_varredura_fecha(capsys):
    objetos = {k: v for k, v in _cinco().items() if k in (OK1, OK2)}
    fila = FilaFalsa()
    rc, out, err = _varre(capsys, ArmazemFalso(objetos), fila)
    assert rc == 0, err
    assert out.splitlines()[0].startswith("balde firma: 2 lidos, 2 ok, 0 ilegíveis, 0 divergentes, 0 ausentes")
    assert [d["estado"] for d in fila.varreduras.values()] == ["concluida"]


def test_chave_que_nao_e_sha256_le_nao_compara_e_diz(capsys):
    espelho = "espelho/" + "a" * 64 + "/" + "b" * 64 + "/espelho.md"
    objetos = {OK1: ("bytes", b"conteudo um"), espelho: ("bytes", b"# espelho")}
    rc, out, err = _varre(capsys, ArmazemFalso(objetos), FilaFalsa())
    assert rc == 0, err
    assert "1 sem comparação" in out.splitlines()[0]
    assert "não comparada" in out and "não é sha256" in out


def test_json_leva_o_resumo_e_os_problemas(capsys):
    rc, out, _ = _varre(capsys, ArmazemFalso(_cinco()), FilaFalsa(), "--json")
    d = json.loads(out)
    assert rc == 1 and d["contagem"] == {"ok": 2, "ilegivel": 1, "divergente": 1, "ausente": 1}
    assert {p["estado"] for p in d["problemas"]} == {"ilegivel", "divergente", "ausente"} and d["codigo"] == 1


# --- retomada -----------------------------------------------------------------------------------

def test_interrompida_no_meio_volta_a_fila_e_retomar_nao_le_de_novo_o_que_ja_leu(capsys):
    objetos = _cinco()
    interrompe = dict(objetos)
    interrompe[ILEGIVEL] = ("interrompe",)
    fila = FilaFalsa()
    primeiro = ArmazemFalso(interrompe)
    rc, out, err = _varre(capsys, primeiro, fila)
    assert rc == 5, (rc, err)                                    # não olhou tudo: nunca 0
    assert primeiro.lidos == [OK1, OK2, ILEGIVEL]
    assert "interrompida" in err
    assert fila.linhas[ILEGIVEL]["estado"] == "pendente"          # o item em voo voltou, sem esperar lease
    assert "restam 3 pendentes" in out.splitlines()[0]

    segundo = ArmazemFalso(objetos)
    rc, out, err = _varre(capsys, segundo, fila, "--retomar")
    assert rc == 1, err
    assert segundo.lidos == [ILEGIVEL, DIVERGENTE, AUSENTE]       # OK1 e OK2 ficaram no banco, não se leem de novo
    assert out.splitlines()[0].startswith("balde firma: 5 lidos, 2 ok, 1 ilegíveis, 1 divergentes, 1 ausentes")
    assert len(fila.varreduras) == 1                              # a mesma varredura, não uma nova


def test_item_em_voo_de_executor_morto_volta_para_a_fila_e_e_lido(capsys, monkeypatch):
    m = _mod()
    fila = FilaFalsa()
    fila.abrir("firma", "", "t", [(OK1, 11), (OK2, 13)])
    fila.linhas[OK1].update(estado="em_voo", executor=f"{m._maquina()}:424242:dead", idade_s=3)
    monkeypatch.setattr(m, "_pid_existe", lambda pid: False)
    armazem = ArmazemFalso({k: v for k, v in _cinco().items() if k in (OK1, OK2)})
    rc, _, err = _varre(capsys, armazem, fila, "--retomar")
    assert rc == 0, err
    assert armazem.lidos == [OK1, OK2]
    assert fila.linhas[OK1]["devolucoes"] == 1


def test_item_em_voo_de_executor_de_outra_maquina_so_volta_quando_o_lease_vence(capsys):
    fila = FilaFalsa()
    fila.abrir("firma", "", "t", [(OK1, 11)])
    fila.linhas[OK1].update(estado="em_voo", executor="outra-maquina:7:beef", idade_s=5)
    armazem = ArmazemFalso({OK1: ("bytes", b"conteudo um")})
    rc, _, err = _varre(capsys, armazem, fila, "--retomar")
    assert rc == 5 and armazem.lidos == []                        # um executor vivo lê: nunca dois ao mesmo tempo
    assert "outra-maquina:7:beef" in err
    fila.linhas[OK1]["idade_s"] = 10_000                          # lease vencido: o executor está perdido
    rc, _, err = _varre(capsys, armazem, fila, "--retomar")
    assert rc == 0, err
    assert armazem.lidos == [OK1]


def test_retomar_sem_varredura_aberta_e_uso_exit_2(capsys):
    armazem = ArmazemFalso(_cinco())
    rc, _, err = _varre(capsys, armazem, FilaFalsa(), "--retomar")
    assert rc == 2 and "nenhuma varredura aberta" in err and armazem.lidos == []


def test_sem_retomar_a_varredura_aberta_e_abandonada_e_a_nova_comeca_do_zero(capsys):
    fila = FilaFalsa()
    _varre(capsys, ArmazemFalso({**_cinco(), OK2: ("interrompe",)}), fila)
    antiga = next(iter(fila.varreduras))
    armazem = ArmazemFalso(_cinco())
    rc, _, err = _varre(capsys, armazem, fila)
    assert rc == 1 and len(armazem.lidos) == 5
    assert fila.varreduras[antiga]["estado"] == "abandonada" and antiga[:8] in err
    assert len(fila.varreduras) == 2


# --- o que nao e problema do objeto ---------------------------------------------------------------

def test_store_fora_nao_vira_ilegivel_devolve_o_item_e_sai_5(capsys):
    objetos = {OK1: ("bytes", b"conteudo um"), OK2: ("fora", "EndpointConnectionError: sem rota"),
               ILEGIVEL: ("ilegivel", CAUSA_ILEGIVEL)}
    fila = FilaFalsa()
    armazem = ArmazemFalso(objetos)
    rc, out, err = _varre(capsys, armazem, fila)
    assert rc == 5, err
    assert armazem.lidos == [OK1, OK2]                            # parou: não seguiu lendo contra um store fora
    assert fila.linhas[OK2]["estado"] == "pendente" and fila.linhas[OK2]["causa"] is None
    assert "EndpointConnectionError" in err
    assert "0 ilegíveis" in out.splitlines()[0] and "restam 2 pendentes" in out.splitlines()[0]


def test_limite_le_so_n_objetos_e_nunca_sai_0_com_pendentes(capsys):
    fila = FilaFalsa()
    armazem = ArmazemFalso(_cinco())
    rc, out, err = _varre(capsys, armazem, fila, "--limite", "2")
    assert armazem.lidos == [OK1, OK2]
    assert rc == 5, err
    assert "2 lidos, 2 ok" in out.splitlines()[0] and "restam 3 pendentes" in out.splitlines()[0]
    rc, _, _ = _varre(capsys, armazem, fila, "--retomar")
    assert rc == 1 and armazem.lidos == [OK1, OK2, ILEGIVEL, DIVERGENTE, AUSENTE]


def test_balde_sem_objeto_nao_e_verde(capsys):
    rc, _, err = _varre(capsys, ArmazemFalso({}), FilaFalsa())
    assert rc == 5 and "nada olhado" in err


def test_colecao_desconhecida_e_limite_invalido_sao_uso(capsys):
    armazem, fila = ArmazemFalso(_cinco()), FilaFalsa()
    assert _varre(capsys, armazem, fila, colecao="outra")[0] == 2
    assert _varre(capsys, armazem, fila, "--limite", "0")[0] == 2
    assert armazem.lidos == [] and fila.varreduras == {}


# --- a fila de verdade: o SQL ----------------------------------------------------------------------

class PsqlGravador:
    def __init__(self, *respostas):
        self.sqls: list[str] = []
        self.respostas = list(respostas)

    def __call__(self, sql):
        self.sqls.append(sql)
        return self.respostas.pop(0) if self.respostas else ""


def test_reivindicar_usa_skip_locked_escapa_a_chave_e_devolve_o_item():
    m = _mod()
    psql = PsqlGravador('{"chave": "espelho/o\'x", "bytes": 12}\n')
    fila = m.FilaPg(psql)
    assert fila.reivindicar(VID, "h:1:a") == ("espelho/o'x", 12)
    sql = psql.sqls[0].upper()
    assert "FOR UPDATE SKIP LOCKED" in sql and "ESTADO = 'PENDENTE'" in sql
    assert "'H:1:A'" in sql
    assert m.FilaPg(PsqlGravador("")).reivindicar(VID, "h:1:a") is None


def test_fechar_so_vale_se_o_item_ainda_e_do_executor_e_escapa_a_causa():
    m = _mod()
    psql = PsqlGravador("1\n")
    assert m.FilaPg(psql).fechar(VID, "k'1", "h:1:a", m.Achado("ilegivel", "Slow'Down", 7)) is True
    sql = psql.sqls[0]
    assert "executor = 'h:1:a'" in sql and "estado = 'em_voo'" in sql
    assert "'k''1'" in sql and "'Slow''Down'" in sql
    assert m.FilaPg(PsqlGravador("")).fechar(VID, "k", "h:1:a", m.Achado("ok", None, 7, "ab")) is False


def test_abrir_abandona_a_aberta_e_enfileira_numa_so_chamada():
    m = _mod()
    psql = PsqlGravador('["11111111-0000-4000-8000-000000000001"]\n',
                        '{"id": "22222222-0000-4000-8000-000000000002", "itens": 2}\n')
    vid, abandonadas = m.FilaPg(psql).abrir("firma", "", "dados/abcd@1234", [("a" * 64, 5), ("b" * 64, 6)])
    assert vid == "22222222-0000-4000-8000-000000000002"
    assert abandonadas == ["11111111-0000-4000-8000-000000000001"]
    assert "'abandonada'" in psql.sqls[0] and "json_to_recordset" in psql.sqls[1]


def test_abrir_que_enfileira_menos_que_a_listagem_nao_abre(capsys):
    m = _mod()
    psql = PsqlGravador("[]\n", '{"id": "22222222-0000-4000-8000-000000000002", "itens": 1}\n')
    with pytest.raises(m.FonteFora, match="1 de 2"):
        m.FilaPg(psql).abrir("firma", "", "q", [("a" * 64, 5), ("b" * 64, 6)])


def test_tabela_ausente_diz_qual_migracao_aplicar(monkeypatch):
    m = _mod()

    def roda(*a, **kw):
        return subprocess.CompletedProcess(a, 1, "", 'ERROR:  relation "acervo.varredura_balde" does not exist\n')

    monkeypatch.setattr(m.subprocess, "run", roda)
    with pytest.raises(m.FonteFora) as e:
        m._psql("select 1")
    assert "099_varredura_balde.sql" in str(e.value) and "release migrar aplicar rag" in str(e.value)


# --- o armazem de verdade, com o cliente S3 trocado -----------------------------------------------

class ErroS3(Exception):
    def __init__(self, codigo, mensagem=""):
        super().__init__(f"{codigo}: {mensagem}")
        self.response = {"Error": {"Code": codigo, "Message": mensagem}}


class ClientError(ErroS3):
    pass


class EndpointConnectionError(Exception):
    pass


class CorpoFalso:
    def __init__(self, blocos, falha=None):
        self.blocos, self.falha, self.fechado = blocos, falha, False

    def iter_chunks(self, tamanho):
        yield from self.blocos
        if self.falha:
            raise self.falha

    def close(self):
        self.fechado = True


class ClienteS3Falso:
    def __init__(self, corpo=None, erro=None):
        self.corpo, self.erro = corpo, erro

    def get_object(self, Bucket, Key):
        if self.erro:
            raise self.erro
        return {"Body": self.corpo}


def test_armazem_le_em_blocos_calcula_o_sha256_e_fecha_o_corpo():
    m = _mod()
    corpo = CorpoFalso([b"conteudo ", b"um"])
    assert m.Armazem(ClienteS3Falso(corpo)).ler("acervo", OK1, 30) == (OK1, 11)
    assert corpo.fechado


def test_armazem_classifica_a_falha_de_leitura():
    m = _mod()
    with pytest.raises(m.ObjetoIlegivel) as e:
        m.Armazem(ClienteS3Falso(erro=ClientError("SlowDownRead", "Resource requested is unreadable"))).ler(
            "acervo", ILEGIVEL, 30)
    assert "SlowDownRead" in str(e.value) and "unreadable" in str(e.value)
    corpo = CorpoFalso([b"meio"], falha=OSError("conexao caiu no meio da leitura"))
    with pytest.raises(m.ObjetoIlegivel) as e:
        m.Armazem(ClienteS3Falso(corpo)).ler("acervo", ILEGIVEL, 30)
    assert "OSError" in str(e.value) and corpo.fechado
    with pytest.raises(m.ObjetoAusente):
        m.Armazem(ClienteS3Falso(erro=ClientError("NoSuchKey"))).ler("acervo", AUSENTE, 30)
    with pytest.raises(m.FonteFora):
        m.Armazem(ClienteS3Falso(erro=EndpointConnectionError("sem rota"))).ler("acervo", OK1, 30)
    with pytest.raises(m.FonteFora):
        m.Armazem(ClienteS3Falso(erro=ClientError("InvalidAccessKeyId"))).ler("acervo", OK1, 30)


def test_armazem_estoura_o_teto_de_tempo_por_objeto(monkeypatch):
    m = _mod()
    relogio = iter([0.0, 1.0, 2.0, 9.0, 10.0, 11.0])
    monkeypatch.setattr(m, "_agora", lambda: next(relogio))
    corpo = CorpoFalso([b"a", b"b", b"c", b"d"])
    with pytest.raises(m.ObjetoIlegivel) as e:
        m.Armazem(ClienteS3Falso(corpo)).ler("acervo", OK1, 5)
    assert "prazo de 5 s" in str(e.value) and corpo.fechado
