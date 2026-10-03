"""#2856 (linhas 153 e 96): `acervo ler biblioteca objeto` — resolve por uuid e grava em --destino.

Sem rede, sem docker, sem MinIO: a consulta ao catalogo (`_consultar`) e o download do store
(`_baixar_do_store`) sao os dois pontos de contato do sub-ato com o mundo e saem trocados aqui.
Contrato: a obra se acha por uuid inteiro, prefixo unico de uuid ou titulo (o de sempre); --destino
grava na pasta pedida (criada se faltar) so dentro de raiz permitida (bancada declarada ou
var/tmp/<ordem_id>), senao exit 4 com a causa; o retorno diz o caminho e o sha256 do que gravou.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
OBJETO = RAIZ / "bin" / "_acervo" / "objeto"

UUID_A = "11111111-aaaa-4bbb-8ccc-000000000001"
UUID_B = "11111111-aaaa-4bbb-8ccc-000000000002"
UUID_C = "9f3c2a10-5d7e-4c11-b2a4-0123456789ab"
CONTEUDO = b"%PDF-1.7 conteudo do original\n"
SHA = hashlib.sha256(CONTEUDO).hexdigest()

LINHAS = {
    UUID_A: f"Bringhurst, Elementos do estilo tipografico\tbringhurst.pdf\tacervo/{SHA}\t{UUID_A}",
    UUID_B: f"Bringhurst (2a edicao)\tbringhurst-2.pdf\tacervo/{'b' * 64}\t{UUID_B}",
    UUID_C: f"People + AI Guidebook\tpeople-ai-guidebook.pdf\tacervo/{SHA}\t{UUID_C}",
}


def _mod():
    loader = importlib.machinery.SourceFileLoader("acervo_objeto", str(OBJETO))
    spec = importlib.util.spec_from_loader("acervo_objeto", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """O catalogo falso responde pelo SQL recebido; o store falso grava CONTEUDO onde mandarem."""
    bancada = tmp_path / "bancada"
    instancia = tmp_path / "instancia"
    cwd = tmp_path / "cwd"
    for p in (bancada, instancia, cwd):
        p.mkdir()
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(bancada))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(instancia))
    monkeypatch.setenv("PF_ORDEM_ID", "o20261003T120000-abc123")
    monkeypatch.chdir(cwd)

    mod = _mod()
    sqls: list[str] = []
    baixados: list[tuple] = []

    def consultar(sql: str) -> str:
        sqls.append(sql)
        if "id::text like" in sql:
            prefixo = sql.split("id::text like '", 1)[1].split("%'", 1)[0]
            return "\n".join(l for u, l in LINHAS.items() if u.startswith(prefixo))
        if "bringhurst" in sql.lower():
            return LINHAS[UUID_A]
        return ""

    def baixar_do_store(bucket: str, sha: str, destino: Path) -> None:
        baixados.append((bucket, sha, Path(destino)))
        Path(destino).write_bytes(CONTEUDO)

    monkeypatch.setattr(mod, "_consultar", consultar)
    monkeypatch.setattr(mod, "_baixar_do_store", baixar_do_store)

    class Mundo:
        pass

    m = Mundo()
    m.mod, m.sqls, m.baixados = mod, sqls, baixados
    m.bancada, m.instancia, m.cwd = bancada, instancia, cwd
    return m


def _roda(m, capsys, *argv):
    rc = m.mod.main(list(argv))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


# --- a classe do termo --------------------------------------------------------------------------

def test_classifica_uuid_prefixo_e_titulo():
    m = _mod()
    assert m.classificar(UUID_A) == ("id", UUID_A)
    assert m.classificar(UUID_A.upper()) == ("id", UUID_A)
    assert m.classificar("11111111-aaaa") == ("id", "11111111-aaaa")
    assert m.classificar("9f3c2a10") == ("id", "9f3c2a10")
    assert m.classificar("Bringhurst") == ("titulo", "Bringhurst")
    assert m.classificar("abc") == ("titulo", "abc")          # curto demais para ser prefixo
    assert m.classificar("People + AI Guidebook") == ("titulo", "People + AI Guidebook")


# --- (a) resolve por uuid -----------------------------------------------------------------------

def test_uuid_inteiro_resolve_e_baixa(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, UUID_C)
    assert rc == 0, err
    assert mundo.baixados == [("acervo", SHA, mundo.baixados[0][2])]
    assert (mundo.cwd / "people-ai-guidebook.pdf").read_bytes() == CONTEUDO
    assert any(f"id::text like '{UUID_C}%'" in s for s in mundo.sqls)


def test_prefixo_unico_de_uuid_resolve(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, "9f3c2a10")
    assert rc == 0, err
    assert (mundo.cwd / "people-ai-guidebook.pdf").is_file()


def test_prefixo_ambiguo_recusa_exit_2_listando_e_nao_grava(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, "11111111-aaaa")
    assert rc == 2
    assert UUID_A in err + out and UUID_B in err + out
    assert mundo.baixados == [] and list(mundo.cwd.iterdir()) == []


def test_prefixo_sem_obra_cai_no_titulo_e_depois_diz_nada_encontrado(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, "deadbeef")
    assert rc == 1 and "nada encontrado para: deadbeef" in err + out
    assert any("id::text like" in s for s in mundo.sqls) and len(mundo.sqls) >= 2


def test_titulo_continua_resolvendo(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, "Bringhurst")
    assert rc == 0, err
    assert (mundo.cwd / "bringhurst.pdf").read_bytes() == CONTEUDO


def test_aspas_no_titulo_nao_quebram_o_sql(mundo, capsys):
    _roda(mundo, capsys, "O'Reilly; drop table acervo.obra")
    assert all("O''Reilly" in s for s in mundo.sqls if "O" in s and "Reilly" in s)


# --- (b) --destino ------------------------------------------------------------------------------

def test_destino_na_bancada_cria_a_pasta_e_o_retorno_diz_caminho_e_sha256(mundo, capsys):
    alvo = mundo.bancada / "wt" / "x" / "entregas" / "bringhurst"
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(alvo))
    assert rc == 0, err
    gravado = alvo / "bringhurst.pdf"
    assert gravado.read_bytes() == CONTEUDO
    assert str(gravado) in out and SHA in out
    assert not (mundo.cwd / "bringhurst.pdf").exists()


def test_destino_em_var_tmp_da_ordem_e_permitido(mundo, capsys):
    alvo = mundo.instancia / "var" / "tmp" / "o20261003T120000-abc123" / "baixados"
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(alvo))
    assert rc == 0, err
    assert (alvo / "bringhurst.pdf").is_file() and SHA in out


def test_destino_fora_da_raiz_permitida_exit_4_com_a_causa_e_nada_criado(mundo, capsys, tmp_path):
    fora = tmp_path / "fora" / "pasta"
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(fora))
    assert rc == 4
    assert "fora das raizes permitidas" in err and str(fora) in err
    assert not (tmp_path / "fora").exists() and mundo.baixados == []


def test_destino_com_ponto_ponto_que_escapa_da_bancada_exit_4(mundo, capsys, tmp_path):
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(mundo.bancada / ".." / "fora"))
    assert rc == 4 and not (tmp_path / "fora").exists()


def test_destino_por_link_simbolico_que_escapa_exit_4(mundo, capsys, tmp_path):
    fora = tmp_path / "fora"
    fora.mkdir()
    (mundo.bancada / "atalho").symlink_to(fora)
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(mundo.bancada / "atalho" / "sub"))
    assert rc == 4 and list(fora.iterdir()) == []


def test_var_tmp_de_outra_ordem_nao_vale(mundo, capsys):
    alvo = mundo.instancia / "var" / "tmp" / "outra-ordem" / "x"
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(alvo))
    assert rc == 4 and not alvo.exists()


def test_destino_posicional_legado_e_o_flag_juntos_exit_2(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, UUID_A, str(mundo.bancada / "a"), "--destino", str(mundo.bancada / "b"))
    assert rc == 2 and mundo.baixados == []


def test_nome_de_arquivo_com_caminho_grava_so_o_nome_dentro_do_destino(mundo, capsys, monkeypatch):
    perigoso = f"Obra\t../../fuga.pdf\tacervo/{SHA}\t{UUID_A}"
    monkeypatch.setattr(mundo.mod, "_consultar", lambda sql: perigoso)
    alvo = mundo.bancada / "ok"
    rc, out, err = _roda(mundo, capsys, UUID_A, "--destino", str(alvo))
    assert rc == 0, err
    assert (alvo / "fuga.pdf").is_file() and not (mundo.bancada / "fuga.pdf").exists()


# --- (c) sem --destino: o de sempre, mas o retorno diz onde gravou ------------------------------

def test_sem_destino_grava_no_diretorio_corrente_e_diz_onde_e_o_sha256(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, UUID_A)
    assert rc == 0, err
    gravado = mundo.cwd / "bringhurst.pdf"
    assert gravado.read_bytes() == CONTEUDO
    assert str(gravado) in out and SHA in out


def test_destino_posicional_legado_continua_valendo(mundo, capsys, tmp_path):
    # forma antiga `acervo baixar "<titulo>" <pasta>`: sem raiz imposta, como sempre foi.
    alvo = tmp_path / "legado"
    rc, out, err = _roda(mundo, capsys, "Bringhurst", str(alvo))
    assert rc == 0, err
    assert (alvo / "bringhurst.pdf").is_file() and str(alvo / "bringhurst.pdf") in out


# --- uso ----------------------------------------------------------------------------------------

def test_sem_termo_e_uso_exit_2(mundo, capsys):
    rc, out, err = _roda(mundo, capsys)
    assert rc == 2 and "uso: acervo ler biblioteca objeto" in err


def test_ajuda_exit_0(mundo, capsys):
    rc, out, err = _roda(mundo, capsys, "--ajuda")
    assert rc == 0 and "--destino" in out
