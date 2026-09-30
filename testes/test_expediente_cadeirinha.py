"""`expediente montar --perfil cadeirinha` (spec cadeirinha §3-§5, card #3158).

O que se trava: o pacote de quem trabalha por delegacao NAO traz a conduta (Aceite do card), nem
alias-cadeiras nem mesa; traz a lente (persona, chapeu), o molde do modo, as rotinas, a regua quando
vem, o acervo consultado e o caderno; combinacao invalida e exit 2 com a lista do que vale; a
cadeira vem da sessao, nunca de argumento; o perfil `cadeira` segue como era.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_expediente import (  # noqa: E402  (stubs e runner do montador, sem os testes dele)
    MESA_STUB, PERSONA_STUB, ROTEADOR_STUB, _executavel, _run_expediente,
)

ORIGEM = "11111111-1111-4111-8111-111111111111"

ACERVO_STUB = """#!/bin/sh
if [ "$*" = "listar casa guia --mapa" ]; then echo "ROTINAS (stub)"; exit 0; fi
if [ "$1 $2 $3" = "ler casa modo" ]; then
  if [ "${STUB_ACERVO_MODO:-ok}" = "falha" ]; then echo "acervo: fora do ar (stub)" >&2; exit 3; fi
  if [ "$4" = "revisar" ]; then echo "# modo revisar (stub)"; echo "O que faz: revisa."; exit 0; fi
  echo "nao-existe: modo $4 (stub)" >&2; exit 1
fi
if [ "$1 $2 $3" = "ler casa lista-de-verificacao" ]; then
  if [ "$4" = "ilegivel" ]; then echo "nao-existe: $4 (stub)" >&2; exit 1; fi
  cat <<'EOF'
# lista de verificacao (stub)
## Como se lê
regra geral que nao entra
## Critérios
| id | criterio |
| A1 | README existe |
### subtitulo dentro de Critérios
| A2 | README cabe em 100 linhas |
## Contrapontos
**A1** — pasta sem manifesto nao leva README
## Curas
cura que nao entra
## Rodapé
nota que nao entra
EOF
  exit 0
