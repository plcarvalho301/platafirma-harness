# componente: componente:escrita
"""Testes herméticos dos registros, política e conversão de borda da escrita (story #4441, t1)."""
from __future__ import annotations

import io
import json
import os
import resource
import sys
from pathlib import Path

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = HARNESS_ROOT / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from escrita.pedido import (  # noqa: E402
    desligar_core_dump,
    eh_uuidv7,
    ler_stdin_limitado,
    ler_token_descritor,
    parsear_pedido,
)
from escrita.politica import (  # noqa: E402
    carregar_politica,
    eh_caminho_protegido,
    eh_superficie_vedada,
    exige_shebang,
    verbo_ligado,
)
from escrita.tipos import (  # noqa: E402
    CAMPOS_ERRO,
    ContextoEscrita,
    ErroEscrita,
    RecusaEscrita,
    ResultadoEscrita,
    emitir_recusa,
)

CONFIG_PATH = HARNESS_ROOT / "registro" / "escrita.yaml"
SCHEMA_PATH = HARNESS_ROOT / "registro" / "esquemas" / "retorno-escrever.schema.json"


def _emitir_e_ler_ultima_linha(recusa: RecusaEscrita) -> tuple[int, dict]:
    buf = io.StringIO()
    saida = emitir_recusa(recusa, fluxo=buf)
    linhas = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(linhas) == 1
    return saida, json.loads(linhas[-1])


def test_registro_escrita_yaml_e_esquema_canonico() -> None:
    pol = carregar_politica(CONFIG_PATH)
    assert pol.versao == 1
    assert pol.entrada_max_bytes == 1_048_576
    assert pol.prazo_max_s == 30
    assert pol.verbos_ligados == frozenset({"repo", "ontologia"})
    assert verbo_ligado(pol, "repo")
    assert verbo_ligado(pol, "ontologia")

    esquema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert "release" in esquema["required"]
    assert set(esquema["properties"]["forma"]["enum"]) == {
        "gravar",
        "criar",
        "trocar",
        "retirar",
        "restaurar",
        "ensaiar",
    }

    res = ResultadoEscrita(
        chave="platafirma-harness:lib/escrita/tipos.py",
        classe="componente",
        forma="gravar",
        morada="git",
        release="rel-20261125",
        pedido="019360a0-8b12-7c00-9a11-001122334455",
        alterou=True,
        ja_gravado=False,
        substituiu=False,
        bytes=42,
        versao="abcdef123456",
    )
    payload = res.como_dict()
    for campo in esquema["required"]:
        assert campo in payload
    assert payload["release"] == "rel-20261125"


def test_politica_ausente_ou_malformada_sai_3(tmp_path: Path) -> None:
    with pytest.raises(RecusaEscrita) as exc_ausente:
        carregar_politica(tmp_path / "inexistente.yaml")
    assert exc_ausente.value.saida == 3
    assert exc_ausente.value.primeiro.codigo == "politica-indisponivel"

    invalido = tmp_path / "escrita.yaml"
    invalido.write_text("versao: [1, 2\n", encoding="utf-8")
    with pytest.raises(RecusaEscrita) as exc_yaml:
        carregar_politica(invalido)
    assert exc_yaml.value.saida == 3
    assert exc_yaml.value.primeiro.codigo == "politica-indisponivel"


def test_catalogo_fechado_e_seis_campos_em_ordem() -> None:
    with pytest.raises(ValueError):
        ErroEscrita(saida=2, codigo="codigo-inventado")
    with pytest.raises(ValueError):
        ErroEscrita(saida=4, codigo="conteudo-vazio")
    with pytest.raises(ValueError):
        ErroEscrita(saida=9, codigo="conteudo-vazio")

    err = ErroEscrita(
        saida=2,
        codigo="conteudo-vazio",
        onde="stdin",
        recebido="0 bytes",
        regra="não truncar",
        cura="envie conteúdo",
        proximo="repo gravar componente x",
    )
    assert tuple(err.como_dict().keys()) == CAMPOS_ERRO

    saida, payload = _emitir_e_ler_ultima_linha(RecusaEscrita(err))
    assert saida == 2
    assert tuple(payload["erro"].keys()) == CAMPOS_ERRO
    assert len(payload["erros"]) == 1

    ctx = ContextoEscrita(verbo="repo", cadeira="engenharia")
    assert ctx.token == ""


