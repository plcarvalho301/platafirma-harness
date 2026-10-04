"""`agente` (card #3156): a declaração, a projeção, o portão da troca de modelo e o rodar.

Hermético: o posto é uma pasta temporária; `sessao` e `expediente` são dublês em PF_BIN; o ollama é um
servidor HTTP local; o CLI do claude é um script. O que se trava: o molde da declaração, a projeção gerada
byte a byte, os dois casos do §11.2 da spec agente e o §11.1 — sem pessoa resolvida, o modelo não é chamado.
"""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("agente", str(REPO_ROOT / "bin" / "agente"))
spec = importlib.util.spec_from_loader("agente", loader)
assert spec and spec.loader
agente = importlib.util.module_from_spec(spec)
loader.exec_module(agente)

ORQ = "11111111-1111-4111-8111-111111111111"     # a sessão de quem chamou
FILHA = "33333333-3333-4333-8333-333333333333"   # a que o dublê de `sessao abrir` cunha

REVISOR = {
    "slug": "revisor", "descricao": "Revisa código e devolve veredito na primeira linha.",
    "dono": {"cadeira": "engenharia", "chapeu": "devops"}, "modo": "revisar",
    "modelo": {"familia": "claude", "versao": "sonnet"}, "ligacoes": ["delegado", "agendado"],
    "ferramentas": ["Read", "Grep", "mcp__claudinho-mcp__ler_arquivo", "mcp__claudinho-mcp__monta_sessao"],
    "pernas": {"fonte_de_fora": False, "dado_pessoal": False, "muda_estado": False},
    "teto": {"turnos": 40, "tokens_execucao": 200000, "tokens_janela": 1000000},
    "fecho": {"comeca_com": "veredito: <0|1|5>", "termina_com": "o último achado", "recebe": "quem delegou"},
}
VARREDOR = {
    "slug": "varredor", "descricao": "Lê texto e separa recortes com âncora.",
    "dono": {"cadeira": "engenharia", "chapeu": "devops"}, "modo": "varrer",
    "modelo": {"familia": "qwen", "versao": "qwen3.5:9b", "local": True}, "ligacoes": ["consultado", "agendado"],
    "ferramentas": [],
    "pernas": {"fonte_de_fora": False, "dado_pessoal": False, "muda_estado": False},
    "teto": {"turnos": 1, "tokens_execucao": 14000, "tokens_janela": 200000, "num_ctx": 16384,
             "vram_max_mib": 12288, "prompt_eval_count_max": 13000},
    "fecho": {"comeca_com": "a lista de achados", "termina_com": "a última âncora", "recebe": "quem chamou"},
}
CONSULTOR = {**copy.deepcopy(REVISOR), "slug": "consultor", "modo": "consultar", "ligacoes": ["consultado"],
             "dono": {"cadeira": "{cadeira}"}}


def com(base: dict, **mudancas) -> dict:
    d = copy.deepcopy(base)
    for k, v in mudancas.items():
        d[k] = v
    return d


# --- o mundo de mentira -------------------------------------------------------------------------

STUB_SESSAO = """#!{py}
import json, os, sys
open(os.environ["STUB_LOG"], "a").write(json.dumps({{"verbo": "sessao", "argv": sys.argv[1:]}}) + "\\n")
if sys.argv[1] == "abrir":
    if os.environ.get("STUB_SESSAO_EXIT"):
        print(json.dumps({{"erro": "nao autorizado"}}))
        sys.exit(int(os.environ["STUB_SESSAO_EXIT"]))
    print(json.dumps({{"sessao_id": "{filha}", "ordem_id": "o-filha"}}))
"""
STUB_EXPEDIENTE = """#!{py}
import json, os, sys
open(os.environ["STUB_LOG"], "a").write(json.dumps({{"verbo": "expediente", "argv": sys.argv[1:],
    "stdin": sys.stdin.read(), "env": {{k: os.environ.get(k) for k in ("PF_CADEIRA", "PF_SESSAO", "PF_ORIGEM_SESSAO")}}}}) + "\\n")
if os.environ.get("STUB_EXPEDIENTE_EXIT"):
    print(json.dumps({{"erro": "modo 'varrer' sem documento na casa"}}))
    sys.exit(int(os.environ["STUB_EXPEDIENTE_EXIT"]))
print(json.dumps({{"pecas": [{{"peca": "persona", "conteudo": "LENTE-PERSONA"}}, {{"peca": "modo", "conteudo": "LENTE-MODO"}},
                              {{"peca": "mesa", "conteudo": None}}]}}))
"""
STUB_ACERVO = """#!{py}
import json
print(json.dumps([{{"tool": "acervo"}}, {{"tool": "repo"}}, {{"tool": "motor"}}]))
"""
STUB_CLAUDE = """#!{py}
import json, os, sys
open(os.environ["STUB_LOG"], "a").write(json.dumps({{"verbo": "claude", "argv": sys.argv[1:], "stdin": sys.stdin.read()}}) + "\\n")
print(json.dumps({{"type": "result", "is_error": False, "result": "veredito: 0 — x@y", "num_turns": 3,
                   "usage": {{"input_tokens": 100, "cache_creation_input_tokens": 50,
                   "cache_read_input_tokens": 1000, "output_tokens": 20}}}}))
"""


