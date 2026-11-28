# componente: componente:verificador
# verifica: ato:verificar
"""test_contrato_verificar — contrato do ato verificar na camada comum (card #4454).

Cobre em memória (sem depender de banco, serviço ou host):
- conforme, divergente e inconclusivo na saída 0
- componente conforme contra gabarito:antipadroes-de-codigo em nome do ops com --json
- fixture com teste fora da lista de portão (T11) divergente com apontamento estruturado
- ficha de teste verde conforme no executor de testes
- múltiplos alvos sob um único retrato de leitura
- concatenação de gabaritos compatíveis
- item de aviso sem mudar o veredito
- modo JSON com versao_contrato, veredito, itens e apontamentos
- saídas 1, 2, 3 e 5 com recusa de seis campos em stderr
- chamada com dois testes delegada à suíte de testes devolvendo o laudo
- recusa de formas ou serviços distintos na saída 2
"""
from __future__ import annotations

import io
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[2]
for _pasta in (HARNESS_ROOT / "lib", HARNESS_ROOT / "bin"):
    if str(_pasta) not in sys.path:
        sys.path.insert(0, str(_pasta))

from _lint.resultado import Apontamento as ApontamentoBruto  # noqa: E402
from _lint.servico import AlvoLint, ErroServicoLint, VereditoLint, julgar as julgar_lint  # noqa: E402
from leitura.recusa import CAMPOS as CAMPOS_RECUSA  # noqa: E402
from suite import OpcoesExecucaoTeste, julgar_laudo  # noqa: E402
from suite.esteira import DubleExecutorIsolado  # noqa: E402
from verificador import (  # noqa: E402
    VERSAO_CONTRATO,
    AlvoVerificado,
    AmbienteVerificacao,
    Apontamento,
    ReguaFicha,
    VereditoEmitido,
    VereditoItem,
    VistaVerificar,
    executar,
)
from verificador.tipos import MOTOR_SUITE_TESTES, SERVICO_EXECUTOR_TESTES, SERVICO_LINT  # noqa: E402


class DubleFichario:
    """Fichário em memória para provar o contrato sem abrir banco casa."""

    def __init__(
        self,
        *,
        reguas: dict[str, ReguaFicha] | None = None,
        alvos: dict[str, AlvoVerificado] | None = None,
        padroes: dict[str, str] | None = None,
    ) -> None:
        self._reguas = dict(reguas or {})
        self._alvos = dict(alvos or {})
        self._padroes = dict(padroes or {})
        self.leituras_regua: list[str] = []
        self.leituras_alvo: list[str] = []

    def ler_regua(self, chave: str) -> ReguaFicha | None:
        self.leituras_regua.append(chave)
        return self._reguas.get(chave)

    def regua_padrao(self, classe: str) -> str | None:
        return self._padroes.get(classe)

    def ler_alvo(self, chave: str) -> AlvoVerificado | None:
        self.leituras_alvo.append(chave)
        return self._alvos.get(chave)

    def linhagem_compativel(self, classe_alvo: str, sobre: Sequence[str]) -> bool:
        norm = classe_alvo.removeprefix("shape:")
        return any(s.removeprefix("shape:") == norm for s in sobre)


class DubleDelegadorSuite:
    """Dublê da interface de delegação à suíte (que a #4455 liga ao ato despachar)."""

    def __init__(self, executor_isolado: Any) -> None:
        self._executor = executor_isolado
        self.chamadas: list[tuple[tuple[str, ...], Path, str]] = []

    def despachar_suite(
        self,
        chaves_fichas: Sequence[str],
        arvore: Path,
        *,
        alvo: str,
        prazo_s: float,
    ) -> VereditoEmitido:
        self.chamadas.append((tuple(chaves_fichas), arvore, alvo))
        laudo = julgar_laudo(
            chaves_fichas,
            arvore,
            opcoes=OpcoesExecucaoTeste(
                alvo=alvo,
                executor_isolado=self._executor,
                prazo_s=prazo_s,
                ficha_confirmada=True,
            ),
        )
        itens = tuple(
            VereditoItem(
                alvo=f"{v.alvo}::{v.quesito}",
                resultado=v.resultado,
                constatacao=v.constatacao,
                apontamentos=tuple(
                    Apontamento(
                        item=a.item,
                        alvo=a.alvo,
                        lugar=a.lugar,
                        exigencia=a.exigencia,
                        severidade=a.severidade,
                        cura=a.cura,
                    )
                    for a in v.apontamentos
                ),
                modo=v.modo,
                quesito=v.quesito,
                motor=v.motor,
            )
            for v in laudo.vereditos
        )
        apontamentos = tuple(a for item in itens for a in item.apontamentos)
        return VereditoEmitido(
            versao_contrato=VERSAO_CONTRATO,
            resultado=laudo.resultado,
            constatacao=laudo.constatacao,
            modo="enquadrou",
            quesito=tuple(chaves_fichas),
            chave=f"{alvo}|{MOTOR_SUITE_TESTES}@{laudo.versao_motor}|{'+'.join(chaves_fichas)}|casa:harness",
            motor=laudo.motor,
            itens=itens,
            apontamentos=apontamentos,
        )


