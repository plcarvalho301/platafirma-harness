# componente: componente:verbo-tarefas
"""O ponteiro do processo do estágio no retorno do `tarefas mover` (story #4359).

O que a casa decidiu: o catálogo liga o processo ao estado que ele conduz (propriedade `conduz` da
ficha, valores `<nivel>:<estado>`); o `mover` de sucesso imprime, depois do pai e das irmãs, uma linha
«  processo do estágio: <chave> — leia <caminho>» por processo ligado; o ponteiro informa e não barra,
então toda falha da consulta ao catálogo some calada (sem linha, sem stderr, mesmo código de saída).

PROVA: roda o `bin/tarefas` de verdade, com `bash`, contra um rastreador de mentira em loopback
(`TAREFAS_BASE`) e um `infra` de mentira (`PF_INFRA_BIN`) que serve o catálogo no formato do
`infra rodar ontologia -- ... --json`; confere o que o verbo imprime, o código de saída e o stderr.
NÃO PROVA: o catálogo nem a Olaria de verdade (isso é o `ler` de cada ficha, na task da Olaria),
nem o tempo real de uma chamada ao `infra` (o teto é provado com um `infra` lento de mentira).
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

# a raiz do harness: a pasta acima que tem bin/tarefas
VERBO = next(p / "bin" / "tarefas" for p in Path(__file__).resolve().parents if (p / "bin" / "tarefas").exists())

LINHA_REFINAR = "  processo do estágio: procedimento:refinar-story — leia instancias/procedimento/refinar-story.md"

CATALOGO = {
    "fichas": {
        "processo": "classe: processo\nfichas: []\n",
        "ciclo": "classe: ciclo\nfichas: []\n",
        "exploracao": "classe: exploracao\nfichas: []\n",
        "missao": (
            "classe: missao\nfichas:\n"
            "- chave: missao:executar-a-story-de-codigo\n  dados:\n    conduz: story:em-execucao\n"
            "  ligacoes:\n    produz: capacidade:desenvolvimento\n"
            "- chave: missao:lapidar-um-card\n  dados:\n    conduz:\n    - épico:em-lapidacao\n"
            "    - feature:em-lapidacao\n  ligacoes:\n    produz: capacidade:tarefas\n"
            "- chave: missao:trabalhar-um-pedido\n  dados:\n    entrega: rotina\n"
            "  ligacoes:\n    produz: capacidade:tarefas\n"
        ),
        "procedimento": (
            "classe: procedimento\nfichas:\n"
            "- chave: procedimento:refinar-story\n  dados:\n    conduz: story:em-refinamento-tecnico\n"
            "  ligacoes:\n    chama: procedimento:recuperar-a-bancada\n"
            "- chave: procedimento:revisar-uma-entrega\n  dados:\n    conduz: story:em-homologacao\n"
            "    entrega: rotina\n"
            "- chave: procedimento:integrar-os-pareceres\n  dados:\n    conduz:\n    - épico:em-parecer\n"
            "    - feature:em-parecer\n"
            "- chave: procedimento:formalizar-uma-feature\n  dados:\n    conduz: feature:priorizada\n"
            "- chave: procedimento:outro-na-lapidacao\n  dados:\n    conduz: 'feature:em-lapidacao'\n"
        ),
    },
    "shapes": {
        "processo": ("classes:\n- slug: processo\n  restricoes:\n  - propriedade: chama\n"
                     "    tipo_de_valor: ligacao\n  referencia:\n"
                     "    endereco: referencias/instancias/processo/<slug>.md\n"),
        "missao": ("classes:\n- slug: missao\n  restricoes:\n  - propriedade: chama\n"
                   "    tipo_de_valor: ligacao\n  golden:\n    tipo: casa\n"
                   "    endereco: instancias/missao/<slug>.md\n    regime: vivo\n"),
        "procedimento": ("classes:\n- slug: procedimento\n  restricoes:\n  - propriedade: chama\n"
                         "    tipo_de_valor: ligacao\n  golden:\n    tipo: casa\n"
                         "    endereco: instancias/procedimento/<slug>.md\n    regime: vivo\n"),
    },
}

INFRA_FALSO = """#!{python}
import json, os, subprocess, sys, time
aqui = os.path.dirname(os.path.abspath(__file__))
dados = json.load(open(os.path.join(aqui, "catalogo.json")))
a = sys.argv[1:]
open(os.path.join(aqui, "chamadas.log"), "a").write(" ".join(a) + "\\n")
# o infra de verdade (bin/infra, exigir_sujeito) sai 3 sem PF_SUJEITO; o fake faz o mesmo
if not os.environ.get("PF_SUJEITO"):
    print("infra: erro: variavel PF_SUJEITO: ausente", file=sys.stderr)
    sys.exit(3)
