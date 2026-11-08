'''lib/ambiente_banco.py — resolve credenciais de leitura do banco e parâmetros de execução de stack.'''
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_ARVORE = Path(__file__).resolve().parents[1]
CANON_INSTANCIA = '/srv/platafirma/casa/'

def _obter_docker_host() -> str:
    return os.environ.get('DOCKER_HOST', 'unix:///run/user/1001/docker.sock')

def _vars_do_dir(caminho: Path) -> dict[str, str]:
    res: dict[str, str] = {}
    try:
        entradas = sorted(caminho.iterdir())
    except OSError:
        return res

    for p in entradas:
        if p.name.endswith('.tmp'):
            continue
        try:
            res[p.name] = p.read_text(encoding='utf-8').strip()
        except OSError:
            pass
    return res

def _env_do_container(container: str) -> dict[str, str]:
    if not container:
        return {}
    docker_host = _obter_docker_host()
    try:
        r = subprocess.run(
            ['docker', 'inspect', container, '--format', '{{range .Config.Env}}{{println .}}{{end}}'],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, 'DOCKER_HOST': docker_host},
            timeout=10,
        )
        if r.returncode != 0:
            return {}
        return dict(linha.split('=', 1) for linha in r.stdout.splitlines() if '=' in linha)
    except (subprocess.SubprocessError, OSError):
        return {}

def _carregar_registro(reg_path: str, stack: str) -> dict:
    if not reg_path:
        return {}
    caminho = Path(reg_path)
    try:
        with open(caminho, encoding='utf-8') as f:
            dados = json.load(f)
            return dados.get(stack) or dados.get('rag') or {}
    except (OSError, json.JSONDecodeError):
        return {}

def _resolver_env_ou_cofre(inst: dict, inst_raiz: Path, stack: str) -> dict[str, str]:
    env: dict[str, str] = {}
    valor = inst.get('env_da_ingestao', '')
    caminho = None
    if valor.startswith(CANON_INSTANCIA):
        caminho = inst_raiz / valor[len(CANON_INSTANCIA):]
    elif valor:
        caminho = Path(valor)

    if caminho is not None and caminho.is_file():
        env['RAG_ENV_FILE'] = str(caminho)
    elif caminho is not None and caminho.is_dir():
        env.update(_vars_do_dir(caminho))
    else:
        cofre_nome = inst.get('banco', {}).get('stack') or inst.get('stack', stack)
        cofre = inst_raiz / 'segredos' / cofre_nome
        cofre_vars = _vars_do_dir(cofre)
        for k, v in cofre_vars.items():
            if k.startswith(('POSTGRES_', 'RAG_')) or k == 'EMBED_MODEL':
                env[k] = v
    return env

def ambiente_da_stack(stack: str = 'rag') -> dict[str, str]:
    reg_path = os.environ.get('PF_MOTOR_REG') or str(_ARVORE / 'registro' / 'motor-instancias.json')
    inst = _carregar_registro(reg_path, stack)
    inst_raiz = Path(os.environ.get('PLATAFIRMA_INSTANCIA', '/srv/platafirma/casa'))

    env = _resolver_env_ou_cofre(inst, inst_raiz, stack)

    if 'EMBED_MODEL' not in env:
        c_name = inst.get('container', 'motor-busca')
        c_env = _env_do_container(c_name)
        if 'EMBED_MODEL' in c_env:
            env['EMBED_MODEL'] = c_env['EMBED_MODEL']

    docker_host = _obter_docker_host()
    if docker_host and 'DOCKER_HOST' not in env:
        env['DOCKER_HOST'] = docker_host

    return env

if __name__ == '__main__':
    stack_arg = sys.argv[1] if len(sys.argv) > 1 else 'rag'
    env_dict = ambiente_da_stack(stack_arg)
    for chave, val in sorted(env_dict.items()):
        sys.stdout.write(f'{chave}={val}\n')
