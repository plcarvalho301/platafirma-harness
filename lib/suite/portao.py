"""Portão de integração na main: cobra o veredito verde da esteira para o par de árvores e grava as fichas (#4299).

O par é a árvore da mudança e a da ponta atual da main. O histórico de vereditos se lê pelo coletor da release
servida, nunca pelo da árvore testada, porque o ramo que mede a si mesmo pode se aprovar. A decisão tem quatro
saídas, nesta ordem:

1. veredito verde para o par exato: integra (saída 0);
2. veredito vermelho ou não medido para o par exato: recusa por falha (saída 1);
3. nenhum veredito para o par, mas veredito para a árvore da mudança sobre outra main: recusa por avanço da main;
4. nenhum veredito para a árvore da mudança: recusa por falta de rodada.

Integrada a mudança, as fichas de verificação que a esteira ensaiou se gravam na Olaria: `criar`, e `trocar` com a
versão lida quando a chave já existe. A chave de serviço só vai no cabeçalho, nunca na saída.

O escape do dono (#4301) integra sem veredito verde e vale igual em qualquer sessão, porque toda sessão roda em nome do
dono. Exige o motivo: sem ele (vazio ou só espaços) o escape para antes de integrar, com saída 1. Com o motivo, grava o
evento no registro só de acréscimo da instância, sem corte (a guarda de 20 anos se cumpre por não haver corte), e só
depois o chamador integra e repete o motivo no pedido e no commit. O escape não grava fichas da esteira: sem verde não há
ficha ensaiada válida.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml

OLARIA_URL_PADRAO = "http://127.0.0.1:8103"
CHAVE_OLARIA_COFRE = Path("/srv/platafirma/casa/segredos/olaria/OLARIA_CHAVE")
ESTADOS_RECUSA = ("vermelho", "nao-medido")
_HTTP_OK = 200

Categoria = Literal["verde", "falha", "falta-de-rodada", "avanco-da-main"]


class OlariaGravacaoErro(RuntimeError):
    """A Olaria recusou ou não respondeu a gravação de uma ficha."""


class GravadorFichasOntologia(Protocol):
    def gravar_fichas(self, fichas: Sequence[Mapping[str, Any]]) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class DecisaoPortao:
    aprovado: bool
    categoria: Categoria
    codigo_saida: int
    mensagem: str
    arvore_mudanca: str
    arvore_main: str
    registro: dict[str, Any] | None
    fichas_gravadas: tuple[str, ...] = field(default=())

    def como_dict(self) -> dict[str, Any]:
        return {
            "aprovado": self.aprovado,
            "categoria": self.categoria,
            "codigo_saida": self.codigo_saida,
            "mensagem": self.mensagem,
            "arvore_mudanca": self.arvore_mudanca,
            "arvore_main": self.arvore_main,
            "registro": self.registro,
            "fichas_gravadas": list(self.fichas_gravadas),
        }


# -- o par de árvores ---------------------------------------------------------------------------------------------------


def _arvore_de(raiz: Path | None, rev: str) -> str:
    """Resolve a revisão para o hash da árvore; sem git, ou com revisão que o git não conhece, vale o texto dado."""
    if raiz is not None and (raiz / ".git").exists():
        r = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "--verify", "--quiet", f"{rev}^{{tree}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return rev


def _listar_vereditos(repositorio: str, pasta_vereditos: str | Path | None) -> list[dict[str, Any]]:
    if pasta_vereditos is not None:
        from suite.coletor import listar_vereditos

        return listar_vereditos(repositorio, pasta=pasta_vereditos)
    from suite.esteira import carregar_coletor_servido

    return carregar_coletor_servido().listar_vereditos(repositorio)


# -- a decisão ----------------------------------------------------------------------------------------------------------


def decidir(registros: Sequence[Mapping[str, Any]], repositorio: str, arvore_mudanca: str, arvore_main: str) -> DecisaoPortao:
    """Aplica as quatro regras sobre o histórico do repositório; o registro mais recente de cada par vence."""
    do_par: dict[str, Any] | None = None
    da_mudanca: dict[str, Any] | None = None
    for reg in reversed(registros):
        if reg.get("arvore_mudanca") != arvore_mudanca:
            continue
        if da_mudanca is None:
            da_mudanca = dict(reg)
        if reg.get("arvore_main") == arvore_main:
            do_par = dict(reg)
            break

    par = (arvore_mudanca, arvore_main)
    if do_par is not None:
        estado = str(do_par.get("estado") or "nao-medido")
        if estado == "verde":
            return DecisaoPortao(True, "verde", 0, f"portão da main: verde — a esteira aprovou o par de {repositorio}", *par, do_par)
        motivo = do_par.get("motivo")
        reprovados = do_par.get("casos_reprovados") or []
        detalhe = f"; reprovados: {', '.join(map(str, reprovados))}" if reprovados else ""
        detalhe += f"; motivo: {motivo}" if motivo else ""
        return DecisaoPortao(
            False,
            "falha",
            1,
            f"portão da main: falha — a esteira reprovou o par de {repositorio} (estado {estado}{detalhe}); "
            "conserte o código ou o teste e empurre de novo",
            *par,
            do_par,
        )
    if da_mudanca is not None:
        return DecisaoPortao(
            False,
            "avanco-da-main",
            1,
            f"portão da main: avanço da main — a main avançou depois da rodada; atualize o ramo com repo sincronizar {repositorio}",
            *par,
            da_mudanca,
        )
    return DecisaoPortao(
        False,
        "falta-de-rodada",
        1,
        f"portão da main: falta de rodada — falta a rodada da esteira para o par de árvores de {repositorio}; espere a rodada",
        *par,
        None,
    )


def avaliar_portao(
    repositorio: str,
    *,
    arvore: str | Path | None = None,
    mudanca: str | None = None,
    base: str | None = None,
    pasta_vereditos: str | Path | None = None,
) -> DecisaoPortao:
    raiz = Path(arvore).resolve() if arvore is not None else None
    arvore_mudanca = _arvore_de(raiz, mudanca or "HEAD")
    arvore_main = _arvore_de(raiz, base or "origin/main")
    return decidir(_listar_vereditos(repositorio, pasta_vereditos), repositorio, arvore_mudanca, arvore_main)


# -- a gravação das fichas ----------------------------------------------------------------------------------------------


def _novo_pedido() -> str:
    """UUID v7: 48 bits de milissegundos, a versão, 12 bits ao acaso, a variante e 62 ao acaso."""
    ms = int(time.time() * 1000)
    acaso = int.from_bytes(secrets.token_bytes(10), "big")
    valor = (ms & ((1 << 48) - 1)) << 80
    valor |= 0x7 << 76
    valor |= ((acaso >> 68) & 0xFFF) << 64
    valor |= 0b10 << 62
    valor |= acaso & ((1 << 62) - 1)
    h = f"{valor:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _chave_olaria(env: Mapping[str, str]) -> str:
    if env.get("OLARIA_CHAVE"):
        return env["OLARIA_CHAVE"].strip()
    try:
        return CHAVE_OLARIA_COFRE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


class GravadorOlaria:
    """Grava fichas de verificação na Olaria: `criar`, e `ler` + `trocar` quando a chave já existe."""

    def __init__(self, url: str | None = None, chave: str | None = None, sujeito: str | None = None,
                 timeout_s: float = 60.0, env: Mapping[str, str] | None = None) -> None:
        env = os.environ if env is None else env
        self.url = (url or env.get("OLARIA_URL") or OLARIA_URL_PADRAO).rstrip("/")
        self._chave = chave if chave is not None else _chave_olaria(env)
        self.sujeito = sujeito or env.get("PF_CADEIRA") or "engenharia"
        self.timeout_s = timeout_s

    def _post(self, rota: str, corpo: dict[str, Any], pedido: str = "") -> tuple[int, dict[str, Any]]:
        req = urllib.request.Request(self.url + rota, data=json.dumps(corpo, ensure_ascii=False).encode("utf-8"), method="POST")
        req.add_header("X-Olaria-Chave", self._chave)
        req.add_header("X-Olaria-Sujeito", self.sujeito)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("User-Agent", "suite-portao")
        req.add_header("X-Olaria-Origem", "suite portao")
        if pedido:
            req.add_header("X-Olaria-Pedido", pedido)
            req.add_header("X-Olaria-Fornada", pedido)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                bruto, status = resp.read(), resp.status
        except urllib.error.HTTPError as exc:
            bruto, status = exc.read(), exc.code
        except (urllib.error.URLError, TimeoutError, socket.timeout, http.client.HTTPException, OSError) as exc:
            raise OlariaGravacaoErro(f"Olaria sem resposta em {self.url}: {exc}") from exc
        try:
            dados = json.loads(bruto or b"{}")
        except ValueError:
            dados = {"erro": bruto[:300].decode("utf-8", "replace")}
        return status, dados if isinstance(dados, dict) else {"erro": str(dados)[:300]}

    def _gravar_uma(self, ficha: Mapping[str, Any]) -> str:
        chave = str(ficha.get("chave") or "")
        classe = str(ficha.get("classe") or "")
        texto = yaml.safe_dump({"fichas": [dict(ficha)]}, sort_keys=False, allow_unicode=True, default_flow_style=False)
        pedido = _novo_pedido()
        status, corpo = self._post("/criar", {"yaml": texto}, pedido)
        if status == _HTTP_OK:
            return chave
        codigos = [str(e.get("codigo")) for e in corpo.get("erros") or [] if isinstance(e, dict)]
        if "ficha-chave-ja-existe" not in codigos:
            raise OlariaGravacaoErro(f"criar {chave} recusado (status {status}): {corpo.get('erro') or codigos}")
        status_l, lido = self._post("/ler", {"classe": classe, "chaves": [chave], "fichas": True})
        versao = str(lido.get("versao") or "")
        if status_l != _HTTP_OK or not versao:
            raise OlariaGravacaoErro(f"ler {chave} sem versão (status {status_l}): {lido.get('erro') or ''}")
        status_t, trocado = self._post("/trocar", {"yaml": texto, "versao": versao, "classe": classe, "chave": chave}, pedido)
        if status_t != _HTTP_OK:
            raise OlariaGravacaoErro(f"trocar {chave} recusado (status {status_t}): {trocado.get('erro') or trocado.get('erros')}")
        return chave

    def gravar_fichas(self, fichas: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
        if fichas and not self._chave:
            raise OlariaGravacaoErro("falta OLARIA_CHAVE no ambiente e no cofre da instância")
        return tuple(self._gravar_uma(f) for f in fichas)


def gravar_fichas_veredito(
    fichas: Sequence[Mapping[str, Any]], *, gravador: GravadorFichasOntologia | None = None
) -> tuple[str, ...]:
    if not fichas:
        return ()
    return (gravador or GravadorOlaria()).gravar_fichas(fichas)


def integrar_com_portao(
    repositorio: str,
    *,
    arvore: str | Path | None = None,
    mudanca: str | None = None,
    base: str | None = None,
    integrador: Callable[[], int] | None = None,
    gravador: GravadorFichasOntologia | None = None,
    pasta_vereditos: str | Path | None = None,
) -> DecisaoPortao:
    """Avalia o par; só com verde chama o integrador e, integrado, grava as fichas que a esteira ensaiou."""
    decisao = avaliar_portao(repositorio, arvore=arvore, mudanca=mudanca, base=base, pasta_vereditos=pasta_vereditos)
    if not decisao.aprovado:
        return decisao
    if integrador is not None:
        rc = integrador()
        if rc != 0:
            return DecisaoPortao(False, "verde", rc, f"portão da main: verde, mas a integração falhou (saída {rc})",
                                 decisao.arvore_mudanca, decisao.arvore_main, decisao.registro)
    fichas = list((decisao.registro or {}).get("fichas_ensaiadas") or [])
    gravadas = gravar_fichas_veredito(fichas, gravador=gravador)
    return DecisaoPortao(True, "verde", 0, decisao.mensagem, decisao.arvore_mudanca, decisao.arvore_main,
                         decisao.registro, gravadas)


# -- o escape do dono ---------------------------------------------------------------------------------------------------

GUARDA_ESCAPE_ANOS = 20
ARQUIVO_ESCAPE = "escapes-do-dono.jsonl"


class EscapeSemMotivo(ValueError):
    """O escape foi pedido sem motivo: nada se integra."""


class EscapeGravacaoErro(RuntimeError):
    """O evento do escape não ficou gravado: sem ele o escape não integra."""


def caminho_registro_escape(registro: str | Path | None = None) -> Path:
    """O registro só de acréscimo do escape: o argumento, `PF_ESCAPE_REGISTRO` ou `<instância>/var/esteira/`."""
    if registro is not None:
        return Path(registro)
    if os.environ.get("PF_ESCAPE_REGISTRO"):
        return Path(os.environ["PF_ESCAPE_REGISTRO"])
    instancia = Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    return instancia / "var" / "esteira" / ARQUIVO_ESCAPE


def exigir_motivo(motivo: str | None) -> str:
    limpo = (motivo or "").strip()
    if not limpo:
        raise EscapeSemMotivo('escape do dono: falta o motivo (--escape "<motivo>"); sem motivo nada se integra')
    return limpo


def gravar_evento_escape(evento: Mapping[str, Any], registro: str | Path | None = None) -> Path:
    """Acrescenta uma linha ao registro, sem corte nem reescrita; falha de escrita levanta, nunca passa calada."""
    arq = caminho_registro_escape(registro)
    linha = json.dumps(dict(evento), ensure_ascii=False, sort_keys=True) + "\n"
    try:
        arq.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(arq, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, linha.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise EscapeGravacaoErro(f"escape do dono: o evento não gravou em {arq}: {exc}") from exc
    return arq


def escapar_do_portao(
    repositorio: str,
    *,
    motivo: str | None,
    pedido: str | None = None,
    arvore: str | Path | None = None,
    mudanca: str | None = None,
    base: str | None = None,
    pasta_vereditos: str | Path | None = None,
    registro: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Valida o motivo e grava o evento do escape; quem chama integra depois, e só com o evento gravado.

    A categoria do veredito entra no evento como estava: verde, falha, falta-de-rodada, avanco-da-main, ou
    `indeterminada` quando o coletor não respondeu (o escape existe justamente para esse dia).
    """
    motivo = exigir_motivo(motivo)
    env = os.environ if env is None else env
    raiz = Path(arvore).resolve() if arvore is not None else None
    arvore_mudanca = _arvore_de(raiz, mudanca or "HEAD")
    arvore_main = _arvore_de(raiz, base or "origin/main")
    try:
        categoria: str = decidir(_listar_vereditos(repositorio, pasta_vereditos), repositorio, arvore_mudanca, arvore_main).categoria
    except Exception:  # noqa: BLE001 - o escape não depende do coletor que ele contorna
        categoria = "indeterminada"
    evento = {
        "evento": "escape-do-dono",
        "guarda_anos": GUARDA_ESCAPE_ANOS,
        "evento_id": _novo_pedido(),
        "ocorrido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sujeito": env.get("PF_SUJEITO") or None,
        "cadeira": env.get("PF_CADEIRA") or None,
        "sessao": env.get("PF_SESSAO") or None,
        "repositorio": repositorio,
        "pedido": pedido,
        "arvore_mudanca": arvore_mudanca,
        "arvore_main": arvore_main,
        "categoria_da_recusa": categoria,
        "motivo": motivo,
    }
    evento["registro"] = str(gravar_evento_escape(evento, registro))
    return evento