@pytest.mark.parametrize(
    "caminho",
    [
        "acesso/politica.yaml",
        "acesso/sujeitos.yaml",
        "sub/.env",
        "sub/.env.prod",
        "chaves/prod.key",
        "/srv/platafirma/casa/segredos/olaria.key",
        "/srv/platafirma/casa/var/log/porta.jsonl",
        "/srv/platafirma/casa/var/fila/engenharia.jsonl",
        "/opt/platafirma/current/harness/bin/repo",
        "platafirma-harness/.git/config",
    ],
)
def test_superficies_vedadas(caminho: str) -> None:
    pol = carregar_politica(CONFIG_PATH)
    assert eh_superficie_vedada(pol, caminho) is True


def test_caminhos_protegidos_por_repo_e_prefixo_e_shebang() -> None:
    pol = carregar_politica(CONFIG_PATH)
    assert eh_caminho_protegido(pol, "platafirma-core", "acesso/pdp.py") is True
    assert eh_caminho_protegido(pol, "platafirma-core", "acesso/pep.py") is True
    assert eh_caminho_protegido(pol, "platafirma-core", "porta/decisao.py") is True
    assert eh_caminho_protegido(pol, "platafirma-core", "deploy/setup-escritor.sh") is True
    assert eh_caminho_protegido(pol, "platafirma-harness", "lib/escrita/tipos.py") is True
    assert eh_caminho_protegido(pol, "platafirma-harness", "lib/leitura/recusa.py") is True
    assert eh_caminho_protegido(pol, "platafirma-harness", "registro/escrita.yaml") is True
    assert eh_caminho_protegido(pol, "platafirma-harness", "deploy-harness/escritor.service") is True
    # Nome solto em outro repo não ativa proteção de outro repo
    assert eh_caminho_protegido(pol, "platafirma-ui", "acesso/pdp.py") is False
    assert eh_caminho_protegido(pol, "platafirma-harness", "testes/test_escrita_borda.py") is False

    assert exige_shebang(pol, "platafirma-harness", "bin/repo") is True
    assert exige_shebang(pol, "platafirma-harness", "deploy-harness/setup.sh") is True
    assert exige_shebang(pol, "platafirma-harness", "bin/_release/conferir/conferir.py") is False
    assert exige_shebang(pol, "platafirma-harness", "lib/escrita/tipos.py") is False


@pytest.mark.parametrize(
    ("argv", "codigo_esperado", "trecho_proximo"),
    [
        (["escrever", "componente", "platafirma-harness:a.py"], "variante-nao-executa", "gravar"),
        (["editar", "chapeu", "chapeu:interfaces"], "variante-nao-executa", "ler"),
        (["gravar", "componente", "platafirma-harness:a.py", "--dry-run"], "variante-nao-executa", "ensaiar"),
        (["gravar", "componente", "platafirma-harness:a.py", "--ensaio"], "variante-nao-executa", "ensaiar"),
        (["gravar", "chapeu", "instancias/chapeu/interfaces.md"], "caminho-solto-recusado", "chapeu:interfaces"),
        (["criar", "chapeu", "/srv/platafirma/casa/x.md"], "caminho-solto-recusado", "<classe>:<slug>"),
        (["gravar", "componente", "platafirma-harness:a.py", "--invalida"], "flag-desconhecida", ""),
        (["criar", "chapeu", "chapeu:x", "--formato", "patch"], "conflito-de-opcoes", ""),
        (["gravar", "componente", "platafirma-harness:a.py", "--pedido", "nao-uuid"], "pedido-invalido", ""),
    ],
)
def test_recusas_de_gramatica_e_borda(
    argv: list[str], codigo_esperado: str, trecho_proximo: str
) -> None:
    pol = carregar_politica(CONFIG_PATH)
    ctx = ContextoEscrita(verbo="repo", exige_objeto_casa="chapeu" in argv)
    with pytest.raises(RecusaEscrita) as exc:
        parsear_pedido("repo", argv, b"conteudo\n", politica=pol, contexto=ctx)
    saida, payload = _emitir_e_ler_ultima_linha(exc.value)
    assert saida == 2
    assert payload["erro"]["codigo"] == codigo_esperado
    assert tuple(payload["erro"].keys()) == CAMPOS_ERRO
    if trecho_proximo:
        assert trecho_proximo in payload["erro"]["proximo"]


