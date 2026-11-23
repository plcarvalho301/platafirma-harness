# componente: componente:abertura
"""Suíte da abertura da sessão (story 4334, feature 4269).

Reúne os testes de unidade de nomes, pauta, rotinas e sessão (lib/abertura) e os seis casos
do Aceite × prova do verbo `expediente montar`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

HARNESS_DIR = Path(__file__).resolve().parents[1]
EXPEDIENTE = HARNESS_DIR / "bin" / "expediente"
APOIO_DIR = HARNESS_DIR / "testes" / "apoio" / "abertura"
PORTA_YAML = HARNESS_DIR / "registro" / "porta.yaml"

sys.path.insert(0, str(HARNESS_DIR / "lib"))

from abertura.nomes import SecaoDasCadeiras, resolver  # noqa: E402
from abertura.pauta import Carta, ContextoDaSessao, Guardado, montar_pauta  # noqa: E402
from abertura.roteiro import (  # noqa: E402
    ParteLida,
    PecaDoRoteiro,
    PedidoDeRoteiro,
    extrair_tupla,
    montar_roteiro,
)
from abertura.rotinas import (  # noqa: E402
    FichaDeProcesso,
    Processo,
    Recusa,
    formatar_rotinas,
    rotinas,
)
from abertura.sessao import exigir_sessao  # noqa: E402
from postura.casa import Ligacoes, SemBanco  # noqa: E402


# --- nomes (lib/abertura/nomes.py) ---------------------------------------------------------------------------------

FIXTURE_NOMES = """# Carla Cangurina

## Gerências

- **estrategia** — aonde a firma vai.
- **portfolio** — os cards no tempo.
- **processos** — a régua do processo.

## Nomes

- cadeira **gestao-estrategica**: gestão, gestão estratégica

# Olga Corujeira

## Gerências

- **engenharia-de-dados** — como o dado se guarda.
- **governanca-de-dados** — quem responde por cada conjunto.
- **ciencia-de-dados** — a vista montada sobre uma base.

## Nomes

- cadeira **dados**: nenhum
- chapéu **engenharia-de-dados**: engenharia
- chapéu **governanca-de-dados**: governança
- chapéu **ciencia-de-dados**: ciência

# Elias Elefante

## Gerências

- **busca** — o motor de busca.
- **contexto** — a janela e a lousa.
- **engenharia-de-harness** — o harness.

## Nomes

