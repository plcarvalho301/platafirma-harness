"""motor raciocinador — o HermiT sobre um modelo formal e os casos somados a ele.

CHAMADA TEMPORÁRIA (dono, 01/11/2026, card #4077): serve a story 3972, que põe à prova o modelo que o
gerador tira das shapes do espelho. A forma definitiva sai na revisão dos documentos do acervo.

    motor raciocinador raciocinar --modelo <modelo.ttl> [--somar <caso.ttl>]...

O `bin/motor` despacha a instância para cá, rodando com o Python do rag da release (rdflib e owlready2). O
modelo recebe o MIREOT servido (as posições dos topos do BFO, sem as quais a disjunção do núcleo não tem o
que reprovar) e cada `--somar`, perde o `owl:imports` e vai ao HermiT. Os arquivos lidos ficam dentro da
bancada declarada ou de `var/tmp` da instância. Nada se grava fora de uma pasta temporária; banco nenhum.

Saída: 0 o modelo fecha; 1 inconsistente ou com classe insatisfazível (as classes vêm nomeadas); 2 uso;
5 não rodou (Java fora do PATH, rdflib ou owlready2 fora do Python, MIREOT fora da máquina, HermiT com
erro), que não equivale a fecha.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

_ARVORE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ARVORE / "lib"))
import raizes  # noqa: E402

USO = "uso: motor raciocinador raciocinar --modelo <modelo.ttl> [--somar <caso.ttl>]..."


def argumentos(argv: list):
    """(modelo, [somados]) ou None se o uso está errado: o ato é `raciocinar`, `--modelo` uma vez."""
    if not argv or argv[0] != "raciocinar":
        return None
    modelo, somados, i = None, [], 1
    while i < len(argv):
        nome = argv[i]
        if nome not in ("--modelo", "--somar") or i + 1 >= len(argv) or not argv[i + 1]:
            return None
        if nome == "--modelo":
            if modelo is not None:
                return None
            modelo = argv[i + 1]
        else:
            somados.append(argv[i + 1])
        i += 2
    return (modelo, somados) if modelo else None


def _raizes_de_leitura() -> list:
    raizes_ok = [(raizes.instancia() / "var" / "tmp").resolve()]
    try:
        raizes_ok.append(raizes.bancada().resolve())
    except raizes.BancadaNaoDeclarada:
        pass
    return raizes_ok


def conferir_caminho(texto: str) -> tuple:
    """(Path, None) se o arquivo existe e cai numa raiz de leitura; (None, motivo) senão."""
    alvo = Path(texto).expanduser().resolve()
    if not any(alvo == r or r in alvo.parents for r in _raizes_de_leitura()):
        return None, f"{texto}: fora da bancada declarada e de var/tmp da instância"
    if not alvo.is_file():
        return None, f"{texto}: não existe"
    return alvo, None


def mireot_servido() -> Path:
    """`PF_MIREOT_TTL`, senão o da release no ar (a mesma resolução de `gerador/mireot.py`)."""
    release = os.environ.get("PLATAFIRMA_RELEASE") or os.path.join(
        os.environ.get("PF_RELEASE_RAIZ") or "/opt/platafirma", "current")
    return Path(os.environ.get("PF_MIREOT_TTL")
                or os.path.join(release, "motor", "onto-ref", "modelo_bfo", "external-mireot.ttl"))


def raciocinar(modelo: Path, somados: list, mireot: Path) -> tuple:
    """(True, motivo, ()) fecha; (False, motivo, classes) reprova; (None, motivo, ()) não rodou."""
    if shutil.which(os.environ.get("JAVA_EXE") or "java") is None:
        return None, "Java fora do PATH: o HermiT roda na JVM", ()
    try:
        from rdflib import Graph
        from rdflib.namespace import OWL
    except Exception as e:
        return None, f"rdflib indisponível: {type(e).__name__}: {e}", ()
    try:
        from owlready2 import World, sync_reasoner_hermit
    except Exception as e:
        return None, f"owlready2 indisponível: {type(e).__name__}: {e}", ()
    g = Graph()
    for arquivo in (modelo, mireot, *somados):
        try:
            g.parse(arquivo, format="turtle")
        except Exception as e:
            return None, f"{arquivo} não se lê como turtle: {type(e).__name__}: {str(e)[:200]}", ()
    for t in list(g.triples((None, OWL.imports, None))):
        g.remove(t)
    with tempfile.TemporaryDirectory(prefix="motor-raciocinador-") as d:
        xml = Path(d) / "modelo.owl"
        g.serialize(xml, format="xml")
        w = World()
        onto = w.get_ontology("file://" + str(xml)).load()
        try:
            with onto:
                sync_reasoner_hermit(w, debug=0)
        except Exception as e:
            if type(e).__name__ == "OwlReadyInconsistentOntologyError":
                return False, f"inconsistente: {str(e)[:300]}", ()
            return None, f"HermiT não rodou: {type(e).__name__}: {str(e)[:300]}", ()
        insat = tuple(sorted(n for n in (getattr(c, "name", str(c)) for c in w.inconsistent_classes())
                             if n != "Nothing"))
    if insat:
        return False, "classes insatisfazíveis: " + ", ".join(insat), insat
    return True, "HermiT: o modelo fecha", ()


def main(argv: list) -> int:
    lido = argumentos(argv)
    if lido is None:
        print(USO, file=sys.stderr)
        return 2
    texto_modelo, textos_somados = lido
    caminhos = []
    for texto in (texto_modelo, *textos_somados):
        alvo, motivo = conferir_caminho(texto)
        if motivo:
            print(f"motor raciocinador: {motivo}", file=sys.stderr)
            return 2
        caminhos.append(alvo)
    mireot = mireot_servido()
    if not mireot.is_file():
        print(f"motor raciocinador: MIREOT servido fora da máquina: {mireot}; sem as posições do BFO o "
              "raciocinador não tem o que reprovar", file=sys.stderr)
        return 5
    estado, motivo, _ = raciocinar(caminhos[0], caminhos[1:], mireot)
    print(f"motor raciocinador: {motivo}", file=sys.stdout if estado is True else sys.stderr)
    print(f"modelo: {caminhos[0]}" + (f" · somados: {', '.join(str(c) for c in caminhos[1:])}"
                                       if len(caminhos) > 1 else ""))
    return 0 if estado is True else 1 if estado is False else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