def _vista_padrao() -> VistaVerificar:
    return VistaVerificar(
        verbos_aceitam=frozenset({"casa", "ops"}),
        alcance_por_verbo={
            "casa": frozenset({"politica", "gabarito", "figura", "verificacao"}),
            "ops": frozenset({"componente", "repositorio"}),
        },
    )


def _reguas_padrao() -> dict[str, ReguaFicha]:
    return {
        "gabarito:antipadroes-de-codigo": ReguaFicha(
            chave="gabarito:antipadroes-de-codigo",
            forma="gabarito",
            sobre=("shape:componente", "shape:repositorio"),
            contra_o_que="construcao",
            garantido_por=SERVICO_LINT,
            versao="1",
        ),
        "gabarito:marcas-pt-br": ReguaFicha(
            chave="gabarito:marcas-pt-br",
            forma="gabarito",
            sobre=("shape:politica", "shape:gabarito"),
            contra_o_que="construcao",
            garantido_por=SERVICO_LINT,
            versao="2",
        ),
        "gabarito:antipadroes-de-organizacao-documental": ReguaFicha(
            chave="gabarito:antipadroes-de-organizacao-documental",
            forma="gabarito",
            sobre=("shape:politica", "shape:gabarito"),
            contra_o_que="construcao",
            garantido_por=SERVICO_LINT,
            versao="1",
        ),
        "gabarito:figura-de-diagrama": ReguaFicha(
            chave="gabarito:figura-de-diagrama",
            forma="gabarito",
            sobre=("shape:figura",),
            contra_o_que="construcao",
            garantido_por=None,
            versao="1",
        ),
        "gabarito:outro-servico": ReguaFicha(
            chave="gabarito:outro-servico",
            forma="gabarito",
            sobre=("shape:politica",),
            contra_o_que="construcao",
            garantido_por="servico:harness:outro",
            versao="1",
        ),
        "teste:alfa": ReguaFicha(
            chave="teste:alfa",
            forma="teste",
            sobre=("shape:componente",),
            contra_o_que="construcao",
            garantido_por=SERVICO_EXECUTOR_TESTES,
            versao="1",
        ),
        "teste:alfa--politica-0011": ReguaFicha(
            chave="teste:alfa--politica-0011",
            forma="teste",
            sobre=("shape:componente",),
            contra_o_que="construcao",
            garantido_por=SERVICO_EXECUTOR_TESTES,
            versao="1",
        ),
    }


def _rodar(verbo: str, argv: list[str], ambiente: AmbienteVerificacao) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    rc = executar(verbo, argv, ambiente=ambiente, stdout=out, stderr=err)
    return rc, out.getvalue(), err.getvalue()


def _ler_recusa_stderr(stderr: str) -> dict[str, str]:
    linhas = [ln for ln in stderr.splitlines() if ln.strip()]
    assert linhas, "stderr vazio na recusa"
    obj = json.loads(linhas[-1])
    for campo in CAMPOS_RECUSA:
        assert campo in obj, f"campo {campo} ausente na recusa: {obj}"
    return obj


def _criar_teste_em_arvore(raiz: Path, rel: str, componente: str, verifica: str | None, funcoes: list[str]) -> None:
    arq = raiz / rel
    arq.parent.mkdir(parents=True, exist_ok=True)
    linhas = [f"# componente: {componente}"]
    if verifica:
        linhas.append(f"# verifica: {verifica}")
    linhas.append("")
    for fn in funcoes:
        linhas.append(f"def {fn}():\n    assert True\n")
    arq.write_text("\n".join(linhas), encoding="utf-8")


