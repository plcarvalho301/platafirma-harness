"""`descansar fita` no Sair do caderno (card #3217, arq:0120 §2 e §10).

O que se trava: a lista do que a fita puxou de fora da cadeira sai do log de giro, so lido, e
so com leitura pela chave que deu certo nesta fita; documento de outra cadeira entra, o da
propria nao; dono que nao se resolve entra dito, nunca omitido. O indice do caderno vem do
banco pelo verbo `mesa`, e o chapeu fora da persona sai marcado.
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("descansar_bin", str(REPO_ROOT / "bin" / "descansar"))
spec = importlib.util.spec_from_loader("descansar_bin", loader)
assert spec and spec.loader
descansar = importlib.util.module_from_spec(spec)
loader.exec_module(descansar)

SID = "2be6bc3b-36fd-43e2-a189-3e01b0ec5e36"
OID = "o20261001T215703-d08875"
UUID_DIREITO = "0d4c1d9e-1111-4222-8333-444455556666"
UUID_IA = "9a8b7c6d-1111-4222-8333-444455556666"


def _reg(tool, ato, args, sessao_id=SID, ordem_id=OID, **extra):
    return {"ts": "2026-10-01T18:58:58.241-03:00", "tool": tool, "ato": ato, "args": args,
            "cadeira": "ia", "sessao_id": sessao_id, "ordem_id": ordem_id, "exit_code": 0,
            "erro": None, **extra}


GIROS = [
    _reg("acervo", "ler", "casa spec landing"),                       # documento de produto
    _reg("acervo", "ler", "casa guia expediente --situacao"),         # de gestao-estrategica
    _reg("acervo", "ler", "casa parecer 2026-10-01-caderno"),         # da propria cadeira
    _reg("acervo", "ler", "casa adr arq:0120"),                       # sem ficha nessa chave
    _reg("persona", "ler", "dados --chapeu curadoria"),               # chapeu de outra cadeira
    _reg("persona", "ler", "ia --chapeu contexto"),                   # o proprio chapeu
    _reg("persona", "ler", "produto"),                                # persona sem chapeu
    _reg("acervo", "ler", f"obra impressao {UUID_DIREITO} --paginas 1-2"),
    _reg("acervo", "ler", f"obra impressao {UUID_IA}"),
    _reg("motor", "rag", "buscar obra \"o que e caderno\""),          # busca: consultar nao e usar
    _reg("acervo", "ler", "casa spec com-erro", exit_code=2),         # nao deu certo
    _reg("acervo", "ler", "casa spec de-outra-fita", sessao_id="outra", ordem_id="outra"),
    {"ts": "2026-10-01T18:58:58.286-03:00", "tool": "-", "evento": "http_req", "sessao_id": SID},
]

ACERVO = {
    "casa:spec/landing": {"ponta": "casa:spec/landing", "dono": "claudinha-produto",
                          "titulo": "Landing"},
    "casa:guia/expediente": {"ponta": "casa:guia/expediente", "dono": "gestao-estrategica",
                             "titulo": None},
    "casa:parecer/2026-10-01-caderno": {"ponta": "casa:parecer/2026-10-01-caderno", "dono": "ia",
                                        "titulo": "Caderno"},
    f"obra:{UUID_DIREITO}": {"ponta": f"obra:{UUID_DIREITO}", "dono": "direito", "titulo": "LGPD"},
    f"obra:{UUID_IA}": {"ponta": f"obra:{UUID_IA}", "dono": "ia", "titulo": "Agentes"},
}


@pytest.fixture()
def log_ops(tmp_path: Path) -> Path:
    d = tmp_path / "ops"
    d.mkdir()
    (d / "ops-2026-10-01.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in GIROS) + "\nlinha cortada {\n",
        encoding="utf-8")
    return d


def test_giros_da_fita_so_os_desta_fita_que_deram_certo(log_ops):
    regs = descansar.giros_da_fita(SID, "", log_ops)
    args = [r["args"] for r in regs]
    assert "casa spec com-erro" not in args, "exit 2 nao e leitura"
    assert "casa spec de-outra-fita" not in args, "outra sessao, outra fita"
    assert all(r.get("tool") != "-" for r in regs), "http_req e transporte, nao giro"
    assert len(regs) == 10
    assert len(descansar.giros_da_fita("", OID, log_ops)) == 10, "a ordem tambem e chave da fita"


def test_sem_chave_da_fita_nao_le_o_log(log_ops):
    assert descansar.giros_da_fita("", "", log_ops) is None
    linhas = descansar.puxado_de_fora("ia", "", "", log_ops, resolver=lambda a: {})
    assert "sessao de mao nao tem log de giro" in linhas[0]


def test_puxados_na_forma_de_ponta_do_mesa_aresta(log_ops):
    achados = descansar.puxados(descansar.giros_da_fita(SID, OID, log_ops), "ia")
    assert set(achados) == {
        "casa:spec/landing", "casa:guia/expediente", "casa:parecer/2026-10-01-caderno",
        "casa:adr/arq:0120", "chapeu:dados/curadoria", f"obra:{UUID_DIREITO}", f"obra:{UUID_IA}"}
    assert "chapeu:ia/contexto" not in achados, "o chapeu da propria cadeira nao e de fora"


def test_lista_o_documento_de_outra_cadeira_e_deixa_o_da_propria_fora(log_ops, monkeypatch):
    monkeypatch.delenv("PF_CHAPEU", raising=False)
    linhas = descansar.puxado_de_fora("ia", SID, OID, log_ops, resolver=lambda a: ACERVO)
    texto = "\n".join(linhas)
    assert "casa:spec/landing" in texto and "documento de produto · «Landing»" in texto
    assert "documento de gestao-estrategica" in texto
    assert "chapeu:dados/curadoria" in texto and "chapéu de dados" in texto
    assert f"obra:{UUID_DIREITO}" in texto and "obra do domínio direito" in texto
    assert "casa:parecer/2026-10-01-caderno" not in texto, "documento da propria cadeira"
    assert f"obra:{UUID_IA}" not in texto, "obra do dominio de mesmo nome da cadeira"
    assert "casa:adr/arq:0120" in texto and "dono não resolvido" in texto, "nao resolvido fica, dito"
    assert linhas[0].startswith("  5 leitura(s) de fora da cadeira")
    assert "mesa aresta <chapeu> --de" in linhas[-1]


def test_acervo_fora_do_ar_lista_tudo_com_o_dono_indeterminavel(log_ops):
    linhas = descansar.puxado_de_fora("ia", SID, OID, log_ops, resolver=lambda a: None)
    texto = "\n".join(linhas)
    assert "casa:parecer/2026-10-01-caderno" in texto, "sem o dono, nada se omite"
    assert texto.count("dono indeterminável") == 6
    assert "chapéu de dados" in texto


def test_fita_que_nao_leu_nada_de_fora_diz_isso(log_ops):
    linhas = descansar.puxado_de_fora("ia", "sessao-sem-giro", "", log_ops,
                                      resolver=lambda a: ACERVO)
    assert linhas == ["  nada de fora da cadeira lido pela chave nesta fita (0 giro(s) lido(s))"]


def test_o_chapeu_do_ambiente_vai_na_linha_de_marcar(log_ops, monkeypatch):
    monkeypatch.setenv("PF_CHAPEU", "engenharia-de-harness")
    linhas = descansar.puxado_de_fora("ia", SID, OID, log_ops, resolver=lambda a: ACERVO)
    assert "mesa aresta engenharia-de-harness --de" in linhas[-1]


# ---------------------------------------------------------------- o indice do banco
MESA_INDICE = """#!/bin/sh
case "${STUB_MESA:-ok}" in
  ok)
    echo "  contexto         2 vigentes · 120/1500 tk · última escrita há 3 d · 1 a revisar"
    echo "  extinto          1 vigente · 40/1500 tk · última escrita há 20 d"
    echo "  engenharia-de-harness 0 vigentes · 0/1500 tk · legado 131 B a triar"
    echo "  (corpo sob demanda: \\`mesa caderno <chapeu>\\`)"
    ;;
  mudo) echo "cadernos: indisponíveis — sessao-db não respondeu; não é caderno vazio"; exit 3 ;;
esac
"""


@pytest.fixture()
def bin_stub(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "bin"
    d.mkdir()
    mesa = d / "mesa"
    mesa.write_text(MESA_INDICE, encoding="utf-8")
    mesa.chmod(0o755)
    monkeypatch.setenv("PF_BIN", str(d))
    return d


def test_indice_do_caderno_vem_do_banco_e_marca_o_chapeu_fora_da_persona(bin_stub):
    linhas = descansar.caderno_do_banco({"contexto", "engenharia-de-harness", "agente"})
    texto = "\n".join(linhas)
    assert "caderno/contexto         2 vigentes" in texto and "1 a revisar" in texto
    assert "legado 131 B a triar" in texto
    extinto = next(l for l in linhas if "extinto" in l)
    assert "ÓRFÃO" in extinto
    assert not any("ÓRFÃO" in l for l in linhas if "contexto" in l)


def test_banco_mudo_sai_declarado_e_nao_como_caderno_vazio(bin_stub, monkeypatch):
    monkeypatch.setenv("STUB_MESA", "mudo")
    assert descansar.caderno_do_banco(None) == [
        "  caderno: cadernos: indisponíveis — sessao-db não respondeu; não é caderno vazio"]
