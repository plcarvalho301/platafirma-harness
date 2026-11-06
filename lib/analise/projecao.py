"""PNG com CRC conferido e metadados variáveis removidos, sem executar decoder."""
from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import zlib
from . import exigir

ASSINATURA=b"\x89PNG\r\n\x1a\n"
VOLATEIS={b"tIME",b"tEXt",b"zTXt",b"iTXt"}

def canonizar_png(arquivo: Path) -> dict:
    dados=arquivo.read_bytes()
    exigir(dados.startswith(ASSINATURA),"projecao-invalida",4)
    partes=[ASSINATURA]
    pos=8;largura=altura=0;fim=False;idat=False
    while pos<len(dados):
        exigir(pos+12<=len(dados),"png-truncado",4)
        tamanho=struct.unpack(">I",dados[pos:pos+4])[0]
        tipo=dados[pos+4:pos+8]
        exigir(pos+12+tamanho<=len(dados),"png-truncado",4)
        corpo=dados[pos+8:pos+8+tamanho]
        crc=struct.unpack(">I",dados[pos+8+tamanho:pos+12+tamanho])[0]
        exigir(zlib.crc32(tipo+corpo)&0xffffffff==crc,"png-crc-invalido",4)
        if pos==8:
            exigir(tipo==b"IHDR" and tamanho==13,"png-ihdr-invalido",4)
            largura,altura=struct.unpack(">II",corpo[:8])
            exigir(largura>0 and altura>0,"png-dimensoes-invalidas",4)
        elif tipo==b"IHDR":
            exigir(False,"png-ihdr-duplicado",4)
        if tipo==b"IDAT":
            idat=True
        if tipo not in VOLATEIS:
            partes.append(dados[pos:pos+12+tamanho])
        pos+=12+tamanho
        if tipo==b"IEND":
            exigir(tamanho==0 and pos==len(dados),"png-fim-invalido",4)
            fim=True;break
    exigir(fim and idat,"png-incompleto",4)
    conteudo=b"".join(partes)
    return {"conteudo":conteudo,"sha256":hashlib.sha256(conteudo).hexdigest(),
            "dimensoes":[largura,altura],"bytes":len(conteudo)}
