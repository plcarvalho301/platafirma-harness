"""Confinamento de caminhos por morada, negativas e lista de extensões (achado 921).

Fonte única de verdade para a camada de leitura (`lib/leitura`) e de escrita
(`lib/escrita`) do harness na casa nova, preservando integralmente a
funcionalidade das duas tools enquanto restringe o alcance às moradas
declaradas (spec porta-so-verbo §§4.1 e 4.6; spec ler-arquivo §9).
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

_NOMES_SEGREDO = frozenset(
    {
        ".credentials.json",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "authorized_keys",
        ".netrc",
        ".pgpass",
        ".git-credentials",
    }
)
_SUFIXOS_SEGREDO = frozenset({".key", ".pem", ".asc", ".kdbx"})

TIPOS_TEXTO = frozenset(
    {
        ".py",
        ".md",
        ".mmd",
        ".d2",
        ".sh",
        ".sql",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".css",
        ".html",
        ".svg",
        ".js",
        ".jsx",
        ".mjs",
        ".ts",
        ".tsx",
        ".php",
        ".txt",
        ".conf",
        ".tsv",
        ".service",
        ".timer",
        ".path",
        ".socket",
        ".ttl",
        ".jsonl",
    }
)
NOMES_TEXTO = frozenset(
    {
        "Dockerfile",
        ".dockerignore",
        ".gitignore",
        ".operacao",
        "VERDES",
        ".conferir-repo",
        "uv.lock",
        "crontab-claudinho",
    }
)
PREFIXO_DOCKERFILE = "Dockerfile."
TIPOS_ENTRADA = frozenset({".csv"})

CLONES = (
    "platafirma-core",
    "platafirma-conhecimento",
    "platafirma-harness",
    "platafirma-motor",
    "platafirma-posto",
    "platafirma-ui",
    "platafirma-casa",
    "platafirma-rastreador",
    "platafirma-casa-espelho",
)
ESCRITA_TETO = 1_048_576
_SEM_BANCADA = (
    "fora de morada: bancada nao declarada — configure PLATAFIRMA_BANCADA ou "
    "~/.config/platafirma/bancada"
)


def _real(p: Path) -> Path:
    try:
        return p.resolve(strict=False)
    except OSError:
        return p


def _sob(alvo: str, raiz: str) -> bool:
    return alvo == raiz or alvo.startswith(raiz.rstrip(os.sep) + os.sep)


def bancada(bancada_dir: Path | None = None) -> Path | None:
    """Retorna a raiz da bancada declarada pela conta, ou None se não declarada."""
    if bancada_dir is not None:
        return Path(bancada_dir)
    env_b = (os.environ.get("PLATAFIRMA_BANCADA") or "").strip()
    if env_b:
        return Path(env_b)
    arq_env = (os.environ.get("PLATAFIRMA_ARQUIVO_BANCADA") or "").strip()
    arq = Path(arq_env) if arq_env else (Path.home() / ".config" / "platafirma" / "bancada")
    if arq.is_file():
        try:
            for ln in arq.read_text(encoding="utf-8").splitlines():
                s = ln.strip()
                if s and not s.startswith("#"):
                    return Path(s)
        except OSError:
            return None
    return None


def release_raiz(release_dir: Path | None = None) -> Path:
    if release_dir is not None:
        return Path(release_dir)
    return Path(os.environ.get("PLATAFIRMA_RELEASE_RAIZ", "/opt/platafirma"))


def instancia_raiz(instancia: Path | None = None) -> Path:
    if instancia is not None:
        return Path(instancia)
    return Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))


def _pdp_raizes(pdp: Path | None = None, release_dir: Path | None = None) -> tuple[Path, ...]:
    cands: list[Path] = []
    if pdp is not None:
        cands.append(Path(pdp))
    env_pdp = (os.environ.get("PDP_DIR") or "").strip()
    if env_pdp:
        cands.append(Path(env_pdp))
    rel = release_raiz(release_dir)
    cands.append(rel / "current" / "politica-acesso")
    cands.append(rel / "current" / "core" / "acesso")
    unicas: list[Path] = []
    vistas: set[str] = set()
    for c in cands:
        for v in (c, _real(c)):
            s = str(v)
            if s not in vistas:
                vistas.add(s)
                unicas.append(v)
    return tuple(unicas)


def eh_segredo(
    caminho: Path,
    *,
    instancia: Path | None = None,
    pdp: Path | None = None,
    release_dir: Path | None = None,
) -> bool:
    """Negativa de segredos e política de acesso (vence morada e inexistência)."""
    alvo = _real(caminho)
    for cand in (caminho, alvo):
        nome = cand.name
        if (
            nome.startswith(".env")
            or cand.suffix.lower() in _SUFIXOS_SEGREDO
            or nome in _NOMES_SEGREDO
        ):
            return True

    inst = instancia_raiz(instancia)
    seg_inst = inst / "segredos"
    for cand in (alvo, caminho.absolute()):
        cand_s = str(cand)
        for seg_raiz in (seg_inst, _real(seg_inst)):
            if _sob(cand_s, str(seg_raiz)):
                return True
        for pdp_r in _pdp_raizes(pdp=pdp, release_dir=release_dir):
            if _sob(cand_s, str(pdp_r)):
                return True

    raizes_inst = [Path("/srv/platafirma")]
    if instancia is not None:
        raizes_inst.append(instancia.parent)
    for base in raizes_inst:
        for cand in (alvo, caminho.absolute()):
            try:
                partes = cand.relative_to(base).parts
            except ValueError:
                continue
            if len(partes) >= 2 and partes[1] == "segredos":
                return True
    return False


def sob_fila(caminho: Path, *, instancia: Path | None = None) -> bool:
    base = instancia_raiz(instancia) / "var" / "fila"
    alvo = _real(caminho)
    fila_real = _real(base)
    return alvo == fila_real or fila_real in alvo.parents


def moradas_leitura(
    *,
    instancia: Path | None = None,
    release_dir: Path | None = None,
) -> tuple[str, ...]:
    """Raízes estáticas da morada de leitura: release e instância (resolvidas)."""
    rel = release_raiz(release_dir)
    inst = instancia_raiz(instancia)
    return tuple(dict.fromkeys(os.path.realpath(r) for r in (rel, inst)))


def resolver_leitura_relativo(
    caminho: str,
    *,
    bancada_dir: Path | None = None,
    cadeira: str = "",
) -> tuple[Path | None, str | None]:
    """Resolve caminho relativo de leitura a partir da bancada declarada."""
    p = Path(caminho)
    if p.is_absolute():
        return p, None
    b = bancada(bancada_dir)
    if b is None:
        return None, _SEM_BANCADA
    partes = PurePosixPath(caminho).parts
    cad = (cadeira or "").strip()
    if cad and partes and partes[0] not in ("wt", "entrada", ".", ".."):
        repo = partes[0]
        resto = partes[1:]
        wt_main = b / "wt" / repo / cad / "main"
        if wt_main.is_dir():
            return wt_main.joinpath(*resto), None
        wt_cad = b / "wt" / repo / cad
        if wt_cad.is_dir():
            wts = sorted(d for d in wt_cad.iterdir() if d.is_dir() and (d / ".git").exists())
            if len(wts) == 1:
                return wts[0].joinpath(*resto), None
    return b / p, None


def nega_morada_leitura(
    caminho: Path,
    *,
    instancia: Path | None = None,
    bancada_dir: Path | None = None,
    release_dir: Path | None = None,
) -> str | None:
    """Retorna None se `caminho` (resolvido) está na morada de leitura, senão o motivo."""
    alvo_s = os.path.realpath(caminho)
    estaticas = moradas_leitura(instancia=instancia, release_dir=release_dir)
    b = bancada(bancada_dir)
    raiz_bancada = os.path.realpath(b) if b is not None else None
    if any(_sob(alvo_s, r) for r in estaticas) or (
        raiz_bancada is not None and _sob(alvo_s, raiz_bancada)
    ):
        return None
    moradas = ", ".join((*estaticas, raiz_bancada or "(bancada nao declarada)"))
    return f"fora de morada: ler_arquivo alcanca so {moradas} (spec porta-so-verbo §4.6)"


def _nome_texto(nome: str) -> bool:
    return nome in NOMES_TEXTO or (
        nome.startswith(PREFIXO_DOCKERFILE) and len(nome) > len(PREFIXO_DOCKERFILE)
    )


def _negadas_escrita(
    *,
    instancia: Path | None = None,
    release_dir: Path | None = None,
) -> dict[Path, str]:
    inst = instancia_raiz(instancia)
    rel = release_raiz(release_dir)
    return {
        rel: "release e imutavel — muda por `release promover`, nunca por escrita",
        inst / "var" / "fila": "use o verbo `fila` (append sob flock, com identidade)",
        inst / "var" / "log": "log nao se edita",
        inst / "segredos": "segredo se grava por `seg segredo gravar`",
    }


def _clones_na_bancada(b: Path) -> list[str]:
    nomes = list(CLONES)
    for raiz in (b, b / "wt"):
        if raiz.is_dir():
            try:
                for p in sorted(raiz.iterdir()):
                    if p.is_dir() and p.name.startswith("platafirma-") and p.name not in nomes:
                        nomes.append(p.name)
            except OSError:
                pass
    return nomes


def _moradas_escrita(
    *,
    instancia: Path | None = None,
    bancada_dir: Path | None = None,
) -> list[tuple[Path, frozenset[str]]]:
    tmp_fita = _real(instancia_raiz(instancia) / "var" / "tmp")
    moradas: list[tuple[Path, frozenset[str]]] = [(tmp_fita, TIPOS_TEXTO)]
    b = bancada(bancada_dir)
    if b is not None:
        b_real = _real(b)
        clones = _clones_na_bancada(b_real)
        moradas += [(b_real / "wt" / c, TIPOS_TEXTO) for c in clones]
        moradas += [(b_real / c, TIPOS_TEXTO) for c in clones]
        moradas.append((b_real / "entrada", TIPOS_ENTRADA))
    return moradas


def _em_bin_do_harness(real_pai: Path, b: Path | None) -> bool:
    if b is None:
        return False
    b_real = _real(b)
    dirs_harness = ("bin", "hooks", "deploy-harness")
    for raiz_clone, profs, miolo, dirs in (
        (b_real / "platafirma-harness", (0,), (), dirs_harness),
        (b_real / "wt" / "platafirma-harness", (1, 2), (), dirs_harness),
        (b_real / "platafirma-posto", (0,), (), ("bin",)),
        (b_real / "wt" / "platafirma-posto", (1, 2), (), ("bin",)),
    ):
        try:
            partes = real_pai.relative_to(raiz_clone).parts
        except ValueError:
            continue
        n = len(miolo)
        if any(
            len(partes) > p + n and partes[p : p + n] == miolo and partes[p + n] in dirs
            for p in profs
        ):
            return True
    return False


def _clone_ausente(raiz: Path, real_pai: Path) -> str | None:
    rel = real_pai.relative_to(raiz).parts
    if raiz.parent.name == "wt":
        if not rel:
            return f"morada: {raiz}/<cadeira>/<card-ou-slug>/<arquivo> — worktree da cadeira e obrigatorio"
        base = raiz / rel[0]
    else:
        base = raiz
    if not base.is_dir():
        if raiz.name == "entrada":
            return f"fora de morada: {base}/ nao existe"
        return (
            f"fora de morada: {base}/ nao existe — clone e worktree nascem por "
            f"`repo abrir {raiz.name}`, write_file nao os cria"
        )
    return None


def _resolve_escrita_relativo(
    pp: PurePosixPath,
    *,
    bancada_dir: Path | None = None,
    cadeira: str = "",
) -> tuple[Path | None, str | None]:
    if pp.is_absolute():
        return Path(str(pp)), None
    b = bancada(bancada_dir)
    if b is None:
        return None, _SEM_BANCADA
    partes = pp.parts
    cad = (cadeira or "").strip()
    if cad and partes and partes[0] not in ("wt", "entrada", ".", ".."):
        repo = partes[0]
        resto = partes[1:]
        wt_cad = b / "wt" / repo / cad
        wt_main = wt_cad / "main"
        if wt_main.is_dir():
            return wt_main.joinpath(*resto), None
        if wt_cad.is_dir():
            wts = sorted(d for d in wt_cad.iterdir() if d.is_dir() and (d / ".git").exists())
            if len(wts) == 1:
                return wts[0].joinpath(*resto), None
            if len(wts) > 1:
                chaves = ", ".join(d.name for d in wts)
                return None, (
                    f"fora de morada: ha mais de uma bancada aberta de '{repo}' para '{cad}' "
                    f"({chaves}) — use wt/{repo}/{cad}/<chave>/<arquivo>"
                )
        if (b / repo).is_dir():
            return None, (
                f"fora de morada: '{pp}' grava no clone compartilhado ({b / repo}/), "
                f"nao na bancada de '{cad}' — abra com 'repo abrir {repo}' ou use "
                f"wt/{repo}/{cad}/..."
            )
    return b / Path(str(pp)), None


def resolver_escrita(
    path: str,
    *,
    instancia: Path | None = None,
    bancada_dir: Path | None = None,
    release_dir: Path | None = None,
    pdp: Path | None = None,
    cadeira: str = "",
    ordem_id: str = "",
) -> tuple[Path | None, str | None, bool]:
    """Valida e resolve destino de escrita: `(alvo_real, erro, exige_shebang)`.

    Ordem: léxico -> relativo -> realpath do pai -> segredo/negativas ->
    morada -> extensão/nome -> existência de clone/fita -> symlink no alvo.
    """
    pp = PurePosixPath(path or "")
    partes = pp.parts
    if not partes or ".." in partes or any(ord(ch) < 32 for ch in path):
        return (
            None,
            "caminho: absoluto ou relativo a bancada, sem '..' nem caractere de controle",
            False,
        )
    if ".git" in partes:
        return None, "fora de morada: .git nao se escreve por write_file — use `repo`", False

    alvo, erro = _resolve_escrita_relativo(pp, bancada_dir=bancada_dir, cadeira=cadeira)
    if erro or alvo is None:
        return None, erro or _SEM_BANCADA, False

    if eh_segredo(alvo, instancia=instancia, pdp=pdp, release_dir=release_dir):
        return None, "segredo: escrita recusada", False

    pai = alvo.parent
    anc = pai
    while not anc.exists():
        anc = anc.parent
    try:
        real_pai = anc.resolve() / pai.relative_to(anc)
    except OSError as exc:
        return None, f"caminho: {exc}", False

    for neg, porque in _negadas_escrita(instancia=instancia, release_dir=release_dir).items():
        for n in dict.fromkeys((neg, _real(neg))):
            if real_pai == n or n in real_pai.parents:
                return None, f"fora de morada: {neg}/ — {porque}", False

    ext = alvo.suffix.lower()
    tmp_fita = _real(instancia_raiz(instancia) / "var" / "tmp")
    b = bancada(bancada_dir)
    moradas = _moradas_escrita(instancia=instancia, bancada_dir=bancada_dir)

    for raiz, tipos in moradas:
        if not (real_pai == raiz or raiz in real_pai.parents):
            continue
        em_bin = _em_bin_do_harness(real_pai, b)
        tipos_efetivos = tipos | {""} if em_bin else tipos
        if ext not in tipos_efetivos and not _nome_texto(alvo.name):
            return (
                None,
                (
                    f"tipo: '{ext or '(sem extensao)'}' fora de "
                    f"{sorted(t or '(sem)' for t in tipos_efetivos)} (e dos nomes "
                    f"{sorted(NOMES_TEXTO)} e {PREFIXO_DOCKERFILE}<sufixo>) em {raiz}/"
                ),
                False,
            )
        exige_shebang = em_bin and ext == "" and not _nome_texto(alvo.name)
        if raiz == tmp_fita:
            rel = real_pai.relative_to(tmp_fita).parts
            if not rel:
                return (
                    None,
                    f"morada: {tmp_fita}/<ordem_id>/<arquivo> — subpasta da fita e obrigatoria",
                    False,
                )
            ord_id = (ordem_id or "").strip()
            if ord_id in ("", "-"):
                return (
                    None,
                    f"morada: {tmp_fita}/<ordem_id>/ exige fita declarada — chame com o sessao_id de monta_sessao",
                    False,
                )
            if ord_id != rel[0]:
                return (
                    None,
                    f"morada: {tmp_fita}/{rel[0]}/ nao e a pasta desta fita ({ord_id})",
                    False,
                )
        else:
            erro_clone = _clone_ausente(raiz, real_pai)
            if erro_clone:
                return None, erro_clone, False

        real_alvo = real_pai / alvo.name
        if real_alvo.is_symlink():
            return None, "alvo e symlink — write_file nao escreve atraves de link", False
        return real_alvo, None, exige_shebang

    lista = ", ".join(str(r) + "/" for r, _ in moradas)
    if b is None:
        lista += " (bancada nao declarada: clones e worktrees fora de alcance)"
    if pp.is_absolute():
        return None, f"fora de morada ({alvo}) — moradas: {lista}", False
    return (
        None,
        (
            f"fora de morada ({alvo}): caminho relativo parte da bancada declarada "
            f"(ex.: wt/<repo>/<cadeira>/<card-ou-slug>/<arquivo>), nao da raiz do repo — moradas: {lista}"
        ),
        False,
    )
