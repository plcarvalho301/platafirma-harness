"""arvore — árvore do repositório da casa: o que mora nela, onde e com que forma.

Cobra o registro de decisão 0138 (repositório pela natureza do arquivo):
  - quatro raízes: `instancias/`, `referencias/`, `verbetes/`, `outros_repos/`;
  - lê a forma da classe (`golden` e `referencia`) e as fichas do fichário que quem chama passa, e não das shapes;
  - ficha de instância para todo documento em `instancias/`, nenhum com o nome da classe;
  - referência apontando classe ou ficha que existe;
  - verbete em `verbetes/<dicionario>/<valor>.md` (nunca `verbetes/classes/...`, regra 13);
  - documento numerado aberto pelo número.
"""
from __future__ import annotations

import os
import posixpath
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from .resultado import Apontamento

RAIZES = ("instancias", "referencias", "verbetes", "outros_repos")
DESTINOS = ("arquitetura", "cofre-backup", "conhecimento", "core", "harness", "motor", "ollama-orchestrator",
            "osint", "posto", "rastreador", "ui")

_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_MARCA = re.compile(r"<([^<>]+)>")
_MARCAS = {"numero": r"[0-9]+", "AAAA-MM-DD": r"[0-9]{4}-[0-9]{2}-[0-9]{2}"}
_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_ESQUEMA = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_ABERTO = re.compile(r"^\s{0,3}#{1,6}\s+Aberto\s*$", re.IGNORECASE)
_A_DECLARAR = re.compile(r"(?:^|\|)\s*(?:«\s*)?a declarar(?:\s*»)?\s*(?:\||$)", re.IGNORECASE)
_MARCADORES = {".gitkeep", ".keep", ".gitignore", ".gitattributes"}
_NUMERADAS = ("registro-de-decisao", "politica")


class _Forma:
    """Uma classe do catálogo com original, referência, definição e critério de identidade."""

    def __init__(self, slug: str, original: Optional[str], referencia: Optional[str],
                 definicao: str = "", criterio: str = ""):
        self.slug = slug
        self.original = original
        self.referencia = referencia
        self.definicao = definicao
        self.criterio = criterio
        self.regex_original = _regex(original) if original else None
        self.regex_referencia = _regex(referencia) if referencia else None


def _regex(padrao: str) -> re.Pattern:
    partes, fim = [], 0
    for m in _MARCA.finditer(padrao):
        partes.append(re.escape(padrao[fim:m.start()]))
        partes.append(_MARCAS.get(m.group(1), _SLUG))
        fim = m.end()
    partes.append(re.escape(padrao[fim:]))
    return re.compile("^" + "".join(partes) + "$")


def _normalizar_formas(formas: dict) -> dict[str, _Forma]:
    saida: dict[str, _Forma] = {}
    for slug, valor in formas.items():
        if isinstance(valor, _Forma):
            saida[slug] = valor
        elif isinstance(valor, dict):
            saida[slug] = _Forma(
                slug,
                valor.get("golden"),
                valor.get("referencia"),
                valor.get("definicao") or "",
                valor.get("criterio") or "",
            )
    return saida


def _destinos() -> tuple:
    de_fora = os.environ.get("PF_ARVORE_DESTINOS")
    return tuple(n.strip() for n in de_fora.split(",") if n.strip()) if de_fora else DESTINOS


