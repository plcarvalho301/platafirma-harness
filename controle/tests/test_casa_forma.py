# `acervo ler casa forma` (card #4046): a forma do texto da classe, lida de acervo.entidade_classe.forma, que o
# gerador de platafirma-conhecimento resolve a partir da shape. Sem banco: a consulta é injetada. Cobre os três
# códigos (0, 3, 2), as quatro marcas e os dois seletores (classe e --suporte).
import importlib.machinery
import importlib.util
import json
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACERVO = os.path.join(REPO, "bin", "_acervo")


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


fm = _carrega("acervo_forma", "forma")

SHA = "4168e2f0df38"
PARECER = {"marca": "genero", "genero": {"valor": "observacao", "rotulo": "observação"},
           "raiz": {"regua": "voz da casa, styleguide §3.1"},
           "secoes": [{"ordem": 1, "slug": "materia-e-pergunta", "rotulo": "Matéria e pergunta", "escrita": "prosa",
                       "obrigatoria": False, "regua": "A matéria…", "origem": "classe"},
                      {"ordem": 2, "slug": "fontes", "rotulo": "Fontes", "escrita": "prosa", "obrigatoria": True,
                       "regua": "As obras…", "origem": "andar"}],
           "reguas_de_campo": [], "canonica": None, "coberta_por": [], "motivo": None}
CATALOGO = {
    "parecer": PARECER,
    "registro-de-decisao": {**PARECER, "marca": "canonica", "genero": None, "secoes": [],
                            "canonica": "arq:0075 (template de ordem fixa)"},
    "componente": {**PARECER, "marca": "coberta-por", "genero": None, "secoes": [],
                   "coberta_por": [{"classe": "servico", "secao": "componentes", "condicao": None}]},
    "obra": {**PARECER, "marca": "sem-forma", "genero": None, "secoes": [], "motivo": "texto de fora"},
}
SUPORTES = {"platafirma-casa@parecer/2026-09-21-organizacao-repos.md": "parecer"}
CASA = {("platafirma-casa", "parecer/2026-10-24-sem-suporte.md"): "parecer"}


def lit(s):
    return "'" + str(s).replace("'", "''") + "'"


def consulta(sql, alvo=None):
    if "from acervo.entidade_classe c" in sql and "c.slug =" in sql:
        slug = sql.split("c.slug = '", 1)[1].split("'", 1)[0]
        if slug not in CATALOGO:
            return None
        return {"classe": slug, "forma": CATALOGO[slug],
                "shape_endereco": f"ontologia/shapes/entidade/{slug}.ttl", "shape_versao": SHA}
    if "json_agg(slug" in sql:
        return sorted(CATALOGO)
    if "acervo.entidade_suporte" in sql:
        end = sql.split("s.endereco = '", 1)[1].split("'", 1)[0]
        return SUPORTES.get(end)
    if "from acervo.casa c" in sql:
        repo = sql.split("c.repo = '", 1)[1].split("'", 1)[0]
        caminho = sql.split("c.path = '", 1)[1].split("'", 1)[0]
        return CASA.get((repo, caminho))
    raise AssertionError(sql)


def test_genero_sai_0_com_as_secoes_a_origem_e_o_sha():
    codigo, carga = fm.resolver(consulta, lit, classe="parecer")
    assert codigo == 0 and carga["marca"] == "genero" and carga["genero"]["valor"] == "observacao"
    fontes = carga["secoes"][-1]
    assert (fontes["slug"], fontes["origem"], fontes["obrigatoria"]) == ("fontes", "andar", True)
    assert carga["shape"]["sha"] == SHA == carga["shape"]["versao"]


@pytest.mark.parametrize("classe, marca, campo, valor", [
    ("registro-de-decisao", "canonica", "canonica", "arq:0075 (template de ordem fixa)"),
    ("componente", "coberta-por", "coberta_por", [{"classe": "servico", "secao": "componentes", "condicao": None}]),
    ("obra", "sem-forma", "motivo", "texto de fora"),
])
def test_as_tres_marcas_sem_secao_saem_3(classe, marca, campo, valor):
    codigo, carga = fm.resolver(consulta, lit, classe=classe)
    assert codigo == 3 and carga["marca"] == marca and carga[campo] == valor and carga["secoes"] == []


def test_classe_desconhecida_sai_2_com_o_vizinho():
    codigo, carga = fm.resolver(consulta, lit, classe="parecr")
    assert codigo == 2 and "parecr" in carga["erro"] and "acervo ler casa forma parecer" in carga["vizinho"]


def test_sem_seletor_sai_2():
    assert fm.resolver(consulta, lit)[0] == 2


def test_suporte_pela_ficha_e_pela_linha_de_casa():
    a = fm.resolver(consulta, lit, suporte="platafirma-casa@parecer/2026-09-21-organizacao-repos.md")
    b = fm.resolver(consulta, lit, suporte="platafirma-casa@parecer/2026-10-24-sem-suporte.md")
    direto = fm.resolver(consulta, lit, classe="parecer")
    assert a[0] == b[0] == 0
    assert a[1]["secoes"] == b[1]["secoes"] == direto[1]["secoes"]


def test_suporte_sem_ficha_nem_casa_sai_2():
    codigo, carga = fm.resolver(consulta, lit, suporte="platafirma-casa@spec/nada.md")
    assert codigo == 2 and "sem ficha" in carga["erro"]


def test_texto_uma_secao_por_bloco_e_o_ponteiro():
    t = fm.texto(fm.resolver(consulta, lit, classe="parecer")[1])
    assert "gênero: observação (observacao)" in t and "2. Fontes (fontes) · prosa · obrigatória · de andar" in t
    assert "canônica: arq:0075" in fm.texto(fm.resolver(consulta, lit, classe="registro-de-decisao")[1])
    assert "coberta por: servico § componentes" in fm.texto(fm.resolver(consulta, lit, classe="componente")[1])


def test_main_recusa_classe_e_suporte_juntos(capsys):
    assert fm.main(["parecer", "--suporte", "x@y.md"]) == 2
    assert "não os dois" in capsys.readouterr().err


def test_o_json_da_saida_e_serializavel():
    json.dumps(fm.resolver(consulta, lit, classe="parecer")[1], ensure_ascii=False)
