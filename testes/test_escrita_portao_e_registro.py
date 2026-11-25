# componente: componente:escrita
"""Testes herméticos do portão, resolução e registro de operações (story #4441, t3)."""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = HARNESS_ROOT / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from escrita.edicao import aplicar_patch, aplicar_trecho  # noqa: E402
from escrita.pedido import gerar_uuidv7, parsear_pedido  # noqa: E402
from escrita.politica import carregar_politica  # noqa: E402
from escrita.portao import (  # noqa: E402
    ContextoAutorizacao,
    CredencialPar,
    SpecClasse,
    SpecVerbo,
    VistaAlcance,
    carregar_vista_alcance,
    decidir_portao,
)
from escrita.registro import (  # noqa: E402
    LinhaOperacao,
    RegistroOperacoes,
    hash_canonico_pedido,
)
from escrita.resolucao import (  # noqa: E402
    EstadoAlvo,
    normalizar_chave_casa,
    resolver_alvo,
    validar_precondicao_versao,
)
from escrita.tipos import (  # noqa: E402
    CAMPOS_ERRO,
    ContextoEscrita,
    RecusaEscrita,
    emitir_recusa,
)

CONFIG_PATH = HARNESS_ROOT / "registro" / "escrita.yaml"
PORTA_YAML = HARNESS_ROOT / "registro" / "porta.yaml"


def _emitir_json(recusa: RecusaEscrita) -> tuple[int, dict]:
    buf = io.StringIO()
    saida = emitir_recusa(recusa, fluxo=buf)
    linhas = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(linhas) == 1
    return saida, json.loads(linhas[-1])


def _cred_ok() -> CredencialPar:
    return CredencialPar(
        uid=1000,
        gid=1000,
        pid=4242,
        usuario="claudinho",
        grupos=frozenset({"claudinho", "platafirma-escrita"}),
    )


def _auth_padrao(
    *,
    raio_card: frozenset[tuple[str, str]] | None = None,
    autorizador=None,
    vista: VistaAlcance | None = None,
) -> ContextoAutorizacao:
    return ContextoAutorizacao(
        politica=carregar_politica(CONFIG_PATH),
        vista=carregar_vista_alcance(PORTA_YAML) if vista is None else vista,
        raio_card=raio_card,
        autorizador_sujeito=autorizador,
    )


def _pedido(
    verbo: str,
    argv: list[str],
    conteudo: bytes = b"conteudo\n",
    *,
    sujeito: str = "dono",
    cadeira: str = "engenharia",
) -> object:
    pol = carregar_politica(CONFIG_PATH)
    ctx = ContextoEscrita(verbo=verbo, cadeira=cadeira, sujeito=sujeito)
    return parsear_pedido(verbo, argv, conteudo, politica=pol, contexto=ctx)


def test_portao_recusa_conta_fora_do_grupo_e_identidade_e_cadeira() -> None:
    auth = _auth_padrao()
    ped = _pedido("repo", ["gravar", "componente", "platafirma-harness:lib/a.py"])

    cred_fora = CredencialPar(
        uid=2000, gid=2000, pid=99, usuario="pf-leitor", grupos=frozenset({"pf-leitor"})
    )
    with pytest.raises(RecusaEscrita) as exc_grupo:
        decidir_portao(ped, cred_fora, auth)
    assert exc_grupo.value.saida == 4
    assert exc_grupo.value.primeiro.codigo == "acesso-negado"

    ped_sem_suj = _pedido(
        "repo", ["gravar", "componente", "platafirma-harness:lib/a.py"], sujeito=""
    )
    with pytest.raises(RecusaEscrita) as exc_suj:
        decidir_portao(ped_sem_suj, _cred_ok(), auth)
    assert exc_suj.value.saida == 4
    assert exc_suj.value.primeiro.codigo == "acesso-negado"

    auth_nega = _auth_padrao(autorizador=lambda s, c, v, f: False)
    with pytest.raises(RecusaEscrita) as exc_pdp:
        decidir_portao(ped, _cred_ok(), auth_nega)
    assert exc_pdp.value.saida == 4
    assert exc_pdp.value.primeiro.codigo == "acesso-negado"


