"""bin/_motor/juiz.py — o juiz do piloto da escada (card #3350; padrao protocolo-medicao-rag, «O juiz»).

A lógica (prompt com o critério que o dono viu, mensagem, leitura da saída do modelo, novas tentativas e o corpo que
vai ao banco) se mede com um gerador de mentira. O modelo real se confere no ar, pela rodada do piloto.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import juiz  # noqa: E402

CRITERIO = {
    "criterio_versao": "v1",
    "graus": [{"id": g, "rotulo": g, "curto": g, "definicao": f"definição de {g}.", "exemplo": f"exemplo de {g}."}
              for g in ("boa", "parcial", "vazia", "enganosa", "irrelevante")],
    "desempate": "Graus vizinhos: o mais baixo.",
}
GRAUS = juiz.graus_do_criterio(CRITERIO)
SECOES = [{"chave": f"uuid-{i}", "titulo": f"Obra › Seção {i}", "texto": f"texto da seção {i}"} for i in (1, 2)]
MAPA = [{"afirmacao": "A política exige X.", "secoes": ["uuid-1"]}, {"afirmacao": "O prazo é Y.", "secoes": ["uuid-2", "uuid-9"]}]


def saida(qualidade="parcial", embasamento=True, afirm=(1, 2), secoes=(1, 2)):
    return json.dumps({"qualidade": qualidade, "embasamento": embasamento,
                       "por_afirmacao": [{"afirmacao": a, "sustentada": True, "motivo": "a seção diz"} for a in afirm],
                       "por_trecho": [{"secao": s, "grau": "responde"} for s in secoes], "motivo": "falta o artigo"})


def test_prompt_traz_o_criterio_que_o_dono_viu_e_o_hash_muda_com_ele():
    s = juiz.sistema(CRITERIO)
    for g in GRAUS:
        assert f"- {g}: definição de {g}. Exemplo: exemplo de {g}." in s
    assert "versão v1" in s and "Graus vizinhos: o mais baixo." in s and "{GRAUS}" not in s
    outro = {**CRITERIO, "desempate": "outro"}
    assert juiz.prompt_hash(s) != juiz.prompt_hash(juiz.sistema(outro))


def test_mensagem_numera_mapa_e_secoes_e_nao_mostra_chave():
    m = juiz.montar_mensagem("pergunta?", "Resposta.", SECOES, MAPA)
    assert "1. A política exige X. → seções 1" in m and "2. O prazo é Y. → seções 2" in m
    assert "[1] Obra › Seção 1" in m and "uuid-" not in m
    assert "(vazio" in juiz.montar_mensagem("p", "r", SECOES, [])


@pytest.mark.parametrize("ruim", [
    "não é json",
    saida(qualidade="otima"),
    saida(embasamento="sim"),
    saida(afirm=(1,)),                 # faltou julgar uma afirmação
    saida(afirm=(1, 2, 3)),            # afirmação que não existe
    saida(secoes=(1, 3)),              # seção fora da lista
    json.dumps({"qualidade": "boa", "embasamento": True}),
])
def test_saida_fora_do_esquema_e_none(ruim):
    assert juiz.interpretar(ruim, GRAUS, 2, 2) is None


def test_saida_com_cerca_de_codigo_passa():
    assert juiz.interpretar("```json\n" + saida() + "\n```", GRAUS, 2, 2)["qualidade"] == "parcial"


def test_seis_respostas_falsas_seis_julgamentos_validos_e_corpo_do_banco():
    chamadas = []

    def gerar(sistema, usuario, tentativa):
        chamadas.append(tentativa)
        return {"texto": "lixo" if tentativa == 0 and len(chamadas) == 1 else saida("irrelevante", False), "segundos": 1.5}

    s = juiz.sistema(CRITERIO)
    julgados = {f"re-{i}": juiz.julgar_resposta(s, GRAUS, "p?", f"r{i}", SECOES, MAPA, gerar) for i in range(6)}
    assert len(julgados) == 6 and chamadas[:2] == [0, 1] and len(chamadas) == 7
    assert julgados["re-0"]["carimbo"]["tentativas"] == 2
    assert julgados["re-1"]["por_trecho"][0] == {"secao": 1, "grau": "responde", "chave": "uuid-1"}
    corpo = juiz.marcas_para_gravar("L", julgados, "claude-x", juiz.prompt_hash(s))
    assert corpo["lote_id"] == "L" and len(corpo["marcas"]) == 6
    m = corpo["marcas"][0]
    assert set(m) == {"resposta_id", "qualidade", "embasamento", "por_afirmacao", "por_trecho", "modelo", "prompt_hash"}
    assert m["qualidade"] == "irrelevante" and m["embasamento"] is False


def test_tres_saidas_ruins_levantam_e_nao_inventam_marca():
    with pytest.raises(RuntimeError):
        juiz.julgar_resposta(juiz.sistema(CRITERIO), GRAUS, "p", "r", SECOES, MAPA, lambda *a: {"texto": "{}", "segundos": 0})
