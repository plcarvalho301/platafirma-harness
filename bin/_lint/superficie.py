"""superficie — predicados de equalizacao de superficies e tools."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .resultado import Apontamento


def _sh(args: list[str], cwd: Optional[str | Path] = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _obter_harness_dir(harness_dir: Optional[Path | str] = None) -> Path:
    if harness_dir is not None:
        return Path(harness_dir)
    env_h = os.environ.get("PF_HARNESS_DIR")
    if env_h:
        return Path(env_h)
    return Path(__file__).resolve().parents[2]


def _conectores_do_produtor(prod: dict, harness_dir: Optional[Path | str] = None) -> tuple[set[str], Optional[str]]:
    hdir = _obter_harness_dir(harness_dir)
    tipo = prod.get("tipo")
    if tipo == "arquivo-rastreado":
        caminho = hdir / prod.get("caminho", ".mcp.json")
        try:
            with open(caminho, encoding="utf-8") as f:
                return set(json.load(f).get("mcpServers", {})), None
        except (OSError, ValueError) as e:
            return set(), f"{prod.get('caminho')}: {e}"
    if tipo == "bash-heredoc-json":
        caminho = hdir / prod.get("arquivo", "")
        marcador = prod.get("marcador", "JSON")
        try:
            texto = open(caminho, encoding="utf-8").read()
        except OSError as e:
            return set(), f"{prod.get('arquivo')}: {e}"
        quebra = chr(10)
        marca_abre = "<<" + marcador
        pos = texto.find(marca_abre)
        if pos == -1:
            return set(), f"heredoc <<{marcador} nao encontrado em {prod.get('arquivo')}"
        linhas_apos = texto[pos + len(marca_abre):].split(quebra)[1:]
        corpo, fechou = [], False
        for linha in linhas_apos:
            if linha.strip() == marcador:
                fechou = True
                break
            corpo.append(linha)
        if not fechou:
            return set(), f"heredoc <<{marcador} nao fechou em {prod.get('arquivo')}"
        try:
            dado = json.loads(quebra.join(corpo))
        except ValueError as e:
            return set(), f"heredoc de {prod.get('arquivo')} nao e JSON valido: {e}"
        return set(dado.get("mcpServers", {})), None
    if tipo == "codigo":
        caminho = hdir / prod.get("arquivo", "")
        simbolo = prod.get("simbolo", "")
        try:
            import ast
            arvore = ast.parse(open(caminho, encoding="utf-8").read())
        except (OSError, SyntaxError) as e:
            return set(), f"{prod.get('arquivo')}: {e}"
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Assign):
                continue
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id == simbolo:
                    if isinstance(no.value, ast.Dict):
                        nomes = set()
                        for k in no.value.keys:
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                nomes.add(k.value)
                        return nomes, None
                    return set(), f"{simbolo} nao e dict literal"
        return set(), f"{simbolo} nao encontrado em {prod.get('arquivo')}"
    return set(), f"tipo de produtor desconhecido: {tipo!r}"


def _texto_da_fita(harness_dir: Optional[Path | str] = None) -> list[str]:
    hdir = _obter_harness_dir(harness_dir)
    alvos = []
    for sub in ("personas", "tool-manifest"):
        d = hdir / sub
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.name.endswith(".md"):
                alvos.append(str(p))
    skills = hdir / "skills"
    if skills.is_dir():
        for sub in skills.iterdir():
            md = sub / "SKILL.md"
            if not md.is_file():
                continue
            try:
                cabeca = md.read_text(encoding="utf-8", errors="replace")[:2000]
                m = re.search(r"^cadeiras:\s*(.+)$", cabeca, re.M)
                if m and "nenhuma" not in m.group(1).lower():
                    alvos.append(str(md))
            except OSError:
                pass
    return alvos


def _tools_citadas(linha: str, padrao: re.Pattern):
    for m in padrao.finditer(linha):
        yield m.group(1) or m.group(2)


def _quebradas_no_staged(padrao: re.Pattern, servidas: set[str], harness_dir: Optional[Path | str] = None) -> list[tuple[str, int, str]]:
    hdir = _obter_harness_dir(harness_dir)
    carregados = {os.path.relpath(c, hdir) for c in _texto_da_fita(hdir)}
    rc, saida, _ = _sh(["git", "diff", "--cached", "--unified=0"], cwd=hdir)
    if rc != 0:
        return []
    achados, arquivo, linha_n = [], None, 0
    for linha in saida.split("\n"):
        if linha.startswith("+++ b/"):
            arquivo = linha[6:].strip()
            continue
        if linha.startswith("@@"):
            m = re.search(r"\+(\d+)", linha)
            linha_n = int(m.group(1)) if m else 0
            continue
        if not linha.startswith("+") or linha.startswith("+++"):
            continue
        if arquivo in carregados:
            for t in _tools_citadas(linha[1:], padrao):
                if t not in servidas:
                    achados.append((arquivo, linha_n, t))
        linha_n += 1
    return achados


def verificar_superficie(
    raiz: Path | str,
    staged: bool = False,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Verifica equalizacao de superficies e conformidade de tools."""
    harness_dir = Path(raiz)
    registro_path = harness_dir / "registro" / "superficies.json"
    if not registro_path.is_file():
        return []

    try:
        with open(registro_path, encoding="utf-8") as f:
            reg = json.load(f)
    except (OSError, ValueError) as e:
        return [
            Apontamento(
                "registro/superficies.json",
                1,
                f"registro de superficies ilegivel: {e}",
                "corrigir formato JSON de registro/superficies.json",
                severidade="bloqueante",
            )
        ]

    conectores = reg.get("conectores", {})
    servidas = {t for c in conectores.values() for t in c.get("serve", [])}
    conhecidas = servidas | set(reg.get("aposentadas", {}).get("nomes", []))
    padrao = re.compile(
        r"\bmcp__[\w-]+__(\w+)\b|\b(" + "|".join(re.escape(t) for t in sorted(conhecidas)) + r")\b"
    )

    apontamentos: list[Apontamento] = []

    # 1. Conectores dos produtores declarados
    if not staged:
        for nome, sup in reg.get("superficies", {}).items():
            if not sup.get("verificavel_do_host"):
                continue
            exigidos = set(sup.get("conectores", []))
            prod = sup.get("produtor")
            if not prod:
                apontamentos.append(
                    Apontamento(
                        "registro/superficies.json",
                        1,
                        f"superficie '{nome}' verificavel sem produtor declarado",
                        "declarar bloco produtor para a superficie em superficies.json",
                        severidade="bloqueante",
                    )
                )
                continue
            produzidos, erro = _conectores_do_produtor(prod, harness_dir)
            if erro:
                apontamentos.append(
                    Apontamento(
                        prod.get("caminho") or prod.get("arquivo") or "registro/superficies.json",
                        1,
                        f"produtor de '{nome}' ilegivel: {erro}",
                        "corrigir arquivo de configuracao do produtor",
                        severidade="bloqueante",
                    )
                )
                continue
            for falta in sorted(exigidos - produzidos):
                apontamentos.append(
                    Apontamento(
                        "registro/superficies.json",
                        1,
                        f"conector prometido nao servido na superficie '{nome}': {falta}",
                        f"servir conector '{falta}' na superficie ou remover de superficies.json",
                        severidade="bloqueante",
                    )
                )

        # 2. Capacidade nas_tres sem meio
        for cap, dado in reg.get("capacidades", {}).items():
            alvo_tools = [
                t for t in re.findall(r"\b\w+\b", dado.get("meio", ""))
                if t.endswith("_search") or t in servidas
            ]
            if dado.get("nas_tres") and not alvo_tools and "verbo" not in dado.get("meio", ""):
                apontamentos.append(
                    Apontamento(
                        "registro/superficies.json",
                        1,
                        f"capacidade nas_tres '{cap}' sem meio servido por conector nenhum",
                        "associar ferramenta valida servida por conector para a capacidade",
                        severidade="aviso",
                    )
                )

    # 3. Quebradas (texto da fita citando tool fora de todo conector)
    if staged:
        quebradas = _quebradas_no_staged(padrao, servidas, harness_dir)
    else:
        quebradas = []
        for caminho in _texto_da_fita(harness_dir):
            try:
                with open(caminho, encoding="utf-8", errors="replace") as f:
                    linhas = f.read().split("\n")
            except OSError:
                continue
            rel = os.path.relpath(caminho, harness_dir)
            if alvo and rel != alvo:
                continue
            for n, linha in enumerate(linhas, 1):
                for t in _tools_citadas(linha, padrao):
                    if t not in servidas:
                        quebradas.append((rel, n, t))

    for arq, n, t in quebradas:
        apontamentos.append(
            Apontamento(
                arq,
                n,
                f"tool citada fora de todo conector servido: '{t}'",
                "usar apenas tools declaradas nos conectores da superficie",
                severidade="bloqueante",
            )
        )

    return apontamentos
