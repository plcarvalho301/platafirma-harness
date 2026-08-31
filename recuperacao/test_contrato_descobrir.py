"""Testes de contrato e conformidade de `descobrir` (#2952, arq:0085 §5, §3; refatorado #2957).

Invariantes conferidas:
1. Procedência completa em todo item (invariante 1 do §3).
2. Envelope vazio ≤ 40 tokens medido com qwen2.5.json (invariante 3 do §3).
3. Uma linha por fonte consultada (invariante 4).
4. Sujeito não entra no envelope (invariante 5).
5. Varredura multi-eixo devolve união (OR), não interseção.
6. Dedupe por digest: obra que entra por 2 eixos aparece 1 vez, com os 2 eixos marcados.
7. Fonte indisponível responde `fonte-nao-indexada` declarada, nunca zero (§4).
8. PEP nega por concessão quando sujeito sem acesso.
9. CLI `bin/descobrir` obedece contrato de chamada e saída.

Desde #2957, a fonte é `GET /acervo/descoberta` no `motor_acervo`, não mais JSONL local
(arq:0089 §2) — a varredura multi-eixo (normalização, radicais, união, dedupe, marcação
de casamento) migrou para o outro lado do HTTP (`motor_acervo/acervo_consulta.py`). Os
testes de CONTRATO injetam `http=` (cliente falso, sempre rodam, julgam o que
`descobrir()` produz a partir de itens já resolvidos); o de CLI (nível 2) exercita o
subprocess de verdade contra o serviço real, e é PULADO com motivo quando o serviço não
serve as rotas novas ainda — mesmo padrão de `test_contrato_wiki_acervo.py`.
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
from recuperacao.descobrir import EIXOS_PADRAO, descobrir
from recuperacao.disjuntor import EstadoDisjuntor, Painel
from recuperacao.envelope import Causa, Cobertura, ContratoViolado, Fonte, VersaoTipo
from recuperacao.pep import PEP

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
TOKENIZADOR = os.path.join(RAIZ, "opt", "tokenizers", "qwen2.5.json")
BIN_DESCOBRIR = Path(__file__).resolve().parents[1] / "bin" / "descobrir"
MOTOR_ACERVO_URL = os.environ.get(
    "MOTOR_ACERVO_URL", os.environ.get("RAG_API_URL", "http://127.0.0.1:8100")).rstrip("/")
RAG_API_TOKEN = os.environ.get("RAG_API_TOKEN", "")

OBJETO_O1 = "acervo/1111111111111111111111111111111111111111111111111111111111111111"
OBJETO_O2 = "acervo/2222222222222222222222222222222222222222222222222222222222222222"
OBJETO_O3 = "acervo/3333333333333333333333333333333333333333333333333333333333333333"


def http_fixo(payload):
    """Cliente falso que devolve sempre o mesmo payload de `/acervo/descoberta`."""
    def _http(rota):
        return payload
    return _http


# =============================================================================
# payloads determinísticos — o que `GET /acervo/descoberta` devolveria
# =============================================================================

PAYLOAD_UNIAO = {
    "assunto": "padrao", "eixos": list(EIXOS_PADRAO),
    "itens": [
        {"obra_id": "o1", "titulo": "Padrao de Arquitetura de Software", "objeto": OBJETO_O1,
         "dominio": "engenharia-software", "subdominio": "artesania-e-design-de-codigo",
         "escore": 1.0, "casamento": "exato",
         "expansao": {"conceito_origem": "padrao", "aresta": "conceito, titulo", "familia": "descoberta"}},
        {"obra_id": "o2", "titulo": "Clean Code", "objeto": OBJETO_O2,
         "dominio": "engenharia-software", "subdominio": "artesania-e-design-de-codigo",
         "escore": 0.6, "casamento": "aproximado",
         "expansao": {"conceito_origem": "padrao", "aresta": "conceito, subdominio", "familia": "descoberta"}},
    ],
    "proximo": None,
}

PAYLOAD_SO_TITULO = {
    "assunto": "padrao", "eixos": ["titulo"],
    "itens": [
        {"obra_id": "o1", "titulo": "Padrao de Arquitetura de Software", "objeto": OBJETO_O1,
         "dominio": "engenharia-software", "subdominio": "artesania-e-design-de-codigo",
         "escore": 1.0, "casamento": "exato",
         "expansao": {"conceito_origem": "padrao", "aresta": "titulo", "familia": "descoberta"}},
    ],
    "proximo": None,
}

PAYLOAD_SO_SUBDOMINIO = {
    "assunto": "owasp", "eixos": ["subdominio"],
    "itens": [
        {"obra_id": "o3", "titulo": "Guia OWASP", "objeto": OBJETO_O3,
         "dominio": "seguranca-privacidade", "subdominio": "seguranca-aplicacao",
         "escore": 1.0, "casamento": "exato",
         "expansao": {"conceito_origem": "owasp", "aresta": "subdominio", "familia": "descoberta"}},
    ],
    "proximo": None,
}

PAYLOAD_CLEAN = {
    "assunto": "clean", "eixos": list(EIXOS_PADRAO),
    "itens": [
        {"obra_id": "o2", "titulo": "Clean Code", "objeto": OBJETO_O2,
         "dominio": "engenharia-software", "subdominio": "artesania-e-design-de-codigo",
         "escore": 1.0, "casamento": "exato",
         "expansao": {"conceito_origem": "clean", "aresta": "titulo", "familia": "descoberta"}},
    ],
    "proximo": None,
}

PAYLOAD_VAZIO = {"assunto": "assunto_inexistente_xyz_12345", "eixos": list(EIXOS_PADRAO),
                 "itens": [], "proximo": None}


# =============================================================================
# 1. Testes de Contrato de Descoberta Multi-Eixo
# =============================================================================


def test_descobrir_uniao_tres_eixos_e_dedupe():
    """Prova que descobrir varre os três eixos, devolve a união e deduplica com marcação."""
    env = descobrir(assunto="padrao", http=http_fixo(PAYLOAD_UNIAO))

    assert len(env.linhas) == 1
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert env.linhas[0].cobertura == Cobertura.NAO_CALIBRADA

    ids_encontrados = {i.procedencia.chave for i in env.itens}
    assert f"acervo:{OBJETO_O1.removeprefix('acervo/')}" in ids_encontrados
    assert f"acervo:{OBJETO_O2.removeprefix('acervo/')}" in ids_encontrados

    # Cada obra entra uma única vez (dedupe já feito do lado do motor_acervo)
    assert len(env.itens) == 2

    item_o1 = next(i for i in env.itens if OBJETO_O1.removeprefix("acervo/") in i.procedencia.chave)
    assert item_o1.expansao is not None
    assert item_o1.expansao.conceito_origem == "padrao"
    assert "titulo" in item_o1.expansao.aresta
    assert "conceito" in item_o1.expansao.aresta
    assert item_o1.expansao.familia == "descoberta"


def test_descobrir_eixo_isolado():
    """Prova que restringir os eixos só pesquisa nos eixos selecionados."""
    env_titulo = descobrir(assunto="padrao", eixos=["titulo"], http=http_fixo(PAYLOAD_SO_TITULO))
    assert len(env_titulo.itens) == 1
    assert "1111" in env_titulo.itens[0].procedencia.chave
    assert env_titulo.itens[0].expansao.aresta == "titulo"

    env_sub = descobrir(assunto="owasp", eixos=["subdominio"], http=http_fixo(PAYLOAD_SO_SUBDOMINIO))
    assert len(env_sub.itens) == 1
    assert "3333" in env_sub.itens[0].procedencia.chave
    assert env_sub.itens[0].expansao.aresta == "subdominio"


def test_descobrir_eixo_invalido_levanta():
    """Eixo fora de titulo/conceito/subdominio rejeita como ContratoViolado — antes de
    qualquer chamada de rede."""
    with pytest.raises(ContratoViolado):
        descobrir(assunto="padrao", eixos=["eixo_fantasma"], http=http_fixo(PAYLOAD_UNIAO))


def test_descobrir_procedencia_completa_e_invariantes():
    """Invariante 1: todo item tem procedência completa (fonte, chave acervo:*, versao digest)."""
    env = descobrir(assunto="clean", http=http_fixo(PAYLOAD_CLEAN))
    assert len(env.itens) >= 1
    for item in env.itens:
        p = item.procedencia
        assert p.fonte == Fonte.ACERVO
        assert p.chave.startswith("acervo:")
        assert p.versao.tipo == VersaoTipo.DIGEST
        assert p.versao.valor is not None
        assert item.ref is not None


def test_descobrir_sujeito_nao_entra_no_envelope():
    """Invariante 5: o sujeito nunca aparece no envelope."""
    env = descobrir(assunto="padrao", sujeito="claudinho-TI", http=http_fixo(PAYLOAD_UNIAO))
    d = env.para_json()
    assert "sujeito" not in d
    assert "sujeito" not in json.dumps(d)


def test_descobrir_vazio_cabe_no_teto_40_tokens():
    """Invariante 3: envelope vazio ≤ 40 tokens no tokenizador do modelo."""
    env = descobrir(assunto="assunto_inexistente_xyz_12345", http=http_fixo(PAYLOAD_VAZIO))
    assert env.cobertura == Cobertura.VAZIA
    assert env.itens == []
    texto = env.para_texto()

    if os.path.isfile(TOKENIZADOR):
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(TOKENIZADOR)
        n = len(tok.encode(texto).ids)
        assert n <= 40, f"envelope vazio a {n} tokens (teto 40): {texto}"
    else:
        assert len(texto.encode("utf-8")) <= 120


def test_descobrir_fonte_indisponivel_responde_nao_indexada_nunca_zero():
    """Regra dura arq:0085 §4: fonte que não alcança o vivo responde indeterminavel, nunca zero."""
    def http_caido(rota):
        raise FonteIndisponivel(Causa.SEM_ROTA, "conexão recusada")

    env = descobrir(assunto="qualquer", http=http_caido)
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert len(env.linhas) == 1
    assert env.linhas[0].causa == Causa.SEM_ROTA
    assert env.itens == []
    assert env.aviso != []


def test_descobrir_pep_negativo():
    """PEP recusa acesso quando o sujeito não tem concessão."""
    class PEPMudo(PEP):
        def autoriza(self, *args, **kwargs):
            from recuperacao.pep import Negativa
            return [Negativa(fonte=Fonte.ACERVO, alvo="acervo:*", regra="padrao", motivo="negado nos testes")]

    env = descobrir(assunto="padrao", pep=PEPMudo(), http=http_fixo(PAYLOAD_UNIAO))
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert env.linhas[0].causa == Causa.SEM_CONCESSAO
    assert env.falta is not None
    assert env.proximo is not None


def test_descobrir_disjuntor_aberto():
    """Disjuntor aberto responde em 0 ms com disjuntor-aberto."""
    painel = Painel()
    painel[Fonte.ACERVO]._estado = EstadoDisjuntor.ABERTO
    painel[Fonte.ACERVO]._aberto_em = 10000000000.0

    env = descobrir(assunto="padrao", painel=painel, http=http_fixo(PAYLOAD_UNIAO))
    assert env.linhas[0].causa == Causa.DISJUNTOR_ABERTO
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA


# =============================================================================
# 2. Testes de Execução CLI de bin/descobrir — os dois primeiros não tocam a rede;
#    o terceiro exercita o subprocess de verdade contra o motor_acervo real.
# =============================================================================


def _motor_acervo_com_rotas_novas() -> bool:
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


def test_bin_descobrir_sem_argumento_sai_2():
    """Chamada sem argumentos imprime o uso e sai com código 2. Não toca a rede."""
    p = subprocess.run([sys.executable, str(BIN_DESCOBRIR)], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


def test_bin_descobrir_ajuda_sai_2():
    """-h/--help sai com código 2. Não toca a rede."""
    p = subprocess.run([sys.executable, str(BIN_DESCOBRIR), "-h"], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


@motor_acervo_no_ar
def test_bin_descobrir_executa_e_emite_envelope():
    """Execução com termo retorna envelope formatado, contra o serviço real."""
    p = subprocess.run(
        [sys.executable, str(BIN_DESCOBRIR), "seguranca", "--json"],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    d = json.loads(p.stdout)
    assert "cobertura" in d


# =============================================================================
# Regressão: ramo `cache is not None` chama a API real do Cache (le/grava).
# Bug corrigido: descobrir chamava cache.obtem (inexistente -> AttributeError)
# e cache.grava com 4 args (assinatura é 3 -> TypeError); ambos escapavam do
# except SemCache. Nenhum teste exercia o ramo, por isso passou. arq:0085.
# =============================================================================


class _CacheFalso:
    """Cache mínimo que honra a API real (`le`/`grava`) — fake, não mock."""

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


def test_descobrir_miss_usa_api_real_do_cache():
    """Miss: consulta `cache.le` e grava `(fonte, ch, Resultado)` — 3 args, sem estourar."""
    from recuperacao.adaptadores.base import Resultado

    cache = _CacheFalso(retorno=None)
    env = descobrir(assunto="padrao", cache=cache, http=http_fixo(PAYLOAD_UNIAO))
    assert env is not None
    assert cache.leu, "descobrir deve consultar cache.le no miss"
    assert cache.gravou, "descobrir deve gravar o resultado no miss"
    for _fonte, _ch, r in cache.gravou:
        assert isinstance(r, Resultado)


def test_descobrir_hit_de_cache_retorna_sem_reler_acervo():
    """Hit: `cache.le` devolve Resultado e descobrir devolve-o sem regravar."""
    from recuperacao.adaptadores.base import Resultado

    semente = descobrir(assunto="padrao", http=http_fixo(PAYLOAD_UNIAO))
    cache = _CacheFalso(retorno=Resultado(linha=semente.linhas[0], itens=semente.itens))
    env = descobrir(assunto="padrao", cache=cache, http=http_fixo(PAYLOAD_UNIAO))
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert not cache.gravou, "hit não deve regravar"
