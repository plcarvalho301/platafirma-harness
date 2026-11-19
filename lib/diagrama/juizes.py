"""Juízes da peça diagrama: o auditor de plano e o crítico de figura.

Cada juiz é uma chamada de `agente rodar` com a entrada montada aqui. O código garante a ordem: o
lint antes do auditor, a checagem estrutural antes do crítico. O gabarito e os documentos da fonte
vêm de origin/main, porque vale o que subiu e não o que a bancada tem.

Saída: 0 veredito 0; 1 defeito (lint, checagem, fonte fora de main ou veredito 1); 2 uso;
3 dependência fora (git, acervo, agente, gabarito); 5 não deu para olhar (o agente falhou ou
respondeu sem a linha de veredito).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from diagrama.checagem import checar_plano_svg
from diagrama.lint import lint_plano

GABARITO_PLANO = "instancias/gabarito/plano-de-diagrama.md"
GABARITO_FIGURA = "instancias/gabarito/figura-de-diagrama.md"
GALERIA_CSV = "outros_repos/harness/skills/diagrama/galeria.csv"
SECAO_GERAL = "Em toda figura"
SECAO_DO_TIPO = {
    "camada": "Camada",
    "modulo": "Módulo",
    "componente-e-conector": "Componente e conector",
    "alocacao": "Alocação",
    "fluxo": "Fluxo",
}
MAX_GALERIA = 2
TETO_AGENTE_S = 240
VEREDITO = re.compile(r"^veredito:\s*([01])\b", re.IGNORECASE)


class Dependencia(Exception):
    """Algo de que o ato depende não respondeu: sai 3."""


class NaoOlhei(Exception):
    """O juiz não deu um veredito que se possa usar: sai 5."""


class FonteForaDeMain(Exception):
    """O plano cita documento que não está em origin/main: defeito do plano, sai 1."""


def raiz_do_repo() -> Path:
    r = subprocess.run(
        ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise Dependencia(f"não achei a raiz do repositório: {r.stderr.strip()[:200]}")
    return Path(r.stdout.strip())


def ler_de_main(caminho: str, raiz: Path | None = None) -> str:
    raiz = raiz or raiz_do_repo()
    r = subprocess.run(["git", "-C", str(raiz), "show", f"origin/main:{caminho}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise FonteForaDeMain(f"{caminho} não está em origin/main: {r.stderr.strip()[:200]}")
    return r.stdout


def bin_do_harness(nome: str) -> str:
    pf_bin = os.environ.get("PF_BIN")
    if pf_bin and (Path(pf_bin) / nome).is_file():
        return str(Path(pf_bin) / nome)
    achado = shutil.which(nome)
    if achado:
        return achado
    local = Path(__file__).resolve().parents[2] / "bin" / nome
    if local.is_file():
        return str(local)
    raise Dependencia(f"verbo {nome} não está no PATH nem em PF_BIN")


def sha12(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()[:12]


# --- gabarito -------------------------------------------------------------------------------

def recortar_gabarito(texto: str, tipo: str) -> str:
    """A abertura do gabarito, a seção «Em toda figura» e a seção do tipo, e mais nada."""
    nome_do_tipo = SECAO_DO_TIPO.get(tipo)
    if nome_do_tipo is None:
        raise Dependencia(f"tipo de figura desconhecido: {tipo!r}")
    partes = re.split(r"(?m)^## (.+)$", texto)
    intro = partes[0].rstrip()
    secoes = {partes[i].strip(): partes[i + 1].rstrip() for i in range(1, len(partes) - 1, 2)}
    for nome in (SECAO_GERAL, nome_do_tipo):
        if nome not in secoes:
            raise Dependencia(f"o gabarito da figura não tem a seção «{nome}»")
    return (f"{intro}\n\n## {SECAO_GERAL}\n{secoes[SECAO_GERAL]}\n\n"
            f"## {nome_do_tipo}\n{secoes[nome_do_tipo]}\n")


# --- galeria --------------------------------------------------------------------------------

def _norma(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def escolher_galeria(texto_csv: str, tipo: str, maximo: int = MAX_GALERIA) -> list[dict]:
    """Até `maximo` figuras do tipo, na ordem das linhas. Colunas: arquivo, tipo, endereço, frase."""
    escolhidas: list[dict] = []
    for i, linha in enumerate(csv.reader(io.StringIO(texto_csv))):
        if len(linha) < 4 or not any(c.strip() for c in linha):
            continue
        if i == 0 and _norma(linha[1]) == "tipo":
            continue
        if _norma(linha[1]) == tipo:
            escolhidas.append({"arquivo": linha[0].strip(), "tipo": tipo,
                               "origem": linha[2].strip(), "frase": linha[3].strip()})
        if len(escolhidas) == maximo:
            break
    return escolhidas


def _acervo(*args: str) -> str:
    r = subprocess.run([bin_do_harness("acervo"), *args], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise Dependencia(f"acervo {' '.join(args[:3])} saiu {r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout


def pasta_da_galeria() -> Path:
    base = os.environ.get("DIAGRAMA_CACHE") or tempfile.gettempdir()
    pasta = Path(base) / "diagrama-galeria"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def baixar_figura(titulo: str, pasta: Path) -> Path:
    """A cópia em disco, guardada pelo sha do objeto; só baixa do acervo a que falta."""
    situacao = _acervo("ler", "biblioteca", "obra", titulo, "--situacao")
    m = re.search(r"Objeto\s*:\s*acervo/([0-9a-f]{64})", situacao)
    if not m:
        raise Dependencia(f"a obra {titulo!r} não tem objeto sob guarda")
    sha = m.group(1)
    sufixo = Path(titulo).suffix or ".png"
    destino = pasta / f"{sha}{sufixo}"
    if destino.is_file():
        return destino
    with tempfile.TemporaryDirectory(dir=pasta) as tmp:
        _acervo("ler", "biblioteca", "objeto", titulo, "--destino", tmp)
        baixados = [p for p in Path(tmp).iterdir() if p.is_file()]
        if len(baixados) != 1:
            raise Dependencia(f"o acervo devolveu {len(baixados)} arquivos para {titulo!r}")
        shutil.move(str(baixados[0]), destino)
    return destino


# --- o agente -------------------------------------------------------------------------------

_SITECUSTOMIZE_STDIN = """\
import io, os, sys
_meu_dir = os.path.dirname(os.path.abspath(__file__))
_partes = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and os.path.abspath(p) != _meu_dir]
if _partes:
    os.environ["PYTHONPATH"] = os.pathsep.join(_partes)
