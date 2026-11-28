# componente: componente:escrita
"""Suíte de contrato do verbo `casa` e da variante `ontologia` (#4470).

Cobre a vista de alcance estática em `registro/vista-alcance.yaml`, a escrita e o ensaio
nas seis capacidades da Olaria sob `casa` e `ontologia`, as recusas `classe-fora-do-verbo`
com `proximo` determinístico, a preservação de `segredo-recusado` (saída 4), a falha fechada
(saída 3) quando o espelho falta ou está corrompido e o despacho do comando `bin/casa`.
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
for caminho in (RAIZ / "lib", RAIZ / "bin"):
    if str(caminho) not in sys.path:
        sys.path.insert(0, str(caminho))

from _olaria import __main__ as olaria_main
from escrita import (
    ContextoEscrita,
    OpcoesExecucao,
    RecusaEscrita,
    executar_ato_escrever,
)
from escrita.moradas.olaria import ConfigOlaria, MoradaOlaria, RespostaHTTP
from escrita.politica import PoliticaEscrita, carregar_politica
from escrita.portao import carregar_vista_alcance as carregar_vista_escrita
from escrita.servidor import ConfigServidor, ServidorEscritor
from leitura.resolvedor import ErroResolucao, resolver_alvo
from leitura.resolvedor import carregar_vista_alcance as carregar_vista_leitura

UUID7_VALIDO = "01960000-0000-7000-8000-000000000042"

AMOSTRAS_SEIS_CAPACIDADES = [
    ("ontologia", "shape", "shape:teste-4470"),
    ("processos", "missao", "missao:mapear-processos-de-capacidade"),
    ("arquitetura", "capacidade", "capacidade:processos"),
    ("norma", "politica", "politica:0001-toda-acao-passa-pela-capacidade-declarada"),
    ("tesauros", "conceito", "conceito:verbo"),
    ("inteligencia", "fenomeno", "fenomeno:sinal-fraco"),
]


@dataclass
class _AmbienteCasa:
    srv: ServidorEscritor
    th: threading.Thread
    sock: Path
    pol: PoliticaEscrita
    chamadas: list[tuple[str, dict[str, Any]]]

    def chamar(self, verbo: str, argv: list[str], entrada: bytes = b"fichas:\n- chave: x\n") -> Any:
        ctx = ContextoEscrita(verbo=verbo, cadeira="engenharia", sujeito="engenharia", sessao_id="s-4470")
        return executar_ato_escrever(
            verbo,
            argv,
            entrada,
            opcoes=OpcoesExecucao(
                contexto=ctx,
                politica=self.pol,
                socket_path=self.sock,
            ),
        )

    def fechar(self) -> None:
        self.srv.parar()
        self.th.join(timeout=5.0)


def _subir_ambiente(tmp_path: Path, *, autorizador: Any = None) -> _AmbienteCasa:
    pol = carregar_politica(RAIZ / "registro" / "escrita.yaml")
    estado = tmp_path / "estado"
    estado.mkdir(parents=True, exist_ok=True)
    sock_path = Path(tempfile.mkdtemp(prefix="pf-casa-")) / "e.sock"
    chamadas: list[tuple[str, dict[str, Any]]] = []

    def _stub(_url: str, rota: str, _hdrs: dict, corpo: dict, _timeout: float) -> RespostaHTTP:
        chamadas.append((rota, corpo))
        payload: dict[str, Any] = (
            {"ok": True, "ensaiado": True, "erros": []}
            if rota == "/ensaiar"
            else {"ok": True, "fornada": corpo.get("fornada", UUID7_VALIDO), "versao": UUID7_VALIDO, "gravado": True}
        )
        return RespostaHTTP(200, payload)

    cfg = ConfigServidor(
        socket_path=sock_path,
        raiz_bancadas=tmp_path,
        estado_dir=estado,
        politica=pol,
        vista=carregar_vista_escrita(),
        moradas={"banco": MoradaOlaria(ConfigOlaria(url="http://127.0.0.1:19997", chave="k-4470"), transporte=_stub)},
        grupo_autorizado="",
        uid_escritor=os.getuid(),
        autorizador_sujeito=autorizador or (lambda _s, _c, _v, _f: True),
    )
    srv = ServidorEscritor(cfg)
    th = threading.Thread(target=srv.servir, kwargs={"instalar_sinais": False}, daemon=True)
    th.start()
    espera = threading.Event()
    for _ in range(500):
        if sock_path.exists():
            break
        espera.wait(0.01)
    assert sock_path.exists()
    return _AmbienteCasa(srv=srv, th=th, sock=sock_path, pol=pol, chamadas=chamadas)


def test_espelho_vista_alcance_cobre_seis_capacidades_e_sem_fossil() -> None:
    vista_e = carregar_vista_escrita()
    vista_l = carregar_vista_leitura()

    assert "casa" in vista_e.verbos
    assert "ontologia" in vista_e.verbos
    assert vista_e.verbos["casa"].aceita_escrever is True
    assert vista_e.verbos["ontologia"].aceita_escrever is True
    assert vista_e.verbos["casa"].classes == vista_e.verbos["ontologia"].classes
    assert "cadeira" not in vista_e.classes

    for _cap, classe, _chave in AMOSTRAS_SEIS_CAPACIDADES:
        assert classe in vista_e.verbos["casa"].classes
        assert vista_e.verbo_dono(classe) == "casa"
        assert classe in vista_l.alcance_verbo["ontologia"]
        assert vista_l.classes[classe].verbo_dono == "busca"

    assert "casa" not in vista_l.verbos_aceitam_ler
    assert "casa" not in vista_l.alcance_verbo
    assert "ontologia" in vista_l.verbos_aceitam_ler


def test_vista_alcance_ausente_ou_corrompida_falha_fechado_saida_3(tmp_path: Path) -> None:
    ausente = tmp_path / "nao-existe.yaml"
    with pytest.raises(RecusaEscrita) as exc_e:
        carregar_vista_escrita(caminho_vista_yaml=ausente)
    assert exc_e.value.saida == 3
    assert exc_e.value.primeiro.codigo == "politica-indisponivel"

    with pytest.raises(ErroResolucao) as exc_l:
        carregar_vista_leitura(caminho_vista_yaml=ausente)
    assert exc_l.value.saida == 3
    assert exc_l.value.recusa.codigo == "politica-indisponivel"

    corrompido = tmp_path / "corrompido.yaml"
    corrompido.write_text("versao: [quebrado\n", encoding="utf-8")
    with pytest.raises(RecusaEscrita) as exc_c:
        carregar_vista_escrita(caminho_vista_yaml=corrompido)
    assert exc_c.value.saida == 3
    assert exc_c.value.primeiro.codigo == "politica-indisponivel"


@pytest.mark.parametrize("verbo", ["casa", "ontologia"])
@pytest.mark.parametrize(("capacidade", "classe", "chave"), AMOSTRAS_SEIS_CAPACIDADES)
def test_escrita_e_ensaio_seis_capacidades_aceitos(
    tmp_path: Path, verbo: str, capacidade: str, classe: str, chave: str
) -> None:
    amb = _subir_ambiente(tmp_path / f"{verbo}_{capacidade}")
    try:
        res_criar = amb.chamar(verbo, ["criar", classe, chave])
        assert res_criar.versao == UUID7_VALIDO

        res_trocar = amb.chamar(verbo, ["trocar", classe, chave, UUID7_VALIDO])
        assert res_trocar.versao == UUID7_VALIDO

        res_ensaiar = amb.chamar(verbo, ["ensaiar", "trocar", classe, chave, UUID7_VALIDO])
        assert res_ensaiar.forma == "ensaiar"
        assert res_ensaiar.alterou is False

        assert len(amb.chamadas) == 3
    finally:
        amb.fechar()


@pytest.mark.parametrize("verbo", ["casa", "ontologia"])
@pytest.mark.parametrize(
    ("classe", "chave", "verbo_dono"),
    [
        ("componente", "platafirma-harness@4470:README.md", "repo"),
        ("card", "card:4470", "tarefas"),
        ("story", "story:4470", "tarefas"),
    ],
)
def test_recusa_classe_fora_do_verbo_com_verbo_dono_em_proximo(
    tmp_path: Path, verbo: str, classe: str, chave: str, verbo_dono: str
) -> None:
    amb = _subir_ambiente(tmp_path / f"recusa_{verbo}_{classe}")
    try:
        with pytest.raises(RecusaEscrita) as exc:
            amb.chamar(verbo, ["criar", classe, chave])
        assert exc.value.saida == 1
        assert exc.value.primeiro.codigo == "classe-fora-do-verbo"
        assert exc.value.primeiro.proximo.startswith(f"{verbo_dono} ")
        assert amb.chamadas == []
    finally:
        amb.fechar()


@pytest.mark.parametrize("verbo", ["casa", "ontologia"])
def test_travas_segredo_e_autorizacao_preservadas(tmp_path: Path, verbo: str) -> None:
    amb_seg = _subir_ambiente(tmp_path / f"trava_seg_{verbo}")
    try:
        with pytest.raises(RecusaEscrita) as exc_seg:
            amb_seg.chamar(verbo, ["criar", "segredo", "segredo:cofre/x"])
        assert exc_seg.value.saida == 4
        assert exc_seg.value.primeiro.codigo == "segredo-recusado"
        assert amb_seg.chamadas == []
    finally:
        amb_seg.fechar()

    amb_neg = _subir_ambiente(
        tmp_path / f"trava_auth_{verbo}",
        autorizador=lambda _s, _c, _v, _f: False,
    )
    try:
        with pytest.raises(RecusaEscrita) as exc_auth:
            amb_neg.chamar(verbo, ["criar", "missao", "missao:teste"])
        assert exc_auth.value.saida == 4
        assert exc_auth.value.primeiro.codigo == "acesso-negado"
        assert amb_neg.chamadas == []
    finally:
        amb_neg.fechar()


def test_comando_bin_casa_encaminha_ao_escritor_unico_e_valida_uuid7(tmp_path: Path) -> None:
    amb = _subir_ambiente(tmp_path / "cli_casa")
    arq_yaml = tmp_path / "missao.yaml"
    arq_yaml.write_text("fichas:\n- chave: missao:mapear-processos-de-capacidade\n", encoding="utf-8")
    env = {
        "PF_ESCRITA_CONFIG": str(RAIZ / "registro" / "escrita.yaml"),
        "PF_ESCRITOR_SOCKET": str(amb.sock),
        "PF_CADEIRA": "engenharia",
        "PF_SUJEITO": "engenharia",
        "PF_SESSAO": "sessao-4470",
    }
    try:
        saida_ok = olaria_main.executar(
            ["trocar", "missao", "missao:mapear-processos-de-capacidade", UUID7_VALIDO, str(arq_yaml)],
            env=env,
            prog="casa",
        )
        assert saida_ok.codigo == 0
        assert len(amb.chamadas) == 1

        saida_versao_ruim = olaria_main.executar(
            ["trocar", "missao", "missao:mapear-processos-de-capacidade", "nao-e-uuid7", str(arq_yaml)],
            env=env,
            prog="casa",
        )
        assert saida_versao_ruim.codigo == 2
        assert "versao-invalida" in saida_versao_ruim.stdout
        assert "busca ler missao:mapear-processos-de-capacidade" in saida_versao_ruim.stdout
        assert len(amb.chamadas) == 1
    finally:
        amb.fechar()


def test_casa_nao_expoe_leitura_no_resolvedor_nem_na_cli() -> None:
    with pytest.raises(ErroResolucao) as exc:
        resolver_alvo("casa", "missao:mapear-processos-de-capacidade")
    assert exc.value.saida == 2
    assert exc.value.recusa.codigo == "ato-nao-aceito"
    assert exc.value.recusa.proximo == "busca ler missao:mapear-processos-de-capacidade"

    for argv, esperado in [
        (["ler", "missao", "missao:mapear-processos-de-capacidade"], "busca ler missao:mapear-processos-de-capacidade"),
        (["listar", "shape"], "busca listar shape"),
        (["preparar", "missao", "missao:mapear-processos-de-capacidade"], "busca ler missao:mapear-processos-de-capacidade"),
    ]:
        saida = olaria_main.executar(argv, env={}, prog="casa")
        assert saida.codigo == 2
        assert "ato-recusado" in saida.stdout
        assert esperado in saida.stdout

    ajuda = olaria_main.executar(["--help"], env={}, prog="casa")
    assert ajuda.codigo == 0
    assert "casa criar" in ajuda.stdout
    assert "busca ler" in ajuda.stdout
    assert "casa ler " not in ajuda.stdout
    assert "casa listar " not in ajuda.stdout


def test_porta_yaml_casa_sem_leitura_e_ontologia_oculta() -> None:
    dados = yaml.safe_load((RAIZ / "registro" / "porta.yaml").read_text(encoding="utf-8"))
    verbos = dados["verbos"]
    desc_casa = str(verbos["casa"]["descricao"])
    assert "não lê" in desc_casa
    assert "ler (leitura, casa)" not in desc_casa
    assert "listar (leitura, casa)" not in desc_casa
    assert verbos["ontologia"].get("modelo") is False


@dataclass(frozen=True)
class _CasoLoteFora:
    argv: list[str]
    conteudo_yaml: str
    proximo_prefixo: str


@pytest.mark.parametrize("prog", ["casa", "ontologia"])
@pytest.mark.parametrize("argv_base", [["ensaiar", "criar", "-"], ["criar", "-"]])
def test_lote_yaml_segredo_recusado_pelo_despachante(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prog: str, argv_base: list[str]
) -> None:
    import io
    import json

    amb = _subir_ambiente(tmp_path / f"lote_seg_{prog}_{argv_base[0]}")
    env = {
        "PF_ESCRITA_CONFIG": str(RAIZ / "registro" / "escrita.yaml"),
        "PF_ESCRITOR_SOCKET": str(amb.sock),
        "PF_CADEIRA": "engenharia",
        "PF_SUJEITO": "engenharia",
        "PF_SESSAO": "sessao-4470",
    }
    conteudo = "fichas:\n- classe: segredo\n  chave: segredo:sonda-homologacao-4470\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(conteudo))
    try:
        saida = olaria_main.executar(argv_base, env=env, prog=prog)
        assert saida.codigo == 4
        payload = json.loads(saida.stderr.strip().splitlines()[-1])
        assert payload["erro"]["codigo"] == "segredo-recusado"
        assert amb.chamadas == []
    finally:
        amb.fechar()


@pytest.mark.parametrize("prog", ["casa", "ontologia"])
@pytest.mark.parametrize(
    "caso",
    [
        _CasoLoteFora(
            ["ensaiar", "criar", "-"],
            "fichas:\n- classe: componente\n  chave: componente:sonda-homologacao-4470\n",
            "repo ",
        ),
        _CasoLoteFora(
            ["ensaiar", "criar", "-"],
            "fichas:\n- classe: story\n  chave: story:sonda-homologacao-4470\n",
            "tarefas ",
        ),
        _CasoLoteFora(
            ["criar", "-"],
            "fichas:\n- classe: componente\n  chave: componente:sonda-homologacao-4470\n",
            "repo ",
        ),
        _CasoLoteFora(
            ["trocar", "-"],
            f"fichas:\n- classe: story\n  chave: story:sonda-homologacao-4470\n  versao: {UUID7_VALIDO}\n",
            "tarefas ",
        ),
    ],
)
def test_lote_yaml_classe_fora_do_verbo_pelo_despachante(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prog: str, caso: _CasoLoteFora
) -> None:
    import io
    import json

    amb = _subir_ambiente(tmp_path / f"lote_fora_{prog}_{caso.argv[0]}")
    env = {
        "PF_ESCRITA_CONFIG": str(RAIZ / "registro" / "escrita.yaml"),
        "PF_ESCRITOR_SOCKET": str(amb.sock),
        "PF_CADEIRA": "engenharia",
        "PF_SUJEITO": "engenharia",
        "PF_SESSAO": "sessao-4470",
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(caso.conteudo_yaml))
    try:
        saida = olaria_main.executar(caso.argv, env=env, prog=prog)
        assert saida.codigo == 1
        payload = json.loads(saida.stderr.strip().splitlines()[-1])
        assert payload["erro"]["codigo"] == "classe-fora-do-verbo"
        assert payload["erro"]["proximo"].startswith(caso.proximo_prefixo)
        assert amb.chamadas == []
    finally:
        amb.fechar()


def test_lote_yaml_misto_e_autorizacao_pelo_despachante(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io
    import json

    amb = _subir_ambiente(tmp_path / "lote_misto")
    env = {
        "PF_ESCRITA_CONFIG": str(RAIZ / "registro" / "escrita.yaml"),
        "PF_ESCRITOR_SOCKET": str(amb.sock),
        "PF_CADEIRA": "engenharia",
        "PF_SUJEITO": "engenharia",
        "PF_SESSAO": "sessao-4470",
    }
    try:
        yaml_misto_seg = (
            "fichas:\n"
            "- classe: missao\n"
            "  chave: missao:valida-4470\n"
            "- classe: segredo\n"
            "  chave: segredo:sonda-4470\n"
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO(yaml_misto_seg))
        s_seg = olaria_main.executar(["ensaiar", "criar", "-"], env=env, prog="casa")
        assert s_seg.codigo == 4
        assert json.loads(s_seg.stderr.strip().splitlines()[-1])["erro"]["codigo"] == "segredo-recusado"
        assert amb.chamadas == []

        yaml_misto_comp = (
            "fichas:\n"
            "- classe: missao\n"
            "  chave: missao:valida-4470\n"
            "- classe: componente\n"
            "  chave: componente:sonda-4470\n"
        )
        monkeypatch.setattr(sys, "stdin", io.StringIO(yaml_misto_comp))
        s_comp = olaria_main.executar(["ensaiar", "criar", "-"], env=env, prog="casa")
        assert s_comp.codigo == 1
        erro_comp = json.loads(s_comp.stderr.strip().splitlines()[-1])["erro"]
        assert erro_comp["codigo"] == "classe-fora-do-verbo"
        assert erro_comp["proximo"].startswith("repo ")
        assert amb.chamadas == []

        yaml_valido = "fichas:\n- classe: missao\n  chave: missao:valida-4470\n"
        monkeypatch.setattr(sys, "stdin", io.StringIO(yaml_valido))
        s_ok = olaria_main.executar(["ensaiar", "criar", "-"], env=env, prog="casa")
        assert s_ok.codigo == 0
        assert len(amb.chamadas) == 1
    finally:
        amb.fechar()

    amb_neg = _subir_ambiente(
        tmp_path / "lote_auth_neg",
        autorizador=lambda _s, _c, _v, _f: False,
    )
    env_neg = {**env, "PF_ESCRITOR_SOCKET": str(amb_neg.sock)}
    monkeypatch.setattr(sys, "stdin", io.StringIO("fichas:\n- classe: missao\n  chave: missao:valida-4470\n"))
    try:
        s_neg = olaria_main.executar(["ensaiar", "criar", "-"], env=env_neg, prog="casa")
        assert s_neg.codigo == 4
        assert json.loads(s_neg.stderr.strip().splitlines()[-1])["erro"]["codigo"] == "acesso-negado"
        assert amb_neg.chamadas == []
    finally:
        amb_neg.fechar()


@pytest.mark.parametrize(
    "classe",
    ["levantamento", "benchmark", "fichamento", "incerteza", "medicao", "parecer", "resenha"],
)
@pytest.mark.parametrize("prog", ["casa", "ontologia"])
def test_casa_alcanca_levantamento_e_filhas_de_observacao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prog: str, classe: str
) -> None:
    """DT 1445: levantamento (capacidade:dados) e demais filhas de observacao são alcançadas por casa/ontologia."""
    import io

    amb = _subir_ambiente(tmp_path / f"obs_{prog}_{classe}")
    env = {
        "PF_ESCRITA_CONFIG": str(RAIZ / "registro" / "escrita.yaml"),
        "PF_ESCRITOR_SOCKET": str(amb.sock),
        "PF_CADEIRA": "engenharia",
        "PF_SUJEITO": "engenharia",
        "PF_SESSAO": "sessao-dt1445",
    }
    conteudo = f"fichas:\n- classe: {classe}\n  chave: {classe}:2026-11-28-teste\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(conteudo))
    try:
        saida = olaria_main.executar(["ensaiar", "criar", "-"], env=env, prog=prog)
        assert saida.codigo == 0, saida.stderr
        assert len(amb.chamadas) == 1
    finally:
        amb.fechar()
