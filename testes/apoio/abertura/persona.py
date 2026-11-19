"""Stub do verbo persona para os testes da abertura."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _extrair_opcao(argv: list[str], flag: str, padrao: str | None = None) -> str | None:
    if flag in argv:
        idx = argv.index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return padrao


def _imprimir_json_ou_texto(conteudo: str, *, como_json: bool, meta: dict | None = None) -> int:
    if como_json:
        payload = {"conteudo": conteudo, "avisos": [], **(meta or {})}
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(conteudo)
    return 0


def _ato_ler(argv: list[str]) -> int:
    cadeira = os.environ.get("PF_CADEIRA", "engenharia")
    if len(argv) > 1 and not argv[1].startswith("--"):
        cadeira = argv[1]
    chapeu = _extrair_opcao(argv, "--chapeu")
    chave = _extrair_opcao(argv, "--chave")
    parte = _extrair_opcao(argv, "--parte") or ("chapeu" if chapeu else "tudo")
    como_json = "--json" in argv

    if chave and chave.startswith("inexistente"):
        print(f"persona: não existe na casa nova: {parte} {chave}", file=sys.stderr)
        return 1

    if parte == "persona":
        alvo = chave or cadeira
        print(f"# Persona {alvo}\n\nEntidade: persona\n\nSou a cadeira {alvo}.")
        return 0
    if parte == "chapeu":
        alvo_ch = chave or chapeu
        print(f"# Chapéu {alvo_ch}\n\nEntidade: chapeu\n\nRecorte {alvo_ch} da cadeira {cadeira}.")
        return 0
    if parte == "posturas":
        perfil = chave or ("cirurgico" if cadeira == "engenharia" else "metodico")
        return _imprimir_json_ou_texto(
            f"POSTURAS EM VIGOR ({perfil})\n- [abertura: decisor] Diante de escolha clara, decide e segue.",
            como_json=como_json,
            meta={"perfil": perfil, "posturas": ["abertura: decisor"]},
        )
    if parte in ("cenarios", "cenario"):
        cen = chave or "tombando-legado"
        return _imprimir_json_ou_texto(
            f"CENÁRIOS PRESENTES\n- [cenário: {cen}] As duas casas convivem até a homologação.",
            como_json=como_json,
            meta={"cenarios": [cen]},
        )
    if parte == "circunstancia":
        circ = chave or "casa-em-tombamento"
        return _imprimir_json_ou_texto(
            f"CIRCUNSTÂNCIA EM VIGOR: {circ}\n- Conferir os dois lados durante o tombamento.",
            como_json=como_json,
            meta={"circunstancia": circ},
        )
    if parte == "ritual":
        rit = chave or "da-casa"
        return _imprimir_json_ou_texto(
            f"RITUAL EM VIGOR: {rit}\n- Fechar pedido avulso no turno.",
            como_json=como_json,
            meta={"ritual": rit},
        )
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        return 2
    ato = argv[0]
    if ato == "nomes":
        arq = Path(os.environ.get("PF_NOMES_FIXTURE") or (BASE / "nomes.md"))
        print(arq.read_text(encoding="utf-8"))
        return 0
    if ato == "cultura":
        print("## Cultura da casa\n\nTodo trabalho passa pela abertura, pelo expediente e pela revisão.")
        return 0
    if ato == "apelidos":
        print("Gabriel Chimpanzé -> engenharia")
        return 0
    if ato == "ler":
        return _ato_ler(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
