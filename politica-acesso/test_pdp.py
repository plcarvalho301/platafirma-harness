"""Prova do PDP. `python3 -m pytest politica-acesso/test_pdp.py -q`

Cada teste corresponde a uma linha do contrato publicado em
PlataFirma:Sec/contrato-de-politica-de-acesso. Regra que não tem teste aqui não está
verificada — e controle não verificado não conta.
"""

from pathlib import Path

import pytest

from pdp import Politica, PoliticaInvalida, Recurso, Sujeito, decide

POLITICA = Politica.de_arquivo(Path(__file__).parent / "politica.yaml")


def sujeito(**kw) -> Sujeito:
    base = dict(id="uuid-1", natureza="cadeira", papeis=("reino",),
                dominios=("plataforma",), temas=(), vetos=(), habilitacao="publico")
    base.update(kw)
    return Sujeito(**base)


def comando(alvo: str, **kw) -> Recurso:
    base = dict(tipo="comando", id=alvo, dominio="plataforma", tema="-", sigilo="publico")
    base.update(kw)
    return Recurso(**base)


# 1. Completude ---------------------------------------------------------------

def test_sem_papel_nega_e_nomeia_o_que_faltou():
    d = decide(sujeito(papeis=()), "run_command", comando("ls"), POLITICA)
    assert not d.permitido
    assert d.por_atributo_ausente
    assert "sujeito.papeis" in d.faltou


def test_recurso_sem_dominio_nega_por_ausencia_nao_por_regra():
    d = decide(sujeito(), "run_command", comando("ls", dominio=None), POLITICA)
    assert not d.permitido and d.faltou == ("recurso.dominio",)


def test_dominio_fora_do_vocabulario_nega():
    d = decide(sujeito(), "run_command", comando("ls", dominio="inventado"), POLITICA)
    assert not d.permitido and "vocabulario" in d.motivo


# 2. Teto de sigilo -----------------------------------------------------------

def test_teto_vence_intersecao_completa():
    d = decide(sujeito(habilitacao="publico"), "ler",
               Recurso(tipo="documento", id="ata", dominio="plataforma", sigilo="secreto"),
               POLITICA)
    assert not d.permitido and d.regra == "teto"


def test_habilitacao_suficiente_passa_do_teto():
    d = decide(sujeito(habilitacao="secreto"), "ler",
               Recurso(tipo="documento", id="ata", dominio="plataforma", sigilo="secreto"),
               POLITICA)
    assert d.permitido


# 3. Veto ---------------------------------------------------------------------

def test_veto_nega_mesmo_com_concessao_vigente():
    d = decide(sujeito(vetos=("plataforma-identidade",)), "run_command",
               comando("ls", dominio="plataforma-identidade"), POLITICA)
    assert not d.permitido and d.regra == "veto"


# 4. Interseção e herança -----------------------------------------------------

def test_concessao_no_pai_alcanca_o_filho():
    d = decide(sujeito(dominios=("plataforma",)), "run_command",
               comando("docker ps", dominio="plataforma-runtime"), POLITICA)
    assert d.permitido


def test_concessao_no_filho_nao_alcanca_o_pai():
    d = decide(sujeito(dominios=("plataforma-runtime",)), "run_command",
               comando("ls", dominio="plataforma"), POLITICA)
    assert not d.permitido and d.regra == "intersecao"


def test_recurso_com_tema_exige_designacao():
    d = decide(sujeito(temas=()), "ler",
               Recurso(tipo="documento", id="x", dominio="plataforma", tema="licitacoes"),
               POLITICA)
    assert not d.permitido and d.regra == "intersecao"


# 5. Matriz -------------------------------------------------------------------

def test_reino_faz_o_que_quiser_no_dominio_da_plataforma():
    d = decide(sujeito(papeis=("reino",)), "run_command",
               comando("docker restart keycloak"), POLITICA)
    assert d.permitido and d.regra == "reino-plataforma-tudo"


def test_fornecedor_le_repo():
    d = decide(sujeito(papeis=("fornecedor",)), "run_command", comando("git status"), POLITICA)
    assert d.permitido and d.regra == "fornecedor-le-repo"


def test_fornecedor_nao_mexe_no_estado_do_host():
    d = decide(sujeito(papeis=("fornecedor",)), "run_command",
               comando("docker restart keycloak"), POLITICA)
    assert not d.permitido and d.regra == "fornecedor-sem-estado-do-host"


def test_negativa_vence_permissao_ainda_que_venha_depois_no_arquivo():
    # `cat` está permitido em fornecedor-le-repo; `.env` está negado logo abaixo.
    d = decide(sujeito(papeis=("fornecedor",)), "run_command",
               comando("cat .env"), POLITICA)
    assert not d.permitido and d.regra == "fornecedor-sem-estado-do-host"


def test_default_e_negar():
    d = decide(sujeito(papeis=("fornecedor",)), "run_command",
               comando("curl https://exemplo.org"), POLITICA)
    assert not d.permitido and d.regra == "default"


# 6. Carregamento -------------------------------------------------------------

def test_politica_com_pai_inexistente_falha_no_carregamento():
    with pytest.raises(PoliticaInvalida):
        Politica({"versao": 1, "eixos": {"dominio": {"a": {"pai": "fantasma"}}}})


def test_politica_com_id_repetido_falha_no_carregamento():
    with pytest.raises(PoliticaInvalida):
        Politica({"versao": 1, "regras": [
            {"id": "x", "efeito": "permite"}, {"id": "x", "efeito": "nega"}]})


def test_versao_desconhecida_falha():
    with pytest.raises(PoliticaInvalida):
        Politica({"versao": 99})
