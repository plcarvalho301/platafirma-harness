# componente: componente:leitura
"""Suíte de contrato nas sete moradas, paridade porta/terminal e mutação das guardas (story #4442, t11)."""
from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import socket
import sys
import tempfile
import threading
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Self

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from leitura import formatos as mod_formatos
from leitura import morada as mod_morada
from leitura import nucleo as mod_nucleo
from leitura import resolvedor as mod_resolvedor
from leitura.cliente import ClienteLeitor
from leitura.daemon import DaemonLeitor
from leitura.moradas import ErroMorada, RegistroMoradas
from leitura.moradas import git as mod_git
from leitura.moradas.balde import AdaptadorBalde, criar_abridor_bytes
from leitura.moradas.banco import AdaptadorBanco
from leitura.moradas.cofre import AdaptadorCofre
from leitura.moradas.fila import AdaptadorFila
from leitura.moradas.git import AdaptadorGit
from leitura.moradas.rastreador import AdaptadorRastreador
from leitura.moradas.wiki import AdaptadorWiki
from leitura.resolvedor import ClasseAlcance, ErroResolucao, VistaAlcance, resolver_alvo
from leitura.tipos import AlvoResolvido, ContextoChamada, ObjetoBruto, SeletorParte

CAMPOS_RECUSA = frozenset({"codigo", "onde", "recebido", "regra", "cura", "proximo"})
CAMPOS_TELEMETRIA = (
    "dur_ms",
    "verbo",
    "forma",
    "classe",
    "morada",
    "exit_code",
    "sujeito",
    "conta_chamadora",
    "release",
)