def _stub(pasta: Path, nome: str, corpo: str) -> None:
    arq = pasta / nome
    arq.write_text(corpo.format(py=sys.executable, filha=FILHA))
    arq.chmod(0o755)


class _Ollama(BaseHTTPRequestHandler):
    pedidos: list = []
    resposta: dict = {}

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).pedidos.append(corpo)
        dados = json.dumps(type(self).resposta).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, *a):
        pass


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    posto, inst, bin_, stub_log = tmp_path / "posto", tmp_path / "inst", tmp_path / "bin", tmp_path / "stub.log"
    (posto / "agentes").mkdir(parents=True)
    bin_.mkdir()
    _stub(bin_, "sessao", STUB_SESSAO)
    _stub(bin_, "expediente", STUB_EXPEDIENTE)
    _stub(bin_, "acervo", STUB_ACERVO)
    _stub(tmp_path, "claude", STUB_CLAUDE)
    for k, v in (("PF_POSTO", posto), ("PLATAFIRMA_INSTANCIA", inst), ("PF_BIN", bin_),
                 ("PF_CLAUDE_BIN", tmp_path / "claude"), ("STUB_LOG", stub_log)):
        monkeypatch.setenv(k, str(v))
    for k in ("PF_SUJEITO", "PF_SESSAO", "STUB_SESSAO_EXIT", "STUB_EXPEDIENTE_EXIT"):
        monkeypatch.delenv(k, raising=False)

    def escreve(*decls):
        for d in decls:
            (posto / "agentes" / f"{d['slug']}.yaml").write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))

    def chamadas():
        return [json.loads(l) for l in stub_log.read_text().splitlines()] if stub_log.exists() else []

    def isolacao(conta, estados):
        pasta = inst / "var" / "log" / "seg"
        pasta.mkdir(parents=True, exist_ok=True)
        rs = [{"estado": e, "conta": conta, "verificacao": f"v{i}", "detalhe": f"d{i}"} for i, e in enumerate(estados)]
        (pasta / "isolacao-2026-09-30.jsonl").write_text(json.dumps({"em": "x", "contas": [conta], "resultados": rs}) + "\n")

    return SimpleNamespace(posto=posto, inst=inst, escreve=escreve, chamadas=chamadas, isolacao=isolacao)


@pytest.fixture
def ollama(monkeypatch):
    classe = type("H", (_Ollama,), {"pedidos": [], "resposta": {
        "message": {"content": "L3 · erro de conexao"}, "prompt_eval_count": 900, "eval_count": 12}})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), classe)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(agente, "OLLAMA_URL", f"http://127.0.0.1:{srv.server_port}")
    yield classe
    srv.shutdown()


@pytest.fixture
def pessoa(monkeypatch):
    monkeypatch.setenv("PF_SUJEITO", "suj-1")
    monkeypatch.setenv("PF_SESSAO", ORQ)


def roda(monkeypatch, slug, tarefa="varra isto", cadeira=None, chapeu=None, como_json=False):
    monkeypatch.setattr(sys, "stdin", io.StringIO(tarefa))
    return agente.ato_rodar(slug, cadeira, chapeu, como_json)


# --- o molde da declaração ----------------------------------------------------------------------

def test_declaracao_no_molde_passa():
    assert agente.valida(REVISOR, "revisor") == []
    assert agente.valida(VARREDOR, "varredor") == []
    assert agente.valida(CONSULTOR, "consultor") == []


@pytest.mark.parametrize("decl,trecho", [
    (com(REVISOR, ferramentas=["Read", "Bash"]), "ferramenta proibida: Bash"),
    (com(REVISOR, ferramentas=["Write"]), "ferramenta proibida: Write"),
    (com(REVISOR, pernas={"fonte_de_fora": True, "dado_pessoal": True, "muda_estado": True}), "as três juntas"),
    (com(REVISOR, pernas={"fonte_de_fora": True, "dado_pessoal": True, "muda_estado": False}), "fonte de fora e dado pessoal"),
    (com(REVISOR, modo="resumir"), "modo:"),
    (com(REVISOR, slug="outro"), "difere do nome do arquivo"),
    (com(VARREDOR, ligacoes=["delegado"]), "delegado só existe para modelo Claude"),
    (com(REVISOR, modo="testar", regua="padrao readme"), "só nos modos revisar e avaliar"),
    (com(REVISOR, regua="guia desenvolvimento"), "regua:"),
    (com(VARREDOR, teto={"turnos": 1, "tokens_execucao": 1, "tokens_janela": 1}), "num_ctx"),
    (com(REVISOR, dono={"cadeira": "engenharia"}), "dono.chapeu"),
    (com(REVISOR, fecho={"comeca_com": "x"}), "fecho:"),
])
def test_declaracao_fora_do_molde_reprova(decl, trecho):
    achados = agente.valida(decl, "revisor")
    assert any(trecho in a for a in achados), achados


def test_numera_poe_o_numero_da_linha_na_frente_e_alarga_com_o_texto():
    assert agente.numera("a\nb") == "  1 | a\n  2 | b\n"
    assert agente.numera("") == ""
    grande = agente.numera("x\n" * 1000).splitlines()
    assert grande[0] == "   1 | x" and grande[-1] == "1000 | x"


