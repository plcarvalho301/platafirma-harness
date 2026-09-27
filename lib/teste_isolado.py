"""Isolamento de suíte de teste: teste não lê nem escreve estado real.

Regra do dono (27/09/2026): teste não depende de estado real — acervo, instância,
release no ar, bancada da conta, serviço de pé, forge, identidade de quem roda. Teste
que depende dele muda de cor quando o sistema evolui, e vermelho por evolução não é
risco a anotar: é teste errado. Regra e porquê: `acervo ler casa guia portoes-do-codigo`.

Cada suíte chama `isolar()` do seu conftest.py, uma vez, antes da coleta:
  1. sai do ambiente toda variável da plataforma (PREFIXOS) e a identidade da conta
     (USER, LOGNAME viram «teste»);
  2. as raízes apontam para um diretório temporário vazio;
  3. os serviços apontam para a porta 9 (discard): nada responde, a falha é imediata;
  4. programas que falam com o mundo (DELATORES) entram no PATH como delatores: saem
     97 dizendo que o teste chamou o real sem stub. O stub de um teste vem antes no PATH
     e ganha do delator.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

PREFIXOS = (
    "PLATAFIRMA_", "PF_", "RAG_", "MOTOR_", "MEM_", "FILA_", "SESSAO_", "MW_",
    "KROKI_", "ACESSO_", "PDP_", "OPS_", "SEG_", "TAREFAS_", "REC_", "CHAT_",
    "INFRA_", "OIDC_", "MINUTA_", "PERSONA_", "AGREGADOR_", "ACERVO_", "CORPUS_",
    "JUIZ_", "OLLAMA_",
)

# variáveis que, mesmo com prefixo da plataforma, são ferramenta e não estado: o
# tokenizador do modelo é artefato pinado (registro/terceiros.json), como o uv
PRESERVAR = ("PLATAFIRMA_TOKENIZADOR",)

DELATORES = ("docker", "gh", "systemctl", "psql", "redis-cli")

SERVICO_MORTO = "http://127.0.0.1:9"


def isolar() -> Path:
    raiz = Path(tempfile.mkdtemp(prefix="pf-teste-"))
    for nome in list(os.environ):
        if nome.startswith(PREFIXOS) and nome not in PRESERVAR:
            del os.environ[nome]

    for sub in ("instancia", "opt", "bancada"):
        (raiz / sub).mkdir()
    os.environ.update({
        "USER": "teste",
        "LOGNAME": "teste",
        "PLATAFIRMA_INSTANCIA": str(raiz / "instancia"),
        "PF_RELEASE_RAIZ": str(raiz / "opt"),
        "PLATAFIRMA_RELEASE": str(raiz / "opt" / "current"),
        "PLATAFIRMA_BANCADA": str(raiz / "bancada"),
        "PLATAFIRMA_ARQUIVO_BANCADA": str(raiz / "bancada-nao-declarada"),
        "PF_ABERTURA_DIR": str(raiz / "instancia" / "var" / "abertura-publicada"),
        "PF_LINT_ACERVO": "/bin/false",
        "RAG_API_URL": SERVICO_MORTO,
        "RAG_API_BASE": SERVICO_MORTO,
        "MOTOR_ACERVO_URL": SERVICO_MORTO,
        "MW_API_URL": SERVICO_MORTO + "/api.php",
        "KROKI_URL": SERVICO_MORTO,
        "TAREFAS_BASE": SERVICO_MORTO + "/api",
        "PF_RASTREADOR_BASE": SERVICO_MORTO,
        "MEM_REDIS_PORT": "9",
        "FILA_REDIS_PORT": "9",
        "REC_CACHE_PORT": "9",
        "SESSAO_PG_PORT": "9",
    })

    delatores = raiz / "delatores"
    delatores.mkdir()
    for prog in DELATORES:
        p = delatores / prog
        p.write_text(
            "#!/bin/sh\n"
            f'echo "teste chamou o {prog} real sem stub: $*" >&2\n'
            "exit 97\n")
        p.chmod(0o755)
    os.environ["PATH"] = f"{delatores}{os.pathsep}{os.environ.get('PATH', '')}"
    return raiz


def desfazer(raiz: Path | None) -> None:
    if raiz is not None:
        shutil.rmtree(raiz, ignore_errors=True)
