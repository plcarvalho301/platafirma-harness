# componente: componente:verbo-busca
"""Story 4426: o ato ler do verbo busca, pela chave, pelo nome e nas recusas.

Os casos puros usam um retrato falso com as linhas que o banco casa devolve (medidas em 22/11/2026)
e uma release de mentira em tmp_path. Os casos com exige("host:casa") rodam o executável contra o
banco casa e a release servida.
"""
from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Self

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BIN = RAIZ / "bin" / "busca"
sys.path.insert(0, str(RAIZ / "lib"))

from leitura import resolvedor
from leitura.recusa import CAMPOS, Recusa, escrever
from leitura.retrato import literal


def _carregar_bin():
    carregador = importlib.machinery.SourceFileLoader("busca_bin", str(BIN))
    spec = importlib.util.spec_from_loader("busca_bin", carregador)
    mod = importlib.util.module_from_spec(spec)
    carregador.exec_module(mod)
    return mod


busca = _carregar_bin()

# ------------------------------------------------------------------ o cadastro de mentira
SHAPE = "00000000-0000-0000-0000-00000000000a"
CLASSES = {  # slug -> uuid da ficha da classe
    "shape": SHAPE,
    "capacidade": "00000000-0000-0000-0000-000000000001",
    "gabarito": "00000000-0000-0000-0000-000000000002",
    "sessao": "00000000-0000-0000-0000-000000000003",
    "card": "00000000-0000-0000-0000-000000000004",
    "servico": "00000000-0000-0000-0000-000000000005",
    "politica": "00000000-0000-0000-0000-000000000006",
    "persona": "00000000-0000-0000-0000-000000000007",
    "gancho": "00000000-0000-0000-0000-000000000008",
    "figura": "00000000-0000-0000-0000-000000000009",
}
MOLDES = {  # uuid da classe -> linhas de SQL_MOLDE
    CLASSES["capacidade"]: [{"fonte": "referencia", "tipo": None, "endereco": "referencias/instancias/capacidade/<slug>.md"}],
    CLASSES["gabarito"]: [
        {"fonte": "golden", "tipo": "casa", "endereco": "instancias/gabarito/<slug>.md"},
        {"fonte": "estrutura", "tipo": "vivo", "endereco": "git"},
    ],
    CLASSES["card"]: [{"fonte": "golden", "tipo": "plataforma", "endereco": "rastreador.item"}],
    CLASSES["servico"]: [{"fonte": "referencia", "tipo": None, "endereco": "referencias/instancias/servico/<stack>/<slug>.md"}],
    CLASSES["politica"]: [
        {"fonte": "golden", "tipo": "casa", "endereco": "instancias/politica/<numero>-<trecho>.md"},
        {"fonte": "estrutura", "tipo": "vivo", "endereco": "postgres"},
    ],
    CLASSES["persona"]: [
        {"fonte": "golden", "tipo": "casa", "endereco": "instancias/persona/<slug>.md"},
        {"fonte": "estrutura", "tipo": "vivo", "endereco": "git"},
    ],
    CLASSES["gancho"]: [{"fonte": "referencia", "tipo": None,
                         "endereco": "referencias/instancias/<pipeline>/<slug do pipeline>.md, na seção dos ganchos"}],
    CLASSES["figura"]: [
        {"fonte": "golden", "tipo": "casa", "endereco": "instancias/figura/<AAAA-MM-DD>-<slug>.md"},
        {"fonte": "estrutura", "tipo": "datado", "endereco": "git"},
    ],
}
FICHAS = {  # chave humana -> (uuid, classe)
    "capacidade:busca": ("10000000-0000-0000-0000-000000000001", "capacidade"),
    "capacidade:sem-arquivo": ("10000000-0000-0000-0000-000000000002", "capacidade"),
    "capacidade:a..b": ("10000000-0000-0000-0000-000000000003", "capacidade"),
    "gabarito:framework-da-ontologia": ("10000000-0000-0000-0000-000000000004", "gabarito"),
    "card:4426": ("10000000-0000-0000-0000-000000000005", "card"),
    "servico:casa:porta": ("10000000-0000-0000-0000-000000000006", "servico"),
    "politica:7-acesso": ("10000000-0000-0000-0000-000000000007", "politica"),
    "gestao-estrategica": ("10000000-0000-0000-0000-000000000008", "persona"),
    "gancho:pre-push": ("10000000-0000-0000-0000-000000000009", "gancho"),
    "figura:2026-11-22-camadas": ("10000000-0000-0000-0000-00000000000a", "figura"),
    **{slug: (u, "shape") for slug, u in CLASSES.items()},
}
NOMES = {  # forma normalizada -> chaves que ela nomeia
    "framework da ontologia": ["gabarito:framework-da-ontologia"],
    "busca": ["capacidade:busca", "verbo:busca", "interface-de-verbo:busca"],
}