def test_portao_recusa_segredo_e_classe_fora_do_alcance_do_verbo() -> None:
    auth = _auth_padrao()

    ped_seg = _pedido("ontologia", ["criar", "segredo", "segredo:olaria-chave"])
    with pytest.raises(RecusaEscrita) as exc_seg:
        decidir_portao(ped_seg, _cred_ok(), auth)
    assert exc_seg.value.saida == 4
    assert exc_seg.value.primeiro.codigo == "segredo-recusado"

    # Classe fora do alcance do verbo sai 1 indicando o verbo dono
    ped_fora = _pedido("repo", ["gravar", "chapeu", "chapeu:back-end"])
    with pytest.raises(RecusaEscrita) as exc_fora:
        decidir_portao(ped_fora, _cred_ok(), auth)
    saida, payload = _emitir_json(exc_fora.value)
    assert saida == 1
    assert payload["erro"]["codigo"] == "classe-fora-do-verbo"
    assert "ontologia" in payload["erro"]["proximo"]
    assert tuple(payload["erro"].keys()) == CAMPOS_ERRO

    # Verbo que não aceita escrever sai 2 (ato-nao-aceito)
    ped_nao_aceita = _pedido("busca", ["criar", "chapeu", "chapeu:back-end"])
    with pytest.raises(RecusaEscrita) as exc_verbo:
        decidir_portao(ped_nao_aceita, _cred_ok(), auth)
    assert exc_verbo.value.saida == 2
    assert exc_verbo.value.primeiro.codigo == "ato-nao-aceito"
    assert "ontologia" in exc_verbo.value.primeiro.proximo


def test_portao_recusa_forma_fora_do_regime_e_forma_sem_morada() -> None:
    auth = _auth_padrao()

    ped_guardada = _pedido("ontologia", ["gravar", "chapeu", "chapeu:back-end"])
    with pytest.raises(RecusaEscrita) as exc_reg:
        decidir_portao(ped_guardada, _cred_ok(), auth)
    assert exc_reg.value.saida == 2
    assert exc_reg.value.primeiro.codigo == "forma-fora-do-regime"
    assert "criar" in exc_reg.value.primeiro.proximo

    ped_comum = _pedido("repo", ["criar", "componente", "platafirma-harness:lib/x.py"])
    with pytest.raises(RecusaEscrita) as exc_com:
        decidir_portao(ped_comum, _cred_ok(), auth)
    assert exc_com.value.saida == 2
    assert exc_com.value.primeiro.codigo == "forma-fora-do-regime"
    assert "gravar" in exc_com.value.primeiro.proximo

    ped_retirar = _pedido(
        "repo", ["retirar", "componente", "platafirma-harness:lib/x.py"], conteudo=b""
    )
    with pytest.raises(RecusaEscrita) as exc_sem_morada:
        decidir_portao(ped_retirar, _cred_ok(), auth)
    assert exc_sem_morada.value.saida == 2
    assert exc_sem_morada.value.primeiro.codigo == "forma-sem-morada"


def test_portao_bloqueia_superficie_vedada_e_caminho_protegido_fora_do_raio() -> None:
    auth_sem_raio = _auth_padrao()

    ped_git = _pedido("repo", ["gravar", "componente", "platafirma-harness:.git/config"])
    with pytest.raises(RecusaEscrita) as exc_git:
        decidir_portao(ped_git, _cred_ok(), auth_sem_raio)
    assert exc_git.value.saida == 4
    assert exc_git.value.primeiro.codigo == "superficie-vedada"

    ped_prot = _pedido(
        "repo", ["gravar", "componente", "platafirma-harness:lib/escrita/portao.py"]
    )
    with pytest.raises(RecusaEscrita) as exc_prot:
        decidir_portao(ped_prot, _cred_ok(), auth_sem_raio)
    assert exc_prot.value.saida == 4
    assert exc_prot.value.primeiro.codigo == "superficie-vedada"

    auth_com_raio = _auth_padrao(
        raio_card=frozenset({("platafirma-harness", "lib/escrita/portao.py")})
    )
    dec = decidir_portao(ped_prot, _cred_ok(), auth_com_raio)
    assert dec.classe == "componente"
    assert dec.morada == "git"


