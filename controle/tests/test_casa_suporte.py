# componente: componente:verbo-acervo
# Contrato do cliente de casa sem banco e sem rede (arq:0115 §3, §7, §8.1, §11; contrato de
# dados D2/D5/D6/D9/D10): o espelho bare do suporte, a leitura por sha, o predicado 8
# (diagrama sem documento), o payload, o plano impresso e a forma da chave. Roda contra um
# forge LOCAL em tmp_path; nada toca rag_extractor nem o forge de verdade.
import importlib.machinery
import importlib.util
import json
import os
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACERVO = os.path.join(REPO, "bin", "_acervo")
GIT = next((p for p in ("/usr/bin/git", "/bin/git") if os.path.exists(p)), "git")


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


casa = _carrega("acervo_casa", "casa")


# ------------------------------------------------------------------ chave e leitura (D9)

def test_rotulo_forca_registro_leva_a_data_da_chave():
    # card #3139 item 1: forca "registro" exibe "registro de AAAA-MM-DD" (a data da chave
    # datada), nao so "registro" cru; decisao/proposta/nao_declarada nao levam data.
    assert casa._rotulo_forca({"forca": "registro", "chave": "2026-09-24-descobrir-a-casa"}) \
        == "registro de 2026-09-24"
    assert casa._rotulo_forca({"forca": "registro", "chave": None}) == "registro"
    assert casa._rotulo_forca({"forca": "decisao", "chave": "arq:0115"}) == "decisão"
    assert casa._rotulo_forca({"forca": "proposta", "chave": "x"}) == "proposta"
    assert casa._rotulo_forca({"forca": "nao_declarada", "chave": "x"}) == "força não declarada"


def test_normalizar_chave():
    assert casa.normalizar("adr", "arq:75") == "arq:0075"
    assert casa.normalizar("adr", "seg:14") == "seg:0014"
    assert casa.normalizar("adr", "75") is None          # numero nu: resolve por serie, no banco
    assert casa.normalizar("adr", "adr e documento vivo") is None   # texto: cai no titulo
    assert casa.normalizar("minuta", "38") == "0038"
    assert casa.normalizar("spec", "acervo") == "acervo"
    assert casa.normalizar("nota-tecnica", "2026-09-08-x") == "2026-09-08-x"
    for ruim in ("arq:11O", "12a", "arq:"):
        with pytest.raises(SystemExit) as e:
            casa.normalizar("adr", ruim)
        assert e.value.code == 2


def test_cobertura_e_servido():
    assert casa.txt_ultimo({"arq": 115, "seg": 14}) == "último: arq:0115 · seg:0014"
    assert casa.txt_ultimo({"": 38}) == "último: 0038"
    assert casa.txt_ultimo(None) is None
    f = {"sha": "a" * 40, "em": "2026-09-23 18:00Z"}
    esp = ("a" * 40, None, "2026-09-23 17:59Z")
    linha = {"repo": "platafirma-casa", "sha": "a" * 40}
    s = casa.servido(linha, f, esp)
    assert s == "aaaaaaaaaaaa (= main do espelho, buscado em 2026-09-23 17:59Z)"
    assert "ingestão defasada" in casa.servido(linha, f, ("b" * 40, None, "2026-09-23 17:59Z"))
    assert "indeterminável" in casa.servido(linha, f, (None, "espelho ausente", None))
    assert casa.servido(linha, None, esp) == "nunca ingerido"
    assert "fora do suporte" in casa.servido({"repo": "platafirma-core", "sha": "a" * 40}, f, esp)
    assert "(igual)" not in s
    # POR LINHA: legado mantido (nova versao recusada) ou fora do recorte serve texto de outro
    # sha que o da fonte; `servido` nao pode dizer "= main" so porque a fonte bate com o main
    velho = casa.servido({"repo": "platafirma-casa", "sha": "c" * 40}, f, esp)
    assert velho.startswith("texto de cccccccccccc; fonte em aaaaaaaaaaaa: versão nova recusada "
                            "ou fora do recorte")
    assert "= main do espelho" not in velho and "main do espelho em aaaaaaaaaaaa" in velho
    # retirada nao serve texto nenhum
    assert casa.servido(dict(linha, retirada_em="2026-09-24"), f, esp).startswith(
        "não servida: retirada em 2026-09-24")
    # cobertura (§11.2): a fonte, o espelho e quantas linhas servem texto de outro sha
    info = {"slug": "adr", "projecao": "adr/<serie>/<numero>-<slug>.md", "regime": "vivo",
            "ultimo": {"arq": 115}, "sem_chave": 0, "fora_da_fonte": 2, "legado": 3,
            "retiradas": 1}
    cab = casa.linha_cobertura(10, info, f, esp=esp)
    assert cab.startswith("10 linha(s) · adr · fonte platafirma-casa@aaaaaaaaaaaa ingerida em "
                          "2026-09-23 18:00Z · = main do espelho, buscado em 2026-09-23 17:59Z")
    assert "2 com texto de outro sha que a fonte" in cab
    assert "3 fora do suporte (legado)" in cab and "1 retirada(s) fora (--todas)" in cab
    assert "ingestão defasada" in casa.linha_cobertura(
        10, info, f, esp=("b" * 40, None, "2026-09-23 17:59Z"))
    assert "com texto de outro sha" not in casa.linha_cobertura(10, info, None, esp=esp)
    assert casa.ident({"chave": None, "repo": "r", "path": "p.md"}) == "r@p.md"
    assert casa.ident({"chave": "arq:0075", "repo": "r", "path": "p.md"}) == "arq:0075"


