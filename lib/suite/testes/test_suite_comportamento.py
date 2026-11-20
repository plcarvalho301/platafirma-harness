# componente: componente:suite
"""Casos de comportamento do componente suite: vínculo, seleção, admissão e medida de eficácia por mutação."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import tomllib

LIB_RAIZ = Path(__file__).resolve().parents[2]
if str(LIB_RAIZ) not in sys.path:
    sys.path.insert(0, str(LIB_RAIZ))

from suite.admissao import DubleOlaria, admitir
from suite.consulta import (
    DubleLeitorOlaria,
    consultar_componente,
    consultar_momento,
    consultar_soltos,
    consultar_stack,
)
from suite.mutacao import (
    MAX_MUTANTES_POR_LINHA,
    MutacaoErro,
    gerar_mutantes_arquivo,
    medir_componente,
)
from suite.selecao import selecionar
from suite.vinculo import ler_vinculo

HARNESS_RAIZ = LIB_RAIZ.parent

_FONTE_PROVA = """\
def classificar(valor: int) -> str:
    if valor > 5:
        return "alto"
    return "baixo"


def desconto(preco: float) -> float:
    if preco >= 50.0:
        return preco * 0.9
    return preco


def funcao_sem_teste(x: int) -> int:
    if x == 0:
        return 100
    return x + 42
"""

_TESTE_PROVA = """\
# componente: calculo
from calculo import classificar, desconto


def test_classificar_confere_saida():
    assert classificar(10) == "alto"
    assert classificar(2) == "baixo"


def test_desconto_cego_sem_conferencia():
    desconto(100.0)
