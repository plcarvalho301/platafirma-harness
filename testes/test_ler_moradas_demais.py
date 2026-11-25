"""Testes dos adaptadores wiki, balde, fila, rastreador e cofre (story #4442, t6)."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.error
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from leitura.moradas import ErroMorada, RegistroMoradas
from leitura.moradas.balde import AdaptadorBalde, criar_abridor_bytes
from leitura.moradas.cofre import AdaptadorCofre
from leitura.moradas.fila import SUJEITO_ATUAL, AdaptadorFila
from leitura.moradas.rastreador import AdaptadorRastreador
from leitura.moradas.wiki import AdaptadorWiki
from leitura.tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    SeletorParte,
)


def _alvo(
    chave: str,
    classe: str,
    morada: str,
    endereco: str | None = None,
    *,
    fechado: bool = True,
) -> AlvoResolvido:
    return AlvoResolvido(
        chave_pedida=chave,
        chave_canonica=chave,
        classe=classe,
        morada=morada,  # type: ignore[arg-type]
        endereco=endereco or chave,
        universo_fechado=fechado,
        digest_release=None,
    )


# ------------------------------------------------------------------ wiki
def test_wiki_ler_revisao_ausencia_timeout_e_listar() -> None:
    chamadas: list[dict[str, str]] = []

    def _http(_url: str, params: Mapping[str, str], _timeout: float) -> dict[str, Any]:
        chamadas.append(dict(params))
        if params.get("list") == "allpages":
            return {"query": {"allpages": [{"title": "Beta"}, {"title": "Alfa"}]}}
        if params.get("titles") == "Falta":
            return {"query": {"pages": {"-1": {"missing": ""}}}}
        if params.get("revids") == "77":
            return {
                "query": {
                    "pages": {
                        "1": {"revisions": [{"revid": 77, "slots": {"main": {"content": "v77"}}}]}
                    }
                }
            }
        return {
            "query": {
                "pages": {
                    "1": {"revisions": [{"revid": 99, "slots": {"main": {"content": "corpo wiki"}}}]}
                }
            }
        }

    wiki = AdaptadorWiki(url_api="http://wiki.local/api.php", cliente_http=_http)
    bruto = wiki.ler_objeto(_alvo("pagina:Inicio", "pagina", "wiki", fechado=False), SeletorParte(), 2_000)
    assert bruto.versao == "99"
    assert bruto.dados == b"corpo wiki"

    bruto_rev = wiki.ler_objeto(
        _alvo("pagina:Inicio", "pagina", "wiki", fechado=False),
        SeletorParte(versao_pedida="77"),
        2_000,
    )
    assert bruto_rev.versao == "77"
    assert bruto_rev.dados == b"v77"

    with pytest.raises(ErroMorada) as exc_miss:
        wiki.ler_objeto(_alvo("pagina:Falta", "pagina", "wiki", fechado=False), SeletorParte(), 2_000)
    assert exc_miss.value.saida == 1
    assert exc_miss.value.recusa.codigo == "chave-inexistente"

    pag = wiki.listar_chaves("pagina", (), None, 1, None, 2_000)
    assert pag.universo_fechado is False
    assert [it["chave"] for it in pag.itens] == ["pagina:Alfa"]
    assert pag.proxima_tupla == (0, "pagina:Alfa")

    def _timeout(_u: str, _p: Mapping[str, str], _t: float) -> dict[str, Any]:
        raise TimeoutError("lento")

    with pytest.raises(ErroMorada) as exc_to:
        AdaptadorWiki(cliente_http=_timeout).ler_objeto(
            _alvo("pagina:Inicio", "pagina", "wiki", fechado=False), SeletorParte(), 500
        )
    assert exc_to.value.saida == 5
    assert exc_to.value.recusa.codigo == "tempo-esgotado"

    def _fora(_u: str, _p: Mapping[str, str], _t: float) -> dict[str, Any]:
        raise OSError("recusado")

    with pytest.raises(ErroMorada) as exc_fora:
        AdaptadorWiki(cliente_http=_fora).ler_objeto(
            _alvo("pagina:Inicio", "pagina", "wiki", fechado=False), SeletorParte(), 500
        )
    assert exc_fora.value.saida == 3
    assert exc_fora.value.recusa.codigo == "morada-sem-resposta"


# ------------------------------------------------------------------ balde
def test_balde_ler_sha256_zip_extrator_e_erros() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("notas.txt", "ola do zip")
    zip_bytes = buf.getvalue()
    sha_zip = hashlib.sha256(zip_bytes).hexdigest()

    txt_bytes = b"texto puro no balde"
    sha_txt = hashlib.sha256(txt_bytes).hexdigest()
    sha_seg = hashlib.sha256(b"segredo").hexdigest()

    abridor = criar_abridor_bytes(
        {
            sha_zip: (zip_bytes, "pacote.zip"),
            sha_txt: (txt_bytes, "doc.txt"),
            sha_seg: (b"segredo", ".env"),
        }
    )
    fds_recebidos: list[tuple[int, dict[str, Any]]] = []

    def _extrator_fake(fd: int, pedido: Mapping[str, Any], _prazo: int) -> dict[str, Any]:
        fds_recebidos.append((fd, dict(pedido)))
        return {"ok": True, "tipo": "application/zip", "conteudo": "ola do zip", "avisos": []}

    balde = AdaptadorBalde(
        abridor=abridor,
        listador=lambda _p: [
            {"sha256": sha_txt, "nome": "doc.txt"},
            {"sha256": sha_seg, "nome": ".env"},
        ],
        extrator=_extrator_fake,
    )

    obj_zip = balde.ler_objeto(
        _alvo(f"objeto:{sha_zip}", "objeto", "balde", fechado=False),
        SeletorParte(membro="notas.txt"),
        3_000,
    )
    assert obj_zip.versao == sha_zip
    assert obj_zip.dados == b"ola do zip"
    assert len(fds_recebidos) == 1
    assert fds_recebidos[0][1]["membro"] == "notas.txt"

    obj_txt = balde.ler_objeto(
        _alvo(f"objeto:{sha_txt}", "objeto", "balde", fechado=False), SeletorParte(), 3_000
    )
    assert obj_txt.dados == txt_bytes

    with pytest.raises(ErroMorada) as exc_seg:
        balde.ler_objeto(
            _alvo(f"objeto:{sha_seg}", "objeto", "balde", fechado=False), SeletorParte(), 3_000
        )
    assert exc_seg.value.saida == 4
    assert exc_seg.value.recusa.codigo == "segredo-fora-do-leitor"

    with pytest.raises(ErroMorada) as exc_bad:
        balde.ler_objeto(_alvo("objeto:nao-e-sha", "objeto", "balde", fechado=False), SeletorParte(), 1_000)
    assert exc_bad.value.saida == 2
    assert exc_bad.value.recusa.codigo == "chave-mal-formada"

    with pytest.raises(ErroMorada) as exc_ver:
        balde.ler_objeto(
            _alvo(f"objeto:{sha_txt}", "objeto", "balde", fechado=False),
            SeletorParte(versao_pedida="0" * 64),
            1_000,
        )
    assert exc_ver.value.saida == 2
    assert exc_ver.value.recusa.codigo == "versao-divergente"

    pag = balde.listar_chaves("objeto", (), None, 10, None, 1_000)
    assert [it["chave"] for it in pag.itens] == [f"objeto:{sha_txt}"]


# ------------------------------------------------------------------ fila
class _ValkeyFalso:
    def __init__(self) -> None:
        self.comandos: list[str] = []
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {
            "fila:mensagens": [
                ("1700-0", {"assunto": "aviso", "de": "ti"}),
                ("1701-0", {"assunto": "entrega", "de": "engenharia"}),
            ]
        }
        self.kv: dict[str, str] = {
            "lousa:s1": json.dumps({"itens": ["a"]}),
            "execucao:e1": json.dumps({"sujeito": "alice", "estado": "ok", "versao": "v1"}),
            "execucao:e2": json.dumps({"sujeito": "bob", "estado": "ok", "versao": "v2"}),
        }

    def xrange(
        self, name: str, min: str = "-", max: str = "+", count: int | None = None
    ) -> list[tuple[str, dict[str, str]]]:
        self.comandos.append("XRANGE")
        itens = self.streams.get(name, [])
        res = [
            (eid, campos)
            for eid, campos in itens
            if (min == "-" or eid >= min) and (max == "+" or eid <= max)
        ]
        return res[:count] if count is not None else res

    def get(self, name: str) -> str | None:
        self.comandos.append("GET")
        return self.kv.get(name)

    def scan_iter(self, match: str | None = None) -> list[str]:
        self.comandos.append("SCAN")
        pref = (match or "").rstrip("*")
        return [k for k in self.kv if k.startswith(pref)]


def test_fila_sem_avancar_consumo_e_isolamento_de_execucao() -> None:
    vk = _ValkeyFalso()
    fila = AdaptadorFila(cliente=vk)

    msg = fila.ler_objeto(_alvo("mensagem:1700-0", "mensagem", "fila"), SeletorParte(), 2_000)
    assert msg.versao == "1700-0"
    assert "aviso" in (msg.dados or b"").decode("utf-8")
    assert all(c in {"XRANGE", "GET", "SCAN"} for c in vk.comandos)

    lousa = fila.ler_objeto(_alvo("lousa:s1", "lousa", "fila"), SeletorParte(), 2_000)
    assert "itens" in (lousa.dados or b"").decode("utf-8")

    tok = SUJEITO_ATUAL.set("alice")
    try:
        ex_ok = fila.ler_objeto(_alvo("execucao:e1", "execucao", "fila"), SeletorParte(), 2_000)
        assert ex_ok.versao == "v1"

        # Execução de outro sujeito sai 4 acesso-negado
        with pytest.raises(ErroMorada) as exc_outro:
            fila.ler_objeto(_alvo("execucao:e2", "execucao", "fila"), SeletorParte(), 2_000)
        assert exc_outro.value.saida == 4
        assert exc_outro.value.recusa.codigo == "acesso-negado"

        # Execução inexistente também sai 4 acesso-negado (não vaza existência)
        with pytest.raises(ErroMorada) as exc_inex:
            fila.ler_objeto(_alvo("execucao:nao-existe", "execucao", "fila"), SeletorParte(), 2_000)
        assert exc_inex.value.saida == 4
        assert exc_inex.value.recusa.codigo == "acesso-negado"

        # Listar execuções conta apenas as do próprio sujeito
        pag = fila.listar_chaves("execucao", (), None, 10, None, 2_000)
        assert pag.total == 1
        assert [it["chave"] for it in pag.itens] == ["execucao:e1"]
    finally:
        SUJEITO_ATUAL.reset(tok)


# ------------------------------------------------------------------ rastreador
def test_rastreador_card_terminal_ancestrais_e_listar() -> None:
    def _http(url: str, params: Mapping[str, str], _timeout: float) -> Any:
        if url.endswith("/cards/4442"):
            base: dict[str, Any] = {
                "id": "4442",
                "titulo": "Leitor unico",
                "estado": "em-execucao",
                "versao": "12",
                "decisoes_ancestrais": ["decisao-epico-1"],
            }
            return base
        if url.endswith("/cards/999"):
            return {"id": "999", "titulo": "Fechado", "estado": "concluido", "versao": "3"}
        if url.endswith("/cards/404"):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]
        if url.endswith("/cards"):
            return {
                "itens": [
                    {"id": "4442", "titulo": "Leitor unico", "estado": "em-execucao", "mae": "4000"},
                    {"id": "999", "titulo": "Fechado", "estado": "concluido", "mae": "4000"},
                ]
            }
        return None

    rast = AdaptadorRastreador(url_base="http://rast.local", cliente_http=_http)

    # Sem --com-decisoes-ancestrais: omite decisoes_ancestrais
    st_sem = rast.ler_objeto(_alvo("story:4442", "story", "rastreador"), SeletorParte(), 2_000)
    assert st_sem.versao == "12"
    assert "decisoes_ancestrais" not in json.loads((st_sem.dados or b"{}").decode("utf-8"))

    # Com --com-decisoes-ancestrais: inclui decisoes_ancestrais
    st_com = rast.ler_objeto(
        _alvo("story:4442", "story", "rastreador"),
        SeletorParte(com_decisoes_ancestrais=True),
        2_000,
    )
    assert "decisoes_ancestrais" in json.loads((st_com.dados or b"{}").decode("utf-8"))

    # Card terminal sai 1 chave-inexistente
    with pytest.raises(ErroMorada) as exc_term:
        rast.ler_objeto(_alvo("card:999", "card", "rastreador"), SeletorParte(), 2_000)
    assert exc_term.value.saida == 1
    assert exc_term.value.recusa.codigo == "chave-inexistente"

    # Listar omite terminal por padrão e aceita filtro --filhas
    pag = rast.listar_chaves("story", (FiltroCatalogo("filhas", "filhas", "4000"),), None, 10, None, 2_000)
    assert pag.total == 1
    assert [it["chave"] for it in pag.itens] == ["story:4442"]


# ------------------------------------------------------------------ cofre
class _PontaSegredoFalsa:
    def ler_segredo(self, alvo: AlvoResolvido, _sel: SeletorParte, _prazo: int) -> ObjetoBruto:
        return ObjetoBruto(alvo=alvo, versao="s1", dados=b"delegado", total_bytes=8)

    def listar_segredos(
        self, _f: Any, _t: str | None, _l: int, _c: CursorDecodificado | None, _p: int
    ) -> PaginaBruta:
        return PaginaBruta("segredo", "s1", None, True, 1, ({"chave": "segredo:api", "rotulo": "api", "resumo_curto": ""},))


def test_cofre_recusa_no_leitor_geral_e_delega_na_ponta() -> None:
    cofre_geral = AdaptadorCofre()
    with pytest.raises(ErroMorada) as exc_seg:
        cofre_geral.ler_objeto(_alvo("segredo:db-pass", "segredo", "cofre"), SeletorParte(), 1_000)
    assert exc_seg.value.saida == 4
    assert exc_seg.value.recusa.codigo == "segredo-fora-do-leitor"
    assert exc_seg.value.recusa.proximo == "seg ler segredo db-pass"

    with pytest.raises(ErroMorada) as exc_lst:
        cofre_geral.listar_chaves("segredo", (), None, 10, None, 1_000)
    assert exc_lst.value.saida == 4
    assert exc_lst.value.recusa.codigo == "segredo-fora-do-leitor"

    cofre_ponta = AdaptadorCofre(ponta_isolada=_PontaSegredoFalsa())
    ok = cofre_ponta.ler_objeto(_alvo("segredo:db-pass", "segredo", "cofre"), SeletorParte(), 1_000)
    assert ok.dados == b"delegado"

    # Mesmo com ponta isolada, superfície vedada (politica.yaml) sai 4 sem delegar
    with pytest.raises(ErroMorada) as exc_ved:
        cofre_ponta.ler_objeto(
            _alvo("acesso/politica.yaml", "segredo", "cofre", "acesso/politica.yaml"),
            SeletorParte(),
            1_000,
        )
    assert exc_ved.value.saida == 4
    assert exc_ved.value.recusa.codigo == "segredo-fora-do-leitor"

    # RegistroMoradas despacha as cinco novas moradas
    reg = RegistroMoradas({"cofre": cofre_geral})
    assert reg.obter("cofre") is cofre_geral