def test_argv_de_listar_e_ler(monkeypatch):
    chamadas = []
    monkeypatch.setattr(casa, "catalogo", lambda j: chamadas.append(("catalogo", j)) or 0)
    monkeypatch.setattr(casa, "listar", lambda e, j, dono=None, situacao=False, todas=False:
                        chamadas.append(("listar", e, dono, todas)) or 0)
    monkeypatch.setattr(casa, "sobre", lambda c, k, e, j, todas=False:
                        chamadas.append(("sobre", c, k, e, todas)) or 0)
    monkeypatch.setattr(casa, "ler", lambda e, s, j, situacao=False, offset=0, cru=False:
                        chamadas.append(("ler", e, s, situacao)) or 0)
    casa.main(["listar"])
    casa.main(["listar", "--json"])
    casa.main(["listar", "adr", "--todas", "--dono", "arquiteto"])
    casa.main(["listar", "--sobre", "verbo", "acervo", "--todas"])
    casa.main(["listar", "spec", "--sobre", "verbo:acervo"])
    casa.main(["listar", "--sobre", "acervo", "--json"])
    casa.main(["ler", "adr", "arq:75", "--situacao"])
    assert chamadas == [
        ("catalogo", False), ("catalogo", True), ("listar", "adr", "arquiteto", True),
        ("sobre", "verbo", "acervo", None, True), ("sobre", "verbo:acervo", None, "spec", False),
        ("sobre", "acervo", None, None, False), ("ler", "adr", "arq:75", True)]
    for ruim in (["listar", "--sobre"], ["ler", "adr"], ["listar", "a", "b"], ["apagar"]):
        with pytest.raises(SystemExit) as e:
            casa.main(ruim)
        assert e.value.code == 2


# ------------------------------------------------------------------ retirada na leitura (§3.5, D4, D9)

LINHA_RETIRADA = {
    "id": "00000000-0000-0000-0000-000000000094", "chave": "arq:0094", "serie": "arq",
    "numero": 94, "repo": "platafirma-casa", "path": "adr/arq/0094-adr-servida-por-verbo.md",
    "sha": "b" * 40, "dono": "arquiteto", "natureza": "golden", "ciclo": "superado",
    "titulo": "0094 — ADR servida por verbo", "subtipo": None, "especie": "adr",
    "criado_em": "2026-09-01", "retirada_em": "2026-09-24", "substituida_por": "arq:0112",
    "vetorizado_em": None}
