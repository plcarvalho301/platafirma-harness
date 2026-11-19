# componente: componente:verbo-repo
"""Portão de integração na main: o veredito do par de árvores decide, e a integração grava as fichas ensaiadas."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

LIB_RAIZ = Path(__file__).resolve().parents[1] / "lib"
if str(LIB_RAIZ) not in sys.path:
    sys.path.insert(0, str(LIB_RAIZ))

from suite import portao as portao_modulo  # noqa: E402
from suite.portao import (  # noqa: E402
    EscapeGravacaoErro,
    EscapeSemMotivo,
    GravadorOlaria,
    OlariaGravacaoErro,
    avaliar_portao,
    escapar_do_portao,
    integrar_com_portao,
)

REPO = "repo-prova"
MUDANCA = "a" * 40
MAIN = "b" * 40
MAIN_NOVA = "c" * 40
FICHA = {
    "classe": "teste-de-comportamento",
    "chave": "teste-de-comportamento:verbo-repo",
    "ligacoes": {"verifica": "componente:verbo-repo"},
}


def _gravar_historico(pasta: Path, *registros: dict[str, Any]) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"{REPO}.jsonl"
    arq.write_text("".join(json.dumps(r) + "\n" for r in registros), encoding="utf-8")
    return pasta


def _reg(estado: str, main: str = MAIN, **extra: Any) -> dict[str, Any]:
    return {"repositorio": REPO, "arvore_mudanca": MUDANCA, "arvore_main": main, "estado": estado, **extra}


class _GravadorFalso:
    def __init__(self) -> None:
        self.recebidas: list[dict[str, Any]] = []

    def gravar_fichas(self, fichas):
        self.recebidas.extend(dict(f) for f in fichas)
        return tuple(str(f["chave"]) for f in fichas)


# -- os quatro casos ----------------------------------------------------------------------------------------------------


def test_par_verde_aprova(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("verde"))
    d = avaliar_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta)
    assert (d.aprovado, d.categoria, d.codigo_saida) == (True, "verde", 0)


def test_par_vermelho_recusa_por_falha(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("vermelho", casos_reprovados=["t::caso"]))
    d = avaliar_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta)
    assert (d.aprovado, d.categoria, d.codigo_saida) == (False, "falha", 1)
    assert "a esteira reprovou" in d.mensagem and "t::caso" in d.mensagem


def test_par_nao_medido_recusa_como_vermelho(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("nao-medido", motivo="Olaria fora"))
    d = avaliar_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta)
    assert (d.categoria, d.codigo_saida) == ("falha", 1)


def test_rodada_mais_recente_do_par_vence(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("verde"), _reg("vermelho"))
    d = avaliar_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta)
    assert d.categoria == "falha"


def test_main_avancada_depois_da_rodada_recusa_com_a_cura(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("verde", main=MAIN))
    d = avaliar_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN_NOVA, pasta_vereditos=pasta)
    assert (d.aprovado, d.categoria, d.codigo_saida) == (False, "avanco-da-main", 1)
    assert "avanço da main" in d.mensagem and f"repo sincronizar {REPO}" in d.mensagem


def test_sem_rodada_para_a_mudanca_recusa_por_falta_de_rodada(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", {**_reg("verde"), "arvore_mudanca": "d" * 40})
    d = avaliar_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta)
    assert (d.aprovado, d.categoria, d.codigo_saida) == (False, "falta-de-rodada", 1)
    assert "falta de rodada" in d.mensagem


def test_revisoes_git_viram_arvores(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    clone.mkdir()
    git = ["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    (clone / "a.txt").write_text("1\n", encoding="utf-8")
    subprocess.run([*git, "add", "a.txt"], check=True)
    subprocess.run([*git, "commit", "-qm", "c1"], check=True)
    arvore = subprocess.run([*git, "rev-parse", "HEAD^{tree}"], check=True, capture_output=True, text=True).stdout.strip()
    pasta = _gravar_historico(tmp_path / "v", {**_reg("verde"), "arvore_mudanca": arvore, "arvore_main": arvore})
    d = avaliar_portao(REPO, arvore=clone, mudanca="HEAD", base="HEAD", pasta_vereditos=pasta)
    assert d.categoria == "verde" and d.arvore_mudanca == arvore


# -- integrar só com verde, e gravar as fichas --------------------------------------------------------------------------


def test_integra_com_verde_e_grava_as_fichas_ensaiadas(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("verde", fichas_ensaiadas=[FICHA]))
    chamadas: list[str] = []
    gravador = _GravadorFalso()
    d = integrar_com_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta,
                            integrador=lambda: chamadas.append("merge") or 0, gravador=gravador)
    assert chamadas == ["merge"]
    assert gravador.recebidas == [FICHA]
    assert d.fichas_gravadas == ("teste-de-comportamento:verbo-repo",)


@pytest.mark.parametrize("historico", [(_reg("vermelho", fichas_ensaiadas=[FICHA]),), ()])
def test_sem_verde_nao_integra_nem_grava(tmp_path: Path, historico: tuple[dict[str, Any], ...]) -> None:
    pasta = _gravar_historico(tmp_path / "v", *historico)
    chamadas: list[str] = []
    gravador = _GravadorFalso()
    d = integrar_com_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta,
                            integrador=lambda: chamadas.append("merge") or 0, gravador=gravador)
    assert d.codigo_saida == 1 and chamadas == [] and gravador.recebidas == []


def test_integracao_que_falha_nao_grava(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("verde", fichas_ensaiadas=[FICHA]))
    gravador = _GravadorFalso()
    d = integrar_com_portao(REPO, arvore=tmp_path, mudanca=MUDANCA, base=MAIN, pasta_vereditos=pasta,
                            integrador=lambda: 3, gravador=gravador)
    assert d.codigo_saida == 3 and gravador.recebidas == []


# -- a Olaria de prova --------------------------------------------------------------------------------------------------


@pytest.fixture
def olaria() -> Iterator[dict[str, Any]]:
    estado: dict[str, Any] = {"existentes": set(), "pedidos": []}

    class Tratador(BaseHTTPRequestHandler):
        def log_message(self, *_a: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            estado["pedidos"].append((self.path, dict(self.headers), corpo))
            if self.headers.get("X-Olaria-Chave") != "chave-de-prova":
                return self._enviar(401, {"erro": "chave"})
            if self.path == "/criar":
                chave = FICHA["chave"]
                if chave in estado["existentes"]:
                    return self._enviar(422, {"estado": "recusada", "erros": [{"codigo": "ficha-chave-ja-existe"}]})
                estado["existentes"].add(chave)
                return self._enviar(200, {"estado": "fez", "fornada": self.headers.get("X-Olaria-Pedido")})
            if self.path == "/ler":
                return self._enviar(200, {"estado": "fez", "versao": "fornada-lida"})
            if self.path == "/trocar":
                ok = corpo.get("versao") == "fornada-lida"
                return self._enviar(200 if ok else 409, {"estado": "fez" if ok else "versao-diferente"})
            return self._enviar(404, {"erro": self.path})

        def _enviar(self, status: int, corpo: dict[str, Any]) -> None:
            dados = json.dumps(corpo).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Tratador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    estado["url"] = f"http://127.0.0.1:{srv.server_address[1]}"
    yield estado
    srv.shutdown()


def test_gravador_cria_e_na_segunda_vez_troca_com_a_versao_lida(olaria: dict[str, Any]) -> None:
    g = GravadorOlaria(url=olaria["url"], chave="chave-de-prova", sujeito="engenharia")
    assert g.gravar_fichas([FICHA]) == (FICHA["chave"],)
    assert g.gravar_fichas([FICHA]) == (FICHA["chave"],)
    rotas = [p for p, _, _ in olaria["pedidos"]]
    assert rotas == ["/criar", "/criar", "/ler", "/trocar"]
    _, cab, corpo = olaria["pedidos"][-1]
    assert corpo["versao"] == "fornada-lida" and cab["X-Olaria-Sujeito"] == "engenharia"
    assert cab["X-Olaria-Pedido"][14] == "7"


def test_gravador_recusado_sobe_erro_sem_mostrar_a_chave(olaria: dict[str, Any]) -> None:
    g = GravadorOlaria(url=olaria["url"], chave="chave-errada-secreta", sujeito="engenharia")
    with pytest.raises(OlariaGravacaoErro) as exc:
        g.gravar_fichas([FICHA])
    assert "chave-errada-secreta" not in str(exc.value)


# -- a linha de comando, pelo coletor servido ---------------------------------------------------------------------------


def _cli(tmp_path: Path, pasta: Path, mudanca: str, base: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": str(LIB_RAIZ),
        "PF_ESTEIRA_VEREDITOS_DIR": str(pasta),
        "PF_ESTEIRA_COLETOR_SERVIDO": str(LIB_RAIZ / "suite" / "coletor.py"),
    })
    return subprocess.run(
        [sys.executable, "-m", "suite", "portao", REPO, "--arvore", str(tmp_path), "--mudanca", mudanca, "--base", base],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=120, check=False,
    )


@pytest.mark.parametrize(
    ("base", "historico", "codigo", "trecho"),
    [
        (MAIN, [_reg("verde")], 0, "verde"),
        (MAIN, [_reg("vermelho")], 1, "a esteira reprovou"),
        (MAIN_NOVA, [_reg("verde")], 1, "avanço da main"),
        (MAIN, [], 1, "falta de rodada"),
    ],
)
def test_cli_sai_com_o_codigo_e_a_causa(tmp_path: Path, base: str, historico: list[dict[str, Any]],
                                         codigo: int, trecho: str) -> None:
    pasta = _gravar_historico(tmp_path / "v", *historico)
    r = _cli(tmp_path, pasta, MUDANCA, base)
    assert r.returncode == codigo, r.stderr
    assert trecho in r.stdout


# -- o escape do dono (#4301) -------------------------------------------------------------------------------------------


def _escapar(tmp_path: Path, motivo: str | None, historico: tuple[dict[str, Any], ...] = (), **extra: Any) -> dict[str, Any]:
    pasta = _gravar_historico(tmp_path / "v", *historico)
    return escapar_do_portao(REPO, motivo=motivo, pedido="77", arvore=tmp_path, mudanca=MUDANCA, base=MAIN,
                             pasta_vereditos=pasta, registro=tmp_path / "escapes.jsonl", **extra)


def _linhas(tmp_path: Path) -> list[dict[str, Any]]:
    arq = tmp_path / "escapes.jsonl"
    return [json.loads(linha) for linha in arq.read_text(encoding="utf-8").splitlines()] if arq.exists() else []


@pytest.mark.parametrize("motivo", [None, "", "   ", "\n\t "])
def test_escape_sem_motivo_para_antes_de_gravar(tmp_path: Path, motivo: str | None) -> None:
    with pytest.raises(EscapeSemMotivo):
        _escapar(tmp_path, motivo, (_reg("vermelho"),))
    assert _linhas(tmp_path) == []


def test_escape_com_motivo_sobre_veredito_vermelho_grava_o_evento_de_20_anos(tmp_path: Path) -> None:
    evento = _escapar(tmp_path, "  esteira fora do ar  ", (_reg("vermelho", casos_reprovados=["t::caso"]),),
                      env={"PF_SUJEITO": "dono", "PF_CADEIRA": "engenharia", "PF_SESSAO": "sessao-1"})
    [gravado] = _linhas(tmp_path)
    assert gravado["evento"] == "escape-do-dono" and gravado["guarda_anos"] == 20
    assert gravado["motivo"] == "esteira fora do ar"
    assert (gravado["categoria_da_recusa"], gravado["pedido"], gravado["repositorio"]) == ("falha", "77", REPO)
    assert (gravado["arvore_mudanca"], gravado["arvore_main"]) == (MUDANCA, MAIN)
    assert (gravado["sujeito"], gravado["cadeira"], gravado["sessao"]) == ("dono", "engenharia", "sessao-1")
    assert gravado["evento_id"] == evento["evento_id"] and gravado["ocorrido_em"]


def test_escape_so_acrescenta_nunca_reescreve(tmp_path: Path) -> None:
    _escapar(tmp_path, "primeiro", (_reg("vermelho"),))
    _escapar(tmp_path, "segundo", (_reg("vermelho"),))
    assert [e["motivo"] for e in _linhas(tmp_path)] == ["primeiro", "segundo"]


@pytest.mark.parametrize("quem", [{}, {"PF_CADEIRA": "engenharia"}, {"PF_SUJEITO": "dono"}, {"PF_CADEIRA": "ti", "PF_SUJEITO": "dono"}])
def test_escape_vale_igual_para_o_dono_e_para_qualquer_cadeira(tmp_path: Path, quem: dict[str, str]) -> None:
    evento = _escapar(tmp_path, "urgente", (_reg("vermelho"),), env=quem)
    assert evento["categoria_da_recusa"] == "falha" and len(_linhas(tmp_path)) == 1


@pytest.mark.parametrize(
    ("historico", "categoria"),
    [((_reg("verde"),), "verde"), ((), "falta-de-rodada"), ((_reg("verde", main=MAIN_NOVA),), "avanco-da-main")],
)
def test_escape_guarda_a_categoria_do_veredito_que_contorna(tmp_path: Path, historico: tuple[dict[str, Any], ...],
                                                            categoria: str) -> None:
    assert _escapar(tmp_path, "motivo", historico)["categoria_da_recusa"] == categoria


def test_escape_funciona_com_o_coletor_fora_do_ar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _quebrado(*_a: Any, **_k: Any) -> list[dict[str, Any]]:
        raise RuntimeError("coletor servido ausente")

    monkeypatch.setattr(portao_modulo, "_listar_vereditos", _quebrado)
    assert _escapar(tmp_path, "coletor caiu")["categoria_da_recusa"] == "indeterminada"
    assert len(_linhas(tmp_path)) == 1


def test_escape_sem_evento_gravado_nao_segue(tmp_path: Path) -> None:
    (tmp_path / "escapes.jsonl").mkdir()
    with pytest.raises(EscapeGravacaoErro):
        _escapar(tmp_path, "motivo", (_reg("vermelho"),))


def _cli_escape(tmp_path: Path, pasta: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": str(LIB_RAIZ),
        "PF_ESTEIRA_VEREDITOS_DIR": str(pasta),
        "PF_ESTEIRA_COLETOR_SERVIDO": str(LIB_RAIZ / "suite" / "coletor.py"),
        "PF_ESCAPE_REGISTRO": str(tmp_path / "escapes.jsonl"),
    })
    return subprocess.run(
        [sys.executable, "-m", "suite", "portao", REPO, "--arvore", str(tmp_path), "--mudanca", MUDANCA, "--base", MAIN, *args],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=120, check=False,
    )


def test_cli_escape_sem_motivo_sai_1_e_nao_grava(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("vermelho"))
    r = _cli_escape(tmp_path, pasta, "--escape", "")
    assert r.returncode == 1 and "falta o motivo" in r.stderr
    assert _linhas(tmp_path) == []


def test_cli_escape_com_motivo_sobre_vermelho_sai_0_e_grava(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("vermelho"))
    r = _cli_escape(tmp_path, pasta, "--escape", "prova do escape", "--pedido", "9")
    assert r.returncode == 0, r.stderr
    [gravado] = _linhas(tmp_path)
    assert (gravado["motivo"], gravado["pedido"], gravado["categoria_da_recusa"]) == ("prova do escape", "9", "falha")
    assert "guarda 20 anos" in r.stdout


def test_cli_escape_nao_grava_fichas(tmp_path: Path) -> None:
    pasta = _gravar_historico(tmp_path / "v", _reg("vermelho", fichas_ensaiadas=[FICHA]))
    r = _cli_escape(tmp_path, pasta, "--escape", "motivo", "--gravar-fichas")
    assert r.returncode == 2 and _linhas(tmp_path) == []
