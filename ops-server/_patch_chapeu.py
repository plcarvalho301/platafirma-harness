#!/usr/bin/env python3
"""Patch do ops-server para a 2a chamada (chapeu) do fluxo de duas chamadas.

read -> assert count==1 -> replace -> write, um alvo por vez. Roda uma vez; fica no
repo como registro. NAO reinicia o servico — isso e ato do TI no gate (o ops-mcp roda
sob systemd --user do TI, e reiniciar superficie em producao pede sign-off dele).
"""
from __future__ import annotations
import sys, pathlib

ALVO = pathlib.Path(__file__).with_name("server.py")
src = ALVO.read_text(encoding="utf-8")


def troca(velho: str, novo: str, rotulo: str) -> None:
    global src
    n = src.count(velho)
    assert n == 1, f"{rotulo}: esperava 1 ocorrencia, achei {n} — abortando sem gravar"
    src = src.replace(velho, novo)
    print(f"  ok: {rotulo}")


# 1) assinatura de _montar + propagacao de --chapeu no argv
troca(
    "def _montar(cadeira: str, atualizar: bool) -> dict:",
    "def _montar(cadeira: str, atualizar: bool, chapeu: str = \"\") -> dict:",
    "assinatura _montar",
)
troca(
    '    argv = [str(RAIZ / "bin" / "monta-sessao"), alvo, "--json"]\n'
    "    if not atualizar:\n"
    '        argv.append("--sem-atualizar")',
    '    argv = [str(RAIZ / "bin" / "monta-sessao"), alvo, "--json"]\n'
    "    if not atualizar:\n"
    '        argv.append("--sem-atualizar")\n'
    "    if chapeu:\n"
    '        argv += ["--chapeu", chapeu.strip()]',
    "argv --chapeu",
)

# 2) assinatura da tool + propagacao para _montar
troca(
    'async def monta_sessao(cadeira: str = "", atualizar: bool = True) -> dict:',
    'async def monta_sessao(cadeira: str = "", atualizar: bool = True, chapeu: str = "") -> dict:',
    "assinatura tool monta_sessao",
)
troca(
    "    r = await anyio.to_thread.run_sync(_montar, cadeira, atualizar)\n"
    '    _audit(tool="monta_sessao", cadeira=cadeira, atualizar=atualizar,',
    "    r = await anyio.to_thread.run_sync(_montar, cadeira, atualizar, chapeu)\n"
    '    _audit(tool="monta_sessao", cadeira=cadeira, atualizar=atualizar, chapeu=chapeu,',
    "chamada _montar + audit",
)

# 3) docstring: descreve o fluxo NOVO de duas chamadas (o cliente le isto)
DOC_VELHO = '''    """Devolve, numa chamada, o contexto de abertura de uma cadeira da PlataFirma:
    persona canônica, tool-manifest que ELA declara, org canônico e a mesa.

    NÃO traz fila nem board. A abertura carrega só o que é impedimento — o que, sem
    ato, deixa o estado como está —, e hoje isso é a mesa. Caixa e carteira saem por
    `fila` e `tarefas`, verbos chamados por ordem do dono como qualquer outro.

    Chamar no lugar de encadear leituras na abertura de sessão — é o que esta tool
    existe para matar. Ler o manifesto NÃO é pré-condição para pensar nem para
    responder: a tool é chamável sob demanda, não obrigatória na entrada.

    `cadeira`: sufixo da persona (`TI`, `IA`, `fabrica`) — o prefixo `claudinho-`/
    `claudinha-` é aceito e descartado. Vazia ou desconhecida devolve `cadeiras`
    com a lista válida, nunca erro mudo.

    `atualizar` (default true): dá `git pull --ff-only` nos clones de persona e org
    antes de ler. Falha de rede não interrompe — o pacote vem do clone com
    `atualizado: false` declarado. Com ou sem pull, `repos` traz sempre `sha`,
    `head_em` (data do commit servido) e `sincronizado_em` (último fetch): clone
    velho e clone no head são indistinguíveis sem isso, e servir do clone só é
    seguro quando a idade vem declarada.

    O pacote sai como CATÁLOGO DE PEÇAS (#189 fase 5): `pecas` é uma lista em ordem de
    injeção, e cada item traz `{peca, dono, ref, sha, regime, tokens, frescor}` mais o
    conteúdo servido. Persona, tool-manifest da cadeira, núcleo comum, org, antirreabertura,
    mesa e índice de cadernos são peças — não há mais uma chave por artefato. Peça que falta
    vem com `frescor: indisponivel` e o motivo, nunca omitida: pacote sem a peça e pacote
    com peça vazia seriam indistinguíveis.

    `pacote` traz a conta do que foi servido — número de peças, tokens medidos com o
    tokenizador do harness, método da contagem e o SHA do clone do montador — e diz se o
    registro em `sessao.peca_servida` aconteceu. `avisos` traz teto estourado, clone
    atrasado e divergência entre o que a persona declara e o que o catálogo serve.

    Persona sem linha `FERRAMENTAL:` devolve `manifesto.ausente` com aviso explícito.
    Ausência declarada, nunca omissão silenciosa. Sem caso vivo hoje: o exemplo que
    morava aqui era a claudinha-osint, desligada em 15/08/2026 (org:0002).
    """'''