LINHA_VIVA = dict(LINHA_RETIRADA, id="00000000-0000-0000-0000-000000000112", chave="arq:0112",
                  numero=112, path="adr/arq/0112-acervo-ler-casa.md", sha="a" * 40,
                  ciclo="publicado", titulo="0112 — acervo ler casa", retirada_em=None,
                  substituida_por=None, vetorizado_em="2026-09-24")


@pytest.fixture
def banco_falso(monkeypatch):
    """acervo.casa de mentira: uma ADR retirada (arq:0094 -> arq:0112) e a sucessora viva."""
    info = {"slug": "adr", "projecao": "adr/<serie>/<numero>-<slug>.md", "regime": "vivo",
            "vivas": 1, "retiradas": 1, "sem_chave": 0, "fora_da_fonte": 0, "legado": 0,
            "ultimo": {"arq": 112}}
    wheres = []

    def linhas(where, limite=None):
        wheres.append(where)
        if "c.chave = 'arq:0094'" in where:
            return [LINHA_RETIRADA]
        if "retirada_em is null" in where:
            return [LINHA_VIVA]
        return [LINHA_RETIRADA, LINHA_VIVA]

    def sem_q(*a, **k):
        raise AssertionError("linha retirada nao le corpo nem outra consulta")

    monkeypatch.setattr(casa, "_especie", lambda especie: info)
    monkeypatch.setattr(casa, "_linhas", linhas)
    monkeypatch.setattr(casa, "_fonte", lambda: {"sha": "a" * 40, "em": "2026-09-24 12:00Z"})
    monkeypatch.setattr(casa._suporte, "main_do_espelho", lambda esp=None: ("a" * 40, None))
    monkeypatch.setattr(casa._suporte, "ultima_busca", lambda esp=None: "2026-09-24 11:59Z")
    monkeypatch.setattr(casa, "_q", sem_q)
    return wheres


def test_ler_retirada_responde_data_e_sucessora_sem_texto(banco_falso, capsys, monkeypatch):
    assert casa.ler("adr", "arq:94", False) == 0
    out = capsys.readouterr().out.splitlines()
    # card #3139 item 1: a marca (força não declarada, sem forca/revisao no banco_falso) abre a
    # saída mesmo em documento retirado, sem corpo (§3.5).
    assert out == [
        "força não declarada · substituída por arq:0112 — adr arq:0094 · 0094 — ADR servida por verbo",
        "arq:0094: retirada em 2026-09-24; substituída por arq:0112",
        "  a vigente: acervo ler casa adr arq:0112"]
    # sem sucessora declarada: diz, e nao inventa a vigente
    sem_sucessora = dict(LINHA_RETIRADA, substituida_por=None)
    monkeypatch.setattr(casa, "_linhas", lambda where, limite=None: [sem_sucessora])
    assert casa.ler("adr", "arq:0094", False) == 0
    assert capsys.readouterr().out.splitlines() == [
        "força não declarada · retirada em 2026-09-24 sem sucessora — adr arq:0094 · "
        "0094 — ADR servida por verbo",
        "arq:0094: retirada em 2026-09-24; sem sucessora declarada"]


def test_ler_retirada_json_tem_corpo_none(banco_falso, capsys):
    assert casa.ler("adr", "arq:0094", True, situacao=True) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["id"] == "arq:0094" and doc["corpo"] is None
    assert doc["retirada_em"] == "2026-09-24" and doc["substituida_por"] == "arq:0112"
    assert doc["situacao"]["status"] == "retirada em 2026-09-24; substituída por arq:0112"
    assert doc["situacao"]["servido"].startswith("não servida: retirada em 2026-09-24")


