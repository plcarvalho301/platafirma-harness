#!/usr/bin/env python3
# registro — leitor único de registro/venvs.json, para release, teste e pre-push
# (card #3150, comentário B1: "release, teste e pre-push importam o mesmo leitor;
# nenhum relê o JSON por conta própria").
"""Registro stack/repositório -> (família, lock, subárvore de teste, esteira, stack_real).

Cada chave do JSON (exceto as que começam com "_", que são comentário, e "repositorios")
declara uma stack: {"familia": "<repo>", "lock": "<caminho do lock na árvore>", "teste":
"<subárvore onde a suíte que usa este venv mora, opcional>"}. `lock` é o caminho
lido por release para construir o venv (chave = <nome>-sha256(lock+python)) e por
teste/pre-push para reaproveitar o mesmo venv, pela mesma chave.

Campo opcional "testes" (card #3316): lista de globs, relativos à raiz de teste da stack
(a subárvore, senão a raiz do clone), que é a suíte da stack quando `teste rodar` vem sem
alvo. Sem ele, a stack que divide repositório com outra e não declara subárvore não tem
suíte própria: rodar da raiz coletaria o repositório inteiro.

Uso:
  registro.py <nome>              família, lock, subárvore, esteira, stack e globs de teste
                                  (TSV; globs separados por vírgula, "-" sem declaração)
  registro.py --familia <familia> uma linha TSV (nome, lock, teste) por stack da família
  registro.py --all               uma linha TSV (nome, família, lock, teste, esteira) por stack

exit: 0 achou · 2 stack/repositório desconhecido ou nome duplicado (stack = repo) ·
      3 registro ausente ou ilegível · 5 stack conhecida sem lock declarado
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def caminho_registro() -> Path:
    return Path(os.environ.get("PLATAFIRMA_VENVS", "registro/venvs.json"))


class RegistroIlegivel(RuntimeError):
    """Registro ausente, ou não é o JSON esperado — sai 3."""


class StackDesconhecida(RuntimeError):
    def __init__(self, nome: str, conhecidas: list[str]):
        super().__init__(nome)
        self.nome = nome
        self.conhecidas = conhecidas


class StackSemLock(RuntimeError):
    def __init__(self, nome: str, lock: str = ""):
        super().__init__(nome)
        self.nome = nome
        self.lock = lock


class NomeDuplicado(RuntimeError):
    def __init__(self, nome: str):
        super().__init__(nome)
        self.nome = nome


def carregar_tudo(caminho: Path | None = None) -> tuple[dict[str, dict], dict[str, dict]]:
    caminho = caminho or caminho_registro()
    try:
        bruto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistroIlegivel(f"registro de venvs ilegível ({caminho}): {exc}") from exc
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError as exc:
        raise RegistroIlegivel(f"registro de venvs não é JSON válido ({caminho}): {exc}") from exc
    if not isinstance(dados, dict):
        raise RegistroIlegivel(f"registro de venvs não é um objeto ({caminho})")

    repos_raw = dados.get("repositorios") or dados.get("_repositorios") or {}
    if not isinstance(repos_raw, dict):
        repos_raw = {}

    stacks_raw = dados.get("stacks") if isinstance(dados.get("stacks"), dict) else {
        k: v for k, v in dados.items() if not k.startswith("_") and k != "repositorios"
    }

    repos: dict[str, dict] = {k: (dict(v) if isinstance(v, dict) else {}) for k, v in repos_raw.items()}
    for s_nome, s_decl in stacks_raw.items():
        if isinstance(s_decl, dict) and s_decl.get("familia"):
            f = s_decl["familia"]
            if f not in repos:
                repos[f] = {"esteira": s_decl.get("esteira", "codigo")}

    # Recusa na leitura de stack com nome igual a repositório (exit 2 nomeando os dois)
    for s_nome in stacks_raw.keys():
        if s_nome in repos:
            raise NomeDuplicado(s_nome)

    return stacks_raw, repos


def carregar(caminho: Path | None = None) -> dict:
    stacks, _ = carregar_tudo(caminho)
    return stacks


def stacks_da_familia(familia: str, caminho: Path | None = None) -> list[tuple[str, str, str]]:
    """[(nome, lock, subárvore de teste)] das stacks declaradas para <familia>."""
    stacks, _ = carregar_tudo(caminho)
    saida = []
    for nome, decl in stacks.items():
        if not isinstance(decl, dict) or decl.get("familia") != familia:
            continue
        saida.append((nome, decl.get("lock", "") or "", decl.get("teste", "") or ""))
    return saida


def resolver(nome: str, caminho: Path | None = None) -> tuple[str, str, str, str, str]:
    """Resolve <nome> (stack ou repositório) -> (stack_real, família, lock, subárvore, esteira).

    Levanta StackDesconhecida, StackSemLock ou NomeDuplicado.
    """
    stacks, repos = carregar_tudo(caminho)

    if nome in stacks:
        decl = stacks[nome]
        if not isinstance(decl, dict):
            raise StackDesconhecida(nome, sorted(list(stacks.keys()) + list(repos.keys())))
        familia = decl.get("familia", "") or ""
        lock = decl.get("lock", "") or ""
        teste = decl.get("teste", "") or ""
        esteira = decl.get("esteira") or repos.get(familia, {}).get("esteira", "codigo")
        if not lock:
            raise StackSemLock(nome, lock)
        return nome, familia, lock, teste, esteira

    if nome in repos:
        repo_decl = repos[nome]
        esteira = repo_decl.get("esteira", "codigo")
        stack_alvo = repo_decl.get("stack")
        if not stack_alvo:
            cands = [s for s, d in stacks.items() if isinstance(d, dict) and d.get("familia") == nome]
            sufixo = nome.replace("platafirma-", "")
            if sufixo in cands:
                stack_alvo = sufixo
            elif cands:
                stack_alvo = cands[0]
        if stack_alvo and stack_alvo in stacks:
            s_decl = stacks[stack_alvo]
            lock = s_decl.get("lock", "") or ""
            teste = s_decl.get("teste", "") or ""
            esteira = s_decl.get("esteira") or esteira
            if not lock:
                raise StackSemLock(stack_alvo, lock)
            return stack_alvo, nome, lock, teste, esteira
        else:
            lock = repo_decl.get("lock", "")
            # esteira documento nao tem venv: quem mede e a admissao da ingestao
            # (spec_teste §1, card #3152 passo 6), entao lock ausente nao e erro.
            if not lock and esteira != "documento":
                raise StackSemLock(nome, lock)
            return nome, nome, lock, repo_decl.get("teste", ""), esteira

    conhecidas = sorted(set(list(stacks.keys()) + list(repos.keys())))
    raise StackDesconhecida(nome, conhecidas)


def coleta(stack_real: str, caminho: Path | None = None) -> list[str]:
    """Globs de teste declarados em "testes" da stack (card #3316); [] sem declaração.

    Glob absoluto, com "..", com espaço ou vírgula, ou campo que não é lista de texto
    tornam o registro ilegível: a coleta errada não pode virar coleta do repositório.
    """
    stacks, _ = carregar_tudo(caminho)
    decl = stacks.get(stack_real)
    if not isinstance(decl, dict) or "testes" not in decl:
        return []
    globs = decl["testes"]
    if not isinstance(globs, list) or not all(isinstance(g, str) and g for g in globs):
        raise RegistroIlegivel(f"'testes' de '{stack_real}' não é lista de globs")
    for g in globs:
        if g.startswith("/") or ".." in g.split("/") or any(ch in g for ch in " \t,"):
            raise RegistroIlegivel(f"glob de teste inválido em '{stack_real}': '{g}'")
    return globs


def stack(nome: str, caminho: Path | None = None) -> tuple[str, str, str]:
    """(família, lock, subárvore de teste) da stack <nome>.

    Compatibilidade com chamadores antigos.
    """
    stack_real, familia, lock, teste, esteira = resolver(nome, caminho)
    return familia, lock, teste


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "--ajuda"):
        print(__doc__.strip())
        return 0
    if argv[0] == "--all":
        try:
            stacks, repos = carregar_tudo()
        except RegistroIlegivel as exc:
            print(f"registro: {exc}", file=sys.stderr)
            return 3
        except NomeDuplicado as exc:
            print(f"registro: stack com nome igual a repositório: '{exc.nome}' (stack '{exc.nome}', repositório '{exc.nome}')", file=sys.stderr)
            return 2
        for s_nome, s_decl in sorted(stacks.items()):
            fam = s_decl.get("familia", "")
            lock = s_decl.get("lock", "")
            teste = s_decl.get("teste", "")
            t_s = teste if teste else "-"
            esteira = s_decl.get("esteira") or repos.get(fam, {}).get("esteira", "codigo")
            print(f"{s_nome}\t{fam}\t{lock}\t{t_s}\t{esteira}")
        return 0
    if argv[0] == "--familia":
        if len(argv) != 2:
            print("erro: --familia exige exatamente <familia>", file=sys.stderr)
            return 2
        try:
            linhas = stacks_da_familia(argv[1])
        except RegistroIlegivel as exc:
            print(f"registro: {exc}", file=sys.stderr)
            return 3
        except NomeDuplicado as exc:
            print(f"registro: stack com nome igual a repositório: '{exc.nome}' (stack '{exc.nome}', repositório '{exc.nome}')", file=sys.stderr)
            return 2
        for nome, lock, teste in linhas:
            print(f"{nome}\t{lock}\t{teste}")
        return 0
    if len(argv) != 1:
        print("erro: um nome de stack ou repositório por chamada (ou --familia <familia>, --all)", file=sys.stderr)
        return 2
    try:
        stack_real, familia, lock, teste, esteira = resolver(argv[0])
        globs = coleta(stack_real)
    except RegistroIlegivel as exc:
        print(f"registro: {exc}", file=sys.stderr)
        return 3
    except NomeDuplicado as exc:
        print(f"registro: stack com nome igual a repositório: '{exc.nome}' (stack '{exc.nome}', repositório '{exc.nome}')", file=sys.stderr)
        return 2
    except StackDesconhecida as exc:
        print(f"registro: stack ou repositório desconhecido: {exc.nome}", file=sys.stderr)
        print("conhecidos: " + (", ".join(exc.conhecidas) or "(nenhum)"), file=sys.stderr)
        return 2
    except StackSemLock as exc:
        print(f"registro: stack '{exc.nome}' sem lock declarado em {caminho_registro()}", file=sys.stderr)
        return 5
    t_val = teste if teste else "-"
    # campo vazio vira "-": TAB e espaco em branco para o read do bash, e dois TABs
    # seguidos colapsariam, deslocando esteira e stack para a coluna errada.
    l_val = lock if lock else "-"
    g_val = ",".join(globs) if globs else "-"
    print(f"{familia}\t{l_val}\t{t_val}\t{esteira}\t{stack_real}\t{g_val}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
