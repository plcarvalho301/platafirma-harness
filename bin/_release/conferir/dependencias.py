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

`--avisos` (opt-in, usa rede) cruza o rol com o OSV: pacote e versao do lock com aviso aberto
vira divergente, com o id (GHSA, PYSEC...), a gravidade, o resumo e a versao em que foi corrigido.
Nao entra no gate de promocao: aviso novo nao deve barrar mudanca que nao e dele. OSV fora do
ar e indeterminavel (exit 5), nunca "sem aviso". Em `--json`, cada pacote ganha `avisos`.

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


_URL = re.compile(r"^(git\+|[a-z][a-z0-9+.-]*://)", re.IGNORECASE)
_REQ = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==|>=|<=|~=|!=|>|<)?\s*([^\s;#\\]+)?")


def ler_requirements(stack, caminho):
    saida = []
    with open(caminho, encoding="utf-8") as f:
        texto = f.read().replace("\\\n", " ")
    for bruta in texto.splitlines():
        linha = bruta.split("#", 1)[0].strip()
        if not linha or linha.startswith("-"):
            continue
        if _URL.match(linha):          # url ou git: "httpx>=0.27" NAO e url (medido no host em 10/10)
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


_SCRIPT_FERRAMENTAL = r'''
. "$1"; PF_VENV_PREFIXO=dependencias
v() { timeout 10 "$@" 2>&1 </dev/null | head -n 1; }
limpa() { printf '%s' "$1" | tr '\n\t' '  '; }
if n="$(resolver_node 2>&1)"; then
  p="${n%%$'\t'*}"; printf 'node\t%s\t%s\n' "$p" "$(v "$p" --version)"
  if np="$(resolver_npm "$p" 2>&1)"; then
    printf 'npm\t%s\t%s\n' "$np" "$(PATH="$(dirname "$p"):$PATH" v "$np" --version)"
  else printf 'npm\t-\t%s\n' "$(limpa "$np")"; fi
else printf 'node\t-\t%s\n' "$(limpa "$n")"; fi
if u="$(resolver_uv 2>&1)"; then printf 'uv\t%s\t%s\n' "$u" "$(v "$u" --version)"
else printf 'uv\t-\t%s\n' "$(limpa "$u")"; fi
if py="$(resolver_python 2>&1)"; then printf 'python\t%s\t%s\n' "${py%%$'\t'*}" "${py##*$'\t'}"
else printf 'python\t-\t%s\n' "$(limpa "$py")"; fi
if c="$(resolver_chromium 2>&1)"; then printf 'chromium\t%s\t%s\n' "$c" "$(v "$c" --version)"
else printf 'chromium\t-\t%s\n' "$(limpa "$c")"; fi
'''


def ferramental(harness):
    """[{ferramenta, caminho, versao}] do que o host resolve para node, npm, uv, python e chromium,
    pelas MESMAS funcoes de lib/venv.sh que constroem o ambiente. Ausente ou recusado sai com o
    motivo no lugar da versao: nao se omite."""
    import subprocess
    venv = os.path.join(harness, "lib", "venv.sh")
    if not os.path.isfile(venv):
        return [{"ferramenta": "?", "caminho": "-", "versao": f"nao li {venv}"}]
    try:
        r = subprocess.run(["bash", "-c", _SCRIPT_FERRAMENTAL, "_", venv], capture_output=True,
                           text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [{"ferramenta": "?", "caminho": "-", "versao": f"nao consegui olhar: {exc}"}]
    saida = []
    for linha in r.stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) == 3:
            saida.append({"ferramenta": partes[0], "caminho": partes[1], "versao": partes[2]})
    return saida


def _celula(texto) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ") or "—"


def markdown(itens, linhas, sha_release, quando, alvo=None, ferr=None):
    """O rol em Markdown, para o dono ler: um retrato datado, derivado das travas (que seguem
    sendo a fonte). Licenca so aparece quando o lock a carrega."""
    por_stack: dict[str, list] = {}
    for p in linhas:
        por_stack.setdefault(p["stack"], []).append(p)
    divergentes = [(n, v) for n, v in itens if v.estado == "divergente"]
    indeterminaveis = [(n, v) for n, v in itens if v.estado == "indeterminavel"]
    npm = sum(1 for p in linhas if p["ecossistema"] == "npm")
    pypi = len(linhas) - npm
    com_licenca = sum(1 for p in linhas if p["licenca"])
    scripts = [p for p in linhas if p["script_de_instalacao"]]
    soltas = sorted(s for s, ps in por_stack.items() if not ps[0].get("construido_pela_release", True))
    data = quando[:10]
    saida = [
        f"# Dependências das travas da casa em {data}: o que cada trava resolve",
        "",
        "Espécie: relatorio",
        "",
        "- **Dono:** ti (Oswaldo Aranha)",
        f"- **Gerado por:** `release conferir dependencias{' ' + alvo if alvo else ''} --md-para <arquivo>`, "
        f"sobre a release {sha_release}, em {quando}",
        "- **Estado:** retrato. A fonte é cada trava no git (`uv.lock`, `package-lock.json`, "
        "requirements); para refazer, rode o mesmo verbo e comite o arquivo novo.",
        "",
        "## 1. Em uma tela",
        "",
        "| o que | quanto |",
        "|---|---|",
        f"| travas lidas | {len(por_stack)} |",
        f"| pacotes resolvidos | {len(linhas)} (npm {npm} · PyPI {pypi}) |",
        f"| pedidos pela própria stack (diretos) | {sum(1 for p in linhas if p['direto'])} |",
        f"| o que a trava não prende (divergente) | {len(divergentes)} |",
        f"| travas que não consegui ler | {len(indeterminaveis)} |",
        f"| pacotes npm que declaram script de instalação | {len(scripts)} (a casa não roda: `npm ci --ignore-scripts`) |",
        f"| com licença no lock | {com_licenca} de {len(linhas)} (só o `package-lock.json` a carrega; "
        "`uv.lock` e requirements não: vazio é vazio, não é livre) |",
        f"| travas que a release não constrói | {', '.join(f'`{s}`' for s in soltas) or 'nenhuma'} |",
        "",
        "## 2. O que a trava não prende",
        "",
    ]
    if divergentes:
        saida += ["| item | por quê |", "|---|---|"]
        saida += [f"| {_celula(n)} | {_celula(v.motivo)} |" for n, v in divergentes]
    else:
        saida.append("Nenhum: todo pacote lido tem versão fixada, fonte oficial e integridade no lock.")
    if indeterminaveis:
        saida += ["", "Não consegui olhar:", "", "| item | por quê |", "|---|---|"]
        saida += [f"| {_celula(n)} | {_celula(v.motivo)} |" for n, v in indeterminaveis]
    saida += ["", "## 3. O que o host resolve (fora das travas)", "",
              "Resolvido pelas mesmas funções de `lib/venv.sh` que constroem o ambiente. Ausente ou recusado "
              "aparece com o motivo no lugar da versão.", ""]
    if ferr:
        saida += ["| ferramenta | caminho | versão ou motivo |", "|---|---|---|"]
        saida += [f"| {_celula(f['ferramenta'])} | {_celula(f['caminho'])} | {_celula(f['versao'])} |" for f in ferr]
    else:
        saida.append("Não consultado nesta rodada.")
    saida += ["", "## 4. Por trava", ""]
    for stack in sorted(por_stack):
        ps = sorted(por_stack[stack], key=lambda p: (not p["direto"], p["pacote"].lower(), p["versao"]))
        construida = ps[0].get("construido_pela_release", True)
        saida += [
            f"### `{stack}`: {len(ps)} pacotes, {sum(1 for p in ps if p['direto'])} pedidos pela stack",
            "",
            "Ambiente construído pela release: " + ("sim" if construida else "não (trava no git, instalada à mão ou por Docker)"),
            "",
            "| pacote | versão | pedido | fonte | integridade (início do hash) | licença | script |",
            "|---|---|---|---|---|---|---|",
        ]
        for p in ps:
            saida.append(
                f"| {_celula(p['pacote'])} | {_celula(p['versao'])} | {'direto' if p['direto'] else 'transitivo'} "
                f"| {_celula(p['fonte'])} | {_celula(p['integridade'])} | {_celula(p['licenca'])} "
                f"| {'declara' if p['script_de_instalacao'] else '—'} |")
        saida.append("")
    return "\n".join(saida)


def escrever_md(destino, raiz_permitida, itens, linhas, sha_release, alvo=None, ferr=None):
    """Grava o Markdown em `destino`, que tem de ser .md absoluto dentro de `raiz_permitida` (a
    bancada declarada): a classe so olha, e esta e a unica escrita, opt-in e contida. 0 ok, 4 recusa."""
    import datetime
    real = os.path.realpath(os.path.dirname(destino) or ".")
    raiz = os.path.realpath(raiz_permitida)
    if not os.path.isabs(destino) or not destino.endswith(".md") \
            or not (real == raiz or real.startswith(raiz + os.sep)):
        print(f"dependencias: --md-para recusado: {destino!r} tem de ser um .md absoluto sob a bancada {raiz}",
              file=sys.stderr)
        return 4
    quando = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(real, exist_ok=True)
    tmp = destino + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(markdown(itens, linhas, sha_release, quando, alvo, ferr))
    os.replace(tmp, destino)
    print(f"dependencias: Markdown escrito em {destino}", file=sys.stderr)
    return 0


# --- avisos de seguranca (feature #3388) --------------------------------------------------
# `--avisos` cruza o rol com o OSV (osv.dev: GHSA, PyPA, RustSec...), que responde por pacote e
# versao exatos do lock. E opt-in porque usa rede e porque aviso novo apareceria como barreira
# em promocao que nao tem nada a ver com ele: o gate de promocao nao o chama.
OSV_BASE = "https://api.osv.dev"
_ECO_OSV = {"npm": "npm", "pypi": "PyPI"}
_ID_OSV = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")

def _osv_http(metodo, caminho, corpo=None):
    """JSON de resposta do OSV; levanta OSError (rede, HTTP ou corpo que nao e JSON)."""
    import urllib.request
    url = (os.environ.get("PF_OSV_URL") or OSV_BASE).rstrip("/") + caminho
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={
        "Content-Type": "application/json", "User-Agent": "platafirma-conferir-dependencias"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (OSError, ValueError) as exc:
        raise OSError(f"OSV {metodo} {caminho}: {exc}") from exc

def _corrigido(detalhe, eco, nome):
    """Versoes em que o aviso foi corrigido para ESTE pacote, como o OSV as publica."""
    alvo = _norm_py(nome) if eco == "pypi" else nome
    fixas = []
    for a in detalhe.get("affected") or []:
        pkg = a.get("package") or {}
        n = pkg.get("name", "")
        if (_norm_py(n) if eco == "pypi" else n) != alvo:
            continue
        for faixa in a.get("ranges") or []:
            for ev in faixa.get("events") or []:
                if ev.get("fixed") and ev["fixed"] not in fixas:
                    fixas.append(ev["fixed"])
    return ", ".join(fixas[:5]) if fixas else "sem correcao publicada"

def consultar_avisos(linhas, osv=None):
    """{(ecossistema, pacote, versao): [{id, resumo, gravidade, corrigido_em}]} dos pacotes do
    rol com aviso aberto (retirado nao conta). `osv(metodo, caminho, corpo)` devolve o JSON da
    resposta e levanta OSError; o padrao fala com o OSV. Nao responde por pacote sem versao
    fixada ("?"): nao ha o que perguntar."""
    osv = osv or _osv_http
    chaves = sorted({(p["ecossistema"], p["pacote"], p["versao"]) for p in linhas
                     if p["ecossistema"] in _ECO_OSV and p["versao"] not in ("", "?")})
    ids_de = {}
    for i in range(0, len(chaves), 500):
        lote = chaves[i:i + 500]
        resp = osv("POST", "/v1/querybatch", {"queries": [
            {"package": {"name": n, "ecosystem": _ECO_OSV[e]}, "version": v} for e, n, v in lote]})
        resultados = resp.get("results") or []
        if len(resultados) != len(lote):
            raise OSError(f"OSV devolveu {len(resultados)} resultados para {len(lote)} consultas")
        for (e, n, v), r in zip(lote, resultados):
            r = r or {}
            ids = [x["id"] for x in r.get("vulns") or [] if x.get("id")]
            token = r.get("next_page_token")
            while token:  # resposta paginada: o resto do mesmo pacote e versao
                pag = osv("POST", "/v1/query", {"package": {"name": n, "ecosystem": _ECO_OSV[e]},
                                                "version": v, "page_token": token})
                ids += [x["id"] for x in pag.get("vulns") or [] if x.get("id")]
                token = pag.get("next_page_token")
            if ids:
                ids_de[(e, n, v)] = ids
    detalhes, saida = {}, {}
    for (e, n, v), ids in ids_de.items():
        lista = []
        for vid in sorted(set(ids)):
            if not _ID_OSV.match(vid):
                continue
            if vid not in detalhes:
                detalhes[vid] = osv("GET", "/v1/vulns/" + vid, None)
            d = detalhes[vid]
            if d.get("withdrawn"):
                continue
            lista.append({
                "id": vid, "resumo": (d.get("summary") or "").strip(),
                "gravidade": str((d.get("database_specific") or {}).get("severity") or ""),
                "corrigido_em": _corrigido(d, e, n)})
        if lista:
            saida[(e, n, v)] = lista
    return saida

def _aplicar_avisos(itens, linhas, achados):
    """Marca cada pacote do rol com seus avisos e vira divergente o item que tem algum."""
    por_nome = {}
    for p in linhas:
        lista = achados.get((p["ecossistema"], p["pacote"], p["versao"]), [])
        p["avisos"] = lista
        if lista:
            por_nome[f"{p['stack']} · {p['ecossistema']} · {p['pacote']} {p['versao']}"] = lista
    novos = []
    for nome, v in itens:
        lista = por_nome.get(nome)
        if lista:
            texto = "; ".join(
                f"{a['id']}{' (' + a['gravidade'] + ')' if a['gravidade'] else ''}: "
                f"{a['resumo'] or 'sem resumo'} — corrigido em {a['corrigido_em']}" for a in lista)
            antes = getattr(v, "motivo", "") if getattr(v, "estado", "") == "divergente" else ""
            v = resultado.divergente(f"{antes}; {texto}" if antes else f"aviso de seguranca {texto}",
                                     desde=getattr(v, "desde", None))
        novos.append((nome, v))
    return novos

def conferir(alvo, como_json, sha_release, registro, prod_raiz, md_para=None, raiz_permitida=None,
             harness=None, avisos=False, osv=None):
    if not os.path.isfile(registro):
        msg = f"registro de venvs ausente: {registro}"
        print(json.dumps({"erro": msg}) if como_json else msg, file=sys.stderr if not como_json else sys.stdout)
        return 5
    itens, linhas = levantar(alvo, registro, prod_raiz)
    if alvo and not itens:
        msg = f"stack {alvo!r} nao declarada em registro/venvs.json (nem trava <familia>:<pasta> na release)"
        print(json.dumps({"erro": msg}) if como_json else msg)
        return 1
    if avisos:
        try:
            itens = _aplicar_avisos(itens, linhas, consultar_avisos(linhas, osv))
        except OSError as exc:
            msg = f"consulta de avisos falhou, nao consegui olhar: {exc}"
            print(json.dumps({"erro": msg}) if como_json else f"dependencias: {msg}",
                  file=sys.stdout if como_json else sys.stderr)
            return 5
    ferr = ferramental(harness) if harness and (md_para or como_json) else None
    if md_para:
        rc_md = escrever_md(md_para, raiz_permitida or "/nao-declarada", itens, linhas, sha_release, alvo, ferr)
        if rc_md:
            return rc_md
    extra = {"pacotes": linhas, "ferramental": ferr or []} if como_json else None
    return resultado.relatorio("dependencias", alvo, itens, sha_release, como_json=como_json, extra=extra)
