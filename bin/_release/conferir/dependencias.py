#!/usr/bin/env python3
"""dependencias — o inventario do que as travas da casa penduram (card #3386).

`release conferir dependencias [<stack>] [--json]`. Uma linha por pacote de cada lock
declarado em registro/venvs.json (uv.lock, requirements, package-lock.json), lido da arvore
SERVIDA da familia (<release>/<familia>/current/<lock>): o que esta no ar, nao o que alguem
lembra. Nao e um artifactory e nao copia pacote: e o ROL do que as travas resolvem, para o
dono ler e para o gate saber o que barrar.

Veredito por pacote (3 estados, o mesmo contrato do `conferir`):
  conforme        versao fixada, vinda do registro oficial (npm ou PyPI), com a integridade
                  que o lock carrega
  divergente      versao nao fixada, fonte fora do registro oficial (git, url, caminho) ou
                  pacote do lock sem integridade — o que a trava nao prende
  indeterminavel  lock ausente na arvore servida ou ilegivel: nao consegui olhar

`--json` traz, alem dos itens, `pacotes`: stack, ecossistema, pacote, versao, direto
(pedido pela propria stack) ou transitivo, fonte, integridade (hash do lock, prefixo),
licenca (so quando o lock a carrega: o package-lock.json v3 carrega as vezes, o uv.lock
nunca — vazio e vazio, nao e livre) e se o pacote declara script de instalacao (que a
casa nunca roda: npm ci --ignore-scripts).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resultado  # noqa: E402

NPM_OFICIAL = "https://registry.npmjs.org/"
PYPI_OFICIAL = "https://pypi.org/simple"


def _linha(stack, eco, pacote, versao, direto, fonte, integridade, licenca="", script=False,
           problema=""):
    return {
        "stack": stack, "ecossistema": eco, "pacote": pacote, "versao": versao,
        "direto": direto, "fonte": fonte, "integridade": integridade,
        "licenca": licenca, "script_de_instalacao": script, "problema": problema,
    }


def _norm_py(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def ler_uv_lock(stack, caminho):
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)
    pacotes = dados.get("package") or []
    diretos = set()
    for p in pacotes:
        src = p.get("source") or {}
        if "virtual" in src or "editable" in src or "directory" in src:
            for d in p.get("dependencies") or []:
                diretos.add(_norm_py(d.get("name", "")))
            for lista in (p.get("optional-dependencies") or {}).values():
                for d in lista:
                    diretos.add(_norm_py(d.get("name", "")))
    saida = []
    for p in pacotes:
        src = p.get("source") or {}
        if "virtual" in src or "editable" in src or "directory" in src:
            continue  # o proprio projeto, nao dependencia
        nome, versao = p.get("name", "?"), p.get("version", "?")
        hashes = []
        if (p.get("sdist") or {}).get("hash"):
            hashes.append(p["sdist"]["hash"])
        hashes += [w["hash"] for w in p.get("wheels") or [] if w.get("hash")]
        integ = hashes[0].replace("sha256:", "")[:16] if hashes else ""
        problema = ""
        if src.get("registry") == PYPI_OFICIAL:
            fonte = "pypi.org"
        else:
            fonte = next(iter(src.values()), "?") if src else "?"
            problema = f"fonte fora do PyPI oficial: {fonte}"
        if not problema and not integ:
            problema = "o lock nao traz hash para este pacote"
        saida.append(_linha(stack, "pypi", nome, versao, _norm_py(nome) in diretos,
                            str(fonte), integ, problema=problema))
    return saida


_REQ = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==|>=|<=|~=|!=|>|<)?\s*([^\s;#\\]+)?")


def ler_requirements(stack, caminho):
    saida = []
    with open(caminho, encoding="utf-8") as f:
        texto = f.read().replace("\\\n", " ")
    for bruta in texto.splitlines():
        linha = bruta.split("#", 1)[0].strip()
        if not linha or linha.startswith(("-", "git+", "http")):
            if linha.startswith(("git+", "http")):
                saida.append(_linha(stack, "pypi", linha, "?", True, linha, "",
                                    problema="fonte fora do PyPI oficial (url ou git)"))
            continue
        m = _REQ.match(linha)
        if not m:
            continue
        nome, _extras, op, versao = m.groups()
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{16})", linha)
        problema = ""
        if op != "==" or not versao:
            problema = f"versao nao fixada ({op or 'sem'}{versao or ''}): a trava nao prende"
        saida.append(_linha(stack, "pypi", nome, versao or "?", True, "pypi.org",
                            hashes[0] if hashes else "", problema=problema))
    return saida


def ler_package_lock(stack, caminho):
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    if int(dados.get("lockfileVersion", 0)) < 2 or "packages" not in dados:
        raise ValueError("package-lock.json sem `packages` (lockfileVersion 1): nao consigo ler")
    pacotes = dados["packages"]
    raiz = pacotes.get("") or {}
    diretos = set()
    for chave in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        diretos.update((raiz.get(chave) or {}).keys())
    saida = []
    for chave, info in pacotes.items():
        if not chave or not isinstance(info, dict):
            continue
        if info.get("link"):
            continue  # workspace: codigo da propria casa
        nome = info.get("name") or chave.rsplit("node_modules/", 1)[-1]
        resolvido = info.get("resolved", "")
        integ = (info.get("integrity") or "")
        problema = ""
        if not resolvido.startswith(NPM_OFICIAL):
            problema = f"fonte fora do registro oficial do npm: {resolvido or 'sem resolved'}"
        elif not integ:
            problema = "o lock nao traz integridade para este pacote"
        lic = info.get("license", "")
        if isinstance(lic, (list, dict)):
            lic = json.dumps(lic, ensure_ascii=False)
        saida.append(_linha(
            stack, "npm", nome, info.get("version", "?"), nome in diretos,
            "registry.npmjs.org" if resolvido.startswith(NPM_OFICIAL) else resolvido,
            integ.split("-", 1)[-1][:16] if integ else "", lic,
            bool(info.get("hasInstallScript")), problema))
    return saida


def _leitor(caminho):
    base = os.path.basename(caminho)
    if base == "uv.lock":
        return ler_uv_lock
    if base == "package-lock.json":
        return ler_package_lock
    return ler_requirements


def _stacks(registro):
    with open(registro, encoding="utf-8") as f:
        dados = json.load(f)
    brutas = dados.get("stacks") if isinstance(dados.get("stacks"), dict) else {
        k: v for k, v in dados.items() if not k.startswith("_") and k != "repositorios"}
    return {k: v for k, v in brutas.items() if isinstance(v, dict) and v.get("lock")}


def levantar(alvo, registro, prod_raiz):
    """([(nome do item, Veredito)], [linhas de pacote]) das stacks do registro."""
    itens, linhas = [], []
    for stack, decl in sorted(_stacks(registro).items()):
        if alvo and alvo != stack:
            continue
        caminho = os.path.join(prod_raiz, decl.get("familia", ""), "current", decl["lock"])
        desde = None
        if not os.path.isfile(caminho):
            itens.append((f"{stack} · lock", resultado.indeterminavel(
                f"{decl['lock']} ausente na release servida de {decl.get('familia')}: "
                "stack declarada e nao servida")))
            continue
        try:
            desde = str(os.path.realpath(os.path.join(prod_raiz, decl["familia"], "current"))
                        ).rsplit(os.sep, 1)[-1][:7]
            pacotes = _leitor(caminho)(stack, caminho)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            itens.append((f"{stack} · lock", resultado.indeterminavel(
                f"{decl['lock']} ilegivel: {exc}")))
            continue
        for p in sorted(pacotes, key=lambda x: (x["pacote"].lower(), x["versao"])):
            nome = f"{stack} · {p['ecossistema']} · {p['pacote']} {p['versao']}"
            if p["problema"]:
                itens.append((nome, resultado.divergente(p["problema"], desde=desde)))
            else:
                itens.append((nome, resultado.conforme(desde=desde)))
            linhas.append(p)

    # Travas que a casa tem e a release NAO constroi (a platafirma-ui instala as dela por
    # Docker ou a mao): entram no rol com o rotulo <familia>:<pasta>, para o inventario ser o
    # que ha na maquina e nao so o que o registro declara. Nao sao stack; nao ha ambiente.
    declaradas = {(d.get("familia"), d["lock"]) for d in _stacks(registro).values()}
    for familia, rel, caminho in _descobrir(registro, prod_raiz, declaradas):
        rotulo = f"{familia}:{os.path.dirname(rel) or '.'}"
        if alvo and alvo != rotulo:
            continue
        try:
            pacotes = _leitor(caminho)(rotulo, caminho)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            itens.append((f"{rotulo} · lock", resultado.indeterminavel(f"{rel} ilegivel: {exc}")))
            continue
        desde = str(os.path.realpath(os.path.join(prod_raiz, familia, "current"))).rsplit(os.sep, 1)[-1][:7]
        for p in sorted(pacotes, key=lambda x: (x["pacote"].lower(), x["versao"])):
            p["construido_pela_release"] = False
            nome = f"{rotulo} · {p['ecossistema']} · {p['pacote']} {p['versao']}"
            if p["problema"]:
                itens.append((nome, resultado.divergente(p["problema"], desde=desde)))
            else:
                itens.append((nome, resultado.conforme(desde=desde)))
            linhas.append(p)
    return itens, linhas


_PULAR = {"node_modules", ".git", "__pycache__", ".venv", "venv", ".tox"}


def _descobrir(registro, prod_raiz, declaradas):
    """(familia, caminho relativo, caminho absoluto) de uv.lock e package-lock.json na arvore
    servida de cada familia de codigo, fora os que o registro ja declara como stack."""
    with open(registro, encoding="utf-8") as f:
        dados = json.load(f)
    familias = {d.get("familia") for d in _stacks(registro).values()}
    for nome, decl in (dados.get("repositorios") or {}).items():
        if isinstance(decl, dict) and decl.get("esteira") != "documento":
            familias.add(nome)
    for familia in sorted(x for x in familias if x):
        raiz = os.path.join(prod_raiz, familia, "current")
        if not os.path.isdir(raiz):
            continue
        real = os.path.realpath(raiz)
        for dp, dns, fns in os.walk(real):
            dns[:] = sorted(d for d in dns if d not in _PULAR)
            for fn in sorted(fns):
                if fn in ("uv.lock", "package-lock.json"):
                    rel = os.path.relpath(os.path.join(dp, fn), real)
                    if (familia, rel) not in declaradas:
                        yield familia, rel, os.path.join(dp, fn)


def conferir(alvo, como_json, sha_release, registro, prod_raiz):
    if not os.path.isfile(registro):
        msg = f"registro de venvs ausente: {registro}"
        print(json.dumps({"erro": msg}) if como_json else msg, file=sys.stderr if not como_json else sys.stdout)
        return 5
    itens, linhas = levantar(alvo, registro, prod_raiz)
    if alvo and not itens:
        msg = f"stack {alvo!r} nao declarada em registro/venvs.json (nem trava <familia>:<pasta> na release)"
        print(json.dumps({"erro": msg}) if como_json else msg)
        return 1
    return resultado.relatorio("dependencias", alvo, itens, sha_release, como_json=como_json,
                               extra={"pacotes": linhas} if como_json else None)
