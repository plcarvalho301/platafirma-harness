# componente: componente:descanso
"""Suíte de unidade e de aceite do descanso (story 4335, feature 4269).

Reúne as unidades de lib/descanso (mensagem, abandono e coletas) e os casos de aceite
de `bin/descansar` e `bin/descansar publicar`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[1]
DESCANSAR = HARNESS_DIR / "bin" / "descansar"
sys.path.insert(0, str(HARNESS_DIR / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import oplog  # noqa: E402
from descanso import abandono, coletas, eventos  # noqa: E402
from descanso.memoria import Fixtura  # noqa: E402
from descanso.publicar import (  # noqa: E402
    FicharioFixtura,
    GravadorArquivo,
    Mensagem,
    Recusada,
    SemDestino,
    publicar,
)
from test_abertura import _rodar_abertura  # noqa: E402

BASE = {"enunciado": "x", "quem": "persona:ia", "destinatario": "persona:ia", "tipo-de-mensagem": "afirmacao"}
SESSAO = "0195f000-aaaa-7bbb-8ccc-000000000001"
SUJEITO = "dono-de-teste"
DESPEDIDA = ["sessão encerrada; até a próxima."]
FICHAS = ["persona:engenharia", "persona:gestao-estrategica", "persona:dados"]


def _regs(ops: Path) -> list[dict]:
    return [json.loads(l) for a in sorted(ops.glob("ops-*.jsonl")) for l in a.read_text().splitlines() if l]


def _fichario_fixtura(tmp_path: Path, chaves: list[str]) -> FicharioFixtura:
    arq = tmp_path / "fichario.json"
    arq.write_text(json.dumps(chaves))
    return FicharioFixtura(arq)


# --- t3: mensagem (lib/descanso/publicar.py) ----------------------------------------------------------------------

def test_mensagem_publicar_nao_duplica_e_carrega_a_sessao(tmp_path):
    g, f = GravadorArquivo(tmp_path / "o.jsonl"), _fichario_fixtura(tmp_path, ["persona:ia", "capacidade:tarefas"])
    dado = {**BASE, "etiqueta": "capacidade:tarefas"}
    msg, gravou = publicar(dado, g, f, sessao="s1")
    assert gravou and msg.etiqueta == ["capacidade:tarefas"] and msg.destinatario == ["persona:ia"]
    assert msg.correlacao == "s1"
    assert publicar(dado, g, f, sessao="s1")[1] is False


def test_mensagem_responde_a_com_relacao(tmp_path):
    msg = Mensagem.de_dict({**BASE, "responde-a": "m1", "relacao-com-a-anterior": "corrige"})
    assert msg.responde_a == "m1" and msg.linha()["responde-a"] == "m1"
    assert "anterior" not in msg.linha()


def test_mensagem_chave_sem_ficha_recusa_e_fichario_fora_nao_grava(tmp_path):
    g = GravadorArquivo(tmp_path / "o.jsonl")
    with pytest.raises(Recusada, match="etiqueta que não é chave de ficha"):
        publicar({**BASE, "etiqueta": ["aresta"]}, g, _fichario_fixtura(tmp_path, ["persona:ia"]))
    with pytest.raises(Recusada, match="destinatário que não é chave de ficha"):
        publicar(BASE, g, _fichario_fixtura(tmp_path, []))
    with pytest.raises(SemDestino):
        publicar(BASE, g, FicharioFixtura(tmp_path / "nao-existe.json"))
    assert not (tmp_path / "o.jsonl").exists()


@pytest.mark.parametrize("dado", [
    None, [],
    {k: v for k, v in BASE.items() if k != "enunciado"},
    {k: v for k, v in BASE.items() if k != "quem"},
    {k: v for k, v in BASE.items() if k != "destinatario"},
    {**BASE, "destinatario": []},
    {k: v for k, v in BASE.items() if k != "tipo-de-mensagem"},
    {**BASE, "tipo-de-mensagem": "premissa"},
    {**BASE, "relacao-com-a-anterior": "corrige"},
    {**BASE, "responde-a": "m1", "relacao-com-a-anterior": "nega"},
    {**BASE, "etiqueta": [3]},
])
def test_mensagem_fora_da_forma_recusa(dado):
    with pytest.raises(Recusada):
        Mensagem.de_dict(dado)


# --- t2: abandono (lib/descanso/abandono.py) ----------------------------------------------------------------------

def test_abandono_so_fecha_a_do_mesmo_sujeito_com_a_chave_vencida(tmp_path):
    ops, mem = tmp_path / "ops", tmp_path / "mem.json"
    mem.write_text(json.dumps({"chaves": ["sessao:viva"]}))
    for sid, suj in (("parada", "a"), ("viva", "a"), ("de-outro", "b"), ("encerrada", "a")):
        eventos.emitir_aberta(sid, sujeito=suj, cadeira="ia", diretorio_=ops)
    eventos.emitir_encerrada("encerrada", sujeito="a", cadeira="ia", desfecho="descanso", diretorio_=ops)

    fech = abandono.fechar_abandonadas("a", Fixtura(mem), diretorio_=ops)

    assert fech.fechadas == ["parada"]
    assert fech.linha() == "1 sessão sua terminou sem descanso desde a última abertura"
    assert abandono.fechar_abandonadas("a", Fixtura(mem), diretorio_=ops).quantas == 0


def test_abandono_sem_candidata_nao_pergunta_a_memoria(tmp_path):
    mem = tmp_path / "mem.json"
    mem.write_text('{"fora": true}')
    assert abandono.fechar_abandonadas("a", Fixtura(mem), diretorio_=tmp_path / "ops").quantas == 0


def test_desfecho_fora_do_vocabulario_levanta(tmp_path):
    with pytest.raises(ValueError):
        eventos.emitir_encerrada("s", sujeito="a", cadeira="ia", desfecho="sumiu", diretorio_=tmp_path)


# --- t1: coletas (lib/descanso/coletas.py) ------------------------------------------------------------------------

def test_rodar_isola_a_coleta_que_falha(tmp_path):
    ops = tmp_path / "ops"
    ctx = {"sessao_id": "s", "cadeira": "ia", "sujeito": "a", "diretorio": str(ops)}

    def quebra(_ctx):
        raise RuntimeError("caiu")

    saida = coletas.rodar(ctx, {"encerramento": coletas.coleta_encerramento, "quebra": quebra})

    assert saida["encerramento"] == {"desfecho": "descanso"}
    assert "caiu" in saida["quebra"]["erro"]
    assert [r["evento"] for r in _regs(ops)] == ["sessao_encerrada", "coleta_falhou"]


def test_aresta_leva_as_pontas_com_ficha_e_o_para_que(tmp_path):
    bin_dir, ops = tmp_path / "bin", tmp_path / "ops"
    bin_dir.mkdir()
    (bin_dir / "mesa").write_text("#!/bin/sh\n# dono: gestao-estrategica\n# use para: guardar o que volta depois\n")
    (bin_dir / "fila").write_text("#!/bin/sh\n# dono: ti\n")
    (bin_dir / "teste").write_text("#!/bin/sh\n# dono: ia\n")
    for tool in ("mesa", "mesa", "fila", "teste"):
        oplog.emitir({"tool": tool, "sessao_id": "s", "cadeira": "ia", "exit_code": 0}, diretorio_=ops)
    destino = tmp_path / "o.jsonl"
    ctx = {"sessao_id": "s", "cadeira": "ia", "sujeito": "a", "diretorio": str(ops), "bin": str(bin_dir),
           "gravador": GravadorArquivo(destino),
           "fichario": _fichario_fixtura(tmp_path, ["persona:ia", "persona:gestao-estrategica"])}

    arestas = coletas.arestas_da_sessao(ctx)
    assert set(arestas) == {("mesa", "gestao-estrategica"), ("fila", "ti")}
    assert len(arestas[("mesa", "gestao-estrategica")]["apoio"]) == 2
    assert coletas.coleta_arestas(ctx) == {"arestas": 2, "gravadas": 2, "recusadas": 0}
    msgs = {m["enunciado"].split(" chamou ")[1].split(",")[0]: m
            for m in map(json.loads, destino.read_text().splitlines())}
    assert msgs["mesa"]["etiqueta"] == ["persona:ia", "persona:gestao-estrategica"]
    assert "para guardar o que volta depois" in msgs["mesa"]["enunciado"]
    assert msgs["fila"]["etiqueta"] == ["persona:ia"]
    assert {m["destinatario"][0] for m in msgs.values()} == {"persona:ia"}
    assert {m["tipo-de-mensagem"] for m in msgs.values()} == {"afirmacao"}


# --- bin/descansar (Aceite × prova da S4335) ----------------------------------------------------------------------

def _eventos(ops: Path) -> list[dict]:
    regs = []
    for arq in sorted(ops.glob("ops-*.jsonl")):
        regs += [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]
    return regs


def _espera_filho(pidfile: Path, prazo_s: float = 30.0) -> None:
    pid = int(pidfile.read_text(encoding="utf-8"))
    fim = time.monotonic() + prazo_s
    while time.monotonic() < fim:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    raise AssertionError(f"o processo das coletas (pid {pid}) não terminou em {prazo_s} s")


def _rodar_descansar(args: list[str], *, entrada: str, env_extra: dict) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for k in ("PF_SESSAO", "PF_CADEIRA", "PF_SUJEITO", "PF_MENSAGEM_ARQUIVO", "PF_FICHARIO_FIXTURE", "PF_BIN"):
        env.pop(k, None)
    env.update(env_extra)
    return subprocess.run([sys.executable, str(DESCANSAR), *args], input=entrada, capture_output=True, text=True,
                          timeout=30, env=env, check=False)


def _fichario(tmp_path: Path, chaves: list[str]) -> str:
    arq = tmp_path / "fichario.json"
    arq.write_text(json.dumps(chaves), encoding="utf-8")
    return str(arq)


def _ambiente_descanso(tmp_path: Path, mensagens: Path) -> dict:
    ops = tmp_path / "ops"
    mem = tmp_path / "valkey.json"
    mem.write_text(json.dumps({"chaves": [f"sessao:{SESSAO}"]}), encoding="utf-8")
    # dois giros da fita em tool de outra cadeira: `expediente` tem `# dono: gestao-estrategica`
    for _ in range(2):
        oplog.emitir({"tool": "expediente", "sessao_id": SESSAO, "cadeira": "engenharia", "exit_code": 0},
                     diretorio_=ops)
    return {"PF_SESSAO": SESSAO, "PF_CADEIRA": "engenharia", "PF_SUJEITO": SUJEITO, "OPS_LOG_DIR": str(ops),
            "PF_VALKEY_FIXTURE": str(mem), "PF_MENSAGEM_ARQUIVO": str(mensagens),
            "PF_FICHARIO_FIXTURE": _fichario(tmp_path, FICHAS),
            "PF_DESCANSO_PIDFILE": str(tmp_path / "coletas.pid")}


def test_descanso_encerra_dispara_as_coletas_e_devolve_so_a_despedida(tmp_path):
    mensagens = tmp_path / "mensagens.jsonl"
    env = _ambiente_descanso(tmp_path, mensagens)
    entrada = json.dumps([
        {"enunciado": "a suíte do descanso roda sem tocar a porta", "apoio": ["card:4335"]},
        {"enunciado": "o dono prefere a resposta sem pergunta de escolha", "quem": "persona:dados",
         "cita": "chat da gestão estratégica, 17/11/2026"},
    ], ensure_ascii=False)

    proc = _rodar_descansar([], entrada=entrada, env_extra=env)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip().splitlines() == DESPEDIDA
    _espera_filho(tmp_path / "coletas.pid")

    regs = {r["evento"]: r for r in _eventos(tmp_path / "ops") if r.get("tool") == eventos.TOOL}
    assert regs["sessao_encerrada"]["desfecho"] == "descanso"
    assert regs["sessao_encerrada"]["correlacao"] == SUJEITO
    assert regs["coleta_observacoes"]["gravadas"] == 2
    assert regs["coleta_arestas"]["arestas"] == 1
    assert "coleta_falhou" not in regs

    gravadas = [json.loads(l) for l in mensagens.read_text(encoding="utf-8").splitlines()]
    assert {g["tipo-de-mensagem"] for g in gravadas} == {"afirmacao"}
    assert all(g["destinatario"] == ["persona:engenharia"] for g in gravadas)
    assert all(g["correlacao"] == SESSAO for g in gravadas)
    licao, preferencia, aresta = sorted(gravadas, key=lambda g: (g["quem"] == "porta", g["cita"] is not None))
    assert licao["quem"] == "persona:engenharia" and licao["apoio"] == ["card:4335"]
    assert preferencia["quem"] == "persona:dados" and preferencia["cita"]
    assert aresta["quem"] == "porta"
    assert aresta["etiqueta"] == ["persona:engenharia", "persona:gestao-estrategica"]
    assert " para " in aresta["enunciado"] and len(aresta["apoio"]) == 2
    assert not any(k in g for g in gravadas for k in ("qualificador", "categoria"))
    assert json.loads(Path(env["PF_VALKEY_FIXTURE"]).read_text())["chaves"] == []


def test_descanso_com_coleta_que_falha_devolve_o_mesmo(tmp_path):
    destino_quebrado = tmp_path / "e-uma-pasta"
    destino_quebrado.mkdir()
    env = _ambiente_descanso(tmp_path, destino_quebrado)

    proc = _rodar_descansar([], entrada='["uma observação"]', env_extra=env)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip().splitlines() == DESPEDIDA
    _espera_filho(tmp_path / "coletas.pid")
    regs = [r for r in _eventos(tmp_path / "ops") if r.get("tool") == eventos.TOOL]
    assert any(r["evento"] == "sessao_encerrada" for r in regs)
    assert {r["coleta"] for r in regs if r["evento"] == "coleta_falhou"} == {"observacoes", "arestas"}


def test_descanso_sem_sessao_recusa(tmp_path):
    proc = _rodar_descansar([], entrada="", env_extra={"OPS_LOG_DIR": str(tmp_path / "ops")})
    assert proc.returncode == 2


def test_abandonada_fecha_e_a_abertura_seguinte_conta(tmp_path):
    ops = tmp_path / "ops"
    (tmp_path / "valkey.json").write_text('{"chaves": []}', encoding="utf-8")   # a chave da parada já venceu
    eventos.emitir_aberta(SESSAO, sujeito=SUJEITO, cadeira="engenharia", diretorio_=ops)

    proc = _rodar_abertura(["engenharia", "--chapeu", "back-end"], pergunta="card 4335",
                           env_extra={"PF_SUJEITO": SUJEITO}, tmp_path=tmp_path)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    assert d["abandonadas"]["quantas"] == 1
    assert "1 sessão sua terminou sem descanso desde a última abertura" in d["avisos"]
    regs = _eventos(ops)
    assert any(r.get("evento") == "sessao_encerrada" and r.get("sobre") == SESSAO
               and r.get("desfecho") == "abandonada" for r in regs)
    assert any(r.get("evento") == "sessao_aberta" and r.get("sobre") == d["sessao_id"] for r in regs)

    # a seguinte não conta de novo a mesma, nem a que acabou de abrir (a chave dela segue viva)
    (tmp_path / "valkey.json").write_text(json.dumps({"chaves": [f"sessao:{d['sessao_id']}"]}), encoding="utf-8")
    proc2 = _rodar_abertura(["engenharia"], pergunta="de novo", env_extra={"PF_SUJEITO": SUJEITO},
                            tmp_path=tmp_path)
    d2 = json.loads(proc2.stdout)
    assert d2["abandonadas"]["quantas"] == 0
    assert not any("sem descanso" in a for a in d2["avisos"])


def test_abandonada_com_a_memoria_fora_diz_que_nao_olhou(tmp_path):
    (tmp_path / "valkey.json").write_text('{"fora": true}', encoding="utf-8")
    eventos.emitir_aberta(SESSAO, sujeito=SUJEITO, cadeira="engenharia", diretorio_=tmp_path / "ops")

    proc = _rodar_abertura(["engenharia"], pergunta="x", env_extra={"PF_SUJEITO": SUJEITO}, tmp_path=tmp_path)

    d = json.loads(proc.stdout)
    assert d["abandonadas"]["quantas"] is None
    assert any(a.startswith("não consegui olhar") for a in d["avisos"])


def test_publicar_grava_etiqueta_de_qualquer_ficha_e_recusa_tipo_fora_e_sem_destinatario(tmp_path):
    destino = tmp_path / "mensagens.jsonl"
    nova = "capacidade:uma-que-o-codigo-nao-conhece"
    env = {"PF_MENSAGEM_ARQUIVO": str(destino), "PF_SESSAO": SESSAO,
           "PF_FICHARIO_FIXTURE": _fichario(tmp_path, [nova, "persona:dados"])}
    base = {"enunciado": "o ornitorrinco põe ovo", "quem": "persona:dados", "destinatario": ["persona:dados"],
            "tipo-de-mensagem": "afirmacao"}

    proc = _rodar_descansar(["publicar", "--json"], entrada=json.dumps({**base, "etiqueta": [nova]}),
                            env_extra=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["gravada"] is True
    gravada = json.loads(destino.read_text(encoding="utf-8").splitlines()[0])
    assert gravada["etiqueta"] == [nova]
    assert gravada["correlacao"] == SESSAO

    recusas = {
        "tipo-de-mensagem fora do dicionário": {**base, "tipo-de-mensagem": "licao"},
        "sem destinatario": {k: v for k, v in base.items() if k != "destinatario"},
        "sem tipo-de-mensagem": {k: v for k, v in base.items() if k != "tipo-de-mensagem"},
        "sem quem": {k: v for k, v in base.items() if k != "quem"},
        "sem enunciado": {**base, "enunciado": " "},
        "etiqueta que não é chave de ficha": {**base, "etiqueta": ["preferencia-do-dono"]},
        "destinatário que não é chave de ficha": {**base, "destinatario": ["ia"]},
        "relacao-com-a-anterior fora": {**base, "responde-a": "m1", "relacao-com-a-anterior": "nega"},
    }
    for motivo, dado in recusas.items():
        p = _rodar_descansar(["publicar", "--json"], entrada=json.dumps(dado, ensure_ascii=False), env_extra=env)
        assert p.returncode == 2, motivo
        assert motivo in json.loads(p.stdout)["erro"], (motivo, p.stdout)
    assert len(destino.read_text(encoding="utf-8").splitlines()) == 1


def test_publicar_sem_destino_sai_3(tmp_path):
    msg = {"enunciado": "a", "quem": "persona:dados", "destinatario": ["persona:dados"],
           "tipo-de-mensagem": "afirmacao"}
    env = {"PF_FICHARIO_FIXTURE": _fichario(tmp_path, ["persona:dados"])}
    assert _rodar_descansar(["publicar"], entrada=json.dumps(msg), env_extra=env).returncode == 3


def test_publicar_grava_pela_rota_de_eventos_forca_quem_da_sessao_e_sai_3_quando_mudo(tmp_path):
    import http.server
    import threading

    recebidos: list[tuple[str, dict]] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            tamanho = int(self.headers.get("Content-Length", "0"))
            corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            recebidos.append((self.headers.get("Authorization", ""), corpo))
            ids = [e["evento_id"] for e in corpo["eventos"]]
            resp = json.dumps({"familia": "mensagem", "inseridos": ids, "existentes": []}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)

        def log_message(self, format, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    porta = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        msg = {"enunciado": "fato novo", "quem": "persona:ia", "destinatario": ["dados"],
               "tipo-de-mensagem": "afirmacao"}
        env = {
            "EVENTOS_API_URL": f"http://127.0.0.1:{porta}",
            "EVENTOS_NEGOCIO_TOKEN": "tok-neg-ensaio",
            "PF_CADEIRA": "dados",
            "PF_SESSAO": SESSAO,
        }
        proc = _rodar_descansar(["publicar", "--json"], entrada=json.dumps(msg), env_extra=env)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert json.loads(proc.stdout)["gravada"] is True
        assert len(recebidos) == 1
        auth, corpo = recebidos[0]
        assert auth == "Bearer tok-neg-ensaio"
        ev = corpo["eventos"][0]
        assert ev["quem"] == "dados", "o quem do publicar sai da cadeira da sessão, mesmo com outro quem pedido"
        assert ev["sobre"] == "dados"
        assert ev["correlacao"] == SESSAO
    finally:
        srv.shutdown()
        srv.server_close()

    # Com o banco de eventos mudo (servidor fechado na mesma porta), sai 3.
    proc_mudo = _rodar_descansar(["publicar", "--json"], entrada=json.dumps(msg), env_extra=env)
    assert proc_mudo.returncode == 3


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, *sys.argv[1:]]))
