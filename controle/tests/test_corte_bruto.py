"""lib/oplog_corte, bin/_infra/corte-bruto e os pedaços do corte em lib/oplog (card #3354; arq:0123 regras 10 e 12).

O corte apaga arquivo e não volta: aqui ele roda só contra uma pasta em tmp_path, uma partição falsa (a leitura
D5.5/D5.6 do acervo) e um rastreador falso. Nada toca o bruto de verdade. O que não se prova aqui é a API de
verdade (a mesma que a #3353 provou), que `corte-bruto --seco --mais-velhos-que 0` confere no ar antes do timer.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

import oplog
import oplog_corte as cw
from oplog_extracao import Falha

RAIZ = Path(__file__).resolve().parents[2]
CORTE = RAIZ / "bin" / "_infra" / "corte-bruto"
HOJE = date(2026, 11, 10)
VELHO, NOVO, RECENTE = "2026-10-01", "2026-10-11", "2026-11-09"       # 40 dias, 30 dias, ontem
SEGREDOS = ("SEGREDO-ARGS", "SEGREDO-PERGUNTA", "SEGREDO-SUJEITO")


def _linhas(dia, n=4):
    corpo = [json.dumps({"ts": f"{dia}T10:00:0{i}-03:00", "tool": "acervo", "ato": "ler", "exit_code": 0,
                         "args": "casa SEGREDO-ARGS", "sujeito": "SEGREDO-SUJEITO", "pergunta": "SEGREDO-PERGUNTA"})
             for i in range(n)]
    return corpo + ["isto nao e json", ""]


def _escreve(pasta, dia, linhas=None):
    (pasta / oplog.nome_do_dia(dia)).write_text("\n".join(linhas or _linhas(dia)) + "\n", encoding="utf-8")


@pytest.fixture
def bruto(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    for dia in (VELHO, NOVO, RECENTE):
        _escreve(pasta, dia)
    return pasta


def _linhagem_de(pasta, dia, passada=True, **mud):
    """A linhagem que a #3353 grava para o dia, contada AQUI por outro caminho que o do corte."""
    dados = (pasta / oplog.nome_do_dia(dia)).read_bytes()
    texto = [l for l in dados.decode("utf-8").splitlines() if l.strip()]
    legiveis = 0
    for l in texto:
        try:
            legiveis += isinstance(json.loads(l), dict)
        except ValueError:
            pass
    linha = {"dia": dia, "arquivo": oplog.nome_do_dia(dia), "bytes": len(dados),
             "sha256": hashlib.sha256(dados).hexdigest(),
             "passada": {"id": f"p-{dia}", "linhas_lidas": len(texto), "linhas_legiveis": legiveis,
                         "linhas_ilegiveis": len(texto) - legiveis} if passada else None}
    linha.update(mud)
    return linha, legiveis


class ParticaoFalsa:
    """D5.5 e D5.6 em memória: a linhagem por dia e os eventos do dia, em páginas com cursor."""

    def __init__(self, pasta, dias=(VELHO, NOVO, RECENTE), eventos=None, falha=None, **desvios):
        self.linhas, self.eventos, self.falha, self.chamadas = {}, {}, falha, []
        for dia in dias:
            linha, legiveis = _linhagem_de(pasta, dia, **desvios.get(dia, {}))
            self.linhas[dia] = linha
            self.eventos[dia] = legiveis
        self.eventos.update(eventos or {})

    def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
        self.chamadas.append((metodo, caminho, dict(params or {})))
        if self.falha:
            raise self.falha
        assert metodo == "GET", f"o corte só lê: {metodo} {caminho}"
        if caminho == "/acervo/log/dias":
            dia = params["desde"]
            assert params["ate"] == dia
            return 200, {"itens": [self.linhas.get(dia, {"dia": dia, "passada": None})], "proximo": None}
        achado = re.fullmatch(r"/acervo/log/dias/(\d{4}-\d{2}-\d{2})/eventos", caminho)
        assert achado, f"rota que a partição falsa não conhece: {caminho}"
        n = self.eventos[achado.group(1)]
        inicio, limite = int((params or {}).get("cursor") or 0), int((params or {}).get("limite", 100))
        fim = min(inicio + limite, n)
        return 200, {"itens": [{"evento_id": str(i)} for i in range(inicio, fim)],
                     "proximo": str(fim) if fim < n else None}


class TarefasFalsa:
    def __init__(self, abertos=()):
        self.abertos, self.criados, self.listagens = set(abertos), [], 0

    def titulos_abertos(self):
        self.listagens += 1
        return set(self.abertos)

    def abrir_incidente(self, titulo, corpo):
        self.criados.append((titulo, corpo))
        return "item 1 criado"


def _corta(bruto, api, tarefas=None, argv=(), hoje=HOJE):
    saida = []
    poda = bruto.parent / "poda.log"
    codigo = cw.main(list(argv), api=api, hoje=hoje, tarefas=tarefas or TarefasFalsa(), saida=saida.append,
                     diretorio_=bruto, poda_log=poda)
    return codigo, saida, poda


def _no_disco(bruto):
    return sorted(oplog.dias_no_disco(bruto))


# --- o portão: os quatro casos do card ------------------------------------------------------------------

def test_dia_de_40_dias_com_linhagem_conferida_sai(bruto):
    codigo, saida, poda = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 0
    assert _no_disco(bruto) == [NOVO, RECENTE], "só o dia velho sai; o de 30 dias e o de ontem ficam"
    assert any(l.startswith(f"corte-bruto {VELHO}: cortado — conferido") for l in saida)
    assert f"corte-bruto {VELHO}: cortado — conferido (idade=40d" in poda.read_text(encoding="utf-8")


def test_dia_sem_linhagem_fica_em_silencio(bruto):
    tarefas = TarefasFalsa()
    codigo, saida, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"passada": False}}), tarefas)
    assert codigo == 0, "retido por falta de linhagem não é falha: a extração ainda não passou"
    assert VELHO in _no_disco(bruto)
    assert tarefas.criados == [] and tarefas.listagens == 0, "em silêncio: nem lista incidente, nem abre"
    assert f"corte-bruto {VELHO}: retido — sem_linhagem" in poda.read_text(encoding="utf-8")


def test_dia_sem_nenhuma_linha_na_particao_tambem_fica(bruto):
    api = ParticaoFalsa(bruto, dias=(NOVO, RECENTE))
    codigo, _, _ = _corta(bruto, api)
    assert codigo == 0 and VELHO in _no_disco(bruto)


def test_sha_divergente_fica_e_abre_incidente_para_a_seguranca(bruto):
    tarefas = TarefasFalsa()
    codigo, saida, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"sha256": "0" * 64}}), tarefas)
    assert codigo == 1
    assert VELHO in _no_disco(bruto), "o arquivo fica no disco"
    assert [t for t, _ in tarefas.criados] == [f"{oplog.ROTULO_BRUTO} {VELHO}: bruto reprovado no portão"]
    assert cw.CADEIRA_DO_INCIDENTE == "seguranca"
    corpo = tarefas.criados[0][1]
    assert "sha256" in corpo and not any(s in corpo for s in SEGREDOS), "o incidente leva contagem, nunca conteúdo"
    log = poda.read_text(encoding="utf-8")
    assert f"corte-bruto {VELHO}: reprovado — sha256 (idade=40d" in log, "o veredito do portao vem primeiro"
    assert f"corte-bruto {VELHO}: incidente aberto" in log


def test_dia_de_30_dias_fica(bruto):
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 0 and NOVO in _no_disco(bruto)


@pytest.mark.parametrize("idade, sai", [(35, False), (36, True)])
def test_o_prazo_e_mais_de_35_dias_pelo_nome_do_arquivo(tmp_path, idade, sai):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    dia = (HOJE - timedelta(days=idade)).isoformat()
    for d in (dia, RECENTE):
        _escreve(pasta, d)
    codigo, _, _ = _corta(pasta, ParticaoFalsa(pasta, dias=(dia, RECENTE)))
    assert codigo == 0 and (dia not in _no_disco(pasta)) is sai


def test_a_idade_vem_do_nome_e_nao_do_mtime(bruto):
    agora = 1_900_000_000
    os.utime(bruto / oplog.nome_do_dia(VELHO), (agora, agora))                  # velho de nome, novo de mtime
    antigo = agora - 200 * 86400
    os.utime(bruto / oplog.nome_do_dia(NOVO), (antigo, antigo))                 # novo de nome, velho de mtime
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 0 and _no_disco(bruto) == [NOVO, RECENTE]


