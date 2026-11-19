# componente: componente:verbo-lint
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

import pytest

RAIZ = Path(__file__).resolve().parents[1]
# só o código desta árvore: a release servida em /opt é a casa velha, e o teste que a importa
# passa na fita sem provar o componente e cai na esteira, que não monta /opt
for _p in (RAIZ / "lib", RAIZ / "bin"):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_pypath_partes = [str(p) for p in (RAIZ / "bin", RAIZ / "lib") if p.exists()]
if os.environ.get("PYTHONPATH"):
    _pypath_partes.append(os.environ["PYTHONPATH"])
os.environ["PYTHONPATH"] = os.pathsep.join(_pypath_partes)

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
- [O ciclo inteiro, da lapidação à formalização, no guia discovery](https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/guia/discovery.md): quem conduz escreve o two-pager, as cadeiras comentam com tipo, o dono valida e aposta, a cadeira dona formaliza.
- [O comentário, tipo a tipo, com o fecho, na spec comentario-tipado](https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/spec/comentario-tipado.md): o que cada cadeira escreve no parecer, e quando ele está fechado.
Peças:
1. [#3411 — guia discovery, skill prosa, styleguide e lista de verificação](https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/guia/discovery.md) (Peças 1, 2, 4 e 6 da aposta)
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
- [spec comentario-tipado](https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/spec/comentario-tipado.md) · produto, #3413
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


def test_dt701_story_no_molde_nao_cobra_onde_nem_passos():
    corpo = (
        "# Escrever a regra no verbo\n"
        "#4288 · story · priorizada\n"
        "Negócio: #10\n"
        "Referencial: spec x\n"
        "Raio de ataque: bin/y · muda: z\n"
        "Comportamento esperado: quando chama, devolve 0\n"
        "Travas: nenhuma\n"
        "Ambiente: bancada local\n"
        "Entrega: ramo main\n"
        "Aceite: pytest -> 1 passed\n"
    )
    aps, *_ = verificar_card_regua("#4288", texto=corpo, lista=LISTA, fecha_existe=False)
    assert aps == []


def test_feature_cita_a_lista_e_a_rev():
    _, chave, rev, _ = verificar_card_regua("#3408", texto=CARD_3408, comentarios="",
                                            lista=LISTA, fecha_existe=True)
    assert chave == CHAVE_DISCOVERY and rev == 2


# ------------------------------------------------------------------ tasks no lugar da lista (#4223, R41)

def _story_com_lista(rotulo, estado="em-execucao"):
    return f"#1 · story · {estado}\nNegócio: #2\n{rotulo}:\n1. fazer x · repo@a · pytest\n"


@pytest.mark.parametrize("rotulo", ["Tarefas", "Unidades"])
def test_story_com_tarefas_ou_unidades_no_corpo_avisa(rotulo):
    aps, *_ = verificar_card_regua("#1", texto=_story_com_lista(rotulo), lista=LISTA,
                                   fecha_existe=False)
    achados = [a for a in aps if a.id == f"CARD_{rotulo.upper()}_NO_CORPO"]
    assert len(achados) == 1
    assert achados[0].severidade == "aviso" and "--nivel task --pai <story>" in achados[0].cura
    assert achados[0].linha == 3


def test_story_sem_lista_no_corpo_nao_avisa():
    aps, *_ = verificar_card_regua("#1", texto="#1 · story · em-execucao\nNegócio: #2\n", lista=LISTA,
                                   fecha_existe=False)
    assert not any(a.id.endswith("_NO_CORPO") for a in aps)


def test_story_entregue_com_lista_e_historico_e_nao_avisa():
    aps, *_ = verificar_card_regua("#1", texto=_story_com_lista("Tarefas", "entregue"), lista=LISTA,
                                   fecha_existe=False)
    assert not any(a.id.endswith("_NO_CORPO") for a in aps)


def test_story_de_prova_em_arquivo_sem_estado_avisa():
    aps, *_ = verificar_card_regua("x.md", texto="Negócio: #2\nTarefas:\n1. fazer x\n", lista=LISTA,
                                   fecha_existe=False)
    assert "CARD_TAREFAS_NO_CORPO" in _ids(aps)


def test_task_pede_onde_e_confere_e_nao_o_debito_antigo():
    aps, *_ = verificar_card_regua("#9", texto="#9 · task · priorizada\nOnde: repo@a\n", lista=LISTA,
                                   fecha_existe=False)
    ids = _ids(aps)
    assert "CARD_CONFERE" in ids and "CARD_ONDE" not in ids
    assert "CARD_PROBLEMA ENCONTRADO" not in ids


# ------------------------------------------------------------------ titulo (#3887)

def _story_com_titulo(titulo):
    return f"# {titulo}\n#1 · story · captada\nNegócio: #2\n"


def test_titulo_acima_de_60_avisa_em_story():
    aps, *_ = verificar_card_regua("#1", texto=_story_com_titulo("x" * 61), lista=LISTA,
                                   fecha_existe=False)
    titulo = [a for a in aps if a.id == "CARD_TITULO"]
    assert len(titulo) == 1
    assert "61 caracteres" in titulo[0].o_que_fere
    assert "rótulo onde se clica" in titulo[0].cura
    assert titulo[0].severidade == "aviso"


def test_titulo_no_teto_nao_avisa():
    aps, *_ = verificar_card_regua("#1", texto=_story_com_titulo("é" * 60), lista=LISTA,
                                   fecha_existe=False)
    assert "CARD_TITULO" not in _ids(aps)


def test_sem_linha_de_titulo_nao_avisa():
    aps, *_ = verificar_card_regua("#1", texto="#1 · story · captada\nNegócio: #2\n",
                                   lista=LISTA, fecha_existe=False)
    assert "CARD_TITULO" not in _ids(aps)


def test_titulo_acima_de_60_avisa_em_feature():
    aps, chave, *_ = verificar_card_regua("#3408", texto=CARD_3408, comentarios="",
                                          lista=LISTA, fecha_existe=True)
    assert chave == CHAVE_DISCOVERY
    assert "CARD_TITULO" in _ids(aps)


@pytest.mark.parametrize(("titulo", "trecho"), [
    ("Ajustar F4 no lint de card", "F4"),
    ("Cobrir H2 na conferência", "H2"),
    ("Reconhecer compose em AP8", "AP8"),
    ("Conferir critério (C1) nos comentários", "C1"),
    ("Adequar molde à arq:0096", "arq:0096"),
    ("Formalizar minuta 0037 no verbo", "minuta 0037"),
    ("Corrigir regressão do #3103", "#3103"),
    ("Alinhar §5 da spec do verbo", "§5"),
])
def test_titulo_com_codigo_opaco_avisa(titulo, trecho):
    aps, *_ = verificar_card_regua("#1", texto=_story_com_titulo(titulo), lista=LISTA,
                                   fecha_existe=False)
    cod = [a for a in aps if a.id == "CARD_TITULO_CODIGO"]
    assert len(cod) == 1
    assert f"«{trecho}»" in cod[0].o_que_fere
    assert "código mora no corpo" in cod[0].cura
    assert cod[0].severidade == "aviso"


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
                              "(https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/guia/discovery.md)",
                              "- O ciclo inteiro").replace(
        "- [O comentário, tipo a tipo, com o fecho, na spec comentario-tipado]"
        "(https://github.com/plcarvalho301/platafirma-casa-espelho/blob/main/spec/comentario-tipado.md)",
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


def test_f4_reconhece_fecho_em_negrito_gravado_pelo_rastreador():
    # DT 354: `tarefas comentar --fecha` grava `**fecho:** <Resultado> — <destino>` no fim do
    # comentário; F4 não pode apontar esses comentários como abertos (caso real #3602).
    com = ("--- #2928 · produto · x ---\nrequisito: barra das portas\nConfere: prova 8\n"
           "**fecho:** Aceito — peças 2 e 8 e Apetite do corpo; a aba foi à spec da Taipa\n\n"
           "--- #2929 · produto · x ---\nburaco: duas regras\nCaso: spec taipa\nRemendo: linha\n"
           "**fecho:** Remendado — linha na Solução e na peça 9\n\n"
           "--- #3065 · arquiteto · x ---\ndecisão (dono): apostar e formalizar\nDescartado: -\n"
           "**fecho:** Formalizada — arq:0124 §3; spec taipa R57 a R60\n")
    aps, _ = _rodar(CARD_3408, com)
    assert "F4" not in _ids(aps)
    assert "F2" not in _ids(aps)


def test_l1_l2():
    longa = " ".join(["palavra"] * 45) + "."
    corpo = CARD_3408.replace("Sai quando: toda frente", "Sai quando: " + longa + " toda frente")
    ids = _ids(_rodar(corpo)[0])
    assert {"L1", "L2"} <= ids


def test_barra_escapada_na_celula_nao_corta_a_coluna():
    linha_c1 = ("| C1 | comentário sem tipo | padrao | primeira linha não casa "
                "`^(insumo\\|pergunta\\|buraco)[: ]` | aviso | Etiquete a primeira linha com o tipo. |")
    lista = parse_lista(LISTA_TXT.replace("| C1 | comentário sem tipo | padrao | regex | aviso | Etiquete. |",
                                          linha_c1))
    c1 = next(i for i in lista["itens"] if i["id"] == "C1")
    assert c1["cura"] == "Etiquete a primeira linha com o tipo."
    assert "insumo|pergunta|buraco" in c1["detector"]


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

# ------------------------------------------------------------------ T10 sem Quebra (emenda de 15/10/2026)

def test_t10_feature_com_filha_e_pecas_ainda_numeradas():
    base = ("#5 · feature · em-parecer\nProblema: p\nSolução:\n- Ao abrir: o dono lê.\n"
            "Peças:\n1. a peça\nFora: f\nResultado: r\nMedida: m\n")
    sem_filha = base + "\nfilhas (nenhuma):\n"
    assert "T10" not in _ids(_rodar(sem_filha)[0])
    com_filha = base + "\nfilhas (abertas):\n  #10\tem-execucao\tengenharia\ta story\n"
    assert "T10" in _ids(_rodar(com_filha)[0])

# ------------------------------------------------------------------ Regras (emenda de 21/10/2026, #3937)

def _feature_com_regras(regras):
    return ("# feature de prova\n#5 · feature · em-parecer\nProblema: p\nSolução:\n- Ao abrir: o dono lê.\n"
            "Peças:\n1. a peça\nFora: f\nResultado: r\nMedida: m\n" + regras + "Sai quando: s\n")


def test_regras_e_secao_propria_e_nao_cai_na_anterior():
    s = secoes_do_corpo(_feature_com_regras("Produtos documentais:\n- d\nRegras:\n1. a → b · R1\n"))
    assert "a → b" not in s["Produtos documentais"].texto()
    assert "a → b" in s["Regras"].texto() and "Sai quando" not in s["Regras"].texto()


def test_regras_no_corpo_da_feature_nao_avisam_durante_a_troca():
    # story #4317: as regras da feature foram ao inventário; a feature que ainda as traz no corpo
    # não é apontada por elas, nem pela linha sem R ou D
    corpo = _feature_com_regras("Regras:\n1. obra com esboço → vale o esboço · R3 da spec x\n"
                                "2. pergunta fechada → a story entra\n3. caso → resultado · D2 da arq:0096\n")
    aps, *_ = verificar_card_regua("#5", texto=corpo, comentarios="", lista=LISTA, fecha_existe=True)
    assert "CARD_REGRAS" not in _ids(aps)


# ------------------------------------------------------------------ a feature na forma da classe (story #4317)

def _feature_da_classe(estado="em-parecer", extra=""):
    return (f"# feature de prova\n#5 · feature · {estado}\nProblema: p\nServe a: s\n"
            "Solução:\n- Ao abrir: o dono lê.\nFora: f\nSai quando: a conferida · lendo · dar certo\n"
            "Apetite: duas fitas\n" + extra)


def _ids_da_feature(corpo, comentarios=""):
    aps, *_ = verificar_card_regua("#5", texto=corpo, comentarios=comentarios, lista=LISTA, fecha_existe=True)
    return aps


def test_feature_da_classe_nao_tem_rotulo_ausente():
    assert "T1" not in _ids(_ids_da_feature(_feature_da_classe()))


def test_feature_cobra_os_rotulos_da_classe_e_nao_os_de_antes():
    so_problema = "# feature de prova\n#5 · feature · em-parecer\nProblema: p\nFora: f\n"
    faltam = {a.o_que_fere.split("[")[1] for a in _ids_da_feature(so_problema) if a.id == "T1"}
    assert faltam == {"rótulo «Serve a:» ausente]", "rótulo «Sai quando:» ausente]",
                      "rótulo «Apetite:» ausente]", "rótulo «Solução:» ausente]"}


def test_feature_com_as_tres_secoes_no_corpo_nao_e_apontada_por_elas():
    extra = ("Peças:\n- uma peça sem número\nRegras:\n1. caso → resultado\n"
             "Produtos documentais:\n- a spec [x](https://exemplo.test/spec)\n")
    aps = _ids_da_feature(_feature_da_classe(extra=extra) + "\nfilhas (abertas):\n  #10\tpriorizada\tengenharia\tstory\n")
    sobre_elas = [a for a in aps if a.id in {"T6", "T10", "CARD_REGRAS"}]
    assert sobre_elas == []


def test_o_epico_segue_na_regua_de_antes():
    epico = "#5 · épico · em-parecer\nProblema: x\nResultado: y\nMedida: m\nFora: f\n"
    aps, *_ = verificar_card_regua("#5", texto=epico, comentarios="", lista=LISTA, fecha_existe=True)
    assert {a.o_que_fere.split("[")[1] for a in aps if a.id == "T1"} == \
        {"rótulo «Solução:» ausente]", "rótulo «Peças:» ausente]"}


def test_buraco_com_mais_de_um_paragrafo_avisa():
    longo = ("--- #1 · dados · 2026-11-17 ---\nburaco: a solução quebra\nCaso: platafirma-x@a.py\n"
             "Remendo: um detalhe\n\nprimeiro parágrafo do argumento\n\nsegundo parágrafo\n")
    curto = ("--- #2 · dados · 2026-11-17 ---\nburaco: a solução quebra\nCaso: platafirma-x@a.py\n"
             "Remendo: um detalhe\n\num parágrafo só\ncom duas linhas\n\n**fecho:** Remendado — Solução\n")
    aps = _ids_da_feature(_feature_da_classe(), longo + curto)
    avisos = [a for a in aps if a.id == "CARD_BURACO_PARAGRAFOS"]
    assert len(avisos) == 1 and "#1" in avisos[0].arquivo and avisos[0].severidade == "aviso"


def test_regra_com_caminho_sai_t5():
    aps, _ = _rodar(_feature_com_regras("Regras:\n1. `logica.py` recusa → sai 400 · R1\n"))
    assert any(a.id == "T5" and "Regras" in a.o_que_fere for a in aps)


def test_t10_nao_le_mais_quebra():
    base = ("#5 · feature · em-parecer\nProblema: p\nSolução:\n- Ao abrir: o dono lê.\n"
            "Peças:\n1. a peça\nFora: f\nResultado: r\nMedida: m\n")
    # Quebra com numero de card, mas sem a filha real (sem o bloco que tarefas ler acrescenta):
    # a emenda de 15/10/2026 tira a Quebra da leitura do T10, so a filha de verdade conta.
    com_quebra_sem_filha = base + "Quebra: 11/10/2026\n1. #10 — a story\n"
    assert "T10" not in _ids(_rodar(com_quebra_sem_filha)[0])


# ------------------------------------------------------------------ lint de árvore da casa (card #4255)

def _carregar_arvore():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_lint.arvore", RAIZ / "bin" / "_lint" / "arvore.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["_lint.arvore"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _git_init(raiz: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=raiz, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=raiz, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=raiz, check=True)


def _gravar(raiz: Path, rel: str, texto: str = "# Título\n") -> None:
    p = raiz / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def test_arvore_valida_passa_sem_apontamentos(tmp_path):
    arvore = _carregar_arvore()
    _git_init(tmp_path)
    _gravar(tmp_path, "instancias/cultura/da-casa.md", "# Cultura da casa\n")
    _gravar(tmp_path, "instancias/registro-de-decisao/0138-natureza.md", "# 0138\n")
    _gravar(tmp_path, "referencias/classes/cultura.md", "# Cultura\n")
    _gravar(tmp_path, "referencias/instancias/cultura/da-casa.md", "# Ref\n")
    _gravar(tmp_path, "verbetes/estrato/formal.md", "# Formal\n")
    _gravar(tmp_path, "outros_repos/conhecimento/README.md", "# ok\n")

    formas = {
        "cultura": {"golden": "instancias/cultura/<slug>.md", "referencia": "referencias/classes/cultura.md"},
        "registro-de-decisao": {"golden": "instancias/registro-de-decisao/<numero>-<trecho>.md"},
    }
    fichas = {("cultura", "da-casa"), ("registro-de-decisao", "0138")}
    dicionarios = {"estrato": {"formal"}}

    aps = arvore.verificar_arvore(tmp_path, formas=formas, fichas=fichas, dicionarios=dicionarios)
    assert aps == []


def test_arvore_cobra_regras_da_adr_0138(tmp_path):
    arvore = _carregar_arvore()
    _git_init(tmp_path)
    _gravar(tmp_path, "1-formal/casa/casa.md")
    _gravar(tmp_path, "solto.md")
    _gravar(tmp_path, "verbetes/classes/cultura.md")
    _gravar(tmp_path, "instancias/cultura/cultura.md")
    _gravar(tmp_path, "instancias/cultura/sem-ficha.md")
    _gravar(tmp_path, "referencias/classes/fantasma.md")
    _gravar(tmp_path, "referencias/instancias/cultura/sem-ficha.md")
    _gravar(tmp_path, "instancias/registro-de-decisao/0138-natureza.md", "# 0139 errado\n")

    formas = {
        "cultura": {"golden": "instancias/cultura/<slug>.md"},
        "registro-de-decisao": {"golden": "instancias/registro-de-decisao/<numero>-<trecho>.md"},
    }
    fichas = {("registro-de-decisao", "0138")}

    aps = arvore.verificar_arvore(tmp_path, formas=formas, fichas=fichas)
    ids = {a.id for a in aps}
    assert "ARVORE_RAIZ" in ids
    assert "ARVORE_TIPO" in ids
    assert "ARVORE_REGRA_13" in ids
    assert "ARVORE_ORIGINAL_DA_CLASSE" in ids
    assert "ARVORE_SEM_FICHA" in ids
    assert "ARVORE_CLASSE" in ids
    assert "ARVORE_NUMERO" in ids


def test_arvore_sem_formas_sai_indeterminavel(tmp_path):
    arvore = _carregar_arvore()
    with pytest.raises(ValueError) as exc:
        arvore.verificar_arvore(tmp_path)
    assert exc.value.args[0] == 5
