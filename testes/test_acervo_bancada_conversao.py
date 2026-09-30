"""#3187: `acervo listar obra bancada <pasta>` — o agregador perfil x docling, sem rede e sem banco.

Pastas sintéticas com relatorio.json (relatório v1 do contrato) exercitam a regra escrita pelo
card #3181 ANTES de rodar: chave = (perda, irrecuperável, inserção, duplicação, ordem), menor
vence, igual empata; falha do método = perda igual ao tamanho_referencia; teste do sinal exato
por tipo amostrado. Os p-valores abaixo foram conferidos à mão (binomial(n, 1/2), contas no
comentário).

Estados de cada LADO (método) de uma obra, nesta precedência (B7):
pendente > n/a (método não cobre o tipo) > n/a (sem referência) > falha do método > medida
indeterminada > medido.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MODULO = RAIZ / "bin" / "_acervo" / "bancada_conversao.py"
LISTAR = RAIZ / "bin" / "_acervo" / "listar"
ACERVO = RAIZ / "bin" / "acervo"


def _carrega():
    spec = importlib.util.spec_from_file_location("bancada_conversao", MODULO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bc = _carrega()


def oid(n: int) -> str:
    return f"{n:08x}-1111-4111-8111-111111111111"


def rel(metodo="perfil", *, perda=0, ref=1000, insercao=0, duplicacao=0, ordem=0, irrec=0,
        classe="B", blocos=100, converter=1000, total=2000, tipo="application/pdf",
        arquivo="x.pdf", **over):
    """Relatório v1 com fidelidade medida. `perda` etc. aceitam int (um papel) ou dict."""
    def papeis(v):
        return v if isinstance(v, dict) else ({"paragrafo": v} if v else {})

    r = {
        "versao_relatorio": 1, "obra_id": "x", "metodo": metodo, "aplicavel": True, "tipo": tipo,
        "arquivo": arquivo, "classe": classe, "reprovado": False, "erro": None, "erro_tipo": None,
        "cabecalho": {"blocos": blocos},
        "fidelidade": {"aplicavel": True, "classe": classe, "tamanho_referencia": ref,
                       "perda": papeis(perda), "insercao": papeis(insercao),
                       "duplicacao": papeis(duplicacao), "ordem": ordem,
                       "irrecuperavel": irrec, "erro": None},
        "tempos_ms": {"converter": converter, "total": total},
    }
    r.update(over)
    return r


def medida_falhou(metodo="perfil", **kw):
    """Conversão válida, MEDIDA de fidelidade com erro (fidelidade.erro): medida indeterminada."""
    return rel(metodo, fidelidade={"aplicavel": True, "classe": "B", "tamanho_referencia": 1000,
                                    "erro": "timeout de 900s na medida de fidelidade"}, **kw)


def sem_fidelidade(metodo="perfil", **kw):
    """Relatório sem erro, aplicável, com fidelidade nula: medida indeterminada também."""
    return rel(metodo, fidelidade=None, **kw)


def falhou(metodo="perfil", erro_tipo="conversao", **kw):
    """O MÉTODO falhou nesta obra (relatorio.erro com erro_tipo de dado)."""
    return rel(metodo, erro="boom", erro_tipo=erro_tipo, fidelidade=None, cabecalho=None, **kw)


def grava(pasta: Path, n: int, perfil=None, docling=None):
    for metodo, r in (("perfil", perfil), ("docling", docling)):
        if r is not None:
            d = pasta / metodo / oid(n)
            d.mkdir(parents=True, exist_ok=True)
            (d / "relatorio.json").write_text(json.dumps(r), encoding="utf-8")


def um(perfil, docling, **kw):
    """decidir() de uma obra."""
    return bc.decidir(oid(1), perfil, docling, **kw)


# ------------------------------------------------------------------ a regra por obra

def test_vence_o_metodo_com_menos_perda_somando_todos_os_papeis():
    assert um(rel(perda=10), rel("docling", perda=20))["vencedor"] == "perfil"
    assert um(rel(perda=20), rel("docling", perda=10))["vencedor"] == "docling"
    # perda é a SOMA dos papéis: 5+6 = 11 < 12
    d = um(rel(perda={"paragrafo": 5, "titulo": 6}), rel("docling", perda={"paragrafo": 12}))
    assert d["vencedor"] == "perfil" and d["perfil"]["perda"] == 11


def test_menos_irrecuperavel_desempata_a_perda_antes_de_inserir():
    # mesma perda; perfil insere 0 mas tem irrecuperável 5; docling insere 100 e tem 0:
    # §2.9 pesa mais que a inserção -> docling
    d = um(rel(perda=10, irrec=5), rel("docling", perda=10, insercao=100))
    assert d["vencedor"] == "docling"


@pytest.mark.parametrize("p, d, esperado", [
    (dict(insercao=1), dict(insercao=2), "perfil"),                       # 3o: inserção
    (dict(insercao=2), dict(insercao=1), "docling"),
    (dict(insercao=1, duplicacao=9), dict(insercao=2, duplicacao=0), "perfil"),   # inserção antes de duplicação
    (dict(duplicacao=1), dict(duplicacao=2), "perfil"),                   # 4o: duplicação
    (dict(duplicacao=2), dict(duplicacao=1), "docling"),
    (dict(duplicacao=1, ordem=9), dict(duplicacao=2, ordem=0), "perfil"),  # duplicação antes de ordem
    (dict(ordem=1), dict(ordem=2), "perfil"),                             # 5o: ordem
    (dict(ordem=2), dict(ordem=1), "docling"),
])
def test_desempate_por_insercao_duplicacao_e_ordem_nessa_ordem(p, d, esperado):
    assert um(rel(perda=10, **p), rel("docling", perda=10, **d))["vencedor"] == esperado


def test_chave_igual_e_empate_e_o_empate_fica_com_o_perfil_no_relatorio():
    d = um(rel(perda=10, insercao=3), rel("docling", perda=10, insercao=3))
    assert d["vencedor"] == "empate" and d["motivo"] == "chave igual"
    assert "fica com o perfil" in bc.REGRA
    # a chave usada fica exposta em cada obra decidida
    assert d["chave"] == {"perfil": [10, 0, 3, 0, 0], "docling": [10, 0, 3, 0, 0]}


# ------------------------------------------------------------------ B4: falha do método

@pytest.mark.parametrize("falha", [
    dict(erro="timeout 900s", erro_tipo="timeout"),                     # timeout
    dict(erro="boom", erro_tipo="conversao"),                           # o método falhou nesta obra
    dict(erro="caiu", erro_tipo="subprocesso"),                         # subprocesso sem relatório
    dict(erro="boom"),                                                  # relatório antigo: sem erro_tipo (ausente)
    dict(reprovado=True, fidelidade=None),                              # reprovado sem métricas
    dict(cabecalho={"blocos": 0}),                                      # blocos=0
])
def test_b4_falha_do_metodo_perde_tudo_e_o_outro_vence(falha):
    d = um(rel(perda=500), rel("docling", **falha))
    assert d["vencedor"] == "perfil"
    assert d["docling"]["estado"] == "falha" and d["docling"]["falha"]
    assert d["docling"]["perda"] == 1000 and d["docling"]["imputada"]
    assert (d["docling"]["insercao"], d["docling"]["duplicacao"], d["docling"]["ordem"],
            d["docling"]["irrecuperavel"]) == (0, 0, 0, 0)
    assert d["perfil"]["falha"] is None and d["perfil"]["estado"] == "medido"


def test_b4_falha_vale_tamanho_referencia_e_pode_perder_para_quem_perdeu_mais():
    # perfil perdeu 1001 (> ref 1000); docling falhou = 1000 -> a falha é 'menos pior'
    d = um(rel(perda=1001), rel("docling", erro="boom", fidelidade=None))
    assert d["vencedor"] == "docling" and d["docling"]["perda"] == 1000


def test_b4_falha_sem_referencia_propria_usa_a_do_outro_lado():
    d = um(rel(perda=10, ref=777), rel("docling", erro="boom", fidelidade=None))
    assert d["docling"]["perda"] == 777 and d["vencedor"] == "perfil"


def test_b4_os_dois_lados_em_falha_e_empate():
    d = um(rel(erro="x"), rel("docling", cabecalho={"blocos": 0}))
    assert d["vencedor"] == "empate" and d["motivo"] == "os dois falharam" and d["na"] is None
    assert d["perfil"]["perda"] == 1000 and d["docling"]["perda"] == 1000


def test_b4_sem_tamanho_referencia_em_nenhum_lado_e_na_e_vem_antes_do_empate_dos_dois_falharem():
    # precedência documentada: n/a por falta de referência vem primeiro
    d = um(rel(erro="x", fidelidade=None), rel("docling", erro="y", fidelidade=None))
    assert d["vencedor"] == "n/a" and d["na"] == "sem referência" and d["chave"] is None
    d = um(rel(perda=1, fidelidade={"aplicavel": True, "perda": {"paragrafo": 1}}),
           rel("docling", erro="y", fidelidade=None))
    assert d["vencedor"] == "n/a" and d["na"] == "sem referência"
    assert "antes do empate" in bc.REGRA and "sem referência" in bc.REGRA


# ------------------------------------------------------------------ B5: medida indeterminada

@pytest.mark.parametrize("indeterminada", [
    medida_falhou("docling"),                    # fidelidade.erro
    sem_fidelidade("docling"),                   # fidelidade nula, relatório sem erro, aplicável
])
def test_b5_medida_indeterminada_nao_e_falha_nada_e_imputado(indeterminada):
    d = um(rel(perda=10), indeterminada)
    assert d["vencedor"] == "indeterminada" and d["indeterminados"] == ["docling"]
    assert d["docling"]["estado"] == "indeterminada" and not d["docling"]["falha"]
    assert d["docling"]["perda"] is None and d["docling"]["imputada"] is False and d["chave"] is None
    assert d["perfil"]["estado"] == "medido"


def test_b5_obra_indeterminada_sai_do_teste_principal_e_e_contada_por_metodo(tmp_path):
    grava(tmp_path, 1, rel(perda=20), rel("docling", perda=10))         # docling vence
    grava(tmp_path, 2, rel(perda=1), medida_falhou("docling"))          # docling indeterminada
    grava(tmp_path, 3, sem_fidelidade(), rel("docling", perda=1))       # perfil indeterminada
    grava(tmp_path, 4, medida_falhou(), medida_falhou("docling"))       # os dois: fora de tudo
    (pdf,) = bc.agregar(str(tmp_path))["tipos"]
    assert (pdf["obras"], pdf["testadas"], pdf["vitorias_docling"], pdf["vitorias_perfil"]) == (4, 1, 1, 0)
    assert pdf["medida_indeterminada"] == {"perfil": 2, "docling": 2}
    assert pdf["falhas"] == {"perfil": 0, "docling": 0} and pdf["pendentes"] == {"perfil": 0, "docling": 0}
    assert pdf["n_a"] == 0 and pdf["sinal_n"] == 1


def test_b5_falha_de_um_lado_com_medida_indeterminada_no_outro_e_indeterminada():
    d = um(falhou(), medida_falhou("docling"))
    assert d["vencedor"] == "indeterminada" and d["indeterminados"] == ["docling"]
    assert d["perfil"]["estado"] == "falha"


def test_b5_reprovado_com_fidelidade_erro_e_medida_indeterminada_nao_falha(tmp_path):
    # reprovado + fidelidade.erro: a MEDIDA falhou, não o método -> indeterminada (B5), nada imputado
    d = um(rel(perda=10), medida_falhou("docling", reprovado=True))
    assert d["vencedor"] == "indeterminada" and d["indeterminados"] == ["docling"]
    lado = d["docling"]
    assert lado["estado"] == "indeterminada" and lado["falha"] is None and lado["reprovado"] is True
    assert lado["perda"] is None and lado["imputada"] is False and d["chave"] is None
    assert bc._lado(medida_falhou(reprovado=True))["estado"] == "indeterminada"
    # reprovado sem métricas E sem fidelidade.erro continua falha do método
    for sem_metricas in (dict(reprovado=True, fidelidade=None),
                         dict(reprovado=True, fidelidade={"aplicavel": True, "tamanho_referencia": 1000,
                                                          "erro": None})):
        assert bc._lado(rel(**sem_metricas))["estado"] == "falha"
    # na pasta: fora do teste principal, contada como medida indeterminada e não como falha
    grava(tmp_path, 1, rel(perda=20), rel("docling", perda=10))
    grava(tmp_path, 2, rel(perda=1), medida_falhou("docling", reprovado=True))
    (pdf,) = bc.agregar(str(tmp_path))["tipos"]
    assert (pdf["obras"], pdf["testadas"], pdf["sinal_n"]) == (2, 1, 1)
    assert pdf["medida_indeterminada"] == {"perfil": 0, "docling": 1}
    assert pdf["falhas"] == {"perfil": 0, "docling": 0}
    assert pdf["reprovados"] == {"perfil": 0, "docling": 1}


def _cenario_sensibilidade_com_falha(pasta: Path):
    """Principal: docling vence 3, perfil vence 1. Obras com medida indeterminada:
       2 com o docling indeterminado e o perfil MEDIDO           (contam nas variantes);
       1 com o perfil indeterminado e o docling MEDIDO           (conta nas variantes);
       2 com o perfil em FALHA e o docling indeterminado         (fora das variantes);
       1 com o docling em FALHA e o perfil indeterminado         (fora das variantes);
       1 com os dois lados indeterminados                        (fora de tudo)."""
    n = 0
    for perda_p, perda_d in [(20, 10)] * 3 + [(10, 20)]:
        n += 1
        grava(pasta, n, rel(perda=perda_p), rel("docling", perda=perda_d))
    grava(pasta, 21, rel(perda=5), medida_falhou("docling"))
    grava(pasta, 22, rel(perda=5), sem_fidelidade("docling"))
    grava(pasta, 23, medida_falhou(), rel("docling", perda=5))
    grava(pasta, 24, falhou(), medida_falhou("docling"))
    grava(pasta, 25, falhou(erro_tipo="timeout"), medida_falhou("docling"))
    grava(pasta, 26, medida_falhou(), falhou("docling"))
    grava(pasta, 27, medida_falhou(), medida_falhou("docling"))


def test_b5_sensibilidade_conta_so_indeterminada_contra_medido_indeterminada_x_falha_fica_fora(tmp_path):
    _cenario_sensibilidade_com_falha(tmp_path)
    res = bc.agregar(str(tmp_path))
    (pdf,) = res["tipos"]
    assert (pdf["obras"], pdf["testadas"], pdf["vitorias_perfil"], pdf["vitorias_docling"]) == (11, 4, 1, 3)
    assert pdf["medida_indeterminada"] == {"perfil": 3, "docling": 5}
    assert pdf["falhas"] == {"perfil": 2, "docling": 1}
    obras = {o["obra_id"]: o for o in res["obras"]}
    for n in (24, 25, 26):      # indeterminado x falha: indeterminada, mas fora das variantes
        assert obras[oid(n)]["vencedor"] == "indeterminada"
        assert "falha" in {obras[oid(n)]["perfil"]["estado"], obras[oid(n)]["docling"]["estado"]}
    # principal: n = 4, wp=1, wd=3. unilateral P(X>=3) = (C(4,3)+C(4,4))/16 = 5/16;
    # bilateral 2*P(X<=1) = 2*(1+4)/16 = 10/16
    assert pdf["sinal_n"] == 4
    assert pdf["sinal_p_unilateral"] == 5 / 16 and pdf["sinal_p_bilateral"] == 10 / 16
    # 3 obras (21, 22, 23): indeterminada de um lado contra MEDIDO do outro.
    # pior caso para o Docling: as 3 contam vitória do perfil: 4 x 3, n = 7,
    #   P(X>=3) = (C(7,3)+C(7,4)+C(7,5)+C(7,6)+C(7,7))/128 = (35+35+21+7+1)/128 = 99/128
    assert pdf["sensibilidade_pior_caso_docling"] == {
        "n": 7, "vitorias_perfil": 4, "vitorias_docling": 3, "p_unilateral": 99 / 128}
    # melhor caso: as 3 contam vitória do docling: 1 x 6, n = 7,
    #   P(X>=6) = (C(7,6)+C(7,7))/128 = (7+1)/128 = 1/16
    assert pdf["sensibilidade_melhor_caso_docling"] == {
        "n": 7, "vitorias_perfil": 1, "vitorias_docling": 6, "p_unilateral": 1 / 16}
    md = bc.render_markdown(res)
    assert "sensibilidade, pior caso para o Docling (um lado indeterminado, o outro medido): " \
           "n=7 · vitórias perfil 4 · docling 3 · p unilateral 0.7734" in md
    assert "sensibilidade, melhor caso para o Docling (um lado indeterminado, o outro medido): " \
           "n=7 · vitórias perfil 1 · docling 6 · p unilateral 0.0625" in md
    # a leitura adotada está na REGRA impressa
    for trecho in ("cada uma dessas obras conta vitória do perfil", "conta vitória do docling",
                   "o outro lado medido", "Indeterminado x falha"):
        assert trecho in bc.REGRA and trecho in md, trecho


def test_b7_falha_x_indeterminada_sem_tamanho_referencia_nos_dois_e_na_sem_referencia():
    # esta checagem vem ANTES da 'medida indeterminada' (e do empate dos dois falharem)
    sem_ref = {"aplicavel": True, "classe": "B", "erro": "timeout na medida"}
    for perfil, docling in [(falhou(), rel("docling", fidelidade=dict(sem_ref))),
                            (falhou(), sem_fidelidade("docling")),
                            (rel(fidelidade=dict(sem_ref)), falhou("docling")),
                            (sem_fidelidade(), falhou("docling", erro_tipo="timeout"))]:
        d = um(perfil, docling)
        assert d["vencedor"] == "n/a" and d["na"] == "sem referência", (perfil, docling)
        assert d["motivo"] == "sem tamanho_referencia em nenhum dos lados"
        assert d["indeterminados"] == [] and d["chave"] is None
    # com tamanho_referencia em algum lado (aqui, o lado indeterminado) continua indeterminada
    d = um(falhou(), medida_falhou("docling"))
    assert d["vencedor"] == "indeterminada" and d["indeterminados"] == ["docling"]
    # sem lado em falha, indeterminada contra medido sem referência continua indeterminada
    medido_sem_ref = rel(fidelidade={"aplicavel": True, "classe": "B", "perda": {"paragrafo": 1}})
    d = um(medido_sem_ref, sem_fidelidade("docling"))
    assert d["vencedor"] == "indeterminada" and d["indeterminados"] == ["docling"]
    # os dois lados em falha, sem referência: a mesma checagem (já coberta), não o empate
    d = um(falhou(), falhou("docling"))
    assert d["vencedor"] == "n/a" and d["na"] == "sem referência"
    # documentado na regra impressa
    assert "um lado em falha e o outro com a medida indeterminada" in bc.REGRA
    assert "antes da medida indeterminada" in bc.REGRA


def test_b7_falha_x_indeterminada_sem_referencia_conta_como_na_e_nao_como_indeterminada_na_pasta(tmp_path):
    grava(tmp_path, 1, rel(perda=20), rel("docling", perda=10))
    grava(tmp_path, 2, falhou(), sem_fidelidade("docling"))
    (pdf,) = bc.agregar(str(tmp_path))["tipos"]
    assert pdf["n_a_motivos"] == {"sem referência": 1} and pdf["n_a"] == 1
    assert pdf["medida_indeterminada"] == {"perfil": 0, "docling": 0}
    assert pdf["falhas"] == {"perfil": 0, "docling": 0}      # n/a não chegou à comparação
    assert pdf["sensibilidade_pior_caso_docling"]["n"] == pdf["sinal_n"] == 1


def _cenario_sensibilidade(pasta: Path):
    """9 pdf no teste principal + obras com medida indeterminada:
       docling vence 6, perfil vence 2, 1 empate;
       indeterminadas: 2 com o docling indeterminado, 1 com o perfil indeterminado, 1 com os dois."""
    n = 0
    for perda_p, perda_d in [(20, 10)] * 6 + [(10, 20)] * 2 + [(10, 10)]:
        n += 1
        grava(pasta, n, rel(perda=perda_p), rel("docling", perda=perda_d))
    grava(pasta, 21, rel(perda=5), medida_falhou("docling"))
    grava(pasta, 22, rel(perda=5), sem_fidelidade("docling"))
    grava(pasta, 23, medida_falhou(), rel("docling", perda=5))
    grava(pasta, 24, medida_falhou(), medida_falhou("docling"))


def test_b5_sensibilidade_p_exatos_conferidos_a_mao(tmp_path):
    _cenario_sensibilidade(tmp_path)
    (pdf,) = bc.agregar(str(tmp_path))["tipos"]
    assert (pdf["vitorias_perfil"], pdf["vitorias_docling"], pdf["empates"]) == (2, 6, 1)
    assert pdf["medida_indeterminada"] == {"perfil": 2, "docling": 3}
    # principal: n = 2 + 6 = 8. unilateral P(X>=6) = (C(8,6)+C(8,7)+C(8,8))/256 = (28+8+1)/256 = 37/256
    # bilateral 2*P(X<=2) = 2*(1+8+28)/256 = 74/256
    assert pdf["sinal_n"] == 8
    assert pdf["sinal_p_unilateral"] == 37 / 256 and pdf["sinal_p_bilateral"] == 74 / 256
    # 3 obras com a medida indeterminada em UM lado (a dos dois lados fica fora de tudo).
    # pior caso para o Docling: as 3 contam vitória do perfil: 5 x 6, n = 11,
    #   P(X>=6) = (C(11,6)+C(11,7)+C(11,8)+C(11,9)+C(11,10)+C(11,11))/2048
    #           = (462+330+165+55+11+1)/2048 = 1024/2048 = 0.5
    assert pdf["sensibilidade_pior_caso_docling"] == {
        "n": 11, "vitorias_perfil": 5, "vitorias_docling": 6, "p_unilateral": 0.5}
    # melhor caso: as 3 contam vitória do docling: 2 x 9, n = 11,
    #   P(X>=9) = (C(11,9)+C(11,10)+C(11,11))/2048 = (55+11+1)/2048 = 67/2048
    assert pdf["sensibilidade_melhor_caso_docling"] == {
        "n": 11, "vitorias_perfil": 2, "vitorias_docling": 9, "p_unilateral": 67 / 2048}
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert "sensibilidade, pior caso para o Docling (um lado indeterminado, o outro medido): " \
           "n=11 · vitórias perfil 5 · docling 6 · p unilateral 0.5000" in md
    assert "sensibilidade, melhor caso para o Docling (um lado indeterminado, o outro medido): " \
           "n=11 · vitórias perfil 2 · docling 9 · p unilateral 0.0327" in md
    # as variantes mostram só n, vitórias e p unilateral (sem p bilateral)
    assert set(pdf["sensibilidade_pior_caso_docling"]) == {"n", "vitorias_perfil", "vitorias_docling", "p_unilateral"}


def test_b5_sensibilidade_so_nos_tipos_amostrados(tmp_path):
    kw = dict(tipo="text/plain", arquivo="a.txt")
    grava(tmp_path, 1, rel(perda=1, **kw), medida_falhou("docling", **kw))
    (txt,) = bc.agregar(str(tmp_path))["tipos"]
    assert txt["regime"] == "censo" and txt["medida_indeterminada"] == {"perfil": 0, "docling": 1}
    assert not any(k.startswith(("sinal_", "sensibilidade_")) for k in txt)


# ------------------------------------------------------------------ B2 / B3: n/a

def test_b2_metodo_que_nao_cobre_o_tipo_e_na_com_motivo_proprio():
    d = um(rel(perda=10), rel("docling", aplicavel=False, classe="C", fidelidade=None))
    assert d["vencedor"] == "n/a" and d["na"] == "método não cobre o tipo" and d["chave"] is None
    assert d["motivo"] == "docling: método não cobre o tipo"
    d = um(rel(aplicavel=False, fidelidade=None), rel("docling", perda=1))
    assert d["na"] == "método não cobre o tipo" and d["motivo"].startswith("perfil:")


@pytest.mark.parametrize("docling", [
    rel("docling", classe="C", fidelidade={"aplicavel": False, "classe": "C",
                                            "motivo": "PDF sem camada de texto: sem R",
                                            "tamanho_referencia": None}),           # classe C
    rel("docling", classe="B", fidelidade={"aplicavel": False, "classe": "B", "motivo": "sem R"}),
])
def test_b3_classe_c_e_fidelidade_nao_aplicavel_sao_na_sem_referencia(docling):
    d = um(rel(perda=10), docling)
    assert d["vencedor"] == "n/a" and d["na"] == "sem referência" and d["chave"] is None


def test_b3_classe_c_em_qualquer_lado_carrega_o_motivo():
    c = rel(classe="C", fidelidade={"aplicavel": False, "classe": "C",
                                    "motivo": "PDF sem camada de texto: sem R",
                                    "tamanho_referencia": None})
    d = um(c, rel("docling", classe="C", fidelidade=None, erro="x"))
    assert d["vencedor"] == "n/a" and d["classe"] == "C" and "sem R" in d["motivo"]


def test_sem_tamanho_referencia_fica_fora_do_teste():
    sem_ref = {"aplicavel": True, "classe": "B", "perda": {"paragrafo": 1}}
    d = um(rel(fidelidade=dict(sem_ref)), rel("docling", fidelidade=dict(sem_ref)))
    assert d["vencedor"] == "n/a" and d["na"] == "sem referência"
    assert d["motivo"] == "sem tamanho_referencia em nenhum dos lados"


# ------------------------------------------------------------------ B1: pendente

def test_b1_lado_sem_relatorio_e_pendente_e_nao_n_a_nem_falha():
    d = um(rel(perda=1), None, prob_d="sem relatorio.json")
    assert d["vencedor"] == "pendente" and d["pendentes"] == ["docling"] and d["na"] is None
    assert d["docling"]["estado"] == "pendente" and d["docling"]["falha"] is None
    assert "docling: sem relatorio.json" in d["motivo"]
    d = um(None, rel("docling"), prob_p="relatório ilegível")
    assert d["vencedor"] == "pendente" and d["pendentes"] == ["perfil"] and "ilegível" in d["motivo"]
    d = um(None, None)
    assert d["pendentes"] == ["perfil", "docling"]


def test_b7_pendente_vem_antes_de_n_a_e_de_tudo():
    d = um(rel("perfil", aplicavel=False, fidelidade=None), None)
    assert d["vencedor"] == "pendente"                                # o lado n/a não salva a obra
    d = um(medida_falhou(), None)
    assert d["vencedor"] == "pendente"


@pytest.mark.parametrize("como", ["so_erro_txt", "so_invalido", "ilegivel", "versao", "erro_txt_ao_lado",
                                   "pasta_vazia", "nao_e_objeto", "so_espelho"])
def test_b1_toda_forma_de_relatorio_nao_valido_e_pendente(tmp_path, como):
    grava(tmp_path, 1, rel(perda=1), rel("docling", perda=2))
    pasta = tmp_path / "docling" / oid(1)
    if como == "so_erro_txt":
        (pasta / "relatorio.json").unlink()
        (pasta / "erro.txt").write_text("404\n", encoding="utf-8")
    elif como == "so_invalido":
        (pasta / "relatorio.json").rename(pasta / "relatorio.invalido.json")
    elif como == "ilegivel":
        (pasta / "relatorio.json").write_text("{quebrado", encoding="utf-8")
    elif como == "versao":
        (pasta / "relatorio.json").write_text(json.dumps(rel("docling", versao_relatorio=3)), encoding="utf-8")
    elif como == "erro_txt_ao_lado":                                  # relatório válido + erro.txt
        (pasta / "erro.txt").write_text("conferência: sha256\n", encoding="utf-8")
    elif como == "pasta_vazia":
        (pasta / "relatorio.json").unlink()
    elif como == "nao_e_objeto":
        (pasta / "relatorio.json").write_text("[1, 2]", encoding="utf-8")
    elif como == "so_espelho":
        (pasta / "relatorio.json").unlink()
        (pasta / "espelho.md").write_text("# x\n", encoding="utf-8")
    res = bc.agregar(str(tmp_path))
    (d,) = res["obras"]
    assert d["vencedor"] == "pendente" and d["pendentes"] == ["docling"] and d["perfil"]["estado"] == "medido"
    assert res["completo"] is False and res["total"]["pendentes"] == {"perfil": 0, "docling": 1}
    assert res["total"]["n_a"] == 0 and res["total"]["testadas"] == 0 and res["total"]["falhas"] == \
        {"perfil": 0, "docling": 0}


def test_b1_relatorio_v2_do_servico_vale_como_v1(tmp_path):
    # #3205: o conversor como serviço grava versao_relatorio 2 (mesmos campos, mais versao_imagem etc.)
    grava(tmp_path, 1, rel(perda=1, versao_relatorio=2), rel("docling", perda=2, versao_relatorio=2))
    res = bc.agregar(str(tmp_path))
    (d,) = res["obras"]
    assert d["perfil"]["estado"] == "medido" and d["docling"]["estado"] == "medido"
    assert d["vencedor"] == "perfil" and res["completo"] is True


def test_b1_so_erro_txt_nao_some_da_estatistica(tmp_path):
    # o achado [alto] do revisor: pasta com só erro.txt virava n/a e sumia da conta
    grava(tmp_path, 1, rel(), rel("docling"))
    (tmp_path / "perfil" / oid(2)).mkdir(parents=True)
    (tmp_path / "perfil" / oid(2) / "erro.txt").write_text("404\n", encoding="utf-8")
    res = bc.agregar(str(tmp_path))
    obras = {o["obra_id"]: o for o in res["obras"]}
    assert set(obras) == {oid(1), oid(2)}
    assert obras[oid(2)]["vencedor"] == "pendente" and obras[oid(2)]["pendentes"] == ["perfil", "docling"]
    assert res["total"]["pendentes"] == {"perfil": 1, "docling": 1} and res["total"]["n_a"] == 0


def test_b1_pendente_fora_do_sinal_contado_por_metodo_no_resumo_do_tipo_e_na_tabela(tmp_path):
    grava(tmp_path, 1, rel(perda=20), rel("docling", perda=10))
    grava(tmp_path, 2, rel(perda=1), rel("docling"))
    (tmp_path / "docling" / oid(2) / "relatorio.json").write_text("{quebrado", encoding="utf-8")
    grava(tmp_path, 3, rel(perda=1), None)                                    # docling: pasta ausente
    res = bc.agregar(str(tmp_path))
    (pdf,) = res["tipos"]
    assert pdf["pendentes"] == {"perfil": 0, "docling": 2} and pdf["pendentes_total"] == 2
    assert (pdf["testadas"], pdf["vitorias_docling"], pdf["sinal_n"]) == (1, 1, 1)   # fora do teste do sinal
    md = bc.render_markdown(res)
    assert "| pendentes (lados não obtidos) | 0 | 2 |" in md
    assert "pendentes 2" in md.split("### pdf")[1]
    linha = next(l for l in md.splitlines() if l.startswith("| " + oid(2)[:8]))
    assert "| pendente: docling: relatório ilegível |" in linha


def test_b1_piloto_incompleto_na_ultima_linha_do_markdown_e_completo_false_no_json(tmp_path):
    grava(tmp_path, 1, rel(), rel("docling"))
    (tmp_path / "perfil" / oid(2)).mkdir(parents=True)
    (tmp_path / "perfil" / oid(2) / "erro.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "docling" / oid(3)).mkdir(parents=True)
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert md.endswith("\n") and md.splitlines()[-1] == "PILOTO INCOMPLETO: 4 lado(s) pendente(s)"
    assert bc.agregar(str(tmp_path))["completo"] is False
    assert json.loads(bc.render_json(bc.agregar(str(tmp_path))))["completo"] is False


def test_b1_sem_pendente_o_piloto_esta_completo(tmp_path):
    grava(tmp_path, 1, rel(), rel("docling"))
    grava(tmp_path, 2, rel(aplicavel=False, fidelidade=None), rel("docling"))            # n/a não é pendente
    grava(tmp_path, 3, rel(), medida_falhou("docling"))                                   # nem indeterminada
    grava(tmp_path, 4, falhou(), rel("docling"))                                          # nem falha
    res = bc.agregar(str(tmp_path))
    assert res["completo"] is True and "PILOTO INCOMPLETO" not in bc.render_markdown(res)
    assert json.loads(bc.render_json(res))["completo"] is True


# ------------------------------------------------------------------ B2: indisponível é pendente

@pytest.mark.parametrize("erro_tipo, trecho", [("indisponivel", "indisponível"), ("inventado", "desconhecido")])
def test_b2_erro_tipo_indisponivel_ou_desconhecido_e_pendente_nao_falha(erro_tipo, trecho):
    d = um(rel(perda=10), rel("docling", erro="docling não instalado", erro_tipo=erro_tipo, fidelidade=None))
    assert d["vencedor"] == "pendente" and d["pendentes"] == ["docling"] and trecho in d["motivo"]
    assert d["docling"]["falha"] is None


@pytest.mark.parametrize("erro_tipo", ["conversao", "timeout", "subprocesso", None])
def test_b4_erro_tipo_de_dado_e_falha_do_metodo_nao_pendente(erro_tipo):
    d = um(rel(perda=10), rel("docling", erro="x", erro_tipo=erro_tipo, fidelidade=None))
    assert d["vencedor"] == "perfil" and d["docling"]["estado"] == "falha"


def test_b1_b2_indisponivel_no_disco_e_pendente_e_deixa_o_piloto_incompleto(tmp_path):
    grava(tmp_path, 1, rel(perda=1), rel("docling", erro="docling fora", erro_tipo="indisponivel",
                                         fidelidade=None))
    res = bc.agregar(str(tmp_path))
    assert res["completo"] is False and res["total"]["pendentes"] == {"perfil": 0, "docling": 1}
    assert res["total"]["falhas"] == {"perfil": 0, "docling": 0}


# ------------------------------------------------------------------ B7: precedência por lado

@pytest.mark.parametrize("nome, perfil, docling, vencedor, na", [
    # B2 > B3: método não cobre o tipo, mesmo com classe C e erro
    ("b2>b3", rel(aplicavel=False, classe="C", fidelidade=None, erro="x"), rel("docling"),
     "n/a", "método não cobre o tipo"),
    # B3 > B4: classe C com erro é 'sem referência', não falha
    ("b3>b4", rel(classe="C", fidelidade=None, erro="x"), rel("docling"), "n/a", "sem referência"),
    # B2 (outro lado) > B3 (este lado)
    ("b2 do outro lado", rel(classe="C", fidelidade=None), rel("docling", aplicavel=False, fidelidade=None),
     "n/a", "método não cobre o tipo"),
    # B4 > B5: blocos=0 com fidelidade.erro é falha (perda imputada), não indeterminada
    ("b4>b5", rel(perda=1), rel("docling", cabecalho={"blocos": 0},
                                fidelidade={"aplicavel": True, "tamanho_referencia": 1000, "erro": "x"}),
     "perfil", None),
    # B5 > medido
    ("b5>medido", rel(perda=1), medida_falhou("docling"), "indeterminada", None),
])
def test_b7_precedencia_por_lado(nome, perfil, docling, vencedor, na):
    d = um(perfil, docling)
    assert d["vencedor"] == vencedor and d["na"] == na, nome


def test_b7_estados_por_lado_na_ordem():
    assert bc._lado(None)["estado"] == "pendente"
    assert bc._lado(rel(aplicavel=False, erro="x"))["estado"] == "na_metodo"
    assert bc._lado(rel(classe="C", erro="x"))["estado"] == "na_ref"
    assert bc._lado(rel(erro="x"))["estado"] == "falha"
    assert bc._lado(medida_falhou())["estado"] == "indeterminada"
    assert bc._lado(rel())["estado"] == "medido"


# ------------------------------------------------------------------ o resto da regra

def test_campo_faltando_nunca_e_keyerror():
    d = um({}, {})                      # nada dentro: as duas medidas indeterminadas, fora de tudo
    assert d["vencedor"] == "indeterminada" and d["tipo"] == "?" and d["indeterminados"] == ["perfil", "docling"]
    esquisito = {"fidelidade": {"aplicavel": True, "tamanho_referencia": 10, "perda": "x"},
                 "cabecalho": [], "tempos_ms": "oi", "classe": 7, "erro": None}
    d = um(esquisito, rel("docling", perda=3, ref=10))
    assert d["vencedor"] == "indeterminada" and d["indeterminados"] == ["perfil"]


def test_reprovado_com_metricas_entra_pelo_que_mediu():
    d = um(rel(perda=1, reprovado=True), rel("docling", perda=2))
    assert d["vencedor"] == "perfil" and d["perfil"]["reprovado"] and d["perfil"]["falha"] is None


# ------------------------------------------------------------------ teste do sinal

@pytest.mark.parametrize("wp, wd, n, bi, uni", [
    # n=10, docling 8 x perfil 2: P(X<=2) = (1+10+45)/1024 = 56/1024
    (2, 8, 10, 112 / 1024, 56 / 1024),          # bilateral = 2*56/1024 = 0.109375; uni P(X>=8) = 56/1024
    (8, 2, 10, 112 / 1024, 1013 / 1024),        # uni P(X>=2) = 1 - (1+10)/1024
    (5, 5, 10, 1.0, 638 / 1024),                # 2*P(X<=5)=1276/1024 -> min(1, .) = 1; P(X>=5) = 638/1024
    (0, 3, 3, 0.25, 0.125),                     # 2*(1/8); P(X>=3) = 1/8
    (3, 0, 3, 0.25, 1.0),                       # 2*(1/8); P(X>=0) = 1
    (0, 6, 6, 2 / 64, 1 / 64),
])
def test_sinal_exato_conferido_a_mao(wp, wd, n, bi, uni):
    r = bc.teste_do_sinal(wp, wd)
    assert r["n"] == n and r["p_bilateral"] == pytest.approx(bi, abs=1e-15)
    assert r["p_unilateral"] == pytest.approx(uni, abs=1e-15)


def test_sinal_sem_sorteio_nao_tem_p():
    assert bc.teste_do_sinal(0, 0) == {"n": 0, "p_bilateral": None, "p_unilateral": None}


def _pdfs_do_sinal(pasta: Path):
    """15 pdf: docling vence 8, perfil vence 2, 3 empates, 1 docling n/a, 1 classe C."""
    pares = ([(rel(perda=20), rel("docling", perda=10))] * 8
             + [(rel(perda=10), rel("docling", perda=20))] * 2
             + [(rel(perda=10), rel("docling", perda=10))] * 3
             + [(rel(perda=1), rel("docling", aplicavel=False, fidelidade=None))]
             + [(rel(classe="C", fidelidade={"aplicavel": False, "classe": "C",
                                             "tamanho_referencia": None}),
                 rel("docling", classe="C", fidelidade=None))])
    for n, (p, d) in enumerate(pares, 1):
        grava(pasta, n, p, d)


def test_sinal_no_tipo_descarta_empates_e_n_a(tmp_path):
    _pdfs_do_sinal(tmp_path)
    (pdf,) = bc.agregar(str(tmp_path))["tipos"]
    assert pdf["tipo"] == "pdf" and pdf["regime"] == "amostrado"
    assert (pdf["obras"], pdf["testadas"], pdf["vitorias_perfil"], pdf["vitorias_docling"],
            pdf["empates"], pdf["n_a"]) == (15, 13, 2, 8, 3, 2)
    assert pdf["n_a_motivos"] == {"método não cobre o tipo": 1, "sem referência": 1}
    assert pdf["sinal_n"] == 10 and pdf["sinal_p_bilateral"] == 0.109375
    assert pdf["sinal_p_unilateral"] == 0.0546875
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert "teste do sinal principal (empates descartados): n=10 · p bilateral 0.1094 · " \
           "p unilateral (docling>perfil) 0.0547" in md
    assert "- n/a por motivo: método não cobre o tipo 1 · sem referência 1" in md


# ------------------------------------------------------------------ medianas

def test_mediana_par_e_impar_e_ignora_ausentes():
    assert bc.mediana([300, 100, 200]) == 200
    assert bc.mediana([400, 100, 300, 200]) == 250
    assert bc.mediana([5]) == 5 and bc.mediana([]) is None
    assert bc.mediana([100, None, 300, "x", True]) == 200


def test_medianas_do_tipo_par_e_impar_e_so_de_quem_converteu(tmp_path):
    for n, (c, t) in enumerate([(100, 1000), (300, 3000), (200, 2000)], 1):     # pdf: 3 (ímpar)
        grava(tmp_path, n, rel(perda=1, converter=c, total=t),
              rel("docling", perda=2, converter=c * 10, total=t * 10))
    grava(tmp_path, 4, rel(perda=1, converter=9999), rel("docling", aplicavel=False, fidelidade=None,
                                                          converter=None))   # docling n/a: não entra
    for n, c in enumerate([100, 200, 300, 400], 10):                              # txt: 4 (par)
        grava(tmp_path, n, rel(tipo="text/plain", arquivo="a.txt", converter=c, total=c + 1),
              rel("docling", tipo="text/plain", arquivo="a.txt", converter=c * 2, total=c * 2))
    tipos = {t["tipo"]: t for t in bc.agregar(str(tmp_path))["tipos"]}
    # pdf perfil: [100,300,200,9999] -> par: (200+300)/2 ; docling: [1000,3000,2000] -> 2000
    assert tipos["pdf"]["mediana_converter_ms"] == {"perfil": 250, "docling": 2000}
    assert tipos["pdf"]["mediana_total_ms"]["docling"] == 20000
    assert tipos["txt"]["mediana_converter_ms"] == {"perfil": 250, "docling": 500}
    assert tipos["txt"]["mediana_total_ms"] == {"perfil": 251, "docling": 500}
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert "| mediana tempos_ms.converter | 250 | 500 |" in md


# ------------------------------------------------------------------ B6: o resumo por tipo traz tudo

def test_b6_resumo_por_tipo_traz_todos_os_campos_pedidos(tmp_path):
    _cenario_sensibilidade(tmp_path)
    grava(tmp_path, 30, rel(reprovado=True, perda=1), falhou("docling"))
    grava(tmp_path, 31, rel(aplicavel=False, fidelidade=None), rel("docling"))
    grava(tmp_path, 32, rel(perda=1), None)                                    # docling pendente
    res = bc.agregar(str(tmp_path))
    (pdf,) = res["tipos"]
    for campo in ("obras", "testadas", "vitorias_perfil", "vitorias_docling", "empates",
                  "sinal_n", "sinal_p_bilateral", "sinal_p_unilateral",
                  "sensibilidade_pior_caso_docling", "sensibilidade_melhor_caso_docling",
                  "n_a", "n_a_motivos", "pendentes", "medida_indeterminada", "falhas",
                  "mediana_converter_ms", "mediana_total_ms", "reprovados"):
        assert campo in pdf, campo
    assert pdf["n_a_motivos"] == {"método não cobre o tipo": 1}
    assert pdf["pendentes"] == {"perfil": 0, "docling": 1} and pdf["falhas"] == {"perfil": 0, "docling": 1}
    assert pdf["reprovados"] == {"perfil": 1, "docling": 0}
    md = bc.render_markdown(res)
    bloco = md.split("### pdf (amostrado)")[1].split("## (c)")[0]
    for linha in ("| mediana tempos_ms.converter |", "| mediana tempos_ms.total |", "| reprovados | 1 | 0 |",
                  "| pendentes (lados não obtidos) | 0 | 1 |", "| medida indeterminada (nada imputado) | 2 | 3 |",
                  "| falhas do método (perda imputada) | 0 | 1 |", "- n/a por motivo:", "- teste do sinal principal",
                  "- sensibilidade, pior caso para o Docling", "- sensibilidade, melhor caso para o Docling"):
        assert linha in bloco, linha
    assert "erros" not in bloco                     # a categoria 'erros' foi substituída por B1-B7


# ------------------------------------------------------------------ censo

def test_tipo_em_censo_reporta_vitorias_e_maior_irrecuperavel_sem_p(tmp_path):
    kw = dict(tipo="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              arquivo="a.docx")
    grava(tmp_path, 1, rel(perda=10, irrec=4, **kw), rel("docling", perda=20, irrec=9, **kw))
    grava(tmp_path, 2, rel(perda=30, irrec=1, **kw), rel("docling", perda=5, irrec=2, **kw))
    grava(tmp_path, 3, rel(perda=5, **kw), rel("docling", perda=5, **kw))
    grava(tmp_path, 4, rel(perda=5, **kw), rel("docling", erro="boom", fidelidade=None, **kw))
    (docx,) = bc.agregar(str(tmp_path))["tipos"]
    assert docx["tipo"] == "docx" and docx["regime"] == "censo"
    assert (docx["vitorias_perfil"], docx["vitorias_docling"], docx["empates"]) == (2, 1, 1)
    assert docx["maior_irrecuperavel"] == {"perfil": 4, "docling": 9}
    assert docx["falhas"] == {"perfil": 0, "docling": 1}
    assert not any(k.startswith(("sinal_", "sensibilidade_")) for k in docx)
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    bloco = md.split("### docx (censo)")[1].split("## (c)")[0]
    assert "maior irrecuperável observado (entre as testadas) | 4 | 9 |" in bloco
    assert "teste do sinal" not in bloco and "sensibilidade" not in bloco


@pytest.mark.parametrize("mime, ext, esperado", [
    ("application/pdf", "pdf", "pdf"),
    ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx", "xlsx"),
    ("text/html", "htm", "htm"), ("text/html", "html", "html"), ("text/html", "", "html"),
    ("message/rfc822", "mht", "mhtml"), ("application/epub+zip", "epub", "epub"),
    ("text/plain", "txt", "txt"), ("", "MOBI", "mobi"), ("application/x-desconhecido", "", "x-desconhecido"),
])
def test_tipo_curto(mime, ext, esperado):
    assert bc.tipo_curto({"tipo": mime, "arquivo": "a." + ext if ext else "a"}) == esperado
    assert bc.tipo_curto({}) == "?" and bc.tipo_curto(None, {"tipo": "application/pdf"}) == "pdf"


# ------------------------------------------------------------------ estratos

def test_estratos_rotulam_a_tabela_e_agrupam_so_os_pdf(tmp_path):
    for n in (1, 2, 3):                                        # estrato A: docling vence 3
        grava(tmp_path, n, rel(perda=20), rel("docling", perda=10))
    grava(tmp_path, 4, rel(perda=10), rel("docling", perda=20))   # estrato B: perfil 2, docling 1
    grava(tmp_path, 5, rel(perda=10), rel("docling", perda=20))
    grava(tmp_path, 6, rel(perda=20), rel("docling", perda=10))
    grava(tmp_path, 7, rel(perda=1), rel("docling", perda=2))     # sem estrato listado
    grava(tmp_path, 8, rel(tipo="text/plain", arquivo="a.txt"), rel("docling", tipo="text/plain",
                                                                      arquivo="a.txt"))
    tsv = tmp_path / "estratos.tsv"
    tsv.write_text("obra_id\testrato\n# pilotos\n\n"
                   f"{oid(1)[:8]}\tA\n{oid(2)[:8]}\tA\n{oid(3)}\tA\n"
                   f"{oid(4)[:8]}\tB\n{oid(5)[:8]}\tB\n{oid(6)[:8]}\tB\n"
                   f"{oid(8)[:8]}\tcenso-txt\n", encoding="utf-8")
    res = bc.agregar(str(tmp_path), bc.ler_estratos(str(tsv)))
    est = {o["obra_id"][:8]: o["estrato"] for o in res["obras"]}
    assert est[oid(1)[:8]] == "A" and est[oid(6)[:8]] == "B" and est[oid(7)[:8]] == "-"
    pdf = next(t for t in res["tipos"] if t["tipo"] == "pdf")
    total_pdf = (pdf["vitorias_perfil"], pdf["vitorias_docling"], pdf["sinal_n"])
    assert total_pdf == (3, 4, 7)          # A: 3 docling; B: 2 perfil + 1 docling; 7: perfil
    por = {e["estrato"]: e for e in pdf["estratos"]}
    assert sorted(por) == ["-", "A", "B"]
    # A: 3 x 0 -> bilateral 2*(1/8) = .25; uni P(X>=3) = 1/8
    assert (por["A"]["sinal_n"], por["A"]["sinal_p_bilateral"], por["A"]["sinal_p_unilateral"]) \
        == (3, 0.25, 0.125)
    # B: perfil 2, docling 1: min=1, P(X<=1) = 4/8 -> bilateral min(1, 1)=1; uni P(X>=1) = 7/8
    assert (por["B"]["sinal_n"], por["B"]["sinal_p_bilateral"], por["B"]["sinal_p_unilateral"]) \
        == (3, 1.0, 0.875)
    # o txt não é agrupado por estrato
    assert "estratos" not in next(t for t in res["tipos"] if t["tipo"] == "txt")
    md = bc.render_markdown(res)
    assert "#### pdf · estrato A" in md and "#### pdf · estrato B" in md and "#### txt" not in md
    linha = next(l for l in md.splitlines() if l.startswith("| " + oid(8)[:8]))
    assert "| txt | censo-txt |" in linha


def test_estratos_com_linha_malformada_ou_arquivo_ausente_e_erro(tmp_path):
    ruim = tmp_path / "ruim.tsv"
    ruim.write_text("abcdef12 sem tab\n", encoding="utf-8")
    with pytest.raises(ValueError):
        bc.ler_estratos(str(ruim))
    err = io.StringIO()
    grava(tmp_path, 1, rel(), rel("docling"))
    assert bc.executar(str(tmp_path), arquivo_estratos=str(ruim), out=io.StringIO(), err=err) == 2
    assert bc.executar(str(tmp_path), arquivo_estratos=str(tmp_path / "nao-existe"),
                       out=io.StringIO(), err=io.StringIO()) == 2


def test_estrato_pelo_prefixo_mais_longo():
    est = {"0000000a": "curto", "0000000a-1111": "longo"}
    assert bc.estrato_de(oid(0xa), est) == "longo" and bc.estrato_de(oid(0xb), est) == "-"
    assert bc.estrato_de(oid(0xa).upper(), est) == "longo"


# ------------------------------------------------------------------ saída

def test_tabela_por_obra_no_molde(tmp_path):
    grava(tmp_path, 1, rel(perda=500, insercao=2, duplicacao=3, ordem=1, irrec=4, converter=111),
          rel("docling", erro="timeout 900s", fidelidade=None, converter=222))
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert md.startswith("# Bancada de conversão: perfil x docling")
    assert "## (a) Por obra" in md and "## (b) Resumo por tipo" in md and "## (c) Contagem total" in md
    assert "| obra | tipo | estrato | classe | perda p / d | inserção p / d | duplicação p / d | " \
           "ordem p / d | irrecuperável p / d | converter ms p / d | vencedor |" in md
    assert f"| {oid(1)[:8]} | pdf | - | B | 500 / 1000! | 2 / 0 | 3 / 0 | 1 / 0 | 4 / 0 | " \
           "111 / 222 | perfil |" in md


def test_n_a_entra_na_tabela_com_o_motivo(tmp_path):
    grava(tmp_path, 1, rel(), rel("docling", aplicavel=False, fidelidade=None, converter=None))
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert "| n/a: docling: método não cobre o tipo |" in md
    assert "- n/a por motivo: método não cobre o tipo 1" in md


def test_regra_impressa_documenta_a_precedencia_e_os_estados():
    for trecho in ("pendente > n/a", "falha do método > medida", "indeterminada > medido",
                   "sem referência", "antes do empate", "INCOMPLETO", "sensibilidade"):
        assert trecho in bc.REGRA, trecho


def test_contagem_total(tmp_path):
    _pdfs_do_sinal(tmp_path)
    grava(tmp_path, 100, rel(reprovado=True, perda=1), rel("docling", perda=1, erro="x"))
    total = bc.agregar(str(tmp_path))["total"]
    assert total["obras"] == 16 and total["vitorias_docling"] == 8 and total["n_a"] == 2
    assert total["reprovados"] == {"perfil": 1, "docling": 0}
    assert total["falhas"] == {"perfil": 0, "docling": 1}
    assert not any(k.startswith(("sinal_", "sensibilidade_")) for k in total)


def _arvore_em_ordem(pasta: Path, ordem):
    for n in ordem:
        tipo = dict(tipo="text/plain", arquivo="a.txt") if n % 2 else {}
        grava(pasta, n, rel(perda=n % 3, **tipo), rel("docling", perda=(n + 1) % 3, **tipo))
    (pasta / "perfil" / oid(90)).mkdir(parents=True)                         # pendente: também determinístico


def test_saida_deterministica_independe_da_ordem_de_criacao(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _arvore_em_ordem(a, range(1, 9))
    _arvore_em_ordem(b, reversed(range(1, 9)))
    ra, rb = bc.agregar(str(a)), bc.agregar(str(b))
    ra.pop("pasta"), rb.pop("pasta")
    assert json.dumps(ra) == json.dumps(rb)
    ordem = [(o["tipo"], o["estrato"], o["obra_id"]) for o in ra["obras"]]
    assert ordem == sorted(ordem)
    assert bc.render_markdown(bc.agregar(str(a))) == bc.render_markdown(bc.agregar(str(a)))
    assert bc.render_json(bc.agregar(str(a))) == bc.render_json(bc.agregar(str(a)))


def test_relatorio_ilegivel_ou_so_erro_txt_aparece_como_pendente(tmp_path):
    grava(tmp_path, 1, rel(), rel("docling"))
    (tmp_path / "docling" / oid(1) / "relatorio.json").write_text("{quebrado", encoding="utf-8")
    (tmp_path / "perfil" / oid(2)).mkdir(parents=True)
    (tmp_path / "perfil" / oid(2) / "erro.txt").write_text("404\n", encoding="utf-8")
    obras = {o["obra_id"]: o for o in bc.agregar(str(tmp_path))["obras"]}
    assert set(obras) == {oid(1), oid(2)}
    assert obras[oid(1)]["vencedor"] == "pendente" and obras[oid(1)]["pendentes"] == ["docling"]
    assert "ilegível" in obras[oid(1)]["motivo"]
    assert obras[oid(2)]["vencedor"] == "pendente" and obras[oid(2)]["pendentes"] == ["perfil", "docling"]
    assert "só erro.txt" in obras[oid(2)]["motivo"]
    md = bc.render_markdown(bc.agregar(str(tmp_path)))
    assert "pendente: docling: relatório ilegível" in md
    assert md.splitlines()[-1] == "PILOTO INCOMPLETO: 3 lado(s) pendente(s)"


# ------------------------------------------------------------------ o verbo

def _roda(*args):
    return subprocess.run([sys.executable, str(LISTAR), "obra", "bancada", *args],
                          capture_output=True, text=True, check=False)


def test_verbo_markdown_json_e_estratos(tmp_path):
    grava(tmp_path, 1, rel(perda=2), rel("docling", perda=1))
    (tmp_path / "e.tsv").write_text(f"{oid(1)[:8]}\tpiloto\n", encoding="utf-8")
    r = _roda(str(tmp_path), "--estratos", str(tmp_path / "e.tsv"))
    assert r.returncode == 0, r.stderr
    assert "## (a) Por obra" in r.stdout and "| piloto |" in r.stdout and "docling |" in r.stdout
    j = _roda(str(tmp_path), "--json", "--estratos", str(tmp_path / "e.tsv"))
    assert j.returncode == 0 and json.loads(j.stdout)["obras"][0]["vencedor"] == "docling"
    assert json.loads(j.stdout)["obras"][0]["estrato"] == "piloto"


def test_a7_pasta_json_e_estratos_valem_em_qualquer_ordem_depois_de_bancada(tmp_path):
    grava(tmp_path, 1, rel(perda=2), rel("docling", perda=1))
    tsv = tmp_path / "e.tsv"
    tsv.write_text(f"{oid(1)[:8]}\tpiloto\n", encoding="utf-8")
    p = str(tmp_path)
    combinacoes = [
        (p, "--json", "--estratos", str(tsv)),
        (p, "--estratos", str(tsv), "--json"),
        ("--json", p, "--estratos", str(tsv)),
        ("--json", "--estratos", str(tsv), p),
        ("--estratos", str(tsv), p, "--json"),
        ("--estratos", str(tsv), "--json", p),
    ]
    saidas = []
    for c in combinacoes:
        r = _roda(*c)
        assert r.returncode == 0, (c, r.stderr)
        obra, = json.loads(r.stdout)["obras"]
        assert obra["vencedor"] == "docling" and obra["estrato"] == "piloto"
        saidas.append(r.stdout)
    assert len(set(saidas)) == 1
    # sem --json: Markdown, com a pasta antes ou depois das opções
    assert _roda("--estratos", str(tsv), p).stdout == _roda(p, "--estratos", str(tsv)).stdout


@pytest.mark.parametrize("extra", [["--sobre", "norma"], ["--eixo", "dominio"], ["--situacao"],
                                    ["--dono", "dados"]])
def test_a7_opcoes_de_outro_ato_com_bancada_sao_exit_2_e_nao_ignoradas(tmp_path, extra):
    grava(tmp_path, 1, rel(perda=2), rel("docling", perda=1))
    for ordem in ((str(tmp_path), *extra), (*extra, str(tmp_path))):
        r = _roda(*ordem)
        assert r.returncode == 2, (ordem, r.stdout, r.stderr)
        assert r.stdout == "" and ("nao valem aqui" in r.stderr or "opcao desconhecida" in r.stderr)


@pytest.mark.parametrize("nome", ["metodos", "bancada"])
def test_a8_depois_de_bancada_o_primeiro_token_sem_hifen_e_a_pasta_mesmo_reservado(tmp_path, nome):
    grava(tmp_path / nome, 1, rel(perda=2), rel("docling", perda=1))
    for cmd in ([sys.executable, str(LISTAR), "obra", "bancada", nome, "--json"],
                [sys.executable, str(LISTAR), "obra", "bancada", "--json", nome],
                ["bash", str(ACERVO), "listar", "obra", "bancada", nome, "--json"]):
        r = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=tmp_path)
        assert r.returncode == 0, (cmd, r.stdout, r.stderr)
        res = json.loads(r.stdout)
        assert res["pasta"] == nome and res["obras"][0]["vencedor"] == "docling"
    # `metodos` ANTES de `bancada` segue sendo a escolha exclusiva (nao vira pasta)
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "metodos", "bancada", nome],
                       capture_output=True, text=True, check=False, cwd=tmp_path)
    assert r.returncode == 2 and "OU" in r.stderr


def test_a7_pasta_duplicada_ou_estratos_sem_valor_e_exit_2(tmp_path):
    grava(tmp_path, 1, rel(perda=2), rel("docling", perda=1))
    assert _roda(str(tmp_path), str(tmp_path)).returncode == 2
    assert _roda(str(tmp_path), "--estratos").returncode == 2


def test_a7_cabecalhos_de_bin_acervo_declaram_arquivo_local_onde_curar_grava_e_listar_le():
    linhas = ACERVO.read_text(encoding="utf-8").splitlines()
    escreve = {l.split("=", 1)[0].removeprefix("# escreve: "): l.split("=", 1)[1]
               for l in linhas if l.startswith("# escreve: ")}
    le = {l.split("=", 1)[0].removeprefix("# le: "): l.split("=", 1)[1]
          for l in linhas if l.startswith("# le: ")}
    assert "arquivo-local" in escreve["curar"].split(",")      # curar --reextrair --bancada grava a pasta
    assert "arquivo-local" in le["listar"].split(",")          # listar obra bancada lê a pasta
    assert "arquivo-local" in escreve["extrato"].split(",")    # o precedente do vocabulário


def test_verbo_uso_errado_exit_2_e_pasta_sem_relatorio_exit_1(tmp_path):
    assert _roda().returncode == 2
    assert _roda(str(tmp_path / "nao-existe")).returncode == 2
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    r = _roda(str(vazia))
    assert r.returncode == 1 and "nenhum relatorio.json" in r.stderr
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--estratos", "x.tsv"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 2 and "--estratos" in r.stderr


def test_acervo_listar_obra_bancada_despacha_ate_o_agregador(tmp_path):
    grava(tmp_path, 1, rel(perda=2), rel("docling", perda=1))
    r = subprocess.run(["bash", str(ACERVO), "listar", "obra", "bancada", str(tmp_path), "--json"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["obras"][0]["vencedor"] == "docling"
    r = subprocess.run(["bash", str(ACERVO), "listar", "obra", "bancada", "--json", str(tmp_path)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run(["bash", str(ACERVO), "listar", "obra", "bancada", str(tmp_path), "--sobre", "x"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 2


def test_ajuda_e_despacho_declaram_o_ato():
    listar = LISTAR.read_text(encoding="utf-8")
    uso = listar.split('USO = """', 1)[1].split('"""', 1)[0]
    assert "acervo listar obra bancada <pasta> [--json] [--estratos <arquivo>]" in uso
    acervo = ACERVO.read_text(encoding="utf-8")
    assert 'listar:obra:bancada)    exec "$ATOS/listar" obra bancada "$@"' in acervo
    assert "acervo listar   obra bancada <pasta> [--json] [--estratos <arquivo>]" in acervo


def test_so_stdlib():
    fonte = MODULO.read_text(encoding="utf-8")
    importados = {l.split()[1].split(".")[0] for l in fonte.splitlines()
                  if l.startswith(("import ", "from ")) and "__future__" not in l}
    assert importados <= {"json", "math", "os", "sys"}, importados
