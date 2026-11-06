"""Ensaios reais de isolamento; rodam somente sob demanda (#4130)."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(RAIZ/"lib"))
from analise.unidade import sondar, executar, MEMORY_MAX, MEMORY_HIGH

def test_host_tem_mecanismo_de_isolamento():
    resultado = sondar()
    relatorio = Path("/srv/platafirma/casa/var/tmp/o20261106T175800-e71467/analise/sonda.json")
    relatorio.parent.mkdir(parents=True, exist_ok=True)
    relatorio.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    assert resultado["systemd"]["exit"] == 0, resultado
    medido = json.loads(resultado["systemd"]["stdout"].strip())
    assert medido["memory.max"] == str(MEMORY_MAX), medido
    assert medido["memory.high"] == str(MEMORY_HIGH), medido
    assert medido["memory.swap.max"] == "0", medido
    assert medido["pids.max"] == "64", medido
    assert medido["inet"] != "permitido", medido
    assert medido["unix"] != "permitido", medido

@pytest.mark.parametrize("codigo,esperado", [
    ("from pathlib import Path\nPath('/saida/tabela.csv').write_text('a\\n1\\n')",0),
    ("import socket\nsocket.socket()",4),
    ("import socket\nsocket.socket(socket.AF_UNIX)",4),
    ("open('/srv/platafirma/casa/segredos/rag/POSTGRES_PASSWORD').read()",4),
    ("open('/entrada/dado','w').write('x')",4),
    ("open('/tmp/fuga','w').write('x')",4),
    ("import subprocess\nsubprocess.Popen(['/usr/bin/sleep','30'])",4),
    ("import modulo_inexistente_4130",4),
])
def test_calculo_contem_tentativas(tmp_path,codigo,esperado):
    receita=tmp_path/"receita"; receita.mkdir()
    entrada=tmp_path/"entrada"; entrada.mkdir()
    saida=tmp_path/"saida"; saida.mkdir()
    (receita/"rodar.py").write_text(codigo)
    rc,metricas=executar([sys.executable,"-I","-B","/executor.py","rodar.py"],
        pasta=receita,entrada=entrada,saida=saida,ambiente=Path(sys.prefix))
    assert rc==esperado
    assert metricas["pico_bytes"]>0


def test_prazo_mata_so_a_unidade(tmp_path):
    from analise import Falha
    receita=tmp_path/"receita";receita.mkdir()
    saida=tmp_path/"saida";saida.mkdir()
    (receita/"rodar.py").write_text("import time\ntime.sleep(30)")
    with pytest.raises(Falha) as e:
        executar([sys.executable,"-I","-B","/executor.py","rodar.py"],
            pasta=receita,saida=saida,ambiente=Path(sys.prefix),prazo=1)
    assert e.value.exit==5

def test_oom_mata_so_a_unidade(tmp_path):
    from analise import Falha
    receita=tmp_path/"receita";receita.mkdir()
    saida=tmp_path/"saida";saida.mkdir()
    (receita/"rodar.py").write_text("import mmap\nx=mmap.mmap(-1,3*1024**3,flags=mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS|mmap.MAP_POPULATE)")
    with pytest.raises(Falha) as e:
        executar([sys.executable,"-I","-B","/executor.py","rodar.py"],
            pasta=receita,saida=saida,ambiente=Path(sys.prefix),
            _tetos_memoria=(128*1024**2,128*1024**2))
    assert e.value.exit==5 and e.value.causa=="teto-oom-kill"