# -- a linha de comando -------------------------------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite portao")
    p.add_argument("repositorio", help="repositório cujo histórico de vereditos se lê")
    p.add_argument("--arvore", default=None, help="clone do repositório, para resolver as revisões em árvores")
    p.add_argument("--mudanca", default=None, help="revisão ou hash da árvore da mudança (padrão HEAD)")
    p.add_argument("--base", default=None, help="revisão ou hash da árvore da ponta atual da main (padrão origin/main)")
    p.add_argument("--gravar-fichas", action="store_true", help="com verde, grava na Olaria as fichas ensaiadas")
    p.add_argument("--escape", default=None, metavar="MOTIVO",
                   help="escape do dono: não cobra o veredito, exige o motivo e grava o evento antes de o chamador integrar")
    p.add_argument("--pedido", default=None, help="número do pedido de integração, que o evento do escape carrega")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite a decisão em JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    kw = {"arvore": args.arvore if args.arvore is not None else Path.cwd(), "mudanca": args.mudanca, "base": args.base}
    if args.escape is not None:
        if args.gravar_fichas:
            sys.stderr.write("escape do dono: não grava fichas da esteira (--gravar-fichas); sem verde não há ficha ensaiada\n")
            return 2
        try:
            evento = escapar_do_portao(args.repositorio, motivo=args.escape, pedido=args.pedido, **kw)
        except EscapeSemMotivo as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        except EscapeGravacaoErro as exc:
            sys.stderr.write(f"{exc}\n")
            return 3
        if args.como_json:
            sys.stdout.write(json.dumps(evento, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(
                f"escape do dono: evento {evento['evento_id']} gravado em {evento['registro']} "
                f"(recusa que o escape contorna: {evento['categoria_da_recusa']}; guarda {GUARDA_ESCAPE_ANOS} anos)\n"
            )
        return 0
    try:
        if args.gravar_fichas:
            decisao = integrar_com_portao(args.repositorio, **kw)
        else:
            decisao = avaliar_portao(args.repositorio, **kw)
    except OlariaGravacaoErro as exc:
        sys.stderr.write(f"portão da main: verde, mas a gravação das fichas falhou — {exc}\n")
        return 3
    if args.como_json:
        sys.stdout.write(json.dumps(decisao.como_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        linha = f"{decisao.mensagem} (mudanca={decisao.arvore_mudanca[:12]} base={decisao.arvore_main[:12]})\n"
        (sys.stdout if decisao.aprovado else sys.stderr).write(linha)
        if not decisao.aprovado:
            sys.stdout.write(linha)
        for chave in decisao.fichas_gravadas:
            sys.stdout.write(f"ficha gravada: {chave}\n")
    return decisao.codigo_saida


__all__ = [
    "DecisaoPortao",
    "EscapeGravacaoErro",
    "EscapeSemMotivo",
    "GravadorFichasOntologia",
    "GravadorOlaria",
    "OlariaGravacaoErro",
    "avaliar_portao",
    "caminho_registro_escape",
    "decidir",
    "escapar_do_portao",
    "exigir_motivo",
    "gravar_evento_escape",
    "gravar_fichas_veredito",
    "integrar_com_portao",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
