"""Preparar, montar e refazer reais sobre população de resultado conhecido."""
from datetime import datetime,timezone
from pathlib import Path
import json
import psycopg
import pytest
from conftest import CONHECIMENTO,RAIZ
from test_extrator import semear
from analise.atos import MotorAnalise
from analise.ambiente import construir,travar

@pytest.fixture
def motor(db,tmp_path):
    cfg,admin=db
    semear(admin)
    reg={
        "populacao-de-turnos":{"tipo":"preparacao","repositorio":"platafirma-conhecimento","caminho":"analise/populacao-de-turnos","versao":"teste"},
        "contagem-por-fonte":{"tipo":"analise","repositorio":"platafirma-conhecimento","caminho":"analise/contagem-por-fonte","versao":"teste"},
    }
    # O travar deste ensaio opera sobre uma cópia descartável da receita.
    import shutil
    conhecimento=tmp_path/"conhecimento"
    shutil.copytree(CONHECIMENTO/"analise",conhecimento/"analise")
    for slug in reg:
        travar(conhecimento/"analise"/slug,tmp_path/"cache")
    def conexao(parte):
        return psycopg.connect(**{**cfg,"user":"analise_extracao" if parte=="origem" else "analise_publicacao"})
    return MotorAnalise(raiz=RAIZ,conhecimento=conhecimento,registro=reg,
        instancia=tmp_path/"instancia",sujeito="sujeito-teste",sessao="s",ordem="o",
        conexao=conexao,autorizar=lambda *args:{"versao":"teste"})

def test_preparar_montar_e_refazer(motor,db):
    rc,base=motor.rodar("preparar","populacao-de-turnos",corte="2026-11-02T00:00:00Z")
    assert rc==0,base
    assert base["manifesto"]["entradas"]["giros"]["linhas"]==3
    assert base["manifesto"]["saidas"]["turnos"]["linhas"]==2
    assert base["expires_at"] is None
    rc,resultado=motor.rodar("montar","contagem-por-fonte",base_id=base["base_id"])
    assert rc==0,resultado
    cat=motor.catalogo()
    from analise.leitura import ler
    dados=ler(cat,resultado["resultado_id"],"contagem","1-10",None,motor.tmp/"o")
    assert dados["linhas"]==[("cli",1),("codex",1)]
    from analise import Falha
    with pytest.raises(Falha) as erro:cat.descartar(base["base_id"])
    assert erro.value.exit==2
    cat.conn.close()
    for ex in (base["execucao_id"],resultado["execucao_id"]):
        rc,repetido=motor.rodar("refazer",origem=ex)
        assert rc==0,repetido
    # A chegada tardia é diferença na entrada, sob o mesmo corte.
    _,admin=db
    import uuid
    id=str(uuid.UUID(int=99))
    admin.execute("INSERT INTO acervo.log VALUES(%s,'2026-11-01T01:00:00Z','engenharia',%s,'turno-tardio','segredo')",(id,str(uuid.UUID(int=100))))
    admin.execute("INSERT INTO acervo.log_giro VALUES(%s,'repo','ler',0,'leitura',1,'codex')",(id,))
    rc,divergente=motor.rodar("refazer",origem=base["execucao_id"],reler=True)
    assert rc==1 and divergente["causa"]=="entrada",divergente

def test_receita_desconhecida_sem_abrir_banco(tmp_path):
    def nao_conectar(_): raise AssertionError("abriu banco antes da admissão")
    m=MotorAnalise(raiz=RAIZ,conhecimento=tmp_path,registro={},instancia=tmp_path,
        sujeito="s",sessao="s",ordem="o",conexao=nao_conectar)
    rc,r=m.rodar("preparar","inexistente")
    assert rc==2 and r["causa"]=="receita-fora-do-registro"
