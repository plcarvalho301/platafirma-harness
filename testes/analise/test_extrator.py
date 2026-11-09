"""Extração real por banco (#4185): snapshot, corte ligado, leitura total e nenhuma escrita."""
from datetime import datetime,timezone
import uuid
import psycopg
import pytest
import yaml
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

def test_extracao_corte_e_rollback(db,bancos,receita,tmp_path):
    cfg,admin=db;semear(admin)
    entrada=tmp_path/"entrada";entrada.mkdir()
    meta=extrair(None,carregar(receita),receita,entrada,datetime(2026,11,2,tzinfo=timezone.utc))
    assert meta["giros"]["linhas"]==3
    assert meta["giros"]["banco"]=="rag" and meta["giros"]["role"]=="analise_leitura@rag"
    assert "segredo-nao-ler" not in (entrada/"giros.csv").read_text()
    assert meta["giros"]["snapshot"]
    pasta=tmp_path/"vazia";pasta.mkdir()
    assert extrair(None,carregar(receita),receita,pasta,datetime(2026,10,1,tzinfo=timezone.utc))["giros"]["linhas"]==0
    assert not admin.execute("SELECT 1 FROM pg_stat_activity WHERE usename='analise_leitura' AND state like 'idle in%'").fetchone()

def test_cruza_dois_bancos_na_mesma_receita(db,bancos,receita,tmp_path):
    """Uma tabela do log (rag) e uma do rastreador, cada consulta no seu banco."""
    cfg,admin=db;semear(admin)
    admin.execute("CREATE TABLE IF NOT EXISTS public.card(id integer PRIMARY KEY,titulo text,estado text)")
    admin.execute("TRUNCATE public.card")
    admin.execute("INSERT INTO public.card VALUES(4185,'analise lê todo banco','em-mitigacao'),(4184,'cadernos','priorizada')")
    r=yaml.safe_load((receita/"receita.yaml").read_text())
    r["tabelas_de_origem"].append({"banco":"rastreador","tabela":"public.card","colunas":["id","titulo","estado"]})
    r["corte"]["rastreador/public.card"]={"por":"snapshot"}
    r["consultas"].append({"nome":"cards","arquivo":"cards.sql"})
    (receita/"cards.sql").write_text("select c.id, c.titulo, c.estado from public.card c order by c.id\n")
    (receita/"receita.yaml").write_text(yaml.safe_dump(r,allow_unicode=True))
    entrada=tmp_path/"entrada";entrada.mkdir()
    meta=extrair(None,carregar(receita),receita,entrada,datetime(2026,11,2,tzinfo=timezone.utc))
    assert meta["giros"]["banco"]=="rag" and meta["cards"]["banco"]=="rastreador"
    assert meta["cards"]["linhas"]==2
    assert "analise lê todo banco" in (entrada/"cards.csv").read_text()

def test_consulta_que_cruza_bancos_no_sql_recusa(db,bancos,receita):
    r=yaml.safe_load((receita/"receita.yaml").read_text())
    r["tabelas_de_origem"].append({"banco":"rastreador","tabela":"public.card","colunas":["id"]})
    r["corte"]["rastreador/public.card"]={"por":"snapshot"}
    r["consultas"].append({"nome":"mistura","arquivo":"mistura.sql"})
    (receita/"mistura.sql").write_text("select c.id from public.card c join acervo.log l on l.ordem_id = c.id where l.ts < :corte\n")
    (receita/"receita.yaml").write_text(yaml.safe_dump(r,allow_unicode=True))
    with pytest.raises(Falha) as e:
        carregar(receita)
    assert e.value.causa=="consulta-cruza-bancos"

def test_banco_fora_do_registro_recusa(bancos,receita):
    r=yaml.safe_load((receita/"receita.yaml").read_text())
    r["tabelas_de_origem"][0]["banco"]="inventado"
    (receita/"receita.yaml").write_text(yaml.safe_dump(r,allow_unicode=True))
    with pytest.raises(Falha) as e:
        carregar(receita)
    assert e.value.causa=="banco-fora-do-registro:inventado"

def test_leitura_alcanca_toda_coluna(db):
    """A role lê tudo: a coluna que a 159 não concedia volta."""
    cfg,admin=db;semear(admin,1)
    from conftest import CONTEINER_PG
    import subprocess
    p=subprocess.run(["docker","exec","-i",CONTEINER_PG,"psql","-X","-A","-t","-U","analise_leitura","-d","postgres"],
                     input="SELECT segredo FROM acervo.log;",capture_output=True,text=True,timeout=30)
    assert p.returncode==0 and p.stdout.strip()=="segredo-nao-ler"

def test_leitura_nao_escreve(db):
    from conftest import CONTEINER_PG
    import subprocess
    for sql in ("INSERT INTO acervo.log(ordem_id) VALUES('fuga');",
                "BEGIN READ WRITE; INSERT INTO acervo.log(ordem_id) VALUES('fuga'); COMMIT;",
                "CREATE TABLE public.fuga(x int);"):
        p=subprocess.run(["docker","exec","-i",CONTEINER_PG,"psql","-X","-v","ON_ERROR_STOP=1","-U","analise_leitura","-d","postgres"],
                         input=sql,capture_output=True,text=True,timeout=30)
        assert p.returncode!=0
    _,admin=db
    assert admin.execute("SELECT count(*) FROM acervo.log WHERE ordem_id='fuga'").fetchone()[0]==0

def test_role_ausente_diz_o_conserto(db,bancos,receita,tmp_path,monkeypatch):
    import json
    from conftest import CONTEINER_PG
    arq=tmp_path/"sem-role.json"
    arq.write_text(json.dumps({"rag":{"conteiner":CONTEINER_PG,"base":"banco_que_nao_existe","dono":"postgres"}}))
    monkeypatch.setenv("PF_ANALISE_BANCOS",str(arq))
    entrada=tmp_path/"entrada";entrada.mkdir()
    with pytest.raises(Falha) as e:
        extrair(None,carregar(receita),receita,entrada,datetime(2026,11,2,tzinfo=timezone.utc))
    assert e.value.exit in (3,5) and e.value.causa.endswith(":rag")

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

def test_duas_consultas_mesmo_snapshot(db,bancos,receita,tmp_path):
    cfg,admin=db;semear(admin)
    r=carregar(receita)
    r["consultas"]=[{"nome":"primeira","arquivo":"giros.sql"},{"nome":"segunda","arquivo":"giros.sql"}]
    entrada=tmp_path/"entrada";entrada.mkdir()
    m=extrair(None,r,receita,entrada,datetime(2026,11,2,tzinfo=timezone.utc))
    assert m["primeira"]["linhas"]==m["segunda"]["linhas"]==3
    assert m["primeira"]["snapshot"]==m["segunda"]["snapshot"]
