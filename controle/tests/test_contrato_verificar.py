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


def test_ops_fixture_teste_fora_de_portao_t11_divergente_sai_0(tmp_path: Path):
    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:verificador": AlvoVerificado(
                chave="componente:verificador",
                classe="componente",
                slug="verificador",
                versao="def456",
                raiz=tmp_path,
            )
        },
    )

    def detector_t11(_cls: str, _slug: str, _alvo: AlvoLint):
        return (
            [
                ApontamentoBruto(
                    arquivo="controle/tests/test_solto.py",
                    linha=1,
                    o_que_fere="T11 teste fora da lista de portão [TESTE_FORA_DE_PORTAO]",
                    cura="incluir o arquivo em controle/tests/VERDES no mesmo commit",
                    severidade="bloqueante",
                    id="T11",
                )
            ],
            "rev1",
        )

    def lint_t11(reguas: Sequence[str], alvos: Sequence[AlvoLint], *, prazo_s: float = 60.0):
        return julgar_lint(reguas, alvos, prazo_s=prazo_s, executor_detector=detector_t11)

    amb = AmbienteVerificacao(vista=_vista_padrao(), fichario=fichario, executor_lint=lint_t11)
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
    assert len(dados["apontamentos"]) == 1
    ap = dados["apontamentos"][0]
    assert ap["item"] == "T11"
    assert ap["lugar"] == "controle/tests/test_solto.py:1"
    assert "T11" in ap["exigencia"]
    assert ap["severidade"] == "bloqueante"
    assert "VERDES" in ap["cura"]


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
