# componente: componente:leitura
"""Testes do núcleo puro de fatiamento, codificação, sumário e cache (story #4442, t3)."""
from __future__ import annotations

import io
import threading
from pathlib import Path

import pytest

from leitura.leitura import ler
from leitura.nucleo import (
    CACHE_EXTRA_BYTES_MAX,
    CacheLRUBytes,
    ErroNucleo,
    montar_sumario,
    processar_objeto,
    resolver_encoding,
    varrer_fluxo,
)
from leitura.tipos import AlvoResolvido, ObjetoBruto, SeletorParte


def _alvo(chave: str = "ato:ler", endereco: str = "ler.md") -> AlvoResolvido:
    return AlvoResolvido(
        chave_pedida=chave,
        chave_canonica=chave,
        classe="ato",
        morada="git",
        endereco=endereco,
        universo_fechado=True,
        digest_release="sha256:abc",
    )


def _reconstruir_por_paginas(dados: bytes, max_bytes: int) -> str:
    bruto = ObjetoBruto(alvo=_alvo(), versao="v1", dados=dados, nome_arquivo="doc.txt")
    seletor = SeletorParte(max_bytes=max_bytes)
    partes: list[str] = []
    for _ in range(200):
        res = processar_objeto(bruto, seletor)
        assert res.conteudo is not None
        partes.append(res.conteudo)
        if not res.parcial:
            break
        assert res.proximo_args is not None
        if "offset" in res.proximo_args:
            seletor = SeletorParte(offset=res.proximo_args["offset"], max_bytes=max_bytes)
        else:
            ini = int(str(res.proximo_args["linhas"]).rstrip("-"))
            seletor = SeletorParte(linhas=(ini, None), max_bytes=max_bytes)
    else:
        pytest.fail("paginação não convergiu em 200 voltas")
    return "".join(partes)


@pytest.mark.parametrize(
    "texto,max_bytes",
    [
        ("linha 1 çãõ 😀\nlinha 2 éêíóú\r\nlinha 3 🚀 fim\r\n", 18),
        ("áéíóú😀🚀" * 15, 11),
        ("a\r\nb\r\nc\r\nd\r\n", 5),
    ],
)
def test_concat_paginas_reconstroi_original_utf8_linha_longa_e_crlf(
    texto: str, max_bytes: int
) -> None:
    reconstruido = _reconstruir_por_paginas(texto.encode("utf-8"), max_bytes)
    assert reconstruido == texto


def test_objeto_vazio_e_cauda_negativa_e_faixa_alem_do_fim() -> None:
    vazio = ObjetoBruto(alvo=_alvo(), versao="v0", dados=b"", nome_arquivo="vazio.txt")
    res_v = processar_objeto(vazio, SeletorParte())
    assert res_v.conteudo == ""
    assert res_v.parcial is False

    linhas = "".join(f"l{i}\n" for i in range(1, 11)).encode("utf-8")
    bruto = ObjetoBruto(alvo=_alvo(), versao="v1", dados=linhas, nome_arquivo="dez.txt")
    res_cauda = processar_objeto(bruto, SeletorParte(cauda_linhas=3))
    assert res_cauda.linhas == (8, 10)
    assert res_cauda.conteudo == "l8\nl9\nl10\n"

    with pytest.raises(ErroNucleo) as exc:
        processar_objeto(bruto, SeletorParte(linhas=(50, 60)))
    assert exc.value.saida == 1
    assert exc.value.recusa.codigo == "faixa-alem-do-fim"
    assert "10" in exc.value.recusa.cura


def test_codificacao_cinco_passos_e_marca_com_perda() -> None:
    # Passo 5: cp1252 puro -> com_perda=True e aviso na primeira linha
    cp_bytes = "Ação e coração — revisão\n".encode("cp1252")
    bruto_cp = ObjetoBruto(alvo=_alvo(), versao="v1", dados=cp_bytes, nome_arquivo="cp.txt")
    res_cp = processar_objeto(bruto_cp, SeletorParte())
    assert res_cp.com_perda is True
    assert "com perda" in res_cp.cabecalho
    assert any("cp1252" in a for a in res_cp.avisos)

    # Passo 4: UTF-8 predominante com 1 byte inválido isolado -> substituição U+FFFD
    utf8_com_erro = ("ação coração revisão çãõ " * 5).encode("utf-8") + b"\xff" + b" fim\n"
    texto, enc, com_perda, avisos = resolver_encoding(utf8_com_erro)
    assert enc == "utf-8"
    assert com_perda is True
    assert "\ufffd" in texto
    assert "bytes_invalidos_substituidos" in avisos

    # Passo 1: --encoding explícita falhando -> saída 2 decodificacao-recusada
    with pytest.raises(ErroNucleo) as exc:
        resolver_encoding(b"\xff\xfe\x80", encoding_pedida="ascii")
    assert exc.value.saida == 2
    assert exc.value.recusa.codigo == "decodificacao-recusada"


