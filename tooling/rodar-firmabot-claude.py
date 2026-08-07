#!/usr/bin/env python3
"""Roda as sondas do gold-set-firmabot no gerador via `claude -p`: uma chamada
isolada por sonda (processo novo, sem sessao persistida, sem tools).

Prompt IDENTICO ao usado nos arms locais (g0_geracao.py, gemma4-12b e
qwen3.5-9b): mesmo `prompt-firmabot.md` como system, mesmo formato de mensagem
(PERGUNTA: / FONTES:). E a condicao para os 3 arms serem comparaveis --
decisao do dono, 2026-08-06.

Nao identico: amostragem. `claude -p` nao expoe temperature/seed/num_predict
na CLI (--help nao lista), diferente dos locais (temperature=0, seed=42,
num_predict=900 via API do Ollama). Assimetria que fica registrada, nao
escondida -- nao ha flag pra fechar por aqui.

Reentrante: pula sonda ja respondida.

Uso: python3 tooling/rodar-firmabot-claude.py [--model sonnet] [--out DIR]
"""
import argparse, json, pathlib, subprocess, sys, datetime

BASE = pathlib.Path(__file__).resolve().parent.parent
SYSTEM_PATH = BASE / "avaliacao/gold-set-firmabot/prompt-firmabot.md"
RESULT_DIR = BASE / "avaliacao/gold-set-firmabot/resultados/G0-rag-base"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet")
    ap.add_argument(
        "--out",
        default=str(BASE / "avaliacao/gold-set-firmabot/resultados/G0-claude-referencia"),
    )
    args = ap.parse_args()

    system_prompt = SYSTEM_PATH.read_text()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(RESULT_DIR.glob("T0-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    for f in files:
        data = json.loads(f.read_text())
        n = data["n"]
        pergunta = data["pergunta"]
        contexto = data["retorno"]["contexto"]
        user_msg = f"PERGUNTA: {pergunta}\n\nFONTES:\n{contexto}"

        out_path = out_dir / f"T0-{n}-resposta.md"
        if out_path.exists() and not out_path.read_text().startswith("ERRO"):
            print(f"[{n}] já feito, pulando", file=sys.stderr)
            continue
        print(f"[{n}] {pergunta[:60]!r}", file=sys.stderr)

        result = subprocess.run(
            [
                "claude", "-p",
                "--system-prompt", system_prompt,
                "--tools", "",
                "--no-session-persistence",
                "--model", args.model,
                user_msg,
            ],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            out_path.write_text(f"ERRO (rc={result.returncode})\n{result.stderr}")
            continue
        out_path.write_text(result.stdout)

    carimbo = out_dir / "carimbo.md"
    carimbo.write_text(
        f"# Carimbo — G0 geração, claude ({args.model})\n\n"
        f"Rodada: {datetime.datetime.utcnow().isoformat()}Z\n\n"
        f"Executor: tooling/rodar-firmabot-claude.py — uma chamada `claude -p` isolada\n"
        f"por sonda (--no-session-persistence, --tools \"\", processo novo a cada sonda).\n\n"
        f"    modelo      {args.model}\n"
        f"    num_ctx     n/a (API, nao GPU local)\n"
        f"    amostragem  nao exposta na CLI --print (sem temperature/seed/num_predict)\n"
        f"    sistema     avaliacao/gold-set-firmabot/prompt-firmabot.md — IDENTICO ao\n"
        f"                usado em G0-gemma4-12b e G0-qwen3.5-9b (g0_geracao.py)\n\n"
        f"Arm oficial (decisao do dono, 2026-08-06), papel de referência de teto —\n"
        f"não substitui G0-gemma4-12b / G0-qwen3.5-9b, que medem viabilidade local.\n"
        f"Prompt agora idêntico aos dois; amostragem não é controlável via --print.\n"
    )
    print(f"pronto: {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
