# componente: componente:escrita
"""Testes herméticos de confinamento de caminho, edição parcial e IO atômico (story #4441, t2)."""
from __future__ import annotations

import errno
import fcntl
import os
import stat
import sys
import time
from pathlib import Path

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = HARNESS_ROOT / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from escrita.caminho import resolver_bancada  # noqa: E402
from escrita.edicao import aplicar_patch, aplicar_trecho  # noqa: E402
from escrita.io_atomico import (  # noqa: E402
    MODO_ARQ_COMUM,
    MODO_ARQ_EXEC,
    MODO_DIR_BANCADA,
    DestinoIO,
    executar_escrita_atomica,
    varrer_temporarios_orfaos,
)
from escrita.pedido import parsear_patch_estrito  # noqa: E402
from escrita.tipos import RecusaEscrita, TrocaTrecho  # noqa: E402


@pytest.mark.parametrize("numero", [errno.EACCES, errno.EPERM])
def test_sem_permissao_na_bancada_sai_4_com_sanear_na_cura(numero: int) -> None:
    """EACCES na bancada é permanente: sai 4 bancada-sem-permissao, nunca 3 com «repita»."""
    from escrita.io_atomico import _erro_os_antes_replace

    exc = PermissionError(numero, "Permission denied", ".pf-esc-x.tmp")
    erro = _erro_os_antes_replace("a.txt", exc).erros[0]
    assert erro.saida == 4
    assert erro.codigo == "bancada-sem-permissao"
    assert erro.proximo == "repo sanear"
    assert "repo sanear" in erro.cura


def _criar_worktree_simulada(
    raiz: Path, repo: str, cadeira: str, chave: str
) -> Path:
    clone_base = raiz / repo
    admin = clone_base / ".git" / "worktrees" / f"{cadeira}-{chave}"
    admin.mkdir(parents=True, exist_ok=True)
    wt = raiz / "wt" / repo / cadeira / chave
    wt.mkdir(parents=True, exist_ok=True)
    arq_git = wt / ".git"
    arq_git.write_text(f"gitdir: {admin}\n", encoding="utf-8")
    (admin / "gitdir").write_text(f"{arq_git}\n", encoding="utf-8")
    return wt


def test_confinamento_caminho_e_selecao_de_bancada(tmp_path: Path) -> None:
    _criar_worktree_simulada(tmp_path, "platafirma-harness", "engenharia", "4441-ato-escrever")
    conf = resolver_bancada(
        "platafirma-harness:lib/escrita/novo.py", "engenharia", tmp_path
    )
    assert conf.repo == "platafirma-harness"
    assert conf.cadeira == "engenharia"
    assert conf.chave_bancada == "4441-ato-escrever"
    assert conf.componentes_alvo == ("lib", "escrita", "novo.py")

    # Segmentos proibidos e .git
    for invalido, cod_esp in (
        ("platafirma-harness:../fora.py", "fora-de-morada"),
        ("platafirma-harness:lib/./x.py", "fora-de-morada"),
        ("platafirma-harness:/abs.py", "fora-de-morada"),
        ("platafirma-harness:.git/config", "superficie-vedada"),
    ):
        with pytest.raises(RecusaEscrita) as exc:
            resolver_bancada(invalido, "engenharia", tmp_path)
        assert exc.value.saida == 4
        assert exc.value.primeiro.codigo == cod_esp

    # Clone-base recusado para cadeira sem bancada
    with pytest.raises(RecusaEscrita) as exc_clone:
        resolver_bancada("platafirma-harness:lib/x.py", "ti", tmp_path)
    assert exc_clone.value.saida == 2
    assert exc_clone.value.primeiro.codigo == "clone-base-recusado"

    # Sem bancada e sem clone-base
    with pytest.raises(RecusaEscrita) as exc_sem:
        resolver_bancada("platafirma-inexistente:lib/x.py", "engenharia", tmp_path)
    assert exc_sem.value.saida == 2
    assert exc_sem.value.primeiro.codigo == "sem-bancada"

    # Múltiplas bancadas sem @chave -> ambígua; com @chave -> resolve
    _criar_worktree_simulada(tmp_path, "platafirma-harness", "engenharia", "9999-outra")
    with pytest.raises(RecusaEscrita) as exc_amb:
        resolver_bancada("platafirma-harness:lib/x.py", "engenharia", tmp_path)
    assert exc_amb.value.saida == 2
    assert exc_amb.value.primeiro.codigo == "bancada-ambigua"

    conf2 = resolver_bancada(
        "platafirma-harness@9999-outra:lib/x.py", "engenharia", tmp_path
    )
    assert conf2.chave_bancada == "9999-outra"


