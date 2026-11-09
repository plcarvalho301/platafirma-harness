"""PostgreSQL 16 descartável, sem volume ou credencial de produção."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import pytest

RAIZ=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(RAIZ/"lib"))
CONHECIMENTO=None
_FONTE_TEMP=None
CONTEINER_PG=None

def pytest_configure(config):
    """O ensaio usa artefatos fixados no teste, sem ler release ou bancada viva."""
    global CONHECIMENTO,_FONTE_TEMP
    import json
    import tempfile
    _FONTE_TEMP=tempfile.TemporaryDirectory(prefix="analise-4130-fixtura-")
    CONHECIMENTO=Path(_FONTE_TEMP.name)
    fontes=json.loads((Path(__file__).parent/"fixtura.json").read_text())
    for nome,conteudo in fontes.items():
        p=CONHECIMENTO/nome;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(conteudo)

def pytest_unconfigure(config):
    if _FONTE_TEMP is not None:
        _FONTE_TEMP.cleanup()

@pytest.fixture(scope="session")
def pg():
    import psycopg
    nome="analise-teste-"+uuid.uuid4().hex[:12]
    senha=uuid.uuid4().hex
    comando=["docker","run","-d","--rm","--name",nome,"--memory=512m","--cpus=1",
             "-p","127.0.0.1::5432","-e","POSTGRES_PASSWORD="+senha,
             "pgvector/pgvector:pg16"]
    p=subprocess.run(comando,capture_output=True,text=True,timeout=60)
    assert p.returncode==0,"PostgreSQL 16 de teste indisponível"
    try:
        porta=subprocess.check_output(["docker","port",nome,"5432/tcp"],text=True).strip().rsplit(":",1)[1]
        cfg=dict(host="127.0.0.1",port=int(porta),dbname="postgres",user="postgres",password=senha)
        admin=None
        for _ in range(100):
            try:
                admin=psycopg.connect(**cfg,autocommit=True);break
            except psycopg.OperationalError:
                time.sleep(0.1)
        assert admin is not None,"PostgreSQL 16 não ficou pronto"
        admin.execute("CREATE SCHEMA acervo")
        admin.execute("CREATE TABLE acervo.log(evento_id uuid PRIMARY KEY,ts timestamptz,cadeira text,sessao_id uuid,ordem_id text,segredo text)")
        admin.execute("CREATE TABLE acervo.log_giro(evento_id uuid,tool text,ato text,exit_code integer,classe text,dur_ms integer,turno_fonte text)")
        mig=CONHECIMENTO/"rag/db/init/159_schema_analise.sql"
        with admin.transaction():
            admin.execute(mig.read_text())
        # #4185: a role de leitura do analise, a mesma de todo banco da casa.
        with admin.transaction():
            admin.execute((RAIZ/"lib/analise/sql/leitura.sql").read_text())
        global CONTEINER_PG
        CONTEINER_PG=nome
        from psycopg import sql
        for role in ("analise_extracao","analise_publicacao"):
            admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role),sql.Literal(senha)))
        yield cfg,admin
        admin.close()
    finally:
        subprocess.run(["docker","rm","-f",nome],capture_output=True,timeout=30)

@pytest.fixture
def db(pg):
    from psycopg import sql
    cfg,admin=pg
    for (t,) in admin.execute("SELECT fisica FROM analise.tabela"):
        admin.execute(sql.SQL("DROP TABLE IF EXISTS analise.{}").format(sql.Identifier(t)))
    admin.execute("TRUNCATE analise.projecao,analise.tabela,analise.resultado,analise.base,analise.execucao,acervo.log_giro,acervo.log CASCADE")
    return cfg,admin

@pytest.fixture
def bancos(pg,tmp_path,monkeypatch):
    """Registro de bancos do ensaio: o rag e o rastreador são o mesmo contêiner descartável."""
    import json
    reg={s:{"conteiner":CONTEINER_PG,"base":"postgres","dono":"postgres"} for s in ("rag","rastreador")}
    arq=tmp_path/"bancos.json";arq.write_text(json.dumps(reg))
    monkeypatch.setenv("PF_ANALISE_BANCOS",str(arq))
    return reg

@pytest.fixture
def receita(tmp_path):
    pasta=tmp_path/"receita"
    shutil.copytree(CONHECIMENTO/"analise/populacao-de-turnos",pasta)
    return pasta

@pytest.fixture
def catalogo(db):
    import psycopg
    from analise.publicacao import Catalogo
    cfg,_=db
    with psycopg.connect(**{**cfg,"user":"analise_publicacao"}) as conn:
        yield Catalogo(conn,"sujeito-teste")