_CORPO_CARD = (
    "<p><strong>Referencial:</strong></p><ul><li>platafirma-core@acesso/ · só leitura</li></ul>"
    "<p><strong>Raio de ataque:</strong><br>platafirma-harness@lib/escrita/portao.py · muda: x<br>"
    "platafirma-harness@deploy-harness/ · muda: y</p>"
    "<p><strong>Comportamento esperado:</strong></p><ul><li>platafirma-harness@lib/leitura/x.py citado</li></ul>"
    "<p><strong>Raio emendado:</strong><br>- platafirma-harness@testes/test_x.py | [executor] prova</p>"
    "<p><strong>Riscos:</strong><br>platafirma-harness@registro/escrita.yaml citado</p>"
)


def _provedor(estado: str = "em-execucao", chamadas: list[str] | None = None):
    from escrita.portao import criar_provedor_raio

    def _http(url: str, _prazo: float) -> object:
        if chamadas is not None:
            chamadas.append(url)
        return {"id": 4441, "estado": estado, "descricao": _CORPO_CARD}

    return criar_provedor_raio("http://rast.local/api", cliente_http=_http)


def test_raio_sai_so_das_secoes_raio_de_ataque_e_raio_emendado() -> None:
    from escrita.portao import extrair_raio_do_corpo

    assert extrair_raio_do_corpo(_CORPO_CARD) == frozenset({
        ("platafirma-harness", "lib/escrita/portao.py"),
        ("platafirma-harness", "deploy-harness/"),
        ("platafirma-harness", "testes/test_x.py"),
    })


def test_portao_le_o_raio_do_card_da_bancada_no_rastreador() -> None:
    chamadas: list[str] = []
    base = _auth_padrao()
    auth = ContextoAutorizacao(
        politica=base.politica, vista=base.vista, provedor_raio=_provedor(chamadas=chamadas)
    )
    ped_no_raio = _pedido(
        "repo", ["gravar", "componente", "platafirma-harness@4441-raio-card:lib/escrita/portao.py"]
    )
    assert decidir_portao(ped_no_raio, _cred_ok(), auth).morada == "git"
    assert chamadas == ["http://rast.local/api/itens/4441"]

    # Citado fora do raio (Comportamento esperado, Riscos) não abre o caminho protegido
    for rel in ("lib/leitura/x.py", "registro/escrita.yaml"):
        ped = _pedido("repo", ["gravar", "componente", f"platafirma-harness@4441-raio-card:{rel}"])
        with pytest.raises(RecusaEscrita) as exc:
            decidir_portao(ped, _cred_ok(), auth)
        assert exc.value.saida == 4
        assert exc.value.primeiro.codigo == "superficie-vedada"

    # Sem bancada na chave não há card de onde ler o raio
    ped_sem_bancada = _pedido("repo", ["gravar", "componente", "platafirma-harness:lib/escrita/portao.py"])
    with pytest.raises(RecusaEscrita) as exc_sem:
        decidir_portao(ped_sem_bancada, _cred_ok(), auth)
    assert exc_sem.value.saida == 4