def _norm(termo: str) -> str:
    return " ".join("".join(c if c.isalnum() else " " for c in termo.lower()).split())


class RetratoFalso:
    """Responde às consultas do resolvedor e do resolver_nomes como o banco casa responderia."""

    def __init__(self) -> None:
        self.consultas: list[str] = []
        self.aberto = False

    def __enter__(self) -> Self:
        self.aberto = True
        return self

    def __exit__(self, *_a: object) -> None:
        self.aberto = False

    def consultar(self, sql: str, *params):
        assert self.aberto, "consulta fora do retrato"
        if sql is resolvedor.SQL_FICHA:
            self.consultas.append("ficha")
            achada = FICHAS.get(params[0])
            if not achada:
                return []
            return [{"uuid": achada[0], "chave": params[0], "classe": achada[1], "classe_uuid": CLASSES[achada[1]]}]
        if sql is resolvedor.SQL_MOLDE:
            self.consultas.append("molde")
            return MOLDES.get(params[0], [])
        if sql is resolvedor.SQL_FICHA_INTEIRA:
            self.consultas.append("ficha-inteira")
            chave = next(k for k, (u, _c) in FICHAS.items() if u == params[0])
            return [{"ficha": {"chave": chave, "classe": FICHAS[chave][1], "dados": {"rotulo": [chave]}, "ligacoes": {}}}]
        raise AssertionError(f"consulta inesperada: {sql[:60]}")

    def resolver_nomes(self, termos):
        self.consultas.append("nomes")
        norm = _norm(termos[0])
        chaves = NOMES.get(norm, [])
        if not chaves:
            return [{"ord": 1, "norm": norm, "passo": None, "chave": None, "classe": None}]
        return [{"ord": 1, "norm": norm, "passo": 4, "chave": c, "classe": c.split(":")[0],
                 "rotulo": c, "definicao": f"definição de {c}"} for c in chaves]


@pytest.fixture
def release(tmp_path: Path) -> Path:
    casa = tmp_path / "current" / "casa"
    (casa / "referencias/instancias/capacidade").mkdir(parents=True)
    (casa / "referencias/instancias/capacidade/busca.md").write_text("# Capacidade busca\n\nAcha e lê.\n", encoding="utf-8")
    (casa / "instancias/gabarito").mkdir(parents=True)
    (casa / "instancias/gabarito/framework-da-ontologia.md").write_text("# Framework da ontologia\n", encoding="utf-8")
    (casa / "instancias/persona").mkdir(parents=True)
    (casa / "instancias/persona/gestao-estrategica.md").write_text("# Gestão estratégica\n", encoding="utf-8")
    (casa / "referencias/instancias/servico/casa").mkdir(parents=True)
    (casa / "referencias/instancias/servico/casa/porta.md").write_text("# Porta\n", encoding="utf-8")
    (casa / "instancias/figura").mkdir(parents=True)
    (casa / "instancias/figura/2026-11-22-camadas.md").write_text("# Camadas\n", encoding="utf-8")
    return tmp_path


