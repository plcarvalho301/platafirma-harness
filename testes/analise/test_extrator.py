"""Extração real com snapshot, corte ligado e prazo externo ao servidor."""
from datetime import datetime,timezone
import threading
import uuid
import psycopg
import pytest
from analise import Falha
from analise.extrator import extrair
from analise.receita import carregar
from analise.supervisor import prazo_extracao

def semear(admin,n=3):
    for i in range(n):
        id=str(uuid.UUID(int=i+1))
        ordem="turno-"+str(i//2)
        admin.execute("INSERT INTO acervo.log VALUES(%s,'2026-11-01T00:00:00Z','engenharia',%s,%s,'segredo-nao-ler')",
                      (id,str(uuid.UUID(int=100)),ordem))
        admin.execute("INSERT INTO acervo.log_giro VALUES(%s,'repo','ler',0,'leitura',1,%s)",(id,"codex" if i<2 else "cli"))

def test_extracao_corte_e_rollback(db,receita,tmp_path):
    cfg,admin=db;semear(admin)
    entrada=tmp_path/"entrada";entrada.mkdir()
    conn=psycopg.connect(**{**cfg,"user":"analise_extracao"})
    meta=extrair(conn,carregar(receita),receita,entrada,datetime(2026,11,2,tzinfo=timezone.utc))
    assert conn.closed
    assert meta["giros"]["linhas"]==3
    assert "segredo-nao-ler" not in (entrada/"giros.csv").read_text()
    assert meta["giros"]["snapshot"]
    c=psycopg.connect(**{**cfg,"user":"analise_extracao"})
    pasta=tmp_path/"vazia";pasta.mkdir()
    assert extrair(c,carregar(receita),receita,pasta,datetime(2026,10,1,tzinfo=timezone.utc))["giros"]["linhas"]==0

def test_coluna_sem_grant_no_banco(db):
    cfg,_=db
    with psycopg.connect(**{**cfg,"user":"analise_extracao"},autocommit=True) as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("SELECT segredo FROM acervo.log")

def test_read_write_nao_muda_origem(db):
    cfg,_=db
    with psycopg.connect(**{**cfg,"user":"analise_extracao"}) as c:
        c.execute("BEGIN READ WRITE")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("INSERT INTO acervo.log(ordem_id) VALUES('fuga')")

def test_prazo_fecha_transacao(db):
    cfg,admin=db
    c=psycopg.connect(**{**cfg,"user":"analise_extracao"})
    pid=c.info.backend_pid
    with pytest.raises(Falha) as e:
        with prazo_extracao(c,0.1):
            c.execute("BEGIN READ ONLY")
            c.execute("SELECT pg_sleep(5)")
    assert e.value.exit==5 and c.closed
    assert not admin.execute("SELECT 1 FROM pg_stat_activity WHERE pid=%s",(pid,)).fetchone()


def test_snapshot_nao_mistura_alteracao_concorrente(db,receita,tmp_path):
    import copy
    cfg,admin=db;semear(admin)
    r=carregar(receita)
    r["consultas"]=[{"nome":"primeira","arquivo":"giros.sql"},{"nome":"segunda","arquivo":"giros.sql"}]
    class Conn(psycopg.Connection):
        def cursor(self,*args,**kwargs):
            if kwargs.get("name")=="analise_1":
                id=str(uuid.UUID(int=999))
                admin.execute("INSERT INTO acervo.log VALUES(%s,'2026-11-01T00:00:00Z','engenharia',%s,'tardio','segredo')",(id,str(uuid.UUID(int=100))))
                admin.execute("INSERT INTO acervo.log_giro VALUES(%s,'repo','ler',0,'leitura',1,'codex')",(id,))
            return super().cursor(*args,**kwargs)
    conn=Conn.connect(**{**cfg,"user":"analise_extracao"})
    entrada=tmp_path/"entrada";entrada.mkdir()
    m=extrair(conn,r,receita,entrada,datetime(2026,11,2,tzinfo=timezone.utc))
    assert m["primeira"]["linhas"]==m["segunda"]["linhas"]==3
    assert admin.execute("SELECT count(*) FROM acervo.log").fetchone()[0]==4