def test_listar_todas_inclui_retiradas(banco_falso, capsys):
    assert casa.listar("adr", False) == 0
    so_vivas = capsys.readouterr().out
    assert "retirada_em is null" in banco_falso[-1]
    assert "1 retirada(s) fora (--todas)" in so_vivas.splitlines()[0]
    assert "arq:0094" not in so_vivas and "arq:0112" in so_vivas
    assert casa.listar("adr", False, todas=True) == 0
    todas = capsys.readouterr().out
    assert "retirada_em is null" not in banco_falso[-1]
    assert "inclui retiradas" in todas.splitlines()[0]
    linha = next(l for l in todas.splitlines() if l.startswith("arq:0094 "))
    # card #3139 item 4: a coluna de texto mostra força · vigência no lugar de ciclo; o
    # título não repete mais o "(retirada em ...)" que a vigência já diz.
    assert "força não declarada · substituída por arq:0112" in linha
    assert linha.endswith("0094 — ADR servida por verbo")
    assert casa.listar("adr", True, situacao=True, todas=True) == 0
    itens = {i["id"]: i for i in json.loads(capsys.readouterr().out)}
    assert itens["arq:0094"]["substituida_por"] == "arq:0112"
    assert itens["arq:0094"]["situacao"]["servido"].startswith("não servida")
    assert itens["arq:0112"]["situacao"]["servido"] == (
        "aaaaaaaaaaaa (= main do espelho, buscado em 2026-09-24 11:59Z)")


# ------------------------------------------------------------------ ler com --offset (#2856 linha 161)

@pytest.fixture
def banco_com_corpo(monkeypatch):
    """acervo.casa de mentira com UMA linha viva cujo corpo o teste escolhe."""
    corpo = {"texto": ""}
    info = {"slug": "levantamento", "projecao": "levantamento/<data>-<slug>.md", "regime": "datado",
            "vivas": 1, "retiradas": 0, "sem_chave": 0, "fora_da_fonte": 0, "legado": 0,
            "ultimo": {}}
    linha = dict(LINHA_VIVA, chave="2026-09-29-conformacao-0118-0119", serie=None, numero=None,
                 especie="levantamento", titulo="Conformação 0118 e 0119")
    monkeypatch.setattr(casa, "_especie", lambda especie: info)
    monkeypatch.setattr(casa, "_linhas", lambda where, limite=None: [linha])
    monkeypatch.setattr(casa, "_fonte", lambda: {"sha": "a" * 40, "em": "2026-09-24 12:00Z"})
    monkeypatch.setattr(casa._suporte, "main_do_espelho", lambda esp=None: ("a" * 40, None))
    monkeypatch.setattr(casa._suporte, "ultima_busca", lambda esp=None: "2026-09-24 11:59Z")
    monkeypatch.setattr(casa, "_q", lambda sql, alvo="": {"corpo": corpo["texto"]})
    return corpo


CHAVE_LONGA = "2026-09-29-conformacao-0118-0119"


def test_ler_documento_longo_sai_inteiro_por_padrao_sem_truncar(banco_com_corpo, capsys):
    assert not hasattr(casa, "PAGINA")
    banco_com_corpo["texto"] = "".join(f"ponto {i:04d} " + "x" * 88 + "\n" for i in range(1200))
    assert len(banco_com_corpo["texto"].encode("utf-8")) == 120_000
    assert casa.ler("levantamento", CHAVE_LONGA, False) == 0
    out = capsys.readouterr().out
    assert "ponto 0000" in out and "ponto 1199" in out
    assert "truncado em" not in out


def test_ler_por_max_bytes_e_offset_reconstroi_o_documento_inteiro(banco_com_corpo, capsys):
    # texto com multibyte (ç, ã, —): `lib/leitura` corta na fronteira UTF-8 sem perder nem repetir bytes
    original = "".join(f"ponto {i:02d} — ação, conformação e decisão\n" for i in range(18))
    banco_com_corpo["texto"] = original
    pedacos, offset = [], 0
    for _ in range(100):
        assert casa.ler("levantamento", CHAVE_LONGA, True, offset=offset, max_bytes=97, inteiro=False) == 0
        doc = json.loads(capsys.readouterr().out)
        assert "\ufffd" not in doc["corpo"]
        assert len(doc["corpo"].encode("utf-8")) <= 97
        pedacos.append(doc["corpo"])
        if doc["next_offset"] is None:
            break
        offset = doc["next_offset"]
    else:
        raise AssertionError("fatiamento por offset nao termina")
    assert len(pedacos) > 3
    assert "".join(pedacos) == original