def rodar(args: list[str], release: Path, retrato: RetratoFalso | None = None) -> tuple[int, str, str, RetratoFalso]:
    retrato = retrato or RetratoFalso()
    out, err = io.StringIO(), io.StringIO()
    codigo = busca.main(["ler", *args], saida=out, erro=err, abrir_retrato=lambda: retrato, release=release)
    return codigo, out.getvalue(), err.getvalue(), retrato


def blob(p: Path) -> str:
    dados = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(dados) + dados).hexdigest()


# ------------------------------------------------------------------ pela chave
def test_chave_le_a_referencia_com_a_versao_do_blob(release: Path) -> None:
    codigo, out, err, _ = rodar(["capacidade:busca"], release)
    arq = release / "current/casa/referencias/instancias/capacidade/busca.md"
    assert codigo == 0, err
    primeira, resto = out.split("\n", 1)
    assert primeira == f"capacidade:busca · versão {blob(arq)} · inteiro"
    assert resto == arq.read_text(encoding="utf-8")


def test_versao_e_a_do_git_hash_object(release: Path, tmp_path: Path) -> None:
    arq = release / "current/casa/referencias/instancias/capacidade/busca.md"
    r = subprocess.run(["git", "hash-object", str(arq)], capture_output=True, text=True, check=True, timeout=10)
    assert busca.blob_sha(arq.read_bytes()) == r.stdout.strip()


def test_json_declara_parcial_e_avisos_fora_do_conteudo(release: Path) -> None:
    codigo, out, _err, _ = rodar(["capacidade:busca", "--json"], release)
    r = json.loads(out)
    assert codigo == 0
    assert r["chave"] == "capacidade:busca" and r["parcial"] is False and r["avisos"] == []
    assert r["documento"] == "referencias/instancias/capacidade/busca.md"
    assert r["cabecalho"].startswith("capacidade:busca · versão ")


def test_chave_sem_dois_pontos_entra_inteira_no_molde(release: Path) -> None:
    codigo, out, err, _ = rodar(["gestao-estrategica"], release)
    assert codigo == 0, err
    assert out.split("\n", 1)[1] == "# Gestão estratégica\n"


