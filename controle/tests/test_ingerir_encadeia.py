"""`ingerir --ate vetor --apply` vai até o ar: cataloga, espelha, confere a faixa, indexa até o gate e promove.

Servidor do acervo falso (HTTP em thread) e verbos `acervo` e `motor` falsos (PF_BIN_ACERVO,
PF_BIN_MOTOR) que seguem o contrato real medido no #3967: o `motor indexar` recusa `--promover` (422
PromocaoDoAcervo), o plano traz `sem_faixa`, o aplicar sem item devolve `modo: nada`, o relatório só tem
os estados de item `pendente`, `faceta_refeita`, `indexada`, `reprovada` e `falhou`, e quem põe no ar é o
`acervo promover`. A obra que um portão barra para ali, com o portão dito, sem derrubar as outras."""
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN_INGERIR = os.path.join(REPO, "bin", "ingerir")

OBRA_A = "aaaaaaaa-0000-4000-8000-000000000001"
OBRA_B = "bbbbbbbb-0000-4000-8000-000000000002"
IMPRESSAO = {OBRA_A: "dddddddd-0000-4000-8000-00000000000a", OBRA_B: "dddddddd-0000-4000-8000-00000000000b"}
LOTE_MOTOR = "cccccccc-0000-4000-8000-000000000003"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (ingerir precisa)")


def _executavel(caminho, conteudo):
    caminho.write_text(conteudo)
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# Os verbos falsos: um script só, lido do cenário que o teste grava. Cada chamada vai ao log.
FALSO = '''
import json, os, sys

verbo, argv = sys.argv[1], sys.argv[2:]
raiz = os.environ["PF_CENARIO_DIR"]
cen = json.load(open(os.path.join(raiz, "cenario.json")))
with open(os.path.join(raiz, "chamadas.log"), "a") as f:
    f.write(verbo + " " + " ".join(argv) + "\\n")
marcadas_em = os.path.join(raiz, "marcadas.txt")


def marcadas():
    return open(marcadas_em).read().split() if os.path.exists(marcadas_em) else []


def acervo():
    ato = argv[0]
    if ato == "espelhar":
        obra = argv[3]
        print("  novo      : combinado@1 · digest x · " + cen["julgamento"].get(obra, "servível"))
        print("  impressão : " + cen["impressao"][obra] + " selada")
    elif ato == "curar":
        if not cen.get("marcar_funciona", True):
            print("0 impressão(ões) servindo com espelho: 0 conformes, 1 reprovadas · plano (nada gravado)")
            sys.exit(1)
        with open(marcadas_em, "a") as f:
            f.write(argv[argv.index("--impressao") + 1] + "\\n")
        print("1 impressão(ões) servindo com espelho: 1 conformes, 0 reprovadas · faixas gravadas")
    elif ato == "promover":
        obra, imp = argv[3], argv[argv.index("--impressao") + 1]
        if obra in cen.get("recusa_promover", {}):
            sys.stderr.write(cen["recusa_promover"][obra] + "\\n")
            sys.exit(1)
        marcacao = cen.get("marcacao", {}).get(obra, "transcrita e indexada")
        corpo = {"promovida": {"id": imp}, "obra_id": obra, "degrau": "vetor", "marcacao": marcacao}
        if marcacao == "transcrita e indexada" and obra not in cen.get("sem_indice", []):
            corpo["indices_promovidos"] = ["i1", "i2"]
        print(json.dumps(corpo))


def motor():
    resto = argv[3:]
    if "--promover" in resto:
        sys.stderr.write("PromocaoDoAcervo: promover é do `acervo promover` (spec motor R24)\\n")
        sys.exit(2)
    if "--relatorio" in resto:
        print(json.dumps({"lote": LOTE, "estado": cen.get("estado_lote", "concluido"), "itens": cen["itens"]}))
    elif "--apply" in resto:
        if cen.get("outro_lote"):
            sys.stderr.write("LoteEmAndamento: já há um lote de indexação rodando\\n")
            sys.exit(4)
        if cen.get("modo_nada"):
            print(json.dumps({"modo": "nada", "n": 0, "itens": [], "sem_faixa": []}))
        else:
            print(json.dumps({"modo": "aplicado", "lote": LOTE, "n": len(cen["itens"])}))
    else:
        sem = [{"impressao_id": cen["impressao"][o], "obra_id": o, "titulo": o, "espelho": True}
               for o in cen.get("sem_faixa", []) if cen["impressao"][o] not in marcadas()]
        print(json.dumps({"modo": "plano", "ato": "indexar-lote", "promover": False, "itens": [],
                          "sem_faixa": sem, "fora_sem_faixa": len(sem)}))


LOTE = "''' + LOTE_MOTOR + '''"
{"acervo": acervo, "motor": motor}[verbo]()
'''