def _carregar_bin_busca() -> Any:
    caminho = RAIZ / "bin" / "busca"
    loader = importlib.machinery.SourceFileLoader("bin_busca_contrato_t11", str(caminho))
    spec = importlib.util.spec_from_loader("bin_busca_contrato_t11", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_BIN_BUSCA = _carregar_bin_busca()


class _CursorBancoFalso:
    def __init__(self, estado: dict[str, Any]) -> None:
        self._estado = estado
        self._rows: list[tuple[Any, ...]] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_a: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        sql_up = sql.strip().upper()
        if sql_up.startswith(("BEGIN", "SET LOCAL")):
            self._rows = []
        elif "FROM CASA.FICHA F" in sql_up and "WHERE F.CHAVE_HUMANA = %S" in sql_up:
            chave = params[0]
            reg = self._estado["fichas"].get(chave) or self._estado["fichas"].get(f"shape:{chave}")
            self._rows = [reg] if reg else []
        elif "MD5(" in sql_up:
            chaves = sorted(self._estado["fichas"])
            digest = hashlib.md5("\n".join(chaves).encode("utf-8")).hexdigest()
            self._rows = [(self._estado["fornada"], digest, len(chaves))]
        elif "SELECT 0 AS ORDEM" in sql_up:
            self._rows = self._listar_linhas(params)
        else:
            self._rows = []

    def _listar_linhas(self, params: Any) -> list[tuple[Any, ...]]:
        chaves = sorted(self._estado["fichas"])
        ult_chave = params[1] if params and len(params) >= 5 else None
        limite = int(params[4]) if params and len(params) >= 5 else len(chaves)
        if ult_chave is not None:
            chaves = [k for k in chaves if k > ult_chave]
        return [(0, k, k, "shape") for k in chaves[:limite]]

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class _ConexaoBancoFalsa:
    def __init__(self, estado: dict[str, Any]) -> None:
        self._estado = estado

    def cursor(self) -> _CursorBancoFalso:
        return _CursorBancoFalso(self._estado)

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class _ValkeyContrato:
    """Stub mínimo de Valkey que registra apenas comandos de leitura fria."""

    def __init__(self) -> None:
        self.comandos: list[str] = []
        self._msgs = [
            ("1700-0", {"assunto": "aviso-1", "de": "ti"}),
            ("1701-0", {"assunto": "aviso-2", "de": "engenharia"}),
        ]
        self._kv = {
            "lousa:s1": json.dumps({"itens": ["tarefa-1"]}),
            "execucao:e1": json.dumps({"sujeito": "engenharia", "estado": "ok", "versao": "v1"}),
        }

    def xrange(
        self, name: str, min: str = "-", max: str = "+", count: int | None = None
    ) -> list[tuple[str, dict[str, str]]]:
        self.comandos.append("XRANGE")
        if name != "fila:mensagens":
            return []
        filtrados = [
            par for par in self._msgs if (min == "-" or par[0] >= min) and (max == "+" or par[0] <= max)
        ]
        return filtrados[:count] if count is not None else filtrados

    def get(self, name: str) -> str | None:
        self.comandos.append("GET")
        return self._kv.get(name)

    def scan_iter(self, match: str | None = None) -> list[str]:
        self.comandos.append("SCAN")
        pref = (match or "").rstrip("*")
        return [k for k in self._kv if k.startswith(pref)]


def _http_wiki(_url: str, params: Mapping[str, str], _timeout: float) -> dict[str, Any]:
    if params.get("list") == "allpages":
        return {"query": {"allpages": [{"title": "alfa"}, {"title": "beta"}]}}
    if params.get("titles") == "falta":
        return {"query": {"pages": {"-1": {"missing": ""}}}}
    return {
        "query": {
            "pages": {
                "1": {
                    "revisions": [
                        {"revid": 42, "slots": {"main": {"content": "wiki linha 1\nwiki linha 2\n"}}}
                    ]
                }
            }
        }
    }


def _http_rastreador(url: str, _params: Mapping[str, str], _timeout: float) -> Any:
    if url.endswith("/itens/4442"):
        return {"id": "4442", "titulo": "Leitor unico", "estado": "em-execucao", "revisao": "r9"}
    if url.endswith("/itens"):
        return {"itens": [{"id": "4442", "titulo": "Leitor unico", "estado": "em-execucao"}]}
    raise KeyError(url)


def _criar_balde() -> tuple[AdaptadorBalde, str, str]:
    buf_zip = io.BytesIO()
    with zipfile.ZipFile(buf_zip, "w") as zf:
        zf.writestr("notas.txt", "conteudo interno do zip\nlinha 2\n")
    zip_bytes = buf_zip.getvalue()
    sha_zip = hashlib.sha256(zip_bytes).hexdigest()
    txt_balde = b"balde linha 1\nbalde linha 2\n"
    sha_txt = hashlib.sha256(txt_balde).hexdigest()

    def _extrator(_fd: int, pedido: Mapping[str, Any], _prazo: int) -> dict[str, Any]:
        texto = "conteudo interno do zip\nlinha 2\n" if pedido.get("membro") == "notas.txt" else "notas.txt\n"
        return {"ok": True, "tipo": "application/zip", "conteudo": texto, "avisos": []}

    adaptador = AdaptadorBalde(
        abridor=criar_abridor_bytes({sha_txt: (txt_balde, "doc.txt"), sha_zip: (zip_bytes, "pacote.zip")}),
        listador=lambda _p: [{"sha256": sha_txt, "nome": "doc.txt"}],
        extrator=_extrator,
    )
    return adaptador, sha_txt, sha_zip


def _vista_sete_moradas() -> VistaAlcance:
    return VistaAlcance(
        verbos_aceitam_ler=frozenset({"busca", "ontologia"}),
        alcance_verbo={"busca": frozenset({"*"}), "ontologia": frozenset({"shape"})},
        classes={
            "ato": ClasseAlcance("ato", "git", "busca", molde="ato/<slug>.md", universo_fechado=True),
            "shape": ClasseAlcance("shape", "banco", "ontologia", universo_fechado=True),
            "sessao": ClasseAlcance("sessao", "banco", "busca", universo_fechado=True),
            "pagina": ClasseAlcance("pagina", "wiki", "acervo", universo_fechado=False),
            "objeto": ClasseAlcance("objeto", "balde", "acervo", universo_fechado=False),
            "mensagem": ClasseAlcance("mensagem", "fila", "fila", universo_fechado=True),
            "card": ClasseAlcance("card", "rastreador", "tarefas", universo_fechado=True),
            "segredo": ClasseAlcance("segredo", "cofre", "seg", universo_fechado=True),
        },
    )


def _subir_daemon_em_socket(daemon: DaemonLeitor) -> tuple[Path, socket.socket, threading.Thread]:
    sock_dir = Path(tempfile.mkdtemp(prefix="pf-ler-c-"))
    sock_path = sock_dir / "leitor.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(64)
    th = threading.Thread(target=daemon.servir_socket, args=(srv,), daemon=True)
    th.start()
    return sock_path, srv, th


def _montar_ambiente_sete_moradas(tmp_path: Path) -> dict[str, Any]:
    raiz_git = tmp_path / "release"
    (raiz_git / "ato").mkdir(parents=True, exist_ok=True)
    (raiz_git / "ato" / "ler.md").write_text("linha 1\nlinha 2\nlinha 3\n", encoding="utf-8")
    (raiz_git / "ato" / "listar.md").write_text("listar 1\nlistar 2\n", encoding="utf-8")

    estado_banco: dict[str, Any] = {
        "fornada": "f-001",
        "fichas": {
            "shape:sessao": (
                "u-1",
                "shape:sessao",
                "shape",
                "f-001",
                {"chave": "shape:sessao", "classe": "shape", "dados": {"slug": ["sessao"]}},
            ),
            "shape:ato": (
                "u-2",
                "shape:ato",
                "shape",
                "f-001",
                {"chave": "shape:ato", "classe": "shape", "dados": {"slug": ["ato"]}},
            ),
        },
    }
    balde, sha_txt, sha_zip = _criar_balde()
    vk = _ValkeyContrato()
    moradas = RegistroMoradas(
        {
            "git": AdaptadorGit(raiz_git),
            "banco": AdaptadorBanco(fabrica_conexao=lambda: _ConexaoBancoFalsa(estado_banco)),
            "wiki": AdaptadorWiki(url_api="http://wiki.local/api.php", cliente_http=_http_wiki),
            "balde": balde,
            "fila": AdaptadorFila(cliente=vk),
            "rastreador": AdaptadorRastreador(url_base="http://rast.local", cliente_http=_http_rastreador),
            "cofre": AdaptadorCofre(),
        }
    )
    telemetria: list[dict[str, Any]] = []
    daemon = DaemonLeitor(
        moradas=moradas,
        vista=_vista_sete_moradas(),
        uids_autorizados=frozenset({os.getuid()}),
        ler_release=lambda: "rel-contrato-1",
        telemetria=telemetria.append,
        segredo_cursor=b"segredo-contrato-t11",
    )
    sock_path, srv, th = _subir_daemon_em_socket(daemon)
    return {
        "daemon": daemon,
        "srv": srv,
        "thread": th,
        "cliente": ClienteLeitor(sock_path),
        "telemetria": telemetria,
        "valkey": vk,
        "estado_banco": estado_banco,
        "sha_txt": sha_txt,
        "sha_zip": sha_zip,
    }


def _fechar_ambiente(amb: dict[str, Any]) -> None:
    amb["daemon"].parar()
    amb["srv"].close()
    amb["thread"].join(timeout=3.0)


def _ctx(origem: str = "cli", sujeito: str = "engenharia", verbo: str = "busca") -> ContextoChamada:
    return ContextoChamada(
        sujeito_jwt=None,
        sujeito=sujeito,
        sessao_id="sessao-contrato",
        ordem_id="ordem-contrato",
        verbo=verbo,
        origem_autenticada=origem,
        origem_declarada=origem,
        prazo_ms=5_000,
    )


def _reconstruir_por_fatias(bruto: ObjetoBruto, orcamento: int) -> str:
    pedacos: list[str] = []
    offset: int | None = 0
    for _ in range(200):
        res = mod_nucleo.processar_objeto(bruto, SeletorParte(offset=offset, max_bytes=orcamento))
        assert res.conteudo is not None
        pedacos.append(res.conteudo)
        if not res.parcial:
            break
        assert res.proximo_args is not None
        prox_off = int(res.proximo_args["offset"])
        assert prox_off > (offset or 0)
        offset = prox_off
    return "".join(pedacos)


# ------------------------------------------------------------------ 1. Contrato nas 7 moradas
@pytest.mark.parametrize(
    ("morada", "classe", "chave_modelo"),
    [
        ("git", "ato", "ato:ler"),
        ("banco", "shape", "shape:sessao"),
        ("wiki", "pagina", "pagina:alfa"),
        ("balde", "objeto", "objeto:{sha_txt}"),
        ("fila", "mensagem", "mensagem:1700-0"),
        ("rastreador", "card", "card:4442"),
    ],
)
def test_contrato_moradas_legiveis_ler_listar_e_telemetria(
    tmp_path: Path, morada: str, classe: str, chave_modelo: str
) -> None:
    amb = _montar_ambiente_sete_moradas(tmp_path)
    try:
        cliente: ClienteLeitor = amb["cliente"]
        chave = chave_modelo.format(sha_txt=amb["sha_txt"])

        resp = cliente.ler(_ctx(), [chave])
        assert resp["exit_code"] == 0, resp
        res = resp["resultado"]
        assert res["morada"] == morada
        assert res["cabecalho"].startswith(f"{chave} · versão {res['versao']} · ")
        assert res["conteudo"]

        resp_fat = cliente.ler(_ctx(), [chave], seletor=SeletorParte(linhas=(1, 1)))
        assert resp_fat["exit_code"] == 0
        assert resp_fat["resultado"]["cabecalho"].startswith(f"{chave} · versão ")

        resp_lst = cliente.listar(_ctx(), classe)
        assert resp_lst["exit_code"] == 0
        assert isinstance(resp_lst["resultado"]["itens"], list)

        resp_vazio = cliente.listar(_ctx(), classe, termo="__inexistente_xyz__")
        assert resp_vazio["exit_code"] == 0
        assert resp_vazio["resultado"]["itens"] == []

        ev = amb["telemetria"][-1]
        assert all(campo in ev for campo in CAMPOS_TELEMETRIA)
        assert ev["release"] == "rel-contrato-1"
    finally:
        _fechar_ambiente(amb)


def test_contrato_cofre_balde_membro_e_fila_sem_consumo(tmp_path: Path) -> None:
    amb = _montar_ambiente_sete_moradas(tmp_path)
    try:
        cliente: ClienteLeitor = amb["cliente"]

        resp_cofre = cliente.ler(_ctx(), ["segredo:api-key"])
        assert resp_cofre["exit_code"] == 4
        assert CAMPOS_RECUSA <= set(resp_cofre["recusa"])
        assert resp_cofre["recusa"]["codigo"] == "segredo-fora-do-leitor"

        resp_mem = cliente.ler(
            _ctx(), [f"objeto:{amb['sha_zip']}!notas.txt"], seletor=SeletorParte(membro="notas.txt")
        )
        assert resp_mem["exit_code"] == 0
        assert "conteudo interno do zip" in resp_mem["resultado"]["conteudo"]

        resp_fila = cliente.ler(_ctx(), ["mensagem:1700-0"])
        assert resp_fila["exit_code"] == 0
        assert amb["valkey"].comandos
        assert all(c in {"XRANGE", "GET", "SCAN"} for c in amb["valkey"].comandos)
    finally:
        _fechar_ambiente(amb)


# ------------------------------------------------------------------ 2. Ficha da classe, cursor e recusas
def test_contrato_ficha_classe_cursor_e_recusas_seis_campos(tmp_path: Path) -> None:
    amb = _montar_ambiente_sete_moradas(tmp_path)
    try:
        cliente: ClienteLeitor = amb["cliente"]

        resp_cls = cliente.ler(_ctx(), ["sessao:"])
        assert resp_cls["exit_code"] == 0
        assert "objeto lido: a ficha da classe sessao" in resp_cls["resultado"]["cabecalho"]

        p1 = cliente.listar(_ctx(), "shape", limite=1)
        assert p1["exit_code"] == 0
        cursor_p1 = p1["resultado"]["cursor"]
        assert cursor_p1

        amb["estado_banco"]["fornada"] = "f-002"
        amb["estado_banco"]["fichas"]["shape:zeta"] = (
            "u-3",
            "shape:zeta",
            "shape",
            "f-002",
            {"chave": "shape:zeta", "classe": "shape", "dados": {}},
        )
        p2 = cliente.listar(_ctx(), "shape", limite=2, cursor=cursor_p1)
        assert p2["exit_code"] == 0
        assert p2["resultado"]["mudou"] is not None
        assert "versao_alterada_entre_paginas" in p2["resultado"]["avisos"]

        p_adul = cliente.listar(_ctx(), "shape", cursor=cursor_p1 + "corrompido")
        assert p_adul["exit_code"] == 2
        assert CAMPOS_RECUSA <= set(p_adul["recusa"])
        assert p_adul["recusa"]["codigo"] == "continuacao-ilegivel"

        p_outro = cliente.listar(_ctx(sujeito="outro-sujeito"), "shape", cursor=cursor_p1)
        assert p_outro["exit_code"] == 2
        assert p_outro["recusa"]["codigo"] == "continuacao-divergente"

        r1 = cliente.ler(_ctx(), ["ato:inexistente"])
        assert r1["exit_code"] == 1
        assert CAMPOS_RECUSA <= set(r1["recusa"])

        r1_alc = cliente.ler(_ctx(verbo="ontologia"), ["ato:ler"])
        assert r1_alc["exit_code"] == 1
        assert r1_alc["recusa"]["codigo"] == "classe-fora-do-verbo"
    finally:
        _fechar_ambiente(amb)


# ------------------------------------------------------------------ 3. Paridade porta/terminal e reconstrução
def test_paridade_porta_e_terminal_e_reconstrucao_por_fatias(tmp_path: Path) -> None:
    amb = _montar_ambiente_sete_moradas(tmp_path)
    try:
        cliente: ClienteLeitor = amb["cliente"]
        matriz = [
            ["ler", "ato:ler", "--json"],
            ["ler", "ato:ler", "--linhas", "1-2", "--json"],
            ["listar", "ato", "--json"],
            ["ler", "/etc/passwd"],
            ["ler", "segredo:x"],
        ]
        for argv in matriz:
            out_cli, err_cli = io.StringIO(), io.StringIO()
            rc_cli = _BIN_BUSCA.main(
                argv,
                saida=out_cli,
                erro=err_cli,
                cliente_leitor=cliente,
                env={"PF_SUJEITO": "engenharia", "PF_LEITOR_UNICO": "true", "PF_ORIGEM": "cli"},
            )
            out_porta, err_porta = io.StringIO(), io.StringIO()
            rc_porta = _BIN_BUSCA.main(
                argv,
                saida=out_porta,
                erro=err_porta,
                cliente_leitor=cliente,
                env={"PF_SUJEITO": "engenharia", "PF_LEITOR_UNICO": "true", "PF_ORIGEM": "porta"},
            )
            assert rc_cli == rc_porta
            assert out_cli.getvalue() == out_porta.getvalue()
            assert err_cli.getvalue() == err_porta.getvalue()

        conteudo_original = (
            "ação rápida 🚀 日本語\r\n"
            + ("palavra-longa-sem-quebra-com-acentos-ção-é-" * 5)
            + "\r\nfim da prova ✅\n"
        )
        dados_orig = conteudo_original.encode("utf-8")
        alvo = AlvoResolvido("ato:prop", "ato:prop", "ato", "git", "ato/prop.md", True, None)
        bruto = ObjetoBruto(
            alvo=alvo, versao="v-prop", dados=dados_orig, nome_arquivo="prop.md", total_bytes=len(dados_orig)
        )
        for orcamento in (17, 32, 64, 128):
            assert _reconstruir_por_fatias(bruto, orcamento) == conteudo_original
    finally:
        _fechar_ambiente(amb)


# ------------------------------------------------------------------ 4. Mutação nas guardas (0 sobreviventes)
def _bloqueou_symlink(raiz_git: Path) -> bool:
    dir_fd = os.open(raiz_git, os.O_RDONLY)
    bloqueou = False
    try:
        fd = mod_git._abrir_segmento(dir_fd, "elo.md", mod_git._FLAGS_ABERTURA, "elo.md")
        os.close(fd)
    except ErroMorada as exc:
        bloqueou = exc.saida == 4
    finally:
        os.close(dir_fd)
    return bloqueou


def _bloqueou_fstat_dev_ino(raiz_git: Path, reg: Path, monkeypatch: pytest.MonkeyPatch) -> bool:
    st_real = os.lstat(reg)
    st_falso = os.stat_result((st_real.st_mode, st_real.st_ino + 99, st_real.st_dev, 1, 0, 0, 3, 0, 0, 0))
    dir_fd = os.open(raiz_git, os.O_RDONLY)
    fd = os.open(reg, os.O_RDONLY)
    bloqueou = False
    try:
        with monkeypatch.context() as mp_in:
            mp_in.setattr(os, "fstat", lambda _fd: st_falso)
            try:
                mod_git._validar_fd_regular(dir_fd, "normal.md", fd, "normal.md")
            except ErroMorada as exc:
                bloqueou = exc.saida == 4
    finally:
        os.close(fd)
        os.close(dir_fd)
    return bloqueou


def _bloqueou_alcance() -> bool:
    bloqueou = False
    try:
        resolver_alvo("ontologia", "ato:ler")
    except ErroResolucao as exc:
        bloqueou = exc.saida == 1
    return bloqueou


def _bloqueou_peercred(tmp_path: Path) -> bool:
    amb = _montar_ambiente_sete_moradas(tmp_path)
    try:
        amb["daemon"]._uids_autorizados = frozenset({999_999})
        return amb["cliente"].ler(_ctx(), ["ato:ler"])["exit_code"] == 4
    finally:
        _fechar_ambiente(amb)


def _bloqueou_xml_entity() -> bool:
    xml_hostil = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>'
    bloqueou = False
    try:
        mod_formatos.parse_xml_seguro(xml_hostil)
    except mod_formatos.ErroDescompressao:
        bloqueou = True
    return bloqueou


def _bloqueou_bomba_zip() -> bool:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zero.bin", b"\x00" * (2 * 1024 * 1024))
    bloqueou = False
    with zipfile.ZipFile(io.BytesIO(buf.getvalue()), "r") as zf:
        try:
            mod_formatos.ler_zip_seguro(zf, "zero.bin")
        except mod_formatos.ErroDescompressao:
            bloqueou = True
    return bloqueou


def _bloqueou_cache_lru() -> bool:
    cache = mod_nucleo.CacheLRUBytes(limite_bytes=100)
    cache.gravar("a", "1", 60)
    cache.gravar("b", "2", 60)
    return cache.obter("a") is None and cache.bytes_usados <= 100


def _testar_mutante(
    monkeypatch: pytest.MonkeyPatch,
    alvo: Any,
    attr: str,
    substituto: Any,
    checar_guarda: Callable[[], bool],
) -> bool:
    """Retorna True se o mutante foi morto (a guarda deixou de bloquear quando mutada)."""
    assert checar_guarda() is True
    with monkeypatch.context() as mp:
        mp.setattr(alvo, attr, substituto)
        return not checar_guarda()


def test_mutacao_guardas_seguranca_e_memoria_zero_sobreviventes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Planta mutantes nas guardas de segurança e memória e prova 0 mutantes sobreviventes."""
    raiz_git = tmp_path / "rel_mut"
    raiz_git.mkdir()
    seg_externo = tmp_path / "fora.txt"
    seg_externo.write_text("segredo\n", encoding="utf-8")
    os.symlink(seg_externo, raiz_git / "elo.md")
    reg = raiz_git / "normal.md"
    reg.write_text("ok\n", encoding="utf-8")

    p_pol = tmp_path / "acesso" / "politica.yaml"
    p_tri = tmp_path / "var" / "trilha" / "trilha-bruta.jsonl"
    orig_cache_init = mod_nucleo.CacheLRUBytes.__init__
    vista_aberta = VistaAlcance(
        verbos_aceitam_ler=frozenset({"ontologia"}),
        alcance_verbo={"ontologia": frozenset({"*"})},
        classes={"ato": ClasseAlcance("ato", "git", "busca", molde="ato/<slug>.md")},
    )
    vista_fechada = VistaAlcance(
        verbos_aceitam_ler=frozenset({"ontologia"}),
        alcance_verbo={"ontologia": frozenset({"shape"})},
        classes={"ato": ClasseAlcance("ato", "git", "busca", molde="ato/<slug>.md")},
    )
    monkeypatch.setattr(mod_resolvedor, "carregar_vista_alcance", lambda *_a, **_k: vista_fechada)

    casos: list[tuple[str, Any, str, Any, Callable[[], bool]]] = [
        ("git.O_NOFOLLOW", mod_git, "_FLAGS_ABERTURA", os.O_RDONLY | os.O_CLOEXEC, lambda: _bloqueou_symlink(raiz_git)),
        (
            "git.fstat_dev_ino",
            mod_git,
            "_validar_fd_regular",
            lambda _d, _u, fd, _r: os.fstat(fd),
            lambda: _bloqueou_fstat_dev_ino(raiz_git, reg, monkeypatch),
        ),
        (
            "resolvedor.vista_alcance",
            mod_resolvedor,
            "carregar_vista_alcance",
            lambda *_a, **_k: vista_aberta,
            _bloqueou_alcance,
        ),
        (
            "daemon.SO_PEERCRED",
            DaemonLeitor,
            "_autorizar_chamador",
            lambda _s, _c: None,
            lambda: _bloqueou_peercred(tmp_path / "peer"),
        ),
        (
            "morada.eh_segredo",
            mod_morada,
            "eh_segredo",
            lambda _p: False,
            lambda: mod_morada.eh_segredo(p_pol) and mod_morada.eh_segredo(p_tri),
        ),
        ("formatos.parse_xml_seguro", mod_formatos, "parse_xml_seguro", lambda _b: None, _bloqueou_xml_entity),
        ("formatos._valida_razao", mod_formatos, "_valida_razao", lambda _d, _c, _r: None, _bloqueou_bomba_zip),
        (
            "nucleo.CacheLRUBytes",
            mod_nucleo.CacheLRUBytes,
            "__init__",
            lambda self, limite_bytes=0: orig_cache_init(self, limite_bytes=10**12),
            _bloqueou_cache_lru,
        ),
    ]

    sobreviventes = [
        nome for nome, alvo, attr, sub, checar in casos if not _testar_mutante(monkeypatch, alvo, attr, sub, checar)
    ]
    assert sobreviventes == [], f"mutantes vivos nas guardas: {sobreviventes}"
    assert mod_formatos.MEMBRO_MAX == 64 * 1024 * 1024
    assert mod_formatos.RAZAO_COMPRESSAO_MAX == 100.0
    assert mod_formatos.CELULAS_XLSX_MAX == 200_000
    assert mod_nucleo.CACHE_EXTRA_BYTES_MAX == 32 * 1024 * 1024