def test_conexao_fecha_antes_de_abrir_o_arquivo(release: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    retrato = RetratoFalso()
    original = busca.ler_arquivo

    def ler(*a, **kw):
        assert not retrato.aberto, "arquivo aberto com o retrato aberto"
        return original(*a, **kw)

    monkeypatch.setattr(busca, "ler_arquivo", ler)
    codigo, _out, err, _ = rodar(["capacidade:busca"], release, retrato)
    assert codigo == 0, err


# ------------------------------------------------------------------ pelo nome
def test_nome_resolve_para_uma_ficha_e_le_o_texto(release: Path) -> None:
    codigo, out, err, retrato = rodar(["framework da ontologia"], release)
    assert codigo == 0, err
    assert out.startswith("gabarito:framework-da-ontologia · versão ")
    assert out.split("\n", 1)[1] == "# Framework da ontologia\n"
    assert retrato.consultas[:2] == ["ficha", "nomes"]


def test_nome_em_palavras_soltas_e_o_mesmo_nome(release: Path) -> None:
    codigo, out, _err, _ = rodar(["framework", "da", "ontologia"], release)
    assert codigo == 0 and out.startswith("gabarito:framework-da-ontologia · ")


def test_nome_de_varias_fichas_devolve_a_coluna_sem_ler(release: Path) -> None:
    codigo, out, err, retrato = rodar(["busca"], release)
    assert codigo == 0, err
    linhas = out.splitlines()
    assert linhas[0] == "«busca» nomeia 3 fichas · leia pela chave"
    assert [ln.split(" · ")[0] for ln in linhas[1:]] == ["capacidade:busca", "verbo:busca", "interface-de-verbo:busca"]
    assert "molde" not in retrato.consultas


def test_nome_que_nao_casa_sai_1_com_buscar_em_proximo(release: Path) -> None:
    codigo, out, err, _ = rodar(["coisa que nao existe"], release)
    assert codigo == 1 and out == ""
    assert "codigo: termo-nao-casou" in err
    assert err.rstrip().endswith("proximo: busca buscar 'coisa que nao existe'")


def test_termo_sem_letra_sai_2(release: Path) -> None:
    codigo, _out, err, _ = rodar(["???"], release)
    assert codigo == 2 and "codigo: termo-sem-letra" in err


def test_chave_inteira_como_nome_nao_casa(release: Path) -> None:
    codigo, _out, err, _ = rodar(["capacidade:inexistente"], release)
    assert codigo == 1 and "termo-nao-casou" in err


# ------------------------------------------------------------------ a ficha da classe
@pytest.mark.parametrize("chave", ["sessao", "sessao:", "shape:sessao"])
def test_classe_le_a_ficha_da_classe_em_shape(chave: str, release: Path) -> None:
    codigo, out, err, _ = rodar([chave], release)
    assert codigo == 0, err
    primeira = out.split("\n", 1)[0]
    assert primeira.startswith("shape:sessao · versão ")
    assert primeira.endswith(" · inteiro · objeto lido: a ficha da classe sessao")
    assert json.loads(out.split("\n", 1)[1])["chave"] == "sessao"


def test_dois_pontos_de_instancia_nao_le_classe(release: Path) -> None:
    codigo, _out, err, _ = rodar(["capacidade:busca:"], release)
    assert codigo == 1 and "termo-nao-casou" in err


# ------------------------------------------------------------------ ficha inteira
def test_classe_sem_documento_devolve_a_ficha_inteira(release: Path) -> None:
    codigo, out, err, retrato = rodar(["card:4426", "--json"], release)
    r = json.loads(out)
    assert codigo == 0, err
    assert r["objeto"] == "ficha" and r["motivo"] == "golden-de-tipo-plataforma"
    assert json.loads(r["conteudo"])["chave"] == "card:4426"
    assert "ficha-inteira" in retrato.consultas


def test_arquivo_ausente_na_release_devolve_a_ficha(release: Path) -> None:
    codigo, out, _err, _ = rodar(["capacidade:sem-arquivo", "--json"], release)
    r = json.loads(out)
    assert codigo == 0 and r["objeto"] == "ficha" and r["motivo"] == "arquivo-ausente-na-release"


def test_morada_que_nao_e_git_nao_se_le(release: Path) -> None:
    codigo, out, _err, _ = rodar(["politica:7-acesso", "--json"], release)
    r = json.loads(out)
    assert codigo == 0 and r["objeto"] == "ficha" and r["motivo"] == "morada-postgres-nao-lida"


def test_chave_com_dois_pontos_seguidos_no_slug_nao_monta_caminho(release: Path) -> None:
    codigo, out, _err, _ = rodar(["capacidade:a..b", "--json"], release)
    r = json.loads(out)
    assert codigo == 0 and r["objeto"] == "ficha" and r["motivo"] == "chave-fora-do-molde"


# ------------------------------------------------------------------ as oito formas do molde
def _f(chave: str, classe: str) -> resolvedor.Ficha:
    return resolvedor.Ficha("u", chave, classe, "c")


@pytest.mark.parametrize(
    ("molde", "chave", "classe", "esperado"),
    [
        ("instancias/gabarito/<slug>.md", "gabarito:x", "gabarito", "instancias/gabarito/x.md"),
        ("instancias/figura/<AAAA-MM-DD>-<slug>.md", "figura:2026-11-22-x", "figura", "instancias/figura/2026-11-22-x.md"),
        ("instancias/politica/<numero>-<trecho>.md", "politica:7-acesso", "politica", "instancias/politica/7-acesso.md"),
        ("referencias/instancias/servico/<stack>/<slug>.md", "servico:casa:porta", "servico",
         "referencias/instancias/servico/casa/porta.md"),
        ("<onde-mora>/<digest>", "artefato:abc", "artefato", None),
        ("referencias/instancias/<pipeline>/<slug do pipeline>.md, na seção dos ganchos", "gancho:x", "gancho", None),
        ("referencias/instancias/parecer/<AAAA-MM-DD>-<slug>.md, ou o corpo de um comentário", "parecer:2026-11-19-x",
         "parecer", "referencias/instancias/parecer/2026-11-19-x.md"),
        ("delegacao/<slug>.md (golden do agente; na automação, referência da declaração)", "delegacao:x", "delegacao", None),
    ],
)
def test_cada_forma_do_molde(molde: str, chave: str, classe: str, esperado: str | None) -> None:
    assert resolvedor.caminho_do_molde(molde, _f(chave, classe))[0] == esperado


def test_molde_de_duas_pastas_pede_duas_partes_na_chave() -> None:
    molde = "referencias/instancias/servico/<stack>/<slug>.md"
    assert resolvedor.caminho_do_molde(molde, _f("servico:porta", "servico")) == (None, "chave-nao-cabe-no-molde")


def test_molde_com_prosa_devolve_a_ficha(release: Path) -> None:
    codigo, out, _err, _ = rodar(["gancho:pre-push", "--json"], release)
    r = json.loads(out)
    assert codigo == 0 and r["objeto"] == "ficha" and r["motivo"] == "molde-nao-entendido"


def test_molde_de_pasta_e_molde_datado_leem_o_arquivo(release: Path) -> None:
    assert rodar(["servico:casa:porta"], release)[1].split("\n", 1)[1] == "# Porta\n"
    assert rodar(["figura:2026-11-22-camadas"], release)[1].split("\n", 1)[1] == "# Camadas\n"


def test_golden_de_tipo_casa_vem_antes_da_referencia() -> None:
    linhas = [
        {"fonte": "referencia", "tipo": None, "endereco": "referencias/instancias/x/<slug>.md"},
        {"fonte": "golden", "tipo": "casa", "endereco": "instancias/x/<slug>.md"},
    ]
    assert resolvedor._molde_da_classe(linhas) == ("instancias/x/<slug>.md", "golden")


# ------------------------------------------------------------------ paginação
def test_arquivo_maior_que_a_pagina_vem_paginado_com_a_chamada_pronta(release: Path) -> None:
    arq = release / "current/casa/referencias/instancias/capacidade/busca.md"
    arq.write_text("".join(f"linha {i:04d} — ação\n" for i in range(400)), encoding="utf-8")
    sha = blob(arq)
    codigo, out, err, _ = rodar(["capacidade:busca", "--max-bytes", "1000", "--json"], release)
    r = json.loads(out)
    assert codigo == 0, err
    assert r["parcial"] is True and r["parte"].startswith("bytes 0–")
    fim = r["bytes"][1]
    assert r["proximo"] == f"busca ler capacidade:busca --offset {fim} --versao {sha} --max-bytes 1000"
    _c, out2, _e, _ = rodar(["capacidade:busca", "--offset", str(fim), "--versao", sha, "--max-bytes", "1000", "--json"], release)
    r2 = json.loads(out2)
    assert r2["bytes"][0] == fim and r2["versao"] == sha and r2["avisos"] == []
    assert r2["cabecalho"].startswith(f"capacidade:busca · versão {sha} · bytes {fim}–")


def test_texto_paginado_poe_proximo_depois_do_conteudo(release: Path) -> None:
    arq = release / "current/casa/referencias/instancias/capacidade/busca.md"
    arq.write_text("x" * 3000 + "\n", encoding="utf-8")
    _c, out, _e, _ = rodar(["capacidade:busca", "--max-bytes", "1000"], release)
    assert out.splitlines()[-2:] == ["--", f"proximo: busca ler capacidade:busca --offset 1000 --versao {blob(arq)} --max-bytes 1000"]


def test_versao_que_mudou_entre_paginas_vira_aviso(release: Path) -> None:
    _c, out, _e, _ = rodar(["capacidade:busca", "--versao", "abc", "--json"], release)
    r = json.loads(out)
    assert r["mudou"] is True and r["avisos"] and "abc" not in r["conteudo"]


# ------------------------------------------------------------------ recusas
def test_caminho_solto_sai_2_sem_abrir_o_banco(release: Path) -> None:
    def nao_abre():
        raise AssertionError("o caminho solto não abre o banco")

    out, err = io.StringIO(), io.StringIO()
    codigo = busca.main(["ler", "/srv/platafirma/casa/x.md"], saida=out, erro=err, abrir_retrato=nao_abre, release=release)
    assert codigo == 2 and out.getvalue() == ""
    assert err.getvalue().startswith("codigo: caminho-solto-recusado · onde: chave · recebido: /srv/platafirma/casa/x.md")
    assert err.getvalue().rstrip().endswith("proximo: busca ler x")


def test_caminho_solto_de_referencia_propoe_a_chave(release: Path) -> None:
    caminho = "/opt/platafirma/current/casa/referencias/instancias/capacidade/busca.md"
    codigo, _out, err, _ = rodar([caminho, "--json"], release)
    campos = json.loads(err)
    assert codigo == 2 and list(campos) == list(CAMPOS)
    assert campos["codigo"] == "caminho-solto-recusado" and campos["proximo"] == "busca ler capacidade:busca"


def test_ato_desconhecido_e_flag_desconhecida_saem_2(release: Path) -> None:
    out, err = io.StringIO(), io.StringIO()
    assert busca.main(["abrir", "x"], saida=out, erro=err) == 2 and "ato-desconhecido" in err.getvalue()
    codigo, _o, err2, _ = rodar(["capacidade:busca", "--linhas", "1-2"], release)
    assert codigo == 2 and "flag-desconhecida" in err2


def test_recusa_tem_seis_campos_na_ordem_e_corta_o_recebido() -> None:
    r = Recusa(2, "x", onde="o", recebido="r" * 500, regra="g", cura="c", proximo="p")
    err = io.StringIO()
    assert escrever(r, fluxo=err) == 2
    assert [p.split(": ", 1)[0] for p in err.getvalue().rstrip().split(" · ")] == list(CAMPOS)
    assert len(r.recebido) == 200
    with pytest.raises(ValueError, match="fora de 0 a 5"):
        Recusa(6, "x")


def test_literal_do_bind_escapa_aspas_barras_e_quebras() -> None:
    assert literal("it's \\ x\nnova") == "'it\\'s \\\\ x\\nnova'"
    assert literal(["a b", 'c"d']) == "'{\"a b\",\"c\\\\\"d\"}'"


# ------------------------------------------------------------------ contra o banco casa
def _executar(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BIN), "ler", *args], capture_output=True, text=True, timeout=30,
                          env={**os.environ}, check=False)


