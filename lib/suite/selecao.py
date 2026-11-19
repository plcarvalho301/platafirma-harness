"""Seleção na fita dos testes do componente mexido."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from suite.vinculo import (
    VinculoArquivo,
    ler_cabecalho,
    ler_vinculo,
    normalizar_componente,
)

LIB_RAIZ = Path(__file__).resolve().parents[1]
_PYTEST_SEM_TESTES = 5

PASTAS_IGNORADAS = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
        "apoio",
        "fixtures",
        "contratos",
    }
)

PASTAS_TESTE = frozenset({"testes", "tests", "provas"})

NOMES_IGNORADOS = frozenset(
    {
        "conftest.py",
        "__init__.py",
        "VERDES",
        "pyproject.toml",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "requirements-teste.txt",
    }
)

EXTENSOES_IGNORADAS = frozenset(
    {
        ".yaml",
        ".yml",
        ".json",
        ".md",
        ".txt",
        ".toml",
        ".lock",
        ".patch",
        ".pyc",
        ".pyo",
        ".ini",
        ".cfg",
        ".sql",
        ".ttl",
    }
)


@dataclass(frozen=True)
class ResultadoSelecao:
    componente: str
    ampliado: bool
    arquivos: tuple[str, ...]
    rodados: int
    aprovados: int
    reprovados: int
    fora_exige: int
    nao_medidos: tuple[str, ...]
    duracao_s: float
    saida: str
    codigo_saida: int

    def como_dict(self) -> dict[str, Any]:
        return {
            "componente": self.componente,
            "ampliado": self.ampliado,
            "arquivos": list(self.arquivos),
            "rodados": self.rodados,
            "aprovados": self.aprovados,
            "reprovados": self.reprovados,
            "fora_exige": self.fora_exige,
            "nao_medidos": list(self.nao_medidos),
            "duracao_s": round(self.duracao_s, 3),
            "codigo_saida": self.codigo_saida,
        }

    def resumo_texto(self) -> str:
        escopo = " (ampliado)" if self.ampliado else ""
        resumo = (
            f"selecao {self.componente}{escopo}: {self.rodados} casos rodados, "
            f"{self.aprovados} aprovados, {self.reprovados} reprovados, "
            f"{self.fora_exige} com exige fora ({self.duracao_s:.2f} s)"
        )
        linhas = [resumo]
        if self.nao_medidos:
            linhas.append(f"nao medido: {', '.join(self.nao_medidos)}")
        return "\n".join(linhas)


def _eh_nome_de_teste(arq: Path) -> bool:
    nome = arq.name
    stem = arq.stem
    return nome.startswith(("test_", "prova_")) or stem.endswith("_test")


def descobrir_arquivos_teste(arvore: str | Path) -> list[Path]:
    """Descobre os arquivos de teste de uma árvore."""
    raiz = Path(arvore).resolve()
    if raiz.is_file():
        return [raiz]
    encontrados: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = sorted(d for d in dirnames if d not in PASTAS_IGNORADAS and not d.startswith("."))
        pasta_atual = Path(dirpath)
        partes_rel = pasta_atual.relative_to(raiz).parts
        em_pasta_teste = any(p in PASTAS_TESTE for p in partes_rel)
        for fn in sorted(filenames):
            if fn in NOMES_IGNORADOS or fn.startswith("."):
                continue
            arq = pasta_atual / fn
            if arq.suffix.lower() in EXTENSOES_IGNORADAS:
                continue
            if _eh_nome_de_teste(arq):
                encontrados.append(arq)
            elif em_pasta_teste:
                try:
                    texto = arq.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                comp, _ = ler_cabecalho(texto)
                if comp is not None:
                    encontrados.append(arq)
    return sorted(encontrados)


def _rodar_pytest(
    raiz: Path,
    arquivos: list[Path],
    *,
    ampliado: bool,
    prazo_s: int = 60,
) -> tuple[int, int, int, int, str]:
    with tempfile.TemporaryDirectory(prefix="suite-pytest-") as tmp:
        tmp_path = Path(tmp)
        rel_json = tmp_path / "relatorio.json"
        cache_dir = tmp_path / "pytest_cache"
        env = dict(os.environ)
        py_paths = [str(LIB_RAIZ), str(raiz)]
        if env.get("PYTHONPATH"):
            py_paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(py_paths))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PF_SUITE_RELATORIO"] = str(rel_json)
        if not ampliado:
            env["PF_SUITE_SEM_EXIGE"] = "1"
        else:
            env.pop("PF_SUITE_SEM_EXIGE", None)

        if importlib.util.find_spec("pytest") is not None:
            base_py = [sys.executable, "-m", "pytest"]
        else:
            uv_bin = shutil.which("uv") or "/usr/local/bin/uv"
            base_py = [
                uv_bin,
                "run",
                "--offline",
                "--no-project",
                "--python",
                sys.executable,
                "--with",
                "pytest",
                "pytest",
            ]
        cmd = [
            *base_py,
            "-p",
            "suite.marcas",
            "-p",
            "no:cacheprovider",
            "-o",
            f"cache_dir={cache_dir}",
            "-q",
            *(str(a) for a in arquivos),
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(raiz),
            env=env,
            capture_output=True,
            text=True,
            timeout=prazo_s,
            check=False,
        )
        saida = (proc.stdout or "") + (proc.stderr or "")
        try:
            dados = json.loads(rel_json.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            dados = None

        if isinstance(dados, dict):
            rodados = int(dados.get("rodados", 0))
            aprovados = int(dados.get("aprovados", 0))
            reprovados = int(dados.get("reprovados", 0))
            fora_exige = int(dados.get("fora_exige", 0))
            if proc.returncode not in (0, _PYTEST_SEM_TESTES) and reprovados == 0:
                reprovados = 1
            return rodados, aprovados, reprovados, fora_exige, saida

        if proc.returncode == _PYTEST_SEM_TESTES:
            return 0, 0, 0, 0, saida
        if proc.returncode == 0:
            return len(arquivos), len(arquivos), 0, 0, saida
        return len(arquivos), 0, 1, 0, saida


def _rodar_script(
    runner: str,
    raiz: Path,
    vinculo: VinculoArquivo,
    *,
    ampliado: bool,
    prazo_s: int = 60,
) -> tuple[int, int, int, int, str]:
    casos = vinculo.casos
    if not ampliado:
        if casos:
            com_exige = [c for c in casos if c.exige]
            sem_exige = [c for c in casos if not c.exige]
            if com_exige and not sem_exige:
                return 0, 0, 0, len(com_exige), ""
            fora = len(com_exige)
            n_rodar = len(sem_exige)
        elif vinculo.exige:
            return 0, 0, 0, 1, ""
        else:
            fora = 0
            n_rodar = 1
    else:
        fora = 0
        n_rodar = max(1, len(casos))

    proc = subprocess.run(
        [runner, str(vinculo.caminho)],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        timeout=prazo_s,
        check=False,
    )
    saida = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        return n_rodar, n_rodar, 0, fora, saida
    return n_rodar, 0, n_rodar, fora, saida


def _coletar_vinculos_componente(
    raiz: Path,
    alvo_comp: str,
    *,
    ampliado: bool,
) -> list[VinculoArquivo]:
    selecionados: list[VinculoArquivo] = []
    for arq in descobrir_arquivos_teste(raiz):
        v = ler_vinculo(arq)
        if v.componente != alvo_comp:
            continue
        if not ampliado and v.classe != "teste-de-comportamento":
            continue
        selecionados.append(v)
    return selecionados


def selecionar(
    componente: str,
    arvore: str | Path = ".",
    *,
    ampliado: bool = False,
    prazo_s: int = 60,
) -> ResultadoSelecao:
    """Seleciona e roda os testes do componente na árvore."""
    t0 = time.monotonic()
    raiz = Path(arvore).resolve()
    alvo_comp = normalizar_componente(componente) or componente
    selecionados = _coletar_vinculos_componente(raiz, alvo_comp, ampliado=ampliado)

    arqs_py: list[Path] = []
    arqs_script: list[tuple[str, VinculoArquivo]] = []
    nao_medidos: list[str] = []
    rels_selecionados: list[str] = []

    for v in selecionados:
        rel = v.caminho.relative_to(raiz).as_posix() if v.caminho.is_relative_to(raiz) else str(v.caminho)
        rels_selecionados.append(rel)
        suf = v.caminho.suffix.lower()
        if suf == ".py":
            arqs_py.append(v.caminho)
        elif suf == ".sh":
            arqs_script.append(("bash", v))
        elif suf == ".mjs":
            arqs_script.append(("node", v))
        else:
            nao_medidos.append(rel)

    rodados = 0
    aprovados = 0
    reprovados = 0
    fora_exige = 0
    saidas: list[str] = []

    if arqs_py:
        r, a, rep, f_ex, s = _rodar_pytest(raiz, arqs_py, ampliado=ampliado, prazo_s=prazo_s)
        rodados, aprovados, reprovados, fora_exige = r, a, rep, f_ex
        if s.strip():
            saidas.append(s.strip())

    for runner, v_scr in arqs_script:
        r, a, rep, f_ex, s = _rodar_script(runner, raiz, v_scr, ampliado=ampliado, prazo_s=prazo_s)
        rodados += r
        aprovados += a
        reprovados += rep
        fora_exige += f_ex
        if s.strip():
            saidas.append(s.strip())

    duracao = time.monotonic() - t0
    cod = 1 if reprovados > 0 else (3 if nao_medidos else 0)
    return ResultadoSelecao(
        componente=alvo_comp,
        ampliado=ampliado,
        arquivos=tuple(rels_selecionados),
        rodados=rodados,
        aprovados=aprovados,
        reprovados=reprovados,
        fora_exige=fora_exige,
        nao_medidos=tuple(nao_medidos),
        duracao_s=duracao,
        saida="\n".join(saidas),
        codigo_saida=cod,
    )


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite selecionar")
    p.add_argument("componente", help="chave ou slug do componente mexido")
    p.add_argument("--arvore", default=".", help="caminho da árvore do repositório")
    p.add_argument("--ampliado", action="store_true", help="inclui fronteira, regra e casos com exige")
    p.add_argument("--prazo", type=int, default=60, help="prazo máximo em segundos")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite o resultado em JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    res = selecionar(
        args.componente,
        arvore=args.arvore,
        ampliado=args.ampliado,
        prazo_s=args.prazo,
    )
    if args.como_json:
        sys.stdout.write(json.dumps(res.como_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(res.resumo_texto() + "\n")
        if res.reprovados > 0 and res.saida:
            sys.stderr.write(res.saida + "\n")
    return res.codigo_saida


if __name__ == "__main__":
    raise SystemExit(main())
