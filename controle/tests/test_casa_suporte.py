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


ingerir = _carrega("casa_ingerir", "casa-ingerir")
casa = _carrega("acervo_casa", "casa")

ARVORE = {
    "adr/arq/0001-primeira.md": "# 0001 — Primeira\n\n- **Status:** aceito\n\n## Contexto\n\ntexto\n",
    "spec/acervo.md": "﻿# Acervo — espécie e chave\n\nEspécie: spec\nSobre: verbo acervo\n\n## Uso\n",
    "spec/acervo.1.mmd": "graph TD; a-->b\n",
    "spec/figura.d2": "a -> b\n",
    "padrao/sem-doc.2.mmd": "graph TD; x-->y\n",
    "nota-tecnica/2026-09-08-cerca.md": "```\n# falso\n```\n\n# Verdadeiro\n",
    "levantamento/2026-08-10-fluxos.md": "sem titulo nenhum\n",
    "levantamento/2026-08-10-fluxos.10.mmd": "graph LR; p-->q\n",
    "adr/org/.gitkeep": "",
    "README.md": "# leia-me\n",
}


def _git(cwd, *args):
    r = subprocess.run([GIT, "-c", "user.name=teste", "-c", "user.email=teste@exemplo.invalid",
                        "-C", str(cwd), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture
def suporte(tmp_path, monkeypatch):
    forge = tmp_path / "forge"
    forge.mkdir()
    _git(forge, "init", "-q")
    _git(forge, "symbolic-ref", "HEAD", "refs/heads/main")
    for p, txt in ARVORE.items():
        f = forge / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(txt, encoding="utf-8")
    _git(forge, "add", "-A")
    _git(forge, "commit", "-q", "-m", "primeiro")
    primeiro = _git(forge, "rev-parse", "HEAD")
    (forge / "spec" / "segunda.md").write_text("# Segunda\n", encoding="utf-8")
    _git(forge, "add", "-A")
    _git(forge, "commit", "-q", "-m", "segundo")
    main = _git(forge, "rev-parse", "HEAD")
    _git(forge, "checkout", "-q", "-b", "outro")
    (forge / "spec" / "fora-de-main.md").write_text("# Fora\n", encoding="utf-8")
    _git(forge, "add", "-A")
    _git(forge, "commit", "-q", "-m", "fora de main")
    _git(forge, "checkout", "-q", "main")
    esp = tmp_path / "instancia" / "var" / "acervo" / "suporte" / "platafirma-casa.git"
    monkeypatch.setenv("PF_SUPORTE_URL", str(forge))
    monkeypatch.setenv("PF_SUPORTE_ESPELHO", str(esp))
    ingerir.garantir_espelho(str(esp), str(forge))
    return {"esp": str(esp), "forge": str(forge), "primeiro": primeiro, "main": main}


# ------------------------------------------------------------------ espelho e sha (§8.1, D10)

def test_espelho_nasce_bare_e_resolve_origin_main(suporte):
    esp = suporte["esp"]
    assert os.path.isfile(os.path.join(esp, "HEAD"))
    assert ingerir.resolver_rev(esp, None) == suporte["main"]
    # refs/heads/* do clone --bare e fossil (arq:0074): o espelho so tem origin/* e tags
    r = subprocess.run([GIT, f"--git-dir={esp}", "for-each-ref", "refs/heads/"],
                       capture_output=True, text=True)
    assert r.stdout.strip() == ""
    assert casa._suporte.main_do_espelho(esp) == (suporte["main"], None)
    # a hora da ultima busca (FETCH_HEAD) e o que o `servido` declara: leitura nao busca
    assert casa._suporte.ultima_busca(esp)
    # segunda chamada: espelho existe, so busca
    ingerir.garantir_espelho(esp, suporte["forge"])
    assert ingerir.resolver_rev(esp, None) == suporte["main"]


def test_rev_tem_de_ser_ancestral_de_main(suporte):
    esp = suporte["esp"]
    assert ingerir.resolver_rev(esp, suporte["primeiro"]) == suporte["primeiro"]
    with pytest.raises(SystemExit) as e:
        ingerir.resolver_rev(esp, "origin/outro")
    assert e.value.code == 1
    with pytest.raises(SystemExit) as e:
        ingerir.resolver_rev(esp, "0" * 40)
    assert e.value.code == 1


def test_espelho_ausente_e_forge_fora_do_ar(tmp_path):
    esp = tmp_path / "x" / "platafirma-casa.git"
    assert casa._suporte.main_do_espelho(str(esp))[0] is None
    assert casa._suporte.ultima_busca(str(esp)) is None
    with pytest.raises(SystemExit) as e:
        ingerir.garantir_espelho(str(esp), str(tmp_path / "forge-que-nao-existe"))
    assert e.value.code == 1


def test_parse_fonte():
    assert ingerir.parse_fonte(None) == ("platafirma-casa", None)
    assert ingerir.parse_fonte("platafirma-casa@abc123") == ("platafirma-casa", "abc123")
    for ruim in ("platafirma-arquitetura", "platafirma-casa@-x", "platafirma-casa@a b"):
        with pytest.raises(SystemExit) as e:
            ingerir.parse_fonte(ruim)
        assert e.value.code == 2


def test_main_recusa_argumento_legado_sem_tocar_rede():
    for argv in (["--adr"], ["platafirma-arquitetura"], ["docs/lista.md"], ["--ate", "x"]):
        with pytest.raises(SystemExit) as e:
            ingerir.main(argv)
        assert e.value.code == 2


def test_base_e_token_vem_do_adaptador_rest():
    # HARNESS_DIR e a raiz do repo (bin/_acervo/ -> tres niveis), onde mora `recuperacao`:
    # com dois niveis o import do adaptador caia calado no default e ignorava MOTOR_ACERVO_URL.
    assert os.path.realpath(ingerir.HARNESS_DIR) == os.path.realpath(REPO)
    assert os.path.isfile(os.path.join(ingerir.HARNESS_DIR, "recuperacao", "adaptadores",
                                       "motor_acervo_rest.py"))
    assert ingerir.ORIGEM_BASE == "recuperacao.adaptadores.motor_acervo_rest"


# ------------------------------------------------------------------ árvore, corpo, payload (D5, D6)

def test_arvore_classifica_e_recusa_diagrama_sem_documento(suporte):
    arvore = ingerir.ler_arvore(suporte["esp"], suporte["main"])
    docs, diagramas, ignorados = ingerir.classificar(arvore)
    assert "README.md" in ignorados and "adr/org/.gitkeep" in ignorados
    assert "README.md" not in docs
    assert set(diagramas) == {"spec/acervo.1.mmd", "spec/figura.d2", "padrao/sem-doc.2.mmd",
                              "levantamento/2026-08-10-fluxos.10.mmd"}
    recusas = ingerir.recusas_diagrama(diagramas, arvore)
    assert {r["path"] for r in recusas} == {"spec/figura.d2", "padrao/sem-doc.2.mmd"}
    assert all("sem documento" in r["motivo"] for r in recusas)


def test_corpos_por_sha_e_titulo(suporte):
    esp, sha = suporte["esp"], suporte["main"]
    docs, _, _ = ingerir.classificar(ingerir.ler_arvore(esp, sha))
    corpos = ingerir.ler_corpos(esp, sha, docs)
    assert set(corpos) == set(docs)
    assert "Espécie: spec" in corpos["spec/acervo.md"]
    assert corpos["adr/arq/0001-primeira.md"] == ARVORE["adr/arq/0001-primeira.md"]
    itens = {i["path"]: i for i in ingerir.montar_itens(sha, docs, corpos)}
    assert itens["adr/arq/0001-primeira.md"]["titulo"] == "0001 — Primeira"
    assert itens["spec/acervo.md"]["titulo"] == "Acervo — espécie e chave"
    assert itens["nota-tecnica/2026-09-08-cerca.md"]["titulo"] == "Verdadeiro"
    assert itens["levantamento/2026-08-10-fluxos.md"]["titulo"] == "2026-08-10-fluxos"
    # rev antiga: a arvore e a do commit, nao a do main
    antigos, _, _ = ingerir.classificar(ingerir.ler_arvore(esp, suporte["primeiro"]))
    assert "spec/segunda.md" not in antigos and "spec/segunda.md" in docs


def test_payload_d6(suporte):
    sha = suporte["main"]
    itens = [{"repo": "platafirma-casa", "path": "spec/acervo.md", "sha_ref": sha,
              "titulo": "t", "corpo": "c"}]
    p = ingerir.montar_payload("dados", "rag", "vetor",
                               {"repo": "platafirma-casa", "sha": sha, "arvore_completa": True}, itens)
    assert set(p) == {"autor", "motor", "ate", "fonte", "itens"}
    assert p["fonte"] == {"repo": "platafirma-casa", "sha": sha, "arvore_completa": True}
    assert set(p["itens"][0]) == {"repo", "path", "sha_ref", "titulo", "corpo"}


# ------------------------------------------------------------------ plano (D10)

def test_plano_secoes_e_codigo_de_saida():
    lote = {"id": "L1", "autor": "dados", "motor": "rag", "ate": "vetor", "itens": [
        {"arquivo": "platafirma-casa@spec/a.md", "veredito": "criar", "portoes": []},
        {"arquivo": "platafirma-casa@runbook/b.md", "veredito": "edicao",
         "portoes": [{"portao": "estrato", "resultado": "aviso", "detail": "falta ## Rollback"}]},
        {"arquivo": "platafirma-casa@adr/arq/0094-x.md", "veredito": "reprovado", "casa_id": "u1",
         "portoes": [{"portao": "superseded", "resultado": "reprovado",
                      "detail": "Status: superseded por arq:0112"},
                     {"portao": "legado", "resultado": "aviso",
                      "detail": "legado mantido: adr/arq/0094-x.md segue servindo a versao anterior"}]},
        # recusado com casa_id de linha RETIRADA: o servidor nao emite `legado`; nao e legado
        {"arquivo": "platafirma-casa@spec/retirada.md", "veredito": "reprovado", "casa_id": "u2",
         "portoes": [{"portao": "sobre", "resultado": "reprovado", "detail": "Sobre: ausente"}]},
        # a palavra 'legado' no motivo nao faz legado: so o portao nomeado
        {"arquivo": "platafirma-casa@guia/legado-velho.md", "veredito": "reprovado",
         "portoes": [{"portao": "projecao", "resultado": "reprovado",
                      "detail": "caminho fora da projecao: guia/legado-velho.md"}]},
        {"arquivo": "platafirma-arquitetura@docs/velho.md", "veredito": "retirar",
         "classificacao": {"chave": "velho"}, "portoes": []},
        {"arquivo": "platafirma-casa@adr/arq/0093-y.md", "veredito": "retirar",
         "classificacao": {"chave": "arq:0093", "substituida_por": "arq:0112"}, "portoes": []},
    ]}
    fonte = {"repo": "platafirma-casa", "sha": "a" * 40, "arvore_completa": True,
             "espelho": "/esp", "docs": 5}
    rec = [{"path": "padrao/sem-doc.2.mmd", "motivo": "fonte de diagrama sem documento"}]
    txt = ingerir.plano(lote, fonte, rec, ["README.md"])
    assert "Resumo: total=7 | criar=1 | edicao=1 | reprovado=3 | retirar=2 | recusa_local=1" in txt
    assert "adr/arq/0094-x.md: superseded: Status: superseded por arq:0112" in txt
    assert "padrao/sem-doc.2.mmd: fonte de diagrama sem documento" in txt
    assert "runbook/b.md: estrato: falta ## Rollback" in txt
    assert "velho (platafirma-arquitetura@docs/velho.md) (sem sucessora declarada)" in txt
    assert "arq:0093 (platafirma-casa@adr/arq/0093-y.md) -> substituida por arq:0112" in txt
    # Avisos: so o estrato; o aviso `legado` tem secao propria e nao se repete
    avisos = txt.split("Avisos (", 1)[1].split("\n\n", 1)[0]
    assert avisos.startswith("1):") and "runbook/b.md" in avisos and "0094" not in avisos
    legado = txt.split("Legado mantido (", 1)[1].split("\n\n", 1)[0]
    assert "adr/arq/0094-x.md" in legado
    assert "spec/retirada.md" not in legado and "guia/legado-velho.md" not in legado
    assert ingerir._legado(lote["itens"][2]) and not ingerir._legado(lote["itens"][3])
    assert not ingerir._legado(lote["itens"][4])
    assert ingerir.tem_recusa(lote, [])
    assert ingerir.tem_recusa({"itens": []}, rec)
    assert not ingerir.tem_recusa({"itens": [{"veredito": "criar"}]}, [])


# ------------------------------------------------------------------ chave e leitura (D9)

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
    monkeypatch.setattr(casa, "ler", lambda e, s, j, situacao=False:
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
    assert out == ["arq:0094: retirada em 2026-09-24; substituída por arq:0112",
                   "  a vigente: acervo ler casa adr arq:0112"]
    # sem sucessora declarada: diz, e nao inventa a vigente
    sem_sucessora = dict(LINHA_RETIRADA, substituida_por=None)
    monkeypatch.setattr(casa, "_linhas", lambda where, limite=None: [sem_sucessora])
    assert casa.ler("adr", "arq:0094", False) == 0
    assert capsys.readouterr().out == "arq:0094: retirada em 2026-09-24; sem sucessora declarada\n"


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
    assert linha.endswith("(retirada em 2026-09-24; substituída por arq:0112)")
    assert casa.listar("adr", True, situacao=True, todas=True) == 0
    itens = {i["id"]: i for i in json.loads(capsys.readouterr().out)}
    assert itens["arq:0094"]["substituida_por"] == "arq:0112"
    assert itens["arq:0094"]["situacao"]["servido"].startswith("não servida")
    assert itens["arq:0112"]["situacao"]["servido"] == (
        "aaaaaaaaaaaa (= main do espelho, buscado em 2026-09-24 11:59Z)")


# ------------------------------------------------------------------ Sobre: e resolver (sem banco)

def test_sobre_so_aceita_classe_de_referente(monkeypatch, capsys):
    # conceito, adr, spec e parecer nao sao referente de Sobre: (arq:0115 §6.2); recusa sem banco
    monkeypatch.setattr(casa, "_q", lambda *a, **k: pytest.fail("nao consulta o banco"))
    for classe in ("conceito", "adr", "spec"):
        with pytest.raises(SystemExit) as e:
            casa._entidade(classe, "acervo")
        assert e.value.code == 2
        assert "nao e referente de Sobre:" in capsys.readouterr().err
    assert set(casa.CLASSES_SOBRE) == {"verbo", "capacidade", "stack", "instancia",
                                       "repositorio", "cadeira", "risco"}


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
    assert "PR → merge em main → acervo ingerir casa platafirma-casa" in r.stderr
    assert "release promover" not in r.stderr
    r = _acervo("ingerir", "casa", "platafirma-arquitetura")
    assert r.returncode == 2
    assert "platafirma-casa" in r.stderr
    r = _acervo("ingerir", "casa")
    assert r.returncode == 2
    assert "falta a entidade" in r.stderr


def test_cabecalho_do_verbo_aponta_o_suporte():
    with open(BIN, encoding="utf-8") as f:
        cab = "".join(f.readline() for _ in range(45))
    assert "# le: ingerir=repo" in cab
    assert "PLATAFIRMA_INSTANCIA" in cab and "platafirma-casa.git" in cab
    assert "PLATAFIRMA_RELEASE" not in cab
    assert 'SPEC="spec acervo (acervo ler casa spec acervo)"' in cab


def test_sem_caminho_fixo_de_platafirma_arquitetura():
    # D9: nada de caminho de platafirma-arquitetura no cliente de casa nem no despachante.
    for rel in ("bin/acervo", "bin/_acervo/casa", "bin/_acervo/casa-ingerir",
                "bin/_acervo/_identidade.py", "bin/_acervo/_suporte.py", "bin/_acervo/exportar"):
        with open(os.path.join(REPO, rel), encoding="utf-8") as f:
            txt = f.read()
        assert "platafirma-arquitetura" not in txt, rel
        assert "macro-global" not in txt, rel
        assert "padrao_path" not in txt, rel