class _Acervo(BaseHTTPRequestHandler):
    pedidos = []
    obras = [OBRA_A, OBRA_B]

    def _json(self, codigo, corpo):
        dado = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def _le(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_PUT(self):
        self._le()
        self._json(201, {})

    def do_POST(self):
        corpo = self._le()
        if self.path == "/acervo/lotes":
            _Acervo.pedidos.append(json.loads(corpo))
            self._json(201, {"id": "L1", "itens": [], "resumo": {}})
        else:
            self._json(202, {})

    def do_GET(self):
        self._json(200, {"id": "L1", "estado": "concluido", "resumo": {"feito": len(_Acervo.obras)}, "itens": [
            {"posicao": i, "obra_id": obra, "estado": "feito", "veredito": "criar", "titulo": f"Obra {obra[0].upper()}"}
            for i, obra in enumerate(_Acervo.obras)]})

    def log_message(self, *a):
        pass


@pytest.fixture
def servidor():
    _Acervo.pedidos = []
    _Acervo.obras = [OBRA_A, OBRA_B]
    srv = HTTPServer(("127.0.0.1", 0), _Acervo)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _item(obra, estado="indexada", aprovado=True, problema=None):
    item = {"obra_id": obra, "estado": estado, "gate": {"aprovado": aprovado}}
    if problema:
        item["problema"] = problema
    return item


def _ambiente(tmp_path, base, **cenario):
    """O cenário padrão: A e B servíveis, faixa marcada, lote indexado e aprovado, promoção que sobe com índice.
    `cenario` troca o que o teste quer mudar."""
    padrao = {"impressao": IMPRESSAO, "julgamento": {OBRA_B: "não servível (sem medida)"},
              "itens": [_item(OBRA_A)]}
    (tmp_path / "cenario.json").write_text(json.dumps({**padrao, **cenario}))
    py = tmp_path / "py"
    py.mkdir()
    _executavel(py / "python3", f'#!/bin/sh\nexec {shlex.quote(PY)} "$@"\n')
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    (falsos / "falso.py").write_text(FALSO, encoding="utf-8")
    for verbo in ("acervo", "motor"):
        _executavel(falsos / verbo, f'#!/usr/bin/env bash\nexec {shlex.quote(PY)} {shlex.quote(str(falsos / "falso.py"))} {verbo} "$@"\n')
    home = tmp_path / "home"
    home.mkdir()
    return dict(os.environ, HOME=str(home), RAG_API_BASE=base, RAG_API_TOKEN="t",
                PF_BIN_ACERVO=str(falsos / "acervo"), PF_BIN_MOTOR=str(falsos / "motor"),
                PF_CENARIO_DIR=str(tmp_path), PF_INGERIR_PASSO="0", PATH=f"{py}:{os.environ.get('PATH', '')}")


def _pasta(tmp_path):
    pasta = tmp_path / "lote"
    pasta.mkdir()
    (pasta / "a.md").write_text("# Obra A\n")
    (pasta / "b.md").write_text("# Obra B\n")
    return pasta


def _ate_vetor(tmp_path, env):
    return subprocess.run([BIN_INGERIR, "--lote", str(_pasta(tmp_path)), "--ate", "vetor", "--apply"],
                          env=env, capture_output=True, text=True, check=False)


def _chamadas(tmp_path):
    log = tmp_path / "chamadas.log"
    return log.read_text().splitlines() if log.exists() else []


def _linha(r, obra):
    return next(l for l in r.stdout.splitlines() if obra in l)


def test_obra_que_passa_em_tudo_sai_no_ar_e_o_motor_nunca_recebe_promover(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor))
    assert _Acervo.pedidos[0]["ate"] == "catalogar"
    assert "Estágios depois de Incorporar: 1 de 1 no ar" in r.stdout
    assert _linha(r, OBRA_A).rstrip().endswith("no ar")
    chamadas = _chamadas(tmp_path)
    assert not any("--promover" in c for c in chamadas if c.startswith("motor"))
    ordem = [c.split()[0] + " " + c.split()[1] for c in chamadas]
    assert ordem == ["acervo espelhar", "motor rag", "motor rag", "motor rag", "acervo promover"]
    assert f"acervo promover biblioteca obra {OBRA_A} --impressao {IMPRESSAO[OBRA_A]} --json" in chamadas
    assert r.returncode == 0


