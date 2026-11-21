# componente: componente:lousa
"""Suíte do trabalho na lousa por chave e dos atos do `bin/mesa` da casa nova (story 4366, feature 4269).

Cobre:
- trabalho gravado por chave (`card:<N>` ou `turno:<id>`) fora da chave da sessão e sem TTL/EXPIRE;
- sobrevivência entre sessões distintas e em fita sem descanso;
- isolamento por cadeira no mesmo card;
- recusa com exit 2 ao guardar sem ocasião;
- evicção de item cujo card está em estado terminal;
- casamento por mudança de estado do card, número do card, chave do trabalho e chapéu;
- remoção por `mesa fez`, atualização por `--corrigir` e recusa de atos de caderno;
- degradação com exit 3 em `bin/mesa` e aviso na abertura quando a memória de trabalho não responde.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[1]
MESA = HARNESS_DIR / "bin" / "mesa"
sys.path.insert(0, str(HARNESS_DIR / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from abertura.pauta import (
    ContextoDaSessao,
    carregar_guardados_da_lousa,
    montar_pauta,
)
from postura.lousa import (
    Fora,
    ItemDeTrabalho,
    Lousa,
    LousaEmMemoria,
    LousaFixtura,
    Ocasiao,
    OcasiaoAusente,
    chave_trabalho,
)
from test_abertura import _rodar_abertura


def _rodar_mesa(
    args: list[str],
    *,
    cadeira: str = "ia",
    valkey_fixture: Path | None = None,
    cards_fixture: Path | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for k in ("PF_CADEIRA", "PF_SESSAO", "PF_ORDEM_ID", "PF_VALKEY_FIXTURE", "PF_CARDS_FIXTURE"):
        env.pop(k, None)
    if cadeira:
        env["PF_CADEIRA"] = cadeira
    if valkey_fixture is not None:
        env["PF_VALKEY_FIXTURE"] = str(valkey_fixture)
    if cards_fixture is not None:
        env["PF_CARDS_FIXTURE"] = str(cards_fixture)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(MESA), *args],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
        check=False,
    )


def _novo_valkey(tmp_path: Path, conteudo: dict | None = None) -> Path:
    arq = tmp_path / "valkey.json"
    arq.write_text(json.dumps(conteudo if conteudo is not None else {"chaves": []}, ensure_ascii=False), encoding="utf-8")
    return arq


# --- Unidade: lousa.py ---------------------------------------------------------------------------------------------

def test_lousa_protocolo_nao_poe_expire_no_trabalho_e_nao_toca_chaves_de_sessao():
    comandos_enviados: list[list[tuple]] = []

    class FakeLousa(Lousa):
        def _manda(self, comandos: list[tuple]) -> list:
            comandos_enviados.append(list(comandos))
            cmd = comandos[0][0]
            if cmd == "HSET":
                return [1]
            if cmd == "HDEL":
                return [1]
            return [[]]

    lousa = FakeLousa()
    item = ItemDeTrabalho(
        chave="card:4366",
        cadeira="ia",
        situacao="guardado",
        card="4366",
        estagio="execucao",
        proxima_jogada="fechar suite",
        ocasiao=Ocasiao(card="4366", estado_card="em-execucao"),
    )
    lousa.gravar_trabalho("ia", item)

    assert len(comandos_enviados) == 1
    assert comandos_enviados[0][0][0] == "HSET"
    assert comandos_enviados[0][0][1] == chave_trabalho("ia") == "lousa:trabalho:{ia}"
    assert comandos_enviados[0][0][2] == "card:4366"
    assert all(c[0] != "EXPIRE" for c in comandos_enviados[0])


def test_lousa_em_memoria_recusa_guardado_sem_ocasiao_e_levanta_fora():
    with pytest.raises(OcasiaoAusente):
        ItemDeTrabalho(chave="card:4366", cadeira="ia", situacao="guardado")

    fora = LousaEmMemoria(fora=True)
    with pytest.raises(Fora):
        fora.listar_trabalhos("ia")


def test_lousa_fixtura_preserva_chaves_da_memoria_de_descanso(tmp_path):
    arq = _novo_valkey(tmp_path, {"chaves": ["sessao:s1", "sessao:s2"]})
    fix = LousaFixtura(arq)
    item = ItemDeTrabalho(chave="card:4366", cadeira="ia", situacao="em_curso", estagio="execucao")
    fix.gravar_trabalho("ia", item)

    bruto = json.loads(arq.read_text(encoding="utf-8"))
    assert bruto["chaves"] == ["sessao:s1", "sessao:s2"]
    assert "card:4366" in bruto["trabalhos"]["ia"]


# --- Cenas de aceite: CLI mesa + abertura --------------------------------------------------------------------------

def test_guardado_sobrevive_a_segunda_sessao_e_a_fita_sem_descanso(tmp_path):
    valkey = _novo_valkey(tmp_path, {"chaves": ["sessao:sessao-1"]})
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4366": {"estado": "em-execucao"}}), encoding="utf-8")

    # Sessão 1 grava trabalho guardado com ocasião de chapéu
    p1 = _rodar_mesa(
        [
            "item",
            "--card", "4366",
            "--estagio", "execucao",
            "--proxima-jogada", "retomar testes da lousa",
            "--guardar",
            "--ocasiao-chapeu", "back-end",
            "--json",
        ],
        cadeira="engenharia",
        valkey_fixture=valkey,
        cards_fixture=cards,
        env_extra={"PF_SESSAO": "sessao-1"},
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    salvo = json.loads(p1.stdout)
    assert salvo["chave"] == "card:4366"
    assert salvo["situacao"] == "guardado"
    assert salvo["ocasiao"]["chapeu"] == "back-end"

    # Sessão 1 morre sem descanso (chave de sessão sumiu da memória de trabalho)
    dado = json.loads(valkey.read_text(encoding="utf-8"))
    dado["chaves"] = []
    valkey.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")

    # Sessão 2 (outra superfície/sessão) abre e recebe o guardado inteiro na pauta
    ab = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="abrir expediente",
        env_extra={"PF_CARDS_FIXTURE": str(cards)},
        tmp_path=tmp_path,
    )
    assert ab.returncode == 0, ab.stdout + ab.stderr
    d = json.loads(ab.stdout)
    assert d["pauta"]["total_guardados"] == 1
    assert len(d["pauta"]["guardados"]) == 1
    assert d["pauta"]["guardados"][0]["chave"] == "card:4366"
    assert "retomar testes da lousa" in d["pauta"]["conteudo"]


def test_guardado_sem_ocasiao_recusado_com_exit_2(tmp_path):
    valkey = _novo_valkey(tmp_path)
    proc = _rodar_mesa(
        [
            "item",
            "--card", "4366",
            "--estagio", "execucao",
            "--proxima-jogada", "tentar guardar sem ocasião",
            "--guardar",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert proc.returncode == 2
    assert "ocasião" in proc.stderr.lower()
    assert LousaFixtura(valkey).listar_trabalhos("ia") == []


def test_item_de_card_terminal_sai_da_lousa_e_fica_fora_da_pauta(tmp_path):
    valkey = _novo_valkey(tmp_path)
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4366": {"estado": "em-execucao"}}), encoding="utf-8")

    p1 = _rodar_mesa(
        [
            "item",
            "--card", "4366",
            "--estagio", "execucao",
            "--proxima-jogada", "fechar card 4366",
            "--guardar",
            "--ocasiao-card", "4366",
        ],
        cadeira="engenharia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr

    # Card passa para estado terminal
    cards.write_text(json.dumps({"4366": {"estado": "entregue"}}), encoding="utf-8")

    ab = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="card 4366",
        env_extra={"PF_CARDS_FIXTURE": str(cards)},
        tmp_path=tmp_path,
    )
    assert ab.returncode == 0, ab.stdout + ab.stderr
    d = json.loads(ab.stdout)
    assert d["pauta"]["total_guardados"] == 0
    assert d["pauta"]["guardados"] == []
    assert "fechar card 4366" not in d["pauta"]["conteudo"]
    assert LousaFixtura(valkey).ler_trabalho("engenharia", "card:4366") is None


def test_guardado_de_outra_cadeira_no_mesmo_card_fica_fora_da_pauta_e_nao_colide(tmp_path):
    valkey = _novo_valkey(tmp_path)
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4366": {"estado": "em-execucao"}}), encoding="utf-8")

    p_ia = _rodar_mesa(
        [
            "item",
            "--card", "4366",
            "--estagio", "execucao",
            "--proxima-jogada", "trabalho exclusivo da ia",
            "--guardar",
            "--ocasiao-card", "4366",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    p_eng = _rodar_mesa(
        [
            "item",
            "--card", "4366",
            "--estagio", "revisao",
            "--proxima-jogada", "trabalho exclusivo da engenharia",
            "--guardar",
            "--ocasiao-card", "4366",
        ],
        cadeira="engenharia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p_ia.returncode == 0 and p_eng.returncode == 0

    ab = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="card 4366",
        env_extra={"PF_CARDS_FIXTURE": str(cards)},
        tmp_path=tmp_path,
    )
    assert ab.returncode == 0, ab.stdout + ab.stderr
    d = json.loads(ab.stdout)
    assert d["pauta"]["total_guardados"] == 1
    assert "trabalho exclusivo da engenharia" in d["pauta"]["conteudo"]
    assert "trabalho exclusivo da ia" not in d["pauta"]["conteudo"]

    # O trabalho da cadeira ia continua intacto
    item_ia = LousaFixtura(valkey).ler_trabalho("ia", "card:4366")
    assert item_ia is not None
    assert item_ia.proxima_jogada == "trabalho exclusivo da ia"


def test_guardado_cujo_card_andou_e_servido_inteiro(tmp_path):
    valkey = _novo_valkey(tmp_path)
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4366": {"estado": "bloqueada"}}), encoding="utf-8")

    p1 = _rodar_mesa(
        [
            "item",
            "--card", "4366",
            "--estagio", "execucao",
            "--proxima-jogada", "retomar quando 4366 destravar",
            "--guardar",
            "--ocasiao-card", "4366",
            "--json",
        ],
        cadeira="engenharia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    assert json.loads(p1.stdout)["ocasiao"]["estado_card"] == "bloqueada"

    # Antes de andar: fora da ocasião (só a conta)
    ab_antes = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="abrir expediente sem citar nada",
        env_extra={"PF_CARDS_FIXTURE": str(cards)},
        tmp_path=tmp_path,
    )
    assert ab_antes.returncode == 0
    p_antes = json.loads(ab_antes.stdout)["pauta"]
    assert p_antes["total_guardados"] == 1
    assert p_antes["fora_da_ocasiao"] == 1
    assert p_antes["guardados"] == []

    # Card muda de estado -> servido inteiro
    cards.write_text(json.dumps({"4366": {"estado": "em-execucao"}}), encoding="utf-8")
    ab_depois = _rodar_abertura(
        ["engenharia", "--chapeu", "back-end"],
        pergunta="abrir expediente sem citar nada",
        env_extra={"PF_CARDS_FIXTURE": str(cards)},
        tmp_path=tmp_path,
    )
    assert ab_depois.returncode == 0
    p_depois = json.loads(ab_depois.stdout)["pauta"]
    assert p_depois["total_guardados"] == 1
    assert p_depois["fora_da_ocasiao"] == 0
    assert len(p_depois["guardados"]) == 1
    assert "retomar quando 4366 destravar" in p_depois["conteudo"]


def test_entrada_sem_card_usa_turno_e_mesa_fez_remove(tmp_path):
    valkey = _novo_valkey(tmp_path)

    p1 = _rodar_mesa(
        [
            "item",
            "--estagio", "investigacao",
            "--ato", "comparar duas abordagens",
            "--json",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
        env_extra={"PF_ORDEM_ID": "o20261118T234620-abc123"},
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    item = json.loads(p1.stdout)
    assert item["chave"] == "turno:o20261118T234620-abc123"
    assert item["situacao"] == "em_curso"
    assert item["proxima_jogada"] == "comparar duas abordagens"

    # mesa ver lista o item
    p_ver = _rodar_mesa(["ver", "--json"], cadeira="ia", valkey_fixture=valkey)
    assert p_ver.returncode == 0
    itens = json.loads(p_ver.stdout)
    assert [i["chave"] for i in itens] == ["turno:o20261118T234620-abc123"]

    # mesa fez remove o item da lousa
    p_fez = _rodar_mesa(["fez", "turno:o20261118T234620-abc123", "--json"], cadeira="ia", valkey_fixture=valkey)
    assert p_fez.returncode == 0
    assert json.loads(p_fez.stdout)["removido"] is True

    p_ver2 = _rodar_mesa(["ver", "--json"], cadeira="ia", valkey_fixture=valkey)
    assert json.loads(p_ver2.stdout) == []


def test_entrada_sem_card_e_sem_turno_usa_a_sessao_dt956(tmp_path):
    valkey = _novo_valkey(tmp_path)
    args = ["item", "--estagio", "sintese", "--ato", "guardar a síntese", "--json"]

    # sem card, sem turno e sem sessão: continua recusando
    p0 = _rodar_mesa(args, cadeira="produto", valkey_fixture=valkey)
    assert p0.returncode == 2
    assert "chave do trabalho exige card ou id do turno" in p0.stdout + p0.stderr

    # a superfície não entrega o turno, e a porta exporta a sessão: ela vira a chave
    p1 = _rodar_mesa(
        args,
        cadeira="produto",
        valkey_fixture=valkey,
        env_extra={"PF_SESSAO": "5df980f4-aca5-4525-95c5-199f4d6820fd"},
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    assert json.loads(p1.stdout)["chave"] == "turno:5df980f4-aca5-4525-95c5-199f4d6820fd"

def test_memoria_fora_sai_3_sem_gravar_em_outro_lugar(tmp_path):
    valkey = _novo_valkey(tmp_path, {"fora": True})
    antes = valkey.read_text(encoding="utf-8")

    p_item = _rodar_mesa(
        ["item", "--card", "4366", "--estagio", "execucao", "--proxima-jogada", "x"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p_item.returncode == 3
    assert valkey.read_text(encoding="utf-8") == antes

    p_fez = _rodar_mesa(["fez", "4366"], cadeira="ia", valkey_fixture=valkey)
    assert p_fez.returncode == 3

    p_ver = _rodar_mesa(["ver"], cadeira="ia", valkey_fixture=valkey)
    assert p_ver.returncode == 3


def test_mesa_recusa_atos_do_caderno_e_aceita_corrigir(tmp_path):
    valkey = _novo_valkey(tmp_path)

    p_cad = _rodar_mesa(["caderno"], cadeira="ia", valkey_fixture=valkey)
    assert p_cad.returncode == 2

    p1 = _rodar_mesa(
        ["item", "--card", "4366", "--estagio", "plano", "--proxima-jogada", "passo 1", "--json"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p1.returncode == 0

    p2 = _rodar_mesa(
        ["item", "--corrigir", "card:4366", "--estagio", "execucao", "--proxima-jogada", "passo 2", "--json"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p2.returncode == 0
    corrigido = json.loads(p2.stdout)
    assert corrigido["estagio"] == "execucao"
    assert corrigido["proxima_jogada"] == "passo 2"


def test_carregar_guardados_sem_eviccao_quando_rastreador_falha():
    lousa = LousaEmMemoria()
    lousa.gravar_trabalho(
        "ia",
        ItemDeTrabalho(
            chave="card:4366",
            cadeira="ia",
            situacao="guardado",
            card="4366",
            estagio="execucao",
            proxima_jogada="manter na lousa",
            ocasiao=Ocasiao(card="4366", estado_card="em-execucao"),
        ),
    )

    def leitor_falho(cards, avisos):
        if avisos is not None:
            avisos.append("rastreador indisponível")
        return {}

    avisos: list[str] = []
    guardados, estados = carregar_guardados_da_lousa("ia", lousa, leitor_cards=leitor_falho, avisos=avisos)
    assert len(guardados) == 1
    assert estados == {}
    assert any("rastreador" in a for a in avisos)
    assert lousa.ler_trabalho("ia", "card:4366") is not None

    pauta = montar_pauta(guardados, [], ContextoDaSessao(cadeira="ia", turno="retomar card:4366"))
    assert len(pauta.guardados) == 1


def test_dt937_mesa_item_recusa_sobrescrita_silenciosa_de_chave_existente(tmp_path):
    valkey = _novo_valkey(tmp_path)
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4406": {"estado": "em-execucao"}}), encoding="utf-8")

    p1 = _rodar_mesa(
        [
            "item",
            "--card", "4406",
            "--estagio", "analise",
            "--proxima-jogada", "arbitrar a separação do porta.yaml",
            "--guardar",
            "--ocasiao-card", "4406",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr

    # Segunda chamada sem --corrigir deve ser recusada mostrando o item atual
    p2 = _rodar_mesa(
        [
            "item",
            "--card", "4406",
            "--estagio", "execucao",
            "--proxima-jogada", "outro texto que nao deve apagar o primeiro",
            "--guardar",
            "--ocasiao-card", "4406",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p2.returncode == 2
    assert "arbitrar a separação do porta.yaml" in p2.stderr
    assert "--corrigir card:4406" in p2.stderr
    assert "mesa corpo card:4406" in p2.stderr

    # O item original permanece intacto
    atual = LousaFixtura(valkey).ler_trabalho("ia", "card:4406")
    assert atual is not None
    assert atual.proxima_jogada == "arbitrar a separação do porta.yaml"


def test_mesa_corpo_edita_e_apaga_sem_tocar_na_moldura(tmp_path):
    valkey = _novo_valkey(tmp_path)
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4406": {"estado": "em-execucao"}}), encoding="utf-8")

    p1 = _rodar_mesa(
        [
            "item",
            "--card", "4406",
            "--estagio", "analise",
            "--proxima-jogada", "fechar desenho",
            "--corpo", "fita A: conclusao inicial\nfita A: detalhe que fica",
            "--guardar",
            "--ocasiao-card", "4406",
            "--json",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    guardado_em_inicial = json.loads(p1.stdout)["guardado_em"]

    # Fita B substitui a conclusao da fita A e acrescenta nova linha
    p2 = _rodar_mesa(
        [
            "corpo", "4406",
            "--antes", "fita A: conclusao inicial\n",
            "--depois", "",
            "--json",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p2.returncode == 0, p2.stdout + p2.stderr
    d2 = json.loads(p2.stdout)
    assert d2["corpo"] == "fita A: detalhe que fica"
    assert d2["situacao"] == "guardado"
    assert d2["estagio"] == "analise"
    assert d2["proxima_jogada"] == "fechar desenho"
    assert d2["guardado_em"] == guardado_em_inicial
    assert d2["ocasiao"]["card"] == "4406"

    p3 = _rodar_mesa(
        ["corpo", "card:4406", "--anexar", "fita B: conclusao revisada", "--json"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p3.returncode == 0, p3.stdout + p3.stderr
    assert json.loads(p3.stdout)["corpo"] == "fita A: detalhe que fica\nfita B: conclusao revisada"

    # --corrigir altera a moldura sem perder o corpo, e recusa --corpo junto
    p_recusa = _rodar_mesa(
        ["item", "--corrigir", "card:4406", "--corpo", "nao pode"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p_recusa.returncode == 2

    p_cor = _rodar_mesa(
        ["item", "--corrigir", "card:4406", "--estagio", "execucao", "--json"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p_cor.returncode == 0, p_cor.stdout + p_cor.stderr
    d_cor = json.loads(p_cor.stdout)
    assert d_cor["estagio"] == "execucao"
    assert d_cor["corpo"] == "fita A: detalhe que fica\nfita B: conclusao revisada"

    # mesa corpo --limpar esvazia o quadro preservando a moldura
    p_limpa = _rodar_mesa(["corpo", "4406", "--limpar", "--json"], cadeira="ia", valkey_fixture=valkey)
    assert p_limpa.returncode == 0, p_limpa.stdout + p_limpa.stderr
    d_limpa = json.loads(p_limpa.stdout)
    assert d_limpa["corpo"] == ""
    assert d_limpa["estagio"] == "execucao"
    assert d_limpa["situacao"] == "guardado"


def test_teto_do_corpo_barra_escrita_e_nunca_quebra_leitura_nem_vaza_na_pauta(tmp_path):
    from postura.lousa import TETO_CORPO_CHARS, CorpoExcedido, EdicaoDeCorpo, editar_corpo

    assert TETO_CORPO_CHARS == 6000
    valkey = _novo_valkey(tmp_path)
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps({"4406": {"estado": "em-execucao"}}), encoding="utf-8")

    # Escrita acima do teto e recusada
    grande = "x" * (TETO_CORPO_CHARS + 1)
    p_grande = _rodar_mesa(
        ["item", "--card", "4406", "--estagio", "execucao", "--corpo", grande],
        cadeira="ia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p_grande.returncode == 2
    assert str(TETO_CORPO_CHARS) in p_grande.stderr

    # Item dentro do teto entra na lousa; abertura traz so a moldura + tamanho, sem vazar o texto do corpo
    texto_corpo = "SEGREDO_DO_CORPO_SO_SOB_DEMANDA"
    p_ok = _rodar_mesa(
        [
            "item",
            "--card", "4406",
            "--estagio", "execucao",
            "--proxima-jogada", "resumo curto na moldura",
            "--corpo", texto_corpo,
            "--guardar",
            "--ocasiao-card", "4406",
        ],
        cadeira="ia",
        valkey_fixture=valkey,
        cards_fixture=cards,
    )
    assert p_ok.returncode == 0, p_ok.stdout + p_ok.stderr

    ab = _rodar_abertura(
        ["ia", "--chapeu", "contexto"],
        pergunta="card 4406",
        env_extra={"PF_CARDS_FIXTURE": str(cards)},
        tmp_path=tmp_path,
    )
    assert ab.returncode == 0, ab.stdout + ab.stderr
    pauta = json.loads(ab.stdout)["pauta"]["conteudo"]
    assert "resumo curto na moldura" in pauta
    assert f"(corpo: {len(texto_corpo)}/{TETO_CORPO_CHARS})" in pauta
    assert texto_corpo not in pauta

    # mesa ver <chave> entrega o corpo inteiro sob demanda
    p_ver = _rodar_mesa(["ver", "4406"], cadeira="ia", valkey_fixture=valkey)
    assert p_ver.returncode == 0, p_ver.stdout + p_ver.stderr
    assert texto_corpo in p_ver.stdout

    # Se o teto diminuir depois, um item ja gravado acima do novo teto continua legivel,
    # e a proxima edicao so passa quando voltar a caber
    with pytest.raises(CorpoExcedido):
        editar_corpo("abcdef", EdicaoDeCorpo(anexar="g"), teto=6)
    assert editar_corpo("abcdefg", EdicaoDeCorpo(antes="efg", depois=""), teto=6) == "abcd"


def test_dt948_mesa_corpo_edita_item_listado_por_ver_e_nomeia_cadeira_quando_ausente(tmp_path):
    """DT 948: mesa corpo aceita todas as formas da chave listada por mesa ver e nomeia a cadeira no erro."""
    valkey = _novo_valkey(tmp_path)

    p_cria = _rodar_mesa(
        [
            "item",
            "--card", "4406",
            "--estagio", "execucao",
            "--proxima-jogada", "fechar parecer",
            "--corpo", "linha inicial",
        ],
        cadeira="seguranca",
        valkey_fixture=valkey,
    )
    assert p_cria.returncode == 0, p_cria.stdout + p_cria.stderr

    # mesa ver lista card:4406
    p_ver = _rodar_mesa(["ver", "--json"], cadeira="seguranca", valkey_fixture=valkey)
    assert p_ver.returncode == 0
    assert [i["chave"] for i in json.loads(p_ver.stdout)] == ["card:4406"]

    # mesa corpo edita com card:4406, --card 4406 e posicional 4406
    for alvo_args, trecho in (
        (["card:4406"], "editado-1"),
        (["--card", "4406"], "editado-2"),
        (["4406"], "editado-3"),
    ):
        p_c = _rodar_mesa(
            ["corpo", *alvo_args, "--anexar", trecho],
            cadeira="seguranca",
            valkey_fixture=valkey,
        )
        assert p_c.returncode == 0, p_c.stdout + p_c.stderr
        assert trecho in p_c.stdout

    # Em outra cadeira, o erro informa explicitamente qual cadeira foi consultada
    p_outra = _rodar_mesa(
        ["corpo", "card:4406", "--anexar", "x"],
        cadeira="ia",
        valkey_fixture=valkey,
    )
    assert p_outra.returncode == 2
    assert "cadeira: ia" in p_outra.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, *sys.argv[1:]]))
