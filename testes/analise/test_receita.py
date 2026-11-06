"""Admissão antes do banco, tipos e estimativa quadrática."""
import copy
import pytest
import yaml
from analise import Falha
from analise.receita import carregar,validar_sql,pre_voo,parametros

@pytest.mark.parametrize("campo",["tipo","pergunta","populacao","metodo","saidas","serializacao","codigo","pilha","corte","consultas","tabelas_de_origem","chave_do_turno"])
def test_campo_ausente_sai_2(receita,campo):
    r=yaml.safe_load((receita/"receita.yaml").read_text());r.pop(campo)
    (receita/"receita.yaml").write_text(yaml.safe_dump(r))
    with pytest.raises(Falha) as e: carregar(receita,"preparar")
    assert e.value.exit==2

@pytest.mark.parametrize("sql,exit",[
 ("select l.ts from acervo.log l",2),
 ("select l.segredo from acervo.log l where l.ts < :corte",4),
 ("select l.ts from acervo.log l where l.ts < :corte or true",4),
 ("select pg_read_file('/etc/passwd') from acervo.log l where l.ts < :corte",4),
 ("select l.ts from acervo.log l where l.ts < :corte; set transaction read write",4),
 ("select l.ts from acervo.log l where l.ts < :corte union select l.ts from acervo.log l",4),
])
def test_sql_contido(receita,sql,exit):
    r=carregar(receita)
    with pytest.raises(Falha) as e: validar_sql(sql,r)
    assert e.value.exit==exit

def test_coluna_corte_fora_da_declaracao(receita):
    r=yaml.safe_load((receita/"receita.yaml").read_text())
    r["corte"]["acervo.log"]["coluna"]="segredo"
    (receita/"receita.yaml").write_text(yaml.safe_dump(r))
    with pytest.raises(Falha) as e: carregar(receita)
    assert e.value.exit==2

def test_receita_usa_artefato_da_versao_registrada(receita,tmp_path):
    import shutil
    from analise.atos import MotorAnalise
    antiga=tmp_path/"artefatos"/("a"*40)
    nova=tmp_path/"artefatos"/("b"*40)
    shutil.copytree(receita,antiga/"analise/populacao-de-turnos")
    nova.mkdir()
    reg={"populacao-de-turnos":{"tipo":"preparacao","repositorio":"platafirma-conhecimento",
         "caminho":"analise/populacao-de-turnos","versao":"a"*40}}
    m=MotorAnalise(raiz=tmp_path,conhecimento=nova,registro=reg,instancia=tmp_path,
                  sujeito="s",sessao="s",ordem="o")
    p,r,origem=m.receita("populacao-de-turnos","preparar")
    assert p==antiga/"analise/populacao-de-turnos"


def test_pre_voo_nao_aloca():
    with pytest.raises(Falha) as e:
        pre_voo({"metodo":"agrupamento-hierarquico","populacao":{"n":232916}})
    assert e.value.exit==5
    assert pre_voo({"metodo":"linear","populacao":{"n":232916}})==0

@pytest.mark.parametrize("p",["outro=1","desde=sem-data","desde=2026-01-01"])
def test_parametro_invalido(receita,p):
    with pytest.raises(Falha) as e: parametros(carregar(receita),[p])
    assert e.value.exit==2
