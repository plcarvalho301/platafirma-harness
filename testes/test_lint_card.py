"""lint card pela lista antipadroes-de-discovery (card #3421).

Caso real: o corpo e comentarios do #3408 como `tarefas ler` e `tarefas comentarios` os
serviam em 11/10/2026. Prova minima do card: o #3408 deixa de ser apontado por falta de
Continuidade, e um buraco sem Remendo sai como C2.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "bin"))

from _lint.card import (
    CHAVE_ADR,
    CHAVE_DISCOVERY,
    conferir_discovery,
    detectar_nivel,
    ler_comentarios,
    secoes_do_corpo,
    verificar_card_regua,
)
from _lint.lista import parse_lista

# a lista como o acervo a serve, so o que o lint le: id, antipadrao, detector, cura
LISTA_TXT = """força não declarada · vigente — lista-de-verificacao antipadroes-de-discovery · Antipadrões
# Antipadrões de discovery

Espécie: lista-de-verificacao
Rev: 2

## Critérios

| # | antipadrão | lei da casa | detector | severidade | cura |
|---|---|---|---|---|---|
| T1 | rótulo obrigatório ausente | arq:0096 | rótulos | aviso | Rode tarefas modelo. |
| T2 | Medida em mais de uma linha | arq:0096 | linhas > 1 | aviso | Uma linha. |
| T3 | número no Problema | arq:0096 | dígito | aviso | Mova o número. |
| T4 | momento sem momento nem pessoa | guia | abertura | aviso | Abra pelo momento. |
| T5 | instrução técnica no corpo | arq:0096 | caminho | aviso | Leve à story. |
| T6 | Peças sem número | guia | N. | aviso | Numere. |
| T7 | regra nova sem cobrador | guia | leitura | aviso | Diga quem cobra. |
| T8 | Fora que proíbe | guia | proibido | aviso | Vira decisão. |
| T9 | Aberto sem dono na aposta | guia | cadeira | aviso | Nomeie. |
| T10 | forma em texto depois do destino | guia | link | aviso | Troque pelo link. |
| C1 | comentário sem tipo | padrao | regex | aviso | Etiquete. |
| C2 | buraco sem remendo | guia | Remendo | aviso | Proponha o remendo. |
| C3 | requisito sem conferir | padrao | Confere | aviso | Diga o comando. |
| C4 | decisão sem quem decidiu | padrao | parênteses | aviso | Nomeie quem. |
| C5 | fecho fora do lugar | padrao | fecho | aviso | Fecho na última linha. |
| C6 | temas diferentes | padrao | leitura | aviso | Parta. |
| C7 | buraco sem medida | guia | Caso | aviso | Aponte onde. |
| L1 | parede de texto | padrao | 400 | aviso | Quebre. |
| L2 | frase longa demais | padrao | 40 | aviso | Parta. |
| L3 | ponteiro nu | padrao | código | aviso | Diga o nome. |
| L4 | jargão sem nome comum | padrao | glossário | aviso | Ponha o nome. |
| L5 | prosa ilegível | padrao | leitura | aviso | Entregue a alguém. |
| F1 | derivado sem card | guia | Procedência | aviso | Ponha a linha. |
| F2 | fecho sem destino | guia | formalizada | aviso | Diga onde. |
| F3 | story derivada sem o que atende | guia | Negócio | aviso | Aponte. |
| F4 | formalização com aberto | guia | aberto | aviso | Feche. |
| F5 | Fontes fora da forma | padrao | três partes | aviso | Escreva. |
| F6 | origem no corpo | arq:0075 | seção | aviso | Leve ao card. |
"""
LISTA = parse_lista(LISTA_TXT)

CARD_3408 = """# O card descreve a solução, e a formalização gera os documentos e as stories
#3408 · feature · em-execucao [derivado; cru: Em lapidação (funil)] · cadeira: produto
  em: #3365 Rastreador: discovery até a aposta, um delivery na ordem do dono, reparo direto e deliberação no card