def test_ops_componente_conforme_gabarito_codigo_json(tmp_path: Path):
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:verificador": AlvoVerificado(
                chave="componente:verificador",
                classe="componente",
                slug="verificador",
                versao="abc123",
                raiz=tmp_path,
                caminho="lib/verificador",
            )
        },
    )

    def lint_ok(reguas: Sequence[str], alvos: Sequence[AlvoLint], *, prazo_s: float = 60.0):
        return julgar_lint(
            reguas,
            alvos,
            prazo_s=prazo_s,
            executor_detector=lambda _cls, _slug, _alvo: ([], "rev1"),
        )

    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_lint=lint_ok)
    rc, stdout, stderr = _rodar(
        "ops",
        ["componente:verificador", "--regua", "gabarito:antipadroes-de-codigo", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["versao_contrato"] == VERSAO_CONTRATO
    assert dados["veredito"]["resultado"] == "sim"
    assert dados["veredito"]["constatacao"] == "conforme"
    assert dados["veredito"]["modo"] == "enquadrou"
    assert dados["veredito"]["motor"] == SERVICO_LINT
    assert dados["apontamentos"] == []


def test_item_de_aviso_nao_altera_veredito_conforme(tmp_path: Path):
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:verificador": AlvoVerificado(
                chave="componente:verificador",
                classe="componente",
                slug="verificador",
                raiz=tmp_path,
            )
        },
    )

    def detector_aviso(_cls: str, _slug: str, _alvo: AlvoLint):
        return (
            [
                ApontamentoBruto(
                    arquivo="lib/verificador/borda.py",
                    linha=10,
                    o_que_fere="D15 número mágico",
                    cura="dar nome à constante",
                    severidade="aviso",
                    id="D15",
                )
            ],
            "rev1",
        )

    amb = AmbienteVerificacao(
        vista=_vista_padrao(),
        fichario=fichario,
        executor_lint=lambda r, a, prazo_s=60.0: julgar_lint(r, a, prazo_s=prazo_s, executor_detector=detector_aviso),
    )
    rc, stdout, _ = _rodar(
        "ops",
        ["componente:verificador", "--regua", "gabarito:antipadroes-de-codigo", "--json"],
        amb,
    )

    assert rc == 0
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "sim"
    assert dados["veredito"]["constatacao"] == "conforme"
    assert len(dados["apontamentos"]) == 1
    assert dados["apontamentos"][0]["severidade"] == "aviso"


def test_inconclusivo_sai_0_e_multiplos_alvos_sob_retrato_unico():
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "politica:0011": AlvoVerificado(chave="politica:0011", classe="politica", slug="0011", texto="ok"),
            "politica:0012": AlvoVerificado(chave="politica:0012", classe="politica", slug="0012", texto="inc"),
        },
    )

    def lint_misto(_reguas: Sequence[str], alvos: Sequence[AlvoLint], *, prazo_s: float = 60.0):
        return [
            VereditoLint(
                alvo=a.chave,
                resultado="sim" if a.chave == "politica:0011" else "nao-sei",
                constatacao="conforme" if a.chave == "politica:0011" else "inconclusivo",
                modo="enquadrou",
                apontamentos=(),
                nao_julgados=(),
                motor=SERVICO_LINT,
                versao_servico="sha1",
            )
            for a in alvos
        ]

    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_lint=lint_misto)
    rc, stdout, _ = _rodar(
        "casa",
        ["politica:0011", "politica:0012", "--regua", "gabarito:marcas-pt-br", "--json"],
        amb,
    )

    assert rc == 0
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "nao-sei"
    assert dados["veredito"]["constatacao"] == "inconclusivo"
    assert len(dados["itens"]) == 2
    assert fichario.leituras_alvo == ["politica:0011", "politica:0012"]


