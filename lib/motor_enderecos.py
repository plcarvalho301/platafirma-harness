"""motor_enderecos — os dois endereços do motor, lidos só do registro das instâncias (#3843, R28 da spec motor).

Quem chama a BUSCA (o `/search` e as rotas `/motor/...`) e quem chama a API do ACERVO (as rotas `/acervo/...`)
são dois grupos, e cada um lê o seu endereço de `registro/motor-instancias.json`, em `<instancia>.enderecos`:
`busca` e `api_acervo`. Nenhum chamador do harness guarda porta literal. Até a virada da #3776 os dois apontam
para o rag-extractor-api; a virada troca o `busca` no registro, e só ele.

O ambiente de cada chamador (MOTOR_ACERVO_URL, RAG_API_URL, RAG_API_BASE) continua valendo mais que o registro:
é o degrau que o teste e a bancada usam. Este módulo só responde o último degrau, o que antes era o literal.

Registro ausente, ilegível ou sem a chave: `EnderecoNaoDeclarado`, com o caminho e a chave. Nunca um default calado.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_ARVORE = Path(__file__).resolve().parents[1]
INSTANCIA = "rag"


class EnderecoNaoDeclarado(RuntimeError):
    """O registro não declara o endereço pedido: sem ele não há onde chamar."""


def caminho_do_registro() -> Path:
    """`PF_MOTOR_REG` (o teste aponta para um temporário) ou o registro da árvore que serve este módulo."""
    return Path(os.environ.get("PF_MOTOR_REG") or _ARVORE / "registro" / "motor-instancias.json")


def _endereco(chave: str, instancia: str) -> str:
    caminho = caminho_do_registro()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise EnderecoNaoDeclarado(f"registro das instâncias ilegível em {caminho}: {e}") from e
    inst = dados.get(instancia) if isinstance(dados, dict) else None
    valor = ((inst or {}).get("enderecos") or {}).get(chave) if isinstance(inst, dict) else None
    if not isinstance(valor, str) or not valor.strip():
        raise EnderecoNaoDeclarado(f"{caminho}: a instância `{instancia}` não declara `enderecos.{chave}`")
    return valor.strip().rstrip("/")


def busca(instancia: str = INSTANCIA) -> str:
    """Base de quem chama a busca: `/search`, `/facets`, `/motor/...`."""
    return _endereco("busca", instancia)


def api_acervo(instancia: str = INSTANCIA) -> str:
    """Base de quem chama a API do acervo: `/acervo/...`."""
    return _endereco("api_acervo", instancia)