# --- cada conferência sozinha reprova --------------------------------------------------------------------

def test_linhagem_com_contagem_de_linhas_diferente_reprova(bruto):
    api = ParticaoFalsa(bruto)
    api.linhas[VELHO]["passada"]["linhas_legiveis"] += 1
    tarefas = TarefasFalsa()
    codigo, _, poda = _corta(bruto, api, tarefas)
    assert codigo == 1 and VELHO in _no_disco(bruto) and len(tarefas.criados) == 1
    assert "reprovado — linhas (" in poda.read_text(encoding="utf-8")


def test_evento_a_menos_na_particao_reprova(bruto):
    api = ParticaoFalsa(bruto, eventos={VELHO: 3})
    tarefas = TarefasFalsa()
    codigo, _, poda = _corta(bruto, api, tarefas)
    assert codigo == 1 and VELHO in _no_disco(bruto)
    assert "reprovado — eventos (" in poda.read_text(encoding="utf-8")


def test_evento_a_mais_na_particao_tambem_reprova(bruto):
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto, eventos={VELHO: 5}))
    assert codigo == 1 and VELHO in _no_disco(bruto)


def test_arquivo_com_tamanho_diferente_da_linhagem_reprova(bruto):
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"bytes": 1}}))
    assert codigo == 1 and "sha256" in poda.read_text(encoding="utf-8")


def test_varias_conferencias_reprovadas_aparecem_juntas(bruto):
    api = ParticaoFalsa(bruto, eventos={VELHO: 1}, **{VELHO: {"sha256": "f" * 64}})
    _, _, poda = _corta(bruto, api)
    assert "reprovado — eventos,sha256 (" in poda.read_text(encoding="utf-8")


def test_a_contagem_de_eventos_atravessa_as_paginas_de_mil(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    _escreve(pasta, VELHO, [json.dumps({"tool": "acervo", "n": i}) for i in range(2500)])
    _escreve(pasta, RECENTE)
    api = ParticaoFalsa(pasta, dias=(VELHO, RECENTE))
    codigo, _, _ = _corta(pasta, api)
    paginas = [c for c in api.chamadas if c[1].endswith("/eventos")]
    assert codigo == 0 and VELHO not in _no_disco(pasta)
    assert len(paginas) == 3 and all(p[2]["limite"] == 1000 for p in paginas)
    assert [p[2].get("cursor") for p in paginas] == [None, "1000", "2000"]


def test_cursor_que_nao_anda_nao_gira_para_sempre(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    _escreve(pasta, VELHO)
    _escreve(pasta, RECENTE)

    class Presa(ParticaoFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if caminho.endswith("/eventos"):
                return 200, {"itens": [{"evento_id": "a"}], "proximo": "a"}
            return super().chamar(metodo, caminho, corpo, params, aceita)
    codigo, _, _ = _corta(pasta, Presa(pasta, dias=(VELHO, RECENTE)))
    assert codigo == 1 and VELHO in _no_disco(pasta)


# --- incidente sem duplicar; API fora --------------------------------------------------------------------

def test_incidente_ja_aberto_nao_se_repete(bruto):
    titulo = f"{oplog.ROTULO_BRUTO} {VELHO}: bruto reprovado no portão"
    tarefas = TarefasFalsa(abertos={titulo, "outro incidente"})
    codigo, saida, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"sha256": "0" * 64}}), tarefas)
    assert codigo == 1 and tarefas.criados == [] and VELHO in _no_disco(bruto)
    assert "incidente já aberto" in poda.read_text(encoding="utf-8")


def test_incidente_que_nao_abre_e_dito_e_o_dia_fica(bruto, capsys):
    class Quebra(TarefasFalsa):
        def abrir_incidente(self, titulo, corpo):
            raise Falha(5, "tarefas criar saiu 1: fora")
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"sha256": "0" * 64}}), Quebra())
    assert codigo == 1, "segue reprovado (o de maior gravidade); a unit falha e a noite seguinte tenta o incidente de novo"
    assert VELHO in _no_disco(bruto)
    assert "incidente NÃO aberto" in poda.read_text(encoding="utf-8")
    assert "incidente não aberto" in capsys.readouterr().err


def test_api_fora_retem_tudo_e_sai_3(bruto):
    api = ParticaoFalsa(bruto, falha=Falha(3, "o acervo não respondeu"))
    codigo, saida, poda = _corta(bruto, api)
    assert codigo == 3 and _no_disco(bruto) == [VELHO, NOVO, RECENTE]
    assert len(api.chamadas) == 1, "API fora para um é fora para todos: para na primeira"
    assert f"corte-bruto {VELHO}: retido — linhagem_indisponivel [3]" in poda.read_text(encoding="utf-8")


def test_token_recusado_sai_4_e_nada_sai(bruto):
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto, falha=Falha(4, "token")))
    assert codigo == 4 and VELHO in _no_disco(bruto)


# --- travas além do portão -------------------------------------------------------------------------------

def test_no_maximo_tres_cortes_por_rodada_do_mais_velho_ao_mais_novo(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    dias = [(HOJE - timedelta(days=n)).isoformat() for n in (45, 44, 43, 42, 41)] + [RECENTE]
    for d in dias:
        _escreve(pasta, d)
    codigo, saida, _ = _corta(pasta, ParticaoFalsa(pasta, dias=dias))
    assert codigo == 0 and _no_disco(pasta) == sorted(dias[3:])
    assert any("2 dia(s) ficam para a próxima rodada (máximo 3 cortes e 1500s por rodada)" in l for l in saida)


def test_o_teto_por_rodada_vem_do_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTE_MAX_DIAS", "1")
    pasta = tmp_path / "ops"
    pasta.mkdir()
    dias = [(HOJE - timedelta(days=n)).isoformat() for n in (45, 44)] + [RECENTE]
    for d in dias:
        _escreve(pasta, d)
    _corta(pasta, ParticaoFalsa(pasta, dias=dias))
    assert _no_disco(pasta) == sorted(dias[1:])


def test_relogio_a_frente_do_bruto_nao_corta(bruto, capsys):
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto), hoje=date(2027, 3, 1))
    assert codigo == 5 and _no_disco(bruto) == [VELHO, NOVO, RECENTE] and not poda.exists()
    assert "relógio ou porta" in capsys.readouterr().err


def test_arquivo_do_futuro_nao_corta(bruto):
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto), hoje=date(2026, 10, 20))
    assert codigo == 5 and VELHO in _no_disco(bruto)


def test_arquivo_que_sumiu_entre_a_listagem_e_a_leitura_nao_quebra(bruto, monkeypatch):
    monkeypatch.setattr(oplog, "conteudo_do_dia", lambda dia, d=None: None)
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 0 and VELHO in _no_disco(bruto)


def test_arquivo_que_muda_depois_da_conferencia_nao_e_apagado(bruto, monkeypatch):
    original = oplog.remover_dia_conferido

    def muda_e_tenta(dia, sha256, diretorio_=None):
        with open(bruto / oplog.nome_do_dia(dia), "a", encoding="utf-8") as f:
            f.write('{"tool":"acervo","chegou":"depois"}\n')
        return original(dia, sha256, diretorio_)
    monkeypatch.setattr(oplog, "remover_dia_conferido", muda_e_tenta)
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 0 and VELHO in _no_disco(bruto)
    assert "retido — mudou_durante_a_conferencia" in poda.read_text(encoding="utf-8")


def test_remover_dia_conferido_so_apaga_com_o_sha_certo(bruto):
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    assert oplog.remover_dia_conferido(VELHO, "0" * 64, bruto) is False and VELHO in _no_disco(bruto)
    assert oplog.remover_dia_conferido("2026-01-01", sha, bruto) is False, "dia que não existe"
    assert oplog.remover_dia_conferido(VELHO, sha, bruto) is True and VELHO not in _no_disco(bruto)


# --- o ensaio --seco ------------------------------------------------------------------------------------