def test_edicao_trecho_exato_linhas_inteiras_e_recusas() -> None:
    # Literal exato e todos=True
    res = aplicar_trecho("a = 1\nb = 1\n", TrocaTrecho(antes="= 1", depois="= 2", todos=True))
    assert res.texto == "a = 2\nb = 2\n"
    assert res.ocorrencias == 2

    with pytest.raises(RecusaEscrita) as exc_amb:
        aplicar_trecho("a = 1\nb = 1\n", TrocaTrecho(antes="= 1", depois="= 2", todos=False))
    assert exc_amb.value.saida == 2
    assert exc_amb.value.primeiro.codigo == "trecho-ambiguo"

    # Linhas inteiras com reindentação e preservação de CRLF
    original = "def f():\r\n    x = 1\r\n    y = 2\r\n"
    res_ind = aplicar_trecho(
        original, TrocaTrecho(antes="x = 1\ny = 2", depois="x = 10\ny = 20")
    )
    assert res_ind.texto == "def f():\r\n    x = 10\r\n    y = 20\r\n"
    assert res_ind.ocorrencias == 1

    # Nunca casa prefixo/sufixo parcial em comentário ou token
    with pytest.raises(RecusaEscrita) as exc_parcial:
        aplicar_trecho("# x = 1\ny = 200\n", TrocaTrecho(antes="x = 1\ny = 2", depois="z = 3"))
    assert exc_parcial.value.saida == 2
    assert exc_parcial.value.primeiro.codigo == "trecho-nao-encontrado"


def test_edicao_patch_estrito_e_recusas() -> None:
    atual = "linha 1\nlinha 2\nlinha 3\n"
    diff_ok = (
        "--- a/lib/mod.py\n"
        "+++ b/lib/mod.py\n"
        "@@ -1,3 +1,3 @@\n"
        " linha 1\n"
        "-linha 2\n"
        "+linha DOIS\n"
        " linha 3\n"
    )
    patch = parsear_patch_estrito(diff_ok)
    res = aplicar_patch(atual, "platafirma-harness:lib/mod.py", patch)
    assert res.texto == "linha 1\nlinha DOIS\nlinha 3\n"
    assert res.hunks_aplicados == 1

    # Cabeçalho de outro caminho -> patch-multi-alvo
    with pytest.raises(RecusaEscrita) as exc_alvo:
        aplicar_patch(atual, "platafirma-harness:lib/outro.py", patch)
    assert exc_alvo.value.saida == 2
    assert exc_alvo.value.primeiro.codigo == "patch-multi-alvo"

    # Deslocamento de 1 linha sem busca aproximada -> hunk-nao-casa
    diff_deslocado = (
        "--- a/lib/mod.py\n"
        "+++ b/lib/mod.py\n"
        "@@ -2,3 +2,3 @@\n"
        " linha 1\n"
        "-linha 2\n"
        "+linha DOIS\n"
        " linha 3\n"
    )
    with pytest.raises(RecusaEscrita) as exc_hunk:
        aplicar_patch(atual, "platafirma-harness:lib/mod.py", parsear_patch_estrito(diff_deslocado))
    assert exc_hunk.value.saida == 2
    assert exc_hunk.value.primeiro.codigo == "hunk-nao-casa"

    # Patch sem efeito -> patch-sem-efeito
    diff_noop = (
        "--- a/lib/mod.py\n"
        "+++ b/lib/mod.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-linha 1\n"
        "+linha 1\n"
        " linha 2\n"
    )
    with pytest.raises(RecusaEscrita) as exc_noop:
        aplicar_patch(atual, "platafirma-harness:lib/mod.py", parsear_patch_estrito(diff_noop))
    assert exc_noop.value.saida == 2
    assert exc_noop.value.primeiro.codigo == "patch-sem-efeito"


