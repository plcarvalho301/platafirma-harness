# componente: componente:verbo-fila
"""DT 798: `fila tratar` em lote pelo seletor e `fila ler --ids`.

Prova: o seletor (--de, --tipo, --assunto, --ate) escolhe, entre as penduradas e as nao lidas,
so as cartas que casam todos os criterios, e trata cada uma pelo mesmo `tratar` do msgid; o
seletor e os msgids se excluem; `--ate` le o dia inteiro ou o carimbo exato; `ler --ids` imprime
so os msgids. Nao prova: a malha de verdade (o fake de `test_fila_ack` tem grupo, ponteiro e PEL).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_fila_ack import StreamRC, _rodar, fila_streams  # noqa: E402


def _c(tec, msgid, de, tipo, assunto):
    return (tec, {"id": msgid, "de": de, "tipo": tipo, "assunto": assunto,
                  "ref": "", "responde": "", "corpo": "c"})


def _rc():
    return StreamRC([
        _c("100-1", "20261116T212000-ti", "ti", "demanda", "a.md: especie parecer nao existe"),
        _c("100-2", "20261116T212001-ti", "ti", "demanda", "b.md: especie guia nao existe"),
        _c("100-3", "20261116T213000-ia", "ia", "pedido", "revisa o motor"),
        _c("100-4", "20261117T080000-ti", "ti", "demanda", "c.md: especie padrao nao existe"),
    ])


PERSONAS = {"ti", "ia", "dados"}


def test_tratar_por_remetente_e_tipo_pega_pendurada_e_nao_lida(monkeypatch, capsys):
    rc = _rc()
    # entrega so as duas primeiras (ficam penduradas); as outras seguem nao lidas
    rc.xreadgroup("cadeira", "ti", ["caixa:ti"], count=2)
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "--de", "ti", "--tipo", "demanda"], rc,
                       personas=PERSONAS)
    assert code == 0, cap
    assert cap.out.splitlines() == ["20261116T212000-ti: tratada", "20261116T212001-ti: tratada",
                                    "20261117T080000-ti: tratada"]
    assert rc.pel == []
    # a carta da ia ficou de fora e segue por tratar
    _, cap = _rodar(monkeypatch, capsys, ["ler", "--penduradas", "--ids"], rc, personas=PERSONAS)
    assert cap.out.splitlines() == ["20261116T213000-ia"]


def test_tratar_ate_o_dia_e_por_trecho_do_assunto(monkeypatch, capsys):
    rc = _rc()
    code, cap = _rodar(monkeypatch, capsys,
                       ["tratar", "--de", "ti", "--ate", "2026-11-16", "--assunto", "ESPECIE GUIA"],
                       rc, personas=PERSONAS)
    assert code == 0
    assert cap.out.splitlines() == ["20261116T212001-ti: tratada"]


def test_ate_aceita_carimbo_exato_e_recusa_o_que_nao_le(monkeypatch, capsys):
    assert fila_streams._ate_normalizado("2026-11-16") == "20261116T235959"
    assert fila_streams._ate_normalizado("20261116T212000") == "20261116T212000"
    assert fila_streams._ate_normalizado("16/11/2026") is None
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "--de", "ti", "--ate", "ontem"], _rc(),
                       personas=PERSONAS)
    assert code == 2
    assert "--ate le AAAA-MM-DD" in cap.err


def test_seletor_e_msgid_juntos_recusam(monkeypatch, capsys):
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "20261116T212000-ti", "--de", "ti"], _rc(),
                       personas=PERSONAS)
    assert code == 2
    assert "nao os dois" in cap.err


def test_seletor_sem_carta_que_case_sai_1(monkeypatch, capsys):
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "--de", "dados"], _rc(), personas=PERSONAS)
    assert code == 1
    assert "nenhuma carta por tratar casa o seletor" in cap.out


def test_tipo_fora_da_lista_recusa(monkeypatch, capsys):
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "--tipo", "inventado"], _rc(),
                       personas=PERSONAS)
    assert code == 2
    assert "tipo invalido" in cap.err


def test_ler_ids_lista_so_os_msgids(monkeypatch, capsys):
    code, cap = _rodar(monkeypatch, capsys, ["ler", "--tudo", "--ids"], _rc(), personas=PERSONAS)
    assert code == 0
    linhas = cap.out.splitlines()
    assert set(linhas) == {"20261116T212000-ti", "20261116T212001-ti", "20261116T213000-ia",
                           "20261117T080000-ti"}
    assert "===MSG" not in cap.out
