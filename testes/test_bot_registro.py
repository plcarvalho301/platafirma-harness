"""O cabecalho de bin/bot se registra no golden record (card #3186).

Um verbo so entra em `verbos_servidos` da porta depois de `acervo registrar <verbo>`, que le o cabecalho por
chave e recusa `# le:`/`# escreve:` fora da forma `<ato>=<recurso>`. Hermetico: o psql e um duble que guarda o SQL.
Prova a gramatica do registrar (capacidade, atos, uma linha de acesso por ato com recurso do enum, ambiente sem
parentese aninhado) e o whitelist do oficio. Nao prova que o psql real aceita (FK de recurso), nem que o verbo
aparece no tools/list.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("registrar", str(REPO_ROOT / "bin" / "_acervo" / "registrar"))
spec = importlib.util.spec_from_loader("registrar", loader)
assert spec and spec.loader
registrar = importlib.util.module_from_spec(spec)
loader.exec_module(registrar)

sys.path.insert(0, str(REPO_ROOT / "lib"))
import uso

BOT = REPO_ROOT / "bin" / "bot"
ATOS = {"declarar": "escrita", "listar": "leitura", "rodar": "escrita", "desligar": "escrita", "caidas": "escrita"}
# os 11 ids de acervo.ferramental_recurso (047): a FK reprova qualquer outro
RECURSOS = {"acervo.obra", "acervo.casa", "acervo.registro", "acervo.*", "release", "repo", "rastreador", "malha",
            "motor", "arquivo-local", "nada"}
AMBIENTE = {"MOTOR_ACERVO_URL", "RAG_API_URL", "RAG_API_BASE", "RAG_TIMEOUT_S", "RAG_API_TOKEN", "PF_CADEIRA",
            "PF_SESSAO", "PF_ORDEM_ID", "PF_SUJEITO", "PF_BIN", "PF_UNITS_DIR", "XDG_DATA_HOME", "PLATAFIRMA_RELEASE",
            "PF_RELEASE_RAIZ", "HOME", "XDG_RUNTIME_DIR", "PF_BOT_SLUGS"}


@pytest.fixture
def sql(monkeypatch):
    enviados: list[str] = []
    monkeypatch.setattr(registrar, "_psql", lambda s, escreve=False: enviados.append(s) or "")
    cap, desc = registrar.registrar_um("bot")
    return cap, desc, "".join(enviados)


def test_capacidade_e_descricao_saem_do_cabecalho(sql):
    cap, desc, _ = sql
    assert cap == "agendamento", "a folha existe no acervo (068); conferir verbo a resolve"
    assert desc.startswith("a camada acima do systemd") and "use para: automação" in desc
    assert "atos: declarar (escrita, agendamento), listar (leitura, agendamento)" in desc


@pytest.mark.parametrize("ato,op", ATOS.items())
def test_cada_ato_entra_com_a_acao_e_a_folha(sql, ato, op):
    assert f"'bot', '{ato}', 'agendamento', '{op}', 'agendamento'" in sql[2]


def test_o_acesso_de_cada_ato_e_declarado_com_recurso_do_enum(sql):
    texto = sql[2]
    acessos = re.findall(r"into acervo\.ferramental_acesso \(verbo, ato, recurso_id, modo\) values \('bot', '(\w+)', '([^']+)', '(le|escreve)'\)", texto)
    assert acessos, "o registrar leu as linhas `# le:` e `# escreve:`"
    assert {r for _, r, _ in acessos} <= RECURSOS
    for ato in ATOS:
        assert {m for a, _, m in acessos if a == ato} == {"le", "escreve"}, f"{ato}: uma linha le e uma escreve"
    assert "'bot', 'listar', 'nada', 'escreve'" in texto
    assert "'bot', 'declarar', 'arquivo-local', 'escreve'" in texto and "'bot', 'declarar', 'acervo.registro', 'escreve'" in texto
    assert "'bot', 'caidas', 'rastreador', 'escreve'" in texto
    assert "'bot', 'desligar', 'arquivo-local', 'escreve'" in texto and "'bot', 'rodar', 'acervo.registro', 'escreve'" in texto


def test_o_ambiente_sai_sem_parentese_aninhado_e_so_com_o_que_o_verbo_le(sql):
    texto = sql[2]
    vistas = set(re.findall(r"into acervo\.ferramental_ambiente \(verbo, variavel, obrigatoria, origem\) values \('bot', '([A-Z0-9_]+)'", texto))
    assert vistas == AMBIENTE, "parentese aninhado ou palavra solta em maiuscula criaria variavel que o verbo nao le"
    assert "'bot', 'PF_CADEIRA', false" in texto and "'bot', 'RAG_API_TOKEN', false" in texto
    assert "'bot', 'PF_BIN', false" in texto
    linha = next(x for x in BOT.read_text().splitlines() if x.startswith("# ambiente:"))
    assert linha.count("(") == linha.count(")") and "((" not in linha


def test_o_cabecalho_passa_o_gate_de_tres_linhas_e_a_ajuda_le_os_cinco_atos():
    linhas = BOT.read_text().splitlines()
    assert linhas[0].startswith("#!/opt/platafirma/current/venv/harness/bin/python")
    assert linhas[1].startswith("# bot — "), "proposito: segunda linha com ' — '"
    chaves = {x.split(":", 1)[0] for x in linhas[:80] if x.startswith("# ") and ":" in x}
    assert {"# capacidade", "# dono", "# classe", "# forma", "# atos", "# exit", "# ambiente"} <= chaves
    assert "# dono: ti" in linhas and "# classe: B" in linhas
    bloco = next(i for i, x in enumerate(linhas) if not x.startswith("#"))      # o bloco contiguo de `#` do topo
    assert bloco < 80, "o registrar le so as 80 primeiras linhas"
    assert uso.atos_do_cabecalho(BOT) == list(ATOS)


def test_o_oficio_tem_o_bot_no_bloco_e_cada_ato_citado_na_prosa_esta_no_cabecalho():
    texto = (REPO_ROOT / "abertura" / "oficio-ferramental.md").read_text()
    bloco = texto.split("```")[1].split()
    assert "bot" in bloco and bloco.index("bot") == bloco.index("agente") + 1
    citados = set(re.findall(r"`bot (\w+)`", texto))
    assert citados and citados <= set(ATOS), f"ato citado fora do `# atos:`: {citados - set(ATOS)}"
