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
