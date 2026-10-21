"""`release conferir copia`: toda materialização viva tem declaração (card #3763; arq:0022 §6.3; arq:0130 D4).

Prova, sem banco e sem balde reais (as portas `ler`, `listagem` e `plano` são trocadas por dicts no formato dos
coletores): o formato da linha `copia-de:`, o que a conferência acusa por defeito (sem modo, sem reprodutibilidade,
chave que não existe), a tabela que ninguém declara, o espelho que nenhuma impressão reclama, a paginação do balde e o
substrato que não responde. Não prova: os bancos e o balde de verdade (a rodada em produção do card).
"""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir"))

import copia  # noqa: E402
import predicados_acervo as pa  # noqa: E402

HEX_A = "a" * 64
HEX_B = "b" * 64
DIG_1 = "1" * 64
DIG_2 = "2" * 64


def _linha(**campos):
    base = {"familia": "impressao", "fonte": "o arquivo da obra", "chave": "id", "atributos": "texto,corte",
            "repoe": "acervo espelhar + acervo recortar", "modo": "materializada", "reproduzivel": "sim",
            "metodo": "acervo espelhar com o método declarado", "insumos": "sha256 do arquivo,digest do método",
            "migracao": "131"}
    base.update(campos)
    return "copia-de: " + " | ".join(f"{k}={v}" for k, v in base.items() if v is not None)


def _tab(schema, tabela, declaracao=None, comentario="Texto da tabela.", colunas=("id", "impressao_id")):
    texto = comentario if declaracao is None else (comentario + "\n" + declaracao if comentario else declaracao)
    return {"schema": schema, "tabela": tabela, "comentario": texto, "colunas": list(colunas)}


def _rag(**mudancas):
    tabelas = {
        "impressao": _tab("acervo", "impressao", _linha()),
        "secao": _tab("acervo", "secao", _linha(chave="impressao_id")),
        "obra": _tab("acervo", "obra"),
    }
    tabelas.update(mudancas)
    return [t for t in tabelas.values() if t is not None]


def _motor(**mudancas):
    ind = {"familia": "indice", "repoe": "motor rag indexar biblioteca", "atributos": "trechos,vetores",
           "migracao": "019"}
    tabelas = {
        "indice": _tab("motor", "indice", _linha(chave="id", **ind)),
        "vetor": _tab("motor", "vetor", _linha(chave="indice_id", **ind), colunas=("indice_id", "alvo_id")),
        "trecho": _tab("motor", "trecho", _linha(chave="impressao_id", **ind)),
    }
    tabelas.update(mudancas)
    return [t for t in tabelas.values() if t is not None]


class Bancos:
    """A porta `ler(banco, sql)`: o catálogo da raiz, as tabelas do rag e as do motor."""

    def __init__(self, rag=None, motor=None, golden=("acervo.obra; arquivo no balde",), fora=()):
        self.rag = _rag() if rag is None else rag
        self.motor = _motor() if motor is None else motor
        self.golden = list(golden)
        self.fora = set(fora)
        self.chamadas = []

    def __call__(self, banco, sql):
        self.chamadas.append((banco, sql))
        if banco in self.fora:
            raise pa.Indeterminavel(f"{banco}: fora do ar")
        if "substrato_golden" in sql:
            return self.golden
        assert "pg_class" in sql
        return self.rag if banco == "rag" else self.motor


def _espelho(objeto=HEX_A, digest=DIG_1, arquivo="espelho.md"):
    return {"objeto": f"espelho/{objeto}/{digest}/{arquivo}"}


def _balde(*itens):
    def listagem(colecao, prefixo):
        return list(itens) if colecao == "firma" and prefixo is None else []
    return listagem


def _plano(*orfaos):
    return lambda: list(orfaos)