def test_seco_confere_e_diz_mas_nao_apaga_nao_grava_e_nao_abre_incidente(bruto):
    tarefas = TarefasFalsa()
    api = ParticaoFalsa(bruto, dias=(VELHO, NOVO, RECENTE), **{NOVO: {"sha256": "0" * 64}})
    codigo, saida, poda = _corta(bruto, api, tarefas, argv=["--seco", "--mais-velhos-que", "20"])
    assert _no_disco(bruto) == [VELHO, NOVO, RECENTE], "o ensaio não apaga nada"
    assert not poda.exists() and tarefas.criados == [] and tarefas.listagens == 0
    assert any(l.startswith(f"corte-bruto {VELHO}: cortaria — conferido") for l in saida)
    assert any(l.startswith(f"corte-bruto {NOVO}: reprovaria — sha256") for l in saida)
    assert saida[-1].startswith("corte-bruto ensaio — candidatos=2 cortados=0") and codigo == 1


def test_mais_velhos_que_sem_seco_e_recusado(bruto, capsys):
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto), argv=["--mais-velhos-que", "0"])
    assert codigo == 2 and VELHO in _no_disco(bruto)
    assert "só vale com --seco" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["--dia", "2026-10-01"], ["--seco", "--mais-velhos-que"], ["--seco", "--mais-velhos-que", "x"]])
def test_o_corte_nao_aceita_dia_a_mao_nem_uso_errado(bruto, argv):
    codigo, _, _ = _corta(bruto, ParticaoFalsa(bruto), argv=argv)
    assert codigo == 2 and _no_disco(bruto) == [VELHO, NOVO, RECENTE]


# --- poda.log: uma linha por dia e a linha de vida ----------------------------------------------------------

def test_poda_log_leva_uma_linha_por_dia_e_a_linha_de_vida(bruto):
    _, _, poda = _corta(bruto, ParticaoFalsa(bruto))
    linhas = poda.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 3 and re.match(r"^\d{4}-\d{2}-\d{2}T[\d:]+[+-]\d{2}:\d{2} corte-bruto ", linhas[0])
    assert ": cortando — conferido" in linhas[0] and ": cortado — conferido" in linhas[1], "a intenção e o resultado"
    assert linhas[2].endswith("corte-bruto ok — candidatos=1 cortados=1 retidos=0 reprovados=0 · prazo=35d · no disco=3 dias")


def test_poda_log_grava_a_linha_de_vida_mesmo_sem_candidato(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    _escreve(pasta, RECENTE)
    _, _, poda = _corta(pasta, ParticaoFalsa(pasta, dias=(RECENTE,)))
    assert "corte-bruto ok — candidatos=0 cortados=0" in poda.read_text(encoding="utf-8")


def test_nada_do_bruto_vai_para_a_saida_nem_para_o_poda_log(bruto):
    _, saida, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"sha256": "0" * 64}}))
    tudo = "\n".join(saida) + poda.read_text(encoding="utf-8")
    assert not any(s in tudo for s in SEGREDOS)


# --- o rastreador de verdade (um binário falso no lugar do `tarefas`) --------------------------------------

@pytest.mark.skipif(shutil.which("bash") is None, reason="sem bash")
def test_tarefas_lista_os_tres_estados_abertos_e_cria_o_incidente_para_a_seguranca(tmp_path, monkeypatch):
    falso = tmp_path / "tarefas"
    falso.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$FAKE_LOG"\n'
        'case "$1" in\n'
        '  listar) case "$3" in detectado) printf "7\\tdetectado\\tvar/log/ops 2026-10-01: bruto reprovado no portão\\n";;\n'
        '                       mitigado) printf "8\\tmitigado\\toutro incidente\\n";; esac ;;\n'
        '  criar) cat > "$FAKE_LOG.stdin"; echo "item 9 criado: $2" ;;\n'
        'esac\n', encoding="utf-8")
    falso.chmod(0o755)
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "chamadas"))
    t = cw.Tarefas(falso)
    assert t.titulos_abertos() == {"var/log/ops 2026-10-01: bruto reprovado no portão", "outro incidente"}
    chamadas = (tmp_path / "chamadas").read_text(encoding="utf-8").splitlines()
    assert chamadas == ["listar --estado detectado", "listar --estado em-mitigacao", "listar --estado mitigado"]
    assert t.abrir_incidente("titulo X", "corpo Y") == "item 9 criado: titulo X"
    assert (tmp_path / "chamadas").read_text(encoding="utf-8").splitlines()[-1] == \
        "criar titulo X --incidente --cadeira seguranca --desc-stdin"
    assert (tmp_path / "chamadas.stdin").read_text(encoding="utf-8") == "corpo Y"


@pytest.mark.skipif(shutil.which("bash") is None, reason="sem bash")
def test_tarefas_que_falha_vira_falha_5_e_binario_ausente_vira_3(tmp_path):
    ruim = tmp_path / "tarefas"
    ruim.write_text('#!/usr/bin/env bash\necho "sem rede" >&2\nexit 7\n', encoding="utf-8")
    ruim.chmod(0o755)
    with pytest.raises(Falha) as e:
        cw.Tarefas(ruim).titulos_abertos()
    assert e.value.codigo == 5 and "sem rede" in str(e.value)
    with pytest.raises(Falha) as e:
        cw.Tarefas(tmp_path / "nao-existe").abrir_incidente("t", "c")
    assert e.value.codigo == 3


def test_o_binario_do_rastreador_padrao_e_o_tarefas_da_mesma_release(monkeypatch):
    monkeypatch.delenv("PF_TAREFAS_BIN", raising=False)
    assert Path(cw.Tarefas().binario) == RAIZ / "bin" / "tarefas"
    monkeypatch.setenv("PF_TAREFAS_BIN", "/bin/true")
    assert cw.Tarefas().binario == "/bin/true"


# --- lib/oplog: o prazo, o disco, o teto ------------------------------------------------------------------

def test_dias_no_disco_ignora_o_que_nao_e_arquivo_do_dia(tmp_path):
    _escreve(tmp_path, "2026-10-02")
    (tmp_path / "ops-2026-13-45.jsonl").write_text("x")
    (tmp_path / "ops-2026-10-03.jsonl.tmp").write_text("x")
    (tmp_path / "outro.jsonl").write_text("x")
    (tmp_path / "ops-2026-10-04.jsonl").mkdir()
    (tmp_path / "ops-2026-10-05.jsonl").symlink_to(tmp_path / "ops-2026-10-02.jsonl")
    assert list(oplog.dias_no_disco(tmp_path)) == ["2026-10-02"]
    assert oplog.dias_no_disco(tmp_path / "nao-existe") == {}


def test_idade_e_mais_velhos_que(tmp_path):
    for d in ("2026-10-01", "2026-10-06", "2026-10-07"):
        _escreve(tmp_path, d)
    assert oplog.idade_em_dias("2026-10-01", HOJE) == 40
    assert oplog.dias_mais_velhos_que(35, HOJE, tmp_path) == ["2026-10-01"], "35 dias exatos ainda ficam"
    assert oplog.dias_mais_velhos_que(34, HOJE, tmp_path) == ["2026-10-01", "2026-10-06"]


@pytest.mark.parametrize("instante, dia", [
    ("2026-10-08T20:56:48.446580+00:00", "2026-10-08"),
    ("2026-10-09T02:59:59+00:00", "2026-10-08"),        # 23:59:59 do dia 8 em Sao_Paulo
    ("2026-10-09T03:00:00+00:00", "2026-10-09"),
    ("2026-10-09T03:00:00Z", "2026-10-09"),
    ("2026-10-08T23:30:00-03:00", "2026-10-08"),
    ("2026-10-08T10:00:00", "2026-10-08"),              # sem fuso: já é local
])
def test_dia_local_e_o_dia_da_porta(instante, dia):
    assert oplog.dia_local(instante) == dia


def test_dia_local_recusa_o_que_nao_e_instante():
    with pytest.raises(ValueError):
        oplog.dia_local("ontem")


def test_cortes_desde_lista_o_dia_velho_sem_arquivo(tmp_path):
    for d in ("2026-10-01", "2026-10-03", RECENTE):
        _escreve(tmp_path, d)
    # janela: de max(desde, 15/09) a hoje - 36 dias (05/10): 01/10, 02/10, 03/10, 04/10, 05/10 menos o que existe
    assert oplog.cortes_desde("2026-10-01", HOJE, tmp_path) == ["2026-10-02", "2026-10-04", "2026-10-05"]
    assert oplog.cortes_desde("2026-10-03", HOJE, tmp_path) == ["2026-10-04", "2026-10-05"]
    assert oplog.cortes_desde("2026-10-06", HOJE, tmp_path) == [], "dia dentro do prazo ausente nunca foi cortado"