def test_concatenacao_de_gabaritos_compativeis():
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={"politica:0011": AlvoVerificado(chave="politica:0011", classe="politica", slug="0011", texto="ok")},
    )
    reguas_recebidas: list[tuple[str, ...]] = []

    def lint_captura(reguas: Sequence[str], alvos: Sequence[AlvoLint], *, prazo_s: float = 60.0):
        reguas_recebidas.append(tuple(reguas))
        return julgar_lint(reguas, alvos, prazo_s=prazo_s, executor_detector=lambda _c, _s, _a: ([], "rev1"))

    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_lint=lint_captura)
    rc, stdout, _ = _rodar(
        "casa",
        [
            "politica:0011",
            "--regua",
            "gabarito:marcas-pt-br",
            "--regua",
            "gabarito:antipadroes-de-organizacao-documental",
            "--json",
        ],
        amb,
    )

    assert rc == 0
    assert reguas_recebidas == [("gabarito:marcas-pt-br", "gabarito:antipadroes-de-organizacao-documental")]
    dados = json.loads(stdout)
    assert dados["veredito"]["quesito"] == [
        "gabarito:marcas-pt-br",
        "gabarito:antipadroes-de-organizacao-documental",
    ]


def test_ops_ficha_de_teste_verde_conforme_no_executor_de_testes(tmp_path: Path):
    _criar_teste_em_arvore(tmp_path, "tests/test_alfa.py", "componente:alfa", None, ["test_ok"])
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:alfa": AlvoVerificado(
                chave="componente:alfa",
                classe="componente",
                slug="alfa",
                raiz=tmp_path,
            )
        },
    )
    duble_exec = DubleExecutorIsolado({"tests/test_alfa.py::test_ok": True})
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_isolado=duble_exec)

    rc, stdout, stderr = _rodar(
        "ops",
        ["componente:alfa", "--regua", "teste:alfa", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "sim"
    assert dados["veredito"]["constatacao"] == "conforme"
    assert dados["veredito"]["motor"] == SERVICO_EXECUTOR_TESTES


def test_ops_dois_testes_delegados_a_suite_devolvem_laudo(tmp_path: Path):
    _criar_teste_em_arvore(tmp_path, "tests/test_a1.py", "componente:alfa", None, ["test_um"])
    _criar_teste_em_arvore(tmp_path, "tests/test_a2.py", "componente:alfa", "politica:0011", ["test_dois"])
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:alfa": AlvoVerificado(
                chave="componente:alfa",
                classe="componente",
                slug="alfa",
                raiz=tmp_path,
            )
        },
    )
    duble_exec = DubleExecutorIsolado(
        {
            "tests/test_a1.py::test_um": True,
            "tests/test_a2.py::test_dois": True,
        }
    )
    delegador = DubleDelegadorSuite(duble_exec)
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, delegador_suite=delegador)

    rc, stdout, stderr = _rodar(
        "ops",
        ["componente:alfa", "--regua", "teste:alfa", "--regua", "teste:alfa--politica-0011", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    assert len(delegador.chamadas) == 1
    dados = json.loads(stdout)
    assert dados["veredito"]["motor"] == MOTOR_SUITE_TESTES
    assert dados["veredito"]["resultado"] == "sim"
    assert len(dados["itens"]) == 2


@pytest.mark.parametrize(
    ("verbo", "argv", "saida_esperada", "codigo_esperado"),
    [
        ("casa", ["politica:0011", "--regua", "gabarito:inexistente"], 1, "regua-inexistente"),
        ("casa", ["politica:fantasma", "--regua", "gabarito:marcas-pt-br"], 1, "alvo-inexistente"),
        ("casa", ["componente:verificador", "--regua", "gabarito:antipadroes-de-codigo"], 1, "classe-fora-do-verbo"),
        ("repo", ["componente:verificador", "--regua", "gabarito:antipadroes-de-codigo"], 2, "ato-nao-aceito"),
        ("casa", ["/etc/passwd", "--regua", "gabarito:marcas-pt-br"], 2, "chave-invalida"),
        ("casa", ["politica:0011", "--desconhecida"], 2, "flag-invalida"),
        ("casa", ["figura:diag-1", "--regua", "gabarito:marcas-pt-br"], 2, "regua-incompativel"),
        (
            "ops",
            ["componente:alfa", "--regua", "gabarito:antipadroes-de-codigo", "--regua", "teste:alfa"],
            2,
            "regua-incompativel",
        ),
        (
            "casa",
            ["politica:0011", "--regua", "gabarito:marcas-pt-br", "--regua", "gabarito:outro-servico"],
            2,
            "regua-incompativel",
        ),
        (
            "ops",
            ["componente:alfa", "--regua", "teste:alfa", "--regua", "teste:alfa--politica-0011"],
            3,
            "dependencia-sem-resposta",
        ),
        ("casa", ["figura:diag-1", "--regua", "gabarito:figura-de-diagrama"], 5, "sem-motor-deterministico"),
    ],
)
def test_tabela_de_recusas_saidas_1_2_3_5(
    tmp_path: Path,
    verbo: str,
    argv: list[str],
    saida_esperada: int,
    codigo_esperado: str,
):
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "politica:0011": AlvoVerificado(chave="politica:0011", classe="politica", slug="0011"),
            "figura:diag-1": AlvoVerificado(chave="figura:diag-1", classe="figura", slug="diag-1"),
            "componente:alfa": AlvoVerificado(chave="componente:alfa", classe="componente", slug="alfa", raiz=tmp_path),
        },
    )
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)
    rc, stdout, stderr = _rodar(verbo, argv, amb)

    assert rc == saida_esperada
    assert stdout == ""
    recusa = _ler_recusa_stderr(stderr)
    assert recusa["codigo"] == codigo_esperado


