"""Contrato dos adaptadores. `python3 -m pytest recuperacao/ -q` da raiz do repo.

Dois níveis, de propósito:

- **contrato** — roda sempre, com cliente falso. Julga o que o adaptador PRODUZ:
  procedência completa, chave com o prefixo certo, versão do tipo certo, falha declarada
  em vez de exceção.
- **conformidade** — roda contra a fonte real e é PULADO com motivo quando ela não está
  no ar. Julga a régua do §5: o resultado bate com o do verbo humano sobre o mesmo
  estado. Pular declarando é diferente de mascarar: o motivo aparece na saída.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from recuperacao.adaptadores import (
    AdaptadorFila,
    AdaptadorMesa,
    AdaptadorRegistro,
    FonteIndisponivel,
    monta_envelope,
)
from recuperacao.adaptadores.registro import SERIES
from recuperacao.envelope import Causa, Cobertura, Fonte, VersaoTipo

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))


# ------------------------------------------------------------------ fila: cliente falso


class FilaFalsa:
    """Só o que o adaptador chama: `ping`, `xrange`, `xinfo_stream`."""

    def __init__(self, entradas=None) -> None:
        self.entradas = entradas or []
        self.consumiu = []

    def ping(self):
        return True

    def xrange(self, chave, min="-", max="+"):
        self.consumiu.append(("xrange", chave))
        return self.entradas

    def xinfo_stream(self, chave):
        ultimo = self.entradas[-1][0] if self.entradas else "0-0"
        return {"last-generated-id": ultimo, "length": len(self.entradas)}

    def xreadgroup(self, *a, **kw):  # pragma: no cover — existe para o teste abaixo falhar
        raise AssertionError("recuperar NÃO pode consumir a caixa de ninguém")


CARTA = ("1787000000000-0", {
    "de": "claudinho-TI", "tipo": "pedido", "assunto": "core.bare voltou a true",
    "ref": "#139", "responde": "", "corpo": "o config foi reescrito às 16:05",
})
CARTA2 = ("1787000009999-0", {
    "de": "claudinha-gestao-estrategica", "tipo": "resposta", "assunto": "gabarito §3",
    "ref": "", "responde": "20260819T200707", "corpo": "campo único, sim",
})


# ================================================================= 1. contrato — fila


def test_fila_produz_procedencia_completa():
    a = AdaptadorFila(cliente=FilaFalsa([CARTA]))
    r = a.busca("claudinho-IA")
    assert len(r.itens) == 1
    p = r.itens[0].procedencia
    assert p.fonte is Fonte.FILA
    assert p.chave == "caixa:claudinho-IA/1787000000000-0"
    assert p.versao.tipo is VersaoTipo.STREAM_ID
    assert p.versao.valor == "1787000000000-0"


def test_fila_carimba_com_last_generated_id():
    a = AdaptadorFila(cliente=FilaFalsa([CARTA, CARTA2]))
    assert a.busca("claudinho-IA").linha.carimbo == "1787000009999-0"


def test_fila_le_frio_e_nunca_move_o_ponteiro():
    falsa = FilaFalsa([CARTA])
    AdaptadorFila(cliente=falsa).busca("claudinho-IA")
    assert [c[0] for c in falsa.consumiu] == ["xrange"], "XREADGROUP consumiria a caixa"


def test_fila_aceita_as_duas_formas_do_alvo():
    a = AdaptadorFila(cliente=FilaFalsa([CARTA]))
    assert a.busca("caixa:claudinho-IA").itens[0].procedencia.chave.startswith("caixa:claudinho-IA/")
    assert AdaptadorFila.caixa("claudinho-IA") == AdaptadorFila.caixa("caixa:claudinho-IA")


def test_fila_filtra_por_tipo_e_por_remetente():
    a = AdaptadorFila(cliente=FilaFalsa([CARTA, CARTA2]))
    assert len(a.busca("claudinho-IA", {"tipo": "pedido"}).itens) == 1
    assert len(a.busca("claudinho-IA", {"de": "claudinho-TI"}).itens) == 1
    assert a.busca("claudinho-IA", {"tipo": "minuta"}).linha.cobertura is Cobertura.VAZIA


def test_fila_sem_alvo_recusa_com_sem_rota():
    r = AdaptadorFila(cliente=FilaFalsa()).busca_declarada("")
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert r.linha.causa is Causa.SEM_ROTA


def test_fila_fora_do_ar_vira_linha_e_nao_excecao():
    a = AdaptadorFila(host="127.0.0.1", porta=1)  # porta morta
    r = a.busca_declarada("claudinho-IA")
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    # `fora-do-ar` com o cliente instalado; `sem-rota` quando falta o módulo. As duas
    # são a mesma coisa para quem lê: a fila não foi alcançada, e o motivo vem dito.
    assert r.linha.causa in (Causa.FORA_DO_AR, Causa.SEM_ROTA)
    assert r.itens == []


def test_fila_texto_nenhum_traz_ref_e_nao_conteudo():
    a = AdaptadorFila(cliente=FilaFalsa([CARTA]))
    it = a.busca("claudinho-IA", texto="nenhum").itens[0]
    assert it.conteudo is None and it.ref


# ============================================================== 2. contrato — registro


def test_registro_conhece_as_tres_series():
    assert set(SERIES) == {"adr", "seg", "ont"}


def test_registro_resolve_chave_exata():
    a = AdaptadorRegistro()
    r = a.busca("adr:0064", texto="nenhum")
    assert len(r.itens) == 1
    p = r.itens[0].procedencia
    assert p.chave == "adr:0064"
    assert p.fonte is Fonte.REGISTRO
    assert p.versao.tipo in (VersaoTipo.SHA, VersaoTipo.DIGEST)


def test_registro_chave_inexistente_e_vazia_nao_e_falha():
    # `vazia` ≠ `fonte-nao-indexada` (arq:0064 §1): a fonte respondeu, e não há registro.
    r = AdaptadorRegistro().busca("adr:9999")
    assert r.linha.cobertura is Cobertura.VAZIA
    assert r.linha.causa is None


def test_registro_busca_por_termo_no_titulo():
    r = AdaptadorRegistro().busca("recuperador", k=20, texto="nenhum")
    chaves = [i.procedencia.chave for i in r.itens]
    assert "adr:0064" in chaves and "adr:0067" in chaves


def test_registro_filtra_por_serie():
    r = AdaptadorRegistro().busca("", {"serie": ["seg"]}, k=50, texto="nenhum")
    assert r.itens and all(i.procedencia.chave.startswith("seg:") for i in r.itens)


def test_registro_traz_conteudo_so_na_chave_exata():
    exata = AdaptadorRegistro().busca("adr:0064", texto="secao").itens[0]
    assert exata.conteudo and "Recuperador" in exata.conteudo
    por_termo = AdaptadorRegistro().busca("recuperador", k=5, texto="secao").itens[0]
    assert por_termo.ref, "busca por termo devolve ref; conteúdo de N ADRs não cabe em envelope"


def test_registro_raiz_inexistente_vira_linha_declarada():
    r = AdaptadorRegistro(raiz="/nao/existe").busca_declarada("adr:0064")
    assert r.linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert r.linha.causa is Causa.SEM_ROTA


def test_registro_carimba_os_dois_repositorios():
    # `ont:` mora em outro repo; carimbo de um só envelheceria calado no outro.
    carimbo = AdaptadorRegistro().busca("adr:0064").linha.carimbo
    assert "arquitetura:" in carimbo and "conhecimento:" in carimbo


# ================================================================== 3. contrato — mesa


class ValkeyFalso:
    def __init__(self, mapa=None) -> None:
        self.mapa = mapa or {}

    def ping(self):
        return True

    def keys(self, padrao):
        if padrao.endswith("*"):
            base = padrao[:-1]
            return [k for k in self.mapa if k.startswith(base)]
        return [k for k in self.mapa if k == padrao]

    def get(self, chave):
        return self.mapa.get(chave)


class PgFalso:
    def __init__(self, linhas) -> None:
        self.linhas = linhas

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, args):
        self._sql = sql

    def fetchall(self):
        return self.linhas


class PgMudo(PgFalso):
    """A metade de item responde com erro. Injetado, e não simulado pela AUSÊNCIA de
    `psycopg` no ambiente: teste que passa por falta de biblioteca instalada volta a
    falhar no dia em que alguém instala a biblioteca, e mede a bancada, não a peça."""

    def __init__(self) -> None:
        super().__init__([])

    def execute(self, sql, args):
        raise RuntimeError("metade de item muda")


PROSA = {"mem:ia:harness": '{"x":"o que fechou nesta fita","t":1787000000}'}
ITEM = [(167, "harness", "emendar o verbo", "bin/_minuta/formalizar", None)]


def test_mesa_le_as_duas_metades():
    a = AdaptadorMesa(sufixo="ia", cliente=ValkeyFalso(PROSA), conexao_pg=PgFalso(ITEM))
    r = a.busca()
    chaves = [i.procedencia.chave for i in r.itens]
    assert "mem:ia:harness" in chaves
    assert "mem:ia:harness#167" in chaves
    assert r.linha.causa is None


def test_mesa_versao_por_metade():
    a = AdaptadorMesa(sufixo="ia", cliente=ValkeyFalso(PROSA), conexao_pg=PgFalso(ITEM))
    por_chave = {i.procedencia.chave: i.procedencia.versao for i in a.busca().itens}
    assert por_chave["mem:ia:harness"].tipo is VersaoTipo.DIGEST, "prosa velha não tem `v`"
    assert por_chave["mem:ia:harness#167"].tipo is VersaoTipo.SEQ
    assert por_chave["mem:ia:harness#167"].valor == "167"


def test_mesa_metade_muda_declara_causa_e_serve_o_que_tem():
    a = AdaptadorMesa(sufixo="ia", cliente=ValkeyFalso(PROSA), conexao_pg=PgMudo())
    r = a.busca()
    assert r.itens, "Valkey de pé serve a prosa mesmo com a outra metade muda"
    assert r.linha.causa is Causa.SEM_ROTA, "degradação declarada, nunca pacote menor calado"


def test_mesa_sem_cadeira_recusa(monkeypatch):
    """`sufixo=""` cai no `PF_CADEIRA` do ambiente por desenho do construtor — sem
    apagar a variável, este teste mede o ambiente da bancada em vez da recusa."""
    monkeypatch.delenv("PF_CADEIRA", raising=False)
    a = AdaptadorMesa(sufixo="", cliente=ValkeyFalso(PROSA), conexao_pg=PgMudo())
    r = a.busca_declarada()
    assert r.linha.causa is Causa.SEM_CONCESSAO


def test_mesa_aceita_pf_cadeira_nas_duas_formas():
    assert AdaptadorMesa(sufixo="claudinho-IA").sufixo == "ia"
    assert AdaptadorMesa(sufixo="IA").sufixo == "ia"


# ========================================== 4. o núcleo: N adaptadores → um envelope


def test_monta_envelope_de_tres_fontes():
    reg = AdaptadorRegistro().busca_declarada("adr:0064", texto="nenhum")
    fila = AdaptadorFila(cliente=FilaFalsa([CARTA])).busca_declarada("claudinho-IA")
    mesa = AdaptadorMesa(sufixo="ia", cliente=ValkeyFalso(PROSA),
                         conexao_pg=PgFalso(ITEM)).busca_declarada()
    env = monta_envelope([reg, fila, mesa])
    assert [l.fonte for l in env.linhas] == [Fonte.REGISTRO, Fonte.FILA, Fonte.MESA]
    assert len(env.itens) == 4


def test_fonte_caida_no_meio_nao_derruba_as_outras():
    reg = AdaptadorRegistro(raiz="/nao/existe").busca_declarada("adr:0064")
    fila = AdaptadorFila(cliente=FilaFalsa([CARTA])).busca_declarada("claudinho-IA")
    env = monta_envelope([reg, fila])
    d = env.para_json()
    assert d["aviso"] == [{"fonte": "registro", "causa": "sem-rota"}]
    assert env.itens, "a fila respondeu normalmente"


def test_sem_gold_nenhuma_fonte_diz_coberta():
    # §13 — fonte sem coleção de teste serve `nao-calibrada` declarado, nunca "boa".
    for r in (
        AdaptadorRegistro().busca_declarada("adr:0064", texto="nenhum"),
        AdaptadorFila(cliente=FilaFalsa([CARTA])).busca_declarada("claudinho-IA"),
    ):
        assert r.linha.cobertura is Cobertura.NAO_CALIBRADA


def test_busca_medida_devolve_latencia():
    _, ms = AdaptadorFila(cliente=FilaFalsa([CARTA])).busca_medida("claudinho-IA")
    assert ms >= 0.0


# ================================================== 5. conformidade contra a fonte real


def _fila_no_ar() -> bool:
    try:
        import redis

        redis.Redis(host="127.0.0.1", port=6379, socket_timeout=0.5).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not os.path.isdir(os.path.join(RAIZ, "platafirma-arquitetura")),
                    reason="clone de platafirma-arquitetura ausente nesta máquina")
def test_conformidade_registro_bate_com_o_diretorio():
    """§5 — o resultado bate com a fonte sobre o mesmo estado."""
    d = os.path.join(RAIZ, "platafirma-arquitetura", "macro-global", "decisions")
    no_disco = {n[:4] for n in os.listdir(d) if n.endswith(".md") and n[:4].isdigit()}
    r = AdaptadorRegistro().busca("", {"serie": ["adr"]}, k=1000, texto="nenhum")
    do_adaptador = {i.procedencia.chave.split(":")[1] for i in r.itens}
    assert do_adaptador == no_disco, "o adaptador viu conjunto diferente do que está no ref"


@pytest.mark.skipif(not _fila_no_ar(), reason="motor-msg (127.0.0.1:6379) não respondeu")
def test_conformidade_fila_bate_com_o_verbo_humano():
    """Contra `fila ler --tudo`, sobre a mesma caixa e o mesmo estado."""
    caixa = "claudinho-IA"
    # `--tudo` é XRANGE, leitura FRIA: não move o ponteiro do grupo, e por isso a
    # conformidade pode ser medida sem consumir a caixa de ninguém.
    p = subprocess.run([os.path.join(RAIZ, "bin", "fila"), "ler", caixa, "--tudo"],
                       capture_output=True, text=True, timeout=30,
                       env={**os.environ, "PF_CADEIRA": caixa})
    if p.returncode != 0:
        pytest.skip(f"`fila ler --tudo` não rodou: {p.stderr.strip()[:120]}")
    r = AdaptadorFila().busca(caixa, k=1000, texto="nenhum")
    # O verbo imprime um bloco `===MSG <msgid>===` por carta. Régua do §5: mesmo estado,
    # mesmo conjunto — e o msgid é o identificador que os dois lados carregam.
    do_verbo = {l.split("===MSG ")[1].rstrip("=") for l in p.stdout.splitlines()
                if l.startswith("===MSG ")}
    do_adaptador = {it.ref.split(" · ")[0] for it in r.itens}
    assert do_adaptador == do_verbo, (
        f"adaptador e verbo divergiram: só no adaptador {do_adaptador - do_verbo}, "
        f"só no verbo {do_verbo - do_adaptador}"
    )
