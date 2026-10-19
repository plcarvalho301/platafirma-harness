"""A decisão da poda do caderno, que saiu do `descansar fita` para o bot (cards #3498 e #3884).

O que se trava (arq:0120, Emenda de 19/10/2026): a passada do bot `caderno-poda` decide sobre as
entradas servíveis de todas as cadeiras. Sai retirada, com o motivo, a premissa vencida, a entrada
que cita linha do balde de débito, a lição sem confirmação há mais de 30 dias, a duplicata do
cânone e a que cita o que não existe mais; a preferência do dono nunca sai pela máquina. Entre as
que ficam, a lição que outro caderno repete (de qualquer cadeira) ou que foi confirmada duas vezes
vai a tombar. A entrada sã fica. As conferências que olham fora (busca, card, verbo) são as do
#3498, agora em lib/caderno_poda.py.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
import caderno_poda  # noqa: E402

HOJE = date(2026, 10, 19)
DUPLICADA = "Migracao de schema recebe o maior numero da pasta mais um e e idempotente"
PAR_A = "Todo fake de teste nasce de um retorno real colado da API, porque o fake esconde o formato real"
PAR_B = "Fake de teste que devolve o campo esperado esconde o formato real: todo fake de API nasce de retorno real colado"
MORTA = "Ate a #3001 sair, o fecho do parecer vai num comentario a parte"
SA = "Juiz-modelo do mesmo modelo concorda com o gerador; a conferencia fica com modelo diferente"


def _e(eid, texto, categoria="licao", cadeira="ia", chapeu="contexto", dias=1, **campos):
    e = {"id": eid, "cadeira": cadeira, "chapeu": chapeu, "categoria": categoria, "texto": texto,
         "confirmada_em": HOJE - timedelta(days=dias), "vale_ate": None}
    e.update(campos)
    return e


# Stubs dos verbos irmaos (PF_BIN): motor diz que so a entrada DUPLICADA repete o canone (e que um
# parecer, material, parece com a sa); tarefas diz que #3001 entregou; conferir acha todo verbo.
STUB_MOTOR = """#!/bin/sh
case "$4" in
  Migracao*) echo '{"fontes":[{"arquivo":"guia ddl-e-migracao","sim":0.73}]}' ;;
  Juiz*) echo '{"fontes":[{"arquivo":"parecer 2026-08-08-julgamento","sim":0.91},{"arquivo":"arq:0012","sim":0.55}]}' ;;
  *) echo '{"fontes":[{"arquivo":"arq:0120","sim":0.60}]}' ;;
esac
"""
STUB_TAREFAS = """#!/bin/sh
case "$2" in
  3001) printf '# titulo\\n#3001 \\302\\267 story \\302\\267 Entregue (terminal) \\302\\267 cadeira: ia\\n' ;;
  3002) printf '# titulo\\n#3002 \\302\\267 story \\302\\267 Englobada (terminal) \\302\\267 cadeira: ia\\n' ;;
  3003) echo "item 3003 foi apagado" >&2; exit 1 ;;
  *) printf '# titulo\\n#%s \\302\\267 story \\302\\267 Em execu\\303\\247\\303\\243o (delivery)\\n' "$2" ;;
