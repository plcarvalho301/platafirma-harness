# componente: componente:poda
"""Testes do aviso de corte, continuação por offset e metadados da poda (`t4`)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from poda.poda import (
    CAP_PADRAO,
    OpcoesAvisoCorte,
    corta,
    linha_humana,
    podar_envelope,
    podar_texto,
)


def _criar_verbo_falso(
    caminho: Path, *, forma: str, poda: str = "inteira", cauda: bool = False
) -> Path:
    cab = [
        "#!/usr/bin/env bash",
        f"# forma: {forma}",
        f"# poda: {poda}",
        f"# cauda: {'sim' if cauda else 'nao'}",
    ]
    caminho.write_text("\n".join(cab) + "\n", encoding="utf-8")
    caminho.chmod(0o755)
    return caminho


def test_cap_padrao_64_kib() -> None:
    assert CAP_PADRAO == 64 * 1024


def test_corte_listagem_leitura_e_json_campos_e_ordem_dos_passos(tmp_path: Path) -> None:
    verbo_list = _criar_verbo_falso(tmp_path / "verbo-list", forma="listagem")
    linhas_list = "".join(f"item-{i:04d}: registro de listagem extenso\n" for i in range(60))
    cap = 900
    env_list = podar_envelope(
        {
            "exit_code": 0,
            "stdout": {
                "texto": linhas_list,
                "truncado": False,
                "bytes_total": len(linhas_list.encode()),
            },
        },
        verbo="verbo-list",
        argv=["verbo-list", "listar"],
        binario=verbo_list,
        sessao_id="sessao-aviso",
        alca="verbo-list listar",
        derrame_dir=tmp_path / "derrames",
        cap=cap,
    )
    meta_l = env_list["poda"]
    assert meta_l["modo"] == "corte"
    assert meta_l["forma"] == "listagem"
    assert meta_l["linhas_total"] == 60
    assert len(env_list["stdout"]["texto"].encode("utf-8")) <= cap

    faltam_l = meta_l["bytes_omitidos"]
    tokens_l = faltam_l // 4
    for superficie in (env_list["stdout"]["texto"], env_list["poda_aviso"], env_list["aviso"]):
        assert f"{meta_l['bytes_produzidos']} bytes no total" in superficie
        assert f"faltam {faltam_l} bytes (~{tokens_l} tokens)" in superficie
        assert "linhas fora" in superficie
        p1 = superficie.index("(1) refaça a chamada mais estreita")
        p2 = superficie.index("(2) recorte com")
        p3 = superficie.index("(3) próxima página com")
        assert p1 < p2 < p3

    verbo_ler = _criar_verbo_falso(tmp_path / "verbo-ler", forma="relatorio", poda="constitutiva")
    texto_ler = "".join(
        f"Parágrafo {i:03d} de documento longo para leitura contínua.\n" for i in range(60)
    )
    env_ler = podar_envelope(
        {
            "exit_code": 0,
            "stdout": {
                "texto": texto_ler,
                "truncado": False,
                "bytes_total": len(texto_ler.encode()),
            },
        },
        verbo="verbo-ler",
        argv=["verbo-ler", "ler", "doc"],
        binario=verbo_ler,
        sessao_id="sessao-aviso",
        alca="verbo-ler ler doc",
        derrame_dir=tmp_path / "derrames",
        cap=cap,
    )
    assert len(env_ler["stdout"]["texto"].encode("utf-8")) <= cap
    assert env_ler["poda"]["forma"] == "relatorio"
    assert env_ler["poda"]["linhas_total"] == 60
    for superficie in (env_ler["stdout"]["texto"], env_ler["poda_aviso"], env_ler["aviso"]):
        assert "leitura incompleta:" in superficie
        assert "linhas fora" not in superficie
        p1 = superficie.index("(1) próxima página com")
        p2 = superficie.index("(2) pedaço por linhas com")
        assert p1 < p2

    verbo_json = _criar_verbo_falso(tmp_path / "verbo-json", forma="json")
    corpo_json = json.dumps(
        {"itens": [{"id": i, "valor": f"bloco-{i:04d}"} for i in range(60)]}, ensure_ascii=False
    )
    env_json = podar_envelope(
        {
            "exit_code": 0,
            "stdout": {
                "texto": corpo_json,
                "truncado": False,
                "bytes_total": len(corpo_json.encode()),
            },
        },
        verbo="verbo-json",
        argv=["verbo-json", "consultar"],
        binario=verbo_json,
        sessao_id="sessao-aviso",
        alca="verbo-json consultar",
        derrame_dir=tmp_path / "derrames",
        cap=cap,
    )
    assert len(env_json["stdout"]["texto"].encode("utf-8")) <= cap
    assert env_json["poda"]["forma"] == "json"
    assert env_json["poda"]["linhas_total"] == 1
    for superficie in (env_json["stdout"]["texto"], env_json["poda_aviso"], env_json["aviso"]):
        assert "fragmento de JSON" in superficie
        p1 = superficie.index("(1) refaça a chamada mais estreita")
        p2 = superficie.index("(2) recorte com")
        p3 = superficie.index("(3) próxima página com")
        assert p1 < p2 < p3


def test_cauda_sem_lavagem_leva_offset_do_fim_da_cabeca(tmp_path: Path) -> None:
    texto = "".join(f"evento-{i:04d}-ok\n" for i in range(100))
    cap = 900
    servido, meta = podar_texto(
        texto,
        tool="teste",
        alca="teste rodar alvo",
        sessao_id="sessao-cauda",
        derrame_dir=tmp_path,
        cap=cap,
        cauda=True,
        forma="log",
    )
    assert meta["lavado"] == []
    assert meta["modo"] == "corte"
    assert len(servido.encode("utf-8")) <= cap
    assert servido.endswith("evento-0099-ok\n")

    cabeca = servido.split("\n[corte no teto:", 1)[0]
    bytes_cabeca = len(cabeca.encode("utf-8"))
    assert bytes_cabeca > 0
    assert meta["offset_continuacao"] == bytes_cabeca
    assert f"offset={bytes_cabeca}" in meta["como_ler"]


def test_lavagem_acima_do_teto_sai_sem_offset_e_avisa_recomeco_do_zero(tmp_path: Path) -> None:
    verbo_ansi = _criar_verbo_falso(tmp_path / "verbo-ansi", forma="listagem")
    texto_ansi = "".join(
        f"\x1b[32mlinha-{i:04d}\x1b[0m detalhe longo da listagem\n" for i in range(80)
    )
    env = podar_envelope(
        {
            "exit_code": 0,
            "stdout": {
                "texto": texto_ansi,
                "truncado": False,
                "bytes_total": len(texto_ansi.encode()),
            },
        },
        verbo="verbo-ansi",
        argv=["verbo-ansi", "listar"],
        binario=verbo_ansi,
        sessao_id="sessao-lavada",
        alca="verbo-ansi listar",
        derrame_dir=tmp_path / "derrames",
        cap=950,
    )
    assert "ansi" in env["poda"]["lavado"]
    assert env["poda"]["modo"] == "corte"
    assert "offset=" not in env["como_ler"]
    assert len(env["stdout"]["texto"].encode("utf-8")) <= 950
    for superficie in (env["stdout"]["texto"], env["poda_aviso"], env["aviso"]):
        assert "começa do zero" in superficie


def test_modo_derrame_abaixo_do_teto_mantem_linha_de_hoje_e_sem_sessao_pede_sessao(
    tmp_path: Path,
) -> None:
    aviso_derrame = linha_humana({"modo": "derrame", "alca": "retorno:s1:0"})
    assert aviso_derrame == "poda: retorno semântico inteiro, sem corte — cru em retorno:s1:0"

    repetido = ("linha repetida igual\n" * 10) + "resumo final\n"
    servido_rep, meta_rep = podar_texto(
        repetido,
        tool="verbo",
        alca="verbo listar",
        sessao_id="sessao-curta",
        derrame_dir=tmp_path,
        cap=4096,
    )
    assert meta_rep.get("modo") != "corte"
    assert "linhas idênticas omitidas" in servido_rep
    assert linha_humana(meta_rep) == "poda: lavado (repeticao)"

    verbo_list = _criar_verbo_falso(tmp_path / "verbo-sem", forma="listagem")
    grande = "".join(f"item-{i:04d}: linha sem sessao\n" for i in range(80))
    env_sem = podar_envelope(
        {
            "exit_code": 0,
            "stdout": {
                "texto": grande,
                "truncado": False,
                "bytes_total": len(grande.encode()),
            },
        },
        verbo="verbo-sem",
        argv=["verbo-sem", "listar"],
        binario=verbo_list,
        sessao_id="-",
        alca="verbo-sem listar",
        derrame_dir=tmp_path / "derrames",
        cap=800,
    )
    assert "como_ler" not in env_sem
    assert "cru" not in env_sem["stdout"]
    assert len(env_sem["stdout"]["texto"].encode("utf-8")) <= 800
    for superficie in (env_sem["stdout"]["texto"], env_sem["poda_aviso"], env_sem["aviso"]):
        assert "pede sessão aberta" in superficie
        assert "ler_arquivo(" not in superficie

    servido_sf, _ = corta(
        grande,
        800,
        alca="retorno:s1:2",
        opcoes=OpcoesAvisoCorte(forma="listagem", tem_filtro=False),
    )
    assert "refaça a chamada mais estreita" not in servido_sf
    assert "(1) recorte com" in servido_sf
