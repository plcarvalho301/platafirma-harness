"""Comandos de sala — parametro de giro que o dono muda do celular, sem shell.

Card 449, decisao do dono em 15/08/2026. Tres comandos, e uma mecanica so: dois
escrevem no journal, um le. Nenhum deles vira giro — o produto e o efeito no
proximo giro, nao uma resposta do modelo.

O que NAO se resolve aqui, e por que:

  - **Nao e `settings.json`.** `chat` reescreve `~/AI/fitas/<cadeira>/.claude/`
    a cada giro (`prepara_cwd`), de proposito. Ajuste gravado la se perde no
    giro seguinte, e o dono ficaria configurando no vazio.
  - **Nao e variavel de ambiente.** `PF_CHAT_MODELO` vale para o worker inteiro
    — um valor para todas as salas, perdido no restart. Comando de sala exige
    valor POR SALA.
  - **Logo e o journal**, lido pelo worker na montagem do giro e repassado ao
    verbo como flag.

A preferencia morre com a rotacao (`troca_de_sala`): sala nova volta ao default.

## O prefixo `pf` e PROVISORIO

Decisao do dono em 15/08/2026: fica, mas como marca de provisoriedade — a forma
final nao foi discutida, e discuti-la naquele momento teria travado a entrega.
Quem for mexer aqui depois: a escolha de `pf` NAO e argumento a favor de `pf`.
O que a substituir precisa resolver e o problema abaixo, nao a estetica.

**Por que existe prefixo.** Comando so vale como mensagem INTEIRA (mesma regra
de `rotacao.COMANDOS`), e mesmo assim `estado`, `custo` ou `esforco extra`
sozinhos sao fala plausivel numa conversa. Ter argumento nao salva: `esforco
extra` tem argumento e continua sendo frase. O que desambigua e o prefixo.

**Por que `zerar` nao leva prefixo.** Esta em producao e funciona no celular do
dono. Trocar a forma de um comando destrutivo por simetria custa mais do que a
simetria vale. A assimetria e conhecida e aceita, nao esquecimento.

**Por que sem barra.** `/qualquer-coisa` e interceptado pelo cliente Matrix
antes de virar evento: o Element recusa com "Unrecognised command" e nao envia
nada. Medido no celular do dono em 15/08; o mesmo comportamento esta aberto no
element-web desde 2017 (issue #4630). Nao ha o que consertar do nosso lado — a
mensagem morre antes de existir.
"""

from __future__ import annotations

import time

from comum import journal

PREFIXO = "pf"

# Enum do motor, medido em `claude --help` na 2.1.220 — nao inventado e nao
# traduzido. `ultracode` nao esta no --help mas esta no binario: e apelido que
# resolve para `xhigh` (`hBc={ultracode:"xhigh"}`) E liga a orquestracao de
# workflow permanente da sessao ("xhigh effort plus standing dynamic-workflow
# orchestration"). Por isso entra aqui como valor proprio, e nao como sinonimo.
ESFORCOS = ("low", "medium", "high", "xhigh", "max", "ultracode")

# Apelidos que o help declara ("an alias for the latest model"). Nome completo
# (`claude-fable-5`) fica de fora de proposito: alias segue o modelo novo, nome
# completo envelhece pinado numa versao que um dia sai do ar.
MODELOS = ("opus", "sonnet", "haiku", "fable", "quinzinho", "qwen", "pandinha")

# Aliases que rodam no motor LOCAL (ollama), nao no Claude. O worker escolhe o
# motor por este mesmo alias (bin/chat: escolhe_motor). Aqui e so para verbalizar
# na sala QUAL cerebro passou a responder — o dono pediu saber, 01/09/2026.
MODELOS_LOCAIS = {"quinzinho": "qwen3.5:9b", "qwen": "qwen3.5:9b", "pandinha": "qwen3.5:9b"}

# Chaves gravadas no journal. Sao o contrato com o worker: mudar o nome aqui
# quebra o repasse, e o giro seguinte volta calado ao default.
K_MODELO = "modelo"
K_ESFORCO = "esforco"


class Comando:
    def __init__(self, verbo: str, arg: str = "") -> None:
        self.verbo = verbo
        self.arg = arg