esac
"""
STUB_CONFERIR = """#!/bin/sh
case "$3" in sumido) echo "nao-existe: verbo sumido"; exit 1 ;; esac
echo "existe: verbo $3"; exit 0
"""


@pytest.fixture()
def stubs(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "bin"
    d.mkdir()
    for nome, corpo in (("motor", STUB_MOTOR), ("tarefas", STUB_TAREFAS), ("conferir", STUB_CONFERIR)):
        f = d / nome
        f.write_text(corpo, encoding="utf-8")
        f.chmod(0o755)
    monkeypatch.setenv("PF_BIN", str(d))
    return tmp_path


def _mortas(texto, cache):
    return caderno_poda.referencias_mortas(texto, cache, lambda cad: ({"contexto", "agente"}, None))


def test_aceite_cada_motivo_de_saida_e_a_sa_fica(stubs):
    entradas = [
        _e(1, DUPLICADA),
        _e(2, MORTA),
        _e(3, "Contorno do motor: ver #2856, linha 12"),
        _e(4, "Licao que ninguem confirmou ha um mes", dias=31),
        _e(5, "X esta aposentado", categoria="premissa", vale_ate=HOJE - timedelta(days=1)),
        _e(6, SA),
    ]
    retirar, tombar = caderno_poda.decide(entradas, HOJE, mortas=_mortas)
    motivos = {e["id"]: m for e, m in retirar}
    assert motivos == {
        1: "duplicata do cânone guia ddl-e-migracao (sim 0.73)",
        2: "referência morta #3001 (entregue)",
        3: "foi ao débito técnico: #2856 linha 12",
        4: f"venceu sem confirmação desde {(HOJE - timedelta(days=31)).strftime('%d/%m/%Y')} (30 dias)",
        5: f"premissa vencida em {(HOJE - timedelta(days=1)).strftime('%d/%m/%Y')}",
    }
    assert tombar == [], "a sã (c6) fica"


def test_preferencia_do_dono_nao_sai_pela_maquina(stubs):
    pref = _e(7, DUPLICADA, categoria="preferencia", dias=200)
    retirar, tombar = caderno_poda.decide([pref], HOJE, mortas=_mortas)
    assert retirar == [] and tombar == []


def test_licao_de_30_dias_ainda_fica():
    e = _e(8, SA, dias=30)
    retirar, _ = caderno_poda.decide([e], HOJE, canone=lambda t: None)
    assert retirar == []


def test_par_entre_cadeiras_tomba_os_dois_lados():
    a = _e(10, PAR_A, cadeira="ia", chapeu="contexto")
    b = _e(11, PAR_B, cadeira="dados", chapeu="curadoria")
    sa = _e(12, SA, cadeira="ia", chapeu="agente")
    _, tombar = caderno_poda.decide([a, b, sa], HOJE, canone=lambda t: None)
    motivos = {e["id"]: m for e, m in tombar}
    assert set(motivos) == {10, 11}
    assert motivos[10].startswith("a mesma lição em dados/curadoria c11")
    assert motivos[11].startswith("a mesma lição em ia/contexto c10")


def test_o_mesmo_caderno_nao_e_par_de_si():
    a = _e(10, PAR_A)
    b = _e(11, PAR_B)
    _, tombar = caderno_poda.decide([a, b], HOJE, canone=lambda t: None)
    assert tombar == []


def test_confirmada_duas_vezes_tomba():
    e = _e(13, SA)
    _, tombar = caderno_poda.decide([e], HOJE, {13: 2}, canone=lambda t: None)
    assert tombar == [(e, "confirmada 2 vezes")]
    _, tombar = caderno_poda.decide([e], HOJE, {13: 1}, canone=lambda t: None)
    assert tombar == []


def test_o_que_sai_nao_e_par_de_ninguem():
    a = _e(10, PAR_A, cadeira="ia", dias=40)
    b = _e(11, PAR_B, cadeira="dados", chapeu="curadoria")
    retirar, tombar = caderno_poda.decide([a, b], HOJE, canone=lambda t: None)
    assert [e["id"] for e, _ in retirar] == [10] and tombar == []


def test_parecer_e_material_nao_canone(stubs):
    assert caderno_poda.duplicata_do_canone(SA) is None, "sim 0,91 contra parecer nao e duplicata"
    assert caderno_poda.duplicata_do_canone(DUPLICADA) == "guia ddl-e-migracao (sim 0.73)"


def test_card_terminal_sem_herdeiro_e_morto_englobado_tem_herdeiro(stubs):
    cache = {}
    assert caderno_poda.estado_card("3001", cache) == ("morto", "entregue")
    assert caderno_poda.estado_card("3002", cache)[0] == "vivo"
    assert caderno_poda.estado_card("3003", cache) == ("morto", "apagado")
    assert caderno_poda.estado_card("3498", cache)[0] == "vivo"


def test_referencia_morta_le_o_texto_verbo_e_chapeu(stubs):
    texto = ("Rodar `sumido abrir x` e `mesa caderno contexto`, ou `git push`; ver chapeu:ia/extinto "
             "e chapeu:ia/contexto; #2856 linha 104")
    mortas = caderno_poda.referencias_mortas(
        texto, {}, declarados_de=lambda cad: ({"contexto", "agente"}, None))
    assert mortas == ["verbo sumido", "chapéu ia/extinto"], "git fica fora; #2856 vivo"


def test_semelhanca_separa_a_mesma_licao_do_mesmo_assunto():
    assert caderno_poda.semelhanca(PAR_A, PAR_B) >= caderno_poda.LIMIAR_PAR
    assert caderno_poda.semelhanca(PAR_A, SA) < caderno_poda.LIMIAR_PAR


def test_balde_sem_linha_nao_e_debito():
    assert caderno_poda.foi_ao_debito("o balde #2856 tem a regra") is None
    assert caderno_poda.foi_ao_debito("débito #2856 linha 104") == "#2856 linha 104"


def test_chapeus_declarados_le_a_abertura(tmp_path):
    (tmp_path / "ia" / "contexto").mkdir(parents=True)
    (tmp_path / "ia" / "persona.md").write_text("x", encoding="utf-8")
    assert caderno_poda.chapeus_declarados(str(tmp_path), "ia") == ({"contexto"}, None)
    slugs, erro = caderno_poda.chapeus_declarados(str(tmp_path), "nenhuma")
    assert slugs is None and "nao encontrada" in erro


def test_o_descansar_nao_poda_mais():
    texto = (REPO_ROOT / "bin" / "descansar").read_text(encoding="utf-8")
    assert "aponta_candidatas" not in texto and "mesa podar" in texto
    assert "A poda nao e sua" in texto, "o roteiro do Sair diz que a poda e do bot"
