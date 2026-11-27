# componente: componente:abertura
"""Contrato do ato `python -m abertura tronco` (F4073, r30)."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_LIB = REPO_ROOT / "lib"


def _criar_infra_fake(tmp_path: Path) -> Path:
    script = tmp_path / "infra-fake"
    script.write_text(
        f"""#!{sys.executable}
import json, sys
args = sys.argv[1:]
if "--" in args:
    args = args[args.index("--") + 1:]
if args[:3] == ["listar", "shape", "--filhas"]:
    print(json.dumps({{"chaves": ["missao", "procedimento"]}}))
elif args[:2] == ["ler", "processo"]:
    print(json.dumps({{"yaml": ""}}))
elif args[:2] == ["ler", "missao"]:
    print(json.dumps({{"yaml": "- chave: missao:executar-a-story-de-codigo\\n  conduz:\\n    - story:em-execucao\\n"}}))
elif args[:2] == ["ler", "procedimento"]:
    print(json.dumps({{"yaml": "- chave: procedimento:homologar-e-entregar-um-pai\\n  conduz: feature:em-homologacao\\n"}}))
elif args[:3] == ["ler", "shape", "procedimento"]:
    print(json.dumps({{"yaml": "  golden:\\n    endereco: instancias/procedimento/<slug>.md\\n"}}))
elif args[:3] == ["ler", "shape", "missao"]:
    print(json.dumps({{"yaml": "  golden:\\n    endereco: instancias/missao/<slug>.md\\n"}}))
else:
    print(json.dumps({{}}))
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _rodar_tronco(payload: dict, infra_fake: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(HARNESS_LIB)
    env["PF_INFRA_BIN"] = str(infra_fake)
    proc = subprocess.run(
        [sys.executable, "-m", "abertura", "tronco"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_tronco_resolve_procedimento_e_missao(tmp_path: Path) -> None:
    infra = _criar_infra_fake(tmp_path)

    res_feat = _rodar_tronco(
        {"card": {"id": 4073, "nivel_nome": "feature", "estado_mostrado": "em-homologacao", "decisao_aposta": 5255}, "chapeu": "interfaces"},
        infra,
    )
    assert res_feat["sem_processo"] is False
    assert res_feat["processo"] == "procedimento:homologar-e-entregar-um-pai"
    assert res_feat["passo"] == "em-homologacao"
    assert res_feat["documento"] == "instancias/procedimento/homologar-e-entregar-um-pai.md"
    assert res_feat["aposta_fechada"] is True

    res_story = _rodar_tronco(
        {"card": {"id": 4393, "nivel": 2, "estado": "em-execucao"}, "chapeu": "back-end"},
        infra,
    )
    assert res_story["sem_processo"] is False
    assert res_story["processo"] == "missao:executar-a-story-de-codigo"
    assert res_story["passo"] == "em-execucao"


def test_tronco_sem_processo_quando_estagio_nao_conduzido(tmp_path: Path) -> None:
    infra = _criar_infra_fake(tmp_path)
    res = _rodar_tronco(
        {"card": {"id": 9999, "nivel_nome": "ideia", "estado": "captada"}, "chapeu": "interfaces"},
        infra,
    )
    assert res == {"processo": None, "passo": None, "sem_processo": True}


def test_carregar_secao_das_cadeiras_usa_platafirma_release_sem_pf_casa_raiz(
    tmp_path: Path, monkeypatch
) -> None:
    sys.path.insert(0, str(HARNESS_LIB))
    from abertura.nomes import carregar_secao_das_cadeiras, resolver

    personas_dir = tmp_path / "release" / "casa" / "instancias" / "persona"
    personas_dir.mkdir(parents=True)
    (personas_dir / "seguranca.md").write_text(
        "# Leonardo Tartaruga\n\n## Nomes\n"
        "- cadeira **seguranca**: Leonardo Tartaruga, Segurança\n"
        "- chapéu **iam**: acesso, controles\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("PF_CASA_RAIZ", raising=False)
    monkeypatch.delenv("PF_NOMES_FIXTURE", raising=False)
    monkeypatch.delenv("PF_SECAO_CADEIRAS", raising=False)
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(tmp_path / "release"))

    secao = carregar_secao_das_cadeiras()
    assert "seguranca" in secao.cadeiras
    res = resolver("seguranca", "iam", secao=secao)
    assert res.ok is True
    assert res.cadeira == "seguranca"
    assert res.chapeu == "iam"
