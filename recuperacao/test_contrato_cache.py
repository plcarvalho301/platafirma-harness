"""Contrato do cache do recuperador (#2308) — chave por fonte, TTL, `rec:stat`.

Dois níveis, como nos demais: contrato com cliente falso (roda sempre) e conformidade
contra o `motor-cache` vivo, pulada com motivo quando ele não está no ar.
"""

from __future__ import annotations

import json
import time
import zlib

import pytest

from recuperacao import cache as C
from recuperacao.adaptadores.base import Adaptador, FonteIndisponivel, Resultado
from recuperacao.envelope import Causa, Cobertura, Fonte, Item, LinhaFonte, Procedencia, Versao, VersaoTipo
from recuperacao.fontes import Classe


# ------------------------------------------------------------------ dublês


class ValkeyFalso:
    """Só o que o cache chama: get, setex, delete, hincrby, hgetall, sismember."""

    def __init__(self, aposentadas=()) -> None:
        self.dados: dict[str, bytes] = {}
        self.ttl: dict[str, int] = {}
        self.stat: dict[str, dict[str, int]] = {}
        self.aposentadas = set(aposentadas)

    def get(self, ch):
        return self.dados.get(ch)

    def set(self, ch, valor, ex=None):
        self.dados[ch], self.ttl[ch] = valor, ex
        return True

    def delete(self, ch):
        self.dados.pop(ch, None)
        return 1

    def hincrby(self, ch, campo, quanto=1):
        self.stat.setdefault(ch, {}).setdefault(campo, 0)
        self.stat[ch][campo] += quanto
        return self.stat[ch][campo]

    def hgetall(self, ch):
        return {k.encode(): str(v).encode() for k, v in self.stat.get(ch, {}).items()}

    def sismember(self, ch, v):
        return v in self.aposentadas


class ValkeyMudo(ValkeyFalso):
    def get(self, ch):
        raise ConnectionError("cache fora do ar")

    def set(self, *a, **kw):
        raise ConnectionError("cache fora do ar")

    def hincrby(self, *a, **kw):
        raise ConnectionError("cache fora do ar")


class FonteFalsa(Adaptador):
    """Adaptador exato mínimo, que CONTA quantas vezes a fonte foi de fato consultada."""

    fonte = Fonte("board")

    def __init__(self, carimbo="203/393", itens=1, quebra_carimbo=False) -> None:
        self._c, self._n, self._quebra = carimbo, itens, quebra_carimbo
        self.buscas = 0

    def _carimbo(self):
        if self._quebra:
            raise FonteIndisponivel(Causa.FORA_DO_AR, "sem carimbo")
        return self._c

    def _busca(self, alvo, filtros, k, texto):
        self.buscas += 1
        return [
            Item(procedencia=Procedencia(fonte=self.fonte, chave=f"item:{i}",
                                         versao=Versao(VersaoTipo.SEQ, str(100 + i))),
                 ref=f"#{i} — item de teste")
            for i in range(self._n)
        ]


class AcervoFalso(FonteFalsa):
    fonte = Fonte("acervo")

    def _busca(self, alvo, filtros, k, texto):
        self.buscas += 1
        return [Item(procedencia=Procedencia(fonte=self.fonte, chave="acervo:abc#s1",
                                             versao=Versao(VersaoTipo.SEQ, "impressao-9")),
                     ref="obra tal, seção 1")]


@pytest.fixture
def falso():
    return ValkeyFalso()


@pytest.fixture
def cache(falso):
    return C.Cache(cliente=falso)


# ================================================================= 1. a chave


def test_chave_tem_fonte_e_carimbo_e_nao_tem_sujeito():
    ch = C.chave(Fonte("board"), "203/393", "item:2300", None)
    assert ch.startswith("rec:board:203/393:")
    assert "claudinho" not in ch, "§9: sujeito NÃO entra na chave — o PEP roda antes"


def test_chave_do_acervo_nao_carrega_carimbo():
    """Carimbo na chave invalidaria o acervo inteiro a cada re-corte de UMA obra (§9)."""
    ch = C.chave(Fonte("acervo"), "acervo:sha-novo", "pergunta", None)
    assert ch.startswith("rec:acervo:")
    assert "sha-novo" not in ch


def test_chave_e_estavel_sob_ordem_de_filtro_e_espaco():
    a = C.chave(Fonte("board"), "1", " item:2300 ", {"cadeira": "x", "estado": "y"})
    b = C.chave(Fonte("board"), "1", "item:2300", {"estado": "y", "cadeira": "x"})
    assert a == b, "mesma consulta com chave diferente é miss fabricado"


def test_chave_separa_k_e_texto():
    base = dict(fonte=Fonte("board"), carimbo="1", alvo="a", filtros=None)
    assert C.chave(**base, k=3) != C.chave(**base, k=8)
    assert C.chave(**base, texto="secao") != C.chave(**base, texto="nenhum")


