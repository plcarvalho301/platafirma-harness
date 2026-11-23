# componente: componente:verbo-busca
"""Story 4427: suíte de contrato do consultar e do leitor do banco casa (`test_busca_consultar.py`)."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
import sys

if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from leitura import casa_db, resolvedor  # noqa: E402
from leitura.recusa import CAMPOS, Recusa, Recusas, escrever_lista  # noqa: E402
from leitura.retrato import SQL, _causa, literal  # noqa: E402

SAIDA_USO = 2
SAIDA_DEP = 3
SAIDA_NEGADO = 4
SAIDA_FALHA = 5


# ==================================================================== t8: retrato, recusa, resolvedor e leitor
def test_literal_liga_nulo_como_texto_vazio() -> None:
    assert literal(None) == "''"


@pytest.mark.parametrize(
    ("mensagem_psql", "saida_esperada", "codigo_esperado"),
    [
        ("psql: error: connection to server failed: Connection refused", SAIDA_DEP, "banco-indisponivel"),
        ('FATAL:  too many connections for role "analise_leitura"', SAIDA_DEP, "conexoes-esgotadas"),
        ("FATAL:  remaining connection slots are reserved", SAIDA_DEP, "conexoes-esgotadas"),
        ("ERROR:  permission denied for table nome", SAIDA_NEGADO, "acesso-negado"),
        ("ERROR:  canceling statement due to statement timeout", SAIDA_FALHA, "prazo-estourado"),
        ("ERROR:  erro interno arbitrario no servidor", SAIDA_FALHA, "falha-interna"),
    ],
)
def test_codigos_de_falha_do_retrato(mensagem_psql: str, saida_esperada: int, codigo_esperado: str) -> None:
    rec = _causa(mensagem_psql)
    assert rec.saida == saida_esperada
    assert rec.codigo == codigo_esperado
    assert mensagem_psql not in rec.cura


def test_escrever_lista_emite_json_com_erro_e_erros_na_ultima_linha() -> None:
    r1 = Recusa(SAIDA_USO, "propriedade-desconhecida", onde="--prop", recebido="x", regra="r", cura="c1", proximo="p1")
    r2 = Recusa(SAIDA_USO, "estado-desconhecido", onde="--estado", recebido="y", regra="r", cura="c2", proximo="p2")
    pacote = Recusas([r1, r2])
    assert pacote.saida == SAIDA_USO
    fluxo = io.StringIO()
    rc = escrever_lista(pacote.erros, fluxo=fluxo)
    assert rc == SAIDA_USO
    linhas = fluxo.getvalue().splitlines()
    assert len(linhas) == 1
    dados = json.loads(linhas[-1])
    assert set(dados) == {"erro", "erros"}
    assert list(dados["erro"]) == list(CAMPOS)
    assert len(dados["erros"]) == 2  # noqa: PLR2004 - dois erros injetados na lista
    assert dados["erro"] == dados["erros"][0]
    assert [e["codigo"] for e in dados["erros"]] == ["propriedade-desconhecida", "estado-desconhecido"]


def test_cinco_arquivos_sql_novos_existem_no_leitor() -> None:
    for nome in (
        "resolver_nomes.sql",
        "catalogo_da_classe.sql",
        "alcance_nivel.sql",
        "consultar_fichas.sql",
        "rastro.sql",
        "valores_da_propriedade.sql",
    ):
        arq = SQL / nome
        assert arq.is_file(), f"faltou {nome}"
        assert arq.read_text(encoding="utf-8").strip()


def test_ficha_inteira_com_e_sem_ligacoes() -> None:
    class _ConFalsa:
        def __init__(self) -> None:
            self.sqls: list[str] = []

        def consultar(self, sql: str, *_p: object) -> list[dict]:
            self.sqls.append(sql)
            if sql is resolvedor.SQL_FICHA_INTEIRA:
                return [{
                    "ficha": {
                        "chave": "gabarito:x",
                        "classe": "gabarito",
                        "dados": {},
                        "ligacoes": {"saida": {"confere": ["capacidade:ontologia"]}, "chegada": {"usa": ["missao:y"]}},
                    },
                }]
            return [{"ficha": {"chave": "gabarito:x", "classe": "gabarito", "dados": {}}}]

    con = _ConFalsa()
    f = resolvedor.Ficha("u1", "gabarito:x", "gabarito", "c1")
    com = resolvedor.ficha_inteira(con, f, com_ligacoes=True)
    sem = resolvedor.ficha_inteira(con, f, com_ligacoes=False)
    assert com["ligacoes"] == {"saida": {"confere": ["capacidade:ontologia"]}, "chegada": {"usa": ["missao:y"]}}
    assert "ligacoes" not in sem


def test_configuracao_versao_da_classe_estrita_no_leitor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ausente = tmp_path / "nao-existe.yaml"
    monkeypatch.setenv("PF_VERSAO_CLASSE_YAML", str(ausente))
    with pytest.raises(Recusa) as exc_ausente:
        casa_db.carregar_eventos_da_versao()
    assert exc_ausente.value.saida == SAIDA_FALHA
    assert exc_ausente.value.codigo == "falha-interna"

    invalido = tmp_path / "invalido.yaml"
    invalido.write_text("versao: 1\nchave_extra: 1\n", encoding="utf-8")
    monkeypatch.setenv("PF_VERSAO_CLASSE_YAML", str(invalido))
    with pytest.raises(Recusa) as exc_inv:
        casa_db.carregar_eventos_da_versao()
    assert exc_inv.value.saida == SAIDA_FALHA
    assert exc_inv.value.codigo == "falha-interna"

    valido = tmp_path / "valido.yaml"
    valido.write_text(
        "versao: 1\n"
        "fontes:\n"
        "  - fornada-da-classe\n"
        "  - iniciou-do-dado-vigente\n"
        "  - iniciou-da-ligacao-vigente\n"
        "  - evento-que-cita-a-classe\n"
        "casos:\n"
        "  shape: [fornada-de-toda-classe]\n"
        "  dicionario: [fornada-de-todo-dicionario, fornada-de-todo-valor]\n"
        "eventos:\n"
        "  - modelos-formais.operacao-em-lote.olaria:olaria\n"
        "  - modelos-formais.pontual.olaria:olaria\n"
        "mais_recente: [ocorrido_em desc, uuid desc]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PF_VERSAO_CLASSE_YAML", str(valido))
    eventos = casa_db.carregar_eventos_da_versao()
    assert eventos == [
        "modelos-formais.operacao-em-lote.olaria:olaria",
        "modelos-formais.pontual.olaria:olaria",
    ]


def test_lista_fixa_de_colunas_declara_classe_alvo_para_capacidade_e_mae() -> None:
    assert casa_db.COLUNAS_SHAPE["capacidade"].classe_alvo == "capacidade"
    assert casa_db.COLUNAS_SHAPE["mae"].classe_alvo == "shape"
    assert casa_db.COLUNAS_SHAPE["raiz"].classe_alvo == "shape"
    assert casa_db.COLUNAS_DICIONARIO["capacidade"].classe_alvo == "capacidade"


def test_autorizacao_cacheada_uma_vez_por_classe_e_filtragem_mista() -> None:
    perguntadas: list[tuple[str, str | None]] = []

    def autorizador(classe: str, sujeito: str | None) -> bool:
        perguntadas.append((classe, sujeito))
        return classe != "segredo"

    class _ConNomes:
        def consultar(self, _sql: str, *_p: object) -> list[dict]:
            return [
                {"ord": 1, "norm": "misto", "passo": 1, "chave": "gabarito:a", "classe": "gabarito",
                 "e_classe": False, "rotulo": "A", "definicao": "da"},
                {"ord": 1, "norm": "misto", "passo": 1, "chave": "gabarito:b", "classe": "gabarito",
                 "e_classe": False, "rotulo": "B", "definicao": "db"},
                {"ord": 1, "norm": "misto", "passo": 2, "chave": "segredo:s", "classe": "segredo",
                 "e_classe": False, "rotulo": "S", "definicao": "ds"},
                {"ord": 2, "norm": "so segredo", "passo": 1, "chave": "segredo:x", "classe": "segredo",
                 "e_classe": False, "rotulo": "X", "definicao": "dx"},
            ]

    with casa_db.retrato({"sujeito": "suj-1"}, conexao=_ConNomes(), autorizador=autorizador) as sessao:
        res = sessao.resolver_nomes(["misto", "so segredo"])

    assert perguntadas == [("gabarito", "suj-1"), ("segredo", "suj-1")]
    chaves_ord1 = [ln["chave"] for ln in res.linhas if ln["ord"] == 1 and ln["chave"]]
    assert chaves_ord1 == ["gabarito:a", "gabarito:b"]
    assert res.ords_negados == frozenset({2})


def test_caminhada_bfs_em_grafo_com_ciclo_e_empate_refaz_rastro_so_da_pagina(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = tmp_path / "versao.yaml"
    cfg.write_text(
        "versao: 1\n"
        "fontes: [fornada-da-classe, iniciou-do-dado-vigente, iniciou-da-ligacao-vigente, evento-que-cita-a-classe]\n"
        "casos:\n"
        "  shape: [fornada-de-toda-classe]\n"
        "  dicionario: [fornada-de-todo-dicionario, fornada-de-todo-valor]\n"
        "eventos: [modelos-formais.operacao-em-lote.olaria:olaria]\n"
        "mais_recente: [ocorrido_em desc, uuid desc]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PF_VERSAO_CLASSE_YAML", str(cfg))

    rastreados: list[list[str]] = []

    class _ConGrafo:
        def consultar(self, sql: str, *params: object) -> list[dict]:
            if "alcance_nivel" in sql:
                fronteira = list(params[0])  # type: ignore[arg-type]
                if fronteira == ["u-alvo"]:
                    return [
                        {"ficha": "u-p1", "pai": "u-alvo", "propriedade": "confere", "posicao": 1},
                        {"ficha": "u-p2", "pai": "u-alvo", "propriedade": "confere", "posicao": 2},
                    ]
                if set(fronteira) == {"u-p1", "u-p2"}:
                    # Ciclo de volta para u-alvo e u-p1 + dois caminhos empatados até u-final
                    # (DISTINCT ON já devolve u-p1 antes de u-p2 pela chave_humana)
                    return [
                        {"ficha": "u-alvo", "pai": "u-p1", "propriedade": "usa", "posicao": 1},
                        {"ficha": "u-p1", "pai": "u-p2", "propriedade": "usa", "posicao": 1},
                        {"ficha": "u-final", "pai": "u-p1", "propriedade": "usa", "posicao": 1},
                        {"ficha": "u-fora-pagina", "pai": "u-p2", "propriedade": "usa", "posicao": 2},
                    ]
                return []
            if "consultar_fichas" in sql:
                return [{
                    "total": 2,
                    "antes": 0,
                    "digest": "v1:" + "a" * 64,
                    "fornada": "019a0000-0000-7000-8000-000000000001",
                    "uuid": "u-final",
                    "ordem": 1,
                    "chave": "gabarito:final",
                    "classe": "gabarito",
                    "rotulo": "Final",
                    "estado": None,
                }]
            if "rastro" in sql:
                uuids = list(params[0])  # type: ignore[arg-type]
                rastreados.append(uuids)
                mapa = {
                    "u-alvo": "capacidade:ontologia",
                    "u-p1": "gabarito:intermediario-1",
                    "u-final": "gabarito:final",
                }
                return [{"uuid": u, "chave_humana": mapa[u]} for u in uuids]
            raise AssertionError(f"SQL inesperado: {sql[:50]}")

    pred = casa_db.PredicadoLigacao(n=1, propriedade_id="prop-1", sentido="saida", alvos=("u-alvo",), passos=3)
    with casa_db.retrato(conexao=_ConGrafo(), autorizador=lambda _c, _s: True) as sessao:
        res = sessao.consultar_fichas({"classes_uuids": ["c-gab"], "ligacoes": [pred]}, tamanho_pagina=1)

    assert len(res["fichas"]) == 1
    assert res["fichas"][0]["caminho"] == [
        {"de": "capacidade:ontologia", "ligacao": "confere", "para": "gabarito:intermediario-1"},
        {"de": "gabarito:intermediario-1", "ligacao": "usa", "para": "gabarito:final"},
    ]
    # u-fora-pagina NÃO entrou na consulta de rastro
    assert rastreados == [["u-alvo", "u-final", "u-p1"]]