def _rodar(alvo=None, bancos=None, itens_do_balde=(_espelho(), _espelho(HEX_B, DIG_2)), orfaos=(), listagem=None):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = copia.conferir_copia(alvo, "abc1234", como_json=True,
                                  portas=copia.Portas(ler=bancos or Bancos(),
                                                      listagem=listagem or _balde(*itens_do_balde),
                                                      plano=_plano(*orfaos)))
    return rc, json.loads(buf.getvalue())


def _item(dados, prefixo):
    return next(i for i in dados["itens"] if i["nome"].startswith(prefixo))


# --- o formato da declaração ---------------------------------------------------------------------

def test_a_declaracao_se_le_campo_a_campo():
    decl, forma = copia.ler_declaracao(_linha())
    assert forma == []
    assert decl["familia"] == "impressao" and decl["modo"] == "materializada" and decl["reproduzivel"] == "sim"
    assert copia.lista_do_campo(decl["atributos"]) == ["texto", "corte"]
    assert copia.defeitos_da_declaracao(decl, ["id", "impressao_id"]) == []


def test_a_linha_da_declaracao_e_a_que_comeca_por_copia_de_depois_do_comentario_da_tabela():
    comentario = "Texto da tabela.\n" + _linha() + "\nOutra linha."
    assert copia.linha_de_declaracao(comentario) == _linha()
    assert copia.linha_de_declaracao("Texto da tabela. Sem declaração.") is None
    assert copia.linha_de_declaracao(None) is None


def test_declaracao_sem_modo_sem_reprodutibilidade_ou_com_chave_que_nao_existe_tem_defeito():
    def defeitos(linha, colunas=("id",)):
        decl, forma = copia.ler_declaracao(linha)
        return forma + copia.defeitos_da_declaracao(decl, list(colunas))

    assert "sem modo" in defeitos(_linha(modo=None))
    assert "sem reproduzivel" in defeitos(_linha(reproduzivel=None))
    assert any("coluna da chave" in d for d in defeitos(_linha(chave="nao_existe")))
    assert any("modo fora da lista" in d for d in defeitos(_linha(modo="quando-der")))
    assert any("reproduzivel fora da lista" in d for d in defeitos(_linha(reproduzivel="talvez")))


def test_reproduzivel_sem_metodo_ou_sem_insumos_tem_defeito_e_nao_reproduzivel_pode_calar_os_dois():
    def defeitos(linha):
        decl, forma = copia.ler_declaracao(linha)
        return forma + copia.defeitos_da_declaracao(decl, ["id"])

    assert "sem metodo" in defeitos(_linha(metodo=None))
    assert "sem insumos" in defeitos(_linha(insumos=None))
    assert defeitos(_linha(reproduzivel="nao", metodo=None, insumos=None)) == []


def test_campo_mal_formado_repetido_ou_desconhecido_tem_defeito():
    _, forma = copia.ler_declaracao(_linha() + " | solto")
    assert any("mal formado" in f for f in forma)
    _, forma = copia.ler_declaracao(_linha() + " | modo=sob-demanda")
    assert any("repetido" in f for f in forma)
    _, forma = copia.ler_declaracao(_linha() + " | cor=azul")
    assert any("desconhecido" in f for f in forma)


def test_o_catalogo_nomeia_a_tabela_golden_pelo_schema_e_pelo_nome():
    nomeados = copia.golden_nomeado(["acervo.obra; arquivo no balde", "motor.indice.metodo; casado por conteudo",
                                     "rastreador.projecao"])
    assert {"acervo.obra", "motor.indice", "rastreador.projecao"} <= nomeados


# --- a classe, com tudo declarado ---------------------------------------------------------------------