def test_io_atomico_modos_sob_umask_0077_exec_e_idempotencia(tmp_path: Path) -> None:
    wt = _criar_worktree_simulada(tmp_path, "platafirma-harness", "engenharia", "4441-ato-escrever")
    estado = tmp_path / "estado"
    antiga = os.umask(0o077)
    try:
        dest = DestinoIO(
            raiz_wt=tmp_path / "wt",
            componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
            componentes_alvo=("sub", "aninhado", "mod.py"),
            estado_dir=estado,
        )
        res1 = executar_escrita_atomica(dest, lambda _atual: (b"x = 1\n", False))
        assert res1.alterou is True and res1.ja_gravado is False and res1.substituiu is False
        arq = wt / "sub" / "aninhado" / "mod.py"
        assert stat.S_IMODE(arq.stat().st_mode) == MODO_ARQ_COMUM
        assert stat.S_IMODE((wt / "sub").stat().st_mode) == MODO_DIR_BANCADA
        assert stat.S_IMODE((wt / "sub" / "aninhado").stat().st_mode) == MODO_DIR_BANCADA

        # Repetição de conteúdo igual não reescreve o inode
        ino_antes = arq.stat().st_ino
        res2 = executar_escrita_atomica(dest, lambda _atual: (b"x = 1\n", False))
        assert res2.alterou is False and res2.ja_gravado is True
        assert arq.stat().st_ino == ino_antes

        # Executável novo recebe 0o775 e troca posterior preserva o bit executável
        dest_bin = DestinoIO(
            raiz_wt=tmp_path / "wt",
            componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
            componentes_alvo=("bin", "ferramenta"),
            estado_dir=estado,
        )
        executar_escrita_atomica(dest_bin, lambda _atual: (b"#!/bin/sh\necho 1\n", True))
        arq_bin = wt / "bin" / "ferramenta"
        assert stat.S_IMODE(arq_bin.stat().st_mode) == MODO_ARQ_EXEC
        executar_escrita_atomica(dest_bin, lambda _atual: (b"#!/bin/sh\necho 2\n", False))
        assert stat.S_IMODE(arq_bin.stat().st_mode) == MODO_ARQ_EXEC
    finally:
        os.umask(antiga)


def test_io_atomico_recusa_symlink_fifo_e_hardlink(tmp_path: Path) -> None:
    wt = _criar_worktree_simulada(tmp_path, "platafirma-harness", "engenharia", "4441-ato-escrever")
    estado = tmp_path / "estado"
    fora = tmp_path / "fora.txt"
    fora.write_text("segredo\n", encoding="utf-8")

    # Symlink no alvo
    (wt / "link.txt").symlink_to(fora)
    dest_link = DestinoIO(
        raiz_wt=tmp_path / "wt",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("link.txt",),
        estado_dir=estado,
    )
    with pytest.raises(RecusaEscrita) as exc_link:
        executar_escrita_atomica(dest_link, lambda _a: (b"novo\n", False))
    assert exc_link.value.saida == 4
    assert exc_link.value.primeiro.codigo == "caminho-com-atalho"

    # Symlink em diretório intermediário
    dir_fora = tmp_path / "dir_fora"
    dir_fora.mkdir()
    (wt / "dir_link").symlink_to(dir_fora)
    dest_dir_link = DestinoIO(
        raiz_wt=tmp_path / "wt",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("dir_link", "arq.txt"),
        estado_dir=estado,
    )
    with pytest.raises(RecusaEscrita) as exc_dlink:
        executar_escrita_atomica(dest_dir_link, lambda _a: (b"novo\n", False))
    assert exc_dlink.value.saida == 4
    assert exc_dlink.value.primeiro.codigo == "caminho-com-atalho"

    # FIFO
    os.mkfifo(wt / "canal.fifo")
    dest_fifo = DestinoIO(
        raiz_wt=tmp_path / "wt",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("canal.fifo",),
        estado_dir=estado,
    )
    with pytest.raises(RecusaEscrita) as exc_fifo:
        executar_escrita_atomica(dest_fifo, lambda _a: (b"novo\n", False))
    assert exc_fifo.value.saida == 4
    assert exc_fifo.value.primeiro.codigo == "superficie-vedada"

    # Hardlink (st_nlink == 2)
    orig = wt / "orig.txt"
    orig.write_text("v1\n", encoding="utf-8")
    os.link(orig, wt / "duplicado.txt")
    dest_hl = DestinoIO(
        raiz_wt=tmp_path / "wt",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("orig.txt",),
        estado_dir=estado,
    )
    with pytest.raises(RecusaEscrita) as exc_hl:
        executar_escrita_atomica(dest_hl, lambda _a: (b"v2\n", False))
    assert exc_hl.value.saida == 4
    assert exc_hl.value.primeiro.codigo == "superficie-vedada"


