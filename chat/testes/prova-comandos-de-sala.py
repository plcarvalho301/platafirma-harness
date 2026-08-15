#!/usr/bin/env python3
"""Prova dos comandos de sala (`pf modelo|esforco|estado`) — card 449.

Sem Synapse e sem motor: o que se prova aqui e a fronteira entre COMANDO e FALA,
a validacao do enum e o repasse ao argv. Essas tres coisas nao dependem de rede,
e sao exatamente onde o erro custa caro — comando engolido como fala nao tem
sintoma, e valor invalido gravado so aparece giros depois, no lugar errado.

    python3 chat/testes/prova-comandos-de-sala.py
"""

from __future__ import annotations

import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "recepcao"))

import comandos  # noqa: E402
from comum import journal  # noqa: E402

falhas: list[str] = []


def bate(nome, obtido, esperado):
    if obtido != esperado:
        falhas.append(f"{nome}: esperava {esperado!r}, veio {obtido!r}")


def prova_fronteira():
    """Fala nunca vira comando; comando nunca vira fala."""
    # FALA — tudo isto tem de virar giro
    for fala in (
        "esforco extra",          # o caso que derrubou a palavra nua
        "estado",
        "modelo opus",            # sem prefixo, e frase plausivel
        "zerar",                  # e da rotacao, nao daqui
        "pf",                     # so o prefixo nao e comando
        "pf modelo opus por favor",  # mais de tres palavras
        "vamos falar de pf modelo",  # nao comeca com o prefixo
    ):
        bate(f"fala {fala!r}", comandos.interpreta(fala), None)

    # COMANDO
    for texto, verbo, arg in (
        ("pf estado", "estado", ""),
        ("pf modelo sonnet", "modelo", "sonnet"),
        ("  PF  Esforco  XHIGH  ", "esforco", "xhigh"),  # caixa e espaco sobrando
    ):
        cmd = comandos.interpreta(texto)
        if cmd is None:
            falhas.append(f"comando {texto!r} foi lido como fala")
            continue
        bate(f"verbo de {texto!r}", cmd.verbo, verbo)
        bate(f"arg de {texto!r}", cmd.arg, arg)


def prova_enum(con):
    sala = "!sala:teste"

    # invalido NAO grava
    saida = comandos.executa(con, sala, "claudinho-IA", comandos.interpreta("pf esforco extra"))
    assert "nao e um esforco valido" in saida, saida
    bate("invalido nao gravou", journal.preferencias_da_sala(con, sala), {})

    # ultracode e valido: apelido do motor, resolve xhigh + orquestracao
    comandos.executa(con, sala, "claudinho-IA", comandos.interpreta("pf esforco ultracode"))
    bate("ultracode gravou", journal.preferencias_da_sala(con, sala).get("esforco"), "ultracode")

    # modelo fora da lista de alias nao grava
    comandos.executa(con, sala, "claudinho-IA", comandos.interpreta("pf modelo gpt"))
    bate("modelo invalido", journal.preferencias_da_sala(con, sala).get("modelo"), None)

    comandos.executa(con, sala, "claudinho-IA", comandos.interpreta("pf modelo haiku"))
    bate("modelo valido", journal.preferencias_da_sala(con, sala).get("modelo"), "haiku")

    # verbo desconhecido nao explode e nao grava
    saida = comandos.executa(con, sala, "claudinho-IA", comandos.interpreta("pf voar alto"))
    assert "nao e comando" in saida, saida

    # estado le sem incrementar o contador de giros
    antes = journal.giros_da_sala(con, sala)
    comandos.executa(con, sala, "claudinho-IA", comandos.interpreta("pf estado"))
    bate("estado nao gira", journal.giros_da_sala(con, sala), antes)


def prova_morte_na_rotacao(con):
    """A preferencia e da sala: rotacionou, morreu."""
    velha, nova = "!velha:teste", "!nova:teste"
    journal.grava_cadeira(con, velha, "claudinho-IA")
    journal.grava_preferencia(con, velha, "modelo", "opus")
    journal.troca_de_sala(con, velha, nova, "claudinho-IA")
    bate("velha limpa", journal.preferencias_da_sala(con, velha), {})
    bate("nova nasce sem heranca", journal.preferencias_da_sala(con, nova), {})


def prova_argv():
    """Ausencia de preferencia nao vira flag; presenca vira a flag do motor."""
    sys.path.insert(0, os.path.join(os.path.dirname(RAIZ), "bin"))
    import importlib.util

    spec = importlib.util.spec_from_loader(
        "chatverbo",
        importlib.machinery.SourceFileLoader(
            "chatverbo", os.path.join(os.path.dirname(RAIZ), "bin", "chat")
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    os.environ.pop("PF_CHAT_MODELO", None)
    limpo = mod.MotorClaudeCode().comando("f1", None, "/tmp")
    bate("sem pedido, sem --effort", "--effort" in limpo, False)

    pedido = mod.MotorClaudeCode(modelo="haiku", esforco="ultracode").comando("f1", None, "/tmp")
    bate("--model repassado", pedido[pedido.index("--model") + 1], "haiku")
    bate("--effort repassado", pedido[pedido.index("--effort") + 1], "ultracode")


def prova_plantio_de_skills():
    """Skill do repo tem de chegar na fita — e so a que declarou destino."""
    import importlib.machinery
    import importlib.util

    spec = importlib.util.spec_from_loader(
        "chatverbo2",
        importlib.machinery.SourceFileLoader(
            "chatverbo2", os.path.join(os.path.dirname(RAIZ), "bin", "chat")
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as tmp:
        origem = os.path.join(tmp, "skills")
        for nome, cab in (
            ("universal", "cadeiras: todas"),
            ("so-ti", "cadeiras: [TI]"),
            ("isolada", "cadeiras: nenhuma"),
            ("sem-campo", None),
        ):
            os.makedirs(os.path.join(origem, nome))
            corpo = "---\nname: %s\n%s\n---\ncorpo\n" % (
                nome, cab if cab else "description: x"
            )
            with open(os.path.join(origem, nome, "SKILL.md"), "w") as f:
                f.write(corpo)
        antigo, mod.SKILLS = mod.SKILLS, origem
        try:
            dot = os.path.join(tmp, ".claude")
            os.makedirs(dot)
            bate("plantio em IA", sorted(mod.planta_skills(dot, "IA")), ["universal"])
            bate("plantio em TI", sorted(mod.planta_skills(dot, "TI")), ["so-ti", "universal"])
            # replantio nao acumula: o .claude/ e reescrito a cada giro
            bate("replantio limpa", sorted(mod.planta_skills(dot, "IA")), ["universal"])
            bate(
                "so o plantado existe em disco",
                sorted(os.listdir(os.path.join(dot, "skills"))),
                ["universal"],
            )
        finally:
            mod.SKILLS = antigo


def main():
    with tempfile.TemporaryDirectory() as tmp:
        con = journal.abre(os.path.join(tmp, "j.sqlite3"))
        prova_fronteira()
        prova_enum(con)
        prova_morte_na_rotacao(con)
        prova_argv()
        prova_plantio_de_skills()

    if falhas:
        print("FALHOU:")
        for f in falhas:
            print("  -", f)
        return 1
    print("prova dos comandos de sala: ok")
    return 0


if __name__ == "__main__":
    import importlib.machinery  # noqa: E402  (usado em prova_argv)

    sys.exit(main())
