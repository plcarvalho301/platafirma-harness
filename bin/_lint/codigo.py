"""codigo — linter de codigo da stack do repositorio (ruff, npm, bash)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .resultado import Apontamento

def detectar_stack(raiz: Path) -> Optional[Tuple[str, str]]:
    """Detecta stack de linter do repo: (stack, comando).
    
    Ordem de deteccao:
      python: pyproject.toml | .ruff.toml | ruff.toml | .ruff_cache
      node:   package.json com scripts.lint
      bash:   bin/ ou *.sh
    """
    if (
        (raiz / "pyproject.toml").is_file()
        or (raiz / ".ruff.toml").is_file()
        or (raiz / "ruff.toml").is_file()
        or (raiz / ".ruff_cache").is_dir()
    ):
        return "python", "ruff check"

    pkg = raiz / "package.json"
    if pkg.is_file():
        try:
            conteudo = pkg.read_text(encoding="utf-8", errors="replace")
            if '"lint"' in conteudo:
                return "node", "npm run lint"
        except OSError:
            pass

    if (raiz / "bin").is_dir() or any(raiz.glob("*.sh")):
        return "bash", "lint_bash"

    return None

def raiz_da_stack(raiz: Path, alvo: Optional[str] = None) -> Path:
    """Projeto que contem o alvo: o diretorio mais proximo, do alvo ate a raiz, com
    manifesto python ou node (card #3074).

    Sem isso, um alvo em subprojeto (platafirma-conhecimento/rag, com pyproject so em
    rag/) herdava a stack da raiz do clone (bash, por causa de bin/) e o ruff nunca
    rodava: 0 apontamentos, verde falso. Sem alvo, ou alvo sem subprojeto, e a raiz.
    """
    raiz = raiz.resolve()
    if not alvo:
        return raiz
    p = (raiz / alvo).resolve()
    d = p if p.is_dir() else p.parent
    while d != raiz and d.is_relative_to(raiz):
        det = detectar_stack(d)
        if det and det[0] in ("python", "node"):
            return d
        d = d.parent
    return raiz

def _lint_bash(raiz: Path, alvo: Optional[str] = None) -> list[Apontamento]:
    apontamentos: list[Apontamento] = []
    candidatos: list[Path] = []
    if alvo:
        p = (raiz / alvo).resolve()
        if p.is_file():
            candidatos.append(p)
    else:
        bin_dir = raiz / "bin"
        if bin_dir.is_dir():
            for f in bin_dir.iterdir():
                if f.is_file() and not f.name.startswith((".", "_")) and "." not in f.name:
                    candidatos.append(f)
        for f in raiz.glob("*.sh"):
            if f.is_file():
                candidatos.append(f)

    for f in candidatos:
        rel = str(f.relative_to(raiz)) if f.is_relative_to(raiz) else f.name
        try:
            linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        in_func = False
        func_name = ""
        last_line = ""
        for i, linha in enumerate(linhas, 1):
            if re.match(r"^[a-zA-Z_0-9]+[ ]*\(\)[ ]*\{", linha):
                in_func = True
                func_name = linha.split("(", 1)[0].strip()
                last_line = ""
            elif in_func and linha.strip() == "}":
                if (
                    re.match(r"^[ \t]*\[.*\][ \t]*&&", last_line)
                    and "||" not in last_line
                ):
                    apontamentos.append(
                        Apontamento(
                            rel,
                            i - 1,
                            f"{func_name} termina com condicional sob set -e sem return/exit explicito",
                            "adicionar exit ou return explicito apos condicional",
                            severidade="bloqueante",
                            id="BASH_SET_E",
                        )
                    )
                in_func = False
            elif in_func and linha.strip() and not linha.strip().startswith("#"):
                last_line = linha

    return apontamentos

def verificar_codigo(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> Tuple[list[Apontamento], Optional[str]]:
    """Roda o linter detectado no repositorio.
    
    Retorna (lista_apontamentos, stack).
    Lanca ValueError(exit_code, msg) se indeterminavel ou linter falhar.
    """
    raiz = Path(raiz).resolve()
    # o linter roda no projeto que contem o alvo (subprojeto com manifesto proprio),
    # com cwd la para o ruff achar a configuracao dele; os caminhos voltam relativos
    # a raiz do clone
    raiz_stack = raiz_da_stack(raiz, alvo)
    prefixo = "" if raiz_stack == raiz else f"{raiz_stack.relative_to(raiz)}/"
    deteccao = detectar_stack(raiz_stack)
    if not deteccao:
        # Exit 5: indeterminavel
        raise ValueError(5, f"indeterminavel — nenhuma stack de lint detectada em {raiz_stack}")

    stack, cmd = deteccao
    apontamentos: list[Apontamento] = []

    alvo_path = (raiz / alvo).resolve() if alvo else raiz_stack
    alvo_rel = str(alvo_path.relative_to(raiz_stack)) if alvo and alvo_path.is_relative_to(raiz_stack) else (alvo or ".")

    if stack == "python":
        # Tenta ruff direto, senao uvx ruff, senao python3 -m ruff
        # --output-format=concise: o parser abaixo le arquivo:linha:col: REGRA; o formato
        # padrao do ruff desde 0.5 (full) quebra a linha e virava apontamento de lixo
        check = ["check", "--output-format=concise", alvo_rel]
        linter_bin = shutil.which("ruff")
        if linter_bin:
            cmd_args = [linter_bin, *check]
        elif shutil.which("uvx"):
            cmd_args = ["uvx", "ruff", *check]
        elif shutil.which("python3"):
            cmd_args = ["python3", "-m", "ruff", *check]
        else:
            raise ValueError(3, "linter python (ruff) ausente no ambiente")

        try:
            proc = subprocess.run(
                cmd_args,
                cwd=str(raiz_stack),
                capture_output=True,
                text=True,
            )
        except OSError as e:
            raise ValueError(3, f"falha ao executar linter python: {e}")

        # Se ruff encontrou erros
        if proc.returncode != 0:
            for linha in proc.stdout.splitlines():
                # Formato: arquivo:linha:col: REGRA mensagem
                partes = linha.split(":", 3)
                if len(partes) >= 4:
                    arq, lin, col, resto = partes[0].strip(), partes[1].strip(), partes[2].strip(), partes[3].strip()
                    try:
                        lin_num = int(lin)
                    except ValueError:
                        lin_num = 1
                    apontamentos.append(
                        Apontamento(
                            prefixo + arq,
                            lin_num,
                            resto,
                            "corrigir apontamento de estilo/qualidade indicado pelo linter",
                            severidade="aviso",
                        )
                    )
                elif len(partes) >= 3:
                    arq, lin, resto = partes[0].strip(), partes[1].strip(), partes[2].strip()
                    try:
                        lin_num = int(lin)
                    except ValueError:
                        lin_num = 1
                    apontamentos.append(
                        Apontamento(
                            prefixo + arq,
                            lin_num,
                            resto,
                            "corrigir apontamento indicado pelo linter",
                            severidade="aviso",
                        )
                    )

        # Se houver bin/ com scripts bash e alvo nao restringe a arquivo python
        if (raiz_stack / "bin").is_dir() and (not alvo or not alvo.endswith(".py")):
            apontamentos.extend(_lint_bash(raiz_stack, alvo_rel if alvo else None))

    elif stack == "node":
        if not shutil.which("npm"):
            raise ValueError(3, "npm ausente no ambiente")
        cmd_args = ["npm", "run", "lint"]
        if alvo:
            cmd_args.extend(["--", alvo_rel])
        try:
            proc = subprocess.run(cmd_args, cwd=str(raiz_stack), capture_output=True, text=True)
            if proc.returncode != 0:
                for l in (proc.stdout + "\n" + proc.stderr).splitlines():
                    if ":" in l:
                        apontamentos.append(
                            Apontamento(
                                alvo or str(raiz.name),
                                1,
                                l.strip(),
                                "corrigir apontamento do linter node",
                                severidade="aviso",
                            )
                        )
        except OSError as e:
            raise ValueError(3, f"falha ao rodar npm run lint: {e}")

    elif stack == "bash":
        apontamentos.extend(_lint_bash(raiz, alvo))

    return apontamentos, stack