def test_tudo_declarado_sai_0_e_conta_o_que_leu():
    rc, dados = _rodar()
    assert rc == 0
    assert all(i["estado"] == "conforme" for i in dados["itens"]) and len(dados["itens"]) == 3
    c = dados["contagem"]
    # banco: impressao e secao; indice: indice, vetor e trecho; balde: dois espelhos; obra é fonte e não conta
    assert (c["total"], c["declaradas"], c["nao_declaradas"], c["fontes"], c["sem_coletor"]) == (7, 7, 0, 1, 5)
    assert dados["ancora"].startswith("release conferir copia: 3 conforme · 0 divergente · 0 não consegui olhar — release abc1234")
    assert "materializações: 7 · declaradas 7 · não declaradas 0 · sem coletor 5" in dados["ancora"]


def test_a_tabela_declarada_aparece_com_o_modo_e_a_reprodutibilidade():
    _, dados = _rodar("indice")
    linha = next(a for a in dados["avisos"] if a.startswith("declarada: motor.indice"))
    assert "família indice" in linha and "modo materializada" in linha and "reproduzível" in linha


def test_so_o_substrato_pedido_e_lido():
    rc, dados = _rodar("indice")
    assert rc == 0 and [i["nome"] for i in dados["itens"]] == ["indice: tabelas do schema motor"]
    assert dados["alvo"] == "indice"


# --- a tabela que ninguém declara ----------------------------------------------------------------------

def test_tabela_do_banco_sem_declaracao_sai_1_e_vai_na_lista():
    bancos = Bancos(rag=_rag(log=_tab("acervo", "log")))
    rc, dados = _rodar("banco", bancos)
    assert rc == 1
    item = _item(dados, "banco")
    assert item["estado"] == "divergente" and "acervo.log" in item["motivo"]
    assert dados["substratos"]["banco"]["nao_declaradas"] == ["acervo.log"]
    assert dados["contagem"]["nao_declaradas"] == 1


def test_tabela_com_prefixo_de_fossil_e_assinalada():
    bancos = Bancos(rag=_rag(b=_tab("acervo", "_backup_fusao_20260815_obra"), m=_tab("acervo", "_mig_trecho"),
                             log=_tab("acervo", "log")))
    rc, dados = _rodar("banco", bancos)
    assert rc == 1
    assert "3 sem declaração" in _item(dados, "banco")["motivo"]
    assert "2 com prefixo de fóssil" in _item(dados, "banco")["motivo"]


def test_tabela_que_o_catalogo_nomeia_como_golden_e_fonte_e_nao_cobra_declaracao():
    bancos = Bancos(rag=_rag(), golden=["acervo.obra; arquivo no balde"])
    rc, dados = _rodar("banco", bancos)
    assert rc == 0
    assert dados["substratos"]["banco"]["fontes"] == ["acervo.obra"]
    sem_catalogo = Bancos(rag=_rag(), golden=[])
    rc, dados = _rodar("banco", sem_catalogo)
    assert rc == 1 and dados["substratos"]["banco"]["nao_declaradas"] == ["acervo.obra"]


def test_tabela_declarada_que_o_catalogo_tambem_nomeia_golden_vira_aviso_de_conflito():
    bancos = Bancos(golden=["acervo.impressao; parte-de obra", "acervo.obra"])
    rc, dados = _rodar("banco", bancos)
    assert rc == 0
    assert any(a.startswith("conflito: o catálogo nomeia acervo.impressao") for a in dados["avisos"])


def test_tabela_do_indice_sem_declaracao_sai_1():
    bancos = Bancos(motor=_motor(geracao=_tab("motor", "geracao")))
    rc, dados = _rodar("indice", bancos)
    assert rc == 1 and "motor.geracao" in _item(dados, "indice")["motivo"]


# --- a declaração com defeito ---------------------------------------------------------------------------

def test_declaracao_sem_modo_e_acusada():
    bancos = Bancos(rag=_rag(impressao=_tab("acervo", "impressao", _linha(modo=None))))
    rc, dados = _rodar("banco", bancos)
    assert rc == 1
    assert "acervo.impressao" in _item(dados, "banco")["motivo"] and "sem modo" in _item(dados, "banco")["motivo"]
    assert dados["substratos"]["banco"]["com_defeito"][0]["tabela"] == "acervo.impressao"
    assert dados["contagem"]["declaradas"] == 1 and dados["contagem"]["nao_declaradas"] == 1


