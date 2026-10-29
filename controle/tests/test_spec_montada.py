# Montagem na leitura da spec (arq:0126 §11 a §13): o `Sobre:` vira a lista de referentes, a
# consulta é uma só, e o render diz o que o golden record serve e o que ainda falta nele. Sem
# banco: a consulta é texto, e o `_q` do cliente é trocado por um dublê.
import importlib.machinery
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACERVO = os.path.join(REPO, "bin", "_acervo")
sys.path.insert(0, ACERVO)

import _spec_montada as sm  # noqa: E402


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


casa = _carrega("acervo_casa_montada", "casa")

CORPO = ("# Spec — o verbo acervo\n\nEspécie: spec\n"
         "- **Sobre:** verbo acervo; capacidade conhecimento; stack rag\n"
         "Estado: no ar, conferida contra produção em 2026-10-11\n\n"
         "## Em uma tela\n\nSobre: stack outra\n")

DADOS = {
    "fichas": [{"classe": "verbo", "chave": "acervo"}, {"classe": "capacidade",
                                                         "chave": "conhecimento"},
               {"classe": "stack", "chave": "rag"}],
    "capacidades": [{"slug": "conhecimento", "rotulo": "conhecimento", "descricao": None,
                     "pai": None}],
    "stacks": [{"slug": "rag", "papel": "recuperacao: extrator, indice e API do acervo",
                "critico": False, "repo": "platafirma-conhecimento",
                "compose": ["/opt/platafirma/current/conhecimento/rag/docker-compose.yml"],
                "segredos": ["/srv/platafirma/casa/segredos/rag/"],
                "reversao": {"via": "promover", "quem": "claudinho-TI", "janela_min": 1,
                             "estado": "indice vetorial em volume", "provado_em": "2026-08-21 — x",
                             "nota": "overlay de GPU entra na volta"},
                "instancias": []}],
    "verbos": [{"slug": "acervo", "capacidade": "conhecimento", "dono": "dados",
                "estado": "servido", "descricao": "opera o acervo", "sucessor": None,
                "instancias": []}],
    "consumo": [{"verbo": "acervo", "servico": "motor_acervo_rest", "caminho": None,
                 "versao_min": None, "atos": ["ler", "listar"]}],
    "acesso": [{"verbo": "acervo", "recurso": "acervo.casa", "modo": "le", "atos": ["ler"]}],
    "segredos_env": [{"verbo": "acervo", "variavel": "RAG_API_TOKEN"}],
    "documentos": [{"especie": "adr", "chave": "arq:0126", "titulo": "Spec é a referência"}],
    "conferida_em": "2026-10-11",
}


def test_referentes_so_do_cabecalho_e_na_ordem():
    assert sm.referentes_do_sobre(CORPO) == [("verbo", "acervo"), ("capacidade", "conhecimento"),
                                            ("stack", "rag")]
    assert sm.referentes_do_sobre("# T\n\nEspécie: spec\n\n## A\n") == []
    assert sm.referentes_do_sobre("# T\n\nSobre: verbo:fila, ???, verbo fila\n") == [
        ("verbo", "fila")]


def test_sql_e_uma_consulta_com_os_referentes():
    refs = sm.referentes_do_sobre(CORPO)
    q = sm.sql(casa._lit, refs, "00000000-0000-0000-0000-000000000001")
    assert q.strip().startswith("select json_build_object(")
    assert "array['acervo']::text[]" in q and "array['rag']::text[]" in q
    assert "e.classe = 'verbo' and e.chave_humana = 'acervo'" in q   # a peça é o 1º referente


def test_documentos_que_declaram_a_peca_saem_da_ligacao_sobre():
    """#4045: o Sobre: é a ligação «sobre» que sai da ficha do documento, de mesmo id da linha de acervo.casa;
    casa_referente saiu. A espécie vem de acervo.casa_especie, que cobre a classe com shape e a espécie antiga."""
    q = " ".join(sm.sql(casa._lit, [("verbo", "acervo")], "00000000-0000-0000-0000-000000000001").split())
    assert "casa_referente" not in q
    assert "from acervo.entidade_relacao r join acervo.entidade e on e.id = r.para_id" in q
    assert "join acervo.casa c on c.id = r.de_id join acervo.casa_especie es on es.casa_id = c.id" in q
    assert "where r.tipo = 'sobre'" in q