def test_portao_nega_raio_de_card_fora_de_execucao_e_sai_3_sem_rastreador() -> None:
    from escrita.portao import criar_provedor_raio

    base = _auth_padrao()
    ped = _pedido(
        "repo", ["gravar", "componente", "platafirma-harness@4441-raio-card:lib/escrita/portao.py"]
    )
    auth_fechado = ContextoAutorizacao(
        politica=base.politica, vista=base.vista, provedor_raio=_provedor(estado="concluida")
    )
    with pytest.raises(RecusaEscrita) as exc_fechado:
        decidir_portao(ped, _cred_ok(), auth_fechado)
    assert exc_fechado.value.saida == 4

    def _fora(_url: str, _prazo: float) -> object:
        raise OSError("connection refused")

    auth_fora = ContextoAutorizacao(
        politica=base.politica,
        vista=base.vista,
        provedor_raio=criar_provedor_raio("http://rast.local/api", cliente_http=_fora),
    )
    with pytest.raises(RecusaEscrita) as exc_fora:
        decidir_portao(ped, _cred_ok(), auth_fora)
    assert exc_fora.value.saida == 3
    assert exc_fora.value.primeiro.codigo == "morada-sem-resposta"
    assert exc_fora.value.primeiro.onde == "bancada"


def test_portao_roda_antes_da_resolucao_sem_consultar_alvo() -> None:
    consultas = 0

    def consultar_morada(_chave: str) -> EstadoAlvo:
        nonlocal consultas
        consultas += 1
        return EstadoAlvo(existe=True, versao="v1")

    auth = _auth_padrao(autorizador=lambda s, c, v, f: False)
    ped = _pedido("ontologia", ["criar", "chapeu", "chapeu:novo"])
    with pytest.raises(RecusaEscrita) as exc:
        dec = decidir_portao(ped, _cred_ok(), auth)
        resolver_alvo(ped, dec, auth.vista)
        consultar_morada(ped.chave)
    assert exc.value.saida == 4
    assert consultas == 0


