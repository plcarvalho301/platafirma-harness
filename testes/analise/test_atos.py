"""Ajuda, recusas e leitura de arquivo conservam a fronteira do verbo."""
import json
from pathlib import Path
import pytest
from analise.atos import main
from analise.acesso_arquivo import negar
from analise.publicacao import Catalogo
from analise import Falha
from test_publicacao import publicar_minima

@pytest.mark.parametrize("args",[["--ajuda"],["preparar","inexistente"],["montar","contagem-por-fonte"]])
def test_jornada_termina_no_guia(args,capsys,monkeypatch,tmp_path):
    from analise.atos import MotorAnalise
    motor=MotorAnalise(raiz=tmp_path,conhecimento=tmp_path,registro={},instancia=tmp_path,sujeito="s",sessao="s",ordem="o")
    monkeypatch.setattr("analise.atos.runtime",lambda:motor)
    rc=main(args)
    assert rc==(0 if args==["--ajuda"] else 2)
    assert capsys.readouterr().out.rstrip().splitlines()[-1]=="analise --guia preparacao"

def test_guia_lido_na_chamada(monkeypatch,capsys):
    monkeypatch.setattr("analise.guia.ler",lambda:"guia em vigor\n")
    assert main(["--guia","preparacao"])==0
    assert capsys.readouterr().out=="guia em vigor\n"

def test_guia_sem_acesso_sai_3(monkeypatch,capsys):
    from analise.guia import CAMINHO
    def indisponivel():raise Falha(3,"guia-indisponivel",CAMINHO)
    monkeypatch.setattr("analise.guia.ler",indisponivel)
    assert main(["--guia","preparacao"])==3
    assert CAMINHO in capsys.readouterr().out

def test_arquivo_de_outro_sujeito_recusa(catalogo,tmp_path,receita,db):
    import psycopg
    cfg,_=db
    out=tmp_path/"out";out.mkdir()
    id,r,m,ex=publicar_minima(catalogo,out,receita)
    instancia=tmp_path/"instancia"
    p=instancia/"var/tmp/o/analise"/ex/"entrada/x.csv"
    p.parent.mkdir(parents=True);p.write_text("privado")
    conexao=lambda parte:psycopg.connect(**{**cfg,"user":"analise_publicacao"})
    assert not negar(p,"sujeito-teste",instancia,conexao)
    assert negar(p,"outro",instancia,conexao)
    assert negar(p,"",instancia,conexao)

def test_porta_aplica_posse_em_arquivo_e_diretorio():
    from conftest import RAIZ
    src=(RAIZ/"ops-server/server.py").read_text()
    assert "or _nega_analise(alvo)" in src
    assert "if _nega_analise(alvo):" in src

def test_listar_bases_e_resultados_com_receita_corte_guarda_e_estado(catalogo,tmp_path,receita,db,monkeypatch,capsys):
    import psycopg
    from analise.atos import MotorAnalise
    from analise.publicacao import novo
    cfg,_=db
    out1=tmp_path/"out1";out1.mkdir()
    r1= json.loads(json.dumps({"tipo":"preparacao","pergunta":"Pergunta da base A","guarda":{"ate_descarte":"homologacao"},
        "saidas":{"tabelas":[{"nome":"x","colunas":[{"nome":"id","tipo":"inteiro"}],"ordem":["id"]}]},
        "serializacao":{"nulo":"","nan":"NaN","datas":"utc","decimais":3}}))
    (out1/"x.csv").write_text("id\n10\n2\n")
    ex1=novo("ex");catalogo.abrir_execucao(ex1,"preparar","s","o")
    b1=catalogo.publicar(ex1,r1,"populacao-de-turnos",out1,{"serializacao":r1["serializacao"],"corte":"2026-11-02T00:00:00Z","saidas":{}})

    out2=tmp_path/"out2";out2.mkdir()
    (out2/"x.csv").write_text("id\n1\n")
    ex2=novo("ex");catalogo.abrir_execucao(ex2,"preparar","s","o")
    b2=catalogo.publicar(ex2,r1,"mineracao-ocel",out2,{"serializacao":r1["serializacao"],"corte":"2026-11-10T00:00:00Z","saidas":{}})

    out_res=tmp_path/"res";out_res.mkdir()
    (out_res/"y.csv").write_text("n\n7\n")
    r_res={"tipo":"analise","pergunta":"Pergunta do resultado","guarda":{"dias":7},
           "saidas":{"tabelas":[{"nome":"y","colunas":[{"nome":"n","tipo":"inteiro"}],"ordem":["n"]}]},
           "serializacao":r1["serializacao"]}
    ex_res=novo("ex");catalogo.abrir_execucao(ex_res,"montar","s","o")
    res_id=catalogo.publicar(ex_res,r_res,"contagem-por-fonte",out_res,{"serializacao":r1["serializacao"],"saidas":{}},catalogo.objeto(b2))

    conexao=lambda parte:psycopg.connect(**{**cfg,"user":"analise_publicacao"})
    motor=MotorAnalise(raiz=tmp_path,conhecimento=tmp_path,registro={},instancia=tmp_path,
        sujeito="sujeito-teste",sessao="s",ordem="o",conexao=conexao,autorizar=lambda *a:{"versao":"teste"})
    monkeypatch.setattr("analise.atos.runtime",lambda:motor)

    assert main(["listar","bases","--receita","mineracao-ocel"])==0
    bloco=json.loads(capsys.readouterr().out)
    assert [it["id"] for it in bloco["itens"]]==[b2]
    item=bloco["itens"][0]
    assert item["receita"]=="mineracao-ocel"
    assert item["pergunta"]=="Pergunta da base A"
    assert item["corte"]=="2026-11-10T00:00:00Z"
    assert item["guarda"]=={"ate_descarte":"homologacao"}
    assert item["estado"]=="pronta"

    assert main(["listar","resultados","--receita","contagem-por-fonte"])==0
    bloco_r=json.loads(capsys.readouterr().out)
    assert [it["id"] for it in bloco_r["itens"]]==[res_id]
    it_r=bloco_r["itens"][0]
    assert it_r["receita"]=="contagem-por-fonte"
    assert it_r["base_id"]==b2
    assert it_r["pergunta"]=="Pergunta do resultado"
    assert it_r["corte"]=="2026-11-10T00:00:00Z"
    assert it_r["guarda"]=={"dias":7}
    assert it_r["estado"]=="pronta"