def test_carimbo_novo_muda_a_chave():
    """É a invalidação inteira do desenho: chave nova + LRU, sem varredura."""
    assert C.chave(Fonte("board"), "203/393", "a", None) != C.chave(Fonte("board"), "204/393", "a", None)


# ================================================================= 2. hit e miss


def test_primeira_chamada_e_miss_e_segunda_e_hit(cache):
    a = FonteFalsa()
    r1, veio1 = C.busca_com_cache(a, "item:2300", cache=cache)
    r2, veio2 = C.busca_com_cache(a, "item:2300", cache=cache)
    assert (veio1, veio2) == (False, True)
    assert a.buscas == 1, "o hit não pode ter ido à fonte"
    assert [i.procedencia.chave for i in r2.itens] == [i.procedencia.chave for i in r1.itens]


def test_hit_reconstroi_procedencia_pelo_construtor_vivo(cache):
    a = FonteFalsa()
    C.busca_com_cache(a, "item:2300", cache=cache)
    r, _ = C.busca_com_cache(a, "item:2300", cache=cache)
    p = r.itens[0].procedencia
    assert isinstance(p, Procedencia) and p.versao.tipo is VersaoTipo.SEQ
    assert r.linha.carimbo == "203/393"


def test_carimbo_novo_derruba_o_hit(cache):
    a = FonteFalsa()
    C.busca_com_cache(a, "item:2300", cache=cache)
    a._c = "204/393"
    _, veio = C.busca_com_cache(a, "item:2300", cache=cache)
    assert veio is False and a.buscas == 2


def test_valor_corrompido_vira_miss_e_some(cache, falso):
    a = FonteFalsa()
    C.busca_com_cache(a, "item:2300", cache=cache)
    ch = next(iter(falso.dados))
    falso.dados[ch] = b'{"linha": {"fonte": "board", "cobertura": "invencao"}}'
    _, veio = C.busca_com_cache(a, "item:2300", cache=cache)
    assert veio is False, "contrato velho no cache não pode entrar no envelope"


def test_cache_mudo_e_miss_e_nao_falha():
    a = FonteFalsa()
    r, veio = C.busca_com_cache(a, "item:2300", cache=C.Cache(cliente=ValkeyMudo()))
    assert veio is False and len(r.itens) == 1


def test_sem_carimbo_a_leitura_vai_a_fonte_sem_cache(falso):
    """Sem carimbo não há chave honesta — e chave com carimbo falso serviria board velho
    para sempre, que é a falha silenciosa que o #2307 existe para evitar."""
    a = FonteFalsa(quebra_carimbo=True)
    r, veio = C.busca_com_cache(a, "item:2300", cache=C.Cache(cliente=falso))
    assert veio is False and falso.dados == {}


# ================================================================= 3. o que não se cacheia


def test_fonte_caida_nao_entra_no_cache(cache, falso):
    class Caida(FonteFalsa):
        def _busca(self, alvo, filtros, k, texto):
            raise FonteIndisponivel(Causa.FORA_DO_AR, "caiu")

    r, _ = C.busca_com_cache(Caida(), "item:2300", cache=cache)
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert falso.dados == {}, "TTL sobre fonte caída transforma 1 s de queda em 60 s"


def test_resposta_vazia_e_cacheavel(cache, falso):
    """Vazia é resposta da fonte, não falha dela: rebuscar toda vez pagaria a consulta
    inteira para reconfirmar uma ausência que o carimbo já protege."""
    r, _ = C.busca_com_cache(FonteFalsa(itens=0), "item:999999", cache=cache)
    assert r.linha.cobertura is Cobertura.VAZIA
    assert len(falso.dados) == 1


# ================================================================= 4. TTL e compressão


def test_ttl_por_classe(cache, falso):
    C.busca_com_cache(FonteFalsa(), "a", cache=cache)
    assert set(falso.ttl.values()) == {C.TTL_S[Classe.EXATA]}
    assert C.TTL_S[Classe.SEMANTICA] == 7 * 24 * 3600


def test_comprime_acima_de_quatro_kb(cache, falso):
    C.busca_com_cache(FonteFalsa(itens=200), "a", k=200, cache=cache)
    bruto = next(iter(falso.dados.values()))
    assert bruto.startswith(C.MARCA_ZLIB)
    assert len(bruto) < len(zlib.decompress(bruto[2:]))


def test_pequeno_nao_comprime(cache, falso):
    C.busca_com_cache(FonteFalsa(itens=1), "a", cache=cache)
    assert not next(iter(falso.dados.values())).startswith(C.MARCA_ZLIB)


# ================================================================= 5. rec:stat