def test_contas_e_provedores_seguem_o_modelo():
    assert agente.conta_do_modelo(REVISOR["modelo"]) == "claudinho"
    assert agente.conta_do_modelo({"familia": "gemini", "versao": "agy"}) == "jaiminho"
    assert agente.conta_do_modelo(VARREDOR["modelo"]) == "claudinho", "Qwen local roda na conta do host"
    assert agente.conta_do_modelo({"familia": "qwen", "versao": "x"}) == "quinzinho"
    assert agente.provedor(VARREDOR["modelo"]) == "host"
    assert agente.provedor({"familia": "gemini", "versao": "agy"}) == "gemini"


# --- a projeção ---------------------------------------------------------------------------------

def test_projecao_claude_leva_cabecalho_modelo_ferramentas_e_o_lote_de_abertura():
    texto = agente.projecao_claude(REVISOR)
    linhas = texto.splitlines()
    assert linhas[0] == "---" and linhas[1].startswith(agente.CABECALHO_GERADO)
    assert "name: revisor" in linhas and "model: sonnet" in linhas and "maxTurns: 40" in linhas
    assert ("tools: Read, Grep, " + ", ".join(g + "ler_arquivo" for g in agente.GRAFIAS) + ", "
            + ", ".join(g + "monta_sessao" for g in agente.GRAFIAS)) in linhas
    assert ('1. `monta_sessao` com `cadeira="engenharia"`, `chapeu="devops"`, `perfil="cadeirinha"`, '
            '`modo="revisar"`, `agente="revisor"`, `origem=<o sessao_id que a delegação trouxe>`') in texto
    assert "sessao abrir" not in texto and "expediente montar" not in texto, "abre pela mesma tool da cadeira"
    assert "pare antes do trabalho" in texto
    for proibida in agente.PROIBIDAS:
        assert f"{proibida}," not in texto and f", {proibida}" not in texto
    assert texto == agente.projecao_claude(REVISOR), "determinística: o --conferir compara byte a byte"


def test_projecao_do_consultor_nao_fixa_cadeira():
    texto = agente.projecao_claude(CONSULTOR)
    assert "`cadeira=<a cadeira que a delegação nomeia>`, `chapeu=<o chapéu que a delegação nomeia>`" in texto


def test_projetada_sem_monta_sessao_e_com_run_command_reprova():
    sem = com(REVISOR, ferramentas=["Read", "mcp__claudinho-mcp__ler_arquivo"])
    assert any("falta mcp__claudinho-mcp__monta_sessao" in a for a in agente.valida(sem, "revisor"))
    largo = com(REVISOR, ferramentas=[*REVISOR["ferramentas"], "mcp__claudinho-mcp__run_command"])
    assert any("ferramenta sem escopo: mcp__claudinho-mcp__run_command" in a for a in agente.valida(largo, "revisor"))
    # #3270: `malote` e o nome novo da mesma tool; declarar qualquer dos dois reprova.
    malote = com(REVISOR, ferramentas=[*REVISOR["ferramentas"], "mcp__claudinho-mcp__malote"])
    assert any("ferramenta sem escopo: mcp__claudinho-mcp__malote" in a for a in agente.valida(malote, "revisor"))
    assert agente.valida(VARREDOR, "varredor") == [], "sem projeção no Code, não abre por monta_sessao"



def test_conector_publica_ler_arquivo_e_mantem_o_apelido_read_file(mundo):
    publicadas = agente.tools_do_conector()
    assert agente.PORTA + "ler_arquivo" in publicadas and agente.PORTA + "read_file" in publicadas


def test_conferir_acusa_tool_que_o_conector_nao_publica(mundo, capsys):
    mundo.escreve(com(REVISOR, ferramentas=[*REVISOR["ferramentas"], "mcp__claudinho-mcp__inventada"]))
    agente.ato_projetar(False, None)
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 1
    assert "fora do conector: agentes/revisor.yaml declara mcp__claudinho-mcp__inventada" in capsys.readouterr().out


def test_conferir_com_acervo_fora_avisa_e_nao_reprova(mundo, capsys, monkeypatch):
    mundo.escreve(REVISOR)
    agente.ato_projetar(False, None)
    monkeypatch.setattr(agente, "tools_do_conector", lambda: None)
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 0
    assert "não foram conferidas contra o conector" in capsys.readouterr().out


def test_projetar_gera_so_as_de_claude_e_o_conferir_sai_0(mundo, capsys):
    mundo.escreve(REVISOR, VARREDOR)
    assert agente.ato_projetar(False, None) == 0
    gerados = sorted(p.name for p in (mundo.posto / ".claude" / "agents").glob("*.md"))
    assert gerados == ["revisor.md"], "o Qwen não tem projeção no Code"
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 0
    assert "conforme: 2 declaração(ões), 1 projeção(ões) Claude" in capsys.readouterr().out