def test_declaracao_sem_a_linha_de_reprodutibilidade_e_acusada():
    bancos = Bancos(motor=_motor(indice=_tab("motor", "indice", _linha(chave="id", reproduzivel=None))))
    rc, dados = _rodar("indice", bancos)
    assert rc == 1 and "sem reproduzivel" in _item(dados, "indice")["motivo"]


def test_reproduzivel_sem_metodo_e_acusada():
    bancos = Bancos(rag=_rag(impressao=_tab("acervo", "impressao", _linha(metodo=None))))
    rc, dados = _rodar("banco", bancos)
    assert rc == 1 and "sem metodo" in _item(dados, "banco")["motivo"]


def test_chave_que_a_tabela_nao_tem_e_acusada():
    bancos = Bancos(rag=_rag(secao=_tab("acervo", "secao", _linha(chave="nao_existe"))))
    rc, dados = _rodar("banco", bancos)
    assert rc == 1 and "coluna da chave" in _item(dados, "banco")["motivo"]


def test_familia_declarada_nao_reproduzivel_vai_a_parte():
    nao = _linha(familia="exportacao", reproduzivel="nao", metodo=None, insumos=None)
    bancos = Bancos(rag=_rag(exp=_tab("acervo", "exportacao", nao)))
    rc, dados = _rodar("banco", bancos)
    assert rc == 0
    linha = next(a for a in dados["avisos"] if a.startswith("famílias declaradas não reproduzíveis"))
    assert linha.endswith("exportacao")
    _, limpo = _rodar("banco")
    assert next(a for a in limpo["avisos"] if a.startswith("famílias declaradas não reproduzíveis")).endswith("nenhuma")


# --- o balde ------------------------------------------------------------------------------------------------

def test_espelho_que_nenhuma_impressao_reclama_aparece_na_lista():
    orfao = f"{HEX_B}/{DIG_2}"
    rc, dados = _rodar("balde", orfaos=(orfao,))
    assert rc == 1
    item = _item(dados, "balde")
    assert item["estado"] == "divergente" and orfao in item["motivo"] and "1 espelho(s) que nenhuma impressão reclama" in item["motivo"]
    b = dados["substratos"]["balde"]
    assert (b["espelhos"], b["declarados"], b["orfaos"]) == (2, 1, [orfao])
    assert dados["contagem"]["nao_declaradas"] == 1


def test_objeto_sob_espelho_sem_a_chave_no_endereco_e_acusado():
    sujo = {"objeto": "espelho/nao-e-hex/arquivo.md"}
    rc, dados = _rodar("balde", itens_do_balde=(_espelho(), sujo))
    assert rc == 1 and "sem o sha do arquivo e o digest no endereço" in _item(dados, "balde")["motivo"]
    assert dados["substratos"]["balde"]["sem_chave"] == ["espelho/nao-e-hex/arquivo.md"]


def test_o_que_mora_na_pasta_do_espelho_nao_e_espelho_a_mais_nem_objeto_sem_chave():
    """Medido em produção (21/10/2026): além de espelho.md e mapa.json, a pasta traz indice.json, e 988 deles saiam como
    objeto sem a chave no endereço."""
    ao_lado = (_espelho(arquivo="mapa.json"), _espelho(arquivo="indice.json"))
    rc, dados = _rodar("balde", itens_do_balde=(_espelho(), *ao_lado))
    assert rc == 0
    assert dados["substratos"]["balde"]["espelhos"] == 1 and dados["substratos"]["balde"]["sem_chave"] == []
    prefixado = {"objeto": f"acervo/espelho/{HEX_A}/{DIG_1}/indice.json"}
    rc, dados = _rodar("balde", itens_do_balde=(prefixado,))
    assert rc == 0 and dados["substratos"]["balde"]["espelhos"] == 1


