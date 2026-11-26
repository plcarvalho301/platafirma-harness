"""lib/topologia.py — resolução de contêiner para stack da topologia (acervo.stack).

Módulo canônico compartilhado entre a verificação de release (bin/_release/conferir/conferir.py)
e a observabilidade de infraestrutura (bin/_infra/eixos.py).
DTs 288 e 377: uma única regra contêiner -> stack no harness.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

PREFIXO_DA_FAMILIA = "platafirma-"
_RE_SHA = re.compile(r"^[0-9a-f]{40}$")
PORTA_MINIMA = 1
PORTA_MAXIMA = 65535


def composes_da_stack(stack: dict) -> list[str]:
    v = stack.get("compose") or []
    return [v] if isinstance(v, str) else list(v)


def stack_do_container(conteiner_ou_labels: dict, topologia: list[dict]) -> str | None:
    """Slug da stack (acervo.stack) cujo compose declarado é o do contêiner.

    O declarado mora sob .../current/<família curta>/<rel>; o contêiner sobe de
    .../<família>/<sha>/<rel> e casa pela família curta e pelo <rel>.

    Duas stacks com o mesmo compose desempatam pelo projeto que o contêiner declara
    (com.docker.compose.project ou projeto); sem desempate, None (nunca a primeira que casa,
    evitando silenciar duplicatas ou mascarar deriva).
    """
    config_files = (
        conteiner_ou_labels.get("config_files")
        or conteiner_ou_labels.get("com.docker.compose.project.config_files")
        or ""
    )
    projeto = (
        conteiner_ou_labels.get("projeto")
        or conteiner_ou_labels.get("com.docker.compose.project")
        or ""
    )

    pares = set()
    for arquivo in [f.strip() for f in config_files.split(",") if f.strip()]:
        partes = arquivo.split(os.sep) if os.sep in arquivo else arquivo.split("/")
        achou_sha = False
        for i, parte in enumerate(partes):
            if _RE_SHA.match(parte):
                familia = partes[i - 1] if i > 0 else ""
                curta = familia.removeprefix(PREFIXO_DA_FAMILIA)
                pares.add((curta, "/".join(partes[i + 1:])))
                achou_sha = True
                break
        if not achou_sha and "/current/" in arquivo:
            resto = arquivo.split("/current/", 1)[1]
            if "/" in resto:
                curta, rel = resto.split("/", 1)
                pares.add((curta.removeprefix(PREFIXO_DA_FAMILIA), rel))

    achados = []
    for stack in topologia:
        for comp in composes_da_stack(stack):
            if "/current/" not in comp:
                continue
            resto = comp.split("/current/", 1)[1]
            if "/" in resto and tuple(resto.split("/", 1)) in pares:
                slug = stack.get("slug")
                if slug and slug not in achados:
                    achados.append(slug)
                break

    if len(achados) <= 1:
        return achados[0] if achados else None

    if projeto:
        do_projeto = [slug for slug in achados if slug == projeto]
        if len(do_projeto) == 1:
            return do_projeto[0]

    return None


stack_do_conteiner = stack_do_container


def _porta_metricas_de_tokens(tokens: list[str]) -> int | None:
    """Extrai a porta de `--metrics [host]:PORTA` ou `--metrics=[host]:PORTA`."""
    alvo = ""
    for i, tok in enumerate(tokens):
        if tok == "--metrics" and i + 1 < len(tokens):
            alvo = tokens[i + 1]
            break
        if tok.startswith("--metrics="):
            alvo = tok.split("=", 1)[1]
            break
    achado = re.search(r":(\d+)$", alvo.strip())
    if not achado:
        return None
    porta = int(achado.group(1))
    return porta if PORTA_MINIMA <= porta <= PORTA_MAXIMA else None


def _tokens_command_cloudflared(caminho: Path) -> tuple[list[str] | None, str]:
    """Lê os tokens de `services.cloudflared.command` em um docker-compose.yml."""
    import shlex

    import yaml

    origem = str(caminho)
    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return None, f"compose ilegível ({origem}): {e}"
    if not isinstance(dados, dict):
        return None, f"compose inválido em {origem}"
    services = dados.get("services")
    cf = services.get("cloudflared") if isinstance(services, dict) else None
    cmd = cf.get("command") if isinstance(cf, dict) else None
    if isinstance(cmd, str):
        try:
            return shlex.split(cmd), origem
        except ValueError as e:
            return None, f"command inválido em {origem}: {e}"
    if isinstance(cmd, list):
        return [str(t) for t in cmd], origem
    return None, f"serviço cloudflared sem command em {origem}"


def porta_metricas_cloudflared(
    compose_path: str | os.PathLike[str] | None = None,
    *,
    env_var: str | None = None,
) -> tuple[int | None, str]:
    """Porta de `--metrics` do `cloudflared` no compose do `core` (fonte única)."""
    import raizes

    if compose_path is not None:
        caminho = Path(compose_path)
    elif env_var and os.environ.get(env_var):
        caminho = Path(os.environ[env_var])
    else:
        caminho = raizes.release() / "core" / "docker-compose.yml"
    tokens, info = _tokens_command_cloudflared(caminho)
    if tokens is None:
        return None, info
    porta = _porta_metricas_de_tokens(tokens)
    if porta is None:
        return None, f"--metrics sem porta válida em {info}"
    return porta, info