def test_resolucao_normalizacao_documento_ambiguo_e_bancada(tmp_path: Path) -> None:
    assert normalizar_chave_casa("sessao") == "shape:sessao"
    assert normalizar_chave_casa("sessao:") == "shape:sessao"
    assert normalizar_chave_casa("chapeu:back-end") == "chapeu:back-end"

    vista_doc = VistaAlcance(
        verbos={
            "arquitetura": SpecVerbo(
                verbo="arquitetura",
                aceita_escrever=True,
                classes=frozenset({"ato"}),
            )
        },
        classes={
            "ato": SpecClasse(
                classe="ato",
                regime="comum",
                morada="git",
                verbo_dono="arquitetura",
                documentos=("golden", "referencia"),
                formas_suportadas=frozenset({"gravar"}),
                moldes=(
                    ("golden", "instancias/ato/<slug>.md"),
                    ("referencia", "referencias/instancias/ato/<slug>.md"),
                ),
            )
        },
    )
    auth_doc = _auth_padrao(vista=vista_doc)
    ped_amb = _pedido("arquitetura", ["gravar", "ato", "ato:escrever"])
    dec_amb = decidir_portao(ped_amb, _cred_ok(), auth_doc)
    with pytest.raises(RecusaEscrita) as exc_amb:
        resolver_alvo(ped_amb, dec_amb, vista_doc)
    assert exc_amb.value.saida == 2
    assert exc_amb.value.primeiro.codigo == "documento-ambiguo"

    ped_ref = _pedido(
        "arquitetura", ["gravar", "ato", "ato:escrever", "--documento", "referencia"]
    )
    dec_ref = decidir_portao(ped_ref, _cred_ok(), auth_doc)
    res_ref = resolver_alvo(ped_ref, dec_ref, vista_doc)
    assert res_ref.alvo.endereco == "referencias/instancias/ato/escrever.md"
    assert res_ref.alvo.documento == "referencia"

    # Resolução real de componente na bancada worktree
    clone = tmp_path / "platafirma-harness"
    clone.mkdir()
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "user.name", "t"], check=True)
    (clone / "README.md").write_text("ok\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(clone), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(clone), "commit", "-q", "-m", "init"], check=True)
    wt = tmp_path / "wt" / "platafirma-harness" / "engenharia" / "4441"
    wt.parent.mkdir(parents=True)
    subprocess.run(
        ["git", "-C", str(clone), "worktree", "add", "-q", "-b", "f/4441", str(wt)],
        check=True,
    )

    auth = _auth_padrao()
    ped_comp = _pedido("repo", ["gravar", "componente", "platafirma-harness:lib/novo.py"])
    dec_comp = decidir_portao(ped_comp, _cred_ok(), auth)
    res_comp = resolver_alvo(ped_comp, dec_comp, auth.vista, raiz_bancadas=tmp_path)
    assert res_comp.bancada is not None
    assert res_comp.alvo.repo == "platafirma-harness"
    assert res_comp.alvo.caminho_relativo == "lib/novo.py"


def test_precondicoes_alvo_inexistente_e_versao_divergente() -> None:
    auth = _auth_padrao()

    # 1. trocar sobre ficha inexistente sai 1 (alvo-inexistente)
    ped_trocar = _pedido(
        "ontologia", ["trocar", "chapeu", "chapeu:fantasma", "019360a0-8b12-7c00-9a11-001122334455"]
    )
    dec_trocar = decidir_portao(ped_trocar, _cred_ok(), auth)
    alvo_trocar = resolver_alvo(ped_trocar, dec_trocar, auth.vista).alvo
    with pytest.raises(RecusaEscrita) as exc_inex:
        validar_precondicao_versao(ped_trocar, alvo_trocar, EstadoAlvo(existe=False))
    saida, payload = _emitir_json(exc_inex.value)
    assert saida == 1
    assert payload["erro"]["codigo"] == "alvo-inexistente"
    assert tuple(payload["erro"].keys()) == CAMPOS_ERRO

    # 2. gravar com --formato trecho em arquivo inexistente sai 1 (alvo-inexistente)
    ped_trecho_inex = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/ausente.py", "--formato", "trecho"],
        conteudo=json.dumps({"antes": "a", "depois": "b"}).encode(),
    )
    dec_ti = decidir_portao(ped_trecho_inex, _cred_ok(), auth)
    alvo_ti = resolver_alvo(ped_trecho_inex, dec_ti, auth.vista).alvo
    with pytest.raises(RecusaEscrita) as exc_ti:
        validar_precondicao_versao(ped_trecho_inex, alvo_ti, EstadoAlvo(existe=False))
    assert exc_ti.value.saida == 1
    assert exc_ti.value.primeiro.codigo == "alvo-inexistente"

    # 3. versão divergente em componente (git) sai 2
    ped_div = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/a.py", "111111111111"],
    )
    dec_div = decidir_portao(ped_div, _cred_ok(), auth)
    alvo_div = resolver_alvo(ped_div, dec_div, auth.vista).alvo
    with pytest.raises(RecusaEscrita) as exc_div:
        validar_precondicao_versao(
            ped_div,
            alvo_div,
            EstadoAlvo(existe=True, versao="222222222222", versao_completa="2" * 40),
        )
    saida_div, payload_div = _emitir_json(exc_div.value)
    assert saida_div == 2
    assert payload_div["erro"]["codigo"] == "versao-divergente"
    assert "ler" in payload_div["erro"]["proximo"]

    # 4. prefixo de 12 dígitos hex válido no git passa
    validar_precondicao_versao(
        ped_div,
        alvo_div,
        EstadoAlvo(existe=True, versao="111111111111", versao_completa="111111111111" + "a" * 28),
    )

    # 5. criar sobre chave já existente sai 2 (ja-existe)
    ped_criar = _pedido("ontologia", ["criar", "chapeu", "chapeu:back-end"])
    dec_criar = decidir_portao(ped_criar, _cred_ok(), auth)
    alvo_criar = resolver_alvo(ped_criar, dec_criar, auth.vista).alvo
    with pytest.raises(RecusaEscrita) as exc_ja:
        validar_precondicao_versao(
            ped_criar, alvo_criar, EstadoAlvo(existe=True, versao="019360a0-8b12-7c00-9a11-001122334455")
        )
    assert exc_ja.value.saida == 2
    assert exc_ja.value.primeiro.codigo == "ja-existe"


