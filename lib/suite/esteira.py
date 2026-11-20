"""Esteira de testes: seleciona os casos do push, executa em ambiente isolado e aciona o coletor servido (#4297)."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from analise import Falha as FalhaUnidade
from analise.unidade import executar as executar_unidade_isolada

from suite import consulta as _consulta
from suite.admissao import DubleOlaria, OlariaIndisponivelErro, admitir
from suite.coletor import (
    PRAZO_QUARENTENA_DIAS,
    CasoSelecionado,
    ClienteBalde,
    DubleBalde,
    LinhaBalde,
    ResultadoBrutoCaso,
    VereditoRodada,
    caminho_veredito_repositorio,
    colocar_em_quarentena,
    estado_quarentena_caso,
    gravar_veredito,
    ler_veredito,
    listar_vereditos,
)
from suite.consulta import ARQUIVOS_DUBLE_ARVORE, inferir_classe_entidade
from suite.selecao import PASTAS_TESTE, descobrir_arquivos_teste
from suite.vinculo import CasoTeste, VinculoArquivo, ler_vinculo

LIB_RAIZ = Path(__file__).resolve().parents[1]
MAX_REPETICOES_ERRATICO = 2
_MIN_LEN_HASH = 7
_MIN_COLUNAS_DOCKER = 2
_SAIDA_NAO_MEDIDO = 3

ARQUIVOS_RAIO_TOTAL = frozenset(
    {
        "uv.lock",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        "requirements-teste.txt",
        "pytest.ini",
        "conftest.py",
        "setup.cfg",
        "tox.ini",
    }
)

_SCRIPT_RUNNER_ISOLADO = """\
import json
import os
import subprocess
import sys
from pathlib import Path

def _limpar_ambiente():
    os.makedirs("/saida/tmp", exist_ok=True)
    os.makedirs("/saida/pytest_tmp", exist_ok=True)
    os.makedirs("/saida/pytest_cache", exist_ok=True)
    for k in list(os.environ):
        if k.startswith(("PF_", "OLARIA_", "CASA_PG_", "POSTGRES_")):
            os.environ.pop(k, None)
    os.environ["TMPDIR"] = "/saida/tmp"
    os.environ["TEMP"] = "/saida/tmp"
    os.environ["TMP"] = "/saida/tmp"
    os.environ["HOME"] = "/saida/tmp"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

def _montar_pythonpath(raiz: Path, casos_py: list[str]) -> str:
    caminhos = [str(raiz)]
    lib_dir = raiz / "lib"
    if lib_dir.is_dir():
        caminhos.append(str(lib_dir))
    for id_caso in casos_py:
        rel_arq = id_caso.split("::", 1)[0]
        pasta = (raiz / rel_arq).parent
        if pasta.is_dir():
            caminhos.append(str(pasta))
            if pasta.name in ("testes", "tests", "provas") and pasta.parent.is_dir():
                caminhos.append(str(pasta.parent))
    if os.environ.get("PYTHONPATH"):
        caminhos.append(os.environ["PYTHONPATH"])
    return os.pathsep.join(dict.fromkeys(caminhos))

