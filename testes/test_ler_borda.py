# componente: componente:leitura
"""Testes dos registros imutáveis e da borda da camada comum do ato ler (story #4442, t2)."""
from __future__ import annotations

import dataclasses
import json
import os

import pytest

from leitura.borda import (
    ErroBorda,
    assinar_cursor,
    calcular_query_hash,
    parsear_chamada_ler,
    sanitizar_recebido,
    validar_lista_estrita,
)
from leitura.tipos import (
    CAMPOS_RECUSA,
    ContextoChamada,
    CursorDecodificado,
    FiltroCatalogo,
    PedidoLer,
    PedidoListar,
    SeletorParte,
)

SEGREDO_TESTE = b"chave-de-teste-hmac-32-bytes-ok!"


def test_registros_sao_imutaveis_e_sujeito_jwt_vazio() -> None:
    ctx = ContextoChamada(sujeito="engenharia", verbo="busca")
    assert ctx.sujeito_jwt is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.sujeito = "outro"  # type: ignore[misc]

    sel = SeletorParte()
    with pytest.raises(dataclasses.FrozenInstanceError):
        sel.max_bytes = 10  # type: ignore[misc]


def test_pf_token_fd_lido_e_fechado_na_largada() -> None:
    r_fd, w_fd = os.pipe()
    os.write(w_fd, b"header.payload.signature")
    os.close(w_fd)
    ctx, ped = parsear_chamada_ler(
        ["ler", "ato:ler"],
        {"PF_CADEIRA": "engenharia", "PF_TOKEN_FD": str(r_fd)},
        verbo="busca",
    )
    assert ctx.sujeito == "engenharia"
    assert ctx.sujeito_jwt is None
    assert isinstance(ped, PedidoLer)
    assert ped.chaves == ("ato:ler",)
    with pytest.raises(OSError):
        os.fstat(r_fd)


@pytest.mark.parametrize("caminho", ["/etc/passwd", "./segredo.txt", "../fora.txt", "~/chave"])
def test_caminho_solto_recusado_com_json_seis_campos(caminho: str) -> None:
    with pytest.raises(ErroBorda) as exc:
        parsear_chamada_ler(["ler", caminho], {"PF_CADEIRA": "engenharia"}, verbo="busca")
    assert exc.value.saida == 2
    payload = json.loads(exc.value.serializar_stderr())
    assert tuple(payload.keys()) == CAMPOS_RECUSA
    assert payload["codigo"] == "caminho-solto-recusado"


@pytest.mark.parametrize(
    "argv",
    [
        ["ler", "ato:ler", "--linhas", "0"],
        ["ler", "ato:ler", "--linhas", "0-5"],
        ["ler", "ato:ler", "--linhas", "10-5"],
        ["ler", "ato:ler", "--max-bytes", "0"],
        ["ler", "ato:ler", "--max-bytes", "-10"],
        ["listar", "ato", "--limite", "0"],
    ],
)
def test_flags_invalidas_saem_2(argv: list[str]) -> None:
    with pytest.raises(ErroBorda) as exc:
        parsear_chamada_ler(argv, {"PF_CADEIRA": "engenharia"}, verbo="busca")
    assert exc.value.saida == 2
    assert any(r.codigo == "flag-invalida" for r in exc.value.recusas)


def test_texto_escalar_no_lugar_de_lista_sai_2() -> None:
    itens, err = validar_lista_estrita("ato:ler", onde="chaves")
    assert itens is None
    assert err is not None
    assert err.saida == 2
    assert err.codigo == "flag-invalida"


@pytest.mark.parametrize(
    "argv",
    [
        ["ler", "ato:ler", "--linhas", "1-10", "--paginas", "1-2"],
        ["ler", "ato:ler", "--linhas", "1-10", "--offset", "5"],
        ["ler", "ato:ler", "--dpi", "150"],
    ],
)
def test_combinacoes_invalidas_saem_2(argv: list[str]) -> None:
    with pytest.raises(ErroBorda) as exc:
        parsear_chamada_ler(argv, {"PF_CADEIRA": "engenharia"}, verbo="busca")
    assert exc.value.saida == 2
    assert any(r.codigo == "combinacao-invalida" for r in exc.value.recusas)


def test_acumula_todos_os_erros_numa_passada_e_sanitiza_recebido() -> None:
    with pytest.raises(ErroBorda) as exc:
        parsear_chamada_ler(
            ["ler", "/etc/passwd", "--linhas", "10-2", "--dpi", "150"],
            {"PF_CADEIRA": "engenharia"},
            verbo="busca",
        )
    codigos = {r.codigo for r in exc.value.recusas}
    assert {"caminho-solto-recusado", "flag-invalida", "combinacao-invalida"} <= codigos
    payload = json.loads(exc.value.serializar_stderr())
    assert "erro" in payload and "erros" in payload and len(payload["erros"]) >= 3

    longo = "Bearer supersecret " + ("x" * 300)
    san = sanitizar_recebido(longo)
    assert len(san) <= 200
    assert "supersecret" not in san


def test_cursor_assinado_valida_sujeito_e_filtros() -> None:
    filtros = (FiltroCatalogo(tipo="prop", nome="estrato", valor="construcao"),)
    qhash = calcular_query_hash("busca", "chapeu", filtros, None)
    cur = CursorDecodificado(
        versao_token="v1",
        sujeito="engenharia",
        verbo="busca",
        classe="chapeu",
        query_hash=qhash,
        versao_retrato="fornada-1",
        ultima_ordem="01",
        ultima_chave="chapeu:interfaces",
    )
    token = assinar_cursor(cur, segredo=SEGREDO_TESTE)

    # Caso válido: mesmo sujeito e mesmos filtros
    _, ped = parsear_chamada_ler(
        ["listar", "chapeu", "--prop", "estrato=construcao", "--cursor", token],
        {"PF_CADEIRA": "engenharia"},
        verbo="busca",
        segredo_cursor=SEGREDO_TESTE,
    )
    assert isinstance(ped, PedidoListar)
    assert ped.cursor == cur

    # Outro sujeito -> continuacao-divergente
    with pytest.raises(ErroBorda) as exc_suj:
        parsear_chamada_ler(
            ["listar", "chapeu", "--prop", "estrato=construcao", "--cursor", token],
            {"PF_CADEIRA": "produto"},
            verbo="busca",
            segredo_cursor=SEGREDO_TESTE,
        )
    assert exc_suj.value.recusas[0].codigo == "continuacao-divergente"

    # Filtro alterado -> continuacao-divergente
    with pytest.raises(ErroBorda) as exc_flt:
        parsear_chamada_ler(
            ["listar", "chapeu", "--prop", "estrato=operacao", "--cursor", token],
            {"PF_CADEIRA": "engenharia"},
            verbo="busca",
            segredo_cursor=SEGREDO_TESTE,
        )
    assert exc_flt.value.recusas[0].codigo == "continuacao-divergente"

    # Token adulterado -> continuacao-ilegivel
    adulterado = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(ErroBorda) as exc_cor:
        parsear_chamada_ler(
            ["listar", "chapeu", "--prop", "estrato=construcao", "--cursor", adulterado],
            {"PF_CADEIRA": "engenharia"},
            verbo="busca",
            segredo_cursor=SEGREDO_TESTE,
        )
    assert exc_cor.value.recusas[0].codigo == "continuacao-ilegivel"