def test_trava_ocupada_sai_3_e_varredura_de_orfaos(tmp_path: Path) -> None:
    wt = _criar_worktree_simulada(tmp_path, "platafirma-harness", "engenharia", "4441-ato-escrever")
    estado = tmp_path / "estado"
    estado.mkdir()
    st = wt.stat()
    arq_trava = estado / f"lock-{st.st_dev}-{st.st_ino}.flock"
    fd = os.open(str(arq_trava), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        dest = DestinoIO(
            raiz_wt=tmp_path / "wt",
            componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
            componentes_alvo=("arq.txt",),
            estado_dir=estado,
            prazo_ns=time.monotonic_ns() + 60_000_000,
            passo_ms=10,
        )
        with pytest.raises(RecusaEscrita) as exc:
            executar_escrita_atomica(dest, lambda _a: (b"oi\n", False))
        assert exc.value.saida == 3
        assert exc.value.primeiro.codigo == "bancada-ocupada"
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    # Varredura remove apenas .pf-esc-*.tmp mais velhos que o teto
    velho = wt / ".pf-esc-antigo.tmp"
    novo = wt / ".pf-esc-recente.tmp"
    velho.write_text("x", encoding="utf-8")
    novo.write_text("y", encoding="utf-8")
    os.utime(velho, (time.time() - 120, time.time() - 120))
    removidos = varrer_temporarios_orfaos(wt, estado, idade_min_s=30)
    assert removidos == [".pf-esc-antigo.tmp"]
    assert not velho.exists()
    assert novo.exists()


def test_io_atomico_endurecimentos_ti(tmp_path: Path) -> None:
    # raiz_wt ausente -> RecusaEscrita saída 3 (não vaza FileNotFoundError)
    dest_ausente = DestinoIO(
        raiz_wt=tmp_path / "wt-nao-existe",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("a.txt",),
        estado_dir=tmp_path / "estado",
    )
    with pytest.raises(RecusaEscrita) as exc_aus:
        executar_escrita_atomica(dest_ausente, lambda _a: (b"x\n", False))
    assert exc_aus.value.saida == 3
    assert exc_aus.value.primeiro.codigo == "morada-sem-resposta"

    # Alvo existente acima do teto de leitura -> saída 2 tamanho-excedido
    wt = _criar_worktree_simulada(tmp_path, "platafirma-harness", "engenharia", "4441-ato-escrever")
    (wt / "grande.txt").write_bytes(b"a" * 200)
    dest_teto = DestinoIO(
        raiz_wt=tmp_path / "wt",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("grande.txt",),
        estado_dir=tmp_path / "estado",
        teto_leitura_bytes=100,
    )
    with pytest.raises(RecusaEscrita) as exc_teto:
        executar_escrita_atomica(dest_teto, lambda _a: (b"curto\n", False))
    assert exc_teto.value.saida == 2
    assert exc_teto.value.primeiro.codigo == "tamanho-excedido"

    # Prazo vencido depois da trava e antes de os.replace -> morada-sem-resposta (não bancada-ocupada)
    dest_prazo = DestinoIO(
        raiz_wt=tmp_path / "wt",
        componentes_bancada=("platafirma-harness", "engenharia", "4441-ato-escrever"),
        componentes_alvo=("prazo.txt",),
        estado_dir=tmp_path / "estado",
        prazo_ns=1,
    )
    with pytest.raises(RecusaEscrita) as exc_prazo:
        executar_escrita_atomica(dest_prazo, lambda _a: (b"ok\n", False))
    assert exc_prazo.value.saida == 3
    assert exc_prazo.value.primeiro.codigo == "morada-sem-resposta"
    assert not (wt / "prazo.txt").exists()

    # .git corrompido (bytes não-UTF-8) não vaza UnicodeDecodeError
    wt_corrompido = _criar_worktree_simulada(tmp_path, "repo-corrompido", "engenharia", "x")
    (wt_corrompido / ".git").write_bytes(b"\xff\xfe")
    with pytest.raises(RecusaEscrita) as exc_git:
        resolver_bancada("repo-corrompido@x:a.txt", "engenharia", tmp_path)
    assert exc_git.value.saida == 2
    assert exc_git.value.primeiro.codigo == "sem-bancada"