else:
    os.environ.pop("PYTHONPATH", None)
if not sys.stdin.isatty():
    _dados = sys.stdin.read()
    _null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(_null, 0)
    os.close(_null)
    sys.stdin = io.StringIO(_dados)
    sys.stdin.isatty = lambda: False
"""


def chamar_agente(slug: str, tarefa: str, anexos: list[str] | None = None) -> tuple[int, str, str]:
    cmd = [bin_do_harness("agente"), "rodar", slug, "--json"]
    for a in anexos or []:
        cmd += ["--anexo", a]
    with tempfile.TemporaryDirectory(prefix="diagrama-stdin-") as guarda:
        (Path(guarda) / "sitecustomize.py").write_text(_SITECUSTOMIZE_STDIN, encoding="utf-8")
        env = dict(os.environ)
        atual = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{guarda}{os.pathsep}{atual}" if atual else guarda
        try:
            r = subprocess.run(cmd, input=tarefa, capture_output=True, text=True,
                               timeout=TETO_AGENTE_S, env=env)
        except subprocess.TimeoutExpired:
            return 5, "", f"agente {slug} estourou o teto de {TETO_AGENTE_S} s"
    retorno = r.stdout
    try:
        retorno = json.loads(r.stdout)["retorno"]
    except (ValueError, KeyError, TypeError):
        pass
    return r.returncode, retorno, r.stderr


def veredito_de(retorno: str) -> tuple[int, str]:
    for linha in retorno.splitlines():
        if linha.strip():
            m = VEREDITO.match(linha.strip())
            if m:
                return int(m.group(1)), retorno.strip()
            break
    raise NaoOlhei(f"a resposta não abre com a linha de veredito: {retorno.strip()[:300]!r}")


def _rodar_juiz(slug: str, tarefa: str, anexos: list[str] | None = None) -> tuple[int, str]:
    rc, retorno, erro = chamar_agente(slug, tarefa, anexos)
    if rc != 0:
        raise NaoOlhei(f"agente {slug} saiu {rc}: {erro.strip()[:300]}")
    return veredito_de(retorno)


# --- os atos --------------------------------------------------------------------------------

def entrada_do_auditor(plano_texto: str, plano_dados: dict, raiz: Path | None = None) -> str:
    gabarito = ler_de_main(GABARITO_PLANO, raiz)
    blocos = [
        "Aplique o gabarito a seguir ao plano de diagrama. Os documentos da fonte dizem o que é verdade.",
        f"## Gabarito\n\n{gabarito.strip()}",
    ]
    docs = []
    for caminho in plano_dados.get("fontes", []):
        docs.append(f"### {caminho}\n\n{ler_de_main(caminho, raiz).strip()}")
    blocos.append("## Documentos da fonte\n\n" + "\n\n".join(docs))
    blocos.append(f"## Plano\n\n```json\n{plano_texto.strip()}\n```")
    blocos.append(f"Responda com «veredito: <0|1> — plano@{sha12(plano_texto.encode('utf-8'))}» "
                  "na primeira linha e depois um defeito por linha, cada um com a linha do plano.")
    return "\n\n".join(blocos) + "\n"


def conferir_plano(caminho_plano: str) -> int:
    cod, defeitos = lint_plano(caminho_plano)
    if cod != 0:
        for d in defeitos:
            print(d, file=sys.stderr)
        return 1
    plano_texto = Path(caminho_plano).read_text(encoding="utf-8")
    try:
        raiz = raiz_do_repo()
        tarefa = entrada_do_auditor(plano_texto, json.loads(plano_texto), raiz)
    except FonteForaDeMain as e:
        print(f"defeito: {e}", file=sys.stderr)
        return 1
    except Dependencia as e:
        print(f"diagrama conferir-plano: {e}", file=sys.stderr)
        return 3
    try:
        veredito, saida = _rodar_juiz("auditor-de-plano", tarefa)
    except NaoOlhei as e:
        print(f"diagrama conferir-plano: não consegui olhar: {e}", file=sys.stderr)
        return 5
    except Dependencia as e:
        print(f"diagrama conferir-plano: {e}", file=sys.stderr)
        return 3
    print(saida)
    return veredito


def entrada_do_critico(plano_texto: str, tipo: str, figuras: list[dict], sha_png: str,
                       raiz: Path | None = None) -> str:
    """Gabarito do tipo, figuras da galeria, plano e PNG, nessa ordem. As marcas [[anexo:N]] pedem a
    imagem em linha; o começo (gabarito e galeria) é igual entre voltas, e o cache o guarda."""
    gabarito = recortar_gabarito(ler_de_main(GABARITO_FIGURA, raiz), tipo)
    blocos = ["Aplique o gabarito a seguir à figura. O plano diz o que ela devia mostrar.",
              f"## Gabarito\n\n{gabarito.strip()}"]
    if figuras:
        refs = [f"Referência {i}: {f['frase']} [[anexo:{i}]]" for i, f in enumerate(figuras, start=1)]
        blocos.append("## Figuras de referência\n\n" + "\n".join(refs))
    else:
        blocos.append("## Figuras de referência\n\nNão há figura de referência para este tipo.")
    blocos.append(f"## Plano\n\n```json\n{plano_texto.strip()}\n```")
    blocos.append(f"## Figura\n\n[[anexo:{len(figuras) + 1}]]")
    blocos.append(f"Responda com «veredito: <0|1> — figura@{sha_png}» na primeira linha e depois um "
                  "defeito por linha, cada um marcado como «conteúdo» ou «forma».")
    return "\n\n".join(blocos) + "\n"


def conferir_figura(caminho_plano: str, caminho_svg: str, caminho_png: str) -> int:
    try:
        cod, defeitos = checar_plano_svg(caminho_plano, caminho_svg)
    except FileNotFoundError as e:
        print(f"diagrama conferir-figura: {e}", file=sys.stderr)
        return 3
    if cod != 0:
        for d in defeitos:
            print(f"defeito: {d}", file=sys.stderr)
        return 1
    png = Path(caminho_png)
    if not png.is_file():
        print(f"diagrama conferir-figura: PNG não encontrado: {caminho_png}", file=sys.stderr)
        return 3
    plano_texto = Path(caminho_plano).read_text(encoding="utf-8")
    tipo = json.loads(plano_texto)["tipo"]
    try:
        raiz = raiz_do_repo()
        try:
            texto_csv = ler_de_main(GALERIA_CSV, raiz)
        except FonteForaDeMain:
            texto_csv = ""
        figuras = escolher_galeria(texto_csv, tipo) if texto_csv else []
        pasta = pasta_da_galeria() if figuras else None
        copias = [str(baixar_figura(f["arquivo"], pasta)) for f in figuras]
        tarefa = entrada_do_critico(plano_texto, tipo, figuras, sha12(png.read_bytes()), raiz)
    except Dependencia as e:
        print(f"diagrama conferir-figura: {e}", file=sys.stderr)
        return 3
    try:
        veredito, saida = _rodar_juiz("critico-de-figura", tarefa, copias + [str(png)])
    except NaoOlhei as e:
        print(f"diagrama conferir-figura: não consegui olhar: {e}", file=sys.stderr)
        return 5
    except Dependencia as e:
        print(f"diagrama conferir-figura: {e}", file=sys.stderr)
        return 3
    print(saida)
    if not figuras:
        print(f"rodou sem referência: a galeria não tem figura do tipo {tipo}")
    return veredito


def main_plano(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print("uso: diagrama conferir-plano <plano.json>", file=sys.stderr)
        return 2
    return conferir_plano(argv[0])


def main_figura(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] in ("-h", "--help"):
        print("uso: diagrama conferir-figura <plano.json> <figura.svg> <figura.png>", file=sys.stderr)
        return 2
    return conferir_figura(*argv)