def test_listar_sobre_le_a_ligacao_sobre(monkeypatch):
    consultas = []
    monkeypatch.setattr(casa, "_entidade", lambda classe, chave: ("verbo", "acervo", "f-1"))
    monkeypatch.setattr(casa, "_q", lambda sql, alvo="", falhar=True: consultas.append((sql, alvo)) or [])
    monkeypatch.setattr(casa, "_fonte", lambda: None)
    monkeypatch.setattr(casa, "txt_fonte", lambda f: "fonte")
    assert casa.sobre("verbo", "acervo", None, False) == 0
    [(sql, alvo)] = consultas
    sql = " ".join(sql.split())
    assert alvo == "acervo.entidade_relacao" and "casa_referente" not in sql
    assert "from acervo.entidade_relacao r join acervo.casa c on c.id = r.de_id" in sql
    assert "r.tipo = 'sobre' and r.para_id = 'f-1'::uuid" in sql


def test_render_monta_cada_bloco_e_segredo_so_por_referencia():
    texto = sm.render(DADOS, sm.referentes_do_sobre(CORPO))
    assert "## Montado na leitura" in texto
    assert "Conferida contra produção: 2026-10-11" in texto
    assert "- verbo acervo (a peça) — opera o acervo · dono dados · servido" in texto
    assert "- stack rag — recuperacao: extrator, indice e API do acervo" in texto
    assert "consome motor_acervo_rest — atos ler, listar" in texto
    assert "- verbo acervo lê acervo.casa — atos ler" in texto
    assert "volta por `promover`; quem volta: claudinho-TI; janela 1 min" in texto
    assert "- stack rag: /srv/platafirma/casa/segredos/rag/" in texto
    assert "- verbo acervo: variável RAG_API_TOKEN" in texto
    assert "### Documentos que declaram verbo acervo em Sobre:" in texto
    assert "- adr arq:0126 · Spec é a referência" in texto
    assert "### Ainda não montado (falta no golden record)" in texto
    assert "G3, arquiteto" in texto and "G2, ti" in texto


def test_render_diz_o_que_nao_resolve_e_o_que_falta_declarar():
    dados = dict(DADOS, fichas=[], verbos=[], capacidades=[], stacks=[], consumo=[], acesso=[],
                 segredos_env=[], documentos=[], conferida_em=None)
    texto = sm.render(dados, [("verbo", "sumido")])
    assert "- verbo sumido (a peça) — não resolve no golden record" in texto
    assert "não declarada no Estado" in texto
    assert "nenhum outro documento de casa declara verbo sumido" in texto
    assert "### Como sobe e como volta" not in texto


def test_compose_gravado_como_texto_de_array_sai_como_lista():
    s = dict(DADOS["stacks"][0], compose='["/a/docker-compose.yml", "/a/gpu.yml"]')
    texto = sm.render(dict(DADOS, stacks=[s]), sm.referentes_do_sobre(CORPO))
    assert "sobe de /a/docker-compose.yml, /a/gpu.yml;" in texto


def test_render_sem_banco_e_sem_sobre():
    assert "indisponível: o banco não respondeu" in sm.render(None, [("verbo", "x")])
    assert "sem `Sobre:` no cabeçalho" in sm.render({}, [])


def test_montagem_nao_derruba_a_leitura_quando_o_banco_cai(monkeypatch):
    def fora(sql, alvo="acervo.casa", falhar=True):
        assert falhar is False
        raise casa._FonteFora("psql falhou")
    monkeypatch.setattr(casa, "_q", fora)
    dados, texto = casa.montagem({"id": "00000000-0000-0000-0000-000000000001"}, CORPO)
    assert dados is None and "indisponível" in texto

    monkeypatch.setattr(casa, "_q", lambda sql, alvo="", falhar=True: DADOS)
    dados, texto = casa.montagem({"id": "00000000-0000-0000-0000-000000000001"}, CORPO)
    assert dados is DADOS and "Conferida contra produção: 2026-10-11" in texto
