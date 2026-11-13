"""release conferir verbo: a capacidade do cabecalho se confere contra o mapa vigente (vocabulario
arquitetura-negocio-operacao, como o acervo o serve), e nao contra a existencia de uma ficha no acervo.
Ficha do mapa antigo segue no acervo depois que o mapa muda; por ela `verificacao` passava (pedido de
gestao-estrategica, 12/11/2026)."""
import importlib.machinery
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFERIR_PATH = RAIZ / "bin" / "_release" / "conferir" / "conferir.py"


def _carregar(caminho, nome):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


conferir = _carregar(CONFERIR_PATH, "conferir_cabecalho_mapa_teste")

MAPA = """decisão · vigente — vocabulario arquitetura-negocio-operacao · Arquitetura de negócio da operação
## As 28 capacidades e o objeto de cada uma

| Capacidade | Mãe | Objeto central | Persona |
|---|---|---|---|
| `gestao-estrategica` | — | a estratégia | gestao-estrategica |
| `busca` | — | a incerteza de quem pergunta | ia |
| `gestao-de-motores` | `busca` | o motor de busca | ia |
| `dados` | — | o conjunto de dados | dados |
| `analise` | `dados` | a vista | dados |
| `operacao` | — | a plataforma: o que está servido agora | ti |
"""


def _mapa(monkeypatch, rc=0, texto=MAPA, erro=""):
    monkeypatch.setattr(conferir, "_MAPA", {})
    monkeypatch.setattr(conferir, "_ler_mapa_vigente", lambda: (rc, texto, erro))


def test_capacidade_do_mapa_e_conforme(monkeypatch):
    _mapa(monkeypatch)
    for cap in ("operacao", "gestao-de-motores", "gestao-estrategica", "analise", "dados/analise", "busca/gestao-de-motores"):
        assert conferir._capacidade_veredito(cap).estado == "conforme", cap


def test_capacidade_do_mapa_antigo_e_divergente(monkeypatch):
    _mapa(monkeypatch)
    for cap in ("verificacao", "trabalho", "motor", "expediente", "sessao", "infra/promocao-de-mudanca", "release"):
        v = conferir._capacidade_veredito(cap)
        assert v.estado == "divergente", cap
        assert "mapa vigente" in v.motivo


def test_mae_errada_e_divergente(monkeypatch):
    _mapa(monkeypatch)
    v = conferir._capacidade_veredito("busca/analise")
    assert v.estado == "divergente"
    assert "'dados'" in v.motivo or "dados" in v.motivo


def test_mapa_que_nao_se_le_e_indeterminavel(monkeypatch):
    _mapa(monkeypatch, rc=5, texto="", erro="banco fora do ar")
    assert conferir._capacidade_veredito("operacao").estado == "indeterminavel"
    _mapa(monkeypatch, texto="documento sem tabela")
    assert conferir._capacidade_veredito("operacao").estado == "indeterminavel"


def test_persona_e_mae_saem_da_tabela(monkeypatch):
    _mapa(monkeypatch)
    caps, erro = conferir._mapa_vigente()
    assert erro is None
    assert len(caps) == 6
    assert caps["operacao"] == {"mae": None, "persona": "ti"}
    assert caps["analise"] == {"mae": "dados", "persona": "dados"}