# o infra de verdade passa a vez a um python que lanca outro: o neto que o teto tem de matar
if os.environ.get("FAKE_NETO"):
    neto = subprocess.Popen(["sleep", "60"])
    open(os.environ["FAKE_NETO"], "w").write(str(neto.pid))
if os.environ.get("FAKE_DEMORA"):
    time.sleep(float(os.environ["FAKE_DEMORA"]))
if os.environ.get("FAKE_FALHA"):
    sys.exit(int(os.environ["FAKE_FALHA"]))
if os.environ.get("FAKE_LIXO"):
    print("isto não é json")
    sys.exit(0)
assert a[:3] == ["rodar", "ontologia", "--"], a
a = a[3:]
if a[:4] == ["listar", "shape", "--filhas", "processo"]:
    print(json.dumps({{"estado": "fez", "classe": "shape", "chaves": ["ciclo", "exploracao", "missao", "procedimento"]}}))
elif a[:2] == ["ler", "shape"]:
    print(json.dumps({{"estado": "fez", "classe": "shape", "yaml": dados["shapes"][a[2]]}}))
elif len(a) >= 3 and a[0] == "ler" and a[2] == "--fichas":
    print(json.dumps({{"estado": "fez", "classe": a[1], "yaml": dados["fichas"][a[1]]}}))
else:
    sys.exit(2)
