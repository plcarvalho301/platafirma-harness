"""Despacho de `conferir ontologia` (card #4276; referencias/instancias/verbo/ontologia.md).

Confere o que já está gravado num estrato (`estrato:<slug>`), numa capacidade (`capacidade:<slug>`) ou numa classe (`<slug>`):
- exige o escopo com saída 2 antes de chamar a Olaria;
- chama `Cliente.raciocinar` por HTTP sem abrir o banco nem importar `olaria`;
- traduz a resposta em saídas 0 (conforme), 1 (divergente ou alvo inexistente), 2 (uso inválido), 3 (dependência fora) e 5 (prazo acabado no meio), sem nunca dizer `conforme` em 3 ou 5.
"""
from __future__ import annotations

import os
import sys

from _olaria import saida as sd
from _olaria.cliente import (
    AmbienteIncompleto,
    Cliente,
    PrazoAcabou,
    SemConexao,
    SemResposta,
    preencher_do_cofre,
)
from _olaria.saida import Saida

PEDIDOS_DE_AJUDA = ("--help", "-h", "--ajuda")
PROXIMO_PADRAO = "conferir ontologia capacidade:<slug>"

USAGE = """\
uso:
  conferir ontologia <estrato:slug|capacidade:slug|classe> [--json]
  conferir --help

saídas:
  0  conforme: o escopo pedido zera na régua e no raciocinador
  1  divergente: a régua ou o raciocinador acusou erro, ou o estrato, a capacidade ou a classe não existe
  2  uso: falta o ato `ontologia` ou o escopo `<estrato:slug|capacidade:slug|classe>`, ou flag desconhecida
  3  dependência: a Olaria, o banco ou o raciocinador não responderam, ou falta OLARIA_URL / OLARIA_CHAVE
  5  indeterminável: o prazo acabou no meio da conferência
"""


def _separar_json(args: list) -> tuple[list, bool]:
    return [a for a in args if a != "--json"], "--json" in args


def _erro_uso(onde: str, recebido: object, cura: str, *, como_json: bool = False,
              proximo: str = PROXIMO_PADRAO) -> Saida:
    return sd.erro_de_uso(
        "uso-invalido",
        onde,
        recebido,
        "A conferência da ontologia exige o escopo: `conferir ontologia <estrato:slug|capacidade:slug|classe>`.",
        cura,
        proximo,
        como_json=como_json,
    )


def _erro_prazo(alvo: str, motivo: str, *, como_json: bool = False) -> Saida:
    d = sd.erro_6(
        "prazo-estourado",
        alvo,
        motivo,
        "A conferência da ontologia tem de terminar dentro do prazo do verbo e do serviço.",
        "Divida o escopo conferindo uma classe por vez ou confira a saúde da Olaria.",
        f"conferir ontologia {alvo}",
    )
    if como_json:
        return Saida(sd.INDETERMINAVEL, sd._json({"estado": "indeterminavel", "alvo": alvo, "erros": [d], "total": 1}))
    return Saida(sd.INDETERMINAVEL, sd._linhas(sd.linha_de_erro(d)),
                 stderr=f"conferir ontologia: prazo estourado em {alvo}\n")


def executar(argv: list, env: dict | None = None, *, prog: str | None = None) -> Saida:
    do_processo = env is None
    env = dict(os.environ if env is None else env)
    if do_processo:
        preencher_do_cofre(env)
    if any(a in PEDIDOS_DE_AJUDA for a in argv):
        return Saida(0, USAGE)
    args, como_json = _separar_json(list(argv))
    if not args:
        return _erro_uso("chamada", "(vazio)", "Informe `ontologia` e o escopo a conferir.", como_json=como_json)
    ato, resto = args[0], args[1:]
    if ato != "ontologia":
        return _erro_uso("ato", ato, "Use `conferir ontologia <estrato:slug|capacidade:slug|classe>`.",
                         como_json=como_json)
    if not resto:
        return _erro_uso("alvo", "(ausente)",
                         "Informe o estrato (`estrato:<slug>`), a capacidade (`capacidade:<slug>`) ou a classe (`<slug>`).",
                         como_json=como_json)
    flags = [a for a in resto if a.startswith("--")]
    if flags:
        return _erro_uso("flag", flags[0], f"Opção desconhecida `{flags[0]}`; use apenas `--json`.",
                         como_json=como_json)
    if len(resto) != 1 or not resto[0].strip():
        return _erro_uso("alvo", " ".join(resto),
                         "Passe exatamente um escopo: `estrato:<slug>`, `capacidade:<slug>` ou `<classe>`.",
                         como_json=como_json)
    alvo = resto[0].strip()
    try:
        cliente = Cliente.do_ambiente(env)
    except AmbienteIncompleto as erro:
        return Saida(sd.FORA, stderr=f"conferir: {erro} não está no ambiente: o verbo não chama o serviço sem ela\n")
    try:
        r = cliente.raciocinar(alvo)
    except SemConexao as erro:
        return Saida(sd.FORA, stderr=f"conferir: o serviço não responde em {env.get('OLARIA_URL', '')}: {erro}\n")
    except PrazoAcabou:
        return _erro_prazo(alvo, f"após {cliente.prazo_s:g} s", como_json=como_json)
    except SemResposta as erro:
        texto_erro = str(erro)
        if "Timeout" in texto_erro or "timed out" in texto_erro.lower() or cliente.restante() <= 0.1:
            return _erro_prazo(alvo, texto_erro or f"após {cliente.prazo_s:g} s", como_json=como_json)
        return Saida(sd.FORA, stderr=f"conferir: a resposta do serviço não chegou: {texto_erro}\n")
    return sd.traduzir("raciocinar", r.status, r.corpo, como_json=como_json)


def main(argv: list | None = None, *, prog: str | None = None) -> int:
    saida = executar(list(sys.argv[1:] if argv is None else argv), prog=prog)
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    if saida.stdout:
        sys.stdout.write(saida.stdout)
        sys.stdout.flush()
    if saida.stderr:
        sys.stderr.write(saida.stderr)
        sys.stderr.flush()
    return saida.codigo


if __name__ == "__main__":
    raise SystemExit(main())
