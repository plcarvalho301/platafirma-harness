"""Todo repositorio de codigo tem teste que o `teste rodar` alcanca, ou diz por que nao (card #3535).

O rastreador ficou meses com self-check que nenhum verbo rodava: estava em `repositorios` do
registro sem chave de venv, e cada story que mexia no codigo dele subia sem teste e ia provada a
mao no ar. Este teste le o registro real e reprova o repositorio de esteira `codigo` que nao tem
nenhuma chave com subarvore de teste e nao declara `teste_fora` com o motivo.

Prova: o registro declara, para cada repositorio de codigo, onde mora a suite ou por que ela nao
existe; a chave com `teste` tem a lista de portao no lugar que o `teste rodar --portao` le.
Nao prova: que a suite passe nem que a lista exista na arvore do outro repositorio (isso e o
`teste rodar <repo> --portao`, que sai 5 com lista ausente).
"""
import json
import subprocess
from pathlib import Path

REGISTRO = Path(__file__).resolve().parents[2] / "registro" / "venvs.json"
RELEASE = Path(__file__).resolve().parents[2] / "bin" / "release"


def _registro():
    dados = json.loads(REGISTRO.read_text(encoding="utf-8"))
    repos = dados.get("repositorios") or {}
    stacks = {k: v for k, v in dados.items() if not k.startswith("_") and k != "repositorios"}
    return repos, stacks


def faltando(repos, stacks):
    """Repositorios de codigo sem chave com 'teste' e sem 'teste_fora' declarado."""
    com_teste = {d.get("familia") for d in stacks.values() if isinstance(d, dict) and d.get("teste")}
    return sorted(
        nome for nome, decl in repos.items()
        if (decl or {}).get("esteira", "codigo") == "codigo"
        and nome not in com_teste
        and not str((decl or {}).get("teste_fora") or "").strip()
    )


def test_todo_repositorio_de_codigo_tem_chave_de_teste_ou_declara_fora():
    repos, stacks = _registro()
    falta = faltando(repos, stacks)
    assert not falta, (
        f"repositorio de codigo sem teste alcancavel: {falta} — de a ele uma chave com 'teste' em "
        "registro/venvs.json (lock e lista de portao na subarvore), ou declare 'teste_fora' com o motivo e o debito"
    )


def test_quem_tem_chave_nao_declara_fora():
    # as duas coisas juntas sao contradicao: o fora vira mentira assim que a chave entra
    repos, stacks = _registro()
    com_teste = {d.get("familia") for d in stacks.values() if isinstance(d, dict) and d.get("teste")}
    assert not sorted(n for n, d in repos.items() if n in com_teste and (d or {}).get("teste_fora"))


def test_o_detector_pega_o_caso_do_rastreador():
    # o estado de antes do #3535: repositorio de codigo, sem chave e sem motivo
    repos = {"platafirma-rastreador": {"esteira": "codigo"}, "platafirma-casa": {"esteira": "documento"}}
    stacks = {"rastreador-tela": {"familia": "platafirma-ui", "lock": "x/package-lock.json"}}
    assert faltando(repos, stacks) == ["platafirma-rastreador"]
    stacks["rastreador"] = {"familia": "platafirma-rastreador", "lock": "api/requirements-teste.txt", "teste": "api"}
    assert faltando(repos, stacks) == []
    repos["platafirma-core"] = {"esteira": "codigo", "teste_fora": "  "}
    assert faltando(repos, stacks) == ["platafirma-core"], "motivo em branco nao e motivo"


def _declarado(tmp_path, repos, repo):
    # a funcao de bin/release, isolada: o promover so confere no ar com o conferir da release
    # a familia que o registro declara (#3535); core e conhecimento sairiam vermelhos e voltariam
    venvs = tmp_path / "venvs.json"
    venvs.write_text(json.dumps({"repositorios": repos}), encoding="utf-8")
    script = f"source <(sed -n '/^conferir_no_ar_declarado()/,/^}}/p' '{RELEASE}'); conferir_no_ar_declarado '{repo}'"
    return subprocess.run(["bash", "-c", script], env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(venvs)},
                          capture_output=True, text=True).returncode


def test_conferir_no_ar_so_com_true_declarado(tmp_path):
    repos = {"platafirma-rastreador": {"esteira": "codigo", "conferir_no_ar": True},
             "platafirma-core": {"esteira": "codigo"},
             "platafirma-motor": {"esteira": "codigo", "conferir_no_ar": "sim"}}
    assert _declarado(tmp_path, repos, "platafirma-rastreador") == 0
    assert _declarado(tmp_path, repos, "platafirma-core") == 1
    assert _declarado(tmp_path, repos, "platafirma-motor") == 1, "so o booleano true liga"
    assert _declarado(tmp_path, repos, "nao-existe") == 1


def test_registro_real_liga_a_conferencia_so_no_rastreador():
    repos, _ = _registro()
    assert sorted(n for n, d in repos.items() if (d or {}).get("conferir_no_ar") is True) == ["platafirma-rastreador"]