def test_servico_lint_sem_resposta_sai_3():
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={"politica:0011": AlvoVerificado(chave="politica:0011", classe="politica", slug="0011")},
    )

    def lint_caiu(_reguas: Sequence[str], _alvos: Sequence[AlvoLint], *, prazo_s: float = 60.0):
        raise ErroServicoLint(3, "dependencia-sem-resposta", "ruff ausente no host")

    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_lint=lint_caiu)
    rc, stdout, stderr = _rodar("casa", ["politica:0011", "--regua", "gabarito:marcas-pt-br"], amb)

    assert rc == 3
    assert stdout == ""
    assert _ler_recusa_stderr(stderr)["codigo"] == "dependencia-sem-resposta"


def _criar_acervo_fixture(tmp_path: Path, textos: dict[str, str]) -> Path:
    """Cria executável PF_LINT_ACERVO que serve as listas de fixture em texto."""
    pasta = tmp_path / "acervo_fixture"
    pasta.mkdir(parents=True, exist_ok=True)
    for chave, conteudo in textos.items():
        (pasta / f"{chave}.md").write_text(conteudo, encoding="utf-8")
    script = pasta / "acervo-fixture"
    script.write_text(
        "#!/bin/sh\n"
        f'f="{pasta}/$4.md"\n'
        '[ "$1 $2" = "ler casa" ] && [ -f "$f" ] && exec cat "$f"\n'
        "exit 1\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_adaptador_real_codigo_t11_teste_fora_do_verdes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    lista_codigo = (
        "força não declarada · vigente — lista-de-verificacao antipadroes-de-codigo · Código\n"
        "# Antipadrões de código\n\nEspécie: lista-de-verificacao\nRev: 3\n\n"
        "| # | antipadrão | detector | classe | cura |\n"
        "|---|---|---|---|---|\n"
        "| T11 | teste fora da lista de portão | predicado TESTE_FORA_DE_PORTAO | bloqueante | incluir em VERDES |\n"
    )
    acervo_bin = _criar_acervo_fixture(tmp_path, {"antipadroes-de-codigo": lista_codigo})
    monkeypatch.setenv("PF_LINT_ACERVO", str(acervo_bin))

    repo = tmp_path / "repo_t11"
    (repo / "controle" / "tests").mkdir(parents=True)
    (repo / "controle" / "tests" / "VERDES").write_text("tests/test_ok.py\n", encoding="utf-8")
    (repo / "controle" / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / "controle" / "tests" / "test_solto.py").write_text("def test_solto():\n    assert True\n", encoding="utf-8")

    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:verificador": AlvoVerificado(
                chave="componente:verificador",
                classe="componente",
                slug="verificador",
                raiz=repo,
            )
        },
    )
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)
    rc, stdout, stderr = _rodar(
        "ops",
        ["componente:verificador", "--regua", "gabarito:antipadroes-de-codigo", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "nao"
    assert dados["veredito"]["constatacao"] == "divergente"
    assert dados["veredito"]["motor"] == SERVICO_LINT
    assert len(dados["apontamentos"]) == 1
    ap = dados["apontamentos"][0]
    assert ap["item"] == "T11"
    assert ap["lugar"] == "controle/tests/test_solto.py:1"
    assert ap["severidade"] == "bloqueante"
    assert "VERDES" in ap["cura"]


def test_adaptador_real_codigo_bloqueante_nao_medido_fecha_nao_sei(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    lista_codigo = (
        "força não declarada · vigente — lista-de-verificacao antipadroes-de-codigo · Código\n"
        "# Antipadrões de código\n\nEspécie: lista-de-verificacao\nRev: 3\n\n"
        "| # | antipadrão | detector | classe | cura |\n"
        "|---|---|---|---|---|\n"
        "| X99 | regra sem detector | predicado PREDICADO_INEXISTENTE | bloqueante | implementar predicado |\n"
    )
    acervo_bin = _criar_acervo_fixture(tmp_path, {"antipadroes-de-codigo": lista_codigo})
    monkeypatch.setenv("PF_LINT_ACERVO", str(acervo_bin))

    repo = tmp_path / "repo_nao_medido"
    (repo / "lib").mkdir(parents=True)
    (repo / "lib" / "ok.py").write_text("x = 1\n", encoding="utf-8")

    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:verificador": AlvoVerificado(
                chave="componente:verificador",
                classe="componente",
                slug="verificador",
                raiz=repo,
            )
        },
    )
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)
    rc, stdout, stderr = _rodar(
        "ops",
        ["componente:verificador", "--regua", "gabarito:antipadroes-de-codigo", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "nao-sei"
    assert dados["veredito"]["constatacao"] == "inconclusivo"
    assert "X99" in dados["nao_julgados"]


_LISTA_FORMA_DE_CARD = (
    "força não declarada · vigente — lista-de-verificacao forma-de-card · Forma de card\n"
    "# Forma de card\n\nEspécie: lista-de-verificacao\nRev: 1\n"
)
_TEXTO_STORY_CURTA = "# Story curta\n#4454 · story · Em execução\n\nNegócio: só negócio.\n"


def _reguas_com_forma_de_card() -> dict[str, ReguaFicha]:
    reguas = dict(_reguas_padrao())
    reguas["gabarito:forma-de-card"] = ReguaFicha(
        chave="gabarito:forma-de-card",
        forma="gabarito",
        sobre=("shape:politica",),
        contra_o_que="construcao",
        garantido_por=SERVICO_LINT,
        versao="1",
    )
    return reguas


def _ambiente_prosa_real(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AmbienteVerificacao:
    """Serviço de lint real sobre a política 0011, com a régua de prosa e a de forma de card servidas."""
    lista_prosa = (
        "força não declarada · vigente — gabarito marcas-pt-br · Marcas de máquina\n"
        "# Marcas de máquina\n\nEntidade: gabarito\nRev: 2\n\nTexto de marcas de máquina.\n"
    )
    listas = {"marcas-pt-br": lista_prosa, "forma-de-card": _LISTA_FORMA_DE_CARD}
    monkeypatch.setenv("PF_LINT_ACERVO", str(_criar_acervo_fixture(tmp_path, listas)))
    alvo = AlvoVerificado(chave="politica:0011", classe="politica", slug="0011", texto=_TEXTO_STORY_CURTA)
    fichario = DubleFichario(reguas=_reguas_com_forma_de_card(), alvos={"politica:0011": alvo})
    return AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)


def test_adaptador_real_prosa_sem_detector_mecanico_sai_5_sem_veredito(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    amb = _ambiente_prosa_real(tmp_path, monkeypatch)
    rc, stdout, stderr = _rodar(
        "casa",
        ["politica:0011", "--regua", "gabarito:marcas-pt-br", "--json"],
        amb,
    )

    assert rc == 5
    assert stdout == ""
    recusa = _ler_recusa_stderr(stderr)
    assert recusa["codigo"] == "sem-motor-deterministico"
    assert recusa["onde"] == "servico-lint"


def test_adaptador_real_prosa_na_uniao_com_regua_mecanica_volta_nao_julgada(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    amb = _ambiente_prosa_real(tmp_path, monkeypatch)
    rc, stdout, stderr = _rodar(
        "casa",
        ["politica:0011", "--regua", "gabarito:marcas-pt-br", "--regua", "gabarito:forma-de-card", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["versao_contrato"] == VERSAO_CONTRATO
    assert dados["veredito"]["motor"] == SERVICO_LINT
    assert "marcas-pt-br" in dados["nao_julgados"]


def test_adaptador_real_card_forma_de_card_e_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    acervo_bin = _criar_acervo_fixture(tmp_path, {"forma-de-card": _LISTA_FORMA_DE_CARD})
    monkeypatch.setenv("PF_LINT_ACERVO", str(acervo_bin))

    fichario = DubleFichario(
        reguas=_reguas_com_forma_de_card(),
        alvos={
            "politica:card-story": AlvoVerificado(
                chave="politica:card-story",
                classe="politica",
                slug="card-story",
                texto=_TEXTO_STORY_CURTA,
            )
        },
    )
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)
    rc, stdout, stderr = _rodar(
        "casa",
        ["politica:card-story", "--regua", "gabarito:forma-de-card", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["motor"] == SERVICO_LINT
    assert any("Aceite" in ap["exigencia"] for ap in dados["apontamentos"])


def test_adaptador_real_organizacao_retorna_bloqueante_ap1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import os
    import subprocess

    lista_org = (
        "força não declarada · vigente — lista-de-verificacao checklist-antipadroes-organizacao-documental · Org\n"
        "# Organização documental\n\nEspécie: lista-de-verificacao\nRev: 2\n\n"
        "| # | antipadrão | detector | classe | cura |\n"
        "|---|---|---|---|---|\n"
        "| AP1 | data no nome em docs/ | data no nome em docs/ | bloqueante | remover data do nome |\n"
    )
    acervo_bin = _criar_acervo_fixture(
        tmp_path,
        {"checklist-antipadroes-organizacao-documental": lista_org},
    )
    monkeypatch.setenv("PF_LINT_ACERVO", str(acervo_bin))

    repo = tmp_path / "repo_org"
    (repo / "docs").mkdir(parents=True)
    (repo / "README.md").write_text("# Repo\n", encoding="utf-8")
    (repo / "docs" / "2026-11-27-nota.md").write_text("# Nota\n", encoding="utf-8")
    ident = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=ident)

    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "politica:0011": AlvoVerificado(
                chave="politica:0011",
                classe="politica",
                slug="0011",
                raiz=repo,
            )
        },
    )
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)
    rc, stdout, stderr = _rodar(
        "casa",
        ["politica:0011", "--regua", "gabarito:antipadroes-de-organizacao-documental", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "nao"
    assert dados["veredito"]["constatacao"] == "divergente"
    assert any(ap["item"] == "AP1" and ap["severidade"] == "bloqueante" for ap in dados["apontamentos"])


def test_adaptador_real_acervo_sem_vazar_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    lista_acervo = (
        "força não declarada · vigente — lista-de-verificacao antipadroes-do-acervo · Acervo\n"
        "# Antipadrões do acervo\n\nEspécie: lista-de-verificacao\nRev: 4\n\n"
        "| # | antipadrão | detector | classe | cura |\n"
        "|---|---|---|---|---|\n"
        "| T1 | obra sem espécie | `especie_id` nulo | bloqueante | catalogar a obra |\n"
    )
    acervo_bin = _criar_acervo_fixture(tmp_path, {"antipadroes-do-acervo": lista_acervo})
    psql_bin = tmp_path / "psql-fixture"
    psql_bin.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "sql = sys.stdin.read()\n"
        "if 'information_schema' in sql:\n"
        "    print(json.dumps({'incidencia': False, 'derivacao': False, 'motivo_retirada': False}))\n"
        "elif 'from acervo.obra' in sql:\n"
        "    print(json.dumps([{'id': 7, 'titulo': 'Obra teste', 'anotacao': '', 'especie': None, "
        "'familia': None, 'tem_especie': False, 'emitido_por': None, 'publicacao': None, "
        "'id_canonico': None, 'incide_emitido_por': None, 'incide_publicacao': None, "
        "'incide_id_canonico': None, 'tem_dominio': True, 'tem_subdominio': True, "
        "'n_conceitos': 2, 'deriva': None}]))\n"
        "else:\n"
        "    print('[]')\n",
        encoding="utf-8",
    )
    psql_bin.chmod(0o755)
    monkeypatch.setenv("PF_LINT_ACERVO", str(acervo_bin))
    monkeypatch.setenv("PF_LINT_ACERVO_PSQL", str(psql_bin))

    reguas = dict(_reguas_padrao())
    reguas["gabarito:antipadroes-do-acervo"] = ReguaFicha(
        chave="gabarito:antipadroes-do-acervo",
        forma="gabarito",
        sobre=("shape:politica",),
        contra_o_que="construcao",
        garantido_por=SERVICO_LINT,
        versao="4",
    )
    fichario = DubleFichario(
        reguas=reguas,
        alvos={"politica:acervo": AlvoVerificado(chave="politica:acervo", classe="politica", slug="acervo")},
    )
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario)
    rc, stdout, stderr = _rodar(
        "casa",
        ["politica:acervo", "--regua", "gabarito:antipadroes-do-acervo", "--json"],
        amb,
    )

    assert rc == 0
    assert stderr == ""
    assert capsys.readouterr().out == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "nao"
    assert dados["veredito"]["constatacao"] == "divergente"
    assert any(ap["item"] == "T1" and ap["severidade"] == "bloqueante" for ap in dados["apontamentos"])


def test_teste_julga_multiplos_alvos_e_recusa_dois_alvos_na_suite(tmp_path: Path):
    arvore_a = tmp_path / "a"
    arvore_b = tmp_path / "b"
    _criar_teste_em_arvore(arvore_a, "tests/test_alfa.py", "componente:alfa", None, ["test_ok"])
    _criar_teste_em_arvore(arvore_b, "tests/test_alfa.py", "componente:alfa", None, ["test_falha"])
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:a": AlvoVerificado(chave="componente:a", classe="componente", slug="a", raiz=arvore_a),
            "componente:b": AlvoVerificado(chave="componente:b", classe="componente", slug="b", raiz=arvore_b),
        },
    )
    duble_exec = DubleExecutorIsolado({"tests/test_alfa.py::test_ok": True, "tests/test_alfa.py::test_falha": False})
    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_isolado=duble_exec)

    rc, stdout, stderr = _rodar(
        "ops",
        ["componente:a", "componente:b", "--regua", "teste:alfa", "--json"],
        amb,
    )
    assert rc == 0
    assert stderr == ""
    dados = json.loads(stdout)
    assert dados["veredito"]["resultado"] == "nao"
    assert [item["alvo"] for item in dados["itens"]] == ["componente:a", "componente:b"]
    assert dados["itens"][0]["resultado"] == "sim"
    assert dados["itens"][1]["resultado"] == "nao"

    rc2, stdout2, stderr2 = _rodar(
        "ops",
        ["componente:a", "componente:b", "--regua", "teste:alfa", "--regua", "teste:alfa--politica-0011"],
        amb,
    )
    assert rc2 == 2
    assert stdout2 == ""
    assert _ler_recusa_stderr(stderr2)["codigo"] == "regua-incompativel"