def test_conferir_acusa_projecao_velha_ausente_e_orfao_sem_cabecalho(mundo, capsys):
    mundo.escreve(REVISOR)
    assert agente.ato_projetar(True, None) == 1
    assert "projeção ausente: .claude/agents/revisor.md" in capsys.readouterr().out
    agente.ato_projetar(False, None)
    arq = mundo.posto / ".claude" / "agents" / "revisor.md"
    arq.write_text(arq.read_text().replace("maxTurns: 40", "maxTurns: 41"))
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 1
    assert "projeção velha" in capsys.readouterr().out
    (mundo.posto / ".claude" / "agents" / "feito-a-mao.md").write_text("---\nname: x\n---\n")
    assert agente.ato_projetar(True, None) == 1
    assert "órfão: .claude/agents/feito-a-mao.md sem o cabeçalho de gerado" in capsys.readouterr().out


def test_conferir_acusa_ferramenta_proibida_e_projetar_nao_gera_com_declaracao_invalida(mundo, capsys):
    mundo.escreve(com(REVISOR, ferramentas=["Bash"]))
    assert agente.ato_projetar(True, None) == 1
    assert "ferramenta proibida: Bash" in capsys.readouterr().out
    assert agente.ato_projetar(False, None) == 1
    assert not (mundo.posto / ".claude" / "agents" / "revisor.md").exists()


def test_projetar_remove_a_projecao_de_declaracao_aposentada(mundo, capsys):
    mundo.escreve(REVISOR)
    agente.ato_projetar(False, None)
    (mundo.posto / "agentes" / "revisor.yaml").unlink()
    mundo.escreve(VARREDOR)
    assert agente.ato_projetar(False, None) == 0
    assert not (mundo.posto / ".claude" / "agents" / "revisor.md").exists()
    assert "removido: .claude/agents/revisor.md" in capsys.readouterr().out


def test_sem_regua_em_revisar_e_aviso_e_nao_reprova(mundo, capsys):
    mundo.escreve(REVISOR)
    agente.ato_projetar(False, None)
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 0
    assert "aviso: revisor: modo revisar sem regua" in capsys.readouterr().out


# --- o portão do PR que troca `modelo` (spec agente §11.2) ---------------------------------------

GEMINI = {"familia": "gemini", "versao": "agy"}


def test_caso_1_conta_alvo_sem_isolacao_conforme_reprova(mundo, capsys, monkeypatch):
    mundo.isolacao("jaiminho", ["ok", "FALHA"])
    mundo.escreve(com(REVISOR, modelo=GEMINI, ligacoes=["consultado"]))
    monkeypatch.setattr(agente, "declaracoes_da_base", lambda posto, ref: {"revisor": REVISOR})
    assert agente.ato_projetar(True, "origin/main") == 1
    assert "caso 1: revisor passa a rodar sob jaiminho" in capsys.readouterr().out


def test_caso_1_conta_nao_medida_reprova(mundo):
    mundo.isolacao("jaiminho", ["NAO MEDIDO"])
    achados = agente.portao_da_troca("revisor", com(REVISOR, modelo=GEMINI), REVISOR)
    assert len(achados) == 1 and "caso 1" in achados[0] and "NAO MEDIDO" in achados[0]


def test_caso_1_sem_medicao_nenhuma_reprova(mundo):
    achados = agente.portao_da_troca("revisor", com(REVISOR, modelo=GEMINI), REVISOR)
    assert len(achados) == 1 and "sem medição registrada" in achados[0]


def test_caso_2_dado_pessoal_para_provedor_novo_fora_do_host_vai_ao_dono(mundo, capsys, monkeypatch):
    pessoal = {"fonte_de_fora": False, "dado_pessoal": True, "muda_estado": False}
    base = com(VARREDOR, pernas=pessoal)
    nova = com(base, modelo=REVISOR["modelo"], ligacoes=["consultado"], teto=REVISOR["teto"])
    mundo.escreve(nova)
    monkeypatch.setattr(agente, "declaracoes_da_base", lambda posto, ref: {"varredor": base})
    assert agente.ato_projetar(True, "origin/main") == 1
    saida = capsys.readouterr().out
    assert "caso 2 — vai ao dono antes do merge" in saida and "provedor claude" in saida


def test_troca_entre_contas_admitidas_sem_perna_de_dado_pessoal_passa(mundo, capsys, monkeypatch):
    mundo.isolacao("jaiminho", ["ok", "ok", "ok"])
    mundo.escreve(com(REVISOR, modelo=GEMINI, ligacoes=["consultado"]))
    monkeypatch.setattr(agente, "declaracoes_da_base", lambda posto, ref: {"revisor": REVISOR})
    assert agente.ato_projetar(True, "origin/main") == 0
    saida = capsys.readouterr().out
    assert "divergente" not in saida and "conforme: 1 declaração(ões)" in saida
    assert agente.portao_da_troca("revisor", com(REVISOR, modelo=GEMINI), REVISOR) == []


def test_mesma_familia_ou_agente_novo_nao_troca_nada(mundo):
    mundo.isolacao("jaiminho", ["FALHA"])
    assert agente.portao_da_troca("revisor", com(REVISOR, modelo={"familia": "claude", "versao": "opus"}), REVISOR) == []
    assert agente.portao_da_troca("novo", com(REVISOR, modelo=GEMINI), None) == []