def test_ler_json_inteiro_por_padrao_e_suporta_max_bytes_e_linhas(banco_com_corpo, capsys):
    banco_com_corpo["texto"] = "x" * 120
    assert casa.ler("levantamento", CHAVE_LONGA, True) == 0
    doc_inteiro = json.loads(capsys.readouterr().out)
    assert doc_inteiro["corpo"] == "x" * 120
    assert doc_inteiro["truncado"] is False and doc_inteiro["next_offset"] is None

    assert casa.ler("levantamento", CHAVE_LONGA, True, max_bytes=50, inteiro=False) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["corpo"] == "x" * 50 and doc["truncado"] is True
    assert doc["bytes_total"] == 120 and doc["next_offset"] == 50
    assert casa.ler("levantamento", CHAVE_LONGA, True, offset=100, max_bytes=50, inteiro=False) == 0
    doc2 = json.loads(capsys.readouterr().out)
    assert doc2["corpo"] == "x" * 20 and doc2["truncado"] is False and doc2["next_offset"] is None

    banco_com_corpo["texto"] = "l1\nl2\nl3\nl4\n"
    assert casa.ler("levantamento", CHAVE_LONGA, False, linhas="2-3") == 0
    assert capsys.readouterr().out.split("\n", 1)[1] == "l2\nl3\n"


def test_ler_offset_alem_do_fim_sai_2(banco_com_corpo, capsys):
    banco_com_corpo["texto"] = "curto\n"
    with pytest.raises(SystemExit) as e:
        casa.ler("levantamento", CHAVE_LONGA, False, offset=99)
    assert e.value.code == 2
    assert "--offset 99" in capsys.readouterr().err


def test_ler_documento_curto_sai_igual_a_antes(banco_com_corpo, capsys):
    banco_com_corpo["texto"] = "# curto\n\ncorpo\n"
    assert casa.ler("levantamento", CHAVE_LONGA, False) == 0
    assert capsys.readouterr().out.split("\n", 1)[1] == "# curto\n\ncorpo\n"


def test_main_ler_aceita_offset_e_recusa_o_malformado(monkeypatch):
    chamadas = []
    monkeypatch.setattr(casa, "ler", lambda e, s, j, situacao=False, offset=0, cru=False, **kw:
                        chamadas.append((e, s, j, offset, kw)) or 0)
    casa.main(["ler", "levantamento", "2026-09-29-x", "--offset", "1200"])
    casa.main(["ler", "--offset", "7", "--linhas", "2-5", "levantamento", "2026-09-29-x", "--json"])
    assert chamadas == [("levantamento", "2026-09-29-x", False, 1200, {}),
                        ("levantamento", "2026-09-29-x", True, 7, {"linhas": "2-5"})]
    for ruim in (["ler", "a", "b", "--offset"], ["ler", "a", "b", "--offset", "x"],
                 ["ler", "a", "b", "--offset", "-1"], ["listar", "a", "--offset", "1"],
                 ["listar", "a", "--linhas", "1-5"], ["ler", "a", "b", "--max-bytes", "0"]):
        with pytest.raises(SystemExit) as e:
            casa.main(ruim)
        assert e.value.code == 2, ruim
    assert len(chamadas) == 2


# ------------------------------------------------------------------ Sobre: e resolver (sem banco)

def test_sobre_so_aceita_classe_de_referente(monkeypatch, capsys):
    # conceito, adr, spec e parecer nao sao referente de Sobre: (arq:0115 §6.2); recusa sem banco
    monkeypatch.setattr(casa, "_q", lambda *a, **k: pytest.fail("nao consulta o banco"))
    for classe in ("conceito", "adr", "spec"):
        with pytest.raises(SystemExit) as e:
            casa._entidade(classe, "acervo")
        assert e.value.code == 2
        assert "nao e referente de Sobre:" in capsys.readouterr().err
    assert set(casa.CLASSES_SOBRE) == {"verbo", "capacidade", "stack", "servico",
                                       "repositorio", "persona", "cadeira", "risco"}
    assert "instancia" not in casa.CLASSES_SOBRE    # saiu do catálogo (arq:0108 §13, #3761, migração 113)


