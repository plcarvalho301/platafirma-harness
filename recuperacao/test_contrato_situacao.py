"""Testes de contrato e conformidade de `situacao` (#2953, arq:0085 §4, §2; refatorado #2957).

Invariantes conferidas:
1. Lê a cadeia viva (impressão -> estado de serviço) e reporta payload {servivel, desde, impressao_id, degrau}.
2. Degrau mapeia nos estados canônicos (ancorado, declarado-não-servindo, sem-obra-não-julgado, órfão).
3. Procedência completa no item (invariante 1 do §3).
4. Envelope vazio ≤ 40 tokens medido com qwen2.5.json (invariante 3 do §3).
5. Uma linha por fonte consultada (invariante 4).
6. Sujeito não entra no envelope (invariante 5).
7. Fonte indisponível responde `fonte-nao-indexada` declarada, nunca zero (§4).
8. PEP nega por concessão quando sujeito sem acesso.
9. CLI `bin/situacao` obedece contrato de chamada e saída.

Desde #2957, a fonte é `GET /acervo/obras/{obra_id}/situacao` no `motor_acervo`, não mais
JSONL local (arq:0089 §2) — a escada de degraus e o casamento de obra migraram para o
outro lado do HTTP (`motor_acervo/acervo_consulta.py`). Os testes de CONTRATO injetam
`http=` (cliente falso, sempre rodam, julgam o que `situacao()` produz a partir de um
payload já resolvido); o de CLI (nível 2) exercita o subprocess de verdade contra o
serviço real, e é PULADO com motivo quando o serviço não serve as rotas novas ainda —
mesmo padrão de `test_contrato_wiki_acervo.py` (`rag_no_ar`/`wiki_no_ar`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from recuperacao.adaptadores.base import FonteIndisponivel
from recuperacao.disjuntor import EstadoDisjuntor, Painel
from recuperacao.envelope import Causa, Cobertura, Fonte
from recuperacao.pep import PEP
from recuperacao.situacao import situacao

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
TOKENIZADOR = os.path.join(RAIZ, "opt", "tokenizers", "qwen2.5.json")
BIN_SITUACAO = Path(__file__).resolve().parents[1] / "bin" / "situacao"
MOTOR_ACERVO_URL = os.environ.get(
    "MOTOR_ACERVO_URL", os.environ.get("RAG_API_URL", "http://127.0.0.1:8100")).rstrip("/")
RAG_API_TOKEN = os.environ.get("RAG_API_TOKEN", "")


# =============================================================================
# payloads determinísticos — o que `GET /acervo/obras/{id}/situacao` devolveria
# =============================================================================

PAYLOAD_ANCORADO = {
    "obra_id": "o1", "titulo": "Clean Architecture",
    "objeto": "acervo/1111111111111111111111111111111111111111111111111111111111111111",
    "servivel": True, "desde": "2026-08-15T10:00:00Z", "impressao_id": "imp-001",
    "degrau": "ancorado", "carimbo": "carimbo-o1", "casamento": "exato",
}
PAYLOAD_DECLARADO_NAO_SERVINDO = {
    "obra_id": "o2", "titulo": "Legacy Code",
    "objeto": "acervo/2222222222222222222222222222222222222222222222222222222222222222",
    "servivel": False, "desde": None, "impressao_id": "imp-002",
    "degrau": "declarado-nao-servindo", "carimbo": "carimbo-o2", "casamento": "exato",
}
PAYLOAD_ORFAO = {
    "obra_id": "o3", "titulo": "Documento Avulso Sem Metadados",
    "objeto": "acervo/3333333333333333333333333333333333333333333333333333333333333333",
    "servivel": True, "desde": "2026-08-01T10:00:00Z", "impressao_id": "imp-003",
    "degrau": "orfao", "carimbo": "carimbo-o3", "casamento": "exato",
}


def http_fixo(payload):
    """Cliente falso que devolve sempre o mesmo payload (ou `None` = 404)."""
    def _http(rota, aceita_ausente=False):
        return payload
    return _http


# =============================================================================
# 1. Testes de Contrato de Situação
# =============================================================================


def test_situacao_ancorado():
    """Obra classificada e com impressão servindo reporta degrau ancorado e servivel True."""
    env = situacao("Clean Architecture", http=http_fixo(PAYLOAD_ANCORADO))

    assert len(env.linhas) == 1
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert len(env.itens) == 1

    item = env.itens[0]
    assert item.procedencia.chave == "acervo:1111111111111111111111111111111111111111111111111111111111111111"
    assert item.conteudo is not None

    payload = json.loads(item.conteudo)
    assert payload["servivel"] is True
    assert payload["desde"] == "2026-08-15T10:00:00Z"
    assert payload["impressao_id"] == "imp-001"
    assert payload["degrau"] == "ancorado"


def test_situacao_declarado_nao_servindo():
    """Obra sem impressão em estado 'servindo' reporta declarado-nao-servindo e servivel False."""
    env = situacao("Legacy Code", http=http_fixo(PAYLOAD_DECLARADO_NAO_SERVINDO))

    assert len(env.itens) == 1
    payload = json.loads(env.itens[0].conteudo)
    assert payload["servivel"] is False
    assert payload["desde"] is None
    assert payload["degrau"] == "declarado-nao-servindo"


def test_situacao_orfao():
    """Obra sem classificação (sem domínio/subdomínio/conceito) reporta degrau orfao."""
    env = situacao("Documento Avulso Sem Metadados", http=http_fixo(PAYLOAD_ORFAO))

    assert len(env.itens) == 1
    payload = json.loads(env.itens[0].conteudo)
    assert payload["degrau"] == "orfao"


def test_situacao_obra_inexistente_retorna_vazio():
    """A API responde 404 (o cliente devolve `None`) -> envelope vazio."""
    env = situacao("Obra Inexistente Fantasma XYZ", http=http_fixo(None))
    assert env.cobertura == Cobertura.VAZIA
    assert env.itens == []


def test_situacao_sujeito_nao_entra_no_envelope():
    """Invariante 5: o sujeito nunca aparece no envelope."""
    env = situacao("Clean Architecture", sujeito="claudinho-dados", http=http_fixo(PAYLOAD_ANCORADO))
    d = env.para_json()
    assert "sujeito" not in d
    assert "sujeito" not in json.dumps(d)


def test_situacao_vazio_cabe_no_teto_40_tokens():
    """Invariante 3: envelope vazio ≤ 40 tokens no tokenizador."""
    env = situacao("Inexistente", http=http_fixo(None))
    texto = env.para_texto()

    if os.path.isfile(TOKENIZADOR):
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(TOKENIZADOR)
        n = len(tok.encode(texto).ids)
        assert n <= 40, f"envelope vazio a {n} tokens (teto 40): {texto}"
    else:
        assert len(texto.encode("utf-8")) <= 120


def test_situacao_fonte_indisponivel_responde_nao_indexada_nunca_zero():
    """Regra dura arq:0085 §4: fonte que não alcança o vivo responde indeterminavel, nunca zero."""
    def http_caido(rota, aceita_ausente=False):
        raise FonteIndisponivel(Causa.SEM_ROTA, "conexão recusada")

    env = situacao("Clean Architecture", http=http_caido)
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert env.linhas[0].causa == Causa.SEM_ROTA
    assert env.itens == []


def test_situacao_pep_negativo():
    """PEP recusa acesso quando o sujeito não tem concessão."""
    class PEPMudo(PEP):
        def autoriza(self, *args, **kwargs):
            from recuperacao.pep import Negativa
            return [Negativa(fonte=Fonte.ACERVO, alvo="acervo:*", regra="padrao", motivo="negado")]

    env = situacao("Clean Architecture", pep=PEPMudo(), http=http_fixo(PAYLOAD_ANCORADO))
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert env.linhas[0].causa == Causa.SEM_CONCESSAO


def test_situacao_disjuntor_aberto():
    """Disjuntor aberto responde em 0 ms com disjuntor-aberto."""
    painel = Painel()
    painel[Fonte.ACERVO]._estado = EstadoDisjuntor.ABERTO
    painel[Fonte.ACERVO]._aberto_em = 10000000000.0

    env = situacao("Clean Architecture", painel=painel, http=http_fixo(PAYLOAD_ANCORADO))
    assert env.linhas[0].causa == Causa.DISJUNTOR_ABERTO
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA


# =============================================================================
# 2. Testes de Execução CLI de bin/situacao — os dois primeiros não tocam a rede;
#    o terceiro exercita o subprocess de verdade contra o motor_acervo real.
# =============================================================================


def _motor_acervo_com_rotas_novas() -> bool:
    """`/health` respondendo não basta: o serviço velho (pré-#2957) também responde.
    Confere se a rota `/acervo/*` já existe (serviço redeployado)."""
    try:
        req = urllib.request.Request(
            f"{MOTOR_ACERVO_URL}/acervo/conceitos",
            headers={"authorization": f"Bearer {RAG_API_TOKEN}"} if RAG_API_TOKEN else {})
        with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310
            return r.status < 500
    except urllib.error.HTTPError as e:
        return e.code != 404
    except Exception:  # noqa: BLE001
        return False


motor_acervo_no_ar = pytest.mark.skipif(
    not _motor_acervo_com_rotas_novas(),
    reason=f"motor_acervo em {MOTOR_ACERVO_URL} sem as rotas /acervo/* (não redeployado "
          "com #2957, ou fora do ar) — CLI pulado, não mascarado")


def test_bin_situacao_sem_argumento_sai_2():
    """Chamada sem argumentos imprime o uso e sai com código 2. Não toca a rede."""
    p = subprocess.run([sys.executable, str(BIN_SITUACAO)], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


def test_bin_situacao_ajuda_sai_2():
    """-h/--help sai com código 2. Não toca a rede."""
    p = subprocess.run([sys.executable, str(BIN_SITUACAO), "-h"], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


@motor_acervo_no_ar
def test_bin_situacao_executa_e_emite_payload():
    """Execução com obra retorna envelope com payload formatado, contra o serviço real."""
    p = subprocess.run(
        [sys.executable, str(BIN_SITUACAO), "2020-devops-transformation-google-cloud-dora", "--json"],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    d = json.loads(p.stdout)
    assert "cobertura" in d
    assert len(d.get("itens", [])) >= 1
    conteudo = json.loads(d["itens"][0]["conteudo"])
    assert "degrau" in conteudo
    assert "servivel" in conteudo


# =============================================================================
# Regressão: ramo `cache is not None` chama a API real do Cache (le/grava).
# Mesmo bug de `descobrir` — cache.obtem/grava-4-args escapavam do except
# SemCache. Trava o contrato de chamada. arq:0085.
# =============================================================================


class _CacheFalsoSit:
    """Cache mínimo que honra a API real (`le`/`grava`)."""

    def __init__(self, retorno=None):
        self.retorno = retorno
        self.leu: list = []
        self.gravou: list = []

    def le(self, fonte, ch):
        self.leu.append((fonte, ch))
        return self.retorno

    def grava(self, fonte, ch, r):
        self.gravou.append((fonte, ch, r))
        return True


def test_situacao_miss_usa_api_real_do_cache():
    """Miss: consulta `cache.le` e grava `(fonte, ch, Resultado)` — 3 args, sem estourar."""
    from recuperacao.adaptadores.base import Resultado

    cache = _CacheFalsoSit(retorno=None)
    env = situacao("Clean Architecture", cache=cache, http=http_fixo(PAYLOAD_ANCORADO))
    assert env is not None
    assert cache.leu, "situacao deve consultar cache.le no miss"
    assert cache.gravou, "situacao deve gravar o resultado no miss"
    for _fonte, _ch, r in cache.gravou:
        assert isinstance(r, Resultado)


def test_situacao_hit_de_cache_retorna_sem_reler_acervo():
    """Hit: `cache.le` devolve Resultado e situacao devolve-o sem regravar."""
    from recuperacao.adaptadores.base import Resultado

    semente = situacao("Clean Architecture", http=http_fixo(PAYLOAD_ANCORADO))
    cache = _CacheFalsoSit(retorno=Resultado(linha=semente.linhas[0], itens=semente.itens))
    env = situacao("Clean Architecture", cache=cache, http=http_fixo(PAYLOAD_ANCORADO))
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert not cache.gravou, "hit não deve regravar"