def _git(posto, *args):
    subprocess.run(["git", "-C", str(posto), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


def test_os_tres_ensaios_do_portao_com_git_de_verdade(mundo, capsys):
    """O que o PR do posto roda: --conferir contra a base (aqui o commit HEAD), sem dublê do git."""
    pessoal = {"fonte_de_fora": False, "dado_pessoal": True, "muda_estado": False}
    base_varredor = com(VARREDOR, pernas=pessoal)
    mundo.escreve(REVISOR, base_varredor)
    _git(mundo.posto, "init", "-q")
    _git(mundo.posto, "add", ".")
    _git(mundo.posto, "commit", "-qm", "base")
    agente.ato_projetar(False, None)
    capsys.readouterr()

    def ensaio(slug, nova, conta_gemini=None):
        if conta_gemini:
            mundo.isolacao("jaiminho", conta_gemini)
        mundo.escreve(nova)
        rc = agente.ato_projetar(True, "HEAD")
        saida = capsys.readouterr().out
        _git(mundo.posto, "checkout", "--", "agentes")
        return rc, saida

    # caso 1: troca para a conta jaiminho, que a última medição não deu conforme
    rc, saida = ensaio("revisor", com(REVISOR, modelo=GEMINI, ligacoes=["consultado"]), ["ok", "FALHA"])
    assert rc == 1 and "caso 1: revisor passa a rodar sob jaiminho" in saida
    # caso 2: perna dado pessoal e o contexto passa do host para o provedor claude
    rc, saida = ensaio("varredor", com(base_varredor, modelo=REVISOR["modelo"], ligacoes=["consultado"],
                                       teto=REVISOR["teto"]))
    assert rc == 1 and "caso 2 — vai ao dono antes do merge" in saida
    # a troca entre contas admitidas, sem perna de dado pessoal, passa
    (mundo.posto / ".claude" / "agents" / "revisor.md").unlink()
    rc, saida = ensaio("revisor", com(REVISOR, modelo=GEMINI, ligacoes=["consultado"]), ["ok", "ok"])
    assert rc == 0 and "caso" not in saida and "divergente" not in saida


def test_base_que_nao_existe_e_indeterminavel_quando_pedida(mundo, monkeypatch):
    mundo.escreve(REVISOR)
    monkeypatch.setattr(agente, "declaracoes_da_base", lambda posto, ref: None)
    assert agente.ato_projetar(True, "origin/inexistente") == 5


def test_sem_git_no_clone_avisa_que_o_portao_nao_foi_conferido(mundo, capsys):
    mundo.escreve(REVISOR)
    agente.ato_projetar(False, None)
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 0
    assert "o portão da troca de modelo (§11.2) não foi conferido" in capsys.readouterr().out


# --- listar e ler -------------------------------------------------------------------------------

def test_listar_filtra_por_modelo_e_modo(mundo, capsys):
    mundo.escreve(REVISOR, VARREDOR)
    assert agente.ato_listar(None, None, False) == 0
    saida = capsys.readouterr().out
    assert "revisor" in saida and "varredor" in saida
    assert agente.ato_listar("qwen", None, False) == 0
    saida = capsys.readouterr().out
    assert "varredor" in saida and "revisor" not in saida
    assert agente.ato_listar(None, "testar", False) == 1
    assert "nenhuma declaração com esse filtro" in capsys.readouterr().err


def test_listar_json(mundo, capsys):
    mundo.escreve(REVISOR)
    assert agente.ato_listar(None, None, True) == 0
    obj = json.loads(capsys.readouterr().out)
    assert obj["agentes"][0]["slug"] == "revisor" and obj["agentes"][0]["dono"] == "engenharia/devops"


def _git_na(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                   capture_output=True)


def _posto_atras_de_origin(mundo, tmp_path):
    """O posto vira um clone destacado em origin/main; depois a origem ganha a declaração `revisor`."""
    import shutil
    origem, semente = tmp_path / "origem.git", tmp_path / "semente"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origem)], check=True)
    (semente / "agentes").mkdir(parents=True)
    _git_na(semente, "init", "-q", "-b", "main")
    (semente / "agentes" / "varredor.yaml").write_text(yaml.safe_dump(VARREDOR, allow_unicode=True, sort_keys=False))
    _git_na(semente, "add", "-A")
    _git_na(semente, "commit", "-q", "-m", "varredor")
    _git_na(semente, "remote", "add", "origin", str(origem))
    _git_na(semente, "push", "-q", "origin", "main")
    shutil.rmtree(mundo.posto)
    _git_na(tmp_path, "clone", "-q", str(origem), str(mundo.posto))
    _git_na(mundo.posto, "checkout", "-q", "--detach", "origin/main")
    (semente / "agentes" / "revisor.yaml").write_text(yaml.safe_dump(REVISOR, allow_unicode=True, sort_keys=False))
    _git_na(semente, "add", "-A")
    _git_na(semente, "commit", "-q", "-m", "revisor")
    _git_na(semente, "push", "-q", "origin", "main")


def test_listar_avanca_o_clone_do_posto_para_origin_main(mundo, tmp_path, capsys):
    """#2856 linha 99: o clone do posto ficava num sha velho e o verbo lia declaração já consertada."""
    _posto_atras_de_origin(mundo, tmp_path)
    assert agente.ato_listar(None, None, False) == 0
    saida = capsys.readouterr().out
    assert "revisor" in saida and "varredor" in saida