def interpreta(corpo: str) -> Comando | None:
    """Mensagem inteira, prefixo `pf`, uma ou duas palavras. Qualquer outra
    coisa e conversa e volta None — na duvida, o texto vira giro. Errar para o
    lado de girar custa um giro; errar para o lado de engolir custa uma fala do
    dono que ninguem responde."""
    partes = corpo.strip().lower().split()
    if len(partes) < 2 or partes[0] != PREFIXO:
        return None
    if len(partes) > 3:
        return None
    return Comando(partes[1], partes[2] if len(partes) == 3 else "")


def _idade(nascida: float | None) -> str:
    if not nascida:
        return "?"
    h = (time.time() - nascida) / 3600.0
    return f"{h:.0f} h" if h >= 1 else f"{h * 60:.0f} min"


def _estado(con, sala: str, cadeira: str) -> str:
    pref = journal.preferencias_da_sala(con, sala)
    fita = journal.fita_da_sala(con, sala)
    return (
        f"**Estado da sala** — cadeira `{cadeira}`\n\n"
        f"- modelo: {pref.get(K_MODELO) or '— (default do verbo)'}\n"
        f"- esforco: {pref.get(K_ESFORCO) or '— (default do motor)'}\n"
        f"- giros nesta fita: {journal.giros_da_sala(con, sala)}\n"
        f"- idade da sala: {_idade(journal.nascimento_da_sala(con, sala))} (rotaciona em 24 h)\n"
        f"- fita: `{fita[:8] if fita else 'ainda nao abriu'}`"
    )


def _fixa(con, sala: str, cmd: Comando, chave: str, enum: tuple[str, ...], rotulo: str) -> str:
    """Valor fora do enum vira erro explicito na sala, e nunca giro.

    Medido em 15/08 na 2.1.220: `claude --effort ultracode` foi aceito sem erro,
    e o `system/init` NAO carimba o effort aplicado. Ou seja, o motor nao valida
    e o stream nao prova — a validacao tem de ser nossa, aqui, antes de gravar.
    """
    if not cmd.arg:
        return f"**Falta o valor.** `{PREFIXO} {cmd.verbo} <{rotulo}>` — {', '.join(enum)}."
    if cmd.arg not in enum:
        return (
            f"**`{cmd.arg}` nao e um {rotulo} valido.** Aceito: {', '.join(enum)}. "
            "Nada foi mudado."
        )
    journal.grava_preferencia(con, sala, chave, cmd.arg)
    # Verbaliza o cerebro: modelo local (ollama) vs Claude, para o dono saber quem
    # responde a partir de agora. So se aplica a `modelo`; esforco nao troca motor.
    cerebro = ""
    if chave == K_MODELO:
        if cmd.arg in MODELOS_LOCAIS:
            cerebro = f" — a partir de agora quem responde e o modelo LOCAL 🖥️ (`{MODELOS_LOCAIS[cmd.arg]}` no ollama), nao o Claude."
        else:
            cerebro = " — quem responde e o Claude ☁️ (modelo remoto)."
    return (
        f"**{rotulo.capitalize()} desta sala: `{cmd.arg}`.**{cerebro} Vale do proximo "
        "giro em diante, e volta ao default quando a sala rotacionar."
    )


def executa(con, sala: str, cadeira: str, cmd: Comando) -> str:
    """Texto do aviso a publicar na sala. Sempre devolve algo: comando que nao
    responde e indistinguivel, para o dono, de mensagem que se perdeu."""
    if cmd.verbo == "estado":
        return _estado(con, sala, cadeira)
    if cmd.verbo == K_MODELO:
        return _fixa(con, sala, cmd, K_MODELO, MODELOS, "modelo")
    if cmd.verbo in (K_ESFORCO, "esforço"):
        return _fixa(con, sala, cmd, K_ESFORCO, ESFORCOS, "esforco")
    return (
        f"**`{cmd.verbo}` nao e comando.** Tenho `{PREFIXO} modelo <alias>`, "
        f"`{PREFIXO} esforco <nivel>` e `{PREFIXO} estado`. Para tela limpa, `zerar`."
    )