"""


class Servidor:
    """Responde pela tabela {(método, caminho): (status, json)} e guarda o que chegou."""

    def __init__(self):
        self.rotas, self.recebido = {}, []
        dono = self

        class H(BaseHTTPRequestHandler):
            def _responde(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = self.rfile.read(n).decode() if n else ""
                dono.recebido.append({"metodo": self.command, "caminho": self.path.split("?")[0], "corpo": corpo})
                status, payload = dono.rotas.get((self.command, self.path.split("?")[0]),
                                                 (404, {"erro": "rota que o teste não conhece"}))
                bruto = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(bruto)))
                self.end_headers()
                self.wfile.write(bruto)

            do_GET = do_POST = do_PATCH = do_DELETE = _responde

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_port}/api"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def fecha(self):
        self.httpd.shutdown()


@pytest.fixture
def api():
    s = Servidor()
    s.rotas[("GET", "/api/registro")] = (200, {"estados": []})
    yield s
    s.fecha()


@pytest.fixture
def infra(tmp_path):
    pasta = tmp_path / "infra-falso"
    pasta.mkdir()
    (pasta / "catalogo.json").write_text(json.dumps(CATALOGO), encoding="utf-8")
    exe = pasta / "infra"
    exe.write_text(INFRA_FALSO.format(python=sys.executable), encoding="utf-8")
    exe.chmod(0o755)
    return exe


def mover(api, infra, destino, *, tmp_path, item=5000, extra=None):
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "TAREFAS_BASE": api.base,
           "PF_CADEIRA": "engenharia", "XDG_RUNTIME_DIR": str(tmp_path), "TMPDIR": str(tmp_path),
           "PF_INFRA_BIN": str(infra), "PF_SUJEITO": "sujeito-de-teste"}
    env.update(extra or {})
    return subprocess.run(["bash", str(VERBO), "mover", str(item), destino], env=env,
                          capture_output=True, text=True, timeout=60)


def movido(nivel, estado, nome=None, **mais):
    return dict({"id": 5000, "chave": "5000", "titulo": "o card", "nivel_nome": nivel, "estado": estado,
                 "estado_nome": nome or estado, "pai": None, "estado_natureza": "ativo"}, **mais)


def chamadas(infra):
    arq = infra.parent / "chamadas.log"
    return arq.read_text(encoding="utf-8").splitlines() if arq.exists() else []


def test_a_story_que_vai_a_refinamento_traz_o_ponteiro_do_refinar_a_story(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "em-refinamento-tecnico",
                                                           "Em refinamento técnico"))
    r = mover(api, infra, "em-refinamento-tecnico", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    linhas = r.stdout.splitlines()
    assert linhas[0].startswith("item 5000 → Em refinamento técnico")
    assert linhas[-1] == LINHA_REFINAR
    assert r.stderr == ""


def test_um_processo_so_aparece_no_estado_e_no_nivel_que_ele_conduz(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "em-execucao", "Em execução"))
    r = mover(api, infra, "em-execucao", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == (
        "  processo do estágio: missao:executar-a-story-de-codigo — leia "
        "instancias/missao/executar-a-story-de-codigo.md")
    assert "refinar-story" not in r.stdout


def test_feature_e_epico_leem_o_valor_de_lista_e_o_nivel_acentuado(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("épico", "em-parecer", "Em parecer"))
    r = mover(api, infra, "em-parecer", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == (
        "  processo do estágio: procedimento:integrar-os-pareceres — leia "
        "instancias/procedimento/integrar-os-pareceres.md")
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("feature", "em-parecer", "Em parecer"))
    assert "integrar-os-pareceres" in mover(api, infra, "em-parecer", tmp_path=tmp_path).stdout


def test_o_mesmo_estado_conduzido_por_dois_processos_sai_em_duas_linhas_na_ordem_da_classe(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("feature", "em-lapidacao", "Em lapidação"))
    r = mover(api, infra, "em-lapidacao", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-2:] == [
        "  processo do estágio: missao:lapidar-um-card — leia instancias/missao/lapidar-um-card.md",
        "  processo do estágio: procedimento:outro-na-lapidacao — leia "
        "instancias/procedimento/outro-na-lapidacao.md"]


def test_estado_sem_processo_ligado_sai_como_hoje_sem_linha_nem_aviso(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "despriorizada", "Despriorizada"))
    r = mover(api, infra, "despriorizada", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "processo do estágio" not in r.stdout
    assert r.stdout.strip() == "item 5000 → Despriorizada: o card"
    assert r.stderr == ""


def test_a_recusa_do_mover_sai_1_sem_ponteiro_e_sem_consultar_o_catalogo(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (
        409, {"erro": "transição não permitida de em-refinamento-tecnico para em-homologacao",
              "destinos": ["em-execucao"]})
    r = mover(api, infra, "em-homologacao", tmp_path=tmp_path)
    assert r.returncode == 1
    assert "processo do estágio" not in r.stdout + r.stderr
    assert chamadas(infra) == []


def test_catalogo_que_falha_nao_muda_o_mover_nem_escreve_no_stderr(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "em-refinamento-tecnico",
                                                           "Em refinamento técnico"))
    for extra in ({"PF_INFRA_BIN": "/bin/false"}, {"FAKE_FALHA": "3"}, {"FAKE_FALHA": "5"}, {"FAKE_LIXO": "1"},
                  {"PF_INFRA_BIN": str(infra.parent / "nao-existe")}):
        r = mover(api, infra, "em-refinamento-tecnico", tmp_path=tmp_path, extra=extra)
        assert r.returncode == 0, (extra, r.stderr)
        assert r.stdout.strip() == "item 5000 → Em refinamento técnico: o card", extra
        assert r.stderr == "", extra


def test_o_teto_de_tempo_corta_a_consulta_lenta_sem_segurar_o_mover(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "em-refinamento-tecnico",
                                                           "Em refinamento técnico"))
    inicio = time.monotonic()
    r = mover(api, infra, "em-refinamento-tecnico", tmp_path=tmp_path,
              extra={"FAKE_DEMORA": "30", "PF_PONTEIRO_TETO": "1"})
    assert r.returncode == 0, r.stderr
    assert "processo do estágio" not in r.stdout and r.stderr == ""
    assert time.monotonic() - inicio < 15


def _vivo(pid):
    try:
        estado = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError):
        return False
    return estado != "Z"


def test_o_teto_mata_o_grupo_inteiro_e_nao_deixa_neto_orfao(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "em-refinamento-tecnico",
                                                           "Em refinamento técnico"))
    arq = tmp_path / "neto.pid"
    r = mover(api, infra, "em-refinamento-tecnico", tmp_path=tmp_path,
              extra={"FAKE_DEMORA": "30", "PF_PONTEIRO_TETO": "1", "FAKE_NETO": str(arq)})
    assert r.returncode == 0, r.stderr
    pid = int(arq.read_text())
    time.sleep(0.5)
    assert not _vivo(pid), "o neto do infra seguiu vivo depois do teto"


def test_sem_identidade_o_infra_recusa_e_o_ponteiro_some_calado(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, movido("story", "em-refinamento-tecnico",
                                                           "Em refinamento técnico"))
    r = mover(api, infra, "em-refinamento-tecnico", tmp_path=tmp_path, extra={"PF_SUJEITO": ""})
    assert r.returncode == 0, r.stderr
    assert "processo do estágio" not in r.stdout and r.stderr == ""


def test_sem_nivel_ou_estado_no_retorno_do_patch_o_verbo_le_o_detalhe_do_item(api, infra, tmp_path):
    api.rotas[("PATCH", "/api/itens/5000")] = (200, {"id": 5000, "titulo": "o card", "estado_nome": "x"})
    api.rotas[("GET", "/api/itens/5000")] = (200, movido("story", "em-refinamento-tecnico"))
    r = mover(api, infra, "em-refinamento-tecnico", tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == LINHA_REFINAR


def test_o_verbo_nao_guarda_tabela_de_estado_para_processo(api, infra, tmp_path):
    texto = VERBO.read_text(encoding="utf-8")
    assert "refinar-story" not in texto and "executar-a-story-de-codigo" not in texto
