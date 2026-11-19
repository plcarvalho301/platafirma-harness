"""Ordem de injeção, mesa, rotinas e consulta da abertura em `bin/expediente` (#3067, #3084, #3314, #3931)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_expediente import SCRIPT, _run_expediente, raiz_hermetica  # noqa: E402, F401


def test_ordem_prefixo_estavel_persona_conduta_contiguo_sem_chapeu(raiz_hermetica):  # noqa: F811
    """Passo 1 (#3067): persona e conduta são as duas primeiras peças, contíguas (sem chapéu)."""
    proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    pecas = d["pecas"]
    assert len(pecas) >= 2
    assert pecas[0]["peca"] == "persona"
    assert pecas[1]["peca"] == "conduta"


def test_ordem_persona_chapeu_conduta_com_chapeu(raiz_hermetica):  # noqa: F811
    """Spec expediente §2, §7 (#3146): com chapéu declarado, chapéu vem em 2º (entre persona e conduta)."""
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"],
        raiz_hermetica,
        stdin_data="pergunta",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "contexto"
    pecas = d["pecas"]
    assert len(pecas) >= 3
    assert pecas[0]["peca"] == "persona"
    assert pecas[1]["peca"] == "chapeu"
    assert pecas[2]["peca"] == "conduta"


def test_prefixo_byte_estavel_entre_aberturas(raiz_hermetica):  # noqa: F811
    """Passo 1 (#3067): aberturas seguidas produzem prefixo persona+conduta byte-idêntico."""
    proc1 = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    proc2 = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc1.returncode == 0
    assert proc2.returncode == 0
    d1 = json.loads(proc1.stdout)
    d2 = json.loads(proc2.stdout)
    p1 = d1["pecas"][:2]
    p2 = d2["pecas"][:2]
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


def test_mesa_recebe_chapeu_resolvido(raiz_hermetica):  # noqa: F811
    """Passo 2 (#3067): chapéu resolvido antes da mesa -> mesa ver <chapeu>."""
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "contexto"
    peca_mesa = next(p for p in d["pecas"] if p["peca"] == "mesa")
    assert peca_mesa["ref"] == "verbo:mesa ver contexto"


def test_mesa_sem_chapeu_fail_to_inteiro(raiz_hermetica):  # noqa: F811
    """Passo 2 (#3067): sem chapéu resolvido -> mesa ver (mesa inteira / fail-to-inteiro)."""
    proc = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        stdin_data="pergunta sem rotulo",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert "chapeu" not in d and "roteador" not in d
    peca_mesa = next(p for p in d["pecas"] if p["peca"] == "mesa")
    assert peca_mesa["ref"] == "verbo:mesa ver"


def test_alias_cadeiras_logo_apos_conduta_sem_chapeu(raiz_hermetica):  # noqa: F811
    proc = _run_expediente(
        ["montar", "--json"], raiz_hermetica, stdin_data="pergunta sem rotulo",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    pecas = json.loads(proc.stdout)["pecas"]
    assert [p["peca"] for p in pecas[:3]] == ["persona", "conduta", "alias-cadeiras"]


def test_conduta_logo_apos_chapeu(raiz_hermetica):  # noqa: F811
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"], raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    pecas = json.loads(proc.stdout)["pecas"]
    assert [p["peca"] for p in pecas[:4]] == ["persona", "chapeu", "conduta", "alias-cadeiras"]


def test_a_consulta_da_abertura_manda_origem_abertura_ao_motor(raiz_hermetica):  # noqa: F811
    log_motor = raiz_hermetica / "motor.log"
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"], raiz_hermetica, stdin_data="pergunta com busca",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin"),
                   "STUB_MOTOR_LOG": str(log_motor)},
    )
    assert proc.returncode == 0
    assert "--origem abertura" in log_motor.read_text()
    peca = next(p for p in json.loads(proc.stdout)["pecas"] if p["peca"] == "acervo-consultado")
    assert peca["ref"].endswith("--k 6 --texto secao --origem abertura")


def test_sem_chapeu_declarado_a_abertura_nao_roteia_nem_consulta_o_acervo(raiz_hermetica):  # noqa: F811
    """O roteador do stub casaria `contexto` nesta pergunta. Sem chapéu declarado ele não roda, o motor
    não é chamado e o pacote tem as seis peças, sem chave de chapéu nem de roteador."""
    log_motor = raiz_hermetica / "motor.log"
    proc = _run_expediente(
        ["montar", "--json"], raiz_hermetica, stdin_data="pergunta sobre janela de contexto",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin"),
                   "STUB_MOTOR_LOG": str(log_motor)},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert not log_motor.exists()
    assert "chapeu" not in d and "roteador" not in d
    assert [p["peca"] for p in d["pecas"]] == ["persona", "conduta", "alias-cadeiras", "mesa"]


def test_com_chapeu_declarado_a_abertura_segue_como_sempre_foi(raiz_hermetica):  # noqa: F811
    """Ordem do dono (21/10/2026, #4377): o chapéu declarado traz o chapéu, a mesa dele e a consulta ao acervo."""
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"], raiz_hermetica, stdin_data="pergunta com busca",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "contexto" and d["roteador"]["via"] == "comando"
    assert [p["peca"] for p in d["pecas"]] == ["persona", "chapeu", "conduta", "alias-cadeiras", "mesa",
                                               "acervo-consultado"]
    refs = {p["peca"]: p["ref"] for p in d["pecas"]}
    assert refs["mesa"] == "verbo:mesa ver contexto"
    assert "cadernos" not in refs


def test_texto_so_traz_a_linha_de_chapeu_e_roteador_com_chapeu_declarado(raiz_hermetica):  # noqa: F811
    env = {"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")}
    sem = _run_expediente(["montar"], raiz_hermetica, env_extra=env)
    com = _run_expediente(["montar", "--chapeu", "contexto"], raiz_hermetica, env_extra=env)
    assert "roteador:" not in sem.stdout and "chapeu: contexto   roteador: comando" in com.stdout


def test_a_consulta_da_abertura_do_perfil_cadeirinha_tambem_declara_a_origem():
    from importlib.machinery import SourceFileLoader
    from importlib.util import module_from_spec, spec_from_loader

    spec = spec_from_loader("expediente_sob_teste", SourceFileLoader("expediente_sob_teste", str(SCRIPT)))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    linha = next(l for l in mod.CATALOGO_CADEIRINHA if l["peca"] == "acervo-consultado")
    assert linha["chamada"].endswith("--origem abertura")
    assert next(l for l in mod.CATALOGO if l["peca"] == "acervo-consultado")["chamada"].endswith(
        "--origem abertura")
