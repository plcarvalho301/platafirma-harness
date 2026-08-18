"""Contrato de `bin/monta-sessao --json` — o verbo PYTHON da fase 5 do #189.

SUBSTITUI o arquivo homônimo anterior, que foi APAGADO e não consertado. O
anterior testava o `monta-sessao` BASH e afirmava, entre outras coisas,
`dados["fila"]["disponivel"]`. As duas premissas morreram: o verbo virou Python
na fase 5, e a fila saiu da abertura inteira por ordem do dono (harness 2ef6e19,
17/08). Contrato que descreve outra geração não se conserta — 17 falhas
vermelhas há dias treinam quem roda a suíte a ler o vermelho como ruído de
fixture, que é pior do que não ter teste.

O QUE ESTE ARQUIVO GARANTE, e só isto: o formato que o `ops-server` e as três
superfícies consomem. Ele roda o verbo DE VERDADE, com `--sem-atualizar` para
não depender de rede, contra o `~/AI` real. Não é teste hermético e não tenta
ser: o valor aqui é pegar mudança de formato antes de ela chegar à abertura de
sessão de alguém.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess

import pytest

VERBO = pathlib.Path(
    os.environ.get("PF_RAIZ", pathlib.Path.home() / "AI")
) / "platafirma-harness" / "bin" / "monta-sessao"

CHAVES_DA_PECA = {"peca", "dono", "ref", "sha", "regime", "tokens", "frescor"}


def monta(*args: str) -> tuple[int, str, str]:
    p = subprocess.run([str(VERBO), *args], capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


@pytest.fixture(scope="module")
def pacote() -> dict:
    if not VERBO.exists():
        pytest.skip(f"verbo ausente: {VERBO}")
    code, out, err = monta("TI", "--json", "--sem-atualizar")
    assert code == 0, f"exit {code}, stderr: {err[:400]}"
    return json.loads(out)


def test_pecas_e_lista_em_ordem_de_injecao(pacote):
    """O pacote é CATÁLOGO DE PEÇAS, não uma chave por artefato (#189 fase 5)."""
    assert isinstance(pacote["pecas"], list) and pacote["pecas"], "pecas vazia ou ausente"


def test_toda_peca_declara_as_sete_chaves(pacote):
    """A tool documenta {peca, dono, ref, sha, regime, tokens, frescor}. Quem consome
    o pacote conta com elas em TODA peça — inclusive na que falhou."""
    for p in pacote["pecas"]:
        faltando = CHAVES_DA_PECA - set(p)
        assert not faltando, f"peça {p.get('peca')!r} sem {sorted(faltando)}"


def test_peca_indisponivel_vem_declarada_e_nao_omitida(pacote):
    """Pacote sem a peça e pacote com peça vazia seriam indistinguíveis. Peça que
    falta vem com frescor 'indisponivel' e motivo — nunca sumindo da lista."""
    for p in pacote["pecas"]:
        if p["frescor"] == "indisponivel":
            assert p.get("motivo"), f"peça {p['peca']!r} indisponível sem motivo"


def test_a_fila_nao_entra_na_abertura(pacote):
    """Ordem do dono, 17/08: a abertura carrega IMPEDIMENTO, e a caixa não é. Não há
    peça de fila, não há envelope, não há contagem. Este teste existe porque a
    regressão já aconteceu uma vez e voltou."""
    assert "fila" not in pacote, "a fila voltou para o pacote de abertura"
    assert not [p for p in pacote["pecas"] if "fila" in p["peca"]], "peça de fila no catálogo"


def test_a_mesa_entra_na_abertura(pacote):
    """O par do teste anterior: a mesa é o único impedimento hoje, e some sem ninguém
    notar se a peça deixar de ser servida."""
    assert [p for p in pacote["pecas"] if p["peca"] == "mesa"], "mesa fora do catálogo"


def test_pacote_declara_a_propria_conta(pacote):
    """`pacote` é a conta do que foi servido: sem ela, teto estourado é invisível."""
    conta = pacote["pacote"]
    assert conta["pecas"] == len(pacote["pecas"]), "conta de peças diverge da lista"
    assert isinstance(conta["tokens"], int) and conta["tokens"] > 0
    assert conta.get("metodo_tokens"), "medição sem método declarado"


def test_cadeira_desconhecida_devolve_a_lista_valida(pacote):
    """Falha declarada, nunca muda: quem errou o nome recebe a lista de volta.

    DIVERGÊNCIA DE NOME, medida em 18/08 e travada aqui como está: o verbo emite
    `cadeiras_validas` e o `ops-server` normaliza para `cadeiras` antes de entregar
    à tool (`r.setdefault("cadeiras", _cadeiras())`). São dois nomes para a mesma
    coisa, e quem lê a saída crua do verbo não recebe o nome documentado. Este teste
    trava o contrato DE HOJE — a unificação é mudança de contrato e sai em card
    próprio, não numa correção de teste."""
    code, out, _ = monta("nao-existe-esta-cadeira", "--json", "--sem-atualizar")
    r = json.loads(out)
    assert "erro" in r, "cadeira desconhecida sem objeto de erro"
    assert r.get("cadeiras_validas"), "cadeira desconhecida sem lista de válidas"
    assert code != 0, "cadeira desconhecida saiu com exit 0"


def test_prefixo_de_persona_e_aceito_e_descartado():
    """`claudinho-TI` e `TI` são a mesma cadeira — o prefixo é rótulo, a chave é o slug."""
    code, out, _ = monta("claudinho-TI", "--json", "--sem-atualizar")
    assert code == 0
    assert json.loads(out)["nome_canonico"] == "claudinho-TI"