def test_cortes_desde_nao_olha_antes_do_inicio_do_bruto(tmp_path):
    _escreve(tmp_path, RECENTE)
    achados = oplog.cortes_desde("2026-01-01", HOJE, tmp_path)
    assert achados[0] == "2026-09-15" and "2026-09-14" not in achados


def test_teto_dentro_acima_e_sem_base(tmp_path):
    for n in range(1, 29):
        (tmp_path / oplog.nome_do_dia(HOJE - timedelta(days=n))).write_bytes(b"x" * 1000)
    t = oplog.teto_do_bruto(HOJE, tmp_path)
    assert t["estado"] == "dentro" and t["mediana_bytes_dia"] == 1000 and t["teto_bytes"] == 52500
    assert t["bytes"] == 28000 and t["dias_na_base"] == 28 and t["dias_no_disco"] == 28
    (tmp_path / oplog.nome_do_dia(HOJE - timedelta(days=60))).write_bytes(b"x" * 60000)
    assert oplog.teto_do_bruto(HOJE, tmp_path)["estado"] == "acima", "o velho fora da base pesa no total"
    (tmp_path / oplog.nome_do_dia(HOJE)).write_bytes(b"x" * 10 ** 6)
    assert oplog.teto_do_bruto(HOJE, tmp_path)["mediana_bytes_dia"] == 1000, "hoje, incompleto, não entra na base"


def test_teto_sem_base_nao_inventa_teto(tmp_path):
    for n in range(1, 4):
        (tmp_path / oplog.nome_do_dia(HOJE - timedelta(days=n))).write_bytes(b"x" * 1000)
    t = oplog.teto_do_bruto(HOJE, tmp_path)
    assert (t["estado"], t["teto_bytes"], t["mediana_bytes_dia"]) == ("sem_base", None, None)
    assert oplog.teto_do_bruto(HOJE, tmp_path / "nada")["estado"] == "sem_base"


def test_teto_usa_a_mediana_e_nao_a_media(tmp_path):
    tamanhos = [100] * 13 + [100_000] + [100] * 14
    for n, t in enumerate(tamanhos, 1):
        (tmp_path / oplog.nome_do_dia(HOJE - timedelta(days=n))).write_bytes(b"x" * t)
    assert oplog.teto_do_bruto(HOJE, tmp_path)["mediana_bytes_dia"] == 100


def _oplog_cli(*args, ops_dir):
    env = {**os.environ, "OPS_LOG_DIR": str(ops_dir), "PYTHONPATH": str(RAIZ / "lib")}
    return subprocess.run([sys.executable, "-m", "oplog", *args], capture_output=True, text=True, env=env, check=False)


def test_cli_do_oplog_responde_dia_local_cortes_e_teto(tmp_path):
    _escreve(tmp_path, RECENTE)
    r = _oplog_cli("dia-local", "2026-10-09T02:00:00+00:00", ops_dir=tmp_path)
    assert (r.returncode, r.stdout.strip()) == (0, "2026-10-08")
    r = _oplog_cli("cortes-desde", "2026-10-01", "--hoje", "2026-11-10", ops_dir=tmp_path)
    assert r.returncode == 1 and r.stdout.splitlines()[0] == "2026-10-01"
    r = _oplog_cli("cortes-desde", "2026-10-30", "--hoje", "2026-11-10", ops_dir=tmp_path)
    assert (r.returncode, r.stdout) == (0, "")
    r = _oplog_cli("teto", "--hoje", "2026-11-10", ops_dir=tmp_path)
    assert r.returncode == 0 and json.loads(r.stdout)["estado"] == "sem_base"
    assert _oplog_cli("dia-local", "ontem", ops_dir=tmp_path).returncode == 2
    assert _oplog_cli("cortes-desde", ops_dir=tmp_path).returncode == 2
    assert _oplog_cli("teto", "--hoje", ops_dir=tmp_path).returncode == 2


# --- a unit, o timer e o binário ---------------------------------------------------------------------------

