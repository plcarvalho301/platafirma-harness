"""Atos do tesauro e das indicações de conceito no padrão do verbo da casa nova (DTs 805 e 806).

Classes atendidas (com ou sem a partição `biblioteca`):
  - `conceito`  (guardada em `acervo.conceito` + `acervo.conceito_rotulo`):
      ler, listar, criar, trocar <versao>, renomear, ensaiar <criar|trocar|renomear>, gravar (recusado -> 2)
  - `indicacao` (guardada em `acervo.indicacao_conceito`):
      listar, ler, admitir, descartar, ensaiar <admitir|descartar>

Só stdlib: roda direto em `python3`, sem depender de venv externo nem abrir rede na importação.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BASE = "http://127.0.0.1:8102"
LINGUAS = ("pt", "en", "zxx")
NATUREZAS = ("processo", "disposicao", "modelo", "fenomeno")
ESTATUTOS = ("instituido", "doutrinario", "natural")
HIERARQUICAS = ("generica", "partitiva", "instancia")
GARANTIAS = ("literaria", "de-uso", "instituida")
ESTADOS_IND = ("pendente", "admitida", "descartada", "todas")
ATOS_ESCRITA = ("criar", "trocar", "renomear", "admitir", "descartar")
CODIGOS_STDERR_JSON = (2, 3, 4, 5)

_MAX_RECEBIDO = 80
_HTTP_BAD_REQUEST = 400
_HTTP_NOT_FOUND = 404
_HTTP_SERVER_ERROR = 500
_PAR_ARGS = 2

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

AJUDA_POR_ATO: dict[str, str] = {
    "ler:conceito": (
        "acervo ler [biblioteca] conceito <slug|uuid> [--json]\n"
        "  Lê um conceito do tesauro com seus rótulos, língua do preferido e versão determinística.\n"
        "  A versão devolvida na primeira linha alimenta `acervo trocar biblioteca conceito <slug> <versao>`."
    ),
    "listar:conceito": (
        "acervo listar [biblioteca] conceito [--natureza <n>] [--estatuto <e>] [--termo <texto>] [--json]\n"
        "  Lista conceitos do tesauro com versão do recorte e contagem."
    ),
    "criar": (
        "acervo criar [biblioteca] conceito <slug> --rotulo <texto> --definicao <texto>\n"
        "  --natureza <processo|disposicao|modelo|fenomeno> --estatuto <instituido|doutrinario|natural>\n"
        "  [--lingua <pt|en|zxx>] [--rotulo-alt <lingua|rotulo>]...\n"
        "  [--pai <slug> --tipo <generica|partitiva|instancia> [--garantia <g>] [--motivo <m>] [--lastro <obra>]]\n"
        "  [--endereco <uri>] [--filhos-exclusivos] [--trata-de <obra,...>]\n"
        "  [--pedido <uuid7>] [--autor <curador>] [--json]\n"
        "  Ensaio sem gravar: acervo ensaiar criar biblioteca conceito <slug> ..."
    ),
    "trocar": (
        "acervo trocar [biblioteca] conceito <slug|uuid> <versao> --motivo <texto>\n"
        "  [--rotulo <texto>] [--lingua <pt|en|zxx>] [--definicao <texto>]\n"
        "  [--natureza <n>] [--estatuto <e>] [--endereco <uri>]\n"
        "  [--filhos-exclusivos | --sem-filhos-exclusivos]\n"
        "  [--pai <slug> --tipo <generica|partitiva|instancia> [--garantia <g>] [--lastro <obra>] | --sem-pai]\n"
        "  [--rotulo-alt <lingua|rotulo>]... [--sem-rotulo-alt <rotulo>]...\n"
        "  [--pedido <uuid7>] [--autor <curador>] [--json]\n"
        "  Substitui atributos e rótulos conferindo a <versao> lida em `acervo ler biblioteca conceito <slug>`.\n"
        "  Para trocar a chave (`slug`), use o ato próprio `acervo renomear biblioteca conceito`.\n"
        "  Ensaio sem gravar: acervo ensaiar trocar biblioteca conceito <slug> <versao> --motivo ..."
    ),
    "renomear": (
        "acervo renomear [biblioteca] conceito <slug-atual> <slug-novo> --motivo <texto>\n"
        "  [--pedido <uuid7>] [--autor <curador>] [--json]\n"
        "  Troca a chave (`slug`) do conceito, preservando o slug anterior como termo de entrada (`zxx`).\n"
        "  Ensaio sem gravar: acervo ensaiar renomear biblioteca conceito <slug-atual> <slug-novo> --motivo ..."
    ),
    "listar:indicacao": (
        "acervo listar [biblioteca] indicacao [<lote|todas>] [--lote <id>]\n"
        "  [--estado <pendente|admitida|descartada|todas>] [--termo <texto>] [--desagrupado] [--json]\n"
        "  Lista indicações de conceitos candidatos com obras vivas, obras retiradas e destino."
    ),
    "ler:indicacao": (
        "acervo ler [biblioteca] indicacao <uuid|termo|slug> [--json]\n"
        "  Lê uma indicação específica ou todas as indicações de um termo, com garantia viva e destino."
    ),
    "admitir": (
        "acervo admitir [biblioteca] indicacao [<lote|todas>] --motivo <texto>\n"
        "  [--termos <a,b>] [--ids <id1,id2>] [--natureza <n>] [--estatuto <e>] [--lingua <pt|en|zxx>]\n"
        "  [--pedido <uuid7>] [--autor <curador>] [--json]\n"
        "  Passa indicações pendentes a `admitida`, ligando obras vivas ao conceito existente quando o termo\n"
        "  já tem conceito ou criando cada conceito novo uma vez. Recusa garantia em obra retirada.\n"
        "  Ensaio sem gravar: acervo ensaiar admitir biblioteca indicacao [<lote|todas>] --motivo ..."
    ),
    "descartar": (
        "acervo descartar [biblioteca] indicacao [<lote|todas>] --motivo <texto>\n"
        "  [--termos <a,b>] [--ids <id1,id2>] [--pedido <uuid7>] [--autor <curador>] [--json]\n"
        "  Passa indicações pendentes a `descartada` com motivo registrado.\n"
        "  Ensaio sem gravar: acervo ensaiar descartar biblioteca indicacao [<lote|todas>] --motivo ..."
    ),
    "ensaiar": (
        "acervo ensaiar <criar|trocar|renomear|admitir|descartar> [biblioteca] <conceito|indicacao> ...\n"
        "  Executa toda a validação e conferência do ato de escrita em transação revertida, sem gravar."
    ),
}


@dataclass(frozen=True)
class ContextoChamada:
    onde: str
    proximo: str
    chave: str = ""
    pedido_id: str | None = None
    como_json: bool = False
    em_escrita: bool = False


def gerar_uuid7() -> str:
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    inteiro = (ms << 80) | (0x7 << 76) | (secrets.randbits(12) << 64) | (0b10 << 62) | secrets.randbits(62)
    return str(uuid.UUID(int=inteiro))


def validar_uuid(valor: str) -> bool:
    return bool(UUID_RE.match(str(valor).strip()))


def _base_url() -> str:
    return (
        os.environ.get("MOTOR_ACERVO_URL")
        or os.environ.get("RAG_API_URL")
        or os.environ.get("RAG_API_BASE")
        or DEFAULT_BASE
    ).rstrip("/")


def _token() -> str:
    do_env = (os.environ.get("RAG_API_TOKEN") or "").strip()
    if do_env:
        return do_env
    lib_dir = str(Path(__file__).resolve().parents[2] / "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    import acervo_token
    return acervo_token.ler_token_acervo()


def _autor_padrao(explicito: str | None) -> str:
    if explicito and explicito.strip():
        return explicito.strip()
    cad = (os.environ.get("PF_CADEIRA") or os.environ.get("PF_CONTA") or "").strip().lower()
    autor = cad.removeprefix("claudinho-").removeprefix("claudinha-") or "dados"
    return "time-platafirma" if autor in {"engenharia", "ti", "ia", "arquiteto", "seguranca"} else autor


def erro_item(
    codigo: str,
    onde: str,
    recebido: Any,
    regra_e_cura: tuple[str, str],
    proximo: str,
) -> dict[str, Any]:
    regra, cura = regra_e_cura
    return {
        "codigo": codigo,
        "onde": onde,
        "recebido": recebido,
        "regra": regra,
        "cura": cura,
        "proximo": proximo,
    }


def _rec_curto(v: Any) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= _MAX_RECEBIDO else s[: _MAX_RECEBIDO - 3] + "..."


def emitir_erros(erros: list[dict[str, Any]], *, como_json: bool, exit_code: int) -> int:
    if como_json:
        sys.stdout.write(json.dumps({"erros": erros, "total": len(erros)}, ensure_ascii=False, indent=2) + "\n")
    else:
        for e in erros:
            sys.stdout.write(
                f"{e['codigo']} · {e['onde']} · recebido: {_rec_curto(e['recebido'])}"
                f" · regra: {e['regra']} · cura: {e['cura']} · proximo: {e['proximo']}\n"
            )
    if exit_code in CODIGOS_STDERR_JSON and erros:
        sys.stderr.write(json.dumps({"erro": erros[0]}, ensure_ascii=False) + "\n")
    return exit_code


class ErroHTTP(Exception):
    def __init__(self, status: int, corpo: Any, texto_cru: str):
        super().__init__(texto_cru)
        self.status = status
        self.corpo = corpo
        self.texto_cru = texto_cru


class ErroTransporte(Exception):
    def __init__(self, exc: Exception, *, em_escrita: bool):
        super().__init__(str(exc))
        self.exc = exc
        self.em_escrita = em_escrita

    @property
    def timeout_ou_queda_em_escrita(self) -> bool:
        if not self.em_escrita:
            return False
        causa = self.exc.reason if isinstance(self.exc, urllib.error.URLError) else self.exc
        return isinstance(self.exc, (TimeoutError, ConnectionResetError, BrokenPipeError)) or isinstance(
            causa, (TimeoutError, ConnectionResetError)
        )


def requisitar(
    metodo: str,
    caminho: str,
    corpo: dict[str, Any] | None = None,
    *,
    em_escrita: bool = False,
    timeout: float = 60.0,
) -> Any:
    cabecalhos = {"accept": "application/json"}
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        cabecalhos["content-type"] = "application/json"
    tok = _token()
    if tok:
        cabecalhos["authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(f"{_base_url()}{caminho}", data=dados, method=metodo, headers=cabecalhos)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            bruto, status = resp.read(), resp.status
    except urllib.error.HTTPError as e:
        bruto, status = e.read(), e.code
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise ErroTransporte(e, em_escrita=em_escrita) from e

    texto = (bruto or b"").decode("utf-8", "replace")
    try:
        obj = json.loads(texto) if texto else {}
    except ValueError:
        obj = {}
    if status >= _HTTP_BAD_REQUEST:
        raise ErroHTTP(status, obj, texto)
    return obj


def _erro_por_titulo_4xx(titulo: str, detalhe: str, corpo: dict[str, Any], ctx: ContextoChamada) -> dict[str, Any] | None:
    por_titulo: dict[str, tuple[str, str, Any, tuple[str, str], str]] = {
        "VersaoDiferente": (
            "versao-diferente",
            f"{ctx.onde}.versao",
            {"esperada": corpo.get("versao_esperada"), "atual": corpo.get("versao_atual")},
            (
                "a versão informada em trocar precisa bater com o estado atual do conceito",
                "releia o conceito para obter a versão atual antes de trocar",
            ),
            f"acervo ler biblioteca conceito {ctx.chave}" if ctx.chave else ctx.proximo,
        ),
        "PedidoComConteudoDiferente": (
            "pedido-com-conteudo-diferente",
            f"{ctx.onde}.pedido",
            detalhe,
            (
                "um mesmo --pedido não pode ser reutilizado com atributos diferentes",
                "gere um novo --pedido (ou omita a flag) para outra mudança",
            ),
            ctx.proximo,
        ),
        "IndicacaoReprovada": (
            "garantia-retirada",
            ctx.onde,
            detalhe,
            (
                "obra retirada não sustenta indicação de conceito como garantia literária",
                "descarte a indicação sem garantia viva com o ato descartar",
            ),
            'acervo descartar biblioteca indicacao --motivo "obra retirada"',
        ),
    }
    if titulo in por_titulo:
        cod, onde_t, rec, rc_t, prox = por_titulo[titulo]
        return erro_item(cod, onde_t, rec, rc_t, prox)
    if titulo in ("ConceitoDuplicado", "RelacaoDuplicada"):
        prox = f"acervo ler biblioteca conceito {ctx.chave}" if ctx.chave else "acervo listar biblioteca conceito"
        return erro_item(
            "conceito-duplicado", ctx.onde, ctx.chave or detalhe,
            (detalhe, "leia o conceito existente e use trocar se quiser alterá-lo"), prox,
        )
    if titulo in ("RelacaoReprovada", "ConceitoReprovado"):
        return erro_item(
            "validacao-falhou", ctx.onde, detalhe,
            (
                "rótulos exclusivos por conceito e conferências ontológicas sem violação nova",
                "corrija o rótulo ou a relação que colidiu e ensaie novamente",
            ),
            ctx.proximo,
        )
    return None


def _tratar_erro_http(err: ErroHTTP, ctx: ContextoChamada) -> int:
    corpo = err.corpo if isinstance(err.corpo, dict) else {}
    titulo = str(corpo.get("title") or "")
    detalhe = str(corpo.get("detail") or err.texto_cru[:200] or f"HTTP {err.status}")

    if err.status in (401, 403):
        return emitir_erros([erro_item(
            "acesso-recusado", ctx.onde, err.status,
            ("o serviço do acervo exige credencial autorizada", "configure RAG_API_TOKEN válido no ambiente da conta"),
            "conferir servico",
        )], como_json=ctx.como_json, exit_code=4)

    if err.status >= _HTTP_SERVER_ERROR:
        return emitir_erros([erro_item(
            "servico-indisponivel", ctx.onde, {"status": err.status, "detalhe": detalhe},
            ("falha no serviço do acervo ou no banco subjacente", "consulte os logs de acervo-guarda"),
            "infra logs acervo-guarda --linhas 50",
        )], como_json=ctx.como_json, exit_code=3)

    if err.status == _HTTP_NOT_FOUND:
        eh_ind = "Indicacao" in titulo
        cod = "indicacao-inexistente" if eh_ind else "conceito-inexistente"
        prox = "acervo listar biblioteca indicacao" if eh_ind else "acervo listar biblioteca conceito"
        return emitir_erros([erro_item(
            cod, ctx.onde, ctx.chave or detalhe,
            ("a chave informada precisa existir no acervo", "confira a chave na listagem da classe"),
            prox,
        )], como_json=ctx.como_json, exit_code=1)

    especifico = _erro_por_titulo_4xx(titulo, detalhe, corpo, ctx)
    if especifico is not None:
        return emitir_erros([especifico], como_json=ctx.como_json, exit_code=1)

    return emitir_erros([erro_item(
        "entrada-invalida", ctx.onde, detalhe,
        ("os valores precisam obedecer ao vocabulário e às restrições da classe", "ajuste o valor apontado em detalhe"),
        ctx.proximo,
    )], como_json=ctx.como_json, exit_code=2 if err.status == _HTTP_BAD_REQUEST else 1)


def executar_chamada(metodo: str, caminho: str, corpo: dict[str, Any] | None, ctx: ContextoChamada) -> tuple[Any, int | None]:
    try:
        res = requisitar(metodo, caminho, corpo, em_escrita=ctx.em_escrita)
    except ErroTransporte as err:
        if err.timeout_ou_queda_em_escrita:
            return None, emitir_erros([erro_item(
                "escrita-indeterminavel",
                ctx.onde,
                {"pedido": ctx.pedido_id, "erro": type(err.exc).__name__},
                (
                    "a conexão caiu ou esgotou o prazo depois do envio da escrita; o servidor pode ter gravado",
                    "confira o estado antes de repetir ou repita com o mesmo --pedido",
                ),
                ctx.proximo,
            )], como_json=ctx.como_json, exit_code=5)
        return None, emitir_erros([erro_item(
            "servico-indisponivel",
            ctx.onde,
            {"base": _base_url(), "erro": type(err.exc).__name__},
            ("o serviço do acervo precisa responder para executar o ato", "verifique a saúde do serviço acervo-guarda"),
            "infra saude",
        )], como_json=ctx.como_json, exit_code=3)
    except ErroHTTP as err:
        return None, _tratar_erro_http(err, ctx)
    return res, None


def _consumir_flag_longa(
    tokens: list[str],
    idx: int,
    valoradas: set[str],
    repetiveis: set[str],
    booleanas: set[str],
) -> tuple[int, tuple[str, Any] | None, tuple[str, str] | None]:
    tok = tokens[idx]
    flag, sep, val = tok.partition("=")
    tem_eq = bool(sep)
    if flag in booleanas:
        return (idx + 1, (flag, True), None) if not tem_eq else (idx + 1, None, ("valor-inesperado", flag))
    if flag not in valoradas and flag not in repetiveis:
        return idx + 1, None, ("desconhecida", flag)
    if not tem_eq:
        if idx + 1 >= len(tokens) or tokens[idx + 1].startswith("--"):
            return idx + 1, None, ("faltou-valor", flag)
        return idx + 2, (flag, tokens[idx + 1]), None
    return idx + 1, (flag, val), None


def parse_opcoes(
    tokens: list[str],
    *,
    valoradas: set[str],
    repetiveis: set[str] | None = None,
    booleanas: set[str] | None = None,
) -> tuple[list[str], dict[str, Any], list[tuple[str, str]]]:
    reps = repetiveis or set()
    bools = booleanas or set()
    pos: list[str] = []
    opts: dict[str, Any] = {k: [] for k in reps}
    erros: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--":
            pos.extend(tokens[i + 1 :])
            break
        if tok.startswith("--"):
            i, par, err = _consumir_flag_longa(tokens, i, valoradas, reps, bools)
            if err:
                erros.append(err)
            elif par:
                k, v = par
                if k in reps:
                    opts[k].append(v)
                else:
                    opts[k] = v
        elif tok.startswith("-") and tok != "-":
            erros.append(("desconhecida", tok))
            i += 1
        else:
            pos.append(tok)
            i += 1
    return pos, opts, erros


def _rejeitar_erros_parse(
    erros_parse: list[tuple[str, str]],
    *,
    ato: str,
    classe: str,
    como_json: bool,
    dicas_nao_aplicaveis: dict[str, tuple[str, str]] | None = None,
) -> int | None:
    if not erros_parse:
        return None
    for _, flag in erros_parse:
        if flag in ("--dry-run", "--ensaio", "--no-apply"):
            return emitir_erros([erro_item(
                "variante-de-flag", f"{ato}.{flag}", flag,
                (
                    "ato de escrita não aceita flag de ensaio; o ensaio é o ato padrão 'ensaiar'",
                    f"chame 'acervo ensaiar {ato} biblioteca {classe} ...'",
                ),
                f"acervo ensaiar {ato} biblioteca {classe} --help",
            )], como_json=como_json, exit_code=2)

    dicas = dicas_nao_aplicaveis or {}
    ajuda_cmd = f"acervo {ato} biblioteca {classe} --help"
    lista: list[dict[str, Any]] = []
    for tipo, flag in erros_parse:
        if tipo == "faltou-valor":
            lista.append(erro_item(
                "argumento-faltando", f"{ato}.{flag}", flag,
                (f"a opção {flag} exige um valor", f"passe o valor logo após {flag}"), ajuda_cmd,
            ))
        elif tipo == "valor-inesperado":
            lista.append(erro_item(
                "formato-invalido", f"{ato}.{flag}", flag,
                (f"a opção booleana {flag} não recebe valor com '='", f"passe apenas {flag}"), ajuda_cmd,
            ))
        elif flag in dicas:
            regra, prox = dicas[flag]
            lista.append(erro_item(
                "flag-nao-aplicavel", f"{ato}.{flag}", flag,
                (regra, "remova a opção ou use o ato indicado em proximo"), prox,
            ))
        else:
            lista.append(erro_item(
                "flag-desconhecida", f"{ato}.{flag}", flag,
                (f"a opção {flag} não faz parte do contrato deste ato", "consulte as opções aceitas com --help"),
                ajuda_cmd,
            ))
    return emitir_erros(lista, como_json=como_json, exit_code=2)


def _resolver_pedido(
    opts: dict[str, Any],
    *,
    ensaio: bool,
    onde: str,
    prox_help: str,
    erros: list[dict[str, Any]],
) -> str | None:
    bruto = opts.get("--pedido")
    if ensaio:
        if bruto is not None:
            erros.append(erro_item(
                "flag-nao-aplicavel", f"{onde}.pedido", bruto,
                ("--pedido só se aplica ao ato de escrita real, não ao ensaio", "remova --pedido no ensaio"),
                prox_help,
            ))
        return None
    if bruto is None:
        return gerar_uuid7()
    cand = bruto.strip()
    if not validar_uuid(cand):
        erros.append(erro_item(
            "formato-invalido", f"{onde}.pedido", cand,
            ("--pedido exige um UUID válido", "passe um UUID válido ou omita --pedido"),
            prox_help,
        ))
        return None
    return cand


def _validar_dominio(
    valor: str | None,
    dominio: tuple[str, ...],
    onde: str,
    rotulo: str,
    prox: str,
) -> dict[str, Any] | None:
    if not valor or valor in dominio:
        return None
    return erro_item(
        "valor-fora-do-dominio", onde, valor,
        (f"{rotulo} deve ser um de: {', '.join(dominio)}", f"informe um {rotulo} válido"),
        prox,
    )


def _validar_rotulo_alt(itens: list[str], onde: str, proximo: str) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    saida: list[dict[str, str]] = []
    erros: list[dict[str, Any]] = []
    for item in itens:
        if "|" not in item:
            erros.append(erro_item(
                "formato-invalido", f"{onde}.rotulo-alt", item,
                ("rótulo alternativo exige língua explícita na forma 'lingua|rotulo'", "use pt|, en| ou zxx|"),
                proximo,
            ))
            continue
        lg, rot = (p.strip() for p in item.split("|", 1))
        err_lg = _validar_dominio(lg, LINGUAS, f"{onde}.rotulo-alt", "língua", proximo)
        if err_lg:
            erros.append(err_lg)
        elif not rot:
            erros.append(erro_item(
                "formato-invalido", f"{onde}.rotulo-alt", item,
                ("texto do rótulo alternativo não pode ser vazio", "preencha o rótulo após 'lingua|'"),
                proximo,
            ))
        else:
            saida.append({"rotulo": rot, "lingua": lg})
    return saida, erros


def _validar_pai_opcoes(
    opts: dict[str, Any],
    onde: str,
    prox: str,
    *,
    exige_motivo: bool,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    pai_slug = (opts.get("--pai") or "").strip()
    erros: list[dict[str, Any]] = []
    if not pai_slug:
        extras = [k for k in ("--tipo", "--garantia", "--lastro") if opts.get(k)]
        if extras:
            erros.append(erro_item(
                "flag-nao-aplicavel", f"{onde}.pai", extras,
                ("--tipo, --garantia e --lastro exigem --pai <slug>", "informe --pai <slug> ou remova as opções"),
                prox,
            ))
        return None, erros

    tp = (opts.get("--tipo") or "").strip()
    gar = (opts.get("--garantia") or "instituida").strip()
    mot = (opts.get("--motivo") or "").strip()
    if tp not in HIERARQUICAS:
        erros.append(erro_item(
            "valor-fora-do-dominio", f"{onde}.tipo", tp or None,
            (f"--pai exige --tipo hierárquico ({', '.join(HIERARQUICAS)})", "passe --tipo generica, partitiva ou instancia"),
            prox,
        ))
    err_g = _validar_dominio(gar, GARANTIAS, f"{onde}.garantia", "garantia", prox)
    if err_g:
        erros.append(err_g)
    if exige_motivo and not mot:
        erros.append(erro_item(
            "argumento-faltando", f"{onde}.motivo", None,
            ("--pai exige --motivo na frase-molde da família", "informe --motivo descrevendo a subordinação"),
            prox,
        ))
    if gar == "literaria" and not (opts.get("--lastro") or "").strip():
        erros.append(erro_item(
            "argumento-faltando", f"{onde}.lastro", None,
            ("garantia 'literaria' exige --lastro <obra>", "informe o uuid da obra garantidora em --lastro"),
            prox,
        ))
    pai_dict: dict[str, Any] = {"slug": pai_slug, "tipo": tp, "garantia": gar}
    if mot:
        pai_dict["motivo"] = mot
    if (opts.get("--lastro") or "").strip():
        pai_dict["lastro"] = opts["--lastro"].strip()
    return pai_dict, erros


def _hash_curto(valor: Any) -> str:
    canon = json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]


def _formatar_rotulos_lista(rotulos: list[dict[str, Any]]) -> str:
    if not rotulos:
        return "(nenhum em conceito_rotulo)"
    return ", ".join(
        f"{r.get('lingua') or '?'}|{r.get('rotulo')} ({'pref' if r.get('papel') == 'preferido' else 'alt'})"
        for r in rotulos
    )


def _saida_json(res: dict[str, Any], pedido_id: str | None) -> int:
    payload = {"pedido": pedido_id, **res} if pedido_id and "pedido" not in res else res
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0


# ---------------------------------------------------------------------------
# CONCEITO
# ---------------------------------------------------------------------------

def cmd_ler_conceito(cauda: list[str], tokens_orig: list[str]) -> int:
    como_json = "--json" in tokens_orig
    pos, _, erros_p = parse_opcoes(cauda, valoradas=set(), booleanas={"--json"})
    rc_err = _rejeitar_erros_parse(erros_p, ato="ler", classe="conceito", como_json=como_json)
    if rc_err is not None:
        return rc_err
    if len(pos) != 1:
        return emitir_erros([erro_item(
            "argumento-faltando" if not pos else "argumento-excedente", "ler.conceito", pos,
            ("ler conceito exige exatamente uma chave (<slug|uuid>)", "informe o slug ou uuid do conceito"),
            "acervo ler biblioteca conceito --help",
        )], como_json=como_json, exit_code=2)

    chave = pos[0].strip()
    ctx = ContextoChamada("ler.conceito", "acervo listar biblioteca conceito", chave=chave, como_json=como_json)
    dados, rc_http = executar_chamada("GET", f"/acervo/conceitos/{urllib.parse.quote(chave, safe='')}", None, ctx)
    if rc_http is not None:
        return rc_http
    if como_json:
        return _saida_json(dados, None)

    lg = dados.get("lingua") or "(sem preferido em conceito_rotulo)"
    alts = dados.get("rotulos_alternativos") or []
    alts_str = ", ".join(f"{a.get('lingua') or '?'}|{a.get('rotulo')}" for a in alts) or "(nenhum)"
    sys.stdout.write(f"conceito · versao {dados.get('versao') or '-'} · {dados.get('slug') or chave}\n")
    sys.stdout.write(f"  id               : {dados.get('id')}\n")
    sys.stdout.write(f"  rotulo           : {dados.get('rotulo')} [{lg}]\n")
    sys.stdout.write(f"  alternativos     : {alts_str}\n")
    sys.stdout.write(f"  natureza/estatuto: {dados.get('natureza')} / {dados.get('estatuto')}\n")
    if dados.get("mais_amplo"):
        sys.stdout.write(f"  mais_amplo       : {dados.get('mais_amplo')} ({dados.get('mais_amplo_tipo')})\n")
    if dados.get("endereco"):
        sys.stdout.write(f"  endereco         : {dados.get('endereco')}\n")
    sys.stdout.write(f"  obras_vivas      : {dados.get('obras_vivas', 0)}\n")
    sys.stdout.write(f"  definicao        : {dados.get('definicao')}\n")
    return 0


def _filtrar_conceitos(itens: list[dict[str, Any]], opts: dict[str, Any]) -> list[dict[str, Any]]:
    nat = opts.get("--natureza")
    est = opts.get("--estatuto")
    termo = (opts.get("--termo") or "").strip().lower()
    saida = [c for c in itens if (not nat or c.get("natureza") == nat) and (not est or c.get("estatuto") == est)]
    if not termo:
        return saida
    return [
        c for c in saida
        if termo in (c.get("slug") or "").lower()
        or termo in (c.get("rotulo") or "").lower()
        or any(termo in str(o).lower() for o in (c.get("outros_rotulos") or []))
    ]


def cmd_listar_conceito(cauda: list[str], tokens_orig: list[str]) -> int:
    como_json = "--json" in tokens_orig
    prox = "acervo listar biblioteca conceito --help"
    pos, opts, erros_p = parse_opcoes(cauda, valoradas={"--natureza", "--estatuto", "--termo"}, booleanas={"--json"})
    rc_err = _rejeitar_erros_parse(erros_p, ato="listar", classe="conceito", como_json=como_json)
    if rc_err is not None:
        return rc_err
    if pos:
        return emitir_erros([erro_item(
            "argumento-excedente", "listar.conceito", pos,
            ("use --termo, --natureza ou --estatuto para filtrar conceitos", "passe o filtro por opção nomeada"), prox,
        )], como_json=como_json, exit_code=2)

    erros_dom = [
        e for e in (
            _validar_dominio(opts.get("--natureza"), NATUREZAS, "listar.conceito.natureza", "natureza", prox),
            _validar_dominio(opts.get("--estatuto"), ESTATUTOS, "listar.conceito.estatuto", "estatuto", prox),
        ) if e is not None
    ]
    if erros_dom:
        return emitir_erros(erros_dom, como_json=como_json, exit_code=2)

    col, rc_http = executar_chamada("GET", "/acervo/conceitos", None, ContextoChamada("listar.conceito", prox, como_json=como_json))
    if rc_http is not None:
        return rc_http

    itens = _filtrar_conceitos(list((col or {}).get("itens") or []), opts)
    versao = _hash_curto([{"slug": c.get("slug"), "rotulo": c.get("rotulo"), "natureza": c.get("natureza")} for c in itens])
    if como_json:
        return _saida_json({"versao": versao, "total": len(itens), "itens": itens}, None)

    sys.stdout.write(f"conceito · versao {versao} · {len(itens)} itens\n")
    for c in itens:
        sys.stdout.write(f"  {c.get('slug')} · {c.get('rotulo')} · {c.get('natureza')}/{c.get('estatuto')}\n")
    return 0


def _campos_opcionais_criar(
    corpo: dict[str, Any],
    opts: dict[str, Any],
    pai_dict: dict[str, Any] | None,
    alts: list[dict[str, str]],
    pedido_id: str | None,
) -> dict[str, Any]:
    trata = [x.strip() for x in (opts.get("--trata-de") or "").split(",") if x.strip()]
    end = (opts.get("--endereco") or "").strip()
    extras = {
        "pai": pai_dict,
        "rotulos_alternativos": alts or None,
        "endereco": end or None,
        "filhos_exclusivos": True if opts.get("--filhos-exclusivos") else None,
        "trata_de": trata or None,
        "pedido": pedido_id,
    }
    corpo.update({k: v for k, v in extras.items() if v is not None})
    return corpo


def _validar_entrada_criar(
    slug: str,
    opts: dict[str, Any],
    *,
    ensaio: bool,
    prox: str,
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
    erros: list[dict[str, Any]] = []
    if not SLUG_RE.match(slug):
        erros.append(erro_item(
            "formato-invalido", "criar.conceito.slug", slug,
            ("slug deve usar apenas letras minúsculas, dígitos e hífen", "reescreva o slug em kebab-case ASCII"), prox,
        ))
    erros.extend([
        erro_item(
            "argumento-faltando", f"criar.conceito.{ob.lstrip('-')}", None,
            (f"{ob} é obrigatório ao criar conceito", f"informe {ob} <valor>"), prox,
        )
        for ob in ("--rotulo", "--definicao", "--natureza", "--estatuto")
        if not (opts.get(ob) or "").strip()
    ])
    nat, est, lingua = (opts.get("--natureza") or "").strip(), (opts.get("--estatuto") or "").strip(), (opts.get("--lingua") or "pt").strip()
    erros.extend([
        e for e in (
            _validar_dominio(nat, NATUREZAS, "criar.conceito.natureza", "natureza", prox),
            _validar_dominio(est, ESTATUTOS, "criar.conceito.estatuto", "estatuto", prox),
            _validar_dominio(lingua, LINGUAS, "criar.conceito.lingua", "língua", prox),
        ) if e is not None
    ])
    alts, errs_alt = _validar_rotulo_alt(opts.get("--rotulo-alt") or [], "criar.conceito", prox)
    pai_dict, errs_pai = _validar_pai_opcoes(opts, "criar.conceito", prox, exige_motivo=True)
    erros.extend([*errs_alt, *errs_pai])
    pedido_id = _resolver_pedido(opts, ensaio=ensaio, onde="criar.conceito", prox_help=prox, erros=erros)
    if erros:
        return None, None, erros

    base: dict[str, Any] = {
        "slug": slug, "rotulo": opts["--rotulo"].strip(), "lingua": lingua,
        "definicao": opts["--definicao"].strip(), "natureza": nat, "estatuto": est,
        "autor": _autor_padrao(opts.get("--autor")), "aplicar": not ensaio,
    }
    return _campos_opcionais_criar(base, opts, pai_dict, alts, pedido_id), pedido_id, []


def cmd_criar_conceito(cauda: list[str], tokens_orig: list[str], *, ensaio: bool) -> int:
    como_json = "--json" in tokens_orig
    prox = "acervo criar biblioteca conceito --help"
    pos, opts, erros_p = parse_opcoes(
        cauda,
        valoradas={
            "--rotulo", "--definicao", "--natureza", "--estatuto", "--lingua",
            "--pai", "--tipo", "--garantia", "--motivo", "--lastro",
            "--endereco", "--trata-de", "--pedido", "--autor",
        },
        repetiveis={"--rotulo-alt"},
        booleanas={"--filhos-exclusivos", "--sem-hermit", "--json"},
    )
    dicas = {
        "--sem-rotulo-alt": ("--sem-rotulo-alt só se aplica a conceito existente em 'trocar'", "acervo trocar biblioteca conceito --help"),
        "--renomear": ("para trocar o slug de conceito existente use o ato 'renomear'", "acervo renomear biblioteca conceito --help"),
        "--apply": ("'criar' já grava sem --apply; para simular use 'ensaiar criar'", "acervo ensaiar criar biblioteca conceito --help"),
    }
    rc_err = _rejeitar_erros_parse(erros_p, ato="criar", classe="conceito", como_json=como_json, dicas_nao_aplicaveis=dicas)
    if rc_err is not None:
        return rc_err
    if len(pos) != 1:
        return emitir_erros([erro_item(
            "argumento-faltando" if not pos else "argumento-excedente", "criar.conceito.slug", pos,
            ("criar conceito exige exatamente o <slug> posicional", "passe o slug canônico após 'conceito'"), prox,
        )], como_json=como_json, exit_code=2)

    slug = pos[0].strip()
    corpo, pedido_id, erros_val = _validar_entrada_criar(slug, opts, ensaio=ensaio, prox=prox)
    if erros_val or corpo is None:
        return emitir_erros(erros_val, como_json=como_json, exit_code=2)

    ctx = ContextoChamada(
        "ensaiar.criar.conceito" if ensaio else "criar.conceito",
        f"acervo ler biblioteca conceito {slug}" if not ensaio else prox,
        chave=slug, pedido_id=pedido_id, como_json=como_json, em_escrita=not ensaio,
    )
    res, rc_http = executar_chamada("POST", "/acervo/conceitos", corpo, ctx)
    if rc_http is not None:
        return rc_http

    if ensaio and not res.get("aprovado", True):
        return emitir_erros([erro_item(
            "validacao-falhou", "ensaiar.criar.conceito", res.get("conferencias"),
            ("as conferências ontológicas reprovaram o conceito proposto", "revise o pai ou a natureza propostos"), prox,
        )], como_json=como_json, exit_code=1)
    if como_json:
        return _saida_json(res, pedido_id)

    versao = res.get("versao") or "-"
    if ensaio:
        sys.stdout.write(f"ensaio aprovado · criar conceito:{slug} · versao {versao}\n")
        sys.stdout.write(f"  rotulo   : {corpo['rotulo']} [{corpo['lingua']}]\n")
        sys.stdout.write(f"  natureza : {corpo['natureza']} / {corpo['estatuto']}\n")
        return 0
    verbo_res = "ja-gravada" if res.get("estado_pedido") == "ja-gravada" else "criada"
    sys.stdout.write(f"{res.get('pedido') or pedido_id}\n{verbo_res} conceito:{slug} · versao {versao}\n")
    return 0


def _checar_conflitos_trocar(opts: dict[str, Any], prox: str) -> list[dict[str, Any]]:
    erros: list[dict[str, Any]] = []
    if not (opts.get("--motivo") or "").strip():
        erros.append(erro_item(
            "argumento-faltando", "trocar.conceito.motivo", None,
            ("trocar conceito exige --motivo registrando a razão da mudança", 'passe --motivo "..."'), prox,
        ))
    if opts.get("--filhos-exclusivos") and opts.get("--sem-filhos-exclusivos"):
        erros.append(erro_item(
            "entrada-invalida", "trocar.conceito.filhos-exclusivos",
            ["--filhos-exclusivos", "--sem-filhos-exclusivos"],
            ("não combine --filhos-exclusivos e --sem-filhos-exclusivos", "escolha apenas uma"), prox,
        ))
    if opts.get("--pai") and opts.get("--sem-pai"):
        erros.append(erro_item(
            "entrada-invalida", "trocar.conceito.pai", ["--pai", "--sem-pai"],
            ("não combine --pai e --sem-pai", "escolha apenas uma"), prox,
        ))
    erros.extend([
        e for e in (
            _validar_dominio((opts.get("--lingua") or "").strip() or None, LINGUAS, "trocar.conceito.lingua", "língua", prox),
            _validar_dominio((opts.get("--natureza") or "").strip() or None, NATUREZAS, "trocar.conceito.natureza", "natureza", prox),
            _validar_dominio((opts.get("--estatuto") or "").strip() or None, ESTATUTOS, "trocar.conceito.estatuto", "estatuto", prox),
        ) if e is not None
    ])
    return erros


def _aplicar_opcoes_trocar(corpo: dict[str, Any], opts: dict[str, Any]) -> None:
    mapa = (
        ("--rotulo", "rotulo"), ("--lingua", "lingua"), ("--definicao", "definicao"),
        ("--natureza", "natureza"), ("--estatuto", "estatuto"), ("--endereco", "endereco"),
    )
    corpo.update({campo: opts[flag].strip() for flag, campo in mapa if opts.get(flag) is not None})
    if opts.get("--filhos-exclusivos"):
        corpo["filhos_exclusivos"] = True
    elif opts.get("--sem-filhos-exclusivos"):
        corpo["filhos_exclusivos"] = False


def _montar_corpo_trocar(
    versao: str,
    opts: dict[str, Any],
    *,
    ensaio: bool,
    prox: str,
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
    erros = _checar_conflitos_trocar(opts, prox)
    alts, errs_alt = _validar_rotulo_alt(opts.get("--rotulo-alt") or [], "trocar.conceito", prox)
    erros.extend(errs_alt)
    remover = [r.strip() for r in (opts.get("--sem-rotulo-alt") or []) if r.strip()]

    corpo: dict[str, Any] = {
        "versao": versao, "motivo": (opts.get("--motivo") or "").strip(),
        "autor": _autor_padrao(opts.get("--autor")), "aplicar": not ensaio,
    }
    _aplicar_opcoes_trocar(corpo, opts)
    if opts.get("--sem-pai"):
        corpo["pai"] = None
    else:
        pai_d, errs_p = _validar_pai_opcoes(opts, "trocar.conceito", prox, exige_motivo=False)
        erros.extend(errs_p)
        if pai_d is not None:
            corpo["pai"] = pai_d
    if alts:
        corpo["rotulos_alternativos"] = alts
    if remover:
        corpo["remover_rotulos"] = remover
    if not (set(corpo) - {"versao", "motivo", "autor", "aplicar"}):
        erros.append(erro_item(
            "argumento-faltando", "trocar.conceito", None,
            ("trocar conceito exige ao menos um atributo ou rótulo a alterar", "passe --rotulo, --lingua, --rotulo-alt ou outro campo"),
            prox,
        ))
    pedido_id = _resolver_pedido(opts, ensaio=ensaio, onde="trocar.conceito", prox_help=prox, erros=erros)
    if pedido_id:
        corpo["pedido"] = pedido_id
    return (None, None, erros) if erros else (corpo, pedido_id, [])


def cmd_trocar_conceito(cauda: list[str], tokens_orig: list[str], *, ensaio: bool) -> int:
    como_json = "--json" in tokens_orig
    prox = "acervo trocar biblioteca conceito --help"
    pos, opts, erros_p = parse_opcoes(
        cauda,
        valoradas={
            "--motivo", "--rotulo", "--lingua", "--definicao", "--natureza", "--estatuto",
            "--endereco", "--pai", "--tipo", "--garantia", "--lastro", "--pedido", "--autor",
        },
        repetiveis={"--rotulo-alt", "--sem-rotulo-alt"},
        booleanas={"--filhos-exclusivos", "--sem-filhos-exclusivos", "--sem-pai", "--json"},
    )
    dicas = {
        "--slug": ("slug é chave do conceito e muda apenas pelo ato próprio 'renomear'", "acervo renomear biblioteca conceito --help"),
        "--renomear": ("slug é chave do conceito e muda apenas pelo ato próprio 'renomear'", "acervo renomear biblioteca conceito --help"),
        "--apply": ("'trocar' já grava sem --apply; para simular use 'ensaiar trocar'", "acervo ensaiar trocar biblioteca conceito --help"),
    }
    rc_err = _rejeitar_erros_parse(erros_p, ato="trocar", classe="conceito", como_json=como_json, dicas_nao_aplicaveis=dicas)
    if rc_err is not None:
        return rc_err
    if len(pos) != _PAR_ARGS:
        eh_falta = len(pos) < _PAR_ARGS
        alvo_dica = pos[0] if pos else "<slug>"
        return emitir_erros([erro_item(
            "argumento-faltando" if eh_falta else "argumento-excedente", "trocar.conceito", pos,
            (
                "trocar conceito exige <slug> e <versao> posicionais",
                "leia o conceito antes para obter a <versao>" if eh_falta else "passe os campos por opções nomeadas",
            ),
            f"acervo ler biblioteca conceito {alvo_dica}" if eh_falta else prox,
        )], como_json=como_json, exit_code=2)

    chave, versao = pos[0].strip(), pos[1].strip()
    corpo, pedido_id, erros_val = _montar_corpo_trocar(versao, opts, ensaio=ensaio, prox=prox)
    if erros_val or corpo is None:
        return emitir_erros(erros_val, como_json=como_json, exit_code=2)

    ctx = ContextoChamada(
        "ensaiar.trocar.conceito" if ensaio else "trocar.conceito",
        f"acervo ler biblioteca conceito {chave}",
        chave=chave, pedido_id=pedido_id, como_json=como_json, em_escrita=not ensaio,
    )
    res, rc_http = executar_chamada("PATCH", f"/acervo/conceitos/{urllib.parse.quote(chave, safe='')}", corpo, ctx)
    if rc_http is not None:
        return rc_http

    if ensaio and not res.get("aprovado", True):
        colisoes = res.get("colisoes") or []
        det = "colisão de rótulo: " + ", ".join(f"{c['rotulo']} ({c['conceito']})" for c in colisoes) if colisoes else "conferência reprovou"
        return emitir_erros([erro_item(
            "validacao-falhou", "ensaiar.trocar.conceito", det,
            ("rótulos exclusivos por conceito e conferências sem violação nova", "escolha outro rótulo ou desfaça o conflito"),
            f"acervo ler biblioteca conceito {chave}",
        )], como_json=como_json, exit_code=1)
    if como_json:
        return _saida_json(res, pedido_id)

    slug_res = (res.get("conceito") or {}).get("slug") or chave
    v_ant, v_dep = res.get("versao_antes") or versao, res.get("versao") or "-"
    if ensaio:
        antes, depois = res.get("antes") or {}, res.get("depois") or {}
        sys.stdout.write(f"ensaio aprovado · trocar conceito:{slug_res} · versao {v_ant} -> {v_dep}\n")
        sys.stdout.write(f"  rotulo  : {antes.get('rotulo')} -> {depois.get('rotulo')}\n")
        sys.stdout.write(f"  rotulos : {_formatar_rotulos_lista(antes.get('rotulos') or [])}\n")
        sys.stdout.write(f"         -> {_formatar_rotulos_lista(depois.get('rotulos') or [])}\n")
        return 0
    verbo_res = "ja-gravada" if res.get("estado_pedido") == "ja-gravada" else "gravada"
    sys.stdout.write(f"{res.get('pedido') or pedido_id}\n{verbo_res} conceito:{slug_res} · versao {v_ant} -> {v_dep}\n")
    return 0


def _montar_corpo_renomear(
    novo: str,
    opts: dict[str, Any],
    *,
    ensaio: bool,
    prox: str,
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
    erros: list[dict[str, Any]] = []
    if not SLUG_RE.match(novo):
        erros.append(erro_item(
            "formato-invalido", "renomear.conceito.slug-novo", novo,
            ("slug novo deve usar apenas letras minúsculas, dígitos e hífen", "reescreva em kebab-case ASCII"), prox,
        ))
    motivo = (opts.get("--motivo") or "").strip()
    if not motivo:
        erros.append(erro_item(
            "argumento-faltando", "renomear.conceito.motivo", None,
            ("renomear conceito exige --motivo", 'passe --motivo "..."'), prox,
        ))
    pedido_id = _resolver_pedido(opts, ensaio=ensaio, onde="renomear.conceito", prox_help=prox, erros=erros)
    if erros:
        return None, None, erros
    corpo: dict[str, Any] = {"slug": novo, "motivo": motivo, "autor": _autor_padrao(opts.get("--autor")), "aplicar": not ensaio}
    if pedido_id:
        corpo["pedido"] = pedido_id
    return corpo, pedido_id, []


def cmd_renomear_conceito(cauda: list[str], tokens_orig: list[str], *, ensaio: bool) -> int:
    como_json = "--json" in tokens_orig
    prox = "acervo renomear biblioteca conceito --help"
    pos, opts, erros_p = parse_opcoes(cauda, valoradas={"--motivo", "--pedido", "--autor"}, booleanas={"--json"})
    dicas = {
        fl: ("renomear altera apenas a chave (slug); para atributos e rótulos use 'trocar'", "acervo trocar biblioteca conceito --help")
        for fl in ("--rotulo", "--lingua", "--definicao", "--rotulo-alt", "--sem-rotulo-alt")
    }
    dicas["--apply"] = ("'renomear' já grava sem --apply; para simular use 'ensaiar renomear'", "acervo ensaiar renomear biblioteca conceito --help")
    rc_err = _rejeitar_erros_parse(erros_p, ato="renomear", classe="conceito", como_json=como_json, dicas_nao_aplicaveis=dicas)
    if rc_err is not None:
        return rc_err
    if len(pos) != _PAR_ARGS:
        return emitir_erros([erro_item(
            "argumento-faltando" if len(pos) < _PAR_ARGS else "argumento-excedente", "renomear.conceito", pos,
            ("renomear conceito exige <slug-atual> e <slug-novo> posicionais", "informe o slug atual e o slug novo"), prox,
        )], como_json=como_json, exit_code=2)

    velho, novo = pos[0].strip(), pos[1].strip()
    corpo, pedido_id, erros_val = _montar_corpo_renomear(novo, opts, ensaio=ensaio, prox=prox)
    if erros_val or corpo is None:
        return emitir_erros(erros_val, como_json=como_json, exit_code=2)
    ctx = ContextoChamada(
        "ensaiar.renomear.conceito" if ensaio else "renomear.conceito",
        f"acervo ler biblioteca conceito {novo}" if not ensaio else prox,
        chave=velho, pedido_id=pedido_id, como_json=como_json, em_escrita=not ensaio,
    )
    res, rc_http = executar_chamada("PATCH", f"/acervo/conceitos/{urllib.parse.quote(velho, safe='')}", corpo, ctx)
    if rc_http is not None:
        return rc_http
    if ensaio and not res.get("aprovado", True):
        return emitir_erros([erro_item(
            "validacao-falhou", "ensaiar.renomear.conceito", res.get("conferencias"),
            ("conferência ontológica reprovou a renomeação", "verifique as conferências reportadas"),
            f"acervo ler biblioteca conceito {velho}",
        )], como_json=como_json, exit_code=1)
    if como_json:
        return _saida_json(res, pedido_id)
    if ensaio:
        sys.stdout.write(f"ensaio aprovado · renomear conceito:{velho} -> {novo}\n")
        return 0
    verbo_res = "ja-gravada" if res.get("estado_pedido") == "ja-gravada" else "renomeada"
    sys.stdout.write(f"{res.get('pedido') or pedido_id}\n{verbo_res} conceito:{velho} -> {novo}\n")
    return 0


def cmd_gravar_recusado(tokens: list[str]) -> int:
    como_json = "--json" in tokens
    pos = [t for t in tokens if not t.startswith("-")]
    if pos and pos[0] == "biblioteca":
        pos = pos[1:]
    classe = pos[0] if pos else "conceito"
    alvo = pos[1] if len(pos) > 1 else "<slug>"
    if classe in ("indicacao", "indicacoes"):
        rc_msg = (
            "indicação é fila curada: transiciona por 'admitir' ou 'descartar', nunca por 'gravar'",
            "use 'admitir' para acolher com garantia viva ou 'descartar' para recusar com motivo",
        )
        prox = "acervo admitir biblioteca indicacao --help"
    else:
        rc_msg = (
            "conceito é classe guardada em banco: usa 'criar' para novo e 'trocar <versao>' para existente",
            "use 'acervo criar biblioteca conceito' ou leia a versão e use 'acervo trocar biblioteca conceito'",
        )
        prox = f"acervo ler biblioteca conceito {alvo}"
    return emitir_erros([erro_item("ato-recusado", "acervo.gravar", "gravar", rc_msg, prox)], como_json=como_json, exit_code=2)


# ---------------------------------------------------------------------------
# INDICACAO
# ---------------------------------------------------------------------------

def _imprimir_indicacoes_agrupadas(itens: list[dict[str, Any]], *, como_json: bool) -> int:
    versao = _hash_curto(itens)
    if como_json:
        return _saida_json({"versao": versao, "total": len(itens), "itens": itens}, None)
    sys.stdout.write(f"indicacao · versao {versao} · {len(itens)} itens\n")
    rot_acao = {
        "criar": "criar",
        "ligar_existente": "ligar ao existente",
        "sem_garantia": "sem garantia (só obra retirada)",
    }
    for it in itens:
        acao = it.get("acao") or "criar"
        alvo = it.get("conceito") or it.get("slug") or ""
        suf_alvo = f" {alvo}" if acao != "sem_garantia" else ""
        ret = len(it.get("de_obra_retirada") or [])
        extra_ret = f" · {ret} de obra retirada" if ret else ""
        sys.stdout.write(
            f"  {it.get('termo')} ({it.get('slug')}) -> {rot_acao.get(acao, acao)}{suf_alvo}"
            f" · {it.get('obras_contagem', 0)} obra(s) viva(s){extra_ret}\n"
        )
    return 0


def cmd_listar_indicacao(cauda: list[str], tokens_orig: list[str]) -> int:
    como_json = "--json" in tokens_orig
    prox = "acervo listar biblioteca indicacao --help"
    pos, opts, erros_p = parse_opcoes(
        cauda, valoradas={"--lote", "--estado", "--termo"}, booleanas={"--desagrupado", "--json"},
    )
    rc_err = _rejeitar_erros_parse(erros_p, ato="listar", classe="indicacao", como_json=como_json)
    if rc_err is not None:
        return rc_err
    if len(pos) > 1 or (pos and opts.get("--lote")):
        return emitir_erros([erro_item(
            "entrada-invalida", "listar.indicacao.lote", pos,
            ("informe no máximo um lote (posicional [<lote|todas>] ou --lote)", "escolha uma única forma"), prox,
        )], como_json=como_json, exit_code=2)

    lote_pos = pos[0].strip() if pos else None
    lote = opts.get("--lote") or (None if lote_pos in (None, "todas") else lote_pos)
    estado = (opts.get("--estado") or "pendente").strip()
    err_est = _validar_dominio(estado, ESTADOS_IND, "listar.indicacao.estado", "--estado", prox)
    if err_est:
        return emitir_erros([err_est], como_json=como_json, exit_code=2)

    termo = (opts.get("--termo") or "").strip() or None
    ctx = ContextoChamada("listar.indicacao", prox, como_json=como_json)
    if not opts.get("--desagrupado") and estado == "pendente" and not termo:
        plano, rc_http = executar_chamada("POST", "/acervo/indicacoes", {"lote_id": lote, "aplicar": False}, ctx)
        if rc_http is not None:
            return rc_http
        return _imprimir_indicacoes_agrupadas(list((plano or {}).get("itens") or []), como_json=como_json)

    qs = {"agrupar": "0", "estado": estado, **({"lote": lote} if lote else {}), **({"termo": termo} if termo else {})}
    col, rc_http = executar_chamada("GET", f"/acervo/indicacoes?{urllib.parse.urlencode(qs)}", None, ctx)
    if rc_http is not None:
        return rc_http
    itens = list((col or {}).get("itens") or [])
    versao = (col or {}).get("versao") or _hash_curto(itens)
    if como_json:
        return _saida_json({"versao": versao, "total": len(itens), "itens": itens}, None)
    sys.stdout.write(f"indicacao · versao {versao} · {len(itens)} itens\n")
    for it in itens:
        tag = "obra retirada" if it.get("obra_retirada") else "obra viva"
        sys.stdout.write(f"  {it.get('id')} · {it.get('termo')} · {it.get('estado')} · {it.get('obra_id')} ({tag})\n")
    return 0


def cmd_ler_indicacao(cauda: list[str], tokens_orig: list[str]) -> int:
    como_json = "--json" in tokens_orig
    pos, _, erros_p = parse_opcoes(cauda, valoradas=set(), booleanas={"--json"})
    rc_err = _rejeitar_erros_parse(erros_p, ato="ler", classe="indicacao", como_json=como_json)
    if rc_err is not None:
        return rc_err
    if len(pos) != 1:
        return emitir_erros([erro_item(
            "argumento-faltando" if not pos else "argumento-excedente", "ler.indicacao", pos,
            ("ler indicacao exige exatamente uma chave (<uuid|termo|slug>)", "informe o uuid ou o termo/slug"),
            "acervo ler biblioteca indicacao --help",
        )], como_json=como_json, exit_code=2)

    chave = pos[0].strip()
    ctx = ContextoChamada("ler.indicacao", "acervo listar biblioteca indicacao", chave=chave, como_json=como_json)
    dados, rc_http = executar_chamada("GET", f"/acervo/indicacoes/{urllib.parse.quote(chave, safe='')}", None, ctx)
    if rc_http is not None:
        return rc_http
    if como_json:
        return _saida_json(dados, None)

    versao = dados.get("versao") or "-"
    dest = dados.get("destino") or {}
    if dados.get("tipo") == "indicacao":
        tag = "retirada" if dados.get("obra_retirada") else "viva"
        sys.stdout.write(f"indicacao · versao {versao} · {dados.get('id')}\n")
        sys.stdout.write(f"  termo   : {dados.get('termo')} ({dados.get('slug')})\n")
        sys.stdout.write(f"  estado  : {dados.get('estado')}\n")
        sys.stdout.write(f"  obra    : {dados.get('obra_id')} ({tag}) — {dados.get('obra_titulo') or '-'}\n")
    else:
        sys.stdout.write(f"indicacao · versao {versao} · {dados.get('slug')}\n")
        sys.stdout.write(f"  termo          : {dados.get('termo')}\n")
        sys.stdout.write(f"  obras_vivas    : {dados.get('obras_contagem', 0)}\n")
        sys.stdout.write(f"  obra_retirada  : {len(dados.get('de_obra_retirada') or [])} indicação(ões)\n")
    sys.stdout.write(f"  destino        : {dest.get('acao')} {dest.get('conceito') or dest.get('motivo') or ''}\n")
    return 0


def _montar_corpo_decisao_indicacao(
    decisao: str,
    pos: list[str],
    opts: dict[str, Any],
    *,
    ensaio: bool,
    prox: str,
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
    erros: list[dict[str, Any]] = []
    if len(pos) > 1 or (pos and opts.get("--lote")):
        erros.append(erro_item(
            "entrada-invalida", f"{decisao}.indicacao.lote", pos,
            ("informe no máximo um lote (posicional [<lote|todas>] ou --lote)", "escolha apenas uma forma"), prox,
        ))
    lote_pos = pos[0].strip() if pos else None
    lote = opts.get("--lote") or (None if lote_pos in (None, "todas") else lote_pos)
    motivo = (opts.get("--motivo") or "").strip()
    if not motivo:
        erros.append(erro_item(
            "argumento-faltando", f"{decisao}.indicacao.motivo", None,
            (f"{decisao} indicacao exige --motivo", 'informe --motivo "..."'), prox,
        ))
    termos = [t.strip() for t in (opts.get("--termos") or "").split(",") if t.strip()] or None
    ids = [i.strip() for i in (opts.get("--ids") or "").split(",") if i.strip()] or None
    if lote is None and lote_pos != "todas" and not termos and not ids:
        erros.append(erro_item(
            "argumento-faltando", f"{decisao}.indicacao.alvo", None,
            (f"{decisao} exige alvo explícito (<lote>, 'todas', --termos ou --ids)", "especifique o alvo"), prox,
        ))

    corpo: dict[str, Any] = {
        "lote_id": lote, "decisao": decisao, "motivo": motivo,
        "autor": _autor_padrao(opts.get("--autor")), "aplicar": not ensaio,
    }
    if termos:
        corpo["termos"] = termos
    if ids:
        corpo["ids"] = ids
    if decisao == "admitir":
        nat = (opts.get("--natureza") or "modelo").strip()
        est = (opts.get("--estatuto") or "doutrinario").strip()
        lg = (opts.get("--lingua") or "pt").strip()
        for err_d in (
            _validar_dominio(nat, NATUREZAS, "admitir.indicacao.natureza", "natureza", prox),
            _validar_dominio(est, ESTATUTOS, "admitir.indicacao.estatuto", "estatuto", prox),
            _validar_dominio(lg, LINGUAS, "admitir.indicacao.lingua", "língua", prox),
        ):
            if err_d:
                erros.append(err_d)
        corpo.update(natureza=nat, estatuto=est, lingua=lg)

    pedido_id = _resolver_pedido(opts, ensaio=ensaio, onde=f"{decisao}.indicacao", prox_help=prox, erros=erros)
    if pedido_id:
        corpo["pedido"] = pedido_id
    return (None, None, erros) if erros else (corpo, pedido_id, [])


def _imprimir_resultado_decisao_indicacao(
    decisao: str,
    res: dict[str, Any],
    pedido_id: str | None,
    motivo: str,
    *,
    ensaio: bool,
) -> int:
    if ensaio:
        if decisao == "admitir":
            itens = res.get("itens") or []
            sys.stdout.write(f"ensaio aprovado · admitir indicacao · {len(itens)} termo(s)\n")
            for it in itens:
                acao = "ligar ao existente" if it.get("acao") == "ligar_existente" else "criar"
                ret = len(it.get("de_obra_retirada") or [])
                extra = f" · {ret} de obra retirada a descartar" if ret else ""
                sys.stdout.write(
                    f"  {it.get('termo')} -> {acao} {it.get('conceito') or it.get('slug')}"
                    f" · {it.get('obras_contagem', 0)} obra(s) viva(s){extra}\n"
                )
        else:
            descs = res.get("descartes") or []
            sys.stdout.write(
                f"ensaio aprovado · descartar indicacao · {len(descs)} termo(s)"
                f" · {sum(d.get('indicacoes', 0) for d in descs)} indicação(ões)\n"
            )
        return 0

    ja = res.get("estado_pedido") == "ja-gravada"
    sys.stdout.write(f"{res.get('pedido') or pedido_id}\n")
    if decisao == "admitir":
        criados, ligados = res.get("criados") or [], res.get("ligados_a_existente") or []
        sys.stdout.write(
            f"{'ja-gravada' if ja else 'admitida'} indicacao · {res.get('indicacoes_admitidas', 0)} admitida(s)"
            f" · {len(criados)} criado(s) · {len(ligados)} ligado(s) ao existente"
            f" · {res.get('indicacoes_descartadas', 0)} de obra retirada descartada(s)\n"
        )
    else:
        sys.stdout.write(
            f"{'ja-gravada' if ja else 'descartada'} indicacao"
            f" · {res.get('indicacoes_descartadas', 0)} descartada(s) · motivo: {motivo}\n"
        )
    return 0


def cmd_decidir_indicacao(decisao: str, cauda: list[str], tokens_orig: list[str], *, ensaio: bool) -> int:
    como_json = "--json" in tokens_orig
    prox = f"acervo {decisao} biblioteca indicacao --help"
    valoradas = {"--motivo", "--termos", "--ids", "--lote", "--pedido", "--autor"}
    dicas: dict[str, tuple[str, str]] = {
        "--indicacoes": ("o lote/escopo é posicional ([<lote|todas>]) ou --lote <id>", prox),
        "--apply": (f"'{decisao}' já grava sem --apply; para simular use 'ensaiar {decisao}'", f"acervo ensaiar {decisao} biblioteca indicacao --help"),
    }
    if decisao == "admitir":
        valoradas |= {"--natureza", "--estatuto", "--lingua"}
        dicas["--descartar"] = ("para descartar indicações use o ato próprio 'descartar'", "acervo descartar biblioteca indicacao --help")
    else:
        for fl in ("--natureza", "--estatuto", "--lingua"):
            dicas[fl] = (f"{fl} só se aplica em 'admitir', não em 'descartar'", prox)

    pos, opts, erros_p = parse_opcoes(cauda, valoradas=valoradas, booleanas={"--json"})
    rc_err = _rejeitar_erros_parse(erros_p, ato=decisao, classe="indicacao", como_json=como_json, dicas_nao_aplicaveis=dicas)
    if rc_err is not None:
        return rc_err

    corpo, pedido_id, erros_val = _montar_corpo_decisao_indicacao(decisao, pos, opts, ensaio=ensaio, prox=prox)
    if erros_val or corpo is None:
        return emitir_erros(erros_val, como_json=como_json, exit_code=2)

    ctx = ContextoChamada(
        f"ensaiar.{decisao}.indicacao" if ensaio else f"{decisao}.indicacao",
        "acervo listar biblioteca indicacao" if not ensaio else prox,
        pedido_id=pedido_id, como_json=como_json, em_escrita=not ensaio,
    )
    res, rc_http = executar_chamada("POST", "/acervo/indicacoes", corpo, ctx)
    if rc_http is not None:
        return rc_http

    if ensaio and not res.get("aprovado", True):
        sem_gar = [it for it in (res.get("itens") or []) if it.get("acao") == "sem_garantia"]
        slugs_sg = ",".join(it.get("slug") or it.get("termo") or "" for it in sem_gar)
        return emitir_erros([erro_item(
            "garantia-retirada", "ensaiar.admitir.indicacao", [it.get("termo") for it in sem_gar],
            ("obra retirada não sustenta indicação como garantia literária", "descarte os termos sem obra viva antes de admitir"),
            f'acervo descartar biblioteca indicacao --termos "{slugs_sg}" --motivo "obra retirada"',
        )], como_json=como_json, exit_code=1)
    if como_json:
        return _saida_json(res, pedido_id)
    return _imprimir_resultado_decisao_indicacao(decisao, res, pedido_id, corpo["motivo"], ensaio=ensaio)


# ---------------------------------------------------------------------------
# Despacho
# ---------------------------------------------------------------------------

def _imprimir_ajuda(ato: str, resto: list[str]) -> int:
    sem_flags = [t for t in resto if not t.startswith("-")]
    if sem_flags and sem_flags[0] == "biblioteca":
        sem_flags = sem_flags[1:]
    cl = sem_flags[0] if sem_flags else ""
    chave = f"{ato}:{'indicacao' if cl in ('indicacao', 'indicacoes') else 'conceito'}" if ato in ("ler", "listar") else ato
    sys.stdout.write((AJUDA_POR_ATO.get(chave) or AJUDA_POR_ATO["ensaiar"]) + "\n")
    return 0


def _despachar_classe(ato: str, classe_tok: str, cauda: list[str], resto: list[str], *, ensaio: bool) -> int:
    como_json = "--json" in resto
    if classe_tok == "conceitos" and ato != "listar":
        return emitir_erros([erro_item(
            "classe-no-plural", f"acervo.{ato}", classe_tok,
            ("o nome da classe no padrão do verbo é singular: 'conceito'", "troque 'conceitos' por 'conceito'"),
            f"acervo {ato} biblioteca conceito --help",
        )], como_json=como_json, exit_code=2)

    if classe_tok in ("conceito", "conceitos"):
        leitura_c = {"ler": cmd_ler_conceito, "listar": cmd_listar_conceito}
        escrita_c = {"criar": cmd_criar_conceito, "trocar": cmd_trocar_conceito, "renomear": cmd_renomear_conceito}
        if ato in leitura_c:
            return leitura_c[ato](cauda, resto)
        if ato in escrita_c:
            return escrita_c[ato](cauda, resto, ensaio=ensaio)
        return emitir_erros([erro_item(
            "ato-nao-aplicavel", f"acervo.{ato}", classe_tok,
            (f"o ato '{ato}' não se aplica a 'conceito'", "use ler, listar, criar, trocar ou renomear"),
            "acervo ler biblioteca conceito --help",
        )], como_json=como_json, exit_code=2)

    if classe_tok in ("indicacao", "indicacoes"):
        leitura_i = {"listar": cmd_listar_indicacao, "ler": cmd_ler_indicacao}
        if ato in leitura_i:
            return leitura_i[ato](cauda, resto)
        if ato in ("admitir", "descartar"):
            return cmd_decidir_indicacao(ato, cauda, resto, ensaio=ensaio)
        return emitir_erros([erro_item(
            "ato-nao-aplicavel", f"acervo.{ato}", classe_tok,
            (f"o ato '{ato}' não se aplica a 'indicacao'", "use listar, ler, admitir ou descartar"),
            "acervo admitir biblioteca indicacao --help",
        )], como_json=como_json, exit_code=2)

    return emitir_erros([erro_item(
        "classe-desconhecida", f"acervo.{ato}", classe_tok,
        ("classe esperada: 'conceito' ou 'indicacao'", "informe 'conceito' ou 'indicacao'"),
        f"acervo {ato} --help",
    )], como_json=como_json, exit_code=2)


def despachar(argv: list[str], *, ensaio: bool = False) -> int:
    como_json = "--json" in argv
    if not argv:
        return emitir_erros([erro_item(
            "argumento-faltando", "acervo", [], ("informe o ato a executar", "consulte a ajuda com --help"), "acervo --ajuda",
        )], como_json=como_json, exit_code=2)

    ato, resto = argv[0], argv[1:]
    if ato == "gravar":
        return cmd_gravar_recusado(resto)
    if ato == "ensaiar":
        if not resto or resto[0] in ("-h", "--help", "--ajuda"):
            sys.stdout.write(AJUDA_POR_ATO["ensaiar"] + "\n")
            return 0
        if resto[0] not in ATOS_ESCRITA:
            return emitir_erros([erro_item(
                "ato-desconhecido", "acervo.ensaiar", resto[0],
                ("ensaiar antecede um ato de escrita: criar, trocar, renomear, admitir ou descartar", "passe um ato de escrita válido"),
                "acervo ensaiar --help",
            )], como_json=como_json, exit_code=2)
        return despachar(resto, ensaio=True)

    if any(t in ("-h", "--help", "--ajuda") for t in resto):
        return _imprimir_ajuda(ato, resto)

    idx = 1 if resto and resto[0] == "biblioteca" else 0
    if resto and resto[0] in ("casa", "registro", "obra"):
        return emitir_erros([erro_item(
            "particao-invalida", f"acervo.{ato}", resto[0],
            ("conceito e indicacao pertencem à partição 'biblioteca'", "use 'biblioteca' ou omita a partição"),
            f"acervo {ato} --help",
        )], como_json=como_json, exit_code=2)
    if idx >= len(resto) or resto[idx].startswith("-"):
        padrao_cl = "indicacao" if ato in ("admitir", "descartar") else "conceito"
        return emitir_erros([erro_item(
            "argumento-faltando", f"acervo.{ato}.classe", resto[idx:],
            (f"informe a classe alvo ('{padrao_cl}')", f"chame 'acervo {ato} biblioteca {padrao_cl} ...'"),
            f"acervo {ato} --help",
        )], como_json=como_json, exit_code=2)

    return _despachar_classe(ato, resto[idx], resto[idx + 1 :], resto, ensaio=ensaio)


def main(argv: list[str] | None = None) -> int:
    return despachar(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