def _git(raiz: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise ValueError(5, f"indeterminavel — git {' '.join(args[:2])} saiu {r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout


def _lista(raiz: Path, *args: str) -> list:
    return [p for p in _git(raiz, *args, "-z").split("\0") if p]


def _texto(raiz: Path, rel: str) -> list:
    try:
        return (raiz / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _links(linhas: list) -> list:
    """(linha, alvo como escrito) de cada link relativo `[texto](caminho)` fora de bloco de código."""
    achados, cerca = [], False
    for i, linha in enumerate(linhas, start=1):
        if linha.lstrip().startswith("```"):
            cerca = not cerca
            continue
        if cerca:
            continue
        for m in _LINK.finditer(linha):
            alvo = m.group(1)
            if alvo.startswith("#") or _ESQUEMA.match(alvo):
                continue
            achados.append((i, alvo))
    return achados


def _quebrados(rel: str, linhas: list, existe) -> list:
    saida = []
    for i, alvo in _links(linhas):
        arquivo = re.split(r"[#?]", alvo, maxsplit=1)[0]
        if not arquivo:
            continue
        resolvido = posixpath.normpath(posixpath.join(posixpath.dirname(rel), arquivo))
        if resolvido.startswith("..") or not existe(resolvido):
            saida.append((i, alvo))
    return saida


def _conjunto(arquivos: list):
    todos = set(arquivos)
    pastas = {posixpath.dirname(a) for a in arquivos}
    for p in list(pastas):
        while p:
            pastas.add(p)
            p = posixpath.dirname(p)
    return lambda caminho: caminho in todos or caminho in pastas


def _chave_da_instancia(classe: str, subpastas: list[str]) -> str:
    nome = "/".join(subpastas)[:-3]
    numero = re.match(r"^(\d+)-", nome)
    if numero and classe in _NUMERADAS:
        return numero.group(1)
    return nome.replace("/", ":")


def _pastas_vazias(raiz: Path) -> list:
    vazias = []
    for atual, subpastas, arquivos in os.walk(raiz):
        subpastas[:] = [d for d in subpastas if d != ".git"]
        if atual == str(raiz):
            continue
        if not arquivos and not any(True for _ in _arquivos_abaixo(Path(atual))):
            vazias.append(os.path.relpath(atual, raiz).replace(os.sep, "/"))
    return [p for p in vazias if posixpath.dirname(p) not in vazias]


def _arquivos_abaixo(pasta: Path):
    for atual, _sub, arquivos in os.walk(pasta):
        for a in arquivos:
            yield Path(atual) / a


def verificar_arvore(
    raiz: Path | str,
    alvo: Optional[str] = None,
    staged: bool = False,
    herdados: Optional[list] = None,
    *,
    formas: Optional[dict] = None,
    fichas: Optional[Iterable[tuple[str, str]]] = None,
    dicionarios: Optional[dict] = None,
) -> list[Apontamento]:
    """Aponta o que destoa da árvore da casa segundo as quatro raízes e a gramática de documentos da casa."""
    if formas is None:
        raise ValueError(5, "indeterminavel — informe formas e fichas do fichário")
    raiz = Path(raiz)
    formas_map = _normalizar_formas(formas)
    fichas_set = set(fichas or ())
    dicionarios_map = {k: set(v) for k, v in (dicionarios or {}).items()}
    destinos = _destinos()

    if staged:
        universo = _lista(raiz, "ls-files")
        sob_juizo = _lista(raiz, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    else:
        universo = _lista(raiz, "ls-files", "--cached", "--others", "--exclude-standard")
        sob_juizo = list(universo)
    universo = [a for a in universo if (raiz / a).is_file()]
    if alvo:
        base = alvo.strip("/")
        sob_juizo = [a for a in sob_juizo if a == base or a.startswith(base + "/")]
    sob_juizo = sorted(a for a in sob_juizo if (raiz / a).is_file())

    apontamentos: list = []
    avisadas: set = set()

    def pasta_uma_vez(pasta: str, o_que: str, cura: str, id_: str):
        if (id_, pasta) not in avisadas:
            avisadas.add((id_, pasta))
            apontamentos.append(Apontamento(pasta, 1, o_que, cura, severidade="aviso", id=id_))

    def aponta(arq: str, linha: int, o_que: str, cura: str, id_: str):
        apontamentos.append(Apontamento(arq, linha, o_que, cura, severidade="aviso", id=id_))

    numeradas: dict = {}
    documentos = []
    for rel in sob_juizo:
        segmentos = rel.split("/")
        nome = segmentos[-1]
        if len(segmentos) == 1:
            if nome in _MARCADORES or nome == ".conferir-repo":
                continue
            aponta(rel, 1, "arquivo na raiz sem natureza (regra 1 do 0138)",
                   "mover para instancias/, referencias/ ou verbetes/, ou apagar", "ARVORE_TIPO")
            continue
        topo = segmentos[0]
        if topo not in RAIZES:
            pasta_uma_vez(topo, "pasta na raiz fora das quatro raízes da casa (instancias, referencias, verbetes, outros_repos)",
                          "mover o arquivo para a raiz da natureza dele e apagar a pasta antiga", "ARVORE_RAIZ")
            continue
        if topo == "outros_repos":
            if len(segmentos) == 2:
                aponta(rel, 1, "arquivo solto em outros_repos/",
                       "mover para a pasta do repositório de destino ou apagar", "ARVORE_TIPO")
            elif segmentos[1] not in destinos:
                pasta_uma_vez(f"outros_repos/{segmentos[1]}",
                              "pasta de outros_repos que não é repositório de destino da casa",
                              "renomear a pasta para o repositório de destino ou apagá-la", "ARVORE_DESTINO")
            continue
        if topo == "instancias" and len(segmentos) >= 3 and segmentos[1] == "figura" and any(
            nome.endswith(ext) for ext in (".svg",)
        ):
            continue
        if not rel.endswith(".md") or nome in _MARCADORES:
            aponta(rel, 1, "arquivo fora da gramática de documentos Markdown da casa",
                   "remover o arquivo que não é documento Markdown", "ARVORE_TIPO")
            continue

        if topo == "instancias":
            if len(segmentos) < 3:
                aponta(rel, 1, "original sem pasta de classe (instancias/<classe>/<slug>.md)",
                       "mover para instancias/<classe>/<slug>.md", "ARVORE_CAMINHO")
                continue
            classe = segmentos[1]
            if len(segmentos) == 3 and nome == f"{classe}.md":
                aponta(rel, 1, "nenhum original pode ter o nome da classe (regra 10 do 0138)",
                       f"renomear para a instância (ex.: instancias/{classe}/da-casa.md) ou mover para referencias/classes/{classe}.md",
                       "ARVORE_ORIGINAL_DA_CLASSE")
                continue
            forma = formas_map.get(classe)
            if forma is None:
                aponta(rel, 1, f"original de classe desconhecida no catálogo [{classe}]",
                       "declarar a classe na Olaria ou corrigir o caminho", "ARVORE_CLASSE")
                continue
            chave = _chave_da_instancia(classe, segmentos[2:])
            if (classe, chave) not in fichas_set and (classe, f"{classe}:{chave}") not in fichas_set:
                aponta(rel, 1, f"original sem ficha no fichário [{classe}:{chave}]",
                       "gravar a ficha na Olaria antes ou junto com o arquivo", "ARVORE_SEM_FICHA")
            if forma.regex_original and not forma.regex_original.match(rel):
                aponta(rel, 1, f"caminho do original fora do molde da classe [{forma.original}]",
                       f"mover para o molde {forma.original}", "ARVORE_CAMINHO")
            if (forma.original and "<numero>" in forma.original) or classe in _NUMERADAS:
                m = re.match(r"^(\d+)-", nome)
                if m:
                    numeradas.setdefault(posixpath.dirname(rel), {}).setdefault(m.group(1), []).append(rel)
            documentos.append((rel, "original", classe))
            continue

        if topo == "referencias":
            if len(segmentos) == 3 and segmentos[1] == "classes":
                classe = nome[:-3]
                if classe not in formas_map:
                    aponta(rel, 1, f"referência de classe aponta classe inexistente [{classe}]",
                           "apagar a referência ou declarar a classe no catálogo", "ARVORE_CLASSE")
                documentos.append((rel, "referencia_classe", classe))
                continue
            if len(segmentos) >= 4 and segmentos[1] == "instancias":
                classe = segmentos[2]
                if classe not in formas_map:
                    aponta(rel, 1, f"referência de instância aponta classe inexistente [{classe}]",
                           "apagar a referência ou declarar a classe no catálogo", "ARVORE_CLASSE")
                    continue
                chave = _chave_da_instancia(classe, segmentos[3:])
                if (classe, chave) not in fichas_set and (classe, f"{classe}:{chave}") not in fichas_set:
                    aponta(rel, 1, f"referência de instância sem ficha no fichário [{classe}:{chave}]",
                           "apagar a referência ou gravar a ficha na Olaria", "ARVORE_SEM_FICHA")
                documentos.append((rel, "referencia_instancia", classe))
                continue
            aponta(rel, 1, "referência fora de referencias/classes/<classe>.md ou referencias/instancias/<classe>/<chave>.md",
                   "mover para referencias/classes/ ou referencias/instancias/", "ARVORE_CAMINHO")
            continue

        if topo == "verbetes":
            if len(segmentos) >= 2 and segmentos[1] == "classes":
                aponta(rel, 1, "regra 13 do 0138: não há verbetes/classes/ (classe não tem original)",
                       "mover para referencias/classes/<classe>.md", "ARVORE_REGRA_13")
                continue
            if len(segmentos) != 3:
                aponta(rel, 1, "verbete fora de verbetes/<dicionario>/<valor>.md",
                       "mover para verbetes/<dicionario>/<valor>.md", "ARVORE_CAMINHO")
                continue
            dic, val = segmentos[1], nome[:-3]
            if dicionarios is not None and (dic not in dicionarios_map or val not in dicionarios_map[dic]):
                aponta(rel, 1, f"verbete aponta entrada ausente do dicionário [{dic}:{val}]",
                       "gravar o valor no dicionário pela Olaria ou apagar o arquivo", "ARVORE_VERBETE")
            documentos.append((rel, "verbete", dic))

    for pasta, por_numero in numeradas.items():
        for numero, arquivos in por_numero.items():
            if len(arquivos) > 1:
                for rel in arquivos:
                    aponta(rel, 1, f"número repetido na mesma classe [{numero}]",
                           "renumerar o documento, porque o número da chave não se repete", "ARVORE_NUMERO")

    for rel, tipo, slug in documentos:
        linhas = _texto(raiz, rel)
        for i, linha in enumerate(linhas, start=1):
            if _ABERTO.match(linha):
                aponta(rel, i, "documento com seção Aberto",
                       "levar o que falta a um card ou ao balde de débito técnico e tirar a seção", "ARVORE_ABERTO")
            if "|" in linha and _A_DECLARAR.search(linha):
                aponta(rel, i, "documento com célula «a declarar»",
                       "levar o que falta a um card ou ao balde de débito técnico e tirar a célula", "ARVORE_ABERTO")
        forma = formas_map.get(slug)
        if tipo == "original" and ((forma and forma.original and "<numero>" in forma.original) or slug in _NUMERADAS):
            no_nome = re.match(r"^(\d+)-", posixpath.basename(rel))
            no_titulo = re.match(r"^#\s+(\d+)\b", linhas[0]) if linhas else None
            if no_nome and no_titulo and int(no_nome.group(1)) != int(no_titulo.group(1)):
                aponta(rel, 1, f"documento numerado cujo nome não abre pelo número da chave [{no_titulo.group(1)}]",
                       "renomear o arquivo para abrir pelo número da chave, que o título diz", "ARVORE_NUMERO")

    for pasta in _pastas_vazias(raiz):
        if not alvo or pasta.startswith(alvo.strip("/")) or alvo.strip("/").startswith(pasta):
            pasta_uma_vez(pasta, "pasta sem documento", "apagar a pasta, que nasce com o primeiro documento",
                          "ARVORE_VAZIA")

    apontamentos.extend(_links_do_commit(raiz, universo, sob_juizo, staged, herdados))
    return apontamentos


def _links_do_commit(raiz, universo, sob_juizo, staged, herdados) -> list:
    """Link relativo quebrado em qualquer .md da árvore."""
    existe_depois = _conjunto(universo)
    markdown = [a for a in universo if a.endswith(".md") and not a.startswith("outros_repos/")]
    saida = []
    quebrados_depois = {a: _quebrados(a, _texto(raiz, a), existe_depois) for a in markdown}
    if not staged:
        for rel in sob_juizo:
            if rel not in quebrados_depois:
                continue
            for i, alvo in quebrados_depois[rel]:
                saida.append(Apontamento(rel, i, f"link relativo quebrado [{alvo}]",
                                         "reescrever o link para o caminho que existe ou tirá-lo",
                                         severidade="aviso", id="ARVORE_LINK"))
        return saida
    try:
        no_head = set(_lista(raiz, "ls-tree", "-r", "--name-only", "HEAD"))
    except ValueError:
        no_head = set()
    existe_antes = _conjunto(sorted(no_head))
    for rel, quebrados in quebrados_depois.items():
        if not quebrados:
            continue
        antes = set()
        if rel in no_head:
            try:
                velho = _git(raiz, "show", f"HEAD:{rel}").splitlines()
            except ValueError:
                velho = []
            antes = {alvo for _, alvo in _quebrados(rel, velho, existe_antes)}
        for i, alvo in quebrados:
            if alvo in antes:
                if herdados is not None:
                    herdados.append((rel, i, alvo))
            else:
                saida.append(Apontamento(rel, i, f"link relativo que o commit quebrou [{alvo}]",
                                         "reescrever o link para o novo caminho do alvo ou tirá-lo",
                                         severidade="aviso", id="ARVORE_LINK"))
    return saida