Problema: na hora de validar, o dono recebe listas, não um texto que descreva a solução. O card de feature tem problema e efeito, a minuta empilha posições, e a solução não tem onde entrar. Na minuta 0046 a seção Decisão misturava spec, ADR, lint e emenda; no épico #3365, a lapidação foram quatro comentários, cada um emendando o anterior. E as cadeiras já lapidam no molde novo sem nada formalizado: a engenharia foi ao two-pager por conta própria, e o tarefas modelo, a ADR 0096 e a skill prosa ainda ensinam o molde velho.
Solução:
- [O ciclo inteiro, da lapidação à formalização, no guia discovery](https://github.com/plcarvalho301/platafirma-casa/blob/main/guia/discovery.md): quem conduz escreve o two-pager, as cadeiras comentam com tipo, o dono valida e aposta, a cadeira dona formaliza.
- [O comentário, tipo a tipo, com o fecho, na spec comentario-tipado](https://github.com/plcarvalho301/platafirma-casa/blob/main/spec/comentario-tipado.md): o que cada cadeira escreve no parecer, e quando ele está fechado.
Peças:
1. [#3411 — guia discovery, skill prosa, styleguide e lista de verificação](https://github.com/plcarvalho301/platafirma-casa/blob/main/guia/discovery.md) (Peças 1, 2, 4 e 6 da aposta)
2. #3412 — emendas à arq:0096 e à arq:0075, Card e Fontes em ADR e spec (Peças 1 e 5)
3. #3413 — spec do comentário tipado (Peças 2 e 3)
4. #3410 — tarefas modelo, fechar comentário e recusa da API por transição (Peças 1, 2, 5 e a parte de recusa da 7)
A Peça 7, nos cobradores que faltam (comentário sem tipo, saída do parecer com aberto, derivado sem card), é da F3.
Fora:
- A tela que mostra comentários e tipos: F4.
- O mecanismo dos tipos no rastreador, os cobradores por transição e o verbo que confere a formalização: F3.
Resultado: o dono valida lendo um texto que descreve a solução, mais só o que está aberto. Cada cadeira contribui com um tema por vez, e cada contribuição fecha no próprio comentário. Outcome, não fecha card: a deliberação some do chat e fica no rastreador.
Medida: frentes apostadas com two-pager no corpo e nenhum comentário aberto · consulta no rastreador · hoje 0 · mínimo todas.
Apetite: quatro fitas de execução, uma por story já criada; não cabendo, a lista de verificação espera a F3 · previsão de produto, 11/10/2026.
Aberto:
- Fica aberto de propósito: se o rastreador guarda as versões anteriores do corpo do card.
Produtos documentais:
- [spec comentario-tipado](https://github.com/plcarvalho301/platafirma-casa/blob/main/spec/comentario-tipado.md) · produto, #3413
Sai quando: toda frente nova nasce no two-pager e as cadeiras comentam com tipo.
Quebra: 11/10/2026, pela decisão do dono no comentário #2075.
1. #3411 · documento · produto — guia discovery, skill prosa, styleguide e lista de verificação (entregue)
2. #3412 · documento · arquiteto — emendas à arq:0096 e à arq:0075 (entregue)
A F5 vai primeiro no épico e não espera a 0046 (comentário #2074 do #3365).

filhas (abertas):
  #3421\tem-execucao\tarquiteto\tlint card confere o two-pager e o comentário tipado
"""

COMENTARIOS_3408 = """--- #2075 · gestao-estrategica · 2026-10-11 14:48:51.868184+00:00 ---
Decisão do dono no chat (gestão estratégica, 11/10/2026): a #3410 é a última da F5.

--- #2076 · produto · 2026-10-11 15:23:10.946636+00:00 ---
decisão (dono): pesquisa e ideação saem do Fora da F5
No chat de 11/10/2026, com produto.
Descartado: manter no Fora a «etapa própria de pesquisa e ideação».
fecho: formalizada — guia discovery, seção «As etapas»

--- #2078 · produto · 2026-10-11 15:23:11.051128+00:00 ---
insumo: levantamento 2026-10-11-moldes-do-discovery-e-da-formalizacao
Traz: os seis moldes da F5 um a um.

--- #2100 · produto · 2026-10-11 22:17:38.069695+00:00 ---
fecho #2077: formalizada — D1 da arq:0096 (Apetite opcional, previsão de quem escreve)

--- #2129 · gestao-estrategica · 2026-10-12 02:24:39.802872+00:00 ---
Conferência da gestão estratégica, 11/10/2026, sobre o Sai quando.
Passa: guia discovery servido.
"""


def _ids(apontamentos):
    return {a.id for a in apontamentos}


def _rodar(texto, comentarios="", *, fecha=True):
    return conferir_discovery("#3408", texto, ler_comentarios(comentarios), LISTA,
                              estado="em-execucao", fecha_existe=fecha)


# ------------------------------------------------------------------ nivel e regua

def test_nivel_pelo_cabecalho_e_nao_pelo_titulo():
    assert detectar_nivel("# a task que vira story\n#9 · feature · captada\n") == "feature"
    assert detectar_nivel("#9 · épico · captada\n") == "epic"


def test_story_segue_a_arq_0096():
    corpo = "#1 · story · captada\nNegócio: #2\n"
    aps, chave, rev, _ = verificar_card_regua("#1", texto=corpo, lista=LISTA, fecha_existe=False)
    assert chave == CHAVE_ADR and rev == 1
    assert "CARD_AMBIENTE" in _ids(aps)


def test_feature_cita_a_lista_e_a_rev():
    _, chave, rev, _ = verificar_card_regua("#3408", texto=CARD_3408, comentarios="",
                                            lista=LISTA, fecha_existe=True)
    assert chave == CHAVE_DISCOVERY and rev == 2


# ------------------------------------------------------------------ prova minima

def test_3408_nao_e_apontado_por_continuidade():
    aps, _ = _rodar(CARD_3408, COMENTARIOS_3408)
    assert not [a for a in aps if "Continuidade" in a.o_que_fere]
    assert "T1" not in _ids(aps)


def test_buraco_sem_remendo_sai_c2():
    com = ("--- #9 · engenharia · 2026-10-11 ---\n"
           "buraco: o momento 2 quebra contra o verbo\n"
           "Caso: platafirma-harness@bin/tarefas:575\n")
    aps, _ = _rodar(CARD_3408, com)
    assert "C2" in _ids(aps)
    assert "C7" not in _ids(aps)


# ------------------------------------------------------------------ o 3408 real

def test_3408_aponta_o_que_a_conferencia_previu():
    aps, avisos = _rodar(CARD_3408, COMENTARIOS_3408)
    por = {}
    for a in aps:
        por.setdefault(a.id, []).append(a.arquivo)
    assert por["C1"] == ["#3408 comentário #2075"]          # sem tipo
    assert por["C5"] == ["#3408 comentário #2100"]          # fecho próprio com --fecha no ar
    assert all("#2129" not in arq for v in por.values() for arq in v)  # conferência é delivery
    assert "L3" in por                                     # (comentário #2074 do #3365) e afins
    assert any("L4" in v for v in avisos)                  # sem detector: dito, não calado
    assert not {"T7", "C6", "L5"} & set(por)               # leitura fica fora


def test_c5_sem_fecha_no_ar_nao_aponta_fecho_proprio():
    aps, _ = _rodar(CARD_3408, COMENTARIOS_3408, fecha=False)
    assert "C5" not in _ids(aps)


# ------------------------------------------------------------------ criterios um a um

def test_t1_estado_captada_so_pede_a_aposta():
    corpo = "#5 · feature · Captada (funil)\nProblema: x\nResultado: y\nMedida: m\nFora: f\n"
    aps = conferir_discovery("#5", corpo, [], LISTA, estado="Captada (funil)")[0]
    assert "T1" not in _ids(aps)
    aps = conferir_discovery("#5", corpo, [], LISTA, estado="em-parecer")[0]
    assert {a.o_que_fere.split("[")[1] for a in aps if a.id == "T1"} == \
        {"rótulo «Solução:» ausente]", "rótulo «Peças:» ausente]"}


def test_t1_rotulo_de_fontes():
    aps, _ = _rodar(CARD_3408 + "Base: levantamento x\n")
    assert "T1" in _ids(aps)


def test_t2_t3_t6_t8():
    corpo = ("#5 · feature · em-parecer\nProblema: hoje 40% dos cards, desde 11/10, no #12 e na arq:0096\n"
             "Solução:\n- Ao abrir: o dono lê.\nPeças:\n- sem número\nFora:\n- nunca a tela\n"
             "Resultado: r\nMedida: a\nb\n")
    aps, _ = _rodar(corpo)
    ids = _ids(aps)
    assert {"T2", "T3", "T6", "T8"} <= ids
    t3 = [a for a in aps if a.id == "T3"]
    assert len(t3) == 1 and "40%" in t3[0].o_que_fere


def test_t4_infinitivo_aponta_momento_nao():
    corpo = ("#5 · feature · em-parecer\nProblema: p\nSolução:\n- Ao abrir: o dono lê.\n"
             "- Escrever o card.\n- Quando fecha: some.\nPeças:\n1. a\nFora: f\nResultado: r\nMedida: m\n")
    aps, _ = _rodar(corpo)
    assert [a.linha for a in aps if a.id == "T4"] == [5]


def test_t5_link_nao_conta_crase_conta():
    aps, _ = _rodar(CARD_3408)
    assert "T5" not in _ids(aps)
    aps, _ = _rodar(CARD_3408.replace("Sai quando: toda", "Sai quando: `tarefas ler` e toda"))
    assert "T5" in _ids(aps)


def test_t9_so_na_aposta():
    corpo = CARD_3408.replace("Aberto:\n", "Aberto:\n- se a tela mostra o tipo\n")
    aps, _ = _rodar(corpo)
    assert "T9" not in _ids(aps)
    aposta = "--- #7 · produto · x ---\ndecisão (dono): apostar e formalizar\nDescartado: nada\n"
    aps, _ = _rodar(corpo, aposta)
    assert "T9" in _ids(aps)


def test_t10_solucao_sem_link_com_spec_servida():
    corpo = CARD_3408.replace("- [O ciclo inteiro, da lapidação à formalização, no guia discovery]"
                              "(https://github.com/plcarvalho301/platafirma-casa/blob/main/guia/discovery.md)",
                              "- O ciclo inteiro").replace(
        "- [O comentário, tipo a tipo, com o fecho, na spec comentario-tipado]"
        "(https://github.com/plcarvalho301/platafirma-casa/blob/main/spec/comentario-tipado.md)",
        "- O comentário")
    aps, _ = _rodar(corpo)
    assert "T10" in _ids(aps)


def test_c3_c4_c7_f2():
    com = ("--- #1 · ti · x ---\nrequisito: recusar entrada vazia\n\n"
           "--- #2 · ti · x ---\ndecisão: sem quem\n\n"
           "--- #3 · ti · x ---\nburaco: quebra\nCaso: no uso do dono\nRemendo: corta\n\n"
           "--- #4 · ti · x ---\npergunta: existe?\nfecho: aceito — num lugar qualquer\n")
    ids = _ids(_rodar(CARD_3408, com)[0])
    assert {"C3", "C4", "C7", "F2"} <= ids


def test_c5_fecho_no_meio_e_em_insumo():
    com = ("--- #1 · ti · x ---\npergunta: existe?\nfecho: respondida — Solução\nmais texto\n\n"
           "--- #2 · ti · x ---\ninsumo: x\nTraz: y\nfecho: aceito — R1\n")
    c5 = [a for a in _rodar(CARD_3408, com)[0] if a.id == "C5"]
    assert {a.arquivo for a in c5} == {"#3408 comentário #1", "#3408 comentário #2"}


def test_f4_aberto_com_aposta_e_fecho_proprio_conta():
    com = ("--- #1 · ti · x ---\npergunta: existe?\n\n"
           "--- #2 · ti · x ---\nburaco: b\nCaso: spec tarefas\nRemendo: r\n\n"
           "--- #3 · gestao · x ---\nfecho #2: remendado — Solução\n\n"
           "--- #4 · produto · x ---\ndecisão (dono): apostar e formalizar\nDescartado: -\n")
    f4 = [a for a in _rodar(CARD_3408, com, fecha=False)[0] if a.id == "F4"]
    assert [a.arquivo for a in f4] == ["#3408 comentário #1"]


def test_l1_l2():
    longa = " ".join(["palavra"] * 45) + "."
    corpo = CARD_3408.replace("Sai quando: toda frente", "Sai quando: " + longa + " toda frente")
    ids = _ids(_rodar(corpo)[0])
    assert {"L1", "L2"} <= ids


def test_secoes_param_na_lista_de_filhas():
    s = secoes_do_corpo(CARD_3408)
    assert "filhas" not in s["Quebra"].texto()


# ------------------------------------------------------------------ pela porta

def _exe(caminho: Path, corpo: str):
    caminho.write_text(corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)


def test_cli_com_numero_le_o_rastreador(tmp_path):
    (tmp_path / "ler.txt").write_text(CARD_3408, encoding="utf-8")
    (tmp_path / "com.txt").write_text(COMENTARIOS_3408, encoding="utf-8")
    (tmp_path / "lista.txt").write_text(LISTA_TXT, encoding="utf-8")
    _exe(tmp_path / "tarefas",
         f"#!/bin/sh\n[ \"$1\" = ler ] && cat {tmp_path}/ler.txt && exit 0\n"
         f"[ \"$1\" = comentarios ] && cat {tmp_path}/com.txt && exit 0\nexit 2\n")
    _exe(tmp_path / "acervo", f"#!/bin/sh\ncat {tmp_path}/lista.txt\n")
    env = dict(os.environ, PF_LINT_TAREFAS=str(tmp_path / "tarefas"),
               PF_LINT_ACERVO=str(tmp_path / "acervo"), PF_LINT_FECHA="1")
    proc = subprocess.run([sys.executable, str(RAIZ / "bin" / "lint"), "card", "3408", "--json"],
                          capture_output=True, text=True, env=env, timeout=60, check=False)
    assert proc.returncode == 1, proc.stderr
    saida = json.loads(proc.stdout)
    assert saida["ancora"].startswith("«lint card #3408: ")
    assert saida["ancora"].endswith("— antipadroes-de-discovery@rev2»")
    assert "L4 tem detector na lista" in proc.stderr
    assert all(a["severidade"] == "aviso" for a in saida["apontamentos"])


def test_cli_rastreador_fora_sai_5(tmp_path):
    _exe(tmp_path / "tarefas", "#!/bin/sh\necho fora >&2\nexit 3\n")
    env = dict(os.environ, PF_LINT_TAREFAS=str(tmp_path / "tarefas"))
    proc = subprocess.run([sys.executable, str(RAIZ / "bin" / "lint"), "card", "#3408"],
                          capture_output=True, text=True, env=env, timeout=60, check=False)
    assert proc.returncode == 5
