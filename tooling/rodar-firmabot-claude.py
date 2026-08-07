#!/usr/bin/env python3
"""Roda as sondas do gold-set-firmabot no gerador via `claude -p`: uma chamada
isolada por sonda (processo novo, sem sessao persistida, sem tools). Resolve
isolamento e janela de contexto ao mesmo tempo -- o custo e trocar candidato
local por API.

NAO e um quarto arm comparavel a G0-gemma4-12b / G0-granite4 / G0-qwen3.5-9b:
aqueles medem viabilidade de MODELO LOCAL (o que roda na maquina, sem
depender de nuvem). Este e referencia de teto via API -- decisao de incluir
como arm oficial e do desenho do instrumento, nao deste script.

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
        user_msg = f"{pergunta}\n\nFontes:\n\n{contexto}"

        out_path = out_dir / f"T0-{n}-resposta.md"
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
        f"por sonda (--no-session-persistence, --tools \"\", sem CLAUDE.md/skills do\n"
        f"repo porque cada processo e novo e nao herda sessao anterior).\n\n"
        f"    modelo      {args.model}\n"
        f"    num_ctx     n/a (API, nao GPU local)\n"
        f"    amostragem  padrao da CLI — sem flag de temperature exposta em --print\n\n"
        f"NAO comparavel a G0-gemma4-12b / G0-granite4 / G0-qwen3.5-9b: aqueles medem\n"
        f"modelo local, este e referencia de teto via API. Incluir como arm oficial da\n"
        f"escada e decisao de desenho do instrumento, nao deste script.\n"
    )
    print(f"pronto: {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
