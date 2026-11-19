"""Admissão da suíte na esteira: confere vínculo, conjunto único, nome, apoio e ensaia fichas na Olaria."""
from __future__ import annotations

import argparse
import ast
import http.client
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from suite.selecao import PASTAS_IGNORADAS, PASTAS_TESTE, descobrir_arquivos_teste
from suite.vinculo import DESTINOS_VERIFICA, VinculoArquivo, extrair_slug_componente, ler_vinculo

_HTTP_ERRO_SERVIDOR = 500
_RE_TOKEN_SEPARADOR = re.compile(r"[_.\-]+")
_RE_TOKEN_CARD = re.compile(r"^(?:\d{3,}|(?:card|dt|debito|incidente)\d+)$", re.IGNORECASE)
_RE_PREFIXO_CARD = re.compile(r"^(?:card|dt|debito|incidente)$", re.IGNORECASE)
_RE_IMPORT_JS = re.compile(
    r"""(?:import\s+(?:[^'"]+?\s+from\s+)?['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)|require\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)

DESTINOS_EXIGE = frozenset({"servico", "modelo", "embedder", "host"})
SERVICOS_CONHECIDOS_PREFIXO = frozenset({"olaria", "casa-db", "rag"})


class OlariaIndisponivelErro(RuntimeError):
    """A Olaria não respondeu ou o ambiente dela não está configurado (saída 3, não medido)."""


@dataclass(frozen=True)
class RecusaAdmissao:
    codigo: str
    arquivo: str
    mensagem: str
    ficha_faltante: str | None = None
    conjunto_existente: str | None = None

    def como_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "codigo": self.codigo,
            "arquivo": self.arquivo,
            "mensagem": self.mensagem,
        }
        if self.ficha_faltante is not None:
            d["ficha_faltante"] = self.ficha_faltante
        if self.conjunto_existente is not None:
            d["conjunto_existente"] = self.conjunto_existente
        return d


@dataclass(frozen=True)
class ResultadoAdmissao:
    estado: str
    codigo_saida: int
    fichas_ensaiadas: tuple[dict[str, Any], ...]
    recusas: tuple[RecusaAdmissao, ...]
    avisos_legado: tuple[RecusaAdmissao, ...] = ()
    motivo_indisponivel: str | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "estado": self.estado,
            "codigo_saida": self.codigo_saida,
            "fichas_ensaiadas": list(self.fichas_ensaiadas),
            "recusas": [r.como_dict() for r in self.recusas],
            "avisos_legado": [a.como_dict() for a in self.avisos_legado],
            "motivo_indisponivel": self.motivo_indisponivel,
        }

    def resumo_texto(self) -> str:
        linhas: list[str] = []
        if self.estado == "nao-medido":
            linhas.append(f"admissao: NAO MEDIDO — {self.motivo_indisponivel or 'Olaria indisponível'}")
            return "\n".join(linhas)
        for av in self.avisos_legado:
            linhas.append(f"aviso (já na main): {av.mensagem}")
        if self.recusas:
            linhas.append(f"admissao: RECUSADO ({len(self.recusas)} erro(s))")
            for r in self.recusas:
                linhas.append(f"  recusa [{r.codigo}]: {r.mensagem}")
        else:
            linhas.append(
                f"admissao: ADMITIDO ({len(self.fichas_ensaiadas)} ficha(s) de verificação ensaiada(s))"
            )
        return "\n".join(linhas)


def _inferir_classe_pela_chave(chave: str) -> str:
    if ":" in chave:
        pref = chave.split(":", 1)[0]
        if pref in SERVICOS_CONHECIDOS_PREFIXO:
            return "servico"
        return pref
    if chave.startswith(("interface-", "contrato-")):
        return "interface"
    if chave.startswith(("politica-", "gabarito-", "configuracao-")):
        return "politica"
    return "componente"


def _validar_ligacao_duble(
    fichas_conhecidas: dict[str, str],
    onde: str,
    destino: str | None,
    classes_permitidas: frozenset[str],
) -> list[dict[str, Any]]:
    if not destino or destino not in fichas_conhecidas:
        return [{"codigo": "ficha-inexistente", "onde": onde, "recebido": destino}]
    if fichas_conhecidas[destino] not in classes_permitidas:
        return [{"codigo": "ficha-ligacao-destino-nao-permitido", "onde": onde, "recebido": destino}]
    return []


class DubleOlaria:
    """Dublê em processo do ensaiador da Olaria para testes de admissão sem credenciais."""

    def __init__(
        self,
        fichas: Iterable[str] | Mapping[str, str] = (),
        *,
        fora_do_ar: bool = False,
        ja_gravadas: Iterable[str] = (),
    ) -> None:
        self.fora_do_ar = fora_do_ar
        self.ja_gravadas = set(ja_gravadas)
        self.fichas: dict[str, str] = {}
        if isinstance(fichas, Mapping):
            for k, cls in fichas.items():
                self.registrar(k, cls)
        else:
            for k in fichas:
                self.registrar(k)

    def registrar(self, chave: str, classe: str | None = None) -> None:
        cls = classe or _inferir_classe_pela_chave(chave)
        self.fichas[chave] = cls
        if cls == "componente" and not chave.startswith("componente:"):
            self.fichas[f"componente:{chave}"] = "componente"

    def _conferir_ficha(self, idx: int, ficha: dict[str, Any]) -> list[dict[str, Any]]:
        erros: list[dict[str, Any]] = []
        chave = ficha.get("chave", "")
        if chave in self.ja_gravadas:
            erros.append({"codigo": "ficha-chave-ja-existe", "onde": f"/fichas/{idx}/chave", "recebido": chave})
        ligs = ficha.get("ligacoes") or {}
        erros.extend(
            _validar_ligacao_duble(
                self.fichas, f"/fichas/{idx}/ligacoes/sobre", ligs.get("sobre"), frozenset({"componente"})
            )
        )
        verifica = ligs.get("verifica")
        if verifica is not None:
            erros.extend(
                _validar_ligacao_duble(
                    self.fichas, f"/fichas/{idx}/ligacoes/verifica", verifica, DESTINOS_VERIFICA
                )
            )
        exige_lista = ligs.get("exige") or []
        if isinstance(exige_lista, str):
            exige_lista = [exige_lista]
        for k, ex in enumerate(exige_lista):
            erros.extend(
                _validar_ligacao_duble(self.fichas, f"/fichas/{idx}/ligacoes/exige/{k}", ex, DESTINOS_EXIGE)
            )
        return erros

    def ensaiar(self, fichas_verificacao: list[dict[str, Any]]) -> dict[str, Any]:
        if self.fora_do_ar:
            raise OlariaIndisponivelErro("serviço da Olaria fora do ar")
        erros: list[dict[str, Any]] = []
        for idx, ficha in enumerate(fichas_verificacao):
            erros.extend(self._conferir_ficha(idx, ficha))
        return {
            "estado": "recusada" if erros else "ensaio",
            "erros": erros,
            "total": len(erros),
        }

    def __call__(self, fichas_verificacao: list[dict[str, Any]]) -> dict[str, Any]:
        return self.ensaiar(fichas_verificacao)


class EnsaiadorOlaria:
    """Cliente HTTP de ensaio na Olaria (`POST /ensaiar`, sem gravar)."""

    def __init__(self, url: str | None = None, chave: str | None = None, timeout_s: float = 30.0) -> None:
        self.url = (url or os.environ.get("OLARIA_URL") or "").rstrip("/")
        self.chave = chave or os.environ.get("OLARIA_CHAVE") or ""
        self.timeout_s = timeout_s

    def ensaiar(self, fichas_verificacao: list[dict[str, Any]]) -> dict[str, Any]:
        if not fichas_verificacao:
            return {"estado": "ensaio", "erros": [], "total": 0}
        if not self.url or not self.chave:
            raise OlariaIndisponivelErro("OLARIA_URL ou OLARIA_CHAVE ausente no ambiente")
        yaml_texto = yaml.safe_dump(
            {"fichas": fichas_verificacao},
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        corpo_req = json.dumps({"yaml": yaml_texto, "ato": "criar"}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(f"{self.url}/ensaiar", data=corpo_req, method="POST")
        req.add_header("X-Olaria-Chave", self.chave)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("User-Agent", "suite-admissao")
        sujeito = os.environ.get("PF_CADEIRA", "")
        if sujeito:
            req.add_header("X-Olaria-Sujeito", sujeito)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                bruto, status = resp.read(), resp.status
        except urllib.error.HTTPError as exc:
            bruto, status = exc.read(), exc.code
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException, OSError) as exc:
            raise OlariaIndisponivelErro(f"Olaria sem resposta em {self.url}: {exc}") from exc

        try:
            dados = json.loads(bruto or b"{}")
        except ValueError as exc:
            raise OlariaIndisponivelErro(f"resposta ilegível da Olaria (status {status})") from exc

        if status >= _HTTP_ERRO_SERVIDOR or dados.get("estado") in ("fora-do-ar", "defeito"):
            raise OlariaIndisponivelErro(dados.get("erro") or f"Olaria devolveu status {status}")
        return dados if isinstance(dados, dict) else {"erros": []}

    def __call__(self, fichas_verificacao: list[dict[str, Any]]) -> dict[str, Any]:
        return self.ensaiar(fichas_verificacao)


def _marca_card_no_nome(stem: str) -> str | None:
    tokens = [t for t in _RE_TOKEN_SEPARADOR.split(stem) if t]
    for idx, tok in enumerate(tokens):
        if _RE_TOKEN_CARD.match(tok):
            return tok
        if _RE_PREFIXO_CARD.match(tok) and idx + 1 < len(tokens) and tokens[idx + 1].isdigit():
            return f"{tok}_{tokens[idx + 1]}"
    return None


def _sugerir_conjunto_alvo(
    rel: str,
    v: VinculoArquivo,
    primeiro_por_par: dict[tuple[str, str | None], str],
    primeiro_por_comp: dict[str, str],
) -> str:
    if v.par is not None and v.par in primeiro_por_par and primeiro_por_par[v.par] != rel:
        return primeiro_por_par[v.par]
    if v.componente is not None and v.componente in primeiro_por_comp and primeiro_por_comp[v.componente] != rel:
        return primeiro_por_comp[v.componente]
    caminho = Path(rel)
    pasta = caminho.parent.as_posix()
    prefixo_pasta = f"{pasta}/" if pasta and pasta != "." else ""
    ext = caminho.suffix or ".py"
    if v.componente is not None:
        slug_comp = (extrair_slug_componente(v.componente) or "componente").replace("-", "_")
        if v.verifica:
            slug_alvo = re.sub(r"[^a-zA-Z0-9_]+", "_", v.verifica).strip("_")
            return f"{prefixo_pasta}test_{slug_comp}_{slug_alvo}{ext}"
        return f"{prefixo_pasta}test_{slug_comp}{ext}"
    tokens = [
        t
        for t in _RE_TOKEN_SEPARADOR.split(caminho.stem)
        if t and not _RE_TOKEN_CARD.match(t) and not _RE_PREFIXO_CARD.match(t)
    ]
    nome_limpo = "_".join(tokens) if tokens else "test_componente"
    return f"{prefixo_pasta}{nome_limpo}{ext}"


def _segmento_eh_apoio_teste(modulo: str) -> bool:
    partes = [p for p in re.split(r"[./\\]+", modulo) if p]
    return any(p in ("testes", "tests") for p in partes)


def _imports_apoio_python(texto: str, modulos_apoio: set[str]) -> list[str]:
    achados: list[str] = []
    try:
        arvore = ast.parse(texto)
    except SyntaxError:
        return achados

    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _segmento_eh_apoio_teste(alias.name) or alias.name in modulos_apoio:
                    achados.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if _segmento_eh_apoio_teste(mod) or mod in modulos_apoio:
                achados.append(mod)
                continue
            for alias in node.names:
                combinado = f"{mod}.{alias.name}".strip(".")
                if (
                    alias.name in ("testes", "tests")
                    or _segmento_eh_apoio_teste(combinado)
                    or combinado in modulos_apoio
                    or alias.name in modulos_apoio
                ):
                    achados.append(combinado)
    return list(dict.fromkeys(achados))


def _imports_apoio_node(texto: str) -> list[str]:
    achados: list[str] = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if limpa.startswith("//"):
            continue
        for m in _RE_IMPORT_JS.finditer(linha):
            spec = m.group(1) or m.group(2) or m.group(3) or ""
            if _segmento_eh_apoio_teste(spec):
                achados.append(spec)
    return list(dict.fromkeys(achados))


def _descobrir_arquivos_producao(raiz: Path, arquivos_teste_set: set[Path]) -> tuple[list[Path], set[str]]:
    producao: list[Path] = []
    modulos_apoio: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in (PASTAS_IGNORADAS - {"apoio", "fixtures", "contratos"}) and not d.startswith(".")
        )
        pasta_atual = Path(dirpath)
        partes_rel = pasta_atual.relative_to(raiz).parts
        em_pasta_teste = any(p in PASTAS_TESTE for p in partes_rel)

        for fn in sorted(filenames):
            if fn.startswith(".") or fn in ("conftest.py", "__init__.py"):
                continue
            arq = pasta_atual / fn
            suf = arq.suffix.lower()
            if suf not in (".py", ".mjs", ".js"):
                continue
            if em_pasta_teste:
                if arq not in arquivos_teste_set and suf == ".py":
                    modulos_apoio.add(arq.stem)
                continue
            if arq in arquivos_teste_set:
                continue
            producao.append(arq)

    return sorted(producao), modulos_apoio


def _arquivos_mudados_git(raiz: Path, base: str) -> set[str]:
    diff = subprocess.run(
        ["git", "-C", str(raiz), "diff", "-z", "--name-only", base],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    novos = subprocess.run(
        ["git", "-C", str(raiz), "ls-files", "-z", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    brutos = (diff.stdout or "").split("\0") + (novos.stdout or "").split("\0")
    return {caminho_rel.strip().lstrip("./") for caminho_rel in brutos if caminho_rel.strip()}


def _executar_ensaiador(
    ensaiador: Any,
    fichas: list[dict[str, Any]],
) -> dict[str, Any]:
    alvo = EnsaiadorOlaria() if ensaiador is None else ensaiador
    try:
        if hasattr(alvo, "ensaiar") and callable(alvo.ensaiar):
            res = alvo.ensaiar(fichas)
        elif callable(alvo):
            res = alvo(fichas)
        else:
            raise TypeError(f"ensaiador inválido: {type(alvo)!r}")
    except OlariaIndisponivelErro:
        raise
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise OlariaIndisponivelErro(str(exc)) from exc

    if isinstance(res, dict):
        if res.get("estado") in ("fora-do-ar", "defeito"):
            raise OlariaIndisponivelErro(str(res.get("erro") or "Olaria fora do ar"))
        return res
    if isinstance(res, list):
        return {"erros": res, "total": len(res)}
    return {"erros": [], "total": 0}


@dataclass
class _ContextoAdmissao:
    raiz: Path
    mudados: set[str] | None
    recusas: list[RecusaAdmissao]
    avisos_legado: list[RecusaAdmissao]
    primeiro_por_par: dict[tuple[str, str | None], str]
    primeiro_por_comp: dict[str, str]
    vinculos_lidos: list[tuple[str, VinculoArquivo]]
    para_ensaiar: list[tuple[str, VinculoArquivo, dict[str, Any]]]

    def eh_mudado(self, rel: str) -> bool:
        return self.mudados is None or rel in self.mudados

    def registrar_violacao(self, violacao: RecusaAdmissao) -> None:
        if self.eh_mudado(violacao.arquivo):
            self.recusas.append(violacao)
        else:
            self.avisos_legado.append(violacao)


def _conferir_vinculos_arvore(ctx: _ContextoAdmissao, com_rel: list[tuple[str, Path]]) -> None:
    for rel, arq in com_rel:
        v = ler_vinculo(arq)
        ctx.vinculos_lidos.append((rel, v))
        if v.componente is None:
            ctx.registrar_violacao(
                RecusaAdmissao(
                    codigo="sem-componente",
                    arquivo=rel,
                    mensagem=f"{rel}: arquivo de teste sem 'componente:' no cabeçalho",
                )
            )
            continue

        if v.componente not in ctx.primeiro_por_comp:
            ctx.primeiro_por_comp[v.componente] = rel
        par = (v.componente, v.verifica)
        if par in ctx.primeiro_por_par:
            primeiro = ctx.primeiro_por_par[par]
            alvo_desc = v.verifica or "comportamento"
            ctx.registrar_violacao(
                RecusaAdmissao(
                    codigo="segundo-conjunto",
                    arquivo=rel,
                    conjunto_existente=primeiro,
                    mensagem=(
                        f"{rel}: segundo conjunto para ({v.componente}, {alvo_desc}) — "
                        f"adicione os casos ao conjunto existente: {primeiro}"
                    ),
                )
            )
        else:
            ctx.primeiro_por_par[par] = rel
            if ctx.eh_mudado(rel):
                ctx.para_ensaiar.append((rel, v, v.como_ficha()))


def _conferir_nomes_e_apoio(ctx: _ContextoAdmissao, arquivos_teste_set: set[Path]) -> None:
    for rel, v in ctx.vinculos_lidos:
        marca_card = _marca_card_no_nome(Path(rel).stem)
        if marca_card is not None:
            sugestao = _sugerir_conjunto_alvo(rel, v, ctx.primeiro_por_par, ctx.primeiro_por_comp)
            ctx.registrar_violacao(
                RecusaAdmissao(
                    codigo="nome-com-card",
                    arquivo=rel,
                    conjunto_existente=sugestao,
                    mensagem=(
                        f"{rel}: arquivo de teste batizado por card ou débito ('{marca_card}') — "
                        f"ponha os casos no conjunto do alvo: {sugestao}"
                    ),
                )
            )

    arquivos_prod, modulos_apoio = _descobrir_arquivos_producao(ctx.raiz, arquivos_teste_set)
    conjunto_padrao = next(iter(ctx.primeiro_por_par.values()), "testes/test_componente.py")
    for arq_prod in arquivos_prod:
        rel_prod = arq_prod.relative_to(ctx.raiz).as_posix() if arq_prod.is_relative_to(ctx.raiz) else arq_prod.name
        try:
            texto_prod = arq_prod.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        proibidos = (
            _imports_apoio_python(texto_prod, modulos_apoio)
            if arq_prod.suffix.lower() == ".py"
            else _imports_apoio_node(texto_prod)
        )
        for imp in proibidos:
            ctx.registrar_violacao(
                RecusaAdmissao(
                    codigo="producao-importa-apoio",
                    arquivo=rel_prod,
                    conjunto_existente=conjunto_padrao,
                    mensagem=(
                        f"{rel_prod}: código de produção importa apoio de teste ('{imp}') — "
                        f"mantenha o apoio e os casos no conjunto do alvo: {conjunto_padrao}"
                    ),
                )
            )


def _registrar_erros_ensaio(ctx: _ContextoAdmissao, resp_ensaio: dict[str, Any]) -> None:
    for erro in resp_ensaio.get("erros") or []:
        if not isinstance(erro, dict):
            continue
        cod_erro = str(erro.get("codigo") or "ficha-invalida")
        onde = str(erro.get("onde") or "")
        recebido = str(erro.get("recebido") or "")
        m_idx = re.match(r"^/fichas/(\d+)(?:/(.*))?$", onde)
        idx_ficha = int(m_idx.group(1)) if m_idx else 0
        sub_caminho = (m_idx.group(2) or "") if m_idx else ""

        if cod_erro in ("ficha-chave-ja-existe", "ficha-identidade-repetida") and sub_caminho in ("", "chave"):
            continue

        if 0 <= idx_ficha < len(ctx.para_ensaiar):
            rel_alvo = ctx.para_ensaiar[idx_ficha][0]
        elif ctx.vinculos_lidos:
            rel_alvo = ctx.vinculos_lidos[0][0]
        else:
            rel_alvo = "<arvore>"

        ctx.registrar_violacao(
            RecusaAdmissao(
                codigo="ficha-invalida",
                arquivo=rel_alvo,
                ficha_faltante=recebido or None,
                mensagem=(
                    f"{rel_alvo}: ficha ausente ou inválida na Olaria "
                    f"({cod_erro}: '{recebido}' em {onde or '/fichas'})"
                ),
            )
        )


def admitir(
    arvore: str | Path = ".",
    *,
    ensaiador: Callable[[list[dict[str, Any]]], Any] | Any = None,
    arquivos_mudados: Iterable[str] | None = None,
    base: str | None = None,
) -> ResultadoAdmissao:
    """Confere a admissão dos conjuntos de teste da árvore e ensaia as fichas na Olaria."""
    raiz = Path(arvore).resolve()
    mudados: set[str] | None = None
    if arquivos_mudados is not None:
        mudados = {str(p).strip().lstrip("./") for p in arquivos_mudados if str(p).strip()}
    elif base is not None:
        mudados = _arquivos_mudados_git(raiz, base)

    ctx = _ContextoAdmissao(
        raiz=raiz,
        mudados=mudados,
        recusas=[],
        avisos_legado=[],
        primeiro_por_par={},
        primeiro_por_comp={},
        vinculos_lidos=[],
        para_ensaiar=[],
    )

    arquivos_teste = descobrir_arquivos_teste(raiz)
    com_rel: list[tuple[str, Path]] = [
        (arq.relative_to(raiz).as_posix() if arq.is_relative_to(raiz) else arq.name, arq)
        for arq in arquivos_teste
    ]
    com_rel.sort(key=lambda item: (1 if ctx.eh_mudado(item[0]) else 0, item[0]))

    _conferir_vinculos_arvore(ctx, com_rel)
    _conferir_nomes_e_apoio(ctx, set(arquivos_teste))

    fichas_ensaiadas = [f for _, _, f in ctx.para_ensaiar]
    if fichas_ensaiadas or ensaiador is not None:
        try:
            resp_ensaio = _executar_ensaiador(ensaiador, fichas_ensaiadas)
        except OlariaIndisponivelErro as exc:
            return ResultadoAdmissao(
                estado="nao-medido",
                codigo_saida=3,
                fichas_ensaiadas=tuple(fichas_ensaiadas),
                recusas=tuple(ctx.recusas),
                avisos_legado=tuple(ctx.avisos_legado),
                motivo_indisponivel=str(exc),
            )
        _registrar_erros_ensaio(ctx, resp_ensaio)

    estado = "recusado" if ctx.recusas else "admitido"
    cod_saida = 1 if ctx.recusas else 0
    return ResultadoAdmissao(
        estado=estado,
        codigo_saida=cod_saida,
        fichas_ensaiadas=tuple(fichas_ensaiadas),
        recusas=tuple(ctx.recusas),
        avisos_legado=tuple(ctx.avisos_legado),
    )


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite admitir")
    p.add_argument("arvore_pos", nargs="?", default=None, help="caminho da árvore do repositório")
    p.add_argument("--arvore", default=None, help="caminho da árvore do repositório")
    p.add_argument("--base", default=None, help="revisão git base para filtrar arquivos mudados")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite o resultado em JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    arvore = args.arvore or args.arvore_pos or "."
    res = admitir(arvore, base=args.base)
    if args.como_json:
        sys.stdout.write(json.dumps(res.como_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        texto = res.resumo_texto() + "\n"
        sys.stdout.write(texto)
        if res.codigo_saida != 0:
            sys.stderr.write(texto)
    return res.codigo_saida


if __name__ == "__main__":
    raise SystemExit(main())