@pytest.mark.parametrize("palavra", ["cadeira", "persona"])
def test_sobre_cadeira_e_persona_procuram_a_ficha_nas_duas_classes(monkeypatch, palavra):
    """#3991: cadeira é rótulo alternativo de persona; a 135 troca a classe das fichas, e até a retirada
    da classe cadeira (#3997) a ficha pode estar em qualquer das duas. Devolve a classe em que achou."""
    sqls = []
    monkeypatch.setattr(casa, "_q", lambda sql, alvo="": sqls.append(sql) or [
        {"id": "u", "classe": "persona", "chave_humana": "dados"}])
    assert casa._entidade(palavra, "dados") == ("persona", "dados", "u")
    assert "array['persona', 'cadeira']::text[]" in sqls[0] and "'verbo'" not in sqls[0]


def test_sobre_sem_classe_procura_so_fichas_ativas_das_classes_de_referente(monkeypatch):
    sqls = []
    monkeypatch.setattr(casa, "_q", lambda sql, alvo="": sqls.append(sql) or [
        {"id": "u", "classe": "verbo", "chave_humana": "acervo"}])
    assert casa._entidade(None, "acervo") == ("verbo", "acervo", "u")
    assert "e.estado = 'ativa'" in sqls[0] and "'risco'" in sqls[0] and "'conceito'" not in sqls[0]


def test_ler_forma_invalida_sai_2_sem_banco(monkeypatch, capsys):
    monkeypatch.setattr(casa, "_q", lambda *a, **k: pytest.fail("nao consulta o banco"))
    with pytest.raises(SystemExit) as e:
        casa.ler("adr", "arq:11O", False)
    assert e.value.code == 2 and "Forma esperada" in capsys.readouterr().err


def test_resolver_adr_forma_no_cliente_e_recusa_quando_a_classe_sai(monkeypatch, capsys):
    ident = casa._identidade
    consultas = []
    monkeypatch.setattr(ident, "psql_json", lambda sql, alvo="query": consultas.append(alvo) or [])
    # a forma de adr e do cliente: recusa antes de qualquer consulta (vale antes e depois da 060)
    with pytest.raises(SystemExit) as e:
        ident.validar_forma("adr", "arq:11O")
    assert e.value.code == 2 and consultas == []
    assert "invalido" in capsys.readouterr().err
    # depois da 060 (adr fora de entidade_classe): recusa e aponta a leitura pela chave
    with pytest.raises(SystemExit) as e:
        ident.validar_forma("adr", "arq:0110")
    assert e.value.code == 2
    assert "acervo ler casa adr arq:0110" in capsys.readouterr().err


def test_resolver_adr_por_slug_do_arquivo(monkeypatch):
    # card #3121: sem chave nem numero, `ler casa adr <slug>` resolve pelo NNNN-<slug>.md do
    # caminho — a adr e regime 'vivo' mas a CHAVE e <serie>:NNNN, nao o slug; sem este degrau
    # o slug do arquivo nunca resolvia.
    info = {"slug": "adr", "regime": "vivo"}
    slug = "sessao-id-a-chave-nomeada-da-entidade-sessao-cunhada-na-borda-como-shadow-session"
    achada = dict(LINHA_VIVA, chave="arq:0091", numero=91,
                 path="adr/arq/0091-" + slug + ".md")
    wheres = []

    def linhas(where, limite=None):
        wheres.append(where)
        return [achada] if "c.path ~" in where else []

    monkeypatch.setattr(casa, "_linhas", linhas)
    assert casa.resolver("adr", slug, info) is achada
    assert any("c.path ~" in w and slug in w for w in wheres)


def test_resolver_adr_slug_ambiguo_lista_opcoes(monkeypatch, capsys):
    info = {"slug": "adr", "regime": "vivo"}
    duas = [dict(LINHA_VIVA, chave="arq:0091"), dict(LINHA_VIVA, chave="arq:0092")]
    monkeypatch.setattr(casa, "_linhas", lambda where, limite=None:
                        duas if "c.path ~" in where else [])
    with pytest.raises(SystemExit) as e:
        casa.resolver("adr", "slug-repetido", info)
    assert e.value.code == 2
    assert "ambiguo" in capsys.readouterr().err


