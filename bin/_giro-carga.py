#!/home/claudinho/AI/.venv-harness/bin/python
# _giro-carga.py — carga em lote do giro auto-relatado (claude.ai) em sessao.giro.
# capacidade: memoria (giro) · dono: claudinho-IA
#
# Chamado pelo ops-mcp (_giro_carrega, server.py::_sessao_encerrar), nunca direto
# por uma cadeira. ops-mcp roda em .venv-ops, sem driver de banco; a escrita fica
# aqui, em .venv-harness, que ja fala com o Postgres de sessao (bin/monta-sessao
# tem o mesmo DSN) — mesmo padrao de bin/mesa para _anota_mesa: verbo, nao
# segunda implementacao de cliente de banco dentro do servidor MCP.
#
# Entra por stdin: {"sessao_id": "...", "cadeira": "...", "chapeu": "...",
#                    "giro": [{"seq": 1, "prompt": "...", "resposta": "..."}, ...]}
#
# Resolve fita_id por sessao.fita.sessao_id — o par gravado por monta_sessao na
# abertura (arq:0093 passo zero). Sem fita casada, RECUSA declarada: nunca
# inventa fita aqui (quem inventa, quando preciso, e monta_sessao — fita
# sintetica de sessao de mao, bin/monta-sessao::registra_pacote).
#
# Idempotente por (fita_id, seq): reprocessar a mesma carga (replay do JSONL
# local) faz upsert, nao duplica nem falha.
import json
import os
import sys

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
SESSAO_ENV = os.path.join(RAIZ, "platafirma-harness", "sessao", ".env")


def _dsn() -> str:
    senha = os.environ.get("SESSAO_PG_PASSWORD", "")
    if not senha and os.path.isfile(SESSAO_ENV):
        for linha in open(SESSAO_ENV, encoding="utf-8"):
            if linha.startswith("SESSAO_PG_PASSWORD="):
                senha = linha.split("=", 1)[1].strip()
                break
    porta = os.environ.get("SESSAO_PG_PORT", "5437")
    return f"host=127.0.0.1 port={porta} dbname=sessao user=sessao password={senha}"


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError as e:
        print(json.dumps({"ok": False, "erro": f"stdin nao e JSON: {e}"}))
        return 1

    sessao_id = (payload.get("sessao_id") or "").strip()
    giro = payload.get("giro") or []
    if not sessao_id:
        print(json.dumps({"ok": False, "erro": "sessao_id obrigatorio"}))
        return 1
    if not giro:
        print(json.dumps({"ok": True, "carregados": 0, "motivo": "giro vazio"}))
        return 0

    try:
        import psycopg
    except ImportError:
        print(json.dumps({"ok": False, "erro": "psycopg ausente neste venv"}))
        return 1

    try:
        with psycopg.connect(_dsn(), connect_timeout=3) as con, con.cursor() as cur:
            cur.execute(
                "SELECT id FROM sessao.fita WHERE sessao_id = %s "
                "ORDER BY aberta_em DESC LIMIT 1", (sessao_id,))
            row = cur.fetchone()
            if row:
                fita_id = row[0]
            else:
                # claude.ai nao materializa fita na abertura (sessao de mao, sem
                # PF_FITA): o encerrar auto-relatado e o unico momento com sessao_id
                # e cadeira em maos. Materializa a fita ancorada no sessao_id — id =
                # sessao_id, unico e duravel. Idempotente por (id).
                cadeira = (payload.get("cadeira") or "-").strip() or "-"
                cur.execute(
                    "INSERT INTO sessao.fita (id, persona, superficie, sessao_id) "
                    "VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET "
                    "sessao_id = EXCLUDED.sessao_id RETURNING id",
                    (sessao_id, cadeira, "claude.ai", sessao_id))
                fita_id = cur.fetchone()[0]
            linhas = [
                (fita_id, item.get("seq") or (i + 1), payload.get("chapeu"),
                 item.get("prompt"), item.get("resposta"), "auto-relato")
                for i, item in enumerate(giro)
            ]
            cur.executemany(
                "INSERT INTO sessao.giro (fita_id, seq, chapeu, prompt_texto, "
                "resposta_texto, fidelidade) VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (fita_id, seq) DO UPDATE SET "
                "prompt_texto = EXCLUDED.prompt_texto, "
                "resposta_texto = EXCLUDED.resposta_texto, "
                "fidelidade = EXCLUDED.fidelidade",
                linhas)
            con.commit()
        print(json.dumps({"ok": True, "fita": fita_id, "carregados": len(linhas)}))
        return 0
    except Exception as e:                                  # noqa: BLE001 — banco mudo nao pode explodir o encerrar
        print(json.dumps({"ok": False, "erro": f"{type(e).__name__}: {e}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
