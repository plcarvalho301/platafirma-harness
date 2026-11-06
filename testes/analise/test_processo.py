"""A chamada pública roda em unidade irmã e usa as duas credenciais de teste."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from conftest import RAIZ,CONHECIMENTO
from test_extrator import semear

def test_cli_em_unidade_dedicada(db,tmp_path):
    cfg,admin=db
    semear(admin)
    servido=tmp_path/"release";servido.mkdir()
    (servido/"conhecimento").symlink_to(CONHECIMENTO,target_is_directory=True)
    politica=servido/"harness/politica-acesso";politica.mkdir(parents=True)
    for nome in ("pdp.py","politica.yaml"):
        shutil.copy2(RAIZ/"politica-acesso"/nome,politica/nome)
    (politica/"sujeitos.yaml").write_text('sujeitos:\n  teste:\n    natureza: pessoa\n    papeis: [operador]\n    dominios: [plataforma]\n')
    instancia=tmp_path/"instancia"
    cofre=instancia/"segredos/rag";cofre.mkdir(parents=True)
    env={**os.environ,"PLATAFIRMA_RELEASE":str(servido),
         "PLATAFIRMA_INSTANCIA":str(instancia),"PF_SUJEITO":"teste",
         "PF_SESSAO":"teste","PF_ORDEM_ID":"teste-cli","PF_CADEIRA":"engenharia"}
    for prefixo in ("ANALISE_ORIGEM_","ANALISE_DESTINO_"):
        (cofre/(prefixo+"PASSWORD")).write_text(cfg["password"])
        env[prefixo+"HOST"]=cfg["host"];env[prefixo+"PORT"]=str(cfg["port"])
        env[prefixo+"DB"]=cfg["dbname"]
    p=subprocess.run([sys.executable,str(RAIZ/"bin/analise"),"preparar","populacao-de-turnos",
                      "--corte","2026-11-02T00:00:00Z"],env=env,capture_output=True,text=True,
                     timeout=60,check=False)
    assert p.returncode==0,p.stdout
    doc=json.loads(p.stdout)
    assert doc["exit"]==0 and doc["base_id"]
    assert doc["manifesto"]["fases"]["extrair"]["pico_bytes"]>0
    assert doc["manifesto"]["unidade"].startswith("platafirma-analise-trabalho-")