def test_o_binario_e_fino_declara_o_exit_nas_40_primeiras_linhas_e_roda(tmp_path):
    linhas = CORTE.read_text(encoding="utf-8").splitlines()
    assert linhas[0] == "#!/usr/bin/env python3" and any(l.startswith("# exit:") for l in linhas[:40])
    env = {**os.environ, "OPS_LOG_DIR": str(tmp_path / "ops"), "PLATAFIRMA_INSTANCIA": str(tmp_path)}
    (tmp_path / "ops").mkdir()
    r = subprocess.run([sys.executable, str(CORTE)], capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 0 and "corte-bruto ok — candidatos=0" in r.stdout
    assert "corte-bruto ok" in (tmp_path / "var" / "log" / "poda.log").read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, str(CORTE), "--ajuda"], capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 0 and r.stdout.startswith("uso: corte-bruto")
    r = subprocess.run([sys.executable, str(CORTE), "--hoje", "x"], capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 2


def test_corte_args_do_dropin_vira_argumento(tmp_path):
    (tmp_path / "ops").mkdir()
    env = {**os.environ, "OPS_LOG_DIR": str(tmp_path / "ops"), "PLATAFIRMA_INSTANCIA": str(tmp_path),
           "CORTE_ARGS": "--seco,--mais-velhos-que,20"}
    r = subprocess.run([sys.executable, str(CORTE)], capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 0 and "corte-bruto ensaio — candidatos=0" in r.stdout
    assert not (tmp_path / "var" / "log" / "poda.log").exists(), "o ensaio não grava poda.log"


def test_service_e_timer_do_corte():
    servico = (RAIZ / "deploy-harness" / "corte-bruto.service").read_text(encoding="utf-8")
    timer = (RAIZ / "deploy-harness" / "corte-bruto.timer").read_text(encoding="utf-8")
    assert "After=linhagem-ops.service" in servico and "Type=oneshot" in servico
    assert "ExecStart=/opt/platafirma/current/venv/harness/bin/python /opt/platafirma/current/harness/bin/_infra/corte-bruto" in servico
    assert "EnvironmentFile=/home/claudinho/.config/ops/env" in servico and "Environment=PF_CADEIRA=ti" in servico
    assert "SuccessExitStatus=0" in servico and "/usr/bin/python3" not in servico
    assert "OnCalendar=*-*-* 01:20:00" in timer and "Persistent=true" in timer and "WantedBy=timers.target" in timer


def test_o_timer_do_corte_entra_na_lista_de_units_de_instalar_depois_da_linhagem():
    instalar = (RAIZ / "deploy-harness" / "instalar").read_text(encoding="utf-8")
    lista = re.findall(r'"deploy-harness/([a-z-]+\.(?:service|timer))\|', instalar)
    assert lista.index("corte-bruto.service") > lista.index("linhagem-ops.timer")
    assert '"deploy-harness/corte-bruto.service|alvo-de-timer"' in instalar
    assert '"deploy-harness/corte-bruto.timer|habilita"' in instalar


def test_so_o_corte_apaga_o_bruto():
    """arq:0123 §12: só o timer corta. `remover_dia_conferido` e `oplog_corte` não aparecem em código de nenhum arquivo
    da árvore (verbo, ops-server, mcp, hooks, agente...) fora de teste: só em lib/oplog.py (a definição),
    lib/oplog_corte.py e bin/_infra/corte-bruto."""
    donos = {"lib/oplog.py", "lib/oplog_corte.py", "bin/_infra/corte-bruto"}
    achados = []
    for arq in sorted(RAIZ.rglob("*")):
        rel = arq.relative_to(RAIZ).as_posix()
        if (not arq.is_file() or arq.is_symlink() or rel in donos or ".git" in arq.parts
                or "__pycache__" in arq.parts or ".pytest_cache" in arq.parts
                or rel.startswith(("controle/tests/", "testes/"))):
            continue
        try:
            if arq.stat().st_size > 2_000_000:
                continue
            texto = arq.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        codigo = "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))
        if "remover_dia_conferido" in codigo or "oplog_corte" in codigo:
            achados.append(rel)
    assert achados == [], f"quem mais chama o corte: {achados}"


# --- o que a revisão independente achou (card #3354) -------------------------------------------------------

def _dois_velhos(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    dias = [(HOJE - timedelta(days=n)).isoformat() for n in (45, 44)]
    for d in (*dias, RECENTE):
        _escreve(pasta, d)
    return pasta, dias


class _Morte(BaseException):
    pass


@pytest.mark.parametrize("morre_na_linha, sai_o_primeiro", [(1, False), (2, True)])
def test_o_processo_que_morre_no_meio_deixa_rastro_de_cada_passo(tmp_path, morre_na_linha, sai_o_primeiro):
    """Kill ou timeout: a intenção («cortando») vai ao poda.log ANTES da remoção, o resultado («cortado») logo
    depois e antes do dia seguinte, e o poda.log vem antes da saída (que é quem morre aqui)."""
    pasta, dias = _dois_velhos(tmp_path)
    poda, vistas = tmp_path / "poda.log", []

    def saida_que_morre(linha):
        vistas.append(linha)
        if len(vistas) == morre_na_linha:
            raise _Morte
    with pytest.raises(_Morte):
        cw.main([], api=ParticaoFalsa(pasta, dias=(*dias, RECENTE)), hoje=HOJE, tarefas=TarefasFalsa(),
                 saida=saida_que_morre, diretorio_=pasta, poda_log=poda)
    log = poda.read_text(encoding="utf-8")
    assert f"corte-bruto {dias[0]}: cortando — conferido" in log, "a intenção está gravada"
    assert (f"corte-bruto {dias[0]}: cortado — conferido" in log) is sai_o_primeiro
    assert (dias[0] not in _no_disco(pasta)) is sai_o_primeiro
    assert dias[1] in _no_disco(pasta) and f"corte-bruto {dias[1]}" not in log, "o segundo nem foi olhado"


def test_erro_inesperado_de_um_dia_retem_o_dia_registra_e_segue(tmp_path, monkeypatch):
    pasta, dias = _dois_velhos(tmp_path)
    real = cw.portao

    def quebra_no_primeiro(api, dia, dados, **k):
        if dia == dias[0]:
            raise RuntimeError("disco")
        return real(api, dia, dados, **k)
    monkeypatch.setattr(cw, "portao", quebra_no_primeiro)
    codigo, _, poda = _corta(pasta, ParticaoFalsa(pasta, dias=(*dias, RECENTE)))
    log = poda.read_text(encoding="utf-8")
    assert codigo == 5 and _no_disco(pasta) == [dias[0], RECENTE]
    assert f"corte-bruto {dias[0]}: retido — erro_inesperado [RuntimeError]" in log
    assert f"corte-bruto {dias[1]}: cortado" in log


@pytest.mark.parametrize("quebra, esperado_na_linha", [
    (PermissionError(13, "negado"), "erro_inesperado [PermissionError]"),
    (IsADirectoryError(21, "pasta"), "erro_inesperado [IsADirectoryError]"),
])
def test_erro_de_disco_na_remocao_retem_e_nao_derruba_a_rodada(bruto, monkeypatch, quebra, esperado_na_linha):
    def remove_e_quebra(dia, sha256, diretorio_=None):
        raise quebra
    monkeypatch.setattr(oplog, "remover_dia_conferido", remove_e_quebra)
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 5 and VELHO in _no_disco(bruto)
    assert esperado_na_linha in poda.read_text(encoding="utf-8")


def test_falha_da_api_num_dia_so_nao_para_a_rodada(tmp_path):
    pasta, dias = _dois_velhos(tmp_path)

    class FalhaSoNoPrimeiro(ParticaoFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if (params or {}).get("desde") == dias[0] or dias[0] in caminho:
                raise Falha(5, "passou de 180s")
            return super().chamar(metodo, caminho, corpo, params, aceita)
    codigo, _, poda = _corta(pasta, FalhaSoNoPrimeiro(pasta, dias=(*dias, RECENTE)))
    assert codigo == 5 and _no_disco(pasta) == [dias[0], RECENTE]
    assert f"corte-bruto {dias[0]}: retido — linhagem_indisponivel [5]" in poda.read_text(encoding="utf-8")


@pytest.mark.parametrize("codigo_da_falha, exit_", [(1, 5), (2, 5), (5, 5)])
def test_falha_de_dia_1_2_ou_5_sai_5_e_nao_se_confunde_com_reprovado(tmp_path, codigo_da_falha, exit_):
    pasta, dias = _dois_velhos(tmp_path)
    codigo, _, _ = _corta(pasta, ParticaoFalsa(pasta, dias=(*dias, RECENTE), falha=Falha(codigo_da_falha, "x")))
    assert codigo == exit_ and _no_disco(pasta) == [*dias, RECENTE]


def test_sobra_de_corte_interrompido_volta_ao_nome_do_dia_e_o_dia_e_decidido_de_novo(bruto):
    nome = bruto / oplog.nome_do_dia(VELHO)
    os.replace(nome, bruto / (nome.name + ".corte"))              # o que um corte que morreu deixa
    assert VELHO not in _no_disco(bruto)
    codigo, saida, poda = _corta(bruto, ParticaoFalsa(bruto, dias=(NOVO, RECENTE), **{}), argv=[])
    assert any(f"corte-bruto {VELHO}: devolvido" in l for l in saida), "a sobra voltou ao nome"
    # sem linhagem do dia na partição falsa: fica, mas fica visível e no lugar certo
    assert VELHO in _no_disco(bruto) and not (bruto / (nome.name + ".corte")).exists()
    assert codigo == 0 and f"corte-bruto {VELHO}: retido — sem_linhagem" in poda.read_text(encoding="utf-8")


def test_devolver_sobras_nao_pisa_em_dia_que_ja_existe(tmp_path):
    _escreve(tmp_path, VELHO)
    (tmp_path / (oplog.nome_do_dia(VELHO) + ".corte")).write_bytes(b"outra")
    voltaram, presas = oplog.devolver_sobras_do_corte(tmp_path)
    assert voltaram == [] and [d for d, _ in presas] == [VELHO], "a sobra que não pôde voltar é dita"
    assert (tmp_path / (oplog.nome_do_dia(VELHO) + ".corte")).read_bytes() == b"outra"
    assert (tmp_path / oplog.nome_do_dia(VELHO)).read_bytes() != b"outra"
    assert oplog.devolver_sobras_do_corte(tmp_path / "nao-existe") == ([], [])


def test_devolver_sobras_ignora_nome_impossivel_e_limpa_o_segundo_nome_do_mesmo_arquivo(tmp_path):
    (tmp_path / "ops-2026-13-45.jsonl.corte").write_bytes(b"x")
    _escreve(tmp_path, VELHO)
    os.link(tmp_path / oplog.nome_do_dia(VELHO), tmp_path / (oplog.nome_do_dia(VELHO) + ".corte"))
    assert oplog.devolver_sobras_do_corte(tmp_path) == ([VELHO], [])
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(["ops-2026-13-45.jsonl.corte", oplog.nome_do_dia(VELHO)])


def test_main_diz_a_sobra_presa_e_sai_5_sem_apagar_nada(bruto):
    (bruto / (oplog.nome_do_dia(NOVO) + ".corte")).write_bytes(b"outros bytes")
    codigo, saida, poda = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 5 and any(f"corte-bruto {NOVO}: sobra presa" in l for l in saida)
    assert (bruto / (oplog.nome_do_dia(NOVO) + ".corte")).read_bytes() == b"outros bytes"
    assert VELHO not in _no_disco(bruto), "o resto da rodada segue: o dia velho conferido sai"


def test_remover_nao_pisa_em_corte_que_ja_existe(bruto):
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    (bruto / (oplog.nome_do_dia(VELHO) + ".corte")).write_bytes(b"sobra de outro corte")
    with pytest.raises(FileExistsError):
        oplog.remover_dia_conferido(VELHO, sha, bruto)
    assert (bruto / (oplog.nome_do_dia(VELHO) + ".corte")).read_bytes() == b"sobra de outro corte"
    assert VELHO in _no_disco(bruto)


def test_devolver_nao_pisa_no_arquivo_novo_que_ocupou_o_nome(bruto, monkeypatch):
    """Alguém cria o arquivo do dia entre o rename e o hash: a devolução não o sobrescreve, o `.corte` fica ao lado."""
    nome = bruto / oplog.nome_do_dia(VELHO)
    antes = nome.read_bytes()
    real = Path.read_bytes

    def le_e_ocupa_o_nome(self):
        if self.name.endswith(".corte"):
            nome.write_bytes(b"arquivo novo")
            return b"bytes que nao batem"
        return real(self)
    monkeypatch.setattr(Path, "read_bytes", le_e_ocupa_o_nome)
    with pytest.raises(FileExistsError):
        oplog.remover_dia_conferido(VELHO, "0" * 64, bruto)
    monkeypatch.undo()
    assert nome.read_bytes() == b"arquivo novo"
    assert (bruto / (nome.name + ".corte")).read_bytes() == antes, "o original segue inteiro, ao lado e visível"


def test_remocao_fecha_a_janela_e_nao_deixa_sobra(bruto):
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    assert oplog.remover_dia_conferido(VELHO, sha, bruto) is True
    assert sorted(p.name for p in bruto.iterdir()) == [oplog.nome_do_dia(NOVO), oplog.nome_do_dia(RECENTE)]
    assert oplog.remover_dia_conferido(VELHO, "0" * 64, bruto) is False
    assert oplog.remover_dia_conferido(NOVO, "0" * 64, bruto) is False
    assert sorted(p.name for p in bruto.iterdir()) == [oplog.nome_do_dia(NOVO), oplog.nome_do_dia(RECENTE)], \
        "sha errado devolve o arquivo ao nome, sem sobra"


def test_remocao_que_falha_ao_tirar_o_nome_do_dia_nao_muda_nada(bruto, monkeypatch):
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    antes = (bruto / oplog.nome_do_dia(VELHO)).read_bytes()
    real = Path.unlink

    def nega_o_nome_do_dia(self, *a, **k):
        if not self.name.endswith(".corte"):
            raise PermissionError(13, "negado")
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "unlink", nega_o_nome_do_dia)
    with pytest.raises(PermissionError):
        oplog.remover_dia_conferido(VELHO, sha, bruto)
    assert (bruto / oplog.nome_do_dia(VELHO)).read_bytes() == antes
    assert not (bruto / (oplog.nome_do_dia(VELHO) + ".corte")).exists(), "o segundo nome saiu"


def test_remocao_que_falha_no_ultimo_passo_devolve_o_arquivo_ao_nome_e_levanta(bruto, monkeypatch):
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    antes = (bruto / oplog.nome_do_dia(VELHO)).read_bytes()
    real = Path.unlink

    def nega_o_corte(self, *a, **k):
        if self.name.endswith(".corte"):
            raise PermissionError(13, "negado")
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "unlink", nega_o_corte)
    with pytest.raises(PermissionError):
        oplog.remover_dia_conferido(VELHO, sha, bruto)
    assert (bruto / oplog.nome_do_dia(VELHO)).read_bytes() == antes, "o dia voltou ao nome"
    monkeypatch.undo()
    assert oplog.devolver_sobras_do_corte(bruto) == ([VELHO], []), "o segundo nome do mesmo arquivo sai na rodada seguinte"
    assert sorted(p.name for p in bruto.iterdir()) == sorted(oplog.nome_do_dia(d) for d in (VELHO, NOVO, RECENTE))


def test_ambiente_ilegivel_e_uso_errado_sai_2_sem_tocar_o_bruto(bruto, monkeypatch):
    monkeypatch.setenv("CORTE_MAX_DIAS", "muitos")
    assert _corta(bruto, ParticaoFalsa(bruto))[0] == 2
    monkeypatch.delenv("CORTE_MAX_DIAS")
    monkeypatch.setenv("LINHAGEM_TIMEOUT_S", "logo")
    assert cw.main([], hoje=HOJE, diretorio_=bruto, poda_log=bruto.parent / "poda.log") == 2
    assert _no_disco(bruto) == [VELHO, NOVO, RECENTE]


def test_a_particao_responde_fora_do_contrato_e_o_dia_fica(bruto):
    class Torta(ParticaoFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            return 200, [{"dia": VELHO}]
    codigo, _, poda = _corta(bruto, Torta(bruto))
    assert codigo == 5 and VELHO in _no_disco(bruto)
    assert "linhagem_indisponivel [5]" in poda.read_text(encoding="utf-8")


def test_resposta_fora_do_contrato_tem_um_destino_so_falha_5_e_o_dia_fica(bruto):
    """D5.6 com corpo que não é objeto, sem lista, ou D5.5 sem a linha do dia: a partição está torta, não o bruto — nada
    de incidente para a segurança, nada de silêncio com exit 0."""
    tarefas = TarefasFalsa()
    for resposta in ([1, 2, 3], {"proximo": None}, {"itens": "nada"}):
        class Eventos(ParticaoFalsa):
            def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,), _r=resposta):
                if caminho.endswith("/eventos"):
                    return 200, _r
                return super().chamar(metodo, caminho, corpo, params, aceita)
        codigo, _, _ = _corta(bruto, Eventos(bruto), tarefas)
        assert codigo == 5 and VELHO in _no_disco(bruto), resposta
    for dias_resposta in ({"itens": "nada"}, {"itens": []}, {"proximo": None}):
        class Dias(ParticaoFalsa):
            def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,), _r=dias_resposta):
                if caminho == "/acervo/log/dias":
                    return 200, _r
                return super().chamar(metodo, caminho, corpo, params, aceita)
        codigo, _, _ = _corta(bruto, Dias(bruto), tarefas)
        assert codigo == 5 and VELHO in _no_disco(bruto), dias_resposta
    assert tarefas.criados == [] and tarefas.listagens == 0