def test_espelho_nao_servivel_para_em_transcrever_e_nao_vai_ao_motor(tmp_path, servidor):
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor))
    assert "Estágios depois de Incorporar: 1 de 2 no ar" in r.stdout
    assert _linha(r, OBRA_A).rstrip().endswith("no ar")
    assert "Transcrever: espelho não servível (sem medida)" in _linha(r, OBRA_B)
    motor = "\n".join(c for c in _chamadas(tmp_path) if c.startswith("motor"))
    assert OBRA_A in motor and OBRA_B not in motor
    assert r.returncode == 1


def test_selada_sem_faixa_e_marcada_pela_cadeia_e_sai_no_ar_com_o_aviso(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, sem_faixa=[OBRA_A]))
    assert "ingerir: Seccionar: a selagem não marcou a seção de Obra A; marcada pela cadeia" in r.stderr
    assert f"acervo curar biblioteca --marcar-secoes --impressao {IMPRESSAO[OBRA_A]} --apply" in _chamadas(tmp_path)
    assert _linha(r, OBRA_A).rstrip().endswith("no ar")
    assert r.returncode == 0


def test_selada_que_segue_sem_faixa_para_em_seccionar_e_nao_chama_o_aplicar(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, sem_faixa=[OBRA_A], marcar_funciona=False))
    assert "Seccionar: sem faixa depois da marcação (0 impressão(ões) servindo com espelho" in _linha(r, OBRA_A)
    assert not any("--apply" in c for c in _chamadas(tmp_path) if c.startswith("motor"))
    assert not any(c.startswith("acervo promover") for c in _chamadas(tmp_path))
    assert r.returncode == 1


def test_gate_reprovado_no_relatorio_para_em_indexar_e_nao_promove(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    itens = [_item(OBRA_A, "reprovada", False, problema="faltam 3 vetores de trecho")]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, itens=itens))
    assert f"Indexar: faltam 3 vetores de trecho (lote {LOTE_MOTOR})" in _linha(r, OBRA_A)
    assert not any(c.startswith("acervo promover") for c in _chamadas(tmp_path))
    assert r.returncode == 1


def test_item_falhou_no_relatorio_para_em_indexar(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    itens = [_item(OBRA_A, "falhou", False, problema="RuntimeError: sem memória")]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, itens=itens))
    assert "Indexar: RuntimeError: sem memória" in _linha(r, OBRA_A)
    assert r.returncode == 1


def test_lote_interrompido_antes_da_obra_para_em_indexar(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    itens = [_item(OBRA_A, "pendente", False)]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, itens=itens, estado_lote="interrompido"))
    assert "Indexar: lote interrompido antes desta obra" in _linha(r, OBRA_A)
    assert r.returncode == 1


def test_outro_lote_no_motor_para_todas_em_indexar_com_a_mensagem(tmp_path, servidor):
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, outro_lote=True, julgamento={}))
    assert "Estágios depois de Incorporar: 0 de 2 no ar" in r.stdout
    for obra in (OBRA_A, OBRA_B):
        assert "Indexar: há outro lote no motor; rodar de novo quando ele fechar" in _linha(r, obra)
    assert not any(c.startswith("acervo promover") for c in _chamadas(tmp_path))
    assert r.returncode == 1