def test_arquivo_fundo_demais_na_pasta_do_espelho_nao_leva_a_chave_do_endereco():
    fundo = {"objeto": f"espelho/{HEX_A}/{DIG_1}/sub/x.json"}
    rc, dados = _rodar("balde", itens_do_balde=(_espelho(), fundo))
    assert rc == 1 and dados["substratos"]["balde"]["sem_chave"] == [fundo["objeto"]]


def test_o_objeto_original_e_fonte_e_nao_copia():
    rc, dados = _rodar("balde", itens_do_balde=(_espelho(), {"objeto": f"acervo/{HEX_A}"}))
    assert rc == 0
    assert dados["substratos"]["balde"]["objetos_originais"] == 1 and dados["contagem"]["total"] == 1


def test_sem_a_familia_do_espelho_declarada_todos_os_espelhos_ficam_sem_declaracao():
    bancos = Bancos(rag=_rag(impressao=_tab("acervo", "impressao"), secao=_tab("acervo", "secao")))
    rc, dados = _rodar("balde", bancos)
    assert rc == 1
    assert "nenhuma tabela do rag declara a família impressao com o atributo texto" in _item(dados, "balde")["motivo"]
    assert dados["substratos"]["balde"]["declarados"] == 0


def test_balde_no_teto_da_rota_lista_por_faixa_e_nao_perde_espelho():
    cheio = [{"objeto": f"acervo/{i:064x}"} for i in range(pa.TETO_LISTAGEM)]

    def listagem(colecao, prefixo):
        if colecao != "firma":
            return []
        if prefixo is None:
            return cheio
        return [_espelho(), _espelho(HEX_B, DIG_2)] if prefixo == "espelho/a" else []

    rc, dados = _rodar("balde", listagem=listagem)
    assert rc == 0 and dados["substratos"]["balde"]["espelhos"] == 2


def test_faixa_que_chega_ao_teto_e_indeterminavel_e_sai_5():
    def listagem(colecao, prefixo):
        if colecao != "firma":
            return []
        return [{"objeto": f"acervo/{i:064x}"} for i in range(pa.TETO_LISTAGEM)]

    rc, dados = _rodar("balde", listagem=listagem)
    assert rc == 5 and _item(dados, "balde")["estado"] == "indeterminavel"


def test_o_plano_de_orfaos_do_acervo_fora_do_ar_e_indeterminavel():
    def plano():
        raise pa.Indeterminavel("balde: acervo apagar saiu 3")

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = copia.conferir_copia("balde", "abc1234", como_json=True,
                                  portas=copia.Portas(ler=Bancos(), listagem=_balde(_espelho()), plano=plano))
    assert rc == 5 and json.loads(buf.getvalue())["itens"][0]["estado"] == "indeterminavel"


def _acervo_falso(tmp_path, corpo, codigo=0):
    script = tmp_path / "acervo"
    script.write_text(f"#!/bin/sh\ncat <<'FIM'\n{corpo}\nFIM\nexit {codigo}\n")
    script.chmod(0o755)
    return str(script)


def test_o_plano_seco_do_acervo_vira_a_lista_de_orfaos(tmp_path):
    corpo = json.dumps({"n": 1, "itens": [{"bucket": "firma", "hex": HEX_B, "digest": DIG_2, "objetos": ["x"]}]})
    assert copia.plano_de_orfaos(_acervo_falso(tmp_path, corpo)) == [f"{HEX_B}/{DIG_2}"]


def test_plano_que_conta_mais_do_que_lista_nao_perde_o_orfao(tmp_path):
    corpo = json.dumps({"n": 3, "itens": [{"hex": HEX_B, "digest": DIG_2}]})
    orfaos = copia.plano_de_orfaos(_acervo_falso(tmp_path, corpo))
    assert len(orfaos) == 3 and orfaos[0] == f"{HEX_B}/{DIG_2}" and "não listado" in orfaos[1]


