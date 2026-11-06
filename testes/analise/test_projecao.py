"""A projeção conserva pixels e dimensões, removendo data e texto variáveis."""
import struct
import zlib
import pytest
from analise.projecao import canonizar_png,ASSINATURA
from analise import Falha
from analise.receita import carregar
from analise.publicacao import novo

def png(texto=b""):
    def chunk(tipo,dados):
        return struct.pack(">I",len(dados))+tipo+dados+struct.pack(">I",zlib.crc32(tipo+dados)&0xffffffff)
    return (ASSINATURA+chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,6,0,0,0))+
            (chunk(b"tEXt",texto) if texto else b"")+
            chunk(b"IDAT",zlib.compress(b"\x00\x00\x00\x00\xff"))+chunk(b"IEND",b""))

def test_metadado_variavel_nao_muda_hash(tmp_path):
    a=tmp_path/"a.png";b=tmp_path/"b.png"
    a.write_bytes(png(b"data\x00ontem"));b.write_bytes(png(b"data\x00hoje"))
    assert canonizar_png(a)==canonizar_png(b)
    assert canonizar_png(a)["dimensoes"]==[1,1]

def test_projecao_publicada(catalogo,tmp_path,receita):
    out=tmp_path/"out";out.mkdir()
    (out/"grafico.png").write_bytes(png())
    r=carregar(receita);r["saidas"]={"projecoes":["grafico"]}
    ex=novo("ex");catalogo.abrir_execucao(ex,"preparar","s","o")
    obj=catalogo.publicar(ex,r,"png",out,{"serializacao":r["serializacao"]})
    assert catalogo.conn.execute("SELECT largura,altura FROM analise.projecao WHERE objeto_id=%s",(obj,)).fetchone()==(1,1)

def test_crc_errado_recusa(tmp_path):
    p=tmp_path/"a.png";p.write_bytes(png()[:-1]+b"x")
    with pytest.raises(Falha) as e:canonizar_png(p)
    assert e.value.exit==4