def test_trecho_ambiguo_e_patch_com_cabecalho_de_outro_caminho_saem_2() -> None:
    # Trecho ambíguo sai 2 com JSON de 6 campos
    ped_amb = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/a.py", "--formato", "trecho"],
        conteudo=json.dumps({"antes": "valor = 1", "depois": "valor = 2"}).encode(),
    )
    assert ped_amb.trecho is not None
    with pytest.raises(RecusaEscrita) as exc_amb:
        aplicar_trecho("valor = 1\noutro = 0\nvalor = 1\n", ped_amb.trecho)
    saida_amb, payload_amb = _emitir_json(exc_amb.value)
    assert saida_amb == 2
    assert payload_amb["erro"]["codigo"] == "trecho-ambiguo"
    assert tuple(payload_amb["erro"].keys()) == CAMPOS_ERRO

    # Patch com cabeçalho de outro caminho sai 2 (patch-multi-alvo)
    diff_outro = (
        "--- a/lib/outro.py\n"
        "+++ b/lib/outro.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-x = 1\n"
        "+x = 2\n"
    ).encode()
    ped_patch = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/alvo.py", "--formato", "patch"],
        conteudo=diff_outro,
    )
    assert ped_patch.patch is not None
    with pytest.raises(RecusaEscrita) as exc_patch:
        aplicar_patch("x = 1\n", ped_patch.chave, ped_patch.patch)
    saida_p, payload_p = _emitir_json(exc_patch.value)
    assert saida_p == 2
    assert payload_p["erro"]["codigo"] == "patch-multi-alvo"
    assert tuple(payload_p["erro"].keys()) == CAMPOS_ERRO


def test_registro_append_only_repeticao_idempotente_e_conflitos(tmp_path: Path) -> None:
    reg = RegistroOperacoes(tmp_path / "estado" / "operacoes.jsonl")
    pid = gerar_uuidv7()
    ped1 = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/a.py", "--pedido", pid],
        conteudo=b"print('ola')\n",
        sujeito="dono",
        cadeira="engenharia",
    )
    sha1 = hash_canonico_pedido(ped1, classe="componente")
    agora = 1_700_000_000.0

    linha = LinhaOperacao(
        pedido=pid,
        sha256_pedido=sha1,
        conta_par="claudinho",
        uid_par=1000,
        gid_par=1000,
        pid_par=4242,
        sujeito="dono",
        verbo="repo",
        cadeira="engenharia",
        forma="gravar",
        classe="componente",
        chave=ped1.chave,
        morada="git",
        endereco="wt/platafirma-harness/engenharia/4441/lib/a.py",
        repo="platafirma-harness",
        caminho_relativo="lib/a.py",
        versao_lida=None,
        versao_gravada="abcdef123456",
        bytes=13,
        exit_code=0,
        release="rel-20261125",
        timestamp=agora,
    )
    reg.registrar(linha)

    # Busca por pedido e repetição idêntica dentro da retenção
    assert reg.buscar_por_pedido(pid) == linha
    rep = reg.consultar_repeticao(ped1, classe="componente", retencao_s=86400, agora=agora + 10)
    assert rep == linha

    # Repetição com sujeito diferente -> saída 2 pedido-com-conteudo-diferente
    ped_suj = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/a.py", "--pedido", pid],
        conteudo=b"print('ola')\n",
        sujeito="outro-sujeito",
        cadeira="engenharia",
    )
    with pytest.raises(RecusaEscrita) as exc_suj:
        reg.consultar_repeticao(ped_suj, classe="componente", retencao_s=86400, agora=agora + 10)
    assert exc_suj.value.saida == 2
    assert exc_suj.value.primeiro.codigo == "pedido-com-conteudo-diferente"

    # Repetição com alvo diferente -> saída 2 pedido-com-conteudo-diferente
    ped_alvo = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/b.py", "--pedido", pid],
        conteudo=b"print('ola')\n",
        sujeito="dono",
        cadeira="engenharia",
    )
    with pytest.raises(RecusaEscrita) as exc_alvo:
        reg.consultar_repeticao(ped_alvo, classe="componente", retencao_s=86400, agora=agora + 10)
    assert exc_alvo.value.saida == 2
    assert exc_alvo.value.primeiro.codigo == "pedido-com-conteudo-diferente"

    # Repetição com conteúdo diferente -> saída 2 pedido-com-conteudo-diferente
    ped_cont = _pedido(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/a.py", "--pedido", pid],
        conteudo=b"print('diferente')\n",
        sujeito="dono",
        cadeira="engenharia",
    )
    with pytest.raises(RecusaEscrita) as exc_cont:
        reg.consultar_repeticao(ped_cont, classe="componente", retencao_s=86400, agora=agora + 10)
    assert exc_cont.value.saida == 2
    assert exc_cont.value.primeiro.codigo == "pedido-com-conteudo-diferente"

    # Fora da janela de retenção não dispara conflito nem repetição
    assert reg.consultar_repeticao(
        ped_cont, classe="componente", retencao_s=86400, agora=agora + 90_000
    ) is None