def test_plano_sem_orfao_e_lista_vazia(tmp_path):
    assert copia.plano_de_orfaos(_acervo_falso(tmp_path, json.dumps({"n": 0, "itens": []}))) == []


def test_plano_seco_que_falha_ou_responde_torto_e_indeterminavel(tmp_path):
    for corpo, codigo in (('{"n": 0}', 3), ("isto não é json", 0), ('{"itens": []}', 0)):
        try:
            copia.plano_de_orfaos(_acervo_falso(tmp_path, corpo, codigo))
        except pa.Indeterminavel as e:
            assert str(e).startswith("balde: ")
        else:
            raise AssertionError(f"devia ser indeterminável: {corpo!r} saindo {codigo}")
    try:
        copia.plano_de_orfaos(str(tmp_path / "nao-existe"))
    except pa.Indeterminavel as e:
        assert str(e).startswith("balde: ")
    else:
        raise AssertionError("acervo que não existe devia ser indeterminável")


# --- substrato que não responde, uso errado, texto ----------------------------------------------------------

def test_banco_do_motor_fora_do_ar_sai_5_e_nao_mascara_o_resto():
    rc, dados = _rodar(bancos=Bancos(fora=("motor",)))
    assert rc == 5
    assert _item(dados, "indice")["estado"] == "indeterminavel"
    assert _item(dados, "banco")["estado"] == "conforme" and _item(dados, "balde")["estado"] == "conforme"


def test_divergencia_pesa_mais_que_substrato_que_nao_respondeu():
    bancos = Bancos(rag=_rag(log=_tab("acervo", "log")), fora=("motor",))
    rc, _ = _rodar(bancos=bancos)
    assert rc == 1


def test_banco_rag_fora_do_ar_deixa_banco_e_balde_indeterminaveis():
    rc, dados = _rodar(bancos=Bancos(fora=("rag",)))
    assert rc == 5
    assert _item(dados, "banco")["estado"] == "indeterminavel" and _item(dados, "balde")["estado"] == "indeterminavel"


def test_substrato_desconhecido_sai_2():
    rc, dados = _rodar("nuvem")
    assert rc == 2 and "substrato desconhecido" in dados["erro"]


def test_a_primeira_linha_do_texto_e_a_ancora_com_a_contagem(capsys):
    rc = copia.conferir_copia(None, "abc1234", portas=copia.Portas(
        ler=Bancos(rag=_rag(log=_tab("acervo", "log"))), listagem=_balde(_espelho()), plano=_plano()))
    saida = capsys.readouterr().out.splitlines()
    assert rc == 1
    assert saida[0].startswith("release conferir copia: 2 conforme · 1 divergente · 0 não consegui olhar — release abc1234")
    assert "materializações: " in saida[0] and "sem coletor 5" in saida[0]
    assert any(l.strip().startswith("NAO banco:") for l in saida)
    assert any("sem coletor (5)" in l for l in saida)


def test_o_que_fica_sem_coletor_e_dito_com_o_porque():
    _, dados = _rodar()
    nomes = [s["familia"] for s in dados["sem_coletor"]]
    assert nomes == ["modelo formal gerado", "unit gerada pelo bot", "CLAUDE.md da fita",
                     "instruções de Project e preferências do claude.ai", "projeção de card"]
    assert all(s["porque"] for s in dados["sem_coletor"])


def test_particao_e_visao_ficam_fora_da_leitura_das_tabelas():
    bancos = Bancos()
    _rodar("banco", bancos)
    sqls = [sql for banco, sql in bancos.chamadas if "pg_class" in sql]
    assert sqls and all("not c.relispartition" in s and "relkind in ('r', 'p', 'm')" in s for s in sqls)
    assert "n.nspname = 'acervo'" in sqls[0]