def test_stat_conta_hit_miss_bytes_e_idade(cache, falso):
    a = FonteFalsa()
    C.busca_com_cache(a, "a", cache=cache)
    C.busca_com_cache(a, "a", cache=cache)
    d = cache.estatistica(Fonte("board"))
    assert (d["hit"], d["miss"]) == (1, 1)
    assert d["bytes"] > 0
    assert d["idade"] >= 0


def test_stat_e_por_fonte_e_nao_agregada(cache):
    C.busca_com_cache(FonteFalsa(), "a", cache=cache)
    assert cache.estatistica(Fonte("board"))["miss"] == 1
    assert cache.estatistica(Fonte("fila"))["miss"] == 0


def test_stat_zerada_existe_em_vez_de_faltar(cache):
    d = cache.estatistica(Fonte("wiki"))
    assert d == {"hit": 0, "miss": 0, "bytes": 0, "idade": 0}


def test_stat_mudo_nao_derruba_a_leitura():
    r, veio = C.busca_com_cache(FonteFalsa(), "a", cache=C.Cache(cliente=ValkeyMudo()))
    assert len(r.itens) == 1 and veio is False


# ================================================================= 6. acervo


def test_acervo_desligado_por_padrao(cache, falso, monkeypatch):
    """§9 — a ordem é `#167 → #283 → cache`, e os dois estão em lapidação (20/08/2026)."""
    monkeypatch.setattr(C, "ACERVO_LIGADO", False)
    a = AcervoFalso()
    C.busca_com_cache(a, "pergunta", cache=cache)
    _, veio = C.busca_com_cache(a, "pergunta", cache=cache)
    assert veio is False and a.buscas == 2 and falso.dados == {}


def test_acervo_ligado_pelo_escape_nomeado(falso, monkeypatch):
    monkeypatch.setattr(C, "ACERVO_LIGADO", True)
    cache = C.Cache(cliente=falso)
    a = AcervoFalso()
    C.busca_com_cache(a, "pergunta", cache=cache)
    _, veio = C.busca_com_cache(a, "pergunta", cache=cache)
    assert veio is True and a.buscas == 1


def test_hit_de_acervo_com_impressao_aposentada_e_recusado(monkeypatch):
    monkeypatch.setattr(C, "ACERVO_LIGADO", True)
    falso = ValkeyFalso(aposentadas={"impressao-9"})
    cache = C.Cache(cliente=falso)
    a = AcervoFalso()
    C.busca_com_cache(a, "pergunta", cache=cache)
    _, veio = C.busca_com_cache(a, "pergunta", cache=cache)
    assert veio is False, "citação de impressão aposentada não pode ser servida do cache"


def test_hit_de_acervo_com_cache_mudo_no_sismember_reprova(monkeypatch):
    """Fail-closed: não sabendo se a impressão ainda serve, rebusca."""
    monkeypatch.setattr(C, "ACERVO_LIGADO", True)

    class SemSet(ValkeyFalso):
        def sismember(self, *a, **kw):
            raise ConnectionError("sem set")

    cache = C.Cache(cliente=SemSet())
    a = AcervoFalso()
    C.busca_com_cache(a, "p", cache=cache)
    _, veio = C.busca_com_cache(a, "p", cache=cache)
    assert veio is False


# ================================================================= 7. conformidade


def motor_cache_no_ar() -> bool:
    try:
        C.Cache().cliente.ping()
    except Exception:  # noqa: BLE001
        return False
    return True


@pytest.mark.skipif(not motor_cache_no_ar(), reason=f"motor-cache fora do ar em {C.HOST}:{C.PORTA}")
def test_conformidade_instancia_e_a_de_cache_e_nao_a_de_memoria():
    """§9 — `msg-mem` (6380) guarda `mem:*` e `fita:*`; `allkeys-lru` lá despejaria a
    mesa. O que se confere é a política DA INSTÂNCIA servida, não a porta escrita aqui."""
    c = C.Cache().cliente

    def conf(nome: str) -> str:
        d = c.config_get(nome)
        v = d.get(nome) or d.get(nome.encode())
        return v.decode() if isinstance(v, bytes) else v

    assert C.PORTA == 6381
    assert conf("maxmemory-policy") == "allkeys-lru"
    assert int(conf("maxmemory")) >= 512 * 1024 * 1024
    assert conf("appendonly") == "no"


@pytest.mark.skipif(not motor_cache_no_ar(), reason="motor-cache fora do ar")
def test_conformidade_ida_e_volta_no_valkey_vivo():
    cache = C.Cache()
    a = FonteFalsa(carimbo=f"conformidade-{int(time.time())}")
    r1, veio1 = C.busca_com_cache(a, "item:2300", cache=cache)
    r2, veio2 = C.busca_com_cache(a, "item:2300", cache=cache)
    assert (veio1, veio2) == (False, True)
    assert a.buscas == 1
    assert r2.itens[0].procedencia.chave == r1.itens[0].procedencia.chave