def test_dia_com_zero_legiveis_nao_passa_se_a_particao_diz_ausente(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    _escreve(pasta, VELHO, ["isto nao e json", "nem isto"])
    _escreve(pasta, RECENTE)

    class Ausente(ParticaoFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if caminho.endswith("/eventos"):
                return 200, {"itens": [], "cobertura": "ausente", "proximo": None}
            return super().chamar(metodo, caminho, corpo, params, aceita)
    api = Ausente(pasta, dias=(VELHO, RECENTE))
    assert api.linhas[VELHO]["passada"]["linhas_legiveis"] == 0
    codigo, _, _ = _corta(pasta, api)
    assert codigo == 5 and VELHO in _no_disco(pasta), "D5.6 dizer ausente depois de D5.5 dizer que há passada é resposta torta"
    # e o mesmo dia, com a partição dizendo a verdade (parcial, nenhum evento), passa
    codigo, _, _ = _corta(pasta, ParticaoFalsa(pasta, dias=(VELHO, RECENTE)))
    assert codigo == 0 and VELHO not in _no_disco(pasta)


def test_linhagem_de_outro_dia_nao_vale(bruto):
    class OutroDia(ParticaoFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if caminho == "/acervo/log/dias":
                return 200, {"itens": [self.linhas[NOVO], self.linhas[RECENTE]], "proximo": None}
            return super().chamar(metodo, caminho, corpo, params, aceita)
    codigo, _, poda = _corta(bruto, OutroDia(bruto))
    assert codigo == 5 and VELHO in _no_disco(bruto), "a linha do dia não veio: fora do contrato, não silêncio"
    assert f"corte-bruto {VELHO}: retido — linhagem_indisponivel [5]" in poda.read_text(encoding="utf-8")


def test_o_motivo_da_particao_aparece_no_poda_log_quando_nao_ha_linhagem(bruto):
    api = ParticaoFalsa(bruto, **{VELHO: {"passada": False, "motivo": "extracao_falhou", "cobertura": "ausente"}})
    codigo, _, poda = _corta(bruto, api)
    assert codigo == 0 and VELHO in _no_disco(bruto)
    assert f"corte-bruto {VELHO}: retido — sem_linhagem:extracao_falhou" in poda.read_text(encoding="utf-8")


@pytest.mark.parametrize("parado_ha, sai_5", [(3, False), (4, True)])
def test_o_bruto_parado_ha_mais_de_3_dias_nao_corta(tmp_path, parado_ha, sai_5):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    recente = (HOJE - timedelta(days=parado_ha)).isoformat()
    for d in (VELHO, recente):
        _escreve(pasta, d)
    codigo, _, _ = _corta(pasta, ParticaoFalsa(pasta, dias=(VELHO, recente)))
    assert (codigo == 5) is sai_5 and ((VELHO in _no_disco(pasta)) is sai_5)


def test_hoje_local_e_o_dia_da_porta_nao_o_do_utc(monkeypatch):
    from datetime import datetime as real, timezone

    class Falso(real):
        @classmethod
        def now(cls, tz=None):
            return real(2026, 11, 10, 2, 30, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(oplog, "datetime", Falso)
    assert oplog.hoje_local() == date(2026, 11, 9), "02:30 UTC é 23:30 do dia 9 em America/Sao_Paulo"


def test_a_contagem_do_portao_e_a_do_extrator_nos_casos_de_borda(tmp_path):
    """O portao confere o que o extrator gravou: mesma regra de linha legivel, inclusive CR solto, CRLF, UTF-8
    invalido, linha em branco e ultima linha sem quebra."""
    import oplog_extracao as ex
    dados = (b'{"tool":"acervo","ts":"2026-10-01T10:00:00-03:00"}\n\n   \nnao e json\n[1,2]\n'
             b'{"tool":"acervo","x":"\xff\xfe"}\n{"tool":"acervo"}\r\n'
             b'{"tool":"acervo","a":1}\r{"tool":"acervo","b":2}\n{"tool":"acervo"')
    (tmp_path / oplog.nome_do_dia(VELHO)).write_bytes(dados)
    c = cw.contas_do_arquivo(dados)
    fecho = ex.extrair(VELHO, tmp_path).fecho("ti")
    assert (c["lidas"], c["legiveis"], c["ilegiveis"]) == (
        fecho["linhas_lidas"], fecho["linhas_legiveis"], fecho["linhas_ilegiveis"])
    assert c["lidas"] == c["legiveis"] + c["ilegiveis"]


def test_conexao_cortada_no_meio_da_resposta_e_falha_5_e_nao_excecao_solta(monkeypatch):
    import http.client
    import urllib.request

    def corta(*a, **k):
        raise http.client.IncompleteRead(b"meio")
    monkeypatch.setattr(urllib.request, "urlopen", corta)
    from oplog_extracao import Api
    with pytest.raises(Falha) as e:
        Api(base="http://127.0.0.1:1", token="").chamar("GET", "/acervo/log/dias")
    assert e.value.codigo == 5


def test_corpo_de_erro_cortado_no_meio_tambem_e_falha_5(monkeypatch):
    import http.client
    import urllib.error
    import urllib.request

    class Corpo:
        def read(self, *a):
            raise http.client.IncompleteRead(b"meio")

        def close(self):
            pass

    def responde_500(*a, **k):
        raise urllib.error.HTTPError("http://x/", 500, "erro", {}, Corpo())
    monkeypatch.setattr(urllib.request, "urlopen", responde_500)
    from oplog_extracao import Api
    with pytest.raises(Falha) as e:
        Api(base="http://127.0.0.1:1", token="").chamar("GET", "/acervo/log/dias")
    assert e.value.codigo == 5 and "HTTP 500" in str(e.value)


# --- a segunda revisão: o que a rodada faz quando tudo pende ---------------------------------------------

def _quatro_velhos(tmp_path):
    pasta = tmp_path / "ops"
    pasta.mkdir()
    dias = [(HOJE - timedelta(days=n)).isoformat() for n in (47, 46, 45, 44)]
    for d in (*dias, RECENTE):
        _escreve(pasta, d)
    return pasta, dias


def test_a_segunda_falha_de_api_seguida_para_a_rodada(tmp_path):
    """Timeout e 5xx não são do dia: N x 180 s estouraria o TimeoutStartSec da unit e mataria a rodada sem linha de vida."""
    pasta, dias = _quatro_velhos(tmp_path)
    api = ParticaoFalsa(pasta, dias=(*dias, RECENTE), falha=Falha(5, "passou de 180s sem resposta"))
    codigo, saida, poda = _corta(pasta, api)
    assert codigo == 5 and _no_disco(pasta) == [*dias, RECENTE]
    assert len(api.chamadas) == 2, "duas tentativas e para"
    log = poda.read_text(encoding="utf-8")
    assert f"corte-bruto {dias[0]}: retido" in log and f"corte-bruto {dias[1]}: retido" in log
    assert f"corte-bruto {dias[2]}" not in log and "corte-bruto ok — candidatos=4" in log, "a linha de vida fecha a rodada"


def test_orcamento_de_tempo_acaba_a_rodada_sem_cortar_nem_morrer(tmp_path, monkeypatch):
    pasta, dias = _quatro_velhos(tmp_path)
    monkeypatch.setenv("CORTE_ORCAMENTO_S", "0")
    codigo, saida, poda = _corta(pasta, ParticaoFalsa(pasta, dias=(*dias, RECENTE)))
    assert codigo == 0 and _no_disco(pasta) == [*dias, RECENTE]
    assert any("4 dia(s) ficam para a próxima rodada (máximo 3 cortes e 0s por rodada)" in l for l in saida)
    assert "corte-bruto ok — candidatos=4 cortados=0" in poda.read_text(encoding="utf-8")


def test_poda_log_que_nao_grava_nao_deixa_cortar(bruto):
    """Sem rastro de intenção gravado, o dia não sai."""
    poda = bruto.parent / "poda.log"
    poda.mkdir()                                        # abrir uma pasta para acrescentar falha com OSError
    saida = []
    codigo = cw.main([], api=ParticaoFalsa(bruto), hoje=HOJE, tarefas=TarefasFalsa(), saida=saida.append,
                     diretorio_=bruto, poda_log=poda)
    assert codigo == 5 and VELHO in _no_disco(bruto)
    assert any(f"corte-bruto {VELHO}: retido — poda_log_nao_gravou" in l for l in saida)


def test_o_exit_e_o_de_maior_gravidade_e_nao_o_de_maior_numero(tmp_path):
    pasta, dias = _dois_velhos(tmp_path)

    class SegundoFalha(ParticaoFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if dias[1] in caminho or (params or {}).get("desde") == dias[1]:
                raise Falha(5, "passou de 180s")
            return super().chamar(metodo, caminho, corpo, params, aceita)
    api = SegundoFalha(pasta, dias=(*dias, RECENTE), **{dias[0]: {"sha256": "0" * 64}})
    codigo, _, _ = _corta(pasta, api)
    assert codigo == 1, "reprovado (pede gente) vale mais que o erro de um dia"
    assert [cw._pior(a, b) for a, b in ((0, 5), (5, 3), (3, 4), (4, 1), (1, 5), (5, 1))] == [5, 3, 4, 1, 1, 1]


def test_o_veredito_do_portao_fica_gravado_mesmo_quando_o_passo_do_incidente_quebra(bruto):
    class Quebra(TarefasFalsa):
        def titulos_abertos(self):
            raise RuntimeError("tarefas caiu de um jeito que ninguem previu")
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto, **{VELHO: {"sha256": "0" * 64}}), Quebra())
    log = poda.read_text(encoding="utf-8")
    assert codigo == 1 and VELHO in _no_disco(bruto)
    assert f"corte-bruto {VELHO}: reprovado — sha256 (idade=40d" in log, "o motivo do portao não some"
    assert f"corte-bruto {VELHO}: retido — erro_inesperado [RuntimeError]" in log


def test_saida_quebrada_depois_da_remocao_nao_reescreve_o_veredito_do_dia(bruto, capsys):
    """A saída quebra depois do `unlink`: o dia saiu, o poda.log tem a linha, e nada diz que ficou."""
    def saida_que_quebra_no_resultado(linha):
        if ": cortado " in linha:
            raise RuntimeError("stdout quebrou")
    poda = bruto.parent / "poda.log"
    codigo = cw.main([], api=ParticaoFalsa(bruto), hoje=HOJE, tarefas=TarefasFalsa(),
                     saida=saida_que_quebra_no_resultado, diretorio_=bruto, poda_log=poda)
    log = poda.read_text(encoding="utf-8")
    assert VELHO not in _no_disco(bruto) and codigo == 0
    assert f"corte-bruto {VELHO}: cortado — conferido" in log and "retido — erro_inesperado" not in log
    assert "a saída falhou (RuntimeError)" in capsys.readouterr().err


def test_saida_quebrada_no_veredito_nao_pula_o_incidente(bruto):
    tarefas = TarefasFalsa()

    def saida_que_quebra_no_reprovado(linha):
        if ": reprovado " in linha:
            raise RuntimeError("stdout quebrou")
    poda = bruto.parent / "poda.log"
    codigo = cw.main([], api=ParticaoFalsa(bruto, **{VELHO: {"sha256": "0" * 64}}), hoje=HOJE, tarefas=tarefas,
                     saida=saida_que_quebra_no_reprovado, diretorio_=bruto, poda_log=poda)
    assert codigo == 1 and len(tarefas.criados) == 1 and "incidente aberto" in poda.read_text(encoding="utf-8")


def test_resultado_que_o_poda_log_nao_gravou_sobe_o_exit_para_5(bruto, monkeypatch):
    """A intenção gravou, o dia saiu, e o poda.log deixou de gravar: ficaria só «cortando», que o rastro lê como
    «morreu no meio». O exit não pode ser 0."""
    real = cw._grava_poda
    chamadas = []

    def grava_so_a_primeira(caminho, linhas):
        chamadas.append(linhas)
        return real(caminho, linhas) if len(chamadas) == 1 else False
    monkeypatch.setattr(cw, "_grava_poda", grava_so_a_primeira)
    codigo, _, poda = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 5 and VELHO not in _no_disco(bruto)
    assert ": cortando " in poda.read_text(encoding="utf-8") and ": cortado " not in poda.read_text(encoding="utf-8")


def test_motivo_da_particao_nao_forja_linha_de_rastro(bruto):
    api = ParticaoFalsa(bruto, **{VELHO: {"passada": False, "motivo": "x\n2099-01-01T00:00:00+00:00 corte-bruto 2026-01-01: cortado"}})
    _, _, poda = _corta(bruto, api)
    linhas = poda.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 2 and all(l.count(" corte-bruto ") == 1 for l in linhas), linhas
    assert "sem_linhagem:x_2099-01-01T00:00:00_00:00_corte-bruto_2026-01-01:" in linhas[0]


# --- a terceira passada: hardlink, janelas de corrida, ambiente ------------------------------------------------

def test_diretorio_sem_hardlink_diz_e_nao_comeca_o_portao(bruto, monkeypatch):
    def link_negado(*a, **k):
        raise PermissionError(1, "Operation not permitted")
    monkeypatch.setattr(os, "link", link_negado)
    api = ParticaoFalsa(bruto)
    codigo, saida, poda = _corta(bruto, api)
    assert codigo == 5 and _no_disco(bruto) == [VELHO, NOVO, RECENTE] and api.chamadas == []
    assert any("sem hardlink no diretório do bruto (PermissionError: Operation not permitted)" in l for l in saida)
    assert not [p.name for p in bruto.iterdir() if p.name.startswith(".sonda")], "a sonda não deixa rastro"
    # e o ensaio `--seco` acusa o mesmo, que é para isso que ele serve no ar
    codigo, saida, _ = _corta(bruto, ParticaoFalsa(bruto), argv=["--seco"])
    assert codigo == 5 and any("sem hardlink" in l for l in saida)


def test_sonda_de_hardlink_funciona_e_limpa(bruto):
    assert oplog.sondar_hardlink(bruto) is None
    assert sorted(p.name for p in bruto.iterdir()) == sorted(oplog.nome_do_dia(d) for d in (VELHO, NOVO, RECENTE))
    assert "FileNotFoundError" in oplog.sondar_hardlink(bruto / "nao-existe")


@pytest.mark.parametrize("max_dias, orcamento", [("-1", "10"), ("3", "-5"), ("3", "nan"), ("3", "inf")])
def test_ambiente_fora_do_possivel_sai_2(bruto, monkeypatch, max_dias, orcamento):
    monkeypatch.setenv("CORTE_MAX_DIAS", max_dias)
    monkeypatch.setenv("CORTE_ORCAMENTO_S", orcamento)
    assert _corta(bruto, ParticaoFalsa(bruto))[0] == 2 and VELHO in _no_disco(bruto)


def test_nome_do_dia_que_some_entre_o_link_e_o_unlink_deixa_o_corte_visivel(bruto, monkeypatch):
    """Outro processo levou o nome do dia: o `.corte` é o único nome dos bytes e não pode ser apagado sem hash."""
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    real = Path.unlink

    def leva_e_diz_que_nao_achou(self, *a, **k):
        if not self.name.endswith(".corte"):
            real(self)
            raise FileNotFoundError(2, "sumiu")
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "unlink", leva_e_diz_que_nao_achou)
    assert oplog.remover_dia_conferido(VELHO, sha, bruto) is False
    monkeypatch.undo()
    assert (bruto / (oplog.nome_do_dia(VELHO) + ".corte")).exists() and VELHO not in _no_disco(bruto)
    assert oplog.devolver_sobras_do_corte(bruto) == ([VELHO], []), "a rodada seguinte o devolve"


def test_interrupcao_depois_do_unlink_nao_tira_o_unico_nome(bruto, monkeypatch):
    sha = cw.contas_do_arquivo((bruto / oplog.nome_do_dia(VELHO)).read_bytes())["sha256"]
    real = Path.unlink

    def apaga_e_interrompe(self, *a, **k):
        if not self.name.endswith(".corte"):
            real(self)
            raise KeyboardInterrupt
        return real(self, *a, **k)
    monkeypatch.setattr(Path, "unlink", apaga_e_interrompe)
    with pytest.raises(KeyboardInterrupt):
        oplog.remover_dia_conferido(VELHO, sha, bruto)
    monkeypatch.undo()
    assert (bruto / (oplog.nome_do_dia(VELHO) + ".corte")).exists(), "os bytes seguem num nome só, visível"


def test_devolver_sobra_com_nome_do_dia_pendurado_vira_presa_e_nao_traceback(tmp_path):
    (tmp_path / (oplog.nome_do_dia(VELHO) + ".corte")).write_bytes(b"x")
    (tmp_path / oplog.nome_do_dia(VELHO)).symlink_to(tmp_path / "nao-existe")
    voltaram, presas = oplog.devolver_sobras_do_corte(tmp_path)
    assert voltaram == [] and [d for d, _ in presas] == [VELHO] and "FileNotFoundError" in presas[0][1]


def test_diretorio_que_nao_lista_vira_presa_e_o_main_nao_sai_com_traceback(bruto, monkeypatch):
    def nega(self):
        raise PermissionError(13, "negado")
    monkeypatch.setattr(Path, "iterdir", nega)
    voltaram, presas = oplog.devolver_sobras_do_corte(bruto)
    assert voltaram == [] and presas[0][0] == "(diretorio)"
    codigo, saida, _ = _corta(bruto, ParticaoFalsa(bruto))
    assert codigo == 5, "PermissionError fora do laco do dia sai 5 e nao 1 (que quer dizer reprovado)"


def test_orcamento_que_acaba_no_meio_do_dia_retem_o_dia(tmp_path, monkeypatch):
    import itertools
    pasta = tmp_path / "ops"
    pasta.mkdir()
    _escreve(pasta, VELHO, [json.dumps({"tool": "acervo", "n": i}) for i in range(2500)])
    _escreve(pasta, RECENTE)
    # inicio da rodada, checagem do dia e primeira página a 0 s; na segunda página o relógio já passou do orçamento
    tempos = itertools.chain([0.0, 0.0, 0.0], itertools.repeat(2000.0))
    monkeypatch.setattr(cw.time, "monotonic", lambda: next(tempos))
    api = ParticaoFalsa(pasta, dias=(VELHO, RECENTE))
    codigo, _, poda = _corta(pasta, api)
    assert codigo == 5 and VELHO in _no_disco(pasta)
    assert len([c for c in api.chamadas if c[1].endswith("/eventos")]) == 1
    assert f"corte-bruto {VELHO}: retido — linhagem_indisponivel [5]" in poda.read_text(encoding="utf-8")


@pytest.mark.parametrize("status, codigo_esperado", [(401, 4), (403, 4), (503, 3), (500, 5), (409, 1)])
def test_corpo_de_erro_cortado_segue_a_tabela_de_exit_pelo_status(monkeypatch, status, codigo_esperado):
    import http.client
    import urllib.error
    import urllib.request

    class Corpo:
        def read(self, *a):
            raise http.client.IncompleteRead(b"meio")

        def close(self):
            pass

    def responde(*a, **k):
        raise urllib.error.HTTPError("http://x/", status, "erro", {}, Corpo())
    monkeypatch.setattr(urllib.request, "urlopen", responde)
    from oplog_extracao import Api
    with pytest.raises(Falha) as e:
        Api(base="http://127.0.0.1:1", token="").chamar("GET", "/acervo/log/dias")
    assert e.value.codigo == codigo_esperado