def test_resolver_adr_numero_puro_nao_cai_no_degrau_de_slug(monkeypatch):
    # regressao: '0091' casa RE_ADR (numero nu) e resolve antes de chegar ao degrau de slug.
    chamou_slug = []

    def linhas(where, limite=None):
        if "c.numero = 91" in where:
            return [dict(LINHA_VIVA, chave="arq:0091", numero=91)]
        if "c.path ~" in where:
            chamou_slug.append(where)
        return []

    monkeypatch.setattr(casa, "_linhas", linhas)
    achada = casa.resolver("adr", "0091", {"slug": "adr", "regime": "vivo"})
    assert achada["chave"] == "arq:0091"
    assert chamou_slug == []


def test_resolver_adr_forma_invalida_nao_casa_slug_e_negativa_lista_formas(monkeypatch, capsys):
    # 'arq-0091' nao e <serie>:NNNN (hifen, nao dois-pontos): normalizar() nao recusa (nao
    # comeca com 'letras:' nem digito), mas nenhum degrau acha nada e a negativa final (exit
    # 1) lista as formas aceitas, incluindo o slug do arquivo.
    monkeypatch.setattr(casa, "_linhas", lambda where, limite=None: [])
    monkeypatch.setattr(casa._identidade, "gerar_negativa", lambda *a, **k: "negativa")
    with pytest.raises(SystemExit) as e:
        casa.resolver("adr", "arq-0091", {"slug": "adr", "regime": "vivo"})
    assert e.value.code == 1
    err = capsys.readouterr().err
    assert "formas:" in err and casa.FORMA_ADR in err and "<slug> do arquivo" in err


# ------------------------------------------------------------------ despachante (sem banco)

BIN = os.path.join(REPO, "bin", "acervo")


def _acervo(*args):
    return subprocess.run([BIN, *args], capture_output=True, text=True,
                          env=dict(os.environ, PF_SESSAO_ID=f"teste-casa-{os.getpid()}"))


def test_despachante_recusas_sem_banco():
    r = _acervo("adr", "0110")
    assert r.returncode == 2
    assert "acervo adr: ato deprecado e removido" in r.stderr
    assert "acervo ler casa adr" in r.stderr
    r = _acervo("escrever", "casa", "spec", "x")
    assert r.returncode == 2
    assert "PR → merge em main." in r.stderr
    assert "release promover" not in r.stderr
    r = _acervo("ingerir", "casa", "platafirma-casa")
    assert r.returncode == 2
    assert "busca consultar" in r.stderr and "busca ler" in r.stderr
    r = _acervo("ingerir", "casa")
    assert r.returncode == 2
    assert "falta a entidade" in r.stderr


def test_cabecalho_do_verbo_aponta_o_suporte():
    with open(BIN, encoding="utf-8") as f:
        # O contrato vai ate a declaracao, sem depender do tamanho do cabecalho.
        linhas = []
        for linha in f:
            linhas.append(linha)
            if linha.startswith("SPEC="):
                break
        cab = "".join(linhas)
    assert "# le: ingerir=repo" in cab
    assert "PLATAFIRMA_INSTANCIA" in cab and "platafirma-casa.git" in cab
    assert "PLATAFIRMA_RELEASE" not in cab
    assert 'SPEC="spec acervo (acervo ler casa spec acervo)"' in cab


def test_sem_caminho_fixo_de_platafirma_arquitetura():
    # D9: nada de caminho de platafirma-arquitetura no cliente de casa nem no despachante.
    for rel in ("bin/acervo", "bin/_acervo/casa",
                "bin/_acervo/_identidade.py", "bin/_acervo/_suporte.py", "bin/_acervo/exportar"):
        with open(os.path.join(REPO, rel), encoding="utf-8") as f:
            txt = f.read()
        assert "platafirma-arquitetura" not in txt, rel
        assert "macro-global" not in txt, rel
        assert "padrao_path" not in txt, rel
