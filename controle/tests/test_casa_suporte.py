# Contrato do cliente de casa sem banco e sem rede (arq:0115 §3, §7, §8.1, §11; contrato de
# dados D2/D5/D6/D9/D10): o espelho bare do suporte, a leitura por sha, o predicado 8
# (diagrama sem documento), o payload, o plano impresso e a forma da chave. Roda contra um
# forge LOCAL em tmp_path; nada toca rag_extractor nem o forge de verdade.
import importlib.machinery
import importlib.util
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
                      "detail": "Status: superseded por arq:0112"}]},
        {"arquivo": "platafirma-arquitetura@docs/velho.md", "veredito": "retirar",
         "classificacao": {"chave": "velho"}, "portoes": []},
    ]}
    fonte = {"repo": "platafirma-casa", "sha": "a" * 40, "arvore_completa": True,
             "espelho": "/esp", "docs": 3}
    rec = [{"path": "padrao/sem-doc.2.mmd", "motivo": "fonte de diagrama sem documento"}]
    txt = ingerir.plano(lote, fonte, rec, ["README.md"])
    assert "Resumo: total=4 | criar=1 | edicao=1 | reprovado=1 | retirar=1 | recusa_local=1" in txt
    assert "adr/arq/0094-x.md: superseded: Status: superseded por arq:0112" in txt
    assert "padrao/sem-doc.2.mmd: fonte de diagrama sem documento" in txt
    assert "runbook/b.md: estrato: falta ## Rollback" in txt
    assert "velho (platafirma-arquitetura@docs/velho.md) (sem sucessora declarada)" in txt
    assert "Legado mantido" in txt
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
    assert "= main do espelho" in casa.servido("platafirma-casa", f, ("a" * 40, None))
    assert "ingestão defasada" in casa.servido("platafirma-casa", f, ("b" * 40, None))
    assert "indeterminável" in casa.servido("platafirma-casa", f, (None, "espelho ausente"))
    assert casa.servido("platafirma-casa", None, ("a" * 40, None)) == "nunca ingerido"
    assert "fora do suporte" in casa.servido("platafirma-core", f, ("a" * 40, None))
    assert "(igual)" not in casa.servido("platafirma-casa", f, ("a" * 40, None))
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
                "bin/_acervo/_identidade.py", "bin/_acervo/_suporte.py"):
        with open(os.path.join(REPO, rel), encoding="utf-8") as f:
            txt = f.read()
        assert "platafirma-arquitetura" not in txt, rel
        assert "macro-global" not in txt, rel
        assert "padrao_path" not in txt, rel
