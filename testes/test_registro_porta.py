"""O registro da porta (registro/porta.yaml, card #4117): o esquema, o conteudo e o que ele promete a quem o le.

Hermetico: le o arquivo do repositorio e o cabecalho dos verbos, sem banco e sem porta no ar. O que a porta faz com
o registro (tools/list sem as ocultas, tools/call da oculta, retencao, degradacao) tem os testes em
ops-server/ (test_contrato_borda.py e _ensaio.py), no venv `ops`.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
import registro_porta as rp  # noqa: E402

REGISTRO = REPO_ROOT / "registro" / "porta.yaml"
FORA_DA_LISTA = {"chat", "minuta", "persona", "preferencia", "sinal", "situacao", "sessao"}


@pytest.fixture(scope="module")
def registro():
    return rp.carrega(REGISTRO)


def _grava(tmp_path, texto):
    arq = tmp_path / "porta.yaml"
    arq.write_text(texto, encoding="utf-8")
    return arq


def test_o_modelo_nao_ve_chat_minuta_persona_preferencia_sinal_situacao_e_sessao_mas_ve_o_metrica(registro):
    vistos = set(rp.visiveis(registro))
    assert not (vistos & FORA_DA_LISTA)
    assert "metrica" in vistos
    # chat, minuta, persona, sinal e situacao saem do registro: a porta nao os executa nem pelo malote
    assert not ({"chat", "minuta", "persona", "sinal", "situacao"} & set(registro["verbos"]))
    # preferencia e sessao ficam executaveis, fora da lista (decisao do dono, comentario 4402)
    for oculto in ("preferencia", "sessao"):
        assert oculto in registro["verbos"] and registro["verbos"][oculto]["modelo"] is False


def test_repo_e_o_unico_retido(registro):
    assert rp.retidos(registro) == {"repo"}


def test_as_tools_de_transporte_sao_as_do_codigo_da_porta(registro):
    """A porta registra as tools de transporte que o codigo define; o registro as nomeia. As duas listas dizem o
    mesmo, e run_command e read_file nao estao em nenhuma."""
    codigo = (REPO_ROOT / "ops-server" / "server.py").read_text(encoding="utf-8")
    lista = re.search(r"^_TOOLS = \[([^\]]+)\]$", codigo, re.M).group(1)
    nomes = [n.strip() for n in lista.split(",")]
    assert re.search(r"^\s+_TOOLS\.append\(monta_sessao\)$", codigo, re.M)
    assert sorted(registro["transporte"]) == sorted([*nomes, "monta_sessao"])
    assert not ({"run_command", "read_file"} & set(registro["transporte"]))


def test_as_faces_da_borda_saem_do_registro(registro):
    faces = {}
    for slug, v in registro["verbos"].items():
        for face in v["faces"]:
            faces.setdefault(face, []).append(slug)
    assert sorted(faces) == ["casca", "motor"]
    assert sorted(faces["casca"]) == ["preferencia", "release", "tarefas"]
    assert sorted(faces["motor"]) == ["fila", "motor"]
    assert registro["verbos"]["motor"]["faces"]["motor"] == {"instancia": "rag", "sem_instancia": ["listar"]}


def test_todo_verbo_do_registro_tem_bin_executavel_com_a_abertura_e_o_use_para(registro):
    for slug in registro["verbos"]:
        bin_ = REPO_ROOT / "bin" / slug
        assert bin_.is_file() and bin_.stat().st_mode & 0o100, slug
        topo = bin_.read_text(encoding="utf-8").splitlines()[:30]
        assert topo[1].startswith(f"# {slug} — "), f"{slug}: a segunda linha abre com o nome e a abertura"
        assert any(l.startswith("# use para: ") for l in topo), f"{slug}: sem `# use para:` no cabecalho"


def test_o_use_para_nao_leva_numero_de_card_nem_spec_nem_adr_e_nao_tem_nao_use_para(registro):
    """Regra do card: gatilho com numero de card, spec ou ADR nao sobe. A unica fala com ADR e a do dono, citada na
    pagina que ele aprovou (`abre a ADR 97`, no acervo)."""
    for slug in registro["verbos"]:
        topo = (REPO_ROOT / "bin" / slug).read_text(encoding="utf-8").splitlines()[:30]
        use = next(l for l in topo if l.startswith("# use para: "))
        assert not re.search(r"#\d{3,}|arq:\d|spec\b|\bADR\b", use) or slug == "acervo", slug
        assert "NÃO use para" not in use and "NAO use para" not in use, slug


def test_o_oficio_com_o_bloco_cercado_saiu():
    assert not (REPO_ROOT / "abertura" / "oficio-ferramental.md").exists()


@pytest.mark.parametrize("texto", [
    "",                                                                         # vazio
    "verbos: {}\ntransporte: {malote: {}}\n",                                   # verbos vazio
    "verbos: {a: {}}\n",                                                        # falta a chave transporte
    "verbos: {a: {}}\ntransporte: {malote: {}}\nextra: 1\n",                    # chave a mais
    "verbos: {A: {}}\ntransporte: {malote: {}}\n",                              # slug fora da forma
    "verbos: {a: {modelo: 'nao'}}\ntransporte: {malote: {}}\n",                 # modelo nao e booleano
    "verbos: {a: {leva: 2}}\ntransporte: {malote: {}}\n",                       # atributo desconhecido
    "verbos: {a: {faces: {casca: {texto: x}}}}\ntransporte: {malote: {}}\n",    # atributo de face desconhecido
    "verbos: {a: {faces: {casca: {sem_instancia: ler}}}}\ntransporte: {malote: {}}\n",
    "verbos: {a: {}}\ntransporte: {malote: {nome: x}}\n",                       # transporte com atributo
    "verbos: [a, b]\ntransporte: {malote: {}}\n",                               # verbos nao e mapa
    "verbos: {a: {}\n",                                                         # nao e YAML
])
def test_registro_fora_da_forma_e_ilegivel(tmp_path, texto):
    with pytest.raises(rp.RegistroIlegivel):
        rp.carrega(_grava(tmp_path, texto))


def test_arquivo_que_nao_existe_e_ilegivel(tmp_path):
    with pytest.raises(rp.RegistroIlegivel):
        rp.carrega(tmp_path / "nao-existe.yaml")


# --- `acervo listar casa ferramental --tools` e `--oficio`: o recorte do que o modelo ve ---------------------

def _listar():
    loader = SourceFileLoader("listar_porta", str(REPO_ROOT / "bin" / "_acervo" / "listar"))
    spec = importlib.util.spec_from_loader("listar_porta", loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


def _golden(registro, sem=()):
    """O golden record dublado (ler o real e ler o banco): um verbo por linha, os do registro e os cinco que sairam."""
    slugs = [s for s in [*registro["verbos"], "chat", "minuta", "persona", "sinal", "situacao"] if s not in sem]
    return [{"capacidade": f"cap-{s}", "verbo": s, "sot": None, "instancias": [],
             "descricao": f"abertura de {s} · use para: gatilho de {s}"} for s in slugs]


def test_tools_projeta_o_que_o_modelo_ve_com_a_descricao_do_golden_e_sem_o_campo_leva(registro, monkeypatch, capsys):
    listar = _listar()
    monkeypatch.setattr(listar, "_psql_json", lambda sql, alvo: _golden(registro))
    listar.listar_ferramental_tools()
    itens = json.loads(capsys.readouterr().out)
    assert [i["tool"] for i in itens] == rp.visiveis(registro)
    assert not (FORA_DA_LISTA & {i["tool"] for i in itens}) and "metrica" in {i["tool"] for i in itens}
    assert all("leva" not in i for i in itens), "quem retem e a porta, pelo registro"
    assert {i["tool"]: i["descricao"] for i in itens}["infra"] == "abertura de infra · use para: gatilho de infra"
    assert "repo" in {i["tool"] for i in itens}, "o retido continua na projecao: quem o segura e a porta"


def test_oficio_serve_o_mesmo_recorte_e_sai_3_se_o_golden_nao_tem_um_verbo_do_registro(registro, monkeypatch, capsys):
    listar = _listar()
    monkeypatch.setattr(listar, "_psql_json", lambda sql, alvo: _golden(registro))
    listar.listar_ferramental(True, so_oficio=True)
    assert [i["verbo"] for i in json.loads(capsys.readouterr().out)] == [
        s for s in [*registro["verbos"], "chat", "minuta", "persona", "sinal", "situacao"] if s in rp.visiveis(registro)]
    monkeypatch.setattr(listar, "_psql_json", lambda sql, alvo: _golden(registro, sem=("mesa",)))
    with pytest.raises(SystemExit) as saida:
        listar.listar_ferramental(True, so_oficio=True)
    assert saida.value.code == 3
    assert "mesa" in capsys.readouterr().err


def test_os_padroes_sao_modelo_verdadeiro_retido_falso_e_sem_faces(tmp_path):
    r = rp.carrega(_grava(tmp_path, "verbos:\n  a:\n  b: {}\ntransporte:\n  malote:\n"))
    assert r["verbos"] == {"a": {"modelo": True, "retido": False, "faces": {}},
                           "b": {"modelo": True, "retido": False, "faces": {}}}
    assert r["transporte"] == ["malote"]
