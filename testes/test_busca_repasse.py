# componente: componente:verbo-busca
"""Story 4427 (t1): repasse de `busca buscar` a `motor rag buscar` e recusa de ato de gestão do motor."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BIN = RAIZ / "bin" / "busca"
sys.path.insert(0, str(RAIZ / "lib"))

from leitura.recusa import CAMPOS  # noqa: E402

CODIGO_RECUSA_USO = 2
CODIGO_FALHA_DEP = 3


def _carregar_bin():
    carregador = importlib.machinery.SourceFileLoader("busca_bin_repasse", str(BIN))
    spec = importlib.util.spec_from_loader("busca_bin_repasse", carregador)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    carregador.exec_module(mod)
    return mod


busca = _carregar_bin()


def _motor_falso(tmp_path: Path) -> tuple[Path, Path]:
    """Motor falso que responde de forma determinística por pergunta, como bin/motor rag buscar."""
    gravado = tmp_path / "chamadas.jsonl"
    script = tmp_path / "motor_falso.py"
    script.write_text(
        textwrap.dedent(
            f"""\
            import json
            import sys
            from pathlib import Path

            arq = Path({str(gravado)!r})
            with arq.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(sys.argv[1:], ensure_ascii=False) + "\\n")

            argv = sys.argv[1:]
            if argv[:2] == ["rag", "buscar"]:
                pergunta = " ".join(argv[2:])
                if "--forcar-erro-3" in argv:
                    sys.stderr.write("motor: servico indisponivel\\n")
                    sys.exit(3)
                corpo = {{"fontes": [{{"n": 1, "trecho": f"achado para {{pergunta}}"}}], "cobertura": "boa"}}
                sys.stdout.write(json.dumps(corpo, ensure_ascii=False) + "\\n")
                sys.stderr.write("motor: particao padrao\\n")
                sys.exit(0)
            sys.stderr.write("chamada inesperada\\n")
            sys.exit(2)
            """
        ),
        encoding="utf-8",
    )
    return script, gravado


@pytest.mark.parametrize(
    "args_pergunta",
    [
        ["biblioteca", "governança de dados"],
        ["casa", "o que diz a política de acesso", "--top-k", "5"],
        ["qual é o prazo do verbo"],
    ],
)
def test_busca_buscar_devolve_exatamente_o_mesmo_que_motor_rag_buscar(
    tmp_path: Path, args_pergunta: list[str],
) -> None:
    motor, gravado = _motor_falso(tmp_path)
    env = {**os.environ, "PF_MOTOR": str(motor)}

    direto = subprocess.run(
        [sys.executable, str(motor), "rag", "buscar", *args_pergunta],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    repassado = subprocess.run(
        [sys.executable, str(BIN), "buscar", *args_pergunta],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )

    assert repassado.returncode == direto.returncode == 0
    assert repassado.stdout == direto.stdout
    assert repassado.stderr == direto.stderr
    chamadas = [json.loads(ln) for ln in gravado.read_text(encoding="utf-8").splitlines()]
    assert chamadas[-1] == ["rag", "buscar", *args_pergunta]


def test_busca_rag_buscar_aceita_forma_antiga_sem_duplicar_instancia(tmp_path: Path) -> None:
    motor, gravado = _motor_falso(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(["rag", "buscar", "biblioteca", "teste"], saida=out, erro=err, motor=motor)
    assert rc == 0
    chamadas = [json.loads(ln) for ln in gravado.read_text(encoding="utf-8").splitlines()]
    assert chamadas == [["rag", "buscar", "biblioteca", "teste"]]


def test_busca_buscar_propaga_codigo_de_saida_e_stderr_do_motor(tmp_path: Path) -> None:
    motor, _ = _motor_falso(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(["buscar", "biblioteca", "--forcar-erro-3"], saida=out, erro=err, motor=motor)
    assert rc == CODIGO_FALHA_DEP
    assert out.getvalue() == ""
    assert err.getvalue() == "motor: servico indisponivel\n"


def test_ato_de_gestao_do_motor_sai_2_com_chamada_pronta_em_proximo() -> None:
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(["ajuste", "peso_dominio", "0.4"], saida=out, erro=err)
    assert rc == CODIGO_RECUSA_USO
    assert out.getvalue() == ""
    corpo = json.loads(err.getvalue().splitlines()[-1])
    assert list(corpo["erro"]) == list(CAMPOS)
    assert corpo["erro"]["codigo"] == "ato-desconhecido"
    assert "motor" in corpo["erro"]["cura"]
    assert corpo["erro"]["proximo"] == "motor rag ajuste peso_dominio 0.4"
    assert corpo["erros"] == [corpo["erro"]]


def test_forma_antiga_rag_ajuste_tambem_sai_2_apontando_motor() -> None:
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(["rag", "ajuste"], saida=out, erro=err)
    assert rc == CODIGO_RECUSA_USO
    corpo = json.loads(err.getvalue().splitlines()[-1])
    assert corpo["erro"]["proximo"] == "motor rag ajuste"


def test_listar_do_motor_vai_sem_instancia_rag_em_proximo() -> None:
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(["listar"], saida=out, erro=err)
    assert rc == CODIGO_RECUSA_USO
    corpo = json.loads(err.getvalue().splitlines()[-1])
    assert corpo["erro"]["codigo"] == "ato-desconhecido"
    assert corpo["erro"]["proximo"] == "motor listar"


def test_ato_fora_do_busca_e_fora_do_motor_sai_2_sem_encaminhar_ao_motor() -> None:
    out, err = io.StringIO(), io.StringIO()
    rc = busca.main(["inexistente", "x"], saida=out, erro=err)
    assert rc == CODIGO_RECUSA_USO
    corpo = json.loads(err.getvalue().splitlines()[-1])
    assert corpo["erro"]["codigo"] == "ato-desconhecido"
    assert not corpo["erro"]["proximo"].startswith("motor ")
