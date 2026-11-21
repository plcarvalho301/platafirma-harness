# componente: componente:analise
"""Guarda da base, do resultado e dos temporários são independentes."""
from datetime import timedelta
import pytest
from analise import Falha,agora
from analise.publicacao import novo,vencimento,Catalogo
from analise.coleta import coletar
from test_publicacao import publicar_minima

def test_ate_descarte_sobrevive(catalogo,tmp_path,receita):
    out=tmp_path/"out";out.mkdir()
    id,r,m,ex=publicar_minima(catalogo,out,receita)
    assert catalogo.objeto(id)["expires_at"] is None
    assert coletar(catalogo,tmp_path)==0

def test_resultado_nao_supera_base():
    limite=agora()+timedelta(days=1)
    assert vencimento({"dias":100},limite)==limite
    assert vencimento({"ate_descarte":"homologacao"},limite)==limite

def test_vencido_impede_leitura(catalogo,tmp_path,receita):
    out=tmp_path/"out";out.mkdir()
    id,r,m,ex=publicar_minima(catalogo,out,receita)
    catalogo.conn.execute("UPDATE analise.base SET expires_at=clock_timestamp()-interval '1 second' WHERE id=%s",(id,))
    with pytest.raises(Falha) as e:catalogo.objeto(id)
    assert e.value.exit==5
    with pytest.raises(Falha) as e:catalogo.execucao(ex)
    assert e.value.exit==5
    assert coletar(catalogo,tmp_path)==1

def test_outro_sujeito_le_pelo_padrao_e_nao_lista(catalogo,tmp_path,receita):
    out=tmp_path/"out";out.mkdir()
    id,r,m,ex=publicar_minima(catalogo,out,receita)
    outro=Catalogo(catalogo.conn,"outro")
    assert outro.listar("bases")==[]
    assert outro.objeto(id)["id"]==id
    catalogo.conn.execute("DELETE FROM analise.entrega WHERE objeto_id=%s",(id,))
    with pytest.raises(Falha) as e:outro.objeto(id)
    assert e.value.exit==4

def test_coleta_remove_temporario_sem_escrita(catalogo,tmp_path):
    ex=novo("ex")
    catalogo.abrir_execucao(ex,"preparar","s","o-perm")
    catalogo.concluir(ex,"pronta",{})
    catalogo.conn.execute(
        "UPDATE analise.execucao SET temporarios_ate=clock_timestamp()-interval '1 second' WHERE id=%s",
        (ex,),
    )
    raiz=tmp_path/"o-perm"/"analise"/ex
    receita_dir=raiz/"receita"
    receita_dir.mkdir(parents=True)
    arq=receita_dir/"preparar.py"
    arq.write_text("print(1)\n")
    arq.chmod(0o444)
    receita_dir.chmod(0o555)
    assert coletar(catalogo,tmp_path)==0
    assert not raiz.exists()
