"""`teste sessao` — um caso por ato e por etapa do §4 da spec_sessao rev 3 (#3053).

Hermetico: `persona`, `acesso` e `seg` sao stubs executaveis em <raiz>/bin (o verbo os
chama por PATH, como a porta faz); o msg-mem e um fake em memoria trocado no modulo; o
registro duravel e trocado no modulo em todo caso menos no que mede a falha dele.
O binario e importado como modulo (sem sufixo .py) e `main(argv)` roda em processo.
"""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import stat

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "bin" / "sessao"

PERSONA_STUB = """#!/bin/sh
if [ -n "${STUB_LOG:-}" ]; then echo "persona $*" >> "$STUB_LOG"; fi
case "${STUB_PERSONA_MODO:-ok}" in
  muda) echo "persona foto: morada nao publicada (stub)" >&2; exit 3 ;;
esac
if [ "$1" = "foto" ]; then
  echo '{"ia": {"alias": "Elias Elefante", "chapeus": ["contexto", "engenharia-de-harness"]}, "fabrica": {"alias": null, "chapeus": []}}'
  exit 0
fi
echo "stub persona: ato desconhecido $1" >&2; exit 2
"""

ACESSO_STUB = """#!/bin/sh
if [ -n "${STUB_LOG:-}" ]; then echo "acesso $*" >> "$STUB_LOG"; fi
rec="$3"
case "${STUB_ACESSO_MODO:-ok}" in
  ok)
    echo '{"permitido": true, "regra": "fornecedor-abre-a-propria-sessao", "motivo": "a fabrica abre a fita na propria cadeira", "faltou": [], "plano": "1a2b3c4d", "sujeito": "'"${PF_SUJEITO}"'", "acao": "sessao_abrir", "recurso": "'"$rec"'"}'
    exit 0 ;;
  nega)
    echo '{"permitido": false, "regra": "default", "motivo": "nenhuma regra permite", "faltou": [], "plano": "1a2b3c4d"}'
    exit 1 ;;
  faltou)
    echo '{"permitido": false, "regra": "projecao", "motivo": "atributo ausente", "faltou": ["papel"], "plano": "1a2b3c4d"}'
    exit 5 ;;
  ausente)
    echo "acesso decidir: PAP servido ausente (stub)" >&2; exit 3 ;;
esac
"""

SEG_STUB = """#!/bin/sh
case "${STUB_SEG_MODO:-ok}" in
  ok) echo "senha-stub"; exit 0 ;;
  falha) echo "seg segredo ler: segredo nao existe (stub)" >&2; exit 1 ;;
esac
"""

class FakeMem:
    """O que o verbo usa do cliente redis: ping, get, set(ex=), exists, delete, scan_iter."""

    def __init__(self):
        self.d: dict[str, str] = {}
        self.persiste = True

    def ping(self):
        return True

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v, ex=None):
        if self.persiste:
            self.d[k] = v
        return True

    def exists(self, k):
        return 1 if k in self.d else 0

    def delete(self, k):
        return 1 if self.d.pop(k, None) is not None else 0

    def scan_iter(self, match="*", count=None):
        pref = match.rstrip("*")
        return [k for k in list(self.d) if k.startswith(pref)]