"""


def _montar_arvore_prova(tmp_path: Path) -> Path:
    arvore = tmp_path / "arvore_prova"
    comp = arvore / "calculo"
    comp.mkdir(parents=True, exist_ok=True)
    (comp / "calculo.py").write_text(_FONTE_PROVA, encoding="utf-8")
    (comp / "test_calculo.py").write_text(_TESTE_PROVA, encoding="utf-8")
    return arvore


def _rodar_cli_medir(arvore: Path, componente: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(LIB_RAIZ)
    return subprocess.run(
        [sys.executable, "-m", "suite", "medir", componente, "--arvore", str(arvore)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


def _rodar_cli_suite(*args: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(LIB_RAIZ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "suite", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_medida_aponta_caso_cego_e_ignora_funcao_sem_teste(tmp_path: Path):
    arvore = _montar_arvore_prova(tmp_path)
    original = (arvore / "calculo" / "calculo.py").read_text(encoding="utf-8")

    medida = medir_componente("componente:calculo", arvore=arvore)

    assert medida.componente == "componente:calculo"
    assert medida.mutantes_gerados > 0
    assert 0 < medida.mutantes_mortos < medida.mutantes_gerados
    assert 0.0 < medida.escore_amostra < 1.0
    assert "funcao_sem_teste" not in medida.funcoes_mutadas
    assert "classificar" in medida.funcoes_mutadas
    assert "desconto" in medida.funcoes_mutadas
    assert medida.candidatos_a_sair == ["test_calculo.py::test_desconto_cego_sem_conferencia"]
    assert len(medida.mutantes_sobreviventes) > 0
    assert (arvore / "calculo" / "calculo.py").read_text(encoding="utf-8") == original


def test_cli_medir_sai_zero_com_candidato_e_mostra_amostra(tmp_path: Path):
    arvore = _montar_arvore_prova(tmp_path)
    proc = _rodar_cli_medir(arvore, "componente:calculo")

    assert proc.returncode == 0
    assert "componente: componente:calculo" in proc.stdout
    assert "amostra:" in proc.stdout
    assert "test_desconto_cego_sem_conferencia" in proc.stdout
    assert "funcao_sem_teste" not in proc.stdout


@pytest.mark.parametrize(
    ("codigo_corpo", "linha_alvo", "operador_esperado", "trecho_esperado"),
    [
        ("    return a == b\n", 2, "troca_comparacao", "!="),
        ("    if ativo:\n        return 1\n", 2, "negacao_condicao", "not (ativo)"),
        ("    return a + b\n", 2, "retorno_none", "return None"),
        ("    limite = 10\n    return limite\n", 2, "troca_constante", "11"),
    ],
)
def test_operadores_de_mutacao_em_tabela(
    tmp_path: Path,
    codigo_corpo: str,
    linha_alvo: int,
    operador_esperado: str,
    trecho_esperado: str,
):
    arq = tmp_path / "alvo.py"
    arq.write_text(f"def fn(a=1, b=2, ativo=True):\n{codigo_corpo}", encoding="utf-8")

    mutantes = gerar_mutantes_arquivo(arq, "alvo.py", {linha_alvo})
    operadores = {m.operador for m in mutantes}
    depois_todos = " ".join(m.depois for m in mutantes)

    assert operador_esperado in operadores
    assert trecho_esperado in depois_todos
    assert len(mutantes) <= MAX_MUTANTES_POR_LINHA


def test_teto_de_tres_mutantes_por_linha_e_filtro_de_cobertura(tmp_path: Path):
    arq = tmp_path / "denso.py"
    arq.write_text(
        "def f(x: int) -> int:\n"
        "    if x == 0 and True:\n"
        "        return 10\n"
        "    return 20\n",
        encoding="utf-8",
    )

    mutantes_linha_2 = gerar_mutantes_arquivo(arq, "denso.py", {2})
    mutantes_sem_cobertura = gerar_mutantes_arquivo(arq, "denso.py", set())

    assert len(mutantes_linha_2) == MAX_MUTANTES_POR_LINHA
    assert mutantes_sem_cobertura == []


def test_componente_inexistente_levanta_erro(tmp_path: Path):
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    with pytest.raises(MutacaoErro, match="não encontrado"):
        medir_componente("componente:inexistente", arvore=vazio)


def test_coverage_declarado_no_grupo_dev_e_fora_de_dependencies():
    pyproject = HARNESS_RAIZ / "venvs" / "harness\" / \"pyproject.toml\"".replace('\"', "")
    pyproject = HARNESS_RAIZ / "venvs" / "harness" / "pyproject.toml"
    lock = HARNESS_RAIZ / "venvs" / "harness" / "uv.lock"
    dados = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps_prod = " ".join(dados.get("project", {}).get("dependencies", []))
    deps_dev = " ".join(dados.get("dependency-groups", {}).get("dev", []))
    texto_lock = lock.read_text(encoding="utf-8")

    assert "coverage" not in deps_prod
    assert "coverage" in deps_dev
    assert 'name = "coverage"' in texto_lock


# --- Vínculo, seleção na fita e admissão na esteira (#4296) ---------------------------------


_CASOS_VINCULO: list[dict[str, Any]] = [
    {
        "nome_arq": "test_comp.py",
        "conteudo": (
            "# componente: suite\nimport pytest\n\n"
            "@pytest.mark.exige('olaria:olaria')\n"
            "@pytest.mark.incidente(4330)\n"
            "def test_um():\n    assert True\n"
        ),
        "comp": "componente:suite",
        "verifica": None,
        "classe": "teste-de-comportamento",
        "exige": ("olaria:olaria",),
        "incidentes": (4330,),
    },
    {
        "nome_arq": "test_front.py",
        "conteudo": (
            "# componente: componente:porta\n# verifica: interface:acervo-escrita\n"
            "def test_rota():\n    assert True\n"
        ),
        "comp": "componente:porta",
        "verifica": "interface:acervo-escrita",
        "classe": "teste-de-fronteira",
        "exige": (),
        "incidentes": (),
    },
    {
        "nome_arq": "test_regra.sh",
        "conteudo": (
            "#!/usr/bin/env bash\n# componente: verbo-repo\n# verifica: politica:0001\n"
            "# exige: host:casa\n# incidente: 3313\ntest_politica() { true; }\n"
        ),
        "comp": "componente:verbo-repo",
        "verifica": "politica:0001",
        "classe": "teste-de-regra",
        "exige": ("host:casa",),
        "incidentes": (3313,),
    },
    {
        "nome_arq": "test_ui.mjs",
        "conteudo": (
            "// componente: ui-pf\n// verifica: gabarito:comportamento\n"
            "// exige: servico:rastreador\ntest('renderiza', () => {});\n"
        ),
        "comp": "componente:ui-pf",
        "verifica": "gabarito:comportamento",
        "classe": "teste-de-regra",
        "exige": ("servico:rastreador",),
        "incidentes": (),
    },
    {
        "nome_arq": "test_controle.py",
        "conteudo": (
            "# componente: porta\n# verifica: controle-de-seguranca:conta-da-porta\n"
            "def test_conta():\n    assert True\n"
        ),
        "comp": "componente:porta",
        "verifica": "controle-de-seguranca:conta-da-porta",
        "classe": "teste-de-regra",
        "exige": (),
        "incidentes": (),
    },
]


def test_admissao_aceita_controle_de_seguranca_como_alvo_do_teste_de_regra():
    duble = DubleOlaria(
        {"componente:porta": "componente", "controle-de-seguranca:conta-da-porta": "controle-de-seguranca"}
    )
    ficha = {
        "classe": "teste-de-regra",
        "chave": "teste-de-regra:porta--controle-de-seguranca-conta-da-porta",
        "ligacoes": {"sobre": "componente:porta", "verifica": "controle-de-seguranca:conta-da-porta"},
    }
    assert duble.ensaiar([ficha])["erros"] == []


@pytest.mark.parametrize("caso", _CASOS_VINCULO, ids=[c["nome_arq"] for c in _CASOS_VINCULO])
def test_ler_vinculo_e_marcas_em_tabela(tmp_path: Path, caso: dict[str, Any]):
    arq = tmp_path / caso["nome_arq"]
    arq.write_text(caso["conteudo"], encoding="utf-8")
    v = ler_vinculo(arq)

    assert v.componente == caso["comp"]
    assert v.verifica == caso["verifica"]
    assert v.classe == caso["classe"]
    assert v.exige == caso["exige"]
    assert v.incidentes == caso["incidentes"]
    ficha = v.como_ficha()
    assert ficha["classe"] == caso["classe"]
    assert ficha["ligacoes"]["sobre"] == caso["comp"]
    assert ficha["ligacoes"].get("verifica") == caso["verifica"]


def test_seletor_fita_roda_tres_deixa_exige_fora_e_ampliado_roda_quatro(tmp_path: Path):
    arvore = tmp_path / "arvore_sel"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_prova_comportamento.py").write_text(
        "# componente: prova\n"
        "import pytest\n\n"
        "def test_c1():\n    assert 1 + 1 == 2\n\n"
        "def test_c2():\n    assert 'a'.upper() == 'A'\n\n"
        "def test_c3():\n    assert len([1, 2, 3]) == 3\n\n"
        "@pytest.mark.exige('olaria:olaria')\n"
        "def test_c4_com_ambiente():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_outro_componente.py").write_text(
        "# componente: outro\ndef test_nao_entra():\n    assert False\n",
        encoding="utf-8",
    )

    res_fita = selecionar("prova", arvore=arvore, ampliado=False)
    assert res_fita.codigo_saida == 0
    assert res_fita.rodados == 3
    assert res_fita.aprovados == 3
    assert res_fita.reprovados == 0
    assert res_fita.fora_exige == 1
    assert res_fita.duracao_s < 60.0

    res_amp = selecionar("prova", arvore=arvore, ampliado=True)
    assert res_amp.codigo_saida == 0
    assert res_amp.rodados == 4
    assert res_amp.aprovados == 4
    assert res_amp.reprovados == 0
    assert res_amp.fora_exige == 0

    proc_cli = _rodar_cli_suite("selecionar", "prova", "--arvore", str(arvore))
    assert proc_cli.returncode == 0
    assert "3 casos rodados" in proc_cli.stdout
    assert "1 com exige fora" in proc_cli.stdout

    proc_cli_amp = _rodar_cli_suite("selecionar", "prova", "--arvore", str(arvore), "--ampliado")
    assert proc_cli_amp.returncode == 0
    assert "4 casos rodados" in proc_cli_amp.stdout


def test_seletor_ampliado_inclui_fronteira_regra_sh_mjs_e_acusa_extensao_nao_medida(tmp_path: Path):
    arvore = tmp_path / "arvore_multi"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_comp.py").write_text(
        "# componente: multi\ndef test_base():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_fronteira.sh").write_text(
        "#!/usr/bin/env bash\n# componente: multi\n# verifica: interface:api\nexit 0\n",
        encoding="utf-8",
    )
    (pasta / "test_regra.mjs").write_text(
        "// componente: multi\n// verifica: politica:0001\nprocess.exit(0);\n",
        encoding="utf-8",
    )

    res_fita = selecionar("multi", arvore=arvore, ampliado=False)
    assert res_fita.rodados == 1
    assert res_fita.arquivos == ("testes/test_comp.py",)

    res_amp = selecionar("multi", arvore=arvore, ampliado=True)
    assert res_amp.codigo_saida == 0
    assert res_amp.rodados == 3
    assert set(res_amp.arquivos) == {
        "testes/test_comp.py",
        "testes/test_fronteira.sh",
        "testes/test_regra.mjs",
    }

    (pasta / "test_estranho.rb").write_text("# componente: multi\nputs 'oi'\n", encoding="utf-8")
    res_nao_medido = selecionar("multi", arvore=arvore, ampliado=False)
    assert res_nao_medido.codigo_saida == 3
    assert "testes/test_estranho.rb" in res_nao_medido.nao_medidos


def test_admissao_aprova_conjunto_valido_e_ensaia_ficha_no_duble(tmp_path: Path):
    arvore = tmp_path / "arvore_ok"
    (arvore / "src").mkdir(parents=True)
    (arvore / "src" / "servico.py").write_text("def somar(a, b):\n    return a + b\n", encoding="utf-8")
    (arvore / "testes").mkdir(parents=True)
    (arvore / "testes" / "test_servico.py").write_text(
        "# componente: servico-x\nimport pytest\n\n"
        "@pytest.mark.exige('olaria:olaria')\n"
        "def test_somar():\n    assert True\n",
        encoding="utf-8",
    )
    (arvore / "testes" / "test_servico_regra.py").write_text(
        "# componente: servico-x\n# verifica: politica:0001\n"
        "def test_regra():\n    assert True\n",
        encoding="utf-8",
    )

    duble = DubleOlaria(
        fichas={
            "componente:servico-x": "componente",
            "olaria:olaria": "servico",
            "politica:0001": "politica",
        }
    )
    res = admitir(arvore, ensaiador=duble)

    assert res.codigo_saida == 0
    assert res.estado == "admitido"
    assert res.recusas == ()
    assert len(res.fichas_ensaiadas) == 2


@pytest.mark.parametrize(
    ("cenario", "arquivos", "codigo_esperado", "trecho_esperado"),
    [
        (
            "sem_componente",
            {"testes/test_orf.py": "def test_sem_cabecalho():\n    assert True\n"},
            "sem-componente",
            "testes/test_orf.py",
        ),
        (
            "componente_nao_eh_ficha",
            {"testes/test_invalido.py": "# componente: nao-existe\ndef test_x():\n    assert True\n"},
            "ficha-invalida",
            "componente:nao-existe",
        ),
        (
            "alvo_nao_eh_ficha",
            {
                "testes/test_alvo_ruim.py": (
                    "# componente: suite\n# verifica: interface:fantasma\n"
                    "def test_x():\n    assert True\n"
                )
            },
            "ficha-invalida",
            "interface:fantasma",
        ),
        (
            "segundo_conjunto_mesmo_par",
            {
                "testes/test_a_primeiro.py": "# componente: suite\ndef test_1():\n    assert True\n",
                "testes/test_b_segundo.py": "# componente: suite\ndef test_2():\n    assert True\n",
            },
            "segundo-conjunto",
            "testes/test_a_primeiro.py",
        ),
        (
            "nome_batizado_por_card",
            {
                "testes/test_suite.py": "# componente: suite\ndef test_1():\n    assert True\n",
                "testes/test_curar_descricao_4144.py": (
                    "# componente: suite\n# verifica: politica:0001\n"
                    "def test_card():\n    assert True\n"
                ),
            },
            "nome-com-card",
            "4144",
        ),
        (
            "producao_python_importa_apoio",
            {
                "src/prod.py": "from suite.testes import apoio\n",
                "testes/apoio.py": "VALOR = 1\n",
                "testes/test_suite.py": "# componente: suite\ndef test_1():\n    assert True\n",
            },
            "producao-importa-apoio",
            "testes/test_suite.py",
        ),
        (
            "producao_node_importa_apoio",
            {
                "src/app.mjs": "import { falso } from '../testes/apoio.mjs';\n",
                "testes/test_suite.py": "# componente: suite\ndef test_1():\n    assert True\n",
            },
            "producao-importa-apoio",
            "testes/test_suite.py",
        ),
    ],
)
def test_admissao_recusa_conjuntos_invalidos_em_tabela(
    tmp_path: Path,
    cenario: str,
    arquivos: dict[str, str],
    codigo_esperado: str,
    trecho_esperado: str,
):
    arvore = tmp_path / cenario
    for rel, conteudo in arquivos.items():
        alvo = arvore / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")

    duble = DubleOlaria(
        fichas={
            "componente:suite": "componente",
            "politica:0001": "politica",
        }
    )
    res = admitir(arvore, ensaiador=duble)

    assert res.codigo_saida == 1
    assert res.estado == "recusado"
    codigos = [r.codigo for r in res.recusas]
    assert codigo_esperado in codigos
    texto = res.resumo_texto()
    assert trecho_esperado in texto


def test_admissao_regra_nova_1_acusa_legado_sem_recusar_e_barra_mudado(tmp_path: Path):
    arvore = tmp_path / "arvore_legado"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_legado_4144.py").write_text(
        "def test_velho_sem_componente():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_novo_valido.py").write_text(
        "# componente: suite\ndef test_novo():\n    assert True\n",
        encoding="utf-8",
    )

    duble = DubleOlaria(fichas={"componente:suite": "componente"})
    res_so_novo = admitir(
        arvore,
        ensaiador=duble,
        arquivos_mudados=["testes/test_novo_valido.py"],
    )
    assert res_so_novo.codigo_saida == 0
    assert res_so_novo.recusas == ()
    assert len(res_so_novo.avisos_legado) >= 1
    assert "aviso (já na main)" in res_so_novo.resumo_texto()

    res_tocou_legado = admitir(
        arvore,
        ensaiador=duble,
        arquivos_mudados=["testes/test_legado_4144.py", "testes/test_novo_valido.py"],
    )
    assert res_tocou_legado.codigo_saida == 1
    assert any(r.arquivo == "testes/test_legado_4144.py" for r in res_tocou_legado.recusas)


def test_admissao_sai_3_nao_medido_quando_olaria_fora(tmp_path: Path):
    arvore = tmp_path / "arvore_olaria_fora"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_suite.py").write_text(
        "# componente: suite\ndef test_ok():\n    assert True\n",
        encoding="utf-8",
    )

    res = admitir(arvore, ensaiador=DubleOlaria(fora_do_ar=True))
    assert res.codigo_saida == 3
    assert res.estado == "nao-medido"
    assert "NAO MEDIDO" in res.resumo_texto()


# --- Consulta da suíte: componente, stack, momento, alvo encerrado e soltos (#4298) -----------


def _montar_arvore_consulta_tres_classes(tmp_path: Path) -> tuple[Path, DubleLeitorOlaria]:
    arvore = tmp_path / "arvore_tres_classes"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_a_comportamento.py").write_text(
        "# componente: prova\n"
        "import pytest\n\n"
        "@pytest.mark.exige('olaria:olaria')\n"
        "def test_comp():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_b_fronteira.py").write_text(
        "# componente: prova\n"
        "# verifica: interface:api-prova\n"
        "def test_front():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_c_regra.py").write_text(
        "# componente: prova\n"
        "# verifica: politica:0001\n"
        "import pytest\n\n"
        "@pytest.mark.incidente(3313)\n"
        "def test_regra():\n    assert True\n",
        encoding="utf-8",
    )
    leitor = DubleLeitorOlaria(
        fichas=[
            {"classe": "componente", "chave": "componente:prova", "ligacoes": {"componente-de": "stack:harness"}},
            {"classe": "servico", "chave": "olaria:olaria", "estado": "servindo"},
            {"classe": "interface", "chave": "interface:api-prova", "ligacoes": {"garantido-por": "componente:prova"}},
            {"classe": "politica", "chave": "politica:0001", "estado": "vigente"},
        ]
    )
    return arvore, leitor


def test_consulta_componente_tres_classes_devolve_tres_linhas_com_classe_alvo_momento(tmp_path: Path):
    arvore, leitor = _montar_arvore_consulta_tres_classes(tmp_path)
    res = consultar_componente("prova", arvore=arvore, leitor=leitor)

    assert res.componente == "componente:prova"
    assert len(res.verificacoes) == 3
    linhas = res.resumo_texto().splitlines()
    assert len(linhas) == 3

    v_comp, v_front, v_regra = res.verificacoes
    assert v_comp.classe == "teste-de-comportamento"
    assert v_comp.alvo is None
    assert v_comp.exige == ("olaria:olaria",)
    assert v_comp.momentos == ("fita", "push")
    assert "fita" in linhas[0] and "teste-de-comportamento" in linhas[0] and "alvo=comportamento" in linhas[0]

    assert v_front.classe == "teste-de-fronteira"
    assert v_front.alvo == "interface:api-prova"
    assert v_front.momentos == ("push",)
    assert "teste-de-fronteira" in linhas[1] and "alvo=interface:api-prova" in linhas[1] and "push" in linhas[1]

    assert v_regra.classe == "teste-de-regra"
    assert v_regra.alvo == "politica:0001"
    assert v_regra.incidentes == (3313,)
    assert "teste-de-regra" in linhas[2] and "alvo=politica:0001" in linhas[2] and "incidente" in linhas[2]
    assert not any(v.para_retirada for v in res.verificacoes)


def test_consulta_stack_separa_quem_fornece_e_quem_consome_na_fronteira(tmp_path: Path):
    arvore = tmp_path / "arvore_stack"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_fornecedor_front.py").write_text(
        "# componente: api-catalogo\n# verifica: interface:catalogo-http\ndef test_forn():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_consumidor_front.py").write_text(
        "# componente: cli-catalogo\n# verifica: interface:catalogo-http\ndef test_cons():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_avulso_front.py").write_text(
        "# componente: avulso\n# verifica: interface:sem-lado\ndef test_avulso():\n    assert True\n",
        encoding="utf-8",
    )
    (pasta / "test_api_comp.py").write_text(
        "# componente: api-catalogo\ndef test_interno():\n    assert True\n",
        encoding="utf-8",
    )

    leitor = DubleLeitorOlaria(
        fichas=[
            {
                "classe": "componente",
                "chave": "componente:api-catalogo",
                "ligacoes": {"componente-de": "catalogo:servidor"},
            },
            {
                "classe": "componente",
                "chave": "componente:cli-catalogo",
                "ligacoes": {"componente-de": ["stack:catalogo", "catalogo:cliente"]},
            },
            {
                "classe": "componente",
                "chave": "componente:avulso",
                "ligacoes": {"componente-de": "stack:catalogo"},
            },
            {
                "classe": "servico",
                "chave": "catalogo:servidor",
                "estado": "servindo",
                "ligacoes": {"expoe": "interface:catalogo-http"},
            },
            {
                "classe": "servico",
                "chave": "catalogo:cliente",
                "estado": "servindo",
                "ligacoes": {"consome": "interface:catalogo-http"},
            },
            {
                "classe": "interface",
                "chave": "interface:catalogo-http",
                "ligacoes": {"garantido-por": "componente:api-catalogo"},
            },
            {
                "classe": "interface",
                "chave": "interface:sem-lado",
            },
        ]
    )

    res = consultar_stack("catalogo", arvore=arvore, leitor=leitor)
    assert res.stack == "stack:catalogo"
    assert [v.componente for v in res.fornece] == ["componente:api-catalogo"]
    assert [v.componente for v in res.consome] == ["componente:cli-catalogo"]
    assert [v.componente for v in res.lado_nao_declarado] == ["componente:avulso"]

    texto = res.resumo_texto()
    idx_forn = texto.index("fronteira — quem fornece:")
    idx_cons = texto.index("fronteira — quem consome:")
    idx_nao = texto.index("fronteira — lado não declarado:")
    assert idx_forn < idx_cons < idx_nao
    assert "componente:api-catalogo" in texto[idx_forn:idx_cons]
    assert "componente:cli-catalogo" in texto[idx_cons:idx_nao]
    assert "componente:avulso" in texto[idx_nao:]


@pytest.mark.parametrize(
    ("momento", "roda_esperado", "qtd_esperada", "trecho_esperado"),
    [
        ("fita", True, 1, "test_a_comportamento.py"),
        ("push", True, 3, "test_b_fronteira.py"),
        ("integracao", False, 3, "não roda teste"),
    ],
)
def test_consulta_momento_em_tabela(
    tmp_path: Path,
    momento: str,
    roda_esperado: bool,
    qtd_esperada: int,
    trecho_esperado: str,
):
    arvore, leitor = _montar_arvore_consulta_tres_classes(tmp_path)
    res = consultar_momento(momento, arvore=arvore, leitor=leitor)

    assert res.momento == momento
    assert res.roda_testes is roda_esperado
    assert len(res.verificacoes) == qtd_esperada
    assert trecho_esperado in res.resumo_texto()


@pytest.mark.parametrize(
    (
        "cenario",
        "cabecalho_e_corpo",
        "fichas",
        "desfechos",
        "retirada_esperada",
        "codigo_esperado",
        "responsavel_esperado",
        "trecho_linha",
    ),
    [
        (
            "alvo_sem_ficha",
            "# componente: prova\n# verifica: interface:fantasma\ndef test_1():\n    assert True\n",
            [{"classe": "componente", "chave": "componente:prova"}],
            (),
            True,
            "sem-ficha",
            "ti",
            "responde: ti",
        ),
        (
            "componente_sem_ficha",
            "# componente: orfao\ndef test_1():\n    assert True\n",
            [],
            (),
            True,
            "sem-ficha",
            "engenharia",
            "responde: engenharia",
        ),
        (
            "politica_revogada_sem_saida",
            "# componente: prova\n# verifica: politica:0001\ndef test_1():\n    assert True\n",
            [
                {"classe": "componente", "chave": "componente:prova"},
                {"classe": "politica", "chave": "politica:0001", "estado": "revogada"},
            ],
            (),
            True,
            "estado-sem-saida",
            "arquiteto",
            "responde: arquiteto",
        ),
        (
            "servico_exige_removido",
            "# componente: prova\nimport pytest\n@pytest.mark.exige('olaria:olaria')\ndef test_1():\n    assert True\n",
            [
                {"classe": "componente", "chave": "componente:prova"},
                {"classe": "servico", "chave": "olaria:olaria", "estado": "removido"},
            ],
            (),
            True,
            "estado-sem-saida",
            "ti",
            "responde: ti",
        ),
        (
            "interface_encerrada_por_desfecho",
            "# componente: prova\n# verifica: interface:antiga\ndef test_1():\n    assert True\n",
            [
                {"classe": "componente", "chave": "componente:prova"},
                {"classe": "interface", "chave": "interface:antiga"},
            ],
            ("interface:antiga",),
            True,
            "evento-de-encerramento",
            "ti",
            "evento de encerramento (responde: ti)",
        ),
        (
            "estado_nao_lido_nao_acusa_retirada",
            "# componente: prova\n# verifica: politica:0002\ndef test_1():\n    assert True\n",
            [
                {"classe": "componente", "chave": "componente:prova"},
                {"classe": "politica", "chave": "politica:0002"},
            ],
            (),
            False,
            None,
            None,
            "estado=estado não lido",
        ),
        (
            "embedder_obsoleto_com_ficha_segue_vivo",
            "# componente: prova\nimport pytest\n@pytest.mark.exige('embedder:bge-m3')\ndef test_1():\n    assert True\n",
            [
                {"classe": "componente", "chave": "componente:prova"},
                {"classe": "embedder", "chave": "embedder:bge-m3", "estado": "obsoleto"},
            ],
            ("embedder:bge-m3",),
            False,
            None,
            None,
            "exige=embedder:bge-m3",
        ),
        (
            "embedder_sem_ficha_acusa_retirada",
            "# componente: prova\nimport pytest\n@pytest.mark.exige('embedder:inexistente')\ndef test_1():\n    assert True\n",
            [{"classe": "componente", "chave": "componente:prova"}],
            (),
            True,
            "sem-ficha",
            "ia",
            "responde: ia",
        ),
    ],
)
def test_consulta_alvo_encerrado_e_excecoes_em_tabela(
    tmp_path: Path,
    cenario: str,
    cabecalho_e_corpo: str,
    fichas: list[dict[str, Any]],
    desfechos: tuple[str, ...],
    retirada_esperada: bool,
    codigo_esperado: str | None,
    responsavel_esperado: str | None,
    trecho_linha: str,
):
    arvore = tmp_path / cenario
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_caso.py").write_text(cabecalho_e_corpo, encoding="utf-8")

    leitor = DubleLeitorOlaria(fichas=fichas, desfechos=desfechos)
    comp = "orfao" if cenario == "componente_sem_ficha" else "prova"
    res = consultar_componente(comp, arvore=arvore, leitor=leitor)

    assert len(res.verificacoes) == 1
    v = res.verificacoes[0]
    assert v.para_retirada is retirada_esperada
    if retirada_esperada:
        assert v.motivos_retirada[0].codigo == codigo_esperado
        assert v.responsavel_retirada == responsavel_esperado
    else:
        assert v.motivos_retirada == ()
    assert trecho_linha in res.resumo_texto()


def test_consulta_soltos_bate_com_admissao_e_cli_consultar(tmp_path: Path):
    arvore = tmp_path / "arvore_soltos"
    pasta = arvore / "testes"
    pasta.mkdir(parents=True)
    (pasta / "test_vinculado.py").write_text("# componente: suite\ndef test_ok():\n    assert True\n", encoding="utf-8")
    (pasta / "test_solto_1.py").write_text("def test_s1():\n    assert True\n", encoding="utf-8")
    (pasta / "test_solto_2.py").write_text("def test_s2():\n    assert True\n", encoding="utf-8")
    (arvore / ".olaria.json").write_text(
        '{"fichas": [{"classe": "componente", "chave": "componente:suite"}]}',
        encoding="utf-8",
    )

    soltos = consultar_soltos(arvore)
    assert soltos.total_descobertos == 3
    assert soltos.total_soltos == 2
    assert soltos.com_vinculo == 1
    assert soltos.arquivos == ("testes/test_solto_1.py", "testes/test_solto_2.py")

    proc_soltos = _rodar_cli_suite("consultar", "soltos", "--arvore", str(arvore))
    assert proc_soltos.returncode == 0
    assert "2 arquivo(s) sem vínculo" in proc_soltos.stdout

    proc_comp = _rodar_cli_suite("consultar", "componente", "suite", "--arvore", str(arvore), "--json")
    assert proc_comp.returncode == 0
    assert '"componente": "componente:suite"' in proc_comp.stdout

    soltos_harness = consultar_soltos(HARNESS_RAIZ)
    assert soltos_harness.total_descobertos == soltos_harness.total_soltos + soltos_harness.com_vinculo
    assert soltos_harness.com_vinculo >= 1


def _executar_cenario_esteira(tmp_path: Path, spec: dict[str, Any]) -> tuple[Any, Any, Path]:
    from suite.esteira import DubleBalde, DubleExecutorIsolado, rodar

    arvore = tmp_path / spec["cenario"]
    arvore.mkdir(parents=True, exist_ok=True)
    for rel, conteudo in spec["arquivos"].items():
        alvo = arvore / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")

    leitor = DubleLeitorOlaria(
        fichas=[
            {"classe": "componente", "chave": "componente:suite", "dados": {"caminho": "suite"}},
            {"classe": "componente", "chave": "componente:outro", "dados": {"caminho": "outro"}},
            {"classe": "interface", "chave": "interface:porta"},
            {"classe": "politica", "chave": "politica:0001"},
            {"classe": "servico", "chave": "olaria:olaria"},
            {"classe": "servico", "chave": "servico:fora"},
        ]
    )
    ensaiador = DubleOlaria(
        fichas={
            "componente:suite": "componente",
            "componente:outro": "componente",
            "interface:porta": "interface",
            "politica:0001": "politica",
            "olaria:olaria": "servico",
            "servico:fora": "servico",
        }
    )
    balde = spec.get("balde") or DubleBalde(linhas=spec.get("debitos_iniciais") or [])
    exec_duble = DubleExecutorIsolado(spec.get("roteiro_exec") or {})
    pasta_ver = tmp_path / "vereditos"
    ativos = set(spec.get("servicos_ativos") or ())

    ver = rodar(
        "repo-prova",
        arvore=arvore,
        mudanca="aaa1111",
        base="bbb2222",
        arquivos_mudados=spec["mudados"],
        leitor=leitor,
        ensaiador=ensaiador,
        executor_isolado=exec_duble,
        sonda_entidade=lambda ch: ch in ativos,
        balde=balde,
        pasta_vereditos=pasta_ver,
    )
    return ver, balde, pasta_ver


@pytest.mark.parametrize(
    "spec",
    [
        {
            "cenario": "selecao_completa_do_push_verde",
            "arquivos": {
                "suite/codigo.py": "X = 1\n",
                "suite/testes/test_suite.py": (
                    "# componente: suite\n"
                    "import pytest\n"
                    "def test_comp_alcancado():\n    assert True\n"
                    "@pytest.mark.exige('olaria:olaria')\n"
                    "def test_exige_comp_alcancado():\n    assert True\n"
                ),
                "outro/testes/test_outro.py": (
                    "# componente: outro\n"
                    "import pytest\n"
                    "def test_comp_fora():\n    assert True\n"
                    "@pytest.mark.incidente(77)\n"
                    "def test_incidente_sempre_roda():\n    assert True\n"
                ),
                "outro/testes/test_fronteira.py": (
                    "# componente: outro\n"
                    "# verifica: interface:porta\n"
                    "def test_fronteira_sempre_roda():\n    assert True\n"
                ),
                "outro/testes/test_regra.py": (
                    "# componente: outro\n"
                    "# verifica: politica:0001\n"
                    "def test_regra_sempre_roda():\n    assert True\n"
                ),
            },
            "mudados": ["suite/codigo.py"],
            "servicos_ativos": {"olaria:olaria"},
            "roteiro_exec": {},
            "estado_esperado": "verde",
            "saida_esperada": 0,
            "rodados_esperados": (
                "outro/testes/test_fronteira.py::test_fronteira_sempre_roda",
                "outro/testes/test_outro.py::test_incidente_sempre_roda",
                "outro/testes/test_regra.py::test_regra_sempre_roda",
                "suite/testes/test_suite.py::test_comp_alcancado",
                "suite/testes/test_suite.py::test_exige_comp_alcancado",
            ),
            "debitos_esperados": (),
        },
        {
            "cenario": "servico_exigido_desligado_sai_nao_medido",
            "arquivos": {
                "suite/testes/test_suite.py": (
                    "# componente: suite\n"
                    "import pytest\n"
                    "@pytest.mark.exige('servico:fora')\n"
                    "def test_precisa_servico_fora():\n    assert True\n"
                ),
            },
            "mudados": ["suite/testes/test_suite.py"],
            "servicos_ativos": set(),
            "roteiro_exec": {},
            "estado_esperado": "nao-medido",
            "saida_esperada": 3,
            "rodados_esperados": (),
            "debitos_esperados": (),
        },
        {
            "cenario": "repositorio_sem_nenhum_teste_vinculado_sai_nao_medido",
            "arquivos": {"suite/codigo.py": "X = 1\n"},
            "mudados": ["suite/codigo.py"],
            "servicos_ativos": set(),
            "roteiro_exec": {},
            "estado_esperado": "nao-medido",
            "saida_esperada": 3,
            "rodados_esperados": (),
            "debitos_esperados": (),
        },
        {
            "cenario": "componente_alcancado_sem_verificacao_sai_nao_medido",
            "arquivos": {
                "outro/codigo.py": "Y = 2\n",
                "suite/testes/test_suite.py": "# componente: suite\ndef test_ok():\n    assert True\n",
            },
            "mudados": ["outro/codigo.py"],
            "servicos_ativos": set(),
            "roteiro_exec": {},
            "estado_esperado": "nao-medido",
            "saida_esperada": 3,
            "rodados_esperados": (),
            "debitos_esperados": (),
        },
        {
            "cenario": "incidente_quebrado_fora_do_alcance_abre_debito_sem_bloquear",
            "arquivos": {
                "suite/codigo.py": "X = 1\n",
                "suite/testes/test_suite.py": "# componente: suite\ndef test_ok():\n    assert True\n",
                "outro/testes/test_outro.py": (
                    "# componente: outro\n"
                    "import pytest\n"
                    "@pytest.mark.incidente(404)\n"
                    "def test_regressao_fora():\n    assert False\n"
                ),
            },
            "mudados": ["suite/codigo.py"],
            "servicos_ativos": set(),
            "roteiro_exec": {"outro/testes/test_outro.py::test_regressao_fora": False},
            "estado_esperado": "verde",
            "saida_esperada": 0,
            "rodados_esperados": (
                "outro/testes/test_outro.py::test_regressao_fora",
                "suite/testes/test_suite.py::test_ok",
            ),
            "debitos_esperados": ("incidente 404: outro/testes/test_outro.py::test_regressao_fora quebrou fora do alcance",),
        },
    ],
)
def test_esteira_selecao_e_julgamento_em_tabela(tmp_path: Path, spec: dict[str, Any]):
    from suite.esteira import ler_veredito

    ver, balde, pasta_ver = _executar_cenario_esteira(tmp_path, spec)

    assert ver.estado == spec["estado_esperado"]
    assert ver.codigo_saida == spec["saida_esperada"]
    assert tuple(sorted(ver.casos_rodados)) == spec["rodados_esperados"]
    assert ver.debitos_abertos == spec["debitos_esperados"]

    gravado = ler_veredito("repo-prova", arvore_mudanca="aaa1111", arvore_main="bbb2222", pasta=pasta_ver)
    assert gravado is not None
    assert gravado["estado"] == spec["estado_esperado"]

    spec_repetido = dict(spec)
    spec_repetido["balde"] = balde
    ver_segunda, _, _ = _executar_cenario_esteira(tmp_path, spec_repetido)
    assert ver_segunda.debitos_abertos == ()
    assert len(balde.listar_abertas()) == len(spec["debitos_esperados"])


@pytest.mark.parametrize(
    "spec_q",
    [
        {
            "cenario": "falha_e_passa_na_mesma_arvore_mede_erratico_e_entra_em_quarentena",
            "debitos_iniciais": [],
            "sequencia_exec": [False, True],
            "estado_esperado": "verde",
            "em_quarentena": ("suite/testes/test_suite.py::test_instavel",),
            "novo_debito_erratico": ("errático: suite/testes/test_suite.py::test_instavel",),
        },
        {
            "cenario": "quarentena_ativa_ate_30_dias_roda_sem_bloquear",
            "debitos_iniciais": [
                {
                    "numero": 10,
                    "idade_dias": 12,
                    "stack": "harness",
                    "texto": "errático: suite/testes/test_suite.py::test_instavel",
                }
            ],
            "sequencia_exec": [False],
            "estado_esperado": "verde",
            "em_quarentena": ("suite/testes/test_suite.py::test_instavel",),
            "novo_debito_erratico": (),
        },
        {
            "cenario": "quarentena_vencida_acima_de_30_dias_volta_a_bloquear",
            "debitos_iniciais": [
                {
                    "numero": 10,
                    "idade_dias": 31,
                    "stack": "harness",
                    "texto": "errático: suite/testes/test_suite.py::test_instavel",
                }
            ],
            "sequencia_exec": [False],
            "estado_esperado": "vermelho",
            "em_quarentena": (),
            "novo_debito_erratico": (),
        },
        {
            "cenario": "falha_em_todas_as_repeticoes_sem_medida_erratica_bloqueia",
            "debitos_iniciais": [],
            "sequencia_exec": [False, False, False],
            "estado_esperado": "vermelho",
            "em_quarentena": (),
            "novo_debito_erratico": (),
        },
    ],
)
def test_esteira_quarentena_erratico_e_prazo_em_tabela(tmp_path: Path, spec_q: dict[str, Any]):
    from suite.esteira import colocar_em_quarentena

    ver, balde, _ = _executar_cenario_esteira(
        tmp_path,
        {
            "cenario": spec_q["cenario"],
            "arquivos": {"suite/testes/test_suite.py": "# componente: suite\ndef test_instavel():\n    assert True\n"},
            "mudados": ["suite/testes/test_suite.py"],
            "debitos_iniciais": spec_q["debitos_iniciais"],
            "roteiro_exec": {"suite/testes/test_suite.py::test_instavel": spec_q["sequencia_exec"]},
        },
    )

    assert ver.estado == spec_q["estado_esperado"]
    assert ver.casos_quarentena == spec_q["em_quarentena"]
    assert ver.debitos_abertos == spec_q["novo_debito_erratico"]

    with pytest.raises(ValueError, match="sem medida de erraticidade"):
        colocar_em_quarentena(
            "suite/testes/test_suite.py::test_sempre_falha",
            passou=False,
            falhou=True,
            balde=balde,
        )


def test_coletor_servido_ignora_coletor_adulterado_no_ramo_e_cli_veredito(tmp_path: Path):
    from suite.esteira import DubleBalde, DubleExecutorIsolado, rodar

    arvore = tmp_path / "ramo_adulterado"
    pasta_suite = arvore / "outros_repos" / "harness" / "lib" / "suite"
    pasta_testes = pasta_suite / "testes"
    pasta_testes.mkdir(parents=True)
    (pasta_suite / "coletor.py").write_text(
        "def julgar_e_gravar(**kwargs):\n    raise RuntimeError('coletor do ramo nao deve rodar')\n",
        encoding="utf-8",
    )
    (pasta_testes / "test_suite.py").write_text(
        "# componente: suite\ndef test_quebra():\n    assert False\n",
        encoding="utf-8",
    )

    leitor = DubleLeitorOlaria(
        fichas=[
            {
                "classe": "componente",
                "chave": "componente:suite",
                "dados": {"caminho": "lib/suite"},
                "ligacoes": {"versionado-em": "repositorio:platafirma-harness"},
            }
        ]
    )
    ensaiador = DubleOlaria(fichas={"componente:suite": "componente"})
    pasta_ver = tmp_path / "vereditos_cli"

    ver = rodar(
        "platafirma-casa-espelho",
        arvore=arvore,
        mudanca="abc123456789",
        base="def987654321",
        arquivos_mudados=["outros_repos/harness/lib/suite/testes/test_suite.py"],
        leitor=leitor,
        ensaiador=ensaiador,
        executor_isolado=DubleExecutorIsolado(
            {"outros_repos/harness/lib/suite/testes/test_suite.py::test_quebra": [False, False, False]}
        ),
        balde=DubleBalde(),
        pasta_vereditos=pasta_ver,
    )

    assert ver.estado == "vermelho"
    assert ver.codigo_saida == 1

    proc_ver = _rodar_cli_suite(
        "veredito",
        "platafirma-casa-espelho",
        "--arvore",
        str(arvore),
        "--mudanca",
        "abc123456789",
        "--base",
        "def987654321",
        "--json",
        env_extra={"PF_ESTEIRA_VEREDITOS_DIR": str(pasta_ver)},
    )
    assert proc_ver.returncode == 1
    assert '"estado": "vermelho"' in proc_ver.stdout


@pytest.mark.filterwarnings("ignore::pytest.PytestUnknownMarkWarning")
@pytest.mark.exige("host:casa")
def test_esteira_isolamento_real_bloqueia_segredo_e_local_do_veredito(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from suite.esteira import DubleBalde, rodar

    arvore = tmp_path / "arvore_isolada"
    pasta = arvore / "suite" / "testes"
    pasta.mkdir(parents=True)
    pasta_ver = tmp_path / "vereditos_reais"
    pasta_ver.mkdir(parents=True)

    (pasta / "test_segredo.py").write_text(
        "# componente: suite\n"
        "import os\n"
        "from pathlib import Path\n\n"
        "def test_nao_alcanca_segredo_nem_veredito():\n"
        "    chave_env = os.environ.get('OLARIA_CHAVE')\n"
        "    cofre = Path('/srv/platafirma/casa/segredos/olaria/OLARIA_CHAVE')\n"
        f"    ver_dir = Path({str(pasta_ver)!r})\n"
        "    assert bool(chave_env) or cofre.exists() or ver_dir.exists()\n",
        encoding="utf-8",
    )

    leitor = DubleLeitorOlaria(
        fichas=[{"classe": "componente", "chave": "componente:suite", "dados": {"caminho": "suite"}}]
    )
    ensaiador = DubleOlaria(fichas={"componente:suite": "componente"})

    monkeypatch.setenv("OLARIA_CHAVE", "segredo-de-prova-nao-deve-vazar")
    ver = rodar(
        "repo-isolado",
        arvore=arvore,
        mudanca="12345678",
        base="87654321",
        arquivos_mudados=["suite/testes/test_segredo.py"],
        leitor=leitor,
        ensaiador=ensaiador,
        balde=DubleBalde(),
        pasta_vereditos=pasta_ver,
        max_repeticoes_erratico=0,
    )

    assert ver.estado == "vermelho"
    assert ver.codigo_saida == 1
    assert "suite/testes/test_segredo.py::test_nao_alcanca_segredo_nem_veredito" in ver.casos_reprovados


# --- Dublê de fronteira e verificação de quem fornece pelo contrato --------------------------

import json
import shutil

import httpx

from suite.contrato import (
    ContratoErro,
    VerificacaoContratoErro,
    ler_copia,
    trazer,
    verificar_fornecedor,
)
from suite.duble import gerar_duble

APOIO_DIR = Path(__file__).resolve().parent / "apoio"
CONTRATO_PROVA = APOIO_DIR / "interface-de-prova.yaml"


def _montar_arvore_fornecedor(tmp_path: Path, texto_yaml: str | None = None) -> tuple[Path, str]:
    arvore = tmp_path / "fornecedor"
    rel = "openapi/interface-de-prova.yaml"
    alvo = arvore / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    if texto_yaml is None:
        shutil.copy2(CONTRATO_PROVA, alvo)
    else:
        alvo.write_text(texto_yaml, encoding="utf-8")
    return arvore, rel


def _app_fornecedor_prova(*, violar_listar: bool = False):
    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        metodo = scope["method"].upper()
        caminho = scope["path"]
        if metodo == "GET" and caminho == "/itens":
            corpo = (
                {"itens": [{"id": "item-1"}], "proximo": None}
                if violar_listar
                else {"itens": [{"id": "item-1", "nome": "Exemplo"}], "proximo": None}
            )
            status = 200
        elif metodo == "POST" and caminho == "/itens":
            corpo = {"id": "item-2", "nome": "Novo item"}
            status = 201
        elif metodo == "GET" and caminho.startswith("/itens/"):
            item_id = caminho.split("/")[-1]
            corpo = {"id": item_id, "nome": "Exemplo"}
            status = 200
        else:
            corpo = {"type": "about:blank", "title": "NaoEncontrado"}
            status = 404
        raw = json.dumps(corpo).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(raw)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": raw})

    return app


def test_import_jsonschema_no_venv():
    import jsonschema

    assert hasattr(jsonschema, "Draft202012Validator")


def test_duble_responde_ao_contrato(tmp_path: Path):
    arvore, rel = _montar_arvore_fornecedor(tmp_path)
    destino = tmp_path / "consumidor" / "testes" / "contratos"
    res = trazer(arvore, rel, "1.0.0", destino=destino)
    assert res.mudou is True
    assert trazer(arvore, rel, "1.0.0", destino=destino).mudou is False

    app = gerar_duble(res.destino)
    with httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://duble") as cli:
        r_list = cli.get("/itens")
        assert r_list.status_code == 200
        assert r_list.json() == {"itens": [{"id": "item-1", "nome": "Exemplo"}], "proximo": None}

        r_post = cli.post("/itens", json={"nome": "Novo item"})
        assert r_post.status_code == 201
        assert r_post.json() == {"id": "item-2", "nome": "Novo item"}

        r_get = cli.get("/itens/item-1")
        assert r_get.status_code == 200
        assert r_get.json() == {"id": "item-1", "nome": "Exemplo"}

        r_422 = cli.post("/itens", json={})
        assert r_422.status_code == 422
        assert r_422.json()["title"] == "EntradaInvalida"

        r_404 = cli.get("/itens/item-1", headers={"x-duble-status": "404"})
        assert r_404.status_code == 404
        assert r_404.json()["title"] == "NaoEncontrado"

    res.destino.write_text(res.destino.read_text(encoding="utf-8") + "\n# adulterado\n", encoding="utf-8")
    with pytest.raises(ContratoErro, match="hash"):
        ler_copia(res.destino)


def test_verifica_quem_fornece(tmp_path: Path):
    arvore, rel = _montar_arvore_fornecedor(tmp_path)
    res = trazer(arvore, rel, "1.0.0", destino=tmp_path / "contratos")

    verificadas = verificar_fornecedor(res.destino, _app_fornecedor_prova(violar_listar=False))
    assert any("GET /itens" in op for op in verificadas)
    assert any("POST /itens" in op for op in verificadas)

    with pytest.raises(VerificacaoContratoErro, match=r"GET /itens"):
        verificar_fornecedor(res.destino, _app_fornecedor_prova(violar_listar=True))


def test_contrato_que_muda(tmp_path: Path):
    arvore, rel = _montar_arvore_fornecedor(tmp_path)
    destino = tmp_path / "consumidor" / "contratos"

    res_v1 = trazer(arvore, rel, "1.0.0", destino=destino)
    app_v1 = gerar_duble(res_v1.destino)

    def caso_consumidor(app_duble) -> None:
        with httpx.Client(transport=httpx.ASGITransport(app=app_duble), base_url="http://duble") as cli:
            dados = cli.get("/itens").json()
            assert dados["itens"][0]["nome"] == "Exemplo"

    caso_consumidor(app_v1)

    texto_v2 = (
        CONTRATO_PROVA.read_text(encoding="utf-8")
        .replace("version: 1.0.0", "version: 2.0.0")
        .replace("nome: Exemplo", "titulo: Exemplo")
        .replace("required: [id, nome]", "required: [id, titulo]")
        .replace("        nome:\n          type: string", "        titulo:\n          type: string")
    )
    (arvore / rel).write_text(texto_v2, encoding="utf-8")

    res_v2 = trazer(arvore, rel, "2.0.0", destino=destino)
    assert res_v2.mudou is True
    app_v2 = gerar_duble(res_v2.destino)
    assert app_v2.sha256 != app_v1.sha256

    with pytest.raises(KeyError, match="nome"):
        caso_consumidor(app_v2)


@pytest.mark.parametrize("versao_pedida", ["9.9.9", "2.5.0"])
def test_versao_nao_publicada_sai_1_e_nomeia(tmp_path: Path, versao_pedida: str):
    arvore, rel = _montar_arvore_fornecedor(tmp_path)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(LIB_RAIZ)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "suite.duble",
            "trazer",
            str(arvore),
            rel,
            versao_pedida,
            "--destino",
            str(tmp_path / "dest"),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 1
    assert versao_pedida in proc.stderr