- cadeira **ia**: inteligência artificial
"""


def test_nome_alternativo_de_cadeira_e_de_chapeu_abre_o_slug_com_aviso():
    secao = SecaoDasCadeiras.de_texto(FIXTURE_NOMES)

    res_gestao = resolver("gestão", None, secao)
    assert res_gestao.ok
    assert res_gestao.cadeira == "gestao-estrategica"
    assert res_gestao.chapeu is None
    assert any("gestao-estrategica" in a for a in res_gestao.avisos)

    res_sem_acento = resolver("GESTAO", None, secao)
    assert res_sem_acento.ok
    assert res_sem_acento.cadeira == "gestao-estrategica"

    res_dados = resolver("dados", "ciência", secao)
    assert res_dados.ok
    assert (res_dados.cadeira, res_dados.chapeu) == ("dados", "ciencia-de-dados")
    assert any("ciencia-de-dados" in a for a in res_dados.avisos)

    res_dados_sem_acento = resolver("dados", "CIENCIA", secao)
    assert res_dados_sem_acento.ok
    assert (res_dados_sem_acento.cadeira, res_dados_sem_acento.chapeu) == ("dados", "ciencia-de-dados")


def test_slug_exato_passa_sem_aviso_e_pedaco_unico_segue_funcionando():
    secao = SecaoDasCadeiras.de_texto(FIXTURE_NOMES)

    res_exato = resolver("dados", "ciencia-de-dados", secao)
    assert res_exato.ok
    assert (res_exato.cadeira, res_exato.chapeu) == ("dados", "ciencia-de-dados")
    assert res_exato.avisos == []

    res_pedaco = resolver("ia", "harness", secao)
    assert res_pedaco.ok
    assert (res_pedaco.cadeira, res_pedaco.chapeu) == ("ia", "engenharia-de-harness")
    assert any("engenharia-de-harness" in a for a in res_pedaco.avisos)


def test_nome_que_nao_casa_recusa_com_a_lista_de_cadeiras_e_chapeus_com_nomes_alternativos():
    secao = SecaoDasCadeiras.de_texto(FIXTURE_NOMES)

    rec_cad = resolver("inexistente", None, secao)
    assert not rec_cad.ok
    assert rec_cad.recusa is not None
    assert "gestao-estrategica" in rec_cad.recusa.mensagem
    assert "gestão" in rec_cad.recusa.mensagem
    assert "ciencia-de-dados" in rec_cad.recusa.mensagem
    assert "ciência" in rec_cad.recusa.mensagem

    rec_ch = resolver("dados", "inexistente", secao)
    assert not rec_ch.ok
    assert rec_ch.recusa is not None
    assert "fora do vocabulário" in rec_ch.recusa.mensagem
    assert "ciencia-de-dados (ciência)" in rec_ch.recusa.mensagem
    assert "gestao-estrategica (gestão, gestão estratégica)" in rec_ch.recusa.mensagem


# --- pauta (lib/abertura/pauta.py) ---------------------------------------------------------------------------------

def test_guardado_fora_da_ocasiao_e_contado_sem_mostrar_o_item():
    guardados = [
        Guardado(
            id=1,
            trabalho="retomar grade da tela",
            chapeu="front-end",
            card="4100",
            guardado_em="2026-11-17T10:00:00+00:00",
        ),
        Guardado(
            id=2,
            trabalho="fechar suite de contrato",
            chapeu="testes",
            card="4200",
            guardado_em="2026-11-17T10:00:00+00:00",
        ),
    ]
    sessao = ContextoDaSessao(
        cadeira="engenharia",
        chapeu="back-end",
        turno="card 4334, execução",
        transicoes_de_card={"4100": "2026-11-17T09:00:00+00:00"},
    )

    pauta = montar_pauta(guardados, [], sessao)

    assert pauta.total_guardados == 2
    assert pauta.fora_da_ocasiao == 2
    assert pauta.guardados == []
    assert "2 guardado(s)" in pauta.conteudo
    assert "retomar grade da tela" not in pauta.conteudo
    assert "fechar suite de contrato" not in pauta.conteudo
    assert "cache_control" not in pauta.como_dict()
    assert "cacheavel" not in pauta.como_dict()


def test_ocasiao_casa_por_card_que_mudou_depois_de_guardado_por_turno_e_por_chapeu():
    por_card = Guardado(
        id=1,
        trabalho="destravar integração",
        chapeu="front-end",
        card="4100",
        guardado_em="2026-11-17T10:00:00+00:00",
    )
    por_turno_numero = Guardado(
        id=2,
        trabalho="revisar migração",
        chapeu="testes",
        card="4334",
        guardado_em="2026-11-17T10:00:00+00:00",
    )
    por_turno_nome = Guardado(
        id=3,
        trabalho="auditoria de rotas",
        chapeu="testes",
        guardado_em="2026-11-17T10:00:00+00:00",
    )
    por_chapeu = Guardado(
        id=4,
        trabalho="sanear fila de eventos",
        chapeu="back-end",
        card="4999",
        guardado_em="2026-11-17T10:00:00+00:00",
    )
    fora = Guardado(
        id=5,
        trabalho="item silencioso",
        chapeu="front-end",
        card="4888",
        guardado_em="2026-11-17T10:00:00+00:00",
    )

    sessao = ContextoDaSessao(
        cadeira="engenharia",
        chapeu="back-end",
        turno="seguir com #4334 e com a auditoria de rotas",
        transicoes_de_card={
            "4100": "2026-11-17T12:00:00+00:00",
            "4888": "2026-11-17T08:00:00+00:00",
        },
    )
    cartas = [Carta(id="m1", de="ti", assunto="porta pronta")]

    pauta = montar_pauta([por_card, por_turno_numero, por_turno_nome, por_chapeu, fora], cartas, sessao)

    assert pauta.total_guardados == 5
    assert pauta.fora_da_ocasiao == 1
    assert [g.id for g in pauta.guardados] == [1, 2, 3, 4]
    assert "destravar integração" in pauta.conteudo
    assert "revisar migração" in pauta.conteudo
    assert "auditoria de rotas" in pauta.conteudo
    assert "sanear fila de eventos" in pauta.conteudo
    assert "item silencioso" not in pauta.conteudo
    assert "porta pronta" in pauta.conteudo
    assert "por referência" in pauta.turno


def test_reforco_chega_colado_ao_turno_com_os_quatro_itens():
    pauta = montar_pauta([], [], ContextoDaSessao(cadeira="ti", turno="atende a caixa"))

    linhas = pauta.conteudo.splitlines()
    assert linhas[0] == pauta.turno
    assert linhas[1] == "reforço:"
    assert linhas[2:6] == [f"- {item}" for item in pauta.reforco]
    assert len(pauta.reforco) == 4
    assert "conferir no ar e depois no fichário" in pauta.reforco[0]
    assert "a classe e a instância no fichário" in pauta.reforco[1]
    assert "À margem" in pauta.reforco[1]
    assert "✅" in pauta.reforco[2]
    assert "não se contorna" in pauta.reforco[3]
    assert not any("monta_sessao" in item for item in pauta.reforco)
    assert pauta.como_dict()["reforco"] == list(pauta.reforco)


def test_pauta_indica_falha_de_leitura_sem_dizer_zero_dt1336():
    pauta = montar_pauta(
        [],
        [],
        ContextoDaSessao(cadeira="ti", turno="verifica a caixa"),
        lousa_erro="valkey fora",
        caixa_erro="fila indisponível",
    )
    assert "lousa: não foi possível ler (valkey fora)" in pauta.conteudo
    assert "caixa: não foi possível ler (fila indisponível)" in pauta.conteudo
    assert "lousa: 0 guardados" not in pauta.conteudo
    assert "caixa: 0 cartas" not in pauta.conteudo
    d = pauta.como_dict()
    assert d["lousa_erro"] == "valkey fora"
    assert d["caixa_erro"] == "fila indisponível"


# --- rotinas (lib/abertura/rotinas.py) -----------------------------------------------------------------------------

class LeitorDeFixture:
    def __init__(self, fichas: list[FichaDeProcesso]) -> None:
        self._fichas = list(fichas)

    def processos_de_rotina(self) -> list[FichaDeProcesso]:
        return list(self._fichas)


def test_processo_sem_gatilho_e_sem_resultado_sao_recusados_e_o_resto_e_servido():
    leitor = LeitorDeFixture([
        FichaDeProcesso(
            chave="procedimento:atender-um-pedido",
            gatilhos=(),
            produz=("capacidade:tarefas",),
            conteudo="# Atender o pedido",
        ),
        FichaDeProcesso(
            chave="missao:trabalhar-um-pedido",
            gatilhos=("gatilho:trabalhar",),
            produz=(),
            conteudo="# Trabalhar um pedido",
        ),
        FichaDeProcesso(
            chave="procedimento:revisar-uma-entrega",
            gatilhos=("gatilho:revisar",),
            produz=("capacidade:tarefas",),
            conteudo="# Revisar a entrega",
        ),
    ])

    servidos, recusas = rotinas(leitor)

    assert len(servidos) == 1
    assert servidos[0] == Processo(
        chave="procedimento:revisar-uma-entrega",
        gatilhos=("gatilho:revisar",),
        produz=("capacidade:tarefas",),
        classe="procedimento",
        conteudo="# Revisar a entrega",
    )
    assert [Recusa(codigo=r.codigo, processo=r.processo) for r in recusas] == [
        Recusa(codigo="processo-sem-gatilho", processo="procedimento:atender-um-pedido"),
        Recusa(codigo="processo-sem-resultado", processo="missao:trabalhar-um-pedido"),
    ]
    texto = formatar_rotinas(servidos)
    assert "procedimento:revisar-uma-entrega" in texto
    assert "# Revisar a entrega" in texto
    assert "atender-um-pedido" not in texto
    assert "trabalhar-um-pedido" not in texto


def test_estado_atual_dos_tres_processos_sem_gatilho_recusa_os_tres_e_serve_vazio():
    leitor = LeitorDeFixture([
        FichaDeProcesso("procedimento:atender-um-pedido", (), ("capacidade:tarefas",)),
        FichaDeProcesso("missao:trabalhar-um-pedido", (), ("capacidade:tarefas",)),
        FichaDeProcesso("procedimento:revisar-uma-entrega", (), ("capacidade:tarefas",)),
    ])

    servidos, recusas = rotinas(leitor)

    assert servidos == []
    assert [r.codigo for r in recusas] == [
        "processo-sem-gatilho",
        "processo-sem-gatilho",
        "processo-sem-gatilho",
    ]
    assert formatar_rotinas(servidos) == ""


def test_ligacoes_processos_de_rotina_consulta_entrega_rotina_gatilho_e_produz():
    chamadas: list[tuple[str, tuple]] = []

    class FakeLigacoes(Ligacoes):
        def _consulta(self, sql: str, parametros: tuple) -> list:
            chamadas.append((sql, parametros))
            return [
                ("procedimento:atender-um-pedido", "procedimento", [], ["capacidade:tarefas"]),
                ("procedimento:revisar-uma-entrega", "procedimento", ["gatilho:revisar"], ["capacidade:tarefas"]),
            ]

    lig = FakeLigacoes()
    fichas = lig.processos_de_rotina()

    assert len(chamadas) == 1
    sql, params = chamadas[0]
    assert params == ("entrega", "rotina")
    assert "casa.ficha" in sql and "casa.dado" in sql and "casa.ligacao" in sql
    assert "dispara" in sql and "produz" in sql
    assert fichas == [
        FichaDeProcesso(
            chave="procedimento:atender-um-pedido",
            gatilhos=(),
            produz=("capacidade:tarefas",),
            classe="procedimento",
        ),
        FichaDeProcesso(
            chave="procedimento:revisar-uma-entrega",
            gatilhos=("gatilho:revisar",),
            produz=("capacidade:tarefas",),
            classe="procedimento",
        ),
    ]


# --- sessao (lib/abertura/sessao.py) -------------------------------------------------------------------------------

def test_chamada_sem_sessao_e_recusada_com_a_chamada_que_abre():
    livres = frozenset({"monta_sessao", "abertura", "painel_tela"})

    recusa = exigir_sessao("tarefas", None, livres)
    assert recusa is not None
    assert recusa.codigo == "sem-sessao"
    assert "monta_sessao" in recusa.chamada
    assert "monta_sessao" in recusa.mensagem
    assert recusa.tool == "tarefas"

    recusa_vazia = exigir_sessao("repo", "", livres)
    assert recusa_vazia is not None
    assert "monta_sessao" in recusa_vazia.chamada


def test_abertura_leituras_da_tela_e_chamada_com_sessao_passam():
    livres = frozenset({"monta_sessao", "abertura", "leitura_tela"})

    assert exigir_sessao("monta_sessao", None, livres) is None
    assert exigir_sessao("abertura", None, livres) is None
    assert exigir_sessao("leitura_tela", None, livres) is None
    assert exigir_sessao("tela:quadro", None, livres) is None
    assert exigir_sessao("tarefas", "823dec4e-6bef-4053-baed-2e54bd0788fc", livres) is None


# --- expediente montar (Aceite × prova da S4334) -------------------------------------------------------------------

_ROTEIRO_PADRAO_FIXTURE = [
    {"classe": "persona", "chave": "engenharia"},
    {"classe": "persona", "chave": "persona:gestao-estrategica"},
    {"classe": "persona", "chave": "persona:dados"},
    {"classe": "persona", "chave": "persona:ia"},
    {"classe": "chapeu", "chave": "chapeu:back-end"},
    {"classe": "chapeu", "chave": "chapeu:ciencia-de-dados"},
    {"classe": "chapeu", "chave": "chapeu:engenharia-de-harness"},
    {"classe": "cultura", "chave": "cultura:da-casa"},
    {"classe": "postura", "chave": "cirurgico"},
    {"classe": "postura", "chave": "metodico"},
    {"classe": "cenario", "chave": "cenario:tombando-legado"},
    {"classe": "circunstancia", "chave": "circunstancia:casa-em-tombamento"},
    {"classe": "ritual", "chave": "ritual:da-casa"},
]


def _rodar_abertura(
    args: list[str],
    *,
    pergunta: str = "",
    env_extra: dict[str, str] | None = None,
    rotinas_fixture: list[dict] | None = None,
    roteiro_fixture: list[dict] | dict | None = None,
    tmp_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for k in ("PF_CADEIRA", "PF_SESSAO", "PF_ORDEM_ID", "PF_FITA", "PF_ABERTURA_DIR"):
        env.pop(k, None)
    env["PF_BIN"] = str(APOIO_DIR)
    env["PF_NOMES_FIXTURE"] = str(APOIO_DIR / "nomes.md")

    if rotinas_fixture is not None and tmp_path is not None:
        arq_rot = tmp_path / "rotinas.json"
        arq_rot.write_text(json.dumps({"processos": rotinas_fixture}, ensure_ascii=False), encoding="utf-8")
        env["PF_ROTINAS_FIXTURE"] = str(arq_rot)
    elif tmp_path is not None:
        arq_rot = tmp_path / "rotinas_padrao.json"
        arq_rot.write_text(
            json.dumps({
                "processos": [
                    {
                        "chave": "procedimento:atender-um-pedido",
                        "gatilhos": ["gatilho:atender"],
                        "produz": ["capacidade:tarefas"],
                        "classe": "procedimento",
                        "conteudo": "# Atender o pedido de quem abriu a sessão",
                    },
                    {
                        "chave": "missao:trabalhar-um-pedido",
                        "gatilhos": ["gatilho:trabalhar"],
                        "produz": ["capacidade:tarefas"],
                        "classe": "missao",
                        "conteudo": "# Trabalhar um pedido até o desfecho",
                    },
                    {
                        "chave": "procedimento:revisar-uma-entrega",
                        "gatilhos": ["gatilho:revisar"],
                        "produz": ["capacidade:tarefas"],
                        "classe": "procedimento",
                        "conteudo": "# Revisar a entrega com quem a pediu",
                    },
                ]
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        env["PF_ROTINAS_FIXTURE"] = str(arq_rot)

    if tmp_path is not None:
        # a abertura emite sessao_aberta (S4335): o oplog e a memória de trabalho ficam no tmp, longe da porta
        env["OPS_LOG_DIR"] = str(tmp_path / "ops")
        fixtura_mem = tmp_path / "valkey.json"
        if not fixtura_mem.exists():
            fixtura_mem.write_text('{"chaves": []}', encoding="utf-8")
        env["PF_VALKEY_FIXTURE"] = str(fixtura_mem)

        arq_roteiro = tmp_path / "roteiro.json"
        payload_roteiro = (
            roteiro_fixture
            if isinstance(roteiro_fixture, dict)
            else {"pecas": _ROTEIRO_PADRAO_FIXTURE if roteiro_fixture is None else roteiro_fixture}
        )
        arq_roteiro.write_text(json.dumps(payload_roteiro, ensure_ascii=False), encoding="utf-8")
        env["PF_ROTEIRO_FIXTURE"] = str(arq_roteiro)

    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        [sys.executable, str(EXPEDIENTE), "montar", *args, "--json"],
        input=pergunta,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        check=False,
    )


def test_slug_valido_devolve_roteiro_rotinas_e_pauta_sem_cache_e_sem_peca_velha(tmp_path):
    proc = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="card 4334, execução",
        tmp_path=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)

    assert d["cadeira"] == "engenharia"
    assert d["chapeu"] == "back-end"
    assert d["sessao_id"] == "11111111-2222-4333-8444-555555555555"
    assert [p["peca"] for p in d["pecas"]] == ["roteiro", "rotinas", "pauta"]

    # Sem peças da casa velha
    nomes_pecas = {p["peca"] for p in d["pecas"]}
    assert "cadernos" not in nomes_pecas
    assert "acervo-consultado" not in nomes_pecas
    assert "mesa" not in nomes_pecas
    assert "guia" not in d["rotinas"]["conteudo"].lower()

    # Sem marca de cache em lugar nenhum do retorno
    texto_json = json.dumps(d, ensure_ascii=False)
    assert "cache_control" not in texto_json
    assert "cacheavel" not in texto_json
    assert "prefixo_cacheavel" not in texto_json

    # Conteúdo das três partes
    assert "Sou a cadeira engenharia" in d["roteiro"]["conteudo"]
    assert "Recorte back-end" in d["roteiro"]["conteudo"]
    assert "Cultura da casa" in d["roteiro"]["conteudo"]
    assert "procedimento:atender-um-pedido" in d["rotinas"]["conteudo"]
    assert "por referência" in d["pauta"]["turno"]

    # Registro da porta inclui monta_sessao em transporte e descansar nos verbos
    porta = yaml.safe_load(PORTA_YAML.read_text(encoding="utf-8"))
    assert "monta_sessao" in porta["transporte"]
    assert "descansar" in porta["verbos"]


def test_nome_alternativo_de_cadeira_e_de_chapeu_abre_o_slug(tmp_path):
    proc_gestao = _rodar_abertura(["gestão"], pergunta="abrir pauta", tmp_path=tmp_path)
    assert proc_gestao.returncode == 0, proc_gestao.stdout + proc_gestao.stderr
    d_gestao = json.loads(proc_gestao.stdout)
    assert d_gestao["cadeira"] == "gestao-estrategica"
    assert any("gestao-estrategica" in a for a in d_gestao["avisos"])

    proc_dados = _rodar_abertura(["dados", "--chapeu", "ciência"], pergunta="abrir vista", tmp_path=tmp_path)
    assert proc_dados.returncode == 0, proc_dados.stdout + proc_dados.stderr
    d_dados = json.loads(proc_dados.stdout)
    assert d_dados["cadeira"] == "dados"
    assert d_dados["chapeu"] == "ciencia-de-dados"
    assert any("ciencia-de-dados" in a for a in d_dados["avisos"])


def test_nome_que_nao_casa_recusa_com_a_lista(tmp_path):
    proc_cad = _rodar_abertura(["inexistente"], tmp_path=tmp_path)
    assert proc_cad.returncode == 2
    d_cad = json.loads(proc_cad.stdout)
    assert "gestao-estrategica" in d_cad["erro"]
    assert "gestão" in d_cad["erro"]
    assert "ciencia-de-dados (ciência)" in d_cad["erro"]
    assert any(c["cadeira"] == "gestao-estrategica" and "gestão" in c["nomes"] for c in d_cad["cadeiras"])

    proc_ch = _rodar_abertura(["dados", "--chapeu", "inexistente"], tmp_path=tmp_path)
    assert proc_ch.returncode == 2
    d_ch = json.loads(proc_ch.stdout)
    assert "fora do vocabulário" in d_ch["erro"]
    assert "ciencia-de-dados (ciência)" in d_ch["erro"]


def test_processo_com_defeito_recusado_sozinho_e_o_resto_e_servido(tmp_path):
    proc = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        rotinas_fixture=[
            {
                "chave": "procedimento:atender-um-pedido",
                "gatilhos": [],
                "produz": ["capacidade:tarefas"],
                "classe": "procedimento",
                "conteudo": "# Atender sem gatilho",
            },
            {
                "chave": "missao:trabalhar-um-pedido",
                "gatilhos": ["gatilho:trabalhar"],
                "produz": [],
                "classe": "missao",
                "conteudo": "# Trabalhar sem resultado",
            },
            {
                "chave": "procedimento:revisar-uma-entrega",
                "gatilhos": ["gatilho:revisar"],
                "produz": ["capacidade:tarefas"],
                "classe": "procedimento",
                "conteudo": "# Revisar válido",
            },
        ],
        tmp_path=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)

    codigos = {r["processo"]: r["codigo"] for r in d["recusas"]}
    assert codigos == {
        "procedimento:atender-um-pedido": "processo-sem-gatilho",
        "missao:trabalhar-um-pedido": "processo-sem-resultado",
    }
    servidos = [p["chave"] for p in d["rotinas"]["processos"]]
    assert servidos == ["procedimento:revisar-uma-entrega"]
    assert "# Revisar válido" in d["rotinas"]["conteudo"]
    assert "# Atender sem gatilho" not in d["rotinas"]["conteudo"]
    assert "# Trabalhar sem resultado" not in d["rotinas"]["conteudo"]


def test_sem_sessao_recusa_com_a_chamada_que_abre_e_deixa_passar_abertura_e_tela():
    livres = frozenset({"monta_sessao", "abertura", "leitura_tela"})

    rec = exigir_sessao("tarefas", None, livres)
    assert rec is not None
    assert rec.codigo == "sem-sessao"
    assert "monta_sessao(cadeira=<slug>, pergunta=<turno>)" in rec.chamada
    assert "monta_sessao" in rec.mensagem

    assert exigir_sessao("monta_sessao", None, livres) is None
    assert exigir_sessao("abertura", None, livres) is None
    assert exigir_sessao("leitura_tela", None, livres) is None
    assert exigir_sessao("tarefas", "11111111-2222-4333-8444-555555555555", livres) is None


def test_4432_pauta_filtra_penduradas_informativas_e_vencidas_e_preserva_metadados():
    from abertura.pauta import extrair_info_de_cabecalho, ler_cartas_da_fila

    saida_fila = json.dumps([
        {
            "msgid": "20261123T190000-engenharia",
            "de": "engenharia",
            "tipo": "resposta",
            "estado": "nao lida",
            "idade_seg": 60,
            "assunto": "resposta nova",
            "ref": "#4432",
            "responde": "20261123T180000-dados",
            "corpo": "chegou agora",
        },
        {
            "msgid": "20261123T150000-ia",
            "de": "ia",
            "tipo": "pedido",
            "estado": "pendurada",
            "idade_seg": 3600,
            "assunto": "pedido recente",
            "ref": "#4432",
            "responde": "",
            "corpo": "precisa de acao",
        },
        {
            "msgid": "20261121T100000-produto",
            "de": "produto",
            "tipo": "handoff",
            "estado": "pendurada",
            "idade_seg": 7200,
            "assunto": "handoff fossil",
            "ref": "",
            "responde": "",
            "corpo": "nao deve entrar na pauta",
        },
        {
            "msgid": "20261118T100000-arquiteto",
            "de": "arquiteto",
            "tipo": "pedido",
            "estado": "pendurada",
            "idade_seg": 60 * 3600,
            "assunto": "pedido antigo >48h",
            "ref": "",
            "responde": "",
            "corpo": "velho demais para pauta ativa",
        },
    ])

    cartas = ler_cartas_da_fila(saida_fila)
    assert len(cartas) == 4
    assert cartas[0].estado == "nao lida"
    assert cartas[0].tipo == "resposta"
    assert cartas[0].idade_seg == 60
    assert cartas[0].ref == "#4432"
    assert cartas[0].responde == "20261123T180000-dados"

    pauta = montar_pauta([], cartas, ContextoDaSessao(cadeira="dados", turno="abrir"))
    assert [c.id for c in pauta.cartas] == ["20261123T190000-engenharia", "20261123T150000-ia"]
    assert pauta.cartas_ocultas == 2
    assert "resposta nova" in pauta.conteudo
    assert "pedido recente" in pauta.conteudo
    assert "handoff fossil" not in pauta.conteudo
    assert "pedido antigo >48h" not in pauta.conteudo
    assert "2 pendurada(s) antiga(s) fora da pauta" in pauta.conteudo

    info = extrair_info_de_cabecalho(
        "#4382 · story · Priorizada (funil) · cadeira: produto · originação: negocio · executor: produto"
    )
    assert info == {"estado": "Priorizada", "cadeira": "produto", "executor": "produto"}


def test_ocasiao_guardado_fora_da_ocasiao_contado_sem_o_item(tmp_path):
    from postura.lousa import ItemDeTrabalho, LousaFixtura, Ocasiao

    fix_valkey = tmp_path / "valkey.json"
    fix_valkey.write_text('{"chaves": []}', encoding="utf-8")
    lousa = LousaFixtura(fix_valkey)
    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="card:4100",
            cadeira="engenharia",
            situacao="guardado",
            card="4100",
            estagio="execucao",
            proxima_jogada="ajustar espaçamento da grade",
            chapeu="front-end",
            ocasiao=Ocasiao(chapeu="front-end"),
        ),
    )
    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="card:4334",
            cadeira="engenharia",
            situacao="guardado",
            card="4334",
            estagio="execucao",
            proxima_jogada="ligar abertura na porta",
            chapeu="back-end",
            ocasiao=Ocasiao(chapeu="back-end"),
        ),
    )

    proc = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="card 4334, execução",
        tmp_path=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    pauta = d["pauta"]

    assert pauta["total_guardados"] == 2
    assert pauta["fora_da_ocasiao"] == 1
    assert len(pauta["guardados"]) == 1
    assert "ligar abertura na porta" in pauta["conteudo"]
    assert "ajustar espaçamento da grade" not in pauta["conteudo"]
    assert "2 guardado(s)" in pauta["conteudo"]


def test_pauta_le_lousa_evicta_card_terminal_e_casa_por_estado_card_chave_e_chapeu(tmp_path):
    from postura.lousa import ItemDeTrabalho, LousaFixtura, Ocasiao

    fix_valkey = tmp_path / "valkey.json"
    fix_valkey.write_text('{"chaves": ["sessao:ativa"]}', encoding="utf-8")
    lousa = LousaFixtura(fix_valkey)

    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="card:5001",
            cadeira="engenharia",
            situacao="guardado",
            card="5001",
            estagio="execucao",
            proxima_jogada="retomar após desbloqueio",
            ocasiao=Ocasiao(card="5001", estado_card="bloqueada"),
        ),
    )
    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="card:5002",
            cadeira="engenharia",
            situacao="guardado",
            card="5002",
            estagio="execucao",
            proxima_jogada="item que já fechou",
            ocasiao=Ocasiao(card="5002", estado_card="em-execucao"),
        ),
    )
    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="turno:o20261118-abc",
            cadeira="engenharia",
            situacao="guardado",
            turno="o20261118-abc",
            estagio="investigacao",
            proxima_jogada="fechar diagnóstico do turno",
            ocasiao=Ocasiao(pedido="diagnóstico avulso"),
        ),
    )
    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="card:5003",
            cadeira="engenharia",
            situacao="guardado",
            card="5003",
            estagio="execucao",
            proxima_jogada="revisar contrato back-end",
            ocasiao=Ocasiao(chapeu="back-end"),
        ),
    )
    lousa.gravar_trabalho(
        "engenharia",
        ItemDeTrabalho(
            chave="card:5004",
            cadeira="engenharia",
            situacao="guardado",
            card="5004",
            estagio="execucao",
            proxima_jogada="silencioso fora da ocasião",
            ocasiao=Ocasiao(card="5004", estado_card="em-execucao"),
        ),
    )

    fix_cards = tmp_path / "cards.json"
    fix_cards.write_text(
        json.dumps(
            {
                "5001": {"estado": "em-execucao"},
                "5002": {"estado": "entregue"},
                "5004": {"estado": "em-execucao"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    proc = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="continuar turno:o20261118-abc",
        env_extra={"PF_CARDS_FIXTURE": str(fix_cards)},
        tmp_path=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    pauta = d["pauta"]

    chaves_servidas = {g["chave"] for g in pauta["guardados"]}
    assert chaves_servidas == {"card:5001", "turno:o20261118-abc", "card:5003"}
    assert pauta["total_guardados"] == 4
    assert pauta["fora_da_ocasiao"] == 1
    assert "item que já fechou" not in pauta["conteudo"]
    assert "silencioso fora da ocasião" not in pauta["conteudo"]

    # Card terminal 5002 foi evictado da lousa e a chave "chaves" foi preservada
    assert lousa.ler_trabalho("engenharia", "card:5002") is None
    assert json.loads(fix_valkey.read_text(encoding="utf-8"))["chaves"] == ["sessao:ativa"]


def test_pauta_degrada_com_aviso_quando_memoria_de_trabalho_esta_fora(tmp_path):
    fix_valkey = tmp_path / "valkey.json"
    fix_valkey.write_text('{"fora": true}', encoding="utf-8")

    proc = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="card 4366, execução",
        tmp_path=tmp_path,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)

    assert d["pauta"]["total_guardados"] == 0
    assert d["pauta"]["guardados"] == []
    assert any("lousa indisponível" in a for a in d["avisos"])


# --- roteiro pela ficha e tupla da primeira linha (S4367) ----------------------------------------------------------

class _FakeLeitorRoteiro:
    def __init__(self, pecas=None, *, sem_banco: bool = False) -> None:
        self._pecas = list(pecas or [])
        self._sem_banco = sem_banco

    def construido_de(self, roteiro: str = "porta"):
        if self._sem_banco:
            raise SemBanco("Olaria indisponível")
        return list(self._pecas)


class _FakeLeitorParte:
    def __init__(self, respostas: dict[str, ParteLida] | None = None) -> None:
        self._respostas = dict(respostas or {})
        self.chamadas: list[tuple[str, str, str | None, str | None]] = []

    def ler(self, classe: str, cadeira: str, chapeu: str | None, *, chave: str | None = None) -> ParteLida:
        self.chamadas.append((classe, cadeira, chapeu, chave))
        chave_mapa = f"{classe}:{chave}" if chave else classe
        if chave_mapa in self._respostas:
            return self._respostas[chave_mapa]
        if classe in self._respostas:
            return self._respostas[classe]
        return ParteLida(
            ok=False,
            conteudo="",
            ref=f"verbo:persona ({classe})",
            erro=f"classe '{classe}' sem leitura",
        )


def test_roteiro_agrupa_construido_de_descarta_instrucao_e_nao_serve_outra_cadeira():
    leitor_ficha = _FakeLeitorRoteiro([
        ("persona", "engenharia"),
        ("persona", "persona:arquiteto"),
        ("chapeu", "chapeu:back-end"),
        ("chapeu", "chapeu:estrategia"),
        ("cultura", "cultura:da-casa"),
        ("postura", "cirurgico"),
        ("cenario", "cenario:tombando-legado"),
        ("circunstancia", "circunstancia:casa-em-tombamento"),
        ("ritual", "ritual:da-casa"),
        ("instrucao", "instrucao:arranque"),
    ])
    leitor_parte = _FakeLeitorParte({
        "persona": ParteLida(ok=True, conteudo="# Gabriel", ref="verbo:persona ler engenharia", instancias=("engenharia",)),
        "chapeu": ParteLida(ok=True, conteudo="# Back-end", ref="verbo:persona ler engenharia --chapeu back-end", instancias=("back-end",)),
        "cultura": ParteLida(ok=True, conteudo="## Cultura", ref="verbo:persona cultura", instancias=("da-casa",)),
        "postura": ParteLida(ok=True, conteudo="POSTURAS: cirurgico", ref="verbo:persona ler engenharia --parte posturas", instancias=("cirurgico",)),
        "cenario": ParteLida(ok=True, conteudo="CENARIO: tombando-legado", ref="verbo:persona ler engenharia --parte cenario", instancias=("tombando-legado",)),
        "circunstancia": ParteLida(ok=True, conteudo="CIRCUNSTANCIA: casa-em-tombamento", ref="verbo:persona ler engenharia --parte circunstancia", instancias=("casa-em-tombamento",)),
        "ritual": ParteLida(ok=True, conteudo="RITUAL: da-casa", ref="verbo:persona ler engenharia --parte ritual", instancias=("da-casa",)),
    })

    montado = montar_roteiro(
        PedidoDeRoteiro(cadeira="engenharia", chapeu="back-end"),
        leitor_ficha,
        leitor_parte,
    )

    assert [p.parte for p in montado.partes] == [
        "persona", "chapeu", "cultura", "postura", "cenario", "circunstancia", "ritual"
    ]
    assert "arquiteto" not in montado.conteudo
    assert "estrategia" not in montado.conteudo
    assert all(c[0] != "instrucao" for c in leitor_parte.chamadas)
    assert not any("instrucao" in a for a in montado.avisos)


def test_roteiro_peca_acrescentada_na_fixture_servida_sem_mudanca_de_codigo():
    leitor_ficha = _FakeLeitorRoteiro([
        PecaDoRoteiro("persona", "engenharia", posicao=1),
        PecaDoRoteiro("sinal-novo", "sinal-novo:vigente", posicao=2),
    ])
    leitor_parte = _FakeLeitorParte({
        "persona": ParteLida(ok=True, conteudo="# Gabriel", ref="verbo:persona", instancias=("engenharia",)),
        "sinal-novo": ParteLida(ok=True, conteudo="SINAL NOVO", ref="verbo:sinal", instancias=("vigente",)),
    })

    montado = montar_roteiro(PedidoDeRoteiro(cadeira="engenharia"), leitor_ficha, leitor_parte)

    assert [p.parte for p in montado.partes] == ["persona", "sinal-novo"]
    assert "SINAL NOVO" in montado.conteudo
    assert montado.avisos == ()


def test_roteiro_peca_sem_leitura_entra_em_aviso_e_serve_o_resto():
    leitor_ficha = _FakeLeitorRoteiro([
        PecaDoRoteiro("persona", "engenharia", posicao=1),
        PecaDoRoteiro("classe-desconhecida", "classe-desconhecida:x", posicao=2),
        PecaDoRoteiro("cultura", "cultura:da-casa", posicao=3),
    ])
    leitor_parte = _FakeLeitorParte({
        "persona": ParteLida(ok=True, conteudo="# Gabriel", ref="verbo:persona", instancias=("engenharia",)),
        "cultura": ParteLida(ok=True, conteudo="## Cultura", ref="verbo:persona cultura", instancias=("da-casa",)),
    })

    montado = montar_roteiro(PedidoDeRoteiro(cadeira="engenharia"), leitor_ficha, leitor_parte)

    assert [p.parte for p in montado.partes] == ["persona", "cultura"]
    assert any("classe-desconhecida" in a for a in montado.avisos)


def test_roteiro_ficha_ausente_ou_banco_fora_serve_lista_padrao_com_aviso():
    leitor_parte = _FakeLeitorParte({
        "persona": ParteLida(ok=True, conteudo="# Gabriel", ref="verbo:persona", instancias=("engenharia",)),
        "cultura": ParteLida(ok=True, conteudo="## Cultura", ref="verbo:persona cultura", instancias=("da-casa",)),
        "postura": ParteLida(ok=True, conteudo="POSTURAS", ref="verbo:posturas", instancias=("cirurgico",)),
        "cenario": ParteLida(ok=True, conteudo="", ref="verbo:cenario", instancias=()),
        "circunstancia": ParteLida(ok=True, conteudo="", ref="verbo:circunstancia", instancias=()),
    })

    sem_banco = montar_roteiro(PedidoDeRoteiro(cadeira="engenharia"), _FakeLeitorRoteiro(sem_banco=True), leitor_parte)
    assert [p.parte for p in sem_banco.partes] == ["persona", "cultura", "postura"]
    assert any("roteiro:porta" in a for a in sem_banco.avisos)

    ficha_vazia = montar_roteiro(PedidoDeRoteiro(cadeira="engenharia"), _FakeLeitorRoteiro([]), leitor_parte)
    assert [p.parte for p in ficha_vazia.partes] == ["persona", "cultura", "postura"]
    assert any("roteiro:porta" in a for a in ficha_vazia.avisos)


def test_roteiro_instancia_fora_do_construido_de_omitida_com_aviso():
    leitor_ficha = _FakeLeitorRoteiro([
        PecaDoRoteiro("persona", "engenharia", posicao=1),
        PecaDoRoteiro("postura", "metodico", posicao=2),
        PecaDoRoteiro("ritual", "ritual:da-casa", posicao=3),
    ])
    leitor_parte = _FakeLeitorParte({
        "persona": ParteLida(ok=True, conteudo="# Gabriel", ref="verbo:persona", instancias=("engenharia",)),
        "postura": ParteLida(ok=True, conteudo="POSTURA: cirurgico", ref="verbo:postura", instancias=("cirurgico",)),
        "ritual": ParteLida(ok=True, conteudo="RITUAL: da-casa", ref="verbo:ritual", instancias=("da-casa",)),
    })

    montado = montar_roteiro(PedidoDeRoteiro(cadeira="engenharia"), leitor_ficha, leitor_parte)

    assert [p.parte for p in montado.partes] == ["persona", "ritual"]
    assert "cirurgico" not in montado.conteudo
    assert any("postura:cirurgico" in a for a in montado.avisos)


def test_roteiro_tupla_primeira_linha_regras():
    t1 = extrair_tupla("(ia, harness)\nrevisar o motor")
    assert t1 is not None and t1.cadeira == "ia" and t1.chapeu == "harness" and t1.overrides == ()

    t2 = extrair_tupla("(engenharia, back-end, postura:cirurgico, ritual:ideacao, cultura:outra)")
    assert t2 is not None
    assert (t2.cadeira, t2.chapeu) == ("engenharia", "back-end")
    assert t2.overrides == (("postura", "cirurgico"), ("ritual", "ideacao"))
    assert any("cultura" in a and "fixa" in a for a in t2.avisos)

    assert extrair_tupla("(ia, harness) na mesma linha") is None
    assert extrair_tupla("antes (ia, harness)") is None
    assert extrair_tupla("sem parenteses") is None


def test_roteiro_expediente_monta_pela_ficha_e_omite_instrucao(tmp_path):
    fixture = [
        {"classe": "persona", "chave": "persona:gestao-estrategica"},
        {"classe": "persona", "chave": "engenharia"},
        {"classe": "chapeu", "chave": "chapeu:back-end"},
        {"classe": "cultura", "chave": "cultura:da-casa"},
        {"classe": "postura", "chave": "metodico"},
        {"classe": "cenario", "chave": "cenario:tombando-legado"},
        {"classe": "circunstancia", "chave": "circunstancia:casa-em-tombamento"},
        {"classe": "ritual", "chave": "ritual:da-casa"},
        {"classe": "instrucao", "chave": "instrucao:arranque"},
    ]
    proc = _rodar_abertura(["gestao-estrategica"], roteiro_fixture=fixture, tmp_path=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)

    partes = [p["parte"] for p in d["roteiro"]["partes"]]
    assert partes == ["persona", "cultura", "postura", "cenario", "circunstancia", "ritual"]
    assert "Sou a cadeira gestao-estrategica" in d["roteiro"]["conteudo"]
    assert "Sou a cadeira engenharia" not in d["roteiro"]["conteudo"]
    assert "Recorte back-end" not in d["roteiro"]["conteudo"]
    assert "CIRCUNSTÂNCIA EM VIGOR" in d["roteiro"]["conteudo"]
    assert "RITUAL EM VIGOR" in d["roteiro"]["conteudo"]


def test_roteiro_expediente_ficha_ausente_e_peca_sem_leitura(tmp_path):
    proc_ausente = _rodar_abertura(
        ["engenharia"],
        roteiro_fixture={"sem_banco": True, "erro": "banco desligado"},
        tmp_path=tmp_path,
    )
    assert proc_ausente.returncode == 0, proc_ausente.stdout + proc_ausente.stderr
    d_aus = json.loads(proc_ausente.stdout)
    assert "Sou a cadeira engenharia" in d_aus["roteiro"]["conteudo"]
    assert any("roteiro:porta" in a for a in d_aus["avisos"])

    proc_sem_leitura = _rodar_abertura(
        ["engenharia"],
        roteiro_fixture=[
            {"classe": "persona", "chave": "engenharia"},
            {"classe": "peca-futura", "chave": "peca-futura:x"},
            {"classe": "cultura", "chave": "cultura:da-casa"},
        ],
        tmp_path=tmp_path,
    )
    assert proc_sem_leitura.returncode == 0, proc_sem_leitura.stdout + proc_sem_leitura.stderr
    d_sl = json.loads(proc_sem_leitura.stdout)
    assert [p["parte"] for p in d_sl["roteiro"]["partes"]] == ["persona", "cultura"]
    assert any("peca-futura" in a for a in d_sl["avisos"])


def test_roteiro_expediente_tupla_ia_harness_recusa_xyz_e_overrides(tmp_path):
    proc_ia = _rodar_abertura(["engenharia"], pergunta="(ia, harness)\nrevisar", tmp_path=tmp_path)
    assert proc_ia.returncode == 0, proc_ia.stdout + proc_ia.stderr
    d_ia = json.loads(proc_ia.stdout)
    assert d_ia["cadeira"] == "ia"
    assert d_ia["chapeu"] == "engenharia-de-harness"
    assert "Sou a cadeira ia" in d_ia["roteiro"]["conteudo"]

    proc_xyz = _rodar_abertura(["engenharia"], pergunta="(xyz)", tmp_path=tmp_path)
    assert proc_xyz.returncode == 2
    d_xyz = json.loads(proc_xyz.stdout)
    assert "gestao-estrategica" in d_xyz["erro"]

    proc_ovr = _rodar_abertura(
        ["engenharia"],
        pergunta="(engenharia, back-end, postura:cirurgico, cultura:outra)",
        tmp_path=tmp_path,
    )
    assert proc_ovr.returncode == 0, proc_ovr.stdout + proc_ovr.stderr
    d_ovr = json.loads(proc_ovr.stdout)
    assert "POSTURAS EM VIGOR (cirurgico)" in d_ovr["roteiro"]["conteudo"]
    assert "Cultura da casa" in d_ovr["roteiro"]["conteudo"]
    assert any("cultura" in a and "fixa" in a for a in d_ovr["avisos"])


def test_roteiro_expediente_tupla_nao_sozinha_e_chave_sem_ficha(tmp_path):
    proc_nao_so = _rodar_abertura(
        ["engenharia"],
        pergunta="(ia, harness) na mesma linha",
        tmp_path=tmp_path,
    )
    assert proc_nao_so.returncode == 0, proc_nao_so.stdout + proc_nao_so.stderr
    d_ns = json.loads(proc_nao_so.stdout)
    assert d_ns["cadeira"] == "engenharia"

    proc_falta = _rodar_abertura(
        ["engenharia"],
        pergunta="(engenharia, back-end, ritual:inexistente)",
        tmp_path=tmp_path,
    )
    assert proc_falta.returncode == 0, proc_falta.stdout + proc_falta.stderr
    d_f = json.loads(proc_falta.stdout)
    assert "Sou a cadeira engenharia" in d_f["roteiro"]["conteudo"]
    assert any("ritual:inexistente" in a for a in d_f["avisos"])


def test_ato_abrir_le_lousa_e_caixa_e_sinaliza_falha_dt1336(tmp_path, monkeypatch):
    from abertura.__main__ import _ato_abrir

    casa = tmp_path / "casa"
    (casa / "instancias" / "persona").mkdir(parents=True)
    (casa / "instancias" / "cultura").mkdir(parents=True)
    (casa / "instancias" / "persona" / "ti.md").write_text(
        "# TI\n\nEntidade: persona\n\n## Nomes\n\n- cadeira **ti**: nenhum\n",
        encoding="utf-8",
    )
    (casa / "instancias" / "cultura" / "da-casa.md").write_text(
        "# Cultura da casa\n\nEntidade: cultura\n\n## Premissas\n\n- Regra.\n",
        encoding="utf-8",
    )

    # 1. Lousa via fixture com 1 guardado + fila fake com 2 cartas
    from postura.lousa import ItemDeTrabalho, LousaFixtura, Ocasiao

    fix_lousa = tmp_path / "lousa.json"
    fix_lousa.write_text("{}", encoding="utf-8")
    LousaFixtura(fix_lousa).gravar_trabalho(
        "ti",
        ItemDeTrabalho(
            chave="card:1336",
            cadeira="ti",
            card="1336",
            situacao="guardado",
            estagio="execucao",
            proxima_jogada="corrigir pauta",
            ocasiao=Ocasiao(card="1336", chapeu="interfaces"),
            corpo="",
        ),
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_fila = fake_bin / "fila"
    fake_fila.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps([\n"
        "  {'msgid': 'm1', 'de': 'arquiteto', 'assunto': 'story liberada', 'corpo': 'corpo longo'},\n"
        "  {'msgid': 'm2', 'de': 'ia', 'assunto': 'revisar porta', 'corpo': 'detalhes'},\n"
        "]))\n",
        encoding="utf-8",
    )
    fake_fila.chmod(0o755)
    monkeypatch.setenv("PF_VALKEY_FIXTURE", str(fix_lousa))
    monkeypatch.setenv("PF_BIN", str(fake_bin))

    saida, rc = _ato_abrir(
        {"cadeira": "ti", "pergunta": "seguir com #1336", "casa_raiz": str(casa)}
    )
    assert rc == 0 and saida["ok"] is True
    assert saida["pauta"]["total_guardados"] == 1
    assert saida["pauta"]["cartas"] == 2
    assert "corrigir pauta" in saida["pauta"]["conteudo"]
    assert "caixa: 2 carta(s)" in saida["pauta"]["conteudo"]
    assert "story liberada" in saida["pauta"]["conteudo"]
    assert "corpo longo" not in saida["pauta"]["conteudo"]

    # 2. Lousa fora e fila falhando -> pauta diz que não conseguiu ler, nunca 0
    fix_lousa.write_text(json.dumps({"fora": True}), encoding="utf-8")
    fake_fila.write_text("#!/usr/bin/env python3\nimport sys; sys.stderr.write('valkey fora\\n'); sys.exit(3)\n", encoding="utf-8")
    fake_fila.chmod(0o755)

    saida_err, rc_err = _ato_abrir(
        {"cadeira": "ti", "pergunta": "oi", "casa_raiz": str(casa)}
    )
    assert rc_err == 0 and saida_err["ok"] is True
    assert "lousa: não foi possível ler" in saida_err["pauta"]["conteudo"]
    assert "caixa: não foi possível ler" in saida_err["pauta"]["conteudo"]
    assert "lousa: 0 guardados" not in saida_err["pauta"]["conteudo"]
    assert "caixa: 0 cartas" not in saida_err["pauta"]["conteudo"]
    assert saida_err["pauta"]["lousa_erro"]
    assert saida_err["pauta"]["caixa_erro"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, *sys.argv[1:]]))
