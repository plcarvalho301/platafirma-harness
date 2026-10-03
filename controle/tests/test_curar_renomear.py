"""#3239: `curar --conceito <slug> --renomear <slug-novo>` contra um servidor HTTP falso do contrato.

O servidor falso (http.server em thread, loopback) responde `PATCH /acervo/conceitos/{id}` como o
contrato `acervo-escrita.yaml` 1.2.0: 200 com o plano, 404 ConceitoNaoEncontrado, 409 ConceitoDuplicado.
`curar` roda num subprocesso do primeiro python que tenha `requests` (o venv de teste pode não ter),
carregado como módulo para que o export, que escreve no clone de conhecimento, se troque sem editar o
verbo. Em fixture: a lista de verificação (as palavras funcionais do D7) vem de um `acervo` falso em
PF_LINT_ACERVO; o texto que cita o slug velho, de uma release e de um espelho de platafirma-casa
montados em tmp; o gerador do HermiT, de um python falso que anota os argumentos.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CURAR = RAIZ / "bin" / "curar"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")

VELHO, NOVO, ID = "velho-slug", "novo-slug", "11111111-2222-3333-4444-555555555555"
BASE_ARGS = ("--conceito", VELHO, "--renomear", NOVO, "--motivo", "prova do #3239", "--autor", "dados")
CONFERENCIAS = ("ciclo", "categoria", "exclusividade", "ciclo_coluna", "rotulo_lingua")
PATCH_EXPORT = "m._repo_conhecimento = lambda: '/clone'\nm._exportar = lambda repo: 'bancada: export de teste'"

LISTA = (
    "força não declarada · vigente — lista-de-verificacao antipadroes-do-acervo · Antipadrões\n"
    "# Antipadrões do acervo\n\nEspécie: lista-de-verificacao\nRev: 6\n\n## Contrapontos\n\n"
    "- **D7 não conta palavra funcional:** de, da, do, to, be, the. Anglicismo passa.\n"
)


def plano(corpo, **over):
    """O que o servidor devolve: o plano da renomeação, como `rc.renomear_conceito` o monta."""
    p = {
        "modo": "aplicado" if corpo.get("aplicar") else "plano",
        "aprovado": True,
        "conceito": {"id": ID, "slug": corpo["slug"], "rotulo": "Rótulo Velho", "natureza": "modelo"},
        "slug": {"de": VELHO, "para": corpo["slug"]},
        "outros_rotulos": {"acrescenta": VELHO, "lingua": "zxx", "ja_era": None},
        "varredura": {"relacoes": 3, "obras": 5, "obras_vivas": 4, "filhos": 2,
                      "endereco": {"valor": None, "cita_o_slug": False}},
        "ficha": {"id": ID, "chave_humana": {"de": VELHO, "para": corpo["slug"]}, "alias": VELHO},
        "motivo": corpo["motivo"],
        "emitido_por": corpo["autor"],
        "conferencias": {n: {"antes": 0, "depois": 0, "novas": []} for n in CONFERENCIAS},
    }
    if corpo.get("aplicar"):
        p["id"] = ID
    p.update(over)
    return p


class Falso:
    def __init__(self):
        self.cenario = lambda corpo, caminho: (200, plano(corpo))
        self.chamadas = []   # (verbo, caminho, corpo)
        falso = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _resp(self, status, obj):
                dados = json.dumps(obj).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/problem+json" if status >= 400 else "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_PATCH(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
                falso.chamadas.append(("PATCH", self.path, corpo))
                self._resp(*falso.cenario(corpo, self.path))

            def do_GET(self):
                falso.chamadas.append(("GET", self.path, None))
                self._resp(200, {"itens": []})

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def fecha(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def patches(self):
        return [c for c in self.chamadas if c[0] == "PATCH"]


@pytest.fixture
def falso():
    f = Falso()
    yield f
    f.fecha()


@pytest.fixture
def ambiente(tmp_path, falso):
    """Env do subprocesso: API falsa, lista falsa, release e espelho de casa em tmp."""
    lista = tmp_path / "lista.md"
    lista.write_text(LISTA, encoding="utf-8")
    acervo = tmp_path / "acervo"
    acervo.write_text("#!/bin/sh\n"
                      '[ "$1 $2 $3 $4" = "ler casa lista-de-verificacao antipadroes-do-acervo" ] '
                      f"&& exec cat {shlex.quote(str(lista))}\nexit 1\n")
    acervo.chmod(0o755)
    release = tmp_path / "release"
    (release / "harness").mkdir(parents=True)
    (release / "harness" / "doc.md").write_text(f"linha um\nuso do conceito {VELHO} aqui\n", encoding="utf-8")
    # colado a hífen, letra ou dígito não é o slug (`tool` não é `tool-use`)
    (release / "harness" / "ruido.md").write_text(f"{VELHO}-extra e meu-{VELHO} e {VELHO}x\n", encoding="utf-8")
    export = release / "conhecimento" / "ontologia" / "acervo"
    export.mkdir(parents=True)
    (export / "conceito.jsonl").write_text(f'{{"slug": "{VELHO}"}}\n', encoding="utf-8")   # o export: fora
    (release / "venv" / "lib").mkdir(parents=True)
    (release / "venv" / "lib" / "x.py").write_text(f"{VELHO}\n", encoding="utf-8")        # ambiente: fora
    env = {**os.environ,
           "MOTOR_ACERVO_URL": falso.url, "RAG_API_TOKEN": "t",
           "PF_LINT_ACERVO": str(acervo),
           "PLATAFIRMA_RELEASE": str(release), "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
           "PF_SUPORTE_ESPELHO": str(tmp_path / "sem-espelho.git"),
           "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1", "HOME": str(tmp_path)}
    for k in ("PF_PROJECAO_PYTHON", "PF_CONHECIMENTO_DIR", "PF_CADEIRA", "PF_CONTA",
              "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    return env


def _curar(env, *argv, patches=""):
    codigo = (
        "import importlib.machinery, importlib.util, sys\n"
        f"loader = importlib.machinery.SourceFileLoader('curar_teste', {str(CURAR)!r})\n"
        "spec = importlib.util.spec_from_loader('curar_teste', loader)\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "loader.exec_module(m)\n"
        f"{patches}\n"
        f"sys.exit(m.main({list(argv)!r}))\n")
    return subprocess.run([PY, "-c", codigo], capture_output=True, text=True, env=env, timeout=120)


# ------------------------------------------------------------------ plano seco

def test_plano_seco_mostra_slug_outros_rotulos_varredura_conferencias_e_veredito(ambiente, falso):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    s = p.stdout
    assert f"slug: {VELHO} -> {NOVO}" in s
    assert f"outros_rotulos: + {VELHO}  (termo de entrada, língua zxx)" in s
    assert f"ficha na raiz : chave_humana {VELHO} -> {NOVO}; alias + {VELHO}" in s
    # quem aponta, no banco, com a contagem de cada
    assert "relações em conceito_relacao : 3" in s
    assert "obras em obra_trata_de       : 5 (vivas 4)" in s
    assert "filhos por mais_amplo_id     : 2" in s
    # quem cita o slug velho por nome, fora do banco: só a palavra inteira, fora o export e o venv
    assert "harness: 1 arquivo(s), 1 linha(s) — doc.md:2" in s
    assert "conceito.jsonl" not in s and "ruido.md" not in s and "x.py" not in s
    assert "não varrido: platafirma-casa (espelho, origin/main) (espelho ausente" in s
    assert "conferência D7 (slug novo): OK" in s and "conferência D8 (slug novo): OK" in s
    assert all(f"conferência {n}" in s for n in CONFERENCIAS)
    assert "HermiT: pulado (--sem-hermit)" in s
    assert "veredito: APROVADO — repita com --apply para gravar" in s
    # uma chamada só, plano seco, pela rota do documento (arq:0090), sem nome de ação
    assert falso.chamadas == [("PATCH", f"/acervo/conceitos/{VELHO}",
                               {"slug": NOVO, "motivo": "prova do #3239", "autor": "dados", "aplicar": False})]


def test_plano_seco_em_json(ambiente):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--json")
    assert p.returncode == 0, p.stdout + p.stderr
    d = json.loads(p.stdout)
    assert set(d) == {"plano", "conferencia_slug", "varredura_texto", "hermit", "aprovado"}
    assert d["aprovado"] is True and d["plano"]["slug"] == {"de": VELHO, "para": NOVO}
    assert d["conferencia_slug"]["D7"]["estado"] == "ok"
    assert d["varredura_texto"]["repos"]["harness"]["exemplos"] == ["doc.md:2"]


def test_varredura_acha_o_slug_no_espelho_de_platafirma_casa(ambiente, tmp_path):
    if not shutil.which("git"):
        pytest.skip("sem git")
    trabalho = tmp_path / "trabalho"
    trabalho.mkdir()

    def git(*a, cwd):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True,
                       capture_output=True)

    git("init", "-q", cwd=trabalho)
    (trabalho / "guia").mkdir()
    (trabalho / "guia" / "g.md").write_text(f"um\ndois\nlê {VELHO}\n", encoding="utf-8")
    git("add", "-A", cwd=trabalho)
    git("commit", "-qm", "c", cwd=trabalho)
    espelho = tmp_path / "espelho.git"
    subprocess.run(["git", "init", "--bare", "-q", str(espelho)], check=True, capture_output=True)
    git("push", "-q", str(espelho), "HEAD:refs/remotes/origin/main", cwd=trabalho)
    p = _curar({**ambiente, "PF_SUPORTE_ESPELHO": str(espelho)}, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "platafirma-casa (espelho, origin/main): 1 arquivo(s), 1 linha(s) — guia/g.md:3" in p.stdout


# ------------------------------------------------------------------ forma do slug novo (D7, D8)

def test_d7_reprova_slug_novo_com_mais_de_tres_partes_e_o_plano_nao_aprova(ambiente, falso):
    p = _curar(ambiente, "--conceito", VELHO, "--renomear", "uma-duas-tres-quatro-cinco", "--motivo", "m",
               "--autor", "dados", "--sem-hermit")
    assert p.returncode == 1, p.stdout + p.stderr
    assert ("conferência D7 (slug novo): REPROVA — 5 partes fora das palavras funcionais "
            "(uma, duas, tres, quatro, cinco); o teto é três") in p.stdout
    assert "veredito: REPROVADO — nada gravado" in p.stdout


@pytest.mark.parametrize("novo,sai", [
    ("indice-de-maturidade-de-governanca", 0),         # três partes fora das funcionais: passa
    ("job-to-be-done", 0),                             # to, be, done: só `job` e `done` contam
    ("indice-de-maturidade-de-governanca-digital", 1),  # quatro: reprova
])
def test_d7_nao_conta_palavra_funcional_da_lista(ambiente, novo, sai):
    p = _curar(ambiente, "--conceito", VELHO, "--renomear", novo, "--motivo", "m", "--autor", "dados",
               "--sem-hermit")
    assert p.returncode == sai, p.stdout + p.stderr
    assert ("conferência D7 (slug novo): OK" in p.stdout) is (sai == 0)


def test_d8_reprova_slug_tese(ambiente):
    p = _curar(ambiente, "--conceito", VELHO, "--renomear", "dado-vs-informacao", "--motivo", "m",
               "--autor", "dados", "--sem-hermit")
    assert p.returncode == 1, p.stdout + p.stderr
    assert "conferência D8 (slug novo): REPROVA — slug contém `-vs-`" in p.stdout
    assert "conferência D7 (slug novo): OK" in p.stdout


def test_lista_que_nao_se_resolve_deixa_o_d7_indeterminavel_e_o_apply_recusa(ambiente, falso, tmp_path):
    env = {**ambiente, "PF_LINT_ACERVO": str(tmp_path / "acervo-que-nao-existe")}
    p = _curar(env, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 1
    assert "conferência D7 (slug novo): INDETERMINÁVEL — a lista antipadroes-do-acervo não se resolveu" in p.stdout
    assert "conferência D8 (slug novo): OK" in p.stdout
    p = _curar(env, *BASE_ARGS, "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 1
    assert "a forma do slug novo reprova (D7/D8) ou não se mediu; nada gravado" in p.stderr
    assert [c[2]["aplicar"] for c in falso.patches()] == [False, False]   # nada de aplicar: True


# ------------------------------------------------------------------ HermiT

def _hermit_falso(tmp_path, ambiente, depois=(), sai=0, antes=()):
    arvore = Path(ambiente["PLATAFIRMA_RELEASE"]) / "conhecimento" / "ontologia" / "projecao"
    arvore.mkdir(parents=True, exist_ok=True)
    (arvore / "gerar-e-raciocinar.py").write_text("# o falso nao le o script\n", encoding="utf-8")
    anotados = tmp_path / "args.txt"
    py = tmp_path / "py-falso"
    py.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "$PF_TESTE_ARGS"\n'
        f'case "$*" in *--renomear*) [ {sai} -eq 0 ] || {{ echo "unrecognized arguments" >&2; exit {sai}; }}\n'
        f"  echo '{json.dumps({'insatisfaziveis': list(depois), 'triplas': 11})}' ;;\n"
        f"*) echo '{json.dumps({'insatisfaziveis': list(antes), 'triplas': 10})}' ;; esac\n")
    py.chmod(0o755)
    return {**ambiente, "PF_PROJECAO_PYTHON": str(py), "PF_TESTE_ARGS": str(anotados)}, anotados


def test_hermit_projeta_a_base_e_a_base_renomeada_e_compara(ambiente, tmp_path):
    env, anotados = _hermit_falso(tmp_path, ambiente)
    p = _curar(env, *BASE_ARGS)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "HermiT insatisfazíveis 0 -> 0  OK" in p.stdout
    assert "veredito: APROVADO" in p.stdout
    chamadas = anotados.read_text(encoding="utf-8").splitlines()
    assert len(chamadas) == 2
    assert "--renomear" not in chamadas[0]
    assert chamadas[1].endswith(f"--renomear {VELHO}:{NOVO}")


def test_hermit_que_ganha_insatisfazivel_reprova_o_plano(ambiente, tmp_path):
    env, _ = _hermit_falso(tmp_path, ambiente, depois=["classe-x"])
    p = _curar(env, *BASE_ARGS)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "HermiT insatisfazíveis 0 -> 1  REPROVA +1  novos: classe-x" in p.stdout
    assert "veredito: REPROVADO — nada gravado" in p.stdout


def test_gerador_no_ar_sem_a_opcao_renomear_falha_seguro(ambiente, falso, tmp_path):
    """Antes do `release promover platafirma-conhecimento` o gerador não conhece `--renomear`."""
    env, _ = _hermit_falso(tmp_path, ambiente, sai=2)
    p = _curar(env, *BASE_ARGS)
    assert p.returncode == 1
    assert "HermiT: falhou" in p.stdout and "unrecognized arguments" in p.stdout
    p = _curar(env, *BASE_ARGS, "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 1
    assert "HermiT não rodou; para gravar mesmo assim passe --sem-hermit" in p.stderr
    assert [c[2]["aplicar"] for c in falso.patches()] == [False, False]


# ------------------------------------------------------------------ --apply

def test_apply_aprovado_grava_exporta_e_diz_o_id(ambiente, falso):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 0, p.stdout + p.stderr
    assert f"Renomeação aplicada: {VELHO} -> {NOVO}" in p.stdout
    assert f"id     : {ID}   (o id do conceito não muda)" in p.stdout
    assert "export : regenerado no clone" in p.stdout and "bancada: export de teste" in p.stdout
    assert [c[2]["aplicar"] for c in falso.patches()] == [False, True]


def test_apply_nao_grava_se_a_conferencia_do_servidor_reprova(ambiente, falso):
    falso.cenario = lambda corpo, caminho: (200, plano(corpo, aprovado=False))
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 1
    assert "conferência SQL reprovou; nada gravado" in p.stderr
    assert [c[2]["aplicar"] for c in falso.patches()] == [False]


def test_apply_nao_grava_se_a_forma_do_slug_reprova(ambiente, falso):
    p = _curar(ambiente, "--conceito", VELHO, "--renomear", "dado-vs-informacao", "--motivo", "m", "--autor",
               "dados", "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 1
    assert [c[2]["aplicar"] for c in falso.patches()] == [False]


# ------------------------------------------------------------------ o que o servidor recusa

def test_slug_novo_que_ja_existe_sai_1_com_conceito_duplicado_e_o_id(ambiente, falso):
    falso.cenario = lambda corpo, caminho: (409, {"type": "about:blank", "title": "ConceitoDuplicado",
                                                  "detail": f"conceito '{NOVO}' já existe (existente-uuid)"})
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 1
    assert "ConceitoDuplicado" in p.stdout and "existente-uuid" in p.stdout


def test_slug_velho_que_nao_existe_sai_1_com_conceito_nao_encontrado(ambiente, falso):
    falso.cenario = lambda corpo, caminho: (404, {"type": "about:blank", "title": "ConceitoNaoEncontrado",
                                                  "detail": VELHO})
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 1
    assert "ConceitoNaoEncontrado" in p.stdout


# ------------------------------------------------------------------ uso errado e a trava do card

@pytest.mark.parametrize("argv,trecho", [
    (("--conceito", VELHO, "--renomear", NOVO, "--autor", "dados"), "renomear exige --motivo"),
    (("--conceito", VELHO, "--renomear", "", "--motivo", "m"), "--renomear exige o slug novo"),
    (("--renomear", NOVO, "--motivo", "m"), "--renomear acompanha --conceito"),
    (("--conceito", VELHO, "--renomear", NOVO, "--motivo", "m", "--pai", "outro"), "não combina com --pai"),
    (("--conceito", VELHO, "--renomear", NOVO, "--motivo", "m", "--rotulo", "R", "--tipo", "generica"),
     "não combina com --rotulo --tipo"),
])
def test_uso_errado_sai_2_sem_chamar_a_api(argv, trecho, ambiente, falso):
    p = _curar(ambiente, *argv)
    assert p.returncode == 2, p.stdout + p.stderr
    assert trecho in p.stderr
    assert falso.chamadas == []


def test_trocar_pai_segue_pela_rota_do_pai_e_nao_pela_do_documento(ambiente, falso):
    """Trava do card: `--conceito` sem `--renomear` não mudou."""
    falso.cenario = lambda corpo, caminho: (200, {
        "modo": "plano", "aprovado": True, "emitido_por": "dados", "molde": "",
        "aresta": {"de": "x", "para": "y", "tipo": "generica", "familia": "hierarquica",
                   "garantia": "instituida", "motivo": "m"},
        "conferencias": {}})
    p = _curar(ambiente, "--conceito", "x", "--pai", "y", "--tipo", "generica", "--garantia", "instituida",
               "--motivo", "m", "--autor", "dados", "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    assert ("GET", "/acervo/conceitos/x/relacoes", None) in falso.chamadas
    assert [c[1] for c in falso.patches()] == ["/acervo/conceitos/x/pai"]


def test_help_do_verbo_lista_o_renomear(ambiente):
    p = _curar(ambiente, "--help")
    assert p.returncode == 0
    assert "--renomear <slug-novo>" in p.stdout


@pytest.mark.parametrize("extra", [
    ("--recortar", "obra-x"),
    ("--reextrair", "obra-x"),
    ("--lote",),
    ("--bancada", "/tmp/x"),
    ("--medida",),
    ("--promover", "obra-x"),
    ("--impressao", "imp-1"),
    ("--obra", "obra-x"),
    ("--trata-de", "outro"),
    ("--expurgar",),
    ("--relacionar",),
])
def test_opcao_de_outro_ato_junto_do_renomear_sai_2_antes_de_despachar(ambiente, falso, extra):
    """Sem a recusa o `main` entregaria o pedido ao outro ato e o --renomear sumiria calado."""
    p = _curar(ambiente, "--conceito", VELHO, "--renomear", NOVO, "--motivo", "m", "--autor", "dados", *extra)
    assert p.returncode == 2, p.stdout + p.stderr
    assert f"não combina com {extra[0]}" in p.stderr
    assert falso.chamadas == []


# ------------------------------------------------------------------ o que o --apply faz depois de gravar

def test_apply_roda_o_export_mesmo_sem_clone_de_conhecimento_declarado(ambiente):
    """`_exportar` delega a `acervo exportar`: não depende de PF_CONHECIMENTO_DIR nem do HermiT."""
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply",
               patches="m._exportar = lambda repo: 'bancada: export de teste'")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "export : regenerado no clone" in p.stdout and "bancada: export de teste" in p.stdout


def test_apply_com_export_que_falha_diz_que_ja_renomeou_e_sai_1(ambiente, falso):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply",
               patches="m._exportar = lambda repo: 'acervo exportar falhou: boom'")
    assert p.returncode == 1, p.stdout + p.stderr
    assert "export : NÃO regenerado (acervo exportar falhou: boom)" in p.stdout
    assert "o slug JÁ foi renomeado: não repita o --apply" in p.stdout
    assert "export : regenerado" not in p.stdout
    assert [c[2]["aplicar"] for c in falso.patches()] == [False, True]


def test_apply_em_json_traz_o_aplicado_o_export_e_se_o_export_deu_certo(ambiente):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply", "--json", patches=PATCH_EXPORT)
    assert p.returncode == 0, p.stdout + p.stderr
    d = json.loads(p.stdout)
    assert set(d) == {"aplicado", "conferencia_slug", "varredura_texto", "hermit", "export", "export_ok"}
    assert d["aplicado"]["modo"] == "aplicado" and d["aplicado"]["id"] == ID
    assert d["export_ok"] is True and d["export"] == "bancada: export de teste"


def test_apply_reprovado_em_json_sai_json_e_nao_grava(ambiente, falso):
    falso.cenario = lambda corpo, caminho: (200, plano(corpo, aprovado=False))
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", "--apply", "--json", patches=PATCH_EXPORT)
    assert p.returncode == 1, p.stdout + p.stderr
    d = json.loads(p.stdout)
    assert d["aprovado"] is False and d["plano"]["aprovado"] is False
    assert [c[2]["aplicar"] for c in falso.patches()] == [False]


def test_plano_recusado_pela_api_diz_que_o_hermit_nao_rodou_e_nao_que_foi_pulado(ambiente, falso):
    falso.cenario = lambda corpo, caminho: (422, {
        "type": "about:blank", "title": "RelacaoReprovada", "detail": "conferência reprovou: ciclo +1",
        "plano": plano(corpo, aprovado=False)})
    p = _curar(ambiente, *BASE_ARGS)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "HermiT: não rodou (a API recusou o plano antes)" in p.stdout
    assert "pulado" not in p.stdout


# ------------------------------------------------------------------ a varredura do texto, nos cantos

def test_slug_com_ponto_casa_o_ponto_literal_e_nao_um_caractere_qualquer(ambiente):
    (Path(ambiente["PLATAFIRMA_RELEASE"]) / "harness" / "ponto.md").write_text(
        "usa a.b aqui\nusa aXb aqui\n", encoding="utf-8")
    p = _curar(ambiente, "--conceito", "a.b", "--renomear", NOVO, "--motivo", "m", "--autor", "dados",
               "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "harness: 1 arquivo(s), 1 linha(s) — ponto.md:1" in p.stdout


def test_diretorio_de_repo_que_e_atalho_e_varrido_e_atalho_interno_nao_e_seguido(ambiente, tmp_path):
    release = Path(ambiente["PLATAFIRMA_RELEASE"])
    real = tmp_path / "real-repo"
    real.mkdir()
    (real / "a.md").write_text(f"cita {VELHO}\n", encoding="utf-8")
    fora = tmp_path / "fora"
    fora.mkdir()
    (fora / "b.md").write_text(f"cita {VELHO}\n", encoding="utf-8")
    (real / "link-para-fora").symlink_to(fora)
    (release / "atalho").symlink_to(real)
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "atalho: 1 arquivo(s), 1 linha(s) — a.md:1" in p.stdout
    assert "b.md" not in p.stdout


@pytest.mark.skipif(os.geteuid() == 0, reason="root lê o diretório fechado")
def test_grep_que_sai_2_fica_como_nao_varrido_e_nao_como_nenhuma_ocorrencia(ambiente):
    fechado = Path(ambiente["PLATAFIRMA_RELEASE"]) / "harness" / "fechado"
    fechado.mkdir()
    (fechado / "x.md").write_text(f"{VELHO}\n", encoding="utf-8")
    fechado.chmod(0)
    try:
        p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    finally:
        fechado.chmod(0o755)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "não varrido: harness (grep saiu 2" in p.stdout


def test_varredura_que_passa_do_tempo_fica_como_nao_varrida(ambiente):
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit", patches="m._VARREDURA_TIMEOUT_S = 0.0001")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "não varrido: harness (passou de 0.0001 s)" in p.stdout
    assert "nenhuma ocorrência" not in p.stdout


def test_vocabulario_derivado_do_export_fica_fora_da_varredura(ambiente):
    voc = Path(ambiente["PLATAFIRMA_RELEASE"]) / "harness" / "rag" / "docs" / "ontologia"
    voc.mkdir(parents=True)
    (voc / "vocabulario.json").write_text(f'{{"subdominios": ["{VELHO}"]}}\n', encoding="utf-8")
    p = _curar(ambiente, *BASE_ARGS, "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "vocabulario.json" not in p.stdout
    assert "harness: 1 arquivo(s), 1 linha(s) — doc.md:2" in p.stdout


# ------------------------------------------------------------------ HermiT: quem já era insatisfazível

@pytest.mark.parametrize("velho,nome_velho", [(VELHO, VELHO), ("a.b", "a_b")])
def test_conceito_que_ja_era_insatisfazivel_nao_conta_como_novo_ao_ser_renomeado(ambiente, tmp_path, velho, nome_velho):
    """A classe volta com o nome novo (o IRI troca `.` por `_`): é a mesma, não um insatisfazível da troca."""
    env, _ = _hermit_falso(tmp_path, ambiente, antes=[nome_velho], depois=[NOVO])
    p = _curar(env, "--conceito", velho, "--renomear", NOVO, "--motivo", "m", "--autor", "dados")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "HermiT insatisfazíveis 1 -> 1  OK" in p.stdout


def test_insatisfazivel_de_outro_conceito_que_surge_na_troca_continua_reprovando(ambiente, tmp_path):
    env, _ = _hermit_falso(tmp_path, ambiente, antes=[VELHO], depois=[NOVO, "outra-classe"])
    p = _curar(env, *BASE_ARGS)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "HermiT insatisfazíveis 1 -> 2  REPROVA +1  novos: outra-classe" in p.stdout