def test_registro_recusa_ensaio_e_lista_arquivos_para_commit(tmp_path: Path) -> None:
    reg = RegistroOperacoes(tmp_path / "operacoes.jsonl")
    linha_ensaio = LinhaOperacao(
        pedido=gerar_uuidv7(),
        sha256_pedido="0" * 64,
        conta_par="claudinho",
        uid_par=1000,
        gid_par=1000,
        pid_par=1,
        sujeito="dono",
        verbo="ontologia",
        cadeira="engenharia",
        forma="ensaiar",
        classe="chapeu",
        chave="chapeu:back-end",
        morada="banco",
        endereco="chapeu:back-end",
        versao_lida=None,
        versao_gravada=None,
        bytes=10,
        exit_code=0,
        release="rel-1",
        timestamp=100.0,
    )
    with pytest.raises(ValueError):
        reg.registrar(linha_ensaio)

    for idx, (rel, morada, rc, cadeira, ts) in enumerate(
        [
            ("lib/a.py", "git", 0, "engenharia", 100.0),
            ("lib/b.py", "git", 0, "engenharia", 110.0),
            ("lib/a.py", "git", 0, "engenharia", 120.0),
            ("lib/falha.py", "git", 2, "engenharia", 130.0),
            ("lib/outra.py", "git", 0, "seguranca", 140.0),
            (None, "banco", 0, "engenharia", 150.0),
        ]
    ):
        reg.registrar(
            LinhaOperacao(
                pedido=f"019360a0-8b12-7c00-9a11-00112233440{idx}",
                sha256_pedido=str(idx) * 64,
                conta_par="claudinho",
                uid_par=1000,
                gid_par=1000,
                pid_par=10,
                sujeito="dono",
                verbo="repo" if morada == "git" else "ontologia",
                cadeira=cadeira,
                forma="gravar" if morada == "git" else "criar",
                classe="componente" if morada == "git" else "chapeu",
                chave=f"platafirma-harness:{rel}" if rel else "chapeu:x",
                morada=morada,
                endereco=rel or "chapeu:x",
                repo="platafirma-harness" if morada == "git" else None,
                caminho_relativo=rel,
                versao_lida=None,
                versao_gravada="abc123456789",
                bytes=5,
                exit_code=rc,
                release="rel-1",
                timestamp=ts,
            )
        )

    assert reg.arquivos_gravados_na_bancada("platafirma-harness", "engenharia") == [
        "lib/a.py",
        "lib/b.py",
    ]
    assert reg.arquivos_gravados_na_bancada("platafirma-harness", "engenharia", desde=115.0) == [
        "lib/a.py",
    ]