@pytest.mark.exige("host:casa")
def test_vivo_capacidade_busca_le_a_referencia_da_release() -> None:
    r = _executar("capacidade:busca")
    arq = Path("/opt/platafirma/current/casa/referencias/instancias/capacidade/busca.md")
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\n", 1)[0].startswith(f"capacidade:busca · versão {blob(arq)} · ")


@pytest.mark.exige("host:casa")
def test_vivo_framework_da_ontologia_le_o_gabarito() -> None:
    r = _executar("framework da ontologia")
    arq = Path("/opt/platafirma/current/casa/instancias/gabarito/framework-da-ontologia.md")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("gabarito:framework-da-ontologia · versão ")
    assert arq.read_text(encoding="utf-8").startswith(r.stdout.split("\n", 1)[1][:200])


@pytest.mark.exige("host:casa")
@pytest.mark.parametrize("chave", ["sessao", "sessao:"])
def test_vivo_sessao_le_a_ficha_da_classe(chave: str) -> None:
    r = _executar(chave)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\n", 1)[0].endswith("objeto lido: a ficha da classe sessao")
    assert r.stdout.startswith("shape:sessao · versão ")


@pytest.mark.exige("host:casa")
def test_vivo_caminho_solto_sai_2() -> None:
    r = _executar("/srv/platafirma/casa/x.md")
    assert r.returncode == 2 and r.stderr.startswith("codigo: caminho-solto-recusado")
