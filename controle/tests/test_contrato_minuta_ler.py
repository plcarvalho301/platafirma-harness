"""Contrato de `minuta ler` lendo pelo acervo (arq:0115 §11.3; incidente #3225).

Prova: com número, com número curto e com slug, o texto vem de `acervo ler casa minuta
<NNNN> --json`, e o slug resolve pelo nome do arquivo da ficha em `acervo listar casa
minuta --json`; minuta que o acervo não tem sai 1 com o motivo; sem argumento, lista as
minutas que convocam PF_CADEIRA (prefixo claudinho- aparado); acervo indeterminável sai 5,
nunca «não encontrada»; o esqueleto de `minuta escrever` traz `Espécie: minuta` antes do
primeiro ##, que é o que a ingestão exige (arq:0115 §7). Não prova: o acervo real (stub).
"""
import json
import os
import subprocess
import textwrap
from pathlib import Path

BIN = Path(__file__).resolve().parents[2] / "bin"

CORPO = textwrap.dedent("""\
    # 0041 — Wiki: rumo e fronteira

    Espécie: minuta

    Aberta por: produto · 2026-10-01
    Convocadas: arquiteto, dados, gestao-estrategica
    Fecha: pedro

    ## Pergunta
    Qual é o papel da wiki?

    ## Posição — produto

    posição escrita

    ## Posição — dados

    ### Diagnóstico — o presente medido
    <a preencher pela própria cadeira>

    ## Decisão
    <quem fecha>
    """)

STUB = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    a = sys.argv[1:]
    with open(os.environ["STUB_LOG"], "a") as f:
        f.write(" ".join(a) + "\\n")
    if os.environ.get("STUB_RC"):
        sys.stdout.write("indeterminável · psql falhou lendo acervo.casa\\n")
        sys.exit(int(os.environ["STUB_RC"]))
    if a[:3] == ["listar", "casa", "minuta"]:
        print(json.dumps([{"chave": "0041", "path": "minuta/0041-wiki-rumo-e-fronteira.md",
                           "titulo": "Wiki: rumo e fronteira"}]))
        sys.exit(0)
    if a[:3] == ["ler", "casa", "minuta"]:
        if a[3] == "0041":
            print(json.dumps({"chave": "0041", "corpo": open(os.environ["STUB_CORPO"]).read()}))
            sys.exit(0)
        sys.stderr.write("acervo casa: nada da especie 'minuta'\\n")
        sys.exit(1)
    sys.exit(2)
    """)


def _ler(tmp_path, *args, **extra):
    stub = tmp_path / "acervo"
    if not stub.exists():
        stub.write_text(STUB)
        stub.chmod(0o755)
        (tmp_path / "corpo.md").write_text(CORPO)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PF_ACERVO_BIN": str(stub),
        "STUB_LOG": str(tmp_path / "acervo.log"),
        "STUB_CORPO": str(tmp_path / "corpo.md"),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-dados",
        **extra,
    }
    return subprocess.run([str(BIN / "minuta"), "ler", *args], env=env,
                          capture_output=True, text=True, check=False)


def test_ler_por_numero_le_pelo_acervo(tmp_path):
    for alvo in ("0041", "41"):
        r = _ler(tmp_path, alvo)
        assert r.returncode == 0, r.stderr
        assert r.stdout == CORPO
    assert "ler casa minuta 0041 --json" in (tmp_path / "acervo.log").read_text()


def test_ler_por_slug_resolve_pelo_arquivo_da_ficha(tmp_path):
    r = _ler(tmp_path, "wiki-rumo-e-fronteira")
    assert r.returncode == 0, r.stderr
    assert r.stdout == CORPO


def test_ler_minuta_que_o_acervo_nao_tem_sai_1(tmp_path):
    r = _ler(tmp_path, "99")
    assert r.returncode == 1
    assert "minuta '99' não encontrada no acervo" in r.stderr


def test_ler_sem_argumento_lista_as_que_convocam_a_cadeira(tmp_path):
    r = _ler(tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("0041  Wiki: rumo e fronteira  aberta por produto")
    assert "convocada  seção: vazia" in r.stdout


def test_ler_sem_argumento_sem_convocacao_sai_1_com_motivo(tmp_path):
    r = _ler(tmp_path, PF_CADEIRA="seguranca")
    assert r.returncode == 1
    assert "nenhuma minuta aberta no acervo convoca 'seguranca'" in r.stderr


def test_acervo_indeterminavel_sai_5_e_nao_nega(tmp_path):
    r = _ler(tmp_path, "41", STUB_RC="5")
    assert r.returncode == 5, r.stderr
    assert "não encontrada" not in r.stderr


def test_escrever_poe_especie_antes_do_primeiro_titulo_de_secao():
    texto = (BIN / "_minuta" / "escrever").read_text()
    i_esp = texto.index('echo "Espécie: minuta"')
    i_sec = texto.index('echo "## Pergunta"')
    assert i_esp < i_sec
