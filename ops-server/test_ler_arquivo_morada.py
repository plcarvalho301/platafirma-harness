"""ler_arquivo confinado à morada da leitura (card #3279, F1) e chave privada por nome (F2).

Morada de leitura = release + instância + bancada declarada INTEIRA, menos as negativas
(segredo, fila), que vencem a morada. Tudo com as raízes em tmp: o teste nunca lê o host.

Aceite coberto: /etc/passwd e /etc recusam «fora de morada»; id_rsa e a lista fechada de
nomes recusam «segredo» mesmo onde o arquivo nem existe; release, instância, bancada de
OUTRA cadeira, rascunho da fita e markdown recém-escrito seguem lendo; symlink não escapa
da morada; a bancada se lê uma vez por chamada e o alvo se resolve uma vez (leveza).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server as s  # noqa: E402


@pytest.fixture
def morada(monkeypatch, tmp_path):
    """Release, instância e bancada em tmp; o teste escreve nelas e lê pela porta."""
    rel, inst, banc = (tmp_path / n for n in ("release", "instancia", "bancada"))
    (rel / "current" / "harness").mkdir(parents=True)
    (inst / "var" / "tmp").mkdir(parents=True)
    (inst / "var" / "fila").mkdir(parents=True)
    (banc / "wt" / "platafirma-core" / "outra-cadeira").mkdir(parents=True)
    monkeypatch.setattr(s, "_MORADAS_LEITURA", (str(rel.resolve()), str(inst.resolve())))
    monkeypatch.setattr(s, "_RAIZES_DE_INSTANCIA", (tmp_path.resolve(),))
    monkeypatch.setattr(s, "FILA_RAIZ", (inst / "var" / "fila").resolve())
    monkeypatch.setattr(s, "TMP_FITA", inst / "var" / "tmp")
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(banc))
    return {"release": rel, "instancia": inst, "bancada": banc}


@pytest.fixture(autouse=True)
def sem_pep():
    with patch.object(s, "_autoriza", return_value=None), patch.object(s, "_audit"):
        yield


def _le(caminho):
    return s.ler_arquivo(caminho=str(caminho))


def _recusa(r) -> str:
    assert r.get("recusado") or r.get("erro"), r
    return r.get("motivo") or r.get("erro")


# --- F1: fora da morada recusa ---------------------------------------------------------
@pytest.mark.parametrize("caminho", ["/etc/passwd", "/etc", "/", "/nao-existe-3279/x.md"])
def test_fora_da_morada_recusa(morada, caminho):
    assert _recusa(_le(caminho)).startswith("fora de morada")


def test_fora_de_morada_nomeia_as_moradas_e_a_bancada(morada):
    motivo = _recusa(_le("/etc/passwd"))
    assert str(morada["bancada"].resolve()) in motivo and "ler_arquivo" in motivo


def test_sem_bancada_declarada_a_morada_diz_isso(morada, monkeypatch, tmp_path):
    monkeypatch.delenv("PLATAFIRMA_BANCADA", raising=False)
    monkeypatch.setenv("PLATAFIRMA_ARQUIVO_BANCADA", str(tmp_path / "nao-declarada"))
    assert "bancada nao declarada" in _recusa(_le("/etc/passwd"))


def test_symlink_da_morada_para_fora_nao_escapa(morada):
    elo = morada["instancia"] / "var" / "tmp" / "elo.md"
    elo.symlink_to("/etc/passwd")
    assert _recusa(_le(elo)).startswith("fora de morada")
    pai = morada["bancada"] / "wt" / "saida"
    pai.symlink_to("/etc")
    assert _recusa(_le(pai / "passwd")).startswith("fora de morada")


# --- F1: o legítimo segue passando ---------------------------------------------------------
def test_release_instancia_e_bancada_de_qualquer_cadeira_leem(morada):
    outra = morada["bancada"] / "wt" / "platafirma-core" / "outra-cadeira"
    alvos = {
        morada["release"] / "current" / "harness" / "guia.md": "da release",
        morada["instancia"] / "var" / "tmp" / "ordem-1" / "rascunho.md": "rascunho da fita",
        outra / "x.py": "x = 1",
        outra / "sub" / "y.md": "y de outra cadeira",
    }
    for caminho, texto in alvos.items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto + "\n")
        r = _le(caminho)
        assert not r.get("recusado") and texto in r["conteudo"], (caminho, r)


def test_raiz_da_bancada_e_diretorios_da_morada_listam(morada):
    for d in (morada["bancada"], morada["bancada"] / "wt", morada["release"], morada["instancia"]):
        r = _le(d)
        assert r.get("diretorio") and not r.get("recusado"), (d, r)


def test_caminho_relativo_e_na_bancada(morada):
    (morada["bancada"] / "wt" / "platafirma-core" / "outra-cadeira" / "nota.md").write_text("oi\n")
    r = _le("wt/platafirma-core/outra-cadeira/nota.md")
    assert "oi" in r["conteudo"]


def test_markdown_recem_escrito_se_relê(morada, monkeypatch):
    # rascunho de var/tmp so se escreve com fita declarada (#3280): a fita deste teste e ordem-9
    monkeypatch.setattr(s, "_sessao_resolve", lambda sid: {
        "sessao_id": "sid-teste", "ordem_id": "ordem-9", "cadeira": "engenharia",
        "sujeito": "", "origem_sessao": ""})
    caminho = "wt/platafirma-core/outra-cadeira/aux.md"
    ok = s.write_file(path=caminho, content="auxiliar\n")
    assert ok.get("ok"), ok
    assert "auxiliar" in _le(morada["bancada"] / caminho)["conteudo"]
    rascunho = morada["instancia"] / "var" / "tmp" / "ordem-9" / "aux.md"
    assert s.write_file(path=str(rascunho), content="rascunho\n", sessao_id="sid-teste").get("ok")
    assert "rascunho" in _le(rascunho)["conteudo"]


# --- as negativas vencem a morada ---------------------------------------------------------
def test_fila_dentro_da_instancia_segue_negada(morada):
    assert "fila" in _recusa(_le(s.FILA_RAIZ / "caixa.jsonl"))


def test_segredo_de_instancia_e_env_dentro_da_morada_seguem_negados(morada):
    seg = morada["instancia"] / "segredos" / "core" / "POSTGRES"
    seg.parent.mkdir(parents=True)
    seg.write_text("nao-leia")
    env = morada["bancada"] / "wt" / "platafirma-core" / "outra-cadeira" / ".env.prod"
    env.write_text("TOKEN=x")
    for alvo in (seg, env):
        assert _recusa(_le(alvo)).startswith("segredo"), alvo


# --- F2: chave privada por nome -----------------------------------------------------------
NOMES = ["id_rsa", "id_ed25519", "id_dsa", "id_ecdsa", "authorized_keys", ".netrc", ".pgpass",
         ".git-credentials", "meu.asc", "cofre.kdbx", "x.key", "x.pem", "MAIUSCULA.PEM"]


@pytest.mark.parametrize("nome", NOMES)
def test_chave_privada_por_nome_e_segredo_mesmo_ausente_e_fora_da_morada(morada, nome):
    # fora da morada e inexistente: «segredo» (a negativa vence), não «fora de morada»/«não existe»
    assert _recusa(_le(f"/home/conta-3279/.ssh/{nome}")).startswith("segredo")


@pytest.mark.parametrize("nome", NOMES)
def test_chave_privada_por_nome_dentro_da_morada_recusa(morada, nome):
    alvo = morada["bancada"] / "wt" / "platafirma-core" / "outra-cadeira" / nome
    alvo.write_text("conteudo-secreto\n")
    r = _le(alvo)
    assert _recusa(r).startswith("segredo") and "conteudo-secreto" not in str(r)


def test_nome_parecido_nao_e_segredo(morada):
    base = morada["bancada"] / "wt" / "platafirma-core" / "outra-cadeira"
    for nome in ("id_rsa.pub", "id_rsa_notas.md", "authorized_keys.md", "netrc.md", "asc.md"):
        (base / nome).write_text("publico\n")
        assert "publico" in _le(base / nome)["conteudo"], nome


# --- leveza ---------------------------------------------------------------------------------
def test_a_bancada_le_do_disco_uma_vez_e_o_alvo_resolve_uma_vez(morada):
    alvo = morada["bancada"] / "wt" / "platafirma-core" / "outra-cadeira" / "leve.md"
    alvo.write_text("leve\n")
    with patch.object(s, "_bancada", wraps=s._bancada) as bancada, \
            patch.object(s, "_real", wraps=s._real) as real:
        r = s.ler_arquivo(caminho="wt/platafirma-core/outra-cadeira/leve.md")
    assert "leve" in r["conteudo"]
    assert bancada.call_count == 1, "bancada lida uma vez por chamada (era uma por consulta)"
    assert real.call_count == 1, "um realpath do alvo, reusado por fila, segredo e morada"


def test_recusa_fora_da_morada_paga_um_realpath_e_uma_leitura_da_bancada(morada):
    with patch.object(s, "_bancada", wraps=s._bancada) as bancada, \
            patch.object(s, "_real", wraps=s._real) as real:
        assert _recusa(_le("/etc/passwd")).startswith("fora de morada")
    assert bancada.call_count == 1 and real.call_count == 1