def _rodar_caso_py(raiz: Path, id_caso: str, py_path: str) -> dict:
    rel_caso = Path("/saida") / f"caso_{abs(hash(id_caso))}.json"
    rel_caso.unlink(missing_ok=True)
    worker = Path("/saida/_pytest_worker.py")
    env = dict(os.environ)
    env["PYTHONPATH"] = py_path
    env["ESTEIRA_CASO_REL"] = str(rel_caso)
    proc = subprocess.run(
        [
            sys.executable,
            str(worker),
            id_caso,
        ],
        cwd=str(raiz),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    saida = ((proc.stdout or "") + "\\n" + (proc.stderr or "")).strip()
    if rel_caso.is_file():
        try:
            dados = json.loads(rel_caso.read_text(encoding="utf-8"))
            if isinstance(dados, dict) and "aprovado" in dados:
                return {
                    "aprovado": bool(dados["aprovado"]) and proc.returncode == 0,
                    "saida": str(dados.get("saida") or saida)[-2000:],
                }
        except Exception:
            pass
    return {
        "aprovado": proc.returncode == 0,
        "saida": saida[-2000:],
    }

def _rodar_caso_script(raiz: Path, runner: str, id_caso: str) -> dict:
    rel_arq = id_caso.split("::", 1)[0]
    proc = subprocess.run(
        [runner, str(raiz / rel_arq)],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    saida = ((proc.stdout or "") + "\\n" + (proc.stderr or "")).strip()
    return {
        "aprovado": proc.returncode == 0,
        "saida": saida[-2000:],
    }

def main() -> int:
    _limpar_ambiente()
    arq_pedido = Path(sys.argv[1])
    arq_saida = Path(sys.argv[2])
    pedido = json.loads(arq_pedido.read_text(encoding="utf-8"))
    casos = list(pedido.get("casos") or [])
    raiz = Path("/receita")

    casos_py = [c for c in casos if c.split("::", 1)[0].endswith(".py")]
    py_path = _montar_pythonpath(raiz, casos_py)

    resultados = {}
    for id_caso in casos:
        rel_arq = id_caso.split("::", 1)[0]
        if rel_arq.endswith(".py"):
            resultados[id_caso] = _rodar_caso_py(raiz, id_caso, py_path)
        elif rel_arq.endswith(".sh"):
            resultados[id_caso] = _rodar_caso_script(raiz, "bash", id_caso)
        elif rel_arq.endswith((".mjs", ".js")):
            resultados[id_caso] = _rodar_caso_script(raiz, "node", id_caso)
        else:
            resultados[id_caso] = {"aprovado": False, "saida": f"extensão não suportada: {rel_arq}"}

    arq_saida.write_text(json.dumps({"casos": resultados}, ensure_ascii=False), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""

_SCRIPT_PYTEST_WORKER = """\
import json
import os
import sys
from pathlib import Path
import pytest

class _PluginCaso:
    def __init__(self) -> None:
        self.chamado = False
        self.pulado = False
        self.aprovado = True
        self.mensagens: list[str] = []

    def pytest_configure(self, config):
        config.addinivalue_line(
            "markers",
            "exige(chave): caso que exige uma entidade de ambiente.",
        )
        config.addinivalue_line(
            "markers",
            "incidente(numero): caso que reproduz um incidente fechado.",
        )

    def pytest_runtest_logreport(self, report):
        if report.skipped and not getattr(report, "wasxfail", None):
            self.pulado = True
            self.mensagens.append("pulado: " + str(report.longrepr))
            return
        if report.when == "call":
            self.chamado = True
            if report.failed:
                self.aprovado = False
                self.mensagens.append(str(report.longrepr))
        elif report.when in ("setup", "teardown") and report.failed:
            self.chamado = True
            self.aprovado = False
            self.mensagens.append(str(report.longrepr))

def main() -> int:
    alvo = sys.argv[1]
    rel = os.environ.get("ESTEIRA_CASO_REL")
    if "::" in alvo:
        arq, nome = alvo.split("::", 1)
        if nome == "<arquivo>":
            alvo = arq
    plugin = _PluginCaso()
    cod = pytest.main(
        [
            "-p",
            "no:cacheprovider",
            "--basetemp=/saida/pytest_tmp",
            "-q",
            alvo,
        ],
        plugins=[plugin],
    )
    # o caso pulado de propósito (marca skip no código) não reprova: roda, e diz que pulou
    ok = (cod == 0) and (plugin.chamado or plugin.pulado) and plugin.aprovado
    if rel:
        Path(rel).write_text(
            json.dumps({"aprovado": ok, "saida": "\\n".join(plugin.mensagens)}, ensure_ascii=False),
            encoding="utf-8",
        )
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
"""


@dataclass(frozen=True)
class PlanoSelecaoRodada:
    repositorio: str
    arvore: Path
    arvore_mudanca: str
    arvore_main: str
    arquivos_mudados: tuple[str, ...]
    alcanca_todos: bool
    componentes_alcancados: tuple[str, ...]
    entidades_mudadas: tuple[str, ...]
    casos: tuple[CasoSelecionado, ...]
    sem_testes_declarados: bool
    componentes_sem_verificacao: tuple[str, ...]


def carregar_coletor_servido() -> Any:
    """Carrega sempre o módulo `coletor` da release servida, nunca o da árvore testada."""
    env_coletor = os.environ.get("PF_ESTEIRA_COLETOR_SERVIDO")
    candidatos: list[Path] = []
    if env_coletor:
        candidatos.append(Path(env_coletor))
    release_raiz = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    candidatos.append(release_raiz / "harness" / "lib" / "suite" / "coletor.py")

    for cand in candidatos:
        if cand.is_file():
            spec = importlib.util.spec_from_file_location("_suite_coletor_servido", str(cand.resolve()))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
                return mod

    import suite.coletor as coletor_padrao

    return coletor_padrao


def _carregar_duble_olaria_de_caminho(cand: Path) -> DubleOlaria | None:
    try:
        texto = cand.read_text(encoding="utf-8")
    except OSError:
        raise FileNotFoundError(cand) from None
    dados = yaml.safe_load(texto) if cand.suffix.lower() in (".yaml", ".yml") else json.loads(texto)
    if not isinstance(dados, dict):
        return DubleOlaria()
    if dados.get("fora_do_ar"):
        return DubleOlaria(fora_do_ar=True)
    mapa_fichas: dict[str, str] = {}
    for item in dados.get("fichas") or []:
        if isinstance(item, dict) and item.get("chave"):
            ch = str(item["chave"])
            cls = str(item.get("classe") or inferir_classe_entidade(ch))
            mapa_fichas[ch] = cls
        elif isinstance(item, str):
            mapa_fichas[item] = inferir_classe_entidade(item)
    return DubleOlaria(fichas=mapa_fichas)


def _resolver_ensaiador_admissao(raiz: Path, ensaiador: Any = None) -> Any:
    if ensaiador is not None:
        return ensaiador
    arq_env = os.environ.get("PF_SUITE_OLARIA_ARQUIVO")
    caminhos = [Path(arq_env)] if arq_env else [raiz / n for n in ARQUIVOS_DUBLE_ARVORE]
    for cand in caminhos:
        try:
            return _carregar_duble_olaria_de_caminho(cand)
        except (FileNotFoundError, ValueError):
            continue
    return None


def _hash_arvore_diretorio(raiz: Path) -> str:
    h = hashlib.sha1()
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = sorted(d for d in dirnames if d not in (".git", "__pycache__", ".pytest_cache"))
        pasta = Path(dirpath)
        for fn in sorted(filenames):
            if fn.endswith((".pyc", ".pyo")):
                continue
            arq = pasta / fn
            try:
                rel = arq.relative_to(raiz).as_posix()
                conteudo = arq.read_bytes()
            except OSError:
                continue
            h.update(rel.encode("utf-8") + b"\0" + conteudo + b"\0")
    return h.hexdigest()


def _git_out(raiz: Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(raiz), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip()


def _todos_arquivos_arvore(raiz: Path) -> list[str]:
    if (raiz / ".git").exists():
        saida = _git_out(raiz, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        if saida is not None:
            return sorted({p.strip().lstrip("./") for p in saida.split("\0") if p.strip()})
    achados: list[str] = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "__pycache__")
        pasta = Path(dirpath)
        for fn in sorted(filenames):
            if fn.startswith(".") or fn.endswith((".pyc", ".pyo")):
                continue
            arq = pasta / fn
            achados.append(arq.relative_to(raiz).as_posix())
    return sorted(achados)


def _inferir_rev_base_git(raiz: Path, rev_mud: str, base: str | None) -> str | None:
    if base is not None:
        return base
    head_sha = _git_out(raiz, "rev-parse", rev_mud)
    for cand in ("origin/main", "main"):
        cand_sha = _git_out(raiz, "rev-parse", "--verify", "-q", cand)
        if cand_sha and cand_sha != head_sha:
            return cand
    n_commits = _git_out(raiz, "rev-list", "--count", rev_mud)
    if n_commits and n_commits.isdigit() and int(n_commits) > 1:
        return f"{rev_mud}~1"
    return None


def _resolver_arvore_main(raiz: Path, *, eh_git: bool, base: str | None, rev_base: str | None, arvore_mud: str) -> str:
    if eh_git:
        alvo_main = base or rev_base or "origin/main"
        achada = (
            _git_out(raiz, "rev-parse", "--verify", "-q", f"{alvo_main}^{{tree}}")
            or _git_out(raiz, "rev-parse", "--verify", "-q", "origin/main^{tree}")
            or _git_out(raiz, "rev-parse", "--verify", "-q", "main^{tree}")
        )
        if achada:
            return achada
    if base and len(base) >= _MIN_LEN_HASH:
        return base
    return arvore_mud


def _resolver_revisoes_e_diff(
    raiz: Path,
    *,
    mudanca: str | None = None,
    base: str | None = None,
    arquivos_mudados: Iterable[str] | None = None,
) -> tuple[str, str, list[str]]:
    eh_git = (raiz / ".git").exists()
    rev_mud = mudanca or "HEAD"
    arvore_mud = (_git_out(raiz, "rev-parse", f"{rev_mud}^{{tree}}") if eh_git else None) or (
        mudanca if mudanca and len(mudanca) >= _MIN_LEN_HASH else _hash_arvore_diretorio(raiz)
    )
    rev_base = _inferir_rev_base_git(raiz, rev_mud, base) if eh_git else base
    arvore_main = _resolver_arvore_main(raiz, eh_git=eh_git, base=base, rev_base=rev_base, arvore_mud=arvore_mud)

    if arquivos_mudados is not None:
        lista_mud = sorted({str(p).strip().lstrip("./") for p in arquivos_mudados if str(p).strip()})
        return arvore_mud, arvore_main, lista_mud

    arq_diff_json = raiz / ".diff.json"
    try:
        dados_diff = json.loads(arq_diff_json.read_text(encoding="utf-8"))
    except OSError:
        dados_diff = None
    if isinstance(dados_diff, dict) and isinstance(dados_diff.get("arquivos_mudados"), list):
        lista_json = sorted({str(p).strip().lstrip("./") for p in dados_diff["arquivos_mudados"] if str(p).strip()})
        return arvore_mud, arvore_main, lista_json

    if eh_git and rev_base:
        diff_z = _git_out(raiz, "diff", "-z", "--name-only", rev_base, rev_mud)
        if diff_z is not None:
            outros_z = _git_out(raiz, "ls-files", "-z", "--others", "--exclude-standard") or ""
            brutos = diff_z.split("\0") + outros_z.split("\0")
            lista = sorted({p.strip().lstrip("./") for p in brutos if p.strip()})
            if lista:
                return arvore_mud, arvore_main, lista

    return arvore_mud, arvore_main, _todos_arquivos_arvore(raiz)


_como_lista_str = _consulta._como_lista_str
_resolver_leitor_ontologia = _consulta._resolver_leitor


def _caminhos_de_ficha_componente(ficha: Mapping[str, Any]) -> list[str]:
    dados = ficha.get("dados") if isinstance(ficha.get("dados"), Mapping) else {}
    brutos = _como_lista_str(dados.get("caminho") if isinstance(dados, Mapping) else None)
    prefixos: list[str] = []
    for c in brutos:
        limpo = c.strip("/")
        if not limpo:
            continue
        prefixos.append(limpo)
    return list(dict.fromkeys(prefixos))


def _stack_de_ficha_componente(ficha: Mapping[str, Any] | None) -> str:
    if not isinstance(ficha, Mapping):
        return "harness"
    ligs = ficha.get("ligacoes")
    if not isinstance(ligs, Mapping):
        return "harness"
    for a in _como_lista_str(ligs.get("componente-de")):
        if a.startswith("stack:"):
            return a.removeprefix("stack:")
        if ":" in a:
            return a.split(":", 1)[0]
    return "harness"


def _servicos_de_ficha_componente(ficha: Mapping[str, Any] | None, servicos_conhecidos: Iterable[str]) -> list[str]:
    if not isinstance(ficha, Mapping):
        return []
    ligs = ficha.get("ligacoes")
    if not isinstance(ligs, Mapping):
        return []
    afetados: list[str] = []
    for a in _como_lista_str(ligs.get("componente-de")):
        if a.startswith("stack:"):
            stack_slug = a.removeprefix("stack:")
            afetados.extend(srv for srv in servicos_conhecidos if srv.startswith(f"{stack_slug}:"))
        elif ":" in a:
            afetados.append(a)
    return list(dict.fromkeys(afetados))


def _arquivo_sob_prefixo(arquivo: str, prefixo: str) -> bool:
    arq = arquivo.strip("/")
    pref = prefixo.strip("/")
    return arq == pref or arq.startswith(f"{pref}/")


def _inferir_prefixo_de_vinculo(raiz: Path, v: VinculoArquivo) -> str:
    if not v.caminho.is_relative_to(raiz):
        return ""
    rel_parent = v.caminho.relative_to(raiz).parent
    if rel_parent.name in PASTAS_TESTE:
        rel_parent = rel_parent.parent
    pos = rel_parent.as_posix()
    return "" if pos in ("", ".") else pos


def _ler_fichas_seguro(leitor: Any, classe: str) -> list[dict[str, Any]]:
    acumuladas: list[dict[str, Any]] = []
    try:
        acumuladas.extend(leitor.ler_fichas(classe))
    except OlariaIndisponivelErro:
        pass
    return acumuladas


def _indexar_componentes(
    raiz: Path,
    fichas_comp: Sequence[Mapping[str, Any]],
    vinculos_validos: Sequence[tuple[str, VinculoArquivo]],
) -> tuple[dict[str, list[str]], dict[str, Mapping[str, Any]], dict[str, str]]:
    prefixos_por_comp: dict[str, list[str]] = {}
    ficha_por_comp: dict[str, Mapping[str, Any]] = {}
    stack_por_comp: dict[str, str] = {}

    for f in fichas_comp:
        ch = str(f.get("chave") or "")
        if not ch:
            continue
        ficha_por_comp[ch] = f
        stack_por_comp[ch] = _stack_de_ficha_componente(f)
        prefs = _caminhos_de_ficha_componente(f)
        if prefs:
            prefixos_por_comp[ch] = prefs

    for _, v in vinculos_validos:
        comp = v.componente
        if not comp:
            continue
        stack_por_comp.setdefault(comp, "harness")
        if not prefixos_por_comp.get(comp):
            pref_inf = _inferir_prefixo_de_vinculo(raiz, v)
            if pref_inf:
                prefixos_por_comp.setdefault(comp, []).append(pref_inf)

    return prefixos_por_comp, ficha_por_comp, stack_por_comp


def _mapear_alcance_diff(
    raiz: Path,
    arquivos_mudados: Sequence[str],
    vinculos_validos: Sequence[tuple[str, VinculoArquivo]],
    leitor: Any,
) -> tuple[bool, set[str], set[str], dict[str, str]]:
    alcanca_todos = any(Path(arq).name in ARQUIVOS_RAIO_TOTAL for arq in arquivos_mudados)
    fichas_comp = _ler_fichas_seguro(leitor, "componente")
    fichas_srv = _ler_fichas_seguro(leitor, "servico")

    servicos_conhecidos = {str(f.get("chave")) for f in fichas_srv if isinstance(f, Mapping) and f.get("chave")}
    for _, v in vinculos_validos:
        servicos_conhecidos.update(ex for ex in v.exige if inferir_classe_entidade(ex, papel="exige") == "servico")

    prefixos_por_comp, ficha_por_comp, stack_por_comp = _indexar_componentes(
        raiz,
        fichas_comp,
        vinculos_validos,
    )

    componentes_alcancados = {
        comp
        for arq in arquivos_mudados
        for comp, prefs in prefixos_por_comp.items()
        if any(_arquivo_sob_prefixo(arq, p) for p in prefs)
    }

    entidades_mudadas: set[str] = set()
    if alcanca_todos:
        for _, v in vinculos_validos:
            entidades_mudadas.update(v.exige)
        entidades_mudadas.update(servicos_conhecidos)
    else:
        for comp in componentes_alcancados:
            entidades_mudadas.update(_servicos_de_ficha_componente(ficha_por_comp.get(comp), servicos_conhecidos))

    return alcanca_todos, componentes_alcancados, entidades_mudadas, stack_por_comp


def _deve_rodar_caso_na_esteira(
    v: VinculoArquivo,
    caso: CasoTeste,
    *,
    no_alcance: bool,
    entidades_mudadas: set[str],
) -> bool:
    if caso.incidentes:
        return True
    if caso.exige:
        return no_alcance or any(ex in entidades_mudadas for ex in caso.exige)
    if v.classe in ("teste-de-fronteira", "teste-de-regra"):
        return True
    return no_alcance


def selecionar_casos_rodada(arvore: str | Path, **opcoes: Any) -> PlanoSelecaoRodada:
    raiz = Path(arvore).resolve()
    repositorio = str(opcoes.get("repositorio") or "platafirma-casa-espelho")
    leitor_res = _resolver_leitor_ontologia(raiz, opcoes.get("leitor"))
    arvore_mud, arvore_main, lista_mud = _resolver_revisoes_e_diff(
        raiz,
        mudanca=opcoes.get("mudanca"),
        base=opcoes.get("base"),
        arquivos_mudados=opcoes.get("arquivos_mudados"),
    )
    set_mud = set(lista_mud)

    arquivos_teste = descobrir_arquivos_teste(raiz)
    vinculos_validos: list[tuple[str, VinculoArquivo]] = []
    for arq in arquivos_teste:
        rel = arq.relative_to(raiz).as_posix() if arq.is_relative_to(raiz) else arq.name
        v = ler_vinculo(arq)
        if v.componente is not None:
            vinculos_validos.append((rel, v))

    sem_testes = len(vinculos_validos) == 0
    alcanca_todos, comps_alcancados, ents_mudadas, stack_por_comp = _mapear_alcance_diff(
        raiz,
        lista_mud,
        vinculos_validos,
        leitor_res,
    )

    for rel, v in vinculos_validos:
        if rel in set_mud and v.componente:
            comps_alcancados.add(v.componente)

    comps_com_verificacao = {v.componente for _, v in vinculos_validos if v.componente and v.casos}
    comps_sem_verif = sorted(c for c in comps_alcancados if c not in comps_com_verificacao)

    casos_selecionados: list[CasoSelecionado] = []
    for rel, v in vinculos_validos:
        comp = v.componente or ""
        classe = v.classe or "teste-de-comportamento"
        no_alcance = alcanca_todos or (comp in comps_alcancados) or (rel in set_mud)
        stack = stack_por_comp.get(comp, "harness")
        casos_arq = v.casos or (
            CasoTeste(nome="<arquivo>", linha=1, exige=v.exige, incidentes=v.incidentes),
        )
        for c in casos_arq:
            if not _deve_rodar_caso_na_esteira(
                v,
                c,
                no_alcance=no_alcance,
                entidades_mudadas=ents_mudadas,
            ):
                continue
            casos_selecionados.append(
                CasoSelecionado(
                    id_caso=f"{rel}::{c.nome}",
                    arquivo=rel,
                    nome_caso=c.nome,
                    componente=comp,
                    classe=classe,
                    exige=c.exige,
                    incidentes=c.incidentes,
                    no_alcance=no_alcance,
                    stack=stack,
                )
            )

    return PlanoSelecaoRodada(
        repositorio=repositorio,
        arvore=raiz,
        arvore_mudanca=arvore_mud,
        arvore_main=arvore_main,
        arquivos_mudados=tuple(lista_mud),
        alcanca_todos=alcanca_todos,
        componentes_alcancados=tuple(sorted(comps_alcancados)),
        entidades_mudadas=tuple(sorted(ents_mudadas)),
        casos=tuple(casos_selecionados),
        sem_testes_declarados=sem_testes,
        componentes_sem_verificacao=tuple(comps_sem_verif),
    )


def _container_docker_ativo(slug: str, chave_hifen: str) -> bool:
    proc_docker = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.State}}\t{{.Status}}"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc_docker.returncode != 0:
        return False
    for linha in (proc_docker.stdout or "").splitlines():
        partes = linha.split("\t")
        if len(partes) < _MIN_COLUNAS_DOCKER:
            continue
        nome, estado = partes[0].strip(), partes[1].strip().lower()
        status = partes[_MIN_COLUNAS_DOCKER].strip().lower() if len(partes) > _MIN_COLUNAS_DOCKER else ""
        if estado != "running" or "unhealthy" in status:
            continue
        if nome in (slug, chave_hifen) or nome.startswith((f"{slug}-", f"{chave_hifen}-")):
            return True
    return False


def _unit_systemd_ativa(slug: str) -> bool:
    proc_unit = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", f"{slug}.service"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return proc_unit.returncode == 0


def _servico_ativo_no_host(chave: str) -> bool:
    slug = chave.split(":", 1)[-1].strip()
    chave_hifen = chave.replace(":", "-").strip()
    return _container_docker_ativo(slug, chave_hifen) or _unit_systemd_ativa(slug)


def _modelo_disponivel_no_host(chave: str) -> bool:
    slug = chave.split(":", 1)[-1].strip().lower()
    if not slug:
        return False
    instancia = Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    pastas_cache = [
        instancia / "cache" / "huggingface" / "hub",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    for pasta in pastas_cache:
        if not pasta.is_dir():
            continue
        try:
            for item in pasta.iterdir():
                if slug in item.name.lower():
                    return True
        except OSError:
            continue
    return False


def isolamento_disponivel_no_host() -> bool:
    if os.environ.get("PF_ESTEIRA_SEM_ISOLAMENTO") == "1":
        return False
    return bool(shutil.which("bwrap") and shutil.which("systemd-run"))


def entidade_disponivel_no_host(chave: str) -> bool:
    fora_env = {x.strip() for x in (os.environ.get("PF_ESTEIRA_ENTIDADES_FORA") or "").split(",") if x.strip()}
    if "*" in fora_env or chave in fora_env:
        return False
    ativas_env = {x.strip() for x in (os.environ.get("PF_ESTEIRA_ENTIDADES_ATIVAS") or "").split(",") if x.strip()}
    if "*" in ativas_env or chave in ativas_env:
        return True

    classe = inferir_classe_entidade(chave, papel="exige")
    if classe == "host":
        return chave == "host:casa" and isolamento_disponivel_no_host()
    if classe in ("modelo", "embedder"):
        return _modelo_disponivel_no_host(chave)
    return _servico_ativo_no_host(chave)


def conferir_entidades_exigidas(
    casos: Sequence[CasoSelecionado],
    *,
    sonda_entidade: Callable[[str], bool] | None = None,
) -> list[str]:
    verificar = sonda_entidade or entidade_disponivel_no_host
    exigidas: list[str] = []
    for c in casos:
        for ex in c.exige:
            if ex not in exigidas:
                exigidas.append(ex)
    return [ex for ex in exigidas if not verificar(ex)]


def _resolver_venv_pytest() -> Path:
    env_venv = os.environ.get("PF_ESTEIRA_VENV_PYTEST")
    if env_venv and (Path(env_venv) / "bin" / "python").exists():
        return Path(env_venv).resolve()
    release_raiz = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    cand_analise = release_raiz / "venv" / "analise"
    if (cand_analise / "bin" / "pytest").exists():
        return cand_analise.resolve()
    if importlib.util.find_spec("pytest") is not None:
        return Path(sys.prefix).resolve()
    venv_pool = Path(os.environ.get("PF_RELEASE_RAIZ", "/opt/platafirma")) / "venv"
    if venv_pool.is_dir():
        for p in sorted(venv_pool.glob("analise-*"), reverse=True):
            if (p / "bin" / "pytest").exists():
                return p.resolve()
    return Path(sys.prefix).resolve()


class DubleExecutorIsolado:
    """Dublê em processo do executor isolado para testes de comportamento rápidos na fita."""

    def __init__(
        self,
        roteiro: Mapping[str, bool | Sequence[bool]] | Callable[[Path, list[str]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.roteiro = roteiro
        self.chamadas: list[tuple[Path, list[str]]] = []
        self._contagem_por_caso: dict[str, int] = {}

    def __call__(self, arvore: Path, ids_casos: list[str]) -> dict[str, dict[str, Any]]:
        self.chamadas.append((arvore, list(ids_casos)))
        if callable(self.roteiro):
            bruto = self.roteiro(arvore, ids_casos)
            saida: dict[str, dict[str, Any]] = {}
            for k, v in bruto.items():
                if isinstance(v, bool):
                    saida[k] = {"aprovado": v, "saida": ""}
                elif isinstance(v, dict):
                    saida[k] = {"aprovado": bool(v.get("aprovado", False)), "saida": str(v.get("saida", ""))}
            return saida

        resultados: dict[str, dict[str, Any]] = {}
        mapa = self.roteiro or {}
        for id_caso in ids_casos:
            idx = self._contagem_por_caso.get(id_caso, 0)
            self._contagem_por_caso[id_caso] = idx + 1
            regra = mapa.get(id_caso, True)
            if isinstance(regra, bool):
                ok = regra
            elif isinstance(regra, Sequence):
                ok = bool(regra[min(idx, len(regra) - 1)]) if regra else True
            else:
                ok = bool(regra)
            resultados[id_caso] = {
                "aprovado": ok,
                "saida": "" if ok else f"falha simulada em {id_caso} (tentativa {idx + 1})",
            }
        return resultados


def _escrever_arquivo_atomico(destino: Path, conteudo: str) -> None:
    tmp = destino.with_suffix(destino.suffix + ".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    tmp.replace(destino)


def projeto_do_caso(raiz: Path, id_caso: str) -> Path | None:
    """O manifesto (pyproject.toml com uv.lock) do repositório onde mora o caso.

    Sobe da pasta do arquivo de teste até a raiz da árvore; em cada nível vale a pasta
    mesma ou `venvs/<nome da pasta>` (o harness guarda o manifesto em venvs/harness).
    """
    raiz_r = raiz.resolve()
    pasta = (raiz_r / id_caso.split("::", 1)[0]).parent
    while True:
        for cand in (pasta, pasta / "venvs" / pasta.name):
            if (cand / "pyproject.toml").is_file() and (cand / "uv.lock").is_file():
                return cand
        if pasta == raiz_r or raiz_r not in pasta.parents:
            return None
        pasta = pasta.parent


def venv_de_teste(projeto: Path) -> Path:
    """O venv de teste do projeto: dependências mais o grupo dev, do lock, sem rede no teste.

    Monta-se fora do isolamento, uma vez por lock, com o python do sistema (que o isolamento
    monta em /usr) e arquivos copiados para dentro do venv, que é a única pasta extra montada.
    Sem venv montado o caso não é medido: nunca cai para outro ambiente.
    """
    lock = projeto / "uv.lock"
    marca = hashlib.sha256(lock.read_bytes() + (projeto / "pyproject.toml").read_bytes()).hexdigest()[:16]
    base = Path(os.environ.get("PF_ESTEIRA_VENVS") or (Path.home() / ".cache" / "platafirma" / "esteira-venvs"))
    destino = base / f"{projeto.name}-{marca}"
    if (destino / "bin" / "pytest").exists():
        return destino
    base.mkdir(parents=True, exist_ok=True)
    tmp = base / f".{destino.name}.{uuid.uuid4().hex[:8]}"
    env = dict(os.environ)
    env.update(
        {
            "UV_PROJECT_ENVIRONMENT": str(tmp),
            "UV_PYTHON_PREFERENCE": "only-system",
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_LINK_MODE": "copy",
        }
    )
    env.pop("VIRTUAL_ENV", None)
    uv_bin = shutil.which("uv") or "/usr/local/bin/uv"
    proc = subprocess.run(
        [uv_bin, "sync", "--frozen", "--group", "dev", "--no-install-project", "--project", str(projeto)],
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode != 0 or not (tmp / "bin" / "pytest").exists():
        shutil.rmtree(tmp, ignore_errors=True)
        causa = ((proc.stderr or proc.stdout or "").strip().splitlines() or ["sem pytest no grupo dev"])[-1]
        raise FalhaUnidade(_SAIDA_NAO_MEDIDO, f"venv-de-teste:{projeto.name}: {causa[:300]}")
    try:
        os.replace(tmp, destino)
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True)
    return destino


RELEASE_PADRAO = Path("/opt/platafirma/current")
FONTES_RELEASE_RO = ("casa-espelho", "harness")


def _montagens_release_ro() -> list[tuple[Path, str]]:
    """Monta em leitura as fontes servidas da casa e do harness no caminho canônico da release (DT 935)."""
    raiz_host = Path((os.environ.get("PLATAFIRMA_RELEASE") or "").strip() or str(RELEASE_PADRAO))
    montagens: list[tuple[Path, str]] = []
    for nome in FONTES_RELEASE_RO:
        cand = raiz_host / nome
        if cand.is_dir():
            montagens.append((cand.resolve(), str(RELEASE_PADRAO / nome)))
    return montagens


class ExecutorIsoladoUnidade:
    """Executor isolado real: roda os casos em `systemd-run` com rede privada e `bwrap`."""

    def __init__(self, prazo_s: float = 180.0, venv_pytest: Path | None = None) -> None:
        self.prazo_s = prazo_s
        self.venv_pytest = venv_pytest

    def __call__(self, arvore: Path, ids_casos: list[str]) -> dict[str, dict[str, Any]]:
        if not ids_casos:
            return {}
        if self.venv_pytest is not None:
            return self._rodar_lote(arvore, ids_casos, self.venv_pytest)
        por_projeto: dict[Path | None, list[str]] = {}
        for id_caso in ids_casos:
            por_projeto.setdefault(projeto_do_caso(arvore, id_caso), []).append(id_caso)
        resultados: dict[str, dict[str, Any]] = {}
        for projeto, ids in por_projeto.items():
            venv = venv_de_teste(projeto) if projeto is not None else _resolver_venv_pytest()
            resultados.update(self._rodar_lote(arvore, ids, venv))
        return resultados

    def _rodar_lote(self, arvore: Path, ids_casos: list[str], venv_base: Path) -> dict[str, dict[str, Any]]:
        venv = Path(venv_base).resolve()
        py_bin = venv / "bin" / "python"
        if not py_bin.exists():
            py_bin = Path(sys.executable).resolve()

        with tempfile.TemporaryDirectory(prefix="esteira-isolada-") as tmp_dir:
            saida_dir = Path(tmp_dir)
            token = uuid.uuid4().hex
            _escrever_arquivo_atomico(saida_dir / "_runner.py", _SCRIPT_RUNNER_ISOLADO)
            _escrever_arquivo_atomico(saida_dir / "_pytest_worker.py", _SCRIPT_PYTEST_WORKER)
            _escrever_arquivo_atomico(
                saida_dir / "pedido.json",
                json.dumps({"casos": list(ids_casos)}, ensure_ascii=False),
            )
            nome_res = f"res-{token}.json"
            comando = [
                str(py_bin),
                "/saida/_runner.py",
                "/saida/pedido.json",
                f"/saida/{nome_res}",
            ]
            status, _ = executar_unidade_isolada(
                comando,
                pasta=arvore.resolve(),
                entrada=None,
                saida=saida_dir,
                ambiente=venv,
                montagens_ro=_montagens_release_ro(),
                rede=False,
                prazo=self.prazo_s,
            )
            arq_res = saida_dir / nome_res
            if status != 0 or not arq_res.is_file():
                return {
                    c: {"aprovado": False, "saida": f"execução isolada terminou com status {status}"}
                    for c in ids_casos
                }
            try:
                dados = json.loads(arq_res.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {c: {"aprovado": False, "saida": "resultado isolado ilegível"} for c in ids_casos}

            mapa_casos = dados.get("casos") if isinstance(dados, dict) else {}
            if not isinstance(mapa_casos, dict):
                mapa_casos = {}

            saida_final: dict[str, dict[str, Any]] = {}
            for c in ids_casos:
                item = mapa_casos.get(c)
                if isinstance(item, dict):
                    saida_final[c] = {
                        "aprovado": bool(item.get("aprovado", False)),
                        "saida": str(item.get("saida") or ""),
                    }
                else:
                    saida_final[c] = {"aprovado": False, "saida": "caso sem saída no lote isolado"}
            return saida_final


def _executar_com_repeticao_erratico(
    arvore: Path,
    casos: Sequence[CasoSelecionado],
    executor: Callable[[Path, list[str]], Mapping[str, Any]],
    abertas_balde: Sequence[LinhaBalde],
    **opcoes: Any,
) -> dict[str, ResultadoBrutoCaso]:
    max_repeticoes = int(opcoes.get("max_repeticoes", MAX_REPETICOES_ERRATICO))
    prazo_quarentena_dias = int(opcoes.get("prazo_quarentena_dias", PRAZO_QUARENTENA_DIAS))
    ids = [c.id_caso for c in casos]
    if not ids:
        return {}

    primeira_rodada = executor(arvore, ids)
    resultados: dict[str, ResultadoBrutoCaso] = {}

    for caso in casos:
        item = primeira_rodada.get(caso.id_caso)
        if isinstance(item, dict):
            aprovado = bool(item.get("aprovado", False))
            saida = str(item.get("saida") or "")
        else:
            aprovado = bool(item)
            saida = ""

        if aprovado:
            resultados[caso.id_caso] = ResultadoBrutoCaso(
                id_caso=caso.id_caso,
                aprovado=True,
                tentativas=1,
                passou_em_repeticao=False,
                saida=saida,
            )
            continue

        est_q = estado_quarentena_caso(caso.id_caso, abertas_balde, prazo_dias=prazo_quarentena_dias)
        if caso.fora_do_alcance_incidente or est_q in ("ativa", "vencida") or max_repeticoes <= 0:
            resultados[caso.id_caso] = ResultadoBrutoCaso(
                id_caso=caso.id_caso,
                aprovado=False,
                tentativas=1,
                passou_em_repeticao=False,
                saida=saida,
            )
            continue

        tentativas = 1
        passou_rep = False
        for _ in range(max_repeticoes):
            tentativas += 1
            rep = executor(arvore, [caso.id_caso])
            item_rep = rep.get(caso.id_caso)
            ok_rep = bool(item_rep.get("aprovado", False)) if isinstance(item_rep, dict) else bool(item_rep)
            if ok_rep:
                passou_rep = True
                break

        resultados[caso.id_caso] = ResultadoBrutoCaso(
            id_caso=caso.id_caso,
            aprovado=False,
            tentativas=tentativas,
            passou_em_repeticao=passou_rep,
            saida=saida,
        )

    return resultados


def _ler_raiz_bancada() -> Path | None:
    val = os.environ.get("PLATAFIRMA_BANCADA", "").strip()
    if val:
        return Path(val)
    arq = Path(os.environ.get("PLATAFIRMA_ARQUIVO_BANCADA", str(Path.home() / ".config" / "platafirma" / "bancada")))
    linhas: list[str] = []
    try:
        linhas.extend(arq.read_text(encoding="utf-8").splitlines())
    except OSError:
        pass
    if linhas and linhas[0].strip():
        return Path(linhas[0].strip())
    return None


def _deduzir_repositorio_de_caminho(arvore: Path) -> str:
    bancada = _ler_raiz_bancada()
    if bancada:
        for base_dir in (bancada / "wt", bancada):
            if arvore.is_relative_to(base_dir):
                partes = arvore.relative_to(base_dir).parts
                if partes:
                    return partes[0]
    return arvore.name


def _resolver_worktree_na_bancada(bancada: Path, repo_nome: str, chave: str) -> Path | None:
    cadeira = os.environ.get("PF_CADEIRA", "").removeprefix("claudinho-").removeprefix("claudinha-")
    if cadeira:
        if chave and (bancada / "wt" / repo_nome / cadeira / chave).is_dir():
            return (bancada / "wt" / repo_nome / cadeira / chave).resolve()
        wt_main = bancada / "wt" / repo_nome / cadeira / "main"
        if wt_main.is_dir():
            return wt_main.resolve()
        pasta_cad = bancada / "wt" / repo_nome / cadeira
        if pasta_cad.is_dir():
            subpastas = sorted(p for p in pasta_cad.iterdir() if p.is_dir() and (p / ".git").exists())
            if len(subpastas) == 1:
                return subpastas[0].resolve()
    clone_base = bancada / repo_nome
    if clone_base.is_dir():
        return clone_base.resolve()
    return None


def resolver_alvo_arvore(alvo: str | Path | None, arvore_arg: str | Path | None = None) -> tuple[str, Path]:
    if arvore_arg:
        arvore_res = Path(arvore_arg).resolve()
        repo = (
            str(alvo).split("@", 1)[0]
            if alvo and not Path(str(alvo)).exists()
            else _deduzir_repositorio_de_caminho(arvore_res)
        )
        return repo, arvore_res

    if alvo is None:
        arvore_res = Path.cwd().resolve()
        return _deduzir_repositorio_de_caminho(arvore_res), arvore_res

    alvo_str = str(alvo).strip()
    cand_direto = Path(alvo_str)
    if cand_direto.exists():
        arvore_res = cand_direto.resolve()
        return _deduzir_repositorio_de_caminho(arvore_res), arvore_res

    pwd_env = os.environ.get("PWD")
    if pwd_env and not cand_direto.is_absolute() and (Path(pwd_env) / cand_direto).exists():
        arvore_res = (Path(pwd_env) / cand_direto).resolve()
        return _deduzir_repositorio_de_caminho(arvore_res), arvore_res

    repo_nome, _, chave = alvo_str.partition("@")
    bancada = _ler_raiz_bancada()
    if bancada is not None:
        achada = _resolver_worktree_na_bancada(bancada, repo_nome, chave)
        if achada is not None:
            return repo_nome, achada

    return repo_nome, cand_direto.resolve()


def rodar(alvo: str | Path | None = None, **opcoes: Any) -> VereditoRodada:
    """Executa a rodada completa da esteira e grava o veredito pelo coletor servido."""
    repositorio, raiz = resolver_alvo_arvore(alvo, opcoes.get("arvore"))
    coletor_mod = carregar_coletor_servido()

    plano = selecionar_casos_rodada(
        raiz,
        repositorio=repositorio,
        mudanca=opcoes.get("mudanca"),
        base=opcoes.get("base"),
        arquivos_mudados=opcoes.get("arquivos_mudados"),
        leitor=opcoes.get("leitor"),
    )

    ensaiador_res = _resolver_ensaiador_admissao(raiz, opcoes.get("ensaiador"))
    res_admissao = admitir(
        raiz,
        ensaiador=ensaiador_res,
        arquivos_mudados=plano.arquivos_mudados,
    )

    executor_isolado = opcoes.get("executor_isolado")
    entidades_fora = conferir_entidades_exigidas(plano.casos, sonda_entidade=opcoes.get("sonda_entidade"))
    if (
        executor_isolado is None
        and not isolamento_disponivel_no_host()
        and "host:isolamento" not in entidades_fora
    ):
        entidades_fora.append("host:isolamento")

    nao_pode_rodar = (
        plano.sem_testes_declarados
        or bool(plano.componentes_sem_verificacao)
        or bool(entidades_fora)
        or res_admissao.codigo_saida in (1, _SAIDA_NAO_MEDIDO)
    )

    balde = opcoes.get("balde")
    prazo_quarentena_dias = int(opcoes.get("prazo_quarentena_dias", PRAZO_QUARENTENA_DIAS))
    max_repeticoes_erratico = int(opcoes.get("max_repeticoes_erratico", MAX_REPETICOES_ERRATICO))

    resultados_brutos: dict[str, ResultadoBrutoCaso] = {}
    if not nao_pode_rodar and plano.casos:
        cliente_balde = coletor_mod.resolver_balde(balde)
        abertas = cliente_balde.listar_abertas()
        exec_fn = executor_isolado or ExecutorIsoladoUnidade()
        try:
            resultados_brutos = _executar_com_repeticao_erratico(
                raiz,
                plano.casos,
                exec_fn,
                abertas,
                max_repeticoes=max_repeticoes_erratico,
                prazo_quarentena_dias=prazo_quarentena_dias,
            )
        except FalhaUnidade as exc:
            # analise.Falha guarda o código em `exit`; sem ler o campo certo, o isolamento ausente
            # (exit 3) reprovava todo caso em vez de deixar o veredito não medido
            if int(getattr(exc, "exit", getattr(exc, "saida", 5))) == _SAIDA_NAO_MEDIDO:
                entidades_fora.append(str(exc))
            else:
                for c in plano.casos:
                    resultados_brutos[c.id_caso] = ResultadoBrutoCaso(
                        id_caso=c.id_caso,
                        aprovado=False,
                        tentativas=1,
                        passou_em_repeticao=False,
                        saida=f"falha na unidade isolada: {exc}",
                    )

    diagnostico = opcoes.get("diagnostico")
    if isinstance(diagnostico, dict):
        diagnostico.update({k: r.saida for k, r in resultados_brutos.items() if not r.aprovado})

    return coletor_mod.julgar_e_gravar(
        repositorio=repositorio,
        arvore_mudanca=plano.arvore_mudanca,
        arvore_main=plano.arvore_main,
        admissao=res_admissao,
        casos_selecionados=plano.casos,
        resultados_brutos=resultados_brutos,
        sem_testes_declarados=plano.sem_testes_declarados,
        componentes_sem_verificacao=plano.componentes_sem_verificacao,
        entidades_indisponiveis=entidades_fora,
        balde=balde,
        pasta_vereditos=opcoes.get("pasta_vereditos"),
        prazo_quarentena_dias=prazo_quarentena_dias,
        hora=opcoes.get("hora"),
        data_medida=opcoes.get("data_medida"),
    )


def _parser_rodar() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite rodar")
    p.add_argument("alvo", nargs="?", default=None, help="repositório ou caminho da árvore")
    p.add_argument("--arvore", default=None, help="caminho da árvore do repositório")
    p.add_argument("--mudanca", default=None, help="revisão ou árvore da mudança")
    p.add_argument("--base", default=None, help="revisão ou árvore da ponta da main")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite o veredito em JSON")
    return p


def _parser_veredito() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite veredito")
    p.add_argument("alvo", nargs="?", default=None, help="repositório ou caminho da árvore")
    p.add_argument("--arvore", default=None, help="caminho da árvore do repositório")
    p.add_argument("--mudanca", default=None, help="revisão ou hash da árvore da mudança")
    p.add_argument("--base", default=None, help="revisão ou hash da árvore da ponta da main")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite o veredito em JSON")
    return p


def main_rodar(argv: list[str] | None = None) -> int:
    try:
        args = _parser_rodar().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    diagnostico: dict[str, str] = {}
    veredito = rodar(
        args.alvo,
        arvore=args.arvore,
        mudanca=args.mudanca,
        base=args.base,
        diagnostico=diagnostico,
    )
    if args.como_json:
        sys.stdout.write(json.dumps(veredito.como_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        texto = veredito.resumo_texto() + "\n"
        sys.stdout.write(texto)
        if veredito.codigo_saida != 0:
            sys.stderr.write(texto)
    sys.stderr.write(texto_do_diagnostico(diagnostico))
    return veredito.codigo_saida


def texto_do_diagnostico(diagnostico: Mapping[str, str], *, por_caso: int = 800, teto: int = 20) -> str:
    """A saída de cada caso reprovado, para quem lê a rodada saber por que ele caiu."""
    if not diagnostico:
        return ""
    ids = sorted(diagnostico)
    linhas = [f"saída dos reprovados ({len(ids)}):"]
    for id_caso in ids[:teto]:
        saida = (diagnostico[id_caso] or "(sem saída)").strip()
        linhas.append(f"--- {id_caso}")
        linhas.append(saida[-por_caso:])
    if len(ids) > teto:
        linhas.append(f"(+{len(ids) - teto} reprovados sem a saída aqui)")
    return "\n".join(linhas) + "\n"


def main_veredito(argv: list[str] | None = None) -> int:
    try:
        args = _parser_veredito().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    repositorio, raiz = resolver_alvo_arvore(args.alvo, args.arvore)
    eh_git = (raiz / ".git").exists()
    arv_mud: str | None = None
    arv_main: str | None = None
    if args.mudanca:
        arv_mud = (_git_out(raiz, "rev-parse", f"{args.mudanca}^{{tree}}") if eh_git else None) or args.mudanca
    if args.base:
        arv_main = (_git_out(raiz, "rev-parse", f"{args.base}^{{tree}}") if eh_git else None) or args.base

    coletor_mod = carregar_coletor_servido()
    reg = coletor_mod.ler_veredito(repositorio, arvore_mudanca=arv_mud, arvore_main=arv_main)
    if reg is None:
        msg = f"veredito {repositorio}: sem rodada gravada\n"
        if args.como_json:
            sys.stdout.write(json.dumps({"repositorio": repositorio, "estado": "sem-rodada"}, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(msg)
            sys.stderr.write(msg)
        return 1

    estado = str(reg.get("estado") or "nao-medido")
    if args.como_json:
        sys.stdout.write(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    else:
        mud_c = str(reg.get("arvore_mudanca") or "?")[:12]
        main_c = str(reg.get("arvore_main") or "?")[:12]
        sys.stdout.write(f"veredito {repositorio} (mudanca={mud_c} base={main_c}): {estado}\n")
    if estado == "verde":
        return 0
    if estado == "nao-medido":
        return _SAIDA_NAO_MEDIDO
    return 1


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        sys.stdout.write(
            "uso:\n"
            "  esteira rodar [<alvo>] [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--json]\n"
            "  esteira veredito [<alvo>] [--arvore <caminho>] [--mudanca <rev>] [--base <rev>] [--json]\n"
        )
        return 0
    ato = argv[0]
    resto = argv[1:]
    if ato == "rodar":
        return main_rodar(resto)
    if ato == "veredito":
        return main_veredito(resto)
    return main_rodar(argv)


__all__ = [
    "MAX_REPETICOES_ERRATICO",
    "PRAZO_QUARENTENA_DIAS",
    "CasoSelecionado",
    "ClienteBalde",
    "DubleBalde",
    "DubleExecutorIsolado",
    "ExecutorIsoladoUnidade",
    "LinhaBalde",
    "PlanoSelecaoRodada",
    "ResultadoBrutoCaso",
    "VereditoRodada",
    "caminho_veredito_repositorio",
    "carregar_coletor_servido",
    "colocar_em_quarentena",
    "conferir_entidades_exigidas",
    "entidade_disponivel_no_host",
    "estado_quarentena_caso",
    "gravar_veredito",
    "isolamento_disponivel_no_host",
    "ler_veredito",
    "listar_vereditos",
    "main",
    "main_rodar",
    "main_veredito",
    "rodar",
    "selecionar_casos_rodada",
]


if __name__ == "__main__":
    raise SystemExit(main())
