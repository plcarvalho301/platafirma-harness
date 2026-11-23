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

from leitura import casa_db, resolvedor
from leitura.recusa import CAMPOS, Recusa, Recusas, escrever_lista
from leitura.retrato import SQL, _causa, literal

SAIDA_USO = 2
SAIDA_DEP = 3
SAIDA_NEGADO = 4
SAIDA_FALHA = 5


def _configurar_versao_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
    return cfg


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
    _configurar_versao_yaml(tmp_path, monkeypatch)

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


# ==================================================================== t9: pedido e consulta por nome
def test_conferencia_de_forma_acumula_erros_sem_abrir_o_banco() -> None:
    from busca.pedido import codificar_cursor, receber_pedido

    # Sem termo e sem --classe -> termo-ausente
    with pytest.raises(Recusas) as exc_vazio:
        receber_pedido([])
    assert [e.codigo for e in exc_vazio.value.erros] == ["termo-ausente"]

    # Predicados sem --classe -> classe-ausente + passos-fora-da-faixa + alvo-mal-formado juntos
    with pytest.raises(Recusas) as exc_multi:
        receber_pedido(["--prop", "x=1", "--ligacao", "confere/9=---", "--sem-ligacao", "usa/2=alvo"])
    codigos = [e.codigo for e in exc_multi.value.erros]
    assert "classe-ausente" in codigos
    assert codigos.count("passos-fora-da-faixa") == 2  # noqa: PLR2004 - 9 fora da faixa e /2 em --sem-ligacao
    assert "alvo-mal-formado" in codigos

    # Termo só de sinais -> termo-sem-letra
    with pytest.raises(Recusas) as exc_sinais:
        receber_pedido(["---"])
    assert [e.codigo for e in exc_sinais.value.erros] == ["termo-sem-letra"]

    # Texto longo demais -> texto-longo-demais
    with pytest.raises(Recusas) as exc_longo:
        receber_pedido(["a" * 201])
    assert [e.codigo for e in exc_longo.value.erros] == ["texto-longo-demais"]

    # Argumento fora do modo (termo + --classe, --ligacoes com --classe, --cursor no modo nome)
    with pytest.raises(Recusas) as exc_modo:
        receber_pedido(["gabarito", "--classe", "shape", "--ligacoes", "sem"])
    assert [e.codigo for e in exc_modo.value.erros] == ["argumento-fora-do-modo", "argumento-fora-do-modo"]

    with pytest.raises(Recusas) as exc_cur_nome:
        receber_pedido(["gabarito", "--cursor", "qualquer"])
    assert [e.codigo for e in exc_cur_nome.value.erros] == ["argumento-fora-do-modo"]

    # Continuação ilegível e divergente
    with pytest.raises(Recusas) as exc_ileg:
        receber_pedido(["--classe", "gabarito", "--cursor", "nao-e-json-valido!!!"])
    assert [e.codigo for e in exc_ileg.value.erros] == ["continuacao-ilegivel"]

    ped_base = receber_pedido(["--classe", "gabarito", "--prop", "a=1", "--prop", "b=2"])
    ped_outra_ordem = receber_pedido(["--classe", "gabarito", "--prop", "b=2", "--prop", "a=1"])
    assert ped_base.resumo == ped_outra_ordem.resumo

    token_bom = codificar_cursor(ordem=1, chave="gabarito:a", fornada="019a0000-0000-7000-8000-000000000001", resumo=ped_base.resumo)
    ped_pag2 = receber_pedido(["--classe", "gabarito", "--prop", "b=2", "--prop", "a=1", "--cursor", token_bom])
    assert ped_pag2.continuacao is not None and ped_pag2.continuacao.chave == "gabarito:a"

    with pytest.raises(Recusas) as exc_div:
        receber_pedido(["--classe", "gabarito", "--prop", "a=outro", "--cursor", token_bom])
    assert [e.codigo for e in exc_div.value.erros] == ["continuacao-divergente"]


def test_consulta_por_nome_demanda_nao_corta_dentro_da_palavra_e_qualificador_vira_condicao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from busca.nome import consultar_por_nome, gerar_cortes_qualificador
    from busca.pedido import receber_pedido

    # "demanda" contém "de" dentro da palavra, mas não em fronteira de palavra
    assert gerar_cortes_qualificador("demanda") == []
    cortes = gerar_cortes_qualificador("gabaritos de modelos formais")
    assert [(c.nucleo, c.qualificador) for c in cortes] == [("gabaritos", "modelos formais")]

    _configurar_versao_yaml(tmp_path, monkeypatch)

    class _ConCorte:
        def resolver_nomes(self, termos: list[str]) -> list[dict]:
            mapa = {
                "gabaritos": [{"passo": 1, "chave": "gabarito", "classe": "shape", "e_classe": True, "rotulo": "Gabarito", "definicao": "d"}],
                "modelos formais": [{"passo": 1, "chave": "capacidade:ontologia", "classe": "capacidade", "e_classe": False, "rotulo": "Ontologia", "definicao": "d"}],
            }
            out: list[dict] = []
            for idx, t in enumerate(termos, start=1):
                norm = t.lower().strip()
                itens = mapa.get(norm)
                if not itens:
                    out.append({"ord": idx, "norm": norm, "passo": None, "chave": None, "classe": None, "e_classe": None})
                else:
                    out.extend({"ord": idx, "norm": norm, **it} for it in itens)
            return out

        def consultar(self, sql: str, *params: object) -> list[dict]:
            if sql is casa_db.SQL_UUID_DA_CLASSE:
                return [{"uuid": "u-cls-gab", "classe": "gabarito"}]
            if sql is resolvedor.SQL_FICHA:
                return [{"uuid": "u-cap-ont", "chave": params[0], "classe": "capacidade", "classe_uuid": "u-cls-cap"}]
            if "alcance_nivel" in sql:
                return [{"ficha": "u-gab-fw", "pai": "u-cap-ont", "propriedade": "confere", "posicao": 1}]
            if "consultar_fichas" in sql:
                return [{
                    "total": 1, "antes": 0, "digest": "v1:" + "b" * 64, "fornada": "019a0000-0000-7000-8000-000000000002",
                    "uuid": "u-gab-fw", "ordem": 1, "chave": "gabarito:framework-da-ontologia", "classe": "gabarito",
                    "rotulo": "Framework da ontologia", "estado": None,
                }]
            if "rastro" in sql:
                return [
                    {"uuid": "u-cap-ont", "chave_humana": "capacidade:ontologia"},
                    {"uuid": "u-gab-fw", "chave_humana": "gabarito:framework-da-ontologia"},
                ]
            raise AssertionError(f"SQL inesperado: {sql[:50]}")

    ped = receber_pedido(["gabaritos de modelos formais"])
    with casa_db.retrato(conexao=_ConCorte(), autorizador=lambda _c, _s: True) as sessao:
        res = consultar_por_nome(sessao, ped)

    assert res["tipo_resultado"] == "condicao-por-nome"
    assert res["classe"] == "gabarito"
    assert res["condicao"] == {"nucleo": "gabaritos", "qualificador": "modelos formais", "chaves": ["capacidade:ontologia"]}
    assert [f["chave"] for f in res["consulta"]["fichas"]] == ["gabarito:framework-da-ontologia"]