def test_saida_5_por_prazo_preserva_vereditos_ja_julgados_em_stdout():
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "politica:0011": AlvoVerificado(chave="politica:0011", classe="politica", slug="0011", texto="a"),
            "politica:0012": AlvoVerificado(chave="politica:0012", classe="politica", slug="0012", texto="b"),
        },
    )

    def lint_estoura(_reguas: Sequence[str], _alvos: Sequence[AlvoLint], *, prazo_s: float = 60.0):
        parcial = VereditoLint(
            alvo="politica:0011",
            resultado="sim",
            constatacao="conforme",
            modo="enquadrou",
            apontamentos=(),
            nao_julgados=(),
            motor=SERVICO_LINT,
            versao_servico="sha1",
        )
        raise ErroServicoLint(
            5,
            "tempo-esgotado",
            "prazo esgotado antes do segundo alvo",
            vereditos_parciais=(parcial,),
        )

    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_lint=lint_estoura)
    rc, stdout, stderr = _rodar(
        "casa",
        ["politica:0011", "politica:0012", "--regua", "gabarito:marcas-pt-br", "--json"],
        amb,
    )

    assert rc == 5
    recusa = _ler_recusa_stderr(stderr)
    assert recusa["codigo"] == "tempo-esgotado"
    dados = json.loads(stdout)
    assert dados["versao_contrato"] == VERSAO_CONTRATO
    assert "veredito" not in dados
    assert len(dados["itens"]) == 1
    assert dados["itens"][0]["alvo"] == "politica:0011"
    assert dados["itens"][0]["resultado"] == "sim"