@pytest.mark.parametrize(
    ("stdin_bytes", "codigo_esperado"),
    [
        (b"", "conteudo-vazio"),
        (b"# parte 1 de 3\nconteudo\n", "conteudo-parcial"),
        (b'{"parcial": true, "texto": "x"}', "conteudo-parcial"),
        (b"caf\xe9\n", "encoding-invalido"),
        (b"abc\x00def", "arquivo-binario"),
        (b"a" * (1_048_576 + 1), "tamanho-excedido"),
    ],
)
def test_recusas_de_conteudo_stdin(stdin_bytes: bytes, codigo_esperado: str) -> None:
    pol = carregar_politica(CONFIG_PATH)
    with pytest.raises(RecusaEscrita) as exc:
        parsear_pedido(
            "repo",
            ["gravar", "componente", "platafirma-harness:lib/x.py"],
            stdin_bytes,
            politica=pol,
        )
    saida, payload = _emitir_e_ler_ultima_linha(exc.value)
    assert saida == 2
    assert payload["erro"]["codigo"] == codigo_esperado
    assert tuple(payload["erro"].keys()) == CAMPOS_ERRO


def test_permitir_vazio_uuidv7_e_leitura_limitada() -> None:
    pol = carregar_politica(CONFIG_PATH)
    ped = parsear_pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/pkg/__init__.py", "--permitir-vazio"],
        b"",
        politica=pol,
    )
    assert ped.conteudo == ""
    assert ped.permitir_vazio is True
    assert eh_uuidv7(ped.pedido)

    with pytest.raises(RecusaEscrita) as exc:
        ler_stdin_limitado(io.BytesIO(b"12345"), 4)
    assert exc.value.saida == 2
    assert exc.value.primeiro.codigo == "tamanho-excedido"


def test_token_lido_apenas_por_descritor_herdado_e_core_dump_zerado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    desligar_core_dump()
    soft, _ = resource.getrlimit(resource.RLIMIT_CORE)
    assert soft == 0

    # Variável de ambiente de token nunca é lida
    monkeypatch.setenv("PF_TOKEN", "segredo-em-env-nao-deve-ser-lido")
    monkeypatch.delenv("PF_TOKEN_FD", raising=False)
    assert ler_token_descritor() == ""

    r_fd, w_fd = os.pipe()
    os.write(w_fd, b"tok-teste-123\n")
    os.close(w_fd)
    monkeypatch.setenv("PF_TOKEN_FD", str(r_fd))
    assert ler_token_descritor() == "tok-teste-123"

    # Token acima do teto (16 KiB) é recusado com token-invalido em vez de truncado
    r2_fd, w2_fd = os.pipe()
    os.write(w2_fd, b"x" * (16_384 + 64))
    os.close(w2_fd)
    monkeypatch.setenv("PF_TOKEN_FD", str(r2_fd))
    with pytest.raises(RecusaEscrita) as exc_tok:
        ler_token_descritor()
    assert exc_tok.value.saida == 4
    assert exc_tok.value.primeiro.codigo == "token-invalido"


def test_codigo_fonte_com_literal_parcial_nao_e_recusado() -> None:
    pol = carregar_politica(CONFIG_PATH)
    codigo_python = b'exemplo = \'{"parcial": true, "texto": "x"}\'\n'
    ped = parsear_pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:testes/exemplo.py"],
        codigo_python,
        politica=pol,
    )
    assert ped.conteudo == codigo_python.decode("utf-8")


def test_sem_import_da_porta_em_lib_escrita() -> None:
    proibidos = {"fastmcp", "starlette", "valkey", "redis"}
    for arq in (LIB_DIR / "escrita").glob("*.py"):
        texto = arq.read_text(encoding="utf-8").lower()
        for pkg in proibidos:
            assert f"import {pkg}" not in texto
            assert f"from {pkg}" not in texto