def test_formato_binario_sem_extrator_sai_1() -> None:
    bruto = ObjetoBruto(alvo=_alvo(), versao="v1", dados=b"\x7fELF\x02\x01\x01\x00", nome_arquivo="bin")
    with pytest.raises(ErroNucleo) as exc:
        processar_objeto(bruto, SeletorParte())
    assert exc.value.saida == 1
    assert exc.value.recusa.codigo == "formato-sem-leitor"


@pytest.mark.parametrize(
    "nome,conteudo,esperado",
    [
        ("mod.py", "CONST = 1\nclass A:\n    class B:\n        async def f(self):\n            pass\n", "async def f"),
        ("doc.md", "---\ntitulo: x\n---\n# Titulo\nSub\n---\n```\n# falso\n```\n", "Titulo"),
        ("cfg.json", '{"a": {"b": 1}, "c": [1, 2]}', "a: object(1)"),
        ("cfg.yaml", "topo:\n  filho: 1\noutro: 2\n", "filho"),
        ("cfg.toml", "[secao]\nchave = 1\n", "secao: object(1)"),
        ("ddl.sql", "CREATE TABLE itens (id int);\nALTER VIEW v_itens RENAME TO v2;\n", "CREATE TABLE itens"),
        ("app.js", "export async function rodar() {}\nclass Motor {}\n", "function rodar"),
        ("app.ts", "export interface Alvo { id: string }\n", "interface Alvo"),
        ("run.sh", "MODO=1\nexecutar() {\n  echo ok\n}\n", "executar"),
        ("style.css", "@media (max-width: 600px) {\n.card { color: red; }\n", ".card"),
        ("page.html", "<h1>Inicio</h1><section>corpo</section>\n", "h1: Inicio"),
    ],
)
def test_sumario_dez_formatos(nome: str, conteudo: str, esperado: str) -> None:
    itens, parcial = montar_sumario(conteudo, nome, max_bytes=10_000)
    assert parcial is False
    assert any(esperado in str(it[1]) for it in itens), itens


def test_varredura_em_blocos_e_cache_lru_abaixo_de_32_mib_sob_concorrencia() -> None:
    linhas = b"x\n" * 2_500
    idx = varrer_fluxo(io.BytesIO(linhas))
    assert idx.total_bytes == len(linhas)
    assert idx.linhas_total == 2_500
    assert len(idx.marcos) == 3  # 0, 1024, 2048
    assert idx.varredura_parcial is False

    cache = CacheLRUBytes(limite_bytes=CACHE_EXTRA_BYTES_MAX)
    peso_bloco = 4 * 1024 * 1024  # 4 MiB
    erros: list[Exception] = []

    def _trabalhador(tid: int) -> None:
        try:
            for k in range(20):
                cache.gravar(f"t{tid}-{k}", f"v{k}", peso_bloco)
                assert cache.bytes_usados <= CACHE_EXTRA_BYTES_MAX
        except Exception as exc:  # pragma: no cover
            erros.append(exc)

    threads = [threading.Thread(target=_trabalhador, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not erros
    assert cache.bytes_usados <= CACHE_EXTRA_BYTES_MAX


def test_casca_leitura_nega_rascunho_de_outra_ordem(tmp_path: Path) -> None:
    inst = tmp_path / "inst"
    rasc = inst / "var" / "rascunho" / "ordem-A" / "nota.txt"
    rasc.parent.mkdir(parents=True)
    rasc.write_text("privado\n", encoding="utf-8")

    negado = ler(rasc, instancia=inst, ordem_id="ordem-B")
    assert negado.get("exit_code") == 4
    assert negado.get("recusado") is True

    permitido = ler(rasc, instancia=inst, ordem_id="ordem-A")
    assert permitido.get("exit_code", 0) == 0
    assert permitido.get("conteudo") == "privado\n"
