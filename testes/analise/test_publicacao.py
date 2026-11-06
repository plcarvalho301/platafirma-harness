"""Atomicidade, ordem tipada e integridade da base publicada."""
from datetime import timedelta
from pathlib import Path
import pytest
from analise import Falha,agora
from analise.receita import carregar
from analise.publicacao import novo
from analise.materializacao import materializar
from analise.serializacao import canonizar

def publicar_minima(cat,pasta,receita):
    r=carregar(receita)
    r["saidas"]={"tabelas":[{"nome":"x","colunas":[{"nome":"id","tipo":"inteiro"}],"ordem":["id"]}]}
    (pasta/"x.csv").write_text("id\n10\n2\n")
    ex=novo("ex");cat.abrir_execucao(ex,"preparar","s","o")
    m={"serializacao":r["serializacao"],"saidas":{}}
    id=cat.publicar(ex,r,"populacao-de-turnos",pasta,m)
    return id,r,m,ex

def test_publicacao_atomica(catalogo,tmp_path,receita):
    r=carregar(receita)
    r["saidas"]={"tabelas":[{"nome":"x","colunas":[{"nome":"id","tipo":"inteiro"}],"ordem":["id"]}]}
    out=tmp_path/"out";out.mkdir()
    (out/"x.csv").write_text("id\n1\n")
    ex=novo("ex");catalogo.abrir_execucao(ex,"preparar","s","o")
    def quebrar(): raise RuntimeError("interrupcao")
    with pytest.raises(RuntimeError):
        catalogo.publicar(ex,r,"p",out,{"serializacao":r["serializacao"]},antes_de_pronto=quebrar)
    assert catalogo.conn.execute("SELECT count(*) FROM analise.base").fetchone()[0]==0
    assert catalogo.conn.execute("SELECT count(*) FROM analise.tabela").fetchone()[0]==0
    assert catalogo.conn.execute("SELECT estado FROM analise.execucao WHERE id=%s",(ex,)).fetchone()[0]=="ativa"

def test_base_adulterada(catalogo,tmp_path,receita):
    out=tmp_path/"out";out.mkdir()
    id,r,m,ex=publicar_minima(catalogo,out,receita)
    base=catalogo.objeto(id)
    receita_analise={"base":{"receitas":["populacao-de-turnos"],"tabelas":["x"]}}
    a=tmp_path/"a";a.mkdir();b=tmp_path/"b";b.mkdir()
    assert materializar(catalogo,base,receita_analise,a)==materializar(catalogo,base,receita_analise,b)
    from psycopg import sql
    fisica=catalogo.conn.execute("SELECT fisica FROM analise.tabela WHERE objeto_id=%s",(id,)).fetchone()[0]
    catalogo.conn.execute(sql.SQL("UPDATE analise.{} SET id=999 WHERE id=2").format(sql.Identifier(fisica)))
    c=tmp_path/"c";c.mkdir()
    with pytest.raises(Falha) as e:materializar(catalogo,base,receita_analise,c)
    assert e.value.exit==5

def test_ordem_com_empate_recusa(tmp_path):
    p=tmp_path/"x.csv";p.write_text("id\n2\n2\n")
    with pytest.raises(Falha) as e:
        canonizar(p,{"colunas":[{"nome":"id","tipo":"inteiro"}],"ordem":["id"]},
            {"nulo":"","nan":"NaN","datas":"utc","decimais":3})
    assert e.value.exit==4