fi
if [ "$1 $2 $3" = "ler casa padrao" ]; then echo "# padrao inteiro (stub)"; echo "## Qualquer"; echo "corpo do padrao"; exit 0; fi
echo "stub acervo: chamada inesperada '$*'" >&2
exit 2
"""

MOTOR_ARGS_STUB = """#!/bin/sh
for a in "$@"; do echo "$a" >> "$STUB_MOTOR_LOG"; done
echo '{"fontes": [{"n": 1, "obra": "casa/doc.md", "section_id": "s1"}], "cobertura": "alta", "contexto": "trecho (stub)", "sinal": {"valor": 0.8, "piso": 0.5}}'
"""


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    raiz = tmp_path / "raiz"
    bin_dir = raiz / "bin"
    (bin_dir / "_expediente").mkdir(parents=True)
    for caminho, texto in ((bin_dir / "persona", PERSONA_STUB), (bin_dir / "mesa", MESA_STUB),
                           (bin_dir / "acervo", ACERVO_STUB), (bin_dir / "motor", MOTOR_ARGS_STUB),
                           (bin_dir / "_expediente" / "rotear", ROTEADOR_STUB)):
        caminho.write_text(texto, encoding="utf-8")
        _executavel(caminho)
    return raiz


def _env(raiz: Path, **extra) -> dict:
    return {"PF_CADEIRA": "ia", "PF_BIN": str(raiz / "bin"), "PF_ORIGEM_SESSAO": ORIGEM,
            "STUB_MOTOR_LOG": str(raiz / "motor.log"), **extra}


def _monta(raiz, *args, stdin="", **env):
    return _run_expediente(["montar", "--perfil", "cadeirinha", "--chapeu", "contexto",
                            "--modo", "revisar", *args, "--json"], raiz, stdin_data=stdin,
                           env_extra=_env(raiz, **env))


def _pecas(proc) -> list[str]:
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return [p["peca"] for p in json.loads(proc.stdout)["pecas"]]


# ---------------------------------------------------------------- o pacote
def test_o_pacote_nao_traz_conduta_nem_alias_nem_mesa(raiz):
    pecas = _pecas(_monta(raiz, stdin="revise o README"))
    for fora in ("conduta", "alias-cadeiras", "mesa"):
        assert fora not in pecas
    assert pecas == ["persona", "chapeu", "modo", "rotinas", "acervo-consultado", "cadernos"]


def test_o_envelope_diz_perfil_modo_e_nao_roteia(raiz):
    d = json.loads(_monta(raiz).stdout)
    assert (d["perfil"], d["modo"], d["regua"], d["chapeu"]) == ("cadeirinha", "revisar", None, "contexto")
    assert d["roteador"]["via"] == "comando", "quem chama sabe o que pede: o roteador nao roda"
    assert d["cadeira"] == "ia"


def test_sem_mensagem_ou_com_sem_acervo_nao_consulta_o_acervo(raiz):
    assert "acervo-consultado" not in _pecas(_monta(raiz))
    assert "acervo-consultado" not in _pecas(_monta(raiz, "--sem-acervo", stdin="algo"))
    assert not (raiz / "motor.log").exists()


def test_a_mensagem_de_delegacao_vai_inteira_num_so_argumento(raiz):
    msg = 'revise o "README" do posto; `ls` $HOME | rm'
    assert "acervo-consultado" in _pecas(_monta(raiz, stdin=msg))
    argumentos = (raiz / "motor.log").read_text().splitlines()
    assert msg in argumentos, "texto livre nao passa por shlex nem por shell"


def test_o_modo_chega_pelo_documento_da_casa(raiz):
    d = json.loads(_monta(raiz).stdout)
    modo = next(p for p in d["pecas"] if p["peca"] == "modo")
    assert modo["ref"] == "verbo:acervo ler casa modo revisar"
    assert "O que faz: revisa." in modo["conteudo"]


# ---------------------------------------------------------------- a regua
def test_lista_de_verificacao_entra_so_com_criterios_e_contrapontos(raiz):
    d = json.loads(_monta(raiz, "--regua", "lista-de-verificacao", "readme").stdout)
    assert [p["peca"] for p in d["pecas"]][3:5] == ["rotinas", "regua"], "a regua vem depois das rotinas"
    regua = next(p for p in d["pecas"] if p["peca"] == "regua")["conteudo"]
    assert "A1 | README existe" in regua and "A2 | README cabe" in regua
    assert "**A1** — pasta sem manifesto" in regua
    for fora in ("Como se lê", "regra geral", "Curas", "nota que nao entra"):
        assert fora not in regua
    assert d["regua"] == ["lista-de-verificacao", "readme"]


def test_padrao_como_regua_segue_inteiro(raiz):
    d = json.loads(_monta(raiz, "--regua", "padrao", "readme").stdout)
    regua = next(p for p in d["pecas"] if p["peca"] == "regua")["conteudo"]
    assert "corpo do padrao" in regua and "## Qualquer" in regua


def test_regua_que_nao_le_nao_e_exit_a_peca_sai_indisponivel(raiz):
    proc = _monta(raiz, "--regua", "lista-de-verificacao", "ilegivel")
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    regua = next(p for p in d["pecas"] if p["peca"] == "regua")
    assert regua["frescor"] == "indisponivel" and regua["conteudo"] is None
    assert any("`regua` indisponível" in a for a in d["avisos"])


# ---------------------------------------------------------------- combinacao invalida: exit 2
@pytest.mark.parametrize("args, frase", [
    (["--perfil", "cadeirinha", "--modo", "revisar"], "exige --chapeu"),
    (["--perfil", "cadeirinha", "--chapeu", "contexto"], "exige --modo"),
    (["--perfil", "cadeirinha"], "exige --chapeu e --modo"),
    (["--modo", "revisar", "--chapeu", "contexto"], "so valem com --perfil cadeirinha"),
    (["--regua", "padrao", "readme"], "so valem com --perfil cadeirinha"),
    (["--perfil", "cadeirinha", "--chapeu", "contexto", "--modo", "inventado"], "modos: varrer, revisar"),
    (["--perfil", "cadeirinha", "--chapeu", "contexto", "--modo", "varrer", "--regua", "padrao", "x"],
     "so vale em revisar e avaliar"),
    (["--perfil", "cadeirinha", "--chapeu", "contexto", "--modo", "revisar", "--regua", "adr", "x"],
     "especies: lista-de-verificacao, padrao"),
    (["--perfil", "cadeirinha", "--chapeu", "invalido", "--modo", "revisar"], "fora do vocabulário"),
    (["--perfil", "cadeirinha", "--chapeu", "contexto", "--modo", "testar"], "sem documento na casa"),
])
def test_combinacao_invalida_sai_2_com_a_lista_do_que_vale(raiz, args, frase):
    proc = _run_expediente(["montar", *args], raiz, env_extra=_env(raiz))
    assert proc.returncode == 2, proc.stdout
    assert frase in proc.stderr


def test_modo_sem_documento_na_casa_sai_2_em_json(raiz):
    proc = _run_expediente(["montar", "--perfil", "cadeirinha", "--chapeu", "contexto",
                            "--modo", "varrer", "--json"], raiz, env_extra=_env(raiz))
    assert proc.returncode == 2
    assert "sem documento na casa" in json.loads(proc.stdout)["erro"]


def test_cadeira_por_argumento_e_recusada_a_cadeira_vem_da_sessao(raiz):
    proc = _run_expediente(["montar", "outra", "--perfil", "cadeirinha", "--chapeu", "contexto",
                            "--modo", "revisar"], raiz, env_extra=_env(raiz))
    assert proc.returncode == 2
    assert "vem da sessao" in proc.stderr


def test_sem_cadeira_na_sessao_sai_3(raiz):
    proc = _monta(raiz, PF_CADEIRA="")
    assert proc.returncode == 3
    assert "sem cadeira" in json.loads(proc.stdout)["erro"]


def test_acervo_fora_do_ar_nao_e_modo_sem_documento(raiz):
    proc = _monta(raiz, STUB_ACERVO_MODO="falha")
    assert proc.returncode == 0, "exit 3 do acervo e dependencia fora, nao 'nao existe'"
    modo = next(p for p in json.loads(proc.stdout)["pecas"] if p["peca"] == "modo")
    assert modo["frescor"] == "indisponivel"


# ---------------------------------------------------------------- a sessao propria
def test_sessao_sem_origem_avisa_e_com_origem_fica_calado(raiz):
    sem = json.loads(_monta(raiz, PF_ORIGEM_SESSAO="").stdout)
    assert any("sem origem_sessao" in a for a in sem["avisos"])
    com = json.loads(_monta(raiz).stdout)
    assert not any("origem_sessao" in a for a in com["avisos"])


# ---------------------------------------------------------------- o que nao mudou
def test_perfil_cadeira_segue_igual_e_nao_ganha_campos(raiz):
    proc = _run_expediente(["montar", "--json"], raiz, env_extra=_env(raiz))
    d = json.loads(proc.stdout)
    assert "conduta" in [p["peca"] for p in d["pecas"]]
    assert "perfil" not in d and "modo" not in d


def test_catalogo_por_perfil_e_o_padrao_segue_com_8(raiz):
    cad = json.loads(_run_expediente(["catalogo", "--json"], raiz).stdout)
    assert len(cad) == 8 and "conduta" in [p["peca"] for p in cad]
    cdi = json.loads(_run_expediente(["catalogo", "--perfil", "cadeirinha", "--json"], raiz).stdout)
    assert [p["peca"] for p in cdi] == ["persona", "chapeu", "modo", "rotinas", "regua",
                                        "acervo-consultado", "cadernos"]
    assert "conduta" not in [p["peca"] for p in cdi]


def test_texto_traz_a_linha_do_perfil(raiz):
    proc = _run_expediente(["montar", "--perfil", "cadeirinha", "--chapeu", "contexto", "--modo", "revisar",
                            "--regua", "padrao", "readme"], raiz, env_extra=_env(raiz))
    assert proc.returncode == 0
    assert "perfil: cadeirinha   modo: revisar   regua: padrao readme" in proc.stdout