def test_clone_do_posto_sujo_nao_e_mexido(mundo, tmp_path, capsys):
    _posto_atras_de_origin(mundo, tmp_path)
    (mundo.posto / "rascunho.txt").write_text("x")
    assert agente.ato_listar(None, None, False) == 0
    saida = capsys.readouterr().out
    assert "varredor" in saida and "revisor" not in saida


def test_ler_devolve_o_arquivo_e_o_inexistente_sai_1_com_vizinho(mundo, capsys):
    mundo.escreve(REVISOR)
    assert agente.ato_ler("revisor") == 0
    assert "slug: revisor" in capsys.readouterr().out
    assert agente.ato_ler("revisr") == 1
    assert "vizinho: agente ler revisor" in capsys.readouterr().err


# --- rodar: o §11.1 e as ligações ---------------------------------------------------------------

def test_sem_pessoa_resolvida_sai_1_sem_abrir_sessao_nem_chamar_o_modelo(mundo, ollama, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    assert roda(monkeypatch, "varredor") == 1
    assert "sem pessoa resolvida" in capsys.readouterr().err
    assert mundo.chamadas() == [] and ollama.pedidos == []
    monkeypatch.setenv("PF_SUJEITO", "suj-1")                      # pessoa sem a sessão de origem: idem
    assert roda(monkeypatch, "varredor") == 1
    assert mundo.chamadas() == [] and ollama.pedidos == []


def test_rodar_varredor_fixa_os_cinco_atributos_antes_de_chamar_o_modelo(mundo, ollama, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    assert roda(monkeypatch, "varredor", tarefa="linha 1\nlinha 3: erro de conexao") == 0
    saida = capsys.readouterr()
    assert saida.out.strip() == "L3 · erro de conexao"
    sessao_abrir, expediente, encerrar = mundo.chamadas()
    assert sessao_abrir["argv"] == ["abrir", "engenharia", "--origem", ORQ, "--agente", "varredor",
                                    "--em-nome-de", "engenharia", "--conta", "claudinho", "--json"]
    assert expediente["argv"] == ["montar", "--perfil", "cadeirinha", "--chapeu", "devops", "--modo", "varrer", "--json"]
    assert expediente["env"] == {"PF_CADEIRA": "engenharia", "PF_SESSAO": FILHA, "PF_ORIGEM_SESSAO": ORQ}
    assert expediente["stdin"] == "linha 1\nlinha 3: erro de conexao"
    assert encerrar["argv"] == ["encerrar", FILHA]
    (pedido,) = ollama.pedidos
    assert pedido["model"] == "qwen3.5:9b" and pedido["stream"] is False
    assert pedido["options"]["num_ctx"] == 16384 and pedido["options"]["temperature"] == 0
    assert pedido["options"]["num_predict"] == 2048, "a saída tem teto próprio, não o que sobra da janela"
    assert pedido["messages"][0]["role"] == "system"
    assert "LENTE-PERSONA" in pedido["messages"][0]["content"] and "LENTE-MODO" in pedido["messages"][0]["content"]
    assert "FECHO do agente `varredor`" in pedido["messages"][0]["content"]
    assert pedido["messages"][1] == {"role": "user", "content": "  1 | linha 1\n  2 | linha 3: erro de conexao\n"}, \
        "no modo varrer o modelo recebe as linhas numeradas; a lente recebeu o texto como veio"
    (log,) = [json.loads(l) for f in (mundo.inst / "var" / "log" / "agente").glob("*.jsonl") for l in f.read_text().splitlines()]
    assert {k: log[k] for k in ("agente", "sujeito", "em_nome_de", "origem", "conta", "exit")} == {
        "agente": "varredor", "sujeito": "suj-1", "em_nome_de": "engenharia", "origem": ORQ, "conta": "claudinho", "exit": 0}
    assert log["sessao_id"] == FILHA and log["uso"] == {"entrada": 900, "saida": 12}


def test_rodar_json_traz_o_retorno_e_os_atributos(mundo, ollama, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    assert roda(monkeypatch, "varredor", como_json=True) == 0
    obj = json.loads(capsys.readouterr().out)
    assert obj["retorno"] == "L3 · erro de conexao" and obj["sessao_id"] == FILHA and obj["origem"] == ORQ
    assert obj["sujeito"] == "suj-1" and obj["em_nome_de"] == "engenharia" and obj["conta"] == "claudinho"


def test_modo_sem_documento_sai_3_e_nao_chama_o_modelo(mundo, ollama, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    monkeypatch.setenv("STUB_EXPEDIENTE_EXIT", "2")
    assert roda(monkeypatch, "varredor") == 3
    assert "sem documento na casa" in capsys.readouterr().err
    assert ollama.pedidos == []
    assert mundo.chamadas()[-1]["argv"] == ["encerrar", FILHA], "a filha não fica aberta"


def test_sessao_que_nega_propaga_a_recusa_e_nao_monta_lente(mundo, ollama, pessoa, monkeypatch):
    mundo.escreve(VARREDOR)
    monkeypatch.setenv("STUB_SESSAO_EXIT", "4")
    assert roda(monkeypatch, "varredor") == 4
    assert [c["verbo"] for c in mundo.chamadas()] == ["sessao"] and ollama.pedidos == []


def test_tarefa_que_passa_do_teto_sai_3_sem_chamar_o_modelo(mundo, ollama, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    assert roda(monkeypatch, "varredor", tarefa="x" * 60000) == 3
    assert "prompt_eval_count_max" in capsys.readouterr().err and ollama.pedidos == []


def test_ollama_fora_do_ar_sai_3(mundo, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    monkeypatch.setattr(agente, "OLLAMA_URL", "http://127.0.0.1:9")
    assert roda(monkeypatch, "varredor") == 3
    assert "ollama" in capsys.readouterr().err


def test_resposta_vazia_do_modelo_e_indeterminavel(mundo, ollama, pessoa, monkeypatch):
    mundo.escreve(VARREDOR)
    ollama.resposta = {"message": {"content": "  "}}
    assert roda(monkeypatch, "varredor") == 5


def test_prompt_acima_do_teto_medido_vira_aviso(mundo, ollama, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR)
    ollama.resposta = {"message": {"content": "ok"}, "prompt_eval_count": 14000, "eval_count": 1}
    assert roda(monkeypatch, "varredor") == 0
    assert "prompt_eval_count 14000 passou de 13000" in capsys.readouterr().err


def test_gemini_ainda_nao_roda_e_sai_3_antes_de_abrir_sessao(mundo, pessoa, monkeypatch, capsys):
    mundo.isolacao("jaiminho", ["ok"])
    mundo.escreve(com(REVISOR, slug="avaliador", modelo=GEMINI, ligacoes=["consultado"]))
    assert roda(monkeypatch, "avaliador") == 3
    assert "é da ti" in capsys.readouterr().err and mundo.chamadas() == []


def test_conta_segregada_sem_isolacao_conforme_sai_4_antes_de_abrir_sessao(mundo, pessoa, monkeypatch, capsys):
    mundo.escreve(com(REVISOR, slug="avaliador", modelo=GEMINI, ligacoes=["consultado"]))
    assert roda(monkeypatch, "avaliador") == 4
    assert "jaiminho não está conforme" in capsys.readouterr().err and mundo.chamadas() == []


def test_declaracao_fora_do_molde_nao_roda(mundo, pessoa, monkeypatch):
    mundo.escreve(com(VARREDOR, ferramentas=["Bash"]))
    assert roda(monkeypatch, "varredor") == 4
    assert mundo.chamadas() == []


def test_slug_inexistente_sai_1_e_sem_tarefa_sai_2(mundo, pessoa, monkeypatch):
    assert roda(monkeypatch, "fantasma") == 1
    mundo.escreve(VARREDOR)
    assert roda(monkeypatch, "varredor", tarefa="  \n") == 2


def test_cadeira_so_vale_no_agente_de_dono_generico(mundo, pessoa, monkeypatch, capsys):
    mundo.escreve(VARREDOR, CONSULTOR)
    assert roda(monkeypatch, "varredor", cadeira="ia") == 2
    assert roda(monkeypatch, "consultor") == 2
    assert "passe --cadeira" in capsys.readouterr().err
    assert roda(monkeypatch, "consultor", cadeira="ia") == 2, "dono {cadeira} sem chapéu fixo pede --chapeu"
    assert "passe --chapeu" in capsys.readouterr().err


def test_claude_monta_a_chamada_do_cli_com_modelo_teto_e_ferramentas(mundo, pessoa, monkeypatch, capsys):
    mundo.escreve(CONSULTOR)
    assert roda(monkeypatch, "consultor", tarefa="o que a ia acha?", cadeira="ia", chapeu="agente") == 0
    assert capsys.readouterr().out.strip() == "veredito: 0 — x@y"
    sessao_abrir, _, claude, _ = mundo.chamadas()
    assert sessao_abrir["argv"][:2] == ["abrir", "ia"] and "--em-nome-de" in sessao_abrir["argv"]
    argv = claude["argv"]
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert argv[argv.index("--max-turns") + 1] == "40"
    assert argv[argv.index("--disallowedTools") + 1] == "Bash,Write,Edit,NotebookEdit"
    assert "mcp__claudinho-mcp__ler_arquivo" in argv[argv.index("--allowedTools") + 1]
    assert "LENTE-PERSONA" in argv[argv.index("--append-system-prompt") + 1]
    assert claude["stdin"] == "o que a ia acha?"


def test_claude_mede_a_entrada_com_o_cache(mundo):
    r = agente.chama_claude(CONSULTOR, "sistema", "tarefa")
    assert r["uso"] == {"entrada": 1150, "saida": 20, "turnos": 3}


# --- por ligação e suplanta (spec agente rev 3) --------------------------------------------------

EXPLORE = com(VARREDOR, ligacoes=["delegado", "consultado", "agendado"], suplanta="Explore",
              por_ligacao={"delegado": {"modelo": {"familia": "claude", "versao": "sonnet"},
                                        "ferramentas": ["Read", "Grep", "Glob", "mcp__claudinho-mcp__monta_sessao"],
                                        "teto": {"turnos": 40, "tokens_execucao": 200000, "tokens_janela": 1000000}}})

def test_varredor_com_delegado_em_claude_e_qwen_no_resto_passa():
    assert agente.valida(EXPLORE, "varredor") == []
    assert agente.tem_projecao(EXPLORE) and not agente.tem_projecao(VARREDOR)
    assert agente.efetiva(EXPLORE, "consultado")["modelo"] == VARREDOR["modelo"]
    assert agente.efetiva(EXPLORE, "delegado")["modelo"]["familia"] == "claude"

@pytest.mark.parametrize("decl,trecho", [
    (com(EXPLORE, suplanta="general-purpose"), "suplanta: um de"),
    (com(VARREDOR, suplanta="Explore"), "suplanta: só vale com a ligação delegada"),
    (com(EXPLORE, por_ligacao={"delegado": {"pernas": {}}}), "por_ligacao: mapa de"),
    (com(EXPLORE, ligacoes=["consultado"], suplanta=None), "por_ligacao.delegado: a ligação não está em ligacoes"),
    (com(EXPLORE, por_ligacao={"delegado": {"modelo": {"familia": "claude", "versao": "sonnet"},
                                            "ferramentas": ["Bash"]}}), "por_ligacao.delegado: ferramenta proibida: Bash"),
    (com(EXPLORE, por_ligacao={"delegado": {"modelo": {"familia": "qwen", "versao": "x", "local": True}}}),
     "delegado só existe para modelo Claude"),
])
def test_por_ligacao_e_suplanta_fora_do_molde_reprovam(decl, trecho):
    d = {k: v for k, v in decl.items() if v is not None}
    achados = agente.valida(d, "varredor")
    assert any(trecho in a for a in achados), achados

def test_projecao_do_suplante_sai_com_o_nome_do_embutido_e_a_execucao_delegada():
    linhas = agente.projecao_claude(EXPLORE).splitlines()
    assert "name: Explore" in linhas and "model: sonnet" in linhas and "maxTurns: 40" in linhas
    assert "tools: Read, Grep, Glob, " + ", ".join(g + "monta_sessao" for g in agente.GRAFIAS) in linhas

def test_projecao_lista_a_porta_nas_tres_grafias_e_a_declaracao_segue_canonica():
    """#3255: no Code Desktop do posto o conector chega pelo uuid; no CLI, como claude_ai_claudinho-mcp."""
    (tools,) = [l for l in agente.projecao_claude(CONSULTOR).splitlines() if l.startswith("tools: ")]
    nomes = tools[len("tools: "):].split(", ")
    for esperado in ("mcp__claudinho-mcp__monta_sessao", "mcp__claude_ai_claudinho-mcp__monta_sessao",
                     "mcp__f40dcc0d-abeb-4254-8b3d-34d33a57565d__monta_sessao"):
        assert esperado in nomes
    assert nomes[:2] == ["Read", "Grep"] and len(nomes) == len(set(nomes)), "embutidas passam como vieram, sem repetir"
    assert agente.grafias("Read") == ["Read"]
    assert agente.valida(CONSULTOR, "consultor") == [], "a declaração não muda: o conector confere o canônico"

def test_projetar_gera_o_explore_e_o_conferir_conta_a_projecao(mundo, capsys):
    mundo.escreve(REVISOR, EXPLORE)
    assert agente.ato_projetar(False, None) == 0
    gerados = sorted(p.name for p in (mundo.posto / ".claude" / "agents").glob("*.md"))
    assert gerados == ["revisor.md", "varredor.md"]
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 0
    assert "conforme: 2 declaração(ões), 2 projeção(ões) Claude" in capsys.readouterr().out

def test_claude_so_consultado_segue_projetado_ao_lado_do_suplante(mundo, capsys):
    """Regressão de 01/10: consultor e curador são Claude sem ligação delegada e têm projeção desde o #3156."""
    mundo.escreve(REVISOR, CONSULTOR, EXPLORE)
    assert agente.ato_projetar(False, None) == 0
    gerados = sorted(p.name for p in (mundo.posto / ".claude" / "agents").glob("*.md"))
    assert gerados == ["consultor.md", "revisor.md", "varredor.md"]
    capsys.readouterr()
    assert agente.ato_projetar(True, None) == 0
    assert "3 projeção(ões) Claude" in capsys.readouterr().out

def test_rodar_consultado_usa_o_qwen_mesmo_com_delegado_em_claude(mundo, ollama, pessoa, monkeypatch, capsys):
    mundo.escreve(EXPLORE)
    assert roda(monkeypatch, "varredor") == 0
    (pedido,) = ollama.pedidos
    assert pedido["model"] == "qwen3.5:9b"
    assert not [c for c in mundo.chamadas() if c["verbo"] == "claude"]

def test_claude_acima_do_teto_de_tokens_avisa_e_nao_corta(mundo, pessoa, monkeypatch, capsys):
    mundo.escreve(com(CONSULTOR, teto={"turnos": 30, "tokens_execucao": 50, "tokens_janela": 600000}))
    assert roda(monkeypatch, "consultor", cadeira="ia", chapeu="agente") == 0
    saida = capsys.readouterr()
    assert "passaram de tokens_execucao 50 (medido, não cortado)" in saida.err
    assert saida.out.strip() == "veredito: 0 — x@y"
