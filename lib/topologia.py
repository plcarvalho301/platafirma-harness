"""lib/topologia.py — resolução de contêiner para stack da topologia (acervo.stack).

Módulo canônico compartilhado entre a verificação de release (bin/_release/conferir/conferir.py)
e a observabilidade de infraestrutura (bin/_infra/eixos.py).
DTs 288 e 377: uma única regra contêiner -> stack no harness.
"""
from __future__ import annotations

import os
import re

PREFIXO_DA_FAMILIA = "platafirma-"
_RE_SHA = re.compile(r"^[0-9a-f]{40}$")


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
        for i, parte in enumerate(partes):
            if _RE_SHA.match(parte):
                familia = partes[i - 1] if i > 0 else ""
                curta = familia.removeprefix(PREFIXO_DA_FAMILIA)
                pares.add((curta, "/".join(partes[i + 1:])))
                break

    achados = []
    for stack in topologia:
        for comp in composes_da_stack(stack):
            if "/current/" not in comp:
                continue
            resto = comp.split("/current/", 1)[1]
            if "/" in resto and tuple(resto.split("/", 1)) in pares:
                slug = stack.get("slug")
                if slug:
                    achados.append(slug)

    if len(achados) <= 1:
        return achados[0] if achados else None

    if projeto:
        do_projeto = [slug for slug in achados if slug == projeto]
        if len(do_projeto) == 1:
            return do_projeto[0]

    return None


stack_do_conteiner = stack_do_container