DOC_NOVO = '''    """Contexto de abertura de uma cadeira da PlataFirma, em DUAS CHAMADAS
    (refactor F5/#2386, docs/abertura-de-sessao/abertura-novo-pedro/P2). Substitui a
    chamada única que despejava todas as peças de abertura de uma vez.

    1ª chamada — monta_sessao(cadeira): persona, ofício (núcleo comum), dono (conduta),
    caderno-head, org, catálogo de existência, índice de cadernos. DEVOLVE OS SLUGS DE
    CHAPÉU em `chapeus_disponiveis` e termina numa pergunta: qual chapéu vestir. Sem o
    chapéu a sessão ainda não trabalha — faltam manifesto da cadeira, caderno do chapéu,
    risco e mesa.

    2ª chamada — monta_sessao(cadeira, chapeu=<slug>): chapéu, tool-manifest da cadeira,
    caderno do chapéu, risco (matriz de risco — substitui a antiga antirreabertura) e a
    mesa. DEVOLVE A FITA. A instrução de arranque manda responder a pergunta da 1ª antes
    de qualquer outra coisa.

    Por que duas: chapéu não se pré-carrega — só a 2ª chamada sabe qual foi escolhido, e
    carregar os três seria contexto gasto em dois que a sessão não vai usar. A fase é
    dirigida por `gatilho.evento` no catálogo (`abertura` / `chapeu`), não por lista fixa.

    `cadeira`: sufixo da persona (`TI`, `IA`) — prefixo `claudinho-`/`claudinha-` aceito
    e descartado. Vazia ou desconhecida devolve `cadeiras`, nunca erro mudo.

    `chapeu`: slug do chapéu para a 2ª chamada. Ausente ou desconhecido devolve
    `chapeus_disponiveis`, nunca erro mudo. Só tem efeito na 2ª chamada.

    `atualizar` (default true): `git pull --ff-only` nos clones antes de ler. Falha de
    rede não interrompe — `repos` traz `sha` e `frescor` do clone servido.

    O pacote sai como CATÁLOGO DE PEÇAS: `pecas` é lista em ordem de injeção
    (estável→volátil dentro da fase), cada item com `{peca, dono, ref, sha, regime,
    tokens, frescor}` mais o conteúdo. Peça que falta vem `frescor: indisponivel` com o
    motivo, nunca omitida — pacote sem a peça e pacote com peça vazia seriam
    indistinguíveis. `pacote` traz a conta do servido e o registro em `sessao`. `avisos`
    traz teto estourado, clone atrasado e divergência persona×catálogo.
    """'''

troca(DOC_VELHO, DOC_NOVO, "docstring da tool")

ALVO.write_text(src, encoding="utf-8")
print(f"\nOK — {ALVO} atualizado.")
