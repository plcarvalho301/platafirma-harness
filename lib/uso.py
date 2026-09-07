#!/usr/bin/env python3
# uso.py — mapa, forma por ato e erro gracioso para os verbos em Python.
# capacidade: construcao
# dono: claudinho-TI
# card: #3016 (feature #3015 — todo verbo com --help e erro de verbo gracioso)
#
# Irma de lib/uso.sh, mesma regua de forma, outro substrato:
#
#   N1  `<verbo>` sem ato, `--help`, `--ajuda`, `-h`  -> mapa com uma linha por ato +
#       tabela `exit:`, em STDOUT, exit 0.
#   N2  `<verbo> <ato> --help`                        -> a forma do ato, STDOUT, exit 0.
#   erro -> linha 1 `erro: <o que faltou>`, depois `corrija:`; STDERR, exit 2.
#
# O argparse ja sabe montar N1 e N2 — o que ele NAO faz e falar portugues, aceitar
# `--ajuda` e errar no formato da casa. Esta camada e so isso; quem tem despacho
# proprio (sem argparse) usa `erro()` e `mapa()` diretamente.
#
#   from uso import Uso, erro, liga_lib   # liga_lib() acha ../lib a partir do verbo
#
#   p = Uso(descricao="memoria de trabalho da cadeira, por chapeu",
#           saidas="0 ok · 1 falha declarada · 2 uso")
#   atos = p.atos()                      # subparsers ja rotulados em pt-BR
#   ver = atos.novo("ver", "o que esta pendente")

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

__all__ = ["Uso", "erro", "nome_do_verbo", "liga_lib", "mapa", "intercepta", "atos_do_cabecalho"]


# --- a mesma regua da lib/uso.sh, para quem nao usa argparse ------------------
#
# Metade dos verbos em Python tem despacho proprio (`sys.argv[1]` num if/elif), e
# converte-los a argparse seria reescrever verbo, nao dar-lhes forma. As funcoes
# abaixo leem o CABECALHO do arquivo do verbo — os mesmos `# ato:` e `# atos:` que a
# lib bash le — e servem N1, N2 e a recusa de ato desconhecido. Uma regua, dois
# substratos, zero texto duplicado.


def _linhas(fonte):
    try:
        return fonte.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _blocos(fonte):
    """[(sinopse, [detalhe])] das linhas `# ato:` do cabecalho. Bloco fecha em
    qualquer linha de comentario que nao seja detalhe (`#` + dois espacos)."""
    saida = []
    dentro = False
    for linha in _linhas(fonte):
        if linha.startswith("#!"):
            continue
        if linha.startswith("# ato:"):
            saida.append((linha[6:].strip(), []))
            dentro = True
        elif dentro and linha.startswith("#  "):
            saida[-1][1].append(linha[1:].strip())
        elif linha.startswith("#"):
            dentro = False
        else:
            break
    return saida


def _chave(fonte, chave):
    marca = f"# {chave}:"
    for linha in _linhas(fonte):
        if linha.startswith(marca):
            return linha[len(marca):].strip()
    return ""


def atos_do_cabecalho(fonte):
    """Nomes dos atos: dos blocos `# ato:` e, na falta deles, da lista `# atos:`.
    Entrada que nao e nome de ato (`ato=<stack>`, `nenhum`, frase com espaco) fica
    de fora — verbo de alvo livre nao tem conjunto a conferir."""
    blocos = _blocos(fonte)
    if blocos:
        return [b[0].split()[0] for b in blocos if b[0].split()]
    crus = [p.strip() for p in _chave(fonte, "atos").split(",")]
    return [p for p in crus
            if p and p != "nenhum" and p.replace("-", "").replace("_", "").isalnum()]


def _proposito(fonte):
    linhas = _linhas(fonte)
    for linha in linhas[1:4]:
        if linha.startswith("# ") and " — " in linha:
            return linha[2:].strip()
    return ""


def _saidas(fonte):
    return _chave(fonte, "exit") or _SAIDAS_PADRAO


def _mapa(verbo, fonte):
    blocos = _blocos(fonte)
    itens = []
    for sinopse, _ in blocos:
        if " — " in sinopse:
            forma, resumo = sinopse.split(" — ", 1)
        else:
            forma, resumo = sinopse, ""
        itens.append((forma.strip(), resumo.strip()))
    if not itens:
        itens = [(nome, "") for nome in atos_do_cabecalho(fonte)]
    return mapa(verbo, _proposito(fonte), itens, _saidas(fonte))