def test_recusa_do_acervo_promover_para_em_servir(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    recusa = {OBRA_A: "GateReprovado: o gate do motor reprovou a impressão"}
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, recusa_promover=recusa))
    assert "Servir: GateReprovado: o gate do motor reprovou a impressão" in _linha(r, OBRA_A)
    assert r.returncode == 1


def test_indice_pronto_no_motor_vai_direto_ao_promover_sem_lote_novo(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, modo_nada=True))
    chamadas = _chamadas(tmp_path)
    assert not any("--relatorio" in c for c in chamadas)
    assert any(c.startswith("acervo promover") for c in chamadas)
    assert _linha(r, OBRA_A).rstrip().endswith("no ar")
    assert r.returncode == 0


def test_impressao_no_ar_sem_indice_nao_conta_como_no_ar(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, sem_indice=[OBRA_A]))
    assert "Servir: impressão no ar sem índice" in _linha(r, OBRA_A)
    assert "0 de 1 no ar" in r.stdout
    assert r.returncode == 1


def test_marcacao_transcrita_sai_no_ar_como_texto_sem_indice(tmp_path, servidor):
    _Acervo.obras = [OBRA_A]
    r = _ate_vetor(tmp_path, _ambiente(tmp_path, servidor, marcacao={OBRA_A: "transcrita"}))
    assert _linha(r, OBRA_A).rstrip().endswith("no ar (texto, sem índice)")
    assert "1 de 1 no ar" in r.stdout
    assert r.returncode == 0


def test_ajuda_nao_manda_o_promover_ao_motor():
    r = subprocess.run([PY, BIN_INGERIR, "--ajuda"], capture_output=True, text=True, check=False)
    assert "--promover" not in r.stderr
    assert "acervo promover" in r.stderr


def test_ate_chunk_para_na_selada_sem_chamar_o_motor(tmp_path, servidor):
    env = _ambiente(tmp_path, servidor)
    r = subprocess.run([BIN_INGERIR, "--lote", str(_pasta(tmp_path)), "--ate", "chunk", "--apply"],
                       env=env, capture_output=True, text=True, check=False)
    assert "1 de 2 selada" in r.stdout
    assert not any(c.startswith("motor") for c in _chamadas(tmp_path))


def test_arquivo_unico_vira_lote_de_um_item_sem_levar_a_pasta(tmp_path, servidor):
    # débito 331: `--lote <arquivo>` ingere só aquele arquivo; o irmão da pasta não entra
    env = _ambiente(tmp_path, servidor)
    pasta = _pasta(tmp_path)
    r = subprocess.run([BIN_INGERIR, "--lote", str(pasta / "a.md")],
                       env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    itens = _Acervo.pedidos[0]["itens"]
    assert [i["arquivo"] for i in itens] == ["a.md"]
    assert itens[0]["titulo"] == "Obra A"

def test_arquivo_unico_aceita_pdf_e_nao_aplica_filtro_de_fantasma(tmp_path, servidor):
    # o arquivo nomeado é a obra, mesmo com extensão que a varredura de pasta tratar como sidecar
    env = _ambiente(tmp_path, servidor)
    alvo = tmp_path / "artigo.pdf"
    alvo.write_bytes(b"%PDF-1.7 teste")
    r = subprocess.run([BIN_INGERIR, "--lote", str(alvo)],
                       env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    assert [i["arquivo"] for i in _Acervo.pedidos[0]["itens"]] == ["artigo.pdf"]

def test_caminho_que_nao_existe_recusa_sem_chamar_o_servidor(tmp_path, servidor):
    env = _ambiente(tmp_path, servidor)
    r = subprocess.run([BIN_INGERIR, "--lote", str(tmp_path / "nao-existe.pdf")],
                       env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 1
    assert "não encontrado" in r.stderr
    assert not _Acervo.pedidos

def test_sem_ate_nao_encadeia(tmp_path, servidor):
    env = _ambiente(tmp_path, servidor)
    r = subprocess.run([BIN_INGERIR, "--lote", str(_pasta(tmp_path)), "--apply"],
                       env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0
    assert "Estágios depois de Incorporar" not in r.stdout
    assert not _chamadas(tmp_path)