def _executavel(p: Path, texto: str) -> None:
    p.write_text(texto, encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

@pytest.fixture()
def amb(tmp_path, monkeypatch):
    """Raiz hermetica + modulo importado + fake msg-mem. Devolve (mod, mem, raiz)."""
    raiz = tmp_path / "raiz"
    (raiz / "bin").mkdir(parents=True)
    _executavel(raiz / "bin" / "persona", PERSONA_STUB)
    _executavel(raiz / "bin" / "acesso", ACESSO_STUB)
    _executavel(raiz / "bin" / "seg", SEG_STUB)
    monkeypatch.setenv("PF_RAIZ", str(raiz))
    monkeypatch.setenv("PF_SUJEITO", "e57eadb1-0000-4000-8000-000000000001")
    monkeypatch.setenv("PF_SUPERFICIE", "code")
    monkeypatch.setenv("STUB_LOG", str(raiz / "chamadas.log"))
    for v in ("STUB_PERSONA_MODO", "STUB_ACESSO_MODO", "STUB_SEG_MODO"):
        monkeypatch.delenv(v, raising=False)
    spec = importlib.util.spec_from_file_location(
        "sessao_mod", SCRIPT, loader=SourceFileLoader("sessao_mod", str(SCRIPT)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mem = FakeMem()
    monkeypatch.setattr(mod, "RAIZ", str(raiz))
    monkeypatch.setattr(mod, "_msgmem", lambda: (mem, None))
    monkeypatch.setattr(mod, "_registra_duravel", lambda sid, slug: None)
    return mod, mem, raiz

def _json(capsys):
    out = capsys.readouterr().out.strip().splitlines()[-1]
    return json.loads(out)

def _log(raiz: Path) -> str:
    p = raiz / "chamadas.log"
    return p.read_text(encoding="utf-8") if p.exists() else ""

# ------------------------------------------------------------------ uso (etapa 1)
def test_sem_ato_e_ato_desconhecido_exit_2(amb, capsys):
    mod, mem, _ = amb
    assert mod.main([]) == 2
    assert mod.main(["dormir"]) == 2
    assert "atos: abrir ver listar encerrar longjob" in capsys.readouterr().err
    assert mod.main(["dormir", "--json"]) == 2
    assert "ato desconhecido" in _json(capsys)["erro"]

def test_abrir_sem_cadeira_exit_2(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["abrir"]) == 2
    assert "uso:" in capsys.readouterr().err
    assert mem.d == {}

def test_abrir_sessao_id_invalido_exit_2_e_nao_cunha(amb, capsys):
    mod, mem, raiz = amb
    assert mod.main(["abrir", "ia", "--sessao-id", "nao-e-uuid", "--json"]) == 2
    assert "chame sem `--sessao-id`" in _json(capsys)["erro"]
    assert mem.d == {}
    assert "acesso" not in _log(raiz)

# ------------------------------------------------------------------ sujeito (etapa 2)
def test_abrir_sem_sujeito_exit_3_nunca_cunha(amb, capsys, monkeypatch):
    mod, mem, raiz = amb
    monkeypatch.delenv("PF_SUJEITO")
    assert mod.main(["abrir", "ia", "--json"]) == 3
    assert "sem sujeito: a porta nao autenticou" in _json(capsys)["erro"]
    assert mem.d == {}
    assert _log(raiz) == ""

# ------------------------------------------------------------------ organizacao (etapa 3, 3')
def test_abrir_cadeira_desconhecida_exit_2_lista_validas(amb, capsys):
    mod, mem, raiz = amb
    assert mod.main(["abrir", "xyz", "--json"]) == 2
    d = _json(capsys)
    assert "validas" in d["erro"] and d["cadeiras_validas"] == ["fabrica", "ia"]
    assert "acesso" not in _log(raiz)
    assert mem.d == {}

def test_abrir_alias_humano_e_prefixo_canonizam(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["abrir", "Elias Elefante", "--json"]) == 0
    assert _json(capsys)["cadeira"] == "ia"
    assert mod.main(["abrir", "claudinho-IA", "--json"]) == 0
    assert _json(capsys)["cadeira"] == "ia"

def test_abrir_organizacao_muda_cunha_nao_canonizada_depois_da_autorizacao(amb, capsys, monkeypatch):
    mod, mem, raiz = amb
    monkeypatch.setenv("STUB_PERSONA_MODO", "muda")
    assert mod.main(["abrir", "IA", "--json"]) == 0
    d = _json(capsys)
    assert d["canonizada"] is False and d["cadeira"] == "ia"
    assert "restrita a cura" in d["regime"]
    assert any("organizacao muda" in a for a in d["avisos"])
    assert "acesso decidir sessao_abrir sessao:ia --json" in _log(raiz)
    chave = json.loads(mem.d[f"sessao:{d['sessao_id']}"])
    assert chave["canonizada"] is False and chave["autorizada_por"].endswith("@1a2b3c4d")

# ------------------------------------------------------------------ autorizacao (etapa 4, 4', 4'')
def test_abrir_negado_exit_4_com_regra_e_nao_cunha(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setenv("STUB_ACESSO_MODO", "nega")
    assert mod.main(["abrir", "ia", "--json"]) == 4
    d = _json(capsys)
    assert d["regra"] == "default" and "quem concede" in d["erro"]
    assert mem.d == {}

def test_abrir_projecao_incompleta_exit_3_nomeia_faltou(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setenv("STUB_ACESSO_MODO", "faltou")
    assert mod.main(["abrir", "ia", "--json"]) == 3
    d = _json(capsys)
    assert d["faltou"] == ["papel"] and "faltou: papel" in d["erro"]
    assert mem.d == {}

def test_abrir_politica_ausente_exit_3(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setenv("STUB_ACESSO_MODO", "ausente")
    assert mod.main(["abrir", "ia", "--json"]) == 3
    assert "politica: ausente" in _json(capsys)["erro"]
    assert mem.d == {}

# ------------------------------------------------------------------ chave viva (etapa 5)
def test_abrir_msgmem_ausente_exit_3_com_id_na_mensagem(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setattr(mod, "_msgmem", lambda: (None, "ConnectionError"))
    assert mod.main(["abrir", "ia", "--json"]) == 3
    d = _json(capsys)
    assert "msg-mem: ausente" in d["erro"] and d["sessao_id"] in d["erro"]

def test_abrir_ok_chave_inteira_e_saida_conforme(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["abrir", "ia", "--json"]) == 0
    d = _json(capsys)
    assert d["cunhada_agora"] is True and d["registrada"] is True and d["duravel"] is True
    assert d["autorizada_por"] == "fornecedor-abre-a-propria-sessao@1a2b3c4d"
    assert d["ordem_id"].startswith("o20") and "-" in d["ordem_id"]
    chave = json.loads(mem.d[f"sessao:{d['sessao_id']}"])
    assert set(chave) >= {"sujeito", "cadeira", "canonizada", "autorizada_por", "ordem_id",
                          "superficie", "aberto_em"}
    assert chave["sujeito"] == os.environ["PF_SUJEITO"] and chave["superficie"] == "code"
    # texto: as linhas do §3
    assert mod.main(["abrir", "ia"]) == 0
    txt = capsys.readouterr().out
    assert txt.startswith("sessao_id: ") and "autorizada_por: fornecedor" in txt
    assert "porte: devolva este sessao_id" in txt

def test_reabrir_mesma_conversa_atualiza_so_ordem_id(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["abrir", "ia", "--json"]) == 0
    d1 = _json(capsys)
    sid = d1["sessao_id"]
    # a porta enriquece a chave com o que so ela tem; a 2a abertura nao apaga
    ch = json.loads(mem.d[f"sessao:{sid}"])
    ch["jti"] = "porta-123"
    mem.d[f"sessao:{sid}"] = json.dumps(ch)
    assert mod.main(["abrir", "ia", "--sessao-id", sid, "--json"]) == 0
    d2 = _json(capsys)
    assert d2["sessao_id"] == sid and d2["cunhada_agora"] is False
    assert d2["ordem_id"] != d1["ordem_id"]
    ch2 = json.loads(mem.d[f"sessao:{sid}"])
    assert ch2["jti"] == "porta-123" and ch2["aberto_em"] == ch["aberto_em"]
    assert len(mem.d) == 1

def test_reabrir_com_id_expirado_regrava_sem_recunhar(amb, capsys):
    mod, mem, _ = amb
    sid = "654160f8-2e43-4478-97b7-a19e7c36bdb5"
    assert mod.main(["abrir", "ia", "--sessao-id", sid, "--json"]) == 0
    d = _json(capsys)
    assert d["sessao_id"] == sid and d["cunhada_agora"] is False
    assert f"sessao:{sid}" in mem.d

# ------------------------------------------------------------------ registro duravel (etapa 6)
def test_registro_duravel_falha_exit_0_declarado(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setattr(mod, "_registra_duravel", _duravel_real(mod))
    monkeypatch.setenv("STUB_SEG_MODO", "falha")
    assert mod.main(["abrir", "ia", "--json"]) == 0
    d = _json(capsys)
    assert d["duravel"] is False and "seg segredo ler" in d["duravel_motivo"]
    assert d["registrada"] is True

def _duravel_real(mod):
    """A funcao original, que para em `_senha_pg` quando o segredo nao vem — sem tocar banco."""
    src_spec = importlib.util.spec_from_file_location(
        "sessao_mod_2", SCRIPT, loader=SourceFileLoader("sessao_mod_2", str(SCRIPT)))
    m2 = importlib.util.module_from_spec(src_spec)
    src_spec.loader.exec_module(m2)
    m2.RAIZ = mod.RAIZ
    return m2._registra_duravel

# ------------------------------------------------------------------ releitura (etapa 7)
def test_gravou_e_nao_confirma_exit_5(amb, capsys):
    mod, mem, _ = amb
    mem.persiste = False
    assert mod.main(["abrir", "ia", "--json"]) == 5
    d = _json(capsys)
    assert "nao confirma" in d["erro"] and d["sessao_id"]

# ------------------------------------------------------------------ ver
def test_ver_existe_nao_existe_e_uso(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["abrir", "ia", "--json"]) == 0
    sid = _json(capsys)["sessao_id"]
    assert mod.main(["ver", sid, "--json"]) == 0
    d = _json(capsys)
    assert d["cadeira"] == "ia" and d["autorizada_por"].startswith("fornecedor")
    assert mod.main(["ver", "654160f8-2e43-4478-97b7-a19e7c36bdb5", "--json"]) == 1
    d = _json(capsys)
    assert d["vizinho"] == "sessao listar" and "varrido" in d
    assert mod.main(["ver", "nao-uuid"]) == 2

def test_ver_nao_canonizada_declara_regime(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setenv("STUB_PERSONA_MODO", "muda")
    assert mod.main(["abrir", "ia", "--json"]) == 0
    sid = _json(capsys)["sessao_id"]
    assert mod.main(["ver", sid]) == 0
    assert "regime: nao canonizada" in capsys.readouterr().out

# ------------------------------------------------------------------ listar
def test_listar_vazio_e_filtro_por_cadeira(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["listar", "--json"]) == 0
    assert _json(capsys)["motivo"] == "nenhuma sessao viva"
    assert mod.main(["abrir", "ia", "--json"]) == 0
    capsys.readouterr()
    assert mod.main(["abrir", "fabrica", "--json"]) == 0
    capsys.readouterr()
    assert mod.main(["listar", "--cadeira", "ia", "--json"]) == 0
    d = _json(capsys)
    assert [s["cadeira"] for s in d["sessoes"]] == ["ia"]
    assert mod.main(["listar"]) == 0
    assert capsys.readouterr().out.count("\n") == 2

# ------------------------------------------------------------------ encerrar
def test_encerrar_apaga_as_tres_e_segunda_vez_exit_1(amb, capsys):
    mod, mem, _ = amb
    assert mod.main(["abrir", "ia", "--json"]) == 0
    sid = _json(capsys)["sessao_id"]
    mem.d[f"ledger:{sid}"] = "{}"
    mem.d[f"giro:{sid}"] = "{}"
    assert mod.main(["encerrar", sid, "--json"]) == 0
    d = _json(capsys)
    assert set(d["apagadas"]) == {f"sessao:{sid}", f"ledger:{sid}", f"giro:{sid}"}
    assert mem.d == {}
    assert mod.main(["encerrar", sid]) == 1
    assert mod.main(["encerrar", "x"]) == 2

# ------------------------------------------------------------------ msg-mem mudo nos atos de leitura
def test_msgmem_mudo_exit_3_em_ver_listar_encerrar(amb, capsys, monkeypatch):
    mod, mem, _ = amb
    monkeypatch.setattr(mod, "_msgmem", lambda: (None, "ConnectionError"))
    sid = "654160f8-2e43-4478-97b7-a19e7c36bdb5"
    assert mod.main(["ver", sid]) == 3
    assert mod.main(["listar"]) == 3
    assert mod.main(["encerrar", sid]) == 3
