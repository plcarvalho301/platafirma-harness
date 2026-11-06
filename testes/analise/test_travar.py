"""O resolvedor só aceita wheels e guarda o lock com hashes."""
from pathlib import Path
import pytest
from analise.ambiente import travar,construir
from analise import Falha

def test_travar_pilha_sem_pacotes(tmp_path):
    p=tmp_path/"receita";p.mkdir()
    (p/"pyproject.toml").write_text('[project]\nname="analise-vazia"\nversion="1"\nrequires-python=">=3.12"\ndependencies=[]\n')
    sha=travar(p,tmp_path/"cache")
    assert len(sha)==64 and (p/"uv.lock").is_file()
    env,ident=construir(p,tmp_path/"ambientes")
    assert (env/"bin/python").is_file()
    assert ident["python"].startswith("3.12")

def test_travar_dependencia_impossivel(tmp_path):
    p=tmp_path/"receita";p.mkdir()
    (p/"pyproject.toml").write_text('[project]\nname="analise-impossivel"\nversion="1"\nrequires-python=">=3.12"\ndependencies=["pandas==0.0.0"]\n')
    with pytest.raises(Falha) as e:travar(p,tmp_path/"cache")
    assert e.value.exit==2 and "pandas" in e.value.causa
