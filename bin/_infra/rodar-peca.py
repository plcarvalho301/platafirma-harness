#!/usr/bin/env python3
"""infra pecas | infra rodar — executa uma peça de código declarada em registro/pecas.json.

Manutenção (dono, 02/11/2026, pedido 20261102T091653-dados): o verbo que roda componente e
serviço sem que cada caso peça verbo próprio. Não é ferramenta nova na porta: é ato do `infra`,
que já é servido, e por isso o malote também o alcança.

O gate é determinístico e mora aqui, não em quem chama:
  1. a peça está declarada em registro/pecas.json (declarar é PR no harness); senão 4;
  2. origem=espelho: o código é o da bancada da sessão no repositório da peça, e cada caminho da
     peça (cwd e pythonpath) tem de ser igual a origin/main, sem arquivo fora do git; senão 4.
     Quem roda o que não subiu não sabe o que rodou: commit e sincronizar antes;
  3. origem=release: a árvore da release no ar, que é imutável.
A credencial do banco vem do cofre pelo mesmo caminho de `acervo exportar` e não é impressa: só
os nomes das variáveis saem no stderr.

Saída: a da peça quando ela roda (o stderr diz «peça saiu N»); 2 uso; 3 dependência (bancada,
python, fetch, registro); 4 peça não declarada ou caminho diferente de origin/main; 5 estourou o
teto ou não abriu.
"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REG = Path(os.environ.get("INFRA_PECAS") or (AQUI.parents[1] / "registro" / "pecas.json"))
TETO_PADRAO_S = 600
USO = ("uso:\n  infra pecas [--json]\n"
       "  infra rodar <peca> [--bancada <chave>] [-- <args da peça>…]")


def morre(msg: str, cod: int = 3):
    print(f"infra rodar: {msg}", file=sys.stderr)
    sys.exit(cod)


def _exportar():
    """O `acervo exportar` é dono da escolha da bancada, do python do rag e do ambiente do banco
    pelo cofre; este ato os reusa, com o repositório da peça e as mensagens de erro daqui."""
    caminho = AQUI.parent / "_acervo" / "exportar"
    loader = importlib.machinery.SourceFileLoader("acervo_exportar_do_infra", str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.morre = morre
    return mod


def registro() -> dict:
    try:
        dados = json.loads(REG.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        morre(f"registro de peças ilegível ({REG}): {e}", 3)
    return {k: v for k, v in dados.items() if not k.startswith("_") and isinstance(v, dict)}


def listar(argv: list) -> int:
    if argv not in ([], ["--json"]):
        print(USO, file=sys.stderr)
        return 2
    pecas = registro()
    if argv:
        print(json.dumps(pecas, ensure_ascii=False, indent=2))
        return 0
    if not pecas:
        print("nenhuma peça declarada")
        return 0
    for nome, p in sorted(pecas.items()):
        print(f"{nome} · dono {p.get('dono', '?')} · {p.get('origem')} {p.get('repo') or p.get('dir', '')}"
              f" · python -m {p.get('modulo')} · ambiente {p.get('ambiente') or 'nenhum'}")
        if p.get("motivo"):
            print(f"  {p['motivo']}")
    return 0


def argumentos(argv: list):
    """(peca, chave da bancada, args da peça) ou None se o uso está errado."""
    if not argv or argv[0].startswith("-"):
        return None
    peca, resto, chave = argv[0], argv[1:], ""
    if resto[:1] == ["--bancada"]:
        if len(resto) < 2 or not resto[1]:
            return None
        chave, resto = resto[1], resto[2:]
    if resto and resto[0] != "--":
        return None
    return peca, chave, resto[1:]


def _git(wt: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(wt), *args], capture_output=True, text=True)


def gate_origin_main(wt: Path, caminhos: list) -> str:
    """O sha de origin/main, se cada caminho da peça é igual a ele; senão sai 4 dizendo o quê."""
    r = _git(wt, "fetch", "--quiet", "origin", "main")
    if r.returncode != 0:
        morre(f"fetch de origin/main falhou em {wt}: {r.stderr.strip()[:300]}", 3)
    r = _git(wt, "rev-parse", "origin/main")
    if r.returncode != 0:
        morre(f"{wt} sem origin/main: {r.stderr.strip()[:300]}", 3)
    sha = r.stdout.strip()
    dif = _git(wt, "diff", "--name-only", "origin/main", "--", *caminhos)
    soltos = _git(wt, "ls-files", "--others", "--exclude-standard", "--", *caminhos)
    if dif.returncode != 0 or soltos.returncode != 0:
        morre(f"não consegui comparar {wt} com origin/main: {(dif.stderr or soltos.stderr).strip()[:300]}", 3)
    fora = [l for l in dif.stdout.splitlines() if l] + [f"{l} (fora do git)" for l in soltos.stdout.splitlines() if l]
    if fora:
        mostra = ", ".join(fora[:10]) + (f" … +{len(fora) - 10}" if len(fora) > 10 else "")
        morre(f"a peça difere de origin/main ({sha[:12]}): {mostra} — commite e sincronize antes de rodar", 4)
    return sha


def rodar(argv: list) -> int:
    lido = argumentos(argv)
    if lido is None:
        print(USO, file=sys.stderr)
        return 2
    nome, chave, args_peca = lido
    pecas = registro()
    p = pecas.get(nome)
    if p is None:
        morre(f"peça não declarada: {nome} — as declaradas são {', '.join(sorted(pecas)) or 'nenhuma'}; "
              f"declarar é PR em registro/pecas.json do harness", 4)
    modulo = p.get("modulo") or ""
    if not modulo:
        morre(f"peça {nome} sem modulo no registro", 3)
    ex = _exportar()
    origem = p.get("origem")
    if origem == "espelho":
        ex.REPO = p.get("repo") or morre(f"peça {nome} sem repo no registro", 3)
        raiz = ex.bancada_do_repo(chave)
        caminhos = sorted({p.get("cwd") or "."} | set(p.get("pythonpath") or []))
        sha = gate_origin_main(raiz, caminhos)
        procedencia = f"{ex.REPO}@{sha[:12]} (origin/main) na bancada {raiz}"
    elif origem == "release":
        raiz = ex.raizes.release() / (p.get("dir") or morre(f"peça {nome} sem dir no registro", 3))
        procedencia = f"release {raiz.resolve()}"
    else:
        morre(f"peça {nome} com origem desconhecida: {origem!r} (espelho ou release)", 3)
    if not raiz.is_dir():
        morre(f"{raiz} não existe", 3)
    if p.get("python") != "rag":
        morre(f"peça {nome}: python {p.get('python')!r} não servido (só rag)", 3)
    py = ex.python_do_rag()
    env = dict(os.environ)
    ambiente = p.get("ambiente") or ""
    if ambiente == "banco-rag":
        env.update(ex.ambiente_da_ingestao())
    elif ambiente:
        morre(f"peça {nome}: ambiente {ambiente!r} não servido (só banco-rag)", 3)
    env["PYTHONPATH"] = os.pathsep.join(str(raiz / c) for c in (p.get("pythonpath") or []))
    # DT 456: o bytecode gravado na bancada fazia o gate recusar a chamada seguinte (fora do git).
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cwd = raiz / (p.get("cwd") or ".")
    teto = int(p.get("teto_s") or TETO_PADRAO_S)
    sujeito = os.environ.get("PF_SUJEITO", "")
    print(f"peça: {nome} · {procedencia} · python -m {modulo} {' '.join(args_peca)}".rstrip()
          + (f" · sujeito={sujeito}" if sujeito else ""), file=sys.stderr, flush=True)
    try:
        r = subprocess.run([py, "-m", modulo, *args_peca], cwd=cwd, env=env, timeout=teto, check=False)
    except subprocess.TimeoutExpired:
        morre(f"peça {nome} estourou o teto de {teto} s", 5)
    except OSError as e:
        morre(f"peça {nome} não abriu: {e}", 5)
    print(f"peça saiu {r.returncode}", file=sys.stderr)
    return r.returncode


def main(argv: list) -> int:
    if not argv or argv[0] not in ("pecas", "rodar"):
        print(USO, file=sys.stderr)
        return 2
    return listar(argv[1:]) if argv[0] == "pecas" else rodar(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