def _forma(verbo, fonte, alvo):
    for sinopse, detalhe in _blocos(fonte):
        if not sinopse.split() or sinopse.split()[0] != alvo:
            continue
        if " — " in sinopse:
            forma, resumo = sinopse.split(" — ", 1)
        else:
            forma, resumo = sinopse, ""
        linhas = [f"uso: {verbo} {forma.strip()}"]
        if resumo.strip():
            linhas.append(f"  {resumo.strip()}")
        linhas.append("")
        linhas += [f"  {d}" for d in detalhe]
        linhas += ["", f"exit: {_saidas(fonte)}"]
        return "\n".join(linhas)
    return _mapa(verbo, fonte)


_AJUDA = ("-h", "--help", "--ajuda", "ajuda")


def intercepta(argv=None, ato_livre=False, sem_ato="mapa", fonte=None):
    """Chamada ANTES de qualquer posicional do verbo (card #3016).

    N1 em stdout/exit 0 para `<verbo>` sem ato, `--help`, `--ajuda`, `-h`; N2 para
    `<verbo> <ato> --help`; recusa graciosa (exit 2) para ato fora do conjunto.
    Nao erra por ajuda: pedido que nao casa com ato declarado cai no mapa.

      ato_livre=True  -> o primeiro argumento e alvo do chamador, nao ato fechado
      sem_ato="passa" -> `<verbo>` pelado ja e chamada valida do verbo
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    arq = Path(fonte or sys.argv[0]).resolve()
    verbo = nome_do_verbo()
    primeiro = argv[0] if argv else ""
    if primeiro in _AJUDA:
        print(_mapa(verbo, arq))
        sys.exit(0)
    if not primeiro:
        if sem_ato == "passa":
            return
        print(_mapa(verbo, arq))
        sys.exit(0)
    declarados = atos_do_cabecalho(arq)
    if len(argv) > 1 and argv[1] in _AJUDA:
        print(_forma(verbo, arq, primeiro) if primeiro in declarados
              else _mapa(verbo, arq))
        sys.exit(0)
    if declarados and not ato_livre and primeiro not in declarados:
        erro(f"ato desconhecido: '{primeiro}'",
             [f"atos de {verbo}: " + ", ".join(declarados),
              f"a forma de um ato: {verbo} <ato> --help"])


def liga_lib() -> None:
    """Poe o diretorio desta lib no sys.path. Chamado pelo verbo antes do import:

        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "lib"))
        from uso import Uso
    """
    aqui = str(Path(__file__).resolve().parent)
    if aqui not in sys.path:
        sys.path.insert(0, aqui)


def nome_do_verbo(argv0: str | None = None) -> str:
    """O nome SERVIDO: `fila`, nao `fila_streams.py`. E o que a cadeira digita."""
    nome = os.path.basename(argv0 or sys.argv[0] or "verbo")
    for sufixo in (".py", ".sh"):
        if nome.endswith(sufixo):
            nome = nome[: -len(sufixo)]
    return nome


def erro(mensagem: str, corrija: str | list[str] | None = None, codigo: int = 2):
    """Erro no formato da casa: linha 1 `erro:`, depois `corrija:`. STDERR, sai 2.

    `corrija` aceita texto (indentado inteiro) ou lista de linhas. Sem ele, a
    correcao e o mapa do verbo, que o chamador passa pronto.
    """
    print(f"erro: {mensagem}", file=sys.stderr)
    if corrija:
        linhas = corrija if isinstance(corrija, list) else corrija.splitlines()
        print("corrija:", file=sys.stderr)
        for linha in linhas:
            print(f"  {linha}" if linha.strip() else "", file=sys.stderr)
    sys.exit(codigo)


def mapa(verbo: str, proposito: str, atos: list[tuple[str, str]], saidas: str) -> str:
    """N1 na mao, para verbo com despacho proprio (sem argparse). Devolve o texto."""
    largura = max((len(forma) for forma, _ in atos), default=0)
    largura = min(max(largura, 12), 40)
    linhas = [proposito, "", f"uso: {verbo} <ato> [args]", ""]
    for forma, resumo in atos:
        if len(forma) <= largura:
            linhas.append(f"  {forma.ljust(largura)}  {resumo}")
        else:
            linhas.append(f"  {forma}")
            linhas.append(f"  {' ' * largura}  {resumo}")
    linhas += ["", f"exit: {saidas}", f"a forma de um ato: {verbo} <ato> --help"]
    return "\n".join(linhas)


# --- traducao das mensagens do argparse -------------------------------------
#
# argparse fala ingles e nao tem gancho de i18n. A lista e curta e fechada: sao as
# mensagens que o usuario de verbo ve. O que nao casar sai como veio — mensagem em
# ingles e pior que em portugues, e mensagem sumida e pior que as duas.
_TRADUCOES = (
    ("the following arguments are required: ", "falta o argumento obrigatorio: "),
    ("unrecognized arguments: ", "argumento nao reconhecido: "),
    ("expected one argument", "a flag exige um valor"),
    ("expected at least one argument", "a flag exige ao menos um valor"),
    ("invalid choice: ", "valor fora do conjunto: "),
    ("(choose from ", "(validos: "),
    ("argument ", "no argumento "),
    ("not allowed with argument", "nao pode vir junto de"),
    ("ambiguous option: ", "opcao ambigua: "),
    ("one of the arguments ", "um dos argumentos "),
    (" is required", " e obrigatorio"),
    ("invalid int value: ", "nao e numero inteiro: "),
)


def _pt(mensagem: str) -> str:
    for de, para in _TRADUCOES:
        mensagem = mensagem.replace(de, para)
    return mensagem


class _Ajuda(argparse.Action):
    """`-h`, `--help` e `--ajuda`, a mesma porta. Sai 0, em STDOUT."""

    def __init__(self, option_strings, dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS, help="mostra esta forma e sai"):
        super().__init__(option_strings=option_strings, dest=dest,
                         default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help(sys.stdout)
        parser.exit(0)


_SAIDAS_PADRAO = "0 ok · 1 falha declarada · 2 uso"


class _Atos:
    """Proxy do objeto de subparsers: cada ato criado por `add_parser` herda a
    tabela `exit:` do pai e ja nasce com `--ajuda`. O verbo nao muda uma linha
    das chamadas que ja tinha — e por isso que a solda e de UMA linha por verbo."""

    def __init__(self, pai: "Uso", sub):
        self._pai = pai
        self._sub = sub

    def add_parser(self, nome, **kw):
        p = self._sub.add_parser(nome, **kw)
        p.saidas = self._pai.saidas
        return p

    # `novo(nome, resumo)` e o acucar de quem escreve verbo novo.
    def novo(self, nome: str, resumo: str, **kw):
        kw.setdefault("help", resumo)
        kw.setdefault("description", resumo)
        return self.add_parser(nome, **kw)

    def __getattr__(self, nome):
        return getattr(self._sub, nome)


class Uso(argparse.ArgumentParser):
    """ArgumentParser da casa: prog = nome servido do verbo, `--ajuda` alias de
    `-h`, cabecalhos e erros em pt-BR, tabela `exit:` no rodape do help.

    Compativel com a assinatura do argparse DE PROPOSITO: trocar
    `argparse.ArgumentParser(...)` por `Uso(...)` no verbo ja liga tudo, e os
    sub-atos vem juntos porque `add_subparsers` fixa `parser_class`."""

    def __init__(self, descricao: str | None = None, saidas: str | None = None, **kw):
        if descricao is not None:
            kw.setdefault("description", descricao)
        kw.setdefault("prog", nome_do_verbo())
        kw.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
        kw["add_help"] = False
        super().__init__(**kw)
        self.saidas = saidas or _SAIDAS_PADRAO
        self.add_argument("-h", "--help", "--ajuda", action=_Ajuda)
        self._positionals.title = "atos" if kw.get("prog") == nome_do_verbo() else "argumentos"
        self._optionals.title = "flags"

    def add_subparsers(self, **kw):
        kw.setdefault("parser_class", type(self))
        kw.setdefault("dest", "ato")
        kw.setdefault("metavar", "<ato>")
        return _Atos(self, super().add_subparsers(**kw))

    # Nome da casa para a mesma coisa.
    def atos(self, **kw) -> _Atos:
        return self.add_subparsers(**kw)

    # --- forma ---------------------------------------------------------------

    def format_usage(self) -> str:
        return super().format_usage().replace("usage: ", "uso: ", 1)

    def format_help(self) -> str:
        texto = super().format_help().replace("usage: ", "uso: ", 1)
        texto = texto.replace("positional arguments:", "argumentos:")
        texto = texto.replace("options:", "flags:")
        texto = texto.replace("optional arguments:", "flags:")
        if getattr(self, "saidas", ""):
            texto = texto.rstrip("\n") + f"\n\nexit: {self.saidas}\n"
        return texto

    # --- erro ----------------------------------------------------------------

    def error(self, message):
        """Formato fixo da casa. O argparse manda a mensagem crua; aqui ela vira
        `erro:` na linha 1 e `corrija:` com a forma logo abaixo, STDERR, exit 2."""
        print(f"erro: {_pt(message)}", file=sys.stderr)
        print("corrija:", file=sys.stderr)
        for linha in self.format_help().splitlines():
            print(f"  {linha}" if linha.strip() else "", file=sys.stderr)
        sys.exit(2)

    def sem_ato(self):
        """`<verbo>` sem ato = mapa em STDOUT, exit 0 — nao e erro, e pergunta."""
        self.print_help(sys.stdout)
        sys.exit(0)
