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
from leitura.resolvedor import ErroResolucao
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
        assert classe in vista_l.alcance_verbo["casa"]
        assert classe in vista_l.alcance_verbo["ontologia"]

    assert "casa" in vista_l.verbos_aceitam_ler
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
        assert len(amb.chamadas) == 1
    finally:
        amb.fechar()
